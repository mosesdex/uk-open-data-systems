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
  const num = v => v == null || Number.isNaN(Number(v)) ? 'n/a' : Number(v).toLocaleString('en-GB');

  /* ---------------------------------------------------------------- nav ---- */
  // The drawer used to list six destinations by a hardcoded id ("#/" + id),
  // three of which (systems, sources, method) had been retired and now only
  // redirect elsewhere -- so "What it answers" landed on the home page and
  // "Sources"/"Method" both landed on the same "About" entry already below
  // them. This lists the structure the site now has instead: the front page,
  // compare, unusual, about and organisations, each with an ORDERED LIST of
  // candidate hrefs in `candidates` -- the same firstServable idea
  // app/assets/lib/routes.js applies to URLs and renderTabbar already applies
  // to the bottom bar -- so renderNav() picks a route that actually renders
  // today instead of a hardcoded href that might redirect. A count is kept
  // only where it names a real, useful quantity (districts, organisations);
  // "About" and "What looks unusual" are not collections and carry none.
  const NAV_PUBLIC = [
    { group: 'Explore', items: [
      { id: '',        candidates: ['#/'],       icon: '◉', label: 'Find your area' },
      { id: 'compare', candidates: ['#/compare'], icon: '⇄', label: 'Compare every district', count: () => Platform.placeList().length },
      { id: 'unusual', candidates: ['#/unusual'], icon: '◆', label: 'What looks unusual' },
      { id: 'about',   candidates: ['#/about'],   icon: 'ⓘ', label: 'How this is built' },
      { id: 'orgs',    candidates: ['#/orgs'],    icon: '⬢', label: 'Organisations', count: () => (Platform.organisations() || []).length },
    ]},
  ];

  const TITLES_PUBLIC = {
    '':        ['Explore', 'Find your area'],
    places:    ['Explore · Places', 'Places'],
    systems:   ['Explore · What it answers', 'The thirteen questions'],
    orgs:      ['Explore · Organisations', 'Organisations'],
    sources:   ['Evidence · Sources', 'Where every figure comes from'],
    method:    ['Evidence · Method', 'How GroundTruth works'],
    search:    ['Search', 'Search'],
    compare:   ['Explore · Compare', 'Compare every district'],
    unusual:   ['Explore · Unusual', 'What looks unusual right now'],
    about:     ['Evidence · How this is built', 'How this is built'],
  };

  /* One shell, two consoles. The public app and the admin console are the same
     product and were two implementations of a sidebar, a top bar and a router.
     Everything below is driven by this config instead. */
  const DEFAULTS = {
    nav: null, titles: null, views: null, legacy: null,
    // Three destinations, not the old four: the front page now carries the
    // navigation, so the bottom bar only needs the way in, the way to see
    // every district side by side, and the way to how this is built.
    // Each item's first element is an ORDERED LIST of candidate hrefs, best
    // first, the same idea app/assets/lib/routes.js applies to URLs:
    // renderTabbar picks the first candidate whose route can actually render
    // today, so a tab degrades to a working link instead of dead-ending, and
    // upgrades itself once a later task adds the better route's handler.
    tabs: [
      [['#/'], '◉', 'Find'],
      [['#/compare', '#/places'], '⇄', 'Compare'],
      [['#/about', '#/method'], 'ⓘ', 'About'],
    ],
    crumb: 'UK GroundTruth',
    // Return [[groupName, items]] for the palette, or null to use the default.
    palette: null,
    // Handle a route; return true if it was handled. Falls through to the
    // built-in public routes when it returns anything else.
    onRoute: null,
  };
  let CFG = DEFAULTS;
  const nav = () => CFG.nav || NAV_PUBLIC;
  const titles = () => CFG.titles || TITLES_PUBLIC;
  const views = () => CFG.views || VIEWS_PUBLIC;
  const legacy = () => CFG.legacy || LEGACY_PUBLIC;

  function renderNav() {
    const box = $('.side__scroll');
    if (!box) return;
    // Same degrade-and-upgrade pattern as renderTabbar below: pick the first
    // candidate href ROUTER_HEADS can render today, and drop an item entirely
    // rather than emit a link nothing can serve.
    const lib = window.GT_LIB || {};
    const heads = lib.ROUTER_HEADS || FALLBACK_HEADS;
    const pick = lib.firstServable || fallbackFirstServable;
    const canRender = head => heads.has(head);
    box.innerHTML = nav().map(g => `
      <div class="side__group">${esc(g.group)}</div>
      ${g.items.map(it => {
        const href = pick(it.candidates || [`#/${it.id}`], canRender);
        if (!href) return '';
        const key = href.slice(2).split('/')[0];
        let c = null;
        try { c = it.count ? it.count() : null; } catch (e) { c = null; }
        const badge = c ? `<span class="navi__ct${it.alert ? ' navi__ct--alert' : ''}">${num(c)}</span>` : '';
        return `<a class="navi" data-nav="${key}" href="${href}">
          <i class="navi__dot" aria-hidden="true"></i>${esc(it.label)}${badge}</a>`;
      }).join('')}
    `).join('') + (CFG.systemList === false ? '' : `
      <div class="side__group">Jump to a question</div>
      <div id="navSystems">${systemNav()}</div>`);
  }

  /* The system list used to be anchors into one long page, with a scroll-spy
     keeping up. Each one is a destination now, so it is a link and nothing
     needs to watch the scroll position. */
  function systemNav() {
    // #/systems/<id> is a renamed route (app/assets/lib/routes.js) that now
    // redirects to #/questions/<id>: linking straight at the renamed route
    // would put a redirecting link in the drawer, so this picks the first
    // candidate that can render today, same as buildHome()'s question list.
    const lib = window.GT_LIB || {};
    const heads = lib.ROUTER_HEADS || FALLBACK_HEADS;
    const pick = lib.firstServable || fallbackFirstServable;
    const canRender = head => heads.has(head);
    return SYSTEMS.map(s => {
      const spec = (typeof CARDS !== 'undefined') && CARDS.SPEC && CARDS.SPEC[s.id];
      const ico = (spec && spec.icon) || '•';
      const dom = (spec && spec.domain) || s.dom || '';
      let fig = '';
      try {
        const r = Platform.systemResult(s.id);
        if (r && r.headline) fig = r.headline;
      } catch (e) { fig = ''; }
      const href = pick(['#/questions/' + s.id, '#/systems/' + s.id], canRender) || ('#/systems/' + s.id);
      return `<a class="navx" data-sysnav="${esc(s.id)}" href="${href}">
        <span class="navx__ico" aria-hidden="true">${ico}</span>
        <span class="navx__tx"><span class="navx__nm">${esc(s.n)}</span>${
          dom ? `<span class="navx__dm">${esc(dom)}</span>` : ''}</span>
        ${fig ? `<span class="navx__fig">${esc(fig)}</span>` : ''}
      </a>`;
    }).join('');
  }

  // Each tab's first element is either a plain route id (a string, as the
  // admin console's own CFG.tabs still passes -- see admin.js) or an ordered
  // list of candidate hrefs (as DEFAULTS.tabs now passes for the public
  // shell). The two shapes need different handling: a string is always
  // rendered as "#/<id>", unconditionally, exactly as before; an array is
  // resolved through firstServable/ROUTER_HEADS the way route() resolves a
  // URL, and the tab is omitted entirely when nothing in it can render yet.
  function renderTabbar() {
    if ($('.tabbar')) return;
    const bar = document.createElement('nav');
    bar.className = 'tabbar';
    bar.setAttribute('aria-label', 'Sections');
    const lib = window.GT_LIB || {};
    const heads = lib.ROUTER_HEADS || FALLBACK_HEADS;
    const pick = lib.firstServable || fallbackFirstServable;
    const canRender = head => heads.has(head);
    bar.innerHTML = (CFG.tabs || DEFAULTS.tabs).map(([spec, ic, l]) => {
      let href, key;
      if (Array.isArray(spec)) {
        href = pick(spec, canRender);
        if (!href) return '';
        key = href.slice(2).split('/')[0];
      } else {
        key = spec;
        href = `#/${spec}`;
      }
      return `<a data-tab="${key}" href="${href}"><i aria-hidden="true">${ic}</i><span>${l}</span></a>`;
    }).join('');
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

    /* "not ok" is three different things, and calling all of them "would not
       answer anonymously" was false: five of the ten hold data and are only
       missing a fetch-log record. Counted separately, and only the ones that
       genuinely refused are described that way. */
    const rows = src.rows || [];
    const blocked  = rows.filter(r => r.blocked).length;
    const absent   = rows.filter(r => !r.blocked && r.provenance === 'absent').length;
    const unlogged = rows.filter(r => r.provenance === 'unlogged').length;
    const holding  = src.total - blocked - absent;

    const tiles = [
      { l: 'Systems with output', v: `${built} of ${SYSTEMS.length}`, s: 'each one measured, none estimated', k: built === SYSTEMS.length ? 'ok' : 'warn', href: '#/systems' },
      { l: 'Sources holding data', v: `${holding} of ${src.total}`,
        s: `${blocked} refused an anonymous request, ${absent} never fetched`,
        k: blocked ? 'warn' : 'ok', href: '#/sources' },
      { l: 'Rows held', v: a ? num(a.rowsHeld) : 'n/a', s: a ? `across ${num(a.tableCount)} tables` : 'platform output not loaded', k: '' },
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
    rows.filter(r => r.blocked).forEach(r => items.push({
      sev: 'bad', tag: 'blocked', t: `${r.name} refused an anonymous request`,
      s: [r.publisher, r.blocked].filter(Boolean).join(' · ').slice(0, 180), href: '#/sources',
    }));
    rows.filter(r => !r.blocked && r.provenance === 'absent').forEach(r => items.push({
      sev: 'warn', tag: 'never fetched', t: `${r.name} holds no data yet`,
      s: `${r.publisher || ''} · registered, nothing on disk`, href: '#/sources',
    }));
    rows.filter(r => r.provenance === 'unlogged').forEach(r => items.push({
      sev: 'none', tag: 'unlogged', t: `${r.name} has data but no fetch record`,
      s: 'a backfill wrote it directly, so the platform cannot say when it arrived',
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
        <div class="vhead__t" style="font-size:17px">One place, the whole record</div>
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
        <div class="vhead__s">Each row opens everything the record holds for that place.</div></div></div>
      <div class="fbar">
        <button class="fchip${placeFilter.min === 0 ? ' is-on' : ''}" data-min="0">All districts</button>
        <button class="fchip${placeFilter.min === 5 ? ' is-on' : ''}" data-min="5">5+ questions</button>
        <button class="fchip${placeFilter.min === 9 ? ' is-on' : ''}" data-min="9">9+ questions</button>
        ${placeFilter.q ? `<button class="fchip is-on" data-clearq>“${esc(placeFilter.q)}” &times;</button>` : ''}
        <span class="fbar__n">${num(rows.length)} of ${num(all.length)}</span>
      </div>
      ${rows.length ? `<div class="dt-wrap"><table class="dt dt--compact">
        <thead><tr><th data-sort="name">District</th><th class="num" data-sort="systems">Questions answered</th>
          <th style="width:1%">Coverage</th></tr></thead>
        <tbody>${rows.map(p => `<tr>
          <td><a class="dtlink" href="#/places/${esc(p.code)}"><b>${esc(p.name)}</b></a></td>
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
    // The district name is now a real link to its place page (#/places/<code>):
    // reachable by keyboard, gives a shareable URL, and opens the redesign's
    // own place page instead of the legacy panel openPlace() used to open.
    // No row-level click handler is attached any more.
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
      ${(() => { const cn = Platform.collectionNote(systemId), pj = Platform.placeJoinNote(systemId);
        return (cn || pj) ? `<div class="prov"><div class="prov__h">Collection and coverage</div>
          <div style="padding:.7rem .75rem;font-size:12.5px;color:var(--ink-2);line-height:1.55">${cn || ''}${cn && pj ? '<br><br>' : ''}${pj || ''}</div></div>` : ''; })()}
      <div class="prov"><div class="prov__h">Provenance · ${rows.length} source${rows.length === 1 ? '' : 's'}</div>
        ${rows.length ? rows.map(r => `<div class="prov__r">
          <span class="prov__k">Source</span><span><b>${esc(r.name)}</b><br>
            <span style="color:var(--ink-3)">${esc(r.publisher || '')}${r.licence ? ' · ' + esc(r.licence) : ''}</span>${r.authority === 'third party'
              ? '<br><span class="st st--warn">aggregator</span> <span style="color:var(--ink-3);font-size:11.5px">served by a third party, not the publisher</span>' : ''}</span>
          <span class="prov__k">Fetched</span><span class="mono">${r.fetched ? esc(String(r.fetched).slice(0, 19).replace('T', ' ')) : 'n/a'}</span>
          <span class="prov__k">State</span><span><span class="st st--${r.ok ? 'ok' : 'bad'}">${esc(r.status)}</span>${r.ok && !r.hashed ? ' <span class="st st--warn">no hash</span>' : ''}</span>
        </div>`).join('') : `<div class="prov__r"><span class="prov__k">n/a</span>
          <span style="color:var(--ink-3)">No source is registered against this system yet.</span></div>`}
      </div>`;
  }

  /* School capacity is returned per education authority, so a two-tier
     district's series is its county's. Drawn small, and labelled with whose. */
  function capacityBlock(c) {
    const pairs = (c.years || []).map((y, i) => [y, Number((c.pct || [])[i])])
      .filter(([, v]) => c.pct && !Number.isNaN(v));
    if (pairs.length < 2) return '';
    const pts = pairs.map(x => x[1]), lo = Math.min(...pts), hi = Math.max(...pts), W = 220, H = 36;
    const xy = pts.map((v, i) => `${(i * W / (pts.length - 1)).toFixed(1)},${(H - 3 - (hi > lo ? (v - lo) / (hi - lo) : .5) * (H - 6)).toFixed(1)}`);
    const a = pts[0], b = pts[pts.length - 1];
    return `<div class="prov" style="margin-top:1rem"><div class="prov__h">School places in use, ${esc(pairs[0][0])} to ${esc(pairs[pairs.length - 1][0])}</div>
      <div style="display:flex;gap:1rem;align-items:center;flex-wrap:wrap;padding:.55rem 0 .35rem">
        <svg viewBox="0 0 ${W} ${H}" width="${W}" height="${H}" role="img" aria-label="From ${a}% to ${b}%" style="max-width:100%;flex:none">
          <polyline points="${xy.join(' ')}" fill="none" stroke="var(--blue-500)" stroke-width="1.6" stroke-linejoin="round"/></svg>
        <div style="flex:1;min-width:0;font-size:12.5px;color:var(--ink-2)"><b>${a}%</b> → <b>${b}%</b> of places in use across ${esc(c.authority)}${c.county ? ' <span class="st st--none">county figure</span>' : ''}</div>
      </div>
      <div class="card__s" style="font-size:11.5px">${c.county
        ? `Capacity is returned per education authority, so this is ${esc(c.authority)} County Council’s series, shared by each of its districts.`
        : 'Capacity is returned per education authority; this is the council’s own series.'}</div></div>`;
  }

  function openPlace(code) {
    const rep = Platform.placeReport(code);
    if (!rep) { openPanel('Place', code, emptyFact('No figures for this district',
      'No system produced a value for this district in the current build.')); return; }
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
          <td>${esc(i.label)}<br><span style="color:var(--ink-3);font-size:11.5px">${esc(i.caveat || '')}</span>${i.scope ? `<br><span class="st st--none">county figure</span> <span style="color:var(--ink-3);font-size:11.5px">${esc(i.scope)}</span>` : ''}</td>
          <td class="num"><span class="st st--${i.tone === 'bad' ? 'bad' : i.tone === 'warn' ? 'warn' : 'ok'}">${esc(i.metric)}</span></td>
        </tr>`).join('')}</tbody></table></div>
      ${rep.capacity ? capacityBlock(rep.capacity) : ''}
      ${rep.silent ? emptyFact(`${rep.silent} systems have nothing to say here`,
        'That is a fact about the published data, not a gap in the platform, either no data reaches this district, or the system is planned at a different geography.',
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

    const limits = [...((d && d.limits) || []), ...Platform.liveLimits(id)];
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

  /* ------------------------------------------------- method and sources --- */
  /* The spine's tiers, what the joins connect, the platform's corrections to
     itself and its cross-checks were all published and shown nowhere. */
  const PREDICATE = {
    sits_in:      ['Postcode', 'District', 'every postcode the register places in a district: the place spine itself'],
    settled_by:   ['Developer contribution', 'Payment', 'each payment recorded against a contribution'],
    collected_by: ['Developer contribution', 'Collecting authority', 'the authority a contribution is owed to'],
    agreed_under: ['Developer contribution', 'Legal agreement', 'the agreement it falls under'],
    evidenced_by: ['Legal agreement', 'Planning application', 'the only published route from an agreement to a site'],
    located_in:   ['Legal agreement', 'District', 'agreements whose site could be placed in a district'],
  };
  const LEDGER_EDGES = new Set(['settled_by', 'collected_by', 'agreed_under', 'evidenced_by', 'located_in']);

  function buildMethod() {
    const spHost = $('#methodSpine');
    if (!spHost || spHost.dataset.built) return;
    const sp = Platform.spineTiers(), pl = sp.place || {}, en = sp.entity || {};
    const tiers = [];
    if (pl.uprn) tiers.push(['Property', 'OS Open UPRN', `${num(pl.uprn.rows)} properties`,
      'An exact point. The file carries no district, so one is taken from the postcode or, failing that, the nearest postcode centroid.']);
    if (pl.postcode) tiers.push(['Postcode', 'Code-Point Open', `${num(pl.postcode.rows)} postcodes`,
      `${num(pl.postcode.distinct_lads)} districts; ${pl.postcode.best_quality_share}% at the publisher’s best positional quality.${pl.postcode.no_district ? ` ${num(pl.postcode.no_district)} carry no district code in the register, so nothing placed through them reaches a district figure.` : ''}`]);
    if (pl.coordinate) tiers.push(['Coordinate', 'Nearest postcode centroid', `${pl.coordinate.resolved_pct}% resolved`,
      `Tested against ${esc(pl.coordinate.tested_against)}: ${num(pl.coordinate.resolved_within_500m)} of a ${num(pl.coordinate.sample)} sample within 500 m. Beyond that it refuses rather than guesses.`]);
    if (pl.street) tiers.push(['Street', 'OS Open USRN', `${num(pl.street.rows)} streets`,
      `Checks a street reference exists and says what kind of street it is (${num(pl.street.street_types)} types).${pl.street.carries_a_name === false ? ' It carries no street name.' : ''}`]);
    if (pl.lad) tiers.push(['District', 'ONS boundaries', `${num(pl.lad.rows)} districts`, 'The unit every district figure is published at.']);
    spHost.innerHTML = tiers.length ? `<div class="dt-wrap"><table class="dt">
        <thead><tr><th>Tier</th><th>Source</th><th class="num">Size</th><th>What it can and cannot tell you</th></tr></thead>
        <tbody>${tiers.map(t => `<tr><td><b>${t[0]}</b></td><td>${t[1]}</td><td class="num">${t[2]}</td><td>${t[3]}</td></tr>`).join('')}</tbody>
      </table></div>
      ${en.register_rows ? `<p class="mnote">Organisation spine: ${num(en.register_rows)} supplier records carrying ${num(en.distinct_names)} distinct names, resolved to ${num(en.distinct_numbers)} company numbers.</p>` : ''}`
      : '<div class="state"><div class="state__t">Spine figures are not in this build</div></div>';

    const g = Platform.graph(), gh = $('#methodGraph');
    if (gh) {
      const bp = (g && g.by_predicate) || {};
      const rows = Object.entries(bp).sort((a, b) => b[1] - a[1]);
      if (!rows.length) gh.innerHTML = '<div class="state"><div class="state__t">Relationship counts are not in this build</div></div>';
      else {
        const total = rows.reduce((a, r) => a + Number(r[1] || 0), 0), spine = Number(bp.sits_in || 0);
        const allLedger = rows.every(([p]) => p === 'sits_in' || LEDGER_EDGES.has(p));
        const unav = (g.unavailable || []), broken = Object.keys(g.broken || {});
        gh.innerHTML = `<div class="dt-wrap"><table class="dt">
            <thead><tr><th>From</th><th>To</th><th class="num">Relationships</th><th>What it means</th></tr></thead>
            <tbody>${rows.map(([p, c]) => { const d = PREDICATE[p] || [p, 'n/a', '']; return `<tr><td>${esc(d[0])}</td><td>${esc(d[1])}</td><td class="num">${num(c)}</td><td>${esc(d[2])}</td></tr>`; }).join('')}</tbody>
          </table></div>
          <p class="mnote">${num(total)} relationships across ${rows.length} declared types. ${unav.length ? `${unav.length} could not be built (${unav.map(esc).join(', ')}).` : 'Every declared type was built'}${broken.length ? `, and ${broken.length} is broken (${broken.map(esc).join(', ')}).` : ', and none is broken.'}
          ${spine ? `${num(spine)} of them are the place spine itself: postcodes placed in districts.${allLedger ? ' The rest trace a developer contribution to the agreement, application and payments behind it.' : ''}` : ''}</p>`;
      }
    }

    const c = Platform.corrections(), ch = $('#methodCorrections');
    if (ch) {
      const es = (c && c.entries) || [], su = (c && c.summary) || {};
      ch.innerHTML = !es.length ? '<div class="state"><div class="state__t">No corrections recorded</div></div>'
        : `<p class="mnote" style="margin:0 0 .8rem">${num(es.length)} corrections to this platform’s own claims. ${su.unguarded ? `${num(su.unguarded)} are not yet guarded by a test.` : 'Every one is guarded by a test that fails if the mistake comes back.'}</p>`
          + es.map(e => `<details class="corr"><summary><b>${esc(String(e.id || '').replace(/-/g, ' '))}</b>
              <span class="st st--${e.severity === 'material' ? 'bad' : 'warn'}">${esc(e.severity || 'noted')}</span>
              <span class="mono card__s">${esc(e.system || '')} · ${esc(e.corrected_on || '')}</span></summary>
              <div class="corr__b">
                <span class="corr__k">Believed</span><span>${esc(e.believed)}</span>
                <span class="corr__k">Actually</span><span>${esc(e.actually)}</span>
                <span class="corr__k">How it was caught</span><span>${esc(e.how_caught)}</span>
                <span class="corr__k">Guarded by</span><span>${e.guard ? `<code>${esc(e.guard)}</code>` : 'no test yet'}${e.guarded ? '' : ' <span class="st st--warn">unguarded</span>'}</span>
                ${(e.tags || []).length ? `<span class="corr__k">Kind of mistake</span><span>${e.tags.map(t => `<span class="st st--none">${esc(t)}</span>`).join(' ')}</span>` : ''}
              </div></details>`).join('');
    }
    const gp = Platform.gaps(), gph = $('#methodGaps');
    if (gph) {
      const chains = (gp && gp.detail) || [];
      if (!chains.length) gph.innerHTML = `<div class="state"><div class="state__t">${gp && gp.error ? 'The gap report failed to build' : 'The gap report is not in this build'}</div></div>`;
      else {
        // Short label for a link's state, and the longer phrase for the summary.
        const CAUSE = {nowhere: ['bad', 'published by nobody', 'are published by nobody', 'is published by nobody'],
                       publisher: ['warn', 'held, not released', 'are held by a publisher that does not release them', 'is held by a publisher that does not release it'],
                       platform: ['warn', 'this platform’s to fix', 'are this platform’s to fix', 'is this platform’s to fix'],
                       unmeasured: ['none', 'not measured', 'could not be measured', 'could not be measured']};
        const bc = gp.by_cause || {}, breaks = Object.values(bc).reduce((x, y) => x + y, 0);
        const and = a => a.length < 2 ? a.join('') : a.slice(0, -1).join(', ') + ' and ' + a[a.length - 1];
        const parts = Object.entries(bc).sort((x, y) => y[1] - x[1])
          .map(([k, v]) => breaks === 1 ? (CAUSE[k] || [])[3] || k : `${num(v)} ${(CAUSE[k] || [])[2] || k}`);
        const title = s => String(s).replace(/-/g, ' ').replace(/^./, ch => ch.toUpperCase());
        gph.innerHTML = `<p class="mnote" style="margin:0 0 .8rem">${num(gp.chains)} questions, ${num(gp.complete)} answerable end to end. `
          + (!breaks ? 'No link is missing.' : breaks === 1 ? `The one missing link ${parts[0]}.` : `Of the ${num(breaks)} missing links, ${and(parts)}.`)
          + (breaks && !bc.platform ? ' None is this platform’s to supply.' : '') + '</p>'
          + chains.map(c => {
              const st = c.complete ? ['ok', 'complete'] : ['bad', 'breaks at ' + c.breaks_at];
              return `<details class="corr"><summary><b>${esc(title(c.chain))}</b>
                <span class="st st--${st[0]}">${esc(st[1])}</span>
                <span class="mono card__s">${num(c.steps_available)} of ${num(c.steps)} links</span></summary>
                <p style="margin:.6rem 0 .5rem;font-size:13px;color:var(--ink-2)">${esc(c.asks)}</p>
                <div class="dt-wrap"><table class="dt dt--compact">
                  <thead><tr><th>Link</th><th>Where it lives</th><th class="num">Populated</th><th>State</th></tr></thead>
                  <tbody>${(c.detail || []).map(s => {
                    const cz = s.available ? ['ok', 'present'] : (CAUSE[s.absent_because] || ['none', s.absent_because || 'absent']);
                    return `<tr><td><b>${esc(s.step)}</b><br><span style="color:var(--ink-3);font-size:11.5px">${esc(s.question || '')}</span>${s.reason ? `<br><span style="color:var(--ink-3);font-size:11.5px">${esc(s.reason)}</span>` : ''}</td>
                      <td class="mono" style="font-size:11.5px;word-break:break-all">${s.table ? esc(s.table + '.' + s.column) : 'n/a'}</td>
                      <td class="num">${s.populated_pct != null ? esc(s.populated_pct) + '%' : 'n/a'}</td>
                      <td><span class="st st--${cz[0]}">${esc(cz[1])}</span></td></tr>`;
                  }).join('')}</tbody></table></div></details>`;
            }).join('');
      }
    }
    spHost.dataset.built = '1';
  }

  function buildSources() {
    const host = $('#sourcesChecks');
    if (!host || host.dataset.built) return;
    const c = Platform.contradictions(), rs = (c && c.results) || [];
    if (!rs.length) { host.innerHTML = '<div class="state"><div class="state__t">No cross-checks in this build</div></div>'; host.dataset.built = '1'; return; }
    const ran = rs.filter(r => r.run), dis = ran.filter(r => r.disagreed > 0), un = rs.filter(r => !r.run);
    // A check over one aggregate row compares two totals; "0% agree" would
    // misstate it, so it shows the two totals instead.
    const agree = r => {
      if (!r.run) return 'n/a';
      const ex = (r.examples || [])[0];
      if (r.compared === 1 && ex && ex.left_value != null && ex.right_value != null) return `${num(ex.left_value)} vs ${num(ex.right_value)}`;
      return r.agreement_pct != null ? `${r.agreement_pct}%` : 'n/a';
    };
    host.innerHTML = `<p class="mnote" style="margin:0 0 .8rem">${num(rs.length)} checks compare a quantity the platform holds twice, by two routes. ${num(ran.length)} ran and ${num(dis.length)} found a disagreement${un.length ? `; ${num(un.length)} could not run because an input is missing` : ''}. A disagreement is reported, never resolved: the platform has no standing to say which record is right.</p>
      <div class="dt-wrap"><table class="dt">
        <thead><tr><th>Quantity</th><th class="num">Compared</th><th class="num">Disagree</th><th class="num">Agreement</th></tr></thead>
        <tbody>${rs.map(r => `<tr><td><b>${esc(r.quantity || r.check)}</b><br><span style="color:var(--ink-3);font-size:11.5px">${esc(r.note || '')}</span></td>
          <td class="num">${r.run ? num(r.compared) : 'n/a'}</td>
          <td class="num">${r.run ? `<span class="st st--${r.disagreed ? 'warn' : 'ok'}">${num(r.disagreed)}</span>` : '<span class="st st--none">not run</span>'}</td>
          <td class="num">${agree(r)}</td></tr>`).join('')}</tbody>
      </table></div>`;
    host.dataset.built = '1';
  }

  /* ---------------------------------------------------------- unusual/about --- */
  // The source behind one row's question. evidence.headlines carries the
  // most specific, per-figure provenance the platform records (the actual
  // dataset a system's headline was derived from); Platform.metricProvenance
  // is the fallback, since every question here is also a map metric id and
  // so always has a registered source list, even where evidence is thin.
  function sourceForQuestion(q) {
    const ev = (Platform.evidence ? Platform.evidence(q) : [])[0];
    if (ev && ev.publisher && ev.dataset) {
      return { text: `${ev.publisher}, ${ev.dataset}`, url: ev.source_url || null };
    }
    const prov = Platform.metricProvenance ? Platform.metricProvenance(q) : null;
    const list = (prov && prov.sources) || [];
    const src = list.find(s => s.ok) || list[0];
    if (src) return { text: `${src.publisher}, ${src.name}`, url: null };
    return null;
  }

  function buildUnusual() {
    const host = $('#unusualBody'); if (!host) return;
    const lib = window.GT_LIB || {};
    const rows = lib.unusualRows ? lib.unusualRows(Platform.payload()) : [];
    const label = id => (SYSTEMS.find(s => s.id === id) || {}).n || id;
    const sourceCell = q => {
      const src = sourceForQuestion(q);
      if (!src) return '<span class="card__s">no source resolved for this figure</span>';
      const text = esc(src.text);
      return src.url ? `<a href="${esc(src.url)}" target="_blank" rel="noopener">${text}</a>` : text;
    };

    const table = `<table class="tbl"><thead><tr>
        <th>Place</th><th>Question</th><th class="num">Its figure</th>
        <th class="num">Measured against</th><th class="num">Gap</th><th>Source</th></tr></thead><tbody>
      ${rows.map(r => `<tr>
        <td><a href="#/places/${esc(r.code)}">${esc(r.name)}</a></td>
        <td>${esc(label(r.question))}</td>
        <td class="num mono">${r.figure.toFixed(1)}%</td>
        <td class="num mono">${r.against.toFixed(1)}%<span class="answer__s"> ${esc(r.againstLabel)}</span></td>
        <td class="num mono">${r.gap.toFixed(1)}</td>
        <td style="font-size:11.5px;white-space:normal;min-width:220px">${sourceCell(r.question)}</td></tr>`).join('')}
      </tbody></table>`;

    // The spec places the four recorded contradictions and the seventeen
    // corrections beneath this table, so a reporter checking one figure can
    // also see where the platform disagrees with itself and what it has
    // already had to fix in public.
    const contra = Platform.contradictions() || {};
    const disagreeing = (contra.results || []).filter(r => r.run && r.disagreed > 0);
    const contraHtml = `
      <h3 class="qlist__h" style="margin-top:2rem">Where the platform checks itself</h3>
      <p class="card__s">${num(disagreeing.length)} of ${num(contra.checks || 0)} cross-checks found a disagreement.
        A disagreement is reported, never resolved: the platform has no standing to say which record is right.</p>
      ${disagreeing.length ? `<div class="dt-wrap"><table class="dt">
        <thead><tr><th>Quantity</th><th class="num">Compared</th><th class="num">Disagree</th></tr></thead>
        <tbody>${disagreeing.map(r => `<tr><td><b>${esc(r.quantity || r.check)}</b><br>
          <span style="color:var(--ink-3);font-size:11.5px">${esc(r.note || '')}</span></td>
          <td class="num">${num(r.compared)}</td>
          <td class="num"><span class="st st--warn">${num(r.disagreed)}</span></td></tr>`).join('')}</tbody>
      </table></div>` : ''}`;

    const corrections = Platform.corrections() || {};
    const entries = corrections.entries || [];
    const correctionsHtml = `
      <h3 class="qlist__h" style="margin-top:2rem">Corrections</h3>
      <p class="card__s">${num(entries.length)} corrections published, each with what was believed,
        what was true, and the test that now guards it.</p>
      <div class="answers">
        ${entries.length ? entries.map(c => `
          <article class="answer">
            <h4 class="answer__q">${esc(String(c.id || 'Correction').replace(/-/g, ' '))}</h4>
            <p class="answer__s">${esc(c.believed || '')}</p>
            <p class="answer__s">${esc(c.actually || '')}</p>
          </article>`).join('') : '<div class="state"><div class="state__t">No corrections recorded</div></div>'}
      </div>`;

    host.innerHTML = table + contraHtml + correctionsHtml;
  }

  /* The inventory used to greet every visitor. It belongs here, next to the
     method and the corrections, where it is evidence rather than a welcome. */
  function buildAbout() {
    const host = $('#aboutBody'); if (!host) return;
    const payload = Platform.payload ? Platform.payload() : null;
    if (!payload) return;
    const sources = Platform.sourceSummary() || {};
    const corrections = Platform.corrections() || {};
    const entries = corrections.entries || [];
    const built = (Platform.builtSystems() || []).length;

    // Corrections first, then the inventory tiles: the merge into #/about
    // orders corrections ahead of the platform inventory, so this renders in
    // that order rather than the inventory-first order the standalone about
    // page used before sources and method were folded in.
    host.innerHTML = `
      <h3 class="qlist__h">Corrections</h3>
      <div class="answers">
        ${entries.length ? entries.map(c => `
          <article class="answer">
            <h4 class="answer__q">${esc(String(c.id || 'Correction').replace(/-/g, ' '))}</h4>
            <p class="answer__s">${esc(c.believed || '')}</p>
            <p class="answer__s">${esc(c.actually || '')}</p>
          </article>`).join('') : '<div class="state"><div class="state__t">No corrections recorded</div></div>'}
      </div>
      <h3 class="qlist__h" style="margin-top:2rem">The platform, in numbers</h3>
      <p class="place__sum">Two joins are added to data anyone can download: where a reference becomes
        a property, a postcode and then one of ${num(Object.keys((payload.places||{}).names||{}).length)}
        districts, and who, where name variants become one company number.</p>
      <div class="tiles">
        ${tile(built + ' of ' + SYSTEMS.length, 'questions with a measured answer')}
        ${tile(num((sources.rows||[]).filter(r => !r.blocked).length) + ' of ' + num((sources.rows||[]).length), 'sources returning data')}
        ${tile(num(entries.length), 'corrections published, each with the test that guards it')}
      </div>`;
  }

  // A small helper so the three figures above read as one object.
  function tile(value, label) {
    return `<div class="tile"><div class="tile__v mono">${esc(value)}</div>
            <div class="tile__l">${esc(label)}</div></div>`;
  }

  /* -------------------------------------------------------------- router --- */
  // 'unusual' and 'about' have their own <div data-view> in app/index.html
  // (compare has none: it reuses 'places'), so both must be listed here or
  // show('unusual')/show('about') would hide every view, including their own,
  // and the destination would render as a blank page.
  const VIEWS_PUBLIC = ['home', 'overview', 'places', 'systems', 'sources', 'method', 'detail', 'unusual', 'about'];

  function show(view) {
    views().forEach(v => {
      const el = $(`[data-view="${v}"]`);
      if (el) el.hidden = v !== view;
    });
    const host = $('#syshost');
    if (host) host.classList.toggle('on', view === 'detail');
    document.body.style.overflow = '';
  }

  function setChrome(key) {
    const T = titles();
    const [crumb, title] = T[key] || T[''] || ['', ''];
    const c = $('.top__crumb'), t = $('.top__title');
    if (c) c.textContent = (CFG.crumb || DEFAULTS.crumb) + ' · ' + crumb;
    // A detail route names the thing itself; the section name is the fallback.
    if (t) t.textContent = docName || title;
    $$('[data-nav]').forEach(a => a.classList.toggle('is-on', a.dataset.nav === key));
    const activeSys = (location.hash.match(/^#\/systems\/([a-z0-9_-]+)/i) || [])[1] || '';
    $$('[data-sysnav]').forEach(a => a.classList.toggle('is-on', a.dataset.sysnav === activeSys));
    $$('[data-tab]').forEach(a => a.classList.toggle('is-on', a.dataset.tab === key));
    const s = $('.side');
    if (s) s.classList.remove('on');
  }

  /* Hashes the old build produced, kept working so nothing anyone saved breaks. */
  const LEGACY_PUBLIC = {
    '#top': '#/method', '#hero': '#/method', '#spines': '#/method', '#chains': '#/method',
    '#place': '#/places', '#systems': '#/systems', '#compare': '#/systems',
    '#feeds': '#/sources', '#honesty': '#/sources', '#kpis': '#/',
    '#org': '#/orgs', '#search': '#/search',
  };

  /* One title and description per route. The shell left both at the homepage
     values, so every tab, bookmark and shared link read the same, and a screen
     reader announced the same sentence on every navigation. The canonical link
     deliberately stays on the root: these are fragments, not separate URLs, and
     a crawler is served the static pages instead. */
  const DOCS = {
    '':        ['Find your area', 'Type a council or district name and see what the connected record holds for it: school places, planning speed, flood defences, care ownership and connectivity, each from a published government file.'],
    places:    ['Places', 'Every district, with school places, planning speed, flood defences, care ownership and connectivity read side by side.'],
    systems:   ['What it answers', 'The thirteen questions the connected record answers, each computed from a published government file.'],
    orgs:      ['Organisations', 'Companies and public bodies resolved to one identifier across procurement, care and ownership records.'],
    sources:   ['Sources', 'Every source the record reads, when it was last fetched, and what failed.'],
    method:    ['Method', 'The two joins, what each figure assumes, and every correction published so far.'],
    search:    ['Search', 'Search organisations, places and the thirteen questions.'],
    compare:   ['Compare every district', 'Every district the connected record covers, with the figures each question answers for it, sortable and exportable.'],
    unusual:   ['What looks unusual', 'Where a place sits furthest from the figure it is published against, with both numbers and the source for each.'],
    about:     ['How this is built', 'The two joins, every source the record reads, the corrections published so far, and what this cannot do.'],
    // Same content as 'systems': #/questions/<id> renders the identical view
    // (see the questions branch in route()), so it needs the same fallback
    // copy here for the rare direct visit to the bare #/questions with no id.
    questions: ['What it answers', 'The thirteen questions the connected record answers, each computed from a published government file.'],
  };

  let docName = '';

  function setDoc(head, seg) {
    let [name, desc] = DOCS[head] || DOCS[''];
    const specific = !!seg[1];
    try {
      if (head === 'places' && seg[1]) {
        const pl = (Platform.placeList() || []).find(x => x.code === seg[1]);
        if (pl) { name = pl.name;
          desc = `What the connected record says about ${pl.name}: school places, planning speed, flood `
               + `defences, care ownership and connectivity, each computed from a published file.`; }
      } else if ((head === 'systems' || head === 'questions') && seg[1]) {
        // #/questions/<id> renders the identical page as #/systems/<id> (see
        // the questions branch in route()), so it earns the same specific
        // title and description rather than falling back to the home page's.
        const sy = SYSTEMS.find(x => x.id === seg[1]);
        if (sy) { name = sy.n; desc = `${sy.n}: ${sy.s || 'one of the thirteen questions the connected record answers'}.`; }
      } else if (head === 'orgs' && seg[1]) {
        name = decodeURIComponent(seg[1]);
        desc = `${name} across procurement, care and ownership records, resolved to one identifier.`;
      }
    } catch (e) { /* the payload may not be in yet; the route title still stands */ }
    docName = specific ? name : '';
    document.title = `${name} | UK GroundTruth`;
    const meta = (sel, val) => { const el = document.querySelector(sel); if (el) el.setAttribute('content', val); };
    meta('meta[name="description"]', desc);
    meta('meta[property="og:title"]', document.title);
    meta('meta[property="og:description"]', desc);
    meta('meta[name="twitter:title"]', document.title);
    meta('meta[name="twitter:description"]', desc);
  }

  // ROUTER_HEADS in app/assets/lib/routes.js is the authoritative list of
  // heads route() below actually dispatches, read off its own if-branches
  // and enforced against them in tests/js/routes.test.js. This local set is
  // only a fallback for the (should not happen) case where the module entry
  // has not loaded and window.GT_LIB.ROUTER_HEADS is unavailable; keep it
  // matching route()'s branches so the degraded behaviour still makes sense.
  const FALLBACK_HEADS = new Set(['', 'places', 'systems', 'orgs', 'sources', 'method', 'search',
    'compare', 'unusual', 'about', 'questions']);

  // Mirrors firstServable in app/assets/lib/routes.js; only a fallback for
  // the same (should not happen) case as FALLBACK_HEADS above, used by
  // renderTabbar when window.GT_LIB.firstServable is unavailable.
  function fallbackFirstServable(candidates, canRender) {
    const list = Array.isArray(candidates) ? candidates : [candidates];
    for (const candidate of list) {
      const head = String(candidate).slice(2).split('/')[0];
      if (canRender(head)) return candidate;
    }
    return null;
  }

  // route() runs on every hash change, so this flag keeps the warning below
  // to a single occurrence instead of spamming the console on each navigation.
  let warnedMissingLib = false;

  /* The front page does one thing. Everything else on it is a signpost. */
  function buildHome() {
    const lib = window.GT_LIB || {};
    // Shared with the door wiring below and the question list further down:
    // same firstServable/ROUTER_HEADS pattern renderTabbar uses, with the
    // same fallback for when the module entry has not loaded.
    const heads = lib.ROUTER_HEADS || FALLBACK_HEADS;
    const pick = lib.firstServable || fallbackFirstServable;
    const canRender = head => heads.has(head);
    const names = (Platform.payload && Platform.payload().places && Platform.payload().places.names) || {};
    const input = $('#findPlace'), hits = $('#findHits'), note = $('#findNote');
    if (!input || !hits) return;

    const go = code => { location.hash = '#/places/' + code; };

    const draw = () => {
      const q = input.value;
      const found = lib.matchPlaces ? lib.matchPlaces(q, names) : [];
      hits.innerHTML = found.map(h =>
        `<button class="find__hit" role="option" data-code="${esc(h.code)}">${esc(h.name)}</button>`).join('');
      hits.hidden = !found.length;
      const postcode = lib.looksLikePostcode && lib.looksLikePostcode(q) && !found.length;
      if (note) {
        note.textContent = postcode
          ? 'Postcodes are not matched yet. Type the council or district name instead.'
          : (q.trim() && !found.length ? 'No district of that name. Try the council that covers it.' : '');
        note.hidden = !note.textContent;
      }
    };

    input.oninput = draw;
    input.onkeydown = e => {
      if (e.key !== 'Enter') return;
      const first = hits.querySelector('.find__hit');
      if (first) go(first.dataset.code);
    };
    hits.onclick = e => {
      const b = e.target.closest('.find__hit');
      if (b) go(b.dataset.code);
    };

    // Three real examples, so the field is obviously usable.
    const eg = $('#findEg');
    if (eg) {
      const examples = [['E07000032', 'Amber Valley'], ['E09000007', 'Camden'], ['E08000003', 'Manchester']]
        .filter(([code]) => names[code]);
      eg.innerHTML = examples.map(([code, name]) =>
        `<a class="chip" href="#/places/${code}">${esc(name)}</a>`).join('');
    }

    const list = $('#qlistBody');
    if (list) {
      // The question view has no handler yet (a later task adds it), so this
      // degrades to #/systems/<id>, which renders today, and upgrades itself
      // once that handler lands -- same firstServable pattern as renderTabbar.
      list.innerHTML = SYSTEMS.map(s => {
        const qid = esc(s.id);
        const href = pick(['#/questions/' + qid, '#/systems/' + qid], canRender) || ('#/systems/' + qid);
        return `<a class="qrow" href="${href}">
           <span class="qrow__n">${esc(s.n)}</span>
           <span class="qrow__s">${esc(s.s || '')}</span>
         </a>`;
      }).join('');
    }

    // The three doors in app/index.html carry a static href as a sensible
    // default (#/compare, #/unusual, #/about) -- none of those heads has a
    // route() handler yet, so left alone they would dead-end on "No such
    // view" on the very first screen. Overwrite each one here with
    // firstServable, preferring the eventual destination and falling back
    // to a head route() can already serve today; it upgrades itself once a
    // later task adds the missing handler, the same pattern used for the
    // question list above. tests/js/routes.test.js checks app/index.html's
    // static hrefs by confirming each door id below is looked up and its
    // href resolved through pick (aliased from firstServable) right here.
    const doorCompareLink = $('#doorCompareLink');
    if (doorCompareLink) doorCompareLink.href = pick(['#/compare', '#/places'], canRender) || '#/places';
    const doorUnusualLink = $('#doorUnusualLink');
    if (doorUnusualLink) doorUnusualLink.href = pick(['#/unusual', '#/places'], canRender) || '#/places';
    const doorAboutLink = $('#doorAboutLink');
    if (doorAboutLink) doorAboutLink.href = pick(['#/about', '#/method'], canRender) || '#/method';

    const compare = $('#doorCompare');
    if (compare) compare.textContent = num(Object.keys(names).length);

    // Both of these were hardcoded placeholders (50, 45) until the routes
    // behind them existed. Now each is computed here, the same way
    // #doorCompare above is, and always overwritten -- including to blank
    // when the real figure is not available -- so a stale or invented number
    // can never sit on the front page.
    const lib2 = window.GT_LIB || {};
    const unusual = $('#doorUnusual');
    if (unusual) unusual.textContent = lib2.unusualTotal ? num(lib2.unusualTotal(Platform.payload())) : '';
    const about = $('#doorAbout');
    const srcs = (Platform.sourceSummary() || {}).rows || [];
    if (about) about.textContent = srcs.length ? num(srcs.length) : '';

    // The front page's only provenance claim, computed from the same payload
    // rather than left as hand-typed text. Each clause is dropped on its own
    // when its number cannot be derived, so a stale figure never survives.
    const cred = $('#findCred');
    if (cred) {
      const publishers = new Set(srcs.map(r => r.publisher).filter(Boolean));
      const correctionsTotal = ((Platform.corrections() || {}).summary || {}).total
        ?? (((Platform.corrections() || {}).entries || []).length || null);
      const parts = [];
      if (srcs.length && publishers.size) parts.push(`${num(srcs.length)} sources from ${num(publishers.size)} publishers.`);
      if (correctionsTotal) parts.push(`${num(correctionsTotal)} corrections published, each with `
        + `what was believed, what was true, and the test that now guards it.`);
      cred.textContent = parts.join(' ');
    }
  }

  /* The place's own figures as a file, written from the rows the page renders
     rather than from a second pass over the payload, so the two can never
     disagree. Nothing is rounded here that the page did not already round. */
  function placeCsv(code, name, rows) {
    const cell = v => `"${String(v == null ? '' : v).replace(/"/g, '""')}"`;
    const head = ['place_code', 'place_name', 'question', 'question_name', 'figure', 'unit',
                  'measured_against', 'against_label', 'caveat', 'method'];
    const lines = [head.join(',')];
    for (const a of rows) {
      lines.push([code, name, a.id, a.name, a.figure, a.unit, a.against, a.againstLabel,
                  a.caveat, a.method].map(cell).join(','));
    }
    return lines.join('\r\n') + '\r\n';
  }

  function downloadPlaceCsv(code, name, rows) {
    const blob = new Blob([placeCsv(code, name, rows)], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${code}.csv`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    // Revoked on the next turn of the loop: Safari needs the object URL to
    // outlive the click that consumes it.
    setTimeout(() => URL.revokeObjectURL(url), 0);
  }

  /* One place, as a document: what it is, what stands out, then every question
     that has an answer for it, and plainly those that do not. */
  function buildPlacePage(code) {
    const host = $('#placePage'), index = $('#placeIndex'), legacy = $('#place');
    if (!host) return;
    const payload = Platform.payload ? Platform.payload() : null;
    const names = (payload && payload.places && payload.places.names) || {};
    const byLad = (payload && payload.places && payload.places.byLad) || {};
    const name = names[code], place = byLad[code];
    if (!name || !place) {
      // An unknown code degrades to the index rather than leaving a "no
      // such place" page up. Clear the stale markup along with hiding it,
      // so a later render that forgets to overwrite host.innerHTML cannot
      // reveal the previous place. The legacy explorer (#place) follows
      // the index here too: no single place is open, so it renders as it
      // does for the index.
      host.hidden = true;
      host.innerHTML = '';
      if (index) index.hidden = false;
      if (legacy) legacy.hidden = false;
      return;
    }

    const lib = window.GT_LIB || {};
    const summary = lib.placeSummary ? lib.placeSummary(code, payload) : [];
    // Each block carries this place's own figures, from the tested module in
    // app/assets/lib/answers.js. Until that module entry loads, the fallback
    // below is the page as it was: the question and a link, with no figure
    // pretending to be local.
    const answers = lib.placeAnswers ? lib.placeAnswers(code, payload) : null;
    // What kind of authority this is, since a county figure shown on a district
    // has to say so. Null where the payload cannot tell, and nothing is guessed.
    const authority = lib.placeAuthority ? lib.placeAuthority(code, payload) : null;
    const answered = SYSTEMS.filter(s => place[s.id]);
    // An answer is a question with a figure, not merely a block: a block whose
    // figure is null in the payload belongs with the absences, so the count and
    // the blocks below it can never disagree.
    const shown = answers ? new Set(answers.map(a => a.id)) : new Set(answered.map(s => s.id));
    // A missing question is not always missing for the same reason, and the
    // reason given has to be one the payload actually states for THIS place,
    // not one that merely happens to be true elsewhere. app/assets/lib/answers.js
    // classifies every absence from the payload itself: national when no place
    // anywhere ever carries the question at all, the county's when this
    // place's own authority record says so and the question has been seen as
    // a county figure somewhere, and otherwise simply unanswered here, with no
    // cause invented. Until that module entry loads, the fallback below still
    // names what is missing, it just never claims a reason it cannot support.
    const absences = lib.placeAbsences ? lib.placeAbsences(code, payload, SYSTEMS.map(s => s.id)) : null;
    const byId = id => SYSTEMS.find(s => s.id === id) || { n: id };
    const national = absences ? absences.national.map(byId) : [];
    const upperTier = absences ? absences.upperTier.map(byId) : [];
    const noFigure = absences ? absences.noFigure.map(byId)
      : SYSTEMS.filter(s => !shown.has(s.id));

    // The question view has no handler yet (a later task adds it), so this
    // degrades to #/systems/<id>, which renders today, and upgrades itself
    // once that handler lands -- same firstServable pattern as renderTabbar.
    const heads = lib.ROUTER_HEADS || FALLBACK_HEADS;
    const pick = lib.firstServable || fallbackFirstServable;
    const canRender = head => heads.has(head);
    const method = id => pick(['#/questions/' + id, '#/systems/' + id], canRender) || ('#/systems/' + id);
    // A figure is a number or a string the module already formatted.
    const fig = v => typeof v === 'number' ? num(v) : String(v);

    const blocks = answers ? answers.map(a => `
          <article class="answer">
            <p class="answer__n">${esc(a.name)}</p>
            <h3 class="answer__q">${esc(a.question)}</h3>
            <p class="answer__f"><span class="answer__fv">${esc(fig(a.figure))}</span>${
              a.unit ? `<span class="answer__fu">${esc(a.unit)}</span>` : ''}</p>
            ${a.against != null ? `<p class="answer__v">Measured against ${esc(num(a.against))}${
              esc(a.unit || '')}, ${esc(a.againstLabel || '')}.</p>` : ''}
            ${a.caveat ? `<p class="answer__c">${esc(a.caveat)}</p>` : ''}
            <a class="answer__go" href="${method(a.id)}">How this is computed</a>
          </article>`).join('')
      : answered.map(s => `
          <article class="answer">
            <h3 class="answer__q">${esc(s.n)}</h3>
            <p class="answer__s">${esc(s.s || '')}</p>
            <a class="answer__go" href="${method(s.id)}">How this is computed</a>
          </article>`).join('');

    host.innerHTML = `
      <h2 class="place__h">${esc(name)}</h2>
      ${authority ? `<p class="place__t">${esc(authority)}</p>` : ''}
      <p class="place__k">${shown.size} of ${SYSTEMS.length} questions answered here</p>
      ${summary.map(line => `<p class="place__sum">${esc(line)}</p>`).join('')}
      <div class="answers">${blocks}</div>
      ${national.length ? `<p class="place__none">${
        national.map(s => esc(s.n)).join(', ')} ${national.length === 1 ? 'is' : 'are'} measured
        only at the national level, not broken down by place at all, so no district ever carries a
        figure for ${national.length === 1 ? 'it' : 'them'}.</p>` : ''}
      ${upperTier.length ? `<p class="place__none">No answer here for ${
        upperTier.map(s => esc(s.n)).join(', ')}. ${upperTier.length === 1 ? 'It is' : 'They are'}
        published for ${esc(absences.countyName)} County Council, not for this district.</p>` : ''}
      ${noFigure.length ? `<p class="place__none">No answer here for ${
        noFigure.map(s => esc(s.n)).join(', ')}. The published record carries no figure for ${
        noFigure.length === 1 ? 'it' : 'them'} at this place.</p>` : ''}
      ${answers && answers.length ? `<p class="place__take"><button type="button" class="chip place__csv"
        id="placeCsv">Download these ${answers.length} figures as CSV</button></p>` : ''}`;

    // The file is written from the same rows the blocks above are, so the page
    // and the download cannot disagree about a single figure.
    const csvBtn = $('#placeCsv');
    if (csvBtn) csvBtn.addEventListener('click', () => downloadPlaceCsv(code, name, answers));
    host.hidden = false;
    if (index) index.hidden = true;
    // A specific place is open: the legacy explorer below (#place) would
    // otherwise still show whichever place its own map last selected --
    // Amber Valley by default -- presented as if it were this place. Hide
    // it while a single place's document is on screen.
    if (legacy) legacy.hidden = true;
  }

  function route() {
    const raw = location.hash || '#/';
    // One table of every hash the app has published, tested in tests/js/routes.test.js.
    let canonical = null;
    if (window.GT_LIB && window.GT_LIB.canonicalHash) {
      const heads = window.GT_LIB.ROUTER_HEADS || FALLBACK_HEADS;
      canonical = window.GT_LIB.canonicalHash(raw, (head) => heads.has(head));
    } else if (!warnedMissingLib) {
      warnedMissingLib = true;
      console.warn('[shell] route aliasing is unavailable because the module entry has not loaded');
    }
    if (canonical) { location.replace(canonical); return; }

    const path = raw.replace(/^#\/?/, '').split('?')[0];
    const seg = path.split('/').filter(Boolean);
    const head = seg[0] || '';
    closePanel();
    setDoc(head, seg);

    // A console supplies its own routes; the public ones are the fallback.
    if (CFG.onRoute) {
      let handled = false;
      safely(() => { handled = CFG.onRoute(head, seg, { show, setChrome, scrollTop, safely }) === true; });
      if (handled) return;
    }

    if (head === '') {
      show('home'); setChrome(''); safely(buildHome, '#viewHome'); scrollTop(); return;
    }

    // Compare is the district index that already exists, given its own door.
    // buildPlaces() creates #placeIndex inside #viewPlaces and returns early if
    // it is already there, so the compare route shows that view rather than
    // building a second table.
    if (head === 'compare') {
      show('places'); setChrome('compare');
      const host = $('#placePage'), index = $('#placeIndex');
      if (host) host.hidden = true;
      safely(buildPlaces, '#viewPlaces');
      if ($('#placeIndex')) $('#placeIndex').hidden = false;
      scrollTop(); return;
    }
    if (head === 'unusual') {
      show('unusual'); setChrome('unusual'); safely(buildUnusual, '#unusualBody'); scrollTop(); return;
    }
    if (head === 'about') {
      // #/sources and #/method both redirect here (app/assets/lib/routes.js),
      // so this is the only place their content can still be reached. The
      // merge calls the same renderers those routes used, each into the
      // section of the about view now holding their old containers, rather
      // than rebuilding what they already produce.
      show('about'); setChrome('about');
      safely(buildMethod, '#methodSpine');
      safely(buildSources, '#sourcesChecks');
      safely(buildAbout, '#aboutBody');
      scrollTop(); return;
    }

    if (head === 'places') {
      show('places'); setChrome('places'); safely(buildPlaces, '#placeIndex'); scrollTop();
      const host = $('#placePage'), index = $('#placeIndex'), legacy = $('#place');
      if (seg[1]) { safely(() => buildPlacePage(seg[1])); }
      else {
        // No code: this is the index, so the legacy explorer (#place)
        // renders as it always has, same as buildPlacePage's own guard
        // clause for an unknown code.
        if (host) host.hidden = true;
        if (index) index.hidden = false;
        if (legacy) legacy.hidden = false;
      }
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

    // Every question link now points at #/questions/<id> (150 outreach emails
    // still point at #/systems/<id>, which keeps working via the branch
    // above). This mirrors that branch exactly, including its tab handling,
    // rather than redirecting, so both URLs render the same page today.
    if (head === 'questions') {
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

    if (head === 'sources') { show('sources'); setChrome('sources'); safely(buildSources, '#sourcesChecks'); scrollTop(); return; }
    if (head === 'method')  { show('method');  setChrome('method');  safely(buildMethod, '#methodSpine'); scrollTop(); return; }
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
                   placeholder="Search places, organisations, questions…" aria-label="Search">
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
      if (CFG.palette) return CFG.palette(q.trim().toLowerCase()) || [];
      const t = q.trim().toLowerCase();
      const out = [];
      const sys = SYSTEMS.filter(s => !t || s.n.toLowerCase().includes(t) || s.s.toLowerCase().includes(t) || s.dom.toLowerCase().includes(t));
      const places = Platform.placeList().filter(p => t && p.name.toLowerCase().includes(t));
      const orgs = (Platform.organisations() || []).filter(o =>
        t && String(o.name || '').toLowerCase().includes(t)).slice(0, 8);

      if (places.length) out.push(['Places', places.slice(0, 8).map(p => ({
        icon: '▣', t: p.name, s: `${p.systems} of thirteen questions answered here`, w: `${p.systems}/13`,
        go: () => { location.hash = '#/places'; setTimeout(() => openPlace(p.code), 30); } }))]);
      if (orgs.length) out.push(['Organisations', orgs.map(o => ({
        icon: '⬢', t: o.name, s: o.number ? 'Company ' + o.number : 'organisation',
        w: (o.systems || []).length ? (o.systems.length + ' sys') : '',
        go: () => { location.hash = '#/orgs/' + encodeURIComponent(o.number || o.name); } }))]);
      if (sys.length) out.push(['Systems', sys.slice(0, 8).map(s => ({
        icon: '▦', t: s.n, s: s.s, w: s.dom,
        go: () => { location.hash = '#/systems/' + s.id; } }))]);
      if (!t) out.push(['Go to', nav().flatMap(g => g.items).map(i => ({
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
  function boot(cfg) {
    CFG = Object.assign({}, DEFAULTS, cfg || {});
    renderNav();
    renderTabbar();

    // The skip link is the first tab stop on every page. Its href="#top" used
    // to double as a URL fragment, and #top is one of the old anchor hashes
    // the route table now sends to #/about, so activating it navigated the
    // whole app away from the page a keyboard user was on. Intercepting the
    // click and moving focus by hand, instead of letting the browser change
    // location.hash, skips to the current page's main content (the <main
    // id="top"> landmark every view renders inside) without touching the
    // route at all.
    const skip = $('.skip');
    if (skip) skip.addEventListener('click', e => {
      e.preventDefault();
      const main = document.getElementById('top');
      if (main) { main.focus(); main.scrollIntoView({ block: 'start' }); }
    });

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

  return { boot, route, show, setChrome, openPlace, openSystemDetail, openPanel, closePanel, capacityBlock,
           provenanceBlock, skeleton, emptyFact, emptyFilter, Palette, SysTabs, esc, num };
})();
