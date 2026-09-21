"""Build a private, offline-only Furusato path-focused Ontology candidate.

The transformer is intentionally fail-closed.  It accepts the current Fabric
``getDefinition`` envelope, validates every supported part and reference, and
emits a fresh private candidate directory.  It never authenticates, calls a
service, deploys an item, or claims that a structurally valid candidate has
been accepted by a Data Agent.
"""

from __future__ import annotations

import argparse
import base64
import binascii
import copy
import hashlib
import json
import re
import stat
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

REPOSITORY = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY / "tools" / "docs"))
from furusato_docs.publication import outside_repo, safe_path  # noqa: E402

SCHEMA_VERSION = "furusato-path-ontology/v1"
SHA256 = re.compile(r"^[0-9a-f]{64}$")
ALLOWED_VALUE_TYPES = {"String", "Boolean", "DateTime", "Object", "BigInt", "Double"}
KEY_VALUE_TYPES = {"String", "BigInt"}
ENTITY_NAMES = {
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
}
RELATIONSHIP_NAMES = {
    "MunicipalityInPrefecture",
    "DonorLivesInPrefecture",
    "SupplierInPrefecture",
    "GiftInCategory",
    "SupplierProvidesGift",
    "DonorMadeDonation",
    "DonationToMunicipality",
    "DonationSelectedGift",
    "MunicipalityCatalogsGift",
    "MunHasCategoryMetric",
    "MunMetricForCategory",
    "PrefHasCategoryMetric",
    "PrefMetricForCategory",
    "ResidencePrefHasFlow",
    "FlowToRecipientPref",
}

# A display composite is useful as an endpoint label, while the underlying name
# is the minimal scalar required for exact name lookup.  Entities not listed
# here need only their key and configured display property.
EXACT_LOOKUP_PROPERTIES = {
    "Municipality": {"MunicipalityName"},
    "Donor": {"DonorName"},
    "Gift": {"GiftName"},
    "Supplier": {"SupplierName"},
}

ENTITY_DEFINITION = re.compile(r"^EntityTypes/([1-9][0-9]*)/definition\.json$")
DATA_BINDING = re.compile(
    r"^EntityTypes/([1-9][0-9]*)/DataBindings/"
    r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\.json$"
)
OVERVIEW = re.compile(r"^EntityTypes/([1-9][0-9]*)/Overviews/definition\.json$")
RELATIONSHIP_DEFINITION = re.compile(
    r"^RelationshipTypes/([1-9][0-9]*)/definition\.json$"
)
CONTEXTUALIZATION = re.compile(
    r"^RelationshipTypes/([1-9][0-9]*)/Contextualizations/"
    r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\.json$"
)
SOURCE_COLUMN_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
OVERVIEW_FIELDS = {"$schema", "widgets", "settings"}


