"""Evidence gaps.

The rule under test: a broken chain says why it broke, and 'we have not built
this' is never confused with 'nobody publishes this'.
"""
import pytest

from groundtruth import gaps as GA
from groundtruth import store


@pytest.fixture
def con(tmp_path):
    c = store.connect(tmp_path / "db")
    for s in ("silver", "gold"):
        c.execute(f"CREATE SCHEMA IF NOT EXISTS {s}")
    yield c
    c.close()


class TestCauses:
    def test_every_declared_absence_names_a_cause_and_a_reason(self):
        """An unexplained gap is a to-do note, not a finding."""
        for chain in GA.CHAINS:
            for step in chain.steps:
                if not step.measurable:
                    assert step.absent_because in (GA.PLATFORM, GA.PUBLISHER, GA.NOWHERE)
                    assert step.reason, f"{chain.name}/{step.name} gives no reason"

    def test_missing_table_is_unmeasured_not_broken(self, con):
        out = GA.measure(con, GA.CHAINS[0])
        first = out["detail"][0]
        assert first["available"] is False
        assert first["absent_because"] == GA.UNMEASURED
        assert first["table_exists"] is False

    def test_structural_and_fixable_gaps_are_reported_apart(self, con):
        r = GA.report(con)
        assert r["not_published_anywhere"], "the national gaps are the finding"
        assert all(g["reason"] for g in r["not_published_anywhere"])
        assert set(r["by_cause"]) <= {GA.PLATFORM, GA.PUBLISHER, GA.NOWHERE, GA.UNMEASURED}


class TestMeasurement:
    def _chain(self, con, populated):
        con.execute("CREATE TABLE silver.contribution (amount DOUBLE)")
        con.execute("INSERT INTO silver.contribution VALUES (1.0)"
                    if populated else "INSERT INTO silver.contribution VALUES (NULL)")

    def test_a_column_populated_on_almost_nothing_is_not_a_working_join(self, con):
        """0.2% populated is not a join. Rounding it up to 'present' is the
        overclaim this platform exists to avoid."""
        con.execute("CREATE TABLE silver.thing (x INTEGER)")
        con.execute("INSERT INTO silver.thing SELECT NULL FROM range(999)")
        con.execute("INSERT INTO silver.thing VALUES (1)")
        state = GA._column_state(con, "silver.thing", "x")
        assert state["populated_pct"] == 0.1
        assert state["populated_pct"] < 1.0

    def test_empty_column_is_distinguished_from_absent_column(self, con):
        con.execute("CREATE TABLE silver.thing (x INTEGER)")
        present = GA._column_state(con, "silver.thing", "x")
        absent = GA._column_state(con, "silver.thing", "nope")
        assert present["column_exists"] is True and present["rows"] == 0
        assert absent["column_exists"] is False and absent["rows"] is None

    def test_reachable_depth_stops_at_the_first_break(self, con):
        out = GA.measure(con, GA.CHAINS[0])
        assert out["reachable_depth"] == 0
        assert out["breaks_at"] == GA.CHAINS[0].steps[0].name
        assert out["complete"] is False
