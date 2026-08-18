# Groundtruth — deep research

Verification date: **17 August 2026**. Every access claim below was tested from a clean
client: no account, no API key, no subscription, no cookie, no referrer.

Raw evidence: [`research/probe-results.tsv`](research/probe-results.tsv),
[`research/probe2.tsv`](research/probe2.tsv), harness in [`research/run-probe.sh`](research/run-probe.sh).

---

## 1. Method

The binding constraint on this platform is not modelling skill or compute. It is **access**.
A source that needs an account cannot be part of Groundtruth, because the whole proposition is
that a government body can reproduce every number without asking anyone's permission.

So the research began by testing access rather than by reading documentation. 101 endpoints
were probed; **69 returned HTTP 200 to an unauthenticated request**. Everything downstream —
architecture, system design, what each system can honestly claim — follows from that result.

Three things this method caught that documentation review would not have:

1. **The Ordnance Survey Downloads API serves the entire free portfolio with no key.**
   Documentation steers you to the OS Data Hub, which wants an account. The `api.os.uk/downloads/v1`
   path does not. A range request returned `HTTP 206` and real ZIP bytes. This is the single most
   important finding in the whole study — see §2.1.
2. **Four of the six DNO open-data portals expose a full Opendatasoft API anonymously**, with
   filtering, aggregation and geospatial querying. The industry position is that grid connection
   data is hard to obtain; for four networks it is a query string.
3. **Several "open" sources are not.** The EPC register serves a sign-in page to an anonymous
   client despite being described as open. Two DfT services return 401. These were removed from
   the platform rather than assumed to work.

### Reading the status codes

| Code | Meaning here | Consequence |
|---|---|---|
| 200 | Data returned to an anonymous client | Usable |
| 401 | Credentials required | Excluded under the no-registration rule |
| 403 | Automated retrieval blocked | Excluded, or needs a manual step |
| 200 + HTML sign-in | Advertised as open, is not | Excluded — the trap case |

---

## 2. The data foundation

### 2.1 The place spine — Ordnance Survey, no key required

Confirmed downloadable anonymously from `https://api.os.uk/downloads/v1/products/{id}/downloads`:

| Product | Format | Size | Role in Groundtruth |
|---|---|---|---|
| OS Open UPRN | CSV | 618.5 MB | Every property reference in GB, with coordinates |
| OS Open Linked Identifiers | CSV | 672.0 MB | **The crosswalk**: property ↔ street ↔ topographic ID |
| OS Open USRN | GeoPackage | 296.9 MB | Street references |
| OS Open TOID | CSV | 1.4 MB | Topographic identifiers |
| Code-Point Open | CSV | 14.5 MB | Postcode centroids |
| OS Open Names | CSV | 103.3 MB | Place and street name gazetteer |
| Boundary-Line | Shapefile | 736.9 MB | Administrative boundaries |
| OS Open Roads | Shapefile | 606.1 MB | Road network |

**Why this matters.** Groundtruth's place spine needs to turn a messy reference into a stable
identifier. Linked Identifiers is precisely that crosswalk, and it is free and unregistered.
The earlier assumption — that the place spine required a licensed addressing product — was wrong
for the identifier layer.

**The licensing line still holds.** These products are open, but the surrounding OS licences
(notably PSGA clause 2.5.3) permit publishing *identifiers* appended to your own data while
prohibiting republishing address strings or coordinates derived from licensed address products.
Groundtruth therefore **emits identifiers, never addresses**. That is an architectural rule, not
a preference — see §5.3.

### 2.2 The entity spine

| Source | Access | What it carries |
|---|---|---|
| Companies House bulk product | 200, daily | 5.4m companies, officers, status |
| Companies House PSC snapshot | 200, daily | Beneficial ownership |
| The Gazette notices (JSON) | 200, realtime | 3m+ notices, each carrying a **structured company number** |
| Find a Tender (OCDS) | 200, realtime | Above-threshold notices |
| Contracts Finder (OCDS) | 200, realtime | Award notices including below-threshold |

