import copy
import unittest

import preview30_runtime as rt
import v3_artifacts


class ArtifactVersionTests(unittest.TestCase):
    def test_current_artifact_snapshot_has_coherent_component_versions(self):
        result = v3_artifacts.snapshot()
        self.assertEqual(result["workshopVersion"], "3.0.0")
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


if __name__ == "__main__":
    unittest.main()
