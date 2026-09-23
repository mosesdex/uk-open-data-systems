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
