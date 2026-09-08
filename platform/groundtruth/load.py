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
    """Load OS Open UPRN: the property tier of the place spine.

    2.3 GB of CSV inside the archive. Expanded to a temporary directory, read
    natively by DuckDB, then removed -- inserting 41 million rows a row at a
    time from Python is hours of work the database does in under a minute.
    """
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
              TRY_CAST(UPRN AS BIGINT)         AS uprn,
              TRY_CAST(X_COORDINATE AS DOUBLE) AS easting,
              TRY_CAST(Y_COORDINATE AS DOUBLE) AS northing,
              TRY_CAST(LATITUDE  AS DOUBLE)    AS latitude,
              TRY_CAST(LONGITUDE AS DOUBLE)    AS longitude
            FROM read_csv('{target}', header=true, all_varchar=true, ignore_errors=true)
            WHERE TRY_CAST(UPRN AS BIGINT) IS NOT NULL
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


def load_crosswalk(con: duckdb.DuckDBPyConnection, zip_path: Path, table: str) -> int:
    """Load an OS Linked Identifiers file.

    Every crosswalk uses the same shape: IDENTIFIER_1 is the property reference,
    IDENTIFIER_2 the thing it links to, and CONFIDENCE the publisher's own view
    of the link. The confidence column is kept rather than dropped -- a link the
    publisher is unsure about must not be presented as certain downstream.
    """
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
            SELECT TRY_CAST(IDENTIFIER_1 AS BIGINT) AS uprn,
                   nullif(trim(CAST(IDENTIFIER_2 AS VARCHAR)), '') AS linked_id,
                   nullif(trim(CONFIDENCE), '')                    AS confidence
            FROM read_csv('{target}', header=true, all_varchar=true, ignore_errors=true)
            WHERE TRY_CAST(IDENTIFIER_1 AS BIGINT) IS NOT NULL
        """)
        return con.execute(f"SELECT count(*) FROM silver.{table}").fetchone()[0]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def load_companies(con: duckdb.DuckDBPyConnection, zip_path: Path) -> int:
    """Load the Companies House basic company data product.

    This is what the entity spine has been missing: a register to resolve
    against, rather than only the identifiers that procurement and care records
    happen to carry. Column names in the published file contain dots and
    leading spaces, so they are selected by quoted name.
    """
    _require(zip_path)
    tmp = Path(tempfile.mkdtemp(prefix="gt-ch-"))
    try:
        with zipfile.ZipFile(zip_path) as z:
            members = [m for m in z.namelist() if m.lower().endswith(".csv")]
            if not members:
                raise LoadError("no CSV member in the Companies House archive")
            target = tmp / "companies.csv"
            with z.open(members[0]) as src, open(target, "wb") as dst:
                shutil.copyfileobj(src, dst, length=1 << 20)

        con.execute("DROP TABLE IF EXISTS silver.company")
        con.execute(f"""
            CREATE TABLE silver.company AS
            SELECT
              nullif(trim("CompanyNumber"), '')                 AS company_number,
              nullif(trim("CompanyName"), '')                   AS name,
              nullif(trim("CompanyStatus"), '')                 AS status,
              nullif(trim("CompanyCategory"), '')               AS category,
              nullif(trim("RegAddress.PostCode"), '')           AS postcode,
              nullif(trim("RegAddress.PostTown"), '')           AS post_town,
              nullif(trim("CountryOfOrigin"), '')               AS country,
              nullif(trim("IncorporationDate"), '')             AS incorporated,
              nullif(trim("SICCode.SicText_1"), '')             AS sic_1
            FROM read_csv('{target}', header=true, all_varchar=true, ignore_errors=true)
            WHERE nullif(trim("CompanyNumber"), '') IS NOT NULL
        """)
        con.execute("CREATE INDEX IF NOT EXISTS idx_company_num ON silver.company(company_number)")
        return con.execute("SELECT count(*) FROM silver.company").fetchone()[0]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def load_charities(con: duckdb.DuckDBPyConnection, zip_path: Path) -> int:
    """Load the Charity Commission register.

    Extends the entity spine to bodies a company register cannot name: many care
    and education providers are charities, not companies. The name is normalised
    the same way company names are, so the two registers answer to one resolver.
    """
    _require(zip_path)
    tmp = Path(tempfile.mkdtemp(prefix="gt-charity-"))
    try:
        with zipfile.ZipFile(zip_path) as z:
            members = [m for m in z.namelist()
                       if m.endswith(".json") and "charity." in m]
            if not members:
                members = [m for m in z.namelist() if m.endswith(".json")]
            if not members:
                raise LoadError("no charity JSON in the extract")
            target = tmp / "charity.json"
            with z.open(members[0]) as src, open(target, "wb") as dst:
                shutil.copyfileobj(src, dst, length=1 << 20)

        con.execute("DROP TABLE IF EXISTS silver.charity")
        con.execute(f"""
            CREATE TABLE silver.charity AS
            SELECT
              CAST(registered_charity_number AS VARCHAR)        AS charity_number,
              nullif(trim(charity_name), '')                    AS name,
              nullif(trim(charity_registration_status), '')     AS status
            FROM read_json('{target}', format='array', maximum_object_size=20000000)
            WHERE registered_charity_number IS NOT NULL
              AND linked_charity_number = 0
        """)
        con.execute("CREATE INDEX IF NOT EXISTS idx_charity_num ON silver.charity(charity_number)")
        # A normalised-name index over registered charities only, so the entity
        # spine can resolve a charitable provider the same way it resolves a
        # company. normalise happens via the shared key, computed in SQL.
        con.execute("DROP TABLE IF EXISTS silver.charity_key")
        con.execute("""CREATE TABLE silver.charity_key AS
            WITH n AS (SELECT charity_number, name,
                trim(regexp_replace(regexp_replace(regexp_replace(
                  regexp_replace(lower(trim(name)),'&',' and '),
                  '[^a-z0-9 ]',' ','g'),' +',' ','g'),'^the ','')) AS k
              FROM silver.charity WHERE status='Registered' AND name IS NOT NULL)
            SELECT charity_number, name, k AS name_key FROM n WHERE k <> ''""")
        con.execute("CREATE INDEX IF NOT EXISTS idx_ckey ON silver.charity_key(name_key)")
        return con.execute("SELECT count(*) FROM silver.charity").fetchone()[0]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def load_rainfall(con: duckdb.DuckDBPyConnection, json_path: Path) -> int:
    """Load rainfall readings: the weather side of the spill normalisation.

    Each reading names its measure, and the station id is the first field of the
    measure id, so spills can be joined to rainfall at the same outlet.
    """
    _require(json_path)
    import json as _json
    doc = _json.loads(Path(json_path).read_text())
    rows = []
    for r in doc.get("items", []):
        measure = r.get("measure", "")
        # .../measures/E7050-rainfall-...  -> station E7050
        station = measure.split("/measures/")[-1].split("-")[0] if measure else None
        rows.append((station, r.get("dateTime"), r.get("value")))
    con.execute("DROP TABLE IF EXISTS silver.rainfall_reading")
    con.execute("""CREATE TABLE silver.rainfall_reading (
        station VARCHAR, reading_time VARCHAR, value DOUBLE)""")
    insert_many(con, "INSERT INTO silver.rainfall_reading VALUES (?,?,?)", rows)
    return len(rows)


def load_births(con: duckdb.DuckDBPyConnection, csv_path: Path) -> int:
    """Load live births per local authority: the cohort input for forecasting."""
    _require(csv_path)
    con.execute("DROP TABLE IF EXISTS silver.births")
    con.execute(f"""
        CREATE TABLE silver.births AS
        SELECT trim(GEOGRAPHY_CODE) AS lad_code,
               trim(GEOGRAPHY_NAME) AS lad_name,
               TRY_CAST(OBS_VALUE AS INTEGER) AS births
        FROM read_csv('{csv_path}', header=true, all_varchar=true, ignore_errors=true)
        WHERE trim(GEOGRAPHY_CODE) <> ''
    """)
    return con.execute("SELECT count(*) FROM silver.births").fetchone()[0]


# Person names normalise loosely: title and punctuation vary between filings for
# the same individual, so they are stripped before two records are called the
# same person. This is deliberately conservative -- a shared-control claim that
# turns out to be two different people is worse than a missed one.
def _psc_person_key(name: str) -> str:
    import re
    if not name:
        return ""
    s = name.lower().strip()
    s = re.sub(r"^(mr|mrs|ms|miss|dr|prof|sir|dame|lord|lady|rev)\.?\s+", "", s)
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def load_psc(con: duckdb.DuckDBPyConnection, bronze: Path) -> int:
    """Load persons of significant control from every snapshot part.

    One row per (company, controlling party). A person is keyed by a normalised
    name so the same individual controlling several companies collapses to one
    key -- which is what makes shared control between bidders visible.
    """
    import json as _json
    parts = sorted(p for p in Path(bronze).glob("psc-snapshot-*.zip")
                   if zipfile.is_zipfile(p))
    if not parts:
        raise LoadError("no PSC snapshot parts on disk -- run: gt backfill --only psc")

    con.execute("DROP TABLE IF EXISTS silver.psc")
    con.execute("""CREATE TABLE silver.psc (
        company_number VARCHAR, kind VARCHAR, name VARCHAR, person_key VARCHAR,
        control VARCHAR)""")

    # The snapshot members are newline-delimited JSON, which DuckDB reads
    # natively -- far faster than a Python loop over 13 GB. The person key still
    # needs the shared normaliser, so that one column is computed per row after
    # the bulk read, over the far smaller set of controlling parties.
    con.create_function("psc_key", _psc_person_key, ["VARCHAR"], "VARCHAR")
    tmp = Path(tempfile.mkdtemp(prefix="gt-psc-"))
    total = 0
    try:
        for zp in parts:
            with zipfile.ZipFile(zp) as z:
                member = [m for m in z.namelist()
                          if m.endswith(".txt") or m.endswith(".json")]
                if not member:
                    continue
                target = tmp / "psc.ndjson"
                with z.open(member[0]) as src, open(target, "wb") as dst:
                    shutil.copyfileobj(src, dst, length=1 << 20)
            con.execute(f"""
                INSERT INTO silver.psc
                WITH raw AS (
                  SELECT company_number, to_json(data) AS d
                  FROM read_json('{target}', format='newline_delimited',
                                 maximum_object_size=10000000, ignore_errors=true,
                                 records=true)
                )
                SELECT company_number,
                       json_extract_string(d, '$.kind')  AS kind,
                       json_extract_string(d, '$.name')  AS name,
                       psc_key(json_extract_string(d, '$.name')) AS person_key,
                       array_to_string(
                         CAST(json_extract(d, '$.natures_of_control') AS VARCHAR[]), ';')
                FROM raw
                WHERE json_extract_string(d, '$.kind') LIKE '%person-with-significant-control%'
            """)
            target.unlink(missing_ok=True)
        total = con.execute("SELECT count(*) FROM silver.psc").fetchone()[0]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    con.execute("CREATE INDEX IF NOT EXISTS idx_psc_company ON silver.psc(company_number)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_psc_person ON silver.psc(person_key)")
    return total

# ---------------------------------------------------------------- corroboration
# These three exist to be compared against something the platform already holds.
# None of them feeds a headline figure; each one is a second route to a quantity
# the platform publishes, so the contradictions module can test a consistency
# this system would otherwise be asserting without evidence.

def load_hydrology_stations(con: duckdb.DuckDBPyConnection, json_path: Path) -> int:
    """The Environment Agency's hydrology station register.

    Baseline normalises spills against the flood-monitoring rainfall network.
    This is the agency's other station register, and the two are expected to
    overlap -- where they do not, one arm of the EA is measuring at a station
    the other does not list.
    """
    _require(json_path)
    con.execute("DROP TABLE IF EXISTS silver.hydrology_station")
    con.execute(f"""
        CREATE TABLE silver.hydrology_station AS
        WITH raw AS (
          SELECT unnest(items) AS i
          FROM read_json_auto('{json_path}', maximum_object_size=400000000)
        )
        SELECT trim(CAST(i.notation AS VARCHAR))    AS notation,
               trim(CAST(i.stationGuid AS VARCHAR)) AS station_guid,
               trim(CAST(i.wiskiID AS VARCHAR))     AS wiski_id,
               CAST(i.label AS VARCHAR)             AS label,
               TRY_CAST(i.lat AS DOUBLE)            AS lat,
               TRY_CAST(i.long AS DOUBLE)           AS long,
               CAST(i.riverName AS VARCHAR)         AS river
        FROM raw
    """)
    return con.execute("SELECT count(*) FROM silver.hydrology_station").fetchone()[0]


def load_neso_tec(con: duckdb.DuckDBPyConnection, json_path: Path) -> int:
    """NESO's transmission connection register, keyed by the DNO hosting each project."""
    _require(json_path)
    con.execute("DROP TABLE IF EXISTS silver.neso_connection")
    con.execute(f"""
        CREATE TABLE silver.neso_connection AS
        WITH raw AS (
          SELECT unnest(result.records) AS r
          FROM read_json_auto('{json_path}', maximum_object_size=200000000)
        )
        SELECT CAST(r."Project Name"   AS VARCHAR) AS project,
               CAST(r."Customer Name"  AS VARCHAR) AS customer,
               CAST(r."Connection Site" AS VARCHAR) AS site,
               CAST(r."Project Status" AS VARCHAR) AS status,
               CAST(r."HOST TO"        AS VARCHAR) AS host_to,
               TRY_CAST(r."MW Connected" AS DOUBLE) AS mw_connected
        FROM raw
    """)
    return con.execute("SELECT count(*) FROM silver.neso_connection").fetchone()[0]


