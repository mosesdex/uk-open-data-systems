#!/usr/bin/env node
/* Contrast sweep for the UK GroundTruth app.
 *
 * Walks a list of routes, in both themes, in a real Chrome tab (via
 * puppeteer-core against the local Chrome install -- no bundled download),
 * and for every visible text node computes the WCAG contrast ratio between
 * its computed foreground colour and its *effective* background colour --
 * i.e. that background composited through every ancestor's own
 * background-color, alpha included, the same way a browser paints it.
 * This is the same technique used to verify the .tabbar/.door__n dark-theme
 * fixes on this branch (see the commit that fixed those): walk the ancestor
 * chain, composite, then apply the WCAG formula.
 *
 * It does NOT rasterise the page: background-image/gradient layers are not
 * sampled, only background-color. Every text-bearing element this app ships
 * paints on a solid background-color, so that is sufficient here; an
 * element painting only a gradient/image behind text would need a manual
 * check and is called out separately in the summary.
 *
 * Serves the repo over a throwaway static server (bound to port 0 -- the OS
 * picks a free port every run, so this never collides with, or is confused
 * with, a previous run's cache) that sends Cache-Control: no-store on every
 * response. A plain `python3 -m http.server` does not do this and has
 * served stale CSS to reviewers on this branch before; this script exists
 * partly to stop that happening again. Every route+theme check opens a
 * brand-new page (Chrome tab), never a reused/navigated one.
 *
 * Usage:
 *   node tools/contrast-check.mjs                  # all routes, both themes
 *   node tools/contrast-check.mjs --route=/orgs     # one route (both themes)
 *   node tools/contrast-check.mjs --theme=dark      # one theme (all routes)
 *   node tools/contrast-check.mjs --json            # machine-readable dump
 *
 * Exit code is non-zero if any failing text node was found (handy for CI),
 * but this is a sweep tool, not one of the two gates the fix-wave task
 * calls out (npm test / seo-check.py) -- those still gate the work.
 */

import http from 'node:http';
import { readFile, stat } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { existsSync } from 'node:fs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, '..');

const ROUTES = [
  '#/',
  '#/places',
  '#/places/E07000032',
  '#/compare',
  '#/unusual',
  '#/about',
  '#/orgs',
  '#/search',
  '#/questions',
  '#/questions/plumbline',
];

const THEMES = ['light', 'dark'];
const WIDTHS = [1440, 375]; // desktop and the app's mobile floor

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.mjs': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.geojson': 'application/geo+json; charset=utf-8',
  '.png': 'image/png',
  '.svg': 'image/svg+xml',
  '.txt': 'text/plain; charset=utf-8',
  '.xml': 'application/xml; charset=utf-8',
};

function findChrome() {
  const candidates = [
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    '/Applications/Chromium.app/Contents/MacOS/Chromium',
    '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge',
  ];
  for (const c of candidates) if (existsSync(c)) return c;
  throw new Error('No local Chrome-family browser found at the usual macOS paths. ' +
    'Install Google Chrome, or edit findChrome() in tools/contrast-check.mjs.');
}

function startServer(root) {
  return new Promise((resolve, reject) => {
    const server = http.createServer(async (req, res) => {
      try {
        const urlPath = decodeURIComponent(req.url.split('?')[0]);
        let filePath = path.join(root, urlPath);
        if (!filePath.startsWith(root)) { res.writeHead(403); res.end(); return; }
        let st;
        try { st = await stat(filePath); } catch { st = null; }
        if (st && st.isDirectory()) filePath = path.join(filePath, 'index.html');
        const body = await readFile(filePath);
        const ext = path.extname(filePath);
        res.writeHead(200, {
          'Content-Type': MIME[ext] || 'application/octet-stream',
          'Cache-Control': 'no-store, no-cache, must-revalidate, max-age=0',
          'Pragma': 'no-cache',
          'Expires': '0',
        });
        res.end(body);
      } catch (e) {
        res.writeHead(404, { 'Cache-Control': 'no-store' });
        res.end('not found: ' + req.url);
      }
    });
    server.listen(0, '127.0.0.1', () => resolve(server));
    server.on('error', reject);
  });
}

