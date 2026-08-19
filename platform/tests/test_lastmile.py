import pytest

from groundtruth import store
from groundtruth.store import insert_many
from groundtruth.systems import lastmile as LM


def _seed(con, premises, sales):
    con.execute("""CREATE TABLE silver.premises_connectivity (
        uprn VARCHAR, postcode_key VARCHAR, postcode VARCHAR,
        current_gigabit VARCHAR, future_gigabit VARCHAR, subsidy_status VARCHAR,
        lad_code VARCHAR, lad_name VARCHAR)""")
    insert_many(con, "INSERT INTO silver.premises_connectivity VALUES (?,?,?,?,?,?,?,?)", premises)
    con.execute("""CREATE TABLE silver.new_build_sale (
        transaction_id VARCHAR, price DOUBLE, sale_date VARCHAR,
        postcode_key VARCHAR, postcode VARCHAR, property_type VARCHAR,
        paon VARCHAR, street VARCHAR)""")
    insert_many(con, "INSERT INTO silver.new_build_sale VALUES (?,?,?,?,?,?,?,?)", sales)


class TestGigabitFlag:
    def test_uses_the_boolean_not_the_subsidy_status(self, tmp_path):
        """current_gigabit is a boolean. 'Gigabit Grey/Black' is a subsidy
        status meaning the market is already served -- a different question.
        Reading the wrong column reports 0% coverage everywhere."""
        con = store.connect(tmp_path / "db")
        _seed(con, [
            ("1", "AA11AA", "AA1 1AA", "true",  "false", "Gigabit Grey/Black", "E1", "Anytown"),
            ("2", "AA11AA", "AA1 1AA", "false", "true",  "Gigabit White",      "E1", "Anytown"),
        ], [])
        LM.build(con)
        row = con.execute("""SELECT premises, gigabit_now, gigabit_pct
                             FROM gold.lastmile_postcode""").fetchone()
        assert row == (2, 1, 50.0)
        con.close()

    def test_flag_matching_is_case_insensitive(self, tmp_path):
        con = store.connect(tmp_path / "db")
        _seed(con, [("1", "AA11AA", "AA1 1AA", "TRUE", "false", None, "E1", "Anytown")], [])
        LM.build(con)
        assert con.execute("SELECT gigabit_now FROM gold.lastmile_postcode").fetchone()[0] == 1
        con.close()


class TestNewBuildComparison:
    def test_new_build_postcodes_are_compared_against_the_rest(self, tmp_path):
        con = store.connect(tmp_path / "db")
        _seed(con, [
            ("1", "NB11AA", "NB1 1AA", "false", "true", None, "E1", "Anytown"),
            ("2", "NB11AA", "NB1 1AA", "false", "true", None, "E1", "Anytown"),
            ("3", "OT11AA", "OT1 1AA", "true",  "false", None, "E1", "Anytown"),
            ("4", "OT11AA", "OT1 1AA", "true",  "false", None, "E1", "Anytown"),
        ], [("t1", 300000.0, "2026-01-01", "NB11AA", "NB1 1AA", "D", "1", "New Road")])
        LM.build(con)
        nb_prem, nb_gig, nb_pct, other_prem, other_pct = LM.comparison(con)
        assert nb_prem == 2 and nb_pct == 0.0
        assert other_prem == 2 and other_pct == 100.0
        con.close()

    def test_postcodes_with_no_sale_are_not_counted_as_new_build(self, tmp_path):
        con = store.connect(tmp_path / "db")
        _seed(con, [("1", "ZZ11ZZ", "ZZ1 1ZZ", "true", "false", None, "E1", "Anytown")], [])
        LM.build(con)
        row = con.execute("""SELECT new_build_sales FROM gold.lastmile_postcode""").fetchone()
        assert row[0] == 0
        con.close()
