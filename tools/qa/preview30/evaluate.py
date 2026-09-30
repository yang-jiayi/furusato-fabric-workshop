"""Preview evaluation CLI. Every command is local/read-only on Fabric."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from preview_contract import (
    EvidenceError, PrivateStore, capture_plan_report, compare, empty_manifest, load_catalog, load_json,
    readiness_errors, report,
)
from proof_files import check_attachment_pack, check_docx, check_html
from observations import check_synonym_only_delta, inspect_mcp_discovery
from source_oracle import compute_oracle, graph_expectations, immutable_baseline, original_suite


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-root", required=True, type=Path)
    commands = parser.add_subparsers(dest="command", required=True)
    offline = commands.add_parser("offline", help="Verify immutable source and prepare an unscored inventory.")
    offline.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[3])
    offline.add_argument("--baseline", required=True)
    offline.add_argument("--label", required=True)
    check = commands.add_parser("report", help="Revalidate private raw evidence; never submit questions.")
    check.add_argument("--manifest", required=True)
    check.add_argument("--oracle", required=True)
    check.add_argument("--readiness", required=True)
    check.add_argument("--out", required=True)
    ready = commands.add_parser("ready", help="Check the explicit runtime readiness handoff.")
    ready.add_argument("--readiness", required=True)
    ready.add_argument("--questions", action="store_true")
    ready.add_argument("--out", required=True)
    graph = commands.add_parser("graph", help="Compute selected-projection counts, without materializing.")
    graph.add_argument("--scope", required=True)
    graph.add_argument("--oracle", required=True)
    graph.add_argument("--out", required=True)
    document = commands.add_parser("document", help="Check local Word/HTML relationships and image links.")
    document.add_argument("--file", required=True, type=Path)
    document.add_argument("--document-root", required=True, type=Path)
    document.add_argument("--out", required=True)
    attachments = commands.add_parser("attachments", help="Validate local package bytes and actual CSV dictionary schemas.")
    attachments.add_argument("--pack-root", required=True, type=Path)
    attachments.add_argument("--dataset-manifest", required=True, type=Path)
    attachments.add_argument("--private-benchmark", help="Private frozen/input suite for exact plaintext-leak detection.")
    attachments.add_argument("--out", required=True)
    captures = commands.add_parser("captures", help="Audit an actual private capture checklist without using a browser.")
    captures.add_argument("--plan", required=True, type=Path)
    captures.add_argument("--manifest")
    captures.add_argument("--readiness")
    captures.add_argument("--out", required=True)
    discovery = commands.add_parser("mcp-discovery", help="Inspect captured native initialize/tools-list replies only.")
    discovery.add_argument("--capture", required=True)
    discovery.add_argument("--out", required=True)
    delta = commands.add_parser("synonym-diff", help="Check a synonym-only change without forgiving collateral changes.")
    delta.add_argument("--before", required=True)
    delta.add_argument("--after", required=True)
    delta.add_argument("--restored")
    delta.add_argument("--entity-part", required=True)
    delta.add_argument("--synonym", required=True)
    delta.add_argument("--out", required=True)
    comparison = commands.add_parser("compare", help="Revalidate both arms before a bounded comparison.")
    comparison.add_argument("--baseline-manifest", required=True)
    comparison.add_argument("--candidate-manifest", required=True)
    comparison.add_argument("--oracle", required=True)
    comparison.add_argument("--readiness", required=True)
    comparison.add_argument("--history")
    comparison.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    store = PrivateStore(args.private_root)

    def read(name):
        return load_json(store.path(name))

    try:
        if args.command == "offline":
            if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,63}", args.label):
                raise EvidenceError("Use a portable label, not a path.")
            oracle = compute_oracle(args.repo_root.resolve())
            preservation = immutable_baseline(args.repo_root.resolve(), args.baseline, oracle)
            original = original_suite(args.repo_root.resolve())
            catalog = load_catalog()
            manifest = empty_manifest(catalog, oracle)
            result = report(manifest, {}, store, oracle, catalog)
            for name, value in (("source-oracle", oracle), ("baseline-preservation", preservation),
                                ("original-suite", original), ("manifest", manifest), ("report", result)):
                store.write(str(Path(args.label) / f"{name}.json"), value)
            print(f"Offline verified: {len(oracle['csv_sha256'])} CSVs; original 10/84 unchanged.")
            print(f"New-feature inventory: {result['case_count']} cases / {result['requested_slots']} slots.")
            print("Live questions: 0; AI accuracy: null; runtime/UI readiness remains blocked.")
            return 0
        if args.command == "ready":
            errors = readiness_errors(read(args.readiness), store, questions=args.questions)
            store.write(args.out, {"state": "blocked" if errors else "ready_for_read_only_capture", "errors": errors})
            print("Readiness: blocked." if errors else "Readiness: verified for read-only capture only.")
            return 2 if errors else 0
        if args.command == "report":
            result = report(read(args.manifest), read(args.readiness), store, read(args.oracle))
            store.write(args.out, result)
            print(f"Evidence-complete AI questions: {result['ai']['scored_questions']}.")
            print(f"Full inventory states: {result['state_counts']}")
            complete = result["state_counts"]["pass"] + result["state_counts"]["unsupported"] == result["requested_slots"]
            return 0 if complete and result["state_counts"]["pass"] else 2
        if args.command == "graph":
            result = graph_expectations(read(args.oracle), read(args.scope))
            store.write(args.out, result)
            print("Scoped graph oracle saved; no live graph acceptance claimed.")
            return 0
        if args.command == "document":
            if args.file.suffix.lower() == ".docx":
                if not args.file.resolve().is_relative_to(args.document_root.resolve()):
                    raise EvidenceError("Document is outside its declared root.")
                result = check_docx(args.file)
            elif args.file.suffix.lower() in {".html", ".htm"}:
                result = check_html(args.file, args.document_root)
            else:
                raise EvidenceError("Only Word .docx and HTML are supported.")
            store.write(args.out, result)
            print(f"Local document references: {result['local_state']}; external links remain explicitly unverified.")
            return 0 if result["local_state"] == "pass" and not result["external_unverified"] else 2
        if args.command == "attachments":
            terms = []
            if args.private_benchmark:
                frozen = read(args.private_benchmark)
                suite = frozen.get("suite", frozen)
                for case in suite["cases"]:
                    terms += [case["question"]]
                    if isinstance(case.get("expected"), str):
                        terms += [case["expected"]]
            result = check_attachment_pack(args.pack_root, args.dataset_manifest, terms)
            store.write(args.out, result)
            print(f"Local attachment package: {result['local_state']}; files={len(result['files'])}; "
                  f"CSV schemas={result['dictionary_schemas_verified']}.")
            print("Upload/model use and PDF/image visual review remain unverified; no UI or AI pass is claimed.")
            return 0 if result["local_state"] == "pass" else 2
        if args.command == "captures":
            result = capture_plan_report(
                load_json(args.plan), store,
                read(args.manifest) if args.manifest else None,
                read(args.readiness) if args.readiness else None,
            )
            store.write(args.out, result)
            print(f"Required real UI views: {result['required_views']}; verified: {result['verified_views']}; "
                  f"missing/unverified: {result['missing_or_unverified_views']}.")
            print("Capture coverage is not factual AI accuracy or full lab acceptance.")
            return 0 if result["state"] == "pass" else 2
        if args.command == "mcp-discovery":
            result = inspect_mcp_discovery(read(args.capture))
            store.write(args.out, result)
            print(f"Native discovery: {result['discovery_state']}; advertised tools={len(result['advertised_tool_names'])}.")
            print("No source-query execution, Copilot action or AI accuracy is implied.")
            return 0 if result["discovery_state"] == "pass" else 2
        if args.command == "synonym-diff":
            result = check_synonym_only_delta(
                read(args.before), read(args.after), args.entity_part, args.synonym,
                read(args.restored) if args.restored else None,
            )
            store.write(args.out, result)
            print(f"Synonym-only structural delta: {result['structural_delta_state']}; "
                  f"protected changes={len(result['protected_content_changes'])}; "
                  f"restored content equals baseline={result['restored_definition_equals_before']}.")
            print("A restore does not erase the changed-state failure or prove source-data/Version-UI behavior.")
            return 0 if result["structural_delta_state"] == "pass" else 2
        if args.command == "compare":
            oracle, readiness = read(args.oracle), read(args.readiness)
            baseline = report(read(args.baseline_manifest), readiness, store, oracle)
            candidate = report(read(args.candidate_manifest), readiness, store, oracle)
            result = compare(baseline, candidate, read(args.history) if args.history else None)
            store.write(args.out, result)
            print(f"Comparison: {result['decision']}; no automatic promotion or cloud mutation.")
            return 0 if result["decision"] == "eligible_for_coordinator_review" else 2
    except (EvidenceError, FileExistsError, OSError, KeyError) as error:
        print(f"Evaluation blocked: {error}")
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
