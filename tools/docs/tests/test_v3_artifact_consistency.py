import copy
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "tools/docs"), str(ROOT / "tools/html"), str(ROOT / "tools/provisioning")]
from furusato_docs import preview30_content as content
from furusato_docs.context import load_notebook
from furusato_html.model import Section
import v3_artifacts


class ArtifactConsistencyDocumentTests(unittest.TestCase):
    def roots(self):
        return [Section(ident=f"ch-{n}", level=1, number=str(n), title=content.t(str(n)), chapter=n)
                for n in range(1, 25)] + [
                    Section(ident="appendix-b", level=1, number="B", title=content.t("B"), appendix="B")]

    def test_shared_sections_bind_real_notebooks_and_no_temp_policy(self):
        manifest = v3_artifacts.snapshot()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "artifact-set.json"
            raw = json.dumps(manifest, ensure_ascii=False).encode("utf-8")
            path.write_bytes(raw)
            roots = self.roots()
            binding = content.artifact_consistency_sections(roots, ROOT, path)
        self.assertEqual(binding["manifestSha256"], hashlib.sha256(raw).hexdigest())
        self.assertEqual(binding["notebookCount"], 5)
        self.assertFalse(binding["tempRequired"])
        text = json.dumps([asdict(s) for s in roots], ensure_ascii=False)
        self.assertIn("Temp不要", text)
        self.assertIn("NOTEBOOK_VERSION", text)
        self.assertIn("3.0.0", text)
        for item in manifest["notebooks"].values():
            self.assertEqual(load_notebook(ROOT / item["path"], ROOT).version, "3.0.0")

    def test_stale_artifact_manifest_is_rejected_before_rendering(self):
        manifest = v3_artifacts.snapshot()
        bad = copy.deepcopy(manifest)
        bad["files"]["WORKSHOP_VERSION"] = "0" * 64
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "artifact-set.json"
            path.write_text(json.dumps(bad), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "changed after"):
                content.artifact_consistency_sections(self.roots(), ROOT, path)


if __name__ == "__main__":
    unittest.main()
