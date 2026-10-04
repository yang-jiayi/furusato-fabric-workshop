"""Pure generation1 bridge preparation; never cloud or consumer acceptance."""
from __future__ import annotations
import base64
import copy
import gzip
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import build_preview30 as builder
import preview30_compatibility as compat
import preview30_runtime as rt
from preview30_notebooks import package, RUNNER
from test_preview30_runtime import scope

TEMP = "44444444-4444-4444-8444-444444444444"
LH = "55555555-5555-4555-8555-555555555555"
CORE = "66666666-6666-4666-8666-666666666666"
BRIDGE = "77777777-7777-4777-8777-777777777777"
GRAPH = "88888888-8888-4888-8888-888888888888"
OTHER = "99999999-9999-4999-8999-999999999999"


def fixtures():
    s = scope()
    items = [
        {"id": LH, "type": "Lakehouse", "displayName": "LH_Furusato_001", "folderId": s["folderId"]},
        {"id": CORE, "type": "Ontology", "displayName": "ONT_Furusato_001", "folderId": s["folderId"]},
    ]
    inventory = {
        "capturedUtc": "2026-01-01T00:00:00Z",
        "workspace": {"id": s["workspaceId"], "displayName": s["workspaceName"]},
        "folders": [{"id": s["folderId"], "displayName": "Approved"},
                    {"id": TEMP, "displayName": "Temp", "parentFolderId": s["folderId"]}],
        "items": copy.deepcopy(items), "recoverableItems": [],
    }
    owned = {"scopeSha256": rt.scope_fingerprint(s),
             "items": {"lakehouse": items[0], "ontology": items[1]},
             "sourceVerification": {"verified": True}, "ontologyVerification": {"generation": 2},
             "ontologyNativeUiHandoff": {"automatedTmdlWritesDisabled": True}}
    return s, inventory, owned


def json_part(path, value):
    return {"path": path, "payloadType": "InlineBase64",
            "payload": base64.b64encode(json.dumps(value, ensure_ascii=False, indent=2).encode("utf-8")).decode("ascii")}


def handoff_fixtures():
    s, inventory, owned = fixtures()
    body, plan = compat.prepare(s, inventory, owned, TEMP)
    metadata = {"id": BRIDGE, "type": "Ontology", "displayName": body["displayName"],
                "workspaceId": s["workspaceId"], "folderId": TEMP,
                "description": body["description"], "properties": {"generation": 1}}
    inventory["items"].append(copy.deepcopy(metadata))
    receipt = {"item": metadata, "typedMetadata": metadata, "bodySha256": plan["create"]["bodySha256"],
               "planSha256": plan["planSha256"]}
    graph = {"graphQueryAcceptance": True, "gqlChecksPassed": 3,
             "scope": {"ontologyId": BRIDGE, "workspaceId": s["workspaceId"],
                       "folderId": TEMP, "sourceLakehouseId": LH, "graphModelId": GRAPH},
             "refreshJob": {"id": OTHER, "itemId": GRAPH, "status": "Completed", "failureReason": None},
             "nativeCounts": {"nodeTypes": 10, "edgeTypes": 15, "nodes": 109592, "directedEdges": 297303},
             "postGqlGuards": {"passed": True}}
    parts = [json_part("Files/Config/data_agent.json", {"schemaVersion": "1.0", "preserved": True})]
    parts.append(json_part("Files/Config/published/stage_config.json", {
        "aiInstructions": "FROZEN generation2 wording.\nPreserve these exact bytes: 日本語  ",
        "experimental": {"codeInterpreterEnabled": True}, "otherSettings": [1, 2, 3],
    }))
    model = compat.legacy_helpers().definition_model(body["definition"])
    entities = [v for path, v in model.items() if compat.legacy_helpers().ENTITY_PART_PATTERN.fullmatch(path)]
    for kind in ("lakehouse_tables", "kusto", "ontology", "semantic_model"):
        value = {"type": kind, "workspaceId": s["workspaceId"],
                 "artifactId": LH if kind == "lakehouse_tables" else OTHER,
                 "displayName": "Frozen " + kind, "userDescription": "Preserve unless ontology.",
                 "dataSourceInstructions": None if kind == "ontology" else "EXACT frozen source instructions",
                 "elements": [{"id": "preserved-native-id", "is_selected": True}], "metadata": {"keep": True}}
        if kind == "ontology":
            value["elements"] = [
                {"id": e["name"], "display_name": e["name"], "type": "ontology.entity",
                 "is_selected": True, "children": [],
                 "description": ",".join(p["name"] for p in e["properties"])} for e in entities]
        parts.append(json_part("Files/Config/published/" + kind + "-frozen/datasource.json", value))
    return s, inventory, owned, receipt, body["definition"], graph, {"parts": parts}


