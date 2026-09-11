"""Upper-tier figures on the district map.

Care, SEND and school capacity are published per upper-tier authority. These
pin the ways that goes wrong: a county's figure landing on a district outside
the county, a grouping with no council treated as one, and a reissued district
code splitting one place into two.
"""
import duckdb
import pytest

from groundtruth import audit, places


@pytest.fixture
def con():
    c = duckdb.connect(":memory:")
    c.execute("CREATE SCHEMA silver")
    c.execute("CREATE SCHEMA gold")
    c.execute("CREATE TABLE silver.lad (lad_code VARCHAR, lad_name VARCHAR)")
    c.execute("""INSERT INTO silver.lad VALUES
        ('E07000008', 'Cambridge'), ('E06000031', 'Peterborough'),
        ('E08000016', 'Barnsley'), ('E09000025', 'Newham')""")
    yield c
    c.close()


def _lookup(con):
    con.execute("""CREATE TABLE silver.lad_county (lad_code VARCHAR, lad_name VARCHAR,
                   county_code VARCHAR, county_name VARCHAR)""")
    con.execute("""INSERT INTO silver.lad_county VALUES
        ('E07000008', 'Cambridge', 'E10000003', 'Cambridgeshire'),
        ('E08000016', 'Barnsley',  'E11000003', 'South Yorkshire'),
        ('E09000025', 'Newham',    'E13000001', 'Inner London')""")


def _tier(con):
    return {r[0]: r[1:] for r in con.execute(
        f"SELECT lad_code, authority_code, figure_for FROM ({places.upper_tier_sql(con)})"
    ).fetchall()}


class TestUpperTier:
    def test_without_the_lookup_every_district_stands_for_itself(self, con):
        assert _tier(con)["E07000008"] == ("E07000008", "district")

    def test_only_county_councils_take_on_a_districts_figures(self, con):
        _lookup(con)
        t = _tier(con)
        assert t["E07000008"] == ("E10000003", "county")
        # Metropolitan counties and Inner London are groupings, not councils.
        assert t["E08000016"] == ("E08000016", "district")
        assert t["E09000025"] == ("E09000025", "district")
        assert t["E06000031"] == ("E06000031", "district")

    def test_a_county_name_resolves_to_the_county_not_a_district(self, con):
        _lookup(con)
        idx = places.authority_index(con)
        assert idx[places.normalise_authority("Cambridgeshire County Council")][0] == "E10000003"
        assert places.normalise_authority("Cambridge") not in idx


class TestCareOnTheMap:
    def test_a_county_figure_reaches_its_own_districts_once(self, con):
        _lookup(con)
        con.execute("""CREATE TABLE gold.bellwether_group (local_authority VARCHAR,
            group_name VARCHAR, branded BOOLEAN, locations INTEGER, beds INTEGER,
            la_beds INTEGER, share_pct DOUBLE)""")
        con.execute("""INSERT INTO gold.bellwether_group VALUES
            ('Cambridgeshire', 'A', true,  3, 300, 1000, 30.0),
            ('Cambridgeshire', 'B', true,  1, 100, 1000, 10.0),
            ('Peterborough',   'C', false, 2,  50,  200, 25.0)""")
        from groundtruth.systems import bellwether
        bellwether.build_districts(con)
        rows = {r[0]: r[1:] for r in con.execute(
            "SELECT lad_code, figure_for, group_name, share_pct FROM gold.bellwether_district"
        ).fetchall()}
        assert len(rows) == 4                          # one row per district
        assert rows["E07000008"] == ("county", "A", 30.0)
        assert rows["E06000031"] == ("district", "C", 25.0)
        assert rows["E08000016"][1] is None            # nothing published for it here


class TestReissuedDistrictCodes:
    def test_they_map_back_to_the_boundary_vintage(self):
        c = duckdb.connect(":memory:")
        expr = places.boundary_code_sql("x")
        got = dict(c.execute(f"SELECT x, {expr} FROM (VALUES ('E08000038'), "
                             "('E08000039'), ('E06000001'), (NULL)) v(x)").fetchall())
        assert got == {"E08000038": "E08000016", "E08000039": "E08000019",
                       "E06000001": "E06000001", None: None}

    def test_the_audit_flags_a_spine_code_the_boundaries_do_not_hold(self, con):
        con.execute("CREATE TABLE silver.place_postcode (postcode_key VARCHAR, lad_code VARCHAR)")
        con.execute("""INSERT INTO silver.place_postcode VALUES
            ('S701AA', 'E08000038'), ('EH11AA', 'S12000036'), ('CB11AA', 'E07000008')""")
        a = audit.Audit()
        audit.check_district_codes(con, a)
        [f] = a.findings
        assert "E08000038" in f.evidence and "S12000036" not in f.evidence
