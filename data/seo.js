// SEO configuration and builders. Consumed by build.js.
//
// Everything search engines see is derived here rather than written into each
// page, so a new system page cannot ship without a canonical URL, a social card
// and structured data. The site is static and generated, so "dynamic metadata"
// means metadata composed at build time from the same content objects the page
// itself is built from -- there is no second copy to drift.
//
// Two rules the rest of this file exists to enforce:
//
//   * Structured data describes only what the page actually contains. This site
//     has no search box, so no SearchAction; no reviews, so no Review; no
//     products, so no Product. Marking up things that are not there is the
//     structured-data equivalent of a false join.
//   * The operational system in app/ is never referenced. It is localhost-only
//     by design, so it appears in no sitemap, no canonical and no link.

// Served from its own apex domain, so the site sits at the origin root. That
// is what makes robots.txt effective -- a robots.txt is only honoured at the
// root, which a GitHub Pages project subpath could never satisfy.
const ORIGIN = process.env.SITE_ORIGIN || 'https://ukgroundtruth.co.uk';
const BASE = process.env.SITE_BASE ?? '';

export const SITE = {
  origin: ORIGIN,
  base: BASE,
  url: `${ORIGIN}${BASE}`,
  name: 'UK GroundTruth',
  tagline: 'One platform, thirteen public data systems',
  publisher: 'Dexter DCL Limited',
  publisherShort: 'Dexter DCL',
  // The one contact route the site publishes. Corrections arrive here too, so
  // it is asserted in the Organization node rather than only rendered in HTML.
  email: 'moses@dextercyberlab.com',
  locale: 'en_GB',
  lang: 'en-GB',
  // No verified brand account, so no twitter:site tag is emitted. A card still
  // renders from the summary_large_image type and the og: tags.
  twitterSite: process.env.SITE_TWITTER || null,
  licence: 'Contains public sector information licensed under the Open Government Licence v3.0.',
};

/** Absolute canonical URL for a built page path such as 'systems/ledger.html'. */
export const canonical = (path = '') => {
  const clean = String(path).replace(/^\/+/, '');
  // The site root is served at both '/' and '/index.html'. One of them has to
  // be the canonical form or the homepage competes with itself.
  if (clean === '' || clean === 'index.html') return `${SITE.url}/`;
  return `${SITE.url}/${clean}`;
};

/** Social card image for a page. Per-system where one exists, else the default. */
export const cardImage = (id) =>
  `${SITE.url}/assets/social/${id && id !== 'index' ? id : 'default'}.png`;

// Titles are composed, then the brand suffix is added only when it fits. A
// title Google truncates mid-word is worse than one without the brand on it.
const TITLE_BUDGET = 62;

export const composeTitle = (name, subtitle) => {
  const full = subtitle ? `${name} — ${subtitle}` : name;
  const withBrand = `${full} | ${SITE.name}`;
  if (withBrand.length <= TITLE_BUDGET) return withBrand;
  return full.length <= 70 ? full : `${name} | ${SITE.name}`;
};

/** Trim a description to a length search engines will actually show. */
export const composeDescription = (text, max = 158) => {
  const flat = String(text).replace(/<[^>]+>/g, '').replace(/\s+/g, ' ').trim();
  if (flat.length <= max) return flat;
  const cut = flat.slice(0, max);
  return cut.slice(0, cut.lastIndexOf(' ')).replace(/[,;:—-]$/, '') + '…';
};

// ---------------------------------------------------------------- JSON-LD

const jsonld = (obj) =>
  `<script type="application/ld+json">${JSON.stringify(obj)
    // A closing tag inside JSON would end the script element early. Escaping it
    // is the difference between structured data and an XSS vector.
    .replace(/</g, '\\u003c')}</script>`;

// The description said "a private proposal document" for as long as the domain
// served the write-up. It now serves the platform, so it says what the platform
// is. No company number or address is asserted: neither has been published, and
// a structured-data field is not the place to guess one.
export const organisation = () => ({
  '@type': 'Organization',
  '@id': `${SITE.url}/#organisation`,
  name: SITE.publisher,
  alternateName: SITE.publisherShort,
  url: `${SITE.url}/`,
  email: SITE.email,
  description:
    'An independent UK company. UK GroundTruth is a platform built by Dexter DCL ' +
    'on published UK government data. It is not a government publication and ' +
    'carries no government endorsement.',
});

