"""Read-only final gate. Save a private decision; exit 2 when acceptance is blocked."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "tools" / "docs"), str(ROOT / "tools" / "data-agent")]
from furusato_docs import preview30_acceptance as acceptance
from furusato_docs import preview30_evidence as private
from furusato_docs import preview30_public_evidence as public
from native_evaluation import PrivateStore


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    inputs = parser.add_mutually_exclusive_group(required=True)
    inputs.add_argument("--private-evidence", type=Path)
    inputs.add_argument("--public-evidence", type=Path)
    parser.add_argument("--original-suite-runs", type=Path)
    parser.add_argument("--selected-original-suite-run-id")
    parser.add_argument("--approval", type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)
    if args.public_evidence:
        if args.original_suite_runs or args.selected_original_suite_run_id:
            parser.error("Public evidence owns its selected run; do not override or mix it.")
        evidence = public.load(args.public_evidence, root=ROOT)
        if "selectedOriginalSuiteRunId" not in evidence:
            parser.error("Supply an explicitly selected reviewed projection, not an automatic legacy/best/latest choice.")
        runs, selected = evidence["originalSuiteRuns"], evidence["selectedOriginalSuiteRunId"]
        evidence_hash = evidence["projectionSha256"]
    else:
        if not args.original_suite_runs or not args.selected_original_suite_run_id:
            parser.error("Private evidence requires explicit reviewed aggregate runs and a selected ID.")
        evidence = private.load(args.private_evidence)
        runs = json.loads(args.original_suite_runs.read_text(encoding="utf-8"))
        selected = args.selected_original_suite_run_id
        evidence_hash = private.digest(args.private_evidence)
    approval = json.loads(args.approval.read_text(encoding="utf-8")) if args.approval else None
    result = acceptance.assess(evidence, runs, selected, evidence_hash, approval)
    if not args.out.is_absolute():
        parser.error("Use an absolute private output path outside any Git repository.")
    store = PrivateStore(args.out.parent)
    store.write(args.out.name, result)
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return 0 if result["readyForFinalPublication"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
