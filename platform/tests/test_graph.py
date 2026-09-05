"""The evidence graph.

The rule under test: an edge whose table is absent is reported as unavailable,
never as zero. A graph that silently drops the edges it cannot serve answers
fewer questions while looking complete.
"""
import pytest

from groundtruth import graph as G
from groundtruth import ids, store


@pytest.fixture
def con(tmp_path):
    c = store.connect(tmp_path / "db")
    c.execute("CREATE SCHEMA IF NOT EXISTS silver")
    yield c
    c.close()


def _contributions(con):
    con.execute("""CREATE TABLE silver.contribution (
        entity BIGINT, reference VARCHAR, organisation_entity BIGINT,
        agreement VARCHAR, purpose VARCHAR, amount DOUBLE, units DOUBLE,
        start_date VARCHAR, has_geometry BOOLEAN)""")
    con.execute("""INSERT INTO silver.contribution VALUES
        (1,'DOV-1-da-con-1',111,'DOV-1-da','health',100,NULL,'2019-04-30',FALSE),
        (2,'DOV-1-da-con-2',111,'DOV-1-da','health',200,NULL,'2019-04-30',FALSE)""")


class TestAvailability:
    def test_missing_table_is_unavailable_not_empty(self, con):
        rows = {r["predicate"]: r for r in G.available(con)}
        assert rows["agreed_under"]["available"] is False
        assert rows["agreed_under"]["edges"] is None, \
            "an absent table has no edge count; zero would be a lie"

    def test_present_table_reports_its_edge_count(self, con):
        _contributions(con)
        rows = {r["predicate"]: r for r in G.available(con)}
        assert rows["agreed_under"]["available"] is True
        assert rows["agreed_under"]["edges"] == 2

    def test_stats_names_what_cannot_be_walked(self, con):
        _contributions(con)
        s = G.stats(con)
        assert "located_in" in s["unavailable"]
        assert s["by_predicate"]["agreed_under"] == 2


class TestTraversal:
    def test_one_hop_follows_the_publishers_own_key(self, con):
        # Keys are authority-qualified: a planning reference is unique per
        # council, so an unqualified edge would join across councils.
        _contributions(con)
        edges = G.neighbours(con, "gt:event:contribution:111/DOV-1-da-con-1")
        by_pred = {e.predicate: e for e in edges}
        assert by_pred["agreed_under"].dst == "gt:event:agreement:111/DOV-1-da"
        assert by_pred["collected_by"].dst == "gt:entity:organisation:111"
        assert by_pred["agreed_under"].confidence == 1.0

    def test_walk_reaches_a_target_kind(self, con):
        _contributions(con)
        paths = G.walk(con, "gt:event:contribution:111/DOV-1-da-con-1",
                       target_kind="entity")
        assert paths and paths[0].end == "gt:entity:organisation:111"

    def test_path_confidence_multiplies_rather_than_taking_the_minimum(self):
        # Three ninety-percent joins are not a ninety-percent answer.
        p = G.Path("gt:event:contribution:x", [
            G.Edge("a", "p", "b", 0.9, "t"),
            G.Edge("b", "p", "c", 0.9, "t"),
            G.Edge("c", "p", "d", 0.9, "t")])
        assert p.confidence == pytest.approx(0.729)

    def test_malformed_start_is_refused(self, con):
        with pytest.raises(ids.IdentifierError):
            G.walk(con, "not-an-identifier")

    def test_traversal_does_not_revisit_a_node(self, con):
        """A cycle in the data must not become an unbounded walk."""
        _contributions(con)
        # a contribution whose agreement points back at the contribution
        con.execute("""INSERT INTO silver.contribution VALUES
            (3,'DOV-1-da',111,'DOV-1-da-con-1',NULL,NULL,NULL,NULL,FALSE)""")
        paths = G.walk(con, "gt:event:contribution:111/DOV-1-da-con-1", max_depth=6)
        ends = [p.end for p in paths]
        assert len(ends) == len(set(ends))
