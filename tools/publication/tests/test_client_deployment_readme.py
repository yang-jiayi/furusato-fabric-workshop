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


def require_immediate_exit_guard(block, command, *, compare=False):
    start = block.find(command)
    if start < 0:
        raise AssertionError(f"Missing command: {command}")
    following = block[start + len(command):]
    if compare:
        difference = re.match(
            r'\s*if\s*\(\s*\$LASTEXITCODE\s+-eq\s+1\s*\)\s*\{\s*throw\s+"[^"\r\n]+"\s*\}',
            following,
        )
        if difference is None:
            raise AssertionError("The inventory-difference exit must stop with a throw")
        following = following[difference.end():]
    guard = re.match(
        r'\s*if\s*\(\s*\$LASTEXITCODE\s+-ne\s+0\s*\)\s*\{\s*throw\s+"[^"\r\n]+"\s*\}',
        following,
    )
    if guard is None:
        raise AssertionError(f"Command lacks an immediate nonzero-exit throw: {command}")


def require_integrity_exit_guards(text):
    japanese = text.split("<details>", 1)[0]
    english = text.split("<summary>English</summary>", 1)[1].split("</details>", 1)[0]
    ja_blocks = re.findall(r"```powershell\n(.*?)\n```", japanese, flags=re.S)
    en_blocks = re.findall(r"```powershell\n(.*?)\n```", english, flags=re.S)
    if len(ja_blocks) != 2 or ja_blocks != en_blocks:
        raise AssertionError("Japanese and English sections must share both canonical PowerShell blocks")
    offline, generation = ja_blocks
    for command in (
        "pwsh ./tools/data/Test-IncrementConsistency.ps1 -DataRoot ./workshop/v3.0.0-preview/data",
        "python ./tools/provisioning/check_current_ontology.py",
    ):
        require_immediate_exit_guard(offline, command)
    for command in (
        'python -c "import sys; assert sys.version_info[:2] == (3, 13)"',
        "$Dirty = git status --porcelain",
        "$GitDir = (git rev-parse --absolute-git-dir).Trim()",
        "git archive --format=zip --output=$Archive HEAD",
        "python -c $Inventory $Source $BeforeInventory",
        "python -B ./tools/provisioning/build_preview30.py",
        "python -c $Inventory $Source $AfterInventory",
    ):
        require_immediate_exit_guard(generation, command)
    require_immediate_exit_guard(
        generation, "python -c $Compare $BeforeInventory $AfterInventory", compare=True,
    )
    return ja_blocks


def mutate_canonical_powershell(text, token, old, new):
    changed = 0

    def replace(match):
        nonlocal changed
        block = match.group(1)
        if token not in block:
            return match.group(0)
        if old not in block:
            raise AssertionError(f"Mutation anchor missing from canonical block: {old}")
        changed += 1
        return "```powershell\n" + block.replace(old, new) + "\n```"

    result = re.sub(r"```powershell\n(.*?)\n```", replace, text, flags=re.S)
    if changed != 2:
        raise AssertionError(f"Expected to mutate both language blocks, found {changed}")
    return result


class ClientDeploymentReadmeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.readme = (ROOT / "README.md").read_text(encoding="utf-8")
        cls.chapter = next((ROOT / "Lab").glob("24-*/README.md")).parent
        cls.client_path = next(cls.chapter.glob("*-24-10-*.md"))
        cls.integrity_path = next(cls.chapter.glob("*-24-11-*.md"))
        cls.client_text = cls.client_path.read_text(encoding="utf-8")
        cls.integrity_text = cls.integrity_path.read_text(encoding="utf-8")
        cls.sections = [cls.client_text.split("<details>", 1)[0],
                        cls.client_text.split("<summary>English</summary>", 1)[1].split("</details>", 1)[0]]

    def test_readme_and_lab_index_reach_latest_client_and_integrity_guidance(self):
        japanese, english = self.readme.split("## English", 1)
        chapter_index = f"Lab/{self.chapter.name}/README.md"
        self.assertIn(f"[第24章]({chapter_index})", japanese)
        self.assertIn(f"[Chapter 24]({chapter_index})", english)
        contents = (self.chapter / "README.md").read_text(encoding="utf-8")
        self.assertIn(f"]({self.client_path.name})", contents)
        self.assertIn(f"]({self.integrity_path.name})", contents)
        for section in self.sections:
            for client in CLIENTS:
                self.assertIn(client, section)
            for host in ("https://docs.github.com/", "https://code.claude.com/", "https://developers.openai.com/"):
                self.assertIn(host, section)

    def test_preview_parameters_match_current_released_notebook_and_keep_gates(self):
        notebook = json.loads(next((WORKSHOP / "notebooks").glob("Notebook_04_*.ipynb")).read_text(encoding="utf-8"))
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
        steps = "\n".join(path.read_text(encoding="utf-8") for path in self.chapter.glob("*.md"))
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

    def test_integrity_commands_preserve_inventory_and_isolate_generation(self):
        ja_blocks = require_integrity_exit_guards(self.integrity_text)
        block = ja_blocks[1]
        for marker in ("sys.version_info[:2] == (3, 13)", "git status --porcelain",
                       "Use a clean pinned checkout", "git archive --format=zip --output=$Archive HEAD",
                       "Expand-Archive -LiteralPath $Archive -DestinationPath $Source",
                       "$BeforeInventory", "$AfterInventory", "Push-Location -LiteralPath $Source",
                       "hashlib.sha256(p.read_bytes()).hexdigest()",
                       "json.dumps(files,sort_keys=True,indent=2),encoding='utf-8'",
                       "for p in sorted(before.keys()|after.keys()) if before.get(p)!=after.get(p)",
                       "finally {", "Pop-Location", "$PreviousGitDir = $env:GIT_DIR",
                       "$PreviousGitWorkTree = $env:GIT_WORK_TREE",
                       "$env:GIT_DIR = $PreviousGitDir", "$env:GIT_WORK_TREE = $PreviousGitWorkTree",
                       "if ($null -eq $PreviousGitDir) { Remove-Item Env:GIT_DIR -ErrorAction SilentlyContinue }",
                       "if ($null -eq $PreviousGitWorkTree) { Remove-Item Env:GIT_WORK_TREE -ErrorAction SilentlyContinue }"):
            self.assertIn(marker, block)
        self.assertLess(block.index("git archive --format=zip"), block.index("Expand-Archive"))
        self.assertLess(block.index("Expand-Archive"), block.index("python -c $Inventory $Source $BeforeInventory"))
        self.assertLess(block.index("python -c $Inventory $Source $BeforeInventory"), block.index("Push-Location"))
        self.assertLess(block.index("Push-Location"), block.index("python -B ./tools/provisioning/build_preview30.py"))
        self.assertLess(block.index("python -B ./tools/provisioning/build_preview30.py"),
                        block.index("python -c $Inventory $Source $AfterInventory"))
        self.assertLess(block.index("python -c $Inventory $Source $AfterInventory"),
                        block.index("python -c $Compare $BeforeInventory $AfterInventory"))
        self.assertIn('if ($LASTEXITCODE -eq 1) { throw "Current generation differs from accepted bytes; record the hashes and stop" }', block)
        self.assertIn('if ($LASTEXITCODE -ne 0) { throw "File inventory comparison failed" }', block)
        cleanup = block[block.index("finally {"):]
        self.assertLess(cleanup.index("$env:GIT_DIR = $PreviousGitDir"), cleanup.index("Pop-Location"))
        self.assertLess(cleanup.index("$env:GIT_WORK_TREE = $PreviousGitWorkTree"), cleanup.index("Pop-Location"))
        self.assertNotIn("Test-OntologyCardinality.ps1", block)
        self.assertNotIn("reseal_runtime.py", block)
        self.assertIn("生成した出力は使いません", self.integrity_text)
        self.assertIn("生成物を配置元へ戻したり、配布・配置に使ったりしません", self.integrity_text)
        self.assertIn("do not use generated output", self.integrity_text)
        self.assertIn("generated files must not be copied back, distributed or deployed", self.integrity_text)
        self.assertIn("Fabricの認証・実行・回答精度の確認とは別です", self.integrity_text)
        self.assertIn("separate from Fabric authentication, execution and answer-quality verification", self.integrity_text)
        mutations = (
            (
                "inverse exit condition",
                "python -B ./tools/provisioning/build_preview30.py",
                'if ($LASTEXITCODE -ne 0) { throw "Current source generation failed; do not use this copy" }',
                'if ($LASTEXITCODE -eq 0) { throw "Current source generation failed; do not use this copy" }',
            ),
            (
                "non-throw exit action",
                "python -B ./tools/provisioning/build_preview30.py",
                'if ($LASTEXITCODE -ne 0) { throw "Current source generation failed; do not use this copy" }',
                'if ($LASTEXITCODE -ne 0) { Write-Output "Current source generation failed; do not use this copy" }',
            ),
            (
                "removed ontology checker",
                "Test-IncrementConsistency.ps1",
                "python ./tools/provisioning/check_current_ontology.py",
                "",
            ),
            (
                "removed inventory-difference stop",
                "python -B ./tools/provisioning/build_preview30.py",
                'if ($LASTEXITCODE -eq 1) { throw "Current generation differs from accepted bytes; record the hashes and stop" }',
                "",
            ),
        )
        for label, token, old, new in mutations:
            with self.subTest(mutation=label):
                mutated = mutate_canonical_powershell(self.integrity_text, token, old, new)
                with self.assertRaises(AssertionError):
                    require_integrity_exit_guards(mutated)


if __name__ == "__main__":
    unittest.main()
