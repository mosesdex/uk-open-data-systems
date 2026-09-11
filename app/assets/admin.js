/* The admin console, on the same shell as the public app.
 *
 * It was already the better-organised of the two -- grouped navigation with
 * live badges, a figure row, real tables, status chips -- which is why that
 * language was promoted to the public app rather than replaced. What it shared
 * with the old public app was the architecture underneath: a sidebar of anchors
 * scrolling one 4,000px page, no landmark, no search, no routes.
 *
 * Everything an operator looks up is now a destination, a palette entry and,
 * where there is more to say than a row can hold, a detail panel.
 */
const Admin = (() => {
  const $  = (s, r = document) => r.querySelector(s);
  const esc = Shell.esc, num = Shell.num;

  const A = () => Platform.adminSummary() || {};
  const raw = () => Platform.admin() || {};

  const NAV = [
    { group: 'Operations', items: [
      { id: '',        icon: '◉', label: 'Control room' },
      { id: 'runs',    icon: '⟳', label: 'Ingest runs',  count: () => (A().runs || []).length },
      // Blocked sources are also absent, so adding the two counted them twice.
      { id: 'sources', icon: '⛁', label: 'Data sources', count: () => (raw().sources || []).filter(s => s.blocked || s.provenance === 'absent').length, alert: true },
    ]},
    { group: 'Platform', items: [
      { id: 'systems',   icon: '▦', label: 'Systems',         count: () => A().systemsTotal },
      { id: 'review',    icon: '⚖', label: 'Match review',    count: () => A().reviewCount, alert: true },
      { id: 'storage',   icon: '▤', label: 'Storage',         count: () => A().tableCount },
      { id: 'integrity', icon: '❖', label: 'Reproducibility', count: () => (A().unregistered || []).length, alert: true },
      { id: 'audit',     icon: '✓', label: 'Audit',           count: () => { const s = (Platform.audit() || {}).summary || {}; return (s.critical || 0) + (s.major || 0); }, alert: true },
    ]},
  ];

  const TITLES = {
    '':          ['Admin console · 127.0.0.1', 'Control room'],
    runs:        ['Admin · Operations',        'Ingest runs'],
    sources:     ['Admin · Operations',        'Data sources'],
    systems:     ['Admin · Platform',          'Systems'],
    review:      ['Admin · Platform',          'Match review'],
    storage:     ['Admin · Platform',          'Storage'],
    integrity:   ['Admin · Platform',          'Reproducibility'],
    audit:       ['Admin · Platform',          'Audit'],
  };

  /* Hashes the old build produced. An operator's bookmark keeps working. */
  const LEGACY = {
    '#ops': '#/', '#runs': '#/runs', '#sources': '#/sources', '#systems': '#/systems',
    '#review': '#/review', '#storage': '#/storage', '#integrity': '#/integrity',
    '#audit': '#/audit',
  };

  const VIEWS = ['ops', 'runs', 'sources', 'systems', 'review', 'storage', 'integrity', 'audit'];

  /* --------------------------------------------------------- attention ---- */
  function buildOps() {
    const a = A(), r = raw();
    const stamp = $('#opsStamp');
    const gen = Platform.generated();
    if (stamp && gen) stamp.textContent = 'database read ' + String(gen).slice(0, 10);

    const items = [];
    (r.sources || []).filter(s => s.blocked).forEach(s => items.push({
      sev: 'bad', tag: 'blocked', t: s.name,
      s: [s.publisher, s.blocked].filter(Boolean).join(' · '), go: '#/sources' }));
    (r.sources || []).filter(s => !s.blocked && s.provenance === 'absent').forEach(s => items.push({
      sev: 'warn', tag: 'never fetched', t: s.name,
      s: (s.publisher || '') + ' · registered, no data on disk', go: '#/sources' }));
    (r.sources || []).filter(s => s.provenance === 'unlogged').forEach(s => items.push({
      sev: 'warn', tag: 'unlogged', t: s.name,
      s: 'holds data with no fetch record — backfill wrote it directly', go: '#/integrity' }));
    if (a.reviewCount) items.push({
      sev: 'warn', tag: 'review', t: `${num(a.reviewCount)} matches await a person`,
      s: 'real ambiguity in the data; nothing has been merged', go: '#/review' });
    (a.unregistered || []).forEach(u => items.push({
      sev: 'warn', tag: 'unregistered', t: String(u), s: 'on disk, absent from the source registry', go: '#/integrity' }));
    (a.truncated || []).forEach(u => items.push({
      sev: 'bad', tag: 'truncated', t: String(u), s: 'the fetch did not complete', go: '#/integrity' }));
    // The audit's serious findings. Registry-vs-log ones restate the source
    // rows above, so they are not listed twice.
    ((Platform.audit() || {}).findings || [])
      .filter(f => (f.severity === 'critical' || f.severity === 'major') && f.check !== 'registry-vs-log')
      .forEach(f => items.push({ sev: 'bad', tag: f.check, t: f.subject, s: f.summary, go: '#/audit' }));

    // Blocking problems first: a list shown twenty at a time must not bury them
    // under warnings, which is what happened once the audit's findings joined it.
    items.sort((x, y) => (x.sev === 'bad' ? 0 : 1) - (y.sev === 'bad' ? 0 : 1));
    const host = $('#opsAttention');
    if (!host) return;
    host.innerHTML = `
      <div class="vhead"><div><div class="vhead__t" style="font-size:17px">Waiting on a person</div>
        <div class="vhead__s">Everything the platform cannot resolve by itself. Nothing here has
        been merged, filled in or guessed.</div></div>
        <div class="vhead__r"><span class="mono card__s">${items.length} OPEN</span></div></div>
      ${items.length ? `<div class="dt-wrap"><table class="dt dt--compact">
        <thead><tr><th>Item</th><th>Detail</th><th style="width:1%">State</th></tr></thead>
        <tbody>${items.slice(0, 20).map(i => `<tr data-href="${i.go}">
          <td><b>${esc(i.t)}</b></td><td>${esc(String(i.s).slice(0, 180))}</td>
          <td><span class="st st--${i.sev}">${esc(i.tag)}</span></td></tr>`).join('')}</tbody>
      </table></div>${items.length > 20 ? `<p class="card__s" style="margin-top:.5rem">And ${items.length - 20} more, under Data sources, Reproducibility and Audit.</p>` : ''}` : `<div class="state"><div class="state__t">Nothing is waiting</div>
        <p class="state__p">Every source fetched, every match resolved, every artefact registered.</p></div>`}`;
  }

  /* -------------------------------------------------------------- audit --- */
  const SEV = { critical: 'bad', major: 'bad', minor: 'warn', note: 'none' };

  function buildAudit() {
    const host = $('#auditBody');
    if (!host) return;
    const au = Platform.audit();
    if (!au || au.error) {
      host.innerHTML = `<div class="state"><div class="state__t">${au ? 'The audit failed to run' : 'This build carries no audit'}</div>
        <p class="state__p">${au ? esc(au.error) : 'It runs on every <span class="mono">gt publish</span>.'}</p></div>`;
      return;
    }
    const s = au.summary || {}, by = s.by_severity || {}, fs = au.findings || [];
    const skipped = au.checks_skipped || [];
    host.innerHTML = `
      <div class="tiles" style="grid-template-columns:repeat(4,minmax(0,1fr))">
        ${['critical', 'major', 'minor', 'note'].map(k => `<div class="tile${by[k] && SEV[k] !== 'none' ? ' tile--' + SEV[k] : ''}">
          <div class="tile__l">${k}</div><div class="tile__v">${num(by[k] || 0)}</div></div>`).join('')}
      </div>
      <p class="card__s" style="margin:.9rem 0">${num(s.checks_run || 0)} checks ran against the database and the published file${skipped.length ? `; ${num(skipped.length)} could not run (${skipped.map(c => esc(c.check)).join(', ')})` : ''}. Nothing is suppressed: a finding leaves this list when what it describes is fixed.</p>
      ${fs.length ? `<div class="dt-wrap"><table class="dt dt--compact">
        <thead><tr><th style="width:1%">Severity</th><th>Subject</th><th>Finding</th></tr></thead>
        <tbody>${fs.map((f, i) => `<tr data-finding="${i}" style="cursor:pointer">
          <td><span class="st st--${SEV[f.severity] || 'none'}">${esc(f.severity)}</span></td>
          <td class="mono" style="font-size:11.5px;word-break:break-all">${esc(f.subject)}</td>
          <td>${esc(f.summary)}<br><span style="color:var(--ink-3);font-size:11.5px">${esc(f.check)}</span></td></tr>`).join('')}</tbody>
      </table></div>` : `<div class="state"><div class="state__t">No findings</div></div>`}`;
  }

  function openFinding(f) {
    if (!f) return;
    const tone = SEV[f.severity] && SEV[f.severity] !== 'none' ? ' tile--' + SEV[f.severity] : '';
    Shell.openPanel('Audit · ' + f.check, f.subject, `
      <div class="tile${tone}"><div class="tile__l">${esc(f.severity)}</div>
        <div class="tile__v" style="font-size:16px;line-height:1.35">${esc(f.summary)}</div></div>
      <div class="prov" style="margin-top:1rem"><div class="prov__h">Evidence</div>
        <div class="prov__r"><span class="mono" style="font-size:12px;white-space:pre-wrap;word-break:break-word">${esc(f.evidence || '—')}</span></div></div>
      <div class="prov" style="margin-top:1rem"><div class="prov__h">Remedy</div>
        <div class="prov__r"><span style="font-size:12.5px">${esc(f.remedy || '—')}</span></div></div>`);
  }

  /* One snapshot per publish: the row count and content hash of every table. */
  function buildHistory() {
    const host = $('#histBody');
    if (!host) return;
    const h = Platform.history(), snaps = (h && h.snapshots) || [];
    host.innerHTML = !snaps.length
      ? `<div class="state"><div class="state__t">No snapshots recorded</div>
          <p class="state__p">${h && h.error ? esc(h.error) : 'One is taken on every publish.'}</p></div>`
      : `<div class="dt-wrap"><table class="dt dt--compact">
          <thead><tr><th>Taken</th><th>Label</th><th>Code</th><th class="num">Tables</th><th class="num">Rows</th></tr></thead>
          <tbody>${snaps.map(x => `<tr><td class="mono" style="font-size:11.5px">${esc(String(x.taken_at || '').slice(0, 16).replace('T', ' '))}</td>
            <td>${esc(x.label || '—')}</td><td class="mono" style="font-size:11.5px">${esc(x.code_version || '—')}</td>
            <td class="num">${num(x.tables || 0)}</td><td class="num">${num(x.rows || 0)}</td></tr>`).join('')}</tbody></table></div>`;
  }

  /* ------------------------------------------------------------ panels ---- */
  function openRun(id) {
    const run = (A().runs || []).find(r => String(r.run_id || r.id) === String(id));
    if (!run) return;
    const rows = Object.entries(run).filter(([k]) => k !== 'sources_detail');
    Shell.openPanel('Ingest run', String(run.run_id || run.id), `
      <div class="tiles" style="grid-template-columns:repeat(2,1fr)">
        <div class="tile tile--ok"><div class="tile__l">Succeeded</div>
          <div class="tile__v">${num(run.succeeded)}</div></div>
        <div class="tile${run.failed ? ' tile--bad' : ''}"><div class="tile__l">Failed</div>
          <div class="tile__v">${num(run.failed)}</div></div>
      </div>
      <div class="prov" style="margin-top:1rem"><div class="prov__h">Every field this run recorded</div>
        ${rows.map(([k, v]) => `<div class="prov__r"><span class="prov__k">${esc(k)}</span>
          <span class="mono" style="font-size:12px">${esc(v == null ? '—' : String(v))}</span></div>`).join('')}
      </div>`);
  }

  function openSource(name) {
    const s = (raw().sources || []).find(x => x.name === name);
    if (!s) return;
    const state = s.blocked ? ['bad', 'blocked'] :
                  s.ok ? ['ok', 'HTTP ' + s.http_status] :
                  s.provenance === 'unlogged' ? ['warn', 'in use, unlogged'] : ['warn', 'never fetched'];
    Shell.openPanel('Source · ' + (s.publisher || ''), s.name, `
      <div class="tile tile--${state[0] === 'ok' ? 'ok' : state[0] === 'bad' ? 'bad' : 'warn'}">
        <div class="tile__l">State</div><div class="tile__v" style="font-size:19px">${esc(state[1])}</div>
        ${s.blocked ? `<div class="tile__s">${esc(s.blocked)}</div>` : ''}</div>
      ${s.provenance === 'unlogged' ? Shell.emptyFact('Holds data with no fetch record',
        'A backfill wrote this file directly rather than through the fetch log, so the platform cannot say when it arrived or from where. That is a gap in provenance, not in the data.') : ''}
      <div class="prov" style="margin-top:1rem"><div class="prov__h">Registry entry</div>
        ${[['Publisher', s.publisher], ['Licence', s.licence], ['Role', s.role], ['Cadence', s.cadence],
           ['Systems', s.systems], ['Last fetch', s.fetched_at], ['Bytes', s.bytes_len || s.disk_bytes],
           ['Provenance', s.provenance],
           ['Served by', s.authority === 'third party' ? 'a third party, not the publisher' : s.authority === 'delegated' ? 'the publisher, through hosting it runs elsewhere' : s.authority === 'publisher' ? 'the publisher' : null]]
          .map(([k, v]) => `<div class="prov__r"><span class="prov__k">${esc(k)}</span>
            <span style="font-size:12.5px">${v == null || v === '' ? '—' : esc(String(v))}</span></div>`).join('')}
      </div>`);
  }

  function openTable(name) {
    const t = (raw().tables || []).find(x => (x.table || x.name) === name);
    if (!t) return;
    Shell.openPanel('Table', name, `
      <div class="tiles" style="grid-template-columns:repeat(2,1fr)">
        <div class="tile"><div class="tile__l">Rows</div><div class="tile__v">${num(t.rows)}</div></div>
        <div class="tile"><div class="tile__l">Layer</div><div class="tile__v" style="font-size:18px">${esc(t.layer || '—')}</div></div>
      </div>
      <div class="prov" style="margin-top:1rem"><div class="prov__h">Every field recorded for this table</div>
        ${Object.entries(t).map(([k, v]) => `<div class="prov__r"><span class="prov__k">${esc(k)}</span>
          <span class="mono" style="font-size:12px">${esc(v == null ? '—' : String(v))}</span></div>`).join('')}
      </div>`);
  }

  /* ----------------------------------------------------------- palette ---- */
  function palette(t) {
    const a = A(), r = raw(), out = [];
    const runs = (a.runs || []).filter(x => !t || String(x.run_id || x.id).toLowerCase().includes(t));
    const srcs = (r.sources || []).filter(x => !t || String(x.name).toLowerCase().includes(t)
                  || String(x.publisher || '').toLowerCase().includes(t));
    const tbls = (r.tables || []).filter(x => t && String(x.table || x.name).toLowerCase().includes(t));

    if (srcs.length) out.push(['Sources', srcs.slice(0, 8).map(s => ({
      icon: '⛁', t: s.name, s: s.publisher || '',
      w: s.blocked ? 'blocked' : s.ok ? 'ok' : 'no data',
      go: () => { location.hash = '#/sources'; setTimeout(() => openSource(s.name), 30); } }))]);
    if (tbls.length) out.push(['Tables', tbls.slice(0, 8).map(x => ({
      icon: '▤', t: x.table || x.name, s: (x.layer || '') + ' layer', w: num(x.rows),
      go: () => { location.hash = '#/storage'; setTimeout(() => openTable(x.table || x.name), 30); } }))]);
    if (t && runs.length) out.push(['Ingest runs', runs.slice(0, 6).map(x => ({
      icon: '⟳', t: String(x.run_id || x.id), s: String(x.started || ''),
      w: (x.failed ? x.failed + ' failed' : 'clean'),
      go: () => { location.hash = '#/runs'; setTimeout(() => openRun(x.run_id || x.id), 30); } }))]);
    if (!t) out.push(['Go to', NAV.flatMap(g => g.items).map(i => ({
      icon: i.icon, t: i.label, s: 'destination', w: '',
      go: () => { location.hash = '#/' + i.id; } }))]);
    return out;
  }

  /* ------------------------------------------------------------- routes --- */
  function onRoute(head, seg, api) {
    if (!VIEWS.includes(head === '' ? 'ops' : head)) return false;
    const view = head === '' ? 'ops' : head;
    api.show(view);
    api.setChrome(head);
    if (view === 'ops') buildOps();
    if (view === 'audit') buildAudit();
    if (view === 'integrity') buildHistory();
    // Every destination gets exactly one h1, naming the view it is on. The
    // card headings inside stay h2 and below.
    promoteHeading(view, (TITLES[head] || TITLES[''])[1]);
    api.scrollTop();
    return true;
  }

  /* The section cards were written for one long page, so their titles are
     divs. On a routed view the first of them is the page heading. */
  function promoteHeading(view, label) {
    document.querySelectorAll('[data-view] h1.vhead__t[data-auto]').forEach(h => h.remove());
    const host = document.querySelector(`[data-view="${view}"]`);
    if (!host || host.querySelector('h1')) return;
    const h = document.createElement('h1');
    h.className = 'vhead__t';
    h.setAttribute('data-auto', '');
    h.style.cssText = 'position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap';
    h.textContent = label;
    host.prepend(h);
  }

  function boot() {
    Shell.boot({
      nav: NAV, titles: TITLES, legacy: LEGACY, views: VIEWS,
      crumb: 'UK GroundTruth',
      systemList: false,
      tabs: [['', '◉', 'Control'], ['sources', '⛁', 'Sources'],
             ['review', '⚖', 'Review'], ['storage', '▤', 'Storage']],
      palette, onRoute,
    });

    // Rows in the operator's tables open the record behind them.
    document.addEventListener('click', e => {
      if (!e.target.closest) return;
      // Rows open their panel from here, after the shell's own click handling;
      // a handler on the row itself fires first and the shell then closes it.
      const tr = e.target.closest('tr[data-run], tr[data-src], tr[data-tbl], tr[data-finding]');
      if (!tr) return;
      if (tr.dataset.run) openRun(tr.dataset.run);
      else if (tr.dataset.src) openSource(tr.dataset.src);
      else if (tr.dataset.tbl) openTable(tr.dataset.tbl);
      else if (tr.dataset.finding != null) openFinding(((Platform.audit() || {}).findings || [])[+tr.dataset.finding]);
    });
  }

  return { boot, openRun, openSource, openTable };
})();
