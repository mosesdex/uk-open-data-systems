"""Command line.

    gt sources                 list the registry
    gt fetch <id> [...]        fetch one or more sources anonymously
    gt fetch --role place_spine
    gt status                  last outcome per source
"""
from __future__ import annotations

import argparse
import sys
import uuid
from datetime import datetime, date
from pathlib import Path

from . import sources as S
from . import store
from .fetch import fetch
from .resolve import resolve, ResolutionError
from . import place as place_mod
from . import load as load_mod
import requests

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DB = DATA / "groundtruth.duckdb"
BRONZE = DATA / "bronze"

GREEN, RED, DIM, BOLD, OFF = "\033[32m", "\033[31m", "\033[2m", "\033[1m", "\033[0m"


def _resolve_url(src: S.Source) -> str | None:
    """Concrete URL for today, or None if it cannot be determined."""
    try:
        return resolve(src)
    except (ResolutionError, requests.RequestException) as exc:
        print(f"{RED}cannot resolve{OFF} {src.id}: {exc}"[:200])
        return None


def cmd_sources(args) -> int:
    rows = S.REGISTRY
    if args.role:
        rows = [s for s in rows if s.role == args.role]
    print(f"{BOLD}{'ID':<32}{'ROLE':<14}{'CADENCE':<12}PUBLISHER{OFF}")
    for s in rows:
        mark = f"{RED}blocked{OFF}" if s.blocked else f"{GREEN}open{OFF}"
        print(f"{s.id:<32}{s.role:<14}{s.cadence:<12}{s.publisher}  [{mark}]")
    n_blocked = sum(1 for s in rows if s.blocked)
    print(f"\n{len(rows)} sources, {len(rows)-n_blocked} admissible, {n_blocked} blocked")
    return 0


def _existing_file(src):
    """The file this source already has, if it looks usable."""
    from . import admin as _admin
    name = _admin._on_disk(BRONZE, src.id)
    if not name:
        return None
    p = BRONZE / name
    if p.stat().st_size < 1024:
        return None
    if p.suffix == ".zip":
        import zipfile
        if not zipfile.is_zipfile(p):
            return None                      # truncated: fetch it again
    return p


def cmd_fetch(args) -> int:
    if args.role:
        targets = [s for s in S.by_role(args.role) if s.admissible]
    elif args.all:
        targets = list(S.admissible())
    else:
        targets = [S.get(i) for i in args.ids]
    if not targets:
        print("nothing to fetch", file=sys.stderr)
        return 2

    # Re-downloading a complete 900 MB archive to discover it has not changed is
    # not a health check, it is an hour. --if-missing skips sources whose file is
    # already on disk and readable.
    if args.if_missing:
        kept = []
        for src in targets:
            existing = _existing_file(src)
            if existing:
                print(f"  {src.id:<32}{DIM}already on disk, {existing.stat().st_size/1e6:.1f} MB{OFF}")
            else:
                kept.append(src)
        targets = kept
        if not targets:
            print("\nnothing missing")
            return 0

    run_id = uuid.uuid4().hex[:12]
    print(f"{DIM}run {run_id} -- {len(targets)} source(s), anonymous{OFF}\n")
    failures = 0
    skipped = 0

    def _record(result):
        # Hold the database only for the instant it takes to log one fetch, so a
        # multi-gigabyte download never locks another fetch out of the DB.
        for attempt in range(30):
            try:
                con = store.connect(DB)
                store.record_fetch(con, run_id, result)
                fresh = (store.changed_since_last(con, result.source_id, result.sha256)
                         if result.ok and result.sha256 else result.ok)
                con.close()
                return fresh
            except Exception:
                import time as _t; _t.sleep(2)
        return result.ok

    for src in targets:
        # Refuse to overwrite real data with a discovery endpoint's response.
        if getattr(src, "needs_backfill", None):
            print(f"  {src.id:<32}{DIM}skipped -- its URL is an index, not the data. "
                  f"Use: gt backfill --only {src.needs_backfill}{OFF}")
            skipped += 1
            continue
        print(f"  {src.id:<32}", end="", flush=True)
        url = _resolve_url(src)
        if url is None:
            failures += 1
            continue
        res = fetch(src, BRONZE, max_bytes=args.max_bytes,
                    url_override=url, timeout=args.timeout)
        fresh = _record(res)
        if res.ok:
            mb = res.bytes_len / 1e6
            tag = "new content" if fresh else "unchanged"
            print(f"{GREEN}HTTP 200{OFF}  {mb:>8.1f} MB  {res.elapsed_ms:>6} ms  {DIM}{tag}{OFF}")
        else:
            failures += 1
            label = f"HTTP {res.http_status}" if res.http_status else "no response"
            print(f"{RED}{label:<8}{OFF}  {DIM}{res.note[:66]}{OFF}")

    fetched = len(targets) - failures - skipped
    tail = f", {skipped} skipped" if skipped else ""
    print(f"\n{fetched} ok, {failures} failed{tail}")
    return 1 if failures and args.strict else 0


def cmd_load(args) -> int:
    """Expand bronze downloads into silver tables."""
    con = store.connect(DB)
    steps = [
        ("postcodes",  lambda: load_mod.load_codepoint(con, BRONZE / "os_code_point_open.zip")),
        ("boundaries", lambda: load_mod.load_lad_boundaries(con, BRONZE / "ons_lad_boundaries.geojson")),
        ("properties", lambda: load_mod.load_uprn(con, BRONZE / "os_open_uprn.zip")),
        # Corroboration sources: each is a second route to something the
        # platform already publishes, so the cross-checks have something to
        # compare against instead of asserting consistency untested.
        ("hydrology",  lambda: load_mod.load_hydrology_stations(con, BRONZE / "ea_hydrology.json")),
        ("neso",       lambda: load_mod.load_neso_tec(con, BRONZE / "neso_tec.json")),
        ("nhs orgs",   lambda: load_mod.load_nhs_ods(con, BRONZE / "nhs_ods.json")),
    ]
    if args.full:
        steps += [
            ("uprn->street",   lambda: load_mod.load_crosswalk(
                con, BRONZE / "os_lids_uprn_usrn.zip", "lids_uprn_usrn")),
            ("uprn->building", lambda: load_mod.load_crosswalk(
                con, BRONZE / "os_lids_uprn_toid.zip", "lids_uprn_toid")),
            ("companies",      lambda: load_mod.load_companies(
                con, BRONZE / "companies_house_bulk.zip")),
            ("psc",            lambda: load_mod.load_psc(con, BRONZE)),
            ("charities",      lambda: load_mod.load_charities(
                con, BRONZE / "charity_register.zip")),
            ("births",         lambda: load_mod.load_births(
                con, BRONZE / "ons_births_area.csv")),
        ]
    for name, fn in steps:
        print(f"  {name:<12}", end="", flush=True)
        try:
            print(f"{GREEN}{fn():>12,}{OFF} rows")
        except load_mod.LoadError as exc:
            print(f"{RED}skipped{OFF}  {DIM}{exc}{OFF}"[:150])
    con.close()
    return 0


def cmd_place(args) -> int:
    con = store.connect(DB)
    for raw in args.postcodes:
        ref = place_mod.resolve_postcode(con, raw)
        if ref.resolved:
            print(f"  {raw:<10} {GREEN}{ref.tier}{OFF}  conf {ref.confidence:.2f}  "
                  f"{ref.latitude:.5f}, {ref.longitude:.5f}  lad={ref.lad_code}  {DIM}{ref.note}{OFF}")
        else:
            print(f"  {raw:<10} {RED}unresolved{OFF}  {DIM}{ref.note}{OFF}")
    con.close()
    return 0


def cmd_coverage(args) -> int:
    con = store.connect(DB)
    cov = place_mod.coverage(con)
    print(f"{BOLD}place spine{OFF}")
    if not cov["tiers"]:
        print("  nothing loaded yet -- run: gt load")
    for tier, info in cov["tiers"].items():
        bits = "  ".join(f"{k}={v:,}" if isinstance(v, int) else f"{k}={v}"
                         for k, v in info.items())
        print(f"  {tier:<10} {bits}")
    print()
    print(f"  {DIM}Code-Point Open covers Great Britain, not the UK: "
          f"Northern Ireland postcodes do not resolve.{OFF}")
    if args.validate:
        from .validate import validate_against_gias
        gias = BRONZE / "gias_establishments.csv"
        if not gias.exists():
            print()
            print(f"  {RED}no GIAS extract to validate against{OFF}"
                  f" -- run: gt fetch gias_establishments")
            con.close(); return 1
        print()
        print(f"{BOLD}validation against the publisher's own coordinates{OFF}")
        v = validate_against_gias(con, gias)
        print(f"  establishments        {v.total:>10,}")
        print(f"  resolved by postcode  {v.resolved:>10,}  ({v.resolve_rate:.1f}%)")
        print(f"  median error          {v.median_m:>10.0f} m")
        print(f"  90th percentile       {v.p90_m:>10.0f} m")
        print(f"  within 100 m          {v.within_100m:>10.1f}%")
        print(f"  within 500 m          {v.within_500m:>10.1f}%")
    con.close()
    return 0


