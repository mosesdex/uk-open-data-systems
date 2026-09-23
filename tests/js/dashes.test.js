import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

// The project rule: no em dash (—) or en dash (–) reaches a shipped
// page. Some source names and one reason category, copied verbatim from a
// published register, arrive in app/data/platform.json carrying one.
// Platform.load() (app/assets/platform.js) repairs them once, right after
// the payload is read, so every reader -- the sources table, the evidence
// panel, the sightline reason bars -- sees clean text. This sandboxes
// shared.js + platform.js exactly the way tools/app-content.mjs already
// does, so the test exercises the real loader against the real committed
// payload, not a reimplementation of either.
const ROOT = fileURLToPath(new URL('../../', import.meta.url));
const read = p => readFileSync(ROOT + p, 'utf8');
const DASH = /[–—]/;

async function loadPlatform() {
  const payload = JSON.parse(read('app/data/platform.json'));
  const savedFetch = globalThis.fetch;
  globalThis.fetch = async () => ({ ok: true, status: 200, json: async () => payload });
  try {
    const shared = read('app/assets/shared.js');
    const platform = read('app/assets/platform.js');
    const runner = new Function(`${shared}\n${platform}\nreturn {SYSTEMS, Platform};`);
    const { Platform } = runner();
    await Platform.load();
    return Platform;
  } finally {
    globalThis.fetch = savedFetch;
  }
}

test('no source name carries an em dash or en dash after load', async () => {
  const Platform = await loadPlatform();
  const rows = Platform.sourceSummary().rows;
  assert.ok(rows.length > 0, 'expected the real payload to carry source rows');
  for (const r of rows) {
    assert.doesNotMatch(r.name, DASH, `source name still carries a dash: ${r.name}`);
  }
});

test('no evidence dataset label carries an em dash or en dash after load', async () => {
  const Platform = await loadPlatform();
  const payload = Platform.payload();
  const headlines = (payload.evidence || {}).headlines || {};
  let checked = 0;
  for (const list of Object.values(headlines)) {
    for (const e of list || []) {
      if (!e.dataset) continue;
      checked++;
      assert.doesNotMatch(e.dataset, DASH, `evidence dataset still carries a dash: ${e.dataset}`);
    }
  }
  assert.ok(checked > 0, 'expected at least one evidence dataset label to check');
});

test('no sightline reason label carries an em dash or en dash after load', async () => {
  const Platform = await loadPlatform();
  const sightline = Platform.sys('sightline');
  const reasons = (sightline && sightline.reasons) || [];
  assert.ok(reasons.length > 0, 'expected the real payload to carry sightline reasons');
  for (const r of reasons) {
    assert.doesNotMatch(r.reason, DASH, `sightline reason still carries a dash: ${r.reason}`);
  }
});
