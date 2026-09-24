import duckdb
import pytest

from groundtruth import areas as A


@pytest.fixture
def con():
    con = duckdb.connect(":memory:")
    con.execute("CREATE SCHEMA silver; CREATE SCHEMA gold")
    con.execute("CREATE TABLE silver.lad (lad_code VARCHAR, lad_name VARCHAR)")
    con.executemany("INSERT INTO silver.lad VALUES (?, ?)", [
        ("E09000007", "Camden"), ("E09000033", "Westminster"),
        ("E08000003", "Manchester"), ("W06000009", "Pembrokeshire"),
    ])
    con.execute("CREATE TABLE silver.lad_area (lad_code VARCHAR, area_code VARCHAR, "
                "area_name VARCHAR, kind VARCHAR)")
    con.executemany("INSERT INTO silver.lad_area VALUES (?, ?, ?, ?)", [
        ("E09000007", "E12000007", "London", "region"),
        ("E09000033", "E12000007", "London", "region"),
        ("E08000003", "E12000002", "North West", "region"),
        ("E08000003", "E47000001", "Greater Manchester", "combined authority"),
    ])
    con.execute("""CREATE TABLE gold.lastmile_authority
                   (lad_code VARCHAR, premises INTEGER, gigabit_now INTEGER,
                    gigabit_pct DOUBLE)""")
    con.executemany("INSERT INTO gold.lastmile_authority VALUES (?, ?, ?, ?)", [
        ("E09000007", 100, 90, 90.0),
        ("E09000033", 900, 450, 50.0),
    ])
    return con


def test_an_area_lists_its_districts(con):
    out = A.build(con)
    assert out["E12000007"]["name"] == "London"
    assert out["E12000007"]["districts"] == ["E09000007", "E09000033"]


def test_a_district_may_belong_to_a_region_and_a_combined_authority(con):
    out = A.build(con)
    assert "E08000003" in out["E12000002"]["districts"]
    assert "E08000003" in out["E47000001"]["districts"]


def test_the_kind_is_carried_so_a_page_can_say_what_it_is_showing(con):
    out = A.build(con)
    assert out["E47000001"]["kind"] == "combined authority"


def test_a_welsh_district_belongs_to_no_area(con):
    out = A.build(con)
    assert not any("W06000009" in a["districts"] for a in out.values())


def test_an_area_whose_districts_are_unknown_is_not_published(con):
    con.execute("INSERT INTO silver.lad_area VALUES "
                "('E99999999', 'E12000099', 'Nowhere', 'region')")
    out = A.build(con)
    assert "E12000099" not in out


def test_a_percentage_is_recomputed_from_the_summed_parts(con):
    # 540 of 1000 premises, not the mean of 90% and 50%, which would be 70%.
    out = A.build(con)
    fig = out["E12000007"]["figures"]["lastmile"]
    assert fig["gigabit_pct"] == 54.0
    assert fig["premises"] == 1000
    assert fig["rule"] == "recomputed"


def test_bellwether_is_refused_rather_than_combined(con):
    con.execute("""CREATE TABLE gold.bellwether_district
                   (lad_code VARCHAR, share_pct DOUBLE, la_beds INTEGER,
                    group_name VARCHAR, authority_name VARCHAR)""")
    con.executemany("INSERT INTO gold.bellwether_district VALUES (?, ?, ?, ?, ?)", [
        ("E09000007", 40.0, 100, "GROUP A", "Camden"),
        ("E09000033", 60.0, 200, "GROUP B", "Westminster"),
    ])
    out = A.build(con)
    fig = out["E12000007"]["figures"].get("bellwether")
    assert fig is not None, "the refusal must be published, not omitted"
    assert fig["rule"] == "not combinable"
    assert "share_pct" not in fig
