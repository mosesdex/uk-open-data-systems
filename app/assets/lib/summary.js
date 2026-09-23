/* Two or three sentences about one place, built only from that place's own
   figures and the comparator each figure is published against. The order is by
   how far the place sits from its comparator, so the sentence a reader most
   needs comes first. Nothing here rounds beyond the payload, and nothing is
   said that the payload does not carry. */

const pct = v => `${Number(v).toFixed(1).replace(/\.0$/, '')}%`;
const count = v => Number(v).toLocaleString('en-GB');

const LINES = [
  {
    id: 'plumbline',
    gap: (p) => (p.plumbline && p.plumbline.statutory_pct != null && p.plumbline.headline_pct != null)
      ? Math.abs(p.plumbline.headline_pct - p.plumbline.statutory_pct) : null,
    say: (p, name) => `Of ${count(p.plumbline.dwelling_decisions)} major housing decisions in `
      + `${name}, ${pct(p.plumbline.statutory_pct)} were made inside the statutory 13 weeks without an `
      + `agreed extension. The published measure for the same authority is ${pct(p.plumbline.headline_pct)}.`,
  },
  {
    id: 'catchment',
    gap: (p, n) => (p.catchment && p.catchment.utilisation_pct != null && n.catchment
      && n.catchment.national && n.catchment.national.utilisation_pct != null)
      ? Math.abs(p.catchment.utilisation_pct - n.catchment.national.utilisation_pct) : null,
    say: (p, name, n) => `School places in ${name} are ${pct(p.catchment.utilisation_pct)} used, `
      + `${count(p.catchment.pupils)} pupils in ${count(p.catchment.capacity)} places, against `
      + `${pct(n.catchment.national.utilisation_pct)} nationally.`,
  },
  {
    id: 'lastmile',
    gap: (p, n) => (p.lastmile && p.lastmile.gigabit_pct != null && n.lastmile
      && n.lastmile.other_pct != null)
      ? Math.abs(p.lastmile.gigabit_pct - n.lastmile.other_pct) : null,
    say: (p, name, n) => `${pct(p.lastmile.gigabit_pct)} of ${count(p.lastmile.premises)} premises in `
      + `${name} are gigabit-ready, against ${pct(n.lastmile.other_pct)} nationally.`,
  },
];

export function placeSummary(code, payload) {
  const places = (payload && payload.places) || {};
  const name = (places.names || {})[code];
  const place = (places.byLad || {})[code];
  if (!name || !place) return [];
  const national = (payload && payload.systems) || {};

  return LINES
    .map(line => ({ line, gap: line.gap(place, national) }))
    .filter(x => x.gap !== null && Number.isFinite(x.gap))
    .sort((a, b) => b.gap - a.gap)
    .slice(0, 3)
    .map(x => x.line.say(place, name, national));
}
