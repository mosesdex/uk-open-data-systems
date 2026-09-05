"""The evidence graph.

``chains.py`` already demonstrates that one fact sets off several systems, but
it does so as a set of hand-written traversals: each chain is a Python function
that knows which tables to read and in which order. That proves the argument and
does not generalise -- a fourteenth question needs a fourteenth function.

This module keeps the same discipline and removes the hand-writing. Edges are
declared against real tables; the traversal is generic. A question the author
never anticipated can be asked by walking the edges, and an edge whose table is
absent reports itself as unavailable rather than contributing an empty result
that looks like an answer.

The rules that make the graph trustworthy are the ones already enforced
elsewhere, restated as properties of an edge:

  * every edge names the table it came from, so a path can be audited
  * every edge carries a confidence, defaulting to the spine that produced it
  * an edge whose source table is missing is *unavailable*, never zero
"""
from __future__ import annotations

from dataclasses import dataclass, field

import duckdb

from . import ids


@dataclass(frozen=True)
class EdgeSpec:
    """A declared relationship, and the query that evidences it.

    ``sql`` must return ``src_key`` and ``dst_key`` columns, and may return a
    ``confidence`` column. Anything else is ignored, so a spec can select extra
    columns for debugging without changing behaviour.
    """
    predicate: str
    src_kind: str
    src_ns: str
    dst_kind: str
    dst_ns: str
    table: str
    sql: str
    confidence: float = 1.0
    note: str = ""


@dataclass
class Edge:
    src: str
    predicate: str
    dst: str
    confidence: float
    table: str

    def __str__(self) -> str:
        return f"{self.src} -[{self.predicate} {self.confidence:.2f}]-> {self.dst}"


@dataclass
class Path:
    start: str
    edges: list[Edge] = field(default_factory=list)

    @property
    def end(self) -> str:
        return self.edges[-1].dst if self.edges else self.start

    @property
    def confidence(self) -> float:
        """Confidence of a path is the product of its edges.

        Multiplying rather than taking the minimum is the conservative choice:
        three ninety-percent joins are not a ninety-percent answer, and a graph
        that reports them as one invites exactly the over-confidence the entity
        spine refuses at a single hop.
        """
        c = 1.0
        for e in self.edges:
            c *= e.confidence
        return c

    def __str__(self) -> str:
        return f"{self.start} " + " ".join(
            f"-[{e.predicate}]-> {e.dst}" for e in self.edges)


# Edges declared over tables this platform actually writes. Each one is a join
# the two spines made possible; that is the whole claim of the project, stated
# as data rather than prose.
REGISTRY: tuple[EdgeSpec, ...] = (
    EdgeSpec(
        predicate="agreed_under",
        src_kind="event", src_ns="contribution",
        dst_kind="event", dst_ns="agreement",
        table="silver.contribution",
        sql="""SELECT CAST(organisation_entity AS VARCHAR) || '/' || reference AS src_key,
                      CAST(organisation_entity AS VARCHAR) || '/' || agreement AS dst_key
               FROM silver.contribution
               WHERE agreement IS NOT NULL AND organisation_entity IS NOT NULL""",
        note="keys are authority-qualified: a bare planning reference is shared "
             "by 62% of contributions across different councils",
    ),
    EdgeSpec(
        predicate="collected_by",
        src_kind="event", src_ns="contribution",
        dst_kind="entity", dst_ns="organisation",
        table="silver.contribution",
        sql="""SELECT CAST(organisation_entity AS VARCHAR) || '/' || reference AS src_key,
                      CAST(organisation_entity AS VARCHAR) AS dst_key
               FROM silver.contribution WHERE organisation_entity IS NOT NULL""",
    ),
    EdgeSpec(
        predicate="settled_by",
        src_kind="event", src_ns="contribution",
        dst_kind="event", dst_ns="transaction",
        table="silver.contribution_transaction",
        sql="""SELECT CAST(organisation_entity AS VARCHAR) || '/' || contribution AS src_key,
                      CAST(organisation_entity AS VARCHAR) || '/' || reference AS dst_key
               FROM silver.contribution_transaction
               WHERE contribution IS NOT NULL AND organisation_entity IS NOT NULL""",
    ),
    EdgeSpec(
        predicate="evidenced_by",
        src_kind="event", src_ns="agreement",
        dst_kind="event", dst_ns="application",
        table="silver.developer_agreement",
        sql="""SELECT CAST(organisation_entity AS VARCHAR) || '/' || reference AS src_key,
                      CAST(organisation_entity AS VARCHAR) || '/' || planning_application AS dst_key
               FROM silver.developer_agreement
               WHERE planning_application IS NOT NULL AND organisation_entity IS NOT NULL""",
        note="carried by 99% of agreements; the only published route to a site",
    ),
    EdgeSpec(
        predicate="located_in",
        src_kind="event", src_ns="agreement",
        dst_kind="place", dst_ns="lad",
        table="silver.agreement_location",
        sql="""SELECT CAST(organisation_entity AS VARCHAR) || '/' || agreement AS src_key,
                      lad AS dst_key, confidence
               FROM silver.agreement_location
               WHERE lad IS NOT NULL AND organisation_entity IS NOT NULL""",
        note="closes for 2 of the 66 authorities that record contributions",
    ),
    EdgeSpec(
        predicate="sits_in",
        src_kind="place", src_ns="postcode",
        dst_kind="place", dst_ns="lad",
        table="silver.place_postcode",
        sql="""SELECT postcode AS src_key, lad_code AS dst_key
               FROM silver.place_postcode WHERE lad_code IS NOT NULL""",
    ),
)


