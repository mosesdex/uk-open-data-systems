# Groundtruth platform

The engine behind the thirteen systems. Resolves two missing joins in UK
government data: **place** (where) and **entity** (who).

## Setup

```bash
cd platform
python3 -m venv .venv && ./.venv/bin/pip install -r requirements.txt
```

## Use

```bash
./.venv/bin/python -m groundtruth.cli sources            # the registry
./.venv/bin/python -m groundtruth.cli fetch --role place_spine
./.venv/bin/python -m groundtruth.cli fetch --all --max-bytes 20000000
./.venv/bin/python -m groundtruth.cli status             # last outcome per source
```

`--max-bytes` truncates each download, which is how to smoke-test without
pulling 1.3 GB of Ordnance Survey products.

## M1 — ingest framework

**The no-registration rule is enforced in code, not documented.** `fetch.py`
refuses to send an `Authorization` header, a cookie, an API key or a bearer
token, and ignores netrc and proxy credentials. Attempting to send any of them
raises `CredentialLeak`. This matters because the platform's whole proposition
is that a government body can reproduce every number without asking permission;
that is only true if nothing here can quietly acquire credentials.

### The trap case

A source that answers `HTTP 200` is not necessarily serving data. The energy
certificate register answers 200, redirects to a different host, and serves an
ordinary GOV.UK landing page with a cookie banner.

The first version of the check looked for sign-in wording and **passed it
straight through**. The rule is now simpler and decisive: *a source that
promises JSON and returns HTML is not serving data*, whatever the HTML says.
Admissibility is decided on content type; sign-in wording only sharpens the
error message. `tests/test_fetch.py` locks this in as a regression test.

### Design notes

- **Failures are recorded, not raised.** A source that cannot be reached is a
  fact worth storing, because coverage figures are only trustworthy if you can
  see what was missed. `bronze.fetch_log` is append-only.
- **Blocked sources stay in the registry.** A platform that silently drops
  unreachable sources cannot be audited.
- **Content is hashed while streaming**, so a publisher replacing a file without
  a changelog shows up as changed content. The research found this happens.
- **Versioned filenames are resolved at fetch time.** Ordnance Survey splits
  Linked Identifiers into one file per identifier pair, stamped with the month.
  `resolve.py` looks up the current release rather than hardcoding a name that
  breaks in four weeks.
- **Schema changes migrate.** `CREATE TABLE IF NOT EXISTS` will not add a column
  to an existing database, so `store.migrate()` applies them explicitly.

## Layout

```
groundtruth/
  sources.py   the registry: url, licence, role, cadence, expected content
  fetch.py     anonymous fetching, credential guard, payload check
  resolve.py   late-binding URLs for versioned publisher filenames
  store.py     DuckDB: bronze / silver / gold, fetch log, migrations
  cli.py       gt sources | fetch | status
tests/         24 offline tests, 2 network tests (-m network)
```

`data/` holds the database and downloads. It is not committed.

## Status

| Milestone | State |
|---|---|
| M1 ingest framework | **done** — 12 admissible sources, 2 blocked and visible |
| M2 place spine | **done** — 1,749,109 postcodes, validated at 64 m median |
| M3 entity spine | **done** — identifier-first, ambiguity reported not guessed |
| M4 Catchment end to end | **done** — 26,605 schools resolved, masking exposed |
| M5 Watchman | **done** — cumulative supplier register, exposure checking |
| M6 Bellwether | **done** — care concentration at entity and group level |
| M7 Bulwark | **done** — 141,468 defences, 7,233 inspections overdue |
| M8 Ledger | **done** — £1.49bn traced, 0% of it mappable |
| M9 Baseline | **done** — spills adjusted for monitor availability |
| M10 Sentinel | **done** — concentration, within what the data supports |
| M11 Highwater | **done** — override rate flat for nine years |
| M12 Plumbline | **done** — 82.8% headline against 15.9% statutory |
| M13 Sightline | **done** — one advice stream has no outcome field at all |
| M14 Lastmile | **done** — new-build postcodes 21 points worse connected |
| M15 Junction | **done** — schemas standardised, 5,833 records withheld |
| M16 Compass | **done** — EHC plans up 127.4% against 4.2% pupil growth |
| **All thirteen systems built** | |
| M17 wire the prototype to real outputs | **done** |
| M18 cross-system chains | **done** — executed, not illustrated |
| M19 UI and system visibility | next |
| M10 wire the prototype to real outputs | |