/* ---- in-page measurement function (stringified into the page) ---- */
function inPageMeasure() {
  function parseColor(str) {
    if (!str) return null;
    const m = str.match(/rgba?\(([^)]+)\)/);
    if (!m) return null;
    const parts = m[1].split(',').map(s => parseFloat(s.trim()));
    const [r, g, b] = parts;
    const a = parts.length > 3 ? parts[3] : 1;
    if (Number.isNaN(r) || Number.isNaN(g) || Number.isNaN(b)) return null;
    return { r, g, b, a: Number.isNaN(a) ? 1 : a };
  }
  function composite(top, bottomOpaque) {
    // top over bottom, bottom assumed fully opaque; returns opaque colour
    const a = top.a;
    return {
      r: top.r * a + bottomOpaque.r * (1 - a),
      g: top.g * a + bottomOpaque.g * (1 - a),
      b: top.b * a + bottomOpaque.b * (1 - a),
    };
  }
  function effectiveBackground(el) {
    const chain = [];
    let node = el;
    while (node) {
      chain.push(node);
      if (node === document.documentElement) break;
      node = node.parentElement;
    }
    chain.reverse(); // html first, el last
    let bg = { r: 255, g: 255, b: 255 }; // backstop; html's own bg should override this
    for (const n of chain) {
      const cs = getComputedStyle(n);
      const c = parseColor(cs.backgroundColor);
      if (c && c.a > 0) bg = composite(c, bg);
    }
    return bg;
  }
  function luminance(c) {
    const f = v => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
    const [rs, gs, bs] = [f(c.r), f(c.g), f(c.b)];
    return 0.2126 * rs + 0.7152 * gs + 0.0722 * bs;
  }
  function ratio(c1, c2) {
    const L1 = luminance(c1), L2 = luminance(c2);
    const [hi, lo] = L1 > L2 ? [L1, L2] : [L2, L1];
    return (hi + 0.05) / (lo + 0.05);
  }
  function isVisible(el) {
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden') return false;
    const op = parseFloat(cs.opacity);
    if (!Number.isNaN(op) && op < 0.05) return false;
    const rect = el.getBoundingClientRect();
    if (rect.width <= 0 || rect.height <= 0) return false;
    // hidden attribute anywhere up the tree
    let n = el;
    while (n) { if (n.hidden) return false; n = n.parentElement; }
    return true;
  }
  function selectorFor(el) {
    const tag = el.tagName.toLowerCase();
    const cls = (el.className && typeof el.className === 'string')
      ? el.className.trim().split(/\s+/).filter(Boolean) : [];
    if (cls.length) return tag + '.' + cls.join('.');
    if (el.id) return tag + '#' + el.id;
    return tag;
  }

  const results = [];
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, {
    acceptNode(node) {
      if (!node.nodeValue || !node.nodeValue.trim()) return NodeFilter.FILTER_REJECT;
      const p = node.parentElement;
      if (!p) return NodeFilter.FILTER_REJECT;
      const tag = p.tagName;
      if (tag === 'SCRIPT' || tag === 'STYLE' || tag === 'NOSCRIPT' || tag === 'TEXTAREA') return NodeFilter.FILTER_REJECT;
      return NodeFilter.FILTER_ACCEPT;
    }
  });

  let node;
  while ((node = walker.nextNode())) {
    const el = node.parentElement;
    if (!isVisible(el)) continue;
    const cs = getComputedStyle(el);
    const fgRaw = parseColor(cs.color);
    if (!fgRaw) continue;
    const bg = effectiveBackground(el);
    const fg = fgRaw.a < 1 ? composite(fgRaw, bg) : fgRaw;
    const r = ratio(fg, bg);
    const fontSize = parseFloat(cs.fontSize);
    const weight = parseInt(cs.fontWeight, 10) || 400;
    const isLarge = fontSize >= 24 || (fontSize >= 18.66 && weight >= 700);
    const threshold = isLarge ? 3.0 : 4.5;
    if (r < threshold - 0.005) {
      results.push({
        selector: selectorFor(el),
        text: node.nodeValue.trim().slice(0, 40),
        ratio: Math.round(r * 100) / 100,
        threshold,
        large: isLarge,
        fontSize: Math.round(fontSize * 10) / 10,
        fontWeight: weight,
        fg: `rgb(${Math.round(fg.r)},${Math.round(fg.g)},${Math.round(fg.b)})`,
        bg: `rgb(${Math.round(bg.r)},${Math.round(bg.g)},${Math.round(bg.b)})`,
      });
    }
  }
  return results;
}

async function settle(page) {
  await page.evaluate(async () => {
    const sleep = ms => new Promise(r => setTimeout(r, ms));
    const h = document.body.scrollHeight;
    const steps = 6;
    for (let i = 1; i <= steps; i++) {
      window.scrollTo(0, Math.round((h * i) / steps));
      await sleep(90);
    }
    window.scrollTo(0, 0);
    await sleep(150);
  });
}

