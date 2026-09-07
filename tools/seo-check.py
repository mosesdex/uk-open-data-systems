#!/usr/bin/env python3
"""Validate the published site's SEO. Run after `node build.js`.

Exits non-zero on any error, so it can gate a deploy. Warnings are printed and
do not fail: a title two characters over budget is worth knowing about and is
not worth blocking a release for.

    python3 tools/seo-check.py
"""
from __future__ import annotations

import json
import pathlib
import posixpath
import re
import sys
from html.parser import HTMLParser

ROOT = pathlib.Path(__file__).resolve().parent.parent
SITE = "https://ukgroundtruth.co.uk"

# The published set, mirroring what .github/workflows/pages.yml assembles.
# Globbing the repo would check pages that never ship (the proposal homepage at
# index.html) and miss the ones that do (the app, which serves from app/).
PUBLISHED = {
    "app/index.html": "",              # served at the root
    "app/mobile.html": "mobile.html",
    "platform.html": "platform.html",
    "research.html": "research.html",
    "examples.html": "examples.html",
    "about.html": "about.html",
    "404.html": "404.html",
    "app/admin.html": "admin.html",   # published, but noindex
}
for _s in sorted(ROOT.glob("systems/*.html")):
    PUBLISHED[f"systems/{_s.name}"] = f"systems/{_s.name}"

# Reachable, deliberately kept out of search: an error page and an operations
# console. Neither belongs in results, and neither goes in the sitemap.
NOINDEX = {"404.html", "app/admin.html"}

PAGES = [ROOT / rel for rel in PUBLISHED]

errors: list[str] = []
warnings: list[str] = []


def err(page, msg):
    errors.append(f"{page}: {msg}")


def warn(page, msg):
    warnings.append(f"{page}: {msg}")


class Headings(HTMLParser):
    def __init__(self):
        super().__init__()
        self.order: list[int] = []

    def handle_starttag(self, tag, attrs):
        if re.fullmatch(r"h[1-6]", tag):
            self.order.append(int(tag[1]))


def rel(p: pathlib.Path) -> str:
    return str(p.relative_to(ROOT))


def repo_path(served: str) -> pathlib.Path | None:
    """Where a published path lives in the repository.

    The publish step merges two trees into one: the app supplies /, /mobile.html,
    /assets and /data from app/, while the site supplies /systems, the
    explanatory pages and the rest of /assets. A checker that only looks at repo
    paths reports the app's own stylesheet as a broken link.
    """
    served = served.lstrip("/")
    for candidate in (ROOT / "app" / served, ROOT / served):
        if candidate.exists():
            return candidate
    if served in ("", "index.html"):
        return ROOT / "app" / "index.html"
    return None


