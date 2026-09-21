"""Offline, opt-in transformation of verified reference assets into one profile.

No reads, network, credential handling or execution occur on import. The builder
accepts in-memory inputs; a canonical repository is read only when explicitly
supplied. It neither binds an item nor configures, creates or publishes an agent.
"""

from __future__ import annotations

import copy
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any, Mapping

SCHEMA = "furusato-unified-data-agent/v1"
PROFILE_SCHEMA = "furusato-unified-profile/v1"
GLOBAL_SCHEMA = "furusato-unified-global/v1"
PROFILE_REVISION = 13
ONTOLOGY_INSTRUCTION_POLICY = "preserve-null-use-global"
INSTRUCTION_LIMIT = 15_000
KQL_FEWSHOTS_FILE = "kusto-fewshots.json"
FEWSHOTS_SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item/dataAgent/definition/fewShots/1.0.0/schema.json"
KINDS = ("lakehouse_tables", "kusto", "ontology")
INSTRUCTION_FILES = {
    "global": "global-instructions.txt",
    "lakehouse_tables": "lakehouse-instructions.txt",
    "kusto": "kusto-instructions.txt",
}
FULL_ONTOLOGY_CONTRACT = {
    "definitionParts": 54, "entityTypes": 10, "staticProperties": 72,
    "timeseriesProperties": 1, "dataBindings": 11, "relationshipTypes": 15,
    "contextualizations": 15, "overviews": 1,
}
SELECTION_COUNTS = {
    "lakehouse_tables": {"selectedObjects": 14, "selectedLeaves": 162},
    "kusto": {"selectedObjects": 4, "selectedLeaves": 10},
    "ontology": {"selectedObjects": 10, "selectedLeaves": 0},
}
SELECTION_TYPES = {
    "lakehouse_tables": {"Table": 11, "Column": 88, "View": 1, "Function": 2},
    "kusto": {"MaterializedView": 1, "Column": 10, "Function": 3},
    "ontology": {"Entity": 10},
}
KQL_FUNCTIONS = (
    "AgentRawObservationTotals", "AgentFileRunSummary", "AgentMunicipalityLeaders",
)
KQL_UTC_FIELDS = {
    "AgentRawObservationTotals": (
        "RequestedStartUtc", "RequestedEndUtc", "TrueFirstObservedAt", "TrueLastObservedAt",
    ),
    "AgentFileRunSummary": (
        "FirstObservedAtUtc", "LastObservedAtUtc", "RequestedStartUtc", "RequestedEndUtc",
    ),
    "AgentMunicipalityLeaders": ("RequestedStartUtc", "RequestedEndUtc"),
}
MODULES = ("reference_models", "reference_sql", "reference_kql", "reference_agent")
SQL_SELECTION = {
    "MunicipalityStatic": "View", "MunicipalityById": "Function",
    "DonationTraceById": "Function",
}
ASSET_FIELDS = {
    "contract", "profileManifest", "globalProfile", "stageConfig", "sources",
    "sqlDdl", "kqlFunctions", "moduleSources", "publicationDescription",
}


class UnifiedAgentError(ValueError):
    """Missing, altered or out-of-scope offline assets; no fallback is allowed."""


def sha256_json(value: Any) -> str:
    raw = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _text(value: Any, label: str, *, instruction: bool = False) -> str:
    if not isinstance(value, str) or not value.strip():
        raise UnifiedAgentError(f"{label} must be explicit nonempty text.")
    if instruction and (
        len(value) > INSTRUCTION_LIMIT or "\r" in value
        or value.startswith("\ufeff") or not value.endswith("\n")
    ):
        raise UnifiedAgentError(f"{label} must be UTF-8/LF, newline terminated and <=15000 characters.")
    return value


