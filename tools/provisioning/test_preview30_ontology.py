"""Candidate shape checks. Passing does not prove a native service deployment."""
import unittest
from preview30_ontology import generate, encode_definition
from preview30_runtime import BASE, load


class Generation2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parts, cls.contract = generate(load(BASE / "ontology" / "ontology-full-definition-template.json"))

    def test_not_legacy_wire(self):
        self.assertIn("database.tmdl", self.parts)
        self.assertIn("compatibilityLevel: 1000000", self.parts["database.tmdl"])
        self.assertFalse(any(p.startswith("EntityTypes/") or p == "definition.json" for p in self.parts))

    def test_exact_business_inventory(self):
        self.assertEqual(len([p for p in self.parts if p.startswith("entities/")]), 10)
        self.assertEqual(sum(len(e["properties"]) for e in self.contract["entities"]), 72)
        self.assertEqual(sum(line.startswith("entityRelationship ") for line in
                             self.parts["entityRelationships.tmdl"].splitlines()), 15)
        self.assertEqual(len(self.contract["relationships"]), 15)
        self.assertEqual(len([p for p in self.parts if p.startswith("tables/")]), 11)

    def test_entity_names_are_business_concepts_not_test_labels(self):
        self.assertEqual({e["name"] for e in self.contract["entities"]}, {
            "Prefecture", "Municipality", "Donor", "GiftCategory", "Gift",
            "Supplier", "Donation", "MunicipalityCategoryMetric",
            "PrefectureCategoryMetric", "PrefectureDonationFlow",
        })
        for entity in self.contract["entities"]:
            self.assertNotRegex(entity["name"], r"(?i)(?:Demo|Test|Sample|Example)(?:\d+)?$")

    def test_one_supplier_junction(self):
        self.assertIn("\t\ttype: table\n\t\ttable: ot_supplier_gift",
                      self.parts["entityRelationships.tmdl"])
        self.assertFalse(any(e["sourceTable"] == "ot_supplier_gift" for e in self.contract["entities"]))

    def test_property_counts_do_not_proxy_backing_columns(self):
        import re
        columns = {path: re.findall(r"^\tcolumn (.+)$", text, re.MULTILINE)
                   for path, text in self.parts.items() if path.startswith("tables/")}
        self.assertEqual(sum(len(value) for value in columns.values()), 88)
        self.assertEqual(len(columns["tables/ot_supplier_gift.tmdl"]), 2)
        municipality = self.parts["entities/Municipality.tmdl"]
        self.assertIn("PrefectureId", columns["tables/ot_municipality.tmdl"])
        self.assertNotRegex(municipality, r"(?m)^\tproperty PrefectureId$")
        self.assertEqual(len(re.findall(r"^\tproperty ", municipality, re.MULTILINE)), 8)

    def test_native_gap_is_not_hidden(self):
        self.assertEqual(self.contract["timeSeriesBinding"]["status"], "requires-native-contract")
        self.assertFalse(self.contract["nativeMetrics"]["tmdlProjectionSupported"])
        self.assertFalse(any(p.startswith("metrics/") for p in self.parts))
        self.assertIn("requires-native-Eventhouse-binding", self.parts["entities/Municipality.tmdl"])

    def test_deterministic_generation(self):
        other, contract = generate(load(BASE / "ontology" / "ontology-full-definition-template.json"))
        self.assertEqual((self.parts, self.contract), (other, contract))

    def test_unbound_environment_is_refused(self):
        with self.assertRaises(ValueError):
            encode_definition(self.parts, {})

    def test_native_lakehouse_locator_is_not_sql_endpoint_guid(self):
        expression = self.parts["expressions.tmdl"]
        self.assertIn("AzureStorage.DataLake", expression)
        self.assertNotIn("Sql.Database(", expression)
        for path, text in self.parts.items():
            if path.startswith("tables/"):
                self.assertIn("annotation ONT_ItemKind = Lakehouse", text)
                self.assertIn("annotation ONT_ItemId = {{source.lakehouse.id}}", text)
                self.assertIn("annotation ONT_SqlDatabase = {{source.lakehouse.displayName}}", text)
                self.assertIn("annotation ONT_PinnedAtUtc = {{source.binding.pinnedAtUtc}}", text)

    def test_namespaces_and_rules(self):
        self.assertIn("ref namespace default", self.parts["model.tmdl"])
        self.assertEqual(len([p for p in self.parts if p.startswith("rules/")]), 4)
        self.assertFalse(self.contract["graph"]["default"])


if __name__ == "__main__":
    unittest.main()
