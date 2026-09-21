"""Load runtime facts and explicit, separately sealed document profiles.

The v2.7.0 Core inputs stay intact when the one-Agent document edition is
selected. Counts, hashes, names, defaults and instructions come from local
assets; a missing unified bundle never silently selects legacy instructions.
"""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import re
import sys
import types
from dataclasses import dataclass, field, replace
from functools import lru_cache
from pathlib import Path
from typing import Any


UNIFIED_DOCUMENT_EDITION = "unified-20260914"


def repo_root() -> Path:
    """Return the repository root (the folder that owns ``VERSION``)."""
    here = Path(__file__).resolve()
    for candidate in here.parents:
        if (candidate / "VERSION").is_file() and (candidate / "workshop").is_dir():
            return candidate
    raise RuntimeError("Repository root with VERSION and workshop/ was not found.")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class NotebookCell:
    number: int
    index: int
    cell_type: str
    heading: str
    first_line: str
    source_lines: int
    is_parameter_cell: bool
    source_sha256: str


@dataclass(frozen=True)
class NotebookInfo:
    name: str
    path: Path
    relative_path: str
    sha256: str
    version: str
    purpose: str
    header_markdown: str
    cells: tuple[NotebookCell, ...]
    parameters: dict[str, Any]

    @property
    def markdown_cells(self) -> int:
        return sum(1 for c in self.cells if c.cell_type == "markdown")

    @property
    def code_cells(self) -> int:
        return sum(1 for c in self.cells if c.cell_type == "code")


@dataclass(frozen=True)
class OntologyProperty:
    name: str
    value_type: str
    description: str
    attributes: dict[str, str]
    is_key: bool
    is_display_name: bool


@dataclass(frozen=True)
class OntologyBinding:
    binding_type: str
    source_type: str
    source_table: str
    timestamp_column: str | None
    column_map: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class OntologyEntity:
    name: str
    key_property: str
    display_name_property: str
    description: str
    attributes: dict[str, str]
    properties: tuple[OntologyProperty, ...]
    bindings: tuple[OntologyBinding, ...]
    synonyms: tuple[str, ...] = ()
    timeseries_properties: tuple[OntologyProperty, ...] = ()

    @property
    def static_binding(self) -> OntologyBinding | None:
        for binding in self.bindings:
            if binding.binding_type == "NonTimeSeries":
                return binding
        return None

    @property
    def timeseries_binding(self) -> OntologyBinding | None:
        for binding in self.bindings:
            if binding.binding_type == "TimeSeries":
                return binding
        return None


@dataclass(frozen=True)
class OntologyRelationship:
    name: str
    origin: str
    target: str
    description: str
    attributes: dict[str, str]
    mapping_table: str
    origin_key_column: str
    target_key_column: str

    @property
    def cardinality(self) -> str:
        return self.attributes.get("cardinality", "")

    @property
    def direction(self) -> str:
        return self.attributes.get("direction", f"{self.origin} -> {self.target}")


@dataclass(frozen=True)
class KqlObject:
    """One management command in the shipped Eventhouse setup script."""

    command: str
    kind: str
    name: str
    detail: str


#: How each supported management command is presented in the participant guide.
#: The parser refuses to describe a command it does not recognise, so a runtime
#: change to the KQL script surfaces as a build failure rather than a stale table.
_KQL_COMMAND_PATTERNS = (
    (
        re.compile(r"^\.create-merge table\s+(?P<name>[A-Za-z0-9_]+)\s*\("),
        "テーブル",
        "create-merge table",
    ),
    (
        re.compile(
            r"^\.create-or-alter table\s+(?P<table>[A-Za-z0-9_]+)\s+ingestion csv mapping\s+'(?P<name>[^']+)'"
        ),
        "ingestion csv mapping",
        "create-or-alter ingestion mapping",
    ),
    (
        re.compile(r"^\.create-or-alter materialized-view\s+(?P<name>[A-Za-z0-9_]+)"),
        "マテリアライズドビュー",
        "create-or-alter materialized-view",
    ),
    (
        re.compile(r"^\.alter table\s+(?P<table>[A-Za-z0-9_]+)\s+policy retention"),
        "ポリシー（retention）",
        "alter table policy retention",
    ),
    (
        re.compile(r"^\.alter table\s+(?P<table>[A-Za-z0-9_]+)\s+policy caching"),
        "ポリシー（caching）",
        "alter table policy caching",
    ),
    (
        re.compile(r"^\.alter table\s+(?P<table>[A-Za-z0-9_]+)\s+policy update"),
        "ポリシー（update）",
        "alter table policy update",
    ),
    (
        re.compile(r"^\.(?:create(?:-or-alter)?|alter)\s+function\b"),
        "関数",
        "function",
    ),
)


