# Activator lifecycle and ingestion evidence / 開始・停止と取り込みの根拠

[README](../../README.md) · [Provisioning](README.md) ·
[Data checklist](../../docs/data-validation-checklist.md)

## 日本語

### 初回起動は定義更新と分ける

Notebook 04 は、監視先が空のまま、停止状態の FileCreated ルールを構築します。
これは安全な構築完了であり、増分の取り込み完了ではありません。
新規ルールの `shouldRun=true` への定義更新、UI の Running、MCP の `isRunning=true` だけを
実行エンジンの初回有効化と同一視しません。**公式 Activator MCP の `start_rule`、
またはポータルの明示的な Start 操作**を使います。停止も `stop_rule` / Stop を使います。

新規ルールの定義フラグだけの変更では起動せず、同じ定義に正式な開始操作を行うと動作するケースを
分離した診断環境で確認しました。一度正式に開始した後は定義変更でも動作し得るため、
「定義更新は常に無効」と一般化しません。全テナント・将来のサービスの保証ではなく、
設定状態と実行状態を分け、実際の配送を確認するための保守的な手順です。

### コマンド

Python 3.10+ と Azure CLI の通常のサインインを使います。依存関係がない場合だけ
`python -m pip install -r tools/provisioning/requirements-activation.txt` で導入します。
実環境 ID と証拠は、無視設定のあるフォルダーも含めて、すべての Git checkout の外で保持します。

```powershell
# Offline: no sign-in, token acquisition or service call.
python .\tools\provisioning\manage_activation.py doctor

# Supply the exact workspace name, Folder GUID and three-digit PID.
$WorkspaceId = '<workspace-guid>'
$WorkspaceName = '<workspace-name>'
$FolderId = '<folder-guid>'
$ParticipantId = '001'
$PrivateRoot = '<absolute-private-root-outside-git>'

# Read-only preview; authentication is required for discovery.
python .\tools\provisioning\manage_activation.py start `
  --workspace-id $WorkspaceId --expected-workspace-name $WorkspaceName `
  --folder-id $FolderId --participant-id $ParticipantId --private-root $PrivateRoot --run preview-start

# Only after approval. Every operation label must be new.
python .\tools\provisioning\manage_activation.py start `
  --workspace-id $WorkspaceId --expected-workspace-name $WorkspaceName `
  --folder-id $FolderId --participant-id $ParticipantId --private-root $PrivateRoot --run approved-start `
  --apply --confirmation "START ACTIVATOR $ParticipantId"

# After the final verification, or on a delivery failure.
python .\tools\provisioning\manage_activation.py stop `
  --workspace-id $WorkspaceId --expected-workspace-name $WorkspaceName `
  --folder-id $FolderId --participant-id $ParticipantId --private-root $PrivateRoot --run approved-stop `
  --apply --confirmation "STOP ACTIVATOR $ParticipantId"
```

`--tenant-id <tenant-guid>` は必要な場合にだけ明示します。Folder はURLの数値 `subfolderId` ではなくGUIDです。
CLIは参加者の命名規則で正確な3 Itemを検索し、ソース、rule ID、イベント条件、
Pipeline、動的な `Type` / `Subject` / `Source` を照合します。別のルール構成は黙って許可しません。
このCLIはファイル送信、Pipeline起動、定義変更、権限変更、容量の再開を行いません。

公式 MCP endpoint：

