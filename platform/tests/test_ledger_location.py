"""Ledger's location join.

The rule under test: the join runs on the publisher's own keys, and the
coverage it achieves is reported rather than implied. Fixing the join without
reporting how little it recovers would be a second overclaim.
"""
import json

import pytest

from groundtruth import store
from groundtruth.systems import ledger as L


AUTH = [{"entity": 111, "name": "Dover District Council"}]


def _setup(tmp_path, contribs, agreements, applications):
    con = store.connect(tmp_path / "db")
    c = tmp_path / "c.json"; c.write_text(json.dumps(contribs))
    t = tmp_path / "t.json"; t.write_text(json.dumps([]))
    a = tmp_path / "a.json"; a.write_text(json.dumps(AUTH))
    L.load(con, c, t, a)
    g = tmp_path / "g.json"; g.write_text(json.dumps(agreements))
    p = tmp_path / "p.json"; p.write_text(json.dumps(applications))
    L.load_agreements(con, g)
    L.load_applications(con, p)
    return con


class TestPointParsing:
    @pytest.mark.parametrize("raw,expect", [
        ("POINT (-0.380513 50.810042)", (-0.380513, 50.810042)),
        ("POINT(-0.38 50.81)", (-0.38, 50.81)),
        ("", (None, None)), ("   ", (None, None)), (None, (None, None)),
        ("MULTIPOLYGON (((0 0)))", (None, None)),
    ])
    def test_reads_the_publishers_format_and_refuses_the_rest(self, raw, expect):
        assert L._point(raw) == expect


class TestLocation:
    def test_join_closes_only_where_the_authority_published_applications(self, tmp_path):
        con = _setup(tmp_path,
            contribs=[
                {"entity": 1, "reference": "A-da-con-1", "organisation-entity": 111,
                 "developer-agreement": "A-da", "amount": "100"},
                {"entity": 2, "reference": "B-da-con-1", "organisation-entity": 111,
                 "developer-agreement": "B-da", "amount": "900"},
            ],
            agreements=[
                {"entity": 10, "reference": "A-da", "organisation-entity": 111,
                 "planning-application": "APP-1"},
                {"entity": 11, "reference": "B-da", "organisation-entity": 111,
                 "planning-application": "APP-2"},
            ],
            # only APP-1 is published, and only it carries a point
            applications=[{"entity": 20, "reference": "APP-1",
                           "organisation-entity": 111,
                           "point": "POINT (1.3 51.1)"}])
        out = L.locate(con)
        assert out["available"] is True
        assert out["located"] == 1 and out["contributions"] == 2
        assert out["located_pct"] == 50.0
        assert out["amount_located"] == 100, "value follows the record, not the count"
        con.close()

    def test_reports_unavailable_rather_than_zero_when_not_loaded(self, tmp_path):
        """Zero located and 'cannot be computed' are different answers, and the
        difference is the whole reason this system exists."""
        con = store.connect(tmp_path / "db")
        con.execute("CREATE SCHEMA IF NOT EXISTS silver")
        out = L.locate(con)
        assert out["available"] is False and "not loaded" in out["reason"]
        con.close()

    def test_gap_names_the_authorities_that_break_the_chain(self, tmp_path):
        con = _setup(tmp_path,
            contribs=[{"entity": 1, "reference": "B-da-con-1",
                       "organisation-entity": 111, "developer-agreement": "B-da",
                       "amount": "900"}],
            agreements=[{"entity": 11, "reference": "B-da",
                         "organisation-entity": 111, "planning-application": "APP-2"}],
            applications=[])
        L.locate(con)
        gap = L.location_gap(con)
        assert gap and gap[0]["authority"] == "Dover District Council"
        assert gap[0]["amount"] == 900 and gap[0]["located"] == 0
        con.close()

    def test_join_does_not_cross_authorities(self, tmp_path):
        """Application references repeat across councils. Joining on reference
        alone would attach one council's money to another's site."""
        con = _setup(tmp_path,
            contribs=[{"entity": 1, "reference": "A-da-con-1",
                       "organisation-entity": 111, "developer-agreement": "A-da",
                       "amount": "100"}],
            agreements=[{"entity": 10, "reference": "A-da",
                         "organisation-entity": 111, "planning-application": "23/001"}],
            applications=[{"entity": 20, "reference": "23/001",
                           "organisation-entity": 999,
                           "point": "POINT (1.3 51.1)"}])
        out = L.locate(con)
        assert out["located"] == 0
        con.close()
