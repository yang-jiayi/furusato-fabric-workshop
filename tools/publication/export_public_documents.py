"""Validate and copy exactly one named participant Word/HTML pair. No publishing."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "docs"))
sys.path.insert(0, str(ROOT / "tools" / "html"))

from furusato_docs.deliverables import deliverable_names, validate_edition  # noqa: E402
from furusato_docs.publication import (  # noqa: E402
    PUBLIC_MODE,
    PublicationError,
    check_directory,
    outside_repo,
    public_word_errors,
    require_public_edition,
    safe_path,
)
from validate_html import (  # noqa: E402
    Report,
    Structure,
    _plain_text,
    check_office_sources,
    check_public_html_policy,
)


def _hashes(directory: Path, names) -> dict[str, str]:
    return {
        name: hashlib.sha256((directory / name).read_bytes()).hexdigest()
        for name in names.public_pair
    }


def validate_pair_policy(root: Path, directory: Path, version: str, edition: str) -> dict[str, str]:
    """Inspect real pair bytes before any copy; this does not replace content validation."""
    require_public_edition(edition)
    names = deliverable_names(version, edition)
    directory = outside_repo(directory, root)
    check_directory(directory, names, required=names.public_pair)
    errors = public_word_errors(directory / names.participant, names)
    raw = (directory / names.html).read_text(encoding="utf-8")
    structure = Structure()
    structure.feed(raw)
    structure.close()
    errors.extend(structure.errors)
    report = Report()
    check_office_sources(
        report, structure.root, root, version, {}, edition,
        public_documents_only=True, source_dir=directory,
    )
    check_public_html_policy(report, structure.root, _plain_text(raw), version, edition)
    errors.extend(f"{check}: {detail}" for _, check, detail in report.failures)
    if errors:
        raise PublicationError("public pair validation failed: " + "; ".join(errors))
    return _hashes(directory, names)


def _validate_content(root: Path, directory: Path, edition: str) -> None:
    from furusato_docs.context import load_context
    from furusato_docs.facts import compute_facts
    from validate_docs import validate_public_documents
    from validate_html import validate

    context = load_context(root, document_edition=edition)
    facts = compute_facts(context)
    reports = validate_public_documents(root, directory, context, facts, edition)
    html_report = validate(root, directory, edition=edition, public_documents_only=True)
    failures = [
        f"{report.target}: {finding.check}: {finding.message}"
        for report in reports
        for finding in report.failures
    ]
    failures.extend(f"HTML: {check}: {detail}" for _, check, detail in html_report.failures)
    if failures:
        raise PublicationError("document content validation failed: " + "; ".join(failures))


def _manifest_path(root: Path, path: Path | None, *pair_directories: Path) -> Path | None:
    if path is None:
        return None
    path = outside_repo(path, root)
    if any(path.is_relative_to(directory) for directory in pair_directories):
        raise PublicationError("the hash manifest must be outside both staging and public pair directories")
    if path.exists() and (not path.is_file() or path.stat().st_nlink != 1):
        raise PublicationError("the manifest must be an unlinked regular file")
    return path


def _manifest_text(digests: dict[str, str]) -> str:
    return "".join(f"{digest}  {name}\n" for name, digest in sorted(digests.items()))


def export(
    root: Path, source: Path, output: Path, edition: str, *, manifest: Path | None = None
) -> dict[str, object]:
    """Fail closed on existing files; never delete, replace or repack any original."""
    require_public_edition(edition)
    version = (root / "VERSION").read_text(encoding="utf-8").strip()
    names = deliverable_names(version, edition)
    source = outside_repo(source, root)
    output = outside_repo(output, root)
    if source.is_relative_to(output) or output.is_relative_to(source):
        raise PublicationError("source staging and export output must be disjoint directories")
    check_directory(output, names)
    if output.exists() and any(output.iterdir()):
        raise PublicationError("refusing to overwrite an export; use a fresh output or --validate-only")
    manifest = _manifest_path(root, manifest, source, output)
    if manifest is not None and manifest.exists():
        raise PublicationError("refusing to overwrite an existing hash manifest")

    digests = validate_pair_policy(root, source, version, edition)
    _validate_content(root, source, edition)
    check_directory(source, names, required=names.public_pair)
    if _hashes(source, names) != digests:
        raise PublicationError("source files changed during validation; freeze them and retry")

    safe_path(output)
    output.mkdir(parents=True, exist_ok=True)
    check_directory(output, names)
    if any(output.iterdir()):
        raise PublicationError("export output changed during validation; nothing will be overwritten")
    for name in names.public_pair:
        safe_path(output / name)
        safe_path(source / name)
        # Exclusive creation, not copy2/replace: a concurrent file is never overwritten.
        with (output / name).open("xb") as target, (source / name).open("rb") as original:
            shutil.copyfileobj(original, target)
    observed = validate_pair_policy(root, output, version, edition)
    if observed != digests:
        raise PublicationError("export bytes differ from the validated source; export is not ready")
    if manifest is not None:
        safe_path(manifest)
        manifest.parent.mkdir(parents=True, exist_ok=True)
        with manifest.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(_manifest_text(observed))
    return {
        "mode": PUBLIC_MODE,
        "edition": edition,
        "output": str(output),
        "files": observed,
        "manifest": str(manifest) if manifest else None,
        "published": False,
    }


def validate_export(
    root: Path, output: Path, edition: str, *, manifest: Path | None = None
) -> dict[str, object]:
    """Read-only revalidation; an optional external manifest must already match."""
    version = (root / "VERSION").read_text(encoding="utf-8").strip()
    output = outside_repo(output, root)
    manifest = _manifest_path(root, manifest, output)
    digests = validate_pair_policy(root, output, version, edition)
    _validate_content(root, output, edition)
    names = deliverable_names(version, edition)
    check_directory(output, names, required=names.public_pair)
    if _hashes(output, names) != digests:
        raise PublicationError("export files changed during validation")
    if manifest is not None:
        if not manifest.is_file() or manifest.read_text(encoding="utf-8") != _manifest_text(digests):
            raise PublicationError("external hash manifest is missing or does not match the public pair")
    return {
        "mode": PUBLIC_MODE,
        "edition": edition,
        "output": str(output),
        "files": digests,
        "validatedOnly": True,
        "published": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, help="external private staging containing only the chosen pair")
    parser.add_argument("--out", required=True, type=Path, help="fresh output outside the repository and source")
    parser.add_argument("--edition", required=True, type=validate_edition)
    parser.add_argument("--manifest", type=Path, help="optional SHA-256 manifest OUTSIDE the two-file directory")
    parser.add_argument("--validate-only", action="store_true", help="revalidate --out without writing anything")
    args = parser.parse_args(argv)
    if args.validate_only and args.source is not None:
        parser.error("--validate-only uses --out only; omit --source")
    if not args.validate_only and args.source is None:
        parser.error("export requires --source")
    try:
        if args.validate_only:
            report = validate_export(ROOT, args.out, args.edition, manifest=args.manifest)
        else:
            report = export(ROOT, args.source, args.out, args.edition, manifest=args.manifest)
    except (PublicationError, OSError, UnicodeError, ValueError) as error:
        print(f"publication refused: {error}", file=sys.stderr)
        return 1
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
