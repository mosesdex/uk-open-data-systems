# Place depth Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make a place page answer more questions and say what each figure means, and let a reader reach their place by postcode or by the name of the region they actually live in.

**Architecture:** The engine in `platform/` already resolves postcodes and grid references to districts through `silver.place_postcode` and `place.py`; the work is to publish what it computes, place three more questions with the resolvers that exist, and export a small postcode index. The app reads the wider payload through the same `placeAnswers()` path it already uses, and gains two pure modules beside `summary.js` and `unusual.js`.

**Tech Stack:** Python 3.14 with DuckDB in `platform/` (pytest), classic scripts plus ES modules in `app/` (`node --test`), static publish through `.github/workflows/pages.yml`.

## Global Constraints

Every task's requirements implicitly include all of these.

- **No em dash in any shipped string.** Use a comma, a full stop or a colon.
- **One router-driven `<h1>` per document.** View headings are `h2` or lower. The `.pagehead` band holds the only `h1`.
- **The campaign URLs must keep resolving**: `#/places/E07000032`, `#/systems/plumbline`, `#/places`, `#/method`, `#/sources`. 150 sent emails point at them.
- **Never publish `platform/`.** The engine, the DuckDB file and `platform/data/` stay out of `_site/`.
- **New links go through `firstServable`** from `app/assets/lib/routes.js` with an ordered candidate list, and any new router head is added to `ROUTER_HEADS`. Linking directly at a route whose handler lands in a later task is the defect this project has hit four times.
- **44px minimum touch targets, 16px minimum form text.**
- **Both themes stay above the AA contrast line.**
- **An absence is stated, never rendered as a zero.** "No monitored outlet here" and "zero spills" are different facts.
- **A rank always states its denominator**, which is the count of districts holding a figure for that question, never 318.
- **Direction is shown only where the payload carries a comparable earlier value** for the same place under the same definition.
- **An ambiguous postcode sector offers its candidate districts.** It never picks one silently.
- Gates, all of which must pass before a task is complete:
  - `npm test`
  - `python3 tools/seo-check.py` (0 errors)
  - `node tools/contrast-check.mjs` (0 failing text nodes)
  - `cd platform && .venv/bin/python -m pytest` for any task touching `platform/`

## File Structure

**Engine, `platform/groundtruth/`**

- `places.py` (modify): gains a `PLACED` map beside `SOURCES` and `TIERED`, for gold tables that already carry `lad_code`.
- `postcodes.py` (create): builds the sector index from `silver.place_postcode`. One responsibility, nothing else.
- `systems/junction.py` (modify): gains a silver loader for the four capacity registers and a district aggregate.
- `systems/sentinel.py` (modify): the procurement loader keeps the buyer and delivery postcodes; a district aggregate follows.
- `areas.py` (create): region and combined-authority membership, and whole-area figures.
- `publish.py` (modify): writes the sector index beside `platform.json`, and adds `areas` to the payload.
- `sources.py` (modify): registers the two ONS lookups Task 7 needs.

**App, `app/assets/lib/`**

- `postcode.js` (create): pure sector parsing and lookup against the index.
- `rank.js` (create): pure ranking of one district against the rest for one question.
- `areas.js` (create): pure area membership and search matching.
- `entry.js` (modify): exports the three new modules onto `window.GT_LIB`.
- `places.js` (modify): `looksLikePostcode` stays; its comment stops saying postcodes are not resolved.

**App, `app/assets/`**

- `shell.js` (modify): the postcode branch in the search, rank lines on the place page, the area route and its builder.
- `app.css` (modify): the rank line and the area page.

**Tests**

- `platform/tests/test_places_placed.py`, `test_postcodes.py`, `test_junction_place.py`, `test_sentinel_place.py`, `test_areas.py`
- `tests/js/postcode.test.js`, `rank.test.js`, `areas.test.js`

---

### Task 1: Publish Baseline to the place pages

`gold.baseline_district` holds 290 districts and has done on every run. `place_view()` never reads it, because `SOURCES` matches gold tables by authority **name** and `TIERED` handles upper-tier publication. A third category is needed for tables that already carry `lad_code`.

**Files:**
- Modify: `platform/groundtruth/places.py`
- Modify: `app/assets/lib/answers.js`
- Test: `platform/tests/test_places_placed.py` (create)
- Test: `tests/js/answers.test.js` (modify, or create if absent)

**Interfaces:**
- Consumes: `gold.baseline_district(lad_code VARCHAR, outlets INTEGER, adjusted_spills DOUBLE, reported_spills DOUBLE)`.
- Produces: `places.byLad[<code>].baseline` in the payload, and a `baseline` entry from `placeAnswers()`. Tasks 5 and 6 add themselves to the same `PLACED` map.

- [ ] **Step 1: Write the failing test**

Create `platform/tests/test_places_placed.py`:

```python
import duckdb
import pytest

from groundtruth import places as PL


@pytest.fixture
def con():
    con = duckdb.connect(":memory:")
    con.execute("CREATE SCHEMA silver; CREATE SCHEMA gold")
    con.execute("CREATE TABLE silver.lad (lad_code VARCHAR, lad_name VARCHAR)")
    con.execute("INSERT INTO silver.lad VALUES ('E07000032', 'Amber Valley'), "
                "('E09000007', 'Camden')")
    con.execute("""CREATE TABLE gold.baseline_district
                   (lad_code VARCHAR, outlets INTEGER,
                    adjusted_spills DOUBLE, reported_spills DOUBLE)""")
    con.execute("INSERT INTO gold.baseline_district VALUES "
                "('E07000032', 14, 812.5, 790.0)")
    return con


def test_a_placed_table_reaches_bylad(con):
    view = PL.place_view(con)
    assert view["places"]["E07000032"]["baseline"]["outlets"] == 14
    assert view["places"]["E07000032"]["baseline"]["adjusted_spills"] == 812.5


def test_a_district_absent_from_the_table_gains_no_entry(con):
    view = PL.place_view(con)
    assert "baseline" not in view["places"].get("E09000007", {})


def test_resolution_reports_placed_coverage(con):
    view = PL.place_view(con)
    rep = view["resolution"]["baseline"]
    assert rep["matched"] == 1
    assert rep["names"] == 2
    assert rep["rate"] == 50.0


def test_the_join_column_is_dropped_from_the_published_row(con):
    view = PL.place_view(con)
    assert "lad_code" not in view["places"]["E07000032"]["baseline"]
```

- [ ] **Step 2: Run it to make sure it fails**

Run: `cd platform && .venv/bin/python -m pytest tests/test_places_placed.py -v`
Expected: FAIL, `KeyError: 'baseline'`.

- [ ] **Step 3: Add the PLACED category**

In `platform/groundtruth/places.py`, after the `TIERED` map (currently ending at line 203), add:

```python
# Systems whose gold table already carries lad_code, because a postcode or a
# grid reference put it there rather than an authority name. SOURCES matches on
# a spelled authority name and TIERED handles upper-tier publication; neither
# fits a table that was placed by the spine itself, which is why Baseline was
# computed on every run and then dropped at this step.
#
# The value is the column holding the district code. Everything else on the row
# is published as the question's figures.
PLACED = {
    "baseline": "lad_code",
}
```

Then, inside `place_view()`, after the `for system, spec in TIERED.items():` loop and before the school capacity block, add:

