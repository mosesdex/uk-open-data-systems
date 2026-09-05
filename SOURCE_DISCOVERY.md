# GroundTruth — data-source discovery roadmap

Deep discovery pass across all 13 systems. **Only Tier A sources are listed** — freely
downloadable or queryable with **no account, no login, no API key, no OAuth, no
subscription, no payment, no manual approval**. Sources needing any of those are
recorded under "Excluded" per system, not in the qualifying lists. Every dataset was
reachability-checked by the research pass; licences noted (almost all OGL v3 or CC0/CC-BY).

Tiers: **1 = critical / new capability** · **2 = big coverage or accuracy gain** ·
**3 = useful context / validation** · **4 = optional**.

---

## The seven cross-cutting unlocks

These recur across many systems and are the highest-leverage things to wire first.

1. **PlanIt API** (`planit.org.uk/api/`) — no-key JSON/CSV/GeoJSON of ~20.6M planning
   applications from ~420 LPAs, 91% geolocated, with decision outcome + dates. Unlocks
   **Highwater, Plumbline, Ledger, Sightline** (the planning four). Rate-limited, aggregated
   from LA registers — confirm attribution/reuse terms before republishing.
2. **planning.data.gov.uk** (MHCLG) — CSV/JSON/GeoJSON/Parquet, OGL. The `developer-agreement`
   → `planning-application` join, brownfield-land (ref + coords), LPA boundaries. Native IDs
   across the planning systems.
3. **DfE Explore Education Statistics** — keyless `/csv` per dataset + `api.education.gov.uk/statistics/v1`.
   Unlocks **Catchment** (school capacity 2009/10–2023/24) and **Compass** (EHCP/SEN/DSG).
4. **EA Defra Data Services Platform** (`environment.data.gov.uk`) — WFS/OGC/GeoJSON/ZIP, OGL.
   Unlocks **Bulwark** (AIMS asset geometry), **Highwater/Sightline** (flood zones, WFD
   catchments), **Baseline** (EDM back-years, Water Quality Archive).
5. **Companies House Free Company Data snapshot** (`download.companieshouse.gov.uk`) — monthly
   ZIP, OGL. Status + overdue accounts/confirmation-statement dates (= distress), SIC, dissolution.
   Unlocks **Watchman**, strengthens **Sentinel/Bellwether**. (The keyed REST/streaming API is
   NOT needed and does not qualify.)
6. **OpenOwnership BODS (CC0)** + **GLEIF LEI golden copy & Level-2 relationships (CC0)** — the
   corporate-group / ultimate-parent graph above PSC. Unlocks deeper **WHO** for
   **Sentinel, Bellwether, Watchman** and the org knowledge-graph.
7. **ONS Open Geography** — ONSPD / NSUL / NSPL / LAD boundaries. The universal **WHERE**
   backbone: postcode & UPRN → LAD, and district polygons for every choropleth.

---

## Cross-system bridge datasets (item 17)

The most valuable finds are not new statistics — they are the **identifiers that let systems join**.

- **`planning-application` reference** bridges **Ledger ↔ Plumbline ↔ Highwater ↔ Sightline**.
  One planning ref → PlanIt/brownfield coordinates → all four planning systems share a site.
- **Company number** bridges **Sentinel ↔ Bellwether ↔ Watchman**; OpenOwnership/GLEIF add the
  parent/group edges so an organisation's footprint spans procurement + care + distress.
- **WFD `water_body_id`** bridges **Sightline ↔ Baseline** (objections ↔ actual spills/quality).
- **ONS LAD code + UPRN/postcode** bridges every geographic system to one district spine.
- **360Giving `GB-COH` recipient id + UK Subsidy beneficiary** give an org's *total* public money
  (contracts + grants + subsidies) — a new cross-channel WHO metric spanning Sentinel + Watchman.

---

## Per-system findings

