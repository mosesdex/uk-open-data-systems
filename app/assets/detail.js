/* What each system is, in plain English, and how to read what it produced.
   Every claim here is one the platform can back with a row in the database. */
const DETAIL = {
  catchment: {
    question: 'Are there school places where the children actually are?',
    why: 'Capital is allocated per pupil planning area, but that geography is published nowhere. A district can be full and half-empty at once, and the two cancel out in the published figures.',
    method: 'Every open school is resolved to a district through the place spine, then pupils and capacity are summed and divided. Mainstream and specialist provision are counted separately, because alternative provision reports capacity on a different basis — blending them produced schools at 330% of capacity in an early build.',
    limits: [
      'Utilisation is computed only over schools that published both a capacity and a roll.',
      'Two-tier counties plan across several districts, so their figures do not attach to one.',
    ],
  },
  sentinel: {
    question: 'Is public money going to the same suppliers, without competition?',
    why: 'Contract records carry company names, not identifiers, so a buyer cannot see that two bidders share an owner, or that six firms take most of a framework.',
    method: 'Every supplier is resolved to a company number where one is published, then awards are grouped by buyer and supplier to surface concentration and uncompeted procedure.',
    limits: [
      'Bid prices are not published in UK data, so price-pattern collusion screens are impossible.',
      'Bidder counts are absent from every notice sampled, so single-bidder rates cannot be computed either.',
      'Concentration has innocent explanations. These are signals to investigate, never verdicts.',
    ],
  },
  highwater: {
    question: 'How often is housing approved against flood advice?',
    why: 'The Environment Agency objects, then frequently never learns what the council decided.',
    method: 'Objections are read from the Agency’s own published list and grouped by outcome and year. Override rates are computed over decided cases only — counting unknowns in the denominator would make the rate improve every time an outcome goes unrecorded.',
    limits: [
      'No row carries an address, postcode or coordinate, so nothing here can be mapped to a site.',
      'Thousands of outcomes were never recorded at all.',
    ],
  },
  plumbline: {
    question: 'Are planning decisions really made on time?',
    why: 'The published figure counts an application as on time if it met an agreed extension, not only if it met the statutory 13 weeks.',
    method: 'Two rates are computed side by side: the published headline, and the share of major dwelling decisions reached within the statutory thirteen weeks without an agreed extension. Decisions made under one are published with no time band, so they count as outside the thirteen weeks.',
    limits: [
      'The two rates cover slightly different populations, so both counts are always shown.',
      'The column that used to show extension reliance directly was discontinued after 2020.',
    ],
  },
  junction: {
    question: 'Where can a project actually connect to the grid?',
    why: 'Network operators publish capacity registers that a developer cannot compare or, in most cases, even download.',
    method: 'Each operator’s register is fetched anonymously and compared against what its own catalogue advertises.',
    limits: [
      'The schemas are not the problem — the registers share most of their fields.',
      'Most advertised records never reach the open route at all.',
    ],
  },
  ledger: {
    question: 'What did developers promise, and did it arrive?',
    why: 'Money is agreed for schools and roads when permission is granted. Whether it was collected or spent is not visible per site.',
    method: 'Contributions are grouped by authority and purpose, and transactions are grouped by funding status to separate agreed from received from spent.',
    limits: [
      'Not one record carries a location, so none of it can be put on a map.',
      'An amount is stated on only part of the records, so the total is published with that denominator.',
    ],
  },
  bellwether: {
    question: 'How much of a council’s care capacity sits with one company?',
    why: 'Each council sees only its own contracts, so a provider that matters across dozens of authorities looks unremarkable in each.',
    method: 'Locations are resolved to company numbers, then concentration is computed twice: by legal entity, and rolled up to the regulator’s brand where one exists.',
    limits: [
      'Around half of care-home beds are unbranded, so the group view cannot see them.',
      'The brand field mixes operator with property owner, so one home can appear under both.',
    ],
  },
  sightline: {
    question: 'Is expert planning advice followed?',
    why: 'Consultee involvement is being reduced, with little evidence about what the advice achieved.',
    method: 'Both published objection streams are read and compared: one carries outcomes, the other has no outcome field at all.',
    limits: [
      'Water quality objections record why the Agency objected and nothing about what happened next.',
    ],
  },
  lastmile: {
    question: 'Do new homes get the broadband the rules require?',
    why: 'New homes have had to be gigabit-connectable since 2022 and nobody checks nationally.',
    method: 'New-build sales are joined to premises-level gigabit status and compared against everywhere else.',
    limits: [
      'Joined on postcode, not property, because Price Paid carries no property reference.',
      'Coverage depends on which regions have been surveyed and fetched.',
    ],
  },
  bulwark: {
    question: 'Who is responsible for a flood defence, and is it being checked?',
    why: 'When a defence fails, the first question is who maintains it.',
    method: 'Owner, operator and maintainer are read separately, and inspections are counted overdue against each asset’s own next-inspection date.',
    limits: [
      'Ownership is unknown on most assets, though the maintainer usually is known.',
      'Condition statistics describe only the quarter of assets that carry a grade.',
    ],
  },
  watchman: {
    question: 'When a supplier fails, what does the public sector lose?',
    why: 'Today this takes weeks. Both halves — insolvency notices and award notices — are already public.',
    method: 'Insolvency notices are matched to a cumulative register of every supplier ever awarded a public contract, by company number where present and by scored name match otherwise.',
    limits: [
      'The register is the asset, not the fetch. At its current size the expected hit rate is a fraction of one per month.',
      'Notices carry a company number most but not all of the time.',
    ],
  },
  compass: {
    question: 'Where will demand for specialist school places be in three years?',
    why: 'Projections are published nationally or per county, so a rising district inside a falling county is invisible until children are placed far from home.',
    method: 'A straight line is fitted to eleven years of published counts per authority and projected forward, then compared against the regional average.',
    limits: [
      'Aggregate counts only. No record about any individual child is read or needed.',
      'A short or erratic series gets no projection rather than an extrapolation.',
    ],
  },
  baseline: {
    question: 'Are sewage spills actually falling?',
    why: 'A spill count is only as good as the share of the year its monitor was recording, and rainfall moves the number regardless of investment.',
    method: 'Every spill count is published with its monitor availability, and a full-year equivalent is computed alongside the raw figure.',
    limits: [
      'Rainfall normalisation uses the nearest station\u2019s 2025 total; a per-outlet daily series would sharpen it further.',
      'An outlet watched for half the year cannot be compared with one watched all year until adjusted.',
    ],
  },
};

