"""Offline refusal-path and immutability tests; these are not cloud evidence."""
from __future__ import annotations
import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import preview30_runtime as runtime


def scope():
    return runtime.scope_from_document({
        "tenantId": "11111111-1111-4111-8111-111111111111",
        "workspaceId": "22222222-2222-4222-8222-222222222222",
        "workspaceName": "test-only",
        "folderId": "33333333-3333-4333-8333-333333333333",
        "portalSubfolderId": "1", "participantId": "001",
        "folderMappingVerified": True,
    }, "dev")


class PreviewRuntimeTests(unittest.TestCase):
    def test_source_paths_are_explicit(self):
        self.assertTrue((runtime.REPO / "tools" / "provisioning" / "preview30_runtime.py").is_file())
        self.assertEqual(runtime.PREVIEW.name, "v3.0.0-preview")

    def test_private_evidence_required(self):
        with self.assertRaises(runtime.SafetyError):
            runtime.private_directory(runtime.REPO / "runtime")

    def test_candidate_name_is_not_mapping_proof(self):
        s = scope()
        s["folderMappingVerified"] = False
        with self.assertRaises(runtime.SafetyError):
            runtime.validate_gate(s, {"planSha256": "x"}, {}, "x")

    def test_exact_gate_acceptance_and_refusals(self):
        s = scope()
        plan = runtime.build_plan(s, {"items": [], "recoverableItems": []},
                                  {"treeSha256": "b" * 64, "files": {}})
        gate = {**{k: s[k] for k in ("workspaceId", "folderId", "participantId")},
                "scopeSha256": runtime.scope_fingerprint(s),
                "planSha256": plan["planSha256"], "allowCloudMutations": True,
                "folderMappingVerified": True, "approvedAt": "2026-01-01T00:00:00Z",
                "folderMappingEvidence": "private portal mapping receipt"}
        runtime.validate_gate(s, plan, gate, plan["planSha256"])
        changed = copy.deepcopy(plan)
        changed["resources"][0]["displayName"] = "unexpected-target"
        with self.assertRaises(runtime.SafetyError):
            runtime.validate_gate(s, changed, gate, plan["planSha256"])
        for field in gate:
            bad = copy.deepcopy(gate)
            bad[field] = False
            with self.subTest(field=field), self.assertRaises(runtime.SafetyError):
                runtime.validate_gate(s, plan, bad, plan["planSha256"])

    def test_no_secret_or_environment_ids_in_planned_names(self):
        names = runtime.planned_resources("123")
        self.assertTrue(all("123" in item["displayName"] for item in names))
        self.assertEqual(len({item["key"] for item in names}), len(names))
        self.assertEqual(next(x for x in names if x["key"] == "ontology")["purpose"], "generation2")

    def test_collision_is_blocking(self):
        s = scope()
        inventory = {"items": [], "recoverableItems": [
            {"displayName": "ONT_Furusato_001", "type": "Ontology"}]}
        baseline = {"treeSha256": "b" * 64, "files": {}}
        plan = runtime.build_plan(s, inventory, baseline)
        self.assertEqual(len(plan["blockers"]), 1)

    def test_resume_requires_exact_owned_receipt_in_folder(self):
        s = scope()
        item = {"id": "44444444-4444-4444-8444-444444444444",
                "displayName": "LH_Furusato_001", "type": "Lakehouse", "folderId": s["folderId"]}
        inventory = {"items": [item], "recoverableItems": []}
        baseline = {"treeSha256": "b" * 64, "files": {}}
        state = {"scopeSha256": runtime.scope_fingerprint(s), "items": {"lakehouse": item}}
        self.assertFalse(runtime.build_plan(s, inventory, baseline, state)["blockers"])
        altered = copy.deepcopy(state)
        altered["items"]["lakehouse"]["id"] = "55555555-5555-4555-8555-555555555555"
        self.assertTrue(runtime.build_plan(s, inventory, baseline, altered)["blockers"])
        outside = copy.deepcopy(inventory)
        outside["items"][0]["folderId"] = "66666666-6666-4666-8666-666666666666"
        self.assertTrue(runtime.build_plan(s, outside, baseline, state)["blockers"])

    def test_released_csv_contract(self):
        result = runtime.immutable_baseline()
        self.assertEqual(result["staticDonationRows"], 80000)
        self.assertEqual(result["staticDonationYen"], 1344099000)
        self.assertEqual(result["acceptedUniqueRows"], 14900)
        self.assertEqual(result["duplicateRows"], 100)

    def test_baseline_gate_pins_corpus_rubric_and_reference_assets_not_evolving_transport(self):
        from types import SimpleNamespace
        with patch.object(runtime.subprocess, "run", return_value=SimpleNamespace(stdout="")) as git:
            runtime.immutable_baseline()
        command = git.call_args.args[0]
        self.assertEqual(tuple(command[command.index("--") + 1:]), runtime.BASELINE_PROTECTED_PATHS)
        self.assertIn("workshop/v2.7.0", command)
        self.assertIn("tools/docs/furusato_docs/tests10.py", command)
        self.assertIn("tools/data-agent/source-contract", command)
        self.assertNotIn("tools/data-agent", command)
        self.assertIn("tools/data-agent/native_mcp.py", runtime.RUNTIME_INPUT_FILES)
        self.assertIn("tools/data-agent/native_evaluation.py", runtime.RUNTIME_INPUT_FILES)

    def test_original_rubric_or_reference_delta_still_blocks_build(self):
        from types import SimpleNamespace
        for path in ("tools/docs/furusato_docs/tests10.py", "tools/data-agent/source-contract/contract.json"):
            with patch.object(runtime.subprocess, "run", return_value=SimpleNamespace(stdout=path + "\n")):
                with self.subTest(path=path), self.assertRaises(runtime.SafetyError):
                    runtime.immutable_baseline()

    def test_latest_receipts_override_old_zero_deployment_flags(self):
        state = {"items": {"ontology": {"id": "owned"}, "semanticModel": {"id": "model"},
                           "dataAgent": {"id": "agent"}},
                 "ontologyVerification": {"generation": 2},
                 "ontologyNativeUiHandoff": {"automatedTmdlWritesDisabled": True},
                 "sourceVerification": {"verified": True},
                 "goldVerification": {"verified": True},
                 "qualityBranch": {"branch": "independent-lakehouse-staged-files"},
                 "modelDaxVerification": {"verified": True},
                 "dataAgentVerification": {"published": True}}
        facts = runtime.live_receipt_summary(state)
        self.assertTrue(facts["cloudMutationsOccurred"])
        self.assertTrue(facts["ontologyDeployed"])
        self.assertTrue(facts["goldVerified"])
        self.assertTrue(facts["dataAgentPublished"])
        self.assertFalse(facts["nativeAutomaticDeliveryVerified"])
        self.assertFalse(facts["aiAnswerQualityVerified"])

    def test_preflight_appends_progress_instead_of_erasing_history(self):
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            s = scope()
            runtime.save(root / "scope.json", s)
            runtime.save(root / "inventory.json", {
                "workspace": {"id": s["workspaceId"]},
                "folders": [{"id": s["folderId"]}], "items": [], "recoverableItems": []})
            progress = root / "progress-ja.md"
            progress.write_text("EXISTING VERIFIED PHASE HISTORY\n", encoding="utf-8")
            args = SimpleNamespace(scope=root / "scope.json", environment="dev",
                                   evidence_dir=root, online=False, inventory=root / "inventory.json")
            with patch.object(runtime, "immutable_baseline", return_value={"treeSha256": "b" * 64, "files": {}}):
                runtime.preflight(args)
            self.assertTrue(progress.read_text(encoding="utf-8").startswith("EXISTING VERIFIED PHASE HISTORY"))

if __name__ == "__main__":
    unittest.main()
