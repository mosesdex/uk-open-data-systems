# Place depth: make a place page answer more, and mean more

Design, 24 September 2026.

## Why

The owner searched London and got City of London: one district of about 8,000
residents, with 4 of 13 questions answered. That is the honest state of the
product, and it has three separate causes, all measured:

1. **The lookup is district-only.** `places.names` holds 318 English district
   names. No district is called London, Greater Manchester or West Midlands, so
   the words most people type match nothing useful.
2. **Four of the thirteen questions carry no per-place data at all.** Baseline,
   Sentinel, Junction and Watchman are absent from `places.byLad` for every one
   of the 318 districts. A place page can therefore never show more than nine
   answers, and most show fewer. Ledger reaches only 58 districts.
3. **A figure with no comparison is not a finding.** "89.5% of school places in
   use" tells a reader nothing without knowing whether that is high, low, or
   moving.

None of the three needs a new subject area. All three are fixable from data
already on disk.

## What this is

Four changes, sharing one new spine.

| # | Change | Where |
|---|---|---|
| 1 | Geography above the district: region and combined authority pages | engine + app |
| 2 | Postcode lookup in the search field | engine + app |
| 5 | Rank, percentile and direction on every figure | app |
| 6 | Place-level answers for Baseline, Sentinel and Junction | engine |

The shared spine is **a postcode-to-district index built from Code-Point Open**,
which the pipeline already downloads and currently uses for nothing.

## Not in scope

- The other selected items. Item 13 (council publication transparency) and item
  36 (watch a place) are separate subsystems and get their own specs; the order
  is at the end of this document.
- The two source registry bugs found while measuring (EPC points at a host that
  now 301s elsewhere; FSA needs an `x-api-version: 2` header). Real, small, and
  operational rather than product; they belong with the pipeline hosting work.
- Watchman. It can be placed by the same mechanism as the others, through the
  registered office address in the Companies House bulk product, but the
  question currently finds **0 exposures nationally**, so every district would
  read zero. Placing it would add a row that says nothing. It waits until the
  insolvency register has accumulated enough to produce signal.
- Ward and LSOA level (item 3). Code-Point Open carries `Admin_ward_code`, so
  this becomes cheap later, but it is a separate change in granularity and is
  not attempted here.
- Ledger's 58-district coverage. That is a source problem, not a join problem:
  0 of 39,325 developer contributions carry a location.

## What the data actually supports

Everything below was checked against the files on disk, not assumed.

### Code-Point Open (already downloaded, 14.5 MB, feeding nothing)

- **1,747,986 postcodes** carry `Admin_district_code`, and also
  `Admin_ward_code`, `Admin_county_code`, eastings and northings.
- 2,863 distinct outcodes; 2,223 touch England.

Two candidate index granularities, measured:

| Index | Keys | Ambiguous keys | Accuracy of a dominant-district rule | Raw JSON |
|---|---|---|---|---|
| Outcode (`SW1A`) | 2,223 | 1,188 | 92.42% | ~49 KB |
| Sector (`SW1A 1`) | 9,129 | 2,228 | 96.45% | ~200 KB |

**Decision: ship the sector index.** 200 KB raw is small beside the 864 KB
payload already served, and 96.45% against 92.42% is the difference between a
lookup that usually works and one that is wrong for one reader in thirteen.

**Ambiguity is not hidden.** A sector spanning more than one district ships its
candidate districts, and the interface asks which one, rather than guessing and
being quietly wrong 3.55% of the time.

### Contracts Finder, for Sentinel

Each release carries `parties[].address.postalCode` for the buyer, and
`tender.items.deliveryAddresses[].postalCode` for where the work happens. The
delivery address is the better join and is preferred where present.

**Honest limit:** the corpus holds 2,065 releases. Spread over 318 districts
that is about six per district, so most districts will carry a small count.
The page says the count, so a reader can judge it.

### DNO embedded capacity registers, for Junction

The registers carry `postcode`, `town_city`, `county`, eastings and northings,
and `longitude`/`latitude` per connection. This is the cleanest of the three: a
direct coordinate, no inference.

### EDM storm overflow annual return, for Baseline

Each outlet carries **`Outlet Discharge NGR`**, a National Grid Reference such
as `SP6419046470`. Converted to eastings and northings and tested against
`ons_lad_boundaries.geojson`, which is already downloaded, this places every
outlet. This is the strongest of the three: about 14,239 outlets across 11
water and sewerage companies, so most districts carry real counts.

### Geography above the district

`ons_lad_county.json` holds 233 features and maps district to county only. Two
new ONS lookups are needed, both open and both small:

- district to region (`RGN`), which is how London boroughs become London
- district to combined authority (`CAUTH`), which is how Greater Manchester and
  the West Midlands become findable

## The changes

### 1. Geography above the district

A new route, `#/areas/<code>`, for a region or combined authority. It shows:

- what the area is, and which districts it contains
- each question's figure for the area as a whole, computed by the engine from
  the constituent districts rather than in the browser, so the weighting is
  explicit and testable
- the constituent districts as a list, each linking to its own page, with the
  widest divergence inside the area named

Searching `London` offers Greater London first and its 33 districts under it.
The district search keeps working exactly as now; areas are added to the same
match list, ranked above a district whose name merely contains the query.

**A whole-area figure must state how it was combined.** A percentage across
districts is a weighted mean, not an average of averages, and the page says so.
Where a question cannot be meaningfully combined, the area page says that
instead of inventing a number.

