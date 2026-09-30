"""Offline checks for the standards-only business RDF candidate."""

import hashlib
import json
from pathlib import Path
import sys
import unittest

from rdflib import BNode, Graph, Literal, URIRef
from rdflib.namespace import OWL, RDF, RDFS, XSD

sys.path.insert(0, str(Path(__file__).resolve().parent))
import preview30_native_rdf as native


class NativeRdfTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = native.SOURCE.read_bytes()
        cls.source = Graph().parse(data=cls.raw, format="turtle")
        cls.candidate = native.build_candidate(cls.source)

    def changed(self):
        return Graph() + self.source

    def test_full_business_schema_without_runtime_equivalence_claim(self):
        counts = native.counts(self.candidate)
        self.assertEqual((counts["classes"], counts["datatype_properties"], counts["object_properties"]),
                         (10, 73, 15))
        self.assertEqual((counts["domains"], counts["ranges"]), (88, 88))
        subjects = {s for kind in native.KINDS for s in self.source.subjects(RDF.type, kind)}
        expected = {(s, p, o) for s, p, o in self.source if s in subjects and p in native.BUSINESS_PREDICATES}
        actual = {(s, p, o) for s, p, o in self.candidate if s in subjects}
        self.assertEqual(actual, expected)
        self.assertEqual(len(subjects), 98)

    def test_standards_only_and_no_instances_or_blank_nodes(self):
        for subject, predicate, value in self.candidate:
            self.assertIsInstance(subject, URIRef)
            self.assertNotIsInstance(value, BNode)
            self.assertIn(predicate, native.BUSINESS_PREDICATES | {OWL.versionInfo})
            self.assertFalse(str(predicate).startswith(str(native.rdf_export.M)))
        self.assertFalse(list(self.candidate.subjects(RDF.type, OWL.AnnotationProperty)))
        for kind in self.candidate.subjects(RDF.type, OWL.Class):
            self.assertFalse(list(self.candidate.subjects(RDF.type, kind)))
        self.assertFalse(list(self.candidate.subjects(RDF.type, OWL.NamedIndividual)))

    def test_all_domains_and_ranges_resolve(self):
        classes = set(self.candidate.subjects(RDF.type, OWL.Class))
        for kind in (OWL.DatatypeProperty, OWL.ObjectProperty):
            for subject in self.candidate.subjects(RDF.type, kind):
                domains = set(self.candidate.objects(subject, RDFS.domain))
                ranges = set(self.candidate.objects(subject, RDFS.range))
                self.assertEqual(len(domains), 1)
                self.assertEqual(len(ranges), 1)
                self.assertLessEqual(domains, classes)
                allowed = classes if kind == OWL.ObjectProperty else set(native.rdf_export.DATATYPES.values())
                self.assertLessEqual(ranges, allowed)
        self.assertIn((native.rdf_export.F.Donation__DonatedAtUtc, RDFS.range, XSD.dateTime), self.candidate)

    def test_manifest_determinism_and_explicit_losses(self):
        first, second = native.artifacts(), native.artifacts()
        self.assertEqual(first, second)
        manifest = json.loads(first["manifest.json"])
        self.assertEqual(manifest["candidate"]["sha256"], hashlib.sha256(first[native.TTL_NAME]).hexdigest())
        self.assertEqual(manifest["source_counts"]["triples"], 2532)
        self.assertEqual(manifest["candidate_counts"]["triples"], 474)
        self.assertEqual(manifest["source_counts"]["fabric_predicate_triples"], 1864)
        self.assertEqual(manifest["candidate_counts"]["fabric_predicate_triples"], 0)
        self.assertEqual(manifest["source_counts"]["skos_alternative_labels"], 103)
        self.assertEqual(manifest["candidate_counts"]["skos_alternative_labels"], 0)
        self.assertEqual(manifest["candidate_counts"]["data_bindings"], 0)
        self.assertFalse(manifest["native_import"]["success_proven"])
        self.assertFalse(manifest["native_import"]["product_root_cause_proven"])
        self.assertEqual(native.SOURCE.read_bytes(), self.raw)
        self.assertEqual(hashlib.sha256(self.raw).hexdigest(), native.SOURCE_SHA256)

    def test_turtle_is_independent_of_graph_insertion_order(self):
        reversed_graph = Graph()
        for triple in reversed(native.rdf_export.sorted_triples(self.candidate)):
            reversed_graph.add(triple)
        data = native.turtle_bytes(self.candidate)
        self.assertEqual(data, native.turtle_bytes(reversed_graph))
        self.assertEqual(set(Graph().parse(data=data, format="turtle")), set(self.candidate))
        self.assertNotIn(b"fabric:", data)
        self.assertNotIn(str(native.rdf_export.M).encode(), data)

    def test_rejects_dangling_domain_and_object_range(self):
        prop = native.rdf_export.F.MunicipalityInPrefecture
        for predicate in (RDFS.domain, RDFS.range):
            with self.subTest(predicate=str(predicate)):
                graph = self.changed()
                graph.set((prop, predicate, native.rdf_export.F.RecipientMunicipality))
                with self.assertRaisesRegex(native.CandidateError, "Dangling"):
                    native.build_candidate(graph)

    def test_rejects_ambiguous_domain_and_unsupported_datatype(self):
        graph = self.changed()
        graph.add((native.rdf_export.F.DonationToMunicipality, RDFS.domain, native.rdf_export.F.Donor))
        with self.assertRaisesRegex(native.CandidateError, "unambiguous"):
            native.build_candidate(graph)
        graph = self.changed()
        graph.set((native.rdf_export.F.Donation__DonationAmountYen, RDFS.range, native.rdf_export.F.Currency))
        with self.assertRaisesRegex(native.CandidateError, "unsupported"):
            native.build_candidate(graph)

    def test_rejects_missing_labels_and_unmapped_axioms(self):
        graph = self.changed()
        graph.remove((native.rdf_export.F.Donor, RDFS.label, None))
        with self.assertRaisesRegex(native.CandidateError, "label"):
            native.build_candidate(graph)
        graph = self.changed()
        graph.add((native.rdf_export.F.Donor, RDFS.subClassOf, native.rdf_export.F.Prefecture))
        with self.assertRaisesRegex(native.CandidateError, "Unmapped"):
            native.build_candidate(graph)


if __name__ == "__main__":
    unittest.main()
