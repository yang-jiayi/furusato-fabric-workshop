"""Build the opt-in reference bundle from canonical local sources.

No candidate definition, private controller, evaluation result, tenant ID or
credential is consumed. GLOBAL is deliberately absent until an operator freezes
one explicitly with reseal_runtime.py --reference-global, --reference-global-sha256
and --reference-global-status. That operation never edits released Core inputs.
"""

from __future__ import annotations

import base64
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

PREFIX = "ai-reference/"
SCHEMA = "furusato-ai-reference-runtime/v1"
SOURCE_CONTRACT_SCHEMA = "furusato-reference-source-contract/v1"
MODULE_PATHS = {
    "reference_models": "tools/data-agent/reference-models/reference_models.py",
    "reference_sql": "tools/provisioning/reference_sql.py",
    "reference_kql": "tools/provisioning/reference_kql.py",
    "reference_ontology": "tools/provisioning/reference_ontology.py",
    "reference_agent": "tools/provisioning/reference_agent.py",
}
KQL_FUNCTIONS = (
    "AgentRawObservationTotals", "AgentFileRunSummary", "AgentMunicipalityLeaders",
)
SQL_SELECTED = {
    "MunicipalityStatic": "View",
    "MunicipalityById": "Function",
    "DonationTraceById": "Function",
}


def json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def load_module(root: Path, name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, root / relative)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def derive_path_template(root: Path) -> dict[str, Any]:
    path = root / "workshop/v2.7.0/ontology/ontology-full-definition-template.json"
    original = json.loads(path.read_text("utf-8"))
    transformer = load_module(root, "_furusato_path_template", "tools/data-agent/path_ontology.py")
    envelope = {"definition": {"parts": [
        {
            "path": part["path"], "payloadType": "InlineBase64",
            "payload": base64.b64encode(canonical(part["content"])).decode("ascii"),
        }
        for part in original["parts"]
    ]}}
    transformed, report = transformer.transform(envelope, "ONT_Furusato_AIPath_<PID>")
    after = report["afterCounts"]
    if (after["entities"], after["staticProperties"], after["timeseriesProperties"],
            after["relationships"], after["contextualizations"]) != (10, 21, 0, 15, 15):
        raise ValueError("Source-faithful AI path derivation changed its structural contract.")
    parts = [
        {"path": part["path"], "content": json.loads(base64.b64decode(part["payload"]))}
        for part in transformed["definition"]["parts"]
    ]
    next(part for part in parts if part["path"] == ".platform")["content"]["metadata"][
        "displayName"
    ] = "{{ontology.displayName}}"
    return {
        "schemaVersion": SCHEMA,
        "ontologyDisplayNameTemplate": "ONT_Furusato_AIPath_<PID>",
        "derivation": {
            "sourceTemplateSha256": digest(path.read_bytes()),
            "transformerSha256": digest((root / "tools/data-agent/path_ontology.py").read_bytes()),
            "contextualizationsPreserved": True,
            "relationshipIdsAndEndpointsPreserved": True,
            "acceptanceClaimed": False,
        },
        "expectedContract": {
            "definitionParts": 52, "entityTypes": 10, "staticProperties": 21,
            "timeseriesProperties": 0, "dataBindings": 10, "relationshipTypes": 15,
            "contextualizations": 15, "overviews": 0,
        },
        "definitionTemplateSha256": digest(canonical(parts)),
        "parts": parts,
    }