## M2 — place spine

```bash
./.venv/bin/python -m groundtruth.cli load
./.venv/bin/python -m groundtruth.cli place "SW1A 1AA"
./.venv/bin/python -m groundtruth.cli coverage --validate
```

**Resolution is tiered, and the tier is always reported.** A postcode centroid
is a useful answer but it is not an exact property, and returning both as "a
location" would be lying by omission. Confidence comes from Ordnance Survey's
own positional quality flag, never from an invented number — and only an exact
property reference is allowed to score 1.0.

| Tier | Source | State |
|---|---|---|
| `uprn` | OS Open UPRN | loads when the product is fetched |
| `postcode` | Code-Point Open | **1,749,109 rows, loaded** |
| `lad` | ONS boundaries | 318 districts |

### Measured, not asserted

GIAS publishes a postcode *and* a coordinate for every school, so the spine can
be checked against the publisher's own answer:

| | |
|---|---|
| Establishments | 27,167 |
| Resolved from postcode alone | 26,605 — **97.9%** |
| Median error | **64 m** |
| 90th percentile | 183 m |
| Within 500 m | 98.5% |

That is the number to quote when someone asks how good "resolved" really is.

### Two limits worth stating

- **Code-Point Open is Great Britain, not the UK.** There are zero Northern
  Ireland postcodes in it — confirmed, and covered by a test. Any coverage
  figure must say GB.
- **Coordinate conversion is a datum shift, not a reprojection.** Skipping the
  Helmert transform puts a point roughly 100 m out, enough to place a property
  on the wrong side of a street. `geo.py` is verified against the Ordnance
  Survey worked example to seven decimal places.

## M3 — entity spine

The harder join. Place has a free national identifier; entity does not, so most
records carry a *name*, written differently every time.

Three rules, each enforced by a test:

1. **An identifier beats a name.** A record carrying a company number resolves
   at confidence 1.0 with no matching at all.
2. **A name match is scored, never silent.** Nothing reaches the auto-accept
   threshold on a name alone; below it, the match goes to a review queue.
3. **Ambiguity is an answer.** Two companies matching equally well is reported
   as ambiguous, not resolved to whichever sorted first.

### Measured on live insolvency notices

The claim being tested was that a Gazette notice always carries a structured
company number. It does not — it carries one **70%** of the time:

| Notice type | Carries a number |
|---|---|
| Appointment of liquidators | 38/38 |
| Meetings of creditors | 5/5 |
| Resolutions for winding up | 17/30 |
| Notices to creditors | 0/6 |
| Notices of intended dividends | 1/7 |

The notice types that mark an actual insolvency event are the reliable ones, so
Watchman still works — but the blanket claim was wrong, and the site has been
corrected.

### The spines cover each other

Notices without a number still print a registered address. Feeding that postcode
to the place spine lifts coverage from 70% to **93%**. That is the compounding
argument made concrete: the second spine rescues what the first cannot identify.

### One correctness fix worth noting

An early version stripped "group", "holdings" and "UK" as noise. It is not
noise: "Northern Care Group Ltd" and "Northern Care Holdings Ltd" are routinely
separate companies with separate numbers, and collapsing them is a false merge.
Only unambiguous legal forms are stripped now.

## M4 — Catchment, end to end

```bash
./.venv/bin/python -m groundtruth.cli catchment
```

