import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

/* The question pages, the organisation index and search could not be scrolled.

   #syshost was once a slide-over panel with its own inner scroller, so
   systempage.js froze the page behind it with body { overflow: hidden } every
   time it rendered. It is a plain route in normal document flow now: #syshost
   is display:block with no height and no overflow of its own, so that lock did
   not hold a panel open, it simply stopped the page moving. Measured before the
   fix: #/questions/<id> 3,029px to 5,054px tall, #/search 1,092px, and #/orgs
   39,736px, all of them immovable, with everything below the fold unreachable.

   This is a structural test because the failure lives in the DOM and the suite
   has no DOM. It reads the shipped source instead, the same way
   tests/js/routes.test.js checks shell.js and app/index.html. */

const read = (p) => readFileSync(new URL(p, import.meta.url), 'utf8');

const SYSTEMPAGE = read('../../app/assets/systempage.js');
const SHELL = read('../../app/assets/shell.js');

test('systempage never freezes the page it has just rendered', () => {
  const locks = SYSTEMPAGE.match(/document\.body\.style\.overflow\s*=\s*['"]hidden['"]/g) || [];
  assert.deepEqual(locks, [],
    'systempage.js renders full-page routes, so locking body scroll makes them '
    + 'unscrollable rather than holding an overlay open');
});

test('no shipped script locks body scroll without an element that scrolls instead', () => {
  // shell.js is allowed to clear the lock; nothing is allowed to set it while
  // the only container in play, #syshost, has no scroller of its own.
  for (const [name, src] of [['systempage.js', SYSTEMPAGE], ['shell.js', SHELL]]) {
    const sets = src.match(/body\.style\.overflow\s*=\s*['"]hidden['"]/g) || [];
    assert.deepEqual(sets, [], `${name} sets a body scroll lock`);
  }
});

test('the container the detail routes render into still declares no scroller', () => {
  // If #syshost ever gains its own overflow and height, a body lock becomes
  // legitimate again and the tests above should be revisited rather than
  // worked around. This pins the assumption they rest on.
  const css = read('../../app/assets/app.css');
  const rule = (css.match(/#syshost\s*\{[^}]*\}/g) || []).join(' ');
  assert.ok(rule, '#syshost should still be styled in app.css');
  assert.ok(!/overflow/.test(rule),
    '#syshost has gained an overflow; revisit whether a body scroll lock is now correct');
});
