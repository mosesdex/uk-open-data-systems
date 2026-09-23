import test from 'node:test';
import assert from 'node:assert/strict';
import { matchPlaces, looksLikePostcode } from '../../app/assets/lib/places.js';

const NAMES = {
  E07000032: 'Amber Valley',
  E06000001: 'Hartlepool',
  E09000007: 'Camden',
  E07000223: 'Adur',
  E08000003: 'Manchester',
  E07000117: 'Burnley',
};

test('an exact name comes first', () => {
  const hits = matchPlaces('Camden', NAMES);
  assert.equal(hits[0].code, 'E09000007');
  assert.equal(hits[0].name, 'Camden');
});

test('a prefix beats a substring', () => {
  const hits = matchPlaces('man', NAMES).map(h => h.name);
  assert.equal(hits[0], 'Manchester');           // starts with
  assert.ok(hits.length >= 1);
});

test('matching ignores case and surrounding space', () => {
  assert.equal(matchPlaces('  aMbEr  ', NAMES)[0].name, 'Amber Valley');
});

test('no query returns nothing, rather than everything', () => {
  assert.deepEqual(matchPlaces('', NAMES), []);
  assert.deepEqual(matchPlaces('   ', NAMES), []);
});

test('an unknown place returns nothing', () => {
  assert.deepEqual(matchPlaces('Atlantis', NAMES), []);
});

test('the limit is honoured', () => {
  assert.equal(matchPlaces('a', NAMES, 2).length, 2);
});

test('a postcode is recognised so the field can say what it needs', () => {
  for (const pc of ['DE5 3TZ', 'de53tz', 'SW1A 1AA', 'M1 1AE']) {
    assert.equal(looksLikePostcode(pc), true, `${pc} should look like a postcode`);
  }
  for (const not of ['Camden', 'Amber Valley', '', 'E07000032']) {
    assert.equal(looksLikePostcode(not), false, `${not} should not`);
  }
});
