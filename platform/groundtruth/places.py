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

# District codes ONS reissued after the May 2024 boundaries this platform draws
# its map from. The postcode register and BDUK's premises file already carry
# the new codes; the boundaries, the county lookup and every system that names
# its authority carry the old. Left alone, Barnsley and Sheffield each became
# two districts -- one with a name and a polygon, the other holding every
# postcode-placed figure -- and the two never met. Mapped back to the boundary
# vintage because that is what the map is drawn from. Checked against the
# schools themselves: GIAS names all 191 schools the spine had placed in
# E08000039 as Sheffield, and all 97 in E08000038 as Barnsley.
CODE_SUCCESSION = {
    "E08000038": "E08000016",   # Barnsley
    "E08000039": "E08000019",   # Sheffield
}


def boundary_code_sql(expr: str) -> str:
    """SQL mapping a district-code expression to the boundary vintage."""
    whens = " ".join(f"WHEN '{new}' THEN '{old}'" for new, old in CODE_SUCCESSION.items())
    return f"(CASE {expr} {whens} ELSE {expr} END)"


# Care, special educational needs and school place planning are duties of the
# upper-tier council. For most districts that is the district's own council; in
# two-tier areas it is the county. ONS's lookup also groups metropolitan
# boroughs into metropolitan counties (E11) and London boroughs into Inner and
# Outer London (E13), but no council holds these duties at either level, so
# only the E10 county councils are used.
UPPER_TIER_PREFIX = "E10"


def districts_loaded(con: duckdb.DuckDBPyConnection) -> bool:
    """Whether there are districts to hand figures to at all."""
    return _table_exists(con, "silver.lad")


def upper_tier_sql(con: duckdb.DuckDBPyConnection) -> str:
    """One row per district, naming the authority whose figures describe it.

    ``figure_for`` is 'district' where the district's own council publishes the
    figure and 'county' where it is the county council's, shared by every
    district in the county and never divided between them, because nothing
    published says how. Without the lookup every district stands for itself,
    so a two-tier district matches nothing rather than being handed a figure
    that is not its own.
    """
    if not _table_exists(con, "silver.lad_county"):
        return ("SELECT lad_code, lad_name, lad_code AS authority_code, "
                "lad_name AS authority_name, 'district' AS figure_for FROM silver.lad")
    return f"""
        SELECT l.lad_code, l.lad_name,
               COALESCE(c.county_code, l.lad_code) AS authority_code,
               COALESCE(c.county_name, l.lad_name) AS authority_name,
               CASE WHEN c.county_code IS NULL THEN 'district' ELSE 'county' END AS figure_for
        FROM silver.lad l
        LEFT JOIN silver.lad_county c
          ON c.lad_code = l.lad_code AND c.county_code LIKE '{UPPER_TIER_PREFIX}%'"""


def authority_index(con: duckdb.DuckDBPyConnection) -> dict[str, tuple[str, str]]:
    """Map a normalised name to (code, name) for every upper-tier authority."""
    idx: dict[str, tuple[str, str]] = {}
    for code, name in con.execute(
            f"SELECT DISTINCT authority_code, authority_name FROM ({upper_tier_sql(con)})"
            ).fetchall():
        key = normalise_authority(name)
        if key:
            idx[key] = (code, name)
    return idx


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
    "compass":    ("gold.compass_district",    "lad_name"),
    "plumbline":  ("gold.plumbline_authority", "lpa"),
    "highwater":  ("gold.highwater_authority", "lpa"),
    "sightline":  ("gold.sightline_authority", "lpa"),
    "bellwether": ("gold.bellwether_district", "lad_name"),
}

# Systems published per upper-tier authority. Their district tables hold one
# row per district with the authority's figures and whether they are the
# district's own or its county's. Resolution is reported against what the
# system itself publishes -- authority names, or DfE's codes -- so the rate says
# how many authorities were placed, not how many districts a county's figure
# was copied to.
TIERED = {
    "bellwether": {"published": "gold.bellwether_group", "key": "local_authority",
                   "label": "local_authority", "where": ""},
    "compass":    {"published": "gold.compass_trend", "key": "la_code",
                   "label": "la_name || ' (series ends ' || last_year || ')'",
                   "where": "provision = 'Education, health and care plan'"},
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
        if system in TIERED or not _table_exists(con, table):
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
            places.setdefault(code, {})[system] = r

    for system, spec in TIERED.items():
        table, key = SOURCES[system][0], spec["key"]
        if not (_table_exists(con, table) and _table_exists(con, spec["published"])):
            continue
        cur = con.execute(f"SELECT * FROM {table} WHERE {key} IS NOT NULL")
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        for r in rows:
            places.setdefault(r["lad_code"], {})[system] = r
        where = f"WHERE {spec['where']}" if spec["where"] else ""
        published = dict(con.execute(
            f"SELECT DISTINCT {key}, {spec['label']} FROM {spec['published']} {where}").fetchall())
        placed = {r[key] for r in rows} & set(published)
        resolution[system] = {
            "names": len(published), "matched": len(placed),
            "rate": round(100 * len(placed) / len(published), 1) if published else 0.0,
            "unmatched": sorted(str(v) for k, v in published.items() if k not in placed)[:12],
            "counties": len({r[key] for r in rows if r.get("figure_for") == "county"}),
            "county_districts": sum(1 for r in rows if r.get("figure_for") == "county"),
        }
        # These repeat what the row's own key and label already say, and no
        # page reads them; dropped once resolution has been measured from them.
        for r in rows:
            for k in ("lad_code", "lad_name", "authority_code", "la_code", "la_name",
                      "local_authority", "provision", "first_year"):
                r.pop(k, None)

    # School capacity is returned per education authority, so a two-tier
    # district's series is its county's. Held once per authority; each district
    # points at the series it sits under.
    capacity: dict[str, dict] = {}
    if _table_exists(con, "gold.catchment_trend_by_district"):
        for auth, name, label, pct in con.execute("""
                SELECT authority_code, any_value(authority_name), year_label,
                       any_value(utilisation_pct)
                FROM gold.catchment_trend_by_district
                GROUP BY authority_code, period, year_label
                ORDER BY authority_code, period""").fetchall():
            s = capacity.setdefault(auth, {"name": name, "years": [], "pct": []})
            s["years"].append(label)
            s["pct"].append(pct)
        for code, auth, level in con.execute("""
                SELECT DISTINCT lad_code, authority_code, figure_for
                FROM gold.catchment_trend_by_district""").fetchall():
            places.setdefault(code, {})["_capacity"] = {"authority": auth, "figure_for": level}

    for code, entry in places.items():
        entry["_systems"] = sorted(k for k in entry if not k.startswith("_"))

    return {"places": places, "resolution": resolution, "districts": len(places),
            "capacity": capacity}
