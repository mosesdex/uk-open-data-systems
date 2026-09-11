"""What an operator needs to see.

The admin console previously showed invented throughput. Everything here is
read from the database or the filesystem, so a number on that screen can be
traced to a row somewhere. Where there is genuinely nothing to show, the
function returns an empty result and the interface says so.
"""
from __future__ import annotations

import json
from pathlib import Path

import duckdb

from . import sources as S

# Tables a system writes, used to report freshness and size per system.
SYSTEM_TABLES = {
    "catchment":  ["gold.catchment_district", "gold.catchment_school", "gold.catchment_specialist", "gold.catchment_district_trend", "gold.catchment_trend", "gold.catchment_trend_by_district"],
    "sentinel":   ["gold.sentinel_buyer", "gold.sentinel_method", "gold.sentinel_repeat", "gold.sentinel_control_footprint", "gold.sentinel_shared_control"],
    "highwater":  ["gold.highwater_outcome", "gold.highwater_trend", "gold.highwater_authority", "gold.highwater_district"],
    "plumbline":  ["gold.plumbline_quarter", "gold.plumbline_authority"],
    "junction":   ["gold.junction_register"],
    "ledger":     ["gold.ledger_authority", "gold.ledger_purpose", "gold.ledger_funding_status"],
    "bellwether": ["gold.bellwether_care", "gold.bellwether_group", "gold.bellwether_footprint", "gold.bellwether_district"],
    "sightline":  ["gold.sightline_reason", "gold.sightline_authority", "gold.sightline_wq_authority", "gold.sightline_wq_district", "gold.sightline_wq_theme"],
    "lastmile":   ["gold.lastmile_postcode", "gold.lastmile_authority"],
    "bulwark":    ["gold.bulwark_authority", "gold.bulwark_responsibility", "gold.bulwark_district"],
    "watchman":   ["gold.watchman_exposure", "gold.watchman_distress"],
    "compass":    ["gold.compass_series", "gold.compass_trend", "gold.compass_divergence", "gold.compass_cohort", "gold.compass_district"],
    "baseline":   ["gold.baseline_outlet", "gold.baseline_company", "gold.baseline_district", "gold.baseline_rainfall", "gold.baseline_trend"],
}

# Bronze files each system reads. Used to spot inputs that were fetched outside
# the registry, which gt fetch --all would not reproduce.
SYSTEM_INPUTS = {
    "catchment": ["gias_establishments.csv"],
    "compass": ["dfe_sen_provision.csv"],
    "bellwether": ["cqc_hsca_locations.ods"],
    "bulwark": ["ea_aims_defences.json"],
    "ledger": ["planning_developer_agreement_contribution.json",
               "planning_developer_agreement_transaction.json",
               "planning_local_authority.json"],
    "baseline": ["edm_annual.zip"],
    "sentinel": ["contracts_finder_bulk.json", "find_a_tender.json"],
    "watchman": ["gazette_insolvency_bulk.json", "contracts_finder_bulk.json"],
    "highwater": ["ea_objections.ods"],
    "sightline": ["ea_objections.ods"],
    "plumbline": ["planning_ps2.csv"],
    "lastmile": ["bduk_north_east.zip", "ppd_monthly.csv"],
}


def _rows(con, sql, params=None):
    cur = con.execute(sql, params or [])
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def _count(con, qualified: str) -> int | None:
    schema, table = qualified.split(".")
    exists = con.execute(
        "SELECT count(*) FROM information_schema.tables WHERE table_schema=? AND table_name=?",
        [schema, table]).fetchone()[0]
    if not exists:
        return None
    return con.execute(f"SELECT count(*) FROM {qualified}").fetchone()[0]


