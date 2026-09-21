"""Regenerate the maintained style carrier asset used by the document build.

    python tools/docs/make_style_carrier.py --source <styled-participant.docx>

This is a maintenance tool, not part of the normal build. It runs the document
builders against a styled source DOCX purely to discover which Fabric UI
screenshots the current content reuses, then writes
``tools/docs/assets/style-carrier.zip`` holding the branded OOXML shell parts
plus exactly those (already cropped) screenshots.

``build_docs.py`` and ``validate_docs.py`` depend only on that asset, so a clean
v2.7 checkout rebuilds and validates without any superseded deliverable present.
Run this only when the reusable screenshot set or the house style changes; the
source DOCX can be restored from git history for the occasion, for example::

    git show <rev>:docs/<superseded-participant>.docx > carrier.docx
    python tools/docs/make_style_carrier.py --source carrier.docx
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from furusato_docs import participant_guide, validation_doc  # noqa: E402
from furusato_docs.console import use_utf8_streams  # noqa: E402
from furusato_docs.context import load_context, repo_root, sha256_file  # noqa: E402
from furusato_docs.facts import compute_facts  # noqa: E402
from furusato_docs.oox import CompactStyleCarrier, StyleCarrier  # noqa: E402
from furusato_docs.tests10 import build_tests  # noqa: E402


def main() -> int:
    use_utf8_streams()
    parser = argparse.ArgumentParser(description="Rebuild tools/docs/assets/style-carrier.zip")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--source",
        help="Styled DOCX to harvest the shell parts and reusable screenshots from",
    )
    group.add_argument(
        "--prune",
        action="store_true",
        help=(
            "Rewrite the existing asset in place, keeping only the screenshots the current "
            "content still uses. Needs no external source DOCX."
        ),
    )
    arguments = parser.parse_args()

    root = repo_root()
    target = StyleCarrier.archive_path(root)

    if arguments.prune:
        if not target.is_file():
            raise SystemExit(f"Nothing to prune; asset not found: {target}")
        carrier: StyleCarrier = CompactStyleCarrier(target)
        source_label = f"{target.relative_to(root).as_posix()} (prune)"
        before = carrier.screenshot_count
    else:
        source = Path(arguments.source)
        if not source.is_absolute():
            source = (root / source).resolve()
        if not source.is_file():
            raise SystemExit(f"Style source not found: {source}")
        carrier = StyleCarrier(source)
        source_label = str(source)
        before = len(carrier.available_screenshots)

    context = load_context(root)
    facts = compute_facts(context)
    tests = build_tests(context, facts)

    scratch = Path(tempfile.mkdtemp(prefix="furusato-carrier-"))
    try:
        participant_guide.build(context, facts, tests, carrier, scratch / "guide.docx", scratch)
        validation_doc.build(context, facts, tests, carrier, scratch / "validation.docx", scratch)
        staged = scratch / StyleCarrier.ARCHIVE_NAME
        registered = json.loads(
            (target.parent / "unified-ui-captures.json").read_text(encoding="utf-8")
        )["captures"]
        carrier.export_archive(staged, carrier.used_tags | set(registered))
        # Fail loudly here rather than at the next build if the asset is incomplete.
        verified = CompactStyleCarrier(staged)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(staged, target)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)

    print(
        json.dumps(
            {
                "source": source_label,
                "archive": str(target.relative_to(root)),
                "screenshotsBefore": before,
                "screenshotsAfter": verified.screenshot_count,
                "bytes": target.stat().st_size,
                "sha256": sha256_file(target),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
