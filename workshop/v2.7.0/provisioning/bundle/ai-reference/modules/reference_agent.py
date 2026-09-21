"""Public-ID-only configuration of an isolated reference Data Agent.

Uses the documented staging datasource/element APIs, followed by a full
getDefinition/updateDefinition round trip for runtime settings and unchanged
Lakehouse few-shots. Only a newly created, explicitly authorized target may be
initialized. An existing target is read-only and must already match exactly.

API contracts:
https://learn.microsoft.com/rest/api/fabric/dataagent/staging/list-datasource-elements
https://learn.microsoft.com/rest/api/fabric/dataagent/staging/update-datasource-element
https://learn.microsoft.com/rest/api/fabric/dataagent/staging/create-datasource
https://learn.microsoft.com/rest/api/fabric/dataagent/items/publish-data-agent

Public element IDs are opaque strings, NOT the UUIDs in datasource.json.
Function interfaces are catalog provenance, never invented discovery children.
"""

from __future__ import annotations

import base64
import copy
import hashlib
import json
from datetime import timedelta
from typing import Any, Callable, Mapping, Sequence
from urllib.parse import urlencode

API = "https://api.fabric.microsoft.com/v1"
GROUPS = {
    "Root", "Schemas", "Tables", "Views", "Functions", "ScalarFunctions",
    "TableValuedFunctions", "MaterializedViews",
}
OBJECTS = {"Table", "View", "MaterializedView", "Function", "Entity"}
MEMBERS = {"Column", "FunctionParameter", "FunctionReturnValue"}
KINDS = ("lakehouse_tables", "kusto", "ontology")


class ReferenceAgentError(ValueError):
    pass


class DiscoveryNotReady(ReferenceAgentError):
    pass


def optional_text(value: Any) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ReferenceAgentError("Optional source metadata must be text or null.")
    return value


def key(path: Sequence[Sequence[str]]) -> tuple[tuple[str, str], ...]:
    return tuple((part[0], part[1]) for part in path)


def discover_tree(fetch_level: Callable[[str | None], Sequence[Mapping[str, Any]]]) -> list[dict]:
    """Read every page at each level; retain the actual IDs and ancestry."""
    records: list[dict] = []
    seen: set[str] = set()

    def visit(root_id=None, path=(), ancestors=()):
        if len(ancestors) > 20 or len(records) > 20_000:
            raise ReferenceAgentError("Datasource discovery exceeded its bounded tree budget.")
        for raw in fetch_level(root_id):
            node = copy.deepcopy(dict(raw))
            identifier = node.get("id")
            if not isinstance(identifier, str) or not identifier or identifier in seen:
                raise ReferenceAgentError("Discovery returned a missing, duplicate or cyclic public ID.")
            seen.add(identifier)
            if not isinstance(node.get("displayName"), str) or not isinstance(node.get("type"), str):
                raise ReferenceAgentError("Discovery returned an invalid name/type contract.")
            for flag in ("isSelected", "hasSubElements"):
                if type(node.get(flag)) is not bool:
                    raise ReferenceAgentError(f"Discovery must report an explicit Boolean {flag}.")
            kind = node["type"]
            current = path if kind in GROUPS else path + ((kind, node["displayName"]),)
            records.append({"path": current, "element": node, "ancestors": ancestors})
            if node["hasSubElements"]:
                visit(identifier, current, ancestors + (node,))

    visit()
    return records


def index_tree(records: Sequence[Mapping[str, Any]]) -> dict[tuple, dict]:
    result = {}
    for record in records:
        node = record["element"]
        if node["type"] in GROUPS or node["type"] == "Schema":
            continue
        path = key(record["path"])
        if path in result:
            raise ReferenceAgentError(f"Ambiguous public name/type/path: {path}")
        result[path] = record
    return result


