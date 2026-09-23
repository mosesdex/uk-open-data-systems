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

export function unusualRows(payload, limit = 50) {
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
  return rows.sort((a, b) => b.gap - a.gap).slice(0, limit);
}
