"""Narrow source, privacy, font and actual-binary checks. No cloud writes."""

import hashlib
import json
import sys
import unittest
from pathlib import Path

import fitz
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_attachments as pack


class AttachmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out = pack.ROOT / "workshop" / "v3.0.0-preview" / "attachments"
        cls.manifest = json.loads((cls.out / "manifest.json").read_text(encoding="utf-8"))
        cls.context = pack.load_context(pack.ROOT, document_edition="unified-20260923", source_version="2.7.0")

    def test_real_files_and_upload_budget(self):
        self.assertLessEqual(len(pack.PACK_NAMES), 10)
        for name in pack.PACK_NAMES:
            path = self.out / name
            self.assertGreater(path.stat().st_size, 0)
            self.assertLessEqual(path.stat().st_size, pack.MAX_BYTES)
            self.assertEqual(pack.sha(path), self.manifest["files"][name]["sha256"])
        self.assertFalse(self.manifest["uploadObserved"])
        self.assertFalse(self.manifest["modelUseObserved"])

    def test_dictionary_matches_actual_public_sources(self):
        actual = (self.out / "data-dictionary.txt").read_text(encoding="utf-8")
        self.assertEqual(pack.dictionary(self.context), actual)
        for entity in self.context.entities:
            self.assertIn(entity.name + " | key=" + entity.key_property, actual)
            for prop in entity.properties:
                self.assertIn(prop.name + " : " + prop.value_type, actual)
        self.assertIn("15000", actual)
        self.assertIn("14900", actual)
        self.assertIn("MunicipalityId is String", actual)
        self.assertIn("NOT a generation-2 definition payload", actual)
        self.assertIn("new TMDL target type=int64", actual)
        self.assertIn("TimeSeries<int64>", actual)
        self.assertIn("DataSource=StaticSeed", actual)
        self.assertIn("DataSource=RealtimeIncrement", actual)
        self.assertIn("NOT payment/shipment confirmation", actual)
        self.assertIn("Gold build completion is independent", actual)
        self.assertIn("static-only companion", actual)
        self.assertFalse(self.manifest["definitionContext"]["nativeBindingVerified"])
        self.assertFalse(self.manifest["definitionContext"]["generation2Payload"])

    def test_pdf_is_readable_embeds_font_and_has_both_languages(self):
        with fitz.open(self.out / "business-requirements.pdf") as pdf:
            self.assertGreaterEqual(len(pdf), 2)
            text = "\n".join(page.get_text() for page in pdf)
            self.assertIn("業務要件", text)
            self.assertIn("Business requirements", text)
            self.assertIn("15,000", text)
            self.assertIn("14,900", text)
            self.assertIn("Gold", text)
            self.assertIn("StaticSeed", text)
            self.assertIn("RealtimeIncrement", text)
            self.assertIn("manual business approval", " ".join(text.split()))
            self.assertNotIn("\ufffd", text)
            font_xrefs = {font[0] for page in pdf for font in page.get_fonts()}
            embedded = [pdf.extract_font(xref)[3] for xref in font_xrefs]
            self.assertTrue(any(embedded), "Japanese font must actually be embedded")
            for page in pdf:
                for block in page.get_text("dict")["blocks"]:
                    if "lines" not in block:
                        continue
                    for line in block["lines"]:
                        for span in line["spans"]:
                            x0, y0, x1, y1 = span["bbox"]
                            self.assertGreaterEqual(x0, 0)
                            self.assertGreaterEqual(y0, 0)
                            self.assertLessEqual(x1, page.rect.width + 1)
                            self.assertLessEqual(y1, page.rect.height + 1)
            pack.assert_portable(text)
            for value in pdf.metadata.values():
                if value:
                    pack.assert_portable(value)

    def test_png_is_legible_schema_not_mock_ui(self):
        with Image.open(self.out / "domain-model.png") as image:
            image.verify()
        with Image.open(self.out / "domain-model.png") as image:
            self.assertEqual((2800, 1900), image.size)
            self.assertIn("not a Fabric UI screenshot", image.info["Title"])
            for relationship in self.context.relationships:
                self.assertIn(relationship.name, image.info["Description"])
            for value in image.info.values():
                if isinstance(value, str):
                    pack.assert_portable(value)

    def test_privacy_guard_negative_cases(self):
        for bad in (
            "https://app.fabric.microsoft.com/groups/anything", r"C:\Users\person\file",
            "user@example.com", "Bearer abc", "sig=abc",
            "00000000-1111-2222-3333-444444444444",
        ):
            with self.assertRaises(ValueError):
                pack.assert_portable(bad)
        for name in ("data-dictionary.txt", "revision-requirements.txt"):
            pack.assert_portable((self.out / name).read_text(encoding="utf-8"))

    def test_revision_requires_object_kind_and_saved_definition_review(self):
        revision = (self.out / "revision-requirements.txt").read_text(encoding="utf-8")
        self.assertIn("a Business Rule is not a relationship", revision)
        self.assertIn("reusableProperty", revision)
        self.assertIn("redefines", revision)
        self.assertIn("save a native version", revision)
        self.assertIn("Restore the baseline", revision)


if __name__ == "__main__":
    unittest.main()
