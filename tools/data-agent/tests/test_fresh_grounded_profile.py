import copy
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import fresh_grounded_profile as fresh
import test_answer_contract_profile as fixtures
from source_grounded_profile import VIEW_DESCRIPTIONS, decoded_parts, inline_part
from answer_contract_profile import SCHEMA_VIEWS


class FreshProfileTests(unittest.TestCase):
    def fixture(self):
        definition, _ = fixtures.ContractTests().grounding_fixture()
        docs = decoded_parts(definition)
        selected = {p: v for p, v in docs.items()
                    if p == "Files/Config/data_agent.json" or
                    ("/draft/" in p and (p.endswith("stage_config.json") or p.endswith("datasource.json")))}
        sql = selected["Files/Config/draft/lakehouse_tables/datasource.json"]
        root = sql["elements"][0]
        root["display_name"] = "Schemas"
        schema = root["children"][0]
        views, tables = schema["children"]
        views["display_name"], tables["display_name"] = "Views", "Tables"
        for name in ("ot_municipality", "ot_donation", "ot_supplier", "ot_supplier_gift"):
            tables["children"].append({"id": "native-" + name, "display_name": name,
                                       "type": "lakehouse_tables.table", "is_selected": True,
                                       "children": []})
        existing = {v["display_name"]: v for v in views["children"]}
        for name in VIEW_DESCRIPTIONS:
            if name not in existing:
                view = {"id": "native-" + name, "display_name": name,
                        "type": "lakehouse_tables.view", "is_selected": False,
                        "children": [{"id": name + "-key", "display_name": "StableId",
                                      "type": "lakehouse_tables.column", "data_type": "varchar",
                                      "is_selected": False}]}
                views["children"].append(view)
                existing[name] = view
        columns = [{"TABLE_NAME": view["display_name"], "COLUMN_NAME": col["display_name"],
                    "DATA_TYPE": col["data_type"]}
                   for view in views["children"] if view["display_name"] in set(VIEW_DESCRIPTIONS) | set(SCHEMA_VIEWS)
                   for col in view["children"]]
        return {"parts": [inline_part(p, v) for p, v in selected.items()]}, columns

    def test_complete_draft_uses_all_current_profiles_without_cloud_calls(self):
        definition, columns = self.fixture()
        saved = copy.deepcopy(definition)
        result, receipt = fresh.compile_fresh_profile(definition, columns)
        self.assertEqual(definition, saved)
        after = decoded_parts(result)
        self.assertFalse(any("/published/" in p for p in after))
        self.assertEqual(receipt["cloudCalls"], 0)
        self.assertEqual(receipt["compilerStages"][-1]["exampleCounts"], {"lakehouse_tables": 15, "kusto": 6})
        self.assertNotIn("StaticSyntheticSnapshot", json.dumps(after))
        before = decoded_parts(definition)
        for path, value in after.items():
            if path.endswith("datasource.json"):
                for key in ("artifactId", "workspaceId", "type"):
                    self.assertEqual(value[key], before[path][key])
        self.assertEqual(result, fresh.compile_fresh_profile(definition, columns)[0])

    def test_missing_verified_view_or_duplicate_column_is_refused(self):
        definition, columns = self.fixture()
        with self.assertRaises(ValueError):
            fresh.compile_fresh_profile(definition, [r for r in columns if r["TABLE_NAME"] != "agent_relationship_dictionary"])
        bad = copy.deepcopy(definition)
        docs = decoded_parts(bad)
        views = docs["Files/Config/draft/lakehouse_tables/datasource.json"]["elements"][0]["children"][0]["children"][0]["children"]
        views.append(copy.deepcopy(views[0]))
        with self.assertRaises(ValueError):
            fresh.compile_fresh_profile({"parts": [inline_part(p, v) for p, v in docs.items()]}, columns)


if __name__ == "__main__":
    unittest.main()
