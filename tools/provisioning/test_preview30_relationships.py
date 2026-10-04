"""Offline companion/source/guard checks, never Graph-query acceptance evidence."""
from __future__ import annotations

import base64
import copy
import gzip
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import build_preview30 as builder
import preview30_deploy as deploy
import preview30_runtime as rt
from preview30_notebooks import package
from preview30_ontology import (
    encode_definition, generate, generate_relationships, lineage, verify_relationships_readback,
)
from test_preview30_runtime import scope


LAKEHOUSE_ID = "44444444-4444-4444-8444-444444444444"
CORE_ID = "55555555-5555-4555-8555-555555555555"
COMPANION_ID = "66666666-6666-4666-8666-666666666666"
PINNED = "2026-01-01T00:00:00+00:00"


def replacements():
    s = scope()
    name = "ONT_Furusato_Relationships_001"
    return {
        "ontology.displayName": name, "ontology.logicalId": lineage("item", s["workspaceId"] + "/" + name),
        "workspace.id": s["workspaceId"], "workspace.name": s["workspaceName"],
        "source.lakehouse.id": LAKEHOUSE_ID, "source.lakehouse.displayName": "LH_Furusato_001",
        "source.lakehouse.oneLakeRootUrl": f"https://onelake.dfs.fabric.microsoft.com/{s['workspaceId']}/{LAKEHOUSE_ID}",
        "source.lakehouse.sqlEndpoint": "unit-test.example.invalid",
        "source.binding.pinnedAtUtc": PINNED,
    }


class RelationshipsBuilderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.template = rt.load(rt.BASE / "ontology/ontology-full-definition-template.json")
        cls.core, _ = generate(cls.template)
        cls.parts, cls.contract = generate_relationships(cls.template)
        cls.definition = encode_definition(cls.parts, replacements())

    def test_only_original_timeseries_property_is_removed(self):
        before = copy.deepcopy(self.template)
        parts, contract = generate_relationships(self.template)
        self.assertEqual(before, self.template)
        self.assertEqual((parts, contract), (self.parts, self.contract))
        self.assertEqual({path for path in self.core if self.core[path] != parts[path]},
                         {"entities/Municipality.tmdl"})
        self.assertNotIn("\tproperty IncomingDonationAmountYen", parts["entities/Municipality.tmdl"])
        self.assertNotIn("\tproperty PrefectureId", parts["entities/Municipality.tmdl"])
        self.assertEqual(sum(line.startswith("\tproperty ") for path, text in parts.items()
                             if path.startswith("entities/") for line in text.splitlines()), 72)
        self.assertEqual(contract["timeseriesProperties"], 0)
        self.assertEqual(contract["staticProperties"], 72)
        self.assertEqual(contract["relationshipTypes"], 15)

    def test_stable_business_identities_and_sources(self):
        removed = lineage("property", "Municipality/IncomingDonationAmountYen")
        identities = lambda parts: sorted(
            line.strip() for text in parts.values() for line in text.splitlines()
            if line.strip().startswith("lineageTag:") and removed not in line)
        self.assertEqual(identities(self.core), identities(self.parts))
        for path in self.core:
            if path.startswith("tables/") or path in {"expressions.tmdl", "entityRelationships.tmdl"}:
                self.assertEqual(self.core[path], self.parts[path])
        self.assertEqual(self.contract["sourceContract"]["nativeOperationalCore"]["staticProperties"], 73)
        self.assertTrue(self.contract["sourceContract"]["sameLakehouse"])
        self.assertFalse(self.contract["sourceContract"]["copiesBusinessData"])
        self.assertFalse(self.contract["deployment"]["dataAgentSourceRoutingChanged"])
        self.assertEqual(self.contract["graph"]["queryAcceptance"], "required-not-assessed")

    def test_not_a_native_core_patch_or_general_timeseries_filter(self):
        changed = copy.deepcopy(self.template)
        municipality = next(p["content"] for p in changed["parts"]
                            if p["path"].startswith("EntityTypes/") and p["path"].count("/") == 2
                            and p["content"].get("name") == "Municipality")
        municipality["timeseriesProperties"].append(
            {**municipality["timeseriesProperties"][0], "name": "UnexpectedObservation"})
        with self.assertRaises(ValueError):
            generate_relationships(changed)
        municipality["timeseriesProperties"].pop()
        municipality["properties"].append({**municipality["properties"][0], "name": "PrefectureId"})
        with self.assertRaises(ValueError):
            generate_relationships(changed)

    def test_bound_generation2_and_reordered_readback(self):
        self.assertNotIn("format", self.definition)
        self.assertFalse(any(part["path"].startswith("EntityTypes/") for part in self.definition["parts"]))
        actual = copy.deepcopy(self.definition)
        actual["parts"].reverse()
        verify_relationships_readback(actual, self.definition)
        with self.assertRaises(ValueError):
            encode_definition(self.parts, {})

    def test_readback_rejects_same_count_identity_source_and_relation_drift(self):
        cases = [
            ("entities/Municipality.tmdl", "keyProperty: MunicipalityId", "keyProperty: MunicipalityName"),
            ("entities/Municipality.tmdl", lineage("entity", "Municipality"), lineage("entity", "Other")),
            ("tables/ot_municipality.tmdl", LAKEHOUSE_ID, CORE_ID),
            ("entityRelationships.tmdl", "MunicipalityInPrefecture", "ChangedRelation"),
        ]
        for path, old, new in cases:
            actual = copy.deepcopy(self.definition)
            part = next(p for p in actual["parts"] if p["path"] == path)
            text = base64.b64decode(part["payload"]).decode("utf-8")
            self.assertIn(old, text)
            part["payload"] = base64.b64encode(text.replace(old, new).encode()).decode()
            with self.subTest(path=path, old=old), self.assertRaises(ValueError):
                verify_relationships_readback(actual, self.definition)
        duplicate = copy.deepcopy(self.definition)
        duplicate["parts"].append(duplicate["parts"][0])
        with self.assertRaises(ValueError):
            verify_relationships_readback(duplicate, self.definition)

    def test_native_crlf_readback_preserves_strict_structural_comparison(self):
        actual = copy.deepcopy(self.definition)
        for part in actual["parts"]:
            text = base64.b64decode(part["payload"]).decode("utf-8")
            part["payload"] = base64.b64encode(text.replace("\n", "\r\n").encode("utf-8")).decode("ascii")
        verify_relationships_readback(actual, self.definition)

    def test_readback_rejects_operational_timeseries_tree(self):
        with self.assertRaises(ValueError):
            verify_relationships_readback(encode_definition(self.core, replacements()), self.definition)

    def test_targeted_build_only_writes_companion_paths(self):
        with patch.object(builder, "write") as write, patch.object(builder, "save") as save:
            result = builder.build_relationships()
        root = rt.PREVIEW / "ontology/relationships"
        self.assertTrue(all(root in call.args[0].parents for call in write.call_args_list))
        self.assertEqual(save.call_args.args[0], root / "contract.json")
        self.assertFalse(result["deployed"])

    def test_fresh_package_contains_companion_and_pins_inputs(self):
        files = json.loads(gzip.decompress(package(data=False)))
        prefix = "workshop/v3.0.0-preview/"
        self.assertIn(prefix + "ontology/relationships/contract.json", files)
        for path, text in self.parts.items():
            self.assertEqual(base64.b64decode(files[prefix + "ontology/relationships/definition/" + path]),
                             text.encode("utf-8"))
        roots = tuple(prefix + folder + "/" for folder in (
            "ontology/definition", "ontology/relationships/definition", "data-agent/definition",
            "powerbi/Furusato_Analytics.SemanticModel"))
        exact = set(rt.RUNTIME_INPUT_FILES) | {
            prefix + "provisioning/gold-contract.json", prefix + "powerbi/native-metrics-contract.json",
            prefix + "ontology/relationships/contract.json",
        }
        inputs = {name: hashlib.sha256(base64.b64decode(value)).hexdigest()
                  for name, value in files.items() if name in exact or name.startswith(roots)
                  or (any(name.startswith(prefix + "data-agent/candidates/" + profile + "/")
                          for profile in rt.CORRECTED_PROFILE_DIRECTORIES)
                      and Path(name).suffix in {".json", ".txt", ".sql"})}
        self.assertEqual(rt.digest(inputs), rt.candidate_fingerprint())


