"""Wire ordering is required by Fabric even when semantic hashes are canonical."""
import base64
import copy
import json
from pathlib import Path
import sys
import types
import unittest
import uuid

import reference_ontology

ROOT = Path(__file__).resolve().parents[2]
NOTEBOOKS = ROOT / "workshop" / "v2.7.0" / "notebooks"


class OntologyWireTests(unittest.TestCase):
    def document(self):
        return {
            "dataBindingConfiguration": {
                "sourceTableProperties": {
                    "itemId": "item", "sourceSchema": "dbo",
                    "sourceType": "LakehouseTable", "workspaceId": "workspace",
                },
            },
            "nested": [{"itemId": "eventhouse", "sourceType": "KustoTable", "databaseName": "db"}],
        }

    def check_wire(self, raw, original):
        actual = json.loads(raw)
        self.assertEqual(actual, original)
        self.assertEqual(next(iter(actual["dataBindingConfiguration"]["sourceTableProperties"])), "sourceType")
        self.assertEqual(next(iter(actual["nested"][0])), "sourceType")
        self.assertEqual(reference_ontology.canonical(actual), reference_ontology.canonical(original))

    def test_discriminator_order_does_not_mutate_values_or_semantic_hashes(self):
        original = self.document()
        before = copy.deepcopy(original)
        self.check_wire(reference_ontology.ontology_json_bytes(original), original)
        self.assertEqual(original, before)

    def test_every_standalone_notebook_uses_the_same_wire_contract(self):
        for number in (2, 3, 4):
            path = next(NOTEBOOKS.glob(f"Notebook_{number:02}_*.ipynb"))
            notebook = json.loads(path.read_text(encoding="utf-8"))
            code = next(
                "".join(cell["source"]) for cell in notebook["cells"]
                if "def _encode_part_json(" in "".join(cell.get("source", []))
            )
            module = types.ModuleType(f"_ontology_wire_notebook_{number}")
            sys.modules[module.__name__] = module
            exec(compile(code, str(path), "exec"), module.__dict__)
            with self.subTest(notebook=number):
                self.check_wire(base64.b64decode(module._encode_part_json(self.document())), self.document())

    def test_path_platform_has_a_stable_workspace_scoped_logical_id(self):
        path = ROOT / "workshop" / "v2.7.0" / "provisioning" / "bundle" / "ai-reference" / "ontology-template.json"
        template = json.loads(path.read_text(encoding="utf-8"))
        workspace = "11111111-1111-1111-1111-111111111111"
        def logical_id(workspace_id):
            definition = reference_ontology.materialize_path_definition(
                template, workspace_id=workspace_id,
                lakehouse_id="22222222-2222-2222-2222-222222222222",
                display_name="ONT_Furusato_AIPath_912",
            )
            platform = json.loads(base64.b64decode(next(p["payload"] for p in definition["parts"] if p["path"] == ".platform")))
            self.assertEqual(platform["config"]["version"], "2.0")
            return platform["config"]["logicalId"]
        first = logical_id(workspace)
        self.assertEqual(str(uuid.UUID(first)), first)
        self.assertEqual(first, logical_id(workspace))
        self.assertNotEqual(first, logical_id("33333333-3333-3333-3333-333333333333"))

    def test_path_graph_counts_include_the_relationship_only_bridge(self):
        path = ROOT / "workshop" / "v2.7.0" / "provisioning" / "bundle" / "ai-reference" / "ontology-template.json"
        template = json.loads(path.read_text(encoding="utf-8"))
        tables = set()
        def visit(value):
            if isinstance(value, dict):
                if value.get("sourceType") == "LakehouseTable":
                    tables.add(value["sourceTableName"])
                for child in value.values():
                    visit(child)
            elif isinstance(value, list):
                for child in value:
                    visit(child)
        visit(template["parts"])
        self.assertIn("ot_supplier_gift", tables)
        self.assertEqual(len(tables), 11)
        self.assertEqual(reference_ontology.PATH_GRAPH_COUNTS["dataSources"], len(tables))


if __name__ == "__main__":
    unittest.main()
