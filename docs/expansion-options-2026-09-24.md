# GroundTruth expansion options

24 September 2026. A menu, not a plan. Pick by number; each picked item then
goes through the normal spec and plan cycle before anything is built.

## What the site does today, measured

- 13 questions, 45 registered sources, 318 districts: **296 in England and 22 in
  Wales**, not 318 English ones as first stated here.
- **9 of the 45 sources are fetched on every run and answer nothing.** The
  pipeline already pays the cost of collecting them.
- **4 of the 13 questions are national only** (Sentinel, Junction, Watchman,
  Baseline), so they are blank on all 318 place pages by construction.
- A typical place page therefore shows 4 to 9 answers, not 13. City of London
  shows 4.
- **Not England only, and not fully England either.** All 22 Welsh districts
  carry a real gigabit figure, because BDUK's open market review covers Wales;
  none carries a school-places figure, because DfE capacity data does not.
  Scotland and Northern Ireland are absent entirely. Corrected on 24 September
  after the payload was measured rather than assumed.

## The "London" result, checked

Typing `London` returns exactly one match: **City of London**, a district of
about 8,000 residents, with 4 of 13 questions answered. The 32 London
boroughs and the Greater London Authority are not reachable by that word at
all, because `places.names` holds only district names and no district is
called London.

This is the single worst first impression the site can give, and it is a
lookup gap, not a data gap. Items 1 and 2 below fix it.

---

## Lane A. Make the existing 13 answers deep (no new subject matter)

| # | Item | What it changes | Source | Effort |
|---|---|---|---|---|
| 1 | **Geography above the district** | `London`, `Greater Manchester`, `West Midlands` land on a combined-authority or region page that aggregates its districts, instead of a near-miss district | ONS LAD-to-CAUTH and LAD-to-region lookups, open | M |
| 2 | **Postcode and outcode lookup** | The search field accepts `SW1A 1AA` and resolves it. Deliberately deferred in the redesign spec; Code-Point Open is **already fetched** and idle | Code-Point Open (held) | M |
| 3 | **Ward and LSOA level** | "Your area" means your neighbourhood, not a borough of 300,000. Several existing sources already publish at LSOA | ONS boundaries, open | L |
| 4 | **Trend on every figure** | The payload already carries `history`, but place pages show one number with no direction. Show 3 to 5 years per figure per place | held | M |
| 5 | **Rank and percentile** | "89.5% of school places in use" alone says nothing. "89.5%, 212th of 318, up from 231st" is a finding | computed, no new source | S |
| 6 | **Push the 4 national-only questions down to place level** | Removes the biggest cause of blank place pages. Contracts Finder carries buyer addresses; the EDM return carries outlet coordinates; both can be placed with the spine that already exists | held | L |
| 7 | **Wales, Scotland, Northern Ireland** | Stops the site being silently wrong for a sixth of the country | StatsWales, Scottish Government, NISRA, all open | L |

## Lane B. Switch on sources already being fetched

Nine sources are collected every run and feed nothing. Cheapest new substance
available.

| # | Item | Question it answers | Source (already held) | Effort |
|---|---|---|---|---|
| 8 | **Housing energy efficiency** | What share of homes here are below EPC C, and how far is this place from its retrofit obligation | EPC register | M |
| 9 | **Care quality, not just care ownership** | Bellwether says who owns the beds. This says whether those beds are rated good | CQC syndication API | M |
| 10 | **Food safety inspection backlog** | How many premises here are overdue an inspection, and how that compares | FSA food hygiene | S |
| 11 | **Transport access against new housing** | Are new homes being built where there is a bus stop | NaPTAN | M |
| 12 | **Rainfall against spill timing** | Baseline normalises spills for rainfall annually. Readings allow per-event checks: did the spill follow the rain, or not | EA rainfall readings | M |
| 13 | **Council publication transparency league** | Which councils publish which datasets, and which publish nothing. A direct measure of open-data compliance, built from the catalogue itself | data.gov.uk CKAN | S |
| 14 | **Street-level joins** | USRN is held but unused; it would let several answers resolve to a street rather than a district | OS Open USRN | M |

## Lane C. New questions from new open sources

Each needs a new source. All listed sources are free and public; the ones
flagged **[check]** need a licence or access review against the project's
no-account, no-key, no-fee rule before being committed to.

