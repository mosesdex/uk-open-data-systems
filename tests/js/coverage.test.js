import test from 'node:test';
import assert from 'node:assert/strict';
import { districtChoice } from '../../app/assets/lib/coverage.js';

// Northumberland is covered, Scottish Borders is not -- the real shape of
// TD124 in the committed index (app/data/postcodes.json), the sector the
// reviewer used to reproduce the silent cross-border navigation.
const NAMES = { E06000057: 'Northumberland', E09000033: 'Westminster', E09000032: 'Wandsworth' };

test('a raw sector with one district is not ambiguous', () => {
  const choice = districtChoice(['E06000057'], NAMES);
  assert.equal(choice.ambiguous, false);
  assert.deepEqual(choice.covered, ['E06000057']);
  assert.deepEqual(choice.missing, []);
});

test('a cross-border sector is ambiguous even though only one side is covered', () => {
  // This is the case the country filter used to hide: filtering to covered
  // districts first left exactly one candidate, which read as unambiguous
  // and triggered a silent navigation. Ambiguity has to be decided from the
  // raw sector, before coverage is applied.
  const choice = districtChoice(['S12000026', 'E06000057'], NAMES);
  assert.equal(choice.ambiguous, true);
  assert.deepEqual(choice.covered, ['E06000057']);
  assert.deepEqual(choice.missing, ['S12000026']);
});

test('all five real England/Scotland border sectors are ambiguous', () => {
  // Taken from app/data/postcodes.json as it stands today.
  const sectors = {
    TD124: ['S12000026', 'E06000057'],
    TD151: ['E06000057', 'S12000026'],
    TD58: ['S12000026', 'E06000057'],
    TD90: ['S12000026', 'E06000063'],
    DG165: ['S12000006', 'E06000063'],
  };
  const names = { E06000057: 'Northumberland', E06000063: 'Cumberland' };
  for (const [sector, districts] of Object.entries(sectors)) {
    const choice = districtChoice(districts, names);
    assert.equal(choice.ambiguous, true, `${sector} should be ambiguous`);
    assert.equal(choice.covered.length, 1, `${sector} should offer exactly one covered district`);
    assert.equal(choice.missing.length, 1, `${sector} should disclose exactly one missing district`);
  }
});

test('a sector where both districts are covered is ambiguous with nothing missing', () => {
  // SW1A1: Westminster and Wandsworth, both carried by this platform. Every
  // England/Wales border sector (29 of them) is this shape too -- ambiguous,
  // but with no disclosure needed because both sides are covered.
  const choice = districtChoice(['E09000033', 'E09000032'], NAMES);
  assert.equal(choice.ambiguous, true);
  assert.deepEqual(choice.covered, ['E09000033', 'E09000032']);
  assert.deepEqual(choice.missing, []);
});

test('a sector with no covered district reports every district as missing', () => {
  const choice = districtChoice(['S12000036'], {});
  assert.equal(choice.ambiguous, false);
  assert.deepEqual(choice.covered, []);
  assert.deepEqual(choice.missing, ['S12000036']);
});

test('no districts and no names index do not throw', () => {
  assert.deepEqual(districtChoice([], NAMES), { ambiguous: false, covered: [], missing: [] });
  assert.deepEqual(districtChoice(['E06000057'], null), { ambiguous: false, covered: [], missing: ['E06000057'] });
  assert.deepEqual(districtChoice(null, NAMES), { ambiguous: false, covered: [], missing: [] });
});
