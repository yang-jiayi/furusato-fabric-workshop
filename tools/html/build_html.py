"""Build docs/furusato-workshop-v2-7-0-complete.html.

The HTML is a complete bilingual mirror of the canonical Word participant guide.
It is produced from the same content model the Word build uses, so the two can
never drift: an unmirrored Japanese string is a hard failure, and every number,
name and instruction still comes from the shipped v2.7.0 runtime.

The build is deterministic. No wall-clock time enters the output; the recorded
build stamp is a digest of the runtime inputs plus the builder sources.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT / "tools" / "docs"))
sys.path.insert(0, str(HERE))

from furusato_docs.context import load_context, runtime_fingerprint  # noqa: E402
from furusato_docs.deliverables import deliverable_names, validate_edition  # noqa: E402
from furusato_docs.facts import compute_facts  # noqa: E402
from furusato_docs.oox import StyleCarrier  # noqa: E402
from furusato_docs.publication import (  # noqa: E402
    PublicationError,
    check_directory,
    prepare_public_build,
    public_word_errors,
    safe_path,
)
from furusato_docs.tests10 import build_tests  # noqa: E402

from furusato_html import __version_of_record__  # noqa: E402
from furusato_html.assets import build_library  # noqa: E402
from furusato_html.capture import capture_participant_guide  # noqa: E402
from furusato_html.mirror import load_mirror, load_ui_strings, suspicious_english  # noqa: E402
from furusato_html.model import build_document  # noqa: E402
from furusato_html.page import render_page  # noqa: E402
from furusato_html.render import RenderContext  # noqa: E402

OUTPUT_NAME = "furusato-workshop-v2-7-0-complete.html"
SUPERSEDED = ("furusato-workshop-v2-6-0-complete.html",)

#: HTML sources and the shared Word content/build helpers.
SOURCE_GLOBS = (
    "tools/html/build_html.py",
    "tools/html/assets/app.css",
    "tools/html/assets/app.js",
    "tools/html/furusato_html/*.py",
    "tools/html/furusato_html/i18n/*.json",
    "tools/docs/furusato_docs/*.py",
)


def source_fingerprint(root: Path) -> dict[str, str]:
    files: dict[str, str] = {}
    for pattern in SOURCE_GLOBS:
        for path in sorted(root.glob(pattern)):
            if path.is_file():
                files[path.relative_to(root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return files


def office_sources(
    root: Path, version: str, edition: str = "", *,
    public_documents_only: bool = False, source_dir: Path | None = None,
) -> dict[str, str]:
    """SHA-256 of each Office deliverable this HTML mirrors."""
    digests: dict[str, str] = {}
    directory = source_dir if source_dir is not None else root / "docs"
    for name in deliverable_names(version, edition).selected_office(public_documents_only):
        path = directory / name
        if not path.is_file():
            raise SystemExit(f"missing Office source to mirror: {path}")
        digests[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    return digests


def content_fingerprint(nodes) -> str:
    """SHA-256 of the captured content model alone.

    Deliberately excludes assets, CSS, JS and the Office byte digests: this is the
    identity of *what the guide says*. A layout-only Office reissue repaginates the
    DOCX and changes its byte digest while leaving this value untouched, which is
    what makes ``--release-digest`` a checkable claim rather than a trusted one.
    """
    return hashlib.sha256(
        json.dumps(nodes, sort_keys=True, separators=(",", ":"), default=str, ensure_ascii=False).encode(
            "utf-8"
        )
    ).hexdigest()


def diagram_sources(context) -> dict[str, str]:
    """SHA-256 of every diagram asset, so the embedded set is auditable."""
    digests: dict[str, str] = {}
    for key, variants in sorted(context.diagrams.items()):
        for suffix, path in sorted(variants.items()):
            digests[f"{key}.{suffix}"] = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    return digests


def atomic_write(path: Path, payload: str, *, overwrite: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not overwrite:
        safe_path(path)
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(payload)
        return
    handle = tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", newline="\n", dir=str(path.parent), delete=False, suffix=".tmp"
    )
    try:
        with handle:
            handle.write(payload)
        os.replace(handle.name, path)
    except BaseException:
        Path(handle.name).unlink(missing_ok=True)
        raise


def build(
    root: Path,
    out_dir: Path,
    keep_superseded: bool = False,
    release_digests: dict[str, str] | None = None,
    expect_content: str | None = None,
    edition: str = "",
    public_documents_only: bool = False,
    unified_assets: dict | None = None,
) -> dict[str, object]:
    context = load_context(root, document_edition=edition, unified_assets=unified_assets)
    names = deliverable_names(context.version, edition)
    if public_documents_only:
        out_dir = prepare_public_build(root, out_dir, names, edition, html=True)
        if release_digests:
            raise PublicationError("public mode records actual Word bytes; --release-digest is not allowed")
        problems = public_word_errors(out_dir / names.participant, names)
        if problems:
            raise PublicationError("; ".join(problems))
    if context.version != __version_of_record__:
        raise SystemExit(
            f"VERSION is {context.version} but tools/html targets {__version_of_record__}."
        )

    facts = compute_facts(context)
    tests = build_tests(context, facts)
    carrier = StyleCarrier.resolve(root)

    capture = capture_participant_guide(
        context, facts, tests, carrier, public_documents_only=public_documents_only
    )
    mirror = load_mirror(public_documents_only=public_documents_only, context=context)
    ui = load_ui_strings(public_documents_only=public_documents_only, context=context)

    document = build_document(capture.nodes, mirror)

    unused = mirror.unused()
    if unused:
        raise SystemExit(
            "The English mirror has entries the content model never used. The Word guide "
            "probably changed; remove or update them:\n  " + "\n  ".join(repr(u) for u in unused[:20])
        )
    stale = suspicious_english(mirror.entries)
    if stale:
        raise SystemExit(
            "English mirror values still look untranslated:\n  "
            + "\n  ".join(repr(s) for s in stale[:20])
        )

    diagram_keys = sorted({b["source_key"] for b in document.figures if b["source_kind"] == "diagram"})
    screenshot_tags = sorted({b["source_key"] for b in document.figures if b["source_kind"] == "screenshot"})
    library = build_library(context, carrier, diagram_keys, screenshot_tags)

    runtime = runtime_fingerprint(context)
    sources = source_fingerprint(root)
    observed = office_sources(
        root, context.version, edition, public_documents_only=public_documents_only,
        source_dir=out_dir if public_documents_only else None,
    )
    content_sha = content_fingerprint(capture.nodes)

    if expect_content is not None and content_sha != expect_content:
        raise SystemExit(
            "--content-fingerprint does not match the captured content model.\n"
            f"  expected {expect_content}\n  actual   {content_sha}\n"
            "The Word source changed more than layout, so this is not a layout-only "
            "reissue. Re-mirror the content instead of restamping the digest."
        )

    release_digests = dict(release_digests or {})
    unknown = sorted(set(release_digests) - set(observed))
    if unknown:
        raise SystemExit(f"--release-digest names unknown Office sources: {unknown}")
    if release_digests and expect_content is None:
        raise SystemExit(
            "--release-digest requires --content-fingerprint. Restamping an Office digest "
            "is only honest when the content model is proven unchanged."
        )

    #: What the footer states, and what was actually on disk at build time. These
    #: differ only for a layout-only Office reissue, and both are always recorded.
    office = {
        name: {"release": release_digests.get(name, digest), "observed": digest}
        for name, digest in observed.items()
    }
    combined = hashlib.sha256(
        json.dumps(
            {"runtime": runtime["combinedSha256"], "sources": sources},
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()

    css = (HERE / "assets" / "app.css").read_text(encoding="utf-8")
    js = (HERE / "assets" / "app.js").read_text(encoding="utf-8")

    ctx = RenderContext(
        ui=ui,
        assets=library,
        version=context.version,
        fingerprint=combined[:16],
        runtime_fingerprint=runtime["combinedSha256"][:16],
        facts=facts,
        context=context,
        stats={
            "css": css,
            "js": js,
            "edition": edition,
            "public_documents_only": public_documents_only,
            "office": office,
            "entity_types": context.ontology_contract["entityTypes"],
            "relationship_types": context.ontology_contract["relationshipTypes"],
            "metadata_objects": context.metadata_object_count,
            "tests": len(tests),
            "dataset_version": context.dataset_manifest["datasetVersion"],
            "download_guide": names.participant,
            **({} if public_documents_only else {
                "download_tests": names.validation,
                "download_workbook": names.workbook,
            }),
        },
    )

    page = render_page(document, ctx)
    if public_documents_only and observed != office_sources(
        root, context.version, edition, public_documents_only=True, source_dir=out_dir
    ):
        raise PublicationError("participant Word changed during HTML rendering; freeze it and rebuild")
    output = out_dir / names.html
    atomic_write(output, page, overwrite=not public_documents_only)

    removed: list[str] = []
    if not public_documents_only and not keep_superseded and not edition:
        for name in SUPERSEDED:
            legacy = out_dir / name
            if legacy.is_file():
                legacy.unlink()
                removed.append(name)
    if public_documents_only:
        check_directory(out_dir, names, required=names.public_pair)

    chapters = [s for s in document.sections]
    headings = sum(1 for _ in document.walk())
    report = {
        "output": str(output),
        "edition": edition,
        "publicDocumentsOnly": public_documents_only,
        "bytes": output.stat().st_size,
        "chapters": len(chapters),
        "sections": headings,
        "tables": len(document.tables),
        "figures": len(document.figures),
        "diagrams": len(diagram_keys),
        "screenshots": len(screenshot_tags),
        "checklistSteps": len(document.checklist),
        "contentFingerprint": content_sha,
        "officeSources": office,
        "translations": len(mirror.entries),
        "uiStrings": len(ui),
        "buildFingerprint": combined,
        "runtimeFingerprint": runtime["combinedSha256"],
        "officeSources": office,
        "diagramSources": diagram_sources(context),
        "removedSuperseded": removed,
    }
    return report


def parse_pairs(items: list[str], flag: str) -> dict[str, str]:
    pairs: dict[str, str] = {}
    for item in items:
        name, _, value = item.partition("=")
        if not name or not value:
            raise SystemExit(f"{flag} expects NAME=SHA256, got {item!r}")
        pairs[name.strip()] = value.strip().lower()
    return pairs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=None, help="output directory (default: docs/)")
    parser.add_argument(
        "--edition", default="", type=validate_edition,
        help="Mirror the separately named Office edition and preserve the original HTML",
    )
    parser.add_argument("--keep-legacy", action="store_true", help="keep superseded HTML deliverables")
    parser.add_argument(
        "--public-documents-only", action="store_true",
        help="Mirror only the participant Word in --out; requires --edition and external private staging",
    )
    parser.add_argument("--json", action="store_true", help="print the build report as JSON")
    parser.add_argument(
        "--release-digest",
        action="append",
        metavar="NAME=SHA256",
        default=[],
        help=(
            "record NAME's canonical release digest in the footer instead of the digest "
            "observed on disk. For layout-only Office reissues that repaginate the DOCX "
            "without changing text, tables or runtime. Requires --content-fingerprint."
        ),
    )
    parser.add_argument(
        "--content-fingerprint",
        default=None,
        metavar="SHA256",
        help="fail unless the captured content model hashes to this value",
    )
    args = parser.parse_args(argv)
    if args.public_documents_only and not args.out:
        parser.error("--public-documents-only requires --out")

    out_dir = Path(args.out) if args.out else ROOT / "docs"
    if not args.public_documents_only:
        out_dir = out_dir.resolve()
    try:
        report = build(
            ROOT,
            out_dir,
            keep_superseded=args.keep_legacy,
            release_digests=parse_pairs(args.release_digest, "--release-digest"),
            expect_content=args.content_fingerprint,
            edition=args.edition,
            public_documents_only=args.public_documents_only,
        )
    except PublicationError as error:
        parser.error(str(error))

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(f"built  {report['output']}")
        print(f"  size          {report['bytes'] / 1048576:.2f} MB")
        print(f"  chapters      {report['chapters']}")
        print(f"  sections      {report['sections']}")
        print(f"  tables        {report['tables']}")
        print(f"  figures       {report['figures']} "
              f"({report['diagrams']} diagrams + {report['screenshots']} screenshots)")
        print(f"  checklist     {report['checklistSteps']} steps")
        print(f"  translations  {report['translations']} guide strings + {report['uiStrings']} UI strings")
        print(f"  fingerprint   {report['buildFingerprint'][:16]}")
        if report["removedSuperseded"]:
            print(f"  removed       {', '.join(report['removedSuperseded'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
