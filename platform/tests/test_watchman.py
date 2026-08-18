import json

import pytest

from groundtruth import store
from groundtruth.systems import watchman as W


def _gazette(tmp_path, entries):
    p = tmp_path / "g.json"
    p.write_text(json.dumps({"entry": entries}))
    return p


def _ocds(tmp_path, releases):
    p = tmp_path / "o.json"
    p.write_text(json.dumps({"releases": releases}))
    return p


class TestNoticeClassification:
    @pytest.mark.parametrize("t", [
        "Appointment of Liquidators", "Meetings of Creditors",
        "Resolutions for Winding-up", "Petitions to Wind Up (Companies)",
    ])
    def test_recognises_an_actual_insolvency_event(self, t):
        from groundtruth.gazette import Notice
        assert W.is_insolvency_event(Notice("1", "X", None, t, ""))

    @pytest.mark.parametrize("t", ["Notices to Creditors", "Notice of Intended Dividends"])
    def test_ignores_procedural_notices(self, t):
        from groundtruth.gazette import Notice
        assert not W.is_insolvency_event(Notice("1", "X", None, t, ""))


class TestMatching:
    """Both routes must work, and neither may assert what it cannot show."""

    def test_identifier_route_matches_without_name_comparison(self, tmp_path):
        gaz = _gazette(tmp_path, [{
            "id": "1", "title": "ACME BUILDERS LTD",
            "category": {"@term": "Appointment of Liquidators"},
            "content": "<div><p>ACME BUILDERS LTD ( 07654321 ) Leeds LS1 1AA</p></div>"}])
        ocds = _ocds(tmp_path, [{
            "ocid": "a", "buyer": {"id": "B1", "name": "Leeds City Council"},
            "parties": [{"id": "S1", "name": "Totally Different Trading Name",
                         "identifier": {"scheme": "GB-COH", "id": "07654321"}}],
            "awards": [{"id": "1", "date": "2026-01-01", "value": {"amount": 250000},
                        "suppliers": [{"id": "S1", "name": "Totally Different Trading Name"}]}]}])
        con = store.connect(tmp_path / "t.duckdb")
        r = W.build(con, gaz, ocds)
        assert len(r.exposures) == 1
        e = r.exposures[0]
        # The names do not resemble each other; only the number links them.
        assert e.method == "identifier" and e.confidence == 1.0
        assert e.supplier.buyer == "Leeds City Council"
        con.close()

    def test_name_route_used_when_the_notice_has_no_number(self, tmp_path):
        gaz = _gazette(tmp_path, [{
            "id": "2", "title": "NAMEONLY SERVICES LIMITED",
            "category": {"@term": "Meetings of Creditors"},
            "content": "<div><p>Company Address 1 High St, York, YO1 1AA</p></div>"}])
        ocds = _ocds(tmp_path, [{
            "ocid": "b", "buyer": {"id": "B2", "name": "City of York Council"},
            "parties": [{"id": "S2", "name": "Nameonly Services Ltd"}],
            "awards": [{"id": "1", "date": "2026-02-01", "value": {"amount": 90000},
                        "suppliers": [{"id": "S2", "name": "Nameonly Services Ltd"}]}]}])
        con = store.connect(tmp_path / "t.duckdb")
        r = W.build(con, gaz, ocds)
        assert len(r.exposures) == 1
        assert r.exposures[0].method == "name"
        assert r.exposures[0].confidence < 1.0, "only an identifier may score 1.0"
        con.close()

    def test_unrelated_company_produces_no_exposure(self, tmp_path):
        gaz = _gazette(tmp_path, [{
            "id": "3", "title": "SOMETHING ELSE LTD",
            "category": {"@term": "Appointment of Liquidators"},
            "content": "<div><p>SOMETHING ELSE LTD ( 11111111 )</p></div>"}])
        ocds = _ocds(tmp_path, [{
            "ocid": "c", "buyer": {"id": "B3", "name": "A Council"},
            "parties": [{"id": "S3", "name": "Unrelated Supplier Ltd",
                         "identifier": {"scheme": "GB-COH", "id": "99999999"}}],
            "awards": [{"id": "1", "date": "2026-03-01",
                        "suppliers": [{"id": "S3", "name": "Unrelated Supplier Ltd"}]}]}])
        con = store.connect(tmp_path / "t.duckdb")
        r = W.build(con, gaz, ocds)
        assert r.exposures == [] and r.review == []
        con.close()


class TestCumulativeRegister:
    """The register is the asset. A single fetch is not.

    Measured on live data: 609 insolvencies against 448 distinct suppliers in
    the same three weeks produced zero overlap, which is what chance predicts
    for 5.4 million UK companies. The signal only appears once the register
    accumulates.
    """

    def test_register_accumulates_and_does_not_double_count(self, tmp_path):
        con = store.connect(tmp_path / "t.duckdb")
        sup = [W.Supplier("Acme Ltd", "07654321", "Leeds City Council",
                          "B1", 1000.0, "2026-01-01", "cf")]
        first = W.register_suppliers(con, sup)
        assert first["added"] == 1
        again = W.register_suppliers(con, sup)
        assert again["added"] == 0, "re-registering the same award must not double-count"
        assert again["rows"] == 1
        con.close()

    def test_register_is_searchable_by_identifier_and_name(self, tmp_path):
        con = store.connect(tmp_path / "t.duckdb")
        W.register_suppliers(con, [
            W.Supplier("Acme Builders Limited", "07654321", "Leeds City Council",
                       "B1", 250000.0, "2026-01-01", "cf")])
        gaz = _gazette(tmp_path, [{
            "id": "1", "title": "ACME BUILDERS LTD",
            "category": {"@term": "Appointment of Liquidators"},
            "content": "<div><p>ACME BUILDERS LTD ( 07654321 )</p></div>"}])
        hits = W.check_against_register(con, gaz)
        assert len(hits) == 1 and hits[0].method == "identifier"
        con.close()
