/* What each question answers about one place, as data rather than as markup.

   The place page used to print the question's codename and the same national
   one-liner on every place, so a reader saw no figure of their own at all.
   This module holds the knowledge the page was missing: for each question,
   which published field is the figure, what the payload publishes it against,
   and the qualification that figure cannot honestly be read without. The view
   renders what this returns and invents nothing.

   Every field name below was read out of app/data/platform.json. A question
   with no object for the place, or whose figure is not a finite number there
   (Welsh authorities carry a catchment block with a null utilisation), returns
   no entry at all: an absent answer is said plainly elsewhere on the page, and
   is never padded with a national figure standing in for a local one.

   Care (Bellwether) and SEND (Compass) are published per upper-tier council,
   so in a two-tier area the district carries its county's figure. The payload
   says so with figure_for and authority_name, and the caveat repeats
   placeReport's wording in app/assets/platform.js rather than inventing a
   second phrasing for the same fact. */

const n = v => Number(v).toLocaleString('en-GB');
const money = v => '£' + n(v);
const isNum = v => v != null && Number.isFinite(Number(v));
/* The regulator's brand field prefixes a group name with BRAND, which is a
   marker for how the group was identified, not part of its name. The caveat
   says how it was identified in words, and app/assets/platform.js strips the
   prefix the same way. */
const group = v => String(v || '').replace('BRAND ', '');

/* The county note, in the words app/assets/platform.js already uses. */
const county = c => (c && c.figure_for === 'county' && c.authority_name)
  ? `${c.authority_name} County Council figure, shared by each of its districts.` : null;

const join = (...parts) => parts.filter(Boolean).join(' ') || null;

/* One entry per question, in the order the place page reads best: the two
   questions that carry a stated comparator first, then the rest. `figure`
   reads the place's own object, `against` may also read the national block. */
const QUESTIONS = [
  {
    id: 'plumbline',
    name: 'Plumbline',
    question: 'What share of major housing decisions were made inside the statutory 13 weeks, without an agreed extension?',
    unit: '%',
    figure: p => p.statutory_pct,
    against: p => p.headline_pct,
    againstLabel: 'the published measure for the same authority',
    caveat: p => `Counted over ${n(p.dwelling_decisions)} major dwelling decisions of ${n(p.major_decisions)} major decisions here.`,
  },
  {
    id: 'catchment',
    name: 'Catchment',
    question: 'How full are the school places here?',
    unit: '%',
    figure: p => p.utilisation_pct,
    against: (p, s) => s.catchment && s.catchment.national && s.catchment.national.utilisation_pct,
    againstLabel: 'the national rate',
    caveat: p => `Computed over the ${p.measured_pct}% of schools publishing both a capacity and a roll.`,
  },
  {
    id: 'lastmile',
    name: 'Lastmile',
    question: 'What share of premises can already take a gigabit connection?',
    unit: '%',
    figure: p => p.gigabit_pct,
    against: (p, s) => s.lastmile && s.lastmile.other_pct,
    againstLabel: 'the national share',
    caveat: p => `Joined on postcode, not property, over ${n(p.premises)} premises.`,
  },
  {
    id: 'compass',
    name: 'Compass',
    question: 'What is the projected three year change in education, health and care plans?',
    unit: '%',
    figure: p => p.projected_change_pct,
    caveat: p => join(county(p),
      `Aggregate counts only, no individual record is used, over ${p.years} years to ${p.last_year}.`),
  },
  {
    id: 'bellwether',
    name: 'Bellwether',
    question: 'How much of the care home capacity here sits with one provider?',
    unit: '%',
    figure: p => p.share_pct,
    caveat: p => join(county(p),
      `${group(p.group_name)} holds ${n(p.beds)} of ${n(p.la_beds)} beds across ${n(p.locations)} locations.`,
      p.branded ? 'Grouped by the regulator’s brand field.'
                : 'This provider is unbranded, so it is counted alone.'),
  },
  {
    id: 'bulwark',
    name: 'Bulwark',
    question: 'How many flood defences here are overdue an inspection?',
    unit: null,
    figure: p => p.inspection_overdue,
    against: p => p.assets,
    againstLabel: 'flood defences recorded here',
    caveat: p => `Condition is graded on ${p.graded_pct}% of them, and a maintainer is named on ${n(p.maintainer_known)}.`,
  },
  {
    id: 'highwater',
    name: 'Highwater',
    question: 'How often was permission granted against Environment Agency flood advice?',
    unit: null,
    figure: p => p.granted_against,
    against: p => p.objections,
    againstLabel: 'flood objections raised here',
    caveat: p => `${n(p.outcome_unknown)} of those objections had no outcome recorded at all.`,
  },
  {
    id: 'sightline',
    name: 'Sightline',
    question: 'How many water quality objections were raised on planning applications here?',
    unit: null,
    figure: p => p.water_objections,
    caveat: p => `Water quality objections carry no outcome field at all, so none of these can be followed to a decision. ${n(p.flood_objections)} flood objections were raised here.`,
  },
  {
    id: 'ledger',
    name: 'Ledger',
    question: 'How much was secured in developer contributions?',
    unit: null,
    figure: p => isNum(p.total_amount) ? money(p.total_amount) : null,
    caveat: p => `An amount is stated on ${p.amount_coverage_pct}% of ${n(p.contributions)} contributions, and ${p.with_location === 0 ? 'none of them carries a location' : `${n(p.with_location)} of them carry a location`}.`,
  },
];