@lru_cache(maxsize=1)
def _kql_helpers():
    """Share the offline lexer with the portable runtime, without sys.path edits."""
    path = Path(__file__).resolve().parents[2] / "provisioning" / "reference_kql.py"
    name = "_furusato_docs_reference_kql"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("The local KQL contract parser could not be loaded.")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def parse_kql_objects(script: str) -> list[KqlObject]:
    """Return the management commands the Eventhouse setup script creates, in order.

    Only complete top-level management commands are considered. The shared
    lexer keeps optional parameters, nested bodies, literal braces and internal
    blank lines together; trailing verification queries are deliberately
    excluded. Function labels retain the existing ``Name()`` convention.
    """
    objects: list[KqlObject] = []
    helpers = _kql_helpers()
    for text in helpers.extract_kql_management_commands(script):
        for pattern, kind, command in _KQL_COMMAND_PATTERNS:
            match = pattern.match(text)
            if not match:
                continue
            groups = match.groupdict()
            name = groups.get("name") or ""
            if command == "function":
                definition = helpers.parse_function_command(text)
                name = definition.name + "()"
                command = definition.verb + " function"
            if not name:
                name = groups.get("table", "")
            objects.append(
                KqlObject(
                    command=command,
                    kind=kind,
                    name=name,
                    detail=_kql_detail(command, text.splitlines(), 0),
                )
            )
            break
        else:
            raise ValueError(f"Unrecognised KQL management command: {text!r}")
    return objects


def _kql_detail(command: str, lines: list[str], index: int) -> str:
    """Pull the concrete settings out of a policy or schema command."""
    if command == "create-merge table":
        columns = 0
        for follow in lines[index + 1 :]:
            if follow.strip().startswith(")"):
                break
            if ":" in follow:
                columns += 1
        return f"{columns} 列"
    if command == "create-or-alter ingestion mapping":
        ordinals = 0
        for follow in lines[index + 1 :]:
            ordinals += follow.count('"Ordinal"')
            if follow.rstrip().endswith("]'"):
                break
        return f"{ordinals} 序数"
    if command == "alter table policy retention":
        follow = lines[index + 1] if index + 1 < len(lines) else ""
        period = re.search(r'"SoftDeletePeriod"\s*:\s*"([^"]+)"', follow)
        recoverability = re.search(r'"Recoverability"\s*:\s*"([^"]+)"', follow)
        days = period.group(1).split(".")[0] if period else "?"
        return f"SoftDeletePeriod {days} 日 / Recoverability {recoverability.group(1) if recoverability else '?'}"
    if command == "alter table policy caching":
        hot = re.search(r"hot\s*=\s*([0-9]+d)", lines[index])
        return f"hot cache {hot.group(1).rstrip('d') if hot else '?'} 日"
    if command == "create-or-alter materialized-view":
        for follow in lines[index : index + 4]:
            source = re.search(r"on table\s+([A-Za-z0-9_]+)", follow)
            if source:
                return f"on table {source.group(1)}"
    return ""


@dataclass(frozen=True)
class AgentGuideProfile:
    """An explicit document profile, separate from the retained Core runtime."""

    instructions: str
    stage_config: dict[str, Any]
    sources: dict[str, dict[str, Any]]
    contract: dict[str, Any]
    instruction_relative_path: str


