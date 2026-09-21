# Data Agent reference contracts

## 日本語

このディレクトリーは、Notebook 04 の **オプトイン参照構成**を再構築するための
SQL・KQL・Ontology 変換・ソースメタデータを保守します。
過去の候補コンパイラー、比較プロファイル、作業履歴は配布対象ではありません。
構造検証や再構築の成功は、ネイティブ回答の品質合格を意味しません。
参照 GLOBAL の `candidate` 状態も、完全評価の合格を示すものではありません。

| ファイル・ディレクトリー | 用途 |
|---|---|
| `reference-models/` | 6 SQL オブジェクトと依存順序、native カタログ照合、30 列の trace スキーマ |
| `operational-functions/` | 承認済み MV の raw 合計、自治体首位、file/run 集計を返す KQL 関数 |
| `path_ontology.py` | 正規テンプレートのキー・15 関係・contextualization を保持する経路用変換 |
| `source-contract/` | SHA-256 固定のソース指示、説明、列・引数インターフェイス |
| `tests/` | SQL の粒度・入力検証、KQL の読み取り範囲、Ontology 構造・安全な出力の回帰検証 |

### Runtime との接続

[`reference_assets.py`](../provisioning/reference_assets.py) は上記のローカル入力から
[`bundle/ai-reference`](../../workshop/v2.7.0/provisioning/bundle/ai-reference/) を生成します。
`source-contract/contract.json` は必要なソース・オブジェクト説明と指示ハッシュだけを持ち、
実環境の ID、基線 snapshot、評価結果、過去のプロファイルを参照しません。
指示本文は配布済みのバイトを保持します。列スキーマは選択設定を兼ねません。
現在の選択範囲は `reference_assets.py` と runtime の契約で管理します。

GLOBAL はこのディレクトリーから生成しません。教材の全体指示は
[`workshop/v2.7.0/data-agent/agent-instructions.txt`](../../workshop/v2.7.0/data-agent/agent-instructions.txt)、
参照構成の全体指示と宣言状態は上記 bundle の `global-instructions.txt` と
`global-profile.json` が保持します。教材の Word/HTML も公開用 bundle を入力とし、
過去の実験プロファイルは必要ありません。再構築手順は
[`tools/provisioning/README.md`](../provisioning/README.md) を参照してください。

### 保持する境界

- SQL は `MunicipalityStatic`、`MunicipalityById`、`DonationTraceById` を直接選択します。
  他の 3 オブジェクトは内部依存・参照定義として残し、元の 11 テーブル・88 列も保持します。
- Trace は寄付 × 登録 Supplier の粒度です。繰り返される寄付額を合計してはいけません。
- Runtime が配置・選択する KQL 関数は `AgentRawObservationTotals`、
  `AgentMunicipalityLeaders`、`AgentFileRunSummary` の 3 本です。
  `AgentObservationLeaders.kql` は既存環境の互換性照合用としてのみ残し、
  新規配置・選択の対象にはしません。raw 観測集計は一意イベント数ではありません。
- SQL/KQL の native 型と、Data Agent のシリアライズされたメタデータは別の証拠です。
  空の型情報や存在しない選択ノードを補ってはいけません。
- この構成は明示的な opt-in が必要です。既定の教材、配布用の固定ファイル、Core の昇格を変更しません。
  実環境の定義、認証情報、回答ログ、評価の正解は Git に保存しないでください。

ローカル検証（認証・サービス接続なし）:

```powershell
python -B -m unittest discover -s .\tools\data-agent\tests -p "test_*.py"
python -B -m unittest discover -s .\tools\provisioning -p "test_reference_*.py"
```

SQL の plan-only 操作と適用時の停止条件は
[`reference-models/README.md`](reference-models/README.md) を参照してください。

`path_ontology.py` は名称や「private candidate」という説明にかかわらず、
公開 bundle の `reference_assets.py` が使う汎用のローカル変換依存です。
削除すると参照構成の再構築が壊れるため、コード・検査を保持します。
実環境の候補定義や評価結果を同梱するものではありません。