```python
    for system, key in PLACED.items():
        table = f"gold.{system}_district"
        if not _table_exists(con, table):
            continue
        cur = con.execute(f"SELECT * FROM {table} WHERE {key} IS NOT NULL")
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        placed = {r[key] for r in rows}
        for r in rows:
            code = r[key]
            if code not in index_codes:
                continue
            # The join column is how the row got here; it says nothing the key
            # of the dictionary does not already say.
            places.setdefault(code, {})[system] = {k: v for k, v in r.items() if k != key}
        resolution[system] = {
            "names": len(index_codes),
            "matched": len(placed & index_codes),
            "rate": round(100 * len(placed & index_codes) / len(index_codes), 1)
                    if index_codes else 0.0,
            "unmatched": sorted(placed - index_codes)[:12],
        }
```

`index_codes` does not exist yet. Add it immediately after `index = build_index(con)` near the top of `place_view()`:

```python
    # Every district the platform knows about, used below to report what share
    # of them a placed system actually reached, and to refuse a code the
    # boundaries do not carry.
    index_codes = {c for (c,) in con.execute("SELECT lad_code FROM silver.lad").fetchall()}
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd platform && .venv/bin/python -m pytest tests/test_places_placed.py -v`
Expected: 4 passed.

- [ ] **Step 5: Teach the app what a Baseline block says**

In `app/assets/lib/answers.js`, add to the `QUESTIONS` array, after the `lastmile` entry:

```javascript
  {
    id: 'baseline',
    name: 'Baseline',
    question: 'How many sewage spills were recorded here, after adjusting for how long each monitor was working?',
    unit: null,
    figure: p => p.adjusted_spills,
    against: p => p.reported_spills,
    againstLabel: 'the number the water companies reported',
    caveat: p => `Counted across ${n(p.outlets)} monitored storm overflow${p.outlets === 1 ? '' : 's'} `
      + `placed in this district by their grid reference. The outlet is where the discharge happens, `
      + `not where the sewage came from, and a district with no monitored outlet is not a district `
      + `with no spills.`,
  },
```

- [ ] **Step 6: Write the failing test for it**

Add to `tests/js/answers.test.js`:

```javascript
import { placeAnswers } from '../../app/assets/lib/answers.js';

const PAYLOAD = {
  systems: {},
  places: { byLad: { E07000032: { baseline: { outlets: 14, adjusted_spills: 812.5, reported_spills: 790 } } } },
};

test('baseline answers with its adjusted figure, against the reported one', () => {
  const a = placeAnswers('E07000032', PAYLOAD).find(x => x.id === 'baseline');
  assert.equal(a.figure, 812.5);
  assert.equal(a.against, 790);
  assert.match(a.caveat, /14 monitored storm overflows/);
});

test('a district with one outlet is not described in the plural', () => {
  const one = { systems: {}, places: { byLad: { X: { baseline: { outlets: 1, adjusted_spills: 3, reported_spills: 3 } } } } };
  const a = placeAnswers('X', one).find(x => x.id === 'baseline');
  assert.match(a.caveat, /1 monitored storm overflow /);
});
```

- [ ] **Step 7: Run both suites**

Run: `npm test`
Expected: all pass, count above 67.

- [ ] **Step 8: Commit**

```bash
git add platform/groundtruth/places.py platform/tests/test_places_placed.py app/assets/lib/answers.js tests/js/answers.test.js
git commit -m "Publish the Baseline figure the engine has always computed"
```

---

### Task 2: Export the postcode sector index

**Files:**
- Create: `platform/groundtruth/postcodes.py`
- Modify: `platform/groundtruth/publish.py`
- Test: `platform/tests/test_postcodes.py` (create)

**Interfaces:**
- Consumes: `silver.place_postcode(postcode_key, postcode, positional_quality, easting, northing, lad_code, ward_code, country_code)`, 1,749,109 rows.
- Produces: `app/data/postcodes.json`, shaped `{"generated": "<iso>", "sectors": {"SW1A1": ["E09000033"], "GU216": ["E07000217", "E07000214"]}}`. Task 3 reads exactly this shape. The first code in each list is the dominant district; a list of length one is unambiguous.

- [ ] **Step 1: Write the failing test**

Create `platform/tests/test_postcodes.py`:

```python
import duckdb
import pytest

from groundtruth import postcodes as PC


@pytest.fixture
def con():
    con = duckdb.connect(":memory:")
    con.execute("CREATE SCHEMA silver")
    con.execute("""CREATE TABLE silver.place_postcode
                   (postcode_key VARCHAR, postcode VARCHAR, positional_quality INTEGER,
                    easting INTEGER, northing INTEGER, lad_code VARCHAR,
                    ward_code VARCHAR, country_code VARCHAR)""")
    rows = [
        ("SW1A1AA", "SW1A 1AA", 10, 0, 0, "E09000033", "W1", "E92000001"),
        ("SW1A1AB", "SW1A 1AB", 10, 0, 0, "E09000033", "W1", "E92000001"),
        # one sector, two districts, heavily skewed
        ("GU216AA", "GU21 6AA", 10, 0, 0, "E07000217", "W2", "E92000001"),
        ("GU216AB", "GU21 6AB", 10, 0, 0, "E07000217", "W2", "E92000001"),
        ("GU216AC", "GU21 6AC", 10, 0, 0, "E07000214", "W3", "E92000001"),
        # Scotland, which this platform does not cover
        ("AB101AB", "AB10 1AB", 10, 0, 0, None, None, "S92000003"),
    ]
    con.executemany("INSERT INTO silver.place_postcode VALUES (?,?,?,?,?,?,?,?)", rows)
    return con


def test_an_unambiguous_sector_yields_one_district(con):
    idx = PC.sector_index(con)
    assert idx["sectors"]["SW1A1"] == ["E09000033"]


def test_an_ambiguous_sector_yields_every_district_dominant_first(con):
    idx = PC.sector_index(con)
    assert idx["sectors"]["GU216"] == ["E07000217", "E07000214"]


def test_a_postcode_with_no_district_is_left_out(con):
    idx = PC.sector_index(con)
    assert "AB101" not in idx["sectors"]


def test_the_index_reports_its_own_accuracy(con):
    idx = PC.sector_index(con)
    # 5 placed postcodes, 4 of which the dominant rule places correctly
    assert idx["postcodes"] == 5
    assert idx["sectors_total"] == 2
    assert idx["dominant_accuracy_pct"] == 80.0


def test_the_key_is_the_sector_with_no_space(con):
    idx = PC.sector_index(con)
    assert all(" " not in k for k in idx["sectors"])
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd platform && .venv/bin/python -m pytest tests/test_postcodes.py -v`
Expected: FAIL, `ModuleNotFoundError: No module named 'groundtruth.postcodes'`.

- [ ] **Step 3: Write the module**

Create `platform/groundtruth/postcodes.py`:

