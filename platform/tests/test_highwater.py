import pytest

from groundtruth import store
from groundtruth.systems import highwater as H


class TestYearNormalisation:
    """The publisher switches format mid-series. Left alone, one financial year
    becomes two values and the time series silently splits."""

    @pytest.mark.parametrize("raw,expect", [
        ("2016-17", "2016-17"), ("2021/22", "2021-22"),
        ("2020-21", "2020-21"), ("2023 / 24", "2023-24"),
        ("2019-2020", "2019-20"),
    ])
    def test_formats_converge(self, raw, expect):
        assert H.normalise_year(raw) == expect

    def test_hyphen_and_slash_forms_of_one_year_are_equal(self):
        assert H.normalise_year("2021/22") == H.normalise_year("2021-22")

    @pytest.mark.parametrize("raw", ["Not Recorded", "", None, "n/a", "2021"])
    def test_unparseable_years_return_none(self, raw):
        assert H.normalise_year(raw) is None


class TestOverrideRate:
    def _seed(self, con, rows):
        con.execute("""CREATE TABLE silver.flood_objection (
            lpa VARCHAR, lpa_website VARCHAR, reference VARCHAR, description VARCHAR,
            residential_units DOUBLE, year_objection VARCHAR, year_decision VARCHAR,
            outcome VARCHAR)""")
        con.executemany(
            "INSERT INTO silver.flood_objection VALUES (?,?,?,?,?,?,?,?)", rows)

    def test_unknown_outcomes_are_excluded_from_the_rate(self, tmp_path):
        """Including unknowns in the denominator would make the override rate
        improve every time the Agency fails to learn an outcome."""
        con = store.connect(tmp_path / "db")
        self._seed(con, [
            ("A", None, "r1", "d", 10.0, "2020-21", None, H.FOLLOWED),
            ("A", None, "r2", "d", 10.0, "2020-21", None, H.AGAINST),
            ("A", None, "r3", "d", 10.0, "2020-21", None, H.UNKNOWN),
            ("A", None, "r4", "d", 10.0, "2020-21", None, H.UNKNOWN),
        ])
        H.build(con)
        row = con.execute("SELECT override_rate_pct, unknown_pct FROM gold.highwater_trend").fetchone()
        assert row[0] == pytest.approx(50.0), "1 of 2 decided cases, not 1 of 4"
        assert row[1] == pytest.approx(50.0), "unknown share reported separately"
        con.close()

    def test_no_decided_cases_gives_null_not_zero(self, tmp_path):
        con = store.connect(tmp_path / "db")
        self._seed(con, [("A", None, "r1", "d", 1.0, "2024-25", None, H.UNKNOWN)])
        H.build(con)
        assert con.execute(
            "SELECT override_rate_pct FROM gold.highwater_trend").fetchone()[0] is None
        con.close()


class TestLocatability:
    def test_reports_that_nothing_carries_a_location(self, tmp_path):
        con = store.connect(tmp_path / "db")
        con.execute("""CREATE TABLE silver.flood_objection (
            lpa VARCHAR, lpa_website VARCHAR, reference VARCHAR, description VARCHAR,
            residential_units DOUBLE, year_objection VARCHAR, year_decision VARCHAR,
            outcome VARCHAR)""")
        con.executemany("INSERT INTO silver.flood_objection VALUES (?,?,?,?,?,?,?,?)", [
            ("Authority A", None, "21/0751/FUL", "houses", 40.0, "2021-22", None, H.FOLLOWED),
            ("Authority B", "http://x", "22/1234", "flats", 12.0, "2022-23", None, H.AGAINST)])
        loc = H.locatability(con)
        # The reference is the only key to the site; the location lives in the
        # authority's own register, not in this file.
        assert loc["with_reference"] == 2 and loc["authorities"] == 2
        assert loc["with_public_register_link"] == 1
        con.close()
