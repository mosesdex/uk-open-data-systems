"""One command that runs the whole platform.

Fetch, load, build every system, run the chains, publish for the prototype.
Each stage reports what it did and what it could not do; a stage that fails is
recorded and the run continues, because a platform that stops at the first
unreachable publisher is useless for a corpus this size.
"""
from __future__ import annotations

import traceback
from dataclasses import dataclass, field
from pathlib import Path

import duckdb


@dataclass
class StageResult:
    name: str
    ok: bool
    detail: str
    seconds: float = 0.0


@dataclass
class RunReport:
    stages: list[StageResult] = field(default_factory=list)

    @property
    def failed(self) -> list[StageResult]:
        return [s for s in self.stages if not s.ok]

    @property
    def ok(self) -> bool:
        return not self.failed


def _stage(report: RunReport, name: str, fn):
    import time
    t0 = time.monotonic()
    try:
        detail = fn() or ""
        report.stages.append(StageResult(name, True, str(detail), time.monotonic() - t0))
    except Exception as exc:                      # noqa: BLE001 - deliberate
        report.stages.append(StageResult(
            name, False, f"{type(exc).__name__}: {exc}"[:200], time.monotonic() - t0))
    return report.stages[-1]


def build_everything(con: duckdb.DuckDBPyConnection, bronze: Path) -> RunReport:
    """Load and build every system whose inputs are present."""
    from .systems import (catchment, watchman, bellwether, bulwark, ledger,
                          baseline, sentinel, highwater, plumbline, sightline,
                          lastmile, compass, junction)
    from . import load as loader, chains, publish

    r = RunReport()
    B = bronze

    _stage(r, "place spine", lambda: (
        f"{loader.load_codepoint(con, B / 'os_code_point_open.zip'):,} postcodes, "
        f"{loader.load_lad_boundaries(con, B / 'ons_lad_boundaries.geojson')} districts"))

    def _catchment():
        c = catchment.build(con, B / "gias_establishments.csv")
        return f"{c.resolved:,} of {c.total:,} schools resolved"
    _stage(r, "catchment", _catchment)

    def _bellwether():
        c = bellwether.load_care(con, B / "cqc_hsca_locations.ods")
        bellwether.build(con); bellwether.build_groups(con)
        return f"{c.rows:,} care locations, {c.identified_pct:.1f}% identified"
    _stage(r, "bellwether", _bellwether)

    def _bulwark():
        n = bulwark.load(con, B / "ea_aims_defences.json"); bulwark.build(con)
        return f"{n:,} flood defences"
    _stage(r, "bulwark", _bulwark)

    def _ledger():
        c = ledger.load(con, B / "planning_developer_agreement_contribution.json",
                        B / "planning_developer_agreement_transaction.json",
                        B / "planning_local_authority.json")
        ledger.build(con)
        return f"{c.contributions:,} contributions, {c.with_geometry} located"
    _stage(r, "ledger", _ledger)

    def _baseline():
        c = baseline.load(con, B / "edm_annual.zip", 2025); baseline.build(con)
        return f"{c.outlets:,} storm overflows"
    _stage(r, "baseline", _baseline)

    def _sentinel():
        paths = [p for p in (B / "contracts_finder_bulk.json", B / "find_a_tender.json")
                 if p.exists()]
        c = sentinel.load(con, *paths); sentinel.build(con)
        return f"{c.awards:,} awards, {c.pct(c.suppliers_identified, c.awards):.1f}% identified"
    _stage(r, "sentinel", _sentinel)

    def _watchman():
        paths = [p for p in (B / "contracts_finder_bulk.json", B / "find_a_tender.json")
                 if p.exists()]
        st = watchman.register_suppliers(con, watchman.load_suppliers(*paths))
        gaz = B / "gazette_insolvency_bulk.json"
        gaz = gaz if gaz.exists() else B / "gazette_insolvency.json"
        exposures = watchman.check_against_register(con, gaz)
        rep = watchman.Report(0, 0, st["rows"], st["distinct_numbers"], exposures, [])
        watchman.write(con, rep)
        return f"register {st['rows']:,} awards, {len(exposures)} exposures"
    _stage(r, "watchman", _watchman)

    def _highwater():
        c = highwater.load(con, B / "ea_objections.ods"); highwater.build(con)
        return f"{c.rows:,} objections, {c.pct(c.with_outcome):.1f}% with an outcome"
    _stage(r, "highwater", _highwater)

    def _plumbline():
        c = plumbline.load(con, B / "planning_ps2.csv"); plumbline.build(con)
        return f"{c.rows:,} rows, {c.authorities} authorities"
    _stage(r, "plumbline", _plumbline)

    def _sightline():
        n = sightline.load_water_quality(con, B / "ea_objections.ods"); sightline.build(con)
        return f"{n} water quality objections"
    _stage(r, "sightline", _sightline)

    def _lastmile():
        zips = sorted(B.glob("bduk_*.zip"))
        n = lastmile.load_premises(con, *zips)
        m = lastmile.load_new_builds(con, B / "ppd_monthly.csv")
        lastmile.build(con)
        return f"{n:,} premises, {m:,} new-build sales"
    _stage(r, "lastmile", _lastmile)

    def _compass():
        c = compass.load(con, B / "dfe_sen_provision.csv"); compass.build(con)
        return f"{c.authorities} authorities over {c.years} years"
    _stage(r, "compass", _compass)

    def _junction():
        import requests, time
        sess = requests.Session(); sess.trust_env = False
        sess.headers.update({"User-Agent": "groundtruth/0.1"})
        states = []
        for op, base, ds in junction.REGISTERS:
            exp = sess.get(junction.EXPORT.format(base=base, ds=ds), timeout=240)
            fields, rows = (junction.parse_export(exp.content.decode("utf-8-sig", "replace"))
                            if exp.status_code == 200 else ([], []))
            meta = sess.get(f"{base}/api/explore/v2.1/catalog/datasets/{ds}", timeout=120)
            rc = (meta.json().get("metas", {}).get("default", {}).get("records_count")
                  if meta.status_code == 200 else None)
            states.append(junction.RegisterState(op, ds, exp.status_code,
                                                 tuple(fields), len(rows), rc))
            time.sleep(1)
        junction.load(con, states)
        g = junction.catalogue_gap(states)
        return f"{g['returned']:,} of {g['advertised']:,} records served"
    _stage(r, "junction", _junction)

    _stage(r, "chains", lambda: f"{sum(c.systems_touched for c in chains.run_all(con))} system responses")
    return r