class RelationshipsPlanTests(unittest.TestCase):
    def plan(self, **kwargs):
        return rt.build_plan(scope(), {"items": [], "recoverableItems": []},
                             {"treeSha256": "b" * 64, "files": {}}, **kwargs)

    def test_core_defaults_unchanged_and_opt_in_adds_only_companion(self):
        default = self.plan()
        opted = self.plan(include_relationships=True)
        self.assertNotIn("relationshipsCompanion", default)
        self.assertEqual(opted["resources"][:-1], default["resources"])
        self.assertEqual(opted["resources"][-1]["displayName"], "ONT_Furusato_Relationships_001")
        self.assertFalse(opted["relationshipsCompanion"]["automaticGraphMaterialization"])
        self.assertFalse(opted["relationshipsCompanion"]["dataAgentSourceRoutingChanged"])
        self.assertNotEqual(default["planSha256"], opted["planSha256"])
        s = scope()
        gate = {**{k: s[k] for k in ("workspaceId", "folderId", "participantId")},
                "scopeSha256": rt.scope_fingerprint(s), "planSha256": default["planSha256"],
                "allowCloudMutations": True, "folderMappingVerified": True,
                "approvedAt": PINNED, "folderMappingEvidence": "unit-test-only"}
        with self.assertRaises(rt.SafetyError):
            rt.validate_gate(s, opted, gate, default["planSha256"])
        gate["planSha256"] = opted["planSha256"]
        rt.validate_gate(s, opted, gate, opted["planSha256"])

    def test_recoverable_companion_blocks_optional_plan(self):
        plan = rt.build_plan(scope(), {"items": [], "recoverableItems": [
            {"displayName": "ont_furusato_relationships_001", "type": "Ontology"}]},
            {"treeSha256": "b" * 64, "files": {}}, include_relationships=True)
        self.assertEqual(len(plan["blockers"]), 1)


def fake_deployment():
    s = scope()
    items = {
        "ontology": {"id": CORE_ID, "type": "Ontology", "displayName": "ONT_Furusato_001", "folderId": s["folderId"]},
        "lakehouse": {"id": LAKEHOUSE_ID, "type": "Lakehouse", "displayName": "LH_Furusato_001", "folderId": s["folderId"]},
    }
    d = SimpleNamespace(
        scope=s, evidence=Path("unused-mocked-evidence"),
        plan={"relationshipsCompanion": {"createOnly": True}},
        resources={r["key"]: r for r in rt.planned_resources("001", include_relationships=True)},
        state={"items": items, "sourceVerification": {"verified": True},
               "relationshipsSourcePinnedAtUtc": PINNED,
               "ontologyNativeUiHandoff": {"automatedTmdlWritesDisabled": True}},
        prefix=f"/workspaces/{s['workspaceId']}", checkpoint=Mock(), client=Mock(),
        require_owned=Mock(side_effect=lambda key: items[key]),
        create=Mock(return_value={"id": COMPANION_ID}),
    )
    d.client.paged.return_value = []

    def request(method, path, **kwargs):
        if method != "GET":
            raise AssertionError("Only create() may perform the single authorized mutation.")
        values = {
            d.prefix: {"displayName": s["workspaceName"]},
            d.prefix + f"/folders/{s['folderId']}": {"id": s["folderId"]},
            d.prefix + f"/ontologies/{CORE_ID}": {"id": CORE_ID, "properties": {"generation": 2}},
            d.prefix + f"/ontologies/{COMPANION_ID}": {"id": COMPANION_ID, "properties": {"generation": 2}},
            d.prefix + f"/lakehouses/{LAKEHOUSE_ID}": {"properties": {
                "sqlEndpointProperties": {"connectionString": replacements()["source.lakehouse.sqlEndpoint"]},
                "oneLakeFilesPath": replacements()["source.lakehouse.oneLakeRootUrl"] + "/Files",
            }},
        }
        return SimpleNamespace(json=lambda: values[path])

    d.client.request.side_effect = request
    d.definition = Mock(side_effect=lambda *a, **k: copy.deepcopy(d.create.call_args.kwargs["definition"]))
    return d


