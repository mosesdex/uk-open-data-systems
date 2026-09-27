/* Where one district sits among the others, for one question.

   A figure on its own is not a finding. "89.5% of school places in use" tells
   a reader nothing until they know whether that is unusual. This ranks a
   district against every other district that holds a figure for the same
   question, and states that denominator, because a rank out of 318 when only
   257 districts carry the figure is a false claim about the other 61.

   The figure is read through placeAnswers, not re-derived here, so there is
   one definition of what each question's figure is and no second chance to
   disagree with the page it annotates.

   Polarity is declared per question rather than assumed. Being high is bad for
   spills and for school place pressure, good for gigabit coverage, and neither
   for a projected change in plan numbers. A question with no honest polarity
   is ranked and left unjudged.

   Rankability is declared per question too, separately from polarity: a
   question can have an honest direction and still not be safe to rank, when
   its per-district bases are too uneven to compare like for like. See
   RANKABLE below. */

import { placeAnswers } from './answers.js';

const POLARITY = {
  plumbline: 'high-is-better',
  catchment: 'high-is-worse',
  lastmile: 'high-is-better',
  baseline: 'high-is-worse',
  bulwark: 'high-is-better',
  highwater: 'high-is-worse',
  sightline: 'high-is-worse',
  bellwether: 'high-is-worse',
  ledger: 'high-is-better',
  compass: 'none',
  junction: 'high-is-better',
  sentinel: 'high-is-worse',
};

/* Whether a question's per-district figures are even comparable enough to
   rank against each other, declared per question rather than inferred from
   a sample-size cutoff.

   Sentinel declines. Measured against the regenerated payload: 199 districts
   carry a figure, the median district has 4 awards and the maximum has 200.
   Sutton's figure rests on 3 awards (1 skipped open competition, so it reads
   33.3%) and used to be shown as "17th of 199 districts": a base that thin
   moves tens of places on one award either way, so the rank on top of it was
   false precision, not a finding, and a reporter could have quoted "17th
   worst in England for uncompetitive procurement" from three contracts. The
   figure and its caveat already say the base is small; only the rank is
   dropped here, because a district-to-district comparison of 3-award and
   200-award bases is not like for like no matter how it is phrased.

   Junction keeps its rank despite covering only 31 districts, because those
   31 are comparable with each other in a way Sentinel's are not: all 31 come
   from Northern Powergrid's register (the one of the four distribution
   operators that publishes rows at all) on one shared definition, not from a
   sampled corpus of wildly uneven per-district counts.

   No numeric threshold (10 awards? 20?) is declared here on purpose: a
   threshold would be arbitrary and would need defending per question, and
   would drift silently out of date as the corpus grows. This is a judgement
   about the data, made once, in the open, and it applies to Sentinel alone
   today. Whoever reconsiders it should re-measure the distribution above
   first, not just flip the flag back. */
const RANKABLE = {
  sentinel: false,
};

const ORDINAL = n => {
  const r100 = n % 100, r10 = n % 10;
  if (r100 >= 11 && r100 <= 13) return n + 'th';
  return n + (r10 === 1 ? 'st' : r10 === 2 ? 'nd' : r10 === 3 ? 'rd' : 'th');
};

/* Every district's figure for one question.

   A place page calls rankFor once per answer, and each call would otherwise
   walk all 318 districts through placeAnswers: thirteen answers on one page is
   over four thousand traversals of the payload. The distribution for a whole
   payload is built once, on the first question that needs it, and reused.

   Keyed by the payload object itself, so a payload revalidated in place is
   recomputed rather than answered from a stale distribution. */
const CACHE = new WeakMap();

function figures(questionId, payload) {
  if (!payload || typeof payload !== 'object') return new Map();
  let byQuestion = CACHE.get(payload);
  if (!byQuestion) { byQuestion = new Map(); CACHE.set(payload, byQuestion); }
  const cached = byQuestion.get(questionId);
  if (cached) return cached;

  const byLad = (payload.places && payload.places.byLad) || {};
  const out = new Map();
  for (const code of Object.keys(byLad)) {
    const hit = placeAnswers(code, payload).find(a => a.id === questionId);
    // value, not figure: a question's figure may be a display string (ledger's
    // formatted currency), and value is what placeAnswers already computed as
    // its numeric equivalent, so nothing here has to parse it back out.
    if (hit && Number.isFinite(Number(hit.value))) out.set(code, Number(hit.value));
  }
  byQuestion.set(questionId, out);
  return out;
}

export function rankFor(code, questionId, payload) {
  // Declared non-comparable, not merely absent here: no line renders for
  // this question anywhere, on any district, regardless of what payload is
  // passed in. See RANKABLE above for why.
  if (RANKABLE[questionId] === false) return null;

  const all = figures(questionId, payload);
  const mine = all.get(code);
  if (mine == null) return null;

  // Descending, so rank 1 is the largest figure. Ties share a rank: the count
  // of districts strictly above this one, plus one.
  let above = 0;
  for (const v of all.values()) if (v > mine) above += 1;
  const rank = above + 1;
  const of = all.size;

  return {
    rank,
    of,
    figure: mine,
    percentile: of > 1 ? Math.round(100 * (of - rank) / (of - 1)) : null,
    polarity: POLARITY[questionId] || 'none',
  };
}

export function rankSentence(r) {
  // One district is not a ranking, and saying "1st of 1" implies a contest.
  if (!r || r.of < 2) return null;
  return `${ORDINAL(r.rank)} of ${r.of} districts with a figure for this question.`;
}
