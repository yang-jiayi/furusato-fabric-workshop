"""Offline contracts for native Data Agent evaluation (no service calls).

The guide's human rubric is authoritative. This module does not use an LLM
judge, infer PASS from keywords, repair answers, or execute reference queries.
Prompts, computed answer keys, judgments and raw evidence belong in a private
directory outside *every* Git checkout, never beside this module.
"""

from __future__ import annotations

import hashlib
import importlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class EvaluationError(ValueError):
    """An input or native evidence contract is not satisfied."""


ORIGINAL_COUNTS = (7, 6, 6, 11, 14, 10, 8, 7, 8, 7)
ORIGINAL_ROUTES = {
    "T01": ["SQL"], "T02": ["SQL"], "T03": ["SQL"], "T04": ["GQL"],
    "T05": ["SQL", "GQL"], "T06": ["KQL"], "T07": ["KQL"],
    "T08": [], "T09": ["SQL", "KQL", "GQL"], "T10": [],
}
T03_NA = frozenset({"T03.evidence.1", "T03.evidence.2", "T03.pass_criteria.2"})
TERMINAL = frozenset({"completed", "failed", "incomplete", "cancelled"})
LABEL = re.compile(r"[A-Za-z][A-Za-z0-9_-]{0,63}\Z")
SHA256 = re.compile(r"[0-9a-f]{64}\Z")


def platform_content_block(text: str) -> bool:
    """Recognize the observed service block, not a generated business refusal."""
    return "There's content here I can't work with." in text


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def encode(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False
    ).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(encode(value)).hexdigest()


def file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as exc:
        raise EvaluationError(f"Cannot read JSON file: {path.name}") from exc


def label(value: str) -> str:
    if not isinstance(value, str) or not LABEL.fullmatch(value):
        raise EvaluationError("Use a short ASCII label, not a path or identifier.")
    return value


