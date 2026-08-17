// Static site generator. Run: node build.js
import { writeFileSync, mkdirSync } from 'node:fs';
import A from './data/systems-a.js';
import B from './data/systems-b.js';
import C from './data/systems-c.js';
import P from './data/platform.js';

// The twelve Groundtruth systems: every source fetchable anonymously, no account, no key, no application.
const DELIVERABLE = ['catchment', 'sentinel', 'highwater', 'plumbline', 'junction', 'ledger', 'bellwether', 'sightline', 'lastmile', 'bulwark', 'watchman', 'compass'];
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
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><rect width='100' height='100' rx='22' fill='%231D4ED8'/><text y='68' x='50' text-anchor='middle' font-size='52' font-family='monospace' font-weight='700' fill='white'>D</text></svg>">
</head>
<body>`;
};

const nav = (depth = 0) => {
  const p = depth ? '../' : '';
  return `<nav class="nav"><div class="wrap nav__inner">
<a class="brand" href="${p}index.html"><span class="brand__mark">D</span>Dexter DCL<span class="brand__sub">Open Data Systems</span></a>
<div class="nav__links">
<a class="hide-sm" href="${p}index.html#thesis">Thesis</a>
<a class="hide-sm" href="${p}index.html#systems">Systems</a>
<a href="${p}platform.html">Platform</a>
<a class="hide-sm" href="${p}index.html#method">Method</a>
<a class="hide-sm" href="${p}index.html#rejected">Rejected</a>
<button class="themetoggle" aria-label="Toggle theme"></button>
</div></div></nav>`;
};

const foot = (depth = 0) => {
  const p = depth ? '../' : '';
  return `<footer class="foot"><div class="wrap">
<div class="foot__grid">
<div>
<h4>Portfolio</h4>
${SYSTEMS.slice(0, 9).map(s => `<a href="${p}systems/${s.id}.html">${s.num} &middot; ${s.name}</a>`).join('\n')}
</div>
<div>
<h4>&nbsp;</h4>
${SYSTEMS.slice(9).map(s => `<a href="${p}systems/${s.id}.html">${s.num} &middot; ${s.name}</a>`).join('\n')}
</div>
<div>
<h4>Sections</h4>
<a href="${p}index.html#thesis">The thesis</a>
<a href="${p}index.html#method">How these were chosen</a>
<a href="${p}index.html#rejected">What we rejected</a>
<a href="${p}index.html#delivery">Delivery and procurement</a>
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
    ['problem', 'The problem'], ['solution', 'The system'], ['data', 'Data foundation'],
    ['features', 'Capabilities'], ['benefits', 'Benefits'], ['delivery', 'Delivery'],
    ['risks', 'Risks &amp; mitigations'], ['sources', 'Sources']
  ];

  return `${head(`${s.name} — Dexter DCL`, esc(s.tagline).slice(0, 180), 1)}
${nav(1)}
<header class="sysHead"><div class="wrap">
<a class="backlink" href="../index.html">&larr; All systems</a>
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

const index = `${head('Dexter DCL — Seventeen Open Data Systems for the United Kingdom', 'Seventeen systems built on free UK government data, each addressing a documented gap where government has published that it cannot answer its own question.')}
${nav()}

<header class="hero">
<div class="hero__grid"></div>
<div class="wrap">
<div class="eyebrow">Dexter DCL &middot; Public service data portfolio &middot; August ${YEAR}</div>
<h1 class="display hero__title">Seventeen systems the UK<br>government cannot<br>currently <em>build itself</em>.</h1>
<p class="lede hero__lede">Each one runs on free, openly licensed government data. Each one closes a gap that government has documented in its own words &mdash; in a National Audit Office report, a Public Accounts Committee finding, or a dataset that admits what it does not know.</p>
<div class="hero__cta">
<a class="btn btn--primary" href="#systems">See the systems</a>
<a class="btn btn--ghost" href="#method">How they were chosen</a>
</div>
</div>
</header>

