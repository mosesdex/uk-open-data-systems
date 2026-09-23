import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { canonicalHash, firstServable, ANCHOR, SECTION, ROUTER_HEADS } from '../../app/assets/lib/routes.js';

// ROUTER_HEADS, exported by routes.js, is the authoritative list of heads
// route() in app/assets/shell.js actually dispatches today. The test below
// titled "ROUTER_HEADS matches..." reads shell.js and enforces that the two
// stay in step, so importing it here (instead of a hand-copied literal set)
// is what keeps these tests meaning what they say.
const canRenderToday = (head) => ROUTER_HEADS.has(head);

// The router (route() in app/assets/shell.js) does not stop at one hop: it
// re-invokes canonicalHash on its own redirect target, so a mapping can
// cascade (e.g. #compare -> #/systems -> #/) before it settles. Asserting
// only the first hop is the same blind spot that let two earlier
// regressions through, so tests that care where a hash actually ends up
// should walk it the way the router does, via this helper, rather than
// calling canonicalHash once. The hard stop at maxHops turns a mapping
// that was miswired into a cycle into a test failure instead of a hang.
function resolveFixedPoint(hash, canRender = canRenderToday, maxHops = 10) {
  let current = hash;
  let hops = 0;
  for (let i = 0; i < maxHops; i++) {
    const next = canonicalHash(current, canRender);
    if (next === null) return { settled: current, hops };
    current = next;
    hops++;
  }
  return { settled: current, hops, exceeded: true };
}

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

// Task 7 gave "questions" and "about" real handlers, so ROUTER_HEADS now
// contains both and canRenderToday renders them like everything else. The
// two paired regressions that used to live here ("...is left alone while
// questions/about has no handler") asserted the opposite -- that the router
// could NOT yet render them -- so their premise is gone and so are they;
// "canonical routes are left alone" above already covers today's steady
// state, including #/questions/plumbline and #/about themselves. What is
// still worth guarding is that the redirect keeps working under a predicate
// that allows only the exact head being tested, independent of whatever
// else ROUTER_HEADS happens to contain, which is what the two tests below
// still do.
test('#/systems/plumbline redirects once questions can render', () => {
  const canRenderWithQuestions = (head) => canRenderToday(head) || head === 'questions';
  assert.equal(canonicalHash('#/systems/plumbline', canRenderWithQuestions), '#/questions/plumbline');
});

test('#/method redirects once about can render', () => {
  const canRenderWithAbout = (head) => canRenderToday(head) || head === 'about';
  assert.equal(canonicalHash('#/method', canRenderWithAbout), '#/about');
});

test('the 150 outreach emails linking #/systems/plumbline redirect to the question under the live router', () => {
  // 150 sent emails link to this exact URL, so if this test fails
  // the redirect must be fixed rather than the test updated.
  assert.equal(canonicalHash('#/systems/plumbline', canRenderToday), '#/questions/plumbline');
});

test('every table mapping resolves to a route once the predicate allows it', () => {
  const canRenderAnything = () => true;
  for (const [hash, expected] of [...Object.entries(ANCHOR), ...Object.entries(SECTION)]) {
    const result = canonicalHash(hash, canRenderAnything);
    assert.ok(result && result.startsWith('#/'),
      `${hash} -> ${JSON.stringify(result)} should start with #/ (table says ${expected})`);
  }
});

