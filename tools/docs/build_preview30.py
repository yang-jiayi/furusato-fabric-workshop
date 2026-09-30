"""Build the actual v3 Preview Word/HTML pair from one complete bilingual model."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import asdict
from pathlib import Path
from docx.shared import Pt

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "tools" / "docs"), str(ROOT / "tools" / "html")]

from furusato_docs.console import use_utf8_streams  # noqa: E402
from furusato_docs.docx_kit import DocumentBuilder, cover_page  # noqa: E402
from furusato_docs.oox import (  # noqa: E402
    apply_japanese_typography, apply_package_metadata, normalise_package_metadata, tidy_contents_tail,
)
from furusato_docs.preview30_content import HTML_NAME, VERSION, WORD_NAME, PREVIEW_NOTICE_JA, build  # noqa: E402
from furusato_docs.word_refresh import refresh_with_word  # noqa: E402
from furusato_html.preview30 import render as render_html  # noqa: E402


def write_word(document, context, carrier, evidence, metadata, target: Path, review: Path, lang="ja"):
    builder = DocumentBuilder(carrier, review / "participant-shell.docx")
    # Reserve room for the real TOC field-end and section boundary. Normal-style
    # inherited spacing can otherwise strand those two hairlines on a blank page.
    for style in builder.document.styles:
        if style.style_id in {"TOC1", "TOC2"}:
            style.font.size = Pt(11)
            style.paragraph_format.space_before = Pt(0)
            style.paragraph_format.space_after = Pt(1)
            style.paragraph_format.line_spacing = 1.0
    status = PREVIEW_NOTICE_JA
    cover_page(
        builder,
        title="Furusato Workshop 3.0 Preview",
        title_break_after="Furusato Workshop",
        subtitle="新Ontology体験・24章・5付録／実データbinding・Metrics・Rules・Copilot添付・Graph・MCP・変更管理",
        version=VERSION,
        tagline=status,
        footer_lines=(
            "Furusato Fabric Workshop", "Microsoft Learn 確認日 2026-09-29",
            "合成教材／元の10問・84条件を保持／Wordと日英HTMLは同じ共有原稿",
            "v2.7の全本文・表・コードは比較参考として保持。旧UI写真は新UIの証拠にしない。",
        ),
    )
    builder.table_of_contents(levels="1-2")
    for section in document.walk():
        builder.heading(section.title.get(lang), section.level, **getattr(section, "word_layout", {}))
        for block in section.blocks:
            kind = block.kind
            if kind == "paragraph":
                builder.body(block["text"].get(lang))
            elif kind == "list":
                builder.bullets([value.get(lang) for value in block["items"]], numbered=block["numbered"])
            elif kind == "callout":
                title = block.get("title")
                builder.callout(block["tone"], block["text"].get(lang), title=title.get(lang) if title else None, **block.get("word_layout", {}))
            elif kind == "code":
                label = block.get("language")
                builder.code_block(block["text"], language=label.get(lang) if label else "")
            elif kind == "prompt":
                builder.code_block(block["text"].get(lang), language="Plan / Act prompt")
            elif kind == "table":
                columns = len(block["headers"])
                widths = block.get("widths") or ([1.25, 5.35] if columns == 2 else [1] * columns)
                layout = {"font_size": 8.0 if columns >= 6 else 9.0, "header_size": 8.0 if columns >= 6 else 9.0, **block.get("word_layout", {})}
                builder.table(
                    [value.get(lang) for value in block["headers"]],
                    [[value.get(lang) for value in row] for row in block["rows"]],
                    caption=block["caption"].get(lang), widths=widths,
                    **layout,
                )
            elif kind == "figure":
                if block["source_kind"] == "diagram":
                    image = context.diagrams[block["source_key"]]["png"]
                elif block["source_kind"] == "reviewed-capture":
                    image = evidence["captures"][block["source_key"]]["path"]
                else:
                    raise ValueError("Legacy or unreviewed screenshot cannot enter the preview Word")
                builder.figure(image, caption=block["caption"].get(lang), alt_text=block["alt"].get(lang), **{"max_height_cm": 15.5, **block.get("word_layout", {})})
            else:
                raise ValueError("Unknown shared-content block: " + kind)
    builder.update_fields_on_open()
    builder.save(target)
    apply_package_metadata(
        target,
        title="Furusato Workshop 3.0 Preview — participant guide",
        subject=status,
        keywords="Fabric IQ, Ontology, Preview, bilingual, synthetic, 24 chapters",
        description="Complete 24-chapter/5-appendix guide. Content SHA256: " + metadata["contentSha256"],
        label_info=carrier.label_info(), custom_properties=carrier.custom_properties(),
    )
    return {"figures": len(builder.figures), "tables": len(builder.tables), "paragraphs": len(builder.document.paragraphs)}


def main(argv=None):
    use_utf8_streams()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path, help="Fresh private pair directory outside the repository")
    parser.add_argument("--review", required=True, type=Path, help="Private build/review directory outside the pair and repository")
    inputs = parser.add_mutually_exclusive_group()
    inputs.add_argument("--evidence", type=Path, help="Coordinator's private original+sanitized evidence manifest")
    inputs.add_argument("--public-evidence", type=Path, help="Approved source-owned public projection; defaults to docs/assets/v3-preview-evidence/manifest.json when present")
    parser.add_argument("--evaluation-report", type=Path, help="Private normalized evaluator report; approved fields only")
    parser.add_argument("--require-evidence", action="store_true", help="Reject an incomplete evidence handoff; does not turn blockers into passes")
    parser.add_argument("--skip-word", action="store_true", help="Draft only: leave fields unrefreshed")
    args = parser.parse_args(argv)
    if args.require_evidence and args.skip_word:
        parser.error("--skip-word is draft-only and cannot be combined with --require-evidence")
    out, review = args.out.resolve(), args.review.resolve()
    if out.is_relative_to(ROOT) or review.is_relative_to(ROOT) or review.is_relative_to(out) or out == review:
        parser.error("Pair and review must be separate private locations outside the public repository")
    if out.exists():
        parser.error("Refusing to overwrite any existing pair directory; choose a fresh stage")
    document, context, facts, carrier, evidence, metadata = build(ROOT, args.evidence, args.evaluation_report, public_evidence_path=args.public_evidence)
    if args.require_evidence and (
        not evidence["complete"]
        or (evidence.get("publicProjection") and evidence.get("freezeStatus") != "frozen-for-build")
    ):
        parser.error("Actual reviewed evidence is incomplete or not finally frozen. Build a visibly labelled draft without --require-evidence.")
    out.mkdir(parents=True)
    review.mkdir(parents=True, exist_ok=True)
    word = out / WORD_NAME
    report = {
        **metadata, "status": "draft",
        "word": write_word(document, context, carrier, evidence, metadata, word, review),
        "wordRefresh": {"ok": False, "detail": "Skipped by explicit draft option"},
    }
    if not args.skip_word:
        result = refresh_with_word(word)
        trimmed = tidy_contents_tail(word) if result.ok else 0
        if trimmed:
            result = refresh_with_word(word)
        report["wordRefresh"] = asdict(result)
        report["wordRefresh"]["trimmedContentsTail"] = trimmed
    report["typography"] = apply_japanese_typography(word)
    report["metadataNormalization"] = normalise_package_metadata(word)
    word_sha = hashlib.sha256(word.read_bytes()).hexdigest()
    html = render_html(document, context, facts, carrier, evidence, metadata, word_sha, ROOT)
    (out / HTML_NAME).write_text(html, encoding="utf-8", newline="\n")
    report["files"] = {name: hashlib.sha256((out / name).read_bytes()).hexdigest() for name in (WORD_NAME, HTML_NAME)}
    report["status"] = "awaiting-layout-and-interaction-validation" if evidence["complete"] else "usable-draft-awaiting-ui-evidence"
    (review / "build.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (review / "shared-content.json").write_text(json.dumps(asdict(document), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (review / "SHA256SUMS.txt").write_text("".join(f"{value}  {name}\n" for name, value in report["files"].items()), encoding="utf-8")
    (review / "participant-shell.docx").unlink(missing_ok=True)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