def cmd_catchment(args) -> int:
    from .systems import catchment as C
    con = store.connect(DB)
    gias = BRONZE / "gias_establishments.csv"
    if not gias.exists():
        print(f"{RED}no school register{OFF} -- run: gt fetch gias_establishments")
        con.close(); return 1
    cov = C.build(con, gias)
    print(f"{BOLD}Catchment{OFF}")
    print(f"  open schools          {cov.total:>9,}")
    print(f"  resolved to a place   {cov.resolved:>9,}  ({cov.resolved_pct:.1f}%)")
    print(f"  published a capacity  {cov.with_capacity:>9,}  ({cov.capacity_pct:.1f}%)")

    cap = BRONZE / "dfe_school_capacity.csv"
    if cap.exists():
        rows = C.load_capacity(con, cap)
        C.build_trend(con)
        yrs, first, last, fp, lp = C.trend_summary(con)
        print(f"  capacity time series  {rows:>9,}  ({yrs} years, {first} to {last}: {fp}% -> {lp}%)")
    else:
        print(f"  {DIM}no capacity time series -- run: gt fetch dfe_school_capacity{OFF}")

    m = con.execute("""SELECT count(*), sum(pupils), sum(capacity),
        round(100.0*sum(pupils)/sum(capacity),1) FROM gold.catchment_district""").fetchone()
    sp = con.execute("""SELECT count(*), sum(pupils), sum(capacity),
        round(100.0*sum(pupils)/sum(capacity),1), sum(over_capacity)
        FROM gold.catchment_specialist""").fetchone()
    print()
    print(f"  {BOLD}mainstream{OFF}  {m[0]} districts  {m[1]:,} pupils / {m[2]:,} places  {m[3]}%")
    print(f"  {BOLD}specialist{OFF}  {sp[0]} districts  {sp[1]:,} pupils / {sp[2]:,} places  {sp[3]}%"
          f"  {RED}{sp[4]} settings over capacity{OFF}")

    print(f"\n{BOLD}where a district average hides both a full and an empty school{OFF}")
    for nm, avg, lo, hi, spread, n in C.masking(con, args.limit):
        print(f"  {nm[:26]:<28} average {avg:>5.1f}%   {DIM}range {lo:.1f}% to {hi:.1f}% over {n} schools{OFF}")
    con.close()
    return 0


def cmd_watchman(args) -> int:
    from .systems import watchman as W
    con = store.connect(DB)
    gaz = BRONZE / ("gazette_insolvency_bulk.json"
                    if (BRONZE / "gazette_insolvency_bulk.json").exists()
                    else "gazette_insolvency.json")
    ocds = [p for p in (BRONZE / "contracts_finder_bulk.json",
                        BRONZE / "contracts_finder.json",
                        BRONZE / "find_a_tender.json") if p.exists()]
    if not gaz.exists() or not ocds:
        print(f"{RED}missing feeds{OFF} -- run: gt fetch gazette_insolvency contracts_finder find_a_tender")
        con.close(); return 1

    stats = W.register_suppliers(con, W.load_suppliers(*ocds))
    print(f"{BOLD}supplier register{OFF}  {DIM}(cumulative -- the register is the asset){OFF}")
    print(f"  awards recorded        {stats['rows']:>9,}   {GREEN}+{stats['added']:,} this run{OFF}")
    print(f"  distinct companies     {stats['distinct_names']:>9,} by name, "
          f"{stats['distinct_numbers']:,} by company number")

    exposures = W.check_against_register(con, gaz)
    print(f"\n{BOLD}exposure{OFF}")
    print(f"  insolvency notices checked against the register")
    print(f"  exposures found        {len(exposures):>9,}")
    for e in exposures[:args.limit]:
        v = f"£{e.supplier.value:,.0f}" if e.supplier.value else "value not published"
        print(f"    {e.notice.title[:34]:<36} {e.supplier.buyer[:32]:<34} {v:>18}  {e.method} {e.confidence:.2f}")
    if not exposures:
        n = stats["distinct_names"] or 1
        need = 875 * n / 5_400_000
        print(f"    {DIM}none -- expected about {need:.1f} per three weeks at this register size.{OFF}")

    d = W.check_distress(con)
    if d:
        tot, care, contracts, _ = W.distress_summary(con)
        print(f"\n{BOLD}distress by company status{OFF}  {DIM}(public-role holders in liquidation/administration){OFF}")
        print(f"  exposures found        {tot:>9,}   {RED}{care} care providers, {contracts} contract suppliers{OFF}")
        for name, status, role, act in con.execute(
                """SELECT name, company_status, role, activity FROM gold.watchman_distress
                   ORDER BY activity DESC LIMIT ?""", [args.limit]).fetchall():
            print(f"    {name[:34]:<36} {status[:22]:<24} {role[:20]:<22} {act}")
    con.close()
    return 0


def cmd_entity(args) -> int:
    from .systems import entity as E
    con = store.connect(DB)
    E.build(con)
    ent, in_care, in_proc, cross = E.summary(con)
    print(f"{BOLD}Entity graph{OFF}  {DIM}the WHO spine{OFF}")
    print(f"  {ent:,} organisations  ·  {in_care:,} in care  ·  {in_proc:,} in procurement")
    print(f"  {BOLD}{cross:,}{OFF} appear in more than one system")
    con.close()
    return 0


def cmd_bellwether(args) -> int:
    from .systems import bellwether as BW
    con = store.connect(DB)
    ods = BRONZE / "cqc_hsca_locations.ods"
    if not ods.exists():
        print(f"{RED}no CQC extract{OFF} -- run: gt fetch cqc_hsca_locations")
        con.close(); return 1
    if args.reload or not con.execute(
            "SELECT count(*) FROM information_schema.tables "
            "WHERE table_schema='silver' AND table_name='care_location'").fetchone()[0]:
        cov = BW.load_care(con, ods)
        print(f"  loaded {cov.rows:,} locations, {cov.identified_pct:.1f}% with a company number")
    BW.build(con); BW.build_groups(con)

    unbranded = BW.unbranded_share(con)
    print(f"{BOLD}Bellwether{OFF}  {DIM}care sector{OFF}")
    print(f"  {DIM}group view cannot see {unbranded}% of beds -- those providers are unbranded{OFF}")
    print(f"\n{BOLD}systemically important groups{OFF}")
    print(f"  {'group':<30}{'LAs':>5}{'cos':>6}{'sites':>7}{'beds':>9}")
    for br, la, co, loc, bd in BW.systemic(con, args.limit):
        print(f"  {br.replace('BRAND ',''):<30}{la:>5}{co:>6}{loc:>7}{bd:>9,}")
    print(f"\n{BOLD}highest single-group share of an authority{OFF}  {DIM}(300+ beds){OFF}")
    for la, gn, br, loc, bd, lab, sh in con.execute("""
            SELECT * FROM gold.bellwether_group WHERE la_beds >= 300
            ORDER BY share_pct DESC LIMIT ?""", [args.limit]).fetchall():
        print(f"  {la[:24]:<26}{sh:>6.1f}%  {bd:>6,} of {lab:>7,}  {gn.replace('BRAND ','')[:30]}")
    con.close()
    return 0


def cmd_bulwark(args) -> int:
    from .systems import bulwark as BK
    con = store.connect(DB)
    src = BRONZE / "ea_aims_defences.json"
    if not src.exists():
        print(f"{RED}no AIMS extract{OFF} -- run: gt fetch ea_aims_defences")
        con.close(); return 1
    if args.reload or not con.execute(
            "SELECT count(*) FROM information_schema.tables WHERE table_schema='silver'"
            " AND table_name='flood_defence'").fetchone()[0]:
        print(f"  loaded {BK.load(con, src):,} assets")
    BK.build(con)
    c = BK.coverage(con)
    print(f"{BOLD}Bulwark{OFF}  {DIM}{c.total:,} flood defences in England{OFF}\n")
    print(f"  maintainer known   {c.maintainer_known:>8,}  {GREEN}{c.pct(c.maintainer_known):5.1f}%{OFF}"
          f"  {DIM}the operational question{OFF}")
    print(f"  owner known        {c.owner_known:>8,}  {RED}{c.pct(c.owner_known):5.1f}%{OFF}"
          f"  {DIM}the headline gap{OFF}")
    print(f"  condition graded   {c.graded:>8,}  {RED}{c.pct(c.graded):5.1f}%{OFF}"
          f"  {DIM}coverage of any condition statistic{OFF}")
    od = con.execute("""SELECT count(*) FROM silver.flood_defence
        WHERE next_inspection IS NOT NULL AND next_inspection < CURRENT_DATE""").fetchone()[0]
    print(f"\n  {BOLD}inspections overdue{OFF} {od:>7,} of {c.with_next_inspection:,} scheduled")
    print(f"\n{BOLD}by responsible maintainer{OFF}")
    for m, a, km, o in con.execute(
            "SELECT * FROM gold.bulwark_responsibility LIMIT ?", [args.limit]).fetchall():
        print(f"  {m[:40]:<42}{a:>7,} assets  {o:>6,} overdue ({100*o/a:4.1f}%)")
    print(f"\n{BOLD}authorities with most overdue{OFF}")
    for la, n, oldest, unm in BK.overdue(con, args.limit):
        print(f"  {la[:26]:<28}{n:>6,}  {DIM}oldest {oldest}{OFF}")
    con.close()
    return 0


