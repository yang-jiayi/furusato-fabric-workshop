"""Source-only regression tests for participant vector and screenshot supplements."""

import hashlib
import copy
import io
import sys
import unittest
import tempfile
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import patch

from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "tools" / "docs"), str(ROOT / "tools" / "html")]

from furusato_docs import participant30_details as details
from furusato_docs.participant30 import FigureFactory, figure_path
from furusato_docs import participant30_figures as figures
from furusato_docs import participant30_text as participant_text
from furusato_html.diagrams import _bold, _owner, _shapes, _width, load_map, parse_lines, residual_japanese
from furusato_html.assets import AssetLibrary
from furusato_html.assets import sanitize_svg
from furusato_html.model import Text
from furusato_html.render import render_figure
from furusato_docs import lab


class ParticipantDetailSourceTests(unittest.TestCase):
    def test_appendix_graph_eligibility_uses_current_binding_not_creation_provenance(self):
        row = next(row for row in participant_text.APPENDICES["E"]["troubleshooting"]
                   if row[0][1] == "Graph shows Ineligible")
        japanese, english = row[1]
        self.assertIn("現在 Semantic model に binding", japanese)
        self.assertIn("現在のバインドと実際のソース", japanese)
        self.assertNotIn("Semantic model から作った", japanese)
        self.assertIn("currently bound to semantic models", english)
        self.assertIn("Delta tables in Lakehouses or mirrored databases", english)
        self.assertIn("multiple backing tables", english)
        self.assertIn("Do not infer the reason from creation provenance", english)
        self.assertIn("stop materialization", english)
        self.assertNotIn("entities generated from", english)

    def test_bilingual_event_example_does_not_change_the_001_only_sequence(self):
        steps = participant_text.CHAPTERS[9]["steps"]
        upload = next(step["text"][0] for step in steps
                      if "002 と 003 はまだ置きません" in step["text"][0])
        self.assertIn("001.csv を1回だけ", upload)
        observation = next(step["text"][0] for step in steps
                           if "p30-09-source-events" in step.get("figures", []))
        caption = figures.FIGURES["p30-09-source-events"]["caption"][0]
        self.assertIn("3件の行", caption)
        self.assertIn("donation_events_003.csv", caption)
        self.assertIn("自分が確認するファイルの行", caption)
        self.assertIn("001.csv の FileCreated 行", observation)
        self.assertIn("donation_events_003.csv を選択した画面例", observation)
        self.assertIn("自分の001の行", observation)
        self.assertIn("再アップロードせずに停止", observation)
        self.assertNotIn("最大3行", observation)
        observation_en = next(step["text"][1] for step in steps
                              if "p30-09-source-events" in step.get("figures", []))
        caption_en = figures.FIGURES["p30-09-source-events"]["caption"][1]
        self.assertIn("three rows", caption_en)
        self.assertIn("donation_events_003.csv selected", caption_en)
        self.assertIn("the file you are checking", caption_en)
        self.assertIn("FileCreated row for /Files/increment/donation_events_001.csv", observation_en)
        self.assertIn("three rows with donation_events_003.csv selected", observation_en)
        self.assertIn("your own 001 row", observation_en)
        self.assertIn("stop without re-uploading", observation_en)
        self.assertNotIn("may show up to", observation_en)
        manifest = json.loads(
            (ROOT / "docs/assets/current-participant/manifest.json").read_text(encoding="utf-8")
        )
        entry = next(item for item in manifest["figures"] if item["id"] == "p30-09-source-events")
        self.assertEqual(
            ["件数・時刻・イベント ID", "Subject・イベント種別・API", "ファイルサイズ・形式"],
            entry["annotations"]["labels"],
        )
        self.assertEqual(
            entry["sha256"],
            hashlib.sha256(figure_path("p30-09-source-events").read_bytes()).hexdigest(),
        )
        self.assertIn("editorial footer removed", entry["pixelEdits"][0])
        self.assertIn("Event table pixels unchanged", entry["pixelEdits"][0])
        with Image.open(figure_path("p30-09-source-events")) as image:
            self.assertEqual((1200, 940), image.size)

    def test_existing_relationships_are_inspect_only_in_both_languages(self):
        chapter = participant_text.CHAPTERS[7]
        self.assertIn("読み取りだけ", chapter["intro"][0][0])
        self.assertIn("without editing", chapter["intro"][0][1])
        self.assertIn("配置済みなら", chapter["steps"][0]["text"][0])
        self.assertIn("do not use Add relationship, Create or Save", chapter["steps"][0]["text"][1])
        self.assertIn("不足", chapter["steps"][4]["text"][0])
        self.assertIn("create only missing", chapter["steps"][4]["text"][1])
        self.assertIn("do not edit settings merely", chapter["steps"][3]["text"][1])

    def test_manual_parameter_guidance_does_not_infer_placeholder_semantics(self):
        spec = figures.FIGURES["p30-09-manual-recovery"]
        self.assertIn("文字列 Value", spec["caption"][0])
        self.assertIn("literal string Value", spec["caption"][1])
        self.assertIn("genuinely empty", spec["caption"][1])
        self.assertNotIn("placeholder", str(spec).lower())
        self.assertIn("visible text Value", spec["alt"][1])
        self.assertIn("independently ensure", spec["alt"][1])

    def test_apply_output_is_an_illustration_not_a_participant_run_claim(self):
        for ident in ("p30-11-executed-output", "p30-11-executed-output-detail"):
            spec = figures.FIGURES[ident]
            self.assertIn("出力例", spec["caption"][0])
            self.assertIn("example", spec["caption"][1])
            for history in ("retained screenshot", "fresh run", "historical", "既存", "保存済み"):
                self.assertNotIn(history, str(spec))
        applied = figures.FIGURES["p30-11-executed-output"]["caption"]
        self.assertIn("自分の実行では、最新のジョブと出力を確認", applied[0])
        self.assertIn("For your run, check the latest job and its output", applied[1])
        gold = figures.FIGURES["p30-11-gold"]["caption"]
        self.assertIn("自分の Notebook 05 の最新実行ジョブと出力", gold[0])
        self.assertIn("check their own latest Notebook 05 job and output", gold[1])
        monitor = figures.FIGURES["p30-11-notebook05-monitor-success"]["caption"]
        self.assertIn("Gold の件数・金額・generation 整合性", monitor[0])
        self.assertIn("OneLake の独立検証", monitor[0])
        self.assertIn("proves only the notebook run completed", monitor[1])
        self.assertIn("verify Gold counts, amounts and generation consistency independently", monitor[1])
        preview = figures.FIGURES["p30-11-schema-preview"]["caption"]
        for value in preview:
            self.assertIn("gold.donations", value)
            self.assertIn("1,000", value)
        self.assertIn("全件数・合計金額ではなく", preview[0])
        self.assertIn("not the full row count or total amount", preview[1])
        self.assertIn("SQL analytics endpoint", preview[1])

    def test_proposal_crop_does_not_claim_a_mode_and_procedure_rechecks_plan(self):
        spec = details.DETAILS["p30-15-noattachment-preview"]
        self.assertTrue(spec["primary"])
        self.assertEqual((1084, 120, 1354, 744), spec["crop"])
        caption = figures.FIGURES["p30-15-noattachment-preview"]["caption"]
        self.assertIn("outside the crop", caption[1])
        self.assertIn("select and verify Plan", caption[1])
        self.assertIn("do not apply proposals", caption[1])
        steps = participant_text.CHAPTERS[15]["steps"]
        self.assertIn("Before prompting, select Plan", steps[0]["text"][1])
        self.assertIn("button colors", steps[0]["text"][1])
        self.assertIn("select and recheck Plan", steps[3]["text"][1])

    def test_main_ontology_proposal_rejects_mismatched_response_counts_and_identities(self):
        contract = json.loads((ROOT / "workshop/v3.0.0-preview/ontology/generation2-contract.json").read_bytes())
        self.assertEqual(10, len(contract["entities"]))
        self.assertEqual(15, len(contract["relationships"]))
        self.assertNotIn("AdministrativeArea", [entity["name"] for entity in contract["entities"]])
        self.assertNotIn("DonationQualityScope", [entity["name"] for entity in contract["entities"]])
        chapter = participant_text.CHAPTERS[15]
        self.assertIn("actual main ontology definition", chapter["before"][0][1])
        validation = chapter["steps"][2]["text"][1]
        self.assertIn("eleven entities and fifteen relationships", validation)
        self.assertIn("every existing ID, type, relationship endpoint/direction", validation)
        self.assertIn("record contradictory assertions as FAIL", validation)
        self.assertIn("an unavailable proposed definition as unverified", validation)
        self.assertIn("An incorrect A answer alone does not prohibit safe comparison B", validation)
        b_entry = chapter["steps"][3]["text"]
        self.assertIn("Aが FAIL・未確認でも", b_entry[0])
        self.assertIn("基準が不正・取得不能・変更済み", b_entry[0])
        self.assertIn("Even if A is FAIL or unverified", b_entry[1])
        self.assertIn("Re-read the authoritative actual main ontology definition", b_entry[1])
        self.assertIn("actual baseline is wrong, unavailable or changed", b_entry[1])
        self.assertIn("Plan/no-write safety cannot be confirmed", b_entry[1])
        self.assertIn("select and recheck Plan", b_entry[1])
        self.assertIn("send exactly the same request as in A", b_entry[1])
        self.assertIn("Do not apply or save", b_entry[1])
        self.assertIn("independently of A's outcome", chapter["steps"][5]["text"][1])
        self.assertNotIn("A passes definition comparison", chapter["steps"][5]["text"][1])
        caption = figures.FIGURES["p30-15-noattachment-preview"]["caption"]
        for value in caption:
            self.assertIn("Entity types 3", value)
            self.assertIn("Relationship types 0", value)
            self.assertIn("AdministrativeArea", value)
        self.assertIn("Rejected/mismatched", caption[1])
        self.assertIn("not an expected or passing result", caption[1])
        self.assertIn("15 Relationship", caption[0])
        for ident in ("p30-15-attachment-grounding", "p30-15-attachment-response-bottom",
                      "p30-15-preview"):
            self.assertIn("fifteen", figures.FIGURES[ident]["caption"][1])
            if ident == "p30-15-attachment-grounding":
                self.assertIn(
                    "This does not establish preservation of the main ontology",
                    figures.FIGURES[ident]["caption"][1],
                )
                self.assertIn("stop on a mismatch", figures.FIGURES[ident]["caption"][1])
                self.assertIn("displayed attachment filename", figures.FIGURES[ident]["alt"][1])
            else:
                self.assertTrue(
                    "不一致" in figures.FIGURES[ident]["alt"][0]
                    or "一致しません" in figures.FIGURES[ident]["alt"][0]
                )
                self.assertIn("mismatched", figures.FIGURES[ident]["alt"][1].lower())
        self.assertIn("not a passing result", figures.FIGURES[
            "p30-15-attachment-response-bottom"]["caption"][1])
        self.assertIn("not a passing example", figures.FIGURES[
            "p30-15-preview"]["caption"][1])
        self.assertIn("通知が回答欄の上部に重なり", figures.FIGURES[
            "p30-15-preview"]["caption"][0])
        self.assertIn("feedback notification overlaps the upper part of the answer pane",
                      figures.FIGURES["p30-15-preview"]["caption"][1])
        self.assertIn("一部が重なったり省略されたり", figures.FIGURES["p30-16-gql"]["caption"][0])
        self.assertIn("some overlapping or ellipsized", figures.FIGURES["p30-16-gql"]["caption"][1])
        self.assertIn("Table view（表形式）で照合してください", figures.FIGURES["p30-16-gql"]["caption"][0])
        self.assertIn("Verify names and IDs in Table view", figures.FIGURES["p30-16-gql"]["caption"][1])

    def test_authentic_detail_recipes_are_exact_contiguous_pixel_crops(self):
        for ident, spec in details.DETAILS.items():
            with self.subTest(ident=ident):
                source_path = details.detail_source_path(ident)
                self.assertTrue(source_path.is_relative_to(ROOT / 'docs' / 'assets'))
                source_bytes = source_path.read_bytes()
                self.assertEqual(spec["sha256"], hashlib.sha256(source_bytes).hexdigest())
                left, top, right, bottom = spec["crop"]
                with Image.open(io.BytesIO(source_bytes)) as source:
                    self.assertEqual(spec["size"], source.size)
                    expected = source.crop(spec["crop"])
                self.assertLessEqual(0, left)
                self.assertLessEqual(0, top)
                self.assertLess(right, spec["size"][0] + 1)
                self.assertLess(bottom, spec["size"][1] + 1)

                with Image.open(io.BytesIO(details.crop_png(ident))) as actual:
                    self.assertEqual(expected.size, actual.size)
                    self.assertEqual(expected.tobytes(), actual.tobytes())

                self.assertTrue(spec["purpose"])
                self.assertTrue(spec["limitations"])
                self.assertTrue(all(figures.FIGURES[ident][field] for field in ("caption", "alt")))

    def test_copy_output_detail_crop_stops_at_the_redacted_run_details_boundary(self):
        ident = "p30-09-copy-002-output-detail"
        spec = details.DETAILS[ident]
        self.assertEqual((671, 416, 1118, 690), spec["crop"])
        source = details.detail_source_path(ident)
        with Image.open(source) as image:
            self.assertEqual((0, 0, 0), image.convert("RGB").getpixel((1123, 530)))
            self.assertLess(spec["crop"][2], 1123)
        self.assertIn(ident, details.SUPPRESSED_PARTICIPANT_DETAILS)
        self.assertFalse((ROOT / "Lab" / "assets" / "p30-09-copy-002-output-detail.png").exists())

    def test_activation001_crop_has_exact_retained_source_provenance(self):
        ident = "p30-09-activation-detail-001"
        spec = details.DETAILS[ident]
        self.assertEqual("activator-001-row-parameters-crop.png", spec["sourceAsset"])
        self.assertEqual((737, 72), spec["size"])
        self.assertEqual((0, 0, 737, 72), spec["crop"])
        self.assertIn("activator-001-history-20261102-r1-right.jpg", spec["limitations"])
        self.assertIn(
            "056b5081e1b9fcefebb388550ee8bca3f3e573dd889150e12afbb44a8e116acd",
            spec["limitations"],
        )
        self.assertIn(
            "688,560-1425,632",
            spec["limitations"],
        )
        self.assertIn("no stitching or reconstruction", spec["limitations"])
        self.assertIn("de208a3a9e07b61ce7a599c184a5e560a7279396b4c6acabae79984c2a931dcd",
                      spec["limitations"])
        self.assertIn("2f6a80987067c421b3635a39925d79bec4ddfe129e65dfb75de910de8a03bbb6",
                      spec["limitations"])
        source = details.detail_source_path(ident)
        lab_asset = ROOT / "Lab" / "assets" / "p30-09-activation-detail-001.png"
        self.assertEqual(
            "23620fa8ec92d732e23d9f2ad757c4df35236fb5e068338f64644b706f6b4fd6",
            hashlib.sha256(source.read_bytes()).hexdigest(),
        )
        with Image.open(source) as source_image, Image.open(lab_asset) as lab_image:
            self.assertEqual(source_image.size, lab_image.size)
            self.assertEqual(source_image.convert("RGBA").tobytes(), lab_image.convert("RGBA").tobytes())

    def test_architecture_has_current_bilingual_vector_panels_at_a4_scale(self):
        source_path = details.architecture_svg_path()
        source = source_path.read_text(encoding="utf-8")
        japanese, english = details.architecture_svg_variants(load_map())
        self.assertEqual(details.ARCHITECTURE_SHA256, hashlib.sha256(source.encode("utf-8")).hexdigest())
        self.assertEqual([], residual_japanese(english))
        self.assertNotIn("3.0.0", source)
        self.assertNotIn("3.0.0", english)
        self.assertIn("Static data", english)
        self.assertIn("静的データ", japanese)
        self.assertIn("94,900", japanese)
        self.assertIn("94,900", english)
        self.assertIn("253,886,000", japanese)
        self.assertIn("253,886,000", english)
        self.assertIn("14,900", japanese)
        self.assertIn("14,900", english)
        self.assertIn("native bindings", english)
        self.assertIn("Graph materialization", english)

        root = ET.fromstring(source)
        view_box = [float(value) for value in root.attrib["viewBox"].split()]
        self.assertEqual(1600, view_box[2])
        a4_painted_width_points = 500.25
        detail_points = 30 * a4_painted_width_points / view_box[2]
        self.assertGreaterEqual(detail_points, 9)
        for artwork in (japanese, english):
            detail_sizes = [
                line.size for line in parse_lines(artwork)
                if 'class="detail"' in line.attrs
            ]
            self.assertTrue(detail_sizes)
            self.assertGreaterEqual(min(detail_sizes) * a4_painted_width_points / view_box[2], 9)

        translations = load_map()
        shapes = _shapes(source)
        for line in parse_lines(source):
            translated = translations.get(line.text, line.text)
            owner = _owner(line, shapes)
            if owner is None:
                continue
            padding = 4 if owner.backplate else min(12, max(4, line.x - owner.x))
            available = owner.x + owner.width - padding - line.x
            self.assertLessEqual(_width(translated, line.size, _bold(line)), available, line.text)

        self.assertEqual(
            "adcede5b0d4dd1d0f9069b3c252e7ca3066e0d3e87bb1ec45f1777710dd57daa",
            hashlib.sha256(figure_path("pc-01-architecture").read_bytes()).hexdigest(),
        )

    def test_architecture_lane_contains_boxes_and_clears_bilingual_footnotes(self):
        japanese, english = details.architecture_svg_variants(load_map())
        for language, artwork in (("ja", japanese), ("en", english)):
            with self.subTest(language=language):
                root = ET.fromstring(artwork)
                lane = next(
                    node for node in root.iter(f"{{{details.SVG_NAMESPACE}}}rect")
                    if node.get("class") == "lane" and node.get("y") == "1015"
                )
                lane_bottom = float(lane.get("y")) + float(lane.get("height")) + 80
                lower_boxes = [
                    node for node in root.iter(f"{{{details.SVG_NAMESPACE}}}rect")
                    if node.get("class") in {"box", "box-data", "box-ai"}
                    and float(node.get("y")) >= float(lane.get("y"))
                ]
                self.assertTrue(lower_boxes)
                for box in lower_boxes:
                    box_bottom = float(box.get("y")) + float(box.get("height")) + 80
                    self.assertLess(box_bottom + 1.5, lane_bottom, box.attrib)

                notes = [
                    node for node in root.iter(f"{{{details.SVG_NAMESPACE}}}text")
                    if node.get("class") == "detail" and node.get("y") in {"1635", "1670"}
                ]
                self.assertEqual(2, len(notes))
                for note in notes:
                    baseline = float(note.get("y")) + 80
                    font_size = float(note.get("font-size"))
                    self.assertGreaterEqual(baseline - font_size - lane_bottom, 10, note.text)
                    self.assertGreater(
                        float(root.get("viewBox").split()[3]) - baseline - font_size * 0.25,
                        10,
                        note.text,
                    )

    def test_existing_figures_keep_full_images_and_add_only_the_approved_details(self):
        for parent, child_ids in details.DETAILS_BY_PARENT.items():
            with self.subTest(parent=parent):
                evidence = {"captures": {parent: None}}
                blocks = FigureFactory(None, evidence).blocks(parent)
                self.assertEqual(parent, blocks[0]["source_key"])
                if details.DETAILS.get(parent, {}).get("primary"):
                    self.assertEqual("participant-detail", blocks[0]["source_kind"])
                else:
                    self.assertIn(blocks[0]["source_kind"], {"participant-capture", "reviewed-capture"})
                self.assertEqual(list(child_ids), [block["source_key"] for block in blocks[1:]])
                self.assertTrue(all(block["source_kind"] == "participant-detail" for block in blocks[1:]))
        architecture = FigureFactory(None, {"captures": {}}).blocks("pc-01-architecture")
        self.assertEqual("participant-diagram", architecture[0]["source_kind"])
        self.assertEqual("pc-01-architecture", architecture[0]["source_key"])
        japanese, english = details.architecture_svg_variants(load_map())
        assets = AssetLibrary()
        assets.diagrams["pc-01-architecture"] = japanese
        assets.diagrams_en["pc-01-architecture"] = english
        context = type("Context", (), {
            "assets": assets,
            "ui": {"lightbox.open": {"ja": "拡大"}},
            "ui_text": staticmethod(lambda _key: Text("図", "Figure")),
            "label": staticmethod(lambda _key: "Open"),
        })()
        markup = render_figure(architecture[0], context)
        self.assertIn("figure--participant-diagram", markup)
        self.assertIn('data-l="ja"', markup)
        self.assertIn('data-l="en"', markup)
        self.assertIn('viewBox="0 0 1600 1770"', markup)

    def test_architecture_retains_the_original_input_edge_and_all_binding_meanings(self):
        japanese, english = details.architecture_svg_variants(load_map())
        root = ET.fromstring(japanese)
        edge = root.find(".//*[@id='increment-to-notebook05']")
        self.assertEqual('edge-dash', edge.get('class'))
        self.assertEqual(('increment-files', 'notebook05'),
                         (edge.get('data-from'), edge.get('data-to')))
        for value in ('Furusato Fabric Workshop 3.1', 'Bind Lakehouse columns',
                      'Time series: Eventhouse (Ch. 10)', 'Metrics: Semantic model (Ch. 12)',
                      'Materialize selection (Ch. 16)', 'increment files also feed Notebook 05'):
            self.assertIn(value, english)
        self.assertEqual('M60 600 H45 V800 H610 V844', edge.get('d'))
        self.assertIn('x="790" y="747"', japanese)

    def test_bilingual_svg_markers_are_path_local_not_global_css_overrides(self):
        for language, artwork in zip(('ja', 'en'), details.architecture_svg_variants(load_map())):
            svg = sanitize_svg(artwork, prefix='test-' + language, title='test', description='test')
            root = ET.fromstring(svg)
            ns = {'svg': details.SVG_NAMESPACE}
            style = root.find('svg:defs/svg:style', ns).text
            self.assertNotIn('marker-end', style)
            markers = {node.get('id') for node in root.findall('.//svg:marker', ns)}
            edges = [node for node in root.findall('.//svg:path', ns)
                     if node.get('class') in ('edge', 'edge-dash')]
            self.assertEqual(12, len(edges))
            for edge in edges:
                marker = edge.get('marker-end')
                self.assertEqual(f'url(#test-{language}-arrow)', marker)
                self.assertIn(marker[5:-1], markers)

    def test_ready_panels_preserve_only_version_neutral_output_with_contiguous_overlap(self):
        primary = details.DETAILS['pc-05-notebook01-ready']
        self.assertTrue(primary['primary'])
        self.assertLess(primary['crop'][3], 283)
        left_key = 'pc-05-notebook01-ready-detail'
        right_key = 'pc-05-notebook01-ready-detail-continuation'
        self.assertIn(left_key, details.SUPPRESSED_PARTICIPANT_DETAILS)
        self.assertIn(right_key, details.SUPPRESSED_PARTICIPANT_DETAILS)
        left, right = [details.DETAILS[key]['crop'] for key in (left_key, right_key)]
        self.assertEqual(100, left[2] - right[0])
        self.assertEqual((left[1], left[3]), (right[1], right[3]))
        self.assertEqual((338, 378), (left[1], left[3]))
        with Image.open(details.detail_source_path('pc-05-notebook01-ready-detail')) as source:
            for bounds in ((0, 338, left[0], 378), (right[2], 338, source.width, 378)):
                excluded = source.crop(bounds).convert('RGB')
                self.assertIsNone(ImageChops.difference(
                    excluded, Image.new('RGB', excluded.size, 'white')).getbbox())
        for ident in ('pc-05-notebook01-ready', left_key, right_key):
            text = str(figures.FIGURES[ident])
            for legacy in ('v3.0.0', 'participant=031', 'generation=1'):
                self.assertNotIn(legacy, text)

    def test_applied_output_trim_preserves_output_ink_and_dq_panels_keep_every_row_column(self):
        ident = 'p30-11-executed-output-detail'
        crop = details.DETAILS[ident]['crop']
        with Image.open(details.detail_source_path(ident)) as source:
            # The far-right scrollbar is UI chrome, not output content.
            excluded = source.crop((crop[2], crop[1], 1049, crop[3])).convert('RGB')
            self.assertIsNone(ImageChops.difference(
                excluded, Image.new('RGB', excluded.size, 'white')).getbbox())
        full = details.DETAILS['p30-11-gold-dq-detail']['crop']
        left = details.DETAILS['p30-11-gold-dq-left-detail']['crop']
        right = details.DETAILS['p30-11-gold-dq-right-detail']['crop']
        self.assertEqual((full[0], full[2]), (left[0], right[2]))
        self.assertEqual((full[1], full[3]), (left[1], left[3]))
        self.assertEqual((full[1], full[3]), (right[1], right[3]))
        self.assertEqual(130, left[2] - right[0])

    def test_stable_original_numbers_and_graph_targets_in_current_model(self):
        model = lab.load_model(ROOT)
        originals = [b for b in model[0].figures if b['source_key'] not in details.DETAILS
                     or details.DETAILS[b['source_key']].get('primary')]
        self.assertEqual(list(range(1, 35)), [b['number'] for b in originals])
        self.assertEqual('p30-16-eligibility', originals[31]['source_key'])
        self.assertEqual('pc-16-unsupported-datasource', originals[32]['source_key'])
        self.assertEqual('p30-16-gql', originals[33]['source_key'])
        for block in model[0].figures:
            if block['source_key'] in details.DETAILS and not details.DETAILS[block['source_key']].get('primary'):
                parent = details.DETAILS[block['source_key']]['parent']
                number = next(b['number'] for b in originals if b['source_key'] == parent)
                siblings = details.DETAILS_BY_PARENT[parent]
                index = siblings.index(block['source_key'])
                suffix = '-detail' if index == 0 else f'-detail-{index + 1}'
                self.assertEqual(f'{number}{suffix}', block['number'])
        self.assertEqual('p30-16-gql', originals[33]['source_key'])

    def test_current_guide_contains_only_the_currently_reviewed_figure_set(self):
        current = lab.load_model(ROOT)
        labels = {block['source_key']: block['number'] for block in current[0].figures}
        self.assertEqual(38, current[-1]['counts']['figures'])
        self.assertNotIn('p30-17-ci-sql-output', labels)
        self.assertNotIn('p30-22-import', labels)
        self.assertEqual(34, labels['p30-16-gql'])

    def test_lab_supplements_keep_original_page_segments_and_bilingual_vector_provenance(self):
        model = lab.load_model(ROOT)
        for section in model[0].walk():
            groups = lab.grouped(section.blocks)
            retained = [b for b in section.blocks
                        if b.kind != 'figure' or b['source_kind'] != 'participant-detail'
                        or details.DETAILS.get(b['source_key'], {}).get('primary')]
            original_groups = lab.grouped(retained)
            keys = lambda values: [next((b['source_key'] for _, b in group if b.kind == 'figure'), None)
                                   for group in values]
            self.assertEqual(keys(original_groups), keys(groups), section.ident)
        with tempfile.TemporaryDirectory(prefix='furusato-lab-test-') as directory:
            output = Path(directory).resolve()
            with self.assertRaises(ValueError):
                output.relative_to(ROOT.resolve())
            writer = lab.LabWriter(ROOT, output, model[1], model[4])
            architecture = next(b for b in model[0].figures if b['number'] == 1)
            ja = writer.render_block(architecture, 'ja', 'vector-test')
            en = writer.render_block(architecture, 'en', 'vector-test')
            self.assertIn('pc-01-architecture-ja.svg', ja)
            self.assertIn('pc-01-architecture-en.svg', en)
            variants = details.architecture_svg_variants(load_map())
            for language, artwork in zip(('ja', 'en'), variants):
                asset = writer.assets['pc-01-architecture-' + language]
                self.assertEqual(language, asset['language'])
                self.assertEqual(details.ARCHITECTURE_SHA256, asset['sourceSha256'])
                self.assertEqual(artwork.encode('utf-8'), (output / asset['file']).read_bytes())
            for block in model[0].figures:
                if block['source_key'] not in details.DETAILS:
                    continue
                writer.asset(block)
                asset = writer.assets[block['source_key']]
                recipe = details.DETAILS[block['source_key']]
                self.assertEqual(list(recipe['crop']), asset['cropBox'])
                self.assertEqual(recipe['sha256'], asset['sourceSha256'])
                self.assertEqual(details.crop_png(block['source_key']),
                                 (output / asset['file']).read_bytes())
            lab.validate_lab_assets(ROOT, output, writer.assets)
            for ident, field in (
                    ('pc-01-architecture-en', 'language'),
                    ('pc-01-architecture-ja', 'sourceSha256'),
                    ('p30-12-metric-list-detail', 'cropBox'),
                    ('p30-12-metric-list-detail', 'sourceSha256')):
                mutated = copy.deepcopy(writer.assets)
                mutated[ident][field] = 'invalid'
                with self.subTest(asset=ident, field=field), self.assertRaises((ValueError, KeyError)):
                    lab.validate_lab_assets(ROOT, Path(directory), mutated)
            missing_kind = copy.deepcopy(writer.assets)
            missing_kind['pc-01-architecture-en']['kind'] = 'unreviewed'
            with self.assertRaisesRegex(ValueError, 'Unknown Lab image kind'):
                lab.validate_lab_assets(ROOT, Path(directory), missing_kind)

if __name__ == "__main__":
    unittest.main()
