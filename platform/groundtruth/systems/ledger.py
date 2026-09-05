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
import re
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


# ---------------------------------------------------------------- location
# Why this exists, and why it recovers so little.
#
# The contribution records carry no geometry: 0 of 39,325, which the coverage
# figures have always said. The investigation behind this section went one step
# further and asked whether the location exists anywhere upstream.
#
#   1. developer-agreement-contribution   no geometry, no point            0%
#   2. developer-agreement (the parent)   no geometry, no point            0%
#      ...but 99% carry a `planning-application` reference.
#   3. planning-application               100,627 records, ~80% with a point
#
# So there is a published route from a contribution to a location, and the
# platform simply never registered the third dataset. That is a real gap and
# this closes it.
#
# It does not, however, make the money mappable. Of the 66 authorities that
# record contributions, 2 publish their planning applications to that dataset,
# so the chain closes for well under 1% of contributions. The rest is not a join
# this platform failed to make; it is a location no publisher has published.
#
# Every join here is qualified by authority. A planning reference is unique per
# council and not nationally -- 62% of contributions share a reference with a
# contribution in a different council -- so joining on the reference alone
# attaches one council's money to another council's site.
#
# Both numbers are reported. Fixing the join and quietly still showing zero
# would hide the fix; reporting the fix without the coverage would imply the
# money can now be mapped. Neither is true on its own.

def load_applications(con: duckdb.DuckDBPyConnection, applications: Path) -> int:
    """The planning applications, which are the only published carrier of a site."""
    con.execute("DROP TABLE IF EXISTS silver.planning_application")
    con.execute("""
        CREATE TABLE silver.planning_application (
          entity BIGINT, reference VARCHAR, organisation_entity BIGINT,
          longitude DOUBLE, latitude DOUBLE, decision_date VARCHAR
        )""")
    rows = json.loads(Path(applications).read_text())
    if isinstance(rows, dict):
        rows = rows.get("entities", rows.get("records", []))
    return insert_many(
        con, "INSERT INTO silver.planning_application VALUES (?,?,?,?,?,?)",
        [(_num(r.get("entity")), r.get("reference"), _num(r.get("organisation-entity")),
          *_point(r.get("point")), r.get("decision-date")) for r in rows])


def load_agreements(con: duckdb.DuckDBPyConnection, agreements: Path) -> int:
    """The agreements, which carry the reference that links the two."""
    con.execute("DROP TABLE IF EXISTS silver.developer_agreement")
    con.execute("""
        CREATE TABLE silver.developer_agreement (
          entity BIGINT, reference VARCHAR, organisation_entity BIGINT,
          planning_application VARCHAR, document_url VARCHAR
        )""")
    rows = json.loads(Path(agreements).read_text())
    if isinstance(rows, dict):
        rows = rows.get("entities", rows.get("records", []))
    return insert_many(
        con, "INSERT INTO silver.developer_agreement VALUES (?,?,?,?,?)",
        [(_num(r.get("entity")), r.get("reference"), _num(r.get("organisation-entity")),
          (r.get("planning-application") or "").strip() or None,
          r.get("document-url")) for r in rows])


def _point(raw) -> tuple[float | None, float | None]:
    """Read `POINT (lon lat)` as the publisher writes it.

    Returns a pair of Nones for anything unparseable rather than raising: a
    malformed point is one unlocated agreement, not a failed run.
    """
    if not raw or not str(raw).strip():
        return (None, None)
    m = re.match(r"\s*POINT\s*\(\s*([-\d.]+)\s+([-\d.]+)\s*\)\s*$", str(raw), re.I)
    if not m:
        return (None, None)
    try:
        return (float(m.group(1)), float(m.group(2)))
    except ValueError:
        return (None, None)