def cmd_ledger(args) -> int:
    from .systems import ledger as L
    con = store.connect(DB)
    f = [BRONZE / n for n in ("planning_developer_agreement_contribution.json",
                              "planning_developer_agreement_transaction.json",
                              "planning_local_authority.json")]
    if not all(p.exists() for p in f):
        print(f"{RED}missing planning extracts{OFF}"); con.close(); return 1
    cov = L.load(con, *f); L.build(con)
    total, with_amount, rows = L.national_total(con)
    print(f"{BOLD}Ledger{OFF}  {DIM}developer contributions{OFF}\n")
    print(f"  contributions        {cov.contributions:>8,}")
    print(f"  stating an amount    {cov.with_amount:>8,}  {cov.pct(cov.with_amount):5.1f}%")
    print(f"  carrying a location  {cov.with_geometry:>8,}  {RED}{cov.pct(cov.with_geometry):5.1f}%{OFF}"
          f"  {DIM}no contribution record carries a point{OFF}")

    # The location the records lack is recoverable through the agreement's
    # planning-application reference -- for the few authorities that publish
    # their applications. Both halves are printed: the join that now works, and
    # the coverage that stops it mattering.
    loc = L.locate(con)
    if not loc["available"]:
        print(f"  recovered via planning application   {DIM}{loc['reason']}{OFF}")
    else:
        print(f"  recovered via agreement {loc['located']:>8,}  "
              f"{RED if loc['located_pct'] < 5 else ''}{loc['located_pct']:5.2f}%{OFF}"
              f"  {DIM}£{loc['amount_located']:,.0f} of £{loc['amount_total']:,.0f}{OFF}")
        gap = L.location_gap(con, limit=args.limit)
        if gap:
            print(f"\n{BOLD}unmappable, by authority{OFF}  "
                  f"{DIM}publishes contributions, not applications{OFF}")
            for g in gap:
                print(f"  {g['authority'][:34]:<36}{g['contributions']:>6,} contribs   "
                      f"£{(g['amount'] or 0):>13,.0f}")
    print(f"\n  {BOLD}£{total:,.0f}{OFF} recorded, over {with_amount:,} of {rows:,} contributions")
    print(f"\n{BOLD}promised against delivered{OFF}")
    for st, n, wa, amt in con.execute(
            "SELECT * FROM gold.ledger_funding_status LIMIT ?", [args.limit]).fetchall():
        print(f"  {st[:26]:<28}{n:>7,} txns   £{(amt or 0):>15,.0f}")
    print(f"\n{BOLD}by purpose{OFF}")
    for p_, n, wa, amt in con.execute(
            "SELECT * FROM gold.ledger_purpose LIMIT ?", [args.limit]).fetchall():
        print(f"  {p_[:26]:<28}{n:>7,}       £{(amt or 0):>15,.0f}")
    con.close()
    return 0


def cmd_baseline(args) -> int:
    from .systems import baseline as BL
    con = store.connect(DB)
    years = [y for y in (2021, 2022, 2023, 2024, 2025)
             if (BRONZE / f"edm_annual_{y}.zip").exists()]
    if years:
        for y in years:
            BL.load_multi(con, BRONZE / f"edm_annual_{y}.zip", y)
    elif (BRONZE / "edm_annual.zip").exists():
        BL.load(con, BRONZE / "edm_annual.zip", args.year); years = [args.year]
    else:
        print(f"{RED}no EDM return{OFF}"); con.close(); return 1
    BL.build(con)
    print(f"{BOLD}Baseline{OFF}  {DIM}storm overflows, {years[0]}-{years[-1]}{OFF}\n")
    tr = con.execute("SELECT year, outlets, reported_spills, adjusted_spills, mean_uptime "
                     "FROM gold.baseline_trend ORDER BY year").fetchall()
    print(f"  {'year':<6}{'outlets':>9}{'reported':>12}{'adjusted':>12}{'uptime':>9}")
    for y, o, rs, adj, up in tr:
        print(f"  {y:<6}{o:>9,}{rs:>12,.0f}{adj:>12,.0f}{up:>8.1f}%")
    print(f"\n{BOLD}by company, latest year{OFF}")
    for comp, rs, adj, av, bw in con.execute(
            """SELECT company, reported_spills, availability_adjusted, mean_availability_pct,
               barely_watched FROM gold.baseline_company
               WHERE year=(SELECT max(year) FROM gold.baseline_company)
               ORDER BY reported_spills DESC LIMIT ?""", [args.limit]).fetchall():
        print(f"  {comp[:24]:<26}{rs:>8,.0f} -> {adj:>8,.0f}   uptime {av:>5.1f}%   {bw:>3} barely watched")
    con.close()
    return 0


def cmd_sentinel(args) -> int:
    from .systems import sentinel as S
    con = store.connect(DB)
    paths = [p for p in (BRONZE / "contracts_finder_bulk.json",
                         BRONZE / "contracts_finder.json",
                         BRONZE / "find_a_tender.json") if p.exists()]
    if not paths:
        print(f"{RED}no procurement feeds{OFF}"); con.close(); return 1
    cov = S.load(con, *paths); S.build(con)
    n, total, pct = S.uncompeted_share(con)
    print(f"{BOLD}Sentinel{OFF}  {DIM}procurement concentration{OFF}\n")
    print(f"  award records          {cov.awards:>8,}")
    print(f"  supplier identified    {cov.suppliers_identified:>8,}  "
          f"{cov.pct(cov.suppliers_identified, cov.awards):5.1f}%")
    print(f"  bidder counts present  {cov.with_tenderer_count:>8,}  "
          f"{RED}single-bidder screens impossible in UK data{OFF}")
    print(f"  awards without open competition  {n:,} of {total:,} ({pct}%)")
    print(f"\n{BOLD}by procurement method{OFF}")
    for m, a, v, sh in con.execute(
            "SELECT * FROM gold.sentinel_method LIMIT ?", [args.limit]).fetchall():
        print(f"  {m:<16}{a:>6,}  {sh:>5.1f}%   £{(v or 0):>14,.0f}")
    print(f"\n{BOLD}buyers concentrating on one supplier{OFF}  {DIM}(a signal, not a verdict){OFF}")
    for b, s_, a, v, sh, vs in con.execute("""
            SELECT * FROM gold.sentinel_buyer WHERE awards >= 5
            ORDER BY top_supplier_award_share DESC LIMIT ?""", [args.limit]).fetchall():
        print(f"  {b[:36]:<38}{sh:>5.1f}% of {a:>3} awards")
    con.close()
    return 0


def cmd_highwater(args) -> int:
    from .systems import highwater as H
    con = store.connect(DB)
    src = BRONZE / "ea_objections.ods"
    if not src.exists():
        print(f"{RED}no objections file{OFF}"); con.close(); return 1
    cov = H.load(con, src); H.build(con)
    loc = H.locatability(con)
    print(f"{BOLD}Highwater{OFF}  {DIM}flood risk objections{OFF}\n")
    print(f"  objections             {cov.rows:>8,}")
    print(f"  with a known outcome   {cov.with_outcome:>8,}  {cov.pct(cov.with_outcome):5.1f}%")
    print(f"  carrying a location    {0:>8,}  {RED}  0.0%{OFF}"
          f"  {DIM}no address, postcode or coordinate on any row{OFF}")
    print(f"  planning references    {loc['with_reference']:>8,}  {DIM}the key to the site,"
          f" across {loc['authorities']} authorities{OFF}")
    print(f"\n{BOLD}outcomes{OFF}")
    for o, n, u in con.execute("SELECT * FROM gold.highwater_outcome").fetchall():
        print(f"  {o[:50]:<52}{n:>7,}  {int(u or 0):>8,} homes")
    print(f"\n{BOLD}override rate, decided cases only{OFF}")
    for y, ob, f_, a, u, orate, upct in con.execute(
            "SELECT * FROM gold.highwater_trend ORDER BY year").fetchall():
        bar = "#" * int((orate or 0) * 3)
        print(f"  {y}  {a:>4} of {ob:>5,}   {(orate or 0):>5.1f}%  {DIM}{bar}{OFF}")
    con.close()
    return 0


