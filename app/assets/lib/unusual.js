/* Where a place sits furthest from the figure it is published against. Three
   questions carry both a local figure and a stated comparator, so those are the
   three this ranks. Every row keeps both numbers, so a reader can check the gap
   rather than trust it.

   Plumbline's gaps (80 to 98 points) run far wider than catchment's or
   lastmile's (usually single digits), so one global sort by absolute gap
   crowds every one of the fifty rows with the same question and the page
   stops being a record of what looks unusual and becomes a record of one
   system. unusualRows ranks within each question first, then takes the
   widest share of the limit from each, so a display cap can never let one
   question's scale hide the other two. */

const COMPARATORS = [
  {
    id: 'plumbline',
    figure: p => p.plumbline && p.plumbline.statutory_pct,
    against: p => p.plumbline && p.plumbline.headline_pct,
    againstLabel: 'the published measure for the same authority',
  },
  {
    id: 'catchment',
    figure: p => p.catchment && p.catchment.utilisation_pct,
    against: (p, n) => n.catchment && n.catchment.national && n.catchment.national.utilisation_pct,
    againstLabel: 'the national rate',
  },
  {
    id: 'lastmile',
    figure: p => p.lastmile && p.lastmile.gigabit_pct,
    against: (p, n) => n.lastmile && n.lastmile.other_pct,
    againstLabel: 'the national share outside new-build postcodes',
  },
];

// Every place/question pair with both a figure and a comparator, unranked
// and unlimited. unusualRows and unusualTotal both build from this, so the
// count shown for "how many diverge" can never drift from what is ranked.
function allRows(payload) {
  const places = (payload && payload.places) || {};
  const names = places.names || {};
  const byLad = places.byLad || {};
  const national = (payload && payload.systems) || {};
  const rows = [];

  for (const [code, place] of Object.entries(byLad)) {
    const name = names[code];
    if (!name) continue;
    for (const c of COMPARATORS) {
      const figure = c.figure(place, national);
      const against = c.against(place, national);
      if (!Number.isFinite(figure) || !Number.isFinite(against)) continue;
      rows.push({ code, name, question: c.id, figure, against,
                  againstLabel: c.againstLabel, gap: Math.abs(against - figure) });
    }
  }
  return rows;
}

// The true count of diverging place/question pairs, with no display limit
// applied. This is what a door or header figure should show: the page below
// lists only the widest of these, and says so.
export function unusualTotal(payload) {
  return allRows(payload).length;
}

// Grouped by question, each group ranked by its own gap, then the display
// limit is shared out evenly across whichever questions actually have rows.
// The split is sequential rather than a flat one-third each: a question with
// fewer qualifying places than an even share (there are none today, but
// nothing here should break if one appears) hands what it cannot use back
// to the questions still to come, rather than the row simply going unfilled.
// So the fifty rows a reader sees are the widest fifty within each question,
// never the fifty widest overall, which one question's much larger gaps
// would otherwise claim entirely.
export function unusualRows(payload, limit = 50) {
  const rows = allRows(payload);
  const groups = COMPARATORS
    .map(c => rows.filter(r => r.question === c.id).sort((a, b) => b.gap - a.gap))
    .filter(g => g.length);

  let remaining = Math.min(limit, rows.length);
  const result = [];
  groups.forEach((g, i) => {
    const groupsLeft = groups.length - i;
    const take = Math.min(g.length, Math.ceil(remaining / groupsLeft));
    result.push(...g.slice(0, take));
    remaining -= take;
  });
  return result;
}
