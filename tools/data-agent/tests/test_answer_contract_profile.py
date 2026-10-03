import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import answer_contract_profile as profile
from source_grounded_profile import decoded_parts, inline_part


class ContractTests(unittest.TestCase):
    def fixture(self):
        docs = {
            "Files/Config/data_agent.json": {"$schema": "2.1.0"},
            "Files/Config/publish_info.json": {"description": "preserved"},
            "Files/Config/published/stage_config.json": {
                "aiInstructions": "before", "experimental": {"enableExperimentalFeatures": True},
            },
        }
        descriptions = json.loads((profile.PROFILE / "schema-descriptions.json").read_bytes())
        objects = {}
        for key in descriptions:
            table, column = key.split(".")
            objects.setdefault(table, []).append({
                "id": "native-" + key, "display_name": column, "type": "lakehouse_tables.column",
                "data_type": "varchar", "description": None, "is_selected": True,
            })
        views = [{"id": "native-" + table, "display_name": table, "type": "lakehouse_tables.view",
                  "is_selected": True, "description": "source description", "children": columns}
                 for table, columns in objects.items()]
        for kind in profile.SOURCES:
            docs[f"Files/Config/published/{kind}/datasource.json"] = {
                "type": kind, "artifactId": kind + "-item", "workspaceId": "workspace",
                "metadata": {"opaque": [1, "keep"]}, "dataSourceInstructions": "old", "userDescription": "old",
                "elements": [{"type": "schema_grouping", "children": [{
                    "type": "lakehouse_tables.schema", "display_name": "dbo", "children": [
                        {"type": "view_grouping", "children": views},
                    ],
                }]}] if kind == "lakehouse_tables" else [{"id": kind, "is_selected": True}],
            }
            if kind in {"lakehouse_tables", "kusto"}:
                docs[f"Files/Config/published/{kind}/fewshots.json"] = {"fewShots": [{"id": "old"}]}
        docs["Files/Config/published/lakehouse_tables/topic.json"] = {"opaque": "keep"}
        for path, value in list(docs.items()):
            if "/published/" in path:
                docs[path.replace("/published/", "/draft/")] = copy.deepcopy(value)
        return {"parts": [inline_part(path, value) for path, value in docs.items()]}

    def test_preserves_original_published_runtime_and_unrecognized_parts(self):
        original = self.fixture()
        saved = copy.deepcopy(original)
        result, receipt = profile.compile_contract_draft(original)
        self.assertEqual(original, saved)
        before, after = decoded_parts(original), decoded_parts(result)
        for path, value in before.items():
            if "/draft/" not in path:
                self.assertEqual(after[path], value)
        self.assertEqual(after["Files/Config/draft/lakehouse_tables/topic.json"], {"opaque": "keep"})
        self.assertEqual(after["Files/Config/draft/stage_config.json"]["experimental"],
                         before["Files/Config/published/stage_config.json"]["experimental"])
        self.assertEqual(receipt["cloudCalls"], 0)

    def test_preserves_all_selection_ids_and_types(self):
        original = self.fixture()
        result, _ = profile.compile_contract_draft(original)

        def without_descriptions(value):
            if isinstance(value, dict):
                return {k: without_descriptions(v) for k, v in value.items() if k != "description"}
            if isinstance(value, list):
                return [without_descriptions(v) for v in value]
            return value

        before, after = decoded_parts(original), decoded_parts(result)
        for kind in profile.SOURCES:
            source = before[f"Files/Config/published/{kind}/datasource.json"]
            actual = after[f"Files/Config/draft/{kind}/datasource.json"]
            for key in source.keys() - {"dataSourceInstructions", "userDescription", "elements"}:
                self.assertEqual(actual[key], source[key])
            self.assertEqual(without_descriptions(actual["elements"]), without_descriptions(source["elements"]))

    def test_every_column_description_is_applied_once(self):
        _, receipt = profile.compile_contract_draft(self.fixture())
        descriptions = json.loads((profile.PROFILE / "schema-descriptions.json").read_bytes())
        self.assertEqual(receipt["describedColumns"], sorted(descriptions))

    def test_missing_or_duplicate_native_column_fails_closed(self):
        for duplicate in (False, True):
            original = decoded_parts(self.fixture())
            nodes = original["Files/Config/published/lakehouse_tables/datasource.json"]["elements"][0]["children"][0]["children"][0]["children"]
            if duplicate:
                nodes.append(copy.deepcopy(nodes[0]))
            else:
                nodes.pop()
            value = {"parts": [inline_part(p, v) for p, v in original.items()]}
            with self.assertRaisesRegex(ValueError, "exactly once"):
                profile.compile_contract_draft(value)

    def test_unselected_contract_column_is_not_implicitly_selected(self):
        original = decoded_parts(self.fixture())
        nodes = original["Files/Config/published/lakehouse_tables/datasource.json"]["elements"][0]["children"][0]["children"][0]["children"]
        nodes[0]["children"][0]["is_selected"] = False
        with self.assertRaisesRegex(ValueError, "unselected"):
            profile.compile_contract_draft({"parts": [inline_part(p, v) for p, v in original.items()]})

    def test_deterministic_with_only_supported_example_types(self):
        self.assertEqual(profile.compile_contract_draft(self.fixture()), profile.compile_contract_draft(self.fixture()))
        _, receipt = profile.compile_contract_draft(self.fixture())
        self.assertEqual(receipt["exampleCounts"], {"lakehouse_tables": 15, "kusto": 5, "ontology": 0, "semantic_model": 0})

    def test_examples_teach_general_patterns_not_expected_answers(self):
        for row in profile.query_examples():
            for forbidden in ("F30-", "2000588", "4000341", "1344099000", "253886000", "7867000", "5015000"):
                self.assertNotIn(forbidden, row["question"] + row["query"])
        queries = [row["query"] for row in profile.query_examples()]
        exhaustive = next(q for q in queries if "SupplierOrdinal" in q)
        self.assertNotIn("TOP ", exhaustive)
        self.assertIn("CatalogSupplierCount", exhaustive)
        compare = next(q for q in queries if "UNION ALL" in q)
        self.assertNotIn("DonationDate", compare)
        self.assertNotIn("YEAR(", compare)
        self.assertIn("ResidentPrefectureId", compare)
        self.assertIn("RecipientPrefectureId", compare)
        self.assertNotIn("GROUP BY", compare)
        self.assertEqual(compare.count("COUNT_BIG(*)"), 2)
        fanout = next(q for q in queries if "OriginalDonationCount" in q)
        self.assertIn("ON s.GiftId=d.GiftId", fanout)
        self.assertIn("COUNT(DISTINCT SupplierId)", fanout)
        self.assertIn("GROUP BY DonationId,GiftId,GiftName", fanout)

    def test_ambiguous_or_unsupported_examples_are_rejected(self):
        for rows in ([{"sourceType": "ontology", "question": "x", "query": "x"}],
                     [{"sourceType": "kusto", "question": "x", "query": "x"}] * 2):
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory)
                (path / "examples.json").write_text(json.dumps({"examples": rows}), encoding="utf-8")
                with self.assertRaises(ValueError):
                    profile.query_examples(path)

    def grounding_fixture(self):
        docs = decoded_parts(self.fixture())
        published = "Files/Config/published/lakehouse_tables/datasource.json"
        schema = docs[published]["elements"][0]["children"][0]
        schema["children"].append({
            "type": "table_grouping", "is_selected": True, "children": [{
                "type": "lakehouse_tables.table", "display_name": "ot_pref_category_metric",
                "id": "metric-base", "is_selected": True,
                "children": [{"id": "metric-base-key", "is_selected": True}],
            }],
        })
        draft = published.replace("/published/", "/draft/")
        docs[draft] = copy.deepcopy(docs[published])
        views = docs[draft]["elements"][0]["children"][0]["children"][0]["children"]
        columns = []
        for name in profile.SCHEMA_VIEWS:
            names = ("RelationshipName", "DeclaredFromEntity", "DeclaredToEntity") if name.endswith("dictionary") else (
                "PrefCategoryMetricId", "PrefectureName", "CategoryName",
            )
            columns.extend({"TABLE_NAME": name, "COLUMN_NAME": column, "DATA_TYPE": "varchar"} for column in names)
            views.append({
                "type": "lakehouse_tables.view", "display_name": name, "id": "native-" + name,
                "is_selected": True, "description": None, "children": [{
                    "type": "lakehouse_tables.column", "display_name": column,
                    "id": "native-" + name + "-" + column, "data_type": "varchar",
                    "is_selected": True, "description": None,
                } for column in names],
            })
        return {"parts": [inline_part(p, v) for p, v in docs.items()]}, columns

    def test_schema_views_use_native_ids_without_changing_published(self):
        original, columns = self.grounding_fixture()
        saved = copy.deepcopy(original)
        compiled, receipt = profile.compile_schema_grounded_draft(original, columns)
        self.assertEqual(original, saved)
        before, after = decoded_parts(original), decoded_parts(compiled)
        for path, value in before.items():
            if "/published/" in path:
                self.assertEqual(after[path], value)
        schema = after["Files/Config/draft/lakehouse_tables/datasource.json"]["elements"][0]["children"][0]
        views = schema["children"][0]["children"]
        added = [v for v in views if v["display_name"] in profile.SCHEMA_VIEWS]
        self.assertEqual({v["id"] for v in added}, {"native-" + n for n in profile.SCHEMA_VIEWS})
        self.assertEqual(len(added), 2)
        base = schema["children"][1]["children"][0]
        self.assertFalse(base["is_selected"])
        self.assertFalse(base["children"][0]["is_selected"])
        self.assertFalse(receipt["sourceIdentitiesAndSelectionsPreserved"])
        self.assertTrue(receipt["sourceIdentitiesPreserved"])
        self.assertEqual(receipt["retiredTableSelections"], ["ot_pref_category_metric"])
        self.assertEqual(profile.compile_schema_grounded_draft(compiled, columns), (compiled, receipt))

    def test_schema_views_reject_wrong_sql_types_and_missing_native_nodes(self):
        original, columns = self.grounding_fixture()
        columns[0]["DATA_TYPE"] = "bigint"
        with self.assertRaisesRegex(ValueError, "SQL metadata"):
            profile.compile_schema_grounded_draft(original, columns)
        original, columns = self.grounding_fixture()
        docs = decoded_parts(original)
        views = docs["Files/Config/draft/lakehouse_tables/datasource.json"]["elements"][0]["children"][0]["children"][0]["children"]
        views.pop()
        with self.assertRaisesRegex(ValueError, "identities"):
            profile.compile_schema_grounded_draft({"parts": [inline_part(p, v) for p, v in docs.items()]}, columns)

    def test_schema_view_definitions_carry_metadata_not_case_answers(self):
        views = profile.PROFILE / "views"
        dictionary = (views / "agent_relationship_dictionary.sql").read_text(encoding="utf-8")
        metric = (views / "agent_prefecture_category_metric.sql").read_text(encoding="utf-8")
        self.assertEqual(dictionary.count("UNION ALL"), 14)
        self.assertIn("'PrefMetricForCategory','PrefectureCategoryMetric','GiftCategory'", dictionary)
        self.assertIn("m.PrefCategoryMetricId", metric)
        self.assertIn("m.PrefCategoryStaticCount AS DonationCount", metric)
        self.assertNotIn("45-01", metric)
        self.assertNotIn("32985000", metric)

    def test_source_value_domains_and_strict_flag_are_preserved(self):
        descriptions = json.loads((profile.PROFILE / "schema-descriptions.json").read_bytes())
        self.assertIn("StaticSyntheticSnapshot", descriptions["agent_donation_detail.DonationDataLayer"])
        self.assertIn("電子決済", descriptions["agent_donation_detail.DonationPaymentMethod"])
        text = (profile.PROFILE / "global-instructions.txt").read_text(encoding="utf-8")
        self.assertIn("DonationAmountYen > 57000", text)
        self.assertNotIn("1157", text)
        rows = profile.query_examples()
        payment = next(row["query"] for row in rows if "DonationPaymentMethod='銀行振込'" in row["query"])
        self.assertNotIn("DonationDataLayer=", payment)
        self.assertNotIn("DonationDate", payment)
        self.assertTrue(any("SELECT DISTINCT DonationDataLayer,DonationPaymentMethod" in row["query"] for row in rows))


if __name__ == "__main__":
    unittest.main()
