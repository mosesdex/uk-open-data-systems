/* Visual system cards for the homepage.
   Each of the thirteen is a self-contained module: name, purpose, a headline
   metric with its unit and context, a small preview matched to what the data
   actually is (a comparison, a distribution, or one of the two genuine time
   series), and a freshness stamp. No preview invents a trend where the data
   has no time dimension. */
const CARDS = (() => {

  // Per-system card spec. `preview` returns {kind, ...} from the payload, or
  // null when there is nothing honest to draw.
  /* The thirteen are marked with one drawn set rather than emoji: emoji are
     different artwork on every platform, and they read informal next to a
     page of measurements. Stroked in currentColor, so each inherits the
     colour of whatever it sits in, and aria-hidden because the name is
     already beside it. */
  const ICON = {
    catchment: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 10.5 12 5l9 5.5M5.5 12v7.5h13V12M9.5 19.5v-4h5v4"/></svg>',
    compass: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18Zm3.2 5.8-2.1 4.4-4.4 2.1 2.1-4.4 4.4-2.1Z"/></svg>',
    plumbline: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 3v9m0 0-3.2 5.2h6.4L12 12Zm-8 14.8h16"/></svg>',
    ledger: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 4.5h11.5a2 2 0 0 1 2 2v13H7a2 2 0 0 1-2-2v-13Zm0 0v13m3.5-9.5h6m-6 4h6"/></svg>',
    highwater: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 16.5c2-1.4 3.5-1.4 5.5 0s3.5 1.4 5.5 0 3.5-1.4 5.5 0M7 12.5V7l5-3 5 3v5.5"/></svg>',
    sightline: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M2.5 12S6 6.5 12 6.5 21.5 12 21.5 12S18 17.5 12 17.5 2.5 12 2.5 12Zm9.5 2.4a2.4 2.4 0 1 0 0-4.8 2.4 2.4 0 0 0 0 4.8Z"/></svg>',
    lastmile: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 19.5v-6m0 0a2 2 0 1 0 0-4 2 2 0 0 0 0 4ZM7.2 6.2a8 8 0 0 0 0 11.3m9.6-11.3a8 8 0 0 1 0 11.3M4.2 3.2a12 12 0 0 0 0 17.3m15.6-17.3a12 12 0 0 1 0 17.3"/></svg>',
    junction: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M13.5 3 6 13.5h5l-1.5 7.5L17 10.5h-5L13.5 3Z"/></svg>',
    bellwether: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 17.5v-4a2 2 0 0 1 2-2h14v6M3 17.5h18M3 13.5V8m13 3.5V9a1.5 1.5 0 0 0-1.5-1.5h-4A1.5 1.5 0 0 0 9 9v2.5"/></svg>',
    bulwark: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 3 4.5 6v6c0 4.2 3.1 7.5 7.5 9 4.4-1.5 7.5-4.8 7.5-9V6L12 3Z"/></svg>',
    watchman: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 3.5a6 6 0 0 0-6 6c0 3.5-1.5 5-1.5 5h15s-1.5-1.5-1.5-5a6 6 0 0 0-6-6Zm-2 14a2 2 0 0 0 4 0"/></svg>',
    sentinel: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M10.5 17a6.5 6.5 0 1 0 0-13 6.5 6.5 0 0 0 0 13Zm4.7-1.8L20.5 20.5"/></svg>',
    baseline: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 3.5s6 6.4 6 10.2A6 6 0 0 1 6 13.7C6 9.9 12 3.5 12 3.5Z"/></svg>',
  };

  const SPEC = {
    catchment: {
      icon: ICON.catchment, domain: 'Education',
      purpose: 'School places matched to the neighbourhoods that need them',
      headline: d => ({ value: d.national.utilisation_pct, unit: '%',
        label: 'of mainstream places in use',
        context: `${fmt(d.national.pupils)} pupils · ${d.national.districts} districts` }),
      preview: d => ({ kind: 'gauge', pct: d.national.utilisation_pct,
        caption: `${d.specialist.over_capacity} specialist settings over capacity` }),
    },
    compass: {
      icon: ICON.compass, domain: 'Education',
      purpose: 'Forecasts specialist-school demand from the incoming cohort',
      headline: d => { const e = (d.national||[]).find(r=>/Education, health/.test(r.provision));
        const pct = e ? Math.round(1000*(e.latest-e.earliest)/e.earliest)/10 : null;
        return { value: pct, unit: '%', prefix: '+', label: 'growth in EHC plans',
          context: e ? `${fmt(e.earliest)} → ${fmt(e.latest)} since 2015` : '',
          trend: pct }; },
      preview: d => { const e = (d.national||[]).find(r=>/Education, health/.test(r.provision));
        return e ? { kind: 'compare', a: {label:'2015', v:e.earliest}, b: {label:'2025', v:e.latest} } : null; },
    },
    plumbline: {
      icon: ICON.plumbline, domain: 'Housing',
      purpose: 'Planning decisions measured against the statutory 13 weeks',
      headline: d => ({ value: d.statutory_pct, unit: '%',
        label: 'within 13 weeks, no extension',
        context: `of ${Number(d.dwelling_decisions || 0).toLocaleString('en-GB')} major dwelling decisions · published measure ${d.headline_pct}%` }),
      preview: d => ({ kind: 'compare', a:{label:'Statutory',v:d.statutory_pct},
        b:{label:'Headline',v:d.headline_pct}, unit:'%' }),
    },
    ledger: {
      icon: ICON.ledger, domain: 'Housing',
      purpose: 'Developer money promised, and whether it ever arrived',
      headline: d => ({ value: d.total/1e9, unit: 'bn', prefix: '£', dec: 2,
        label: 'in contributions recorded',
        context: `${d.located} of ${fmt(d.contributions)} can be mapped` }),
      preview: d => ({ kind: 'bars', rows: (d.status||[]).slice(0,4).map(r=>({
        n: r.status, v: r.total_amount })), fmt: money }),
    },
    highwater: {
      icon: ICON.highwater, domain: 'Environment',
      purpose: 'Homes approved against Environment Agency flood advice',
      headline: d => { const a=(d.outcomes||[]).find(r=>/against/i.test(r.outcome));
        return { value: a?a.objections:0, unit: '',
          label: 'granted against flood advice',
          context: `${fmt((d.outcomes||[]).reduce((s,r)=>s+r.objections,0))} objections in all` }; },
      preview: d => ({ kind: 'line',
        series: (d.trend||[]).map(r=>r.override_rate_pct||0),
        labels: (d.trend||[]).map(r=>r.year),
        caption: 'override rate, 9 years, flat, not rising' }),
    },
    sightline: {
      icon: ICON.sightline, domain: 'Planning',
      purpose: 'Whether expert planning advice is actually followed',
      headline: d => ({ value: (d.reasons||[]).reduce((s,r)=>s+r.objections,0), unit: '',
        label: 'water-quality objections',
        context: 'none carry any recorded outcome' }),
      preview: d => ({ kind: 'bars', rows: (d.reasons||[]).slice(0,4).map(r=>({
        n: r.reason, v: r.objections })), fmt: fmt }),
    },
    lastmile: {
      icon: ICON.lastmile, domain: 'Digital',
      purpose: 'Do new homes get the broadband the rules require',
      headline: d => ({ value: d.new_build_pct, unit: '%',
        label: 'gigabit in new-build postcodes',
        context: `${d.other_pct}% everywhere else` }),
      preview: d => ({ kind: 'compare', a:{label:'New build',v:d.new_build_pct},
        b:{label:'Elsewhere',v:d.other_pct}, unit:'%' }),
    },
    junction: {
      icon: ICON.junction, domain: 'Energy',
      purpose: 'Grid connection capacity a developer can actually find',
      headline: d => { const r=d.registers||[];
        const got=r.reduce((s,x)=>s+Number(x.rows||0),0);
        const adv=r.reduce((s,x)=>s+Number(x.catalogue_records||0),0);
        return { value: adv?Math.round(1000*got/adv)/10:0, unit: '%',
          label: 'of records actually served',
          context: `${fmt(got)} of ${fmt(adv)} advertised` }; },
      preview: d => { const r=d.registers||[];
        return { kind: 'bars', rows: r.map(x=>({ n:x.operator, v:Number(x.rows||0) })), fmt: fmt }; },
    },
    ledger_placeholder: null,
    bellwether: {
      icon: ICON.bellwether, domain: 'Social care',
      purpose: 'How much of a council’s care sits with one company',
      headline: d => { const t=(d.systemic||[])[0];
        return { value: t?t.authorities:0, unit: '',
          label: 'authorities rely on one group',
          context: t ? `${(t.brand||'').replace('BRAND ','')} · ${fmt(t.beds)} beds` : '' }; },
      preview: d => ({ kind: 'bars', rows: (d.systemic||[]).slice(0,5).map(r=>({
        n: (r.brand||'').replace('BRAND ',''), v: r.beds })), fmt: fmt }),
    },
    bulwark: {
      icon: ICON.bulwark, domain: 'Environment',
      purpose: 'Who is responsible for a flood defence, and is it checked',
      headline: d => ({ value: d.coverage.overdue, unit: '',
        label: 'inspections overdue',
        context: `owner known on ${Math.round(100*d.coverage.owner_known/d.coverage.assets)}% of ${fmt(d.coverage.assets)}` }),
      preview: d => ({ kind: 'bars', rows: (d.by_maintainer||[]).slice(0,5).map(r=>({
        n: r.maintainer, v: r.assets })), fmt: fmt }),
    },
    watchman: {
      icon: ICON.watchman, domain: 'Procurement',
      purpose: 'When a supplier fails, what the public sector loses',
      headline: d => ({ value: (d.exposures||[]).length, unit: '',
        label: 'live exposures found',
        context: 'the register must accumulate to produce signal' }),
      preview: () => ({ kind: 'note', text: 'Zero is correct at this register size. Award notices name only winners; the register needs years to compound.' }),
    },
    compass_placeholder: null,
    sentinel: {
      icon: ICON.sentinel, domain: 'Procurement',
      purpose: 'Public money going to the same suppliers, and who owns them',
      headline: d => { const m=d.method||[];
        const un=m.filter(x=>['direct','limited'].includes(x.method)).reduce((s,x)=>s+Number(x.awards||0),0);
        const tot=m.reduce((s,x)=>s+Number(x.awards||0),0);
        return { value: tot?Math.round(1000*un/tot)/10:0, unit: '%',
          label: 'of awards skip open competition',
          context: `${(d.control_footprint||[]).length} owners behind several suppliers` }; },
      preview: d => ({ kind: 'bars', rows: (d.method||[]).map(r=>({
        n: r.method, v: r.awards })), fmt: fmt }),
    },
    baseline: {
      icon: ICON.baseline, domain: 'Water',
      purpose: 'Sewage spills, adjusted for the weather that caused them',
      headline: d => ({ value: d.national.adjusted, unit: '',
        label: 'spills, adjusted for uptime',
        context: `${fmt(d.national.reported)} reported · ${d.national.mean_uptime}% uptime` }),
      preview: d => ({ kind: 'bars', rows: (d.weather||[]).slice(0,5).map(r=>({
        n: r.company, v: r.spills_per_100mm_rain })), fmt: v=>fmt(Math.round(v)),
        caption: 'spills per 100mm of local rain' }),
    },
  };

  const fmt = n => n==null ? 'n/a' : Number(n).toLocaleString('en-GB');
  const money = v => v==null ? 'n/a' : (v>=1e9 ? '£'+(v/1e9).toFixed(2)+'bn'
                    : v>=1e6 ? '£'+(v/1e6).toFixed(1)+'m' : '£'+fmt(Math.round(v)));

  return { SPEC, fmt, money };
})();
