import pytest

from groundtruth import store
from groundtruth.store import insert_many
from groundtruth.systems import sightline as SL


def _seed_flood(con, rows):
    con.execute("""CREATE TABLE silver.flood_objection (
        lpa VARCHAR, lpa_website VARCHAR, reference VARCHAR, description VARCHAR,
        residential_units DOUBLE, year_objection VARCHAR, year_decision VARCHAR,
        outcome VARCHAR)""")
    insert_many(con, "INSERT INTO silver.flood_objection VALUES (?,?,?,?,?,?,?,?)", rows)


def _seed_water(con, rows):
    con.execute("""CREATE TABLE silver.water_quality_objection (
        lpa VARCHAR, reference VARCHAR, description VARCHAR, reason VARCHAR)""")
    insert_many(con, "INSERT INTO silver.water_quality_objection VALUES (?,?,?,?)", rows)


class TestStreams:
    def test_a_missing_outcome_field_is_not_the_same_as_an_unknown_outcome(self, tmp_path, monkeypatch):
        """Flood risk records 'unknown' for some cases. Water quality has no
        outcome column at all, which is a different and worse condition."""
        con = store.connect(tmp_path / "db")
        _seed_flood(con, [
            ("A", None, "r1", "d", 1.0, "2024-25", None, "Environment Agency advice followed"),
            ("A", None, "r2", "d", 1.0, "2024-25", None, "Outcome currently unknown"),
        ])
        _seed_water(con, [("A", "r3", "d", "Unacceptable risk to water quality")])
        monkeypatch.setattr(SL, "sheets", lambda p: ["Flood_Risk", "Water_Quality"])
        got = {s.name: s for s in SL.streams(con, tmp_path / "x.ods")}
        assert got["flood risk"].has_outcome_field is True
        assert got["flood risk"].tracked_pct == pytest.approx(50.0)
        assert got["water quality"].has_outcome_field is False
        assert got["water quality"].tracked_pct == 0.0
        con.close()


class TestReasons:
    def test_reasons_are_grouped_with_authority_counts(self, tmp_path):
        con = store.connect(tmp_path / "db")
        _seed_water(con, [
            ("A", "r1", "d", "Insufficient Info - Water Quality"),
            ("B", "r2", "d", "Insufficient Info - Water Quality"),
            ("A", "r3", "d", "Non-mains drainage proposed in sewered area"),
        ])
        _seed_flood(con, [])
        SL.build(con)
        rows = {r[0]: (r[1], r[2]) for r in con.execute(
            "SELECT * FROM gold.sightline_reason").fetchall()}
        assert rows["Insufficient Info - Water Quality"] == (2, 2)
        assert rows["Non-mains drainage proposed in sewered area"] == (1, 1)
        con.close()


class TestSheetIsolation:
    """The workbook holds two datasets. Reading every row concatenates them."""

    def test_ods_reader_can_select_one_sheet(self, tmp_path):
        from groundtruth.ods import sheets as list_sheets, table
        p = "data/bronze/ea_objections.ods"
        import os
        if not os.path.exists(p):
            pytest.skip("objections workbook not fetched")
        assert list_sheets(p) == ["Flood_Risk", "Water_Quality"]
        flood = sum(1 for _ in table(p, min_header_cells=6, sheet="Flood_Risk"))
        both = sum(1 for _ in table(p, min_header_cells=6))
        assert flood == 23336
        assert both > flood, "unfiltered reading picks up the second sheet"