The first system on the spines. 27,167 open schools, 26,605 resolved to a
district (97.9%), 317 mainstream district pictures built.

### What it exposes

| | Districts | Pupils | Places | Utilisation |
|---|---|---|---|---|
| Mainstream | 317 | 8,543,252 | 9,539,518 | 89.6% |
| Specialist | 271 | 203,373 | 216,062 | **94.1%** |

629 specialist settings hold more pupils than places.

The masking table is the point of the system. Waverley averages 91.1% — a
district that looks comfortable — while containing a school at 48% and another
at 228%. Aggregation cancels the surplus against the shortage and neither
appears in published figures.

### A correction the data forced

The first build blended specialist provision into the district average and
produced schools at 330% of capacity. That is not a data error: 12.5% of pupil
referral units and 5.1% of special academies hold more pupils than places,
against 0.1–0.4% of mainstream schools. "Capacity" simply means something
different for alternative provision.

Blending the two produces a utilisation figure that means nothing, so mainstream
and specialist are now counted separately everywhere, and the split is covered
by tests. The specialist figure is worth having in its own right — it is the
SEND pressure in the research, measured.

## M5 — Watchman

```bash
./.venv/bin/python -m groundtruth.cli watchman
```

Reuses the entity spine and the Gazette parser built in M3, which is the
compounding argument in practice: the system itself is a few hundred lines.

### The finding that changed the design

Run against three weeks of live data, Watchman found **zero** exposures — and
that is the correct answer, not a bug:

| | |
|---|---|
| Companies entering insolvency | 609 |
| Distinct companies appearing as public suppliers | 448 |
| Overlap | **0** |

With roughly 5.4 million UK companies, 609 insolvencies against a 448-company
register gives an expected overlap of about 0.05. Zero is what chance predicts.

| Register size | Expected hits per three weeks |
|---|---|
| 1,264 (three weeks of notices) | 0.2 |
| 10,000 | 1.6 |
| 100,000 | 16.2 |
| 250,000 | 40.5 |

So **the register is the asset, not the fetch**. `register_suppliers` accumulates
and deduplicates into a persistent table across runs rather than rebuilding from
the latest download, and backfilling historic award notices is the operational
requirement before the system produces signal.

### Measured on the way

- Supplier records carry a Companies House identifier **30.9%** of the time
  across both feeds — 33.9% on Contracts Finder, 55% on Find a Tender. Identifier
  matching alone cannot close the loop, which is why the name route exists and
  why every link is scored.
- Contracts Finder pages by **date cursor** (`publishedTo`), not page number. A
  `&page=` parameter is silently ignored and returns the same 100 releases: an
  early collection produced 1,500 rows containing 93 distinct notices.

## M6 — Bellwether

```bash
./.venv/bin/python -m groundtruth.cli fetch cqc_hsca_locations
./.venv/bin/python -m groundtruth.cli bellwether
```

### The blocked source was the wrong source

The CQC syndication API returns 401 and was recorded as blocked in M1. The
regulator also publishes a fuller extract as a plain file, reachable with no
key at all — 57,867 locations, 122 columns, carrying **bed counts, a brand
field, and a provider Companies House number on 92.4% of care-home beds**.
That is more than the API would have given. Worth remembering: a blocked
endpoint is not the same as a blocked dataset.

### Concentration is reported at two levels

Neither alone is honest.

**Legal entity** is exact but understates a group trading through several
companies. Care UK runs Islington homes through two numbered entities — each
looks like 26.8% of the borough; the group is 53.6%.

**Group** catches that, using the regulator's brand field, but the field is
imperfect and the imperfections are published alongside it:

- **49% of care-home beds are unbranded.** The group view cannot see them, and
  the figure travels with every group statistic.
- **The field mixes operator with owner.** "Care UK Community Partnerships Ltd"
  is branded *Welltower* — the investment trust that owns the property, not the
  company running the home. Islington therefore shows Care UK and Welltower each
  at 26.8%, which is two true statements about the same 203 beds.