def runs(con: duckdb.DuckDBPyConnection, limit: int = 10) -> list[dict]:
    """Fetch runs, newest first. This is the real audit trail."""
    return _rows(con, f"""
        SELECT run_id,
               min(fetched_at)                          AS started,
               count(*)                                 AS sources,
               count(*) FILTER (WHERE ok)               AS succeeded,
               count(*) FILTER (WHERE NOT ok)           AS failed,
               sum(bytes_len)                           AS bytes,
               sum(elapsed_ms)                          AS elapsed_ms
        FROM bronze.fetch_log
        GROUP BY run_id ORDER BY started DESC LIMIT {limit}""")


# What a source's file is called on disk, where the id alone does not say.
DISK_ALIASES = {
    "bduk_premises": ["bduk_north_east.zip"],
    "cqc_hsca_locations": ["cqc_hsca_locations.ods"],
    "edm_annual_return": ["edm_annual.zip"],
    "ea_flood_objections": ["ea_objections.ods"],
    "hmlr_price_paid_monthly": ["ppd_monthly.csv"],
    "planning_developer_contributions": [
        "planning_developer_agreement_contribution.json"],
    "contracts_finder": ["contracts_finder_bulk.json", "contracts_finder.json"],
    "gazette_insolvency": ["gazette_insolvency_bulk.json", "gazette_insolvency.json"],
    "dfe_sen_provision": ["dfe_sen_provision.csv"],
    "planning_ps2": ["planning_ps2.csv"],
    # Written by `gt backfill` under their own names, or as several parts.
    "planning_developer_agreements": ["developer_agreements.json"],
    "ch_psc": ["psc-snapshot-*.zip"],
    "ea_rainfall_annual": ["rainfall_annual_*.json"],
}

# What each `gt backfill` step writes (see backfill.py), by filename pattern.
# Reproducible on another machine by that command rather than by `gt fetch`.
BACKFILL_OUTPUTS = {
    "bduk_*.zip": "bduk", "edm_annual_*.zip": "edm",
    "companies_house_bulk.zip": "companies", "rainfall_annual_*.json": "rainfall",
    "psc-snapshot-*.zip": "psc", "contracts_finder_bulk.json": "contracts",
    "gazette_insolvency_bulk.json": "gazette",
    "developer_agreements.json": "developer_agreements",
}


def _on_disk(bronze: Path, source_id: str) -> str | None:
    """The file this source's data is actually in, if any."""
    for name in DISK_ALIASES.get(source_id, []):
        # An alias can be a pattern: some sources arrive as several parts.
        if any(bronze.glob(name)):
            return name
    for suffix in (".csv", ".json", ".geojson", ".zip", ".ods", ".xml", ".bin"):
        p = bronze / f"{source_id}{suffix}"
        if p.exists():
            return p.name
    return None


def source_health(con: duckdb.DuckDBPyConnection,
                  bronze: Path | None = None) -> list[dict]:
    """Every registered source with its last recorded outcome.

    A source can hold usable data without a fetch-log entry, because some inputs
    were downloaded by hand during development. Reporting those as "never
    fetched" is wrong -- the data is there, it is the *provenance* that is
    missing, and that is a different and more precise problem.
    """
    rows = _rows(con, """
        WITH last AS (
          SELECT *, row_number() OVER (PARTITION BY source_id ORDER BY fetched_at DESC) rn
          FROM bronze.fetch_log)
        SELECT r.id, r.name, r.publisher, r.role, r.cadence, r.licence, r.systems,
               r.blocked,
               l.http_status, COALESCE(l.ok, FALSE) AS ok, l.bytes_len,
               l.elapsed_ms, l.fetched_at, l.sha256, l.note
        FROM bronze.source_registry r
        LEFT JOIN last l ON l.source_id = r.id AND l.rn = 1
        ORDER BY (l.fetched_at IS NULL) DESC, r.role, r.id""")
    # Who serves each source, by the audit's rule, so a page can say when a
    # figure rests on an intermediary rather than the publisher.
    from .audit import source_authority
    urls = {s.id: s.url for s in S.REGISTRY}
    for r in rows:
        r["authority"] = source_authority(urls.get(r["id"], ""))
    if bronze is not None:
        bronze = Path(bronze)
        for r in rows:
            disk = _on_disk(bronze, r["id"])
            r["disk_file"] = disk
            r["disk_bytes"] = sum(p.stat().st_size for p in bronze.glob(disk)) if disk else None
            if r["fetched_at"]:
                r["provenance"] = "logged"
            elif disk:
                r["provenance"] = "unlogged"      # present, but not via gt fetch
            else:
                r["provenance"] = "absent"
    return rows


