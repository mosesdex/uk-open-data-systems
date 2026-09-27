"""Region and combined authority pages: the whole-area figures.

Searching London used to return City of London, a district of about 8,000
residents, because no district is named London -- only 33 of them, together,
are. silver.lad_area (built by load.load_lad_area) says which districts sit
inside which region or combined authority; this module turns that membership
into whole-area figures for the eleven questions that can honestly carry one.

The two things that make a whole-area figure a confident lie rather than a
finding, and how this module avoids each:

  * A percentage must never be the mean of district percentages -- that
    weights a district of 8,000 people the same as one of 300,000. Every
    percentage here is recomputed from the summed numerator and denominator
    instead (see RULES["..."]["rule"] == "recomputed").
  * A figure published per upper-tier authority (Compass) is copied onto
    every district of that authority, so summing or averaging across
    districts would count a county's figure once per district it covers.
    Combined over distinct authority_name first instead ("dedupe-weighted").
    A figure that differs by nature between authorities and cannot honestly
    be combined at all (Bellwether) is refused outright ("not combinable"):
    the area page says so and links to the districts, which can answer it.

RULES is the declared content; build() and the handful of _combine_* helpers
below it are the one generic combiner Task 7's brief asks for, so a twelfth
question is a new table row here, not a new branch of code.
"""
from __future__ import annotations

import duckdb

from . import places as PL

# Every question that can be combined, and how. Five publish per upper-tier
# authority under a name (lpa / local_authority / authority) rather than a
# lad_code -- the same nine-spellings problem places.py already solved for
# the place page -- so those five carry key_kind "name" and are resolved
# against silver.lad through places.build_index, the identical lookup the
# place page's own SOURCES resolution uses. The other six already carry
# lad_code on every row (either because a postcode or grid reference placed
# them there, like Baseline, Junction and Sentinel, or because their own
# district table was built with it, like Catchment, Lastmile, Compass and
# Bellwether) and are read directly.
RULES: dict[str, dict] = {
    "catchment": {
        "table": "gold.catchment_district", "key": "lad_code",
        "rule": "recomputed",
        "sum_fields": ["pupils", "capacity", "schools", "schools_measured"],
        "recompute": [
            {"num": "pupils", "den": "capacity", "out": "utilisation_pct"},
            {"num": "schools_measured", "den": "schools", "out": "measured_pct"},
        ],
    },
    "lastmile": {
        "table": "gold.lastmile_authority", "key": "lad_code",
        "rule": "recomputed",
        "sum_fields": ["premises", "gigabit_now"],
        "recompute": [{"num": "gigabit_now", "den": "premises", "out": "gigabit_pct"}],
    },
    "highwater": {
        "table": "gold.highwater_authority", "key": "lpa", "key_kind": "name",
        "rule": "recomputed",
        "sum_fields": ["objections", "granted_against", "outcome_unknown", "homes_against"],
        "recompute": [{"num": "granted_against", "den": "objections", "out": "override_rate_pct"}],
    },
    "bulwark": {
        "table": "gold.bulwark_authority", "key": "local_authority", "key_kind": "name",
        "rule": "recomputed",
        "sum_fields": ["assets", "graded", "inspection_overdue"],
        "recompute": [{"num": "graded", "den": "assets", "out": "graded_pct"}],
    },
    "ledger": {
        "table": "gold.ledger_authority", "key": "authority", "key_kind": "name",
        "rule": "recomputed",
        "sum_fields": ["contributions", "with_amount", "total_amount", "with_location"],
        "recompute": [{"num": "with_amount", "den": "contributions", "out": "amount_coverage_pct"}],
    },
    "baseline": {
        "table": "gold.baseline_district", "key": "lad_code",
        "rule": "sum",
        "sum_fields": ["outlets", "adjusted_spills", "reported_spills"],
    },
    "sightline": {
        "table": "gold.sightline_authority", "key": "lpa", "key_kind": "name",
        "rule": "sum",
        "sum_fields": ["flood_objections", "flood_outcome_unknown", "water_objections"],
    },
    "plumbline": {
        "table": "gold.plumbline_authority", "key": "lpa", "key_kind": "name",
        "rule": "weighted",
        # The numerator behind each percentage is never published, only the
        # percentage and the count of decisions it was struck over -- so that
        # count is what has to carry the weight instead.
        "weighted": [
            {"pct": "statutory_pct", "weight": "dwelling_decisions"},
            {"pct": "headline_pct", "weight": "major_decisions"},
        ],
    },
    "compass": {
        "table": "gold.compass_district", "key": "lad_code",
        "rule": "dedupe-weighted",
        # TIERED: every district of a county carries an identical copy of
        # that county's figure, so the county must be counted once, not once
        # per district it happens to cover.
        "dedupe_key": "authority_name",
        "weighted": [{"pct": "projected_change_pct", "weight": "mean_pupils"}],
    },
    "sentinel": {
        "table": "gold.sentinel_district", "key": "lad_code",
        "rule": "recomputed",
        "sum_fields": ["awards", "closed_awards", "total_value"],
        "recompute": [{"num": "closed_awards", "den": "awards", "out": "closed_pct"}],
    },
    "junction": {
        "table": "gold.junction_district", "key": "lad_code",
        "rule": "sum",
        "sum_fields": ["connections", "connected_mw", "accepted_mw"],
    },
    "bellwether": {
        "table": "gold.bellwether_district", "key": "lad_code",
        "rule": "not combinable",
        "reason": (
            "Bellwether is the largest care group's share of one authority's beds, "
            "and the largest group differs between authorities. Adding one "
            "authority's share to another's would produce a number that describes "
            "nothing, so this is published per district only. See each district "
            "below for its own figure."
        ),
    },
}


