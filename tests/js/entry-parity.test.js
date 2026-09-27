import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, readdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

/* app/assets/lib/entry.js is the one bridge between the ES modules and the
   classic scripts: it imports every pure function and hangs it on
   window.GT_LIB. It is maintained by hand, and nothing else in this suite
   loads it, because every other test imports the modules directly.

   That gap took the live site down. entry.js imported placeAbsenceNotes from
   answers.js while a visitor still held a cached answers.js from before that
   export existed. A missing export is a module-graph SyntaxError, not a
   missing property, so the whole graph failed and window.GT_LIB was never
   assigned: search, postcode lookup, area lookup and route aliasing all died
   at once, on a site whose tests were entirely green.

   These tests read the shipped source, the same way tests/js/routes.test.js
   and tests/js/scroll.test.js do, and assert the bridge is internally
   consistent. */

const here = (p) => fileURLToPath(new URL(p, import.meta.url));
const LIB = here('../../app/assets/lib/');
const read = (f) => readFileSync(LIB + f, 'utf8');

const ENTRY = read('entry.js');

/* Every `import { a, b } from './x.js'` in entry.js, as {file: [names]}. */
function entryImports() {
  const out = {};
  const re = /import\s*\{([^}]+)\}\s*from\s*'\.\/([\w.-]+)'/g;
  let m;
  while ((m = re.exec(ENTRY))) {
    out[m[2]] = m[1].split(',').map(s => s.trim()).filter(Boolean);
  }
  return out;
}

/* Every `export function name` / `export const name` in one module. */
function exportsOf(file) {
  const src = read(file);
  const names = [];
  const re = /^export\s+(?:async\s+)?(?:function|const|let|class)\s+([A-Za-z_$][\w$]*)/gm;
  let m;
  while ((m = re.exec(src))) names.push(m[1]);
  return names;
}

/* The names entry.js hangs on window.GT_LIB, from its Object.assign literal. */
function bridgedNames() {
  const body = ENTRY.slice(ENTRY.indexOf('Object.assign'));
  const open = body.indexOf('{', body.indexOf('window.GT_LIB || {}') + 1);
  const literal = body.slice(open + 1, body.indexOf('}', body.lastIndexOf(',')) + 1);
  return literal.replace(/[{}]/g, '').split(',').map(s => s.trim().split(':')[0]).filter(Boolean);
}

test('entry.js imports at least one name, so the parser is actually working', () => {
  // Guards the tests below: a regex that silently matched nothing would make
  // every other assertion in this file vacuously pass.
  const imports = entryImports();
  assert.ok(Object.keys(imports).length >= 5,
    `expected entry.js to import from several modules, parsed ${JSON.stringify(imports)}`);
});

test('every name entry.js imports is actually exported by that module', () => {
  for (const [file, names] of Object.entries(entryImports())) {
    const available = exportsOf(file);
    assert.ok(available.length > 0, `parsed no exports at all from ${file}`);
    for (const name of names) {
      assert.ok(available.includes(name),
        `entry.js imports ${name} from ${file}, which does not export it. `
        + `A missing export fails the whole module graph, not just this name.`);
    }
  }
});

test('every name entry.js imports reaches window.GT_LIB', () => {
  const bridged = bridgedNames();
  assert.ok(bridged.length >= 5, `parsed too few bridged names: ${JSON.stringify(bridged)}`);
  for (const names of Object.values(entryImports())) {
    for (const name of names) {
      assert.ok(bridged.includes(name),
        `${name} is imported by entry.js but never assigned to window.GT_LIB, `
        + `so the shell cannot reach it`);
    }
  }
});

test('entry.js imports every module in the lib directory, or the unused one is deliberate', () => {
  // A module nobody bridges is either dead or a forgotten wiring step. Both are
  // worth knowing about; the second is what left placeAbsenceNotes undefined in
  // the running app while its own tests passed.
  const files = readdirSync(LIB).filter(f => f.endsWith('.js') && f !== 'entry.js');
  const imported = Object.keys(entryImports());
  const orphans = files.filter(f => !imported.includes(f));
  assert.deepEqual(orphans, [],
    `these modules are not reached from entry.js: ${orphans.join(', ')}`);
});
