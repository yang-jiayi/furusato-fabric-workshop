"""Offline tests for the current-edition source validator; no fixtures are written."""
from __future__ import annotations

from pathlib import Path
import unittest
from unittest.mock import patch

try:
    from . import check_current_ontology as checker
except ImportError:
    import check_current_ontology as checker


SOURCE_ROOT = Path(__file__).resolve().parents[2]


class CurrentOntologyValidatorTests(unittest.TestCase):
    def test_current_source_passes_and_reports_recomputed_counts(self):
        result = checker.validate_source_root(SOURCE_ROOT)
        self.assertEqual("v3.0.0-preview", result["edition"])
        self.assertEqual(109592, result["nodeTotal"])
        self.assertEqual(297303, result["edgeTotal"])
        self.assertEqual(32, result["generation2DefinitionFiles"])

    def test_legacy_runtime_root_is_not_a_default_or_valid_target(self):
        legacy_root = SOURCE_ROOT / "workshop" / "v2.7.0"
        with self.assertRaisesRegex(checker.ValidationError, "Required current-edition file"):
            checker.validate_source_root(legacy_root)

    def test_changed_current_seed_csv_fails_closed(self):
        original_read = checker._read_bytes
        target = f"workshop/{checker.CURRENT_EDITION}/data/seed/prefectures.csv"

        def changed_read(root, relative_path):
            raw = original_read(root, relative_path)
            return raw + b"\n" if relative_path == target else raw

        with patch.object(checker, "_read_bytes", side_effect=changed_read):
            with self.assertRaisesRegex(checker.ValidationError, "artifact SHA-256 mismatch"):
                checker.validate_source_root(SOURCE_ROOT)

    def test_changed_current_generation2_contract_fails_closed(self):
        original_read = checker._read_bytes
        target = checker.GEN2_CONTRACT_PATH

        def changed_read(root, relative_path):
            raw = original_read(root, relative_path)
            return raw + b"\n" if relative_path == target else raw

        with patch.object(checker, "_read_bytes", side_effect=changed_read):
            with self.assertRaisesRegex(checker.ValidationError, "artifact SHA-256 mismatch"):
                checker.validate_source_root(SOURCE_ROOT)

    def test_changed_current_generation2_definition_fails_closed(self):
        original_read = checker._read_bytes
        target = f"workshop/{checker.CURRENT_EDITION}/ontology/definition/entityRelationships.tmdl"

        def changed_read(root, relative_path):
            raw = original_read(root, relative_path)
            return raw + b"\n" if relative_path == target else raw

        with patch.object(checker, "_read_bytes", side_effect=changed_read):
            with self.assertRaisesRegex(checker.ValidationError, "artifact SHA-256 mismatch"):
                checker.validate_source_root(SOURCE_ROOT)

    def test_missing_current_dependency_fails_closed(self):
        original_read = Path.read_bytes
        missing = SOURCE_ROOT / checker.DATASET_MANIFEST_PATH

        def missing_read(path):
            if path == missing:
                raise FileNotFoundError(path)
            return original_read(path)

        with patch.object(Path, "read_bytes", missing_read):
            with self.assertRaisesRegex(checker.ValidationError, "Required current-edition file"):
                checker.validate_source_root(SOURCE_ROOT)

    def test_present_invalid_outer_manifest_never_falls_back_to_checkout(self):
        original_read = checker._read_bytes
        original_exists = Path.exists

        def exists(path):
            return True if path == SOURCE_ROOT / checker.ARTIFACT_SET_PATH else original_exists(path)

        def read(root, relative):
            return b"{}" if relative == checker.ARTIFACT_SET_PATH else original_read(root, relative)

        with patch.object(Path, "exists", exists), patch.object(checker, "_read_bytes", read):
            with self.assertRaisesRegex(checker.ValidationError, "sourceTreeSha256"):
                checker.validate_source_root(SOURCE_ROOT)

    def test_edition_file_and_version_are_bound_to_current_publication(self):
        import json
        original_read = checker._read_bytes

        def read(root, relative):
            raw = original_read(root, relative)
            if relative == checker.EDITION_PATH:
                obj = json.loads(raw)
                obj["workshopVersion"] = "3.0.0"
                return json.dumps(obj).encode()
            return raw

        with patch.object(checker, "_read_bytes", read):
            with self.assertRaisesRegex(checker.ValidationError, "edition/version"):
                checker.validate_source_root(SOURCE_ROOT)

    def test_dangling_outer_manifest_symlink_never_falls_back(self):
        original_symlink = Path.is_symlink

        def is_symlink(path):
            return True if path == SOURCE_ROOT / checker.ARTIFACT_SET_PATH else original_symlink(path)

        with patch.object(Path, "is_symlink", is_symlink):
            with self.assertRaisesRegex(checker.ValidationError, "must not be a symlink"):
                checker.validate_source_root(SOURCE_ROOT)


if __name__ == "__main__":
    unittest.main()
