"""Highwater -- flood risk objections against what actually happened.

The Environment Agency objects to planning applications on flood risk grounds
and publishes the list. Two defects make it far less useful than it should be:

  * **No location.** The file carries a planning authority name and the
    authority's own reference. There is no address, no postcode and no
    coordinate on any of 23,519 rows, so an objection cannot be put on a map
    or joined to a flood zone. This is the gap the place spine exists to close,
    and closing it requires the authority's own planning register -- the
    reference is the key, but the register is where the location lives.
  * **No outcome on 7,011 rows.** The Agency records what it objected to, then
    frequently never learns what the authority decided.

What can be computed today is the outcome picture for the rows that do have one,
the override rate over time, and how many homes were involved. Every figure is
published against the subset it was computed over.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import duckdb

from ..ods import table
from ..store import insert_many

SHEET = "Flood_Risk"
COL = {"lpa": 0, "website": 1, "reference": 2, "description": 3,
       "units": 4, "year_objection": 5, "year_decision": 6, "outcome": 7}

FOLLOWED = "Environment Agency advice followed"
AGAINST = "Permission granted against Environment Agency advice"
UNKNOWN = "Outcome currently unknown"


@dataclass(frozen=True)
class Coverage:
    rows: int
    with_outcome: int
    with_units: int
    with_reference: int
    with_website: int

    def pct(self, n: int) -> float:
        return 100 * n / self.rows if self.rows else 0.0


def normalise_year(v: str | None) -> str | None:
    """The publisher switches from 2020-21 to 2021/22 partway through the series.

    Left alone, the same financial year appears as two distinct values and any
    time series silently splits in half.
    """
    if not v:
        return None
    s = str(v).strip()
    m = re.match(r"^(\d{4})\s*[-/]\s*(\d{2,4})$", s)
    if not m:
        return None
    start, end = m.group(1), m.group(2)
    return f"{start}-{end[-2:]}"


def _num(v):
    try:
        return float(str(v).strip())
    except (TypeError, ValueError):
        return None


def _text(v):
    s = str(v).strip() if v is not None else ""
    return s or None


def load(con: duckdb.DuckDBPyConnection, ods_path: Path) -> Coverage:
    rows = []
    # Read the flood risk sheet only. The workbook also holds a water quality
    # sheet with a similar shape; without this filter its rows append to the
    # flood risk data and inflate every total.
    for _h, r in table(ods_path, min_header_cells=6, sheet=SHEET):
        def g(k):
            i = COL[k]
            return r[i] if i < len(r) else None
        lpa = _text(g("lpa"))
        if not lpa:
            continue
        rows.append((
            lpa, _text(g("website")), _text(g("reference")), _text(g("description")),
            _num(g("units")), normalise_year(g("year_objection")),
            normalise_year(g("year_decision")), _text(g("outcome")),
        ))

    con.execute("DROP TABLE IF EXISTS silver.flood_objection")
    con.execute("""
        CREATE TABLE silver.flood_objection (
          lpa VARCHAR, lpa_website VARCHAR, reference VARCHAR, description VARCHAR,
          residential_units DOUBLE, year_objection VARCHAR, year_decision VARCHAR,
          outcome VARCHAR
        )""")
    insert_many(con, "INSERT INTO silver.flood_objection VALUES (?,?,?,?,?,?,?,?)", rows)

    c = con.execute(f"""
        SELECT count(*),
               count(*) FILTER (WHERE outcome IS NOT NULL AND outcome <> '{UNKNOWN}'),
               count(residential_units), count(reference), count(lpa_website)
        FROM silver.flood_objection""").fetchone()
    return Coverage(*c)


def build(con: duckdb.DuckDBPyConnection) -> None:
    con.execute("DROP TABLE IF EXISTS gold.highwater_outcome")
    con.execute("""
        CREATE TABLE gold.highwater_outcome AS
        SELECT COALESCE(outcome, 'not stated') AS outcome,
               count(*) AS objections,
               round(sum(residential_units)) AS residential_units
        FROM silver.flood_objection GROUP BY 1 ORDER BY objections DESC
    """)

    # Override rate over time, computed only over decided cases. Including
    # unknowns in the denominator would make the rate look better every time
    # the Agency fails to learn an outcome.
    con.execute(f"""
        CREATE OR REPLACE TABLE gold.highwater_trend AS
        SELECT year_objection AS year,
               count(*)                                          AS objections,
               count(*) FILTER (WHERE outcome = '{FOLLOWED}')    AS advice_followed,
               count(*) FILTER (WHERE outcome = '{AGAINST}')     AS granted_against,
               count(*) FILTER (WHERE outcome = '{UNKNOWN}')     AS outcome_unknown,
               round(100.0 * count(*) FILTER (WHERE outcome = '{AGAINST}')
                     / nullif(count(*) FILTER (WHERE outcome IN ('{FOLLOWED}','{AGAINST}')), 0), 1)
                                                                 AS override_rate_pct,
               round(100.0 * count(*) FILTER (WHERE outcome = '{UNKNOWN}') / count(*), 1)
                                                                 AS unknown_pct
        FROM silver.flood_objection
        WHERE year_objection IS NOT NULL
        GROUP BY 1 ORDER BY 1
    """)

    con.execute(f"""
        CREATE OR REPLACE TABLE gold.highwater_authority AS
        SELECT lpa,
               count(*)                                       AS objections,
               count(*) FILTER (WHERE outcome = '{AGAINST}')  AS granted_against,
               count(*) FILTER (WHERE outcome = '{UNKNOWN}')  AS outcome_unknown,
               round(sum(residential_units))                  AS residential_units,
               round(100.0 * count(*) FILTER (WHERE outcome = '{AGAINST}')
                     / nullif(count(*) FILTER (WHERE outcome IN ('{FOLLOWED}','{AGAINST}')), 0), 1)
                                                              AS override_rate_pct
        FROM silver.flood_objection
        GROUP BY lpa HAVING count(*) >= 20
        ORDER BY override_rate_pct DESC NULLS LAST
    """)


def locatability(con: duckdb.DuckDBPyConnection) -> dict:
    """What it would take to put these objections on a map."""
    row = con.execute("""
        SELECT count(*), count(reference), count(lpa_website), count(DISTINCT lpa)
        FROM silver.flood_objection""").fetchone()
    return {"objections": row[0], "with_reference": row[1],
            "with_public_register_link": row[2], "authorities": row[3]}
