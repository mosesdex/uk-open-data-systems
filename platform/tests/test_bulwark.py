import json
from datetime import date

import pytest

from groundtruth import store
from groundtruth.systems import bulwark as BK


def _write(tmp_path, rows):
    p = tmp_path / "aims.json"
    p.write_text(json.dumps(rows))
    return p


def _asset(**kw):
    base = dict(asset_id="1", asset_sub_type="Wall", primary_purpose="Flood Risk Management",
                protection_type="Fluvial", asset_maintainer="Environment Agency",
                asset_operator="Unknown", asset_owner="Unknown",
                current_condition="3", target_condition="3",
                last_inspection_date=None, next_inspection_date=None,
                local_authority="Dorset", water_management_area="Wessex",
                water_course_name="River Frome", asset_length=100.0)
    base.update(kw)
    return base


class TestDateParsing:
    """The publisher uses DD/MM/YYYY. Getting this wrong is silent and total."""

    def test_parses_publisher_format(self, tmp_path):
        p = _write(tmp_path, [_asset(next_inspection_date="30/03/2026",
                                     last_inspection_date="12/09/2024")])
        con = store.connect(tmp_path / "t.duckdb")
        BK.load(con, p)
        row = con.execute(
            "SELECT next_inspection, last_inspection FROM silver.flood_defence").fetchone()
        assert row[0] == date(2026, 3, 30), "30/03 is 30 March, not 3 October"
        assert row[1] == date(2024, 9, 12)
        con.close()

    def test_day_and_month_are_not_transposed(self, tmp_path):
        # 13 cannot be a month, so this pins the ordering.
        p = _write(tmp_path, [_asset(next_inspection_date="13/07/2025")])
        con = store.connect(tmp_path / "t.duckdb")
        BK.load(con, p)
        assert con.execute("SELECT next_inspection FROM silver.flood_defence").fetchone()[0] \
            == date(2025, 7, 13)
        con.close()

    def test_wholesale_parse_failure_raises_rather_than_reporting_zero(self, tmp_path):
        """The bug this replaces reported 'no inspection is overdue' from 0 parsed dates."""
        rows = [_asset(next_inspection_date="2026年3月30日") for _ in range(50)]
        p = _write(tmp_path, rows)
        con = store.connect(tmp_path / "t.duckdb")
        with pytest.raises(ValueError, match="date parsing failed"):
            BK.load(con, p)
        con.close()


class TestCoverage:
    def test_maintainer_and_owner_are_reported_separately(self, tmp_path):
        """The alarming number must not stand in for the useful one."""
        p = _write(tmp_path, [
            _asset(asset_maintainer="Environment Agency", asset_owner="Unknown"),
            _asset(asset_maintainer="Local Authority", asset_owner="Unknown"),
            _asset(asset_maintainer="Unknown", asset_owner="Unknown"),
        ])
        con = store.connect(tmp_path / "t.duckdb")
        BK.load(con, p)
        c = BK.coverage(con)
        assert c.owner_known == 0
        assert c.maintainer_known == 2, "maintainer is known even where owner is not"
        con.close()

    def test_condition_coverage_is_measured_not_assumed(self, tmp_path):
        p = _write(tmp_path, [
            _asset(current_condition="3"), _asset(current_condition="  "),
            _asset(current_condition=None), _asset(current_condition="2"),
        ])
        con = store.connect(tmp_path / "t.duckdb")
        BK.load(con, p)
        c = BK.coverage(con)
        # Blank and whitespace must not count as graded.
        assert c.graded == 2 and c.pct(c.graded) == 50.0
        con.close()


class TestOverdue:
    def test_only_past_dates_count_as_overdue(self, tmp_path):
        p = _write(tmp_path, [
            _asset(asset_id="past", next_inspection_date="01/01/2020"),
            _asset(asset_id="future", next_inspection_date="01/01/2099"),
            _asset(asset_id="none", next_inspection_date=None),
        ])
        con = store.connect(tmp_path / "t.duckdb")
        BK.load(con, p)
        rows = BK.overdue(con)
        assert sum(r[1] for r in rows) == 1
        con.close()
