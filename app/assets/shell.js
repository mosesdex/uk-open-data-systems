/* The application shell: navigation, routing and the views that were missing.
 *
 * What this replaces: a single 8,500px page whose sidebar scrolled to anchors,
 * and four "views" (system, compare, organisations, search) that rendered into
 * a fixed full-screen overlay -- so opening any of them threw away the sidebar,
 * the breadcrumb and the search box.
 *
 * Now there are six destinations, each a URL, and every one of them keeps the
 * shell. Rendering is delegated to the modules that already do it well
 * (CARDS, JOINS, SYSVIEW, SystemPage, GT); this file owns arrangement, routing
 * and the views nobody had built yet.
 */
const Shell = (() => {
  const $  = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
  const esc = v => String(v == null ? '' : v)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  const num = v => v == null || Number.isNaN(Number(v)) ? '—' : Number(v).toLocaleString('en-GB');

  /* ---------------------------------------------------------------- nav ---- */
  const NAV = [
    { group: 'Explore', items: [
      { id: '',        icon: '◉', label: 'Overview' },
      { id: 'places',  icon: '▣', label: 'Places',        count: () => Platform.placeList().length },
      { id: 'systems', icon: '▦', label: 'Systems',       count: () => Platform.builtSystems().length },
      { id: 'orgs',    icon: '⬢', label: 'Organisations', count: () => (Platform.organisations() || []).length },
    ]},
    { group: 'Evidence', items: [
      // The count here is the number of sources that would not answer an
      // anonymous request. It is red because that is the product's own
      // headline caveat, and it belongs in front of people permanently.
      { id: 'sources', icon: '⛁', label: 'Sources', count: () => Platform.sourceSummary().total - Platform.sourceSummary().ok, alert: true },
      { id: 'method',  icon: '❋', label: 'Method' },
    ]},
  ];

  const TITLES = {
    '':        ['Explore', 'National picture'],
    places:    ['Explore · Places', 'Places'],
    systems:   ['Explore · Systems', 'The thirteen systems'],
    orgs:      ['Explore · Organisations', 'Organisations'],
    sources:   ['Evidence · Sources', 'Where every figure comes from'],
    method:    ['Evidence · Method', 'How GroundTruth works'],
    search:    ['Search', 'Search'],
  };

  function renderNav() {
    const box = $('.side__scroll');
    if (!box) return;
    box.innerHTML = NAV.map(g => `
      <div class="side__group">${esc(g.group)}</div>
      ${g.items.map(it => {
        let c = null;
        try { c = it.count ? it.count() : null; } catch (e) { c = null; }
        const badge = c ? `<span class="navi__ct${it.alert ? ' navi__ct--alert' : ''}">${num(c)}</span>` : '';
        return `<a class="navi" data-nav="${it.id}" href="#/${it.id}">
          <i class="navi__dot" aria-hidden="true"></i>${esc(it.label)}${badge}</a>`;
      }).join('')}
    `).join('') + `
      <div class="side__group">Jump to a system</div>
      <div id="navSystems">${systemNav()}</div>`;
  }

  /* The system list used to be anchors into one long page, with a scroll-spy
     keeping up. Each one is a destination now, so it is a link and nothing
     needs to watch the scroll position. */
  function systemNav() {
    return SYSTEMS.map(s => {
      const spec = (typeof CARDS !== 'undefined') && CARDS.SPEC && CARDS.SPEC[s.id];
      const ico = (spec && spec.icon) || '•';
      const dom = (spec && spec.domain) || s.dom || '';
      let fig = '';
      try {
        const r = Platform.systemResult(s.id);
        if (r && r.headline) fig = r.headline;
      } catch (e) { fig = ''; }
      return `<a class="navx" data-sysnav="${esc(s.id)}" href="#/systems/${esc(s.id)}">
        <span class="navx__ico" aria-hidden="true">${ico}</span>
        <span class="navx__tx"><span class="navx__nm">${esc(s.n)}</span>${
          dom ? `<span class="navx__dm">${esc(dom)}</span>` : ''}</span>
        ${fig ? `<span class="navx__fig">${esc(fig)}</span>` : ''}
      </a>`;
    }).join('');
  }

  function renderTabbar() {
    if ($('.tabbar')) return;
    const bar = document.createElement('nav');
    bar.className = 'tabbar';
    bar.setAttribute('aria-label', 'Sections');
    bar.innerHTML = [
      ['',        '◉', 'Overview'],
      ['places',  '▣', 'Places'],
      ['systems', '▦', 'Systems'],
      ['sources', '⛁', 'Sources'],
    ].map(([id, ic, l]) =>
      `<a data-tab="${id}" href="#/${id}"><i aria-hidden="true">${ic}</i><span>${l}</span></a>`).join('');
    document.body.appendChild(bar);
  }

  /* ------------------------------------------------------------- states ---- */
  const skeleton = (rows = 3) =>
    `<div class="skelcard">${'<div class="skel skel--90"></div><div class="skel skel--70"></div><div class="skel skel--45"></div>'.repeat(rows)}</div>`;

  const emptyFact = (title, body, href, cta) => `
    <div class="state state--fact">
      <div class="state__t">${esc(title)}</div>
      <p class="state__p" style="margin-inline:0">${body}</p>
      ${href ? `<p style="margin-top:.5rem"><a class="btn btn--ghost" href="${href}">${esc(cta || 'See why')} &rarr;</a></p>` : ''}
    </div>`;

  const emptyFilter = (what) => `
    <div class="state">
      <div class="state__t">Nothing matches those filters</div>
      <p class="state__p">No ${esc(what)} match every filter at once. Remove one to widen the search.</p>
      <p style="margin-top:.7rem"><button class="btn btn--ghost" data-clear-filters>Clear filters</button></p>
    </div>`;

  /* ------------------------------------------------------------ overview --- */
  function buildOverview() {
    const host = $('#viewOverview');
    if (!host || host.dataset.built) return;

    const a = Platform.adminSummary();
    const src = Platform.sourceSummary();
    const built = Platform.builtSystems().length;
    const contra = Platform.contradictions();
    const corr = Platform.corrections();
    const gen = Platform.generated();

    const stamp = $('#ovStamp');
    if (stamp && gen) stamp.textContent = 'computed ' + String(gen).slice(0, 10);

    const blocked = src.total - src.ok;
    const tiles = [
      { l: 'Systems with output', v: `${built} of ${SYSTEMS.length}`, s: 'each one measured, none estimated', k: built === SYSTEMS.length ? 'ok' : 'warn', href: '#/systems' },
      { l: 'Sources returning data', v: `${src.ok} of ${src.total}`, s: `${blocked} would not answer anonymously`, k: blocked ? 'warn' : 'ok', href: '#/sources' },
      { l: 'Rows held', v: a ? num(a.rowsHeld) : '—', s: a ? `across ${num(a.tableCount)} tables` : 'platform output not loaded', k: '' },
      { l: 'Districts covered', v: num(Platform.placeList().length), s: 'every English district with a figure', k: '', href: '#/places' },
    ];
    $('#ovTiles').innerHTML = tiles.map(t => {
      const inner = `<div class="tile__l">${esc(t.l)}</div><div class="tile__v">${esc(t.v)}</div>
        <div class="tile__s">${esc(t.s)}</div>`;
      const cls = `tile${t.k ? ' tile--' + t.k : ''}`;
      return t.href ? `<a class="${cls}" href="${t.href}">${inner}</a>` : `<div class="${cls}">${inner}</div>`;
    }).join('');

    /* Needs attention: the mobile app had this and the desktop never did. */
    const items = [];
    (src.rows || []).filter(r => r.blocked || (!r.ok && r.provenance !== 'unlogged')).forEach(r => items.push({
      sev: r.blocked ? 'bad' : 'warn',
      tag: r.blocked ? 'blocked' : 'not fetched',
      t: `${r.name} is not returning data`,
      s: [r.publisher, r.blocked].filter(Boolean).join(' · ').slice(0, 160),
      href: '#/sources',
    }));
    // Both arrive as objects carrying a summary plus their rows, not as arrays.
    ((contra && contra.results) || []).filter(c => c.run && c.disagreed > 0).forEach(c => items.push({
      sev: 'warn', tag: 'contradiction',
      t: `${c.quantity || c.check} disagrees across systems`,
      s: `${num(c.disagreed)} of ${num(c.compared)} compared · ${c.agreement_pct}% agree`,
      href: '#/sources',
    }));
    ((contra && contra.results) || []).filter(c => !c.run).forEach(c => items.push({
      sev: 'none', tag: 'not run',
      t: `${c.quantity || c.check} was not cross-checked`,
      s: c.note || 'the inputs this check needs are not both present',
      href: '#/sources',
    }));
    ((corr && corr.entries) || []).forEach(c => items.push({
      sev: 'ok', tag: 'correction',
      t: c.id ? String(c.id).replace(/-/g, ' ') : 'Correction applied',
      s: c.actually || c.believed || '', href: '#/method',
    }));

    $('#ovAttention').innerHTML = `
      <div class="vhead"><div>
        <div class="vhead__t" style="font-size:17px">Needs attention</div>
        <div class="vhead__s">Sources that failed, and the cross-checks the platform runs against its
        own output. Kept visible rather than hidden.</div></div>
        <div class="vhead__r"><span class="mono card__s">${items.length} OPEN</span></div></div>
      ${items.length ? `<div class="dt-wrap"><table class="dt">
        <thead><tr><th>Item</th><th>Detail</th><th style="width:1%">State</th></tr></thead>
        <tbody>${items.slice(0, 12).map(i => `<tr data-href="${i.href}">
          <td><b>${esc(i.t)}</b></td><td>${esc(i.s)}</td>
          <td><span class="st st--${i.sev}">${esc(i.tag)}</span></td></tr>`).join('')}</tbody>
      </table></div>` : `<div class="state"><div class="state__t">Nothing needs attention</div>
        <p class="state__p">Every registered source answered, and no cross-check disagreed.</p></div>`}`;

    $('#ovMap').innerHTML = `
      <div class="vhead"><div>
        <div class="vhead__t" style="font-size:17px">One place, every system</div>
        <div class="vhead__s">Every district, shaded by how many of the thirteen can say anything
        there.</div></div>
        <div class="vhead__r"><a class="btn btn--ghost" href="#/places">Open Places &rarr;</a></div></div>`;

    host.dataset.built = '1';
  }

  /* -------------------------------------------------------------- places --- */
  let placeFilter = { q: '', min: 0 };

  function buildPlaces() {
    const host = $('#viewPlaces');
    if (!host || $('#placeIndex')) return;
    const wrap = document.createElement('div');
    wrap.id = 'placeIndex';
    wrap.style.marginTop = '1.4rem';
    host.appendChild(wrap);
    renderPlaceIndex();
  }

  function renderPlaceIndex() {
    const box = $('#placeIndex');
    if (!box) return;
    const all = Platform.placeList();
    const rows = all.filter(p =>
      (!placeFilter.q || p.name.toLowerCase().includes(placeFilter.q.toLowerCase())) &&
      p.systems >= placeFilter.min);

    box.innerHTML = `
      <div class="vhead"><div>
        <div class="vhead__t" style="font-size:17px">Every district</div>
        <div class="vhead__s">Each row opens what all thirteen systems found there.</div></div></div>
      <div class="fbar">
        <button class="fchip${placeFilter.min === 0 ? ' is-on' : ''}" data-min="0">All districts</button>
        <button class="fchip${placeFilter.min === 5 ? ' is-on' : ''}" data-min="5">5+ systems</button>
        <button class="fchip${placeFilter.min === 9 ? ' is-on' : ''}" data-min="9">9+ systems</button>
        ${placeFilter.q ? `<button class="fchip is-on" data-clearq>“${esc(placeFilter.q)}” &times;</button>` : ''}
        <span class="fbar__n">${num(rows.length)} of ${num(all.length)}</span>
      </div>
      ${rows.length ? `<div class="dt-wrap"><table class="dt dt--compact">
        <thead><tr><th data-sort="name">District</th><th class="num" data-sort="systems">Systems reporting</th>
          <th style="width:1%">Coverage</th></tr></thead>
        <tbody>${rows.map(p => `<tr data-place="${esc(p.code)}">
          <td><b>${esc(p.name)}</b></td>
          <td class="num">${p.systems} of 13</td>
          <td><span class="st st--${p.systems >= 9 ? 'ok' : p.systems >= 5 ? 'warn' : 'none'}">${
            p.systems >= 9 ? 'broad' : p.systems >= 5 ? 'partial' : 'thin'}</span></td>
        </tr>`).join('')}</tbody></table></div>` : emptyFilter('districts')}`;

    box.querySelectorAll('[data-min]').forEach(b => b.onclick = () => {
      placeFilter.min = Number(b.dataset.min); renderPlaceIndex();
    });
    const cq = box.querySelector('[data-clearq]');
    if (cq) cq.onclick = () => { placeFilter.q = ''; renderPlaceIndex(); };
    const cf = box.querySelector('[data-clear-filters]');
    if (cf) cf.onclick = () => { placeFilter = { q: '', min: 0 }; renderPlaceIndex(); };
    box.querySelectorAll('[data-place]').forEach(tr => tr.onclick = () => openPlace(tr.dataset.place));
  }

  /* -------------------------------------------------- detail panel + prov --- */
  let panel, scrim;

  function ensurePanel() {
    if (panel) return;
    scrim = document.createElement('div');
    scrim.className = 'scrim';
    scrim.hidden = true;
    scrim.addEventListener('click', closePanel);
    panel = document.createElement('aside');
    panel.className = 'dpanel';
    panel.setAttribute('role', 'dialog');
    panel.setAttribute('aria-modal', 'false');
    panel.hidden = true;
    document.body.append(scrim, panel);
  }

  function openPanel(kicker, title, bodyHtml) {
    ensurePanel();
    panel.innerHTML = `
      <div class="dpanel__h">
        <div><div class="dpanel__k">${esc(kicker)}</div><div class="dpanel__t">${esc(title)}</div></div>
        <button class="iconbtn dpanel__x" data-close aria-label="Close">&times;</button>
      </div>
      <div class="dpanel__b">${bodyHtml}</div>`;
    panel.querySelector('[data-close]').onclick = closePanel;
    panel.hidden = false; scrim.hidden = false;
    requestAnimationFrame(() => { panel.classList.add('on'); scrim.classList.add('on'); });
    panel.querySelector('[data-close]').focus();
  }

  function closePanel() {
    if (!panel) return;
    panel.classList.remove('on'); scrim.classList.remove('on');
    setTimeout(() => { if (panel) { panel.hidden = true; scrim.hidden = true; } }, 180);
  }

  /* Every record ends at provenance. This is the claim the product is built on,
     so it gets a fixed place in the panel rather than a footnote. */
  function provenanceBlock(systemId) {
    const rows = Platform.systemProvenance(systemId) || [];
    const method = Platform.systemMethod(systemId);
    if (!rows.length && !method) return '';
    return `
      ${method ? `<div class="prov"><div class="prov__h">Method</div>
        <div style="padding:.7rem .75rem;font-size:12.5px;color:var(--ink-2);line-height:1.55">${esc(method)}</div></div>` : ''}
      <div class="prov"><div class="prov__h">Provenance · ${rows.length} source${rows.length === 1 ? '' : 's'}</div>
        ${rows.length ? rows.map(r => `<div class="prov__r">
          <span class="prov__k">Source</span><span><b>${esc(r.name)}</b><br>
            <span style="color:var(--ink-3)">${esc(r.publisher || '')}${r.licence ? ' · ' + esc(r.licence) : ''}</span></span>
          <span class="prov__k">Fetched</span><span class="mono">${r.fetched ? esc(String(r.fetched).slice(0, 19).replace('T', ' ')) : '—'}</span>
          <span class="prov__k">State</span><span><span class="st st--${r.ok ? 'ok' : 'bad'}">${esc(r.status)}</span></span>
        </div>`).join('') : `<div class="prov__r"><span class="prov__k">—</span>
          <span style="color:var(--ink-3)">No source is registered against this system yet.</span></div>`}
      </div>`;
  }

  function openPlace(code) {
    const rep = Platform.placeReport(code);
    if (!rep) { openPanel('Place', code, emptyFact('No figures for this district',
      'No system produced a value here. Districts with none are usually two-tier counties, where services are planned across several districts at once.')); return; }
    const body = `
      <div class="tiles" style="grid-template-columns:repeat(2,1fr)">
        <div class="tile tile--ok"><div class="tile__l">Systems reporting</div>
          <div class="tile__v">${rep.items.length} of 13</div></div>
        <div class="tile${rep.silent ? ' tile--warn' : ''}"><div class="tile__l">Silent here</div>
          <div class="tile__v">${rep.silent}</div></div>
      </div>
      <div class="dt-wrap" style="margin-top:1rem"><table class="dt dt--compact">
        <thead><tr><th>System</th><th>What it found</th><th class="num">Value</th></tr></thead>
        <tbody>${rep.items.map(i => `<tr data-sys="${esc(i.system.toLowerCase())}">
          <td><b>${esc(i.system)}</b></td>
          <td>${esc(i.label)}<br><span style="color:var(--ink-3);font-size:11.5px">${esc(i.caveat || '')}</span></td>
          <td class="num"><span class="st st--${i.tone === 'bad' ? 'bad' : i.tone === 'warn' ? 'warn' : 'ok'}">${esc(i.metric)}</span></td>
        </tr>`).join('')}</tbody></table></div>
      ${rep.silent ? emptyFact(`${rep.silent} systems have nothing to say here`,
        'That is a fact about the published data, not a gap in the platform — either no data reaches this district, or the system is planned at a different geography.',
        '#/sources', 'See the sources') : ''}`;
    openPanel('Place · ' + code, rep.name, body);
    panel.querySelectorAll('[data-sys]').forEach(tr => tr.onclick = () => {
      const id = tr.dataset.sys;
      if (SYSTEMS.some(s => s.id === id)) { closePanel(); location.hash = '#/systems/' + id; }
    });
  }

  /* The overview has always told people to "click any card to see the sources,
     the method, and what it cannot tell you". DETAIL held exactly that text for
     all thirteen systems and nothing ever called it. This is that panel. */
  function openSystemDetail(id) {
    const meta = SYSTEMS.find(x => x.id === id);
    const d = (typeof DETAIL !== 'undefined' && DETAIL[id]) || null;
    const r = Platform.systemResult(id);
    if (!meta) return;

    const limits = (d && d.limits) || [];
    const body = `
      ${r ? `<div class="tile tile--ok" style="margin-bottom:1rem">
        <div class="tile__l">${esc(r.label)}</div>
        <div class="tile__v">${esc(r.headline)}</div>
        ${r.sub ? `<div class="tile__s">${esc(r.sub)}</div>` : ''}</div>`
       : emptyFact('No measured output yet',
           'This system has not produced a figure in the current build. Nothing is estimated in its place.')}
      ${d ? `
        <h4 class="dpanel__k" style="margin-bottom:.3rem">The question</h4>
        <p style="font-size:14px;color:var(--ink);margin-bottom:.9rem">${esc(d.question)}</p>
        <h4 class="dpanel__k" style="margin-bottom:.3rem">Why it matters</h4>
        <p style="font-size:13px;color:var(--ink-2);line-height:1.6;margin-bottom:.9rem">${esc(d.why)}</p>
        <h4 class="dpanel__k" style="margin-bottom:.3rem">Method</h4>
        <p style="font-size:13px;color:var(--ink-2);line-height:1.6">${esc(d.method)}</p>` : ''}
      ${limits.length ? `<div class="state state--fact" style="margin-top:1rem">
        <div class="state__t">What it cannot tell you</div>
        <ul style="margin:.5rem 0 0;padding-left:1.1rem;font-size:12.5px;color:var(--ink-2);line-height:1.6">
          ${limits.map(l => `<li>${esc(l)}</li>`).join('')}</ul></div>` : ''}
      ${provenanceBlock(id)}
      <p style="margin-top:1.1rem"><a class="btn" href="#/systems/${esc(id)}" data-goto>Open the full system &rarr;</a></p>`;

    openPanel('System · ' + (meta.dom || ''), meta.n, body);
    const go = panel.querySelector('[data-goto]');
    if (go) go.onclick = () => closePanel();
  }

  /* -------------------------------------------------------------- router --- */
  const VIEWS = ['overview', 'places', 'systems', 'sources', 'method', 'detail'];

  function show(view) {
    VIEWS.forEach(v => {
      const el = $(`[data-view="${v}"]`);
      if (el) el.hidden = v !== view;
    });
    const host = $('#syshost');
    if (host) host.classList.toggle('on', view === 'detail');
    document.body.style.overflow = '';
  }

  function setChrome(key) {
    const [crumb, title] = TITLES[key] || TITLES[''];
    const c = $('.top__crumb'), t = $('.top__title');
    if (c) c.textContent = 'UK GroundTruth · ' + crumb;
    if (t) t.textContent = title;
    $$('[data-nav]').forEach(a => a.classList.toggle('is-on', a.dataset.nav === key));
    const activeSys = (location.hash.match(/^#\/systems\/([a-z0-9_-]+)/i) || [])[1] || '';
    $$('[data-sysnav]').forEach(a => a.classList.toggle('is-on', a.dataset.sysnav === activeSys));
    $$('[data-tab]').forEach(a => a.classList.toggle('is-on', a.dataset.tab === key));
    const s = $('.side');
    if (s) s.classList.remove('on');
  }

  /* Hashes the old build produced, kept working so nothing anyone saved breaks. */
  const LEGACY = {
    '#top': '#/method', '#hero': '#/method', '#spines': '#/method', '#chains': '#/method',
    '#place': '#/places', '#systems': '#/systems', '#compare': '#/systems',
    '#feeds': '#/sources', '#honesty': '#/sources', '#kpis': '#/',
    '#org': '#/orgs', '#search': '#/search',
  };

  function route() {
    const raw = location.hash || '#/';
    if (LEGACY[raw]) { location.replace(LEGACY[raw]); return; }
    const legacySys = raw.match(/^#system\/([a-z0-9_-]+)$/i);
    if (legacySys) { location.replace('#/systems/' + legacySys[1]); return; }
    const legacyOrg = raw.match(/^#org\/(.+)$/);
    if (legacyOrg) { location.replace('#/orgs/' + legacyOrg[1]); return; }

    const path = raw.replace(/^#\/?/, '').split('?')[0];
    const seg = path.split('/').filter(Boolean);
    const head = seg[0] || '';
    closePanel();

    if (head === '' ) {
      show('overview'); setChrome(''); safely(buildOverview, '#viewOverview'); scrollTop(); return;
    }

    if (head === 'places') {
      show('places'); setChrome('places'); safely(buildPlaces, '#placeIndex'); scrollTop();
      if (seg[1]) safely(() => openPlace(seg[1]));
      return;
    }

    if (head === 'systems') {
      if (seg[1] && SYSTEMS.some(s => s.id === seg[1])) {
        show('detail'); setChrome('systems');
        safely(() => { SystemPage.render(seg[1]); SysTabs.install(seg[1], seg[2] || 'summary'); }, '#syspage');
        scrollTop();
        return;
      }
      show('systems'); setChrome('systems'); scrollTop();
      return;
    }

    if (head === 'orgs') {
      show('detail'); setChrome('orgs');
      safely(() => { if (seg[1]) SystemPage.orgProfile(decodeURIComponent(seg.slice(1).join('/')));
                     else SystemPage.orgIndex(); }, '#syspage');
      scrollTop();
      return;
    }

    if (head === 'sources') { show('sources'); setChrome('sources'); scrollTop(); return; }
    if (head === 'method')  { show('method');  setChrome('method');  scrollTop(); return; }
    if (head === 'search')  { show('detail');  setChrome('search'); safely(SystemPage.search, '#syspage'); scrollTop(); return; }

    // Unknown route: say so, and offer the way back.
    show('detail'); setChrome('');
    const root = $('#syspage');
    if (root) root.innerHTML = `<div class="sp-top"><a class="sp-back" href="#/">&larr; Overview</a></div>
      <div class="state" style="margin-top:2rem"><div class="state__t">No such view</div>
      <p class="state__p"><span class="mono">${esc(raw)}</span> does not match anything this
      application serves.</p></div>`;
  }

  /* A view that fails to build should say so where it would have drawn, not
     take the whole shell down with it. */
  function safely(fn, targetSel) {
    try { fn(); }
    catch (err) {
      console.error('[shell] view failed to build', err);
      const t = targetSel && $(targetSel);
      if (t) t.innerHTML = `<div class="state state--bad"><div class="state__t">This view failed to build</div>
        <p class="state__p" style="margin-inline:0">${esc(err && err.message || err)}</p></div>`;
    }
  }

  const scrollTop = () => window.scrollTo({ top: 0, behavior: 'auto' });

  /* --------------------------------------------------------- system tabs --- */
  /* Twelve anchor "tabs" scrolled through thirteen sections rendered at once.
     These five actually switch, and each is a URL. */
  const SysTabs = (() => {
    /* SystemPage emits sections keyed exactly like this. Grouping is by exact
       key, not substring: "method" and "sources" would otherwise collide. */
    const GROUP = {
      overview: 'summary', join: 'summary', numbers: 'summary',
      data: 'data', explore: 'data',
      records: 'records',
      trends: 'trend', insights: 'trend',
      pipeline: 'method', sources: 'method', method: 'method', related: 'method',
    };
    const ORDER = ['summary', 'data', 'records', 'trend', 'method'];
    const LABEL = { summary: 'Summary', data: 'Data', records: 'Records', trend: 'Trend', method: 'Method' };

    const sections = root => $$('.sp-sec', root)
      .map(el => ({ el, key: el.id.replace(/^sp-/, '') }));

    function select(sysId, tab) {
      const root = $('#syspage');
      if (!root) return;
      if (!LABEL[tab]) tab = 'summary';
      sections(root).forEach(s => { s.el.hidden = (GROUP[s.key] || 'summary') !== tab; });
      $$('[data-systab]', root).forEach(b => b.classList.toggle('is-on', b.dataset.systab === tab));
      const live = $('#syspage .sp-sec:not([hidden])');
      if (live) live.scrollIntoView({ block: 'nearest' });
    }

    /* Replaces the anchor strip with tabs that actually switch. Twelve anchors
       into thirteen sections rendered at once is not a tab bar. */
    function install(sysId, tab) {
      const root = $('#syspage');
      if (!root) return;
      const strip = root.querySelector('.sp-nav');
      if (!strip) return;
      const present = new Set(sections(root).map(s => GROUP[s.key] || 'summary'));
      const tabs = ORDER.filter(t => present.has(t));
      if (tabs.length < 2) return;
      strip.innerHTML = tabs.map(t =>
        `<button class="sp-nav__i" type="button" data-systab="${t}">${LABEL[t]}</button>`).join('');
      strip.querySelectorAll('[data-systab]').forEach(b => b.onclick = () => {
        location.hash = `#/systems/${sysId}/${b.dataset.systab}`;
      });
      select(sysId, tabs.includes(tab) ? tab : 'summary');
    }
    return { install, select };
  })();

  /* ------------------------------------------------------------- palette --- */
  const Palette = (() => {
    let box, input, list, rows = [], cur = 0;

    function build() {
      if (box) return;
      box = document.createElement('div');
      box.className = 'pal';
      box.innerHTML = `
        <div class="pal__box" role="dialog" aria-label="Search">
          <div class="pal__in"><span aria-hidden="true">⌕</span>
            <input type="search" autocomplete="off" spellcheck="false"
                   placeholder="Search places, organisations, systems…" aria-label="Search">
          </div>
          <div class="pal__list"></div>
          <div class="pal__hint"><span><kbd>&uarr;</kbd><kbd>&darr;</kbd> move</span>
            <span><kbd>&crarr;</kbd> open</span><span><kbd>esc</kbd> back</span>
            <span style="margin-left:auto">Every result shows which systems hold it</span></div>
        </div>`;
      document.body.appendChild(box);
      input = box.querySelector('input');
      list = box.querySelector('.pal__list');
      box.addEventListener('click', e => { if (e.target === box) close(); });
      input.addEventListener('input', () => render(input.value));
      input.addEventListener('keydown', key);
    }

    function results(q) {
      const t = q.trim().toLowerCase();
      const out = [];
      const sys = SYSTEMS.filter(s => !t || s.n.toLowerCase().includes(t) || s.s.toLowerCase().includes(t) || s.dom.toLowerCase().includes(t));
      const places = Platform.placeList().filter(p => t && p.name.toLowerCase().includes(t));
      const orgs = (Platform.organisations() || []).filter(o =>
        t && String(o.name || '').toLowerCase().includes(t)).slice(0, 8);

      if (places.length) out.push(['Places', places.slice(0, 8).map(p => ({
        icon: '▣', t: p.name, s: `${p.systems} of 13 systems report here`, w: `${p.systems}/13`,
        go: () => { location.hash = '#/places'; setTimeout(() => openPlace(p.code), 30); } }))]);
      if (orgs.length) out.push(['Organisations', orgs.map(o => ({
        icon: '⬢', t: o.name, s: o.number ? 'Company ' + o.number : 'organisation',
        w: (o.systems || []).length ? (o.systems.length + ' sys') : '',
        go: () => { location.hash = '#/orgs/' + encodeURIComponent(o.number || o.name); } }))]);
      if (sys.length) out.push(['Systems', sys.slice(0, 8).map(s => ({
        icon: '▦', t: s.n, s: s.s, w: s.dom,
        go: () => { location.hash = '#/systems/' + s.id; } }))]);
      if (!t) out.push(['Go to', NAV.flatMap(g => g.items).map(i => ({
        icon: i.icon, t: i.label, s: 'destination', w: '',
        go: () => { location.hash = '#/' + i.id; } }))]);
      return out;
    }

    function render(q) {
      const groups = results(q);
      rows = []; cur = 0;
      if (!groups.length) {
        list.innerHTML = `<div class="state" style="margin:.6rem"><div class="state__t">No match</div>
          <p class="state__p">Nothing in the platform matches “${esc(q)}”. Try a district, a company, or a system.</p></div>`;
        return;
      }
      list.innerHTML = groups.map(([name, items]) =>
        `<div class="pal__g">${esc(name)} · ${items.length}</div>` +
        items.map(it => {
          const i = rows.push(it) - 1;
          return `<button class="pal__r" data-i="${i}">
            <span class="pal__ri" aria-hidden="true">${it.icon}</span>
            <span class="pal__rt"><b>${esc(it.t)}</b><span>${esc(it.s)}</span></span>
            <span class="pal__rw">${esc(it.w)}</span></button>`;
        }).join('')).join('');
      list.querySelectorAll('[data-i]').forEach(b =>
        b.onclick = () => { const it = rows[+b.dataset.i]; close(); it.go(); });
      mark();
    }

    function mark() {
      list.querySelectorAll('.pal__r').forEach((b, i) => b.classList.toggle('is-on', i === cur));
      const on = list.querySelector('.pal__r.is-on');
      if (on) on.scrollIntoView({ block: 'nearest' });
    }

    function key(e) {
      if (e.key === 'Escape') { e.preventDefault(); close(); return; }
      if (e.key === 'ArrowDown') { e.preventDefault(); cur = Math.min(cur + 1, rows.length - 1); mark(); return; }
      if (e.key === 'ArrowUp')   { e.preventDefault(); cur = Math.max(cur - 1, 0); mark(); return; }
      if (e.key === 'Enter' && rows[cur]) { e.preventDefault(); const it = rows[cur]; close(); it.go(); }
    }

    function open(seed = '') {
      build();
      box.classList.add('on');
      input.value = seed;
      render(seed);
      setTimeout(() => { input.focus(); input.select(); }, 20);
    }
    function close() { if (box) box.classList.remove('on'); }
    const isOpen = () => !!box && box.classList.contains('on');
    return { open, close, isOpen };
  })();

  /* ---------------------------------------------------------------- boot --- */
  function boot() {
    renderNav();
    renderTabbar();

    // The top bar input opens the palette rather than a full-page takeover.
    const top = $('#topSearch');
    if (top) {
      const openWith = () => { const v = top.value; top.value = ''; top.blur(); Palette.open(v); };
      top.addEventListener('focus', () => Palette.open(''));
      top.addEventListener('input', openWith);
    }
    addEventListener('keydown', e => {
      if (e.key === '/' && !/^(INPUT|TEXTAREA|SELECT)$/.test(e.target.tagName || '') && !Palette.isOpen()) {
        e.preventDefault(); Palette.open('');
      }
      if (e.key === 'Escape') { if (Palette.isOpen()) Palette.close(); else closePanel(); }
    });

    // Rows that carry a destination behave like links.
    document.addEventListener('click', e => {
      if (!e.target.closest) return;
      const tr = e.target.closest('tr[data-href]');
      if (tr) { location.hash = tr.dataset.href; return; }
      // A figure card explains itself in place rather than navigating away.
      const kpi = e.target.closest('.kpi[data-sysid]');
      if (kpi) { openSystemDetail(kpi.dataset.sysid); }
    });
    document.addEventListener('keydown', e => {
      if (e.key !== 'Enter' && e.key !== ' ') return;
      const kpi = e.target.closest && e.target.closest('.kpi[data-sysid]');
      if (kpi) { e.preventDefault(); openSystemDetail(kpi.dataset.sysid); }
    });

    // The district picker inside Places feeds the same index the table uses,
    // instead of being a third unrelated search box.
    const ps = $('#placeSearch');
    if (ps) ps.addEventListener('input', () => { placeFilter.q = ps.value; renderPlaceIndex(); });

    addEventListener('hashchange', route);
    route();
  }

  return { boot, route, openPlace, openSystemDetail, openPanel, closePanel, provenanceBlock, Palette, SysTabs };
})();