@dataclass
class RuntimeContext:
    root: Path
    version: str
    dataset_manifest: dict[str, Any]
    workspace_contract: dict[str, Any]
    checksums: dict[str, str]
    agent_instructions: str
    agent_stage_config: dict[str, Any]
    agent_sources: dict[str, dict[str, Any]]
    agent_fewshots: list[dict[str, str]]
    pipeline: dict[str, Any]
    kql_setup: str
    notebooks: dict[str, NotebookInfo]
    entities: list[OntologyEntity]
    relationships: list[OntologyRelationship]
    ontology_contract: dict[str, Any]
    semantic_manifest: dict[str, Any] = field(default_factory=dict)
    variable_library: dict[str, Any] = field(default_factory=dict)
    variable_library_value_sets: list[str] = field(default_factory=list)
    diagrams: dict[str, dict[str, Path]] = field(default_factory=dict)
    document_edition: str = ""
    unified_profile: AgentGuideProfile | None = None

    # ---------------------------------------------------------------- helpers
    @property
    def is_unified_guide(self) -> bool:
        return self.document_edition == UNIFIED_DOCUMENT_EDITION

    @property
    def guide_profile(self) -> AgentGuideProfile:
        if not self.is_unified_guide or self.unified_profile is None:
            raise ValueError("The unified document edition requires its sealed Agent profile.")
        return self.unified_profile

    @property
    def guide_agent_instructions(self) -> str:
        return self.guide_profile.instructions if self.is_unified_guide else self.agent_instructions

    @property
    def guide_agent_stage_config(self) -> dict[str, Any]:
        return self.guide_profile.stage_config if self.is_unified_guide else self.agent_stage_config

    @property
    def guide_instruction_relative_path(self) -> str:
        if self.is_unified_guide:
            return self.guide_profile.instruction_relative_path
        return f"workshop/v{self.version}/data-agent/agent-instructions.txt"

    def guide_source_text(self, source_type: str) -> tuple[str, str]:
        """Return description/instructions without inventing serialized source IDs."""
        if self.is_unified_guide:
            source = self.guide_profile.sources[source_type]
            return source["description"], source.get("instructions") or ""
        source = self.agent_sources[source_type]
        return source["userDescription"], source.get("dataSourceInstructions") or ""

    @property
    def guide_kql_fewshots(self) -> list[dict[str, str]]:
        if not self.is_unified_guide:
            return []
        return self.guide_profile.sources["kusto"]["fewShots"]["fewShots"]

    @property
    def expected(self) -> dict[str, Any]:
        return self.dataset_manifest["expected"]

    @property
    def expected_increment(self) -> dict[str, Any]:
        return self.dataset_manifest["expectedIncrement"]

    @property
    def names(self) -> dict[str, str]:
        return self.workspace_contract["participantNames"]

    @property
    def seed_files(self) -> list[dict[str, Any]]:
        return self.dataset_manifest["files"]

    @property
    def increment_files(self) -> list[dict[str, Any]]:
        return self.dataset_manifest["incrementFiles"]

    @property
    def csv_count(self) -> int:
        return len(self.seed_files) + len(self.increment_files)

    @property
    def metadata_object_count(self) -> int:
        contract = self.ontology_contract
        return (
            contract["entityTypes"]
            + contract["staticProperties"]
            + contract["timeseriesProperties"]
            + contract["relationshipTypes"]
        )

    def entity(self, name: str) -> OntologyEntity:
        for item in self.entities:
            if item.name == name:
                return item
        raise KeyError(name)

    def relationship(self, name: str) -> OntologyRelationship:
        for item in self.relationships:
            if item.name == name:
                return item
        raise KeyError(name)

    def node_count(self, entity_name: str) -> int:
        entity = self.entity(entity_name)
        binding = entity.static_binding
        assert binding is not None, entity_name
        return int(self.expected["nodeCounts"][binding.source_table])

    def edge_count(self, relationship_name: str) -> int:
        return int(self.expected["edgeCounts"][relationship_name])

    @property
    def kql_objects(self) -> list[KqlObject]:
        """Management objects the shipped Eventhouse setup script creates."""
        return parse_kql_objects(self.kql_setup)

    @property
    def udf_source(self) -> str:
        path = self.root / "workshop" / f"v{self.version}" / "udf" / "calc_furusato_deduction.py"
        return path.read_text("utf-8") if path.is_file() else ""

    @property
    def udf_relative_path(self) -> str:
        return f"workshop/v{self.version}/udf/calc_furusato_deduction.py"


_PARAM_ASSIGNMENT = re.compile(r"^([A-Z][A-Z0-9_]*)\s*=\s*(.+?)\s*$")


def _literal(raw: str) -> Any:
    raw = raw.strip()
    if raw.startswith("f\"") or raw.startswith("f'"):
        return raw
    try:
        return json.loads(raw.replace("True", "true").replace("False", "false").replace("'", '"'))
    except Exception:
        return raw


def _parse_parameter_cell(source: str) -> dict[str, Any]:
    parameters: dict[str, Any] = {}
    for line in source.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        match = _PARAM_ASSIGNMENT.match(stripped)
        if match:
            parameters[match.group(1)] = _literal(match.group(2))
    return parameters


