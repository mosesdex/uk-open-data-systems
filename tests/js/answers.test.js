import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { placeAnswers, placeAuthority, placeAbsences } from '../../app/assets/lib/answers.js';

const PAYLOAD = JSON.parse(readFileSync(new URL('./fixtures/payload.json', import.meta.url)));
const byLad = PAYLOAD.places.byLad;
const CODES = Object.keys(byLad);

// The real, published payload, not the four-place fixture above: whether a
// question is genuinely national, genuinely the county's, or simply absent
// for one place only shows up at real scale, across all 318 places and the
// app's full 13-question list (four of which, sentinel, junction, watchman
// and baseline, carry no per-place object anywhere and are not in the
// fixture at all). Asserting the classification against invented fixture
// numbers would prove nothing about what a reader actually sees.
const REAL_PAYLOAD = JSON.parse(
  readFileSync(new URL('../../app/data/platform.json', import.meta.url))
);
const REAL_CODES = Object.keys(REAL_PAYLOAD.places.byLad);
// Mirrors app/assets/shared.js's SYSTEMS ids, which shell.js reads to build
// this same list: not importable here, since shared.js is a classic script,
// not a module.
const ALL_IDS = ['catchment', 'sentinel', 'highwater', 'plumbline', 'junction', 'ledger',
  'bellwether', 'sightline', 'lastmile', 'bulwark', 'watchman', 'compass', 'baseline'];

/* A figure is either a number or a preformatted string built from one, so the
   check below reduces both to the number and looks for it in the payload. */
const numeric = figure => typeof figure === 'number'
  ? figure : Number(String(figure).replace(/[^0-9.-]/g, ''));

const valuesOf = obj => Object.values(obj).filter(v => typeof v === 'number');

test('every figure returned is a figure the payload holds for that place', () => {
  for (const code of CODES) {
    for (const a of placeAnswers(code, PAYLOAD)) {
      const block = byLad[code][a.id];
      assert.ok(block, `${code} has a ${a.id} block`);
      assert.ok(valuesOf(block).includes(numeric(a.figure)),
        `${code}/${a.id}: figure ${a.figure} is not in ${JSON.stringify(block)}`);
    }
  }
});

test('every comparator returned is a figure the payload holds, locally or nationally', () => {
  for (const code of CODES) {
    for (const a of placeAnswers(code, PAYLOAD)) {
      if (a.against === null) { assert.equal(a.againstLabel, null); continue; }
      assert.equal(typeof a.against, 'number');
      assert.ok(a.againstLabel && a.againstLabel.length > 3, 'a comparator is labelled');
      const local = valuesOf(byLad[code][a.id]);
      const national = JSON.stringify(PAYLOAD.systems).includes(String(a.against));
      assert.ok(local.includes(a.against) || national,
        `${code}/${a.id}: comparator ${a.against} is in neither the place nor the national block`);
    }
  }
});

test('a question with no data for a place returns no entry', () => {
  // Camden carries no plumbline block in the fixture, and no bulwark, highwater,
  // sightline or ledger either.
  const ids = placeAnswers('E09000007', PAYLOAD).map(a => a.id);
  assert.ok(!ids.includes('plumbline'), 'no plumbline entry for a place without one');
  for (const id of ['bulwark', 'highwater', 'sightline', 'ledger']) {
    assert.ok(!ids.includes(id), `no ${id} entry`);
    assert.equal(byLad.E09000007[id], undefined, `and the fixture really has no ${id}`);
  }
  assert.deepEqual(ids.sort(), ['bellwether', 'catchment', 'compass', 'lastmile']);
});

test('a block whose figure is null in the payload is not an answer', () => {
  // Pembrokeshire has a catchment block, but no school publishes both figures
  // there, so utilisation_pct is null. A page must not print an empty figure.
  assert.equal(byLad.W06000009.catchment.utilisation_pct, null);
  const ids = placeAnswers('W06000009', PAYLOAD).map(a => a.id);
  assert.deepEqual(ids, ['lastmile']);
});

test('an entry is never returned for _capacity or _systems', () => {
  assert.ok(byLad.E07000032._capacity, 'the fixture carries the internal keys');
  assert.ok(byLad.E07000032._systems, 'the fixture carries the internal keys');
  for (const code of CODES) {
    for (const a of placeAnswers(code, PAYLOAD)) {
      assert.ok(!a.id.startsWith('_'), `${a.id} is not a question`);
      assert.ok(!['_capacity', '_systems'].includes(a.id));
    }
  }
});

