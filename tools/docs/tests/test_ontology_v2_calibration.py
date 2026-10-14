"""Offline procedure rendering and publication-boundary checks; no AI results."""
from pathlib import Path
import hashlib
import json
import os
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import build_ontology_v2_calibration as calibration


class CalibrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=os.environ.get('EVALUATION_TEST_TEMP'))
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.root.chmod(0o700)
        self.source = self.root / 'procedure.md'
        self.source.write_text('# 校正手順 / Calibration and proofreading\n\n'
                               'これは手順です。[実結果](README.md)は別資料です。\n\n'
                               'This is a procedure. [Actual results](README.md) are separate.\n\n'
                               '## 記録 / Recording\n\n'
                               '1. 条件とソースを固定します。\n\n'
                               '1. Freeze conditions and sources.\n\n'
                               '| 確認 / Check | 根拠 / Evidence |\n|---|---|\n'
                               '| 実行 / Execution | 実結果 / Actual result |\n', encoding='utf-8')

    def build(self, output=None):
        return calibration.build(self.source, output or self.root / 'out', report_date='2026-10-15',
                                 source_date_epoch=1792022400, repo=calibration.REPO)

    def test_shared_markdown_renders_both_formats_and_public_links(self):
        value = self.build()
        self.assertTrue(value['markdownWordHtmlParity'])
        self.assertEqual(hashlib.sha256(self.source.read_bytes()).hexdigest(), value['sourceMarkdownSha256'])
        self.assertFalse(value['procedureIsEvaluationEvidence'])
        self.assertFalse(value['microsoftWordRenderChecked'])
        self.assertFalse(value['htmlBrowserChecked'])
        web = (self.root / 'out/calibration-and-proofreading.html').read_text()
        self.assertIn(value['outputs']['calibration-and-proofreading.docx'], web)
        self.assertIn('https://github.com/yang-jiayi/furusato-fabric-workshop/blob/main/docs/v3.0.0/tuning-20261015/README.md', web)
        with zipfile.ZipFile(self.root / 'out/calibration-and-proofreading.docx') as archive:
            self.assertIn(b'General', archive.read('docProps/custom.xml'))
            self.assertNotIn(b'fldChar', archive.read('word/document.xml'))
            self.assertNotIn(b'instrText', archive.read('word/document.xml'))
            self.assertNotIn(b'<Pages>', archive.read('docProps/app.xml'))
            relationships = archive.read('word/_rels/document.xml.rels').decode()
            self.assertNotIn(str(self.root), relationships)
            self.assertIn('https://github.com/', relationships)

    def test_existing_output_is_never_replaced(self):
        self.build()
        old = (self.root / 'out/calibration-and-proofreading.docx').read_bytes()
        with self.assertRaises(FileExistsError):
            self.build()
        self.assertEqual(old, (self.root / 'out/calibration-and-proofreading.docx').read_bytes())

    def test_private_source_and_unfinished_draft_are_rejected(self):
        for unsafe in ('/workspace/private', 'PRIVATE DRAFT — NOT PUBLISHABLE',
                       'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee', 'Bearer ' + 'x' * 45):
            with self.subTest(value=unsafe):
                self.source.write_text('# 校正 / Calibration and proofreading\n\n' + unsafe)
                with self.assertRaises(ValueError):
                    self.build()
                self.assertFalse((self.root / 'out').exists())

    def test_unsafe_link_targets_are_rejected(self):
        for target in ('javascript:alert(1)', 'file:///etc/passwd', '/private/data',
                       '../../../../../../secret', 'https://user:password@example.com', '//example.com'):
            with self.subTest(target=target):
                with self.assertRaises(ValueError):
                    calibration.link_target(target, calibration.DEFAULT_PUBLIC_SOURCE)

    def test_bad_table_shape_is_not_silently_dropped(self):
        self.source.write_text('# 校正 / Calibration and proofreading\n\n| a | b |\n|---|---|\n|one|two|three|\n')
        with self.assertRaises(ValueError):
            self.build()

    def test_public_checkout_output_is_rejected(self):
        output = calibration.REPO / 'docs/SHOULD-NOT-BE-CREATED-calibration-test'
        with self.assertRaises(ValueError):
            self.build(output)
        self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()
