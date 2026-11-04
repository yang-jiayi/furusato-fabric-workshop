"""Offline Prep for AI contracts; these checks do not activate native settings."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import re
import unittest

import preview30_runtime as rt

POWERBI = rt.PREVIEW / "powerbi"
MODEL = POWERBI / "Furusato_Analytics.SemanticModel/definition"
PREP = POWERBI / "prep-for-ai"


def objects():
    result = {}
    for path in (MODEL / "tables").glob("*.tmdl"):
        text = path.read_text(encoding="utf-8")
        columns = {}
        measures = {}
        for match in re.finditer(r"^\t(column|measure) ([^\n]+?)(?: = ([^\n]*))?\n(.*?)(?=^\t(?:column|measure|partition|///)|\Z)",
                                 text, re.MULTILINE | re.DOTALL):
            kind, name, dax, properties = match.groups()
            name = name.strip("'")
            if kind == "column":
                columns[name] = properties
            else:
                measures[name] = dax
        result[path.stem] = {"columns": columns, "measures": measures}
    return result


def validate_selection(contract, model):
    selected = contract["tables"]
    if set(selected) != set(model) or set(contract["agentSelectedTables"]) != set(selected):
        raise ValueError("Prep and Agent table selections must match the model")
    all_measures = {name for table in selected.values() for name in table["measures"]}
    for table, chosen in selected.items():
        columns = chosen["columns"] + chosen["dependencyColumns"]
        if len(columns) != len(set(columns)) or not set(columns) <= model[table]["columns"].keys():
            raise ValueError("Unknown or duplicate column")
        if set(chosen["measures"]) != model[table]["measures"].keys():
            raise ValueError("Missing or unknown business measure")
        for name in columns:
            sort = re.search(r"sortByColumn: (.+)", model[table]["columns"][name])
            if sort and sort[1].strip("'") not in columns:
                raise ValueError("Missing sort dependency")
        for dax in model[table]["measures"].values():
            for owner, column in re.findall(r"'([^']+)'\[([^\]]+)\]", dax):
                if column not in selected[owner]["columns"] + selected[owner]["dependencyColumns"]:
                    raise ValueError("Missing DAX column dependency")
            expression = re.sub(r"'[^']+'\[[^\]]+\]", "", dax)
            if not set(re.findall(r"\[([^\]]+)\]", expression)) <= all_measures:
                raise ValueError("Missing DAX measure dependency")
    relationships = (MODEL / "relationships.tmdl").read_text(encoding="utf-8")
    for owner, column in re.findall(r"(?:from|to)Column: ([^.]+)\.(.+)", relationships):
        if column not in selected[owner]["columns"] + selected[owner]["dependencyColumns"]:
            raise ValueError("Missing relationship dependency")


class SemanticAIContractTests(unittest.TestCase):
    def setUp(self):
        self.contract = json.loads((PREP / "schema.json").read_bytes())
        self.model = objects()

    def test_selected_objects_and_transitive_dax_relationship_sort_dependencies(self):
        validate_selection(self.contract, self.model)
        self.assertEqual(sum(len(t["measures"]) for t in self.model.values()), 10)
        self.assertEqual(len(self.model), 5)

    def test_missing_dependencies_and_unknown_objects_are_rejected(self):
        cases = [
            ("寄附", "dependencyColumns", "高額寄附フラグ"),
            ("日付", "dependencyColumns", "月番号"),
            ("寄附者", "dependencyColumns", "寄附者ID"),
            ("寄附", "measures", "寄附総額"),
        ]
        for table, kind, name in cases:
            contract = copy.deepcopy(self.contract)
            contract["tables"][table][kind].remove(name)
            with self.subTest(name=name), self.assertRaises(ValueError):
                validate_selection(contract, self.model)
        self.contract["tables"]["寄附"]["columns"].append("Unknown")
        with self.assertRaises(ValueError):
            validate_selection(self.contract, self.model)

    def test_all_numeric_attributes_use_explicit_summarization_none(self):
        for table in self.model.values():
            for name, properties in table["columns"].items():
                if "dataType: int64" in properties:
                    with self.subTest(column=name):
                        self.assertIn("summarizeBy: none", properties)
        self.assertIn("discourageImplicitMeasures", (MODEL / "model.tmdl").read_text("utf-8"))

    def test_business_dax_and_relationships_preserve_the_inherited_contract(self):
        base = rt.BASE / "powerbi/Furusato_Analytics.SemanticModel/definition"
        for path in (MODEL / "tables").glob("*.tmdl"):
            inherited = (base / "tables" / path.name).read_text("utf-8")
            measures = lambda text: re.findall(r"^\tmeasure (.+) = (.+)$", text, re.MULTILINE)
            actual = dict(measures(path.read_text("utf-8")))
            for name, expression in measures(inherited):
                self.assertEqual(actual[name], expression)
        self.assertEqual((MODEL / "relationships.tmdl").read_bytes(),
                         (base / "relationships.tmdl").read_bytes())
        metrics = json.loads((POWERBI / "native-metrics-contract.json").read_bytes())
        for item in metrics["measures"]:
            self.assertEqual(self.model[item["table"]]["measures"][item["name"]], item["dax"])

    def test_instructions_are_bounded_population_aware_and_not_answer_keys(self):
        text = (PREP / self.contract["instructionsFile"]).read_text("utf-8")
        self.assertLessEqual(len(text), 10000)
        self.assertLessEqual(len(text.encode("utf-16-le")) // 2, 10000)
        for term in ("KEEPFILTERS", "BLANK", "JPY", "StaticSeed", "RealtimeIncrement",
                     "Japan Standard Time", "居住都道府県", "寄附先都道府県",
                     "前年同期間", "not fiscal", "not an alert"):
            self.assertIn(term, text)
        for answer in ("94900", "1596157000", "80000", "1344099000", "14900",
                       "252058000", "15000", "253886000"):
            self.assertNotIn(answer, re.sub(r"[,\s]", "", text))
        agent = (PREP / self.contract["agentGuidanceFile"]).read_text("utf-8")
        for calculation in ("CALCULATE(", "KEEPFILTERS(", "SUM(", "57000"):
            self.assertNotIn(calculation, agent)
        self.assertFalse(self.contract["nativeConfigurationIncludedInDefinition"])
        self.assertFalse(self.contract["schemaIsAuthorizationBoundary"])

    def test_verified_answer_candidate_uses_actual_visible_visual_fields(self):
        candidate = self.contract["verifiedAnswers"]
        self.assertEqual(candidate["status"], "optional-not-configured")
        self.assertTrue(5 <= len(candidate["triggerQuestions"]) <= 7)
        self.assertLessEqual(candidate["maximumFlexibleFilters"], 3)
        visual = json.loads((POWERBI / "Furusato_Analytics.Report" / candidate["candidateVisual"]).read_bytes())
        projected = visual["visual"]["query"]["queryState"]
        fields = [p["field"] for state in projected.values() for p in state["projections"]]
        self.assertEqual(len(fields), 3)
        for field in fields:
            kind, value = next(iter(field.items()))
            table = value["Expression"]["SourceRef"]["Entity"]
            name = value["Property"]
            if kind == "Column":
                self.assertNotIn("isHidden", self.model[table]["columns"][name])
            else:
                self.assertIn(name, self.model[table]["measures"])


if __name__ == "__main__":
    unittest.main()
