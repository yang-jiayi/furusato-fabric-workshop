"""Offline, credential-free contracts for the opt-in reference architecture."""

from __future__ import annotations

import base64
import copy
import hashlib
import json
from pathlib import Path
import unittest
from types import SimpleNamespace
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse

import reference_agent as agent
import reference_assets
import reference_ontology as ontology
import workshop_runtime as runtime

ROOT = Path(__file__).resolve().parents[2]
WORKSHOP = ROOT / "workshop/v2.7.0"


def public_tree(kind, specification):
    """Synthetic public IDs deliberately differ from serialized IDs and paths."""
    nodes = {}
    children = {None: []}
    parents = {}

    def add(path, description="", data_type=None):
        if path in parents:
            return nodes[parents[path]]
        parent_id = None
        if len(path) > 1:
            parent_id = add(path[:-1])["id"]
        identifier = f"opaque /+%={len(nodes) + 1}"
        native_kind, name = path[-1]
        node = {
            "id": identifier, "type": native_kind, "displayName": name,
            "isSelected": False, "hasSubElements": False, "state": "Available",
            "description": description,
        }
        if data_type is not None:
            node["dataType"] = data_type
        nodes[identifier] = node
        parents[path] = identifier
        children[identifier] = []
        children[parent_id].append(node)
        if parent_id:
            nodes[parent_id]["hasSubElements"] = True
        return node

    for entry in specification["elements"]:
        path = agent.key(entry["path"])
        if kind == "kusto" and path[-1][0] == "Function":
            path = (("Functions", "Functions"),) + path
        if kind == "kusto" and path[0][0] == "MaterializedView":
            path = (("MaterializedViews", "Materialized Views"),) + path
        add(path)
    for name, contract in specification.get("referenceObjects", {}).items():
        path = (("Schema", "agent_ref"), (contract["type"], name))
        child_kind = "FunctionReturnValue" if contract["type"] == "Function" else "Column"
        for field, _ in contract["fields"]:
            add(path + ((child_kind, field),), data_type="" if child_kind == "FunctionReturnValue" else "varchar")
        if contract["parameter"]:
            add(path + (("FunctionParameter", contract["parameter"]),), data_type="bigint")
    if kind == "kusto":
        add((("Functions", "Functions"), ("Function", "AgentObservationLeaders")))
        add((("Table", "DonationEvents"), ("Column", "EventID")))
    if kind == "lakehouse_tables":
        first = next(agent.key(entry["path"]) for entry in specification["elements"] if entry["path"][-1][0] == "Table")
        add(first + (("Column", "_WorkshopGenerationId"),))
    return nodes, children


def apply_changes(nodes, children, changes):
    for change in changes:
        node = nodes[change["id"]]
        node.update({"isSelected": change["body"]["isSelected"]})
        if "description" in change["body"]:
            node["description"] = change["body"]["description"]
        if node["type"] in agent.OBJECTS:
            def cascade(identifier):
                for child in children[identifier]:
                    child["isSelected"] = node["isSelected"]
                    cascade(child["id"])
            cascade(node["id"])


def encoded(path, value):
    return {
        "path": path, "payloadType": "InlineBase64",
        "payload": base64.b64encode(json.dumps(value).encode()).decode(),
    }