Unbranded providers are treated as their own group, never pooled: the
placeholder means "no group", not "the same group".

### What it finds

| Group | Authorities | Companies | Locations | Beds |
|---|---|---|---|---|
| Welltower | **124** | 72 | 562 | 37,404 |
| Care UK | 80 | 1 | 241 | 16,368 |
| Barchester Healthcare | 81 | 1 | 237 | 14,944 |

One owner group across 124 authorities is exactly the exposure no single council
can see from its own contracts — and it is computable today from a free file.

## M7 — Bulwark

```bash
./.venv/bin/python -m groundtruth.cli bulwark
```

### The registered source was the wrong endpoint

M1 registered the Environment Agency asset-management API for this system. It
carries condition and inspection dates but **no owner field and no geometry**,
so it cannot answer "who owns this defence" at all. The spatial dataset
published through the WFS service carries owner, operator, maintainer, condition
and geometry for all 141,468 assets. Same publisher, different endpoint,
entirely different capability. `RESEARCH.md` has been corrected.

The WFS also supports `resultType=hits`, so exact national counts can be taken
without transferring the data — the coverage figures below cost a few kilobytes.

### The headline number is not the useful number

| | | |
|---|---|---|
| Maintainer known | 128,573 | **90.9%** |
| Owner known | 37,225 | 26.3% |
| Condition graded | 35,191 | 24.9% |

"73.7% of flood defences have no known owner" is true and confirms the research
figure exactly. But when a defence fails, the operational question is who
maintains it — and that is answered for **nine assets in ten**. Bulwark reports
both and does not let the more alarming number stand in for the more useful one.

Condition coverage of 24.9% also confirms the research: any national condition
statistic describes a quarter of the estate, so that denominator travels with
every figure the system publishes.

### 7,233 inspections are overdue

Against the assets' own scheduled next-inspection dates, oldest from 2024.
The Environment Agency's own assets have the highest overdue rate of any named
maintainer — 8.5%, against 4.0% for private owners.

### A silent failure worth recording

The first build reported **zero** overdue inspections. Not a data finding: AIMS
publishes `DD/MM/YYYY` and `date.fromisoformat` returned `None` for all 103,667
values, so "none are overdue" was computed over nothing. The parser now handles
the real format, was checked empirically rather than assumed — across all values
the first component reaches 31 and the second never exceeds 12 — and **raises**
if more than 2% of dates fail, rather than quietly reporting a statistic over
the rows that happened to work.

## M8 — Ledger

```bash
./.venv/bin/python -m groundtruth.cli ledger
```

Confirms the research exactly: **39,325 contributions, £1,491,818,575**, and
**not one record carries a location**. Both `geometry` and `point` are present
on every record and empty on every record, so £1.49bn of obligations cannot be
put on a map.

### The total covers 70.4% of records

Only 27,699 of 39,325 contributions state an amount. The headline is published
with that denominator attached, because a figure that implies the other 29.6%
are worth nothing is wrong.

### Promised is not delivered

The transaction table carries a funding status on 99.2% of 49,891 records, which
separates what was agreed from what actually moved:

| Status | Transactions | Amount |
|---|---|---|
| received | 13,017 | £517,329,167 |
| secured | 19,526 | £387,104,279 |
| allocated | 8,203 | £257,460,646 |
| **spent** | 7,379 | **£154,801,702** |

That last row is the system's reason for existing.

### A robustness bug the tests caught

DuckDB's `executemany` raises on an empty list, so a publisher legitimately
returning zero rows for one dataset would have crashed the loader mid-run. Every
loader now goes through `store.insert_many`, which treats an empty result as a
fact to record rather than an error.

## M9 — Baseline

```bash
./.venv/bin/python -m groundtruth.cli baseline
```

