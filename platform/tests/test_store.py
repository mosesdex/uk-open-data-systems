import uuid
from pathlib import Path

from groundtruth import store
from groundtruth.fetch import FetchResult


def _result(sid="gazette_insolvency", sha="a" * 64, ok=True):
    return FetchResult(sid, "2026-08-18T09:00:00+00:00", 200, ok, sha,
                       1234, "application/json", 42, "/tmp/x.json", "ok", "https://x")


def test_registry_is_mirrored_into_the_database(tmp_path: Path):
    con = store.connect(tmp_path / "t.duckdb")
    n = con.execute("SELECT count(*) FROM bronze.source_registry").fetchone()[0]
    assert n > 0
    con.close()


def test_fetch_log_is_append_only_and_records_failures(tmp_path: Path):
    con = store.connect(tmp_path / "t.duckdb")
    run = uuid.uuid4().hex[:12]
    store.record_fetch(con, run, _result())
    store.record_fetch(con, run, _result(sid="epc_domestic", sha=None, ok=False))
    rows = con.execute("SELECT source_id, ok FROM bronze.fetch_log ORDER BY source_id").fetchall()
    assert rows == [("epc_domestic", False), ("gazette_insolvency", True)]
    con.close()


def test_change_detection_spots_a_silently_replaced_file(tmp_path: Path):
    con = store.connect(tmp_path / "t.duckdb")
    run = uuid.uuid4().hex[:12]
    store.record_fetch(con, run, _result(sha="a" * 64))
    # first successful fetch: nothing to compare against
    assert store.changed_since_last(con, "gazette_insolvency", "a" * 64) is True
    store.record_fetch(con, run, _result(sha="a" * 64))
    assert store.changed_since_last(con, "gazette_insolvency", "a" * 64) is False
    store.record_fetch(con, run, _result(sha="b" * 64))
    assert store.changed_since_last(con, "gazette_insolvency", "b" * 64) is True
    con.close()


def test_status_shows_sources_never_fetched(tmp_path: Path):
    con = store.connect(tmp_path / "t.duckdb")
    rows = store.latest_status(con)
    notes = {r[0]: r[7] for r in rows}
    assert "never fetched" in notes["os_open_uprn"]
    assert notes["epc_domestic"].startswith("blocked:")
    con.close()


def test_migration_adds_a_column_to_an_existing_database(tmp_path):
    """A database created before a column existed must be upgraded, not wiped."""
    import duckdb as _d
    from groundtruth import store as _s

    db = tmp_path / "old.duckdb"
    con = _d.connect(str(db))
    # Recreate the pre-migration schema: fetch_log without final_url.
    con.execute("CREATE SCHEMA IF NOT EXISTS bronze")
    con.execute("""CREATE TABLE bronze.fetch_log (
        run_id VARCHAR, source_id VARCHAR, fetched_at TIMESTAMP,
        http_status INTEGER, ok BOOLEAN, sha256 VARCHAR, bytes_len BIGINT,
        content_type VARCHAR, elapsed_ms INTEGER, path VARCHAR, note VARCHAR)""")
    con.close()

    con = _s.connect(db)                      # should migrate rather than fail
    cols = {r[0] for r in con.execute(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_schema='bronze' AND table_name='fetch_log'").fetchall()}
    assert "final_url" in cols
    _s.record_fetch(con, "run", _result())    # and the insert must now work
    assert con.execute("SELECT count(*) FROM bronze.fetch_log").fetchone()[0] == 1
    assert _s.migrate(con) == []              # idempotent
    con.close()
