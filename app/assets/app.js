/* Groundtruth prototype runtime. No dependencies: charts, maps and counters
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
  function count(el, to, opts={}){
    const dur = opts.dur || 1100, dec = opts.dec || 0, pre = opts.pre || '', suf = opts.suf || '';
    if (matchMedia('(prefers-reduced-motion: reduce)').matches){
      el.textContent = pre + to.toLocaleString('en-GB',{minimumFractionDigits:dec,maximumFractionDigits:dec}) + suf; return;
    }
    const t0 = performance.now();
    const tick = t => {
      const k = Math.min((t - t0)/dur, 1), e = 1 - Math.pow(1 - k, 3), v = to * e;
      el.textContent = pre + v.toLocaleString('en-GB',{minimumFractionDigits:dec,maximumFractionDigits:dec}) + suf;
      if (k < 1) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  }
  function countAll(root=document){
    const io = new IntersectionObserver(es => es.forEach(e => {
      if (!e.isIntersecting) return;
      const el = e.target;
      count(el, parseFloat(el.dataset.count),
        {dec:+(el.dataset.dec||0), pre:el.dataset.pre||'', suf:el.dataset.suf||''});
      io.unobserve(el);
    }), {threshold:.4});
    root.querySelectorAll('[data-count]').forEach(el => io.observe(el));
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

  async function choropleth(el, {values={}, label='', fallbackSpread=false,
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
    function setMetric({values:vals={}, label:lbl='', ramp:rk='blue', animate=true}={}){
      current = {values:vals, label:lbl, rampKey:rk};
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
        tip.innerHTML = `<b>${p.dataset.n}</b><span>${v !== '' && v != null
          ? current.label.replace('{}', (+v).toLocaleString('en-GB'))
          : 'no value published here'}</span>`;
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

    setMetric({values, label, ramp:rampKey, animate:false});
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
  function line(el, series, {w=680,h=210,labels=[]}={}){
    const pad={l:42,r:12,t:12,b:26};
    const all=series.flatMap(s=>s.v); const lo=Math.min(...all,0), hi=Math.max(...all);
    const X=i=>pad.l+i/(series[0].v.length-1)*(w-pad.l-pad.r);
    const Y=v=>h-pad.b-((v-lo)/((hi-lo)||1))*(h-pad.t-pad.b);
    const ticks=4, grid=Array.from({length:ticks+1},(_,i)=>{
      const v=lo+(hi-lo)*i/ticks, y=Y(v);
      return `<line x1="${pad.l}" x2="${w-pad.r}" y1="${y}" y2="${y}" stroke="var(--line)" stroke-width="1"/>
      <text x="${pad.l-7}" y="${y+3.5}" text-anchor="end" font-size="9.5" font-family="var(--mono)" fill="var(--ink-3)">${Math.round(v).toLocaleString('en-GB')}</text>`;
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

  return {fmt,pct,money,count,countAll,reveal,choropleth,bars,donut,spark,line,boot,meters,ramp};
})();
document.addEventListener('DOMContentLoaded', GT.boot);
