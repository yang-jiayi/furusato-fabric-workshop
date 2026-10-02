"""v3-specific gates in addition to (not replacing) the original guide tests."""

import copy
import json
import sys
import unittest
from collections import Counter
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "tools" / "docs"), str(ROOT / "tools" / "html")]

from furusato_docs import preview30_content as content
from furusato_docs import preview30_evidence as evidence
from furusato_docs.facts import compute_facts
from furusato_docs.tests10 import build_tests
from furusato_html.capture import capture_participant_guide
from furusato_html.mirror import load_mirror
from furusato_html.model import build_document
from package_preview30 import require_full_validation, REQUIRED_FULL_CHECKS
from import_preview30_evidence import capture_caption


def signature(block):
    value = copy.deepcopy(asdict(block))
    value["payload"].pop("number", None)
    value["payload"].pop("widths", None)
    value["payload"].pop("word_layout", None)
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


class Preview30ContentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with patch.object(content.preview30_public_evidence, "resolve", return_value=evidence.load()):
            cls.doc, cls.context, cls.facts, cls.carrier, cls.evidence, cls.meta = content.build(ROOT)
        cls.tests10 = build_tests(cls.context, cls.facts)
        captured = capture_participant_guide(cls.context, cls.facts, cls.tests10, cls.carrier, public_documents_only=True)
        cls.original = build_document(captured.nodes, load_mirror(public_documents_only=True, context=cls.context))

    def test_approved_structure_and_original_rubric(self):
        self.assertEqual(list(range(1, 25)), [s.chapter for s in self.doc.sections[:24]])
        self.assertEqual(list("ABCDE"), [s.appendix for s in self.doc.sections[24:]])
        self.assertEqual(24, self.meta["counts"]["chapters"])
        self.assertEqual(5, self.meta["counts"]["appendices"])
        self.assertEqual(10, self.meta["counts"]["tests"])
        self.assertEqual(84, self.meta["counts"]["conditions"])

    def test_all_original_prose_tables_and_code_preserved(self):
        expected = Counter(
            signature(b) for s in self.original.walk() for b in s.blocks
            if b.kind != "figure" or b["source_kind"] != "screenshot"
        )
        actual = Counter(
            signature(b) for s in self.doc.walk() if "-legacy-" in s.ident for b in s.blocks
        )
        self.assertFalse(expected - actual, "An original substantive block was dropped or rewritten")
        self.assertEqual(24, sum("-legacy-" in s.ident and s.level == 2 for s in self.doc.walk()))

    def test_no_old_ui_screenshots_claimed_as_new(self):
        self.assertGreater(self.meta["omittedLegacyUICaptures"], 0)
        self.assertEqual(0, self.meta["currentUICaptures"])
        self.assertFalse(self.evidence["complete"])
        self.assertTrue(all(b["source_kind"] == "diagram" for b in self.doc.figures))
        self.assertTrue(all(v["status"] == "not-run" for v in self.evidence["labs"].values()))

    def test_every_chapter_has_complete_current_procedure(self):
        for chapter in self.doc.sections[:24]:
            current = {s.number.rsplit(".", 1)[-1]: s for s in chapter.children if "-legacy-" not in s.ident}
            self.assertTrue({"1", "2", "3"}.issubset(current), chapter.title.en)
            actions = current["2"].blocks[0]["items"]
            self.assertGreaterEqual(len(actions), 4, chapter.title.en)
            for action in actions:
                self.assertGreater(len(action.ja), 15)
                self.assertGreater(len(action.en), 25)
                self.assertNotEqual(action.ja, action.en)

    def test_current_sections_are_in_numeric_order(self):
        for chapter in self.doc.sections:
            order = [int(s.number.rsplit(".", 1)[-1]) for s in chapter.children if "-legacy-" not in s.ident]
            self.assertEqual(sorted(order), order)
            self.assertEqual(len(order), len(set(order)))

    def test_matched_attachment_preview_stays_unapplied_and_separate(self):
        section = next(s for s in self.doc.walk() if s.ident == "ch-15-6")
        text = json.dumps(asdict(section), ensure_ascii=False)
        for token in (
            "separate matched Plan comparison", "same new prompt once",
            "DonationQualityScope", "DataLayer:String", "keyless/unbound",
            "saved definition remained unchanged",
            "No Approve, Act, Save or materialization", "complete proposed stable-ID",
            "earlier three-file pair", "original84 acceptance",
        ):
            self.assertIn(token, text)

    def test_zero_question_preflight_and_failed_mount_are_not_quality_credit(self):
        sections = {s.ident: s for s in self.doc.walk()}
        context = json.dumps(asdict(sections["ch-20-7"]), ensure_ascii=False)
        runtime = json.dumps(asdict(sections["ch-20-10"]), ensure_ascii=False)
        restore = json.dumps(asdict(sections["ch-21-5"]), ensure_ascii=False)
        for token in ("zero datasource parts", "Ten protected agents", "questions and publications were zero"):
            self.assertIn(token, context)
        for token in (
            "zero-question preflight", "notifications/initialized",
            "no question, conversation or source-execution credit",
            "complete stdout or exitValue", "question-journal durability proof",
            "keep questions disabled", "separate durable intent",
            "runtime-context guard failure before authentication",
            "managed-token retrieval and questions were zero",
            "claim neither MCP connectivity nor an Agent/authentication-service failure",
            "py4j JavaMap rather than a builtin dict",
            "HTTP202 with text/plain Accepted",
            "recognizes only this exact explicit acknowledgement",
            "initialize200", "tools/list200", "complete native frames",
            "Questions, source queries and source writes were zero",
        ):
            self.assertIn(token, runtime)
        for token in (
            "Create a version of my current work first", "cancelled",
            "unchanged saved definition", "not a new version or another restoration",
            "one native New version", "HTTP400", "No versions yet",
            "neither the planned description edit nor Restore was performed",
            "definitions remained byte-identical", "Do not resend private endpoints",
        ):
            self.assertIn(token, restore)

    def test_new_features_keep_required_limits(self):
        text = json.dumps(asdict(self.doc), ensure_ascii=False)
        for token in (
            "start_rule", "stop_rule", "PutBlob", "15,000", "14,900", "Business Rules",
            "10files/conversation", "5MB/file", "stable IDs", "Read+Build",
            "Resolve underlying DAX", "semantic-model-backed", "single-parent",
            "not ingestion/RDF import", "no OWL export", "Preserved", "Auto-fixed",
            "Not supported", "Version history", "2027-01-31",
        ):
            self.assertIn(token, text)

    def test_new_definition_contract_is_not_old_json_relabelled(self):
        current = {
            section.chapter: "\n".join(
                json.dumps(asdict(block), ensure_ascii=False)
                for child in section.walk() if "-legacy-" not in child.ident
                for block in child.blocks
            )
            for section in self.doc.sections[:24]
        }
        for token in ("TMDL/TMSL++", "1000000", "properties.generation", "namespaces/default.tmdl", "lineageTag", "InlineBase64"):
            self.assertIn(token, current[24])
        self.assertIn("backingMeasure", current[12])
        self.assertIn("not DAX", current[12])
        self.assertIn("pending-native-binding", current[24])
        self.assertIn("does not exclude a supplied part", current[24])
        self.assertIn("immutable", current[14])
        self.assertIn("read and write", current[4])
        self.assertIn("FIDO/Windows Hello", current[4])
        self.assertIn("Never extract/inject tokens or cookies", current[4])
        self.assertIn("equal TMDL text or hashes", current[21])
        self.assertIn("do not invent internal V4 endpoints", current[21])
        self.assertIn("do not prove preservation", current[22])

    def test_v3_native_measure_definitions_come_from_source(self):
        source = json.loads((ROOT / "workshop/v3.0.0-preview/powerbi/native-metrics-contract.json").read_text(encoding="utf-8"))
        section = next(s for s in self.doc.walk() if s.ident == "ch-12-6")
        rows = next(block["rows"] for block in section.blocks if block.kind == "table")
        self.assertEqual(
            [(m["table"], m["name"], m["dax"], m["formatString"]) for m in source["measures"]],
            [tuple(cell.ja for cell in row) for row in rows],
        )
        self.assertIn("KEEPFILTERS", section.blocks[-1]["text"].en)
        self.assertIn("14,900", section.blocks[-1]["text"].en)

    def test_new_ontology_context_and_mcp_runtime_do_not_relabel_legacy_execution(self):
        context = next(s for s in self.doc.walk() if s.ident == "ch-20-7")
        runtime = next(s for s in self.doc.walk() if s.ident == "ch-20-10")
        context_text = json.dumps(asdict(context), ensure_ascii=False)
        runtime_text = json.dumps(asdict(runtime), ensure_ascii=False)
        for token in (
            "read-only", "SQL/KQL/DAX", "legacy Ontology GQL", "Download ontology context",
            "ten minutes", "No data added", "does not establish deletion or denied permissions",
            "do not assume cross-source joins",
        ):
            self.assertIn(token.lower(), context_text.lower())
        for token in (
            "management plane", "MCP runtime", "Model Context Protocol", "unpublished Agent",
            "private monkeypatches", "not independent source-execution trace", "2026-08-26",
            "must not resubmit or replace the original ten/84",
            "<WORKSPACE_ID>", "<DATA_AGENT_ID>",
        ):
            self.assertIn(token, runtime_text)

    def test_v3_parameter_defaults_are_literal_not_comments(self):
        section = next(s for s in self.doc.walk() if s.ident == "appendix-b-2")
        rows = next(block["rows"] for block in section.blocks if block.kind == "table")
        defaults = {row[0].ja: row[1].ja for row in rows}
        self.assertEqual(14, len(defaults))
        self.assertEqual("''", defaults["ENVIRONMENT"])
        self.assertEqual("False", defaults["APPLY_CHANGES"])
        self.assertEqual("False", defaults["ALLOW_AUTOMATED_APPLY"])
        self.assertNotIn("#", defaults["SCOPE_FILE"])
        self.assertIn("RULE_STATEMENT_OVERRIDES", defaults)

    def test_portable_template_and_observed_native_ts_are_distinct(self):
        section = next(s for s in self.doc.walk() if s.ident == "ch-24-6")
        text = "\n".join(block["text"].en for block in section.blocks)
        self.assertIn("UNBOUND", text)
        self.assertIn("not its current state", text)
        self.assertIn("native operational querying reconciled", text)
        self.assertIn("Graph materialization separately stores a derived projection", text)
        self.assertIn("neither automatic materialization nor zero-copy Graph is claimed", text)

    def test_current_progress_keeps_source_repair_scoped(self):
        section = next(s for s in self.doc.walk() if s.ident == "ch-6-5")
        text = json.dumps(asdict(section), ensure_ascii=False)
        self.assertIn("Before repair", text)
        self.assertIn("17 rows by eight columns", text)
        self.assertIn("blocker is cleared for this Municipality sample", text)
        self.assertIn("not for all ten entities", text)
        self.assertNotIn("Until then keep blocked-functional-binding", text)

    def test_current_native_timeseries_count_change_is_not_hidden(self):
        section = next(s for s in self.doc.walk() if s.ident == "ch-10-5")
        text = json.dumps(asdict(section), ensure_ascii=False)
        for token in (
            "72 static + one time series = 73", "Fourteen columns",
            "73 static + one time series = 74", "Municipality.PrefectureId",
            "TimeSeries<int64>", "DonationEvents.DonatedAt",
            "Review retains", "FUNCTIONAL native TS querying",
            "not TS Graph or direct-dashboard success", "internal reasoning stay private",
        ):
            self.assertIn(token, text)

    def test_eventing_and_independent_gold_are_not_conflated(self):
        event = json.dumps(asdict(next(s for s in self.doc.walk() if s.ident == "ch-9-4")), ensure_ascii=False)
        gold = json.dumps(asdict(next(s for s in self.doc.walk() if s.ident == "ch-11-4")), ensure_ascii=False)
        for token in ("delayToleranceMs=120000", "not isolated", "84,687,000", "5,000",
                      "FeatureNotAvailable", "zero jobs", "native Run UI", "blank Type/Subject/Source",
                      "Manual001 is excluded", "rule stayed stopped", "15,000 rows/14,900 EventIDs/100 duplicates",
                      "outside the fixture window", "extent statistics are not a query-result proxy",
                      "missing onramp is not the current cause"):
            self.assertIn(token, event)
        self.assertIn("29 outputs", gold)
        self.assertIn("does not read Eventhouse", gold)

    def test_native_metrics_keep_observed_controls_and_trace_limit(self):
        section = next(s for s in self.doc.walk() if s.ident == "ch-12-7")
        text = json.dumps(asdict(section), ensure_ascii=False)
        for token in ("five Japanese business entities", "ten native Metrics", "SourceModel",
                      "View expression", "Hide expression", "Metric synonyms aren't available yet.",
                      "independent execution-path proof is missing", "Do not replay full TMDL"):
            self.assertIn(token, text)

    def test_live_answer_agreement_is_not_overall_accuracy(self):
        section = next(s for s in self.doc.walk() if s.ident == "ch-19-8")
        text = json.dumps(asdict(section), ensure_ascii=False)
        for token in ("3/3 questions", "10/10 numeric cells", "unobservable 3/3",
                      "Proven 0/3", "Unscored at this smoke snapshot", "not an independent human",
                      "Do not label this"):
            self.assertIn(token, text)

    def test_rdf_native_success_is_only_the_reduced_candidate(self):
        section = next(s for s in self.doc.walk() if s.ident == "ch-22-5")
        text = json.dumps(asdict(section), ensure_ascii=False)
        for token in ("459,935", "52,841", "Preserved 98", "Fixed automatically 0",
                      "Not supported 0", "SKOS altLabel", "not a lossless legacy round trip",
                      "native import/export/reimport cycle completed", "14/14 TMDL",
                      "namespace URI/default namespace are preserved", "xsd:long", "xsd:integer"):
            self.assertIn(token, text)

    def test_current_entity_names_are_business_concepts(self):
        current = "\n".join(
            json.dumps(asdict(block), ensure_ascii=False)
            for section in self.doc.walk() if "-legacy-" not in section.ident
            for block in section.blocks
        )
        self.assertNotIn("MunicipalityDemo", current)
        self.assertIn("business name Municipality", current)
        self.assertIn("technical reference, not an entity type", current)

    def test_supplemental_captures_do_not_reduce_completion_requirements(self):
        requests = evidence.requests()
        self.assertEqual(26, sum(item.get("completionRequired", True) for item in requests))
        self.assertEqual(24, sum(item.get("completionRequired", True) for item in requests if item["lab"] != "copilot-additive-entity"))
        optional = {item["id"] for item in requests if not item.get("completionRequired", True)}
        self.assertTrue({"p30-06-instances", "p30-15-act-preview"}.issubset(optional))

    def test_completed_labs_keep_architecture_and_failure_boundaries(self):
        text = json.dumps(asdict(self.doc), ensure_ascii=False)
        for token in (
            "InvalidPropertyType IncomingDonationAmountYen", "109,592 nodes/297,303",
            "No extra Lakehouse/source dataset copy is made", "Components CHECKBOX", "Row click only focused",
            "amount ranks, not business IDs", "MunicipalityDisplayName AS AreaName",
            "wrong-column SQL failure", "does not consider Rules", "negative-access checks remain unproven",
            "Python Succeeded", "installed Noto CJK", "without source requery or CSV overwrite",
            "not credit for the original84", "native-link checks in21.4",
            "model.tmdl are byte-identical", "not fix or pass the old shared-reference bug",
            "--include-relationships", "deploy-relationships", "new-plan-sha256",
            "Preview is not GA", "not runtime readiness guarantees",
        ):
            self.assertIn(token, text)

    def test_final_ai_results_are_not_invented_from_historical_runs(self):
        section = next(s for s in self.doc.walk() if s.ident == "ch-19-5")
        text = json.dumps(asdict(section), ensure_ascii=False)
        self.assertIn("No approved final-freeze aggregate projection is supplied", text)
        self.assertNotIn("accepted=True", text)

    def test_context_mcp_and_native_connector_diagnostics_are_separate(self):
        text = json.dumps(asdict(self.doc), ensure_ascii=False)
        for token in (
            "39", "38", "N/A", "zero precondition skips", "39+38+4+3=84",
            "This API version is not supported for the specified Ontology item.",
            "do not describe Graph/data absence as the root cause",
            "not an instruction-only causal A/B",
            "Keep native UI/SDK qualification", "MCP39/38/4/3 ledger",
            "never an implicit generation1 fallback", "default downgrade",
            "GQL on the separate Compat consumer are verified",
            "original84 quality gate is not accepted",
            "same Lakehouse mappings",
        ):
            self.assertIn(token, text)

    def test_final_compat_result_is_preview_not_quality_approval(self):
        section = next(s for s in self.doc.walk() if s.ident == "ch-19-10")
        text = json.dumps(asdict(section), ensure_ascii=False)
        for token in ("48 PASS+36 FAIL=84", "manual fixed-rubric offline assessment",
                      "not a direct causal MCP A/B", "native-gate acceptance",
                      "Main is not promoted", "not AI-quality approval or GA",
                      "Evaluation records and runtime/Notebook versions are frozen",
                      "Editorial corrections do not change the recorded scores",
                      "Stable v2.7 artifacts are not replaced"):
            self.assertIn(token, text)

    def test_fresh_native_ui_diagnostic_is_not_mcp_rescoring_or_banner_inference(self):
        section = next(s for s in self.doc.walk() if s.ident == "ch-17-6")
        text = json.dumps(asdict(section), ensure_ascii=False)
        for token in ("Complete CONFIRM", "contains one user message", "three actual KQL",
                      "incorrect2025 window", "available2026 window", "Twenty-one",
                      "scores were not overwritten", "recordedModel/runtime/stage",
                      "UI banner", "do not call the answer perfect"):
            self.assertIn(token, text)

    def test_gold_attachment_receipt_is_now_verified_but_not_ai_business_credit(self):
        text = json.dumps(asdict(next(s for s in self.doc.walk() if s.ident == "ch-15-6")), ensure_ascii=False)
        for token in ("four-file upload acknowledgement", "correct document-grounded Gold",
                      "ontology definition unchanged", "six local tests", "not current-pack certification"):
            self.assertIn(token, text)

    def test_explicit_capture_placement_requires_public_bilingual_caption(self):
        ident = "p30-06-instances"
        allowed = {ident: {"lab": "entities"}}
        self.assertEqual(
            (ident, "修復後の部分観測", "Partial post-repair observation"),
            capture_caption({"id": ident, "caption": {"ja": "修復後の部分観測", "en": "Partial post-repair observation"}}, allowed),
        )
        with self.assertRaises(ValueError):
            capture_caption({"id": ident, "caption": {"en": "Missing Japanese"}}, allowed)
        with self.assertRaises(ValueError):
            capture_caption({"id": ident, "caption": {"ja": "画面", "en": "person@example.com"}}, allowed)
        with self.assertRaises(ValueError):
            capture_caption({"id": "unreviewed-placement"}, allowed)

    def test_copilot_success_and_stable_ids_do_not_hide_shared_detach(self):
        section = next(s for s in self.doc.walk() if s.ident == "ch-15-7")
        text = json.dumps(asdict(section), ensure_ascii=False)
        self.assertIn("shared-reference preservation FAILED", text)
        self.assertIn("reusableProperty: AreaName", text)
        self.assertIn("do not erase the original failure", text)
        self.assertIn("failed candidate was not promoted", text)
        self.assertIn("source-data rollback was not tested", text)
        self.assertIn("no projected Metrics", text)

    def test_entity_metadata_inheritance_claim_is_qualified_by_actual_ui(self):
        chapter = next(s for s in self.doc.sections if s.chapter == 14)
        text = json.dumps(asdict(chapter), ensure_ascii=False)
        self.assertIn("Observed discrepancy", text)
        self.assertIn("Inherited from AdministrativeArea", text)
        self.assertIn("stored", text)
        self.assertIn("effective metadata", text)
        self.assertIn("explicit local override", text)
        self.assertNotIn("Entity descriptions, synonyms, ordinary relationships and data bindings are not inherited", text)

    def test_namespace_ui_is_not_inferred_from_tmdl_support(self):
        section = next(s for s in self.doc.walk() if s.ident == "ch-14-5")
        text = json.dumps(asdict(section), ensure_ascii=False)
        self.assertIn("UNVERIFIED", text)
        self.assertIn("not a conclusion that it is unsupported globally", text)
        self.assertIn("default.tmdl", text)
        self.assertIn("invent no alternate click path", text)

    def test_rebuilding_content_is_deterministic(self):
        with patch.object(content.preview30_public_evidence, "resolve", return_value=evidence.load()):
            again = content.build(ROOT)[-1]
        self.assertEqual(self.meta["contentSha256"], again["contentSha256"])

    def test_baseline_is_explicit_even_after_release_version_changes(self):
        original = Path.read_text
        def read(path, *args, **kwargs):
            return "3.0.0-preview" if path == ROOT / "VERSION" else original(path, *args, **kwargs)
        with patch.object(Path, "read_text", read):
            context = content.load_context(ROOT, source_version="2.7.0", document_edition="unified-20260923")
            self.assertEqual("2.7.0", context.version)
        with self.assertRaises(ValueError):
            content.load_context(ROOT, source_version="3.0.0-preview")

    def test_all_required_capture_ids_have_placement(self):
        text = json.dumps(asdict(self.doc), ensure_ascii=False)
        for request in evidence.requests():
            if request.get("completionRequired", True):
                self.assertIn(request["id"], text)
            self.assertGreaterEqual(request["chapter"], 1)
            self.assertLessEqual(request["chapter"], 24)

    def test_supplementary_context_does_not_replace_required_capture_inventory(self):
        requests = evidence.requests()
        self.assertEqual(26, sum(item.get("completionRequired", True) for item in requests))
        optional = {item["id"] for item in requests if not item.get("completionRequired", True)}
        self.assertIn("p30-09-copy-001-manual", optional)
        self.assertIn("p30-20-data-agent-mcp-settings", optional)
        self.assertIn("p30-15-noattachment-preview", optional)
        self.assertIn("p30-11-executed-parameters", optional)
        self.assertIn("p30-21-metric-rich-version", optional)
        self.assertNotIn("p30-20-mcp", optional)

    def test_reusable_preflight_and_final_admission_remain_separate(self):
        section = next(s for s in self.doc.walk() if s.ident == "ch-20-10")
        text = json.dumps(asdict(section), ensure_ascii=False)
        for token in ("preflight_mcp.py", "no question-submission path", "RequireAcceptance",
                      "26 completion captures", "unmet conditions stop artifact creation"):
            self.assertIn(token, text)


