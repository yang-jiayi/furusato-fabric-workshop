"""Keep corrected Word filenames, HTML links and provenance on the same edition."""

from __future__ import annotations

import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools" / "docs"))
sys.path.insert(0, str(ROOT / "tools" / "html"))

from furusato_docs.deliverables import deliverable_names, validate_edition
from build_html import office_sources
from validate_html import Report, Structure, check_office_sources, validate


class DeliverableEditionTests(unittest.TestCase):
    def test_original_names_are_unchanged(self):
        names = deliverable_names("2.7.0")
        self.assertEqual(
            names.participant, "Fabric_IQ_Ontology_Workshop_Furusato_Participant_v2.7.0.docx"
        )
        self.assertEqual(names.validation, "Furusato_Data_Agent_Validation_10_v2.7.0.docx")
        self.assertEqual(
            names.workbook, "Furusato_Notebook_01-05_Processing_Specification_v2.7.0.xlsx"
        )
        self.assertEqual(names.html, "furusato-workshop-v2-7-0-complete.html")

    def test_edition_changes_all_names_not_the_version(self):
        original = deliverable_names("2.7.0")
        revised = deliverable_names("2.7.0", "deployment-review-20260905")
        for old, new in zip((*original.office, original.html), (*revised.office, revised.html)):
            with self.subTest(name=old):
                self.assertEqual(
                    new, f"{Path(old).stem}_deployment-review-20260905{Path(old).suffix}"
                )
                self.assertNotEqual(new, old)

    def test_invalid_editions_are_rejected(self):
        for edition in ("../original", r"..\original", "/tmp", "a.b", "two words", "UPPER", "-a", "a" * 41):
            with self.subTest(edition=edition), self.assertRaises(ValueError):
                validate_edition(edition)

    def test_empty_edition_is_backward_compatible(self):
        self.assertEqual(validate_edition(""), "")
        self.assertEqual(deliverable_names("2.7.0", ""), deliverable_names("2.7.0"))

    def test_missing_revised_sources_do_not_fall_back_to_originals(self):
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            docs = root / "docs"
            docs.mkdir()
            for name in deliverable_names("2.7.0").office:
                (docs / name).write_bytes(b"original release")
            with self.assertRaisesRegex(SystemExit, "missing Office source"):
                office_sources(root, "2.7.0", "revised")

    def test_revised_footer_and_download_links_must_match(self):
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            docs = root / "docs"
            docs.mkdir()
            names = deliverable_names("2.7.0", "revised")
            original_names = deliverable_names("2.7.0")
            for name in original_names.office:
                (docs / name).write_bytes(b"untouched original")
            for name in names.office:
                (docs / name).write_bytes(name.encode("ascii"))
            digests = office_sources(root, "2.7.0", "revised")
            self.assertEqual(set(digests), set(names.office))
            for name in original_names.office:
                self.assertEqual((docs / name).read_bytes(), b"untouched original")
            markup = "".join(
                f'<p data-office-source="{name}" data-office-release="{digest}" '
                f'data-office-observed="{digest}"></p><a download href="{name}">Office</a>'
                for name, digest in digests.items()
            )
            for stale_link in (False, True):
                with self.subTest(stale_link=stale_link):
                    structure = Structure()
                    source = markup.replace(
                        f'href="{names.participant}"', f'href="{original_names.participant}"'
                    ) if stale_link else markup
                    structure.feed(source)
                    structure.close()
                    report = Report()
                    check_office_sources(report, structure.root, root, "2.7.0", digests, "revised")
                    failed = {check for status, check, _ in report.results if status == "FAIL"}
                    self.assertEqual(failed, {"source.downloadEdition"} if stale_link else set())
            (docs / names.validation).write_bytes(b"changed after HTML build")
            report = Report()
            check_office_sources(report, structure.root, root, "2.7.0", digests, "revised")
            self.assertIn("source.matchesDisk", {c for s, c, _ in report.results if s == "FAIL"})
            self.assertNotEqual(digests[names.validation], hashlib.sha256(b"changed after HTML build").hexdigest())

    def test_validator_does_not_validate_original_html_for_revised_edition(self):
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            (root / "VERSION").write_text("2.7.0\n", encoding="utf-8")
            (root / deliverable_names("2.7.0").html).write_text("original", encoding="utf-8")
            report = validate(root, root, edition="revised")
            self.assertEqual([check for status, check, _ in report.results if status == "FAIL"], ["file.exists"])


if __name__ == "__main__":
    unittest.main()
