"""Evidence bundles: an investigation, packaged so someone else can check it.

A finding that only exists inside this platform is not much use to a journalist
filing a story, a councillor asking a question, or an auditor who has to stand
behind a number. What they need is the finding plus everything required to
disbelieve it: the sources, the joins, the confidence, the coverage, and an
honest statement of what the platform could not determine.

So a bundle is not an export of results. It is an export of results *and their
defences*, and the defences are assembled from the parts of the platform that
already exist rather than written by hand:

    sources        the registry entry and the fetch record for every source
                   the investigation's items depend on
    records        the gold rows behind each item, named table by table
    confidence     the resolution tier and score each spine achieved
    limitations    the evidence gaps, the corrected claims, and the internal
                   contradictions that bear on these systems

The limitations section is the one that makes this worth sending. A bundle that
lists only what was found invites the reader to assume the rest is solid; this
one tells them where it is not, using the same checks that are published on the
site.

Nothing is recomputed here. Every figure is read from the table that produced it
and carries that table's name, so a disagreement between the bundle and the
platform is impossible by construction rather than by discipline.
"""
from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timezone
from pathlib import Path

import duckdb

from . import ids


def _exists(con, qualified: str) -> bool:
    schema, _, table = qualified.partition(".")
    return con.execute(
        "SELECT count(*) FROM information_schema.tables "
        "WHERE table_schema = ? AND table_name = ?", [schema, table]).fetchone()[0] > 0


def _rows(con, sql, params=None) -> list[dict]:
    cur = con.execute(sql, params or [])
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def _systems_touched(items: list[dict]) -> set[str]:
    """Which systems an investigation's items plausibly draw on.

    Derived from the kinds of thing collected rather than declared, so the
    limitations section cannot claim relevance it does not have.
    """
    kinds = {(i["kind"], i["namespace"]) for i in items}
    systems: set[str] = set()
    for kind, ns in kinds:
        if ns in ("contribution", "agreement", "transaction", "application"):
            systems |= {"ledger", "plumbline"}
        if ns == "company":
            systems |= {"bellwether", "sentinel", "watchman"}
        if ns in ("lad", "postcode", "uprn"):
            systems |= {"catchment", "lastmile", "baseline", "bulwark", "highwater"}
        if ns == "organisation":
            systems |= {"ledger", "plumbline", "sightline"}
    return systems


def _provenance_for(con, items: list[dict]) -> list[dict]:
    """The registry entry and latest retrieval for every source involved."""
    from . import sources as S
    systems = _systems_touched(items)
    wanted = [s for s in S.REGISTRY
              if not systems or (set(s.systems) & systems) or s.role != "domain"]
    log = {}
    if _exists(con, "bronze.fetch_log"):
        log = {r["source_id"]: r for r in _rows(con, """
            WITH last AS (SELECT *, row_number() OVER
                   (PARTITION BY source_id ORDER BY fetched_at DESC) rn
                 FROM bronze.fetch_log WHERE ok)
            SELECT source_id, fetched_at, http_status, sha256, bytes_len, final_url
            FROM last WHERE rn = 1""")}
    out = []
    for s in wanted:
        rec = log.get(s.id)
        out.append({
            "id": s.id, "name": s.name, "publisher": s.publisher,
            "url": s.url, "licence": s.licence, "cadence": s.cadence,
            "role": s.role, "systems": list(s.systems),
            "blocked": s.blocked,
            "retrieved_at": rec["fetched_at"].isoformat() if rec else None,
            "http_status": rec["http_status"] if rec else None,
            "sha256": rec["sha256"] if rec else None,
            "bytes": rec["bytes_len"] if rec else None,
            # Stated plainly: a source with no retrieval record is data whose
            # provenance this bundle cannot vouch for.
            "retrieval_recorded": bool(rec),
        })
    return sorted(out, key=lambda r: (not r["retrieval_recorded"], r["id"]))


