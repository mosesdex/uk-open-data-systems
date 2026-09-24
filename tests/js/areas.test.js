import test from 'node:test';
import assert from 'node:assert/strict';
import { matchAreas, areaDistricts } from '../../app/assets/lib/areas.js';

const AREAS = {
  E12000007: { name: 'London', kind: 'region', districts: ['E09000001', 'E09000007'] },
  E12000005: { name: 'West Midlands', kind: 'region', districts: new Array(30).fill('X') },
  E47000007: { name: 'West Midlands', kind: 'combined authority', districts: new Array(7).fill('X') },
};

test('an exact area name matches', () => {
  const hits = matchAreas('London', AREAS);
  assert.equal(hits.length, 1);
  assert.equal(hits[0].code, 'E12000007');
  assert.equal(hits[0].kind, 'region');
});

test('a colliding name offers both, so neither is silently preferred', () => {
  const hits = matchAreas('West Midlands', AREAS);
  assert.equal(hits.length, 2);
  const kinds = hits.map(h => h.kind).sort();
  assert.deepEqual(kinds, ['combined authority', 'region']);
});

test('matching is case insensitive and ignores surrounding space', () => {
  assert.equal(matchAreas('  london ', AREAS)[0].code, 'E12000007');
});

test('a prefix matches, so typing partly through a name finds it', () => {
  assert.equal(matchAreas('Lond', AREAS)[0].code, 'E12000007');
});

test('a query matching nothing returns nothing', () => {
  assert.deepEqual(matchAreas('Atlantis', AREAS), []);
  assert.deepEqual(matchAreas('', AREAS), []);
  assert.deepEqual(matchAreas('London', null), []);
});

test('an area reports its districts, and an unknown code reports none', () => {
  assert.equal(areaDistricts('E12000007', AREAS).length, 2);
  assert.deepEqual(areaDistricts('ZZ', AREAS), []);
  assert.deepEqual(areaDistricts('E12000007', null), []);
});
