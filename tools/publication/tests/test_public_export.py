"""Publication policy tests use tiny fixtures, never rebuild or edit release files."""

from __future__ import annotations

import hashlib
import base64
import os
import shutil
import stat
import sys
import unittest
import uuid
import warnings
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools" / "publication"))

import export_public_documents as publication
import validate_html as html_validation
from furusato_docs.deliverables import deliverable_names
from furusato_docs.publication import (
    PUBLIC_NOTICE,
    PUBLIC_PARAMETER_NOTE,
    PUBLIC_RECORD_NOTE,
    PublicationError,
    check_directory,
    prepare_public_build,
    public_link_error,
    public_word_errors,
    safe_path,
)

EDITION = "agent-quality-20260907"
OFFICE_RELATIONSHIPS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
CONTENT_TYPES = (
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
    '<Default Extension="xml" ContentType="application/xml"/>'
    '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
    '<Override PartName="/word/document.xml" '
    'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
    '</Types>'
)


def relationships(kind: str, target: str, *, prefix: str = OFFICE_RELATIONSHIPS) -> bytes:
    return (
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        f'<Relationship Id="r1" Type="{prefix}/{kind}" Target="{target}"/>'
        '</Relationships>'
    ).encode("utf-8")


class PublicExportTests(unittest.TestCase):
    def setUp(self):
        self.area = ROOT / "tools" / "publication" / (".p" + uuid.uuid4().hex[:8])
        self.repo = self.area / "r"
        self.repo.mkdir(parents=True)
        self.addCleanup(shutil.rmtree, self.area)
        (self.repo / "VERSION").write_text("2.7.0\n", encoding="utf-8", newline="\n")
        self.names = deliverable_names("2.7.0", EDITION)
        self.source = self.area / "s"
        self.output = self.area / "export"
        self.manifest = self.area / "evidence" / "SHA256SUMS.txt"
        self.source.mkdir()
        self.write_word()
        self.write_html()
        docs = self.repo / "docs"
        docs.mkdir()
        self.originals = {}
        for edition in ("", "deployment-review-20260905"):
            names = deliverable_names("2.7.0", edition)
            for name in (*names.office, names.html):
                self.originals[docs / name] = ("immutable " + name).encode("utf-8")
        self.originals[docs / "old-authoring.pptx"] = b"private authoring original"
        for path, content in self.originals.items():
            path.write_bytes(content)
        self.content_validation = patch.object(publication, "_validate_content")
        self.validate_content = self.content_validation.start()
        self.addCleanup(self.content_validation.stop)

    def tearDown(self):
        for path, content in self.originals.items():
            self.assertEqual(path.read_bytes(), content, f"original modified: {path}")

    def write_word(self, *, extra: dict[str, bytes] | None = None, body_extra: str = ""):
        text = PUBLIC_NOTICE + PUBLIC_RECORD_NOTE + PUBLIC_PARAMETER_NOTE
        document = (
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            f"<w:body><w:p><w:r><w:t>{escape(text)}</w:t></w:r></w:p>{body_extra}</w:body></w:document>"
        )
        parts = {
            "word/document.xml": document.encode("utf-8"),
            "[Content_Types].xml": CONTENT_TYPES.encode("utf-8"),
            **(extra or {}),
        }
        with zipfile.ZipFile(self.source / self.names.participant, "w") as archive:
            for name, content in parts.items():
                archive.writestr(name, content)

    def markup(self) -> str:
        digest = hashlib.sha256((self.source / self.names.participant).read_bytes()).hexdigest()
        return (
            '<!DOCTYPE html><html><head><meta name="publication-mode" content="public-documents-only">'
            "</head><body>"
            f"<p>{escape(PUBLIC_NOTICE + PUBLIC_RECORD_NOTE + PUBLIC_PARAMETER_NOTE)}</p>"
            f'<p data-office-source="{self.names.participant}" data-office-release="{digest}" '
            f'data-office-observed="{digest}">{self.names.participant} sha256 {digest}</p>'
            f'<a href="{self.names.participant}" download>Word</a>'
            "</body></html>"
        )

    def write_html(self, raw: str | None = None):
        (self.source / self.names.html).write_text(
            raw if raw is not None else self.markup(), encoding="utf-8", newline="\n"
        )

    def test_export_is_exact_pair_byte_identical_and_manifest_external(self):
        before = {p.name: p.read_bytes() for p in self.source.iterdir()}
        result = publication.export(self.repo, self.source, self.output, EDITION, manifest=self.manifest)
        self.assertEqual({p.name for p in self.output.iterdir()}, set(self.names.public_pair))
        self.assertEqual({p.name: p.read_bytes() for p in self.output.iterdir()}, before)
        self.assertEqual({p.name: p.read_bytes() for p in self.source.iterdir()}, before)
        self.assertEqual(self.manifest.read_bytes().count(b"\n"), 2)
        self.assertNotIn(b"\r", self.manifest.read_bytes())
        self.assertFalse(result["published"])
        self.validate_content.assert_called_once_with(self.repo, self.source, EDITION)

    def test_no_manifest_is_added_by_default(self):
        result = publication.export(self.repo, self.source, self.output, EDITION)
        self.assertIsNone(result["manifest"])
        self.assertEqual(len(list(self.output.iterdir())), 2)

    def test_existing_pair_is_validated_read_only_not_overwritten(self):
        publication.export(self.repo, self.source, self.output, EDITION, manifest=self.manifest)
        before = publication._hashes(self.output, self.names)
        with self.assertRaisesRegex(PublicationError, "overwrite"):
            publication.export(self.repo, self.source, self.output, EDITION)
        result = publication.validate_export(self.repo, self.output, EDITION, manifest=self.manifest)
        self.assertEqual(result["files"], before)
        self.assertTrue(result["validatedOnly"])
        self.manifest.write_text("wrong hash\n", encoding="utf-8", newline="\n")
        with self.assertRaisesRegex(PublicationError, "manifest"):
            publication.validate_export(self.repo, self.output, EDITION, manifest=self.manifest)
        self.assertEqual(publication._hashes(self.output, self.names), before)

    def test_unexpected_files_are_never_cleaned(self):
        for extra in ("old.docx", self.names.workbook, self.names.validation, "notes.json", ".hidden"):
            output = self.area / uuid.uuid4().hex[:6]
            output.mkdir()
            sentinel = output / extra
            sentinel.write_bytes(b"preserve")
            with self.subTest(extra=extra), self.assertRaisesRegex(PublicationError, "unexpected"):
                publication.export(self.repo, self.source, output, EDITION)
            self.assertEqual(list(output.iterdir()), [sentinel])
            self.assertEqual(sentinel.read_bytes(), b"preserve")

    def test_unexpected_source_companion_fails_without_changing_it(self):
        companion = self.source / self.names.workbook
        companion.write_bytes(b"internal workbook")
        with self.assertRaisesRegex(PublicationError, "unexpected"):
            publication.export(self.repo, self.source, self.output, EDITION)
        self.assertEqual(companion.read_bytes(), b"internal workbook")
        self.assertFalse(self.output.exists())

    def test_missing_companion_is_not_required_but_missing_selected_word_fails(self):
        publication.validate_pair_policy(self.repo, self.source, "2.7.0", EDITION)
        (self.source / self.names.participant).rename(self.area / "held-word.docx")
        with self.assertRaisesRegex(PublicationError, "missing public documents"):
            publication.export(self.repo, self.source, self.output, EDITION)
        self.assertFalse(self.output.exists())

    def test_output_and_manifest_safety_precedes_content_validation(self):
        cases = (
            (self.repo / "docs" / "public", None),
            (self.source, None),
            (self.source / "nested", None),
            (self.area, None),
            (self.area / "x" / ".." / "export", None),
            (self.output, self.output / "SHA256SUMS.txt"),
            (self.output, self.source / "SHA256SUMS.txt"),
            (self.output, self.repo / "hashes.txt"),
        )
        for output, manifest in cases:
            with self.subTest(output=output, manifest=manifest), self.assertRaises(PublicationError):
                publication.export(self.repo, self.source, output, EDITION, manifest=manifest)
        self.validate_content.assert_not_called()
        self.assertFalse(self.output.exists())

    def test_manifest_is_not_overwritten(self):
        self.manifest.parent.mkdir()
        self.manifest.write_bytes(b"existing evidence")
        with self.assertRaisesRegex(PublicationError, "overwrite"):
            publication.export(self.repo, self.source, self.output, EDITION, manifest=self.manifest)
        self.assertEqual(self.manifest.read_bytes(), b"existing evidence")
        self.assertFalse(self.output.exists())

    def test_failed_content_validation_exports_nothing(self):
        self.validate_content.side_effect = PublicationError("content gate failed")
        with self.assertRaisesRegex(PublicationError, "content gate"):
            publication.export(self.repo, self.source, self.output, EDITION)
        self.assertFalse(self.output.exists())
        self.assertFalse(self.manifest.exists())

    def test_source_or_destination_change_during_validation_is_refused(self):
        def change_source(*_):
            with (self.source / self.names.html).open("a", encoding="utf-8", newline="\n") as handle:
                handle.write("\n")

        self.validate_content.side_effect = change_source
        with self.assertRaisesRegex(PublicationError, "changed during validation"):
            publication.export(self.repo, self.source, self.output, EDITION)
        self.assertFalse(self.output.exists())
        self.write_html()

        def change_output(*_):
            self.output.mkdir()
            (self.output / self.names.html).write_bytes(b"concurrent file")

        self.validate_content.side_effect = change_output
        with self.assertRaisesRegex(PublicationError, "changed during validation"):
            publication.export(self.repo, self.source, self.output, EDITION)
        self.assertEqual((self.output / self.names.html).read_bytes(), b"concurrent file")

    def test_excluded_links_are_rejected_even_without_download_attribute(self):
        bad_links = (
            self.names.validation, self.names.workbook, "old.html", "runtime.zip",
            "../private.docx", "file:///C:/private/source.xlsx",
            "https://example.invalid/" + self.names.validation,
            "https://example.invalid/record%2Exlsx", "data:application/zip;base64,AA==",
        )
        for link in bad_links:
            with self.subTest(link=link):
                self.assertIsNotNone(public_link_error(link, self.names))
                self.write_html(self.markup().replace("</body>", f'<a href="{link}">extra</a></body>'))
                with self.assertRaisesRegex(PublicationError, "publication.links"):
                    publication.validate_pair_policy(self.repo, self.source, "2.7.0", EDITION)

    def test_duplicate_href_rejected_before_export(self):
        raw = self.markup().replace(
            f'<a href="{self.names.participant}"',
            f'<a href="data:application/zip;base64,UEsFBgAAAAAAAAAAAAAAAAAAAAAAAA==" '
            f'href="{self.names.participant}"',
        )
        self.write_html(raw)
        with self.assertRaisesRegex(PublicationError, "duplicate attribute"):
            publication.export(self.repo, self.source, self.output, EDITION)
        self.validate_content.assert_not_called()
        self.assertFalse(self.output.exists())

    def test_duplicate_attributes_rejected_case_insensitively_on_both_tag_forms(self):
        attributes = (
            f'HREF="data:application/zip;base64,UEsFBgAAAAAAAAAAAAAAAAAAAAAAAA==" '
            f'href="{self.names.participant}" download',
            f'href="{self.names.participant}" DOWNLOAD="companion.zip" download=""',
            f'href="{self.names.participant}" download data-note="same" DATA-NOTE="same"',
        )
        original_anchor = f'<a href="{self.names.participant}" download>Word</a>'
        for attrs in attributes:
            for ending in (">Word</a>", " />"):
                with self.subTest(attrs=attrs, ending=ending):
                    self.write_html(self.markup().replace(original_anchor, f"<a {attrs}{ending}"))
                    with self.assertRaisesRegex(PublicationError, "duplicate attribute"):
                        publication.validate_pair_policy(self.repo, self.source, "2.7.0", EDITION)
        self.validate_content.assert_not_called()
        self.assertFalse(self.output.exists())

    def test_duplicate_attributes_fail_full_and_public_before_content_loading(self):
        original_anchor = f'<a href="{self.names.participant}" download>Word</a>'
        for public in (False, True):
            for ending in (">Word</a>", " />"):
                for attrs in (
                    f'HREF="data:application/zip;base64,AA==" href="{self.names.participant}" download',
                    f'href="{self.names.participant}" DOWNLOAD="companion.zip" download=""',
                ):
                    with self.subTest(public=public, ending=ending, attrs=attrs):
                        self.write_html(self.markup().replace(original_anchor, f"<a {attrs}{ending}"))
                        with patch.object(
                            html_validation, "load_context",
                            side_effect=AssertionError("invalid markup must fail before content loading"),
                        ) as load:
                            report = html_validation.validate(
                                self.repo, self.source, edition=EDITION, public_documents_only=public,
                            )
                        load.assert_not_called()
                        self.assertTrue(any(
                            check == "html.wellformed" and "duplicate attribute" in detail
                            for _, check, detail in report.failures
                        ), report.failures)

    def test_parser_keeps_first_duplicate_value_and_accepts_unambiguous_attributes(self):
        for ending in (">Word</a>", " />"):
            structure = html_validation.Structure()
            structure.feed(f'<a HREF="unsafe.zip" href="safe.docx"{ending}')
            structure.close()
            self.assertEqual(structure.root.children[0].attrs["href"], "unsafe.zip")
            self.assertTrue(any("duplicate attribute" in error for error in structure.errors))
        structure = html_validation.Structure()
        structure.feed(
            '<a HREF="#first" download>first</a><a href="#second" download>second</a>'
            '<img SRC="data:image/png;base64,AA==" alt="image" />'
            '<script>const sample = \'<a href="one" HREF="two">\';</script>'
        )
        structure.close()
        self.assertEqual(structure.errors, [])

    def test_relocated_word_package_rejected_before_export(self):
        companion = (self.source / self.names.participant).read_bytes()
        content_types = CONTENT_TYPES.replace(
            "</Types>",
            '<Override PartName="/word/packages/companion.docx" '
            'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document"/></Types>',
        )
        self.write_word(extra={
            "word/packages/companion.docx": companion,
            "word/_rels/document.xml.rels": relationships("package", "packages/companion.docx"),
            "[Content_Types].xml": content_types.encode("utf-8"),
        })
        self.write_html()
        with self.assertRaisesRegex(PublicationError, "embedded attachment"):
            publication.export(self.repo, self.source, self.output, EDITION)
        self.validate_content.assert_not_called()
        self.assertFalse(self.output.exists())

    def test_word_rejects_object_relationships_at_any_location(self):
        for prefix in (OFFICE_RELATIONSHIPS, "http://purl.oclc.org/ooxml/officeDocument/relationships"):
            for kind in ("package", "oleObject", "subDocument", "aFChunk", "control"):
                with self.subTest(prefix=prefix, kind=kind):
                    self.write_word(extra={
                        "custom/companion.payload": b"opaque attachment fixture",
                        "custom/_rels/holder.xml.rels": relationships(kind, "companion.payload", prefix=prefix),
                    })
                    errors = public_word_errors(self.source / self.names.participant, self.names)
                    self.assertTrue(any(
                        f"embedded attachment relationship {kind.casefold()}" in error for error in errors
                    ), errors)

    def test_word_rejects_object_markup_in_main_header_vml_and_typed_xml(self):
        word_ns = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
        strict_ns = "http://purl.oclc.org/ooxml/wordprocessingml/main"
        cases = (
            (None, '<w:object/>', None),
            (None, '<w:altChunk/>', None),
            (None, '<w:subDoc/>', None),
            ("word/header1.xml", f'<w:hdr xmlns:w="{word_ns}"><w:object/></w:hdr>', None),
            ("word/footer1.xml", f'<s:ftr xmlns:s="{strict_ns}"><s:subDoc/></s:ftr>', None),
            (
                "word/drawings/object.vml",
                '<xml xmlns:o="urn:schemas-microsoft-com:office:office"><o:OLEObject Type="Embed"/></xml>',
                None,
            ),
            (
                "custom/object.payload",
                f'<w:part xmlns:w="{word_ns}"><w:object/></w:part>',
                "application/xml",
            ),
        )
        for part, markup, content_type in cases:
            with self.subTest(part=part, markup=markup):
                extra = {part: markup.encode("utf-8")} if part else {}
                if content_type:
                    extra["[Content_Types].xml"] = CONTENT_TYPES.replace(
                        "</Types>", f'<Override PartName="/{part}" ContentType="{content_type}"/></Types>',
                    ).encode("utf-8")
                self.write_word(extra=extra, body_extra="" if part else markup)
                errors = public_word_errors(self.source / self.names.participant, self.names)
                self.assertTrue(any("embedded attachment markup" in error for error in errors), errors)

    def test_word_rejects_attachment_content_types_without_object_relationships(self):
        content_types = (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/vnd.openxmlformats-officedocument.oleObject",
            "application/vnd.ms-excel.sheet.binary.macroEnabled.12",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml",
            "application/pdf",
            "text/html",
        )
        for content_type in content_types:
            for kind in ("Default", "Override"):
                with self.subTest(content_type=content_type, kind=kind):
                    attribute = (
                        'Extension="payload"' if kind == "Default"
                        else 'PartName="/custom/companion.payload"'
                    )
                    declaration = f'<{kind} {attribute} ContentType="{content_type}"/>'
                    self.write_word(extra={
                        "custom/companion.payload": b"<part/>",
                        "[Content_Types].xml": CONTENT_TYPES.replace(
                            "</Types>", declaration + "</Types>",
                        ).encode("utf-8"),
                    })
                    errors = public_word_errors(self.source / self.names.participant, self.names)
                    self.assertTrue(any("embedded attachment content type" in error for error in errors), errors)

    def test_word_rejects_nested_packages_and_ole_with_generic_content_types(self):
        for blob in (
            (self.source / self.names.participant).read_bytes(),
            b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"OLE fixture",
        ):
            with self.subTest(signature=blob[:8]):
                self.write_word(extra={
                    "custom/renamed.bin": blob,
                    "[Content_Types].xml": CONTENT_TYPES.replace(
                        "</Types>", '<Default Extension="bin" ContentType="application/octet-stream"/></Types>',
                    ).encode("utf-8"),
                })
                errors = public_word_errors(self.source / self.names.participant, self.names)
                self.assertTrue(any("embedded attachment package/OLE bytes" in error for error in errors), errors)

    def test_word_rejects_additional_main_document_relationships(self):
        for source, target in (
            ("_rels/.rels", "word/other.xml"),
            ("word/_rels/document.xml.rels", "other.xml"),
        ):
            with self.subTest(source=source, target=target):
                self.write_word(extra={
                    source: relationships("officeDocument", target),
                    "word/other.xml": b"<other/>",
                })
                errors = public_word_errors(self.source / self.names.participant, self.names)
                self.assertTrue(any("embedded attachment subdocument relationship" in error for error in errors), errors)

    def test_word_allows_images_charts_and_escaped_object_examples(self):
        word_ns = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
        chart_ns = "http://schemas.openxmlformats.org/drawingml/2006/chart"
        drawing_ns = "http://schemas.openxmlformats.org/drawingml/2006/main"
        declarations = (
            '<Default Extension="png" ContentType="image/png"/>'
            '<Override PartName="/word/charts/chart1.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.drawingml.chart+xml"/>'
            '<Override PartName="/word/header1.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.header+xml"/>'
        )
        rels = (
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            f'<Relationship Id="rImage" Type="{OFFICE_RELATIONSHIPS}/image" Target="media/pixel.png"/>'
            f'<Relationship Id="rChart" Type="{OFFICE_RELATIONSHIPS}/chart" Target="charts/chart1.xml"/>'
            f'<Relationship Id="rHeader" Type="{OFFICE_RELATIONSHIPS}/header" Target="header1.xml"/>'
            '</Relationships>'
        )
        self.write_word(
            extra={
                "_rels/.rels": relationships("officeDocument", "word/document.xml"),
                "word/_rels/document.xml.rels": rels.encode("utf-8"),
                "word/charts/chart1.xml": f'<c:chartSpace xmlns:c="{chart_ns}"><c:chart/></c:chartSpace>'.encode("utf-8"),
                "word/header1.xml": f'<w:hdr xmlns:w="{word_ns}"><w:p/></w:hdr>'.encode("utf-8"),
                "word/media/pixel.png": base64.b64decode(
                    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/h0sAAAAASUVORK5CYII="
                ),
                "[Content_Types].xml": CONTENT_TYPES.replace("</Types>", declarations + "</Types>").encode("utf-8"),
            },
            body_extra=(
                '<w:p><w:r><w:t>&lt;w:object/&gt;</w:t></w:r></w:p>'
                f'<w:p><w:r><w:drawing xmlns:r="{OFFICE_RELATIONSHIPS}">'
                f'<a:blip xmlns:a="{drawing_ns}" r:embed="rImage"/>'
                f'<c:chart xmlns:c="{chart_ns}" r:id="rChart"/>'
                '</w:drawing></w:r></w:p>'
            ),
        )
        self.assertEqual(public_word_errors(self.source / self.names.participant, self.names), [])
        self.write_html()
        publication.validate_pair_policy(self.repo, self.source, "2.7.0", EDITION)

    def test_word_rejects_missing_or_invalid_content_types(self):
        self.write_word(extra={"[Content_Types].xml": b"<invalid/>"})
        errors = public_word_errors(self.source / self.names.participant, self.names)
        self.assertTrue(any("content-types manifest" in error for error in errors), errors)
        self.write_word()
        path = self.source / self.names.participant
        with zipfile.ZipFile(path) as archive:
            document = archive.read("word/document.xml")
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("word/document.xml", document)
        self.assertTrue(public_word_errors(path, self.names))

    def test_word_rejects_duplicate_parts_instead_of_choosing_one_copy(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            with zipfile.ZipFile(self.source / self.names.participant, "a") as archive:
                archive.writestr("word/document.xml", b"<another/>")
        errors = public_word_errors(self.source / self.names.participant, self.names)
        self.assertTrue(any("duplicate Word package parts" in error for error in errors), errors)

    def test_public_footer_rejects_wrong_edition_duplicates_and_restamping(self):
        original = self.markup()
        replacements = (
            original.replace(f'href="{self.names.participant}"', 'href="old.docx"'),
            original.replace('data-office-source="', 'data-office-source="../'),
            original.replace('data-office-release="', 'data-office-release="0'),
            original.replace(" download>", ' download="wrong.docx">'),
            original.replace(" sha256 ", " "),
            original.replace("</body>", f'<a href="{self.names.participant}" download>extra</a></body>'),
            original.replace(
                "</body>",
                f'<p data-office-source="{self.names.participant}" data-office-release="a"></p></body>',
            ),
            original.replace('content="public-documents-only"', 'content="full-authoring"'),
        )
        for raw in replacements:
            with self.subTest(raw=raw[-180:]), self.assertRaises(PublicationError):
                self.write_html(raw)
                publication.validate_pair_policy(self.repo, self.source, "2.7.0", EDITION)

    def test_word_rejects_hidden_companions_and_external_companion_links(self):
        rel = (
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            f'<Relationship Id="r1" Type="hyperlink" Target="{self.names.workbook}" TargetMode="External"/>'
            "</Relationships>"
        )
        self.write_word(extra={
            "word/embeddings/record.xlsx": b"hidden companion",
            "word/_rels/document.xml.rels": rel.encode("utf-8"),
        })
        errors = public_word_errors(self.source / self.names.participant, self.names)
        self.assertTrue(any("embedded attachment" in error for error in errors))
        self.assertTrue(any("excluded companion" in error for error in errors))

    def test_empty_edition_and_unsafe_filenames_are_rejected(self):
        for edition in ("", "../original", r"..\original"):
            with self.subTest(edition=edition), self.assertRaises(ValueError):
                publication.export(self.repo, self.source, self.output, edition)
        names = deliverable_names("../2.7.0", EDITION)
        with self.assertRaisesRegex(PublicationError, "unsafe public filename"):
            check_directory(self.output, names)

    def test_public_build_is_fresh_external_and_never_overwrites_originals(self):
        fresh = self.area / "build"
        self.assertEqual(prepare_public_build(self.repo, fresh, self.names, EDITION), fresh)
        fresh.mkdir()
        word = fresh / self.names.participant
        word.write_bytes(b"staged participant")
        self.assertEqual(prepare_public_build(self.repo, fresh, self.names, EDITION, html=True), fresh)
        with self.assertRaisesRegex(PublicationError, "overwrite"):
            prepare_public_build(self.repo, fresh, self.names, EDITION)
        (fresh / self.names.html).write_bytes(b"staged HTML")
        with self.assertRaisesRegex(PublicationError, "overwrite"):
            prepare_public_build(self.repo, fresh, self.names, EDITION, html=True)
        with self.assertRaisesRegex(PublicationError, "outside"):
            prepare_public_build(self.repo, self.repo / "docs", self.names, EDITION)

    def test_hardlinked_files_are_not_accepted(self):
        target = self.area / "linked"
        target.mkdir()
        os.link(self.source / self.names.participant, target / self.names.participant)
        with self.assertRaisesRegex(PublicationError, "regular file"):
            check_directory(target, self.names)

    def test_windows_reparse_points_are_rejected_before_resolving(self):
        original = Path.lstat
        alias = self.area / "junction"

        def lstat(path, *args, **kwargs):
            if path == alias:
                return SimpleNamespace(st_mode=stat.S_IFDIR, st_file_attributes=0x400)
            return original(path, *args, **kwargs)

        with patch.object(Path, "lstat", lstat), self.assertRaisesRegex(PublicationError, "reparse"):
            safe_path(alias / "public")

    def test_windows_aliases_and_alternate_streams_are_rejected_without_writes(self):
        for name in ("hashes.txt:stream", "export.", "export ", "NUL", "CON.txt"):
            with self.subTest(name=name), self.assertRaisesRegex(PublicationError, "Windows path"):
                safe_path(self.area / name)
        for namespace in (r"\\?\C:\publication", r"\\.\C:\publication"):
            with self.subTest(namespace=namespace), self.assertRaisesRegex(PublicationError, "namespaces"):
                safe_path(Path(namespace))


if __name__ == "__main__":
    unittest.main()
