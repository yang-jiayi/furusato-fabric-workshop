"""Offline native-shape patch tests; not Instances or cloud execution evidence."""
import base64
import unittest
from preview30_native_binding import prepare_patch, _decode


def part(path, text):
    return {"path": path, "payloadType": "InlineBase64",
            "payload": base64.b64encode(text.encode()).decode()}


class NativeBindingPatchTests(unittest.TestCase):
    def setUp(self):
        self.definition = {"parts": [
            part("expressions.tmdl", 'expression DatabaseQuery =\n\t\tlet\n\t\t    database = Sql.Database("example", "old")\n\t\tin\n\t\t    database\n\tlineageTag: retained-expression\n'),
            part("tables/ot_municipality.tmdl", "table ot_municipality\n\tlineageTag: retained-table\n\tcolumn MunicipalityId\n\t\tdataType: string\n\t\tlineageTag: retained-column\n\t\tsourceColumn: MunicipalityId\n\tpartition ot_municipality = entity\n\t\tmode: directLake\n\t\tsource\n\t\t\tentityName: ot_municipality\n\t\t\tschemaName: dbo\n\t\t\texpressionSource: DatabaseQuery\n"),
            part("entities/Municipality.tmdl", "entity Municipality\n\tlineageTag: retained-entity\n\tbackingTable: ot_municipality\n"),
            part("model.tmdl", "model Model\n\nreusableProperty SharedName\n\tlineageTag: keep-shared\n"),
        ]}
        self.kwargs = dict(
            workspace_id="11111111-1111-4111-8111-111111111111",
            lakehouse_id="22222222-2222-4222-8222-222222222222",
            lakehouse_name="Example_Lakehouse", workspace_name="Example Workspace",
            sql_endpoint="example.datawarehouse.fabric.microsoft.com",
            pinned_at_utc="2026-01-01T00:00:00Z",
            one_lake_root_url="https://onelake.dfs.fabric.microsoft.com/11111111-1111-4111-8111-111111111111/22222222-2222-4222-8222-222222222222",
            table_names=["ot_municipality"])

    def test_native_shape_preserves_ids_and_shared_definitions(self):
        candidate, proof = prepare_patch(self.definition, **self.kwargs)
        after = _decode(candidate)
        self.assertIn("AzureStorage.DataLake", after["expressions.tmdl"])
        self.assertNotIn("Sql.Database(", after["expressions.tmdl"])
        self.assertIn("annotation ONT_ItemKind = Lakehouse", after["tables/ot_municipality.tmdl"])
        self.assertIn("annotation ONT_SqlDatabase = Example_Lakehouse", after["tables/ot_municipality.tmdl"])
        self.assertEqual(after["model.tmdl"], _decode(self.definition)["model.tmdl"])
        self.assertTrue(proof["lineageIdsPreserved"])
        self.assertEqual(proof["status"], "prepared-not-applied")

    def test_wrong_lakehouse_locator_refused(self):
        self.kwargs["one_lake_root_url"] += "/different"
        with self.assertRaises(ValueError):
            prepare_patch(self.definition, **self.kwargs)

    def test_native_expression_name_changes_references_not_lineages(self):
        candidate, proof = prepare_patch(self.definition, **self.kwargs,
                                         target_expression_name="DirectLake - Example_Lakehouse")
        after = _decode(candidate)
        self.assertIn("expression 'DirectLake - Example_Lakehouse' =", after["expressions.tmdl"])
        self.assertIn("expressionSource: 'DirectLake - Example_Lakehouse'",
                      after["tables/ot_municipality.tmdl"])
        self.assertTrue(proof["lineageIdsPreserved"])

    def test_metrics_roundtrip_refused(self):
        self.definition["parts"].append(part("metrics/NativeMetric.tmdl", "metric NativeMetric\n"))
        with self.assertRaises(ValueError):
            prepare_patch(self.definition, **self.kwargs)

    def test_annotation_injection_refused(self):
        self.kwargs["workspace_name"] = "Example\nannotation Bad = 1"
        with self.assertRaises(ValueError):
            prepare_patch(self.definition, **self.kwargs)


if __name__ == "__main__":
    unittest.main()
