"""Each system's headline, recorded with where it came from.

The site leads every system with one figure. At each publish that figure is
written to the evidence layer exactly as published, with the source it rests
on (its retrieval time and checksum, from the fetch log), the steps that
produced it, what it was computed over, and the other sources joined to it.
`gt why` can then answer for every headline, and the audit's provenance check
measures something rather than an empty table.

This covers the headlines. District and row-level figures are not yet recorded
one by one, and the audit and the admin console both say so.
"""
from __future__ import annotations

import math
from datetime import datetime, timezone

import duckdb

from . import provenance as P
from . import sources as S

# The source each headline rests on. Stated rather than inferred: several
# systems read more than one domain source, and which one carries the figure
# is a fact about the method, not about the order of the registry.
PRIMARY = {
    "baseline": "edm_annual_return", "bellwether": "cqc_hsca_locations",
    "bulwark": "ea_aims_defences", "catchment": "gias_establishments",
    "compass": "dfe_sen_provision", "highwater": "ea_flood_objections",
    "junction": "dno_ecr_ukpn", "lastmile": "bduk_premises",
    "ledger": "planning_developer_contributions", "plumbline": "planning_ps2",
    "sentinel": "contracts_finder", "sightline": "ea_flood_objections",
    "watchman": "gazette_insolvency",
}

# How each other source a system reads meets the primary one.
_JOIN_ON = {"place_spine": "district", "entity_spine": "company number",
            "domain": "combined"}


def subject(system: str) -> str:
    return f"gt:document:publication:groundtruth-{system}"


def _half_up(x: float, places: int = 1) -> float:
    """The site's Math.round, which rounds halves up, not to even."""
    f = 10 ** places
    return math.floor(x * f + 0.5) / f


def _one(con, sql: str, params=()):
    try:
        return con.execute(sql, list(params)).fetchone()
    except duckdb.Error:
        return None


def _pct(v):
    return None if v is None else f"{v}%"


def _num(v):
    return None if v is None else f"{v:,.0f}"


def _fig(field, label, value, text, steps, coverage=None, note=None):
    return {"field": field, "label": label, "value_num": value, "value_text": text,
            "steps": steps, "coverage": coverage, "note": note}


# One function per system, each reading the published payload so the recorded
# value is the one the site shows.
def _catchment(s, con):
    n = s.get("national") or {}
    if n.get("utilisation_pct") is None:
        return []
    return [_fig("mainstream_utilisation_pct", "of mainstream school places in use",
                 n["utilisation_pct"], _pct(n["utilisation_pct"]),
                 ["open mainstream schools from the establishment register",
                  "pupils and capacity summed over the schools that publish both",
                  "pupils divided by capacity"],
                 (n.get("schools_measured"), n.get("schools")),
                 "schools that publish both a pupil count and a capacity")]


def _ledger(s, con):
    if s.get("total") is None:
        return []
    return [_fig("contributions_gbp", "of developer contributions recorded",
                 s["total"], f"£{s['total'] / 1e9:.2f}bn",
                 ["every developer contribution on the planning data platform",
                  "amounts summed where one is stated"],
                 (s.get("with_amount"), s.get("contributions")),
                 "contributions that state an amount")]


def _bulwark(s, con):
    c = s.get("coverage") or {}
    if c.get("overdue") is None:
        return []
    dated = _one(con, "SELECT count(next_inspection), count(*) FROM silver.flood_defence")
    return [_fig("inspections_overdue", "flood defence inspections overdue",
                 c["overdue"], _num(c["overdue"]),
                 ["every flood defence in the Environment Agency's asset register",
                  "counted where the asset's own next-inspection date has passed"],
                 tuple(dated) if dated else None,
                 "defences whose record carries a next-inspection date")]


def _plumbline(s, con):
    out = []
    timed = _one(con, """SELECT sum(major_dwellings_total - major_dwellings_extended),
                                sum(major_dwellings_total)
                         FROM silver.planning_performance WHERE quarter >= '2023'""")
    if s.get("statutory_pct") is not None:
        out.append(_fig(
            "statutory_pct", "major dwelling decisions made within 13 weeks without an extension",
            s["statutory_pct"], _pct(s["statutory_pct"]),
            ["major dwelling decisions since 2023 from the planning performance table",
             "those decided within 8 weeks, or 8 to 13 weeks, without a performance agreement",
             "divided by all major dwelling decisions"],
            tuple(timed) if timed and timed[0] is not None else None,
            "decisions with a published time band; those made under an agreed extension "
            "have none, and count as outside the 13 weeks"))
    if s.get("headline_pct") is not None:
        out.append(_fig(
            "headline_pct", "major decisions in time, counting agreed extensions",
            s["headline_pct"], _pct(s["headline_pct"]),
            ["major decisions since 2023 from the planning performance table",
             "in time: within 13 weeks, or within an agreed extension",
             "divided by all major decisions"],
            (s.get("major_decisions"), s.get("major_decisions")),
            "every major decision carries an in-time status"))
    return out


