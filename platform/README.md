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
| M7–M9 remaining systems | next |
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
