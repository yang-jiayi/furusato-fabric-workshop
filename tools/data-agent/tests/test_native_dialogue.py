"""Offline, synthetic Responses dialogue capture and predecessor integrity."""

from __future__ import annotations

import copy
import os
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import evaluate_native as runner
import native_evaluation as ne
from test_native_evaluation import example_case
from test_native_runner import FakeClient, definition


class DialogueClient(FakeClient):
    def __init__(self):
        super().__init__()
        self.conversation_id = "conversation-dialogue"
        self.conversation_creations = 0
        self.submitted_conversations = []
        self.next_response_id = None
        self.response["conversation"] = {"id": self.conversation_id}

    def new_conversation(self):
        self.conversation_creations += 1
        return runner.RawReply(ne.encode({"id": self.conversation_id}))

    def submit(self, question, conversation_id):
        self.submitted_conversations.append(conversation_id)
        self.response["id"] = self.next_response_id or f"response-turn-{len(self.submissions) + 1}"
        return super().submit(question, conversation_id)


class DialogueTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(dir=os.environ.get("EVALUATION_TEST_TEMP"))
        self.store = ne.PrivateStore(Path(self.folder.name) / "private")
        self.addCleanup(self.folder.cleanup)
        self.client = DialogueClient()
        self.used = set()
        self.expected = runner.definition_digest(definition())
        self.read_definition = definition

    def capture(self, slot="dialogue/turn-1", previous=None, question=None, **kwargs):
        case = example_case()
        if question is not None:
            case["question"] = question
        return runner.capture_case(
            self.store, slot, case, self.client, self.read_definition, self.expected,
            self.used, 10, previous_record_path=previous, **kwargs,
        )

    def follow(self, record, slot="dialogue/turn-2", **kwargs):
        return self.capture(slot, record["record_path"], **kwargs)

    def rewrite_artifact(self, record, name, value):
        matches = [a for a in record["artifacts"] if Path(a["path"]).name == name]
        self.assertEqual(len(matches), 1)
        artifact = matches[0]
        path = self.store.path(artifact["path"])
        path.write_bytes(ne.encode(value))
        artifact["sha256"] = ne.file_digest(path)

    def rewrite_record(self, record):
        self.store.path(record["record_path"]).write_bytes(ne.encode(record))

    def assert_not_submitted(self, action):
        before = len(self.client.submissions)
        creations = self.client.conversation_creations
        record = action()
        self.assertEqual(record["submission_count"], 0)
        self.assertNotEqual(record["status"], "completed")
        self.assertEqual(len(self.client.submissions), before)
        self.assertEqual(self.client.conversation_creations, creations)
        return record

    def test_root_still_creates_a_fresh_conversation(self):
        record = self.capture()
        self.assertEqual(record["status"], "completed")
        self.assertIs(record["fresh_conversation"], True)
        self.assertEqual(record["turn_index"], 1)
        self.assertNotIn("previous_record", record)
        self.assertEqual(self.client.conversation_creations, 1)
        self.assertEqual(self.used, {self.client.conversation_id})
        self.assertTrue(self.store.path("dialogue/turn-1/conversation.body").exists())
        runner.verify_record(self.store, record)

    def test_omitting_predecessor_still_creates_an_independent_root(self):
        first = self.capture()
        self.client.conversation_id = "conversation-independent"
        self.client.response["conversation"] = self.client.conversation_id
        second = self.capture("independent/turn-1")
        self.assertEqual(second["status"], "completed")
        self.assertIs(second["fresh_conversation"], True)
        self.assertEqual(second["turn_index"], 1)
        self.assertNotIn("previous_record", second)
        self.assertNotEqual(first["conversation_id"], second["conversation_id"])
        self.assertEqual(self.client.conversation_creations, 2)
        self.assertEqual(len(self.used), 2)
        runner.verify_record(self.store, second)

    def test_two_and_three_turns_share_context_without_rewriting_any_question(self):
        questions = ["  Synthetic first question.\n", "確認します。\n\tその対象のみ。 ", "Yes — unchanged?\n\n"]
        records = []
        for index, question in enumerate(questions, 1):
            previous = records[-1]["record_path"] if records else None
            record = self.capture(f"dialogue/turn-{index}", previous, question)
            records.append(record)
            self.assertEqual(record["status"], "completed")
            self.assertEqual(record["turn_index"], index)
            self.assertEqual(record["submission_count"], 1)
            self.assertIs(record["fresh_conversation"], index == 1)
            self.assertEqual(record["conversation_id"], self.client.conversation_id)
            self.assertEqual(self.store.read(record["request_artifact"]), {
                "input": question, "conversation": self.client.conversation_id,
                "model": "server-default-fixture", "stream": False,
            })
            if previous is not None:
                self.assertEqual(record["previous_record"], {
                    "path": previous, "sha256": ne.file_digest(self.store.path(previous)),
                    "response_id": records[-2]["response"]["id"],
                })
                self.assertFalse(self.store.path(f"dialogue/turn-{index}/conversation.body").exists())
            runner.verify_record(self.store, record)
        self.assertEqual(self.client.submissions, questions)
        self.assertEqual(self.client.submitted_conversations, [self.client.conversation_id] * 3)
        self.assertEqual(self.client.conversation_creations, 1)
        self.assertEqual(self.client.diagnostic_calls, [
            (self.client.conversation_id, record["response"]["id"]) for record in records
        ])
        review = self.store.read("dialogue/turn-3/review.json")
        self.assertTrue(all(row["verdict"] == "UNCLEAR" for row in review["conditions"]))
        self.assertFalse(ne.grade_case(example_case(), records[-1], review)["question_pass"])

    def test_predecessor_and_exclusive_claim_are_durable_before_post(self):
        first = self.capture()
        first_bytes = self.store.path(first["record_path"]).read_bytes()
        submit = self.client.submit

        def inspect(question, conversation_id):
            intent = self.store.read("dialogue/turn-2/submission-intent.json")
            claim = self.store.read("dialogue/turn-1/continuation-claim.json")
            self.assertEqual(intent, claim)
            self.assertEqual(intent["previous_record"]["sha256"],
                             ne.file_digest(self.store.path(first["record_path"])))
            self.assertEqual(intent["previous_record"]["response_id"], first["response"]["id"])
            self.assertEqual(intent["record_path"], "dialogue/turn-2/record.json")
            self.assertEqual(intent["turn_index"], 2)
            self.assertIs(intent["fresh_conversation"], False)
            self.assertFalse(self.store.path("dialogue/turn-2/record.json").exists())
            return submit(question, conversation_id)

        self.client.submit = inspect
        second = self.follow(first)
        self.assertEqual(second["status"], "completed")
        self.assertEqual(len(self.client.submissions), 2)
        self.assertEqual(self.store.path(first["record_path"]).read_bytes(), first_bytes)
        runner.verify_record(self.store, second)

    def test_previous_record_without_new_metadata_remains_compatible(self):
        first = self.capture()
        path = first.pop("record_path")
        del first["turn_index"]
        intent = self.store.read("dialogue/turn-1/submission-intent.json")
        for key in ("turn_index", "record_path", "fresh_conversation"):
            del intent[key]
        self.rewrite_artifact(first, "submission-intent.json", intent)
        self.store.path(path).write_bytes(ne.encode(first))
        second = self.capture("dialogue/turn-2", path)
        self.assertEqual(second["status"], "completed")
        self.assertEqual(second["turn_index"], 2)
        runner.verify_record(self.store, second)

    def test_failed_cancelled_and_incomplete_native_predecessors_are_blocked(self):
        for status in ("failed", "cancelled", "incomplete"):
            with self.subTest(status=status):
                self.client = DialogueClient()
                self.used = set()
                self.client.response["status"] = status
                first = self.capture(f"{status}/turn-1")
                self.assertEqual(first["status"], "native_failure_captured")
                self.assert_not_submitted(lambda: self.follow(first, f"{status}/turn-2"))

    def test_unfinished_predecessors_are_blocked(self):
        for status in ("queued", "in_progress"):
            with self.subTest(status=status):
                self.client = DialogueClient()
                self.used = set()
                self.client.response["status"] = status
                ticks = iter([0, 11])
                first = self.capture(f"{status}/turn-1", monotonic=lambda: next(ticks))
                self.assertEqual(first["status"], "unfinished_timeout")
                self.assert_not_submitted(lambda: self.follow(first, f"{status}/turn-2"))

    def test_platform_block_in_completed_envelope_cannot_be_continued(self):
        self.client.response["output"][-1]["content"][0]["text"] = (
            "There's content here I can't work with. Try asking a new question."
        )
        first = self.capture()
        self.assertEqual(first["status"], "native_failure_captured")
        self.assert_not_submitted(lambda: self.follow(first))

    def test_relabelled_terminal_failure_or_platform_block_is_still_blocked(self):
        for failure in ("failed", "block"):
            with self.subTest(failure=failure):
                self.client = DialogueClient()
                self.used = set()
                if failure == "failed":
                    self.client.response["status"] = "failed"
                else:
                    self.client.response["output"][-1]["content"][0]["text"] = (
                        "There's content here I can't work with."
                    )
                first = self.capture(f"{failure}/turn-1")
                first["status"] = "completed"
                self.rewrite_record(first)
                self.assert_not_submitted(lambda: self.follow(first, f"{failure}/turn-2"))

    def test_completed_response_with_top_level_error_cannot_be_continued(self):
        self.client.response["error"] = {"code": "synthetic_error"}
        first = self.capture()
        self.assertEqual(first["status"], "evidence_incomplete")
        self.assert_not_submitted(lambda: self.follow(first))

    def test_recovered_internal_planning_errors_keep_their_evidence_status(self):
        self.client.response["output"][0]["status"] = "failed"
        self.client.response["output"][0]["error"] = {"code": "synthetic_planning_error"}
        first = self.capture()
        self.assertEqual(first["status"], "evidence_incomplete")
        self.assertEqual(first["response"]["status"], "completed")
        second = self.follow(first)
        self.assertEqual(second["status"], "evidence_incomplete")
        third = self.follow(second, "dialogue/turn-3")
        self.assertEqual(third["status"], "evidence_incomplete")
        self.assertEqual(self.client.conversation_creations, 1)
        self.assertEqual(len(self.client.submissions), 3)
        runner.verify_record(self.store, third)

    def test_recoverable_planning_status_does_not_skip_wire_or_definition_checks(self):
        self.client.response["output"][0]["error"] = {"code": "synthetic_planning_error"}
        first = self.capture()
        self.assertEqual(first["status"], "evidence_incomplete")
        for artifact_name, value in (
            ("request.body", {
                "input": first["question"], "conversation": first["conversation_id"],
                "instructions": "Synthetic forbidden override.",
            }),
            ("configuration-after.json", definition("changed")),
        ):
            with self.subTest(artifact=artifact_name):
                changed = copy.deepcopy(first)
                path = next(a["path"] for a in changed["artifacts"]
                            if Path(a["path"]).name == artifact_name)
                original = self.store.path(path).read_bytes()
                self.rewrite_artifact(changed, artifact_name, value)
                self.rewrite_record(changed)
                self.assert_not_submitted(lambda: self.follow(first, f"dialogue/{artifact_name}"))
                self.store.path(path).write_bytes(original)
                self.rewrite_record(first)

    def test_incomplete_final_or_unpaired_tools_are_not_recovered_planning_errors(self):
        for fault in ("missing-final", "unfinished-final", "unpaired-tool", "refusal"):
            with self.subTest(fault=fault):
                self.client = DialogueClient()
                self.used = set()
                output = self.client.response["output"]
                if fault == "missing-final":
                    output.pop()
                elif fault == "unfinished-final":
                    output[-1]["status"] = "in_progress"
                elif fault == "unpaired-tool":
                    output.pop(1)
                else:
                    output[-1]["content"] = [{"type": "refusal", "refusal": "Synthetic refusal."}]
                first = self.capture(f"{fault}/turn-1")
                self.assertEqual(first["status"], "evidence_incomplete")
                self.assert_not_submitted(lambda: self.follow(first, f"{fault}/turn-2"))

    def test_optional_diagnostics_feature403_remains_acceptable(self):
        def diagnostics(*args):
            raise runner.NativeEvidenceError("Synthetic feature gate.", ne.encode({
                "Message": "Data Agent diagnostics feature is not enabled.",
                "Source": "AISKILL", "error_code": "PERMISSION_DENIED",
            }), 403)

        self.client.diagnostics = diagnostics
        first = self.capture()
        second = self.follow(first)
        self.assertEqual(first["status"], "completed")
        self.assertEqual(second["status"], "completed")
        self.assertEqual(second["diagnostics_status"], "feature_unavailable")
        runner.verify_record(self.store, second)

    def test_other_diagnostics_errors_cannot_be_continued(self):
        def diagnostics(*args):
            raise TimeoutError("Synthetic diagnostics failure.")

        self.client.diagnostics = diagnostics
        first = self.capture()
        self.assertEqual(first["status"], "evidence_incomplete")
        self.assert_not_submitted(lambda: self.follow(first))

    def test_unregistered_conversation_is_rejected_before_post(self):
        first = self.capture()
        self.used.clear()
        self.assert_not_submitted(lambda: self.follow(first))

    def test_different_current_or_frozen_configuration_is_rejected_before_post(self):
        first = self.capture()
        self.read_definition = lambda: definition("different")
        self.assert_not_submitted(lambda: self.follow(first, "dialogue/drift"))
        self.expected = runner.definition_digest(definition("different"))
        self.assert_not_submitted(lambda: self.follow(first, "dialogue/new-baseline"))

    def test_predecessor_configuration_drift_is_rejected_before_post(self):
        definitions = iter([definition(), definition("different")])
        self.read_definition = lambda: next(definitions)
        first = self.capture()
        self.assertEqual(first["status"], "configuration_changed")
        self.read_definition = definition
        self.assert_not_submitted(lambda: self.follow(first))

    def test_changed_predecessor_question_conversation_or_count_is_rejected(self):
        first = self.capture()
        for field, value in (
            ("question", "Changed question"), ("conversation_id", "foreign-conversation"),
            ("submission_count", 2), ("submission_count", True),
        ):
            with self.subTest(field=field, value=value):
                changed = copy.deepcopy(first)
                changed[field] = value
                self.rewrite_record(changed)
                self.used.add("foreign-conversation")
                self.assert_not_submitted(
                    lambda: self.follow(first, f"dialogue/{field}-{value}"),
                )
        self.rewrite_record(first)

    def test_raw_or_parsed_predecessor_response_tampering_is_rejected(self):
        first = self.capture()
        changed = copy.deepcopy(first)
        changed["response"]["output"][-1]["content"][0]["text"] = "Externally corrected."
        self.rewrite_record(changed)
        self.assert_not_submitted(lambda: self.follow(first, "dialogue/parsed-tamper"))
        self.rewrite_record(first)
        self.store.path(first["response_artifact"]).write_bytes(ne.encode({"edited": True}))
        self.assert_not_submitted(lambda: self.follow(first, "dialogue/raw-tamper"))

    def test_missing_or_copied_predecessor_record_is_not_a_new_identity(self):
        first = self.capture()
        self.store.write("copied/record.json", first)
        self.assert_not_submitted(lambda: self.capture("dialogue/copy", "copied/record.json"))
        self.assert_not_submitted(lambda: self.capture("dialogue/missing", "missing/record.json"))

    def test_explicit_native_previous_response_id_must_match_the_link(self):
        first = self.capture()
        self.client.response["previous_response_id"] = first["response"]["id"]
        second = self.follow(first)
        self.assertEqual(second["response"]["status"], "completed")
        self.assertEqual(second["status"], "evidence_incomplete")
        self.client.response["previous_response_id"] = second["response"]["id"]
        third = self.follow(second, "dialogue/turn-3")
        self.assertEqual(third["response"]["status"], "completed")
        self.assertEqual(len(self.client.submissions), 3)
        runner.verify_record(self.store, third)

    def test_foreign_native_previous_response_id_or_reused_response_id_blocks_next_turn(self):
        for fault in ("foreign-predecessor", "reused-response"):
            with self.subTest(fault=fault):
                self.client = DialogueClient()
                self.used = set()
                first = self.capture(f"{fault}/turn-1")
                if fault == "foreign-predecessor":
                    self.client.response["previous_response_id"] = "foreign-response"
                else:
                    self.client.next_response_id = first["response"]["id"]
                second = self.follow(first, f"{fault}/turn-2")
                self.assertNotEqual(second["status"], "completed")
                self.assertEqual(len(self.client.submissions), 2)
                self.assert_not_submitted(lambda: self.follow(second, f"{fault}/turn-3"))

    def test_ambiguous_followup_never_replays_even_through_a_different_slot(self):
        first = self.capture()

        def ambiguous(question, conversation_id):
            self.client.submissions.append(question)
            raise TimeoutError("Synthetic ambiguous POST.")

        self.client.submit = ambiguous
        second = self.follow(first)
        self.assertEqual(second["status"], "submission_outcome_unknown")
        self.assertEqual(len(self.client.submissions), 2)
        self.assertEqual(self.client.retrievals, 0)
        with self.assertRaises(FileExistsError):
            self.follow(first)
        self.assert_not_submitted(lambda: self.follow(first, "dialogue/replay"))
        self.assert_not_submitted(lambda: self.follow(second, "dialogue/turn-3"))

    def test_completed_predecessor_can_only_be_consumed_once(self):
        first = self.capture()
        second = self.follow(first)
        self.assertEqual(second["status"], "completed")
        self.assert_not_submitted(lambda: self.follow(first, "dialogue/fork"))
        third = self.follow(second, "dialogue/turn-3")
        self.assertEqual(third["status"], "completed")
        self.assertEqual(len(self.client.submissions), 3)

    def test_interruption_after_claim_without_terminal_record_still_prevents_replay(self):
        first = self.capture()

        def interrupted(question, conversation_id):
            raise KeyboardInterrupt()

        self.client.submit = interrupted
        with self.assertRaises(KeyboardInterrupt):
            self.follow(first)
        self.store.path("dialogue/turn-2/record.json").unlink()
        self.assert_not_submitted(lambda: self.follow(first, "dialogue/replay"))

    def test_followup_cannot_be_relabelled_fresh_or_unlinked(self):
        first = self.capture()
        second = self.follow(first)
        for field, value in (
            ("fresh_conversation", True), ("turn_index", 1), ("previous_record", None),
        ):
            with self.subTest(field=field):
                changed = copy.deepcopy(second)
                changed[field] = value
                with self.assertRaises(ne.EvaluationError):
                    runner.verify_record(self.store, changed)
        second["artifacts"].append(next(
            copy.deepcopy(a) for a in first["artifacts"] if Path(a["path"]).name == "conversation.body"
        ))
        with self.assertRaises(ne.EvaluationError):
            runner.verify_record(self.store, second)

    def test_turn_metadata_cannot_be_removed_to_disguise_a_capture_as_legacy(self):
        first = self.capture()
        for fields in (("turn_index",), ("turn_index", "record_path")):
            with self.subTest(fields=fields):
                changed = copy.deepcopy(first)
                for field in fields:
                    del changed[field]
                with self.assertRaises(ne.EvaluationError):
                    runner.verify_record(self.store, changed)

    def test_rehashed_receipts_cannot_change_the_previous_response_or_turn_index(self):
        first = self.capture()
        second = self.follow(first)
        for field in ("response_id", "turn_index"):
            with self.subTest(field=field):
                changed = copy.deepcopy(second)
                intent = self.store.read("dialogue/turn-2/submission-intent.json")
                original = copy.deepcopy(intent)
                if field == "response_id":
                    changed["previous_record"]["response_id"] = "foreign-response"
                    intent["previous_record"] = changed["previous_record"]
                else:
                    changed["turn_index"] = 7
                    intent["turn_index"] = 7
                self.rewrite_artifact(changed, "submission-intent.json", intent)
                self.rewrite_artifact(changed, "continuation-claim.json", intent)
                with self.assertRaisesRegex(ne.EvaluationError, "exact predecessor"):
                    runner.verify_record(self.store, changed)
                self.rewrite_artifact(second, "submission-intent.json", original)
                self.rewrite_artifact(second, "continuation-claim.json", original)

    def test_terminal_record_hash_link_and_all_ancestor_raw_hashes_are_checked(self):
        first = self.capture()
        second = self.follow(first)
        third = self.follow(second, "dialogue/turn-3")
        original = self.store.path(second["record_path"]).read_bytes()
        self.store.path(second["record_path"]).write_bytes(original + b"\n")
        with self.assertRaisesRegex(ne.EvaluationError, "Predecessor record hash"):
            runner.verify_record(self.store, third)
        self.store.path(second["record_path"]).write_bytes(original)
        self.store.path(first["response_artifact"]).write_bytes(ne.encode({"tampered": True}))
        with self.assertRaises(ne.EvaluationError):
            runner.verify_record(self.store, third)
        self.assert_not_submitted(lambda: self.follow(third, "dialogue/turn-4"))

    def test_self_referential_chain_is_rejected_without_recursive_loading(self):
        first = self.capture()
        second = self.follow(first)
        second["previous_record"] = {
            "path": second["record_path"], "sha256": "0" * 64,
            "response_id": first["response"]["id"],
        }
        intent = self.store.read("dialogue/turn-2/submission-intent.json")
        intent["previous_record"] = second["previous_record"]
        self.rewrite_artifact(second, "submission-intent.json", intent)
        second["artifacts"] = [
            a for a in second["artifacts"] if Path(a["path"]).name != "continuation-claim.json"
        ]
        claim_path = "dialogue/turn-2/continuation-claim.json"
        sha = self.store.write(claim_path, intent)
        second["artifacts"].append({"path": claim_path, "sha256": sha})
        with self.assertRaisesRegex(ne.EvaluationError, "cycle"):
            runner.verify_record(self.store, second)


if __name__ == "__main__":
    unittest.main()