### 1. Catchment (school places vs pupils, WHERE)
- **Have:** GIAS establishments, ONS births, OS UPRN/Linked Identifiers.
- **Top new (Tier 1):** DfE **School Capacity ("Capacity - school")** — 282k rows, 2009/10–2023/24,
  places vs pupils per school with over-capacity/unfilled, keyed by URN / new_la_code / planning-area;
  **LA pupil forecasts** (to 2031/32, incl. housing-driven places); **Applications & offers**
  (oversubscription); **Special-school capacity + specialist-in-mainstream** (the specialist split);
  **GIAS all-groups** (trust → **Companies House number** = WHO).
- **Tier 2:** LA planned place changes (basic need); Schools/pupils characteristics (FSM/deprivation).
- **Best joins:** `school_urn`, `new_la_code` (LAD), `planning_area_code`, trust `Companies House Number`.
- **New capability:** snapshot → **14-year trend + forward forecast**; places-vs-need weighted by
  deprivation; shortfall attributed to the responsible **trust (WHO)**.
- **Gap:** no open national catchment-area / place-planning-area **polygons** (join by code, can't map the areas).
- **Priority: HIGH** (turns the exemplar system from point-in-time into a time series).

### 2. Sentinel (procurement concentration + ownership, WHO)
- **Have:** Contracts Finder + Find a Tender OCDS, CH PSC + index, Charity register, Gazette.
- **Top new (Tier 1):** **GLEIF LEI + Level-2 parent relationships (CC0)** — corporate-group layer
  above PSC, incl. cross-border parents, RA-entity-id = CH number; **OpenOwnership BODS bulk (ODC-BY)**
  — beneficial-owner graph; **Public Contracts Scotland** + **Sell2Wales** OCDS (devolved contracts
  absent from Contracts Finder); **360Giving grants** (`grants.csv`, GB-COH recipient ids).
- **Tier 2:** **Payment Practices Reporting** (`check-payment-practices.service.gov.uk/export/csv/` —
  supplier late-payment behaviour, keyed by company number).
- **Tier 3:** UK Subsidy Transparency DB; Crown Representatives & Strategic Suppliers list; OpenOpps/TBFY OCDS archive.
- **Best joins:** company number, OCID, LEI, buyer id, recipient GB-COH id.
- **New capability:** see one **ultimate parent** behind several "competing" suppliers; an org's public
  money across **contracts + grants + subsidies**; devolved-nation coverage.
- **Gap:** CH officers/appointments + charges are request-only (not Tier A); no free national aggregation
  of LA contract registers with common IDs; subsidy/strategic-supplier feeds are name-only.
- **Priority: HIGH** (directly deepens the WHO join and the org graph).

### 3. Highwater (flood objections vs approvals over time, WHERE)
- **Have:** EA flood-risk objections; OS UPRN/Linked Identifiers.
- **Top new (Tier 1):** **PlanIt** (the outcome+date join — pairs each objection to its decision, lets
  the override rate be tracked per LPA per year); **EA Flood Map for Planning Zones 2 & 3** (WFS/GeoJSON
  — independent flood-risk denominator: approvals *in* FZ2/FZ3 regardless of formal objection); **LPA
  boundaries** (crosswalk backbone).
- **Tier 2:** Planning Inspectorate appeals casework (the appeal-stage override channel); **Recorded Flood
  Outlines** (1946– , with dates — "approved-against-advice then actually flooded").
- **Tier 3:** Flood Warning / Alert Areas.
- **Best joins:** LPA code, application reference, postcode, easting/northing, geometry (point-in-polygon).
- **New capability:** override rate becomes a **per-LPA year-on-year league table**; realised-harm story
  (approvals later flooded).
- **Gap:** no single dataset natively links an objection to its specific application — inferred by ref/coord match.
- **Priority: HIGH.**

### 4. Plumbline (statutory vs headline planning speed, WHERE)
- **Have:** MHCLG PS2 (aggregate LPA counts).
- **Top new (Tier 1):** **PlanIt** application-level dates — recompute each decision against the 13-week
  statutory clock and detect extensions from raw records rather than trusting LPA "on-time" figures;
  **Live tables P120/P122/P123** (the official headline series incl. "within 13 weeks" vs "agreed
  extension" — the benchmark, plus historical back-years); **Housing Delivery Test** measurements;
  **LPA boundaries**; **planning.data.gov.uk planning-application** (native-ID, maturing).
- **Tier 1 (London):** London Development Database (developer identity + completions).
- **Best joins:** LPA code, application reference, applicant_company → CH number (London cleanest).
- **New capability:** reconstruct the statutory-vs-headline gap from **raw application records**; correlate
  lenient extensions with under-delivery (HDT).
- **Gap:** no national field flags extension-of-time/PPA — must be inferred; developer→company clean only for London.
- **Priority: HIGH.**

### 5. Junction (grid capacity served vs advertised)
- **Have:** 4 DNO Embedded Capacity Registers.
- **Top new (Tier 1):** **NGED (ex-WPD) ECR** + **SSEN ECR** — completes **all six GB DNO groups**;
  **UKPN Grid & Primary Sites** + **NPg Heatmap Substation Areas** (substation coordinates + advertised
  headroom = the WHERE layer + the advertised side).
- **Tier 2:** NESO **TEC Register** (transmission connection queue); NESO Embedded Register (Scotland
  cross-check); NGED LTDS + Network Development Plan (firm/advertised capacity + headroom).
- **Best joins:** operator, substation name/GSP, licence area, easting/northing, capacity MW.
- **New capability:** full-GB served-vs-advertised; map connections to substation coordinates; contrast
  embedded (DNO) against the transmission queue.
- **Gap:** no consistent cross-DNO substation-ID/coordinate crosswalk — needs fuzzy name + easting/northing matching.
- **Priority: MEDIUM-HIGH** (mechanical — same schema, drops in; doubles coverage).

### 6. Ledger (developer contributions, WHERE was missing)
- **Have:** MHCLG developer-agreement-contribution; OS UPRN/Linked Identifiers.
- **THE unlock (Tier 1):** the parent **`developer-agreement`** record carries a **`planning-application`
  reference** → join to **PlanIt / planning.data.gov.uk planning-application / brownfield-land** for
  coordinates. **The locationless money becomes mappable.** Plus **developer-agreement-transaction**
  (promised→secured→spent status), **brownfield-land** (ref + point in one file), **Infrastructure Funding
  Statement** index.
- **Tier 2:** s106tracker.co.uk (IFS cross-check, licence caveat).
- **Best joins:** developer-agreement key, planning-application reference, coordinates/UPRN, LPA code.
- **New capability:** **map S106/CIL for the first time** (the system's headline "0 mappable" finding
  flips to a derived, honest geography); promised-vs-spent by purpose *and place*.
- **Gap:** the ref→coordinate join is probabilistic (free-text refs); developer→company number weak
  (identity lives in deed PDFs). GroundTruth should materialise & publish this derived mappable ledger as its own value-add.
- **Priority: HIGH** (converts the weakest system's core limitation into a capability).

### 7. Bellwether (care provider concentration, WHO)
- **Have:** CQC active locations, CH PSC + index, Charity register, Gazette, GIAS.
- **Top new (Tier 1):** **CQC "Care directory with filters" ODS** — carries **per-location bed counts**
  (the capacity denominator we lack); **CQC Market Oversight list** (~60 systemic corporate groups —
  the exact target entities + validation set); **OpenOwnership BODS (CC0)** — pre-built ownership/parent
  graph resolving brand → owning company → group.
- **Tier 2:** NHS ODS "Social Care Providers and Sites" (ODS code crosswalk, parent→site); CQC "Care
  directory with ratings"; **Ofsted children's-homes MI** (extends to children's social care).
- **Best joins:** CQC location/provider id, company number, ODS code, postcode, LA code.
- **New capability:** concentration by **actual beds** not just location counts; quality (ratings) across a
  group's estate; children's social care as a second domain.
- **Gap:** no open **CQC provider id → company number** bridge (build via name/postcode/PSC); occupancy not open.
- **Priority: HIGH** (beds unlock the real concentration metric).

### 8. Sightline (water-quality planning objections, WHERE)
- **Have:** EA flood-risk objections (reused).
- **Top new (Tier 1):** **WFD River Water Body Catchments (GeoJSON, `water_body_id`)** — the spatial spine;
  **WFD classifications + RNAG reason codes** (official reason taxonomy + status); **Natural England
  Nutrient-Neutrality Catchments** (the single biggest driver of water-quality objections nationally);
  **PlanIt** (application corpus by authority); **planning.data.gov.uk** designations.
- **Tier 2:** Water Quality Archive (measured evidence); EDM storm overflows (adds water-company WHO);
  Protected Sites SSSI/SAC/SPA.
- **Tier 3:** Bathing Water Quality; Rivers Trust sewage-map layers.
- **Best joins:** `water_body_id`, catchment id, LPA code, application lat/lon (point-in-polygon).
- **New capability:** thin sampled reasons → a real system: objections joined to **actual water-body status,
  nutrient catchments, and spills**.
- **Gap:** statutory-consultee responses aren't open structured data — must be scraped/classified.
- **Priority: MEDIUM-HIGH** (biggest relative upgrade — currently the weakest system).

### 9. Lastmile (gigabit new-build vs existing, WHERE)
- **Have:** BDUK OMR premises, HMLR Price Paid, OS UPRN/Linked Identifiers.
- **Top new (Tier 1):** **ONS Postcode Directory (ONSPD)** + **NSUL (UPRN→LAD)** + **NSPL** — the
  district roll-up join tables (postcode/UPRN → LAD, the exact "by district" axis).
- **Tier 2:** **BDUK Project Gigabit premises contracted/built** (adds the **operator WHO** + subsidised
  vs commercial build); NSPL alt.
- **Tier 3:** Open Postcode Geo / Doogal (no-key postcode mirrors); **PlainBroadband** (clean Tier-A
  LA-level Ofcom gigabit figures — the way around Ofcom's bot block).
- **Best joins:** postcode, UPRN, LAD code, easting/northing, operator.
- **New capability:** robust district aggregation; explain gaps by operator / subsidy status.
- **Excluded (honest):** Ofcom Connected Nations postcode files — OGL but the whole ofcom.org.uk domain is
  Cloudflare bot-blocked (manual download only, so non-qualifying for automation); EPC bulk needs GOV.UK
  One Login; ThinkBroadband bulk is gated.
- **Gap:** no open automatable postcode/UPRN-level gigabit file; no open new-build-completion or full-fibre
  (vs gigabit-capable) feed.
- **Priority: MEDIUM** (join tables are quick wins; coverage source stays BDUK).

### 10. Bulwark (flood-defence assets + overdue inspections, WHERE/WHO)
- **THE unlock (Tier 1):** **AIMS Asset Bundle** — the full asset register **with EPSG:27700 geometry**
  (GeoJSON/Shapefile/GeoPackage ZIP, OGL, no login) → assets placed by **coordinate, not authority name**;
  **AIMS Spatial Flood Defences (standardised attributes)** WFS/GeoJSON, daily; **5-year FCRM Asset
  Maintenance Programme** (real maintenance/overdue dimension).
- **Tier 2:** Decommissioned assets (distinguish removed vs overdue); RoFRS (risk factoring defence
  condition); **IDB boundaries** (non-EA maintainer WHO).
- **Best joins:** asset id, easting/northing/geometry → LAD (point-in-polygon), authority name, UPRN.
- **New capability:** replace the name-only district join with **coordinate placement**; overdue-inspection
  from the maintenance programme + condition attributes.
- **Gap:** non-EA (LLFA) assets fragmented across ~150 councils under INSPIRE (not OGL); no single open
  per-asset "last-inspected date".
- **Priority: HIGH** (fixes a known accuracy limitation directly).

### 11. Watchman (company distress vs public roles, WHO)
- **Have:** CH PSC + index, Contracts Finder + FTS, CQC, Gazette.
- **Top new (Tier 1):** **CH Free Company Data snapshot** — status + **overdue accounts/confirmation-statement**
  dates = distress signals keyed by company number (the biggest fix for "zero exposures"); **Gazette
  strike-off/dissolution notice types** (keyless date-ranged feed); **360Giving grants**, **GIAS academy
  trusts** (trust→CH number), **Charity Commission bulk extract** — public-role feeds keyed by company number.
- **Tier 2:** **OpenSanctions disqualified-directors** mirror (⚠ CC-BY-NC — non-commercial only);
  DataLedger dissolved-company deltas; NHS spend ≥£25k.
- **Tier 3:** LA spend >£500 / contract registers.
- **Best joins:** company number (strong); supplier/recipient **name** (weak — the missing matcher).
- **New capability:** actual live-exposure detection (distress ∩ active public duty) — the system finally fires.
- **Excluded:** CH REST/streaming API (key); disqualified-officers bulk (request-only); CCJ register (fee);
  Individual Insolvency Register (search-only).
- **Gap:** every non-CH public-role feed joins on **name, not number** — a robust name→CH-number matcher is
  the real unlock and the reason exposures currently read zero.
- **Priority: HIGH** (makes a currently-empty system productive).

### 12. Compass (SEN/EHC demand by authority, WHERE)
- **Have:** DfE SEN provision, ONS births, GIAS.
- **Top new (Tier 1):** **EHCP (SEN2) survey** — plans, new plans, 20-week timeliness, tribunals,
  placements, need type, 2019–2025 by LA; **SEN in England** (need-type + SEN-support tier); **EES
  keyless API**; **ONS 2022 subnational population projections** (future 0–19 denominator); **DSG high-needs
  allocations** (money vs demand).
- **Tier 2:** School Capacity special-provision demand; Suspensions/exclusions by SEN; MoJ SEND tribunal volumes.
- **Tier 3:** IMD 2019 (deprivation covariate — note LAD vs education-LA geography mismatch).
- **Best joins:** `new_la_code` (GSS), `old_la_code`, region_code, URN. (Build one LA-code crosswalk.)
- **New capability:** funding-gap (EHCP growth vs DSG); **forward** demand vs projected child population;
  timeliness/tribunal stress signals.
- **Gap:** EHCP waiting lists, independent-placement cost, Ofsted SEND-area outcomes not open/LA-keyed.
- **Priority: HIGH** (adds money + forward-looking axes to a strong system).

### 13. Baseline (sewage spills, WHERE/WHO)
- **Have:** EDM single-year, EA rainfall.
- **Top new (Tier 1):** **EDM annual returns 2020–2024** (five years, identical schema — drops straight in
  for the trend); **National Storm Overflow Hub** near-real-time feed (event-level status/timestamps — a new
  dimension); **Water Company Boundaries** (Ofwat/Stream — the **WHO-as-polygon** layer); **Catchment Data
  Explorer** WFD status (`water_body_id`).
- **Tier 2:** Water Quality Archive (measured downstream impact); Bathing Water Quality; NRFA river flow +
  catchment rainfall (sharper weather-normalisation).
- **Tier 3:** Designated Shellfish Waters.
- **Best joins:** permit/outlet id, company, easting/northing → LAD, `water_body_id`, receiving water.
- **New capability:** **multi-year trend**; near-real-time spills; company-area choropleths; spills correlated
  with actual receiving-water status.
- **Gap:** spill **volume** (m³) never open (duration/count only); per-company real-time URLs must be pulled
  live per water body.
- **Priority: HIGH** (multi-year is a straight drop-in; big storytelling gain).

---

## Recommended implementation order

1. **DfE School Capacity + EES API** → Catchment time-series & Compass EHCP/DSG (one loader, two systems).
2. **AIMS Asset Bundle (geometry)** → Bulwark coordinate placement (fixes a known limitation).
3. **EDM 2020–2024 back-years** → Baseline trend (identical schema, trivial).
4. **PlanIt + planning.data.gov.uk** → the planning four (Highwater outcomes, Plumbline statutory clock,
   Ledger mapping, Sightline corpus) — one integration, four systems.
5. **CH Free Company Data snapshot** → Watchman distress + Sentinel/Bellwether status/SIC.
6. **CQC care-directory-with-beds + Market Oversight** → Bellwether real concentration.
7. **OpenOwnership BODS + GLEIF** → deeper WHO across the org graph.
8. **NGED + SSEN ECRs** → Junction full-GB coverage.
9. **ONS Geography (ONSPD/NSUL/LAD)** → tighten the WHERE spine everywhere.
10. **WFD catchments + Nutrient Neutrality** → Sightline as a real water-quality system.

## Global honesty notes (access rule held)
Excluded as **non-qualifying** wherever found: Ofcom Connected Nations (domain bot-blocked, manual only),
EPC bulk (GOV.UK One Login), CQC syndication API (subscription key), Companies House REST/streaming +
officers/appointments/charges bulk (key or request-only), Register of Judgments/CCJ (fee), Individual
Insolvency Register (search-only), ThinkBroadband bulk (gated), OS AddressBase (paid), various Apify
scrapers (paid). These are named in each system's section so the boundary stays auditable.

---

## Implementation progress (verified during build)

- **Catchment — DONE.** `dfe_school_capacity` source wired; `gold.catchment_trend` +
  `catchment_district_trend` built (282,131 school-year rows, 2009/10–2023/24). Payload
  `catchment.trend`; UI shows the primary-vs-secondary line. National utilisation 90.8%→88.8%;
  SCAP latest (88.8%) cross-checks the GIAS snapshot (89.6%).
- **Sightline — DONE.** `planit_planning_wq` source + polite paged backfill
  (`gt backfill --only planit`) + loader (`silver.planning_water_quality`) + gold
  (`sightline_wq_theme/authority/district`) + publish + sysview all wired. Now a mapped
  national corpus of **285 water-quality planning applications across 79 authorities**
  (phosphate 188 + nutrient-neutrality 97), 216 decided, placed into 56 districts via
  `spatial.point`. Map concentrates correctly on Somerset / Herefordshire nutrient
  catchments. UI: district-map primary, objection-reason bars secondary, computed insights.
  NOTE: the literal "water quality" term (~1,136 apps) was throttled out on this run; a later
  calm `gt backfill --only planit` tops it up (dedup by uid, so it only adds).
- **Ledger mapping — BLOCKED on PlanIt, verified.** The `developer-agreement` bulk carries a
  planning-application ref on 12,696 of 12,775 rows, but **no coordinates**. Tested resolving
  those refs against planning.data.gov.uk's own `planning-application` bulk (100,627 rows, 98%
  with a point): only **40 of 12,775** match — that dataset covers ~6 pilot LPAs, so its refs
  barely overlap. **Conclusion: Ledger mapping requires a bounded PlanIt ref→coordinate lookup
  (~12.7k uids), which must wait until PlanIt is not otherwise in use** (the API throttles hard).
  The promised→secured→spent pipeline and by-purpose breakdown already run on the full bulk
  (39,325 contributions / 49,891 transactions) — mapping is the only missing piece.
- **Plumbline — DONE (no fetch needed).** PS2 already carries 47 years of quarterly data
  (1979 Q2–2026 Q1); the statutory-vs-headline series was computed in `gold.plumbline_quarter`
  but never surfaced. Added `plumbline.trend` (annualised 2008–2025) to the payload and an
  "Over time" line to the UI. Shows the divergence opening with the extension-of-time regime:
  the gap grew from 3.8 pts (2008) to 69.7 pts (2025) as the headline climbed to 86% and the
  real statutory rate collapsed to ~16%. The MHCLG Live Tables in the roadmap would only
  duplicate what PS2 already provides — not needed.
- **Ledger mapping — NOT FEASIBLE from free sources (tested, closed).** Beyond the
  planning.data.gov.uk 0.3% result, PlanIt was tested for exact-ref resolution: its `search`
  is fuzzy word-matching, returns the wrong applications, and the developer-agreement bulk
  nulls the LPA so refs cannot be scoped. There is no reliable free path from a S106 record to
  a coordinate. The "0 mappable" finding stands and is now evidence-backed — it is the honest
  result, not a gap to paper over.
- **Highwater — DONE (no PlanIt needed).** The EA objections already carry an LPA name (426
  distinct) + residential units + outcome. Added `gold.highwater_authority` (per-authority
  override rate) and `gold.highwater_district` (placed by name->code via `spatial.code_for_name`,
  which was upgraded to strip "London Borough of" / "Metropolitan Borough Council" / "Councils"
  etc. — match rose from 1 to 221 of 282 authorities). UI: override map (secondary), authority
  explorer, and a top-overrider insight (Hammersmith & Fulham, 49 approvals against advice,
  44.1%). The PlanIt unknown-resolution unlock stays blocked by the same fuzzy-ref problem as Ledger.
- **Baseline — DONE (multi-year, no new fetch).** All EDM annual returns (2020-2025) were
  already in bronze; only 2025 was loaded. Wrote a header-text-driven loader (`load_multi`) that
  handles the layout drift across years (combined vs per-company sheets, shifted columns, missing
  LTA column). Loads 2021-2025 (2020's single-sheet-per-company format is incompatible, skipped).
  Year-guarded the national/company/weather aggregations, added `gold.baseline_trend`, payload
  `baseline.trend`, and an "Over time" reported-vs-adjusted line. Finding: spills swing with
  weather (2023 wettest at 464k reported, 2022 driest), and the reported-vs-adjusted gap has
  closed from ~172k hidden by monitor downtime in 2021 to <10k in 2025 as uptime rose 94.9%->97.3%.
  Also upgraded `GT.line` with a fitted-axis option and compact k/m tick labels.
- **Compass — DONE (no fetch needed).** The 11-year national series (2015-2025) was already in
  `gold.compass_series` but only surfaced as an earliest/latest pair. Added `compass.trend` to the
  payload and an indexed "Over time" line (2015=100, so EHC plans / SEN support / all pupils share
  one axis). Finding: EHC plans ×2.27 (index 227) while the pupil population is ×1.04 and has
  actually fallen since 2023 — demand is detaching from the size of the child population. The DSG
  high-needs funding + EHCP SEN2 timeliness in the roadmap remain as a further (fetch-based) add.
- **Watchman — DONE (no new fetch; the empty system now fires).** The CH bulk snapshot was
  already loaded as `silver.company` (5.7m rows, carries `status`). Added `check_distress`: joins
  public-role holders (CQC care providers + public-contract suppliers) to CH status and flags those
  in liquidation/administration/voluntary-arrangement/receivership. New `gold.watchman_distress`,
  payload `distress`/`by_status`/`by_role`/`distress_list`, and a full sysview (was an honest empty
  state). Result: **287 exposures — 284 care providers + 3 contract suppliers in financial distress
  while holding a live public duty** (209 in outright liquidation). Example: LaserCare Clinics
  (Harrogate) in liquidation while registered for 48 CQC care locations. The overdue-accounts/CS
  distress signals (roadmap) would need the CH due-date columns, not in the current silver.company.
- **PlanIt rate-limit reality.** The API throttles aggressively on rapid/large queries; the
  backfill handler backs off (10–70s) and caps to on-topic slices. Broad terms ("foul drainage"
  ~21k, "sewage" ~17k) are deliberately excluded — too broad and too heavy for a donation-funded API.
