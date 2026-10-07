import copy
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import standard_contract_restoration as restoration
from answer_contract_profile import SCHEMA_VIEWS, compile_schema_grounded_draft
from fresh_grounded_profile import compiler_snapshot
from source_grounded_profile import VIEW_DESCRIPTIONS, compile_draft, compile_view_backed_draft, decoded_parts, inline_part
from test_fresh_grounded_profile import FreshProfileTests
from time_layer_isolation import compile_isolated_draft


def isolated_fixture():
    definition, columns = FreshProfileTests().fixture()
    source, _ = compile_draft(compiler_snapshot(definition))
    views, _ = compile_view_backed_draft(source, [r for r in columns if r["TABLE_NAME"] in VIEW_DESCRIPTIONS])
    contract, _ = compile_schema_grounded_draft(
        compiler_snapshot(views), [r for r in columns if r["TABLE_NAME"] in SCHEMA_VIEWS])
    isolated, _ = compile_isolated_draft(compiler_snapshot(contract))
    return isolated


def selections(nodes):
    result = {}
    stack = list(nodes)
    while stack:
        node = stack.pop()
        if "id" in node:
            result[(node["id"], node.get("display_name"))] = node.get("is_selected")
        stack.extend(node.get("children", []))
    return result


class StandardContractRestorationTests(unittest.TestCase):
    def setUp(self):
        self.original = isolated_fixture()
        self.result, self.receipt = restoration.compile_restored_draft(self.original)
        self.before, self.after = decoded_parts(self.original), decoded_parts(self.result)

    def source(self, documents, kind):
        return next(v for p, v in documents.items() if p.startswith("Files/Config/draft/")
                    and p.endswith("/datasource.json") and v["type"] == kind)

    def test_global_contract_is_first_and_within_documented_limit(self):
        text = self.after["Files/Config/draft/stage_config.json"]["aiInstructions"]
        self.assertTrue(text.startswith(restoration.CONTRACT_MARKER))
        self.assertLessEqual(len(text), restoration.GLOBAL_LIMIT)
        self.assertEqual(self.receipt["globalInstructionsCharacters"], len(text))
        for phrase in ("[2026-08-01T00:00:00Z, 2026-09-01T00:00:00Z)", "「2025」は静的seedの年ラベル",
                       "受入（その都道府県の自治体が受け取った寄付）", "件数と金額の両方で求め",
                       "1寄付=1行", "All timestamps are UTC.",
                       "Relationship: Municipality -MunicipalityInPrefecture-> Prefecture",
                       "Traversal: Prefecture <-MunicipalityInPrefecture- Municipality (reverse)",
                       "SupplierProvidesGiftはカタログ登録", "EventIDがない", "ご提示の合計は、このワークショップの総寄付件数ではありません。",
                       "Source: Ontology | Method: relationship COUNT aggregation",
                       "Lakehouseに県列があっても所属県はOntology", "\n【所属県（Ontology）】", "\n突き合わせキー: MunicipalityId\n",
                       "\nTraversal: Municipality -MunicipalityInPrefecture-> Prefecture (forward)\n",
                       "\nRecipient schema: Donation -DonationToMunicipality-> Municipality\n",
                       "「約」や万・億への換算で言い換えない", "倍率と増減率を同じ数で書かない",
                       "\n倍率 = A÷B = <倍率>倍\n", "この3行の後に、倍率や増減率を言い換えた要約文を書かない",
                       "KEEPFILTERSのない通常のCALCULATE", "CatalogGiftCountは業者のカタログ全体"):
            self.assertIn(phrase, text)
        self.assertIn("## 最優先: 対象日のtimezoneと表示のtimezoneを分離", text)

    def test_conflicting_registry_and_file_clauses_are_replaced(self):
        text = self.after["Files/Config/draft/stage_config.json"]["aiInstructions"]
        for old, new in restoration.GLOBAL_REPLACEMENTS:
            self.assertNotIn(old, text)
            self.assertEqual(text.count(new), 1)

    def test_published_parts_identities_and_selections_are_preserved(self):
        for path, value in self.before.items():
            if not path.startswith("Files/Config/draft/"):
                self.assertEqual(self.after[path], value)
        for kind in restoration.TYPES:
            old, new = self.source(self.before, kind), self.source(self.after, kind)
            for key in ("artifactId", "workspaceId", "displayName", "type", "metadata"):
                self.assertEqual(new.get(key), old.get(key))
            self.assertEqual(selections(new.get("elements", [])), selections(old.get("elements", [])))
            self.assertTrue(new["dataSourceInstructions"].endswith(old["dataSourceInstructions"]))
        self.assertEqual(self.after["Files/Config/draft/stage_config.json"]["experimental"],
                         self.before["Files/Config/draft/stage_config.json"]["experimental"])
        self.assertEqual(self.receipt["cloudCalls"], 0)

    def test_examples_add_patterns_and_group_file_runs(self):
        self.assertEqual(self.receipt["exampleCounts"], {"lakehouse_tables": 17, "kusto": 9})
        kusto = self.after["Files/Config/draft/kusto/fewshots.json"]["fewShots"]
        file_rows = [r for r in kusto if r["question"].startswith("2026年8月のCSVごとに")]
        self.assertEqual(len(file_rows), 1)
        self.assertIn("by SourceFile, WorkshopRunId, ParticipantAlias", file_rows[0]["query"])
        month = next(r for r in kusto if r["question"].startswith("年の指定がない「8月」"))
        self.assertIn("datetime(2026-08-01T00:00:00Z)", month["query"])
        self.assertNotIn("2025", month["query"])
        for row in kusto:
            self.assertNotRegex(row["query"], r"top \d+ by [^|;]+,")
        sql = self.after["Files/Config/draft/lakehouse_tables/fewshots.json"]["fewShots"]
        both = next(r for r in sql if "受入と在住" in r["question"])
        for column in ("PrefReceivedStaticCount", "PrefReceivedTotalYen", "PrefResidentStaticCount", "PrefResidentTotalYen"):
            self.assertIn(column, both["query"])
        ids = [r["id"] for r in kusto + sql]
        self.assertEqual(len(ids), len(set(ids)))

    def test_source_contracts_descriptions_and_column_semantics(self):
        kusto = self.source(self.after, "kusto")
        self.assertTrue(kusto["dataSourceInstructions"].startswith("## Standard workshop scope (highest priority)"))
        self.assertIn("August 2026", kusto["userDescription"])
        self.assertIn("in ONE summarize BY MunicipalityID", kusto["dataSourceInstructions"])
        self.assertIn("Never take a metric from arg_max", kusto["dataSourceInstructions"])
        ontology = self.source(self.after, "ontology")
        self.assertIn("count(m) AS MunicipalityCount", ontology["dataSourceInstructions"])
        self.assertIn("never translate a Japanese name to English", ontology["dataSourceInstructions"])
        self.assertIn("WHERE m.MunicipalityId = '<MunicipalityId>'", ontology["dataSourceInstructions"])
        self.assertIn("membership COUNT", ontology["userDescription"])
        self.assertIn("forward MunicipalityInPrefecture traversal", ontology["userDescription"])
        model = self.source(self.after, "semantic_model")["dataSourceInstructions"]
        self.assertIn("WITHOUT KEEPFILTERS would replace the outer filter", model)
        sql = self.source(self.after, "lakehouse_tables")
        self.assertIn("PrefResidentStaticCount", sql["dataSourceInstructions"])
        text = json.dumps(sql["elements"], ensure_ascii=False)
        self.assertIn("It is NOT the number of registrations of one particular gift", text)
        self.assertEqual(self.receipt["describedColumns"], ["agent_supplier_catalog.CatalogGiftCount"])

    def test_refuses_double_application_and_missing_context(self):
        with self.assertRaisesRegex(ValueError, "already present"):
            restoration.compile_restored_draft(self.result)
        docs = copy.deepcopy(self.before)
        stage = docs["Files/Config/draft/stage_config.json"]
        stage["aiInstructions"] = stage["aiInstructions"].replace(restoration.GLOBAL_REPLACEMENTS[0][0], "")
        with self.assertRaisesRegex(ValueError, "missing or ambiguous"):
            restoration.compile_restored_draft({"parts": [inline_part(p, v) for p, v in docs.items()]})

    def test_refuses_unselected_described_column(self):
        docs = copy.deepcopy(self.before)
        sql = self.source(docs, "lakehouse_tables")
        stack = list(sql["elements"])
        while stack:
            node = stack.pop()
            if node.get("display_name") == "CatalogGiftCount":
                node["is_selected"] = False
            stack.extend(node.get("children", []))
        with self.assertRaisesRegex(ValueError, "exist once and be selected"):
            restoration.compile_restored_draft({"parts": [inline_part(p, v) for p, v in docs.items()]})

    def test_overlay_contains_no_benchmark_answer_values(self):
        restoration.overlay_inputs()
        with tempfile.TemporaryDirectory() as directory:
            copy_dir = Path(directory) / "profile"
            shutil.copytree(restoration.PROFILE, copy_dir)
            path = copy_dir / "global-contract.txt"
            path.write_text(path.read_text(encoding="utf-8") + "\n都城市は1,813件。\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "benchmark answer values"):
                restoration.overlay_inputs(copy_dir)

    def test_deterministic(self):
        self.assertEqual(restoration.compile_restored_draft(self.original), (self.result, self.receipt))


if __name__ == "__main__":
    unittest.main()
