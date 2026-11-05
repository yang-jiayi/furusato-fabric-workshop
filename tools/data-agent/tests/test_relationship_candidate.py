"""Static both-layer policy and byte invariants; not model-behavior evaluation."""
import copy
import unittest
from unittest.mock import patch

import dependency_candidate as dependency
import relationship_candidate as candidate
from evaluate_native import definition_digest
from measured_contract_profile import stage_sources
from source_grounded_profile import inline_part
from test_decomposition_candidate import fixtures, pin_model


class RelationshipCandidateTests(unittest.TestCase):
    def setUp(self):
        self.agent, self.model = fixtures()
        for part in self.agent["parts"]:
            part["path"] = part["path"].replace(
                "lakehouse_tables-Participant_lakehouse_tables", "lakehouse-tables-LH_Furusato_101"
            )
        self.pins = dict(expected_agent_sha256=definition_digest(self.agent),
                         expected_model_part_sha256=pin_model(self.model))
        self.old, self.old_model, _ = dependency.compile_candidate(self.agent, self.model, **self.pins)
        self.new, self.new_model, self.receipt = candidate.compile_candidate(
            self.agent, self.model, **self.pins)

    def test_exact_second_part_and_field_only(self):
        old = {p["path"]: p for p in self.old["parts"]}
        new = {p["path"]: p for p in self.new["parts"]}
        self.assertEqual(list(old), list(new))
        self.assertEqual([candidate.SOURCE_PATH], [p for p in old if old[p] != new[p]])
        a = copy.deepcopy(stage_sources(self.old, "draft")[0])
        b = copy.deepcopy(stage_sources(self.new, "draft")[0])
        text = a[candidate.SOURCE_PATH]["dataSourceInstructions"]
        self.assertEqual(text.replace(candidate.BEFORE, candidate.AFTER, 1),
                         b[candidate.SOURCE_PATH]["dataSourceInstructions"])
        b[candidate.SOURCE_PATH]["dataSourceInstructions"] = text
        self.assertEqual(a, b)
        self.assertEqual(self.old_model, self.new_model)
        self.assertEqual(2, len(self.receipt["changedAgentFields"]))
        self.assertEqual(9994, self.receipt["globalInstructionUtf16Units"])
        self.assertLessEqual(self.receipt["changedSourceInstructionUtf16Units"]["lakehouse_tables"], 10000)

    def test_verified_local_lookup_requires_instance_and_related_key(self):
        text = candidate.AFTER
        for required in ("only after an actual local Ontology query has returned",
                         "requested relationship predicate and related stable ID",
                         "separate exact-key SQL lookup", "sources' exact keys",
                         "cite Ontology for the verified relationship and SQL for attributes"):
            self.assertIn(required, text)
        global_text = stage_sources(self.new, "draft")[0]["Files/Config/draft/stage_config.json"]["aiInstructions"]
        self.assertIn(dependency.DEPENDENCY, global_text)
        self.assertIn(dependency.prior.DECOMPOSITION, global_text)

    def test_unverified_relationship_cannot_use_fk_or_federation_fallback(self):
        for required in ("Schema/context alone or a local-only federation response is not that evidence",
                         "unavailable or unverified", "state the relationship limitation",
                         "never infer a fallback from foreign keys"):
            self.assertIn(required, candidate.AFTER)

    def test_requested_gql_and_membership_counts_remain_separate(self):
        text = stage_sources(self.new, "draft")[0][candidate.SOURCE_PATH]["dataSourceInstructions"]
        for required in ("does not satisfy requested GQL/Graph execution",
                         "never relabel SQL as GQL", "does not answer membership/containment sets",
                         "or relationship-backed counts",
                         "Do not answer them by counting or grouping `ot_municipality.PrefectureId`"):
            self.assertIn(required, text)
        self.assertFalse(self.receipt["runtimeBehaviorVerified"])
        self.assertFalse(self.receipt["answerAccuracyAccepted"])
        self.assertEqual(0, self.receipt["cloudCalls"])

    def test_fail_closed_and_nonmutating(self):
        saved = copy.deepcopy((self.agent, self.model))
        self.assertEqual((self.new, self.new_model, self.receipt),
                         candidate.compile_candidate(*saved, **self.pins))
        self.assertEqual(saved, (self.agent, self.model))
        with patch.object(candidate, "BEFORE", "missing anchor"):
            with self.assertRaisesRegex(ValueError, "anchor changed"):
                candidate.compile_candidate(*saved, **self.pins)
        with patch.object(candidate, "AFTER", candidate.AFTER + "x" * 10000):
            with self.assertRaisesRegex(ValueError, "service limit"):
                candidate.compile_candidate(*saved, **self.pins)


if __name__ == "__main__":
    unittest.main()
