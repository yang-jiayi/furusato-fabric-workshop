"""Integrity boundaries for the explicit standalone current delivery route."""
from hashlib import sha256
from contextlib import redirect_stderr
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch
from lxml import html as html_parser

ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT/'tools/docs'),str(ROOT/'tools/html')]
import current_delivery as delivery
from furusato_html.preview30 import render
from furusato_docs import preview30_release as release
from furusato_docs.current_publication import CurrentPublication, publication_for_model
from furusato_docs.participant30_deployment import append_deployment_sections
from furusato_docs.participant30_text import PARAMETER_NOTES
from furusato_docs.lab import write_lab
from furusato_html.model import Section, Text


class CurrentDeliveryTests(unittest.TestCase):
    def test_current_author_route_matches_edition_and_maintenance_readme_stays_out_of_package(self):
        readme = (ROOT / "tools/docs/README.md").read_text(encoding="utf-8")
        self.assertIn("CURRENT_HTML_LAB.md", readme)
        self.assertIn("WORKSHOP_VERSION", readme)
        self.assertNotIn("docs/v3.0.0", readme)
        self.assertNotIn("docs/v3-preview", readme)
        self.assertIn("no Word or PDF", readme)
        files = delivery.approved_doc_files(
            ROOT, set(delivery.subprocess.check_output(
                ["git", "-C", str(ROOT), "ls-files", "-z"]).decode().split("\0")))
        self.assertNotIn("tools/docs/README.md", files)
        self.assertIn("tools/docs/CURRENT_HTML_LAB.md", files)

    def test_retired_word_guard_distinguishes_literal_source_vocabulary(self):
        self.assertFalse(delivery.retired_guide_reference(
            'It usually opens with a place-of-origin word such as a prefecture name.'))
        for value in ('Use Word or HTML', 'Read guide.DOCX', 'Open microsoft word',
                      'use the word document', 'download the word file'):
            with self.subTest(value=value):
                self.assertTrue(delivery.retired_guide_reference(value))

    def test_current_package_rejects_all_word_and_pdf_entries(self):
        self.assertEqual(0, delivery.validate_retired_document_inventory([
            'guide/current.html', 'attachments/business-requirements.txt']))
        for name in ('guide/legacy.docx', 'attachments/requirements.pdf',
                     'source/docs/assets/upstream/Microsoft_Terms_of_Use.PDF'):
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, 'retired document exports'):
                delivery.validate_retired_document_inventory(['guide/current.html', name])

    def test_current_source_binds_textual_icon_terms_without_pdf(self):
        manifest = delivery.current_source_manifest(ROOT)
        files = manifest['files']
        self.assertIn('docs/assets/architecture/upstream/NOTICE.txt', files)
        self.assertNotIn('docs/assets/architecture/upstream/Microsoft_Terms_of_Use.pdf', files)
        self.assertFalse(any(Path(name).suffix.lower() in {'.docx', '.pdf'} for name in files))
        icon_manifest = json.loads((ROOT / 'docs/assets/architecture/icon-manifest.json').read_text(encoding='utf-8'))
        for item in icon_manifest['licensingEvidence']:
            self.assertTrue((ROOT / 'docs/assets/architecture' / item['localPath']).is_file())
            self.assertNotEqual('.pdf', Path(item['localPath']).suffix.lower())
        notice = (ROOT / 'docs/assets/architecture/upstream/NOTICE.txt').read_text(encoding='utf-8')
        self.assertIn('Do not crop, flip, rotate or distort icons', ' '.join(notice.split()))
        self.assertIn('https://learn.microsoft.com/azure/architecture/icons/', notice)

    def test_exact_experimental_profile_inputs_are_bound_in_current_package(self):
        files=delivery.current_profile_files(ROOT)
        self.assertEqual(len(files),9)
        self.assertTrue(all(name.startswith(delivery.CURRENT_PROFILE_DIR+'/') for name in files))
        self.assertIn(delivery.CURRENT_PROFILE_DIR+'/global-instructions.txt',files)
        with tempfile.TemporaryDirectory() as temp:
            import shutil
            root=Path(temp)
            shutil.copytree(ROOT/delivery.CURRENT_PROFILE_DIR,root/delivery.CURRENT_PROFILE_DIR)
            (root/delivery.CURRENT_PROFILE_DIR/'global-instructions.txt').write_text('drift',encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'profile hash mismatch'):
                delivery.current_profile_files(root)

    def test_participant_checksums_and_notebook_help_follow_current_edition(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            scope = root / 'workshop/v3.0.0-preview/provisioning/scope.example.json'
            scope.parent.mkdir(parents=True)
            scope.write_bytes((ROOT / scope.relative_to(root)).read_bytes())
            for version in ('3.0.0', '3.1.0'):
                (root / 'WORKSHOP_VERSION').write_text(version, encoding='utf-8')
                section = Section('ch-24', 1, '24', Text('Deployment', 'Deployment'), chapter=24)
                append_deployment_sections(section, root)
                text = repr(section)
                self.assertIn(f'docs/v{version}/current', text)
                self.assertIn(CurrentPublication(version).package_name, text)
                self.assertNotIn('current-20261015.zip', text)
                self.assertIn('source/workshop/v3.0.0-preview', text)
                self.assertIn('API displayName (raw; value is between markers)', text)
                self.assertIn('unmodified API value set by the command', text)
                self.assertIn('Quoted JSON is an escaped representation, not the value to copy into scope.json', text)
                self.assertIn('inspect the API output and code units', text)
                self.assertIn('do not write if they differ', text)
                self.assertIn('PowerShell 7 (pwsh)', text)
                self.assertIn('winget install --exact --id Microsoft.PowerShell', text)
                self.assertIn('Microsoftの公式インストール手順', text)
                self.assertIn("Microsoft's official installation instructions", text)
        for description in PARAMETER_NOTES['NOTEBOOK_VERSION']:
            self.assertIn('NOTEBOOK_VERSION', description)
            self.assertNotIn('3.0.0', description)

    def test_current_filenames_follow_workshop_version_without_rewriting_word_profiles(self):
        version=(ROOT/'WORKSHOP_VERSION').read_text(encoding='utf-8').strip()
        self.assertEqual(delivery.PUBLICATION.version,version)
        self.assertEqual(delivery.HTML_NAME,'furusato-workshop-v'+version.replace('.','-')+'-complete.html')
        self.assertEqual(delivery.PACKAGE_NAME,'Furusato_Workshop_v'+version+'_current.zip')
        self.assertEqual(release.V300.version,'3.0.0')
        self.assertEqual(release.V300.html_name,'furusato-workshop-v3-0-0-complete.html')
        for invalid in ('3.1','../3.1.0','3.1.0/guide','3.1.0-preview'):
            with self.subTest(version=invalid),self.assertRaises(ValueError):
                CurrentPublication(invalid)

    def test_html_lab_hero_does_not_repeat_the_purpose_as_a_status(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / 'guide'
            delivery.build(ROOT, output)
            html = (output / delivery.HTML_NAME).read_text(encoding='utf-8')
        self.assertEqual(
            1,
            html.count('合成データを使い、Lakehouse・Eventhouse・Ontology・Data Agentを順に構築して確かめるハンズオン教材です。'),
        )
        self.assertNotIn('class="hero__status"', html)
        self.assertIn('Do not crop, flip, rotate or distort them', html)
        self.assertIn('https://learn.microsoft.com/azure/architecture/icons/', html)

    def test_every_table_has_one_horizontal_scroll_cue_before_its_scroller(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / 'guide'
            delivery.build(ROOT, output)
            tree = html_parser.fromstring((output / delivery.HTML_NAME).read_bytes())
        tables = tree.xpath(".//table")
        wrappers = tree.xpath(
            ".//div[contains(concat(' ', normalize-space(@class), ' '), ' table-wrap ')]"
        )
        self.assertEqual(len(tables), len(wrappers))
        for wrapper in wrappers:
            hints = wrapper.xpath(
                ".//p[contains(concat(' ', normalize-space(@class), ' '), ' table-hint ')]"
            )
            regions = wrapper.xpath(
                ".//div[contains(concat(' ', normalize-space(@class), ' '), ' table-scroll ')]"
            )
            caption = wrapper.xpath(".//caption")[0].text_content()
            with self.subTest(table=caption):
                self.assertEqual(1, len(hints))
                self.assertEqual(1, len(regions))
                self.assertIn('table-hint--top', hints[0].get('class', '').split())
                self.assertLess(list(wrapper).index(hints[0]), list(wrapper).index(regions[0]))
                hint_text = ''.join(hints[0].itertext())
                self.assertIn('横スクロールできる表', hint_text)
                self.assertIn('Horizontally scrollable table', hint_text)
        for ident, table_class in (
            ('ch-17-7', 'selection-contract'),
            ('appendix-b-1', 'notebook-parameters'),
        ):
            with self.subTest(section=ident):
                section = tree.get_element_by_id(ident)
                wrapper = section.xpath(
                    ".//div[contains(concat(' ', normalize-space(@class), ' '), ' table-wrap ')]"
                )[0]
                hints = wrapper.xpath(
                    ".//p[contains(concat(' ', normalize-space(@class), ' '), ' table-hint ')]"
                )
                hint = hints[0]
                region = wrapper.xpath(
                    ".//div[contains(concat(' ', normalize-space(@class), ' '), ' table-scroll ')]"
                )[0]
                table = region.xpath(".//table")[0]
                self.assertEqual(1, len(hints))
                self.assertIn('table-hint--top', hint.get('class', '').split())
                self.assertLess(list(wrapper).index(hint), list(wrapper).index(region))
                self.assertIn(table_class, table.get('class', '').split())
                self.assertEqual('0', region.get('tabindex'))
                self.assertEqual('region', region.get('role'))
                hint_text = ''.join(hint.itertext())
                self.assertIn('横スクロールできる表', hint_text)
                self.assertIn('Horizontally scrollable table', hint_text)
                if ident == 'ch-17-7':
                    source_table = next(
                        block for block in delivery.load_model(ROOT)[0].tables
                        if block['caption'].en == 'Actual flat selection contract'
                    )
                    source_description = next(
                        row[5].en for row in source_table['rows']
                        if 'PrefectureId,PrefectureName' in row[5].en
                    )
                    description = section.xpath(
                        ".//table/tbody/tr/td[5][contains(., 'PrefectureId,PrefectureName')]//span[@data-l='en']"
                    )[0]
                    self.assertEqual(source_description, description.text_content())
                    self.assertGreater(len(description.xpath(".//wbr")), 0)

    def test_figure28_labels_the_current_distributed_attachment_in_html_and_lab(self):
        model = delivery.load_model(ROOT)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            output = root / 'guide'
            delivery.build(ROOT, output)
            tree = html_parser.fromstring((output / delivery.HTML_NAME).read_bytes())
            figure = tree.get_element_by_id('figure-28')
            caption = ''.join(figure.xpath('./figcaption//text()'))
            alt = figure.xpath('.//img/@alt')[0]
            self.assertIn('business-requirements.pdf', caption)
            self.assertIn('attachments/business-requirements.txt', caption)
            self.assertIn('business-requirements.txt', alt)
            self.assertIn('ZIP', caption)

            lab = root / 'Lab'
            write_lab(ROOT, lab, model=model)
            pages = list(lab.rglob('*p30-15-attachment-grounding*.md'))
            self.assertEqual(1, len(pages))
            text = pages[0].read_text(encoding='utf-8')
            self.assertIn('business-requirements.pdf', text)
            self.assertIn('attachments/business-requirements.txt', text)
            self.assertIn('business-requirements.txt', text)

    def test_standalone_version_binding_is_independent_of_historical_word_approval(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            for version in ('3.0.0','3.1.0'):
                (root/'WORKSHOP_VERSION').write_text(version,encoding='utf-8')
                metadata={'version':version,'participantEdition':True,'deliveryMode':'html-lab',
                          'currentArtifactSet':{'workshopVersion':version}}
                self.assertEqual(publication_for_model(root,metadata,None,None).version,version)
                for word_sha,profile in ((None,release.V300),('b'*64,None)):
                    with self.subTest(version=version,profile=profile),self.assertRaises(ValueError):
                        publication_for_model(root,metadata,word_sha,profile)
                metadata['currentArtifactSet']['workshopVersion']='2.7.0'
                with self.assertRaises(ValueError):
                    publication_for_model(root,metadata,None,None)

    def test_explicit_browser_takes_priority_on_linux_and_windows(self):
        chromium=object()
        for platform in ('linux','win32'):
            with self.subTest(platform=platform),patch.object(delivery.sys,'platform',platform),patch.object(Path,'is_file',return_value=True):
                self.assertEqual(delivery.select_browser_executable(chromium,Path('custom-browser')),Path('custom-browser').resolve())

    def test_missing_explicit_browser_does_not_fall_back(self):
        with patch.object(Path,'is_file',return_value=False),self.assertRaisesRegex(FileNotFoundError,'existing file'):
            delivery.select_browser_executable(object(),Path('missing-browser'))

    def test_linux_prefers_existing_system_chromium(self):
        with patch.object(delivery.sys,'platform','linux'),patch.object(Path,'is_file',return_value=True):
            self.assertEqual(delivery.select_browser_executable(object()),Path('/usr/bin/chromium'))

    def test_playwright_chromium_fallback_on_windows_and_linux(self):
        installed=Path('playwright-chromium')
        chromium=Mock(executable_path=str(installed))
        for platform in ('linux','win32'):
            with self.subTest(platform=platform),patch.object(delivery.sys,'platform',platform),patch.object(Path,'is_file',autospec=True,side_effect=lambda path:path==installed):
                self.assertEqual(delivery.select_browser_executable(chromium),installed)

    def test_missing_playwright_browser_reports_dependency(self):
        with patch.object(delivery.sys,'platform','win32'),patch.object(Path,'is_file',return_value=False):
            with self.assertRaisesRegex(FileNotFoundError,'python -m playwright install chromium'):
                delivery.select_browser_executable(Mock(executable_path='missing-playwright-browser'))

    def test_browser_executable_argument_requires_browser_and_existing_file(self):
        cases=[
            ['validate','--out','.','--browser-executable',__file__],
            ['validate','--out','.','--browser','--browser-executable','.'],
            ['validate','--out','.','--browser','--browser-executable','missing-browser'],
            ['build','--out','.','--browser-executable',__file__],
            ['package','--out','.','--package','package.zip','--browser-executable',__file__],
        ]
        for argv in cases:
            with self.subTest(argv=argv),redirect_stderr(io.StringIO()),self.assertRaises(SystemExit) as error:
                delivery.parse_args(argv)
            self.assertEqual(error.exception.code,2)

    def test_browser_arguments_accept_explicit_and_default_selection(self):
        args=delivery.parse_args(['validate','--out','.','--browser','--browser-executable',__file__])
        self.assertTrue(args.browser)
        self.assertEqual(args.browser_executable,Path(__file__))
        args=delivery.parse_args(['validate','--out','.','--browser'])
        self.assertTrue(args.browser)
        self.assertIsNone(args.browser_executable)
        self.assertFalse(delivery.parse_args(['validate','--out','.']).browser)

    def test_paired_renderer_still_requires_original_release_binding(self):
        with self.assertRaises(ValueError):
            render(None,None,None,None,None,{'version':'3.0.0'},'a'*64,ROOT,release_profile=release.V300)

    def test_standalone_renderer_rejects_paired_digest_or_unbound_model(self):
        for metadata, word_sha in [
            ({'version':'3.0.0','participantEdition':True,'deliveryMode':'html-lab'},None),
            ({'version':'3.0.0','participantEdition':True,'deliveryMode':'html-lab','currentArtifactSet':{'sourceCommit':'a'*40}},'b'*64),
        ]:
            with self.subTest(metadata=metadata,word_sha=word_sha),self.assertRaises(ValueError):
                render(None,None,None,None,None,metadata,word_sha,ROOT,release_profile=release.V300,delivery_mode='html-lab')

    def test_packaging_requires_completed_browser_checks_on_exact_bytes(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/delivery.HTML_NAME
            path.write_text('first html')
            sha=sha256(path.read_bytes()).hexdigest()
            receipt={'schemaVersion':'furusato-current-html-lab-validation/v1','deliveryMode':'html-lab',
                     'static':{'passed':True,'htmlSha256':sha},'browser':{'passed':False,'htmlSha256':sha}}
            with self.assertRaises(ValueError):delivery.require_validated(path,receipt)
            receipt['browser']['passed']=True
            delivery.require_validated(path,receipt)
            path.write_text('modified html')
            with self.assertRaises(ValueError):delivery.require_validated(path,receipt)

    def test_unexpected_private_lab_files_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            (root/'README.md').write_text('Expected guide')
            delivery.checked_lab_files(root,{'README.md'})
            for name in ('.env','storage-state.json','extra.md'):
                path=root/name
                path.write_text('private test fixture')
                with self.subTest(name=name),self.assertRaises(ValueError):
                    delivery.checked_lab_files(root,{'README.md'})
                path.unlink()

    def test_unapproved_private_authoring_files_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            directory=root/'tools/docs';directory.mkdir(parents=True)
            (directory/'current_delivery.py').write_text('# known authoring source')
            self.assertEqual(delivery.approved_doc_files(root,set()),{'tools/docs/current_delivery.py'})
            for name in ('.env','storage-state.json','unreviewed-helper.py'):
                path=directory/name
                path.write_text('private test fixture')
                with self.subTest(name=name),self.assertRaises(ValueError):
                    delivery.approved_doc_files(root,set())
                path.unlink()

    def test_expected_lab_filename_cannot_hide_appended_private_content(self):
        with tempfile.TemporaryDirectory() as temp:
            lab=Path(temp);path=lab/'README.md';expected=b'Generated current index\n'
            path.write_bytes(expected)
            delivery.checked_lab_files(lab,{'README.md':expected})
            path.write_bytes(expected+b'PRIVATE TEST FIXTURE\n')
            with self.assertRaises(ValueError):delivery.checked_lab_files(lab,{'README.md':expected})

    def test_supplied_manifest_cannot_bypass_private_path_guard(self):
        for name in ('tools/docs/.env','tools/data-agent/private/answer.json',
                     'tools/docs/storage-state.json','workshop/attachments/manual.pdf',
                     'docs/manual.docx'):
            with self.subTest(name=name),self.assertRaises(ValueError):
                delivery.validate_source_manifest_paths(ROOT,{'files':{name:'0'*64}})

    def test_external_staged_lab_links_use_the_virtual_repository_layout(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/'repo';root.mkdir();(root/'workshop/v3.0.0-preview').mkdir(parents=True)
            lab=Path(temp)/'stage/Lab';lab.mkdir(parents=True)
            (lab/'README.md').write_text('[HTML](../docs/'+delivery.HTML_NAME+')\n[Source](../workshop/v3.0.0-preview)')
            source='workshop/v3.0.0-preview/notebook.txt'
            files={'source/'+source:b'test public source'}
            delivery.add_lab_aliases(files,root,lab,{source:'0'*64},b'validated html')
            self.assertEqual(files['docs/'+delivery.HTML_NAME],b'validated html')
            self.assertEqual(files[source],b'test public source')

    def test_bilingual_markdown_links_are_read_as_utf8(self):
        with tempfile.TemporaryDirectory() as temp:
            lab=Path(temp)
            page=lab/'README.md'
            page.write_text('[準備](../docs/guide.html)\n',encoding='utf-8')
            original=Path.read_text
            def explicit_utf8(path,*args,**kwargs):
                self.assertEqual(kwargs.get('encoding'),'utf-8')
                return original(path,*args,**kwargs)
            with patch.object(Path,'read_text',explicit_utf8):
                self.assertEqual(list(delivery.markdown_links(lab)),[(page,'../docs/guide.html')])

    def test_extracted_lab_links_must_resolve_inside_actual_package(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            lab=root/'Lab';lab.mkdir()
            (lab/'README.md').write_text('[Guide](../docs/guide.html)')
            with self.assertRaises(ValueError):delivery.validate_packaged_links(root)
            (root/'docs').mkdir();(root/'docs/guide.html').write_text('actual html')
            self.assertEqual(delivery.validate_packaged_links(root),1)


if __name__=='__main__':unittest.main()
