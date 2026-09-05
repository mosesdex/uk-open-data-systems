"""Snapshots and change detection.

The rule under test: history is recorded as manifests, not copies, and the
change that matters most -- a publisher rewriting a file in place without
changing its row count -- is detected rather than missed.
"""
import pytest

from groundtruth import store, temporal as T


@pytest.fixture
def con(tmp_path):
    c = store.connect(tmp_path / "db")
    c.execute("CREATE SCHEMA IF NOT EXISTS silver")
    c.execute("CREATE TABLE silver.thing (id BIGINT, name VARCHAR)")
    c.execute("INSERT INTO silver.thing VALUES (1,'a'),(2,'b')")
    yield c
    c.close()


class TestSnapshot:
    def test_records_shape_without_copying_rows(self, con):
        s = T.snapshot(con, label="first")
        assert s["tables"] >= 1 and s["rows"] >= 2
        held = con.execute(
            "SELECT row_count, column_count FROM history.manifest "
            "WHERE table_name = 'thing'").fetchone()
        assert held == (2, 2)

    def test_snapshots_are_listed_newest_first(self, con):
        a = T.snapshot(con, label="first")["snapshot_id"]
        con.execute("INSERT INTO silver.thing VALUES (3,'c')")
        b = T.snapshot(con, label="second")["snapshot_id"]
        listed = [s["snapshot_id"] for s in T.snapshots(con)]
        if a != b:                       # same-second snapshots share an id
            assert listed[0] == b


class TestDiff:
    def test_row_movement_is_reported(self, con):
        a = T.snapshot(con)["snapshot_id"]
        con.execute("INSERT INTO silver.thing VALUES (3,'c')")
        con.execute("UPDATE history.manifest SET snapshot_id = ? WHERE snapshot_id = ?",
                    ["S1", a])
        b = T.snapshot(con)["snapshot_id"]
        d = T.diff(con, "S1", b)
        moved = {r["table"]: r for r in d["row_changes"]}
        assert moved["silver.thing"]["delta"] == 1

    def test_in_place_rewrite_is_caught_when_the_row_count_does_not_move(self, con):
        """The case the fetch log found happens: a publisher replaces a file
        without a changelog. Row counts alone would call this no change."""
        a = T.snapshot(con)["snapshot_id"]
        con.execute("UPDATE history.manifest SET snapshot_id = ? WHERE snapshot_id = ?",
                    ["S1", a])
        con.execute("UPDATE silver.thing SET name = 'CHANGED' WHERE id = 1")
        b = T.snapshot(con)["snapshot_id"]
        d = T.diff(con, "S1", b)
        assert d["row_changes"] == []
        assert "silver.thing" in d["rewritten_in_place"]

    def test_schema_change_is_reported_separately(self, con):
        a = T.snapshot(con)["snapshot_id"]
        con.execute("UPDATE history.manifest SET snapshot_id = ? WHERE snapshot_id = ?",
                    ["S1", a])
        con.execute("ALTER TABLE silver.thing ADD COLUMN extra VARCHAR")
        b = T.snapshot(con)["snapshot_id"]
        d = T.diff(con, "S1", b)
        assert d["schema_changes"][0]["added"] == ["extra"]

    def test_unknown_snapshot_is_an_error_not_an_empty_diff(self, con):
        T.snapshot(con)
        with pytest.raises(ValueError):
            T.diff(con, "nope", "also-nope")


class TestAsOf:
    def test_works_before_any_snapshot_was_taken(self, con):
        # Reads the append-only records, so it answers for any instant.
        out = T.as_of(con, "2099-01-01")
        assert out["nearest_snapshot"] is None
        assert out["observations"] == 0