class AgentServiceFixture:
    """A credential-free public/serialized service double with different ID spaces."""
    def __init__(self, assets):
        self.assets = assets
        self.calls = []
        self.sources = {}
        self.trees = {}
        self.configured = None
        self.published = None
        self.now = datetime(2026, 1, 1, tzinfo=timezone.utc)
        self.clock = lambda: self.now
        self.timeout_seconds = 60
        self.poll_interval_seconds = 1

    def sleeper(self, seconds):
        self.now += timedelta(seconds=seconds)

    def _paged(self, url):
        parsed = urlparse(url)
        stage = "staging" if "/staging/" in parsed.path else "published"
        if parsed.path.endswith("/datasources"):
            return copy.deepcopy(list(self.sources.values()))
        source_id = parsed.path.split("/datasources/", 1)[1].split("/", 1)[0]
        root = parse_qs(parsed.query).get("rootId", [None])[0]
        return copy.deepcopy(self.trees[source_id][1][root])

    def _request(self, method, url, json_body=None, **kwargs):
        self.calls.append((method, url, copy.deepcopy(json_body)))
        parsed = urlparse(url)
        response = SimpleNamespace(status_code=200, headers={}, content=b"{}")
        if method == "POST" and parsed.path.endswith("/datasources"):
            kind = "lakehouse_tables" if json_body["type"] == "LakehouseTables" else (
                "kusto" if json_body["itemReference"]["itemId"].endswith("2") else "ontology"
            )
            source_id = f"source-{kind}"
            source = {
                "id": source_id, **copy.deepcopy(json_body),
                "displayName": kind, "description": "", "instructions": "",
            }
            if kind != "lakehouse_tables":
                source["fabricItemType"] = "KQLDatabase" if kind == "kusto" else "Ontology"
            self.sources[source_id] = source
            self.trees[source_id] = public_tree(kind, self.assets["sources"][kind])
            response.status_code = 201
        elif method == "PATCH" and parsed.path.endswith("/elements"):
            source_id = parsed.path.split("/datasources/", 1)[1].split("/", 1)[0]
            identifier = parse_qs(parsed.query)["id"][0]
            nodes, children = self.trees[source_id]
            apply_changes(nodes, children, [{"id": identifier, "body": json_body}])
        elif method == "PATCH" and "/datasources/" in parsed.path:
            source_id = parsed.path.rsplit("/", 1)[1]
            self.sources[source_id].update(json_body)
        elif method == "POST" and parsed.path.endswith("/updateDefinition"):
            self.configured = copy.deepcopy(json_body["definition"])
        elif method == "POST" and parsed.path.endswith("/staging/publish"):
            self.published = copy.deepcopy(self.configured)
            for part in self.configured["parts"]:
                if "/draft/" in part["path"]:
                    duplicate = copy.deepcopy(part)
                    duplicate["path"] = duplicate["path"].replace("/draft/", "/published/")
                    self.published["parts"].append(duplicate)
        else:
            raise AssertionError(f"Unexpected operation: {method} {url}")
        return response

    def get_definition(self, workspace_id, agent_id):
        if self.published is not None:
            return copy.deepcopy(self.published)
        if self.configured is not None:
            return copy.deepcopy(self.configured)
        parts = [encoded("Files/Config/draft/stage_config.json", {"aiInstructions": ""})]
        type_map = {
            "Schema": "lakehouse_tables.schema", "Table": "lakehouse_tables.table",
            "View": "lakehouse_tables.view", "Column": "lakehouse_tables.column",
            "Function": "lakehouse_tables.function", "FunctionParameter": "function.parameter",
            "FunctionReturnValue": "function.returnValue",
        }
        for kind in agent.KINDS:
            source = self.sources[f"source-{kind}"]
            _, children = self.trees[source["id"]]

            def serialize(root=None):
                result = []
                for node in children[root]:
                    native = node["type"]
                    serialized_type = type_map.get(native, "function_grouping")
                    if kind == "kusto":
                        serialized_type = {
                            "MaterializedViews": "kusto", "Functions": "function_grouping",
                            "MaterializedView": "kusto.table", "Table": "kusto.table",
                            "Column": "kusto.column", "Function": "kusto.function",
                        }[native]
                    if kind == "ontology":
                        serialized_type = "ontology.entity"
                    item = {
                        "id": "serialized-uuid-space-" + str(len(result)) + node["id"],
                        "display_name": node["displayName"], "type": serialized_type,
                        "description": node["description"], "is_selected": node["isSelected"],
                        "children": serialize(node["id"]),
                    }
                    if "dataType" in node:
                        item["data_type"] = node["dataType"]
                    result.append(item)
                return result

            reference = source.get("lakehouseReference", source.get("itemReference"))
            parts.append(encoded(f"Files/Config/draft/{kind}/datasource.json", {
                "type": kind, "artifactId": reference["itemId"], "workspaceId": reference["workspaceId"],
                "userDescription": source["description"], "dataSourceInstructions": source["instructions"],
                "elements": serialize(),
            }))
        return {"parts": parts}


