"""Review answer-content conditions without pretending MCP exposes execution."""

from __future__ import annotations

from typing import Any

from native_evaluation import EvaluationError, T03_NA, contains_truncation, digest, pointer
from native_mcp import OBSERVABILITY_BLOCKERS, native_view, observability


# Structural rubric references, not answer keys. These original conditions
# require actual source execution/returned rows, not merely a correct label.
EXECUTION_REQUIRED = frozenset({
    "T01.evidence.1", "T04.pass_criteria.2", "T05.pass_criteria.2",
    "T06.pass_criteria.2", "T09.pass_criteria.1",
})


def execution_required(condition: dict[str, Any]) -> bool:
    return (
        condition["id"] in EXECUTION_REQUIRED
        or condition.get("required_evidence") == "native_execution"
    )


def review_template(case: dict[str, Any], record: dict[str, Any]) -> dict[str, Any]:
    view, _ = native_view(record.get("response", {}))
    return {
        "case_id": case["id"], "record_sha256": digest(record), "reviewer": "",
        "assessment": "answer_content_conditions_only",
        "observability": observability(),
        "branch": "answer", "branch_evidence_pointer": "", "branch_note": "",
        "data_matches_frozen_fixture": False, "platform_block_detected": None,
        "native_final_text_pointers": [x["pointer"] for x in view["final_texts"]],
        "conditions": [{
            "id": condition["id"], "verdict": "UNCLEAR",
            "basis": "native_execution" if execution_required(condition) else "unreviewed",
            "note": "", "evidence": [],
        } for condition in case["conditions"]],
    }


def grade_case(
    case: dict[str, Any], record: dict[str, Any], review: dict[str, Any] | None,
) -> dict[str, Any]:
    """Manual condition judgments and strict acceptance are different outputs.

    Execution is unobservable for this transport, regardless of a reviewer's
    checkbox, a source label, a final-answer table or a SQL-looking text block.
    """
    count = len(case["conditions"])
    base = {
        "case_id": case["id"], "total_conditions": count, "question_pass": False,
        "assessment": "answer_content_conditions_only",
        "observability_blockers": list(OBSERVABILITY_BLOCKERS),
        "observability": observability(),
    }
    errors = []
    if review is None:
        errors.append("not_reviewed")
    if record.get("status") != "completed":
        errors.append("capture_not_completed")
    if record.get("case_id") != case["id"] or record.get("question") != case["question"]:
        errors.append("question_identity_mismatch")
    if record.get("submission_count") != 1:
        errors.append("not_exactly_one_submission")
    if record.get("fresh_mcp_session") is not True or record.get("history_supplied") is not False:
        errors.append("fresh_mcp_session_not_established")
    if (record.get("conversation_id") or record.get("backend_conversation_id")
            or record.get("fresh_conversation") is True):
        errors.append("unsupported_backend_conversation_claim")
    if (not record.get("configuration_before_sha256")
            or record.get("configuration_before_sha256") != record.get("configuration_after_sha256")):
        errors.append("configuration_missing_or_changed")
    response = record.get("response", {})
    view, native_errors = native_view(response)
    errors += native_errors
    if contains_truncation(response):
        errors.append("truncated_native_evidence")
    if review is not None:
        if review.get("record_sha256") != digest(record) or review.get("case_id") != case["id"]:
            errors.append("review_record_hash_or_identity_mismatch")
        if not str(review.get("reviewer", "")).strip():
            errors.append("reviewer_missing")
        if review.get("data_matches_frozen_fixture") is not True:
            errors.append("deployed_data_fixture_not_verified")
        if review.get("platform_block_detected") is not False:
            errors.append("platform_block_or_unreviewed_platform_status")
    if errors:
        return {
            **base, "pass": 0, "fail": count, "na": 0,
            "answer_content_condition_errors": sorted(set(errors)),
            "gate_errors": sorted(set(errors) | set(OBSERVABILITY_BLOCKERS)),
            "all_reviewed_conditions_pass": False,
        }
    assert review is not None
    rows = review.get("conditions", [])
    expected = {c["id"]: c for c in case["conditions"]}
    if (len(rows) != count or len({r.get("id") for r in rows}) != count
            or {r.get("id") for r in rows} != set(expected)):
        errors.append("rubric_condition_set_changed")
    final_pointers = {x["pointer"] for x in view["final_texts"]}
    allowed_na: frozenset[str] = frozenset()
    if review.get("branch") == "clarification":
        if (case["id"] == "T03"
                and review.get("branch_evidence_pointer") in final_pointers
                and str(review.get("branch_note", "")).strip()):
            allowed_na = T03_NA
        else:
            errors.append("clarification_branch_not_allowed_or_evidenced")
    elif review.get("branch") != "answer":
        errors.append("unknown_answer_branch")
    if errors:
        return {
            **base, "pass": 0, "fail": count, "na": 0,
            "answer_content_condition_errors": errors,
            "gate_errors": errors + list(OBSERVABILITY_BLOCKERS),
            "all_reviewed_conditions_pass": False,
        }
    decisions = []
    for row in rows:
        verdict = row.get("verdict")
        note = str(row.get("note", "")).strip()
        problems = []
        if verdict == "NA":
            if row["id"] not in allowed_na or not note:
                problems.append("illegal_na")
        elif verdict not in {"PASS", "FAIL", "UNCLEAR"}:
            problems.append("invalid_verdict")
        if verdict == "PASS":
            if execution_required(expected[row["id"]]) or row.get("basis") == "native_execution":
                problems.append("native_execution_evidence_unobservable")
            elif row.get("basis") != "native_answer":
                problems.append("answer_content_basis_not_reviewed")
            refs = row.get("evidence", [])
            if not note or not refs:
                problems.append("pass_without_explanation_and_evidence")
            for ref in refs:
                try:
                    # Only exact final-text locations qualify, not RPC IDs,
                    # root objects or an inferred internal source-call list.
                    if ref not in final_pointers:
                        raise EvaluationError("Not a native answer text location.")
                    if not isinstance(pointer(response, ref), str) or not pointer(response, ref).strip():
                        raise EvaluationError("Empty native text.")
                except EvaluationError:
                    problems.append("pass_cites_missing_or_nonanswer_evidence")
        effective = "FAIL" if problems or verdict == "UNCLEAR" else verdict
        decisions.append({
            "id": row["id"], "requested_verdict": verdict, "verdict": effective,
            "basis": row.get("basis"), "errors": problems,
        })
    passed, failed, na = (
        sum(row["verdict"] == value for row in decisions) for value in ("PASS", "FAIL", "NA")
    )
    assert passed + failed + na == count
    return {
        **base, "pass": passed, "fail": failed, "na": na,
        "answer_content_condition_errors": [e for row in decisions for e in row["errors"]],
        "condition_decisions": decisions,
        "all_reviewed_conditions_pass": failed == 0 and passed > 0,
        # Never promote MCP to strict acceptance, even with all visible
        # conditions met. These blockers are not a 0% factual-accuracy claim.
        "gate_errors": list(OBSERVABILITY_BLOCKERS),
    }
