"""Sentinel -- procurement integrity, within what UK data actually supports.

Two standard screens are impossible here, and saying so up front is more useful
than implying otherwise:

  * **Price screens are impossible.** Bid prices are not published in UK
    procurement data, so the whole family of statistical price-pattern tests
    cannot be run.
  * **Single-bidder rates are impossible.** `numberOfTenderers` is present on
    **none** of the notices sampled, so "how many suppliers competed" cannot be
    answered from the feed.

What remains is structural, and it is what the research identified as the most
tractable signal available: concentration. Who wins repeatedly from whom, how
much of a buyer's spend goes to one supplier, and how often competition is
skipped altogether through direct award.

None of this is an accusation. Concentration has innocent explanations --
specialist markets, small local supplier bases, genuine incumbency. Sentinel
surfaces the pattern and the buyer investigates; it does not score anyone.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import duckdb

from .. import entity
from ..store import insert_many

# Methods that skip open competition. 'direct' is an award with no competition
# at all; 'limited' restricts who may bid.
UNCOMPETED = ("direct", "limited")
# Above this many suppliers on one contract it is a framework, not a competed
# award, and shared control between two of them is not a collusion signal.
MAX_COMPETED_FIELD = 6


@dataclass(frozen=True)
class Coverage:
    releases: int
    awards: int
    with_value: int
    with_method: int
    with_tenderer_count: int
    suppliers_identified: int
    identified_via_register: int = 0

    def pct(self, n: int, of: int | None = None) -> float:
        d = of or self.releases
        return 100 * n / d if d else 0.0


def load(con: duckdb.DuckDBPyConnection, *paths: Path) -> Coverage:
    rows = []
    releases = awards = with_value = with_method = with_tenderers = identified = 0
    via_register = 0

    for path in paths:
        if not Path(path).exists():
            continue
        doc = json.loads(Path(path).read_text())
        for rel in doc.get("releases", []):
            releases += 1
            tender = rel.get("tender") or {}
            buyer = rel.get("buyer") or {}
            method = tender.get("procurementMethod")
            if method:
                with_method += 1
            if tender.get("numberOfTenderers") is not None:
                with_tenderers += 1

            party_num = {}
            for p in rel.get("parties", []) or []:
                ident = p.get("identifier") or {}
                if ident.get("scheme") == "GB-COH" and ident.get("id"):
                    party_num[p.get("id")] = str(ident["id"])

            for award in rel.get("awards", []) or []:
                value = (award.get("value") or {}).get("amount")
                if value:
                    with_value += 1
                for sup in award.get("suppliers", []) or []:
                    awards += 1
                    num = entity.normalise_company_number(party_num.get(sup.get("id")))
                    if num:
                        identified += 1
                    else:
                        # Nothing published a number for this supplier. Ask the
                        # register directly; an unambiguous hit is recorded, an
                        # ambiguous one is left unresolved rather than guessed.
                        ref = entity.resolve_in_register(con, name=sup.get("name"))
                        if ref.resolved:
                            num = ref.company_number
                            identified += 1
                            via_register += 1
                    rows.append((
                        rel.get("ocid"), str(buyer.get("id") or ""),
                        (buyer.get("name") or "").strip(),
                        (sup.get("name") or "").strip(),
                        entity.normalise_name(sup.get("name") or ""),
                        num, method, tender.get("procurementMethodDetails"),
                        tender.get("mainProcurementCategory"),
                        float(value) if value else None,
                        str(award.get("date") or "")[:10],
                    ))

    con.execute("DROP TABLE IF EXISTS silver.procurement_award")
    con.execute("""
        CREATE TABLE silver.procurement_award (
          ocid VARCHAR, buyer_id VARCHAR, buyer VARCHAR,
          supplier VARCHAR, supplier_key VARCHAR, company_number VARCHAR,
          method VARCHAR, method_detail VARCHAR, category VARCHAR,
          value DOUBLE, award_date VARCHAR
        )""")
    insert_many(con, "INSERT INTO silver.procurement_award VALUES (?,?,?,?,?,?,?,?,?,?,?)", rows)
    return Coverage(releases, awards, with_value, with_method, with_tenderers,
                    identified, via_register)


def build(con: duckdb.DuckDBPyConnection) -> None:
    """Concentration measures. Signals to investigate, not verdicts."""
    shared_control(con)
    build_footprint(con)
    con.execute("DROP TABLE IF EXISTS gold.sentinel_buyer")
    con.execute(f"""
        CREATE TABLE gold.sentinel_buyer AS
        WITH per_pair AS (
          SELECT buyer, COALESCE(company_number, 'name:' || supplier_key) AS supplier_id,
                 any_value(supplier) AS supplier,
                 count(*) AS awards, sum(value) AS value
          FROM silver.procurement_award
          WHERE buyer <> '' AND supplier_key <> ''
          GROUP BY buyer, supplier_id
        ),
        buyer_tot AS (
          SELECT buyer, count(*) AS suppliers, sum(awards) AS awards,
                 sum(value) AS value
          FROM per_pair GROUP BY buyer
        )
        SELECT t.buyer, t.suppliers, t.awards, round(t.value) AS total_value,
               round(100.0 * max(p.awards) / t.awards, 1)          AS top_supplier_award_share,
               round(100.0 * max(p.value) / nullif(t.value, 0), 1) AS top_supplier_value_share
        FROM buyer_tot t JOIN per_pair p USING (buyer)
        GROUP BY t.buyer, t.suppliers, t.awards, t.value
        HAVING t.awards >= 3
        ORDER BY top_supplier_award_share DESC
    """)

    con.execute("DROP TABLE IF EXISTS gold.sentinel_method")
    con.execute(f"""
        CREATE TABLE gold.sentinel_method AS
        SELECT COALESCE(method, 'not stated') AS method,
               count(*) AS awards, round(sum(value)) AS value,
               round(100.0 * count(*) / (SELECT count(*) FROM silver.procurement_award), 1) AS share_pct
        FROM silver.procurement_award
        GROUP BY 1 ORDER BY awards DESC
    """)

    con.execute("DROP TABLE IF EXISTS gold.sentinel_repeat")
    con.execute("""
        CREATE TABLE gold.sentinel_repeat AS
        SELECT buyer, any_value(supplier) AS supplier,
               COALESCE(company_number, 'name:' || supplier_key) AS supplier_id,
               count(*) AS awards, round(sum(value)) AS total_value
        FROM silver.procurement_award
        WHERE buyer <> '' AND supplier_key <> ''
        GROUP BY buyer, supplier_id
        HAVING count(*) >= 3
        ORDER BY awards DESC, total_value DESC NULLS LAST
    """)


def _psc_ready(con) -> bool:
    return con.execute("SELECT count(*) FROM information_schema.tables "
                       "WHERE table_schema='silver' AND table_name='psc'").fetchone()[0] > 0


def shared_control(con: duckdb.DuckDBPyConnection) -> None:
    """Bidders on the same contract that share a controlling person.

    This is the collusion signal price and bidder-count screens cannot give,
    because UK data does not publish either. Two companies bidding for one award
    while a single person ultimately controls both is not proof of anything --
    incumbency and group structures are innocent -- but it is exactly the pattern
    a buyer should look at, and nobody surfaces it today.
    """
    con.execute("DROP TABLE IF EXISTS gold.sentinel_shared_control")
    if not _psc_ready(con):
        con.execute("""CREATE TABLE gold.sentinel_shared_control (
            ocid VARCHAR, buyer VARCHAR, person VARCHAR, controller_kind VARCHAR,
            company_a VARCHAR, supplier_a VARCHAR,
            company_b VARCHAR, supplier_b VARCHAR)""")
        return
    # A framework can award dozens of suppliers together; two of them sharing a
    # director there is coincidence, not collusion. Only genuinely competed
    # awards -- a small field of suppliers on one contract -- are considered, and
    # a corporate parent controlling its own subsidiary is excluded, because that
    # is an ordinary group structure rather than two independent bidders.
    con.execute(f"""
        CREATE TABLE gold.sentinel_shared_control AS
        WITH counts AS (
          SELECT ocid, count(DISTINCT company_number) AS n_suppliers
          FROM silver.procurement_award
          WHERE company_number IS NOT NULL AND ocid IS NOT NULL
          GROUP BY ocid
        ),
        bidders AS (
          SELECT DISTINCT a.ocid, a.buyer, a.company_number, a.supplier
          FROM silver.procurement_award a JOIN counts c USING (ocid)
          WHERE a.company_number IS NOT NULL
            AND c.n_suppliers BETWEEN 2 AND {MAX_COMPETED_FIELD}
        ),
        pairs AS (
          SELECT a.ocid, a.buyer,
                 a.company_number AS company_a, a.supplier AS supplier_a,
                 b.company_number AS company_b, b.supplier AS supplier_b
          FROM bidders a JOIN bidders b
            ON a.ocid = b.ocid AND a.company_number < b.company_number
        )
        SELECT DISTINCT p.ocid, p.buyer, pa.name AS person, pa.kind AS controller_kind,
               p.company_a, p.supplier_a, p.company_b, p.supplier_b
        FROM pairs p
        JOIN silver.psc pa ON pa.company_number = p.company_a
        JOIN silver.psc pb ON pb.company_number = p.company_b
        WHERE pa.person_key = pb.person_key AND pa.person_key <> ''
          -- exclude one company being the controlling entity of the other
          AND pa.kind = 'individual-person-with-significant-control'
          AND lower(pa.name) NOT IN (lower(p.supplier_a), lower(p.supplier_b))
    """)


def shared_control_stats(con: duckdb.DuckDBPyConnection) -> dict:
    """Why shared-control-on-one-contract finds little, stated as data.

    OCDS award notices name the winning supplier, not the losing bidders. So a
    contract almost always has one supplier, and two award-winners sharing an
    owner on the same notice is rare by construction -- not because collusion is
    absent, but because the data does not show who competed. This is the same
    wall that makes price and single-bidder screens impossible.
    """
    if not _psc_ready(con):
        return {"psc_loaded": False}
    total = con.execute("SELECT count(DISTINCT ocid) FROM silver.procurement_award "
                        "WHERE ocid IS NOT NULL").fetchone()[0]
    multi = con.execute("""SELECT count(*) FROM (
        SELECT ocid FROM silver.procurement_award
        WHERE company_number IS NOT NULL AND ocid IS NOT NULL
        GROUP BY ocid HAVING count(DISTINCT company_number) > 1)""").fetchone()[0]
    # The contracts the check actually examines: a small field of suppliers.
    competed = con.execute(f"""SELECT count(*) FROM (
        SELECT ocid FROM silver.procurement_award
        WHERE company_number IS NOT NULL AND ocid IS NOT NULL
        GROUP BY ocid
        HAVING count(DISTINCT company_number) BETWEEN 2 AND {MAX_COMPETED_FIELD})""").fetchone()[0]
    pairs = con.execute("SELECT count(*) FROM gold.sentinel_shared_control").fetchone()[0]
    return {"psc_loaded": True, "contracts": total,
            "multi_supplier_contracts": multi, "competed_contracts": competed,
            "competed_field_max": MAX_COMPETED_FIELD, "shared_control_pairs": pairs}


def control_footprint(con: duckdb.DuckDBPyConnection, limit: int = 10):
    """People who control several suppliers to the same buyer, across awards.

    This is the signal PSC actually powers. Shared control on a single contract
    is rare because award notices name only the winner; but one owner behind
    several of a buyer's suppliers over time needs no bidder list, and it is the
    concentration pattern an auditor should look at. Never a verdict -- one
    person legitimately owning two firms a council uses is common.
    """
    if not _psc_ready(con):
        return []
    return con.execute(f"""
        SELECT p.person_key, any_value(p.name) AS person, a.buyer,
               count(DISTINCT a.company_number) AS companies,
               count(DISTINCT a.ocid)           AS awards,
               round(sum(a.value))              AS total_value
        FROM silver.procurement_award a
        JOIN silver.psc p ON p.company_number = a.company_number
        WHERE a.company_number IS NOT NULL AND a.buyer <> '' AND p.person_key <> ''
        GROUP BY p.person_key, a.buyer
        HAVING count(DISTINCT a.company_number) > 1
        ORDER BY companies DESC, awards DESC LIMIT {limit}
    """).fetchall()


def build_footprint(con: duckdb.DuckDBPyConnection) -> None:
    con.execute("DROP TABLE IF EXISTS gold.sentinel_control_footprint")
    if not _psc_ready(con):
        con.execute("""CREATE TABLE gold.sentinel_control_footprint (
            person VARCHAR, buyer VARCHAR, companies INTEGER,
            awards INTEGER, total_value DOUBLE)""")
        return
    con.execute("""
        CREATE TABLE gold.sentinel_control_footprint AS
        SELECT any_value(p.name) AS person, a.buyer,
               count(DISTINCT a.company_number) AS companies,
               count(DISTINCT a.ocid)           AS awards,
               round(sum(a.value))              AS total_value
        FROM silver.procurement_award a
        JOIN silver.psc p ON p.company_number = a.company_number
        WHERE a.company_number IS NOT NULL AND a.buyer <> '' AND p.person_key <> ''
        GROUP BY p.person_key, a.buyer
        HAVING count(DISTINCT a.company_number) > 1
        ORDER BY companies DESC, awards DESC
    """)


def uncompeted_share(con: duckdb.DuckDBPyConnection) -> tuple[int, int, float]:
    row = con.execute(f"""
        SELECT count(*) FILTER (WHERE method IN {UNCOMPETED}), count(*)
        FROM silver.procurement_award""").fetchone()
    return row[0], row[1], round(100 * row[0] / row[1], 1) if row[1] else 0.0
