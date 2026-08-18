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

    pst = sub.add_parser("status", help="last outcome per source")
    pst.set_defaults(fn=cmd_status)

    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
