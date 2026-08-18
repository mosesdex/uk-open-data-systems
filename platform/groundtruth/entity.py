"""The entity spine: turning an organisation name into one identified body.

This is the harder of the two joins. Place has a national identifier that is
free, complete and published (the property reference). Entity does not: most
datasets carry a *name*, and names are written differently every time --
"SOFTCAT PLC - FCA", "Softcat plc", "SOFTCAT PUBLIC LIMITED COMPANY".

The rules here follow from that:

  1. An identifier always beats a name. If a record carries a company number,
     use it and stop.
  2. A name match is scored, never silent. Anything below the accept threshold
     goes to a human queue rather than being merged.
  3. Ambiguity is an answer. If two companies match equally well, that is
     reported as ambiguous -- not resolved to whichever sorted first.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

# Only unambiguous legal forms are stripped. Words like "group", "holdings" and
# "UK" look like noise but are not: in UK corporate structures "Northern Care
# Group Ltd" and "Northern Care Holdings Ltd" are routinely separate companies
# with separate numbers. Stripping them merges entities that a buyer would
# rightly say are different, so they stay.
SUFFIXES = (
    "public limited company", "limited liability partnership",
    "community interest company", "charitable incorporated organisation",
    "limited", "ltd", "plc", "llp", "cic", "cio", "lp",
    "incorporated", "inc",
)
# Regulator and scheme decorations appended to buyer/supplier names.
DECORATIONS = re.compile(
    r"\s*[-–—]\s*(fca|pra|ofgem|ofwat|ofcom|cqc|ofsted|nhs|mod|dfe|dwp)\s*$",
    re.IGNORECASE,
)
COMPANY_NUMBER = re.compile(r"^(?:[A-Z]{2})?\d{6,8}$")

ACCEPT = 0.95      # merge without review
REVIEW = 0.80      # queue for a human
# below REVIEW: not a match


@dataclass(frozen=True)
class EntityRef:
    method: str                 # "identifier" | "name" | "none"
    confidence: float
    company_number: str | None
    name: str | None = None
    candidates: tuple[str, ...] = field(default_factory=tuple)
    note: str = ""

    @property
    def resolved(self) -> bool:
        return self.company_number is not None

    @property
    def needs_review(self) -> bool:
        return REVIEW <= self.confidence < ACCEPT


UNRESOLVED = EntityRef("none", 0.0, None, note="no identifier and no name match")


def normalise_company_number(raw: str | int | None) -> str | None:
    """Companies House numbers are 8 characters, zero padded, sometimes prefixed."""
    if raw is None:
        return None
    s = re.sub(r"\s+", "", str(raw)).upper()
    if not s or not COMPANY_NUMBER.match(s):
        return None
    prefix = "".join(c for c in s if c.isalpha())
    digits = "".join(c for c in s if c.isdigit())
    if not digits:
        return None
    return f"{prefix}{digits.zfill(8 - len(prefix))}" if prefix else digits.zfill(8)


def normalise_name(raw: str | None) -> str:
    """Reduce a name to its identifying core.

    Strips legal form, regulator decoration, punctuation and the word 'the',
    so that the many spellings of one organisation collapse together.
    """
    if not raw:
        return ""
    s = str(raw).lower()
    s = DECORATIONS.sub("", s)
    s = re.sub(r"[&]", " and ", s)
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    if s.startswith("the "):
        s = s[4:]
    # strip trailing legal forms, repeatedly: "x holdings ltd" -> "x"
    changed = True
    while changed:
        changed = False
        for suf in sorted(SUFFIXES, key=len, reverse=True):
            if s.endswith(" " + suf):
                s = s[: -(len(suf) + 1)].strip()
                changed = True
    return s


def _similarity(a: str, b: str) -> float:
    """Token-set similarity. Deliberately simple and explainable.

    A buyer will eventually ask why two records were merged; 'they share every
    significant word' is an answer that survives that conversation.
    """
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    ta, tb = set(a.split()), set(b.split())
    if not ta or not tb:
        return 0.0
    overlap = len(ta & tb)
    return overlap / max(len(ta), len(tb))


def resolve(
    *,
    company_number: str | int | None = None,
    name: str | None = None,
    index: dict[str, list[tuple[str, str]]] | None = None,
) -> EntityRef:
    """Resolve to one organisation.

    `index` maps a normalised name to (company_number, registered_name) pairs.
    """
    num = normalise_company_number(company_number)
    if num:
        return EntityRef("identifier", 1.0, num, name,
                         note="carried a company number -- no matching required")

    if not name or index is None:
        return UNRESOLVED

    key = normalise_name(name)
    if not key:
        return UNRESOLVED

    exact = index.get(key)
    if exact:
        if len(exact) == 1:
            return EntityRef("name", 0.97, exact[0][0], exact[0][1],
                             note=f"exact match on normalised name {key!r}")
        return EntityRef("name", 0.0, None, name,
                         candidates=tuple(c for c, _ in exact[:5]),
                         note=f"{len(exact)} companies share the name {key!r} -- ambiguous")

    best: list[tuple[float, str, str]] = []
    for cand_key, entries in index.items():
        score = _similarity(key, cand_key)
        if score >= REVIEW:
            for num_, nm in entries:
                best.append((score, num_, nm))
    if not best:
        return EntityRef("none", 0.0, None, name, note=f"no candidate above {REVIEW}")

    best.sort(key=lambda t: -t[0])
    top = best[0]
    tied = [b for b in best if abs(b[0] - top[0]) < 1e-9]
    if len(tied) > 1:
        return EntityRef("name", 0.0, None, name,
                         candidates=tuple(t[1] for t in tied[:5]),
                         note=f"{len(tied)} equally good matches -- ambiguous, not guessed")
    # A fuzzy match never reaches the auto-accept threshold on its own.
    return EntityRef("name", min(top[0], ACCEPT - 0.01), top[1], top[2],
                     note=f"closest name match, score {top[0]:.2f}")


def build_index(rows) -> dict[str, list[tuple[str, str]]]:
    """Index (company_number, name) pairs by normalised name."""
    index: dict[str, list[tuple[str, str]]] = {}
    for number, name in rows:
        num = normalise_company_number(number)
        key = normalise_name(name)
        if num and key:
            index.setdefault(key, []).append((num, name))
    return index
