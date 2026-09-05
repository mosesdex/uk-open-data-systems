"""Point-in-polygon assignment to local authority districts.

The platform has coordinate conversion (geo.py) but no spatial-join engine, so
this is a small, dependency-free ray-casting resolver over the ONS LAD
boundaries. It is deliberately simple: a bounding-box pre-filter narrows the
candidate districts for each point, then a standard even-odd ray cast tests the
exterior ring(s). Holes are ignored — a district's islands and inlets do not
change which authority a flood outlet or defence belongs to at this resolution.

Used by systems whose records carry coordinates (baseline) or an authority name
(bulwark) but no ONS code, so their figures can be mapped district by district.
"""
from __future__ import annotations

import json
import os
import unicodedata

BOUNDARIES = os.path.join(os.path.dirname(__file__), "..", "data", "bronze",
                          "ons_lad_boundaries.geojson")


class Lads:
    """The LAD boundaries, indexed for point lookup and name lookup."""

    def __init__(self, features):
        # each entry: (code, name, [rings], (minx, miny, maxx, maxy))
        self._entries = []
        self._by_name = {}
        for code, name, rings in features:
            xs = [x for r in rings for x, _ in r]
            ys = [y for r in rings for _, y in r]
            bbox = (min(xs), min(ys), max(xs), max(ys))
            self._entries.append((code, name, rings, bbox))
            self._by_name[_norm(name)] = code

    def point(self, lon, lat):
        """Return the LAD code containing (lon, lat), or None."""
        if lon is None or lat is None:
            return None
        for code, _name, rings, (minx, miny, maxx, maxy) in self._entries:
            if lon < minx or lon > maxx or lat < miny or lat > maxy:
                continue
            if any(_in_ring(lon, lat, r) for r in rings):
                return code
        return None

    def code_for_name(self, name):
        """Return the LAD code for an authority name, or None.

        Tries the exact normalised name, then a stripped variant with common
        local-authority prefixes/suffixes removed, so "London Borough of
        Hammersmith & Fulham" or "Rotherham Metropolitan Borough Council" match
        the bare district names in the boundary set."""
        if not name:
            return None
        return self._by_name.get(_norm(name)) or self._by_name.get(_strip_la(name))


def _norm(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return " ".join(s.lower().replace("&", "and").split())


# Prefixes/suffixes that decorate an authority name but are not part of the
# district's own name in the ONS boundary set.
_LA_PREFIXES = ("london borough of ", "royal borough of ", "city of ",
                "borough of ", "county of ")
_LA_SUFFIXES = (" metropolitan borough council", " metropolitan district council",
                " borough council", " district council", " city council",
                " county council", " councils", " council", " metropolitan borough",
                " borough", " (b)", " (met b)")


def _strip_la(name):
    s = _norm(name)
    for p in _LA_PREFIXES:
        if s.startswith(p):
            s = s[len(p):]
    for suf in _LA_SUFFIXES:
        if s.endswith(suf):
            s = s[: -len(suf)]
            break
    return s.strip()


def _in_ring(x, y, ring):
    """Even-odd ray cast: is (x, y) inside this ring?"""
    inside = False
    n = len(ring)
    j = n - 1
    for i in range(n):
        xi, yi = ring[i]
        xj, yj = ring[j]
        if (yi > y) != (yj > y):
            xint = (xj - xi) * (y - yi) / (yj - yi) + xi
            if x < xint:
                inside = not inside
        j = i
    return inside


def _rings(geom):
    """Exterior rings of a Polygon or MultiPolygon, as lists of (lon, lat)."""
    t = geom["type"]
    if t == "Polygon":
        return [[(pt[0], pt[1]) for pt in geom["coordinates"][0]]]
    if t == "MultiPolygon":
        return [[(pt[0], pt[1]) for pt in poly[0]] for poly in geom["coordinates"]]
    return []


def load(path: str = BOUNDARIES) -> Lads:
    with open(path) as f:
        gj = json.load(f)
    feats = []
    for ft in gj["features"]:
        p = ft["properties"]
        code = p.get("LAD24CD") or p.get("c")
        name = p.get("LAD24NM") or p.get("n")
        rings = _rings(ft["geometry"])
        if code and rings:
            feats.append((code, name, rings))
    return Lads(feats)