def check_page(p: pathlib.Path) -> None:
    name = rel(p)
    h = p.read_text()

    title = re.search(r"<title>(.*?)</title>", h, re.S)
    desc = re.search(r'<meta name="description" content="(.*?)">', h, re.S)
    canon = re.findall(r'<link rel="canonical" href="([^"]+)">', h)
    robots = re.findall(r'<meta name="robots" content="([^"]+)">', h)

    if not title or not title.group(1).strip():
        err(name, "no <title>")
    elif len(title.group(1)) > 70:
        warn(name, f"title is {len(title.group(1))} chars; may be truncated")

    if not desc:
        err(name, "no meta description")
    elif not 70 <= len(desc.group(1)) <= 175:
        warn(name, f"description is {len(desc.group(1))} chars (aim 70-165)")

    if len(canon) != 1:
        err(name, f"expected exactly 1 canonical, found {len(canon)}")
    elif not canon[0].startswith(SITE):
        err(name, f"canonical is not an absolute site URL: {canon[0]}")
    else:
        served = PUBLISHED.get(name)
        expect = f"{SITE}/" if served == "" else f"{SITE}/{served}"
        if canon[0] != expect:
            err(name, f"canonical {canon[0]} does not match where the page is "
                      f"served ({expect})")

    if len(robots) != 1:
        err(name, f"expected exactly 1 robots meta, found {len(robots)}")
    elif name not in NOINDEX and "noindex" in robots[0]:
        err(name, "an indexable page carries noindex")
    elif name in NOINDEX and "noindex" not in robots[0]:
        err(name, f"{name} should be noindex")

    for prop in ("og:title", "og:description", "og:url", "og:image", "og:type"):
        if f'property="{prop}"' not in h:
            err(name, f"missing {prop}")
    for prop in ("twitter:card", "twitter:title", "twitter:image"):
        if f'name="{prop}"' not in h:
            err(name, f"missing {prop}")

    # og:image must point at a file that exists, or the preview is blank.
    for img in re.findall(r'<meta property="og:image" content="([^"]+)">', h):
        if repo_path(img.replace(SITE + "/", "")) is None:
            err(name, f"og:image does not exist: {img}")

    # Structured data must parse. Invalid JSON-LD is ignored silently by
    # crawlers, which is the worst failure mode: it looks implemented.
    indexable = not (robots and "noindex" in robots[0])
    blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', h, re.S)
    if not blocks and indexable:
        err(name, "no JSON-LD")
    for b in blocks:
        try:
            data = json.loads(b.replace("\\u003c", "<"))
        except json.JSONDecodeError as exc:
            err(name, f"JSON-LD does not parse: {exc}")
            continue
        nodes = data.get("@graph", [data])
        if "@context" not in data:
            err(name, "JSON-LD has no @context")
        for n in nodes:
            if "@type" not in n:
                err(name, f"JSON-LD node has no @type: {list(n)[:3]}")
        for n in nodes:
            if n.get("@type") == "BreadcrumbList":
                pos = [i["position"] for i in n["itemListElement"]]
                if pos != list(range(1, len(pos) + 1)):
                    err(name, f"breadcrumb positions are not sequential: {pos}")

    hp = Headings()
    hp.feed(h)
    h1s = [x for x in hp.order if x == 1]
    if len(h1s) != 1:
        err(name, f"expected exactly 1 h1, found {len(h1s)}")
    if hp.order and hp.order[0] != 1:
        warn(name, f"first heading is h{hp.order[0]}, not h1")
    for a, b in zip(hp.order, hp.order[1:]):
        if b > a + 1:
            warn(name, f"heading level jumps h{a} -> h{b}")
            break

    # Images need alt text and intrinsic dimensions.
    for tag in re.findall(r"<img\b[^>]*>", h):
        if "alt=" not in tag:
            err(name, f"image without alt: {tag[:70]}")
        if "width=" not in tag or "height=" not in tag:
            warn(name, f"image without width/height (layout shift): {tag[:70]}")

    # The app's containers ship empty and fill from JavaScript. If the static
    # copy ever stops being generated, the page silently loses almost all of
    # its crawlable content while still looking perfectly fine in a browser.
    if name in ("app/index.html", "app/mobile.html"):
        if "<!-- generated:static-content -->" not in h:
            err(name, "static content block is missing; run: node tools/app-content.mjs")
        else:
            body = re.sub(r"(?is)<script.*?</script>|<style.*?</style>", " ", h)
            wordcount = len(re.sub(r"\s+", " ", re.sub(r"(?s)<[^>]+>", " ", body)).split())
            if wordcount < 250:
                err(name, f"only {wordcount} words of crawlable HTML; the app's "
                          "content is not reaching non-rendering crawlers")

    # The operational system must never be linked from the public site.
    for bad in ("app/index.html", "app/admin.html", "app/mobile.html"):
        if bad in h:
            err(name, f"links to the local-only system: {bad}")

    # Internal links must resolve.
    for href in re.findall(r'href="([^"#?][^"]*?)"', h):
        if href.startswith(("http://", "https://", "mailto:", "data:", "//")):
            continue
        raw = href.split("#")[0].split("?")[0]
        if not raw:
            continue
        # A template placeholder is a link built at runtime, not a link in the
        # document. The values these produce are checked against the live site.
        if "${" in raw or "{{" in raw:
            continue
        # An app page is served from the root, so '../systems/x' from it lands
        # at '/systems/x'. Resolve against the served path, not the repo path.
        served = PUBLISHED.get(name, name)
        # Resolve against the served location, then map back into the repo. A
        # '../systems/x' link from a root-served app page lands at '/systems/x',
        # which the browser clamps to the site root.
        base = posixpath.dirname("/" + served)
        # normpath applies '..' properly and clamps it at the root, which is
        # exactly what a browser does with '../systems/x' on a root-served page.
        landed = posixpath.normpath(posixpath.join(base, raw)).lstrip("/")
        if repo_path(landed or "index.html") is None:
            err(name, f"broken internal link: {href} (serves as /{landed})")