class PrivateStore:
    """Exclusive-create evidence storage; rejects symlinks escaping its root."""

    @staticmethod
    def _reject_git_path(path: Path) -> None:
        for parent in (path, *path.parents):
            if (parent / ".git").exists():
                raise EvaluationError("Evidence and answer keys must be outside Git.")

    def __init__(self, root: Path):
        if not root.is_absolute():
            raise EvaluationError("The private evidence root must be absolute.")
        self.root = root.resolve()
        self._reject_git_path(self.root)
        self.root.mkdir(parents=True, exist_ok=True)

    def path(self, relative: str | Path) -> Path:
        value = Path(relative)
        if value.is_absolute() or ".." in value.parts:
            raise EvaluationError("Evidence paths must be relative and contained.")
        candidate = (self.root / value).resolve()
        if not candidate.is_relative_to(self.root):
            raise EvaluationError("Evidence path escapes its private root.")
        self._reject_git_path(candidate)
        return candidate

    def input_path(self, path: Path) -> Path:
        resolved = path.resolve()
        if not resolved.is_relative_to(self.root):
            raise EvaluationError("Private inputs must also be under the evidence root.")
        self._reject_git_path(resolved)
        return resolved

    def write(self, relative: str | Path, value: Any) -> str:
        return self.write_bytes(relative, encode(value))

    def write_bytes(self, relative: str | Path, content: bytes) -> str:
        path = self.path(relative)
        path.parent.mkdir(parents=True, exist_ok=True)
        # Do not overwrite or select a newer/better result for an existing slot.
        with path.open("xb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        return hashlib.sha256(content).hexdigest()

    def read(self, relative: str | Path) -> Any:
        return read_json(self.path(relative))


def original_suite(repo: Path) -> dict[str, Any]:
    """Evaluate the unchanged shared guide builder against its packaged CSVs."""
    docs = repo / "tools" / "docs"
    sys.path.insert(0, str(docs))
    try:
        context_module = importlib.import_module("furusato_docs.context")
        facts_module = importlib.import_module("furusato_docs.facts")
        tests_module = importlib.import_module("furusato_docs.tests10")
        # Refuse an import cached from another checkout.
        for module in (context_module, facts_module, tests_module):
            if not Path(module.__file__).resolve().is_relative_to(docs.resolve()):
                raise EvaluationError("Guide module was loaded from another checkout.")
        context = context_module.load_context(repo)
        tests = tests_module.build_tests(context, facts_module.compute_facts(context))
    finally:
        sys.path.pop(0)
    cases = []
    for test in tests:
        conditions = [
            {
                "id": f"{test.test_id}.{field}.{index}",
                "text": text,
                "source_field": field,
                "source_index": index - 1,
            }
            for field in ("evidence", "pass_criteria")
            for index, text in enumerate(getattr(test, field), 1)
        ]
        cases.append({
            "id": test.test_id, "title": test.title, "question": test.question,
            "expected": test.expected, "route": test.route,
            "query_shape": test.query_shape, "conditions": conditions,
            "required_query_languages": ORIGINAL_ROUTES[test.test_id],
        })
    if tuple(len(case["conditions"]) for case in cases) != ORIGINAL_COUNTS:
        raise EvaluationError("The original ten-question / 84-condition contract changed.")
    source_files = [
        docs / "furusato_docs" / name
        for name in ("context.py", "facts.py", "tests10.py")
    ]
    data = repo / "workshop" / f"v{context.version}" / "data"
    source_files += sorted(data.rglob("*.csv"))
    source_files += [data / "dataset-manifest.json", data / "SHA256SUMS.txt"]
    suite = {
        "schema_version": 1, "kind": "original", "cases": cases,
        "provenance": {
            "builder": "tools/docs/furusato_docs/tests10.py::build_tests",
            "rubric": "evidence + pass_criteria, verbatim and in source order",
            "clarification": "guide_agent.py §17.13; T03 numeric-only conditions",
            "files": {
                path.relative_to(repo).as_posix(): file_digest(path)
                for path in source_files
            },
        },
    }
    validate_suite(suite)
    return suite


def validate_suite(suite: dict[str, Any]) -> None:
    if suite.get("schema_version") != 1 or suite.get("kind") not in {"original", "heldout"}:
        raise EvaluationError("Unsupported suite schema or suite kind.")
    cases = suite.get("cases")
    if not isinstance(cases, list) or not cases:
        raise EvaluationError("A suite must contain cases.")
    seen, condition_ids = set(), set()
    for case in cases:
        case_id = label(case.get("id", ""))
        if case_id in seen or not str(case.get("question", "")).strip():
            raise EvaluationError("Duplicate case ID or missing question.")
        seen.add(case_id)
        if not case.get("conditions"):
            raise EvaluationError("Every question needs its frozen conditions.")
        if not set(case.get("required_query_languages", [])).issubset({"SQL", "KQL", "GQL"}):
            raise EvaluationError("Unknown required query language.")
        for condition in case["conditions"]:
            key = condition.get("id")
            if not key or key in condition_ids or not condition.get("text"):
                raise EvaluationError("Duplicate/empty condition ID or empty condition.")
            condition_ids.add(key)
    if suite["kind"] == "original":
        if [c["id"] for c in cases] != [f"T{i:02}" for i in range(1, 11)]:
            raise EvaluationError("Original question IDs/order changed.")
        if tuple(len(c["conditions"]) for c in cases) != ORIGINAL_COUNTS:
            raise EvaluationError("Original condition count changed.")
    elif any(case["id"].startswith("T") for case in cases):
        raise EvaluationError("Held-out cases must not masquerade as original questions.")


def freeze_suite(store: PrivateStore, relative: str, suite: dict[str, Any]) -> str:
    validate_suite(suite)
    return store.write(relative, {
        "frozen_at_utc": now_utc(), "suite_sha256": digest(suite), "suite": suite,
    })


def load_suite(store: PrivateStore, relative: str) -> dict[str, Any]:
    frozen = store.read(relative)
    suite = frozen["suite"]
    validate_suite(suite)
    if digest(suite) != frozen.get("suite_sha256"):
        raise EvaluationError("Frozen suite hash mismatch.")
    return suite


def parse_native_body(body: bytes) -> dict[str, Any]:
    """Parse JSON or a terminal SSE response, never promote partial deltas.

    The SDK's convenience normalizer may create a completed message from text
    deltas. This evaluator deliberately uses raw HTTP bodies instead.
    """
    try:
        text = body.decode("utf-8-sig")
        if text.lstrip().startswith("{"):
            payload = json.loads(text)
            if not isinstance(payload, dict):
                raise EvaluationError("Native response must be an object.")
            return payload
        events = []
        for block in text.replace("\r\n", "\n").replace("\r", "\n").split("\n\n"):
            data = "\n".join(line[5:].lstrip() for line in block.splitlines()
                             if line.startswith("data:"))
            if not data or data == "[DONE]":
                continue
            event = json.loads(data)
            if not isinstance(event, dict):
                raise EvaluationError("Malformed native SSE event.")
            events.append(event)
        terminal = [
            e for e in events if e.get("type") in {
                "response.completed", "response.failed",
                "response.incomplete", "response.cancelled",
            }
        ]
        if len(terminal) != 1 or not isinstance(terminal[0].get("response"), dict):
            raise EvaluationError("No unique terminal native response; no delta fallback.")
        payload = terminal[0]["response"]
        if terminal[0]["type"] != f"response.{payload.get('status')}":
            raise EvaluationError("Native SSE status contradiction.")
        # Save all bytes separately; missing output items are not synthesized.
        if any(e.get("type") == "error" for e in events):
            raise EvaluationError("An error event occurred in the native stream.")
        return payload
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise EvaluationError("Malformed or unfinished native HTTP body.") from exc


def pointer(document: Any, path: str) -> Any:
    """RFC 6901 pointer, with /@json for an explicitly encoded native JSON value."""
    if not isinstance(path, str) or (path and not path.startswith("/")):
        raise EvaluationError("Expected an absolute JSON pointer.")
    value = document
    try:
        for part in path.split("/")[1:] if path else []:
            part = part.replace("~1", "/").replace("~0", "~")
            if part == "@json":
                if not isinstance(value, str):
                    raise EvaluationError("@json must target a native JSON string.")
                value = json.loads(value)
            elif isinstance(value, list):
                if not re.fullmatch(r"0|[1-9][0-9]*", part):
                    raise EvaluationError("Invalid array index.")
                value = value[int(part)]
            else:
                value = value[part]
        return value
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        raise EvaluationError(f"Missing native evidence at {path}") from exc


def native_view(response: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Return exact final texts and call-correlated tool outputs; no guesses."""
    problems: list[str] = []
    if response.get("status") != "completed":
        problems.append("native_status_not_completed")
    if response.get("error") or response.get("incomplete_details"):
        problems.append("native_error_or_incomplete_details")
    if not response.get("id"):
        problems.append("native_response_id_missing")
    if response.get("previous_response_id"):
        problems.append("native_previous_response_context")
    outputs = response.get("output")
    if not isinstance(outputs, list):
        return {"final_texts": [], "calls": []}, problems + ["native_output_missing"]
    final_texts, calls, returns, codes = [], {}, {}, []
    for index, item in enumerate(outputs):
        if not isinstance(item, dict):
            problems.append("malformed_output_item")
            continue
        kind = item.get("type")
        prefix = f"/output/{index}"
        if kind == "message":
            if item.get("role") != "assistant" or item.get("status") != "completed":
                problems.append("unfinished_or_nonassistant_message")
            for content_index, content in enumerate(item.get("content", [])):
                if content.get("type") == "refusal":
                    problems.append("platform_refusal_not_business_answer")
                elif content.get("type") == "output_text" and isinstance(content.get("text"), str):
                    if content["text"].strip():
                        final_texts.append({
                            "pointer": f"{prefix}/content/{content_index}/text",
                            "text": content["text"],
                        })
                        if platform_content_block(content["text"]):
                            problems.append("native_platform_content_block")
        elif kind in {"function_call", "function_call_output"}:
            call_id = item.get("call_id")
            bucket = calls if kind == "function_call" else returns
            if not isinstance(call_id, str) or not call_id or call_id in bucket:
                problems.append("missing_or_duplicate_call_id")
            else:
                bucket[call_id] = {"item": item, "pointer": prefix}
            if item.get("status") not in (None, "completed"):
                problems.append("unfinished_tool_item")
            if item.get("error"):
                problems.append("tool_error")
        elif kind == "code_interpreter_call":
            if item.get("status") != "completed" or "outputs" not in item:
                problems.append("incomplete_code_interpreter_evidence")
            codes.append({"id": item.get("id"), "pointer": prefix, "item": item})
        elif kind != "reasoning":
            problems.append("unsupported_native_output_item")
    if not final_texts:
        problems.append("native_final_answer_missing")
    if set(calls) != set(returns):
        problems.append("unpaired_native_tool_calls")
    paired = []
    for call_id, call in calls.items():
        returned = returns.get(call_id)
        if returned is None:
            continue
        if "output" not in returned["item"] or returned["item"]["output"] is None:
            problems.append("native_tool_result_missing")
        paired.append({
            "call_id": call_id, "name": call["item"].get("name"),
            "arguments_pointer": call["pointer"] + "/arguments",
            "result_pointer": returned["pointer"] + "/output",
        })
    return {"final_texts": final_texts, "calls": paired, "code_calls": codes}, problems


def contains_truncation(value: Any) -> bool:
    if isinstance(value, dict):
        return any(
            (key.lower() in {"truncated", "is_truncated", "has_more", "istruncated"}
             and val is True) or contains_truncation(val)
            for key, val in value.items()
        )
    if isinstance(value, list):
        return any(contains_truncation(item) for item in value)
    if isinstance(value, str) and value.lstrip().startswith(("{", "[")):
        try:
            return contains_truncation(json.loads(value))
        except ValueError:
            return False
    return False


def _under(path: str, prefix: str) -> bool:
    return path == prefix or path.startswith(prefix + "/")


def trace_gate(
    response: dict[str, Any], view: dict[str, Any], review: dict[str, Any],
    required_languages: list[str],
) -> list[str]:
    """Require human classification of *every* call and native query/result links.

    This is provenance validation, not a SQL security parser. A reviewer must
    inspect every executed query, source scope, row completeness and result.
    A query merely proposed by a generator is not an executed-query proof.
    """
    problems, languages = [], set()
    trace = review.get("trace", {})
    if trace.get("all_steps_and_results_complete") is not True:
        problems.append("trace_completeness_not_confirmed")
    if trace.get("all_queries_scope_reviewed") is not True:
        problems.append("query_scope_not_reviewed")
    declared = trace.get("calls", [])
    actual = {call["call_id"]: call for call in view["calls"]}
    if len(declared) != len(actual) or {d.get("call_id") for d in declared} != set(actual):
        problems.append("trace_review_does_not_cover_every_call")
    for entry in declared:
        call = actual.get(entry.get("call_id"))
        if not call or not str(entry.get("note", "")).strip():
            problems.append("call_review_or_note_missing")
            continue
        queries = entry.get("queries", [])
        classification = entry.get("classification")
        if classification not in {"data", "metadata"} or (
            classification == "data" and not queries
        ) or (classification == "metadata" and queries):
            problems.append("unclassified_or_unproven_data_call")
        for query in queries:
            language = query.get("language")
            qp, rp = query.get("query_pointer", ""), query.get("result_pointer", "")
            try:
                # Query may be executed directly in arguments, or occur inside
                # a returned substep. Results can NEVER come from final prose.
                if not any(_under(qp, prefix) for prefix in (
                    call["arguments_pointer"], call["result_pointer"]
                )) or not _under(rp, call["result_pointer"]):
                    raise EvaluationError("Query/result is not linked to this native call.")
                query_text, rows = pointer(response, qp), pointer(response, rp)
                if not isinstance(query_text, str) or not query_text.strip():
                    raise EvaluationError("Executed query text is missing.")
                if not isinstance(rows, (list, dict)):
                    raise EvaluationError("A structured returned result is required.")
                if contains_truncation(rows):
                    raise EvaluationError("Returned results are truncated.")
                if not query.get("source") or language not in {"SQL", "KQL", "GQL"}:
                    raise EvaluationError("Query language/source attribution missing.")
                if query.get("executed_not_merely_generated") is not True:
                    raise EvaluationError("Execution has not been verified.")
                if query.get("complete_returned_result") is not True:
                    raise EvaluationError("Result completeness has not been verified.")
                languages.add(language)
            except EvaluationError as exc:
                problems.append(str(exc))
    codes = trace.get("code_calls", [])
    actual_codes = {c["id"] for c in view.get("code_calls", [])}
    if (len(codes) != len(actual_codes)
            or {c.get("id") for c in codes} != actual_codes
            or any(c.get("reviewed") is not True for c in codes)):
        problems.append("code_interpreter_evidence_not_reviewed")
    if not set(required_languages).issubset(languages):
        problems.append("required_executed_query_route_missing")
    return problems


def review_template(case: dict[str, Any], record: dict[str, Any]) -> dict[str, Any]:
    if record.get("protocol") == "fabric-mcp":
        from mcp_grading import review_template as mcp_review_template
        return mcp_review_template(case, record)
    response = record.get("response", {})
    view, _ = native_view(response)
    return {
        "case_id": case["id"], "record_sha256": digest(record), "reviewer": "",
        "branch": "answer", "branch_evidence_pointer": "", "branch_note": "",
        "data_matches_frozen_fixture": False,
        "platform_block_detected": False,
        "trace": {
            "all_steps_and_results_complete": False,
            "all_queries_scope_reviewed": False,
            "calls": [{
                **call, "classification": "", "note": "", "queries": [],
            } for call in view["calls"]],
            "code_calls": [{
                "id": call["id"], "reviewed": False,
            } for call in view.get("code_calls", [])],
        },
        "conditions": [{
            "id": c["id"], "verdict": "UNCLEAR", "note": "", "evidence": [],
        } for c in case["conditions"]],
    }


def grade_case(
    case: dict[str, Any], record: dict[str, Any] | None, review: dict[str, Any] | None,
) -> dict[str, Any]:
    """Score every condition. Missing evidence never reduces the denominator."""
    count = len(case["conditions"])
    base = {"case_id": case["id"], "total_conditions": count, "question_pass": False}
    if record is None or review is None:
        if record is not None and record.get("protocol") == "fabric-mcp":
            from mcp_grading import grade_case as grade_mcp_case
            return grade_mcp_case(case, record, review)
        return {**base, "pass": 0, "fail": count, "na": 0,
                "gate_errors": ["not_run" if record is None else "not_reviewed"]}
    if record.get("protocol") == "fabric-mcp":
        from mcp_grading import grade_case as grade_mcp_case
        return grade_mcp_case(case, record, review)
    problems = []
    if record.get("status") != "completed":
        problems.append("capture_not_completed")
    if record.get("case_id") != case["id"] or record.get("question") != case["question"]:
        problems.append("question_identity_mismatch")
    if record.get("submission_count") != 1 or record.get("fresh_conversation") is not True:
        problems.append("not_exactly_one_fresh_submission")
    if (not record.get("configuration_before_sha256")
            or record.get("configuration_before_sha256") != record.get("configuration_after_sha256")):
        problems.append("configuration_missing_or_changed")
    if review.get("record_sha256") != digest(record) or review.get("case_id") != case["id"]:
        problems.append("review_record_hash_or_identity_mismatch")
    if not str(review.get("reviewer", "")).strip():
        problems.append("reviewer_missing")
    if review.get("data_matches_frozen_fixture") is not True:
        problems.append("deployed_data_fixture_not_verified")
    if review.get("platform_block_detected") is not False:
        problems.append("platform_block_or_unreviewed_platform_status")
    response = record.get("response", {})
    view, native_problems = native_view(response)
    problems += native_problems
    if contains_truncation(response):
        problems.append("truncated_native_evidence")
    branch = review.get("branch")
    allowed_na: frozenset[str] = frozenset()
    required_routes = case["required_query_languages"]
    if branch == "clarification":
        if case["id"] != "T03":
            problems.append("clarification_not_allowed_for_this_case")
        else:
            # The human confirms the meaning; the pointer proves the cited
            # clarification is in the unchanged native final answer.
            allowed_na = T03_NA
            required_routes = []
            final_pointers = {v["pointer"] for v in view["final_texts"]}
            if (review.get("branch_evidence_pointer") not in final_pointers
                    or not str(review.get("branch_note", "")).strip()):
                problems.append("clarification_branch_not_evidenced")
    elif branch != "answer":
        problems.append("unknown_answer_branch")
    problems += trace_gate(response, view, review, required_routes)
    rows = review.get("conditions", [])
    citation_prefixes = (
        [v["pointer"] for v in view["final_texts"]]
        + [c[key] for c in view["calls"] for key in ("arguments_pointer", "result_pointer")]
        + [c["pointer"] + suffix for c in view.get("code_calls", []) for suffix in ("/code", "/outputs")]
    )
    expected_ids = [c["id"] for c in case["conditions"]]
    if (len(rows) != count or len({r.get("id") for r in rows}) != count
            or {r.get("id") for r in rows} != set(expected_ids)):
        problems.append("rubric_condition_set_changed")
    results = []
    for row in rows:
        verdict = row.get("verdict")
        note = str(row.get("note", "")).strip()
        if verdict == "NA":
            if row.get("id") not in allowed_na or not note:
                problems.append("illegal_na")
        elif verdict not in {"PASS", "FAIL", "UNCLEAR"}:
            problems.append("invalid_verdict")
        if verdict == "PASS":
            references = row.get("evidence", [])
            if not note or not references:
                problems.append("pass_without_explanation_and_evidence")
            for reference in references:
                try:
                    if not any(_under(reference, prefix) for prefix in citation_prefixes):
                        raise EvaluationError("Citation is not final text or a native tool argument/result.")
                    value = pointer(response, reference)
                    if value is None or value == "":
                        problems.append("pass_cites_empty_native_evidence")
                except EvaluationError:
                    problems.append("pass_cites_missing_native_evidence")
        results.append("FAIL" if verdict == "UNCLEAR" else verdict)
    if problems:
        return {**base, "pass": 0, "fail": count, "na": 0,
                "gate_errors": sorted(set(problems))}
    passed, failed, na = (results.count(value) for value in ("PASS", "FAIL", "NA"))
    return {**base, "question_pass": failed == 0 and passed > 0,
            "pass": passed, "fail": failed, "na": na, "gate_errors": []}


def summarize(cases: list[dict[str, Any]]) -> dict[str, Any]:
    total = sum(c["total_conditions"] for c in cases)
    passed, failed, na = (sum(c[k] for c in cases) for k in ("pass", "fail", "na"))
    if passed + failed + na != total:
        raise EvaluationError("Condition denominator mismatch.")
    return {
        "question_pass": sum(c["question_pass"] for c in cases),
        "question_total": len(cases), "condition_pass": passed,
        "condition_fail": failed, "condition_na": na, "condition_total": total,
        "condition_applicable": total - na,
        "all_questions_pass": bool(cases) and all(c["question_pass"] for c in cases),
    }
