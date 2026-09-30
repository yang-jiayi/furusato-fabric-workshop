"""Deterministic generation-2 TMDL from the immutable Furusato business model.

The input JSON is a business-model source, not a deployment wire format.
No generation-1 definition part is emitted.  Native projected DAX Metrics are
deliberately not synthesized: their backingMeasure does not round-trip in TMDL.
"""
from __future__ import annotations
import base64
from collections import OrderedDict
import copy
import json
from pathlib import Path
import re
from typing import Any
import uuid

TYPE_MAP = {"BigInt": "int64", "String": "string", "Double": "double",
            "Boolean": "boolean", "DateTime": "dateTime"}
NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, "urn:furusato:workshop:v3:ontology")


def lineage(kind: str, name: str) -> str:
    """Logical identity only; never a live Fabric artifact ID."""
    return str(uuid.uuid5(NAMESPACE, f"{kind}/{name}"))


def identifier(name: str) -> str:
    return name if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name) else "'" + name.replace("'", "''") + "'"


def description(lines: list[str], text: str, depth: int = 0) -> None:
    if len(text) > 4000:
        raise ValueError("Ontology description exceeds the documented 4,000-character limit.")
    for line in text.replace("\r", "").splitlines():
        if line:
            lines.append("\t" * depth + "/// " + line)


def metadata(lines: list[str], value: dict[str, Any], depth: int = 1) -> None:
    indent = "\t" * depth
    for synonym in value.get("synonyms", []):
        if len(synonym) > 100:
            raise ValueError("Ontology synonym exceeds 100 characters.")
        lines.append(indent + "synonym " + identifier(synonym))
    for key, item in sorted(value.get("customAttributes", {}).items()):
        # Annotation payloads use JSON strings so punctuation never becomes TMDL syntax.
        encoded = json.dumps(item, ensure_ascii=False, separators=(",", ":"))
        if len(encoded) > 4000:
            raise ValueError("Ontology annotation exceeds 4,000 characters.")
        lines.append(indent + "annotation " + identifier("Furusato_" + key) + " = " + encoded)