test('a county figure shown on a district says whose figure it is', () => {
  const answers = placeAnswers('E07000032', PAYLOAD);
  for (const id of ['compass', 'bellwether']) {
    const block = byLad.E07000032[id];
    assert.equal(block.figure_for, 'county', `the fixture ${id} is a county figure`);
    const a = answers.find(x => x.id === id);
    assert.ok(a.caveat.includes(block.authority_name), `${id} caveat names ${block.authority_name}`);
    assert.match(a.caveat, /County Council figure, shared by each of its districts/);
  }
});

test('the regulator\u2019s brand marker is not printed as part of a provider name', () => {
  const a = placeAnswers('E09000007', PAYLOAD).find(x => x.id === 'bellwether');
  assert.equal(byLad.E09000007.bellwether.group_name, 'BRAND Shaw Healthcare');
  assert.ok(a.caveat.includes('Shaw Healthcare holds 120 of 510 beds'), a.caveat);
  assert.doesNotMatch(a.caveat, /BRAND /);
  assert.match(a.caveat, /brand field/);          // how it was grouped is still said
});

test('a place that publishes its own figure carries no county attribution', () => {
  for (const code of ['E09000007', 'E06000001']) {
    for (const a of placeAnswers(code, PAYLOAD)) {
      assert.doesNotMatch(a.caveat || '', /County Council figure/,
        `${code}/${a.id} should not claim a county figure`);
    }
  }
});

test('every entry carries a caveat and a link to how it is computed', () => {
  for (const code of CODES) {
    for (const a of placeAnswers(code, PAYLOAD)) {
      assert.ok(a.caveat && a.caveat.length > 10, `${code}/${a.id} has a caveat`);
      assert.equal(a.method, `#/questions/${a.id}`);
      assert.ok(a.name && a.question.length > 10, `${code}/${a.id} is asked in plain English`);
      assert.match(a.question, /\?$/, `${code}/${a.id} asks a question`);
    }
  }
});

test('no returned string carries an invented number or an empty slot', () => {
  for (const code of CODES) {
    for (const a of placeAnswers(code, PAYLOAD)) {
      for (const s of [a.name, a.question, a.caveat, a.againstLabel, a.method]) {
        if (s === null) continue;
        assert.doesNotMatch(s, /undefined|NaN|null/, `${code}/${a.id}: ${s}`);
      }
    }
  }
});

test('no string contains an em dash or an en dash', () => {
  for (const code of CODES) {
    for (const a of placeAnswers(code, PAYLOAD)) {
      for (const s of [a.name, a.question, a.caveat, a.againstLabel, a.method,
                       typeof a.figure === 'string' ? a.figure : '']) {
        assert.doesNotMatch(String(s || ''), /\u2014|\u2013/, `dash in ${code}/${a.id}: ${s}`);
      }
    }
    assert.doesNotMatch(String(placeAuthority(code, PAYLOAD) || ''), /\u2014|\u2013/);
  }
});

test('an unknown place answers nothing rather than guessing', () => {
  assert.deepEqual(placeAnswers('E99999999', PAYLOAD), []);
  assert.deepEqual(placeAnswers('', PAYLOAD), []);
  assert.deepEqual(placeAnswers('E07000032', null), []);
});

test('the sharpest known figures come through exactly as published', () => {
  const amber = placeAnswers('E07000032', PAYLOAD);
  const plumbline = amber.find(a => a.id === 'plumbline');
  assert.equal(plumbline.figure, 8.7);
  assert.equal(plumbline.unit, '%');
  assert.equal(plumbline.against, 97.6);
  assert.match(plumbline.againstLabel, /published measure for the same authority/);

  const catchment = amber.find(a => a.id === 'catchment');
  assert.equal(catchment.figure, 91);
  assert.equal(catchment.against, 89.5);          // systems.catchment.national.utilisation_pct

  const ledger = amber.find(a => a.id === 'ledger');
  assert.equal(ledger.figure, '£5,099,873');      // ledger.total_amount, not rounded
  assert.equal(ledger.against, null);
  assert.equal(ledger.againstLabel, null);
});