def cmd_plumbline(args) -> int:
    from .systems import plumbline as P
    con = store.connect(DB)
    src = BRONZE / "planning_ps2.csv"
    if not src.exists():
        print(f"{RED}no PS2 extract{OFF}"); con.close(); return 1
    if args.reload or not con.execute(
            "SELECT count(*) FROM information_schema.tables WHERE table_schema='silver'"
            " AND table_name='planning_performance'").fetchone()[0]:
        cov = P.load(con, src)
        print(f"  loaded {cov.rows:,} rows, {cov.authorities} authorities")
    P.build(con)
    h, st, md, dd = P.national_gap(con, since=args.since)
    print(f"{BOLD}Plumbline{OFF}  {DIM}major applications since {args.since}{OFF}\n")
    print(f"  published headline 'in time'   {GREEN}{h:>6.1f}%{OFF}  {DIM}counts agreed extensions"
          f" · {md:,.0f} decisions{OFF}")
    print(f"  within the statutory deadline  {RED}{st:>6.1f}%{OFF}  {DIM}major dwellings within"
          f" 13 weeks · {dd:,.0f} decisions{OFF}")
    print(f"  {BOLD}gap {h-st:.1f} points{OFF}")
    print(f"\n{DIM}  The two rates cover slightly different populations -- all majors against"
          f"\n  major dwellings -- and both counts are shown so neither is read as the other.{OFF}")
    print(f"\n{BOLD}the column that used to show this directly{OFF}")
    for y, rows_, pop, pct in P.transparency_column_status(con):
        mark = GREEN if pct > 50 else RED
        print(f"  {y}  'within maximum time' populated on {mark}{pct:>5.1f}%{OFF} of rows")
    print(f"\n{BOLD}widest gap by authority{OFF}")
    for lpa, md_, hp, dd_, sp in con.execute(
            "SELECT * FROM gold.plumbline_authority LIMIT ?", [args.limit]).fetchall():
        print(f"  {lpa[:26]:<28} headline {hp:>5.1f}%   statutory {sp:>5.1f}%   gap {hp-sp:>5.1f}")
    con.close()
    return 0


def cmd_sightline(args) -> int:
    from .systems import sightline as SL
    from .systems import highwater as H
    con = store.connect(DB)
    src = BRONZE / "ea_objections.ods"
    if not src.exists():
        print(f"{RED}no objections workbook{OFF}"); con.close(); return 1
    if not con.execute("SELECT count(*) FROM information_schema.tables WHERE"
                       " table_schema='silver' AND table_name='flood_objection'").fetchone()[0]:
        H.load(con, src)
    SL.load_water_quality(con, src); SL.build(con)
    wq = BRONZE / "planit_planning_wq.json"
    if wq.exists():
        n = SL.load_planit(con, wq); SL.build_planit(con)
        apps, auth, dec, dist = SL.planit_summary(con)
        print(f"{BOLD}Sightline{OFF}  {DIM}water-quality objections + national planning corpus{OFF}")
        print(f"  PlanIt corpus  {apps:,} applications · {auth} authorities · {dec} decided · {dist} districts\n")
    else:
        print(f"{BOLD}Sightline{OFF}  {DIM}is expert planning advice followed?{OFF}")
        print(f"  {DIM}no PlanIt corpus -- run: gt backfill --only planit{OFF}\n")
    for s in SL.streams(con, src):
        if s.has_outcome_field:
            print(f"  {s.name:<16}{s.objections:>7,} objections   outcome tracked on "
                  f"{GREEN}{s.tracked_pct:5.1f}%{OFF}")
        else:
            print(f"  {s.name:<16}{s.objections:>7,} objections   {RED}no outcome field at all{OFF}")
    print(f"\n{DIM}  'Unknown for some' and 'no field at all' are different conditions."
          f"\n  One of the two published advice streams has no evidence base whatsoever.{OFF}")
    print(f"\n{BOLD}why the Agency objected on water quality{OFF}")
    for r, n, a in con.execute(
            "SELECT * FROM gold.sightline_reason LIMIT ?", [args.limit]).fetchall():
        print(f"  {r[:50]:<52}{n:>5}  {DIM}{a} authorities{OFF}")
    con.close()
    return 0


def cmd_lastmile(args) -> int:
    from .systems import lastmile as LM
    con = store.connect(DB)
    bduk = sorted(BRONZE.glob("bduk_*.zip"))
    ppd = BRONZE / "ppd_monthly.csv"
    if not bduk or not ppd.exists():
        print(f"{RED}missing premises or price paid data{OFF}"); con.close(); return 1
    if args.reload or not con.execute(
            "SELECT count(*) FROM information_schema.tables WHERE table_schema='silver'"
            " AND table_name='premises_connectivity'").fetchone()[0]:
        print(f"  premises {LM.load_premises(con, *bduk):,}   new-build sales "
              f"{LM.load_new_builds(con, ppd):,}")
    LM.build(con)
    nb_p, nb_g, nb_pct, ot_p, ot_pct = LM.comparison(con)
    print(f"{BOLD}Lastmile{OFF}  {DIM}gigabit where new homes are being built{OFF}\n")
    print(f"  new-build postcodes    {RED}{nb_pct:>6.1f}%{OFF} gigabit   {DIM}{nb_p:,} premises{OFF}")
    print(f"  everywhere else        {GREEN}{ot_pct:>6.1f}%{OFF} gigabit   {DIM}{ot_p:,} premises{OFF}")
    print(f"  {BOLD}difference {nb_pct-ot_pct:+.1f} points{OFF}")
    print(f"\n{DIM}  Joined on postcode, not property: Price Paid carries no property"
          f"\n  reference. This measures the postcodes new homes sell in, which is a"
          f"\n  proxy for the homes themselves.{OFF}")
    print(f"\n{BOLD}by authority{OFF}")
    for la, p_, g, gp, nb, nbp in con.execute(
            "SELECT * FROM gold.lastmile_authority ORDER BY premises DESC LIMIT ?",
            [args.limit]).fetchall():
        d = f"{nbp:>6.1f}%" if nbp is not None else "     -"
        print(f"  {la[:22]:<24}{gp:>6.1f}% overall  {d} new-build  {DIM}{int(nb or 0)} sales{OFF}")
    con.close()
    return 0


def cmd_junction(args) -> int:
    import requests as _rq, time as _t
    from .systems import junction as J
    con = store.connect(DB)
    sess = _rq.Session(); sess.trust_env = False
    sess.headers.update({"User-Agent": "groundtruth/0.1"})
    states = []
    for op, base, ds in J.REGISTERS:
        exp = sess.get(J.EXPORT.format(base=base, ds=ds), timeout=240)
        fields, rows = (J.parse_export(exp.content.decode("utf-8-sig", errors="replace"))
                        if exp.status_code == 200 else ([], []))
        meta = sess.get(f"{base}/api/explore/v2.1/catalog/datasets/{ds}", timeout=120)
        rc = (meta.json().get("metas", {}).get("default", {}).get("records_count")
              if meta.status_code == 200 else None)
        states.append(J.RegisterState(op, ds, exp.status_code, tuple(fields), len(rows), rc))
        _t.sleep(1)
    J.load(con, states)
    gap = J.catalogue_gap(states); cmp_ = J.compare(states)
    print(f"{BOLD}Junction{OFF}  {DIM}embedded capacity registers{OFF}\n")
    print(f"  {'operator':<24}{'catalogue':>11}{'open export':>13}{'fields':>8}")
    for st in states:
        mark = GREEN if st.publishes_data else RED
        print(f"  {st.operator:<24}{st.catalogue_records or 0:>11,}"
              f"{mark}{st.rows:>13,}{OFF}{len(st.fields):>8}")
    print(f"\n  advertised {gap['advertised']:,} records; the open route returns "
          f"{gap['returned']:,}")
    print(f"  {RED}{gap['withheld']:,} records never reach it{OFF}  "
          f"{DIM}({gap['operators_serving_data']} of {gap['operators']} operators serve data){OFF}")
    print(f"\n  {BOLD}the schemas are not the problem{OFF}: {cmp_['shared_fields']} of "
          f"{cmp_['distinct_fields']} fields shared by all ({cmp_['shared_pct']}%)")
    print(f"  {DIM}Ofgem mandated a common format and the operators followed it."
          f"\n  Availability through the open route is the gap, not comparability.{OFF}")
    con.close()
    return 0


def cmd_compass(args) -> int:
    from .systems import compass as C
    con = store.connect(DB)
    src = BRONZE / "dfe_sen_provision.csv"
    if not src.exists():
        print(f"{RED}no SEN extract{OFF}"); con.close(); return 1
    if args.reload or not con.execute(
            "SELECT count(*) FROM information_schema.tables WHERE table_schema='silver'"
            " AND table_name='sen_provision'").fetchone()[0]:
        cov = C.load(con, src)
        print(f"  loaded {cov.rows:,} rows, {cov.authorities} authorities, {cov.years} years")
    C.build(con)
    print(f"{BOLD}Compass{OFF}  {DIM}special educational needs demand{OFF}\n")
    for prov, y0, y1, latest, earliest in C.national(con):
        if latest and earliest:
            pct = 100 * (latest - earliest) / earliest
            mark = RED if pct > 50 else DIM
            print(f"  {prov[:42]:<44}{earliest:>10,} -> {latest:>10,}   {mark}{pct:+6.1f}%{OFF}")
    print(f"\n{DIM}  Aggregate counts only. No record about any individual child is read"
          f"\n  or needed, which is what makes this deliverable without an agreement.{OFF}")
    print(f"\n{BOLD}fastest-rising EHC plan demand{OFF}  {DIM}3-year projection on an 11-year trend{OFF}")
    for la, name, prov, yrs, f_, l_, mean, slope, ch3, pct in con.execute(
            "SELECT * FROM gold.compass_trend WHERE provision = ? "
            "ORDER BY projected_change_pct DESC LIMIT ?", [C.EHC_PLAN, args.limit]).fetchall():
        print(f"  {name[:26]:<28}{slope:>7.1f}/yr   +{ch3:>6,.0f} over 3 years   {pct:>6.1f}%")
    print(f"\n{BOLD}diverging most from their region{OFF}  {DIM}the mismatch the system exists for{OFF}")
    for name, region, lapct, regpct, div in con.execute(
            "SELECT * FROM gold.compass_divergence LIMIT ?", [args.limit]).fetchall():
        print(f"  {name[:24]:<26}{lapct:>7.1f}%  {DIM}region {regpct:>6.1f}%{OFF}   {div:>+6.1f}")
    con.close()
    return 0


