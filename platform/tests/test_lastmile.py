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


class TestRecencyFilter:
    """The connectivity duty covers homes built recently. Loading 31 years of
    price-paid data and treating a 1998 new-build as a new home would answer the
    wrong question."""

    def test_since_drops_older_sales(self, tmp_path):
        import csv
        rows = [
            "{a},250000,1998-05-01 00:00,AA1 1AA,D,Y,F,1,,Old Rd,,,,,",
            "{b},300000,2023-05-01 00:00,BB2 2BB,D,Y,F,2,,New Rd,,,,,",
        ]
        p = tmp_path / "pp.csv"
        p.write_text("\n".join(r.format(a="{x1}", b="{x2}") for r in rows) + "\n")
        from groundtruth import store
        con = store.connect(tmp_path / "db")
        n = LM.load_new_builds(con, p, since="2021-01-01")
        assert n == 1, "only the 2023 sale should survive the recency filter"
        d = con.execute("SELECT sale_date FROM silver.new_build_sale").fetchone()[0]
        assert d.startswith("2023")
        con.close()

    def test_no_since_keeps_everything(self, tmp_path):
        p = tmp_path / "pp.csv"
        p.write_text(
            "{x1},250000,1998-05-01 00:00,AA1 1AA,D,Y,F,1,,Old Rd,,,,,\n"
            "{x2},300000,2023-05-01 00:00,BB2 2BB,D,Y,F,2,,New Rd,,,,,\n")
        from groundtruth import store
        con = store.connect(tmp_path / "db")
        assert LM.load_new_builds(con, p) == 2
        con.close()


class TestPublisherCsvDialect:
    """BDUK writes a blank district code as a quoted empty field, and two
    district names contain a comma. DuckDB sniffs the CSV dialect from the
    first file of the glob and applies it to every other member of the
    archive, so an archive whose first member happens to contain no quoted
    field at all is read with quoting disabled: '""' survives as two literal
    quote characters, and 'Kingston upon Hull, City of' is truncated at its
    comma. Both are silent -- the rows load, they are just wrong.
    """

    HEADER = ("uprn,struprn,bduk_recognised_premises,country,postcode,lot_id,"
              "lot_name,subsidy_control_status,current_gigabit,future_gigabit,"
              "local_authority_district_ons_code,local_authority_district_ons,"
              "region_ons_code,region_ons")

    def _archive(self, tmp_path):
        import zipfile
        # sorted first: nothing quoted anywhere, which is what misleads the sniffer
        plain = ("1,str1,true,England,AA1 1AA,1,Lot,Gigabit White,true,false,"
                 "E09000001,Anytown,E12000007,London")
        quoted = ('2,str2,true,England,BB2 2BB,1,Lot,Gigabit Grey/Black,true,false,'
                  '"",Merton,"",London\n'
                  '3,str3,true,England,CC3 3CC,1,Lot,Gigabit Grey/Black,true,false,'
                  'E06000010,"Kingston upon Hull, City of",E12000003,Yorkshire')
        zp = tmp_path / "bduk_region.zip"
        with zipfile.ZipFile(zp, "w") as z:
            z.writestr("a_unquoted.csv", self.HEADER + "\n" + plain + "\n")
            z.writestr("b_quoted.csv", self.HEADER + "\n" + quoted + "\n")
        return zp

    def test_a_blank_district_code_loads_as_null_not_two_quote_characters(self, tmp_path):
        con = store.connect(tmp_path / "db")
        LM.load_premises(con, self._archive(tmp_path))
        code = con.execute("SELECT lad_code FROM silver.premises_connectivity "
                           "WHERE uprn = '2'").fetchone()[0]
        assert code is None, f"blank code loaded as {code!r}"
        con.close()

    def test_a_district_name_containing_a_comma_survives_intact(self, tmp_path):
        con = store.connect(tmp_path / "db")
        LM.load_premises(con, self._archive(tmp_path))
        name = con.execute("SELECT lad_name FROM silver.premises_connectivity "
                           "WHERE uprn = '3'").fetchone()[0]
        assert name == "Kingston upon Hull, City of"
        con.close()


class TestMissingDistrictCode:
    """Three London premises carry a district name and no district code. The
    authority table groups by name, so they are counted there; anything keyed
    on the code could not reach them, and the two views of one system
    disagreed by exactly one premise in Merton, Lewisham and Tower Hamlets.
    """

    def test_a_premise_with_a_name_and_no_code_keeps_its_district(self, tmp_path):
        con = store.connect(tmp_path / "db")
        _seed(con, [
            ("1", "AA11AA", "AA1 1AA", "true", "false", None, "E09000024", "Merton"),
            ("2", "ZZ99ZZ", "ZZ9 9ZZ", "true", "false", None, None,        "Merton"),
        ], [])
        LM.build(con)
        row = con.execute("SELECT lad_code, premises FROM gold.lastmile_postcode "
                          "WHERE postcode_key = 'ZZ99ZZ'").fetchone()
        assert row == ("E09000024", 1), \
            "the district is known by name, so the code is recoverable"
        con.close()

    def test_the_authority_total_is_reachable_from_the_postcode_table_by_code(self, tmp_path):
        con = store.connect(tmp_path / "db")
        _seed(con, [
            ("1", "AA11AA", "AA1 1AA", "true", "false", None, "E09000024", "Merton"),
            ("2", "ZZ99ZZ", "ZZ9 9ZZ", "true", "false", None, None,        "Merton"),
        ], [])
        LM.build(con)
        left = con.execute("SELECT premises FROM gold.lastmile_authority "
                           "WHERE lad_code = 'E09000024'").fetchone()[0]
        right = con.execute("SELECT sum(premises) FROM gold.lastmile_postcode "
                            "WHERE lad_code = 'E09000024'").fetchone()[0]
        assert left == right == 2
        con.close()

    def test_a_district_with_no_code_anywhere_is_not_given_someone_elses(self, tmp_path):
        """Recovering the code from the name is only sound because the name
        maps to exactly one code. A name that never appears with a code keeps
        a null rather than borrowing one."""
        con = store.connect(tmp_path / "db")
        _seed(con, [
            ("1", "AA11AA", "AA1 1AA", "true", "false", None, "E09000024", "Merton"),
            ("2", "ZZ99ZZ", "ZZ9 9ZZ", "true", "false", None, None,        "Nowhere"),
        ], [])
        LM.build(con)
        row = con.execute("SELECT lad_code FROM gold.lastmile_postcode "
                          "WHERE postcode_key = 'ZZ99ZZ'").fetchone()
        assert row[0] is None
        con.close()