14,302 storm overflows. Every spill count is published with the share of the
year its monitor was actually recording, and a full-year-equivalent alongside
the raw number.

| | |
|---|---|
| Reported spills | 291,412 |
| Availability-adjusted | **300,326** (+3.1%) |
| Mean monitor uptime | 97.3% |
| Watched 90%+ of the year | 13,228 of 14,302 (92.5%) |
| Located from grid reference | 14,245 (99.6%) |

The adjustment is smaller than the concern implies — uptime in 2025 is genuinely
high — and saying so is the point. The number matters where it is small: **72
outlets were watched for under half the year**, and their counts cannot be
compared with anything until adjusted.

Outlet locations are published as National Grid References, not coordinates, so
`geo.ngr_to_bng` converts them. A malformed reference returns `None` rather than
a guess: an outlet placed in the wrong 100 km square is worse than an outlet
with no location at all.

## M10 — Sentinel

```bash
./.venv/bin/python -m groundtruth.cli sentinel
```

### Two standard screens are impossible, and the system says so

- **Price screens.** Bid prices are not published in UK procurement data, so the
  statistical price-pattern family cannot be run. Known from the research.
- **Single-bidder rates.** `numberOfTenderers` is present on **zero** of 1,802
  notices sampled. "How many suppliers competed" cannot be answered from the
  feed at all. Found by building.

What remains is concentration, which the research identified as the most
tractable available signal:

| Method | Awards | Share | Value |
|---|---|---|---|
| selective | 986 | 53.3% | £3.16bn |
| open | 292 | 15.8% | £7.32bn |
| direct | 86 | 4.6% | £60.3m |
| limited | 37 | 2.0% | £291m |

**6.6% of awards skipped open competition.** Buyer concentration surfaces cases
like one regulator placing 69.6% of 23 awards with a single supplier.

None of this is an accusation. Concentration has innocent explanations —
specialist markets, small local supplier bases, genuine incumbency. Sentinel
surfaces the pattern for a buyer to investigate; it does not score anyone.

## M11 — Highwater

```bash
./.venv/bin/python -m groundtruth.cli highwater
```

23,519 objections across 429 authorities. Confirms the research exactly:
**7,011 outcomes unknown**, and **not one row carries an address, postcode or
coordinate**. The authority's own planning reference is present on 23,457 rows —
that reference is the key to the site, but the location lives in the authority's
register, not in this file.

| Outcome | Objections | Homes |
|---|---|---|
| EA advice followed | 15,690 | 344,518 |
| Outcome unknown | 7,011 | — |
| **Granted against EA advice** | **635** | **2,949** |

### The override rate has been flat for nine years

| Year | Against advice | Rate |
|---|---|---|
| 2016-17 | 84 | 4.2% |
| 2018-19 | 105 | 4.8% |
| 2020-21 | 56 | 3.0% |
| 2022-23 | 60 | 3.4% |
| 2024-25 | 5 | 3.8% |

Independently reproduces the finding the research recorded for Sightline: the
rate is stable, even where raw counts move. Rates are computed over **decided
cases only** — including unknowns in the denominator would make the override
rate improve every time the Agency fails to learn an outcome, which a test now
prevents.

### A quiet trap in the year column

The publisher switches from `2020-21` to `2021/22` partway through the series.
Left alone the same financial year becomes two values and the time series splits
in half. `normalise_year` converges them, with tests for both forms.

## M12 — Plumbline

```bash
./.venv/bin/python -m groundtruth.cli plumbline
```

The published performance figure counts an application as decided on time if it
met an **agreed extension**, not the deadline in law. Both numbers are true;
only one is the one people think they are reading.

| Since 2023 | |
|---|---|
| Published headline "in time" | **82.8%** (7,894 major decisions) |
| Major dwellings within 13 weeks | **15.9%** (14,844 decisions) |
| Gap | **66.9 points** |

Individual authorities: Wokingham and Lambeth both report **100%** on the
published measure against roughly **17%** within the statutory period.