def _table_exists(con: duckdb.DuckDBPyConnection, qualified: str) -> bool:
    schema, _, table = qualified.partition(".")
    return con.execute(
        "SELECT count(*) FROM information_schema.tables "
        "WHERE table_schema = ? AND table_name = ?", [schema, table]
    ).fetchone()[0] > 0


def available(con: duckdb.DuckDBPyConnection) -> list[dict]:
    """Which declared edges can currently be walked, and which cannot.

    An absent table is reported, not hidden. A graph that silently drops the
    edges it cannot serve answers fewer questions while looking complete.
    """
    out = []
    for spec in REGISTRY:
        ok = _table_exists(con, spec.table)
        n, err = None, None
        if ok:
            try:
                n = con.execute(f"SELECT count(*) FROM ({spec.sql})").fetchone()[0]
            except duckdb.Error as exc:
                # A spec that no longer binds -- a publisher renamed a column, or
                # the declaration was wrong -- is a recorded failure like any
                # other. Raising here would take the whole graph down because one
                # edge is stale; hiding it would leave a silently missing edge.
                ok, err = False, str(exc).splitlines()[0]
        out.append({"predicate": spec.predicate, "table": spec.table,
                    "available": ok, "edges": n, "error": err,
                    "from": f"{spec.src_kind}:{spec.src_ns}",
                    "to": f"{spec.dst_kind}:{spec.dst_ns}",
                    "note": spec.note})
    return out


def _specs_from(kind: str, namespace: str) -> list[EdgeSpec]:
    return [s for s in REGISTRY if s.src_kind == kind and s.src_ns == namespace]


def neighbours(con: duckdb.DuckDBPyConnection, node: str,
               predicate: str | None = None, limit: int = 200) -> list[Edge]:
    """One hop out from a node."""
    ident = ids.parse(node)
    edges: list[Edge] = []
    for spec in _specs_from(ident.kind, ident.namespace):
        if predicate and spec.predicate != predicate:
            continue
        if not _table_exists(con, spec.table):
            continue
        try:
            cur = con.execute(
                f"SELECT * FROM ({spec.sql}) WHERE src_key = ? LIMIT {int(limit)}",
                [ident.key])
        except duckdb.Error:
            continue                       # stale spec; reported by available()
        cols = [d[0] for d in cur.description]
        for row in cur.fetchall():
            r = dict(zip(cols, row))
            dst_key = r.get("dst_key")
            if dst_key is None:
                continue
            try:
                dst = ids.mint(spec.dst_kind, spec.dst_ns, dst_key)
            except ids.IdentifierError:
                # A key the publisher wrote in a shape we cannot quote is a
                # recorded gap, not an edge. Skipping silently would inflate
                # coverage; the count difference is visible via available().
                continue
            conf = r.get("confidence")
            edges.append(Edge(str(ident), spec.predicate, str(dst),
                              float(conf) if conf is not None else spec.confidence,
                              spec.table))
    return edges


def walk(con: duckdb.DuckDBPyConnection, start: str, *,
         max_depth: int = 4, target_kind: str | None = None,
         target_ns: str | None = None, limit: int = 50) -> list[Path]:
    """Breadth-first traversal from a node.

    Breadth-first so the shortest evidential path is found first: a shorter
    path multiplies fewer confidences and is easier for a reader to check.
    """
    ids.parse(start)                      # refuse a malformed start outright
    seen = {start}
    frontier = [Path(start)]
    found: list[Path] = []
    for _ in range(max_depth):
        nxt: list[Path] = []
        for path in frontier:
            for edge in neighbours(con, path.end):
                if edge.dst in seen:
                    continue
                seen.add(edge.dst)
                extended = Path(path.start, path.edges + [edge])
                nxt.append(extended)
                if target_kind:
                    d = ids.parse(edge.dst)
                    if d.kind == target_kind and (not target_ns or d.namespace == target_ns):
                        found.append(extended)
                        if len(found) >= limit:
                            return found
                else:
                    found.append(extended)
                    if len(found) >= limit:
                        return found
        if not nxt:
            break
        frontier = nxt
    return found


def stats(con: duckdb.DuckDBPyConnection) -> dict:
    """Size of the graph, and how much of it is currently walkable."""
    rows = available(con)
    live = [r for r in rows if r["available"]]
    return {
        "declared_edges": len(rows),
        "available_edges": len(live),
        "unavailable": [r["predicate"] for r in rows if not r["available"]],
        "broken": {r["predicate"]: r["error"] for r in rows if r.get("error")},
        "total_relationships": sum(r["edges"] or 0 for r in live),
        "by_predicate": {r["predicate"]: r["edges"] for r in live},
    }
