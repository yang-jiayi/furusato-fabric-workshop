"""Runtime engine embedded in Notebook 04.

The released path uses the Python standard library, ``requests``, supplied
Fabric ``notebookutils`` and the embedded Ontology creator. The opt-in AI
reference path additionally requires the documented SQL driver prerequisites.
Every mutation is guarded by an exact preview hash; no non-idempotent POST is
retried automatically. reseal_runtime.py is the sole Notebook 04 writer.
"""
from __future__ import annotations

import base64
import copy
import gzip
import hashlib
import json
import re
import sys
import time
import types
import urllib.parse
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, MutableMapping, Sequence

import requests

FABRIC_API = "https://api.fabric.microsoft.com/v1"
MAX_PAGE_REQUESTS = 1000
MAX_RETRY_DELAY_SECONDS = 60.0
EXPECTED_TABLES = (
    "stg_prefectures",
    "stg_municipalities",
    "stg_donors",
    "stg_categories",
    "stg_gifts",
    "stg_businesses",
    "stg_business_gifts",
    "stg_donation_orders",
    "ot_prefecture",
    "ot_municipality",
    "ot_donor",
    "ot_gift_category",
    "ot_gift",
    "ot_supplier",
    "ot_supplier_gift",
    "ot_donation",
    "ot_mun_category_metric",
    "ot_pref_category_metric",
    "ot_pref_donation_flow",
    "audit_furusato_load_manifest",
)
PUBLISH_CONTROL_TABLE = "audit_furusato_publish_control"
EXPECTED_DATA_AGENT_TABLES = (
    "ot_prefecture",
    "ot_municipality",
    "ot_donor",
    "ot_gift_category",
    "ot_gift",
    "ot_supplier",
    "ot_donation",
    "ot_mun_category_metric",
    "ot_pref_category_metric",
    "ot_pref_donation_flow",
    "ot_supplier_gift",
)
EXPECTED_ONTOLOGY_ENTITIES = (
    "Prefecture",
    "Municipality",
    "Donor",
    "GiftCategory",
    "Gift",
    "Supplier",
    "Donation",
    "MunicipalityCategoryMetric",
    "PrefectureCategoryMetric",
    "PrefectureDonationFlow",
)
TOKEN_PATTERN = re.compile(
    r"(?i)(authorization|bearer|sharedaccesskey|sig=|client_secret|password)"
)
GUID_PATTERN = re.compile(
    r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"
)
PARTICIPANT_PATTERN = re.compile(r"^(?!000$)[0-9]{3}$")
EXPECTED_KQL_MANAGEMENT_COMMANDS = 5
SAFE_ALIAS_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{2,63}$")


class ProvisioningError(RuntimeError):
    """Base fail-closed provisioner exception."""


class ConflictError(ProvisioningError):
    """A same-name item exists but is not the exact desired state."""


class AmbiguousOutcomeError(ProvisioningError):
    """A non-idempotent request may have reached the service."""


class OperationFailedError(ProvisioningError):
    """A Fabric LRO or job completed unsuccessfully."""


class OperationTimeoutError(ProvisioningError):
    """A bounded poll exceeded its timeout."""


def _is_http_status_error(error: Exception, status_code: int) -> bool:
    return f"failed with http {status_code}:" in str(error).casefold()


def utc_now() -> datetime:
    return datetime.now(UTC)


def parse_iso_datetime(value: Any) -> datetime:
    text = str(value).strip()
    if text[-1:].casefold() == "z":
        text = text[:-1] + "+00:00"
    text = re.sub(
        r"(\.\d{6})\d+(?=(?:[+-]\d{2}:\d{2})?$)",
        r"\1",
        text,
    )
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_json(value: Any) -> str:
    return sha256_bytes(canonical_json_bytes(value))


def _describe_endpoint(url: Any) -> str:
    parsed = urllib.parse.urlsplit(str(url))
    path = parsed.path or "/"
    return GUID_PATTERN.sub("<id>", path)


def _retry_delay_seconds(retry_after: Any, attempt: int) -> float:
    fallback = float(min(2**attempt, 10))
    if retry_after is None:
        return fallback
    try:
        requested = float(str(retry_after).strip())
    except ValueError:
        return fallback
    if requested <= 0:
        return fallback
    return min(requested, MAX_RETRY_DELAY_SECONDS)


def sanitize_error(value: BaseException | str) -> str:
    text = str(value)
    text = GUID_PATTERN.sub("<redacted-guid>", text)
    text = re.sub(r"https?://[^\s\"'<>]+", "<redacted-url>", text)
    text = re.sub(
        r"(?i)(authorization|bearer|sharedaccesskey|client_secret|password)"
        r"\s*[:=]\s*\S+",
        r"\1=<redacted>",
        text,
    )
    return text[:1000]


def render_placeholders(value: Any, bindings: Mapping[str, str]) -> Any:
    if isinstance(value, dict):
        return {key: render_placeholders(item, bindings) for key, item in value.items()}
    if isinstance(value, list):
        return [render_placeholders(item, bindings) for item in value]
    if isinstance(value, str):
        rendered = value
        for placeholder, replacement in bindings.items():
            rendered = rendered.replace("{{" + placeholder + "}}", replacement)
        unresolved = re.findall(r"\{\{[^{}]+\}\}", rendered)
        if unresolved:
            raise ProvisioningError(
                f"Unresolved placeholders remain: {sorted(set(unresolved))}"
            )
        return rendered
    return value


def encode_part(path: str, value: Any, *, raw_text: bool = False) -> dict[str, str]:
    if raw_text:
        payload_bytes = str(value).encode("utf-8")
    else:
        payload_bytes = json.dumps(
            value, ensure_ascii=False, indent=2, sort_keys=True
        ).encode("utf-8")
    return {
        "path": path.replace("\\", "/"),
        "payload": base64.b64encode(payload_bytes).decode("ascii"),
        "payloadType": "InlineBase64",
    }


def decode_definition_parts(definition: Mapping[str, Any]) -> dict[str, bytes]:
    result: dict[str, bytes] = {}
    for part in definition.get("parts", []):
        path = str(part["path"]).replace("\\", "/")
        if path in result:
            raise ProvisioningError(f"Duplicate definition part path: {path}")
        result[path] = base64.b64decode(part["payload"], validate=True)
    return result


def normalize_semantic_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): normalize_semantic_value(child)
            for key, child in sorted(value.items())
        }
    if isinstance(value, list):
        return [normalize_semantic_value(child) for child in value]
    if isinstance(value, str):
        stripped = value.strip()
        if stripped[:1] in {"{", "["}:
            try:
                parsed = json.loads(stripped)
            except json.JSONDecodeError:
                return value
            return normalize_semantic_value(parsed)
    return value


def normalize_data_agent_source(document: Mapping[str, Any]) -> dict[str, Any]:
    """Compare authored bindings and effective selections, not UI cache IDs.

    Opening the editor hydrates unselected schema trees and regenerates
    their UI IDs. Resource IDs, selected names/types/descriptions and
    source instructions remain protected by the comparison.
    """
    result = copy.deepcopy(dict(document))
    selected = []

    def visit(node: Mapping[str, Any], path: tuple[str, ...] = (), enabled: bool = True) -> None:
        kind = str(node.get("type", ""))
        grouping = kind.endswith("_grouping") or kind == "kusto"
        enabled = enabled and (grouping or bool(node.get("is_selected", True)))
        if not enabled:
            return
        if "display_name" in node:
            path = path + (str(node["display_name"]),)
        if kind.endswith((".schema", ".table", ".column", ".view", ".function")) or kind in {"function.parameter", "function.returnValue"}:
            selected.append({
                "path": list(path),
                "definition": {key: copy.deepcopy(value) for key, value in node.items() if key not in {"id", "children"}},
            })
        for child in node.get("children", []):
            visit(child, path, enabled)

    for element in result.pop("elements", []):
        visit(element)
    result["effectiveSelectedObjects"] = sorted(selected, key=lambda value: tuple(value["path"]))
    return result