def _cell_heading(cells: list[dict[str, Any]], index: int) -> str:
    """Return the nearest preceding markdown heading for a notebook cell."""
    for probe in range(index, -1, -1):
        source = "".join(cells[probe]["source"])
        for line in source.splitlines():
            if line.startswith("#"):
                return line.lstrip("#").strip()
        if cells[probe]["cell_type"] == "markdown" and source.strip():
            return source.strip().splitlines()[0][:120]
    first = "".join(cells[index]["source"]).strip().splitlines()
    return first[0][:120] if first else ""


def load_notebook(path: Path, root: Path) -> NotebookInfo:
    raw = path.read_text(encoding="utf-8")
    notebook = json.loads(raw)
    cells = notebook["cells"]
    header_markdown = "".join(cells[0]["source"])
    version_match = re.search(r"\*\*Workshop version:\*\*\s*([0-9][0-9.]*)", header_markdown)
    purpose_lines = [
        line.strip()
        for line in header_markdown.splitlines()
        if line.strip() and not line.startswith("#") and not line.startswith("**")
    ]
    parameter_cell_index = next(
        (i for i, cell in enumerate(cells[:4]) if cell["cell_type"] == "code"), None
    )
    parameters: dict[str, Any] = {}
    if parameter_cell_index is not None:
        parameters = _parse_parameter_cell("".join(cells[parameter_cell_index]["source"]))

    parsed_cells: list[NotebookCell] = []
    for index, cell in enumerate(cells):
        source = "".join(cell["source"])
        lines = source.splitlines()
        parsed_cells.append(
            NotebookCell(
                number=index + 1,
                index=index,
                cell_type=cell["cell_type"],
                heading=_cell_heading(cells, index),
                first_line=lines[0] if lines else "",
                source_lines=len(lines),
                is_parameter_cell=index == parameter_cell_index,
                source_sha256=sha256_text(source),
            )
        )

    return NotebookInfo(
        name=path.stem,
        path=path,
        relative_path=path.relative_to(root).as_posix(),
        sha256=sha256_file(path),
        version=version_match.group(1) if version_match else "",
        purpose=purpose_lines[0] if purpose_lines else "",
        header_markdown=header_markdown,
        cells=tuple(parsed_cells),
        parameters=parameters,
    )


