"""Where a number came from.

The platform could already answer this at the level of a *source*: the fetch log
records what was retrieved, when, with which status and which checksum. That is
enough to audit a run and not enough to audit a figure. "£4.7m of contributions
in this district" is assembled from particular rows, joined in a particular way,
at a particular confidence, and none of that survived into the published
payload.

This module records lineage at the level of the individual observation, so a
reader can click a number and be told which published record it came from, what
was done to it, what it was joined to, and how sure the platform is.

Three categories, kept apart on purpose:

  published  the publisher stated this value; the platform copied it
  derived    the platform computed it from published values, reproducibly
  modelled   the platform produced it through an assumption

Nothing in this repository currently emits ``modelled``, and the category exists
so that if anything ever does, it cannot be mistaken for the other two. A
platform whose headline principle is "nothing estimated" needs somewhere to put
an estimate the day it acquires one, or the principle quietly erodes instead of
being visibly broken.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone

import duckdb

PUBLISHED = "published"
DERIVED = "derived"
MODELLED = "modelled"
DERIVATIONS = (PUBLISHED, DERIVED, MODELLED)

SCHEMA = """
CREATE SCHEMA IF NOT EXISTS evidence;

-- One row per observation. Append-only, like the fetch log: an observation that
-- turned out to be wrong is superseded by a later run, not edited in place,
-- because the whole point is to be able to ask what the platform believed then.
CREATE TABLE IF NOT EXISTS evidence.observation (
  observation_id VARCHAR NOT NULL,
  run_id         VARCHAR NOT NULL,
  subject        VARCHAR NOT NULL,      -- a Groundtruth identifier
  field          VARCHAR NOT NULL,
  value_text     VARCHAR,
  value_num      DOUBLE,
  derivation     VARCHAR NOT NULL,      -- published | derived | modelled
  source_id      VARCHAR,
  source_url     VARCHAR,
  publisher      VARCHAR,
  dataset        VARCHAR,
  record_ref     VARCHAR,               -- the publisher's own row identifier
  published_at   VARCHAR,
  retrieved_at   TIMESTAMP,
  source_sha256  VARCHAR,
  transformations VARCHAR,              -- JSON array, in order applied
  joins          VARCHAR,               -- JSON array of {on, to, confidence}
  confidence     DOUBLE,
  coverage_n     BIGINT,                -- records the figure was computed over
  coverage_of    BIGINT,                -- records that could have contributed
  note           VARCHAR,
  recorded_at    TIMESTAMP NOT NULL
);
"""


class ProvenanceError(ValueError):
    """An observation that cannot be traced. Refused rather than stored: an
    untraceable row in a provenance table is worse than an absent one, because
    it looks like evidence."""


@dataclass
class Observation:
    """One traceable value.

    ``coverage_n`` and ``coverage_of`` are not decoration. The project rule is
    that coverage travels with every statistic, and a derived figure that does
    not state what it was computed over cannot honour it.
    """
    subject: str
    field: str
    derivation: str
    value_text: str | None = None
    value_num: float | None = None
    source_id: str | None = None
    source_url: str | None = None
    publisher: str | None = None
    dataset: str | None = None
    record_ref: str | None = None
    published_at: str | None = None
    retrieved_at: datetime | None = None
    source_sha256: str | None = None
    transformations: list[str] = field(default_factory=list)
    joins: list[dict] = field(default_factory=list)
    confidence: float | None = None
    coverage_n: int | None = None
    coverage_of: int | None = None
    note: str | None = None

    def validate(self) -> None:
        if self.derivation not in DERIVATIONS:
            raise ProvenanceError(
                f"derivation {self.derivation!r} is not one of {DERIVATIONS}")
        if not self.subject or not self.field:
            raise ProvenanceError("an observation needs a subject and a field")
        if self.derivation == PUBLISHED and not self.source_id:
            raise ProvenanceError(
                f"{self.subject}/{self.field} claims to be published but names no source")
        if self.derivation == DERIVED and not (self.transformations or self.joins):
            raise ProvenanceError(
                f"{self.subject}/{self.field} claims to be derived but records "
                "neither a transformation nor a join")
        if self.confidence is not None and not 0.0 <= self.confidence <= 1.0:
            raise ProvenanceError(f"confidence {self.confidence} is outside 0..1")

    @property
    def observation_id(self) -> str:
        """Stable within a run: same subject, field and run means same row."""
        from . import ids
        return ids.short(f"{self.subject}|{self.field}", length=20)

    @property
    def coverage_pct(self) -> float | None:
        if not self.coverage_of:
            return None
        return round(100.0 * (self.coverage_n or 0) / self.coverage_of, 2)


def init(con: duckdb.DuckDBPyConnection) -> None:
    con.execute(SCHEMA)


def record(con: duckdb.DuckDBPyConnection, run_id: str,
           observations: list[Observation]) -> int:
    """Store observations. Validates every one before storing any."""
    init(con)
    for o in observations:
        o.validate()
    now = datetime.now(timezone.utc)
    rows = [(
        o.observation_id, run_id, o.subject, o.field, o.value_text, o.value_num,
        o.derivation, o.source_id, o.source_url, o.publisher, o.dataset,
        o.record_ref, o.published_at, o.retrieved_at, o.source_sha256,
        json.dumps(o.transformations), json.dumps(o.joins), o.confidence,
        o.coverage_n, o.coverage_of, o.note, now,
    ) for o in observations]
    if rows:
        con.executemany(
            "INSERT INTO evidence.observation VALUES " + "(" + ",".join("?" * 22) + ")",
            rows)
    return len(rows)


def from_source(source, run_id: str = "", **kw) -> dict:
    """Fill the publisher half of an observation from a registry Source.

    Keeps callers from retyping the publisher and URL, which is how those
    fields drift out of agreement with the registry.
    """
    return dict(source_id=source.id, source_url=source.url,
                publisher=source.publisher, dataset=getattr(source, "name", None), **kw)


def explain(con: duckdb.DuckDBPyConnection, subject: str,
            field_name: str | None = None) -> list[dict]:
    """Why does this number say what it says?

    Returns the most recent observation per field for a subject, newest run
    first, with the transformation and join chain decoded.
    """
    init(con)
    sql = """
        WITH latest AS (
          SELECT *, row_number() OVER (
                      PARTITION BY subject, field ORDER BY recorded_at DESC) AS rn
          FROM evidence.observation WHERE subject = ?
        )
        SELECT * FROM latest WHERE rn = 1
    """
    params: list = [subject]
    if field_name:
        sql += " AND field = ?"
        params.append(field_name)
    sql += " ORDER BY field"
    cur = con.execute(sql, params)
    cols = [d[0] for d in cur.description]
    out = []
    for row in cur.fetchall():
        d = dict(zip(cols, row))
        d["transformations"] = json.loads(d.get("transformations") or "[]")
        d["joins"] = json.loads(d.get("joins") or "[]")
        if d.get("coverage_of"):
            d["coverage_pct"] = round(
                100.0 * (d.get("coverage_n") or 0) / d["coverage_of"], 2)
        d.pop("rn", None)
        out.append(d)
    return out


def summary(con: duckdb.DuckDBPyConnection) -> dict:
    """What the evidence layer holds, split by category.

    Exposed so the admin console can show the published/derived/modelled split
    rather than asserting the platform estimates nothing.
    """
    init(con)
    rows = con.execute("""
        SELECT derivation, count(*) AS n, count(DISTINCT subject) AS subjects
        FROM evidence.observation GROUP BY 1 ORDER BY 1""").fetchall()
    by = {r[0]: {"observations": r[1], "subjects": r[2]} for r in rows}
    total = sum(v["observations"] for v in by.values())
    untraced = con.execute("""
        SELECT count(*) FROM evidence.observation
        WHERE derivation = 'published' AND record_ref IS NULL""").fetchone()[0]
    return {
        "total": total,
        "by_derivation": by,
        "modelled": by.get(MODELLED, {}).get("observations", 0),
        "published_without_record_ref": untraced,
    }