def cmd_publish(args) -> int:
    from . import publish
    con = store.connect(DB)
    dest = Path(args.out) if args.out else ROOT.parent / "app" / "data" / "platform.json"
    payload = publish.write(con, dest)
    size = dest.stat().st_size
    print(f"{BOLD}published{OFF} {dest}")
    print(f"  {size/1024:.0f} KB   {len(payload['built_systems'])} systems with real output")
    print(f"  {DIM}{', '.join(payload['built_systems'])}{OFF}")
    con.close()
    return 0


def cmd_chains(args) -> int:
    from . import chains as CH
    con = store.connect(DB)
    for ch in CH.run_all(con):
        print(f"\n{BOLD}{ch.name}{OFF}  {DIM}{ch.trigger} · {ch.spine} spine{OFF}")
        if not ch.steps:
            print(f"  {DIM}no system has produced output for this chain yet{OFF}")
            continue
        for st in ch.steps:
            mark = f"{GREEN}*{OFF}" if st.found else f"{DIM}-{OFF}"
            print(f"  {mark} {BOLD}{st.system:<12}{OFF}{DIM}{st.question}{OFF}")
            print(f"    {st.answer}")
        print(f"  {DIM}{ch.systems_touched} systems answered from one fact{OFF}")
    r = CH.reuse_summary(con)
    print(f"\n{BOLD}where the compounding comes from{OFF}")
    print(f"  place spine   {len(r['place_spine_users']):>2} systems  {DIM}{', '.join(r['place_spine_users'])}{OFF}")
    print(f"  entity spine  {len(r['entity_spine_users']):>2} systems  {DIM}{', '.join(r['entity_spine_users'])}{OFF}")
    print(f"  both          {len(r['both_spines']):>2} systems  {DIM}{', '.join(r['both_spines'])}{OFF}")
    print(f"  {DIM}Two resolvers, {r['systems_built']} systems. The nth costs less than the first.{OFF}")
    con.close()
    return 0


def cmd_run(args) -> int:
    """Fetch (optionally), build every system, publish."""
    from . import run as R, publish
    con = store.connect(DB)
    if args.fetch:
        print(f"{BOLD}fetching{OFF}")
        cmd_fetch(argparse.Namespace(ids=[], role=None, all=True, max_bytes=None,
                                     timeout=600, strict=False))
    print(f"\n{BOLD}building{OFF}")
    report = R.build_everything(con, BRONZE)
    for st in report.stages:
        mark = f"{GREEN}ok  {OFF}" if st.ok else f"{RED}fail{OFF}"
        print(f"  {mark} {st.name:<14}{st.seconds:>6.1f}s  {DIM}{st.detail[:70]}{OFF}")
    dest = ROOT.parent / "app" / "data" / "platform.json"
    payload = publish.write(con, dest)
    print(f"\n{BOLD}published{OFF} {len(payload['built_systems'])} systems to {dest.name}")
    if report.failed:
        print(f"{RED}{len(report.failed)} stage(s) failed{OFF} "
              f"{DIM}-- recorded, not hidden; the run continued{OFF}")
    con.close()
    return 1 if (report.failed and args.strict) else 0


def cmd_serve(args) -> int:
    from . import serve as S
    app = ROOT.parent / "app"
    print(f"{BOLD}Groundtruth{OFF}  {DIM}operational system, local only{OFF}")
    try:
        S.serve(app, port=args.port, open_browser=not args.no_open)
    except (FileNotFoundError, OSError) as exc:
        print(f"{RED}{exc}{OFF}")
        return 1
    return 0


def cmd_backfill(args) -> int:
    """Complete the sources that were originally taken in part."""
    from . import backfill as B
    sess = B._session()
    parts = args.only or ["bduk", "edm", "companies", "aims", "ps2", "psc", "contracts", "gazette",
                          "nhs_ods", "ckan"]
    results = []
    if "bduk" in parts:
        print(f"{BOLD}BDUK premises, all regions{OFF}")
        results += B.fetch_bduk(BRONZE, sess)
    if "edm" in parts:
        print(f"{BOLD}EDM storm overflow, all years{OFF}")
        results += B.fetch_edm(BRONZE, sess)
    if "companies" in parts:
        print(f"{BOLD}Companies House basic company data{OFF}")
        results.append(B.fetch_companies_house(BRONZE, sess))
    if "contracts" in parts:
        print(f"{BOLD}Contracts Finder backfill{OFF}")
        results.append(B.fetch_contracts(BRONZE, pages=args.pages, s=sess))
    if "aims" in parts:
        print(f"{BOLD}Environment Agency flood defences, all pages{OFF}")
        results.append(B.fetch_aims(BRONZE, sess))
    if "ps2" in parts:
        print(f"{BOLD}Planning statistics PS2 table{OFF}")
        results.append(B.fetch_ps2(BRONZE, sess))
    if "rainfall" in parts:
        print(f"{BOLD}Annual rainfall totals per station{OFF}")
        results.append(B.fetch_rainfall(BRONZE, s=sess))
    if "psc" in parts:
        print(f"{BOLD}Companies House PSC, all snapshot parts{OFF}")
        results.append(B.fetch_psc(BRONZE, sess))
    if "nhs_ods" in parts:
        results.append(B.fetch_nhs_ods(BRONZE, s=sess))
    if "ckan" in parts:
        results.append(B.fetch_ckan(BRONZE, s=sess))
    if "gazette" in parts:
        print(f"{BOLD}Gazette insolvency backfill{OFF}")
        results.append(B.fetch_gazette(BRONZE, pages=args.pages, s=sess))
    if "planit" in parts:
        print(f"{BOLD}PlanIt water-quality planning corpus (polite, rate-limited){OFF}")
        results.append(B.fetch_planit_planning(BRONZE, sess))

    print()
    for r in results:
        mark = f"{GREEN}ok  {OFF}" if r.ok else f"{RED}fail{OFF}"
        size = f"{r.bytes/1e6:>8.1f} MB" if r.bytes else " " * 11
        print(f"  {mark} {r.name:<34}{size}  {DIM}{r.detail[:52]}{OFF}")
    failed = [r for r in results if not r.ok]
    print(f"\n{len(results)-len(failed)} complete, {len(failed)} failed")
    return 1 if failed and args.strict else 0


def cmd_status(args) -> int:
    con = store.connect(DB)
    rows = store.latest_status(con)
    print(f"{BOLD}{'ID':<32}{'ROLE':<14}{'STATUS':<10}{'SIZE':>10}  NOTE{OFF}")
    for sid, role, _pub, status, ok, blen, _at, note in rows:
        if ok:
            st, size = f"{GREEN}200{OFF}     ", f"{blen/1e6:>7.1f} MB"
        else:
            st, size = f"{RED}{(str(status) if status > 0 else '-'):<8}{OFF}", " " * 10
        print(f"{sid:<32}{role:<14}{st}{size}  {DIM}{note[:56]}{OFF}")
    con.close()
    return 0


def cmd_claims(args) -> int:
    """Corrections the platform has made to its own published claims."""
    from . import claims as C
    s = C.summary()
    print(f"{BOLD}Corrected claims{OFF}  {DIM}what was believed, and what the source says{OFF}\n")
    print(f"  recorded {s['total']}   guarded by a test {s['guarded']}   "
          f"{RED if s['unguarded'] else ''}unguarded {s['unguarded']}{OFF}\n")
    for c in C.ARCHIVE:
        if args.system and c.system != args.system:
            continue
        mark = "" if c.guarded else f"  {RED}no guard{OFF}"
        print(f"  {BOLD}{c.id}{OFF}  {DIM}{c.system}{OFF}{mark}")
        print(f"    believed   {c.believed}")
        print(f"    actually   {c.actually}")
        print(f"    caught by  {DIM}{c.how_caught}{OFF}\n")
    return 0


