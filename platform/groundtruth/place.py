"""The place spine: turning a messy reference into a stable identifier.

Resolution is tiered, and the tier is always reported. A postcode centroid is a
useful answer, but it is not the same answer as an exact property, and a
platform that returns both as "a location" is lying by omission. Every result
carries the tier it achieved and a confidence derived from the publisher's own
quality flag -- never an invented number.

Tiers, best first:
  uprn       an exact property reference
  postcode   a postcode centroid, from Code-Point Open
  coordinate a grid reference, resolved to the district of the nearest postcode
             centroid -- for records that carry a location and no identifier
  street     a street reference checked against the national register
  lad        an administrative district only

The coordinate tier exists because the property tier could not reach a district
on its own: the UPRN file carries no LAD, so a record with an exact point and no
postcode fell out of every by-district statistic. It is deliberately the weakest
tier, its confidence falls with distance, and it refuses beyond a stated radius
rather than guessing.
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
    usrn: int | None = None
    street_type: str | None = None
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


def resolve_coordinate(con: duckdb.DuckDBPyConnection,
                       easting: float | None, northing: float | None,
                       *, max_metres: int = 500) -> PlaceRef:
    """District of the nearest postcode centroid to a British National Grid point.

    For records that carry a location and no identifier at all -- the case the
    property tier could not serve, because the UPRN file has no district in it.

    Confidence falls with distance and the search stops at ``max_metres``. A
    point in the middle of a moor genuinely has no nearby centroid, and
    returning the nearest one from ten miles away would be a fabricated answer
    dressed as a resolved one.
    """
    if con is None:
        return PlaceRef("none", 0.0, None, None, None, None, None,
                        note="no database connection")
    if easting is None or northing is None:
        return PlaceRef("none", 0.0, None, None, None, None, None,
                        note="no grid reference given")
    if not _has(con, "place_postcode"):
        return PlaceRef("none", 0.0, None, None, None, None, None,
                        note="postcode tier not loaded -- fetch os_code_point_open")
    try:
        e, n = int(easting), int(northing)
    except (TypeError, ValueError):
        return PlaceRef("none", 0.0, None, None, None, None, None,
                        note=f"not a grid reference: {easting!r}, {northing!r}")

    row = con.execute("""
        SELECT lad_code, ward_code, easting, northing,
               sqrt((easting - ?) * (easting - ?) + (northing - ?) * (northing - ?)) AS d
        FROM silver.place_postcode
        WHERE lad_code IS NOT NULL
          AND easting  BETWEEN ? - ? AND ? + ?
          AND northing BETWEEN ? - ? AND ? + ?
        ORDER BY d
        LIMIT 1
    """, [e, e, n, n, e, max_metres, e, max_metres,
          n, max_metres, n, max_metres]).fetchone()

    if row is None or row[4] > max_metres:
        return PlaceRef("none", 0.0, e, n, None, None, None,
                        note=f"no postcode centroid within {max_metres} m")

    lad, ward, _pe, _pn, d = row
    lat, lon = bng_to_wgs84(e, n)
    # Linear falloff from the postcode tier's weakest confidence. A point on top
    # of a centroid is still only as good as that centroid.
    conf = round(max(0.10, 0.60 * (1.0 - d / max_metres)), 2)
    return PlaceRef("coordinate", conf, e, n, lat, lon, lad, ward_code=ward,
                    note=f"nearest postcode centroid, {d:.0f} m")


def resolve_street(con: duckdb.DuckDBPyConnection, usrn: int | str) -> PlaceRef:
    """Place a street reference against the national street register.

    OS Open USRN carries no street name -- its columns are usrn, street_type and
    a geometry, and nothing in it will tell you a street is called Acacia
    Avenue. So this does not name a street. It says the reference exists, what
    kind of street it is, and where it is, which is the difference between
    carrying a number and having checked it.
    """
    if con is None:
        return PlaceRef("none", 0.0, None, None, None, None, None,
                        note="no database connection")
    if not _has(con, "place_street"):
        return PlaceRef("none", 0.0, None, None, None, None, None,
                        note="street tier not loaded -- fetch os_open_usrn")
    try:
        key = int(usrn)
    except (TypeError, ValueError):
        return PlaceRef("none", 0.0, None, None, None, None, None,
                        note=f"not a street reference: {usrn!r}")
    row = con.execute(
        "SELECT street_type, easting, northing FROM silver.place_street WHERE usrn = ?",
        [key]).fetchone()
    if row is None:
        # 954 references in the property-to-street crosswalk are not in the
        # register. Saying so beats returning a location for a street that the
        # register does not list.
        return PlaceRef("none", 0.0, None, None, None, None, None, usrn=key,
                        note=f"street {key} is not in the register")
    stype, e, n = row
    lat, lon = bng_to_wgs84(e, n)
    # A street centroid locates a line, not a point on it: weaker than a
    # postcode centroid, which at least aims at a cluster of addresses.
    return PlaceRef("street", 0.40, e, n, lat, lon, None,
                    usrn=key, street_type=stype,
                    note=f"street register centroid, {stype.lower()}" if stype
                         else "street register centroid")


def resolve(con: duckdb.DuckDBPyConnection, *, uprn=None, postcode=None,
            easting=None, northing=None) -> PlaceRef:
    """Best available tier for whatever identifiers a record happens to carry.

    The property tier gives an exact coordinate but no administrative district --
    the UPRN file carries no LAD. When a postcode is also present, its district
    is grafted onto the property result, so a record keeps the precise point and
    still aggregates by authority. Without this, property-resolved records fall
    out of every by-district statistic.
    """
    from dataclasses import replace
    if uprn is not None:
        ref = resolve_uprn(con, uprn)
        if ref.resolved:
            if ref.lad_code is None and postcode is not None:
                pc = resolve_postcode(con, postcode)
                if pc.resolved and pc.lad_code:
                    return replace(ref, lad_code=pc.lad_code, ward_code=pc.ward_code)
            if ref.lad_code is None:
                # No postcode to graft. The property still has a point, so the
                # coordinate tier can supply the district it was missing --
                # keeping the exact location and its own confidence.
                co = resolve_coordinate(con, ref.easting, ref.northing)
                if co.resolved and co.lad_code:
                    return replace(ref, lad_code=co.lad_code, ward_code=co.ward_code,
                                   note=ref.note + f"; district from {co.note}")
            return ref
    if postcode is not None:
        ref = resolve_postcode(con, postcode)
        if ref.resolved:
            return ref
    if easting is not None and northing is not None:
        ref = resolve_coordinate(con, easting, northing)
        if ref.resolved:
            return ref
    return UNRESOLVED


def _has(con: duckdb.DuckDBPyConnection, table: str) -> bool:
    return con.execute("""
        SELECT count(*) FROM information_schema.tables
        WHERE table_schema='silver' AND table_name=?""", [table]).fetchone()[0] > 0


# A property reference and a postcode that disagree by more than this are not
# describing the same place. Measured on the school register: genuine estates
# spread a few hundred metres, while broken identifiers land hundreds of
# kilometres away.
CONFLICT_METRES = 2_000


def cross_check(con: duckdb.DuckDBPyConnection, uprn, postcode) -> dict:
    """Resolve a record both ways and report whether the two agree.

    A published property reference can be wrong. In the school register, some
    point to the opposite end of the country. Nothing downstream should treat
    such a reference as authoritative simply because it resolved, so the two
    tiers are compared and the disagreement is reported rather than hidden.
    """
    import math
    p = resolve_uprn(con, uprn) if uprn is not None else UNRESOLVED
    q = resolve_postcode(con, postcode) if postcode else UNRESOLVED
    if not (p.resolved and q.resolved):
        return {"comparable": False, "metres": None, "conflict": False,
                "tier": p.tier if p.resolved else q.tier}
    dlat = (p.latitude - q.latitude) * 111_320
    dlon = ((p.longitude - q.longitude) * 111_320
            * math.cos(math.radians(q.latitude)))
    d = math.hypot(dlat, dlon)
    return {"comparable": True, "metres": round(d), "conflict": d > CONFLICT_METRES,
            "tier": "uprn"}


def coverage(con: duckdb.DuckDBPyConnection) -> dict:
    """What the spine can currently resolve, and at which tier."""
    out: dict = {"tiers": {}}
    if _has(con, "place_postcode"):
        n, lads, quality, no_lad = con.execute("""
            SELECT count(*), count(DISTINCT lad_code),
                   avg(CASE WHEN positional_quality = 10 THEN 1.0 ELSE 0.0 END),
                   count(*) - count(lad_code)
            FROM silver.place_postcode
        """).fetchone()
        out["tiers"]["postcode"] = {
            "rows": n, "distinct_lads": lads,
            "best_quality_share": round((quality or 0) * 100, 1),
            # Postcodes the register carries with no district code: anything
            # placed through one reaches no district figure.
            "no_district": no_lad,
        }
    if _has(con, "place_uprn"):
        n = con.execute("SELECT count(*) FROM silver.place_uprn").fetchone()[0]
        out["tiers"]["uprn"] = {"rows": n}
    if _has(con, "place_street"):
        n, types = con.execute(
            "SELECT count(*), count(DISTINCT street_type) FROM silver.place_street"
        ).fetchone()
        # carries_a_name is stated rather than left to be assumed: OS Open
        # USRN has no street name in it, and a street tier that looks like
        # it might would be read as one.
        out["tiers"]["street"] = {"rows": n, "street_types": types,
                                  "carries_a_name": False}
    if _has(con, "lad"):
        out["tiers"]["lad"] = {
            "rows": con.execute("SELECT count(*) FROM silver.lad").fetchone()[0]
        }
    # The coordinate tier has no table of its own -- it is a lookup against the
    # postcode tier. Its coverage is therefore measured, not counted: NaPTAN is
    # 435,000 real locations published by a department that is not Ordnance
    # Survey, so it tests the tier against something the spine did not build.
    if _has(con, "place_postcode") and _has(con, "naptan_node"):
        total, within = con.execute("""
            WITH s AS (
              -- A fixed sample, not a random one: a random draw moved the
              -- published rate between builds of unchanged data (98.7%, then
              -- 99.2%), which is a figure changing for no reason a reader
              -- could find.
              SELECT easting, northing FROM silver.naptan_node
              WHERE easting IS NOT NULL
              ORDER BY hash(easting, northing), easting, northing
              LIMIT 2000
            )
            SELECT count(*),
                   count(*) FILTER (WHERE EXISTS (
                     SELECT 1 FROM silver.place_postcode p
                     WHERE p.lad_code IS NOT NULL
                       AND p.easting  BETWEEN s.easting  - 500 AND s.easting  + 500
                       AND p.northing BETWEEN s.northing - 500 AND s.northing + 500))
            FROM s
        """).fetchone()
        out["tiers"]["coordinate"] = {
            "tested_against": "NaPTAN access nodes",
            "sample": total,
            "resolved_within_500m": within,
            "resolved_pct": round(100.0 * within / total, 1) if total else None,
        }
    for name, table in (("uprn_to_street", "lids_uprn_usrn"),
                        ("uprn_to_building", "lids_uprn_toid")):
        if _has(con, table):
            out.setdefault("crosswalks", {})[name] = con.execute(
                f"SELECT count(*) FROM silver.{table}").fetchone()[0]
    return out
