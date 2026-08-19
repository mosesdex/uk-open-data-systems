/* Reads what the platform actually computed.
   Every figure rendered through this module comes from a gold table via
   platform.json. Where a system produced no output the panel says so, rather
   than falling back to a number typed in by hand. */
const Platform = (() => {
  let data = null;

  async function load(path = 'data/platform.json') {
    if (data) return data;
    try {
      const r = await fetch(path);
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
      system: 'Plumbline', label: 'Decided within the statutory deadline',
      value: p.statutory_pct, suffix: '%',
      note: `published headline is ${p.headline_pct}%`});

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
        return {headline: d.statutory_pct + '%', label: 'decided within the legal deadline',
          sub: `published headline is ${d.headline_pct}%`};
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

  const chains = () => (data && data.chains) || [];
  const reuse = () => (data && data.reuse) || null;
  const generated = () => (data && data.generated) || null;
  const builtSystems = () => (data && data.built_systems) || [];
  const error = () => (data && data.error) || null;

  return {load, sys, has, headlines, systemResult, sourceSummary, spineSummary,
          districtValues, districtLookup, chains, reuse, generated,
          builtSystems, error};
})();
