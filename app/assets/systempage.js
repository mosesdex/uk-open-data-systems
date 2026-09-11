/* Full-screen system page. One template, so every system reads the same way:
   overview -> numbers -> data -> trends -> insights -> pipeline -> sources ->
   methodology -> records -> related. Each system supplies only its own plain
   English, its metric choices, its insight generators and its charts through
   SYSVIEW; everything structural is shared. Nothing is invented: metrics and
   insights are computed from the platform's own gold tables. */
const SystemPage = (() => {
  const n = v => v == null ? '—' : Number(v).toLocaleString('en-GB');
  const pct = v => v == null ? '—' : v + '%';
  const money = v => v == null ? '—' : (v >= 1e9 ? '£' + (v/1e9).toFixed(2) + 'bn'
                    : v >= 1e6 ? '£' + (v/1e6).toFixed(1) + 'm' : '£' + n(Math.round(v)));

  // The layered sub-nav. Sections render only if they have content, and the
  // nav lists only the ones that rendered — so an empty system never shows a
  // dead link.
  const SECTIONS = [
    ['overview',    'Overview'],
    ['join',        'The missing join'],
    ['numbers',     'Key numbers'],
    ['data',        'The data'],
    ['explore',     'Explore'],
    ['trends',      'Over time'],
    ['insights',    'Key insights'],
    ['pipeline',    'How it works'],
    ['sources',     'Sources'],
    ['method',      'Methodology'],
    ['records',     'The records'],
    ['related',     'Related'],
  ];

  function freshest(sources) {
    const dated = sources.filter(s => s.fetched && s.ok);
    if (!dated.length) return null;
    return dated.sort((a,b) => new Date(b.fetched) - new Date(a.fetched))[0];
  }

  // ---- the per-system data journey, scoped like the drawer's was ----
  function journeyOver(id, meta, info, sources, out) {
    const mb = b => !b ? '' : (b >= 1e9 ? (b/1e9).toFixed(1)+' GB' : b >= 1e6 ? (b/1e6).toFixed(1)+' MB' : Math.round(b/1e3)+' KB');
    const pubs = [...new Set(sources.map(s => s.publisher).filter(Boolean))];
    const live = sources.filter(s => s.ok).length;
    const bytes = sources.reduce((a, s) => a + (s.bytes || 0), 0);
    const spineOne = meta.spine === 'both' ? 'place + entity'
                   : meta.spine === 'place' ? 'place spine' : 'entity spine';
    const spineText = meta.spine === 'both'
        ? 'This system needs both joins: each record is placed on the map and matched to the organisation behind it.'
      : meta.spine === 'place'
        ? 'Each record is resolved to a place — a property or a postcode, then the district it sits in.'
        : 'Each record is resolved to one organisation — a company number or registered charity.';
    let headline = '';
    try {
      const sp = (typeof CARDS !== 'undefined') && CARDS.SPEC && CARDS.SPEC[id];
      const h = sp && sp.headline && sp.headline(out);
      if (h) headline = (h.trend != null ? (h.trend > 0 ? '+' : '') + h.trend + '%'
        : (h.prefix||'') + (h.value != null ? n(h.value) : '') + (h.unit||'')) + (h.label ? ' ' + h.label : '');
    } catch (e) {}
    return {
      source:  { one: `${sources.length} feed${sources.length===1?'':'s'}`,
        detail: `Computed from ${sources.length} published source${sources.length===1?'':'s'}: ` + sources.map(s => s.name).join('; ') + '. None requires an account, key or fee.',
        stat: pubs.length ? `Publishers: ${pubs.join(' · ')}` : '' },
      collect: { one: bytes ? `${mb(bytes)} fetched` : `${live}/${sources.length} live`,
        detail: (Platform.collectionNote(id) || 'Every feed is open to an anonymous request.') + ' A source that stops responding shows as failing rather than serving stale data.',
        stat: `${live} of ${sources.length} live` + (bytes ? ` · ${mb(bytes)} on disk` : '') },
      process: { one: spineOne, detail: spineText + ' This is the join government data is missing.', stat: null },
      validate:{ one: 'coverage attached',
        detail: (Platform.systemMethod(id) || info.method || 'Every figure carries the share of records it was computed over.'),
        stat: 'Nothing modelled or estimated — every value is computed from the feeds above' },
      groundtruth: { one: headline || meta.n, detail: `${info.question} ${info.why || ''}`.trim(),
        stat: headline ? `${meta.n} · ${headline}` : meta.n },
      public: { one: 'this page', detail: 'Published as open figures here. Every number can be traced back through the stages above.', stat: null },
    };
  }

  function explain(shows, read, standout) {
    return `<div class="sp-explain">
      <div class="sp-explain__i"><div class="sp-explain__k">What this shows</div><p>${shows}</p></div>
      <div class="sp-explain__i"><div class="sp-explain__k">How to read it</div><p>${read}</p></div>
      <div class="sp-explain__i"><div class="sp-explain__k">What stands out</div><p>${standout}</p></div>
    </div>`;
  }

  let root, host;

  function render(id) {
    const meta = SYSTEMS.find(x => x.id === id);
    const info = DETAIL[id];
    if (!meta || !info) return;
    const out  = Platform.sys(id);
    const spec = (typeof CARDS !== 'undefined' && CARDS.SPEC) ? CARDS.SPEC[id] : null;
    const view = (typeof SYSVIEW !== 'undefined') ? (SYSVIEW[id] || {}) : {};
    const sources = Platform.systemProvenance(id);
    const fresh = freshest(sources);
    const fr = fresh ? GT.freshness(fresh.cadence, fresh.fetched) : {state:'unknown', label:'provenance pending'};
    const domain = (spec && spec.domain) || meta.dom || '';
    const icon = (spec && spec.icon) || '◍';
    const spineLabel = meta.spine === 'both' ? 'WHERE + WHO' : meta.spine === 'place' ? 'WHERE' : 'WHO';

    // ---- section content ----
    const present = new Set();
    const S = {};

    // Overview
    S.overview = `<div class="sp-lede">
      <div class="sp-lede__i"><div class="sp-lede__k">What is this?</div><p>${view.whatIs || info.question}</p></div>
      <div class="sp-lede__i"><div class="sp-lede__k">Why does it matter?</div><p>${view.why || info.why}</p></div>
      <div class="sp-lede__i"><div class="sp-lede__k">What GroundTruth shows</div><p>${view.shows || 'The current figures for this question, computed from published data and traceable to source.'}</p></div>
    </div>`;
    present.add('overview');

    // The missing join — GroundTruth's core differentiator, made visible.
    // WHAT is recorded, the WHERE/WHO joins added, and the before->after story.
    const j = (typeof JOINS !== 'undefined') ? JOINS[id] : null;
    if (j) {
      const w = (k, lab, cls) => `<div class="mj__w ${cls}">
        <span class="mj__wk">${lab}</span>
        <p>${j[k] || 'No join — this dimension is not in the source.'}</p></div>`;
      const stage = (cls, lab, txt, i) => `<div class="mj__stage ${cls}" style="--i:${i}">
        <div class="mj__lab">${lab}</div><p>${txt}</p></div>`;
      S.join = `<div class="mj">
        <div class="mj__www">
          ${w('what', 'WHAT', 'mj__w--what')}
          ${w('where', 'WHERE', 'mj__w--where')}
          ${w('who', 'WHO', 'mj__w--who')}
        </div>
        <div class="mj__flow" data-reveal>
          ${stage('mj__stage--before', 'Before GroundTruth', j.before, 0)}
          <div class="mj__arrow" style="--i:1">→</div>
          ${stage('mj__stage--connect', 'GroundTruth connects', j.connect, 2)}
          <div class="mj__arrow" style="--i:3">→</div>
          ${stage('mj__stage--after', 'After', j.after, 4)}
          <div class="mj__arrow" style="--i:5">→</div>
          ${stage('mj__stage--possible', 'What becomes possible', j.possible, 6)}
        </div>
      </div>`;
      present.add('join');
    }

    // Key numbers
    const metrics = (view.metrics ? view.metrics(out) : []).filter(Boolean);
    metrics.push({ label:'Data freshness', value: fr.state==='current'?'Current':fr.state==='stale'?'Awaiting update':'—',
      sub: fresh ? `${fresh.name} · ${fr.label}` : 'source provenance pending' });
    if (metrics.length) {
      S.numbers = `<div class="sp-cards">${metrics.map(m => `<div class="sp-card">
        <div class="sp-card__l">${m.label}</div>
        <div class="sp-card__v">${m.value}</div>
        ${m.sub ? `<div class="sp-card__s">${m.sub}</div>` : ''}</div>`).join('')}</div>`;
      present.add('numbers');
    }

    // The data (primary visual + explanation). Charts drawn after mount.
    if (view.primary) {
      S.data = `<div class="sp-viz">
        <div class="sp-viz__chart" data-chart="primary"></div>
        ${view.primary.explain ? explain(view.primary.explain.shows, view.primary.explain.read, view.primary.explain.standout) : ''}
      </div>` + (view.secondary ? `<div class="sp-viz mt-4">
        ${view.secondary.title ? `<div class="sp-h">${view.secondary.title}</div>` : ''}
        <div class="sp-viz__chart" data-chart="secondary"></div>
        ${view.secondary.explain ? explain(view.secondary.explain.shows, view.secondary.explain.read, view.secondary.explain.standout) : ''}
      </div>` : '');
      present.add('data');
    }

    // Explore — interactive filters, only where the data supports them.
    // A location picker for systems with per-area rows; a year picker for
    // systems with a genuine back-series. Never shown when there is nothing to
    // filter, so the control can't imply data that isn't there.
    const exp = view.explore ? view.explore(out) : null;   // {by,label,rows:[{key,name}],detail(key)->[{label,value,sub}]}
    const tf  = view.timeFilter ? view.timeFilter(out) : null; // {years:[...],default,apply(year)->{cards,barsRows,barsFmt,caption}}
    if ((exp && exp.rows && exp.rows.length) || (tf && tf.years && tf.years.length)) {
      S.explore = (exp && exp.rows.length ? `
        <div class="sp-flt">
          <label class="sp-flt__lab" for="spLoc">Pick a ${exp.label || 'place'}</label>
          <select class="sp-flt__sel" id="spLoc" data-explore>
            <option value="">${exp.placeholder || 'Choose one…'}</option>
            ${exp.rows.map(r => `<option value="${r.key}">${r.name}</option>`).join('')}
          </select>
          ${exp.hint ? `<span class="sp-flt__hint">${exp.hint}</span>` : ''}
        </div>
        <div class="sp-flt__out" data-explore-out></div>` : '')
        + (tf && tf.years.length ? `
        <div class="sp-flt mt-3">
          <span class="sp-flt__lab">Pick a year</span>
          <div class="sp-yrs" data-year>${tf.years.map(y =>
            `<button class="sp-yr${y === tf.default ? ' is-on' : ''}" data-y="${y}">${tf.yearLabel ? tf.yearLabel(y) : y}</button>`).join('')}</div>
        </div>
        <div class="sp-flt__out" data-year-out></div>` : '');
      present.add('explore');
    }

    // Over time — honest note when there is no series
    const trend = view.trends ? view.trends(out) : null;
    if (trend) {
      S.trends = (trend.cards ? `<div class="sp-cards sp-cards--3">${trend.cards.map(c => `<div class="sp-card">
        <div class="sp-card__l">${c.label}</div><div class="sp-card__v">${c.value}</div>
        ${c.sub?`<div class="sp-card__s">${c.sub}</div>`:''}</div>`).join('')}</div>` : '')
        + (trend.draw ? `<div class="sp-viz mt-4"><div class="sp-viz__chart" data-chart="trend"></div>
        ${trend.explain ? explain(trend.explain.shows, trend.explain.read, trend.explain.standout) : ''}</div>` : '')
        + (trend.note ? `<div class="note mt-3"><div class="note__title">On history</div><p>${trend.note}</p></div>` : '');
      present.add('trends');
    } else {
      S.trends = `<div class="note"><div class="note__title">A point-in-time picture</div>
        <p>This system currently publishes the latest snapshot. When the source releases a comparable back-series, this page will show the change over time here rather than a single number.</p></div>`;
      present.add('trends');
    }

    // Key insights
    const insights = (view.insights ? view.insights(out) : []).filter(Boolean);
    if (insights.length) {
      S.insights = `<ul class="sp-ins">${insights.map(t => `<li class="sp-ins__i"><span class="sp-ins__b"></span><span>${t}</span></li>`).join('')}</ul>
        <p class="card__s mt-2">Each insight is read directly from the figures above, not written by hand.</p>`;
      present.add('insights');
    }

    // Pipeline
    S.pipeline = `<div class="jn" data-chart="journey"></div>`;
    present.add('pipeline');

    // Sources
    if (sources.length) {
      S.sources = `<div class="stack" style="gap:.5rem">${sources.map(src => `
        <div class="sp-src">
          <div class="row" style="justify-content:space-between;align-items:baseline">
            <span style="font-size:13.5px;font-weight:600">${src.name}</span>
            <span class="tag ${src.ok?'tag--ok':'tag--bad'}">${src.status}</span></div>
          <div class="card__s" style="font-size:12px;margin-top:.15rem">${src.publisher}</div>
          <div class="row card__s mono" style="font-size:10.5px;margin-top:.35rem;gap:.8rem;color:var(--ink-3)">
            <span>${src.licence || 'licence not stated'}</span><span>${src.cadence || 'cadence not stated'}</span>
            ${src.bytes ? `<span>${(src.bytes/1e6).toFixed(1)} MB</span>` : ''}
          </div></div>`).join('')}</div>`;
      present.add('sources');
    }

    // Methodology
    const defs = view.definitions || [];
    S.method = `<div class="sp-method">
      <div class="sp-method__row"><div class="sp-method__k">How it is computed</div><p>${Platform.systemMethod(id) || info.method}</p></div>
      <div class="sp-method__row"><div class="sp-method__k">Collection</div><p>${Platform.collectionNote(id) || 'Every source behind this system is open to an anonymous request — no account, key or fee.'}</p></div>
      <div class="sp-method__row"><div class="sp-method__k">Validation</div><p>Every figure carries the share of records it was computed over; ambiguous matches are reported, not guessed. Nothing is modelled or estimated.</p></div>
      <div class="sp-method__row"><div class="sp-method__k">Coverage</div><p>${view.coverage || 'England, latest published release of each source.'}${Platform.placeJoinNote(id) ? `<br><span style="display:inline-block;margin-top:.4rem">${Platform.placeJoinNote(id)}</span>` : ''}</p></div>
      ${defs.length ? `<div class="sp-method__row"><div class="sp-method__k">Definitions</div><dl class="sp-defs">${defs.map(d => `<dt>${d.t}</dt><dd>${d.d}</dd>`).join('')}</dl></div>` : ''}
    </div>`;
    present.add('method');

    // Limitations (folded into methodology block visually but its own anchor)
    S.method += `<div class="sp-h mt-5">Data limitations</div>
      <div class="stack mt-2" style="gap:.5rem">${[...(info.limits || []), ...Platform.liveLimits(id)].map((l,i) => `
        <div class="step"><div class="step__n">${i+1}</div>
        <p class="card__desc" style="flex:1;min-width:0;padding-top:.15rem">${l}</p></div>`).join('')}</div>`;

    // Records (secondary — collapsed by default)
    S.records = `<details class="sp-rec"><summary class="sp-rec__sum">View the underlying figures</summary>
      <div class="sp-rec__body mt-3">${renderFindings(id, out)}</div></details>`;
    present.add('records');

    // Related
    const rel = (view.related || []).map(r => {
      const m = SYSTEMS.find(x => x.id === r.id); const sp = (typeof CARDS!=='undefined'&&CARDS.SPEC)?CARDS.SPEC[r.id]:null;
      if (!m) return '';
      return `<a class="sp-rel" href="#system/${r.id}"><span class="sp-rel__ico">${(sp&&sp.icon)||'◍'}</span>
        <span class="sp-rel__tx"><span class="sp-rel__nm">${m.n}</span><span class="sp-rel__why">${r.why}</span></span>
        <span class="sp-rel__go">→</span></a>`;
    }).filter(Boolean).join('');
    if (rel) { S.related = `<div class="sp-rels">${rel}</div>`; present.add('related'); }

    // ---- assemble ----
    const nav = SECTIONS.filter(([k]) => present.has(k))
      .map(([k,l]) => `<a class="sp-nav__i" href="#sp-${k}" data-sp="${k}">${l}</a>`).join('');
    const sectionHTML = SECTIONS.filter(([k]) => present.has(k)).map(([k,l]) => `
      <section class="sp-sec" id="sp-${k}"><h2 class="sp-sec__h">${l}</h2>${S[k]}</section>`).join('');

    root.innerHTML = `
      <header class="sp-top">
        <button class="sp-back" id="spBack">← All systems</button>
        <div class="sp-top__nav">
          <button class="sp-step" id="spPrev" title="Previous system">‹</button>
          <button class="sp-step" id="spNext" title="Next system">›</button>
        </div>
      </header>
      <div class="sp-hero">
        <div class="sp-hero__ico">${icon}</div>
        <div class="sp-hero__tx">
          <div class="sp-hero__kick">${domain.toUpperCase()} · ${spineLabel} · ${meta.st.toUpperCase()}</div>
          <h1 class="sp-hero__h">${meta.n}</h1>
          <p class="sp-hero__sub">${view.whatIs ? info.question : info.question}</p>
        </div>
        <div class="fresh fresh--${fr.state} sp-hero__fresh"><i></i>${fr.label}</div>
      </div>
      <nav class="sp-nav">${nav}</nav>
      <div class="sp-body">${sectionHTML}</div>
      <footer class="sp-foot card__s">Every figure on this page is computed on this machine from the sources listed above. Nothing is modelled, estimated or filled in by hand.</footer>`;

    // ---- draw charts (after DOM exists) ----
    const $ = sel => root.querySelector(sel);
    if (view.primary && view.primary.draw) view.primary.draw(out, $('[data-chart="primary"]'), { n, pct, money, GT, Platform });
    if (view.secondary && view.secondary.draw) view.secondary.draw(out, $('[data-chart="secondary"]'), { n, pct, money, GT, Platform });
    if (trend && trend.draw) trend.draw(out, $('[data-chart="trend"]'), { n, pct, money, GT, Platform });
    const jn = $('[data-chart="journey"]');
    if (jn && GT.journey) GT.journey(jn, Platform.pipeline() || {}, { over: journeyOver(id, meta, info, sources, out) });

    GT.countAll(root); GT.meters(root);

    // ---- filters ----
    const card = m => `<div class="sp-card"><div class="sp-card__l">${m.label}</div>
      <div class="sp-card__v">${m.value}</div>${m.sub ? `<div class="sp-card__s">${m.sub}</div>` : ''}</div>`;
    if (exp && exp.rows && exp.rows.length) {
      const sel = $('[data-explore]'); const outEl = $('[data-explore-out]');
      const mapEl = $('[data-chart="primary"]');
      sel.addEventListener('change', () => {
        const key = sel.value;
        // clear any map highlight
        if (mapEl && mapEl.__map) {
          mapEl.querySelectorAll('path.is-sel').forEach(p => p.classList.remove('is-sel'));
        }
        if (!key) { outEl.innerHTML = ''; if (mapEl && mapEl.__map) mapEl.__map.resetZoom(); return; }
        const cards = (exp.detail ? exp.detail(key) : []).filter(Boolean);
        const row = exp.rows.find(r => r.key === key);
        outEl.innerHTML = `<div class="sp-flt__head">${row ? row.name : ''}</div>
          <div class="sp-cards sp-cards--3 mt-2">${cards.map(card).join('')}</div>`;
        GT.countAll(outEl);
        if (mapEl && mapEl.__map) {
          const p = mapEl.querySelector(`path[data-c="${key}"]`);
          if (p) { p.classList.add('is-sel'); mapEl.__map.zoomTo(key); }
        }
      });
    }
    if (tf && tf.years && tf.years.length) {
      const outEl = $('[data-year-out]');
      const paint = year => {
        root.querySelectorAll('[data-year] .sp-yr').forEach(b => b.classList.toggle('is-on', b.dataset.y == year));
        const r = tf.apply(year);
        outEl.innerHTML = (r.cards ? `<div class="sp-cards sp-cards--3">${r.cards.map(card).join('')}</div>` : '')
          + (r.barsRows ? `<div class="sp-viz mt-3">${r.caption ? `<div class="sp-h">${r.caption}</div>` : ''}<div class="sp-viz__chart" data-year-chart></div></div>` : '');
        if (r.barsRows) GT.bars(outEl.querySelector('[data-year-chart]'), r.barsRows, { fmt: r.barsFmt || (v => v.toLocaleString('en-GB')) });
        GT.countAll(outEl);
      };
      root.querySelectorAll('[data-year] .sp-yr').forEach(b => b.addEventListener('click', () => paint(b.dataset.y)));
      paint(tf.default);
    }

    // ---- interactions ----
    $('#spBack').addEventListener('click', close);
    const ids = SYSTEMS.map(x => x.id); const i = ids.indexOf(id);
    $('#spPrev').addEventListener('click', () => go(ids[(i - 1 + ids.length) % ids.length]));
    $('#spNext').addEventListener('click', () => go(ids[(i + 1) % ids.length]));

    // reveal-on-scroll for the missing-join flow (honours reduced motion)
    const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
    root.querySelectorAll('[data-reveal]').forEach(el => {
      if (reduce) { el.classList.add('in'); return; }
      const io = new IntersectionObserver((es, o) => es.forEach(e => {
        if (e.isIntersecting) { el.classList.add('in'); o.disconnect(); }
      }), { root, threshold: 0.2 });
      io.observe(el);
    });

    // sub-nav scroll-spy
    const navLinks = [...root.querySelectorAll('.sp-nav__i')];
    const secs = navLinks.map(a => root.querySelector('#sp-' + a.dataset.sp)).filter(Boolean);
    if (secs.length) {
      const io = new IntersectionObserver(es => es.forEach(e => {
        if (!e.isIntersecting) return;
        navLinks.forEach(a => a.classList.toggle('is-on', a.dataset.sp === e.target.id.replace('sp-','')));
      }), { root, rootMargin: '-15% 0px -75% 0px', threshold: 0 });
      secs.forEach(s => io.observe(s));
      navLinks.forEach(a => a.addEventListener('click', ev => {
        ev.preventDefault();
        root.querySelector('#sp-' + a.dataset.sp).scrollIntoView({ behavior: 'smooth', block: 'start' });
      }));
    }

    host.classList.add('on');
    document.body.style.overflow = 'hidden';
    root.scrollTop = 0;
  }

  // The comparison matrix: all 13 systems on one screen, WHAT/WHERE/WHO plus a
  // verified headline each — visual, not a plain table, and every row is a link.
  function compare() {
    const headline = id => {
      try {
        const sp = (typeof CARDS !== 'undefined' && CARDS.SPEC) ? CARDS.SPEC[id] : null;
        const h = sp && sp.headline && sp.headline(Platform.sys(id));
        if (!h) return '';
        return h.trend != null ? (h.trend > 0 ? '+' : '') + h.trend + '%'
          : (h.prefix || '') + (h.value != null ? n(h.value) : '') + (h.unit || '');
      } catch (e) { return ''; }
    };
    const rows = SYSTEMS.map(m => {
      const sp = (typeof CARDS !== 'undefined' && CARDS.SPEC) ? CARDS.SPEC[m.id] : null;
      const jj = (typeof JOINS !== 'undefined') ? JOINS[m.id] : {};
      const info = DETAIL[m.id] || {};
      const dash = '<span class="cmp__none">no join</span>';
      return `<a class="cmp__row" href="#system/${m.id}">
        <div class="cmp__sys"><span class="cmp__ico">${(sp && sp.icon) || '◍'}</span>
          <span><span class="cmp__nm">${m.n}</span>
          <span class="cmp__q">${info.question || ''}</span></span></div>
        <div class="cmp__cell" data-h="WHAT">${jj.what || ''}</div>
        <div class="cmp__cell cmp__cell--where" data-h="WHERE">${jj.where || dash}</div>
        <div class="cmp__cell cmp__cell--who" data-h="WHO">${jj.who || dash}</div>
        <div class="cmp__metric" data-h="VERIFIED">${headline(m.id)}</div>
      </a>`;
    }).join('');
    root.innerHTML = `
      <header class="sp-top">
        <button class="sp-back" id="spBack">← Home</button>
      </header>
      <div class="sp-hero">
        <div class="sp-hero__ico">▦</div>
        <div class="sp-hero__tx">
          <div class="sp-hero__kick">ALL THIRTEEN SYSTEMS</div>
          <h1 class="sp-hero__h">What · Where · Who</h1>
          <p class="sp-hero__sub">Every system records something (WHAT). GroundTruth adds the geographic join (WHERE) and the organisation join (WHO). Here is all thirteen at a glance — each row opens the full system.</p>
        </div>
      </div>
      <div class="cmp">
        <div class="cmp__head">
          <div>System</div><div>WHAT is recorded</div>
          <div class="cmp__cell--where">WHERE join</div><div class="cmp__cell--who">WHO join</div><div>Verified</div>
        </div>
        ${rows}
      </div>
      <footer class="sp-foot card__s">Every figure is computed from published records on one machine. Nothing is estimated.</footer>`;
    root.querySelector('#spBack').addEventListener('click', close);
    host.classList.add('on');
    document.body.style.overflow = 'hidden';
    root.scrollTop = 0;
  }

  // ---- organisation knowledge graph (the WHO spine) ----
  const SYS_NAME = id => { const m = SYSTEMS.find(x => x.id === id); return m ? m.n : id; };
  const orgMoney = v => v == null ? '—' : (v >= 1e9 ? '£' + (v/1e9).toFixed(2) + 'bn'
                   : v >= 1e6 ? '£' + (v/1e6).toFixed(1) + 'm' : '£' + n(Math.round(v)));

  function orgIndex() {
    const orgs = Platform.organisations();
    const chip = s => `<span class="org-sys org-sys--${s}">${SYS_NAME(s)}</span>`;
    const foot = o => {
      const bits = [];
      if (o.care) bits.push(`${n(o.care.beds)} care beds · ${n(o.care.authorities)} authorities`);
      if (o.proc) bits.push(`${n(o.proc.awards)} award${o.proc.awards === 1 ? '' : 's'} · ${orgMoney(o.proc.value)}`);
      return bits.join('  ·  ');
    };
    const row = o => `<a class="org-row" href="#org/${o.id}" data-name="${(o.name || '').toLowerCase()}" data-cross="${o.systems.length > 1}">
      <div class="org-row__main">
        <span class="org-row__nm">${o.name}</span>
        <span class="org-row__foot">${foot(o)}</span>
      </div>
      <div class="org-row__sys">${o.systems.map(chip).join('')}</div>
      <span class="org-row__go">→</span></a>`;
    const cross = orgs.filter(o => o.systems.length > 1).length;
    root.innerHTML = `
      <header class="sp-top"><button class="sp-back" id="spBack">← Home</button></header>
      <div class="sp-hero">
        <div class="sp-hero__ico">◉</div>
        <div class="sp-hero__tx">
          <div class="sp-hero__kick">THE WHO SPINE</div>
          <h1 class="sp-hero__h">Organisations</h1>
          <p class="sp-hero__sub">Every system resolves the organisations it names to one Companies House number. That shared identifier is the join — an organisation seen in more than one system is one entity from two angles. ${n(orgs.length)} shown, ${cross} appearing in more than one system.</p>
        </div>
      </div>
      <div class="sp-nav" style="gap:.6rem;padding:.7rem 0">
        <input class="org-search" id="orgSearch" type="search" placeholder="Search organisations…" aria-label="Search organisations">
        <label class="org-toggle"><input type="checkbox" id="orgCross"> In more than one system</label>
      </div>
      <div class="org-list" id="orgList">${orgs.map(row).join('')}</div>
      <footer class="sp-foot card__s">Only organisations whose company number actually appears in a system are listed there. Every figure is computed from published records. Nothing is estimated.</footer>`;
    root.querySelector('#spBack').addEventListener('click', close);
    const list = root.querySelector('#orgList');
    const q = root.querySelector('#orgSearch');
    const cx = root.querySelector('#orgCross');
    const filter = () => {
      const term = q.value.trim().toLowerCase();
      const only = cx.checked;
      list.querySelectorAll('.org-row').forEach(a => {
        const ok = (!term || a.dataset.name.includes(term)) && (!only || a.dataset.cross === 'true');
        a.style.display = ok ? '' : 'none';
      });
    };
    q.addEventListener('input', filter);
    cx.addEventListener('change', filter);
    host.classList.add('on'); document.body.style.overflow = 'hidden'; root.scrollTop = 0;
  }

  function orgProfile(id) {
    const o = Platform.organisations().find(x => x.id === id);
    if (!o) { location.hash = 'org'; return; }
    const owners = (o.owners || []).map(w =>
      `<div class="org-node org-node--owner"><span class="org-node__k">${w.kind === 'person' ? 'PERSON' : 'ORGANISATION'}</span>${w.name}</div>`
    ).join('') || `<div class="org-node org-node--empty">No person of significant control recorded</div>`;
    const sysNodes = o.systems.map(s =>
      `<a class="org-node org-node--sys org-sys--${s}" href="#system/${s}"><span class="org-node__k">SYSTEM</span>${SYS_NAME(s)} →</a>`
    ).join('');
    const careBlock = o.care ? `
      <div class="org-sec"><h2 class="sp-sec__h">Care sector — where (Bellwether)</h2>
        <div class="sp-cards sp-cards--3">
          <div class="sp-card"><div class="sp-card__l">Care beds</div><div class="sp-card__v">${n(o.care.beds)}</div><div class="sp-card__s">across ${n(o.care.locations)} locations</div></div>
          <div class="sp-card"><div class="sp-card__l">Local authorities</div><div class="sp-card__v">${n(o.care.authorities)}</div><div class="sp-card__s">councils it operates in</div></div>
          <div class="sp-card"><div class="sp-card__l">Brand</div><div class="sp-card__v" style="font-size:18px">${(o.brand || '—').replace(/^BRAND /, '')}</div><div class="sp-card__s">as the regulator groups it</div></div>
        </div>
        ${o.care.top_las && o.care.top_las.length ? `<div class="sp-h mt-4">Largest authorities by beds</div>
          <div class="org-bars">${o.care.top_las.map(l => `<div class="org-bar"><span>${l.name}</span><b>${n(l.beds)}</b></div>`).join('')}</div>` : ''}
      </div>` : '';
    const procBlock = o.proc ? `
      <div class="org-sec"><h2 class="sp-sec__h">Public procurement — who (Sentinel)</h2>
        <div class="sp-cards sp-cards--3">
          <div class="sp-card"><div class="sp-card__l">Awards</div><div class="sp-card__v">${n(o.proc.awards)}</div><div class="sp-card__s">public contracts won</div></div>
          <div class="sp-card"><div class="sp-card__l">Total value</div><div class="sp-card__v">${orgMoney(o.proc.value)}</div><div class="sp-card__s">across ${n(o.proc.buyers)} buyer${o.proc.buyers === 1 ? '' : 's'}</div></div>
          <div class="sp-card"><div class="sp-card__l">Buyers</div><div class="sp-card__v">${n(o.proc.buyers)}</div><div class="sp-card__s">public bodies</div></div>
        </div>
        ${o.proc.top_buyers && o.proc.top_buyers.length ? `<div class="sp-h mt-4">Largest buyers by value</div>
          <div class="org-bars">${o.proc.top_buyers.map(b => `<div class="org-bar"><span>${b.name}</span><b>${orgMoney(b.value)}</b></div>`).join('')}</div>` : ''}
      </div>` : '';
    const crossNote = o.systems.length > 1 ? `<div class="note mt-3" style="border-left:3px solid var(--uk-red)">
        <div class="note__title">One organisation, ${o.systems.length} systems</div>
        <p>${o.name} appears in ${o.systems.map(SYS_NAME).join(' and ')} — the same company number in both. Each government dataset saw only its own slice; the shared identifier is what joins them into one organisation.</p></div>` : '';
    root.innerHTML = `
      <header class="sp-top"><button class="sp-back" id="spBack">← All organisations</button></header>
      <div class="sp-hero">
        <div class="sp-hero__ico">◉</div>
        <div class="sp-hero__tx">
          <div class="sp-hero__kick">ORGANISATION · ${o.status ? o.status.toUpperCase() : 'STATUS UNKNOWN'}${o.town ? ' · ' + o.town.toUpperCase() : ''}</div>
          <h1 class="sp-hero__h">${o.name}</h1>
          <p class="sp-hero__sub">Company ${o.id}${o.incorporated ? ' · incorporated ' + String(o.incorporated).slice(0, 10) : ''}. ${o.systems.map(SYS_NAME).join(' + ')}.</p>
        </div>
      </div>
      <div class="sp-body">
        <section class="sp-sec"><h2 class="sp-sec__h">The connection</h2>
          <div class="org-graph">
            <div class="org-col"><div class="org-col__k">Controlled by</div>${owners}</div>
            <div class="org-graph__arrow">→</div>
            <div class="org-col"><div class="org-col__k">Organisation</div>
              <div class="org-node org-node--self">${o.name}<span class="org-node__k">CO. ${o.id}</span></div></div>
            <div class="org-graph__arrow">→</div>
            <div class="org-col"><div class="org-col__k">Appears in</div>${sysNodes}</div>
          </div>
          ${crossNote}
        </section>
        ${careBlock}${procBlock}
        <section class="sp-sec"><h2 class="sp-sec__h">Evidence</h2>
          <p class="card__s">This profile is built only from records that name this company number: CQC care registrations (Bellwether) and Contracts Finder awards (Sentinel), with ownership from Companies House persons of significant control. Open the systems above to see the underlying records.</p>
        </section>
      </div>
      <footer class="sp-foot card__s">Every figure is computed from published records on one machine. Nothing is estimated.</footer>`;
    root.querySelector('#spBack').addEventListener('click', () => { location.hash = 'org'; });
    GT.countAll(root);
    host.classList.add('on'); document.body.style.overflow = 'hidden'; root.scrollTop = 0;
  }

  // ---- cross-system search: one box over systems, organisations, locations ----
  function search() {
    root.innerHTML = `
      <header class="sp-top"><button class="sp-back" id="spBack">← Close</button></header>
      <div class="gs">
        <div class="gs__box">
          <span class="gs__ico">⌕</span>
          <input class="gs__input" id="gsInput" type="search" autocomplete="off"
            placeholder="Search organisations, places, systems…" aria-label="Search">
        </div>
        <p class="gs__hint">One search across all thirteen systems. Every result shows which systems it appears in.</p>
        <div class="gs__results" id="gsResults"></div>
      </div>`;
    root.querySelector('#spBack').addEventListener('click', close);
    const input = root.querySelector('#gsInput');
    const results = root.querySelector('#gsResults');
    const orgs = Platform.organisations();
    const places = Platform.placeList ? Platform.placeList() : [];
    const nf = v => Number(v || 0).toLocaleString('en-GB');

    const render = term => {
      term = term.trim().toLowerCase();
      if (!term) {
        results.innerHTML = `<div class="gs__empty">Try a company (“Barchester”), a district (“Leeds”), or a system (“flood”).</div>`;
        return;
      }
      const sysHits = SYSTEMS.filter(m => {
        const sp = (typeof CARDS !== 'undefined' && CARDS.SPEC) ? CARDS.SPEC[m.id] : null;
        const info = DETAIL[m.id] || {};
        return (m.n + ' ' + (sp ? sp.domain + ' ' + sp.purpose : '') + ' ' + (info.question || '')).toLowerCase().includes(term);
      }).slice(0, 6);
      const orgHits = orgs.filter(o => (o.name || '').toLowerCase().includes(term)).slice(0, 12);
      const placeHits = places.filter(p => (p.name || '').toLowerCase().includes(term)).slice(0, 12);

      const total = sysHits.length + orgHits.length + placeHits.length;
      if (!total) { results.innerHTML = `<div class="gs__empty">No matches for “${term}”.</div>`; return; }

      const sysBadge = id => `<span class="org-sys org-sys--${id === 'sentinel' || id === 'watchman' ? 'sentinel' : 'bellwether'}">${SYS_NAME(id)}</span>`;
      let html = '';
      if (sysHits.length) html += `<div class="gs__grp"><div class="gs__gk">Systems</div>${
        sysHits.map(m => { const sp = (typeof CARDS !== 'undefined' && CARDS.SPEC) ? CARDS.SPEC[m.id] : null;
          return `<a class="gs__r" href="#system/${m.id}"><span class="gs__ri">${sp ? sp.icon : '◍'}</span>
            <span class="gs__rt"><b>${m.n}</b><span>${sp ? sp.domain : ''} · ${DETAIL[m.id] ? DETAIL[m.id].question : ''}</span></span>
            <span class="gs__rw">${m.spine === 'both' ? 'WHERE+WHO' : m.spine === 'place' ? 'WHERE' : 'WHO'}</span></a>`; }).join('')}</div>`;
      if (orgHits.length) html += `<div class="gs__grp"><div class="gs__gk">Organisations · ${orgHits.length}</div>${
        orgHits.map(o => `<a class="gs__r" href="#org/${o.id}"><span class="gs__ri">◉</span>
          <span class="gs__rt"><b>${o.name}</b><span>${o.systems.length > 1 ? 'in ' + o.systems.length + ' systems' : 'in ' + SYS_NAME(o.systems[0])}${o.town ? ' · ' + o.town : ''}</span></span>
          <span class="gs__rsys">${o.systems.map(sysBadge).join('')}</span></a>`).join('')}</div>`;
      if (placeHits.length) html += `<div class="gs__grp"><div class="gs__gk">Places · ${placeHits.length}</div>${
        placeHits.map(p => `<button class="gs__r" data-place="${p.code}"><span class="gs__ri">▣</span>
          <span class="gs__rt"><b>${p.name}</b><span>${p.systems} of 13 systems report here</span></span>
          <span class="gs__rw">${p.systems}/13</span></button>`).join('')}</div>`;
      results.innerHTML = html;
      results.querySelectorAll('[data-place]').forEach(b => b.addEventListener('click', () => {
        close();
        if (window.__gtShowPlace) window.__gtShowPlace(b.dataset.place);
      }));
    };
    input.addEventListener('input', () => render(input.value));
    if (pendingQuery) { input.value = pendingQuery; pendingQuery = ''; }
    render(input.value);
    host.classList.add('on'); document.body.style.overflow = 'hidden'; root.scrollTop = 0;
    setTimeout(() => input.focus(), 50);
  }

  // Carries a query typed in the top bar across the route change, so the
  // search view opens already showing results rather than an empty box.
  let pendingQuery = '';
  function seedSearch(q) {
    const input = document.getElementById('gsInput');
    if (!input) return;
    input.value = q;
    input.dispatchEvent(new Event('input', {bubbles: true}));
    input.focus();
    input.setSelectionRange(q.length, q.length);
  }

  function go(id) { location.hash = 'system/' + id; }
  function open(id) { render(id); }
  function close() {
    host.classList.remove('on');
    document.body.style.overflow = '';
  }

  function boot(opts) {
    host = document.getElementById('syshost');
    root = document.getElementById('syspage');
    if (!host || !root) return;
    // The shell owns the router now. This keeps working standalone for anything
    // that still boots this module on its own.
    if (opts && opts.router === false) return;
    const route = () => {
      const m = location.hash.match(/^#system\/([a-z0-9_-]+)$/i);
      const om = location.hash.match(/^#org\/(.+)$/);
      if (m && SYSTEMS.some(x => x.id === m[1])) open(m[1]);
      else if (location.hash === '#compare') compare();
      else if (location.hash === '#search') search();
      else if (location.hash === '#org') orgIndex();
      else if (om) orgProfile(decodeURIComponent(om[1]));
      else if (host.classList.contains('on')) { host.classList.remove('on'); document.body.style.overflow = ''; }
    };
    addEventListener('hashchange', route);
    addEventListener('keydown', e => { if (e.key === 'Escape' && host.classList.contains('on')) { go(''); close(); } });

    // The top bar carries a real input. Typing in it opens the search view and
    // hands the query straight over, so the first keystroke is not thrown away.
    const top = document.getElementById('topSearch');
    if (top) {
      const handoff = () => {
        const q = top.value;
        pendingQuery = q;
        if (location.hash !== '#search') location.hash = 'search';
        else seedSearch(q);
        top.value = '';
      };
      top.addEventListener('input', () => { if (top.value.trim()) handoff(); });
      top.addEventListener('keydown', e => { if (e.key === 'Enter') { e.preventDefault(); handoff(); } });
    }

    addEventListener('keydown', e => {
      if (e.key === '/' && !/^(INPUT|TEXTAREA|SELECT)$/.test(e.target.tagName || '') && !host.classList.contains('on')) {
        e.preventDefault();
        if (top) top.focus(); else location.hash = 'search';
      }
    });
    route();
  }

  return { boot, render, compare, go, close, search, orgIndex, orgProfile, host: () => host, root: () => root };
})();