The Gazette result is the important one. Insolvency notices carry the company number as a field,
so Watchman never has to match on company *name* — the hardest and least reliable join in UK data.

### 2.3 Verified sources by domain

69 endpoints returned 200. Grouped:

- **Place / geography** — OS portfolio (8 products), ONS Open Geography (3,905 services), Code-Point Open
- **Entity** — Companies House bulk + PSC, The Gazette, both OCDS procurement APIs
- **Planning** — MHCLG Planning Data Platform (entities, datasets, title boundaries, developer contributions)
- **Education** — GIAS full establishment CSV (52,486 rows), Explore Education Statistics API
- **Environment** — EA flood monitoring, rainfall (1,044 stations), hydrology, **asset management**, ecology
- **Energy** — NESO CKAN, UKPN (137 datasets), SPEN, Northern Powergrid, ENWL
- **Property** — HMLR Price Paid, UK House Price Index, Land Registry linked-data endpoints
- **Statistics** — ONS API, NOMIS
- **Other** — NHS ODS, UKHSA, FSA ratings, data.police.uk, DfT casualties, NaPTAN, legislation.gov.uk, Parliament APIs

### 2.4 What failed, and why it stays visible

| Source | Code | Position |
|---|---|---|
| CQC syndication API | 401 | Needs a key. The published location file is still free — use that. |
| Charity Commission API | 401 | Needs a key. Bulk extracts remain downloadable. |
| Bus Open Data Service | 401 | Needs a free account — still excluded by the rule. |
| EPC register | 200 + sign-in HTML | **Advertised as open, is not.** Lastmile uses Price Paid Data instead. |
| Ofcom Connected Nations | 403 | Blocks automation; needs a manual download. |
| GIAS download page | 403 | Page blocks bots — but the underlying CSV is directly reachable. |
| Stat-Xplore (DWP) | 503 | Account required. |
| Local Land Charges | 403 | Search service blocks automation. |

These are published in the platform's own admin console rather than hidden. A system that quietly
drops a source it cannot reach is a system whose coverage figures cannot be trusted.

---

## 3. Measured baseline

Computed from the GIAS full extract, 17 August 2026 (52,486 establishments; 27,167 open):

| Measure | Value | Meaning |
|---|---|---|
| Open schools | 27,167 | Denominator |
| Carrying a property reference (UPRN) | **96.5%** | The place link is nearly solved *in this dataset* |
| Carrying coordinates | 97.7% | |
| Carrying a trust/company identifier | **45.4%** | The entity link is barely half-solved |
| Total capacity | 9,928,858 places | |
| Total pupils | 8,857,132 | |
| National utilisation | 89.2% | |
| Distinct academy trusts | 2,185 | |
| Largest group | United Learning Trust, 96 schools | Concentration is real and measurable |

**This is the thesis, measured.** In the single dataset with the best identifier hygiene in UK
government, *where* is 96.5% solved and *who* is 45.4% solved. Most datasets are far worse on both.

### A finding worth stating plainly

Joining these authorities to ONS boundaries by name matched **152 of 316** districts. The 30
unmatched education authorities are two-tier counties — Kent, Lancashire, Hampshire, Essex,
Surrey, Norfolk, Staffordshire and others — whose schools span several districts.

That is not a data-cleaning nuisance. It is exactly the defect Catchment exists to fix: school
planning happens on a geography that is published nowhere and does not align with the
administrative geography everything else uses. The prototype surfaces this rather than papering
over it.

---

## 4. The thirteen systems

Each entry covers what the user asked: sources, function, logic, problem, data in and out,
and how it connects to the rest.

### 4.1 Catchment — school place planning
- **In**: GIAS (daily CSV, 200), School Capacity, ONS births and migration, ONS boundaries
- **Logic**: rebuild the 3,651 pupil planning areas from the school-membership table DfE already
  publishes; apportion births and migration to those areas; project forward by year group
- **Out**: planning-area boundaries (openly licensed), surplus/shortage by area and year group
- **Problem**: £1.096bn of Basic Need capital is allocated on a geography published nowhere
- **Depends on**: place spine. **Feeds**: Compass, Plumbline
- **Free-data verdict**: fully buildable today