The two rates cover slightly different populations — all majors against major
dwellings — and both denominators are printed alongside them so neither is read
as the other. The gap is far too large to be explained by scope.

### The column that showed this directly was discontinued

The source used to publish "decided within maximum time", which is where agreed
extensions land. Comparing it with the 13-week columns gave extension reliance
outright. It was populated on **100% of rows in 2019** and **0% since 2024**:

| Year | Populated |
|---|---|
| 2018–19 | 100% |
| 2020 | 75.1% |
| 2021–23 | under 0.4% |
| 2024 onward | 0% |

The field that made the distinction visible is no longer published. Noticing
that quietly happening is the kind of thing this platform exists to do.

### Finding the data at all

The quarterly statistics release carries only a PDF factsheet. The actual tables
live in a separate live-tables collection whose attachments are reachable through
the gov.uk content API. The loader also fails loudly if a named column is
missing, rather than computing against whatever sits at that position.

## M13 — Sightline

```bash
./.venv/bin/python -m groundtruth.cli sightline
```

The Environment Agency publishes two objection streams in one workbook, and the
contrast between them is the finding:

| Stream | Objections | Outcome |
|---|---|---|
| Flood risk | 23,336 | tracked on 70.0% |
| Water quality | 180 | **no outcome field at all** |

"Unknown for some" and "no field at all" are different conditions. A consultee
regime being cut back on the grounds that it adds delay has, for one of its two
published objection streams, **no evidence base whatsoever** about whether the
advice was taken. The water quality sheet records why the Agency objected —
insufficient information (58), non-mains drainage in a sewered area (45) — and
nothing about what the authority then did.

### A bug in M11 that this milestone caught

The objections workbook holds two sheets. The ODS reader iterated every row in
the file regardless of sheet, so Highwater silently loaded **23,519** rows: the
23,336 flood risk objections plus 183 water quality rows appended underneath.
Those 183 were exactly the "(blank)" outcome category in the M11 output.

The reader now supports sheet selection, Highwater reads `Flood_Risk` only, and
the total is 23,336 — matching the published figure. The outcome counts were
never affected, since the appended rows carried no outcome value, so M11's
substantive findings stand; only the total was inflated. A test asserts the
flood sheet holds exactly 23,336 rows and that unfiltered reading picks up more.

## M14 — Lastmile

```bash
./.venv/bin/python -m groundtruth.cli lastmile
```

New homes have been legally required to be gigabit connectable since 2022, and
nobody checks nationally because the two halves live with different bodies:
Price Paid flags new builds at address level, BDUK publishes gigabit status per
premises. Both free, both unregistered. Ofcom's Connected Nations — the obvious
third source — returns 403 even from a browser user agent, so it is excluded.

### New-build postcodes are worse connected, not better

| North East, 1,423,443 premises | Gigabit |
|---|---|
| Postcodes with a recent new-build sale | **66.7%** |
| Everywhere else | **87.8%** |
| Difference | **−21.1 points** |

Sunderland is 91.2% overall and **28.5%** in its new-build postcodes.

The join is on **postcode, not property** — Price Paid carries no property
reference — so this measures the postcodes new homes sell in rather than the
homes themselves. That caveat is printed with the figures. Closing it properly
is exactly the address-to-property matching the place spine exists to do.

### Two mistakes worth recording

**Wrong column.** `current_gigabit` is a boolean; `Gigabit Grey/Black` is a
*subsidy status* meaning the market is already served. Reading the second as if
it were the first reported **0% coverage everywhere** — a confident, uniform,
completely wrong answer. A test now pins the distinction.

**Wrong loader.** Inserting 1.4m premises row by row from Python took minutes and
timed out. Handing the CSVs to DuckDB's own reader does it in **0.8 seconds**.
Both loaders now read natively.

## M15 — Junction

```bash
./.venv/bin/python -m groundtruth.cli junction
```

