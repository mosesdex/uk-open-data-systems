"""Exploring the graph, rather than querying it.

``graph.py`` answers "what is connected to this", one hop at a time, in
identifiers. That is the right primitive and the wrong interface for a person:
nobody investigating a company wants to read ``gt:entity:company:02571516`` and
hold four hops in their head.

This module expands a neighbourhood, labels every node with the name its
publisher gave it, and renders the result as something a person can look at. It
adds no edges of its own -- an edge that appears here appears in the graph, and
therefore in a table, and therefore in a source.

The one thing it deliberately does not do is lay out a picture that implies more
than the data supports. Node labels come from published names; a node whose name
is not published keeps its identifier rather than being given a plausible one.
"""
from __future__ import annotations

import html
from dataclasses import dataclass, field

import duckdb

from . import graph as G
from . import ids

# Where a label for each kind of node is published. First hit wins; a miss
# leaves the identifier in place, which is honest and occasionally informative.
_LABELS: dict[tuple[str, str], tuple[tuple[str, str, str], ...]] = {
    ("entity", "company"): (
        ("gold.entity", "company_number", "name"),
        ("silver.company", "company_number", "name"),
    ),
    ("entity", "organisation"): (
        ("silver.planning_authority", "entity", "name"),
    ),
    ("place", "lad"): (
        ("silver.lad", "lad_code", "lad_name"),
        ("gold.catchment_district", "lad_code", "lad_name"),
    ),
}


@dataclass
class Node:
    identifier: str
    kind: str
    namespace: str
    label: str
    depth: int

    @property
    def labelled(self) -> bool:
        return self.label != self.identifier


@dataclass
class Neighbourhood:
    centre: str
    nodes: dict[str, Node] = field(default_factory=dict)
    edges: list[G.Edge] = field(default_factory=list)
    truncated: bool = False

    @property
    def size(self) -> tuple[int, int]:
        return len(self.nodes), len(self.edges)

    def as_dict(self) -> dict:
        return {
            "centre": self.centre,
            "nodes": [{"id": n.identifier, "kind": n.kind, "namespace": n.namespace,
                       "label": n.label, "depth": n.depth, "labelled": n.labelled}
                      for n in self.nodes.values()],
            "edges": [{"src": e.src, "predicate": e.predicate, "dst": e.dst,
                       "confidence": e.confidence, "table": e.table}
                      for e in self.edges],
            "truncated": self.truncated,
        }


def _exists(con: duckdb.DuckDBPyConnection, qualified: str) -> bool:
    schema, _, table = qualified.partition(".")
    return con.execute(
        "SELECT count(*) FROM information_schema.tables "
        "WHERE table_schema = ? AND table_name = ?", [schema, table]
    ).fetchone()[0] > 0


def label(con: duckdb.DuckDBPyConnection, identifier: str) -> str:
    """The published name for a node, or its identifier if none is published."""
    try:
        ident = ids.parse(identifier)
    except ids.IdentifierError:
        return identifier
    for table, key_col, name_col in _LABELS.get((ident.kind, ident.namespace), ()):
        if not _exists(con, table):
            continue
        try:
            row = con.execute(
                f"SELECT {name_col} FROM {table} WHERE CAST({key_col} AS VARCHAR) = ? "
                f"AND {name_col} IS NOT NULL LIMIT 1", [ident.key]).fetchone()
        except duckdb.Error:
            continue
        if row and row[0]:
            return str(row[0])
    return identifier


def neighbourhood(con: duckdb.DuckDBPyConnection, centre: str, *,
                  depth: int = 2, max_nodes: int = 60,
                  per_node: int = 12) -> Neighbourhood:
    """Expand outwards from a node, breadth first.

    ``per_node`` caps how many edges any single node contributes. Without it one
    hub -- a large authority, a national supplier -- fills the whole budget and
    the result stops being a neighbourhood and becomes a list of that hub's
    children.
    """
    ids.parse(centre)
    n = Neighbourhood(centre=centre)
    n.nodes[centre] = Node(centre, *_kind_ns(centre), label(con, centre), 0)
    frontier = [centre]
    for d in range(1, depth + 1):
        nxt: list[str] = []
        for node in frontier:
            for edge in G.neighbours(con, node, limit=per_node)[:per_node]:
                if len(n.nodes) >= max_nodes:
                    n.truncated = True
                    return n
                n.edges.append(edge)
                if edge.dst not in n.nodes:
                    n.nodes[edge.dst] = Node(edge.dst, *_kind_ns(edge.dst),
                                             label(con, edge.dst), d)
                    nxt.append(edge.dst)
        if not nxt:
            break
        frontier = nxt
    return n


def _kind_ns(identifier: str) -> tuple[str, str]:
    try:
        i = ids.parse(identifier)
        return i.kind, i.namespace
    except ids.IdentifierError:
        return "unknown", "unknown"


def between(con: duckdb.DuckDBPyConnection, a: str, b: str, *,
            max_depth: int = 4) -> list[G.Path]:
    """How, if at all, two things are connected.

    Returns every path found up to ``max_depth``, shortest first, because the
    shortest path multiplies fewest confidences and is the one a reader can
    check by hand.
    """
    ids.parse(a)
    ids.parse(b)
    paths = G.walk(con, a, max_depth=max_depth, limit=500)
    hits = [p for p in paths if p.end == b]
    hits.sort(key=lambda p: (len(p.edges), -p.confidence))
    return hits


_MERMAID_SAFE = str.maketrans({'"': "'", "\n": " ", "[": "(", "]": ")"})


def to_mermaid(n: Neighbourhood) -> str:
    """Render as a Mermaid graph.

    Mermaid rather than an image: it is text, so it survives in a terminal, a
    markdown export and an evidence bundle without a rendering dependency, and
    it can be diffed.
    """
    alias = {ident: f"n{i}" for i, ident in enumerate(n.nodes)}
    lines = ["graph LR"]
    for ident, node in n.nodes.items():
        text = node.label.translate(_MERMAID_SAFE)[:48]
        shape = ("([%s])" if node.kind == "place" else
                 "[%s]" if node.kind == "entity" else "(%s)")
        lines.append(f"  {alias[ident]}{shape % text}")
    for e in n.edges:
        if e.src in alias and e.dst in alias:
            lines.append(f"  {alias[e.src]} -->|{e.predicate}| {alias[e.dst]}")
    return "\n".join(lines)


def to_text(n: Neighbourhood) -> str:
    """A plain tree, for a terminal."""
    by_src: dict[str, list[G.Edge]] = {}
    for e in n.edges:
        by_src.setdefault(e.src, []).append(e)
    out: list[str] = []
    seen: set[str] = set()

    def walk(node: str, prefix: str, last: bool, depth: int) -> None:
        if node in seen or depth > 6:
            return
        seen.add(node)
        label_ = n.nodes[node].label if node in n.nodes else node
        connector = "" if not prefix else ("`- " if last else "|- ")
        out.append(f"{prefix}{connector}{label_}")
        kids = by_src.get(node, [])
        child_prefix = prefix + ("" if not prefix else ("   " if last else "|  "))
        for i, e in enumerate(kids):
            out.append(f"{child_prefix}|  [{e.predicate}]")
            walk(e.dst, child_prefix, i == len(kids) - 1, depth + 1)

    walk(n.centre, "", True, 0)
    if n.truncated:
        out.append("  ... truncated: node budget reached")
    return "\n".join(out)