### 4.2 Sentinel — procurement integrity
- **In**: Find a Tender + Contracts Finder OCDS APIs (both 200), Companies House bulk + PSC
- **Logic**: resolve every bidder and buyer to a company number; build the directorship and
  ownership graph; aggregate call-offs to parent frameworks; flag shared control between bidders
- **Out**: connected-bidder flags, framework concentration measures, supplier-to-buyer graph
- **Problem**: contract records carry names, not identifiers, so shared control is invisible
- **Constraint (verified earlier)**: **bid prices are not published in UK data**, which kills the
  statistical price-screen family of collusion tests. Sentinel therefore relies on structural
  signals — shared directors, shared PSCs, framework concentration — not price patterns
- **Depends on**: entity spine. **Feeds**: Watchman, Bellwether

### 4.3 Highwater — flood risk vs what got built
- **In**: EA planning objections (23,336 records, 426 authorities), Flood Map for Planning,
  NaFRA2, planning.data.gov.uk
- **Logic**: resolve each objection to a site, join to flood zone, recover the decision from the
  authority's own published register where the EA's record says "outcome unknown" (~30%)
- **Out**: national compliance figure, objection-to-outcome record
- **Problem**: the objections file has no address, postcode or coordinate
- **Depends on**: place spine. **Feeds**: Sightline, Bulwark

### 4.4 Plumbline — housing delivery honestly measured
- **In**: PS1/PS2 statistics, net additional dwellings, indicators of new supply, PINS statistics
- **Logic**: report performance against the statutory deadline *and* the extended deadline, always
  side by side; track extension usage as a first-class metric; maintain a running delivery estimate
  between official measurements
- **Out**: dual compliance figures, extension-usage rate, interim delivery estimate
- **Problem**: 91% "on time" becomes 19% measured against the actual statutory deadline
- **Note**: the EPC-based completion proxy was **removed** — EPC is not anonymously accessible

### 4.5 Junction — grid connection capacity
- **In**: NESO CKAN (200), UKPN/SPEN/NPg/ENWL Opendatasoft APIs (200), TEC register, GSP boundaries
- **Logic**: normalise each operator's capacity figure to one stated definition, publish each
  operator's own method alongside it, match projects across transmission and distribution
  registers with a published confidence score
- **Out**: comparable capacity by node, cross-register project matches
- **Problem** (corrected during research): the gap is **not** access — 5 of 6 DNOs publish. The
  real gap is that each computes "available capacity" on its own basis, so the numbers cannot be compared
- **Depends on**: both spines

### 4.6 Ledger — developer contributions
- **In**: developer agreement contributions (39,325 records, £1.49bn), transactions (49,891 records
  carrying received/spent status), planning applications, title boundaries
- **Logic**: attach each contribution to a site; read the received/spent status the schema already
  carries but nothing currently reads spatially
- **Out**: contributions mapped by council, ward, site and purpose; promised-vs-delivered
- **Problem**: address text is 98.1% populated, property reference **0.0%** — so £1.49bn cannot be mapped
- **Depends on**: place spine (heaviest user)

### 4.7 Bellwether — provider concentration
- **In**: CQC active locations file (free download; the *API* needs a key), Ofsted providers,
  GIAS + academy trust membership, Companies House
- **Logic**: resolve owner-name variants to one company; compute concentration by council and sector
- **Out**: concentration measures, corrected group sizes
- **Measured**: CQC carries a company number on 93.9% of beds; academy trusts 100%; GIAS overall 45.4%
- **Depends on**: entity spine. **Feeds**: Watchman

### 4.8 Sightline — is expert advice followed
- **In**: EA flood objections, EA water-quality objections (a second, largely untouched sheet),
  planning decisions
- **Logic**: link advice to decision to outcome; publish override rates with context
- **Out**: override rate by authority, advice-to-outcome record
- **Finding**: the override *rate* has been flat for nine years even as raw counts rose — context
  that changes the interpretation entirely
