"""Export the portable full teaching ontology as RDF/OWL; no Fabric calls."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import sys
from typing import Any
import xml.etree.ElementTree as ET

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.compare import isomorphic
from rdflib.namespace import OWL, RDF, RDFS, SKOS, XSD, split_uri

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "provisioning"))
from reference_assets import canonical, digest  # noqa: E402

ONTOLOGY_IRI = URIRef("https://github.com/yang-jiayi/furusato-fabric-workshop/ontology/furusato")
F = Namespace(str(ONTOLOGY_IRI) + "#")
M = Namespace(str(ONTOLOGY_IRI) + "/fabric-mapping#")
PREFIXES = {"rdf": RDF, "rdfs": RDFS, "owl": OWL, "skos": SKOS, "xsd": XSD, "furusato": F, "fabric": M}
EXPECTED = {"definitionParts": 54, "entityTypes": 10, "staticProperties": 72, "timeseriesProperties": 1,
            "dataBindings": 11, "relationshipTypes": 15, "contextualizations": 15, "overviews": 1}
DATATYPES = {"BigInt": XSD.long, "String": XSD.string, "DateTime": XSD.dateTime,
             "Boolean": XSD.boolean, "Double": XSD.double}
FORMATS = {"furusato-ontology.ttl": "turtle", "furusato-ontology.rdf": "xml", "furusato-ontology.owl": "xml"}
IDENTIFIER = re.compile(r"[A-Za-z][A-Za-z0-9_]*\Z")


class ExportError(ValueError):
    pass


def require(condition: Any, message: str) -> None:
    if not condition:
        raise ExportError(message)


def json_literal(value: Any) -> Literal:
    return Literal(canonical(value).decode("utf-8"))


def enrichment(graph: Graph, subject: URIRef, value: dict[str, Any]) -> None:
    if value.get("description"):
        graph.add((subject, RDFS.comment, Literal(value["description"])))
    for synonym in value.get("synonyms", []):
        graph.add((subject, SKOS.altLabel, Literal(synonym)))
    for key, item in value.get("customAttributes", {}).items():
        require(IDENTIFIER.fullmatch(key), f"Unsupported custom attribute name: {key}")
        graph.add((subject, M[key], json_literal(item) if isinstance(item, (dict, list)) else Literal(item)))
    if value:
        graph.add((subject, M.semanticEnrichmentJson, json_literal(value)))


def part_annotation(graph: Graph, subject: URIRef, path: str, content: Any) -> None:
    graph.add((subject, M.definitionPart, Literal(path)))
    graph.add((subject, M.definitionJson, json_literal(content)))


def source_annotation(graph: Graph, subject: URIRef, source: dict[str, Any]) -> None:
    kind = source.get("sourceType")
    require(kind in {"LakehouseTable", "KustoTable"}, f"Unsupported binding source: {kind}")
    expected_variables = {"workspaceId": "{{workspace.id}}"}
    if kind == "LakehouseTable":
        expected_variables["itemId"] = "{{source.lakehouse.id}}"
    else:
        expected_variables.update({
            "itemId": "{{source.eventhouse.id}}",
            "clusterUri": "{{source.kqlDatabase.queryServiceUri}}",
            "databaseName": "{{source.kqlDatabase.displayName}}",
        })
    for key, expected in expected_variables.items():
        require(source.get(key) == expected, f"Expected portable placeholder for {key}; do not publish live deployment IDs")
    for key, value in source.items():
        require(IDENTIFIER.fullmatch(key), f"Unsupported source key: {key}")
        graph.add((subject, M[key], json_literal(value) if isinstance(value, (dict, list)) else Literal(value)))


def build_graph(template: dict[str, Any], source_sha256: str) -> Graph:
    require(template.get("expectedContract") == EXPECTED, "Only the complete 10/72/1/15 workshop ontology is supported")
    parts = template.get("parts", [])
    require(len(parts) == EXPECTED["definitionParts"], "Unexpected definition part count")
    require(template.get("definitionTemplateSha256") == digest(canonical(parts)), "Source definition-template seal is stale")
    paths = [part["path"] for part in parts]
    require(len(set(paths)) == len(paths), "Duplicate definition part paths")
    contents = {part["path"]: part["content"] for part in parts}
    require("definition.json" in contents and ".platform" in contents, "Missing root/platform definition")
    graph = Graph(bind_namespaces="none")
    for prefix, namespace in PREFIXES.items():
        graph.bind(prefix, namespace)
    graph.add((ONTOLOGY_IRI, RDF.type, OWL.Ontology))
    graph.add((ONTOLOGY_IRI, RDFS.label, Literal("Furusato full teaching ontology")))
    graph.add((ONTOLOGY_IRI, OWL.versionInfo, Literal(template["packageVersion"])))
    graph.add((ONTOLOGY_IRI, RDFS.comment, Literal(
        "Schema-only OWL/RDF projection of the portable Fabric full ontology. Fabric bindings, "
        "time-series behavior, keys and dataset cardinality remain annotations, not executable "
        "connectors or OWL integrity constraints. No donation/donor instances are exported."
    )))
    graph.add((ONTOLOGY_IRI, M.sourceTemplateFileSha256, Literal(source_sha256)))
    graph.add((ONTOLOGY_IRI, M.sourceDefinitionTemplateSha256, Literal(template["definitionTemplateSha256"])))
    graph.add((ONTOLOGY_IRI, M.expectedContractJson, json_literal(EXPECTED)))
    graph.add((ONTOLOGY_IRI, M.sourceSelectorsJson, json_literal(template["sourceSelectors"])))
    graph.add((ONTOLOGY_IRI, M.omittedDefinitionPart, Literal(".platform")))
    part_annotation(graph, ONTOLOGY_IRI, "definition.json", contents["definition.json"])
    entities: dict[str, tuple[URIRef, dict[str, Any]]] = {}
    properties: dict[tuple[str, str], URIRef] = {}
    property_kinds: dict[tuple[str, str], str] = {}
    mapped_properties: set[tuple[str, str]] = set()
    relationships: dict[str, tuple[URIRef, dict[str, Any]]] = {}
    claimed: set[URIRef] = {ONTOLOGY_IRI}
    counts: Counter[str] = Counter(definitionParts=len(parts))
    used_parts = {"definition.json", ".platform"}

    def claim(local: str) -> URIRef:
        uri = F[local]
        require(uri not in claimed, f"RDF identifier collision: {local}")
        claimed.add(uri)
        return uri

    for path, entity in contents.items():
        match = re.fullmatch(r"EntityTypes/([^/]+)/definition\.json", path)
        if not match:
            continue
        entity_id = match[1]
        require(entity.get("id") == entity_id and entity_id not in entities, "Invalid/duplicate entity ID")
        require(IDENTIFIER.fullmatch(entity["name"]), "Unsupported entity name")
        require(entity.get("baseEntityTypeId") is None and not entity.get("untypedProperties"),
                "Inheritance/untyped properties require an explicit RDF mapping")
        uri = claim(entity["name"])
        entities[entity_id] = (uri, entity)
        graph.add((uri, RDF.type, OWL.Class))
        graph.add((uri, RDFS.label, Literal(entity["name"])))
        graph.add((uri, M.entityTypeId, Literal(entity_id)))
        enrichment(graph, uri, entity.get("semanticEnrichment", {}))
        part_annotation(graph, uri, path, entity)
        used_parts.add(path)
        counts["entityTypes"] += 1
        for field, kind in (("properties", "static"), ("timeseriesProperties", "timeSeries")):
            for prop in entity.get(field, []):
                key = (entity_id, prop["id"])
                require(key not in properties, f"Duplicate property ID in {entity['name']}")
                require(IDENTIFIER.fullmatch(prop["name"]), "Unsupported property name")
                require(prop["valueType"] in DATATYPES, f"Unsupported valueType: {prop['valueType']}")
                require(prop.get("redefines") is None, "Redefined properties need an explicit RDF mapping")
                prop_uri = claim(entity["name"] + "__" + prop["name"])
                properties[key] = prop_uri
                property_kinds[key] = kind
                graph.add((prop_uri, RDF.type, OWL.DatatypeProperty))
                graph.add((prop_uri, RDFS.domain, uri))
                graph.add((prop_uri, RDFS.range, DATATYPES[prop["valueType"]]))
                graph.add((prop_uri, RDFS.label, Literal(prop["name"])))
                graph.add((prop_uri, M.propertyId, Literal(prop["id"])))
                graph.add((prop_uri, M.valueType, Literal(prop["valueType"])))
                graph.add((prop_uri, M.propertyKind, Literal(kind)))
                graph.add((prop_uri, M.propertyDefinitionJson, json_literal(prop)))
                enrichment(graph, prop_uri, prop.get("semanticEnrichment", {}))
                counts["staticProperties" if kind == "static" else "timeseriesProperties"] += 1
        keys = entity["entityIdParts"]
        require(keys and len(set(keys)) == len(keys), "Invalid entity key parts")
        for position, key_id in enumerate(keys):
            key = (entity_id, key_id)
            require(key in properties and property_kinds[key] == "static", "Entity key does not resolve to a static property")
            graph.add((uri, M.keyProperty, properties[key]))
            graph.add((properties[key], M.keyPosition, Literal(position)))
        display = (entity_id, entity["displayNamePropertyId"])
        require(display in properties and property_kinds[display] == "static", "Display property does not resolve")
        graph.add((uri, M.displayNameProperty, properties[display]))

    for path, relationship in contents.items():
        match = re.fullmatch(r"RelationshipTypes/([^/]+)/definition\.json", path)
        if not match:
            continue
        rel_id = match[1]
        require(relationship.get("id") == rel_id and rel_id not in relationships, "Invalid relationship ID")
        require(IDENTIFIER.fullmatch(relationship["name"]), "Unsupported relationship name")
        source_id = relationship["source"]["entityTypeId"]
        target_id = relationship["target"]["entityTypeId"]
        require(source_id in entities and target_id in entities, "Relationship endpoint does not resolve")
        uri = claim(relationship["name"])
        relationships[rel_id] = (uri, relationship)
        graph.add((uri, RDF.type, OWL.ObjectProperty))
        graph.add((uri, RDFS.domain, entities[source_id][0]))
        graph.add((uri, RDFS.range, entities[target_id][0]))
        graph.add((uri, RDFS.label, Literal(relationship["name"])))
        graph.add((uri, M.relationshipTypeId, Literal(rel_id)))
        enrichment(graph, uri, relationship.get("semanticEnrichment", {}))
        part_annotation(graph, uri, path, relationship)
        counts["relationshipTypes"] += 1
        used_parts.add(path)

    def mappings(subject: URIRef, entity_id: str, bindings: list[dict[str, str]], predicate: URIRef) -> None:
        seen: set[str] = set()
        require(bindings, "An empty key/property binding would lose grounding")
        for position, binding in enumerate(bindings):
            property_id = binding["targetPropertyId"]
            require(property_id not in seen, "Duplicate target property in one binding")
            seen.add(property_id)
            key = (entity_id, property_id)
            require(key in properties, "Binding points to a property owned by a different or absent entity")
            require(isinstance(binding.get("sourceColumnName"), str) and binding["sourceColumnName"].strip(),
                    "A source column name must be nonempty")
            node = claim(str(subject).removeprefix(str(F)) + "_" + str(predicate).removeprefix(str(M)) + "_" + str(position))
            graph.add((subject, predicate, node))
            graph.add((node, M.property, properties[key]))
            graph.add((node, M.sourceColumnName, Literal(binding["sourceColumnName"])))
            graph.add((node, M.bindingPosition, Literal(position)))
            graph.add((node, M.propertyBindingJson, json_literal(binding)))

    for path, content in contents.items():
        match = re.fullmatch(r"EntityTypes/([^/]+)/DataBindings/([^/]+)\.json", path)
        if match:
            entity_id, binding_id = match.groups()
            require(entity_id in entities and content.get("id") == binding_id, "Invalid binding owner/ID")
            node = claim("binding_" + binding_id)
            graph.add((entities[entity_id][0], M.hasDataBinding, node))
            config = content["dataBindingConfiguration"]
            kind = config["dataBindingType"]
            source = config["sourceTableProperties"]
            require(kind in {"NonTimeSeries", "TimeSeries"}, "Unknown binding type")
            require((kind == "TimeSeries") == (source["sourceType"] == "KustoTable"), "Unexpected workshop source/binding combination")
            graph.add((node, M.dataBindingType, Literal(kind)))
            source_annotation(graph, node, source)
            mappings(node, entity_id, config["propertyBindings"], M.hasPropertyBinding)
            mapped_properties.update((entity_id, item["targetPropertyId"]) for item in config["propertyBindings"])
            if kind == "TimeSeries":
                require(config.get("timestampColumnName"), "Time-series binding is missing its timestamp column")
                require(any(property_kinds[(entity_id, item["targetPropertyId"])] == "timeSeries"
                            for item in config["propertyBindings"]), "Time-series property is not bound")
                graph.add((node, M.timestampColumnName, Literal(config["timestampColumnName"])))
            else:
                require(all(property_kinds[(entity_id, item["targetPropertyId"])] == "static"
                            for item in config["propertyBindings"]), "A static binding targets a time-series property")
            part_annotation(graph, node, path, content)
            counts["dataBindings"] += 1
            used_parts.add(path)
            continue
        match = re.fullmatch(r"RelationshipTypes/([^/]+)/Contextualizations/([^/]+)\.json", path)
        if match:
            rel_id, context_id = match.groups()
            require(rel_id in relationships and content.get("id") == context_id, "Invalid contextualization owner/ID")
            rel_uri, rel = relationships[rel_id]
            node = claim("contextualization_" + context_id)
            graph.add((rel_uri, M.hasContextualization, node))
            require(content["dataBindingTable"]["sourceType"] == "LakehouseTable", "Contextualization must use a Lakehouse linking table")
            source_annotation(graph, node, content["dataBindingTable"])
            for side in ("source", "target"):
                entity_id = rel[side]["entityTypeId"]
                bindings = content[side + "KeyRefBindings"]
                require({item["targetPropertyId"] for item in bindings} == set(entities[entity_id][1]["entityIdParts"]),
                        f"Contextualization omits/misassigns the {side} composite key")
                mappings(node, entity_id, bindings, M[side + "KeyBinding"])
            part_annotation(graph, node, path, content)
            counts["contextualizations"] += 1
            used_parts.add(path)
            continue
        match = re.fullmatch(r"EntityTypes/([^/]+)/Overviews/definition\.json", path)
        if match:
            require(match[1] in entities, "Overview owner does not resolve")
            node = claim("overview_" + match[1])
            graph.add((entities[match[1]][0], M.hasOverview, node))
            part_annotation(graph, node, path, content)
            counts["overviews"] += 1
            used_parts.add(path)
    require(used_parts == set(contents), "Unmapped definition parts: " + ", ".join(sorted(set(contents) - used_parts)))
    require(mapped_properties == set(properties), "Some ontology properties have no source binding")
    require(dict(counts) == EXPECTED, f"Actual ontology counts differ from the full contract: {dict(counts)}")
    annotation_predicates = {predicate for _, predicate, _ in graph if str(predicate).startswith(str(M))}
    annotation_predicates.add(SKOS.altLabel)
    for predicate in annotation_predicates:
        graph.add((predicate, RDF.type, OWL.AnnotationProperty))
    return graph


def term_text(term: URIRef | Literal) -> str:
    if isinstance(term, URIRef):
        for prefix, namespace in PREFIXES.items():
            local = str(term).removeprefix(str(namespace))
            if local != str(term) and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_-]*", local):
                return prefix + ":" + local
    return term.n3()


def sorted_triples(graph: Graph):
    return sorted(graph, key=lambda triple: tuple(term.n3() for term in triple))


def turtle_bytes(graph: Graph) -> bytes:
    lines = ["# Generated schema projection; no instance donation data. Do not hand-edit."]
    lines.extend(f"@prefix {prefix}: <{namespace}> ." for prefix, namespace in PREFIXES.items())
    lines.append("")
    lines.extend(" ".join(term_text(term) for term in triple) + " ." for triple in sorted_triples(graph))
    return ("\n".join(lines) + "\n").encode("utf-8")


def xml_bytes(graph: Graph) -> bytes:
    for prefix, namespace in PREFIXES.items():
        ET.register_namespace(prefix, str(namespace))
    root = ET.Element(ET.QName(str(RDF), "RDF"))
    subjects: dict[URIRef, ET.Element] = {}
    for subject, predicate, obj in sorted_triples(graph):
        require(isinstance(subject, URIRef), "Anonymous schema resources are unsupported")
        if subject not in subjects:
            subjects[subject] = ET.SubElement(root, ET.QName(str(RDF), "Description"), {str(ET.QName(str(RDF), "about")): str(subject)})
        namespace, local = split_uri(predicate)
        child = ET.SubElement(subjects[subject], ET.QName(namespace, local))
        if isinstance(obj, URIRef):
            child.set(ET.QName(str(RDF), "resource"), str(obj))
        else:
            require(isinstance(obj, Literal), "Unsupported RDF object")
            if obj.language:
                child.set("{http://www.w3.org/XML/1998/namespace}lang", obj.language)
            elif obj.datatype:
                child.set(ET.QName(str(RDF), "datatype"), str(obj.datatype))
            child.text = str(obj)
    ET.indent(root, space="  ")
    return ET.tostring(root, encoding="utf-8", xml_declaration=True) + b"\n"


def artifacts(source: Path) -> dict[str, bytes]:
    raw = source.read_bytes()
    graph = build_graph(json.loads(raw), digest(raw))
    xml = xml_bytes(graph)
    files = {"furusato-ontology.ttl": turtle_bytes(graph), "furusato-ontology.rdf": xml, "furusato-ontology.owl": xml}
    for name, data in files.items():
        parsed = Graph().parse(data=data, format=FORMATS[name])
        require(isomorphic(graph, parsed), f"RDF round-trip changed the graph: {name}")
    files["SHA256SUMS.txt"] = "".join(f"{digest(data)}  {name}\n" for name, data in sorted(files.items())).encode("ascii")
    return files


def export(source: Path, output: Path, *, check: bool = False) -> dict[str, str]:
    files = artifacts(source)
    if check:
        mismatches = [name for name, data in files.items() if not (output / name).is_file() or (output / name).read_bytes() != data]
        require(not mismatches, "Missing/stale RDF artifacts: " + ", ".join(mismatches))
    else:
        require(not output.is_symlink(), "Refusing a symlink output directory")
        for name in files:
            target = output / name
            require(not target.is_symlink() and (not target.exists() or target.is_file()),
                    f"Refusing an unsafe output target: {name}")
            require(not target.exists() or target.stat().st_nlink == 1, f"Refusing a hard-linked output: {name}")
        output.mkdir(parents=True, exist_ok=True)
        for name, data in files.items():
            (output / name).write_bytes(data)
    return {name: digest(data) for name, data in files.items()}


def main() -> int:
    version = (ROOT / "VERSION").read_text("utf-8").strip()
    default = ROOT / "workshop" / ("v" + version) / "ontology"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--template", type=Path, default=default / "ontology-full-definition-template.json")
    parser.add_argument("--output-dir", type=Path, default=default / "rdf")
    parser.add_argument("--check", action="store_true", help="Read-only check of graph-equivalent, byte-identical generated files.")
    args = parser.parse_args()
    try:
        hashes = export(args.template, args.output_dir, check=args.check)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"Ontology RDF export failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({"mode": "check" if args.check else "export", "counts": EXPECTED, "sha256": hashes}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
