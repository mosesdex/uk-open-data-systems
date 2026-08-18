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

    pst = sub.add_parser("status", help="last outcome per source")
    pst.set_defaults(fn=cmd_status)

    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
