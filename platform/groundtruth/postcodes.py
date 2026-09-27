"""The postcode index the browser can afford to read.

silver.place_postcode holds 1,749,109 rows. Shipping it would be absurd, and
shipping nothing is why the front page has to tell a reader that a postcode is
not matched. A sector, the outcode plus the first digit of the incode, is the
compromise that was measured rather than guessed:

    outcode  SW1A     2,223 English keys, 92.42% placed by the dominant rule
    sector   SW1A 1   9,129 English keys, 96.45% placed by the dominant rule

The sector index wins and is what this builds. The remaining 3.55% is not
absorbed by guessing: a sector that spans more than one district ships all of
them, dominant first, and the interface asks which one rather than being
quietly wrong for one reader in twenty-eight.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone

import duckdb


def sector_index(con: duckdb.DuckDBPyConnection) -> dict:
    """Sector to districts, dominant first, with the accuracy it achieves."""
    rows = con.execute("""
        SELECT postcode_key, lad_code
        FROM silver.place_postcode
        WHERE lad_code IS NOT NULL AND length(postcode_key) >= 5
    """).fetchall()

    counts: dict[str, Counter] = defaultdict(Counter)
    for key, lad in rows:
        # postcode_key is the postcode with the space removed, so the incode is
        # always the last three characters and the sector is everything before
        # the final two.
        counts[key[:-2]][lad] += 1

    sectors = {
        sector: [lad for lad, _ in c.most_common()]
        for sector, c in counts.items()
    }
    total = sum(sum(c.values()) for c in counts.values())
    dominant = sum(max(c.values()) for c in counts.values())

    return {
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "postcodes": total,
        "sectors_total": len(sectors),
        "ambiguous_sectors": sum(1 for c in counts.values() if len(c) > 1),
        "dominant_accuracy_pct": round(100 * dominant / total, 2) if total else 0.0,
        "sectors": dict(sorted(sectors.items())),
    }
