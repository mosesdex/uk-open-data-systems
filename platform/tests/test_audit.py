"""The integrity audit.

The rule under test: a check that could not run is reported as skipped rather
than as a pass, and a failing check is itself a finding. An audit that finds
nothing must be distinguishable from an audit that did not look.
"""
import pytest

from groundtruth import audit as A
from groundtruth import store


@pytest.fixture
def con(tmp_path):
    c = store.connect(tmp_path / "db")
    for s in ("silver", "gold"):
        c.execute(f"CREATE SCHEMA IF NOT EXISTS {s}")
    yield c
    c.close()


class TestReporting:
    def test_skipped_check_is_not_a_pass(self, con):
        a = A.Audit()
        a.skip("x", "table absent")
        assert a.summary()["checks_skipped"] == 1
        assert a.summary()["findings"] == 0

    def test_a_check_that_raises_becomes_a_finding(self, con, monkeypatch):
        def explode(c, a):
            raise RuntimeError("boom")
        monkeypatch.setattr(A, "CHECKS", (explode,))
        out = A.run(con)
        assert out.summary()["major"] == 1
        assert "boom" in out.findings[0].summary

    def test_findings_sort_most_severe_first(self):
        a = A.Audit()
        a.add("c", A.NOTE, "s", "note")
        a.add("c", A.CRITICAL, "s", "critical")
        a.add("c", A.MAJOR, "s", "major")
        assert [f.severity for f in a.sorted()] == [A.CRITICAL, A.MAJOR, A.NOTE]

    def test_network_checks_are_off_by_default(self, con, monkeypatch):
        called = []
        monkeypatch.setattr(A, "CHECKS", ())
        monkeypatch.setattr(A, "NETWORK_CHECKS", (lambda c, a: called.append(1),))
        A.run(con)
        assert called == []
        A.run(con, network=True)
        assert called == [1]


class TestChecks:
    def test_duplicate_keys_are_found(self, con):
        con.execute("CREATE TABLE gold.entity (company_number VARCHAR)")
        con.execute("INSERT INTO gold.entity VALUES ('1'),('1'),('2')")
        a = A.Audit()
        A.check_duplicates(con, a)
        assert any("duplicated keys" in f.summary for f in a.findings)

    def test_null_join_keys_report_the_unjoinable_share(self, con):
        con.execute("CREATE TABLE gold.catchment_school (urn VARCHAR, lad_code VARCHAR)")
        con.execute("INSERT INTO gold.catchment_school VALUES ('1',NULL),('2','E1')")
        a = A.Audit()
        A.check_null_keys(con, a)
        f = next(f for f in a.findings if "lad_code" in f.subject)
        assert "50.0%" in f.summary

    def test_empty_table_is_reported_rather_than_ignored(self, con):
        con.execute("CREATE TABLE gold.thing (x INTEGER)")
        a = A.Audit()
        A.check_orphan_tables(con, a)
        assert any(f.subject == "gold.thing" for f in a.findings)

    def test_an_index_page_declared_as_html_is_not_a_content_trap(self, con):
        """The registry declares some sources as HTML index pages that must be
        parsed. Flagging those was this check's own first false positive."""
        from groundtruth import sources as S
        html_sources = [s for s in S.REGISTRY
                        if any("html" in c.lower() for c in s.expect_content)]
        assert html_sources, "fixture assumes at least one declared-HTML source"
        con.execute("""INSERT INTO bronze.fetch_log VALUES
            ('r1', ?, now(), 200, TRUE, 'abc', 7442, 'text/html', 10, 'p', 'ok', NULL)""",
            [html_sources[0].id])
        a = A.Audit()
        A.check_content_traps(con, a)
        assert not [f for f in a.findings if f.subject == html_sources[0].id]

    def test_source_authority_accepts_a_publishers_own_delivery_host(self):
        a = A.Audit()
        assert "services1.arcgis.com" in A.DELEGATED_HOSTS
        assert "www.planit.org.uk" not in A.DELEGATED_HOSTS