class CompatibilityBuilderTests(unittest.TestCase):
    def test_production_defaults_to_root_without_temp(self):
        s, inventory, owned = fixtures()
        inventory["folders"] = [f for f in inventory["folders"] if f["id"] != TEMP]
        body, plan = compat.prepare(s, inventory, owned)
        self.assertEqual(body["folderId"], s["folderId"])
        self.assertEqual(plan["contract"]["deployment"]["defaultPlacement"], "specified-folder-direct")
        self.assertFalse(plan["allowCloudMutations"])

    def test_exact_static_template_and_unchanged_baseline(self):
        original = rt.load(compat.TEMPLATE)
        before = copy.deepcopy(original)
        template, contract = compat.build_template(original)
        self.assertEqual(original, before)
        self.assertEqual(compat.legacy_helpers().validate_template(original)["definitionParts"], 54)
        self.assertEqual(compat.legacy_helpers().validate_template(template), compat.COUNTS)
        self.assertEqual(len(template["parts"]), 53)
        self.assertEqual(contract["expectedGeneration"], 1)
        self.assertFalse(contract["defaultEnabled"])
        self.assertFalse(contract["implicitFallback"])
        self.assertFalse(contract["evidenceBoundary"]["full10Question84ConditionAcceptanceImplied"])
        self.assertNotIn("eventhouse", template["sourceSelectors"])
        self.assertEqual(len(template["expectedSourceTables"]["lakehouse"]), 11)

    def test_only_ts_and_item_metadata_change(self):
        original = rt.load(compat.TEMPLATE)
        template, _ = compat.build_template(original)
        before = {p["path"]: p["content"] for p in original["parts"]}
        after = {p["path"]: p["content"] for p in template["parts"]}
        missing = set(before) - set(after)
        self.assertEqual(len(missing), 1)
        self.assertEqual(before[next(iter(missing))]["dataBindingConfiguration"]["dataBindingType"], "TimeSeries")
        for path, value in after.items():
            old = copy.deepcopy(before[path])
            if path == ".platform":
                old["metadata"]["description"] = compat.DESCRIPTION
            elif compat.legacy_helpers().ENTITY_PART_PATTERN.fullmatch(path):
                old["timeseriesProperties"] = []
            self.assertEqual(value, old, path)
        self.assertEqual(sum(len(v["properties"]) for p, v in after.items()
                             if compat.legacy_helpers().ENTITY_PART_PATTERN.fullmatch(p)), 72)

    def test_deterministic_exact_source_body_and_preview_hash(self):
        s, inventory, owned = fixtures()
        originals = copy.deepcopy((s, inventory, owned))
        first = compat.prepare(s, inventory, owned, TEMP)
        self.assertEqual(first, compat.prepare(s, inventory, owned, TEMP))
        self.assertEqual((s, inventory, owned), originals)
        body, plan = first
        self.assertEqual(rt.digest(body), plan["create"]["bodySha256"])
        self.assertEqual(rt.digest({k: v for k, v in plan.items() if k != "planSha256"}), plan["planSha256"])
        self.assertFalse(plan["allowCloudMutations"])
        self.assertEqual(body["folderId"], TEMP)
        self.assertEqual(body["displayName"], "ONT_Furusato_AgentCompat_001")
        self.assertNotIn("format", body["definition"])
        source_count, tables = 0, set()
        for part in body["definition"]["parts"]:
            self.assertFalse(part["path"].endswith(".tmdl"))
            value = json.loads(base64.b64decode(part["payload"], validate=True))
            for source in (value.get("dataBindingConfiguration", {}).get("sourceTableProperties"),
                           value.get("dataBindingTable")):
                if source:
                    self.assertEqual(next(iter(source)), "sourceType")
                    self.assertEqual(source["sourceType"], "LakehouseTable")
                    self.assertEqual(source["itemId"], LH)
                    self.assertEqual(source["workspaceId"], s["workspaceId"])
                    self.assertEqual(source["sourceSchema"], "dbo")
                    tables.add(source["sourceTableName"])
                    source_count += 1
        self.assertEqual((source_count, len(tables)), (25, 11))

    def test_absence_ownership_scope_and_generation_refusals(self):
        cases = ("active", "recoverable", "wrong-temp-parent", "unmapped", "wrong-owner", "unverified-source", "legacy-core")
        for case in cases:
            s, inv, owned = fixtures()
            if case in {"active", "recoverable"}:
                inv["items" if case == "active" else "recoverableItems"].append({
                    "id": BRIDGE, "type": "DataAgent", "displayName": "ont_furusato_agentcompat_001"})
            elif case == "wrong-temp-parent":
                inv["folders"][1]["parentFolderId"] = OTHER
            elif case == "unmapped":
                s["folderMappingVerified"] = False
            elif case == "wrong-owner":
                owned["items"]["lakehouse"]["id"] = OTHER
            elif case == "unverified-source":
                owned["sourceVerification"]["verified"] = False
            else:
                owned["ontologyVerification"]["generation"] = 1
            with self.subTest(case=case), self.assertRaises(rt.SafetyError):
                compat.prepare(s, inv, owned, TEMP)

    def test_generation1_readback_required_and_source_drift_refused(self):
        s, inv, owned, receipt, definition, graph, frozen = handoff_fixtures()
        meta = receipt["typedMetadata"]
        self.assertTrue(compat.verify_readback(s, owned, TEMP, meta, definition)["verified"])
        for generation in (2, None, True, 1.0, "1"):
            wrong = copy.deepcopy(meta)
            wrong["properties"]["generation"] = generation
            with self.subTest(generation=generation), self.assertRaises(rt.SafetyError):
                compat.verify_readback(s, owned, TEMP, wrong, definition)
        broken = copy.deepcopy(definition)
        part = next(p for p in broken["parts"] if "/DataBindings/" in p["path"])
        content = json.loads(base64.b64decode(part["payload"]))
        content["dataBindingConfiguration"]["sourceTableProperties"]["itemId"] = OTHER
        part["payload"] = compat.legacy_helpers()._encode_part_json(content)
        with self.assertRaises(rt.SafetyError):
            compat.verify_readback(s, owned, TEMP, meta, broken)

    def test_default_gen2_paths_and_relationships_remain_separate(self):
        self.assertFalse(any("AgentCompat" in r["displayName"] for r in rt.planned_resources("001", include_relationships=True)))
        self.assertNotIn("agent-handoff", RUNNER)
        self.assertNotIn("compatibility", RUNNER)
        self.assertEqual(next(r for r in rt.planned_resources("001") if r["key"] == "ontology")["purpose"], "generation2")

    def test_optional_build_and_package_are_offline_only(self):
        with patch.object(builder, "save") as save:
            result = builder.build_agent_compatibility()
        self.assertEqual(result["definitionParts"], 53)
        self.assertFalse(result["deployed"])
        self.assertFalse(result["agentConfigurationChanged"])
        root = rt.PREVIEW / "ontology/agent-compat"
        self.assertEqual({call.args[0] for call in save.call_args_list},
                         {root / "definition-template.json", root / "contract.json"})
        files = json.loads(gzip.decompress(package(data=False)))
        for relative in compat.PACKAGED_INPUTS:
            self.assertEqual(base64.b64decode(files[relative]), (rt.REPO / relative).read_bytes())
        self.assertIn("workshop/v3.0.0-preview/ontology/agent-compat/definition-template.json", files)
        self.assertIn("workshop/v3.0.0-preview/ontology/agent-compat/contract.json", files)


