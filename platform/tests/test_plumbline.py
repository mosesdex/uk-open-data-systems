import pytest

from groundtruth import store
from groundtruth.systems import plumbline as P


def _seed(con, rows):
    con.execute("""CREATE TABLE silver.planning_performance (
        lpa VARCHAR, lpa_code VARCHAR, quarter VARCHAR,
        major_decisions DOUBLE, major_in_time DOUBLE,
        minor_decisions DOUBLE, minor_in_time DOUBLE,
        major_dwellings_total DOUBLE, major_dwellings_within_8w DOUBLE,
        major_dwellings_8_to_13w DOUBLE, major_dwellings_within_max DOUBLE)""")
    con.executemany(
        "INSERT INTO silver.planning_performance VALUES (?,?,?,?,?,?,?,?,?,?,?)", rows)


class TestHeadlineVersusStatutory:
    def test_both_figures_are_produced(self, tmp_path):
        """An authority can be at 100% on the published measure and a fraction
        of that against the deadline in law. Both must be reported."""
        con = store.connect(tmp_path / "db")
        _seed(con, [("Anytown", "E1", "2024 Q1",
                     100.0, 100.0, 0.0, 0.0,   # every major decision 'in time'
                     100.0, 5.0, 15.0, None)])  # only 20 within 13 weeks
        P.build(con)
        row = con.execute("""SELECT headline_pct, statutory_pct
                             FROM gold.plumbline_quarter""").fetchone()
        assert row[0] == 100.0
        assert row[1] == 20.0
        con.close()

    def test_zero_decisions_do_not_divide_by_zero(self, tmp_path):
        con = store.connect(tmp_path / "db")
        _seed(con, [("Anytown", "E1", "2024 Q1", 5.0, 5.0, 0.0, 0.0, 0.0, 0.0, 0.0, None)])
        P.build(con)
        assert con.execute(
            "SELECT statutory_pct FROM gold.plumbline_quarter").fetchone()[0] is None
        con.close()

    def test_national_gap_reports_both_denominators(self, tmp_path):
        con = store.connect(tmp_path / "db")
        _seed(con, [("A", "E1", "2024 Q1", 50.0, 40.0, 0.0, 0.0, 80.0, 10.0, 10.0, None)])
        headline, statutory, majors, dwellings = P.national_gap(con, since="2023")
        assert headline == 80.0 and statutory == 25.0
        # The two rates are computed over different populations, so both counts
        # travel with them.
        assert majors == 50.0 and dwellings == 80.0
        con.close()


class TestDiscontinuedColumn:
    def test_transparency_column_status_is_reported(self, tmp_path):
        """'Within maximum time' distinguished statutory from extended, and the
        publisher stopped populating it after 2020. Losing that quietly is the
        kind of thing this system exists to notice."""
        con = store.connect(tmp_path / "db")
        _seed(con, [
            ("A", "E1", "2019 Q1", 1.0, 1.0, 0, 0, 1.0, 1.0, 0.0, 1.0),
            ("A", "E1", "2024 Q1", 1.0, 1.0, 0, 0, 1.0, 1.0, 0.0, None),
        ])
        status = {r[0]: r[3] for r in P.transparency_column_status(con)}
        assert status["2019"] == 100.0
        assert status["2024"] == 0.0
        con.close()


class TestSchemaGuard:
    def test_missing_columns_raise_rather_than_computing_wrongly(self, tmp_path):
        bad = tmp_path / "ps2.csv"
        bad.write_text("title\nsubtitle\nLPANM,Quarter,Something Else\nA,2024 Q1,1\n")
        con = store.connect(tmp_path / "db")
        with pytest.raises(ValueError, match="PS2 columns not found"):
            P.load(con, bad)
        con.close()