def generate(template: dict[str, Any]) -> tuple[dict[str, str], dict[str, Any]]:
    parts = {p["path"]: p["content"] for p in template["parts"]}
    entities = {v["id"]: v for p, v in parts.items()
                if p.startswith("EntityTypes/") and p.count("/") == 2
                and p.endswith("/definition.json")}
    relationships = {v["id"]: v for p, v in parts.items()
                     if p.startswith("RelationshipTypes/") and p.count("/") == 2
                     and p.endswith("/definition.json")}
    bindings: dict[str, dict[str, Any]] = {}
    contexts: dict[str, dict[str, Any]] = {}
    for path, content in parts.items():
        if "/DataBindings/" in path:
            config = content["dataBindingConfiguration"]
            if config["dataBindingType"] == "NonTimeSeries":
                bindings[path.split("/")[1]] = config
        if "/Contextualizations/" in path:
            contexts[path.split("/")[1]] = content
    if (len(entities), len(relationships), len(bindings), len(contexts)) != (10, 15, 10, 15):
        raise ValueError("Unexpected baseline business model inventory.")

    columns: dict[str, OrderedDict[str, str]] = {}
    table_for: dict[str, str] = {}
    property_names: dict[str, dict[str, str]] = {}
    property_columns: dict[str, dict[str, str]] = {}
    keys: dict[str, str] = {}
    for entity_id, entity in entities.items():
        binding = bindings[entity_id]
        table = binding["sourceTableProperties"]["sourceTableName"]
        if binding["sourceTableProperties"]["sourceType"] != "LakehouseTable":
            raise ValueError("Core static sources must remain managed Lakehouse tables.")
        table_for[entity_id] = table
        property_names[entity_id] = {p["id"]: p["name"] for p in entity["properties"]}
        property_columns[entity_id] = {p["targetPropertyId"]: p["sourceColumnName"]
                                       for p in binding["propertyBindings"]}
        if len(entity["entityIdParts"]) != 1:
            raise ValueError("Generation2 keyProperty is singular; composite key needs explicit migration.")
        keys[entity_id] = entity["entityIdParts"][0]
        columns[table] = OrderedDict()
        for prop in entity["properties"]:
            columns[table][property_columns[entity_id][prop["id"]]] = TYPE_MAP[prop["valueType"]]

    tom: list[str] = []
    entity_relations: list[str] = []
    relation_inventory = []

    def add_column(table: str, column: str, kind: str) -> None:
        existing = columns.setdefault(table, OrderedDict()).get(column)
        if existing and existing != kind:
            raise ValueError(f"Conflicting type for {table}.{column}")
        columns[table][column] = kind

    def tom_relationship(name: str, a: str, ac: str, b: str, bc: str,
                         from_cardinality: str, to_cardinality: str) -> None:
        tom.extend([f"relationship {identifier(name)}",
                    f"\tfromColumn: {identifier(a)}.{identifier(ac)}",
                    f"\ttoColumn: {identifier(b)}.{identifier(bc)}",
                    f"\tfromCardinality: {from_cardinality}",
                    f"\ttoCardinality: {to_cardinality}",
                    "\tcrossFilteringBehavior: oneDirection", ""])

    for rel_id, rel in relationships.items():
        ctx = contexts[rel_id]
        a_id, b_id = rel["source"]["entityTypeId"], rel["target"]["entityTypeId"]
        a, b = entities[a_id], entities[b_id]
        at, bt = table_for[a_id], table_for[b_id]
        link = ctx["dataBindingTable"]["sourceTableName"]
        if len(ctx["sourceKeyRefBindings"]) != 1 or len(ctx["targetKeyRefBindings"]) != 1:
            raise ValueError("Only singular baseline relationship keys may be translated.")
        ar, br = ctx["sourceKeyRefBindings"][0], ctx["targetKeyRefBindings"][0]
        ac, bc = property_columns[a_id][ar["targetPropertyId"]], property_columns[b_id][br["targetPropertyId"]]
        akind, bkind = columns[at][ac], columns[bt][bc]
        add_column(link, ar["sourceColumnName"], akind)
        add_column(link, br["sourceColumnName"], bkind)
        enrichment = rel.get("semanticEnrichment", {})
        description(entity_relations, enrichment.get("description", ""))
        entity_relations.extend([f"entityRelationship {identifier(rel['name'])}",
                                 "\tlineageTag: " + lineage("relationship", rel["name"]),
                                 f"\tfromEntity: {identifier(a['name'])}",
                                 f"\ttoEntity: {identifier(b['name'])}"])
        metadata(entity_relations, enrichment)
        entity_relations.extend(["", "\tbackingConfiguration"])
        rel_name = "rel_" + rel["name"]
        if link == at:
            tom_relationship(rel_name, at, br["sourceColumnName"], bt, bc, "many", "one")
            entity_relations.append(f"\t\trelationship: {identifier(rel_name)}")
        elif link == bt:
            tom_relationship(rel_name, at, ac, bt, ar["sourceColumnName"], "one", "many")
            entity_relations.append(f"\t\trelationship: {identifier(rel_name)}")
        else:
            rfrom, rto = rel_name + "_from", rel_name + "_to"
            tom_relationship(rfrom, link, ar["sourceColumnName"], at, ac, "many", "one")
            tom_relationship(rto, link, br["sourceColumnName"], bt, bc, "many", "one")
            entity_relations.extend(["\t\ttype: table", f"\t\ttable: {identifier(link)}",
                                     f"\t\tfromRelationship: {identifier(rfrom)}",
                                     f"\t\ttoRelationship: {identifier(rto)}"])
        entity_relations.append("")
        relation_inventory.append({"name": rel["name"], "fromEntity": a["name"],
                                   "toEntity": b["name"], "sourceTable": link})

    output: dict[str, str] = {}
    inventory = []
    for entity_id, entity in entities.items():
        table = table_for[entity_id]
        enrichment = entity.get("semanticEnrichment", {})
        lines: list[str] = []
        description(lines, enrichment.get("description", ""))
        lines.extend([f"entity {identifier(entity['name'])}",
                      "\tlineageTag: " + lineage("entity", entity["name"]),
                      f"\tbackingTable: {identifier(table)}",
                      f"\tkeyProperty: {identifier(property_names[entity_id][keys[entity_id]])}"])
        metadata(lines, enrichment)
        lines.append("")
        props = []
        for prop in entity["properties"]:
            meta = prop.get("semanticEnrichment", {})
            column = property_columns[entity_id][prop["id"]]
            description(lines, meta.get("description", ""), 1)
            lines.extend([f"\tproperty {identifier(prop['name'])}",
                          f"\t\tdataType: {TYPE_MAP[prop['valueType']]}",
                          "\t\tlineageTag: " + lineage("property", entity["name"] + "/" + prop["name"])])
            metadata(lines, meta, 2)
            lines.extend(["", "\t\tbackingConfiguration",
                          f"\t\t\tvalueColumn: {identifier(table)}.{identifier(column)}", ""])
            props.append({"name": prop["name"], "dataType": TYPE_MAP[prop["valueType"]],
                          "sourceColumn": column})
        # The sole operational time-series property remains explicitly unbound
        # until the native Eventhouse source contract has been captured/read back.
        for prop in entity.get("timeseriesProperties", []):
            description(lines, prop.get("semanticEnrichment", {}).get("description", ""), 1)
            lines.extend([f"\tproperty {identifier(prop['name'])}",
                          f"\t\tdataType: TimeSeries<{TYPE_MAP[prop['valueType']]}>",
                          "\t\tlineageTag: " + lineage("property", entity["name"] + "/" + prop["name"]),
                          '\t\tannotation Furusato_BindingStatus = "requires-native-Eventhouse-binding"',
                          ""])
        output[f"entities/{entity['name']}.tmdl"] = "\n".join(lines) + "\n"
        inventory.append({"name": entity["name"], "namespace": "default",
                          "lineageTag": lineage("entity", entity["name"]),
                          "sourceTable": table, "sourceSchema": "dbo",
                          "keyProperty": property_names[entity_id][keys[entity_id]],
                          "properties": props,
                          "timeSeriesBindingStatus": "pending-native-binding" if entity.get("timeseriesProperties") else "not-applicable"})

    for table, cols in columns.items():
        lines = [f"table {identifier(table)}", "\tlineageTag: " + lineage("table", table), ""]
        for column, kind in cols.items():
            lines.extend([f"\tcolumn {identifier(column)}", f"\t\tdataType: {kind}",
                          f"\t\tsourceColumn: {column}", ""])
        lines.extend([f"\tpartition {identifier(table)} = entity", "\t\tmode: directLake",
                      "\t\tsource", f"\t\t\tentityName: {table}",
                      "\t\t\tschemaName: dbo",
                      "\t\t\texpressionSource: 'DirectLake - {{source.lakehouse.displayName}}'", "",
                      "\t\tannotation ONT_WorkspaceId = {{workspace.id}}", "",
                      "\t\tannotation ONT_ItemId = {{source.lakehouse.id}}", "",
                      "\t\tannotation ONT_ItemKind = Lakehouse", "",
                      "\t\tannotation ONT_ItemName = {{source.lakehouse.displayName}}", "",
                      "\t\tannotation ONT_WorkspaceName = {{workspace.name}}", "",
                      "\t\tannotation ONT_SqlEndpoint = {{source.lakehouse.sqlEndpoint}}", "",
                      "\t\tannotation ONT_SqlDatabase = {{source.lakehouse.displayName}}", "",
                      "\t\tannotation ONT_PinnedAtUtc = {{source.binding.pinnedAtUtc}}", ""])
        output[f"tables/{table}.tmdl"] = "\n".join(lines)

    output["expressions.tmdl"] = (
        "/// Observed native OneLake binding contract; partition ONT_* annotations identify the Fabric item.\n"
        "expression 'DirectLake - {{source.lakehouse.displayName}}' =\n"
        "\t\tlet\n"
        '\t\t    Source = AzureStorage.DataLake("{{source.lakehouse.oneLakeRootUrl}}", [HierarchicalNavigation=true])\n'
        "\t\tin\n\t\t    Source\n"
    )
    output["relationships.tmdl"] = "\n".join(tom)
    output["entityRelationships.tmdl"] = "\n".join(entity_relations)
    output["database.tmdl"] = "database\n\tcompatibilityLevel: 1000000\n"
    output["namespaces/default.tmdl"] = "namespace default\n\tlineageTag: default\n"
    rules = {
        "StaticAndOperationalSeparation": (
            "Donation represents only the immutable static baseline. Municipality operational observations are raw time-series events. Never add those observations to static Donation counts or amounts.",
            ["Donation", "Municipality"]),
        "SupplierAttribution": (
            "SupplierProvidesGift describes catalog eligibility, not a supplier assigned to a donation. A many-to-many supplier catalog join must not duplicate Donation amounts or imply an order-level supplier.",
            ["Supplier", "Gift", "Donation"]),
        "RankTieBreak": (
            "Published rank columns are deterministic ordinal ranks. Preserve their source-defined amount-descending and identifier-ascending tie-break rules rather than substituting a dense rank.",
            ["Donor", "Municipality", "GiftCategory"]),
        "RawObservationSemantics": (
            "IncomingDonationAmountYen represents raw ingested operational observations, including duplicate events. Deduplicated accepted increments belong to the separate quality-processed Lakehouse serving layer, not to the raw Eventhouse count.",
            ["Municipality"]),
    }
    for name, (statement, refs) in rules.items():
        lines = [f"rule {name}", "\tlineageTag: " + lineage("rule", name),
                 "\tstatement: " + statement]
        lines += [f"\truleReferencedEntity {entity}" for entity in refs]
        output[f"rules/{name}.tmdl"] = "\n".join(lines) + "\n"
    model = ["model Model", ""]
    model += ["ref table " + identifier(t) for t in columns]
    model += ["", *["ref entity " + identifier(e["name"]) for e in entities.values()],
              "", "ref namespace default", ""]
    model += ["ref rule " + r for r in rules]
    output["model.tmdl"] = "\n".join(model) + "\n"
    output[".platform"] = json.dumps({
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
        "metadata": {"type": "Ontology", "displayName": "{{ontology.displayName}}"},
        "config": {"version": "2.0", "logicalId": "{{ontology.logicalId}}"},
    }, ensure_ascii=False, indent=2) + "\n"
    contract = {
        "schemaVersion": "furusato-generation2-candidate/v1",
        "generation": 2, "compatibilityLevel": 1000000,
        "entityTypes": 10, "staticProperties": 72, "timeseriesProperties": 1,
        "staticBindings": 10, "relationshipTypes": 15, "backingTables": 11,
        "nativeLakehouseSourceContract": {
            "connector": "AzureStorage.DataLake", "hierarchicalNavigation": True,
            "partitionType": "entity", "mode": "directLake",
            "itemKind": "Lakehouse", "sqlDatabaseLocator": "Lakehouse display name, not SQL endpoint GUID",
            "annotations": ["ONT_WorkspaceId", "ONT_ItemId", "ONT_ItemKind", "ONT_ItemName",
                            "ONT_WorkspaceName", "ONT_SqlEndpoint", "ONT_SqlDatabase", "ONT_PinnedAtUtc"],
            "nativeInstancesVerificationRequired": True,
        },
        "nativeRules": list(rules), "entities": inventory, "relationships": relation_inventory,
        "timeSeriesBinding": {"status": "requires-native-contract", "entity": "Municipality",
                              "property": "IncomingDonationAmountYen",
                              "sourceTable": "DonationEvents", "keyColumn": "MunicipalityID",
                              "valueColumn": "DonationAmountYen", "orderingColumn": "DonatedAt"},
        "nativeMetrics": {"status": "requires-native-semantic-model-binding",
                          "sourceOwnsDax": True, "tmdlProjectionSupported": False},
        "graph": {"materialization": "opt-in", "default": False},
        "migration": {
            "doNotUpdateGeneration1InPlace": True, "preserveOriginal": True,
            "newItemRequiresConsumerReconnection": True,
            "stableIdentity": "UUIDv5 lineageTag derived from semantic kind/name; not a deployed item ID",
            "baseEntityTypeChange": "immutable; native change is delete/recreate, isolated lab only",
            "afterNativeMetrics": "do not round-trip complete ontology TMDL; backingMeasure may be lost",
        },
    }
    return output, contract


