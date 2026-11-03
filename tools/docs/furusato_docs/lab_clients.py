"""Current client entrypoints and source-integrity checks for the participant Lab."""
from __future__ import annotations

from furusato_html.model import Block, Text
from .participant30 import add_section, paragraph, bullet_list, text_table


def code(text, language):
    return Block("code", {"text": text, "language": Text(language, language)})


def append_sections(chapter):
    add_section(chapter, "10", ("支援ツールを選び、同じ配置手順を使う", "Choose a client and use the same deployment procedure"), [
        paragraph((
            "どの支援ツールでも、この Lab の24.4〜24.9と同じ配布ファイル、配置先、計画、承認記録を使います。まず読み取りと計画から始めます。クライアントがシェルやFabric操作を提供しない場合は、手順を確認したうえで、自分の認証済み端末またはFabricポータルで実行します。別のNotebookや設定を記憶から生成させません。",
            "Every client uses the same distributed files, scope, plan and approval records from 24.4–24.9. Start with reading and planning. If the client provides no shell or Fabric operations, review the procedure and execute it from your authenticated terminal or Fabric portal. Do not ask the client to invent a different Notebook or configuration from memory.")),
        text_table([("クライアント", "Client"), ("使い方", "How to use it")], [
            ["GitHub Copilot Desktop / Copilot app", ("ローカルの作業フォルダーを開き、手順と計画を確認します。設定済みのツールで実行できる範囲を確認し、利用できない操作は認証済み端末やポータルで行います。", "Open the local project and review the procedure and plan. Check the configured tools' capabilities; use your authenticated terminal or portal for unavailable operations.")],
            ["GitHub Copilot CLI", ("--helpで現在のオプションを確認し、--planで計画から始めます。承認前の作成や実行を指示しません。", "Check current options with --help and start with --plan. Do not request creation or execution before approval.")],
            ["Claude Code", ("--helpで現在のオプションを確認し、--permission-mode planで読み取りと計画から始めます。", "Check current options with --help and begin with reading and planning through --permission-mode plan.")],
            ["OpenAI Codex", ("--helpで現在のオプションを確認し、read-onlyのsandboxとon-requestの承認設定で計画します。必要な操作だけを、利用環境の承認方法で許可します。", "Check current options with --help and plan with a read-only sandbox and on-request approval. Permit only the required operations through the environment's approval mechanism.")],
            ["Scout", ("この項目はMicrosoft Scout (Frontier)を利用する場合に限ります。ScoutOSなど別製品の手順と混同しません。利用できる接続先と操作を画面で確認し、ローカルシェルがあるとは仮定しません。", "This applies only if using Microsoft Scout (Frontier). Do not confuse it with another product such as ScoutOS. Inspect available connections and operations; do not assume a local shell.")],
            ["Microsoft 365 Copilot Cowork", ("利用できるFabric・Power BI接続と操作範囲を確認します。手順整理を依頼できてもローカルシェルや配置権限があるとは仮定せず、必要なコマンドは認証済み端末で実行します。", "Inspect available Fabric/Power BI connections and supported operations. Procedure assistance does not establish a local shell or deployment permission; run required commands in your authenticated terminal.")],
        ], ("利用するクライアントの入口", "Client entrypoints")),
        paragraph(("ローカルCLIを利用する場合の計画開始例です。導入済みのバージョンが各オプションを提供することを--helpで確認してから実行します。", "These examples start local CLI planning. Before use, confirm with --help that your installed version provides each option.")),
        code('copilot --plan --prompt "Read Lab/README.md and Chapter 24. Inspect the source and propose the scoped deployment plan. Do not create or run resources yet."\nclaude --permission-mode plan "Read Lab/README.md and Chapter 24. Inspect the source and propose the scoped deployment plan. Do not create or run resources yet."\ncodex --sandbox read-only --ask-for-approval on-request "Read Lab/README.md and Chapter 24. Inspect the source and propose the scoped deployment plan. Do not create or run resources yet."', "PowerShell"),
        paragraph(("GitHubのリポジトリ閲覧、支援ツールへのログイン、Fabricの本人認証は別です。24.4のAzure CLI認証をコマンド実行環境で行い、MFAは通常の本人確認で完了します。トークンやCookieを別の端末からコピーしません。Fabric MCPは追加の任意経路であり、利用する場合も対応する認証・権限・操作を確認します。", "Repository access, client login and Fabric identity authentication are separate. Complete the Azure CLI authentication in 24.4 in the command execution environment, including normal MFA. Never copy tokens or cookies from another machine. Fabric MCP is an optional additional route; verify its authentication, permissions and supported operations separately.")),
        paragraph(("基本の配置経路は24.4〜24.9のCLIです。配布済みNotebook 04を使う場合は、同じscope・resource-plan・write-gate・記録先を設定します。プレビューの初期値は次のとおりです。パスと表示名を自分の実値に置き換え、パラメーター以外のセルや埋め込みパッケージは編集しません。", "The primary deployment route is the CLI in 24.4–24.9. If using distributed Notebook 04, set the same scope, resource plan, write gate and evidence directory. The preview values below use placeholders for your actual paths and display name. Edit the parameters only, not other code cells or the embedded package.")),
        code('PARTICIPANT_ID = "001"\nENVIRONMENT = "dev"\nEXPECTED_WORKSPACE_NAME = "<exact workspace display name>"\nSCOPE_FILE = "<private scope.json path>"\nPLAN_FILE = "<private resource-plan.json path>"\nWRITE_GATE_FILE = "<private write-gate.json path>"\nPRIVATE_EVIDENCE_DIR = "<private evidence directory>"\nACTION = "preflight"\nAPPLY_CHANGES = False\nALLOW_AUTOMATED_APPLY = False\nCONFIRMED_PLAN_SHA256 = ""\nRUN_NOTEBOOK01 = False', "Python"),
        bullet_list([
            ("プレビューで実際の配置先、競合、作成対象とplanSha256を確認し、24.5の計画に対応する承認記録を使います。適用時だけAPPLY_CHANGESをTrueにし、CONFIRMED_PLAN_SHA256に実際の値を設定します。Jobs APIによる自動適用を承認した場合だけALLOW_AUTOMATED_APPLYも有効にします。", "Inspect the actual destination, conflicts, resource list and planSha256 in preview and use the matching approval record from 24.5. Set APPLY_CHANGES=True and the actual CONFIRMED_PLAN_SHA256 only for apply. Enable ALLOW_AUTOMATED_APPLY only for explicitly authorized Jobs API automation."),
            ("成功したNotebook 01や増分取り込みを再実行しません。CLIで完了した工程をNotebookで重ねません。FileCreatedの設定、実配送、Copy結果、KQL件数、停止状態は24.7と9〜10章でそれぞれ確かめます。", "Do not rerun a successful Notebook 01 or increment ingestion, or repeat a CLI-completed stage through a Notebook. Check FileCreated configuration, actual delivery, Copy results, KQL counts and stopped state separately with 24.7 and Chapters 9–10."),
        ]),
        paragraph(("各クライアントの公式資料", "Official documentation for each client")),
        bullet_list([Text(url, url) for url in (
            "https://docs.github.com/en/copilot/concepts/agents/about-copilot-cli",
            "https://code.claude.com/docs/en/cli-reference",
            "https://developers.openai.com/codex/cli/reference/",
            "https://learn.microsoft.com/en-us/microsoft-scout/overview",
            "https://docs.scoutos.com/introduction",
            "https://learn.microsoft.com/en-us/microsoft-365/copilot/cowork/get-started",
            "https://learn.microsoft.com/en-us/microsoft-365/copilot/cowork/cowork-faq",
            "https://learn.microsoft.com/en-us/fabric/iq/connectors/cowork-overview",
        )]),
    ])
    add_section(chapter, "11", ("配布データと実行資産を確認する", "Verify distributed data and runtime assets"), [
        paragraph(("この検査には PowerShell 7（pwsh）が必要です。Windows では未導入の場合、24.4の環境準備で導入します。Linux では Microsoft の公式インストール手順に従って導入してから実行します。", "This check requires PowerShell 7 (pwsh). On Windows, install it during the Chapter 24.4 environment setup if needed. On Linux, follow Microsoft's official installation instructions before running it: https://learn.microsoft.com/powershell/scripting/install/installing-powershell-on-linux")),
        paragraph(("ZIPの外部SHA-256照合に加えて、次の読み取り専用コマンドで現在版のCSVとOntologyをオフライン検証できます。リポジトリまたはZIP展開後のsourceディレクトリを起点に実行します。データ検査には現在版のdataパスを明示し、旧版の既定値を使いません。Python検査は現在の公開ソースマニフェストの整合性とGeneration 2定義・契約の実バイトを確認し、seed CSVからノード・エッジ・参加数を再計算します。どちらもFabricへ接続・書き込みません。旧版スクリプトの全検査との同等性や、Fabric上のOntology/Graph実行・配置を証明するものではありません。", "Alongside the external ZIP SHA-256 check, these read-only commands validate the current edition's CSVs and ontology offline. Run them from the repository root or the extracted ZIP's source directory. The data check explicitly selects the current data path instead of using the legacy default. The Python check validates the current publication source manifest and Generation 2 definition/contract bytes, then recomputes node, edge and participation counts from the seed CSVs. Neither connects to or writes to Fabric. This is not full parity with every legacy-script check and does not prove a Fabric Ontology/Graph runtime or deployment.")),
        code('pwsh ./tools/data/Test-IncrementConsistency.ps1 -DataRoot ./workshop/v3.0.0-preview/data\nif ($LASTEXITCODE -ne 0) { throw "Dataset check failed" }\npython ./tools/provisioning/check_current_ontology.py\nif ($LASTEXITCODE -ne 0) { throw "Current ontology check failed" }', "PowerShell"),
        paragraph(("ソースの再現性を調べる場合だけ、コミットを固定したクリーンなcheckoutとPython 3.13を使い、次のコマンドで現在版を別コピーに展開して生成前後の全ファイルをSHA-256で比較します。抽出先に .git は作らず、生成器の保護基線検査に限り、固定したcheckoutのGitメタデータを一時的に参照します。旧版のreseal_runtime.py --checkはworkshop/v2.7.0だけを検査し、現在版の証明にはなりません。現在版のバイト単位の再現性は未確認です。Python 3.13の使用だけでバイト一致が保証されるわけではありません。差分があれば一覧を記録して停止し、生成した出力は使いません。配置元を変更せず、生成物を配置元へ戻したり、配布・配置に使ったりしません。CSV・NotebookのSHAだけを確認する参加者は、この再生成検査を行う必要はありません。", "Only when checking source regeneration, use a clean checkout pinned to a commit and Python 3.13. The command below extracts that commit into a separate copy and compares SHA-256 inventories of all files before and after generation. The extracted copy has no .git directory; for the builder's protected-baseline check only, it temporarily refers to Git metadata from the pinned checkout. The legacy reseal_runtime.py --check examines workshop/v2.7.0 only; it does not prove the current edition. Current byte-for-byte regeneration is not qualified, and using Python 3.13 alone does not guarantee byte identity. If files differ, record the list and stop; do not use generated output. The source checkout is not modified, and generated files must not be copied back, distributed or deployed. Participants who only need CSV/Notebook hashes do not need this regeneration check.")),
        code('''$ErrorActionPreference = "Stop"
python -c "import sys; assert sys.version_info[:2] == (3, 13)"
if ($LASTEXITCODE -ne 0) { throw "Use Python 3.13 for the current generator compatibility check; this alone does not guarantee byte identity" }
$Dirty = git status --porcelain
if ($LASTEXITCODE -ne 0) { throw "Git status failed" }
if ($Dirty) { throw "Use a clean pinned checkout; preserve existing edits" }
$GitDir = (git rev-parse --absolute-git-dir).Trim()
if ($LASTEXITCODE -ne 0) { throw "Could not locate the pinned checkout's Git metadata" }
$CheckRoot = Join-Path $env:USERPROFILE ("Furusato-current-generation-check-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $CheckRoot | Out-Null
$Archive = Join-Path $CheckRoot "source.zip"
$Source = Join-Path $CheckRoot "source"
$BeforeInventory = Join-Path $CheckRoot "before.json"
$AfterInventory = Join-Path $CheckRoot "after.json"
$Inventory = "import hashlib,json,pathlib,sys; root=pathlib.Path(sys.argv[1]); out=pathlib.Path(sys.argv[2]); files={p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}; out.write_text(json.dumps(files,sort_keys=True,indent=2),encoding='utf-8')"
$Compare = "import json,pathlib,sys; before=json.loads(pathlib.Path(sys.argv[1]).read_text(encoding='utf-8')); after=json.loads(pathlib.Path(sys.argv[2]).read_text(encoding='utf-8')); diff=[{'path':p,'before':before.get(p),'after':after.get(p)} for p in sorted(before.keys()|after.keys()) if before.get(p)!=after.get(p)]; print(json.dumps(diff,indent=2)); raise SystemExit(1 if diff else 0)"
git archive --format=zip --output=$Archive HEAD
if ($LASTEXITCODE -ne 0) { throw "Git archive failed" }
Expand-Archive -LiteralPath $Archive -DestinationPath $Source
python -c $Inventory $Source $BeforeInventory
if ($LASTEXITCODE -ne 0) { throw "Could not hash the accepted archive" }
Write-Output ("Private check evidence: " + $CheckRoot)
Push-Location -LiteralPath $Source
$PreviousGitDir = $env:GIT_DIR
$PreviousGitWorkTree = $env:GIT_WORK_TREE
$env:GIT_DIR = $GitDir
$env:GIT_WORK_TREE = $Source
try {
    python -B ./tools/provisioning/build_preview30.py
    if ($LASTEXITCODE -ne 0) { throw "Current source generation failed; do not use this copy" }
    python -c $Inventory $Source $AfterInventory
    if ($LASTEXITCODE -ne 0) { throw "Could not hash generated files" }
    python -c $Compare $BeforeInventory $AfterInventory
    if ($LASTEXITCODE -eq 1) { throw "Current generation differs from accepted bytes; record the hashes and stop" }
    if ($LASTEXITCODE -ne 0) { throw "File inventory comparison failed" }
}
finally {
    if ($null -eq $PreviousGitDir) { Remove-Item Env:GIT_DIR -ErrorAction SilentlyContinue }
    else { $env:GIT_DIR = $PreviousGitDir }
    if ($null -eq $PreviousGitWorkTree) { Remove-Item Env:GIT_WORK_TREE -ErrorAction SilentlyContinue }
    else { $env:GIT_WORK_TREE = $PreviousGitWorkTree }
    Pop-Location
}''', "PowerShell"),
        paragraph(("検査後も配置元は元の固定コミットです。差分やエラーがあれば停止して記録し、生成した出力を使わずに原因を調べます。この検査はFabricの認証・実行・回答精度の確認とは別です。", "The original pinned commit remains the deployment source after the check. Stop and record any diff or error, and diagnose it without using generated output. This check is separate from Fabric authentication, execution and answer-quality verification.")),
    ])
