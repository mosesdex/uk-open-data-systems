"""A place to keep an investigation.

Everything else here answers a question and forgets it. That is fine for a
dashboard and useless for the work this platform is actually for: someone
following a company across four systems over three weeks, who needs to come back
on Thursday to what they found on Monday, and eventually hand it to someone else.

An investigation is a named collection of identifiers, with a note against each
saying why it is in the collection. It is deliberately thin -- it stores what was
gathered and why, and nothing that could be recomputed. The figures stay in the
gold tables; the profile is assembled on demand. Copying them in would create a
second version of every number that could drift from the first, which is the
failure this platform exists to prevent.

Two rules make it evidence rather than a scrapbook:

  * every item carries the reason it was added and when, so a reader can tell a
    deliberate inclusion from a speculative one
  * removing an item marks it removed rather than deleting the row, because "we
    looked at this and ruled it out" is a finding and deleting it destroys the
    finding
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone

import duckdb

from . import ids

SCHEMA = """
CREATE SCHEMA IF NOT EXISTS workspace;

CREATE TABLE IF NOT EXISTS workspace.investigation (
  id          VARCHAR NOT NULL,
  name        VARCHAR NOT NULL,
  question    VARCHAR,
  created_at  TIMESTAMP NOT NULL,
  closed_at   TIMESTAMP,
  outcome     VARCHAR
);

-- Append-only in spirit: an item is marked removed, never deleted, so a ruled
-- out line of enquiry stays visible as one.
CREATE TABLE IF NOT EXISTS workspace.item (
  investigation_id VARCHAR NOT NULL,
  identifier       VARCHAR NOT NULL,
  kind             VARCHAR NOT NULL,
  namespace        VARCHAR NOT NULL,
  why              VARCHAR NOT NULL,
  found_via        VARCHAR,
  added_at         TIMESTAMP NOT NULL,
  removed_at       TIMESTAMP,
  removed_because  VARCHAR
);

