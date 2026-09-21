"""Opt-in public mode preserves the full guide and the full-authoring default."""

from __future__ import annotations

import hashlib
import io
import json
import shutil
import sys
import unittest
import uuid
from contextlib import ExitStack, redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools" / "docs"))
sys.path.insert(0, str(ROOT / "tools" / "html"))

import build_docs
import validate_docs
from build_html import office_sources
from furusato_docs.context import load_context
from furusato_docs.deliverables import deliverable_names
from furusato_docs.facts import compute_facts
from furusato_docs.oox import StyleCarrier
from furusato_docs.parameters import PARAMETER_COLUMNS, build_parameter_rows
from furusato_docs.publication import PUBLIC_COVER, PUBLIC_NOTICE, PUBLIC_RECORD_NOTE, public_text_errors
from furusato_docs.tests10 import build_tests
from furusato_docs.validators import Report as WordReport
from furusato_html.capture import capture_participant_guide
from furusato_html.mirror import load_mirror, load_ui_strings
from furusato_html.model import Text, build_document
from furusato_html.page import _cover, _footer, _head
from sync_i18n import _strings
from validate_html import Report, Structure, check_office_sources

EDITION = "agent-quality-20260907"


def captured_text(builder):
    return "\n".join(text for node in builder.nodes for text, _ in _strings(node))


class PublicGuideContentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        originals = [
            path for path in (ROOT / "docs").iterdir()
            if path.suffix.lower() in {".docx", ".xlsx", ".html"}
        ] + [ROOT / "tools" / "docs" / "assets" / "style-carrier.zip"]
        cls.original_hashes = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in originals}
        cls.context = load_context(ROOT)
        facts = compute_facts(cls.context)
        cls.tests = build_tests(cls.context, facts)
        carrier = StyleCarrier.resolve(ROOT)
        cls.full = capture_participant_guide(cls.context, facts, cls.tests, carrier)
        cls.public = capture_participant_guide(
            cls.context, facts, cls.tests, carrier, public_documents_only=True
        )
        cls.text = captured_text(cls.public)

    def test_all_chapters_code_and_figures_are_preserved(self):
        for kind in ("heading", "code", "figure"):
            with self.subTest(kind=kind):
                self.assertEqual(
                    [node for node in self.full.nodes if node.kind == kind],
                    [node for node in self.public.nodes if node.kind == kind],
                )
        self.assertEqual(len([n for n in self.public.nodes if n.kind == "heading" and n["level"] == 1]), 24)

    def test_ten_questions_and_complete_rubrics_are_unchanged(self):
        self.assertEqual(len(self.tests), 10)
        for test in self.tests:
            with self.subTest(test=test.test_id):
                self.assertIn(test.question, self.text)
                rubric = f"{test.test_id} の評価基準"
                self.assertEqual(
                    [n for n in self.full.nodes if n.kind == "table" and n["caption"] == rubric],
                    [n for n in self.public.nodes if n.kind == "table" and n["caption"] == rubric],
                )
        for marker in ("10/10", "UNCLEAR は FAIL", "EXECUTION_ERROR", "10 問すべて"):
            self.assertIn(marker, self.text)

    def test_all_parameter_tables_and_defaults_are_preserved(self):
        full = [n for n in self.full.nodes if n.kind == "table" and n["headers"] == list(PARAMETER_COLUMNS)]
        public = [n for n in self.public.nodes if n.kind == "table" and n["headers"] == list(PARAMETER_COLUMNS)]
        self.assertEqual(len(full), 5)
        self.assertEqual(full, public)
        for key in self.context.notebooks:
            for row in build_parameter_rows(self.context, key):
                self.assertIn(row[0], self.text)

    def test_public_mode_has_record_instructions_not_mandatory_companions(self):
        self.assertEqual(public_text_errors(self.text), [])
        self.assertIn(PUBLIC_COVER, self.public.cover["footer_lines"])
        self.assertIn("実習用 Notebook・コード・データはこの文書ペアには同梱しません", self.text)
        self.assertIn("回答原本は保持", self.text)
        self.assertIn("質問・期待値・実行結果を Agent の設定へ転記しません", self.text)

    def test_public_validation_requires_complete_in_guide_rubrics_and_specifications(self):
        report = WordReport("captured public guide")
        validate_docs.check_in_guide_companions(self.text, self.context, self.tests, report)
        self.assertFalse(report.failures, report.failures)
        damaged = self.text.replace(self.tests[-1].question, "missing question")
        damaged = damaged.replace("STALE_LEASE_OWNER_RUN_ID", "missing parameter")
        report = WordReport("negative fixture")
        validate_docs.check_in_guide_companions(damaged, self.context, self.tests, report)
        failed = {finding.check for finding in report.failures}
        self.assertIn(f"publication.rubric.{self.tests[-1].test_id}", failed)
        self.assertIn("publication.parameterSpecifications", failed)

    def test_default_full_authoring_copy_has_not_changed(self):
        text = captured_text(self.full)
        self.assertNotIn(PUBLIC_NOTICE, text)
        self.assertNotIn(PUBLIC_RECORD_NOTE, text)
        self.assertNotIn(PUBLIC_COVER, self.full.cover["footer_lines"])
        self.assertIn("記録は別冊の Test 10 記録票を使用します", text)
        self.assertIn("このガイドと同じ配布版の処理仕様ワークブック", text)

    def test_both_mirrors_are_strict_complete_and_have_no_orphans(self):
        for public, capture in ((False, self.full), (True, self.public)):
            with self.subTest(public=public):
                mirror = load_mirror(public_documents_only=public)
                document = build_document(capture.nodes, mirror)
                self.assertEqual(len(document.sections), 24)
                self.assertFalse(mirror.unused())
                self.assertFalse(mirror.missing)

    def test_original_office_html_and_style_carrier_bytes_are_unchanged(self):
        self.assertEqual(
            {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in self.original_hashes},
            self.original_hashes,
        )