def _records_for(con, item: dict) -> list[dict]:
    """The stored rows behind one item, each naming its table."""
    ident = ids.parse(item["identifier"])
    found: list[dict] = []

    if ident.kind == "entity" and ident.namespace == "company":
        for table, col in (("gold.entity", "company_number"),
                           ("gold.bellwether_footprint", "company_number"),
                           ("gold.watchman_distress", "company_number"),
                           ("gold.sentinel_repeat", "supplier_id")):
            if _exists(con, table):
                rows = _rows(con, f"SELECT * FROM {table} WHERE {col} = ? LIMIT 25",
                             [ident.key])
                if rows:
                    found.append({"table": table, "rows": rows})

    elif ident.kind == "entity" and ident.namespace == "organisation":
        # A planning authority. Its own row names it; the ledger row is what it
        # collected, and is joined on the name the authority table supplies.
        name = None
        if _exists(con, "silver.planning_authority"):
            rows = _rows(con, "SELECT * FROM silver.planning_authority WHERE entity = ?",
                         [int(ident.key)])
            if rows:
                name = rows[0].get("name")
                found.append({"table": "silver.planning_authority", "rows": rows})
        if name and _exists(con, "gold.ledger_authority"):
            rows = _rows(con, "SELECT * FROM gold.ledger_authority WHERE authority = ?",
                         [name])
            if rows:
                found.append({"table": "gold.ledger_authority", "rows": rows})

    elif ident.kind == "place" and ident.namespace == "lad":
        for table in ("gold.catchment_district", "gold.lastmile_authority",
                      "gold.baseline_district", "gold.bulwark_district",
                      "gold.highwater_district"):
            if _exists(con, table):
                rows = _rows(con, f"SELECT * FROM {table} WHERE lad_code = ? LIMIT 5",
                             [ident.key])
                if rows:
                    found.append({"table": table, "rows": rows})

    elif ident.kind == "event" and ident.namespace in ("contribution", "agreement"):
        try:
            org, ref = ids.split_qualified(ident)
        except ids.IdentifierError:
            return found
        if ident.namespace == "contribution" and _exists(con, "silver.contribution"):
            rows = _rows(con, "SELECT * FROM silver.contribution "
                              "WHERE reference = ? AND organisation_entity = ?",
                         [ref, int(org)])
            if rows:
                found.append({"table": "silver.contribution", "rows": rows})
        if ident.namespace == "agreement" and _exists(con, "silver.developer_agreement"):
            rows = _rows(con, "SELECT * FROM silver.developer_agreement "
                              "WHERE reference = ? AND organisation_entity = ?",
                         [ref, int(org)])
            if rows:
                found.append({"table": "silver.developer_agreement", "rows": rows})
    return found


def _limitations(con, items: list[dict]) -> dict:
    """What the reader should not conclude from this bundle."""
    from . import claims as C
    systems = _systems_touched(items)

    relevant_claims = [c for c in C.ARCHIVE
                       if c.system in systems or c.system == "platform"]

    gaps_out: dict = {}
    try:
        from . import gaps as G
        report = G.report(con)
        gaps_out = {
            "not_published_anywhere": report["not_published_anywhere"],
            "fixable_here": report["fixable_here"],
        }
    except Exception as exc:
        gaps_out = {"error": str(exc).splitlines()[0]}

    contradictions_out: list = []
    try:
        from . import contradictions as CD
        full = CD.run_all(con, limit=3)
        contradictions_out = [
            {"check": r["check"], "quantity": r["quantity"],
             "compared": r.get("compared"), "disagreed": r.get("disagreed"),
             "agreement_pct": r.get("agreement_pct"), "note": r.get("note")}
            for r in full["results"] if r["run"] and r["disagreed"]]
    except Exception as exc:
        contradictions_out = [{"error": str(exc).splitlines()[0]}]

    return {
        "corrected_claims": [
            {"id": c.id, "system": c.system, "believed": c.believed,
             "actually": c.actually, "guard": c.guard}
            for c in relevant_claims],
        "evidence_gaps": gaps_out,
        "internal_disagreements": contradictions_out,
        "standing_caveats": [
            "The place spine is built on Code-Point Open, which covers Great "
            "Britain. Any coverage figure here is GB, never UK.",
            "Figures are computed over the records that state a value. Where a "
            "coverage percentage is given, the remainder is unknown rather than "
            "zero.",
            "Name matches are scored and ties are reported as ambiguous. Nothing "
            "in this bundle was merged on a name alone below the accept threshold.",
        ],
    }


