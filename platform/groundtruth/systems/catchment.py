"""Catchment -- school place planning at the geography that matters.

The defect: capital is allocated per pupil planning area, but that geography is
published nowhere, so surplus in one part of a district and shortage in another
cancel out in the published figures and nobody sees either.

What this builds, from GIAS and the place spine:

  * every open school resolved to a district, with the tier recorded
  * capacity, pupils and utilisation per district
  * the surplus/shortage picture, and where it is masked by aggregation

Every output carries its own coverage. A utilisation figure computed over the
70% of schools that published a capacity is not a district's utilisation, and
saying so is the difference between a statistic and a guess.
"""
from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from pathlib import Path

import duckdb

from .. import place

OPEN = "Open"

# Special schools, pupil referral units and alternative provision report
# "capacity" on a different basis from mainstream schools: 12.5% of PRUs and
# 5.1% of special academies record more pupils than places, against 0.1-0.4%
# of mainstream schools. Averaging the two together produces a utilisation
# figure that means nothing, so they are counted separately throughout.
SPECIAL_MARKERS = ("special", "pupil referral", "alternative provision",
                   "hospital school", "secure unit")


def is_mainstream(establishment_type: str) -> bool:
    t = (establishment_type or "").lower()
    return not any(m in t for m in SPECIAL_MARKERS)


@dataclass(frozen=True)
class Coverage:
    total: int
    resolved: int
    with_capacity: int

    @property
    def resolved_pct(self) -> float:
        return 100 * self.resolved / self.total if self.total else 0.0

    @property
    def capacity_pct(self) -> float:
        return 100 * self.with_capacity / self.total if self.total else 0.0


def _int(v) -> int | None:
    try:
        n = int(float(v))
        return n if n > 0 else None
    except (TypeError, ValueError):
        return None