```python
"""The postcode index the browser can afford to read.

silver.place_postcode holds 1,749,109 rows. Shipping it would be absurd, and
shipping nothing is why the front page has to tell a reader that a postcode is
not matched. A sector, the outcode plus the first digit of the incode, is the
compromise that was measured rather than guessed:

    outcode  SW1A     2,223 English keys, 92.42% placed by the dominant rule
    sector   SW1A 1   9,129 English keys, 96.45% placed by the dominant rule

The sector index wins and is what this builds. The remaining 3.55% is not
absorbed by guessing: a sector that spans more than one district ships all of
them, dominant first, and the interface asks which one rather than being
quietly wrong for one reader in twenty-eight.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone

import duckdb


def sector_index(con: duckdb.DuckDBPyConnection) -> dict:
    """Sector to districts, dominant first, with the accuracy it achieves."""
    rows = con.execute("""
        SELECT postcode_key, lad_code
        FROM silver.place_postcode
        WHERE lad_code IS NOT NULL AND length(postcode_key) >= 5
    """).fetchall()

    counts: dict[str, Counter] = defaultdict(Counter)
    for key, lad in rows:
        # postcode_key is the postcode with the space removed, so the incode is
        # always the last three characters and the sector is everything before
        # the final two.
        counts[key[:-2]][lad] += 1

    sectors = {
        sector: [lad for lad, _ in c.most_common()]
        for sector, c in counts.items()
    }
    total = sum(sum(c.values()) for c in counts.values())
    dominant = sum(max(c.values()) for c in counts.values())

    return {
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "postcodes": total,
        "sectors_total": len(sectors),
        "ambiguous_sectors": sum(1 for c in counts.values() if len(c) > 1),
        "dominant_accuracy_pct": round(100 * dominant / total, 2) if total else 0.0,
        "sectors": dict(sorted(sectors.items())),
    }
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd platform && .venv/bin/python -m pytest tests/test_postcodes.py -v`
Expected: 5 passed.

- [ ] **Step 5: Write it out beside the payload**

`platform/groundtruth/publish.py` writes the payload in `write(con, dest)` at
line 493, where `dest` is `app/data/platform.json`, so the index belongs beside
it at `dest.parent`. `_exists(con, schema, table)` is already defined at line 39.

Add this to `write()`, immediately after the first `_dump(payload, dest)` call,
so the index is written even if the audit or history steps below it raise:

```python
    # The postcode index is a separate file on purpose. It is about 200 KB, and
    # a reader browsing by district name should never pay for it; the front page
    # fetches it only when a postcode is actually typed.
    from . import postcodes as PC
    if _exists(con, "silver", "place_postcode"):
        (dest.parent / "postcodes.json").write_text(
            json.dumps(PC.sector_index(con), separators=(",", ":")), encoding="utf8")
```

- [ ] **Step 6: Build it against the real database and check the measured claims**

Run:
```bash
cd platform && .venv/bin/python -c "
import duckdb, json
from groundtruth import postcodes as PC
con = duckdb.connect('data/groundtruth.duckdb', read_only=True)
idx = PC.sector_index(con)
print('sectors', idx['sectors_total'], 'ambiguous', idx['ambiguous_sectors'],
      'accuracy', idx['dominant_accuracy_pct'])
print('bytes', len(json.dumps(idx, separators=(',',':'))))
"
```
Expected: roughly 9,100 sectors, accuracy near 96.4%, under 300,000 bytes. If the accuracy is materially below 96%, stop and report it rather than proceeding; the spec's decision rests on that number.

- [ ] **Step 7: Commit**

```bash
git add platform/groundtruth/postcodes.py platform/groundtruth/publish.py platform/tests/test_postcodes.py
git commit -m "Export a postcode sector index the browser can afford to read"
```

---

### Task 3: Resolve a postcode in the search field

**Files:**
- Create: `app/assets/lib/postcode.js`
- Modify: `app/assets/lib/entry.js`, `app/assets/lib/places.js` (comment only), `app/assets/shell.js`
- Test: `tests/js/postcode.test.js` (create)

**Interfaces:**
- Consumes: `app/data/postcodes.json` as Task 2 shapes it.
- Produces: `sectorKey(raw)` returning a sector key or null, and `sectorDistricts(raw, index)` returning an array of district codes, possibly empty. Both pure; the fetch lives in `shell.js`.

- [ ] **Step 1: Write the failing test**

Create `tests/js/postcode.test.js`:

```javascript
import test from 'node:test';
import assert from 'node:assert/strict';
import { sectorKey, sectorDistricts } from '../../app/assets/lib/postcode.js';

const INDEX = { sectors: { SW1A1: ['E09000033'], GU216: ['E07000217', 'E07000214'] } };

test('a full postcode reduces to its sector', () => {
  assert.equal(sectorKey('SW1A 1AA'), 'SW1A1');
  assert.equal(sectorKey('sw1a1aa'), 'SW1A1');
  assert.equal(sectorKey('  GU21   6AC '), 'GU216');
});

test('something that is not a postcode has no sector', () => {
  assert.equal(sectorKey('Camden'), null);
  assert.equal(sectorKey(''), null);
  assert.equal(sectorKey(null), null);
  assert.equal(sectorKey('SW1A'), null);
});

test('an unambiguous sector returns one district', () => {
  assert.deepEqual(sectorDistricts('SW1A 1AA', INDEX), ['E09000033']);
});

test('an ambiguous sector returns every candidate, dominant first', () => {
  assert.deepEqual(sectorDistricts('GU21 6AC', INDEX), ['E07000217', 'E07000214']);
});

test('a sector the index does not carry returns nothing', () => {
  assert.deepEqual(sectorDistricts('ZZ99 9ZZ', INDEX), []);
});

test('a sector outside England still resolves, so the caller can say where', () => {
  // The index carries Wales and Scotland on purpose. This module reports what
  // the index holds; deciding that England only is covered is the caller's job.
  const wales = { sectors: { CF101: ['W06000015'] } };
  assert.deepEqual(sectorDistricts('CF10 1AA', wales), ['W06000015']);
});

test('a missing index returns nothing rather than throwing', () => {
  assert.deepEqual(sectorDistricts('SW1A 1AA', null), []);
  assert.deepEqual(sectorDistricts('SW1A 1AA', {}), []);
});
```

- [ ] **Step 2: Run it to verify it fails**

Run: `node --test tests/js/postcode.test.js`
Expected: FAIL, cannot find module `postcode.js`.

- [ ] **Step 3: Write the module**

Create `app/assets/lib/postcode.js`:

