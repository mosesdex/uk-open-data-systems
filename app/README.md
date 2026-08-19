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

## Still illustrative

Admin throughput, the match-review queue, users and the audit log remain sample
data, labelled as such in the interface.
