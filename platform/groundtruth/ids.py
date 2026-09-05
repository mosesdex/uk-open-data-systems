"""Groundtruth identifiers.

A researcher who wants to cite "this company" or "this property" currently has
to quote a name and hope the reader reconciles it the same way. That is the
problem the two spines exist to solve, so the resolved thing needs a name of its
own that can be written down, put in a footnote and resolved again later.

The scheme is deliberately *derived*, not allocated:

    gt:entity:company:01234567
    gt:place:uprn:100023336956
    gt:place:postcode:SW1A1AA
    gt:event:contribution:111/DOV-17-01530-da-con-1

A sequential registry (``gt:place:GB-00001234``) was the obvious first design
and is the wrong one here. It requires a counter that must survive every
rebuild, it makes an identifier depend on the order rows happened to load, and
two operators running the same pipeline over the same snapshot would mint
different identifiers for the same property. All three break reproducibility,
which is the point of publishing identifiers at all.

Deriving the identifier from the publisher's own key costs nothing, survives a
rebuild from an empty database, and stays legible: a reader
who sees ``gt:entity:company:01234567`` can check it at Companies House without
asking us for a lookup table.

Where a fixed-width token is genuinely needed -- a URL slug, a column in a
fixed-format export -- :func:`short` renders a stable digest of the same
identifier. It is a rendering of the identifier, never a replacement for it.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

SCHEME = "gt"

# The four object families the evidence graph is built from. Anything that is
# not one of these does not get an identifier, because an identifier that means
# "some row somewhere" is not an identifier.
KINDS = ("place", "entity", "event", "document")

# Namespaces per kind: the publisher's own identifier system. Adding one is a
# deliberate act -- it asserts that the publisher's key is stable enough to
# quote, which is exactly the claim an identifier makes.
NAMESPACES: dict[str, tuple[str, ...]] = {
    "place":    ("uprn", "postcode", "lad", "toid", "usrn"),
    "entity":   ("company", "charity", "organisation", "school", "care", "provider"),
    "event":    ("contribution", "transaction", "award", "application",
                 "agreement", "objection", "inspection", "spill", "connection"),
    "document": ("register", "notice", "publication"),
}

_SEGMENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]*$")
_BASE32 = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"   # Crockford: no I, L, O, U


class IdentifierError(ValueError):
    """A malformed identifier. Raised rather than returning None: minting a bad
    identifier silently would put it in an export, and an export is forever."""


@dataclass(frozen=True)
class Identifier:
    kind: str
    namespace: str
    key: str

    def __str__(self) -> str:
        return f"{SCHEME}:{self.kind}:{self.namespace}:{self.key}"

    @property
    def short(self) -> str:
        return short(str(self))


def normalise_key(namespace: str, raw: str | int | None) -> str | None:
    """Canonicalise a publisher key so one thing gets one identifier.

    The normalisations here are only those the publisher's own format allows.
    A postcode is case- and space-insensitive by definition, so folding it is
    safe. A company number is zero-padded to eight because Companies House
    itself does. Nothing here guesses.
    """
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None

    if namespace == "postcode":
        s = re.sub(r"\s+", "", s).upper()
    elif namespace == "company":
        # Companies House pads to eight; "1234567" and "01234567" are one company.
        s = s.strip().upper()
        if s.isdigit():
            s = s.zfill(8)
    elif namespace in ("uprn", "toid", "usrn", "organisation"):
        # Numeric references arrive as floats from JSON often enough to matter:
        # 100023336956.0 and 100023336956 must not become two properties.
        try:
            s = str(int(float(s)))
        except (TypeError, ValueError):
            return None
    else:
        s = s.strip()

    return s or None


def mint(kind: str, namespace: str, key: str | int | None) -> Identifier:
    """Build an identifier, or refuse."""
    if kind not in KINDS:
        raise IdentifierError(f"unknown kind {kind!r}; expected one of {KINDS}")
    allowed = NAMESPACES[kind]
    if namespace not in allowed:
        raise IdentifierError(
            f"unknown namespace {namespace!r} for {kind}; expected one of {allowed}")
    norm = normalise_key(namespace, key)
    if norm is None:
        raise IdentifierError(f"empty key for {kind}:{namespace}")
    if not _SEGMENT.match(norm):
        raise IdentifierError(f"key {norm!r} is not quotable as an identifier segment")
    return Identifier(kind, namespace, norm)


def parse(text: str) -> Identifier:
    """Read an identifier back. The inverse of ``str(Identifier)``."""
    if not isinstance(text, str):
        raise IdentifierError(f"not an identifier: {text!r}")
    parts = text.split(":", 3)
    if len(parts) != 4 or parts[0] != SCHEME:
        raise IdentifierError(f"not a {SCHEME}: identifier: {text!r}")
    _, kind, namespace, key = parts
    return mint(kind, namespace, key)


def is_valid(text: str) -> bool:
    try:
        parse(text)
        return True
    except IdentifierError:
        return False


def short(identifier: str | Identifier, length: int = 16) -> str:
    """A fixed-width rendering, for URL slugs and fixed-format exports.

    Crockford base32 over a blake2b digest. At sixteen characters the space is
    about 1.2e24, so a corpus of a hundred million objects carries a collision
    probability around four in a billion -- small enough to render, never small
    enough to justify discarding the real identifier.
    """
    text = str(identifier)
    digest = hashlib.blake2b(text.encode("utf-8"), digest_size=16).digest()
    n = int.from_bytes(digest, "big")
    out = []
    for _ in range(length):
        n, r = divmod(n, 32)
        out.append(_BASE32[r])
    return "".join(reversed(out))


# -- convenience constructors, so callers do not repeat the namespace strings --

def place_uprn(uprn) -> Identifier:
    return mint("place", "uprn", uprn)


def place_postcode(postcode) -> Identifier:
    return mint("place", "postcode", postcode)


def place_lad(code) -> Identifier:
    return mint("place", "lad", code)


def entity_company(number) -> Identifier:
    return mint("entity", "company", number)


def entity_organisation(entity) -> Identifier:
    """A planning.data.gov.uk organisation entity, as carried by MHCLG datasets."""
    return mint("entity", "organisation", entity)


# Planning references are unique per authority, not nationally: 24,306 of the
# 39,325 developer contributions share a reference with a contribution in a
# different council, and 5,381 of 12,775 agreements do. An identifier built on
# the bare reference therefore merges records from different authorities, which
# is the silent false join this whole platform exists to prevent. The authority
# is part of the key.
def event_contribution(reference, organisation) -> Identifier:
    return mint("event", "contribution", _qualified(organisation, reference))


def event_application(reference, organisation) -> Identifier:
    return mint("event", "application", _qualified(organisation, reference))


def event_agreement(reference, organisation) -> Identifier:
    return mint("event", "agreement", _qualified(organisation, reference))


def _qualified(organisation, reference) -> str:
    """`<organisation>/<reference>`, the key the publisher actually guarantees."""
    org = normalise_key("organisation", organisation)
    ref = normalise_key("event", reference)
    if org is None or ref is None:
        raise IdentifierError(
            f"a planning reference needs its authority to be unique: "
            f"got organisation={organisation!r} reference={reference!r}")
    return f"{org}/{ref}"


def split_qualified(identifier: Identifier | str) -> tuple[str, str]:
    """The authority and the reference behind a qualified event identifier."""
    ident = identifier if isinstance(identifier, Identifier) else parse(identifier)
    org, sep, ref = ident.key.partition("/")
    if not sep:
        raise IdentifierError(f"{ident} is not authority-qualified")
    return org, ref
