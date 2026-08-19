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
