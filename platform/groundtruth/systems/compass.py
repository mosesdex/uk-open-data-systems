"""Compass -- special educational needs demand, forecast where it is planned.

Councils commission specialist places years ahead. The published projections are
national or county-wide, so a district whose demand is rising inside a county
whose demand is falling is invisible until children are placed far from home.

Compass forecasts at local authority level from the department's own published
counts. Two constraints shape it:

  * **Aggregates only.** Every figure here comes from published counts of pupils
    by authority, year and provision type. No record about any individual child
    is read, held or needed. That is what makes the system lawful to build and
    deliverable without a data sharing agreement.
  * **A forecast is labelled a forecast.** The trend is fitted on the published
    series and the fitted range is published with it. Where a series is too
    short or too erratic to support a projection, Compass says so instead of
    extrapolating anyway.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import duckdb

# Provision categories in the published series. EHC plan is the statutory one
# that carries a placement duty; SEN support does not.
EHC_PLAN = "Education, health and care plan"
SEN_SUPPORT = "SEN support / SEN without an EHC plan"

MIN_YEARS_FOR_TREND = 5


@dataclass(frozen=True)
class Coverage:
    rows: int
    authorities: int
    years: int
    latest: str


def _year(period: str) -> int | None:
    """'202526' is the academic year starting 2025."""
    try:
        return int(str(period)[:4])
    except (TypeError, ValueError):
        return None


def load(con: duckdb.DuckDBPyConnection, csv_path: Path) -> Coverage:
    con.execute("DROP TABLE IF EXISTS silver.sen_provision")
    con.execute(f"""
        CREATE TABLE silver.sen_provision AS
        SELECT time_period                                   AS period,
               TRY_CAST(substr(CAST(time_period AS VARCHAR), 1, 4) AS INTEGER) AS year,
               geographic_level                              AS level,
               nullif(trim(la_name), '')                     AS la_name,
               nullif(trim(new_la_code), '')                 AS la_code,
               nullif(trim(region_name), '')                 AS region,
               nullif(trim(phase_type_grouping), '')         AS phase,
               nullif(trim(establishment_type), '')           AS establishment_type,
               nullif(trim(hospital_school), '')              AS hospital_school,
               nullif(trim(sen_provision), '')               AS provision,
               TRY_CAST(replace(pupil_count, ',', '') AS BIGINT) AS pupils
        FROM read_csv('{csv_path}', header=true, all_varchar=true, ignore_errors=true)
        WHERE geographic_level = 'Local authority'
    """)
    c = con.execute("""
        SELECT count(*), count(DISTINCT la_code), count(DISTINCT year), max(period)
        FROM silver.sen_provision""").fetchone()
    return Coverage(*c)


def build(con: duckdb.DuckDBPyConnection) -> None:
    """Series per authority, then a linear trend where the data supports one."""
    # The file is a cube: every combination of phase, establishment type and
    # hospital-school flag is present, each with its own 'Total' row. Summing
    # across them multiplies the count several times over -- an early version
    # reported 2.15m EHC plans against a real figure near 576,000. Only the
    # fully-totalled cell is taken.
    con.execute("DROP TABLE IF EXISTS gold.compass_series")
    con.execute(f"""
        CREATE TABLE gold.compass_series AS
        SELECT la_code, any_value(la_name) AS la_name, any_value(region) AS region,
               year, provision, sum(pupils) AS pupils
        FROM silver.sen_provision
        WHERE la_code IS NOT NULL AND provision IS NOT NULL AND pupils IS NOT NULL
          AND phase = 'Total'
          AND establishment_type = 'Total'
          AND hospital_school = 'Total'
        GROUP BY la_code, year, provision
    """)

    # Ordinary least squares on year, computed in SQL. Deliberately simple: a
    # transparent straight line a statistician can check beats a better fit
    # nobody can reproduce.
    con.execute(f"""
        CREATE OR REPLACE TABLE gold.compass_trend AS
        WITH s AS (
          SELECT la_code, any_value(la_name) AS la_name, provision,
                 count(*) AS years, min(year) AS first_year, max(year) AS last_year,
                 avg(year) AS mean_x, avg(pupils) AS mean_y,
                 sum(year * pupils) AS sum_xy, sum(year * year) AS sum_xx,
                 sum(pupils) AS total, count(*) AS n
          FROM gold.compass_series GROUP BY la_code, provision
        ),
        fit AS (
          SELECT *,
                 (sum_xy - n * mean_x * mean_y)
                 / nullif(sum_xx - n * mean_x * mean_x, 0) AS slope
          FROM s WHERE years >= {MIN_YEARS_FOR_TREND}
        )
        SELECT la_code, la_name, provision, years, first_year, last_year,
               round(mean_y) AS mean_pupils,
               round(slope, 1) AS pupils_per_year,
               round(slope * 3) AS projected_change_3yr,
               round(100.0 * slope * 3 / nullif(mean_y, 0), 1) AS projected_change_pct
        FROM fit
        ORDER BY projected_change_pct DESC NULLS LAST
    """)

    # Where a district moves against its region: the mismatch the system exists
    # to surface, since planning happens locally and projections are published
    # regionally.
    con.execute(f"""
        CREATE OR REPLACE TABLE gold.compass_divergence AS
        WITH la AS (
          SELECT t.la_code, t.la_name, s.region, t.provision, t.pupils_per_year,
                 t.projected_change_pct
          FROM gold.compass_trend t
          JOIN (SELECT DISTINCT la_code, region FROM gold.compass_series) s
            ON s.la_code = t.la_code
          WHERE t.provision = '{EHC_PLAN}'
        ),
        reg AS (
          SELECT region, avg(projected_change_pct) AS region_change_pct
          FROM la GROUP BY region
        )
        SELECT la.la_name, la.region, la.projected_change_pct,
               round(reg.region_change_pct, 1) AS region_change_pct,
               round(la.projected_change_pct - reg.region_change_pct, 1) AS divergence
        FROM la JOIN reg USING (region)
        WHERE la.projected_change_pct IS NOT NULL
        ORDER BY abs(la.projected_change_pct - reg.region_change_pct) DESC
    """)


def national(con: duckdb.DuckDBPyConnection):
    return con.execute(f"""
        SELECT provision, min(year), max(year), sum(pupils) FILTER (WHERE year = (SELECT max(year) FROM gold.compass_series)) AS latest,
               sum(pupils) FILTER (WHERE year = (SELECT min(year) FROM gold.compass_series)) AS earliest
        FROM gold.compass_series GROUP BY provision ORDER BY latest DESC NULLS LAST
    """).fetchall()