```javascript
/* Turning a typed postcode into the district it sits in.

   The index this reads is built by platform/groundtruth/postcodes.py and
   served as app/data/postcodes.json. It is keyed by sector, the outcode plus
   the first digit of the incode, which places 96.45% of postcodes by its first
   candidate. The remaining sectors span more than one district and carry all
   of them, dominant first, so the caller can ask rather than guess. */

const FULL = /^([A-Z]{1,2}\d[A-Z\d]?)\s*(\d)([A-Z]{2})$/i;

export function sectorKey(raw) {
  const m = FULL.exec(String(raw || '').trim().replace(/\s+/g, ' '));
  return m ? (m[1] + m[2]).toUpperCase() : null;
}

export function sectorDistricts(raw, index) {
  const key = sectorKey(raw);
  if (!key) return [];
  const sectors = (index && index.sectors) || null;
  if (!sectors) return [];
  const hit = sectors[key];
  return Array.isArray(hit) ? hit.slice() : [];
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `node --test tests/js/postcode.test.js`
Expected: 7 passed.

- [ ] **Step 5: Bridge it to the shell**

In `app/assets/lib/entry.js`, add the import and the two names to the `Object.assign`:

```javascript
import { sectorKey, sectorDistricts } from './postcode.js';
```

- [ ] **Step 6: Replace the "not matched yet" message with a real lookup**

In `app/assets/shell.js`, inside `buildHome()`, replace the `draw` function and the message it sets. The index is fetched once, lazily, the first time a postcode is recognised:

```javascript
    // The sector index is about 200 KB and only a postcode needs it, so it is
    // fetched on first use rather than on page load. One in-flight request at
    // a time; every later call reuses the resolved value.
    let pcIndex = null, pcPending = null;
    const loadIndex = () => {
      if (pcIndex) return Promise.resolve(pcIndex);
      if (!pcPending) {
        pcPending = fetch('data/postcodes.json')
          .then(r => (r.ok ? r.json() : null))
          .then(j => { pcIndex = j; return j; })
          .catch(() => null);
      }
      return pcPending;
    };

    const say = text => {
      if (!note) return;
      note.textContent = text || '';
      note.hidden = !text;
    };

    const showCandidates = codes => {
      hits.innerHTML = codes.map(code =>
        `<button class="find__hit" role="option" data-code="${esc(code)}">${
          esc(names[code] || code)}</button>`).join('');
      hits.hidden = !codes.length;
    };

    // The index carries Wales and Scotland as well as England: 9,113 English
    // sectors, 592 Welsh, 1,136 Scottish. That is deliberate. This platform's
    // sources are England only, and a Welsh reader who types a real postcode is
    // owed that sentence, not "not in the index", which would be false.
    const COUNTRY = { W: 'Wales', S: 'Scotland', N: 'Northern Ireland' };

    const resolvePostcode = q => {
      loadIndex().then(idx => {
        // The field may have moved on while the index was loading.
        if (input.value !== q) return;
        const all = lib.sectorDistricts ? lib.sectorDistricts(q, idx) : [];
        if (!all.length) {
          say('That postcode is not in the index. Try the council or district name.');
          return;
        }
        const codes = all.filter(code => names[code]);
        if (!codes.length) {
          // The sector resolved, to somewhere this platform does not cover.
          const where = COUNTRY[String(all[0])[0]];
          say(where
            ? `That postcode is in ${where}. Every source this platform reads is England only, so there is nothing to show for it yet.`
            : 'That postcode resolves to a district this platform does not carry.');
          return;
        }
        if (codes.length === 1) { go(codes[0]); return; }
        showCandidates(codes);
        say('That postcode sector spans more than one district. Which one?');
      });
    };

    const draw = () => {
      const q = input.value;
      const found = lib.matchPlaces ? lib.matchPlaces(q, names) : [];
      hits.innerHTML = found.map(h =>
        `<button class="find__hit" role="option" data-code="${esc(h.code)}">${esc(h.name)}</button>`).join('');
      hits.hidden = !found.length;
      if (found.length) { say(''); return; }
      if (lib.sectorKey && lib.sectorKey(q)) { say('Looking that postcode up.'); resolvePostcode(q); return; }
      say(q.trim() ? 'No district of that name. Try the council that covers it.' : '');
    };
```

- [ ] **Step 7: Correct the comment that says postcodes are not resolved**

In `app/assets/lib/places.js`, replace the third paragraph of the header comment:

```javascript
   A typed postcode is resolved by postcode.js against a sector index served
   separately, so this module stays the name index and nothing more.
```

- [ ] **Step 8: Verify in the browser**

Start the preview, then at `#/` check all four branches:

- `SW1A 1AA` is an ambiguous sector (`E09000033`, `E09000032`) and must offer both, not choose.
- `GU21 6AA` is unambiguous (`E07000217`) and must go straight to Amber Valley's equivalent, the Woking place page.
- `CF10 1AA` is Cardiff and must say the postcode is in Wales and that the sources are England only.
- `ZZ99 9ZZ` is in no sector and must say it is not in the index.

Check the console is clean in every case.

- [ ] **Step 9: Run the gates and commit**

```bash
npm test && python3 tools/seo-check.py && node tools/contrast-check.mjs
git add app/assets/lib/postcode.js app/assets/lib/entry.js app/assets/lib/places.js app/assets/shell.js tests/js/postcode.test.js
git commit -m "Resolve a typed postcode to its district, and ask when a sector spans two"
```

---

### Task 4: Rank, percentile and direction on every figure

No engine work. This ranks a district against every other district holding a figure for the same question, reusing `placeAnswers()` so there is exactly one definition of what a question's figure is.

**Files:**
- Create: `app/assets/lib/rank.js`
- Modify: `app/assets/lib/entry.js`, `app/assets/shell.js`, `app/assets/app.css`
- Test: `tests/js/rank.test.js` (create)

**Interfaces:**
- Consumes: `placeAnswers(code, payload)` from `answers.js`, and `payload.places.byLad`.
- Produces: `rankFor(code, questionId, payload)` returning `{rank, of, percentile, polarity}` or `null`, and `rankSentence(r)` returning a string or `null`.

- [ ] **Step 1: Write the failing test**

Create `tests/js/rank.test.js`:

```javascript
import test from 'node:test';
import assert from 'node:assert/strict';
import { rankFor, rankSentence } from '../../app/assets/lib/rank.js';

const lad = (pct) => ({ lastmile: { gigabit_pct: pct, premises: 1000 } });
const PAYLOAD = {
  systems: {},
  places: { byLad: { A: lad(90), B: lad(80), C: lad(70), D: { catchment: { utilisation_pct: 95, measured_pct: 99 } } } },
};

test('the highest figure ranks first', () => {
  const r = rankFor('A', 'lastmile', PAYLOAD);
  assert.equal(r.rank, 1);
  assert.equal(r.of, 3);
});

test('the denominator counts only districts holding that figure', () => {
  // D has no lastmile block, so it is not in the denominator
  assert.equal(rankFor('C', 'lastmile', PAYLOAD).of, 3);
});

test('a district with no figure for the question has no rank', () => {
  assert.equal(rankFor('D', 'lastmile', PAYLOAD), null);
  assert.equal(rankFor('ZZ', 'lastmile', PAYLOAD), null);
});

test('ties share a rank rather than being ordered arbitrarily', () => {
  const tied = { systems: {}, places: { byLad: { A: lad(80), B: lad(80), C: lad(70) } } };
  assert.equal(rankFor('A', 'lastmile', tied).rank, 1);
  assert.equal(rankFor('B', 'lastmile', tied).rank, 1);
  assert.equal(rankFor('C', 'lastmile', tied).rank, 3);
});

test('the sentence names the denominator, never 318', () => {
  const s = rankSentence(rankFor('B', 'lastmile', PAYLOAD));
  assert.match(s, /2nd of 3 districts/);
  assert.doesNotMatch(s, /318/);
});

test('polarity is declared per question, not inferred from the number', () => {
  const one = { systems: {}, places: { byLad: { D: PAYLOAD.places.byLad.D, E: { catchment: { utilisation_pct: 80, measured_pct: 99 } } } } };
  assert.equal(rankFor('D', 'catchment', one).polarity, 'high-is-worse');
  assert.equal(rankFor('A', 'lastmile', PAYLOAD).polarity, 'high-is-better');
});

test('a question whose polarity is genuinely ambiguous is left unjudged', () => {
  const p = { systems: {}, places: { byLad: {
    A: { compass: { projected_change_pct: 12 } }, B: { compass: { projected_change_pct: 4 } } } } };
  assert.equal(rankFor('A', 'compass', p).polarity, 'none');
});

test('the sentence never says better or worse, whatever the polarity', () => {
  // The rank states position. Whether that position is good is the reader's
  // call, and the caveat beside it is what they need to make it.
  for (const code of ['A', 'B', 'C']) {
    assert.doesNotMatch(rankSentence(rankFor(code, 'lastmile', PAYLOAD)), /better|worse/);
  }
});

test('a rank of one district says so rather than claiming a ranking', () => {
  const only = { systems: {}, places: { byLad: { A: lad(90) } } };
  assert.equal(rankSentence(rankFor('A', 'lastmile', only)), null);
});
```

- [ ] **Step 2: Run it to verify it fails**

Run: `node --test tests/js/rank.test.js`
Expected: FAIL, cannot find module `rank.js`.

