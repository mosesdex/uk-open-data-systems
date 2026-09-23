/* Where a place sits furthest from the figure it is published against. Three
   questions carry both a local figure and a stated comparator, so those are the
   three this ranks. Every row keeps both numbers, so a reader can check the gap
   rather than trust it. */

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
    againstLabel: 'the national share',
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

export function unusualRows(payload, limit = 50) {
  return allRows(payload).sort((a, b) => b.gap - a.gap).slice(0, limit);
}
