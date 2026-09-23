import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { unusualRows, unusualTotal } from '../../app/assets/lib/unusual.js';

const PAYLOAD = JSON.parse(readFileSync(new URL('./fixtures/payload.json', import.meta.url)));

// The real, published payload, not the four-place fixture above: the spread
// across questions this behaviour exists to fix only shows up at real scale,
// where plumbline's gaps genuinely do run 80 to 98 points against catchment
// and lastmile's single digits. Asserting the spread against invented
// fixture numbers would prove nothing about what a reader actually sees.
const REAL_PAYLOAD = JSON.parse(
  readFileSync(new URL('../../app/data/platform.json', import.meta.url))
);

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

// The behaviour item F exists for: plumbline's gaps run far wider than
// catchment's or lastmile's, so a single global sort by gap used to crowd
// every one of the fifty rows with plumbline alone. These tests check the
// outcome a reader sees, not the grouping/allocation mechanism that produces
// it, against the real published data.

test('more than one question appears among the returned rows, at the real scale', () => {
  const questions = new Set(unusualRows(REAL_PAYLOAD).map(r => r.question));
  assert.ok(questions.size > 1,
    `expected rows from more than one question, got only: ${[...questions]}`);
});

test('no single question fills every returned row', () => {
  const rows = unusualRows(REAL_PAYLOAD);
  const counts = {};
  for (const r of rows) counts[r.question] = (counts[r.question] || 0) + 1;
  for (const [question, count] of Object.entries(counts)) {
    assert.ok(count < rows.length,
      `${question} filled all ${rows.length} rows`);
  }
});

test('within each question, rows are ordered by descending gap', () => {
  const byQuestion = {};
  for (const row of unusualRows(REAL_PAYLOAD)) {
    (byQuestion[row.question] ||= []).push(row);
  }
  for (const [question, rows] of Object.entries(byQuestion)) {
    for (let i = 1; i < rows.length; i++) {
      assert.ok(rows[i - 1].gap >= rows[i].gap,
        `${question} row ${i} (gap ${rows[i].gap}) exceeds row ${i - 1} (gap ${rows[i - 1].gap})`);
    }
  }
});

test('the number returned never exceeds the limit', () => {
  for (const limit of [0, 1, 3, 17, 50, 500]) {
    const rows = unusualRows(REAL_PAYLOAD, limit);
    assert.ok(rows.length <= limit,
      `limit ${limit} returned ${rows.length} rows`);
  }
});

test('a question with no qualifying rows contributes no empty slot and does not crash', () => {
  // Cloned from the real payload, then the national comparator one question
  // needs is removed so every place fails that question's qualifying test
  // (figure without a comparator to measure it against) -- the same "no
  // rows for this question" condition allRows() already guards against
  // elsewhere, not a fabricated figure.
  const withoutCatchment = JSON.parse(JSON.stringify(REAL_PAYLOAD));
  delete withoutCatchment.systems.catchment;

  let rows;
  assert.doesNotThrow(() => { rows = unusualRows(withoutCatchment, 50); });
  assert.ok(rows.every(r => r && Number.isFinite(r.gap)), 'no empty or malformed slot');
  assert.ok(!rows.some(r => r.question === 'catchment'), 'the empty question contributes no rows');
  assert.ok(new Set(rows.map(r => r.question)).size > 1,
    'the remaining questions still share the rows the missing one gave up');
  assert.equal(rows.length, Math.min(50, unusualTotal(withoutCatchment)));
});