- [ ] **Step 3: Write the module**

Create `app/assets/lib/rank.js`:

```javascript
/* Where one district sits among the others, for one question.

   A figure on its own is not a finding. "89.5% of school places in use" tells
   a reader nothing until they know whether that is unusual. This ranks a
   district against every other district that holds a figure for the same
   question, and states that denominator, because a rank out of 318 when only
   257 districts carry the figure is a false claim about the other 61.

   The figure is read through placeAnswers, not re-derived here, so there is
   one definition of what each question's figure is and no second chance to
   disagree with the page it annotates.

   Polarity is declared per question rather than assumed. Being high is bad for
   spills and for school place pressure, good for gigabit coverage, and neither
   for a projected change in plan numbers. A question with no honest polarity
   is ranked and left unjudged. */

import { placeAnswers } from './answers.js';

const POLARITY = {
  plumbline: 'high-is-better',
  catchment: 'high-is-worse',
  lastmile: 'high-is-better',
  baseline: 'high-is-worse',
  bulwark: 'high-is-better',
  highwater: 'high-is-worse',
  sightline: 'high-is-worse',
  bellwether: 'high-is-worse',
  ledger: 'high-is-better',
  compass: 'none',
};

const ORDINAL = n => {
  const r100 = n % 100, r10 = n % 10;
  if (r100 >= 11 && r100 <= 13) return n + 'th';
  return n + (r10 === 1 ? 'st' : r10 === 2 ? 'nd' : r10 === 3 ? 'rd' : 'th');
};

/* Every district's figure for one question.

   A place page calls rankFor once per answer, and each call would otherwise
   walk all 318 districts through placeAnswers: thirteen answers on one page is
   over four thousand traversals of the payload. The distribution for a whole
   payload is built once, on the first question that needs it, and reused.

   Keyed by the payload object itself, so a payload revalidated in place is
   recomputed rather than answered from a stale distribution. */
const CACHE = new WeakMap();

function figures(questionId, payload) {
  if (!payload || typeof payload !== 'object') return new Map();
  let byQuestion = CACHE.get(payload);
  if (!byQuestion) { byQuestion = new Map(); CACHE.set(payload, byQuestion); }
  const cached = byQuestion.get(questionId);
  if (cached) return cached;

  const byLad = (payload.places && payload.places.byLad) || {};
  const out = new Map();
  for (const code of Object.keys(byLad)) {
    const hit = placeAnswers(code, payload).find(a => a.id === questionId);
    if (hit && Number.isFinite(Number(hit.figure))) out.set(code, Number(hit.figure));
  }
  byQuestion.set(questionId, out);
  return out;
}

export function rankFor(code, questionId, payload) {
  const all = figures(questionId, payload);
  const mine = all.get(code);
  if (mine == null) return null;

  // Descending, so rank 1 is the largest figure. Ties share a rank: the count
  // of districts strictly above this one, plus one.
  let above = 0;
  for (const v of all.values()) if (v > mine) above += 1;
  const rank = above + 1;
  const of = all.size;

  return {
    rank,
    of,
    figure: mine,
    percentile: of > 1 ? Math.round(100 * (of - rank) / (of - 1)) : null,
    polarity: POLARITY[questionId] || 'none',
  };
}

export function rankSentence(r) {
  // One district is not a ranking, and saying "1st of 1" implies a contest.
  if (!r || r.of < 2) return null;
  return `${ORDINAL(r.rank)} of ${r.of} districts with a figure for this question.`;
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `node --test tests/js/rank.test.js`
Expected: 9 passed.

- [ ] **Step 5: Render the line on the place page**

In `app/assets/lib/entry.js` add `rankFor` and `rankSentence`. Then in `app/assets/shell.js`, inside `buildPlacePage`, in the branch that renders an `.answer` article from an entry `a`, add after the `answer__v` line:

```javascript
            ${(() => {
              const r = lib.rankFor && lib.rankFor(code, a.id, Platform.payload());
              const s = r && lib.rankSentence && lib.rankSentence(r);
              return s ? `<p class="answer__r">${esc(s)}</p>` : '';
            })()}
```

`lib` and `code` must both be in scope at that point; read the function before editing and hoist `const lib = window.GT_LIB || {};` to the top of `buildPlacePage` if it is not already there.

- [ ] **Step 6: Style it**

In `app/assets/app.css`, beside the other `.answer__*` rules:

```css
.answer__r{margin:.25rem 0 0;font-size:14px;color:var(--ink-3)}
```

- [ ] **Step 7: Verify the rank against a recomputation**

Run:
```bash
node -e "
const fs=require('fs');
import('./app/assets/lib/rank.js').then(async ({rankFor})=>{
  const p=JSON.parse(fs.readFileSync('app/data/platform.json','utf8'));
  const r=rankFor('E07000032','lastmile',p);
  const all=Object.entries(p.places.byLad).filter(([,v])=>v.lastmile&&Number.isFinite(v.lastmile.gigabit_pct));
  const mine=p.places.byLad['E07000032'].lastmile.gigabit_pct;
  const above=all.filter(([,v])=>v.lastmile.gigabit_pct>mine).length;
  console.log('module', r.rank, 'of', r.of, '| recomputed', above+1, 'of', all.length);
});"
```
Expected: the two agree exactly.

- [ ] **Step 8: Run the gates and commit**

```bash
npm test && python3 tools/seo-check.py && node tools/contrast-check.mjs
git add app/assets/lib/rank.js app/assets/lib/entry.js app/assets/shell.js app/assets/app.css tests/js/rank.test.js
git commit -m "Say where a district sits among the others, and against how many"
```

---

### Task 5: Place Junction

`gold.junction_register` holds 4 rows about the operators' publishing behaviour. The connection rows are on disk and not loaded at all.

**Files:**
- Modify: `platform/groundtruth/systems/junction.py`
- Modify: `platform/groundtruth/places.py` (one line in `PLACED`)
- Modify: `app/assets/lib/answers.js`
- Test: `platform/tests/test_junction_place.py` (create)

**Interfaces:**
- Consumes: `platform/data/bronze/dno_ecr_{ukpn,npg,enwl,spen}.csv`, semicolon delimited, carrying `postcode`, `town_city`, `county`, `location_x_coordinate_eastings_where_data_is_held`, `location_y_coordinate_northings_where_data_is_held`, `longitude`, `latitude`, `connection_status`, `already_connected_registered_capacity_mw`, `accepted_to_connect_registered_capacity_mw`, `licence_area`.
- Produces: `silver.junction_connection` and `gold.junction_district(lad_code, connections, connected_mw, accepted_mw, placed_pct)`.

- [ ] **Step 1: Write the failing test**

Create `platform/tests/test_junction_place.py`:

```python
import duckdb
import pytest

from groundtruth.systems import junction as J


