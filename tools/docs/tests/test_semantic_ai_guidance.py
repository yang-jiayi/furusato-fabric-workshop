"""The bilingual current guide must expose native-apply and evidence boundaries."""
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "tools/docs"), str(ROOT / "tools/html")]
from furusato_docs.participant_semantic_ai import append_sections, PAYLOAD
from furusato_html.model import Section, Text


class SemanticAIGuidanceTests(unittest.TestCase):
    def test_current_common_publication_status_matches_chapter_17_and_readme_bilingually(self):
        from furusato_docs.participant_current_tuning import append_current_tuning_sections
        semantic = Section("ch-12", 1, "12", Text("12", "12"), chapter=12)
        agent = Section("ch-17", 1, "17", Text("17", "17"), chapter=17)
        append_sections(semantic, ROOT)
        append_current_tuning_sections(agent, ROOT)
        common = [b["text"] for b in semantic.children[0].blocks if b.kind == "code"][-1]
        current = next(s for s in agent.children if s.number == "17.6")
        self.assertEqual(common, current.blocks[2]["text"])
        import hashlib
        self.assertEqual(3_394, len(common.encode("utf-16-le")) // 2)
        sha = "7edbd1657c49f19db27dfeeaa23a1d9b720717cdb22b90263017aa2c3f238f26"
        self.assertEqual(sha, hashlib.sha256(common.encode("utf-8")).hexdigest())
        readme = (ROOT / "README.md").read_text("utf-8")
        for language, verified, pending in (
            ("ja", "設定読み戻しは確認済み", "回答品質の測定は未実施"),
            ("en", "configuration readbacks of this text have been verified",
             "answer-quality measurement is pending"),
        ):
            prose = "\n".join(b["text"].get(language) for b in semantic.children[0].blocks
                              if b.kind == "paragraph")
            for term in ("3,394", sha, "Draft", "Published", verified, pending,
                         "--common-guidance", "17.9"):
                self.assertIn(term, prose)
            for obsolete in ("separate candidate", "別候補", "unmeasured common", "未評価の共通"):
                self.assertNotIn(obsolete, prose)
        for term in ("3,394", sha, "--common-guidance", "公開設定の読み戻しは確認済み",
                     "回答品質の測定は未実施", "configuration readbacks have been verified",
                     "Answer-quality measurement is pending", "Metrics", "GQL"):
            self.assertIn(term, readme)

    def test_common_routing_precedence_and_legitimate_clarification(self):
        guidance = (ROOT / PAYLOAD / "agent-instructions.txt").read_text("utf-8")
        for term in (
            "Explicit user population, source and period take precedence",
            "complete static 2025 snapshot", "one Donation per row",
            "dataset label, not an added date filter",
            "both count and amount leaders", "do not ask which metric",
            "explicitly requested Gold", "unchanged model-level Prep for AI",
            "not before source routing", "documented August 2026 source window",
            "label the year and UTC", "static-clause year does not set",
            "Preserve an explicitly requested different period",
            "recipient versus resident", "relative period without a reference date",
        ):
            self.assertIn(term, guidance)
        self.assertLess(guidance.index("Explicit user population"),
                        guidance.index("Ask a concise clarification"))

    def test_common_composition_preserves_source_rules_and_failure_boundaries(self):
        guidance = (ROOT / PAYLOAD / "agent-instructions.txt").read_text("utf-8")
        for term in (
            "existing source-owned recipe", "raw aggregate before",
            "EventID limit", "never invent unique counts, surrogate identities",
            "Never calculate, display or repeat an unsupported cross-population sum",
            "even to refute", "Retain every requested field",
            "actual stable ID/name pair", "file/run fields and UTC timestamps",
            "executed GQL with returned results", "join-planning metadata and SQL do not",
            "missing required evidence as success", "Income, wealth, tax liability",
            "Never bypass a platform content block",
            "blocked response as a successful business refusal",
        ):
            self.assertIn(term, guidance)
        self.assertLess(len(guidance), 10_000)
        self.assertNotIn("\r", guidance)
        import re
        self.assertEqual(["2025", "2026"], re.findall(r"\d+", guidance))

    def test_native_navigation_figures_and_persistence_boundary(self):
        from furusato_docs.participant30 import FigureFactory, figure_path
        from PIL import Image
        chapter = Section("ch-12", 1, "12", Text("12", "12"), chapter=12)
        append_sections(chapter, ROOT, figures=FigureFactory(None, {}))
        figures = [b for b in chapter.children[0].blocks if b.kind == "figure"]
        self.assertEqual([b["source_key"] for b in figures], [
            "pc-12-prep-navigation", "pc-12-prep-donation-schema",
            "pc-12-prep-date-schema", "pc-12-prep-model-instructions"])
        for figure in figures:
            path = figure_path(figure["source_key"])
            with Image.open(path) as image:
                self.assertGreater(image.width, 1000)
            self.assertTrue(figure["caption"].ja)
            self.assertTrue(figure["caption"].en)
            self.assertTrue(figure["alt"].ja)
            self.assertTrue(figure["alt"].en)
        prose = "\n".join(
            t.en for b in chapter.children[0].blocks
            for t in ([b["text"]] if b.kind == "paragraph" else b["items"] if b.kind == "list" else []))
        for term in ("Home > Copilot dropdown > Prep data for AI", "right paddle",
                     "use Back", "do not select a consent box that disables it",
                     "not proof of effective AI serving", "39 selected fields out of 41"):
            self.assertIn(term, prose)

    def test_evaluation_layer_split_and_current_only_distribution(self):
        from furusato_docs import participant30_evaluation as evaluation
        import current_delivery
        for term in ("model-level Prep for AI", "rollback", "native Apply",
                     "Never reuse an instruction-only", "experimental"):
            self.assertIn(term, evaluation.README)
        self.assertNotIn("already adopted", evaluation.README)
        self.assertIn("tools/data-agent/README.md", current_delivery.MAINTAINER_ONLY_DOCS)
        self.assertIn("workshop/v3.0.0-preview/README-runtime.md",
                      current_delivery.MAINTAINER_ONLY_DOCS)

    def test_bilingual_steps_and_exact_versioned_payloads(self):
        chapter = Section("ch-12", 1, "12", Text("12", "12"), chapter=12)
        append_sections(chapter, ROOT)
        self.assertEqual([s.number for s in chapter.children], ["12.6", "12.7"])
        codes = [b["text"] for s in chapter.children for b in s.blocks if b.kind == "code"]
        contract = json.loads((ROOT / PAYLOAD / "schema.json").read_bytes())
        self.assertEqual(codes, [(ROOT / PAYLOAD / contract[key]).read_text("utf-8")
                                 for key in ("instructionsFile", "agentGuidanceFile")])
        for language in ("ja", "en"):
            prose = "\n".join(b["text"].get(language) for s in chapter.children
                              for b in s.blocks if b.kind == "paragraph")
            for term in ("Prep for AI", "DAX", "SDK", "Verified answers", "KEEPFILTERS", "BLANK"):
                self.assertIn(term, prose)
        english = "\n".join(
            text.en for s in chapter.children for b in s.blocks
            for text in ([b["text"]] if b.kind == "paragraph" else b["items"] if b.kind == "list" else []))
        for boundary in ("does not activate", "cannot configure", "not an authorization boundary",
                         "optional and unconfigured", "do not prove verified answers",
                         "saved to the LSDL", "unvalidated here, not declared unsupported",
                         "sync only once a day", "older than 24 hours", "last 14 days",
                         "do not support CI/CD", "when Fabric IQ is enabled"):
            self.assertIn(boundary, english)


if __name__ == "__main__":
    unittest.main()