class CompatibilityAgentHandoffTests(unittest.TestCase):
    def test_only_three_source_fields_change_and_global_ci_are_byte_identical(self):
        s, inv, owned, receipt, definition, graph, frozen = handoff_fixtures()
        before = copy.deepcopy(frozen)
        draft, handoff = compat.agent_handoff(s, inv, owned, TEMP, receipt, definition, graph, frozen, "published")
        self.assertEqual(frozen, before)
        self.assertEqual(handoff["selectedOntologyGeneration"], 1)
        self.assertFalse(handoff["allowCloudMutations"])
        self.assertFalse(handoff["promotionAllowed"])
        self.assertFalse(handoff["publicationAllowedByPreparation"])
        self.assertEqual([c["field"] for c in handoff["onlyChangedOntologyFields"]], ["artifactId", "displayName", "userDescription"])
        old_parts = {p["path"]: p for p in frozen["parts"]}
        self.assertFalse(any("/published/" in p["path"] for p in draft["parts"]))
        for part in draft["parts"]:
            old_path = part["path"].replace("/draft/", "/published/")
            old = old_parts.get(old_path, old_parts.get(part["path"]))
            if "ontology-frozen/datasource.json" not in part["path"]:
                self.assertEqual(part["payload"], old["payload"], part["path"])
            else:
                actual = json.loads(base64.b64decode(part["payload"]))
                expected = json.loads(base64.b64decode(old["payload"]))
                self.assertEqual(actual["artifactId"], BRIDGE)
                for key in set(expected) - {"artifactId", "displayName", "userDescription"}:
                    self.assertEqual(actual[key], expected[key])
        settings = json.loads(base64.b64decode(old_parts["Files/Config/published/stage_config.json"]["payload"]))
        self.assertEqual(handoff["globalUtf8Sha256"], hashlib.sha256(settings["aiInstructions"].encode("utf-8")).hexdigest())

    def test_core_ts_selection_is_not_silently_filtered(self):
        s, inv, owned, receipt, definition, graph, frozen = handoff_fixtures()
        part = next(p for p in frozen["parts"] if "ontology-frozen/datasource.json" in p["path"])
        value = json.loads(base64.b64decode(part["payload"]))
        next(e for e in value["elements"] if e["display_name"] == "Municipality")["description"] += ",IncomingDonationAmountYen"
        part["payload"] = json_part(part["path"], value)["payload"]
        with self.assertRaises(rt.SafetyError):
            compat.agent_handoff(s, inv, owned, TEMP, receipt, definition, graph, frozen, "published")

    def test_graph_readiness_wrong_scope_and_existing_candidate_refused(self):
        for case in ("not-completed", "not-query-accepted", "wrong-counts", "wrong-source", "missing-owner", "candidate-collision"):
            s, inv, owned, receipt, definition, graph, frozen = handoff_fixtures()
            if case == "not-completed":
                graph["refreshJob"]["status"] = "Cancelled"
            elif case == "not-query-accepted":
                graph["graphQueryAcceptance"] = False
            elif case == "wrong-counts":
                graph["nativeCounts"]["nodes"] = 0
            elif case == "wrong-source":
                graph["scope"]["sourceLakehouseId"] = OTHER
            elif case == "missing-owner":
                receipt["bodySha256"] = None
            else:
                inv["recoverableItems"].append({"displayName": "DA_Furusato_AgentCompat_001"})
            with self.subTest(case=case), self.assertRaises(rt.SafetyError):
                compat.agent_handoff(s, inv, owned, TEMP, receipt, definition, graph, frozen, "published")

    def test_ci_or_direct_model_is_not_added_implicitly(self):
        for case in ("ci", "model"):
            s, inv, owned, receipt, definition, graph, frozen = handoff_fixtures()
            if case == "ci":
                part = next(p for p in frozen["parts"] if p["path"].endswith("stage_config.json"))
                settings = json.loads(base64.b64decode(part["payload"]))
                settings["experimental"]["codeInterpreterEnabled"] = False
                part["payload"] = json_part(part["path"], settings)["payload"]
            else:
                frozen["parts"] = [p for p in frozen["parts"] if "semantic_model-frozen/" not in p["path"]]
            with self.subTest(case=case), self.assertRaises(rt.SafetyError):
                compat.agent_handoff(s, inv, owned, TEMP, receipt, definition, graph, frozen, "published")


if __name__ == "__main__":
    unittest.main()