def _load_ontology(
    template: dict[str, Any], semantic: dict[str, Any]
) -> tuple[list[OntologyEntity], list[OntologyRelationship]]:
    parts = {part["path"]: part["content"] for part in template["parts"]}
    entity_defs: dict[str, dict[str, Any]] = {}
    entity_bindings: dict[str, list[dict[str, Any]]] = {}
    relationship_defs: dict[str, dict[str, Any]] = {}
    relationship_contexts: dict[str, dict[str, Any]] = {}

    for path, content in parts.items():
        segments = path.split("/")
        if segments[0] == "EntityTypes" and len(segments) >= 3:
            entity_id = segments[1]
            if segments[2] == "definition.json":
                entity_defs[entity_id] = content
            elif segments[2] == "DataBindings":
                entity_bindings.setdefault(entity_id, []).append(content)
        elif segments[0] == "RelationshipTypes" and len(segments) >= 3:
            relationship_id = segments[1]
            if segments[2] == "definition.json":
                relationship_defs[relationship_id] = content
            elif segments[2] == "Contextualizations":
                relationship_contexts[relationship_id] = content

    property_names: dict[str, str] = {}
    for definition in entity_defs.values():
        for prop in definition.get("properties", []):
            property_names[prop["id"]] = prop["name"]
    # The single time-series Property is created by its data binding, so it is not
    # part of any EntityType definition. Recover its name from the semantic manifest
    # and attach it to the unresolved target property id of the time-series binding.
    timeseries_names = [
        name
        for entity in (semantic.get("entities") or {}).values()
        for name in (entity.get("timeseriesProperties") or {})
    ]
    for bindings in entity_bindings.values():
        for binding in bindings:
            configuration = binding["dataBindingConfiguration"]
            if configuration["dataBindingType"] != "TimeSeries":
                continue
            for item in configuration["propertyBindings"]:
                if item["targetPropertyId"] not in property_names and len(timeseries_names) == 1:
                    property_names[item["targetPropertyId"]] = timeseries_names[0]

    entities: list[OntologyEntity] = []
    for entity_id, definition in entity_defs.items():
        key_ids = set(definition.get("entityIdParts") or [])
        display_id = definition.get("displayNamePropertyId")
        properties = tuple(
            OntologyProperty(
                name=prop["name"],
                value_type=prop.get("valueType", ""),
                description=(prop.get("semanticEnrichment") or {}).get("description", ""),
                attributes=dict(((prop.get("semanticEnrichment") or {}).get("customAttributes") or {})),
                is_key=prop["id"] in key_ids,
                is_display_name=prop["id"] == display_id,
            )
            for prop in definition.get("properties", [])
        )
        bindings: list[OntologyBinding] = []
        for binding in entity_bindings.get(entity_id, []):
            configuration = binding["dataBindingConfiguration"]
            table = configuration["sourceTableProperties"]
            bindings.append(
                OntologyBinding(
                    binding_type=configuration["dataBindingType"],
                    source_type=table["sourceType"],
                    source_table=table["sourceTableName"],
                    timestamp_column=configuration.get("timestampColumnName"),
                    column_map=tuple(
                        (item["sourceColumnName"], property_names.get(item["targetPropertyId"], ""))
                        for item in configuration["propertyBindings"]
                    ),
                )
            )
        enrichment = definition.get("semanticEnrichment") or {}
        semantic_entity = (semantic.get("entities") or {}).get(definition["name"], {})
        semantic_enrichment = semantic_entity.get("semanticEnrichment") or {}
        timeseries_properties = tuple(
            OntologyProperty(
                name=ts_name,
                value_type=ts_body.get("valueType", ""),
                description=(ts_body.get("semanticEnrichment") or {}).get("description", ""),
                attributes=dict(((ts_body.get("semanticEnrichment") or {}).get("customAttributes") or {})),
                is_key=False,
                is_display_name=False,
            )
            for ts_name, ts_body in (semantic_entity.get("timeseriesProperties") or {}).items()
        )
        entities.append(
            OntologyEntity(
                name=definition["name"],
                key_property=next((p.name for p in properties if p.is_key), ""),
                display_name_property=next((p.name for p in properties if p.is_display_name), ""),
                description=enrichment.get("description", ""),
                attributes=dict(enrichment.get("customAttributes") or {}),
                properties=properties,
                bindings=tuple(sorted(bindings, key=lambda b: b.binding_type != "NonTimeSeries")),
                synonyms=tuple(semantic_enrichment.get("synonyms") or ()),
                timeseries_properties=timeseries_properties,
            )
        )

    entity_names = {entity_id: definition["name"] for entity_id, definition in entity_defs.items()}
    relationships: list[OntologyRelationship] = []
    for relationship_id, definition in relationship_defs.items():
        context = relationship_contexts.get(relationship_id, {})
        enrichment = definition.get("semanticEnrichment") or {}
        source_bindings = context.get("sourceKeyRefBindings") or [{}]
        target_bindings = context.get("targetKeyRefBindings") or [{}]
        relationships.append(
            OntologyRelationship(
                name=definition["name"],
                origin=entity_names.get(definition["source"]["entityTypeId"], ""),
                target=entity_names.get(definition["target"]["entityTypeId"], ""),
                description=enrichment.get("description", ""),
                attributes=dict(enrichment.get("customAttributes") or {}),
                mapping_table=(context.get("dataBindingTable") or {}).get("sourceTableName", ""),
                origin_key_column=source_bindings[0].get("sourceColumnName", ""),
                target_key_column=target_bindings[0].get("sourceColumnName", ""),
            )
        )

    entity_order = [
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
    ]
    relationship_order = list(
        json.loads(json.dumps(list(RELATIONSHIP_ORDER)))
    )
    entities.sort(key=lambda e: entity_order.index(e.name) if e.name in entity_order else 99)
    relationships.sort(
        key=lambda r: relationship_order.index(r.name) if r.name in relationship_order else 99
    )
    return entities, relationships


RELATIONSHIP_ORDER = (
    "MunicipalityInPrefecture",
    "DonorLivesInPrefecture",
    "SupplierInPrefecture",
    "GiftInCategory",
    "MunicipalityCatalogsGift",
    "SupplierProvidesGift",
    "DonorMadeDonation",
    "DonationToMunicipality",
    "DonationSelectedGift",
    "MunHasCategoryMetric",
    "MunMetricForCategory",
    "PrefHasCategoryMetric",
    "PrefMetricForCategory",
    "ResidencePrefHasFlow",
    "FlowToRecipientPref",
)