This milestone reversed its own premise, which is the reason it was worth doing.

### The schemas are not the problem

The four embedded capacity registers share **51 of 77 field names (66.2%)** and
run to 58–63 columns each. Ofgem mandated a common format and the operators
followed it.

An earlier version of this analysis reported **1.3%** commonality. That was
wrong: it had compared three genuine registers against an LTDS appendix table,
a different regulatory return entirely. Catching that mattered — the wrong number
supported exactly the story the research expected to find.

### Availability is the problem

| Operator | Catalogue says | Open export returns |
|---|---|---|
| UK Power Networks | 4,496 | **0** |
| Northern Powergrid | 937 | 937 |
| Electricity North West | 567 | **0** |
| SP Energy Networks | 770 | **0** |

**6,770 records advertised, 937 returned, 5,833 that never reach the open
route.** The datasets are listed, dated and sized in each portal's own
catalogue. Only one operator in four actually serves the data anonymously.

### An access quirk worth knowing

On these portals `/records` returns **HTTP 403** to an anonymous client while
`/exports/csv` returns **200** for the same dataset. Anyone testing the obvious
endpoint concludes the data is closed. It is not — and the earlier research note
claiming "full Opendatasoft APIs anonymously" was based on the catalogue
endpoint, so it is now stated precisely.

## M16 — Compass

```bash
./.venv/bin/python -m groundtruth.cli compass
```

The last of the thirteen systems, and the one with the sharpest number in it.

| England, 2015/16 → 2025/26 | | |
|---|---|---|
| All pupils | 8,559,540 → 8,920,227 | +4.2% |
| SEN support | 991,981 → 1,319,780 | +33.0% |
| **EHC plans** | 236,806 → **538,547** | **+127.4%** |

Statutory plans have more than doubled while the pupil population grew 4.2%.

Compass forecasts at **local authority** level, which is where places are
commissioned, and flags where an authority moves against its region — Newham is
projected up 58.1% against a London average of 21.6%. National and regional
projections cannot show that.

**Aggregates only.** No record about any individual child is read, held or
needed, and a test asserts that only aggregate columns are retained. That is
what makes the system deliverable without a data sharing agreement.

### A four-fold error, caught before it went anywhere

The first build reported **2,154,188 EHC plans** against a real England figure
near 576,000. The file is a cube: every combination of phase, establishment type
and hospital-school flag appears, each with its own `Total` row. Summing across
them counts the same children several times over. Only the fully-totalled cell
is taken now, a test asserts one row per authority, year and provision, and the
corrected figure lands where the published statistic does.

## M18 — cross-system chains

```bash
./.venv/bin/python -m groundtruth.cli chains
```

The argument for one platform rather than thirteen procurements is that one fact
sets off several systems at once. That is easy to assert, so the chains are
**executed against the gold tables** and report what each step actually returns.
A system with nothing to say is left out rather than narrated — asserted by a
test that runs the chains against an empty database and requires zero steps.

**A council approves housing** — one decision, six real answers:

| System | Answer |
|---|---|
| Plumbline | 15.9% decided within the legal deadline, against an 82.8% headline |
| Ledger | £1,491,818,575 recorded, **0 of it mappable** |
| Highwater | 635 of 23,336 objections overridden |
| Sightline | 180 water quality objections, **none with a recorded outcome** |
| Catchment | 89.6% of places already used across 317 districts |
| Lastmile | 66.7% gigabit in new-build postcodes against 87.8% elsewhere |

**A company goes bust** reaches Watchman, Bellwether and Sentinel; **a regulator
reissues its reference numbers** reaches Baseline, Junction and Bellwether — the
same repair in three industries.

### The compounding, counted

Two resolvers carry thirteen systems: **7** depend on the place spine, **3** on
the entity spine, **3** on both. Each spine was built once. A test asserts every
system is assigned to a spine, so none can quietly belong to neither.
