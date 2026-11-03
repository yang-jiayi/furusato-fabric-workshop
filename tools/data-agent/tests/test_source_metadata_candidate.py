"""Offline source-metadata candidate tests; these do not run or grade answers."""
import base64
import copy
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import source_metadata_candidate as candidate
from evaluate_native import definition_digest
from measured_contract_profile import stage_sources
from source_grounded_profile import decoded_parts, inline_part
from test_current_profile import fixture


ROOT = Path(__file__).resolve().parents[3]
MODEL_ROOT = ROOT / "workshop" / "v3.0.0-preview" / "powerbi" / "Furusato_Analytics.SemanticModel"
NOTEBOOK_PATH = ROOT / "workshop" / "v3.0.0-preview" / "notebooks" / "Notebook_05_Furusato_Analytics_Quality_and_BI.ipynb"


def model_fixture():
    return {
        "format": "TMDL",
        "parts": [
            {
                "path": path.relative_to(MODEL_ROOT).as_posix(),
                "payloadType": "InlineBase64",
                "payload": base64.b64encode(path.read_bytes()).decode("ascii"),
            }
            for path in sorted((MODEL_ROOT / "definition" / "tables").glob("*.tmdl"))
        ],
    }


def notebook_fixture():
    return json.loads(NOTEBOOK_PATH.read_text(encoding="utf-8"))


def walk(nodes):
    for node in nodes:
        yield node
        yield from walk(node.get("children", []))


def compile_fixture(agent, model, notebook):
    return candidate.compile_candidate(
        agent, model, notebook,
        expected_agent_sha256=definition_digest(agent),
        expected_model_sha256=definition_digest(model),
        expected_part_count=len(agent["parts"]),
    )


def fixture_with_scope_clause():
    definition = fixture()
    parts = decoded_parts(definition)
    for stage in ("draft", "published"):
        path = f"Files/Config/{stage}/stage_config.json"
        parts[path]["aiInstructions"] = candidate.GLOBAL_SCOPE_REWRITE_BEFORE + "\nKeep the rest of the global policy."
    parts["Files/Config/unrelated.json"] = {"unchanged": True}
    return {"parts": [inline_part(path, value) for path, value in parts.items()]}


