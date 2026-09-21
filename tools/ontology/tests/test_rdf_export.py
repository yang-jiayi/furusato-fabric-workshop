"""Protect the full ontology schema, portable grounding and deterministic formats."""

from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools" / "ontology"))
import export_ontology_rdf as exporter
from rdflib import Graph, Literal
from rdflib.compare import isomorphic
from rdflib.namespace import OWL, RDF, RDFS, SKOS, XSD

SOURCE = ROOT / "workshop" / "v2.7.0" / "ontology" / "ontology-full-definition-template.json"


class OntologyRdfTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = SOURCE.read_bytes()
        cls.template = json.loads(cls.raw)
        cls.graph = exporter.build_graph(cls.template, exporter.digest(cls.raw))

    def changed(self, mutate):
        template = copy.deepcopy(self.template)
        mutate(template)
        template["definitionTemplateSha256"] = exporter.digest(exporter.canonical(template["parts"]))
        return template

    def test_exact_full_schema_and_no_donation_instances(self):
        g, f, m = self.graph, exporter.F, exporter.M
        self.assertEqual(len(set(g.subjects(RDF.type, OWL.Class))), 10)
        self.assertEqual(len(set(g.subjects(RDF.type, OWL.DatatypeProperty))), 73)
        self.assertEqual(len(set(g.subjects(RDF.type, OWL.ObjectProperty))), 15)
        self.assertEqual(len(set(g.subjects(m.propertyKind, Literal("static")))), 72)
        self.assertEqual(len(set(g.subjects(m.propertyKind, Literal("timeSeries")))), 1)
        self.assertEqual(len(list(g.triples((None, m.hasDataBinding, None)))), 11)
        self.assertEqual(len(list(g.triples((None, m.hasContextualization, None)))), 15)
        self.assertFalse(list(g.triples((None, RDF.type, OWL.NamedIndividual))))
        for cls in g.subjects(RDF.type, OWL.Class):
            self.assertFalse(list(g.triples((None, RDF.type, cls))))
        self.assertIn((f.Donation__DonationAmountYen, RDFS.range, XSD.long), g)
        self.assertIn((f.Donation__DonatedAtUtc, RDFS.range, XSD.dateTime), g)
        self.assertIn((f.Donation__DonationDateJst, RDFS.range, XSD.string), g)

    def test_each_relationship_retains_declared_direction_and_cardinality_annotation(self):
        for part in self.template["parts"]:
            if not part["path"].startswith("RelationshipTypes/") or not part["path"].endswith("/definition.json"):
                continue
            rel = part["content"]
            g, f, m = self.graph, exporter.F, exporter.M
            entities = {str(g.value(uri, m.entityTypeId)): uri for uri in g.subjects(RDF.type, OWL.Class)}
            uri = f[rel["name"]]
            with self.subTest(relationship=rel["name"]):
                self.assertEqual(g.value(uri, RDFS.domain), entities[rel["source"]["entityTypeId"]])
                self.assertEqual(g.value(uri, RDFS.range), entities[rel["target"]["entityTypeId"]])
                self.assertEqual(str(g.value(uri, m.cardinality)), rel["semanticEnrichment"]["customAttributes"]["cardinality"])
        self.assertFalse(list(self.graph.triples((None, OWL.hasKey, None))))
        self.assertFalse(list(self.graph.triples((None, OWL.cardinality, None))))
        self.assertFalse(list(self.graph.triples((None, OWL.inverseOf, None))))
        self.assertFalse(list(self.graph.triples((None, RDF.type, OWL.FunctionalProperty))))

    def test_all_nonplatform_parts_round_trip_losslessly_as_annotations(self):
        recovered = {
            str(path): json.loads(str(self.graph.value(subject, exporter.M.definitionJson)))
            for subject, _, path in self.graph.triples((None, exporter.M.definitionPart, None))
        }
        expected = {part["path"]: part["content"] for part in self.template["parts"] if part["path"] != ".platform"}
        self.assertEqual(recovered, expected)
        self.assertEqual(len(recovered), 53)

    def test_nonstandard_predicates_have_explicit_property_declarations(self):
        standard = {RDF.type, RDFS.label, RDFS.comment, RDFS.domain, RDFS.range, OWL.versionInfo}
        declared = {
            subject
            for kind in (OWL.AnnotationProperty, OWL.ObjectProperty, OWL.DatatypeProperty)
            for subject in self.graph.subjects(RDF.type, kind)
        }
        self.assertEqual(set(self.graph.predicates()) - standard - declared, set())
        self.assertIn((SKOS.altLabel, RDF.type, OWL.AnnotationProperty), self.graph)

    def test_every_property_domain_datatype_key_and_display_mapping_matches_source(self):
        g, m = self.graph, exporter.M
        ranges = {"BigInt": XSD.long, "String": XSD.string, "DateTime": XSD.dateTime}
        checked = 0
        for part in self.template["parts"]:
            if not part["path"].startswith("EntityTypes/") or part["path"].count("/") != 2:
                continue
            entity = part["content"]
            uri = g.value(predicate=m.entityTypeId, object=Literal(entity["id"]))
            self.assertIsNotNone(uri)
            self.assertEqual(g.value(uri, RDFS.label), Literal(entity["name"]))
            by_id = {}
            for prop_uri in g.subjects(RDFS.domain, uri):
                if (prop_uri, RDF.type, OWL.DatatypeProperty) in g:
                    by_id[str(g.value(prop_uri, m.propertyId))] = prop_uri
            all_properties = entity["properties"] + entity.get("timeseriesProperties", [])
            self.assertEqual(set(by_id), {prop["id"] for prop in all_properties})
            for field, kind in (("properties", "static"), ("timeseriesProperties", "timeSeries")):
                for prop in entity.get(field, []):
                    prop_uri = by_id[prop["id"]]
                    with self.subTest(entity=entity["name"], property=prop["name"]):
                        self.assertEqual(set(g.objects(prop_uri, RDFS.domain)), {uri})
                        self.assertEqual(set(g.objects(prop_uri, RDFS.range)), {ranges[prop["valueType"]]})
                        self.assertEqual(g.value(prop_uri, RDFS.label), Literal(prop["name"]))
                        self.assertEqual(g.value(prop_uri, m.propertyKind), Literal(kind))
                        enrich = prop.get("semanticEnrichment", {})
                        self.assertEqual(g.value(prop_uri, RDFS.comment), Literal(enrich["description"]) if enrich.get("description") else None)
                        self.assertEqual(set(g.objects(prop_uri, SKOS.altLabel)), {Literal(x) for x in enrich.get("synonyms", [])})
                    checked += 1
            keys = sorted(g.objects(uri, m.keyProperty), key=lambda key: int(g.value(key, m.keyPosition)))
            self.assertEqual(keys, [by_id[key] for key in entity["entityIdParts"]])
            self.assertEqual(g.value(uri, m.displayNameProperty), by_id[entity["displayNamePropertyId"]])
        self.assertEqual(checked, 73)

    def test_every_binding_and_contextualization_retains_owner_source_and_ordered_columns(self):
        g, m = self.graph, exporter.M
        entities = {str(g.value(uri, m.entityTypeId)): uri for uri in g.subjects(RDF.type, OWL.Class)}
        relationships = {str(g.value(uri, m.relationshipTypeId)): uri for uri in g.subjects(RDF.type, OWL.ObjectProperty)}
        checked = 0
        for part in self.template["parts"]:
            path, content = part["path"], part["content"]
            if "/DataBindings/" in path:
                owner = entities[path.split("/")[1]]
                relation = m.hasDataBinding
                config = content["dataBindingConfiguration"]
                source = config["sourceTableProperties"]
                mappings = [(m.hasPropertyBinding, owner, config["propertyBindings"])]
            elif "/Contextualizations/" in path:
                owner = relationships[path.split("/")[1]]
                relation = m.hasContextualization
                source = content["dataBindingTable"]
                mappings = [
                    (m.sourceKeyBinding, g.value(owner, RDFS.domain), content["sourceKeyRefBindings"]),
                    (m.targetKeyBinding, g.value(owner, RDFS.range), content["targetKeyRefBindings"]),
                ]
            else:
                continue
            node = g.value(predicate=m.definitionPart, object=Literal(path))
            with self.subTest(part=path):
                self.assertIn((owner, relation, node), g)
                for name, value in source.items():
                    self.assertEqual(g.value(node, m[name]), Literal(value))
                for predicate, entity_uri, original in mappings:
                    projected = []
                    for binding in sorted(g.objects(node, predicate), key=lambda item: int(g.value(item, m.bindingPosition))):
                        prop = g.value(binding, m.property)
                        self.assertEqual(g.value(prop, RDFS.domain), entity_uri)
                        projected.append({"sourceColumnName": str(g.value(binding, m.sourceColumnName)),
                                          "targetPropertyId": str(g.value(prop, m.propertyId))})
                    self.assertEqual(projected, original)
            checked += 1
        self.assertEqual(checked, 26)

    def test_timeseries_has_actual_timestamp_column_and_property_mapping(self):
        g, f, m = self.graph, exporter.F, exporter.M
        bindings = list(g.subjects(m.dataBindingType, Literal("TimeSeries")))
        self.assertEqual(len(bindings), 1)
        node = bindings[0]
        self.assertEqual(g.value(node, m.timestampColumnName), Literal("DonatedAt"))
        self.assertEqual(g.value(node, m.sourceTableName), Literal("DonationEvents"))
        self.assertEqual(g.value(node, m.itemId), Literal("{{source.eventhouse.id}}"))
        mapped = {
            (g.value(item, m.property), str(g.value(item, m.sourceColumnName)))
            for item in g.objects(node, m.hasPropertyBinding)
        }
        self.assertIn((f.Municipality__IncomingDonationAmountYen, "DonationAmountYen"), mapped)
        self.assertIn((f.Municipality__MunicipalityId, "MunicipalityID"), mapped)

    def test_three_formats_parse_to_the_same_graph_with_stable_bytes(self):
        first = exporter.artifacts(SOURCE)
        self.assertEqual(first, exporter.artifacts(SOURCE))
        self.assertEqual(first["furusato-ontology.rdf"], first["furusato-ontology.owl"])
        for name, format_name in exporter.FORMATS.items():
            graph = Graph().parse(data=first[name], format=format_name)
            self.assertTrue(isomorphic(self.graph, graph), name)
        self.assertEqual(first["SHA256SUMS.txt"].count(b"\n"), 3)
        self.assertNotIn(b"\r", first["SHA256SUMS.txt"])

    def test_shipped_exports_match_current_source(self):
        exporter.export(SOURCE, SOURCE.parent / "rdf", check=True)

    def test_check_is_read_only_and_detects_corruption(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "absent"
            with self.assertRaisesRegex(exporter.ExportError, "Missing/stale"):
                exporter.export(SOURCE, output, check=True)
            self.assertFalse(output.exists())
            exporter.export(SOURCE, output)
            (output / "furusato-ontology.ttl").write_bytes(b"corrupt")
            before = {p.name: p.read_bytes() for p in output.iterdir()}
            with self.assertRaisesRegex(exporter.ExportError, "Missing/stale"):
                exporter.export(SOURCE, output, check=True)
            self.assertEqual(before, {p.name: p.read_bytes() for p in output.iterdir()})

    def test_stale_source_seal_is_rejected(self):
        bad = copy.deepcopy(self.template)
        bad["definitionTemplateSha256"] = "0" * 64
        with self.assertRaisesRegex(exporter.ExportError, "seal"):
            exporter.build_graph(bad, "0" * 64)

    def test_duplicate_and_unknown_parts_are_rejected(self):
        for mutate in (
            lambda t: t["parts"].__setitem__(-1, copy.deepcopy(t["parts"][0])),
            lambda t: t["parts"][2].update(path="Unknown/new-preview-part.json"),
        ):
            with self.subTest(mutate=mutate), self.assertRaises(exporter.ExportError):
                exporter.build_graph(self.changed(mutate), "0" * 64)

    def test_unresolved_relationship_endpoint_is_rejected(self):
        def change(t):
            part = next(p for p in t["parts"] if p["path"].startswith("RelationshipTypes/") and p["path"].endswith("/definition.json"))
            part["content"]["target"]["entityTypeId"] = "unknown"
        with self.assertRaisesRegex(exporter.ExportError, "endpoint"):
            exporter.build_graph(self.changed(change), "0" * 64)

    def test_cross_entity_property_binding_is_rejected(self):
        def change(t):
            next(p for p in t["parts"] if "/DataBindings/" in p["path"])["content"]["dataBindingConfiguration"]["propertyBindings"][0]["targetPropertyId"] = "unknown"
        with self.assertRaisesRegex(exporter.ExportError, "property owned"):
            exporter.build_graph(self.changed(change), "0" * 64)

    def test_missing_composite_key_member_is_rejected(self):
        def change(t):
            part = next(p for p in t["parts"] if "/Contextualizations/" in p["path"])
            part["content"]["sourceKeyRefBindings"] = []
        with self.assertRaisesRegex(exporter.ExportError, "composite key"):
            exporter.build_graph(self.changed(change), "0" * 64)

    def test_timeseries_without_timestamp_is_rejected(self):
        def change(t):
            config = next(p["content"]["dataBindingConfiguration"] for p in t["parts"] if "/DataBindings/" in p["path"]
                          and p["content"]["dataBindingConfiguration"]["dataBindingType"] == "TimeSeries")
            del config["timestampColumnName"]
        with self.assertRaisesRegex(exporter.ExportError, "timestamp"):
            exporter.build_graph(self.changed(change), "0" * 64)

    def test_live_deployment_identity_is_not_exported(self):
        def change(t):
            source = next(p["content"]["dataBindingConfiguration"]["sourceTableProperties"] for p in t["parts"] if "/DataBindings/" in p["path"])
            source["workspaceId"] = "11111111-2222-3333-4444-555555555555"
        with self.assertRaisesRegex(exporter.ExportError, "portable placeholder"):
            exporter.build_graph(self.changed(change), "0" * 64)

    def test_unknown_datatype_is_not_guessed(self):
        def change(t):
            part = next(p for p in t["parts"] if p["path"].startswith("EntityTypes/") and "/DataBindings/" not in p["path"] and p["content"].get("properties"))
            part["content"]["properties"][0]["valueType"] = "Object"
        with self.assertRaisesRegex(exporter.ExportError, "valueType"):
            exporter.build_graph(self.changed(change), "0" * 64)


if __name__ == "__main__":
    unittest.main()
