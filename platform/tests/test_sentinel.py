import json

import pytest

from groundtruth import store
from groundtruth.systems import sentinel as S


def _ocds(tmp_path, releases, name="o.json"):
    p = tmp_path / name
    p.write_text(json.dumps({"releases": releases}))
    return p


def _release(ocid, buyer, supplier, value=1000, method="open", number=None):
    parties = [{"id": "S1", "name": supplier}]
    if number:
        parties[0]["identifier"] = {"scheme": "GB-COH", "id": number}
    return {"ocid": ocid, "buyer": {"id": "B1", "name": buyer},
            "tender": {"procurementMethod": method}, "parties": parties,
            "awards": [{"id": "1", "date": "2026-01-01", "value": {"amount": value},
                        "suppliers": [{"id": "S1", "name": supplier}]}]}


class TestWhatCannotBeComputed:
    """Two standard screens are impossible in UK data. The system must report
    that rather than implying it ran them."""

    def test_bidder_counts_are_absent(self, tmp_path):
        p = _ocds(tmp_path, [_release("a", "Council", "Acme Ltd")])
        con = store.connect(tmp_path / "db")
        cov = S.load(con, p)
        assert cov.with_tenderer_count == 0
        con.close()

    def test_supplier_identification_is_partial_and_measured(self, tmp_path):
        p = _ocds(tmp_path, [
            _release("a", "Council", "Acme Ltd", number="07654321"),
            _release("b", "Council", "Beta Ltd"),
        ])
        con = store.connect(tmp_path / "db")
        cov = S.load(con, p)
        assert cov.awards == 2 and cov.suppliers_identified == 1
        con.close()


class TestConcentration:
    def test_repeated_awards_to_one_supplier_are_surfaced(self, tmp_path):
        p = _ocds(tmp_path, [
            _release("a", "Council", "Acme Ltd", number="07654321"),
            _release("b", "Council", "Acme Ltd", number="07654321"),
            _release("c", "Council", "Acme Ltd", number="07654321"),
            _release("d", "Council", "Other Ltd", number="09999999"),
        ])
        con = store.connect(tmp_path / "db")
        S.load(con, p); S.build(con)
        row = con.execute("""SELECT top_supplier_award_share FROM gold.sentinel_buyer
                             WHERE buyer='Council'""").fetchone()
        assert row[0] == pytest.approx(75.0)
        rep = con.execute("SELECT awards FROM gold.sentinel_repeat").fetchall()
        assert rep and rep[0][0] == 3
        con.close()

    def test_one_company_under_two_names_is_counted_once(self, tmp_path):
        """The entity spine is what makes concentration measurable at all."""
        p = _ocds(tmp_path, [
            _release("a", "Council", "Acme Limited", number="07654321"),
            _release("b", "Council", "ACME LTD", number="07654321"),
            _release("c", "Council", "Other Ltd", number="09999999"),
        ])
        con = store.connect(tmp_path / "db")
        S.load(con, p); S.build(con)
        suppliers = con.execute("""SELECT suppliers FROM gold.sentinel_buyer
                                   WHERE buyer='Council'""").fetchone()[0]
        assert suppliers == 2, "two spellings of one company number are one supplier"
        con.close()

    def test_uncompeted_share_counts_direct_and_limited(self, tmp_path):
        p = _ocds(tmp_path, [
            _release("a", "Council", "A Ltd", method="direct"),
            _release("b", "Council", "B Ltd", method="limited"),
            _release("c", "Council", "C Ltd", method="open"),
            _release("d", "Council", "D Ltd", method="selective"),
        ])
        con = store.connect(tmp_path / "db")
        S.load(con, p); S.build(con)
        n, total, pct = S.uncompeted_share(con)
        assert n == 2 and total == 4 and pct == 50.0
        con.close()