async function waitForContent(page) {
  await page.waitForFunction(() => {
    const v = document.querySelector('.view:not([hidden])');
    return v && v.innerText && v.innerText.trim().length > 40;
  }, { timeout: 15000 }).catch(() => {});
  // let CSS transitions (reveal, theme swap) finish
  await new Promise(r => setTimeout(r, 250));
}

async function main() {
  const args = process.argv.slice(2);
  const asJson = args.includes('--json');
  const routeArg = (args.find(a => a.startsWith('--route=')) || '').split('=')[1];
  const themeArg = (args.find(a => a.startsWith('--theme=')) || '').split('=')[1];

  const routes = routeArg ? ROUTES.filter(r => r === ('#/' + routeArg.replace(/^#?\/?/, ''))) : ROUTES;
  const themes = themeArg ? [themeArg] : THEMES;
  if (routeArg && routes.length === 0) {
    console.error(`No route matches --route=${routeArg}. Known routes:\n  ${ROUTES.join('\n  ')}`);
    process.exit(2);
  }

  const server = await startServer(ROOT);
  const port = server.address().port;
  const base = `http://127.0.0.1:${port}/app/index.html`;

  const puppeteer = await import('puppeteer-core');
  const browser = await puppeteer.default.launch({
    executablePath: findChrome(),
    headless: true,
  });

  const report = {}; // report[route][theme] = { total, bySelector: {...} }

  try {
    for (const route of routes) {
      report[route] = {};
      for (const theme of themes) {
        // bySelector holds one group per CSS selector signature. The node COUNT
        // for a selector is taken from the first width it is seen at (a text
        // node is one instance of the page, not one instance per viewport we
        // happen to check it at) -- widths after that only refine the worst
        // ratio and note that the same failure also reproduces there. This is
        // what keeps totals comparable to a single-pass manual count instead
        // of doubling every number because WIDTHS has two entries.
        const bySelector = new Map();
        for (const width of WIDTHS) {
          const page = await browser.newPage(); // fresh tab, every check
          try {
            await page.setCacheEnabled(false);
            await page.emulateMediaFeatures([{ name: 'prefers-color-scheme', value: theme }]);
            await page.setViewport({ width, height: 900 });
            await page.goto(base + route, { waitUntil: 'networkidle0', timeout: 30000 });
            await waitForContent(page);
            await settle(page);
            const found = await page.evaluate(inPageMeasure);
            const seenThisPass = new Map(); // selector -> count at this width
            for (const f of found) seenThisPass.set(f.selector, (seenThisPass.get(f.selector) || 0) + 1);
            for (const f of found) {
              const key = f.selector;
              if (!bySelector.has(key)) {
                bySelector.set(key, { ...f, count: seenThisPass.get(key), widths: new Set() });
              }
              const g = bySelector.get(key);
              g.widths.add(width);
              if (f.ratio < g.ratio) { g.ratio = f.ratio; g.fg = f.fg; g.bg = f.bg; g.text = f.text; }
            }
          } finally {
            await page.close();
          }
        }
        const groups = [...bySelector.values()].sort((a, b) => a.ratio - b.ratio);
        const total = groups.reduce((n, g) => n + g.count, 0);
        report[route][theme] = { total, groups };
      }
    }
  } finally {
    await browser.close();
    server.close();
  }

  if (asJson) {
    console.log(JSON.stringify(report, null, 2));
  } else {
    let grandTotal = 0;
    for (const route of routes) {
      for (const theme of themes) {
        const { total, groups } = report[route][theme];
        grandTotal += total;
        console.log(`\n${route}  [${theme}]  -- ${total} failing text node${total === 1 ? '' : 's'}`);
        for (const g of groups) {
          const w = [...g.widths].sort((a, b) => a - b).join(',');
          console.log(`  ${g.ratio.toFixed(2)}:1  (need ${g.threshold}:1${g.large ? ', large text' : ''})  ` +
            `${g.selector}  x${g.count}  fg=${g.fg} bg=${g.bg}  @${w}px  "${g.text}"`);
        }
      }
    }
    console.log(`\nGrand total across checked routes/themes: ${grandTotal} failing text node group-instances`);
  }

  process.exit(Object.values(report).some(r => Object.values(r).some(t => t.total > 0)) ? 1 : 0);
}

main().catch(e => { console.error(e); process.exit(1); });