### ネイティブ評価 / Native evaluator — private evidence only

公開済み Data Agent の実回答収集には `--transport mcp` を使います。
既存の `az login`、`requests`、`azure-identity` を利用でき、ブラウザーや ODBC Driver、
大きな Fabric SDK は不要です。質問・正解・応答・レビューは Git の外の非公開ルートへ保存します。
各問で新しい MCP セッションを使い、質問は 1 回だけ送ります。

MCP で取得できる回答本文の条件判定と、内部 SQL/KQL/GQL などを含む厳密な受入は別です。
観測できない実行証跡を補完せず、厳密な合格 0 件を「事実回答の正答率 0%」と表現しません。
元の 10 問・84 条件は変更しません。構成変更後は新しい campaign を凍結して全問を再評価し、
改善に使用した held-out は回帰用と区別します。以下に前提・コマンド・判定方法を示します。

`evaluate_native.py` now supports the **public Fabric MCP endpoint** through
`native_mcp.py`. This transport has been exercised against published agents.
It requires only `requests` and `azure-identity`, reuses `az login` by default,
and needs **no browser session, system ODBC driver, full Fabric SDK, regional
workload host or capacity ID**. It does not authenticate or submit anything
during `doctor`, `freeze`, `plan`, `report`, or local tests.

**MCP is an answer-only evidence surface.** The observed native reply exposes
answer text, not the internal executed SQL/KQL/GQL or their result rows.
Neither a JSON-RPC ID nor an MCP session ID is a backend conversation ID.
The evaluator creates a fresh HTTP client/MCP session for each exact question,
but does not manufacture backend identity or claim unobservable execution.
No request redirects or automatic retries are permitted; an uncertain question
submission is not resent.

Consequently:

- `run` success means **capture completed**, not answer-quality acceptance.
- `report` writes its report but exits with code **2** when acceptance is
  blocked or fails. This is not a reason to resend questions or overwrite an
  existing report; inspect its condition counts and gate errors.
- MCP reports separate reviewed **condition PASS/FAIL/N/A** from strict
  whole-question acceptance. Unobservable execution keeps strict acceptance
  blocked; **zero strict passes is not 0% factual accuracy**.
- Native-final content conditions require an explicit human judgment,
  `basis: "native_answer"`, a reason and a final-text JSON pointer, for example
  `/result/content/0/text`. New review files default to `UNCLEAR` and
  `basis: "unreviewed"`; UNCLEAR is FAIL.
- A condition requiring native execution/results cannot PASS from an answer
  table, a source label or SQL-looking text. Known original execution
  requirements are protected. For a custom private rubric, mark such conditions
  with `"required_evidence": "native_execution"` **before freezing** the suite.
  A reviewer can also mark `basis: "native_execution"`; MCP cannot prove it.
- The original T03 clarification branch retains only its three numeric-only
  N/A conditions. Observability remains a separate failed gate.

All deployment JSON, exact prompts, CSV-derived keys, requests, replies,
snapshots and reviews must be under an **absolute private root outside Git**.
Do not point this at a repository directory, including an ignored directory.
Raw files and campaign plans are exclusive-create and hash-checked. Create new
campaign/output names for new configurations; never overwrite previous runs.
Every resolved input/output path is also checked for nested Git checkouts,
including worktrees created after the private store was initialized. Reporting
rechecks the frozen deployment/data fingerprint; missing or changed evidence
invalidates the affected batches and case judgments. SDK/Responses capture saves
the received request and reply before validating the wire request, so a rejected
request cannot discard an already received native answer.

Example private deployment JSON (real values belong only in private storage):

```json
{
  "configurations": [{
    "label": "candidate",
    "workspace_id": "<workspace ID>",
    "data_agent_id": "<published agent ID>",
    "stage": "production",
    "transport": "mcp",
    "data_fingerprint_file": "deployment/data-fingerprint.json",
    "original_repeats": 2,
    "heldout_repeats": 1
  }]
}
```