def source_metadata(root: Path, path_template: dict[str, Any]) -> dict[str, Any]:
    kql = load_module(root, "_furusato_reference_kql_metadata", MODULE_PATHS["reference_kql"])
    function_contracts = kql.validate_function_contracts(
        kql.load_function_scripts(root / "tools/data-agent/operational-functions")
    )
    config = root / "workshop/v2.7.0/provisioning/bundle/data-agent/Files/Config/published"
    by_type = {
        document["type"]: document
        for path in config.glob("*/datasource.json")
        for document in [json.loads(path.read_text("utf-8"))]
    }
    contract_root = root / "tools/data-agent/source-contract"
    contract = json.loads((contract_root / "contract.json").read_text("utf-8"))
    if contract.get("schemaVersion") != SOURCE_CONTRACT_SCHEMA:
        raise ValueError("Unsupported structural source contract schema.")
    trace_fields = json.loads(
        (contract_root / "trace-and-operational-descriptions.json").read_text("utf-8")
    )
    result: dict[str, Any] = {}
    for kind, instruction_key in (("lakehouse_tables", "lakehouse"), ("kusto", "kusto")):
        record = contract["instructions"][instruction_key]
        raw = (contract_root / record["file"]).read_bytes()
        if digest(raw) != record["sha256"]:
            raise ValueError(f"Unpinned structural source instructions: {kind}")
        result[kind] = {
            "instructions": raw.decode("utf-8"),
            "description": contract["sourceDescriptions"][kind],
            "elements": [],
        }
    result["ontology"] = {
        "instructions": by_type["ontology"].get("dataSourceInstructions", ""),
        "description": contract["sourceDescriptions"]["ontology"],
        "elements": [],
    }
    public_types = {
        "lakehouse_tables.schema": "Schema", "lakehouse_tables.table": "Table",
        "lakehouse_tables.column": "Column", "kusto.table": "MaterializedView",
        "kusto.column": "Column",
    }

    def collect(nodes, output, path=()):
        for node in nodes:
            if node.get("is_selected") is False:
                continue
            kind = public_types.get(node.get("type"))
            current = path + ((kind, node["display_name"]),) if kind else path
            if kind and kind != "Schema":
                output.append({"path": [list(piece) for piece in current],
                               "description": node.get("description", "")})
            collect(node.get("children", []), output, current)

    for kind in ("lakehouse_tables", "kusto"):
        collect(by_type[kind]["elements"], result[kind]["elements"])
    base = result["lakehouse_tables"]["elements"]
    if sum(entry["path"][-1][0] == "Table" for entry in base) != 11 or sum(
        entry["path"][-1][0] == "Column" for entry in base
    ) != 88:
        raise ValueError("The released Lakehouse selection is not the required 11/88 contract.")
    schema = json.loads(
        (contract_root / "entrypoint-schema.json").read_text("utf-8")
    )["objects"]
    field_text = json.loads(
        (contract_root / "field-descriptions.json").read_text("utf-8")
    )
    trace = json.loads((root / "tools/data-agent/reference-models/trace-schema.json").read_text("utf-8"))
    result["lakehouse_tables"]["referenceObjects"] = {}
    for name, kind in SQL_SELECTED.items():
        fields = (
            trace["fields"] if name == "DonationTraceById"
            else schema[name]["returnValues" if kind == "Function" else "fields"]
        )
        description = (
            trace_fields[name]
            if name == "DonationTraceById" else contract["objectDescriptions"][name]
        )
        base.append({"path": [["Schema", "agent_ref"], [kind, name]], "description": description})
        descriptions = {**field_text, **trace_fields} if name == "DonationTraceById" else field_text
        parameter = (
            None if kind == "View"
            else ("@RequestedMunicipalityId" if name == "MunicipalityById" else "@RequestedDonationId")
        )
        result["lakehouse_tables"]["referenceObjects"][name] = {
            "type": kind, "fields": fields,
            "fieldDescriptions": {field: descriptions[field] for field, _ in fields},
            "parameter": parameter,
            "parameterDescription": descriptions[parameter] if parameter else None,
        }
    for name in KQL_FUNCTIONS:
        result["kusto"]["elements"].append({
            "path": [["Function", name]],
            "description": trace_fields[name] if name in trace_fields else function_contracts[name].docstring,
        })
    for part in path_template["parts"]:
        if part["path"].startswith("EntityTypes/") and part["path"].endswith("/definition.json"):
            entity = part["content"]
            result["ontology"]["elements"].append({
                "path": [["Entity", entity["name"]]],
                "description": ",".join(prop["name"] for prop in entity["properties"]),
            })
    result["lakehouse_tables"]["fewShots"] = json.loads(
        next(config.glob("lakehouse-tables-*/fewshots.json")).read_text("utf-8")
    )
    return result


def build_assets(root: Path) -> dict[str, str]:
    """Return generated files; the transactional resealer is the sole writer."""
    path_template = derive_path_template(root)
    assets = {
        PREFIX + "ontology-template.json": json_text(path_template),
        PREFIX + "source-metadata.json": json_text(source_metadata(root, path_template)),
    }
    for name, path in MODULE_PATHS.items():
        assets[PREFIX + f"modules/{name}.py"] = (root / path).read_bytes().decode("utf-8")
    sql = load_module(root, "_furusato_reference_models_build", MODULE_PATHS["reference_models"])
    ddl = sql.load_ddl(root / "tools/data-agent/reference-models")
    sql.validate_plan(ddl)
    for name, text in ddl:
        assets[PREFIX + "sql/" + name] = text
    for name in KQL_FUNCTIONS:
        assets[PREFIX + f"kql/{name}.kql"] = (
            root / f"tools/data-agent/operational-functions/{name}.kql"
        ).read_bytes().decode("utf-8")
    contract = {
        "schemaVersion": SCHEMA,
        "enabledByDefault": False,
        "globalProfileRequired": True,
        "agentNameTemplate": "DA_Furusato_AIReference_<PID>",
        "agentOntologyNameTemplate": "ONT_Furusato_AIPath_<PID>",
        "sqlDdlOrder": [name for name, _ in ddl],
        "sqlObjects": dict(sql.EXPECTED_OBJECTS),
        "selectedSqlObjects": SQL_SELECTED,
        "kqlFunctions": list(KQL_FUNCTIONS),
        "kqlBaseManagementCommandCount": 5,
        "kqlReferenceManagementCommandCount": 8,
        "modules": list(MODULE_PATHS),
        "nativeSchemaProvenance": (
            "SQL sys catalog and KQL .show function / getschema are separate from "
            "Agent metadata. Empty serialized SQL data types remain empty. KQL functions "
            "are discovered Available Function leaves with hasSubElements=false."
        ),
        "files": {path: digest(text.encode("utf-8")) for path, text in sorted(assets.items())},
    }
    assets[PREFIX + "contract.json"] = json_text(contract)
    return assets
