import copy
import json
from pathlib import Path
import tempfile
import unittest

import preview30_runtime as rt
import v3_artifacts
import build_preview30


class ArtifactVersionTests(unittest.TestCase):
    def test_current_artifact_snapshot_has_coherent_component_versions(self):
        result = v3_artifacts.snapshot()
        self.assertEqual(result["workshopVersion"], rt.WORKSHOP_VERSION)
        self.assertEqual(result["edition"]["datasetVersion"], "2.7.0-realistic.1")
        self.assertEqual(result["csvFiles"], 11)
        self.assertEqual(set(result["notebooks"]), {"01", "02", "03", "04", "05"})
        self.assertFalse(result["tempRequired"])
        self.assertFalse(result["cloudDeploymentProvenByThisManifest"])
        self.assertIn("tools/data-agent/fresh_grounded_profile.py", result["files"])

    def test_stale_notebook_version_and_processing_edits_are_rejected(self):
        path = next((rt.PREVIEW / "notebooks").glob("Notebook_01_*.ipynb"))
        old = rt.load(next((rt.BASE / "notebooks").glob("Notebook_01_*.ipynb")))
        value = rt.load(path)
        self.assertTrue(v3_artifacts.verify_notebook(value, old))
        bad = copy.deepcopy(value)
        bad["metadata"]["furusato"]["version"] = "2.7.0"
        with self.assertRaises(ValueError):
            v3_artifacts.verify_notebook(bad, old)
        bad = copy.deepcopy(value)
        bad["cells"][3]["source"].append("\nunexpected_change = True\n")
        with self.assertRaises(ValueError):
            v3_artifacts.verify_notebook(bad, old)

    def test_notebook05_exit_value_contract_is_the_only_processing_delta(self):
        path = next((rt.PREVIEW / "notebooks").glob("Notebook_05_*.ipynb"))
        old = rt.load(next((rt.BASE / "notebooks").glob("Notebook_05_*.ipynb")))
        value = rt.load(path)
        self.assertTrue(v3_artifacts.verify_notebook(value, old, number="05"))
        bad = copy.deepcopy(value)
        bad["cells"][-1]["source"].append("\nunexpected_change = True\n")
        with self.assertRaises(ValueError):
            v3_artifacts.verify_notebook(bad, old, number="05")

    def test_preview_contract_requires_current_workshop_identity(self):
        contract = {"edition": rt.EDITION, "workshopVersion": rt.WORKSHOP_VERSION}
        self.assertTrue(v3_artifacts.verify_preview_contract(contract))
        stale = {**contract, "workshopVersion": "3.0.0"}
        with self.assertRaises(ValueError):
            v3_artifacts.verify_preview_contract(stale)

    def test_builder_requires_explicit_canonical_alignment_for_stale_contract(self):
        baseline = {"treeSha256": "a" * 64, "files": {}, "staticDonationRows": 1}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            existing = root / "preview-contract.json"
            existing.write_text(json.dumps({
                "edition": "v3.0.0-preview", "workshopVersion": "3.0.0",
            }), encoding="utf-8")
            canonical = root / "WORKSHOP_VERSION"
            canonical.write_text(rt.WORKSHOP_VERSION, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "stale"):
                build_preview30.build_preview_contract(baseline, contract_path=existing)
            generated = build_preview30.build_preview_contract(
                baseline, contract_path=existing, align_preview_contract_from=canonical)
            self.assertEqual(generated["workshopVersion"], rt.WORKSHOP_VERSION)
            canonical.write_text("3.0.0", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "does not match"):
                build_preview30.build_preview_contract(
                    baseline, contract_path=existing, align_preview_contract_from=canonical)

    def test_notebook_manifest_matches_embedded_payload_hash_and_length(self):
        expected = {
            number: {"path": "notebooks/NB" + number, "bundle": {
                "payloadSha256": number, "compressedBytes": int(number),
            }} for number in ("02", "03", "04")
        }
        manifest = {
            number: {"path": entry["path"], "payloadSha256": entry["bundle"]["payloadSha256"],
                     "compressedBytes": entry["bundle"]["compressedBytes"]}
            for number, entry in expected.items()
        }
        self.assertTrue(v3_artifacts.verify_notebook_bundle_manifest(manifest, expected))
        for field in ("payloadSha256", "compressedBytes"):
            broken = copy.deepcopy(manifest)
            broken["03"][field] = "incorrect"
            with self.assertRaises(ValueError):
                v3_artifacts.verify_notebook_bundle_manifest(broken, expected)


if __name__ == "__main__":
    unittest.main()
