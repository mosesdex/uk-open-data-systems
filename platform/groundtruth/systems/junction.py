"""Junction -- grid connection capacity, and whether it can be compared at all.

The earlier research corrected an assumption: the problem is not that network
operators refuse to publish embedded capacity registers. They publish them. The
problem is that the same regulatory return arrives in incompatible shapes, so
the numbers cannot be put side by side.

Building it corrected the assumption a second time, in the opposite direction.

**The schemas are not the problem.** The four embedded capacity registers share
53 field names and run to 58-63 columns each. Ofgem mandated a common format and
the operators followed it. An earlier version of this analysis reported 1.3%
commonality, which was wrong: it had compared three genuine registers against an
LTDS appendix table, which is a different return entirely.

**Availability is the problem.** Each portal's catalogue reports thousands of
records, and the anonymous export returns a column header and nothing else for
three of the four:

    operator                catalogue    export
    UK Power Networks           4,496         0
    Northern Powergrid            937       937
    Electricity North West        567         0
    SP Energy Networks            770         0

The datasets are not empty. They are listed, dated, and sized, and the open
route returns none of it. A connector applying to the wrong network cannot find
that out from the published data.

One more access quirk worth knowing: `/records` returns HTTP 403 to an anonymous
client on these portals while `/exports/csv` returns 200 for the same dataset.
Anyone testing the obvious endpoint concludes the data is closed. It is not.
"""
from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from pathlib import Path

import duckdb

from ..place import resolve_coordinate, resolve_postcode
from ..store import insert_many

EXPORT = "{base}/api/explore/v2.1/catalog/datasets/{ds}/exports/csv"

# The four registers reachable without an account, and the operator each belongs
# to. Dataset identifiers differ per operator for the same regulatory return.
REGISTERS = (
    ("UK Power Networks", "https://ukpowernetworks.opendatasoft.com",
     "ukpn-embedded-capacity-register-1-under-1mw"),
    ("Northern Powergrid", "https://northernpowergrid.opendatasoft.com",
     "embedded-capacity-register"),
    ("Electricity North West", "https://electricitynorthwest.opendatasoft.com",
     "enwl-embedded-capacity-register-2-1mw-and-above"),
    ("SP Energy Networks", "https://spenergynetworks.opendatasoft.com",
     "embedded-capacity-register"),
)


@dataclass(frozen=True)
class RegisterState:
    operator: str
    dataset: str
    http_status: int
    fields: tuple[str, ...]
    rows: int
    catalogue_records: int | None = None

    @property
    def publishes_schema(self) -> bool:
        return bool(self.fields)

    @property
    def publishes_data(self) -> bool:
        return self.rows > 0

    @property
    def withheld(self) -> int:
        """Records the catalogue claims that the open export does not return."""
        if self.catalogue_records is None:
            return 0
        return max(0, self.catalogue_records - self.rows)


def parse_export(text: str) -> tuple[list[str], list[dict]]:
    """Opendatasoft exports are semicolon delimited."""
    if not text.strip():
        return [], []
    delimiter = ";" if text.count(";") > text.count(",") else ","
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    fields = [f for f in (reader.fieldnames or []) if f]
    return fields, list(reader)


def capacity_fields(fields) -> list[str]:
    return sorted(f for f in fields if "capacity" in f.lower())


def catalogue_gap(states: list[RegisterState]) -> dict:
    """Records the catalogues advertise against records the open route returns."""
    advertised = sum(s.catalogue_records or 0 for s in states)
    returned = sum(s.rows for s in states)
    return {"advertised": advertised, "returned": returned,
            "withheld": advertised - returned,
            "operators_serving_data": sum(1 for s in states if s.publishes_data),
            "operators": len(states)}


def compare(states: list[RegisterState]) -> dict:
    """How far the registers diverge, over those that publish a schema."""
    withschema = [s for s in states if s.publishes_schema]
    if len(withschema) < 2:
        return {"comparable": False, "reason": "fewer than two schemas available"}
    sets = {s.operator: set(s.fields) for s in withschema}
    common = set.intersection(*sets.values())
    union = set.union(*sets.values())
    return {
        "comparable": True,
        "operators": len(sets),
        "distinct_fields": len(union),
        "shared_fields": len(common),
        "shared_pct": round(100 * len(common) / len(union), 1) if union else 0.0,
        "per_operator": {
            op: {"fields": len(f), "not_shared": len(f - common),
                 "capacity_fields": capacity_fields(f)}
            for op, f in sets.items()
        },
        "shared": sorted(common),
    }


def load(con: duckdb.DuckDBPyConnection, states: list[RegisterState]) -> None:
    con.execute("DROP TABLE IF EXISTS gold.junction_register")
    con.execute("""
        CREATE TABLE gold.junction_register (
          operator VARCHAR, dataset VARCHAR, http_status INTEGER,
          field_count INTEGER, rows BIGINT, catalogue_records BIGINT,
          withheld BIGINT, publishes_schema BOOLEAN, publishes_data BOOLEAN,
          capacity_field_count INTEGER
        )""")
    insert_many(con, "INSERT INTO gold.junction_register VALUES (?,?,?,?,?,?,?,?,?,?)",
                [(s.operator, s.dataset, s.http_status, len(s.fields), s.rows,
                  s.catalogue_records, s.withheld, s.publishes_schema,
                  s.publishes_data, len(capacity_fields(s.fields))) for s in states])


