"""Current participant validator entry points, not historical default datasets."""
from pathlib import Path
import json
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools/docs'))
import current_delivery as delivery


class CurrentValidationEntriesTests(unittest.TestCase):
    def test_source_inventory_includes_real_checker_and_dependency_bytes(self):
        baseline = json.loads((ROOT / 'docs/SOURCE_ARTIFACT_SET.json').read_bytes())
        with patch.object(delivery.v3_artifacts, 'snapshot', return_value=baseline):
            manifest = delivery.current_source_manifest(ROOT)
        delivery.validate_participant_validation_entries(manifest)
        for name in delivery.PARTICIPANT_VALIDATION_FILES:
            self.assertEqual(delivery.digest((ROOT / name).read_bytes()), manifest['files'][name])

    def test_required_validator_source_entries_fail_closed(self):
        names = delivery.PARTICIPANT_VALIDATION_FILES
        self.assertEqual(names, {
            'tools/data/Test-IncrementConsistency.ps1',
            'tools/provisioning/check_current_ontology.py',
        })
        delivery.validate_participant_validation_entries({'files': dict.fromkeys(names, 'a' * 64)})
        for missing in names:
            with self.subTest(missing=missing), self.assertRaisesRegex(ValueError, 'validation entries'):
                delivery.validate_participant_validation_entries({
                    'files': dict.fromkeys(names - {missing}, 'a' * 64)})

    def test_documented_commands_explicitly_target_current_runtime(self):
        text = (ROOT / 'tools/docs/furusato_docs/lab_clients.py').read_text(encoding='utf-8')
        self.assertIn('Test-IncrementConsistency.ps1 -DataRoot ./workshop/v3.0.0-preview/data', text)
        self.assertIn('check_current_ontology.py', text)
        self.assertNotIn('pwsh ./tools/ontology/Test-OntologyCardinality.ps1', text)


if __name__ == '__main__':
    unittest.main()
