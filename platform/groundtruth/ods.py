"""Minimal OpenDocument spreadsheet reader.

CQC publishes its fullest location extract as .ods. The file is large, so rows
are streamed rather than held in memory, and repeated-cell runs are expanded
because ODS compresses runs of identical cells with a repeat attribute -- ignore
it and every column after the first blank run silently shifts.
"""
from __future__ import annotations

import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Iterator

NS = {
    "table": "urn:oasis:names:tc:opendocument:xmlns:table:1.0",
    "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
}
_REPEAT = "{%s}number-columns-repeated" % NS["table"]
_P = "{%s}p" % NS["text"]

# A single cell may claim a repeat of 1000+ to pad a row out to the sheet width.
# Expanding that faithfully would be correct but wasteful, so runs are capped.
MAX_REPEAT = 200


def rows(path: Path | str, *, max_rows: int | None = None) -> Iterator[list[str]]:
    with zipfile.ZipFile(path) as z:
        with z.open("content.xml") as fh:
            n = 0
            for _event, el in ET.iterparse(fh, events=("end",)):
                if not el.tag.endswith("}table-row"):
                    continue
                cells: list[str] = []
                for c in el.findall("table:table-cell", NS):
                    rep = int(c.get(_REPEAT, 1))
                    text = "".join(t.text or "" for t in c.iter(_P))
                    cells.extend([text] * min(rep, MAX_REPEAT))
                el.clear()
                yield cells
                n += 1
                if max_rows and n >= max_rows:
                    return


def table(path: Path | str, *, min_header_cells: int = 20):
    """Yield (header, row) pairs, skipping the preamble rows publishers add."""
    header: list[str] | None = None
    for cells in rows(path):
        populated = sum(1 for c in cells if c.strip())
        if header is None:
            if populated >= min_header_cells:
                header = cells
            continue
        if populated == 0:
            continue
        yield header, cells