- **Note**: Active Travel England casework is held in a structured system but published nowhere;
  Sightline cannot use it until it is released

### 4.9 Lastmile — gigabit compliance for new homes
- **In**: BDUK open market review premises data, **HMLR Price Paid** (old/new flag identifies
  new-builds at address level), OS Open UPRN + Linked Identifiers
- **Logic**: match new homes to premises-level connectivity status; compare subsidy targets against
  the development pipeline
- **Out**: compliance picture for the 2022 building-regulation duty; subsidy overlap analysis
- **Change from earlier design**: EPC replaced by Price Paid Data after EPC failed the access test

### 4.10 Bulwark — who owns flood defences
- **In**: **AIMS spatial flood defences via WFS (200)** — 141,468 assets with owner,
  operator, maintainer, condition, inspection dates and geometry. *Correction: the
  asset-management API registered earlier carries condition but **no owner and no
  geometry**, so it cannot answer this system's question. Same publisher, different endpoint.*
- **Logic**: resolve each asset to the land parcel beneath it, the parcel to a registered owner;
  separate genuinely unowned from merely unrecorded; flag overdue inspections
- **Out**: ownership attribution, inspection-overdue list, coverage-qualified condition statistics
- **Problem**: owner is "Unknown" on **73.7%** of 141,468 assets (measured, matching the
  published figure), and only **24.9%** carry a condition grade at all
- **Measured correction**: the *maintainer* is known for **90.9%**. The operational question
  is largely answered; it is legal ownership that is missing. **7,233 inspections are overdue**
  against the assets' own scheduled dates
- **Research upgrade**: the asset API was newly confirmed accessible — this system is stronger
  than previously assessed

### 4.11 Watchman — insolvency exposure
- **In**: The Gazette JSON (structured company number), Companies House filing history and charges,
  both OCDS procurement feeds
- **Logic**: on a notice, resolve the company number and immediately enumerate every public
  dependency; treat late filings and new charges as **events that have occurred**, not predictions
- **Out**: exposure list within minutes of a notice; watchlist of distress signals
- **Why not a credit model**: standard financial distress models need profit data that small
  companies never file. Watchman reports facts instead of scoring them

### 4.12 Compass — SEND demand forecasting
- **In**: EHCP statistics, ONS population, Catchment's planning-area geography
- **Logic**: forecast at planning-area rather than county level; project specialist place demand
- **Out**: demand projection and specialist place requirement for statutory plans
- **Privacy**: uses published aggregate statistics only. **No individual children's records** are
  touched — this is what makes it lawful and deliverable
- **Depends on**: Catchment

### 4.13 Baseline — sewage spills normalised for rainfall
- **In**: EDM storm overflow data (72,168 records; `old_unique_id_pre_2024` field), **EA rainfall
  (1,044 stations, 15-minute)**, EA hydrology
- **Logic**: normalise spill behaviour against actual local rainfall; report monitor availability
  alongside every spill count; bridge the 2024 reference-number change
- **Out**: weather-adjusted spill measures, monitor-availability-qualified statistics
- **Problem**: a 35% fall in a drier-than-average year tells you nothing about whether £22.1bn of
  investment worked
- **Depends on**: both spines

---

## 5. Architecture

### 5.1 Shape

```
  39 open feeds ──▶ FETCH ──▶ VALIDATE ──▶ RESOLVE ──▶ SCORE ──▶ PUBLISH ──▶ 13 systems
                                            │  │
                                    place ──┘  └── entity
```

Two resolvers, thirteen consumers. The systems are thin; the resolvers are the platform.

### 5.2 Storage and compute

The whole corpus is in the low hundreds of gigabytes — the OS products dominate. This runs on one
well-specified machine with a columnar store (DuckDB or Postgres + PostGIS). It does not need a
cluster, and saying so honestly is a competitive advantage when the buyer has been quoted otherwise.

- **Bronze**: raw fetch, immutable, hash-stamped, with the HTTP status and licence recorded
- **Silver**: validated, schema-conformed, identifiers attached
- **Gold**: per-system published outputs

