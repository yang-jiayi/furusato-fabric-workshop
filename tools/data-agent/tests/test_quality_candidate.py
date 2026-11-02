"""Offline candidate construction tests, not live query/answer acceptance."""
import copy
import base64
from pathlib import Path
import unittest

import current_profile
import quality_candidate as candidate
from measured_contract_profile import stage_sources
from source_grounded_profile import decoded_parts, inline_part
from test_current_profile import fixture


def baseline():
    actual = fixture()
    _, stage, _ = current_profile.load_profile()
    return {"parts": [inline_part(p["path"], stage) if p["path"].endswith("/stage_config.json")
                      else p for p in actual["parts"]]}

def model_fixture():
    root = Path(__file__).resolve().parents[3] / "workshop/v3.0.0-preview/powerbi/Furusato_Analytics.SemanticModel"
    return {"parts": [{"path": p.relative_to(root).as_posix(), "payloadType": "InlineBase64",
                       "payload": base64.b64encode(p.read_bytes()).decode()}
                      for p in sorted((root / "definition/tables").glob("*.tmdl"))]}


class QualityCandidateTests(unittest.TestCase):
    def setUp(self):
        self.before = baseline()
        self.model = model_fixture()
        self.after, self.receipt = candidate.compile_candidate(self.before, self.model)

    def test_published_shared_and_ontology_payloads_preserved(self):
        original = {p["path"]: p for p in self.before["parts"]}
        actual = {p["path"]: p for p in self.after["parts"]}
        for path, part in original.items():
            if not path.startswith("Files/Config/draft/"):
                self.assertEqual(part, actual[path])
        _, before_sources, _ = stage_sources(self.before, "published")
        _, after_sources, _ = stage_sources(self.after, "draft")
        for kind, (path, source) in before_sources.items():
            _, updated = after_sources[kind]
            for key, value in source.items():
                if key != "dataSourceInstructions":
                    self.assertEqual(value, updated[key], (kind, key))
            if kind == "ontology":
                self.assertEqual(original[path]["payload"], actual[path.replace("/published/", "/draft/")]["payload"])

    def test_targeted_fidelity_contracts_and_limits(self):
        docs, sources, _ = stage_sources(self.after, "draft")
        text = docs["Files/Config/draft/stage_config.json"]["aiInstructions"]
        self.assertIn("24-hour UTC", text)
        self.assertIn("stored unfiltered ranks cannot answer a filtered ranking", text)
        self.assertLessEqual(len(text.encode("utf-16-le")) // 2, 10000)
        kql = sources["kusto"][1]["dataSourceInstructions"]
        self.assertIn("TOTAL row separately", kql)
        self.assertIn("same predicates", kql)
        self.assertIn("WorkshopRunId, SourceFile, ParticipantAlias", kql)
        self.assertNotIn(candidate.RUN_ANCHOR, kql)
        self.assertIn(candidate.RUN_REPLACEMENT, kql)
        sql = sources["lakehouse_tables"][1]["dataSourceInstructions"]
        self.assertIn("before GROUP BY", sql)
        self.assertIn("SAME dimension row", sql)
        model = sources["semantic_model"][1]["dataSourceInstructions"]
        self.assertIn("KEEPFILTERS intersects", model)
        self.assertIn("whether equality is excluded", model)
        self.assertIn('CALCULATE([寄附件数], KEEPFILTERS(\'寄附\'[データソース] = "RealtimeIncrement"))', model)
        self.assertIn("57,000 円を超える", model)
        self.assertEqual(len(self.receipt["modelMetadataPartSha256"]), 1)
        self.assertFalse(self.receipt["answerAccuracyAccepted"])
        self.assertEqual(self.receipt["cloudCalls"], 0)

    def test_reject_unknown_examples_duplicate_paths_and_changed_baseline(self):
        for part in (
            inline_part("Files/Config/published/unreviewed/fewshots.json", {}),
            inline_part("Files/Config/draft/unreviewed/fewshots.json", {}),
            copy.deepcopy(self.before["parts"][0]),
        ):
            modified = copy.deepcopy(self.before)
            modified["parts"].append(part)
            with self.assertRaises(ValueError):
                candidate.compile_candidate(modified, self.model)
        modified = copy.deepcopy(self.before)
        path = "Files/Config/published/stage_config.json"
        modified["parts"] = [inline_part(path, {"aiInstructions": "unexpected profile"})
                             if p["path"] == path else p for p in modified["parts"]]
        with self.assertRaisesRegex(ValueError, "anchor changed"):
            candidate.compile_candidate(modified, self.model)

    def test_metadata_comes_from_supplied_model_not_hardcoded_answers(self):
        changed = copy.deepcopy(self.model)
        for part in changed["parts"]:
            raw = base64.b64decode(part["payload"])
            part["payload"] = base64.b64encode(raw.replace(b"57,000", b"61,234")).decode()
        output, receipt = candidate.compile_candidate(self.before, changed)
        _, sources, _ = stage_sources(output, "draft")
        instructions = sources["semantic_model"][1]["dataSourceInstructions"]
        self.assertIn("61,234", instructions)
        self.assertNotIn("57,000", instructions)
        self.assertNotEqual(receipt["modelMetadataPartSha256"], self.receipt["modelMetadataPartSha256"])
        with self.assertRaisesRegex(ValueError, "ten workshop measures"):
            candidate.compile_candidate(self.before, {"parts": []})
        duplicate = copy.deepcopy(self.model)
        duplicate["parts"].append(copy.deepcopy(duplicate["parts"][0]))
        with self.assertRaisesRegex(ValueError, "Duplicate model"):
            candidate.compile_candidate(self.before, duplicate)

    def test_input_is_not_mutated_and_compilation_is_deterministic(self):
        saved = copy.deepcopy(self.before)
        saved_model = copy.deepcopy(self.model)
        second, receipt = candidate.compile_candidate(self.before, self.model)
        self.assertEqual(saved, self.before)
        self.assertEqual(second, self.after)
        self.assertEqual(receipt, self.receipt)
        self.assertEqual(saved_model, self.model)
        docs = decoded_parts(second)
        self.assertEqual({p for p in docs if "/draft/" in p},
                         {p.replace("/published/", "/draft/", 1) for p in docs if "/published/" in p})


if __name__ == "__main__":
    unittest.main()
