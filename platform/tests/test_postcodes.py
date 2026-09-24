import duckdb
import pytest

from groundtruth import postcodes as PC


@pytest.fixture
def con():
    con = duckdb.connect(":memory:")
    con.execute("CREATE SCHEMA silver")
    con.execute("""CREATE TABLE silver.place_postcode
                   (postcode_key VARCHAR, postcode VARCHAR, positional_quality INTEGER,
                    easting INTEGER, northing INTEGER, lad_code VARCHAR,
                    ward_code VARCHAR, country_code VARCHAR)""")
    rows = [
        ("SW1A1AA", "SW1A 1AA", 10, 0, 0, "E09000033", "W1", "E92000001"),
        ("SW1A1AB", "SW1A 1AB", 10, 0, 0, "E09000033", "W1", "E92000001"),
        # one sector, two districts, heavily skewed
        ("GU216AA", "GU21 6AA", 10, 0, 0, "E07000217", "W2", "E92000001"),
        ("GU216AB", "GU21 6AB", 10, 0, 0, "E07000217", "W2", "E92000001"),
        ("GU216AC", "GU21 6AC", 10, 0, 0, "E07000214", "W3", "E92000001"),
        # Scotland, which this platform does not cover
        ("AB101AB", "AB10 1AB", 10, 0, 0, None, None, "S92000003"),
    ]
    con.executemany("INSERT INTO silver.place_postcode VALUES (?,?,?,?,?,?,?,?)", rows)
    return con


def test_an_unambiguous_sector_yields_one_district(con):
    idx = PC.sector_index(con)
    assert idx["sectors"]["SW1A1"] == ["E09000033"]


def test_an_ambiguous_sector_yields_every_district_dominant_first(con):
    idx = PC.sector_index(con)
    assert idx["sectors"]["GU216"] == ["E07000217", "E07000214"]


def test_a_postcode_with_no_district_is_left_out(con):
    idx = PC.sector_index(con)
    assert "AB101" not in idx["sectors"]


def test_the_index_reports_its_own_accuracy(con):
    idx = PC.sector_index(con)
    # 5 placed postcodes, 4 of which the dominant rule places correctly
    assert idx["postcodes"] == 5
    assert idx["sectors_total"] == 2
    assert idx["dominant_accuracy_pct"] == 80.0


def test_the_key_is_the_sector_with_no_space(con):
    idx = PC.sector_index(con)
    assert all(" " not in k for k in idx["sectors"])