def table_sizes(con: duckdb.DuckDBPyConnection) -> list[dict]:
    out = []
    for schema, table in con.execute("""
            SELECT table_schema, table_name FROM information_schema.tables
            WHERE table_schema IN ('bronze','silver','gold')
            ORDER BY table_schema, table_name""").fetchall():
        try:
            n = con.execute(f"SELECT count(*) FROM {schema}.{table}").fetchone()[0]
        except duckdb.Error:
            n = None
        out.append({"schema": schema, "table": table, "rows": n})
    return out


def system_state(con: duckdb.DuckDBPyConnection, bronze: Path) -> list[dict]:
    """Per-system: has it run, how much did it write, are its inputs present."""
    bronze = Path(bronze)
    out = []
    for sid, tables in SYSTEM_TABLES.items():
        counts = {t: _count(con, t) for t in tables}
        built = any(v is not None for v in counts.values())
        total = sum(v for v in counts.values() if v)
        inputs = SYSTEM_INPUTS.get(sid, [])
        missing = [f for f in inputs if not (bronze / f).exists()]
        present = [f for f in inputs if (bronze / f).exists()]
        out.append({
            "system": sid, "built": built, "rows": total,
            "tables": [{"table": t, "rows": v} for t, v in counts.items()],
            "inputs": inputs, "present_inputs": present, "missing_inputs": missing,
        })
    return sorted(out, key=lambda r: (not r["built"], r["system"]))


def registry_gaps(bronze: Path) -> dict:
    """Files on disk that no registered source would produce.

    These were fetched by hand during development. They work, but `gt fetch`
    will not reproduce them, so a rebuild on another machine would fail. Naming
    them is more useful than pretending the registry is complete.
    """
    bronze = Path(bronze)
    if not bronze.exists():
        return {"unregistered": [], "truncated": [], "registered_ids": 0}
    expected = set()
    for s in S.REGISTRY:
        for suffix in (".csv", ".json", ".geojson", ".zip", ".xml", ".ods", ".bin"):
            expected.add(s.id + suffix)
    on_disk = [p for p in bronze.iterdir() if p.is_file() and not p.name.startswith(".")]
    # A file a backfill step writes under its own name is reproducible, by
    # `gt backfill`. Counting those as hand-fetched put all 32 PSC parts and
    # every BDUK region on the list of files nothing produces.
    import fnmatch
    backfilled: dict[str, int] = {}
    unregistered = []
    for p in sorted(on_disk, key=lambda p: p.name):
        if p.name in expected:
            continue
        part = next((v for pat, v in BACKFILL_OUTPUTS.items() if fnmatch.fnmatch(p.name, pat)), None)
        if part:
            backfilled[part] = backfilled.get(part, 0) + 1
        else:
            unregistered.append(p.name)
    # 21 MB exactly is the --max-bytes cap used while disk was tight.
    truncated = sorted(p.name for p in on_disk
                       if p.suffix == ".zip" and 20_900_000 < p.stat().st_size < 21_100_000)
    return {"unregistered": unregistered, "truncated": truncated,
            "backfilled": backfilled,
            "registered_ids": len(S.REGISTRY),
            "catalogue": catalogue_audit(bronze)}


