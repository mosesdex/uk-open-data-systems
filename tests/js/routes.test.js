import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { canonicalHash, ANCHOR, SECTION, ROUTER_HEADS } from '../../app/assets/lib/routes.js';

// ROUTER_HEADS, exported by routes.js, is the authoritative list of heads
// route() in app/assets/shell.js actually dispatches today. The test below
// titled "ROUTER_HEADS matches..." reads shell.js and enforces that the two
// stay in step, so importing it here (instead of a hand-copied literal set)
// is what keeps these tests meaning what they say.
const canRenderToday = (head) => ROUTER_HEADS.has(head);

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

test('#/systems/plumbline is left alone while questions has no handler', () => {
  // Regression: today's router cannot render "questions" yet, so redirecting
  // there would swap a working URL for "No such view". The 150 outreach
  // emails that link here must keep rendering something.
  assert.equal(canonicalHash('#/systems/plumbline', canRenderToday), null);
});

test('#/systems/plumbline redirects once questions can render', () => {
  const canRenderWithQuestions = (head) => canRenderToday(head) || head === 'questions';
  assert.equal(canonicalHash('#/systems/plumbline', canRenderWithQuestions), '#/questions/plumbline');
});

test('#/method is left alone while about has no handler', () => {
  assert.equal(canonicalHash('#/method', canRenderToday), null);
});

test('#/method redirects once about can render', () => {
  const canRenderWithAbout = (head) => canRenderToday(head) || head === 'about';
  assert.equal(canonicalHash('#/method', canRenderWithAbout), '#/about');
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

  const routeStart = src.indexOf('function route() {');
  assert.ok(routeStart !== -1, 'could not find function route() in shell.js');
  const routeEnd = src.indexOf('function safely(fn, targetSel) {', routeStart);
  assert.ok(routeEnd !== -1, 'could not find the end of route() in shell.js');
  const routeSrc = src.slice(routeStart, routeEnd);

  const dispatched = new Set();
  const pattern = /head === '([^']*)'/g;
  let m;
  while ((m = pattern.exec(routeSrc)) !== null) dispatched.add(m[1]);

  assert.deepEqual(dispatched, ROUTER_HEADS,
    `heads route() dispatches (${JSON.stringify([...dispatched].sort())}) must match ` +
    `ROUTER_HEADS (${JSON.stringify([...ROUTER_HEADS].sort())})`);
});

test('every legacy fragment redirects somewhere real, or already renders itself', () => {
  // Regression for the "guard suppresses the redirect and the raw fragment
  // is not dispatchable either" hole: with the real ROUTER_HEADS predicate,
  // none of these thirteen published fragments should hit the "No such
  // view" fallback.
  const canRenderReal = (head) => ROUTER_HEADS.has(head);
  const fragments = [
    '#top', '#hero', '#spines', '#chains', '#compare', '#feeds', '#honesty',
    '#place', '#systems', '#kpis', '#org/12345678', '#search', '#system/plumbline',
  ];

  const failures = [];
  for (const fragment of fragments) {
    const result = canonicalHash(fragment, canRenderReal);
    if (result === null) {
      const ownHead = fragment.replace(/^#\/?/, '').split('/')[0];
      if (!ROUTER_HEADS.has(ownHead)) {
        failures.push(`${fragment} -> null, but its own head "${ownHead}" is not in ROUTER_HEADS`);
      }
    } else {
      const head = result.slice(2).split('/')[0];
      if (!ROUTER_HEADS.has(head)) {
        failures.push(`${fragment} -> ${result}, whose head "${head}" is not in ROUTER_HEADS`);
      }
    }
  }

  assert.deepEqual(failures, [], `dead-ending fragments:\n${failures.join('\n')}`);
});
