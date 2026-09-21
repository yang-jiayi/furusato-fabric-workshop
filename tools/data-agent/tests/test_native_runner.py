"""Native transport contract tests: all HTTP/SDK operations are fakes."""

from __future__ import annotations

import base64
import copy
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import evaluate_native as runner
import native_evaluation as ne
from test_native_evaluation import approved_review, example_case, example_response


def definition(marker="fixture"):
    return {"definition": {"parts": [{
        "path": "Files/Config/production/stage_config.json",
        "payloadType": "InlineBase64",
        "payload": base64.b64encode(ne.encode({"marker": marker})).decode(),
    }]}}


class FakeClient:
    def __init__(self):
        self.submissions = []
        self.retrievals = 0
        self.response = example_response()
        self.diagnostic_calls = []

    def new_conversation(self):
        return runner.RawReply(ne.encode({"id": "conversation-fixture"}))

    def submit(self, question, conversation_id):
        self.submissions.append(question)
        return runner.RawReply(ne.encode(self.response), request_body=ne.encode({
            "input": question, "conversation": conversation_id,
            "model": "server-default-fixture", "stream": False,
        }))

    def retrieve(self, response_id):
        self.retrievals += 1
        return runner.RawReply(ne.encode(self.response))

    def diagnostics(self, conversation_id, response_id):
        self.diagnostic_calls.append((conversation_id, response_id))
        return {"fixture_diagnostics": True}


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=os.environ.get("EVALUATION_TEST_TEMP"))
        self.store = ne.PrivateStore(Path(self.temp.name) / "private")
        self.client = FakeClient()
        self.case = example_case()
        self.baseline = definition()
        self.read_definition = lambda: self.baseline

    def tearDown(self):
        self.temp.cleanup()

    def capture(self, relative="batch/T01", **kwargs):
        return runner.capture_case(
            self.store, relative, self.case, self.client, self.read_definition,
            runner.definition_digest(self.baseline), set(), 10, **kwargs,
        )

    def test_one_original_wire_question_no_instructions_or_rewriting(self):
        record = self.capture()
        self.assertEqual(self.client.submissions, [self.case["question"]])
        self.assertEqual(record["status"], "completed")
        self.assertEqual(record["response"], self.client.response)
        self.assertEqual(len(self.client.diagnostic_calls), 1)
        runner.verify_record(self.store, record)
        review = self.store.read("batch/T01/review.json")
        self.assertTrue(all(r["verdict"] == "UNCLEAR" for r in review["conditions"]))

    def test_ambiguous_question_post_not_retried(self):
        def fail(question, conversation_id):
            self.client.submissions.append(question)
            raise TimeoutError("Synthetic network ambiguity.")
        self.client.submit = fail
        record = self.capture()
        self.assertEqual(record["status"], "submission_outcome_unknown")
        self.assertEqual(len(self.client.submissions), 1)
        self.assertEqual(self.client.retrievals, 0)

    def test_existing_slot_cannot_be_rerun(self):
        self.capture()
        with self.assertRaises(FileExistsError):
            self.capture()
        self.assertEqual(len(self.client.submissions), 1)

    def test_before_definition_drift_prevents_question(self):
        self.read_definition = lambda: definition("changed")
        record = self.capture()
        self.assertNotEqual(record["status"], "completed")
        self.assertEqual(self.client.submissions, [])

    def test_after_definition_drift_invalidates_capture(self):
        sequence = iter([definition(), definition("changed")])
        self.read_definition = lambda: next(sequence)
        record = self.capture()
        self.assertEqual(record["status"], "configuration_changed")
        self.assertEqual(len(self.client.submissions), 1)

    def test_missing_after_definition_is_not_success(self):
        calls = []
        def reader():
            calls.append(True)
            if len(calls) == 2:
                raise TimeoutError()
            return definition()
        self.read_definition = reader
        self.assertEqual(self.capture()["status"], "configuration_unverified")

    def test_expired_run_stays_failed_not_business_refusal(self):
        self.client.response["status"] = "failed"
        self.client.response["error"] = {"code": "fixture_content_filter"}
        record = self.capture()
        self.assertNotEqual(record["status"], "completed")
        self.assertEqual(len(self.client.submissions), 1)
        self.assertEqual(record["status"], "native_failure_captured")

    def test_completed_envelope_with_service_block_is_not_a_business_answer(self):
        message = "There's content here I can't work with. Try asking a new question."
        self.client.response["output"][-1]["content"][0]["text"] = message
        record = self.capture()
        self.assertEqual(record["status"], "native_failure_captured")
        self.assertIn("native_platform_content_block", record["native_structure_issues"])
        self.assertEqual(record["native_final_texts"][0]["text"], message)
        self.assertEqual(len(self.client.submissions), 1)

    def test_running_poll_deadline_fails(self):
        self.client.response["status"] = "in_progress"
        times = iter([0, 11])
        record = self.capture(monotonic=lambda: next(times), sleep=lambda _: None)
        self.assertEqual(record["status"], "unfinished_timeout")
        self.assertEqual(len(self.client.submissions), 1)

    def test_raw_answer_tampering_detected(self):
        record = self.capture()
        self.store.path(record["response_artifact"]).write_bytes(ne.encode({"edited": True}))
        with self.assertRaises(ne.EvaluationError):
            runner.verify_record(self.store, record)

    def test_parsed_answer_tampering_detected(self):
        record = self.capture()
        record["response"]["output"][-1]["content"][0]["text"] = "Externally corrected."
        with self.assertRaises(ne.EvaluationError):
            runner.verify_record(self.store, record)

    def test_diagnostics_failure_does_not_send_again(self):
        self.client.diagnostics = lambda *args: (_ for _ in ()).throw(TimeoutError())
        record = self.capture()
        self.assertEqual(record["status"], "evidence_incomplete")
        self.assertEqual(len(self.client.submissions), 1)

    def feature_gate(self, message="Data Agent diagnostics feature is not enabled."):
        def fail(*args):
            raise runner.NativeEvidenceError("Native diagnostics HTTP 403; no question retry.", ne.encode({
                "Message": message, "Source": "AISKILL", "error_code": "PERMISSION_DENIED",
            }), 403)
        self.client.diagnostics = fail

    def test_optional_diagnostic_feature_gate_preserves_native_response_and_error(self):
        self.feature_gate()
        record = self.capture()
        self.assertEqual(record["status"], "completed")
        self.assertEqual(record["diagnostics_status"], "feature_unavailable")
        self.assertEqual(record["response"], self.client.response)
        self.assertEqual(len(self.client.submissions), 1)
        self.assertFalse(self.store.path("batch/T01/diagnostics.json").exists())
        runner.verify_record(self.store, record)
        self.assertTrue(all(row["verdict"] == "UNCLEAR"
                            for row in self.store.read("batch/T01/review.json")["conditions"]))

    def test_feature_gate_does_not_waive_missing_native_call_outputs(self):
        self.feature_gate()
        self.client.response["output"] = [
            item for item in self.client.response["output"]
            if item["type"] != "function_call_output"
        ]
        record = self.capture()
        self.assertEqual(record["status"], "evidence_incomplete")
        self.assertIn("unpaired_native_tool_calls", record["native_structure_issues"])

    def test_other_diagnostic_permission_errors_remain_blocking(self):
        self.feature_gate(message="Access denied.")
        record = self.capture()
        self.assertEqual(record["status"], "evidence_incomplete")
        self.assertNotIn("diagnostics_status", record)
        self.assertEqual(len(self.client.submissions), 1)

    def test_feature_gate_receipt_cannot_be_relabelled_as_another_response(self):
        self.feature_gate()
        record = self.capture()
        receipt_path = "batch/T01/diagnostics-unavailable.json"
        receipt = self.store.read(receipt_path)
        receipt["response_id"] = "different-response"
        self.store.path(receipt_path).write_bytes(ne.encode(receipt))
        for artifact in record["artifacts"]:
            if artifact["path"] == receipt_path:
                artifact["sha256"] = ne.file_digest(self.store.path(receipt_path))
        with self.assertRaises(ne.EvaluationError):
            runner.verify_record(self.store, record)

    def test_foreign_wire_question_fails(self):
        original_submit = self.client.submit
        self.client.submit = lambda q, c: original_submit(q + "changed", c)
        record = self.capture()
        self.assertNotEqual(record["status"], "completed")
        self.assertEqual(record["submission_count"], 1)
        self.assertEqual(
            self.store.path(record["response_artifact"]).read_bytes(),
            ne.encode(self.client.response),
        )
        self.assertEqual(self.client.retrievals, 0)

    def test_malformed_wire_request_retains_received_native_reply(self):
        original_submit = self.client.submit

        def submit(question, conversation_id):
            reply = original_submit(question, conversation_id)
            return runner.RawReply(reply.body, request_body=b"{malformed")

        self.client.submit = submit
        record = self.capture()
        self.assertNotEqual(record["status"], "completed")
        self.assertEqual(len(self.client.submissions), 1)
        self.assertEqual(record["last_http_status"], 200)
        self.assertEqual(self.store.path(record["request_artifact"]).read_bytes(), b"{malformed")
        self.assertEqual(
            self.store.path(record["response_artifact"]).read_bytes(),
            ne.encode(self.client.response),
        )

    def test_response_conversation_mismatch_fails(self):
        self.client.response["conversation"] = {"id": "another-conversation"}
        self.assertNotEqual(self.capture()["status"], "completed")

    def test_configuration_hashes_must_reference_actual_native_snapshot(self):
        record = self.capture()
        record["configuration_before_sha256"] = ne.digest({"replaced": True})
        record["configuration_after_sha256"] = record["configuration_before_sha256"]
        with self.assertRaises(ne.EvaluationError):
            runner.verify_record(self.store, record)

    def test_no_explicit_online_opt_in_never_constructs_client(self):
        with patch.object(runner, "run_batch") as run:
            result = runner.main([
                "--private-root", str(self.store.root), "run", "--plan", "missing.json",
                "--configuration", "candidate", "--suite", "original", "--repeat", "1",
            ])
        self.assertEqual(result, 2)
        run.assert_not_called()

    def test_native_http_deployment_requires_capacity_and_observed_host(self):
        self.store.write("data.json", {"fixture": True})
        value = {
            "label": "candidate", "workspace_id": str(UUID(int=1)),
            "data_agent_id": str(UUID(int=2)), "stage": "production",
            "data_fingerprint_file": "data.json", "transport": "responses-http",
            "capacity_id": str(UUID(int=3)),
            "workload_host": "https://wabi-offline-fixture.analysis.windows.net/",
        }
        validated = runner.validate_deployment(self.store, {"configurations": [value]})[0]
        self.assertEqual(validated["native_protocol_contract"], runner.PROTOCOL_VERSION)
        self.assertEqual(validated["transport"], "responses-http")
        for field in ("capacity_id", "workload_host"):
            broken = dict(value)
            del broken[field]
            with self.subTest(field=field), self.assertRaises(ne.EvaluationError):
                runner.validate_deployment(self.store, {"configurations": [broken]})

    def test_definition_digest_ignores_json_and_part_order_not_content(self):
        first = definition()
        second = copy.deepcopy(first)
        second["definition"]["parts"][0]["payload"] = base64.b64encode(
            b'{ "marker" : "fixture" }'
        ).decode()
        self.assertEqual(runner.definition_digest(first), runner.definition_digest(second))
        self.assertNotEqual(runner.definition_digest(first), runner.definition_digest(definition("other")))

    def test_definition_lro_polls_public_operation_id_not_regional_location(self):
        operation_id = str(UUID(int=9))
        replies = []
        for status, headers, body in (
            (202, {"x-ms-operation-id": operation_id,
                   "Location": f"https://wabi-offline-fixture.analysis.windows.net/v1/operations/{operation_id}"}, None),
            (200, {}, {"status": "Succeeded"}),
            (200, {}, definition()),
        ):
            reply = MagicMock()
            reply.__enter__.return_value = reply
            reply.status_code, reply.headers = status, headers
            reply.json.return_value = body
            replies.append(reply)
        reader = runner.DefinitionReader(credential=None)
        try:
            with patch.object(reader, "request", side_effect=replies) as request:
                actual = reader.read({"workspace_id": str(UUID(int=1)), "data_agent_id": str(UUID(int=2))})
            self.assertEqual(actual, definition())
            self.assertEqual(request.call_args_list[1].args,
                             ("GET", f"https://api.fabric.microsoft.com/v1/operations/{operation_id}"))
            self.assertEqual(request.call_args_list[2].args,
                             ("GET", f"https://api.fabric.microsoft.com/v1/operations/{operation_id}/result"))
        finally:
            reader.close()

    def test_private_plan_requires_ids_but_does_no_network(self):
        original = ne.original_suite(Path(__file__).resolve().parents[3])
        heldout = {"schema_version": 1, "kind": "heldout", "cases": [example_case("H01")]}
        ne.freeze_suite(self.store, "original.json", original)
        ne.freeze_suite(self.store, "heldout.json", heldout)
        self.store.write("data.json", {"fixture": True})
        deployment = {"configurations": [{
            "label": "candidate", "workspace_id": str(UUID(int=1)),
            "data_agent_id": str(UUID(int=2)), "stage": "production",
            "data_fingerprint_file": "data.json",
        }]}
        with patch.object(runner, "NativeClient") as client:
            relative = runner.create_plan(
                self.store, "example", deployment, "original.json", "heldout.json", 3, 1,
            )
        client.assert_not_called()
        plan = runner.load_plan(self.store, relative)
        report = runner.report_campaign(self.store, plan)
        original_group = next(g for g in report["groups"] if g["suite"] == "original")
        self.assertEqual(original_group["planned_runs"], 3)
        self.assertEqual(original_group["all_repeats"]["question_total"], 30)
        self.assertEqual(original_group["all_repeats"]["condition_fail"], 84 * 3)
        self.assertFalse(report["acceptance"])
        self.assertEqual(len(report["batches"]), 4)
        self.assertTrue(all("batch_unfinished_or_incomplete" in b["batch_gate_errors"]
                            for b in report["batches"]))

    def test_repetition_overrides_are_frozen_per_configuration(self):
        original = ne.original_suite(Path(__file__).resolve().parents[3])
        heldout = {"schema_version": 1, "kind": "heldout", "cases": [example_case("H01")]}
        ne.freeze_suite(self.store, "original.json", original)
        ne.freeze_suite(self.store, "heldout.json", heldout)
        self.store.write("data.json", {"fixture": True})
        configurations = [{
            "label": name, "workspace_id": str(UUID(int=1)),
            "data_agent_id": str(UUID(int=index)), "stage": "production",
            "data_fingerprint_file": "data.json", "original_repeats": repeat,
            "heldout_repeats": 1,
        } for index, (name, repeat) in enumerate((("core", 1), ("reference", 2), ("ci", 1)), 2)]
        path = runner.create_plan(
            self.store, "schedule", {"configurations": configurations},
            "original.json", "heldout.json", 3, 1,
        )
        plan = runner.load_plan(self.store, path)
        self.assertEqual([s["configuration"] for s in plan["slots"] if s["suite"] == "original"],
                         ["core", "reference", "reference", "ci"])
        self.assertEqual(len(plan["slots"]), 7)

    def synthetic_campaign(self):
        """Exercise the entire file/plan/review protocol with no workshop answers."""
        original = {
            "schema_version": 1, "kind": "original",
            "cases": [
                example_case(
                    f"T{i:02}", [], [f"T{i:02}.fixture.{j}" for j in range(n)],
                ) for i, n in enumerate(ne.ORIGINAL_COUNTS, 1)
            ],
        }
        heldout = {"schema_version": 1, "kind": "heldout", "cases": [example_case("H01", [])]}
        ne.freeze_suite(self.store, "original.json", original)
        ne.freeze_suite(self.store, "heldout.json", heldout)
        self.store.write("data.json", {"fixture": True})
        deployment = {"configurations": [{
            "label": "candidate", "workspace_id": str(UUID(int=1)),
            "data_agent_id": str(UUID(int=2)), "stage": "production",
            "data_fingerprint_file": "data.json",
        }]}
        relative = runner.create_plan(
            self.store, "measurement", deployment, "original.json", "heldout.json", 2, 1,
        )
        plan = runner.load_plan(self.store, relative)
        self.store.write("campaigns/measurement/candidate/baseline-definition.json", definition())
        for slot in plan["slots"]:
            batch_path = runner.slot_path(plan, slot)
            self.store.write(f"{batch_path}/started.json", {"plan_sha256": ne.digest(plan), "slot": slot})
            suite = ne.load_suite(self.store, plan["suite_files"][slot["suite"]])
            for case in suite["cases"]:
                key = f"{slot['suite']}-{slot['repeat']}-{case['id']}"
                client = FakeClient()
                client.response = example_response(False)
                client.response["id"] = f"response-{key}"
                client.new_conversation = lambda key=key: runner.RawReply(ne.encode({"id": f"conversation-{key}"}))
                case_path = f"{batch_path}/{case['id']}"
                record = runner.capture_case(
                    self.store, case_path, case, client, definition,
                    runner.definition_digest(definition()), set(), 10,
                )
                self.assertEqual(record["status"], "completed")
                # Human decisions are the only intentionally editable evidence
                # artifacts. This is a synthetic grader, not production scoring.
                self.store.path(f"{case_path}/review.json").write_bytes(
                    ne.encode(approved_review(case, record))
                )
            self.store.write(f"{batch_path}/batch.json", {
                "slot": slot, "status": "captured_pending_human_review",
                "configuration_sha256": runner.definition_digest(definition()),
                "case_statuses": [{"case_id": c["id"], "status": "completed"} for c in suite["cases"]],
            })
        return plan

    def test_complete_campaign_accepts_only_after_every_human_condition(self):
        report = runner.report_campaign(self.store, self.synthetic_campaign())
        self.assertTrue(report["acceptance"])
        self.assertTrue(all(batch["batch_pass"] for batch in report["batches"]))

    def test_reporting_rejects_changed_data_fingerprint_for_every_case(self):
        plan = self.synthetic_campaign()
        self.store.path("data.json").write_bytes(ne.encode({"fixture": "changed"}))
        self.assert_data_fingerprint_blocks_report(plan)

    def test_reporting_rejects_missing_data_fingerprint_for_every_case(self):
        plan = self.synthetic_campaign()
        self.store.path("data.json").unlink()
        self.assert_data_fingerprint_blocks_report(plan)

    def assert_data_fingerprint_blocks_report(self, plan):
        report = runner.report_campaign(self.store, plan)
        self.assertFalse(report["acceptance"])
        for batch in report["batches"]:
            self.assertIn("batch_data_fingerprint_missing_or_changed", batch["batch_gate_errors"])
            self.assertFalse(batch["batch_pass"])
            for case in batch["cases"]:
                self.assertIn("batch_data_fingerprint_missing_or_changed", case["gate_errors"])
                self.assertFalse(case["question_pass"])
                self.assertEqual(case["pass"], 0)
                self.assertEqual(case["na"], 0)
                self.assertEqual(case["fail"], case["total_conditions"])

    def test_best_run_is_not_substituted_for_all_repeats(self):
        plan = self.synthetic_campaign()
        path = "campaigns/measurement/candidate/original/repeat-001/T01/review.json"
        review = self.store.read(path)
        review["conditions"][0]["verdict"] = "FAIL"
        self.store.path(path).write_bytes(ne.encode(review))
        report = runner.report_campaign(self.store, plan)
        group = next(g for g in report["groups"] if g["suite"] == "original")
        self.assertEqual(group["all_repeats"]["question_pass"], 19)
        self.assertEqual(group["all_repeats"]["question_total"], 20)
        self.assertEqual(group["all_repeats"]["condition_pass"], 167)
        self.assertEqual(group["all_repeats"]["condition_total"], 168)
        self.assertEqual(group["fully_passing_runs"], 1)
        self.assertEqual(group["best_single_run_only_not_repeatability"]["question_pass"], 10)
        self.assertFalse(report["acceptance"])

    def test_all_case_files_do_not_accept_an_unfinished_batch(self):
        plan = self.synthetic_campaign()
        self.store.path("campaigns/measurement/candidate/original/repeat-001/batch.json").unlink()
        report = runner.report_campaign(self.store, plan)
        self.assertFalse(report["acceptance"])
        self.assertIn("batch_unfinished_or_incomplete", report["batches"][0]["batch_gate_errors"])


if __name__ == "__main__":
    unittest.main()
