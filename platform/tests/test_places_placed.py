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
    # Assert on the districts the loop actually placed, not just Camden's
    # absence: Camden has no row in any table in this fixture, so it never
    # enters `places` regardless of whether the PLACED loop runs at all.
    # Only comparing against the full set catches a loop that places a
    # district it should not, or misses one it should.
    placed = {code for code, entry in view["places"].items() if "baseline" in entry}
    assert placed == {"E07000032"}
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


def test_resolution_marks_itself_placed_and_names_the_unreached_district(con):
    view = PL.place_view(con)
    rep = view["resolution"]["baseline"]
    # A consumer branches on `kind` to tell a placed join apart from a name
    # match; `unmatched` must name the district with no row (Camden) rather
    # than sit empty, which is what the wrong-direction set difference gave.
    assert rep["kind"] == "placed"
    assert rep["unmatched"] == ["E09000007"]
