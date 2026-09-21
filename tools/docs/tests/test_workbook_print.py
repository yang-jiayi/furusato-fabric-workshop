"""Printed-workbook gate: identity survives horizontal tiling, and nothing collides.

The reference sheets are wider than one A4 page, so Excel tiles them. Anything
that identifies a sheet therefore has to be drawn per printed page, not placed in
a body row that the tile boundary slices. Two defects reached paper that way: the
Parameters_Core subtitle printed truncated on its continuation tiles, and the
64-character notebook digest never printed whole on any page at all.

The workbook is exported through Excel itself, so what is measured is what Excel
prints - not what openpyxl declares.

    python tools/docs/tests/test_workbook_print.py
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys

import fitz
import openpyxl
import win32com.client

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools" / "docs"))

from furusato_docs.deliverables import deliverable_names, validate_edition

WORKBOOK = ROOT / "docs" / "Furusato_Notebook_01-05_Processing_Specification_v2.7.0.xlsx"
SCRATCH = ROOT / ".workbook-print"

NOTEBOOK_SHEETS = ("NB01", "NB02", "NB03", "NB04", "NB05")
DIGEST = re.compile(r"[0-9a-f]{64}")

#: A page belongs to a notebook sheet when its header carries that sheet's digest.
HEADER_DIGEST = re.compile(r"File SHA-256:\s*([0-9a-f]{64})")


def export_pdf(workbook_path: pathlib.Path = WORKBOOK) -> pathlib.Path:
    SCRATCH.mkdir(exist_ok=True)
    target = (SCRATCH / "workbook.pdf").resolve()
    if target.exists():
        target.unlink()
    excel = win32com.client.DispatchEx("Excel.Application")
    excel.Visible = False
    excel.DisplayAlerts = False
    book = excel.Workbooks.Open(str(workbook_path.resolve()), ReadOnly=True)
    try:
        book.ExportAsFixedFormat(0, str(target))
    finally:
        book.Close(False)
        excel.Quit()
    return target


def collisions(page) -> list[str]:
    """Word boxes that overlap horizontally on the same printed line.

    Two words on one baseline whose boxes intersect are painting over each other,
    which is what a truncated-then-spilled cell looks like on paper.
    """
    found: list[str] = []
    words = page.get_text("words")
    lines: dict[tuple[int, int], list[tuple]] = {}
    for word in words:
        key = (round(word[1]), round(word[3]))
        lines.setdefault(key, []).append(word)
    for row in lines.values():
        row.sort(key=lambda w: w[0])
        for left, right in zip(row, row[1:]):
            if right[0] < left[2] - 0.6:
                found.append(f"{left[4]!r} over {right[4]!r}")
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--edition", default="", type=validate_edition)
    arguments = parser.parse_args()
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    workbook_path = ROOT / "docs" / deliverable_names(version, arguments.edition).workbook
    if not workbook_path.is_file():
        print(f"  FAIL workbook not found: {workbook_path}")
        return 1

    book = openpyxl.load_workbook(workbook_path)
    expected = {book[name]["B3"].value: book[name]["A1"].value for name in NOTEBOOK_SHEETS}
    core_title = str(book["Parameters_Core"]["A1"].value)
    core_subtitle = str(book["Parameters_Core"]["A2"].value)

    pdf_path = export_pdf(workbook_path)
    document = fitz.open(str(pdf_path))
    failures = 0
    notebook_tiles = 0
    core_tiles = 0
    problems: list[str] = []

    for index, page in enumerate(document, start=1):
        flat = page.get_text().replace("\n", "")
        header = HEADER_DIGEST.search(flat)
        if header:
            notebook_tiles += 1
            digest = header.group(1)
            if digest not in expected:
                problems.append(f"p{index}: header digest {digest[:12]} is not a shipped notebook")
            elif expected[digest] not in flat:
                problems.append(f"p{index}: {expected[digest]} name incomplete on the tile")
            elif len(DIGEST.findall(digest)) != 1:
                problems.append(f"p{index}: digest is not exactly 64 hex characters")
        if core_title in flat:
            core_tiles += 1
            if core_subtitle not in flat:
                problems.append(f"p{index}: Parameters_Core subtitle truncated on this tile")
        overlaps = collisions(page)
        if overlaps:
            problems.append(f"p{index}: {len(overlaps)} colliding word box(es), e.g. {overlaps[0]}")

    checks = (
        ("workbook.print.notebookIdentity", notebook_tiles >= len(NOTEBOOK_SHEETS),
         f"{notebook_tiles} notebook tiles carry a complete 64-hex digest in their page header"),
        ("workbook.print.coreSubtitle", core_tiles >= 1,
         f"{core_tiles} Parameters_Core tiles carry the complete subtitle"),
        ("workbook.print.noCollision", not problems,
         f"{document.page_count} printed pages, problems={problems[:3]}"),
    )
    for name, passed, detail in checks:
        print(f"  {'ok  ' if passed else 'FAIL'} {name}: {detail}")
        failures += 0 if passed else 1

    document.close()
    pdf_path.unlink(missing_ok=True)
    try:
        SCRATCH.rmdir()
    except OSError:
        pass

    print(f"\n{len(checks)} workbook print checks, {failures} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
