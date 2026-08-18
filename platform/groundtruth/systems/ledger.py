"""Ledger -- developer contributions traced to the site.

When planning permission is granted, developers agree to pay for schools, roads
and affordable housing. Nationally that is £1.49bn of recorded obligations. The
records exist. What they do not carry is a location: across all 39,325
contributions, **not one** has a geometry or a point.

So the money cannot be mapped, and "what was promised for this site, and did it
arrive" is unanswerable -- not because the data is secret, but because the
spatial join was never made.

Two things this system is careful about:

  * **The total is over the records that state an amount.** Only 70.4% of
    contributions do. A headline that implies the other 29.6% are worth nothing
    is wrong, and the coverage is published with the figure.
  * **Promised is not delivered.** The transaction table carries a funding
    status, so contributions that were agreed can be separated from those
    actually received and spent. That distinction is the point of the system.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import duckdb

from ..store import insert_many


@dataclass(frozen=True)
class Coverage:
    contributions: int
    with_amount: int
    with_purpose: int
    with_geometry: int
    transactions: int
    with_status: int

    def pct(self, n: int, of: int | None = None) -> float:
        d = of or self.contributions
        return 100 * n / d if d else 0.0


def _num(v):
    try:
        f = float(v)
        return f if f == f else None      # reject NaN
    except (TypeError, ValueError):
        return None


def _blank(v) -> bool:
    return v is None or not str(v).strip()


def load(con: duckdb.DuckDBPyConnection, contributions: Path,
         transactions: Path, authorities: Path) -> Coverage:
    con.execute("DROP TABLE IF EXISTS silver.contribution")
    con.execute("""
        CREATE TABLE silver.contribution (
          entity BIGINT, reference VARCHAR, organisation_entity BIGINT,
          agreement VARCHAR, purpose VARCHAR, amount DOUBLE, units DOUBLE,
          start_date VARCHAR, has_geometry BOOLEAN
        )""")
    crows = json.loads(Path(contributions).read_text())
    insert_many(con, 
        "INSERT INTO silver.contribution VALUES (?,?,?,?,?,?,?,?,?)",
        [(_num(r.get("entity")), r.get("reference"), _num(r.get("organisation-entity")),
          r.get("developer-agreement"), (r.get("contribution-purpose") or "").strip() or None,
          _num(r.get("amount")), _num(r.get("units")), r.get("start-date"),
          not (_blank(r.get("geometry")) and _blank(r.get("point")))) for r in crows])

    con.execute("DROP TABLE IF EXISTS silver.contribution_transaction")
    con.execute("""
        CREATE TABLE silver.contribution_transaction (
          entity BIGINT, reference VARCHAR, organisation_entity BIGINT,
          contribution VARCHAR, status VARCHAR, amount DOUBLE, start_date VARCHAR
        )""")
    trows = json.loads(Path(transactions).read_text())
    insert_many(con, 
        "INSERT INTO silver.contribution_transaction VALUES (?,?,?,?,?,?,?)",
        [(_num(r.get("entity")), r.get("reference"), _num(r.get("organisation-entity")),
          r.get("developer-agreement-contribution"),
          (r.get("contribution-funding-status") or "").strip() or None,
          _num(r.get("amount")), r.get("start-date")) for r in trows])

    con.execute("DROP TABLE IF EXISTS silver.planning_authority")
    con.execute("CREATE TABLE silver.planning_authority (entity BIGINT PRIMARY KEY, name VARCHAR)")
    insert_many(con, "INSERT OR IGNORE INTO silver.planning_authority VALUES (?,?)",
                    [(_num(r.get("entity")), r.get("name"))
                     for r in json.loads(Path(authorities).read_text())])

    c = con.execute("""
        SELECT count(*), count(amount), count(purpose), count(*) FILTER (WHERE has_geometry)
        FROM silver.contribution""").fetchone()
    t = con.execute("""
        SELECT count(*), count(status) FROM silver.contribution_transaction""").fetchone()
    return Coverage(c[0], c[1], c[2], c[3], t[0], t[1])


def build(con: duckdb.DuckDBPyConnection) -> None:
    con.execute("DROP TABLE IF EXISTS gold.ledger_authority")
    con.execute("""
        CREATE TABLE gold.ledger_authority AS
        SELECT COALESCE(a.name, 'organisation ' || c.organisation_entity) AS authority,
               count(*)                                   AS contributions,
               count(c.amount)                            AS with_amount,
               round(sum(c.amount), 0)                    AS total_amount,
               round(100.0 * count(c.amount) / count(*), 1) AS amount_coverage_pct,
               count(*) FILTER (WHERE c.has_geometry)     AS with_location
        FROM silver.contribution c
        LEFT JOIN silver.planning_authority a ON a.entity = c.organisation_entity
        GROUP BY 1 ORDER BY total_amount DESC NULLS LAST
    """)

    con.execute("DROP TABLE IF EXISTS gold.ledger_purpose")
    con.execute("""
        CREATE TABLE gold.ledger_purpose AS
        SELECT COALESCE(purpose, 'not stated')       AS purpose,
               count(*)                              AS contributions,
               count(amount)                         AS with_amount,
               round(sum(amount), 0)                 AS total_amount
        FROM silver.contribution
        GROUP BY 1 ORDER BY total_amount DESC NULLS LAST
    """)

    # Promised against delivered: the distinction the system exists to make.
    con.execute("DROP TABLE IF EXISTS gold.ledger_funding_status")
    con.execute("""
        CREATE TABLE gold.ledger_funding_status AS
        SELECT COALESCE(status, 'not stated')  AS status,
               count(*)                        AS transactions,
               count(amount)                   AS with_amount,
               round(sum(amount), 0)           AS total_amount
        FROM silver.contribution_transaction
        GROUP BY 1 ORDER BY total_amount DESC NULLS LAST
    """)


def national_total(con: duckdb.DuckDBPyConnection) -> tuple[float, int, int]:
    """Total, and the record counts it is computed over."""
    return con.execute("""
        SELECT round(sum(amount), 0), count(amount), count(*) FROM silver.contribution
    """).fetchone()
