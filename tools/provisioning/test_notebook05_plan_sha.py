"""Offline Notebook05 plan hash helper; no Spark or network."""

from __future__ import annotations

from pathlib import Path
import re
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import notebook05_plan_sha as helper


class Notebook05PlanShaTests(unittest.TestCase):
    def test_hash_is_deterministic_and_bound_to_participant(self):
        first = helper.build_plan("107", "Workshop A")
        self.assertRegex(first["sha256"], re.compile(r"\A[0-9a-f]{64}\Z"))
        self.assertEqual(first, helper.build_plan("107", "Workshop A"))
        self.assertEqual(first["document"]["participantId"], "107")
        self.assertNotEqual(first["sha256"], helper.build_plan("108", "Workshop A")["sha256"])

    def test_automated_apply_binds_the_workspace_name(self):
        automated = helper.build_plan("107", "Workshop A")
        self.assertTrue(automated["document"]["allowAutomatedApply"])
        self.assertNotEqual(automated["sha256"], helper.build_plan("107", "Workshop B")["sha256"])
        manual = helper.build_plan("107", "Workshop A", automated_apply=False)
        self.assertNotIn("allowAutomatedApply", manual["document"])
        self.assertNotEqual(automated["sha256"], manual["sha256"])
        self.assertEqual(manual["sha256"], helper.build_plan("107", "Workshop B", automated_apply=False)["sha256"])

    def test_runtime_module_is_not_left_registered(self):
        helper.build_plan("107", "Workshop A")
        self.assertNotIn("notebook05_runtime", sys.modules)


if __name__ == "__main__":
    unittest.main()
