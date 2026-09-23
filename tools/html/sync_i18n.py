"""Report the drift between the canonical Word content model and the English mirror.

Maintenance helper. It never writes to ``tools/docs`` or ``docs``; it only tells
you which Japanese strings still need an English mirror (and which mirror
entries the guide no longer uses), so the bilingual HTML can be brought back in
step after the Word guide changes.

    python tools/html/sync_i18n.py                 # human summary
    python tools/html/sync_i18n.py --json out.json # machine-readable delta
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT / "tools" / "docs"))
sys.path.insert(0, str(HERE))

from furusato_docs.context import load_context  # noqa: E402
from furusato_docs.deliverables import validate_edition  # noqa: E402
from furusato_docs.facts import compute_facts  # noqa: E402
from furusato_docs.oox import StyleCarrier  # noqa: E402
from furusato_docs.tests10 import build_tests  # noqa: E402

from furusato_html.capture import capture_participant_guide  # noqa: E402
from furusato_html.mirror import load_mirror, suspicious_english  # noqa: E402
from furusato_html.model import build_document  # noqa: E402


def collect(
    root: Path, *, public_documents_only: bool = False, context=None, document_edition: str = ""
) -> dict[str, object]:
    context = context or load_context(root, document_edition=document_edition)
    facts = compute_facts(context)
    tests = build_tests(context, facts)
    carrier = StyleCarrier.resolve(root)
    capture = capture_participant_guide(
        context, facts, tests, carrier, public_documents_only=public_documents_only
    )

    mirror = load_mirror(strict=False, public_documents_only=public_documents_only, context=context)
    document = build_document(capture.nodes, mirror)

    chapter_of: dict[str, str] = {}
    role_of: dict[str, str] = {}
    order: list[str] = []
    seen: set[str] = set()
    chapter = ""
    for node in capture.nodes:
        if node.kind == "heading" and node["level"] == 1:
            chapter = node["text"]
        for text, role in _strings(node):
            if not text or text in seen:
                continue
            seen.add(text)
            order.append(text)
            chapter_of[text] = chapter
            role_of[text] = role

    missing = [
        {"ja": text, "chapter": chapter_of.get(text, ""), "role": role_of.get(text, "")}
        for text in mirror.missing
    ]
    return {
        "missing": missing,
        "unused": mirror.unused(),
        "suspicious": suspicious_english(mirror.entries),
        "translated": len(mirror.entries),
        "neutral": len(mirror.neutral),
        "sections": sum(1 for _ in document.walk()),
        "order": order,
    }


def _strings(node) -> list[tuple[str, str]]:
    kind = node.kind
    if kind == "heading":
        return [(node["text"], f"heading level {node['level']}")]
    if kind in ("body", "paragraph"):
        return [(node["text"], "paragraph")]
    if kind == "bullets":
        role = "list item (numbered)" if node["numbered"] else "list item"
        return [(item, role) for item in node["items"]]
    if kind == "callout":
        out = [(node["text"], f"callout body ({node['tone']})")]
        if node.get("title"):
            out.append((node["title"], "callout title"))
        return out
    if kind == "code":
        return [(node["language"], "code block language label")] if node.get("language") else []
    if kind == "table":
        caption = node["caption"]
        out = [(caption, "table caption")]
        out += [(h, f"table column header (table: {caption[:40]})") for h in node["headers"]]
        for row in node["rows"]:
            out += [(cell, f"table cell (table: {caption[:40]})") for cell in row]
        return out
    if kind == "figure":
        return [
            (node["caption"], "figure caption"),
            (node["alt"], "figure alt text (describes the image for screen readers)"),
        ]
    return []


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", default=None, help="write the delta to this JSON file")
    parser.add_argument("--edition", default="", type=validate_edition, help="Document edition to inspect")
    parser.add_argument(
        "--public-documents-only", action="store_true",
        help="Check the explicit public-mode mirror overlay without modifying full-authoring translations",
    )
    parser.add_argument(
        "--prune",
        action="store_true",
        help="drop mirror entries the content model no longer uses",
    )
    parser.add_argument(
        "--rewrite",
        action="store_true",
        help="rewrite the guide-*.json chunks in document order (no content change)",
    )
    args = parser.parse_args(argv)
    if args.public_documents_only and (args.prune or args.rewrite):
        parser.error("public-mode drift is read-only; edit public-documents.json explicitly")
    if args.edition == "unified-20260923" and (args.prune or args.rewrite):
        parser.error("unified-mode drift is read-only; edit unified-documents.json explicitly")

    delta = collect(
        ROOT, public_documents_only=args.public_documents_only, document_edition=args.edition
    )
    if args.json:
        payload = {key: value for key, value in delta.items() if key != "order"}
        Path(args.json).write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")

    if args.prune and delta["unused"]:
        removed = _prune(set(delta["unused"]))
        print(f"pruned {removed} obsolete mirror entries")
        delta["unused"] = []

    if args.rewrite:
        if delta["missing"]:
            print("refusing to rewrite while mirrors are missing; add them first")
            return 1
        chunks = _rewrite(list(delta["order"]))
        print(f"rewrote {chunks} chunk files in document order")

    print(f"mirror entries      {delta['translated']}")
    print(f"language-neutral    {delta['neutral']}")
    print(f"missing mirrors     {len(delta['missing'])}")
    print(f"unused mirrors      {len(delta['unused'])}")
    print(f"suspicious values   {len(delta['suspicious'])}")
    for item in delta["missing"][:15]:
        print(f"  + {item['ja'][:90]}")
    for item in delta["unused"][:15]:
        print(f"  - {item[:90]}")
    return 1 if (delta["missing"] or delta["unused"] or delta["suspicious"]) else 0


def _prune(unused: set[str]) -> int:
    directory = HERE / "furusato_html" / "i18n"
    removed = 0
    for path in sorted(directory.glob("guide-*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        kept = {key: value for key, value in payload.items() if key not in unused}
        if len(kept) == len(payload):
            continue
        removed += len(payload) - len(kept)
        if kept:
            path.write_text(
                json.dumps(kept, ensure_ascii=False, indent=1) + "\n",
                encoding="utf-8",
                newline="\n",
            )
        else:
            path.unlink()
    return removed


#: Chunk size chosen purely for reviewability of a diff; it carries no meaning.
CHUNK_SIZE = 150


def _rewrite(order: list[str]) -> int:
    """Re-emit the mirror as document-ordered chunks, unchanged in content."""
    directory = HERE / "furusato_html" / "i18n"
    merged: dict[str, str] = {}
    for path in sorted(directory.glob("guide-*.json")):
        merged.update(json.loads(path.read_text(encoding="utf-8")))

    ordered = [key for key in order if key in merged]
    remainder = sorted(set(merged) - set(ordered))
    ordered.extend(remainder)
    if len(ordered) != len(merged):
        raise RuntimeError("chunk rewrite would lose entries; aborting")

    for path in directory.glob("guide-*.json"):
        path.unlink()
    count = 0
    for index in range(0, len(ordered), CHUNK_SIZE):
        part = ordered[index : index + CHUNK_SIZE]
        count += 1
        payload = {key: merged[key] for key in part}
        (directory / f"guide-{count:02d}.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=1) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    return count


if __name__ == "__main__":
    raise SystemExit(main())
