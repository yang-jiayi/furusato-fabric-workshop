"""Offline field/metadata guards, not live inference or answer grading."""
import base64
import copy
import hashlib
from pathlib import Path
import unittest

import current_profile
import decomposition_candidate as candidate
import quality_candidate
from evaluate_native import definition_digest
from measured_contract_profile import stage_sources
from source_grounded_profile import inline_part
from test_current_profile import fixture


def fixtures():
    root = Path(__file__).resolve().parents[3] / "workshop/v3.0.0-preview/powerbi/Furusato_Analytics.SemanticModel"
    model = {"parts": [
        {"path": path.relative_to(root).as_posix(), "payloadType": "InlineBase64",
         "payload": base64.b64encode(path.read_bytes()).decode("ascii")}
        for path in sorted((root / "definition/tables").glob("*.tmdl"))
    ]}
    _, stage, _ = current_profile.load_profile()
    initial = {"parts": [
        inline_part(part["path"], stage) if part["path"].endswith("/stage_config.json") else part
        for part in fixture()["parts"]
    ]}
    reviewed, _ = quality_candidate.compile_candidate(initial, model)
    draft = {part["path"]: part for part in reviewed["parts"] if "/draft/" in part["path"]}
    for part in reviewed["parts"]:
        if "/published/" in part["path"]:
            part["payload"] = draft[part["path"].replace("/published/", "/draft/")]["payload"]
    return reviewed, model


def pin_model(model):
    part = next(p for p in model["parts"] if p["path"] == candidate.MODEL_PATH)
    return hashlib.sha256(base64.b64decode(part["payload"])).hexdigest()


def compile_fixture(agent, model):
    return candidate.compile_candidate(
        agent, model, expected_agent_sha256=definition_digest(agent),
        expected_model_part_sha256=pin_model(model),
    )


