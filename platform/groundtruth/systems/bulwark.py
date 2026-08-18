"""Bulwark -- who owns and maintains flood defences.

England has 141,468 recorded flood defences. The owner is "Unknown" on 73.7% of
them. That number is usually quoted as a scandal, and it is a real gap, but it
is also the wrong question to lead with.

Measured here: **the maintainer is known for 90.9%** of assets. When a defence
fails, the operational question is who is responsible for maintaining it, and
that is answered for nine assets in ten. It is legal *ownership* that is
missing. Bulwark reports both, and does not let the more alarming number stand
in for the more useful one.

The second finding is about condition. Only **24.9%** of assets carry a
condition grade at all, so any national condition statistic describes a quarter
of the estate. That coverage travels with every figure this system publishes.

A note on sources. The asset-management API at environment.data.gov.uk exposes
condition and inspection dates but **no owner field and no geometry**, so it
cannot answer this question. The spatial dataset published through the WFS
service carries owner, operator, maintainer and geometry for the full estate.
Same publisher, different endpoint, entirely different capability.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

import duckdb

from ..store import insert_many

UNKNOWN = "Unknown"
GRADES = ("1", "2", "3", "4", "5")


@dataclass(frozen=True)
class Coverage:
    total: int
    owner_known: int
    operator_known: int
    maintainer_known: int
    graded: int
    with_next_inspection: int

    def pct(self, n: int) -> float:
        return 100 * n / self.total if self.total else 0.0


def load(con: duckdb.DuckDBPyConnection, path: Path) -> int:
    rows = json.loads(Path(path).read_text())
    con.execute("DROP TABLE IF EXISTS silver.flood_defence")
    con.execute("""
        CREATE TABLE silver.flood_defence (
          asset_id VARCHAR, sub_type VARCHAR, purpose VARCHAR, protection VARCHAR,
          maintainer VARCHAR, operator VARCHAR, owner VARCHAR,
          current_condition VARCHAR, target_condition VARCHAR,
          last_inspection DATE, next_inspection DATE,
          local_authority VARCHAR, water_area VARCHAR, watercourse VARCHAR,
          length DOUBLE
        )""")

    def clean(v):
        if v is None:
            return None
        s = str(v).strip()
        return s or None

    parsed = failed = 0

    def dt(v):
        """Parse a publisher date, counting failures instead of hiding them.

        AIMS publishes DD/MM/YYYY, not ISO. Verified empirically rather than
        assumed: across 103,667 values the first component reaches 31 and the
        second never exceeds 12. An earlier version used fromisoformat, which
        returned None for every row and produced a confident, wrong claim that
        no inspection anywhere was overdue.
        """
        nonlocal parsed, failed
        s = clean(v)
        if not s:
            return None
        for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d/%m/%y"):
            try:
                out = datetime.strptime(s[:10], fmt).date()
                parsed += 1
                return out
            except ValueError:
                continue
        failed += 1
        return None

    insert_many(con, 
        "INSERT INTO silver.flood_defence VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        [(clean(r.get("asset_id")), clean(r.get("asset_sub_type")),
          clean(r.get("primary_purpose")), clean(r.get("protection_type")),
          clean(r.get("asset_maintainer")), clean(r.get("asset_operator")),
          clean(r.get("asset_owner")), clean(r.get("current_condition")),
          clean(r.get("target_condition")), dt(r.get("last_inspection_date")),
          dt(r.get("next_inspection_date")), clean(r.get("local_authority")),
          clean(r.get("water_management_area")), clean(r.get("water_course_name")),
          r.get("asset_length")) for r in rows])

    if failed and failed > parsed * 0.02:
        raise ValueError(
            f"date parsing failed on {failed:,} of {failed + parsed:,} values. "
            "The publisher has probably changed format -- fix the parser rather "
            "than shipping a statistic computed over the rows that happened to work."
        )
    return len(rows)


def coverage(con: duckdb.DuckDBPyConnection) -> Coverage:
    row = con.execute(f"""
        SELECT count(*),
               count(*) FILTER (WHERE owner      IS NOT NULL AND owner      <> '{UNKNOWN}'),
               count(*) FILTER (WHERE operator   IS NOT NULL AND operator   <> '{UNKNOWN}'),
               count(*) FILTER (WHERE maintainer IS NOT NULL AND maintainer <> '{UNKNOWN}'),
               count(*) FILTER (WHERE current_condition IN {GRADES}),
               count(*) FILTER (WHERE next_inspection IS NOT NULL)
        FROM silver.flood_defence""").fetchone()
    return Coverage(*row)


def build(con: duckdb.DuckDBPyConnection, today: date | None = None) -> None:
    today = today or date.today()
    con.execute("DROP TABLE IF EXISTS gold.bulwark_authority")
    con.execute(f"""
        CREATE TABLE gold.bulwark_authority AS
        SELECT
          COALESCE(local_authority, 'not stated')            AS local_authority,
          count(*)                                           AS assets,
          count(*) FILTER (WHERE maintainer IS NOT NULL
                             AND maintainer <> '{UNKNOWN}')  AS maintainer_known,
          count(*) FILTER (WHERE owner IS NOT NULL
                             AND owner <> '{UNKNOWN}')       AS owner_known,
          count(*) FILTER (WHERE current_condition IN {GRADES}) AS graded,
          -- condition statistics describe only the graded subset, so the
          -- denominator is stated rather than assumed
          round(avg(TRY_CAST(current_condition AS DOUBLE))
                FILTER (WHERE current_condition IN {GRADES}), 2) AS mean_condition,
          round(100.0 * count(*) FILTER (WHERE current_condition IN {GRADES})
                      / count(*), 1)                         AS graded_pct,
          count(*) FILTER (WHERE next_inspection IS NOT NULL
                             AND next_inspection < DATE '{today}') AS inspection_overdue
        FROM silver.flood_defence
        GROUP BY 1
        HAVING count(*) >= 20
        ORDER BY assets DESC
    """)

    con.execute("DROP TABLE IF EXISTS gold.bulwark_responsibility")
    con.execute("""
        CREATE TABLE gold.bulwark_responsibility AS
        SELECT COALESCE(maintainer, 'not stated') AS maintainer,
               count(*)                           AS assets,
               round(sum(length) / 1000.0, 1)     AS km,
               count(*) FILTER (WHERE next_inspection IS NOT NULL
                                  AND next_inspection < CURRENT_DATE) AS overdue
        FROM silver.flood_defence
        GROUP BY 1 ORDER BY assets DESC
    """)


def overdue(con: duckdb.DuckDBPyConnection, limit: int = 10):
    """Assets whose own next-inspection date has already passed."""
    return con.execute(f"""
        SELECT COALESCE(local_authority, 'not stated') AS la,
               count(*) AS overdue,
               min(next_inspection) AS oldest,
               count(*) FILTER (WHERE maintainer = '{UNKNOWN}') AS also_unmaintained
        FROM silver.flood_defence
        WHERE next_inspection IS NOT NULL AND next_inspection < CURRENT_DATE
        GROUP BY 1 ORDER BY overdue DESC LIMIT {limit}
    """).fetchall()
