"""Storage.

Three layers, in the usual order:

  bronze -- exactly what the publisher served, plus how and when it was fetched
  silver -- validated, conformed, identifiers attached
  gold   -- what each system publishes

DuckDB is a single file. The whole UK open-data corpus for this platform is in
the low hundreds of gigabytes, so it does not need a cluster, and the research
found no reason to pretend otherwise.
"""
from __future__ import annotations

from pathlib import Path

import duckdb

from .sources import REGISTRY

SCHEMA = """
CREATE SCHEMA IF NOT EXISTS bronze;
CREATE SCHEMA IF NOT EXISTS silver;
CREATE SCHEMA IF NOT EXISTS gold;

-- The registry, materialised so a run can be audited without reading the code.
CREATE TABLE IF NOT EXISTS bronze.source_registry (
  id           VARCHAR PRIMARY KEY,
  name         VARCHAR NOT NULL,
  publisher    VARCHAR NOT NULL,
  url          VARCHAR NOT NULL,
  fmt          VARCHAR NOT NULL,
  role         VARCHAR NOT NULL,
  licence      VARCHAR NOT NULL,
  cadence      VARCHAR NOT NULL,
  systems      VARCHAR,
  notes        VARCHAR,
  blocked      VARCHAR
);

-- Append-only. A failed fetch is a recorded fact, not an absence: coverage
-- figures are only trustworthy if you can see what could not be reached.
CREATE TABLE IF NOT EXISTS bronze.fetch_log (
  run_id       VARCHAR NOT NULL,
  source_id    VARCHAR NOT NULL,
  fetched_at   TIMESTAMP NOT NULL,
  http_status  INTEGER NOT NULL,
  ok           BOOLEAN NOT NULL,
  sha256       VARCHAR,
  bytes_len    BIGINT NOT NULL,
  content_type VARCHAR,
  elapsed_ms   INTEGER,
  path         VARCHAR,
  note         VARCHAR,
  final_url    VARCHAR
);
"""


# Columns added after the first release. CREATE TABLE IF NOT EXISTS will not add
# a column to a database that already exists, so they are applied explicitly.
MIGRATIONS: tuple[tuple[str, str, str], ...] = (
    ("bronze", "fetch_log", "final_url VARCHAR"),
)


def migrate(con: duckdb.DuckDBPyConnection) -> list[str]:
    """Bring an existing database up to the current schema. Idempotent."""
    applied = []
    for schema, table, coldef in MIGRATIONS:
        column = coldef.split()[0]
        existing = {
            r[0] for r in con.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = ? AND table_name = ?", [schema, table]
            ).fetchall()
        }
        if column not in existing:
            con.execute(f"ALTER TABLE {schema}.{table} ADD COLUMN {coldef}")
            applied.append(f"{schema}.{table}.{column}")
    return applied


def connect(db_path: Path | str) -> duckdb.DuckDBPyConnection:
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(db_path))
    con.execute(SCHEMA)
    migrate(con)
    sync_registry(con)
    return con


def sync_registry(con: duckdb.DuckDBPyConnection) -> int:
    """Mirror the code registry into the database, so the two cannot drift."""
    con.execute("DELETE FROM bronze.source_registry")
    con.executemany(
        """INSERT INTO bronze.source_registry
           (id,name,publisher,url,fmt,role,licence,cadence,systems,notes,blocked)
           VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        [(s.id, s.name, s.publisher, s.url, s.fmt, s.role, s.licence, s.cadence,
          ",".join(s.systems), s.notes, s.blocked) for s in REGISTRY],
    )
    return len(REGISTRY)


def record_fetch(con: duckdb.DuckDBPyConnection, run_id: str, result) -> None:
    con.execute(
        """INSERT INTO bronze.fetch_log
           (run_id,source_id,fetched_at,http_status,ok,sha256,bytes_len,
            content_type,elapsed_ms,path,note,final_url)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
        [run_id, result.source_id, result.fetched_at, result.http_status,
         result.ok, result.sha256, result.bytes_len, result.content_type,
         result.elapsed_ms, result.path, result.note, result.final_url],
    )


def latest_status(con: duckdb.DuckDBPyConnection):
    """Most recent outcome per source, joined to what the registry expects."""
    return con.execute("""
        WITH last AS (
          SELECT *, row_number() OVER (PARTITION BY source_id ORDER BY fetched_at DESC) rn
          FROM bronze.fetch_log
        )
        SELECT r.id, r.role, r.publisher,
               COALESCE(l.http_status, -1) AS http_status,
               COALESCE(l.ok, FALSE)       AS ok,
               l.bytes_len, l.fetched_at,
               COALESCE(l.note, CASE WHEN r.blocked IS NOT NULL
                                     THEN 'blocked: ' || r.blocked
                                     ELSE 'never fetched' END) AS note
        FROM bronze.source_registry r
        LEFT JOIN last l ON l.source_id = r.id AND l.rn = 1
        ORDER BY r.role, r.id
    """).fetchall()


def changed_since_last(con: duckdb.DuckDBPyConnection, source_id: str, sha256: str) -> bool:
    """True when this content differs from the previous successful fetch.

    Used to skip expensive downstream work, and to notice a publisher silently
    replacing a file -- which the research found happens without a changelog.
    """
    row = con.execute("""
        SELECT sha256 FROM bronze.fetch_log
        WHERE source_id = ? AND ok AND sha256 IS NOT NULL
        ORDER BY fetched_at DESC LIMIT 1 OFFSET 1
    """, [source_id]).fetchone()
    return row is None or row[0] != sha256
