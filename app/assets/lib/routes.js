/* Every hash the app has ever published, mapped to the destinations that
   could serve it. The outreach campaign links to #/systems/<id> from 150
   emails, so that route cannot simply stop existing: it resolves to the
   question it always meant.

   Each entry below is an ORDERED LIST of candidate destinations, best
   first, not a single hash. The first entry is where the hash should
   eventually land; any entries after it are earlier destinations that
   render today. canonicalHash walks the list and returns the first
   candidate whose head canRender approves, so a mapping upgrades itself
   automatically once a later task adds a route handler for the better
   destination, and degrades to something that renders today rather than
   dead-ending on a destination with no handler yet. */

export const SECTION = {
  '#/systems': ['#/'],
  '#/sources': ['#/about', '#/sources'],
  '#/method': ['#/about', '#/method'],
};

export const ANCHOR = {
  '#top': ['#/about', '#/method'], '#hero': ['#/about', '#/method'],
  '#spines': ['#/about', '#/method'], '#chains': ['#/about', '#/method'],
  '#place': ['#/places'], '#systems': ['#/'], '#compare': ['#/compare', '#/systems'],
  '#feeds': ['#/about', '#/sources'], '#honesty': ['#/about', '#/sources'], '#kpis': ['#/'],
  '#org': ['#/orgs'], '#search': ['#/search'],
};

// The heads route() in app/assets/shell.js actually dispatches today. This
// is the authoritative copy: shell.js and the test suite both read it
// instead of keeping their own hand-copied list in step.
export const ROUTER_HEADS = new Set(['', 'places', 'systems', 'orgs', 'sources', 'method', 'search']);

function resolve(hash) {
  if (Object.prototype.hasOwnProperty.call(ANCHOR, hash)) return ANCHOR[hash];
  if (Object.prototype.hasOwnProperty.call(SECTION, hash)) return SECTION[hash];

  const renamed = hash.match(/^#\/systems\/(.+)$/);
  if (renamed) return [`#/questions/${renamed[1]}`, `#/systems/${renamed[1]}`];

  const legacySystem = hash.match(/^#system\/([a-z0-9_-]+)$/i);
  if (legacySystem) return [`#/questions/${legacySystem[1]}`, `#/systems/${legacySystem[1]}`];

  const legacyOrg = hash.match(/^#org\/(.+)$/);
  if (legacyOrg) return [`#/orgs/${legacyOrg[1]}`];

  return null;
}

// canRender tells canonicalHash what the app can actually serve right now.
// A redirect to a route with no handler is worse than leaving the URL
// alone: the old hash at least rendered something, while a destination
// with no handler renders "No such view". The redesign lands its route
// handlers over several tasks, so a destination that is correct in the
// tables above can still be unservable today. Default to "render anything"
// so callers that do not care about this yet keep the old behaviour.
export function canonicalHash(raw, canRender = () => true) {
  const hash = String(raw || '').trim();
  if (!hash || hash === '#' || hash === '#/') return null;

  const candidates = resolve(hash);
  if (candidates === null) return null;

  for (const candidate of candidates) {
    const head = candidate.slice(2).split('/')[0];
    if (canRender(head)) {
      // The winning candidate can be the raw hash itself (e.g. a renamed
      // route degrading back to its own current form): that is not a
      // redirect, it is already canonical, so say so with null.
      return candidate === hash ? null : candidate;
    }
  }

  // Nothing in the candidate list can render today; leave the URL alone
  // rather than send it somewhere that dead-ends.
  return null;
}