class SourceMetadataCandidateTests(unittest.TestCase):
    def setUp(self):
        self.agent = fixture_with_scope_clause()
        self.model = model_fixture()
        self.notebook = notebook_fixture()
        self.after, self.receipt = compile_fixture(self.agent, self.model, self.notebook)

    def test_only_draft_source_metadata_and_shared_scope_change(self):
        original = {part["path"]: part for part in self.agent["parts"]}
        actual = {part["path"]: part for part in self.after["parts"]}
        changed = [path for path in original if original[path] != actual[path]]
        self.assertEqual(set(changed), set(self.receipt["changedDraftFields"]))
        self.assertTrue(all(path.startswith("Files/Config/draft/") for path in changed))
        self.assertEqual(len(changed), 4)
        self.assertIn("Files/Config/draft/stage_config.json", changed)
        self.assertEqual(
            {"Files/Config/draft/stage_config.json": ["aiInstructions"]},
            {path: self.receipt["changedDraftFields"][path]
             for path in changed if path.endswith("stage_config.json")},
        )
        for path, part in original.items():
            if not path.startswith("Files/Config/draft/"):
                self.assertEqual(part, actual[path])
        self.assertTrue(self.receipt["publishedAndNativeOntologyPartsPreserved"])
        self.assertTrue(self.receipt["sourceSelectionsAndIdentitiesPreserved"])
        self.assertEqual(self.agent, fixture_with_scope_clause())

    def test_outer_delegation_spec_covers_same_source_totals_and_rankings(self):
        docs = decoded_parts(self.after)
        global_text = docs["Files/Config/draft/stage_config.json"]["aiInstructions"]
        self.assertNotIn(candidate.GLOBAL_SCOPE_REWRITE_BEFORE, global_text)
        self.assertIn(candidate.GLOBAL_SCOPE_REWRITE_AFTER, global_text)
        self.assertIn("Keep the rest of the global policy.", global_text)
        for marker in (
            "one specification", "same source", "every delegated query",
            "including totals and rankings", "Filter facts before aggregation",
            "Check each query/result", "report missing filters",
            "unfiltered stored ranks",
        ):
            self.assertIn(marker, global_text)
        self.assertFalse(any(case in global_text for case in ("B08", "B17", "T07")))

    def test_fresh_readback_scope_and_hashes_are_pinned(self):
        sources = {}
        for stage in ("draft", "published"):
            _, stage_sources, _ = candidate.stage_sources(self.agent, stage)
            sources[stage] = {kind: source[1]["artifactId"] for kind, source in stage_sources.items()}
        scope = {
            "tenantId": "00000000-0000-0000-0000-000000000011",
            "workspaceId": "00000000-0000-0000-0000-000000000001",
            "folderId": "00000000-0000-0000-0000-000000000003",
            "agentId": "00000000-0000-0000-0000-000000000002",
            "semanticModelId": sources["draft"]["semantic_model"],
            "agentType": "DataAgent",
            "agentParentFolderId": "00000000-0000-0000-0000-000000000003",
            "draftSourceIds": sources["draft"],
            "publishedSourceIds": sources["published"],
        }
        receipt = {
            "result": "fresh-read-only-definition-snapshot",
            "identityVerified": True,
            **scope,
            "agentCanonicalSha256": definition_digest(self.agent),
            "modelCanonicalSha256": definition_digest(self.model),
            "agentParts": 13,
            "modelParts": len(self.model["parts"]),
            "agentAdjacentFreshReadSame": True,
            "modelAdjacentFreshReadSame": True,
            "cloudWrites": 0,
            "updateDefinitionRequests": 0,
            "publishRequests": 0,
            "questionSubmissions": 0,
        }
        receipt_sha = hashlib.sha256(json.dumps(receipt, sort_keys=True).encode()).hexdigest()
        with patch.object(candidate, "EXPECTED_AGENT_SHA256", definition_digest(self.agent)), \
                patch.object(candidate, "EXPECTED_MODEL_SHA256", definition_digest(self.model)):
            refreshed, refreshed_receipt = candidate.compile_fresh_candidate(
                self.agent, self.model, self.notebook,
                expected_agent_sha256=definition_digest(self.agent),
                expected_model_sha256=definition_digest(self.model),
                expected_scope=scope,
                fresh_readback_receipt=receipt,
                fresh_readback_receipt_sha256=receipt_sha,
            )
            self.assertEqual(refreshed, self.after)
            self.assertEqual(receipt_sha, refreshed_receipt["freshReadbackReceiptSha256"])
            self.assertTrue(refreshed_receipt["freshReadbackIdentityAndParentFolderVerified"])
            self.assertTrue(refreshed_receipt["inputStageIsFreshCurrentDefinition"])
            wrong_scope = dict(scope, folderId="00000000-0000-0000-0000-000000000099")
            with self.assertRaisesRegex(ValueError, "identity, parent folder or source bindings"):
                candidate.compile_fresh_candidate(
                    self.agent, self.model, self.notebook,
                    expected_agent_sha256=definition_digest(self.agent),
                    expected_model_sha256=definition_digest(self.model),
                    expected_scope=wrong_scope,
                    fresh_readback_receipt=receipt,
                    fresh_readback_receipt_sha256=receipt_sha,
                )

    def test_lakehouse_and_kusto_guidance_matches_failure_layer(self):
        _, sources, _ = stage_sources(self.after, "draft")
        lakehouse = sources["lakehouse_tables"][1]
        instructions = lakehouse["dataSourceInstructions"]
        self.assertIn("EACH delegated SQL query", instructions)
        self.assertIn("dbo.ot_donation before aggregation", instructions)
        self.assertIn("a separately filtered total does not constrain a separate ranking query", instructions)
        nodes = list(walk(lakehouse["elements"]))
        descriptions = {
            node["display_name"]: node["description"]
            for node in nodes
            if node.get("display_name") in {
                "ot_donation", "DonationPaymentMethod", "MunicipalityStaticCount",
                "MunicipalityStaticTotalYen", "MunicipalityAmountRank",
            }
        }
        self.assertEqual(5, len(descriptions))
        self.assertIn("before grouping or ranking", descriptions["ot_donation"])
        self.assertIn("all payment methods", descriptions["MunicipalityStaticTotalYen"])
        self.assertIn("cannot answer a filtered transaction ranking", descriptions["MunicipalityStaticCount"])
        self.assertIn("derive a filtered ranking", descriptions["MunicipalityAmountRank"])

        kusto = sources["kusto"][1]
        self.assertIn("yyyy-MM-dd HH:mm:ss", kusto["dataSourceInstructions"])
        self.assertIn("copy the returned 24-hour value exactly", kusto["dataSourceInstructions"])
        self.assertIn("semantic model provides Notebook 05 Gold", kusto["dataSourceInstructions"])
        self.assertIn("raw Eventhouse observations", kusto["dataSourceInstructions"])
        self.assertTrue(all(0 < size <= candidate.LIMIT
                            for size in self.receipt["instructionUtf16Units"].values()))

    def test_verified_model_metadata_is_exposed_on_selected_elements(self):
        _, sources, _ = stage_sources(self.after, "draft")
        semantic = sources["semantic_model"][1]
        nodes = list(walk(semantic["elements"]))
        measures = {
            node["display_name"]: node["description"]
            for node in nodes
            if node.get("type") == "semantic_model.measure"
            and node.get("display_name") in {
                "静的寄附総額", "静的寄附件数", "受入増分寄附総額",
                "受入増分寄附件数", "高額寄附件数",
            }
        }
        self.assertEqual(5, len(measures))
        self.assertIn("KEEPFILTERS(", measures["静的寄附総額"])
        self.assertIn("outer filter", measures["静的寄附総額"])
        self.assertIn("'寄附'[データソース] = \"StaticSeed\"", measures["静的寄附総額"])
        self.assertIn("Verified DAX expression:", measures["高額寄附件数"])
        self.assertIn("'寄附'[高額寄附フラグ] = TRUE()", measures["高額寄附件数"])
        self.assertEqual(1, measures["高額寄附件数"].count("KEEPFILTERS intersects"))
        self.assertNotIn("Model metadata:", measures["高額寄附件数"])
        self.assertIn("DonationAmountYen > 57000", measures["高額寄附件数"])
        self.assertIn("exactly JPY 57,000 is excluded", measures["高額寄附件数"])
        flag = next(node for node in nodes
                    if node.get("type") == "semantic_model.column"
                    and node.get("display_name") == "高額寄附フラグ")
        self.assertIn("DonationAmountYen > 57000", flag["description"])
        self.assertIn("not a notification rule", flag["description"])

    def test_exact_offline_request_hash_and_model_are_unchanged(self):
        body = candidate.candidate_request_body(self.after)
        body_bytes = json.dumps(
            body, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        self.assertEqual(hashlib.sha256(body_bytes).hexdigest(),
                         self.receipt["candidateUpdateRequestBodySha256"])
        self.assertEqual(definition_digest(self.agent),
                         self.receipt["inputAgentCanonicalSha256"])
        self.assertEqual(definition_digest(self.model),
                         self.receipt["inputModelCanonicalSha256"])
        self.assertFalse(self.receipt["semanticModelDefinitionChanged"])
        self.assertFalse(self.receipt["notebookDataChanged"])
        self.assertEqual(0, self.receipt["cloudCalls"])
        self.assertFalse(self.receipt["answerAccuracyAccepted"])
        self.assertEqual("not performed", self.receipt["liveSubmissionOrPublication"])

    def test_rejects_drift_missing_provenance_and_conflicting_metadata(self):
        with self.assertRaisesRegex(ValueError, "Agent differs"):
            candidate.compile_candidate(self.agent, self.model, self.notebook)
        with self.assertRaisesRegex(ValueError, "previous prepublication Agent pin is stale"):
            candidate.compile_candidate(
                self.agent, self.model, self.notebook,
                expected_agent_sha256=candidate.PREVIOUS_AGENT_SHA256,
                expected_model_sha256=definition_digest(self.model),
            )
        with self.assertRaisesRegex(ValueError, "Agent part count"):
            candidate.compile_candidate(
                self.agent,
                self.model,
                self.notebook,
                expected_agent_sha256=definition_digest(self.agent),
                expected_model_sha256=definition_digest(self.model),
                expected_part_count=12,
            )
        missing_threshold = copy.deepcopy(self.notebook)
        for cell in missing_threshold["cells"]:
            cell["source"] = [line.replace(candidate.NOTEBOOK_THRESHOLD, "F.lit(True)")
                              for line in cell.get("source", [])]
        with self.assertRaisesRegex(ValueError, "does not verify"):
            compile_fixture(self.agent, self.model, missing_threshold)

        wrong_filter_column = copy.deepcopy(self.model)
        table = next(part for part in wrong_filter_column["parts"]
                     if part["path"] == candidate.MODEL_PATH)
        text = base64.b64decode(table["payload"]).decode("utf-8-sig")
        text = text.replace("KEEPFILTERS('寄附'[データソース]", "KEEPFILTERS('寄附'[DonatedAtUtc]", 1)
        table["payload"] = base64.b64encode(text.encode("utf-8")).decode("ascii")
        with self.assertRaisesRegex(ValueError, "unexpected inner predicate"):
            compile_fixture(self.agent, wrong_filter_column, self.notebook)

        changed = copy.deepcopy(self.agent)
        docs, sources, _ = stage_sources(changed, "draft")
        path, source = sources["semantic_model"]
        node = next(node for node in walk(source["elements"])
                    if node.get("type") == "semantic_model.measure"
                    and node.get("display_name") == "静的寄附総額")
        node["description"] = "Pre-existing unrelated metadata."
        changed["parts"] = [
            inline_part(path, source) if part["path"] == path else part
            for part in changed["parts"]
        ]
        with self.assertRaisesRegex(ValueError, "Refusing to overwrite"):
            compile_fixture(changed, self.model, self.notebook)

        different_published = decoded_parts(self.agent)
        different_published["Files/Config/published/stage_config.json"]["aiInstructions"] += "\nDistinct published policy"
        changed = {"parts": [inline_part(path, value) for path, value in different_published.items()]}
        with self.assertRaisesRegex(ValueError, "Draft and Published global instructions differ"):
            compile_fixture(changed, self.model, self.notebook)

    def test_candidate_is_deterministic_and_does_not_mutate_inputs(self):
        original = copy.deepcopy((self.agent, self.model, self.notebook))
        second, receipt = compile_fixture(self.agent, self.model, self.notebook)
        self.assertEqual((self.after, self.receipt), (second, receipt))
        self.assertEqual(original, (self.agent, self.model, self.notebook))


if __name__ == "__main__":
    unittest.main()
