"""Offline one-Agent plan and sealed-profile tests."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

import workshop_runtime as runtime

ROOT = Path(__file__).resolve().parents[2]
BUNDLE = ROOT / "workshop" / "v2.7.0" / "provisioning" / "bundle"


class UnifiedRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = {
            "bundle": {p.relative_to(BUNDLE).as_posix(): p.read_bytes().decode("utf-8")
                       for p in BUNDLE.rglob("*") if p.is_file()},
            "assetHashes": json.loads(
                (BUNDLE.parent / "payload-manifest.json").read_text(encoding="utf-8")
            )["assetHashes"],
        }

    def test_legacy_defaults_are_preserved(self):
        config = runtime.ProvisioningConfig(participant_id="012")
        self.assertFalse(config.enable_unified_data_agent)
        self.assertFalse(config.enable_ai_reference_architecture)
        self.assertEqual(runtime.reference_agent_target(config, runtime.build_names("012"))["role"], "released")

    def test_modes_are_mutually_exclusive(self):
        config = runtime.ProvisioningConfig(
            enable_unified_data_agent=True, enable_ai_reference_architecture=True,
        )
        with self.assertRaisesRegex(runtime.ProvisioningError, "mutually exclusive"):
            runtime.validate_config(config)

    def test_unified_flag_is_boolean(self):
        with self.assertRaises(runtime.ProvisioningError):
            runtime.validate_config(runtime.ProvisioningConfig(enable_unified_data_agent="true"))

    def test_unified_mode_cannot_redirect_to_another_agent(self):
        config = runtime.ProvisioningConfig(
            enable_unified_data_agent=True, reference_agent_name="Some_other_agent",
        )
        with self.assertRaisesRegex(runtime.ProvisioningError, "primary Agent"):
            runtime.validate_config(config)

    def test_profile_enables_ci_and_preserves_full_teaching_ontology(self):
        assets = runtime.load_unified_assets(self.payload)
        self.assertEqual(assets["unifiedContract"]["teachingOntologyShape"], [10, 72, 1, 15])
        self.assertTrue(assets["stageConfig"]["experimental"]["codeInterpreterEnabled"])
        self.assertTrue(assets["stageConfig"]["experimental"]["enableExperimentalFeatures"])
        self.assertEqual(set(assets["sources"]), {"lakehouse_tables", "kusto", "ontology"})
        self.assertEqual(len(assets["sources"]["ontology"]["elements"]), 10)
        self.assertIsNone(assets["sources"]["ontology"]["instructions"])

    def test_unified_preview_creates_one_primary_agent_and_no_aipath(self):
        config = runtime.ProvisioningConfig(participant_id="012", enable_unified_data_agent=True)
        plan = runtime.build_preview_plan(
            config, self.payload, workspace_name="Fixture", folder_id="folder", existing_items=[],
        )
        self.assertEqual(len(plan.entries), 8)
        self.assertEqual([p.display_name for p in plan.entries if p.item_type == "DataAgent"], ["DA_Furusato_012"])
        self.assertEqual([p.display_name for p in plan.entries if p.item_type == "Ontology"], ["ONT_Furusato_012"])
        self.assertEqual(plan.reference_target["role"], "unified")
        self.assertTrue(plan.flags["enableUnifiedDataAgent"])
        self.assertNotIn("enableAiReferenceArchitecture", plan.flags)

    def test_missing_or_modified_profile_never_uses_reference_as_fallback(self):
        payload = copy.deepcopy(self.payload)
        del payload["bundle"]["unified-agent/contract.json"]
        with self.assertRaises(runtime.ProvisioningError):
            runtime.load_unified_assets(payload)
        payload = copy.deepcopy(self.payload)
        payload["bundle"]["unified-agent/profile.json"] += " "
        with self.assertRaisesRegex(runtime.ProvisioningError, "digest"):
            runtime.load_unified_assets(payload)

    def test_reference_lineage_and_core_source_are_pinned(self):
        for key in ("referenceContractSha256", "coreOntologySourceSha256"):
            payload = copy.deepcopy(self.payload)
            contract = json.loads(payload["bundle"]["unified-agent/contract.json"])
            contract[key] = "0" * 64
            payload["bundle"]["unified-agent/contract.json"] = json.dumps(contract)
            with self.subTest(key=key), self.assertRaises(runtime.ProvisioningError):
                runtime.load_unified_assets(payload)


if __name__ == "__main__":
    unittest.main()