/* The list above is a whitelist, so the two internal keys a place object also
   carries, _capacity and _systems, can never be walked into an answer block:
   they are bookkeeping about the place, not questions asked of it. */

export function placeAnswers(code, payload) {
  const places = (payload && payload.places) || {};
  const place = (places.byLad || {})[code];
  if (!place) return [];
  const systems = (payload && payload.systems) || {};
  const out = [];

  for (const q of QUESTIONS) {
    const p = place[q.id];
    if (!p) continue;
    const figure = q.figure(p, systems);
    // A block with no figure of its own is not an answer. Saying nothing is
    // the honest outcome; the page lists the question among its absences.
    if (figure == null || (typeof figure === 'number' && !Number.isFinite(figure))) continue;

    const raw = q.against ? q.against(p, systems) : null;
    const hasAgainst = isNum(raw);
    out.push({
      id: q.id,
      name: q.name,
      question: q.question,
      figure,
      unit: q.unit || null,
      against: hasAgainst ? Number(raw) : null,
      againstLabel: hasAgainst ? q.againstLabel : null,
      caveat: q.caveat ? q.caveat(p, systems) : null,
      method: `#/questions/${q.id}`,
    });
  }
  return out;
}

/* What kind of authority this place is, which a county figure shown on a
   district page cannot be read without. The payload carries the distinction in
   _capacity: a district in a two-tier county is served by a county council, so
   its capacity figure belongs to another code and is marked figure_for county,
   exactly the test app/assets/platform.js already makes. A single-tier
   authority is its own upper tier and carries its own. Where the payload
   carries no _capacity at all, this says nothing rather than guessing. */
export function placeAuthority(code, payload) {
  const places = (payload && payload.places) || {};
  const place = (places.byLad || {})[code];
  const cap = place && place._capacity;
  if (!cap) return null;
  if (cap.figure_for === 'county') {
    const name = ((places.capacityTrend || {})[cap.authority] || {}).name;
    return name
      ? `District in a two-tier area. Upper-tier figures here are ${name} County Council’s.`
      : 'District in a two-tier area. Upper-tier figures here belong to its county council.';
  }
  if (cap.figure_for === 'district') {
    return 'Single-tier authority. The upper-tier figures here are this council’s own.';
  }
  return null;
}
