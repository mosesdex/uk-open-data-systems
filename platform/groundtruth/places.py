"""Resolving authority names so systems can be read side by side.

Nine of the thirteen systems publish something per local authority, and no two
publishers spell an authority the same way:

    Catchment   Gravesham
    Ledger      Arun District Council
    Highwater   London Borough of Croydon
    Sightline   East Lindsey District Council
    Bulwark     West Lindsey

This is the place-spine problem at authority scale, and it is why a citizen
cannot currently ask "what do all these systems say about where I live". The
answer exists; it is split across nine spellings of the same word.

Resolution here is deliberately conservative. Decorations that carry no
identifying information are stripped -- council, borough, district, "London
Borough of". Anything that survives must match a real ONS district exactly,
because attaching one authority's figures to another is worse than reporting
nothing for it. The unmatched share is published rather than hidden.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

import duckdb

# Removed because they never distinguish two authorities from each other.
DECORATIONS = (
    "london borough of", "royal borough of", "city and county of",
    "county borough council", "metropolitan borough council",
    "district council", "borough council", "county council", "city council",
    "unitary authority", "council of the", "the city of",
    "borough of", "district of", "city of", "council",
)
# Authorities that genuinely changed name or merged. Published so the mapping
# can be argued with rather than discovered.
ALIASES = {
    "kingston upon hull": "kingston upon hull, city of",
    "herefordshire": "herefordshire, county of",
    "bristol": "bristol, city of",
    "st albans": "st albans",
    "king s lynn and west norfolk": "kings lynn and west norfolk",
    "st edmundsbury": "west suffolk",
    "the vale of glamorgan": "vale of glamorgan",
}


@dataclass
class ResolutionReport:
    total: int = 0
    matched: int = 0
    unmatched: list[str] = field(default_factory=list)

    @property
    def rate(self) -> float:
        return 100 * self.matched / self.total if self.total else 0.0


def normalise_authority(raw: str | None) -> str:
    """Reduce an authority name to a comparable key."""
    if not raw:
        return ""
    s = str(raw).lower().strip()
    s = s.replace("&", "and")
    s = re.sub(r"[^a-z0-9\s,]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    changed = True
    while changed:
        changed = False
        for dec in DECORATIONS:
            if s.startswith(dec + " "):
                s = s[len(dec) + 1:].strip(); changed = True
            if s.endswith(" " + dec):
                s = s[: -(len(dec) + 1)].strip(); changed = True
    s = re.sub(r"\s+", " ", s).strip(" ,")
    return ALIASES.get(s, s)


def build_index(con: duckdb.DuckDBPyConnection) -> dict[str, tuple[str, str]]:
    """Map a normalised name to (lad_code, official name) from ONS boundaries."""
    idx: dict[str, tuple[str, str]] = {}
    for code, name in con.execute(
            "SELECT lad_code, lad_name FROM silver.lad").fetchall():
        key = normalise_authority(name)
        if key:
            idx[key] = (code, name)
    return idx


def resolve_many(index: dict, names) -> tuple[dict[str, str], ResolutionReport]:
    """Map each supplied name to a district code, reporting what did not match."""
    out: dict[str, str] = {}
    rep = ResolutionReport()
    for raw in names:
        if raw is None:
            continue
        rep.total += 1
        hit = index.get(normalise_authority(raw))
        if hit:
            out[raw] = hit[0]
            rep.matched += 1
        else:
            rep.unmatched.append(raw)
    return out, rep


# Which table and column each system publishes per authority.
SOURCES = {
    "catchment":  ("gold.catchment_district",  "lad_name"),
    "bulwark":    ("gold.bulwark_authority",   "local_authority"),
    "ledger":     ("gold.ledger_authority",    "authority"),
    "lastmile":   ("gold.lastmile_authority",  "lad_name"),
    "compass":    ("gold.compass_trend",       "la_name"),
    "plumbline":  ("gold.plumbline_authority", "lpa"),
    "highwater":  ("gold.highwater_authority", "lpa"),
    "sightline":  ("gold.sightline_authority", "lpa"),
    "bellwether": ("gold.bellwether_group",    "local_authority"),
}


def _table_exists(con, qualified: str) -> bool:
    schema, table = qualified.split(".")
    return con.execute(
        "SELECT count(*) FROM information_schema.tables "
        "WHERE table_schema=? AND table_name=?", [schema, table]).fetchone()[0] > 0


def place_view(con: duckdb.DuckDBPyConnection) -> dict:
    """Everything every system knows, keyed by district.

    The point of the platform, made answerable: one place, every system.
    """
    if not _table_exists(con, "silver.lad"):
        return {"places": {}, "resolution": {}, "districts": 0}

    index = build_index(con)
    places: dict[str, dict] = {}
    resolution: dict[str, dict] = {}

    for system, (table, col) in SOURCES.items():
        if not _table_exists(con, table):
            continue
        cur = con.execute(f"SELECT * FROM {table}")
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        names = {r.get(col) for r in rows if r.get(col)}
        mapping, rep = resolve_many(index, names)
        resolution[system] = {
            "names": rep.total, "matched": rep.matched,
            "rate": round(rep.rate, 1), "unmatched": sorted(rep.unmatched)[:12],
        }
        for r in rows:
            code = mapping.get(r.get(col))
            if not code:
                continue
            entry = places.setdefault(code, {})
            # Bellwether publishes one row per provider; keep the largest share.
            if system == "bellwether":
                cur_best = entry.get("bellwether")
                if not cur_best or (r.get("share_pct") or 0) > (cur_best.get("share_pct") or 0):
                    entry["bellwether"] = r
            elif system == "compass":
                if r.get("provision") == "Education, health and care plan":
                    entry["compass"] = r
            else:
                entry[system] = r

    for code, entry in places.items():
        entry["_systems"] = sorted(k for k in entry if not k.startswith("_"))

    return {"places": places, "resolution": resolution, "districts": len(places)}
