"""Loading bronze downloads into silver tables.

Archives are expanded one member at a time and removed immediately after the
load, so peak disk stays bounded by the largest single file rather than the sum
of everything. That matters: the Ordnance Survey products are large, and a
loader that expands everything first will fill a volume that had ample room.
"""
from __future__ import annotations

import shutil
import tempfile
import zipfile
from pathlib import Path

import duckdb

from .store import insert_many

# Code-Point Open ships headerless CSVs plus a separate header file.
CODEPOINT_COLUMNS = [
    "postcode", "positional_quality", "easting", "northing", "country_code",
    "nhs_regional_ha_code", "nhs_ha_code", "admin_county_code",
    "admin_district_code", "admin_ward_code",
]


class LoadError(RuntimeError):
    pass


def _require(path: Path) -> Path:
    if not path.exists():
        raise LoadError(f"missing bronze file: {path}. Fetch it first.")
    if path.suffix == ".zip" and not zipfile.is_zipfile(path):
        raise LoadError(
            f"{path.name} is not a readable archive -- it is probably a truncated "
            "download. Re-fetch it without --max-bytes."
        )
    return path


def load_codepoint(con: duckdb.DuckDBPyConnection, zip_path: Path) -> int:
    """Load every postcode in GB with its coordinate and administrative codes.

    Code-Point Open is the postcode tier of the place spine: complete, national,
    and free. It resolves to a postcode centroid rather than a building, which
    is why the resolver records the tier it achieved -- see place.py.
    """
    _require(zip_path)
    tmp = Path(tempfile.mkdtemp(prefix="gt-codepoint-"))
    try:
        with zipfile.ZipFile(zip_path) as z:
            members = [m for m in z.namelist()
                       if m.startswith("Data/CSV/") and m.endswith(".csv")]
            if not members:
                raise LoadError("no Data/CSV/*.csv members found in Code-Point Open")
            for m in members:
                target = tmp / Path(m).name
                with z.open(m) as src, open(target, "wb") as dst:
                    shutil.copyfileobj(src, dst, length=1 << 20)

        cols = ", ".join(f"'{c}': 'VARCHAR'" for c in CODEPOINT_COLUMNS)
        con.execute("DROP TABLE IF EXISTS silver.place_postcode")
        con.execute(f"""
            CREATE TABLE silver.place_postcode AS
            SELECT
              upper(replace(postcode, ' ', ''))            AS postcode_key,
              trim(postcode)                               AS postcode,
              TRY_CAST(positional_quality AS INTEGER)      AS positional_quality,
              TRY_CAST(easting  AS INTEGER)                AS easting,
              TRY_CAST(northing AS INTEGER)                AS northing,
              nullif(trim(admin_district_code), '')        AS lad_code,
              nullif(trim(admin_ward_code), '')            AS ward_code,
              nullif(trim(country_code), '')               AS country_code
            FROM read_csv('{tmp}/*.csv', header=false, columns={{{cols}}})
        """)
        n = con.execute("SELECT count(*) FROM silver.place_postcode").fetchone()[0]
        con.execute("CREATE INDEX IF NOT EXISTS idx_pc ON silver.place_postcode(postcode_key)")
        return n
    finally:
        shutil.rmtree(tmp, ignore_errors=True)   # never leave an expansion behind


def load_uprn(con: duckdb.DuckDBPyConnection, zip_path: Path) -> int:
    """Load OS Open UPRN: the property tier of the place spine."""
    _require(zip_path)
    tmp = Path(tempfile.mkdtemp(prefix="gt-uprn-"))
    try:
        with zipfile.ZipFile(zip_path) as z:
            members = [m for m in z.namelist() if m.lower().endswith(".csv")]
            if not members:
                raise LoadError("no CSV member found in OS Open UPRN")
            target = tmp / "uprn.csv"
            with z.open(members[0]) as src, open(target, "wb") as dst:
                shutil.copyfileobj(src, dst, length=1 << 20)

        con.execute("DROP TABLE IF EXISTS silver.place_uprn")
        con.execute(f"""
            CREATE TABLE silver.place_uprn AS
            SELECT
              TRY_CAST(UPRN AS BIGINT)      AS uprn,
              TRY_CAST(X_COORDINATE AS DOUBLE) AS easting,
              TRY_CAST(Y_COORDINATE AS DOUBLE) AS northing,
              TRY_CAST(LATITUDE  AS DOUBLE) AS latitude,
              TRY_CAST(LONGITUDE AS DOUBLE) AS longitude
            FROM read_csv('{target}', header=true, ignore_errors=true)
        """)
        return con.execute("SELECT count(*) FROM silver.place_uprn").fetchone()[0]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def load_lids(con: duckdb.DuckDBPyConnection, zip_path: Path, table: str,
              left: str, right: str) -> int:
    """Load a Linked Identifiers crosswalk file into silver."""
    _require(zip_path)
    tmp = Path(tempfile.mkdtemp(prefix="gt-lids-"))
    try:
        with zipfile.ZipFile(zip_path) as z:
            members = [m for m in z.namelist() if m.lower().endswith(".csv")]
            if not members:
                raise LoadError(f"no CSV member in {zip_path.name}")
            target = tmp / "lids.csv"
            with z.open(members[0]) as src, open(target, "wb") as dst:
                shutil.copyfileobj(src, dst, length=1 << 20)

        con.execute(f"DROP TABLE IF EXISTS silver.{table}")
        con.execute(f"""
            CREATE TABLE silver.{table} AS
            SELECT TRY_CAST({left} AS BIGINT) AS left_id,
                   TRY_CAST({right} AS BIGINT) AS right_id
            FROM read_csv('{target}', header=true, ignore_errors=true)
        """)
        return con.execute(f"SELECT count(*) FROM silver.{table}").fetchone()[0]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def load_lad_boundaries(con: duckdb.DuckDBPyConnection, geojson_path: Path) -> int:
    """Load administrative boundaries, for aggregation and mapping."""
    _require(geojson_path)
    import json
    gj = json.loads(geojson_path.read_text())
    rows = [(f["properties"].get("LAD24CD") or f["properties"].get("c"),
             f["properties"].get("LAD24NM") or f["properties"].get("n"))
            for f in gj["features"]]
    con.execute("DROP TABLE IF EXISTS silver.lad")
    con.execute("CREATE TABLE silver.lad (lad_code VARCHAR PRIMARY KEY, lad_name VARCHAR)")
    insert_many(con, "INSERT OR IGNORE INTO silver.lad VALUES (?, ?)", rows)
    return con.execute("SELECT count(*) FROM silver.lad").fetchone()[0]
