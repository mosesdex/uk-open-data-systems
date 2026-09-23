import test from 'node:test';
import assert from 'node:assert/strict';
import { canonicalHash, ANCHOR, SECTION } from '../../app/assets/lib/routes.js';

// The heads route() in app/assets/shell.js actually dispatches today. Kept in
// sync by hand with the HEADS constant in shell.js, which is the thing that
// matters in the running app; this list only needs to match it for the tests
// below to mean what they say.
const TODAYS_ROUTER = new Set(['', 'places', 'systems', 'orgs', 'sources', 'method', 'search']);
const canRenderToday = (head) => TODAYS_ROUTER.has(head);

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