def selection_rules(
    kind: str, records: Sequence[Mapping[str, Any]], specification: Mapping[str, Any],
    *, public: bool = True,
) -> dict:
    """Bind portable contracts to discovered paths, not guessed identifiers."""
    actual = index_tree(records)
    wanted = {key(entry["path"]): entry["description"] for entry in specification["elements"]}
    if len(wanted) != len(specification["elements"]):
        raise ReferenceAgentError("Duplicate portable selection paths.")
    for path in wanted:
        if path not in actual:
            raise DiscoveryNotReady(f"Required source element was not discovered: {path}")
        if public and actual[path]["element"].get("state") != "Available":
            state = actual[path]["element"].get("state")
            error = DiscoveryNotReady if state in {"SchemaUnavailable", "NotAvailable"} else ReferenceAgentError
            raise error(f"Required source element is not Available ({state}): {path}")
        if kind == "kusto" and path[-1][0] == "Function":
            if actual[path]["element"]["hasSubElements"] is not False:
                raise ReferenceAgentError("KQL Function must be an Available leaf, not a fabricated interface tree.")
    for name, contract in specification.get("referenceObjects", {}).items():
        parent = (("Schema", "agent_ref"), (contract["type"], name))
        fields = {}
        parameters = []
        for path, record in actual.items():
            if path[:len(parent)] != parent or len(path) == len(parent):
                continue
            node = record["element"]
            if node["type"] == "FunctionParameter":
                parameters.append(node["displayName"])
                wanted[path] = contract["parameterDescription"]
            elif node["type"] in {"Column", "FunctionReturnValue"} and not node["hasSubElements"]:
                if node["displayName"] in fields:
                    raise ReferenceAgentError(f"Duplicate discovered return column in {name}.")
                fields[node["displayName"]] = path
            else:
                raise ReferenceAgentError(f"Unsupported native SQL interface tree in {name}: {path}")
            if public and node.get("state") != "Available":
                raise ReferenceAgentError(f"Unavailable native SQL interface element: {path}")
        expected = [field for field, _ in contract["fields"]]
        if set(fields) < set(expected):
            raise DiscoveryNotReady(f"Discovered SQL return fields are incomplete for {name}; native catalog proof is required.")
        if set(fields) != set(expected):
            raise ReferenceAgentError(f"Discovered SQL return fields differ for {name}; native catalog proof is required.")
        parameter = contract["parameter"]
        if [value.lstrip("@") for value in parameters] != ([] if parameter is None else [parameter.lstrip("@")]):
            raise ReferenceAgentError(f"Discovered SQL parameters differ for {name}.")
        for field, path in fields.items():
            wanted[path] = contract["fieldDescriptions"][field]
    return wanted


def effective_selected(record: Mapping[str, Any]) -> bool:
    """Grouping false does not disable explicitly selected queryable leaves."""
    return record["element"]["isSelected"] and all(
        node["isSelected"] for node in record["ancestors"] if node["type"] in OBJECTS
    )


def selection_changes(kind: str, records: Sequence[Mapping[str, Any]], specification: Mapping[str, Any]) -> list[dict]:
    wanted = selection_rules(kind, records, specification)
    actual = index_tree(records)
    changes = []
    for path, record in actual.items():
        node = record["element"]
        selected = path in wanted
        if selected or node["isSelected"] or node["type"] in MEMBERS:
            body = {"isSelected": selected}
            if selected:
                body["description"] = wanted[path]
            changes.append({"id": node["id"], "path": path, "body": body})
    # Selecting a table can select all columns. Apply every leaf decision after
    # the parent, including explicitly false unpublished raw/unapproved leaves.
    return sorted(changes, key=lambda change: (len(change["path"]), change["path"]))


def verify_selection(
    kind: str, records: Sequence[Mapping[str, Any]], specification: Mapping[str, Any],
    *, public: bool = True,
) -> dict:
    wanted = selection_rules(kind, records, specification, public=public)
    actual = index_tree(records)
    selected = {path for path, record in actual.items() if effective_selected(record)}
    if selected != set(wanted):
        raise ReferenceAgentError(
            f"{kind} selected leaves differ: missing={sorted(set(wanted) - selected)}, "
            f"unapproved={sorted(selected - set(wanted))}"
        )
    for path, description in wanted.items():
        if actual[path]["element"].get("description", "") != description:
            raise ReferenceAgentError(f"Source element description differs: {path}")
    return {
        "selectedObjects": sum(path[-1][0] in OBJECTS for path in wanted),
        "selectedLeaves": sum(path[-1][0] in MEMBERS for path in wanted),
        "selectionIdentity": "discovered-public-id/name/type/path" if public else "serialized-name/type/path",
    }


def decode_parts(definition: Mapping[str, Any]) -> dict[str, dict]:
    result = {}
    for part in definition.get("definition", definition)["parts"]:
        path = part["path"]
        if path in result or part.get("payloadType") != "InlineBase64":
            raise ReferenceAgentError("Duplicate or unsupported Data Agent definition part.")
        result[path] = {
            "part": copy.deepcopy(part),
            "value": json.loads(base64.b64decode(part["payload"], validate=True)),
        }
    return result


