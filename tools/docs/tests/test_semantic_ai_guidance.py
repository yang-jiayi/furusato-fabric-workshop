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
