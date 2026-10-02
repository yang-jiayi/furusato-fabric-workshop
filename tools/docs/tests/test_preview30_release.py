"""Offline release-profile fixtures; no real Word, browser, cloud or publication."""

import copy
import hashlib
import io
import json
import shutil
import sys
import unittest
import uuid
import zipfile
from contextlib import ExitStack, redirect_stderr, redirect_stdout
from dataclasses import FrozenInstanceError, asdict, dataclass, replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "tools" / "docs"), str(ROOT / "tools" / "html"), str(Path(__file__).resolve().parent)]

import build_preview30 as builder
import package_preview30 as packager
import validate_preview30 as validator
from build_preview30_reports import report_payloads
from furusato_docs import preview30_acceptance as acceptance
from furusato_docs import preview30_content as content
from furusato_docs import preview30_evidence as private
from furusato_docs import preview30_public_evidence as public
from furusato_docs import preview30_release as release
from furusato_docs import preview30_reporting as reporting
from furusato_docs.validators import Report
from furusato_html import preview30 as html_renderer
from furusato_html.model import Document
from test_preview30_selected_reporting import synthetic_projection, synthetic_run

WORD_FIXTURE = b"Synthetic test sentinel, not an actual Word document."
HTML_FIXTURE = "<p>Synthetic renderer stub, not a workshop deliverable.</p>"


@dataclass
class SyntheticRefresh:
    ok: bool = True
    detail: str = "Synthetic fixture only; Word was not invoked"


def snapshot():
    data = synthetic_projection()
    run = synthetic_run(release.RELEASE_RUN_ID, all_pass=True)
    run["counts"] = dict(release.RELEASE_COUNTS)
    run["failureCounts"] = {"content": 1, "nativeAcceptance": 7}
    run["caseAggregates"][4]["counts"].update({"pass": 13, "fail": 1})
    run["caseAggregates"][9]["counts"].update({"pass": 0, "fail": 7})
    run["caseAggregates"][9].update(nativeGate=True, completedNativeResponse=False)
    data["originalSuiteRuns"][2] = run
    data["selectedOriginalSuiteRunId"] = run["id"]
    return data


