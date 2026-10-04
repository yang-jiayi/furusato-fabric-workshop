import copy
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import time_layer_isolation as isolation
from answer_contract_profile import PROFILE as BASE, SOURCES
from source_grounded_profile import decoded_parts, inline_part


class TimeLayerIsolationTests(unittest.TestCase):
    def fixture(self):
        documents = {
            "Files/Config/data_agent.json": {"$schema": "2.1.0"},
            "Files/Config/publish_info.json": {"description": "unchanged"},
            "Files/Config/published/stage_config.json": {
                "aiInstructions": (BASE / "global-instructions.txt").read_text(encoding="utf-8").strip(),
                "experimental": {"codeInterpreterEnabled": True, "enableExperimentalFeatures": True},
            },
        }
        rows = json.loads((BASE / "examples.json").read_bytes())["examples"]
        for kind, (filename, description) in SOURCES.items():
            prefix = "Files/Config/published/" + kind + "/"
            documents[prefix + "datasource.json"] = {
                "type": kind, "artifactId": "item-" + kind, "workspaceId": "workspace",
                "dataSourceInstructions": (BASE / filename).read_text(encoding="utf-8").strip(),
                "userDescription": description, "metadata": {"opaque": [1, "retain"]},
                "elements": [{"id": "other-" + kind, "is_selected": True}],
            }
            examples = [r for r in rows if r["sourceType"] == kind]
            if examples:
                documents[prefix + "fewshots.json"] = {"fewShots": [
                    {"id": kind + str(i), "question": row["question"], "query": row["query"]}
                    for i, row in enumerate(examples)
                ]}
        documents["Files/Config/published/lakehouse_tables/datasource.json"]["elements"] = [{
            "display_name": "Schemas", "type": "schema_grouping", "id": "root", "is_selected": True,
            "children": [{
                "display_name": "dbo", "type": "lakehouse_tables.schema", "id": "dbo", "is_selected": True,
                "children": [{
                    "display_name": "Views", "type": "view_grouping", "id": "views", "is_selected": True,
                    "children": [{
                        "display_name": "agent_donation_detail", "type": "lakehouse_tables.view",
                        "id": "detail", "is_selected": True, "children": [
                            {"display_name": "DonationDataLayer", "type": "lakehouse_tables.column",
                             "id": "tag", "is_selected": True, "description": "The value is StaticSyntheticSnapshot."},
                            {"display_name": "DonationId", "type": "lakehouse_tables.column",
                             "id": "key", "is_selected": True, "description": "business identity"},
                        ],
                    }],
                }],
            }],
        }]
        documents["Files/Config/published/lakehouse_tables/topic.json"] = {"opaque": "preserve"}
        return {"parts": [inline_part(path, value) for path, value in documents.items()]}

    def test_published_parts_original_and_runtime_are_preserved(self):
        original = self.fixture()
        saved = copy.deepcopy(original)
        result, receipt = isolation.compile_isolated_draft(original)
        self.assertEqual(original, saved)
        before, after = decoded_parts(original), decoded_parts(result)
        for path, value in before.items():
            self.assertEqual(after[path], value)
        self.assertEqual(after["Files/Config/draft/stage_config.json"]["experimental"],
                         before["Files/Config/published/stage_config.json"]["experimental"])
        self.assertEqual(after["Files/Config/draft/lakehouse_tables/topic.json"], {"opaque": "preserve"})
        self.assertEqual(receipt["cloudCalls"], 0)
        self.assertFalse(receipt["baseDataAndModelMeasuresChanged"])

    def test_only_the_named_constant_column_is_deselected(self):
        original = self.fixture()
        result, receipt = isolation.compile_isolated_draft(original)
        after = decoded_parts(result)
        columns = after["Files/Config/draft/lakehouse_tables/datasource.json"]["elements"][0]["children"][0]["children"][0]["children"][0]["children"]
        self.assertEqual([(c["id"], c["is_selected"]) for c in columns], [("tag", False), ("key", True)])
        self.assertEqual(receipt["deselectedSqlColumns"], [
            ["Schemas", "dbo", "Views", "agent_donation_detail", "DonationDataLayer"],
        ])
        for kind in SOURCES:
            original_source = decoded_parts(original)[f"Files/Config/published/{kind}/datasource.json"]
            current_source = after[f"Files/Config/draft/{kind}/datasource.json"]
            for key in ("artifactId", "workspaceId", "metadata", "userDescription"):
                self.assertEqual(current_source[key], original_source[key])

    def test_draft_context_cannot_leak_the_physical_tag_to_gold(self):
        result, receipt = isolation.compile_isolated_draft(self.fixture())
        after = decoded_parts(result)
        self.assertEqual(receipt["exampleCounts"], {"lakehouse_tables": 15, "kusto": 6})
        draft = {path: value for path, value in after.items() if "/draft/" in path}
        self.assertNotIn(isolation.PROVENANCE_LITERAL, json.dumps(draft))
        model = draft["Files/Config/draft/semantic_model/datasource.json"]["dataSourceInstructions"]
        self.assertIn(isolation.MODEL_STATIC, model)
        self.assertIn(isolation.MODEL_INCREMENT, model)
        sql = draft["Files/Config/draft/lakehouse_tables/fewshots.json"]["fewShots"]
        self.assertTrue(any(r["query"] == "SELECT DISTINCT DonationPaymentMethod FROM dbo.agent_donation_detail ORDER BY DonationPaymentMethod" for r in sql))
        self.assertFalse(any("DonationDataLayer" in r["query"] for r in sql))

    def test_filter_timezone_is_distinct_from_display_timezone(self):
        result, _ = isolation.compile_isolated_draft(self.fixture())
        rows = decoded_parts(result)["Files/Config/draft/kusto/fewshots.json"]["fewShots"]
        examples = [r["query"] for r in rows if "WindowEndUtc=WindowEndUtc" in r["query"]]
        utc = next(q for q in examples if "FilterTimezone='UTC'" in q)
        jst = next(q for q in examples if "FilterTimezone='Asia/Tokyo'" in q)
        self.assertNotIn("datetime_local_to_utc", utc)
        self.assertIn("datetime(2026-08-05T00:00:00Z)", utc)
        self.assertIn("datetime_local_to_utc", jst)
        for query in examples:
            self.assertIn("DisplayTimezone='UTC'", query)
            self.assertIn("EventMinute >= WindowStartUtc and EventMinute < WindowEndUtc", query)
            self.assertIn("sum(ObservationCount)", query)
            self.assertIn("min(FirstObservedAt)", query)
            self.assertIn("max(LastObservedAt)", query)

    def test_rejects_ambiguous_examples(self):
        docs = decoded_parts(self.fixture())
        rows = docs["Files/Config/published/kusto/fewshots.json"]["fewShots"]
        rows.append(copy.deepcopy(rows[0]))
        with self.assertRaisesRegex(ValueError, "example is missing or ambiguous"):
            isolation.compile_isolated_draft({"parts": [inline_part(p, v) for p, v in docs.items()]})

    def test_rejects_unexpected_selected_provenance_fields(self):
        docs = decoded_parts(self.fixture())
        views = docs["Files/Config/published/lakehouse_tables/datasource.json"]["elements"][0]["children"][0]["children"][0]["children"]
        views.append(copy.deepcopy(views[0]))
        views[-1]["display_name"] = "unrelated"
        with self.assertRaisesRegex(ValueError, "known static detail"):
            isolation.compile_isolated_draft({"parts": [inline_part(p, v) for p, v in docs.items()]})

    def test_deterministic_and_preserves_no_benchmark_answers(self):
        original = self.fixture()
        self.assertEqual(isolation.compile_isolated_draft(original), isolation.compile_isolated_draft(original))
        for path in isolation.PROFILE.iterdir():
            if path.suffix in {".txt", ".json"}:
                text = path.read_text(encoding="utf-8")
                for value in ("F30-O08", "F31-H11", "2026-08-11", "14995", "253886000"):
                    self.assertNotIn(value, text)


if __name__ == "__main__":
    unittest.main()
