"""Cross-system chains.

The argument for one platform rather than thirteen procurements is that a single
fact arriving sets off several systems at once, and that each new system costs
less than the one before it. That is easy to assert and worth demonstrating, so
this module runs the chains against the real gold tables and reports what each
step actually returns.

A step that finds nothing says so. The chains are not illustrations.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

import duckdb


@dataclass
class Step:
    system: str
    question: str
    answer: str
    found: int = 0
    detail: list = field(default_factory=list)


@dataclass
class Chain:
    name: str
    trigger: str
    spine: str
    steps: list[Step] = field(default_factory=list)

    @property
    def systems_touched(self) -> int:
        return len({s.system for s in self.steps if s.found})


def _has(con, schema, table) -> bool:
    return con.execute(
        "SELECT count(*) FROM information_schema.tables "
        "WHERE table_schema=? AND table_name=?", [schema, table]).fetchone()[0] > 0


def _rows(con, sql, params=None):
    cur = con.execute(sql, params or [])
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def chain_company_fails(con: duckdb.DuckDBPyConnection, company_number: str | None = None) -> Chain:
    """A company enters insolvency. What does the public sector lose?"""
    c = Chain("A company goes bust", "an insolvency notice is published", "entity")

    if _has(con, "silver", "supplier_register"):
        n = con.execute("SELECT count(DISTINCT company_number) FROM silver.supplier_register "
                        "WHERE company_number IS NOT NULL").fetchone()[0]
        c.steps.append(Step("Watchman", "which public suppliers are on the register?",
                            f"{n:,} companies with a company number", n))

    if _has(con, "silver", "care_location"):
        rows = _rows(con, """SELECT provider, company_number, count(*) AS locations,
            sum(beds) AS beds, count(DISTINCT local_authority) AS authorities
            FROM silver.care_location WHERE company_number IS NOT NULL AND beds > 0
            GROUP BY provider, company_number ORDER BY authorities DESC LIMIT 3""")
        c.steps.append(Step("Bellwether", "does it run care the public depends on?",
                            f"the largest identified provider spans "
                            f"{rows[0]['authorities']} authorities" if rows else "no care data",
                            len(rows), rows))

    if _has(con, "silver", "procurement_award"):
        rows = _rows(con, """SELECT supplier, company_number, count(*) AS awards,
            round(sum(value)) AS value, count(DISTINCT buyer) AS buyers
            FROM silver.procurement_award WHERE company_number IS NOT NULL
            GROUP BY supplier, company_number ORDER BY awards DESC LIMIT 3""")
        c.steps.append(Step("Sentinel", "which contracts and buyers are exposed?",
                            f"top identified supplier holds {rows[0]['awards']} awards "
                            f"across {rows[0]['buyers']} buyers" if rows else "no award data",
                            len(rows), rows))
    return c


def chain_development_approved(con: duckdb.DuckDBPyConnection) -> Chain:
    """One planning decision, six systems."""
    c = Chain("A council approves housing", "a planning decision is published", "place")

    if _has(con, "gold", "plumbline_quarter"):
        from .systems import plumbline as P
        h, st, md, dd = P.national_gap(con, since="2023")
        c.steps.append(Step("Plumbline", "was it decided within the legal deadline?",
                            f"{st}% were, against a published headline of {h}%", 1))

    if _has(con, "silver", "contribution"):
        total, located = con.execute(
            "SELECT round(sum(amount)), count(*) FILTER (WHERE has_geometry) "
            "FROM silver.contribution").fetchone()
        c.steps.append(Step("Ledger", "what did the developer agree to pay, and where?",
                            f"£{total:,.0f} recorded, {located} of it mappable", 1))

    if _has(con, "silver", "flood_objection"):
        n, against = con.execute("""SELECT count(*), count(*) FILTER (
            WHERE outcome = 'Permission granted against Environment Agency advice')
            FROM silver.flood_objection""").fetchone()
        c.steps.append(Step("Highwater", "did a flood objection stand against it?",
                            f"{against} of {n:,} objections were overridden", against))

    if _has(con, "silver", "water_quality_objection"):
        n = con.execute("SELECT count(*) FROM silver.water_quality_objection").fetchone()[0]
        c.steps.append(Step("Sightline", "was other expert advice followed?",
                            f"{n} water quality objections, none with a recorded outcome", n))

    if _has(con, "gold", "catchment_district"):
        d, u = con.execute("""SELECT count(*), round(100.0*sum(pupils)/nullif(sum(capacity),0),1)
            FROM gold.catchment_district""").fetchone()
        c.steps.append(Step("Catchment", "are there school places for the children?",
                            f"{u}% of places already used across {d} districts", d))

    if _has(con, "gold", "lastmile_authority"):
        from .systems import lastmile as LM
        nb_p, nb_g, nb_pct, ot_p, ot_pct = LM.comparison(con)
        c.steps.append(Step("Lastmile", "will the homes have decent broadband?",
                            f"{nb_pct}% in new-build postcodes against {ot_pct}% elsewhere", 1))
    return c


def chain_reference_reissued(con: duckdb.DuckDBPyConnection) -> Chain:
    """The same repair, in four industries."""
    c = Chain("A regulator reissues its reference numbers",
              "identifiers change and series break", "entity")
    if _has(con, "silver", "storm_overflow"):
        n = con.execute("SELECT count(*) FROM silver.storm_overflow").fetchone()[0]
        c.steps.append(Step("Baseline", "sewage: can an overflow be tracked across 2024?",
                            f"{n:,} outlets, bridged on the pre-2024 identifier", n))
    if _has(con, "gold", "junction_register"):
        adv, ret = con.execute("""SELECT sum(catalogue_records), sum(rows)
            FROM gold.junction_register""").fetchone()
        c.steps.append(Step("Junction", "electricity: are the registers comparable?",
                            f"{adv:,} advertised, {ret:,} served through the open route", ret))
    if _has(con, "silver", "care_location"):
        multi = con.execute("""SELECT count(*) FROM (
            SELECT company_number FROM silver.care_location
            WHERE company_number IS NOT NULL GROUP BY company_number
            HAVING count(DISTINCT provider) > 1)""").fetchone()[0]
        c.steps.append(Step("Bellwether", "care: does one company trade as several?",
                            f"{multi} company numbers appear under more than one name", multi))
    return c


ALL: tuple[Callable, ...] = (chain_company_fails, chain_development_approved,
                             chain_reference_reissued)


def run_all(con: duckdb.DuckDBPyConnection) -> list[Chain]:
    return [fn(con) for fn in ALL]


def reuse_summary(con: duckdb.DuckDBPyConnection) -> dict:
    """Which systems lean on which spine -- the compounding, counted."""
    place = ["catchment", "ledger", "highwater", "plumbline", "lastmile", "bulwark", "compass"]
    entity = ["sentinel", "watchman", "bellwether"]
    both = ["junction", "baseline", "sightline"]
    built = set()
    for t in ("catchment_district", "ledger_purpose", "highwater_trend", "plumbline_quarter",
              "lastmile_authority", "bulwark_authority", "compass_trend", "sentinel_method",
              "watchman_exposure", "bellwether_group", "junction_register",
              "baseline_company", "sightline_reason"):
        if _has(con, "gold", t):
            built.add(t.split("_")[0])
    return {"place_spine_users": sorted(set(place) & built),
            "entity_spine_users": sorted(set(entity) & built),
            "both_spines": sorted(set(both) & built),
            "systems_built": len(built)}
