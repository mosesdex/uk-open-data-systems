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

    con = store.connect(DB)
    run_id = uuid.uuid4().hex[:12]
    print(f"{DIM}run {run_id} -- {len(targets)} source(s), anonymous{OFF}\n")
    failures = 0

    for src in targets:
        print(f"  {src.id:<32}", end="", flush=True)
        url = _resolve_url(src)
        if url is None:
            failures += 1
            continue
        res = fetch(src, BRONZE, max_bytes=args.max_bytes,
                    url_override=url, timeout=args.timeout)
        store.record_fetch(con, run_id, res)
        if res.ok:
            mb = res.bytes_len / 1e6
            fresh = store.changed_since_last(con, src.id, res.sha256)
            tag = "new content" if fresh else "unchanged"
            print(f"{GREEN}HTTP 200{OFF}  {mb:>8.1f} MB  {res.elapsed_ms:>6} ms  {DIM}{tag}{OFF}")
        else:
            failures += 1
            label = f"HTTP {res.http_status}" if res.http_status else "no response"
            print(f"{RED}{label:<8}{OFF}  {DIM}{res.note[:66]}{OFF}")

    con.close()
    print(f"\n{len(targets)-failures} ok, {failures} failed")
    return 1 if failures and args.strict else 0


def cmd_load(args) -> int:
    """Expand bronze downloads into silver tables."""
    con = store.connect(DB)
    steps = [
        ("postcodes",  lambda: load_mod.load_codepoint(con, BRONZE / "os_code_point_open.zip")),
        ("boundaries", lambda: load_mod.load_lad_boundaries(con, BRONZE / "ons_lad_boundaries.geojson")),
        ("properties", lambda: load_mod.load_uprn(con, BRONZE / "os_open_uprn.zip")),
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
        print(f"    {DIM}A register of 100,000 suppliers would surface roughly 16.{OFF}")
        print(f"    {DIM}Backfilling historic award notices is the operational requirement.{OFF}")
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
          f"  {DIM}the gap: none of it can be mapped{OFF}")
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
    src = BRONZE / "edm_annual.zip"
    if not src.exists():
        print(f"{RED}no EDM return{OFF}"); con.close(); return 1
    cov = BL.load(con, src, args.year); BL.build(con)
    print(f"{BOLD}Baseline{OFF}  {DIM}storm overflows, {args.year}{OFF}\n")
    print(f"  outlets                {cov.outlets:>8,}")
    print(f"  monitor availability   {cov.with_availability:>8,}  {cov.pct(cov.with_availability):5.1f}%")
    print(f"  located from grid ref  {cov.located:>8,}  {cov.pct(cov.located):5.1f}%")
    print(f"  watched 90%+ of year   {cov.fully_watched:>8,}  {cov.pct(cov.fully_watched):5.1f}%")
    t = con.execute("""SELECT round(sum(spills)), round(sum(spills_full_year_equivalent)),
        round(avg(operational_pct),1) FROM gold.baseline_outlet""").fetchone()
    print(f"\n  reported spills        {t[0]:>8,.0f}")
    print(f"  availability-adjusted  {t[1]:>8,.0f}   {GREEN}{100*(t[1]-t[0])/t[0]:+.1f}%{OFF}")
    print(f"\n{BOLD}by company{OFF}")
    for y, comp, o, rs, adj, av, uw, bw in con.execute(
            "SELECT * FROM gold.baseline_company LIMIT ?", [args.limit]).fetchall():
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
    print(f"{BOLD}Sightline{OFF}  {DIM}is expert planning advice followed?{OFF}\n")
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
    pf.set_defaults(fn=cmd_fetch)

    pl = sub.add_parser("load", help="expand bronze downloads into silver tables")
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

    pst = sub.add_parser("status", help="last outcome per source")
    pst.set_defaults(fn=cmd_status)

    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
