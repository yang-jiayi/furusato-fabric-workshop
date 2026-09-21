"""Keep client entry points aligned with the released, gated Notebook workflow."""

from __future__ import annotations

import ast
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[3]
WORKSHOP = ROOT / "workshop" / "v2.7.0"
CLIENTS = (
    "GitHub Copilot Desktop / Copilot app",
    "GitHub Copilot CLI",
    "Claude Code",
    "OpenAI Codex",
    "Scout",
    "Microsoft 365 Copilot Cowork",
)


def assignments(source: str) -> dict[str, object]:
    values = {}
    for node in ast.parse(source).body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    values[target.id] = ast.literal_eval(node.value)
    return values


class ClientDeploymentReadmeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = (ROOT / "README.md").read_text("utf-8")
        cls.sections = [
            cls.text.split(heading, 1)[1].split("\n### ", 1)[0]
            for heading in (
                "### ツール別のデプロイ手順",
                "### Deployment by client",
            )
        ]

    def test_both_languages_have_six_client_entry_points(self):
        for section in self.sections:
            for client in CLIENTS:
                with self.subTest(client=client):
                    self.assertEqual(section.count(f"#### {client}\n"), 1)
            self.assertIn("2026-09-18", section)
            self.assertIn("https://docs.github.com/", section)
            self.assertIn("https://code.claude.com/", section)
            self.assertIn("https://developers.openai.com/", section)

    def test_preview_parameters_are_real_and_preserve_all_gates(self):
        notebook = json.loads(
            (WORKSHOP / "notebooks" / "Notebook_04_Furusato_Provision_Complete_Workshop.ipynb")
            .read_text("utf-8")
        )
        declared = assignments("\n".join(
            "".join(cell["source"])
            for cell in notebook["cells"]
            if "parameters" in cell.get("metadata", {}).get("tags", [])
        ))
        contract = json.loads((WORKSHOP / "participant-workspace-contract.json").read_text("utf-8"))
        expected = {
            flag: True
            for flag in contract["workshopProvisioningAutomation"]["requiredApplyFlags"]
        } | {
            "APPLY_CHANGES": False,
            "CONFIRMED_PLAN_SHA256": "",
            "EXCLUSIVE_CREATE_WINDOW_CONFIRMED": False,
            "ALLOW_AUTOMATED_APPLY": False,
            "USE_PARTICIPANT_NOTEBOOK_NAMES": True,
            "ENABLE_UNIFIED_DATA_AGENT": True,
            "ENABLE_AI_REFERENCE_ARCHITECTURE": False,
        }
        examples = []
        for section in self.sections:
            blocks = re.findall(r"```python\n(.*?)\n```", section, flags=re.S)
            self.assertEqual(len(blocks), 1)
            values = assignments(blocks[0])
            self.assertEqual(set(values) - set(declared), set())
            for name, value in expected.items():
                with self.subTest(parameter=name):
                    if isinstance(value, bool):
                        self.assertIs(values[name], value)
                    else:
                        self.assertEqual(values[name], value)
            self.assertIn("PARTICIPANT_ID", values)
            self.assertIn("EXPECTED_WORKSPACE_NAME", values)
            examples.append(values)
        self.assertEqual(examples[0], examples[1])

    def test_client_commands_start_with_planning_or_read_only_access(self):
        expected = (
            "copilot --plan",
            "claude --permission-mode plan",
            "codex --sandbox read-only --ask-for-approval on-request",
        )
        for section in self.sections:
            commands = "\n".join(re.findall(r"```powershell\n(.*?)\n```", section, flags=re.S))
            for command in expected:
                self.assertIn(command, commands)
            self.assertNotRegex(
                commands,
                r"--allow-all|--yolo|--autopilot|--dangerously|bypassPermissions|gh copilot",
            )
            self.assertNotIn("claude --permission-mode default", commands)

    def test_verification_does_not_claim_six_live_deployments(self):
        japanese, english = self.sections
        self.assertIn("6製品すべての実機デプロイを検証したものではありません", japanese)
        self.assertIn("not an end-to-end deployment test of all six clients", english)
        for section in self.sections:
            self.assertIn("FileCreated", section)
            self.assertIn("PLAN_SHA256", section)
            self.assertIn("MCP", section)
            visible = re.sub(r"https://[^)\s]+", "", section)
            self.assertNotRegex(visible, r"\b[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}\b")
            self.assertNotIn("C:\\Users\\", section)

    def test_local_commands_match_across_languages(self):
        blocks = [
            re.findall(r"```powershell\n(.*?)\n```", section, flags=re.S)
            for section in self.sections
        ]
        self.assertEqual(blocks[0], blocks[1])

    def test_scout_identity_is_conditional_and_cowork_has_no_assumed_shell(self):
        for section in self.sections:
            scout = section.split("#### Scout\n", 1)[1].split("\n#### ", 1)[0]
            cowork = section.split("#### Microsoft 365 Copilot Cowork\n", 1)[1]
            for marker in (
                "Microsoft Scout (Frontier)",
                "https://learn.microsoft.com/en-us/microsoft-scout/overview",
                "https://docs.scoutos.com/introduction",
            ):
                self.assertIn(marker, scout)
            for marker in (
                "https://learn.microsoft.com/en-us/microsoft-365/copilot/cowork/get-started",
                "https://learn.microsoft.com/en-us/microsoft-365/copilot/cowork/cowork-faq",
                "https://learn.microsoft.com/en-us/fabric/iq/connectors/cowork-overview",
                "Power BI",
            ):
                self.assertIn(marker, cowork)
            self.assertNotIn("```powershell", scout + cowork)
            self.assertNotIn("az login", scout + cowork)
        self.assertIn("を利用する場合に限ります", self.sections[0])
        self.assertIn("applies only if using", self.sections[1])

    def test_reseal_command_is_scoped_to_a_disposable_committed_copy(self):
        section = self.text.split("### 検証と再生成", 1)[1].split("\n## English", 1)[0]
        blocks = re.findall(r"```powershell\n(.*?)\n```", section, flags=re.S)
        checks = [block for block in blocks if "reseal_runtime.py --check" in block]
        self.assertEqual(len(checks), 1)
        for marker in (
            "git status --porcelain",
            "git archive --format=zip",
            "Expand-Archive",
            "Push-Location",
            "finally",
            "Pop-Location",
            "$LASTEXITCODE",
        ):
            self.assertIn(marker, checks[0])
        self.assertIn("読み取り専用ではありません", section)


if __name__ == "__main__":
    unittest.main()