/* Render what a system actually found, from its own gold tables. */
function renderFindings(id, d) {
  if (!d) return '<p class="card__s">This system has not been run yet.</p>';
  const n = v => v == null ? '—' : Number(v).toLocaleString('en-GB');
  const money = v => v == null ? '—' : (v >= 1e9 ? '£' + (v/1e9).toFixed(2) + 'bn'
                    : v >= 1e6 ? '£' + (v/1e6).toFixed(1) + 'm' : '£' + n(Math.round(v)));
  const big = (v, l, s) => `<div class="kpi" style="--accent:var(--uk-blue)">
      <div class="kpi__l">${l}</div><div class="kpi__v">${v}</div>
      ${s ? `<div class="kpi__m">${s}</div>` : ''}</div>`;
  const table = (cols, rows, fmt = {}) => `<div class="tablewrap" style="overflow-x:auto">
      <table class="tbl"><thead><tr>${cols.map(c => `<th>${c.label}</th>`).join('')}</tr></thead>
      <tbody>${rows.map(r => `<tr>${cols.map(c => {
        const raw = r[c.key];
        const val = fmt[c.key] ? fmt[c.key](raw) : (typeof raw === 'number' ? n(raw) : (raw ?? '—'));
        return `<td${c.mono ? ' class="mono"' : ''}>${val}</td>`;
      }).join('')}</tr>`).join('')}</tbody></table></div>`;

  switch (id) {
    case 'catchment':
      return `<div class="grid g2">
        ${big(d.national.utilisation_pct + '%', 'Mainstream places in use',
             `${n(d.national.pupils)} pupils in ${n(d.national.capacity)} places`)}
        ${big(n(d.specialist.over_capacity), 'Specialist settings over capacity',
             `${d.specialist.utilisation_pct}% utilisation across ${d.specialist.districts} districts`)}
      </div>
      <div class="card__s mt-4 mb-2">Districts under the most pressure</div>
      ${table([{label:'District',key:'lad_name'},{label:'Schools',key:'schools',mono:1},
               {label:'Pupils',key:'pupils',mono:1},{label:'Places used',key:'utilisation_pct',mono:1}],
              d.by_district.slice().sort((a,b)=>b.utilisation_pct-a.utilisation_pct).slice(0,10),
              {utilisation_pct:v=>v+'%'})}`;
    case 'ledger':
      return `<div class="grid g2">
        ${big(money(d.total), 'Recorded in contributions', `over ${n(d.with_amount)} of ${n(d.contributions)} records`)}
        ${big(n(d.located), 'Records carrying a location', 'none of it can be mapped')}
      </div>
      <div class="card__s mt-4 mb-2">Promised against delivered</div>
      ${table([{label:'Status',key:'status'},{label:'Transactions',key:'transactions',mono:1},
               {label:'Amount',key:'total_amount',mono:1}], d.status, {total_amount:money})}`;
    case 'bulwark':
      return `<div class="grid g2">
        ${big(n(d.coverage.overdue), 'Inspections overdue', 'against their own due dates')}
        ${big(Math.round(100*d.coverage.maintainer_known/d.coverage.assets) + '%', 'Maintainer known',
             `owner known on ${Math.round(100*d.coverage.owner_known/d.coverage.assets)}% of ${n(d.coverage.assets)}`)}
      </div>
      <div class="card__s mt-4 mb-2">Who maintains England’s flood defences</div>
      ${table([{label:'Maintainer',key:'maintainer'},{label:'Assets',key:'assets',mono:1},
               {label:'Kilometres',key:'km',mono:1},{label:'Overdue',key:'overdue',mono:1}], d.by_maintainer)}`;
    case 'plumbline':
      return `<div class="grid g2">
        ${big(d.statutory_pct + '%', 'Within 13 weeks, no extension', `${n(d.dwelling_decisions)} major dwelling decisions`)}
        ${big(d.headline_pct + '%', 'The published headline', `counts agreed extensions as on time · ${n(d.major_decisions)} major decisions`)}
      </div>
      ${d.dwellings_extended_pct != null ? `<div class="note mt-4"><div class="note__title">What separates the two figures</div>
        <p>${d.dwellings_extended_pct}% of major dwelling decisions, and ${d.extended_pct}% of all major decisions, were made
        under an agreed extension or performance agreement. Those count as in time on the headline. The published table
        gives them no time band, so the statutory figure counts them as outside the thirteen weeks. Agreeing an extension
        is lawful: this measures reliance on extensions, not breaches of the law.</p></div>` : ''}
      <div class="card__s mt-4 mb-2">Widest gap between the two figures</div>
      ${table([{label:'Authority',key:'lpa'},{label:'Headline',key:'headline_pct',mono:1},
               {label:'Statutory',key:'statutory_pct',mono:1}], d.worst,
              {headline_pct:v=>v+'%', statutory_pct:v=>v+'%'})}`;
    case 'compass': {
      const ehc = (d.national||[]).find(r=>/Education, health/.test(r.provision));
      return `<div class="grid g2">
        ${ehc ? big('+' + (Math.round(1000*(ehc.latest-ehc.earliest)/ehc.earliest)/10) + '%',
             'Growth in statutory EHC plans', `${n(ehc.earliest)} to ${n(ehc.latest)} since 2015`) : ''}
        ${big(n((d.rising||[]).length), 'Authorities projected', 'on eleven years of published counts')}
      </div>
      <div class="card__s mt-4 mb-2">Fastest-rising demand</div>
      ${table([{label:'Authority',key:'la_name'},{label:'Per year',key:'pupils_per_year',mono:1},
               {label:'Over 3 years',key:'projected_change_3yr',mono:1},
               {label:'Change',key:'projected_change_pct',mono:1}], d.rising, {projected_change_pct:v=>v+'%'})}
      ${(d.cohort||[]).length ? `<div class="card__s mt-4 mb-2">Demand intensity against the incoming birth cohort</div>
      <p class="card__s" style="font-size:11px;margin-bottom:.5rem">An index, not a per-child rate: EHC plans across all
      school ages against one year of births. High where a small cohort carries many plans.</p>
      ${table([{label:'Authority',key:'la_name'},{label:'EHC plans',key:'ehc_mean',mono:1},
               {label:'Annual births',key:'annual_births',mono:1},
               {label:'Index',key:'ehc_per_1000_births',mono:1}], d.cohort,
              {ehc_mean:v=>n(Math.round(v))})}` : ''}`;
    }
    case 'baseline': {
      const w=d.weather||[];
      return `<div class="grid g2">
        ${big(n(d.national.adjusted), 'Spills adjusted for uptime', `${n(d.national.reported)} reported`)}
        ${big(d.national.mean_uptime + '%', 'Mean monitor uptime', `${n(d.national.outlets)} outlets`)}
      </div>
      ${w.length ? `<div class="note mt-4"><div class="note__title">Adjusting for the weather, not just the monitor</div>
        <p>Raw spill counts reward a dry year. Dividing each company's spills by the rainfall that
        actually fell near its outlets separates what the network did from what the sky did — and it
        reorders the table. A company spilling heavily in a dry region looks worse than one spilling
        the same amount where it rains twice as much.</p></div>
      <div class="card__s mt-4 mb-2">Spills per 100mm of local rainfall (weather-adjusted)</div>
      ${table([{label:'Company',key:'company'},{label:'Spills',key:'spills',mono:1},
               {label:'Local rain',key:'mean_local_rain_mm',mono:1},
               {label:'Per 100mm',key:'spills_per_100mm_rain',mono:1}], w,
              {mean_local_rain_mm:v=>n(Math.round(v))+'mm'})}` : ''}
      <div class="card__s mt-4 mb-2">By water company (raw and uptime-adjusted)</div>
      ${table([{label:'Company',key:'company'},{label:'Reported',key:'reported_spills',mono:1},
               {label:'Adjusted',key:'availability_adjusted',mono:1},
               {label:'Uptime',key:'mean_availability_pct',mono:1}], d.by_company,
              {mean_availability_pct:v=>v+'%'})}`;
    }
    case 'bellwether': {
      const t=(d.systemic||[])[0];
      return `<div class="grid g2">
        ${t ? big(n(t.authorities), 'Authorities depend on one group',
              `${(t.brand||'').replace('BRAND ','')} — ${n(t.beds)} beds`) : ''}
        ${big(n((d.systemic||[]).length), 'Groups tracked', 'across every authority')}
      </div>
      <div class="card__s mt-4 mb-2">Groups spanning the most authorities</div>
      ${table([{label:'Group',key:'brand'},{label:'Authorities',key:'authorities',mono:1},
               {label:'Companies',key:'companies',mono:1},{label:'Beds',key:'beds',mono:1}],
              d.systemic, {brand:v=>String(v).replace('BRAND ','')})}`;
    }
    case 'highwater': {
      const against=(d.outcomes||[]).find(r=>/against/i.test(r.outcome));
      const unknown=(d.outcomes||[]).find(r=>/unknown/i.test(r.outcome));
      return `<div class="grid g2">
        ${against ? big(n(against.objections), 'Granted against flood advice', `${n(against.residential_units)} homes`) : ''}
        ${unknown ? big(n(unknown.objections), 'Outcomes never recorded', 'the Agency never learned') : ''}
      </div>
      <div class="card__s mt-4 mb-2">Override rate by year, decided cases only</div>
      ${table([{label:'Year',key:'year'},{label:'Objections',key:'objections',mono:1},
               {label:'Against advice',key:'granted_against',mono:1},
               {label:'Rate',key:'override_rate_pct',mono:1}], d.trend, {override_rate_pct:v=>v==null?'—':v+'%'})}`;
    }
    case 'lastmile': {
      const wg=d.worst_gap||[];
      return `<div class="grid g2">
        ${big(d.new_build_pct + '%', 'Gigabit in new-build postcodes', 'nationally')}
        ${big(d.other_pct + '%', 'Gigabit everywhere else', `${n(d.new_build_premises)} new-build premises`)}
      </div>
      <div class="note mt-4"><div class="note__title">The national average hides the story</div>
        <p>Across 503,171 recent new-build sales the national gap is just ${(d.new_build_pct-d.other_pct).toFixed(1)} points —
        new homes are not systematically worse connected. But the problem is intensely local:
        some authorities run 25 points below their own average, others above it.</p></div>
      ${wg.length ? `<div class="card__s mt-4 mb-2">Where new-build postcodes lag most (500+ recent sales)</div>
      ${table([{label:'Authority',key:'lad_name'},{label:'New-build',key:'gigabit_pct_new_build',mono:1},
               {label:'Overall',key:'gigabit_pct',mono:1},{label:'Gap',key:'gap',mono:1},
               {label:'Sales',key:'new_build_sales',mono:1}], wg,
              {gigabit_pct_new_build:v=>v+'%', gigabit_pct:v=>v+'%', gap:v=>'−'+v+' pts'})}` : ''}`;
    }
    case 'sentinel': {
      const m=d.method||[];
      const un=m.filter(x=>['direct','limited'].includes(x.method)).reduce((a,x)=>a+Number(x.awards||0),0);
      const tot=m.reduce((a,x)=>a+Number(x.awards||0),0);
      const fp=d.control_footprint||[];
      return `<div class="grid g2">
        ${big((Math.round(1000*un/tot)/10)+'%', 'Awards skipping open competition', `across ${n(tot)} award records`)}
        ${big(n(d.control_footprint_total != null ? d.control_footprint_total : fp.length), 'Owners behind several of a buyer’s suppliers', 'from 8m ownership records')}
      </div>
      ${(() => { const p = d.shared_control_probe;
        if (!p || !p.psc_loaded || p.shared_control_pairs) return '';
        return `<div class="note mt-4"><div class="note__title">Checked, and none found: a shared owner on one contract</div>
        <p>Of ${n(p.competed_contracts)} contracts naming between two and ${n(p.competed_field_max)} suppliers, none has two
        under the same controlling person, leaving aside a parent company and its own subsidiary. Award notices name the
        winners, not the bidders, so the check sees little: ${n(p.multi_supplier_contracts)} of ${n(p.contracts)} contracts
        name more than one supplier at all.</p></div>`; })()}
      ${fp.length ? `<div class="note mt-4"><div class="note__title">One owner, several suppliers, one buyer</div>
        <p>This is the collusion-adjacent signal that <em>is</em> possible in UK data. Award notices name
        only the winner, not who bid — so shared control on a single contract almost never shows.
        But one person controlling several of a buyer’s suppliers over time needs no bidder list.
        A signal to look at, never a verdict.</p></div>
      <div class="card__s mt-4 mb-2">Beneficial owners controlling multiple suppliers to one buyer</div>
      ${table([{label:'Owner',key:'person'},{label:'Buyer',key:'buyer'},
               {label:'Companies',key:'companies',mono:1},{label:'Awards',key:'awards',mono:1},
               {label:'Value',key:'total_value',mono:1}], fp, {total_value:money})}` : ''}
      <div class="card__s mt-4 mb-2">Buyers concentrating on one supplier</div>
      ${table([{label:'Buyer',key:'buyer'},{label:'Suppliers',key:'suppliers',mono:1},
               {label:'Awards',key:'awards',mono:1},
               {label:'Top supplier share',key:'top_supplier_award_share',mono:1}], d.concentrated,
              {top_supplier_award_share:v=>v+'%'})}`;
    }
    case 'junction': {
      const r=d.registers||[];
      const adv=r.reduce((a,x)=>a+Number(x.catalogue_records||0),0);
      const got=r.reduce((a,x)=>a+Number(x.rows||0),0);
      return `<div class="grid g2">
        ${big(n(got)+' of '+n(adv), 'Records actually served', `${r.filter(x=>x.publishes_data).length} of ${r.length} operators`)}
        ${big(n(adv-got), 'Never reach the open route', 'listed, dated, and undownloadable')}
      </div>
      <div class="card__s mt-4 mb-2">Per operator</div>
      ${table([{label:'Operator',key:'operator'},{label:'Catalogue says',key:'catalogue_records',mono:1},
               {label:'Export returns',key:'rows',mono:1},{label:'Fields',key:'field_count',mono:1}], r)}`;
    }
    case 'sightline': {
      const tot=(d.reasons||[]).reduce((a,x)=>a+Number(x.objections||0),0);
      return `<div class="grid g2">
        ${big(n(tot), 'Water quality objections', 'none carry a recorded outcome')}
        ${big('0', 'With an outcome field', 'the field does not exist')}
      </div>
      <div class="card__s mt-4 mb-2">Why the Agency objected</div>
      ${table([{label:'Reason',key:'reason'},{label:'Objections',key:'objections',mono:1},
               {label:'Authorities',key:'authorities',mono:1}], d.reasons)}`;
    }
    case 'watchman': {
      // The distressed organisations were published and shown only as the top
      // one in an insight. None has a profile on this site, so each links to its
      // own Companies House record rather than to an empty page.
      const list = d.distress_list || [];
      const e = s => String(s ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
      const rows = list.map(x => ({
        name: x.company_number
          ? `<a href="https://find-and-update.company-information.service.gov.uk/company/${encodeURIComponent(x.company_number)}" target="_blank" rel="noopener">${e(x.name)}</a>`
          : e(x.name),
        company_number: e(x.company_number || '—'),
        company_status: e(x.company_status),
        role: e(x.role),
        activity: x.role === 'CQC care provider' ? `${n(x.activity)} care locations` : n(x.activity),
      }));
      return `<div class="grid g2">
        ${big(n((d.exposures||[]).length), 'Exposures in the current window', 'the register must accumulate first')}
        ${big('—', 'Historic backfill', 'not yet fetched')}
      </div>
      <p class="card__s mt-3">Zero is the correct answer at this register size, not a failure.
      Matching a few weeks of insolvencies against a few weeks of awards is expected to find
      almost nothing; the register needs years of award notices before it produces signal.</p>
      ${rows.length ? `<div class="card__s mt-4 mb-2">Holding a public role while financially distressed · ${n(rows.length)} · each name opens its Companies House record</div>
      ${table([{label:'Organisation',key:'name'},{label:'Company',key:'company_number',mono:1},
               {label:'Companies House status',key:'company_status'},{label:'Public role',key:'role'},
               {label:'Scale',key:'activity',mono:1}], rows)}` : ''}`;
    }
    default:
      return '<p class="card__s">No renderer for this system yet.</p>';
  }
}
