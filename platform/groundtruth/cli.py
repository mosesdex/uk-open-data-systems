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

    pst = sub.add_parser("status", help="last outcome per source")
    pst.set_defaults(fn=cmd_status)

    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
