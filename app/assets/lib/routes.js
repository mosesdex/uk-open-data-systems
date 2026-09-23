/* Every hash the app has ever published, mapped to the one it means now.
   The outreach campaign links to #/systems/<id> from 150 emails, so that route
   cannot simply stop existing: it resolves to the question it always meant. */

const SECTION = {
  '#/systems': '#/',
  '#/sources': '#/about',
  '#/method': '#/about',
};

const ANCHOR = {
  '#top': '#/about', '#hero': '#/about', '#spines': '#/about', '#chains': '#/about',
  '#place': '#/places', '#systems': '#/', '#compare': '#/compare',
  '#feeds': '#/about', '#honesty': '#/about', '#kpis': '#/',
  '#org': '#/orgs', '#search': '#/search',
};

export function canonicalHash(raw) {
  const hash = String(raw || '').trim();
  if (!hash || hash === '#' || hash === '#/') return null;

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