The public MCP route supports **published/production** agents; `sandbox` is
rejected rather than silently replaced. Freeze transport selection in the
deployment JSON or with `plan --transport mcp`; there is no run-time transport
override. `--credential default` selects `DefaultAzureCredential` instead of
the default Azure CLI credential.

```powershell
$env:EVALUATION_PRIVATE_ROOT = '<absolute private evidence directory outside Git>'

# Offline imports only; no token acquisition or endpoint call:
python -B .\tools\data-agent\evaluate_native.py doctor --transport mcp

# One-time extraction of the unchanged original 10/84 into private storage.
# Supply a separately prepared, private unseen suite; do not overwrite a frozen one:
python -B .\tools\data-agent\evaluate_native.py freeze `
  --held-out-input unseen-specification.json

# Freeze all configurations, suites and repetition counts before submissions:
python -B .\tools\data-agent\evaluate_native.py plan `
  --name candidate-next --deployment updated-deployment.json --transport mcp `
  --repeats 2 --held-out-repeats 1

# ONLINE: only after explicit authorization and verified data/configuration readiness:
python -B .\tools\data-agent\evaluate_native.py run `
  --plan campaigns\candidate-next\plan.json --configuration candidate `
  --suite original --repeat 1 --credential azure-cli `
  --allow-submit-native-questions

# Review the private per-case review.json files; then create a new report file:
python -B .\tools\data-agent\evaluate_native.py report `
  --plan campaigns\candidate-next\plan.json --out reports\review-001.json
