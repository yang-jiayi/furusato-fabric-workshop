"""Local fixtures exercise gate behavior; they are never live evidence."""

from __future__ import annotations

import copy
import base64
import hashlib
import os
import shutil
import struct
import sys
import unittest
import zlib
from io import BytesIO
from pathlib import Path
from uuid import uuid4
from zipfile import ZipFile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import preview_contract as pc
from proof_files import check_attachment_pack, check_docx, check_html, image_pixel_signature, png_pixels, redaction_errors, rendered_image_geometry
from source_oracle import compute_oracle, graph_expectations, immutable_baseline, original_suite
from observations import check_synonym_only_delta, inspect_mcp_discovery

REPO = Path(__file__).resolve().parents[4]
BASELINE = "40921a0006394340f1284fd25c2824549d430c1c"
FROZEN = "2026-01-01T00:00:02Z"
CAPTURED = "2026-01-01T00:00:03Z"


def png_bytes(width, height, changes=None, mode=0):
    changes = changes or {}
    rows = []
    for y in range(height):
        raw = bytearray()
        for x in range(width):
            raw.extend(changes.get((x, y), (240, 241, 242)))
        filtered = bytes(raw)
        if mode == 1:
            filtered = bytes((value - (raw[index - 3] if index >= 3 else 0)) % 256
                             for index, value in enumerate(raw))
        rows.append(bytes([mode]) + filtered)

    def chunk(kind, payload):
        return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)

    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(b"".join(rows))) + chunk(b"IEND", b""))


class PrivateFixture(unittest.TestCase):
    def setUp(self):
        configured = os.environ.get("PREVIEW30_TEST_ROOT")
        if not configured:
            self.fail("Set PREVIEW30_TEST_ROOT to an owned, non-temporary private directory outside Git.")
        self.root = Path(configured).resolve() / f"unit-{uuid4().hex}"
        self.root.mkdir(parents=True)
        self.store = pc.PrivateStore(self.root)
        self.counter = 0
        self.catalog = pc.load_catalog()
        self.oracle = {"static": {"rows": 1, "amount_yen": 100, "unique_donation_ids": 1,
                                 "from_utc": "2025-01-01T00:00:00Z", "to_utc": "2025-01-01T00:00:00Z"}}
        self.manifest = pc.empty_manifest(self.catalog, self.oracle, FROZEN)
        self.readiness = {
            "workspace_id": "11111111-1111-1111-1111-111111111111",
            "folder_id": "22222222-2222-2222-2222-222222222222",
            "portal_folder_id": "fixture-folder", "folder_mapping_verified": True,
            "read_only_queries_ready": True, "questions_authorized": True,
            "approved_at_utc": "2026-01-01T00:00:00Z", "approved_by": "unit fixture",
            "identity_sha256": "a" * 64, "forbidden_item_ids": [], "items": {},
        }
        roles = sorted({role for case in self.catalog["cases"] for role in case["required_items"]})
        for index, role in enumerate(roles, 1):
            self.readiness["items"][role] = {
                "id": f"00000000-0000-0000-0000-{index:012d}", "type": role,
                "workspace_id": self.readiness["workspace_id"], "folder_id": self.readiness["folder_id"],
                "ready": True,
            }
        for name in ("scope_receipt", "source_readiness_receipt"):
            self.readiness[name] = self.json_artifact({
                "status": "observed", "scope_sha256": pc.scope_fingerprint(self.readiness),
                "captured_at_utc": "2026-01-01T00:00:01Z",
            })
        self.manifest["context"].update(
            scope_sha256=pc.scope_fingerprint(self.readiness), identity_sha256="a" * 64,
            prompts_sha256=pc.digest({}), configuration_sha256="b" * 64,
        )

    def tearDown(self):
        if hasattr(self, "root") and self.root.is_dir():
            shutil.rmtree(self.root)

    def json_artifact(self, body):
        self.counter += 1
        path = f"fixture-{self.counter}.json"
        checksum = self.store.write(path, body)
        return {"path": path, "sha256": checksum}

    def proof(self, kind, body=None):
        body = body or {
            "request": {"query": "SELECT marker FROM unit_fixture"},
            "response": {"rows": {"marker": 1}, "request_id": "unit-call", "status": "succeeded",
                         "id": "unit-response", "conversation_id": "unit-conversation"},
        }
        artifact = self.json_artifact(body)
        proof = {
            "kind": kind, "origin": "native_tool", "captured_at_utc": CAPTURED,
            "context_sha256": pc.digest(self.manifest["context"]),
            "artifact": artifact,
            "item_ids": [self.readiness["items"]["lakehouse"]["id"]],
            "review": {"reviewer": "unit fixture", "note": "Simulated input for a unit test, never live proof.",
                       "artifact_sha256": artifact["sha256"]},
        }
        if kind in {"source_query", "execution_trace"}:
            proof["trace"] = {
                "call_id": "unit-call", "call_id_pointer": "/response/request_id", "language": "SQL",
                "query_pointer": "/request/query", "result_pointer": "/response/rows",
                "execution_pointer": "/response/status", "executed": True,
                "scope_reviewed": True, "complete": True, "reviewer": "unit fixture",
                "all_native_calls_reviewed": True,
            }
            proof["response_id_pointer"] = "/response/id"
        if kind == "native_response":
            proof.update(
                final_text_pointer="/response/text", terminal_status="completed",
                conversation_id="unit-conversation", conversation_identity_kind="backend_conversation",
                conversation_id_pointer="/response/conversation_id", response_id_pointer="/response/id",
                question_pointer="/request/question",
            )
        key = f"proof-{self.counter}"
        self.manifest["evidence"][key] = proof
        return key

    def replace_body(self, key, body):
        artifact = self.json_artifact(body)
        proof = self.manifest["evidence"][key]
        proof["artifact"] = artifact
        proof["review"]["artifact_sha256"] = artifact["sha256"]

    def record(self, case_id):
        return next(r for r in self.manifest["records"] if r["case_id"] == case_id and r["repeat"] == 1)

    def case(self, case_id):
        return next(c for c in self.catalog["cases"] if c["id"] == case_id)

    def activate(self, case_id, roles):
        record = self.record(case_id)
        record.update(state="pass", support="supported", reviewer="unit fixture", reason="Unit gate fixture.",
                      evidence=roles)
        for key in roles.values():
            proof = self.manifest["evidence"][key]
            proof["item_ids"] = sorted(set(proof["item_ids"]) | {
                self.readiness["items"][role]["id"] for role in self.case(case_id)["required_items"]
            })
        first = next(iter(roles))
        record["checks"] = {
            key: {"state": "pass", "reason": "Unit review fixture.",
                  "citations": [{"role": first, "pointer": "/response/rows"}]}
            for key in self.case(case_id)["checks"]
        }
        return record

    def data_case(self):
        body = {"request": {"query": "SELECT marker FROM unit_fixture"},
                "response": {"rows": self.oracle["static"], "request_id": "unit-call", "status": "succeeded"}}
        record = self.activate("DATA01", {name: self.proof("source_query", body) for name in ("totals", "schema")})
        record["oracle_assertions"] = {
            key: {"role": "totals", "pointer": "/response/rows/" + key.split(".")[-1]}
            for key in self.case("DATA01")["oracle_assertions"]
        }
        return record

    def ai_case(self):
        question = "Unit fixture question; never submit this as a benchmark."
        checksum = hashlib.sha256(question.encode()).hexdigest()
        self.manifest["prompt_hashes"]["COPILOT02"] = checksum
        self.manifest["context"]["prompts_sha256"] = pc.digest(self.manifest["prompt_hashes"])
        body = {"request": {"question": question, "query": "SELECT marker FROM unit_fixture"},
                "response": {"text": "Unit answer.", "rows": {"marker": 1}, "id": "unit-response",
                             "conversation_id": "unit-conversation", "request_id": "unit-call", "status": "succeeded"}}
        record = self.activate("COPILOT02", {
            "answer": self.proof("native_response", body), "trace": self.proof("execution_trace", body),
            "source": self.proof("source_query", body),
        })
        record.update(prompt_sha256=checksum, fresh_conversation=True, conversation_id="unit-conversation",
                      submission_count=1, configuration_before_sha256="b" * 64, configuration_after_sha256="b" * 64)
        return record

    def assess(self, record):
        return pc.assess_case(self.case(record["case_id"]), record, self.manifest, self.readiness, self.store, self.oracle)