def serialized_sources(parts: Mapping[str, dict], stage: str) -> dict[str, tuple[str, dict]]:
    sources = {}
    prefix = f"Files/Config/{stage}/"
    for path, record in parts.items():
        if not path.startswith(prefix) or not path.endswith("/datasource.json"):
            continue
        value = record["value"]
        kind = value.get("type")
        if kind not in KINDS or kind in sources:
            raise ReferenceAgentError(f"Unexpected or duplicate serialized source: {kind}")
        sources[kind] = (path, value)
    if set(sources) != set(KINDS):
        raise ReferenceAgentError(f"{stage} must contain exactly the three approved sources.")
    return sources


def serialized_records(source: Mapping[str, Any]) -> list[dict]:
    kind = source["type"]
    type_map = {
        "lakehouse_tables.schema": "Schema", "lakehouse_tables.table": "Table",
        "lakehouse_tables.view": "View", "lakehouse_tables.function": "Function",
        "lakehouse_tables.column": "Column", "function.parameter": "FunctionParameter",
        "function.returnValue": "FunctionReturnValue",
        "kusto.function": "Function", "kusto.column": "Column",
        "kusto.materialized_view": "MaterializedView", "ontology.entity": "Entity",
    }
    group_types = {
        "schema_grouping", "table_grouping", "view_grouping", "function_grouping",
        "materialized_view_grouping", "table_valued_function_grouping",
        "kusto", "lakehouse_tables", "ontology",
    }
    records = []

    def visit(nodes, path=(), ancestors=(), group=""):
        for node in nodes:
            native_kind = type_map.get(node.get("type"))
            if node.get("type") == "kusto.table":
                native_kind = "MaterializedView" if group == "Materialized Views" else "Table"
            if native_kind is None:
                if node.get("type") not in group_types:
                    if node.get("is_selected") is not False:
                        raise ReferenceAgentError(f"Unsupported selected serialized element type: {node.get('type')}")
                    continue
                visit(node.get("children", []), path, ancestors, node.get("display_name", group))
                continue
            observed = {
                "id": node.get("id"),
                "type": native_kind,
                "displayName": node["display_name"],
                "description": node.get("description", ""),
                "isSelected": node.get("is_selected", False),
                "hasSubElements": bool(node.get("children")),
            }
            if type(observed["isSelected"]) is not bool:
                raise ReferenceAgentError("Serialized selections must be Boolean.")
            current = path + ((native_kind, observed["displayName"]),)
            records.append({"path": current, "element": observed, "ancestors": ancestors})
            visit(node.get("children", []), current, ancestors + (observed,), group)

    visit(source.get("elements", []))
    if kind == "kusto":
        for record in records:
            if record["element"]["type"] == "Function" and record["element"]["hasSubElements"]:
                raise ReferenceAgentError("Serialized KQL Function must retain its observed empty children.")
    return records


def verify_definition(
    definition: Mapping[str, Any],
    assets: Mapping[str, Any],
    bindings: Mapping[str, Mapping[str, str]],
    *,
    stages: Sequence[str] = ("draft", "published"),
) -> None:
    parts = decode_parts(definition)
    for stage in stages:
        config = copy.deepcopy(parts[f"Files/Config/{stage}/stage_config.json"]["value"])
        expected = copy.deepcopy(assets["stageConfig"])
        for value in (config, expected):
            if value.get("experimental", {}).get("codeInterpreterEnabled") is False:
                value["experimental"].pop("codeInterpreterEnabled")
        if config != expected:
            raise ReferenceAgentError(f"{stage} runtime/GLOBAL differs from the explicitly frozen profile.")
        for kind, (path, source) in serialized_sources(parts, stage).items():
            target = bindings[kind]
            if source.get("artifactId") != target["itemId"] or source.get("workspaceId") != target["workspaceId"]:
                raise ReferenceAgentError(f"{stage} {kind} is bound to the wrong item.")
            spec = assets["sources"][kind]
            if optional_text(source.get("userDescription")) != optional_text(spec["description"]) or optional_text(
                source.get("dataSourceInstructions")
            ) != optional_text(spec["instructions"]):
                raise ReferenceAgentError(f"{stage} {kind} source instructions/description differ.")
            verify_selection(kind, serialized_records(source), spec, public=False)
            if kind == "lakehouse_tables" or (kind == "kusto" and "fewShots" in spec):
                shots_path = path.removesuffix("datasource.json") + "fewshots.json"
                if shots_path not in parts or parts[shots_path]["value"] != spec["fewShots"]:
                    raise ReferenceAgentError(f"{stage} {kind} few-shots differ from the frozen examples.")