def cmd_graph(args) -> int:
    """The evidence graph: which relationships can currently be walked."""
    from . import graph as G
    con = store.connect(DB)
    if args.node:
        paths = G.walk(con, args.node, max_depth=args.depth, limit=args.limit)
        print(f"{BOLD}from{OFF} {args.node}\n")
        if not paths:
            print(f"  {DIM}no edges from this node{OFF}")
        for p_ in paths:
            print(f"  {p_}   {DIM}confidence {p_.confidence:.3f}{OFF}")
        con.close()
        return 0
    s = G.stats(con)
    print(f"{BOLD}Evidence graph{OFF}\n")
    print(f"  declared relationships  {s['declared_edges']:>4}")
    print(f"  walkable now            {s['available_edges']:>4}")
    print(f"  total edges             {s['total_relationships']:>12,}\n")
    for row in G.available(con):
        state = f"{GREEN}walkable{OFF}" if row["available"] else f"{DIM}unavailable{OFF}"
        n = f"{row['edges']:,}" if row["edges"] is not None else "--"
        print(f"  {row['predicate']:<16}{row['from']:<22}-> {row['to']:<20}"
              f"{n:>12}  {state}")
        if row["note"]:
            print(f"    {DIM}{row['note']}{OFF}")
    con.close()
    return 0


def cmd_why(args) -> int:
    """Where a number came from."""
    from . import provenance as P
    con = store.connect(DB)
    rows = P.explain(con, args.subject, args.field)
    if not rows:
        print(f"{DIM}no observations recorded for {args.subject}{OFF}")
        print(f"{DIM}the evidence layer fills as systems record through provenance.record(){OFF}")
        con.close()
        return 0
    for r in rows:
        val = r["value_text"] if r["value_num"] is None else f"{r['value_num']:,}"
        print(f"{BOLD}{r['field']}{OFF}  {val}   {DIM}{r['derivation']}{OFF}")
        if r["source_id"]:
            print(f"  source     {r['publisher']} / {r['dataset']}  {DIM}{r['source_id']}{OFF}")
        if r["record_ref"]:
            print(f"  record     {r['record_ref']}")
        for step in r["transformations"]:
            print(f"    -> {step}")
        for j in r["joins"]:
            print(f"    join on {j.get('on')} to {j.get('to')}")
        if r.get("coverage_pct") is not None:
            print(f"  coverage   {r['coverage_pct']}%  "
                  f"({r['coverage_n']:,} of {r['coverage_of']:,})")
        if r["confidence"] is not None:
            print(f"  confidence {r['confidence']:.3f}")
        print()
    con.close()
    return 0


def cmd_snapshot(args) -> int:
    """Record, list or compare the shape of the platform over time."""
    from . import temporal as T
    con = store.connect(DB)
    if args.diff:
        d = T.diff(con, *args.diff)
        print(f"{BOLD}{d['before']} -> {d['after']}{OFF}\n")
        for t_ in d["tables_added"]:
            print(f"  {GREEN}+{OFF} {t_}")
        for t_ in d["tables_removed"]:
            print(f"  {RED}-{OFF} {t_}")
        for r in d["row_changes"]:
            sign = "+" if r["delta"] > 0 else ""
            print(f"  ~ {r['table']:<40}{sign}{r['delta']:,}")
        for r in d["schema_changes"]:
            print(f"  {RED}schema{OFF} {r['table']}  added={r['added']} removed={r['removed']}")
        for t_ in d["rewritten_in_place"]:
            print(f"  {RED}rewritten in place{OFF} {t_}  "
                  f"{DIM}same row count, different content{OFF}")
        con.close()
        return 0
    if args.list:
        for s in T.snapshots(con):
            print(f"  {s['snapshot_id']}  {s['tables']:>3} tables  "
                  f"{(s['rows'] or 0):>14,} rows  {DIM}{s['label'] or ''}{OFF}")
        con.close()
        return 0
    out = T.snapshot(con, label=args.label or "")
    print(f"  snapshot {BOLD}{out['snapshot_id']}{OFF}  "
          f"{out['tables']} tables, {out['rows']:,} rows")
    con.close()
    return 0


def cmd_profile(args) -> int:
    """Everything the platform knows about one place or one organisation."""
    from . import profiles as PR
    con = store.connect(DB)
    ident = args.identifier
    prof = (PR.organisation_profile(con, ident) if ":entity:" in ident
            else PR.place_profile(con, ident))
    if not prof.get("resolved"):
        print(f"{RED}unresolved{OFF}  {DIM}{prof.get('reason')}{OFF}")
        con.close(); return 1
    title = prof.get("name") or prof.get("lad_code")
    print(f"{BOLD}{title}{OFF}  {DIM}{prof['identifier']}{OFF}")
    if prof.get("resolved_from"):
        print(f"  {DIM}resolved from {prof['resolved_from']}{OFF}")
    if prof.get("company_number"):
        print(f"  {DIM}{prof.get('status')} - incorporated {prof.get('incorporated')}"
              f" - {prof.get('post_town')}{OFF}")
        if prof.get("authorities_operated_in"):
            a = prof["authorities_operated_in"]
            print(f"  operates in {len(a)} authorities: "
                  f"{DIM}{', '.join(a[:6])}{'...' if len(a) > 6 else ''}{OFF}")
    print(f"  {prof['systems_with_data']} of {prof['systems_checked']} systems hold data")
    if prof.get("by_name"):
        print(f"  {DIM}{prof['by_identifier']} matched on an identifier, "
              f"{prof['by_name']} on a name{OFF}")
    print()
    for s in prof["sections"]:
        if not s["available"]:
            print(f"  {s['system']:<20}{DIM}unavailable - {s['note']}{OFF}")
            continue
        if not s["facts"]:
            print(f"  {s['system']:<20}{DIM}no rows - {s['note']}{OFF}")
            continue
        mark = "" if s["match"] == "identifier" else f"  {DIM}[name match]{OFF}"
        print(f"  {BOLD}{s['system']}{OFF}{mark}  {DIM}{s['table']}{OFF}")
        facts = s["facts"]
        if "rows" in facts:
            print(f"      {DIM}{facts['count']} rows{OFF}")
            for r in facts["rows"][:args.limit]:
                bits = "  ".join(f"{k}={v}" for k, v in list(r.items())[:5])
                print(f"      {bits}")
            continue
        for k, v in list(facts.items())[:12]:
            if v is None or k in ("lad_code", "lad_name"):
                continue
            v = f"{v:,}" if isinstance(v, int) else v
            print(f"      {k:<26}{v}")
    con.close()
    return 0


def cmd_ask(args) -> int:
    """Answer a question, showing the plan before the answer."""
    from . import search as SE
    con = store.connect(DB)
    q = " ".join(args.question)
    out = SE.answer(con, q, limit=args.limit)
    p = out["plan"]
    verdict = {"yes": GREEN, "partial": "", "no": RED}[p["answerable"]]
    print(f"{BOLD}{q}{OFF}\n")
    print(f"{BOLD}plan{OFF}")
    print(f"  answerable        {verdict}{p['answerable']}{OFF}")
    if p["places"]:
        print(f"  places            " +
              ", ".join(f"{h['name']} ({h['lad_code']})" for h in p["places"]))
    if p["organisations"]:
        print(f"  organisations     " +
              ", ".join(f"{h['name']} ({h['company_number']})" for h in p["organisations"]))
    print(f"  systems           {', '.join(p['systems']) or DIM + 'none matched' + OFF}")
    for tbl in p["tables"]:
        print(f"  reads             {DIM}{tbl}{OFF}")
    for j in p["joins"]:
        print(f"  joins             {DIM}{j}{OFF}")
    for b in p["blocked"]:
        print(f"  {RED}blocked{OFF}           {b}")
    if p["unresolved"]:
        print(f"  {DIM}not understood    {', '.join(p['unresolved'])}{OFF}")

    if out["answer"] is None:
        print(f"\n{RED}Groundtruth cannot answer this.{OFF}")
        for w in out["why_not"]:
            print(f"  {w}")
        con.close(); return 0

    heading = ("what it can show instead" if p["blocked"] else "answer")
    print(f"\n{BOLD}{heading}{OFF}")
    if p["blocked"]:
        print(f"  {DIM}the question as asked cannot be answered; "
              f"this is the nearest the corpus supports{OFF}")
    for r in out["results"][:args.limit]:
        print(f"  {BOLD}{r['subject']}{OFF}")
        for s in r.get("sections", [])[:8]:
            if not (s["available"] and s["facts"]):
                continue
            facts = s["facts"]
            if "rows" in facts:
                print(f"    {BOLD}{s['system']}{OFF}  {DIM}{facts['count']} rows, "
                      f"{s['table']}{OFF}")
                for row in facts["rows"][:args.limit]:
                    bits = "  ".join(f"{v}" for v in list(row.values())[:4]
                                     if v is not None)
                    print(f"      {bits}")
                continue
            bits = "  ".join(f"{k}={v}" for k, v in list(facts.items())[:4]
                             if v is not None and k not in ("lad_code", "lad_name"))
            print(f"    {s['system']:<16}{bits}")
        for row in r.get("rows", [])[:args.limit]:
            print("    " + "  ".join(f"{k}={v}" for k, v in list(row.items())[:5]))
    con.close()
    return 0


