# SEO

Everything search engines see is generated. There is no page with hand-written
metadata, because a hand-written tag is one that goes stale the first time a
system is added.

```bash
node build.js              # pages + sitemap.xml + robots.txt + 404.html
python3 tools/social-cards.py   # 23 Open Graph images, after a content change
python3 tools/seo-check.py      # validate; exits non-zero on error
```

## Where things live

| Concern | File |
|---|---|
| Site config, canonicals, JSON-LD, meta tags, sitemap, robots | `data/seo.js` |
| Page assembly (calls into the above) | `build.js` |
| Social card generation | `tools/social-cards.py` |
| Validation | `tools/seo-check.py` |
| Publish + guards | `.github/workflows/pages.yml` |

Adding a system to `data/systems-*.js` is enough. It gets a title, description,
canonical, robots directive, Open Graph and Twitter tags, a `WebPage` and
`BreadcrumbList` graph, a sitemap entry and a social card with no further work.
`tools/seo-check.py` fails if any of those are missing.

## What is deliberately not marked up

Structured data describes only what a page contains. Absent, and why:

- **SearchAction** — the site has no search endpoint. Declaring one puts a
  sitelinks searchbox in front of users that cannot work.
- **FAQPage** — `examples.html` holds problem/solution pairs, not questions and
  answers. It reads like an FAQ and is not one.
- **Product, Review, Event, LocalBusiness, Person** — the site sells nothing,
  carries no reviews, hosts no events, has no premises page and no bylined
  author. Marking any of them up would be inventing content.
- **Article author / datePublished** — the pages carry no bylines or publication
  dates, so neither is asserted.

## The domain

The site is served from **https://ukgroundtruth.co.uk**, its own apex domain, so
it sits at the origin root. That is what makes `robots.txt` effective: a
robots.txt is only ever honoured at the root, which a GitHub Pages project
subpath could not satisfy. The constraint recorded in the first version of this
file is resolved.

`CNAME` in the repository root holds the domain and the publish workflow copies
it into the artifact — GitHub Pages will not serve a custom domain without it.

### DNS at Hostinger

Point the apex at GitHub Pages' four addresses, and `www` at the Pages host.
In hPanel: **Domains → DNS / Nameservers → Manage DNS records**.

| Type | Name | Value | TTL |
|---|---|---|---|
| A | `@` | `185.199.108.153` | 3600 |
| A | `@` | `185.199.109.153` | 3600 |
| A | `@` | `185.199.110.153` | 3600 |
| A | `@` | `185.199.111.153` | 3600 |
| CNAME | `www` | `mosesdex.github.io.` | 3600 |

Delete any existing A or CNAME record on `@` or `www` first — Hostinger parks
new domains on its own page, and a leftover record will win.

Then in the repository: **Settings → Pages → Custom domain**, enter
`ukgroundtruth.co.uk`, save, and tick **Enforce HTTPS** once the certificate is
issued. The certificate is issued after DNS resolves, which is usually minutes
and can take up to a day.

Verify from a terminal:

```bash
dig +short ukgroundtruth.co.uk A          # the four 185.199.x addresses
curl -sI https://ukgroundtruth.co.uk/     # HTTP/2 200
curl -s  https://ukgroundtruth.co.uk/robots.txt | head -1
```

### If the domain ever moves again

Nothing is hardcoded. The build takes both values from the environment:

```bash
SITE_ORIGIN=https://example.com SITE_BASE= node build.js
python3 tools/social-cards.py
python3 tools/seo-check.py
```

Update `CNAME`, and the `SITE` constant at the top of `tools/seo-check.py`.

## Guards in CI

The publish workflow refuses to ship if:

- `app/`, `platform/`, `data/` or `research/` reach the output
- any published page links to the local-only system
- the sitemap lists a page that is not in the artifact

`tools/seo-check.py` additionally verifies, for all 23 pages: one `h1`, no
heading-level jumps, exactly one canonical, unique canonicals across the site,
present and parseable JSON-LD, sequential breadcrumb positions, an `og:image`
that exists on disk, no `noindex` on an indexable page, resolving internal
links, and sitemap/canonical agreement in both directions.
