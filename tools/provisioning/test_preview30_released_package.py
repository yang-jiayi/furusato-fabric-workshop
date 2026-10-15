"""Released ZIP baseline checks, with real immutable CSVs and zero cloud I/O."""
from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import preview30_runtime as rt


class ReleasedPackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture_temp = tempfile.TemporaryDirectory()
        cls.fixture = Path(cls.fixture_temp.name) / "released-source"
        cls.fixture.mkdir()
        names = set(rt.RUNTIME_INPUT_FILES)
        names.add("workshop/v3.0.0-preview/provisioning/baseline-hashes.json")
        cls.protected = {}
        for relative in rt.BASELINE_PROTECTED_PATHS:
            root = rt.REPO / relative
            paths = [root] if root.is_file() else sorted(root.rglob("*"))
            for path in paths:
                if path.is_file():
                    if path.is_symlink():
                        raise AssertionError("Source fixture must not contain symlinks")
                    name = path.relative_to(rt.REPO).as_posix()
                    names.add(name)
                    cls.protected[name] = hashlib.sha256(path.read_bytes()).hexdigest()
        files = {}
        for name in names:
            target = cls.fixture / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(rt.REPO / name, target)
            files[name] = hashlib.sha256(target.read_bytes()).hexdigest()
        cls.baseline = rt.load(cls.fixture / "workshop/v3.0.0-preview/provisioning/baseline-hashes.json")
        cls.manifest = {"schemaVersion": "furusato-v3-artifact-set/v1", "workshopVersion": rt.WORKSHOP_VERSION,
            "runtimeProfile": rt.EDITION, "sourceCommit": "a" * 40,
            "edition": rt.load(cls.fixture / "workshop/v3.0.0-preview/edition.json"),
            "files": files, "sourceTreeSha256": rt.digest(files),
            "immutableBaselineTreeSha256": cls.baseline["treeSha256"],
            "baselineProtection": {"schemaVersion": "furusato-protected-baseline/v1",
                "baselineCommit": rt.BASELINE_COMMIT, "protectedPaths": list(rt.BASELINE_PROTECTED_PATHS),
                "files": cls.protected, "treeSha256": rt.digest(cls.protected)}}
        (cls.fixture / "artifact-set.json").write_text(json.dumps(cls.manifest), encoding="utf-8")

    @classmethod
    def tearDownClass(cls):
        cls.fixture_temp.cleanup()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "source"
        shutil.copytree(self.fixture, self.root)
        self.env = patch.dict(os.environ, {key: value for key, value in os.environ.items()
            if key not in {"GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR"}}, clear=True)
        self.env.start()
        self.paths = patch.multiple(rt, REPO=self.root, BASE=self.root / "workshop/v2.7.0",
                                    PREVIEW=self.root / "workshop/v3.0.0-preview")
        self.paths.start()

    def tearDown(self):
        self.paths.stop()
        self.env.stop()
        self.temp.cleanup()

    def change_manifest(self, change):
        doc = copy.deepcopy(self.manifest)
        change(doc)
        (self.root / "artifact-set.json").write_text(json.dumps(doc), encoding="utf-8")

    def test_real_109_file_baseline_and_csvs_verify_without_git_or_cloud(self):
        with patch.object(rt.subprocess, "run") as git, patch.object(rt, "EvidenceClient") as cloud:
            result = rt.immutable_baseline()
        self.assertEqual(result, self.baseline)
        self.assertEqual(len(result["files"]), 109)
        self.assertEqual(result["staticDonationRows"], 80000)
        self.assertEqual(result["staticDonationYen"], 1344099000)
        self.assertEqual(result["acceptedUniqueRows"], 14900)
        git.assert_not_called()
        cloud.assert_not_called()

    def test_nonprotected_runtime_tamper_is_detected_before_online_client(self):
        (self.root / "tools/provisioning/preview30_deploy.py").write_text("tampered", encoding="utf-8")
        scope_path = Path(self.temp.name) / "scope.json"
        scope_path.write_text(json.dumps({"tenantId": "11111111-1111-4111-8111-111111111111",
            "workspaceId": "22222222-2222-4222-8222-222222222222", "workspaceName": "fixture",
            "folderId": "33333333-3333-4333-8333-333333333333", "portalSubfolderId": "1", "participantId": "001"}))
        args = SimpleNamespace(scope=scope_path, environment="dev", evidence_dir=Path(self.temp.name) / "evidence", online=True)
        with patch.object(rt, "EvidenceClient") as cloud, self.assertRaises(rt.SafetyError):
            rt.preflight(args)
        cloud.assert_not_called()

    def test_missing_modified_or_extra_protected_file_is_rejected(self):
        original = self.root / "tools/docs/furusato_docs/tests10.py"
        data = original.read_bytes()
        for action in ("missing", "modified", "extra"):
            with self.subTest(action=action):
                original.write_bytes(data)
                extra = self.root / "tools/data-agent/source-contract/unlisted.json"
                if extra.exists():
                    extra.unlink()
                if action == "missing":
                    original.unlink()
                elif action == "modified":
                    original.write_bytes(data + b"\n# changed\n")
                else:
                    extra.write_text("{}")
                with self.assertRaises(rt.SafetyError):
                    rt._released_package_baseline()

    def test_protected_bytecode_and_symlinks_are_rejected(self):
        cache = self.root / "tools/data-agent/reference-models/__pycache__"
        cache.mkdir()
        bytecode = cache / "reference_models.cpython-313.pyc"
        bytecode.write_bytes(b"unlisted executable bytecode")
        with self.assertRaises(rt.SafetyError):
            rt._released_package_baseline()
        bytecode.unlink()
        target = self.root / "tools/docs/furusato_docs/tests10.py"
        target.unlink()
        target.symlink_to(self.fixture / "tools/docs/furusato_docs/tests10.py")
        with self.assertRaises(rt.SafetyError):
            rt._released_package_baseline()

    def test_path_traversal_absolute_backslash_and_alias_paths_are_rejected(self):
        for name in ("../outside", "/absolute", "tools/../outside", "tools\\outside", "tools//outside", "C:/outside"):
            def change(doc):
                doc["files"][name] = "b" * 64
                doc["sourceTreeSha256"] = rt.digest(doc["files"])
            with self.subTest(name=name):
                self.change_manifest(change)
                with self.assertRaises(rt.SafetyError):
                    rt._released_package_baseline()

    def test_duplicate_manifest_keys_are_rejected(self):
        path = self.root / "artifact-set.json"
        path.write_text('{"schemaVersion":"one","schemaVersion":"two"}')
        with self.assertRaisesRegex(rt.SafetyError, "Duplicate"):
            rt._released_package_baseline()

    def test_schema_version_source_and_baseline_bindings_are_required(self):
        changes = [lambda d: d.update(schemaVersion="unknown"), lambda d: d.update(workshopVersion="9.0.0"),
                   lambda d: d.update(runtimeProfile="legacy"), lambda d: d.update(sourceCommit="unknown"),
                   lambda d: d.update(sourceTreeSha256="0" * 64),
                   lambda d: d.update(immutableBaselineTreeSha256="0" * 64),
                   lambda d: d["baselineProtection"].update(baselineCommit="b" * 40),
                   lambda d: d["baselineProtection"].update(protectedPaths=[]),
                   lambda d: d["baselineProtection"].update(treeSha256="0" * 64)]
        for index, change in enumerate(changes):
            with self.subTest(change=index):
                self.change_manifest(change)
                with self.assertRaises(rt.SafetyError):
                    rt._released_package_baseline()

    def test_removing_protected_file_from_both_inventories_does_not_hide_it(self):
        name = "tools/docs/furusato_docs/tests10.py"
        def change(doc):
            del doc["files"][name]
            del doc["baselineProtection"]["files"][name]
            doc["sourceTreeSha256"] = rt.digest(doc["files"])
            doc["baselineProtection"]["treeSha256"] = rt.digest(doc["baselineProtection"]["files"])
        self.change_manifest(change)
        with self.assertRaises(rt.SafetyError):
            rt._released_package_baseline()

    def test_baseline_receipt_cannot_be_substituted_with_rehashed_wrong_counts(self):
        path = self.root / "workshop/v3.0.0-preview/provisioning/baseline-hashes.json"
        altered = copy.deepcopy(self.baseline)
        altered["staticDonationRows"] = 79999
        path.write_text(json.dumps(altered))
        def change(doc):
            doc["files"][path.relative_to(self.root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
            doc["sourceTreeSha256"] = rt.digest(doc["files"])
        self.change_manifest(change)
        with self.assertRaisesRegex(rt.SafetyError, "Independent CSV"):
            rt.immutable_baseline()

    def test_git_error_and_broken_git_marker_never_fall_back_to_package(self):
        (self.root / ".git").write_text("gitdir: /missing/worktree")
        failure = subprocess.CalledProcessError(128, ["git"])
        with patch.object(rt.subprocess, "run", side_effect=failure) as git, \
                patch.object(rt, "_released_package_baseline") as package, self.assertRaises(subprocess.CalledProcessError):
            rt.immutable_baseline()
        package.assert_not_called()
        command = git.call_args.args[0]
        self.assertEqual(tuple(command[command.index("--") + 1:]), rt.BASELINE_PROTECTED_PATHS)
        self.assertIn(rt.BASELINE_COMMIT, command)
        self.assertTrue(git.call_args.kwargs["check"])

    def test_explicit_git_environment_never_selects_package_mode(self):
        with patch.dict(os.environ, {"GIT_DIR": "/missing/git"}):
            self.assertTrue(rt._git_metadata_present())

    def test_private_directory_remains_outside_extracted_source(self):
        with self.assertRaises(rt.SafetyError):
            rt.private_directory(self.root / "private-evidence")


if __name__ == "__main__":
    unittest.main()
