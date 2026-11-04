"""Integrity boundaries for the explicit standalone current delivery route."""
from hashlib import sha256
from contextlib import redirect_stderr
import io
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch
from urllib.parse import unquote, urlsplit
from lxml import html as html_parser

ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT/'tools/docs'),str(ROOT/'tools/html')]
import current_delivery as delivery
from furusato_html.preview30 import render
from furusato_docs import preview30_release as release
from furusato_docs.current_publication import CurrentPublication, publication_for_model
from furusato_docs import participant30_evaluation
from furusato_docs import participant30_figures as figure_source
from furusato_docs.participant30_deployment import append_deployment_sections
from furusato_docs.participant30_text import PARAMETER_NOTES
from furusato_docs.lab import write_lab
from furusato_html.model import Section, Text
from furusato_html.render import rich


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
            for version in (delivery.PUBLICATION.version,):
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
        for invalid in ('3.1','../3.1.0','3.1.0/guide','3.1.0-preview'):
            with self.subTest(version=invalid),self.assertRaises(ValueError):
                CurrentPublication(invalid)

    def test_current_guide_chapter17_numbers_are_contiguous(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / 'guide'
            delivery.build(ROOT, output)
            tree = html_parser.fromstring((output / delivery.HTML_NAME).read_bytes())
        section_ids = [
            element.get('id')
            for element in tree.xpath('//*[@id]')
            if re.fullmatch(r'ch-17-\d+', element.get('id', ''))
        ]
        self.assertEqual([f'ch-17-{number}' for number in range(1, 17)], section_ids)
        section_text = {
            ident: ' '.join(tree.xpath(f'//*[@id="{ident}"]')[0].itertext())
            for ident in ('ch-17-2', 'ch-17-3')
        }
        self.assertIn('17.2 Scope and prerequisites', section_text['ch-17-2'])
        self.assertIn('17.3 Steps', section_text['ch-17-3'])

    def test_current_support_and_architecture_links_resolve(self):
        source_paths = (
            ROOT / 'docs/public-onboarding/README.md',
            ROOT / 'docs/single-agent-workshop.md',
            ROOT / 'SECURITY.md',
            ROOT / 'docs/architecture/README.md',
            ROOT / 'docs/architecture/overview.ja.md',
            ROOT / 'docs/architecture/overview.en.md',
            ROOT / 'docs/architecture/sources.md',
        )
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / 'guide'
            delivery.build(ROOT, output)
            tree = html_parser.fromstring((output / delivery.HTML_NAME).read_bytes())
        guide_ids = set(tree.xpath('//*[@id]/@id'))
        for source in source_paths:
            markdown = source.read_text(encoding='utf-8')
            for target in re.findall(r'\[[^\]]+\]\(([^)]+)\)', markdown):
                parsed = urlsplit(target.strip())
                if parsed.scheme or parsed.netloc:
                    continue
                path = (source.parent / unquote(parsed.path)).resolve() if parsed.path else source.resolve()
                with self.subTest(source=source.relative_to(ROOT), target=target):
                    try:
                        path.relative_to(ROOT.resolve())
                    except ValueError:
                        self.fail('Local documentation link escapes the repository')
                    self.assertTrue(path.exists(), f'Missing linked path: {target}')
                    if parsed.fragment and path.name == delivery.HTML_NAME:
                        self.assertIn(parsed.fragment, guide_ids, f'Missing HTML fragment: {target}')

        ja_svg = (ROOT / 'Lab/assets/pc-01-architecture-ja.svg').read_text(encoding='utf-8')
        en_svg = (ROOT / 'Lab/assets/pc-01-architecture-en.svg').read_text(encoding='utf-8')
        self.assertIn('Semantic model', ja_svg)
        self.assertIn('DAX', ja_svg)
        self.assertIn('Semantic model', en_svg)
        self.assertIn('DAX', en_svg)
        for source in source_paths[2:]:
            content = source.read_text(encoding='utf-8')
            self.assertNotRegex(
                content,
                r'(?i)\bthree sources\b|\b3 sources\b|3 ソース|ネイティブ GQL',
            )
        security = (ROOT / 'SECURITY.md').read_text(encoding='utf-8')
        self.assertIn('84', security)
        self.assertIn('General', security)
        self.assertIn('Git-native', security)
        self.assertNotRegex(
            security,
            r'(?i)reviewed\s*v?3\.0\.0|v2\.7\.0|versioned public pairs|versioned copies|corresponding edition',
        )
        source_anchors = (ROOT / 'docs/architecture/sources.md').read_text(encoding='utf-8')
        for notebook in (
            'Notebook_01_Furusato_Prepare_Ontology_Data.ipynb',
            'Notebook_04_Furusato_Provision_Complete_Workshop.ipynb',
            'Notebook_05_Furusato_Analytics_Quality_and_BI.ipynb',
        ):
            self.assertIn(f'../../workshop/v3.0.0-preview/notebooks/{notebook}', source_anchors)
        self.assertNotRegex(
            source_anchors,
            r'workshop/v2\.7\.0/notebooks/Notebook_0[145]',
        )

    def test_chapter6_binding_crops_match_the_observed_route_and_keep_mapping_checks(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / 'guide'
            delivery.build(ROOT, output)
            tree = html_parser.fromstring((output / delivery.HTML_NAME).read_bytes())
        chapter = tree.get_element_by_id('ch-6')
        text = ' '.join(chapter.itertext())
        for phrase in (
            'Manage property bindings',
            'Bind data',
            'Data sources',
            'Properties',
            'Primary',
            'ot_municipality',
            'Source-column labels are truncated',
            'full names',
            'make no changes and ask the instructor',
            'close with Cancel',
            'stop without creating or saving and ask the instructor',
        ):
            self.assertIn(phrase, text)
        self.assertIn('Municipality Bind data: Properties view', text)

    def test_chapter19_practice_callout_does_not_print_markdown_emphasis(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / 'guide'
            delivery.build(ROOT, output)
            tree = html_parser.fromstring((output / delivery.HTML_NAME).read_bytes())
        chapter = tree.get_element_by_id('ch-19-2')
        callout = next(
            item for item in chapter.xpath(
                ".//aside[contains(concat(' ', normalize-space(@class), ' '), ' callout--note ')]"
            )
            if 'Test the ontology' in item.text_content()
        )
        text = ' '.join(callout.itertext())
        self.assertIn('Ontology agent の Test the ontology', text)
        self.assertIn('Questions from Test the ontology', text)
        self.assertNotIn('**Test the ontology**', text)

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
            ('ch-17-5', 'selection-contract'),
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
                self.assertEqual('0', region.get('tabindex'))
                self.assertEqual('region', region.get('role'))
                hint_text = ''.join(hint.itertext())
                self.assertIn('横スクロールできる表', hint_text)
                self.assertIn('Horizontally scrollable table', hint_text)
                if ident == 'ch-17-5':
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
                self.assertIn(table_class, table.get('class', '').split())

    def test_markdown_links_are_anchors_before_bare_url_autolinking(self):
        rendered = rich(
            "[Semantic model best practices](https://learn.microsoft.com/fabric/example) "
            "and [Add data sources to a Data Agent](https://learn.microsoft.com/fabric/agent)"
        )
        self.assertIn(
            '<a href="https://learn.microsoft.com/fabric/example" rel="noreferrer noopener">'
            'Semantic model best practices</a>',
            rendered,
        )
        self.assertIn(
            '<a href="https://learn.microsoft.com/fabric/agent" rel="noreferrer noopener">'
            'Add data sources to a Data Agent</a>',
            rendered,
        )
        self.assertNotIn("](<a href", rendered)
        self.assertNotRegex(rendered, r"\[[^\]]+\]\(https?://")

    def test_current_guide_visual_repairs_are_visible_and_keep_rubric_source_frozen(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / 'guide'
            delivery.build(ROOT, output)
            tree = html_parser.fromstring((output / delivery.HTML_NAME).read_bytes())
        visible = " ".join(tree.xpath("//text()[not(ancestor::code)]"))
        self.assertNotIn("](<a href", visible)
        self.assertNotRegex(visible, r"\[[^\]]+\]\(https?://")

        tuning = tree.get_element_by_id("ch-17-10")
        text = " ".join(tuning.itertext())
        for filename in (
            "definition/kusto.json",
            "definition/lakehouse_tables.json",
            "definition/ontology.json",
            "definition/semantic_model.json",
            "definition/stage_config.json",
        ):
            caption = f"ポータブル ステージ テンプレート: {filename}"
            caption_position = text.index(caption)
            next_caption = min(
                (position for position in (
                    text.find(f"ポータブル ステージ テンプレート: definition/{name}", caption_position + 1)
                    for name in (
                        "kusto.json", "lakehouse_tables.json", "ontology.json",
                        "semantic_model.json", "stage_config.json",
                    )
                ) if position >= 0),
                default=len(text),
            )
            label_node = tuning.xpath(
                ".//p[contains(., $filename)]",
                filename=filename,
            )[0]
            following_block = label_node.xpath(
                "following::div[contains(concat(' ',normalize-space(@class),' '),' codeblock ')][1]"
            )[0]
            self.assertLess(caption_position, next_caption)
            self.assertIn(filename, label_node.text_content())
            self.assertIn(filename, following_block.text_content())
            self.assertIn("JSON", following_block.text_content())
        self.assertIn("ポータブル ステージ テンプレート", text)
        global_section = tree.get_element_by_id("ch-17-6")
        self.assertIn("Agent 全体への指示", global_section.text_content())
        self.assertIn("高額寄附フラグ", tree.get_element_by_id("ch-17-14").text_content())
        self.assertNotIn("高額寄付フラグ", tree.get_element_by_id("ch-17-14").text_content())

        for prompt in tree.xpath("//div[contains(concat(' ',normalize-space(@class),' '),' codeblock--prompt ')]"):
            bar = prompt.xpath("./div[contains(@class,'codeblock__bar')]")
            self.assertEqual(1, len(bar))
            expected_label = "プロンプト" if prompt.get("data-l") == "ja" else "Prompt"
            self.assertIn(expected_label, bar[0].text_content())
            self.assertEqual(1, len(bar[0].xpath(".//button[@data-copy-target]")))

        for section_id, expected_heading in (
            ("appendix-e-2", "Microsoft Learn の参考資料"),
            ("appendix-e-3", "クレジットとアイコン利用条件"),
        ):
            section = tree.get_element_by_id(section_id)
            self.assertIn(expected_heading, section.xpath("./h3")[0].text_content())
        self.assertNotIn(
            "Microsoft Azure Public Service Icons",
            tree.get_element_by_id("appendix-e-1").text_content(),
        )
        self.assertIn(
            "Microsoft Azure Public Service Icons",
            tree.get_element_by_id("appendix-e-3").text_content(),
        )
        tables = tree.xpath(
            "//table[.//th[@scope='row' and contains(normalize-space(.), 'B14.fact')]]"
        )
        self.assertEqual(1, len(tables))
        japanese_criterion = tables[0].xpath(
            ".//th[@scope='row' and contains(normalize-space(.), 'B14.fact')]/following-sibling::td[1]"
        )[0].xpath(".//span[@data-l='ja']")[0].text_content()
        self.assertIn("1: 452025", japanese_criterion)
        self.assertIn("2: 272132", japanese_criterion)
        for rank, municipality_id in (
            (3, "012190"), (4, "442020"), (5, "462209"),
        ):
            self.assertIn(f"{rank}: {municipality_id}", japanese_criterion)
        self.assertNotIn("1 452025", japanese_criterion)
        suite = participant30_evaluation.public_suite(ROOT)
        original = next(
            condition["text"]
            for case in suite["regression"]["cases"] if case["id"] == "B14"
            for condition in case["conditions"] if condition["id"] == "B14.fact"
        )
        self.assertIn("1 452025", original)
        self.assertNotIn("1: 452025", original)

    def test_inline_cli_options_do_not_break_at_double_dash(self):
        self.assertEqual('<code class="cli-option">--check</code>', rich("`--check`"))

    def test_short_inline_tokens_get_bounded_no_wrap_class(self):
        self.assertEqual(
            '<code class="inline-token">452025-01</code>',
            rich("`452025-01`"),
        )
        self.assertEqual(
            '<code class="inline-token">寄附</code>',
            rich("`寄附`"),
        )
        self.assertEqual(
            '<code class="inline-token">COUNTROWS(&#x27;寄附&#x27;)</code>',
            rich("`COUNTROWS('寄附')`"),
        )
        self.assertEqual(
            '<code>workshop/very/long-reference-token-1234567890</code>',
            rich("`workshop/very/long-reference-token-1234567890`"),
        )

    def test_reviewed_identifiers_remain_atomic_inline_tokens(self):
        for token in (
            "452025-01",
            "2026-08-31T23:58:20Z",
            "apply-metadata",
            "COUNTROWS('寄附')",
            "data-dictionary.txt",
            "profile-manifest.json",
        ):
            with self.subTest(token=token):
                self.assertEqual(
                    f'<code class="inline-token">{token.replace(chr(39), "&#x27;")}</code>',
                    rich(f"`{token}`"),
                )
        css = (ROOT / "tools/html/assets/preview30.css").read_text(encoding="utf-8")
        self.assertIn("p code.inline-token, li code.inline-token", css)
        self.assertIn("white-space: nowrap", css)

    def test_lab_client_resources_have_a_localized_heading(self):
        model = delivery.load_model(ROOT)
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "Lab"
            write_lab(ROOT, output, model=model)
            pages = [path.read_text(encoding="utf-8") for path in output.rglob("*.md")]
        self.assertTrue(any("各クライアントの公式資料" in page for page in pages))
        self.assertTrue(any("Official documentation for each client" in page for page in pages))

    def test_attachment_grounding_figure_labels_the_current_distributed_attachment_in_html_and_lab(self):
        model = delivery.load_model(ROOT)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            output = root / 'guide'
            delivery.build(ROOT, output)
            tree = html_parser.fromstring((output / delivery.HTML_NAME).read_bytes())
            figure, = tree.xpath(
                '//figure[.//img[contains(@alt, "Agent conversation with a Plan/Act composer")]]'
            )
            caption = ''.join(figure.xpath('./figcaption//text()'))
            alt = figure.xpath('.//img/@alt')[0]
            self.assertIn('business-requirements.pdf', caption)
            self.assertIn('attachments/business-requirements.txt', caption)
            self.assertIn('business-requirements.pdf', alt)
            self.assertNotIn('current ZIP', caption)
            self.assertNotIn('current ZIP', alt)
            self.assertIn('use the distributed', caption)
            self.assertIn('Attachment-based agent-answer example', caption)
            self.assertIn('添付資料を使ったエージェントの回答例', caption)
            self.assertIn('Agent conversation with a Plan/Act composer', alt)
            self.assertTrue(figure_source.FIGURES['p30-16-gql']['caption'][0].endswith('。'))
            self.assertIn('Plan/Act composer を含むエージェントの会話画面', alt)
            self.assertNotIn('PDF-viewer', caption)
            self.assertNotIn('PDF ビューア', caption)
            self.assertNotIn('PDF-viewer', alt)
            self.assertNotIn('PDF ビューア', alt)

            lab = root / 'Lab'
            write_lab(ROOT, lab, model=model)
            pages = list(lab.rglob('*p30-15-attachment-grounding*.md'))
            self.assertEqual(1, len(pages))
            text = pages[0].read_text(encoding='utf-8')
            self.assertIn('business-requirements.pdf', text)
            self.assertIn('attachments/business-requirements.txt', text)
            self.assertIn('business-requirements.txt', text)

    def test_figure2_is_a_participant_preflight_example(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / 'guide'
            delivery.build(ROOT, output)
            tree = html_parser.fromstring((output / delivery.HTML_NAME).read_bytes())
            caption = ''.join(
                tree.get_element_by_id('figure-2').xpath('./figcaption//text()')
            )
            self.assertIn('F16', caption)
            self.assertIn('最低要件ではありません', caption)
            self.assertIn('Edit', caption)
            self.assertNotIn('2026-11-01', caption)
            self.assertNotIn('post-deployment evidence', caption)

    def test_figure9_describes_the_visible_003_example_and_001_action(self):
        model = delivery.load_model(ROOT)
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / 'guide'
            delivery.build(ROOT, output)
            tree = html_parser.fromstring((output / delivery.HTML_NAME).read_bytes())
            caption = ''.join(
                tree.get_element_by_id('figure-9').xpath('./figcaption//text()')
            )
            for phrase in ('3件の行', 'donation_events_003.csv', '自分が確認するファイルの行'):
                self.assertIn(phrase, caption)
            self.assertIn('Microsoft.Fabric.OneLake.FileCreated', caption)
            self.assertIn('PutBlob', caption)
            self.assertNotIn('期待状態ではありません', caption)

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