<div class="wrap"><div class="statband">
<div class="stat"><div class="stat__num">10</div><div class="stat__label">Systems, each with a named sponsor and procurement route</div></div>
<div class="stat"><div class="stat__num">7,011</div><div class="stat__label">Flood objection outcomes the Environment Agency does not know</div></div>
<div class="stat"><div class="stat__num">3,651</div><div class="stat__label">Pupil planning areas whose boundaries are published nowhere</div></div>
<div class="stat"><div class="stat__num">0</div><div class="stat__label">Suppliers on the statutory debarment list, 21 months in</div></div>
</div></div>

<section class="section" id="thesis">
<div class="wrap">
<div class="eyebrow">The thesis</div>
<h2 class="mt-3">Government publishes far better than it enforces, and measures far less than it publishes.</h2>
<div class="prose mt-4">
<p>The United Kingdom has some of the best open government data in the world. It also has a striking pattern of publishing data that nobody joins, retiring measures it still needs, and running multi-billion pound programmes on evidence it admits is incomplete.</p>
<p>This is not speculation. It is the government's own account of itself. The team that runs the national data portal wrote, in ${YEAR}, that:</p>
<div class="note mt-3 mb-3">
<div class="note__title">data.gov.uk product team, ${YEAR}</div>
<p style="margin:0">&ldquo;the original approach has failed and led to broken links and low usage&rdquo; &mdash; with more than a quarter of links leading to error pages, and many datasets last updated years ago.</p>
</div>
<p>The same pattern repeats across departments. The Public Accounts Committee found that the Department for Education <strong>&ldquo;does not know whether home to school transport is achieving value for money&rdquo;</strong> &mdash; a £2.6bn annual spend. The National Audit Office found that the department <strong>&ldquo;does not know how many spaces are available in mainstream schools or other settings&rdquo;</strong> while councils carry billions in special educational needs deficits. The Environment Agency publishes a national dataset in which <strong>30% of the outcomes are recorded as unknown</strong>.</p>
<p>Every system in this portfolio starts from one of those admissions. Not from a technology looking for a use, and not from a dataset looking for a purpose &mdash; from a documented statement, by a public body, that it cannot answer a question it needs answered.</p>
<h3>Three structural facts shape all ten</h3>
<p><strong>The UK publishes aggregates, not events.</strong> Almost every domain has a good national statistical release and no open record of the underlying decisions, transactions or cases. The analytical value is almost always in the missing event layer.</p>
<p><strong>Address-level linkage is the recurring bottleneck.</strong> Unique property reference numbers exist and are free, but the datasets that would need joining &mdash; planning applications, spend transactions, placements, connection applications &mdash; either lack them or are not published at all.</p>
<p><strong>Official statistics are being withdrawn, not added.</strong> Journey time statistics were discontinued. The Office for Local Government was closed after seventeen months. The Competition and Markets Authority withdrew its cartel screening tool in 2020 and never replaced it. Discontinuation creates the clearest openings, because the user need survives the statistic.</p>
</div>
</div>
</section>

<section class="section section--alt" id="systems">
<div class="wrap">
<div class="eyebrow">The portfolio</div>
<h2 class="mt-3">Seventeen systems</h2>
<p class="lede mt-3">Filter by the part of government each one serves. Every system has a full brief covering the problem, the data, the capabilities, the delivery phasing, the risks and the sources.</p>
<div class="filters mt-4">
<button class="filter is-on" data-filter="all">All seventeen</button>
${allThemes.map(t => `<button class="filter" data-filter="${t}">${THEMES[t] || t}</button>`).join('\n')}
</div>
<p class="tiny muted mb-3" data-filter-count>10 systems</p>
<div class="grid">
${cards}
</div>
</div>
</section>

