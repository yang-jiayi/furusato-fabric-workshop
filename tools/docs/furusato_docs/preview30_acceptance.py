"""Final-publication admission; draft completeness is not user acceptance."""

from __future__ import annotations

import json
from pathlib import Path

from . import preview30_evidence as private
from . import preview30_public_evidence as public


SCHEMA = "furusato-preview30-acceptance/v1"
APPROVAL_SCHEMA = "furusato-preview30-publication-approval/v1"
APPROVAL_FIELDS = {
    "schemaVersion", "selectedOriginalSuiteRunId", "evidenceSha256",
    "finalPublicationApproved", "reviewer", "reviewedAt",
}


def assess(evidence, runs, selected_id, evidence_sha256, approval=None):
    """Inputs must already pass the private/public provenance loaders."""
    runs = public.suite_runs(runs)
    selected = public.selected_original_suite_run({
        "originalSuiteRuns": runs, "selectedOriginalSuiteRunId": selected_id,
    }, required=True)
    checks = []

    def check(name, passed, detail):
        checks.append({"check": name, "passed": passed is True, "detail": detail})

    counts = selected["counts"]
    check("original-fixed-suite", selected["questionCount"] == 10 and selected["conditionCount"] == 84,
          "The original ten questions and all 84 conditions are mandatory.")
    check("original-zero-fail", counts["fail"] == counts["blocked"] == counts["executionUnverified"] == 0,
          "A targeted diagnostic, heldout or best-of combination cannot replace the selected complete run.")
    check("original-native-acceptance", selected["accepted"] is True
          and selected["freshBackendProof"] is True
          and public.original_execution_proof(selected, selected["independentExecutionTraces"]),
          "Require reviewed acceptance, genuine backend proof and the original source-execution routes.")
    check("case-level-proof", "caseAggregates" in selected,
          "Final admission requires all ten case aggregates, including contextual refusal completion.")
    cases = selected.get("caseAggregates", [])
    check("original-na-scope", bool(cases) and all(
        row["counts"]["notApplicable"] <= (3 if row["case"] == "T03" else 0)
        for row in cases
    ), "Only the original T03 clarification branch permits its three numeric-only N/A conditions.")
    expected_labs = {item["lab"] for item in private.requests()}
    labs = evidence["labs"]
    incomplete_labs = sorted(lab for lab in expected_labs if labs.get(lab, {}).get("status") != "passed")
    check("all-required-labs", not incomplete_labs,
          "Unfinished or known-issue lanes: " + (", ".join(incomplete_labs) or "none"))
    needed = [item["id"] for item in private.requests() if item.get("completionRequired", True)]
    partial = sorted(ident for ident in needed
                     if evidence["captures"].get(ident, {}).get("completionEvidence") is not True)
    check("required-completion-captures", not partial,
          "Missing/partial required captures: " + (", ".join(partial) or "none"))
    check("review-coverage", evidence["complete"] is True,
          "Coverage alone can include documented blockers and is not all-feature acceptance.")
    check("reviewed-public-freeze", evidence.get("publicProjection") is True
          and evidence.get("freezeStatus") == "frozen-for-build",
          "Private staging or a partial public projection cannot authorize final publication.")
    valid_approval = False
    if approval is not None:
        public.exact_fields(approval, APPROVAL_FIELDS, "publication approval", APPROVAL_FIELDS)
        if approval["schemaVersion"] != APPROVAL_SCHEMA or type(approval["finalPublicationApproved"]) is not bool:
            raise ValueError("Invalid publication approval schema or flag.")
        public.safe_text(approval["reviewer"], "publication reviewer")
        public.timestamp(approval["reviewedAt"], "publication approval time")
        valid_approval = (
            approval["finalPublicationApproved"] is True
            and approval["selectedOriginalSuiteRunId"] == selected_id
            and approval["evidenceSha256"] == evidence_sha256
        )
    check("explicit-bound-publication-approval", valid_approval,
          "Approval must explicitly identify this exact evidence hash and selected run; no automatic promotion.")
    return {
        "schemaVersion": SCHEMA, "selectedOriginalSuiteRunId": selected_id,
        "evidenceSha256": evidence_sha256, "originalCounts": counts,
        "readyForFinalPublication": all(row["passed"] for row in checks),
        "checks": checks, "publicationPerformed": False, "mainPromotionPerformed": False,
        "knownFailuresReclassified": False, "draftBuildPermissionChanged": False,
    }


def require_public_acceptance(evidence_path: Path, approval_path: Path | None, *, root: Path):
    evidence = public.load(evidence_path, root=root)
    if "selectedOriginalSuiteRunId" not in evidence:
        raise ValueError("Final admission requires an explicit selectedOriginalSuiteRunId.")
    approval = json.loads(approval_path.read_text(encoding="utf-8")) if approval_path else None
    result = assess(evidence, evidence["originalSuiteRuns"], evidence["selectedOriginalSuiteRunId"],
                    evidence["projectionSha256"], approval)
    if not result["readyForFinalPublication"]:
        failed = [row["check"] for row in result["checks"] if not row["passed"]]
        raise ValueError("Final publication acceptance blocked: " + ", ".join(failed))
    return result
