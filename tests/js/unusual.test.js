import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { unusualRows, unusualTotal } from '../../app/assets/lib/unusual.js';

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

test('the lastmile comparator names the population it actually covers', () => {
  // lastmile.other_pct is coverage among premises outside new-build
  // postcodes (platform/groundtruth/systems/lastmile.py), compared here
  // against a place's all-premises figure, a different population, so the
  // label must say "outside new-build postcodes" rather than a flat
  // "the national share".
  const row = unusualRows(PAYLOAD).find(r => r.question === 'lastmile');
  assert.match(row.againstLabel, /outside new-build postcodes/);
});

test('the total counts every diverging pair, not just the capped display list', () => {
  // The fixture has 4 places and 3 comparators; not every place carries every
  // question, so the total is the count of qualifying pairs, not 4 * 3.
  const total = unusualTotal(PAYLOAD);
  assert.equal(total, unusualRows(PAYLOAD, total).length);
  assert.ok(total > unusualRows(PAYLOAD, 1).length, 'the total is not itself capped');
});