test('the authority type comes from the payload, and is silent when it cannot', () => {
  // A district whose capacity figure belongs to its county council.
  assert.equal(byLad.E07000032._capacity.figure_for, 'county');
  assert.match(placeAuthority('E07000032', PAYLOAD), /^District in a two-tier area\./);
  assert.match(placeAuthority('E07000032', PAYLOAD), /Derbyshire County Council/);

  // A London borough and a unitary each carry their own.
  for (const code of ['E09000007', 'E06000001']) {
    assert.equal(byLad[code]._capacity.authority, code);
    assert.match(placeAuthority(code, PAYLOAD), /^Single-tier authority\./);
  }

  // No _capacity in the payload, so nothing is claimed.
  assert.equal(byLad.W06000009._capacity, undefined);
  assert.equal(placeAuthority('W06000009', PAYLOAD), null);
  assert.equal(placeAuthority('E99999999', PAYLOAD), null);
});

test('a question never published per place is classified as national for every place', () => {
  // sentinel, junction, watchman and baseline never carry a per-place object
  // anywhere in the real payload: they are measured only nationally, so every
  // one of the 318 places must call them national, and never upper-tier or
  // merely unanswered here.
  const neverPerPlace = ALL_IDS.filter(id =>
    !REAL_CODES.some(code => REAL_PAYLOAD.places.byLad[code][id] !== undefined));
  assert.deepEqual(neverPerPlace.sort(), ['baseline', 'junction', 'sentinel', 'watchman']);

  for (const code of REAL_CODES) {
    const a = placeAbsences(code, REAL_PAYLOAD, ALL_IDS);
    for (const id of neverPerPlace) {
      assert.ok(a.national.includes(id), `${code}: ${id} should be classified national`);
      assert.ok(!a.upperTier.includes(id), `${code}: ${id} must not be called upper-tier`);
      assert.ok(!a.noFigure.includes(id), `${code}: ${id} must not be called merely unanswered`);
    }
  }
});

test('a question published for this place is not listed as absent at all', () => {
  for (const code of REAL_CODES) {
    const shownIds = new Set(placeAnswers(code, REAL_PAYLOAD).map(x => x.id));
    const a = placeAbsences(code, REAL_PAYLOAD, ALL_IDS);
    for (const id of shownIds) {
      assert.ok(!a.national.includes(id), `${code}/${id}: answered, so not national`);
      assert.ok(!a.upperTier.includes(id), `${code}/${id}: answered, so not upper-tier`);
      assert.ok(!a.noFigure.includes(id), `${code}/${id}: answered, so not unanswered`);
    }
  }
});

test('every absence lands in exactly one bucket, covering every missing question', () => {
  for (const code of REAL_CODES) {
    const shownIds = new Set(placeAnswers(code, REAL_PAYLOAD).map(x => x.id));
    const a = placeAbsences(code, REAL_PAYLOAD, ALL_IDS);
    const missing = ALL_IDS.filter(id => !shownIds.has(id));
    const buckets = [...a.national, ...a.upperTier, ...a.noFigure];
    assert.deepEqual(buckets.slice().sort(), missing.slice().sort(), `${code}: buckets cover exactly what's missing`);
    assert.equal(new Set(buckets).size, buckets.length, `${code}: no question is placed in two buckets`);
  }
});

test('a single-tier authority never blames the county for its own missing questions', () => {
  // Camden and Hartlepool are each their own upper tier (placeAuthority calls
  // them "Single-tier authority... this council's own"), so nothing missing
  // for them can honestly be called the county's. Every one of their missing
  // questions is published for some other place in the fixture (Amber Valley
  // carries all nine), so the absence here is real, just never above-district.
  for (const code of ['E09000007', 'E06000001']) {
    assert.match(placeAuthority(code, PAYLOAD), /^Single-tier authority\./);
    const shownIds = new Set(placeAnswers(code, PAYLOAD).map(x => x.id));
    const questionIds = ['plumbline', 'catchment', 'lastmile', 'compass', 'bellwether',
      'bulwark', 'highwater', 'sightline', 'ledger'];
    const missingQuestions = questionIds.filter(id => !shownIds.has(id));
    assert.ok(missingQuestions.length > 0, `${code}: fixture should leave something missing to test`);

    const a = placeAbsences(code, PAYLOAD, ALL_IDS);
    assert.deepEqual(a.upperTier, [], `${code}: a single-tier authority has no upper-tier absence`);
    assert.equal(a.countyName, null);
    for (const id of missingQuestions) {
      assert.ok(a.noFigure.includes(id), `${code}/${id}: published elsewhere, absent here, no cause invented`);
    }
  }
});

test('an unknown place has no absences rather than a guessed one', () => {
  assert.equal(placeAbsences('E99999999', PAYLOAD, ALL_IDS), null);
  assert.equal(placeAbsences('E07000032', null, ALL_IDS), null);
});