class DecompositionCandidateTests(unittest.TestCase):
    def setUp(self):
        self.agent, self.model = fixtures()
        self.after, self.model_after, self.receipt = compile_fixture(self.agent, self.model)

    def test_exact_agent_field_diff_and_source_identity_preservation(self):
        original = {p["path"]: p for p in self.agent["parts"]}
        actual = {p["path"]: p for p in self.after["parts"]}
        changed = [path for path in original if original[path] != actual[path]]
        self.assertEqual(changed, ["Files/Config/draft/stage_config.json"])
        before_docs, before_sources, _ = stage_sources(self.agent, "draft")
        after_docs, after_sources, _ = stage_sources(self.after, "draft")
        path = changed[0]
        before_config, after_config = copy.deepcopy(before_docs[path]), copy.deepcopy(after_docs[path])
        before_config.pop("aiInstructions")
        after_config.pop("aiInstructions")
        self.assertEqual(before_config, after_config)
        self.assertEqual(before_sources, after_sources)
        text = after_docs[path]["aiInstructions"]
        self.assertIn("EVERY applicable subquestion", text)
        self.assertIn("unless the user explicitly changes scope", text)
        self.assertIn("A separate filtered total does not scope another query", text)
        self.assertLessEqual(len(text.encode("utf-16-le")) // 2, 10000)
        self.assertTrue(all(n <= 10000 for n in self.receipt["unchangedSourceInstructionUtf16Units"].values()))
        self.assertFalse(self.receipt["semanticModelSourceInstructionsSupported"])

    def test_model_changes_only_five_descriptions_and_preserves_all_expressions(self):
        before = {p["path"]: p for p in self.model["parts"]}
        after = {p["path"]: p for p in self.model_after["parts"]}
        self.assertEqual([p for p in before if before[p] != after[p]], [candidate.MODEL_PATH])
        raw = base64.b64decode(before[candidate.MODEL_PATH]["payload"])
        updated = base64.b64decode(after[candidate.MODEL_PATH]["payload"])
        old_lines, new_lines = raw.splitlines(keepends=True), updated.splitlines(keepends=True)
        self.assertEqual([l for l in old_lines if l.startswith(b"\tmeasure ")],
                         [l for l in new_lines if l.startswith(b"\tmeasure ")])
        retained = [l for l in new_lines if not l.startswith((
            b"\t/// Filter semantics:", b"\t/// Executable definition:",
        ))]
        self.assertEqual(raw, b"".join(retained))
        self.assertEqual(len(self.receipt["changedModelFields"]), 5)
        self.assertEqual(sum(l.startswith(b"\tmeasure ") for l in new_lines), 10)
        self.assertNotIn(b"PrepForAI", updated)
        self.assertNotIn(b"aiInstructions", updated)

    def test_definition_description_is_derived_not_a_benchmark_answer(self):
        modified = copy.deepcopy(self.model)
        part = next(p for p in modified["parts"] if p["path"] == candidate.MODEL_PATH)
        raw = base64.b64decode(part["payload"]).replace(b' = "RealtimeIncrement"', b' = "OtherPopulation"')
        part["payload"] = base64.b64encode(raw).decode("ascii")
        _, output, _ = compile_fixture(self.agent, modified)
        text = base64.b64decode(next(p for p in output["parts"] if p["path"] == candidate.MODEL_PATH)["payload"]).decode()
        self.assertIn('/// Executable definition: CALCULATE', text)
        self.assertIn('"OtherPopulation"', text)
        additions = candidate.DECOMPOSITION + candidate.FILTER_DESCRIPTION
        for forbidden in ("B08", "B17", "95,542,000", "95542000", "2,925,000", "2925000", "Verified Answer"):
            self.assertNotIn(forbidden, additions)
        self.assertEqual(self.receipt["fewshotsAdded"], 0)
        self.assertEqual(self.receipt["cloudCalls"], 0)
        self.assertFalse(self.receipt["answerAccuracyAccepted"])

    def test_reject_drift_duplicates_concurrent_draft_and_overlength(self):
        with self.assertRaisesRegex(ValueError, "reviewed input pin"):
            candidate.compile_candidate(self.agent, self.model)
        duplicate = copy.deepcopy(self.model)
        duplicate["parts"].append(copy.deepcopy(duplicate["parts"][0]))
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            compile_fixture(self.agent, duplicate)
        docs, _, _ = stage_sources(self.agent, "draft")
        path = "Files/Config/draft/stage_config.json"
        changed = copy.deepcopy(self.agent)
        config = copy.deepcopy(docs[path])
        config["aiInstructions"] += "\nConcurrent change."
        changed["parts"] = [inline_part(path, config) if p["path"] == path else p for p in changed["parts"]]
        with self.assertRaisesRegex(ValueError, "concurrent work"):
            compile_fixture(changed, self.model)
        overlength = copy.deepcopy(self.agent)
        for stage in ("draft", "published"):
            path = f"Files/Config/{stage}/stage_config.json"
            config = copy.deepcopy(docs["Files/Config/draft/stage_config.json"])
            config["aiInstructions"] += "\U0001f600" * 1000
            overlength["parts"] = [inline_part(path, config) if p["path"] == path else p for p in overlength["parts"]]
        with self.assertRaisesRegex(ValueError, "service limit"):
            compile_fixture(overlength, self.model)
        source_overlength = copy.deepcopy(self.agent)
        _, published_sources, _ = stage_sources(source_overlength, "published")
        source_path, source = published_sources["semantic_model"]
        source = copy.deepcopy(source)
        source["dataSourceInstructions"] = "\U0001f600" * 5001
        source_overlength["parts"] = [
            inline_part(source_path, source) if p["path"] == source_path else p
            for p in source_overlength["parts"]
        ]
        with self.assertRaisesRegex(ValueError, "source instructions exceed"):
            compile_fixture(source_overlength, self.model)
        with self.assertRaisesRegex(ValueError, "owning table"):
            candidate.compile_candidate(self.agent, self.model, expected_agent_sha256=definition_digest(self.agent),
                                        expected_model_part_sha256="0" * 64)

    def test_deterministic_without_input_mutation(self):
        saved = copy.deepcopy((self.agent, self.model))
        self.assertEqual((self.after, self.model_after, self.receipt), compile_fixture(self.agent, self.model))
        self.assertEqual(saved, (self.agent, self.model))


if __name__ == "__main__":
    unittest.main()
