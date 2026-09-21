"""Keep the participant entry points free of internal investigation history."""

from __future__ import annotations

import json
from pathlib import Path
import re
import unittest
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[3]
EDITION = "unified-20260914"
RETIRED_REPORTS = {
    "core-baseline-upgrade-evaluation.md",
    "core-evidence-followup.md",
    "core-native-improvement-results.md",
    "data-agent-improvement-report.md",
}
PAIR = {
    f"Fabric_IQ_Ontology_Workshop_Furusato_Participant_v2.7.0_{EDITION}.docx",
    f"furusato-workshop-v2-7-0-complete_{EDITION}.html",
}


class ParticipantDistributionTests(unittest.TestCase):
    def deployment_prompts(self):
        text = (ROOT / "README.md").read_text("utf-8")
        prompts = []
        for heading in ("### デプロイ依頼プロンプト", "### Copy-paste deployment prompt"):
            section = text.split(heading, 1)[1].split("\n### ", 1)[0]
            blocks = re.findall(r"```text\n(.*?)\n```", section, flags=re.S)
            self.assertEqual(len(blocks), 1, heading)
            prompts.append(blocks[0])
        return prompts

    def usage_references(self):
        text = (ROOT / "README.md").read_text("utf-8")
        return [
            text.split(heading, 1)[1].split("\n### ", 1)[0]
            for heading in (
                "### 参考実績：時間・AI利用量（2026-09-17）",
                "### Reference run: time and AI usage (2026-09-17)",
            )
        ]

    def test_usage_reference_tables_preserve_bilingual_usd_jpy_values(self):
        expected = [
            ("1,739.67", "$17.40", "2,716"),
            ("2,102.27", "$21.02", "3,283"),
            ("2,672.97", "$26.73", "4,174"),
            ("1,005.27", "$10.05", "1,570"),
            ("2,758.43", "$27.58", "4,307"),
            ("1,125.73", "$11.26", "1,758"),
            ("1,346.77", "$13.47", "2,103"),
            ("410.81", "$4.11", "641"),
            ("1,409.80", "$14.10", "2,201"),
            ("2,317.21", "$23.17", "3,618"),
            ("16,888.95", "$168.89", "26,372"),
        ]
        for section in self.usage_references():
            rows = [line for line in section.splitlines() if line.startswith("|") and "$" in line]
            self.assertEqual(len(rows), len(expected))
            for row, values in zip(rows, expected):
                columns = [column.strip().replace("**", "") for column in row.strip("|").split("|")]
                with self.subTest(row=columns[0]):
                    self.assertEqual(len(columns), 5)
                    self.assertEqual(columns[2:4], list(values[:2]))
                    self.assertEqual(columns[4].replace("JPY ", "").removesuffix("円"), values[2])

    def test_usage_reference_is_dated_scoped_and_not_an_invoice_guarantee(self):
        japanese, english = self.usage_references()
        for section in (japanese, english):
            for marker in ("2026-09-17", "00:41:07", "03:44:24", "JST", "140", "gpt-6-astra",
                           "1 AI credit = $0.01 USD", "156.147", "08:21:39", "1789600899",
                           "https://query1.finance.yahoo.com/v8/finance/chart/JPY=X"):
                self.assertIn(marker, section)
            self.assertNotRegex(section, r"\b[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}\b")
            self.assertNotIn(".copilot", section)
        for marker in ("参考値", "保証するものではありません", "追加請求額ではありません",
                       "丸め前の USD", "当日終値", "為替手数料", "同期完了後", "CU 費用"):
            self.assertIn(marker, japanese)
        for marker in ("reference values", "not a standard duration", "additional invoice charges",
                       "unrounded USD", "daily closing rate", "FX fees", "post-synchronization", "CU charges"):
            self.assertIn(marker, english)

    def test_deployment_prompts_preserve_current_apply_and_ingestion_contracts(self):
        contract = json.loads(
            (ROOT / "workshop" / "v2.7.0" / "participant-workspace-contract.json").read_text("utf-8")
        )
        for prompt in self.deployment_prompts():
            for marker in (
                "https://github.com/yang-jiayi/furusato-fabric-workshop", "main",
                "PARTICIPANT_ID:", "EXPECTED_WORKSPACE_NAME", "subfolderId",
                "ENABLE_UNIFIED_DATA_AGENT=True", "ENABLE_AI_REFERENCE_ARCHITECTURE=False",
                "USE_PARTICIPANT_NOTEBOOK_NAMES=True", "ALLOW_AUTOMATED_APPLY=True",
                "APPLY_CHANGES=False", "APPLY_CHANGES=True",
                "PLAN_SHA256", "CONFIRMED_PLAN_SHA256",
                "EXCLUSIVE_CREATE_WINDOW_CONFIRMED=True", "EXCLUSIVE_APPLY_WINDOW_CONFIRMED=True",
                "FileCreated", "Subject", "Ready",
                "donation_events_001.csv", "donation_events_002.csv", "donation_events_003.csv",
                "profileRevision", "SHA-256", "reseal_runtime.py --check",
            ):
                with self.subTest(marker=marker):
                    self.assertIn(marker, prompt)
            for flag in contract["workshopProvisioningAutomation"]["requiredApplyFlags"]:
                self.assertIn(flag, prompt)
            self.assertNotRegex(prompt, r"\b[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}\b")
            self.assertNotIn(".copilot", prompt)

    def test_deployment_prompts_require_approval_and_prompt_blocker_reporting(self):
        japanese, english = self.deployment_prompts()
        for marker in ("承認を得る", "5分以内", "最後に成功した操作", "無言で手動 Pipeline",
                       "削除・復元・上書き", "実際の入力・実行済み Python", "満点や常時成功を保証しない"):
            self.assertIn(marker, japanese)
        for marker in ("obtain approval", "within five minutes", "last successful operation",
                       "Do not silently substitute a manual Pipeline", "Do not delete, restore, overwrite",
                       "actual inputs, executed Python", "do not promise full marks or universal success"):
            self.assertIn(marker, english)

    def test_docs_inventory_contains_only_current_participant_materials(self):
        expected = PAIR | {"single-agent-workshop.md", "data-validation-checklist.md"}
        actual = {path.name for path in (ROOT / "docs").iterdir() if path.is_file()}
        self.assertEqual(actual, expected)
        self.assertTrue((ROOT / "docs" / "assets").is_dir())

    def test_entry_points_do_not_reintroduce_internal_reports_or_scores(self):
        for relative in ("README.md", "docs/single-agent-workshop.md"):
            text = ROOT.joinpath(*relative.split("/")).read_text("utf-8")
            with self.subTest(path=relative):
                for name in RETIRED_REPORTS:
                    self.assertNotIn(name, text)
                self.assertNotRegex(text, r"\bCore-[A-E]\b|SR_JA|Windows Hello")
                self.assertNotRegex(text, r"\b(?:148|154|146|152)/168\b")
                self.assertNotRegex(text, r"conv_fab\w+|resp_fab\w+")
                self.assertIn("ENABLE_UNIFIED_DATA_AGENT=True", text)
                self.assertIn("ENABLE_AI_REFERENCE_ARCHITECTURE=False", text)

    def test_local_markdown_links_resolve_after_report_removal(self):
        paths = [ROOT / "README.md", ROOT / "SECURITY.md"]
        paths.extend((ROOT / "docs").glob("*.md"))
        paths.extend((ROOT / "tools").rglob("README.md"))
        for path in paths:
            text = path.read_text("utf-8")
            for target in re.findall(r"\[[^\]\n]*\]\(([^)\s]+)\)", text):
                parsed = urlsplit(target)
                if parsed.scheme or not parsed.path:
                    continue
                destination = (path.parent / unquote(parsed.path)).resolve()
                with self.subTest(path=str(path.relative_to(ROOT)), target=target):
                    self.assertTrue(destination.exists(), f"Broken local link: {target}")

    def test_removing_history_preserves_runtime_and_classification_assets(self):
        for relative in (
            "SECURITY.md", "LICENSE",
            "workshop/v2.7.0/data/DATASET.md",
            "workshop/v2.7.0/notebooks/Notebook_04_Furusato_Provision_Complete_Workshop.ipynb",
            "tools/docs/assets/style-carrier.zip",
        ):
            with self.subTest(path=relative):
                self.assertTrue(ROOT.joinpath(*relative.split("/")).is_file())


if __name__ == "__main__":
    unittest.main()