class ReferenceArchitectureTests(unittest.TestCase):
    def test_published_source_reads_use_the_documented_item_root(self):
        urls = []
        client = SimpleNamespace(_paged=lambda url: urls.append(url) or [])
        public = agent.PublicAgentClient(client, "workspace", "agent")
        public.sources("published")
        public.tree("source", "published")
        self.assertEqual(urls, [
            public.base + "/datasources",
            public.base + "/datasources/source/elements",
        ])
        with self.assertRaises(agent.ReferenceAgentError):
            public.sources("unknown")

    def test_optional_source_text_distinguishes_unset_from_invalid_values(self):
        self.assertEqual(agent.optional_text(None), agent.optional_text(""))
        self.assertEqual(agent.optional_text("  exact bytes  "), "  exact bytes  ")
        for invalid in (False, 0, [], {}):
            with self.subTest(invalid=invalid), self.assertRaises(agent.ReferenceAgentError):
                agent.optional_text(invalid)

    def test_serialized_table_valued_function_group_keeps_function_interfaces(self):
        source = {
            "type": "lakehouse_tables",
            "elements": [{
                "id": "schema", "type": "lakehouse_tables.schema", "display_name": "agent_ref",
                "is_selected": False, "children": [{
                    "type": "table_valued_function_grouping", "display_name": "Table-valued Functions",
                    "is_selected": False, "children": [{
                        "id": "function", "type": "lakehouse_tables.function",
                        "display_name": "MunicipalityById", "is_selected": True, "children": [{
                            "id": "parameter", "type": "function.parameter",
                            "display_name": "@RequestedMunicipalityId", "is_selected": True, "children": [],
                        }],
                    }],
                }],
            }],
        }
        records = agent.serialized_records(source)
        paths = {agent.key(record["path"]) for record in records if agent.effective_selected(record)}
        prefix = (("Schema", "agent_ref"), ("Function", "MunicipalityById"))
        self.assertEqual(paths, {prefix, prefix + (("FunctionParameter", "@RequestedMunicipalityId"),)})

    def test_serialized_native_materialized_view_group_retains_selected_children(self):
        source = {
            "type": "kusto",
            "elements": [{
                "type": "materialized_view_grouping", "display_name": "Materialized Views",
                "is_selected": False, "children": [{
                    "id": "view", "type": "kusto.materialized_view",
                    "display_name": "DonationObservationSummaryForAgent", "is_selected": True,
                    "description": "Approved summary",
                    "children": [{
                        "id": "column", "type": "kusto.column", "display_name": "ObservationCount",
                        "is_selected": True, "description": "Raw observation count", "children": [],
                    }],
                }],
            }],
        }
        specification = {"elements": [
            {"path": [["MaterializedView", "DonationObservationSummaryForAgent"]], "description": "Approved summary"},
            {"path": [["MaterializedView", "DonationObservationSummaryForAgent"], ["Column", "ObservationCount"]],
             "description": "Raw observation count"},
        ]}
        proof = agent.verify_selection("kusto", agent.serialized_records(source), specification, public=False)
        self.assertEqual((proof["selectedObjects"], proof["selectedLeaves"]), (1, 1))

    @classmethod
    def setUpClass(cls):
        cls.path_template = reference_assets.derive_path_template(ROOT)
        cls.metadata = reference_assets.source_metadata(ROOT, cls.path_template)

    def test_teaching_source_is_not_modified_by_deterministic_derivation(self):
        path = WORKSHOP / "ontology/ontology-full-definition-template.json"
        before = path.read_bytes()
        first = reference_assets.derive_path_template(ROOT)
        second = reference_assets.derive_path_template(ROOT)
        self.assertEqual(first, second)
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(first["expectedContract"], ontology.PATH_COUNTS)
        original = json.loads(before)
        source_contexts = {
            part["path"]: part["content"] for part in original["parts"] if "/Contextualizations/" in part["path"]
        }
        actual_contexts = {
            part["path"]: part["content"] for part in first["parts"] if "/Contextualizations/" in part["path"]
        }
        self.assertEqual(source_contexts, actual_contexts)
        self.assertEqual(len(actual_contexts), 15)
        self.assertEqual(original["expectedContract"]["staticProperties"], 72)
        self.assertFalse(first["derivation"]["acceptanceClaimed"])

    def test_path_materialization_uses_discovered_ids_and_real_dbo(self):
        ws = "10000000-0000-4000-8000-000000000001"
        lh = "10000000-0000-4000-8000-000000000002"
        result = ontology.materialize_path_definition(
            self.path_template, workspace_id=ws, lakehouse_id=lh, display_name="ONT_Furusato_AIPath_912",
        )
        self.assertEqual(len(result["parts"]), 52)
        rendered = "".join(base64.b64decode(part["payload"]).decode() for part in result["parts"])
        self.assertNotIn("{{", rendered)
        self.assertNotIn("KustoTable", rendered)
        self.assertEqual(rendered.count('"sourceSchema":"dbo"'), 25)
        self.assertIn(ws, rendered)
        self.assertIn(lh, rendered)
        with self.assertRaisesRegex(ValueError, "separate participant"):
            ontology.materialize_path_definition(
                self.path_template, workspace_id=ws, lakehouse_id=lh, display_name="ONT_Furusato_912",
            )

    def test_security_unknown_is_not_reported_disabled(self):
        self.assertEqual(ontology.compatibility_observation({})["oneLakeSecurity"], "UNKNOWN")
        self.assertEqual(
            ontology.compatibility_observation({"properties": {"oneLakeSecurityEnabled": False}})["oneLakeSecurity"],
            "DISABLED",
        )
        self.assertEqual(
            ontology.compatibility_observation({"properties": {"oneLakeSecurityEnabled": "false"}})["oneLakeSecurity"],
            "UNKNOWN",
        )

    def test_both_ontology_graph_lifecycles_reuse_observed_refresh_jobs(self):
        class Client(runtime.WorkshopFabricClient):
            def __init__(self):
                self.now = datetime(2026, 1, 1, tzinfo=timezone.utc)
                super().__init__(
                    lambda: self.fail_auth(), lambda: self.fail_auth(),
                    clock=lambda: self.now, sleeper=self.sleep,
                    timeout_seconds=60, poll_interval_seconds=10,
                )
                self.polled = []

            def fail_auth(self):
                raise AssertionError("No credentials should be acquired by the mocked lifecycle")

            def sleep(self, seconds):
                self.now += timedelta(seconds=seconds)

            def get_definition(self, workspace_id, item_id):
                return {"parts": [
                    encoded("graphType.json", {"nodeTypes": [{}] * 10, "edgeTypes": [{}] * 15}),
                    encoded("dataSources.json", {"dataSources": [{}] * 11}),
                    encoded("graphDefinition.json", {"nodeTables": [{}] * 10, "edgeTables": [{}] * 15}),
                ]}

            def recent_jobs(self, workspace_id, item_id, job_type, **kwargs):
                return [{"id": item_id + "-service-refresh", "status": "Completed"}]

            def poll_job(self, workspace_id, item_id, job_id):
                self.polled.append(job_id)
                return {"id": job_id, "status": "Completed"}

            def _request(self, *args, **kwargs):
                raise AssertionError("Observed automatic refreshes must not be resubmitted")

        client = Client()
        _, teaching = client.run_or_reuse_graph_refresh("workspace", "teaching")
        _, path = client.run_or_reuse_graph_refresh(
            "workspace", "path", expected_counts=ontology.PATH_GRAPH_COUNTS,
        )
        self.assertEqual((teaching, path), ("RECENT_REUSED", "RECENT_REUSED"))
        self.assertEqual(client.polled, ["teaching-service-refresh", "path-service-refresh"])
        with self.assertRaises(runtime.OperationTimeoutError):
            client.wait_for_graph_compilation(
                "workspace", "path", expected_counts={**ontology.PATH_GRAPH_COUNTS, "dataSources": 10},
            )
        self.assertEqual(len(client.polled), 2)

    def test_reference_is_off_by_default_and_does_not_replace_core_name(self):
        config = runtime.ProvisioningConfig(participant_id="912")
        runtime.validate_config(config)
        names = runtime.build_names("912")
        self.assertFalse(config.enable_ai_reference_architecture)
        self.assertEqual(runtime.reference_agent_target(config, names)["name"], "DA_Furusato_912")
        self.assertEqual(names.agent_ontology, "ONT_Furusato_AIPath_912")
        config.enable_ai_reference_architecture = True
        self.assertEqual(runtime.reference_agent_target(config, names)["name"], "DA_Furusato_AIReference_912")
        config.reference_agent_name = names.data_agent
        with self.assertRaisesRegex(runtime.ProvisioningError, "Core promotion"):
            runtime.validate_config(config)

    def test_authorized_candidate_requires_name_role_and_exact_id(self):
        config = runtime.ProvisioningConfig(
            participant_id="912", enable_ai_reference_architecture=True,
            reference_agent_name="Already_authorized_candidate",
        )
        with self.assertRaises(runtime.ProvisioningError):
            runtime.validate_config(config)
        config.reference_agent_role = "authorized-candidate"
        with self.assertRaises(runtime.ProvisioningError):
            runtime.validate_config(config)
        config.reference_agent_expected_id = "20000000-0000-4000-8000-000000000001"
        runtime.validate_config(config)

    def test_missing_global_fails_before_any_notebook_context_or_auth(self):
        config = runtime.ProvisioningConfig(enable_ai_reference_architecture=True)
        with self.assertRaisesRegex(runtime.ProvisioningError, "hash-pinned"):
            runtime.execute_provisioning(config, {"bundle": {}}, notebookutils=None, spark=None)

    def test_sql_endpoint_wait_handles_null_readiness_metadata(self):
        now = [datetime(2026, 1, 1, tzinfo=timezone.utc)]
        snapshots = iter([
            {"properties": None},
            {"properties": {"sqlEndpointProperties": None}},
            {"displayName": "DiscoveredName", "properties": {
                "sqlEndpointProperties": {"connectionString": "discovered.datawarehouse.fabric.microsoft.com"},
            }},
        ])
        client = SimpleNamespace(
            clock=lambda: now[0], timeout_seconds=60, poll_interval_seconds=1,
            sleeper=lambda seconds: now.__setitem__(0, now[0] + timedelta(seconds=seconds)),
            get_lakehouse=lambda _ws, _lh: next(snapshots),
        )
        self.assertEqual(runtime.wait_for_sql_endpoint(client, "workspace", "lakehouse")["displayName"], "DiscoveredName")

    def test_exact_public_name_type_path_selects_only_approved_sources(self):
        for kind, spec in self.metadata.items():
            with self.subTest(kind=kind):
                nodes, children = public_tree(kind, spec)
                records = agent.discover_tree(lambda root: children[root])
                changes = agent.selection_changes(kind, records, spec)
                self.assertTrue(all(change["id"].startswith("opaque /+%=") for change in changes))
                self.assertFalse(any(
                    nodes[change["id"]]["type"] in agent.GROUPS for change in changes
                ))
                apply_changes(nodes, children, changes)
                records = agent.discover_tree(lambda root: children[root])
                report = agent.verify_selection(kind, records, spec)
                self.assertGreater(report["selectedObjects"], 0)
                if kind == "lakehouse_tables":
                    selected_columns = [
                        record for record in records if agent.effective_selected(record)
                        and record["path"][0] == ("Schema", "dbo") and record["element"]["type"] == "Column"
                    ]
                    self.assertEqual(len(selected_columns), 88)
                    generation = next(node for node in nodes.values() if node["displayName"] == "_WorkshopGenerationId")
                    self.assertFalse(generation["isSelected"])
                if kind == "kusto":
                    functions = [node for node in nodes.values() if node["type"] == "Function" and node["isSelected"]]
                    self.assertEqual(len(functions), 3)
                    self.assertTrue(all(not node["hasSubElements"] for node in functions))
                    self.assertFalse(next(node for node in nodes.values() if node["type"] == "Functions")["isSelected"])
                    self.assertFalse(next(node for node in nodes.values() if node["displayName"] == "EventID")["isSelected"])

    def test_legacy_kql_function_is_optional_and_never_selected(self):
        spec = self.metadata["kusto"]
        nodes, children = public_tree("kusto", spec)
        for root, items in children.items():
            children[root] = [node for node in items if node["displayName"] != "AgentObservationLeaders"]
        records = agent.discover_tree(lambda root: children[root])
        changes = agent.selection_changes("kusto", records, spec)
        self.assertNotIn("AgentObservationLeaders", str(changes))
        apply_changes(nodes, children, changes)
        agent.verify_selection("kusto", agent.discover_tree(lambda root: children[root]), spec)

    def test_kql_fake_children_unavailable_or_unapproved_selection_fail(self):
        spec = self.metadata["kusto"]
        for defect in ("children", "unavailable", "raw"):
            with self.subTest(defect=defect):
                nodes, children = public_tree("kusto", spec)
                records = agent.discover_tree(lambda root: children[root])
                apply_changes(nodes, children, agent.selection_changes("kusto", records, spec))
                function = next(node for node in nodes.values() if node["displayName"] == "AgentFileRunSummary")
                if defect == "children":
                    function["hasSubElements"] = True
                elif defect == "unavailable":
                    function["state"] = "SchemaUnavailable"
                else:
                    next(node for node in nodes.values() if node["displayName"] == "DonationEvents")["isSelected"] = True
                with self.assertRaises(agent.ReferenceAgentError):
                    agent.verify_selection("kusto", agent.discover_tree(lambda root: children[root]), spec)

    def test_missing_trace30_column_fails_before_selection(self):
        spec = self.metadata["lakehouse_tables"]
        nodes, children = public_tree("lakehouse_tables", spec)
        trace = next(node for node in nodes.values() if node["displayName"] == "DonationTraceById")
        children[trace["id"]] = [
            node for node in children[trace["id"]] if node["displayName"] != "RowGrain"
        ]
        with self.assertRaisesRegex(agent.ReferenceAgentError, "SQL return fields"):
            agent.selection_changes("lakehouse_tables", agent.discover_tree(lambda root: children[root]), spec)

    def test_different_schema_or_type_is_not_matched_by_name(self):
        spec = self.metadata["lakehouse_tables"]
        for defect in ("schema", "type"):
            nodes, children = public_tree("lakehouse_tables", spec)
            if defect == "schema":
                next(node for node in nodes.values() if node["displayName"] == "agent_ref")["displayName"] = "foreign"
            else:
                next(node for node in nodes.values() if node["displayName"] == "DonationTraceById")["type"] = "Table"
            with self.assertRaises(agent.ReferenceAgentError):
                agent.selection_changes("lakehouse_tables", agent.discover_tree(lambda root: children[root]), spec)

    def test_function_group_false_still_has_significant_serialized_selection(self):
        function = {
            "id": "serialized-uuid-not-public", "type": "kusto.function",
            "display_name": "AgentFileRunSummary", "is_selected": True,
            "description": "Structural interface", "children": [],
        }
        source = {
            "elements": [{
                "type": "function_grouping", "display_name": "Functions", "is_selected": False,
                "children": [function],
            }],
        }
        actual = runtime.normalize_data_agent_source(source)
        self.assertEqual(len(actual["effectiveSelectedObjects"]), 1)
        changed = copy.deepcopy(source)
        changed["elements"][0]["children"][0]["is_selected"] = False
        self.assertNotEqual(actual, runtime.normalize_data_agent_source(changed))

    def test_public_patch_uses_encoded_query_id_not_serialized_uuid(self):
        calls = []
        class Client:
            def _request(self, method, url, **kwargs):
                calls.append((method, url, kwargs))
        public = agent.PublicAgentClient(Client(), "workspace", "agent")
        opaque = "opaque /+%="
        public.request("PATCH", "/staging/datasources/source/elements?" + agent.urlencode({"id": opaque}), {"isSelected": True})
        self.assertEqual(parse_qs(urlparse(calls[0][1]).query), {"id": [opaque]})
        self.assertIn("/elements?", calls[0][1])
        self.assertNotIn("/elements/opaque", calls[0][1])

    def test_runtime_patch_never_invents_source_children_or_fills_blank_types(self):
        sources = {}
        for kind in agent.KINDS:
            sources[f"Files/Config/draft/{kind}/datasource.json"] = {
                "type": kind, "elements": [{
                    "id": "native-serialized-id", "type": "function.returnValue",
                    "display_name": "DonationId", "data_type": "", "children": [],
                }],
            }
        definition = {"parts": [encoded(path, value) for path, value in sources.items()]}
        assets = {"stageConfig": {"aiInstructions": "explicit candidate"}, "sources": self.metadata}
        updated = agent.draft_with_runtime(definition, assets)
        before, after = agent.decode_parts(definition), agent.decode_parts(updated)
        for path in sources:
            self.assertEqual(before[path]["part"], after[path]["part"])
            self.assertEqual(after[path]["value"]["elements"][0]["data_type"], "")

    def test_fresh_public_source_configuration_publishes_exact_and_reuses_read_only(self):
        assets = {
            "sources": self.metadata,
            "stageConfig": {
                "aiInstructions": "Synthetic explicitly pinned reference GLOBAL.",
                "experimental": {"enableExperimentalFeatures": True, "codeInterpreterEnabled": False},
            },
            "globalProfile": {"status": "candidate"},
        }
        bindings = {
            kind: {"workspaceId": "workspace", "itemId": f"item-{index}"}
            for index, kind in enumerate(agent.KINDS, 1)
        }
        client = AgentServiceFixture(assets)
        result = agent.configure_reference_agent(client, "workspace", "agent", assets, bindings, initialize=True)
        self.assertEqual(result["state"], "CREATED")
        self.assertFalse(result["acceptanceClaimed"])
        self.assertEqual(len(result["selections"]), 6)
        self.assertEqual(sum(url.endswith("/staging/publish") for _, url, _ in client.calls), 1)
        for method, url, body in client.calls:
            if method == "PATCH" and "/elements?" in url:
                self.assertTrue(parse_qs(urlparse(url).query)["id"][0].startswith("opaque /+%="))
                self.assertEqual(set(body) - {"isSelected", "description"}, set())
        parts = agent.decode_parts(client.published)
        returns = []
        for _, source in agent.serialized_sources(parts, "published").values():
            def collect(nodes):
                for node in nodes:
                    if node["type"] == "function.returnValue":
                        returns.append(node["data_type"])
                    collect(node["children"])
            collect(source["elements"])
        self.assertEqual(returns, [""] * 52)
        before = len(client.calls)
        reused = agent.configure_reference_agent(client, "workspace", "agent", assets, bindings, initialize=False)
        self.assertEqual(reused["state"], "REUSED")
        self.assertEqual(len(client.calls), before)
        client.sources["source-ontology"]["itemReference"]["itemId"] = "foreign-full-ontology"
        with self.assertRaisesRegex(agent.ReferenceAgentError, "foreign"):
            agent.configure_reference_agent(client, "workspace", "agent", assets, bindings, initialize=False)
        self.assertEqual(len(client.calls), before)
        client.sources["source-ontology"]["itemReference"]["itemId"] = bindings["ontology"]["itemId"]
        client.sources["source-ontology"]["type"] = "UnsupportedFabricType"
        with self.assertRaisesRegex(agent.ReferenceAgentError, "datasource type"):
            agent.configure_reference_agent(client, "workspace", "agent", assets, bindings, initialize=False)
        self.assertEqual(len(client.calls), before)


if __name__ == "__main__":
    unittest.main()
