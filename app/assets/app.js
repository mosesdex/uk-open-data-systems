/* UK GroundTruth prototype runtime. No dependencies: charts, maps and counters
   are drawn directly as SVG so the whole thing runs from static files. */
const GT = (() => {
  const fmt = n => n == null ? '—' : n.toLocaleString('en-GB');
  const pct = n => n == null ? '—' : n.toFixed(1) + '%';
  const money = n => n >= 1e9 ? '£' + (n/1e9).toFixed(2) + 'bn'
                  : n >= 1e6 ? '£' + (n/1e6).toFixed(1) + 'm'
                  : '£' + fmt(Math.round(n));

  /* ---- reveal on scroll ---- */
  function reveal(){
    const io = new IntersectionObserver(es => es.forEach(e => {
      if (e.isIntersecting){ e.target.classList.add('in'); io.unobserve(e.target); }
    }), {threshold:.08, rootMargin:'0px 0px -40px'});
    document.querySelectorAll('.rise:not(.in)').forEach((el,i) => {
      const box = el.getBoundingClientRect();
      // Anything already on screen, or scrolled past, is shown at once. A deep
      // link such as #systems jumps the page before the observer ever fires, and
      // without this the target section stays invisible for good.
      if (box.top < innerHeight && box.bottom > -innerHeight) {
        el.classList.add('in');
        return;
      }
      el.style.transitionDelay = Math.min(i*38, 320) + 'ms';
      io.observe(el);
    });
    // Last resort: never leave content hidden because an observer misfired.
    clearTimeout(reveal._t);
    reveal._t = setTimeout(() => {
      document.querySelectorAll('.rise:not(.in)').forEach(el => {
        const box = el.getBoundingClientRect();
        if (box.top < innerHeight * 1.5) el.classList.add('in');
      });
    }, 1200);
  }

  // A hash change moves the viewport without scrolling, so re-run the check.
  addEventListener('hashchange', () => reveal());

  /* ---- animated counters ---- */
  /* Figures are written at their true value, once.
     They used to count up from zero over 1.1s, which meant this platform spent
     the first second of every visit displaying numbers that were wrong -- 4.3%
     where the answer was 89.6%. On a product whose entire argument is that the
     figure traces to a record, that is the one flourish it cannot afford. The
     animation also ran on requestAnimationFrame, which suspends in a background
     tab, so a figure could be left frozen part-way up. */
  function count(el, to, opts={}){
    const dec = opts.dec || 0, pre = opts.pre || '', suf = opts.suf || '';
    el.textContent = pre + to.toLocaleString('en-GB',
      {minimumFractionDigits:dec, maximumFractionDigits:dec}) + suf;
  }
  function countAll(root=document){
    root.querySelectorAll('[data-count]').forEach(el => count(el, parseFloat(el.dataset.count),
      {dec:+(el.dataset.dec||0), pre:el.dataset.pre||'', suf:el.dataset.suf||''}));
  }

  /* ---- choropleth from real ONS boundaries ---- */
  /* Two ramps. Blue means "more of a neutral or good thing"; red means "more of
     a problem". Shading overdue inspections on the same scale as gigabit
     coverage would imply that more overdue inspections is an achievement. */
  const RAMPS = {
    blue: [[221,229,247],[53,99,201],[1,20,63]],
    red:  [[253,238,241],[224,110,130],[142,10,32]],
  };
  function ramp(t, key='blue'){
    const [a,b,c] = RAMPS[key] || RAMPS.blue;
    t = Math.max(0, Math.min(1, t));
    const m = t<.5 ? a.map((v,i)=>v+(b[i]-v)*(t/.5)) : b.map((v,i)=>v+(c[i]-v)*((t-.5)/.5));
    return `rgb(${m.map(Math.round).join(',')})`;
  }
  const NO_DATA = 'var(--line)';

  async function choropleth(el, {values={}, label='', notes={}, fallbackSpread=false,
                                 ramp:rampKey='blue'}={}){
    const gj = await fetch(el.dataset.geo || 'data/lad.geojson').then(r=>r.json());
    // project lon/lat -> screen, equirectangular scaled for UK latitudes
    let minX=1e9,minY=1e9,maxX=-1e9,maxY=-1e9;
    const K = Math.cos(53 * Math.PI/180);
    const pts = f => (f.geometry.type==='Polygon' ? [f.geometry.coordinates] : f.geometry.coordinates);
    gj.features.forEach(f => pts(f).forEach(p => p[0].forEach(([x,y])=>{
      const px = x*K; if(px<minX)minX=px; if(px>maxX)maxX=px; if(y<minY)minY=y; if(y>maxY)maxY=y;
    })));
    const W = 560, H = 700, pad = 12;
    const s = Math.min((W-pad*2)/(maxX-minX), (H-pad*2)/(maxY-minY));
    const ox = (W-(maxX-minX)*s)/2, oy = (H-(maxY-minY)*s)/2;
    const P = (x,y) => [((x*K-minX)*s+ox).toFixed(1), (H-((y-minY)*s+oy)).toFixed(1)];

    const svg = ['<svg class="mapsvg" viewBox="0 0 '+W+' '+H+'" preserveAspectRatio="xMidYMid meet"'
      + ' role="img" aria-label="Map of local authorities">'];
    const boxes = {};
    gj.features.forEach(f => {
      let bx0=1e9, by0=1e9, bx1=-1e9, by1=-1e9;
      const d = pts(f).map(poly => 'M' + poly[0].map(([x,y])=>{
        const [px,py] = P(x,y);
        const nx=+px, ny=+py;
        if(nx<bx0)bx0=nx; if(nx>bx1)bx1=nx; if(ny<by0)by0=ny; if(ny>by1)by1=ny;
        return px+','+py;
      }).join('L') + 'Z').join('');
      boxes[f.properties.c] = [bx0,by0,bx1,by1];
      svg.push(`<path d="${d}" fill="${NO_DATA}" data-c="${f.properties.c}"`
        + ` data-n="${f.properties.n}" tabindex="-1"><title>${f.properties.n}</title></path>`);
    });
    svg.push('</svg>');
    el.innerHTML = svg.join('') + '<div class="maptip" id="'+ (el.id||'m') +'-tip"></div>';

    const svgEl = el.querySelector('svg');
    const tip = el.querySelector('.maptip');
    const paths = [...el.querySelectorAll('path')];
    const home = [0,0,W,H];
    let current = {values:{}, label:'', rampKey};

    /* Recolour every district for a new metric.
       anime.js interpolates the fills and staggers them from the middle of the
       country outwards, so the map visibly re-shades instead of snapping. */
    function setMetric({values:vals={}, label:lbl='', notes:nts={}, ramp:rk='blue', animate=true}={}){
      current = {values:vals, label:lbl, notes:nts, rampKey:rk};
      const real = Object.values(vals).filter(v=>v!=null && !Number.isNaN(v));
      const lo = real.length ? Math.min(...real) : 0;
      const hi = real.length ? Math.max(...real) : 1;
      const targets = paths.map(p => {
        const v = vals[p.dataset.c];
        p.dataset.v = (v==null ? '' : v);
        if (v == null) return NO_DATA;
        const t = hi>lo ? (v-lo)/(hi-lo) : .5;
        return ramp(t, rk);
      });
      const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
      if (!animate || reduced || typeof anime === 'undefined') {
        paths.forEach((p,i) => { p.style.fill = targets[i]; });
        return;
      }
      paths.forEach((p,i) => { p.__target = targets[i]; });
      anime.animate(paths, {
        fill: (p) => p.__target,
        duration: 520,
        ease: 'outQuad',
        delay: anime.stagger(2.2, {from: 'center'}),
      });
    }

    /* Frame one district. Animating the viewBox keeps every path in place and
       simply moves the camera, which is cheaper and steadier than transforming
       316 elements. */
    function zoomTo(code, {padding=46, duration=620}={}){
      const b = boxes[code];
      const to = b
        ? (() => {
            const w = Math.max(b[2]-b[0], 40) + padding*2;
            const h = Math.max(b[3]-b[1], 40) + padding*2;
            const side = Math.max(w, h * (W/H));
            const cx = (b[0]+b[2])/2, cy = (b[1]+b[3])/2;
            return [cx - side/2, cy - (side*(H/W))/2, side, side*(H/W)];
          })()
        : home;
      const from = svgEl.getAttribute('viewBox').split(/\s+/).map(Number);
      const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
      if (reduced || typeof anime === 'undefined') {
        svgEl.setAttribute('viewBox', to.join(' ')); return;
      }
      const state = {a:from[0], b:from[1], c:from[2], d:from[3]};
      anime.animate(state, {
        a: to[0], b: to[1], c: to[2], d: to[3],
        duration, ease: 'inOutQuad',
        onUpdate: () => svgEl.setAttribute('viewBox',
          `${state.a.toFixed(1)} ${state.b.toFixed(1)} ${state.c.toFixed(1)} ${state.d.toFixed(1)}`),
      });
    }
    const resetZoom = () => zoomTo(null);

    paths.forEach(p => {
      p.addEventListener('mousemove', ev => {
        const r = el.getBoundingClientRect();
        const v = p.dataset.v;
        const has = v !== '' && v != null;
        const note = has && (current.notes || {})[p.dataset.c];
        tip.innerHTML = `<b>${p.dataset.n}</b><span>${has
          ? current.label.replace('{}', (+v).toLocaleString('en-GB'))
          : 'no value published here'}</span>${note
          ? `<em>${String(note).replace(/[&<>"]/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[ch]))}</em>` : ''}`;
        tip.classList.add('on');
        let x = ev.clientX-r.left+12, y = ev.clientY-r.top+12;
        if (x > r.width-190) x -= 200;
        tip.style.left = x+'px'; tip.style.top = y+'px';
      });
      p.addEventListener('mouseleave', () => tip.classList.remove('on'));
      p.addEventListener('click', () => {
        el.querySelectorAll('path.is-sel').forEach(o=>o.classList.remove('is-sel'));
        p.classList.add('is-sel');
        zoomTo(p.dataset.c);
        el.dispatchEvent(new CustomEvent('pick',
          {detail:{code:p.dataset.c, name:p.dataset.n, value:p.dataset.v}}));
      });
    });

    setMetric({values, label, notes, ramp:rampKey, animate:false});
    el.__map = {setMetric, zoomTo, resetZoom, paths, boxes, home};
    return el.__map;
  }

  /* ---- bar list ---- */
  function bars(el, rows, {fmt:f=fmt, max=null}={}){
    const hi = max ?? Math.max(...rows.map(r=>r.v));
    el.innerHTML = rows.map(r => `<div class="bar">
      <span class="bar__n" title="${r.n}">${r.n}</span>
      <span class="bar__t"><i class="bar__f" data-w="${(r.v/hi*100).toFixed(1)}"></i></span>
      <span class="bar__v">${f(r.v)}</span></div>`).join('');
    const io = new IntersectionObserver(es => es.forEach(e => {
      if(!e.isIntersecting) return;
      el.querySelectorAll('.bar__f').forEach((b,i) =>
        setTimeout(()=>{ b.style.width = b.dataset.w + '%'; }, i*55));
      io.disconnect();
    }),{threshold:.25});
    io.observe(el);
  }

  /* ---- donut ---- */
  function donut(el, segs, {size=132, thick=15, center=''}={}){
    const r = (size-thick)/2, C = 2*Math.PI*r, tot = segs.reduce((a,s)=>a+s.v,0);
    let off = 0;
    const parts = segs.map(s => {
      const len = tot? s.v/tot*C : 0;
      const el2 = `<circle cx="${size/2}" cy="${size/2}" r="${r}" fill="none" stroke="${s.c}"
        stroke-width="${thick}" stroke-dasharray="0 ${C}" stroke-dashoffset="${-off}"
        data-da="${len} ${C-len}" transform="rotate(-90 ${size/2} ${size/2})" stroke-linecap="butt"/>`;
      off += len; return el2;
    }).join('');
    el.innerHTML = `<svg class="donut" width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">
      <circle cx="${size/2}" cy="${size/2}" r="${r}" fill="none" stroke="var(--blue-050)" stroke-width="${thick}"/>
      ${parts}
      ${center?`<text x="${size/2}" y="${size/2+1}" text-anchor="middle" dominant-baseline="middle"
        font-family="var(--mono)" font-size="19" font-weight="650" fill="var(--ink)">${center}</text>`:''}
    </svg>`;
    const io = new IntersectionObserver(es => es.forEach(e=>{
      if(!e.isIntersecting) return;
      el.querySelectorAll('circle[data-da]').forEach((c,i)=>
        setTimeout(()=>c.setAttribute('stroke-dasharray', c.dataset.da), 90*i));
      io.disconnect();
    }),{threshold:.3});
    io.observe(el);
  }

  /* ---- sparkline / area ---- */
  function spark(vals, {w=72,h=22,c='var(--blue-500)',fill=false}={}){
    const lo=Math.min(...vals), hi=Math.max(...vals), sp=hi-lo||1;
    const pt=(v,i)=>[(i/(vals.length-1)*w).toFixed(1),(h-((v-lo)/sp)*(h-3)-1.5).toFixed(1)];
    const d='M'+vals.map(pt).map(p=>p.join(',')).join('L');
    const area=fill?`<path d="${d}L${w},${h}L0,${h}Z" fill="${c}" opacity=".13"/>`:'';
    return `<svg width="${w}" height="${h}" viewBox="0 0 ${w} ${h}">${area}
      <path d="${d}" fill="none" stroke="${c}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
  }

  /* ---- line chart with axes ---- */
  function line(el, series, {w=680,h=210,labels=[],zero=true}={}){
    const pad={l:42,r:12,t:12,b:26};
    // zero:true anchors the axis at 0 (honest for rates near zero); zero:false
    // fits the axis to the data with a small margin, so movement in a high, narrow
    // band (e.g. utilisation in the 80s-90s) is legible rather than a flat line.
    const all=series.flatMap(s=>s.v);
    let lo, hi;
    if (zero) { lo=Math.min(...all,0); hi=Math.max(...all); }
    else { const mn=Math.min(...all), mx=Math.max(...all), m=(mx-mn)*0.15||1; lo=mn-m; hi=mx+m; }
    const X=i=>pad.l+i/(series[0].v.length-1)*(w-pad.l-pad.r);
    const Y=v=>h-pad.b-((v-lo)/((hi-lo)||1))*(h-pad.t-pad.b);
    // Compact tick labels so large values (hundreds of thousands) fit the axis
    // gutter instead of being clipped.
    const tick=v=>{const a=Math.abs(v);
      return a>=1e6?(v/1e6).toFixed(a<1e7?1:0)+'m'
           : a>=1e3?Math.round(v/1e3)+'k'
           : Math.round(v).toLocaleString('en-GB');};
    const ticks=4, grid=Array.from({length:ticks+1},(_,i)=>{
      const v=lo+(hi-lo)*i/ticks, y=Y(v);
      return `<line x1="${pad.l}" x2="${w-pad.r}" y1="${y}" y2="${y}" stroke="var(--line)" stroke-width="1"/>
      <text x="${pad.l-7}" y="${y+3.5}" text-anchor="end" font-size="9.5" font-family="var(--mono)" fill="var(--ink-3)">${tick(v)}</text>`;
    }).join('');
    const paths=series.map((s,si)=>{
      const d='M'+s.v.map((v,i)=>`${X(i).toFixed(1)},${Y(v).toFixed(1)}`).join('L');
      const L=1400;
      return `<path d="${d}" fill="none" stroke="${s.c}" stroke-width="2.1" stroke-linejoin="round"
        stroke-linecap="round" stroke-dasharray="${L}" stroke-dashoffset="${L}" data-draw="${si}">
        <animate attributeName="stroke-dashoffset" from="${L}" to="0" dur="1.3s" begin="${si*.18}s" fill="freeze"
          calcMode="spline" keySplines="0.16 1 0.3 1" keyTimes="0;1"/></path>`
        + s.v.map((v,i)=>`<circle cx="${X(i).toFixed(1)}" cy="${Y(v).toFixed(1)}" r="2.6" fill="${s.c}"
          opacity="0"><animate attributeName="opacity" to="1" dur=".3s" begin="${si*.18+1+i*.03}s" fill="freeze"/></circle>`).join('');
    }).join('');
    const xl=labels.map((t,i)=>`<text x="${X(i).toFixed(1)}" y="${h-8}" text-anchor="middle"
      font-size="9.5" font-family="var(--mono)" fill="var(--ink-3)">${t}</text>`).join('');
    el.innerHTML=`<svg viewBox="0 0 ${w} ${h}" style="width:100%;height:auto">${grid}${paths}${xl}</svg>`;
  }

  /* ---- compact data previews for cards. One dispatcher, so every card
         speaks the same visual language. Each returns an inline SVG/HTML string. */
  function preview(spec){
    if (!spec) return '';
    const n = v => Number(v).toLocaleString('en-GB');
    if (spec.kind === 'gauge'){
      const p = Math.max(0, Math.min(100, spec.pct||0));
      const tone = p>95?'var(--hot)':p>88?'var(--warm,#9A6300)':'var(--cool)';
      return `<div class="pv"><div class="pv__gauge">
        <div class="pv__gaugefill" style="width:${p}%;background:${tone}"></div>
        <span class="pv__gaugemark" style="left:100%"></span></div>
        <div class="pv__cap">${spec.caption||''}</div></div>`;
    }
    if (spec.kind === 'compare'){
      const {a,b,unit=''} = spec; const hi=Math.max(a.v,b.v)||1;
      const bar=(x,c)=>`<div class="pv__cmprow"><span class="pv__cmpl">${x.label}</span>
        <span class="pv__cmpt"><i style="width:${Math.max(2,x.v/hi*100)}%;background:${c}"></i></span>
        <span class="pv__cmpv">${n(x.v)}${unit}</span></div>`;
      return `<div class="pv">${bar(a,'var(--uk-blue)')}${bar(b,'var(--ink-3)')}
        <div class="pv__cap">${spec.caption||''}</div></div>`;
    }
    if (spec.kind === 'bars'){
      const rows=(spec.rows||[]).filter(r=>r.v!=null);
      const hi=Math.max(...rows.map(r=>r.v),1);
      const f=spec.fmt||n;
      return `<div class="pv">${rows.map(r=>`<div class="pv__brow">
        <span class="pv__bl" title="${r.n}">${String(r.n).replace('BRAND ','')}</span>
        <span class="pv__bt"><i style="width:${Math.max(2,r.v/hi*100)}%"></i></span>
        <span class="pv__bv">${f(r.v)}</span></div>`).join('')}
        <div class="pv__cap">${spec.caption||''}</div></div>`;
    }
    if (spec.kind === 'line'){
      const v=spec.series||[]; if(v.length<2) return '';
      const lo=Math.min(...v), hi=Math.max(...v), sp=hi-lo||1, W=240,H=54;
      const pt=(x,i)=>[(i/(v.length-1)*W).toFixed(1),(H-6-((x-lo)/sp)*(H-14)).toFixed(1)];
      const d=v.map(pt).map(p=>p.join(',')).join(' L');
      return `<div class="pv"><svg viewBox="0 0 ${W} ${H}" class="pv__line" preserveAspectRatio="none">
        <path d="M${d}" fill="none" stroke="var(--uk-blue)" stroke-width="2" vector-effect="non-scaling-stroke"/>
        ${v.map((x,i)=>{const[px,py]=pt(x,i);return `<circle cx="${px}" cy="${py}" r="2" fill="var(--uk-blue)"/>`}).join('')}
        </svg><div class="pv__cap">${spec.caption||''}</div></div>`;
    }
    if (spec.kind === 'note'){
      return `<div class="pv"><div class="pv__note">${spec.text||''}</div></div>`;
    }
    return '';
  }

  /* ---- freshness: turn a cadence + last-fetch into a status a person reads ---- */
  function freshness(cadence, fetchedAt){
    if (!fetchedAt) return {state:'unknown', label:'provenance pending'};
    const days=(Date.now()-new Date(String(fetchedAt).replace(' ','T')).getTime())/864e5;
    const cad=(cadence||'').toLowerCase();
    const window = cad.includes('realtime')||cad.includes('daily')?7
      : cad.includes('week')?21 : cad.includes('month')?60
      : cad.includes('quarter')?140 : 500;
    const ago = days<1?'today' : days<2?'yesterday'
      : days<31?Math.round(days)+' days ago' : Math.round(days/30)+' months ago';
    return {state: days<=window?'current':'stale', label:'updated '+ago, cadence};
  }

  /* ---- data journey: the pipeline, made clickable ----
     Six stages from a publisher's file to the number on the page. Clicking a
     stage expands what happens there, with the platform's real counts. This is
     the transparency piece: a visitor can see not just the number, but how it
     was arrived at. */
  function journey(mount, p, opts){
    opts = opts || {};
    const n = v => Number(v||0).toLocaleString('en-GB');
    const gb = b => b>=1e9 ? (b/1e9).toFixed(1)+' GB' : Math.round(b/1e6)+' MB';
    const stages = [
      {k:'source', ico:'\u{1F3DB}', name:'Source',
       one: p.source ? `${p.source.sources} published sources` : 'published sources',
       detail:'Government and regulator data anyone can download. No source is used unless it can be retrieved with no account, key or fee.',
       stat: p.source ? `${p.source.sources} sources · ${p.source.publishers} publishers · ${p.source.blocked} refused because they need a login` : ''},
      {k:'collect', ico:'\u{2B07}', name:'Collect',
       one: p.collect ? `${gb(p.collect.downloaded_bytes)} fetched` : 'fetched anonymously',
       // Built from the registry: only sources fetched through it are hashed.
       detail:(() => {
         const rows = (typeof Platform !== 'undefined' && Platform.sourceSummary().rows) || [];
         const held = rows.filter(r => r.provenance !== 'absent'), hashed = held.filter(r => r.sha256).length;
         const tail = ' A source that starts failing shows as failing rather than quietly going stale.';
         if (!held.length || hashed === held.length) return 'Each file is downloaded without credentials, its content hashed, and its HTTP status recorded.' + tail;
         return `Each file fetched through the registry is downloaded without credentials, its content hashed and its HTTP status recorded — ${hashed} of the ${held.length} sources holding data. The other ${held.length - hashed} arrived by bulk import and carry no recorded hash.` + tail;
       })(),
       stat: p.collect ? `${gb(p.collect.downloaded_bytes)} across ${p.collect.runs} recorded fetches` : ''},
      {k:'process', ico:'\u{2699}', name:'Process',
       one: p.process ? `${n(p.process.properties)} places, ${n(p.process.companies)} companies` : 'resolved to place and entity',
       detail:'The two missing joins are built here. Every record is matched to a place (a property or postcode) and, where relevant, to an organisation (a company or charity). This is what government data lacks.',
       stat: p.process ? `${n(p.process.properties)} properties · ${n(p.process.crosswalks)} identifier links · ${n(p.process.companies)} companies · ${n(p.process.ownership)} ownership records` : ''},
      {k:'validate', ico:'\u{2713}', name:'Validate',
       one: p.validate ? `${p.validate.gold_tables} checked outputs` : 'coverage attached',
       detail:'Every figure ships with the share of records it was computed over, and every match carries a confidence. Nothing merges silently; anything ambiguous is reported, not guessed.',
       stat: p.validate ? `${p.validate.gold_tables} published tables, each carrying its own coverage` : ''},
      {k:'groundtruth', ico:'\u{25C9}', name:'UK GroundTruth',
       one: p.groundtruth ? `${p.groundtruth.systems} systems` : 'thirteen systems',
       detail:'The joined data answers thirteen questions nobody can currently answer — school places, flood defences, procurement ownership, and more.',
       stat: p.groundtruth ? `${p.groundtruth.systems} systems, all on the same two joins` : ''},
      {k:'public', ico:'\u{1F310}', name:'Public',
       one: 'the number you see',
       detail:'Published as open figures on this page. Nothing is estimated or modelled — every number is computed from the sources above and can be traced back to them.',
       stat: p.public && p.public.generated ? 'last computed '+String(p.public.generated).replace('T',' ').replace('+00:00',' UTC') : ''},
    ];
    // Per-system scoping: when opened from a system, every stage can be
    // overridden with that system's own content, keyed by stage id
    // ({source,collect,process,validate,groundtruth,public}). Each override may
    // set one/detail/stat; anything omitted keeps the platform-level default.
    // Applied before render so the step labels and the panels agree.
    if (opts.over){
      stages.forEach(st=>{
        const o = opts.over[st.k];
        if (!o) return;
        if (o.one    != null) st.one    = o.one;
        if (o.detail != null) st.detail = o.detail;
        if (o.stat   != null) st.stat   = o.stat;
      });
    }
    const steps = stages.map((st,i)=>`<button class="jn__step" data-i="${i}" ${i===0?'aria-expanded="true"':''}>
        <span class="jn__ico">${st.ico}</span>
        <span class="jn__name">${st.name}</span>
        <span class="jn__one">${st.one}</span>
      </button>${i<stages.length-1?'<span class="jn__arrow">\u2192</span>':''}`).join('');
    mount.innerHTML = `<div class="jn__track">${steps}</div><div class="jn__panel" id="${mount.id}-panel"></div>`;
    const panel = mount.querySelector('.jn__panel');
    const show = i => {
      const st = stages[i];
      mount.querySelectorAll('.jn__step').forEach((b,j)=>b.classList.toggle('is-on',j===i));
      panel.innerHTML = `<div class="jn__pnl">
        <div class="jn__pnlhd"><span class="jn__ico">${st.ico}</span>
          <span class="jn__pnlname">${i+1}. ${st.name}</span></div>
        <p class="jn__pnltext">${st.detail}</p>
        ${st.stat?`<div class="jn__pnlstat">${st.stat}</div>`:''}</div>`;
    };
    mount.querySelectorAll('.jn__step').forEach(b=>b.addEventListener('click',()=>show(+b.dataset.i)));
    show(0);
  }

  /* ---- theme ---- */
  function theme(){
    const K='gt-theme';
    const set=t=>{document.documentElement.dataset.theme=t;localStorage.setItem(K,t);};
    const cur=localStorage.getItem(K); if(cur) set(cur);
    document.querySelectorAll('[data-theme-toggle]').forEach(b=>b.addEventListener('click',()=>
      set(document.documentElement.dataset.theme==='dark'?'light':'dark')));
  }

  /* ---- misc ---- */
  function sidebar(){
    document.querySelectorAll('[data-side-toggle]').forEach(b=>b.addEventListener('click',()=>
      document.querySelector('.side')?.classList.toggle('open')));
  }
  function meters(root=document){
    const io=new IntersectionObserver(es=>es.forEach(e=>{
      if(!e.isIntersecting)return;
      const i=e.target.querySelector('i'); if(i) i.style.width=i.dataset.w+'%';
      io.unobserve(e.target);
    }),{threshold:.4});
    root.querySelectorAll('.meter').forEach(m=>io.observe(m));
  }
  function boot(){ theme(); sidebar(); reveal(); countAll(); meters(); }

  return {fmt,pct,money,count,countAll,reveal,choropleth,bars,donut,spark,line,boot,meters,ramp,preview,freshness,journey};
})();
document.addEventListener('DOMContentLoaded', GT.boot);
