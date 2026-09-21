# 公開版のデプロイと評価 / Public deployment and evaluation

[README](../../README.md) · [Security](../../SECURITY.md) ·
[Native evaluator](../../tools/data-agent/README.md)

## 日本語

### 公開版で保持するもの

`v2.7.0 / unified-20260914` の Word／HTML、合成 CSV、封印済み Notebook 01–05、
bundle・契約、参照／統合プロファイル、再構築ソース、標準 **10問・84条件**と汎用評価エンジンを保持します。
元の教材を短縮した評価や、内部の追加問題・正解・過去の回答ログへの置換は行いません。
公開版のローカル検査は Fabric の新規デプロイや実回答の検証ではなく、全問正答・常時成功を保証しません。

### デプロイ

1. [元と同じ URL](https://github.com/yang-jiayi/furusato-fabric-workshop) から新しく clone し、
   取得した公開側のコミットを固定します。旧 Private checkout を pull／merge／mirror しません。
   新しい GitHub repository ID に Secrets・Environments・Actions の履歴や認証設定は引き継がれません。
   必要な GitHub 連携、AI クライアント、Azure CLI／Fabric 認証は別々に再確認・再承認してください。
   Windows では PBIR の階層が深いため、clone 先に短いパスを選んでください。
2. dev/test/prod ごとに対象 Workspace・空 Folder・未使用 PID `001`–`999`・接続先・
   非公開の設定／証跡ルートを明示します。ID・資格情報は Git 外で管理し、配布 Notebook に固定しません。
   稼働中の capacity、権限、Ontology／Data Agent の提供条件を確認します。
   統合 SQL ヘルパーは Fabric Notebook driver 上の `pyodbc` と ODBC Driver 18 が必要です。
3. [Word](../Fabric_IQ_Ontology_Workshop_Furusato_Participant_v2.7.0_unified-20260914.docx)と
   [HTML](../furusato-workshop-v2-7-0-complete_unified-20260914.html)を同じフォルダーに置き、
   [RELEASE_SHA256SUMS.txt](../../RELEASE_SHA256SUMS.txt) と
   [配布物の検証](../../README.md#deployment-integrity-checks)で照合します。
   `reseal_runtime.py --check` は書き換えを伴うため**捨てるためのコピー内だけ**で実行し、
   差分が出たコピーを配布・デプロイしません。
4. [README の共通実行経路](../../README.md#ツール別のデプロイ手順)に従います。
   Notebook 04 のコース設定は `ENABLE_UNIFIED_DATA_AGENT=True`、
   `ENABLE_AI_REFERENCE_ARCHITECTURE=False`。配布ファイルの既定 False は変更していません。
   `APPLY_CHANGES=False` の preview → 対象・`PLAN_SHA256` の確認 → 明示承認 → apply の順です。
   Jobs API の場合は `ALLOW_AUTOMATED_APPLY` と `EXPECTED_WORKSPACE_NAME` も明示します。
   既存 Item を上書きせず、FileCreated・各増分・Graph・Notebook 05／Power BI を別々に確認します。
   トリガー不達を無言で手動取り込みへ置換したり、成功済みの取り込みを再実行したりしません。

### 標準評価と追加評価

- **標準**：現行ガイドの元の10問・84条件をそのまま使い、1問1会話で記録します。
  標準だけの手動評価と下記のオフライン抽出に内部問題集は不要です。CI 演習は別枠です。
- **自動 campaign**：既存 `plan` は標準に加えて、利用者が用意した非空の private held-out suite を必要とします。
  追加入力は標準の代わりではありません。内部問題集は公開版に含まれず、自動取得もしません。
  `schema_version: 1`、`kind: "heldout"`、固有 ID・質問・判定条件・必要な query language を持つ
  `cases` を作り、実行証拠が必要な条件は凍結前に `required_evidence: "native_execution"` とします。
  改善に使用した追加問題は以後「未見」ではなく回帰用です。
- **保存先**：設定・問題・正解・生応答・レビューは、無視設定のあるディレクトリーも含め、
  すべての Git checkout の外の絶対パスへ保存します。凍結済みファイルは上書きできません。
- **承認**：`doctor`・`freeze`・`plan` は認証取得／ネットワーク送信をしません。
  実質問の送信は対象・構成・反復回数の確認と別承認後だけで、
  `--allow-submit-native-questions` が必須です。失敗を成功するまで再送しません。

## English

### What the public distribution retains

The `v2.7.0 / unified-20260914` Word/HTML pair, synthetic CSVs, sealed Notebooks 01–05,
bundle/contracts, reference/unified profiles, rebuild sources, standard **10 questions /
84 conditions**, and generic evaluator remain available. No shortened rubric or
internal extra question/answer/result pack replaces the standard. Local packaging
checks are not a fresh live Fabric deployment or answer-quality test and guarantee
neither universal execution success nor perfect answers.

### Deployment

1. Clone [the unchanged URL](https://github.com/yang-jiayi/furusato-fabric-workshop) afresh
   and pin the new public commit. Never pull/merge/mirror old private history into it.
   The new GitHub repository ID inherits no Secrets, Environments, Actions history
   or authentication settings. Separately recheck/reauthorize GitHub integrations,
   the AI client, and Azure CLI/Fabric authentication.
   On Windows, choose a short clone path because the PBIR directory hierarchy is deep.
2. Explicitly select separate dev/test/prod Workspace, empty Folder, unused PID
   `001`–`999`, connections and private configuration/evidence roots. Keep IDs and
   credentials outside Git, not hardcoded in distributed notebooks. Verify active
   capacity, permissions and feature availability. Unified SQL requires `pyodbc`
   and ODBC Driver 18 on the **Fabric Notebook driver**, not only your local PC.
3. Keep the [Word](../Fabric_IQ_Ontology_Workshop_Furusato_Participant_v2.7.0_unified-20260914.docx)
   and [HTML](../furusato-workshop-v2-7-0-complete_unified-20260914.html) together.
   Check [release hashes](../../RELEASE_SHA256SUMS.txt) and follow the
   [distribution checks](../../README.md#deployment-integrity-checks).
   `reseal_runtime.py --check` mutates files: run it **only in a disposable copy**.
   Never distribute/deploy a regenerated copy that differs from the approved payload.
4. Follow the [shared execution route](../../README.md#deployment-by-client).
   Explicitly select `ENABLE_UNIFIED_DATA_AGENT=True` and
   `ENABLE_AI_REFERENCE_ARCHITECTURE=False`; the distributed defaults remain False.
   Preview with `APPLY_CHANGES=False`, inspect target/`PLAN_SHA256`, obtain approval,
   then apply. Jobs API execution also requires explicit `ALLOW_AUTOMATED_APPLY`
   and `EXPECTED_WORKSPACE_NAME`. Do not overwrite mismatched existing Items.
   Verify FileCreated, each increment, Graph, Notebook 05 and Power BI separately.
   Never silently replace a failed trigger with manual ingestion or replay accepted data.

### Standard evaluation and private additions

- **Standard:** use the guide's original 10/84 verbatim, with a fresh conversation per
  question. Manual standard evaluation and offline extraction require no internal
  problem pack. Record CI exercises separately.
- **Automated campaign:** the unchanged `plan` contract additionally requires your
  own nonempty private held-out suite. It does not replace the original suite.
  No internal pack is shipped or fetched. Supply `schema_version: 1`, `kind: "heldout"`
  and `cases` with unique IDs, questions, conditions and required query languages.
  Mark execution-dependent conditions `required_evidence: "native_execution"` before
  freezing. Cases used for improvement become regression, not unseen, material.
- **Storage:** deployment configuration, prompts, keys, raw replies and reviews belong
  at an absolute private path outside **every** Git checkout, including ignored folders.
  Frozen files are exclusive-create; use new roots/campaign names, not overwrites.
- **Authorization:** `doctor`, `freeze` and `plan` acquire no token and make no network
  calls. Real submissions require separate approval after checking target/configuration/
  repetitions, plus `--allow-submit-native-questions`. Never retry until success.

## Commands / コマンド

Run from a fresh, pinned public checkout. Python 3.10+ is required; MCP `doctor`/online
capture need `requests` and `azure-identity`. Install missing dependencies in a local
environment only when needed. These two workflows use **different fresh private roots**.

標準だけのオフライン確認 / Standard-only offline check:

```powershell
$env:EVALUATION_PRIVATE_ROOT = '<new absolute private standard-evaluation root outside Git>'
python -B .\tools\data-agent\evaluate_native.py doctor --transport mcp
if ($LASTEXITCODE -ne 0) { throw 'Resolve local dependencies before proceeding' }
python -B .\tools\data-agent\evaluate_native.py freeze
if ($LASTEXITCODE -ne 0) { throw 'Standard freeze failed; preserve existing files' }
```

This extracts the unchanged guide/CSV-derived suite, not native answers or proof of
query execution. Review the current guide for manual evaluation. To use the existing
campaign runner, choose a **different new private root** and place your own
`custom-heldout.json`, `deployment.json` and verified data-fingerprint file under it.
The deployment JSON schema is in the [evaluator README](../../tools/data-agent/README.md).
For MCP, `stage: "production"` means the published Agent stage; it is **not** a substitute
for selecting/authorizing your dev/test/prod environment.

追加入力を使う campaign の凍結 / Offline campaign preparation with separate custom input:

```powershell
$env:EVALUATION_PRIVATE_ROOT = '<new absolute private campaign root outside Git>'
python -B .\tools\data-agent\evaluate_native.py freeze --held-out-input custom-heldout.json
if ($LASTEXITCODE -ne 0) { throw 'Suite freeze failed' }
python -B .\tools\data-agent\evaluate_native.py plan `
  --name public-course --deployment deployment.json --transport mcp `
  --repeats 2 --held-out-repeats 1
if ($LASTEXITCODE -ne 0) { throw 'Campaign plan failed; do not submit questions' }
```

**ONLINE — separate explicit approval required / 実送信は別途明示承認後のみ:**

```powershell
python -B .\tools\data-agent\evaluate_native.py run `
  --plan campaigns/public-course/plan.json --configuration <approved-configuration-label> `
  --suite original --repeat 1 --credential azure-cli --allow-submit-native-questions
```

Run only the predeclared slots, including the second original repeat and separately
labelled held-out slots. Review actual evidence, then use `report` with a **new** private
output filename. A successful capture is not a quality pass; blocked/failed acceptance
can produce report exit code **2**, not permission to resubmit.

## Evidence limits / 証拠の制限

MCP は回答本文を取得する経路です。実行済み SQL/KQL/GQL・完全な結果行・backend conversation ID を
証明しません。回答内の query 風テキスト、出典名、JSON-RPC／MCP session ID を実行証跡に代用しません。
同じ run の実 query と結果が観測できない条件は未確認／不合格のままです。
厳密合格0件を「事実回答の正答率0%」とは読み替えません。

MCP captures answer text, not proof of executed SQL/KQL/GQL, complete result rows or
backend conversation identity. Query-looking text, source labels and JSON-RPC/MCP
session IDs cannot replace same-run executed-query/result evidence. Missing evidence
remains unconfirmed/failing; zero strict passes is not 0% factual answer accuracy.
Optional SDK/Responses paths need separate live qualification. Keep original evidence
unchanged and follow the [current response checks](../single-agent-workshop.md).
