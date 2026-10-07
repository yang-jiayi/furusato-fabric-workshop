import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from build_native_tuning_addendum import render_html, sections, validate_study


class TuningAddendumTests(unittest.TestCase):
    def fixture(self):
        return {
            "schemaVersion": "furusato-native-tuning-study/v1", "date": "2026-10-03",
            "baseline": {"label": "baseline", "caseCount": 20, "content": {"PASS": 12, "FAIL": 7, "UNKNOWN": 1},
                         "factual": {"PASS": 15, "FAIL": 4, "UNKNOWN": 1}},
            "rounds": [{"label": "candidate", "caseCount": 20, "content": {"PASS": 20, "FAIL": 0, "UNKNOWN": 0},
                        "factual": {"PASS": 20, "FAIL": 0, "UNKNOWN": 0}}],
            "unseen": None, "cohortNoteJa": "固定した開発20問。",
            "changesJa": ["変更"], "changesEn": ["Change"], "remainingJa": ["未使用セット未実施"],
            "remainingEn": ["Unused set not run"], "mainPromoted": False,
            "oldStudiesChanged": False, "humanSignoff": False,
        }

    def test_unknown_prevents_all_pass_notice(self):
        study = self.fixture()
        study["rounds"][0]["content"] = {"PASS": 19, "FAIL": 0, "UNKNOWN": 1}
        self.assertIn("FAILまたはUNKNOWN", sections(study)[0]["paragraphs"][0])

    def test_absent_unseen_is_not_counted_as_pass(self):
        text = render_html(self.fixture(), "a" * 64)
        self.assertIn("未使用セットは未実施", text)
        self.assertIn("20 / 0 / 0", text)
        self.assertIn("独立した人間のsign-offではありません", text)

    def test_changed_denominator_and_missing_verdict_fail(self):
        for change in ({"PASS": 20, "FAIL": 1, "UNKNOWN": 0}, {"PASS": 20, "FAIL": 0}):
            study = self.fixture()
            study["rounds"][0]["content"] = change
            with self.assertRaises(ValueError):
                validate_study(study)

    def test_unseen_has_its_own_denominator(self):
        study = self.fixture()
        study["unseen"] = {"label": "unseen", "caseCount": 7,
                           "content": {"PASS": 5, "FAIL": 1, "UNKNOWN": 1},
                           "factual": {"PASS": 6, "FAIL": 0, "UNKNOWN": 1}}
        self.assertIn("未使用7問", sections(study)[1]["paragraphs"][0])

    def test_factual_failure_cannot_be_a_complete_content_pass(self):
        study = self.fixture()
        study["rounds"][0]["factual"] = {"PASS": 19, "FAIL": 1, "UNKNOWN": 0}
        with self.assertRaisesRegex(ValueError, "contradict"):
            validate_study(study)

    def test_expanded_cohort_is_not_relabelled_as_independent(self):
        study = self.fixture()
        study["unseen"] = {"label": "first unused", "caseCount": 12,
                           "content": {"PASS": 9, "FAIL": 3, "UNKNOWN": 0},
                           "factual": {"PASS": 10, "FAIL": 2, "UNKNOWN": 0}}
        study["expandedDevelopment"] = {
            "label": "known32", "caseCount": 32,
            "content": {"PASS": 32, "FAIL": 0, "UNKNOWN": 0},
            "factual": {"PASS": 32, "FAIL": 0, "UNKNOWN": 0},
            "formerlyUnusedQuestionsNowUsedForTuning": True,
        }
        page = render_html(study, "a" * 64)
        self.assertIn("9 / 3 / 0", page)
        self.assertIn("32 / 0 / 0", page)
        self.assertIn("新しい独立検証とは扱いません", page)
        study["expandedDevelopment"]["caseCount"] = 31
        study["expandedDevelopment"]["content"]["PASS"] = 31
        study["expandedDevelopment"]["factual"]["PASS"] = 31
        with self.assertRaisesRegex(ValueError, "both complete"):
            validate_study(study)

    def test_escapes_content_and_preserves_input(self):
        study = self.fixture()
        study["changesEn"] = ["<script>not executable</script>"]
        before = copy.deepcopy(study)
        page = render_html(study, "a" * 64)
        self.assertIn("&lt;script&gt;", page)
        self.assertNotIn("<script>", page)
        self.assertEqual(study, before)

    def test_standard_benchmark_table_matches_configurations(self):
        study = self.fixture()
        study["standardBenchmark"] = {
            "conditions": 84, "repetitions": 2, "ceiling": 77, "noteJa": "T10は遮断。", "noteEn": "T10 blocked.",
            "rows": [{"label": "baseline", "scores": [36, 34]}, {"label": "candidate", "scores": [74, 73]}],
        }
        page = render_html(study, "a" * 64)
        self.assertIn("74/84", page)
        self.assertIn("36/84", page)
        self.assertEqual(sections(study)[1]["title"], "標準10問・84条件 / Standard ten, 84 conditions")
        for change in ({"rows": [{"label": "candidate", "scores": [74, 73]}]},
                       {"rows": [{"label": "baseline", "scores": [36]}, {"label": "candidate", "scores": [74, 73]}]},
                       {"rows": [{"label": "baseline", "scores": [36, 34]}, {"label": "candidate", "scores": [78, 73]}]},
                       {"noteEn": " "}):
            broken = copy.deepcopy(study)
            broken["standardBenchmark"].update(change)
            with self.assertRaises(ValueError):
                validate_study(broken)

    def test_narrative_overrides_replace_defaults_in_pairs(self):
        study = self.fixture()
        study.update({"applyVerifyJa": ["正式Agentへ直接適用。"], "applyVerifyEn": ["Applied to the formal Agent."],
                      "adoptionJa": "利用者の指示で正式Agentへ反映。", "adoptionEn": "Applied on user instruction."})
        page = render_html(study, "a" * 64)
        self.assertIn("正式Agentへ直接適用。", page)
        self.assertIn("利用者の指示で正式Agentへ反映。", page)
        self.assertNotIn("比較用Agentを使い", page)
        self.assertNotIn("主Agentへは昇格していません", page)
        self.assertIn("AI補助審査", page)
        for key in ("applyVerifyEn", "adoptionJa"):
            broken = copy.deepcopy(study)
            del broken[key]
            with self.assertRaisesRegex(ValueError, "both Japanese and English"):
                validate_study(broken)
        broken = copy.deepcopy(study)
        broken["applyVerifyJa"] = []
        with self.assertRaisesRegex(ValueError, "nonempty"):
            validate_study(broken)


if __name__ == "__main__":
    unittest.main()
