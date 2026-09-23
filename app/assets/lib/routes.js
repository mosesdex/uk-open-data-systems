/* Every hash the app has ever published, mapped to the one it means now.
   The outreach campaign links to #/systems/<id> from 150 emails, so that route
   cannot simply stop existing: it resolves to the question it always meant. */

export const SECTION = {
  '#/systems': '#/',
  '#/sources': '#/about',
  '#/method': '#/about',
};

export const ANCHOR = {
  '#top': '#/about', '#hero': '#/about', '#spines': '#/about', '#chains': '#/about',
  '#place': '#/places', '#systems': '#/', '#compare': '#/compare',
  '#feeds': '#/about', '#honesty': '#/about', '#kpis': '#/',
  '#org': '#/orgs', '#search': '#/search',
};

function resolve(hash) {
  if (Object.prototype.hasOwnProperty.call(ANCHOR, hash)) return ANCHOR[hash];
  if (Object.prototype.hasOwnProperty.call(SECTION, hash)) return SECTION[hash];

  const renamed = hash.match(/^#\/systems\/(.+)$/);
  if (renamed) return `#/questions/${renamed[1]}`;

  const legacySystem = hash.match(/^#system\/([a-z0-9_-]+)$/i);
  if (legacySystem) return `#/questions/${legacySystem[1]}`;

  const legacyOrg = hash.match(/^#org\/(.+)$/);
  if (legacyOrg) return `#/orgs/${legacyOrg[1]}`;

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

  const destination = resolve(hash);
  if (destination === null) return null;

  const head = destination.slice(2).split('/')[0];
  return canRender(head) ? destination : null;
}
