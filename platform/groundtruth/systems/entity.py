"""The organisation knowledge graph — the WHO spine made queryable.

Every system that names an organisation resolves it to a Companies House number.
This module gathers those numbers into one entity table: for each company, what
it does in the care sector (Bellwether) and in public procurement (Sentinel),
who controls it (persons of significant control), and what the register says
about it. The point is the cross-system join — a company that appears in more
than one system is a single organisation seen from two angles, and that link is
only ever drawn where the same company number genuinely appears in both.

Nothing here is invented: an organisation is listed in a system only if its
company number is present in that system's own records.
"""
from __future__ import annotations

import duckdb


def build(con: duckdb.DuckDBPyConnection) -> None:
    # Per-company footprint in the care sector.
    con.execute("DROP TABLE IF EXISTS gold.entity_care_agg")
    con.execute("""
        CREATE TABLE gold.entity_care_agg AS
        SELECT upper(trim(company_number))                AS cn,
               any_value(provider)                        AS provider,
               any_value(nullif(brand, ''))               AS brand,
               count(DISTINCT location)                   AS locations,
               sum(beds)                                  AS beds,
               count(DISTINCT local_authority)            AS authorities
        FROM silver.care_location
        WHERE company_number IS NOT NULL AND trim(company_number) <> ''
        GROUP BY 1
    """)

    # Per-company footprint in public procurement.
    con.execute("DROP TABLE IF EXISTS gold.entity_proc_agg")
    con.execute("""
        CREATE TABLE gold.entity_proc_agg AS
        SELECT upper(trim(company_number))                AS cn,
               any_value(supplier)                        AS supplier,
               count(*)                                   AS awards,
               round(sum(value))                          AS value,
               count(DISTINCT buyer)                      AS buyers
        FROM silver.procurement_award
        WHERE company_number IS NOT NULL AND trim(company_number) <> ''
        GROUP BY 1
    """)

    # The entity table: one row per company seen in any system, with what the
    # register knows and which systems it appears in.
    con.execute("DROP TABLE IF EXISTS gold.entity")
    con.execute("""
        CREATE TABLE gold.entity AS
        SELECT COALESCE(c.cn, p.cn)                        AS company_number,
               COALESCE(co.name, c.provider, p.supplier)   AS name,
               co.status, co.post_town, co.incorporated, co.sic_1,
               c.brand,
               c.locations   AS care_locations, c.beds AS care_beds,
               c.authorities AS care_authorities,
               p.awards      AS proc_awards, p.value AS proc_value,
               p.buyers      AS proc_buyers,
               (c.cn IS NOT NULL)                          AS in_care,
               (p.cn IS NOT NULL)                          AS in_proc
        FROM gold.entity_care_agg c
        FULL OUTER JOIN gold.entity_proc_agg p ON c.cn = p.cn
        LEFT JOIN silver.company co ON co.company_number = COALESCE(c.cn, p.cn)
    """)


def summary(con: duckdb.DuckDBPyConnection):
    return con.execute("""
        SELECT count(*)                              AS entities,
               count(*) FILTER (WHERE in_care)       AS in_care,
               count(*) FILTER (WHERE in_proc)       AS in_proc,
               count(*) FILTER (WHERE in_care AND in_proc) AS cross_system
        FROM gold.entity
    """).fetchone()
