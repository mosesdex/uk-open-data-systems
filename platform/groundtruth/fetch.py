"""Anonymous fetching.

The platform's whole proposition is that a government body can reproduce every
number without asking anyone's permission. That is only true if nothing here can
quietly acquire credentials, so this module refuses to send them:

  * no Authorization header, no API key, no bearer token
  * no cookies, sent or stored
  * no netrc, no proxy auth

It also catches the trap case found during research: a publisher returning
HTTP 200 with an HTML sign-in page instead of the data it advertises.
"""
from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path

import requests

from .sources import Source

USER_AGENT = "groundtruth/0.1 (+https://mosesdex.github.io/uk-open-data-systems/)"

# Headers that would constitute authentication. Their presence is a bug.
FORBIDDEN_HEADERS = {"authorization", "cookie", "x-api-key", "api-key",
                     "ocp-apim-subscription-key", "proxy-authorization"}

# Extra detail when a mismatch is specifically a sign-in wall. Diagnostic only:
# the admissibility decision is made on content type, not on these.
LOGIN_MARKERS = (b"sign in", b"log in", b"login", b"password",
                 b"authentication", b"csrf")


class CredentialLeak(RuntimeError):
    """Raised when a request would carry authentication of any kind."""


@dataclass(frozen=True)
class FetchResult:
    source_id: str
    fetched_at: str
    http_status: int
    ok: bool
    sha256: str | None
    bytes_len: int
    content_type: str
    elapsed_ms: int
    path: str | None
    note: str
    final_url: str = ""

    def as_row(self) -> dict:
        return asdict(self)


def _clean_session() -> requests.Session:
    s = requests.Session()
    s.trust_env = False          # ignore proxy and netrc credentials in the environment
    s.cookies.clear()
    s.auth = None
    s.headers.clear()
    s.headers.update({"User-Agent": USER_AGENT, "Accept": "*/*"})
    return s


def _assert_anonymous(headers: dict) -> None:
    present = {k.lower() for k in headers} & FORBIDDEN_HEADERS
    if present:
        raise CredentialLeak(
            f"refusing to send authentication: {sorted(present)}. "
            "Groundtruth only uses sources reachable without credentials."
        )


def payload_problem(body: bytes, content_type: str, expected: tuple[str, ...]) -> str | None:
    """Return why a 200 response is not usable data, or None if it is fine.

    The decisive test is content type, not page contents. A source that
    advertises JSON and answers with HTML is not serving data, whatever the
    HTML happens to say. This was learned the hard way: the energy certificate
    register answers 200, redirects to another host, and serves an ordinary
    GOV.UK landing page with a cookie banner -- no login form anywhere. A
    detector that looked for sign-in wording passed it straight through.
    """
    ct = content_type.split(";")[0].strip().lower()
    if not ct:
        return None                       # publisher declared nothing; accept
    if any(ct.startswith(e) for e in expected):
        return None
    head = body[:4000].lower()
    if any(m in head for m in LOGIN_MARKERS):
        return f"served {ct} with sign-in wording, expected {expected[0]}"
    return f"served {ct}, expected {expected[0]} -- not data"


def fetch(
    source: Source,
    dest_dir: Path,
    *,
    timeout: int = 120,
    max_bytes: int | None = None,
    url_override: str | None = None,
) -> FetchResult:
    """Retrieve a source anonymously, hashing as it streams.

    Never raises on an HTTP error: a failing source is a recorded fact, not a
    crash, because coverage figures depend on knowing what could not be reached.
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    url = url_override or source.url

    if source.blocked:
        return FetchResult(source.id, now, 0, False, None, 0, "", 0, None,
                           f"skipped: {source.blocked}", url)

    session = _clean_session()
    _assert_anonymous(session.headers)

    try:
        with session.get(url, stream=True, timeout=timeout,
                         allow_redirects=True) as r:
            _assert_anonymous(r.request.headers)
            ctype = r.headers.get("Content-Type", "")
            digest = hashlib.sha256()
            total = 0
            path = dest_dir / f"{source.id}.part"
            head = b""

            with open(path, "wb") as fh:
                for chunk in r.iter_content(chunk_size=1 << 20):
                    if not chunk:
                        continue
                    if len(head) < 4000:
                        head += chunk[:4000]
                    digest.update(chunk)
                    fh.write(chunk)
                    total += len(chunk)
                    if max_bytes and total >= max_bytes:
                        break

            elapsed = int((time.monotonic() - started) * 1000)

            if r.status_code != 200:
                path.unlink(missing_ok=True)
                return FetchResult(source.id, now, r.status_code, False, None,
                                   total, ctype, elapsed, None,
                                   f"HTTP {r.status_code} -- not admissible", r.url)

            problem = payload_problem(head, ctype, source.expect_content)
            if problem:
                path.unlink(missing_ok=True)
                host_note = ""
                if _host(r.url) != _host(url):
                    host_note = f" (redirected to {_host(r.url)})"
                return FetchResult(
                    source.id, now, 200, False, None, total, ctype, elapsed, None,
                    f"HTTP 200 but {problem}{host_note}", r.url,
                )

            final = dest_dir / f"{source.id}{_suffix(source.fmt)}"
            path.replace(final)
            return FetchResult(source.id, now, 200, True, digest.hexdigest(),
                               total, ctype, elapsed, str(final),
                               "truncated to max_bytes" if max_bytes and total >= max_bytes else "ok",
                               r.url)

    except requests.RequestException as exc:
        elapsed = int((time.monotonic() - started) * 1000)
        return FetchResult(source.id, now, 0, False, None, 0, "", elapsed, None,
                           f"transport error: {type(exc).__name__}: {exc}"[:300], url)


def _host(u: str) -> str:
    from urllib.parse import urlparse
    return urlparse(u).netloc


def _suffix(fmt: str) -> str:
    return {"csv": ".csv", "json": ".json", "geojson": ".geojson",
            "zip-csv": ".zip", "zip-shp": ".zip", "xml": ".xml"}.get(fmt, ".bin")
