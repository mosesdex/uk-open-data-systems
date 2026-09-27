// Give the module graph a versioned directory, so a deploy cannot serve half of it.
//
// The app's pure logic lives in ES modules under assets/lib/. index.html loads
// one of them, entry.js, and entry.js imports the other nine by relative path.
// Every one of those files is fetched separately and cached separately, and
// GitHub Pages serves them with max-age=600.
//
// So for ten minutes after a deploy a returning visitor can hold a new
// entry.js beside an old answers.js. That is not a degraded page, it is a dead
// one: a name a module no longer exports is a module-graph SyntaxError, so
// nothing in the graph runs and window.GT_LIB is never assigned. Search,
// postcode lookup, area lookup and route aliasing all stop at once. It
// happened on the 27 September deploy and it would happen again on any deploy
// that changes what a module exports.
//
// The fix is to make mixing impossible rather than unlikely. The directory is
// renamed to carry a hash of its own contents, and the HTML is pointed at the
// new name. A relative import inside a module resolves against that module's
// own URL, so entry.js in assets/lib-a1b2c3/ pulls answers.js from
// assets/lib-a1b2c3/ without any import rewriting: the whole graph moves
// together or not at all. A browser has never seen the new directory, so it
// has nothing stale to serve from it.
//
// Versioning the directory rather than each file is what makes this work with
// no source changes. A query string on entry.js alone would not: its imports
// would still resolve to the unversioned, cached siblings.
//
//   node tools/version-modules.mjs _site
//
import { createHash } from 'node:crypto';
import { readdirSync, readFileSync, renameSync, statSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';

const LIB = 'assets/lib';

/** Every file under dir, relative to it, sorted, so the hash is stable. */
export function filesUnder(dir) {
  const out = [];
  const walk = (rel) => {
    for (const name of readdirSync(join(dir, rel)).sort()) {
      const r = rel ? `${rel}/${name}` : name;
      if (statSync(join(dir, r)).isDirectory()) walk(r);
      else out.push(r);
    }
  };
  walk('');
  return out;
}

/** A short hash over the names and bytes of a directory's contents. */
export function hashDir(dir) {
  const h = createHash('sha256');
  for (const rel of filesUnder(dir)) {
    // The name goes in too, so renaming a file changes the hash even when the
    // bytes are unchanged between them.
    h.update(rel);
    h.update(readFileSync(join(dir, rel)));
  }
  return h.digest('hex').slice(0, 12);
}

/** Point every src or href at the versioned directory. */
export function rewrite(html, version) {
  // Only src and href attributes, because index.html's comments discuss these
  // module paths in prose. Rewriting those too would leave a comment pointing
  // at a directory that exists only in the deployed copy, which is a small lie
  // in the place this codebase keeps its reasoning. Only the directory prefix
  // moves; the file path after it is untouched, so a module added later needs
  // no change here.
  return html.replace(
    /\b(src|href)=(["'])([^"']*)\2/g,
    (whole, attr, quote, value) => value.includes(`${LIB}/`)
      ? `${attr}=${quote}${value.split(`${LIB}/`).join(`${LIB}-${version}/`)}${quote}`
      : whole);
}

export function versionModules(site) {
  const libDir = join(site, LIB);
  const version = hashDir(libDir);
  renameSync(libDir, join(site, `${LIB}-${version}`));

  let rewritten = 0;
  for (const name of readdirSync(site)) {
    if (!name.endsWith('.html')) continue;
    const path = join(site, name);
    const before = readFileSync(path, 'utf8');
    const after = rewrite(before, version);
    if (after === before) continue;
    writeFileSync(path, after);
    rewritten += 1;
  }

  // A rename with nothing pointing at the new name is worse than doing
  // nothing: the site would ship with a module directory no page loads.
  if (rewritten === 0) {
    throw new Error(`no HTML in ${site} referenced ${LIB}/, so the rename would break the app`);
  }

  // And nothing may still point at the old path, which no longer exists.
  for (const name of readdirSync(site)) {
    if (!name.endsWith('.html')) continue;
    const src = readFileSync(join(site, name), 'utf8');
    const stale = src.match(new RegExp(`\\b(?:src|href)=["'][^"']*${LIB}/`));
    if (stale) {
      throw new Error(`${name} still loads from ${LIB}/ after rewriting: ${stale[0]}`);
    }
  }

  return { version, rewritten };
}

// Run directly, not when imported by the tests.
if (process.argv[1] && process.argv[1].endsWith('version-modules.mjs')) {
  const site = process.argv[2];
  if (!site) {
    console.error('usage: node tools/version-modules.mjs <site-dir>');
    process.exit(2);
  }
  const { version, rewritten } = versionModules(site);
  console.log(`module graph versioned: ${LIB}-${version} (${rewritten} page(s) rewritten)`);
}
