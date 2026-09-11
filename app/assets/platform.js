/* Reads what the platform actually computed.
   Every figure rendered through this module comes from a gold table via
   platform.json. Where a system produced no output the panel says so, rather
   than falling back to a number typed in by hand. */
const Platform = (() => {
  let data = null;

  async function load(path = 'data/platform.json') {
    if (data) return data;
    try {
      // The payload is rewritten every time the platform is rebuilt, and a
      // conditional request can still serve a stale copy from disk cache even
      // with no-store set. Showing yesterday's figures as today's is the one
      // failure this interface must not have, so the URL is made unique.
      const r = await fetch(`${path}?t=${Date.now()}`, {cache: 'no-store'});
      if (!r.ok) throw new Error('HTTP ' + r.status);
      data = await r.json();
    } catch (e) {
      data = {generated: null, systems: {}, spine: {}, sources: {}, built_systems: []};
      data.error = String(e.message || e);
    }
    return data;
  }

  const sys = id => (data && data.systems && data.systems[id]) || null;
  const has = id => !!sys(id);
  const pipeline = () => (data && data.pipeline) || null;
  const organisations = () => (data && data.organisations) || [];

  /* Headline figures, each traced to the system that produced it. */
  function headlines() {
    const out = [];
    const c = sys('catchment'), l = sys('ledger'), b = sys('bulwark'),
          cm = sys('compass'), p = sys('plumbline'), bl = sys('baseline');

    if (c && c.national) out.push({
      system: 'Catchment', label: 'Mainstream places used',
      value: c.national.utilisation_pct, suffix: '%',
      note: `${Number(c.national.pupils).toLocaleString('en-GB')} pupils in `
          + `${Number(c.national.capacity).toLocaleString('en-GB')} places`});

    if (c && c.specialist) out.push({
      system: 'Catchment', label: 'Specialist settings over capacity',
      value: c.specialist.over_capacity, suffix: '',
      note: `${c.specialist.utilisation_pct}% utilisation across ${c.specialist.districts} districts`});

    if (l) out.push({
      system: 'Ledger', label: 'Developer contributions recorded',
      value: l.total, prefix: '£', money: true,
      note: `${l.located} of ${Number(l.contributions).toLocaleString('en-GB')} carry a location`});

    if (b && b.coverage) out.push({
      system: 'Bulwark', label: 'Flood defence inspections overdue',
      value: b.coverage.overdue, suffix: '',
      note: `maintainer known on ${Math.round(100*b.coverage.maintainer_known/b.coverage.assets)}% of `
          + `${Number(b.coverage.assets).toLocaleString('en-GB')} assets`});

    if (p) out.push({
      system: 'Plumbline', label: 'Decided within 13 weeks without an extension',
      value: p.statutory_pct, suffix: '%',
      note: `of ${Number(p.dwelling_decisions).toLocaleString('en-GB')} major dwelling decisions; the published measure is ${p.headline_pct}%`});

    if (cm && cm.national) {
      const ehc = cm.national.find(r => /Education, health/.test(r.provision));
      if (ehc && ehc.earliest) out.push({
        system: 'Compass', label: 'Growth in statutory EHC plans',
        value: Math.round(1000*(ehc.latest-ehc.earliest)/ehc.earliest)/10, suffix: '%',
        note: `${Number(ehc.earliest).toLocaleString('en-GB')} to ${Number(ehc.latest).toLocaleString('en-GB')} since 2015`});
    }

    if (bl && bl.national) out.push({
      system: 'Baseline', label: 'Spills after adjusting for monitor uptime',
      value: bl.national.adjusted, suffix: '',
      note: `${Number(bl.national.reported).toLocaleString('en-GB')} reported, `
          + `mean uptime ${bl.national.mean_uptime}%`});

    return out;
  }

  function sourceSummary() {
    const rows = (data && data.sources && data.sources.status) || [];
    return {
      total: rows.length,
      ok: rows.filter(r => r.ok).length,
      blocked: rows.filter(r => r.blocked).length,
      rows,
    };
  }

  function spineSummary() {
    const s = (data && data.spine) || {};
    const place = s.place || {};
    return {
      postcodes: place.postcode ? place.postcode.rows : null,
      properties: place.uprn ? place.uprn.rows : null,
      districts: place.lad ? place.lad.rows : null,
      register: s.entity ? s.entity.register_rows : null,
      registerNumbers: s.entity ? s.entity.distinct_numbers : null,
    };
  }

  /* Per-district values for the choropleth, straight from Catchment. */
  function districtValues(metric = 'utilisation_pct') {
    const c = sys('catchment');
    if (!c || !c.by_district) return {};
    const out = {};
    c.by_district.forEach(d => {
      if (d.lad_code != null && d[metric] != null) out[d.lad_code] = d[metric];
    });
    return out;
  }

  function districtLookup() {
    const c = sys('catchment');
    const out = {};
    if (c && c.by_district) c.by_district.forEach(d => { out[d.lad_code] = d; });
    return out;
  }

  /* One measured headline per system, so all thirteen can be seen at once.
     A system with no output returns null and its card says so. */
  function systemResult(id) {
    const d = sys(id);
    if (!d) return null;
    const n = v => Number(v).toLocaleString('en-GB');
    const money = v => v >= 1e9 ? '£' + (v/1e9).toFixed(2) + 'bn' : '£' + n(Math.round(v));
    switch (id) {
      case 'catchment':
        return d.national && {headline: d.national.utilisation_pct + '%',
          label: 'of mainstream school places in use',
          sub: `${d.specialist ? d.specialist.over_capacity : 0} specialist settings over capacity`};
      case 'ledger':
        return {headline: money(d.total), label: 'of developer contributions recorded',
          sub: `${d.located} of ${n(d.contributions)} carry a location`};
      case 'bulwark':
        return d.coverage && {headline: n(d.coverage.overdue), label: 'inspections overdue',
          sub: `maintainer known on ${Math.round(100*d.coverage.maintainer_known/d.coverage.assets)}% of ${n(d.coverage.assets)} defences`};
      case 'plumbline':
        return {headline: d.statutory_pct + '%', label: 'decided within 13 weeks without an extension',
          sub: `of ${n(d.dwelling_decisions)} major dwelling decisions; the published measure is ${d.headline_pct}%`};
      case 'compass': {
        const e = (d.national || []).find(r => /Education, health/.test(r.provision));
        return e && e.earliest && {headline: '+' + (Math.round(1000*(e.latest-e.earliest)/e.earliest)/10) + '%',
          label: 'growth in statutory EHC plans',
          sub: `${n(e.earliest)} to ${n(e.latest)} since 2015`};
      }
      case 'baseline':
        return d.national && {headline: n(d.national.adjusted), label: 'spills after adjusting for monitor uptime',
          sub: `${n(d.national.reported)} reported across ${n(d.national.outlets)} outlets`};
      case 'highwater': {
        const o = d.outcomes || [];
        const against = o.find(r => /against/i.test(r.outcome));
        const total = o.reduce((a, r) => a + Number(r.objections || 0), 0);
        return against && {headline: n(against.objections), label: 'permissions granted against flood advice',
          sub: `of ${n(total)} objections; ${n((o.find(r=>/unknown/i.test(r.outcome))||{}).objections||0)} outcomes never recorded`};
      }
      case 'lastmile':
        return {headline: d.new_build_pct + '%', label: 'gigabit in new-build postcodes',
          sub: `against ${d.other_pct}% everywhere else`};
      case 'junction': {
        const r = d.registers || [];
        const adv = r.reduce((a,x)=>a+Number(x.catalogue_records||0),0);
        const got = r.reduce((a,x)=>a+Number(x.rows||0),0);
        return {headline: n(got) + ' of ' + n(adv), label: 'capacity records actually served',
          sub: `${r.filter(x=>x.publishes_data).length} of ${r.length} operators serve data openly`};
      }
      case 'bellwether': {
        const t = (d.systemic || [])[0];
        return t && {headline: n(t.authorities), label: 'authorities depend on one care group',
          sub: `${t.brand.replace('BRAND ','')} — ${n(t.beds)} beds across ${t.companies} companies`};
      }
      case 'sentinel': {
        const m = d.method || [];
        const un = m.filter(x => ['direct','limited'].includes(x.method))
                    .reduce((a,x)=>a+Number(x.awards||0),0);
        const tot = m.reduce((a,x)=>a+Number(x.awards||0),0);
        return tot && {headline: (Math.round(1000*un/tot)/10) + '%',
          label: 'of awards skipped open competition',
          sub: `across ${n(tot)} award records`};
      }
      case 'sightline': {
        const r = d.reasons || [];
        const tot = r.reduce((a,x)=>a+Number(x.objections||0),0);
        return {headline: n(tot), label: 'water quality objections',
          sub: 'none carry a recorded outcome — the field does not exist'};
      }
      case 'watchman':
        return {headline: n((d.exposures || []).length), label: 'exposures found in the sample',
          sub: 'the register must accumulate before this produces signal'};
      default: return null;
    }
  }

  /* Operator view. Everything below traces to a row in the database or a file
     on disk; nothing is illustrative. */
  const admin = () => (data && data.admin) || null;

  /* ---- one place, every system ---- */
  const placesRaw = () => (data && data.places) || null;

  /* Metrics the map can shade by. Each names the system that produced it, how
     to read it, and whether a high value is good or bad -- the palette must not
     imply that more overdue inspections is an achievement. */
  const MAP_METRICS = [
    {id:'coverage',  system:'Platform',   label:'Systems reporting',
     unit:'', hint:'how many of the thirteen can say anything here', good:'high'},
    {id:'catchment', system:'Catchment',  label:'School places in use',
     unit:'%', hint:'mainstream capacity used', good:'low', pick:d=>d.catchment && d.catchment.utilisation_pct},
    {id:'compass',   system:'Compass',    label:'EHC plan growth projected',
     unit:'%', hint:'three-year projection', good:'low', pick:d=>d.compass && d.compass.projected_change_pct},
    {id:'plumbline', system:'Plumbline',  label:'Within 13 weeks, no extension',
     unit:'%', hint:'major dwelling decisions', good:'high', pick:d=>d.plumbline && d.plumbline.statutory_pct},
    {id:'bulwark',   system:'Bulwark',    label:'Flood inspections overdue',
     unit:'', hint:'past their own due date', good:'low', pick:d=>d.bulwark && d.bulwark.inspection_overdue},
    {id:'lastmile',  system:'Lastmile',   label:'Premises gigabit-ready',
     unit:'%', hint:'where BDUK has surveyed', good:'high', pick:d=>d.lastmile && d.lastmile.gigabit_pct},
    {id:'bellwether',system:'Bellwether', label:'Care beds with one group',
     unit:'%', hint:'largest single provider share', good:'low', pick:d=>d.bellwether && d.bellwether.share_pct},
    {id:'highwater', system:'Highwater',  label:'Granted against flood advice',
     unit:'', hint:'permissions overriding an objection', good:'low', pick:d=>d.highwater && d.highwater.granted_against},
    {id:'ledger',    system:'Ledger',     label:'Contributions recorded',
     unit:'£', hint:'developer obligations', good:'high', pick:d=>d.ledger && d.ledger.total_amount},
  ];

  /* Plain-English method per metric, so a figure on the map can be traced to
     how it was produced, not just to who published the input. */
  const METRIC_METHOD = {
    coverage:  {system:null, method:'Counts how many of the thirteen systems produced a figure for each district. Districts with none are usually two-tier counties, where services are planned across several districts at once.'},
    catchment: {system:'catchment', method:'Sums pupils and capacity across every open mainstream school resolved to the district, then divides. Specialist provision is counted separately because it reports capacity on a different basis.'},
    compass:   {system:'compass', method:'Fits a straight line to eleven years of published EHC plan counts for the authority and projects three years forward. Aggregate counts only — no record about any individual child is used.'},
    plumbline: {system:'plumbline', method:'Divides major dwelling decisions reached within the statutory thirteen weeks without an agreed extension by all major dwelling decisions; those made under an extension have no published time band and count as outside. The published headline instead counts agreed extensions as on time.'},
    bulwark:   {system:'bulwark', method:'Counts flood defences whose own next-inspection date has already passed. Dates are published as DD/MM/YYYY and parsed strictly.'},
    lastmile:  {system:'lastmile', method:'Divides premises flagged gigabit-capable by all surveyed premises in the district. Joined on postcode, not property, because Price Paid carries no property reference.'},
    bellwether:{system:'bellwether', method:'Takes the largest single provider group\u2019s share of care beds in the authority. Grouped by the regulator\u2019s brand field where present; unbranded providers count alone.'},
    highwater: {system:'highwater', method:'Counts planning permissions granted after the Environment Agency objected on flood risk grounds, from the Agency\u2019s own published objections list.'},
    ledger:    {system:'ledger', method:'Sums developer contribution amounts recorded for the authority. An amount is stated on only part of the records, and none of them carry a location.'},
  };

  /* Sources registered against one system, by its id. Used by the detail
     drawer, where every one of the thirteen needs its own provenance -- not
     just the nine that happen to be map metrics. */
  function systemProvenance(systemId) {
    const all = (data && data.sources && data.sources.status) || [];
    const feeds = all.filter(r =>
      (r.systems || '').split(',').map(x => x.trim()).filter(Boolean).includes(systemId));
    return feeds.map(r => ({
      name: r.name, publisher: r.publisher, licence: r.licence, cadence: r.cadence,
      fetched: r.fetched_at, bytes: r.bytes_len || r.disk_bytes,
      status: r.blocked ? 'blocked' : (r.ok ? 'HTTP ' + r.http_status
              : r.provenance === 'unlogged' ? 'in use' : 'not fetched'),
      ok: r.blocked ? false : (r.ok || r.provenance === 'unlogged'),
      // Only a source fetched through the registry has its bytes hashed; one
      // that arrived by bulk import holds data with no hash behind it.
      hashed: !!r.sha256,
      // Who serves it, by the audit's rule: the publisher, the publisher's own
      // hosting elsewhere, or a third party in between.
      authority: r.authority || null,
    }));
  }

  const systemMethod = id => (METRIC_METHOD[id] || {}).method || null;

  /* Which registered sources feed the system behind a metric. */
  function metricProvenance(id) {
    const spec = METRIC_METHOD[id] || METRIC_METHOD.coverage;
    const all = (data && data.sources && data.sources.status) || [];
    const sys = spec.system;
    const feeds = sys
      ? all.filter(r => (r.systems || '').split(',').map(x => x.trim()).includes(sys))
      : all.filter(r => r.provenance !== 'absent');
    return {
      system: sys,
      method: spec.method,
      sources: feeds.map(r => ({
        name: r.name, publisher: r.publisher, licence: r.licence,
        cadence: r.cadence, fetched: r.fetched_at, bytes: r.bytes_len || r.disk_bytes,
        status: r.blocked ? 'blocked' : (r.ok ? 'HTTP ' + r.http_status
                : r.provenance === 'unlogged' ? 'in use' : 'not fetched'),
        ok: r.blocked ? false : (r.ok || r.provenance === 'unlogged'),
      })),
      allSources: sys ? null : feeds.length,
    };
  }

  function mapMetrics() {
    const p = placesRaw();
    if (!p) return [];
    // Only offer a metric that actually has values, so the switcher never
    // presents an empty map as a finding.
    return MAP_METRICS.filter(m => {
      if (m.id === 'coverage') return true;
      return Object.values(p.byLad).some(d => {
        const v = m.pick(d); return v != null && !Number.isNaN(v);
      });
    });
  }

  function metricValues(id) {
    const p = placesRaw();
    if (!p) return {};
    if (id === 'coverage') return placeCoverage();
    const m = MAP_METRICS.find(x => x.id === id);
    if (!m) return {};
    const out = {};
    Object.entries(p.byLad).forEach(([code, d]) => {
      const v = m.pick(d);
      if (v != null && !Number.isNaN(v)) out[code] = v;
    });
    return out;
  }

  const metricSpec = id => MAP_METRICS.find(x => x.id === id) || MAP_METRICS[0];

  function placeCoverage() {
    const p = placesRaw();
    if (!p) return {};
    const out = {};
    Object.entries(p.byLad).forEach(([code, v]) => { out[code] = (v._systems || []).length; });
    return out;
  }

  function placeList() {
    const p = placesRaw();
    if (!p) return [];
    return Object.entries(p.byLad).map(([code, v]) => ({
      code, name: p.names[code] || code, systems: (v._systems || []).length,
    })).sort((a, b) => a.name.localeCompare(b.name));
  }

  /* What each system says about one district, in plain sentences. */
  function placeReport(code) {
    const p = placesRaw();
    if (!p || !p.byLad[code]) return null;
    const d = p.byLad[code];
    const n = v => v == null ? '—' : Number(v).toLocaleString('en-GB');
    const money = v => v == null ? '—' : (v >= 1e6 ? '£' + (v/1e6).toFixed(1) + 'm' : '£' + n(Math.round(v)));
    const items = [];
    // Care and SEND are published per upper-tier council. In a two-tier area
    // the district carries its county's figure; say so rather than imply it is
    // the district's own.
    const scope = c => c && c.figure_for === 'county'
      ? `${c.authority_name} County Council figure, shared by each of its districts` : null;
    const cap = d._capacity && (p.capacityTrend || {})[d._capacity.authority];

    if (d.catchment) {
      const c = d.catchment;
      items.push({system:'Catchment', metric: c.utilisation_pct + '%', label:'of school places in use',
        detail:`${n(c.pupils)} pupils in ${n(c.capacity)} places across ${n(c.schools)} schools`,
        caveat:`computed over the ${c.measured_pct}% of schools publishing both figures`,
        tone: c.utilisation_pct > 95 ? 'bad' : c.utilisation_pct > 88 ? 'warn' : 'ok'});
    }
    if (d.compass) {
      const c = d.compass;
      items.push({system:'Compass', metric:(c.projected_change_pct>0?'+':'') + c.projected_change_pct + '%',
        label:'projected change in EHC plans',
        detail:`${c.pupils_per_year > 0 ? '+' : ''}${c.pupils_per_year}/year over ${c.years} years, ${n(c.projected_change_3yr)} more in three`,
        caveat:'aggregate counts only — no individual record is used',
        scope: scope(c),
        tone: c.projected_change_pct > 30 ? 'bad' : c.projected_change_pct > 10 ? 'warn' : 'ok'});
    }
    if (d.plumbline) {
      const c = d.plumbline;
      items.push({system:'Plumbline', metric: c.statutory_pct + '%', label:'decided within 13 weeks without an extension',
        detail:`the published headline for this authority is ${c.headline_pct}%`,
        caveat:`${n(c.dwelling_decisions)} major dwelling decisions`,
        tone: (c.headline_pct - c.statutory_pct) > 50 ? 'bad' : 'warn'});
    }
    if (d.ledger) {
      const c = d.ledger;
      items.push({system:'Ledger', metric: money(c.total_amount), label:'in developer contributions',
        detail:`${n(c.contributions)} contributions, ${n(c.with_location)} of them mappable`,
        caveat:`an amount is stated on ${c.amount_coverage_pct}% of them`,
        tone: c.with_location === 0 ? 'bad' : 'ok'});
    }
    if (d.bulwark) {
      const c = d.bulwark;
      items.push({system:'Bulwark', metric: n(c.inspection_overdue), label:'flood inspections overdue',
        detail:`${n(c.assets)} defences, maintainer known on ${n(c.maintainer_known)}, owner on ${n(c.owner_known)}`,
        caveat:`condition graded on ${c.graded_pct}% of them${c.graded ? `, averaging grade ${c.mean_condition} on the Environment Agency’s scale of 1 (very good) to 5 (very poor)` : ''}`,
        tone: c.inspection_overdue > 100 ? 'bad' : c.inspection_overdue > 0 ? 'warn' : 'ok'});
    }
    if (d.highwater) {
      const c = d.highwater;
      items.push({system:'Highwater', metric: n(c.granted_against), label:'granted against flood advice',
        detail:`${n(c.objections)} objections, ${n(c.residential_units)} homes involved`,
        caveat:`${n(c.outcome_unknown)} outcomes were never recorded`,
        tone: c.granted_against > 5 ? 'bad' : c.granted_against > 0 ? 'warn' : 'ok'});
    }
    if (d.sightline) {
      const c = d.sightline;
      items.push({system:'Sightline', metric: n(c.water_objections), label:'water quality objections',
        detail:`${n(c.flood_objections)} flood objections, ${n(c.flood_outcome_unknown)} with no recorded outcome`,
        caveat:'water quality objections carry no outcome field at all',
        tone: c.water_objections > 0 ? 'warn' : 'ok'});
    }
    if (d.bellwether) {
      const c = d.bellwether;
      items.push({system:'Bellwether', metric: c.share_pct + '%', label:'of care beds with one group',
        detail:`${(c.group_name||'').replace('BRAND ','')} — ${n(c.beds)} of ${n(c.la_beds)} beds`,
        caveat: c.branded ? 'grouped by the regulator’s brand field' : 'this provider is unbranded, so counted alone',
        scope: scope(c),
        tone: c.share_pct > 40 ? 'bad' : c.share_pct > 25 ? 'warn' : 'ok'});
    }
    if (d.lastmile) {
      const c = d.lastmile;
      items.push({system:'Lastmile', metric: c.gigabit_pct + '%', label:'of premises gigabit-ready',
        detail: c.gigabit_pct_new_build != null
          ? `${c.gigabit_pct_new_build}% in postcodes with a new-build sale`
          : `${n(c.premises)} premises`,
        caveat:'joined on postcode, not property',
        tone: c.gigabit_pct < 80 ? 'warn' : 'ok'});
    }
    return {code, name: p.names[code] || code, items,
            silent: 13 - items.length,
            capacity: cap ? {authority: cap.name, county: d._capacity.figure_for === 'county',
                             years: cap.years || [], pct: cap.pct || []} : null};
  }

  function placeResolution() {
    const p = placesRaw();
    return p ? p.resolution : {};
  }

  function adminSummary() {
    const a = admin();
    if (!a) return null;
    const srcs = a.sources || [];
    const sys = a.systems || [];
    const lastRun = (a.runs || [])[0] || null;
    const tables = a.tables || [];
    return {
      sourcesTotal: srcs.length,
      sourcesOk: srcs.filter(s => s.ok).length,
      sourcesBlocked: srcs.filter(s => s.blocked).length,
      sourcesLogged: srcs.filter(s => s.provenance === 'logged').length,
      sourcesUnlogged: srcs.filter(s => s.provenance === 'unlogged').length,
      sourcesAbsent: srcs.filter(s => s.provenance === 'absent').length,
      sourcesWithData: srcs.filter(s => s.provenance !== 'absent').length,
      systemsBuilt: sys.filter(s => s.built).length,
      systemsTotal: sys.length,
      systemsMissingInputs: sys.filter(s => (s.missing_inputs || []).length).length,
      rowsHeld: tables.reduce((t, r) => t + (r.rows || 0), 0),
      tableCount: tables.length,
      reviewCount: (a.review || []).length,
      unregistered: (a.registry || {}).unregistered || [],
      truncated: (a.registry || {}).truncated || [],
      lastRun,
      runs: a.runs || [],
    };
  }

  /* Limits that are facts about the current output rather than the method.
     The static ones live in DETAIL; these are computed from the payload, so
     they cannot drift from the figures they qualify. Catchment's unplaced
     schools are the first: a reader who sees "483 not placed" with no reason
     would fairly take it for a failure, and most of them are not in England. */
  function liveLimits(id) {
    const out = [];
    if (id === 'catchment') {
      const nat = (sys('catchment') || {}).national || {};
      const r = nat.unplaced_by_reason;
      if (r && nat.schools_unplaced) {
        const n = v => Number(v || 0).toLocaleString('en-GB');
        const s = (v, one, many) => `${n(v)} ${Number(v) === 1 ? one : many}`;
        const parts = [];
        if (r.outside_great_britain) parts.push(`${n(r.outside_great_britain)} are outside Great Britain — British schools overseas, offshore schools and service schools abroad`);
        if (r.online_only) parts.push(`${n(r.online_only)} are online-only providers with no site`);
        if (r.in_wales) parts.push(`${n(r.in_wales)} are in Wales, outside this system’s England scope`);
        let text = `${s(nat.schools_unplaced, 'mainstream school is', 'mainstream schools are')} not placed in a district.`;
        if (parts.length) text += ` ${parts.join('; ')}.`;
        const eng = (r.postcode_not_in_register || 0) + (r.no_location_in_record || 0)
                  + (r.located_no_district || 0);
        if (eng) {
          const why = [];
          if (r.postcode_not_in_register) why.push(`${n(r.postcode_not_in_register)} carry a postcode the national register does not yet hold`);
          if (r.no_location_in_record) why.push(`${n(r.no_location_in_record)} have no location in their record`);
          if (r.located_no_district) why.push(`${n(r.located_no_district)} have a location but no district`);
          text += ` The other ${s(eng, 'is an English school', 'are English schools')} the place spine cannot locate: ${why.join(', and ')}.`;
        }
        // A reason this sentence does not name must not disappear from it: if
        // the parts stop adding up to the headline, say so.
        const counted = Object.values(r).reduce((a, v) => a + Number(v || 0), 0);
        if (counted !== Number(nat.schools_unplaced)) {
          text += ` (The reasons above account for ${n(counted)} of the ${n(nat.schools_unplaced)}.)`;
        }
        out.push(text);
      }
    }
    return out;
  }

  const _n = v => Number(v || 0).toLocaleString('en-GB');
  const _esc = v => String(v == null ? '' : v)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  const spineTiers = () => (data && data.spine) || {};
  const graph = () => (data && data.graph) || null;

  /* How a system's inputs arrived, built from the registry rather than
     asserted. The method pages used to say every source was "hashed so the
     exact file is recorded". Seven sources arrived by bulk import and carry no
     hash, which made that sentence false on eight of the thirteen systems. */
  function collectionNote(id) {
    const held = systemProvenance(id).filter(f => f.ok);
    if (!held.length) return null;
    const bulk = held.filter(f => !f.hashed);
    const lead = 'Every source behind this system is open to an anonymous request — no account, key or fee.';
    const names = bulk.map(f => _esc(f.name)).join('; ');
    const h = held.length - bulk.length;
    if (!bulk.length) return held.length === 1
      ? `${lead} Its one source was fetched through the registry, which hashes the bytes so the exact file is recorded.`
      : `${lead} All ${_n(held.length)} were fetched through the registry, which hashes the bytes so the exact file is recorded.`;
    if (!h) return held.length === 1
      ? `${lead} Its one source arrived by bulk import and carries no recorded hash (${names}).`
      : `${lead} None was fetched through the registry: all ${_n(held.length)} arrived by bulk import and carry no recorded hash (${names}).`;
    return `${lead} ${_n(h)} of the ${_n(held.length)} ${h === 1 ? 'was' : 'were'} fetched through the registry, which hashes the bytes so the exact file is recorded; `
      + `${bulk.length === 1 ? 'the other arrived by bulk import and carries' : `the other ${_n(bulk.length)} arrived by bulk import and carry`} no recorded hash (${names}).`;
  }

  /* What each system's place join achieved. Every district figure a system
     publishes rests on it, and it was published and shown nowhere: a reader of
     Sightline's map had no way to know a third of its authorities are not on
     it. The source's own names are listed and no reason is asserted for them,
     because the unmatched are not one kind of thing. */
  function placeJoinNote(id) {
    const r = placeResolution()[id];
    if (!r || !r.names) return null;
    const miss = r.names - r.matched;
    // Upper-tier systems are matched to councils, and a county's figures go to
    // every district it covers, so the note says how far they reach.
    const verb = r.counties != null ? 'matched a council' : 'matched a district';
    const cty = r.counties ? ` ${_n(r.counties)} ${r.counties === 1 ? 'is a county council, whose figures are' : 'are county councils, whose figures are'} shown on each of the ${_n(r.county_districts)} districts they cover, labelled as county figures.` : '';
    if (!miss) return `Place join: all ${_n(r.names)} authorities named in this system’s data ${verb}.${cty}`;
    const eg = (r.unmatched || []).filter(x => x && String(x).toLowerCase() !== 'unknown').slice(0, 4);
    return `Place join: ${_n(r.matched)} of ${_n(r.names)} authorities named in this system’s data ${verb} (${r.rate}%).${cty} `
      + `${_n(miss)} did not${eg.length ? `, among them ${eg.map(_esc).join(', ')}` : ''}; ${miss === 1 ? 'its figures are' : 'their figures are'} not on the district map.`;
  }

  /* Districts whose value for a metric is their county council's, so the map
     can say so on hover instead of implying the district's own figure. */
  function metricNotes(id) {
    const p = placesRaw();
    const m = MAP_METRICS.find(x => x.id === id);
    if (!p || !m || !m.system) return {};
    const key = String(m.system).toLowerCase(), out = {};
    Object.entries(p.byLad).forEach(([code, d]) => {
      const r = d[key];
      if (r && r.figure_for === 'county') out[code] = `${r.authority_name} County Council figure`;
    });
    return out;
  }

  const chains = () => (data && data.chains) || [];
  const reuse = () => (data && data.reuse) || null;
  const generated = () => (data && data.generated) || null;
  const builtSystems = () => (data && data.built_systems) || [];
  const error = () => (data && data.error) || null;

  /* The cross-checks the platform runs against its own output. Surfaced so an
     interface can show where the platform disagrees with itself rather than
     leaving a reader to add up two screens. */
  const contradictions = () => (data && data.contradictions) || null;
  const corrections = () => (data && data.corrections) || null;
  // What the platform found wrong with itself at publish, where each evidence
  // chain stops, and the snapshots that make builds comparable.
  const audit = () => (data && data.audit) || null;
  const gaps = () => (data && data.gaps) || null;
  const history = () => (data && data.history) || null;
  // Each system's headline as recorded at publish: source, checksum, steps, coverage.
  const evidenceSummary = () => (data && data.evidence) || null;
  const evidence = id => ((evidenceSummary() || {}).headlines || {})[id] || [];

  return {load, sys, has, pipeline, organisations, headlines, systemResult, sourceSummary, spineSummary,
          districtValues, districtLookup, chains, reuse, admin, adminSummary,
          placeCoverage, placeList, placeReport, placeResolution,
          mapMetrics, metricValues, metricSpec, metricProvenance,
          systemProvenance, systemMethod,
          generated, builtSystems, error, contradictions, corrections, liveLimits,
          collectionNote, placeJoinNote, spineTiers, graph, metricNotes, audit, gaps, history, evidence, evidenceSummary};
})();
