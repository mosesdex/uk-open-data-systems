"""Plumbline -- planning performance measured against the statutory 13 weeks.

An authority reports that 91% of major applications were decided "in time" and
is judged compliant. The published figure counts an application as on time if it
met an *agreed extension*, not the statutory deadline. Measured against the
statutory 13 weeks alone, the same authority can be at a fraction of that.

Both numbers are true. Only one is the one people think they are reading, so
Plumbline always publishes them side by side, plus the extension rate that
explains the difference.

Statutory periods used here, from the published category breakdown:

  majors  13 weeks
  minors   8 weeks

A finding from building this. The source used to publish "decided within maximum
time", which is where agreed extensions land, and comparing it with the 13-week
columns gave the extension reliance directly. **That column was discontinued
after 2020** -- populated on 100% of rows in 2019, 0.3% by 2021, and nothing
since 2023. The field that made the distinction visible is no longer published.

So the comparison is now made between two columns that are still published:

  headline   decisions "in time" as a share of all major decisions, where
             in time includes agreed extensions and performance agreements
  statutory  major dwelling decisions reached within the statutory
             13 weeks, without an agreed extension

The scopes differ slightly -- the headline covers all majors, the statutory
figure covers major dwellings -- and both are labelled wherever they appear.

Two things the table's own structure settles. Its "PAs" are performance
agreements -- agreed extensions of time and planning performance agreements --
not prior approvals: listed building consents and advertisements carry them,
and neither can be a prior approval. And decisions made under one are
published with no time band, so the statutory figure counts them as outside
the 13 weeks. It is the share known to have been decided within the statutory
period without an extension. Agreeing an extension is lawful, which is why the
figure is not described as the legal deadline.
"""
from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from pathlib import Path

import duckdb

from ..store import insert_many

HEADER_ROW = 2          # 0-indexed: two title rows precede it

# Column headings, matched by exact text so a reordered release cannot silently
# shift the meaning of a number.
C_LPA = "LPANM"
C_LPACD = "LPACD"
C_QUARTER = "Quarter"
# The headline is every decision in time -- within the statutory period, or
# within an agreed extension -- over every decision. The table splits both
# halves by whether a performance agreement ("PAs") applied, so the in-time
# count is the two added together. Reading only the "(excluding PAs)" half left
# out the three quarters of major decisions made under an agreement.
C_MAJOR_DECISIONS = "Total decisions; major total (all)"
C_MAJOR_IN_TIME = "Total decisions in time; major total (excluding PAs)"
C_MAJOR_IN_TIME_PA = "Total decisions in time; major total (PAs only)"
C_MAJOR_PA = "Total decisions; major total (PAs only)"
C_MINOR_DECISIONS = "Total decisions; minor total (all)"
C_MINOR_IN_TIME = "Total decisions in time; minor total (excluding PAs)"
C_MINOR_IN_TIME_PA = "Total decisions in time; minor total (PAs only)"
C_MAJDW_8 = "Total decided within 8 weeks; major dwellings (excluding PAs)"
C_MAJDW_8_13 = "Total decided within 8 to 13 weeks; major dwellings (excluding PAs)"
C_MAJDW_MAX = "Total decided within maximum time; major dwellings (excluding PAs)"
C_MAJDW_TOTAL = "Total decisions; major dwellings (all)"
C_MAJDW_PA = "Total decisions; major dwellings (PAs only)"


@dataclass(frozen=True)
class Coverage:
    rows: int
    quarters: int
    authorities: int


