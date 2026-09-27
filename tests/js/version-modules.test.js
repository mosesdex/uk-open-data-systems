import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, mkdirSync, writeFileSync, readFileSync, existsSync, renameSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { hashDir, rewrite, versionModules } from '../../tools/version-modules.mjs';

/* tools/version-modules.mjs exists because a deploy served a new entry.js
   beside a cached old answers.js, which is a module-graph SyntaxError rather
   than a missing property, so window.GT_LIB was never assigned and every
   module-backed feature stopped at once. See the tool's own header. */

function site({ entry = "import { a } from './dep.js';", dep = 'export const a = 1;',
                html = '<script type="module" src="assets/lib/entry.js"></script>' } = {}) {
  const dir = mkdtempSync(join(tmpdir(), 'gt-site-'));
  mkdirSync(join(dir, 'assets/lib'), { recursive: true });
  writeFileSync(join(dir, 'assets/lib/entry.js'), entry);
  writeFileSync(join(dir, 'assets/lib/dep.js'), dep);
  writeFileSync(join(dir, 'index.html'), html);
  return dir;
}

test('the whole directory moves, so a graph can never be half stale', () => {
  const dir = site();
  const { version } = versionModules(dir);
  assert.ok(!existsSync(join(dir, 'assets/lib')), 'the unversioned directory must be gone');
  const moved = join(dir, `assets/lib-${version}`);
  assert.ok(existsSync(join(moved, 'entry.js')));
  assert.ok(existsSync(join(moved, 'dep.js')), 'every module moves together, not just the entry');
});

test('the import inside the module is left alone, because the directory carries the version', () => {
  const dir = site();
  const { version } = versionModules(dir);
  const entry = readFileSync(join(dir, `assets/lib-${version}/entry.js`), 'utf8');
  assert.match(entry, /from '\.\/dep\.js'/,
    'a relative import resolves against its own module URL, so it needs no rewriting');
});

test('the page points at the versioned directory and never at the old one', () => {
  const dir = site();
  const { version, rewritten } = versionModules(dir);
  const html = readFileSync(join(dir, 'index.html'), 'utf8');
  assert.equal(rewritten, 1);
  assert.match(html, new RegExp(`assets/lib-${version}/entry\\.js`));
  assert.doesNotMatch(html, /assets\/lib\/entry\.js/);
});

test('changing any module changes the version, so the browser cannot reuse the old one', () => {
  const a = hashDir(join(site(), 'assets/lib'));
  const b = hashDir(join(site({ dep: 'export const a = 2;' }), 'assets/lib'));
  assert.notEqual(a, b);
});

test('identical contents give an identical version, so an unchanged deploy does not churn', () => {
  assert.equal(hashDir(join(site(), 'assets/lib')), hashDir(join(site(), 'assets/lib')));
});

test('renaming a module changes the version even when the bytes are the same', () => {
  const one = site();
  const two = site();
  // same bytes, different file name
  renameSync(join(two, 'assets/lib/dep.js'), join(two, 'assets/lib/other.js'));
  assert.notEqual(hashDir(join(one, 'assets/lib')), hashDir(join(two, 'assets/lib')));
});

test('a site whose pages reference nothing is refused, not silently broken', () => {
  const dir = site({ html: '<p>no modules here</p>' });
  assert.throws(() => versionModules(dir), /no HTML .* referenced/,
    'renaming with nothing pointing at the new name would ship a directory no page loads');
});

test('rewrite moves only the directory prefix, so a module added later needs no change here', () => {
  const html = '<script src="assets/lib/entry.js"></script><link href="assets/lib/later.js">';
  const out = rewrite(html, 'abc123');
  assert.equal(out,
    '<script src="assets/lib-abc123/entry.js"></script><link href="assets/lib-abc123/later.js">');
});

test('a comment discussing the path in prose is left alone', () => {
  // index.html explains its own routing in comments that name
  // app/assets/lib/routes.js. Those are reasoning, not references, and a
  // rewritten one would point at a directory that exists only after deploy.
  const html = '<!-- see assets/lib/routes.js for why -->\n<script src="assets/lib/entry.js"></script>';
  const out = rewrite(html, 'abc123');
  assert.match(out, /<!-- see assets\/lib\/routes\.js for why -->/);
  assert.match(out, /src="assets\/lib-abc123\/entry\.js"/);
});

test('a page that only mentions the path in prose is not counted as rewritten', () => {
  const dir = site({ html: '<!-- assets/lib/routes.js is discussed here -->' });
  assert.throws(() => versionModules(dir), /no HTML .* referenced/,
    'prose is not a reference, so such a site genuinely loads no modules');
});