def _require(value: Any, fields: set[str], label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or not fields.issubset(value):
        raise UnifiedAgentError(f"{label} is missing required fields: {sorted(fields)}.")
    return value


def _selection(source: Any, kind: str) -> dict[str, Any]:
    source = _require(source, {"description", "instructions", "elements"}, f"{kind} source")
    _text(source["description"], f"{kind} description")
    if kind != "ontology" or source["instructions"] is not None:
        _text(source["instructions"], f"{kind} instructions", instruction=True)
    if not isinstance(source["elements"], list) or not source["elements"]:
        raise UnifiedAgentError(f"{kind} source elements must be an explicit nonempty list.")
    return {key: copy.deepcopy(value) for key, value in source.items() if key != "instructions"}


def _check_manifest(manifest: Any) -> Mapping[str, Any]:
    required = {
        "schemaVersion", "status", "validationStatus", "enabledByDefault", "acceptanceClaimed",
        "instructionCharacterLimit", "files", "referenceSelectionsSha256",
        "teachingOntologySourceSha256", "expectedOntologyContract", "expectedSelections",
        "ontologyInstructionPolicy", "profileRevision",
    }
    manifest = _require(manifest, required, "Unified profile manifest")
    if (
        manifest["schemaVersion"] != PROFILE_SCHEMA or manifest["status"] != "candidate"
        or manifest["validationStatus"] != "offline-only"
        or manifest["enabledByDefault"] is not False or manifest["acceptanceClaimed"] is not False
        or manifest["instructionCharacterLimit"] != INSTRUCTION_LIMIT
        or manifest["expectedOntologyContract"] != FULL_ONTOLOGY_CONTRACT
        or manifest["expectedSelections"] != SELECTION_COUNTS
        or manifest["ontologyInstructionPolicy"] != ONTOLOGY_INSTRUCTION_POLICY
        or type(manifest["profileRevision"]) is not int or manifest["profileRevision"] != PROFILE_REVISION
    ):
        raise UnifiedAgentError("Unified manifest must declare the offline-only, full teaching profile.")
    if not isinstance(manifest["files"], Mapping) or set(manifest["files"]) != {
        *INSTRUCTION_FILES.values(), KQL_FEWSHOTS_FILE,
    }:
        raise UnifiedAgentError("Unified instruction/few-shot file inventory differs.")
    fingerprints = manifest["referenceSelectionsSha256"]
    if not isinstance(fingerprints, Mapping) or set(fingerprints) != {"lakehouse_tables", "kusto"}:
        raise UnifiedAgentError("Both reference selection fingerprints are required.")
    for digest in (*fingerprints.values(), manifest["teachingOntologySourceSha256"]):
        if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise UnifiedAgentError("Selection fingerprints must be lowercase SHA-256 values.")
    return manifest


def _check_instruction(text: Any, record: Any, label: str) -> None:
    text = _text(text, label, instruction=True)
    record = _require(record, {"sha256", "characters"}, f"{label} fingerprint")
    if (
        type(record["characters"]) is not int or record["characters"] != len(text)
        or record["sha256"] != hashlib.sha256(text.encode("utf-8")).hexdigest()
    ):
        raise UnifiedAgentError(f"{label} fingerprint/character count mismatch.")


def _expected_kql_query(function: str) -> str:
    expressions = [
        f'{field} = iff(isnull({field}), "", '
        f'strcat(replace_string(format_datetime({field}, "yyyy-MM-dd HH:mm:ss.fffffff"), " ", "T"), "Z"))'
        for field in KQL_UTC_FIELDS[function]
    ]
    return (
        "let StartUtc = datetime(null);\nlet EndUtc = datetime(null);\n"
        f"{function}(StartUtc, EndUtc)\n| extend " + ",\n    ".join(expressions) + "\n"
    )


def _check_kql_fewshots(value: Any, record: Any) -> None:
    record = _require(record, {"sha256", "canonicalSha256", "exampleCount"}, "KQL few-shot fingerprint")
    value = _require(value, {"$schema", "fewShots"}, "KQL few-shots")
    if (
        set(value) != {"$schema", "fewShots"} or value["$schema"] != FEWSHOTS_SCHEMA
        or not isinstance(value["fewShots"], list) or len(value["fewShots"]) != len(KQL_FUNCTIONS)
        or type(record["exampleCount"]) is not int or record["exampleCount"] != len(KQL_FUNCTIONS)
        or sha256_json(value) != record["canonicalSha256"]
    ):
        raise UnifiedAgentError("KQL few-shot count, schema or canonical digest differs.")
    ids = set()
    for example, function in zip(value["fewShots"], KQL_FUNCTIONS):
        _require(example, {"id", "question", "query"}, "KQL few-shot example")
        identifier = _text(example["id"], "KQL few-shot ID")
        _text(example["question"], "KQL few-shot question")
        if set(example) != {"id", "question", "query"} or identifier in ids:
            raise UnifiedAgentError("KQL few-shot fields or unique identities differ.")
        ids.add(identifier)
        if example["query"] != _expected_kql_query(function):
            raise UnifiedAgentError(f"KQL few-shot must retain the exact post-helper UTC-only wrapper: {function}")


def _load_kql_fewshots(raw: Any, record: Any) -> dict[str, Any]:
    raw = _text(raw, "KQL few-shot JSON")
    record = _require(record, {"sha256", "canonicalSha256", "exampleCount"}, "KQL few-shot fingerprint")
    if (
        "\r" in raw or raw.startswith("\ufeff") or not raw.endswith("\n")
        or hashlib.sha256(raw.encode("utf-8")).hexdigest() != record["sha256"]
    ):
        raise UnifiedAgentError("KQL few-shot UTF-8/LF bytes or file digest differ.")
    try:
        value = json.loads(raw)
    except ValueError as exc:
        raise UnifiedAgentError("KQL few-shot file is not valid JSON.") from exc
    _check_kql_fewshots(value, record)
    return value


def validate_profile_files(files: Mapping[str, str]) -> dict[str, Any]:
    """Validate three instruction texts plus independently pinned KQL examples."""
    if not isinstance(files, Mapping) or set(files) != {
        "manifest.json", *INSTRUCTION_FILES.values(), KQL_FEWSHOTS_FILE,
    }:
        raise UnifiedAgentError("Unified profile files are missing or unexpected.")
    raw = _text(files["manifest.json"], "manifest.json")
    if "\r" in raw or raw.startswith("\ufeff") or not raw.endswith("\n"):
        raise UnifiedAgentError("Unified manifest must be newline-terminated UTF-8/LF.")
    try:
        manifest = json.loads(raw)
    except ValueError as exc:
        raise UnifiedAgentError("Unified manifest is not valid JSON.") from exc
    _check_manifest(manifest)
    for name in INSTRUCTION_FILES.values():
        _check_instruction(files[name], manifest["files"][name], name)
    _load_kql_fewshots(files[KQL_FEWSHOTS_FILE], manifest["files"][KQL_FEWSHOTS_FILE])
    return copy.deepcopy(manifest)


def load_profile_files(repo_root: Path | str) -> dict[str, str]:
    """Read only canonical local profile files, explicitly and without writes."""
    folder = Path(repo_root) / "tools" / "data-agent" / "unified"
    try:
        result = {
            name: (folder / name).read_bytes().decode("utf-8")
            for name in ("manifest.json", *INSTRUCTION_FILES.values(), KQL_FEWSHOTS_FILE)
        }
    except (OSError, UnicodeError) as exc:
        raise UnifiedAgentError("Canonical local unified profile files are unavailable.") from exc
    validate_profile_files(result)
    return result


def _teaching_source(source: Any) -> dict[str, Any]:
    """Strip serialized binding IDs; accept only the complete flat entity inventory."""
    if not isinstance(source, Mapping):
        raise UnifiedAgentError("Core teaching Ontology datasource metadata is required.")
    if "type" in source:
        _require(source, {"type", "elements", "userDescription", "dataSourceInstructions"}, "Core Ontology source")
        if source["type"] != "ontology" or not isinstance(source["elements"], list):
            raise UnifiedAgentError("Expected a Core ontology datasource.json.")
        elements = []
        for node in source["elements"]:
            _require(node, {"type", "is_selected", "children", "display_name", "description"}, "Core entity")
            if node["type"] != "ontology.entity" or node["is_selected"] is not True or node["children"] != []:
                raise UnifiedAgentError("Core Ontology must explicitly select every complete entity.")
            elements.append({
                "path": [["Entity", _text(node["display_name"], "Core entity name")]],
                "description": _text(node["description"], "Core property inventory"),
            })
        source = {
            "description": source["userDescription"],
            "instructions": source["dataSourceInstructions"],
            "elements": elements,
        }
    _selection(source, "ontology")
    if len(source["elements"]) != FULL_ONTOLOGY_CONTRACT["entityTypes"]:
        raise UnifiedAgentError("Teaching Ontology must retain all 10 entities.")
    return copy.deepcopy(dict(source))


def _check_selection(
    source: Mapping[str, Any], kind: str, manifest: Mapping[str, Any],
    *, unified_kql: bool = False,
) -> None:
    expected = (
        manifest["teachingOntologySourceSha256"] if kind == "ontology"
        else manifest["referenceSelectionsSha256"][kind]
    )
    selection = _selection(source, kind)
    if kind == "kusto" and unified_kql:
        selection.pop("fewShots", None)
    if sha256_json(selection) != expected:
        raise UnifiedAgentError(f"{kind} selection differs from the pinned portable contract.")
    paths = []
    for entry in source["elements"]:
        _require(entry, {"path", "description"}, f"{kind} selected element")
        path = entry["path"]
        if (
            not isinstance(path, list) or not path
            or any(not isinstance(part, list) or len(part) != 2
                   or any(not isinstance(value, str) or not value for value in part) for part in path)
        ):
            raise UnifiedAgentError(f"{kind} portable path is malformed.")
        _text(entry["description"], f"{kind} element description")
        paths.append(tuple(tuple(part) for part in path))
    types = Counter(path[-1][0] for path in paths)
    if len(set(paths)) != len(paths) or types != SELECTION_TYPES[kind]:
        raise UnifiedAgentError(f"{kind} selected object/column counts or unique paths differ.")
    leaves = types["Column"]
    if kind == "lakehouse_tables":
        interfaces = _require(source.get("referenceObjects"), set(SQL_SELECTION), "SQL interfaces")
        if set(interfaces) != set(SQL_SELECTION):
            raise UnifiedAgentError("SQL interfaces must contain exactly the approved view and two TVFs.")
        for name, field_count, parameter in (
            ("MunicipalityStatic", 20, None),
            ("MunicipalityById", 22, "@RequestedMunicipalityId"),
            ("DonationTraceById", 30, "@RequestedDonationId"),
        ):
            interface = _require(interfaces[name], {"type", "fields", "parameter"}, name)
            if (
                interface["type"] != SQL_SELECTION[name] or interface["parameter"] != parameter
                or not isinstance(interface["fields"], list) or len(interface["fields"]) != field_count
                or (("Schema", "agent_ref"), (interface["type"], name)) not in paths
            ):
                raise UnifiedAgentError(f"SQL interface count/parameter differs: {name}")
            leaves += field_count + int(parameter is not None)
    elif kind == "kusto":
        objects = {path for path in paths if path[-1][0] != "Column"}
        if objects != {
            (("MaterializedView", "DonationObservationSummaryForAgent"),),
            *((("Function", name),) for name in KQL_FUNCTIONS),
        }:
            raise UnifiedAgentError("KQL objects differ from the approved MV and three helpers.")
    else:
        properties = [entry["description"].split(",") for entry in source["elements"]]
        if (
            any(len(path) != 1 for path in paths) or sum(map(len, properties)) != 73
            or any(not all(names) or len(set(names)) != len(names) for names in properties)
            or [path[0][1] for path, names in zip(paths, properties) if "IncomingDonationAmountYen" in names]
            != ["Municipality"]
        ):
            raise UnifiedAgentError("Full teaching property inventory must retain 72 static plus one time-series property.")
    counts = {"selectedObjects": len(paths) - types["Column"], "selectedLeaves": leaves}
    if counts != SELECTION_COUNTS[kind]:
        raise UnifiedAgentError(f"{kind} selected object/leaf counts differ.")


def _check_reference(reference: Any, manifest: Mapping[str, Any]) -> None:
    _require(reference, {"contract", "globalProfile", "stageConfig", "sources",
                         "sqlDdl", "kqlFunctions", "moduleSources"}, "Verified reference assets")
    contract = _require(reference["contract"], {
        "schemaVersion", "files", "sqlDdlOrder", "sqlObjects", "selectedSqlObjects", "kqlFunctions", "modules",
    }, "Reference contract")
    if (
        contract["schemaVersion"] != "furusato-ai-reference-runtime/v1"
        or contract["selectedSqlObjects"] != SQL_SELECTION
        or contract["kqlFunctions"] != list(KQL_FUNCTIONS)
        or set(contract["modules"]) != {*MODULES, "reference_ontology"}
    ):
        raise UnifiedAgentError("Verified reference inventory is not the approved helper contract.")
    stage = _require(reference["stageConfig"], {"aiInstructions", "experimental"}, "Reference stageConfig")
    global_text = _text(stage["aiInstructions"], "Reference GLOBAL", instruction=True)
    if not isinstance(stage["experimental"], Mapping):
        raise UnifiedAgentError("Reference experimental config must be explicit.")
    profile = _require(reference["globalProfile"], {"schemaVersion", "status", "sha256"}, "Reference GLOBAL profile")
    if (
        profile["schemaVersion"] != "furusato-reference-global/v1"
        or profile["status"] not in {"candidate", "accepted"}
        or profile["sha256"] != hashlib.sha256(global_text.encode("utf-8")).hexdigest()
    ):
        raise UnifiedAgentError("Reference GLOBAL must already be verified and hash-pinned.")
    sources = reference["sources"]
    if not isinstance(sources, Mapping) or set(sources) != set(KINDS):
        raise UnifiedAgentError("Reference assets must contain exactly three sources.")
    for kind in KINDS:
        _selection(sources[kind], kind)
        if kind != "ontology":
            _check_selection(sources[kind], kind, manifest)
    ddl = reference["sqlDdl"]
    if not isinstance(ddl, (list, tuple)) or any(not isinstance(pair, (list, tuple)) or len(pair) != 2 for pair in ddl):
        raise UnifiedAgentError("Reference SQL DDL must retain its ordered name/text pairs.")
    if [name for name, _ in ddl] != contract["sqlDdlOrder"]:
        raise UnifiedAgentError("Reference SQL DDL order changed.")
    for field, names in (("kqlFunctions", KQL_FUNCTIONS), ("moduleSources", contract["modules"])):
        if not isinstance(reference[field], Mapping) or set(reference[field]) != set(names):
            raise UnifiedAgentError(f"Reference {field} inventory changed.")
    files = _require(contract["files"], set(), "Reference file hashes")
    materialized = [
        *((f"sql/{name}", text) for name, text in ddl),
        *((f"kql/{name}.kql", text) for name, text in reference["kqlFunctions"].items()),
        *((f"modules/{name}.py", text) for name, text in reference["moduleSources"].items()),
    ]
    for path, text in materialized:
        _text(text, f"Reference {path}")
        if files.get("ai-reference/" + path) != hashlib.sha256(text.encode("utf-8")).hexdigest():
            raise UnifiedAgentError(f"Verified reference helper digest changed: {path}")


def build_unified_assets(
    verified_reference_assets: Mapping[str, Any],
    teaching_ontology_source: Mapping[str, Any] | None = None,
    profile_files: Mapping[str, str] | None = None,
    *,
    repo_root: Path | str | None = None,
) -> dict[str, Any]:
    """Return hash-bound assets compatible with reference_agent's pure helpers.

    Pass all three inputs positionally or by their declared keyword names for
    a filesystem-free build. Alternatively pass a
    canonical repo_root to load missing profile files and the released Core
    published Ontology datasource. Never consumes the reference path template.
    """
    if (profile_files is None or teaching_ontology_source is None) and repo_root is None:
        raise UnifiedAgentError("Pass in-memory profile/Core metadata or an explicit canonical repo_root.")
    if profile_files is None:
        profile_files = load_profile_files(repo_root)
    manifest = validate_profile_files(profile_files)
    _check_reference(verified_reference_assets, manifest)
    if teaching_ontology_source is None:
        path = (
            Path(repo_root) / "workshop" / "v2.7.0" / "provisioning" / "bundle"
            / "data-agent" / "Files" / "Config" / "published"
            / "ontology-{{name.ontology}}" / "datasource.json"
        )
        try:
            teaching_ontology_source = json.loads(path.read_bytes().decode("utf-8"))
        except (OSError, UnicodeError, ValueError) as exc:
            raise UnifiedAgentError("Canonical Core teaching Ontology metadata is unavailable.") from exc
    teaching = _teaching_source(teaching_ontology_source)
    _check_selection(teaching, "ontology", manifest)
    if teaching["instructions"] is not None:
        raise UnifiedAgentError("Core Ontology instructions must be explicit null; guidance belongs in GLOBAL.")
    reference = verified_reference_assets
    sources = {kind: copy.deepcopy(reference["sources"][kind]) for kind in KINDS if kind != "ontology"}
    sources["ontology"] = teaching
    for kind in KINDS:
        if kind != "ontology":
            sources[kind]["instructions"] = profile_files[INSTRUCTION_FILES[kind]]
    sources["kusto"]["fewShots"] = _load_kql_fewshots(
        profile_files[KQL_FEWSHOTS_FILE], manifest["files"][KQL_FEWSHOTS_FILE],
    )
    stage = copy.deepcopy(reference["stageConfig"])
    stage["aiInstructions"] = profile_files[INSTRUCTION_FILES["global"]]
    stage["experimental"].update({"codeInterpreterEnabled": True, "enableExperimentalFeatures": True})
    result = {
        "contract": {
            "schemaVersion": SCHEMA, "mode": "unified", "enabledByDefault": False,
            "profileRevision": PROFILE_REVISION,
            "agentTargetRole": "existing-primary", "ontologyBindingRole": "teachingOntology",
            "ontologyAction": "reuse-only", "expectedOntologyContract": copy.deepcopy(FULL_ONTOLOGY_CONTRACT),
            "ontologyInstructionPolicy": ONTOLOGY_INSTRUCTION_POLICY,
            "expectedSelections": copy.deepcopy(SELECTION_COUNTS), "acceptanceClaimed": False,
            "referenceContractSha256": sha256_json(reference["contract"]),
            "referenceGlobalSha256": reference["globalProfile"]["sha256"],
            "profileManifestSha256": sha256_json(manifest),
            **{key: copy.deepcopy(reference["contract"][key]) for key in (
                "sqlDdlOrder", "sqlObjects", "selectedSqlObjects", "kqlFunctions",
            )},
            "modules": list(MODULES),
        },
        "profileManifest": manifest,
        "globalProfile": {
            "schemaVersion": GLOBAL_SCHEMA, "status": "candidate",
            "profileRevision": PROFILE_REVISION,
            "sha256": manifest["files"][INSTRUCTION_FILES["global"]]["sha256"],
            "statusProvenance": "Offline assembly only; native validation and publication are not claimed.",
        },
        "stageConfig": stage,
        "sources": sources,
        "sqlDdl": copy.deepcopy(reference["sqlDdl"]),
        "kqlFunctions": copy.deepcopy(reference["kqlFunctions"]),
        "moduleSources": {name: reference["moduleSources"][name] for name in MODULES},
        "publicationDescription": (
            "Unified Furusato profile: full teaching Ontology, approved SQL/KQL reference helpers "
            "and post-query Code Interpreter (Preview). Configuration is not answer-quality acceptance."
        ),
    }
    result["contract"]["sha256"] = sha256_json(result)
    verify_unified_assets(result)
    return result


def verify_unified_assets(assets: Mapping[str, Any]) -> dict[str, Any]:
    """Check the offline content seal and source boundaries, never live bindings."""
    if not isinstance(assets, Mapping) or set(assets) != ASSET_FIELDS:
        raise UnifiedAgentError("Unified asset fields are missing/unexpected; no ontology template is allowed.")
    contract = _require(assets["contract"], {
        "schemaVersion", "mode", "enabledByDefault", "agentTargetRole", "ontologyBindingRole",
        "ontologyAction", "expectedOntologyContract", "expectedSelections", "acceptanceClaimed",
        "profileManifestSha256", "sha256", "modules", "kqlFunctions", "selectedSqlObjects",
        "ontologyInstructionPolicy", "profileRevision",
    }, "Unified contract")
    if (
        contract["schemaVersion"] != SCHEMA or contract["mode"] != "unified"
        or contract["enabledByDefault"] is not False or contract["acceptanceClaimed"] is not False
        or contract["agentTargetRole"] != "existing-primary" or contract["ontologyAction"] != "reuse-only"
        or contract["ontologyBindingRole"] != "teachingOntology"
        or contract["ontologyInstructionPolicy"] != ONTOLOGY_INSTRUCTION_POLICY
        or type(contract["profileRevision"]) is not int or contract["profileRevision"] != PROFILE_REVISION
        or contract["expectedOntologyContract"] != FULL_ONTOLOGY_CONTRACT
        or contract["expectedSelections"] != SELECTION_COUNTS
        or contract["modules"] != list(MODULES) or contract["kqlFunctions"] != list(KQL_FUNCTIONS)
        or contract["selectedSqlObjects"] != SQL_SELECTION
        or not isinstance(assets["moduleSources"], Mapping) or set(assets["moduleSources"]) != set(MODULES)
        or not isinstance(assets["kqlFunctions"], Mapping) or set(assets["kqlFunctions"]) != set(KQL_FUNCTIONS)
    ):
        raise UnifiedAgentError("Unified profile mode, helper or teaching Ontology contract differs.")
    unsigned = copy.deepcopy(dict(assets))
    expected = unsigned["contract"].pop("sha256")
    if sha256_json(unsigned) != expected:
        raise UnifiedAgentError("Unified asset digest mismatch.")
    manifest = _check_manifest(assets["profileManifest"])
    if sha256_json(manifest) != contract["profileManifestSha256"]:
        raise UnifiedAgentError("Unified profile manifest digest mismatch.")
    stage = _require(assets["stageConfig"], {"aiInstructions", "experimental"}, "Unified stageConfig")
    experimental = _require(stage["experimental"], {"codeInterpreterEnabled", "enableExperimentalFeatures"}, "Unified CI flags")
    if experimental["codeInterpreterEnabled"] is not True or experimental["enableExperimentalFeatures"] is not True:
        raise UnifiedAgentError("Unified Code Interpreter flags must both be explicitly true.")
    profile = _require(assets["globalProfile"], {"schemaVersion", "status", "sha256", "profileRevision"}, "Unified GLOBAL profile")
    if (
        profile["schemaVersion"] != GLOBAL_SCHEMA or profile["status"] != "candidate"
        or type(profile["profileRevision"]) is not int or profile["profileRevision"] != PROFILE_REVISION
        or profile["sha256"] != manifest["files"][INSTRUCTION_FILES["global"]]["sha256"]
    ):
        raise UnifiedAgentError("Unified GLOBAL is not the explicit candidate profile.")
    _check_instruction(stage["aiInstructions"], manifest["files"][INSTRUCTION_FILES["global"]], "Unified GLOBAL")
    if not isinstance(assets["sources"], Mapping) or set(assets["sources"]) != set(KINDS):
        raise UnifiedAgentError("Unified assets must select exactly three sources, including ONE Ontology.")
    for kind, source in assets["sources"].items():
        _check_selection(source, kind, manifest, unified_kql=kind == "kusto")
        if kind == "ontology":
            if source["instructions"] is not None:
                raise UnifiedAgentError("Ontology instructions must remain explicit null; guidance belongs in GLOBAL.")
        else:
            _check_instruction(source["instructions"], manifest["files"][INSTRUCTION_FILES[kind]], f"{kind} instructions")
        if kind == "kusto":
            _require(source, {"fewShots"}, "Unified KQL source")
            _check_kql_fewshots(source["fewShots"], manifest["files"][KQL_FEWSHOTS_FILE])
    _text(assets["publicationDescription"], "Unified publication description")
    return {
        "mode": "unified", "profileRevision": PROFILE_REVISION,
        "globalCharacters": len(stage["aiInstructions"]),
        "globalSha256": profile["sha256"], "assetSha256": contract["sha256"],
        "kustoFewShotsSha256": manifest["files"][KQL_FEWSHOTS_FILE]["canonicalSha256"],
        "kustoFewShotCount": len(KQL_FUNCTIONS),
        "selections": copy.deepcopy(SELECTION_COUNTS), "acceptanceClaimed": False,
    }
