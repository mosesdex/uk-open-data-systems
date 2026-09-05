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


def load_rainfall(con: duckdb.DuckDBPyConnection, path: Path) -> int:
    """Annual rainfall total per station, with its coordinates."""
    import json as _json
    rows = _json.loads(Path(path).read_text())
    con.execute("DROP TABLE IF EXISTS silver.rainfall_station")
    con.execute("""CREATE TABLE silver.rainfall_station (
        station VARCHAR, label VARCHAR, lat DOUBLE, long DOUBLE,
        annual_mm DOUBLE, days INTEGER)""")
    insert_many(con, "INSERT INTO silver.rainfall_station VALUES (?,?,?,?,?,?)",
                [(r.get("station"), r.get("label"),
                  r.get("lat"), r.get("long"),
                  r.get("annual_mm"), r.get("days")) for r in rows])
    return len(rows)


def _has(con, table):
    return con.execute("SELECT count(*) FROM information_schema.tables "
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

    # Weather normalisation: assign each outlet the rainfall of its nearest
    # station, then compare spills against rainfall. A fall in spills in a year
    # that was also drier tells you less than a fall in a wet year. This closes
    # the second half of the system -- the availability adjustment was the first.
    con.execute("DROP TABLE IF EXISTS gold.baseline_rainfall")
    if _has(con, "rainfall_station"):
        con.execute("""
            CREATE TABLE gold.baseline_rainfall AS
            WITH nearest AS (
              SELECT o.unique_id, o.company, o.spills, o.operational_pct,
                     (SELECT r.annual_mm FROM silver.rainfall_station r
                      WHERE r.lat IS NOT NULL
                      ORDER BY (r.lat-o.latitude)*(r.lat-o.latitude)
                             + (r.long-o.longitude)*(r.long-o.longitude)
                      LIMIT 1) AS local_rain_mm
              FROM gold.baseline_outlet o
              WHERE o.latitude IS NOT NULL AND o.spills IS NOT NULL
                AND o.year = (SELECT max(year) FROM gold.baseline_outlet)
            )
            SELECT company,
                   count(*)                              AS outlets,
                   round(sum(spills))                    AS spills,
                   round(avg(local_rain_mm), 0)          AS mean_local_rain_mm,
                   -- spills per 100mm of rainfall: the weather-adjusted rate.
                   -- separates what the network did from what the sky did.
                   round(sum(spills) / nullif(avg(local_rain_mm), 0) * 100, 1)
                                                         AS spills_per_100mm_rain
            FROM nearest WHERE local_rain_mm IS NOT NULL
            GROUP BY company ORDER BY spills DESC
        """)
    else:
        con.execute("""CREATE TABLE gold.baseline_rainfall (
            company VARCHAR, outlets INTEGER, spills DOUBLE,
            mean_local_rain_mm DOUBLE, spills_per_100mm_rain DOUBLE)""")

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

    con.execute("DROP TABLE IF EXISTS gold.baseline_trend")
    con.execute("""
        CREATE TABLE gold.baseline_trend AS
        SELECT year,
               count(*)                                          AS outlets,
               round(sum(spills))                                AS reported_spills,
               round(sum(spills_full_year_equivalent))           AS adjusted_spills,
               round(avg(operational_pct), 1)                    AS mean_uptime
        FROM gold.baseline_outlet
        GROUP BY year ORDER BY year
    """)

    _by_district(con)


def _by_district(con: duckdb.DuckDBPyConnection) -> None:
    """Assign each outlet to a district by point-in-polygon, so spills can be
    mapped. Uptime-adjusted spills are summed per district for the latest year."""
    from .. import spatial
    lads = spatial.load()
    rows = con.execute("""
        SELECT longitude, latitude, spills_full_year_equivalent, spills
        FROM gold.baseline_outlet
        WHERE year = (SELECT max(year) FROM gold.baseline_outlet)
          AND latitude IS NOT NULL AND longitude IS NOT NULL
    """).fetchall()
    agg = {}
    for lon, lat, adj, raw in rows:
        code = lads.point(lon, lat)
        if not code:
            continue
        a = agg.setdefault(code, [0, 0.0, 0.0])
        a[0] += 1
        a[1] += adj or 0.0
        a[2] += raw or 0.0
    con.execute("DROP TABLE IF EXISTS gold.baseline_district")
    con.execute("""CREATE TABLE gold.baseline_district
                   (lad_code VARCHAR, outlets INTEGER,
                    adjusted_spills DOUBLE, reported_spills DOUBLE)""")
    if agg:
        con.executemany("INSERT INTO gold.baseline_district VALUES (?, ?, ?, ?)",
                        [(c, v[0], round(v[1], 1), round(v[2], 1)) for c, v in agg.items()])


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


# ---------------------------------------------------------------------------
# Multi-year EDM loader. The annual returns drift in layout every year (combined
# "All WaSC" sheet in 2025; per-company sheets 2021-2024; shifted columns and a
# missing long-term-average column in some years). Rather than a fixed column map
# per year, this finds columns by their header text, so one loader ingests every
# year's return into silver.storm_overflow keyed by year.
# ---------------------------------------------------------------------------
_HDR_MATCH = {
    "company":        ("water company name", "water company"),
    "site_name":      ("site name",),
    "permit":         ("ea permit",),
    "ngr":            ("ngr", "grid ref", "discharge ngr"),
    "receiving_water":("receiving water",),
    "bathing_water":  ("bathing water",),
    "duration":       ("total duration",),
    "spills":         ("counted spills", "spill count", "counted using"),
    "lta":            ("long-term average", "long term average"),
    "operational_pct":("edm operation", "% of time"),
    "unique_id":      ("unique id", "unique reference"),
}


def _map_header(header_cells):
    """Return {field: col_index} by matching header text substrings."""
    idx = {}
    low = [(str(c).lower().replace("\n", " ") if c is not None else "") for c in header_cells]
    for field, subs in _HDR_MATCH.items():
        for i, h in enumerate(low):
            if any(s in h for s in subs):
                # prefer the first match; for operational_pct take the plain one
                if field == "operational_pct" and ("reason" in h or "activity" in h):
                    continue
                idx.setdefault(field, i)
    return idx


def load_multi(con: duckdb.DuckDBPyConnection, zip_path: Path, year: int) -> int:
    """Load one annual return (any year's layout) into silver.storm_overflow."""
    with zipfile.ZipFile(zip_path) as z:
        member = ([n for n in z.namelist() if n.endswith(".xlsx") and "all water" in n.lower()]
                  or [n for n in z.namelist() if n.endswith(".xlsx")])
        if not member:
            raise ValueError(f"no workbook in {zip_path.name}")
        data = z.read(member[0])
    wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    sheets = ["All WaSC"] if "All WaSC" in wb.sheetnames else wb.sheetnames

    rows = []
    for sheet in sheets:
        ws = wb[sheet]
        grid = list(ws.iter_rows(values_only=True))
        # find the header row: the first row that mentions a permit or company header
        hrow = None
        for i, r in enumerate(grid[:12]):
            low = " ".join(str(c).lower() for c in r if c is not None)
            if "ea permit" in low or "water company name" in low:
                hrow = i; break
        if hrow is None:
            continue
        idx = _map_header(grid[hrow])
        if "spills" not in idx or "operational_pct" not in idx:
            continue
        def g(r, f):
            i = idx.get(f)
            return r[i] if (i is not None and i < len(r)) else None
        for r in grid[hrow + 1:]:
            comp = _text(g(r, "company"))
            site = _text(g(r, "site_name"))
            permit = _text(g(r, "permit"))
            if not (comp or site or permit):
                continue
            spills = _num(g(r, "spills"))
            if spills is None:
                continue
            ngr = _text(g(r, "ngr"))
            bng = ngr_to_bng(ngr) if ngr else None
            lat = lon = None
            if bng:
                lat, lon = bng_to_wgs84(*bng)
            pct = _num(g(r, "operational_pct"))
            if pct is not None and pct <= 1.0:
                pct *= 100
            uid = _text(g(r, "unique_id")) or (permit or f"{comp}|{site}")
            rows.append((
                year, uid, comp, site, permit, None, ngr,
                bng[0] if bng else None, bng[1] if bng else None, lat, lon,
                _text(g(r, "receiving_water")), _text(g(r, "bathing_water")),
                spills, _num(g(r, "lta")), pct,
            ))

    con.execute("""CREATE TABLE IF NOT EXISTS silver.storm_overflow (
          year INTEGER, unique_id VARCHAR, company VARCHAR, site_name VARCHAR,
          permit VARCHAR, asset_type VARCHAR, ngr VARCHAR,
          easting INTEGER, northing INTEGER, latitude DOUBLE, longitude DOUBLE,
          receiving_water VARCHAR, bathing_water VARCHAR,
          spills DOUBLE, long_term_average DOUBLE, operational_pct DOUBLE)""")
    con.execute(f"DELETE FROM silver.storm_overflow WHERE year = {year}")
    if rows:
        from ..store import insert_many
        insert_many(con, "INSERT INTO silver.storm_overflow VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)
    return len(rows)
