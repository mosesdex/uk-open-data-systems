"""What the platform knew, and when.

Government data is not static, and the interesting questions are usually about
change: a company that had no contracts in 2021 and forty by 2024, a site that
was approved before the flood map moved. Answering those needs the platform to
remember its own past, not just the publisher's latest file.

The obvious implementation -- copy the database each run -- is wrong here. The
corpus is four gigabytes and growing, most tables are unchanged between runs,
and a snapshot regime that costs four gigabytes a day will be switched off
within a fortnight and then quietly not exist.

So this stores *manifests*, not copies. Two append-only tables already record
history without anyone having planned it that way: ``bronze.fetch_log`` stamps
every retrieval with a checksum, and ``evidence.observation`` stamps every
figure with the run that produced it. A manifest adds the third piece -- the
shape of each table at a point in time -- and the three together answer "what
did Groundtruth hold on this date" without duplicating a byte.

What this deliberately does not do is reconstruct a row as it was. That needs
per-row versioning, which is a real cost and should be paid per table, on
purpose, for tables where it earns its keep -- not switched on globally because
it sounded thorough.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone

import duckdb

SCHEMA = """
CREATE SCHEMA IF NOT EXISTS history;

-- One row per table per snapshot. Append-only.
CREATE TABLE IF NOT EXISTS history.manifest (
  snapshot_id  VARCHAR NOT NULL,
  taken_at     TIMESTAMP NOT NULL,
  label        VARCHAR,
  code_version VARCHAR,
  schema_name  VARCHAR NOT NULL,
  table_name   VARCHAR NOT NULL,
  row_count    BIGINT NOT NULL,
  column_count INTEGER NOT NULL,
  columns      VARCHAR NOT NULL,      -- JSON, ordered: detects a schema change
  content_hash VARCHAR                -- NULL when the table was too large to hash
);
"""

# Above this many rows a full content hash is skipped: hashing a 1.4m-row table
# on every snapshot costs more than the change signal is worth, and the row
# count plus column list still catches the changes that matter operationally.
HASH_ROW_LIMIT = 500_000


@dataclass(frozen=True)
class TableState:
    schema: str
    table: str
    rows: int
    columns: tuple[str, ...]
    content_hash: str | None

    @property
    def qualified(self) -> str:
        return f"{self.schema}.{self.table}"


def init(con: duckdb.DuckDBPyConnection) -> None:
    con.execute(SCHEMA)


def _tables(con: duckdb.DuckDBPyConnection,
            schemas: tuple[str, ...]) -> list[tuple[str, str]]:
    marks = ",".join("?" * len(schemas))
    return [(r[0], r[1]) for r in con.execute(
        f"""SELECT table_schema, table_name FROM information_schema.tables
            WHERE table_schema IN ({marks}) ORDER BY 1, 2""", list(schemas)).fetchall()]


def _state(con: duckdb.DuckDBPyConnection, schema: str, table: str) -> TableState:
    cols = tuple(r[0] for r in con.execute(
        """SELECT column_name FROM information_schema.columns
           WHERE table_schema = ? AND table_name = ? ORDER BY ordinal_position""",
        [schema, table]).fetchall())
    rows = con.execute(f'SELECT count(*) FROM "{schema}"."{table}"').fetchone()[0]
    digest = None
    if rows <= HASH_ROW_LIMIT and cols:
        # Order-independent: XOR-free but sorted, so a rewrite that changes row
        # order without changing content does not read as a change.
        h = hashlib.blake2b(digest_size=16)
        cur = con.execute(
            f'SELECT * FROM "{schema}"."{table}" ORDER BY ALL')
        for row in cur.fetchall():
            h.update(repr(row).encode("utf-8", "replace"))
        digest = h.hexdigest()
    return TableState(schema, table, rows, cols, digest)


def snapshot(con: duckdb.DuckDBPyConnection, label: str = "",
             code_version: str = "",
             schemas: tuple[str, ...] = ("silver", "gold")) -> dict:
    """Record the shape of the platform now."""
    init(con)
    taken = datetime.now(timezone.utc)
    snapshot_id = taken.strftime("%Y%m%dT%H%M%SZ")
    rows = []
    for schema, table in _tables(con, schemas):
        s = _state(con, schema, table)
        rows.append((snapshot_id, taken, label or None, code_version or None,
                     s.schema, s.table, s.rows, len(s.columns),
                     json.dumps(list(s.columns)), s.content_hash))
    if rows:
        con.executemany(
            "INSERT INTO history.manifest VALUES (?,?,?,?,?,?,?,?,?,?)", rows)
    return {"snapshot_id": snapshot_id, "taken_at": taken.isoformat(),
            "tables": len(rows), "rows": sum(r[6] for r in rows)}


def snapshots(con: duckdb.DuckDBPyConnection, limit: int = 20) -> list[dict]:
    init(con)
    cur = con.execute("""
        SELECT snapshot_id, min(taken_at) AS taken_at, any_value(label) AS label,
               any_value(code_version) AS code_version,
               count(*) AS tables, sum(row_count) AS rows
        FROM history.manifest GROUP BY snapshot_id
        ORDER BY taken_at DESC LIMIT ?""", [limit])
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def diff(con: duckdb.DuckDBPyConnection, before: str, after: str) -> dict:
    """What changed between two snapshots.

    Reports added and removed tables, row-count movement, schema changes and
    content changes separately. A table whose rows are unchanged but whose
    content hash moved is the interesting case -- that is a publisher
    rewriting history in place, which the fetch log found happens.
    """
    init(con)
    def load(sid):
        return {(r[0], r[1]): {"rows": r[2], "columns": json.loads(r[3]),
                               "hash": r[4]}
                for r in con.execute(
            """SELECT schema_name, table_name, row_count, columns, content_hash
               FROM history.manifest WHERE snapshot_id = ?""", [sid]).fetchall()}

    a, b = load(before), load(after)
    if not a:
        raise ValueError(f"no such snapshot: {before}")
    if not b:
        raise ValueError(f"no such snapshot: {after}")

    added = sorted(f"{s}.{t}" for s, t in b.keys() - a.keys())
    removed = sorted(f"{s}.{t}" for s, t in a.keys() - b.keys())
    row_changes, schema_changes, silent = [], [], []
    for key in sorted(a.keys() & b.keys()):
        name = f"{key[0]}.{key[1]}"
        x, y = a[key], b[key]
        if x["rows"] != y["rows"]:
            row_changes.append({"table": name, "before": x["rows"],
                                "after": y["rows"], "delta": y["rows"] - x["rows"]})
        if x["columns"] != y["columns"]:
            schema_changes.append({
                "table": name,
                "added": [c for c in y["columns"] if c not in x["columns"]],
                "removed": [c for c in x["columns"] if c not in y["columns"]]})
        if (x["rows"] == y["rows"] and x["hash"] and y["hash"]
                and x["hash"] != y["hash"]):
            silent.append(name)
    return {"before": before, "after": after,
            "tables_added": added, "tables_removed": removed,
            "row_changes": row_changes, "schema_changes": schema_changes,
            "rewritten_in_place": silent}


def as_of(con: duckdb.DuckDBPyConnection, when: str) -> dict:
    """What the platform held at a moment, from the append-only records.

    Reads the fetch log and the evidence table rather than any snapshot, so it
    works for any instant, including before the first snapshot was taken.
    """
    init(con)
    fetched = con.execute("""
        SELECT count(DISTINCT source_id), max(fetched_at)
        FROM bronze.fetch_log WHERE ok AND fetched_at <= ?""", [when]).fetchone()
    has_obs = con.execute(
        """SELECT count(*) FROM information_schema.tables
           WHERE table_schema='evidence' AND table_name='observation'""").fetchone()[0]
    observations = 0
    if has_obs:
        observations = con.execute(
            "SELECT count(*) FROM evidence.observation WHERE recorded_at <= ?",
            [when]).fetchone()[0]
    snap = con.execute("""
        SELECT snapshot_id FROM history.manifest WHERE taken_at <= ?
        ORDER BY taken_at DESC LIMIT 1""", [when]).fetchone()
    return {"as_of": when,
            "sources_fetched": fetched[0] or 0,
            "latest_fetch": fetched[1],
            "observations": observations,
            "nearest_snapshot": snap[0] if snap else None}
