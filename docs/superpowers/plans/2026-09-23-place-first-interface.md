# Place-first interface Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the UK GroundTruth app from an operations console into a place-first public interface: one action on the front page, three doors behind it, and a place page that reads as a document.

**Architecture:** The app is a hash-routed single-page app made of classic browser scripts that assign globals (`app/assets/*.js`), reading one payload (`app/data/platform.json`). New pure logic goes into ES modules under `app/assets/lib/`, which Node's built-in test runner imports directly and a single module entry exposes to the classic scripts as `window.GT_LIB`. No framework, no build step for the app, no change to the payload or the engine.

**Tech Stack:** Vanilla ES2022, classic scripts plus one module entry, `node --test` (Node 26, already installed), Python 3 for `tools/seo-check.py`, GitHub Pages for publishing.

## Global Constraints

- No em dash or en dash in any shipped string, in either the literal or `&mdash;` entity form. Replace with the punctuation the sentence needs.
- The thirteen are questions the connected record answers, never "systems". Real-world systems (the planning system, the statutory consultee system, the electricity system operator) keep the word.
- Campaign URLs must keep resolving: `#/places/E07000032`, `#/systems/plumbline`, `#/places`, `#/method`, `#/sources`. They are in 150 outreach emails.
- Do not regress the audit fixes: one router-driven `h1` per document with view titles as `h2`; the drawer leaves the tab order when closed and its button carries `aria-expanded`; 44px minimum interactive targets and 16px form text; the payload revalidated (`cache: 'no-cache'`, no cache-busting query); district boundaries fetched once per page; both themes above WCAG AA contrast.
- `python3 tools/seo-check.py` must exit 0 before any commit that touches `app/index.html` or the generated pages.
- Identity is fixed: navy, UK blue, IBM Plex Sans and Mono. The register changes, the palette and faces do not.
- Never edit generated files directly. `index.html` (root), `systems/*.html`, `platform.html`, `research.html`, `examples.html`, `about.html`, `404.html`, `sitemap.xml` and `robots.txt` are written by `node build.js` from `data/*.js` and `build.js`. `app/index.html` is hand-written but has figures injected into it by `tools/app-content.mjs` at the end of `node build.js`.

---

### Task 1: Test harness and route aliasing

Adds the JavaScript test cycle the repo does not have yet, and makes every old URL resolve to the new structure.

**Files:**
- Create: `app/assets/lib/routes.js`
- Create: `app/assets/lib/entry.js`
- Create: `tests/js/routes.test.js`
- Modify: `package.json` (scripts)
- Modify: `app/index.html` (one script tag)
- Modify: `app/assets/shell.js` (route aliasing)

**Interfaces:**
- Consumes: nothing.
- Produces: `canonicalHash(raw: string) => string | null` from `app/assets/lib/routes.js`, returning the hash a raw hash should be replaced with, or `null` when it is already canonical. `window.GT_LIB` object created by `app/assets/lib/entry.js`.

- [ ] **Step 1: Write the failing test**

Create `tests/js/routes.test.js`:

```js
import test from 'node:test';
import assert from 'node:assert/strict';
import { canonicalHash } from '../../app/assets/lib/routes.js';

test('canonical routes are left alone', () => {
  for (const hash of ['#/', '#/places', '#/places/E07000032', '#/compare', '#/unusual', '#/about']) {
    assert.equal(canonicalHash(hash), null, `${hash} should already be canonical`);
  }
});

test('a question keeps its place when the section is renamed', () => {
  // 150 outreach emails link to #/systems/plumbline. It must land on the question.
  assert.equal(canonicalHash('#/systems/plumbline'), '#/questions/plumbline');
  assert.equal(canonicalHash('#/systems/plumbline/sources'), '#/questions/plumbline/sources');
});

test('retired sections point at their replacement', () => {
  assert.equal(canonicalHash('#/systems'), '#/');
  assert.equal(canonicalHash('#/sources'), '#/about');
  assert.equal(canonicalHash('#/method'), '#/about');
});

test('the older anchor links still work', () => {
  assert.equal(canonicalHash('#place'), '#/places');
  assert.equal(canonicalHash('#system/plumbline'), '#/questions/plumbline');
  assert.equal(canonicalHash('#org/12345678'), '#/orgs/12345678');
});

test('an empty or unknown hash is canonical', () => {
  assert.equal(canonicalHash(''), null);
  assert.equal(canonicalHash('#/nonsense'), null);
});
```

- [ ] **Step 2: Run it and watch it fail**

Run: `node --test tests/js/routes.test.js`
Expected: FAIL, `Cannot find module` for `app/assets/lib/routes.js`.

- [ ] **Step 3: Write the module**

Create `app/assets/lib/routes.js`:

