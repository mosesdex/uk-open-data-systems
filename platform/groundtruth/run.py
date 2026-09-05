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


def _has(con, schema, table) -> bool:
    return con.execute("SELECT count(*) FROM information_schema.tables "
                       "WHERE table_schema=? AND table_name=?", [schema, table]).fetchone()[0] > 0


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
        cap = B / "dfe_school_capacity.csv"
        extra = ""
        if cap.exists():
            catchment.load_capacity(con, cap); catchment.build_trend(con)
            yrs = catchment.trend_summary(con)[0]
            extra = f", {yrs}-year capacity trend"
        return f"{c.resolved:,} of {c.total:,} schools resolved{extra}"
    _stage(r, "catchment", _catchment)

    def _bellwether():
        c = bellwether.load_care(con, B / "cqc_hsca_locations.ods")
        bellwether.build(con); bellwether.build_groups(con)
        return (f"{c.rows:,} care locations, {c.identified_pct:.1f}% identified "
                f"(+{c.via_register:,} company, +{c.via_charity:,} charity)")
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
        # The agreements and applications are what make a location recoverable at
        # all. Both are optional: a run without them reports the location gap
        # unchanged rather than failing, which is how every other stage behaves.
        located = None
        agreements, applications = (B / "developer_agreements.json",
                                    B / "planning_applications.json")
        if agreements.exists() and applications.exists():
            ledger.load_agreements(con, agreements)
            ledger.load_applications(con, applications)
            try:
                from . import spatial
                lads = spatial.load()
            except Exception:
                lads = None
            located = ledger.locate(con, lads=lads)
        tail = ""
        if located and located.get("available"):
            tail = (f", {located['located']:,} recovered via agreement "
                    f"({located['located_pct']}%)")
        return (f"{c.contributions:,} contributions, "
                f"{c.with_geometry} carrying a location{tail}")
    _stage(r, "ledger", _ledger)

    def _baseline():
        # Load every annual return present (layouts differ by year; the
        # header-driven loader handles them). 2020's format is incompatible.
        loaded = []
        for y in (2021, 2022, 2023, 2024, 2025):
            zp = B / f"edm_annual_{y}.zip"
            if zp.exists():
                baseline.load_multi(con, zp, y); loaded.append(y)
        if not loaded:
            baseline.load(con, B / "edm_annual.zip", 2025)
        c = None
        rain = B / "rainfall_annual_2025.json"
        if rain.exists():
            baseline.load_rainfall(con, rain)
        baseline.build(con)
        latest = con.execute("SELECT max(year), count(*) FROM gold.baseline_outlet "
                             "WHERE year=(SELECT max(year) FROM gold.baseline_outlet)").fetchone()
        yrs = con.execute("SELECT count(DISTINCT year) FROM gold.baseline_outlet").fetchone()[0]
        return f"{latest[1]:,} storm overflows ({latest[0]}), {yrs}-year trend"
    _stage(r, "baseline", _baseline)

    def _sentinel():
        paths = [p for p in (B / "contracts_finder_bulk.json", B / "find_a_tender.json")
                 if p.exists()]
        c = sentinel.load(con, *paths); sentinel.build(con)
        return (f"{c.awards:,} awards, {c.pct(c.suppliers_identified, c.awards):.1f}% "
                f"identified (+{c.identified_via_register:,} via the register)")
    _stage(r, "sentinel", _sentinel)

    def _watchman():
        paths = [p for p in (B / "contracts_finder_bulk.json", B / "find_a_tender.json")
                 if p.exists()]
        sups, gained = watchman.enrich_from_register(con, watchman.load_suppliers(*paths))
        st = watchman.register_suppliers(con, sups)
        st["from_register"] = gained
        gaz = B / "gazette_insolvency_bulk.json"
        gaz = gaz if gaz.exists() else B / "gazette_insolvency.json"
        exposures = watchman.check_against_register(con, gaz)
        rep = watchman.Report(0, 0, st["rows"], st["distinct_numbers"], exposures, [])
        watchman.write(con, rep)
        d = watchman.check_distress(con)
        return (f"register {st['rows']:,} awards, {len(exposures)} notice exposures, "
                f"{d} status-distress exposures")
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
        wq = B / "planit_planning_wq.json"
        extra = ""
        if wq.exists():
            sightline.load_planit(con, wq); sightline.build_planit(con)
            apps = sightline.planit_summary(con)[0]
            extra = f", {apps:,} PlanIt applications"
        return f"{n} water quality objections{extra}"
    _stage(r, "sightline", _sightline)

    def _lastmile():
        zips = sorted(B.glob("bduk_*.zip"))
        n = lastmile.load_premises(con, *zips)
        # Full price-paid history when available, restricted to homes sold new in
        # the last five years -- the population the connectivity duty covers.
        full = B / "hmlr_price_paid_full.csv"
        if full.exists():
            m = lastmile.load_new_builds(con, full, since="2021-01-01")
        else:
            m = lastmile.load_new_builds(con, B / "ppd_monthly.csv")
        lastmile.build(con)
        return f"{n:,} premises, {m:,} recent new-build sales"
    _stage(r, "lastmile", _lastmile)

    def _compass():
        # Births feed the cohort join; load them first if present.
        births = B / "ons_births_area.csv"
        if births.exists():
            loader.load_births(con, births)
        c = compass.load(con, B / "dfe_sen_provision.csv"); compass.build(con)
        cohort = con.execute("SELECT count(*) FROM gold.compass_cohort").fetchone()[0] \
            if _has(con, "gold", "compass_cohort") else 0
        return f"{c.authorities} authorities over {c.years} years, {cohort} with a birth cohort"
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

    def _entity():
        from .systems import entity
        entity.build(con)
        e, ic, ip, cross = entity.summary(con)
        return f"{e:,} organisations, {cross} cross-system"
    _stage(r, "entity", _entity)

    _stage(r, "chains", lambda: f"{sum(c.systems_touched for c in chains.run_all(con))} system responses")
    return r