```

Repeat only the predeclared slots (including the separately labelled held-out
suite). Any held-out material used for improvement becomes regression material.
Run requests are bound to the frozen harness hash; read-only reporting of older
plans is allowed and discloses a harness-version mismatch without modifying
the historical evidence.

### Optional Responses evidence

`responses-http` is an optional SDK-aligned workload path, not a stable public
Fabric REST contract. Supply an **observed** HTTPS workload origin from the
Fabric runtime's `synapse.ml.fabric.service_discovery.get_fabric_env_config()`;
do not guess one from a capacity region or substitute a tenant metadata host.
The client accepts the existing `*.analysis.windows.net` form and the observed
capacity-identified `*.pbidedicated.windows.net` form. A dedicated origin must
match the explicitly supplied capacity ID. Paths, credentials, ports and
non-Microsoft origin overrides are rejected.

A read-only retrieval against the observed dedicated origin recovered an
existing Responses result with real conversation/response IDs and paired
source calls/results. This does not recover an unidentified old MCP run or
establish compatibility for every tenant. Qualify the chosen stage/runtime and
preserve the actual bodies before a new comparison.

The optional server diagnostics GET can return the specific HTTP 403
`Data Agent diagnostics feature is not enabled.` The capture retains that exact
native error and a correlated receipt as `diagnostics-unavailable.*`, records
`diagnostics_status: "feature_unavailable"`, and does not submit the question
again. Other diagnostic errors remain capture blockers. This narrow feature
gate does **not** turn a source failure into success or waive missing calls,
results, final answers, source-scope review or rubric conditions. Execution
evidence must still come from the unchanged native response; a feature-gate
receipt proves no query. Native Markdown-formatted result strings also do not
automatically meet the strict grader's structured-result requirement.

#### Explicit same-conversation confirmation turns

The Python `capture_case` API accepts the opt-in keyword `previous_record_path`
for SDK/Responses confirmation workflows. Omit it for a fresh conversation;
the original-suite/campaign CLI and MCP behavior are unchanged. Reuse the same
native client, frozen definition digest and `used_conversations` set:

```python
used_conversations = set()
first = capture_case(
    store, "confirmation/turn-1", first_case, client, read_definition,
    frozen_definition_sha256, used_conversations, 120,
)
second = capture_case(
    store, "confirmation/turn-2", confirmation_case, client, read_definition,
    frozen_definition_sha256, used_conversations, 120,
    previous_record_path="confirmation/turn-1/record.json",
)
verify_record(store, second)  # Also verifies the predecessor chain, iteratively.
```

Each case's question is submitted unchanged, once, with no added history,
instructions, model override or `previous_response_id` request parameter.
Follow-ups reuse the recorded native conversation, set `fresh_conversation:
false`, increment `turn_index`, and bind `previous_record` to the predecessor's
path, exact file SHA-256 and terminal response ID. They never create or invent
a new-conversation receipt. Earlier fresh captures without turn metadata are
valid roots when their original evidence passes all checks.

Before POST, `submission-intent.json` and an exclusive
`continuation-claim.json` beside the predecessor durably bind the next turn.
A predecessor can be consumed only once: an ambiguous/interrupted send cannot
be replayed or bypassed by choosing another slot or an older turn. All evidence
still belongs in private storage outside Git.

Continuation requires a registered conversation, intact raw evidence, one
submission, an actual completed native response and unchanged before/after
definitions matching the frozen digest. Failures, cancellations, unfinished
runs, platform content blocks, diagnostic errors other than the documented
feature403, or tampering block submission. A completed final answer with
recovered internal tool/planning errors may continue while retaining
`evidence_incomplete`; no quality gate is waived.

`response.status` is the native runtime state; record `status` describes
capture/evidence, **not whether a confirmation was answered correctly**.
Reviews remain ungraded. Grade dialogue semantics separately; the original
fresh-question campaign grader is not a multi-turn acceptance grader.

The UI's **Export Diagnostic File** is separate from this server GET. A successful
UI export can contain an empty or different conversation. Match the artifact,
stage, runtime, real conversation/response IDs and execution timestamps; never
use JSON-RPC IDs as backend identity. An inactive capacity can make a previously
observed workload origin unavailable while the public item API still lists the
agent. Do not recreate the item or resume a paid capacity automatically.

`sdk` remains unqualified in this environment. Imports and passing local tests
alone never establish live connectivity, trace completeness or answer accuracy.
Historical investigation records are not participant materials. Follow the
[current response checks](../../docs/single-agent-workshop.md).

### Public standard and separate private inputs

The standard ten questions/84 conditions are already public in the current guide.
`native_evaluation.py` extracts them unchanged from the guide builder and packaged
synthetic CSVs; `freeze` without `--held-out-input` writes only that standard suite
to a new private root. No internal problem pack is needed for the guide's manual
standard evaluation or that offline extraction.

The existing campaign `plan` contract additionally requires a separately frozen,
nonempty custom held-out suite. Prepare your own private specification; no internal
questions, keys or past results are supplied or fetched. Use a new private root
for the combined freeze rather than overwriting the standard-only freeze.
See [bilingual public onboarding](../../docs/public-onboarding/README.md).

Experimental instruction packages and their package-only tests are not part of
this current distribution. The generic `path_ontology.py` transformer remains:
`reference_assets.py` needs it to reproduce the sealed reference bundle. Its
private-output safeguards and all current runtime/evaluation tests remain intact.

A completed Responses envelope can contain the same service content-block
message as MCP. Both paths now identify that known block as a native failure,
not a business refusal or correct answer; the raw message is retained.

## English

These maintained sources rebuild the opt-in reference runtime without historical
candidate profiles or compiler scripts. `reference_assets.py` packages the SQL,
KQL, path-only Ontology template, and source-contract metadata deterministically.
Source instruction bytes are hash-pinned; GLOBAL remains independently bundled
with its explicit status. Native schemas and serialized Agent metadata stay
separate. Internal SQL dependencies and the unselected legacy KQL compatibility
function are intentionally retained. Structural checks do not establish complete
native answer-quality acceptance or promote any configuration to Core.