@pytest.fixture
def con():
    con = duckdb.connect(":memory:")
    con.execute("CREATE SCHEMA silver; CREATE SCHEMA gold")
    con.execute("""CREATE TABLE silver.place_postcode
                   (postcode_key VARCHAR, postcode VARCHAR, positional_quality INTEGER,
                    easting INTEGER, northing INTEGER, lad_code VARCHAR,
                    ward_code VARCHAR, country_code VARCHAR)""")
    con.executemany("INSERT INTO silver.place_postcode VALUES (?,?,?,?,?,?,?,?)", [
        ("SW1A1AA", "SW1A 1AA", 10, 530047, 179951, "E09000033", "W1", "E92000001"),
    ])
    con.execute("""CREATE TABLE silver.junction_connection
                   (operator VARCHAR, postcode VARCHAR, easting INTEGER, northing INTEGER,
                    connection_status VARCHAR, connected_mw DOUBLE, accepted_mw DOUBLE)""")
    con.executemany("INSERT INTO silver.junction_connection VALUES (?,?,?,?,?,?,?)", [
        ("UKPN", "SW1A 1AA", None, None, "Connected", 2.5, 0.0),
        ("UKPN", "SW1A 1AA", None, None, "Accepted to connect", 0.0, 1.5),
        # no postcode, but a grid reference near the one centroid above
        ("UKPN", None, 530050, 179955, "Connected", 1.0, 0.0),
        # neither, so it cannot be placed and must be counted as unplaced
        ("UKPN", None, None, None, "Connected", 9.9, 0.0),
    ])
    return con


def test_a_postcode_places_a_connection(con):
    J.by_district(con)
    row = con.execute("SELECT connections, connected_mw, accepted_mw "
                      "FROM gold.junction_district WHERE lad_code = 'E09000033'").fetchone()
    assert row[0] == 3
    assert row[1] == pytest.approx(3.5)
    assert row[2] == pytest.approx(1.5)


def test_a_grid_reference_places_a_connection_with_no_postcode(con):
    J.by_district(con)
    n = con.execute("SELECT connections FROM gold.junction_district "
                    "WHERE lad_code = 'E09000033'").fetchone()[0]
    assert n == 3, "the coordinate-only row should be placed by its nearest centroid"


def test_a_row_with_no_location_is_reported_not_dropped_silently(con):
    J.by_district(con)
    pct = con.execute("SELECT placed_pct FROM gold.junction_district "
                      "WHERE lad_code = 'E09000033'").fetchone()[0]
    assert pct == 75.0, "3 of 4 rows placed, and the page must be able to say so"


def test_no_district_row_is_created_for_an_unplaceable_row(con):
    J.by_district(con)
    codes = [r[0] for r in con.execute("SELECT lad_code FROM gold.junction_district").fetchall()]
    assert codes == ["E09000033"]
    assert None not in codes
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd platform && .venv/bin/python -m pytest tests/test_junction_place.py -v`
Expected: FAIL, `AttributeError: module 'groundtruth.systems.junction' has no attribute 'by_district'`.

- [ ] **Step 3: Write the loader and the aggregate**

In `platform/groundtruth/systems/junction.py`, add:

```python
from ..place import resolve_coordinate, resolve_postcode

# The four registers are published separately, with the same columns under the
# same names but semicolon delimited. Loaded into one silver table so the
# question is asked once, of every operator, rather than four times.
_ECR = {
    "UKPN": "dno_ecr_ukpn.csv",
    "NPG": "dno_ecr_npg.csv",
    "ENWL": "dno_ecr_enwl.csv",
    "SPEN": "dno_ecr_spen.csv",
}


def load_connections(con, bronze) -> int:
    """Every operator's capacity register, as one table."""
    con.execute("DROP TABLE IF EXISTS silver.junction_connection")
    con.execute("""CREATE TABLE silver.junction_connection
                   (operator VARCHAR, postcode VARCHAR, easting INTEGER, northing INTEGER,
                    connection_status VARCHAR, connected_mw DOUBLE, accepted_mw DOUBLE)""")
    loaded = 0
    for operator, filename in _ECR.items():
        path = bronze / filename
        if not path.exists():
            continue
        con.execute("""
            INSERT INTO silver.junction_connection
            SELECT ?,
                   nullif(trim(postcode), ''),
                   try_cast(location_x_coordinate_eastings_where_data_is_held AS INTEGER),
                   try_cast(location_y_coordinate_northings_where_data_is_held AS INTEGER),
                   connection_status,
                   coalesce(try_cast(already_connected_registered_capacity_mw AS DOUBLE), 0),
                   coalesce(try_cast(accepted_to_connect_registered_capacity_mw AS DOUBLE), 0)
            FROM read_csv(?, delim=';', header=true, all_varchar=true,
                          ignore_errors=true)
        """, [operator, str(path)])
        loaded = con.execute("SELECT count(*) FROM silver.junction_connection").fetchone()[0]
    return loaded


def by_district(con) -> None:
    """Connections and capacity per district, with how many rows were placeable.

    A register row carries a postcode, a grid reference, both, or neither. The
    postcode is preferred because it is the publisher's own statement of where
    the connection is; the grid reference is the fallback, through the same
    nearest-centroid tier every other coordinate-placed figure uses. A row with
    neither is not dropped quietly: placed_pct says what share of the rows
    behind a district's figure could be located at all.
    """
    rows = con.execute("""
        SELECT postcode, easting, northing, connected_mw, accepted_mw
        FROM silver.junction_connection
    """).fetchall()

    agg: dict[str, list] = {}
    placed = unplaced = 0
    for postcode, easting, northing, connected, accepted in rows:
        ref = resolve_postcode(con, postcode) if postcode else None
        if ref is None or ref.lad_code is None:
            ref = resolve_coordinate(con, easting, northing)
        if ref.lad_code is None:
            unplaced += 1
            continue
        placed += 1
        a = agg.setdefault(ref.lad_code, [0, 0.0, 0.0])
        a[0] += 1
        a[1] += connected or 0.0
        a[2] += accepted or 0.0

    total = placed + unplaced
    pct = round(100 * placed / total, 1) if total else 0.0

    con.execute("DROP TABLE IF EXISTS gold.junction_district")
    con.execute("""CREATE TABLE gold.junction_district
                   (lad_code VARCHAR, connections INTEGER,
                    connected_mw DOUBLE, accepted_mw DOUBLE, placed_pct DOUBLE)""")
    if agg:
        con.executemany(
            "INSERT INTO gold.junction_district VALUES (?, ?, ?, ?, ?)",
            [(c, v[0], round(v[1], 2), round(v[2], 2), pct) for c, v in agg.items()])
```

Then call `load_connections` and `by_district` from wherever this module's other build steps are invoked; read `platform/groundtruth/run.py` and follow the existing call order rather than inventing one.

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd platform && .venv/bin/python -m pytest tests/test_junction_place.py -v`
Expected: 4 passed.

- [ ] **Step 5: Wire it into the payload**

In `platform/groundtruth/places.py`, add to `PLACED`:

```python
    "junction": "lad_code",
```

- [ ] **Step 6: Teach the app the block**

In `app/assets/lib/answers.js`, add to `QUESTIONS`:

```javascript
  {
    id: 'junction',
    name: 'Junction',
    question: 'How much generation and storage capacity is connected to the grid here, and how much more is accepted but not yet built?',
    unit: ' MW',
    figure: p => p.connected_mw,
    against: p => p.accepted_mw,
    againstLabel: 'accepted to connect but not yet connected',
    caveat: p => `Across ${n(p.connections)} connection${p.connections === 1 ? '' : 's'} in the `
      + `distribution operators' own capacity registers, of which ${p.placed_pct}% of all register `
      + `rows could be located at all. The connection is where the equipment is, not who the power `
      + `serves.`,
  },