class PublicBuildInterfaceTests(unittest.TestCase):
    def setUp(self):
        self.area = ROOT / "tools" / "docs" / (".p" + uuid.uuid4().hex[:8])
        self.repo = self.area / "r"
        self.repo.mkdir(parents=True)
        self.addCleanup(shutil.rmtree, self.area)
        self.stage = self.area / "staging"
        self.context = SimpleNamespace(version="2.7.0", root=self.repo)
        self.facts = SimpleNamespace(observation=SimpleNamespace(calendar=None))
        self.names = deliverable_names("2.7.0", EDITION)
        self.old_bytes = {}
        for edition in ("", "deployment-review-20260905"):
            old = deliverable_names("2.7.0", edition)
            for name in (*old.office, old.html):
                path = self.repo / "docs" / name
                path.parent.mkdir(exist_ok=True)
                path.write_bytes(b"preserved original")
                self.old_bytes[path] = path.read_bytes()

    def tearDown(self):
        self.assertEqual({p: p.read_bytes() for p in self.old_bytes}, self.old_bytes)

    def build_mocks(self, stack):
        builder = SimpleNamespace(figures=[], tables=[], document=SimpleNamespace(paragraphs=[]))
        carrier = SimpleNamespace(
            source=str(self.repo / "tools" / "docs" / "assets" / "style-carrier.zip"),
            label_info=lambda: b"label",
        )

        def word(_context, _facts, _tests, _carrier, path, _scratch, **_kwargs):
            path.write_bytes(b"unit-test Word builder output")
            return builder

        def workbook(_context, path, *_args):
            path.write_bytes(b"unit-test workbook output")
            return {}

        values = {
            "repo_root": self.repo, "load_context": self.context, "compute_facts": self.facts,
            "build_tests": [], "runtime_fingerprint": {"fileCount": 1, "combinedSha256": "abc"},
        }
        for name, value in values.items():
            stack.enter_context(patch.object(build_docs, name, return_value=value))
        stack.enter_context(patch.object(build_docs.StyleCarrier, "resolve", return_value=carrier))
        guide = stack.enter_context(patch.object(build_docs.participant_guide, "build", side_effect=word))
        record = stack.enter_context(patch.object(build_docs.validation_doc, "build", side_effect=word))
        book = stack.enter_context(patch.object(build_docs.workbook, "build", side_effect=workbook))
        refresh = stack.enter_context(patch.object(
            build_docs, "refresh_with_word",
            return_value=SimpleNamespace(ok=True, detail="unit-test refresh", pages=1, words=1),
        ))
        excel = stack.enter_context(patch.object(build_docs, "refresh_with_excel"))
        stack.enter_context(patch.object(build_docs, "tidy_contents_tail", return_value=0))
        stack.enter_context(patch.object(build_docs, "apply_japanese_typography", return_value={}))
        stack.enter_context(patch.object(build_docs, "normalise_package_metadata", return_value={}))
        return guide, record, book, refresh, excel

    def test_public_cli_builds_and_refreshes_only_participant_word(self):
        with ExitStack() as stack, redirect_stdout(io.StringIO()) as stdout:
            guide, record, book, refresh, excel = self.build_mocks(stack)
            self.assertEqual(build_docs.main([
                "--out", str(self.stage), "--edition", EDITION, "--public-documents-only",
            ]), 0)
        report = json.loads(stdout.getvalue())
        self.assertTrue(report["publicDocumentsOnly"])
        self.assertNotIn("validationDocument", report)
        self.assertNotIn("workbook", report)
        self.assertNotIn("removedSuperseded", report)
        self.assertTrue(guide.call_args.kwargs["public_documents_only"])
        refresh.assert_called_once_with(self.stage / self.names.participant)
        record.assert_not_called()
        book.assert_not_called()
        excel.assert_not_called()
        self.assertEqual([p.name for p in self.stage.iterdir()], [self.names.participant])

    def test_full_authoring_cli_still_builds_all_three_with_original_names(self):
        with ExitStack() as stack, redirect_stdout(io.StringIO()) as stdout:
            guide, record, book, _, _ = self.build_mocks(stack)
            self.assertEqual(build_docs.main([
                "--out", str(self.stage), "--skip-word", "--skip-excel", "--keep-legacy",
            ]), 0)
        self.assertFalse(json.loads(stdout.getvalue())["publicDocumentsOnly"])
        self.assertFalse(guide.call_args.kwargs["public_documents_only"])
        record.assert_called_once()
        book.assert_called_once()
        self.assertEqual({p.name for p in self.stage.iterdir()}, set(deliverable_names("2.7.0").office))

    def test_public_word_never_overwrites_a_file_created_during_the_build(self):
        with ExitStack() as stack, redirect_stdout(io.StringIO()):
            guide, _, _, _, _ = self.build_mocks(stack)
            generate = guide.side_effect

            def concurrent(*args, **kwargs):
                result = generate(*args, **kwargs)
                (self.stage / self.names.participant).write_bytes(b"other build")
                return result

            guide.side_effect = concurrent
            with self.assertRaises(FileExistsError):
                build_docs.main([
                    "--out", str(self.stage), "--edition", EDITION, "--public-documents-only",
                ])
        self.assertEqual((self.stage / self.names.participant).read_bytes(), b"other build")
        self.assertEqual(len(list(self.stage.iterdir())), 1)

    def test_public_build_reports_final_bytes_even_if_word_refresh_fails(self):
        with ExitStack() as stack, redirect_stdout(io.StringIO()) as stdout:
            _, _, _, refresh, _ = self.build_mocks(stack)
            refresh.return_value = SimpleNamespace(ok=False, detail="unavailable", pages=None, words=None)

            def normalize(path):
                path.write_bytes(b"final metadata-restored bytes")
                return {"restored": True}

            build_docs.normalise_package_metadata.side_effect = normalize
            self.assertEqual(build_docs.main([
                "--out", str(self.stage), "--edition", EDITION, "--public-documents-only",
            ]), 0)
        report = json.loads(stdout.getvalue())
        self.assertFalse(report["wordRefresh"]["participantGuide"]["ok"])
        self.assertEqual(
            report["participantGuide"]["sha256"],
            hashlib.sha256((self.stage / self.names.participant).read_bytes()).hexdigest(),
        )

    def test_public_and_full_validation_dispatch_keep_distinct_checks(self):
        self.stage.mkdir()
        (self.stage / self.names.participant).write_bytes(b"unit-test participant fixture")
        all_checks = (
            "validate_final_runtime", "validate_toolchain", "validate_runtime_parity", "validate_guide",
            "validate_validation_doc", "validate_workbook", "validate_checklist", "validate_visual",
        )
        for public in (False, True):
            with self.subTest(public=public), ExitStack() as stack, redirect_stdout(io.StringIO()):
                for name, value in (
                    ("repo_root", self.repo), ("load_context", self.context),
                    ("compute_facts", self.facts), ("build_tests", []),
                ):
                    stack.enter_context(patch.object(validate_docs, name, return_value=value))
                mocks = {
                    name: stack.enter_context(patch.object(validate_docs, name, return_value=WordReport(name)))
                    for name in all_checks
                }
                args = ["--out", str(self.stage), "--edition", EDITION, "--json"]
                if public:
                    args.append("--public-documents-only")
                self.assertEqual(validate_docs.main(args), 0)
                expected = {"validate_toolchain", "validate_guide", "validate_visual"} if public else set(all_checks)
                self.assertEqual({name for name, check in mocks.items() if check.called}, expected)

    def test_public_office_hash_source_is_one_selected_file_not_three_or_fallback(self):
        self.stage.mkdir()
        word = self.stage / self.names.participant
        word.write_bytes(b"staged public Word")
        digests = office_sources(
            self.repo, "2.7.0", EDITION, public_documents_only=True, source_dir=self.stage
        )
        self.assertEqual(digests, {self.names.participant: hashlib.sha256(word.read_bytes()).hexdigest()})
        with self.assertRaisesRegex(SystemExit, "missing Office source"):
            office_sources(self.repo, "2.7.0", EDITION, source_dir=self.stage)
        with self.assertRaisesRegex(SystemExit, "missing Office source"):
            office_sources(self.repo, "2.7.0", "missing", public_documents_only=True)

    def test_public_cover_and_footer_have_exactly_one_real_download_and_hash(self):
        self.stage.mkdir()
        for public in (False, True):
            with self.subTest(public=public):
                for name in self.names.selected_office(public):
                    (self.stage / name).write_bytes(name.encode("ascii"))
                digests = office_sources(
                    self.repo, "2.7.0", EDITION, public_documents_only=public, source_dir=self.stage
                )
                ui = load_ui_strings(public_documents_only=public)
                ctx = SimpleNamespace(
                    ui=ui, version="2.7.0", fingerprint="build", runtime_fingerprint="runtime",
                    ui_text=lambda key: Text(ui[key]["ja"], ui[key]["en"]),
                    stats={
                        "entity_types": 10, "relationship_types": 15, "metadata_objects": 1,
                        "tests": 10, "edition": EDITION, "dataset_version": "unit-test", "css": "",
                        "office": digests, "download_guide": self.names.participant,
                        "public_documents_only": public,
                        **({} if public else {
                            "download_tests": self.names.validation, "download_workbook": self.names.workbook,
                        }),
                    },
                )
                raw = _head(ctx) + _cover(ctx, None) + _footer(ctx)
                structure = Structure()
                structure.feed(raw)
                structure.close()
                report = Report()
                check_office_sources(
                    report, structure.root, self.repo, "2.7.0", digests, EDITION,
                    public_documents_only=public, source_dir=self.stage,
                )
                self.assertFalse(report.failures, report.failures)
                self.assertEqual(raw.count("data-office-source="), 1 if public else 3)
                self.assertEqual(raw.count(" download>"), 1 if public else 3)
                if public:
                    self.assertIn('name="publication-mode" content="public-documents-only"', raw)
                    self.assertNotIn(self.names.validation, raw)
                    self.assertNotIn(self.names.workbook, raw)


if __name__ == "__main__":
    unittest.main()