DIAGRAM_KEYS = (
    "rdb-bi-ontology-mental-model",
    "rdb-to-ontology-decision-tree",
    "furusato-ontology-layers",
    "system-data-flow",
    "data-agent-source-routing",
    "ontology-data-agent-poc-production",
    "ontology-authoring-evaluation-lifecycle",
)


def _unified_builder(root: Path):
    path = root / "tools" / "provisioning" / "unified_agent.py"
    module = types.ModuleType("_furusato_docs_unified_agent")
    module.__file__ = str(path)
    exec(compile(path.read_bytes(), str(path), "exec"), module.__dict__)
    return module


def _load_sealed_unified_assets(context: RuntimeContext) -> dict[str, Any]:
    """Read the document profile from the sealed bundle, never from a tenant.

    Rebuild with the pure profile API to verify the packaged profile against its
    original source contracts. No AIPath definition is read or required here.
    """
    bundle = context.root / "workshop" / f"v{context.version}" / "provisioning" / "bundle"

    def text(relative: str) -> str:
        return (bundle / relative).read_bytes().decode("utf-8")

    try:
        sealed = json.loads(text("unified-agent/contract.json"))
        module = _unified_builder(context.root)
        expected_files = {
            "unified-agent/profile.json", "unified-agent/modules/unified_agent.py",
            *("unified-agent/inputs/" + name for name in (
                "manifest.json", *module.INSTRUCTION_FILES.values(), module.KQL_FEWSHOTS_FILE,
            )),
        }
        if (
            sealed.get("schemaVersion") != "furusato-unified-agent-runtime/v1"
            or sealed.get("teachingOntologyShape") != [10, 72, 1, 15]
            or sealed.get("createsAIPath") is not False
            or sealed.get("agentNameTemplate") != context.names["dataAgent"]
            or sealed.get("codeInterpreterEnabled") is not True
            or sealed.get("acceptanceClaimed") is not False
            or set(sealed.get("files", {})) != expected_files
        ):
            raise ValueError("Unified document bundle inventory or source contract differs.")
        for name, digest in sealed["files"].items():
            if sha256_text(text(name)) != digest:
                raise ValueError(f"Unified document asset hash mismatch: {name}")
        canonical_module = context.root / "tools" / "provisioning" / "unified_agent.py"
        if text("unified-agent/modules/unified_agent.py").encode("utf-8") != canonical_module.read_bytes():
            raise ValueError("The sealed and canonical unified profile builders differ; reseal first.")
        core_path = sealed.get("coreOntologySourcePath", "")
        if core_path not in {
            path.relative_to(bundle).as_posix()
            for path in (bundle / "data-agent" / "Files" / "Config" / "published").glob("*/datasource.json")
        } or sha256_text(text(core_path)) != sealed.get("coreOntologySourceSha256"):
            raise ValueError("The sealed teaching Ontology source does not match Core.")
        core = json.loads(text(core_path))
        if core != context.agent_sources["ontology"]:
            raise ValueError("The unified profile does not use the guide's full teaching source.")
        reference_contract_text = text("ai-reference/contract.json")
        if sha256_text(reference_contract_text) != sealed.get("referenceContractSha256"):
            raise ValueError("The shared reference helper contract changed after sealing.")
        contract = json.loads(reference_contract_text)
        for names in (contract["sqlDdlOrder"], contract["kqlFunctions"], contract["modules"]):
            if not all(
                isinstance(name, str) and name not in {".", ".."}
                and re.fullmatch(r"[A-Za-z0-9_.-]+", name)
                for name in names
            ):
                raise ValueError("Reference helper names must be plain file identifiers.")
        sources_text = text("ai-reference/source-metadata.json")
        if sha256_text(sources_text) != contract["files"].get("ai-reference/source-metadata.json"):
            raise ValueError("The shared source metadata hash differs.")
        stage = copy.deepcopy(context.agent_stage_config)
        stage["aiInstructions"] = text("ai-reference/global-instructions.txt")
        reference = {
            "contract": contract,
            "globalProfile": json.loads(text("ai-reference/global-profile.json")),
            "stageConfig": stage,
            "sources": json.loads(sources_text),
            "sqlDdl": tuple((name, text("ai-reference/sql/" + name)) for name in contract["sqlDdlOrder"]),
            "kqlFunctions": {name: text("ai-reference/kql/" + name + ".kql") for name in contract["kqlFunctions"]},
            "moduleSources": {name: text("ai-reference/modules/" + name + ".py") for name in contract["modules"]},
        }
        profile_files = {
            name.rsplit("/", 1)[-1]: text(name)
            for name in expected_files if name.startswith("unified-agent/inputs/")
        }
        assets = module.build_unified_assets(
            reference, core, profile_files=profile_files
        )
        profile = json.loads(text("unified-agent/profile.json"))
        if profile != {name: assets[name] for name in (
            "stageConfig", "sources", "globalProfile", "publicationDescription"
        )}:
            raise ValueError("The sealed profile differs from its verified inputs.")
        return assets
    except (OSError, KeyError, UnicodeError) as error:
        raise ValueError(
            "The sealed unified-agent document profile is incomplete; finish the parent reseal first. "
            "Do not substitute legacy Core or canonical unsealed inputs."
        ) from error


