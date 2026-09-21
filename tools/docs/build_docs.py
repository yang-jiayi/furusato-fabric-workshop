"""Deterministic build entry point for the v2.7.0 Office deliverables.

    python tools/docs/build_docs.py [--skip-word] [--out DIR]

Every value comes from ``workshop/v2.7.0``; the build fails loudly rather than
emitting a deliverable that disagrees with the shipped runtime.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from furusato_docs import participant_guide, validation_doc, workbook  # noqa: E402
from furusato_docs.context import load_context, repo_root, runtime_fingerprint, sha256_file  # noqa: E402
from furusato_docs.console import use_utf8_streams  # noqa: E402
from furusato_docs.deliverables import deliverable_names, validate_edition  # noqa: E402
from furusato_docs.excel_refresh import refresh_with_excel  # noqa: E402
from furusato_docs.facts import compute_facts  # noqa: E402
from furusato_docs.oox import (  # noqa: E402
    StyleCarrier,
    apply_japanese_typography,
    normalise_package_metadata,
    tidy_contents_tail,
)
from furusato_docs.publication import (  # noqa: E402
    PublicationError,
    check_directory,
    display_path,
    prepare_public_build,
    safe_path,
)
from furusato_docs.tests10 import build_tests  # noqa: E402
from furusato_docs.word_refresh import refresh_with_word  # noqa: E402
from furusato_docs.workbook import reattach_label as reattach_workbook_label  # noqa: E402

STYLE_CARRIER_ASSET = "tools/docs/assets/style-carrier.zip"
#: One-time migration convenience: the superseded deliverables this release replaces.
#: Deleting them is a no-op on a clean v2.7 checkout, where they are already absent.
SUPERSEDED = (
    "docs/Fabric_IQ_Ontology_Workshop_Furusato_Participant_v2.6.0.docx",
    "docs/Furusato_Data_Agent_Ontology_Test_100_v2.6.0.docx",
    "docs/Furusato_Notebook_01-05_Processing_Specification_v2.6.0.xlsx",
)

def main(argv: list[str] | None = None) -> int:
    use_utf8_streams()
    parser = argparse.ArgumentParser(description="Build the Furusato v2.7.0 Office deliverables.")
    parser.add_argument("--out", default=None, help="Output directory (default: docs)")
    parser.add_argument(
        "--edition", default="", type=validate_edition,
        help="Append a named correction edition to filenames, preserving the original release",
    )
    parser.add_argument("--skip-word", action="store_true", help="Skip the Word COM field/TOC refresh")
    parser.add_argument(
        "--public-documents-only", action="store_true",
        help="Build only the participant Word; requires --edition and a fresh --out outside the repository",
    )
    parser.add_argument(
        "--skip-excel", action="store_true", help="Skip the Excel COM formula recalculation"
    )
    parser.add_argument(
        "--skip-workbook",
        action="store_true",
        help="Leave the existing workbook untouched (for a Word-only layout rebuild)",
    )
    parser.add_argument(
        "--keep-legacy",
        action="store_true",
        help="Do not delete the superseded deliverables this release replaces (no-op on a clean checkout)",
    )
    arguments = parser.parse_args(argv)
    public = arguments.public_documents_only
    if public and (not arguments.out or arguments.skip_workbook):
        parser.error("--public-documents-only requires --out and cannot be combined with --skip-workbook")

    root = repo_root()
    context = load_context(root, document_edition=arguments.edition)
    names = deliverable_names(context.version, arguments.edition)
    out_dir = root / (arguments.out or "docs")
    if public:
        try:
            out_dir = prepare_public_build(root, out_dir, names, arguments.edition)
        except PublicationError as error:
            parser.error(str(error))
    else:
        out_dir = out_dir.resolve()
    fingerprint = runtime_fingerprint(context)
    facts = compute_facts(context)
    tests = build_tests(context, facts)

    carrier = StyleCarrier.resolve(root)
    report_carrier = str(Path(carrier.source).relative_to(root))

    out_dir.mkdir(parents=True, exist_ok=True)

    guide_path = out_dir / names.participant
    validation_path = out_dir / names.validation
    workbook_path = out_dir / names.workbook
    if arguments.skip_workbook and not workbook_path.is_file():
        parser.error(f"--skip-workbook requires the selected edition's workbook: {workbook_path}")

    scratch = Path(tempfile.mkdtemp(prefix="furusato-docs-", dir=str(out_dir)))
    report: dict[str, object] = {
        "version": context.version,
        "edition": arguments.edition,
        "publicDocumentsOnly": public,
        "styleCarrier": report_carrier,
        "runtimeInputs": {
            "fileCount": fingerprint["fileCount"],
            "combinedSha256": fingerprint["combinedSha256"],
        },
    }
    try:
        working_guide = scratch / "participant.docx" if public else guide_path
        guide_builder = participant_guide.build(
            context, facts, tests, carrier, working_guide, scratch, public_documents_only=public
        )
        if public:
            safe_path(guide_path)
            with guide_path.open("xb") as target, working_guide.open("rb") as generated:
                shutil.copyfileobj(generated, target)
        validation_builder = None
        if not public:
            validation_builder = validation_doc.build(context, facts, tests, carrier, validation_path, scratch)
        sheet_stats: dict[str, int] | None = None
        if not public and not arguments.skip_workbook:
            sheet_stats = workbook.build(
                context, workbook_path, carrier.label_info(), facts.observation.calendar
            )
    finally:
        shutil.rmtree(scratch, ignore_errors=True)

    report["participantGuide"] = {
        "path": display_path(guide_path, root),
        "figures": len(guide_builder.figures),
        "tables": len(guide_builder.tables),
        "paragraphs": len(guide_builder.document.paragraphs),
        "sha256": sha256_file(guide_path),
    }
    if validation_builder is not None:
        report["validationDocument"] = {
            "path": display_path(validation_path, root),
            "figures": len(validation_builder.figures),
            "tables": len(validation_builder.tables),
            "paragraphs": len(validation_builder.document.paragraphs),
            "sha256": sha256_file(validation_path),
        }
    if not public:
        report["workbook"] = {
            "path": display_path(workbook_path, root),
            "sheets": sheet_stats,
            "sha256": sha256_file(workbook_path),
            "rebuilt": sheet_stats is not None,
        }

    if not arguments.skip_word:
        word_report = {}
        word_targets = [("participantGuide", guide_path)]
        if not public:
            word_targets.append(("validationDocument", validation_path))
        for name, path in word_targets:
            result = refresh_with_word(path)
            trimmed = 0
            if result.ok:
                # Word materialises the contents listing on the first pass; drop the
                # empty container paragraph it leaves behind, then repaginate so the
                # stored page statistics match the trimmed layout.
                trimmed = tidy_contents_tail(path)
                if trimmed:
                    result = refresh_with_word(path)
            word_report[name] = {
                "ok": result.ok,
                "detail": result.detail,
                "pages": result.pages,
                "words": result.words,
                "trimmedContentsTail": trimmed,
            }
            # Word drops the explicit Japanese typography defaults on save; write
            # them back so the delivered file states them rather than relying on
            # every consumer resolving the implicit defaults identically.
            word_report[name]["typographyRestored"] = apply_japanese_typography(path)
            # Last write on the package: Word stamps its own tenant's default
            # sensitivity label and the signed-in user into every COM save, so the
            # approved classification and authorship are restored afterwards. The
            # file must not be reopened in Word after this point.
            word_report[name]["metadata"] = normalise_package_metadata(path)
            if result.ok:
                report[name]["sha256"] = sha256_file(path)  # type: ignore[index]
                report[name]["pages"] = result.pages  # type: ignore[index]
                report[name]["words"] = result.words  # type: ignore[index]
        report["wordRefresh"] = word_report
    else:
        report["wordRefresh"] = {"skipped": True}

    if not public and not arguments.skip_excel and not arguments.skip_workbook:
        # Excel caches the computed values next to the formulas so previews and
        # PDF exports are not blank. The Purview label parts are re-attached
        # afterwards because Excel rewrites the package.
        excel_result = refresh_with_excel(workbook_path)
        if excel_result.ok:
            reattach_workbook_label(workbook_path, carrier.label_info(), context)
            report["workbook"]["sha256"] = sha256_file(workbook_path)  # type: ignore[index]
        report["excelRefresh"] = {
            "ok": excel_result.ok,
            "detail": excel_result.detail,
            "sheets": excel_result.sheets,
        }
    else:
        report["excelRefresh"] = {"skipped": True}

    if not public and not arguments.keep_legacy and not arguments.edition:
        removed = []
        for relative in SUPERSEDED:
            legacy_path = root / relative
            if legacy_path.is_file():
                legacy_path.unlink()
                removed.append(relative)
        report["removedSuperseded"] = removed

    if public:
        check_directory(out_dir, names, required=(names.participant,))
        report["participantGuide"]["sha256"] = sha256_file(guide_path)  # type: ignore[index]
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
