import pytest

from groundtruth import store
from groundtruth.systems import compass as C


def _csv(tmp_path, rows):
    header = ("time_period,time_identifier,geographic_level,country_code,country_name,"
              "region_name,region_code,old_la_code,la_name,new_la_code,pcon_code,"
              "pcon_name,phase_type_grouping,establishment_type,hospital_school,"
              "sen_provision,pupil_count,pupil_percent")
    p = tmp_path / "sen.csv"
    p.write_text(header + "\n" + "\n".join(rows) + "\n")
    return p


def _row(period, la, code, phase, est, hosp, provision, count, region="East"):
    # Fields are quoted: the provision label contains a comma
    # ("Education, health and care plan"), which splits an unquoted row.
    cells = [period, "Academic year", "Local authority", "E92000001", "England",
             region, "E12", "301", la, code, "", "", phase, est, hosp,
             provision, str(count), "1.0"]
    return ",".join(f'"{c}"' for c in cells)


class TestCubeCollapse:
    """The file carries subtotals inside itself. Summing across them multiplies
    the answer: an early version reported 2.15m EHC plans against a real figure
    near 576,000."""

    def test_only_the_fully_totalled_cell_is_counted(self, tmp_path):
        rows = [
            _row("201516", "Anytown", "E1", "Total", "Total", "Total", C.EHC_PLAN, 100),
            # the same 100 children, broken down three more ways
            _row("201516", "Anytown", "E1", "State-funded primary", "Total", "Total", C.EHC_PLAN, 60),
            _row("201516", "Anytown", "E1", "Total", "Community school", "Total", C.EHC_PLAN, 40),
            _row("201516", "Anytown", "E1", "Total", "Total", "No", C.EHC_PLAN, 98),
        ]
        con = store.connect(tmp_path / "db")
        C.load(con, _csv(tmp_path, rows)); C.build(con)
        total = con.execute("SELECT sum(pupils) FROM gold.compass_series").fetchone()[0]
        assert total == 100, "subtotal rows must not be added to the total"
        con.close()

    def test_one_row_per_authority_year_provision(self, tmp_path):
        rows = [_row(f"20{y}{y+1}", "Anytown", "E1", "Total", "Total", "Total",
                     C.EHC_PLAN, 100 + y) for y in range(15, 20)]
        con = store.connect(tmp_path / "db")
        C.load(con, _csv(tmp_path, rows)); C.build(con)
        worst = con.execute("""SELECT max(n) FROM (SELECT count(*) n FROM gold.compass_series
                               GROUP BY la_code, year, provision)""").fetchone()[0]
        assert worst == 1
        con.close()


class TestTrend:
    def test_a_rising_series_projects_upward(self, tmp_path):
        rows = [_row(f"20{y}{y+1}", "Anytown", "E1", "Total", "Total", "Total",
                     C.EHC_PLAN, 100 + (y - 15) * 10) for y in range(15, 22)]
        con = store.connect(tmp_path / "db")
        C.load(con, _csv(tmp_path, rows)); C.build(con)
        row = con.execute("""SELECT pupils_per_year, projected_change_3yr
                             FROM gold.compass_trend""").fetchone()
        assert row[0] == pytest.approx(10.0, abs=0.5)
        assert row[1] == pytest.approx(30.0, abs=2)
        con.close()

    def test_short_series_gets_no_projection(self, tmp_path):
        """Fewer than five years is not enough to extrapolate from."""
        rows = [_row(f"20{y}{y+1}", "Anytown", "E1", "Total", "Total", "Total",
                     C.EHC_PLAN, 100) for y in range(15, 18)]
        con = store.connect(tmp_path / "db")
        C.load(con, _csv(tmp_path, rows)); C.build(con)
        assert con.execute("SELECT count(*) FROM gold.compass_trend").fetchone()[0] == 0
        con.close()


class TestPrivacy:
    def test_only_aggregate_columns_are_retained(self, tmp_path):
        """No column capable of identifying a child is loaded. This is what
        makes the system lawful to build without a sharing agreement."""
        rows = [_row("201516", "Anytown", "E1", "Total", "Total", "Total", C.EHC_PLAN, 100)]
        con = store.connect(tmp_path / "db")
        C.load(con, _csv(tmp_path, rows))
        cols = {r[0] for r in con.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema='silver' AND table_name='sen_provision'").fetchall()}
        assert cols == {"period", "year", "level", "la_name", "la_code", "region",
                        "phase", "establishment_type", "hospital_school",
                        "provision", "pupils"}
        con.close()