def build(con: duckdb.DuckDBPyConnection, investigation: str) -> dict:
    """Assemble the bundle."""
    from . import investigations as I
    from . import profiles as P

    inv = I.get(con, investigation)
    live = inv.live_items

    subjects = []
    for item in live:
        entry = {"identifier": item["identifier"], "kind": item["kind"],
                 "namespace": item["namespace"], "why": item["why"],
                 "found_via": item["found_via"],
                 "added_at": item["added_at"].isoformat() if item["added_at"] else None,
                 "records": _records_for(con, item)}
        try:
            if item["kind"] == "entity" and item["namespace"] == "company":
                entry["profile"] = P.organisation_profile(con, item["identifier"])
            elif item["kind"] == "place":
                entry["profile"] = P.place_profile(con, item["identifier"])
        except Exception as exc:
            entry["profile"] = {"error": str(exc).splitlines()[0]}
        subjects.append(entry)

    snapshot = None
    if _exists(con, "history.manifest"):
        row = con.execute("SELECT snapshot_id, max(taken_at) FROM history.manifest "
                          "GROUP BY snapshot_id ORDER BY 2 DESC LIMIT 1").fetchone()
        snapshot = row[0] if row else None

    return {
        "bundle": {
            "investigation": inv.id,
            "name": inv.name,
            "question": inv.question,
            "opened": inv.created_at.isoformat(),
            "closed": inv.closed_at.isoformat() if inv.closed_at else None,
            "outcome": inv.outcome,
            "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "snapshot": snapshot,
        },
        "summary": {
            "subjects": len(live),
            "by_kind": inv.by_kind(),
            "ruled_out": len(inv.ruled_out),
            "notes": len(inv.notes),
            "systems_touched": sorted(_systems_touched(live)),
        },
        "method": [
            "Resolve each subject to a Groundtruth identifier derived from the "
            "publisher's own key, so it can be re-resolved independently.",
            "Read every figure from the gold table the system wrote; recompute "
            "nothing, so the bundle cannot disagree with the platform.",
            "Report the match type for every join: an identifier match and a "
            "name match are not the same evidence.",
            "State coverage with every statistic, and list what could not be "
            "determined at all.",
        ],
        "subjects": subjects,
        "ruled_out": [
            {"identifier": i["identifier"], "why_added": i["why"],
             "ruled_out_because": i["removed_because"],
             "removed_at": i["removed_at"].isoformat() if i["removed_at"] else None}
            for i in inv.ruled_out],
        "notes": [{"at": n["noted_at"].isoformat(), "text": n["text"]}
                  for n in inv.notes],
        "sources": _provenance_for(con, live),
        "limitations": _limitations(con, live),
    }


def to_json(bundle: dict) -> str:
    return json.dumps(bundle, indent=2, default=str)


def to_markdown(bundle: dict) -> str:
    """A readable pack. Deliberately plain: this gets pasted into an email."""
    b, s = bundle["bundle"], bundle["summary"]
    out: list[str] = []
    w = out.append

    w(f"# {b['name']}")
    w("")
    if b["question"]:
        w(f"**Question.** {b['question']}")
        w("")
    w(f"Groundtruth evidence bundle · generated {b['generated']}"
      + (f" · snapshot `{b['snapshot']}`" if b["snapshot"] else ""))
    w("")
    if b["outcome"]:
        w(f"**Outcome.** {b['outcome']}")
        w("")

    w("## Summary")
    w("")
    w(f"- {s['subjects']} subjects: "
      + ", ".join(f"{n} {k}" for k, n in sorted(s["by_kind"].items())))
    w(f"- {s['ruled_out']} ruled out, {s['notes']} notes")
    w(f"- systems drawn on: {', '.join(s['systems_touched']) or 'none'}")
    w("")

    w("## How this was assembled")
    w("")
    for step in bundle["method"]:
        w(f"- {step}")
    w("")

    w("## Subjects")
    w("")
    for sub in bundle["subjects"]:
        w(f"### `{sub['identifier']}`")
        w("")
        w(f"Included because: {sub['why']}")
        if sub.get("found_via"):
            w(f"Found via: {sub['found_via']}")
        w("")
        prof = sub.get("profile") or {}
        if prof.get("resolved"):
            name = prof.get("name") or prof.get("lad_code")
            w(f"**{name}** — {prof.get('systems_with_data')} of "
              f"{prof.get('systems_checked')} systems hold data"
              + (f", {prof.get('by_identifier')} matched on an identifier and "
                 f"{prof.get('by_name')} on a name" if prof.get("by_name") is not None else ""))
            w("")
        for rec in sub["records"]:
            w(f"- `{rec['table']}` — {len(rec['rows'])} row(s)")
        w("")

    if bundle["ruled_out"]:
        w("## Ruled out")
        w("")
        w("Kept deliberately: a line of enquiry that was closed is a finding.")
        w("")
        for r in bundle["ruled_out"]:
            w(f"- `{r['identifier']}` — added because {r['why_added']}; "
              f"ruled out because {r['ruled_out_because']}")
        w("")

    if bundle["notes"]:
        w("## Notes")
        w("")
        for n in bundle["notes"]:
            w(f"- {n['at']} — {n['text']}")
        w("")

    w("## Sources")
    w("")
    w("| Source | Publisher | Licence | Retrieved | Status | Checksum |")
    w("|---|---|---|---|---|---|")
    for src in bundle["sources"]:
        got = src["retrieved_at"] or "**not recorded**"
        sha = (src["sha256"] or "")[:12] or "—"
        w(f"| {src['id']} | {src['publisher']} | {src['licence']} | {got} "
          f"| {src['http_status'] or '—'} | `{sha}` |")
    w("")
    unrecorded = [s for s in bundle["sources"] if not s["retrieval_recorded"]]
    if unrecorded:
        w(f"> {len(unrecorded)} of {len(bundle['sources'])} sources have no recorded "
          f"retrieval. Their data is present and this bundle cannot vouch for when "
          f"it was obtained or whether it has changed since.")
        w("")

    lim = bundle["limitations"]
    w("## Limitations")
    w("")
    w("Read this section before quoting anything above.")
    w("")
    for caveat in lim["standing_caveats"]:
        w(f"- {caveat}")
    w("")

    gaps = lim.get("evidence_gaps") or {}
    if gaps.get("not_published_anywhere"):
        w("### Not published anywhere in the UK")
        w("")
        w("No platform can close these; they are gaps in national data.")
        w("")
        for g in gaps["not_published_anywhere"]:
            w(f"- **{g['chain']} / {g['step']}** — {g['reason']}")
        w("")
    if gaps.get("fixable_here"):
        w("### Not yet joined by this platform")
        w("")
        for g in gaps["fixable_here"]:
            w(f"- **{g['chain']} / {g['step']}** — {g['reason']}")
        w("")

    if lim["internal_disagreements"]:
        w("### Where this platform disagrees with itself")
        w("")
        for d in lim["internal_disagreements"]:
            if "error" in d:
                continue
            w(f"- `{d['check']}` — {d['disagreed']} of {d['compared']} compared "
              f"({d['agreement_pct']}% agreement) on {d['quantity']}")
        w("")

    if lim["corrected_claims"]:
        w("### Claims this platform has already corrected")
        w("")
        w("Published in full so a reader can judge the error rate rather than "
          "take an assurance.")
        w("")
        for c in lim["corrected_claims"]:
            w(f"- **{c['id']}** ({c['system']}) — believed: {c['believed'][:150]}… "
              f"Actually: {c['actually'][:200]}…")
        w("")

    w("---")
    w("")
    w("Every figure above is read from the table that produced it. Reproduce with "
      "`gt bundle <investigation>`; check the sources with `gt audit --network`; "
      "see the full correction archive with `gt claims`.")
    return "\n".join(out)


