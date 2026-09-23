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
