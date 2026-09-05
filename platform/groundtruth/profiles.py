"""Everything the platform knows about one place, or one organisation.

The thirteen systems each answer their own question well and separately. Nobody
asking about a district wants to run thirteen commands and join the answers by
hand, and the join is exactly what the two spines make possible -- so not
offering it wastes the thing the project built.

A profile is therefore an assembly, not a new calculation. Every figure is read
from the gold table the system already wrote, and every figure carries the table
it came from, so a profile can be audited back to a system and from there to a
source. Nothing is recomputed here, because a second implementation of a
statistic is a second chance to disagree with the first.

Two rules the assembly must not break:

  * a system with no table is *unavailable*, never zero -- the distinction
    between "no flood defences here" and "Bulwark has not run" is the whole
    reason the platform reports coverage
  * a district matched to a name-keyed table by name is reported as a name
    match, because that is what it is
"""
from __future__ import annotations

from dataclasses import dataclass, field

import duckdb

from . import ids

# Tables keyed by ONS district code -- an identifier match, no ambiguity.
# Tables keyed by an authority *name* are handled separately and flagged.
_BY_LAD = {
    "catchment":  ("gold.catchment_district", "lad_code"),
    "baseline":   ("gold.baseline_district", "lad_code"),
    "bulwark":    ("gold.bulwark_district", "lad_code"),
    "highwater":  ("gold.highwater_district", "lad_code"),
    "lastmile":   ("gold.lastmile_authority", "lad_code"),
    "sightline":  ("gold.sightline_wq_district", "lad_code"),
    "specialist": ("gold.catchment_specialist", "lad_code"),
}

# Tables keyed by the authority's name as its publisher writes it. Matching
# these is a name match and is labelled as one.
_BY_NAME = {
    "bulwark_authority":   ("gold.bulwark_authority", "local_authority"),
    "highwater_authority": ("gold.highwater_authority", "lpa"),
    "plumbline":           ("gold.plumbline_authority", "lpa"),
    "ledger":              ("gold.ledger_authority", "authority"),
    "sightline_authority": ("gold.sightline_authority", "lpa"),
    "compass":             ("gold.compass_cohort", "la_name"),
}

# Name-keyed tables holding many rows per authority -- a list, not a summary.
# Kept separate because taking the first row of these would silently present one
# care provider as though it were the authority's whole picture.
_BY_NAME_MANY = {
    "bellwether": ("gold.bellwether_care", "local_authority",
                   "provider, company_number, locations, beds, share_pct",
                   "beds"),
    "bellwether_group": ("gold.bellwether_group", "local_authority",
                         "group_name, branded, locations, beds, share_pct",
                         "beds"),
}

# Systems published against upper-tier authorities rather than districts. Social
# care and SEND are county responsibilities, so Worthing has no care row at all
# and West Sussex has 238. A profile that showed an empty section there would
# read as "no care homes in Worthing", which is false and the opposite of the
# truth. The platform holds no district-to-county mapping, so the honest output
# is to name the level difference rather than guess the parent.
_UPPER_TIER = {"bellwether", "bellwether_group", "compass"}
_UPPER_TIER_NOTE = ("published against upper-tier authorities, not districts: "
                    "social care and SEND are county responsibilities. An absent "
                    "row here means this district is not an upper-tier authority, "
                    "not that there is nothing to report")


@dataclass
class Section:
    """One system's contribution to a profile."""
    system: str
    table: str
    available: bool
    match: str = "identifier"          # identifier | name | none
    facts: dict = field(default_factory=dict)
    note: str = ""

    def as_dict(self) -> dict:
        return {"system": self.system, "table": self.table,
                "available": self.available, "match": self.match,
                "facts": self.facts, "note": self.note}


def _exists(con: duckdb.DuckDBPyConnection, qualified: str) -> bool:
    schema, _, table = qualified.partition(".")
    return con.execute(
        "SELECT count(*) FROM information_schema.tables "
        "WHERE table_schema = ? AND table_name = ?", [schema, table]
    ).fetchone()[0] > 0