def catalogue_audit(bronze: Path) -> dict:
    """This registry measured against the catalogue government publishes.

    A platform that says what it uses, and never what it does not, is reporting
    its own successes. data.gov.uk is the list of everything on offer, so the
    honest denominator is available rather than assumed -- and the answer is
    unflattering by design: 44 registered sources against tens of thousands of
    published datasets.

    Nothing here is a join on dataset identity. The only match attempted is on
    publisher name, which is a small controlled vocabulary rather than the open
    set of organisation names that makes entity matching hazardous.
    """
    path = Path(bronze) / "data_gov_uk_ckan.json"
    if not path.exists():
        return {"available": False,
                "note": "catalogue not held -- run: gt backfill --only ckan"}
    try:
        doc = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError) as exc:
        return {"available": False, "note": f"catalogue unreadable: {exc}"}

    results = doc.get("results") or []
    published = doc.get("count")
    held = len(results)

    publishers: dict[str, int] = {}
    for d in results:
        title = ((d.get("organization") or {}).get("title") or "").strip()
        if title:
            publishers[title.casefold()] = publishers.get(title.casefold(), 0) + 1

    ours = {s.publisher.casefold() for s in S.REGISTRY if s.publisher}
    matched = sorted(p for p in ours if p in publishers)
    return {
        "available": True,
        "datasets_published": published,
        "datasets_held": held,
        # The catalogue reports its own total. Holding fewer than that is a
        # short read, and saying so beats quoting the smaller number as if it
        # were the catalogue.
        "complete": published is not None and held >= published,
        "short_by": (published - held) if (published is not None and held < published) else 0,
        "distinct_publishers": len(publishers),
        "registry_sources": len(S.REGISTRY),
        "publishers_we_read": len(ours),
        "publishers_found_in_catalogue": len(matched),
        "share_of_catalogue_used_pct": (
            round(100.0 * len(S.REGISTRY) / published, 4) if published else None),
    }


def review_queue(con: duckdb.DuckDBPyConnection, limit: int = 40) -> list[dict]:
    """Genuine ambiguity found in the data, not a mock-up.

    Two kinds, both real and both consequential:
      * one company number trading under several names -- resolving these is
        what changes a provider's apparent size
      * one name carrying several company numbers -- merging these would be a
        false merge, so they must never auto-accept
    """
    items: list[dict] = []

    if _count(con, "silver.care_location"):
        for r in _rows(con, f"""
                SELECT company_number,
                       count(DISTINCT provider) AS spellings,
                       sum(beds)                AS beds,
                       min(provider)            AS example_a,
                       max(provider)            AS example_b
                FROM silver.care_location
                WHERE company_number IS NOT NULL AND beds > 0
                GROUP BY company_number HAVING count(DISTINCT provider) > 1
                ORDER BY spellings DESC, beds DESC LIMIT {limit}"""):
            items.append({
                "kind": "one company, several names", "source": "CQC care locations",
                "key": r["company_number"],
                "left": r["example_a"], "right": r["example_b"],
                "weight": r["beds"], "variants": r["spellings"],
                "note": f"{r['spellings']} spellings, {r['beds']:,} beds — merging these "
                        f"changes the provider's apparent size",
                "action": "merge under the company number",
            })

    if _count(con, "silver.supplier_register"):
        for r in _rows(con, f"""
                SELECT name_key, count(DISTINCT company_number) AS numbers,
                       min(name) AS example_a, max(name) AS example_b,
                       count(*) AS awards
                FROM silver.supplier_register
                WHERE company_number IS NOT NULL
                GROUP BY name_key HAVING count(DISTINCT company_number) > 1
                ORDER BY numbers DESC LIMIT {limit}"""):
            items.append({
                "kind": "one name, several companies", "source": "procurement register",
                "key": r["name_key"],
                "left": r["example_a"], "right": r["example_b"],
                "weight": r["awards"], "variants": r["numbers"],
                "note": f"{r['numbers']} distinct company numbers share this name — "
                        f"merging them would be a false merge",
                "action": "keep separate",
            })

    return items


def build(con: duckdb.DuckDBPyConnection, bronze: Path) -> dict:
    return {
        "runs": runs(con),
        "sources": source_health(con, bronze),
        "tables": table_sizes(con),
        "systems": system_state(con, bronze),
        "registry": registry_gaps(bronze),
        "review": review_queue(con),
    }