def draft_with_runtime(definition: Mapping[str, Any], assets: Mapping[str, Any]) -> dict:
    """Preserve the discovered schema tree verbatim, including blank SQL data types."""
    parts = decode_parts(definition)
    sources = serialized_sources(parts, "draft")
    replacements = {"Files/Config/draft/stage_config.json": assets["stageConfig"]}
    lh_path = sources["lakehouse_tables"][0]
    replacements[lh_path.removesuffix("datasource.json") + "fewshots.json"] = assets["sources"][
        "lakehouse_tables"
    ]["fewShots"]
    if "fewShots" in assets["sources"]["kusto"]:
        kql_path = sources["kusto"][0]
        replacements[kql_path.removesuffix("datasource.json") + "fewshots.json"] = assets["sources"]["kusto"]["fewShots"]
    output = {path: value["part"] for path, value in parts.items()}
    for path, value in replacements.items():
        output[path] = {
            "path": path, "payloadType": "InlineBase64",
            "payload": base64.b64encode(
                json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            ).decode("ascii"),
        }
    return {"parts": [output[path] for path in sorted(output)]}


class PublicAgentClient:
    def __init__(self, client, workspace_id: str, agent_id: str):
        self.client = client
        self.workspace_id = workspace_id
        self.agent_id = agent_id
        self.base = f"{API}/workspaces/{workspace_id}/dataAgents/{agent_id}"

    def request(self, method: str, suffix: str, body=None, expected=(200,)):
        return self.client._request(
            method, self.base + suffix, json_body=body, expected=expected,
            safe_retry=method == "GET",
        )

    def stage_path(self, stage: str) -> str:
        if stage == "staging":
            return self.base + "/staging"
        if stage == "published":
            return self.base
        raise ReferenceAgentError("Unknown Data Agent stage.")

    def sources(self, stage="staging"):
        return self.client._paged(self.stage_path(stage) + "/datasources")

    def tree(self, source_id: str, stage="staging"):
        base = self.stage_path(stage) + f"/datasources/{source_id}/elements"
        return discover_tree(lambda root_id: self.client._paged(
            base + ("?" + urlencode({"rootId": root_id}) if root_id is not None else "")
        ))

    def wait_for_tree(self, source_id: str, kind: str, specification: Mapping[str, Any]):
        deadline = self.client.clock() + timedelta(seconds=self.client.timeout_seconds)
        while self.client.clock() < deadline:
            records = self.tree(source_id)
            try:
                selection_rules(kind, records, specification)
            except DiscoveryNotReady:
                self.client.sleeper(self.client.poll_interval_seconds)
            else:
                return records
        raise ReferenceAgentError(f"{kind} source discovery did not expose the complete required contract before timeout.")

    def match_sources(self, bindings: Mapping[str, Mapping[str, str]], stage="staging") -> dict:
        sources = self.sources(stage)
        result = {}
        for source in sources:
            if source.get("type") not in {"LakehouseTables", "FabricItem"}:
                raise ReferenceAgentError("Unsupported public datasource type.")
            kind = "lakehouse_tables" if source.get("type") == "LakehouseTables" else {
                "KQLDatabase": "kusto", "Ontology": "ontology",
            }.get(source.get("fabricItemType"))
            reference = source.get("lakehouseReference" if kind == "lakehouse_tables" else "itemReference", {})
            if (
                kind not in bindings or kind in result
                or reference.get("referenceType") != "ById"
                or any(reference.get(field) != bindings[kind][field] for field in ("itemId", "workspaceId"))
                or not isinstance(source.get("id"), str) or not source["id"]
            ):
                raise ReferenceAgentError("Unexpected, duplicate or foreign public datasource binding.")
            result[kind] = source
        return result

    def initialize_sources(self, bindings: Mapping[str, Mapping[str, str]]) -> dict:
        if self.sources():
            raise ReferenceAgentError("New Data Agent already has sources; refusing ambiguous initialization.")
        for kind, reference in bindings.items():
            request = {
                "type": "LakehouseTables" if kind == "lakehouse_tables" else "FabricItem",
                "lakehouseReference" if kind == "lakehouse_tables" else "itemReference": {
                    "referenceType": "ById", **reference,
                },
            }
            response = self.request("POST", "/staging/datasources", request, expected=(201, 202))
            if response.status_code == 202:
                self.client.poll_operation(self.client._operation_id(response))
        result = self.match_sources(bindings)
        deadline = self.client.clock() + timedelta(seconds=self.client.timeout_seconds)
        while set(result) != set(KINDS) and self.client.clock() < deadline:
            self.client.sleeper(self.client.poll_interval_seconds)
            result = self.match_sources(bindings)
        if set(result) != set(KINDS):
            raise ReferenceAgentError("Created datasource bindings did not propagate; no automatic create retry.")
        return result


