# Groundtruth prototype

Three interfaces over the platform:

| File | Interface |
|---|---|
| `index.html` | Public — reads real platform output |
| `admin.html` | Admin — feed health, pipeline, review queue |
| `mobile.html` | Mobile — device frame, tabbed |

## It reads what the platform computed

`data/platform.json` is written by the platform, not by hand:

```bash
cd ../platform
./.venv/bin/python -m groundtruth.cli publish
```

That writes every gold table the platform has produced, stamped with the run
time. The public interface renders from it through `assets/platform.js`. If the
file is missing the page says so rather than falling back to figures typed in
earlier — a missing panel is honest, a stale one is not.

Currently live from real output:

| Figure | Value | System |
|---|---|---|
| Mainstream school places in use | 89.6% | Catchment |
| Specialist settings over capacity | 629 | Catchment |
| Developer contributions recorded | £1.49bn | Ledger |
| Flood defence inspections overdue | 7,300 | Bulwark |
| Decided within the statutory deadline | 15.9% | Plumbline |
| Growth in statutory EHC plans | 127.4% | Compass |
| Spills adjusted for monitor uptime | 300,326 | Baseline |

The choropleth is Catchment's per-district output over real ONS boundaries, and
clicking a district shows its utilisation, the **coverage that figure rests on**,
and its organisation-resolution rate. The source table is the fetcher's own
recorded HTTP status, not a claim about what should work.

The overdue-inspection count moves between runs because it is computed against
the current date. That is the system working, not drift.

## All thirteen systems are visible, with results

Every system card on the public and mobile interfaces carries the measured
headline that system produced — not a description of what it would do:

| System | What it found |
|---|---|
| Catchment | 89.6% of mainstream school places in use |
| Sentinel | 6.6% of awards skipped open competition |
| Highwater | 635 permissions granted against flood advice |
| Plumbline | 15.9% decided within the legal deadline |
| Junction | 937 of 6,770 capacity records actually served |
| Ledger | £1.49bn recorded, 0 of it mappable |
| Bellwether | 124 authorities depend on one care group |
| Sightline | 180 water quality objections, no outcome field |
| Lastmile | 66.7% gigabit in new-build postcodes |
| Bulwark | 7,300 inspections overdue |
| Watchman | register must accumulate before it produces signal |
| Compass | +127.4% growth in statutory EHC plans |
| Baseline | 300,326 spills after adjusting for uptime |

A system with no output says so rather than showing a description in place of a
result.

## A bug worth recording

Reveal-on-scroll never fired for content reached by a deep link. Landing on
`#systems` jumped the page past the observer, so the section stayed **invisible
permanently** — the whole point of the page, blank. Elements already on screen
are now revealed immediately, `hashchange` re-runs the check, and a timeout
guarantees nothing stays hidden because an observer misfired.

## Still illustrative

Admin throughput, the match-review queue, users and the audit log remain sample
data, labelled as such in the interface.