def generate_relationships(template: dict[str, Any]) -> tuple[dict[str, str], dict[str, Any]]:
    """Build a NEW static companion, never a patch for the operational ontology."""
    source = copy.deepcopy(template)
    entities = [p["content"] for p in source["parts"]
                if p["path"].startswith("EntityTypes/") and p["path"].count("/") == 2
                and p["path"].endswith("/definition.json")]
    timeseries = [(entity["name"], prop["name"]) for entity in entities
                  for prop in entity.get("timeseriesProperties", [])]
    if timeseries != [("Municipality", "IncomingDonationAmountYen")]:
        raise ValueError("Only the original single operational time-series property may be omitted.")
    if sum(len(entity["properties"]) for entity in entities) != 72:
        raise ValueError("Use the portable original core, not a native-edited operational definition.")
    for entity in entities:
        entity["timeseriesProperties"] = []
    parts, contract = generate(source)
    contract.update({
        "schemaVersion": "furusato-generation2-relationships/v1",
        "timeseriesProperties": 0,
        "timeSeriesBinding": {"status": "not-applicable",
                              "retainedInOperationalCore": "Municipality.IncomingDonationAmountYen"},
        "nativeMetrics": {"status": "not-applicable", "tmdlProjectionSupported": False},
        "sourceContract": {
            "definition": "portable-original-core",
            "portableCore": {"entityTypes": 10, "staticProperties": 72,
                             "timeseriesProperties": 1, "relationshipTypes": 15},
            "nativeOperationalCore": {
                "entityTypes": 10, "staticProperties": 73, "timeseriesProperties": 1,
                "relationshipTypes": 15, "promotedProperty": "Municipality.PrefectureId",
                "note": "Observed after native binding; not a portable property promotion.",
            },
            "omittedProperty": "Municipality.IncomingDonationAmountYen",
            "sameLakehouse": True, "copiesBusinessData": False,
            "entityPropertyRelationshipIdentitiesPreserved": True,
            "operationalCoreAndKqlBindingUnchanged": True,
            "staticAndOperationalAmountsMustNotBeAdded": True,
        },
        "deployment": {
            "displayName": "ONT_Furusato_Relationships_<PID>",
            "default": False, "createOnly": True, "requiresApprovedResourcePlan": True,
            "replacesCore": False, "rerunsDataNotebooks": False,
            "dataAgentSourceRoutingChanged": False,
        },
        "graph": {
            "materialization": "explicit-native-handoff", "default": False,
            "eligibilityIsRefreshOrQueryProof": False,
            "queryAcceptance": "required-not-assessed",
            "managedGraphIdentity": "discover-native-identity-never-infer-from-ontology-id",
            "operationalCoreLimitation": "Observed HTTP400 InvalidPropertyType: IncomingDonationAmountYen despite Eligible UI.",
        },
    })
    return parts, contract