公式資料：[Activator remote MCP server (preview)](https://learn.microsoft.com/en-us/fabric/real-time-intelligence/mcp-remote-activator)。
この手順は**既に構築されたルールの管理**だけを使い、MCPの`create_rule`でOneLake/Pipelineルールを新規作成しません。
Previewの対応範囲とtool catalogueを対象環境で照合し、未対応時は正式なポータル操作を使います。

```text
https://api.fabric.microsoft.com/v1/mcp/workspaces/{workspaceId}/reflexes/{activatorId}
```

初期化と `tools/list` で `start_rule` / `stop_rule` / `list_rules` / `get_activations_for_rule` の
利用可否を確認します。MCPの開始が利用できなければポータルの正式なStartへ戻り、
ALM定義のフラグ書換えを代替手段にしません。既にフラグだけを変更しStartが選べない場合は、
実行中Jobを確認してから、対象ルールをStop→Startするか、公式 `start_rule` を実行します。

### ファイルは完成したバイト列を1回だけ送る

配布CSVのSHA-256を確認してから、OneLake Blobの `PutBlob` を1回使い、
`x-ms-blob-type: BlockBlob` と `If-None-Match: *` を付けます。
同じファイルの再アップロード・上書きはしません。
監視先でCreateFile→Append→FlushWithCloseを使うと、
0-byte作成時と書き込み完了時の両方からFileCreatedが発生する場合があります。

`activation_runtime.put_complete_increment` は発見済みの `oneLakeFilesPath`、
Workspace/Lakehouse ID、配布ファイル名、全バイト列、配布SHA-256、
Storage token providerと `PrivateStore` を受け取り、1回のPutBlobと全バイトreadbackを行います。
8 MiB以下の同梱3増分専用です。認証情報は記録しません。
初期化済みの `PrivateStore` も、毎回Git外・包含範囲を再確認し、出力は排他的に作成します。

```python
# Run with tools/provisioning on the Python import path.
from pathlib import Path
from activation_runtime import PrivateStore, put_complete_increment

receipt = put_complete_increment(
    one_lake_files_path=discovered_lakehouse["properties"]["oneLakeFilesPath"],
    workspace_id=workspace_id,
    lakehouse_id=discovered_lakehouse["id"],
    filename=csv_path.name,
    content=csv_path.read_bytes(),
    expected_sha256=released_csv_sha256,
    token_provider=lambda: credential.get_token("https://storage.azure.com/.default").token,
    store=PrivateStore(Path(private_file_receipt_root)),
)
```

この関数は低レベルの送信処理です。呼出し元は、対象の正式開始receipt、監視先の空状態、
各ファイルの一度だけの送信intent、前のファイルの検証完了を確認します。
最初の配送が未確認なら2本目へ進みません。アップロードの結果不明や412は、
失敗を記録して既存ファイル・イベント・Job・実データを調べる理由であり、再送の理由ではありません。

### 成功判定

| 状態 | 証明したこと |
|---|---|
| `requires_formal_start` | 停止状態の構築完了。正式開始は未実施 |
| `armed_unverified` | 正式開始の応答とRunningを確認。配送は未検証 |
| `uploaded_unverified` | 完成ファイルのバイトを確認。配送は未検証 |
| `automatic_delivery_verified` | 実イベント1件、実activation1件、正しいPipelineの新規Completed Job1件を照合 |
| データ検証完了 | 上記に加え、Copy入力・出力とSourceFile別のKQL件数・金額が一致 |

`verify_automatic_delivery` は以下を照合します。

- 全バイト検証済みで、同じSubjectのPutBlob FileCreatedが1件、サイズ・Source・Event IDが一致すること。
- 実activationのrule ID、対象Workspace/Pipeline、`Type` / `Subject` / `Source` とactivation IDが一致すること。
- 事前一覧にないJobが1件だけで、対象PipelineのCompletedであり、activationと実行時刻が対応すること。
- 運用者が手動で起動した制御用Jobを成功証拠から除外すること。

ネイティブのイベント表とMCP `structuredContent.activations`、事前・事後Job一覧をJSONとして
非公開ルートへ保存し、`verify_automatic_delivery` の名前付き引数と同じ形で入力します。
`manual_job_ids` はJSONでは配列です。`events` には実表の `___id`、`___type`、`___source`、
`___subject`、`api`、`contentLength` を保持し、欠落値を作って埋めません。

```powershell
python .\tools\provisioning\manage_activation.py verify `
  --private-root $PrivateRoot --input delivery-input.json --out delivery-result.json
```

これはオフライン検査であり、入力JSONを本物にする仕組みではありません。
保存した生応答・Request ID・ハッシュと取得経路を一緒に保管します。
`invokeType=Manual` が返ってもそのラベルだけで起動経路を判断せず、実activationとJobを照合します。
Live feedのActionプレビューはactivation履歴の代わりにしません。
`DataNotAvailable` は0件の成功結果ではありません。余分なイベント・Job、別対象、
途中失敗、未確認データは不合格です。配送の合格もCopyやKQLの合格を代替しません。

### 不成立時

正式にStopし、遅延したJobと実データを確認して記録します。
Stopは既に作成されたJobを取り消しません。容量エラーだけを理由に容量設定を変更しません。
手動取り込み・履歴イベントの再処理・ファイルの退避と再作成には別の明示承認が必要です。
標準データや元10問／84条件を変更して、欠けた結果を合格にしません。

## English

Use the official Activator MCP **`start_rule` / `stop_rule`** operations, or the portal
Start / Stop controls. Updating `shouldRun` through an item definition is not an
equivalent first-start procedure. Running metadata can be visible while automatic
execution has not initialized. A previously initialized rule may behave differently;
this is not a claim that all definition updates always fail.
See the [official preview documentation](https://learn.microsoft.com/en-us/fabric/real-time-intelligence/mcp-remote-activator).
This workflow manages an already created rule; it does not use MCP `create_rule`
to author a OneLake/Pipeline rule. Recheck the target's available tool catalogue.

Notebook 04 deliberately leaves the trigger stopped and emits
`ACTIVATOR_REQUIRES_FORMAL_START`. Use the commands above with an explicitly selected
workspace name, Folder GUID and PID. `start` / `stop` remain read-only previews without
`--apply` and the exact confirmation. Each operation uses a fresh private run label,
discovers the target and verifies the source/rule/action wiring. `doctor` and `verify`
are offline; discovery previews authenticate. The CLI never uploads or runs a Pipeline.

For automated uploads, send each complete released CSV using a single **PutBlob**
with **`If-None-Match: *`** and verify its full bytes. The Python helper above is limited
to the three packaged small CSVs; its caller must check official-start evidence,
empty/prior-file state and one-time intent. Watched CreateFile/Append/FlushWithClose
can produce both an empty-file and a committed-file event. Do not overwrite or retry
an uncertain upload. A 412 means an existing file needs investigation.

Keep `armed_unverified`, `uploaded_unverified`, `automatic_delivery_verified` and final
Copy/KQL validation separate. The offline delivery gate requires exactly one real
complete-file event, one native activation with matching rule/target/Type/Subject/Source,
and one new Completed Pipeline job in the activation window, excluding manual controls.
Use actual event rows, MCP activation history and job responses; never manufacture
missing evidence. The generic `invokeType=Manual` label is not sufficient to classify
the execution path. Live-feed previews are not production activation history, and
`DataNotAvailable` is an error, not a successful zero count.

Keep all configuration, IDs, raw responses and receipts outside every Git checkout.
On failure, formally stop the rule, check late jobs and data, and report the exact
stage. Stop does not cancel jobs already submitted. Manual fallback or file replay
requires separate approval. These safeguards do not change the dataset, Ontology,
Agent instructions or original ten questions / 84 conditions.
