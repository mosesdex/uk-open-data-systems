"""Sightline -- whether expert planning advice is followed.

Statutory consultees advise planning authorities. Government is reducing that
involvement. The question nobody can currently answer is what the advice
achieved: how often it was followed, and what happened when it was not.

The Environment Agency publishes two objection lists in one workbook, and the
contrast between them is the finding:

  * **Flood risk** -- 23,336 objections, and an outcome column. The Agency
    learns what the authority decided in 69.9% of cases.
  * **Water quality** -- 181 objections, an objection *reason* column, and **no
    outcome column at all**. Not "unknown" for some: the field does not exist,
    so the outcome of every water quality objection is untracked.

A consultee regime being cut back on the grounds that it adds delay has, for one
of its two published objection streams, no evidence base whatsoever about
whether the advice was taken.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import duckdb

from ..ods import table, sheets
from ..store import insert_many

FLOOD_SHEET = "Flood_Risk"
WATER_SHEET = "Water_Quality"
WQ_COL = {"lpa": 0, "reference": 1, "description": 2, "reason": 3}


@dataclass(frozen=True)
class Stream:
    name: str
    objections: int
    has_outcome_field: bool
    outcome_known: int

    @property
    def tracked_pct(self) -> float:
        if not self.has_outcome_field or not self.objections:
            return 0.0
        return 100 * self.outcome_known / self.objections


def _text(v):
    s = str(v).strip() if v is not None else ""
    return s or None


def load_water_quality(con: duckdb.DuckDBPyConnection, ods_path: Path) -> int:
    rows = []
    for _h, r in table(ods_path, min_header_cells=4, sheet=WATER_SHEET):
        def g(k):
            i = WQ_COL[k]
            return _text(r[i]) if i < len(r) else None
        lpa = g("lpa")
        if not lpa or lpa.startswith("Local planning authority"):
            continue
        rows.append((lpa, g("reference"), g("description"), g("reason")))

    con.execute("DROP TABLE IF EXISTS silver.water_quality_objection")
    con.execute("""
        CREATE TABLE silver.water_quality_objection (
          lpa VARCHAR, reference VARCHAR, description VARCHAR, reason VARCHAR
        )""")
    insert_many(con, "INSERT INTO silver.water_quality_objection VALUES (?,?,?,?)", rows)
    return len(rows)


def streams(con: duckdb.DuckDBPyConnection, ods_path: Path) -> list[Stream]:
    """The two advice streams, side by side."""
    present = set(sheets(ods_path))
    out: list[Stream] = []

    flood = con.execute("""
        SELECT count(*), count(*) FILTER (
            WHERE outcome IS NOT NULL AND outcome <> 'Outcome currently unknown')
        FROM silver.flood_objection""").fetchone()
    out.append(Stream("flood risk", flood[0], True, flood[1]))

    if WATER_SHEET in present:
        n = con.execute("SELECT count(*) FROM silver.water_quality_objection").fetchone()[0]
        # There is no outcome column on this sheet at all.
        out.append(Stream("water quality", n, False, 0))
    return out


def build(con: duckdb.DuckDBPyConnection) -> None:
    con.execute("DROP TABLE IF EXISTS gold.sightline_reason")
    con.execute("""
        CREATE TABLE gold.sightline_reason AS
        SELECT COALESCE(reason, 'not stated') AS reason,
               count(*) AS objections,
               count(DISTINCT lpa) AS authorities
        FROM silver.water_quality_objection
        GROUP BY 1 ORDER BY objections DESC
    """)

    # Authorities appearing in both streams: where one consultee raised two
    # different concerns, only one of which is ever followed up.
    con.execute("DROP TABLE IF EXISTS gold.sightline_authority")
    con.execute("""
        CREATE TABLE gold.sightline_authority AS
        SELECT COALESCE(f.lpa, w.lpa)                 AS lpa,
               COALESCE(f.flood_objections, 0)        AS flood_objections,
               COALESCE(f.flood_unknown, 0)           AS flood_outcome_unknown,
               COALESCE(w.water_objections, 0)        AS water_objections
        FROM (SELECT lpa, count(*) AS flood_objections,
                     count(*) FILTER (WHERE outcome = 'Outcome currently unknown')
                       AS flood_unknown
              FROM silver.flood_objection GROUP BY lpa) f
        FULL OUTER JOIN
             (SELECT lpa, count(*) AS water_objections
              FROM silver.water_quality_objection GROUP BY lpa) w
        ON f.lpa = w.lpa
        ORDER BY water_objections DESC, flood_objections DESC
    """)
