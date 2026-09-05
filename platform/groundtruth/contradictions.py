"""Where two official records disagree.

Government data contradicts itself routinely: a project a council calls complete
is active in the contract register and under construction in the planning data.
The instinct is to pick a winner, and the instinct is wrong. This platform has
no standing to declare which arm of government is right, and a resolver that
quietly picks one destroys the most useful signal in the corpus -- that the
disagreement exists at all.

So the output of this module is never "the answer is X". It is "these two
records disagree, here is each one, here is where each came from".

The checks below compare quantities the platform holds twice, by two routes.
That is not a contrived exercise: every one of them is a number a reader could
find on two different screens of this system, and a platform that publishes both
without ever comparing them is asserting a consistency it has not tested.

A check whose tables are absent is reported as *unrun*, not as agreement. An
untested claim and a tested one that passed must never look the same.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import duckdb


@dataclass(frozen=True)
class Check:
    """Two routes to one quantity.

    ``sql`` must return ``subject``, ``left_value`` and ``right_value``. It may
    return ``detail``. Rows where the two values agree are discarded by the
    runner, so a check returning nothing means the two routes agree everywhere.
    """
    id: str
    quantity: str
    left: str                     # human description of the first route
    right: str                    # and the second
    tables: tuple[str, ...]
    sql: str
    tolerance: float = 0.0        # absolute; rounding in a published table is not a contradiction
    note: str = ""


@dataclass
class Disagreement:
    check: str
    quantity: str
    subject: str
    left_value: float | None
    right_value: float | None
    left: str
    right: str
    detail: str = ""

    @property
    def difference(self) -> float | None:
        if self.left_value is None or self.right_value is None:
            return None
        return self.right_value - self.left_value

    @property
    def pct(self) -> float | None:
        if not self.left_value:
            return None
        d = self.difference
        return None if d is None else round(100.0 * d / self.left_value, 2)


CHECKS: tuple[Check, ...] = (
    Check(
        id="catchment-school-count",
        quantity="schools in a district",
        left="gold.catchment_district.schools, the district summary",
        right="mainstream rows in gold.catchment_school for that district",
        tables=("gold.catchment_district", "gold.catchment_school"),
        sql="""
            SELECT d.lad_code AS subject,
                   d.schools  AS left_value,
                   count(s.urn) AS right_value,
                   d.lad_name AS detail
            FROM gold.catchment_district d
            LEFT JOIN gold.catchment_school s
              ON s.lad_code = d.lad_code AND s.mainstream
            GROUP BY d.lad_code, d.schools, d.lad_name
        """,
        note="the summary counts mainstream schools only, so the detail is "
             "filtered to match. Comparing it to every row instead reports 294 "
             "false contradictions -- the specialist settings -- which is how "
             "this check was first written.",
    ),
    Check(
        id="lastmile-premises",
        quantity="premises in a district",
        left="gold.lastmile_authority.premises, the authority summary",
        right="sum of gold.lastmile_postcode.premises for that district",
        tables=("gold.lastmile_authority", "gold.lastmile_postcode"),
        sql="""
            SELECT a.lad_code AS subject,
                   a.premises AS left_value,
                   coalesce(sum(p.premises), 0) AS right_value,
                   a.lad_name AS detail
            FROM gold.lastmile_authority a
            LEFT JOIN gold.lastmile_postcode p ON p.lad_code = a.lad_code
            GROUP BY a.lad_code, a.premises, a.lad_name
        """,
    ),
    Check(
        id="highwater-objections",
        quantity="flood objections in an authority",
        left="gold.highwater_district.objections, keyed on the district code",
        right="gold.highwater_authority.objections, keyed on the authority name",
        tables=("gold.highwater_district", "gold.highwater_authority",
                "gold.catchment_district"),
        sql="""
            SELECT d.lad_code AS subject,
                   d.objections AS left_value,
                   a.objections AS right_value,
                   n.lad_name AS detail
            FROM gold.highwater_district d
            JOIN gold.catchment_district n ON n.lad_code = d.lad_code
            JOIN gold.highwater_authority a
              ON a.lpa = n.lad_name
              OR a.lpa = n.lad_name || ' Council'
              OR a.lpa = n.lad_name || ' Borough Council'
              OR a.lpa = n.lad_name || ' District Council'
        """,
        note="a code-keyed and a name-keyed view of one system; a mismatch here "
             "is usually the name match, which is the point of checking it",
    ),
    Check(
        id="bulwark-assets",
        quantity="flood defence assets in an authority",
        left="gold.bulwark_district.assets, keyed on the district code",
        right="gold.bulwark_authority.assets, keyed on the authority name",
        tables=("gold.bulwark_district", "gold.bulwark_authority"),
        sql="""
            SELECT d.lad_code AS subject,
                   d.assets    AS left_value,
                   a.assets    AS right_value,
                   d.lad_name  AS detail
            FROM gold.bulwark_district d
            JOIN gold.bulwark_authority a ON a.local_authority = d.lad_name
        """,
    ),
    Check(
        id="ledger-located",
        quantity="developer contributions carrying a location",
        left="gold.ledger_authority.with_location, from the contribution's own geometry",
        right="contributions joined to silver.agreement_location via the agreement",
        tables=("gold.ledger_authority", "silver.contribution",
                "silver.agreement_location", "silver.planning_authority"),
        sql="""
            SELECT l.authority AS subject,
                   l.with_location AS left_value,
                   count(loc.agreement) AS right_value,
                   'contribution geometry vs agreement join' AS detail
            FROM gold.ledger_authority l
            LEFT JOIN silver.planning_authority pa ON pa.name = l.authority
            LEFT JOIN silver.contribution c ON c.organisation_entity = pa.entity
            LEFT JOIN silver.agreement_location loc
                   ON loc.agreement = c.agreement
                  AND loc.organisation_entity = c.organisation_entity
            GROUP BY l.authority, l.with_location
        """,
        note="these disagree by construction once the agreement join runs: the "
             "left is what the publisher stated, the right is what the platform "
             "recovered. Both are true and they measure different things.",
    ),
    Check(
        id="sentinel-award-total",
        quantity="procurement awards in total",
        left="sum of gold.sentinel_method.awards, the published grouping",
        right="rows in silver.procurement_award, the loaded corpus",
        tables=("gold.sentinel_method", "silver.procurement_award"),
        sql="""
            SELECT 'all awards' AS subject,
                   (SELECT sum(awards) FROM gold.sentinel_method) AS left_value,
                   (SELECT count(*) FROM silver.procurement_award) AS right_value,
                   'grouping against the corpus it groups' AS detail
        """,
        note="a grouping that does not account for every award it groups is "
             "dropping rows somewhere between silver and gold",
    ),
    Check(
        id="sentinel-buyer-coverage",
        quantity="awards represented in the buyer view",
        left="sum of gold.sentinel_buyer.awards",
        right="awards in silver.procurement_award naming a buyer",
        tables=("gold.sentinel_buyer", "silver.procurement_award"),
        sql="""
            SELECT 'all buyers' AS subject,
                   (SELECT sum(awards) FROM gold.sentinel_buyer) AS left_value,
                   (SELECT count(*) FROM silver.procurement_award
                     WHERE buyer IS NOT NULL AND trim(buyer) <> '') AS right_value,
                   'buyer view against every award with a buyer' AS detail
        """,
        note="these are expected to differ: Sentinel's buyer view holds the "
             "buyers that meet its threshold, not all of them. The check exists "
             "so the size of that gap is stated rather than discovered by a "
             "reader adding up two screens.",
    ),
)


def _exists(con: duckdb.DuckDBPyConnection, qualified: str) -> bool:
    schema, _, table = qualified.partition(".")
    return con.execute(
        "SELECT count(*) FROM information_schema.tables "
        "WHERE table_schema = ? AND table_name = ?", [schema, table]
    ).fetchone()[0] > 0


def run_check(con: duckdb.DuckDBPyConnection, check: Check,
              limit: int = 50) -> dict:
    """Run one check. Never decides which side is correct."""
    missing = [t for t in check.tables if not _exists(con, t)]
    if missing:
        return {"check": check.id, "quantity": check.quantity, "run": False,
                "reason": f"needs {', '.join(missing)}", "disagreements": []}
    try:
        cur = con.execute(check.sql)
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    except duckdb.Error as exc:
        # A check that no longer binds is a broken check, not agreement.
        return {"check": check.id, "quantity": check.quantity, "run": False,
                "reason": f"check failed to run: {str(exc).splitlines()[0]}",
                "disagreements": []}

    found = []
    for r in rows:
        lv, rv = r.get("left_value"), r.get("right_value")
        if lv is None and rv is None:
            continue
        if lv is not None and rv is not None and abs(float(rv) - float(lv)) <= check.tolerance:
            continue
        found.append(Disagreement(
            check.id, check.quantity, str(r.get("subject")),
            None if lv is None else float(lv),
            None if rv is None else float(rv),
            check.left, check.right, str(r.get("detail") or "")))
    found.sort(key=lambda d: abs(d.difference or 0), reverse=True)
    return {"check": check.id, "quantity": check.quantity, "run": True,
            "compared": len(rows), "disagreed": len(found),
            "agreement_pct": (round(100.0 * (len(rows) - len(found)) / len(rows), 2)
                              if rows else None),
            "note": check.note,
            "disagreements": [d.__dict__ | {"difference": d.difference, "pct": d.pct}
                              for d in found[:limit]]}


def run_all(con: duckdb.DuckDBPyConnection, limit: int = 10) -> dict:
    results = [run_check(con, c, limit=limit) for c in CHECKS]
    ran = [r for r in results if r["run"]]
    return {
        "checks": len(results),
        "run": len(ran),
        "unrun": [{"check": r["check"], "reason": r["reason"]}
                  for r in results if not r["run"]],
        "with_disagreement": sum(1 for r in ran if r["disagreed"]),
        "total_disagreements": sum(r["disagreed"] for r in ran),
        "results": results,
    }