### 5.3 Rules that are not negotiable

1. **Emit identifiers, never addresses.** Keeps the platform inside the OS licensing line permanently.
2. **Every match carries a confidence score, published.** Nothing merges silently. Low-confidence
   matches go to a human queue.
3. **Every statistic ships with its coverage.** "73.7% unknown" is a finding, not something to hide.
4. **Every source records its access status.** A source that starts returning 403 must show as failing,
   not silently produce a smaller number.
5. **Reproducibility.** Same inputs, same commit, same outputs — because a government buyer will
   eventually be challenged on a number by a named company.

### 5.4 How the systems interoperate

Four demonstrated chains:

- **A company fails** → Watchman (Gazette) → Bellwether (care exposure) → Sentinel (contracts) → Ledger (unpaid obligations)
- **A development is approved** → Plumbline, Ledger, Sightline, Highwater, Catchment, Lastmile — six systems, one reference number
- **A flood defence has no owner** → place link → entity link → Watchman (is the owner solvent?)
- **A regulator reissues its reference numbers** → the same repair serves sewage, electricity and care

**Backwards compounding**: the place resolver was built for Ledger and immediately reused by
Highwater, Sightline, Plumbline and Catchment. The entity resolver was built for Sentinel and
reused by Bellwether and Watchman. The nth system is cheaper than the first — this is the core
economic argument for one platform rather than thirteen procurements.

### 5.5 Automation and intelligence

Ordered by defensibility, most defensible first:

1. **Deterministic joins** on published identifiers — no model, exact, auditable. Most of the value.
2. **Probabilistic matching** for names and addresses, with published confidence and a human queue.
3. **Event detection** — a notice appears, a date passes, a threshold is crossed. Facts, not forecasts.
4. **Normalisation and reconciliation** — one definition across operators; bridging reissued references.
5. **Forecasting** — only where the statistical basis genuinely supports it (Compass, Plumbline).

Deliberately excluded: anything that predicts individual behaviour, scores a person, or presents a
model output as a fact. The buyer is a government body that will be asked to defend the number.

### 5.6 Security, reliability, scale

- **Data classification**: everything ingested is already public. This removes an entire class of
  risk and is the strongest single argument in an assurance conversation.
- **Personal data**: none processed. Compass uses aggregates by design.
- **Supply-chain**: sources are pinned and hashed; a changed schema fails the run rather than
  silently producing wrong numbers.
- **Availability**: publishers change URLs without notice (NESO replaces linked files with no
  changelog; `chargepoints.dft.gov.uk` stopped resolving entirely, with a lookalike non-government
  domain now soliciting registrations). Mitigation: content hashing, retention of prior snapshots,
  and alerting on structural change.
- **Scale**: bounded by the size of UK open data, which is small and grows slowly.
- **Egress**: outputs are identifiers and statistics, so publishing is cheap and licence-safe.

### 5.7 Residency and clearance — the real constraint

Remote access from Nigeria is a restricted international transfer under UK GDPR, and there is no
adequacy decision for Nigeria. BPSS and SC clearance require UK residency history. Since the
platform processes **no personal data**, the GDPR transfer question is largely moot — but
clearance requirements attach to the *contract*, not the data. This shapes the commercial route
more than the technical one.

---

## 6. What free data can and cannot do

**Can**: all thirteen systems, on 69 verified-open sources, with no account anywhere. The place
spine is free and unregistered. The entity spine is free and unregistered. That was not certain
before this study, and it is the finding that makes the platform viable.

**Cannot, today**:
- Bid prices — not published, so price-based collusion screens are impossible
- Active Travel England casework — held structured, published nowhere
- EPC-based completion tracking — not anonymously accessible
- Ofcom Connected Nations automation — blocked, needs a manual step
- Individual-level anything — excluded by design, not by capability

**The honest summary**: the ceiling is set by what government chooses to publish, not by what can
be computed. Groundtruth's proposition is that the published material already supports far more
than is currently extracted from it — because the two joins that would unlock it have never been
built.