<section class="section" id="method">
<div class="wrap">
<div class="eyebrow">Method</div>
<h2 class="mt-3">How these ten were chosen &mdash; and why several obvious ideas are missing</h2>
<div class="prose mt-4">
<p>The portfolio was assembled by parallel research across the UK open data estate, current government priorities, existing civic technology, and ten candidate problem domains. Each candidate was then tested against four questions.</p>
<p><strong>Is the data genuinely open?</strong> Not &ldquo;in principle available&rdquo; &mdash; actually retrievable, machine-readable, and licensed for reuse. Several attractive ideas failed here. Linking new homes to flood risk at national scale, for example, requires address lifecycle dates that exist only in a licensed Ordnance Survey product, which is why the best published analysis comes from an insurer rather than from government.</p>
<p><strong>Has government said it has the problem?</strong> Every system cites a National Audit Office report, a select committee finding, a departmental admission, or a dataset whose own documentation concedes the gap. Proposals that assert a problem on the author's authority are worth less than proposals that quote the buyer describing it.</p>
<p><strong>Does something already do this well?</strong> Ideas were dropped where a capable incumbent exists. Prescribing analysis is well served. Planning application aggregation, procurement market intelligence and retrofit targeting all have working products. A proposal that pitches government something it already has is worse than useless.</p>
<p><strong>Would it survive?</strong> The UK record here is poor and instructive. Three flagship civic data projects &mdash; a council spending comparison tool, an armchair auditor, and a local data platform &mdash; are so thoroughly dead that their domains now serve gambling spam. The national planning aggregation that others build on is, by its author's own description, a retirement hobby, and it has been losing councils twenty at a time to bot protection since June ${YEAR}. The only UK civic data products that are clearly secure are the ones with a paying customer.</p>
<div class="note note--warn mt-4">
<div class="note__title">A note on political timing</div>
<p style="margin:0">This research was compiled after the change of government in July ${YEAR}. The mission framework has been retired, the Department for Science, Innovation and Technology was abolished on 21 July, and responsibility for digital transformation, artificial intelligence and public sector fraud now sits with three different departments. The replacement ten-year plan has not been published. Every sponsor named in this portfolio reflects the machinery as it stands in August ${YEAR}, not as it stood in June.</p>
</div>
</div>
</div>
</section>

<section class="section section--alt" id="rejected">
<div class="wrap">
<div class="eyebrow">Discipline</div>
<h2 class="mt-3">What was considered and rejected</h2>
<p class="lede mt-3">A portfolio is only as credible as the ideas it declines. These were researched properly and left out.</p>
<div class="tablewrap mt-4">
<table><thead><tr><th>Idea</th><th>Why it was rejected</th></tr></thead><tbody>
<tr><td><strong>Retrofit targeting engine</strong></td><td>Household-level need derives from benefits and income data that cannot lawfully be published, so targeting belongs to bodies with legal access. Commercial tools already serve councils at £20,000&ndash;£80,000 a year. Retained only as outcome accountability, which nobody does.</td></tr>
<tr><td><strong>National planning application aggregator</strong></td><td>The gap is real &mdash; the government platform holds records from a handful of authorities and warns it is &ldquo;not yet ready for use&rdquo;. But an existing volunteer service already covers 420 authorities and 20.6 million applications. Building a rival duplicates fragile infrastructure rather than strengthening it.</td></tr>
<tr><td><strong>Empty homes versus housing need</strong></td><td>Property-level empty homes data comes from council tax records and is personal data. The only publishable product is a re-presentation of local authority statistics that are already free. A campaigning gap, not a product gap.</td></tr>
<tr><td><strong>Land ownership transparency</strong></td><td>Strong case until March ${YEAR}, when government committed to providing free spatial land ownership data for larger properties. Building against a moat the state is about to drain is poor timing.</td></tr>
<tr><td><strong>Prescribing and clinical analytics</strong></td><td>Well served by an established academic platform with secure long-term funding. No gap worth entering.</td></tr>
<tr><td><strong>Council financial distress tracker</strong></td><td>Genuinely unserved, and Exceptional Financial Support is published as prose inside annual guidance with no machine-readable form. Rejected on data integrity: more than 300 councils hold disclaimed audit opinions, so any resilience model inherits the disclaimer. Revisit once local audit recovers.</td></tr>
</tbody></table>
</div>
<div class="note mt-4">
<div class="note__title">The gap nobody asked about, which may matter most</div>
<p style="margin:0">Every system in this portfolio, and every commercial product in the same space, has to resolve addresses. The free national identifier carries coordinates but no address text; the addressed product is licensed, and reaches end of life in autumn 2027. An open UK address database is the shared infrastructure underneath all of it. It is out of scope here because the blocker is a commercial model rather than a technical problem &mdash; but it is the single highest-leverage ask any of these systems could make of government.</p>
</div>
</div>
</section>

