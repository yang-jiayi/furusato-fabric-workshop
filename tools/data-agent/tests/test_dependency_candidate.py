"""Offline invariant tests, not live routing or answer-quality evaluation."""
import base64
import copy
import re
import unittest
from unittest.mock import patch

import decomposition_candidate as prior
import dependency_candidate as candidate
from evaluate_native import definition_digest
from measured_contract_profile import stage_sources
from source_grounded_profile import inline_part
from test_decomposition_candidate import fixtures, pin_model


def compile_fixture(agent, model):
    return candidate.compile_candidate(
        agent, model, expected_agent_sha256=definition_digest(agent),
        expected_model_part_sha256=pin_model(model),
    )


class DependencyCandidateTests(unittest.TestCase):
    def setUp(self):
        self.agent, self.model = fixtures()
        self.old, self.old_model, self.old_receipt = prior.compile_candidate(
            self.agent, self.model, expected_agent_sha256=definition_digest(self.agent),
            expected_model_part_sha256=pin_model(self.model))
        self.new, self.new_model, self.receipt = compile_fixture(self.agent, self.model)

    def test_exact_field_diffs_and_prior_model_bytes(self):
        old = {p["path"]: p for p in self.old["parts"]}
        new = {p["path"]: p for p in self.new["parts"]}
        path = "Files/Config/draft/stage_config.json"
        self.assertEqual([path], [p for p in old if old[p] != new[p]])
        a = json_config(old[path])
        b = json_config(new[path])
        before, after = a.pop("aiInstructions"), b.pop("aiInstructions")
        self.assertEqual(a, b)
        expected = before
        for source, target in candidate.COMPACTIONS:
            self.assertEqual(1, expected.count(source))
            expected = expected.replace(source, target, 1)
        inherited_line = next(line for line in expected.splitlines() if line.startswith(prior.DECOMPOSITION))
        expected = expected.replace(inherited_line, inherited_line + "\n" + candidate.DEPENDENCY, 1)
        self.assertEqual(expected, after)
        self.assertIn(prior.DECOMPOSITION, after)
        self.assertEqual(self.old_model, self.new_model)
        self.assertEqual(stage_sources(self.old, "draft")[1], stage_sources(self.new, "draft")[1])
        self.assertTrue(self.receipt["allTenExecutableMeasuresBytePreserved"])
        self.assertEqual(5, len(self.receipt["changedModelFields"]))

    def test_dependency_population_rank_and_explanation_guards(self):
        text = candidate.DEPENDENCY
        for marker in (
            "first source's key before", "exact returned-ID predicate",
            "type, leading zeros and full representation", "nonempty target_entities",
            "required_fields is not a target", "local relationship traversal",
            "does not block separate supported source queries", "source-field key mapping",
            "operational window does not filter a static snapshot", "without reranking its single row",
            "full intended population before", "applicable user filters",
            "Do not fetch all entities or raise caps",
        ):
            self.assertIn(marker, text)
        self.assertLessEqual(self.receipt["globalInstructionUtf16Units"], 10000)
        self.assertTrue(all(n <= 10000 for n in self.receipt["unchangedSourceInstructionUtf16Units"].values()))
        additions = text + "".join(new for _, new in candidate.COMPACTIONS)
        self.assertFalse(re.search(r"\bB(?:08|15|17)\b|\b20(?:25|26)\b|\b\d{5,}\b", additions))
        self.assertFalse(self.receipt["answerAccuracyAccepted"])
        self.assertFalse(self.receipt["runtimeBehaviorVerified"])
        self.assertEqual(0, self.receipt["cloudCalls"])

    def test_unchanged_sections_and_compact_safeguards(self):
        old_docs = stage_sources(self.old, "draft")[0]
        new_docs = stage_sources(self.new, "draft")[0]
        key = "Files/Config/draft/stage_config.json"
        before, after = old_docs[key]["aiInstructions"], new_docs[key]["aiInstructions"]
        for line in before.splitlines():
            if line not in {a for a, _ in candidate.COMPACTIONS}:
                self.assertIn(line, after)
        for marker in ("All timestamps are UTC.", "FirstObservedAtUtc", "LastObservedAtUtc",
                       "without computing or repeating", "EventID", "raw-minus-Gold",
                       "relationship-backed count", "verified binding/runtime", "Preserve BLANK",
                       "Do not bypass a platform content block"):
            self.assertIn(marker, after)

    def test_deterministic_nonmutating_and_fail_closed(self):
        saved = copy.deepcopy((self.agent, self.model))
        self.assertEqual((self.new, self.new_model, self.receipt), compile_fixture(*saved))
        self.assertEqual(saved, (self.agent, self.model))
        with patch.object(candidate, "DEPENDENCY", candidate.DEPENDENCY + "\U0001f600" * 1000):
            with self.assertRaisesRegex(ValueError, "service limit"):
                compile_fixture(self.agent, self.model)
        with patch.object(candidate, "COMPACTIONS", (("missing anchor", "replacement"),)):
            with self.assertRaisesRegex(ValueError, "anchor changed"):
                compile_fixture(self.agent, self.model)
        with self.assertRaisesRegex(ValueError, "reviewed input pin"):
            candidate.compile_candidate(self.agent, self.model)
        # Concurrent Draft drift must still fail before any candidate is returned.
        drift = copy.deepcopy(self.agent)
        path = "Files/Config/draft/stage_config.json"
        docs = stage_sources(drift, "draft")[0]
        config = copy.deepcopy(docs[path])
        config["aiInstructions"] += "\nConcurrent edit"
        drift["parts"] = [inline_part(path, config) if p["path"] == path else p for p in drift["parts"]]
        with self.assertRaisesRegex(ValueError, "concurrent work"):
            compile_fixture(drift, self.model)


def json_config(part):
    import json
    return json.loads(base64.b64decode(part["payload"], validate=True))


if __name__ == "__main__":
    unittest.main()