class ReleaseProfileTests(unittest.TestCase):
    def setUp(self):
        self.work = ROOT / (".preview30-release-test-" + uuid.uuid4().hex)
        self.work.mkdir()
        self.addCleanup(shutil.rmtree, self.work)
        self.source, self.private = self.work / "source", self.work / "private"
        self.source.mkdir()
        self.private.mkdir()
        self.projection = self.source / release.V300.evidence_relative
        self.projection.parent.mkdir(parents=True)
        self.approval_path = self.private / "release-approval.json"
        self.data = snapshot()
        self.write_projection()
        self.approval = {
            "schemaVersion": release.APPROVAL_SCHEMA, "approved": True, "userAuthorized": True,
            "version": "3.0.0", "selectedOriginalSuiteRunId": release.RELEASE_RUN_ID,
            "evidenceProjectionSha256": packager.sha(self.projection.read_bytes()),
            "knownLimitationsAcknowledged": True, "originalCounts": dict(release.RELEASE_COUNTS),
        }
        self.write_approval()

    def write_projection(self):
        self.projection.write_text(json.dumps(self.data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def write_approval(self):
        self.approval_path.write_text(json.dumps(self.approval, indent=2) + "\n", encoding="utf-8")

    def resolve(self):
        return release.resolve_evidence(
            self.source, public_evidence_path=self.projection,
            release_profile=release.V300, release_approval=self.approval_path,
        )

    def metadata(self, profile=release.V300):
        evidence, binding = self.resolve()
        value = {
            "version": profile.version, "contentSha256": hashlib.sha256(b"synthetic shared source").hexdigest(),
            "counts": {"chapters": 24, "appendices": 5, "headings": 0, "tables": 0, "figures": 0, "tests": 10, "conditions": 84},
            "evidenceComplete": evidence["complete"], "evidenceScope": public.SCOPE,
            "labStates": {lab: row["status"] for lab, row in evidence["labs"].items()},
            "knownIssueLabs": [], "releaseFreezeStatus": evidence["freezeStatus"],
            "allFeaturesPassedClaimed": False, "finalUserAcceptanceCertified": False,
            "publicEvidenceProjectionSha256": evidence["projectionSha256"],
            "originalSuiteRuns": evidence["originalSuiteRuns"],
            **reporting.selection_metadata(evidence),
        }
        if profile.is_release:
            value["documentRelease"] = binding
        return value

    def model_stub(self, root, evidence_path, evaluation_path, **kwargs):
        profile = release.get_profile(kwargs["release_profile"])
        evidence, _ = release.resolve_evidence(root, evidence_path, evaluation_path, **kwargs)
        return Document([], [], [], []), None, None, None, evidence, self.metadata(profile)

    def minimal_html(self, metadata, profile):
        assets = SimpleNamespace(screenshots={}, screenshot_sizes={})
        with patch.object(html_renderer, "build_library", return_value=assets):
            with patch.object(html_renderer, "load_ui_strings", return_value={}):
                return html_renderer.render(
                    Document([], [], [], []), None, None, None, {"captures": {}},
                    metadata, packager.sha(WORD_FIXTURE), ROOT, release_profile=profile,
                )

    def inspect_html(self, source, metadata, profile):
        report = Report(target="synthetic HTML profile fixture")
        with patch.object(Path, "read_text", return_value=source):
            with patch.object(Path, "read_bytes", return_value=WORD_FIXTURE):
                with patch.object(Path, "is_file", return_value=True):
                    validator.inspect_html(
                        self.private / "pair", Document([], [], [], []), metadata, report,
                        release_profile=profile,
                    )
        return report

    def create_reports(self, profile):
        reports = self.source / profile.reports_relative
        reports.mkdir(parents=True, exist_ok=True)
        payloads = report_payloads(self.projection, root=self.source)
        payloads["SHA256SUMS.txt"] = "".join(
            f"{packager.sha(blob)}  {name}\n" for name, blob in sorted(payloads.items())
        ).encode("utf-8")
        for name, blob in payloads.items():
            (reports / name).write_bytes(blob)
        return reports

    def create_pair_receipt(self, profile):
        pair = self.private / ("pair-" + profile.name)
        pair.mkdir()
        (pair / profile.word_name).write_bytes(WORD_FIXTURE)
        (pair / profile.html_name).write_text(HTML_FIXTURE, encoding="utf-8")
        receipt = {
            "passedLocalChecks": True,
            "findings": [{"check": name, "level": "PASS"} for name in sorted(packager.REQUIRED_FULL_CHECKS)],
            "files": {file.name: packager.sha(file.read_bytes()) for file in pair.iterdir()},
            "documentIdentity": release.document_identity(self.metadata(profile), profile),
        }
        path = self.private / ("validation-" + profile.name + ".json")
        path.write_text(json.dumps(receipt), encoding="utf-8")
        return pair, path, receipt

    def create_attachments(self):
        directory = self.source / "workshop" / "v3.0.0-preview" / "attachments"
        directory.mkdir(parents=True)
        files = {}
        for name in packager.ATTACHMENTS:
            if name != "manifest.json":
                blob = ("Synthetic attachment test sentinel: " + name).encode("utf-8")
                (directory / name).write_bytes(blob)
                files[name] = {"sha256": packager.sha(blob)}
        (directory / "manifest.json").write_text(json.dumps({"files": files}), encoding="utf-8")

    def test_profiles_are_explicit_immutable_and_keep_legacy_names(self):
        self.assertIs(release.PREVIEW, release.get_profile())
        self.assertEqual(("3.0.0-preview", "Furusato Workshop 3.0 Preview"), (
            release.PREVIEW.version, release.PREVIEW.title,
        ))
        self.assertEqual(content.WORD_NAME, release.PREVIEW.word_name)
        self.assertEqual(content.HTML_NAME, release.PREVIEW.html_name)
        for module in (builder, validator, packager, html_renderer):
            self.assertEqual(content.WORD_NAME, module.WORD_NAME)
            self.assertEqual(content.HTML_NAME, module.HTML_NAME)
        self.assertEqual(packager.PACKAGE_NAME, "Furusato_Workshop_v3.0.0-preview_DRAFT.zip")
        self.assertEqual("Fabric_IQ_Ontology_Workshop_Furusato_Participant_v3.0.0.docx", release.V300.word_name)
        self.assertEqual("furusato-workshop-v3-0-0-complete.html", release.V300.html_name)
        self.assertEqual("Furusato_Workshop_v3.0.0.zip", release.V300.package_name)
        with self.assertRaises(FrozenInstanceError):
            release.V300.version = "GA"
        for value in ("latest", "3.0.0", None, [], replace(release.V300, version="GA")):
            with self.subTest(value=value), self.assertRaises(ValueError):
                release.get_profile(value)

    def test_valid_approval_keeps_current_and_historical_decisions_unmodified(self):
        before = self.projection.read_bytes()
        evidence, binding = self.resolve()
        self.assertEqual(self.data["originalSuiteRuns"], evidence["originalSuiteRuns"])
        self.assertEqual(before, self.projection.read_bytes())
        self.assertEqual(dict(release.RELEASE_COUNTS), binding["originalCounts"])
        self.assertEqual("workshop/v3.0.0-preview", binding["sourceAssetFolder"])
        self.assertEqual("docs/v3.0.0/guide", binding["publicGuideDirectory"])
        self.assertEqual("docs/v3.0.0/reports", binding["publicReportsDirectory"])
        self.assertTrue(binding["userAuthorized"])
        self.assertTrue(binding["knownLimitationsAcknowledged"])
        for key in ("originalSuiteAccepted", "aiAnswerQualityAccepted", "mainPromoted",
                    "allFeaturesPassedClaimed", "generalAvailabilityClaimed", "finalUserAcceptanceCertified"):
            self.assertIs(False, binding[key])
        self.assertFalse(evidence["complete"])
        self.assertEqual(26, sum(item.get("completionRequired", True) for item in private.requests()))
        text = json.dumps(binding)
        self.assertNotIn(str(self.private), text)
        self.assertNotIn("release-approval.json", text)
        public.public_strings(binding, "release metadata")

    def test_wrong_missing_or_private_approval_fields_are_rejected(self):
        original = copy.deepcopy(self.approval)
        mutations = [
            lambda a: a.pop("knownLimitationsAcknowledged"),
            lambda a: a.update(approved=False),
            lambda a: a.update(approved=1),
            lambda a: a.update(userAuthorized=False),
            lambda a: a.update(knownLimitationsAcknowledged=False),
            lambda a: a.update(version="3.0.0-preview"),
            lambda a: a.update(schemaVersion=acceptance.APPROVAL_SCHEMA),
            lambda a: a.update(selectedOriginalSuiteRunId="synthetic-newer"),
            lambda a: a.update(evidenceProjectionSha256="0" * 64),
            lambda a: a["originalCounts"].update({"pass": 84, "fail": 0}),
            lambda a: a["originalCounts"].update({"blocked": False}),
            lambda a: a["originalCounts"].pop("notApplicable"),
            lambda a: a.update(privatePath=str(self.private)),
        ]
        for mutate in mutations:
            self.approval = copy.deepcopy(original)
            mutate(self.approval)
            self.write_approval()
            with self.subTest(mutate=mutate), self.assertRaises(ValueError):
                self.resolve()

    def test_duplicate_approval_keys_and_source_owned_approval_are_rejected(self):
        self.approval_path.write_text(
            json.dumps(self.approval).replace('"approved": true', '"approved": false, "approved": true'),
            encoding="utf-8",
        )
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            self.resolve()
        self.write_approval()
        source_approval = self.source / "approval.json"
        source_approval.write_bytes(self.approval_path.read_bytes())
        with self.assertRaisesRegex(ValueError, "external private"):
            release.resolve_evidence(self.source, release_profile=release.V300, release_approval=source_approval)

    def test_projection_is_explicit_source_owned_and_hash_bound(self):
        self.projection.write_bytes(self.projection.read_bytes() + b"\n")
        with self.assertRaisesRegex(ValueError, "exact projection"):
            self.resolve()
        self.write_projection()
        for path in (self.private / "manifest.json", self.source / public.DEFAULT_RELATIVE,
                     self.source / "docs" / "assets" / "other" / "manifest.json"):
            with self.subTest(path=path), self.assertRaisesRegex(ValueError, "docs/assets/v3.0.0-evidence"):
                release.resolve_evidence(
                    self.source, public_evidence_path=path, release_profile=release.V300,
                    release_approval=self.approval_path,
                )
        explicit = self.resolve()
        implicit = release.resolve_evidence(self.source, release_profile="v3.0.0", release_approval=self.approval_path)
        self.assertEqual(explicit, implicit)

    def test_release_is_not_permission_to_select_another_run_or_change_results(self):
        original = copy.deepcopy(self.data)
        for mutate in (
            lambda d: d.pop("selectedOriginalSuiteRunId"),
            lambda d: d.update(selectedOriginalSuiteRunId="synthetic-newer"),
            lambda d: d["originalSuiteRuns"][2].update(promoted=True),
            lambda d: d["originalSuiteRuns"][2].update(accepted=True),
            lambda d: d.update(approved=False),
        ):
            self.data = copy.deepcopy(original)
            mutate(self.data)
            self.write_projection()
            self.approval["evidenceProjectionSha256"] = packager.sha(self.projection.read_bytes())
            self.write_approval()
            with self.subTest(mutate=mutate), self.assertRaises(ValueError):
                self.resolve()
        self.data = original
        run = self.data["originalSuiteRuns"][2]
        run["counts"].update({"pass": 77, "fail": 7})
        run["caseAggregates"][4]["counts"].update({"pass": 14, "fail": 0})
        run["failureCounts"]["content"] = 0
        self.write_projection()
        self.approval.update(evidenceProjectionSha256=packager.sha(self.projection.read_bytes()), originalCounts=run["counts"])
        self.write_approval()
        with self.assertRaisesRegex(ValueError, "76 PASS/8 FAIL"):
            self.resolve()

    def test_private_overrides_or_an_approval_on_default_profile_are_not_ignored(self):
        for kwargs in ({"evidence_path": Path("private.json")}, {"evaluation_path": Path("private.json")}):
            with self.subTest(kwargs=kwargs), self.assertRaisesRegex(ValueError, "without private overrides"):
                release.resolve_evidence(
                    self.source, release_profile=release.V300, release_approval=self.approval_path, **kwargs,
                )
        with self.assertRaisesRegex(ValueError, "requires --release-profile"):
            release.resolve_evidence(self.source, release_approval=self.approval_path)

    def test_all_three_entrypoints_stop_before_model_or_output_for_missing_or_wrong_approval(self):
        pair, review, output = (self.private / name for name in ("pair", "review", "package"))
        receipt = self.private / "validation.json"
        for approved_path in (None, self.approval_path):
            self.approval["evidenceProjectionSha256"] = "0" * 64
            self.write_approval()
            flags = ["--release-profile", "v3.0.0"]
            if approved_path:
                flags += ["--release-approval", str(approved_path)]
            operations = (
                (builder, lambda: builder.main(["--out", str(pair), "--review", str(review), *flags])),
                (validator, lambda: validator.main(["--pair", str(pair), "--review", str(review), *flags])),
                (packager, lambda: packager.package(
                    pair, receipt, output, None, release_profile=release.V300, release_approval=approved_path,
                )),
            )
            for module, operation in operations:
                with self.subTest(module=module.__name__, approval=bool(approved_path)):
                    with patch.object(module, "ROOT", self.source), patch.object(content, "load_context") as load:
                        with self.assertRaises(ValueError):
                            operation()
                        load.assert_not_called()
                    self.assertFalse(any(path.exists() for path in (pair, review, output, receipt)))

    def test_full_shared_models_preserve_legacy_content_runtime_profiles_and_ledgers(self):
        context = content.load_context(ROOT, document_edition="unified-20260923", source_version="2.7.0")
        carrier = content.StyleCarrier.resolve(ROOT)
        runtime_sections = content.runtime_candidate_sections
        with patch.object(content, "load_context", return_value=context):
            with patch.object(content.StyleCarrier, "resolve", return_value=carrier):
                with patch.object(content, "runtime_candidate_sections", side_effect=lambda sections, root: runtime_sections(sections, ROOT)):
                    preview = content.build(self.source, public_evidence_path=self.projection)
                    current = content.build(
                        self.source, public_evidence_path=self.projection,
                        release_profile=release.V300, release_approval=self.approval_path,
                    )
        before, after = asdict(preview[0]), asdict(current[0])
        notice = after["sections"][0]["blocks"].pop(0)["payload"]["text"]["en"]
        self.assertIn("user-authorized", notice)
        self.assertIn("76 PASS/8 FAIL", notice)
        self.assertIn("--require-acceptance", notice)
        self.assertEqual(before, after)
        self.assertEqual(preview[-1]["counts"], current[-1]["counts"])
        self.assertEqual((10, 84), tuple(current[-1]["counts"][key] for key in ("tests", "conditions")))
        self.assertEqual("2.7.0", current[-1]["baselineVersion"])
        self.assertEqual(self.data["originalSuiteRuns"], current[-1]["originalSuiteRuns"])
        self.assertEqual("preview", current[-1]["finalEvaluation"]["method"]["runtime"])
        self.assertIn("workshop/v3.0.0-preview", json.dumps(after))
        self.assertNotIn("documentRelease", preview[-1])
        self.assertEqual("3.0.0", current[-1]["version"])
        mcp = next(section for section in current[0].walk() if section.ident == "ch-20-10")
        self.assertFalse(mcp.children)
        self.assertEqual("callout", mcp.blocks[-3].kind)
        self.assertTrue(all(block.kind == "paragraph" for block in mcp.blocks[-2:]))
        self.assertEqual([
            "https://learn.microsoft.com/fabric/data-science/fabric-data-agent-sdk",
            "https://learn.microsoft.com/fabric/data-science/consume-data-agent-python",
        ], [block["text"].en for block in mcp.blocks[-2:]])

    def test_default_and_explicit_preview_model_metadata_are_identical(self):
        with patch.object(public, "resolve", return_value=private.load()):
            default = content.build(ROOT)
            explicit = content.build(ROOT, release_profile="preview")
        self.assertEqual(asdict(default[0]), asdict(explicit[0]))
        self.assertEqual(default[-1], explicit[-1])
        self.assertIn("48 PASS/36 FAIL", default[0].sections[0].blocks[0]["text"].en)
        self.assertEqual(packager.START_HERE, packager.start_here(default[-1]))

    def test_word_cover_and_core_metadata_use_profile_without_rendering_a_document(self):
        for profile in (release.PREVIEW, release.V300):
            metadata = self.metadata(profile)
            target = self.private / profile.word_name
            fake = MagicMock()
            fake.document.styles = []
            fake.document.paragraphs = []
            fake.figures = fake.tables = []
            with self.subTest(profile=profile.name), patch.object(builder, "DocumentBuilder", return_value=fake):
                with patch.object(builder, "cover_page") as cover, patch.object(builder, "apply_package_metadata") as core:
                    builder.write_word(
                        Document([], [], [], []), None, MagicMock(), {"captures": {}}, metadata,
                        target, self.private, release_profile=profile,
                    )
            self.assertEqual(profile.title, cover.call_args.kwargs["title"])
            self.assertEqual(profile.version, cover.call_args.kwargs["version"])
            self.assertEqual(profile.title + " — participant guide", core.call_args.kwargs["title"])
            self.assertEqual(
                builder.ascii_parentheses(release.presentation(metadata, profile)["ja"]),
                core.call_args.kwargs["subject"],
            )
            self.assertNotRegex(core.call_args.kwargs["subject"], "[（）]")
            self.assertIn("Preview", core.call_args.kwargs["keywords"])
            self.assertFalse(target.exists())

    def test_html_titles_local_word_links_and_provenance_for_both_profiles(self):
        for profile in (release.PREVIEW, release.V300):
            metadata = self.metadata(profile)
            source = self.minimal_html(metadata, profile)
            with self.subTest(profile=profile.name):
                self.assertIn("<title>" + profile.title + "</title>", source)
                self.assertIn(f'<a download href="{profile.word_name}"', source)
                self.assertIn(f"<h1>Furusato Workshop<br>{profile.display_version}</h1>", source)
                self.assertNotIn(str(self.private), source)
                report = self.inspect_html(source, metadata, profile)
                self.assertTrue(report.passed, report.failures)
                if profile.is_release:
                    self.assertIn("76 PASS/8 FAIL", source)
                    self.assertIn("product features remain Preview", source)
                    self.assertIn("User-authorized document release 3.0.0", source)

    def test_head_title_is_not_confused_with_accessible_svg_figure_titles(self):
        for profile in (release.PREVIEW, release.V300):
            metadata = self.metadata(profile)
            source = self.minimal_html(metadata, profile)
            svg = '<svg role="img" aria-labelledby="figure-title"><title id="figure-title">Diagram title</title></svg>'
            source = source.replace('<main id="main">', '<main id="main">' + svg)
            with self.subTest(profile=profile.name):
                report = self.inspect_html(source, metadata, profile)
                self.assertTrue(report.passed, report.failures)
                head_title = "<title>" + profile.title + "</title>"
                for replacement in ("", head_title + head_title, "<title>Wrong edition</title>"):
                    report = self.inspect_html(source.replace(head_title, replacement), metadata, profile)
                    self.assertIn("html.documentTitle", [finding.check for finding in report.failures])

    def test_reference_spacing_fix_is_release_and_english_print_only(self):
        preview = self.minimal_html(self.metadata(release.PREVIEW), release.PREVIEW)
        current = self.minimal_html(self.metadata(), release.V300)
        self.assertNotIn(html_renderer.RELEASE_PRINT_CSS, preview)
        self.assertIn(html_renderer.RELEASE_PRINT_CSS, current)
        self.assertIn('@media print', html_renderer.RELEASE_PRINT_CSS)
        self.assertEqual(2, html_renderer.RELEASE_PRINT_CSS.count('html[data-lang="en"] #ch-20-10'))
        self.assertIn('margin-bottom:2mm', html_renderer.RELEASE_PRINT_CSS)
        self.assertIn('margin-block:0', html_renderer.RELEASE_PRINT_CSS)
        for forbidden in ("display", "visibility", "overflow", "font-size", "height", "break-before"):
            self.assertNotIn(forbidden, html_renderer.RELEASE_PRINT_CSS)

    def test_validator_rejects_wrong_title_link_profile_or_selected_provenance(self):
        metadata = self.metadata()
        original = self.minimal_html(metadata, release.V300)
        for old, new, expected in (
            ("<title>Furusato Workshop 3.0.0</title>", "<title>Furusato Workshop 3.0 Preview</title>", "html.documentTitle"),
            (f'href="{release.V300.word_name}"', 'href="../private.docx"', "html.exactWordLink"),
            ('"profile": "v3.0.0"', '"profile": "preview"', "html.documentProfile"),
            ('"wordFilename": "' + release.V300.word_name + '"', '"wordFilename": "other.docx"', "html.profileFilenames"),
            ('"publicEvidenceProjectionSha256": "' + metadata["publicEvidenceProjectionSha256"] + '"',
             '"publicEvidenceProjectionSha256": "' + "0" * 64 + '"', "html.selectedProjection"),
        ):
            with self.subTest(expected=expected):
                self.assertIn(old, original)
                report = self.inspect_html(original.replace(old, new), metadata, release.V300)
                self.assertIn(expected, [finding.check for finding in report.failures])

    def test_renderers_reject_metadata_for_the_other_profile(self):
        metadata = self.metadata()
        with self.assertRaisesRegex(ValueError, "explicit release profile"):
            self.minimal_html(metadata, release.PREVIEW)
        with patch.object(builder, "DocumentBuilder") as word:
            with self.assertRaisesRegex(ValueError, "explicit release profile"):
                builder.write_word(Document([], [], [], []), None, None, {}, metadata,
                                   self.private / "absent.docx", self.private)
            word.assert_not_called()

    def test_builder_threads_both_profiles_using_only_renderer_stubs(self):
        for profile in (release.PREVIEW, release.V300):
            pair = self.private / ("built-pair-" + profile.name)
            review = self.private / ("build-review-" + profile.name)
            args = ["--out", str(pair), "--review", str(review), "--public-evidence", str(self.projection)]
            if profile.is_release:
                args += ["--release-profile", profile.name, "--release-approval", str(self.approval_path)]
            else:
                args += ["--skip-word"]
            def fake_word(document, context, carrier, evidence, metadata, target, review, **kwargs):
                target.write_bytes(WORD_FIXTURE)
                return {"syntheticFixtureOnly": True}
            with self.subTest(profile=profile.name), ExitStack() as stack:
                stack.enter_context(patch.object(builder, "ROOT", self.source))
                stack.enter_context(patch.object(builder, "build", side_effect=self.model_stub))
                word = stack.enter_context(patch.object(builder, "write_word", side_effect=fake_word))
                html = stack.enter_context(patch.object(builder, "render_html", return_value=HTML_FIXTURE))
                stack.enter_context(patch.object(builder, "refresh_with_word", return_value=SyntheticRefresh()))
                stack.enter_context(patch.object(builder, "tidy_contents_tail", return_value=0))
                stack.enter_context(patch.object(builder, "apply_japanese_typography", return_value={}))
                stack.enter_context(patch.object(builder, "normalise_package_metadata", return_value={}))
                stack.enter_context(redirect_stdout(io.StringIO()))
                self.assertEqual(0, builder.main(args))
            self.assertEqual({profile.word_name, profile.html_name}, {file.name for file in pair.iterdir()})
            self.assertEqual(profile, word.call_args.kwargs["release_profile"])
            self.assertEqual(profile, html.call_args.kwargs["release_profile"])
            report = json.loads((review / "build.json").read_text(encoding="utf-8"))
            self.assertEqual(release.document_identity(self.metadata(profile), profile), report["documentIdentity"])
            if profile.is_release:
                self.assertNotIn("draft", report["status"])
                self.assertFalse(report["aiAnswerQualityAccepted"])

    def test_release_cannot_use_unrefreshed_word_or_waive_requested_full_evidence(self):
        pair, review = self.private / "pair", self.private / "review"
        args = ["--out", str(pair), "--review", str(review), "--release-profile", "v3.0.0",
                "--release-approval", str(self.approval_path)]
        for flag in ("--skip-word", "--require-evidence"):
            with self.subTest(flag=flag), patch.object(builder, "ROOT", self.source):
                with patch.object(builder, "build", side_effect=self.model_stub):
                    with self.assertRaises(SystemExit), redirect_stderr(io.StringIO()):
                        builder.main([*args, flag])
            self.assertFalse(pair.exists())
            self.assertFalse(review.exists())

    def test_validation_receipt_tracks_profile_even_when_more_local_checks_are_needed(self):
        for profile in (release.PREVIEW, release.V300):
            pair, _, _ = self.create_pair_receipt(profile)
            review = self.private / ("checked-" + profile.name)
            args = ["--pair", str(pair), "--review", str(review), "--public-evidence", str(self.projection)]
            if profile.is_release:
                args += ["--release-profile", "v3.0.0", "--release-approval", str(self.approval_path)]
            with self.subTest(profile=profile.name), ExitStack() as stack:
                stack.enter_context(patch.object(validator, "ROOT", self.source))
                stack.enter_context(patch.object(validator, "build", side_effect=self.model_stub))
                inspections = [stack.enter_context(patch.object(validator, name)) for name in (
                    "inspect_word", "inspect_html", "check_capture_fidelity",
                )]
                stack.enter_context(redirect_stdout(io.StringIO()))
                self.assertEqual(0, validator.main(args))
            receipt = json.loads((review / "validation.json").read_text(encoding="utf-8"))
            self.assertEqual(release.document_identity(self.metadata(profile), profile), receipt["documentIdentity"])
            self.assertTrue(all(mock.call_args.kwargs["release_profile"] == profile for mock in inspections))
            if profile.is_release:
                self.assertEqual("more-local-validation-required", receipt["status"])
            with self.assertRaisesRegex(ValueError, "Full Word"):
                packager.require_full_validation(receipt)

    def test_receipt_cannot_mix_profile_source_run_projection_or_counts(self):
        metadata = self.metadata()
        valid = {"documentIdentity": release.document_identity(metadata, release.V300)}
        release.require_validation_identity(valid, metadata, release.V300)
        mutations = (
            lambda v: v.pop("documentIdentity"),
            lambda v: v["documentIdentity"].update(releaseProfile="preview"),
            lambda v: v["documentIdentity"].update(sourceAssetProfile="v3.0.0"),
            lambda v: v["documentIdentity"].update(selectedOriginalSuiteRunId="synthetic-newer"),
            lambda v: v["documentIdentity"].update(publicEvidenceProjectionSha256="0" * 64),
            lambda v: v["documentIdentity"].update(contentSha256="0" * 64),
            lambda v: v["documentIdentity"]["documentRelease"]["originalCounts"].update({"pass": 84, "fail": 0}),
        )
        for mutate in mutations:
            receipt = copy.deepcopy(valid)
            mutate(receipt)
            with self.subTest(mutate=mutate), self.assertRaisesRegex(ValueError, "package inputs disagree"):
                release.require_validation_identity(receipt, metadata, release.V300)
        release.require_validation_identity({}, self.metadata(release.PREVIEW))
        with self.assertRaises(ValueError):
            release.require_validation_identity(valid, self.metadata(release.PREVIEW))

    def test_pair_allowlist_hashes_and_profile_receipt_are_required(self):
        for profile in (release.PREVIEW, release.V300):
            pair, path, receipt = self.create_pair_receipt(profile)
            with self.subTest(profile=profile.name):
                packager.load_validated_inputs(pair, path, release_profile=profile)
                if profile.is_release:
                    receipt.pop("documentIdentity")
                    path.write_text(json.dumps(receipt), encoding="utf-8")
                    with self.assertRaisesRegex(ValueError, "release profile"):
                        packager.load_validated_inputs(pair, path, release_profile=profile)
                    receipt["documentIdentity"] = release.document_identity(self.metadata(), release.V300)
                    path.write_text(json.dumps(receipt), encoding="utf-8")
                (pair / profile.word_name).write_bytes(WORD_FIXTURE + b" changed")
                with self.assertRaisesRegex(ValueError, "changed since"):
                    packager.load_validated_inputs(pair, path, release_profile=profile)
                (pair / "private.json").write_text("{}", encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "exact two-file"):
                    packager.load_validated_inputs(pair, path, release_profile=profile)

    def test_report_scope_is_narrow_and_legacy_report_scope_remains_available(self):
        metadata = self.metadata()
        reports = self.create_reports(release.V300)
        self.assertEqual(4, len(packager.collect_public_reports(metadata, root=self.source, release_profile=release.V300)))
        for path in (self.source / "docs" / "v3-preview" / "reports",
                     reports.parent / "guide", reports / ".." / "other", self.private):
            with self.subTest(path=path), self.assertRaisesRegex(ValueError, "docs/v3.0.0/reports"):
                packager.collect_public_reports(metadata, root=self.source, reports_path=path, release_profile=release.V300)
        self.create_reports(release.PREVIEW)
        self.assertEqual(4, len(packager.collect_public_reports(self.metadata(release.PREVIEW), root=self.source)))
        with self.assertRaisesRegex(ValueError, "docs/v3-preview"):
            packager.collect_public_reports(self.metadata(release.PREVIEW), root=self.source, reports_path=reports)
        outside = self.private / "external-report.md"
        outside.write_text("private fixture", encoding="utf-8")
        original_resolve = Path.resolve
        def redirected(path, *args, **kwargs):
            return outside if path == reports / "evaluation-report.md" else original_resolve(path, *args, **kwargs)
        with patch.object(Path, "resolve", redirected):
            with self.assertRaisesRegex(ValueError, "inside the approved reports"):
                packager.collect_public_reports(metadata, root=self.source, release_profile=release.V300)

    def test_package_and_status_bind_actual_inputs_without_changing_default_draft_semantics(self):
        self.create_attachments()
        for profile in (release.PREVIEW, release.V300):
            self.create_reports(profile)
            pair, path, validation = self.create_pair_receipt(profile)
            output = self.private / ("package-" + profile.name)
            with self.subTest(profile=profile.name), ExitStack() as stack:
                stack.enter_context(patch.object(packager, "ROOT", self.source))
                stack.enter_context(patch.object(packager, "build", side_effect=self.model_stub))
                for name in ("inspect_word", "inspect_html", "check_capture_fidelity"):
                    stack.enter_context(patch.object(packager, name))
                result = packager.package(
                    pair, path, output, None, public_evidence_path=self.projection,
                    release_profile=profile, release_approval=self.approval_path if profile.is_release else None,
                )
            self.assertEqual(profile.package_name, result["archive"])
            self.assertEqual(profile.kind, result["kind"])
            with zipfile.ZipFile(output / profile.package_name) as archive:
                names = set(archive.namelist())
                self.assertIn("guide/" + profile.word_name, names)
                self.assertIn("guide/" + profile.html_name, names)
                self.assertIn(profile.status_name, names)
                state = json.loads(archive.read(profile.status_name))
                self.assertEqual(profile.version, state["edition"])
                self.assertEqual(self.data["originalSuiteRuns"], state["approvedOriginalSuiteAggregates"])
                self.assertFalse(state["aiAnswerQualityAccepted"])
                self.assertFalse(state["mainPromoted"])
                self.assertFalse(state["finalUserAcceptanceCertified"])
                self.assertFalse(state["liveVerificationCertified"])
                self.assertNotIn(str(self.private), archive.read(profile.status_name).decode("utf-8"))
                self.assertNotIn("release-approval.json", "\n".join(names))
                if profile.is_release:
                    self.assertNotIn("DRAFT_STATUS.json", names)
                    self.assertEqual(validation["documentIdentity"], state["documentIdentity"])
                    self.assertEqual(state["documentIdentity"], result["documentIdentity"])
                    self.assertEqual(dict(release.RELEASE_COUNTS), state["documentRelease"]["originalCounts"])
                    self.assertTrue(state["documentRelease"]["userAuthorized"])
                    self.assertIn("known limitations", archive.read("START_HERE.txt").decode("utf-8"))
                else:
                    self.assertEqual("furusato-local-draft-package/v1", state["schemaVersion"])
                    self.assertEqual("DRAFT", state["kind"])
                    self.assertNotIn("documentRelease", state)

    def test_packaging_rejects_mismatched_identity_before_recheck_or_archive(self):
        pair, path, receipt = self.create_pair_receipt(release.V300)
        receipt["documentIdentity"]["sourceAssetFolder"] = "workshop/v3.0.0"
        path.write_text(json.dumps(receipt), encoding="utf-8")
        output = self.private / "package"
        with patch.object(packager, "ROOT", self.source), patch.object(packager, "build", side_effect=self.model_stub):
            with patch.object(packager, "inspect_word") as inspect:
                with self.assertRaisesRegex(ValueError, "package inputs disagree"):
                    packager.package(pair, path, output, None, release_profile="v3.0.0",
                                     release_approval=self.approval_path)
                inspect.assert_not_called()
        self.assertFalse(output.exists())

    def test_known_limitations_approval_never_satisfies_strict_acceptance(self):
        strict = {
            "schemaVersion": acceptance.APPROVAL_SCHEMA, "selectedOriginalSuiteRunId": release.RELEASE_RUN_ID,
            "evidenceSha256": self.approval["evidenceProjectionSha256"], "finalPublicationApproved": True,
            "reviewer": "synthetic-review", "reviewedAt": "2026-10-02T00:00:00Z",
        }
        strict_path = self.private / "strict-approval.json"
        strict_path.write_text(json.dumps(strict), encoding="utf-8")
        self.resolve()
        with self.assertRaisesRegex(ValueError, "original-zero-fail"):
            acceptance.require_public_acceptance(self.projection, strict_path, root=self.source)
        pair, review, output = (self.private / name for name in ("pair", "review", "package"))
        with patch.object(builder, "ROOT", self.source), patch.object(builder, "build") as build:
            with self.assertRaisesRegex(ValueError, "Final publication acceptance blocked"):
                builder.main([
                    "--out", str(pair), "--review", str(review), "--release-profile", "v3.0.0",
                    "--release-approval", str(self.approval_path), "--require-acceptance",
                    "--acceptance-approval", str(strict_path),
                ])
            build.assert_not_called()
        with patch.object(packager, "ROOT", self.source), patch.object(packager, "build") as build:
            with self.assertRaisesRegex(ValueError, "Final publication acceptance blocked"):
                packager.package(
                    pair, self.private / "validation.json", output, None, release_profile=release.V300,
                    release_approval=self.approval_path, require_acceptance=True, acceptance_approval=strict_path,
                )
            build.assert_not_called()
        self.assertFalse(any(path.exists() for path in (pair, review, output)))


if __name__ == "__main__":
    unittest.main()