class EvidenceBoundaryTests(unittest.TestCase):
    def load_capture_fixture(self, *, width=1372, height=952, completion=False, status="observed", functional=True):
        ident = "p30-06-entities"
        payload = {
            "schemaVersion": "furusato-preview30-evidence/v1",
            "captures": [{
                "id": ident, "original": "original.png", "sanitized": "reviewed.png",
                "originalSha256": "a" * 64, "sanitizedSha256": "a" * 64,
                "actualUI": True, "reviewed": True, "experience": "new",
                "capturedAt": "2026-09-29T00:00:00Z", "reviewer": "coordinator",
                "redactions": "Region excludes identities",
                "redactionReview": "accounts-urls-ids-paths-removed",
                "completionEvidence": completion,
                "caption": {"ja": "画面の観測", "en": "Observed native UI"},
            }],
            "labs": {"entities": {
                "status": status, "reason": {"ja": "観測", "en": "Observation"},
                "evidenceIds": [ident], "executionAndReadbackObserved": status == "passed",
                "functionalBindingVerified": functional,
            }},
        }
        image = SimpleNamespace(
            width=width, height=height, size=(width, height), info={},
            getexif=lambda: {}, verify=lambda: None,
        )
        with patch.object(Path, "read_text", return_value=json.dumps(payload)):
            with patch.object(evidence, "requests", return_value=[{"id": ident, "lab": "entities"}]):
                with patch.object(evidence, "_private_file", return_value=Path("private-image.png")):
                    with patch.object(evidence, "digest", return_value="a" * 64):
                        with patch.object(evidence.Image, "open") as opened:
                            opened.return_value.__enter__.return_value = image
                            return evidence.load(Path("manifest.json"))

    def test_absent_manifest_cannot_claim_complete(self):
        result = evidence.load()
        self.assertFalse(result["complete"])
        self.assertEqual({}, result["captures"])
        self.assertNotIn("passed", [r["status"] for r in result["labs"].values()])

    def test_old_or_unreviewed_ui_is_rejected_before_file_io(self):
        for bad in (
            {"actualUI": False, "reviewed": True, "experience": "new"},
            {"actualUI": True, "reviewed": False, "experience": "new"},
            {"actualUI": True, "reviewed": True, "experience": "old"},
        ):
            data = {"schemaVersion": "furusato-preview30-evidence/v1", "captures": [{"id": "p30-06-entities", **bad}]}
            with patch.object(Path, "read_text", return_value=json.dumps(data)):
                with patch.object(evidence, "requests", return_value=[{"id": "p30-06-entities", "lab": "entities"}]):
                    with self.assertRaises(ValueError):
                        evidence.load(Path("manifest.json"))

    def test_passed_without_captures_or_readback_is_rejected(self):
        data = {
            "schemaVersion": "furusato-preview30-evidence/v1", "captures": [],
            "labs": {"entities": {"status": "passed", "reason": {"ja": "成功", "en": "Success"}, "evidenceIds": []}},
        }
        with patch.object(Path, "read_text", return_value=json.dumps(data)):
            with patch.object(evidence, "requests", return_value=[{"id": "p30-06-entities", "lab": "entities"}]):
                with self.assertRaises(ValueError):
                    evidence.load(Path("manifest.json"))

    def test_private_identity_in_public_caption_is_rejected(self):
        with self.assertRaises(ValueError):
            evidence._pair({"ja": "成功", "en": "Account person@example.com"}, "caption")

    def test_observed_orientation_never_completes_a_lab(self):
        result = self.load_capture_fixture()
        self.assertFalse(result["complete"])
        self.assertEqual("observed", result["labs"]["entities"]["status"])

    def test_partial_capture_cannot_be_relabelled_passed(self):
        with self.assertRaisesRegex(ValueError, "Partial/orientation"):
            self.load_capture_fixture(status="passed", completion=False)

    def test_portrait_excerpt_does_not_weaken_completion_size_gate(self):
        self.assertFalse(self.load_capture_fixture(width=379, height=902)["complete"])
        with self.assertRaisesRegex(ValueError, "Completion UI capture"):
            self.load_capture_fixture(width=379, height=902, completion=True, status="passed")

    def test_explicit_completion_still_requires_all_existing_gates(self):
        self.assertTrue(self.load_capture_fixture(completion=True, status="passed")["complete"])

    def test_schema_only_entity_cannot_pass_functional_binding(self):
        with self.assertRaisesRegex(ValueError, "functional Instances/query"):
            self.load_capture_fixture(completion=True, status="passed", functional=False)
    def test_copilot_act_pass_requires_shared_reference_invariant(self):
        ident = "p30-15-act-readback"
        raw = {
            "schemaVersion": "furusato-preview30-evidence/v1", "captures": [],
            "labs": {"copilot-act": {
                "status": "passed", "reason": {"ja": "主張", "en": "Claim"},
                "evidenceIds": [], "executionAndReadbackObserved": True,
                "invariants": {name: name != "sharedPropertyReferencesPreserved" for name in evidence.ACT_INVARIANTS},
            }},
        }
        with patch.object(Path, "read_text", return_value=json.dumps(raw)):
            with patch.object(evidence, "requests", return_value=[{"id": ident, "lab": "copilot-act"}]):
                with self.assertRaisesRegex(ValueError, "shared-property"):
                    evidence.load(Path("manifest.json"))


class DraftPackageGateTests(unittest.TestCase):
    def good_report(self):
        return {
            "passedLocalChecks": True,
            "findings": [{"check": name, "level": "PASS"} for name in sorted(REQUIRED_FULL_CHECKS)],
        }

    def test_full_local_checks_are_required(self):
        require_full_validation(self.good_report())

    def test_incomplete_interaction_report_cannot_be_packaged(self):
        value = self.good_report()
        value["findings"] = [f for f in value["findings"] if f["check"] != "interaction.noExternalRequests"]
        with self.assertRaisesRegex(ValueError, "interaction evidence"):
            require_full_validation(value)

    def test_failure_cannot_be_hidden_by_top_level_pass(self):
        value = self.good_report()
        value["findings"].append({"check": "image.privacy", "level": "FAIL"})
        with self.assertRaisesRegex(ValueError, "contains failures"):
            require_full_validation(value)

    def test_failed_validation_is_not_usable_as_verified_input(self):
        value = self.good_report()
        value["passedLocalChecks"] = False
        with self.assertRaisesRegex(ValueError, "did not pass"):
            require_full_validation(value)


if __name__ == "__main__":
    unittest.main()