def _exists(con: duckdb.DuckDBPyConnection, qualified: str) -> bool:
    schema, table = qualified.split(".")
    return con.execute(
        "SELECT count(*) FROM information_schema.tables "
        "WHERE table_schema = ? AND table_name = ?", [schema, table]).fetchone()[0] > 0


def _rows_by_district(con: duckdb.DuckDBPyConnection, spec: dict, name_index: dict) -> dict[str, dict]:
    """This question's rows, keyed by district code, whichever way each row
    names its district: directly, or by an authority name resolved against
    the same index the place page's own SOURCES resolution uses."""
    table = spec["table"]
    if not _exists(con, table):
        return {}
    key = spec["key"]
    cur = con.execute(f"SELECT * FROM {table} WHERE {key} IS NOT NULL")
    cols = [d[0] for d in cur.description]
    rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    if spec.get("key_kind") == "name":
        out: dict[str, dict] = {}
        for r in rows:
            hit = name_index.get(PL.normalise_authority(r[key]))
            if hit and hit[0] not in out:
                out[hit[0]] = r
        return out
    return {r[key]: r for r in rows}


def _weighted(specs: list[dict], rows: list[dict]) -> dict:
    out: dict = {"weighted_by": {}}
    for w in specs:
        pct_f, weight_f = w["pct"], w["weight"]
        weighed = [r for r in rows if r.get(pct_f) is not None and r.get(weight_f)]
        total_weight = sum(r[weight_f] for r in weighed)
        out[pct_f] = round(sum(r[pct_f] * r[weight_f] for r in weighed) / total_weight, 1) \
            if total_weight else None
        out[weight_f] = sum(r.get(weight_f) or 0 for r in rows)
        out["weighted_by"][pct_f] = weight_f
    return out


def _combine(spec: dict, rows: list[dict]) -> dict:
    """One rule, applied to whichever rows this area's districts carry for a
    question. rows is never empty -- build() only calls this once a question
    has at least one row among the area's districts."""
    rule = spec["rule"]

    if rule == "not combinable":
        return {"rule": rule, "districts": len(rows), "reason": spec["reason"]}

    if rule in ("weighted", "dedupe-weighted"):
        source = rows
        authorities = None
        if rule == "dedupe-weighted":
            dedupe_key = spec["dedupe_key"]
            seen: dict = {}
            for r in rows:
                k = r.get(dedupe_key)
                if k is not None and k not in seen:
                    seen[k] = r
            source = list(seen.values())
            authorities = len(source)
        out = {"rule": rule, "districts": len(rows)}
        if authorities is not None:
            out["authorities"] = authorities
        out.update(_weighted(spec["weighted"], source))
        return out

    # "recomputed" and "sum" both start from the summed fields; "recomputed"
    # additionally turns some of those sums into a percentage.
    sums = {f: sum(r.get(f) or 0 for r in rows) for f in spec["sum_fields"]}
    out = {"rule": rule, "districts": len(rows), **sums}
    if rule == "recomputed":
        for rc in spec["recompute"]:
            num, den, out_field = rc["num"], rc["den"], rc["out"]
            out[out_field] = round(100.0 * sums[num] / sums[den], 1) if sums.get(den) else None
    return out


def build(con: duckdb.DuckDBPyConnection) -> dict:
    """Every region and combined authority, its districts and its whole-area
    figures. An area whose districts are all unknown to the place spine is
    not published at all; a question no district of an area carries a row
    for gets no entry, exactly as a place page's own absences work."""
    if not _exists(con, "silver.lad_area") or not _exists(con, "silver.lad"):
        return {}

    known = {r[0] for r in con.execute("SELECT lad_code FROM silver.lad").fetchall()}
    areas: dict[str, dict] = {}
    for lad_code, area_code, area_name, kind in con.execute(
            "SELECT lad_code, area_code, area_name, kind FROM silver.lad_area"
            ).fetchall():
        if lad_code not in known:
            continue
        entry = areas.setdefault(area_code, {"name": area_name, "kind": kind, "districts": set()})
        entry["districts"].add(lad_code)
    if not areas:
        return {}
    for entry in areas.values():
        entry["districts"] = sorted(entry["districts"])

    name_index = PL.build_index(con)
    for qid, spec in RULES.items():
        rows_by_district = _rows_by_district(con, spec, name_index)
        if not rows_by_district:
            continue
        for entry in areas.values():
            rows = [rows_by_district[d] for d in entry["districts"] if d in rows_by_district]
            if not rows:
                continue
            entry.setdefault("figures", {})[qid] = _combine(spec, rows)

    for entry in areas.values():
        entry.setdefault("figures", {})

    return areas