def _compass(s, con):
    e = next((r for r in s.get("national") or []
              if "Education, health" in str(r.get("provision"))), None)
    if not e or not e.get("earliest"):
        return []
    v = _half_up(100 * (e["latest"] - e["earliest"]) / e["earliest"])
    return [_fig("ehc_plan_growth_pct", "growth in statutory EHC plans", v, f"+{v}%",
                 ["EHC plan counts from DfE's special educational needs statistics",
                  "summed nationally for the first and latest years",
                  "change as a share of the first year"],
                 None, f"{e['earliest']:,} plans in the first year, {e['latest']:,} in the latest")]


def _baseline(s, con):
    n = s.get("national") or {}
    if n.get("adjusted") is None:
        return []
    cov = _one(con, """SELECT count(operational_pct), count(*) FROM gold.baseline_outlet
                       WHERE year = (SELECT max(year) FROM gold.baseline_outlet)""")
    return [_fig("adjusted_spills", "storm overflow spills after adjusting for monitor uptime",
                 n["adjusted"], _num(n["adjusted"]),
                 ["each storm overflow's annual event duration monitoring return",
                  "each outlet's spill count scaled to a full year by its monitor uptime",
                  "summed across outlets"],
                 tuple(cov) if cov else None, "outlets whose return states monitor uptime")]


def _highwater(s, con):
    o = s.get("outcomes") or []
    against = next((r for r in o if "against" in str(r.get("outcome", "")).lower()), None)
    if not against:
        return []
    total = sum(int(r.get("objections") or 0) for r in o)
    unknown = sum(int(r.get("objections") or 0) for r in o
                  if "unknown" in str(r.get("outcome", "")).lower())
    return [_fig("granted_against_advice", "permissions granted against flood-risk advice",
                 against["objections"], _num(against["objections"]),
                 ["every Environment Agency objection to planning on flood-risk grounds",
                  "counted where the recorded outcome is permission granted against the advice"],
                 (total - unknown, total), "objections with a recorded outcome")]


def _lastmile(s, con):
    if s.get("new_build_pct") is None:
        return []
    return [_fig("new_build_gigabit_pct", "of premises in new-build postcodes gigabit-capable",
                 s["new_build_pct"], _pct(s["new_build_pct"]),
                 ["premises-level gigabit availability from BDUK",
                  "postcodes with a recent new-build sale in the Price Paid data",
                  "share of premises in those postcodes that are gigabit-capable"],
                 None, f"against {s.get('other_pct')}% everywhere else")]


def _junction(s, con):
    r = s.get("registers") or []
    if not r:
        return []
    adv = sum(int(x.get("catalogue_records") or 0) for x in r)
    got = sum(int(x.get("rows") or 0) for x in r)
    return [_fig("records_served", "capacity records actually served", got, f"{got:,} of {adv:,}",
                 ["each distribution operator's embedded capacity register",
                  "the records its catalogue advertises, against the records its API serves"],
                 (got, adv),
                 f"{sum(1 for x in r if x.get('publishes_data'))} of {len(r)} operators serve data openly")]


def _bellwether(s, con):
    t = (s.get("systemic") or [None])[0]
    if not t:
        return []
    of = _one(con, "SELECT count(DISTINCT local_authority) FROM gold.bellwether_group")
    brand = str(t.get("brand", "")).replace("BRAND ", "")
    return [_fig("authorities_on_one_group", "authorities where the largest care group holds beds",
                 t["authorities"], _num(t["authorities"]),
                 ["every CQC-registered care location with beds",
                  "grouped by the regulator's brand field",
                  "for the largest group by beds, the authorities where it holds any"],
                 (t["authorities"], of[0]) if of else None,
                 f"{brand}: {int(t.get('beds') or 0):,} beds across {t.get('companies')} companies")]


