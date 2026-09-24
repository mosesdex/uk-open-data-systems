import duckdb
import pytest

from groundtruth.systems import junction as J


@pytest.fixture
def con():
    con = duckdb.connect(":memory:")
    con.execute("CREATE SCHEMA silver; CREATE SCHEMA gold")
    con.execute("""CREATE TABLE silver.place_postcode
                   (postcode_key VARCHAR, postcode VARCHAR, positional_quality INTEGER,
                    easting INTEGER, northing INTEGER, lad_code VARCHAR,
                    ward_code VARCHAR, country_code VARCHAR)""")
    con.executemany("INSERT INTO silver.place_postcode VALUES (?,?,?,?,?,?,?,?)", [
        ("SW1A1AA", "SW1A 1AA", 10, 530047, 179951, "E09000033", "W1", "E92000001"),
    ])
    con.execute("""CREATE TABLE silver.junction_connection
                   (operator VARCHAR, postcode VARCHAR, easting INTEGER, northing INTEGER,
                    connection_status VARCHAR, connected_mw DOUBLE, accepted_mw DOUBLE)""")
    con.executemany("INSERT INTO silver.junction_connection VALUES (?,?,?,?,?,?,?)", [
        ("UKPN", "SW1A 1AA", None, None, "Connected", 2.5, 0.0),
        ("UKPN", "SW1A 1AA", None, None, "Accepted to connect", 0.0, 1.5),
        # no postcode, but a grid reference near the one centroid above
        ("UKPN", None, 530050, 179955, "Connected", 1.0, 0.0),
        # neither, so it cannot be placed and must be counted as unplaced
        ("UKPN", None, None, None, "Connected", 9.9, 0.0),
    ])
    return con


def test_a_postcode_places_a_connection(con):
    J.by_district(con)
    row = con.execute("SELECT connections, connected_mw, accepted_mw "
                      "FROM gold.junction_district WHERE lad_code = 'E09000033'").fetchone()
    assert row[0] == 3
    assert row[1] == pytest.approx(3.5)
    assert row[2] == pytest.approx(1.5)


def test_a_grid_reference_places_a_connection_with_no_postcode(con):
    J.by_district(con)
    n = con.execute("SELECT connections FROM gold.junction_district "
                    "WHERE lad_code = 'E09000033'").fetchone()[0]
    assert n == 3, "the coordinate-only row should be placed by its nearest centroid"


def test_a_row_with_no_location_is_reported_not_dropped_silently(con):
    J.by_district(con)
    pct = con.execute("SELECT placed_pct FROM gold.junction_district "
                      "WHERE lad_code = 'E09000033'").fetchone()[0]
    assert pct == 75.0, "3 of 4 rows placed, and the page must be able to say so"


def test_no_district_row_is_created_for_an_unplaceable_row(con):
    J.by_district(con)
    codes = [r[0] for r in con.execute("SELECT lad_code FROM gold.junction_district").fetchall()]
    assert codes == ["E09000033"]
    assert None not in codes
