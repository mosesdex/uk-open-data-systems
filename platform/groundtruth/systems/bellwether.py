"""Bellwether -- provider concentration in care and education.

The question a council cannot currently answer: how much of our capacity sits
with one company, and which other councils depend on the same company? Each
authority sees only its own contracts, so a provider that is systemically
important across eleven councils looks unremarkable in each.

Two sectors, one method:

  * care -- CQC publishes a company number and a bed count per location
  * education -- the school register publishes a trust identifier per school

Care is the easier case precisely because the regulator already publishes the
identifier. Education is not: the trust identifier is a departmental code, not
a company number, so the two sectors cannot yet be joined to each other. That
limit is reported rather than papered over.

Concentration is reported at two levels, because neither alone is honest:

  * **legal entity** -- exact, keyed on the company number. Understates a group
    that trades through several companies. Care UK runs Islington homes through
    two numbered entities; each looks like 26.8% of the borough, the group is
    53.6%.
  * **group** -- keyed on the regulator's brand field. Catches the above, but
    the field is imperfect: 49% of care-home beds are unbranded, and it mixes
    operator brand with owner group. "Care UK Community Partnerships Ltd" is
    branded Welltower, after the investment trust that owns the property, not
    the company that runs the home.

Both are published, labelled, with the unbranded share stated.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import duckdb

from .. import entity
from ..ods import table

# Column names, not positions: the published header pads itself out with
# repeated empty cells, so positions are not stable between releases.
COL_BEDS = "Care homes beds"
COL_LA = "Location Local Authority"
COL_COMPANY = "Provider Companies House Number"
COL_PROVIDER = "Provider Name"
COL_BRAND = "Brand Name"
COL_LOCATION = "Location Name"
COL_TYPE = "Location Type/Sector"


@dataclass(frozen=True)
class SectorCoverage:
    rows: int
    with_identifier: int
    label: str

    @property
    def identified_pct(self) -> float:
        return 100 * self.with_identifier / self.rows if self.rows else 0.0


def _index(header: list[str]) -> dict[str, int]:
    return {name.strip(): i for i, name in enumerate(header) if name.strip()}


def _get(row: list[str], idx: dict[str, int], col: str) -> str:
    i = idx.get(col)
    return row[i].strip() if i is not None and i < len(row) else ""


def _int(v: str) -> int:
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return 0


def load_care(con: duckdb.DuckDBPyConnection, ods_path: Path) -> SectorCoverage:
    """Load CQC locations, resolving each provider to a company number."""
    records, idx = [], None
    identified = 0
    for header, row in table(ods_path):
        if idx is None:
            idx = _index(header)
        num = entity.normalise_company_number(_get(row, idx, COL_COMPANY))
        if num:
            identified += 1
        records.append((
            _get(row, idx, COL_LOCATION),
            _get(row, idx, COL_LA),
            _get(row, idx, COL_TYPE),
            _int(_get(row, idx, COL_BEDS)),
            num,
            _get(row, idx, COL_PROVIDER),
            entity.normalise_name(_get(row, idx, COL_PROVIDER)),
            _get(row, idx, COL_BRAND),
        ))

    con.execute("DROP TABLE IF EXISTS silver.care_location")
    con.execute("""
        CREATE TABLE silver.care_location (
          location VARCHAR, local_authority VARCHAR, sector VARCHAR,
          beds INTEGER, company_number VARCHAR, provider VARCHAR,
          provider_key VARCHAR, brand VARCHAR
        )""")
    con.executemany(
        "INSERT INTO silver.care_location VALUES (?,?,?,?,?,?,?,?)", records)
    return SectorCoverage(len(records), identified, "care")


def build(con: duckdb.DuckDBPyConnection) -> None:
    """Concentration per authority, by company where known and by name otherwise."""
    con.execute("DROP TABLE IF EXISTS gold.bellwether_care")
    con.execute("""
        CREATE TABLE gold.bellwether_care AS
        WITH by_provider AS (
          SELECT local_authority,
                 COALESCE(company_number, 'name:' || provider_key) AS provider_id,
                 any_value(provider)      AS provider,
                 any_value(company_number) AS company_number,
                 count(*)                 AS locations,
                 sum(beds)                AS beds
          FROM silver.care_location
          WHERE local_authority <> '' AND beds > 0
          GROUP BY local_authority, provider_id
        ),
        totals AS (
          SELECT local_authority, sum(beds) AS la_beds, sum(locations) AS la_locations
          FROM by_provider GROUP BY local_authority
        )
        SELECT p.local_authority, p.provider, p.company_number,
               p.locations, p.beds, t.la_beds,
               round(100.0 * p.beds / nullif(t.la_beds, 0), 1) AS share_pct
        FROM by_provider p JOIN totals t USING (local_authority)
        WHERE t.la_beds > 0
        ORDER BY share_pct DESC
    """)

    # A provider's footprint across authorities: the view no single council has.
    con.execute("DROP TABLE IF EXISTS gold.bellwether_footprint")
    con.execute("""
        CREATE TABLE gold.bellwether_footprint AS
        SELECT COALESCE(company_number, 'name:' || provider_key) AS provider_id,
               any_value(provider)                    AS provider,
               any_value(company_number)              AS company_number,
               count(DISTINCT local_authority)        AS authorities,
               count(*)                               AS locations,
               sum(beds)                              AS beds
        FROM silver.care_location
        WHERE beds > 0
        GROUP BY provider_id
        HAVING count(DISTINCT local_authority) > 1
        ORDER BY beds DESC
    """)


UNBRANDED = "-"


def build_groups(con: duckdb.DuckDBPyConnection) -> None:
    """Concentration rolled up to the group, where the regulator names one.

    Unbranded providers are treated as their own group rather than pooled: the
    placeholder means "no group", not "all the same group".
    """
    con.execute("DROP TABLE IF EXISTS gold.bellwether_group")
    con.execute(f"""
        CREATE TABLE gold.bellwether_group AS
        WITH keyed AS (
          SELECT local_authority, beds,
                 CASE WHEN brand IS NULL OR brand = '' OR brand = '{UNBRANDED}'
                      THEN 'entity:' || COALESCE(company_number, provider_key)
                      ELSE 'group:' || brand END      AS group_id,
                 CASE WHEN brand IS NULL OR brand = '' OR brand = '{UNBRANDED}'
                      THEN provider ELSE brand END    AS group_name,
                 (brand IS NOT NULL AND brand <> '' AND brand <> '{UNBRANDED}') AS branded
          FROM silver.care_location WHERE beds > 0 AND local_authority <> ''
        ),
        per_la AS (
          SELECT local_authority, group_id, any_value(group_name) AS group_name,
                 any_value(branded) AS branded,
                 count(*) AS locations, sum(beds) AS beds
          FROM keyed GROUP BY local_authority, group_id
        ),
        totals AS (
          SELECT local_authority, sum(beds) AS la_beds FROM per_la GROUP BY local_authority
        )
        SELECT p.local_authority, p.group_name, p.branded, p.locations, p.beds,
               t.la_beds, round(100.0 * p.beds / nullif(t.la_beds, 0), 1) AS share_pct
        FROM per_la p JOIN totals t USING (local_authority)
        ORDER BY share_pct DESC
    """)


def systemic(con: duckdb.DuckDBPyConnection, limit: int = 10):
    """Groups whose failure would touch many authorities at once."""
    return con.execute(f"""
        SELECT brand,
               count(DISTINCT local_authority) AS authorities,
               count(DISTINCT company_number)  AS companies,
               count(*)                        AS locations,
               sum(beds)                       AS beds
        FROM silver.care_location
        WHERE beds > 0 AND brand IS NOT NULL AND brand <> '' AND brand <> '{UNBRANDED}'
        GROUP BY brand
        ORDER BY beds DESC LIMIT {limit}
    """).fetchall()


def unbranded_share(con: duckdb.DuckDBPyConnection) -> float:
    """Share of beds the group view cannot see. Travels with every group figure."""
    row = con.execute(f"""
        SELECT sum(beds) FILTER (WHERE brand = '{UNBRANDED}' OR brand IS NULL OR brand = ''),
               sum(beds)
        FROM silver.care_location WHERE beds > 0""").fetchone()
    return round(100.0 * (row[0] or 0) / (row[1] or 1), 1)


def name_variants(con: duckdb.DuckDBPyConnection, limit: int = 10):
    """Where one company trades under several spellings.

    This is the correction that changes a provider's apparent size: the entity
    spine collapses the variants, the raw register does not.
    """
    return con.execute(f"""
        SELECT company_number,
               count(DISTINCT provider) AS spellings,
               sum(beds)                AS beds,
               any_value(provider)      AS example
        FROM silver.care_location
        WHERE company_number IS NOT NULL AND beds > 0
        GROUP BY company_number
        HAVING count(DISTINCT provider) > 1
        ORDER BY spellings DESC, beds DESC
        LIMIT {limit}
    """).fetchall()
