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
        self.assertIn('This check requires PowerShell 7 (pwsh)', text)
        self.assertIn('この検査には PowerShell 7（pwsh）が必要です', text)
        self.assertIn('installing-powershell-on-linux', text)
        self.assertNotIn('pwsh ./tools/ontology/Test-OntologyCardinality.ps1', text)
        self.assertIn('build_preview30.py', text)
        self.assertNotIn('legacy', text.lower())
        self.assertNotIn('reseal_runtime.py --check', text)
        self.assertIn('The data check explicitly selects the current data path', text)
        self.assertIn('Current byte-for-byte regeneration is not qualified', text)
        self.assertIn('SHA-256 inventories of all files before and after generation', text)
        self.assertIn('before.json', text)
        self.assertIn('after.json', text)
        self.assertIn('Private check evidence: ', text)
        self.assertIn('this alone does not guarantee byte identity', text)
        self.assertIn('The extracted copy has no .git directory', text)
        self.assertIn('$Dirty = git status --porcelain', text)
        self.assertEqual(text.count('git status --porcelain'), 1)
        self.assertIn('git rev-parse --absolute-git-dir', text)
        self.assertIn('$env:GIT_WORK_TREE = $Source', text)
        self.assertIn('$env:GIT_DIR = $GitDir', text)
        self.assertNotIn('GetTempPath()', text)
        self.assertNotIn('At reviewed commit ', text)
        self.assertLess(text.index('$Dirty = git status --porcelain'), text.index('git archive --format=zip'))
        self.assertLess(text.index('python -c $Inventory $Source $BeforeInventory'),
                        text.index('Push-Location -LiteralPath $Source'))
        self.assertIn('python -c $Inventory $Source $AfterInventory', text)
        self.assertIn('python -c $Compare $BeforeInventory $AfterInventory', text)
        self.assertNotIn('$Changes = git status --porcelain', text)
        self.assertNotIn('python -B ./tools/provisioning/reseal_runtime.py --check', text)


if __name__ == '__main__':
    unittest.main()
