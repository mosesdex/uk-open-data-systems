"""Publishing gold tables as static JSON for the prototype.

The prototype has been running on figures pasted in by hand. This turns it into
a view of what the platform actually computed: every number it shows comes from
a gold table, with the run that produced it stamped alongside.

Nothing here reshapes or rounds a figure to make it look better. If a system
produced no output, it is published as absent rather than omitted, because a
missing panel is honest and a stale one is not.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import duckdb

from . import place


def _exists(con: duckdb.DuckDBPyConnection, schema: str, table: str) -> bool:
    return con.execute(
        "SELECT count(*) FROM information_schema.tables "
        "WHERE table_schema = ? AND table_name = ?", [schema, table]).fetchone()[0] > 0


def _rows(con, sql: str, params=None) -> list[dict]:
    cur = con.execute(sql, params or [])
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def _one(con, sql: str):
    r = con.execute(sql).fetchone()
    return r if r else None


def build_payload(con: duckdb.DuckDBPyConnection) -> dict:
    generated = datetime.now(timezone.utc).isoformat(timespec="seconds")
    out: dict = {"generated": generated, "systems": {}, "spine": {}, "sources": {}}

    # ---- spine ----
    cov = place.coverage(con)
    out["spine"]["place"] = cov.get("tiers", {})
    if _exists(con, "silver", "supplier_register"):
        n, names, nums = _one(con, """SELECT count(*), count(DISTINCT name_key),
            count(DISTINCT company_number) FROM silver.supplier_register""")
        out["spine"]["entity"] = {"register_rows": n, "distinct_names": names,
                                  "distinct_numbers": nums or 0}

    # ---- sources ----
    if _exists(con, "bronze", "fetch_log"):
        out["sources"]["status"] = _rows(con, """
            WITH last AS (SELECT *, row_number() OVER (PARTITION BY source_id
                          ORDER BY fetched_at DESC) rn FROM bronze.fetch_log)
            SELECT r.id, r.name, r.publisher, r.role, r.cadence,
                   COALESCE(l.http_status, 0) AS http_status,
                   COALESCE(l.ok, FALSE) AS ok, l.bytes_len, r.blocked
            FROM bronze.source_registry r
            LEFT JOIN last l ON l.source_id = r.id AND l.rn = 1
            ORDER BY r.role, r.id""")

    # ---- systems ----
    S = out["systems"]

    if _exists(con, "gold", "catchment_district"):
        S["catchment"] = {
            "national": _rows(con, """SELECT count(*) AS districts, sum(pupils) AS pupils,
                sum(capacity) AS capacity,
                round(100.0*sum(pupils)/nullif(sum(capacity),0),1) AS utilisation_pct
                FROM gold.catchment_district""")[0],
            "specialist": _rows(con, """SELECT count(*) AS districts, sum(pupils) AS pupils,
                sum(capacity) AS capacity,
                round(100.0*sum(pupils)/nullif(sum(capacity),0),1) AS utilisation_pct,
                sum(over_capacity) AS over_capacity FROM gold.catchment_specialist""")[0],
            "by_district": _rows(con, """SELECT lad_code, lad_name, schools, pupils,
                capacity, utilisation_pct, measured_pct, entity_resolved_pct
                FROM gold.catchment_district WHERE lad_code IS NOT NULL"""),
        }

    if _exists(con, "gold", "bulwark_authority"):
        S["bulwark"] = {
            "coverage": _rows(con, """SELECT count(*) AS assets,
                count(*) FILTER (WHERE maintainer IS NOT NULL AND maintainer <> 'Unknown') AS maintainer_known,
                count(*) FILTER (WHERE owner IS NOT NULL AND owner <> 'Unknown') AS owner_known,
                count(*) FILTER (WHERE current_condition IN ('1','2','3','4','5')) AS graded,
                count(*) FILTER (WHERE next_inspection IS NOT NULL AND next_inspection < CURRENT_DATE) AS overdue
                FROM silver.flood_defence""")[0],
            "by_maintainer": _rows(con, "SELECT * FROM gold.bulwark_responsibility LIMIT 8"),
        }

    if _exists(con, "gold", "ledger_funding_status"):
        total, with_amount, rows = _one(con, """SELECT round(sum(amount)), count(amount),
            count(*) FROM silver.contribution""")
        S["ledger"] = {
            "total": total, "with_amount": with_amount, "contributions": rows,
            "located": _one(con, "SELECT count(*) FILTER (WHERE has_geometry) FROM silver.contribution")[0],
            "status": _rows(con, "SELECT * FROM gold.ledger_funding_status LIMIT 8"),
            "purpose": _rows(con, "SELECT * FROM gold.ledger_purpose LIMIT 8"),
        }

    if _exists(con, "gold", "bellwether_group"):
        S["bellwether"] = {
            "systemic": _rows(con, """SELECT brand, count(DISTINCT local_authority) AS authorities,
                count(DISTINCT company_number) AS companies, count(*) AS locations, sum(beds) AS beds
                FROM silver.care_location WHERE beds > 0 AND brand NOT IN ('-','')
                GROUP BY brand ORDER BY beds DESC LIMIT 10"""),
            "top_share": _rows(con, """SELECT local_authority, group_name, beds, la_beds, share_pct
                FROM gold.bellwether_group WHERE la_beds >= 300
                ORDER BY share_pct DESC LIMIT 10"""),
        }

    if _exists(con, "gold", "baseline_company"):
        S["baseline"] = {
            "national": _rows(con, """SELECT round(sum(spills)) AS reported,
                round(sum(spills_full_year_equivalent)) AS adjusted,
                round(avg(operational_pct),1) AS mean_uptime,
                count(*) AS outlets FROM gold.baseline_outlet""")[0],
            "by_company": _rows(con, "SELECT * FROM gold.baseline_company LIMIT 12"),
        }

    if _exists(con, "gold", "highwater_trend"):
        S["highwater"] = {
            "outcomes": _rows(con, "SELECT * FROM gold.highwater_outcome"),
            "trend": _rows(con, "SELECT * FROM gold.highwater_trend ORDER BY year"),
        }

    if _exists(con, "gold", "plumbline_quarter"):
        from .systems import plumbline as P
        h, st, md, dd = P.national_gap(con, since="2023")
        S["plumbline"] = {
            "headline_pct": h, "statutory_pct": st,
            "major_decisions": md, "dwelling_decisions": dd,
            "worst": _rows(con, "SELECT * FROM gold.plumbline_authority LIMIT 10"),
        }

    if _exists(con, "gold", "sentinel_method"):
        S["sentinel"] = {
            "method": _rows(con, "SELECT * FROM gold.sentinel_method"),
            "concentrated": _rows(con, """SELECT * FROM gold.sentinel_buyer
                WHERE awards >= 5 ORDER BY top_supplier_award_share DESC LIMIT 10"""),
        }

    if _exists(con, "gold", "junction_register"):
        S["junction"] = {"registers": _rows(con, "SELECT * FROM gold.junction_register")}

    if _exists(con, "gold", "compass_trend"):
        S["compass"] = {
            "national": _rows(con, """SELECT provision, sum(pupils) FILTER (WHERE year = (SELECT min(year) FROM gold.compass_series)) AS earliest,
                sum(pupils) FILTER (WHERE year = (SELECT max(year) FROM gold.compass_series)) AS latest
                FROM gold.compass_series GROUP BY provision"""),
            "rising": _rows(con, """SELECT la_name, pupils_per_year, projected_change_3yr,
                projected_change_pct FROM gold.compass_trend
                WHERE provision = 'Education, health and care plan'
                ORDER BY projected_change_pct DESC LIMIT 10"""),
            "divergence": _rows(con, "SELECT * FROM gold.compass_divergence LIMIT 10"),
        }

    if _exists(con, "gold", "lastmile_authority"):
        from .systems import lastmile as LM
        nb_p, nb_g, nb_pct, ot_p, ot_pct = LM.comparison(con)
        S["lastmile"] = {"new_build_pct": nb_pct, "other_pct": ot_pct,
                         "new_build_premises": nb_p, "other_premises": ot_p,
                         "by_authority": _rows(con, "SELECT * FROM gold.lastmile_authority LIMIT 12")}

    if _exists(con, "gold", "sightline_reason"):
        S["sightline"] = {"reasons": _rows(con, "SELECT * FROM gold.sightline_reason LIMIT 10")}

    if _exists(con, "gold", "watchman_exposure"):
        S["watchman"] = {"exposures": _rows(con, "SELECT * FROM gold.watchman_exposure LIMIT 20")}

    out["built_systems"] = sorted(S)
    return out


def write(con: duckdb.DuckDBPyConnection, dest: Path) -> dict:
    payload = build_payload(con)
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(payload, default=str, separators=(",", ":")))
    return payload
