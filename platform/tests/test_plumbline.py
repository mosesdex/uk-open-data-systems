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
        of that against the statutory 13 weeks. Both must be reported."""
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


class TestHeadlineBase:
    """The headline once read only the decisions made without a performance
    agreement, leaving out three quarters of them."""
    HEAD = [P.C_LPA, P.C_QUARTER, P.C_MAJOR_DECISIONS, P.C_MAJOR_IN_TIME,
            P.C_MAJOR_IN_TIME_PA, P.C_MAJOR_PA, P.C_MAJDW_TOTAL, P.C_MAJDW_8,
            P.C_MAJDW_8_13, P.C_MAJDW_MAX, P.C_MAJDW_PA]

    def _csv(self, tmp_path, values):
        import csv
        p = tmp_path / "ps2.csv"
        with open(p, "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["title"])
            w.writerow(["subtitle"])
            w.writerow(self.HEAD)
            w.writerow(values)
        return p

    def test_the_headline_counts_decisions_made_under_an_extension(self, tmp_path):
        """Bournemouth, Christchurch and Poole, 2024 Q2, as published: 29 major
        decisions, 2 without an agreement (both in time) and 27 under one (23 in
        time). Reading only the first half gave 2 of 2."""
        con = store.connect(tmp_path / "db")
        P.load(con, self._csv(tmp_path, ["BCP", "2024 Q2", 29, 2, 23, 27, 21, 0, 2, "", 19]))
        P.build(con)
        headline, statutory = con.execute(
            "SELECT headline_pct, statutory_pct FROM gold.plumbline_quarter").fetchone()
        assert headline == round(100 * 25 / 29, 1)
        assert statutory == round(100 * 2 / 21, 1)
        assert P.extension_share(con, since="2024") == (round(100 * 27 / 29, 1),
                                                         round(100 * 19 / 21, 1))
        con.close()

    def test_both_halves_of_the_headline_come_from_the_same_scope(self):
        assert P.C_MAJOR_DECISIONS.endswith("(all)")
        assert P.C_MAJOR_IN_TIME.endswith("(excluding PAs)")
        assert P.C_MAJOR_IN_TIME_PA.endswith("(PAs only)")
