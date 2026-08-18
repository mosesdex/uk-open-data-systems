"""Watchman -- insolvency exposure across public suppliers.

When a supplier fails on a Friday afternoon, the question is which departments,
councils and services depend on it. Today that takes weeks. The answer is
already public: insolvency notices and procurement award notices are both open
feeds. Nothing here predicts a failure -- it reports one that has happened, and
enumerates the exposure.

The supplier register must be **cumulative**, not a rolling window. Measured on
three weeks of live data: 609 companies entered insolvency while 448 distinct
companies appeared as public suppliers. The overlap was zero -- and that is
what chance predicts. With roughly 5.4 million UK companies, 609 insolvencies
against a 448-company register gives an expected overlap of about 0.05.

The signal only appears once the register holds every supplier ever awarded a
public contract, accumulated across runs, rather than whoever happened to be
awarded one this month. `register_suppliers` therefore appends and deduplicates
into a persistent table instead of rebuilding from the latest fetch.

Two further measured facts shape the design:

  * Insolvency notices carry a company number 70% of the time, reliably for the
    notice types that mark an actual insolvency event.
  * Supplier records carry a Companies House identifier 34-55% of the time
    depending on the feed.

So identifier matching alone will not close the loop. Name matching is required,
which is why every link is scored and anything uncertain is queued rather than
asserted.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import duckdb

from ..store import insert_many

from .. import entity
from ..gazette import Notice, parse as parse_notices

# Notice types that mark a company actually entering an insolvency process,
# as opposed to procedural or creditor-facing notices.
INSOLVENCY_EVENTS = (
    "appointment of liquidators", "meetings of creditors",
    "resolutions for winding-up", "resolutions for winding up",
    "appointment of administrators", "petitions to wind up",
)


@dataclass(frozen=True)
class Supplier:
    name: str
    company_number: str | None
    buyer: str
    buyer_id: str
    value: float | None
    award_date: str
    source: str


@dataclass(frozen=True)
class Exposure:
    notice: Notice
    supplier: Supplier
    method: str
    confidence: float
    note: str


@dataclass
class Report:
    notices: int
    events: int
    suppliers: int
    suppliers_identified: int
    exposures: list[Exposure] = field(default_factory=list)
    review: list[Exposure] = field(default_factory=list)

    @property
    def supplier_identified_pct(self) -> float:
        return 100 * self.suppliers_identified / self.suppliers if self.suppliers else 0.0


def _num(v) -> float | None:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def load_suppliers(*paths: Path) -> list[Supplier]:
    """Extract awarded suppliers from OCDS release packages."""
    out: list[Supplier] = []
    for path in paths:
        if not Path(path).exists():
            continue
        doc = json.loads(Path(path).read_text())
        for rel in doc.get("releases", []):
            buyer = rel.get("buyer") or {}
            # Companies House ids live on the party record, not the award.
            party_num = {}
            for p in rel.get("parties", []) or []:
                ident = p.get("identifier") or {}
                if ident.get("scheme") == "GB-COH" and ident.get("id"):
                    party_num[p.get("id")] = str(ident["id"])
            for award in rel.get("awards", []) or []:
                value = (award.get("value") or {}).get("amount")
                for sup in award.get("suppliers", []) or []:
                    out.append(Supplier(
                        name=(sup.get("name") or "").strip(),
                        company_number=entity.normalise_company_number(
                            party_num.get(sup.get("id"))),
                        buyer=(buyer.get("name") or "").strip(),
                        buyer_id=str(buyer.get("id") or ""),
                        value=_num(value),
                        award_date=str(award.get("date") or ""),
                        source=Path(path).stem,
                    ))
    return out


def is_insolvency_event(notice: Notice) -> bool:
    return any(k in (notice.notice_type or "").lower() for k in INSOLVENCY_EVENTS)


def build(con: duckdb.DuckDBPyConnection, gazette_path: Path,
          *ocds_paths: Path) -> Report:
    notices = parse_notices(gazette_path)
    events = [n for n in notices if is_insolvency_event(n)]
    suppliers = load_suppliers(*ocds_paths)
    identified = sum(1 for s in suppliers if s.company_number)

    by_number: dict[str, list[Supplier]] = {}
    for s in suppliers:
        if s.company_number:
            by_number.setdefault(s.company_number, []).append(s)
    name_index = entity.build_index(
        [(s.company_number or "00000000", s.name) for s in suppliers if s.name])
    by_name_key: dict[str, list[Supplier]] = {}
    for s in suppliers:
        key = entity.normalise_name(s.name)
        if key:
            by_name_key.setdefault(key, []).append(s)

    report = Report(len(notices), len(events), len(suppliers), identified)

    for n in events:
        # Route one: the notice carries a number and a supplier record does too.
        num = entity.normalise_company_number(n.company_number)
        if num and num in by_number:
            for s in by_number[num]:
                report.exposures.append(Exposure(
                    n, s, "identifier", 1.0,
                    "company number on both records -- no matching required"))
            continue
        # Route two: match on name, scored, never silently accepted.
        key = entity.normalise_name(n.title)
        if not key:
            continue
        hit = by_name_key.get(key)
        if hit:
            conf = 0.97 if len(hit) == 1 else 0.0
            for s in hit:
                exp = Exposure(n, s, "name", conf,
                               f"exact match on normalised name {key!r}"
                               if conf else f"{len(hit)} suppliers share this name -- ambiguous")
                (report.exposures if conf >= entity.ACCEPT else report.review).append(exp)
    return report


def register_suppliers(con: duckdb.DuckDBPyConnection, suppliers: list[Supplier]) -> dict:
    """Accumulate suppliers into a persistent register.

    Each run adds whatever the feeds published since last time. The register is
    the asset; a single fetch is not.
    """
    con.execute("""
        CREATE TABLE IF NOT EXISTS silver.supplier_register (
          name_key       VARCHAR,
          company_number VARCHAR,
          name           VARCHAR,
          buyer          VARCHAR,
          value          DOUBLE,
          award_date     VARCHAR,
          source         VARCHAR,
          PRIMARY KEY (name_key, buyer, award_date)
        )""")
    before = con.execute("SELECT count(*) FROM silver.supplier_register").fetchone()[0]
    rows = []
    for s in suppliers:
        key = entity.normalise_name(s.name)
        if not key:
            continue
        rows.append((key, s.company_number, s.name, s.buyer, s.value,
                     s.award_date, s.source))
    if rows:
        insert_many(con, 
            "INSERT OR IGNORE INTO silver.supplier_register VALUES (?,?,?,?,?,?,?)", rows)
    after = con.execute("SELECT count(*) FROM silver.supplier_register").fetchone()[0]
    distinct = con.execute(
        "SELECT count(DISTINCT name_key), count(DISTINCT company_number) "
        "FROM silver.supplier_register").fetchone()
    return {"added": after - before, "rows": after,
            "distinct_names": distinct[0], "distinct_numbers": distinct[1] or 0}


def check_against_register(con: duckdb.DuckDBPyConnection, gazette_path: Path) -> list[Exposure]:
    """Check new insolvency notices against everything ever registered."""
    notices = [n for n in parse_notices(gazette_path) if is_insolvency_event(n)]
    out: list[Exposure] = []
    for n in notices:
        num = entity.normalise_company_number(n.company_number)
        rows = []
        method, conf, note = "", 0.0, ""
        if num:
            rows = con.execute(
                "SELECT name, buyer, value, award_date, source, company_number "
                "FROM silver.supplier_register WHERE company_number = ?", [num]).fetchall()
            method, conf, note = "identifier", 1.0, "company number on both records"
        if not rows:
            key = entity.normalise_name(n.title)
            if key:
                rows = con.execute(
                    "SELECT name, buyer, value, award_date, source, company_number "
                    "FROM silver.supplier_register WHERE name_key = ?", [key]).fetchall()
                method, conf, note = "name", 0.97, f"exact match on normalised name {key!r}"
        for nm, buyer, value, date, src, cnum in rows:
            out.append(Exposure(
                n, Supplier(nm, cnum, buyer, "", value, date, src), method, conf, note))
    return out


def write(con: duckdb.DuckDBPyConnection, report: Report) -> None:
    con.execute("DROP TABLE IF EXISTS gold.watchman_exposure")
    con.execute("""
        CREATE TABLE gold.watchman_exposure (
          company VARCHAR, company_number VARCHAR, notice_type VARCHAR,
          published VARCHAR, buyer VARCHAR, contract_value DOUBLE,
          award_date VARCHAR, method VARCHAR, confidence DOUBLE, note VARCHAR
        )""")
    rows = [(e.notice.title, e.supplier.company_number or e.notice.company_number,
             e.notice.notice_type, e.notice.published, e.supplier.buyer,
             e.supplier.value, e.supplier.award_date, e.method, e.confidence, e.note)
            for e in report.exposures + report.review]
    if rows:
        insert_many(con, 
            "INSERT INTO gold.watchman_exposure VALUES (?,?,?,?,?,?,?,?,?,?)", rows)
