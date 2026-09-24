import test from 'node:test';
import assert from 'node:assert/strict';
import { rankFor, rankSentence } from '../../app/assets/lib/rank.js';

const lad = (pct) => ({ lastmile: { gigabit_pct: pct, premises: 1000 } });
const PAYLOAD = {
  systems: {},
  places: { byLad: { A: lad(90), B: lad(80), C: lad(70), D: { catchment: { utilisation_pct: 95, measured_pct: 99 } } } },
};

test('the highest figure ranks first', () => {
  const r = rankFor('A', 'lastmile', PAYLOAD);
  assert.equal(r.rank, 1);
  assert.equal(r.of, 3);
});

test('the denominator counts only districts holding that figure', () => {
  // D has no lastmile block, so it is not in the denominator
  assert.equal(rankFor('C', 'lastmile', PAYLOAD).of, 3);
});

test('a district with no figure for the question has no rank', () => {
  assert.equal(rankFor('D', 'lastmile', PAYLOAD), null);
  assert.equal(rankFor('ZZ', 'lastmile', PAYLOAD), null);
});

test('ties share a rank rather than being ordered arbitrarily', () => {
  const tied = { systems: {}, places: { byLad: { A: lad(80), B: lad(80), C: lad(70) } } };
  assert.equal(rankFor('A', 'lastmile', tied).rank, 1);
  assert.equal(rankFor('B', 'lastmile', tied).rank, 1);
  assert.equal(rankFor('C', 'lastmile', tied).rank, 3);
});

test('the sentence names the denominator, never 318', () => {
  const s = rankSentence(rankFor('B', 'lastmile', PAYLOAD));
  assert.match(s, /2nd of 3 districts/);
  assert.doesNotMatch(s, /318/);
});

test('polarity is declared per question, not inferred from the number', () => {
  const one = { systems: {}, places: { byLad: { D: PAYLOAD.places.byLad.D, E: { catchment: { utilisation_pct: 80, measured_pct: 99 } } } } };
  assert.equal(rankFor('D', 'catchment', one).polarity, 'high-is-worse');
  assert.equal(rankFor('A', 'lastmile', PAYLOAD).polarity, 'high-is-better');
});

test('a question whose polarity is genuinely ambiguous is left unjudged', () => {
  const p = { systems: {}, places: { byLad: {
    A: { compass: { projected_change_pct: 12 } }, B: { compass: { projected_change_pct: 4 } } } } };
  assert.equal(rankFor('A', 'compass', p).polarity, 'none');
});

test('the sentence never says better or worse, whatever the polarity', () => {
  // The rank states position. Whether that position is good is the reader's
  // call, and the caveat beside it is what they need to make it.
  for (const code of ['A', 'B', 'C']) {
    assert.doesNotMatch(rankSentence(rankFor(code, 'lastmile', PAYLOAD)), /better|worse/);
  }
});

test('a rank of one district says so rather than claiming a ranking', () => {
  const only = { systems: {}, places: { byLad: { A: lad(90) } } };
  assert.equal(rankSentence(rankFor('A', 'lastmile', only)), null);
});

// The brief's ORDINAL guard (r100 >= 11 && r100 <= 13) exists specifically to
// keep the teens from reading as "11st, 12nd, 13rd". These ranks are only
// reachable through rankSentence, so the wording is exercised the same way a
// reader sees it rather than by reaching into the unexported helper.
test('ordinal suffixes are correct for the teens and the round numbers after them', () => {
  const many = { systems: {}, places: { byLad: {} } };
  // 111 districts: rank 1 goes to the top figure, rank 111 to the bottom, so a
  // figure of (112 - rank) at code Rn puts Rn exactly at that rank.
  for (let i = 1; i <= 111; i++) many.places.byLad['R' + i] = lad(112 - i);

  const wantedAt = { 1: '1st', 2: '2nd', 3: '3rd', 4: '4th', 11: '11th', 12: '12th', 13: '13th', 21: '21st', 101: '101st', 111: '111th' };
  for (const [rank, ordinal] of Object.entries(wantedAt)) {
    const code = 'R' + rank;
    const s = rankSentence(rankFor(code, 'lastmile', many));
    assert.match(s, new RegExp('^' + ordinal + ' of 111 districts'), `rank ${rank} should read ${ordinal}, got: ${s}`);
  }
});
