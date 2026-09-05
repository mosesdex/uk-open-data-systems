#!/usr/bin/env python3
"""Generate the Open Graph / Twitter card images.

One 1200x630 PNG per indexable page, drawn from the same content modules the
pages themselves are built from, so a new system cannot ship with a missing or
mismatched card. Run after a content change:

    python3 tools/social-cards.py

The cards are committed rather than generated in CI: they change rarely, the
publish workflow copies static files only, and a card that fails to build in CI
would silently ship a broken preview.
"""
from __future__ import annotations

import json
import pathlib
import re
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "social"

W, H = 1200, 630
INK = (14, 20, 33)
PAPER = (247, 248, 250)
ACCENT = (29, 78, 216)
MUTED = (110, 122, 140)
RULE = (222, 227, 235)

BOLD = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
REG = "/System/Library/Fonts/Supplemental/Arial.ttf"
MONO = "/System/Library/Fonts/Menlo.ttc"


def font(path: str, size: int):
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.load_default()


def wrap(draw, text: str, f, max_w: int, max_lines: int = 3) -> list[str]:
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = f"{cur} {w}".strip()
        if draw.textlength(trial, font=f) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
            if len(lines) == max_lines:
                break
    if cur and len(lines) < max_lines:
        lines.append(cur)
    if len(lines) == max_lines and draw.textlength(lines[-1], font=f) > max_w - 40:
        lines[-1] = lines[-1][:-3] + "…"
    return lines


def card(eyebrow: str, title: str, subtitle: str, dest: pathlib.Path) -> None:
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)

    # A single accent bar across the top, and the brand mark bottom-left. The
    # card is deliberately plain: it is read at thumbnail size in a feed.
    d.rectangle([0, 0, W, 10], fill=ACCENT)

    x, y = 84, 96
    f_eye = font(MONO, 24)
    f_title = font(BOLD, 78)
    f_sub = font(REG, 32)
    f_brand = font(BOLD, 28)
    f_foot = font(REG, 24)

    if eyebrow:
        d.text((x, y), eyebrow.upper(), font=f_eye, fill=ACCENT)
        y += 54

    for line in wrap(d, title, f_title, W - 2 * x, max_lines=2):
        d.text((x, y), line, font=f_title, fill=INK)
        y += 88

    if subtitle:
        y += 14
        for line in wrap(d, subtitle, f_sub, W - 2 * x, max_lines=3):
            d.text((x, y), line, font=f_sub, fill=MUTED)
            y += 44

    d.line([(x, H - 118), (W - x, H - 118)], fill=RULE, width=2)
    d.rounded_rectangle([x, H - 88, x + 46, H - 42], radius=11, fill=ACCENT)
    d.text((x + 14, H - 82), "G", font=f_brand, fill=PAPER)
    d.text((x + 62, H - 79), "UK GroundTruth", font=f_brand, fill=INK)
    d.text((W - x - d.textlength("Dexter DCL", font=f_foot), H - 77),
           "Dexter DCL", font=f_foot, fill=MUTED)

    dest.parent.mkdir(parents=True, exist_ok=True)
    img.save(dest, "PNG", optimize=True)


def systems() -> list[dict]:
    """Read the content modules through node, so this stays the single source."""
    script = (
        "const load=async()=>{const A=(await import('./data/systems-a.js')).default,"
        "B=(await import('./data/systems-b.js')).default,"
        "C=(await import('./data/systems-c.js')).default;"
        "console.log(JSON.stringify([...A,...B,...C].map(s=>"
        "({id:s.id,num:s.num,name:s.name,subtitle:s.subtitle}))));};load();"
    )
    out = subprocess.run(["node", "--input-type=module", "-e", script],
                         cwd=ROOT, capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


PAGES = [
    ("default", "", "UK GroundTruth",
     "One platform, thirteen public data systems. Every source open to an anonymous request."),
    ("index", "", "UK GroundTruth",
     "UK government records what happened. It rarely records where, or which organisation."),
    ("platform", "Architecture", "Two joins, one platform",
     "Resolve place and resolve entity once, as public infrastructure, and thirteen systems become possible."),
    ("research", "Research", "What is actually open",
     "An access audit of 101 UK government endpoints. 69 returned data to an anonymous request."),
    ("examples", "Problems and solutions", "One problem, thirteen times",
     "Two real situations for every system: what goes wrong today, and what the system does about it."),
]


def main() -> int:
    made = 0
    for slug, eyebrow, title, sub in PAGES:
        card(eyebrow, title, sub, OUT / f"{slug}.png")
        made += 1
    for s in systems():
        card(f"System {s['num']}", s["name"], s["subtitle"], OUT / f"{s['id']}.png")
        made += 1
    print(f"wrote {made} cards to {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
