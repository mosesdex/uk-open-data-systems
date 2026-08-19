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


@dataclass(frozen=True)
class Coverage:
    releases: int
    awards: int
    with_value: int
    with_method: int
    with_tenderer_count: int
    suppliers_identified: int

    def pct(self, n: int, of: int | None = None) -> float:
        d = of or self.releases
        return 100 * n / d if d else 0.0


def load(con: duckdb.DuckDBPyConnection, *paths: Path) -> Coverage:
    rows = []
    releases = awards = with_value = with_method = with_tenderers = identified = 0

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
    return Coverage(releases, awards, with_value, with_method, with_tenderers, identified)


def build(con: duckdb.DuckDBPyConnection) -> None:
    """Concentration measures. Signals to investigate, not verdicts."""
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


def uncompeted_share(con: duckdb.DuckDBPyConnection) -> tuple[int, int, float]:
    row = con.execute(f"""
        SELECT count(*) FILTER (WHERE method IN {UNCOMPETED}), count(*)
        FROM silver.procurement_award""").fetchone()
    return row[0], row[1], round(100 * row[0] / row[1], 1) if row[1] else 0.0