| # | Item | Question | Source | Effort |
|---|---|---|---|---|
| 15 | **Local crime** | What is recorded here, at street level, and how has it moved | data.police.uk, open API, no key | M |
| 16 | **Road safety** | Where people are hurt, against speed limits and school locations | DfT STATS19, open | M |
| 17 | **NHS waiting times** | How long people here wait, by procedure, at the trust that serves them | NHS England statistics, open | L |
| 18 | **GP access** | Patients per GP here, and whether that is getting worse | NHS Digital workforce and list sizes, open | M |
| 19 | **NHS dentistry access** | Which practices here take new NHS patients | NHS open data | M |
| 20 | **School results and Ofsted** | Joined to the capacity figure Catchment already holds: are the full schools also the good ones | DfE performance tables, Ofsted MI, open | M |
| 21 | **Ofsted inspection backlog** | Which schools here are overdue an inspection | Ofsted MI, open | S |
| 22 | **Air quality against permissions** | Is new development being approved in places already over the limit | DEFRA AURN and background maps, open | L |
| 23 | **River and bathing water classification** | Pairs directly with the spill figures already held | EA classifications, open | M |
| 24 | **Homelessness and temporary accommodation** | How many households here are in temporary accommodation, and for how long | MHCLG live tables, open | M |
| 25 | **Right to Buy against replacement** | Council homes sold here versus council homes built | MHCLG, open | S |
| 26 | **Council financial distress** | Reserves, borrowing and overspend: which authorities are near a section 114 notice | MHCLG RO and RA returns, open | M |
| 27 | **Council tax and business rates collection** | What share is actually collected here | MHCLG, open | S |
| 28 | **Corporate and overseas property ownership** | Who owns your area, by company and by country **[check]** | HM Land Registry ownership datasets | M |
| 29 | **Empty and second homes** | How many dwellings here are empty, against the housing waiting list | Council tax base returns, open | S |
| 30 | **Local plan currency and housing delivery test** | Which councils are working to an out-of-date plan. This is the cause sitting behind Plumbline's 15.9% | MHCLG, open | M |
| 31 | **Planning appeal outcomes** | How often a refusal here is overturned on appeal | Planning Inspectorate, open | M |
| 32 | **Bus service withdrawal** | How much bus mileage this authority has lost | DfT bus statistics, open | S |
| 33 | **EV charge point coverage** | Charge points per 1,000 people here | DfT charging device statistics, open | S |
| 34 | **Broadband and mobile detail** | Beyond Lastmile's gigabit figure: actual speeds, and mobile not-spots | Ofcom Connected Nations, open | M |
| 35 | **FOI responsiveness** | Which councils answer, which delay, which refuse **[check]** | ICO decision notices, WhatDoTheyKnow | M |

## Lane D. Platform capability, not new data

| # | Item | Why it matters | Effort |
|---|---|---|---|
| 36 | **Watch a place or a question** | Turns one visit into a standing relationship. The single highest-leverage item for adoption | M |
| 37 | **Public API and per-place bulk download** | Makes the record usable by others, which is the point of the project | M |
| 38 | **Embeddable single-figure widget** | A local newsroom can put one figure and its source in a story | S |
| 39 | **Compare 2 to 5 places side by side** | The question every reader asks second | S |
| 40 | **Per-figure provenance page** | The exact file, its fetch time, and the transformation, so a civil servant can reproduce the number | M |
| 41 | **Change log per place** | What moved on this page since last time, which is also what makes alerts worth having | M |
| 42 | **Source quality scoring** | Completeness, timeliness, and how often each source breaks | S |
| 43 | **Automated contradiction detection** | The payload holds 4 contradictions found by hand. Find them by rule instead | M |

## Lane E. Audience surfaces

| # | Item | For whom | Effort |
|---|---|---|---|
| 44 | **Council self-service view** | An authority sees how it compares and, more usefully, which of its own datasets are missing or stale | M |
| 45 | **Reporter mode** | Leads ranked by divergence, each with a quote-ready sentence and the source link | M |
| 46 | **Evidence-backed letter to a councillor or MP** | A resident turns a figure into an action | S |
| 47 | **One-page place summary as PDF** | The thing people actually forward | S |
| 48 | **Plain-English mode** | Widens the audience past people who read statistics for a living | M |

---

## What to do first, if you want a recommendation

1, 2, 5 and 6 together. They are the reason the site felt thin: the search
could not find London, the figures had no context, and a third of the
questions were structurally blank on every place page. None of them need a new
source. Then 13 and 36, which are cheap and change what the site is for.
