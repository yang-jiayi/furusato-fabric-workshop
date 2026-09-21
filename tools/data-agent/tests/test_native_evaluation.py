"""Offline tests only; synthetic answers are not workshop answer keys."""

from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import native_evaluation as ne


def example_case(case_id="T01", languages=None, condition_ids=None):
    return {
        "id": case_id, "question": "Synthetic offline question.",
        "required_query_languages": ["SQL"] if languages is None else languages,
        "conditions": [{
            "id": key, "text": "Synthetic condition; not a workshop expected answer.",
        } for key in (condition_ids or [case_id + ".example"])],
    }


def example_response(with_call=True):
    output = []
    if with_call:
        output += [
            {"type": "function_call", "call_id": "call-fixture", "name": "fixture_query",
             "status": "completed", "arguments": json.dumps({"query": "SELECT marker FROM fixture"})},
            {"type": "function_call_output", "call_id": "call-fixture",
             "output": json.dumps({"rows": [{"marker": "example"}]})},
        ]
    output.append({
        "type": "message", "role": "assistant", "status": "completed",
        "content": [{"type": "output_text", "text": "Native synthetic final answer."}],
    })
    return {"id": "response-fixture", "status": "completed", "output": output}


def example_record(case=None, with_call=True):
    case = case or example_case()
    return {
        "case_id": case["id"], "question": case["question"], "status": "completed",
        "fresh_conversation": True, "submission_count": 1,
        "configuration_before_sha256": ne.digest({"fixture": True}),
        "configuration_after_sha256": ne.digest({"fixture": True}),
        "response": example_response(with_call),
    }


def approved_review(case, record):
    review = ne.review_template(case, record)
    view, _ = ne.native_view(record["response"])
    final = view["final_texts"][0]["pointer"]
    review.update(reviewer="Offline fixture reviewer", data_matches_frozen_fixture=True)
    review["trace"].update(all_steps_and_results_complete=True, all_queries_scope_reviewed=True)
    for entry in review["trace"]["calls"]:
        entry.update(classification="data", note="Synthetic complete execution/result.")
        entry["queries"] = [{
            "language": "SQL", "source": "synthetic fixture",
            "query_pointer": entry["arguments_pointer"] + "/@json/query",
            "result_pointer": entry["result_pointer"] + "/@json/rows",
            "executed_not_merely_generated": True, "complete_returned_result": True,
        }]
    for row in review["conditions"]:
        row.update(verdict="PASS", note="Synthetic human decision.", evidence=[final])
    return review


