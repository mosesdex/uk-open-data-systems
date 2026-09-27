import test from 'node:test';
import assert from 'node:assert/strict';
import { sectorKey, sectorDistricts } from '../../app/assets/lib/postcode.js';

const INDEX = { sectors: { SW1A1: ['E09000033'], GU216: ['E07000217', 'E07000214'] } };

test('a full postcode reduces to its sector', () => {
  assert.equal(sectorKey('SW1A 1AA'), 'SW1A1');
  assert.equal(sectorKey('sw1a1aa'), 'SW1A1');
  assert.equal(sectorKey('  GU21   6AC '), 'GU216');
});

test('something that is not a postcode has no sector', () => {
  assert.equal(sectorKey('Camden'), null);
  assert.equal(sectorKey(''), null);
  assert.equal(sectorKey(null), null);
  assert.equal(sectorKey('SW1A'), null);
});

test('an unambiguous sector returns one district', () => {
  assert.deepEqual(sectorDistricts('SW1A 1AA', INDEX), ['E09000033']);
});

test('an ambiguous sector returns every candidate, dominant first', () => {
  assert.deepEqual(sectorDistricts('GU21 6AC', INDEX), ['E07000217', 'E07000214']);
});

test('a sector the index does not carry returns nothing', () => {
  assert.deepEqual(sectorDistricts('ZZ99 9ZZ', INDEX), []);
});

test('a sector outside England still resolves, so the caller can say where', () => {
  // The index carries Wales and Scotland on purpose. This module reports what
  // the index holds; deciding that England only is covered is the caller's job.
  const wales = { sectors: { CF101: ['W06000015'] } };
  assert.deepEqual(sectorDistricts('CF10 1AA', wales), ['W06000015']);
});

test('a missing index returns nothing rather than throwing', () => {
  assert.deepEqual(sectorDistricts('SW1A 1AA', null), []);
  assert.deepEqual(sectorDistricts('SW1A 1AA', {}), []);
});