def check_site() -> None:
    sm = ROOT / "sitemap.xml"
    if not sm.is_file():
        err("sitemap.xml", "missing")
        return
    locs = re.findall(r"<loc>([^<]+)</loc>", sm.read_text())
    if not locs:
        err("sitemap.xml", "contains no URLs")
    if len(locs) != len(set(locs)):
        err("sitemap.xml", "contains duplicate URLs")

    for loc in locs:
        if not loc.startswith(SITE):
            err("sitemap.xml", f"URL outside the site: {loc}")
            continue
        path = loc[len(SITE) + 1:]
        if repo_path(path or "index.html") is None:
            err("sitemap.xml", f"lists a page that does not exist: /{path}")

    # Every canonical URL on the site should appear in the sitemap, and vice
    # versa: an indexable page missing from the sitemap is a page nobody asked
    # to have crawled.
    canonicals = set()
    for p in PAGES:
        h = p.read_text()
        if "noindex" in (re.findall(r'<meta name="robots" content="([^"]+)">', h) or [""])[0]:
            continue
        canonicals |= set(re.findall(r'<link rel="canonical" href="([^"]+)">', h))
    missing = canonicals - set(locs)
    if missing:
        err("sitemap.xml", f"indexable pages not listed: {sorted(missing)}")
    extra = set(locs) - canonicals
    if extra:
        err("sitemap.xml", f"lists pages that are not canonical anywhere: {sorted(extra)}")

    rb = ROOT / "robots.txt"
    if not rb.is_file():
        err("robots.txt", "missing")
    else:
        text = rb.read_text()
        if "Sitemap:" not in text:
            err("robots.txt", "does not reference the sitemap")
        if re.search(r"^Disallow:\s*/\s*$", text, re.M):
            err("robots.txt", "disallows the whole site")
        # Anything the pages fetch at runtime must stay crawlable. A blocked
        # payload lets a crawler render the app with no figures in it, which
        # looks like an empty product rather than a blocked resource.
        disallowed = [ln.split(":", 1)[1].strip()
                      for ln in text.splitlines()
                      if ln.strip().lower().startswith("disallow:")
                      and ln.split(":", 1)[1].strip()]
        runtime = set()
        for page in PAGES:
            body = page.read_text()
            runtime |= set(re.findall(r"""fetch\(\s*['"`]([^'"`?]+)""", body))
            runtime |= set(re.findall(r'data-geo="([^"]+)"', body))
        for src in ROOT.glob("app/assets/*.js"):
            body = src.read_text()
            runtime |= set(re.findall(r"""fetch\(\s*['"`]([^'"`?$]+)""", body))
            runtime |= set(re.findall(r"""=\s*['"]([\w./-]+\.json)['"]""", body))
        for res in sorted(runtime):
            served = "/" + res.lstrip("./")
            for rule in disallowed:
                if served.startswith(rule.rstrip("*")):
                    err("robots.txt", f"blocks {served}, which the app fetches "
                                      f"at runtime (rule: Disallow: {rule})")
        for asset in ("assets/style.css", "assets/app.css", "assets/app.js"):
            if re.search(rf"^Disallow:.*{re.escape(asset)}", text, re.M):
                err("robots.txt", f"blocks a render-critical asset: {asset}")

    if not (ROOT / "404.html").is_file():
        err("404.html", "missing")

    # Canonicals must be unique across pages: two pages claiming one canonical
    # is a request to de-index one of them.
    seen: dict[str, str] = {}
    for p in PAGES:
        for c in re.findall(r'<link rel="canonical" href="([^"]+)">', p.read_text()):
            if c in seen:
                err(rel(p), f"shares its canonical with {seen[c]}: {c}")
            seen[c] = rel(p)


def main() -> int:
    for p in PAGES:
        check_page(p)
    check_site()

    print(f"checked {len(PAGES)} pages")
    for w in warnings:
        print(f"  warn   {w}")
    for e in errors:
        print(f"  ERROR  {e}")
    print(f"\n{len(errors)} errors, {len(warnings)} warnings")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
