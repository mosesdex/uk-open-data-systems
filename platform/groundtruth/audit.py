"""Data integrity audit.

Everything else in this platform checks one thing well. This runs the checks a
reader would run if they did not trust us, all of them, and reports what fails.

The audit is deliberately mechanical. A prose assurance that "sources were
verified" ages badly and cannot be re-run; a check that fails loudly next
quarter when a publisher changes a column is worth more than a paragraph. So
every finding here is produced by code that can be run again, and the audit
reports its own coverage: how many of the platform's claims it was actually able
to test.

Findings carry a severity, and the severities mean specific things:

  critical  a published figure is wrong, or rests on a source that is not what
            the registry says it is
  major     a figure cannot be reproduced or verified from what is stored
  minor     a discrepancy that does not change a published number
  note      something a reader should know that is not a defect

An audit that finds nothing is not a passing audit -- it is an audit that did
not look. Coverage is therefore reported alongside the findings.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

import duckdb

CRITICAL, MAJOR, MINOR, NOTE = "critical", "major", "minor", "note"
_ORDER = {CRITICAL: 0, MAJOR: 1, MINOR: 2, NOTE: 3}


@dataclass
class Finding:
    check: str
    severity: str
    subject: str
    summary: str
    evidence: str = ""
    remedy: str = ""

    def as_dict(self) -> dict:
        return {"check": self.check, "severity": self.severity,
                "subject": self.subject, "summary": self.summary,
                "evidence": self.evidence, "remedy": self.remedy}


@dataclass
class Audit:
    findings: list[Finding] = field(default_factory=list)
    checks_run: list[str] = field(default_factory=list)
    checks_skipped: list[dict] = field(default_factory=list)

    def add(self, *a, **kw) -> None:
        self.findings.append(Finding(*a, **kw))

    def skip(self, check: str, reason: str) -> None:
        self.checks_skipped.append({"check": check, "reason": reason})

    def summary(self) -> dict:
        by = {}
        for f in self.findings:
            by[f.severity] = by.get(f.severity, 0) + 1
        return {
            "checks_run": len(self.checks_run),
            "checks_skipped": len(self.checks_skipped),
            "findings": len(self.findings),
            "by_severity": by,
            "critical": by.get(CRITICAL, 0),
            "major": by.get(MAJOR, 0),
        }

    def sorted(self) -> list[Finding]:
        return sorted(self.findings, key=lambda f: (_ORDER[f.severity], f.check))


def _exists(con, qualified: str) -> bool:
    schema, _, table = qualified.partition(".")
    return con.execute(
        "SELECT count(*) FROM information_schema.tables "
        "WHERE table_schema = ? AND table_name = ?", [schema, table]).fetchone()[0] > 0


def _cols(con, qualified: str) -> list[str]:
    schema, _, table = qualified.partition(".")
    return [r[0] for r in con.execute(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_schema = ? AND table_name = ? ORDER BY ordinal_position",
        [schema, table]).fetchall()]


# --------------------------------------------------------------- source layer

def check_registry_vs_log(con, a: Audit) -> None:
    """Does every admissible source actually have data behind it?

    A source in the registry with no successful fetch is not a source, it is an
    intention. The registry is what the site publishes as the platform's
    evidence base, so the gap between the two is a published overclaim.
    """
    a.checks_run.append("registry-vs-log")
    from . import sources as S
    if not _exists(con, "bronze.fetch_log"):
        a.skip("registry-vs-log", "bronze.fetch_log absent")
        return
    ok_ids = {r[0] for r in con.execute(
        "SELECT DISTINCT source_id FROM bronze.fetch_log WHERE ok").fetchall()}
    # A source retrieved by a backfill step has data in the database but no row
    # in the fetch log, because the backfill functions write files directly.
    # That is a provenance hole rather than a missing source, and the two must
    # not be reported as the same thing: one is "we do not have this", the other
    # is "we have it and cannot say when or from what".
    unlogged, absent = [], []
    for src in S.REGISTRY:
        if src.blocked or src.id in ok_ids:
            continue
        (unlogged if src.needs_backfill else absent).append(src)

    for src in absent:
        a.add("registry-vs-log", MAJOR, src.id,
              "registered as admissible but has no successful fetch on record",
              evidence=f"no bronze.fetch_log row with ok=true for {src.id}",
              remedy=f"fetch it, or mark it blocked with a reason: {src.url}")
    if unlogged:
        a.add("registry-vs-log", MAJOR, "bronze.fetch_log",
              f"{len(unlogged)} backfilled sources have data but no retrieval record",
              evidence="unlogged: " + ", ".join(s.id for s in unlogged),
              remedy="backfill steps should call store.record_fetch() like fetch() "
                     "does, so every byte in the database carries a timestamp, an "
                     "HTTP status and a checksum")


def check_freshness(con, a: Audit, stale_days: int = 120) -> None:
    """How old is the newest successful fetch, per source?

    Cadence is declared in the registry, so a daily source last retrieved months
    ago is publishing figures the site describes as current.
    """
    a.checks_run.append("freshness")
    if not _exists(con, "bronze.fetch_log"):
        a.skip("freshness", "bronze.fetch_log absent")
        return
    from . import sources as S
    cadence_days = {"daily": 1, "weekly": 7, "monthly": 31, "quarterly": 92,
                    "annual": 366, "annually": 366, "yearly": 366}
    rows = con.execute("""
        SELECT source_id, max(fetched_at) FROM bronze.fetch_log
        WHERE ok GROUP BY 1""").fetchall()
    latest = {r[0]: r[1] for r in rows}
    now = datetime.now(timezone.utc)
    for src in S.REGISTRY:
        when = latest.get(src.id)
        if when is None:
            continue
        if when.tzinfo is None:
            when = when.replace(tzinfo=timezone.utc)
        age = (now - when).days
        expected = cadence_days.get(src.cadence.lower().split()[0], 366)
        if age > max(stale_days, expected * 4):
            a.add("freshness", MAJOR if age > 365 else MINOR, src.id,
                  f"last successful fetch was {age} days ago, cadence is {src.cadence}",
                  evidence=f"newest ok fetch {when:%Y-%m-%d}",
                  remedy="re-fetch before publishing figures described as current")


def check_content_traps(con, a: Audit) -> None:
    """Did any stored fetch return the wrong kind of content?

    The energy certificate register returns a sign-in page with HTTP 200. The
    fetch layer refuses those, but a source whose declared content type never
    matched what arrived should be visible here rather than only in a log.
    """
    a.checks_run.append("content-traps")
    if not _exists(con, "bronze.fetch_log"):
        a.skip("content-traps", "bronze.fetch_log absent")
        return
    from . import sources as S
    expected = {s.id: tuple(x.lower() for x in s.expect_content) for s in S.REGISTRY}
    rows = con.execute("""
        SELECT source_id, http_status, content_type, note, bytes_len
        FROM bronze.fetch_log
        WHERE ok AND content_type IS NOT NULL
          AND (lower(content_type) LIKE '%html%' OR bytes_len < 1024)""").fetchall()
    for sid, status, ctype, note, size in rows:
        want = expected.get(sid, ())
        # An index page that the registry declares as HTML is not a trap: some
        # publishers list their real files on a page that must be parsed first.
        # Flagging those was this check's own first false positive.
        if any(w in (ctype or "").lower() for w in want):
            continue
        a.add("content-traps", CRITICAL, sid,
              "a fetch recorded as successful returned content the registry did not expect",
              evidence=f"status={status} content_type={ctype} expected={want} bytes={size}",
              remedy="a 200 is not data; treat this source as blocked until it serves the dataset")


# ---------------------------------------------------------------- table layer

def check_orphan_tables(con, a: Audit) -> None:
    """Tables holding nothing.

    An empty gold table is published as a system with no output. That is honest
    only if the system is reported as absent rather than as zero.
    """
    a.checks_run.append("empty-tables")
    for schema in ("silver", "gold"):
        for (t,) in con.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = ? ORDER BY 1", [schema]).fetchall():
            n = con.execute(f'SELECT count(*) FROM "{schema}"."{t}"').fetchone()[0]
            if n == 0:
                a.add("empty-tables", MINOR, f"{schema}.{t}",
                      "table exists but holds no rows",
                      evidence="row count 0",
                      remedy="publish the system as absent, not as zero")


def check_duplicates(con, a: Audit) -> None:
    """Keys that should be unique and are not.

    A duplicated key silently multiplies every downstream aggregate it joins
    into, which is the failure mode least likely to look wrong on a chart.
    """
    a.checks_run.append("duplicate-keys")
    candidates = [
        ("silver.place_postcode", "postcode"),
        ("silver.place_uprn", "uprn"),
        ("silver.contribution", "reference"),
        ("silver.developer_agreement", "reference"),
        ("silver.company", "company_number"),
        ("gold.catchment_school", "urn"),
        ("gold.catchment_district", "lad_code"),
        ("gold.lastmile_authority", "lad_code"),
        ("gold.entity", "company_number"),
    ]
    for table, key in candidates:
        if not _exists(con, table) or key not in _cols(con, table):
            continue
        dupes, worst = con.execute(f"""
            SELECT count(*), max(n) FROM (
              SELECT "{key}" AS k, count(*) AS n FROM {table}
              WHERE "{key}" IS NOT NULL GROUP BY 1 HAVING count(*) > 1)""").fetchone()
        if dupes:
            a.add("duplicate-keys",
                  MAJOR if table.startswith("gold.") else MINOR,
                  f"{table}.{key}",
                  f"{dupes:,} duplicated keys, worst repeated {worst} times",
                  evidence=f"SELECT {key}, count(*) FROM {table} GROUP BY 1 HAVING count(*) > 1",
                  remedy="deduplicate at load, or state why the key is not unique")


def check_null_keys(con, a: Audit) -> None:
    """Join keys that are absent on rows that need them."""
    a.checks_run.append("null-join-keys")
    candidates = [
        ("gold.catchment_school", "lad_code", MAJOR),
        ("gold.catchment_district", "lad_code", MAJOR),
        ("silver.place_postcode", "lad_code", MAJOR),
        ("silver.procurement_award", "company_number", NOTE),
        ("silver.care_location", "company_number", NOTE),
        ("silver.contribution", "agreement", MINOR),
    ]
    for table, key, sev in candidates:
        if not _exists(con, table) or key not in _cols(con, table):
            continue
        total, missing = con.execute(
            f'SELECT count(*), count(*) - count("{key}") FROM {table}').fetchone()
        if missing and total:
            pct = round(100.0 * missing / total, 2)
            a.add("null-join-keys", sev, f"{table}.{key}",
                  f"{missing:,} of {total:,} rows ({pct}%) carry no {key}",
                  evidence=f"these rows cannot participate in any join on {key}",
                  remedy="report the unjoinable share alongside any figure computed over this table")


# ------------------------------------------------------------- geography/scope

def check_geographic_scope(con, a: Audit) -> None:
    """Is the platform's stated scope the scope of its data?

    Code-Point Open is Great Britain. Any figure described as UK-wide that rests
    on it is wrong by the population of Northern Ireland.
    """
    a.checks_run.append("geographic-scope")
    if not _exists(con, "silver.place_postcode"):
        a.skip("geographic-scope", "place spine not loaded")
        return
    cols = _cols(con, "silver.place_postcode")
    if "country_code" not in cols:
        a.skip("geographic-scope", "no country_code on the postcode table")
        return
    rows = con.execute("""
        SELECT country_code, count(*) FROM silver.place_postcode
        GROUP BY 1 ORDER BY 2 DESC""").fetchall()
    countries = {r[0]: r[1] for r in rows}
    ni = sum(v for k, v in countries.items() if k and k.startswith("N"))
    if ni == 0:
        a.add("geographic-scope", NOTE, "silver.place_postcode",
              "the place spine holds zero Northern Ireland postcodes",
              evidence=f"country codes present: {', '.join(sorted(str(k) for k in countries))}",
              remedy="every coverage figure derived from this spine must say GB, not UK")


def check_date_ranges(con, a: Audit) -> None:
    """What period does each dataset actually cover?

    A figure presented as current over a corpus that stops three years ago is
    not wrong so much as undated, and undated is how a stale number survives.
    """
    a.checks_run.append("date-ranges")
    candidates = [
        ("silver.procurement_award", "award_date"),
        ("silver.contribution", "start_date"),
        ("silver.developer_agreement", "reference"),
        ("silver.flood_objection", "year"),
        ("gold.compass_series", "year"),
        ("gold.baseline_outlet", "year"),
        ("gold.catchment_trend", "year_label"),
    ]
    for table, col in candidates:
        if not _exists(con, table) or col not in _cols(con, table):
            continue
        try:
            lo, hi, n = con.execute(
                f'SELECT min("{col}"), max("{col}"), count("{col}") FROM {table}').fetchone()
        except duckdb.Error:
            continue
        if n:
            a.add("date-ranges", NOTE, f"{table}.{col}",
                  f"covers {lo} to {hi} over {n:,} rows",
                  evidence="stated so a reader can judge whether a figure is current",
                  remedy="publish the period alongside any figure computed from it")


# ------------------------------------------------------------- match quality

def check_match_quality(con, a: Audit) -> None:
    """How much of each spine actually resolved?

    The platform's claim is that it makes two joins possible. The share of rows
    those joins reach is the measure of that claim, and a low share is a finding
    rather than a detail.
    """
    a.checks_run.append("match-quality")
    checks = [
        ("entity spine into procurement", "silver.procurement_award",
         "company_number", 50.0),
        ("entity spine into care", "silver.care_location", "company_number", 50.0),
        ("place spine into schools", "gold.catchment_school", "lad_code", 90.0),
    ]
    for label, table, col, expect in checks:
        if not _exists(con, table) or col not in _cols(con, table):
            continue
        total, resolved = con.execute(
            f'SELECT count(*), count("{col}") FROM {table}').fetchone()
        if not total:
            continue
        pct = round(100.0 * resolved / total, 2)
        if pct < expect:
            a.add("match-quality", MAJOR, f"{table}.{col}",
                  f"{label} resolves {pct}% of rows, below the {expect}% this "
                  f"system's figures assume",
                  evidence=f"{resolved:,} of {total:,} rows carry {col}",
                  remedy="publish the resolved share with every statistic computed over it")
        else:
            a.add("match-quality", NOTE, f"{table}.{col}",
                  f"{label} resolves {pct}% of rows",
                  evidence=f"{resolved:,} of {total:,}")


def check_ambiguity(con, a: Audit) -> None:
    """Names that match more than one registered body.

    The entity spine reports these rather than resolving them. The count is a
    ceiling on how much of the corpus can ever be joined by name.
    """
    a.checks_run.append("name-ambiguity")
    if not _exists(con, "silver.company_key"):
        a.skip("name-ambiguity", "silver.company_key absent")
        return
    try:
        from . import entity as E
        stats = E.register_stats(con)
    except Exception as exc:
        a.skip("name-ambiguity", f"register_stats failed: {str(exc).splitlines()[0]}")
        return
    pct = stats.get("ambiguous_pct")
    if pct:
        a.add("name-ambiguity", NOTE, "silver.company_key",
              f"{pct}% of distinct company names are shared by more than one company",
              evidence=f"{stats.get('ambiguous_names'):,} of {stats.get('distinct_names'):,} names",
              remedy="any name-only match against these is unresolvable by construction")


# ------------------------------------------------------- published vs derived

def check_published_payload(con, a: Audit, payload_path=None) -> None:
    """Does the published payload agree with the database it claims to describe?

    The site is static JSON. If it was written from an older run, every figure a
    reader sees is a figure this database no longer holds.
    """
    a.checks_run.append("payload-agreement")
    import json
    from pathlib import Path
    payload_path = Path(payload_path or (
        Path(__file__).resolve().parent.parent.parent / "app" / "data" / "platform.json"))
    if not payload_path.exists():
        a.skip("payload-agreement", f"no payload at {payload_path}")
        return
    d = json.loads(payload_path.read_text())
    built = d.get("built_systems") or []
    generated = d.get("generated")

    if _exists(con, "bronze.fetch_log"):
        newest = con.execute(
            "SELECT max(fetched_at) FROM bronze.fetch_log WHERE ok").fetchone()[0]
        if newest and generated:
            gen = datetime.fromisoformat(generated)
            if newest.tzinfo is None:
                newest = newest.replace(tzinfo=timezone.utc)
            if newest > gen:
                a.add("payload-agreement", MAJOR, "app/data/platform.json",
                      "data has been fetched since the payload was generated",
                      evidence=f"payload generated {generated}, newest fetch {newest}",
                      remedy="republish: gt run, or publish.write()")

    # Every system the payload claims is built should have rows behind it.
    from . import admin as _admin
    for system in built:
        tables = _admin.SYSTEM_TABLES.get(system, [])
        if not tables:
            continue
        present = [t for t in tables if _exists(con, t)]
        if not present:
            a.add("payload-agreement", CRITICAL, system,
                  "published as a built system but none of its tables exist",
                  evidence=f"expected one of {', '.join(tables)}",
                  remedy="rebuild the system or remove it from built_systems")
            continue
        total = sum(con.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
                    for t in present)
        if total == 0:
            a.add("payload-agreement", MAJOR, system,
                  "published as a built system but its tables are empty",
                  evidence=f"{', '.join(present)} hold 0 rows",
                  remedy="publish as absent rather than as a system with no output")


def check_provenance_coverage(con, a: Audit) -> None:
    """How much of what is published can name where it came from?"""
    a.checks_run.append("provenance-coverage")
    if not _exists(con, "evidence.observation"):
        a.add("provenance-coverage", MAJOR, "evidence.observation",
              "no observation-level provenance has been recorded",
              evidence="the evidence table is absent or empty",
              remedy="systems should record through provenance.record() so a "
                     "figure can be traced to a source record")
        return
    n = con.execute("SELECT count(*) FROM evidence.observation").fetchone()[0]
    if n == 0:
        a.add("provenance-coverage", MAJOR, "evidence.observation",
              "the evidence table exists but holds no observations",
              remedy="wire provenance.record() into each system's build step")


# ------------------------------------------------------------- live publisher

# Hosts that are the publisher's own delivery infrastructure even though the
# domain is not a government one. Each is here because it was checked, not
# because the name looked plausible: ONS publishes boundaries through ArcGIS
# Online, HM Land Registry through its own S3 bucket, the Charity Commission
# through Azure blob storage, DfE through an Azure web app, and each DNO through
# its own OpenDataSoft portal. A host not on this list and not a government
# domain is a third-party intermediary and is reported as one.
DELEGATED_HOSTS = (
    "services1.arcgis.com",                      # ONS Open Geography Portal
    "prod.publicdata.landregistry.gov.uk.s3-website-eu-west-1.amazonaws.com",
    "ccewuksprdoneregsadata1.blob.core.windows.net",   # Charity Commission
    "ea-edubase-api-prod.azurewebsites.net",     # DfE, GIAS
    "www.nomisweb.co.uk",                        # ONS labour market service
    "ukpowernetworks.opendatasoft.com",
    "northernpowergrid.opendatasoft.com",
    "electricitynorthwest.opendatasoft.com",
    "spenergynetworks.opendatasoft.com",
)

GOV_SUFFIXES = (".gov.uk", ".gov.scot", ".gov.wales", ".nhs.uk",
                "thegazette.co.uk", "api.os.uk", "cqc.org.uk")


def check_source_authority(con, a: Audit) -> None:
    """Is each source served by the body that publishes it?

    Anonymity is the platform's stated access rule, and it is not the same as
    authority. A dataset can be perfectly open and still come from someone other
    than the publisher, which changes what a figure derived from it can claim.
    """
    a.checks_run.append("source-authority")
    import urllib.parse
    from . import sources as S
    for src in S.REGISTRY:
        host = urllib.parse.urlparse(src.url).netloc.lower()
        if host in DELEGATED_HOSTS or any(host.endswith(s) for s in GOV_SUFFIXES):
            continue
        a.add("source-authority", MAJOR if not src.blocked else NOTE, src.id,
              "served by a third party rather than the publishing body",
              evidence=f"host {host}",
              remedy="label figures derived from this as coming from an "
                     "aggregator, or replace it with the publisher's own feed")


def check_live_sources(con, a: Audit, timeout: int = 45) -> None:
    """Does every admissible source still serve data to an anonymous request?

    This is the platform's headline claim, and it is the one most likely to stop
    being true without anyone noticing: publishers add bot protection, rotate
    filenames and retire endpoints without a changelog. Run over the network, so
    it is separated from the checks that read only the database.
    """
    a.checks_run.append("live-sources")
    import requests
    from . import sources as S
    from .resolve import resolve, ResolutionError
    for src in S.REGISTRY:
        if src.blocked:
            continue
        try:
            url = resolve(src)
        except (ResolutionError, requests.RequestException) as exc:
            a.add("live-sources", MAJOR, src.id,
                  "URL cannot be resolved for today",
                  evidence=str(exc).splitlines()[0][:160],
                  remedy="the registry URL is a template or a listing that no longer resolves")
            continue
        try:
            r = requests.get(url, timeout=timeout, stream=True,
                             headers={"User-Agent": "groundtruth/0.1"})
            status, ctype = r.status_code, (r.headers.get("content-type") or "").split(";")[0]
            r.close()
        except requests.RequestException as exc:
            a.add("live-sources", MAJOR, src.id,
                  "does not respond",
                  evidence=f"{type(exc).__name__} on {url[:100]}",
                  remedy="confirm the endpoint has not been retired, then block it with a reason")
            continue
        if status != 200:
            a.add("live-sources", CRITICAL if status in (401, 403) else MAJOR, src.id,
                  f"no longer serves data anonymously: HTTP {status}",
                  evidence=f"{status} from {url[:100]}",
                  remedy="the access standard is that an anonymous request returns "
                         "data; this source no longer meets it and must be blocked "
                         "with a reason rather than left listed as admissible")
            continue
        want = tuple(x.lower() for x in src.expect_content)
        if not ctype:
            # No content-type header at all. Not proof of bad content, but it
            # means the header cannot be used to verify the payload, so the
            # body has to be sniffed before loading.
            a.add("live-sources", MINOR, src.id,
                  "serves 200 with no content-type header",
                  evidence=f"no content-type from {url[:100]}",
                  remedy="verify this payload by sniffing the body; the header "
                         "cannot confirm it")
        elif want and not any(w in ctype.lower() for w in want):
            a.add("live-sources", CRITICAL, src.id,
                  "returns 200 with content the registry does not expect",
                  evidence=f"got {ctype}, expected one of {want}",
                  remedy="a 200 is not data; verify before loading")


NETWORK_CHECKS = (check_live_sources,)


CHECKS = (
    check_registry_vs_log, check_freshness, check_content_traps,
    check_source_authority,
    check_orphan_tables, check_duplicates, check_null_keys,
    check_geographic_scope, check_date_ranges,
    check_match_quality, check_ambiguity,
    check_published_payload, check_provenance_coverage,
)


def run(con: duckdb.DuckDBPyConnection, *, network: bool = False) -> Audit:
    """Run the audit. ``network`` adds the checks that contact publishers."""
    a = Audit()
    for check in CHECKS + (NETWORK_CHECKS if network else ()):
        try:
            check(con, a)
        except Exception as exc:                # a failing check is a finding
            a.add(check.__name__, MAJOR, "audit",
                  f"the check itself failed: {str(exc).splitlines()[0]}",
                  remedy="an audit that cannot run is not a passing audit")
    return a
