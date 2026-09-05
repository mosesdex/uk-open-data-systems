"""What should be joinable, and is not.

Coverage figures answer "how much of this table is populated". They do not
answer the question a reader actually has, which is "can this platform follow a
decision from permission to consequence, and if not, where does the trail stop".

So this module states, per chain, the fields a question needs and then measures
which of them the corpus supplies. The output is a gap: the chain, the step that
breaks it, and whether the break is something the platform could fix or
something no publisher publishes.

That distinction is the whole value of the exercise. "Groundtruth has not built
this yet" and "the United Kingdom does not record this" look identical in an
empty result and are completely different facts. The first is a backlog item.
The second is a finding about the state of national data infrastructure, and it
is arguably the most useful thing this platform produces -- because nobody else
is positioned to measure it.

Nothing here estimates. A step is measured against the database, and a step
whose table is absent is reported as unmeasured rather than assumed broken.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import duckdb

# Why a step is broken. The categories are deliberately few and sharp.
PLATFORM = "platform"        # we could fix this; the data exists somewhere
PUBLISHER = "publisher"      # the data exists but this publisher withholds it
NOWHERE = "nowhere"          # nobody in the UK publishes this at all
UNMEASURED = "unmeasured"    # the table is absent, so nothing is claimed


@dataclass(frozen=True)
class Step:
    """One link a chain depends on.

    ``table`` and ``column`` name where the fact would live. ``absent_because``
    is stated for steps known to be unavailable, and must be one of the four
    categories -- an unexplained gap is a to-do note, not a finding.
    """
    name: str
    question: str
    table: str = ""
    column: str = ""
    absent_because: str = ""
    reason: str = ""

    @property
    def measurable(self) -> bool:
        return bool(self.table and self.column)


@dataclass(frozen=True)
class Chain:
    name: str
    asks: str
    steps: tuple[Step, ...]
    matters: str = ""


CHAINS: tuple[Chain, ...] = (
    Chain(
        name="permission-to-consequence",
        asks="A site was permitted. What was promised, was it paid, and what "
             "was built?",
        matters="This is the question local government is least able to answer "
                "about itself, and every step of it is meant to be public.",
        steps=(
            Step("the permission", "which application?",
                 "silver.developer_agreement", "planning_application"),
            Step("the site", "where is it?",
                 "silver.agreement_location", "lad"),
            Step("the promise", "what was agreed?",
                 "silver.contribution", "amount"),
            Step("the payment", "was it received?",
                 "silver.contribution_transaction", "status"),
            Step("completion", "was it built, and when?",
                 absent_because=NOWHERE,
                 reason="Construction completion is not published against a "
                        "planning reference anywhere in England. The permission "
                        "trail ends at approval."),
            Step("occupancy", "is anyone living there?",
                 absent_because=NOWHERE,
                 reason="Actual occupancy is not published against a planning "
                        "reference. New-build sales are the nearest proxy and "
                        "are a different measurement."),
            Step("the infrastructure", "what did the money buy?",
                 absent_because=PUBLISHER,
                 reason="Authorities record the contribution's purpose but not "
                        "the scheme it funded, so money cannot be followed to a "
                        "school place or a road."),
        ),
    ),
    Chain(
        name="supplier-to-risk",
        asks="A company holds public contracts. How exposed is the public "
             "sector if it fails?",
        matters="Watchman and Bellwether both depend on this chain, and it is "
                "the one an insolvency makes urgent overnight.",
        steps=(
            Step("the award", "who won what?",
                 "silver.procurement_award", "supplier"),
            Step("the company", "which registered body is that?",
                 "silver.procurement_award", "company_number"),
            Step("the ownership", "who controls it?",
                 "silver.psc", "name"),
            Step("the services", "what else do they run?",
                 "silver.care_location", "company_number"),
            Step("the distress signal", "are they failing?",
                 "gold.watchman_distress", "company_status"),
            Step("the contract value at risk", "how much is exposed?",
                 absent_because=PUBLISHER,
                 reason="Award values are published; remaining contract term "
                        "and renewal status are not, so exposure cannot be "
                        "reduced to a figure that means anything."),
        ),
    ),
    Chain(
        name="tender-to-collusion",
        asks="Were these bidders competing?",
        matters="Sentinel can measure concentration and shared control. It "
                "cannot run the standard collusion screens, and the reason is "
                "not a Groundtruth limitation.",
        steps=(
            Step("the award", "who won?",
                 "silver.procurement_award", "supplier"),
            Step("the method", "how was it let?",
                 "silver.procurement_award", "method"),
            Step("shared control", "do the bidders share a director?",
                 "silver.psc", "company_number"),
            Step("the bid prices", "what did each bidder ask?",
                 absent_because=NOWHERE,
                 reason="Bid prices are not published in UK procurement data. "
                        "No price-based screen can be built by anyone, here or "
                        "elsewhere."),
            Step("the bidder count", "how many bid?",
                 absent_because=NOWHERE,
                 reason="Bidder counts are not published either, so the "
                        "single-bidder screen is unavailable nationally."),
        ),
    ),
    Chain(
        name="place-to-pressure",
        asks="Is this district under simultaneous pressure?",
        matters="Every input exists. What is missing is that they are published "
                "at different geographies, which is a joining problem rather "
                "than a data one.",
        steps=(
            Step("school places", "are schools full?",
                 "gold.catchment_district", "utilisation_pct"),
            Step("connectivity", "is it served?",
                 "gold.lastmile_authority", "gigabit_pct"),
            Step("flood exposure", "is it at risk?",
                 "gold.highwater_district", "objections"),
            Step("sewage", "is the water clean?",
                 "gold.baseline_district", "adjusted_spills"),
            Step("care capacity", "who provides care here?",
                 absent_because=PLATFORM,
                 reason="Bellwether is published against 152 upper-tier "
                        "authorities and this chain is keyed to 317 districts. "
                        "The platform holds no district-to-county mapping, so "
                        "the join is unmade rather than impossible."),
            Step("SEND demand", "is specialist provision under pressure?",
                 absent_because=PLATFORM,
                 reason="Compass is likewise upper-tier. Same missing mapping."),
        ),
    ),
)


def _column_state(con: duckdb.DuckDBPyConnection, table: str,
                  column: str) -> dict:
    """Is the column there, and how much of it is populated?

    Presence and population are reported separately: a column that exists and
    is empty is a different finding from one that was never created, and
    collapsing them is how a platform ends up claiming coverage it lacks.
    """
    schema, _, name = table.partition(".")
    has_table = con.execute(
        "SELECT count(*) FROM information_schema.tables "
        "WHERE table_schema = ? AND table_name = ?", [schema, name]).fetchone()[0] > 0
    if not has_table:
        return {"table_exists": False, "column_exists": False,
                "rows": None, "populated": None, "populated_pct": None}
    has_col = con.execute(
        "SELECT count(*) FROM information_schema.columns "
        "WHERE table_schema = ? AND table_name = ? AND column_name = ?",
        [schema, name, column]).fetchone()[0] > 0
    if not has_col:
        return {"table_exists": True, "column_exists": False,
                "rows": None, "populated": None, "populated_pct": None}
    rows, populated = con.execute(
        f'SELECT count(*), count("{column}") FROM {table}').fetchone()
    return {"table_exists": True, "column_exists": True,
            "rows": rows, "populated": populated,
            "populated_pct": round(100.0 * populated / rows, 2) if rows else 0.0}


def measure(con: duckdb.DuckDBPyConnection, chain: Chain,
            threshold: float = 1.0) -> dict:
    """Walk a chain and report where it stops.

    ``threshold`` is the population percentage below which a step counts as
    broken. It defaults to 1%, not 50%: a step populated on 0.2% of rows is not
    a working join, and rounding it up to "present" is the overclaim this
    platform exists to avoid.
    """
    results = []
    broke_at = None
    for step in chain.steps:
        if not step.measurable:
            state = {"table_exists": None, "column_exists": None,
                     "rows": None, "populated": None, "populated_pct": None}
            ok = False
            because = step.absent_because or NOWHERE
        else:
            state = _column_state(con, step.table, step.column)
            if not state["table_exists"] or not state["column_exists"]:
                ok, because = False, (step.absent_because or UNMEASURED)
            else:
                ok = (state["populated_pct"] or 0.0) >= threshold
                because = "" if ok else (step.absent_because or PLATFORM)
        results.append({"step": step.name, "question": step.question,
                        "table": step.table or None, "column": step.column or None,
                        "available": ok, "absent_because": because or None,
                        "reason": step.reason or None, **state})
        if not ok and broke_at is None:
            broke_at = step.name

    reachable = 0
    for r in results:
        if not r["available"]:
            break
        reachable += 1
    return {
        "chain": chain.name, "asks": chain.asks, "matters": chain.matters,
        "steps": len(results), "steps_available": sum(1 for r in results if r["available"]),
        "reachable_depth": reachable,
        "breaks_at": broke_at,
        "complete": broke_at is None,
        "detail": results,
    }


def report(con: duckdb.DuckDBPyConnection, threshold: float = 1.0) -> dict:
    """Every chain, and a tally of why the broken ones break."""
    chains = [measure(con, c, threshold) for c in CHAINS]
    tally: dict[str, int] = {}
    for c in chains:
        for step in c["detail"]:
            if not step["available"] and step["absent_because"]:
                tally[step["absent_because"]] = tally.get(step["absent_because"], 0) + 1
    fixable = [
        {"chain": c["chain"], "step": s["step"], "reason": s["reason"]}
        for c in chains for s in c["detail"]
        if not s["available"] and s["absent_because"] == PLATFORM
    ]
    structural = [
        {"chain": c["chain"], "step": s["step"], "reason": s["reason"]}
        for c in chains for s in c["detail"]
        if not s["available"] and s["absent_because"] == NOWHERE
    ]
    return {
        "chains": len(chains),
        "complete": sum(1 for c in chains if c["complete"]),
        "broken": sum(1 for c in chains if not c["complete"]),
        "by_cause": tally,
        "fixable_here": fixable,
        "not_published_anywhere": structural,
        "detail": chains,
    }