def with_document_edition(
    context: RuntimeContext, edition: str, *, unified_assets: dict[str, Any] | None = None
) -> RuntimeContext:
    """Select guide content without changing the retained data/runtime baseline.

    The caller supplies the complete pure ``build_unified_assets`` result.
    ``load_context`` rebuilds this from the sealed document profile when needed.
    Missing unified assets never select Core.
    """
    if edition != UNIFIED_DOCUMENT_EDITION:
        if unified_assets is not None:
            raise ValueError("Unified assets require the unified document edition.")
        return replace(context, document_edition=edition, unified_profile=None)
    if unified_assets is None:
        raise ValueError(
            "unified-20260914 requires verified unified_assets from the sealed bundle; "
            "Core instructions are not a fallback."
        )
    _unified_builder(context.root).verify_unified_assets(unified_assets)
    contract = unified_assets["contract"]
    if contract["expectedOntologyContract"] != context.ontology_contract:
        raise ValueError("The guide and unified profile must use the same full teaching Ontology.")
    instructions = unified_assets["stageConfig"]["aiInstructions"]
    if len(instructions) >= int(context.workspace_contract["dataAgent"]["globalInstructionsCharLimit"]):
        raise ValueError("Unified GLOBAL must remain below the workshop instruction budget.")
    if unified_assets["sources"]["lakehouse_tables"]["fewShots"]["fewShots"] != context.agent_fewshots:
        raise ValueError("The unified guide must preserve the original held-out-safe SQL examples.")
    profile = AgentGuideProfile(
        instructions=instructions,
        stage_config=copy.deepcopy(unified_assets["stageConfig"]),
        sources=copy.deepcopy(unified_assets["sources"]),
        contract=copy.deepcopy(contract),
        instruction_relative_path=f"workshop/v{context.version}/provisioning/bundle/unified-agent/inputs/global-instructions.txt",
    )
    return replace(context, document_edition=edition, unified_profile=profile)


