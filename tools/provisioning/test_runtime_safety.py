"""Regression tests for defects found during the full live workshop deployment."""
from __future__ import annotations

import copy
from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path
import sys
import types
import unittest
from urllib.parse import urlparse
from urllib.request import url2pathname

ROOT = Path(__file__).resolve().parents[2]
WORKSHOP = ROOT / "workshop" / "v2.7.0"


def load_provisioner():
    path = WORKSHOP / "notebooks" / "Notebook_04_Furusato_Provision_Complete_Workshop.ipynb"
    notebook = json.loads(path.read_text(encoding="utf-8"))
    module = types.ModuleType("furusato_live_regression_runtime")
    sys.modules[module.__name__] = module
    runtime = next(
        "".join(cell["source"]) for cell in notebook["cells"]
        if cell["cell_type"] == "code" and "class WorkshopFabricClient:" in "".join(cell["source"])
    )
    exec(compile(runtime, str(path) + ":provisioner-runtime", "exec"), module.__dict__)
    return module


class LiveProvisioningSafetyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = load_provisioner()
        path = WORKSHOP / "notebooks" / "Notebook_01_Furusato_Prepare_Ontology_Data.ipynb"
        cls.notebook = json.loads(path.read_text(encoding="utf-8"))

    def test_participant_is_bound_in_persisted_notebook_not_only_job_parameters(self):
        before = copy.deepcopy(self.notebook)
        bound = self.runtime.bind_notebook_to_lakehouse(
            self.notebook, "workspace", "lakehouse", "LH_Furusato_906",
            participant_id="906",
        )
        parameters = "".join(bound["cells"][1]["source"])
        self.assertIn('PARTICIPANT_ID = "906"', parameters)
        self.assertNotIn('PARTICIPANT_ID = "001"', parameters)
        self.assertEqual(before, self.notebook)
        self.assertEqual(
            bound["metadata"]["dependencies"]["lakehouse"]["default_lakehouse_name"],
            "LH_Furusato_906",
        )

    def test_ambiguous_parameter_assignment_is_rejected(self):
        notebook = copy.deepcopy(self.notebook)
        notebook["cells"][1]["source"].append('PARTICIPANT_ID = "001"\n')
        with self.assertRaises(self.runtime.ProvisioningError):
            self.runtime.bind_notebook_to_lakehouse(
                notebook, "workspace", "lakehouse", "LH_Furusato_906", participant_id="906"
            )

    def test_invalid_participant_is_rejected(self):
        for participant in ("000", "", "1000", "90x"):
            with self.subTest(participant=participant), self.assertRaises(self.runtime.ProvisioningError):
                self.runtime.bind_notebook_to_lakehouse(
                    self.notebook, "workspace", "lakehouse", "LH_Furusato_906",
                    participant_id=participant,
                )

    def test_seed_keeps_documented_path(self):
        self.assertEqual(
            self.runtime.dataset_target_relative_path("seed/donors.csv", "906"),
            "furusato/seed/donors.csv",
        )

    def test_increment_is_not_uploaded_into_watched_folder(self):
        for number in (1, 2, 3):
            path = self.runtime.dataset_target_relative_path(
                f"increment/donation_events_{number:03}.csv", "906"
            )
            self.assertEqual(
                path, f"_provisioning/furusato/906/increment/donation_events_{number:03}.csv"
            )
            self.assertFalse(path.startswith("increment/"))

    def test_provisioning_hands_off_without_claiming_activation(self):
        handoff = self.runtime.activation_handoff()
        self.assertEqual(handoff["state"], "requires_formal_start")
        self.assertEqual(handoff["startOperation"], "start_rule")
        self.assertEqual(handoff["stopOperation"], "stop_rule")
        self.assertFalse(handoff["definitionShouldRun"])
        self.assertFalse(handoff["runningMetadataIsDeliveryProof"])
        self.assertEqual(handoff["uploadApi"], "PutBlob")
        self.assertEqual(handoff["uploadIfNoneMatch"], "*")
        self.assertTrue(handoff["manualFallbackRequiresSeparateApproval"])

    def test_unexpected_dataset_path_fails_closed(self):
        with self.assertRaises(self.runtime.ProvisioningError):
            self.runtime.dataset_target_relative_path("other/donors.csv", "906")

    def test_all_notebook_cells_fit_the_live_fabric_editor(self):
        for path in (WORKSHOP / "notebooks").glob("*.ipynb"):
            notebook = json.loads(path.read_text(encoding="utf-8"))
            for index, cell in enumerate(notebook["cells"]):
                with self.subTest(notebook=path.name, cell=index):
                    self.assertLess(len("".join(cell["source"]).encode("utf-8")), 500_000)

    def test_split_payload_executes_in_order_without_external_files(self):
        path = WORKSHOP / "notebooks" / "Notebook_04_Furusato_Provision_Complete_Workshop.ipynb"
        notebook = json.loads(path.read_text(encoding="utf-8"))
        cells = [
            cell for cell in notebook["cells"]
            if "furusato-provisioning-payload" in cell.get("metadata", {}).get("tags", [])
        ]
        self.assertGreater(len(cells), 1)
        namespace = {}
        for cell in cells:
            exec("".join(cell["source"]), namespace)
        payload = namespace["PROVISIONING_PAYLOAD"]
        self.assertNotIn("_PAYLOAD_CHUNKS", namespace)
        self.assertEqual(len(payload["datasetGzipBase64"]), 11)
        self.assertEqual(payload["packageVersion"], "2.7.0")
        for relative, text in payload["bundle"].items():
            self.assertEqual(
                text.encode("utf-8"),
                (WORKSHOP / "provisioning" / "bundle" / relative).read_bytes(),
            )

    def test_full_file_verification_does_not_use_preview_head(self):
        class FileSystem:
            def __init__(self, data=None):
                self.data = data
                self.writes = 0

            def exists(self, path):
                return self.data is not None

            def head(self, path, max_bytes):
                raise AssertionError("A preview API must never verify complete file bytes")

            def cp(self, source, destination):
                Path(url2pathname(urlparse(destination).path)).write_bytes(self.data)
                return True

            def put(self, path, text, overwrite):
                assert self.data is None and not overwrite
                self.data = text.encode("utf-8")
                self.writes += 1
                return True

        raw = ("自治体,Donation\n" * 80_000).encode("utf-8")
        fs = FileSystem()
        utils = types.SimpleNamespace(fs=fs)
        self.assertEqual(self.runtime.ensure_onelake_text_file(utils, "abfss://test", raw), "CREATED")
        self.assertEqual(self.runtime.ensure_onelake_text_file(utils, "abfss://test", raw), "REUSED")
        self.assertEqual(fs.writes, 1)
        fs.data = b"x" + raw[1:]
        with self.assertRaises(self.runtime.ConflictError):
            self.runtime.ensure_onelake_text_file(utils, "abfss://test", raw)
        self.assertEqual(fs.writes, 1)

    def test_schema_enabled_table_gate_uses_managed_delta_directories(self):
        runtime = self.runtime
        expected = set(runtime.EXPECTED_TABLES) | {runtime.PUBLISH_CONTROL_TABLE}

        class Client:
            def get_lakehouse(self, workspace_id, lakehouse_id):
                return {"properties": {"defaultSchema": "dbo"}}

            def _request(self, *args, **kwargs):
                raise AssertionError("Legacy tables API is not supported for schema-enabled Lakehouses")

        class FileSystem:
            delta_names = set(expected)

            def ls(self, path):
                self.last_path = path
                return [types.SimpleNamespace(name=name, isDir=True) for name in expected | {"not_a_table"}]

            def exists(self, path):
                return path.rsplit("/", 2)[-2] in self.delta_names and path.endswith("/_delta_log")

        fs = FileSystem()
        utils = types.SimpleNamespace(fs=fs)
        actual = runtime.verify_twenty_tables(Client(), utils, "workspace", "lakehouse", "LH_Furusato_906")
        self.assertEqual(actual, expected)
        self.assertTrue(fs.last_path.endswith("/lakehouse/Tables/dbo"))
        fs.delta_names.remove("ot_donation")
        with self.assertRaises(runtime.ProvisioningError):
            runtime.verify_twenty_tables(Client(), utils, "workspace", "lakehouse", "LH_Furusato_906")

    def test_ontology_references_real_default_schema(self):
        template = json.loads((WORKSHOP / "ontology/ontology-full-definition-template.json").read_text("utf-8"))
        schemas = []

        def visit(value):
            if isinstance(value, dict):
                if "sourceSchema" in value:
                    schemas.append(value["sourceSchema"])
                for child in value.values():
                    visit(child)
            elif isinstance(value, list):
                for child in value:
                    visit(child)

        visit(template["parts"])
        self.assertEqual(schemas, ["dbo"] * 25)

    def test_reflex_keeps_dynamic_subject_and_explicit_pipeline_default(self):
        bundle = WORKSHOP / "provisioning/bundle"
        pipeline = json.loads((bundle / "data-pipeline/pipeline-content.json").read_text("utf-8"))
        entities = json.loads((bundle / "reflex/ReflexEntities.json").read_text("utf-8"))
        rule = next(e["payload"]["definition"] for e in entities if e.get("payload", {}).get("definition", {}).get("type") == "Rule")
        instance = json.loads(rule["instance"])
        action = next(row for step in instance["steps"] for row in step["rows"] if row.get("kind") == "FabricItemInvocation")
        parameters = next(a["values"] for a in action["arguments"] if a["name"] == "parameters")
        parsed = {}
        for parameter in parameters:
            args = {a["name"]: a for a in parameter["arguments"]}
            parsed[args["parameterName"]["value"]] = args
        self.assertEqual(set(parsed), set(pipeline["properties"]["parameters"]))
        self.assertEqual(
            parsed["IncrementFileName"]["parameterValue"]["values"],
            [{"type": "string", "value": "donation_events_001.csv"}],
        )
        for name in ("Type", "Subject", "Source"):
            value = parsed[name]["parameterValue"]["values"][0]
            self.assertEqual(value["kind"], "EventFieldReference")
            self.assertEqual(value["arguments"][0]["value"], "___" + name.lower())
        self.assertFalse(rule["settings"]["shouldRun"])

    def graph_client(self, *, compiled, recent=None, response=None):
        runtime = self.runtime
        now = [datetime(2026, 9, 5, tzinfo=timezone.utc)]

        def sleep(seconds):
            now[0] += timedelta(seconds=seconds)

        class Client(runtime.WorkshopFabricClient):
            def get_definition(self, *args, **kwargs):
                return {"parts": [
                    runtime.encode_part("graphType.json", {"nodeTypes": [{}] * (10 if compiled else 0), "edgeTypes": [{}] * (15 if compiled else 0)}),
                    runtime.encode_part("dataSources.json", {"dataSources": [{}] * (11 if compiled else 0)}),
                    runtime.encode_part("graphDefinition.json", {"nodeTables": [{}] * (10 if compiled else 0), "edgeTables": [{}] * (15 if compiled else 0)}),
                ]}

            def recent_jobs(self, workspace, item, job_type, **kwargs):
                if job_type != "Refresh":
                    raise AssertionError("Discovery must use the registered Graph job type")
                return recent or []

            def poll_job(self, workspace, item, job_id):
                return {"id": job_id, "status": "Completed"}

            def _request(self, *args, **kwargs):
                if response is None:
                    raise AssertionError("A second refresh must not be submitted")
                return response

        return Client(lambda: "test-only", lambda: "test-only", clock=lambda: now[0],
                      sleeper=sleep, timeout_seconds=3, poll_interval_seconds=1)

    def test_empty_generated_graph_is_never_refreshed(self):
        client = self.graph_client(compiled=False)
        with self.assertRaises(self.runtime.OperationTimeoutError):
            client.run_or_reuse_graph_refresh("workspace", "graph")

    def test_matching_automatic_graph_refresh_is_reused(self):
        client = self.graph_client(compiled=True, recent=[{"id": "automatic-refresh", "status": "Completed"}])
        result, status = client.run_or_reuse_graph_refresh("workspace", "graph")
        self.assertEqual(result["id"], "automatic-refresh")
        self.assertEqual(status, "RECENT_REUSED")

    def test_unverified_synchronous_graph_response_fails_closed(self):
        response = types.SimpleNamespace(status_code=200, headers={}, content=b"{}", json=lambda: {})
        client = self.graph_client(compiled=True, response=response)
        with self.assertRaises(self.runtime.AmbiguousOutcomeError):
            client.run_or_reuse_graph_refresh("workspace", "graph")

    def test_empty_graph_response_waits_for_late_job_without_resubmission(self):
        response = types.SimpleNamespace(status_code=200, headers={}, content=b"{}", json=lambda: {})
        client = self.graph_client(compiled=True, response=response)
        submitted = []

        def request(*args, **kwargs):
            submitted.append(client.clock())
            return response

        def recent(workspace, item, job_type, **kwargs):
            self.assertEqual(job_type, "Refresh")
            if submitted and client.clock() >= submitted[0] + timedelta(seconds=1):
                return [{"id": "late-refresh", "status": "Completed"}]
            return []

        client._request = request
        client.recent_jobs = recent
        result, status = client.run_or_reuse_graph_refresh("workspace", "graph")
        self.assertEqual(result["id"], "late-refresh")
        self.assertEqual(status, "STARTED")
        self.assertEqual(len(submitted), 1)

    def test_analytics_recognizes_fully_qualified_fabric_schema(self):
        path = WORKSHOP / "notebooks/Notebook_05_Furusato_Analytics_Quality_and_BI.ipynb"
        notebook = json.loads(path.read_text("utf-8"))
        module = types.ModuleType("furusato_analytics_schema_regression")
        sys.modules[module.__name__] = module
        exec(compile("".join(notebook["cells"][3]["source"]), str(path), "exec"), module.__dict__)
        for namespace in ("dbo", "Fabric IQ Workshop.LH_Furusato_906.dbo", "`Workspace`.`Lakehouse`.`dbo`"):
            spark = types.SimpleNamespace(sql=lambda query, value=namespace: types.SimpleNamespace(collect=lambda: [(value,)]))
            module._require_schema_enabled_lakehouse(spark)
        for namespace in ("LH_without_schemas", "default", None):
            spark = types.SimpleNamespace(sql=lambda query, value=namespace: types.SimpleNamespace(collect=lambda: [(value,)]))
            with self.assertRaises(module.AnalyticsExtensionError):
                module._require_schema_enabled_lakehouse(spark)

    def test_data_agent_default_false_is_not_confused_with_enabled(self):
        def definition(value):
            return {"parts": [self.runtime.encode_part("Files/Config/draft/stage_config.json", value)]}

        absent = definition({"aiInstructions": "Keep source boundaries."})
        disabled = definition({"aiInstructions": "Keep source boundaries.", "experimental": {"codeInterpreterEnabled": False}})
        enabled = definition({"aiInstructions": "Keep source boundaries.", "experimental": {"codeInterpreterEnabled": True}})
        self.assertTrue(self.runtime.definitions_equal(absent, disabled))
        self.assertFalse(self.runtime.definitions_equal(absent, enabled))

    def test_analytics_calendar_uses_complete_years_and_rejects_bad_bounds(self):
        path = WORKSHOP / "notebooks/Notebook_05_Furusato_Analytics_Quality_and_BI.ipynb"
        notebook = json.loads(path.read_text("utf-8"))
        module = types.ModuleType("furusato_analytics_calendar_regression")
        sys.modules[module.__name__] = module
        exec(compile("".join(notebook["cells"][3]["source"]), str(path), "exec"), module.__dict__)
        start, end = module._calendar_year_bounds(date(2025, 1, 1), date(2026, 9, 1))
        self.assertEqual((start, end), (date(2025, 1, 1), date(2026, 12, 31)))
        self.assertEqual((end - start).days + 1, 730)
        self.assertEqual(
            module._calendar_year_bounds(datetime(2024, 2, 29, 12), datetime(2024, 9, 1)),
            (date(2024, 1, 1), date(2024, 12, 31)),
        )
        for bounds in ((None, date(2026, 1, 1)), (date(2026, 1, 1), None), (date(2026, 2, 1), date(2025, 1, 1))):
            with self.assertRaises(module.AnalyticsExtensionError):
                module._calendar_year_bounds(*bounds)
        plan = module.build_plan(module.AnalyticsExtensionConfig(participant_id="001"))
        self.assertEqual(plan["document"]["calendarCoverage"], "complete-calendar-years")

    def test_data_agent_hydration_keeps_binding_and_exposure_guards(self):
        original = {
            "type": "lakehouse_tables", "artifactId": "lakehouse-a", "workspaceId": "workspace-a",
            "dataSourceInstructions": "Static snapshot only.", "metadata": {},
            "elements": [{"type": "table_grouping", "display_name": "Tables", "is_selected": True, "id": "old-group",
                          "children": [{"type": "lakehouse_tables.table", "display_name": "ot_donation",
                                        "is_selected": True, "id": "old-table", "description": "Donation grain.",
                                        "children": [{"type": "lakehouse_tables.column", "display_name": "DonationId",
                                                      "is_selected": True, "id": "old-column", "data_type": "bigint",
                                                      "description": "Stable identity.", "children": []}]}]}],
        }
        hydrated = copy.deepcopy(original)
        hydrated["elements"][0]["id"] = "new-group"
        hydrated["elements"][0]["children"][0]["id"] = "new-table"
        hydrated["elements"][0]["children"][0]["children"][0]["id"] = "new-column"
        hydrated["elements"][0]["children"].append({
            "type": "lakehouse_tables.table", "display_name": "unapproved_raw", "is_selected": False,
            "children": [{"type": "lakehouse_tables.column", "display_name": "SensitiveKey", "is_selected": True}],
        })

        def definition(value):
            return {"parts": [self.runtime.encode_part("Files/Config/draft/lakehouse/datasource.json", value)]}

        self.assertTrue(self.runtime.definitions_equal(definition(original), definition(hydrated)))
        for field in ("artifactId", "workspaceId", "dataSourceInstructions"):
            changed = copy.deepcopy(hydrated)
            changed[field] = "different"
            self.assertFalse(self.runtime.definitions_equal(definition(original), definition(changed)))
        changed = copy.deepcopy(hydrated)
        changed["elements"][0]["children"][-1]["is_selected"] = True
        self.assertFalse(self.runtime.definitions_equal(definition(original), definition(changed)))
        changed = copy.deepcopy(hydrated)
        changed["elements"][0]["children"][0]["description"] = "Wrong grain."
        self.assertFalse(self.runtime.definitions_equal(definition(original), definition(changed)))


if __name__ == "__main__":
    unittest.main(verbosity=2)
