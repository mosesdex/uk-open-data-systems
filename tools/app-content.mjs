// Renders the app's key content into static HTML at build time.
//
// The app is a JavaScript application: its containers ship empty and fill from
// data/platform.json in the browser. That is fine for a person and bad for
// everything else -- a crawler that does not execute JavaScript, and most AI
// search systems, see 91 words on /mobile.html and no systems at all on /.
// The site's whole substance is invisible to them.
//
// So the same figures are rendered here, at build time, into the containers the
// app later overwrites. A person with JavaScript sees exactly what they saw
// before; a crawler without it sees the thirteen systems and what each one
// found.
//
// The figures come from the app's own platform.js rather than from a second
// implementation in this file. A separate copy of `systemResult` would be a
// second chance to disagree with the interface it is meant to mirror, which is
// the failure this project exists to prevent.
//
//   node tools/app-content.mjs
//
import { readFileSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

// fileURLToPath, not .pathname: the repository path contains a space, and
// .pathname hands back a percent-encoded string that fs cannot open.
const ROOT = fileURLToPath(new URL('..', import.meta.url));
const read = (p) => readFileSync(ROOT + p, 'utf8');

const START = '<!-- generated:static-content -->';
const END = '<!-- /generated:static-content -->';

// ---- run the app's own modules, so the numbers cannot drift ---------------
const payload = JSON.parse(read('app/data/platform.json'));
globalThis.fetch = async () => ({
  ok: true, status: 200, json: async () => payload,
});

const sandbox = {};
const shared = read('app/assets/shared.js');
const platform = read('app/assets/platform.js');
const runner = new Function(`${shared}\n${platform}\nreturn {SYSTEMS, Platform};`);
const { SYSTEMS, Platform } = runner();
await Platform.load();
if (Platform.error()) throw new Error('platform.json did not load: ' + Platform.error());

const esc = (s) => String(s ?? '')
  .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  .replace(/"/g, '&quot;');

// ---- the block ------------------------------------------------------------
function systemsBlock({ compact = false } = {}) {
  const rows = SYSTEMS.map((s) => {
    const r = Platform.systemResult(s.id);
    const figure = r
      ? `<p class="card__s"><strong>${esc(r.headline)}</strong> ${esc(r.label)}${
          r.sub ? ` &mdash; ${esc(r.sub)}` : ''}</p>`
      : `<p class="card__s">No measured output yet.</p>`;
    return `<li><a href="${compact ? '../' : ''}systems/${esc(s.id)}.html"><strong>${esc(s.n)}</strong></a>
 &mdash; ${esc(s.s)}. ${figure}</li>`;
  }).join('\n');

  const built = Platform.builtSystems().length;
  const src = Platform.sourceSummary();
  const generated = Platform.generated();

  return `${START}
<section class="static-summary">
<h2>The thirteen systems, and what each one found</h2>
<p>Every figure below is computed from a published government record and carries
the coverage it rests on. ${built} of ${SYSTEMS.length} systems have measured
output; ${src.ok} of ${src.total} registered sources returned data to an
unauthenticated request on the last run.${
    generated ? ` Computed ${esc(String(generated).slice(0, 10))}.` : ''}</p>
<ul>
${rows}
</ul>
<p>Each system links to a brief setting out its sources, its method, and what it
cannot tell you.</p>
</section>
${END}`;
}

// ---- inject ---------------------------------------------------------------
function inject(file, container, block) {
  const path = ROOT + file;
  let html = readFileSync(path, 'utf8');

  if (html.includes(START)) {
    html = html.replace(new RegExp(`${START}[\\s\\S]*?${END}`), block);
  } else {
    // Seed it inside the container the app later overwrites, so the static copy
    // is replaced by the live one the moment scripts run.
    const open = new RegExp(`(<div[^>]*id="${container}"[^>]*>)`);
    if (!open.test(html)) throw new Error(`no #${container} in ${file}`);
    html = html.replace(open, `$1\n${block}\n`);
  }
  writeFileSync(path, html);
  return html.length;
}

const n1 = inject('app/index.html', 'sysGrid', systemsBlock());
const n2 = inject('app/mobile.html', 'mSystems', systemsBlock({ compact: true }));
console.log(`static content injected: app/index.html (${n1} bytes), app/mobile.html (${n2} bytes)`);
