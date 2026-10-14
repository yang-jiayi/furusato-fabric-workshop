"""Version selection and immutable historical inputs; synthetic source metadata only."""
import ast
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import measured_contract_profile as measured
from source_grounded_profile import decoded_parts
import test_measured_contract_gen2 as native_tests


class MeasuredContractVersionTests(unittest.TestCase):
    def test_default_and_explicit_versions_report_their_validated_identity(self):
        original, inputs, _ = native_tests.fixture()
        self.assertEqual(measured.CURRENT_PROFILE, "measured-contract-20261015")
        self.assertEqual(measured.PROFILE.name, measured.CURRENT_PROFILE)
        for name in measured.SUPPORTED_PROFILES:
            with self.subTest(profile=name):
                profile = measured.PROFILE_ROOT / name
                out, receipt = measured.compile_measured_draft(original, profile=profile, **inputs)
                self.assertEqual(receipt["profile"], name)
                self.assertEqual(receipt["profileManifestSha256"], measured.digest(json.loads((profile / "profile-manifest.json").read_bytes())))
                self.assertEqual(decoded_parts(out)["Files/Config/draft/stage_config.json"]["aiInstructions"],
                                 (profile / "global-instructions.txt").read_text().strip())
                if name == measured.CURRENT_PROFILE:
                    self.assertEqual((out, receipt), measured.compile_measured_draft(original, **inputs))
                else:
                    self.assertEqual(receipt["instructionUtf16Units"],
                                     {"global": 9981, "lakehouse_tables": 9989, "kusto": 8665, "semantic_model": 6989})

    def test_only_three_instruction_inputs_change_and_fewshot_identity_is_stable(self):
        legacy = measured.PROFILE_ROOT / "measured-contract-20261009"
        current_manifest = json.loads((measured.PROFILE / "profile-manifest.json").read_bytes())
        old_manifest = json.loads((legacy / "profile-manifest.json").read_bytes())
        changed = {name for name in current_manifest["sha256"]
                   if current_manifest["sha256"][name] != old_manifest["sha256"][name]}
        self.assertEqual(changed, {"global-instructions.txt", "lakehouse-instructions.txt", "semantic-model-instructions.txt"})
        for name in set(old_manifest["sha256"]) - changed | {"sql-schema-inventory.sql"}:
            self.assertEqual((measured.PROFILE / name).read_bytes(), (legacy / name).read_bytes())
        original, inputs, path = native_tests.fixture()
        outputs = [measured.compile_measured_draft(original, profile=measured.PROFILE_ROOT / name, **inputs)[0]
                   for name in measured.SUPPORTED_PROFILES]
        docs = [decoded_parts(out) for out in outputs]
        self.assertEqual(docs[0]["Files/Config/draft/kusto/fewshots.json"], docs[1]["Files/Config/draft/kusto/fewshots.json"])
        self.assertEqual([p for p in outputs[0]["parts"] if "/draft/" not in p["path"]],
                         [p for p in outputs[1]["parts"] if "/draft/" not in p["path"]])
        self.assertEqual(docs[0][path.replace("/published/", "/draft/")], docs[1][path.replace("/published/", "/draft/")])

    def test_staged_directory_name_is_not_a_profile_identity_and_unknown_identity_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            staged = Path(directory) / "reviewed-copy"
            shutil.copytree(measured.PROFILE, staged)
            original, inputs, _ = native_tests.fixture()
            _, receipt = measured.compile_measured_draft(original, profile=staged, **inputs)
            self.assertEqual(receipt["profile"], measured.CURRENT_PROFILE)
            manifest_path = staged / "profile-manifest.json"
            manifest = json.loads(manifest_path.read_bytes())
            for identity in ("unknown-profile", None, [measured.CURRENT_PROFILE]):
                manifest["profile"] = identity
                manifest_path.write_text(json.dumps(manifest))
                with self.subTest(identity=identity), self.assertRaises(ValueError):
                    measured.profile_inputs(staged)

    def test_current_edition_runtime_and_build_profile_identities_agree(self):
        edition = json.loads((measured.REPO / "workshop/v3.0.0-preview/edition.json").read_bytes())
        self.assertEqual(edition["correctedAgentProfile"], measured.CURRENT_PROFILE)
        for filename in ("preview30_runtime.py", "build_preview30.py"):
            tree = ast.parse((measured.REPO / "tools/provisioning" / filename).read_text())
            declared = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Dict):
                    for key, value in zip(node.keys, node.values):
                        if isinstance(key, ast.Constant) and key.value == "correctedAgentProfile":
                            declared.append(ast.literal_eval(value))
            with self.subTest(source=filename):
                self.assertEqual(len(declared), 1)
                self.assertEqual(declared[0], "data-agent/candidates/" + measured.CURRENT_PROFILE)
            if filename == "preview30_runtime.py":
                profiles = next(ast.literal_eval(node.value) for node in tree.body
                                if isinstance(node, ast.Assign)
                                and any(isinstance(target, ast.Name) and target.id == "CORRECTED_PROFILE_DIRECTORIES"
                                        for target in node.targets))
                self.assertIn(measured.CURRENT_PROFILE, profiles)
                self.assertIn("measured-contract-20261009", profiles)

    def test_cli_exposes_only_fixed_supported_profile_choices(self):
        help_text = subprocess.check_output([sys.executable, "-B", str(Path(measured.__file__)), "--help"], text=True)
        self.assertIn("--profile", help_text)
        for name in measured.SUPPORTED_PROFILES:
            self.assertIn(name, help_text)
        rejected = subprocess.run([sys.executable, "-B", str(Path(measured.__file__)), "--profile", "../untrusted"],
                                  text=True, capture_output=True)
        self.assertEqual(rejected.returncode, 2)
        self.assertIn("invalid choice", rejected.stderr)


if __name__ == "__main__":
    unittest.main()