def cmd_contradictions(args) -> int:
    """Where two official records disagree. Neither is chosen."""
    from . import contradictions as CD
    con = store.connect(DB)
    out = CD.run_all(con, limit=args.limit)
    print(f"{BOLD}Contradictions{OFF}  {DIM}two routes to one quantity{OFF}\n")
    print(f"  checks {out['checks']}   run {out['run']}   "
          f"disagreeing {out['with_disagreement']}   "
          f"rows in disagreement {out['total_disagreements']:,}\n")
    for r in out["results"]:
        if not r["run"]:
            print(f"  {r['check']:<26}{DIM}not run - {r['reason']}{OFF}")
            continue
        colour = RED if r["disagreed"] else GREEN
        print(f"  {BOLD}{r['check']}{OFF}  {DIM}{r['quantity']}{OFF}")
        print(f"    compared {r['compared']:,}   "
              f"{colour}disagreed {r['disagreed']:,}{OFF}   "
              f"agreement {r['agreement_pct']}%")
        if r["note"]:
            print(f"    {DIM}{r['note']}{OFF}")
        for d in r["disagreements"][:args.limit]:
            print(f"      {str(d['subject'])[:34]:<36}"
                  f"{d['left_value']:>12,.0f} vs {d['right_value']:>12,.0f}"
                  f"   {DIM}{d['detail'][:28]}{OFF}")
        if r["disagreed"]:
            print(f"    {DIM}left:  {r['disagreements'][0]['left']}{OFF}")
            print(f"    {DIM}right: {r['disagreements'][0]['right']}{OFF}")
        print()
    con.close()
    return 0


def cmd_gaps(args) -> int:
    """What should be joinable, and is not."""
    from . import gaps as GP
    con = store.connect(DB)
    r = GP.report(con, threshold=args.threshold)
    print(f"{BOLD}Evidence gaps{OFF}  {DIM}where the trail stops, and why{OFF}\n")
    print(f"  chains {r['chains']}   complete {r['complete']}   broken {r['broken']}")
    causes = "   ".join(f"{k} {v}" for k, v in sorted(r["by_cause"].items()))
    print(f"  {DIM}{causes}{OFF}\n")
    for c in r["detail"]:
        mark = f"{GREEN}complete{OFF}" if c["complete"] else f"{RED}breaks at {c['breaks_at']}{OFF}"
        print(f"  {BOLD}{c['chain']}{OFF}  {mark}")
        print(f"    {DIM}{c['asks']}{OFF}")
        for s in c["detail"]:
            if s["available"]:
                pct = "" if s["populated_pct"] is None else f"  {s['populated_pct']}% populated"
                print(f"      {GREEN}ok{OFF}    {s['step']:<26}{DIM}{s['table'] or ''}{pct}{OFF}")
            else:
                why = s["absent_because"] or "?"
                print(f"      {RED}gap{OFF}   {s['step']:<26}{DIM}{why}{OFF}")
                if s["reason"]:
                    print(f"            {DIM}{s['reason']}{OFF}")
        print()
    if r["not_published_anywhere"]:
        print(f"{BOLD}not published anywhere in the UK{OFF}  "
              f"{DIM}no platform can close these{OFF}")
        for g in r["not_published_anywhere"]:
            print(f"  {g['chain']}/{g['step']}")
    if r["fixable_here"]:
        print(f"\n{BOLD}fixable in this platform{OFF}")
        for g in r["fixable_here"]:
            print(f"  {g['chain']}/{g['step']}")
    con.close()
    return 0


def cmd_explore(args) -> int:
    """Expand the graph around a node and render it."""
    from . import relationships as RL
    con = store.connect(DB)
    if args.to:
        paths = RL.between(con, args.node, args.to, max_depth=args.depth)
        if not paths:
            print(f"{DIM}no path within {args.depth} hops{OFF}")
        for p_ in paths[:args.limit]:
            print(f"  {p_}   {DIM}confidence {p_.confidence:.3f}{OFF}")
        con.close(); return 0
    n = RL.neighbourhood(con, args.node, depth=args.depth, max_nodes=args.limit)
    nodes, edges = n.size
    print(f"{BOLD}{RL.label(con, args.node)}{OFF}  {DIM}{args.node}{OFF}")
    print(f"  {nodes} nodes, {edges} edges, depth {args.depth}"
          + (f"  {RED}truncated{OFF}" if n.truncated else "") + "\n")
    print(RL.to_mermaid(n) if args.mermaid else RL.to_text(n))
    con.close()
    return 0


def cmd_audit(args) -> int:
    """Run the data integrity audit."""
    from . import audit as AU
    con = store.connect(DB)
    a = AU.run(con, network=args.network)
    s = a.summary()
    print(f"{BOLD}Data integrity audit{OFF}  "
          f"{DIM}{'with live publisher checks' if args.network else 'database only'}{OFF}\n")
    print(f"  checks run {s['checks_run']}   skipped {s['checks_skipped']}   "
          f"findings {s['findings']}")
    bits = "   ".join(f"{k} {v}" for k, v in sorted(s["by_severity"].items()))
    print(f"  {bits}\n")
    for sk in a.checks_skipped:
        print(f"  {DIM}skipped {sk['check']}: {sk['reason']}{OFF}")
    colour = {"critical": RED, "major": RED, "minor": "", "note": DIM}
    for f in a.sorted():
        if args.severity and f.severity != args.severity:
            continue
        c = colour[f.severity]
        print(f"  {c}{f.severity.upper():<9}{OFF}{BOLD}{f.subject}{OFF}  {DIM}{f.check}{OFF}")
        print(f"    {f.summary}")
        if f.evidence:
            print(f"    {DIM}{f.evidence}{OFF}")
        if f.remedy and f.severity in ("critical", "major"):
            print(f"    {DIM}remedy: {f.remedy}{OFF}")
    con.close()
    return 1 if s["critical"] else 0


def cmd_investigate(args) -> int:
    """Create and work an investigation."""
    from . import investigations as I
    con = store.connect(DB)
    try:
        if args.new:
            inv = I.create(con, args.new, question=args.question)
            print(f"  created {BOLD}{inv.id}{OFF}")
        elif args.add:
            out = I.add(con, args.name, args.add, why=args.why or "",
                        found_via="added by hand")
            print(f"  {'added' if out['added'] else 'already present'}  {args.add}")
        elif args.rule_out:
            I.remove(con, args.name, args.rule_out, because=args.why or "")
            print(f"  ruled out {args.rule_out}")
        elif args.expand:
            out = I.expand(con, args.name, args.expand, depth=args.depth)
            print(f"  added {out['added']} from {out['seed']} "
                  f"({out['already_present']} already present)")
        elif args.note:
            I.note(con, args.name, args.note)
            print("  noted")
        elif args.close:
            I.close(con, args.name, outcome=args.close)
            print("  closed")
        elif args.name:
            inv = I.get(con, args.name)
            state = f"{DIM}closed{OFF}" if not inv.open else f"{GREEN}open{OFF}"
            print(f"{BOLD}{inv.name}{OFF}  {DIM}{inv.id}{OFF}  {state}")
            if inv.question:
                print(f"  {DIM}{inv.question}{OFF}")
            if inv.outcome:
                print(f"  outcome: {inv.outcome}")
            counts = "  ".join(f"{k} {v}" for k, v in sorted(inv.by_kind().items()))
            print(f"\n  {len(inv.live_items)} subjects   {counts}")
            for i in inv.live_items:
                print(f"    {i['identifier']}")
                print(f"      {DIM}{i['why']}{OFF}")
                if i["found_via"]:
                    print(f"      {DIM}via {i['found_via']}{OFF}")
            if inv.ruled_out:
                print(f"\n  {len(inv.ruled_out)} ruled out")
                for i in inv.ruled_out:
                    print(f"    {DIM}{i['identifier']} -- {i['removed_because']}{OFF}")
            for n in inv.notes:
                print(f"\n  {DIM}{n['noted_at']:%Y-%m-%d %H:%M}{OFF}  {n['text']}")
        else:
            rows = I.listing(con)
            if not rows:
                print(f"  {DIM}no investigations yet -- gt investigate --new \"name\"{OFF}")
            for r in rows:
                state = "closed" if r["closed_at"] else "open"
                print(f"  {r['id']:<34}{r['items']:>4} subjects  "
                      f"{r['ruled_out']:>3} ruled out  {DIM}{state}{OFF}")
    except I.InvestigationError as exc:
        print(f"{RED}{exc}{OFF}")
        con.close(); return 1
    con.close()
    return 0


