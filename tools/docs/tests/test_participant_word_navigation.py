"""Field-free export checks use real OOXML; no Word or Fabric calls."""

import copy
import io
import sys
import tempfile
import unittest
import zipfile
from contextlib import redirect_stderr
from pathlib import Path

from lxml import etree

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "tools/docs"), str(ROOT / "tools/html")]

import build_preview30 as builder
import package_preview30 as packager
import validate_preview30 as validator
from furusato_docs import participant_word as navigation
from furusato_docs.docx_kit import DocumentBuilder
from furusato_docs.oox import StyleCarrier
from furusato_docs.reproducible import write_package


class ParticipantWordNavigationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="participant-word-navigation-")
        self.addCleanup(temporary.cleanup)
        self.work = Path(temporary.name)
        self.path = self.work / "guide.docx"

    def guide(self):
        document = DocumentBuilder(StyleCarrier.resolve(ROOT), self.work / "shell.docx")
        entries = [(index, "第" + str(index) + "章 手順") for index in range(1, 30)]
        navigation.chapter_contents(document, entries)
        for index, title in entries:
            navigation.add_bookmark(document.heading(title, 1), index)
            document.body("参加者が行う手順です。")
        document.save(self.path)
        navigation.remove_carried_fields(self.path)
        with zipfile.ZipFile(self.path) as archive:
            return {name: archive.read(name) for name in archive.namelist()}

    def receipt(self):
        return {
            "passedLocalChecks": True, "participantEdition": True,
            "wordNavigation": "headings", "microsoftWordLayoutVerified": False,
            "findings": [{"check": name, "level": "PASS"}
                         for name in packager.REQUIRED_PARTICIPANT_CHECKS],
        }

    def test_chapter_links_are_persistent_and_point_to_matching_actual_headings(self):
        parts = self.guide()
        checks = navigation.inspect_navigation(parts)
        self.assertTrue(all(result for result, _ in checks.values()), checks)
        document = etree.fromstring(parts["word/document.xml"])
        self.assertEqual(29, len(list(document.iter(navigation.W + "hyperlink"))))
        self.assertNotIn(b"PAGEREF", parts["word/document.xml"])
        self.assertNotIn(b"Word", parts["word/document.xml"])
        with zipfile.ZipFile(self.path) as archive:
            self.assertIsNone(archive.testzip())

    def test_wrong_missing_or_repeated_hyperlink_target_is_rejected(self):
        original = self.guide()
        for target in ("MissingChapter", "FurusatoChapter002", ""):
            parts = copy.deepcopy(original)
            document = etree.fromstring(parts["word/document.xml"])
            link = next(document.iter(navigation.W + "hyperlink"))
            link.set(navigation.W + "anchor", target)
            parts["word/document.xml"] = etree.tostring(document)
            self.assertFalse(navigation.inspect_navigation(parts)["word.headingNavigationTargets"][0])

    def test_footer_field_and_cached_page_result_are_removed_without_losing_other_text(self):
        parts = self.guide()
        parts["word/footer1.xml"] = (
            '<w:ftr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            '<w:p><w:r><w:t>Workshop </w:t></w:r>'
            '<w:r><w:fldChar w:fldCharType="begin"/></w:r><w:r><w:instrText> PAGE </w:instrText></w:r>'
            '<w:r><w:fldChar w:fldCharType="separate"/></w:r><w:r><w:t>OLD_PAGE_232</w:t></w:r>'
            '<w:r><w:fldChar w:fldCharType="end"/></w:r>'
            '<w:fldSimple w:instr="NUMPAGES"><w:r><w:t>OLD_TOTAL_232</w:t></w:r></w:fldSimple>'
            '<w:r><w:t> guide</w:t></w:r></w:p></w:ftr>'
        ).encode()
        self.assertFalse(navigation.inspect_navigation(parts)["word.noOfficeFields"][0])
        write_package(self.path, parts)
        self.assertEqual(2, navigation.remove_carried_fields(self.path))
        with zipfile.ZipFile(self.path) as archive:
            footer = archive.read("word/footer1.xml")
        self.assertIn(b"Workshop", footer)
        self.assertIn(b"guide", footer)
        self.assertNotIn(b"OLD_", footer)
        self.assertNotIn(b"fld", footer)

    def test_bookmark_end_must_exist(self):
        parts = self.guide()
        document = etree.fromstring(parts["word/document.xml"])
        end = next(document.iter(navigation.W + "bookmarkEnd"))
        end.getparent().remove(end)
        parts["word/document.xml"] = etree.tostring(document)
        self.assertFalse(navigation.inspect_navigation(parts)["word.headingNavigationBookmarks"][0])

    def test_duplicate_bookmark_ids_cannot_be_mistaken_for_valid_targets(self):
        parts = self.guide()
        document = etree.fromstring(parts["word/document.xml"])
        starts = list(document.iter(navigation.W + "bookmarkStart"))
        ends = list(document.iter(navigation.W + "bookmarkEnd"))
        starts[1].set(navigation.W + "id", starts[0].get(navigation.W + "id"))
        ends[1].set(navigation.W + "id", ends[0].get(navigation.W + "id"))
        parts["word/document.xml"] = etree.tostring(document)
        self.assertFalse(navigation.inspect_navigation(parts)["word.headingNavigationBookmarks"][0])

    def test_portable_fonts_bind_japanese_mixed_text_and_preserve_monospace_code(self):
        document = DocumentBuilder(StyleCarrier.resolve(ROOT), self.work / "shell.docx")
        document.body("日本語と `KEEPFILTERS` の混在を確認します。")
        document.table(["列名", "説明"], [["寄附金額", "日本語の正確な表示"]], caption="表示確認", widths=[2, 4])
        document.code_block("SELECT [寄附金額] FROM [寄附];", language="SQL")
        document.save(self.path)
        with zipfile.ZipFile(self.path) as archive:
            old_numbering = archive.read("word/numbering.xml")
        receipt = navigation.apply_fonts(self.path)
        self.assertGreater(receipt["codeRunsBound"], 0)
        with zipfile.ZipFile(self.path) as archive:
            parts = {name: archive.read(name) for name in archive.namelist()}
        self.assertTrue(navigation.inspect_fonts(parts)[0])
        self.assertEqual(old_numbering, parts["word/numbering.xml"])
        body = etree.fromstring(parts["word/document.xml"])
        for run in body.iter(navigation.W + "r"):
            text = "".join(node.text or "" for node in run.iter(navigation.W + "t"))
            fonts = run.find(navigation.W + "rPr/" + navigation.W + "rFonts")
            if "KEEPFILTERS" in text or "SELECT" in text:
                self.assertEqual(navigation.CODE_FONT, fonts.get(navigation.W + "eastAsia"))
        styles = etree.fromstring(parts["word/styles.xml"])
        default = styles.find(navigation.W + "docDefaults/" + navigation.W + "rPrDefault/" + navigation.W + "rPr/" + navigation.W + "rFonts")
        default.set(navigation.W + "asciiTheme", "minorHAnsi")
        parts["word/styles.xml"] = etree.tostring(styles)
        self.assertFalse(navigation.inspect_fonts(parts)[0])

    def test_mode_is_participant_only_and_never_final_acceptance(self):
        self.assertEqual("fields", navigation.require_mode("fields"))
        with self.assertRaisesRegex(ValueError, "participant-edition"):
            navigation.require_mode("headings")
        with self.assertRaisesRegex(ValueError, "acceptance gate"):
            navigation.require_mode("headings", participant_edition=True, require_acceptance=True)

    def test_participant_receipt_does_not_satisfy_default_word_render_gate(self):
        receipt = self.receipt()
        packager.require_full_validation(receipt, word_navigation="headings", participant_edition=True)
        with self.assertRaisesRegex(ValueError, "navigation mode"):
            packager.require_full_validation(receipt)
        default = copy.deepcopy(receipt)
        default.pop("wordNavigation")
        with self.assertRaisesRegex(ValueError, "Full Word rendering"):
            packager.require_full_validation(default)

    def test_participant_gate_requires_all_browser_and_navigation_checks_and_honest_scope(self):
        for name in packager.REQUIRED_PARTICIPANT_CHECKS:
            receipt = self.receipt()
            receipt["findings"] = [row for row in receipt["findings"] if row["check"] != name]
            with self.subTest(check=name), self.assertRaisesRegex(ValueError, "evidence is missing"):
                packager.require_full_validation(receipt, word_navigation="headings", participant_edition=True)
        for field, value in (("participantEdition", False), ("microsoftWordLayoutVerified", True),
                             ("stats", {"word": {"pages": 232}})):
            receipt = self.receipt()
            receipt[field] = value
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, "no Microsoft Word"):
                packager.require_full_validation(receipt, word_navigation="headings", participant_edition=True)

    def test_cli_rejects_headings_before_any_build_without_participant_flag(self):
        calls = (
            (builder.main, ["--out", str(self.work / "pair"), "--review", str(self.work / "review")]),
            (validator.main, ["--pair", str(self.work / "pair"), "--review", str(self.work / "review")]),
        )
        for main, args in calls:
            stderr = io.StringIO()
            with self.subTest(main=main), redirect_stderr(stderr), self.assertRaises(SystemExit) as error:
                main(args + ["--word-navigation", "headings"])
            self.assertEqual(2, error.exception.code)
            self.assertIn("requires --participant-edition", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
