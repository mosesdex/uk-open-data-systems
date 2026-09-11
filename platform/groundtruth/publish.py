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


def _unplaced_reasons(con) -> dict | None:
    """Mainstream schools with no district, by the reason Catchment recorded.

    Counted over the same rows as schools_unplaced, so the parts sum to the
    headline. None when the table predates the column, rather than zeros that
    would read as "no reason to give".
    """
    cols = {r[0] for r in con.execute(
        "SELECT column_name FROM duckdb_columns() "
        "WHERE schema_name = 'gold' AND table_name = 'catchment_school'").fetchall()}
    if "unplaced_reason" not in cols:
        return None
    return {k: v for k, v in con.execute("""
        SELECT unplaced_reason, count(*) FROM gold.catchment_school
        WHERE mainstream AND lad_code IS NULL GROUP BY 1""").fetchall() if k}


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


def _entity_profiles(con) -> list[dict]:
    """A bounded, meaningful slice of the organisation graph: every company that
    spans more than one system, plus the largest by care footprint and by
    procurement value. Each profile carries only what its own records support —
    its systems, its owners (persons of significant control), its geography and
    its cross-system links."""
    if not _exists(con, "gold", "entity"):
        return []
    picks = {}
    def take(rows):
        for r in rows:
            picks.setdefault(r["company_number"], r)
    take(_rows(con, "SELECT * FROM gold.entity WHERE in_care AND in_proc"))
    take(_rows(con, "SELECT * FROM gold.entity WHERE in_care ORDER BY care_beds DESC NULLS LAST LIMIT 60"))
    take(_rows(con, "SELECT * FROM gold.entity WHERE in_proc ORDER BY proc_value DESC NULLS LAST LIMIT 45"))
    ids = list(picks)
    if not ids:
        return []
    ph = ",".join("?" * len(ids))

    owners = {}
    for o in _rows(con, f"""SELECT upper(trim(company_number)) AS cn, kind, name
                            FROM silver.psc WHERE upper(trim(company_number)) IN ({ph})
                            AND name IS NOT NULL""", ids):
        owners.setdefault(o["cn"], [])
        if len(owners[o["cn"]]) < 6:
            owners[o["cn"]].append({
                "name": o["name"],
                "kind": "person" if o["kind"] and "individual" in o["kind"] else "organisation",
            })

    las = {}
    for r in _rows(con, f"""SELECT upper(trim(company_number)) AS cn, local_authority AS la,
                            sum(beds) AS beds FROM silver.care_location
                            WHERE upper(trim(company_number)) IN ({ph}) AND local_authority IS NOT NULL
                            GROUP BY 1,2 ORDER BY beds DESC NULLS LAST""", ids):
        las.setdefault(r["cn"], [])
        if len(las[r["cn"]]) < 8:
            las[r["cn"]].append({"name": r["la"], "beds": r["beds"]})

    buyers = {}
    for r in _rows(con, f"""SELECT upper(trim(company_number)) AS cn, buyer,
                            count(*) AS awards, round(sum(value)) AS value
                            FROM silver.procurement_award
                            WHERE upper(trim(company_number)) IN ({ph}) AND buyer IS NOT NULL
                            GROUP BY 1,2 ORDER BY value DESC NULLS LAST""", ids):
        buyers.setdefault(r["cn"], [])
        if len(buyers[r["cn"]]) < 8:
            buyers[r["cn"]].append({"name": r["buyer"], "awards": r["awards"], "value": r["value"]})

    out = []
    for cn, e in picks.items():
        systems = []
        if e["in_care"]:
            systems.append("bellwether")
        if e["in_proc"]:
            systems.append("sentinel")
        out.append({
            "id": cn, "name": e["name"] or cn, "status": e["status"],
            "town": e["post_town"], "incorporated": e["incorporated"], "brand": e["brand"],
            "systems": systems,
            "care": {"locations": e["care_locations"], "beds": e["care_beds"],
                     "authorities": e["care_authorities"], "top_las": las.get(cn, [])} if e["in_care"] else None,
            "proc": {"awards": e["proc_awards"], "value": e["proc_value"],
                     "buyers": e["proc_buyers"], "top_buyers": buyers.get(cn, [])} if e["in_proc"] else None,
            "owners": owners.get(cn, []),
        })
    # cross-system first, then by combined footprint
    out.sort(key=lambda o: (-len(o["systems"]),
                            -((o["care"]["beds"] or 0) if o["care"] else 0)
                            - ((o["proc"]["value"] or 0) / 1e6 if o["proc"] else 0)))
    return out


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
    # One source of truth for source state, so the public list and the operator
    # console can never disagree about whether a feed is supplying data.
    if _exists(con, "bronze", "fetch_log"):
        from . import admin as _admin
        bronze_dir = Path(__file__).resolve().parent.parent / "data" / "bronze"
        out["sources"]["status"] = _admin.source_health(con, bronze_dir)

    # ---- systems ----
    S = out["systems"]

    if _exists(con, "gold", "catchment_district"):
        S["catchment"] = {
            # Coverage travels with every statistic, and the national headline
            # was the one place it did not. This figure is computed over the
            # schools that publish both a roll and a capacity, in districts the
            # place spine resolved -- so it states both, as each district row
            # already did.
            "national": _rows(con, """SELECT count(*) AS districts, sum(pupils) AS pupils,
                sum(capacity) AS capacity,
                round(100.0*sum(pupils)/nullif(sum(capacity),0),1) AS utilisation_pct,
                sum(schools) AS schools, sum(schools_measured) AS schools_measured,
                round(100.0*sum(schools_measured)/nullif(sum(schools),0),1) AS measured_pct
                FROM gold.catchment_district""")[0]
                | (lambda x: {"schools_unplaced": x[0],
                              "pupils_unplaced": x[1] or 0,
                              "unplaced_pct": round(100.0 * x[0] / (x[0] + x[2]), 2)
                                              if (x[0] + x[2]) else 0.0})(
                    con.execute("""SELECT
                        (SELECT count(*) FROM gold.catchment_school
                          WHERE mainstream AND lad_code IS NULL),
                        (SELECT sum(pupils) FROM gold.catchment_school
                          WHERE mainstream AND lad_code IS NULL),
                        (SELECT sum(schools) FROM gold.catchment_district)""").fetchone())
                | {"unplaced_by_reason": _unplaced_reasons(con)},
            "specialist": _rows(con, """SELECT count(*) AS districts, sum(pupils) AS pupils,
                sum(capacity) AS capacity,
                round(100.0*sum(pupils)/nullif(sum(capacity),0),1) AS utilisation_pct,
                sum(over_capacity) AS over_capacity FROM gold.catchment_specialist""")[0],
            "by_district": _rows(con, """SELECT lad_code, lad_name, schools, pupils,
                capacity, utilisation_pct, measured_pct, entity_resolved_pct
                FROM gold.catchment_district WHERE lad_code IS NOT NULL"""),
            "trend": _rows(con, """SELECT year_label, utilisation_pct, primary_pct,
                secondary_pct, pupils, capacity, schools
                FROM gold.catchment_trend ORDER BY period""")
                if _exists(con, "gold", "catchment_trend") else [],
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
            "by_district": _rows(con, "SELECT lad_code, lad_name, assets, overdue, owner_known FROM gold.bulwark_district")
                if _exists(con, "gold", "bulwark_district") else [],
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
                count(*) AS outlets FROM gold.baseline_outlet
                WHERE year=(SELECT max(year) FROM gold.baseline_outlet)""")[0],
            "by_company": _rows(con, """SELECT * FROM gold.baseline_company
                WHERE year=(SELECT max(year) FROM gold.baseline_company)
                ORDER BY reported_spills DESC LIMIT 12"""),
            "by_district": _rows(con, "SELECT lad_code, outlets, adjusted_spills, reported_spills FROM gold.baseline_district")
                if _exists(con, "gold", "baseline_district") else [],
            "trend": _rows(con, "SELECT year, outlets, reported_spills, adjusted_spills, mean_uptime FROM gold.baseline_trend ORDER BY year")
                if _exists(con, "gold", "baseline_trend") else [],
            "weather": _rows(con, """SELECT company, spills, mean_local_rain_mm,
                spills_per_100mm_rain FROM gold.baseline_rainfall
                ORDER BY spills_per_100mm_rain DESC LIMIT 12""")
                if _exists(con, "gold", "baseline_rainfall") else [],
        }

    if _exists(con, "gold", "highwater_trend"):
        S["highwater"] = {
            "outcomes": _rows(con, "SELECT * FROM gold.highwater_outcome"),
            "trend": _rows(con, "SELECT * FROM gold.highwater_trend ORDER BY year"),
            "by_authority": _rows(con, """SELECT lpa, objections, granted_against,
                override_rate_pct, homes_against FROM gold.highwater_authority
                WHERE granted_against > 0 ORDER BY granted_against DESC LIMIT 15""")
                if _exists(con, "gold", "highwater_authority") else [],
            "by_district": _rows(con, "SELECT lad_code, objections, granted_against FROM gold.highwater_district")
                if _exists(con, "gold", "highwater_district") else [],
        }

    if _exists(con, "gold", "plumbline_quarter"):
        from .systems import plumbline as P
        h, st, md, dd = P.national_gap(con, since="2023")
        ext_major, ext_dw = P.extension_share(con, since="2023")
        S["plumbline"] = {
            "headline_pct": h, "statutory_pct": st,
            "major_decisions": md, "dwelling_decisions": dd,
            # What separates the two: decisions made under an agreed extension.
            "extended_pct": ext_major, "dwellings_extended_pct": ext_dw,
            "worst": _rows(con, "SELECT * FROM gold.plumbline_authority LIMIT 10"),
            # 47 years of PS2 are already loaded; annualise from 2008 so the
            # extension-of-time divergence (post-2013) is visible over time.
            "trend": _rows(con, """SELECT left(quarter,4) AS year,
                round(100.0*sum(major_in_time)/nullif(sum(major_decisions),0),1) AS headline_pct,
                round(100.0*sum(within_13_weeks)/nullif(sum(dwelling_decisions),0),1) AS statutory_pct,
                sum(dwelling_decisions) AS dwelling_decisions
                FROM gold.plumbline_quarter
                WHERE TRY_CAST(left(quarter,4) AS INTEGER) BETWEEN 2008 AND 2025
                GROUP BY 1 ORDER BY 1"""),
        }

    if _exists(con, "gold", "sentinel_method"):
        S["sentinel"] = {
            "method": _rows(con, "SELECT * FROM gold.sentinel_method"),
            "concentrated": _rows(con, """SELECT * FROM gold.sentinel_buyer
                WHERE awards >= 5 ORDER BY top_supplier_award_share DESC LIMIT 10"""),
            "shared_control": _rows(con, "SELECT * FROM gold.sentinel_shared_control LIMIT 20")
                if _exists(con, "gold", "sentinel_shared_control") else [],
            "control_footprint": _rows(con,
                "SELECT * FROM gold.sentinel_control_footprint LIMIT 15")
                if _exists(con, "gold", "sentinel_control_footprint") else [],
            # The list above is capped for size; the count is not.
            "control_footprint_total": _rows(con,
                "SELECT count(*) AS n FROM gold.sentinel_control_footprint")[0]["n"]
                if _exists(con, "gold", "sentinel_control_footprint") else 0,
        }
        # The shared-control check can find nothing. Publish what it examined,
        # so a zero reads as a result rather than as a missing section.
        if _exists(con, "gold", "sentinel_shared_control"):
            from .systems import sentinel as _sen
            S["sentinel"]["shared_control_probe"] = _sen.shared_control_stats(con)

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
            "cohort": _rows(con, """SELECT la_name, ehc_mean, annual_births,
                ehc_per_1000_births FROM gold.compass_cohort
                WHERE annual_births >= 500 ORDER BY ehc_per_1000_births DESC LIMIT 10""")
                if _exists(con, "gold", "compass_cohort") else [],
            # National annual series (2015 onward) so the divergence between EHC
            # plans and the pupil population can be shown over time, not just as
            # a start/end pair.
            "trend": _rows(con, """SELECT year,
                sum(pupils) FILTER (WHERE provision = 'Education, health and care plan') AS ehc,
                sum(pupils) FILTER (WHERE provision = 'SEN support / SEN without an EHC plan') AS sen,
                sum(pupils) FILTER (WHERE provision = 'Total') AS total
                FROM gold.compass_series GROUP BY year ORDER BY year"""),
        }

    if _exists(con, "gold", "lastmile_authority"):
        from .systems import lastmile as LM
        nb_p, nb_g, nb_pct, ot_p, ot_pct = LM.comparison(con)
        S["lastmile"] = {"new_build_pct": nb_pct, "other_pct": ot_pct,
                         "new_build_premises": nb_p, "other_premises": ot_p,
                         "by_authority": _rows(con, "SELECT * FROM gold.lastmile_authority LIMIT 12"),
                         "by_district": _rows(con, """SELECT lad_code, lad_name, premises,
                             gigabit_pct FROM gold.lastmile_authority
                             WHERE lad_code IS NOT NULL"""),
                         "worst_gap": _rows(con, """SELECT lad_name, gigabit_pct,
                             gigabit_pct_new_build, new_build_sales,
                             round(gigabit_pct - gigabit_pct_new_build, 1) AS gap
                             FROM gold.lastmile_authority
                             WHERE gigabit_pct_new_build IS NOT NULL AND new_build_sales >= 500
                             ORDER BY gap DESC LIMIT 10""")}

    if _exists(con, "gold", "sightline_reason"):
        S["sightline"] = {"reasons": _rows(con, "SELECT * FROM gold.sightline_reason LIMIT 10")}
        if _exists(con, "gold", "sightline_wq_authority"):
            S["sightline"]["corpus"] = _rows(con, """SELECT count(*) AS applications,
                count(DISTINCT lpa) AS authorities,
                count(*) FILTER (WHERE decided_date IS NOT NULL) AS decided
                FROM silver.planning_water_quality""")[0]
            S["sightline"]["by_theme"] = _rows(con, "SELECT * FROM gold.sightline_wq_theme")
            S["sightline"]["by_authority_wq"] = _rows(con,
                "SELECT * FROM gold.sightline_wq_authority LIMIT 15")
            S["sightline"]["by_district"] = _rows(con,
                "SELECT lad_code, applications FROM gold.sightline_wq_district")

    if _exists(con, "gold", "watchman_exposure"):
        S["watchman"] = {"exposures": _rows(con, "SELECT * FROM gold.watchman_exposure LIMIT 20")}
        if _exists(con, "gold", "watchman_distress"):
            S["watchman"]["distress"] = _rows(con, """SELECT count(*) AS total,
                count(*) FILTER (WHERE role='CQC care provider') AS care,
                count(*) FILTER (WHERE role='Public contract supplier') AS contracts
                FROM gold.watchman_distress""")[0]
            S["watchman"]["by_status"] = _rows(con, """SELECT company_status AS status,
                count(*) AS n FROM gold.watchman_distress GROUP BY 1 ORDER BY 2 DESC""")
            S["watchman"]["by_role"] = _rows(con, """SELECT role, count(*) AS n
                FROM gold.watchman_distress GROUP BY 1 ORDER BY 2 DESC""")
            S["watchman"]["distress_list"] = _rows(con, """SELECT name, company_status,
                role, activity, company_number FROM gold.watchman_distress
                ORDER BY activity DESC LIMIT 25""")

    # Cross-system chains, executed rather than illustrated.
    from . import chains as CH
    out["chains"] = [
        {"name": c.name, "trigger": c.trigger, "spine": c.spine,
         "systems_touched": c.systems_touched,
         "steps": [{"system": s.system, "question": s.question,
                    "answer": s.answer, "found": s.found} for s in c.steps]}
        for c in CH.run_all(con)
    ]
    out["reuse"] = CH.reuse_summary(con)

    # One place, every system -- the platform's proposition made answerable.
    from . import places as PL
    pv = PL.place_view(con)
    lad_names = dict(con.execute("SELECT lad_code, lad_name FROM silver.lad").fetchall()) \
        if _exists(con, "silver", "lad") else {}
    out["places"] = {
        "districts": pv["districts"],
        "resolution": pv["resolution"],
        "names": lad_names,
        "byLad": pv["places"],
        "capacityTrend": pv.get("capacity", {}),
    }

    # Operator view: everything traceable to a row, nothing invented.
    from . import admin as A
    out["admin"] = A.build(con, Path(__file__).resolve().parent.parent / "data" / "bronze")

    # The data journey, with real counts at each stage. This is what makes the
    # pipeline diagram honest: every stage shows what the platform actually did.
    def _n(tbl):
        sch, t = tbl.split(".")
        if not _exists(con, sch, t):
            return 0
        return con.execute(f"SELECT count(*) FROM {tbl}").fetchone()[0]

    srcs = out.get("sources", {}).get("status", [])
    fetched = [r for r in srcs if r.get("provenance") in ("logged", "unlogged")]
    publishers = sorted({r.get("publisher") for r in fetched if r.get("publisher")})
    total_bytes = 0
    if _exists(con, "bronze", "fetch_log"):
        row = con.execute("SELECT sum(bytes_len) FROM bronze.fetch_log WHERE ok").fetchone()
        total_bytes = row[0] or 0

    out["organisations"] = _entity_profiles(con)

    out["pipeline"] = {
        "source":  {"sources": len(fetched), "publishers": len(publishers),
                    "blocked": sum(1 for r in srcs if r.get("blocked"))},
        "collect": {"downloaded_bytes": total_bytes,
                    "runs": _n("bronze.fetch_log")},
        "process": {"properties": _n("silver.place_uprn"),
                    "postcodes": _n("silver.place_postcode"),
                    "crosswalks": _n("silver.lids_uprn_usrn") + _n("silver.lids_uprn_toid"),
                    "companies": _n("silver.company"),
                    "ownership": _n("silver.psc"),
                    "charities": _n("silver.charity")},
        "validate": {"gold_tables": len([1 for t in
                       con.execute("SELECT table_name FROM information_schema.tables "
                                   "WHERE table_schema='gold'").fetchall()])},
        "groundtruth": {"systems": len(S)},
        "public": {"generated": generated},
    }

    # The corrections belong in the payload, not in a closing paragraph. A
    # platform that publishes its own error rate is making a checkable claim;
    # one that mentions it in prose is making a reassuring noise.
    from . import claims as _claims
    out["corrections"] = {"summary": _claims.summary(),
                          "entries": _claims.as_payload()}

    # What can currently be walked, so the graph's coverage is published on the
    # same terms as everything else.
    try:
        from . import graph as _graph
        out["graph"] = _graph.stats(con)
    except Exception as exc:                 # a stale spec must not stop a publish
        out["graph"] = {"error": str(exc).splitlines()[0]}

    # Where the platform's own outputs disagree with each other. Published on
    # the same terms as everything else: a check that could not run is listed as
    # unrun, not quietly omitted.
    try:
        from . import contradictions as _cd
        full = _cd.run_all(con, limit=5)
        out["contradictions"] = {
            "checks": full["checks"], "run": full["run"],
            "unrun": full["unrun"],
            "with_disagreement": full["with_disagreement"],
            "total_disagreements": full["total_disagreements"],
            "results": [{k: v for k, v in r.items() if k != "disagreements"}
                        | {"examples": r["disagreements"][:3]}
                        for r in full["results"]],
        }
    except Exception as exc:
        out["contradictions"] = {"error": str(exc).splitlines()[0]}

    # Where each evidence chain stops, and whether that is this platform's
    # doing, a publisher's, or nobody's. Published so the gaps can be argued
    # with on the same terms as the figures.
    try:
        from . import gaps as _gaps
        out["gaps"] = _gaps.report(con)
    except Exception as exc:
        out["gaps"] = {"error": str(exc).splitlines()[0]}

    out["built_systems"] = sorted(S)
    return out


def _dump(payload: dict, dest: Path) -> None:
    dest.write_text(json.dumps(payload, default=str, separators=(",", ":")))


def _code_version() -> str:
    import subprocess
    try:
        return subprocess.run(["git", "describe", "--always", "--dirty"],
                              cwd=Path(__file__).resolve().parent, capture_output=True,
                              text=True, timeout=5).stdout.strip()
    except Exception:
        return ""


def write(con: duckdb.DuckDBPyConnection, dest: Path) -> dict:
    payload = build_payload(con)
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    _dump(payload, dest)

    # The audit compares the file just written with the database, so it runs
    # after the first write and its findings go into a second.
    from dataclasses import asdict
    from . import audit as _audit
    try:
        a = _audit.run(con, payload_path=dest)
        payload["audit"] = {"summary": a.summary(),
                            "findings": [asdict(f) for f in a.sorted()],
                            "checks_run": a.checks_run,
                            "checks_skipped": a.checks_skipped}
    except Exception as exc:
        payload["audit"] = {"error": str(exc).splitlines()[0]}

    # Every publish records the shape of what it was built from. A publish
    # that was not recorded cannot be reconstructed later, so the history
    # starts with each publish rather than whenever someone remembers.
    from . import temporal as _temporal
    try:
        snap = _temporal.snapshot(con, label="publish", code_version=_code_version())
        payload["history"] = {"latest": snap,
                              "snapshots": _temporal.snapshots(con, limit=20)}
    except Exception as exc:
        payload["history"] = {"error": str(exc).splitlines()[0]}

    _dump(payload, dest)
    return payload