def load_nhs_ods(con: duckdb.DuckDBPyConnection, json_path: Path) -> int:
    """The NHS organisation register: a large, independent set of UK postcodes."""
    _require(json_path)
    con.execute("DROP TABLE IF EXISTS silver.nhs_organisation")
    con.execute(f"""
        CREATE TABLE silver.nhs_organisation AS
        WITH raw AS (
          SELECT unnest(Organisations) AS o
          FROM read_json_auto('{json_path}', maximum_object_size=400000000)
        )
        SELECT CAST(o.OrgId AS VARCHAR)                  AS org_id,
               CAST(o.Name AS VARCHAR)                   AS name,
               CAST(o.Status AS VARCHAR)                 AS status,
               CAST(o.PrimaryRoleDescription AS VARCHAR) AS role,
               upper(replace(trim(CAST(o.PostCode AS VARCHAR)), ' ', '')) AS postcode_key
        FROM raw
    """)
    # A name index, built the same way the charity one is, so the entity spine
    # can offer a fourth identifier authority. Only active organisations: a
    # closed trust is not who is running a care home today.
    con.execute("DROP TABLE IF EXISTS silver.nhs_key")
    con.execute("""CREATE TABLE silver.nhs_key AS
        WITH n AS (SELECT org_id, name,
            trim(regexp_replace(regexp_replace(regexp_replace(
              regexp_replace(lower(trim(name)),'&',' and '),
              '[^a-z0-9 ]',' ','g'),' +',' ','g'),'^the ','')) AS k
          FROM silver.nhs_organisation
          WHERE name IS NOT NULL AND lower(status) = 'active')
        SELECT org_id, name, k AS name_key FROM n WHERE k <> ''""")
    con.execute("CREATE INDEX IF NOT EXISTS idx_nhskey ON silver.nhs_key(name_key)")
    return con.execute("SELECT count(*) FROM silver.nhs_organisation").fetchone()[0]

