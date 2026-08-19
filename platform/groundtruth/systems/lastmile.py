"""Lastmile -- gigabit connectivity where new homes are actually being built.

Since 2022 building regulations have required new homes to be built gigabit
connectable. Nobody checks nationally, because the two halves of the question
are published by different bodies and never joined:

  * **Where new homes are.** HM Land Registry Price Paid data flags new-build
    transactions at address level, free and unregistered.
  * **What connectivity exists.** Building Digital UK publishes premises-level
    gigabit status keyed on the property reference, free and unregistered.

Ofcom's Connected Nations, the obvious third source, blocks automated retrieval
with HTTP 403 even from a browser user agent, so it is excluded.

The join here is on **postcode**, not property. Price Paid carries a postcode
and an address but no property reference; BDUK carries both. So this measures
the connectivity of the postcodes new homes are sold in, which is a good proxy
and not the same as measuring each home. That distinction is stated everywhere
the figures appear, and closing it properly needs the address-to-property
matching the place spine exists to do.
"""
from __future__ import annotations

import csv
import io
import shutil
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path

import duckdb

from ..place import normalise_postcode
from ..store import insert_many

# current_gigabit is a boolean flag. "Gigabit Grey/Black" lives in
# subsidy_control_status and means the market is already served, which is a
# different question -- confusing the two silently reports 0% coverage.
GIGABIT_TRUE = "true"


@dataclass(frozen=True)
class Coverage:
    premises: int
    with_uprn: int
    with_postcode: int
    gigabit_now: int
    new_build_sales: int
    matched_postcodes: int

    def pct(self, n: int, of: int | None = None) -> float:
        d = of or self.premises
        return 100 * n / d if d else 0.0


def load_premises(con: duckdb.DuckDBPyConnection, *zips: Path) -> int:
    """Load premises through DuckDB's own CSV reader.

    These files run to millions of rows. Inserting them a row at a time from
    Python is minutes of work for something the database does in seconds, so
    the archive members are expanded to a temporary directory and read natively,
    then removed.
    """
    con.execute("DROP TABLE IF EXISTS silver.premises_connectivity")
    con.execute("""
        CREATE TABLE silver.premises_connectivity (
          uprn VARCHAR, postcode_key VARCHAR, postcode VARCHAR,
          current_gigabit VARCHAR, future_gigabit VARCHAR,
          subsidy_status VARCHAR, lad_code VARCHAR, lad_name VARCHAR
        )""")
    total = 0
    for zp in zips:
        if not Path(zp).exists():
            continue
        tmp = Path(tempfile.mkdtemp(prefix="gt-bduk-"))
        try:
            with zipfile.ZipFile(zp) as z:
                members = [m for m in z.namelist() if m.lower().endswith(".csv")]
                for m in members:
                    with z.open(m) as src, open(tmp / Path(m).name, "wb") as dst:
                        shutil.copyfileobj(src, dst, length=1 << 20)
            con.execute(f"""
                INSERT INTO silver.premises_connectivity
                SELECT nullif(trim(uprn), '')                       AS uprn,
                       -- same normalisation the place spine uses
                       upper(replace(trim(postcode), ' ', ''))      AS postcode_key,
                       trim(postcode)                               AS postcode,
                       nullif(trim(current_gigabit), '')            AS current_gigabit,
                       nullif(trim(future_gigabit), '')             AS future_gigabit,
                       nullif(trim(subsidy_control_status), '')     AS subsidy_status,
                       nullif(trim(local_authority_district_ons_code), '') AS lad_code,
                       nullif(trim(local_authority_district_ons), '')      AS lad_name
                FROM read_csv('{tmp}/*.csv', header=true, all_varchar=true,
                              ignore_errors=true)
            """)
            total = con.execute(
                "SELECT count(*) FROM silver.premises_connectivity").fetchone()[0]
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    return total