def verify_relationships_readback(actual: dict[str, Any], expected: dict[str, Any]) -> None:
    """Fail closed on structural/source/identity drift, tolerating object reordering."""
    def decode(definition: dict[str, Any]) -> dict[str, str]:
        result = {}
        for part in definition["parts"]:
            path = part["path"]
            if (path in result or part["payloadType"] != "InlineBase64"
                    or not (path == ".platform" or path.endswith(".tmdl"))):
                raise ValueError("Expected unique generation2 TMDL parts.")
            result[path] = base64.b64decode(part["payload"], validate=True).decode("utf-8")
        return result

    def field(text: str, key: str) -> str:
        values = re.findall(r"(?m)^\s*" + re.escape(key) + r":\s*(.+)$", text)
        if len(values) != 1:
            raise ValueError("Missing or ambiguous readback field: " + key)
        return values[0].strip().strip("'")

    def blocks(text: str, pattern: str) -> dict[str, str]:
        matches = list(re.finditer(pattern, text, re.MULTILINE))
        result = {}
        for i, match in enumerate(matches):
            name = match.group(1).strip().strip("'")
            if name in result:
                raise ValueError("Duplicate readback object: " + name)
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            result[name] = text[match.end():end]
        return result

    def signature(parts: dict[str, str]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        property_count = 0
        for path, text in parts.items():
            if path == ".platform":
                continue  # Service-owned item metadata is not a business identity.
            if path.startswith("entities/"):
                declarations = blocks(text, r"^entity (.+)$")
                if len(declarations) != 1:
                    raise ValueError("Expected one entity per TMDL part.")
                name, body = next(iter(declarations.items()))
                header = re.split(r"(?m)^\tproperty ", body, maxsplit=1)[0]
                props = blocks(body, r"^\tproperty (.+)$")
                property_count += len(props)
                result[path] = {
                    "name": name,
                    **{key: field(header, key) for key in ("lineageTag", "backingTable", "keyProperty")},
                    "properties": {prop: {key: field(value, key) for key in
                                         ("dataType", "lineageTag", "valueColumn")}
                                   for prop, value in props.items()},
                }
                if any("TimeSeries" in prop["dataType"] for prop in result[path]["properties"].values()):
                    raise ValueError("The relationship companion cannot contain time-series properties.")
            elif path == "entityRelationships.tmdl":
                relationships = blocks(text, r"^entityRelationship (.+)$")
                if len(relationships) != 15:
                    raise ValueError("Relationship readback must contain all fifteen relations.")
                result[path] = {
                    name: {**{key: field(body, key) for key in ("lineageTag", "fromEntity", "toEntity")},
                           "backing": sorted(line.strip() for line in body.splitlines()
                                             if line.startswith("\t\t") and line.strip())}
                    for name, body in relationships.items()}
            else:
                # Includes every table/source locator, FK column and rule statement.
                result[path] = sorted(line.strip() for line in text.splitlines()
                                      if line.strip() and not line.lstrip().startswith("///"))
        if (sum(path.startswith("entities/") for path in result), property_count,
                sum(path.startswith("tables/") for path in result)) != (10, 72, 11):
            raise ValueError("Relationship readback must contain 10 entities / 72 properties / 11 tables.")
        return result

    if signature(decode(actual)) != signature(decode(expected)):
        raise ValueError("Relationship readback changed a business identity, binding or relationship.")


def encode_definition(parts: dict[str, str], replacements: dict[str, str]) -> dict[str, Any]:
    encoded = []
    for path, text in sorted(parts.items()):
        for key, value in replacements.items():
            text = text.replace("{{" + key + "}}", value)
        if re.search(r"\{\{[^{}]+\}\}", text):
            raise ValueError("Unresolved environment placeholder: " + path)
        encoded.append({"path": path, "payloadType": "InlineBase64",
                        "payload": base64.b64encode(text.encode("utf-8")).decode("ascii")})
    # The deployed preview resolves generation from the .tmdl parts. Explicit
    # format=TMDL is rejected by its Ontology definition surface; omit it.
    return {"parts": encoded}