def _one(con: duckdb.DuckDBPyConnection, table: str, key_col: str, key) -> dict | None:
    cur = con.execute(f'SELECT * FROM {table} WHERE {key_col} = ? LIMIT 1', [key])
    row = cur.fetchone()
    if row is None:
        return None
    return dict(zip([d[0] for d in cur.description], row))


def lad_name(con: duckdb.DuckDBPyConnection, lad_code: str) -> str | None:
    """The district's name, from whichever table currently carries the pair."""
    for table, code_col, name_col in (("silver.lad", "lad_code", "lad_name"),
                                      ("gold.catchment_district", "lad_code", "lad_name"),
                                      ("gold.bulwark_district", "lad_code", "lad_name")):
        if _exists(con, table):
            row = con.execute(
                f"SELECT {name_col} FROM {table} WHERE {code_col} = ? LIMIT 1",
                [lad_code]).fetchone()
            if row and row[0]:
                return row[0]
    return None


def _name_candidates(name: str) -> list[str]:
    """The spellings one authority is published under.

    'Cornwall', 'Cornwall Council' and 'Cornwall County Council' are one
    authority written three ways. Generating the variants and matching exactly
    is preferable to fuzzy matching: it either hits a published spelling or it
    does not, and there is no score to over-trust.
    """
    base = name.strip()
    stripped = base
    for suffix in (" Council", " Borough Council", " District Council",
                   " County Council", " City Council",
                   " Metropolitan Borough Council", " London Borough"):
        if stripped.endswith(suffix):
            stripped = stripped[: -len(suffix)].strip()
            break
    out = {base, stripped,
           f"{stripped} Council", f"{stripped} Borough Council",
           f"{stripped} District Council", f"{stripped} County Council",
           f"{stripped} City Council", f"London Borough of {stripped}"}
    return [v for v in out if v]


def place_profile(con: duckdb.DuckDBPyConnection, identifier: str) -> dict:
    """Assemble everything known about a district.

    Accepts a ``gt:place:lad:`` identifier. A postcode identifier is resolved to
    its district first, and the resolution is reported rather than hidden, since
    a postcode is a smaller thing than a district and the answer is about the
    district.
    """
    ident = ids.parse(identifier)
    resolved_from = None
    if ident.namespace == "postcode":
        row = con.execute(
            "SELECT lad_code FROM silver.place_postcode WHERE postcode = ? LIMIT 1",
            [ident.key]).fetchone() if _exists(con, "silver.place_postcode") else None
        if not row or not row[0]:
            return {"identifier": identifier, "resolved": False,
                    "reason": "postcode not in the place spine"}
        # Record the canonical identifier, not the raw text: 'BN43 1AA' and
        # 'bn431aa' are one postcode, and the trail should say which one.
        resolved_from, ident = str(ident), ids.place_lad(row[0])
    elif ident.namespace != "lad":
        return {"identifier": identifier, "resolved": False,
                "reason": f"place profiles cover districts and postcodes, not {ident.namespace}"}

    code = ident.key
    name = lad_name(con, code)
    sections: list[Section] = []

    for system, (table, key_col) in _BY_LAD.items():
        if not _exists(con, table):
            sections.append(Section(system, table, False,
                                    note="system has not run"))
            continue
        facts = _one(con, table, key_col, code)
        sections.append(Section(system, table, True, "identifier", facts or {},
                                "" if facts else "no rows for this district"))

    if name:
        variants = _name_candidates(name)
        marks = ",".join("?" * len(variants))
        for system, (table, key_col) in _BY_NAME.items():
            if not _exists(con, table):
                sections.append(Section(system, table, False,
                                        note="system has not run"))
                continue
            cur = con.execute(
                f"SELECT * FROM {table} WHERE {key_col} IN ({marks}) LIMIT 1", variants)
            row = cur.fetchone()
            facts = dict(zip([d[0] for d in cur.description], row)) if row else {}
            miss = (_UPPER_TIER_NOTE if system in _UPPER_TIER
                    else f"no row published under any spelling of {name!r}")
            sections.append(Section(
                system, table, True, "name" if facts else "none", facts,
                "" if facts else miss))

        for system, (table, key_col, cols, order) in _BY_NAME_MANY.items():
            if not _exists(con, table):
                sections.append(Section(system, table, False,
                                        note="system has not run"))
                continue
            cur = con.execute(
                f"SELECT {cols} FROM {table} WHERE {key_col} IN ({marks}) "
                f"ORDER BY {order} DESC NULLS LAST LIMIT 25", variants)
            names = [d[0] for d in cur.description]
            rows = [dict(zip(names, r)) for r in cur.fetchall()]
            miss = (_UPPER_TIER_NOTE if system in _UPPER_TIER
                    else f"no row published under any spelling of {name!r}")
            sections.append(Section(
                system, table, True, "name" if rows else "none",
                {"rows": rows, "count": len(rows)} if rows else {},
                "" if rows else miss))

    live = [s for s in sections if s.available and s.facts]
    return {
        "identifier": str(ident),
        "resolved": True,
        "resolved_from": resolved_from,
        "lad_code": code,
        "name": name,
        "systems_with_data": len(live),
        "systems_checked": len(sections),
        "by_identifier": sum(1 for s in live if s.match == "identifier"),
        "by_name": sum(1 for s in live if s.match == "name"),
        "sections": [s.as_dict() for s in sections],
    }