def locate(con: duckdb.DuckDBPyConnection, lads=None) -> dict:
    """Join contributions to a site, and report exactly how far it gets.

    The join is on the publisher's own key throughout -- contribution.agreement
    to agreement.reference, agreement.planning_application to application
    reference -- so nothing here is a name match and confidence is 1.0 for the
    link itself. The uncertainty is entirely in coverage, which is reported
    separately rather than folded into a confidence score.
    """
    for t in ("developer_agreement", "planning_application"):
        if not con.execute(
                "SELECT count(*) FROM information_schema.tables "
                "WHERE table_schema='silver' AND table_name=?", [t]).fetchone()[0]:
            return {"available": False,
                    "reason": f"silver.{t} not loaded -- run: gt backfill {t}"}

    con.execute("DROP TABLE IF EXISTS silver.agreement_location")
    con.execute("""
        CREATE TABLE silver.agreement_location AS
        SELECT a.reference                AS agreement,
               a.planning_application     AS application,
               a.organisation_entity      AS organisation_entity,
               p.longitude, p.latitude,
               1.0                        AS confidence,
               CAST(NULL AS VARCHAR)      AS lad
        FROM silver.developer_agreement a
        JOIN silver.planning_application p
          ON p.reference = a.planning_application
         AND p.organisation_entity = a.organisation_entity
        WHERE p.longitude IS NOT NULL AND p.latitude IS NOT NULL
    """)

    # District assignment is a spatial containment, not a nearest-neighbour
    # guess, so it is a derived fact rather than an estimate.
    if lads is not None:
        rows = con.execute(
            "SELECT agreement, organisation_entity, longitude, latitude "
            "FROM silver.agreement_location").fetchall()
        # Qualified by authority: an agreement reference is unique per council,
        # not nationally, so updating by reference alone would stamp one
        # council's district onto another's agreement.
        upd = [(lads.point(lon, lat), agr, org) for agr, org, lon, lat in rows]
        upd = [(code, agr, org) for code, agr, org in upd if code]
        if upd:
            con.executemany(
                "UPDATE silver.agreement_location SET lad = ? "
                "WHERE agreement = ? AND organisation_entity = ?", upd)

    total, located = con.execute("""
        SELECT count(*),
               count(*) FILTER (WHERE l.agreement IS NOT NULL)
        FROM silver.contribution c
        LEFT JOIN silver.agreement_location l
               ON l.agreement = c.agreement
              AND l.organisation_entity = c.organisation_entity
    """).fetchone()
    amount_total, amount_located = con.execute("""
        SELECT coalesce(sum(c.amount), 0),
               coalesce(sum(c.amount) FILTER (WHERE l.agreement IS NOT NULL), 0)
        FROM silver.contribution c
        LEFT JOIN silver.agreement_location l
               ON l.agreement = c.agreement
              AND l.organisation_entity = c.organisation_entity
    """).fetchone()

    return {
        "available": True,
        "contributions": total,
        "located": located,
        "located_pct": round(100.0 * located / total, 2) if total else 0.0,
        "amount_total": amount_total,
        "amount_located": amount_located,
        "amount_located_pct": (round(100.0 * amount_located / amount_total, 2)
                               if amount_total else 0.0),
    }


def location_gap(con: duckdb.DuckDBPyConnection, limit: int = 20) -> list[dict]:
    """Which authorities break the chain, and how much money is behind each.

    This is the useful output of the exercise. The platform cannot publish the
    missing applications, but it can say precisely who has not published them
    and what is unmappable as a result -- which is an answer no single dataset
    can give.
    """
    cur = con.execute("""
        SELECT COALESCE(pa.name, 'organisation ' || CAST(c.organisation_entity AS VARCHAR))
                                                     AS authority,
               count(*)                              AS contributions,
               round(coalesce(sum(c.amount), 0), 0)  AS amount,
               count(*) FILTER (WHERE l.agreement IS NOT NULL) AS located,
               count(DISTINCT c.agreement)           AS agreements
        FROM silver.contribution c
        LEFT JOIN silver.planning_authority pa ON pa.entity = c.organisation_entity
        LEFT JOIN silver.agreement_location l
               ON l.agreement = c.agreement
              AND l.organisation_entity = c.organisation_entity
        GROUP BY 1
        HAVING count(*) FILTER (WHERE l.agreement IS NOT NULL) = 0
        ORDER BY amount DESC NULLS LAST
        LIMIT ?
    """, [limit])
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]