def load_new_builds(con: duckdb.DuckDBPyConnection, ppd_csv: Path,
                    limit: int | None = None) -> int:
    """Price Paid transactions flagged as new build.

    The file has no header row; column order is fixed by the publisher.
    """
    con.execute("DROP TABLE IF EXISTS silver.new_build_sale")
    con.execute(f"""
        CREATE TABLE silver.new_build_sale AS
        SELECT column00 AS transaction_id,
               TRY_CAST(column01 AS DOUBLE)                AS price,
               substr(column02, 1, 10)                     AS sale_date,
               upper(replace(trim(column03), ' ', ''))     AS postcode_key,
               trim(column03)                              AS postcode,
               column04                                    AS property_type,
               column07                                    AS paon,
               column09                                    AS street
        FROM read_csv('{ppd_csv}', header=false, all_varchar=true, ignore_errors=true)
        WHERE column05 = 'Y'          -- the publisher's old/new flag
          AND trim(column03) <> ''
    """)
    return con.execute("SELECT count(*) FROM silver.new_build_sale").fetchone()[0]


def build(con: duckdb.DuckDBPyConnection) -> None:
    """Connectivity of the postcodes new homes are sold in."""
    con.execute("DROP TABLE IF EXISTS gold.lastmile_postcode")
    con.execute(f"""
        CREATE TABLE gold.lastmile_postcode AS
        SELECT p.postcode_key,
               any_value(p.lad_name)                                  AS lad_name,
               count(*)                                               AS premises,
               count(*) FILTER (WHERE lower(p.current_gigabit) = '{GIGABIT_TRUE}')
                                                                      AS gigabit_now,
               round(100.0 * count(*) FILTER (WHERE lower(p.current_gigabit) = '{GIGABIT_TRUE}')
                     / count(*), 1)                                   AS gigabit_pct,
               count(DISTINCT s.transaction_id)                       AS new_build_sales
        FROM silver.premises_connectivity p
        LEFT JOIN silver.new_build_sale s USING (postcode_key)
        WHERE p.postcode_key IS NOT NULL
        GROUP BY p.postcode_key
    """)

    con.execute("DROP TABLE IF EXISTS gold.lastmile_authority")
    con.execute("""
        CREATE TABLE gold.lastmile_authority AS
        SELECT lad_name,
               sum(premises)                                          AS premises,
               sum(gigabit_now)                                       AS gigabit_now,
               round(100.0 * sum(gigabit_now) / nullif(sum(premises), 0), 1)
                                                                      AS gigabit_pct,
               sum(new_build_sales)                                   AS new_build_sales,
               -- connectivity of postcodes that saw a new-build sale, against all
               round(100.0 * sum(gigabit_now) FILTER (WHERE new_build_sales > 0)
                     / nullif(sum(premises) FILTER (WHERE new_build_sales > 0), 0), 1)
                                                                      AS gigabit_pct_new_build
        FROM gold.lastmile_postcode
        WHERE lad_name IS NOT NULL
        GROUP BY lad_name
        ORDER BY premises DESC
    """)


def comparison(con: duckdb.DuckDBPyConnection):
    """Gigabit availability in new-build postcodes against everywhere else."""
    return con.execute(f"""
        SELECT
          sum(premises) FILTER (WHERE new_build_sales > 0)            AS nb_premises,
          sum(gigabit_now) FILTER (WHERE new_build_sales > 0)         AS nb_gigabit,
          round(100.0 * sum(gigabit_now) FILTER (WHERE new_build_sales > 0)
                / nullif(sum(premises) FILTER (WHERE new_build_sales > 0), 0), 1),
          sum(premises) FILTER (WHERE new_build_sales = 0)            AS other_premises,
          round(100.0 * sum(gigabit_now) FILTER (WHERE new_build_sales = 0)
                / nullif(sum(premises) FILTER (WHERE new_build_sales = 0), 0), 1)
        FROM gold.lastmile_postcode
    """).fetchone()