def load_naptan(con: duckdb.DuckDBPyConnection, csv_path: Path) -> int:
    """Every public transport access node, with a grid reference.

    Held as the test set for the coordinate tier of the place spine: 435,000
    real locations, published by a department that is not Ordnance Survey, each
    of which should resolve to a district if that tier works.
    """
    _require(csv_path)
    con.execute("DROP TABLE IF EXISTS silver.naptan_node")
    con.execute(f"""
        CREATE TABLE silver.naptan_node AS
        SELECT trim(ATCOCode)                    AS atco_code,
               trim(CommonName)                  AS name,
               trim(LocalityName)                AS locality,
               trim(AdministrativeAreaCode)      AS admin_area_code,
               trim(StopType)                    AS stop_type,
               TRY_CAST(Easting  AS INTEGER)     AS easting,
               TRY_CAST(Northing AS INTEGER)     AS northing,
               TRY_CAST(Latitude  AS DOUBLE)     AS lat,
               TRY_CAST(Longitude AS DOUBLE)     AS long
        FROM read_csv('{csv_path}', header=true, all_varchar=true, ignore_errors=true)
        WHERE trim(ATCOCode) <> ''
    """)
    return con.execute("SELECT count(*) FROM silver.naptan_node").fetchone()[0]

def load_usrn_streets(con: duckdb.DuckDBPyConnection, zip_path: Path) -> int:
    """The national street register: every USRN, its type and where it is.

    Note what this product does not contain: a street name. Its columns are
    id, geometry, usrn and street_type, and nothing in OS Open USRN will tell
    you a street is called Acacia Avenue. What it gives is that the reference
    exists, what kind of street it is, and a coordinate -- so a USRN carried by
    another record can be checked against the register rather than trusted, and
    placed rather than only referenced.

    The archive holds a 963 MB GeoPackage, so it is extracted to a temporary
    directory and read through the spatial extension.
    """
    _require(zip_path)
    tmp = Path(tempfile.mkdtemp(prefix="gt-usrn-"))
    try:
        with zipfile.ZipFile(zip_path) as z:
            member = next((n for n in z.namelist() if n.endswith(".gpkg")), None)
            if member is None:
                raise LoadError(f"no GeoPackage inside {zip_path.name}")
            z.extract(member, tmp)
        gpkg = tmp / member
        con.execute("INSTALL spatial")
        con.execute("LOAD spatial")
        con.execute("DROP TABLE IF EXISTS silver.place_street")
        con.execute(f"""
            CREATE TABLE silver.place_street AS
            SELECT CAST(usrn AS BIGINT)                                AS usrn,
                   CAST(street_type AS VARCHAR)                        AS street_type,
                   CAST(round(ST_X(ST_Centroid(geometry))) AS INTEGER) AS easting,
                   CAST(round(ST_Y(ST_Centroid(geometry))) AS INTEGER) AS northing
            FROM ST_Read('{gpkg}')
            WHERE usrn IS NOT NULL
        """)
        con.execute("CREATE INDEX IF NOT EXISTS idx_street_usrn ON silver.place_street(usrn)")
        return con.execute("SELECT count(*) FROM silver.place_street").fetchone()[0]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