def configure_reference_agent(
    client,
    workspace_id: str,
    agent_id: str,
    assets: Mapping[str, Any],
    bindings: Mapping[str, Mapping[str, str]],
    *,
    initialize: bool,
) -> dict:
    """Configure only a newly-created target; existing targets must be exact."""
    public = PublicAgentClient(client, workspace_id, agent_id)
    sources = public.initialize_sources(bindings) if initialize else public.match_sources(bindings)
    if set(sources) != set(KINDS):
        raise ReferenceAgentError("Existing reference Agent has a partial source set; no overwrite performed.")
    for kind, source in sources.items():
        spec = assets["sources"][kind]
        records = public.wait_for_tree(source["id"], kind, spec) if initialize else public.tree(source["id"])
        if initialize:
            changes = selection_changes(kind, records, spec)
            for change in changes:
                public.request(
                    "PATCH",
                    f"/staging/datasources/{source['id']}/elements?" + urlencode({"id": change["id"]}),
                    change["body"],
                )
            public.request("PATCH", f"/staging/datasources/{source['id']}", {
                "instructions": spec["instructions"], "description": spec["description"],
            })
        else:
            verify_selection(kind, records, spec)
    if initialize:
        current = client.get_definition(workspace_id, agent_id)
        desired = draft_with_runtime(current, assets)
        verify_definition(desired, assets, bindings, stages=("draft",))
        response = client._request(
            "POST", public.base + "/updateDefinition", json_body={"definition": desired},
            expected=(200, 202), safe_retry=False,
        )
        if response.status_code == 202:
            client.poll_operation(client._operation_id(response))
        verify_definition(client.get_definition(workspace_id, agent_id), assets, bindings, stages=("draft",))
        staged_sources = public.match_sources(bindings)
        if set(staged_sources) != set(KINDS):
            raise ReferenceAgentError("Staging lost an approved datasource; refusing to publish.")
        for kind, source in staged_sources.items():
            spec = assets["sources"][kind]
            if optional_text(source.get("instructions")) != optional_text(spec["instructions"]) or optional_text(
                source.get("description")
            ) != optional_text(spec["description"]):
                raise ReferenceAgentError(f"Staging source metadata changed for {kind}; refusing to publish.")
            verify_selection(kind, public.tree(source["id"]), assets["sources"][kind])
        public.request("POST", "/staging/publish", {
            "publishedDescription": assets.get("publicationDescription", (
                "Explicitly packaged Furusato AI reference architecture; "
                f"profile status: {assets['globalProfile']['status']}. "
                "Provisioning success is not native answer-quality acceptance."
            )),
        })
    verify_definition(client.get_definition(workspace_id, agent_id), assets, bindings)
    summary = {}
    for stage in ("staging", "published"):
        actual = public.match_sources(bindings, stage)
        if set(actual) != set(KINDS):
            raise ReferenceAgentError(f"{stage} public source bindings are incomplete.")
        for kind, source in actual.items():
            spec = assets["sources"][kind]
            if optional_text(source.get("instructions")) != optional_text(spec["instructions"]) or optional_text(
                source.get("description")
            ) != optional_text(spec["description"]):
                raise ReferenceAgentError(f"{stage} public source metadata differs for {kind}.")
            summary[f"{stage}.{kind}"] = verify_selection(kind, public.tree(source["id"], stage), spec)
    return {
        "state": "CREATED" if initialize else "REUSED",
        "selections": summary,
        "globalSha256": hashlib.sha256(assets["stageConfig"]["aiInstructions"].encode("utf-8")).hexdigest(),
        "profileStatus": assets["globalProfile"]["status"],
        "acceptanceClaimed": False,
    }
