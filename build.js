// Static site generator. Run: node build.js
import { writeFileSync, mkdirSync } from 'node:fs';
import A from './data/systems-a.js';
import B from './data/systems-b.js';
import C from './data/systems-c.js';
import P from './data/platform.js';
import CHAINS from './data/chains.js';
import EX from './data/examples.js';

// The thirteen Groundtruth systems: every source fetchable anonymously, no account, no key, no application.
const DELIVERABLE = ['catchment', 'sentinel', 'highwater', 'plumbline', 'junction', 'ledger', 'bellwether', 'sightline', 'lastmile', 'bulwark', 'watchman', 'compass', 'baseline'];
const sysById = Object.fromEntries([...A, ...B, ...C].map(s => [s.id, s]));

const SYSTEMS = [...A, ...B, ...C];
const YEAR = '2026';
const esc = s => String(s).replace(/&(?![a-zA-Z#][a-zA-Z0-9]*;)/g, '&amp;');

const THEMES = {
  fraud: 'Fraud &amp; integrity', central: 'Central government', local: 'Local government',
  money: 'Public money', housing: 'Housing', children: 'Children &amp; families',
  climate: 'Climate &amp; energy', transport: 'Transport', operations: 'Operations', equity: 'Equity'
};

const head = (title, desc, depth = 0) => {
  const p = depth ? '../' : '';
  return `<!doctype html>
<html lang="en-GB">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${title}</title>
<meta name="description" content="${desc}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;450;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&family=Newsreader:opsz,wght@6..72,400;6..72,500;6..72,600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="${p}assets/style.css">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><rect width='100' height='100' rx='22' fill='%231D4ED8'/><text y='68' x='50' text-anchor='middle' font-size='52' font-family='monospace' font-weight='700' fill='white'>G</text></svg>">
</head>
<body>`;
};

const nav = (depth = 0) => {
  const p = depth ? '../' : '';
  return `<nav class="nav"><div class="wrap nav__inner">
<a class="brand" href="${p}index.html"><span class="brand__mark">G</span>Groundtruth<span class="brand__sub">by Dexter DCL</span></a>
<div class="nav__links">
<a class="hide-sm" href="${p}index.html#thesis">The problem</a>
<a class="hide-sm" href="${p}index.html#systems">Systems</a>
<a class="hide-sm" href="${p}index.html#chains">How they help each other</a>
<a href="${p}examples.html">Problems &amp; solutions</a>
<a href="${p}app/index.html">Prototype</a>
<a class="hide-sm" href="${p}index.html#overall">Why one platform</a>
<a href="${p}platform.html">Architecture</a>
<button class="themetoggle" aria-label="Toggle theme"></button>
</div></div></nav>`;
};

const foot = (depth = 0) => {
  const p = depth ? '../' : '';
  return `<footer class="foot"><div class="wrap">
<div class="foot__grid">
<div>
<h4>Groundtruth systems</h4>
${DELIVERABLE.slice(0, 7).map(id => sysById[id]).map(s => `<a href="${p}systems/${s.id}.html">${s.num} &middot; ${s.name}</a>`).join('\n')}
</div>
<div>
<h4>&nbsp;</h4>
${DELIVERABLE.slice(7).map(id => sysById[id]).map(s => `<a href="${p}systems/${s.id}.html">${s.num} &middot; ${s.name}</a>`).join('\n')}
</div>
<div>
<h4>Sections</h4>
<a href="${p}index.html#chains">How they help each other</a>
<a href="${p}index.html#sequence">Build order</a>
<a href="${p}index.html#delivery">Delivery and procurement</a>
<a href="${p}index.html#rejected">Out of scope</a>
</div>
<div>
<h4>About</h4>
<p class="small muted">Prepared by Dexter DCL, an independent UK company. This is a private proposal document. It is not a government publication and carries no government endorsement.</p>
</div>
</div>
<div class="foot__bottom">
<span>&copy; <span data-year>${YEAR}</span> Dexter DCL Limited. Research compiled August ${YEAR}.</span>
<span>Contains public sector information licensed under the Open Government Licence v3.0.</span>
</div>
</div></footer>
<script src="${p}assets/app.js"></script>
</body></html>`;
};

/* ---------------- Detail pages ---------------- */
function detailPage(s, i) {
  const prev = SYSTEMS[(i - 1 + SYSTEMS.length) % SYSTEMS.length];
  const next = SYSTEMS[(i + 1) % SYSTEMS.length];

  const toc = [
    ['problem', 'The problem'], ['solution', 'The system'], ['examples', 'Worked examples'], ['data', 'Data foundation'],
    ['features', 'Capabilities'], ['benefits', 'Benefits'], ['delivery', 'Delivery'],
    ['risks', 'Risks &amp; mitigations'], ['sources', 'Sources']
  ];

  return `${head(`${s.name} — Dexter DCL`, esc(s.tagline).slice(0, 180), 1)}
${nav(1)}
<header class="sysHead"><div class="wrap">
<a class="backlink" href="../index.html">&larr; Groundtruth</a>
<div class="eyebrow">System ${s.num} &middot; ${s.status}</div>
<h1 class="display" style="font-size:clamp(2.2rem,5vw,3.6rem);margin-top:1rem">${s.name}</h1>
<p class="lede" style="margin-top:.6rem">${esc(s.subtitle)}</p>
<p class="prose" style="margin-top:1.4rem;font-size:1.05rem">${esc(s.tagline)}</p>
<div class="flexrow mt-3">${s.themes.map(t => `<span class="tag tag--accent">${THEMES[t] || t}</span>`).join('')}</div>
</div></header>

<div class="wrap section">
<div class="sysLayout">
<main>

<section id="problem">
<div class="eyebrow">The problem</div>
<div class="prose mt-2">${s.problem.map(p => `<p>${esc(p)}</p>`).join('\n')}</div>
<div class="impact mt-4">${s.impact.map(([n, l]) => `<div class="impact__cell"><div class="impact__n">${esc(n)}</div><div class="impact__l">${esc(l)}</div></div>`).join('')}</div>
</section>

<hr class="hr">

<section id="solution">
<div class="eyebrow">The system</div>
<div class="prose mt-2">${s.solution.map(p => `<p>${esc(p)}</p>`).join('\n')}</div>
</section>

${EX.bySystem[s.id] ? `<hr class="hr">

<section id="examples">
<div class="eyebrow">Worked examples</div>
<h3 class="mt-2">Two situations this system answers</h3>
<div class="grid grid--2 mt-4">
${EX.bySystem[s.id].map((e, n) => `<div class="card">
<div class="card__num">EXAMPLE ${n + 1}</div>
<div class="mt-3"><div class="feat__t" style="color:var(--hot)">The problem</div>
<p class="card__desc mt-1" style="flex:none">${esc(e.problem)}</p></div>
<div class="mt-3"><div class="feat__t" style="color:var(--cool)">What ${s.name} does</div>
<p class="card__desc mt-1" style="flex:none">${esc(e.solution)}</p></div>
</div>`).join('\n')}
</div>
</section>` : ''}

<hr class="hr">

<section id="data">
<div class="eyebrow">Data foundation</div>
<h3 class="mt-2">Every dataset below is open, or its access constraint is stated</h3>
<div class="tablewrap mt-3">
<table><thead><tr><th>Dataset</th><th>Publisher</th><th>What it provides</th></tr></thead>
<tbody>${s.datasets.map(([d, p, w]) => `<tr><td><strong>${esc(d)}</strong></td><td class="muted">${esc(p)}</td><td>${esc(w)}</td></tr>`).join('')}</tbody></table>
</div>
</section>

<hr class="hr">

<section id="features">
<div class="eyebrow">Capabilities</div>
<div class="feat mt-3">${s.features.map(([t, d], n) => `<div class="feat__item"><div class="feat__ico">${String(n + 1).padStart(2, '0')}</div><div><div class="feat__t">${esc(t)}</div><div class="feat__d">${esc(d)}</div></div></div>`).join('')}</div>
</section>

<hr class="hr">

<section id="benefits">
<div class="eyebrow">Benefits</div>
<div class="grid grid--2 mt-3">
<div class="card"><h4>For government</h4><ul class="prose small mt-2" style="max-width:none">${s.benefits.government.map(b => `<li>${esc(b)}</li>`).join('')}</ul></div>
<div class="card"><h4>For the public</h4><ul class="prose small mt-2" style="max-width:none">${s.benefits.public.map(b => `<li>${esc(b)}</li>`).join('')}</ul></div>
</div>
</section>

<hr class="hr">

<section id="delivery">
<div class="eyebrow">Delivery</div>
<div class="specrow mt-3"><div class="specrow__k">Likely sponsor</div><div class="specrow__v">${esc(s.buyer)}</div></div>
<div class="specrow"><div class="specrow__k">Procurement route</div><div class="specrow__v">${esc(s.route)}</div></div>
<h3 class="mt-4 mb-3">Phasing</h3>
<div class="phases">${s.phases.map(([t, d, x], n) => `<div class="phase"><div class="phase__n">${n + 1}</div><div><div class="phase__t">${esc(t)}</div><div class="phase__meta">${esc(d)}</div><div class="phase__d">${esc(x)}</div></div></div>`).join('')}</div>
</section>

<hr class="hr">

<section id="risks">
<div class="eyebrow">Risks &amp; mitigations</div>
<div class="grid mt-3">${s.risks.map(([t, d]) => `<div class="card"><div class="card__title" style="font-size:1rem;margin:0">${esc(t)}</div><p class="card__desc">${esc(d)}</p></div>`).join('')}</div>
</section>

<hr class="hr">

<section id="sources">
<div class="eyebrow">Sources</div>
<div class="srcs mt-3">${s.sources.map(([t, u], n) => `<div class="src"><span class="src__n">${String(n + 1).padStart(2, '0')}</span><span><a href="${u}" target="_blank" rel="noopener">${esc(t)}</a></span></div>`).join('')}</div>
<p class="tiny muted mt-3">All sources checked in August ${YEAR}. Figures carry the reference period of their source, which may differ from publication date. Where a figure could not be verified against a primary source it is not used.</p>
</section>

<hr class="hr">
<div class="flexrow" style="justify-content:space-between">
<a class="btn btn--ghost" href="../systems/${prev.id}.html">&larr; ${prev.num} ${prev.name}</a>
<a class="btn btn--ghost" href="../systems/${next.id}.html">${next.num} ${next.name} &rarr;</a>
</div>

</main>
<aside class="sysLayout__aside">
<div class="toc"><div class="toc__title">On this page</div>
${toc.map(([id, l]) => `<a href="#${id}">${l}</a>`).join('\n')}
</div>
</aside>
</div>
</div>
${foot(1)}`;
}

/* ---------------- Index ---------------- */
const allThemes = [...new Set(SYSTEMS.flatMap(s => s.themes))];

const cards = SYSTEMS.map(s => `<a class="card" href="systems/${s.id}.html" data-themes="${s.themes.join(' ')}">
<div class="card__num">SYSTEM ${s.num}</div>
<div class="card__title">${s.name}</div>
<div class="card__desc"><strong>${esc(s.subtitle)}.</strong> ${esc(s.tagline)}</div>
<div class="card__foot">${s.themes.map(t => `<span class="tag">${THEMES[t] || t}</span>`).join('')}</div>
</a>`).join('\n');

const OUT = ['transit', 'threshold', 'waypoint', 'hearth', 'freehold'];
const GT = DELIVERABLE.map(id => sysById[id]);
const OUTS = OUT.map(id => sysById[id]);

const index = `${head('Groundtruth — one platform, thirteen public data systems',
  'Groundtruth resolves places and organisations across UK government data. Thirteen systems run on it, every one using data anyone can download without an account.')}
${nav()}

<header class="hero">
<div class="hero__grid"></div>
<div class="wrap">
<div class="eyebrow">Dexter DCL</div>
<h1 class="display hero__title mt-3">Groundtruth</h1>
<p class="lede hero__lede">Government keeps good records of <em>what</em> happened. It very often fails to record <em>where</em> it happened, or <em>which organisation</em> was involved &mdash; at least not in a form a computer can match up.<br><br>That one gap makes thirteen genuinely useful things impossible. Groundtruth closes it.</p>
<div class="hero__cta">
<a class="btn btn--primary" href="#systems">The thirteen systems</a>
<a class="btn btn--ghost" href="#chains">How they help each other</a>
</div>
</div>
</header>

<div class="wrap">
<div class="statband">
<div class="stat"><div class="stat__num">13</div><div class="stat__label">Systems it makes possible</div></div>
<div class="stat"><div class="stat__num">2</div><div class="stat__label">Missing links it fixes: where, and who</div></div>
<div class="stat"><div class="stat__num">0</div><div class="stat__label">Sign-ups, keys or permissions needed</div></div>
<div class="stat"><div class="stat__num">£0</div><div class="stat__label">Cost of the data. All of it is free</div></div>
</div>
</div>

<section class="section" id="thesis">
<div class="wrap wrap--narrow">
<div class="eyebrow">The problem</div>
<h2 class="mt-3">What is actually broken</h2>
<div class="prose mt-4">
<p>Imagine a hospital where every file has a patient&rsquo;s name but no date of birth and no NHS number. You have three files for &ldquo;John Smith&rdquo;. One person, or three? The files are real. They are simply useless for anything that needs joining up.</p>
<p>That is the state of a lot of UK government data. Four real examples:</p>
</div>

<div class="feat mt-4">
<div class="feat__item"><div class="feat__ico">1</div><div>
<div class="feat__t">The flood people don&rsquo;t know where</div>
<div class="feat__d">The Environment Agency has objected to <strong>23,336</strong> building plans on flood risk grounds. The list has no address, no postcode and no map point. It cannot map its own objections &mdash; and for <strong>7,011</strong> of them it never found out what the council decided.</div></div></div>

<div class="feat__item"><div class="feat__ico">2</div><div>
<div class="feat__t">A ministry can&rsquo;t say which sites</div>
<div class="feat__d">Housebuilders owe councils <strong>£1,491,818,575</strong> for schools, roads and affordable homes. The government&rsquo;s own database records every penny &mdash; and not one location. The field for the property reference is filled in on <strong>0.0%</strong> of records. The address field, in the same records, is filled in on <strong>98.1%</strong>.</div></div></div>

<div class="feat__item"><div class="feat__ico">3</div><div>
<div class="feat__t">Councils get maps they can&rsquo;t read</div>
<div class="feat__d">School places are planned across <strong>3,651</strong> local areas. The boundaries of those areas are published nowhere, so councils receive data for a geography they cannot draw &mdash; while <strong>£1.096bn</strong> of school building money is handed out on it.</div></div></div>

<div class="feat__item"><div class="feat__ico">4</div><div>
<div class="feat__t">Nobody knows who owns the flood defences</div>
<div class="feat__d">England has <strong>141,629</strong> recorded flood defences. The owner is listed as &ldquo;Unknown&rdquo; on <strong>73.7%</strong> of them. If one fails, nobody can say who was responsible for maintaining it.</div></div></div>
</div>

<div class="note mt-4">
<div class="note__title">Here is the point</div>
<p style="margin:0">None of those is a missing dataset. The data exists and is free. Each one is a <strong>missing link</strong> &mdash; and there are only two kinds.</p>
</div>

<div class="grid grid--2 mt-4">
<div class="card"><div class="card__num" style="color:var(--accent)">LINK ONE</div>
<h3 class="card__title">Where</h3>
<p class="card__desc mt-2">Turning a messy reference like <em>&ldquo;East Devon 21/0751/FUL&rdquo;</em> into a point on a map. Seven of the thirteen systems need this.</p></div>
<div class="card"><div class="card__num" style="color:var(--accent-2)">LINK TWO</div>
<h3 class="card__title">Who</h3>
<p class="card__desc mt-2">Turning a messy name like <em>&ldquo;SOFTCAT LTD - FCA&rdquo;</em> into one identified organisation. Five of the thirteen need this. One needs both.</p></div>
</div>

<div class="prose mt-4">
<p>Groundtruth builds those two links once, and gives them away. It is not clever &mdash; it is the same job the postcode did. Postcodes added no new information; they just gave everyone one shared way of saying <em>here</em>, and that unlocked everything from mail sorting to insurance.</p>
</div>
<div class="flexrow mt-4"><a class="btn btn--ghost" href="platform.html">The technical detail &rarr;</a></div>
</div>
</section>

<section class="section section--alt" id="systems">
<div class="wrap">
<div class="eyebrow">The platform</div>
<h2 class="mt-3">Thirteen systems</h2>
<p class="lede mt-3">Each one addresses a gap the responsible department has documented itself. Every dataset they depend on was tested and returns data to an anonymous request &mdash; no account, no API key, no application, no approval.</p>
<div class="filters mt-4">
<button class="filter is-on" data-filter="all">All thirteen</button>
${Object.entries(THEMES).map(([k, v]) => `<button class="filter" data-filter="${k}">${v}</button>`).join('')}
</div>
<p class="small muted mb-3" data-filter-count>13 systems</p>
<div class="grid">
${GT.map(s => `<a class="card" href="systems/${s.id}.html" data-themes="${s.themes.join(' ')}">
<div class="card__num">${s.num}</div>
<h3 class="card__title">${s.name}</h3>
<p class="card__desc">${esc(s.subtitle)}</p>
<div class="card__foot">${s.themes.map(t => `<span class="tag">${THEMES[t] || t}</span>`).join('')}</div>
</a>`).join('\n')}
</div>
</div>
</section>

<section class="section" id="chains">
<div class="wrap">
<div class="eyebrow">Compounding</div>
<h2 class="mt-3">How they help each other</h2>
<div class="prose mt-4">${CHAINS.intro.map(p => `<p>${esc(p)}</p>`).join('\n')}</div>
<div class="grid grid--2 mt-5">
${CHAINS.chains.map(c => `<div class="card">
<div class="card__num">${c.label}</div>
<h3 class="card__title">${esc(c.trigger)}</h3>
<div class="phases mt-3">
${c.steps.map((st, i) => `<div class="phase"><div class="phase__n">${i + 1}</div><div><div class="phase__t">${esc(st[0])}</div><div class="phase__d">${esc(st[1])}</div></div></div>`).join('\n')}
</div>
<div class="note mt-2"><div class="note__title">What that gives you</div>${esc(c.outcome)}</div>
</div>`).join('\n')}
</div>

<div class="wrap--narrow mt-5" style="margin-inline:auto">
<h3>And the work compounds backwards</h3>
<p class="prose mt-2">${esc(CHAINS.reuse.intro)}</p>
<div class="feat mt-4">
${CHAINS.reuse.items.map((r, i) => `<div class="feat__item"><div class="feat__ico">${String(i + 1).padStart(2, '0')}</div><div><div class="feat__t">${esc(r[0])}</div><div class="feat__d">${esc(r[1])}</div></div></div>`).join('')}
</div>
</div>
</div>
</section>

<section class="section section--ink" id="overall">
<div class="wrap wrap--narrow">
<div class="eyebrow">The whole point</div>
<h2 class="mt-3">${EX.overall.heading}</h2>
<div class="prose mt-4" style="color:#B4BAC6">${EX.overall.body.map(p => `<p>${esc(p)}</p>`).join('\n')}</div>
<p class="small mt-4" style="color:#8A91A0">There are twenty-six worked examples on the system pages &mdash; two each, every one a real situation somebody in government currently cannot get to the bottom of.</p>
</div>
</section>

<section class="section section--alt" id="sequence">
<div class="wrap wrap--narrow">
<div class="eyebrow">Sequence</div>
<h2 class="mt-3">What to build first</h2>
<p class="lede mt-3">The first move is unpaid on purpose. A company with no filed accounts does not win a departmental contract &mdash; it wins one after it has visibly fixed something.</p>
<div class="phases mt-5">
${P.sequence.map((s, i) => `<div class="phase">
<div class="phase__n">${i + 1}</div>
<div><div class="phase__t">${esc(s[0])}</div><div class="phase__meta">${esc(s[1])}</div><div class="phase__d">${esc(s[2])}</div></div>
</div>`).join('\n')}
</div>
</div>
</section>

<section class="section" id="delivery">
<div class="wrap">
<div class="eyebrow">Delivery</div>
<h2 class="mt-3">How government would buy it</h2>
<div class="prose mt-4">
<p><strong>Central digital spend controls ended on 1 April ${YEAR}.</strong> Departments are now accountable for applying the functional standards themselves, and assurance applies only above their own delegated authority limits. A pilot is a departmental decision rather than a central one.</p>
<p><strong>Framework entry reopens.</strong> The current digital outcomes framework was let as an open framework under the Procurement Act, with reopening cycles &mdash; so missing a window is no longer fatal. Product-shaped systems route through the cloud framework; delivery-shaped ones through digital outcomes; unproven research through the small business research initiative, where the department funds development and the supplier retains the intellectual property.</p>
<p><strong>Small supplier status is a scored advantage attached to a published target.</strong> Departments must set and publish three-year small business spend targets and report progress annually. They are collectively behind, and central government's small business share has fallen rather than risen.</p>
<h3>What makes a proposition land</h3>
<p>The counter-fraud programme is the template worth copying. Government published a loss estimate it owns, reported savings against it, credited data-matching explicitly, and translated the result into nurses and repaired roads. Every system here is framed the same way: against a published number the department already accepts, with recovered or avoided cost rather than capability uplift as the headline.</p>
<p>Two further things now count as compliance arguments rather than sales points. Open standards and data portability are required by the technology code of practice, and the central digital team for local government has named supplier lock-in and inconsistent interfaces as the problem it exists to solve. And there is a durable advantage in depending on nothing: <strong>every source these thirteen systems use is fetchable without an account, so there is no registration to revoke and no licence to terminate.</strong></p>
</div>
</div>
</section>

<section class="section section--alt" id="rejected">
<div class="wrap">
<div class="eyebrow">Out of scope</div>
<h2 class="mt-3">Five we left out, and why</h2>
<p class="lede mt-3">Researched, written up, and excluded &mdash; for three different reasons. They stay published because a rejected idea with a stated reason is worth more than a quiet deletion.</p>
<div class="grid mt-4">
${OUTS.map(s => `<a class="card" href="systems/${s.id}.html">
<div class="card__num">${s.num}</div>
<h3 class="card__title">${s.name}</h3>
<p class="card__desc">${esc(s.subtitle)}</p>
<div class="card__foot"><span class="tag tag--warm">${s.id === 'freehold' ? 'Needs a registered account' : (s.id === 'waypoint' || s.id === 'hearth') ? 'Rejected on merit' : 'Needs cleared UK staff'}</span></div>
</a>`).join('\n')}
</div>
<div class="note note--warn mt-4">
<div class="note__title">Why each is out</div>
<p style="margin:0"><strong>Transit and Threshold</strong> handle live social care records and placements for homeless children. They need a UK-resident, security-cleared operations tier. Year two, not never &mdash; and the largest money in the portfolio sits behind them. <strong>Freehold</strong> depends on ownership data that redirects to a sign-in under a licence with audit rights and a 48-hour delete clause. <strong>Waypoint and Hearth</strong> were killed by the research itself: government had already shipped a free replacement for one, and the other targets a market that is legally blocked and commercially served.</p>
</div>
</div>
</section>

<section class="section section--ink">
<div class="wrap wrap--narrow" style="text-align:center">
<div class="eyebrow" style="justify-content:center">Method</div>
<h2 class="mt-3">Fifteen published claims were corrected.</h2>
<p class="lede mt-3" style="margin-inline:auto;color:#B4BAC6">Research overturned our own findings repeatedly &mdash; a premise that was already solved, a market that was legally blocked, a linkage key that does not exist in the published data, a trend that vanished once the rate behind it was computed, and one figure derived and then presented as though a document had said it. Roughly half of what sounded solid needed correction once someone checked the primary source. Every system brief carries its sources for that reason.</p>
<div class="hero__cta" style="justify-content:center">
<a class="btn btn--primary" style="background:var(--paper);color:var(--ink)" href="systems/${GT[0].id}.html">Start with ${GT[0].name}</a>
<a class="btn btn--ghost" style="border-color:#3A414F;color:var(--paper)" href="platform.html">The architecture</a>
</div>
</div>
</section>

${foot()}`;

/* ---------------- Platform page ---------------- */
const platform = `${head(`${P.name} — the unified platform | Dexter DCL`,
  'Five open-data systems delivered as one platform, on a shared place and entity resolution layer.')}
${nav()}

<header class="hero">
<div class="hero__grid"></div>
<div class="wrap">
<div class="eyebrow">The unified platform</div>
<h1 class="display hero__title mt-3">${P.name} <em>resolves what<br>nothing else resolves.</em></h1>
<p class="lede hero__lede">${P.standfirst}</p>
<div class="hero__cta">
<a class="btn btn--primary" href="#spines">The two spines</a>
<a class="btn btn--ghost" href="#sequence">Build sequence</a>
</div>
</div>
</header>

<div class="wrap">
<div class="statband">
<div class="stat"><div class="stat__num">5</div><div class="stat__label">Products, delivered from one platform</div></div>
<div class="stat"><div class="stat__num">2</div><div class="stat__label">Missing links it fixes: where, and who</div></div>
<div class="stat"><div class="stat__num">3,651</div><div class="stat__label">Planning areas whose boundaries nobody publishes</div></div>
<div class="stat"><div class="stat__num">0</div><div class="stat__label">Personal data records any of the five touch</div></div>
</div>
</div>

<section class="section" id="thesis">
<div class="wrap wrap--narrow">
<div class="eyebrow">Why one platform</div>
<h2 class="mt-3">Five products that break in the same two places</h2>
<div class="prose mt-4">
${P.thesis.map(t => `<p>${t}</p>`).join('\n')}
</div>
</div>
</section>

<section class="section section--alt" id="spines">
<div class="wrap">
<div class="eyebrow">Architecture</div>
<h2 class="mt-3">The two spines</h2>
<div class="grid grid--2 mt-4">
${P.spines.map(sp => `<div class="card" id="${sp.id}">
<div class="card__num">${sp.name.toUpperCase()}</div>
<h3 class="card__title">${sp.role}</h3>
<p class="card__desc mt-2">${sp.problem}</p>
<div class="mt-3 feat">
${sp.builds.map((b, i) => `<div class="feat__item">
<div class="feat__ico">${i + 1}</div>
<div><div class="feat__t">${b[0]}</div><div class="feat__d">${b[1]}</div></div>
</div>`).join('\n')}
</div>
<div class="note note--warn mt-3">
<div class="note__title">Binding constraint</div>
${sp.constraint}
</div>
${sp.gotchas ? `<div class="mt-3">
<div class="note__title" style="color:var(--hot)">What the spine has to survive</div>
<ul class="small muted mt-2" style="padding-left:1.2em">
${sp.gotchas.map(g => `<li style="margin-top:.45em">${g}</li>`).join('\n')}
</ul>
</div>` : ''}
</div>`).join('\n')}
</div>
</div>
</section>

<section class="section">
<div class="wrap">
<div class="eyebrow">Dependency</div>
<h2 class="mt-3">Which product needs which spine</h2>
<p class="lede mt-3">Junction needs both, which is the useful test that this is a real architecture rather than a story told after the fact.</p>
<div class="tablewrap mt-4">
<table>
<thead><tr>${P.matrix.head.map(h => `<th>${h}</th>`).join('')}</tr></thead>
<tbody>
${P.matrix.rows.map(r => {
  const s = sysById[r[0].toLowerCase()];
  return `<tr>
<td><a href="systems/${s.id}.html" style="color:var(--accent);text-decoration:none;font-weight:600">${s.num} &middot; ${r[0]}</a></td>
<td>${r[1] ? '<span class="tag tag--accent">Place</span>' : '<span class="muted">&mdash;</span>'}</td>
<td>${r[2] ? '<span class="tag tag--cool">Entity</span>' : '<span class="muted">&mdash;</span>'}</td>
<td>${r[3]}</td>
</tr>`;
}).join('\n')}
</tbody>
</table>
</div>
</div>
</section>

<section class="section section--alt">
<div class="wrap">
<div class="eyebrow">Reality check</div>
<h2 class="mt-3">What is buildable, and what is not</h2>
<div class="grid grid--2 mt-4">
<div class="card">
<div class="card__num" style="color:var(--cool)">BUILDABLE TODAY</div>
<div class="mt-3 feat">
${P.buildable.now.map(b => `<div class="feat__item">
<div class="feat__ico" style="background:var(--cool-soft);color:var(--cool)">&check;</div>
<div><div class="feat__t">${b[0]}</div><div class="feat__d">${b[1]}</div></div>
</div>`).join('\n')}
</div>
</div>
<div class="card">
<div class="card__num" style="color:var(--hot)">GENUINELY BLOCKED</div>
<div class="mt-3 feat">
${P.buildable.blocked.map(b => `<div class="feat__item">
<div class="feat__ico" style="background:var(--hot-soft);color:var(--hot)">&times;</div>
<div><div class="feat__t">${b[0]}</div><div class="feat__d">${b[1]}</div></div>
</div>`).join('\n')}
</div>
</div>
</div>
</div>
</section>

<section class="section" id="sequence">
<div class="wrap wrap--narrow">
<div class="eyebrow">Sequence</div>
<h2 class="mt-3">Build order, and why</h2>
<p class="lede mt-3">The first move is unpaid on purpose. A company with no filed accounts does not win a departmental contract; it wins one after it has visibly fixed something.</p>
<div class="phases mt-5">
${P.sequence.map((s, i) => `<div class="phase">
<div class="phase__n">${i + 1}</div>
<div>
<div class="phase__t">${s[0]}</div>
<div class="phase__meta">${s[1]}</div>
<div class="phase__d">${s[2]}</div>
</div>
</div>`).join('\n')}
</div>
</div>
</section>

<section class="section section--ink">
<div class="wrap wrap--narrow">
<div class="eyebrow">Before anyone writes code</div>
<h2 class="mt-3">Three things that would sink this</h2>
<div class="prose mt-4" style="color:#B4BAC6">
${P.honesty.map(h => `<p>${h}</p>`).join('\n')}
</div>
</div>
</section>

${foot()}`;

/* ---------------- Write ---------------- */
mkdirSync('systems', { recursive: true });
const examples = `${head('Problems and solutions — all thirteen Groundtruth systems',
  'Two real situations for every one of the thirteen Groundtruth systems: what goes wrong today, and what the system does about it.')}
${nav()}

<header class="sysHead"><div class="wrap">
<a class="backlink" href="index.html">&larr; Groundtruth</a>
<div class="eyebrow">Problems &amp; solutions</div>
<h1 class="display" style="font-size:clamp(2.2rem,5vw,3.6rem);margin-top:1rem">Twenty-six situations</h1>
<p class="lede" style="margin-top:.6rem">Two for each of the thirteen systems. On the left, what goes wrong today. On the right, what the system does about it.</p>
<p class="prose" style="margin-top:1.4rem;font-size:1.05rem">Every situation below is real, and every one is caused by the same thing: a record exists, but nothing can be matched to it. No new data is collected anywhere on this page.</p>
</div></header>

<div class="wrap section">

<div class="eyebrow">Jump to a system</div>
<div class="grid grid--3 mt-3">
${GT.map((s, i) => `<a class="card" href="#${s.id}" style="padding:1rem 1.15rem">
<div class="card__num">${String(i + 1).padStart(2, '0')}</div>
<div class="feat__t mt-1">${s.name}</div>
<p class="card__desc mt-1" style="flex:none;font-size:.92rem">${esc(s.subtitle)}</p>
</a>`).join('\n')}
</div>

${GT.map((s, i) => EX.bySystem[s.id] ? `
<hr class="hr">

<section id="${s.id}">
<div class="eyebrow">${String(i + 1).padStart(2, '0')} &middot; ${s.themes.map(t => THEMES[t] || t).join(' &middot; ')}</div>
<h2 class="mt-2">${s.name}</h2>
<p class="lede" style="margin-top:.5rem;font-size:1.1rem">${esc(s.subtitle)}</p>

<div class="grid grid--2 mt-4">
${EX.bySystem[s.id].map((e, n) => `<div class="card">
<div class="card__num">SITUATION ${n + 1}</div>
<div class="mt-3"><div class="feat__t" style="color:var(--hot)">What goes wrong today</div>
<p class="card__desc mt-1" style="flex:none">${esc(e.problem)}</p></div>
<div class="mt-3"><div class="feat__t" style="color:var(--cool)">What ${s.name} does</div>
<p class="card__desc mt-1" style="flex:none">${esc(e.solution)}</p></div>
</div>`).join('\n')}
</div>

<p class="mt-3"><a class="backlink" href="systems/${s.id}.html">Full detail on ${s.name} &rarr;</a></p>
</section>` : '').join('\n')}

<hr class="hr">

<section id="overall">
<div class="eyebrow">The pattern</div>
<h2 class="mt-3">${EX.overall.heading}</h2>
<div class="prose mt-4">${EX.overall.body.map(p => `<p>${esc(p)}</p>`).join('\n')}</div>
<p class="mt-4"><a class="backlink" href="platform.html">How the platform is built &rarr;</a></p>
</section>

</div>
${foot()}`;

writeFileSync('index.html', index);
writeFileSync('platform.html', platform);
writeFileSync('examples.html', examples);
SYSTEMS.forEach((s, i) => writeFileSync(`systems/${s.id}.html`, detailPage(s, i)));
console.log(`Built index.html + ${SYSTEMS.length} system pages:`);
SYSTEMS.forEach(s => console.log(`  systems/${s.id}.html  ${s.num} ${s.name}`));