export const website = () => ({
  '@type': 'WebSite',
  '@id': `${SITE.url}/#website`,
  url: `${SITE.url}/`,
  name: SITE.name,
  inLanguage: SITE.lang,
  publisher: { '@id': `${SITE.url}/#organisation` },
  license: 'https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/',
  // No SearchAction: this site has no search endpoint, and claiming one would
  // put a broken sitelinks searchbox in front of users.
});

export const breadcrumbs = (trail) => ({
  '@type': 'BreadcrumbList',
  '@id': `${trail[trail.length - 1].url}#breadcrumbs`,
  itemListElement: trail.map((step, i) => ({
    '@type': 'ListItem',
    position: i + 1,
    name: step.name,
    item: step.url,
  })),
});

export const webPage = ({ url, title, description, trail, extra = {} }) => ({
  '@type': 'WebPage',
  '@id': `${url}#webpage`,
  url,
  name: title,
  description,
  inLanguage: SITE.lang,
  isPartOf: { '@id': `${SITE.url}/#website` },
  publisher: { '@id': `${SITE.url}/#organisation` },
  ...(trail ? { breadcrumb: { '@id': `${url}#breadcrumbs` } } : {}),
  ...extra,
});

/** One @graph per page: fewer scripts, and the nodes can reference each other. */
export const graph = (nodes) =>
  jsonld({ '@context': 'https://schema.org', '@graph': nodes.filter(Boolean) });

// ---------------------------------------------------------------- head tags

/**
 * Every tag a page needs to be indexed, canonicalised and shared.
 * `robots` defaults to full indexing; pass 'noindex, follow' for anything that
 * should be reachable but not competing in search.
 */
export const metaTags = ({
  url, title, description, image, type = 'website',
  robots = 'index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1',
  modified = null,
}) => {
  const t = [
    `<link rel="canonical" href="${url}">`,
    `<meta name="robots" content="${robots}">`,
    `<meta property="og:type" content="${type}">`,
    `<meta property="og:site_name" content="${SITE.name}">`,
    `<meta property="og:locale" content="${SITE.locale}">`,
    `<meta property="og:url" content="${url}">`,
    `<meta property="og:title" content="${title}">`,
    `<meta property="og:description" content="${description}">`,
    `<meta property="og:image" content="${image}">`,
    `<meta property="og:image:width" content="1200">`,
    `<meta property="og:image:height" content="630">`,
    `<meta property="og:image:alt" content="${title}">`,
    `<meta name="twitter:card" content="summary_large_image">`,
    `<meta name="twitter:title" content="${title}">`,
    `<meta name="twitter:description" content="${description}">`,
    `<meta name="twitter:image" content="${image}">`,
  ];
  if (SITE.twitterSite) t.push(`<meta name="twitter:site" content="${SITE.twitterSite}">`);
  if (modified) t.push(`<meta property="article:modified_time" content="${modified}">`);
  return t.join('\n');
};

// ---------------------------------------------------------------- sitemap

/**
 * urls: [{ path, changefreq, priority, lastmod }]
 * Only pages that are actually indexable belong here. A sitemap listing a
 * noindex page is a contradictory instruction, and search engines report it.
 */
export const sitemap = (urls) =>
  `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${urls.map(u => `  <url>
    <loc>${canonical(u.path)}</loc>${u.lastmod ? `
    <lastmod>${u.lastmod}</lastmod>` : ''}
    <changefreq>${u.changefreq || 'monthly'}</changefreq>
    <priority>${(u.priority ?? 0.5).toFixed(1)}</priority>
  </url>`).join('\n')}
</urlset>
`;

/**
 * robots.txt. Written for the case where this site is later served from its own
 * domain; at a project subpath a crawler will not read it, which is documented
 * rather than silently accepted.
 */
export const robots = () => `# ${SITE.name} — ${SITE.publisher}
#
# What ships is the app: the interfaces at / and /mobile.html, the data they
# read, and the system briefs they link to. What never ships is the engine in
# platform/ -- the fetchers, the source registry and the database -- and the
# operator console, which the publish workflow removes and then fails the build
# if it reappears.

User-agent: *
Allow: /

# The app renders from these at runtime. Blocking them would let a crawler load
# the page and see an application with no figures in it, which is worse than
# not being crawled at all.
Allow: ${SITE.base}/assets/
Allow: ${SITE.base}/data/

# Never deployed. Stated so that an accidental deploy is also disallowed.
Disallow: ${SITE.base}/platform/
Disallow: ${SITE.base}/research/
Disallow: ${SITE.base}/admin.html

Sitemap: ${SITE.url}/sitemap.xml
`;