<section class="section section--alt">
<div class="wrap">
<div class="eyebrow">The unified platform</div>
<h2 class="mt-3">Twelve of these are one system</h2>
<p class="lede mt-3">Twelve of the seventeen break at the same two joins &mdash; resolving places, and resolving organisations. Built once as shared infrastructure, they stop being twelve separate builds. Every source these twelve depend on was tested and returns data to an anonymous request: <strong>no account, no API key, no application, no approval</strong>.</p>
<div class="grid mt-4">
${DELIVERABLE.map(id => {
  const s = sysById[id];
  return `<a class="card" href="systems/${s.id}.html">
<div class="card__num">${s.num}</div>
<h3 class="card__title">${s.name}</h3>
<p class="card__desc">${s.subtitle}</p>
<div class="card__foot"><span class="tag tag--accent">Groundtruth</span><span class="tag">No personal data</span></div>
</a>`;
}).join('\n')}
</div>
<div class="flexrow mt-4">
<a class="btn btn--primary" href="platform.html">See the platform architecture &rarr;</a>
</div>
</div>
</section>

<section class="section" id="delivery">
<div class="wrap">
<div class="eyebrow">Delivery</div>
<h2 class="mt-3">How government would actually buy these</h2>
<div class="prose mt-4">
<p>Three changes in ${YEAR} make this materially easier than it was.</p>
<p><strong>Central digital spend controls ended on 1 April ${YEAR}.</strong> Departments are now accountable for applying the functional standards themselves, and assurance applies only above their own delegated authority limits. A pilot is a departmental decision rather than a central one.</p>
<p><strong>Framework entry reopens.</strong> The current digital outcomes framework was let as an open framework under the Procurement Act, with reopening cycles &mdash; so missing a window is no longer fatal. Product-shaped systems route through the cloud framework; delivery-shaped ones through digital outcomes; unproven research through the small business research initiative, where the department funds development and the supplier retains the intellectual property.</p>
<p><strong>Small supplier status is a scored advantage attached to a published target.</strong> Departments must set and publish three-year small business spend targets and report progress annually. They are collectively behind, and central government's small business share has fallen rather than risen. The Prime Minister has stated an intention to use public procurement to back British industry.</p>
<h3>What makes a proposition land</h3>
<p>The counter-fraud programme is the template worth copying. Government published a loss estimate it owns, reported savings against it, credited data-matching explicitly, and translated the result into nurses and repaired roads. Every system here is framed the same way: against a published number the department already accepts, with recovered or avoided cost rather than capability uplift as the headline.</p>
<p>Two further things now count as compliance arguments rather than sales points. Open standards and data portability are required by the technology code of practice, and the central digital team for local government has named supplier lock-in and inconsistent interfaces as the problem it exists to solve. And sovereignty is a live commercial position: one major health region rejected a US-built data platform in favour of a domestic alternative, and councils have publicly objected to the same supplier.</p>
</div>
</div>
</section>

<section class="section section--ink">
<div class="wrap wrap--narrow" style="text-align:center">
<div class="eyebrow" style="justify-content:center">Dexter DCL</div>
<h2 class="mt-3">Every claim here is traceable.</h2>
<p class="lede mt-3" style="margin-inline:auto;color:#B4BAC6">Each system brief carries its sources. Figures that could not be verified against a primary source were not used, and where the underlying data is weak, the brief says so rather than rounding the uncertainty away.</p>
<div class="hero__cta" style="justify-content:center">
<a class="btn btn--primary" style="background:var(--paper);color:var(--ink)" href="systems/${SYSTEMS[0].id}.html">Start with System 01</a>
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
<div class="stat"><div class="stat__num">2</div><div class="stat__label">Resolution layers underneath them</div></div>
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
writeFileSync('index.html', index);
writeFileSync('platform.html', platform);
SYSTEMS.forEach((s, i) => writeFileSync(`systems/${s.id}.html`, detailPage(s, i)));
console.log(`Built index.html + ${SYSTEMS.length} system pages:`);
SYSTEMS.forEach(s => console.log(`  systems/${s.id}.html  ${s.num} ${s.name}`));
