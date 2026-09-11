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


class TestTheAuditChecksTheCorpusItHas:
    """Two of the audit's major findings were the audit's own mistakes: a table
    map that listed one of Watchman's two tables, and a host allowlist that did
    not know NESO publishes on its own domain. Both came from adding things
    without updating what enumerates them, so these fail when that happens."""

    def test_every_gold_table_a_system_builds_is_mapped(self):
        import pathlib, re
        from groundtruth import admin
        root = pathlib.Path(__file__).resolve().parent.parent / "groundtruth" / "systems"
        src = "\n".join(p.read_text() for p in root.glob("*.py"))
        made = set(re.findall(r"(?:CREATE(?: OR REPLACE)? TABLE|TABLE IF EXISTS)\s+gold\.(\w+)", src))
        for sid, tabs in admin.SYSTEM_TABLES.items():
            for t in sorted(made):
                if t.startswith(sid + "_"):
                    assert f"gold.{t}" in tabs, f"gold.{t} is built by {sid} but not mapped"

    def test_only_the_known_aggregator_fails_source_authority(self):
        import urllib.parse
        from groundtruth import audit, sources as S
        host = lambda s: urllib.parse.urlparse(s.url).netloc.lower()
        failing = {s.id for s in S.REGISTRY if not s.blocked
                   and host(s) not in audit.DELEGATED_HOSTS
                   and not any(host(s).endswith(x) for x in audit.GOV_SUFFIXES)}
        # PlanIt is a volunteer-run aggregator. Anything else on an unclassified
        # host fails here until someone decides which it is.
        assert failing == {"planit_planning_wq"}

    def test_planning_references_are_unique_per_authority_not_nationally(self):
        import duckdb
        from groundtruth import audit
        con = duckdb.connect(":memory:"); con.execute("CREATE SCHEMA silver")
        con.execute("CREATE TABLE silver.contribution(organisation_entity INTEGER, reference VARCHAR)")
        con.execute("INSERT INTO silver.contribution VALUES (1, '21/0001'), (2, '21/0001')")
        a = audit.Audit(); audit.check_duplicates(con, a)
        assert not [f for f in a.findings if "contribution" in f.subject]
        con.execute("INSERT INTO silver.contribution VALUES (1, '21/0001')")
        a = audit.Audit(); audit.check_duplicates(con, a)
        assert [f for f in a.findings if "contribution" in f.subject]