```

- [ ] **Step 7: Run every gate and commit**

```bash
cd platform && .venv/bin/python -m pytest && cd ..
npm test && python3 tools/seo-check.py && node tools/contrast-check.mjs
git add platform/groundtruth/systems/junction.py platform/groundtruth/places.py platform/tests/test_junction_place.py app/assets/lib/answers.js
git commit -m "Load the capacity registers and place their connections by district"
```

---

### Task 6: Place Sentinel

`silver.procurement_award` drops the postcode the raw file carries.

**Files:**
- Modify: `platform/groundtruth/systems/sentinel.py`
- Modify: `platform/groundtruth/places.py` (one line in `PLACED`)
- Modify: `app/assets/lib/answers.js`
- Test: `platform/tests/test_sentinel_place.py` (create)

**Interfaces:**
- Consumes: `platform/data/bronze/contracts_finder_bulk.json`, where each release carries `parties[]` with `roles` including `buyer` and `address.postalCode`, and optionally `tender.items[].deliveryAddresses[].postalCode`.
- Produces: `silver.procurement_award` gaining `buyer_postcode` and `delivery_postcode`, and `gold.sentinel_district(lad_code, awards, total_value, closed_awards, closed_pct, placed_pct)`.

- [ ] **Step 1: Write the failing test**

Create `platform/tests/test_sentinel_place.py`:

```python
import duckdb
import pytest

from groundtruth.systems import sentinel as S


@pytest.fixture
def con():
    con = duckdb.connect(":memory:")
    con.execute("CREATE SCHEMA silver; CREATE SCHEMA gold")
    con.execute("""CREATE TABLE silver.place_postcode
                   (postcode_key VARCHAR, postcode VARCHAR, positional_quality INTEGER,
                    easting INTEGER, northing INTEGER, lad_code VARCHAR,
                    ward_code VARCHAR, country_code VARCHAR)""")
    con.executemany("INSERT INTO silver.place_postcode VALUES (?,?,?,?,?,?,?,?)", [
        ("LN57JH", "LN5 7JH", 10, 0, 0, "E07000138", "W1", "E92000001"),
        ("SW1A1AA", "SW1A 1AA", 10, 0, 0, "E09000033", "W2", "E92000001"),
    ])
    con.execute("""CREATE TABLE silver.procurement_award
                   (ocid VARCHAR, buyer VARCHAR, method VARCHAR, value DOUBLE,
                    buyer_postcode VARCHAR, delivery_postcode VARCHAR)""")
    con.executemany("INSERT INTO silver.procurement_award VALUES (?,?,?,?,?,?)", [
        ("a", "Trust", "open", 100.0, "LN5 7JH", None),
        # delivery wins over buyer: the work happens in Westminster
        ("b", "Trust", "limited", 200.0, "LN5 7JH", "SW1A 1AA"),
        ("c", "Trust", "open", 300.0, None, None),
    ])
    return con


def test_an_award_is_placed_by_its_buyer_postcode(con):
    S.by_district(con)
    row = con.execute("SELECT awards, total_value FROM gold.sentinel_district "
                      "WHERE lad_code = 'E07000138'").fetchone()
    assert row == (1, 100.0)


def test_a_delivery_address_beats_the_buyer_address(con):
    S.by_district(con)
    row = con.execute("SELECT awards, total_value FROM gold.sentinel_district "
                      "WHERE lad_code = 'E09000033'").fetchone()
    assert row == (1, 200.0)


def test_the_closed_share_is_counted_per_district(con):
    S.by_district(con)
    closed = con.execute("SELECT closed_awards, closed_pct FROM gold.sentinel_district "
                         "WHERE lad_code = 'E09000033'").fetchone()
    assert closed == (1, 100.0)


def test_the_placed_share_is_published_so_the_count_can_be_judged(con):
    S.by_district(con)
    pct = con.execute("SELECT DISTINCT placed_pct FROM gold.sentinel_district").fetchone()[0]
    assert pct == pytest.approx(66.7, abs=0.1)
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd platform && .venv/bin/python -m pytest tests/test_sentinel_place.py -v`
Expected: FAIL, no attribute `by_district`.

- [ ] **Step 3: Keep the postcodes, then aggregate**

In `platform/groundtruth/systems/sentinel.py`, widen the `silver.procurement_award` creation to carry two more columns, reading the buyer's own address and the delivery address out of the release:

```python
def _postcodes(release: dict) -> tuple[str | None, str | None]:
    """The buyer's address and where the work is delivered, if either is given.

    Delivery is the better answer to "where is this happening" and is preferred
    downstream; the buyer address is the fallback, and is a registered office as
    often as it is a place of work. Both are published so the weaker one can be
    argued with rather than silently relied on.
    """
    buyer = None
    for party in release.get("parties") or []:
        if "buyer" in (party.get("roles") or []):
            buyer = ((party.get("address") or {}).get("postalCode") or "").strip() or None
            break
    delivery = None
    for item in ((release.get("tender") or {}).get("items") or []):
        for addr in item.get("deliveryAddresses") or []:
            got = (addr.get("postalCode") or "").strip()
            if got:
                delivery = got
                break
        if delivery:
            break
    return buyer, delivery
```

Add `buyer_postcode VARCHAR, delivery_postcode VARCHAR` to the table definition and pass both values through the insert, using `_postcodes(release)`. Then add:

```python
# A method that did not go to open competition. The same predicate the national
# figure already uses; kept in one place so the district figure and the national
# one cannot disagree about what "closed" means.
_CLOSED = ("limited", "direct", "negotiated")


def by_district(con) -> None:
    """Awards and value per district, and how many skipped open competition.

    Placed by the delivery address where the notice gives one, and by the
    buyer's address otherwise. Both are weak: a buyer address is frequently a
    head office. placed_pct is published beside the figures so a reader can see
    how much of the corpus reached a district at all, and the corpus is small,
    about six awards per district.
    """
    from ..place import resolve_postcode

    rows = con.execute("""
        SELECT method, value, buyer_postcode, delivery_postcode
        FROM silver.procurement_award
    """).fetchall()

    agg: dict[str, list] = {}
    placed = unplaced = 0
    for method, value, buyer_pc, delivery_pc in rows:
        code = None
        for pc in (delivery_pc, buyer_pc):
            if not pc:
                continue
            ref = resolve_postcode(con, pc)
            if ref.lad_code:
                code = ref.lad_code
                break
        if code is None:
            unplaced += 1
            continue
        placed += 1
        a = agg.setdefault(code, [0, 0.0, 0])
        a[0] += 1
        a[1] += value or 0.0
        if str(method or "").lower() in _CLOSED:
            a[2] += 1

    total = placed + unplaced
    pct = round(100 * placed / total, 1) if total else 0.0

    con.execute("DROP TABLE IF EXISTS gold.sentinel_district")
    con.execute("""CREATE TABLE gold.sentinel_district
                   (lad_code VARCHAR, awards INTEGER, total_value DOUBLE,
                    closed_awards INTEGER, closed_pct DOUBLE, placed_pct DOUBLE)""")
    if agg:
        con.executemany(
            "INSERT INTO gold.sentinel_district VALUES (?, ?, ?, ?, ?, ?)",
            [(c, v[0], round(v[1], 2), v[2],
              round(100 * v[2] / v[0], 1) if v[0] else 0.0, pct)
             for c, v in agg.items()])
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd platform && .venv/bin/python -m pytest tests/test_sentinel_place.py -v`
Expected: 4 passed.

- [ ] **Step 5: Wire it into the payload**

In `platform/groundtruth/places.py`, add to `PLACED`:

```python
    "sentinel": "lad_code",
