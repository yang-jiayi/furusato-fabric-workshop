"""Build an explicit v3 document edition from one complete bilingual model."""

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
from furusato_docs import preview30_release as release  # noqa: E402
from furusato_docs.preview30_acceptance import require_public_acceptance  # noqa: E402
from furusato_docs.typography import ascii_parentheses  # noqa: E402
from furusato_docs.word_refresh import refresh_with_word  # noqa: E402
from furusato_html.preview30 import render as render_html  # noqa: E402
from furusato_docs.participant30 import TAGLINE as PARTICIPANT_TAGLINE, figure_path as participant_figure_path  # noqa: E402


def write_word(
    document, context, carrier, evidence, metadata, target: Path, review: Path, lang="ja", *,
    release_profile=release.PREVIEW,
):
    profile = release.require_metadata_profile(metadata, release_profile)
    builder = DocumentBuilder(carrier, review / "participant-shell.docx")
    # Extra snapshot/artifact entries must not strand the last TOC rows.
    compact_contents = profile.is_snapshot or "currentArtifactSet" in metadata
    for style in builder.document.styles:
        if profile.is_snapshot and style.style_id == "Title":
            style.font.size = Pt(25)
        if style.style_id in {"TOC1", "TOC2"}:
            style.font.size = Pt(11)
            style.paragraph_format.space_before = Pt(0)
            style.paragraph_format.space_after = Pt(0 if compact_contents else 1)
            style.paragraph_format.line_spacing = 1.0
    status = release.presentation(metadata, profile).get(lang, PREVIEW_NOTICE_JA)
    participant = bool(metadata.get("participantEdition"))
    if participant:
        status = PARTICIPANT_TAGLINE[lang]
    cover_page(
        builder,
        title=profile.title,
        title_break_after="Furusato Workshop",
        subtitle=(
            "参加者用手順書／Lakehouse・Eventhouse・Ontology・Data Agent のハンズオン" if participant else
            "新Ontology体験・24章・5付録／実データbinding・Metrics・Rules・Copilot添付・Graph・MCP・変更管理"
        ),
        version=profile.version,
        tagline=status,
        footer_lines=(
            "Furusato Fabric Workshop", "Microsoft Learn 確認日 2026-09-29",
            "データはすべて合成データです。自治体名とコードだけが実在の参照ラベルです。",
        ) if participant else (
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
                builder.bullets([value.get(lang) for value in block["items"]], numbered=block["numbered"],
                                start=block.get("start") or 1)
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
                elif block["source_kind"] == "participant-capture":
                    image = participant_figure_path(block["source_key"])
                else:
                    raise ValueError("Legacy or unreviewed screenshot cannot enter the preview Word")
                builder.figure(image, caption=block["caption"].get(lang), alt_text=block["alt"].get(lang), **{"max_height_cm": 15.5, **block.get("word_layout", {})})
            else:
                raise ValueError("Unknown shared-content block: " + kind)
    builder.update_fields_on_open()
    builder.save(target)
    description = "Complete 24-chapter/5-appendix guide. Content SHA256: " + metadata["contentSha256"]
    if participant:
        description = "Participant guide, 24 chapters and 5 appendices. Content SHA256: " + metadata["contentSha256"]
        if "currentArtifactSet" in metadata:
            description += ". Artifact-set SHA256: " + metadata["currentArtifactSet"]["manifestSha256"]
    apply_package_metadata(
        target,
        title=profile.title + " — participant guide",
        subject=ascii_parentheses(status),
        keywords=("Fabric IQ, Ontology, hands-on, bilingual, synthetic, 24 chapters" if participant
                  else "Fabric IQ, Ontology, Preview, bilingual, synthetic, 24 chapters"),
        description=description,
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
    inputs.add_argument("--public-evidence", type=Path, help="Approved source-owned projection; default is selected by the explicit document profile")
    parser.add_argument("--evaluation-report", type=Path, help="Private normalized evaluator report; approved fields only")
    parser.add_argument("--artifact-manifest", type=Path,
                        help="Bind a separately generated current guide to verified v3 source artifacts; historical files stay unchanged.")
    parser.add_argument("--require-evidence", action="store_true", help="Reject an incomplete evidence handoff; does not turn blockers into passes")
    parser.add_argument("--skip-word", action="store_true", help="Draft only: leave fields unrefreshed")
    parser.add_argument("--require-acceptance", action="store_true", help="Final-use gate: reject every unresolved original-suite, lab, capture or publication-approval condition")
    parser.add_argument("--acceptance-approval", type=Path, help="Explicit approval bound to the selected public evidence hash and run")
    release.add_arguments(parser)
    args = parser.parse_args(argv)
    profile = release.get_profile(args.release_profile)
    release.check_options(
        profile, args.release_approval, evidence_path=args.evidence, evaluation_path=args.evaluation_report,
        evaluation100_path=args.evaluation100,
    )
    if profile.is_release and args.skip_word:
        parser.error("--skip-word is Preview/DRAFT-only; a release requires refreshed Word fields")
    if args.acceptance_approval and not args.require_acceptance:
        parser.error("--acceptance-approval requires --require-acceptance")
    if args.require_acceptance:
        if args.evidence or args.skip_word:
            parser.error("Final-use admission requires a reviewed public projection and refreshed Word fields.")
        require_public_acceptance(args.public_evidence or ROOT / profile.evidence_relative,
                                  args.acceptance_approval, root=ROOT)
    if args.require_evidence and args.skip_word:
        parser.error("--skip-word is draft-only and cannot be combined with --require-evidence")
    out, review = args.out.resolve(), args.review.resolve()
    if out.is_relative_to(ROOT) or review.is_relative_to(ROOT) or review.is_relative_to(out) or out == review:
        parser.error("Pair and review must be separate private locations outside the public repository")
    if out.exists():
        parser.error("Refusing to overwrite any existing pair directory; choose a fresh stage")
    document, context, facts, carrier, evidence, metadata = build(
        ROOT, args.evidence, args.evaluation_report, public_evidence_path=args.public_evidence,
        release_profile=profile, release_approval=args.release_approval,
        evaluation100_path=args.evaluation100,
        **({"artifact_manifest_path": args.artifact_manifest} if args.artifact_manifest else {}),
        **({"participant_edition": True} if args.participant_edition else {}),
    )
    if args.require_evidence and (
        not evidence["complete"]
        or (evidence.get("publicProjection") and evidence.get("freezeStatus") != "frozen-for-build")
    ):
        parser.error("Actual reviewed evidence is incomplete or not finally frozen. Build a visibly labelled draft without --require-evidence.")
    out.mkdir(parents=True)
    review.mkdir(parents=True, exist_ok=True)
    word = out / profile.word_name
    report = {
        **metadata, "status": "known-limitations-release-build" if profile.is_release else "draft",
        "documentIdentity": release.document_identity(metadata, profile),
        "word": write_word(document, context, carrier, evidence, metadata, word, review, release_profile=profile),
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
    html = render_html(document, context, facts, carrier, evidence, metadata, word_sha, ROOT, release_profile=profile)
    (out / profile.html_name).write_text(html, encoding="utf-8", newline="\n")
    report["files"] = {name: hashlib.sha256((out / name).read_bytes()).hexdigest() for name in (profile.word_name, profile.html_name)}
    report["status"] = "awaiting-layout-and-interaction-validation" if evidence["complete"] else "usable-draft-awaiting-ui-evidence"
    if profile.is_release:
        report["status"] = "user-authorized-release-awaiting-layout-and-interaction-validation"
    if profile.is_snapshot:
        report["status"] = "dated-validation-snapshot-awaiting-layout-and-interaction-validation"
    (review / "build.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (review / "shared-content.json").write_text(json.dumps(asdict(document), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (review / "SHA256SUMS.txt").write_text("".join(f"{value}  {name}\n" for name, value in report["files"].items()), encoding="utf-8")
    (review / "participant-shell.docx").unlink(missing_ok=True)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
