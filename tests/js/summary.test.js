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
    assert.doesNotMatch(line, /—|–/, `dash in: ${line}`);
  }
});
