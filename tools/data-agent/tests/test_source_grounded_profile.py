import copy
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("source_grounded_profile", ROOT / "source_grounded_profile.py")
profile = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(profile)


class ProfileTests(unittest.TestCase):
    def fixture(self):
        documents = {
            "Files/Config/data_agent.json": {"$schema": "2.1.0"},
            "Files/Config/published/stage_config.json": {
                "$schema": "1.0.0", "aiInstructions": "before",
                "experimental": {"codeInterpreterEnabled": True, "enableExperimentalFeatures": True},
            },
        }
        for index, kind in enumerate(profile.INSTRUCTIONS):
            documents[f"Files/Config/published/{kind}-source/datasource.json"] = {
                "$schema": "1.0.0", "type": kind, "artifactId": f"item-{index}", "workspaceId": "workspace",
                "displayName": f"source-{index}", "dataSourceInstructions": None, "userDescription": "before",
                "metadata": {"opaque": {"preserve": [1, 2]}},
                "elements": [{"id": f"element-{index}", "is_selected": True, "description": "selection",
                              "children": [{"id": "column", "is_selected": False}]}],
            }
        return {"definition": {"parts": [profile.inline_part(path, value) for path, value in documents.items()]}}

    def test_preserves_all_source_identity_metadata_and_selection(self):
        original = self.fixture()
        saved = copy.deepcopy(original)
        result, receipt = profile.compile_draft(original)
        self.assertEqual(original, saved)
        actual, before = profile.decoded_parts(result), profile.decoded_parts(original)
        for path, value in before.items():
            if path.endswith("datasource.json"):
                compiled = actual[path.replace("/published/", "/draft/")]
                for key in value.keys() - {"dataSourceInstructions", "userDescription"}:
                    self.assertEqual(compiled[key], value[key])
        self.assertEqual(receipt["cloudCalls"], 0)
        self.assertFalse(receipt["publishedByCompiler"])
        self.assertFalse(any("/published/" in path for path in actual))

    def test_stage_switches_are_not_changed(self):
        original = self.fixture()
        result, _ = profile.compile_draft(original)
        actual, before = profile.decoded_parts(result), profile.decoded_parts(original)
        self.assertEqual(actual["Files/Config/draft/stage_config.json"]["experimental"],
                         before["Files/Config/published/stage_config.json"]["experimental"])

    def test_examples_only_for_supported_sources(self):
        result, _ = profile.compile_draft(self.fixture())
        docs = profile.decoded_parts(result)
        bundles = {path: value for path, value in docs.items() if path.endswith("fewshots.json")}
        self.assertEqual(len(bundles), 2)
        self.assertEqual(sorted(len(value["fewShots"]) for value in bundles.values()), [4, 8])
        self.assertTrue(all("lakehouse_tables" in p or "kusto" in p for p in bundles))
        self.assertEqual(len({row["id"] for bundle in bundles.values() for row in bundle["fewShots"]}), 12)

    def test_compile_is_deterministic(self):
        self.assertEqual(profile.compile_draft(self.fixture()), profile.compile_draft(self.fixture()))

    def test_rejects_missing_source(self):
        fixture = self.fixture()
        fixture["definition"]["parts"].pop()
        with self.assertRaisesRegex(ValueError, "four"):
            profile.compile_draft(fixture)

    def test_rejects_duplicate_path(self):
        fixture = self.fixture()
        fixture["definition"]["parts"].append(fixture["definition"]["parts"][0])
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            profile.compile_draft(fixture)

    def test_never_silently_discards_existing_examples_or_topics(self):
        fixture = self.fixture()
        fixture["definition"]["parts"].append(profile.inline_part(
            "Files/Config/published/lakehouse_tables-source/fewshots.json",
            {"fewShots": [{"id": "prior", "question": "existing", "query": "SELECT 1"}]},
        ))
        with self.assertRaisesRegex(ValueError, "reconciliation"):
            profile.compile_draft(fixture)

    def test_old_conflicting_rules_are_not_appended(self):
        text = (profile.PROFILE / "lakehouse-instructions.txt").read_text(encoding="utf-8")
        self.assertIn("These SQL registry/count questions ARE supported", text)
        self.assertIn("SECOND query", text)
        self.assertIn("Do not join ot_supplier_gift into a donation SUM or COUNT", text)
        self.assertNotIn("Do not answer them by counting", text)

    def test_raw_calendar_and_hourly_examples_use_the_requested_grain(self):
        rows = profile.examples()
        hourly = next(row["query"] for row in rows if "by UtcHour=" in row["query"])
        daily = next(row["query"] for row in rows if "range UtcDay" in row["query"])
        self.assertNotIn("by UtcHour=bin(EventMinute,1h),", hourly)
        self.assertIn("sum(ObservationCount)", hourly)
        self.assertIn("sum(ObservedAmountYen)", hourly)
        self.assertIn("join kind=leftouter Daily on UtcDay", daily)
        self.assertNotIn("take 1", daily)

    def test_examples_contain_queries_not_benchmark_answers(self):
        for row in profile.examples():
            self.assertNotIn("F30-", row["question"] + row["query"])
            self.assertNotIn("1344099000", row["query"])
            self.assertNotIn("1596157000", row["query"])
            self.assertNotIn("253886000", row["query"])

    def test_view_backed_requires_all_four_verified_schemas(self):
        with self.assertRaisesRegex(ValueError, "exactly four"):
            profile.compile_view_backed_draft(self.fixture(), [])

    def test_view_backed_change_preserves_published_and_other_sources(self):
        docs = profile.decoded_parts(self.fixture())
        for path, value in list(docs.items()):
            if "/published/" in path:
                docs[path.replace("/published/", "/draft/")] = copy.deepcopy(value)
        static_path = "Files/Config/draft/lakehouse_tables-source/datasource.json"
        tables = [{
            "display_name": name, "id": name, "type": "lakehouse_tables.table",
            "is_selected": True, "children": [{"id": "column-" + name, "is_selected": True}],
        } for name in ("ot_municipality", "ot_donation", "ot_supplier", "ot_supplier_gift", "ot_prefecture")]
        views = [{
            "display_name": name, "id": "native-" + name, "type": "lakehouse_tables.view",
            "is_selected": False, "children": [{
                "id": "native-column-" + name, "display_name": "StableId", "data_type": "varchar",
                "type": "lakehouse_tables.column", "description": None, "is_selected": False,
            }],
        } for name in profile.VIEW_DESCRIPTIONS]
        docs[static_path]["elements"] = [{
            "display_name": "dbo", "id": "schema", "type": "lakehouse_tables.schema",
            "is_selected": True, "children": [
                {"display_name": "Tables", "type": "table_grouping", "children": tables},
                {"display_name": "Views", "type": "view_grouping", "children": views},
            ],
        }]
        original = {"parts": [profile.inline_part(path, value) for path, value in docs.items()]}
        columns = [{"TABLE_NAME": name, "COLUMN_NAME": "StableId", "DATA_TYPE": "varchar"}
                   for name in profile.VIEW_DESCRIPTIONS]
        result, receipt = profile.compile_view_backed_draft(original, columns)
        after = profile.decoded_parts(result)
        for path, value in docs.items():
            if path.startswith("Files/Config/published/") or ("datasource.json" in path and path != static_path):
                self.assertEqual(after[path], value)
        self.assertEqual(after[static_path]["artifactId"], docs[static_path]["artifactId"])
        groups = after[static_path]["elements"][0]["children"]
        selected = {t["display_name"] for group in groups for t in group["children"] if t["is_selected"]}
        self.assertEqual(selected, {"ot_prefecture", *profile.VIEW_DESCRIPTIONS})
        self.assertEqual([v["id"] for v in groups[1]["children"]], [v["id"] for v in views])
        self.assertTrue(all(not c["is_selected"] for t in groups[0]["children"][:4] for c in t["children"]))
        self.assertEqual(len(groups), 2)
        self.assertEqual(receipt["cloudCalls"], 0)

    def test_view_sql_preserves_fact_and_catalog_grains(self):
        view_dir = profile.PROFILE / "views"
        detail = (view_dir / "agent_donation_detail.sql").read_text(encoding="utf-8")
        catalog = (view_dir / "agent_donor_catalog_supplier.sql").read_text(encoding="utf-8")
        self.assertNotIn("ot_supplier_gift", detail)
        self.assertIn("SELECT DISTINCT", catalog)
        self.assertIn("COUNT_BIG(*) OVER (PARTITION BY pairs.DonorId)", catalog)
        snapshot = (view_dir / "agent_municipality_snapshot.sql").read_text(encoding="utf-8")
        self.assertNotIn("DonationDate", snapshot)
        self.assertNotIn("WHERE", snapshot)


if __name__ == "__main__":
    unittest.main()
