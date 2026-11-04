"""Guard documentation boundaries for Data Agent semantic-model guidance."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "tools" / "docs"), str(ROOT / "tools" / "html")]

from furusato_docs import lab  # noqa: E402
from furusato_docs.participant_current_tuning import (  # noqa: E402
    _assets,
    append_current_tuning_sections,
)
from furusato_html.model import Section, Text  # noqa: E402


class SemanticInstructionBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.assets = _assets(ROOT)
        cls.chapter = Section(
            "chapter-17",
            1,
            "17",
            Text("17. Agent", "17. Agent"),
            chapter=17,
        )
        append_current_tuning_sections(cls.chapter, ROOT)
        cls.sections = {section.ident: section for section in cls.chapter.children}

    @staticmethod
    def prose(section):
        return {
            language: "\n".join(
                block["text"].get(language)
                for block in section.blocks
                if block.kind == "paragraph"
            )
            for language in ("ja", "en")
        }

    def test_current_common_path_is_consistent_in_both_languages(self):
        reference = self.prose(self.sections["chapter-17-6"])
        prepare = self.prose(self.sections["chapter-17-9"])
        review = self.prose(self.sections["chapter-17-10"])
        for language in ("ja", "en"):
            for prose in (reference, prepare, review):
                self.assertIn("--common-guidance", prose[language])
            self.assertIn("設定読み戻しは確認済み" if language == "ja"
                          else "configuration readbacks of this text have been verified",
                          reference[language])
            self.assertIn("回答品質の測定は未実施" if language == "ja"
                          else "answer-quality measurement is pending", reference[language])
            for value in ("3,394", "UTF-16", "rawSha256", "lfSha256",
                          "7edbd1657c49f19db27dfeeaa23a1d9b720717cdb22b90263017aa2c3f238f26",
                          "baseline", "payload", "manifest", "Ontology context",
                          "path/type/is_selected", "active few-shot file/example",
                          "shared-field readbacks", "complete-stage", "dataSourceInstructions",
                          "userDescription"):
                self.assertIn(value, review[language])
            for obsolete in ("9994", "9,994", "default lane", "既定経路", "両経路"):
                self.assertNotIn(obsolete, review[language])
            self.assertIn("fail-closed" if language == "ja" else "fails closed", review[language])
            self.assertIn("停止" if language == "ja" else "Stop", review[language])
            self.assertIn("同じ" if language == "ja" else "same complete", review[language])

    def test_bound_candidate_continues_through_apply_publish_verify_without_quality_claims(self):
        for suffix in (11, 12, 13):
            prose = self.prose(self.sections[f"chapter-17-{suffix}"])
            for language in ("ja", "en"):
                self.assertIn("PrivateRoot", prose[language])
                self.assertIn("固定された共通指示の候補" if language == "ja"
                              else "bound common-guidance candidate", prose[language])
                self.assertIn("17.9", prose[language])
        verify = self.prose(self.sections["chapter-17-13"])
        for language in ("ja", "en"):
            for term in ("Graph/GQL", "Metrics", "readback"):
                self.assertIn(term, verify[language])
        for term in ("model Prep", "source readiness", "effective AI serving", "answer accuracy"):
            self.assertIn(term, verify["en"])

    def test_prepare_hash_wording_passes_existing_composition_terminology_guard(self):
        from furusato_docs.participant30 import JARGON
        prose = self.prose(self.sections["chapter-17-9"])
        self.assertIn("元ファイル", prose["ja"])
        self.assertIn("original-file", prose["en"])
        for language in ("ja", "en"):
            self.assertIsNone(JARGON.search(prose[language]))

    def test_source_reference_distinguishes_supported_metadata_and_agent_global_guidance(self):
        section = self.sections["chapter-17-7"]
        prose = self.prose(section)
        for language in ("ja", "en"):
            self.assertIn("semantic_model.instructions", prose[language])
            self.assertIn("DAX", prose[language])
            self.assertIn("Prep for AI", prose[language])
            self.assertIn("https://learn.microsoft.com/en-us/fabric/data-science/semantic-model-best-practices",
                          prose[language])
            self.assertIn("https://learn.microsoft.com/en-us/fabric/data-science/data-agent-add-datasources",
                          prose[language])
        self.assertIn("Agent 全体の Instructions", prose["ja"])
        self.assertIn("Agent-wide Instructions", prose["en"])
        self.assertIn("model metadata", prose["en"])
        self.assertIn("verified answers", prose["en"])
        self.assertIn("not guarantees", prose["en"])
        self.assertIn("serialized reference", prose["en"])
        self.assertIn("source fields", prose["en"])
        self.assertIn("メタデータ Description", prose["ja"])
        self.assertIn("metadata", prose["en"])
        self.assertIn("17.10", prose["ja"])
        self.assertIn("17.10", prose["en"])
        self.assertIn("entire compiled Draft definition", prose["en"])
        self.assertIn("compiled Draft definition 全体", prose["ja"])
        self.assertIn("stop and request review", prose["en"])
        self.assertIn("停止してレビューを依頼", prose["ja"])
        self.assertNotIn("apply only other values", prose["en"])
        self.assertNotIn("その他の値だけを", prose["ja"])

    def test_definition_diff_and_apply_readbacks_do_not_claim_semantic_field_effect(self):
        diff_prose = self.prose(self.sections["chapter-17-10"])
        apply_prose = self.prose(self.sections["chapter-17-11"])
        for language in ("ja", "en"):
            self.assertIn("serialized", diff_prose[language].lower())
            self.assertIn("dataSourceInstructions", diff_prose[language])
            self.assertIn("DAX", diff_prose[language])
            self.assertIn("readback", diff_prose[language].lower())
            self.assertIn("readback", apply_prose[language].lower())
            self.assertIn("DAX", apply_prose[language])
            if language == "en":
                self.assertIn("does not mean SemanticModel-source", apply_prose[language])
            else:
                self.assertIn("DAX に作用することを意味しません", apply_prose[language])

    def test_global_reference_routes_model_rules_to_native_prep(self):
        prose = self.prose(self.sections["chapter-17-6"])
        for language in ("ja", "en"):
            self.assertIn("12.6", prose[language])
            self.assertIn("12.7", prose[language])
            self.assertIn("DAX", prose[language])
        self.assertIn("not passed", prose["en"])
        self.assertIn("do not partially rewrite", prose["en"])

    def test_apply_scope_requires_unchanged_semantic_fields_or_stop_for_review(self):
        diff_prose = self.prose(self.sections["chapter-17-10"])
        apply_prose = self.prose(self.sections["chapter-17-11"])
        for language in ("ja", "en"):
            whole_definition = ("entire compiled Draft definition" if language == "en"
                                else "compiled definition 全体")
            current = "current Draft" if language == "en" else "現行 Draft"
            unchanged = "unchanged" if language == "en" else "同一であること"
            review = "request review" if language == "en" else "レビューを依頼"
            do_not_apply = "do not run `--apply`" if language == "en" else "--apply を実行せず"
            self.assertIn(whole_definition, diff_prose[language])
            self.assertIn(current, diff_prose[language])
            self.assertIn("candidate", diff_prose[language])
            self.assertIn("dataSourceInstructions", diff_prose[language])
            self.assertIn("userDescription", diff_prose[language])
            self.assertIn(unchanged, diff_prose[language])
            self.assertIn(review, diff_prose[language])
            apply_whole_definition = ("entire compiled Draft definition" if language == "en"
                                      else "compiled Draft definition 全体")
            self.assertIn(apply_whole_definition, apply_prose[language])
            self.assertIn(review, apply_prose[language])
            self.assertIn(do_not_apply, apply_prose[language])

    def test_semantic_definition_readable_view_adds_boundary_without_rewriting_literal(self):
        section = self.sections["chapter-17-10"]
        block = section.blocks[10]
        self.assertEqual("code", block.kind)
        self.assertTrue(block.get("canonicalLiteral"))
        serialized = json.loads(block["text"])
        self.assertEqual(
            self.assets["source_instructions"]["semantic_model"]["instructions"],
            serialized["dataSourceInstructions"],
        )

        writer = lab.LabWriter(ROOT, ROOT / "unused-lab-output", None, None)
        ja = writer.render_block(block, "ja", "ch-17-10:10")
        en = writer.render_block(block, "en", "ch-17-10:10")
        for rendered, language in ((ja, "ja"), (en, "en")):
            self.assertIn(lab.readable_literal(serialized["dataSourceInstructions"]), rendered)
            self.assertIn(block["text"], rendered)
            self.assertIn("serialized reference", rendered.lower())
            self.assertIn("DAX", rendered)
            self.assertLess(rendered.index("Note:") if language == "en" else rendered.index("注意:"),
                            rendered.index("Readable instruction view"))
        self.assertIn("サポート", ja)
        self.assertIn("not a Data Agent-supported editable field", en)


if __name__ == "__main__":
    unittest.main()
