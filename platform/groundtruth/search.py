"""One way in, and a visible query plan.

The front door to a platform like this is usually a search box that returns an
answer and hides how it got there. That is the wrong shape for this project. The
whole argument is that an answer is only worth as much as the joins underneath
it, so an interface that conceals the joins throws away the argument to look
clever.

So search here does four things in order, and shows all four:

  1. resolve the words to things -- places, organisations, systems
  2. state the plan: which datasets, which joins, in which order
  3. say whether the question is answerable, and how completely
  4. answer it, with coverage

Step three is the one that matters. "Groundtruth cannot currently determine
this, and here is precisely which piece is missing" is a better answer than a
confident number over a 6% join, and it is the answer this corpus most often
supports. A search that always produces something would have to invent the
difference.

Deliberately not an interpreter of free-form language. It resolves the nouns it
can verify against the spines and matches topics to systems by keyword. A parser
that guessed at intent would be introducing exactly the unfalsifiable step the
rest of the platform refuses.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

import duckdb

from . import ids

# What each system can answer, and the gold table that proves it can. The
# keywords are the vocabulary the corpus actually supports -- a word not here is
# a word the platform should say it cannot act on rather than approximate.
SYSTEMS: dict[str, dict] = {
    "catchment":  {"about": "school places against capacity",
                   "keywords": ("school", "schools", "pupil", "pupils", "places",
                                "capacity", "classroom", "education"),
                   "table": "gold.catchment_district"},
    "compass":    {"about": "SEND demand and its trend",
                   "keywords": ("send", "sen", "ehc", "special", "needs"),
                   "table": "gold.compass_cohort"},
    "plumbline":  {"about": "planning performance as measured, not as headlined",
                   "keywords": ("planning performance", "decisions", "in time",
                                "determined", "speed"),
                   "table": "gold.plumbline_authority"},
    "highwater":  {"about": "development permitted against flood objections",
                   "keywords": ("flood", "flooding", "floodplain", "objection",
                                "objections", "flood risk"),
                   "table": "gold.highwater_district"},
    "bulwark":    {"about": "flood defence ownership and condition",
                   "keywords": ("defence", "defences", "sea wall", "embankment",
                                "asset", "assets", "maintainer"),
                   "table": "gold.bulwark_district"},
    "baseline":   {"about": "storm overflow spills, weather adjusted",
                   "keywords": ("sewage", "spill", "spills", "overflow",
                                "storm", "water quality", "discharge"),
                   "table": "gold.baseline_district"},
    "lastmile":   {"about": "gigabit availability, including at new build",
                   "keywords": ("broadband", "gigabit", "connectivity", "fibre",
                                "internet", "new build"),
                   "table": "gold.lastmile_authority"},
    "ledger":     {"about": "developer contributions promised and delivered",
                   "keywords": ("developer", "contribution", "contributions",
                                "section 106", "s106", "cil", "obligation"),
                   "table": "gold.ledger_authority"},
    "bellwether": {"about": "care provider concentration and exposure",
                   "keywords": ("care", "care home", "provider", "beds",
                                "residential", "nursing"),
                   "table": "gold.bellwether_care"},
    "sentinel":   {"about": "procurement concentration and repeat awards",
                   "keywords": ("procurement", "contract", "contracts", "award",
                                "awards", "supplier", "tender", "bidder"),
                   "table": "gold.sentinel_buyer"},
    "watchman":   {"about": "insolvency exposure across public suppliers",
                   "keywords": ("insolvency", "insolvent", "administration",
                                "liquidation", "distress", "failure"),
                   "table": "gold.watchman_distress"},
    "sightline":  {"about": "statutory consultee advice and its outcome",
                   "keywords": ("consultee", "advice", "statutory", "objected"),
                   "table": "gold.sightline_authority"},
    "junction":   {"about": "what grid operators publish about capacity",
                   "keywords": ("grid", "connection", "capacity", "dno",
                                "electricity", "queue"),
                   "table": "gold.junction_register"},
}

# Things the corpus cannot answer at all, and why. Naming them is more useful
# than letting a search return an empty result that reads like an absence of
# activity rather than an absence of data.
KNOWN_UNANSWERABLE: tuple[tuple[tuple[str, ...], str], ...] = (
    (("bid price", "bid prices", "single bidder", "how many bidders"),
     "Bid prices and bidder counts are not published in UK procurement data at "
     "all, so no collusion screen based on them can be built by anyone."),
    (("occupancy", "occupied", "completion date", "completed homes"),
     "Construction completion and actual occupancy are not published against "
     "planning references, so a permission cannot be followed to a built home."),
    (("northern ireland", "belfast", "ni "),
     "The place spine is built on Code-Point Open, which covers Great Britain. "
     "There are zero Northern Ireland postcodes in it."),
)

_STOP = {"the", "a", "an", "in", "of", "for", "with", "and", "or", "to", "how",
         "many", "much", "what", "which", "where", "who", "are", "is", "has",
         "have", "show", "me", "list", "most", "by", "on", "at", "per", "do"}


@dataclass
class Plan:
    """What a search would do, stated before it does it."""
    question: str
    places: list[dict] = field(default_factory=list)
    organisations: list[dict] = field(default_factory=list)
    systems: list[str] = field(default_factory=list)
    tables: list[str] = field(default_factory=list)
    joins: list[str] = field(default_factory=list)
    blocked: list[str] = field(default_factory=list)
    unresolved: list[str] = field(default_factory=list)

    @property
    def answerable(self) -> str:
        if self.blocked and not self.systems:
            return "no"
        if not self.systems:
            return "no"
        if self.blocked or not (self.places or self.organisations):
            return "partial"
        return "yes"

    def as_dict(self) -> dict:
        return {"question": self.question, "answerable": self.answerable,
                "places": self.places, "organisations": self.organisations,
                "systems": self.systems, "tables": self.tables,
                "joins": self.joins, "blocked": self.blocked,
                "unresolved": self.unresolved}


def _exists(con: duckdb.DuckDBPyConnection, qualified: str) -> bool:
    schema, _, table = qualified.partition(".")
    return con.execute(
        "SELECT count(*) FROM information_schema.tables "
        "WHERE table_schema = ? AND table_name = ?", [schema, table]
    ).fetchone()[0] > 0


def _match_places(con: duckdb.DuckDBPyConnection, question: str,
                  limit: int = 5) -> list[dict]:
    """Districts named in the question.

    Matched against the published district names rather than a gazetteer of our
    own, so a hit means a name this platform can actually key on.
    """
    if not _exists(con, "gold.catchment_district"):
        return []
    q = question.lower()
    rows = con.execute(
        "SELECT lad_code, lad_name FROM gold.catchment_district "
        "WHERE lad_name IS NOT NULL").fetchall()
    hits = []
    for code, name in rows:
        n = name.lower()
        # word-boundary match: 'Ryedale' must not fire on 'ryedales', and a
        # two-letter district must not match inside another word.
        if re.search(rf"\b{re.escape(n)}\b", q):
            hits.append({"identifier": str(ids.place_lad(code)),
                         "lad_code": code, "name": name, "matched_on": "name"})
    hits.sort(key=lambda h: -len(h["name"]))
    return hits[:limit]


def _match_organisations(con: duckdb.DuckDBPyConnection, question: str,
                         limit: int = 5) -> list[dict]:
    """Organisations named in the question, by exact registered name.

    Exact rather than fuzzy on purpose. The entity spine already refuses to
    resolve a name below its threshold, and a search box is not the place to
    relax a rule the rest of the platform enforces.
    """
    if not _exists(con, "gold.entity"):
        return []
    q = question.upper()
    words = [w for w in re.findall(r"[A-Za-z][A-Za-z&'.-]{3,}", question)
             if w.lower() not in _STOP]
    if not words:
        return []
    rows = con.execute(
        """SELECT company_number, name, status FROM gold.entity
           WHERE name IS NOT NULL AND length(name) > 4 LIMIT 200000""").fetchall()
    hits = []
    for number, name, status in rows:
        if name.upper() in q:
            hits.append({"identifier": str(ids.entity_company(number)),
                         "company_number": number, "name": name,
                         "status": status, "matched_on": "exact registered name"})
    hits.sort(key=lambda h: -len(h["name"]))
    return hits[:limit]


def _match_systems(question: str) -> list[str]:
    q = f" {question.lower()} "
    out = []
    for system, meta in SYSTEMS.items():
        if system in q:
            out.append(system)
            continue
        for kw in meta["keywords"]:
            if re.search(rf"\b{re.escape(kw)}\b", q):
                out.append(system)
                break
    return sorted(set(out))


def _blocked(question: str) -> list[str]:
    q = question.lower()
    return [reason for terms, reason in KNOWN_UNANSWERABLE
            if any(t in q for t in terms)]


def plan(con: duckdb.DuckDBPyConnection, question: str) -> Plan:
    """Resolve a question into the work it would take, without doing it."""
    p = Plan(question=question)
    p.places = _match_places(con, question)
    p.organisations = _match_organisations(con, question)
    p.systems = _match_systems(question)
    p.blocked = _blocked(question)

    for s in p.systems:
        table = SYSTEMS[s]["table"]
        if _exists(con, table):
            p.tables.append(table)
        else:
            p.blocked.append(f"{s} has not run: {table} is not in the database")

    if p.places and p.systems:
        p.joins.append("place spine: district code -> each system's district table")
    if p.organisations and p.systems:
        p.joins.append("entity spine: company number -> each system's company table")

    known = {w for h in p.places for w in h["name"].lower().split()}
    known |= {w for h in p.organisations for w in h["name"].lower().split()}
    known |= {k for s in p.systems for k in SYSTEMS[s]["keywords"]}
    known |= set(SYSTEMS) | _STOP
    for w in re.findall(r"[a-z]{4,}", question.lower()):
        if w not in known and not any(w in k for k in known):
            p.unresolved.append(w)
    p.unresolved = sorted(set(p.unresolved))
    return p


def answer(con: duckdb.DuckDBPyConnection, question: str,
           limit: int = 10) -> dict:
    """Plan the question, then execute as much of it as the corpus supports."""
    from . import profiles

    p = plan(con, question)
    out: dict = {"plan": p.as_dict(), "results": [], "coverage": {}}

    if p.answerable == "no":
        out["answer"] = None
        out["why_not"] = p.blocked or [
            "no system in this platform covers the subject of this question"]
        return out

    # A named place or organisation makes this a profile question, which is the
    # assembled answer the spines exist to make possible.
    for place in p.places[:limit]:
        prof = profiles.place_profile(con, place["identifier"])
        wanted = [s for s in prof.get("sections", [])
                  if not p.systems or s["system"] in p.systems]
        out["results"].append({"subject": place["name"],
                               "identifier": place["identifier"],
                               "sections": wanted})
    for org in p.organisations[:limit]:
        out["results"].append({"subject": org["name"],
                               "identifier": org["identifier"],
                               "profile": profiles.organisation_profile(
                                   con, org["identifier"])})

    # No place or organisation named: answer at national level from the systems
    # the question matched.
    if not out["results"] and p.systems:
        for s in p.systems:
            table = SYSTEMS[s]["table"]
            if not _exists(con, table):
                continue
            cur = con.execute(f"SELECT * FROM {table} LIMIT ?", [limit])
            cols = [d[0] for d in cur.description]
            rows = [dict(zip(cols, r)) for r in cur.fetchall()]
            total = con.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
            out["results"].append({"subject": s, "about": SYSTEMS[s]["about"],
                                   "table": table, "rows_total": total,
                                   "rows": rows})

    out["coverage"] = {
        "systems_matched": len(p.systems),
        "systems_with_data": len([t for t in p.tables]),
        "places_resolved": len(p.places),
        "organisations_resolved": len(p.organisations),
        "words_not_understood": p.unresolved,
    }
    out["answer"] = p.answerable
    return out
