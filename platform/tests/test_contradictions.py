"""Contradiction detection.

The rule under test: two disagreeing official records are both reported, neither
is chosen, and a check that could not run is never reported as agreement.
"""
import pytest

from groundtruth import contradictions as C
from groundtruth import store


@pytest.fixture
def con(tmp_path):
    c = store.connect(tmp_path / "db")
    c.execute("CREATE SCHEMA IF NOT EXISTS gold")
    yield c
    c.close()


def _catchment(con, summary_count):
    con.execute("""CREATE TABLE gold.catchment_district (
        lad_code VARCHAR, lad_name VARCHAR, schools INTEGER)""")
    con.execute("INSERT INTO gold.catchment_district VALUES ('E1','Adur',?)",
                [summary_count])
    # the summary counts mainstream schools, so the detail carries the flag
    con.execute("""CREATE TABLE gold.catchment_school (
        urn VARCHAR, lad_code VARCHAR, mainstream BOOLEAN)""")
    con.execute("INSERT INTO gold.catchment_school VALUES "
                "('1','E1',TRUE),('2','E1',TRUE),('3','E1',FALSE)")


CHECK = next(c for c in C.CHECKS if c.id == "catchment-school-count")


class TestRunning:
    def test_unrun_check_is_not_agreement(self, con):
        """An untested claim and a tested one that passed must not look alike."""
        out = C.run_check(con, CHECK)
        assert out["run"] is False and "needs" in out["reason"]
        assert out["disagreements"] == []

    def test_agreement_produces_no_disagreement(self, con):
        _catchment(con, summary_count=2)
        out = C.run_check(con, CHECK)
        assert out["run"] is True and out["disagreed"] == 0
        assert out["agreement_pct"] == 100.0

    def test_disagreement_reports_both_sides_and_picks_neither(self, con):
        _catchment(con, summary_count=5)
        out = C.run_check(con, CHECK)
        assert out["disagreed"] == 1
        d = out["disagreements"][0]
        assert d["left_value"] == 5 and d["right_value"] == 2
        assert d["difference"] == -3
        assert d["left"] and d["right"], "each side names where it came from"
        assert "correct" not in out and "resolved" not in out

    def test_specialist_settings_are_not_counted_as_a_contradiction(self, con):
        """Comparing the mainstream summary to every row reported 294 false
        contradictions on the real corpus. The filter is the fix."""
        _catchment(con, summary_count=2)
        assert C.run_check(con, CHECK)["disagreed"] == 0

    def test_broken_check_is_reported_not_silently_passed(self, con):
        con.execute("CREATE TABLE gold.catchment_district (lad_code VARCHAR)")
        con.execute("CREATE TABLE gold.catchment_school (urn VARCHAR)")
        out = C.run_check(con, CHECK)
        assert out["run"] is False and "failed to run" in out["reason"]

    def test_tolerance_absorbs_rounding_but_not_a_real_gap(self, con):
        _catchment(con, summary_count=3)
        loose = C.Check(**{**CHECK.__dict__, "id": "loose", "tolerance": 1.0})
        assert C.run_check(con, loose)["disagreed"] == 0
        tight = C.Check(**{**CHECK.__dict__, "id": "tight", "tolerance": 0.0})
        assert C.run_check(con, tight)["disagreed"] == 1


class TestSuite:
    def test_run_all_separates_unrun_from_agreed(self, con):
        _catchment(con, summary_count=5)
        out = C.run_all(con)
        assert out["checks"] == len(C.CHECKS)
        assert out["run"] == 1
        assert len(out["unrun"]) == len(C.CHECKS) - 1
        assert out["total_disagreements"] == 1

    def test_every_check_declares_the_tables_it_needs(self):
        for c in C.CHECKS:
            assert c.tables, f"{c.id} names no tables"
            assert c.left and c.right, f"{c.id} does not describe both routes"


class TestLastmilePremises:
    """The authority summary and the postcode detail are two routes to one
    number, and they disagreed for Merton, Lewisham and Tower Hamlets by
    exactly one premise each: a premise the publisher gave a district name and
    no district code. The summary counts it, the code-keyed detail cannot see
    it.
    """

    CHECK = next(c for c in C.CHECKS if c.id == "lastmile-premises")

    def _build(self, con, rows):
        from groundtruth.store import insert_many
        from groundtruth.systems import lastmile as LM
        con.execute("""CREATE TABLE silver.premises_connectivity (
            uprn VARCHAR, postcode_key VARCHAR, postcode VARCHAR,
            current_gigabit VARCHAR, future_gigabit VARCHAR,
            subsidy_status VARCHAR, lad_code VARCHAR, lad_name VARCHAR)""")
        insert_many(con, "INSERT INTO silver.premises_connectivity "
                         "VALUES (?,?,?,?,?,?,?,?)", rows)
        con.execute("""CREATE TABLE silver.new_build_sale (
            transaction_id VARCHAR, price DOUBLE, sale_date VARCHAR,
            postcode_key VARCHAR, postcode VARCHAR, property_type VARCHAR,
            paon VARCHAR, street VARCHAR)""")
        LM.build(con)

    def test_a_codeless_premise_is_not_a_contradiction(self, con):
        self._build(con, [
            ("1", "AA11AA", "AA1 1AA", "true", "false", None, "E09000024", "Merton"),
            ("2", "SW199DL", "SW19 9DL", "true", "false", None, None,      "Merton"),
        ])
        out = C.run_check(con, self.CHECK)
        assert out["run"] is True
        assert out["disagreed"] == 0, out["disagreements"]

    def test_a_real_gap_is_still_reported(self, con):
        """The fix must not be a tolerance wide enough to hide anything."""
        self._build(con, [
            ("1", "AA11AA", "AA1 1AA", "true", "false", None, "E09000024", "Merton"),
        ])
        con.execute("UPDATE gold.lastmile_authority SET premises = premises + 1")
        out = C.run_check(con, self.CHECK)
        assert out["disagreed"] == 1
        assert out["disagreements"][0]["difference"] == -1
