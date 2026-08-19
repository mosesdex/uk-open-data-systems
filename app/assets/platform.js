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

  const chains = () => (data && data.chains) || [];
  const reuse = () => (data && data.reuse) || null;
  const generated = () => (data && data.generated) || null;
  const builtSystems = () => (data && data.built_systems) || [];
  const error = () => (data && data.error) || null;

  return {load, sys, has, headlines, sourceSummary, spineSummary,
          districtValues, districtLookup, chains, reuse, generated,
          builtSystems, error};
})();