class EvidenceTests(PrivateFixture):
    def test_schema_and_catalog_states_match_validator(self):
        schema = pc.load_json(Path(pc.__file__).with_name("evidence.schema.json"))
        self.assertEqual(schema["$defs"]["state"]["enum"], list(pc.STATES))
        self.assertEqual(self.catalog["states"], list(pc.STATES))
        self.assertEqual(len(self.catalog["cases"]), 26)

    def test_validator_changes_cannot_reinterpret_old_frozen_scores(self):
        self.data_case()
        self.manifest["validator_sha256"] = "d" * 64
        result = pc.report(self.manifest, self.readiness, self.store, self.oracle)
        self.assertFalse(result["validator_matches_frozen_plan"])
        self.assertEqual(result["supported_pass"], 0)
        self.assertEqual(result["supported_missing_evidence"], 1)

    def test_all_initial_slots_blocked_and_no_accuracy(self):
        result = pc.report(self.manifest, {}, self.store, self.oracle)
        self.assertEqual(result["requested_slots"], 36)
        self.assertEqual(result["state_counts"]["blocked"], 36)
        self.assertEqual(result["ai"]["scored_questions"], 0)
        self.assertIsNone(result["ai"]["accuracy"])
        self.assertEqual(result["capacity_measurements"], [])

    def test_empty_verified_capture_list_keeps_every_view_blocked(self):
        plan = {"schemaVersion": 1, "state": "blocked-authentication", "canvasAuthentication": "confirmed",
                "requestedCaptures": [{"id": f"view-{index}", "chapter": index} for index in range(1, 18)],
                "verifiedCaptures": []}
        result = pc.capture_plan_report(plan, self.store)
        self.assertEqual((result["required_views"], result["verified_views"]), (17, 0))
        self.assertTrue(all(row["state"] == "blocked" for row in result["views"]))
        self.assertIsNone(result["ai_accuracy"])
        self.assertTrue(result["authentication_surfaces"]["top_level_authentication_is_not_ontology_ui_evidence"])

    def test_a_verified_capture_label_is_not_evidence(self):
        plan = {"schemaVersion": 1, "requestedCaptures": [{"id": "view"}], "verifiedCaptures": ["view"]}
        result = pc.capture_plan_report(plan, self.store)
        self.assertEqual(result["verified_views"], 0)
        self.assertEqual(result["views"][0]["state"], "unverified")

    def test_capture_inventory_rejects_duplicate_views(self):
        plan = {"schemaVersion": 1, "requestedCaptures": [{"id": "view"}], "verifiedCaptures": ["view", "view"]}
        with self.assertRaises(pc.EvidenceError):
            pc.capture_plan_report(plan, self.store)

    def test_supplementary_observations_do_not_replace_required_views(self):
        plan = {"schemaVersion": 1, "requestedCaptures": [{"id": "view"}],
                "verifiedCaptures": [{"id": "supplementary", "status": "observed"}]}
        result = pc.capture_plan_report(plan, self.store)
        self.assertEqual((result["required_views"], result["verified_views"]), (1, 0))
        self.assertEqual(len(result["supplementary_observations"]), 1)
        self.assertFalse(result["supplementary_observations"][0]["counts_toward_required_views"])

    def test_data_case_positive_fixture(self):
        self.assertEqual(self.assess(self.data_case())["state"], "pass")

    def test_data_case_is_not_an_ai_question(self):
        self.data_case()
        result = pc.report(self.manifest, self.readiness, self.store, self.oracle)
        self.assertEqual(result["supported_pass"], 1)
        self.assertEqual(result["ai"]["scored_questions"], 0)
        self.assertIsNone(result["ai"]["accuracy"])

    def test_binding_labels_and_direct_sql_do_not_prove_native_instances(self):
        errors = pc._feature_errors({"id": "UI02"}, {}, {}, {"binding": {"labels": "correct"}}, {})
        self.assertTrue(any("native_instances_readback_unverified" in error for error in errors))

    def test_native_source_kind_error_fails_binding_functional_gate(self):
        record = {"functional_readback": {"status_pointer": "/response/status", "rows_pointer": "/response/rows"}}
        bodies = {"functional": {"response": {"status": "failed", "rows": [],
                  "error": "The kind of Fabric item this data source points to couldn't be identified."}}}
        errors = pc._feature_errors({"id": "UI02"}, record, {}, bodies, {})
        self.assertIn("source_truth_mismatch:native_binding_instances_failed", errors)

    def test_actual_native_instance_rows_satisfy_functional_subgate(self):
        record = {"functional_readback": {"status_pointer": "/response/status", "rows_pointer": "/response/rows"}}
        bodies = {"functional": {"response": {"status": "completed", "rows": [{"Id": "unit-fixture"}]}}}
        self.assertEqual(pc._feature_errors({"id": "UI02"}, record, {}, bodies, {}), [])

    def test_numeric_mismatch_is_counted_failure(self):
        record = self.data_case()
        key = record["evidence"]["totals"]
        body = pc.load_json(self.store.artifact(self.manifest["evidence"][key]["artifact"]))
        body["response"]["rows"]["amount_yen"] = 101
        self.replace_body(key, body)
        result = self.assess(record)
        self.assertEqual(result["state"], "fail")
        self.assertIn("source_truth_mismatch:static.amount_yen", result["errors"])

    def test_data_not_available_is_missing_not_zero_or_success(self):
        record = self.data_case()
        key = record["evidence"]["totals"]
        body = pc.load_json(self.store.artifact(self.manifest["evidence"][key]["artifact"]))
        body["response"]["rows"] = {"error": "DataNotAvailable"}
        self.replace_body(key, body)
        result = self.assess(record)
        self.assertEqual(result["state"], "unverified")
        self.assertTrue(any("DataNotAvailable" in error for error in result["errors"]))

    def test_question_mentioning_data_not_available_is_not_a_source_error(self):
        self.assertFalse(pc.missing_data({
            "request": {"question": "Explain why a confirmed zero is not DataNotAvailable."},
            "response": {"rows": [{"Count": 0}]},
        }))

    def test_data_not_available_explanation_is_distinct_from_native_error(self):
        self.assertFalse(pc.missing_data({"response": {"text": "DataNotAvailable does not mean zero."}}))
        self.assertTrue(pc.missing_data({"response": {"error": {"message": "Source returned DataNotAvailable."}}}))
        self.assertTrue(pc.missing_data('{"error":{"code":"DataNotAvailable"}}'))

    def test_hash_tamper_cannot_pass(self):
        record = self.data_case()
        proof = self.manifest["evidence"][record["evidence"]["totals"]]
        self.store.path(proof["artifact"]["path"]).write_bytes(b"{}")
        self.assertEqual(self.assess(record)["state"], "unverified")

    def test_mock_old_ui_and_stale_capture_rejected(self):
        for mutation in ({"origin": "mock"}, {"origin": "legacy_ui"},
                         {"captured_at_utc": "2025-01-01T00:00:00Z"}, {"context_sha256": "c" * 64}):
            with self.subTest(mutation=mutation):
                record = self.data_case()
                self.manifest["evidence"][record["evidence"]["totals"]].update(mutation)
                self.assertEqual(self.assess(record)["state"], "unverified")

    def test_unauthorized_item_and_principal_rejected(self):
        record = self.data_case()
        proof = self.manifest["evidence"][record["evidence"]["totals"]]
        proof["item_ids"] = ["99999999-9999-9999-9999-999999999999"]
        self.readiness["identity_sha256"] = "c" * 64
        result = self.assess(record)
        self.assertEqual(result["state"], "unverified")
        self.assertIn("principal_fingerprint_mismatch", result["errors"])

    def test_unrelated_but_allowlisted_item_cannot_stand_in_for_case_target(self):
        record = self.ai_case()
        for key in record["evidence"].values():
            self.manifest["evidence"][key]["item_ids"] = [self.readiness["items"]["lakehouse"]["id"]]
        self.assertIn("required_item_identity_not_in_case_evidence", self.assess(record)["errors"])

    def test_folder_mapping_gate_not_bypassed_by_ids(self):
        record = self.data_case()
        self.readiness["folder_mapping_verified"] = False
        self.assertIn("folder_mapping_verified", self.assess(record)["errors"])

    def test_new_child_folder_requires_matching_native_ancestry_receipt(self):
        child = "33333333-3333-3333-3333-333333333333"
        receipt = self.json_artifact({"id": child, "parentFolderId": self.readiness["folder_id"],
                                     "workspaceId": self.readiness["workspace_id"]})
        self.readiness["folders"] = {child: {"parent_id": self.readiness["folder_id"],
                                            "workspace_id": self.readiness["workspace_id"],
                                            "newly_created": True, "receipt": receipt}}
        folders, errors = pc.verified_folder_scope(self.readiness, self.store)
        self.assertIn(child, folders)
        self.assertEqual(errors, [])
        self.readiness["folders"][child]["parent_id"] = "44444444-4444-4444-4444-444444444444"
        folders, errors = pc.verified_folder_scope(self.readiness, self.store)
        self.assertNotIn(child, folders)
        self.assertTrue(errors)

    def test_old_or_cross_workspace_folder_cannot_be_registered_as_new_scope(self):
        child = "33333333-3333-3333-3333-333333333333"
        receipt = self.json_artifact({"id": child, "parentFolderId": self.readiness["folder_id"],
                                     "workspaceId": self.readiness["workspace_id"]})
        self.readiness["folders"] = {child: {"parent_id": self.readiness["folder_id"],
                                            "workspace_id": "44444444-4444-4444-4444-444444444444",
                                            "newly_created": False, "receipt": receipt}}
        folders, errors = pc.verified_folder_scope(self.readiness, self.store)
        self.assertNotIn(child, folders)
        self.assertTrue(errors)

    def test_latest_closed_live_gate_overrides_an_older_ready_file(self):
        record = self.data_case()
        self.store.write("live-gate.json", {"state": "closed", "scope_sha256": None})
        self.assertIn("latest_live_gate_closed_or_unverified", self.assess(record)["errors"])

    def test_generated_query_cannot_prove_execution(self):
        record = self.data_case()
        self.manifest["evidence"][record["evidence"]["totals"]]["trace"]["executed"] = False
        self.assertEqual(self.assess(record)["state"], "unverified")

    def test_numeric_one_is_not_an_execution_success_status(self):
        record = self.data_case()
        key = record["evidence"]["totals"]
        body = pc.load_json(self.store.artifact(self.manifest["evidence"][key]["artifact"]))
        body["response"]["status"] = 1
        self.replace_body(key, body)
        self.assertTrue(any("query_execution_not_observed" in error for error in self.assess(record)["errors"]))

    def test_final_answer_table_is_not_query_trace(self):
        record = self.data_case()
        proof = self.manifest["evidence"][record["evidence"]["totals"]]
        proof["trace"]["result_pointer"] = "/response/answer"
        body = {"request": {"query": "SELECT 1"}, "response": {"answer": [{"amount": 100}]}}
        self.replace_body(record["evidence"]["totals"], body)
        self.assertTrue(any("prose" in error for error in self.assess(record)["errors"]))

    def test_full_case_repeat_inventory_cannot_shrink(self):
        self.manifest["records"].pop()
        with self.assertRaises(pc.EvidenceError):
            pc.report(self.manifest, {}, self.store, self.oracle)

    def test_original_routing_criteria_cannot_be_silently_removed(self):
        del self.manifest["original_inventory"]["routing_applicability"]["T04"]
        with self.assertRaises(pc.EvidenceError):
            pc.report(self.manifest, {}, self.store, self.oracle)

    def test_unsupported_requires_actual_negative_probe(self):
        record = self.record("DASHBOARD01")
        record.update(state="unsupported", support="unsupported", blocker="No direct feature observed.")
        result = self.assess(record)
        self.assertEqual(result["state"], "unverified")
        self.assertEqual(result["support"], "pending")
        key = self.proof("capability_probe", {"response": {"available": False}})
        record.update(support_evidence=key, unsupported_pointer="/response/available")
        result = pc.report(self.manifest, self.readiness, self.store, self.oracle)
        self.assertEqual(result["state_counts"]["unsupported"], 1)
        self.assertEqual(result["requested_slots"], 36)

    def test_ai_needs_actual_response_and_correlated_trace(self):
        record = self.ai_case()
        self.assertEqual(self.assess(record)["state"], "pass")
        trace_key = record["evidence"]["trace"]
        body = pc.load_json(self.store.artifact(self.manifest["evidence"][trace_key]["artifact"]))
        body["response"]["id"] = "different-response"
        self.replace_body(trace_key, body)
        self.assertIn("query_trace_not_correlated_with_native_answer", self.assess(record)["errors"])

    def test_mcp_session_is_not_backend_conversation(self):
        record = self.ai_case()
        self.manifest["evidence"][record["evidence"]["answer"]]["conversation_identity_kind"] = "mcp_session"
        self.assertEqual(self.assess(record)["state"], "unverified")

    def test_wrong_prompt_and_configuration_drift_rejected(self):
        record = self.ai_case()
        record["prompt_sha256"] = "c" * 64
        record["configuration_after_sha256"] = "d" * 64
        result = self.assess(record)
        self.assertIn("submitted_prompt_differs_from_frozen_prompt", result["errors"])
        self.assertIn("configuration_drift", result["errors"])

    def test_zero_or_incomplete_questions_cannot_have_aggregate_accuracy(self):
        self.ai_case()
        result = pc.report(self.manifest, self.readiness, self.store, self.oracle)
        self.assertEqual(result["ai"]["scored_questions"], 1)
        self.assertIsNone(result["ai"]["accuracy"])

    def test_no_cherry_picking_repeats_or_reusing_conversation(self):
        first = self.ai_case()
        second = next(r for r in self.manifest["records"] if r["case_id"] == "COPILOT02" and r["repeat"] == 2)
        second.update(copy.deepcopy(first))
        second["repeat"] = 2
        result = pc.report(self.manifest, self.readiness, self.store, self.oracle)
        changed = [r for r in result["inventory"] if r["case_id"] == "COPILOT02" and r["repeat"] < 3]
        self.assertTrue(all(r["state"] == "unverified" for r in changed))

    def test_estimated_cu_cannot_be_reported_as_measured(self):
        self.manifest["capacity_measurements"] = [{"kind": "estimated", "value": 1, "unit": "CU"}]
        with self.assertRaises(pc.EvidenceError):
            pc.report(self.manifest, {}, self.store, self.oracle)

    def test_observed_latency_only(self):
        self.data_case()
        proofs = list(self.manifest["evidence"].values())
        proofs[0]["measurement"] = {"kind": "estimated", "latency_ms": 500}
        proofs[1]["measurement"] = {"kind": "observed", "latency_ms": 150}
        result = pc.report(self.manifest, self.readiness, self.store, self.oracle)
        self.assertEqual([r["latency_ms"] for r in result["latency_measurements"]], [150])

    def test_stale_telemetry_does_not_measure_current_run(self):
        self.data_case()
        proof = next(iter(self.manifest["evidence"].values()))
        proof["measurement"] = {"kind": "observed", "latency_ms": 123}
        proof["context_sha256"] = "e" * 64
        result = pc.report(self.manifest, self.readiness, self.store, self.oracle)
        self.assertEqual(result["latency_measurements"], [])

    def test_source_failure_is_counted_without_inventing_factual_accuracy(self):
        record = self.ai_case()
        key = record["evidence"]["trace"]
        body = pc.load_json(self.store.artifact(self.manifest["evidence"][key]["artifact"]))
        body["response"]["status"] = "failed"
        body["response"]["error"] = {"code": "SourceQueryFailed"}
        self.replace_body(key, body)
        self.manifest["evidence"][key]["trace"]["error_pointer"] = "/response/error"
        result = pc.report(self.manifest, self.readiness, self.store, self.oracle)
        self.assertEqual(len(result["source_query_failures"]), 1)
        self.assertEqual(result["ai"]["scored_questions"], 0)
        self.assertIsNone(result["ai"]["accuracy"])

    def test_version_restore_checks_definition_not_just_receipt(self):
        record = self.activate("VERSION01", {
            "saved": self.proof("definition", {"response": {"rows": {"version": "saved"}}}),
            "modified": self.proof("definition", {"response": {"rows": {"version": "modified"}}}),
            "restored": self.proof("definition", {"response": {"rows": {"version": "wrong"}}}),
            "history": self.proof("operation_receipt"), "source": self.proof("source_query"),
        })
        record["definition_content_pointer"] = "/response/rows"
        self.assertEqual(self.assess(record)["state"], "fail")
        self.replace_body(record["evidence"]["restored"], {"response": {"rows": {"version": "saved"}}})
        self.assertEqual(self.assess(record)["state"], "pass")

    def test_rdf_import_requires_empty_item_and_loss_inventory(self):
        record = self.activate("RDF02", {
            "before": self.proof("definition"), "export": self.proof("rdf_file"),
            "empty": self.proof("definition", {"response": {"entities": [{"name": "already-present"}]}}),
            "summary": self.proof("rdf_import_log", {"response": {"summary": {"preserved": []}}}),
            "after": self.proof("definition"),
        })
        record["rdf"] = {"empty_entities_pointer": "/response/entities", "summary_pointer": "/response/summary"}
        self.manifest["evidence"][record["evidence"]["export"]]["format"] = "OWL"
        result = self.assess(record)
        self.assertIn("rdf_target_not_empty", result["errors"])
        self.assertIn("rdf_loss_transform_inventory_missing", result["errors"])
        self.assertIn("owl_export_not_supported", result["errors"])

    def test_private_store_no_overwrite_or_escape(self):
        self.store.write("exclusive.json", {})
        with self.assertRaises(FileExistsError):
            self.store.write("exclusive.json", {})
        with self.assertRaises(pc.EvidenceError):
            self.store.path(r"..\escape.json")
        (self.root / ".git").mkdir()
        with self.assertRaises(pc.EvidenceError):
            self.store.path("nested.json")

    def test_reject_private_evidence_inside_source_checkout(self):
        with self.assertRaises(pc.EvidenceError):
            pc.PrivateStore(Path(pc.__file__).parent)

    def test_comparison_enforces_same_context_and_original_regression(self):
        baseline = pc.report(self.manifest, self.readiness, self.store, self.oracle)
        candidate = copy.deepcopy(baseline)
        candidate["context"]["identity_sha256"] = "d" * 64
        result = pc.compare(baseline, candidate)
        self.assertEqual(result["decision"], "blocked")
        self.assertIn("comparison_context_changed:identity_sha256", result["errors"])
        self.assertIn("original_regression_not_evaluated", result["errors"])

    def test_critical_failure_and_baseline_regression_reject_candidate(self):
        self.data_case()
        baseline = pc.report(self.manifest, self.readiness, self.store, self.oracle)
        candidate = copy.deepcopy(baseline)
        item = next(r for r in candidate["inventory"] if r["case_id"] == "DATA01")
        item["state"] = "fail"
        result = pc.compare(baseline, candidate)
        self.assertEqual(result["decision"], "reject")
        self.assertIn(["DATA01", 1], result["regressions"])

    def test_identical_failure_or_candidate_budget_stops_loop(self):
        baseline = pc.report(self.manifest, self.readiness, self.store, self.oracle)
        history = [{"failure_fingerprint": "same"}] * 2
        self.assertEqual(pc.compare(baseline, baseline, history)["decision"], "stop")


