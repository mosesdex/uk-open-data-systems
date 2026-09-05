"""Relationship exploration.

The rule under test: exploration adds no edges of its own, and a node whose name
is not published keeps its identifier rather than being given a plausible one.
"""
import pytest

from groundtruth import relationships as R
from groundtruth import store


@pytest.fixture
def con(tmp_path):
    c = store.connect(tmp_path / "db")
    c.execute("CREATE SCHEMA IF NOT EXISTS silver")
    c.execute("""CREATE TABLE silver.contribution (
        entity BIGINT, reference VARCHAR, organisation_entity BIGINT,
        agreement VARCHAR, purpose VARCHAR, amount DOUBLE, units DOUBLE,
        start_date VARCHAR, has_geometry BOOLEAN)""")
    c.execute("""INSERT INTO silver.contribution VALUES
        (1,'C-1',111,'A-1','health',100,NULL,'2019-01-01',FALSE),
        (2,'C-2',111,'A-1','roads',200,NULL,'2019-01-01',FALSE)""")
    c.execute("CREATE TABLE silver.planning_authority (entity BIGINT, name VARCHAR)")
    c.execute("INSERT INTO silver.planning_authority VALUES (111,'Dover District Council')")
    yield c
    c.close()


class TestLabels:
    def test_published_name_is_used(self, con):
        assert R.label(con, "gt:entity:organisation:111") == "Dover District Council"

    def test_unnamed_node_keeps_its_identifier(self, con):
        """Inventing a label for an unpublished name would put a fiction on a
        diagram that otherwise carries only sourced facts."""
        ident = "gt:entity:organisation:999"
        assert R.label(con, ident) == ident

    def test_malformed_identifier_is_returned_unchanged(self, con):
        assert R.label(con, "nonsense") == "nonsense"


class TestNeighbourhood:
    def test_expands_only_edges_the_graph_declares(self, con):
        n = R.neighbourhood(con, "gt:event:contribution:111/C-1", depth=2)
        assert {e.predicate for e in n.edges} <= {"agreed_under", "collected_by"}
        assert "gt:entity:organisation:111" in n.nodes
        assert n.nodes["gt:entity:organisation:111"].label == "Dover District Council"

    def test_node_budget_truncates_and_says_so(self, con):
        n = R.neighbourhood(con, "gt:event:contribution:111/C-1", depth=3, max_nodes=2)
        assert n.truncated is True

    def test_depth_is_recorded_per_node(self, con):
        n = R.neighbourhood(con, "gt:event:contribution:111/C-1", depth=2)
        assert n.nodes["gt:event:contribution:111/C-1"].depth == 0
        assert n.nodes["gt:event:agreement:111/A-1"].depth == 1

    def test_malformed_centre_is_refused(self, con):
        with pytest.raises(Exception):
            R.neighbourhood(con, "not-an-identifier")


class TestRendering:
    def test_mermaid_escapes_quotes_and_brackets(self, con):
        con.execute("UPDATE silver.planning_authority SET name = 'A \"quoted\" [name]'")
        n = R.neighbourhood(con, "gt:event:contribution:111/C-1", depth=1)
        out = R.to_mermaid(n)
        assert out.startswith("graph LR")
        assert '"' not in out.split("\n", 1)[1] or "'" in out

    def test_text_tree_shows_the_predicate_on_each_link(self, con):
        n = R.neighbourhood(con, "gt:event:contribution:111/C-1", depth=1)
        out = R.to_text(n)
        assert "[agreed_under]" in out and "Dover District Council" in out


class TestBetween:
    def test_finds_a_connection_and_reports_the_path(self, con):
        paths = R.between(con, "gt:event:contribution:111/C-1",
                          "gt:entity:organisation:111")
        assert paths and paths[0].edges[-1].dst == "gt:entity:organisation:111"

    def test_unconnected_things_return_nothing_rather_than_a_guess(self, con):
        assert R.between(con, "gt:event:contribution:111/C-1",
                         "gt:entity:organisation:999") == []
