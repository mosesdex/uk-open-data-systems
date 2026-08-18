"""Reading insolvency notices.

The research claim being relied on: a Gazette notice carries a *structured*
company number, so an exposure question can be answered without matching on
company name -- the hardest and least reliable join in UK data.

This module extracts (company_number, company_name, notice_type) from the
published feed so that claim can be measured rather than assumed.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

# Numbers appear inside the notice body, usually parenthesised after the name.
NUMBER_IN_TEXT = re.compile(r"\(\s*((?:[A-Z]{2})?\d{6,8})\s*\)")
COMPANY_NUMBER_ANY = re.compile(r"\b((?:SC|NI|OC|SO|NC|FC|GE|IP|RS)?\d{6,8})\b")
TAG = re.compile(r"<[^>]+>")
# Notices that omit the number still print a registered address. The postcode in
# it lets the place spine locate a company the entity spine could not identify.
POSTCODE_IN_TEXT = re.compile(
    r"\b([A-Z]{1,2}\d[A-Z\d]?)\s+(\d[A-Z]{2})\b"
)


@dataclass(frozen=True)
class Notice:
    notice_id: str
    title: str
    company_number: str | None
    notice_type: str
    published: str
    postcode: str | None = None

    @property
    def identified(self) -> bool:
        return self.company_number is not None

    @property
    def locatable(self) -> bool:
        """True when the place spine can locate this even without an identifier."""
        return self.postcode is not None


def _text(html: str) -> str:
    return TAG.sub(" ", html or "")


def parse(path: Path) -> list[Notice]:
    doc = json.loads(Path(path).read_text())
    out: list[Notice] = []
    for e in doc.get("entry", []):
        content = e.get("content")
        if isinstance(content, dict):
            content = content.get("#text", "")
        body = _text(content or "")
        m = NUMBER_IN_TEXT.search(body) or COMPANY_NUMBER_ANY.search(body)
        cat = e.get("category")
        ntype = cat.get("@term", "") if isinstance(cat, dict) else str(cat or "")
        pc = POSTCODE_IN_TEXT.search(body.upper())
        out.append(Notice(
            notice_id=str(e.get("id", "")),
            title=(e.get("title") or "").strip(),
            company_number=m.group(1) if m else None,
            notice_type=ntype,
            published=str(e.get("published", "")),
            postcode=f"{pc.group(1)} {pc.group(2)}" if pc else None,
        ))
    return out
