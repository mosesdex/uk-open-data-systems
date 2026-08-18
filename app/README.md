# Groundtruth prototype

Three interfaces over the same platform:

| File | Interface | For |
|---|---|---|
| `index.html` | Public | Coverage map, the two links, thirteen systems, source catalogue |
| `admin.html` | Admin | Feed health, ingest pipeline, match review queue, alert rules, audit log |
| `mobile.html` | Mobile | Alerts, local picture, systems and search, in a device frame |

No build step and no dependencies — open any file directly, or serve the folder.

## What is real

- Boundaries: ONS Local Authority Districts, May 2024, ultra-generalised (318 features)
- School figures: DfE GIAS full extract, 17 August 2026 (52,486 establishments, 27,167 open)
- Linkage coverage: computed, not estimated — 96.5% carry a property reference, 45.4% a trust identifier
- Source catalogue: every row returned HTTP 200 to an unauthenticated request on 17 August 2026

## What is illustrative

Admin throughput figures, the match review queue, users and the audit log are sample data for
demonstration. They are labelled as such in the interface.

## Design

Union Flag palette — Pantone 280 blue, Pantone 186 red, white — used structurally for navigation,
emphasis and alerting rather than decoratively. Charts, maps and counters are drawn as SVG at
runtime with no charting library.