class OutputWriteError(OSError):
    """A reserved output directory contains a retained failed write."""


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def reject_duplicate_members(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, child in pairs:
        if key in value:
            raise ValueError(f"Duplicate JSON object member: {key}")
        value[key] = child
    return value


def strict_json_loads(raw: str | bytes) -> Any:
    try:
        return json.loads(raw, object_pairs_hook=reject_duplicate_members)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("Invalid UTF-8 JSON") from error


def canonical_path(path: Any) -> str:
    if not isinstance(path, str) or not path:
        raise ValueError("Definition part paths must be nonempty strings")
    logical = PurePosixPath(path)
    if (
        "\\" in path
        or logical.is_absolute()
        or ".." in logical.parts
        or str(logical) != path
        or path == "."
    ):
        raise ValueError(f"Ambiguous or noncanonical definition part path: {path!r}")
    return path


def classify_path(path: str) -> tuple[str, tuple[str, ...]]:
    if path == "definition.json":
        return "root", ()
    if path == ".platform":
        return "platform", ()
    for kind, pattern in (
        ("entity", ENTITY_DEFINITION),
        ("binding", DATA_BINDING),
        ("overview", OVERVIEW),
        ("relationship", RELATIONSHIP_DEFINITION),
        ("contextualization", CONTEXTUALIZATION),
    ):
        match = pattern.fullmatch(path)
        if match:
            return kind, match.groups()
    raise ValueError(f"Unhandled Ontology definition part path: {path}")


def decode_parts(envelope: dict[str, Any]) -> dict[str, bytes]:
    if not isinstance(envelope, dict):
        raise ValueError("The Fabric definition envelope must be an object")
    definition = envelope.get("definition")
    if not isinstance(definition, dict):
        raise ValueError("The Fabric definition envelope requires definition")
    parts = definition.get("parts")
    if not isinstance(parts, list) or not parts:
        raise ValueError("The Fabric definition envelope requires nonempty definition.parts")

    decoded: dict[str, bytes] = {}
    for part in parts:
        if not isinstance(part, dict):
            raise ValueError("Every definition part must be an object")
        path = canonical_path(part.get("path"))
        classify_path(path)
        if path in decoded:
            raise ValueError(f"Duplicate definition part path: {path}")
        if part.get("payloadType") != "InlineBase64":
            raise ValueError(f"Unsupported payloadType in {path}")
        payload = part.get("payload")
        if not isinstance(payload, str):
            raise ValueError(f"Missing base64 payload in {path}")
        try:
            decoded[path] = base64.b64decode(payload, validate=True)
        except (binascii.Error, ValueError) as error:
            raise ValueError(f"Invalid base64 payload in {path}") from error
    return decoded


def json_part(path: str, raw: bytes) -> dict[str, Any]:
    try:
        value = strict_json_loads(raw)
    except ValueError as error:
        raise ValueError(f"Definition part is not valid UTF-8 JSON: {path}") from error
    if not isinstance(value, dict):
        raise ValueError(f"Definition part must contain one JSON object: {path}")
    return value


def require_guid(value: Any, label: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{label} must be a GUID string")
    try:
        parsed = uuid.UUID(value)
    except ValueError as error:
        raise ValueError(f"{label} must be a GUID string") from error
    if str(parsed) != value:
        raise ValueError(f"{label} must be a canonical lowercase GUID")
    return value


def require_id(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.isdigit() or value.startswith("0"):
        raise ValueError(f"{label} must be a positive decimal 64-bit ID string")
    number = int(value)
    if not 0 < number < 2**63:
        raise ValueError(f"{label} is outside the positive signed 64-bit range")
    return value


def require_source_column(value: Any, label: str) -> str:
    if not isinstance(value, str) or not SOURCE_COLUMN_NAME.fullmatch(value):
        raise ValueError(f"{label} must be a nonempty unambiguous source-column identifier")
    return value


@dataclass
class Model:
    decoded: dict[str, bytes]
    values: dict[str, dict[str, Any]]
    entities: dict[str, dict[str, Any]]
    entity_paths: dict[str, str]
    properties: dict[str, dict[str, dict[str, Any]]]
    bindings: dict[str, list[tuple[str, dict[str, Any]]]]
    relationships: dict[str, dict[str, Any]]
    relationship_paths: dict[str, str]
    contextualizations: dict[str, list[tuple[str, dict[str, Any]]]]
    overviews: list[str]


def parse_model(envelope: dict[str, Any]) -> Model:
    decoded = decode_parts(envelope)
    values = {path: json_part(path, raw) for path, raw in decoded.items()}
    if set(path for path in decoded if path in {"definition.json", ".platform"}) != {
        "definition.json",
        ".platform",
    }:
        raise ValueError("Ontology definition requires exactly definition.json and .platform")
    if values["definition.json"] != {}:
        raise ValueError("Ontology definition.json must be the empty object")
    platform = values[".platform"]
    metadata = platform.get("metadata")
    if not isinstance(metadata, dict) or metadata.get("type") != "Ontology":
        raise ValueError(".platform must declare metadata.type Ontology")
    if not isinstance(metadata.get("displayName"), str) or not metadata["displayName"].strip():
        raise ValueError(".platform requires a nonempty metadata.displayName")

    entities: dict[str, dict[str, Any]] = {}
    entity_paths: dict[str, str] = {}
    properties: dict[str, dict[str, dict[str, Any]]] = {}
    bindings_by_id: dict[str, list[tuple[str, dict[str, Any]]]] = {}
    relationships: dict[str, dict[str, Any]] = {}
    relationship_paths: dict[str, str] = {}
    contextualizations_by_id: dict[str, list[tuple[str, dict[str, Any]]]] = {}
    overviews: list[str] = []
    global_ids: dict[str, str] = {}
    global_property_types: dict[str, tuple[str, str]] = {}

    for path, value in values.items():
        kind, groups = classify_path(path)
        if kind == "entity":
            folder_id = require_id(groups[0], f"Entity folder ID in {path}")
            entity_id = require_id(value.get("id"), f"Entity ID in {path}")
            if folder_id != entity_id:
                raise ValueError(f"Entity folder ID does not match payload ID in {path}")
            name = value.get("name")
            if not isinstance(name, str) or name in entities:
                raise ValueError(f"Missing or duplicate entity name in {path}")
            if entity_id in global_ids:
                raise ValueError(f"Duplicate Ontology ID {entity_id} in {path}")
            global_ids[entity_id] = path
            entity_properties: dict[str, dict[str, Any]] = {}
            property_names: set[str] = set()
            for collection in ("properties", "timeseriesProperties", "untypedProperties"):
                entries = value.get(collection, [])
                if not isinstance(entries, list):
                    raise ValueError(f"{collection} must be an array in {path}")
                for prop in entries:
                    if not isinstance(prop, dict):
                        raise ValueError(f"{collection} contains a nonobject in {path}")
                    prop_id = require_id(prop.get("id"), f"Property ID in {path}")
                    prop_name = prop.get("name")
                    value_type = prop.get("valueType")
                    allowed = {"Any"} if collection == "untypedProperties" else ALLOWED_VALUE_TYPES
                    if not isinstance(prop_name, str) or not prop_name:
                        raise ValueError(f"Property name is missing in {path}")
                    if value_type not in allowed:
                        raise ValueError(f"Unsupported property valueType in {path}: {value_type}")
                    if prop_id in global_ids:
                        raise ValueError(f"Duplicate property ID {prop_id} in {path}")
                    if prop_name in property_names:
                        raise ValueError(f"Duplicate property name {prop_name} in {path}")
                    previous_type = global_property_types.get(prop_name)
                    if previous_type and previous_type[0] != value_type:
                        raise ValueError(
                            f"Property name {prop_name} has conflicting value types "
                            f"{previous_type[0]} and {value_type} across entities"
                        )
                    global_ids[prop_id] = path
                    property_names.add(prop_name)
                    global_property_types.setdefault(prop_name, (value_type, path))
                    entity_properties[prop_id] = {
                        "value": prop,
                        "collection": collection,
                    }
            entities[name] = value
            entity_paths[name] = path
            properties[entity_id] = entity_properties
        elif kind == "binding":
            entity_id, path_guid = groups
            require_guid(path_guid, f"Binding path ID in {path}")
            payload_guid = require_guid(value.get("id"), f"Binding payload ID in {path}")
            if path_guid != payload_guid:
                raise ValueError(f"Binding path ID does not match payload ID in {path}")
            bindings_by_id.setdefault(entity_id, []).append((path, value))
        elif kind == "relationship":
            folder_id = require_id(groups[0], f"Relationship folder ID in {path}")
            relationship_id = require_id(value.get("id"), f"Relationship ID in {path}")
            if folder_id != relationship_id:
                raise ValueError(f"Relationship folder ID does not match payload ID in {path}")
            name = value.get("name")
            if not isinstance(name, str) or name in relationships:
                raise ValueError(f"Missing or duplicate relationship name in {path}")
            if relationship_id in global_ids:
                raise ValueError(f"Duplicate Ontology ID {relationship_id} in {path}")
            global_ids[relationship_id] = path
            relationships[name] = value
            relationship_paths[name] = path
        elif kind == "contextualization":
            relationship_id, path_guid = groups
            require_guid(path_guid, f"Contextualization path ID in {path}")
            payload_guid = require_guid(value.get("id"), f"Contextualization payload ID in {path}")
            if path_guid != payload_guid:
                raise ValueError(f"Contextualization path ID does not match payload ID in {path}")
            contextualizations_by_id.setdefault(relationship_id, []).append((path, value))
        elif kind == "overview":
            overviews.append(path)

    if set(entities) != ENTITY_NAMES:
        raise ValueError(
            f"Expected the ten canonical Furusato entities; got {sorted(entities)}"
        )
    if set(relationships) != RELATIONSHIP_NAMES:
        raise ValueError(
            f"Expected the fifteen canonical Furusato relationships; got {sorted(relationships)}"
        )

    entity_ids = {value["id"]: name for name, value in entities.items()}
    for name, entity in entities.items():
        entity_id = entity["id"]
        key_ids = entity.get("entityIdParts")
        display_id = entity.get("displayNamePropertyId")
        if not isinstance(key_ids, list) or not key_ids:
            raise ValueError(f"{name} must retain at least one entity key")
        if not isinstance(display_id, str):
            raise ValueError(f"{name} must retain a displayNamePropertyId")
        for key_id in key_ids:
            if key_id not in properties[entity_id]:
                raise ValueError(f"{name} key references a missing property: {key_id}")
            value_type = properties[entity_id][key_id]["value"]["valueType"]
            if value_type not in KEY_VALUE_TYPES:
                raise ValueError(f"{name} key property has unsupported type {value_type}")
        if display_id not in properties[entity_id]:
            raise ValueError(f"{name} display name references a missing property: {display_id}")

        static_count = 0
        for path, binding in bindings_by_id.get(entity_id, []):
            config = binding.get("dataBindingConfiguration")
            if not isinstance(config, dict):
                raise ValueError(f"Missing dataBindingConfiguration in {path}")
            binding_type = config.get("dataBindingType")
            if binding_type not in {"NonTimeSeries", "TimeSeries"}:
                raise ValueError(f"Unknown dataBindingType in {path}")
            source = config.get("sourceTableProperties")
            if not isinstance(source, dict):
                raise ValueError(f"Missing sourceTableProperties in {path}")
            source_type = source.get("sourceType")
            if binding_type == "NonTimeSeries":
                static_count += 1
                if source_type != "LakehouseTable":
                    raise ValueError(f"NonTimeSeries binding is not Lakehouse-backed: {path}")
            elif source_type not in {"LakehouseTable", "KustoTable"}:
                raise ValueError(f"Unsupported TimeSeries source in {path}")
            mappings = config.get("propertyBindings")
            if not isinstance(mappings, list):
                raise ValueError(f"propertyBindings must be an array in {path}")
            seen_targets: set[str] = set()
            for mapping in mappings:
                if not isinstance(mapping, dict):
                    raise ValueError(f"Nonobject property binding in {path}")
                target = mapping.get("targetPropertyId")
                if target not in properties[entity_id]:
                    raise ValueError(f"Binding references unknown property {target} in {path}")
                if target in seen_targets:
                    raise ValueError(f"Binding maps property {target} more than once in {path}")
                require_source_column(
                    mapping.get("sourceColumnName"),
                    f"Binding source column in {path}",
                )
                seen_targets.add(target)
        if static_count != 1:
            raise ValueError(f"{name} must have exactly one NonTimeSeries binding")

    for name, relationship in relationships.items():
        relationship_id = relationship["id"]
        source = relationship.get("source")
        target = relationship.get("target")
        if not isinstance(source, dict) or not isinstance(target, dict):
            raise ValueError(f"{name} is missing source or target")
        source_id = source.get("entityTypeId")
        target_id = target.get("entityTypeId")
        if source_id not in entity_ids or target_id not in entity_ids or source_id == target_id:
            raise ValueError(f"{name} has invalid entity endpoints")
        contexts = contextualizations_by_id.get(relationship_id, [])
        if len(contexts) != 1:
            raise ValueError(f"{name} must have exactly one contextualization")
        context_path, context = contexts[0]
        table = context.get("dataBindingTable")
        if not isinstance(table, dict) or table.get("sourceType") != "LakehouseTable":
            raise ValueError(f"{name} contextualization must use a Lakehouse table")
        for field, endpoint_id in (
            ("sourceKeyRefBindings", source_id),
            ("targetKeyRefBindings", target_id),
        ):
            mappings = context.get(field)
            if not isinstance(mappings, list) or not mappings:
                raise ValueError(f"{field} is missing in {context_path}")
            targets = []
            for mapping in mappings:
                if not isinstance(mapping, dict):
                    raise ValueError(f"Nonobject {field} entry in {context_path}")
                require_source_column(
                    mapping.get("sourceColumnName"),
                    f"Contextualization source column in {context_path}",
                )
                targets.append(mapping.get("targetPropertyId"))
            if targets != entities[entity_ids[endpoint_id]]["entityIdParts"]:
                raise ValueError(
                    f"{name} {field} must map the endpoint key in declared key order"
                )

    for relationship_id in contextualizations_by_id:
        if relationship_id not in {value["id"] for value in relationships.values()}:
            raise ValueError(
                f"Contextualization belongs to unknown relationship {relationship_id}"
            )
    for entity_id in bindings_by_id:
        if entity_id not in entity_ids:
            raise ValueError(f"Data binding belongs to unknown entity {entity_id}")
    for path in overviews:
        entity_id = OVERVIEW.fullmatch(path).group(1)  # type: ignore[union-attr]
        if entity_id not in entity_ids:
            raise ValueError(f"Overview belongs to unknown entity {entity_id}")
        overview = values[path]
        unexpected_fields = set(overview) - OVERVIEW_FIELDS
        if unexpected_fields:
            raise ValueError(
                f"Unassessed Overview fields cannot be omitted from {path}: "
                f"{sorted(unexpected_fields)}"
            )
        if overview.get("widgets") != [] or overview.get("settings") is not None:
            raise ValueError(
                f"Nonempty Overview semantics are unsupported by this path-only transform: {path}"
            )

    return Model(
        decoded=decoded,
        values=values,
        entities=entities,
        entity_paths=entity_paths,
        properties=properties,
        bindings=bindings_by_id,
        relationships=relationships,
        relationship_paths=relationship_paths,
        contextualizations=contextualizations_by_id,
        overviews=overviews,
    )


def validate_expected_source_shape(model: Model) -> tuple[str, str]:
    expected_counts = {
        "parts": 54,
        "entities": 10,
        "staticProperties": 72,
        "timeseriesProperties": 1,
        "dataBindings": 11,
        "propertyBindings": 74,
        "relationships": 15,
        "contextualizations": 15,
        "contextualizationKeyBindings": 30,
    }
    counts = model_counts(model)
    if counts != expected_counts:
        raise ValueError(
            f"Source is not the assessed canonical 54-part contract: {counts}"
        )

    municipality = model.entities["Municipality"]
    municipality_id = municipality["id"]
    if len(model.overviews) != 1:
        raise ValueError("Expected exactly one assessed empty Municipality Overview")
    overview_path = model.overviews[0]
    overview_owner = OVERVIEW.fullmatch(overview_path).group(1)  # type: ignore[union-attr]
    if overview_owner != municipality_id:
        raise ValueError("The only assessed Overview must belong to Municipality")

    timeseries_properties = [
        (name, prop)
        for name, entity in model.entities.items()
        for prop in entity.get("timeseriesProperties", [])
    ]
    if len(timeseries_properties) != 1:
        raise ValueError("Expected exactly one assessed time-series property")
    owner, timeseries_property = timeseries_properties[0]
    if (
        owner != "Municipality"
        or timeseries_property.get("name") != "IncomingDonationAmountYen"
        or timeseries_property.get("valueType") != "BigInt"
    ):
        raise ValueError(
            "The assessed time-series property must be Municipality."
            "IncomingDonationAmountYen (BigInt)"
        )

    timeseries_bindings = [
        (entity_id, path, value)
        for entity_id, entries in model.bindings.items()
        for path, value in entries
        if value["dataBindingConfiguration"]["dataBindingType"] == "TimeSeries"
    ]
    if len(timeseries_bindings) != 1:
        raise ValueError("Expected exactly one assessed TimeSeries binding")
    owner_id, binding_path, binding = timeseries_bindings[0]
    config = binding["dataBindingConfiguration"]
    source = config["sourceTableProperties"]
    if (
        owner_id != municipality_id
        or source.get("sourceType") != "KustoTable"
        or source.get("sourceTableName") != "DonationEvents"
    ):
        raise ValueError(
            "The assessed TimeSeries binding must be Municipality -> Kusto DonationEvents"
        )
    require_source_column(
        config.get("timestampColumnName"),
        f"TimeSeries timestamp column in {binding_path}",
    )
    expected_targets = {
        timeseries_property["id"],
        *municipality["entityIdParts"],
    }
    actual_targets = {
        mapping["targetPropertyId"] for mapping in config["propertyBindings"]
    }
    if actual_targets != expected_targets:
        raise ValueError(
            "The assessed TimeSeries binding must map only the Municipality key and "
            "IncomingDonationAmountYen"
        )
    return overview_path, binding_path


def model_counts(model: Model) -> dict[str, int]:
    static_properties = sum(
        len(entity.get("properties", [])) + len(entity.get("untypedProperties", []))
        for entity in model.entities.values()
    )
    timeseries_properties = sum(
        len(entity.get("timeseriesProperties", [])) for entity in model.entities.values()
    )
    bindings = [entry for entries in model.bindings.values() for entry in entries]
    property_bindings = sum(
        len(value["dataBindingConfiguration"].get("propertyBindings", []))
        for _, value in bindings
    )
    contexts = [
        entry for entries in model.contextualizations.values() for entry in entries
    ]
    contextualization_key_bindings = sum(
        len(value.get("sourceKeyRefBindings", []))
        + len(value.get("targetKeyRefBindings", []))
        for _, value in contexts
    )
    return {
        "parts": len(model.decoded),
        "entities": len(model.entities),
        "staticProperties": static_properties,
        "timeseriesProperties": timeseries_properties,
        "dataBindings": len(bindings),
        "propertyBindings": property_bindings,
        "relationships": len(model.relationships),
        "contextualizations": len(contexts),
        "contextualizationKeyBindings": contextualization_key_bindings,
    }


def property_inventory(model: Model) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for name, entity in sorted(model.entities.items()):
        result[name] = [
            prop["name"]
            for collection in ("properties", "timeseriesProperties", "untypedProperties")
            for prop in entity.get(collection, [])
        ]
    return result


def _semantic_strings(value: Any, path: str):
    if isinstance(value, dict):
        for key, child in value.items():
            yield f"{path}/{key}", "key", key
            yield from _semantic_strings(child, f"{path}/{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _semantic_strings(child, f"{path}/{index}")
    elif isinstance(value, str):
        yield path, "value", value


def semantic_reference_findings(
    entities: dict[str, dict[str, Any]],
    removed_properties: dict[str, list[dict[str, str]]],
) -> list[dict[str, Any]]:
    removed_names = {
        record["name"]: owner
        for owner, records in removed_properties.items()
        for record in records
    }
    findings: list[dict[str, Any]] = []
    for entity_name, entity in sorted(entities.items()):
        scopes = [("entity/semanticEnrichment", entity.get("semanticEnrichment", {}))]
        for collection in ("properties", "timeseriesProperties", "untypedProperties"):
            for prop in entity.get(collection, []):
                scopes.append(
                    (
                        f"{collection}/{prop['name']}/semanticEnrichment",
                        prop.get("semanticEnrichment", {}),
                    )
                )
        for scope, enrichment in scopes:
            for path, member_kind, text in _semantic_strings(enrichment, scope):
                matches = [
                    {"name": name, "ownerEntity": owner}
                    for name, owner in removed_names.items()
                    if re.search(
                        rf"(?<![A-Za-z0-9_]){re.escape(name)}(?![A-Za-z0-9_])",
                        text,
                    )
                ]
                if matches:
                    findings.append(
                        {
                            "retainingEntity": entity_name,
                            "path": path,
                            "memberKind": member_kind,
                            "removedProperties": matches,
                            "text": text,
                        }
                    )
    return findings


def repair_assessed_semantic_references(
    entities: dict[str, dict[str, Any]],
    removed_properties: dict[str, list[dict[str, str]]],
) -> dict[str, Any]:
    detected = semantic_reference_findings(entities, removed_properties)
    resolved: list[dict[str, Any]] = []
    donation = entities["Donation"]
    donation_id = next(
        prop for prop in donation["properties"] if prop["name"] == "DonationId"
    )
    enrichment = donation_id.get("semanticEnrichment")
    if not isinstance(enrichment, dict) or not isinstance(enrichment.get("description"), str):
        raise ValueError("DonationId requires its assessed semantic description")
    old_sentence = (
        "When a user says 寄付ID or Donation ID followed by a number, filter this "
        "property for exact identity; never reinterpret that number as DonationAmountYen."
    )
    new_sentence = (
        "When a user says 寄付ID or Donation ID followed by a number, filter this "
        "property for exact identity."
    )
    if old_sentence not in enrichment["description"]:
        raise ValueError("Assessed DonationId semantic description changed unexpectedly")
    enrichment["description"] = enrichment["description"].replace(
        old_sentence, new_sentence, 1
    )
    resolved.append(
        {
            "retainingEntity": "Donation",
            "path": "properties/DonationId/semanticEnrichment/description",
            "removedProperty": "DonationAmountYen",
            "action": "targeted sentence rewrite",
        }
    )
    unresolved = semantic_reference_findings(entities, removed_properties)
    if unresolved:
        raise ValueError(
            "Retained semantic metadata still references removed properties: "
            + ", ".join(
                f"{record['retainingEntity']}:{record['path']}"
                for record in unresolved
            )
        )
    return {
        "scannedScopes": [
            "entity semanticEnrichment including customAttributes and synonyms",
            "retained property semanticEnrichment including customAttributes",
        ],
        "detectedBeforeTargetedRepair": detected,
        "targetedRepairs": resolved,
        "unresolvedAfterRepair": unresolved,
    }


def repair_relationship_semantics(
    relationships: dict[str, dict[str, Any]],
    removed_properties: dict[str, list[dict[str, str]]],
    entity_names_by_id: dict[str, str],
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    removed_names = {
        record["name"]: owner
        for owner, records in removed_properties.items()
        for record in records
    }

    def references(value: Any) -> list[dict[str, str]]:
        matches: dict[str, str] = {}
        for _, _, text in _semantic_strings(value, "semanticEnrichment"):
            for property_name, owner in removed_names.items():
                if re.search(
                    rf"(?<![A-Za-z0-9_]){re.escape(property_name)}"
                    rf"(?![A-Za-z0-9_])",
                    text,
                ):
                    matches[property_name] = owner
        return [
            {"name": property_name, "ownerEntity": owner}
            for property_name, owner in sorted(matches.items())
        ]

    transformed = copy.deepcopy(relationships)
    detected: list[dict[str, Any]] = []
    repairs: list[dict[str, Any]] = []
    for name, relationship in sorted(transformed.items()):
        enrichment = relationship.get("semanticEnrichment")
        if enrichment is None:
            enrichment = {}
            relationship["semanticEnrichment"] = enrichment
        if not isinstance(enrichment, dict):
            raise ValueError(f"{name} semanticEnrichment must be an object when present")
        for path, member_kind, text in _semantic_strings(
            enrichment, "semanticEnrichment"
        ):
            hits = [
                {"name": property_name, "ownerEntity": owner}
                for property_name, owner in removed_names.items()
                if re.search(
                    rf"(?<![A-Za-z0-9_]){re.escape(property_name)}"
                    rf"(?![A-Za-z0-9_])",
                    text,
                )
            ]
            if hits:
                detected.append(
                    {
                        "relationship": name,
                        "path": path,
                        "memberKind": member_kind,
                        "removedProperties": hits,
                        "text": text,
                    }
                )

        source_name = entity_names_by_id[relationship["source"]["entityTypeId"]]
        target_name = entity_names_by_id[relationship["target"]["entityTypeId"]]
        description = enrichment.get("description")
        if not isinstance(description, str) or not description.strip():
            raise ValueError(f"{name} requires its existing business description")
        description_references = references(description)
        if description_references:
            if (
                name not in {"GiftInCategory", "SupplierProvidesGift"}
                or {hit["name"] for hit in description_references} != {"DonationAmountYen"}
            ):
                raise ValueError(f"Unassessed removed-property description in {name}")
            description = description.replace(
                "DonationAmountYen", "donation amounts from the governed SQL source"
            )
        enrichment["description"] = description + (
            f" Candidate-only directed path from {source_name} to {target_name}. "
            "Use the declared relationship and contextualization keys for traversal, "
            "resolve endpoint keys exactly, and return entity display labels. For explicit "
            "relationship membership/count questions, execute graph COUNT over the matching "
            "entity keys at the requested grain and report the key, count and scope. "
            "Do not add count enrichments to an exact-instance trace unless requested. "
            "This representation exposes no monetary or operational time-series attributes; "
            "business donation metrics remain owned by the governed SQL or KQL source. "
            "Metadata descriptions alone are not evidence of executed counts or paths."
        )
        repairs.append(
            {
                "relationship": name,
                "path": "semanticEnrichment/description",
                "action": "preserve business meaning, repair assessed property wording, and append path/count guidance",
            }
        )

        custom = enrichment.get("customAttributes")
        if custom is not None:
            if not isinstance(custom, dict):
                raise ValueError(
                    f"{name} semanticEnrichment.customAttributes must be an object"
                )
            for key in list(custom):
                if references({key: custom[key]}):
                    removed = references({key: custom[key]})
                    repairs_by_relationship = {
                        "DonationSelectedGift": (
                            "aggregate DonationAmountYen from Donation, not Gift",
                            "Donation amounts are SQL-owned at Donation grain, not Gift or "
                            "catalog-registration grain; do not aggregate money in this "
                            "path-only Ontology.",
                        ),
                        "DonorMadeDonation": (
                            "count target Donation entities and sum their DonationAmountYen",
                            "Traversal identifies Donation endpoints. Query governed SQL "
                            "for donation totals and monetary amounts at Donation grain; "
                            "count graph endpoints only for explicit relationship evidence.",
                        ),
                        "SupplierProvidesGift": (
                            "do not sum DonationAmountYen across Suppliers without an explicit "
                            "allocation rule because multi-supplier Gifts can duplicate attribution",
                            "No allocation of donation amounts to Suppliers is defined. "
                            "Multi-supplier catalog paths can duplicate attribution; "
                            "do not derive supplier donation totals from them.",
                        ),
                    }
                    assessed = repairs_by_relationship.get(name)
                    if key != "aggregationGuard" or assessed is None or custom[key] != assessed[0]:
                        raise ValueError(f"Unassessed stale relationship custom attribute: {name}.{key}")
                    custom[key] = assessed[1]
                    repairs.append(
                        {
                            "relationship": name,
                            "path": f"semanticEnrichment/customAttributes/{key}",
                            "removedProperties": removed,
                            "action": "retain aggregation safety with source-owned wording",
                        }
                    )

    unresolved = []
    for name, relationship in sorted(transformed.items()):
        hits = references(relationship.get("semanticEnrichment", {}))
        if hits:
            unresolved.append({"relationship": name, "removedProperties": hits})
    if unresolved:
        raise ValueError(
            "Retained relationship semantics still reference removed properties: "
            + ", ".join(record["relationship"] for record in unresolved)
        )
    return transformed, {
        "scannedScope": "all retained relationship semanticEnrichment fields",
        "detectedBeforeTargetedRepair": detected,
        "targetedRepairs": repairs,
        "unresolvedAfterRepair": unresolved,
    }


def path_guidance(name: str, key_names: list[str], display_name: str) -> str:
    keys = ", ".join(key_names)
    return (
        f"Candidate-only path representation for {name}. Use relationship traversal and "
        f"exact lookup by {keys}; return {display_name} as the endpoint label. "
        "For explicit relationship membership/count questions, execute graph COUNT over "
        "the matching entity keys at the requested grain and return the key, count and scope. "
        "Do not add count enrichments to an exact-instance trace unless requested. "
        "Use the separately governed SQL or KQL source for other attributes, dates, and "
        "business donation or operational measures. "
        "This structural guidance does not guarantee Data Agent routing or answer compliance."
    )


def transform(
    envelope: dict[str, Any],
    candidate_display_name: str,
    source_definition_sha256: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if not isinstance(candidate_display_name, str) or not candidate_display_name.strip():
        raise ValueError("candidate_display_name must be a nonempty explicit value")
    if source_definition_sha256 is not None and (
        not isinstance(source_definition_sha256, str)
        or not SHA256.fullmatch(source_definition_sha256)
    ):
        raise ValueError("source_definition_sha256 must be a verified lowercase SHA-256")
    source = parse_model(envelope)
    source_display_name = source.values[".platform"]["metadata"]["displayName"]
    if candidate_display_name == source_display_name:
        raise ValueError("Candidate display name must differ from the source Ontology")
    expected_overview_path, expected_timeseries_binding_path = (
        validate_expected_source_shape(source)
    )

    changed: dict[str, bytes] = {}
    removed_paths = set(source.overviews)
    kept_properties: dict[str, list[str]] = {}
    removed_properties: dict[str, list[dict[str, str]]] = {}
    description_guidance: dict[str, str] = {}
    transformed_entities: dict[str, dict[str, Any]] = {}

    for name, entity in source.entities.items():
        entity_id = entity["id"]
        prop_index = source.properties[entity_id]
        key_ids = list(entity["entityIdParts"])
        display_id = entity["displayNamePropertyId"]
        keep_ids = set(key_ids) | {display_id}
        required_names = EXACT_LOOKUP_PROPERTIES.get(name, set())
        for required_name in required_names:
            matches = [
                prop_id
                for prop_id, record in prop_index.items()
                if record["value"]["name"] == required_name
            ]
            if len(matches) != 1:
                raise ValueError(
                    f"{name} requires exactly one existing lookup property {required_name}"
                )
            keep_ids.add(matches[0])

        value = copy.deepcopy(entity)
        removed: list[dict[str, str]] = []
        for collection in ("properties", "timeseriesProperties", "untypedProperties"):
            original = value.get(collection, [])
            retained = []
            for prop in original:
                if prop["id"] in keep_ids:
                    retained.append(prop)
                else:
                    removed.append(
                        {
                            "id": prop["id"],
                            "name": prop["name"],
                            "valueType": prop["valueType"],
                            "collection": collection,
                        }
                    )
            value[collection] = retained
        remaining_ids = {
            prop["id"]
            for collection in ("properties", "timeseriesProperties", "untypedProperties")
            for prop in value.get(collection, [])
        }
        if not set(key_ids) <= remaining_ids:
            raise ValueError(f"Transformation would remove a key from {name}")
        if display_id not in remaining_ids:
            raise ValueError(f"Transformation would remove the display name from {name}")
        remaining_timeseries = value.get("timeseriesProperties", [])
        if remaining_timeseries:
            raise ValueError(f"Path-focused candidate unexpectedly retained time series on {name}")

        key_names = [prop_index[prop_id]["value"]["name"] for prop_id in key_ids]
        display_name = prop_index[display_id]["value"]["name"]
        guidance = path_guidance(name, key_names, display_name)
        enrichment = value.get("semanticEnrichment")
        if enrichment is None:
            enrichment = {}
            value["semanticEnrichment"] = enrichment
        if not isinstance(enrichment, dict):
            raise ValueError(f"{name} semanticEnrichment must be an object when present")
        enrichment["description"] = guidance
        description_guidance[name] = guidance
        transformed_entities[name] = value
        kept_properties[name] = [
            prop["name"]
            for collection in ("properties", "timeseriesProperties", "untypedProperties")
            for prop in value.get(collection, [])
        ]
        removed_properties[name] = removed

        for path, binding in source.bindings[entity_id]:
            config = binding["dataBindingConfiguration"]
            if config["dataBindingType"] == "TimeSeries":
                removed_paths.add(path)
                continue
            binding_value = copy.deepcopy(binding)
            binding_config = binding_value["dataBindingConfiguration"]
            binding_config["propertyBindings"] = [
                mapping
                for mapping in binding_config["propertyBindings"]
                if mapping["targetPropertyId"] in keep_ids
            ]
            mapped_ids = {
                mapping["targetPropertyId"] for mapping in binding_config["propertyBindings"]
            }
            if not set(key_ids) <= mapped_ids or display_id not in mapped_ids:
                raise ValueError(f"Static binding would not populate key/display for {name}")
            if not keep_ids <= mapped_ids:
                raise ValueError(f"Static binding would not populate every kept property for {name}")
            changed[path] = json_bytes(binding_value)

    entity_semantic_inspection = repair_assessed_semantic_references(
        transformed_entities,
        removed_properties,
    )
    for name, value in transformed_entities.items():
        changed[source.entity_paths[name]] = json_bytes(value)
    entity_names_by_id = {
        entity["id"]: name for name, entity in source.entities.items()
    }
    transformed_relationships, relationship_semantic_inspection = (
        repair_relationship_semantics(
            source.relationships,
            removed_properties,
            entity_names_by_id,
        )
    )
    for name, value in transformed_relationships.items():
        changed[source.relationship_paths[name]] = json_bytes(value)

    platform = copy.deepcopy(source.values[".platform"])
    platform["metadata"]["displayName"] = candidate_display_name
    removed_platform_identity = False
    config = platform.get("config")
    if config is not None:
        if not isinstance(config, dict):
            raise ValueError(".platform config must be an object when present")
        if "logicalId" in config:
            del config["logicalId"]
            removed_platform_identity = True
    changed[".platform"] = json_bytes(platform)
    expected_removed_paths = {
        expected_overview_path,
        expected_timeseries_binding_path,
    }
    if removed_paths != expected_removed_paths:
        raise ValueError(
            "Removal plan diverged from the assessed Overview/TimeSeries pair"
        )

    candidate = copy.deepcopy(envelope)
    candidate_parts = []
    for part in candidate["definition"]["parts"]:
        path = part["path"]
        if path in removed_paths:
            continue
        if path in changed:
            part["payload"] = base64.b64encode(changed[path]).decode("ascii")
        candidate_parts.append(part)
    candidate["definition"]["parts"] = candidate_parts
    result = parse_model(candidate)

    for name, path in source.relationship_paths.items():
        before = copy.deepcopy(source.values[path])
        after = copy.deepcopy(result.values[path])
        before.pop("semanticEnrichment", None)
        after.pop("semanticEnrichment", None)
        if before != after:
            raise ValueError(f"Relationship structure changed unexpectedly: {name}")
    for entries in source.contextualizations.values():
        for path, _ in entries:
            if result.decoded[path] != source.decoded[path]:
                raise ValueError(f"Contextualization payload changed unexpectedly: {path}")

    source_inventory = property_inventory(source)
    result_inventory = property_inventory(result)
    if result_inventory != kept_properties:
        raise ValueError("Post-transform property inventory does not match the keep plan")

    report = {
        "schemaVersion": SCHEMA_VERSION,
        "status": "offline-candidate",
        "candidateDisplayName": candidate_display_name,
        "sourceDisplayName": source_display_name,
        **(
            {"sourceDefinitionSha256": source_definition_sha256}
            if source_definition_sha256 is not None
            else {}
        ),
        "beforeCounts": model_counts(source),
        "afterCounts": model_counts(result),
        "keptProperties": kept_properties,
        "removedProperties": removed_properties,
        "removedParts": sorted(removed_paths),
        "entityDescriptionGuidance": description_guidance,
        "semanticReferenceInspection": {
            "entitiesAndRetainedProperties": entity_semantic_inspection,
            "relationships": relationship_semantic_inspection,
        },
        "sourcePropertyInventory": source_inventory,
        "relationshipNames": sorted(result.relationships),
        "relationshipPayloadsPreservedByteForByte": False,
        "relationshipIdsEndpointsAndOtherFieldsPreserved": True,
        "contextualizationPayloadsPreservedByteForByte": True,
        "sourcePlatformLogicalIdRemoved": removed_platform_identity,
        "unsupportedAiPropertyFlagsAdded": False,
        "truthClaimsAdded": False,
        "liveDeploymentPerformed": False,
        "acceptanceClaimed": False,
    }
    return candidate, report


def build_artifacts(
    envelope: dict[str, Any],
    candidate_display_name: str,
    protected_item_ids: list[str],
    protection_baseline: dict[str, str],
    source_definition_sha256: str,
) -> dict[str, dict[str, Any]]:
    if not protected_item_ids or len(set(protected_item_ids)) != len(protected_item_ids):
        raise ValueError("Provide a nonempty, duplicate-free protected item inventory")
    for item_id in protected_item_ids:
        require_guid(item_id, "Protected item ID")
    if (
        not isinstance(source_definition_sha256, str)
        or not SHA256.fullmatch(source_definition_sha256)
    ):
        raise ValueError("Provide the verified source-file SHA-256")
    if (
        not isinstance(protection_baseline, dict)
        or set(protection_baseline) != {"path", "sha256"}
        or not isinstance(protection_baseline["path"], str)
        or not protection_baseline["path"]
        or not isinstance(protection_baseline["sha256"], str)
        or not SHA256.fullmatch(protection_baseline["sha256"])
    ):
        raise ValueError("Provide an explicit verified protection baseline path and SHA-256")

    candidate, delta = transform(
        envelope,
        candidate_display_name,
        source_definition_sha256,
    )
    model = parse_model(candidate)
    source_tables = sorted(
        {
            value["dataBindingConfiguration"]["sourceTableProperties"]["sourceTableName"]
            for entries in model.bindings.values()
            for _, value in entries
        }
    )
    protected = {
        "schemaVersion": SCHEMA_VERSION,
        "status": "protected-read-only",
        "protectedItemIds": protected_item_ids,
        "reusedProtectionBaseline": protection_baseline,
        "sourceDefinitionSha256": source_definition_sha256,
        "preservedRelationships": delta["relationshipNames"],
        "preservedContextualizationCount": delta["afterCounts"]["contextualizations"],
        "repositorySharedOntologyModified": False,
        "liveItemsModified": False,
    }
    readiness = {
        "schemaVersion": SCHEMA_VERSION,
        "status": "OFFLINE_STRUCTURALLY_READY_FOR_PARENT_REVIEW",
        "candidateDisplayName": candidate_display_name,
        "supersedesOfflineOutput": (
            "ontology (initial offline-only artifacts; preserved and not deployment input)"
        ),
        "counts": delta["afterCounts"],
        "sourceTables": source_tables,
        "checks": {
            "allReferencesResolved": True,
            "tenEntityIdentitiesPreserved": True,
            "fifteenRelationshipGraphPreserved": True,
            "allContextualizationsPreserved": True,
            "keysAndTypesPreserved": True,
            "displayNamesPreserved": True,
            "timeSeriesOwnershipRemoved": delta["afterCounts"]["timeseriesProperties"] == 0,
            "kustoBindingsRemovedWithoutDanglingReferences": all(
                value["dataBindingConfiguration"]["sourceTableProperties"]["sourceType"]
                != "KustoTable"
                for entries in model.bindings.values()
                for _, value in entries
            ),
            "retainedSemanticReferencesInspected": True,
            "noDanglingSemanticReferences": all(
                not inspection["unresolvedAfterRepair"]
                for inspection in delta["semanticReferenceInspection"].values()
            ),
        },
        "compatibilityFindings": [
            "The candidate uses only documented Ontology entity, NonTimeSeries Lakehouse "
            "binding, relationship, and contextualization part shapes.",
            "The source binding identifiers remain environment-specific and are confined "
            "to this private output; the transformer has no embedded workspace/item defaults.",
            "The canonical 98-object semantic metadata file is not copied: removed property "
            "entries would be stale, while retained properties keep their embedded metadata.",
        ],
        "blockersBeforeAnyWrite": [
            "At creation time, a parent must supply and verify the target workspace, folder, "
            "unique display name, and source binding compatibility.",
            "Offline definition inspection cannot prove that source tables are managed, that "
            "OneLake security is disabled, or that Delta column mapping is disabled.",
            "The documented Ontology definition has no per-property Data Agent source-"
            "instruction or few-shot part; no unsupported AI flags were invented.",
            "Structural validity does not establish native Data Agent reliability. A separate "
            "read-only assessment is required after an explicitly approved deployment/wiring.",
        ],
        "postCreateRequirements": [
            "After the create LRO succeeds, resolve and verify the new server-assigned item ID "
            "before candidate Data Agent wiring."
        ],
        "liveDeploymentPerformed": False,
        "accepted": False,
    }
    plan = {
        "schemaVersion": SCHEMA_VERSION,
        "status": "plan-only",
        "supersedesOfflineOutput": (
            "ontology (initial offline-only artifacts; preserved and not deployment input)"
        ),
        "operation": "createItem",
        "itemType": "Ontology",
        "candidateDefinitionFile": "candidate-definition.json",
        "requiredExplicitDeploymentInputs": [
            "target workspace identity",
            "target folder identity",
            "candidate display name",
            "freshly verified source Lakehouse identity and binding compatibility",
        ],
        "authorizedOwner": "parent",
        "steps": [
            "Re-fetch/verify the source identity and compatibility immediately before authoring.",
            "Apply the parent's authorization and preview controls under the existing explicit "
            "autonomous user request.",
            "Create exactly one new candidate Ontology; do not update the shared Ontology.",
            "Resolve and verify the new server-assigned item ID after the create LRO succeeds.",
            "Wire only the approved candidate Data Agent to the new Ontology.",
            "Perform a separate read-only native reliability assessment.",
        ],
        "automaticAuthentication": False,
        "automaticWrite": False,
        "liveDeploymentPerformed": False,
    }
    return {
        "candidate-definition.json": candidate,
        "semantic-delta.json": delta,
        "protected-inventory.json": protected,
        "readiness-summary.json": readiness,
        "deployment-plan.json": plan,
    }


def _exclusive_write(path: Path, data: bytes) -> None:
    target = safe_path(path)
    with target.open("xb") as stream:
        stream.write(data)


def write_fresh_directory(out: Path, artifacts: dict[str, dict[str, Any]]) -> None:
    original = Path(out)
    destination = outside_repo(original, REPOSITORY)
    parent = safe_path(original.parent)
    if not parent.is_dir():
        raise ValueError("The private output parent must already exist as a directory")
    if destination.exists():
        raise ValueError("Output directory already exists; use a fresh exclusive directory")

    serialized = {name: json_bytes(value) for name, value in artifacts.items()}
    try:
        destination.mkdir(exist_ok=False)
    except FileExistsError as error:
        raise ValueError(
            "Output directory appeared concurrently; no files were written"
        ) from error

    written: list[str] = []
    try:
        for name, data in serialized.items():
            _exclusive_write(destination / name, data)
            written.append(name)
    except (OSError, ValueError) as error:
        failure = {
            "schemaVersion": SCHEMA_VERSION,
            "status": "FAILED_PARTIAL_OUTPUT_RETAINED",
            "writtenFiles": written,
            "failedArtifact": name,
            "errorType": type(error).__name__,
            "error": str(error),
        }
        try:
            _exclusive_write(destination / "_FAILED.json", json_bytes(failure))
        except (OSError, ValueError) as marker_error:
            raise OutputWriteError(
                f"Partial output retained at {destination}; artifact write failed with "
                f"{type(error).__name__}: {error}; failure marker also failed with "
                f"{type(marker_error).__name__}: {marker_error}"
            ) from error
        raise OutputWriteError(
            f"Partial output retained and marked failed at {destination}: "
            f"{type(error).__name__}: {error}"
        ) from error


def read_verified_file(path: Path, expected_sha256: str, label: str) -> tuple[Path, bytes]:
    if not isinstance(expected_sha256, str) or not SHA256.fullmatch(expected_sha256):
        raise ValueError(f"{label} requires an explicit lowercase SHA-256")
    checked = safe_path(path)
    before = checked.stat()
    if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
        raise ValueError(f"{label} must be an unlinked regular file")
    raw = checked.read_bytes()
    after = checked.stat()
    if (before.st_size, before.st_mtime_ns, before.st_ino) != (
        after.st_size,
        after.st_mtime_ns,
        after.st_ino,
    ):
        raise ValueError(f"{label} changed while being read")
    if sha256(raw) != expected_sha256:
        raise ValueError(f"{label} SHA-256 does not match the explicit pin")
    return checked, raw


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--definition", type=Path, required=True)
    parser.add_argument("--source-sha256", required=True)
    parser.add_argument("--candidate-display-name", required=True)
    parser.add_argument("--protected-item-id", action="append", required=True)
    parser.add_argument("--protection-baseline", type=Path, required=True)
    parser.add_argument("--protection-baseline-sha256", required=True)
    parser.add_argument(
        "--out",
        type=Path,
        required=True,
        help="Fresh private directory outside the repository",
    )
    arguments = parser.parse_args()
    try:
        _, raw = read_verified_file(
            arguments.definition,
            arguments.source_sha256,
            "Source definition",
        )
        baseline_path, _ = read_verified_file(
            outside_repo(arguments.protection_baseline, REPOSITORY),
            arguments.protection_baseline_sha256,
            "Protection baseline",
        )
        envelope = strict_json_loads(raw.decode("utf-8-sig"))
        artifacts = build_artifacts(
            envelope,
            arguments.candidate_display_name,
            arguments.protected_item_id,
            {
                "path": str(baseline_path),
                "sha256": arguments.protection_baseline_sha256,
            },
            arguments.source_sha256,
        )
        write_fresh_directory(arguments.out, artifacts)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError, KeyError, TypeError) as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