class FileTests(PrivateFixture):
    def attachment_pack(self, extra_text=""):
        pack = self.root / "pack"
        pack.mkdir()
        text = "fixture.csv | rows=1\nColumns: Id, Amount\n" + extra_text
        dictionary = pack / "data-dictionary.txt"
        dictionary.write_text(text, encoding="utf-8")
        checksum = pc.file_hash(dictionary)
        manifest = {
            "schemaVersion": "furusato-attachments/v1", "synthetic": True,
            "conversationScoped": True, "dataIngestion": False, "rdfImport": False,
            "containsPrivateEvaluationAnswers": False, "uploadObserved": False, "modelUseObserved": False,
            "maxFilesPerConversation": 10, "maxBytesPerFile": 5242880, "sourceDatasetVersion": "unit-only",
            "files": {dictionary.name: {"bytes": dictionary.stat().st_size, "sha256": checksum}},
        }
        (pack / "manifest.json").write_bytes(pc.encode(manifest))
        (pack / "SHA256SUMS.txt").write_text(checksum + "  data-dictionary.txt\n", encoding="utf-8")
        dataset = self.root / "dataset.json"
        dataset.write_bytes(pc.encode({"datasetVersion": "unit-only",
                                      "files": [{"file": "fixture.csv", "rows": 1, "header": "Id,Amount"}],
                                      "incrementFiles": []}))
        return pack, dataset

    def test_attachment_package_success_does_not_imply_service_use(self):
        pack, dataset = self.attachment_pack()
        result = check_attachment_pack(pack, dataset)
        self.assertEqual(result["local_state"], "pass")
        self.assertEqual(result["dictionary_schemas_verified"], 1)
        self.assertEqual(result["upload_state"], "unverified")
        self.assertEqual(result["model_read_use_state"], "unverified")
        self.assertFalse(result["new_ui_evidence"])
        self.assertIsNone(result["ai_accuracy"])

    def test_private_benchmark_text_is_rejected_from_attachment(self):
        pack, dataset = self.attachment_pack("A private unseen fixture question.")
        result = check_attachment_pack(pack, dataset, ["A private unseen fixture question."])
        self.assertEqual(result["local_state"], "fail")
        self.assertIn("private_benchmark_text_detected:data-dictionary.txt", result["errors"])

    def test_png_filter_roundtrip_and_mask_integrity(self):
        raw, redacted = self.root / "raw.png", self.root / "redacted.png"
        raw.write_bytes(png_bytes(8, 8, mode=1))
        redacted.write_bytes(png_bytes(8, 8, {(1, 1): (0, 0, 0)}))
        self.assertEqual(png_pixels(raw)[:3], (8, 8, 3))
        self.assertEqual(redaction_errors(raw, redacted, [{"x": 1, "y": 1, "width": 1, "height": 1}]), [])
        self.assertIn("pixels_changed_outside_declared_redactions", redaction_errors(raw, redacted, []))

    def test_declared_native_crop_preserves_original_pixels(self):
        raw, crop = self.root / "raw.png", self.root / "crop.png"
        raw.write_bytes(png_bytes(8, 8, {(3, 3): (10, 20, 30)}))
        crop.write_bytes(png_bytes(4, 4, {(1, 1): (10, 20, 30)}))
        self.assertEqual(redaction_errors(raw, crop, [], [2, 2, 6, 6]), [])
        crop.write_bytes(png_bytes(4, 4))
        self.assertIn("pixels_changed_outside_declared_redactions",
                      redaction_errors(raw, crop, [], [2, 2, 6, 6]))

    def test_crop_outside_original_is_rejected(self):
        raw, crop = self.root / "raw.png", self.root / "crop.png"
        raw.write_bytes(png_bytes(8, 8))
        crop.write_bytes(png_bytes(4, 4))
        self.assertIn("invalid_capture_crop_box", redaction_errors(raw, crop, [], [0, 0, 12, 4]))

    def test_png_resize_and_excessive_mask_are_not_accepted(self):
        raw, changed = self.root / "raw.png", self.root / "changed.png"
        raw.write_bytes(png_bytes(8, 8))
        changed.write_bytes(png_bytes(7, 8))
        self.assertIn("capture_resized_cropped_or_reencoded", redaction_errors(raw, changed, []))
        changed.write_bytes(raw.read_bytes())
        self.assertIn("redaction_obscures_too_much_evidence",
                      redaction_errors(raw, changed, [{"x": 0, "y": 0, "width": 8, "height": 8}]))

    def test_png_checksum_detects_corruption(self):
        raw = self.root / "raw.png"
        data = bytearray(png_bytes(8, 8))
        data[20] ^= 1
        raw.write_bytes(data)
        with self.assertRaises(pc.EvidenceError):
            png_pixels(raw)

    def test_html_missing_images_and_anchors_are_failures(self):
        html = self.root / "guide.html"
        html.write_text('<h1 id="a">A</h1><img src="missing.png"><a href="#missing">Bad</a>', encoding="utf-8")
        result = check_html(html, self.root)
        self.assertEqual(result["local_state"], "fail")
        self.assertEqual(len(result["errors"]), 2)

    def test_html_local_links_good_external_still_unverified(self):
        (self.root / "image.png").write_bytes(png_bytes(8, 8))
        html = self.root / "guide.html"
        html.write_text('<h1 id="a">A</h1><img src="image.png"><a href="#a">A</a>'
                        '<a href="https://learn.microsoft.com/">Docs</a>', encoding="utf-8")
        result = check_html(html, self.root)
        self.assertEqual(result["local_state"], "pass")
        self.assertEqual(len(result["external_unverified"]), 1)
        self.assertFalse(result["live_screenshot_provenance_implied"])

    def test_html_self_contained_pngs_are_decoded_and_hashed(self):
        content = png_bytes(8, 8)
        html = self.root / "guide.html"
        html.write_text('<img src="data:image/png;base64,' + base64.b64encode(content).decode() + '">', encoding="utf-8")
        result = check_html(html, self.root)
        self.assertEqual(result["local_state"], "pass")
        self.assertEqual(result["images"][0]["sha256"], hashlib.sha256(content).hexdigest())
        self.assertEqual((result["images"][0]["width"], result["images"][0]["height"]), (8, 8))

    def test_html_invalid_inline_images_are_not_accepted(self):
        html = self.root / "guide.html"
        html.write_text('<img src="data:image/png;base64,broken">', encoding="utf-8")
        result = check_html(html, self.root)
        self.assertEqual(result["local_state"], "fail")

    def test_lossless_webp_embed_matches_original_png_pixels(self):
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("Optional Pillow publication-image decoder unavailable.")
        png = png_bytes(8, 8, {(1, 1): (10, 20, 30)})
        output = BytesIO()
        with Image.open(BytesIO(png)) as image:
            image.save(output, format="WEBP", lossless=True)
        webp = output.getvalue()
        self.assertEqual(image_pixel_signature(png)["rgba_sha256"], image_pixel_signature(webp)["rgba_sha256"])
        html = self.root / "guide.html"
        html.write_text('<img src="data:image/webp;base64,' + base64.b64encode(webp).decode() + '">', encoding="utf-8")
        result = check_html(html, self.root)
        self.assertEqual(result["local_state"], "pass")
        self.assertEqual(result["images"][0]["mime"], "image/webp")

    def test_unchanged_image_bytes_do_not_excuse_rendered_distortion(self):
        result = rendered_image_geometry([{"document": "html-ja", "matching_capture_placements": [{
            "capture_id": "portrait", "page": 1, "native_width": 379, "native_height": 902,
            "display_rects_points": [[0, 0, 284.25, 425.25]],
        }]}])
        self.assertEqual(result["state"], "fail")
        self.assertGreater(result["images"][0]["horizontal_to_vertical_scale_ratio"], 1.5)

    def test_proportionally_scaled_capture_passes_geometry_gate(self):
        result = rendered_image_geometry([{"document": "word", "matching_capture_placements": [{
            "capture_id": "portrait", "page": 1, "native_width": 379, "native_height": 902,
            "display_rects_points": [[0, 0, 151.6, 360.8]],
        }]}])
        self.assertEqual(result["state"], "pass")

    def test_docx_missing_media_and_unresolved_relationship(self):
        path = self.root / "guide.docx"
        with ZipFile(path, "w") as archive:
            archive.writestr("word/document.xml",
                             '<document xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
                             '<image r:embed="rMissing"/></document>')
            archive.writestr("word/_rels/document.xml.rels",
                             '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                             '<Relationship Id="r1" Target="media/missing.png"/></Relationships>')
        result = check_docx(path)
        self.assertEqual(result["local_state"], "fail")
        self.assertEqual(len(result["errors"]), 2)

    def test_generated_files_are_not_attachment_upload(self):
        path = self.root / "dictionary.txt"
        path.write_text("Unit dictionary without private evaluation answers.", encoding="utf-8")
        key = self.proof("upload_receipt")
        proof = self.manifest["evidence"][key]
        proof["attachments"] = [{"path": path.name, "sha256": pc.file_hash(path), "size_bytes": path.stat().st_size}]
        errors, _ = pc.evidence_errors(proof, "upload_receipt", self.manifest["context"], self.readiness, self.store)
        self.assertIn("upload_session_or_content_review_missing", errors)
        self.assertIn("uploaded_bytes_or_receipt_missing", errors)

    def test_attachment_count_and_size_caps(self):
        path = self.root / "too-large.txt"
        path.write_bytes(b"x" * (5242880 + 1))
        key = self.proof("upload_receipt")
        proof = self.manifest["evidence"][key]
        proof.update(actual_upload=True, conversation_id="unit-conversation")
        proof["review"]["no_heldout_or_secrets"] = True
        proof["attachments"] = [{"path": path.name, "sha256": pc.file_hash(path),
                                 "size_bytes": path.stat().st_size, "upload_id": "fixture"}] * 11
        errors, _ = pc.evidence_errors(proof, "upload_receipt", self.manifest["context"], self.readiness, self.store)
        self.assertIn("attachment_count_out_of_bounds", errors)
        self.assertIn("attachment_size_out_of_bounds", errors)


class RealSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.oracle = compute_oracle(REPO)

    def test_real_static_and_increment_data_contract(self):
        self.assertEqual((self.oracle["static"]["rows"], self.oracle["static"]["amount_yen"]), (80000, 1344099000))
        increment = self.oracle["increment"]
        self.assertEqual((increment["raw_rows"], increment["unique_event_ids"], increment["duplicate_event_ids"]),
                         (15000, 14900, 100))
        self.assertEqual((increment["raw_amount_yen"], increment["accepted_amount_yen"]), (253886000, 252058000))
        self.assertFalse(self.oracle["live_data_verified"])

    def test_original_full_graph_and_partial_are_distinct(self):
        graph = self.oracle["graph"]
        self.assertEqual((graph["full_original_nodes"], graph["full_original_edges"]), (109592, 297303))
        result = graph_expectations(self.oracle, {
            "projection": "selected_original_tables", "tables": ["ot_municipality", "ot_prefecture"],
            "relationships": ["MunicipalityInPrefecture"],
        })
        self.assertEqual((result["node_count"], result["edge_count"]), (1788, 1741))

    def test_filtered_or_mislabelled_full_graph_never_gets_full_counts(self):
        scope = {"projection": "full_original", "tables": ["ot_prefecture"], "relationships": []}
        with self.assertRaises(pc.EvidenceError):
            graph_expectations(self.oracle, scope)
        scope.update(projection="selected_original_tables", filters={"PrefectureID": 1})
        with self.assertRaises(pc.EvidenceError):
            graph_expectations(self.oracle, scope)

    def test_graph_relationship_needs_both_endpoints(self):
        with self.assertRaises(pc.EvidenceError):
            graph_expectations(self.oracle, {"projection": "selected_original_tables",
                                            "tables": ["ot_prefecture"], "relationships": ["MunicipalityInPrefecture"]})

    def test_original_csv_and_rubric_bytes_match_public_baseline(self):
        result = immutable_baseline(REPO, BASELINE, self.oracle)
        self.assertTrue(result["all_byte_identical"])
        self.assertEqual(len(result["files"]), 15)

    def test_original_suite_is_unchanged_public_ten_eightyfour(self):
        frozen = original_suite(REPO)
        self.assertEqual(len(frozen["suite"]["cases"]), 10)
        self.assertEqual(sum(len(case["conditions"]) for case in frozen["suite"]["cases"]), 84)
        self.assertTrue(frozen["published_not_independent_hidden"])


class Gen2ContractTests(unittest.TestCase):
    @staticmethod
    def part(path, text):
        return {"path": path, "payloadType": "InlineBase64",
                "payload": base64.b64encode(text.encode("utf-8")).decode("ascii")}

    def parts(self):
        return [
            self.part(".platform", '{"metadata":{"type":"Ontology"},"config":{"version":"2.0"}}'),
            self.part("database.tmdl", "database\n\tcompatibilityLevel: 1000000\n"),
            self.part("model.tmdl", "model Model\n\tref namespace default\n"),
            self.part("namespaces/default.tmdl", "namespace default\n"),
        ]

    def test_gen2_requires_native_generation_and_tmdl_readback(self):
        self.assertEqual(pc.gen2_definition_check(2, self.parts())["errors"], [])
        self.assertIn("source_truth_mismatch:ontology_generation_not_two",
                      pc.gen2_definition_check(1, self.parts())["errors"])

    def test_legacy_entitytypes_json_is_not_new_ui_evidence(self):
        parts = [self.part("EntityTypes/unit/definition.json", "{}")]
        result = pc.gen2_definition_check(1, parts)
        self.assertIn("source_truth_mismatch:legacy_entitytypes_json_is_not_gen2", result["errors"])
        self.assertIn("required_gen2_readback_parts_missing", result["errors"])

    def test_adding_a_table_dax_measure_is_legal_but_not_metric_proof(self):
        parts = self.parts() + [self.part("tables/Source.tmdl", "table Source\n\tmeasure Total = SUM(Source[Amount])\n")]
        self.assertEqual(pc.gen2_definition_check(2, parts)["errors"], [])

    def test_explicit_dax_metric_is_rejected(self):
        parts = self.parts() + [self.part("metrics/Unsafe.tmdl", "metric Unsafe\n\texpression\n\t\tdialect: DAX\n")]
        self.assertIn("source_truth_mismatch:explicit_dax_metric_forbidden",
                      pc.gen2_definition_check(2, parts)["errors"])

    def test_projected_tmdl_marks_roundtrip_loss_without_denying_gen2_identity(self):
        parts = self.parts() + [self.part("metrics/Projected.tmdl", "metric Projected\n\ttype: projected\n")]
        result = pc.gen2_definition_check(2, parts)
        self.assertEqual(result["errors"], [])
        self.assertEqual(len(result["roundtrip_limitations"]), 1)

    def test_metric_gate_requires_actual_source_owned_projection_link(self):
        binding = {
            "surface": "native_ui", "metric_type_pointer": "/response/metric/type",
            "backing_measure_pointer": "/response/metric/backingMeasure",
            "source_table_pointer": "/response/measure/table",
            "source_measure_pointer": "/response/measure/name",
            "source_dax_pointer": "/response/measure/expression",
        }
        record = {"metric_binding": binding,
                  "metric_reconciliation": {"dax_pointer": "/response/value", "source_pointer": "/response/value"}}
        bodies = {
            "model": {"response": {"measure": {"table": "Source", "name": "Total", "expression": "SUM(Source[Amount])"}}},
            "metric": {"response": {"metric": {"type": "projected", "backingMeasure": {"table": "Source", "measure": "Total"}}}},
            "dax": {"response": {"value": 100}}, "source": {"response": {"value": 100}},
        }
        proofs = {"metric": {"origin": "coordinator_browser"}}
        self.assertEqual(pc._feature_errors({"id": "METRIC01"}, record, proofs, bodies, {}), [])
        binding["surface"] = "tmdl_export"
        self.assertIn("tmdl_export_is_not_projected_metric_link_evidence",
                      pc._feature_errors({"id": "METRIC01"}, record, proofs, bodies, {}))
        binding["surface"] = "native_ui"
        bodies["metric"]["response"]["metric"]["backingMeasure"]["measure"] = "Other"
        self.assertIn("source_truth_mismatch:metric_backing_measure_identity",
                      pc._feature_errors({"id": "METRIC01"}, record, proofs, bodies, {}))


class NativeObservationTests(unittest.TestCase):
    @staticmethod
    def discovery():
        return {"aiQuestionsSent": 0, "mutations": 0, "requests": [
            {"method": "initialize", "status": 200, "requestId": "init-fixture",
             "body": pc.encode({"jsonrpc": "2.0", "id": 1, "result": {
                 "protocolVersion": "2025-06-18", "serverInfo": {"name": "Microsoft Fabric Ontology", "version": "1.0"}
             }}).decode()},
            {"method": "notifications/initialized", "status": 202, "body": ""},
            {"method": "tools/list", "status": 200, "requestId": "list-fixture",
             "body": pc.encode({"jsonrpc": "2.0", "id": 2, "result": {"tools": [
                 {"name": "ask_ontology", "inputSchema": {"type": "object", "required": ["request"]}},
                 {"name": "list_ontology_rules", "inputSchema": {"type": "object", "required": []}},
                 {"name": "list_ontology_entities", "inputSchema": {"type": "object", "required": []}},
             ]}}).decode()},
        ]}

    def test_native_catalog_success_does_not_prove_an_answer_or_query(self):
        result = inspect_mcp_discovery(self.discovery())
        self.assertEqual(result["discovery_state"], "pass")
        self.assertEqual(result["protocol_version"], "2025-06-18")
        self.assertEqual(len(result["advertised_tool_names"]), 3)
        self.assertNotIn("list_ontology_entity_types", result["advertised_tool_names"])
        self.assertFalse(result["query_execution_proven"])
        self.assertIsNone(result["ai_accuracy"])

    def test_failed_notification_and_question_call_are_not_hidden(self):
        capture = self.discovery()
        capture["requests"][1]["status"] = 500
        capture["requests"].append({"method": "tools/call", "status": 200, "body": "{}"})
        result = inspect_mcp_discovery(capture)
        self.assertEqual(result["discovery_state"], "unverified")
        self.assertIn("initialized_notification_failed", result["errors"])
        self.assertIn("non_discovery_request_present", result["errors"])

    @staticmethod
    def snapshot(text, moment):
        return {"itemId": "fixture-item", "readOnly": True, "capturedUtc": moment,
                "definition": {"parts": [Gen2ContractTests.part("entities/Area.tmdl", text)]}}

    def test_exact_entity_synonym_addition_preserves_protected_content(self):
        text = "/// Original description\nentity Area\n\tproperty Name\n\t\treusableProperty: Name\n"
        before = self.snapshot(text, FROZEN)
        after = self.snapshot(text + "\n\tsynonym Region\n", CAPTURED)
        result = check_synonym_only_delta(before, after, "entities/Area.tmdl", "Region")
        self.assertEqual(result["structural_delta_state"], "pass")
        self.assertEqual(result["protected_content_changes"], [])

    def test_lost_reusable_reference_fails_even_when_restore_succeeds(self):
        text = "/// Original description\nentity Area\n\tlineageTag: same\n\tproperty Name\n\t\treusableProperty: Name\n"
        before = self.snapshot(text, FROZEN)
        after = self.snapshot(text.replace("\t\treusableProperty: Name\n", "") + "\tsynonym Region\n", CAPTURED)
        restored = self.snapshot(text, "2026-01-01T00:00:04Z")
        result = check_synonym_only_delta(before, after, "entities/Area.tmdl", "Region", restored)
        self.assertEqual(result["structural_delta_state"], "fail")
        self.assertTrue(result["restored_definition_equals_before"])
        self.assertTrue(result["restore_does_not_erase_failed_candidate"])
        self.assertFalse(result["version_history_ui_action_proven"])

    def test_property_synonym_is_not_the_requested_entity_synonym(self):
        text = "entity Area\n\tproperty Name\n"
        result = check_synonym_only_delta(self.snapshot(text, FROZEN),
                                         self.snapshot(text + "\t\tsynonym Region\n", CAPTURED),
                                         "entities/Area.tmdl", "Region")
        self.assertEqual(result["structural_delta_state"], "fail")


if __name__ == "__main__":
    unittest.main()