```js
/* Every hash the app has ever published, mapped to the one it means now.
   The outreach campaign links to #/systems/<id> from 150 emails, so that route
   cannot simply stop existing: it resolves to the question it always meant. */

const SECTION = {
  '#/systems': '#/',
  '#/sources': '#/about',
  '#/method': '#/about',
};

const ANCHOR = {
  '#top': '#/about', '#hero': '#/about', '#spines': '#/about', '#chains': '#/about',
  '#place': '#/places', '#systems': '#/', '#compare': '#/compare',
  '#feeds': '#/about', '#honesty': '#/about', '#kpis': '#/',
  '#org': '#/orgs', '#search': '#/search',
};

export function canonicalHash(raw) {
  const hash = String(raw || '').trim();
  if (!hash || hash === '#' || hash === '#/') return null;

  if (Object.prototype.hasOwnProperty.call(ANCHOR, hash)) return ANCHOR[hash];
  if (Object.prototype.hasOwnProperty.call(SECTION, hash)) return SECTION[hash];

  const renamed = hash.match(/^#\/systems\/(.+)$/);
  if (renamed) return `#/questions/${renamed[1]}`;

  const legacySystem = hash.match(/^#system\/([a-z0-9_-]+)$/i);
  if (legacySystem) return `#/questions/${legacySystem[1]}`;

  const legacyOrg = hash.match(/^#org\/(.+)$/);
  if (legacyOrg) return `#/orgs/${legacyOrg[1]}`;

  return null;
}
```

- [ ] **Step 4: Run the test again**

Run: `node --test tests/js/routes.test.js`
Expected: PASS, 5 tests.

- [ ] **Step 5: Add the test script**

Modify `package.json`, replacing the `scripts` block:

```json
  "scripts": {
    "build": "node build.js",
    "test": "node --test tests/js/"
  },
```

Run: `npm test`
Expected: PASS, 5 tests.

- [ ] **Step 6: Expose the module to the classic scripts**

Create `app/assets/lib/entry.js`:

```js
/* The app is built from classic scripts that assign globals. The pure logic
   lives in modules so the test runner can import it directly, and this entry is
   the one bridge between the two: it runs deferred, before DOMContentLoaded, so
   the router finds it by the time any route is handled. */
import { canonicalHash } from './routes.js';

window.GT_LIB = Object.assign(window.GT_LIB || {}, { canonicalHash });
```

Modify `app/index.html`. Find the first classic script tag (`<script src="assets/shared.js"></script>`) and insert immediately above it:

```html
<script type="module" src="assets/lib/entry.js"></script>
```

- [ ] **Step 7: Use it in the router**

Modify `app/assets/shell.js`. Replace the opening of `route()`, which currently reads:

```js
  function route() {
    const raw = location.hash || '#/';
    const L = legacy();
    if (L[raw]) { location.replace(L[raw]); return; }
    const legacySys = raw.match(/^#system\/([a-z0-9_-]+)$/i);
    if (legacySys) { location.replace('#/systems/' + legacySys[1]); return; }
    const legacyOrg = raw.match(/^#org\/(.+)$/);
    if (legacyOrg) { location.replace('#/orgs/' + legacyOrg[1]); return; }
```

with:

```js
  function route() {
    const raw = location.hash || '#/';
    // One table of every hash the app has published, tested in tests/js/routes.test.js.
    const canonical = (window.GT_LIB && window.GT_LIB.canonicalHash)
      ? window.GT_LIB.canonicalHash(raw) : null;
    if (canonical) { location.replace(canonical); return; }
```

- [ ] **Step 8: Verify the campaign URLs in a browser**

Run: `python3 -m http.server 8765 --directory app` in one terminal.
Visit each of these and confirm the view renders and the console is clean:
`http://localhost:8765/#/places/E07000032`, `#/systems/plumbline`, `#/places`, `#/method`, `#/sources`.
Expected: the first two render, `#/method` and `#/sources` land on `#/about` once Task 7 exists, and until then on the method and sources views they already have. Note which in the commit message.

- [ ] **Step 9: Commit**

```bash
git add package.json app/assets/lib/routes.js app/assets/lib/entry.js tests/js/routes.test.js app/index.html app/assets/shell.js
git commit -m "Route every published hash through one tested table"
```

---

### Task 2: Place matching for the front page field

The front page asks for a council or district name. This is the matcher behind it.

**Files:**
- Create: `app/assets/lib/places.js`
- Create: `tests/js/places.test.js`
- Modify: `app/assets/lib/entry.js`

**Interfaces:**
- Consumes: `canonicalHash` exists; nothing else.
- Produces: `matchPlaces(query: string, names: Record<string,string>, limit = 8) => Array<{code: string, name: string}>`, ranked: exact match first, then names starting with the query, then names containing it, each group alphabetical. `looksLikePostcode(query: string) => boolean`.

- [ ] **Step 1: Write the failing test**

Create `tests/js/places.test.js`:

```js
import test from 'node:test';
import assert from 'node:assert/strict';
import { matchPlaces, looksLikePostcode } from '../../app/assets/lib/places.js';

const NAMES = {
  E07000032: 'Amber Valley',
  E06000001: 'Hartlepool',
  E09000007: 'Camden',
  E07000223: 'Adur',
  E08000003: 'Manchester',
  E07000117: 'Burnley',
};

test('an exact name comes first', () => {
  const hits = matchPlaces('Camden', NAMES);
  assert.equal(hits[0].code, 'E09000007');
  assert.equal(hits[0].name, 'Camden');
});

test('a prefix beats a substring', () => {
  const hits = matchPlaces('man', NAMES).map(h => h.name);
  assert.equal(hits[0], 'Manchester');           // starts with
  assert.ok(hits.length >= 1);
});

test('matching ignores case and surrounding space', () => {
  assert.equal(matchPlaces('  aMbEr  ', NAMES)[0].name, 'Amber Valley');
});

test('no query returns nothing, rather than everything', () => {
  assert.deepEqual(matchPlaces('', NAMES), []);
  assert.deepEqual(matchPlaces('   ', NAMES), []);
});

test('an unknown place returns nothing', () => {
  assert.deepEqual(matchPlaces('Atlantis', NAMES), []);
});

test('the limit is honoured', () => {
  assert.equal(matchPlaces('a', NAMES, 2).length, 2);
});

test('a postcode is recognised so the field can say what it needs', () => {
  for (const pc of ['DE5 3TZ', 'de53tz', 'SW1A 1AA', 'M1 1AE']) {
    assert.equal(looksLikePostcode(pc), true, `${pc} should look like a postcode`);
  }
  for (const not of ['Camden', 'Amber Valley', '', 'E07000032']) {
    assert.equal(looksLikePostcode(not), false, `${not} should not`);
  }
});
```

- [ ] **Step 2: Run it and watch it fail**

Run: `node --test tests/js/places.test.js`
Expected: FAIL, `Cannot find module`.

- [ ] **Step 3: Write the module**

Create `app/assets/lib/places.js`:

```js
/* The front page takes a council or district name. The payload ships
   places.names, 318 of them, which is the whole index this needs.

   Postcodes are deliberately not resolved here: the payload carries counts
   about the postcode spine, not a lookup, and a full index is far too large to
   ship. The field recognises one so it can say so plainly. */

const POSTCODE = /^[A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2}$/i;

export function looksLikePostcode(query) {
  return POSTCODE.test(String(query || '').trim());
}

export function matchPlaces(query, names, limit = 8) {
  const q = String(query || '').trim().toLowerCase();
  if (!q) return [];

  const exact = [], starts = [], contains = [];
  for (const [code, name] of Object.entries(names || {})) {
    const n = String(name).toLowerCase();
    if (n === q) exact.push({ code, name });
    else if (n.startsWith(q)) starts.push({ code, name });
    else if (n.includes(q)) contains.push({ code, name });
  }
  const byName = (a, b) => a.name.localeCompare(b.name, 'en-GB');
  return [...exact.sort(byName), ...starts.sort(byName), ...contains.sort(byName)].slice(0, limit);
}
```

- [ ] **Step 4: Run the test again**

Run: `node --test tests/js/places.test.js`
Expected: PASS, 7 tests.

- [ ] **Step 5: Expose it**

Modify `app/assets/lib/entry.js`:

```js
import { canonicalHash } from './routes.js';
import { matchPlaces, looksLikePostcode } from './places.js';

window.GT_LIB = Object.assign(window.GT_LIB || {}, { canonicalHash, matchPlaces, looksLikePostcode });
```

- [ ] **Step 6: Commit**

```bash
git add app/assets/lib/places.js app/assets/lib/entry.js tests/js/places.test.js
git commit -m "Match a typed place name against the 318 the payload ships"
```

---

### Task 3: The front page

One action, three doors, the thirteen listed quietly underneath. No sidebar.

**Files:**
- Modify: `app/index.html` (new `home` view, header, sidebar removal)
- Modify: `app/assets/shell.js` (`VIEWS_PUBLIC`, `TITLES_PUBLIC`, `DOCS`, route branch, nav)
- Modify: `app/assets/app.css` (hero, doors, question list)

**Interfaces:**
- Consumes: `window.GT_LIB.matchPlaces`, `window.GT_LIB.looksLikePostcode`, `Platform.placeList()`, the payload's `places.names`.
- Produces: a view registered as `home`, rendered by `buildHome()` in `shell.js`.

- [ ] **Step 1: Expose the payload**

The new modules take the whole payload, and `Platform` has no accessor for it.
Modify `app/assets/platform.js`. Add this line beside the other one-line
accessors, directly under `const pipeline = () => (data && data.pipeline) || null;`:

```js
  // The lib modules under assets/lib take the whole payload, so it needs a door.
  const payload = () => data;
```

Then add `payload` to the returned object on the `return {load, sys, has, pipeline, ...` line,
immediately after `load`:

```js
  return {load, payload, sys, has, pipeline, organisations, headlines, systemResult, sourceSummary, spineSummary,
```

Run: `node --check app/assets/platform.js`
Expected: no output.

- [ ] **Step 2: Add the view markup**

Modify `app/index.html`. Immediately after `<main class="pad" id="top">`, insert:

```html
  <div class="view" data-view="home" id="viewHome" hidden>
    <section class="find">
      <h2 class="find__h">What does the public record say about your area?</h2>
      <p class="find__s">Type a council or district name. Every figure on the page that follows is
        computed from a published government file, and says which one.</p>
      <div class="find__box">
        <label class="visually-hidden" for="findPlace">Council or district name</label>
        <input id="findPlace" type="search" autocomplete="off" spellcheck="false"
               placeholder="Amber Valley, Camden, Manchester">
        <div class="find__hits" id="findHits" role="listbox" aria-label="Matching places" hidden></div>
        <p class="find__note" id="findNote" hidden></p>
      </div>
      <div class="find__eg" id="findEg"></div>
      <p class="find__cred">45 sources from 22 publishers. Seventeen corrections published, each with
        what was believed, what was true, and the test that now guards it.</p>
    </section>

    <nav class="doors" aria-label="Other ways in">
      <a class="door" href="#/compare">
        <span class="door__n" id="doorCompare">318</span>
        <span class="door__t">Compare every district</span>
        <span class="door__s">One table, sortable by any figure, exportable.</span>
      </a>
      <a class="door" href="#/unusual">
        <span class="door__n" id="doorUnusual">50</span>
        <span class="door__t">What looks unusual right now</span>
        <span class="door__s">Where a place diverges most from the published figure, with the source.</span>
      </a>
      <a class="door" href="#/about">
        <span class="door__n" id="doorAbout">45</span>
        <span class="door__t">How this is built</span>
        <span class="door__s">The two joins, every source, and what this cannot do.</span>
      </a>
    </nav>

    <section class="qlist">
      <h2 class="qlist__h">The thirteen questions</h2>
      <div id="qlistBody"></div>
    </section>
  </div>
```

- [ ] **Step 3: Register the view and its copy**

Modify `app/assets/shell.js`:

Replace `const VIEWS_PUBLIC = ['overview', 'places', 'systems', 'sources', 'method', 'detail'];` with:

```js
  const VIEWS_PUBLIC = ['home', 'overview', 'places', 'unusual', 'about', 'systems', 'sources', 'method', 'detail'];
```

In `TITLES_PUBLIC`, replace the `''` entry with:

```js
    '':        ['Explore', 'Find your area'],
```

In `DOCS`, replace the `''` entry with:

```js
    '':        ['Find your area', 'Type a council or district name and see what the connected record holds for it: school places, planning speed, flood defences, care ownership and connectivity, each from a published government file.'],
```

- [ ] **Step 4: Render it**

Modify `app/assets/shell.js`. Add this function immediately above `function route() {`:

```js
  /* The front page does one thing. Everything else on it is a signpost. */
  function buildHome() {
    const lib = window.GT_LIB || {};
    const names = (Platform.payload && Platform.payload().places && Platform.payload().places.names) || {};
    const input = $('#findPlace'), hits = $('#findHits'), note = $('#findNote');
    if (!input || !hits) return;

    const go = code => { location.hash = '#/places/' + code; };

    const draw = () => {
      const q = input.value;
      const found = lib.matchPlaces ? lib.matchPlaces(q, names) : [];
      hits.innerHTML = found.map(h =>
        `<button class="find__hit" role="option" data-code="${esc(h.code)}">${esc(h.name)}</button>`).join('');
      hits.hidden = !found.length;
      const postcode = lib.looksLikePostcode && lib.looksLikePostcode(q) && !found.length;
      if (note) {
        note.textContent = postcode
          ? 'Postcodes are not matched yet. Type the council or district name instead.'
          : (q.trim() && !found.length ? 'No district of that name. Try the council that covers it.' : '');
        note.hidden = !note.textContent;
      }
    };

    input.oninput = draw;
    input.onkeydown = e => {
      if (e.key !== 'Enter') return;
      const first = hits.querySelector('.find__hit');
      if (first) go(first.dataset.code);
    };
    hits.onclick = e => {
      const b = e.target.closest('.find__hit');
      if (b) go(b.dataset.code);
    };

    // Three real examples, so the field is obviously usable.
    const eg = $('#findEg');
    if (eg) {
      const examples = [['E07000032', 'Amber Valley'], ['E09000007', 'Camden'], ['E08000003', 'Manchester']]
        .filter(([code]) => names[code]);
      eg.innerHTML = examples.map(([code, name]) =>
        `<a class="chip" href="#/places/${code}">${esc(name)}</a>`).join('');
    }

    const list = $('#qlistBody');
    if (list) {
      list.innerHTML = SYSTEMS.map(s =>
        `<a class="qrow" href="#/questions/${esc(s.id)}">
           <span class="qrow__n">${esc(s.n)}</span>
           <span class="qrow__s">${esc(s.s || '')}</span>
         </a>`).join('');
    }

    const compare = $('#doorCompare');
    if (compare) compare.textContent = num(Object.keys(names).length);
  }
```

- [ ] **Step 5: Route to it**

Modify `app/assets/shell.js`. Replace the empty-head branch in `route()`:

```js
    if (head === '' ) {
      show('overview'); setChrome(''); safely(buildOverview, '#viewOverview'); scrollTop(); return;
    }
```

with:

```js
    if (head === '') {
      show('home'); setChrome(''); safely(buildHome, '#viewHome'); scrollTop(); return;
    }
```

- [ ] **Step 6: Style it**

Modify `app/assets/app.css`. Append:

```css
/* ---------- the front door ---------- */
.find{max-width:44rem;margin:3.5rem auto 3rem;text-align:center}
.find__h{font-size:clamp(26px,4.4vw,40px);line-height:1.15;letter-spacing:-.03em;font-weight:700;
  margin:0 0 .7rem;text-wrap:balance}
.find__s{font-size:17px;line-height:1.6;color:var(--ink-2);margin:0 auto 1.6rem;max-width:34rem}
.find__box{position:relative;text-align:left}
.find__box input{width:100%;min-height:56px;font-size:17px;padding:0 1rem;border-radius:12px;
  border:1px solid var(--line-2,var(--line));background:var(--surface);color:var(--ink)}
.find__box input:focus-visible{outline:2px solid var(--blue-500);outline-offset:2px}
.find__hits{position:absolute;left:0;right:0;top:calc(100% + .4rem);z-index:20;background:var(--surface);
  border:1px solid var(--line);border-radius:12px;box-shadow:var(--shadow-2);overflow:hidden}
.find__hit{display:block;width:100%;text-align:left;min-height:44px;padding:.6rem 1rem;border:0;
  background:none;font:inherit;font-size:16px;color:var(--ink);cursor:pointer}
.find__hit:hover,.find__hit:focus-visible{background:var(--blue-050)}
.find__note{margin:.6rem 0 0;font-size:14px;color:var(--ink-2)}
.find__eg{display:flex;flex-wrap:wrap;gap:.5rem;justify-content:center;margin:1.1rem 0 0}
.chip{display:inline-flex;align-items:center;min-height:36px;padding:0 .8rem;border-radius:999px;
  border:1px solid var(--line);font-size:14px;color:var(--ink-2);text-decoration:none}
.chip:hover{border-color:var(--blue-300);color:var(--blue-600)}
.find__cred{margin:1.8rem auto 0;max-width:36rem;font-size:14px;line-height:1.6;color:var(--ink-3)}

.doors{display:flex;flex-direction:column;gap:.6rem;max-width:52rem;margin:0 auto 3rem}
.door{display:grid;grid-template-columns:5.5rem 1fr;align-items:baseline;gap:.2rem 1.2rem;
  padding:1.1rem 1.3rem;border:1px solid var(--line);border-radius:12px;background:var(--surface);
  text-decoration:none;color:inherit}
.door:hover{border-color:var(--blue-300)}
.door__n{grid-row:span 2;font-family:var(--mono);font-size:26px;font-weight:600;color:var(--blue-600);
  font-variant-numeric:tabular-nums}
.door__t{font-size:17px;font-weight:600}
.door__s{font-size:14.5px;color:var(--ink-2)}

.qlist{max-width:52rem;margin:0 auto 4rem}
.qlist__h{font-size:18px;font-weight:600;letter-spacing:-.01em;margin:0 0 .8rem;color:var(--ink-2)}
.qrow{display:grid;grid-template-columns:11rem 1fr;gap:.2rem 1rem;padding:.75rem .2rem;
  border-top:1px solid var(--line);text-decoration:none;color:inherit}
.qrow:hover .qrow__n{color:var(--blue-600)}
.qrow__n{font-weight:600;font-size:15.5px}
.qrow__s{font-size:14.5px;color:var(--ink-2)}
@media (max-width:700px){
  .find{margin-top:2rem}
  .door{grid-template-columns:1fr;gap:.15rem}
  .door__n{grid-row:auto}
  .qrow{grid-template-columns:1fr}
}
```

- [ ] **Step 7: Verify in the browser**

Run: `python3 -m http.server 8765 --directory app`
Visit `http://localhost:8765/#/` and check, at 1440 wide and at 375 wide:
- typing `amber` lists Amber Valley, Enter opens `#/places/E07000032`
- typing `DE5 3TZ` shows the postcode note rather than silence
- the three example chips navigate
- no console errors, no horizontal scrollbar

- [ ] **Step 8: Run the gates**

Run: `npm test && python3 tools/seo-check.py`
Expected: tests pass, `0 errors, 0 warnings`.

- [ ] **Step 9: Commit**

```bash
git add app/index.html app/assets/shell.js app/assets/app.css app/assets/platform.js
git commit -m "Open on one question: what does the record say about your area"
```

---

### Task 4: Retire the sidebar

The permanent dark sidebar is the single thing that makes the app read as an internal console. It becomes a slim header everywhere, and the drawer stays for narrow screens.

**Files:**
- Modify: `app/assets/app.css` (grid, header)
- Modify: `app/assets/shell.css` (drawer breakpoint)
- Modify: `app/index.html` (header contents)
- Modify: `app/assets/shell.js` (`renderTabbar` items)

**Interfaces:**
- Consumes: the drawer behaviour added on 22 September (`sidebar()` in `app/assets/app.js`), unchanged.
- Produces: nothing new. `.app` becomes a single column at every width.

- [ ] **Step 1: Make the shell one column**

Modify `app/assets/app.css`. Find `.app{` and change its `grid-template-columns` so the sidebar is never a layout column:

```css
.app{display:grid;grid-template-columns:1fr;min-height:100vh}
```

- [ ] **Step 2: Make the drawer the only sidebar**

Modify `app/assets/shell.css`. Change the drawer media query from `@media(max-width:860px){` to apply at every width by moving the `.side` rules out of the query. Cut these three rules out of the `@media(max-width:860px)` block and paste them above it, unwrapped:

```css
/* The sidebar is a drawer at every width now: the front page does the work the
   permanent sidebar used to, and a console rail is what made this read as an
   internal tool. */
.side{position:fixed;inset:0 auto 0 0;width:266px;z-index:70;transform:translateX(-100%);
  transition:transform .18s var(--ease-out)}
.side.on{transform:none;box-shadow:var(--shadow-3)}
```

- [ ] **Step 3: Keep the menu button at every width**

Modify `app/assets/app.css`. Find the rule that hides the menu button on wide screens (search for `data-side-toggle` or `.iconbtn` inside a `min-width` query). If one exists, delete it. Then confirm `app/assets/app.js`'s `sidebar()` still inerts the drawer when closed by changing its media query:

```js
    const offCanvas = matchMedia('(max-width:100000px)');
```

Replace that line with a constant instead, since the drawer is now always off-canvas:

```js
    const offCanvas = { matches: true, addEventListener() {} };
```

- [ ] **Step 4: Cut the mobile bar to three**

Modify `app/assets/shell.js`. In `renderTabbar`, replace the item list it renders with exactly three destinations:

```js
    const items = [
      { href: '#/', label: 'Find' },
      { href: '#/compare', label: 'Compare' },
      { href: '#/about', label: 'About' },
    ];
```

- [ ] **Step 5: Verify**

Run: `python3 -m http.server 8765 --directory app`
At 1440: no sidebar column, the menu button opens the drawer, Escape closes it, focus returns to the button.
At 375: the bottom bar shows three items, each at least 44px tall.
Run: `npm test && python3 tools/seo-check.py`
Expected: pass, `0 errors`.

- [ ] **Step 6: Commit**

```bash
git add app/assets/app.css app/assets/shell.css app/assets/app.js app/assets/shell.js
git commit -m "Retire the permanent sidebar; the front page carries the navigation"
```

---

### Task 5: The place summary

Two or three true sentences about one place, generated from that place's own figures.

**Files:**
- Create: `app/assets/lib/summary.js`
- Create: `tests/js/fixtures/payload.json`
- Create: `tests/js/summary.test.js`
- Modify: `app/assets/lib/entry.js`

**Interfaces:**
- Consumes: the payload shape `{ places: { names, byLad }, systems }`.
- Produces: `placeSummary(code: string, payload: object) => string[]`, zero to three sentences, most notable first. Never invents a figure, never rounds beyond one decimal place.

- [ ] **Step 1: Write the fixture**

Create `tests/js/fixtures/payload.json`. These are the real field names and real values for Amber Valley, trimmed to what the summary reads:

```json
{
  "places": {
    "names": { "E07000032": "Amber Valley", "E06000001": "Hartlepool" },
    "byLad": {
      "E07000032": {
        "plumbline": { "lpa": "Amber Valley", "major_decisions": 85.0, "headline_pct": 97.6,
                       "dwelling_decisions": 46.0, "statutory_pct": 8.7 },
        "catchment": { "lad_name": "Amber Valley", "schools": 68, "capacity": 19488,
                       "pupils": 17734, "utilisation_pct": 91.0 },
        "lastmile": { "lad_name": "Amber Valley", "premises": 130067, "gigabit_pct": 81.8 }
      },
      "E06000001": {
        "catchment": { "lad_name": "Hartlepool", "schools": 40, "capacity": 12000,
                       "pupils": 11000, "utilisation_pct": 91.7 }
      }
    }
  },
  "systems": {
    "plumbline": { "headline_pct": 90.4, "statutory_pct": 15.9 },
    "catchment": { "national": { "utilisation_pct": 89.5 } },
    "lastmile": { "new_build_pct": 83.3, "other_pct": 83.5 }
  }
}
```

- [ ] **Step 2: Write the failing test**

Create `tests/js/summary.test.js`:

```js
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { placeSummary } from '../../app/assets/lib/summary.js';

const PAYLOAD = JSON.parse(readFileSync(new URL('./fixtures/payload.json', import.meta.url)));

test('the sharpest divergence leads', () => {
  const [first] = placeSummary('E07000032', PAYLOAD);
  // 8.7 against a published 97.6 is the widest gap this place has.
  assert.match(first, /8\.7%/);
  assert.match(first, /97\.6%/);
  assert.match(first, /Amber Valley/);
});

test('every sentence names a figure the payload holds', () => {
  const lines = placeSummary('E07000032', PAYLOAD);
  assert.ok(lines.length >= 2 && lines.length <= 3, `got ${lines.length} sentences`);
  for (const line of lines) {
    assert.match(line, /\d/, `no figure in: ${line}`);
    assert.doesNotMatch(line, /undefined|NaN|null/);
  }
});

test('a place with one question gets one sentence, not padding', () => {
  const lines = placeSummary('E06000001', PAYLOAD);
  assert.equal(lines.length, 1);
  assert.match(lines[0], /91\.7%/);
});

test('an unknown place produces nothing rather than guessing', () => {
  assert.deepEqual(placeSummary('E99999999', PAYLOAD), []);
  assert.deepEqual(placeSummary('', PAYLOAD), []);
});

test('no em dash reaches the copy', () => {
  for (const line of placeSummary('E07000032', PAYLOAD)) {
    assert.doesNotMatch(line, /\u2014|\u2013/, `dash in: ${line}`);
  }
});
```

- [ ] **Step 3: Run it and watch it fail**

Run: `node --test tests/js/summary.test.js`
Expected: FAIL, `Cannot find module`.

- [ ] **Step 4: Write the module**

Create `app/assets/lib/summary.js`:

```js
/* Two or three sentences about one place, built only from that place's own
   figures and the comparator each figure is published against. The order is by
   how far the place sits from its comparator, so the sentence a reader most
   needs comes first. Nothing here rounds beyond the payload, and nothing is
   said that the payload does not carry. */

const pct = v => `${Number(v).toFixed(1).replace(/\.0$/, '')}%`;
const count = v => Number(v).toLocaleString('en-GB');

const LINES = [
  {
    id: 'plumbline',
    gap: (p) => (p.plumbline && p.plumbline.statutory_pct != null && p.plumbline.headline_pct != null)
      ? Math.abs(p.plumbline.headline_pct - p.plumbline.statutory_pct) : null,
    say: (p, name) => `Of ${count(p.plumbline.dwelling_decisions)} major housing decisions in `
      + `${name}, ${pct(p.plumbline.statutory_pct)} were made inside the statutory 13 weeks without an `
      + `agreed extension. The published measure for the same authority is ${pct(p.plumbline.headline_pct)}.`,
  },
  {
    id: 'catchment',
    gap: (p, n) => (p.catchment && p.catchment.utilisation_pct != null && n.catchment
      && n.catchment.national && n.catchment.national.utilisation_pct != null)
      ? Math.abs(p.catchment.utilisation_pct - n.catchment.national.utilisation_pct) : null,
    say: (p, name, n) => `School places in ${name} are ${pct(p.catchment.utilisation_pct)} used, `
      + `${count(p.catchment.pupils)} pupils in ${count(p.catchment.capacity)} places, against `
      + `${pct(n.catchment.national.utilisation_pct)} nationally.`,
  },
  {
    id: 'lastmile',
    gap: (p, n) => (p.lastmile && p.lastmile.gigabit_pct != null && n.lastmile
      && n.lastmile.other_pct != null)
      ? Math.abs(p.lastmile.gigabit_pct - n.lastmile.other_pct) : null,
    say: (p, name, n) => `${pct(p.lastmile.gigabit_pct)} of ${count(p.lastmile.premises)} premises in `
      + `${name} are gigabit-ready, against ${pct(n.lastmile.other_pct)} nationally.`,
  },
];

export function placeSummary(code, payload) {
  const places = (payload && payload.places) || {};
  const name = (places.names || {})[code];
  const place = (places.byLad || {})[code];
  if (!name || !place) return [];
  const national = (payload && payload.systems) || {};

  return LINES
    .map(line => ({ line, gap: line.gap(place, national) }))
    .filter(x => x.gap !== null && Number.isFinite(x.gap))
    .sort((a, b) => b.gap - a.gap)
    .slice(0, 3)
    .map(x => x.line.say(place, name, national));
}
```

- [ ] **Step 5: Run the test again**

Run: `node --test tests/js/summary.test.js`
Expected: PASS, 5 tests.

- [ ] **Step 6: Expose it**

Modify `app/assets/lib/entry.js` so it reads in full:

```js
/* The app is built from classic scripts that assign globals. The pure logic
   lives in modules so the test runner can import it directly, and this entry is
   the one bridge between the two: it runs deferred, before DOMContentLoaded, so
   the router finds it by the time any route is handled. */
import { canonicalHash } from './routes.js';
import { matchPlaces, looksLikePostcode } from './places.js';
import { placeSummary } from './summary.js';

window.GT_LIB = Object.assign(window.GT_LIB || {}, {
  canonicalHash, matchPlaces, looksLikePostcode, placeSummary,
});
```

- [ ] **Step 7: Commit**

```bash
git add app/assets/lib/summary.js app/assets/lib/entry.js tests/js/summary.test.js tests/js/fixtures/payload.json
git commit -m "Say what a place's figures mean, in sentences built from those figures"
```

---

### Task 6: The place page

**Files:**
- Modify: `app/assets/shell.js` (`openPlace`, place view rendering)
- Modify: `app/index.html` (place view markup)
- Modify: `app/assets/app.css` (answer blocks)

**Interfaces:**
- Consumes: `window.GT_LIB.placeSummary`, `Platform.payload()`, `SYSTEMS`.
- Produces: `buildPlacePage(code)` in `shell.js`, rendering into `#placePage`.

- [ ] **Step 1: Add the markup**

Modify `app/index.html`. Inside the existing `data-view="places"` view, above the existing index table, insert:

```html
    <div id="placePage" hidden></div>
```

- [ ] **Step 2: Render the page**

Modify `app/assets/shell.js`. Add above `function route() {`:

```js
  /* One place, as a document: what it is, what stands out, then every question
     that has an answer for it, and plainly those that do not. */
  function buildPlacePage(code) {
    const host = $('#placePage'), index = $('#placeIndex');
    if (!host) return;
    const payload = Platform.payload ? Platform.payload() : null;
    const names = (payload && payload.places && payload.places.names) || {};
    const byLad = (payload && payload.places && payload.places.byLad) || {};
    const name = names[code], place = byLad[code];
    if (!name || !place) { host.hidden = true; if (index) index.hidden = false; return; }

    const lib = window.GT_LIB || {};
    const summary = lib.placeSummary ? lib.placeSummary(code, payload) : [];
    const answered = SYSTEMS.filter(s => place[s.id]);
    const missing = SYSTEMS.filter(s => !place[s.id]);

    host.innerHTML = `
      <h2 class="place__h">${esc(name)}</h2>
      <p class="place__k">${answered.length} of ${SYSTEMS.length} questions answered here</p>
      ${summary.map(line => `<p class="place__sum">${esc(line)}</p>`).join('')}
      <div class="answers">
        ${answered.map(s => `
          <article class="answer">
            <h3 class="answer__q">${esc(s.n)}</h3>
            <p class="answer__s">${esc(s.s || '')}</p>
            <a class="answer__go" href="#/questions/${esc(s.id)}">How this is computed</a>
          </article>`).join('')}
      </div>
      ${missing.length ? `<p class="place__none">No answer here for ${
        missing.map(s => esc(s.n)).join(', ')}. That is usually because the service is run by the
        county rather than the district, and the figure is published at that level.</p>` : ''}`;
    host.hidden = false;
    if (index) index.hidden = true;
  }
```

- [ ] **Step 3: Call it from the route**

Modify `app/assets/shell.js`. In the `places` branch of `route()`, replace:

```js
      if (seg[1]) safely(() => openPlace(seg[1]));
```

with:

```js
      const host = $('#placePage'), index = $('#placeIndex');
      if (seg[1]) { safely(() => buildPlacePage(seg[1])); }
      else { if (host) host.hidden = true; if (index) index.hidden = false; }
```

- [ ] **Step 4: Style it**

Modify `app/assets/app.css`. Append:

```css
/* ---------- one place, as a document ---------- */
.place__h{font-size:clamp(28px,4.2vw,40px);line-height:1.12;letter-spacing:-.03em;font-weight:700;
  margin:.4rem 0 .3rem;text-wrap:balance}
.place__k{font-family:var(--mono);font-size:12px;letter-spacing:.1em;text-transform:uppercase;
  color:var(--ink-3);margin:0 0 1.4rem}
.place__sum{font-size:18px;line-height:1.6;max-width:44rem;margin:0 0 .9rem}
.answers{display:flex;flex-direction:column;gap:.1rem;margin:2rem 0 1.5rem;max-width:52rem}
.answer{padding:1.1rem 0;border-top:1px solid var(--line)}
.answer__q{font-size:17px;font-weight:650;margin:0 0 .2rem}
.answer__s{font-size:15px;color:var(--ink-2);margin:0 0 .5rem;max-width:40rem}
.answer__go{font-size:14px;color:var(--blue-600);text-decoration:none}
.answer__go:hover{text-decoration:underline}
.place__none{font-size:14.5px;line-height:1.6;color:var(--ink-3);max-width:44rem;
  padding-top:1rem;border-top:1px solid var(--line)}
```

- [ ] **Step 5: Verify**

Visit `http://localhost:8765/#/places/E07000032`.
Expected: the name as the visible heading, two or three sentences leading with the 8.7 against 97.6 gap, one block per answered question, and the sentence about questions with no answer. Then check a two-tier county district and a combined authority: `#/places/E07000223` and `#/places/E47000004` if present in `places.names`.
Run: `npm test && python3 tools/seo-check.py`

- [ ] **Step 6: Commit**

```bash
git add app/index.html app/assets/shell.js app/assets/app.css
git commit -m "Give a place its own page, led by what stands out about it"
```

---

### Task 7: Compare, Unusual and About

**Files:**
- Create: `app/assets/lib/unusual.js`
- Create: `tests/js/unusual.test.js`
- Modify: `app/assets/lib/entry.js`
- Modify: `app/index.html` (three views)
- Modify: `app/assets/shell.js` (three route branches)

**Interfaces:**
- Consumes: the payload, `placeSummary` unchanged.
- Produces: `unusualRows(payload, limit = 50) => Array<{code, name, question, figure, against, againstLabel, gap}>`, sorted by `gap` descending.

- [ ] **Step 1: Write the failing test**

Create `tests/js/unusual.test.js`:

```js
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { unusualRows } from '../../app/assets/lib/unusual.js';

const PAYLOAD = JSON.parse(readFileSync(new URL('./fixtures/payload.json', import.meta.url)));

test('the widest gap comes first', () => {
  const rows = unusualRows(PAYLOAD);
  assert.equal(rows[0].code, 'E07000032');
  assert.equal(rows[0].question, 'plumbline');
  assert.equal(Math.round(rows[0].gap * 10) / 10, 88.9);   // 97.6 - 8.7
});

test('every row carries both figures and what they are measured against', () => {
  for (const row of unusualRows(PAYLOAD)) {
    assert.ok(row.name, 'row has a place name');
    assert.equal(typeof row.figure, 'number');
    assert.equal(typeof row.against, 'number');
    assert.ok(row.againstLabel.length > 3);
  }
});

test('the limit is honoured', () => {
  assert.equal(unusualRows(PAYLOAD, 1).length, 1);
});

test('a place missing a question contributes no row for it', () => {
  const rows = unusualRows(PAYLOAD).filter(r => r.code === 'E06000001');
  assert.deepEqual(rows.map(r => r.question), ['catchment']);
});
```

- [ ] **Step 2: Run it and watch it fail**

Run: `node --test tests/js/unusual.test.js`
Expected: FAIL, `Cannot find module`.

- [ ] **Step 3: Write the module**

Create `app/assets/lib/unusual.js`:

```js
/* Where a place sits furthest from the figure it is published against. Three
   questions carry both a local figure and a stated comparator, so those are the
   three this ranks. Every row keeps both numbers, so a reader can check the gap
   rather than trust it. */

const COMPARATORS = [
  {
    id: 'plumbline',
    figure: p => p.plumbline && p.plumbline.statutory_pct,
    against: p => p.plumbline && p.plumbline.headline_pct,
    againstLabel: 'the published measure for the same authority',
  },
  {
    id: 'catchment',
    figure: p => p.catchment && p.catchment.utilisation_pct,
    against: (p, n) => n.catchment && n.catchment.national && n.catchment.national.utilisation_pct,
    againstLabel: 'the national rate',
  },
  {
    id: 'lastmile',
    figure: p => p.lastmile && p.lastmile.gigabit_pct,
    against: (p, n) => n.lastmile && n.lastmile.other_pct,
    againstLabel: 'the national share',
  },
];

export function unusualRows(payload, limit = 50) {
  const places = (payload && payload.places) || {};
  const names = places.names || {};
  const byLad = places.byLad || {};
  const national = (payload && payload.systems) || {};
  const rows = [];

  for (const [code, place] of Object.entries(byLad)) {
    const name = names[code];
    if (!name) continue;
    for (const c of COMPARATORS) {
      const figure = c.figure(place, national);
      const against = c.against(place, national);
      if (!Number.isFinite(figure) || !Number.isFinite(against)) continue;
      rows.push({ code, name, question: c.id, figure, against,
                  againstLabel: c.againstLabel, gap: Math.abs(against - figure) });
    }
  }
  return rows.sort((a, b) => b.gap - a.gap).slice(0, limit);
}
```

- [ ] **Step 4: Run the test again**

Run: `node --test tests/js/unusual.test.js`
Expected: PASS, 4 tests.

- [ ] **Step 5: Expose the ranking**

Modify `app/assets/lib/entry.js`, adding the import and the key:

```js
import { unusualRows } from './unusual.js';
```

and extend the assignment so it reads:

```js
window.GT_LIB = Object.assign(window.GT_LIB || {}, {
  canonicalHash, matchPlaces, looksLikePostcode, placeSummary, unusualRows,
});
```

- [ ] **Step 6: Add the two views**

Modify `app/index.html`. After the `home` view, add these two. Compare needs no
view of its own: it shows the existing places index, which `buildPlaces()`
already renders into `#viewPlaces`.

```html
  <div class="view" data-view="unusual" id="viewUnusual" hidden>
    <h2 class="place__h">What looks unusual right now</h2>
    <p class="find__s" style="text-align:left;margin-left:0">Where a place sits furthest from the figure
      it is published against. Both numbers are shown, so the gap can be checked before it is quoted.</p>
    <div id="unusualBody"></div>
  </div>

  <div class="view" data-view="about" id="viewAbout" hidden>
    <h2 class="place__h">How this is built</h2>
    <div id="aboutBody"></div>
  </div>
```

- [ ] **Step 7: Render and route them**

Modify `app/assets/shell.js`. Add above `route()`:

```js
  function buildUnusual() {
    const host = $('#unusualBody'); if (!host) return;
    const lib = window.GT_LIB || {};
    const rows = lib.unusualRows ? lib.unusualRows(Platform.payload()) : [];
    const label = id => (SYSTEMS.find(s => s.id === id) || {}).n || id;
    host.innerHTML = `<table class="tbl"><thead><tr>
        <th>Place</th><th>Question</th><th class="num">Its figure</th>
        <th class="num">Measured against</th><th class="num">Gap</th></tr></thead><tbody>
      ${rows.map(r => `<tr>
        <td><a href="#/places/${esc(r.code)}">${esc(r.name)}</a></td>
        <td>${esc(label(r.question))}</td>
        <td class="num mono">${r.figure.toFixed(1)}%</td>
        <td class="num mono">${r.against.toFixed(1)}%<span class="answer__s"> ${esc(r.againstLabel)}</span></td>
        <td class="num mono">${r.gap.toFixed(1)}</td></tr>`).join('')}
      </tbody></table>`;
  }
```

Then in `route()`, add these branches immediately before the `places` branch:

```js
    // Compare is the district index that already exists, given its own door.
    // buildPlaces() creates #placeIndex inside #viewPlaces and returns early if
    // it is already there, so the compare route shows that view rather than
    // building a second table.
    if (head === 'compare') {
      show('places'); setChrome('compare');
      const host = $('#placePage'), index = $('#placeIndex');
      if (host) host.hidden = true;
      safely(buildPlaces, '#viewPlaces');
      if ($('#placeIndex')) $('#placeIndex').hidden = false;
      scrollTop(); return;
    }
    if (head === 'unusual') {
      show('unusual'); setChrome('unusual'); safely(buildUnusual, '#unusualBody'); scrollTop(); return;
    }
    if (head === 'about') {
      show('about'); setChrome('about'); safely(buildAbout, '#aboutBody'); scrollTop(); return;
    }
```

Add the three entries to `TITLES_PUBLIC`, beside the ones already there:

```js
    compare:   ['Explore · Compare', 'Compare every district'],
    unusual:   ['Explore · Unusual', 'What looks unusual right now'],
    about:     ['Evidence · How this is built', 'How this is built'],
```

and to `DOCS`:

```js
    compare:   ['Compare every district', 'Every district the connected record covers, with the figures each question answers for it, sortable and exportable.'],
    unusual:   ['What looks unusual', 'Where a place sits furthest from the figure it is published against, with both numbers and the source for each.'],
    about:     ['How this is built', 'The two joins, every source the record reads, the corrections published so far, and what this cannot do.'],
```

Then add `buildAbout()` above `route()`. It moves the platform inventory off the
front page and puts it where it belongs, as evidence:

```js
  /* The inventory used to greet every visitor. It belongs here, next to the
     method and the corrections, where it is evidence rather than a welcome. */
  function buildAbout() {
    const host = $('#aboutBody'); if (!host) return;
    const payload = Platform.payload ? Platform.payload() : null;
    if (!payload) return;
    const sources = Platform.sourceSummary() || {};
    const corrections = Platform.corrections() || {};
    const entries = corrections.entries || [];
    const built = (Platform.builtSystems() || []).length;

    host.innerHTML = `
      <p class="place__sum">Two joins are added to data anyone can download: where a reference becomes
        a property, a postcode and then one of ${num(Object.keys((payload.places||{}).names||{}).length)}
        districts, and who, where name variants become one company number.</p>
      <div class="tiles">
        ${tile(built + ' of ' + SYSTEMS.length, 'questions with a measured answer')}
        ${tile(num((sources.rows||[]).filter(r => !r.blocked).length) + ' of ' + num((sources.rows||[]).length), 'sources returning data')}
        ${tile(num(entries.length), 'corrections published, each with the test that guards it')}
      </div>
      <h3 class="qlist__h" style="margin-top:2rem">Corrections</h3>
      <div class="answers">
        ${entries.map(c => `
          <article class="answer">
            <h4 class="answer__q">${esc(c.title || c.id || 'Correction')}</h4>
            <p class="answer__s">${esc(c.believed || '')}</p>
            <p class="answer__s">${esc(c.truth || c.correction || '')}</p>
          </article>`).join('')}
      </div>`;
  }

  // A small helper so the three figures above read as one object.
  function tile(value, label) {
    return `<div class="tile"><div class="tile__v mono">${esc(value)}</div>
            <div class="tile__l">${esc(label)}</div></div>`;
  }
```

Before writing it, confirm the field names on a correction entry, since this is
the only place the plan guesses at them:

Run: `python3 -c "import json;d=json.load(open('app/data/platform.json'));print(list(d['corrections']['entries'][0]))"`
Expected: a list of keys. Use those exact keys in the two `answer__s` lines and
drop any that do not exist.

- [ ] **Step 8: Verify and commit**

Run: `npm test && python3 tools/seo-check.py`, then visit `#/compare`, `#/unusual`, `#/about` at both widths.

```bash
git add app/assets/lib/unusual.js app/assets/lib/entry.js tests/js/unusual.test.js app/index.html app/assets/shell.js
git commit -m "Add compare, unusual and how-this-is-built behind the front door"
```

---

### Task 8: The visual register

The spec asks for a different bearing, not different colours: larger body text,
wider gutters, fewer borders, cards only where they earn their keep. The
component CSS in Tasks 3 to 7 already follows it; this task applies it to the
shell so the two do not disagree.

**Files:**
- Modify: `app/assets/app.css`

**Interfaces:**
- Consumes: the tokens already defined on `:root` and `[data-theme="dark"]`.
- Produces: nothing new. No token is renamed, so no other file changes.

- [ ] **Step 1: Raise the body size and the measure**

Modify `app/assets/app.css`. In the `body` rule, change `font-size:15px` to:

```css
  font-size:16px;
```

- [ ] **Step 2: Give the page room**

Find `.pad{` and replace its padding with a wider gutter and more vertical rhythm:

```css
.pad{padding:2rem 1.6rem 4rem;max-width:72rem;margin:0 auto}
```

- [ ] **Step 3: Check nothing collapsed**

Run: `python3 -m http.server 8765 --directory app`
At 1440 and at 375, on `#/`, `#/places/E07000032`, `#/compare`, `#/unusual`, `#/about`:
- no horizontal overflow
- no text overlapping a neighbour
- tables still inside their scrollers
- every interactive target at least 44px

Run: `npm test && python3 tools/seo-check.py`
Expected: pass, `0 errors, 0 warnings`.

- [ ] **Step 4: Commit**

```bash
git add app/assets/app.css
git commit -m "Give the interface room: 16px body, wider gutters, fewer rules"
```

---

### Task 9: Final verification and publish

**Files:** none changed unless a check fails.

- [ ] **Step 1: The full gate**

```bash
npm test
python3 tools/seo-check.py
node build.js && python3 tools/seo-check.py
```
Expected: all tests pass; `0 errors, 0 warnings` both times.

- [ ] **Step 2: Campaign URLs**

With the local server running, visit and confirm each renders with no console error:
`#/places/E07000032`, `#/systems/plumbline`, `#/places`, `#/method`, `#/sources`.

- [ ] **Step 3: Accessibility and responsive**

At 375 and 1440, on `#/`, `#/places/E07000032`, `#/compare`:
- exactly one visible `h1`
- no horizontal overflow
- every on-screen interactive target at least 44px in both dimensions
- contrast measured in both themes, no value below 4.5:1 for body text

- [ ] **Step 4: Check no dash reached the copy**

```bash
python3 - <<'EOF'
import glob, pathlib
files = ['app/index.html'] + glob.glob('app/assets/*.js') + glob.glob('app/assets/lib/*.js')
bad = {f: n for f in files
       for n in [sum(pathlib.Path(f).read_text().count(x) for x in ('\u2014', '\u2013', '&mdash;', '&ndash;'))] if n}
print(bad or 'clean')
EOF
```
Expected: `clean`.

- [ ] **Step 5: Publish**

```bash
git push origin full-data-and-spines
git checkout main && git merge --ff-only full-data-and-spines && git push origin main
git checkout full-data-and-spines
gh run list --limit 1
```
Then confirm live: `curl -s https://ukgroundtruth.co.uk/ | grep -c "What does the public record say"` returns 1.