def cmd_bundle(args) -> int:
    """Export an investigation as an evidence pack."""
    from . import bundles as BU
    con = store.connect(DB)
    if args.out:
        out = BU.write(con, args.name, Path(args.out))
        print(f"  {BOLD}{out['path']}{OFF}")
        for f in out["files"]:
            print(f"    {f}")
        print(f"\n  {out['subjects']} subjects, {out['sources']} sources")
        if out["sources_without_retrieval_record"]:
            print(f"  {RED}{out['sources_without_retrieval_record']} sources have no "
                  f"recorded retrieval{OFF}  {DIM}stated in the pack{OFF}")
    else:
        print(BU.to_markdown(BU.build(con, args.name)))
    con.close()
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="gt", description="Groundtruth platform")
    sub = p.add_subparsers(dest="cmd", required=True)

    ps = sub.add_parser("sources", help="list the source registry")
    ps.add_argument("--role", choices=["place_spine", "entity_spine", "domain"])
    ps.set_defaults(fn=cmd_sources)

    pf = sub.add_parser("fetch", help="fetch sources anonymously")
    pf.add_argument("ids", nargs="*")
    pf.add_argument("--role", choices=["place_spine", "entity_spine", "domain"])
    pf.add_argument("--all", action="store_true")
    pf.add_argument("--max-bytes", type=int, default=None,
                    help="stop after N bytes -- useful for smoke tests on large products")
    pf.add_argument("--timeout", type=int, default=120)
    pf.add_argument("--strict", action="store_true", help="exit non-zero if any source fails")
    pf.add_argument("--if-missing", action="store_true",
                    help="skip sources whose file is already on disk and readable")
    pf.set_defaults(fn=cmd_fetch)

    pl = sub.add_parser("load", help="expand bronze downloads into silver tables")
    pl.add_argument("--full", action="store_true",
                    help="also load the identifier crosswalks and company register (~16 GB of CSV)")
    pl.set_defaults(fn=cmd_load)

    pp = sub.add_parser("place", help="resolve postcodes through the place spine")
    pp.add_argument("postcodes", nargs="+")
    pp.set_defaults(fn=cmd_place)

    pc = sub.add_parser("coverage", help="what the place spine can resolve")
    pc.add_argument("--validate", action="store_true",
                    help="measure accuracy against GIAS published coordinates")
    pc.set_defaults(fn=cmd_coverage)

    pcat = sub.add_parser("catchment", help="build and report the Catchment system")
    pcat.add_argument("--limit", type=int, default=8)
    pcat.set_defaults(fn=cmd_catchment)

    pw = sub.add_parser("watchman", help="build the supplier register and check exposure")
    pw.add_argument("--limit", type=int, default=10)
    pw.set_defaults(fn=cmd_watchman)

    pe = sub.add_parser("entity", help="build the organisation knowledge graph")
    pe.set_defaults(fn=cmd_entity)

    pb = sub.add_parser("bellwether", help="provider concentration in care")
    pb.add_argument("--limit", type=int, default=8)
    pb.add_argument("--reload", action="store_true")
    pb.set_defaults(fn=cmd_bellwether)

    pbk = sub.add_parser("bulwark", help="flood defence responsibility and inspections")
    pbk.add_argument("--limit", type=int, default=6)
    pbk.add_argument("--reload", action="store_true")
    pbk.set_defaults(fn=cmd_bulwark)

    pl2 = sub.add_parser("ledger", help="developer contributions promised and delivered")
    pl2.add_argument("--limit", type=int, default=6)
    pl2.set_defaults(fn=cmd_ledger)

    pbl = sub.add_parser("baseline", help="storm overflow spills, availability adjusted")
    pbl.add_argument("--year", type=int, default=2025)
    pbl.add_argument("--limit", type=int, default=6)
    pbl.set_defaults(fn=cmd_baseline)

    psn = sub.add_parser("sentinel", help="procurement concentration signals")
    psn.add_argument("--limit", type=int, default=6)
    psn.set_defaults(fn=cmd_sentinel)

    phw = sub.add_parser("highwater", help="flood objections and outcomes")
    phw.set_defaults(fn=cmd_highwater)

    ppl = sub.add_parser("plumbline", help="planning performance, headline against statutory")
    ppl.add_argument("--since", default="2023")
    ppl.add_argument("--limit", type=int, default=6)
    ppl.add_argument("--reload", action="store_true")
    ppl.set_defaults(fn=cmd_plumbline)

    psl = sub.add_parser("sightline", help="consultee advice and whether it is tracked")
    psl.add_argument("--limit", type=int, default=8)
    psl.set_defaults(fn=cmd_sightline)

    plm = sub.add_parser("lastmile", help="gigabit coverage where new homes are built")
    plm.add_argument("--limit", type=int, default=8)
    plm.add_argument("--reload", action="store_true")
    plm.set_defaults(fn=cmd_lastmile)

    pjn = sub.add_parser("junction", help="grid capacity registers and what they serve")
    pjn.set_defaults(fn=cmd_junction)

    pcm = sub.add_parser("compass", help="SEND demand forecast by authority")
    pcm.add_argument("--limit", type=int, default=6)
    pcm.add_argument("--reload", action="store_true")
    pcm.set_defaults(fn=cmd_compass)

    ppb = sub.add_parser("publish", help="write gold tables as JSON for the prototype")
    ppb.add_argument("--out", default=None)
    ppb.set_defaults(fn=cmd_publish)

    pch = sub.add_parser("chains", help="run the cross-system chains against real output")
    pch.set_defaults(fn=cmd_chains)

    prun = sub.add_parser("run", help="build every system and publish")
    prun.add_argument("--fetch", action="store_true", help="fetch sources first")
    prun.add_argument("--strict", action="store_true", help="exit non-zero if a stage fails")
    prun.set_defaults(fn=cmd_run)

    pcl = sub.add_parser("claims", help="corrections this platform made to its own claims")
    pcl.add_argument("--system", default=None)
    pcl.set_defaults(fn=cmd_claims)

    pgr = sub.add_parser("graph", help="the evidence graph and what can be walked")
    pgr.add_argument("--node", default=None, help="a gt: identifier to walk from")
    pgr.add_argument("--depth", type=int, default=4)
    pgr.add_argument("--limit", type=int, default=25)
    pgr.set_defaults(fn=cmd_graph)

    pwy = sub.add_parser("why", help="where a number came from")
    pwy.add_argument("subject", help="a gt: identifier")
    pwy.add_argument("--field", default=None)
    pwy.set_defaults(fn=cmd_why)

    psn = sub.add_parser("snapshot", help="record or compare the platform over time")
    psn.add_argument("--label", default=None)
    psn.add_argument("--list", action="store_true")
    psn.add_argument("--diff", nargs=2, metavar=("BEFORE", "AFTER"), default=None)
    psn.set_defaults(fn=cmd_snapshot)

    ppf = sub.add_parser("profile", help="everything known about one place or organisation")
    ppf.add_argument("identifier", help="a gt: place or entity identifier")
    ppf.add_argument("--limit", type=int, default=5)
    ppf.set_defaults(fn=cmd_profile)

    pask = sub.add_parser("ask", help="answer a question, showing the plan first")
    pask.add_argument("question", nargs="+")
    pask.add_argument("--limit", type=int, default=6)
    pask.set_defaults(fn=cmd_ask)

    pcd = sub.add_parser("contradictions", help="where two official records disagree")
    pcd.add_argument("--limit", type=int, default=5)
    pcd.set_defaults(fn=cmd_contradictions)

    pgp = sub.add_parser("gaps", help="what should be joinable, and is not")
    pgp.add_argument("--threshold", type=float, default=1.0)
    pgp.set_defaults(fn=cmd_gaps)

    pex = sub.add_parser("explore", help="expand the graph around a node")
    pex.add_argument("node")
    pex.add_argument("--to", default=None, help="find paths to another node")
    pex.add_argument("--depth", type=int, default=2)
    pex.add_argument("--limit", type=int, default=40)
    pex.add_argument("--mermaid", action="store_true")
    pex.set_defaults(fn=cmd_explore)

    pau = sub.add_parser("audit", help="data integrity audit")
    pau.add_argument("--network", action="store_true",
                     help="also check every source still serves data anonymously")
    pau.add_argument("--severity", default=None,
                     choices=["critical", "major", "minor", "note"])
    pau.set_defaults(fn=cmd_audit)

    piv = sub.add_parser("investigate", help="create and work an investigation")
    piv.add_argument("name", nargs="?", default=None)
    piv.add_argument("--new", default=None, metavar="NAME")
    piv.add_argument("--question", default=None)
    piv.add_argument("--add", default=None, metavar="ID")
    piv.add_argument("--rule-out", dest="rule_out", default=None, metavar="ID")
    piv.add_argument("--why", default=None, help="required with --add and --rule-out")
    piv.add_argument("--expand", default=None, metavar="SEED")
    piv.add_argument("--depth", type=int, default=2)
    piv.add_argument("--note", default=None)
    piv.add_argument("--close", default=None, metavar="OUTCOME")
    piv.set_defaults(fn=cmd_investigate)

    pbu = sub.add_parser("bundle", help="export an investigation as an evidence pack")
    pbu.add_argument("name")
    pbu.add_argument("--out", default=None, help="directory to write; omit to print")
    pbu.set_defaults(fn=cmd_bundle)

    psv = sub.add_parser("serve", help="run the system on localhost")
    psv.add_argument("--port", type=int, default=8787)
    psv.add_argument("--no-open", action="store_true", help="do not open a browser")
    psv.set_defaults(fn=cmd_serve)

    pbf = sub.add_parser("backfill", help="complete sources taken only in part")
    pbf.add_argument("--only", nargs="*",
                     choices=["bduk", "edm", "companies", "aims", "ps2", "psc", "rainfall", "contracts", "gazette", "planit", "nhs_ods", "ckan"])
    pbf.add_argument("--pages", type=int, default=200)
    pbf.add_argument("--strict", action="store_true")
    pbf.set_defaults(fn=cmd_backfill)

    pst = sub.add_parser("status", help="last outcome per source")
    pst.set_defaults(fn=cmd_status)

    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