### 2. Postcode lookup

The search field accepts a postcode. `looksLikePostcode()` already exists in
`app/assets/lib/places.js` and currently produces a message saying a place name
is needed. It now resolves:

- sector found, one district: go straight to that place page
- sector found, several districts: ask which, listing them
- sector not found: say the postcode was not recognised, and offer name search

The index is a separate file, not part of `platform.json`, fetched only when a
postcode is actually typed. Nobody browsing by name pays 200 KB for it.

### 5. Rank, percentile and direction

Every figure on a place page gains a line stating where the place sits and
which way it is moving:

> 89.5% of school places in use. 212th of 317 districts with a figure. Up from
> 231st three years ago.

Computed in the browser from `places.byLad`, which already holds every
district's figure, and from `places.capacityTrend` and the payload's `history`
where a series exists. No new source, no engine change.

**Rules, so a rank never lies:**

- The denominator is districts that have a figure for that question, never 318.
  A rank of 212th of 257 is stated as such.
- Direction is shown only where the payload carries a comparable earlier value
  for the same place and the same definition. A changed definition is not a
  trend, and is not drawn as one.
- Higher is not automatically better. Each question declares its polarity, and
  a figure with no meaningful polarity gets a rank without a judgement.

### 6. Place-level Baseline, Sentinel and Junction

Each gains a `byLad` block from the joins described above. Each carries:

- the figure, and the count of underlying records it rests on
- what it is measured against, as the existing answers already do
- the caveat, which for these three is specific and must not be generalised:
  Sentinel's district count is small; Junction's connection is where the
  equipment is, not who benefits; Baseline's outlet is where the discharge
  happens, not where the sewage came from

**A district with no records says so**, with the reason, rather than being
hidden or shown as zero. Zero spills and no monitored outlet are different
facts and are never rendered the same way.

## Architecture

The engine in `platform/` gains one new module, the postcode spine, which every
one of the three new place joins uses. It is built once per run into the
DuckDB database and exported twice: as the per-question `byLad` blocks inside
`platform.json`, and as the standalone sector index the browser fetches.

Nothing about the payload's existing shape changes. `places.byLad` gains three
more question keys; the app reads them through `placeAnswers()` exactly as it
reads the nine already there.

The app gains: an area route and its builder, a postcode branch in the existing
search, and a ranking module beside `summary.js` and `unusual.js`.

## Verification

- `npm test`, `python3 tools/seo-check.py`, `node tools/contrast-check.mjs` all
  clean, as now.
- The postcode index is tested against Code-Point Open itself: a sample of
  10,000 real postcodes resolves to the district that Code-Point Open records
  for them, and the measured accuracy matches the 96.45% claimed here.
- Searching `London`, `Greater Manchester`, `West Midlands`, `Birmingham` and
  `SW1A 1AA` each reach a page that answers.
- Every campaign URL still resolves: `#/places/E07000032`,
  `#/systems/plumbline`, `#/places`, `#/method`, `#/sources`.
- Baseline, Sentinel and Junction each render on a two-tier district, a unitary
  and a London borough.
- A district with no records for a new question renders its absence sentence,
  and that sentence is checked to be true for that district.
- Ranks are checked against a recomputation from `places.byLad` in the test, not
  eyeballed.

## Risks

- **A rank that flatters or damns a council unfairly.** Mitigated by naming the
  denominator, refusing direction without a comparable earlier value, and
  declaring polarity per question rather than assuming it.
- **A postcode resolving to the wrong district.** Mitigated by shipping
  candidates for ambiguous sectors and asking, rather than guessing.
- **Whole-area figures that are arithmetically wrong.** Mitigated by computing
  them in the engine, where they are tested, and stating the weighting on the
  page.
- **Sentinel looking authoritative on six records.** Mitigated by showing the
  record count beside every figure it produces.
- **Payload growth.** The three new `byLad` blocks add to an 864 KB file. If it
  passes about 1.2 MB, the place blocks split into a per-place fetch. Measured
  before merge, not assumed.

## Order of work

1. The postcode spine in the engine, and the sector index it exports.
2. Postcode lookup in the search field (change 2).
3. Rank, percentile and direction (change 5), which needs no engine work and
   can land in parallel with 1 and 2.
4. Baseline, then Junction, then Sentinel (change 6), in that order, because
   Baseline has the most records and proves the join hardest.
5. Region and combined authority pages (change 1), last, because a whole-area
   figure is only worth showing once the questions behind it are placed.

Steps 1 to 3 already answer the complaint that started this. Steps 4 and 5 are
what make a place page worth returning to.

## What follows this spec

- **Item 13, council publication transparency.** A new question built from the
  data.gov.uk CKAN catalogue, which is already downloaded and holds 68,017
  datasets with their publishing organisation, last-modified date and licence.
  Its own spec.
- **Item 36, watch a place.** Subscriptions in Dexmail, a scheduled run that
  diffs each payload against the last and sends what moved. Needs the change
  log that step 5 of this spec makes possible. Its own spec.
- **Pipeline hosting and registry repair.** Move the fetch to the LunaNode box
  on a schedule, and fix the two registry bugs found while measuring: the EPC
  register now 301s to `get-energy-performance-data.communities.gov.uk`, and
  the Food Standards Agency returns 404 without `x-api-version: 2` and 200 with
  it. Operational, and independent of everything above.
