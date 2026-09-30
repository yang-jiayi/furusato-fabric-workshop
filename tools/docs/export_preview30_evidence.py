"""Export an explicitly approved, sanitized public projection; never copy originals."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "docs"))
from furusato_docs import preview30_evaluation as evaluation  # noqa: E402
from furusato_docs import preview30_evidence as private  # noqa: E402
from furusato_docs import preview30_public_evidence as public  # noqa: E402


def public_lab(lab, value):
    projected = {key: value[key] for key in public.LAB_FIELDS if key in value}
    if "invariants" in projected:
        names = private.ADDITIVE_INVARIANTS if lab == "copilot-additive-entity" else private.ACT_INVARIANTS
        projected["invariants"] = {name: value["invariants"][name] for name in names if name in value["invariants"]}
    return projected


def export_projection(
    evidence_path: Path, output: Path, *, reviewed_at: str, reviewer: str,
    approved: bool, runs_path: Path | None = None, evaluation_path: Path | None = None,
    root: Path | None = None, freeze_status: str = "awaiting-final-consumer-proof",
):
    root = (root or ROOT).resolve()
    evidence_path, output = evidence_path.resolve(), output.resolve()
    if not approved:
        raise ValueError("Explicit approval is required; this tool does not perform visual privacy review")
    if evidence_path.is_relative_to(root):
        raise ValueError("Import from the private original+sanitized manifest, not a public projection")
    assets = root / "docs" / "assets"
    if output == assets or not output.is_relative_to(assets) or output.exists():
        raise ValueError("Choose a fresh reviewed projection directory beneath source docs/assets")
    checked = private.load(evidence_path)
    raw_bytes = evidence_path.read_bytes()
    raw = json.loads(raw_bytes)
    data = {
        "schemaVersion": public.SCHEMA, "scope": public.SCOPE, "approved": True,
        "freezeStatus": freeze_status,
        "reviewedAt": reviewed_at, "reviewer": reviewer, "captures": [],
        "labs": {lab: public_lab(lab, raw["labs"][lab]) for lab in sorted(checked["labs"])},
    }
    blobs = {}
    for ident, entry in sorted(checked["captures"].items()):
        blob = entry["path"].read_bytes()
        if private.digest(entry["path"]) != entry["sha256"]:
            raise ValueError("Sanitized bytes changed after private validation")
        filename = f"captures/{entry['sha256']}.png"
        blobs[filename] = blob
        data["captures"].append({
            "id": ident, "file": filename, "sha256": entry["sha256"],
            "originalSha256": entry["originalSha256"], "capturedAt": entry["capturedAt"],
            "reviewedAt": reviewed_at, "actualUI": True, "experience": "new",
            "privacyReview": "accounts-urls-ids-paths-removed",
            "completionEvidence": entry["completionEvidence"], "caption": entry["caption"],
        })
    if runs_path is not None:
        if runs_path.resolve().is_relative_to(root):
            raise ValueError("Supply the review-only aggregate input privately before export")
        data["originalSuiteRuns"] = public.suite_runs(json.loads(runs_path.read_text(encoding="utf-8")))
    if evaluation_path is not None:
        data["evaluationReport"] = evaluation.load(evaluation_path)
    public.timestamp(reviewed_at, "reviewedAt")
    if evidence_path.read_bytes() != raw_bytes:
        raise ValueError("Private evidence manifest changed during export")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".preview30-review-", dir=output.parent) as temporary:
        stage = Path(temporary) / "projection"
        (stage / "captures").mkdir(parents=True)
        for filename, blob in sorted(blobs.items()):
            (stage / filename).write_bytes(blob)
        payload = json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
        (stage / "manifest.json").write_text(payload, encoding="utf-8")
        projected = public.load(stage / "manifest.json", root=root)
        private.load(evidence_path)
        if evidence_path.read_bytes() != raw_bytes:
            raise ValueError("Private evidence changed during public projection validation")
        if output.exists():
            raise FileExistsError("Projection destination appeared during review; nothing was replaced")
        stage.rename(output)
    return {
        "schemaVersion": public.SCHEMA, "captures": len(data["captures"]),
        "uniqueSanitizedImages": len(blobs), "manifestSha256": private.digest(output / "manifest.json"),
        "reviewCoverageComplete": projected["complete"], "scope": public.SCOPE,
        "originalFilesIncluded": False, "privatePathsIncluded": False,
        "newDeploymentReadinessCertified": False,
        "freezeStatus": projected["freezeStatus"],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-evidence", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--reviewed-at", required=True)
    parser.add_argument("--reviewer", required=True, help="Portable reviewer role, not an account/UPN")
    parser.add_argument("--approve-public-projection", action="store_true")
    parser.add_argument("--original-suite-runs", type=Path, help="Private approved aggregate list; never raw answers or a condition matrix")
    parser.add_argument("--evaluation-report", type=Path, help="Optional private normalized report; existing approved projection only")
    parser.add_argument("--freeze-status", choices=sorted(public.FREEZE_STATUSES), default="awaiting-final-consumer-proof")
    args = parser.parse_args(argv)
    result = export_projection(
        args.private_evidence, args.out, reviewed_at=args.reviewed_at, reviewer=args.reviewer,
        approved=args.approve_public_projection, runs_path=args.original_suite_runs,
        evaluation_path=args.evaluation_report,
        freeze_status=args.freeze_status,
    )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
