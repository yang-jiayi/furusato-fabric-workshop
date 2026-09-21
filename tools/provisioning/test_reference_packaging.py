"""Offline source/payload/profile sealing and opt-in plan regression tests."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import reference_ontology

import reference_assets
import reseal_runtime
import workshop_runtime as runtime

ROOT = Path(__file__).resolve().parents[2]
WORKSHOP = ROOT / "workshop/v2.7.0"


class ReferencePackagingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.generated = reference_assets.build_assets(ROOT)
        cls.global_text = "Synthetic test-only explicitly frozen reference GLOBAL.\n"

    def payload(self, *, profile=True):
        bundle = dict(self.generated)
        stage = "data-agent/Files/Config/published/stage_config.json"
        bundle[stage] = (WORKSHOP / "provisioning/bundle" / stage).read_text("utf-8")
        if profile:
            bundle["ai-reference/global-instructions.txt"] = self.global_text
            bundle["ai-reference/global-profile.json"] = json.dumps({
                "schemaVersion": "furusato-reference-global/v1",
                "sha256": hashlib.sha256(self.global_text.encode()).hexdigest(),
                "status": "candidate",
            })
        return {"bundle": bundle, "assetHashes": {
            name: name + "-hash" for name in (
                "lakehouseSpec", "eventhouseSpec", "kqlSchema", "notebook01",
                "pipeline", "ontologyTemplate", "dataAgent", "reflex", "aiReference",
            )
        }}

    def test_generated_assets_are_deterministic_source_exact_and_do_not_freeze_global(self):
        self.assertEqual(self.generated, reference_assets.build_assets(ROOT))
        self.assertNotIn("ai-reference/global-instructions.txt", self.generated)
        contract = json.loads(self.generated["ai-reference/contract.json"])
        self.assertEqual(len(contract["sqlObjects"]), 6)
        self.assertEqual(len(contract["sqlDdlOrder"]), 7)
        self.assertEqual(contract["kqlReferenceManagementCommandCount"], 8)
        self.assertNotIn("AgentObservationLeaders", contract["kqlFunctions"])
        for path, expected in contract["files"].items():
            self.assertEqual(hashlib.sha256(self.generated[path].encode()).hexdigest(), expected)
        for name in contract["sqlDdlOrder"]:
            self.assertEqual(
                self.generated["ai-reference/sql/" + name].encode(),
                (ROOT / "tools/data-agent/reference-models" / name).read_bytes(),
            )
        for name in contract["kqlFunctions"]:
            self.assertEqual(
                self.generated[f"ai-reference/kql/{name}.kql"].encode(),
                (ROOT / f"tools/data-agent/operational-functions/{name}.kql").read_bytes(),
            )

    def test_missing_or_unpinned_global_never_falls_back_to_released_instructions(self):
        with self.assertRaisesRegex(runtime.ProvisioningError, "incomplete"):
            runtime.load_reference_assets(self.payload(profile=False))
        for defect in ("hash", "status", "empty", "bom"):
            payload = self.payload()
            if defect in {"hash", "status"}:
                profile = json.loads(payload["bundle"]["ai-reference/global-profile.json"])
                profile["sha256" if defect == "hash" else "status"] = "untrusted"
                payload["bundle"]["ai-reference/global-profile.json"] = json.dumps(profile)
            else:
                payload["bundle"]["ai-reference/global-instructions.txt"] = "" if defect == "empty" else "\ufeff" + self.global_text
            with self.subTest(defect=defect), self.assertRaises(runtime.ProvisioningError):
                runtime.load_reference_assets(payload)
        assets = runtime.load_reference_assets(self.payload())
        self.assertEqual(assets["stageConfig"]["aiInstructions"], self.global_text)
        self.assertEqual(assets["globalProfile"]["status"], "candidate")

    def test_incomplete_sql_kql_or_module_contract_fails_before_import(self):
        for field in ("sqlDdlOrder", "kqlFunctions", "modules"):
            payload = self.payload()
            contract = json.loads(payload["bundle"]["ai-reference/contract.json"])
            contract[field] = contract[field][:-1]
            payload["bundle"]["ai-reference/contract.json"] = json.dumps(contract)
            with self.subTest(field=field), self.assertRaisesRegex(runtime.ProvisioningError, "inventory"):
                runtime.load_reference_assets(payload)
        payload = self.payload()
        payload["bundle"]["ai-reference/sql/060_donation_trace_by_id.sql"] += "\n"
        with self.assertRaisesRegex(runtime.ProvisioningError, "digest mismatch"):
            runtime.load_reference_assets(payload)

    def test_sealed_helpers_import_without_driver_credentials_repository_files_or_network(self):
        assets = runtime.load_reference_assets(self.payload())
        modules = runtime.load_reference_modules(assets)
        self.assertEqual(set(modules), set(assets["contract"]["modules"]))
        self.assertEqual(runtime.load_reference_modules(assets), modules)
        self.assertEqual(modules["reference_ontology"].PATH_COUNTS["staticProperties"], 21)
        self.assertTrue(all(module.__package__.startswith("_furusato_reference_") for module in modules.values()))

    def test_default_preview_retains_eight_items_and_opt_in_adds_separate_ontology(self):
        config = runtime.ProvisioningConfig(participant_id="912")
        baseline = runtime.build_preview_plan(
            config, self.payload(profile=False), workspace_name="unit", folder_id="folder", existing_items=[],
        )
        self.assertEqual(len(baseline.entries), 8)
        self.assertEqual(next(entry.display_name for entry in baseline.entries if entry.key == "dataAgent"), "DA_Furusato_912")
        self.assertIsNone(baseline.reference_target)
        config.enable_ai_reference_architecture = True
        extended = runtime.build_preview_plan(
            config, self.payload(), workspace_name="unit", folder_id="folder", existing_items=[],
        )
        self.assertEqual(len(extended.entries), 9)
        self.assertEqual(next(entry.display_name for entry in extended.entries if entry.key == "dataAgent"), "DA_Furusato_AIReference_912")
        self.assertIn("ONT_Furusato_AIPath_912", [entry.display_name for entry in extended.entries])
        self.assertNotEqual(extended.sha256, baseline.sha256)

    def test_authorized_existing_target_never_becomes_an_implicit_fourth_agent(self):
        config = runtime.ProvisioningConfig(
            participant_id="912", enable_ai_reference_architecture=True,
            reference_agent_name="Authorized_existing_candidate",
            reference_agent_role="authorized-candidate",
            reference_agent_expected_id="90000000-0000-4000-8000-000000000001",
        )
        missing = runtime.build_preview_plan(
            config, self.payload(), workspace_name="unit", folder_id="folder", existing_items=[],
        )
        self.assertTrue(missing.blockers)
        actual = {"id": config.reference_agent_expected_id, "displayName": config.reference_agent_name, "type": "DataAgent"}
        existing = runtime.build_preview_plan(
            config, self.payload(), workspace_name="unit", folder_id="folder", existing_items=[actual],
        )
        self.assertFalse(existing.blockers)
        selected = next(entry for entry in existing.entries if entry.key == "dataAgent")
        self.assertEqual(selected.current_status, "EXISTS_REQUIRES_EXACT_VERIFICATION")
        self.assertEqual(existing.sha256, missing.sha256)

    def test_frozen_global_packaging_never_writes_the_released_global(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / "explicit-profile.txt"
            source.write_bytes(self.global_text.encode())
            released = root / "workshop/v2.7.0/data-agent/agent-instructions.txt"
            released.parent.mkdir(parents=True)
            released.write_bytes(b"released global remains exact\n")
            expected = hashlib.sha256(source.read_bytes()).hexdigest()
            reseal_runtime.freeze_reference_global(root, source, expected, "candidate")
            self.assertEqual(released.read_bytes(), b"released global remains exact\n")
            result = root / "workshop/v2.7.0/provisioning/bundle/ai-reference/global-profile.json"
            self.assertEqual(json.loads(result.read_bytes())["sha256"], expected)
            before = result.read_bytes()
            with self.assertRaises(SystemExit):
                reseal_runtime.freeze_reference_global(root, source, "0" * 64, "accepted")
            self.assertEqual(result.read_bytes(), before)

    def test_notebook_runtime_is_generated_byte_exact_from_canonical_source(self):
        notebook = json.loads((WORKSHOP / "notebooks/Notebook_04_Furusato_Provision_Complete_Workshop.ipynb").read_text("utf-8"))
        actual = reseal_runtime.notebook_code_source(notebook, "class WorkshopFabricClient:")
        self.assertEqual(actual.encode(), (ROOT / "tools/provisioning/workshop_runtime.py").read_bytes())
        parameters = "".join(next(cell for cell in notebook["cells"] if "# Fabric parameter cell" in "".join(cell["source"]))["source"])
        self.assertIn("ENABLE_AI_REFERENCE_ARCHITECTURE = False", parameters)
        self.assertIn("ENABLE_UNIFIED_DATA_AGENT = False", parameters)

    def test_notebook_orchestration_orders_native_objects_before_agent_discovery(self):
        self.check_notebook_orchestration(unified=False)

    def test_unified_orchestration_uses_teaching_ontology_and_one_primary_agent(self):
        self.check_notebook_orchestration(unified=True)

    def check_notebook_orchestration(self, *, unified):
        def identifier(number):
            return f"50000000-0000-4000-8000-{number:012d}"

        workspace_id, folder_id = identifier(1), identifier(2)
        config = runtime.ProvisioningConfig(
            participant_id="912", expected_workspace_name="FixtureWorkspace",
            apply_changes=True, exclusive_create_window_confirmed=True,
            execute_notebook_01=True, create_pipeline=True, refresh_graph=True,
            create_data_agent=True, create_reflex=True, enable_ai_reference_architecture=not unified,
            enable_unified_data_agent=unified,
            operation_timeout_seconds=60, poll_interval_seconds=1,
        )
        names = runtime.build_names(config.participant_id)
        payload = self.payload()
        payload["assetHashes"]["unifiedAgent"] = "unified-fixture-hash"
        payload.update({
            "notebook01": {}, "ontologyTemplate": {},
            "kqlManagementCommands": reseal_runtime.extract_kql_management_commands(
                (WORKSHOP / "kql/Furusato_Eventhouse_Setup_v2.7.0.kql").read_text("utf-8")
            ),
        })
        unified_assets = runtime.load_reference_assets(payload)
        unified_assets["stageConfig"]["experimental"]["codeInterpreterEnabled"] = True
        with patch.object(runtime, "load_unified_assets", return_value=unified_assets):
            plan = runtime.build_preview_plan(
                config, payload, workspace_name=config.expected_workspace_name,
                folder_id=folder_id, existing_items=[],
            )
        config.confirmed_plan_sha256 = plan.sha256
        events = []
        driver = object()
        lakehouse = {
            "id": identifier(3), "type": "Lakehouse", "displayName": names.lakehouse,
            "folderId": folder_id, "properties": {
                "defaultSchema": "dbo",
                "oneLakeFilesPath": f"https://onelake.dfs.fabric.microsoft.com/{workspace_id}/{identifier(3)}/Files",
                "sqlEndpointProperties": {
                    "connectionString": "dynamic-fixture.datawarehouse.fabric.microsoft.com",
                },
            },
        }
        eventhouse = {"id": identifier(4), "type": "Eventhouse", "displayName": names.eventhouse, "folderId": folder_id}
        kql = {
            "id": identifier(5), "type": "KQLDatabase", "displayName": names.kql_database,
            "folderId": folder_id, "properties": {
                "parentEventhouseItemId": eventhouse["id"], "queryServiceUri": "https://fixture.kusto.fabric.microsoft.com",
            },
        }
        client = Mock()
        client.clock = runtime.utc_now
        client.timeout_seconds, client.poll_interval_seconds = 60, 1
        client.get_item.return_value = {"folderId": folder_id, "folderName": "fixture"}
        client.list_items.return_value = []
        client.find_unique_item.return_value = None
        client.wait_for_unique_item.return_value = kql
        client.get_lakehouse.return_value = lakehouse
        client.wait_for_lakehouse_property.return_value = (lakehouse, lakehouse["properties"]["oneLakeFilesPath"])
        client.wait_for_kql_database_property.side_effect = lambda _ws, _id, prop: (kql, kql["properties"][prop])

        def simple_item(_workspace, *, item_type, **kwargs):
            events.append("create:" + item_type)
            return (lakehouse if item_type == "Lakehouse" else eventhouse), "CREATED"

        client.ensure_simple_item.side_effect = simple_item
        client.ensure_definition_item.side_effect = lambda _ws, **kwargs: ({
            "id": identifier(7 if kwargs["item_type"] == "Ontology" else 8),
            "type": kwargs["item_type"], "displayName": kwargs["display_name"], "folderId": folder_id,
        }, "CREATED")
        client.create_item.side_effect = lambda _ws, body: {**body, "id": identifier(6 if body["type"] == "Ontology" else 9)}

        def refresh(_ws, graph_id, **kwargs):
            events.append("refresh:" + graph_id)
            return {"status": "Completed"}, "RECENT_REUSED"

        client.run_or_reuse_graph_refresh.side_effect = refresh
        sql = Mock()
        sql.require_odbc_driver.side_effect = lambda: (events.append("driver-preflight") or driver)
        sql.deploy_reference_sql.side_effect = lambda *args, **kwargs: (events.append("sql") or {"catalogVerified": True})
        kql_helper = Mock()
        kql_helper.provision_kql.side_effect = lambda *args, **kwargs: (events.append("kql") or {"enabled": True})
        agent_helper = Mock()
        agent_helper.configure_reference_agent.side_effect = lambda *args, **kwargs: (events.append("agent") or {"state": "CREATED"})
        modules = {
            "reference_sql": sql, "reference_kql": kql_helper,
            "reference_ontology": reference_ontology, "reference_agent": agent_helper,
        }
        utils = Mock()
        utils.runtime.context = {
            "currentWorkspaceId": workspace_id, "currentWorkspaceName": config.expected_workspace_name,
            "currentNotebookId": identifier(10), "currentTenantId": identifier(11), "isForInteractive": True,
        }
        utils.fs.mkdirs.return_value = True
        utils.credentials.getToken.side_effect = AssertionError("No live credentials in orchestration tests")
        checkpoint = Mock()
        checkpoint.load.return_value = None
        ontology_namespace = {
            "FabricApiError": RuntimeError, "FabricApiClient": Mock(),
            "build_creation_plan": Mock(return_value=SimpleNamespace(definition={"parts": []})),
            "verify_complete_definition": Mock(return_value={"verified": True}),
        }
        with (
            patch.object(runtime, "WorkshopFabricClient", return_value=client),
            patch.object(runtime, "load_reference_modules", return_value=modules),
            patch.object(runtime, "load_unified_assets", return_value=unified_assets),
            patch.object(runtime, "CheckpointStore", return_value=checkpoint),
            patch.object(runtime, "decode_embedded_dataset", return_value={}),
            patch.object(runtime, "bind_notebook_to_lakehouse", return_value={}),
            patch.object(runtime, "verify_twenty_tables"),
            patch.object(runtime, "verify_kql_schema"),
            patch.object(runtime, "bundle_definition", return_value={"parts": []}),
            patch.object(runtime, "verify_reflex_fail_closed"),
            patch.object(runtime, "wait_for_complete_ontology_definition"),
            patch.object(runtime, "resolve_graph_model", side_effect=lambda _c, _w, name, _i, **kwargs: {
                "id": identifier(12 if "AIPath" in name else 13),
            }),
            patch("builtins.print"),
        ):
            result = runtime.execute_provisioning(
                config, payload, notebookutils=utils, spark=None, ontology_namespace=ontology_namespace,
            )
        self.assertEqual(result["mode"], "Apply")
        self.assertLess(events.index("driver-preflight"), events.index("create:Lakehouse"))
        self.assertLess(events.index("sql"), events.index("kql"))
        self.assertLess(events.index("kql"), events.index("agent"))
        graph_id = identifier(13 if unified else 12)
        self.assertLess(events.index("refresh:" + graph_id), events.index("agent"))
        self.assertIs(sql.deploy_reference_sql.call_args.kwargs["db_driver"], driver)
        self.assertEqual(sql.deploy_reference_sql.call_args.args[0], lakehouse)
        self.assertEqual(sql.deploy_reference_sql.call_args.kwargs["source_wait_timeout"], 60)
        agent_bindings = agent_helper.configure_reference_agent.call_args.args[4]
        if unified:
            self.assertEqual(agent_bindings["ontology"]["itemId"], result["items"]["ontology"]["id"])
            self.assertNotIn("agentOntology", result["items"])
            self.assertNotIn("refresh:" + identifier(12), events)
            self.assertEqual(plan.reference_target["name"], names.data_agent)
            self.assertEqual(len([e for e in plan.entries if e.item_type == "DataAgent"]), 1)
            self.assertTrue(agent_helper.configure_reference_agent.call_args.args[3]["stageConfig"]["experimental"]["codeInterpreterEnabled"])
        else:
            self.assertEqual(agent_bindings["ontology"]["itemId"], result["items"]["agentOntology"]["id"])
            self.assertNotEqual(agent_bindings["ontology"]["itemId"], result["items"]["ontology"]["id"])
            self.assertEqual(result["ontologyCompatibility"]["oneLakeSecurity"], "UNKNOWN")
        self.assertEqual(checkpoint.save.call_args.args[0]["phase"], "complete")
        utils.credentials.getToken.assert_not_called()


if __name__ == "__main__":
    unittest.main()