# The four registers are published separately, with the same columns under the
# same names but semicolon delimited. Loaded into one silver table so the
# question is asked once, of every operator, rather than four times.
_ECR = {
    "UKPN": "dno_ecr_ukpn.csv",
    "NPG": "dno_ecr_npg.csv",
    "ENWL": "dno_ecr_enwl.csv",
    "SPEN": "dno_ecr_spen.csv",
}

# Every column name is shared across the four files except this one. SP Energy
# Networks writes "xcoordinate"/"ycoordinate" (no underscore before the word
# "coordinate") where UKPN, NPG and ENWL all write "x_coordinate"/"y_coordinate"
# for the identical field. Confirmed by reading each file's own header rather
# than assumed from the brief, because Ofgem mandates the return, not the exact
# spelling, and a publisher can drift from the other three without drifting
# from the standard. Resolved per file below instead of hand-mapped per
# operator, so a header that is later corrected upstream, or a fifth operator
# added under either spelling, is picked up without a code change.
_EASTING_NAMES = ("location_x_coordinate_eastings_where_data_is_held",
                  "location_xcoordinate_eastings_where_data_is_held")
_NORTHING_NAMES = ("location_y_coordinate_northings_where_data_is_held",
                   "location_ycoordinate_northings_where_data_is_held")


def _pick_column(columns: list[str], candidates: tuple[str, ...], path: Path) -> str:
    for name in candidates:
        if name in columns:
            return name
    raise ValueError(f"{path.name}: none of {candidates} found in header {columns}")


def load_connections(con: duckdb.DuckDBPyConnection, bronze: Path) -> int:
    """Every operator's capacity register, as one table."""
    con.execute("DROP TABLE IF EXISTS silver.junction_connection")
    con.execute("""CREATE TABLE silver.junction_connection
                   (operator VARCHAR, postcode VARCHAR, easting INTEGER, northing INTEGER,
                    connection_status VARCHAR, connected_mw DOUBLE, accepted_mw DOUBLE)""")
    loaded = 0
    for operator, filename in _ECR.items():
        path = bronze / filename
        if not path.exists():
            continue
        # Read the file's own header before trusting either candidate spelling
        # of the eastings/northings columns -- see _EASTING_NAMES above.
        columns = [d[0] for d in con.execute(
            "SELECT * FROM read_csv(?, delim=';', header=true, all_varchar=true, "
            "ignore_errors=true) LIMIT 0", [str(path)]).description]
        easting_col = _pick_column(columns, _EASTING_NAMES, path)
        northing_col = _pick_column(columns, _NORTHING_NAMES, path)
        con.execute(f"""
            INSERT INTO silver.junction_connection
            SELECT ?,
                   nullif(trim(postcode), ''),
                   try_cast("{easting_col}" AS INTEGER),
                   try_cast("{northing_col}" AS INTEGER),
                   connection_status,
                   coalesce(try_cast(already_connected_registered_capacity_mw AS DOUBLE), 0),
                   coalesce(try_cast(accepted_to_connect_registered_capacity_mw AS DOUBLE), 0)
            FROM read_csv(?, delim=';', header=true, all_varchar=true,
                          ignore_errors=true)
        """, [operator, str(path)])
        loaded = con.execute("SELECT count(*) FROM silver.junction_connection").fetchone()[0]
    return loaded


def by_district(con: duckdb.DuckDBPyConnection) -> None:
    """Connections and capacity per district, with how many rows were placeable.

    A register row carries a postcode, a grid reference, both, or neither. The
    postcode is preferred because it is the publisher's own statement of where
    the connection is; the grid reference is the fallback, through the same
    nearest-centroid tier every other coordinate-placed figure uses. A row with
    neither is not dropped quietly: placed_pct says what share of the rows
    behind a district's figure could be located at all.
    """
    rows = con.execute("""
        SELECT postcode, easting, northing, connected_mw, accepted_mw
        FROM silver.junction_connection
    """).fetchall()

    agg: dict[str, list] = {}
    placed = unplaced = 0
    for postcode, easting, northing, connected, accepted in rows:
        ref = resolve_postcode(con, postcode) if postcode else None
        if ref is None or ref.lad_code is None:
            ref = resolve_coordinate(con, easting, northing)
        if ref.lad_code is None:
            unplaced += 1
            continue
        placed += 1
        a = agg.setdefault(ref.lad_code, [0, 0.0, 0.0])
        a[0] += 1
        a[1] += connected or 0.0
        a[2] += accepted or 0.0

    total = placed + unplaced
    pct = round(100 * placed / total, 1) if total else 0.0

    con.execute("DROP TABLE IF EXISTS gold.junction_district")
    con.execute("""CREATE TABLE gold.junction_district
                   (lad_code VARCHAR, connections INTEGER,
                    connected_mw DOUBLE, accepted_mw DOUBLE, placed_pct DOUBLE)""")
    if agg:
        con.executemany(
            "INSERT INTO gold.junction_district VALUES (?, ?, ?, ?, ?)",
            [(c, v[0], round(v[1], 2), round(v[2], 2), pct) for c, v in agg.items()])
