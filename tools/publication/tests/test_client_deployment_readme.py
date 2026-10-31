"""The current README leads to complete client, preview, gate and integrity guidance in Lab."""
from __future__ import annotations

import ast
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[3]
WORKSHOP = ROOT / "workshop/v3.0.0-preview"
CLIENTS = ("GitHub Copilot Desktop / Copilot app", "GitHub Copilot CLI", "Claude Code",
           "OpenAI Codex", "Scout", "Microsoft 365 Copilot Cowork")


def assignments(source):
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
        cls.readme = (ROOT / "README.md").read_text()
        cls.chapter = next((ROOT / "Lab").glob("24-*/README.md")).parent
        cls.client_path = next(cls.chapter.glob("*-24-10-*.md"))
        cls.integrity_path = next(cls.chapter.glob("*-24-11-*.md"))
        cls.client_text = cls.client_path.read_text()
        cls.integrity_text = cls.integrity_path.read_text()
        cls.sections = [cls.client_text.split("<details>", 1)[0],
                        cls.client_text.split("<summary>English</summary>", 1)[1].split("</details>", 1)[0]]

    def test_readme_and_lab_index_reach_latest_client_and_integrity_guidance(self):
        self.assertIn(f"](Lab/{self.chapter.name}/README.md)", self.readme)
        contents = (self.chapter / "README.md").read_text()
        self.assertIn(f"]({self.client_path.name})", contents)
        self.assertIn(f"]({self.integrity_path.name})", contents)
        for section in self.sections:
            for client in CLIENTS:
                self.assertIn(client, section)
            for host in ("https://docs.github.com/", "https://code.claude.com/", "https://developers.openai.com/"):
                self.assertIn(host, section)

    def test_preview_parameters_match_current_released_notebook_and_keep_gates(self):
        notebook = json.loads(next((WORKSHOP / "notebooks").glob("Notebook_04_*.ipynb")).read_text())
        declared = assignments("\n".join("".join(cell["source"]) for cell in notebook["cells"]
                              if "parameters" in cell.get("metadata", {}).get("tags", [])))
        examples = []
        for section in self.sections:
            blocks = re.findall(r"```python\n(.*?)\n```", section, flags=re.S)
            self.assertEqual(1, len(blocks))
            values = assignments(blocks[0])
            self.assertFalse(set(values) - set(declared))
            for name in ("APPLY_CHANGES", "ALLOW_AUTOMATED_APPLY", "RUN_NOTEBOOK01"):
                self.assertIs(False, values[name])
                self.assertIs(declared[name], values[name])
            self.assertEqual("", values["CONFIRMED_PLAN_SHA256"])
            self.assertEqual("preflight", values["ACTION"])
            for name in ("PARTICIPANT_ID", "ENVIRONMENT", "EXPECTED_WORKSPACE_NAME", "SCOPE_FILE",
                         "PLAN_FILE", "WRITE_GATE_FILE", "PRIVATE_EVIDENCE_DIR"):
                self.assertIn(name, values)
            examples.append(values)
        self.assertEqual(examples[0], examples[1])

    def test_common_current_deployment_commands_and_exact_approval_remain_complete(self):
        steps = "\n".join(path.read_text() for path in self.chapter.glob("*.md"))
        for command in ("az login --tenant", "preflight @Common --online", "deploy-sources", "--run-notebook01",
                        "verify-sources", "deploy-notebooks", "deploy-realtime", "deploy-core", "start-activator",
                        "check-activator-readiness", "stop-activator", "verify-gold", "deploy-semantic-model",
                        "refresh-model", "verify-model", "deploy-agent", "publish-agent"):
            self.assertIn(command, steps)
        for gate in ("$Plan.blockers", "$Plan.planSha256", "APPROVE $PlanSha", "$MappingEvidence",
                     "$GateDocument.allowCloudMutations", "$GateDocument.folderMappingVerified",
                     "$GateDocument.approvedAt", '"--write-gate", $Gate, "--confirm", $PlanSha'):
            self.assertIn(gate, steps)
        self.assertIn("FileCreated", steps)
        self.assertIn("PLAN_SHA256", steps)

    def test_client_commands_start_with_planning_and_match_across_languages(self):
        commands = [re.findall(r"```powershell\n(.*?)\n```", section, flags=re.S) for section in self.sections]
        self.assertEqual(commands[0], commands[1])
        for blocks in commands:
            text = "\n".join(blocks)
            for command in ("copilot --plan", "claude --permission-mode plan",
                            "codex --sandbox read-only --ask-for-approval on-request"):
                self.assertIn(command, text)
            self.assertNotRegex(text, r"--allow-all|--yolo|--autopilot|--dangerously|bypassPermissions|gh copilot")
        for section in self.sections:
            self.assertIn("--help", section)
            self.assertIn("MCP", section)
            self.assertNotRegex(section, r"\b[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}\b")

    def test_scout_identity_and_cowork_capabilities_are_not_assumed(self):
        for section in self.sections:
            for marker in ("Microsoft Scout (Frontier)", "https://learn.microsoft.com/en-us/microsoft-scout/overview",
                           "https://docs.scoutos.com/introduction", "Power BI",
                           "https://learn.microsoft.com/en-us/microsoft-365/copilot/cowork/get-started",
                           "https://learn.microsoft.com/en-us/microsoft-365/copilot/cowork/cowork-faq",
                           "https://learn.microsoft.com/en-us/fabric/iq/connectors/cowork-overview"):
                self.assertIn(marker, section)
        self.assertIn("利用する場合に限ります", self.sections[0])
        self.assertIn("applies only if using", self.sections[1])
        self.assertIn("do not assume a local shell", self.sections[1])

    def test_integrity_commands_preserve_status_and_isolate_reseal(self):
        for marker in ("Test-IncrementConsistency.ps1", "Test-OntologyCardinality.ps1",
                       "$LASTEXITCODE", "git status --porcelain", "git archive --format=zip",
                       "Expand-Archive", "Push-Location", "finally", "Pop-Location",
                       "sys.version_info[:2] == (3, 13)"):
            self.assertIn(marker, self.integrity_text)
        for section in self.integrity_text.split("<details>"):
            checks = [block for block in re.findall(r"```powershell\n(.*?)\n```", section, flags=re.S)
                      if "reseal_runtime.py --check" in block]
            self.assertEqual(1, len(checks))
            self.assertLess(checks[0].index("Push-Location"), checks[0].index("reseal_runtime.py --check"))
        self.assertIn("読み取り専用ではありません", self.integrity_text)
        self.assertIn("not read-only", self.integrity_text)


if __name__ == "__main__":
    unittest.main()
