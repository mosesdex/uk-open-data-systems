"""Baseline -- sewage spills reported honestly.

A regulator asked whether £22.1bn of investment is working sees spill counts
fall and calls it progress. Two things make that reading unsafe:

  * **Monitors are not always on.** A spill count is only as good as the share
    of the year the monitor was actually recording. An overflow watched for half
    the year and one watched all year are not comparable, and an overflow that
    goes dark looks like it improved.
  * **Weather moves the number.** Spills follow rainfall. A drier year produces
    fewer spills with no change in the network at all.

This system fixes the first properly and prepares the second. Every spill count
is published with its monitor availability, and a normalised rate -- spills per
operational day -- is computed alongside the raw count. Outlets are resolved to
coordinates from their grid reference so rainfall can be joined per outlet.
"""
from __future__ import annotations

import io
import zipfile
from dataclasses import dataclass
from pathlib import Path

import duckdb
import openpyxl

from ..geo import ngr_to_bng, bng_to_wgs84
from ..store import insert_many

SHEET = "All WaSC"
HEADER_ROW = 7          # 1-indexed; rows above are guidance notes
COL = {
    "unique_id": 0, "company": 1, "site_name": 2, "permit": 4,
    "asset_type": 7, "ngr": 8, "waterbody": 10, "receiving_water": 11,
    "bathing_water": 13, "duration": 15, "spills": 16, "lta": 17,
    "data_start": 18, "operational_pct": 19,
}


@dataclass(frozen=True)
class Coverage:
    outlets: int
    with_spills: int
    with_availability: int
    located: int
    fully_watched: int

    def pct(self, n: int) -> float:
        return 100 * n / self.outlets if self.outlets else 0.0


def _num(v):
    if v is None:
        return None
    try:
        f = float(str(v).strip().rstrip("%"))
        return f if f == f else None
    except (TypeError, ValueError):
        return None


def _text(v):
    return str(v).strip() if v is not None and str(v).strip() else None


def load(con: duckdb.DuckDBPyConnection, zip_path: Path, year: int) -> Coverage:
    with zipfile.ZipFile(zip_path) as z:
        member = [n for n in z.namelist()
                  if n.endswith(".xlsx") and "all water" in n.lower()]
        if not member:
            raise ValueError(f"no all-companies workbook in {zip_path.name}")
        data = z.read(member[0])

    wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    ws = wb[SHEET]

    rows = []
    for i, r in enumerate(ws.iter_rows(values_only=True), start=1):
        if i <= HEADER_ROW:
            continue
        uid = _text(r[COL["unique_id"]]) if len(r) > COL["unique_id"] else None
        if not uid:
            continue
        ngr = _text(r[COL["ngr"]])
        bng = ngr_to_bng(ngr) if ngr else None
        lat = lon = None
        if bng:
            lat, lon = bng_to_wgs84(*bng)
        pct = _num(r[COL["operational_pct"]])
        # Some returns express availability as a fraction rather than a percentage.
        if pct is not None and pct <= 1.0:
            pct *= 100
        rows.append((
            year, uid, _text(r[COL["company"]]), _text(r[COL["site_name"]]),
            _text(r[COL["permit"]]), _text(r[COL["asset_type"]]), ngr,
            bng[0] if bng else None, bng[1] if bng else None, lat, lon,
            _text(r[COL["receiving_water"]]), _text(r[COL["bathing_water"]]),
            _num(r[COL["spills"]]), _num(r[COL["lta"]]), pct,
        ))

    con.execute(f"DELETE FROM silver.storm_overflow WHERE year = {year}"
                if _has(con, "storm_overflow") else "SELECT 1")
    con.execute("""
        CREATE TABLE IF NOT EXISTS silver.storm_overflow (
          year INTEGER, unique_id VARCHAR, company VARCHAR, site_name VARCHAR,
          permit VARCHAR, asset_type VARCHAR, ngr VARCHAR,
          easting INTEGER, northing INTEGER, latitude DOUBLE, longitude DOUBLE,
          receiving_water VARCHAR, bathing_water VARCHAR,
          spills DOUBLE, long_term_average DOUBLE, operational_pct DOUBLE
        )""")
    insert_many(con, "INSERT INTO silver.storm_overflow VALUES "
                     "(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)

    c = con.execute(f"""
        SELECT count(*), count(spills), count(operational_pct), count(latitude),
               count(*) FILTER (WHERE operational_pct >= 90)
        FROM silver.storm_overflow WHERE year = {year}""").fetchone()
    return Coverage(*c)


def _has(con, table: str) -> bool:
    return con.execute(
        "SELECT count(*) FROM information_schema.tables "
        "WHERE table_schema='silver' AND table_name=?", [table]).fetchone()[0] > 0


def build(con: duckdb.DuckDBPyConnection) -> None:
    """Raw and availability-adjusted spill measures, side by side."""
    con.execute("DROP TABLE IF EXISTS gold.baseline_outlet")
    con.execute("""
        CREATE TABLE gold.baseline_outlet AS
        SELECT year, unique_id, company, site_name, latitude, longitude,
               receiving_water, bathing_water, spills, long_term_average,
               operational_pct,
               -- spills per day the monitor was actually recording. An outlet
               -- watched for half the year is not comparable to one watched all
               -- year, and this is what makes them comparable.
               CASE WHEN operational_pct > 0
                    THEN round(spills / (365.0 * operational_pct / 100.0), 4)
               END AS spills_per_operational_day,
               CASE WHEN operational_pct > 0
                    THEN round(spills * 100.0 / operational_pct, 1)
               END AS spills_full_year_equivalent
        FROM silver.storm_overflow
        WHERE spills IS NOT NULL
    """)

    con.execute("DROP TABLE IF EXISTS gold.baseline_company")
    con.execute("""
        CREATE TABLE gold.baseline_company AS
        SELECT year, company,
               count(*)                                          AS outlets,
               round(sum(spills))                                AS reported_spills,
               round(sum(spills_full_year_equivalent))           AS availability_adjusted,
               round(avg(operational_pct), 1)                    AS mean_availability_pct,
               count(*) FILTER (WHERE operational_pct < 90)      AS under_watched,
               count(*) FILTER (WHERE operational_pct < 50)      AS barely_watched
        FROM gold.baseline_outlet
        GROUP BY year, company
        ORDER BY year DESC, reported_spills DESC
    """)


def under_watched(con: duckdb.DuckDBPyConnection, limit: int = 10):
    """Outlets whose reported count rests on a monitor that was mostly off."""
    return con.execute(f"""
        SELECT company, site_name, spills, operational_pct,
               spills_full_year_equivalent
        FROM gold.baseline_outlet
        WHERE operational_pct IS NOT NULL AND operational_pct < 50 AND spills > 0
        ORDER BY spills_full_year_equivalent - spills DESC
        LIMIT {limit}
    """).fetchall()