def _n(v):
    try:
        return float(str(v).replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def load(con: duckdb.DuckDBPyConnection, ps2_csv: Path) -> Coverage:
    raw = Path(ps2_csv).read_text(encoding="utf-8-sig", errors="replace")
    reader = list(csv.reader(io.StringIO(raw)))
    header = [c.strip() for c in reader[HEADER_ROW]]
    idx = {name: i for i, name in enumerate(header) if name}

    missing = [c for c in (C_LPA, C_QUARTER, C_MAJOR_DECISIONS, C_MAJOR_IN_TIME,
                           C_MAJOR_IN_TIME_PA, C_MAJDW_TOTAL,
                           C_MAJDW_8, C_MAJDW_8_13, C_MAJDW_MAX) if c not in idx]
    if missing:
        raise ValueError(
            f"PS2 columns not found: {missing}. The publisher has changed the "
            "table; fix the mapping rather than computing against the wrong column."
        )

    def g(row, name):
        i = idx.get(name)
        return _n(row[i]) if i is not None and i < len(row) else None

    def both(row, a, b):
        # The two halves of an in-time count; absent only if both are.
        x, y = g(row, a), g(row, b)
        return None if x is None and y is None else (x or 0.0) + (y or 0.0)

    rows = []
    for row in reader[HEADER_ROW + 1:]:
        if not row or not str(row[idx[C_LPA]]).strip():
            continue
        rows.append((
            str(row[idx[C_LPA]]).strip(),
            str(row[idx[C_LPACD]]).strip() if C_LPACD in idx else None,
            str(row[idx[C_QUARTER]]).strip(),
            g(row, C_MAJOR_DECISIONS), both(row, C_MAJOR_IN_TIME, C_MAJOR_IN_TIME_PA),
            g(row, C_MINOR_DECISIONS), both(row, C_MINOR_IN_TIME, C_MINOR_IN_TIME_PA),
            g(row, C_MAJDW_TOTAL), g(row, C_MAJDW_8), g(row, C_MAJDW_8_13),
            g(row, C_MAJDW_MAX), g(row, C_MAJOR_PA), g(row, C_MAJDW_PA),
        ))

    con.execute("DROP TABLE IF EXISTS silver.planning_performance")
    con.execute("""
        CREATE TABLE silver.planning_performance (
          lpa VARCHAR, lpa_code VARCHAR, quarter VARCHAR,
          major_decisions DOUBLE, major_in_time DOUBLE,
          minor_decisions DOUBLE, minor_in_time DOUBLE,
          major_dwellings_total DOUBLE,
          major_dwellings_within_8w DOUBLE, major_dwellings_8_to_13w DOUBLE,
          major_dwellings_within_max DOUBLE,
          major_extended DOUBLE, major_dwellings_extended DOUBLE
        )""")
    insert_many(con, "INSERT INTO silver.planning_performance VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)
    c = con.execute("""SELECT count(*), count(DISTINCT quarter), count(DISTINCT lpa)
                       FROM silver.planning_performance""").fetchone()
    return Coverage(*c)


def build(con: duckdb.DuckDBPyConnection) -> None:
    """Headline against statutory, both labelled with their scope."""
    con.execute("DROP TABLE IF EXISTS gold.plumbline_quarter")
    con.execute("""
        CREATE TABLE gold.plumbline_quarter AS
        SELECT quarter,
               sum(major_decisions)                                   AS major_decisions,
               sum(major_in_time)                                     AS major_in_time,
               -- published headline: counts agreed extensions as on time
               round(100.0 * sum(major_in_time) / nullif(sum(major_decisions), 0), 1)
                                                                      AS headline_pct,
               sum(major_dwellings_total)                             AS dwelling_decisions,
               sum(major_dwellings_within_8w + major_dwellings_8_to_13w)
                                                                      AS within_13_weeks,
               -- within the statutory 13 weeks, without an agreed extension
               round(100.0 * sum(major_dwellings_within_8w + major_dwellings_8_to_13w)
                     / nullif(sum(major_dwellings_total), 0), 1)      AS statutory_pct
        FROM silver.planning_performance
        WHERE quarter IS NOT NULL AND quarter <> ''
        GROUP BY quarter
        HAVING sum(major_decisions) > 0
        ORDER BY quarter
    """)

    con.execute("DROP TABLE IF EXISTS gold.plumbline_authority")
    con.execute("""
        CREATE TABLE gold.plumbline_authority AS
        SELECT lpa,
               sum(major_decisions)                                   AS major_decisions,
               round(100.0 * sum(major_in_time) / nullif(sum(major_decisions), 0), 1)
                                                                      AS headline_pct,
               sum(major_dwellings_total)                             AS dwelling_decisions,
               round(100.0 * sum(major_dwellings_within_8w + major_dwellings_8_to_13w)
                     / nullif(sum(major_dwellings_total), 0), 1)      AS statutory_pct
        FROM silver.planning_performance
        WHERE quarter >= '2023'
        GROUP BY lpa
        HAVING sum(major_dwellings_total) >= 20 AND sum(major_decisions) >= 20
        ORDER BY headline_pct - statutory_pct DESC NULLS LAST
    """)


def national_gap(con: duckdb.DuckDBPyConnection, since: str = "2023"):
    """Published headline against the statutory reality, since `since`."""
    return con.execute(f"""
        SELECT round(100.0 * sum(major_in_time) / nullif(sum(major_decisions), 0), 1),
               round(100.0 * sum(major_dwellings_within_8w + major_dwellings_8_to_13w)
                     / nullif(sum(major_dwellings_total), 0), 1),
               sum(major_decisions), sum(major_dwellings_total)
        FROM silver.planning_performance WHERE quarter >= '{since}'
    """).fetchone()


def extension_share(con: duckdb.DuckDBPyConnection, since: str = "2023"):
    """How many decisions were made under an agreed extension, since `since`.

    This is what separates the two figures: an extended decision is in time on
    the headline and, having no published time band, outside the statutory 13
    weeks. Returns (major %, major dwelling %), or Nones on a table loaded
    before the columns were read.
    """
    cols = {r[0] for r in con.execute(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_schema = 'silver' AND table_name = 'planning_performance'").fetchall()}
    if "major_extended" not in cols:
        return None, None
    return con.execute(f"""
        SELECT round(100.0 * sum(major_extended) / nullif(sum(major_decisions), 0), 1),
               round(100.0 * sum(major_dwellings_extended)
                     / nullif(sum(major_dwellings_total), 0), 1)
        FROM silver.planning_performance WHERE quarter >= '{since}'""").fetchone()


def transparency_column_status(con: duckdb.DuckDBPyConnection):
    """When the publisher stopped populating 'within maximum time'."""
    return con.execute("""
        SELECT substr(quarter, 1, 4) AS year, count(*) AS rows,
               count(major_dwellings_within_max) AS populated,
               round(100.0 * count(major_dwellings_within_max) / count(*), 1) AS pct
        FROM silver.planning_performance
        WHERE quarter >= '2018' GROUP BY 1 ORDER BY 1
    """).fetchall()
