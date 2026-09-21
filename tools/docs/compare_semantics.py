"""Prove that a rebuild changed only package metadata.

A metadata-only pass must leave the *content* of the deliverables untouched: the
same words, the same tables, the same pictures, the same pagination, the same
workbook cells. Comparing file digests cannot show that, because rewriting a
single property changes the digest of the whole ZIP.

This tool reduces each deliverable to a semantic fingerprint that deliberately
excludes everything a metadata pass is allowed to touch — core, app and custom
properties, the classification part, and ZIP member order and timestamps — then
compares two snapshots.

    python tools\\docs\\compare_semantics.py --save before.json
    ... rebuild ...
    python tools\\docs\\compare_semantics.py --compare before.json

Snapshots are written wherever the caller asks; nothing is left in the repository.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree

sys.path.insert(0, str(Path(__file__).resolve().parent))

from furusato_docs.console import use_utf8_streams  # noqa: E402
from furusato_docs.context import repo_root  # noqa: E402
from furusato_docs.deliverables import deliverable_names, validate_edition  # noqa: E402

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

#: Parts a metadata-only pass is allowed to rewrite. Everything else must match.
VOLATILE_PARTS = {
    "docProps/core.xml",
    "docProps/app.xml",
    "docProps/custom.xml",
    "docMetadata/LabelInfo.xml",
    "[Content_Types].xml",
    "_rels/.rels",
}

CHECKLIST = "docs/data-validation-checklist.md"


def _digest(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def _strip_ids(xml: str) -> str:
    """Drop the identifiers Word and Excel regenerate on every save.

    ``w14:paraId``/``w14:textId`` and the ``w:rsid*`` table are revision-save
    bookkeeping, ``w:nsid``/``w16cid:durableId`` identify numbering instances,
    ``wp14:anchorId``/``wp14:editId`` identify drawing anchors, ``w14:docId`` and
    ``xr:uid`` identify the file itself, ``_Toc*`` bookmarks are renumbered every
    time the contents listing is rebuilt, and ``calcId``/``fileVersion`` record
    which Excel build last wrote the workbook. Office also normalises explicit
    ``w:val="true"`` booleans to the bare element. Every one of these is assigned
    randomly on save and says nothing about the content of the document.
    """
    xml = re.sub(r'\s+w14:(paraId|textId)="[0-9A-Fa-f]+"', "", xml)
    xml = re.sub(r'\s+wp14:(anchorId|editId)="[0-9A-Fa-f]+"', "", xml)
    xml = re.sub(r'\s+w16cid:durableId="\d+"', "", xml)
    xml = re.sub(r'\s+w:rsid[A-Za-z]*="[0-9A-Fa-f]+"', "", xml)
    xml = re.sub(r"<w:rsids>.*?</w:rsids>", "", xml, flags=re.DOTALL)
    xml = re.sub(r"<w:rsid\b[^>]*/>", "", xml)
    xml = re.sub(r"<w:nsid\b[^>]*/>", "", xml)
    xml = re.sub(r"<w14:docId\b[^>]*/>", "", xml)
    xml = re.sub(r'\s+xr:uid="\{[0-9A-Fa-f-]+\}"', "", xml)
    xml = re.sub(r"_Toc\d+", "_Toc", xml)
    xml = re.sub(r'\s+w:val="(?:true|1)"(\s*/?>)', r"\1", xml)
    xml = re.sub(r"<fileVersion\b[^>]*/>", "", xml)
    return re.sub(r'\s+calcId="\d+"', "", xml)


def snapshot_document(path: Path) -> dict[str, object]:
    with zipfile.ZipFile(path) as archive:
        parts = {name: archive.read(name) for name in archive.namelist()}

    tree = ElementTree.fromstring(parts["word/document.xml"])
    paragraphs = []
    tables = []
    for paragraph in tree.iter(f"{W}p"):
        text = "".join(node.text or "" for node in paragraph.iter(f"{W}t"))
        if text.strip():
            paragraphs.append(text)
    for table in tree.iter(f"{W}tbl"):
        rows = []
        for row in table.findall(f"{W}tr"):
            rows.append(
                [
                    "".join(node.text or "" for node in cell.iter(f"{W}t")).strip()
                    for cell in row.findall(f"{W}tc")
                ]
            )
        tables.append(rows)

    media = {
        name: _digest(blob)
        for name, blob in sorted(parts.items())
        if name.startswith("word/media/")
    }
    alt_text = sorted(
        (node.get("name", ""), node.get("descr", ""))
        for node in tree.iter("{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}docPr")
    )
    toc_entries = [
        text
        for text in paragraphs
        if re.match(r"^(第\s*\d|付録\s*[A-Z]|\d+\.\s)", text.strip())
    ]
    stable_parts = {
        name: _digest(_strip_ids(blob.decode("utf-8")).encode("utf-8") if name.endswith(".xml") else blob)
        for name, blob in sorted(parts.items())
        if name not in VOLATILE_PARTS
    }
    return {
        "paragraphCount": len(paragraphs),        "paragraphDigest": _digest("\n".join(paragraphs).encode("utf-8")),
        "tableCount": len(tables),
        "tableDigest": _digest(json.dumps(tables, ensure_ascii=False).encode("utf-8")),
        "media": media,
        "altTextDigest": _digest(json.dumps(alt_text, ensure_ascii=False).encode("utf-8")),
        "tocEntryCount": len(toc_entries),
        "stableParts": stable_parts,
    }


def snapshot_workbook(path: Path) -> dict[str, object]:
    from openpyxl import load_workbook

    book = load_workbook(path, data_only=False)
    sheets: dict[str, object] = {}
    for sheet in book.worksheets:
        cells = [
            [cell.coordinate, str(cell.value), cell.number_format]
            for row in sheet.iter_rows()
            for cell in row
            if cell.value is not None
        ]
        sheets[sheet.title] = {
            "cells": _digest(json.dumps(cells, ensure_ascii=False).encode("utf-8")),
            "cellCount": len(cells),
            "merged": sorted(str(area) for area in sheet.merged_cells.ranges),
            "columnWidths": {key: round(value.width or 0, 2) for key, value in sorted(sheet.column_dimensions.items())},
            "printArea": sheet.print_area,
            "printTitles": sheet.print_title_rows,
            "paperSize": str(sheet.page_setup.paperSize),
            "orientation": sheet.page_setup.orientation,
            "freezePanes": sheet.freeze_panes,
            "autoFilter": str(sheet.auto_filter.ref) if sheet.auto_filter.ref else None,
            "conditionalFormats": len(list(sheet.conditional_formatting)),
        }
    with zipfile.ZipFile(path) as archive:
        stable_parts = {
            name: _digest(
                _strip_ids(archive.read(name).decode("utf-8")).encode("utf-8")
                if name.endswith(".xml")
                else archive.read(name)
            )
            for name in sorted(archive.namelist())
            if name not in VOLATILE_PARTS
        }
    return {"sheets": sheets, "stableParts": stable_parts}


def build_snapshot(root: Path, edition: str = "") -> dict[str, object]:
    snapshot: dict[str, object] = {}
    version = (root / "VERSION").read_text(encoding="utf-8").strip()
    names = deliverable_names(version, edition)
    for name in (names.participant, names.validation):
        relative = f"docs/{name}"
        snapshot[relative] = snapshot_document(root / relative)
    workbook = f"docs/{names.workbook}"
    snapshot[workbook] = snapshot_workbook(root / workbook)
    snapshot[CHECKLIST] = {"sha256": _digest((root / CHECKLIST).read_bytes())}
    return snapshot


def _differences(before: object, after: object, path: str = "") -> list[str]:
    if isinstance(before, dict) and isinstance(after, dict):
        found: list[str] = []
        for key in sorted(set(before) | set(after)):
            if key not in before:
                found.append(f"{path}/{key}: added")
            elif key not in after:
                found.append(f"{path}/{key}: removed")
            else:
                found.extend(_differences(before[key], after[key], f"{path}/{key}"))
        return found
    if before != after:
        return [f"{path}: {before!r} -> {after!r}"]
    return []


def _content_only(snapshot: dict) -> dict:
    """Drop the raw-part digests, keeping only what the reader actually sees.

    Used to compare across a change to the normaliser itself, where the raw-part
    digests are not comparable but the content fingerprints still are.
    """
    return {
        name: {key: value for key, value in entry.items() if key != "stableParts"}
        for name, entry in snapshot.items()
    }


def main() -> int:
    use_utf8_streams()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--edition", default="", type=validate_edition, help="Named correction edition")
    parser.add_argument("--save", type=Path, help="Write a snapshot of the current deliverables")
    parser.add_argument("--compare", type=Path, help="Compare the current deliverables against a snapshot")
    parser.add_argument(
        "--content-only",
        action="store_true",
        help="Compare only the reader-visible fingerprints, ignoring raw OOXML part digests",
    )
    arguments = parser.parse_args()

    root = repo_root()
    snapshot = build_snapshot(root, arguments.edition)

    if arguments.save:
        arguments.save.parent.mkdir(parents=True, exist_ok=True)
        arguments.save.write_text(json.dumps(snapshot, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"snapshot written: {arguments.save}")
        return 0

    if arguments.compare:
        previous = json.loads(arguments.compare.read_text(encoding="utf-8"))
        current = snapshot
        if arguments.content_only:
            previous, current = _content_only(previous), _content_only(snapshot)
        differences = _differences(previous, current)
        if differences:
            print(f"{len(differences)} semantic difference(s):")
            for line in differences[:60]:
                print(f"  {line}")
            return 1
        scope = "content, tables, media, alt text and workbook cells" if arguments.content_only else (
            "content, tables, media, alt text, workbook cells and every non-metadata OOXML part"
        )
        print(f"no semantic differences: {scope} are identical")
        return 0

    print(json.dumps(snapshot, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
