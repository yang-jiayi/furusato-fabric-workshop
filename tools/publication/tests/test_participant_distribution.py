"""The active participant distribution is exhaustive current HTML plus Lab."""
from hashlib import sha256
import json
from pathlib import Path
import re
import unittest
import tempfile
from urllib.parse import unquote, urlsplit
import zipfile

ROOT=Path(__file__).resolve().parents[3]
HTML='furusato-workshop-v3-1-0-complete.html'
PACKAGE='Furusato_Workshop_v3.1.0_current.zip'


class ParticipantDistributionTests(unittest.TestCase):
    def test_active_entrypoints_offer_only_current_guides(self):
        japanese_readme=(ROOT/'README.md').read_text(encoding='utf-8')
        self.assertIn('[日英HTML手順書をダウンロード](docs/furusato-workshop-v3-1-0-complete.html?raw=true)して',japanese_readme)
        self.assertNotIn('**[日英HTML手順書をダウンロード]',japanese_readme)
        for relative in ('README.md','docs/README.md','docs/v3.1.0/current/README.md'):
            with self.subTest(path=relative):
                text=(ROOT/relative).read_text(encoding='utf-8')
                self.assertIn('Lab',text)
                self.assertIn(HTML,text)
                self.assertIn(PACKAGE,text)
                self.assertNotRegex(text,r'\]\([^)]*\.docx(?:[)#]|$)')
                self.assertNotRegex(text,r'189/281|217/281|2026-09-17|参考実績|Historical evaluations')

    def test_current_html_and_checksums_match_distribution_bytes(self):
        versioned=ROOT/'docs/v3.1.0/current'
        self.assertEqual((ROOT/'docs'/HTML).read_bytes(),(versioned/'guide'/HTML).read_bytes())
        self.assertEqual((ROOT/'docs'/PACKAGE).read_bytes(),(versioned/PACKAGE).read_bytes())
        for name in ('DOCUMENT_VALIDATION.json','LAB_VALIDATION.json'):
            self.assertEqual((ROOT/'docs'/name).read_bytes(),(versioned/name).read_bytes())
        with zipfile.ZipFile(ROOT/'docs'/PACKAGE) as archive:
            self.assertEqual((versioned/'artifact-set.json').read_bytes(),
                             archive.read('source/artifact-set.json'))
        for relative in ('docs/SHA256SUMS.txt','docs/v3.1.0/current/SHA256SUMS.txt'):
            path=ROOT/relative
            entries={}
            for line in path.read_text(encoding='utf-8').splitlines():
                digest,name=line.split('  ',1)
                self.assertNotIn(name,entries)
                entries[name]=digest
                self.assertNotIn('.docx',name.lower())
                self.assertEqual(digest,sha256((path.parent/name).read_bytes()).hexdigest(),name)
            self.assertTrue(any(name.endswith(HTML) for name in entries))
            self.assertTrue(any(name.endswith(PACKAGE) for name in entries))

    def test_current_package_is_complete_and_contains_no_retired_guide_or_reports(self):
        with zipfile.ZipFile(ROOT/'docs'/PACKAGE) as archive:
            self.assertIsNone(archive.testzip())
            names=archive.namelist()
            self.assertEqual(len(names),len(set(names)))
            self.assertFalse(any(name.lower().endswith('.docx') for name in names))
            self.assertFalse(any(name.lower().endswith('.pdf') for name in names))
            self.assertFalse(any(name.startswith(('reports/', 'source/docs/v3.0.0/',
                                                  'source/docs/v3-preview/',
                                                  'source/docs/assets/v2.7.0/',
                                                  'source/docs/assets/v3.0.0-',
                                                  'source/docs/assets/v3-preview-'))
                                 for name in names))
            for name in ('Lab/README.md','guide/'+HTML,'source/artifact-set.json','START_HERE.txt','DOCUMENT_VALIDATION.json','LAB_VALIDATION.json'):
                self.assertIn(name,names)
            for path in (ROOT/'Lab').rglob('*'):
                if path.is_file():
                    self.assertEqual(path.read_bytes(),archive.read('Lab/'+path.relative_to(ROOT/'Lab').as_posix()))
            self.assertEqual((ROOT/'docs'/HTML).read_bytes(),archive.read('guide/'+HTML))
            self.assertEqual(archive.read('docs/'+HTML),archive.read('guide/'+HTML))
            receipt=json.loads(archive.read('DOCUMENT_VALIDATION.json'))
            self.assertTrue(receipt['static']['passed'])
            self.assertTrue(receipt['browser']['passed'])
            lab_receipt=json.loads(archive.read('LAB_VALIDATION.json'))
            self.assertEqual(receipt['static']['modelBlocks'],640)
            self.assertEqual(receipt['static']['modelBlocks'],lab_receipt['sourceBlocksChecked'])
            self.assertEqual(receipt['static']['htmlSha256'],sha256(archive.read('guide/'+HTML)).hexdigest())
            manifest=json.loads(archive.read('PACKAGE_MANIFEST.json'))
            self.assertEqual(manifest['deliveryMode'],'html-lab')
            for name,expected in manifest['files'].items():
                self.assertEqual(expected,sha256(archive.read(name)).hexdigest(),name)
            with tempfile.TemporaryDirectory() as temp:
                archive.extractall(temp)
                extracted=Path(temp).resolve()
                checked=0
                for page in (extracted/'Lab').rglob('*.md'):
                    for target in re.findall(r'\[[^\]\n]*\]\(([^)\s]+)\)',
                                             page.read_text(encoding='utf-8')):
                        parsed=urlsplit(target)
                        if parsed.scheme or not parsed.path:continue
                        destination=(page.parent/unquote(parsed.path)).resolve()
                        self.assertTrue(destination.is_relative_to(extracted))
                        self.assertTrue(destination.exists(),str(page)+' -> '+target)
                        checked+=1
                self.assertGreaterEqual(checked,655)

    def test_packaged_source_inventory_preserves_the_real_protected_baseline(self):
        with zipfile.ZipFile(ROOT/'docs'/PACKAGE) as archive:
            manifest=json.loads(archive.read('source/artifact-set.json'))
            from lxml import html
            tree=html.fromstring(archive.read('guide/'+HTML))
            provenance=json.loads(tree.get_element_by_id('preview30-provenance').text)
            self.assertEqual(provenance['currentArtifactSet']['manifestSha256'],sha256(archive.read('source/artifact-set.json')).hexdigest())
            self.assertEqual(provenance['currentArtifactSet']['sourceTreeSha256'],manifest['sourceTreeSha256'])
            for name,expected in manifest['files'].items():
                self.assertEqual(expected,sha256(archive.read('source/'+name)).hexdigest(),name)
            for name,expected in manifest['baselineProtection']['files'].items():
                self.assertEqual(expected,sha256(archive.read('source/'+name)).hexdigest(),name)
            self.assertEqual(manifest['dataChecks']['staticDonationRows'],80000)
            self.assertEqual(manifest['dataChecks']['staticDonationYen'],1344099000)
            self.assertEqual(manifest['documentationBinding']['deliveryMode'],'html-lab')

    def test_current_local_markdown_links_resolve(self):
        paths=[ROOT/'README.md',ROOT/'docs/README.md',ROOT/'docs/v3.1.0/current/README.md']
        paths.extend((ROOT/'Lab').rglob('*.md'))
        for path in paths:
            for target in re.findall(r'\[[^\]\n]*\]\(([^)\s]+)\)',
                                     path.read_text(encoding='utf-8')):
                parsed=urlsplit(target)
                if parsed.scheme or not parsed.path:continue
                with self.subTest(path=path.relative_to(ROOT),target=target):
                    self.assertTrue((path.parent/unquote(parsed.path)).resolve().exists())

    def test_runtime_and_historical_classification_assets_remain_available(self):
        for relative in ('SECURITY.md','LICENSE','workshop/v2.7.0/data/DATASET.md',
                         'workshop/v2.7.0/notebooks/Notebook_04_Furusato_Provision_Complete_Workshop.ipynb',
                         'tools/docs/assets/style-carrier.zip'):
            self.assertTrue((ROOT/relative).is_file(),relative)


if __name__=='__main__':unittest.main()
