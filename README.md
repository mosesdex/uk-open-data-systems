# Ten Open Data Systems for the United Kingdom

A research-backed portfolio of ten public service systems, each built on free, openly licensed UK government data, and each addressing a gap that government has documented in its own words.

**Live site:** https://mosesdex.github.io/uk-open-data-systems/

Prepared by **Dexter DCL**, an independent UK company. This is a private proposal document. It is not a government publication and carries no government endorsement.

---

## The thesis

The UK has some of the best open government data in the world, and a striking pattern of publishing data nobody joins, retiring measures it still needs, and running multi-billion pound programmes on evidence it admits is incomplete.

That is not an outside opinion. It is government's own account of itself. The team running the national data portal wrote in 2026 that "the original approach has failed and led to broken links and low usage," with more than a quarter of links leading to error pages.

Every system here starts from an admission like that — a National Audit Office report, a Public Accounts Committee finding, or a dataset whose own documentation concedes what it does not know.

## The ten systems

| # | System | Addresses |
|---|---|---|
| 01 | **Sentinel** | Procurement integrity and collusion detection |
| 02 | **Transit** | Local government reorganisation data continuity |
| 03 | **Compass** | SEND demand forecasting and transport optimisation |
| 04 | **Threshold** | Temporary accommodation cost and placement intelligence |
| 05 | **Plumbline** | Planning pipeline truth and delivery measurement |
| 06 | **Highwater** | Floodplain development monitoring |
| 07 | **Catchment** | School place planning at the geography that matters |
| 08 | **Waypoint** | Public transport accessibility measurement |
| 09 | **Hearth** | Retrofit outcome accountability |
| 10 | **Junction** | Unified grid connection queue intelligence |

## Selected findings

Figures verified against primary sources in August 2026.

- The Environment Agency's planning objections dataset contains **23,336 records across 426 authorities**, of which **7,011 — 30% — have an outcome recorded as unknown**. Permissions granted against its flood advice rose from **28 in 2021-22 to 102 in 2024-25**.
- England has **3,651 pupil planning areas** and publishes the boundaries of none of them as open geospatial data.
- The statutory debarment list contains **zero suppliers**, 21 months after the regime commenced. The Competition and Markets Authority withdrew its cartel screening tool in **January 2020** and never replaced it.
- The Public Accounts Committee found that DfE **"does not know whether home to school transport is achieving value for money"** — a £2.6bn annual spend.
- **134 councils** are being merged into **38 unitary authorities** with a vesting day of **1 April 2028**.
- Four of six distribution network operators return **zero rows** to anonymous clients; the only national aggregation is six months stale and named `ecr_manual_combine_test`.

## What was rejected, and why

The portfolio documents six ideas that were researched properly and left out — including retrofit targeting (blocked by data protection law and already served commercially), land ownership transparency (government committed to opening it in 2026), and a council financial distress tracker (more than 300 councils hold disclaimed audit opinions, so any model inherits the disclaimer).

## Build

Static site, no framework, no build dependencies beyond Node.

```bash
node build.js
```

Content lives in `data/systems-a.js` and `data/systems-b.js`. `build.js` generates `index.html` and `systems/*.html`. Styles in `assets/style.css`; progressive-enhancement JS in `assets/app.js`.

## Sources and licence

Every system brief carries its sources. Figures that could not be verified against a primary source were not used, and where underlying data is weak the brief says so rather than rounding the uncertainty away.

Contains public sector information licensed under the [Open Government Licence v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/).

Code and content in this repository: [MIT](LICENSE).
