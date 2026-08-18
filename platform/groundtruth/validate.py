"""Validating the place spine against a publisher's own coordinates.

The spine resolves a postcode to a centroid. GIAS publishes both a postcode and
a coordinate for the same school, so the two can be compared directly. That
gives a measured accuracy figure rather than an asserted one -- and it is the
number to quote when someone asks how good "resolved" actually is.
"""
from __future__ import annotations

import csv
import io
import math
from dataclasses import dataclass
from pathlib import Path

import duckdb

from . import place
from .geo import bng_to_wgs84


@dataclass(frozen=True)
class Validation:
    total: int
    resolved: int
    compared: int
    median_m: float
    p75_m: float
    p90_m: float
    p99_m: float
    within_100m: float
    within_500m: float

    @property
    def resolve_rate(self) -> float:
        return 100 * self.resolved / self.total if self.total else 0.0


def validate_against_gias(con: duckdb.DuckDBPyConnection, csv_path: Path) -> Validation:
    rows = list(csv.DictReader(io.open(csv_path, encoding="latin-1")))
    live = [r for r in rows if r.get("EstablishmentStatus (name)") == "Open"]

    resolved = 0
    errs: list[float] = []
    for r in live:
        ref = place.resolve_postcode(con, r.get("Postcode", ""))
        if not ref.resolved:
            continue
        resolved += 1
        e, n = r.get("Easting", "").strip(), r.get("Northing", "").strip()
        if not (e and n):
            continue
        try:
            tlat, tlon = bng_to_wgs84(float(e), float(n))
        except ValueError:
            continue
        dlat = (ref.latitude - tlat) * 111_320
        dlon = (ref.longitude - tlon) * 111_320 * math.cos(math.radians(tlat))
        errs.append(math.hypot(dlat, dlon))

    errs.sort()
    q = lambda p: errs[int(len(errs) * p)] if errs else float("nan")
    share = lambda m: 100 * sum(1 for e in errs if e <= m) / len(errs) if errs else 0.0
    return Validation(len(live), resolved, len(errs), q(.5), q(.75), q(.90), q(.99),
                      share(100), share(500))
