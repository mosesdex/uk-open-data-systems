import duckdb
import pytest

from groundtruth import places as PL


@pytest.fixture
def con():
    con = duckdb.connect(":memory:")
    con.execute("CREATE SCHEMA silver; CREATE SCHEMA gold")
    con.execute("CREATE TABLE silver.lad (lad_code VARCHAR, lad_name VARCHAR)")
    con.execute("INSERT INTO silver.lad VALUES ('E07000032', 'Amber Valley'), "
                "('E09000007', 'Camden')")
    con.execute("""CREATE TABLE gold.baseline_district
                   (lad_code VARCHAR, outlets INTEGER,
                    adjusted_spills DOUBLE, reported_spills DOUBLE)""")
    con.execute("INSERT INTO gold.baseline_district VALUES "
                "('E07000032', 14, 812.5, 790.0)")
    return con


def test_a_placed_table_reaches_bylad(con):
    view = PL.place_view(con)
    assert view["places"]["E07000032"]["baseline"]["outlets"] == 14
    assert view["places"]["E07000032"]["baseline"]["adjusted_spills"] == 812.5


def test_a_district_absent_from_the_table_gains_no_entry(con):
    view = PL.place_view(con)
    assert "baseline" not in view["places"].get("E09000007", {})


def test_resolution_reports_placed_coverage(con):
    view = PL.place_view(con)
    rep = view["resolution"]["baseline"]
    assert rep["matched"] == 1
    assert rep["names"] == 2
    assert rep["rate"] == 50.0


def test_the_join_column_is_dropped_from_the_published_row(con):
    view = PL.place_view(con)
    assert "lad_code" not in view["places"]["E07000032"]["baseline"]