def build(con: duckdb.DuckDBPyConnection, gias_csv: Path) -> Coverage:
    """Resolve schools to places and write the gold tables."""
    rows = list(csv.DictReader(io.open(gias_csv, encoding="latin-1")))
    live = [r for r in rows if r.get("EstablishmentStatus (name)") == OPEN]

    records = []
    resolved = with_capacity = 0
    for r in live:
        ref = place.resolve(con, uprn=r.get("UPRN") or None,
                            postcode=r.get("Postcode") or None)
        cap, pup = _int(r.get("SchoolCapacity")), _int(r.get("NumberOfPupils"))
        if ref.resolved:
            resolved += 1
        if cap:
            with_capacity += 1
        records.append((
            r.get("URN", ""), r.get("EstablishmentName", ""),
            r.get("TypeOfEstablishment (name)", ""),
            r.get("PhaseOfEducation (name)", ""),
            r.get("LA (name)", ""),
            ref.lad_code, ref.tier, ref.confidence,
            ref.latitude, ref.longitude,
            cap, pup,
            (r.get("Trusts (code)") or "").strip() or None,
            (r.get("Trusts (name)") or "").strip() or None,
            is_mainstream(r.get("TypeOfEstablishment (name)", "")),
        ))

    con.execute("DROP TABLE IF EXISTS gold.catchment_school")
    con.execute("""
        CREATE TABLE gold.catchment_school (
          urn VARCHAR, name VARCHAR, type VARCHAR, phase VARCHAR,
          la_name VARCHAR, lad_code VARCHAR,
          place_tier VARCHAR, place_confidence DOUBLE,
          latitude DOUBLE, longitude DOUBLE,
          capacity INTEGER, pupils INTEGER,
          trust_code VARCHAR, trust_name VARCHAR,
          mainstream BOOLEAN
        )""")
    con.executemany(
        "INSERT INTO gold.catchment_school VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", records)

    # District picture. Utilisation is computed only over schools that published
    # both numbers, and the share doing so travels with the figure.
    con.execute("DROP TABLE IF EXISTS gold.catchment_district")
    con.execute("""
        CREATE TABLE gold.catchment_district AS
        SELECT
          s.lad_code,
          COALESCE(l.lad_name, 'unknown')                       AS lad_name,
          count(*)                                              AS schools,
          count(*) FILTER (WHERE capacity IS NOT NULL
                             AND pupils IS NOT NULL)            AS schools_measured,
          sum(capacity) FILTER (WHERE pupils IS NOT NULL)       AS capacity,
          sum(pupils)   FILTER (WHERE capacity IS NOT NULL)     AS pupils,
          round(100.0 * sum(pupils)   FILTER (WHERE capacity IS NOT NULL)
                      / nullif(sum(capacity) FILTER (WHERE pupils IS NOT NULL), 0), 1)
                                                                AS utilisation_pct,
          round(100.0 * count(*) FILTER (WHERE capacity IS NOT NULL
                                           AND pupils IS NOT NULL) / count(*), 1)
                                                                AS measured_pct,
          round(100.0 * count(*) FILTER (WHERE trust_code IS NOT NULL) / count(*), 1)
                                                                AS entity_resolved_pct
        FROM gold.catchment_school s
        LEFT JOIN silver.lad l ON l.lad_code = s.lad_code
        WHERE s.lad_code IS NOT NULL AND s.mainstream
        GROUP BY s.lad_code, l.lad_name
        HAVING count(*) >= 3
        ORDER BY utilisation_pct DESC NULLS LAST
    """)
    # Specialist provision, reported separately rather than blended away.
    con.execute("DROP TABLE IF EXISTS gold.catchment_specialist")
    con.execute("""
        CREATE TABLE gold.catchment_specialist AS
        SELECT
          s.lad_code,
          COALESCE(l.lad_name, 'unknown')                    AS lad_name,
          count(*)                                           AS settings,
          sum(capacity)  FILTER (WHERE pupils IS NOT NULL)   AS capacity,
          sum(pupils)    FILTER (WHERE capacity IS NOT NULL) AS pupils,
          round(100.0 * sum(pupils)   FILTER (WHERE capacity IS NOT NULL)
                      / nullif(sum(capacity) FILTER (WHERE pupils IS NOT NULL), 0), 1)
                                                             AS utilisation_pct,
          count(*) FILTER (WHERE capacity IS NOT NULL AND pupils IS NOT NULL
                             AND pupils > capacity)          AS over_capacity
        FROM gold.catchment_school s
        LEFT JOIN silver.lad l ON l.lad_code = s.lad_code
        WHERE s.lad_code IS NOT NULL AND NOT s.mainstream
        GROUP BY s.lad_code, l.lad_name
        HAVING count(*) >= 3
        ORDER BY utilisation_pct DESC NULLS LAST
    """)
    return Coverage(len(live), resolved, with_capacity)


def pressure(con: duckdb.DuckDBPyConnection, limit: int = 10):
    """Districts under the most and least pressure, coverage attached."""
    return con.execute(f"""
        SELECT lad_name, schools, utilisation_pct, measured_pct,
               capacity - pupils AS spare_places
        FROM gold.catchment_district
        WHERE utilisation_pct IS NOT NULL AND measured_pct >= 60
        ORDER BY utilisation_pct DESC LIMIT {limit}
    """).fetchall()


def masking(con: duckdb.DuckDBPyConnection, limit: int = 10):
    """Where a district average hides both a full school and an empty one.

    This is the effect Catchment exists to expose: aggregation cancels the two
    out, so neither the surplus nor the shortage appears in published figures.
    """
    return con.execute(f"""
        WITH s AS (
          SELECT lad_code, urn, name,
                 100.0 * pupils / nullif(capacity, 0) AS util
          FROM gold.catchment_school
          WHERE capacity IS NOT NULL AND pupils IS NOT NULL AND capacity >= 50
            AND mainstream
        )
        SELECT d.lad_name,
               d.utilisation_pct                       AS district_average,
               round(min(s.util), 1)                   AS emptiest_school,
               round(max(s.util), 1)                   AS fullest_school,
               round(max(s.util) - min(s.util), 1)     AS spread,
               count(*)                                AS schools_compared
        FROM s JOIN gold.catchment_district d USING (lad_code)
        GROUP BY d.lad_name, d.utilisation_pct
        HAVING count(*) >= 10 AND min(s.util) < 75 AND max(s.util) > 100
        ORDER BY spread DESC LIMIT {limit}
    """).fetchall()