def load_context(
    root: Path | None = None, *, document_edition: str = "", unified_assets: dict[str, Any] | None = None
) -> RuntimeContext:
    root = root or repo_root()
    workshop = root / "workshop" / "v2.7.0"
    version = (root / "VERSION").read_text(encoding="utf-8").strip()

    dataset_manifest = json.loads((workshop / "data" / "dataset-manifest.json").read_text("utf-8"))
    workspace_contract = json.loads((workshop / "participant-workspace-contract.json").read_text("utf-8"))

    checksums: dict[str, str] = {}
    for line in (workshop / "data" / "SHA256SUMS.txt").read_text("utf-8").splitlines():
        if not line.strip():
            continue
        digest, name = line.split(maxsplit=1)
        checksums[name.strip()] = digest

    agent_instructions = (workshop / "data-agent" / "agent-instructions.txt").read_text("utf-8")
    published = workshop / "provisioning" / "bundle" / "data-agent" / "Files" / "Config" / "published"
    stage_config = json.loads((published / "stage_config.json").read_text("utf-8"))

    agent_sources: dict[str, dict[str, Any]] = {}
    for folder in sorted(published.iterdir()):
        if folder.is_dir() and (folder / "datasource.json").is_file():
            payload = json.loads((folder / "datasource.json").read_text("utf-8"))
            agent_sources[payload["type"]] = payload

    fewshots_path = next(published.glob("lakehouse-tables-*/fewshots.json"))
    agent_fewshots = json.loads(fewshots_path.read_text("utf-8"))["fewShots"]

    pipeline = json.loads(
        (workshop / "provisioning" / "bundle" / "data-pipeline" / "pipeline-content.json").read_text("utf-8")
    )
    kql_setup = (workshop / "kql" / f"Furusato_Eventhouse_Setup_v{version}.kql").read_text("utf-8")

    notebooks: dict[str, NotebookInfo] = {}
    for path in sorted((workshop / "notebooks").glob("Notebook_*.ipynb")):
        info = load_notebook(path, root)
        notebooks[info.name[:11]] = info

    template = json.loads((workshop / "ontology" / "ontology-full-definition-template.json").read_text("utf-8"))
    semantic = json.loads((workshop / "ontology" / "ontology-semantic-metadata.json").read_text("utf-8"))
    entities, relationships = _load_ontology(template, semantic)

    diagrams: dict[str, dict[str, Path]] = {}
    assets = root / "docs" / "assets" / f"v{version}"
    for key in DIAGRAM_KEYS:
        entry: dict[str, Path] = {}
        for suffix in ("svg", "png"):
            candidate = assets / f"{key}.{suffix}"
            if candidate.is_file():
                entry[suffix] = candidate
        if entry:
            diagrams[key] = entry

    library_root = workshop / "variable-library-template"
    variable_library: dict[str, Any] = {}
    value_sets: list[str] = []
    if (library_root / "variables.json").is_file():
        variable_library = json.loads((library_root / "variables.json").read_text("utf-8"))
    if (library_root / "settings.json").is_file():
        value_sets = list(json.loads((library_root / "settings.json").read_text("utf-8")).get("valueSetsOrder", []))

    context = RuntimeContext(
        root=root,
        version=version,
        dataset_manifest=dataset_manifest,
        workspace_contract=workspace_contract,
        checksums=checksums,
        agent_instructions=agent_instructions,
        agent_stage_config=stage_config,
        agent_sources=agent_sources,
        agent_fewshots=agent_fewshots,
        pipeline=pipeline,
        kql_setup=kql_setup,
        notebooks=notebooks,
        entities=entities,
        relationships=relationships,
        ontology_contract=template["expectedContract"],
        semantic_manifest=semantic,
        variable_library=variable_library,
        variable_library_value_sets=value_sets,
        diagrams=diagrams,
    )
    if document_edition == UNIFIED_DOCUMENT_EDITION and unified_assets is None:
        unified_assets = _load_sealed_unified_assets(context)
    return with_document_edition(context, document_edition, unified_assets=unified_assets)


def yen(value: int | float) -> str:
    return f"{int(value):,} 円"


def num(value: int | float) -> str:
    return f"{int(value):,}"


#: Every runtime file the document build reads. The build records a fingerprint of
#: these so a report always states exactly which on-disk runtime produced the docs.
RUNTIME_INPUT_GLOBS = (
    "VERSION",
    "workshop/v{version}/participant-workspace-contract.json",
    "workshop/v{version}/data/dataset-manifest.json",
    "workshop/v{version}/data/SHA256SUMS.txt",
    "workshop/v{version}/data/seed/*.csv",
    "workshop/v{version}/data/increment/*.csv",
    "workshop/v{version}/data-agent/agent-instructions.txt",
    "workshop/v{version}/kql/*.kql",
    "workshop/v{version}/notebooks/*.ipynb",
    "workshop/v{version}/ontology/*.json",
    "workshop/v{version}/provisioning/bundle/data-agent/Files/Config/**/*.json",
    "workshop/v{version}/provisioning/bundle/data-pipeline/*.json",
    "workshop/v{version}/variable-library-template/*.json",
    "workshop/v{version}/variable-library-template/valueSets/*.json",
    "docs/assets/v{version}/*.png",
)


def runtime_fingerprint(context: "RuntimeContext") -> dict[str, Any]:
    """Return a per-file and combined digest of everything the build consumes."""
    files: dict[str, str] = {}
    for pattern in RUNTIME_INPUT_GLOBS:
        resolved = pattern.format(version=context.version)
        if "*" in resolved:
            matches = sorted(context.root.glob(resolved))
        else:
            candidate = context.root / resolved
            matches = [candidate] if candidate.is_file() else []
        for path in matches:
            if path.is_file():
                files[path.relative_to(context.root).as_posix()] = sha256_file(path)
    profile: dict[str, str] = {}
    if context.is_unified_guide:
        profile = {
            "documentEdition": context.document_edition,
            "guideProfileSha256": context.guide_profile.contract["sha256"],
        }
    inputs = {"files": files, **profile} if profile else files
    combined = hashlib.sha256(
        json.dumps(inputs, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return {"fileCount": len(files), "combinedSha256": combined, "files": files, **profile}
