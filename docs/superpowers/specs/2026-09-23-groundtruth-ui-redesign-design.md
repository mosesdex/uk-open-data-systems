# UK GroundTruth: place-first interface

Design, 23 September 2026.

## Why

The interface is organised around the machine that produces the data rather than
the person who came to read it. Four problems, all confirmed by the owner:

1. It reads as an internal operations console: a permanent dark sidebar, a count
   beside every nav item, mono labels throughout.
2. The first screen is platform inventory. A visitor meets "13 of 13", "43 of
   45", "185,950,986" and "318" before anything about their own area.
3. Six top-level destinations plus thirteen named things, with no single obvious
   next step.
4. The visual register is flat: small uniform type, cards everywhere, little
   hierarchy.

The data does not have these problems. `places.byLad` already carries all 318
districts with per-question figures; the interface simply never leads with them.

## What this is

One dominant action, three doors behind it.

The front page asks what the public record says about your area and takes a
council or district name. Everything else is reachable but subordinate. The
thirteen stop being a menu and become what a place page answers.

## Not in scope

- The engine in `platform/`, the payload shape, and any figure or its wording.
- The thirteen static brief pages under `systems/`, which are separate SEO
  surfaces and were rewritten on 22 September.
- Visual identity. Navy, UK blue and IBM Plex stay, because the mark is in the
  outreach reaching 150 organisations and in the reel. The register changes, the
  identity does not.
- Any new data collection. Everything below is computed from `platform.json` as
  it ships today.

## Structure

| Destination | Route | Job |
|---|---|---|
| Front door | `#/` | Find a place. Three doors underneath. |
| Place | `#/places/<code>` | Everything the record holds for one area. |
| Compare | `#/compare` | All 318 districts, sortable, exportable. |
| Unusual | `#/unusual` | Where a place diverges from the published figure. |
| How this is built | `#/about` | Method, sources, corrections, limits, inventory. |
| One question | `#/questions/<id>` | The national view of one of the thirteen. |
| Organisation | `#/orgs/<id>` | One company or body across the record. |

The first five rows are the navigation; the last two are detail views reached
from them. Six top-level items become four. Organisations moves out of the top level and is
reached from search and from place pages. Sources and Method merge into "How this
is built", which also absorbs the platform inventory currently on the front page.

### URL compatibility, non-negotiable

The outreach campaign links to `#/places/<code>` and `#/systems/<id>` from 150
emails. Both must keep working:

- `#/places/<code>` is unchanged and remains the place route.
- `#/systems/<id>` aliases to `#/questions/<id>` with a replace, as the existing
  `legacy()` map already does for older routes.
- `#/systems`, `#/sources`, `#/method` alias to `#/`, `#/about`, `#/about`.

A test asserts every campaign URL still resolves to a rendered view.

## The front page

Header: the mark, the place search, the theme toggle. No sidebar at any width.

Hero: one question, one input.

- Heading: "What does the public record say about your area?"
- One field taking a council or district name, matching against `places.names`,
  which ships 318 entries today.
- Postcode entry is deliberately not in this pass. The payload carries counts
  about the postcode spine (1,749,109 rows) but no lookup, and a full postcode
  index is far too large to ship. An outcode-level lookup (around 3,000 entries,
  roughly 60KB) would cover it and needs a small addition to the engine, so it
  is a follow-on rather than a promise made here. The field accepts a typed
  postcode and says plainly that it needs a place name for now.
- Three real examples beside it as chips, chosen to be recognisable rather than
  extreme.
- One quiet credibility line underneath: 45 sources, 22 publishers, seventeen
  corrections published.

Then three doors as full-width rows, each carrying a real figure rather than an
icon: compare every district, what looks unusual right now, how this is built.

Then the thirteen questions listed plainly, in one column, for browsing. They do
not compete with the search.

The inventory figures move to "How this is built".

## The place page

This is the product. It is a document, not a dashboard.

1. **Identity.** The place name, and what kind of authority it is, since a county
   figure shown on a district must say so.
2. **Summary.** Two or three sentences generated from that place's own data,
   leading with its sharpest figure and naming the comparison. Built from the
   same logic already proven in the outreach generator.
3. **Answers.** One block per question that has data for this place:
   - the question in plain English
   - the figure, large, in Plex Mono with tabular figures
   - what it is measured against (national, or the published measure)
   - the caveat in the muted tone, never omitted
   - the source, its date, and a link to how it was computed
4. **Absences.** A question with no answer for this place says so and why, rather
   than being hidden. Two-tier areas are the common case.
5. **Take it away.** The place's figures as CSV, and a link to the method.

## Compare

The existing places table, given room: all 318 districts, sortable by any
column, filterable by region, exportable as CSV. This is the analyst's door and
needs no invention, only space and better type.

## Unusual

Computed client-side from `places.byLad` and `systems`. Ranked by the absolute
gap in percentage points between a place's own figure and its stated comparator,
for the questions that carry both (planning speed against the published measure,
school place use against the national rate, gigabit coverage against the national
share). The top fifty are listed, each with the place, the two figures, the gap
and the source. Below them sit the four recorded contradictions and the seventeen
corrections. Every row carries its source, so a reporter can check it before
quoting it.

## Visual register

Same tokens, different bearing.

- **Surfaces.** Cards only for the three doors and the answer blocks. Everything
  else sits on the page ground. No nested cards.
- **Type.** Body 16 to 17px. Place headline around 40px desktop, 28px mobile.
  Figures large in the mono face. One family in several weights, as now.
- **Space.** Wider gutters, more vertical rhythm, fewer rules and borders.
- **Colour.** Blue for actions and links only. Semantic colours for status.
  Near-white ground in light, deep navy in dark, both already tokenised.
- **Chrome.** No permanent sidebar. A slim header. On mobile the bottom bar drops
  from six items to three: Find, Compare, About.

## Carried forward, not to be regressed

The audit fixes of 22 September stay:

- one router-driven `h1` per document, with view titles as `h2`
- the drawer leaves the tab order when closed, with `aria-expanded` on its button
- 44px minimum targets, 16px form text
- the payload revalidated rather than refetched, boundaries parsed once
- both themes above the AA contrast line
- no em dash in any shipped string

## Verification

- `python3 tools/seo-check.py` passes with 0 errors.
- Browser checks at 375 and 1440: no horizontal overflow, one visible `h1`,
  targets at or above 44px, no console errors.
- Contrast re-measured in both themes, alpha composited.
- Every campaign URL resolves: `#/places/E07000032`, `#/systems/plumbline`,
  `#/places`, `#/method`, `#/sources`.
- The place page renders for a two-tier district, a unitary, and a combined
  authority, since all three shade differently.

## Risks

- **Breaking the campaign links.** Mitigated by aliases and an explicit test.
- **Losing analyst power** in pursuit of a cleaner front page. Mitigated by
  Compare keeping the full table.
- **Scope creep into the brief pages.** They are out of scope here.
- **The summary paragraph asserting something false.** It is generated from the
  same figures the blocks show, with the same caveats, and says nothing the data
  does not carry.

## Order of work

1. Router and aliases, with the campaign-URL test.
2. Front page.
3. Place page.
4. Compare and Unusual.
5. How this is built, absorbing the inventory.
6. Mobile pass, then the verification list above.

Steps 1 to 3 are the minimum that answers all four complaints, and are worth
shipping on their own. Steps 4 and 5 can follow as a second pass without leaving
the interface in a half-finished state, because the old routes keep working
throughout.
