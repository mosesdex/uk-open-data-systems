import json

import pytest

from groundtruth import store
from groundtruth.systems import ledger as L


def _files(tmp_path, contribs, txns, auths):
    a = tmp_path / "c.json"; a.write_text(json.dumps(contribs))
    b = tmp_path / "t.json"; b.write_text(json.dumps(txns))
    c = tmp_path / "a.json"; c.write_text(json.dumps(auths))
    return a, b, c


AUTH = [{"entity": 111, "name": "Dover District Council"}]


class TestCoverage:
    def test_amount_coverage_is_measured_not_assumed(self, tmp_path):
        """The national total covers 70.4% of records. Reporting it as if it
        covered all of them would overstate what is known."""
        c, t, a = _files(tmp_path, [
            {"entity": 1, "organisation-entity": 111, "amount": "1000"},
            {"entity": 2, "organisation-entity": 111, "amount": ""},
            {"entity": 3, "organisation-entity": 111},
        ], [], AUTH)
        con = store.connect(tmp_path / "db")
        cov = L.load(con, c, t, a)
        assert cov.contributions == 3 and cov.with_amount == 1
        total, with_amount, all_rows = L.national_total(con)
        assert total == 1000 and with_amount == 1 and all_rows == 3
        con.close()

    def test_empty_geometry_and_point_count_as_no_location(self, tmp_path):
        # Both fields are present on every record and empty on every record.
        c, t, a = _files(tmp_path, [
            {"entity": 1, "organisation-entity": 111, "geometry": "", "point": ""},
            {"entity": 2, "organisation-entity": 111, "geometry": "  ", "point": ""},
            {"entity": 3, "organisation-entity": 111, "point": "POINT(1 2)"},
        ], [], AUTH)
        con = store.connect(tmp_path / "db")
        cov = L.load(con, c, t, a)
        assert cov.with_geometry == 1, "only a genuine point counts as located"
        con.close()


class TestPromisedVersusDelivered:
    def test_funding_status_separates_agreed_from_spent(self, tmp_path):
        c, t, a = _files(tmp_path,
            [{"entity": 1, "organisation-entity": 111, "amount": "1000"}],
            [{"entity": 10, "organisation-entity": 111, "amount": "600",
              "contribution-funding-status": "received"},
             {"entity": 11, "organisation-entity": 111, "amount": "400",
              "contribution-funding-status": "spent"}], AUTH)
        con = store.connect(tmp_path / "db")
        L.load(con, c, t, a); L.build(con)
        rows = {r[0]: r[3] for r in con.execute(
            "SELECT * FROM gold.ledger_funding_status").fetchall()}
        assert rows["received"] == 600 and rows["spent"] == 400
        con.close()

    def test_authority_names_are_resolved(self, tmp_path):
        c, t, a = _files(tmp_path,
            [{"entity": 1, "organisation-entity": 111, "amount": "500"}], [], AUTH)
        con = store.connect(tmp_path / "db")
        L.load(con, c, t, a); L.build(con)
        name = con.execute("SELECT authority FROM gold.ledger_authority").fetchone()[0]
        assert name == "Dover District Council"
        con.close()

    def test_unknown_organisation_is_labelled_not_dropped(self, tmp_path):
        c, t, a = _files(tmp_path,
            [{"entity": 1, "organisation-entity": 999, "amount": "500"}], [], AUTH)
        con = store.connect(tmp_path / "db")
        L.load(con, c, t, a); L.build(con)
        name = con.execute("SELECT authority FROM gold.ledger_authority").fetchone()[0]
        assert "999" in name, "an unmatched authority must stay visible"
        con.close()
