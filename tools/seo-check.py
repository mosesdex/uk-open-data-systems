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
import re
import sys
from html.parser import HTMLParser

ROOT = pathlib.Path(__file__).resolve().parent.parent
SITE = "https://ukgroundtruth.co.uk"

PAGES = sorted(p for p in ROOT.glob("*.html")) + sorted(ROOT.glob("systems/*.html"))

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

    if len(robots) != 1:
        err(name, f"expected exactly 1 robots meta, found {len(robots)}")
    elif name != "404.html" and "noindex" in robots[0]:
        err(name, "an indexable page carries noindex")
    elif name == "404.html" and "noindex" not in robots[0]:
        err(name, "the error page should be noindex")

    for prop in ("og:title", "og:description", "og:url", "og:image", "og:type"):
        if f'property="{prop}"' not in h:
            err(name, f"missing {prop}")
    for prop in ("twitter:card", "twitter:title", "twitter:image"):
        if f'name="{prop}"' not in h:
            err(name, f"missing {prop}")

    # og:image must point at a file that exists, or the preview is blank.
    for img in re.findall(r'<meta property="og:image" content="([^"]+)">', h):
        local = ROOT / img.replace(SITE + "/", "")
        if not local.is_file():
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

    # The operational system must never be linked from the public site.
    for bad in ("app/index.html", "app/admin.html", "app/mobile.html"):
        if bad in h:
            err(name, f"links to the local-only system: {bad}")

    # Internal links must resolve.
    for href in re.findall(r'href="([^"#?][^"]*?)"', h):
        if href.startswith(("http://", "https://", "mailto:", "data:", "//")):
            continue
        target = (p.parent / href.split("#")[0].split("?")[0]).resolve()
        if not target.exists():
            err(name, f"broken internal link: {href}")


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
        path = loc[len(SITE) + 1:] or "index.html"
        if not (ROOT / path).is_file():
            err("sitemap.xml", f"lists a page that does not exist: {path}")

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
        for asset in ("assets/style.css", "assets/app.js"):
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