def _csv(rows: list[dict]) -> str:
    if not rows:
        return ""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(rows[0]))
    writer.writeheader()
    for r in rows:
        writer.writerow({k: ("" if v is None else v) for k, v in r.items()})
    return buf.getvalue()


def write(con: duckdb.DuckDBPyConnection, investigation: str,
          dest: Path) -> dict:
    """Write the bundle out as a directory of files.

    JSON for a machine, Markdown for a person, CSV for a spreadsheet. The same
    content three ways rather than three different selections of it.
    """
    bundle = build(con, investigation)
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)

    written = []
    (dest / "bundle.json").write_text(to_json(bundle))
    written.append("bundle.json")
    (dest / "README.md").write_text(to_markdown(bundle))
    written.append("README.md")

    sources_csv = _csv(bundle["sources"])
    if sources_csv:
        (dest / "sources.csv").write_text(sources_csv)
        written.append("sources.csv")

    subjects = [{"identifier": s["identifier"], "kind": s["kind"],
                 "namespace": s["namespace"], "why": s["why"],
                 "found_via": s["found_via"], "added_at": s["added_at"],
                 "tables": ";".join(r["table"] for r in s["records"])}
                for s in bundle["subjects"]]
    subjects_csv = _csv(subjects)
    if subjects_csv:
        (dest / "subjects.csv").write_text(subjects_csv)
        written.append("subjects.csv")

    records_dir = dest / "records"
    n_records = 0
    for sub in bundle["subjects"]:
        for rec in sub["records"]:
            records_dir.mkdir(parents=True, exist_ok=True)
            safe = (ids.short(sub["identifier"], 10) + "_"
                    + rec["table"].replace(".", "_") + ".csv")
            (records_dir / safe).write_text(_csv(rec["rows"]))
            n_records += 1
    if n_records:
        written.append(f"records/ ({n_records} files)")

    return {"path": str(dest), "files": written,
            "subjects": bundle["summary"]["subjects"],
            "sources": len(bundle["sources"]),
            "sources_without_retrieval_record":
                sum(1 for s in bundle["sources"] if not s["retrieval_recorded"])}