CREATE TABLE IF NOT EXISTS workspace.note (
  investigation_id VARCHAR NOT NULL,
  noted_at         TIMESTAMP NOT NULL,
  text             VARCHAR NOT NULL
);
"""

_SLUG = re.compile(r"[^a-z0-9]+")


class InvestigationError(ValueError):
    """A malformed investigation operation."""


@dataclass
class Investigation:
    id: str
    name: str
    question: str | None
    created_at: datetime
    closed_at: datetime | None = None
    outcome: str | None = None
    items: list[dict] = field(default_factory=list)
    notes: list[dict] = field(default_factory=list)

    @property
    def open(self) -> bool:
        return self.closed_at is None

    @property
    def live_items(self) -> list[dict]:
        return [i for i in self.items if not i["removed_at"]]

    @property
    def ruled_out(self) -> list[dict]:
        return [i for i in self.items if i["removed_at"]]

    def by_kind(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for i in self.live_items:
            out[i["kind"]] = out.get(i["kind"], 0) + 1
        return out


def init(con: duckdb.DuckDBPyConnection) -> None:
    con.execute(SCHEMA)


def slug(name: str) -> str:
    s = _SLUG.sub("-", name.strip().lower()).strip("-")
    if not s:
        raise InvestigationError("an investigation needs a name with a letter in it")
    return s[:60]


def create(con: duckdb.DuckDBPyConnection, name: str,
           question: str | None = None) -> Investigation:
    init(con)
    key = slug(name)
    existing = con.execute(
        "SELECT count(*) FROM workspace.investigation WHERE id = ?", [key]).fetchone()[0]
    if existing:
        raise InvestigationError(f"an investigation called {key!r} already exists")
    now = datetime.now(timezone.utc)
    con.execute("INSERT INTO workspace.investigation VALUES (?,?,?,?,NULL,NULL)",
                [key, name.strip(), question, now])
    return Investigation(key, name.strip(), question, now)


def add(con: duckdb.DuckDBPyConnection, investigation: str, identifier: str,
        why: str, found_via: str | None = None) -> dict:
    """Put something in the collection, with the reason it is there.

    The reason is required. An item with no reason is indistinguishable from an
    accident three weeks later, and this collection is meant to be handed on.
    """
    init(con)
    ident = ids.parse(identifier)
    if not why or not why.strip():
        raise InvestigationError(
            "every item needs a reason; an unexplained item is not evidence")
    _require(con, investigation)
    already = con.execute(
        "SELECT count(*) FROM workspace.item "
        "WHERE investigation_id = ? AND identifier = ? AND removed_at IS NULL",
        [investigation, str(ident)]).fetchone()[0]
    if already:
        return {"added": False, "reason": "already in this investigation"}
    now = datetime.now(timezone.utc)
    con.execute("INSERT INTO workspace.item VALUES (?,?,?,?,?,?,?,NULL,NULL)",
                [investigation, str(ident), ident.kind, ident.namespace,
                 why.strip(), found_via, now])
    return {"added": True, "identifier": str(ident)}


def remove(con: duckdb.DuckDBPyConnection, investigation: str, identifier: str,
           because: str) -> dict:
    """Rule something out. The row stays; ruling out is a finding."""
    init(con)
    ident = ids.parse(identifier)
    if not because or not because.strip():
        raise InvestigationError(
            "ruling something out needs a reason -- that reason is the finding")
    n = con.execute(
        "UPDATE workspace.item SET removed_at = ?, removed_because = ? "
        "WHERE investigation_id = ? AND identifier = ? AND removed_at IS NULL",
        [datetime.now(timezone.utc), because.strip(), investigation, str(ident)])
    return {"removed": True, "identifier": str(ident)}


def note(con: duckdb.DuckDBPyConnection, investigation: str, text: str) -> None:
    init(con)
    _require(con, investigation)
    if not text.strip():
        raise InvestigationError("an empty note records nothing")
    con.execute("INSERT INTO workspace.note VALUES (?,?,?)",
                [investigation, datetime.now(timezone.utc), text.strip()])


def close(con: duckdb.DuckDBPyConnection, investigation: str,
          outcome: str) -> None:
    """Close it with a stated outcome, including 'nothing found'.

    A closed investigation with no outcome is the same problem as an item with
    no reason: it cannot be handed to anyone.
    """
    init(con)
    _require(con, investigation)
    if not outcome.strip():
        raise InvestigationError(
            "closing needs an outcome; 'nothing found' is a valid one and must be said")
    con.execute(
        "UPDATE workspace.investigation SET closed_at = ?, outcome = ? WHERE id = ?",
        [datetime.now(timezone.utc), outcome.strip(), investigation])


def _require(con: duckdb.DuckDBPyConnection, investigation: str) -> None:
    n = con.execute("SELECT count(*) FROM workspace.investigation WHERE id = ?",
                    [investigation]).fetchone()[0]
    if not n:
        raise InvestigationError(f"no investigation called {investigation!r}")


def _rows(con, sql, params=None) -> list[dict]:
    cur = con.execute(sql, params or [])
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def get(con: duckdb.DuckDBPyConnection, investigation: str) -> Investigation:
    init(con)
    head = _rows(con, "SELECT * FROM workspace.investigation WHERE id = ?",
                 [investigation])
    if not head:
        raise InvestigationError(f"no investigation called {investigation!r}")
    h = head[0]
    inv = Investigation(h["id"], h["name"], h["question"], h["created_at"],
                        h["closed_at"], h["outcome"])
    inv.items = _rows(con, "SELECT * FROM workspace.item WHERE investigation_id = ? "
                           "ORDER BY added_at", [investigation])
    inv.notes = _rows(con, "SELECT * FROM workspace.note WHERE investigation_id = ? "
                           "ORDER BY noted_at", [investigation])
    return inv


def listing(con: duckdb.DuckDBPyConnection) -> list[dict]:
    init(con)
    return _rows(con, """
        SELECT i.id, i.name, i.question, i.created_at, i.closed_at, i.outcome,
               count(t.identifier) FILTER (WHERE t.removed_at IS NULL) AS items,
               count(t.identifier) FILTER (WHERE t.removed_at IS NOT NULL) AS ruled_out
        FROM workspace.investigation i
        LEFT JOIN workspace.item t ON t.investigation_id = i.id
        GROUP BY ALL ORDER BY i.created_at DESC""")


def expand(con: duckdb.DuckDBPyConnection, investigation: str, seed: str, *,
           depth: int = 2, max_items: int = 25) -> dict:
    """Follow the graph out from a seed and add what it reaches.

    Every item added this way records the path that reached it, so a reader can
    see the difference between something a person put in and something a
    traversal found -- and can check the traversal.
    """
    from . import relationships as R
    init(con)
    _require(con, investigation)
    ids.parse(seed)
    n = R.neighbourhood(con, seed, depth=depth, max_nodes=max_items + 1)
    added, skipped = [], 0
    origin = {e.dst: e for e in n.edges}
    for identifier, node in n.nodes.items():
        if identifier == seed or len(added) >= max_items:
            continue
        edge = origin.get(identifier)
        via = (f"{edge.predicate} from {edge.src} ({edge.table})" if edge
               else "reached by traversal")
        out = add(con, investigation, identifier,
                  why=f"reached from {seed} at depth {node.depth}",
                  found_via=via)
        if out["added"]:
            added.append(identifier)
        else:
            skipped += 1
    return {"seed": seed, "added": len(added), "already_present": skipped,
            "truncated": n.truncated, "identifiers": added}
