"""Late-binding URL resolution.

Some publishers version their filenames. Ordnance Survey splits Linked
Identifiers into one file per identifier pair, each stamped with the month
(lids-2026-08_csv_BLPU-UPRN-Street-USRN.zip). Hardcoding that would break at
the next release, so the exact file is resolved at fetch time from the
product's own download listing.
"""
from __future__ import annotations

from datetime import date

import requests

from .sources import Source

OS_PRODUCT_DOWNLOADS = "https://api.os.uk/downloads/v1/products/{p}/downloads"


class ResolutionError(RuntimeError):
    """Raised when a source's concrete URL cannot be determined."""


def _session() -> requests.Session:
    s = requests.Session()
    s.trust_env = False
    s.headers.update({"User-Agent": "groundtruth/0.1", "Accept": "application/json"})
    return s


def os_download_url(product: str, pattern: str, *, timeout: int = 60) -> str:
    """Find the download whose filename contains `pattern`, for this release."""
    r = _session().get(OS_PRODUCT_DOWNLOADS.format(p=product), timeout=timeout)
    r.raise_for_status()
    items = r.json()
    matches = [i for i in items if pattern.lower() in i.get("url", "").lower()]
    if not matches:
        available = sorted({
            i.get("url", "").split("fileName=")[-1] for i in items if "fileName=" in i.get("url", "")
        })
        raise ResolutionError(
            f"no {product} download matching {pattern!r}. Available: {available[:10]}"
        )
    # Smallest match: these files are alternate encodings of the same content.
    return min(matches, key=lambda i: i.get("size", 1 << 62))["url"]


def resolve(source: Source, *, timeout: int = 60) -> str:
    """Return the concrete URL to fetch for this source, today."""
    url = source.url
    if "{date}" in url:
        url = url.replace("{date}", date.today().strftime("%Y%m%d"))
    if source.os_product and source.os_file_pattern:
        return os_download_url(source.os_product, source.os_file_pattern, timeout=timeout)
    return url