def semantic_definition_parts(definition: Mapping[str, Any]) -> dict[str, bytes]:
    normalized: dict[str, bytes] = {}
    for path, content in decode_definition_parts(definition).items():
        if path.casefold() == ".platform":
            continue
        try:
            document = json.loads(content.decode("utf-8-sig"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            normalized[path] = content
        else:
            if path in {"Files/Config/draft/stage_config.json", "Files/Config/published/stage_config.json"}:
                experimental = document.get("experimental")
                if isinstance(experimental, dict):
                    # The service omits the explicit false default. Live
                    # Draft/Published Tools UI proved it off; true remains
                    # significant and is never normalized away.
                    if experimental.get("codeInterpreterEnabled") is False:
                        experimental.pop("codeInterpreterEnabled")
                    if not experimental:
                        document.pop("experimental", None)
            if path.startswith("Files/Config/") and path.endswith("/datasource.json") and document.get("type") in {"lakehouse_tables", "kusto"}:
                document = normalize_data_agent_source(document)
            normalized[path] = canonical_json_bytes(
                normalize_semantic_value(document)
            )
    return normalized


def definition_digest(definition: Mapping[str, Any]) -> str:
    parts = semantic_definition_parts(definition)
    normalized = [
        {"path": path, "sha256": sha256_bytes(content)}
        for path, content in sorted(parts.items())
    ]
    return sha256_json(normalized)


def definitions_equal(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    return definition_digest(left) == definition_digest(right)


def extract_kql_management_commands(text: str) -> list[str]:
    verification_marker = "// Pipeline ingestion verification."
    if verification_marker not in text:
        raise ProvisioningError(
            f"KQL script is missing the exact verification marker: "
            f"{verification_marker}"
        )
    schema_text = text.split(verification_marker, 1)[0]
    commands: list[str] = []
    current: list[str] = []
    for line in schema_text.replace("\r\n", "\n").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("//"):
            continue
        if line.startswith(".") and current:
            commands.append("\n".join(current).strip())
            current = []
        current.append(line)
    if current:
        commands.append("\n".join(current).strip())
    commands = [command for command in commands if command.startswith(".")]
    if len(commands) != EXPECTED_KQL_MANAGEMENT_COMMANDS:
        raise ProvisioningError(
            f"Expected {EXPECTED_KQL_MANAGEMENT_COMMANDS} KQL management commands "
            f"before verification, found {len(commands)}"
        )
    # A verification query is never a management command: it is either a
    # placeholder-bearing template, a `let` binding, or a bare table or
    # materialized-view reference at column zero.
    leak_markers = (
        "<SourceFile>",
        "<WorkshopRunId>",
        "\nlet ",
        "\nDonationEvents\n",
        "\nDonationEvents\r\n",
        "\nDonationObservationSummaryForAgent\n",
    )
    invalid = [
        command
        for command in commands
        if any(marker in command for marker in leak_markers)
        or command.lstrip().startswith(("let ", "|"))
    ]
    if invalid:
        raise ProvisioningError(
            "KQL verification queries leaked into management commands."
        )
    return commands


@dataclass(frozen=True)
class ProvisioningNames:
    lakehouse: str
    eventhouse: str
    kql_database: str
    notebook01: str
    pipeline: str
    ontology: str
    data_agent: str
    reflex: str
    agent_ontology: str
    reference_data_agent: str


def build_names(participant_id: str, *, suffix_notebook_name: bool = False) -> ProvisioningNames:
    if not PARTICIPANT_PATTERN.fullmatch(participant_id):
        raise ProvisioningError(
            "PARTICIPANT_ID must be a three-digit value from 001 through 999."
        )
    return ProvisioningNames(
        lakehouse=f"LH_Furusato_{participant_id}",
        eventhouse=f"EH_Furusato_{participant_id}",
        kql_database=f"EH_Furusato_{participant_id}",
        notebook01="Notebook_01_Furusato_Prepare_Ontology_Data" + (
            f"_{participant_id}" if suffix_notebook_name else ""
        ),
        pipeline=f"PL_Furusato_{participant_id}",
        ontology=f"ONT_Furusato_{participant_id}",
        data_agent=f"DA_Furusato_{participant_id}",
        reflex=f"My activator_{participant_id}",
        agent_ontology=f"ONT_Furusato_AIPath_{participant_id}",
        reference_data_agent=f"DA_Furusato_AIReference_{participant_id}",
    )


def resolve_tenant_id(
    runtime_context: Mapping[str, Any],
    fabric_token_provider: Callable[[], str],
) -> str:
    for key in ("currentTenantId", "tenantId"):
        value = str(runtime_context.get(key) or "")
        if GUID_PATTERN.fullmatch(value):
            return value
    token = fabric_token_provider()
    parts = token.split(".")
    if len(parts) != 3:
        raise ProvisioningError("Fabric token is not a JWT and tenantId is unavailable.")
    padded = parts[1] + "=" * (-len(parts[1]) % 4)
    try:
        claims = json.loads(
            base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8")
        )
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProvisioningError("Fabric token tenant claim could not be decoded.") from exc
    tenant_id = str(claims.get("tid") or "")
    if not GUID_PATTERN.fullmatch(tenant_id):
        raise ProvisioningError("Fabric token does not contain a valid tenant claim.")
    return tenant_id


@dataclass
class ProvisioningConfig:
    participant_id: str = "001"
    expected_workspace_name: str = ""
    apply_changes: bool = False
    confirmed_plan_sha256: str = ""
    exclusive_create_window_confirmed: bool = False
    execute_notebook_01: bool = False
    refresh_graph: bool = False
    create_data_agent: bool = False
    create_pipeline: bool = False
    create_reflex: bool = False
    operation_timeout_seconds: int = 900
    poll_interval_seconds: int = 10
    enable_ai_reference_architecture: bool = False
    enable_unified_data_agent: bool = False
    reference_agent_name: str = ""
    reference_agent_role: str = "isolated-reference"
    reference_agent_expected_id: str = ""
    allow_automated_apply: bool = False
    use_participant_notebook_names: bool = False


MIN_POLL_INTERVAL_SECONDS = 1
MAX_POLL_INTERVAL_SECONDS = 120
MIN_OPERATION_TIMEOUT_SECONDS = 60
MAX_OPERATION_TIMEOUT_SECONDS = 7200


def validate_config(config: ProvisioningConfig) -> None:
    if not re.fullmatch(r"\d{3}", str(config.participant_id)):
        raise ProvisioningError(
            "PARTICIPANT_ID must be exactly three digits, for example '004'. "
            f"Received {config.participant_id!r}."
        )
    poll = int(config.poll_interval_seconds)
    if not MIN_POLL_INTERVAL_SECONDS <= poll <= MAX_POLL_INTERVAL_SECONDS:
        raise ProvisioningError(
            "POLL_INTERVAL_SECONDS must be between "
            f"{MIN_POLL_INTERVAL_SECONDS} and {MAX_POLL_INTERVAL_SECONDS}; "
            f"received {poll}."
        )
    timeout = int(config.operation_timeout_seconds)
    if not MIN_OPERATION_TIMEOUT_SECONDS <= timeout <= MAX_OPERATION_TIMEOUT_SECONDS:
        raise ProvisioningError(
            "OPERATION_TIMEOUT_SECONDS must be between "
            f"{MIN_OPERATION_TIMEOUT_SECONDS} and {MAX_OPERATION_TIMEOUT_SECONDS}; "
            f"received {timeout}."
        )
    if timeout < poll:
        raise ProvisioningError(
            "OPERATION_TIMEOUT_SECONDS must not be smaller than POLL_INTERVAL_SECONDS."
        )
    if type(config.enable_ai_reference_architecture) is not bool:
        raise ProvisioningError("ENABLE_AI_REFERENCE_ARCHITECTURE must be Boolean.")
    if type(config.enable_unified_data_agent) is not bool:
        raise ProvisioningError("ENABLE_UNIFIED_DATA_AGENT must be Boolean.")
    if type(config.allow_automated_apply) is not bool:
        raise ProvisioningError("ALLOW_AUTOMATED_APPLY must be Boolean.")
    if type(config.use_participant_notebook_names) is not bool:
        raise ProvisioningError("USE_PARTICIPANT_NOTEBOOK_NAMES must be Boolean.")
    if config.allow_automated_apply and not config.expected_workspace_name.strip():
        raise ProvisioningError("Automated apply requires EXPECTED_WORKSPACE_NAME.")
    reference_agent_target(config, build_names(config.participant_id))


def reference_agent_target(config: ProvisioningConfig, names: ProvisioningNames) -> dict[str, str]:
    if config.enable_unified_data_agent:
        if config.enable_ai_reference_architecture:
            raise ProvisioningError("Unified and isolated AI reference modes are mutually exclusive.")
        if config.reference_agent_name or config.reference_agent_expected_id or config.reference_agent_role != "isolated-reference":
            raise ProvisioningError("Unified mode uses the primary Agent name; reference target overrides are not allowed.")
        return {"name": names.data_agent, "role": "unified", "expectedId": ""}
    if not config.enable_ai_reference_architecture:
        if config.reference_agent_name or config.reference_agent_expected_id or config.reference_agent_role != "isolated-reference":
            raise ProvisioningError("Reference target overrides require ENABLE_AI_REFERENCE_ARCHITECTURE=True.")
        return {"name": names.data_agent, "role": "released", "expectedId": ""}
    target = config.reference_agent_name or names.reference_data_agent
    if target.casefold() == names.data_agent.casefold():
        raise ProvisioningError("Core promotion is not supported by this provisioner; use the separate authorized promotion procedure.")
    if config.reference_agent_role == "isolated-reference":
        if target != names.reference_data_agent or config.reference_agent_expected_id:
            raise ProvisioningError("A custom existing target requires role 'authorized-candidate' and its exact item ID.")
    elif config.reference_agent_role == "authorized-candidate":
        if not config.reference_agent_name or not GUID_PATTERN.fullmatch(config.reference_agent_expected_id):
            raise ProvisioningError("Authorized candidate reuse requires an explicit name and discovered GUID.")
    else:
        raise ProvisioningError("Unknown reference Agent target role.")
    if not target.strip() or target != target.strip() or any(ord(char) < 32 for char in target):
        raise ProvisioningError("Reference Agent target name is invalid.")
    return {"name": target, "role": config.reference_agent_role, "expectedId": config.reference_agent_expected_id}


def load_reference_assets(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Fail before authentication when an enabled reference bundle is incomplete."""
    bundle = payload["bundle"]
    prefix = "ai-reference/"
    required = ("contract.json", "source-metadata.json", "ontology-template.json",
                "global-profile.json", "global-instructions.txt")
    missing = [name for name in required if prefix + name not in bundle]
    if missing:
        raise ProvisioningError(
            "AI reference architecture is incomplete: " + ", ".join(missing)
            + ". Keep ENABLE_AI_REFERENCE_ARCHITECTURE=False until the operator packages "
            "an explicit hash-pinned candidate/accepted reference GLOBAL with reseal_runtime.py."
        )
    contract = json.loads(bundle[prefix + "contract.json"])
    if contract.get("schemaVersion") != "furusato-ai-reference-runtime/v1":
        raise ProvisioningError("Unsupported AI reference bundle contract.")
    expected_modules = ["reference_models", "reference_sql", "reference_kql", "reference_ontology", "reference_agent"]
    expected_sql = [
        "001_create_schema.sql", "010_municipality_static.sql", "020_donation_attributes.sql",
        "030_gift_catalog_suppliers.sql", "040_municipality_by_id.sql", "050_donation_by_id.sql",
        "060_donation_trace_by_id.sql",
    ]
    expected_kql = ["AgentRawObservationTotals", "AgentFileRunSummary", "AgentMunicipalityLeaders"]
    if (
        contract.get("modules") != expected_modules
        or contract.get("sqlDdlOrder") != expected_sql
        or contract.get("kqlFunctions") != expected_kql
        or set(contract.get("sqlObjects", {})) != {
            "MunicipalityStatic", "DonationAttributes", "GiftCatalogSuppliers",
            "MunicipalityById", "DonationById", "DonationTraceById",
        }
        or contract.get("selectedSqlObjects") != {
            "MunicipalityStatic": "View", "MunicipalityById": "Function", "DonationTraceById": "Function",
        }
    ):
        raise ProvisioningError("AI reference module/SQL/KQL inventory is incomplete or changed.")
    expected_files = {
        prefix + "source-metadata.json", prefix + "ontology-template.json",
        *(prefix + f"modules/{name}.py" for name in expected_modules),
        *(prefix + "sql/" + name for name in expected_sql),
        *(prefix + f"kql/{name}.kql" for name in expected_kql),
    }
    if set(contract.get("files", {})) != expected_files:
        raise ProvisioningError("AI reference asset hash inventory is incomplete or unexpected.")
    for path, expected in contract["files"].items():
        if path not in bundle or sha256_bytes(bundle[path].encode("utf-8")) != expected:
            raise ProvisioningError(f"AI reference asset digest mismatch: {path}")
    profile = json.loads(bundle[prefix + "global-profile.json"])
    instructions = bundle[prefix + "global-instructions.txt"]
    if (
        profile.get("schemaVersion") != "furusato-reference-global/v1"
        or profile.get("status") not in {"candidate", "accepted"}
        or profile.get("sha256") != sha256_bytes(instructions.encode("utf-8"))
        or not instructions.strip() or len(instructions) > 15_000 or "\r" in instructions
        or instructions.startswith("\ufeff")
    ):
        raise ProvisioningError("Reference GLOBAL requires exact UTF-8/LF bytes, a matching hash and explicit candidate/accepted status.")
    config = json.loads(bundle["data-agent/Files/Config/published/stage_config.json"])
    config["aiInstructions"] = instructions
    return {
        "contract": contract, "globalProfile": profile, "stageConfig": config,
        "sources": json.loads(bundle[prefix + "source-metadata.json"]),
        "ontologyTemplate": json.loads(bundle[prefix + "ontology-template.json"]),
        "sqlDdl": tuple((name, bundle[prefix + "sql/" + name]) for name in contract["sqlDdlOrder"]),
        "kqlFunctions": {name: bundle[prefix + f"kql/{name}.kql"] for name in contract["kqlFunctions"]},
        "moduleSources": {name: bundle[prefix + f"modules/{name}.py"] for name in contract["modules"]},
    }


def load_reference_modules(assets: Mapping[str, Any]) -> dict[str, Any]:
    """Load sealed standard Python modules in an isolated, content-addressed package."""
    package_name = "_furusato_reference_" + sha256_json(assets["moduleSources"])[:16]
    if package_name not in sys.modules:
        package = types.ModuleType(package_name)
        package.__path__ = []
        sys.modules[package_name] = package
    result = {}
    for name, source in assets["moduleSources"].items():
        full_name = package_name + "." + name
        module = sys.modules.get(full_name)
        if module is None:
            module = types.ModuleType(full_name)
            module.__package__ = package_name
            module.__file__ = str(Path.cwd() / "_furusato_runtime" / "modules" / f"{name}.py")
            sys.modules[full_name] = module
            try:
                exec(compile(source, module.__file__, "exec"), module.__dict__)
            except BaseException:
                del sys.modules[full_name]
                raise
        result[name] = module
    return result


def load_unified_assets(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Read a sealed one-Agent profile; never substitute the isolated AIPath profile."""
    base = load_reference_assets(payload)
    bundle = payload["bundle"]
    prefix = "unified-agent/"
    if prefix + "contract.json" not in bundle:
        raise ProvisioningError("Unified Agent assets are not packaged; keep ENABLE_UNIFIED_DATA_AGENT=False.")
    contract = json.loads(bundle[prefix + "contract.json"])
    if (
        contract.get("schemaVersion") != "furusato-unified-agent-runtime/v1"
        or contract.get("teachingOntologyShape") != [10, 72, 1, 15]
        or contract.get("referenceContractSha256") != sha256_bytes(bundle["ai-reference/contract.json"].encode("utf-8"))
    ):
        raise ProvisioningError("Unified profile lineage or teaching Ontology contract differs.")
    hashes = contract.get("files", {})
    if not isinstance(hashes, dict) or prefix + "profile.json" not in hashes:
        raise ProvisioningError("Unified profile hash inventory is missing.")
    actual_paths = {path for path in bundle if path.startswith(prefix) and path != prefix + "contract.json"}
    if set(hashes) != actual_paths:
        raise ProvisioningError("Unified profile contains missing or unexpected assets.")
    for path, expected in hashes.items():
        if sha256_bytes(bundle[path].encode("utf-8")) != expected:
            raise ProvisioningError(f"Unified asset digest mismatch: {path}")
    core_path = contract.get("coreOntologySourcePath")
    if not isinstance(core_path, str) or not core_path.startswith("data-agent/Files/Config/published/"):
        raise ProvisioningError("Unified profile lacks its canonical teaching Ontology source.")
    if core_path not in bundle or sha256_bytes(bundle[core_path].encode("utf-8")) != contract.get("coreOntologySourceSha256"):
        raise ProvisioningError("Unified profile's teaching source changed after packaging.")
    profile = json.loads(bundle[prefix + "profile.json"])
    if set(profile) != {"stageConfig", "sources", "globalProfile", "publicationDescription"}:
        raise ProvisioningError("Unified runtime profile has unexpected fields.")
    stage = profile["stageConfig"]
    instructions = stage.get("aiInstructions", "")
    if (not isinstance(instructions, str) or not instructions.strip() or len(instructions) > 15000
            or "\r" in instructions or instructions.startswith("\ufeff")
            or stage.get("experimental", {}).get("enableExperimentalFeatures") is not True
            or stage.get("experimental", {}).get("codeInterpreterEnabled") is not True):
        raise ProvisioningError("Unified GLOBAL/Preview/Code Interpreter contract is invalid.")
    if set(profile["sources"]) != {"lakehouse_tables", "kusto", "ontology"}:
        raise ProvisioningError("Unified mode requires exactly three source kinds.")
    ontology = profile["sources"]["ontology"]
    if ontology.get("instructions") is not None or len(ontology.get("elements", [])) != 10:
        raise ProvisioningError("Unified mode must retain the ten teaching Ontology entities.")
    if profile["globalProfile"].get("sha256") != sha256_bytes(instructions.encode("utf-8")):
        raise ProvisioningError("Unified GLOBAL fingerprint is invalid.")
    return {**base, **profile, "unifiedContract": contract}


@dataclass
class PlanEntry:
    key: str
    item_type: str
    display_name: str
    desired_digest: str | None
    current_status: str
    current_id: str | None = None


@dataclass
class ProvisioningPlan:
    workspace_name: str
    folder_id: str
    participant_id: str
    names: ProvisioningNames
    payload_sha256: str
    entries: list[PlanEntry]
    flags: dict[str, bool]
    blockers: list[str] = field(default_factory=list)
    reference_target: dict[str, str] | None = None

    @property
    def sha256(self) -> str:
        document = asdict(self)
        document.pop("blockers", None)
        for entry in document["entries"]:
            entry.pop("current_id", None)
            entry.pop("current_status", None)
        return sha256_json(document)


@dataclass(frozen=True)
class JobMonitor:
    kind: str
    identifier: str


class WorkshopFabricClient:
    """Fabric/Kusto REST client with bounded safe retries and LRO support."""

    def __init__(
        self,
        fabric_token_provider: Callable[[], str],
        kusto_token_provider: Callable[[], str],
        *,
        session: requests.Session | None = None,
        sleeper: Callable[[float], None] = time.sleep,
        clock: Callable[[], datetime] = utc_now,
        timeout_seconds: int = 900,
        poll_interval_seconds: int = 10,
    ) -> None:
        self.fabric_token_provider = fabric_token_provider
        self.kusto_token_provider = kusto_token_provider
        self.session = session or requests.Session()
        self.sleeper = sleeper
        self.clock = clock
        self.timeout_seconds = timeout_seconds
        self.poll_interval_seconds = poll_interval_seconds

    def _request(
        self,
        method: str,
        url: str,
        *,
        audience: str = "fabric",
        json_body: Any | None = None,
        expected: Iterable[int] = (200,),
        safe_retry: bool | None = None,
    ) -> requests.Response:
        method = method.upper()
        safe = method in {"GET", "HEAD"} if safe_retry is None else safe_retry
        attempts = 4 if safe else 1
        last_error: Exception | None = None
        for attempt in range(attempts):
            token = (
                self.fabric_token_provider()
                if audience == "fabric"
                else self.kusto_token_provider()
            )
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            }
            try:
                response = self.session.request(
                    method,
                    url,
                    headers=headers,
                    json=json_body,
                    timeout=60,
                )
            except requests.RequestException as exc:
                last_error = exc
                if not safe:
                    raise AmbiguousOutcomeError(
                        f"{method} {_describe_endpoint(url)} outcome is ambiguous; "
                        "inspect state before retrying."
                    ) from exc
                if attempt + 1 == attempts:
                    raise ProvisioningError(
                        f"{method} {_describe_endpoint(url)} failed: "
                        f"{sanitize_error(exc)}"
                    ) from exc
                self.sleeper(min(2**attempt, 10))
                continue
            if response.status_code in expected:
                return response
            if safe and response.status_code in {401, 408, 429, 500, 502, 503, 504}:
                if attempt + 1 < attempts:
                    self.sleeper(
                        _retry_delay_seconds(
                            response.headers.get("Retry-After"),
                            attempt,
                        )
                    )
                    continue
            message = sanitize_error(response.text)
            raise ProvisioningError(
                f"{method} {_describe_endpoint(url)} failed with HTTP "
                f"{response.status_code}: {message}"
            )
        raise ProvisioningError(
            f"{method} {_describe_endpoint(url)} failed: "
            f"{sanitize_error(last_error or 'request failed')}"
        )

    def _paged(self, url: str) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        next_url: str | None = url
        visited: set[str] = set()
        while next_url:
            if next_url in visited:
                raise ProvisioningError(
                    "Fabric paging repeated a continuation page and was stopped."
                )
            visited.add(next_url)
            if len(visited) > MAX_PAGE_REQUESTS:
                raise ProvisioningError(
                    f"Fabric paging exceeded {MAX_PAGE_REQUESTS} pages."
                )
            payload = self._request("GET", next_url).json()
            result.extend(payload.get("value", []))
            continuation_uri = payload.get("continuationUri")
            token = payload.get("continuationToken")
            if continuation_uri:
                next_url = continuation_uri
            elif token:
                separator = "&" if "?" in url else "?"
                next_url = f"{url}{separator}continuationToken={urllib.parse.quote(token)}"
            else:
                next_url = None
        return result

    def list_items(
        self,
        workspace_id: str,
        *,
        folder_id: str | None = None,
        recursive: bool = False,
    ) -> list[dict[str, Any]]:
        url = f"{FABRIC_API}/workspaces/{workspace_id}/items"
        if folder_id:
            query = urllib.parse.urlencode(
                {
                    "rootFolderId": folder_id,
                    "recursive": str(recursive).lower(),
                }
            )
            url = f"{url}?{query}"
        return self._paged(url)

    def find_unique_item(
        self,
        workspace_id: str,
        item_type: str,
        display_name: str,
        *,
        folder_id: str | None = None,
    ) -> dict[str, Any] | None:
        matches = [
            item
            for item in self.list_items(workspace_id, folder_id=folder_id)
            if str(item.get("type", "")).casefold() == item_type.casefold()
            and item.get("displayName") == display_name
        ]
        if len(matches) > 1:
            raise ConflictError(
                f"Multiple {item_type} items have display name {display_name!r}."
            )
        return matches[0] if matches else None

    def wait_for_unique_item(
        self,
        workspace_id: str,
        item_type: str,
        display_name: str,
        *,
        folder_id: str | None = None,
    ) -> dict[str, Any]:
        deadline = self.clock() + timedelta(seconds=self.timeout_seconds)
        while self.clock() < deadline:
            item = self.find_unique_item(
                workspace_id,
                item_type,
                display_name,
                folder_id=folder_id,
            )
            if item:
                return item
            self.sleeper(self.poll_interval_seconds)
        raise OperationTimeoutError(
            f"Created {item_type} {display_name!r} was not visible in time."
        )

    def get_item(self, workspace_id: str, item_id: str) -> dict[str, Any]:
        return self._request(
            "GET", f"{FABRIC_API}/workspaces/{workspace_id}/items/{item_id}"
        ).json()

    def require_item_in_folder(
        self,
        workspace_id: str,
        item: Mapping[str, Any],
        *,
        folder_id: str,
        item_type: str,
        display_name: str,
    ) -> dict[str, Any]:
        details = (
            dict(item)
            if item.get("folderId")
            else self.get_item(workspace_id, str(item["id"]))
        )
        if str(details.get("folderId") or "") != folder_id:
            raise ConflictError(
                f"Existing {item_type} {display_name!r} is outside the target Folder."
            )
        return details

    def get_kql_database(
        self,
        workspace_id: str,
        item_id: str,
    ) -> dict[str, Any]:
        return self._request(
            "GET",
            f"{FABRIC_API}/workspaces/{workspace_id}/kqlDatabases/{item_id}",
        ).json()

    def get_lakehouse(
        self,
        workspace_id: str,
        item_id: str,
    ) -> dict[str, Any]:
        return self._request(
            "GET",
            f"{FABRIC_API}/workspaces/{workspace_id}/lakehouses/{item_id}",
        ).json()

    def wait_for_item_property(
        self,
        workspace_id: str,
        item_id: str,
        property_name: str,
    ) -> tuple[dict[str, Any], Any]:
        deadline = self.clock() + timedelta(seconds=self.timeout_seconds)
        while self.clock() < deadline:
            item = self.get_item(workspace_id, item_id)
            value = item.get("properties", {}).get(property_name)
            if value:
                return item, value
            self.sleeper(self.poll_interval_seconds)
        raise OperationTimeoutError(
            f"Item property {property_name!r} was not provisioned in time."
        )

    def wait_for_kql_database_property(
        self,
        workspace_id: str,
        item_id: str,
        property_name: str,
    ) -> tuple[dict[str, Any], Any]:
        deadline = self.clock() + timedelta(seconds=self.timeout_seconds)
        while self.clock() < deadline:
            try:
                item = self.get_kql_database(workspace_id, item_id)
            except ProvisioningError as exc:
                if not _is_http_status_error(exc, 404):
                    raise
                self.sleeper(self.poll_interval_seconds)
                continue
            value = item.get("properties", {}).get(property_name)
            if value:
                return item, value
            self.sleeper(self.poll_interval_seconds)
        raise OperationTimeoutError(
            f"KQL Database property {property_name!r} was not provisioned in time."
        )

    def wait_for_lakehouse_property(
        self,
        workspace_id: str,
        item_id: str,
        property_name: str,
    ) -> tuple[dict[str, Any], Any]:
        deadline = self.clock() + timedelta(seconds=self.timeout_seconds)
        while self.clock() < deadline:
            try:
                item = self.get_lakehouse(workspace_id, item_id)
            except ProvisioningError as exc:
                if not _is_http_status_error(exc, 404):
                    raise
                self.sleeper(self.poll_interval_seconds)
                continue
            value = item.get("properties", {}).get(property_name)
            if value:
                return item, value
            self.sleeper(self.poll_interval_seconds)
        raise OperationTimeoutError(
            f"Lakehouse property {property_name!r} was not provisioned in time."
        )

    def check_active_capacity(self, workspace_id: str) -> dict[str, Any]:
        workspace = self._request(
            "GET", f"{FABRIC_API}/workspaces/{workspace_id}"
        ).json()
        capacity_id = workspace.get("capacityId")
        if not capacity_id:
            raise ProvisioningError(
                "Current workspace has no assigned capacity; the Notebook cannot assign itself."
            )
        try:
            capacity = self._request(
                "GET", f"{FABRIC_API}/capacities/{capacity_id}"
            ).json()
        except ProvisioningError:
            return {
                "id": capacity_id,
                "state": "Unknown",
                "note": (
                    "Capacity state could not be read; the workspace has an assigned "
                    "capacity so provisioning continues."
                ),
            }
        if str(capacity.get("state", "")).casefold() != "active":
            raise ProvisioningError("Current workspace capacity is not active.")
        return capacity

    def poll_operation(self, operation_id: str) -> dict[str, Any]:
        deadline = self.clock() + timedelta(seconds=self.timeout_seconds)
        while self.clock() < deadline:
            try:
                payload = self._request(
                    "GET", f"{FABRIC_API}/operations/{operation_id}"
                ).json()
            except ProvisioningError as exc:
                if not _is_http_status_error(exc, 404):
                    raise
                self.sleeper(self.poll_interval_seconds)
                continue
            status = str(payload.get("status", "")).casefold()
            if status == "succeeded":
                return payload
            if status in {"failed", "cancelled"}:
                raise OperationFailedError(
                    f"Fabric operation {status}: {sanitize_error(payload.get('error', ''))}"
                )
            self.sleeper(self.poll_interval_seconds)
        raise OperationTimeoutError("Fabric operation timed out.")

    @staticmethod
    def _operation_id(response: requests.Response) -> str:
        operation_id = response.headers.get("x-ms-operation-id")
        if operation_id:
            return operation_id
        location = response.headers.get("Location", "")
        match = re.search(r"/operations/([^/?]+)", location)
        if match:
            return match.group(1)
        raise ProvisioningError("202 response did not include an operation identifier.")

    def create_item(
        self,
        workspace_id: str,
        body: Mapping[str, Any],
    ) -> dict[str, Any] | None:
        response = self._request(
            "POST",
            f"{FABRIC_API}/workspaces/{workspace_id}/items",
            json_body=body,
            expected=(200, 201, 202),
            safe_retry=False,
        )
        if response.status_code == 202:
            self.poll_operation(self._operation_id(response))
            return None
        return response.json() if response.content else None

    def get_definition(
        self,
        workspace_id: str,
        item_id: str,
        *,
        format_name: str | None = None,
    ) -> dict[str, Any]:
        format_query = (
            f"?format={urllib.parse.quote(format_name, safe='')}"
            if format_name
            else ""
        )
        response = self._request(
            "POST",
            (
                f"{FABRIC_API}/workspaces/{workspace_id}/items/{item_id}/"
                f"getDefinition{format_query}"
            ),
            json_body={},
            expected=(200, 202),
            safe_retry=True,
        )
        if response.status_code == 200:
            payload = response.json()
        else:
            operation_id = self._operation_id(response)
            self.poll_operation(operation_id)
            payload = self._request(
                "GET", f"{FABRIC_API}/operations/{operation_id}/result"
            ).json()
        return payload.get("definition", payload)

    def wait_for_definition_match(
        self,
        workspace_id: str,
        item_id: str,
        definition: Mapping[str, Any],
    ) -> dict[str, Any]:
        format_name = str(definition.get("format") or "") or None
        deadline = self.clock() + timedelta(seconds=self.timeout_seconds)
        while self.clock() < deadline:
            try:
                current = self.get_definition(
                    workspace_id,
                    item_id,
                    format_name=format_name,
                )
                if definitions_equal(current, definition):
                    return current
            except ProvisioningError as exc:
                if not _is_http_status_error(exc, 404):
                    raise
            self.sleeper(self.poll_interval_seconds)
        raise OperationTimeoutError(
            "Created item definition did not become the exact desired definition in time."
        )

    def ensure_definition_item(
        self,
        workspace_id: str,
        *,
        item_type: str,
        display_name: str,
        folder_id: str,
        definition: Mapping[str, Any],
        description: str = "",
    ) -> tuple[dict[str, Any], str]:
        existing = self.find_unique_item(
            workspace_id,
            item_type,
            display_name,
            folder_id=folder_id,
        )
        if existing:
            self.require_item_in_folder(
                workspace_id,
                existing,
                folder_id=folder_id,
                item_type=item_type,
                display_name=display_name,
            )
            current = self.get_definition(
                workspace_id,
                str(existing["id"]),
                format_name=str(definition.get("format") or "") or None,
            )
            if not definitions_equal(current, definition):
                raise ConflictError(
                    f"Existing {item_type} {display_name!r} differs from desired definition."
                )
            return existing, "REUSED"
        body: dict[str, Any] = {
            "displayName": display_name,
            "type": item_type,
            "folderId": folder_id,
            "definition": definition,
        }
        if description:
            body["description"] = description
        created = self.create_item(workspace_id, body)
        item = created or self.wait_for_unique_item(
            workspace_id,
            item_type,
            display_name,
            folder_id=folder_id,
        )
        self.require_item_in_folder(
            workspace_id,
            item,
            folder_id=folder_id,
            item_type=item_type,
            display_name=display_name,
        )
        self.wait_for_definition_match(
            workspace_id, str(item["id"]), definition
        )
        return item, "CREATED"

    def ensure_simple_item(
        self,
        workspace_id: str,
        *,
        item_type: str,
        display_name: str,
        folder_id: str,
        creation_payload: Mapping[str, Any] | None = None,
    ) -> tuple[dict[str, Any], str]:
        existing = self.find_unique_item(
            workspace_id,
            item_type,
            display_name,
            folder_id=folder_id,
        )
        if existing:
            self.require_item_in_folder(
                workspace_id,
                existing,
                folder_id=folder_id,
                item_type=item_type,
                display_name=display_name,
            )
            return existing, "REUSED"
        body: dict[str, Any] = {
            "displayName": display_name,
            "type": item_type,
            "folderId": folder_id,
        }
        if creation_payload:
            body["creationPayload"] = dict(creation_payload)
        created = self.create_item(workspace_id, body)
        item = created or self.wait_for_unique_item(
            workspace_id,
            item_type,
            display_name,
            folder_id=folder_id,
        )
        self.require_item_in_folder(
            workspace_id,
            item,
            folder_id=folder_id,
            item_type=item_type,
            display_name=display_name,
        )
        return item, "CREATED"

    def recent_jobs(
        self,
        workspace_id: str,
        item_id: str,
        job_type: str,
        *,
        minutes: int = 5,
    ) -> list[dict[str, Any]]:
        url = f"{FABRIC_API}/workspaces/{workspace_id}/items/{item_id}/jobs/instances"
        jobs = self._paged(url)
        cutoff = self.clock() - timedelta(minutes=minutes)
        result = []
        for job in jobs:
            if str(job.get("jobType") or "").casefold() != job_type.casefold():
                continue
            raw = (
                job.get("startTimeUtc")
                or job.get("createdDateTime")
                or job.get("startTime")
            )
            if not raw:
                continue
            started = parse_iso_datetime(raw)
            status = str(job.get("status") or "").casefold()
            if started >= cutoff or status in {
                "notstarted",
                "queued",
                "running",
                "inprogress",
            }:
                result.append(job)
        return sorted(result, key=lambda item: str(item.get("startTimeUtc", "")), reverse=True)

    def wait_for_recent_job(
        self,
        workspace_id: str,
        item_id: str,
        job_type: str,
    ) -> dict[str, Any]:
        deadline = self.clock() + timedelta(seconds=self.timeout_seconds)
        while self.clock() < deadline:
            recent = self.recent_jobs(
                workspace_id,
                item_id,
                job_type,
                minutes=max(5, (self.timeout_seconds // 60) + 2),
            )
            if recent:
                return recent[0]
            self.sleeper(self.poll_interval_seconds)
        raise OperationTimeoutError(
            f"Submitted {job_type} job did not expose an instance in time."
        )

    def start_job(
        self,
        workspace_id: str,
        item_id: str,
        job_type: str,
        *,
        body: Mapping[str, Any] | None = None,
    ) -> JobMonitor:
        response = self._request(
            "POST",
            (
                f"{FABRIC_API}/workspaces/{workspace_id}/items/{item_id}"
                f"/jobs/{urllib.parse.quote(job_type, safe='')}/instances"
            ),
            json_body=body or {},
            expected=(202,),
            safe_retry=False,
        )
        location = response.headers.get("Location", "")
        match = re.search(r"/instances/([^/?]+)", location)
        if match:
            return JobMonitor("instance", match.group(1))
        operation = response.headers.get("x-ms-operation-id")
        if operation:
            return JobMonitor("operation", operation)
        raise AmbiguousOutcomeError(
            "Job submission returned no monitor identifier; inspect recent jobs before retrying."
        )

    def poll_job(
        self,
        workspace_id: str,
        item_id: str,
        job_id: str,
    ) -> dict[str, Any]:
        deadline = self.clock() + timedelta(seconds=self.timeout_seconds)
        url = (
            f"{FABRIC_API}/workspaces/{workspace_id}/items/{item_id}"
            f"/jobs/instances/{job_id}"
        )
        while self.clock() < deadline:
            try:
                job = self._request("GET", url).json()
            except ProvisioningError as exc:
                if not _is_http_status_error(exc, 404):
                    raise
                self.sleeper(self.poll_interval_seconds)
                continue
            status = str(job.get("status", "")).casefold()
            if status in {"completed", "succeeded"}:
                return job
            if status in {"failed", "cancelled", "canceled", "deduped"}:
                raise OperationFailedError(
                    f"Job {status}: {sanitize_error(job.get('failureReason', ''))}"
                )
            self.sleeper(self.poll_interval_seconds)
        raise OperationTimeoutError("Fabric job timed out.")

    def run_or_reuse_recent_job(
        self,
        workspace_id: str,
        item_id: str,
        job_type: str,
        *,
        body: Mapping[str, Any] | None = None,
    ) -> tuple[dict[str, Any], str]:
        recent = self.recent_jobs(
            workspace_id,
            item_id,
            job_type,
            minutes=max(5, (self.timeout_seconds // 60) + 2),
        )
        if recent:
            candidate = recent[0]
            job_id = str(candidate.get("id") or candidate.get("jobInstanceId"))
            if not job_id:
                raise ProvisioningError("Recent job lacks an instance ID.")
            return self.poll_job(workspace_id, item_id, job_id), "RECENT_REUSED"
        monitor = self.start_job(workspace_id, item_id, job_type, body=body)
        if monitor.kind == "instance":
            return (
                self.poll_job(
                    workspace_id,
                    item_id,
                    monitor.identifier,
                ),
                "STARTED",
            )
        self.poll_operation(monitor.identifier)
        candidate = self.wait_for_recent_job(workspace_id, item_id, job_type)
        job_id = str(candidate.get("id") or candidate.get("jobInstanceId") or "")
        if not job_id:
            raise ProvisioningError("Submitted job lacks an instance ID.")
        return self.poll_job(workspace_id, item_id, job_id), "STARTED"

    def wait_for_graph_compilation(
        self,
        workspace_id: str,
        graph_model_id: str,
        *,
        expected_counts: Mapping[str, int] | None = None,
    ) -> dict[str, int]:
        expected = dict(expected_counts) if expected_counts is not None else {
            "nodeTypes": 10, "edgeTypes": 15, "dataSources": 11,
            "nodeTables": 10, "edgeTables": 15,
        }
        deadline = self.clock() + timedelta(seconds=self.timeout_seconds)
        counts: dict[str, int] = {}
        while self.clock() < deadline:
            parts = decode_definition_parts(self.get_definition(workspace_id, graph_model_id))
            documents = {
                path: json.loads(parts.get(path, b"{}"))
                for path in ("graphType.json", "dataSources.json", "graphDefinition.json")
            }
            counts = {
                "nodeTypes": len(documents["graphType.json"].get("nodeTypes", [])),
                "edgeTypes": len(documents["graphType.json"].get("edgeTypes", [])),
                "dataSources": len(documents["dataSources.json"].get("dataSources", [])),
                "nodeTables": len(documents["graphDefinition.json"].get("nodeTables", [])),
                "edgeTables": len(documents["graphDefinition.json"].get("edgeTables", [])),
            }
            if counts == expected:
                return counts
            self.sleeper(self.poll_interval_seconds)
        raise OperationTimeoutError(
            "Ontology graph compilation did not produce the complete model; "
            f"expected={expected}; actual={counts}. No refresh was submitted."
        )

    def run_or_reuse_graph_refresh(
        self,
        workspace_id: str,
        graph_model_id: str,
        *,
        expected_counts: Mapping[str, int] | None = None,
    ) -> tuple[dict[str, Any], str]:
        if expected_counts is None:
            self.wait_for_graph_compilation(workspace_id, graph_model_id)
        else:
            self.wait_for_graph_compilation(workspace_id, graph_model_id, expected_counts=expected_counts)
        # Ontology compilation can start an automatic refresh. Allow its
        # job record to propagate instead of racing it with a second run.
        registration_deadline = self.clock() + timedelta(seconds=min(60, self.timeout_seconds))
        recent = self.recent_jobs(
            workspace_id,
            graph_model_id,
            "Refresh",
            minutes=max(5, (self.timeout_seconds // 60) + 2),
        )
        while self.clock() < registration_deadline and (
            not recent or str(recent[0].get("status", "")).casefold() in {"failed", "cancelled", "canceled"}
        ):
            self.sleeper(self.poll_interval_seconds)
            recent = self.recent_jobs(
                workspace_id, graph_model_id, "Refresh",
                minutes=max(5, (self.timeout_seconds // 60) + 2),
            )
        active = [
            job for job in recent
            if str(job.get("status", "")).casefold() in {"notstarted", "queued", "running", "inprogress"}
        ]
        if active:
            recent = active
        elif recent and (
            str(recent[0].get("status", "")).casefold() == "failed"
            and (recent[0].get("failureReason") or {}).get("errorCode") == "GraphNotRefreshable"
        ):
            # The complete definition was proved above. This specific failure
            # is an automatic refresh that raced initial graph compilation.
            recent = []
        if recent:
            job_id = str(
                recent[0].get("id") or recent[0].get("jobInstanceId") or ""
            )
            if not job_id:
                raise ProvisioningError("Recent Graph refresh lacks a job ID.")
            return self.poll_job(workspace_id, graph_model_id, job_id), "RECENT_REUSED"
        response = self._request(
            "POST",
            (
                f"{FABRIC_API}/workspaces/{workspace_id}/graphModels/"
                f"{graph_model_id}/jobs/refreshGraph/instances"
            ),
            json_body={},
            expected=(200, 202),
            safe_retry=False,
        )
        location = response.headers.get("Location", "")
        match = re.search(r"/instances/([^/?]+)", location)
        if match:
            return (
                self.poll_job(
                    workspace_id,
                    graph_model_id,
                    match.group(1),
                ),
                "STARTED",
            )
        operation_id = response.headers.get("x-ms-operation-id")
        if operation_id:
            return self.poll_operation(operation_id), "STARTED"
        if response.status_code == 200:
            # A synchronous 200 carries no monitor identifier, so the refresh is
            # only provably finished once a terminal job or an explicit terminal
            # status confirms it. Never checkpoint on an unverified 200.
            follow_up = self.recent_jobs(
                workspace_id,
                graph_model_id,
                "Refresh",
                minutes=max(5, (self.timeout_seconds // 60) + 2),
            )
            if follow_up:
                job_id = str(
                    follow_up[0].get("id")
                    or follow_up[0].get("jobInstanceId")
                    or ""
                )
                if job_id:
                    return (
                        self.poll_job(workspace_id, graph_model_id, job_id),
                        "STARTED",
                    )
            body = response.json() if response.content else {}
            status = str(
                (body or {}).get("status") or (body or {}).get("state") or ""
            ).casefold()
            if status in {"failed", "cancelled", "canceled", "deduped"}:
                raise ProvisioningError(
                    f"Graph refresh reported a terminal status of {status!r}."
                )
            if status in {"completed", "succeeded"}:
                return body, "COMPLETED_SYNCHRONOUSLY"
            try:
                candidate = self.wait_for_recent_job(workspace_id, graph_model_id, "Refresh")
            except OperationTimeoutError as exc:
                raise AmbiguousOutcomeError(
                    "Graph refresh returned HTTP 200 without a terminal status "
                    "or monitor identifier, and no job appeared before the bounded "
                    "registration timeout. Inspect history before any retry."
                ) from exc
            job_id = str(candidate.get("id") or candidate.get("jobInstanceId") or "")
            if not job_id:
                raise ProvisioningError("Submitted Graph refresh lacks a job ID.")
            return self.poll_job(workspace_id, graph_model_id, job_id), "STARTED"
        raise ProvisioningError("Graph refresh did not return a monitor identifier.")

    def execute_kusto(
        self,
        query_service_uri: str,
        database_name: str,
        csl: str,
        *,
        management: bool,
    ) -> dict[str, Any]:
        endpoint = "/v1/rest/mgmt" if management else "/v1/rest/query"
        response = self._request(
            "POST",
            query_service_uri.rstrip("/") + endpoint,
            audience="kusto",
            json_body={"db": database_name, "csl": csl},
            expected=(200,),
            safe_retry=False,
        )
        return response.json()


def bind_notebook_to_lakehouse(
    notebook: Mapping[str, Any],
    workspace_id: str,
    lakehouse_id: str,
    lakehouse_name: str,
    *,
    participant_id: str | None = None,
) -> dict[str, Any]:
    result = copy.deepcopy(notebook)
    if participant_id is not None:
        build_names(participant_id)
        parameter_cells = [
            cell for cell in result.get("cells", [])
            if "parameters" in cell.get("metadata", {}).get("tags", [])
        ]
        if len(parameter_cells) != 1:
            raise ProvisioningError("Notebook 01 must have exactly one parameter cell.")
        parameter_cell = parameter_cells[0]
        source = parameter_cell.get("source", [])
        text = "".join(source) if isinstance(source, list) else source
        text, replacements = re.subn(
            r"(?m)^PARTICIPANT_ID\s*=\s*[^\n]*$",
            f"PARTICIPANT_ID = {json.dumps(participant_id)}",
            text,
        )
        if replacements != 1:
            raise ProvisioningError("Notebook 01 PARTICIPANT_ID assignment is ambiguous.")
        parameter_cell["source"] = text.splitlines(keepends=True)
    metadata = result.setdefault("metadata", {})
    dependencies = metadata.setdefault("dependencies", {})
    dependencies["lakehouse"] = {
        "default_lakehouse": lakehouse_id,
        "default_lakehouse_name": lakehouse_name,
        "default_lakehouse_workspace_id": workspace_id,
        "known_lakehouses": [{"id": lakehouse_id}],
    }
    for cell in result.get("cells", []):
        cell.setdefault("metadata", {})
        if cell.get("cell_type") == "code":
            cell.setdefault("execution_count", None)
            cell.setdefault("outputs", [])
            source = cell.get("source", [])
            if isinstance(source, list):
                cell["source"] = [
                    line if index == len(source) - 1 or line.endswith("\n") else line + "\n"
                    for index, line in enumerate(source)
                ]
    return result


def dataset_target_relative_path(relative_path: str, participant_id: str) -> str:
    """Keep watched increments absent until the FileCreated trigger is running."""
    build_names(participant_id)
    if relative_path.startswith("seed/"):
        return relative_path.replace("seed/", "furusato/seed/", 1)
    if relative_path.startswith("increment/"):
        return f"_provisioning/furusato/{participant_id}/{relative_path}"
    raise ProvisioningError(f"Unexpected dataset path {relative_path!r}.")


def bundle_definition(
    bundle: Mapping[str, str],
    prefix: str,
    bindings: Mapping[str, str],
    *,
    format_name: str | None = None,
) -> dict[str, Any]:
    parts = []
    normalized_prefix = prefix.rstrip("/") + "/"
    for bundle_path, text in sorted(bundle.items()):
        if not bundle_path.startswith(normalized_prefix):
            continue
        relative = bundle_path[len(normalized_prefix):]
        document = render_placeholders(json.loads(text), bindings)
        rendered_path = render_placeholders(relative, bindings)
        parts.append(encode_part(rendered_path, document))
    if not parts:
        raise ProvisioningError(f"Bundle prefix contains no definition files: {prefix}")
    definition: dict[str, Any] = {"parts": parts}
    if format_name:
        definition["format"] = format_name
    return definition


def verify_reflex_fail_closed(definition: Mapping[str, Any]) -> None:
    documents = [
        json.loads(content.decode("utf-8"))
        for content in decode_definition_parts(definition).values()
    ]
    serialized = json.dumps(documents, ensure_ascii=False)
    # The only shipped Reflex rule is the OneLake FileCreated trigger that
    # starts the Data Pipeline. No external notification target may exist.
    for forbidden in ("EmailMessage", "TeamsMessage", "sentTo", "copyTo", "bCCTo"):
        if forbidden in serialized:
            raise ProvisioningError(
                f"Reflex contains an external notification binding: {forbidden}"
            )
    for required in (
        "Microsoft.Fabric.OneLake.FileCreated",
        "FabricItemInvocation",
        "fabricItemAction-v1",
    ):
        if required not in serialized:
            raise ProvisioningError(
                f"Reflex does not prove the OneLake FileCreated pipeline trigger: {required}"
            )
    found_disabled_rule = False

    def visit(node: Any) -> None:
        nonlocal found_disabled_rule
        if isinstance(node, dict):
            for key, value in node.items():
                if key in {"enabled", "shouldRun"} and value is True:
                    raise ProvisioningError(
                        f"Reflex contains an enabled {key} flag."
                    )
                if key == "shouldRun" and value is False:
                    found_disabled_rule = True
                if key == "state" and isinstance(value, str):
                    if value.casefold() not in {"disabled", "off"}:
                        raise ProvisioningError(
                            f"Reflex contains non-disabled state {value!r}."
                        )
                visit(value)
        elif isinstance(node, list):
            for value in node:
                visit(value)
        elif isinstance(node, str) and node.lstrip().startswith(("{", "[")):
            try:
                embedded = json.loads(node)
            except json.JSONDecodeError:
                return
            visit(embedded)

    for document in documents:
        visit(document)
    if not found_disabled_rule:
        raise ProvisioningError("Reflex definition does not prove disabled rules.")


def decode_embedded_dataset(payload: Mapping[str, Any]) -> dict[str, bytes]:
    manifest = payload["datasetManifest"]
    encoded_files = payload["datasetGzipBase64"]
    files: dict[str, bytes] = {}
    manifest_entries = {
        **{
            f"seed/{entry['file']}": entry
            for entry in manifest["files"]
        },
        **{
            f"increment/{entry['file']}": entry
            for entry in manifest["incrementFiles"]
        },
    }
    if set(encoded_files) != set(manifest_entries):
        raise ProvisioningError("Embedded data files do not match dataset-manifest.json.")
    for path, encoded in sorted(encoded_files.items()):
        raw = gzip.decompress(base64.b64decode(encoded, validate=True))
        entry = manifest_entries[path]
        if sha256_bytes(raw) != entry["sha256"]:
            raise ProvisioningError(f"Embedded dataset hash mismatch: {path}")
        text = raw.decode("utf-8")
        lines = text.splitlines()
        if not lines or lines[0] != entry["header"]:
            raise ProvisioningError(f"Embedded dataset header mismatch: {path}")
        if len(lines) - 1 != int(entry["rows"]):
            raise ProvisioningError(f"Embedded dataset row count mismatch: {path}")
        files[path] = raw
    return files


def notebook_fs_read_bytes(notebookutils: Any, uri: str, max_bytes: int) -> bytes:
    """Verify complete file bytes; fs.head is a preview, not a full-file API."""
    from pathlib import Path
    from tempfile import TemporaryDirectory

    with TemporaryDirectory(prefix="furusato-verify-") as directory:
        local = Path(directory) / "payload.bin"
        if notebookutils.fs.cp(uri, local.as_uri()) is False:
            raise ProvisioningError("OneLake verification copy returned false.")
        if local.stat().st_size > max_bytes:
            raise ConflictError("OneLake workshop file exceeds its packaged byte budget.")
        return local.read_bytes()


def ensure_onelake_text_file(
    notebookutils: Any,
    uri: str,
    raw: bytes,
    *,
    timeout_seconds: int = 900,
    poll_interval_seconds: int = 10,
    sleeper: Callable[[float], None] = time.sleep,
    clock: Callable[[], datetime] = utc_now,
) -> str:
    text = raw.decode("utf-8")
    if wait_for_onelake_exists(
        notebookutils,
        uri,
        timeout_seconds=timeout_seconds,
        poll_interval_seconds=poll_interval_seconds,
        sleeper=sleeper,
        clock=clock,
    ):
        existing_bytes = notebook_fs_read_bytes(notebookutils, uri, len(raw) + 1)
        if existing_bytes != raw:
            raise ConflictError(
                "An existing OneLake workshop file differs from the packaged bytes."
            )
        return "REUSED"
    result = notebookutils.fs.put(uri, text, False)
    if result is False:
        raise ProvisioningError("OneLake workshop file creation returned false.")
    written_bytes = notebook_fs_read_bytes(notebookutils, uri, len(raw) + 1)
    if written_bytes != raw:
        raise ProvisioningError(
            "OneLake workshop file verification failed: "
            f"expectedSha256={sha256_bytes(raw)}; actualSha256={sha256_bytes(written_bytes)}"
        )
    return "CREATED"


def onelake_files_path_to_abfss(
    one_lake_files_path: str,
    *,
    workspace_id: str,
    lakehouse_id: str,
) -> str:
    if not GUID_PATTERN.fullmatch(workspace_id) or not GUID_PATTERN.fullmatch(
        lakehouse_id
    ):
        raise ProvisioningError("OneLake GUID addressing requires valid item IDs.")
    parsed = urllib.parse.urlsplit(one_lake_files_path)
    host = (parsed.hostname or "").casefold()
    if (
        parsed.scheme.casefold() != "https"
        or parsed.username
        or parsed.password
        or parsed.port is not None
        or parsed.query
        or parsed.fragment
        or not re.fullmatch(
            r"(?:[a-z0-9-]+-)?onelake\.dfs\.fabric\.microsoft\.com",
            host,
        )
    ):
        raise ProvisioningError("Lakehouse returned an unsupported OneLake Files URI.")
    segments = [
        urllib.parse.unquote(segment)
        for segment in parsed.path.split("/")
        if segment
    ]
    expected = [workspace_id, lakehouse_id, "Files"]
    if len(segments) != len(expected) or any(
        actual.casefold() != desired.casefold()
        for actual, desired in zip(segments, expected)
    ):
        raise ProvisioningError(
            "Lakehouse OneLake Files URI did not match the current workspace and item."
        )
    return (
        f"abfss://{workspace_id}@{host}/"
        f"{lakehouse_id}/Files"
    )


def _is_retryable_onelake_exists_error(error: Exception) -> bool:
    text = str(error).casefold()
    return (
        ".dfs.fabric.microsoft.com" in text
        and "action=getstatus" in text
        and (", 400, head," in text or ", 404, head," in text)
    )


def wait_for_onelake_exists(
    notebookutils: Any,
    uri: str,
    *,
    timeout_seconds: int,
    poll_interval_seconds: int,
    sleeper: Callable[[float], None] = time.sleep,
    clock: Callable[[], datetime] = utc_now,
) -> bool:
    deadline = clock() + timedelta(seconds=timeout_seconds)
    while True:
        try:
            return bool(notebookutils.fs.exists(uri))
        except Exception as exc:
            # Fabric exposes the runtime-only Py4J exception through this API.
            if not _is_retryable_onelake_exists_error(exc):
                raise
            if clock() >= deadline:
                raise OperationTimeoutError(
                    "OneLake path did not become available before the timeout."
                ) from exc
            sleeper(poll_interval_seconds)


def notebook_fs_head_text(
    notebookutils: Any,
    path: str,
    max_bytes: int,
) -> str:
    value = notebookutils.fs.head(path, max_bytes)
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return str(value)


def provisioning_payload_digest(payload: Mapping[str, Any]) -> str:
    serialized = (
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        .replace("\r\n", "\n")
        .replace("\r", "\n")
        + "\n"
    )
    return sha256_bytes(serialized.encode("utf-8"))


def build_preview_plan(
    config: ProvisioningConfig,
    payload: Mapping[str, Any],
    *,
    workspace_name: str,
    folder_id: str,
    existing_items: Sequence[Mapping[str, Any]],
) -> ProvisioningPlan:
    names = build_names(
        config.participant_id,
        suffix_notebook_name=config.use_participant_notebook_names,
    )
    target = reference_agent_target(config, names)
    if config.enable_unified_data_agent:
        load_unified_assets(payload)
    elif config.enable_ai_reference_architecture:
        load_reference_assets(payload)
    desired = [
        ("lakehouse", "Lakehouse", names.lakehouse, payload["assetHashes"]["lakehouseSpec"]),
        ("eventhouse", "Eventhouse", names.eventhouse, payload["assetHashes"]["eventhouseSpec"]),
        ("kqlDatabase", "KQLDatabase", names.kql_database, payload["assetHashes"]["kqlSchema"]),
        ("notebook01", "Notebook", names.notebook01, payload["assetHashes"]["notebook01"]),
        ("pipeline", "DataPipeline", names.pipeline, payload["assetHashes"]["pipeline"]),
        ("ontology", "Ontology", names.ontology, payload["assetHashes"]["ontologyTemplate"]),
        ("dataAgent", "DataAgent", target["name"],
         payload["assetHashes"]["unifiedAgent"] if config.enable_unified_data_agent
         else payload["assetHashes"]["aiReference"] if config.enable_ai_reference_architecture
         else payload["assetHashes"]["dataAgent"]),
        ("reflex", "Reflex", names.reflex, payload["assetHashes"]["reflex"]),
    ]
    if config.enable_ai_reference_architecture:
        desired.insert(-2, ("agentOntology", "Ontology", names.agent_ontology, payload["assetHashes"]["aiReference"]))
    entries: list[PlanEntry] = []
    blockers: list[str] = []
    for key, item_type, display_name, digest in desired:
        matches = [
            item for item in existing_items
            if str(item.get("type", "")).casefold() == item_type.casefold()
            and item.get("displayName") == display_name
        ]
        if len(matches) > 1:
            blockers.append(f"duplicate {item_type} name: {display_name}")
            status = "BLOCKED_DUPLICATE"
            item_id = None
        elif matches:
            status = "EXISTS_REQUIRES_EXACT_VERIFICATION"
            item_id = str(matches[0].get("id", ""))
        else:
            status = "CREATE"
            item_id = None
        if key == "dataAgent" and target["role"] == "authorized-candidate" and item_id != target["expectedId"]:
            blockers.append("authorized reference candidate name/item-ID does not match the target Folder")
        entries.append(PlanEntry(key, item_type, display_name, digest, status, item_id))
    flags = {
        "executeNotebook01": config.execute_notebook_01,
        "refreshGraph": config.refresh_graph,
        "createDataAgent": config.create_data_agent,
        "createPipeline": config.create_pipeline,
        "createReflex": config.create_reflex,
    }
    if config.enable_ai_reference_architecture:
        flags["enableAiReferenceArchitecture"] = True
    if config.enable_unified_data_agent:
        flags["enableUnifiedDataAgent"] = True
    if config.allow_automated_apply:
        flags["allowAutomatedApply"] = True
    return ProvisioningPlan(
        workspace_name=workspace_name,
        folder_id=folder_id,
        participant_id=config.participant_id,
        names=names,
        payload_sha256=provisioning_payload_digest(payload),
        entries=entries,
        flags=flags,
        blockers=blockers,
        reference_target=target if config.enable_ai_reference_architecture or config.enable_unified_data_agent else None,
    )


def render_preview(plan: ProvisioningPlan, *, apply_mode: bool = False) -> list[str]:
    lines = [
        "FURUSATO WORKSHOP PROVISIONING PLAN (APPLY)"
        if apply_mode
        else "FURUSATO WORKSHOP PROVISIONING PREVIEW",
        f"Workspace: {plan.workspace_name}",
        f"Participant: {plan.participant_id}",
        f"Payload SHA-256: {plan.payload_sha256}",
    ]
    for entry in plan.entries:
        lines.append(
            f"- {entry.key}: {entry.item_type} {entry.display_name!r} -> "
            f"{entry.current_status}; desired={entry.desired_digest}"
        )
    for key, enabled in plan.flags.items():
        lines.append(f"- flag {key}={enabled}")
    if plan.blockers:
        lines.extend(f"BLOCKER: {item}" for item in plan.blockers)
    lines.append(f"PLAN_SHA256={plan.sha256}")
    if apply_mode:
        lines.append(
            "APPLY_REQUESTED: Fabric, Kusto, OneLake, event, and job writes will run "
            "after the gates below pass."
        )
    else:
        lines.append(
            "PREVIEW_ONLY: no Fabric, Kusto, OneLake, event, or job write occurred."
        )
    return lines


def validate_apply_gates(
    config: ProvisioningConfig,
    plan: ProvisioningPlan,
    runtime_context: Mapping[str, Any],
) -> None:
    if plan.blockers:
        raise ProvisioningError(f"Plan contains blockers: {plan.blockers}")
    if not config.apply_changes:
        raise ProvisioningError("APPLY_CHANGES is false.")
    if config.confirmed_plan_sha256.strip().casefold() != plan.sha256.strip().casefold():
        raise ProvisioningError(
            "CONFIRMED_PLAN_SHA256 does not match the preview. Re-run the preview cell "
            f"and paste the printed PLAN_SHA256 value (expected {plan.sha256})."
        )
    if not config.exclusive_create_window_confirmed:
        raise ProvisioningError("EXCLUSIVE_CREATE_WINDOW_CONFIRMED must be true.")
    if not runtime_context.get("isForInteractive", False) and not config.allow_automated_apply:
        raise ProvisioningError(
            "Live provisioning is allowed only interactively unless "
            "ALLOW_AUTOMATED_APPLY=True was included in the confirmed preview."
        )
    if config.allow_automated_apply and config.expected_workspace_name != plan.workspace_name:
        raise ProvisioningError("Automated apply requires an exact Workspace-name guard.")
    required_flags = {
        "EXECUTE_NOTEBOOK_01": config.execute_notebook_01,
        "CREATE_PIPELINE": config.create_pipeline,
        "REFRESH_GRAPH": config.refresh_graph,
        "CREATE_DATA_AGENT": config.create_data_agent,
        "CREATE_REFLEX": config.create_reflex,
    }
    disabled = sorted(name for name, enabled in required_flags.items() if not enabled)
    if disabled:
        raise ProvisioningError(
            "Complete live provisioning requires all component flags; "
            f"disabled={disabled}"
        )


class CheckpointStore:
    def __init__(
        self,
        notebookutils: Any,
        path: str,
        *,
        timeout_seconds: int = 900,
        poll_interval_seconds: int = 10,
        sleeper: Callable[[float], None] = time.sleep,
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        self.notebookutils = notebookutils
        self.path = path
        self.backup_path = path + ".bak"
        self.timeout_seconds = timeout_seconds
        self.poll_interval_seconds = poll_interval_seconds
        self.sleeper = sleeper
        self.clock = clock

    def load(self) -> dict[str, Any] | None:
        primary_exists = wait_for_onelake_exists(
            self.notebookutils,
            self.path,
            timeout_seconds=self.timeout_seconds,
            poll_interval_seconds=self.poll_interval_seconds,
            sleeper=self.sleeper,
            clock=self.clock,
        )
        candidate = self.path if primary_exists else self.backup_path
        if not primary_exists and not wait_for_onelake_exists(
            self.notebookutils,
            self.backup_path,
            timeout_seconds=self.timeout_seconds,
            poll_interval_seconds=self.poll_interval_seconds,
            sleeper=self.sleeper,
            clock=self.clock,
        ):
            return None
        try:
            return json.loads(
                notebook_fs_head_text(
                    self.notebookutils,
                    candidate,
                    4 * 1024 * 1024,
                )
            )
        except json.JSONDecodeError as exc:
            if candidate == self.backup_path or not wait_for_onelake_exists(
                self.notebookutils,
                self.backup_path,
                timeout_seconds=self.timeout_seconds,
                poll_interval_seconds=self.poll_interval_seconds,
                sleeper=self.sleeper,
                clock=self.clock,
            ):
                raise ProvisioningError("Checkpoint JSON is invalid.") from exc
            try:
                return json.loads(
                    notebook_fs_head_text(
                        self.notebookutils,
                        self.backup_path,
                        4 * 1024 * 1024,
                    )
                )
            except json.JSONDecodeError as backup_exc:
                raise ProvisioningError(
                    "Checkpoint and backup JSON are both invalid."
                ) from backup_exc

    def save(self, document: Mapping[str, Any]) -> None:
        temporary = self.path + ".tmp"
        text = json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True)
        put_result = self.notebookutils.fs.put(temporary, text, True)
        if put_result is False:
            raise ProvisioningError("Temporary checkpoint creation returned false.")
        if (
            notebook_fs_head_text(
                self.notebookutils,
                temporary,
                len(text.encode("utf-8")) + 1,
            )
            != text
        ):
            raise ProvisioningError("Temporary checkpoint verification failed.")
        had_primary = wait_for_onelake_exists(
            self.notebookutils,
            self.path,
            timeout_seconds=self.timeout_seconds,
            poll_interval_seconds=self.poll_interval_seconds,
            sleeper=self.sleeper,
            clock=self.clock,
        )
        if had_primary:
            if wait_for_onelake_exists(
                self.notebookutils,
                self.backup_path,
                timeout_seconds=self.timeout_seconds,
                poll_interval_seconds=self.poll_interval_seconds,
                sleeper=self.sleeper,
                clock=self.clock,
            ):
                self.notebookutils.fs.rm(self.backup_path)
            self.notebookutils.fs.mv(self.path, self.backup_path)
        try:
            self.notebookutils.fs.mv(temporary, self.path)
            if (
                notebook_fs_head_text(
                    self.notebookutils,
                    self.path,
                    len(text.encode("utf-8")) + 1,
                )
                != text
            ):
                raise ProvisioningError("Checkpoint replacement verification failed.")
        except Exception:
            if wait_for_onelake_exists(
                self.notebookutils,
                self.path,
                timeout_seconds=self.timeout_seconds,
                poll_interval_seconds=self.poll_interval_seconds,
                sleeper=self.sleeper,
                clock=self.clock,
            ):
                self.notebookutils.fs.rm(self.path)
            if had_primary and wait_for_onelake_exists(
                self.notebookutils,
                self.backup_path,
                timeout_seconds=self.timeout_seconds,
                poll_interval_seconds=self.poll_interval_seconds,
                sleeper=self.sleeper,
                clock=self.clock,
            ):
                self.notebookutils.fs.mv(self.backup_path, self.path)
            raise
        if had_primary and wait_for_onelake_exists(
            self.notebookutils,
            self.backup_path,
            timeout_seconds=self.timeout_seconds,
            poll_interval_seconds=self.poll_interval_seconds,
            sleeper=self.sleeper,
            clock=self.clock,
        ):
            self.notebookutils.fs.rm(self.backup_path)


def advance_checkpoint_document(
    current: Mapping[str, Any] | None,
    *,
    phase: str,
    ordered_phases: Sequence[str],
    plan_sha256: str,
    items: Mapping[str, Any],
    updated_at_utc: str,
    updates: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if phase not in ordered_phases:
        raise ProvisioningError(f"Unknown checkpoint phase {phase!r}.")
    result = copy.deepcopy(dict(current or {}))
    current_phase = str(result.get("phase") or "")
    current_index = (
        ordered_phases.index(current_phase)
        if current_phase in ordered_phases
        else -1
    )
    requested_index = ordered_phases.index(phase)
    if requested_index >= current_index:
        result["phase"] = phase
    merged_items = dict(result.get("items") or {})
    merged_items.update(copy.deepcopy(dict(items)))
    result.update(
        {
            "schemaVersion": 2,
            "planSha256": plan_sha256,
            "items": merged_items,
            "updatedAtUtc": updated_at_utc,
        }
    )
    if updates:
        result.update(copy.deepcopy(dict(updates)))
    return result


def _table_names_from_response(payload: Any) -> set[str]:
    if isinstance(payload, dict):
        rows = payload.get("value") or payload.get("data") or payload.get("tables") or []
    else:
        rows = payload
    names = set()
    for item in rows or []:
        if isinstance(item, str):
            names.add(item)
        elif isinstance(item, Mapping):
            name = item.get("name") or item.get("tableName") or item.get("displayName")
            if name:
                names.add(str(name).split(".")[-1])
    return names


def _fetch_lakehouse_table_names(
    client: WorkshopFabricClient,
    workspace_id: str,
    lakehouse_id: str,
) -> set[str]:
    base_url = (
        f"{FABRIC_API}/workspaces/{workspace_id}/lakehouses/{lakehouse_id}"
        "/tables?maxResults=100"
    )
    names: set[str] = set()
    visited: set[str] = set()
    next_url: str | None = base_url
    while next_url:
        if next_url in visited:
            raise ProvisioningError(
                "Lakehouse table paging repeated a continuation page and was stopped."
            )
        visited.add(next_url)
        if len(visited) > MAX_PAGE_REQUESTS:
            raise ProvisioningError(
                f"Lakehouse table paging exceeded {MAX_PAGE_REQUESTS} pages."
            )
        payload = client._request("GET", next_url).json()
        names |= _table_names_from_response(payload)
        continuation_uri = (
            payload.get("continuationUri") if isinstance(payload, Mapping) else None
        )
        token = (
            payload.get("continuationToken") if isinstance(payload, Mapping) else None
        )
        if continuation_uri:
            next_url = str(continuation_uri)
        elif token:
            next_url = (
                f"{base_url}&continuationToken="
                f"{urllib.parse.quote(str(token))}"
            )
        else:
            next_url = None
    return names


def verify_twenty_tables(
    client: WorkshopFabricClient,
    notebookutils: Any,
    workspace_id: str,
    lakehouse_id: str,
    lakehouse_name: str,
) -> set[str]:
    details = client.get_lakehouse(workspace_id, lakehouse_id)
    schema = str(details.get("properties", {}).get("defaultSchema") or "")
    if schema:
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", schema):
            raise ProvisioningError("Unexpected Lakehouse default schema name.")
        # The legacy /tables API and NotebookUtils listTables both reject
        # schema-enabled Lakehouses. Verify managed Delta directories in
        # the discovered default schema through the supported OneLake FS.
        table_root = (
            f"abfss://{workspace_id}@onelake.dfs.fabric.microsoft.com/"
            f"{lakehouse_id}/Tables/{schema}"
        )
        actual = {
            str(entry.name).rstrip("/").rsplit("/", 1)[-1]
            for entry in notebookutils.fs.ls(table_root)
            if entry.isDir and notebookutils.fs.exists(
                f"{table_root}/{str(entry.name).rstrip('/').rsplit('/', 1)[-1]}/_delta_log"
            )
        }
    else:
        try:
            actual = _fetch_lakehouse_table_names(client, workspace_id, lakehouse_id)
        except ProvisioningError:
            actual = _table_names_from_response(
                notebookutils.lakehouse.listTables(lakehouse_name, workspace_id)
            )
    missing = sorted((set(EXPECTED_TABLES) | {PUBLISH_CONTROL_TABLE}) - actual)
    if missing:
        raise ProvisioningError(f"Lakehouse table verification failed; missing={missing}")
    return actual


def verify_kql_schema(
    client: WorkshopFabricClient,
    query_uri: str,
    database_name: str,
) -> dict[str, Any]:
    checks = {
        "table": ".show table DonationEvents schema as json",
        "csvMapping": ".show table DonationEvents ingestion csv mappings",
        "materializedView": ".show materialized-view DonationObservationSummaryForAgent",
        "retention": ".show table DonationEvents policy retention",
        "caching": ".show table DonationEvents policy caching",
    }
    results = {}
    for key, command in checks.items():
        result = client.execute_kusto(
            query_uri, database_name, command, management=True
        )
        if not result.get("Tables"):
            raise ProvisioningError(f"KQL verification returned no table for {key}.")
        results[key] = result
    required_by_check = {
        "table": ("DonationEvents", "EventID"),
        "csvMapping": ("DonationEvents_IncrementCsvMap",),
        "materializedView": ("DonationObservationSummaryForAgent",),
        "retention": ("90.00:00:00",),
        "caching": ("7.00:00:00",),
    }
    forbidden_by_check = {
        "csvMapping": ("DonationEvents_CsvMap",),
        "table": ("DonationObservationsForAgent",),
        "materializedView": ("ProjectDonationObservationsForAgent",),
    }
    for key, tokens in forbidden_by_check.items():
        rendered = json.dumps(results[key], ensure_ascii=False)
        for forbidden in tokens:
            if re.search(rf"\b{re.escape(forbidden)}\b", rendered):
                raise ProvisioningError(
                    f"KQL verification found the removed {forbidden!r} mapping."
                )
    for key, tokens in required_by_check.items():
        rendered = json.dumps(results[key], ensure_ascii=False)
        for required in tokens:
            if required not in rendered:
                raise ProvisioningError(
                    f"KQL verification did not prove {required!r} in the {key} result."
                )
    return results


def wait_for_sql_endpoint(client: WorkshopFabricClient, workspace_id: str, lakehouse_id: str) -> dict[str, Any]:
    """Wait only for discovered connection metadata, without guessing an endpoint."""
    deadline = client.clock() + timedelta(seconds=client.timeout_seconds)
    while client.clock() < deadline:
        lakehouse = client.get_lakehouse(workspace_id, lakehouse_id)
        properties = lakehouse.get("properties")
        endpoint = properties.get("sqlEndpointProperties") if isinstance(properties, Mapping) else None
        if (
            isinstance(endpoint, Mapping)
            and isinstance(endpoint.get("connectionString"), str)
            and endpoint["connectionString"].strip()
        ):
            return lakehouse
        client.sleeper(client.poll_interval_seconds)
    raise OperationTimeoutError("Lakehouse SQL connection metadata did not become available before timeout.")


def resolve_graph_model(
    client: WorkshopFabricClient,
    workspace_id: str,
    ontology_name: str,
    ontology_id: str,
    *,
    folder_id: str | None = None,
) -> dict[str, Any]:
    suffix = ontology_id.replace("-", "")
    pattern = re.compile(rf"^{re.escape(ontology_name)}_graph_{re.escape(suffix)}$", re.I)
    deadline = client.clock() + timedelta(seconds=client.timeout_seconds)
    while client.clock() < deadline:
        matches = [
            item for item in client.list_items(workspace_id, folder_id=folder_id)
            if str(item.get("type", "")).casefold() == "graphmodel"
            and pattern.fullmatch(str(item.get("displayName", "")))
        ]
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            raise ConflictError("Multiple generated GraphModel children were found.")
        client.sleeper(client.poll_interval_seconds)
    raise OperationTimeoutError("Generated GraphModel was not discovered in time.")


def wait_for_complete_ontology_definition(
    fabric_client: WorkshopFabricClient,
    ontology_client: Any,
    workspace_id: str,
    ontology_id: str,
    desired_definition: Mapping[str, Any],
    verify_complete_definition: Callable[
        [Mapping[str, Any], Mapping[str, Any]],
        Mapping[str, Any],
    ],
    *,
    retryable_error: Callable[[Exception], bool] | None = None,
) -> dict[str, Any]:
    deadline = fabric_client.clock() + timedelta(
        seconds=fabric_client.timeout_seconds
    )
    while fabric_client.clock() < deadline:
        try:
            current = ontology_client.get_definition(workspace_id, ontology_id)
        except Exception as exc:
            if retryable_error is None or not retryable_error(exc):
                raise
            fabric_client.sleeper(fabric_client.poll_interval_seconds)
            continue
        verification = verify_complete_definition(current, desired_definition)
        if bool(verification.get("verified")):
            return current
        fabric_client.sleeper(fabric_client.poll_interval_seconds)
    raise OperationTimeoutError(
        "Created Ontology definition did not become the exact requested "
        "definition in time."
    )


def execute_provisioning(
    config: ProvisioningConfig,
    payload: Mapping[str, Any],
    *,
    notebookutils: Any,
    spark: Any,
    requests_session: requests.Session | None = None,
    ontology_namespace: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Plan or apply the complete workshop in the current Notebook workspace."""
    validate_config(config)
    reference_assets = (
        load_unified_assets(payload) if config.enable_unified_data_agent
        else load_reference_assets(payload) if config.enable_ai_reference_architecture else None
    )
    context = notebookutils.runtime.context
    workspace_id = str(context["currentWorkspaceId"])
    workspace_name = str(context["currentWorkspaceName"])
    current_notebook_id = str(context.get("currentNotebookId", ""))
    if config.expected_workspace_name and workspace_name != config.expected_workspace_name:
        raise ProvisioningError(
            f"Workspace mismatch: expected {config.expected_workspace_name!r}."
        )
    if not current_notebook_id:
        raise ProvisioningError("Runtime context did not expose currentNotebookId.")

    client = WorkshopFabricClient(
        lambda: notebookutils.credentials.getToken("pbi"),
        lambda: notebookutils.credentials.getToken("kusto"),
        session=requests_session,
        timeout_seconds=config.operation_timeout_seconds,
        poll_interval_seconds=config.poll_interval_seconds,
    )
    client.check_active_capacity(workspace_id)
    current_notebook = client.get_item(workspace_id, current_notebook_id)
    folder_id = str(current_notebook.get("folderId") or "")
    if not folder_id:
        raise ProvisioningError(
            "Notebook 04 must run from the target Fabric Folder."
        )

    embedded_files = decode_embedded_dataset(payload)
    existing_items = client.list_items(workspace_id, folder_id=folder_id)
    plan = build_preview_plan(
        config,
        payload,
        workspace_name=workspace_name,
        folder_id=folder_id,
        existing_items=existing_items,
    )
    for line in render_preview(plan, apply_mode=config.apply_changes):
        print(line)
    if not config.apply_changes:
        return {"mode": "Preview", "planSha256": plan.sha256}
    validate_apply_gates(config, plan, context)
    reference_modules = load_reference_modules(reference_assets) if reference_assets else {}
    reference_sql_driver = None
    if reference_assets:
        reference_modules["reference_sql"].plan_reference_sql(reference_assets["sqlDdl"])
        reference_modules["reference_kql"].validate_function_contracts(reference_assets["kqlFunctions"])
        reference_sql_driver = reference_modules["reference_sql"].require_odbc_driver()
    tenant_id = resolve_tenant_id(
        context,
        lambda: notebookutils.credentials.getToken("pbi"),
    )

    names = plan.names
    result: dict[str, Any] = {
        "mode": "Apply",
        "planSha256": plan.sha256,
        "workspaceName": workspace_name,
        "items": {},
    }

    lakehouse, state = client.ensure_simple_item(
        workspace_id,
        item_type="Lakehouse",
        display_name=names.lakehouse,
        folder_id=folder_id,
        creation_payload={"enableSchemas": True},
    )
    result["items"]["lakehouse"] = {"id": lakehouse["id"], "state": state}
    lakehouse_details, one_lake_files_path = client.wait_for_lakehouse_property(
        workspace_id,
        str(lakehouse["id"]),
        "oneLakeFilesPath",
    )
    if not str(lakehouse_details.get("properties", {}).get("defaultSchema") or ""):
        raise ConflictError(
            "Lakehouse is not schema-enabled; expected a default schema."
        )
    if reference_assets and lakehouse_details["properties"]["defaultSchema"] != "dbo":
        raise ConflictError("AI reference architecture requires the discovered managed dbo schema.")
    one_lake_files_root = onelake_files_path_to_abfss(
        str(one_lake_files_path),
        workspace_id=workspace_id,
        lakehouse_id=str(lakehouse["id"]),
    )
    checkpoint_path = (
        f"{one_lake_files_root}/_provisioning/furusato/"
        f"{config.participant_id}/"
        + (
            ("state-unified-" if config.enable_unified_data_agent else "state-ai-reference-")
            + sha256_json(plan.reference_target)[:16] + ".json"
            if reference_assets else "state.json"
        )
    )
    checkpoint = CheckpointStore(
        notebookutils,
        checkpoint_path,
        timeout_seconds=config.operation_timeout_seconds,
        poll_interval_seconds=config.poll_interval_seconds,
        sleeper=client.sleeper,
        clock=client.clock,
    )
    prior = checkpoint.load()
    if prior and prior.get("planSha256") != plan.sha256:
        raise ConflictError("Checkpoint belongs to a different provisioning plan.")
    checkpoint_state: dict[str, Any] = dict(prior or {})

    checkpoint_phases = (
        "lakehouse-created",
        "dataset-uploaded",
        "lakehouse-data-ready",
        "kql-ready",
        "pipeline-ready",
        "ontology-ready",
        *(("agent-ontology-ready",) if config.enable_ai_reference_architecture else ()),
        "complete",
    )

    def checkpoint_reached(phase: str) -> bool:
        if not checkpoint_state:
            return False
        try:
            return checkpoint_phases.index(str(checkpoint_state.get("phase"))) >= (
                checkpoint_phases.index(phase)
            )
        except ValueError:
            return False

    def save_phase(phase: str, **updates: Any) -> None:
        next_state = advance_checkpoint_document(
            checkpoint_state,
            phase=phase,
            ordered_phases=checkpoint_phases,
            plan_sha256=plan.sha256,
            items=result["items"],
            updated_at_utc=utc_now().isoformat(),
            updates=updates,
        )
        checkpoint_state.clear()
        checkpoint_state.update(next_state)
        checkpoint.save(checkpoint_state)

    save_phase("lakehouse-created")
    # The event subscription needs the folder, but files must arrive only
    # after the participant has enabled the FileCreated trigger.
    if notebookutils.fs.mkdirs(f"{one_lake_files_root}/increment") is False:
        raise ProvisioningError("Could not create the increment watch folder.")
    for relative_path, raw in sorted(embedded_files.items()):
        target = dataset_target_relative_path(relative_path, config.participant_id)
        uri = f"{one_lake_files_root}/{target}"
        ensure_onelake_text_file(
            notebookutils,
            uri,
            raw,
            timeout_seconds=config.operation_timeout_seconds,
            poll_interval_seconds=config.poll_interval_seconds,
            sleeper=client.sleeper,
            clock=client.clock,
        )
    save_phase("dataset-uploaded")
    print(
        "INCREMENTS_STAGED: bundled increments are outside Files/increment; "
        "enable the FileCreated trigger, then upload them sequentially."
    )

    notebook01 = bind_notebook_to_lakehouse(
        payload["notebook01"],
        workspace_id,
        str(lakehouse["id"]),
        names.lakehouse,
        participant_id=config.participant_id,
    )
    notebook_definition = {
        "format": "ipynb",
        "parts": [encode_part("notebook-content.ipynb", notebook01)],
    }
    notebook_item, state = client.ensure_definition_item(
        workspace_id,
        item_type="Notebook",
        display_name=names.notebook01,
        folder_id=folder_id,
        definition=notebook_definition,
    )
    result["items"]["notebook01"] = {"id": notebook_item["id"], "state": state}
    if config.execute_notebook_01:
        if not checkpoint_reached("lakehouse-data-ready"):
            client.run_or_reuse_recent_job(
                workspace_id,
                str(notebook_item["id"]),
                "RunNotebook",
                body={
                    "executionData": {
                        "configuration": {
                            "defaultLakehouse": {
                                "id": str(lakehouse["id"]),
                                "name": names.lakehouse,
                            }
                        }
                    }
                },
            )
        verify_twenty_tables(
            client,
            notebookutils,
            workspace_id,
            str(lakehouse["id"]),
            names.lakehouse,
        )
    save_phase("lakehouse-data-ready")
    if reference_assets:
        lakehouse_details = wait_for_sql_endpoint(client, workspace_id, str(lakehouse["id"]))
        result["referenceSql"] = reference_modules["reference_sql"].deploy_reference_sql(
            lakehouse_details, reference_assets["sqlDdl"],
            lambda: notebookutils.credentials.getToken("https://database.windows.net/"),
            db_driver=reference_sql_driver,
            connect_timeout=min(30, config.operation_timeout_seconds),
            query_timeout=min(180, config.operation_timeout_seconds),
            source_wait_timeout=config.operation_timeout_seconds,
            poll_interval=config.poll_interval_seconds,
        )

    eventhouse, state = client.ensure_simple_item(
        workspace_id,
        item_type="Eventhouse",
        display_name=names.eventhouse,
        folder_id=folder_id,
    )
    result["items"]["eventhouse"] = {"id": eventhouse["id"], "state": state}

    kql_existing = client.find_unique_item(
        workspace_id,
        "KQLDatabase",
        names.kql_database,
        folder_id=folder_id,
    )
    if kql_existing is None:
        kql_database = client.wait_for_unique_item(
            workspace_id,
            "KQLDatabase",
            names.kql_database,
            folder_id=folder_id,
        )
        kql_state = "GENERATED"
    else:
        kql_database, kql_state = kql_existing, "REUSED"
    kql_details, parent_eventhouse_id = client.wait_for_kql_database_property(
        workspace_id,
        str(kql_database["id"]),
        "parentEventhouseItemId",
    )
    if str(kql_details.get("folderId") or "") != folder_id:
        raise ConflictError("Existing KQL Database is outside the target Folder.")
    if str(parent_eventhouse_id) != str(eventhouse["id"]):
        raise ConflictError("Existing KQL Database belongs to another Eventhouse.")
    result["items"]["kqlDatabase"] = {
        "id": kql_database["id"],
        "state": kql_state,
    }
    kql_details, query_uri_value = client.wait_for_kql_database_property(
        workspace_id,
        str(kql_database["id"]),
        "queryServiceUri",
    )
    query_uri = str(query_uri_value)
    for command in payload["kqlManagementCommands"]:
        client.execute_kusto(query_uri, names.kql_database, command, management=True)
    verify_kql_schema(client, query_uri, names.kql_database)
    if reference_assets:
        result["referenceKql"] = reference_modules["reference_kql"].provision_kql(
            client, query_uri, names.kql_database, reference_assets["kqlFunctions"], enabled=True,
        )
    save_phase("kql-ready")

    bindings = {
        "workspace.id": workspace_id,
        "tenant.id": tenant_id,
        "item.lakehouse.id": str(lakehouse["id"]),
        "item.kqlDatabase.id": str(kql_database["id"]),
        "item.kqlDatabase.queryServiceUri": query_uri,
        "name.lakehouse": names.lakehouse,
        "name.eventhouse": names.eventhouse,
        "name.kqlDatabase": names.kql_database,
        "name.pipeline": names.pipeline,
        "name.ontology": names.ontology,
        "name.dataAgent": names.data_agent,
        "name.reflex": names.reflex,
    }
    if config.create_pipeline:
        pipeline_definition = bundle_definition(
            payload["bundle"], "data-pipeline", bindings
        )
        pipeline, state = client.ensure_definition_item(
            workspace_id,
            item_type="DataPipeline",
            display_name=names.pipeline,
            folder_id=folder_id,
            definition=pipeline_definition,
        )
        result["items"]["pipeline"] = {"id": pipeline["id"], "state": state}
        bindings["item.pipeline.id"] = str(pipeline["id"])

    save_phase("pipeline-ready")

    if ontology_namespace is None:
        ontology_namespace = globals()
    required_ontology_symbols = (
        "FabricApiError",
        "FabricApiClient",
        "build_creation_plan",
        "verify_complete_definition",
    )
    if any(symbol not in ontology_namespace for symbol in required_ontology_symbols):
        raise ProvisioningError("Ontology creator core was not embedded before execution.")
    ontology_client = ontology_namespace["FabricApiClient"](
        lambda: notebookutils.credentials.getToken("pbi"),
        operation_timeout_seconds=config.operation_timeout_seconds,
    )
    ontology_sources = {
        "lakehouse": {
            **dict(lakehouse),
            "displayName": names.lakehouse,
        },
        "eventhouse": {
            **dict(eventhouse),
            "displayName": names.eventhouse,
        },
        "kqlDatabase": {
            **dict(kql_details),
            "id": str(kql_database["id"]),
            "displayName": names.kql_database,
            "properties": {
                **dict(kql_details.get("properties") or {}),
                "queryServiceUri": query_uri,
                "parentEventhouseItemId": str(parent_eventhouse_id),
            },
        },
    }
    ontology_plan = ontology_namespace["build_creation_plan"](
        payload["ontologyTemplate"],
        participant_id=config.participant_id,
        workspace_id=workspace_id,
        workspace_name=workspace_name,
        sources=ontology_sources,
        folder_id=folder_id,
        folder_name=str(current_notebook.get("folderName") or "current"),
    )
    existing_ontology = client.find_unique_item(
        workspace_id,
        "Ontology",
        names.ontology,
        folder_id=folder_id,
    )
    if existing_ontology:
        client.require_item_in_folder(
            workspace_id,
            existing_ontology,
            folder_id=folder_id,
            item_type="Ontology",
            display_name=names.ontology,
        )
        ontology = existing_ontology
        ontology_state = "REUSED"
        current = ontology_client.get_definition(
            workspace_id, str(ontology["id"])
        )
        verification = ontology_namespace["verify_complete_definition"](
            current, ontology_plan.definition
        )
        if not verification["verified"]:
            raise ConflictError(
                "Existing Ontology differs from the 54-part template."
            )
    else:
        ontology_body = {
            "displayName": names.ontology,
            "type": "Ontology",
            "folderId": folder_id,
            "definition": ontology_plan.definition,
        }
        created_ontology = client.create_item(workspace_id, ontology_body)
        ontology = created_ontology or client.wait_for_unique_item(
            workspace_id,
            "Ontology",
            names.ontology,
            folder_id=folder_id,
        )
        ontology_state = "CREATED"
        client.require_item_in_folder(
            workspace_id,
            ontology,
            folder_id=folder_id,
            item_type="Ontology",
            display_name=names.ontology,
        )
        wait_for_complete_ontology_definition(
            client,
            ontology_client,
            workspace_id,
            str(ontology["id"]),
            ontology_plan.definition,
            ontology_namespace["verify_complete_definition"],
            retryable_error=lambda exc: (
                isinstance(exc, ontology_namespace["FabricApiError"])
                and str(exc).startswith("Fabric HTTP 404:")
            ),
        )
    result["items"]["ontology"] = {"id": ontology["id"], "state": ontology_state}
    graph = resolve_graph_model(
        client,
        workspace_id,
        names.ontology,
        str(ontology["id"]),
        folder_id=folder_id,
    )
    result["items"]["graphModel"] = {"id": graph["id"], "state": "GENERATED"}
    if config.refresh_graph and not config.enable_ai_reference_architecture and not checkpoint_reached("ontology-ready"):
        client.run_or_reuse_graph_refresh(workspace_id, str(graph["id"]))
    save_phase("ontology-ready")

    bindings["item.ontology.id"] = str(ontology["id"])
    if config.enable_ai_reference_architecture:
        path_runtime = reference_modules["reference_ontology"]
        path_definition = path_runtime.materialize_path_definition(
            reference_assets["ontologyTemplate"],
            workspace_id=workspace_id,
            lakehouse_id=str(lakehouse["id"]),
            display_name=names.agent_ontology,
        )
        path_item, path_state = client.ensure_definition_item(
            workspace_id, item_type="Ontology", display_name=names.agent_ontology,
            folder_id=folder_id, definition=path_definition,
        )
        path_graph = resolve_graph_model(
            client, workspace_id, names.agent_ontology, str(path_item["id"]), folder_id=folder_id,
        )
        # Both refresh lifecycles are observed through the same bounded job
        # discovery, including service-started refreshes. No questions are sent.
        teaching_refresh, _ = client.run_or_reuse_graph_refresh(workspace_id, str(graph["id"]))
        path_refresh, _ = client.run_or_reuse_graph_refresh(
            workspace_id, str(path_graph["id"]), expected_counts=path_runtime.PATH_GRAPH_COUNTS,
        )
        result["items"]["agentOntology"] = {"id": path_item["id"], "state": path_state}
        result["items"]["agentGraphModel"] = {"id": path_graph["id"], "state": "GENERATED"}
        result["ontologyCompatibility"] = {
            **path_runtime.compatibility_observation(lakehouse_details),
            "teachingRefreshStatus": teaching_refresh.get("status", teaching_refresh.get("state")),
            "pathRefreshStatus": path_refresh.get("status", path_refresh.get("state")),
        }
        bindings["item.agent_ontology.id"] = str(path_item["id"])
        bindings["name.agent_ontology"] = names.agent_ontology
        save_phase("agent-ontology-ready")
    if config.create_data_agent and reference_assets:
        target = plan.reference_target
        existing = client.find_unique_item(
            workspace_id, "DataAgent", target["name"], folder_id=folder_id,
        )
        if target["expectedId"] and (not existing or str(existing["id"]) != target["expectedId"]):
            raise ConflictError("Authorized candidate target changed since preview.")
        initialize = existing is None
        if initialize:
            created = client.create_item(workspace_id, {
                "displayName": target["name"], "type": "DataAgent", "folderId": folder_id,
            })
            data_agent = created or client.wait_for_unique_item(
                workspace_id, "DataAgent", target["name"], folder_id=folder_id,
            )
        else:
            data_agent = existing
        client.require_item_in_folder(
            workspace_id, data_agent, folder_id=folder_id, item_type="DataAgent", display_name=target["name"],
        )
        selection = reference_modules["reference_agent"].configure_reference_agent(
            client, workspace_id, str(data_agent["id"]), reference_assets,
            {
                "lakehouse_tables": {"workspaceId": workspace_id, "itemId": str(lakehouse["id"])},
                "kusto": {"workspaceId": workspace_id, "itemId": str(kql_database["id"])},
                "ontology": {
                    "workspaceId": workspace_id,
                    "itemId": str(ontology["id"] if config.enable_unified_data_agent else path_item["id"]),
                },
            },
            initialize=initialize,
        )
        result["items"]["dataAgent"] = {"id": data_agent["id"], **selection}
    elif config.create_data_agent:
        data_agent_definition = bundle_definition(
            payload["bundle"], "data-agent", bindings
        )
        data_agent, state = client.ensure_definition_item(
            workspace_id,
            item_type="DataAgent",
            display_name=names.data_agent,
            folder_id=folder_id,
            definition=data_agent_definition,
        )
        verified_definition = client.get_definition(
            workspace_id, str(data_agent["id"])
        )
        if not definitions_equal(verified_definition, data_agent_definition):
            raise ProvisioningError("Data Agent definition verification failed.")
        result["items"]["dataAgent"] = {"id": data_agent["id"], "state": state}

    if config.create_reflex:
        reflex_definition = bundle_definition(payload["bundle"], "reflex", bindings)
        verify_reflex_fail_closed(reflex_definition)
        reflex, state = client.ensure_definition_item(
            workspace_id,
            item_type="Reflex",
            display_name=names.reflex,
            folder_id=folder_id,
            definition=reflex_definition,
        )
        result["items"]["reflex"] = {"id": reflex["id"], "state": state}
    save_phase("complete")
    return result