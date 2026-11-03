"""Current 3.1 participant guide composition: procedure only, no working history."""

import hashlib
import re
import sys
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "tools" / "docs"), str(ROOT / "tools" / "html")]

import validate_preview30 as validator
from furusato_docs import participant30
from furusato_docs import participant30_details
from furusato_docs import participant30_evaluation
from furusato_docs import participant30_figures as figures
from furusato_docs import participant30_text as text
from furusato_docs import lab as current_delivery


def texts(document):
    for value in validator.model_texts(document):
        yield value
    for section in document.walk():
        for block in section.blocks:
            if block.kind == "figure":
                yield block["alt"]


class ParticipantEditionTests(unittest.TestCase):
    def test_current_package_paths_are_explained_without_renaming_working_assets(self):
        setup = " ".join(value for pair in text.CHAPTERS[4]["before"] for value in pair)
        self.assertIn("source/WORKSHOP_VERSION", setup)
        self.assertIn("not the course edition", setup)
        self.assertIn("Do not rename", setup)
        for chapter, relative in (
            (5, "workshop/v3.0.0-preview/data/seed"),
            (8, "workshop/v3.0.0-preview/kql/Furusato_Eventhouse_Setup_v2.7.0.kql"),
            (11, "workshop/v3.0.0-preview/notebooks"),
        ):
            with self.subTest(chapter=chapter):
                before = " ".join(value for pair in text.CHAPTERS[chapter]["before"] for value in pair)
                self.assertIn("source/" + relative, before)
                self.assertIn("Git checkout", before)
                self.assertIn("先頭の source/ を除", before)
                self.assertIn("current ZIP", before)
                self.assertTrue((ROOT / relative).exists())
        kql = " ".join(value for pair in text.CHAPTERS[8]["before"] for value in pair)
        self.assertIn("actual current filename, not the course edition", kql)

    @classmethod
    def setUpClass(cls):
        cls.document, _, _, _, cls.evidence, cls.metadata = current_delivery.load_model(ROOT)

    def test_shape_and_checklists(self):
        sections = self.document.sections
        self.assertEqual(29, len(sections))
        self.assertTrue(self.metadata["participantEdition"])
        for section in sections[:24]:
            numbers = [child.number for child in section.children]
            self.assertEqual([f"{section.chapter}.1", f"{section.chapter}.2"], numbers[:2])
            steps = section.children[2] if section.chapter == 17 else section.children[1]
            self.assertEqual(section.chapter >= 4, steps.checklist_id is not None, section.number)
            if section.chapter == 17:
                self.assertIn("Scope and prerequisites", section.children[1].title.en)
                self.assertIn("Steps", steps.title.en)
                self.assertEqual("17.3", steps.number)
        self.assertNotIn("-legacy-", " ".join(s.ident for s in self.document.walk()))

    def test_no_working_records_or_history(self):
        current_procedure_terms = {"receipt", "seed", "execution evidence"}
        for language in ("ja", "en"):
            prose = " ".join(value.get(language) for value in texts(self.document))
            hits = validator.participant_working_content(prose, self.document, language)
            self.assertLessEqual(
                set(hits),
                current_procedure_terms,
                f"Unexpected working-record or history content in {language}: {hits}",
            )
        self.assertEqual(0, self.metadata["retainedLegacyChapters"])
        self.assertEqual(0, self.metadata["retainedLegacyAppendices"])
        joined = " ".join(value.ja + " " + value.en for value in texts(self.document))
        for phrase in ("76 PASS", "48 PASS", "artifact-set", "sourceCommit", "Temp", "R8", "holdout"):
            self.assertNotIn(phrase, joined)
        self.assertNotIn(".private-diagnostic", joined)

    def test_step_numbering_continues_around_figures(self):
        for section in self.document.walk():
            is_steps = (
                section.title.en.endswith(" Steps")
                or section.title.ja.endswith(" 操作手順")
            )
            if not is_steps or section.level != 2 or not section.chapter:
                continue
            expected = 1
            for block in section.blocks:
                if block.kind == "list" and block["numbered"]:
                    self.assertEqual(expected, block.get("start", 1), section.number)
                    expected += len(block["items"])
            self.assertGreater(expected, 1, section.number)

    def test_figures_have_participant_captions(self):
        used = self.metadata["participantFigures"]
        self.assertEqual(len(used), len(set(used)))
        self.assertEqual(len(used), len(self.document.figures))
        for ident in used:
            spec = figures.FIGURES[ident]
            for key in ("caption", "alt"):
                self.assertTrue(all(part.strip() for part in spec[key]), ident)
            if (not ident.startswith("diagram:")
                    and ident not in participant30.participant_figures()
                    and ident not in participant30_details.DETAILS):
                self.assertIn(ident, self.evidence["captures"])

    def test_english_captions_translate_japanese_screen_meaning(self):
        self.assertIn(
            "Only accepted increments quality-checked and deduplicated by Notebook 05; separate from Eventhouse observations.",
            figures.FIGURES["p30-12-metrics"]["caption"][1],
        )
        for ident, expected in {
            "p30-12-metrics": "accepted-increment donation total",
            "pc-12-report-canvas": "The Japanese card labels mean total donations",
            "p30-15-noattachment-preview": "the available evidence does not establish what the data layer means",
            "p30-15-attachment-grounding": "The Japanese answer distinguishes static donations, Eventhouse observations and Notebook 05 quality-processed Gold",
            "p30-15-preview": "does not imply approval or delivery",
        }.items():
            with self.subTest(figure=ident):
                self.assertIn(expected, figures.FIGURES[ident]["caption"][1])
        self.assertIn(
            "not a passing example for the main ontology retaining fifteen relationships",
            figures.FIGURES["p30-15-preview"]["caption"][1],
        )

    def test_chapter15_attachment_instructions_use_text_file_without_stale_capture(self):
        lab = (ROOT / "Lab" / "15-design-improve-and-query-with-ontology-copilot-the-built-in-ontol"
               / "03-15-2-p30-15-attachment-grounding.md").read_text(encoding="utf-8")
        self.assertIn("business-requirements.pdf", lab)
        self.assertIn("current ZIP contains `attachments/business-requirements.txt`", lab)
        self.assertIn("select the supplied TXT for the exercise", lab)
        self.assertIn("現行 ZIP には `attachments/business-requirements.txt`", lab)
        self.assertIn("ZIP 内の TXT を選びます", lab)
        self.assertNotIn("p30-15-attachments.png", lab)
        self.assertIn("does not establish preservation of the main ontology", lab)

    def test_ontology_agent_japanese_answer_figures_have_english_reading_aids(self):
        expected = {
            "p30-15-noattachment-preview": (
                "Visible Japanese answer (translated summary; illustrative, not an accepted result)",
                "three entities and no relationships with a structural warning",
            ),
            "p30-15-attachment-grounding": (
                "StaticSeed as static data and RealtimeIncrement as quality-accepted increments",
                "catalog registration rather than fulfillment",
            ),
            "p30-15-attachment-response-bottom": (
                "without a relationship layer, cross-entity questions may not be answerable",
                "unapplied Plan draft preview",
            ),
            "p30-15-preview": (
                "missing relationship layer may limit cross-entity questions",
                "this is not a passing example for the main ontology retaining fifteen relationships",
            ),
        }
        for ident, phrases in expected.items():
            with self.subTest(figure=ident):
                caption = figures.FIGURES[ident]["caption"][1]
                for phrase in phrases:
                    self.assertIn(phrase, caption)
        no_attachment = figures.FIGURES["p30-15-noattachment-preview"]["caption"][1]
        self.assertIn("three entities and no relationships with a structural warning", no_attachment)
        self.assertNotIn("zero errors and one warning", no_attachment)
        attachment = figures.FIGURES["p30-15-attachment-grounding"]["caption"][1]
        self.assertIn("existing entities, keys and bindings are unchanged", attachment)
        self.assertIn("This does not establish preservation of the main ontology", attachment)
        for below_frame_category in ("shared references", "inheritance", "property types", "relationships are unchanged"):
            self.assertNotIn(below_frame_category, attachment)

        lab = ROOT / "Lab" / "15-design-improve-and-query-with-ontology-copilot-the-built-in-ontol"
        for filename, phrase in (
            ("02-15-2-p30-15-noattachment-preview.md", "three entities and no relationships with a structural warning"),
            ("03-15-2-p30-15-attachment-grounding.md", "catalog registration rather than fulfillment"),
            ("04-15-2-p30-15-attachment-response-bottom.md", "structural caution, not an error"),
            ("05-15-2-p30-15-preview.md", "unapplied draft preview"),
        ):
            with self.subTest(lab_file=filename):
                self.assertIn(phrase, (lab / filename).read_text(encoding="utf-8"))
        no_attachment_lab = (lab / "02-15-2-p30-15-noattachment-preview.md").read_text(encoding="utf-8")
        self.assertIn("three entities and no relationships with a structural warning", no_attachment_lab)
        self.assertNotIn("It reports 0 errors and 1 warning", no_attachment_lab)
        attachment_lab = (lab / "03-15-2-p30-15-attachment-grounding.md").read_text(encoding="utf-8")
        self.assertIn("existing entities, keys and bindings are unchanged", attachment_lab)
        self.assertIn("This does not establish preservation of the main ontology", attachment_lab)
        english_caption = attachment_lab.split("<summary>English</summary>", 1)[1]
        english_caption = english_caption.split(
            "](../assets/p30-15-attachment-grounding.png)", 1
        )[1]
        for below_frame_category in ("shared references", "inheritance", "property types", "relationships are unchanged"):
            self.assertNotIn(below_frame_category, english_caption)

    def test_appendix_e_wording_and_ontology_agent_link_are_clear_and_unique(self):
        appendix = text.APPENDICES["E"]
        self.assertTrue(any(
            question == ("Instances に行が表示されない", "The Instances tab shows no rows")
            for question, _ in appendix["troubleshooting"]
        ))
        agent_url = participant30.LEARN_BASE + "how-to-use-ontology-agent"
        resolved_links = [
            participant30.LEARN_BASE + link if not link.startswith("http") else link
            for link in appendix["links"]
        ]
        self.assertEqual(1, resolved_links.count(agent_url))

    def test_existing_ontology_rule_is_checked_before_creation_and_only_changed_rules_are_saved(self):
        steps = text.CHAPTERS[13]["steps"]
        list_instruction = steps[2]["text"]
        create_instruction = steps[3]["text"]
        save_instruction = steps[4]["text"]
        self.assertIn("SupplierAttribution が既にあるか", list_instruction[0])
        self.assertIn("look for an existing SupplierAttribution", list_instruction[1])
        self.assertIn("見つからない場合だけ New rule", list_instruction[0])
        self.assertIn("only if it is missing", list_instruction[1])
        self.assertIn("SupplierAttribution が見つからなかった場合", create_instruction[0])
        self.assertIn("If SupplierAttribution was not found", create_instruction[1])
        self.assertIn("必要な変更がある場合だけ Save", save_instruction[0])
        self.assertIn("only when you made an actual change", save_instruction[1])
        self.assertIn("Save を有効にするためだけに", save_instruction[0])
        self.assertIn("just to enable it", save_instruction[1])

    def test_shared_workspace_guards_apply_to_target_resources_not_unrelated_items(self):
        chapter8_instruction = text.CHAPTERS[8]["steps"][3]["text"]
        chapter9_preparation = text.CHAPTERS[9]["before"][0]
        self.assertIn("共有 Workspace であることだけでは停止理由になりません", chapter8_instruction[0])
        self.assertIn("A shared workspace alone is not a reason to stop", chapter8_instruction[1])
        self.assertIn("他の参加者が所有・使用する既存リソースには書き込みません", chapter8_instruction[0])
        self.assertIn("never write to supplied shared resources", chapter8_instruction[1])
        self.assertIn("共有ワークスペース内の別リソースにデータがあることだけでは停止しません", chapter9_preparation[0])
        self.assertIn("Data in unrelated resources elsewhere in the shared workspace alone is not a stop condition", chapter9_preparation[1])
        self.assertIn("対象の DonationEvents", chapter9_preparation[0])
        self.assertIn("target DonationEvents table", chapter9_preparation[1])
        self.assertIn("already contains data", chapter9_preparation[1])

    def test_scoring_condition_tables_have_a_scoped_screen_layout_class(self):
        condition_tables = [
            block for section in self.document.walk() for block in section.blocks
            if block.kind == "table" and "Condition ID" in [cell.en for cell in block["headers"]]
        ]
        self.assertTrue(condition_tables)
        self.assertTrue(all(set(block.get("tableClass", "").split()) == {
                                "canonical-condition-rubric", "evaluation-reference"
                            }
                            for block in condition_tables))

    def test_evaluation_kit_points_to_current_lab_and_html_guide(self):
        readme = (ROOT / "workshop" / "v3.0.0-preview" / "data-agent"
                  / "participant-evaluation" / "README.md").read_text(encoding="utf-8")
        self.assertEqual(participant30_evaluation.README, readme)
        for content in (participant30_evaluation.README, readme):
            self.assertIn("docs/v3.1.0/current/guide/furusato-workshop-v3-1-0-complete.html", content)
            self.assertIn("guide/furusato-workshop-v3-1-0-complete.html", content)
            self.assertIn("Lab/19-evaluate-and-improve-ai-answer-quality/", content)
            self.assertIn("Lab/appendix-c-evaluation-questions-scoring-and-recording-forms/", content)
            self.assertIn("Git checkout", content)
            self.assertIn("ZIP root", content)
            self.assertNotIn("source/docs/v3.1.0/", content)
            self.assertNotIn("Word / HTML", content)

        package = ROOT / "docs" / "v3.1.0" / "current" / "Furusato_Workshop_v3.1.0_current.zip"
        with zipfile.ZipFile(package) as archive:
            names = set(archive.namelist())
        self.assertIn("guide/furusato-workshop-v3-1-0-complete.html", names)
        self.assertIn("Lab/19-evaluate-and-improve-ai-answer-quality/README.md", names)
        self.assertIn("Lab/appendix-c-evaluation-questions-scoring-and-recording-forms/README.md", names)
        self.assertIn(
            "source/workshop/v3.0.0-preview/data-agent/participant-evaluation/README.md",
            names,
        )
        self.assertNotIn(
            "source/docs/v3.1.0/current/guide/furusato-workshop-v3-1-0-complete.html",
            names,
        )

    def test_history_illustration_cannot_substitute_for_target_file_evidence(self):
        caption_ja, caption_en = figures.FIGURES["p30-09-native-delivery"]["caption"]
        step = next(step for step in text.CHAPTERS[9]["steps"]
                    if "p30-09-native-delivery" in step.get("figures", []))
        instruction_ja, instruction_en = step["text"]
        self.assertIn("この概要だけでは001の処理", caption_ja)
        self.assertIn("does not verify processing of 001", caption_en)
        self.assertIn("six KPIs", caption_en)
        self.assertIn("/Files/increment/donation_events_001.csv", instruction_en)
        self.assertIn("record the actual activation row", instruction_en)
        self.assertIn("stop without re-uploading", instruction_en)
        self.assertIn("未確認", instruction_ja)
        self.assertIn("再アップロードせずに停止", instruction_ja)
        capture = next(block for block in self.document.figures
                       if block["source_key"] == "p30-09-native-delivery")
        self.assertEqual("participant-capture", capture["source_kind"])
        manifest = participant30.participant_figures()["p30-09-native-delivery"]
        self.assertTrue(manifest["actualUI"])
        self.assertEqual((1469, 593), (manifest["width"], manifest["height"]))
        self.assertEqual(
            "7b78f7761dfa691c2b4a0ad9dfc8b779c436a05728fb426dedf6437bc9ef9353",
            manifest["originalSha256"],
        )
        detail = next(
            block for block in self.document.figures
            if block["source_key"] == "p30-09-activation-detail-001"
        )
        self.assertEqual("participant-detail", detail["source_kind"])
        self.assertIn("one of three UUID-filtered rows", participant30_details.DETAILS[
            "p30-09-activation-detail-001"
        ]["limitations"])
        self.assertIn("neither is shown in this crop", participant30_details.DETAILS[
            "p30-09-activation-detail-001"
        ]["limitations"])
        caption_ja, caption_en = figures.FIGURES["p30-09-activation-detail-001"]["caption"]
        self.assertIn("実際の001 activation 行", caption_ja)
        self.assertIn("図の外に時刻や全処理チェーンの証明はありません", caption_ja)
        self.assertIn("actual 001 activation row", caption_en)
        self.assertIn("does not show the event time or prove the full processing chain", caption_en)
        for internal_detail in ("2026-11-02", "UUID", "three", "left-hand", "receipt", "participant-102"):
            self.assertNotIn(internal_detail, caption_en)
        lesson = (ROOT / "Lab" / "09-pipeline-and-onelake-event-integration"
                  / "03-9-2-p30-09-native-delivery.md").read_text(encoding="utf-8")
        self.assertIn(caption_ja, lesson)
        self.assertIn(caption_en, lesson)
        self.assertNotIn("2026-11-02", lesson)
        self.assertNotIn("one of three UUID-filtered rows", lesson)

    def test_chapter09_nonempty_guard_is_scoped_to_the_exact_target(self):
        source_ja, source_en = text.CHAPTERS[9]["before"][0]
        lab_path = ROOT / "Lab" / "09-pipeline-and-onelake-event-integration" / "01-9-1-what-you-will-do.md"
        lab_content = lab_path.read_text(encoding="utf-8").replace("&lt;", "<").replace("&gt;", ">")
        for value in (source_ja, source_en):
            self.assertIn(value, lab_content)
        self.assertIn("対象の DonationEvents", source_ja)
        self.assertIn("対象の DonationEvents テーブル、Files/increment または OneLake Delta", source_ja)
        self.assertIn("別リソースにデータがあることだけでは停止しません", source_ja)
        self.assertIn("target DonationEvents table, Files/increment or OneLake Delta", source_en)
        self.assertIn("already contains data", source_en)
        self.assertIn("Data in unrelated resources elsewhere", source_en)

    def test_notebook05_preview_figure_is_plan_only_and_crop_excludes_execution_header(self):
        ident = "pc-11-notebook05-preview"
        caption_ja, caption_en = figures.FIGURES[ident]["caption"]
        alt_ja, alt_en = figures.FIGURES[ident]["alt"]
        manifest = participant30.participant_figures()[ident]

        self.assertEqual([32, 32, 704, 246], manifest["cropBox"])
        self.assertEqual((672, 214), (manifest["width"], manifest["height"]))
        self.assertEqual((1480, 270), (manifest["originalWidth"], manifest["originalHeight"]))
        self.assertEqual(
            "8f3ea3cce01a1a17799da5f2a913f1a5d956435803f6365d2c76bcf039790d7e",
            manifest["originalSha256"],
        )
        self.assertIn("PLAN_SHA256 は使わず", caption_ja)
        self.assertIn("図の PLAN_SHA256", caption_ja)
        self.assertIn("value freshly printed by your own preview", caption_en)
        self.assertIn("Do not reuse the illustrated PLAN_SHA256", caption_en)
        for caption in (caption_ja, caption_en):
            self.assertIn("13", caption)
            self.assertIn("29", caption)
        self.assertNotIn("成功のチェック", alt_ja)
        self.assertNotIn("実行時刻", alt_ja)
        self.assertNotIn("execution tick", alt_en.lower())
        self.assertNotIn("execution time", alt_en.lower())
        self.assertIn("apply", caption_en)
        self.assertIn("Gold updates", caption_en)
        self.assertIn("fresh 3.1 run", caption_en)

    def test_gold_explorer_preview_is_not_sql_or_full_aggregation_evidence(self):
        caption_ja, caption_en = figures.FIGURES["p30-11-schema-preview"]["caption"]
        alt_ja, alt_en = figures.FIGURES["p30-11-schema-preview"]["alt"]
        self.assertIn("Lakehouse Explorer", caption_ja)
        self.assertIn("最大1,000行", caption_ja)
        self.assertIn("全件数", caption_ja)
        self.assertIn("SQL analytics endpoint", caption_ja)
        self.assertIn("Lakehouse Explorer", caption_en)
        self.assertIn("up to 1,000 rows", caption_en)
        self.assertIn("not the full row count", caption_en)
        self.assertIn("not a SQL analytics endpoint query result", caption_en)
        self.assertIn("サンプル行", alt_ja)
        self.assertIn("sample rows", alt_en)

        steps = text.CHAPTERS[11]["steps"]
        for language in (0, 1):
            step_text = " ".join(step["text"][language] for step in steps)
            self.assertIn("gold.donations", step_text)
            self.assertIn("endpoint", step_text.lower())
            self.assertIn("unverified" if language else "未確認", step_text)
            self.assertIn("permissions" if language else "権限", step_text)
        english_steps = " ".join(step["text"][1] for step in steps)
        self.assertIn("run a SQL aggregation over the full table", english_steps)
        self.assertIn("are expectations, not measurements", english_steps)
        self.assertNotIn("currently verified read-only SQL catalog", english_steps)

    def test_kql_overview_figure_distinguishes_rounded_ingestion_from_today(self):
        ident = "p30-08-kql-overview"
        caption_ja, caption_en = figures.FIGURES[ident]["caption"]
        alt_ja, alt_en = figures.FIGURES[ident]["alt"]
        manifest = participant30.participant_figures()[ident]

        self.assertEqual("p30-08-kql-overview-current.png", manifest["file"])
        self.assertEqual(
            "3e7ac914132d9a100eda22893c2cedc22552bacc77520d5c6ba6c53425138a03",
            manifest["sha256"],
        )
        self.assertEqual((1241, 720), (manifest["width"], manifest["height"]))
        for caption in (caption_ja, caption_en):
            self.assertIn("15K", caption)
            self.assertTrue(any(term in caption.lower() for term in ("exact", "正確")))
            for unavailable_claim in ("OneLakeDisabled", "mirror disabled", "execution tick"):
                self.assertNotIn(unavailable_claim.lower(), caption.lower())
        self.assertIn("3D", caption_ja)
        self.assertIn("3D", caption_en)
        self.assertIn("Rows today は 0", caption_ja)
        self.assertIn("Rows today is 0", caption_en)
        self.assertIn("exact total", caption_en)
        self.assertIn("正確な総数ではなく", caption_ja)
        self.assertIn("source reconciliation", caption_en)
        self.assertIn("source reconciliation", caption_ja)
        self.assertIn("not evidence of a fresh execution", caption_en)
        self.assertIn("実行、新規データの materialization", caption_ja)
        self.assertIn("table mirroring", caption_en)
        for value in (caption_ja, caption_en, alt_ja, alt_en):
            self.assertNotIn("completeDataActivityTracker", value)
        self.assertIn("DonationEvents", alt_en)
        self.assertIn("DonationEvents", alt_ja)
        self.assertIn("3D", alt_en)
        self.assertIn("3D", alt_ja)

    def test_kql_overview_explains_preserved_avatar_privacy_redaction(self):
        figure = figures.FIGURES["p30-08-kql-overview"]
        for field in ("caption", "alt"):
            ja, en = figure[field]
            for token in ("テーブルカードのアバター", "プライバシー保護", "意図的に黒塗り"):
                self.assertIn(token, ja)
            for token in ("table-card avatar", "intentionally blacked out", "for privacy"):
                self.assertIn(token, en)
            for value in (ja, en):
                self.assertIn("3D", value)
                self.assertIn("15K", value)
                self.assertIn("Rows today", value)
        manifest = participant30.participant_figures()["p30-08-kql-overview"]
        self.assertEqual(
            "3e7ac914132d9a100eda22893c2cedc22552bacc77520d5c6ba6c53425138a03",
            manifest["sha256"],
        )
        self.assertEqual((1241, 720), (manifest["width"], manifest["height"]))

    def test_graph_prerequisites_and_stop_guidance_follow_projection_support(self):
        graph = text.CHAPTERS[16]
        intro = " ".join(value for row in graph["intro"] for value in row)
        before = " ".join(value for row in graph["before"] for value in row)
        steps = " ".join(step["text"][1] for step in graph["steps"])
        checks = repr(graph["checks"])

        self.assertIn("narrower source requirements than general Ontology source support", intro)
        self.assertIn("Delta tables from Lakehouses or mirrored databases", intro)
        self.assertIn("bound to semantic models are unsupported", intro)
        self.assertIn("multiple backing tables", intro)
        self.assertIn("generic binding type alone", intro)
        self.assertIn("how-to-use-ontology-graph#limitations", " ".join(graph["links"]))
        self.assertIn("semantic-model binding or multiple backing tables", steps)
        self.assertIn("generic binding display", steps)
        self.assertIn("required entity or relationship is Ineligible", steps)
        self.assertIn("stop new materialization for that scope", steps)
        self.assertIn("independent SQL, KQL and DAX", steps)
        self.assertIn("not supported for Graph projection", checks)
        self.assertNotIn("AzureStorage.DataLake", intro + before + steps + checks)
        self.assertNotIn("DirectLake means", intro + before + steps + checks)

    def test_graph_selection_figure_is_controls_only_and_uses_verified_crop(self):
        ident = "p30-16-eligibility"
        caption_ja, caption_en = figures.FIGURES[ident]["caption"]
        alt_ja, alt_en = figures.FIGURES[ident]["alt"]
        manifest = participant30.participant_figures()[ident]

        self.assertTrue(manifest["actualUI"])
        self.assertEqual("graph-eligibility-controls-crop.png", manifest["file"])
        self.assertEqual(
            "8216fcf88f718a59b843ceb054775f83712bae555ea7e1836d107d1d4d3b0cea",
            manifest["sha256"],
        )
        self.assertEqual((686, 883), (manifest["width"], manifest["height"]))
        self.assertEqual((1372, 883), (manifest["originalWidth"], manifest["originalHeight"]))
        self.assertEqual([0, 0, 686, 883], manifest["cropBox"])
        self.assertEqual("Lab/assets/p30-16-eligibility.png", manifest["originalFile"])
        self.assertEqual(
            "3bc15540e94fe29adca9a564130f23ed3ad96d7e6afffc2705cce3ac0512ff3b",
            manifest["originalSha256"],
        )
        image = participant30.PARTICIPANT_ASSETS / manifest["file"]
        self.assertEqual(manifest["sha256"], hashlib.sha256(image.read_bytes()).hexdigest())

        for caption in (caption_ja, caption_en):
            self.assertTrue(any(term in caption for term in ("Status", "status")))
        self.assertIn("現在の適格性の証拠ではありません", caption_ja)
        self.assertIn("not current eligibility evidence", caption_en)
        for alt in (alt_ja, alt_en):
            self.assertIn("Status", alt)
            self.assertNotIn("Eligible", alt)
            self.assertNotIn("適格", alt)

        graph_step = text.CHAPTERS[16]["steps"][1]
        self.assertIn("必須範囲の Status を実行時に確認", graph_step["text"][0])
        self.assertIn("Check Status for your own required scope", graph_step["text"][1])
        self.assertIn("select only Eligible items", graph_step["text"][1])

    def test_protected_evaluation_questions_are_complete(self):
        appendix_c = next(s for s in self.document.sections if s.appendix == "C")
        questions = [child for child in appendix_c.children if re.search(r"\bT\d\d\b", child.title.ja)]
        self.assertEqual(10, len(questions))
        self.assertEqual(84, self.metadata["counts"]["conditions"])
        overview = next(b for b in appendix_c.children[0].blocks if b.kind == "table")
        expected = {row[2].ja for row in overview["rows"]}
        shown = {b["text"].ja if hasattr(b["text"], "ja") else b["text"]
                 for s in questions for b in s.blocks if b.kind in {"callout", "code"}}
        self.assertEqual(expected, expected & shown)
        for section in questions:
            self.assertIn("table", [b.kind for b in section.blocks], section.number)

    def test_text_module_covers_every_chapter_and_appendix(self):
        self.assertEqual(set(range(1, 25)), set(text.CHAPTERS))
        self.assertEqual(set("ABCDE"), set(text.APPENDICES))
        self.assertEqual(set(range(1, 25)), set(text.CHAPTER_TITLES))
        self.assertEqual(participant30.TAGLINE.keys(), {"ja", "en"})

    def test_calibration_uses_existing_measure_definitions(self):
        model = ROOT / "workshop/v3.0.0-preview/powerbi/Furusato_Analytics.SemanticModel/definition/tables/寄附.tmdl"
        definitions = dict(re.findall(r"^\s*measure ([^=\n]+?)\s*=\s*(.+)$", model.read_text(encoding="utf-8"), re.MULTILINE))
        examples = "\n".join(step["code"][1] for step in text.CHAPTERS[12]["steps"] if "code" in step)
        for name in ("静的寄附件数", "受入増分寄附件数"):
            self.assertIn(f"[{name}] = {definitions[name]}", examples)

    def test_standard_route_keeps_one_ontology_and_retains_execution_boundaries(self):
        procedures = " ".join(step["text"][1] for chapter in text.CHAPTERS.values() for step in chapter["steps"])
        for obsolete in ("create a separate ontology for this lab", "Create an empty ontology for this chapter",
                         "Import the exported file into another new, empty ontology", "ONT_Furusato_Relationships_<PID>"):
            self.assertNotIn(obsolete, procedures)
        agent = " ".join(step["text"][1] for step in text.CHAPTERS[17]["steps"])
        self.assertIn("measured-contract-20261015", agent)
        self.assertIn("bronze.donation_events_raw", agent)
        calibration = " ".join(step["text"][1] for step in text.CHAPTERS[19]["steps"])
        self.assertIn("12 AM=00, 12 PM=12", calibration)
        self.assertIn("Retain execution failures", calibration)
        self.assertIn("Do not resubmit questions", calibration)


if __name__ == "__main__":
    unittest.main()