class GradingTests(unittest.TestCase):
    def setUp(self):
        self.case = example_case()
        self.record = example_record(self.case)
        self.review = approved_review(self.case, self.record)

    def grade(self):
        self.review["record_sha256"] = ne.digest(self.record)
        return ne.grade_case(self.case, self.record, self.review)

    def assertBlocked(self):
        result = self.grade()
        self.assertFalse(result["question_pass"])
        self.assertEqual(result["fail"], len(self.case["conditions"]))
        self.assertEqual(result["na"], 0)
        self.assertTrue(result["gate_errors"])
        return result

    def test_fully_evidenced_case_passes(self):
        self.assertTrue(self.grade()["question_pass"])

    def test_service_block_inside_completed_response_still_fails(self):
        self.record["response"]["output"][-1]["content"][0]["text"] = (
            "There's content here I can't work with. Try asking a new question."
        )
        result = self.assertBlocked()
        self.assertIn("native_platform_content_block", result["gate_errors"])

    def test_explicit_business_refusal_is_not_the_service_block(self):
        self.assertFalse(ne.platform_content_block(
            "These synthetic records cannot establish income or personal tax advice."
        ))

    def test_missing_record_stays_in_denominator(self):
        result = ne.grade_case(self.case, None, None)
        self.assertEqual(result["fail"], 1)
        self.assertIn("not_run", result["gate_errors"])

    def test_missing_review_is_not_a_pass(self):
        self.assertFalse(ne.grade_case(self.case, self.record, None)["question_pass"])

    def test_unclear_is_fail_not_na(self):
        self.review["conditions"][0]["verdict"] = "UNCLEAR"
        result = self.grade()
        self.assertEqual((result["pass"], result["fail"], result["na"]), (0, 1, 0))

    def test_partial_condition_pass_does_not_pass_question(self):
        self.case = example_case(condition_ids=["one", "two"])
        self.record = example_record(self.case)
        self.review = approved_review(self.case, self.record)
        self.review["conditions"][1]["verdict"] = "FAIL"
        result = self.grade()
        self.assertEqual(result["pass"], 1)
        self.assertFalse(result["question_pass"])

    def test_platform_states_fail_closed(self):
        for status in ("in_progress", "queued", "failed", "cancelled", "incomplete"):
            with self.subTest(status=status):
                self.record["response"]["status"] = status
                self.assertBlocked()

    def test_platform_refusal_is_not_business_refusal(self):
        self.record["response"]["output"][-1]["content"] = [
            {"type": "refusal", "refusal": "Platform refused."}
        ]
        self.assertBlocked()

    def test_explicit_platform_block_detection(self):
        self.review["platform_block_detected"] = True
        self.assertBlocked()

    def test_native_business_refusal_can_have_zero_queries(self):
        self.case = example_case("T10", [])
        self.record = example_record(self.case, with_call=False)
        self.review = approved_review(self.case, self.record)
        self.assertTrue(self.grade()["question_pass"])

    def test_numeric_answer_without_required_query_cannot_pass(self):
        self.record = example_record(self.case, with_call=False)
        self.review = approved_review(self.case, self.record)
        self.assertBlocked()

    def test_configuration_drift_is_not_waived(self):
        self.record["configuration_after_sha256"] = ne.digest({"different": True})
        self.assertBlocked()

    def test_missing_configuration_proof(self):
        del self.record["configuration_before_sha256"]
        self.assertBlocked()

    def test_wrong_question(self):
        self.record["question"] += " additional instruction"
        self.assertBlocked()

    def test_context_or_duplicate_send(self):
        for key, value in (("fresh_conversation", False), ("submission_count", 2)):
            with self.subTest(key=key):
                saved = self.record[key]
                self.record[key] = value
                self.assertBlocked()
                self.record[key] = saved

    def test_previous_response_context(self):
        self.record["response"]["previous_response_id"] = "previous-fixture"
        self.assertBlocked()

    def test_stale_review_hash(self):
        self.record["response"]["output"][-1]["content"][0]["text"] += " edited"
        result = ne.grade_case(self.case, self.record, self.review)
        self.assertIn("review_record_hash_or_identity_mismatch", result["gate_errors"])

    def test_missing_unpaired_or_duplicate_tool_output(self):
        for mutate in (
            lambda r: r["output"].pop(1),
            lambda r: r["output"].append(copy.deepcopy(r["output"][1])),
            lambda r: r["output"][1].update(call_id="other-call"),
        ):
            with self.subTest(mutate=mutate):
                self.record["response"] = example_response()
                mutate(self.record["response"])
                self.assertBlocked()

    def test_call_coverage_is_required(self):
        self.review["trace"]["calls"] = []
        self.assertBlocked()

    def test_completeness_and_scope_must_both_be_confirmed(self):
        for field in ("all_steps_and_results_complete", "all_queries_scope_reviewed"):
            with self.subTest(field=field):
                self.review["trace"][field] = False
                self.assertBlocked()
                self.review["trace"][field] = True

    def test_external_result_or_final_prose_cannot_fill_tool_output(self):
        self.review["trace"]["calls"][0]["queries"][0]["result_pointer"] = (
            "/output/2/content/0/text"
        )
        self.assertBlocked()

    def test_query_merely_generated_does_not_count_as_executed(self):
        self.review["trace"]["calls"][0]["queries"][0]["executed_not_merely_generated"] = False
        self.assertBlocked()

    def test_native_empty_rows_are_valid_returned_results(self):
        self.record["response"]["output"][1]["output"] = json.dumps({"rows": []})
        self.assertTrue(self.grade()["question_pass"])

    def test_missing_rows_are_not_empty_results(self):
        self.record["response"]["output"][1]["output"] = json.dumps({"rows": None})
        self.assertBlocked()

    def test_truncated_results_fail_even_with_correct_final(self):
        self.record["response"]["output"][1]["output"] = json.dumps({
            "rows": {"rows": [{"marker": "example"}], "has_more": True},
        })
        self.assertBlocked()

    def test_truncation_marker_outside_rows_in_encoded_output_also_fails(self):
        self.record["response"]["output"][1]["output"] = json.dumps({
            "rows": [{"marker": "example"}], "has_more": True,
        })
        self.assertBlocked()

    def test_condition_cannot_cite_run_id_or_whole_response_as_evidence(self):
        for reference in ("/id", ""):
            with self.subTest(reference=reference):
                self.review["conditions"][0]["evidence"] = [reference]
                self.assertBlocked()

    def test_unknown_output_shape_fails(self):
        self.record["response"]["output"].insert(0, {"type": "unknown_tool_type"})
        self.assertBlocked()

    def test_missing_native_final_is_not_filled_from_output_text(self):
        self.record["response"]["output"].pop()
        self.record["response"]["output_text"] = "Convenience fallback."
        self.assertBlocked()

    def test_unfinished_message_fails(self):
        self.record["response"]["output"][-1]["status"] = "in_progress"
        self.assertBlocked()

    def test_pass_needs_evidence_and_explanation(self):
        for key, value in (("note", ""), ("evidence", []), ("evidence", ["/not-there"])):
            with self.subTest(key=key, value=value):
                self.review = approved_review(self.case, self.record)
                self.review["conditions"][0][key] = value
                self.assertBlocked()

    def test_deleted_or_duplicate_rubric_rows_fail(self):
        for rows in ([], [self.review["conditions"][0]] * 2):
            with self.subTest(rows=rows):
                self.review["conditions"] = rows
                self.assertBlocked()

    def test_na_not_allowed_in_normal_branch(self):
        self.review["conditions"][0]["verdict"] = "NA"
        self.assertBlocked()

    def test_clarification_not_allowed_outside_original_t03(self):
        self.review["branch"] = "clarification"
        self.assertBlocked()

    def test_original_t03_retains_exact_three_numeric_na_conditions(self):
        condition_ids = [
            "T03.evidence.1", "T03.evidence.2", "T03.evidence.3",
            "T03.pass_criteria.1", "T03.pass_criteria.2", "T03.pass_criteria.3",
        ]
        self.case = example_case("T03", ["SQL"], condition_ids)
        self.record = example_record(self.case, with_call=False)
        self.review = approved_review(self.case, self.record)
        self.review.update(
            branch="clarification", branch_evidence_pointer="/output/0/content/0/text",
            branch_note="Human checked both meanings are explicitly offered for clarification.",
        )
        for row in self.review["conditions"]:
            if row["id"] in ne.T03_NA:
                row.update(verdict="NA", note="Numeric-only row on the guide's clarification branch.")
        result = self.grade()
        self.assertTrue(result["question_pass"])
        self.assertEqual((result["pass"], result["fail"], result["na"]), (3, 0, 3))
        self.review["conditions"][2]["verdict"] = "NA"
        self.assertBlocked()

    def test_unreviewed_code_execution_fails(self):
        self.record["response"]["output"].append({
            "type": "code_interpreter_call", "id": "code-fixture",
            "status": "completed", "code": "print('example')", "outputs": [],
        })
        self.assertBlocked()