def _sentinel(s, con):
    m = s.get("method") or []
    tot = sum(int(x.get("awards") or 0) for x in m)
    if not tot:
        return []
    un = sum(int(x.get("awards") or 0) for x in m if x.get("method") in ("direct", "limited"))
    unstated = sum(int(x.get("awards") or 0) for x in m if x.get("method") in (None, "", "not stated"))
    v = _half_up(100 * un / tot)
    return [_fig("uncompeted_share_pct", "of awards made without open competition", v, _pct(v),
                 ["contract award notices from Contracts Finder and Find a Tender",
                  "grouped by the procurement method each notice states",
                  "direct and limited awards divided by all awards"],
                 (tot - unstated, tot),
                 "awards whose notice states a method; the rest stay in the denominator")]


def _sightline(s, con):
    r = s.get("reasons") or []
    if not r:
        return []
    tot = sum(int(x.get("objections") or 0) for x in r)
    return [_fig("water_quality_objections", "water quality objections", tot, _num(tot),
                 ["Environment Agency objections to planning applications",
                  "those raised on water quality grounds"],
                 None, "none carries a recorded outcome: the field does not exist")]


def _watchman(s, con):
    ex = s.get("exposures")
    if ex is None:
        return []
    return [_fig("notice_exposures", "suppliers found in an insolvency notice", len(ex), _num(len(ex)),
                 ["suppliers named on public contract awards",
                  "matched by company number to insolvency notices in the Gazette"],
                 None, "the register of suppliers must accumulate before this produces signal")]


FIGURES = {
    "baseline": _baseline, "bellwether": _bellwether, "bulwark": _bulwark,
    "catchment": _catchment, "compass": _compass, "highwater": _highwater,
    "junction": _junction, "lastmile": _lastmile, "ledger": _ledger,
    "plumbline": _plumbline, "sentinel": _sentinel, "sightline": _sightline,
    "watchman": _watchman,
}


def _last_fetch(con, source_id: str):
    row = _one(con, """SELECT fetched_at, sha256 FROM bronze.fetch_log
                       WHERE source_id = ? AND ok ORDER BY fetched_at DESC LIMIT 1""", [source_id])
    return (row[0], row[1]) if row else (None, None)


def headlines(con: duckdb.DuckDBPyConnection, payload: dict) -> list[tuple[P.Observation, str]]:
    """(observation, label) for every headline in a built payload."""
    reg = {s.id: s for s in S.REGISTRY}
    out = []
    for system, fn in FIGURES.items():
        s = (payload.get("systems") or {}).get(system)
        if not s:
            continue
        src = reg.get(PRIMARY[system])
        joins = [{"on": _JOIN_ON.get(x.role, "combined"), "to": x.id}
                 for x in S.REGISTRY
                 if system in x.systems and x.id != PRIMARY[system] and not x.blocked]
        retrieved, sha = _last_fetch(con, src.id) if src else (None, None)
        for f in fn(s, con):
            cov = f["coverage"]
            n, of = ((int(cov[0]), int(cov[1]))
                     if cov and cov[0] is not None and cov[1] is not None else (None, None))
            note = f["note"] or ""
            if src and retrieved is None:
                note += ("; " if note else "") + ("the source file holds no fetch record, so its "
                                                  "retrieval time and checksum are not known")
            out.append((P.Observation(
                subject=subject(system), field=f["field"], derivation=P.DERIVED,
                value_num=float(f["value_num"]) if f["value_num"] is not None else None,
                value_text=f["value_text"], retrieved_at=retrieved, source_sha256=sha,
                transformations=list(f["steps"]), joins=joins,
                coverage_n=n, coverage_of=of, note=note or None,
                **(P.from_source(src) if src else {})), f["label"]))
    return out


def record_headlines(con: duckdb.DuckDBPyConnection, payload: dict) -> dict:
    """Record every headline and return what the site publishes about them."""
    run_id = "publish-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    pairs = headlines(con, payload)
    P.record(con, run_id, [o for o, _ in pairs])
    by_system: dict[str, list] = {}
    for o, label in pairs:
        system = o.subject.rsplit("groundtruth-", 1)[-1]
        by_system.setdefault(system, []).append({
            "subject": o.subject, "field": o.field, "label": label,
            "value_num": o.value_num, "value_text": o.value_text,
            "derivation": o.derivation, "source_id": o.source_id,
            "publisher": o.publisher, "dataset": o.dataset, "source_url": o.source_url,
            "retrieved_at": o.retrieved_at.isoformat() if o.retrieved_at else None,
            "sha256": o.source_sha256, "transformations": o.transformations,
            "joins": o.joins, "coverage_n": o.coverage_n, "coverage_of": o.coverage_of,
            "coverage_pct": o.coverage_pct, "note": o.note})
    return {"run_id": run_id, "summary": P.summary(con), "scope": "headlines",
            "headlines": by_system}
