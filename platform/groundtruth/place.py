"""The place spine: turning a messy reference into a stable identifier.

Resolution is tiered, and the tier is always reported. A postcode centroid is a
useful answer, but it is not the same answer as an exact property, and a
platform that returns both as "a location" is lying by omission. Every result
carries the tier it achieved and a confidence derived from the publisher's own
quality flag -- never an invented number.

Tiers, best first:
  uprn     an exact property reference
  postcode a postcode centroid, from Code-Point Open
  lad      an administrative district only
"""
from __future__ import annotations

import re
from dataclasses import dataclass

import duckdb

from .geo import bng_to_wgs84

# Code-Point Open positional quality: 10 means the centroid sits within the
# building of the address closest to the postcode mean; 90 means it was imputed.
# Confidence follows the publisher rather than being invented here.
PQ_CONFIDENCE = {10: 0.95, 20: 0.90, 30: 0.85, 40: 0.75, 50: 0.65,
                 60: 0.50, 90: 0.30}

POSTCODE_RE = re.compile(
    r"^([A-Z]{1,2}\d[A-Z\d]?)\s*(\d[A-Z]{2})$", re.IGNORECASE
)


@dataclass(frozen=True)
class PlaceRef:
    tier: str
    confidence: float
    easting: int | None
    northing: int | None
    latitude: float | None
    longitude: float | None
    lad_code: str | None
    ward_code: str | None = None
    uprn: int | None = None
    note: str = ""

    @property
    def resolved(self) -> bool:
        return self.latitude is not None


UNRESOLVED = PlaceRef("none", 0.0, None, None, None, None, None,
                      note="no tier matched")


def normalise_postcode(raw: str) -> str | None:
    """Return a canonical key, or None if this is not a postcode.

    Deliberately strict. Accepting near-misses is how a place spine quietly
    starts attributing records to the wrong district.
    """
    if not raw:
        return None
    s = re.sub(r"\s+", "", str(raw)).upper()
    m = POSTCODE_RE.match(s)
    return f"{m.group(1)}{m.group(2)}" if m else None


def resolve_postcode(con: duckdb.DuckDBPyConnection, raw: str) -> PlaceRef:
    key = normalise_postcode(raw)
    if key is None:
        return PlaceRef("none", 0.0, None, None, None, None, None,
                        note=f"not a valid postcode: {raw!r}")
    row = con.execute("""
        SELECT easting, northing, lad_code, ward_code, positional_quality
        FROM silver.place_postcode WHERE postcode_key = ?
    """, [key]).fetchone()
    if row is None:
        return PlaceRef("none", 0.0, None, None, None, None, None,
                        note=f"postcode not in Code-Point Open: {key}")
    e, n, lad, ward, pq = row
    lat, lon = bng_to_wgs84(e, n)
    return PlaceRef("postcode", PQ_CONFIDENCE.get(pq, 0.5), e, n, lat, lon,
                    lad, ward, note=f"centroid, positional quality {pq}")


def resolve_uprn(con: duckdb.DuckDBPyConnection, uprn: int | str) -> PlaceRef:
    if not _has(con, "place_uprn"):
        return PlaceRef("none", 0.0, None, None, None, None, None,
                        note="property tier not loaded -- fetch os_open_uprn")
    try:
        key = int(uprn)
    except (TypeError, ValueError):
        return PlaceRef("none", 0.0, None, None, None, None, None,
                        note=f"not a property reference: {uprn!r}")
    row = con.execute("""
        SELECT easting, northing, latitude, longitude
        FROM silver.place_uprn WHERE uprn = ?
    """, [key]).fetchone()
    if row is None:
        return PlaceRef("none", 0.0, None, None, None, None, None,
                        note=f"property reference not found: {key}")
    e, n, lat, lon = row
    return PlaceRef("uprn", 1.0, int(e) if e else None, int(n) if n else None,
                    lat, lon, None, uprn=key, note="exact property")


def resolve(con: duckdb.DuckDBPyConnection, *, uprn=None, postcode=None) -> PlaceRef:
    """Best available tier for whatever identifiers a record happens to carry."""
    if uprn is not None:
        ref = resolve_uprn(con, uprn)
        if ref.resolved:
            return ref
    if postcode is not None:
        ref = resolve_postcode(con, postcode)
        if ref.resolved:
            return ref
    return UNRESOLVED


def _has(con: duckdb.DuckDBPyConnection, table: str) -> bool:
    return con.execute("""
        SELECT count(*) FROM information_schema.tables
        WHERE table_schema='silver' AND table_name=?""", [table]).fetchone()[0] > 0


def coverage(con: duckdb.DuckDBPyConnection) -> dict:
    """What the spine can currently resolve, and at which tier."""
    out: dict = {"tiers": {}}
    if _has(con, "place_postcode"):
        n, lads, quality = con.execute("""
            SELECT count(*), count(DISTINCT lad_code),
                   avg(CASE WHEN positional_quality = 10 THEN 1.0 ELSE 0.0 END)
            FROM silver.place_postcode
        """).fetchone()
        out["tiers"]["postcode"] = {
            "rows": n, "distinct_lads": lads,
            "best_quality_share": round((quality or 0) * 100, 1),
        }
    if _has(con, "place_uprn"):
        n = con.execute("SELECT count(*) FROM silver.place_uprn").fetchone()[0]
        out["tiers"]["uprn"] = {"rows": n}
    if _has(con, "lad"):
        out["tiers"]["lad"] = {
            "rows": con.execute("SELECT count(*) FROM silver.lad").fetchone()[0]
        }
    return out