def organisation_profile(con: duckdb.DuckDBPyConnection, identifier: str) -> dict:
    """Assemble everything known about one organisation.

    Accepts a ``gt:entity:company:`` identifier. The company number is the join
    throughout, so every section here is an identifier match -- which is why the
    entity spine insists on one.
    """
    ident = ids.parse(identifier)
    if ident.namespace != "company":
        return {"identifier": identifier, "resolved": False,
                "reason": f"organisation profiles are keyed on a company number, "
                          f"not {ident.namespace}"}
    number = ident.key

    if not _exists(con, "gold.entity"):
        return {"identifier": str(ident), "resolved": False,
                "reason": "gold.entity has not been built -- run: gt entity"}
    core = _one(con, "gold.entity", "company_number", number)
    if core is None:
        return {"identifier": str(ident), "resolved": False,
                "reason": "no organisation in the entity spine with this number"}

    sections: list[Section] = []
    for system, table, key_col in (
            ("bellwether", "gold.bellwether_footprint", "company_number"),
            ("bellwether_care", "gold.bellwether_care", "company_number"),
            ("watchman", "gold.watchman_distress", "company_number"),
            ("sentinel", "gold.sentinel_repeat", "supplier_id"),
            ("care_detail", "gold.entity_care_agg", "cn"),
            ("procurement_detail", "gold.entity_proc_agg", "cn")):
        if not _exists(con, table):
            sections.append(Section(system, table, False, note="system has not run"))
            continue
        cur = con.execute(f"SELECT * FROM {table} WHERE {key_col} = ? LIMIT 5", [number])
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        sections.append(Section(
            system, table, True, "identifier",
            {"rows": rows, "count": len(rows)} if rows else {},
            "" if rows else "no rows for this company number"))

    # Where the organisation operates. A footprint is a claim about places, so
    # it is assembled from the tables that name them rather than asserted.
    footprint: list[str] = []
    if _exists(con, "gold.bellwether_care"):
        footprint = [r[0] for r in con.execute(
            """SELECT DISTINCT local_authority FROM gold.bellwether_care
               WHERE company_number = ? AND local_authority IS NOT NULL
               ORDER BY 1 LIMIT 100""", [number]).fetchall()]

    live = [s for s in sections if s.available and s.facts]
    return {
        "identifier": str(ident),
        "resolved": True,
        "company_number": number,
        "name": core.get("name"),
        "status": core.get("status"),
        "incorporated": core.get("incorporated"),
        "post_town": core.get("post_town"),
        "in_care": core.get("in_care"),
        "in_procurement": core.get("in_proc"),
        "care_locations": core.get("care_locations"),
        "care_beds": core.get("care_beds"),
        "procurement_awards": core.get("proc_awards"),
        "procurement_value": core.get("proc_value"),
        "authorities_operated_in": footprint,
        "systems_with_data": len(live),
        "systems_checked": len(sections),
        "sections": [s.as_dict() for s in sections],
    }