class ParsingTests(unittest.TestCase):
    def test_raw_json_roundtrip_keeps_exact_answer(self):
        response = example_response()
        self.assertEqual(ne.parse_native_body(ne.encode(response)), response)

    def test_terminal_sse_with_crlf_and_done(self):
        response = example_response()
        body = (
            "event: response.completed\r\ndata: "
            + json.dumps({"type": "response.completed", "response": response})
            + "\r\n\r\ndata: [DONE]\r\n\r\n"
        ).encode()
        self.assertEqual(ne.parse_native_body(body), response)

    def test_delta_only_sse_is_never_a_completed_answer(self):
        with self.assertRaises(ne.EvaluationError):
            ne.parse_native_body(b'data: {"type":"response.output_text.delta","delta":"answer"}\n\n')

    def test_missing_final_output_not_reconstructed_from_stream_items(self):
        response = {"id": "fixture", "status": "completed", "output": []}
        body = b'data: {"type":"response.output_text.done","text":"answer"}\n\n'
        body += b"data: " + json.dumps({"type": "response.completed", "response": response}).encode() + b"\n\n"
        view, issues = ne.native_view(ne.parse_native_body(body))
        self.assertEqual(view["final_texts"], [])
        self.assertIn("native_final_answer_missing", issues)

    def test_conflicting_terminal_states_fail(self):
        payload = {"type": "response.completed", "response": {"status": "failed"}}
        with self.assertRaises(ne.EvaluationError):
            ne.parse_native_body(b"data: " + ne.encode(payload).replace(b"\n", b"") + b"\n\n")

    def test_multiple_terminal_responses_fail(self):
        payload = json.dumps({"type": "response.completed", "response": example_response()}).encode()
        with self.assertRaises(ne.EvaluationError):
            ne.parse_native_body((b"data: " + payload + b"\n\n") * 2)

    def test_json_pointer_requires_explicit_json_decoding(self):
        value = {"x": json.dumps({"a/b": [{"~c": "original"}]})}
        self.assertEqual(ne.pointer(value, "/x/@json/a~1b/0/~0c"), "original")
        for path in ("/x/a~1b", "/x/@json/missing", "/x/@json/a~1b/-1"):
            with self.subTest(path=path), self.assertRaises(ne.EvaluationError):
                ne.pointer(value, path)


class StorageAndProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=os.environ.get("EVALUATION_TEST_TEMP"))
        self.root = Path(self.temp.name)
        self.store = ne.PrivateStore(self.root / "private")

    def tearDown(self):
        self.temp.cleanup()

    def test_no_overwrite(self):
        self.store.write("record.json", {"one": True})
        with self.assertRaises(FileExistsError):
            self.store.write("record.json", {"two": True})

    def test_path_escape_and_absolute_rejected(self):
        for path in ("../outside", self.root / "outside"):
            with self.subTest(path=path), self.assertRaises(ne.EvaluationError):
                self.store.path(path)

    def test_any_git_checkout_rejected_including_worktree_git_file(self):
        repo = self.root / "repo"
        repo.mkdir()
        (repo / ".git").write_text("gitdir: unused", encoding="utf-8")
        with self.assertRaises(ne.EvaluationError):
            ne.PrivateStore(repo / "evidence")

    def test_nested_git_checkouts_reject_every_input_and_output_path(self):
        for kind in ("directory", "worktree-file"):
            with self.subTest(kind=kind):
                repo = self.store.root / kind / "repo"
                repo.mkdir(parents=True)
                if kind == "directory":
                    (repo / ".git").mkdir()
                else:
                    (repo / ".git").write_text("gitdir: unused", encoding="utf-8")
                relative = Path(kind) / "repo" / "evidence" / "answer.json"
                with self.assertRaises(ne.EvaluationError):
                    self.store.path(relative)
                with self.assertRaises(ne.EvaluationError):
                    self.store.input_path(self.store.root / relative)
                with self.assertRaises(ne.EvaluationError):
                    self.store.write(relative, {"must_not_be_written": True})
                self.assertFalse((repo / "evidence").exists())

    def test_checkout_created_after_store_initialization_is_rejected(self):
        repo = self.store.root / "later"
        self.assertEqual(self.store.path("later/answer.json"), repo / "answer.json")
        repo.mkdir()
        (repo / ".git").mkdir()
        with self.assertRaises(ne.EvaluationError):
            self.store.path("later/answer.json")

    def test_symlink_escape_rejected(self):
        outside = self.root / "outside"
        outside.mkdir()
        try:
            (self.store.root / "link").symlink_to(outside, target_is_directory=True)
        except OSError:
            self.skipTest("Host does not allow test symlinks.")
        with self.assertRaises(ne.EvaluationError):
            self.store.path("link/raw.json")

    def test_private_input_must_be_inside_evidence_root(self):
        with self.assertRaises(ne.EvaluationError):
            self.store.input_path(self.root / "elsewhere.json")

    def test_heldout_cannot_impersonate_original_ids(self):
        with self.assertRaises(ne.EvaluationError):
            ne.validate_suite({"schema_version": 1, "kind": "heldout", "cases": [example_case()]})

    def test_frozen_suite_tampering_detected(self):
        suite = {"schema_version": 1, "kind": "heldout", "cases": [example_case("H01")]}
        ne.freeze_suite(self.store, "heldout.json", suite)
        frozen = self.store.read("heldout.json")
        frozen["suite"]["cases"][0]["question"] += " altered"
        # Intentional corruption of a synthetic test fixture, not a real capture.
        self.store.path("heldout.json").write_bytes(ne.encode(frozen))
        with self.assertRaises(ne.EvaluationError):
            ne.load_suite(self.store, "heldout.json")

    def test_exact_shared_guide_and_84_conditions_no_answers_logged(self):
        repo = Path(__file__).resolve().parents[3]
        suite = ne.original_suite(repo)
        self.assertEqual([c["id"] for c in suite["cases"]], [f"T{i:02}" for i in range(1, 11)])
        self.assertEqual(sum(len(c["conditions"]) for c in suite["cases"]), 84)
        from furusato_docs.context import load_context
        from furusato_docs.facts import compute_facts
        from furusato_docs.tests10 import build_tests
        context = load_context(repo)
        for source, frozen in zip(build_tests(context, compute_facts(context)), suite["cases"]):
            self.assertEqual(frozen["question"], source.question)
            self.assertEqual([c["text"] for c in frozen["conditions"]],
                             list(source.evidence) + list(source.pass_criteria))

    def test_denominators_keep_na_separate(self):
        summary = ne.summarize([
            {"total_conditions": 6, "pass": 3, "fail": 0, "na": 3, "question_pass": True},
            {"total_conditions": 2, "pass": 1, "fail": 1, "na": 0, "question_pass": False},
        ])
        self.assertEqual(summary["question_pass"], 1)
        self.assertEqual(summary["condition_total"], 8)
        self.assertEqual(summary["condition_applicable"], 5)
        self.assertFalse(summary["all_questions_pass"])


if __name__ == "__main__":
    unittest.main()