class RelationshipsDeploymentTests(unittest.TestCase):
    def test_no_opt_in_is_refused_before_any_service_request(self):
        d = fake_deployment()
        d.resources.pop("relationshipsOntology")
        with patch.object(deploy, "Deployment", return_value=d), self.assertRaises(rt.SafetyError):
            deploy.deploy_relationships(SimpleNamespace())
        d.client.request.assert_not_called()
        d.create.assert_not_called()

    def test_unverified_sources_and_notebook_flag_refused(self):
        for flag in ("sources", "notebook"):
            d = fake_deployment()
            if flag == "sources":
                d.state["sourceVerification"]["verified"] = False
            with (self.subTest(flag=flag), patch.object(deploy, "Deployment", return_value=d),
                  self.assertRaises(rt.SafetyError)):
                deploy.deploy_relationships(SimpleNamespace(run_notebook01=flag == "notebook"))
            d.client.request.assert_not_called()
            d.create.assert_not_called()

    def test_native_core_untouched_and_exact_reproducible_handoff(self):
        d = fake_deployment()
        before_core = copy.deepcopy(d.state["items"]["ontology"])
        with patch.object(deploy, "Deployment", return_value=d), patch.object(deploy, "save") as save:
            result = deploy.deploy_relationships(SimpleNamespace())
        self.assertEqual(d.create.call_args.args, ("relationshipsOntology",))
        self.assertEqual(d.create.call_count, 1)
        d.definition.assert_called_once_with(COMPANION_ID, skill="fabriciq-ontology-cli")
        self.assertEqual(d.state["items"]["ontology"], before_core)
        self.assertEqual(result["preservedOperationalOntologyId"], CORE_ID)
        self.assertEqual(result["sourceLakehouseId"], LAKEHOUSE_ID)
        self.assertEqual(result["generation"], 2)
        self.assertEqual(len(result["entitySelection"]), 10)
        self.assertEqual(len(result["relationshipSelection"]), 15)
        self.assertEqual(result["staticProperties"], 72)
        self.assertIsNone(result["managedGraphId"])
        self.assertFalse(result["automaticGraphMaterialization"])
        self.assertFalse(result["copiedBusinessData"])
        self.assertFalse(result["dataAgentSourceRoutingChanged"])
        self.assertEqual(result["graphQueryAcceptance"], "required-not-assessed")
        self.assertEqual(save.call_args.args[0].name, "relationships-native-handoff.json")

    def test_fresh_case_insensitive_collision_refused(self):
        for kind in ("Ontology", "GraphModel"):
            d = fake_deployment()
            d.client.paged.return_value = [{
                "id": COMPANION_ID, "type": kind,
                "displayName": "ont_furusato_relationships_001", "folderId": scope()["folderId"],
            }]
            with (self.subTest(kind=kind), patch.object(deploy, "Deployment", return_value=d),
                  self.assertRaises(rt.SafetyError)):
                deploy.deploy_relationships(SimpleNamespace())
            d.create.assert_not_called()

    def test_generation_failure_never_falls_back(self):
        d = fake_deployment()
        request = d.client.request.side_effect

        def generation_one(method, path, **kwargs):
            if path.endswith("/ontologies/" + COMPANION_ID):
                return SimpleNamespace(json=lambda: {"properties": {"generation": 1}})
            return request(method, path, **kwargs)

        d.client.request.side_effect = generation_one
        with (patch.object(deploy, "Deployment", return_value=d), patch.object(deploy, "save"),
              self.assertRaises(rt.SafetyError)):
            deploy.deploy_relationships(SimpleNamespace())
        self.assertEqual(d.create.call_count, 1)
        d.definition.assert_not_called()
        self.assertNotIn("relationshipsVerification", d.state)

    def test_source_locator_must_match_owned_lakehouse(self):
        d = fake_deployment()
        request = d.client.request.side_effect

        def wrong_source(method, path, **kwargs):
            value = request(method, path, **kwargs).json()
            if "/lakehouses/" in path:
                value["properties"]["oneLakeFilesPath"] = (
                    replacements()["source.lakehouse.oneLakeRootUrl"].replace(LAKEHOUSE_ID, CORE_ID) + "/Files")
            return SimpleNamespace(json=lambda: value)

        d.client.request.side_effect = wrong_source
        with patch.object(deploy, "Deployment", return_value=d), self.assertRaises(rt.SafetyError):
            deploy.deploy_relationships(SimpleNamespace())
        d.create.assert_not_called()

    def test_schema_drift_never_emits_an_accepted_handoff(self):
        d = fake_deployment()

        def changed_definition(*args, **kwargs):
            actual = copy.deepcopy(d.create.call_args.kwargs["definition"])
            actual["parts"] = [part for part in actual["parts"] if part["path"] != "entities/Donation.tmdl"]
            return actual

        d.definition.side_effect = changed_definition
        with (patch.object(deploy, "Deployment", return_value=d), patch.object(deploy, "save") as save,
              self.assertRaises(ValueError)):
            deploy.deploy_relationships(SimpleNamespace())
        self.assertNotIn("relationshipsVerification", d.state)
        self.assertFalse(any(call.args[0].name == "relationships-native-handoff.json"
                             for call in save.call_args_list))

    def test_one_create_lro_receipt_is_read_back_without_retry(self):
        d = object.__new__(deploy.Deployment)
        d.scope = scope()
        d.prefix = "/workspaces/" + d.scope["workspaceId"]
        d.resources = {"relationshipsOntology": rt.planned_resources("001", include_relationships=True)[-1]}
        item = {"id": COMPANION_ID, "displayName": d.resources["relationshipsOntology"]["displayName"],
                "type": "Ontology", "folderId": d.scope["folderId"]}
        d.state = {"items": {}, "pendingCreates": {}}
        d.client = Mock()
        d.client.paged.side_effect = [[], [], [item]]
        d.client.request.return_value = SimpleNamespace(
            status_code=202, headers={"x-ms-operation-id": "unit-create-operation"})
        checkpoints = []
        d.checkpoint = lambda: checkpoints.append(copy.deepcopy(d.state))
        d.verify_definition = Mock()
        d.allow = Mock()
        d.poll_lro = Mock()
        definition = {"parts": [{"path": "database.tmdl", "payload": "unit-test-only"}]}
        with patch.object(deploy.time, "sleep"):
            actual = d.create("relationshipsOntology", definition=definition, skill="fabriciq-ontology-cli")
        self.assertEqual(actual["id"], COMPANION_ID)
        self.assertEqual(d.client.request.call_count, 1)
        d.poll_lro.assert_called_once_with("unit-create-operation", skill="fabriciq-ontology-cli")
        self.assertTrue(any(checkpoint["pendingCreates"].get("relationshipsOntology", {}).get("operationId")
                            == "unit-create-operation" for checkpoint in checkpoints))
        self.assertFalse(d.state["pendingCreates"])
        self.assertEqual(d.state["items"]["relationshipsOntology"]["desiredDefinitionSha256"], rt.digest(definition))
        self.assertEqual(d.allow.call_args.args[1]["body"]["folderId"], d.scope["folderId"])
        d.verify_definition.assert_called_once_with(
            "relationshipsOntology", item, definition, skill="fabriciq-ontology-cli")

    def test_uncertain_lro_keeps_intent_and_refuses_second_post(self):
        for missing_operation in (True, False):
            d = object.__new__(deploy.Deployment)
            d.scope = scope()
            d.prefix = "/workspaces/" + d.scope["workspaceId"]
            d.resources = {"relationshipsOntology": rt.planned_resources("001", include_relationships=True)[-1]}
            d.state = {"items": {}, "pendingCreates": {}}
            d.client = Mock()
            d.client.paged.return_value = []
            d.client.request.return_value = SimpleNamespace(
                status_code=202, headers={} if missing_operation else {"x-ms-operation-id": "uncertain"})
            d.checkpoint = Mock()
            d.allow = Mock()
            d.poll_lro = Mock(side_effect=rt.SafetyError("LRO timed out"))
            with self.subTest(missing_operation=missing_operation), patch.object(deploy.time, "sleep"):
                with self.assertRaises(rt.SafetyError):
                    d.create("relationshipsOntology", skill="fabriciq-ontology-cli")
                self.assertIn("relationshipsOntology", d.state["pendingCreates"])
                with self.assertRaises(rt.SafetyError):
                    d.create("relationshipsOntology", skill="fabriciq-ontology-cli")
            self.assertEqual(d.client.request.call_count, 1)

    def test_existing_create_receipt_and_pending_intent_guards_apply(self):
        for mode in ("pending", "moved", "unowned", "owned"):
            d = object.__new__(deploy.Deployment)
            d.scope = scope()
            d.prefix = "/workspaces/" + d.scope["workspaceId"]
            d.resources = {"relationshipsOntology": rt.planned_resources("001", include_relationships=True)[-1]}
            item = {"id": COMPANION_ID, "displayName": d.resources["relationshipsOntology"]["displayName"],
                    "type": "Ontology", "folderId": d.scope["folderId"]}
            d.state = {"items": {}, "pendingCreates": {}}
            d.client = Mock()
            d.checkpoint = Mock()
            d.verify_definition = Mock()
            if mode == "pending":
                d.state["pendingCreates"]["relationshipsOntology"] = {"operationId": "unit-operation"}
                d.client.paged.return_value = []
            else:
                d.client.paged.return_value = [item]
                if mode != "unowned":
                    d.state["items"]["relationshipsOntology"] = copy.deepcopy(item)
                if mode == "moved":
                    item["folderId"] = CORE_ID
            with self.subTest(mode=mode):
                if mode == "owned":
                    self.assertEqual(d.create("relationshipsOntology"), item)
                else:
                    with self.assertRaises(rt.SafetyError):
                        d.create("relationshipsOntology")
            d.client.request.assert_not_called()


if __name__ == "__main__":
    unittest.main()