test('ROUTER_HEADS matches every head route() in shell.js actually dispatches', () => {
  // This is the guard that stops ROUTER_HEADS and route()'s own branches
  // drifting apart: it reads shell.js as text, pulls out every head literal
  // from a "head === '<name>'" branch inside route(), and checks the set
  // against ROUTER_HEADS. A later task that adds a handler without updating
  // ROUTER_HEADS (or the reverse) fails here.
  const here = path.dirname(fileURLToPath(import.meta.url));
  const shellPath = path.join(here, '../../app/assets/shell.js');
  const src = fs.readFileSync(shellPath, 'utf8');

  // Tolerate optional whitespace between a function's name and its brace
  // (e.g. "function route () {") so a harmless reformat doesn't break this
  // test along with whatever it's meant to guard.
  const routeMatch = /function\s+route\s*\(\s*\)\s*\{/.exec(src);
  assert.ok(routeMatch, 'could not find function route() in shell.js');
  const routeStart = routeMatch.index;
  const safelyMatch = /function\s+safely\s*\(\s*fn\s*,\s*targetSel\s*\)\s*\{/.exec(src.slice(routeStart));
  assert.ok(safelyMatch, 'could not find the end of route() in shell.js');
  const routeEnd = routeStart + safelyMatch.index;
  const routeSrc = src.slice(routeStart, routeEnd);

  const dispatched = new Set();
  // Accept either quote style around the head literal, matched by the same
  // quote character (not '/" mixed), rather than assuming single quotes.
  const pattern = /head === (['"])([^'"]*)\1/g;
  let m;
  while ((m = pattern.exec(routeSrc)) !== null) dispatched.add(m[2]);

  assert.deepEqual(dispatched, ROUTER_HEADS,
    `heads route() dispatches (${JSON.stringify([...dispatched].sort())}) must match ` +
    `ROUTER_HEADS (${JSON.stringify([...ROUTER_HEADS].sort())})`);
});

test('FALLBACK_HEADS in shell.js matches ROUTER_HEADS', () => {
  // FALLBACK_HEADS is shell.js's own hand-copied literal of the heads route()
  // dispatches, used only when window.GT_LIB has not loaded. Nothing else
  // keeps it in step with ROUTER_HEADS, so this reads shell.js as text, the
  // same way the test above checks route() itself, and checks the two sets
  // match.
  const here = path.dirname(fileURLToPath(import.meta.url));
  const shellPath = path.join(here, '../../app/assets/shell.js');
  const src = fs.readFileSync(shellPath, 'utf8');

  const fallbackMatch = /FALLBACK_HEADS\s*=\s*new Set\(\s*\[([^\]]*)\]\s*\)/.exec(src);
  assert.ok(fallbackMatch, 'could not find FALLBACK_HEADS in shell.js');

  const fallback = new Set();
  // Same tolerant quote matching as the route() parse above.
  const itemPattern = /(['"])([^'"]*)\1/g;
  let fm;
  while ((fm = itemPattern.exec(fallbackMatch[1])) !== null) fallback.add(fm[2]);

  assert.deepEqual(fallback, ROUTER_HEADS,
    `FALLBACK_HEADS in shell.js (${JSON.stringify([...fallback].sort())}) must match ` +
    `ROUTER_HEADS (${JSON.stringify([...ROUTER_HEADS].sort())})`);
});

test('every legacy fragment settles on a route the router can render', () => {
  // Regression for the "guard suppresses the redirect and the raw fragment
  // is not dispatchable either" hole, and for the cascade the router
  // performs on its own redirect target (e.g. #compare -> #/systems -> #/,
  // two hops before it renders). Earlier versions of this test only checked
  // the first hop, which is exactly the blind spot that let that cascade
  // through unnoticed; this resolves each published fragment the way the
  // router does, all the way to where it actually settles.
  const fragments = [
    '#top', '#hero', '#spines', '#chains', '#compare', '#feeds', '#honesty',
    '#place', '#systems', '#kpis', '#org/12345678', '#search', '#system/plumbline',
  ];

  for (const fragment of fragments) {
    const { settled, hops, exceeded } = resolveFixedPoint(fragment, canRenderToday);

    assert.ok(!exceeded,
      `${fragment} did not settle within the 10-hop cap (took ${hops} hop(s), stuck at ${settled})`);

    const head = settled.replace(/^#\/?/, '').split('/')[0];
    assert.ok(ROUTER_HEADS.has(head),
      `${fragment} settles on ${settled} after ${hops} hop(s), whose head "${head}" is not in ROUTER_HEADS`);
  }
});

test('no hash in any table can fail to terminate', () => {
  // Independent of what ROUTER_HEADS allows today, the resolve() tables
  // themselves must never cycle. A predicate that accepts every head forces
  // canonicalHash to always take the first candidate, which is the
  // structural worst case for finding a cycle in the tables: it walks every
  // key exactly as written, not filtered down to what currently renders.
  const canRenderAnything = () => true;
  const regexExamples = ['#/systems/plumbline', '#system/plumbline', '#org/12345678'];
  const allHashes = [...Object.keys(ANCHOR), ...Object.keys(SECTION), ...regexExamples];

  for (const hash of allHashes) {
    const { settled, hops, exceeded } = resolveFixedPoint(hash, canRenderAnything);
    assert.ok(!exceeded,
      `${hash} did not terminate within the 10-hop cap (took ${hops} hop(s), stuck at ${settled})`);
  }
});

// firstServable is canonicalHash's picking logic pulled out as a small pure
// helper, for callers with an ordered list of candidate destinations and no
// route to redirect through -- such as renderTabbar in app/assets/shell.js,
// picking which of a tab's candidate hrefs to render. Task 7 gave "compare"
// and "about" real handlers, so the first two lists below now resolve to
// their own first entry under today's ROUTER_HEADS; the third case keeps a
// head nothing will ever route to as the rejected candidate, so the actual
// picking logic (skip what the predicate rejects, take the first accepted)
// is still exercised rather than the assertion becoming vacuous.
test('firstServable picks the first candidate the router can render today', () => {
  assert.equal(firstServable(['#/compare', '#/places'], canRenderToday), '#/compare');
  assert.equal(firstServable(['#/about', '#/method'], canRenderToday), '#/about');
  assert.equal(firstServable(['#/nonsense', '#/places'], canRenderToday), '#/places');
});

test('firstServable accepts a single string as well as a list', () => {
  assert.equal(firstServable('#/', canRenderToday), '#/');
});

test('firstServable returns null when no candidate can render', () => {
  assert.equal(firstServable(['#/nowhere'], canRenderToday), null);
});

test('every candidate list in DEFAULTS.tabs resolves to a route under today\'s ROUTER_HEADS', () => {
  // Read DEFAULTS.tabs out of shell.js as text, the same way the ROUTER_HEADS
  // and FALLBACK_HEADS tests above read route() and FALLBACK_HEADS, so this
  // fails if someone adds a bottom-bar tab whose candidates all point
  // nowhere the router can render today.
  const here = path.dirname(fileURLToPath(import.meta.url));
  const shellPath = path.join(here, '../../app/assets/shell.js');
  const src = fs.readFileSync(shellPath, 'utf8');

  const tabsMatch = /tabs:\s*\[/.exec(src);
  assert.ok(tabsMatch, 'could not find DEFAULTS.tabs in shell.js');

  // Walk bracket depth from the opening "[" to its match, rather than a
  // single regex, since each tab item nests its own candidate-href array
  // inside the outer tabs array.
  let depth = 0, end = -1;
  for (let i = tabsMatch.index + tabsMatch[0].length - 1; i < src.length; i++) {
    if (src[i] === '[') depth++;
    else if (src[i] === ']') { depth--; if (depth === 0) { end = i; break; } }
  }
  assert.ok(end > -1, 'could not find the end of DEFAULTS.tabs in shell.js');
  const tabsSrc = src.slice(tabsMatch.index, end + 1);

  // Each tab item's own candidate-href array has no brackets nested inside
  // it, so a bracket pair containing no further brackets is exactly one
  // tab's candidate list (the item wrapper and the outer tabs array both
  // contain nested brackets, so this does not match them).
  const candidateLists = (tabsSrc.match(/\[[^[\]]*\]/g) || [])
    .map(list => [...list.matchAll(/'([^']*)'/g)].map(m => m[1]))
    .filter(list => list.length);

  assert.ok(candidateLists.length >= 3,
    `expected at least 3 tab candidate lists in DEFAULTS.tabs, found ${candidateLists.length}`);
  for (const candidates of candidateLists) {
    const winner = firstServable(candidates, canRenderToday);
    assert.ok(winner,
      `tab candidates ${JSON.stringify(candidates)} have no route ROUTER_HEADS can render today`);
  }
});

test('every hardcoded #/ link in shell.js and app/index.html resolves to a head ROUTER_HEADS can serve', () => {
  // This is the structural guard for a defect that has recurred in this
  // project: a link pointing at a route head with no handler in route()
  // yet, which dead-ends on "No such view" instead of degrading to
  // something that renders today. The cure the project already has is
  // firstServable(candidates, canRender), which walks an ordered list of
  // candidate destinations and picks the first one the router can serve,
  // upgrading itself once a later task adds the missing handler.
  //
  // One occurrence of this defect lived outside shell.js entirely: the
  // front page's three doors in app/index.html point straight at
  // #/compare, #/unusual and #/about, none of which route() served at the
  // time. A test that reads only shell.js cannot see a defect sitting in
  // markup, so this test reads both files with the same rule.
  //
  // This test reads each file as text, finds every href="#/..." literal --
  // including ones built with template literals, such as
  // href="#/places/${code}" -- and reduces each to its head, the first path
  // segment after #/. A segment that is entirely a template expression
  // (e.g. the "${it.id}" in href="#/${it.id}") has no value known statically,
  // so it is treated as a wildcard rather than a literal head and is not
  // checked. Every literal head found must already be in ROUTER_HEADS, or
  // be provably resolved at render time:
  //
  //  - in shell.js, by a firstServable(...) call on that same line (the
  //    degrade-and-upgrade pattern renderTabbar and buildHome both use);
  //  - in app/index.html, whose static markup cannot call firstServable
  //    itself, by carrying an id that buildHome() in shell.js looks up
  //    (via $(...) or getElementById) and, within a few lines of that
  //    lookup, resolves through firstServable/pick -- i.e. real, working
  //    code that overwrites the static default at render time, not a
  //    coincidental id or comment placed only to satisfy this test.
  //
  // A raw link straight to an unservable head with no such evidence fails
  // here, rather than only being caught by hand at review time.
  const here = path.dirname(fileURLToPath(import.meta.url));
  const shellPath = path.join(here, '../../app/assets/shell.js');
  const indexPath = path.join(here, '../../app/index.html');
  const shellSrc = fs.readFileSync(shellPath, 'utf8');
  const indexSrc = fs.readFileSync(indexPath, 'utf8');

  // buildHome() is where app/index.html's static door links get overwritten
  // at render time. Extract its body the same way the ROUTER_HEADS test
  // above extracts route()'s -- start at the function's own opening brace,
  // end at the next function's -- so the id-coverage check below only
  // credits a real call inside buildHome, not a coincidental match
  // anywhere else in the file.
  const buildHomeMatch = /function\s+buildHome\s*\(\s*\)\s*\{/.exec(shellSrc);
  assert.ok(buildHomeMatch, 'could not find function buildHome() in shell.js');
  const buildHomeStart = buildHomeMatch.index;
  const buildPlacePageMatch = /function\s+buildPlacePage\s*\(/.exec(shellSrc.slice(buildHomeStart));
  assert.ok(buildPlacePageMatch, 'could not find the end of buildHome() in shell.js');
  const buildHomeLines = shellSrc.slice(buildHomeStart, buildHomeStart + buildPlacePageMatch.index).split('\n');

  // True when buildHome() looks up this exact id (by $('#id') or
  // getElementById('id')) and, within the next couple of lines, resolves
  // its href through firstServable (aliased locally as "pick").
  const idResolvedInBuildHome = (id) => {
    const lookup = new RegExp(`\\$\\(\\s*['"]#${id}['"]\\s*\\)|getElementById\\(\\s*['"]${id}['"]\\s*\\)`);
    for (let i = 0; i < buildHomeLines.length; i++) {
      if (!lookup.test(buildHomeLines[i])) continue;
      const nearby = buildHomeLines.slice(i, i + 3).join('\n');
      if (/\b(firstServable|pick)\(/.test(nearby)) return true;
    }
    return false;
  };

  // The captured group excludes newlines and quotes, so a match can never
  // straddle more than the one line its href="..." attribute is written on.
  const linkPattern = /href="(#\/[^"\n]*)"/g;
  const isWildcardSegment = (segment) => /^\$\{[^}]*\}$/.test(segment);

  const lineNumberAt = (src, index) => src.slice(0, index).split('\n').length;
  const lineTextAt = (src, index) => {
    const start = src.lastIndexOf('\n', index) + 1;
    const end = src.indexOf('\n', index);
    return src.slice(start, end === -1 ? src.length : end).trim();
  };

  const failures = [];

  const scan = (label, src, isCovered) => {
    linkPattern.lastIndex = 0;
    let m;
    while ((m = linkPattern.exec(src)) !== null) {
      const linkText = m[0];
      const target = m[1];
      const afterHash = target.replace(/^#\//, '');
      const head = afterHash.split('/')[0] || '';

      if (isWildcardSegment(head)) continue; // value not known statically, cannot be checked
      if (ROUTER_HEADS.has(head)) continue;

      const line = lineTextAt(src, m.index);
      if (isCovered(line)) continue;

      failures.push(`${label}:${lineNumberAt(src, m.index)}: ${linkText} -- head "${head}" is not in ` +
        `ROUTER_HEADS and is not provably resolved at render time`);
    }
  };

  scan('app/assets/shell.js', shellSrc,
    (line) => line.includes('firstServable(')); // resolved dynamically on this line

  scan('app/index.html', indexSrc, (line) => {
    const idMatch = /\bid="([\w-]+)"/.exec(line);
    return !!idMatch && idResolvedInBuildHome(idMatch[1]);
  });

  assert.deepEqual(failures, [],
    `found hardcoded link(s) pointing at a route head route() cannot serve:\n` +
    failures.join('\n'));
});
