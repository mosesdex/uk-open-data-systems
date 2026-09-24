import duckdb
import pytest

from groundtruth.systems import sentinel as S


@pytest.fixture
def con():
    con = duckdb.connect(":memory:")
    con.execute("CREATE SCHEMA silver; CREATE SCHEMA gold")
    con.execute("""CREATE TABLE silver.place_postcode
                   (postcode_key VARCHAR, postcode VARCHAR, positional_quality INTEGER,
                    easting INTEGER, northing INTEGER, lad_code VARCHAR,
                    ward_code VARCHAR, country_code VARCHAR)""")
    con.executemany("INSERT INTO silver.place_postcode VALUES (?,?,?,?,?,?,?,?)", [
        ("LN57JH", "LN5 7JH", 10, 0, 0, "E07000138", "W1", "E92000001"),
        ("SW1A1AA", "SW1A 1AA", 10, 0, 0, "E09000033", "W2", "E92000001"),
    ])
    con.execute("""CREATE TABLE silver.procurement_award
                   (ocid VARCHAR, buyer VARCHAR, method VARCHAR, value DOUBLE,
                    buyer_postcode VARCHAR, delivery_postcode VARCHAR)""")
    con.executemany("INSERT INTO silver.procurement_award VALUES (?,?,?,?,?,?)", [
        ("a", "Trust", "open", 100.0, "LN5 7JH", None),
        # delivery wins over buyer: the work happens in Westminster
        ("b", "Trust", "limited", 200.0, "LN5 7JH", "SW1A 1AA"),
        ("c", "Trust", "open", 300.0, None, None),
    ])
    return con


def test_an_award_is_placed_by_its_buyer_postcode(con):
    S.by_district(con)
    row = con.execute("SELECT awards, total_value FROM gold.sentinel_district "
                      "WHERE lad_code = 'E07000138'").fetchone()
    assert row == (1, 100.0)


def test_a_delivery_address_beats_the_buyer_address(con):
    S.by_district(con)
    row = con.execute("SELECT awards, total_value FROM gold.sentinel_district "
                      "WHERE lad_code = 'E09000033'").fetchone()
    assert row == (1, 200.0)


def test_the_closed_share_is_counted_per_district(con):
    S.by_district(con)
    closed = con.execute("SELECT closed_awards, closed_pct FROM gold.sentinel_district "
                         "WHERE lad_code = 'E09000033'").fetchone()
    assert closed == (1, 100.0)


def test_the_placed_share_is_published_so_the_count_can_be_judged(con):
    S.by_district(con)
    pct = con.execute("SELECT DISTINCT placed_pct FROM gold.sentinel_district").fetchone()[0]
    assert pct == pytest.approx(66.7, abs=0.1)