```

- [ ] **Step 6: Teach the app the block**

In `app/assets/lib/answers.js`, add to `QUESTIONS`:

```javascript
  {
    id: 'sentinel',
    name: 'Sentinel',
    question: 'What share of public contracts awarded here skipped open competition?',
    unit: '%',
    figure: p => p.closed_pct,
    against: (p, s) => s.sentinel && s.sentinel.national && s.sentinel.national.closed_pct,
    againstLabel: 'the national share',
    caveat: p => `Over ${n(p.awards)} award${p.awards === 1 ? '' : 's'} placed in this district, a `
      + `small base: ${p.placed_pct}% of the whole corpus could be located, and the corpus itself `
      + `is a sample rather than every award. A notice is placed by where the work is delivered `
      + `where it says, and by the buyer's own address otherwise, which is often a head office.`,
  },
```

If `systems.sentinel.national.closed_pct` does not exist in the payload, drop the `against` and `againstLabel` keys rather than inventing a comparator. Check first:

```bash
python3 -c "import json;p=json.load(open('app/data/platform.json'));print(json.dumps(p['systems'].get('sentinel'))[:400])"
```

- [ ] **Step 7: Run every gate and commit**

```bash
cd platform && .venv/bin/python -m pytest && cd ..
npm test && python3 tools/seo-check.py && node tools/contrast-check.mjs
git add platform/groundtruth/systems/sentinel.py platform/groundtruth/places.py platform/tests/test_sentinel_place.py app/assets/lib/answers.js
git commit -m "Keep the procurement postcodes the loader dropped, and place the awards"
```

---

### Task 7: Region and combined authority pages

The last task, because a whole-area figure is only worth showing once the questions behind it are placed.

**Files:**
- Modify: `platform/groundtruth/sources.py`, `platform/groundtruth/publish.py`
- Create: `platform/groundtruth/areas.py`
- Create: `app/assets/lib/areas.js`
- Modify: `app/assets/lib/entry.js`, `app/assets/lib/routes.js`, `app/assets/shell.js`, `app/index.html`, `app/assets/app.css`
- Test: `platform/tests/test_areas.py` (create), `tests/js/areas.test.js` (create)

**Interfaces:**
- Consumes: two ONS lookups registered in `sources.py`, district to region and district to combined authority, both from the ONS Open Geography Portal, both open and both small.
- Produces: `payload.areas`, shaped
  `{"E12000007": {"name": "London", "kind": "region", "districts": ["E09000001", ...]}}`,
  and a route `#/areas/<code>`.

- [ ] **Step 1: Register the two lookups**

In `platform/groundtruth/sources.py`, add two entries beside the existing `ons_lad_county` one, following its exact shape, for the district-to-region and district-to-combined-authority lookups. Fetch them and confirm both return 200 and parse:

```bash
cd platform && .venv/bin/python -m groundtruth.cli fetch --only ons_lad_region ons_lad_cauth
```

Use whatever the CLI's real fetch subcommand is; read `platform/groundtruth/cli.py` first.

- [ ] **Step 2: Write the failing test for area membership**

Create `platform/tests/test_areas.py`:

```python
import duckdb
import pytest

from groundtruth import areas as A


@pytest.fixture
def con():
    con = duckdb.connect(":memory:")
    con.execute("CREATE SCHEMA silver; CREATE SCHEMA gold")
    con.execute("CREATE TABLE silver.lad (lad_code VARCHAR, lad_name VARCHAR)")
    con.executemany("INSERT INTO silver.lad VALUES (?, ?)", [
        ("E09000007", "Camden"), ("E09000033", "Westminster"), ("E08000003", "Manchester"),
    ])
    con.execute("CREATE TABLE silver.lad_area (lad_code VARCHAR, area_code VARCHAR, "
                "area_name VARCHAR, kind VARCHAR)")
    con.executemany("INSERT INTO silver.lad_area VALUES (?, ?, ?, ?)", [
        ("E09000007", "E12000007", "London", "region"),
        ("E09000033", "E12000007", "London", "region"),
        ("E08000003", "E12000002", "North West", "region"),
        ("E08000003", "E47000001", "Greater Manchester", "combined authority"),
    ])
    return con


def test_an_area_lists_its_districts(con):
    out = A.build(con)
    assert out["E12000007"]["name"] == "London"
    assert out["E12000007"]["districts"] == ["E09000007", "E09000033"]


def test_a_district_may_belong_to_a_region_and_a_combined_authority(con):
    out = A.build(con)
    assert "E08000003" in out["E12000002"]["districts"]
    assert "E08000003" in out["E47000001"]["districts"]


def test_the_kind_is_carried_so_a_page_can_say_what_it_is_showing(con):
    out = A.build(con)
    assert out["E47000001"]["kind"] == "combined authority"


def test_an_area_with_no_districts_is_not_published(con):
    con.execute("INSERT INTO silver.lad_area VALUES ('E99999999', 'E12000099', 'Nowhere', 'region')")
    out = A.build(con)
    # its only district is not in silver.lad, so the area has nothing to show
    assert "E12000099" not in out
```

- [ ] **Step 3: Run it to verify it fails, then write `areas.py`**

Run: `cd platform && .venv/bin/python -m pytest tests/test_areas.py -v`
Expected: FAIL, no module `groundtruth.areas`.

Write `platform/groundtruth/areas.py` so the four tests pass. It reads `silver.lad_area`, keeps only districts present in `silver.lad`, sorts each district list, and drops any area left with none.

- [ ] **Step 4: Publish it**

In `publish.py`, add `out["areas"] = A.build(con)` beside the existing `out["places"]`.

- [ ] **Step 5: Write the failing test for the app side**

Create `tests/js/areas.test.js` covering: `matchAreas(query, areas)` puts an exact area name first, an area outranks a district whose name merely contains the query, and an unknown query returns nothing. Write the tests before the module, run them, watch them fail.

- [ ] **Step 6: Write `app/assets/lib/areas.js` and add the route**

Add `areas` to `ROUTER_HEADS` in `app/assets/lib/routes.js` in the same commit as the `route()` branch that handles it, never before. Add the view container to `app/index.html` and `buildAreaPage(code)` to `shell.js`.

The page shows the area's name and kind, its districts as a list linking to each place page, and for each question a whole-area figure. **A percentage across districts is a weighted mean, and the page says which quantity weighted it.** A question that cannot be honestly combined says so instead of showing a number.

- [ ] **Step 7: Verify the search**

`London`, `Greater Manchester` and `West Midlands` each reach an area page. `Camden` still reaches its district page. `City of London` still reaches its own district page and is not shadowed by London.

- [ ] **Step 8: Run every gate and commit**

```bash
cd platform && .venv/bin/python -m pytest && cd ..
npm test && python3 tools/seo-check.py && node tools/contrast-check.mjs
git add -A platform app tests
git commit -m "Give a region and a combined authority a page, so London finds something"
```

---

## Final verification, after all seven tasks

- [ ] Rebuild the payload and the static pages: `node build.js`
- [ ] All four gates clean: pytest, `npm test`, `tools/seo-check.py`, `tools/contrast-check.mjs`
- [ ] Measure the payload: `ls -l app/data/platform.json`. If it is over 1.2 MB, stop and report, as the spec's risk section requires.
- [ ] In the browser at 375 and 1440, both themes: `#/`, `#/places/E07000032`, `#/places/E09000001`, `#/areas/E12000007`, `#/compare`, `#/unusual`, `#/about`, `#/questions`. One visible `h1` each, no horizontal overflow, no console errors.
- [ ] Every campaign URL resolves: `#/places/E07000032`, `#/systems/plumbline`, `#/places`, `#/method`, `#/sources`.
- [ ] `grep -rn "—" app/` returns nothing.
- [ ] A district with no Baseline, Junction or Sentinel row renders its absence sentence, and that sentence is true for that district.
- [ ] Count the answers on City of London. It was 4 of 13. Report the new number.
