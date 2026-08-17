# Groundtruth

**One platform. Thirteen public data systems. No registration anywhere.**

British government publishes records that say *what* happened but not, in any form a
computer can match, *where* it happened or *who* it involved. Groundtruth resolves those
two things — and thirteen systems become possible that are not possible today.

Live: **https://mosesdex.github.io/uk-open-data-systems/**

## The two spines

| Spine | Resolves | Systems |
|---|---|---|
| **Place** | Planning references, sites and assets to canonical property identifiers and coordinates | 7 |
| **Entity** | Organisations and assets to canonical identifiers across registers | 4 |
| **Both** | | 2 |

## The thirteen systems

| # | System | What it does |
|---|---|---|
| 01 | Sentinel | Public procurement integrity and collusion detection |
| 03 | Compass | SEND demand forecasting (aggregate half) |
| 05 | Plumbline | Honest planning performance measurement |
| 06 | Highwater | Floodplain development monitoring |
| 07 | Catchment | School place planning at the geography that matters |
| 10 | Junction | Unified grid connection queue intelligence |
| 11 | Ledger | Developer contributions, made mappable |
| 12 | Bellwether | Provider concentration and failure exposure |
| 13 | Sightline | Statutory consultee advice, and what happened to it |
| 14 | Lastmile | Connectivity at new homes |
| 16 | Bulwark | Flood defence ownership and condition |
| 17 | Watchman | Insolvency exposure across public suppliers |
| 18 | Baseline | Sewage spills, adjusted for the weather |

Five further systems are published but sit outside Groundtruth — two need
security-cleared UK staff, one needs a registered account, and two were rejected by the
research itself. Reasons are stated on the site.

## The access standard

Every dataset these thirteen depend on was tested and returns data to an anonymous
request: **no account, no API key, no application, no approval.** There is no
registration to revoke and no licence to terminate.

## Build

```bash
node build.js
```

Static output. Content lives in `data/`; `build.js` generates `index.html`,
`platform.html` and `systems/*.html`.

## Note on accuracy

Fifteen published claims were corrected during research, including one figure that was
derived and then presented as though a source had stated it. Roughly half of what
sounded solid needed correction once someone checked the primary source. Every system
brief carries its sources for that reason.

---

Prepared by Dexter DCL. A private proposal document — not a government publication, and
carrying no government endorsement. Contains public sector information licensed under
the Open Government Licence v3.0.
