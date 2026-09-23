# tools/provisioning — provisioning チェーンの reseal / provisioning chain reseal

[日本語](#日本語) | [English](#english)

---

## 日本語

`workshop/v2.7.0` の runtime を編集したあと、provisioning チェーン全体を
ディスク上のファイルから決定的に再計算します。

### Workshop の1体構成

Notebook 04 の `ENABLE_UNIFIED_DATA_AGENT=True` は、主Agent
`DA_Furusato_<PID>` 1体に参照SQL/KQL機能とCode Interpreterを構成します。
接続するOntologyは教材用 `ONT_Furusato_<PID>` のみで、
AIPath Ontologyや別のAI Reference／Code Interpreter Agentは作成しません。
`ENABLE_AI_REFERENCE_ARCHITECTURE` とは同時に有効化できません。
両フラグの既定値は互換性のためFalseで、新しい1体構成の教材が前者を明示的に有効化します。

`tools/data-agent/unified` の指示と `unified_agent.py` が入力です。
resealerは `bundle/unified-agent/profile.json` とハッシュ付き契約を生成し、
参照SQL/KQL契約と教材Ontologyのソース定義にも結び付けます。
GLOBAL・SQL・KQLの指示を分け、Ontology固有の指示フィールドは従来どおりnullのまま、
関係の指針はGLOBALへ収録します。Code Interpreterは取得済み結果の追加計算・図・ファイル用で、
必要なSQL/KQL/GQLの実行証跡を置き換えません。

既存の主Agentが異なる構成の場合、このprovisionerは自動で上書きしません。
現行定義を退避し、Draftだけを統合・検証してから公開する移行が必要です。
別体の旧Agentを削除するのは、統合後の公開版と共有ソースの保持を確認してからです。
構成の封印やデプロイ成功を、回答精度の向上やバージョン昇格の証明にしません。

### なぜ必要か

Notebook 04 は runtime 全体を gzip + base64 の payload として複数のセルに埋め込み、
2 つの manifest と参加者契約が同じバイト列をハッシュで固定しています。
したがって bundle のソースを 1 文字でも変えると、次の連鎖が一斉に古くなります。

```
bundle のソース
  -> bundle-manifest.json                (ファイル単位ハッシュとセマンティックハッシュ)
  -> Notebook_04 の埋め込み payload      (gzip + base64 チャンク)
  -> payload-manifest.json               (payload ダイジェストと asset ダイジェスト)
  -> participant-workspace-contract.json (固定しているすべてのダイジェスト)
```

手で書き写す余地をなくすため、このツールがすべてを再計算します。

Fabric の対話実行には 1 セル 500k の制限があります。payload は
`furusato-provisioning-payload` タグの付いた連続セルに分割し、各セルを
450,000 UTF-8 bytes 以下に保ちます。最後の payload セルで連結・展開するため、
Notebook 単体で実行できる性質は変わりません。runtime の検出は固定セル番号ではなく
宣言によって行います。

### 使い方

```powershell
python tools/provisioning/reseal_runtime.py            # チェーンを書き直す
python tools/provisioning/reseal_runtime.py --check    # v2.7.0 の出力が変化したら失敗する
python tools/provisioning/test_runtime_safety.py       # 実機で発見した runtime 回帰を検査
```

**`--check` は読み取り専用ではありません。** 再生成後に差分を検出するため、
正常に再生成できても差分で終了コード 1 になった場合、変更は残ります。
下記のゲート例外によるロールバックとは別です。デプロイ前の照合では、
固定コミットを新しい一時ディレクトリーへ展開し、そのコピー内でのみ実行してください。
差分があれば停止し、再生成されたコピーを配布・デプロイしません。

ソースを変更していない状態で実行しても、出力はバイト単位で同一です。
`--check` は実行前後の `workshop/v2.7.0` を直接比較するため、repository 内の
無関係な作業中ファイルには反応せず、reseal が変更した runtime ファイルだけを
差分として検出します。同じバイト列のファイルは書き直さず、変更がある場合だけ
同じディレクトリーの一時ファイルから置換します。そのため dirty worktree でも
CI でも同じゲートとして使えます。

文書 validator の `FINAL_RUNTIME.payloadSha256` は、承認した配布版を固定する別の pin です。
runtime を意図的に変更したリリースでは、生成した payload と両 manifest・参加者契約を照合した後で
この pin も更新します。resealer が承認済み版の pin を自動的に追従させることはありません。

### 実機回帰で守ること

- 新規Activatorは `shouldRun` の定義更新で開始したことにせず、公式 `start_rule` / `stop_rule` を使う。
  [ライフサイクルと配送検証](activation.md)の `manage_activation.py` は対象発見・preview・明示承認を行う。
  Runningは `armed_unverified`、実イベント・activation・Completed Job照合後だけ
  `automatic_delivery_verified`。Copy/KQLの合格はさらに別の確認である。
- 生成した Notebook 01 の parameter cell に、選択した Participant ID を反映する。
- 増分 CSV は `Files/_provisioning/furusato/<PID>/increment` に保管し、
  `Files/increment` は空で用意する。FileCreated トリガーを正式な開始操作で起動した後、
  参加者が監視フォルダーへ 1 本ずつアップロードする。
- CSV の完全一致は一時 driver file への `fs.cp` と byte 比較で確認する。
  部分表示用 `fs.head` を全文検証として使わない。
- schema-enabled Lakehouse では、発見した default schema 内の Delta directory と
  `_delta_log` を検証する。未対応の旧 `/tables` API を再試行しない。
- Ontology の `sourceSchema` は実在する `dbo` を指す。Graph の定義が編成された後、
  `Refresh` ジョブを確認し、自動 refresh を重複実行しない。
- Data Agent の比較では resource ID と有効な選択・説明・指示を保持し、UI が再生成する
  schema tree ID と未選択の枝を区別する。既定値 `false` の省略は有効化 `true` と区別する。
- Optional の `gold.donation_agent` は静的データと受入済み増分を含む混合テーブルであり、
  Core の `ot_*` 静的スナップショットではない。静的な質問では実列
  `DataSource = 'StaticSeed'`、受入済み・重複排除後の増分では
  `DataSource = 'RealtimeIncrement'` を使い、Eventhouse の生の観測件数とは区別する。
  Core を変更しない別の評価構成で、追加前後の同じ質問とソース境界を記録する。
- `test_runtime_safety.py` は、これらの正常系・拒否系と payload の分割・復元を検査する。
- Kusto v1 の結果は table-of-contents の `Kind` と `Ordinal` でデータ表と
  メタデータ表を区別する。メタデータの `Name` 列を関数一覧として扱わず、
  番号付きの QueryStatus にある部分失敗も拒否する。

### 実行される処理

| 手順 | 内容 |
|---|---|
| Notebook 埋め込みの更新 | Notebook 02 / 03 の `ONTOLOGY_METADATA` / `ONTOLOGY_DEFINITION_TEMPLATE` を ontology の正本から再生成する |
| ランク説明の同期 | Data Agent の Lakehouse ソースにある `*Rank` 列の説明を、ontology セマンティックメタデータの説明で上書きする |
| bundle manifest | ファイル単位の SHA-256、few-shot / stage config の意味ハッシュ、グローバル指示の文字数・バイト数・上限を書き直す |
| payload | bundle・dataset CSV・Notebook 01・ontology template・KQL 管理コマンドから payload を組み立て、Notebook 04 のセルへ書き戻す |
| payload manifest | payload のダイジェストとサイズ、asset ダイジェスト、runtime ハッシュを書き直す |
| 参加者契約 | payload / notebook / manifest / ソース説明 / ソース指示 / few-shot / ontology / dataset / KQL の各ダイジェストを書き直す |

### ゲート

次のいずれかに該当する場合、ツールは終了コード 1 で停止し、実行中に更新した
ファイルを開始前のバイト列へ戻します。そのため、途中まで reseal された状態は残りません。

- draft と published の few-shot または stage config が一致しない。
- `stage_config.aiInstructions` が `agent-instructions.txt` を反映していない。
- グローバル指示が 15,000 文字（この配布物が封じた安全側の予算）を超えている。
- `ontology-full-definition-template.json` の `definitionTemplateSha256` が古い。
- 封印対象ファイルのいずれかに CR（キャリッジリターン）が含まれている。
- payload に載せる bundle テキストが、ディスク上のバイト列と一致しない。
- 契約に埋め込んだ description / instructions / few-shots が、bundle の値または
  自身が宣言するダイジェストと一致しない。

### 改行コードを LF に固定する理由

ランタイムのピンは、ファイルの生バイト列の SHA-256 です。`Path.write_text` は
`\n` を `os.linesep` に変換するため、Windows で reseal すると CRLF が書き込まれ、
Linux で reseal した場合と別のダイジェストになっていました。さらに payload 側は
`read_text` の universal newlines で LF に畳まれていたため、参加者が payload を
展開して書き出した LF ファイルは、CRLF で計算された bundle manifest のダイジェスト
と一致しませんでした。このツールは `write_lf()` で符号化済みバイト列を書き込み、
変換層そのものを取り除きます。`runtime.lfDeterminism` /
`runtime.payloadBundleParity` / `runtime.resealDeterminism` が検査します。

### 決定性テスト

    python tools/provisioning/test_determinism.py

CRLF 混入、payload とディスクの不一致、契約テキストの手書き編集、廃止した
`globalInstructionsChars` / `globalInstructionsBytes` の復活という 4 つの欠陥を
実際に埋め込み、対応するゲートが検出することを確認します。さらに、workshop 外の
無関係な dirty file を置いても `reseal_runtime.py --check` が成功することと、
ゲート失敗時に途中までの書き込みがすべて元へ戻ることを確認します。

### 明示的な自動実行

Notebook 04 と 05 は、既定では引き続き対話実行でのみ書き込みます。
Jobs API で適用する場合は、preview 前に `ALLOW_AUTOMATED_APPLY=True` と
正確な `EXPECTED_WORKSPACE_NAME` を指定します。自動実行の選択はプランの
ハッシュに含まれます。preview のハッシュ確認、排他的な実行ウィンドウ、
すべての既存データ・定義・権限チェックは省略されません。
Notebook 02 と 03 の対話実行制限は変更しません。

同一 Workspace の別 Folder でも Notebook の同名作成は拒否されます。
複数参加者を同じ Workspace に配置するときは、インポートする Notebook 名に
`_<PID>` を付け、Notebook 04 の `USE_PARTICIPANT_NOTEBOOK_NAMES=True` を
preview 前に指定します。作成される Notebook 01 にも同じ接尾辞が付き、
既存参加者の Notebook を再利用・上書きしません。既定名は変更しません。

### 実環境 API との互換性

Ontology の JSON は意味ハッシュを変えずに `sourceType` を先頭に配置し、
同じ serializer を Notebook 02–04 に埋め込みます。AIPath には固有の logical ID
を与え、10 個の Entity テーブルと Supplier/Gift 関係表の計 11 ソースを保持します。
自動 Graph 更新の `GraphNotRefreshable` は、完全な編成と実行中ジョブなしを
確認した場合だけ再実行します。

Agent は materialized-view / table-valued-function の実際の型と階層を解釈し、
未設定の指示を null と空文字で区別しません。Published の参照 API は
アイテム直下の `/datasources`、Staging は `/staging/datasources` です。
FileCreated の検証では、原子的な OneLake Blob `PutBlob` 後の自動ジョブと
実件数を確認します。DFS 書き込み成功だけをイベント配送の証拠にせず、
手動 Pipeline 起動への無言の置換や重複アップロードはしません。
`activation_runtime.py` は完成CSVのPutBlob1回・上書き拒否・全バイトreadbackと、
nativeイベント／activation／Job照合の共通処理です。配布CSV、元10問／84条件、
Ontology、Agent指示を変更しません。生応答と操作receiptはGit外に保存します。
`test_activation_runtime.py` で初回正式開始、通知だけのMCP応答、認証前の拒否、
対象違い、イベント／Job重複、履歴不明、手動制御の誤採点を検査します。

### AI 参照構成のソースと明示的な封印

`workshop_runtime.py` が Notebook 04 の実行コードの正本です。Notebook のセルは
直接編集せず、このファイルと runtime helper を変更した後に resealer を実行します。
`reference_assets.py` は既存の SQL/KQL ソース、`path_ontology.py` の変換、
既存のソース指示から `bundle/ai-reference` を生成します。非公開の候補定義や
評価記録、現在のテナント ID は入力にしません。

`ENABLE_AI_REFERENCE_ARCHITECTURE=False` が既定値です。True にするときは、
別途承認した GLOBAL の正確なバイト列、SHA-256、`candidate` または `accepted`
の宣言を先に封印します。未封印なら認証前に停止し、公開済み GLOBAL へ
フォールバックしません。status は運用者の宣言であり、封印処理による品質証明ではありません。

配布 bundle には `ai-reference/global-instructions.txt` と
`ai-reference/global-profile.json` を同梱しています。前者の SHA-256 は
`e52c3acf2578f180ff8a78576e3fb1f9ddb9563dac92b9ca49acae6bfbcaefb4`、
宣言 status は `candidate` です。14,998 文字で、この配布物の 15,000 文字予算を守ります。
同一 ID の 3 ソースが実際に成功した場合だけ照合完了を宣言し、静的 SQL の規則が
必要な Ontology 処理を抑止しないよう明確化しています。安全な代替は Static 2025 UTC
の寄付額と順位に限定し、各表に実際の出典を残します。
過去の別 profile の満点を、この設定の品質承認へ転用しません。
現行コースの構成と確認項目は [Data Agent の回答確認](../../docs/single-agent-workshop.md)を参照してください。
標準 Core は別構成として保持し、有限の成功を本番全般の `accepted` へ読み替えません。

```powershell
python tools/provisioning/reseal_runtime.py --reference-global <explicit-file> --reference-global-sha256 <exact-sha256> --reference-global-status candidate
```

参照構成の Agent は `DA_Furusato_AIReference_<PID>`、参照用 Ontology は
`ONT_Furusato_AIPath_<PID>` です。従来の `ONT_Furusato_<PID>` は 10/72/1/15、
別モデルは 10/21/0/15 を保ちます。認可済みの既存候補を再利用する場合だけ
`REFERENCE_AGENT_ROLE="authorized-candidate"`、`REFERENCE_AGENT_NAME`、
`REFERENCE_AGENT_EXPECTED_ID` を明示します。既存構成が完全一致しなければ停止し、
Core への昇格や置換は行いません。

SQL は notebook から実行する portable helper を使い、Windows PowerShell を
notebook から呼びません。必要な SQL driver、token audience、接続条件は
`reference_sql.py` のモジュール説明が正本です。ライブラリを自動インストールせず、
不足時は前提条件を示して停止します。public Agent element ID は実際の discovery
結果だけを使い、serialized UUID、SQL/KQL の native interface、選択状態を混同しません。

### ランク説明を同期する理由

ランクは、Lakehouse の列と Ontology の Property が完全に同じ測定値を指す唯一の
列群です。両者が別の文を持つと、Agent は「同額なら同順位（dense）」と
「同額でも順位は重複しない（row_number）」の両方を同時に読むことになります。
そのため、このツールは言い換えるのではなく ontology の文をそのまま複製し、
`tools/docs/validate_docs.py` の `runtime.rankDescriptionParity` と
`runtime.noDenseRankWording` が一致を検査します。

---

## English

### Explicit lifecycle and automatic-delivery evidence

Use [the lifecycle procedure](activation.md) after Notebook 04, which intentionally
ships the FileCreated rule stopped. `manage_activation.py` previews the exact scoped
rule and uses official `start_rule` / `stop_rule` only after explicit approval.
It does not equate a definition's `shouldRun` or Running metadata with execution.
`activation_runtime.py` supplies single complete-file PutBlob with no-overwrite
guards and a native event/activation/new Completed Job gate. Copy/KQL verification
remains separate. `test_activation_runtime.py` covers these boundaries.
No dataset, Ontology or Agent instruction changes are required by this correction.

Recomputes the whole provisioning chain deterministically from the files on disk
after any edit to the `workshop/v2.7.0` runtime.

### Single-Agent workshop mode

`ENABLE_UNIFIED_DATA_AGENT=True` configures one primary `DA_Furusato_<PID>`
with reference SQL/KQL helpers, the full teaching `ONT_Furusato_<PID>` and
Code Interpreter. It creates no AIPath or separate reference/interpreter
Agent. It is mutually exclusive with `ENABLE_AI_REFERENCE_ARCHITECTURE`;
both remain False by default for compatibility, and the single-Agent guide
explicitly enables unified mode.

The resealer packages `tools/data-agent/unified` and `unified_agent.py` as a
hash-bound `bundle/unified-agent/profile.json`, linked to the reference helper
contract and teaching Ontology source. Ontology-specific instructions remain
null; graph guidance is in GLOBAL. CI is post-query analysis/visualization,
not a substitute for required SQL/KQL/GQL evidence.

An existing different primary configuration is not overwritten automatically.
Back it up, validate the unified draft while preserving the published stage,
then publish and verify before retiring the other Agents. Neither sealing nor
deployment proves higher answer accuracy or authorizes a quality promotion.

The document validator's `FINAL_RUNTIME.payloadSha256` separately pins the approved
distribution. For an intentional runtime release, update it only after reconciling
the generated payload, both manifests and participant contract. The resealer does
not automatically move the approved-release pin.

### Why it exists

Notebook 04 carries the whole runtime as a gzip+base64 payload in several cells,
and two manifests plus the participant contract pin the same bytes by hash. One
character changed in a bundle source therefore invalidates a chain:

```
bundle sources
  -> bundle-manifest.json                (per-file and semantic digests)
  -> Notebook_04 embedded payload        (gzip+base64 chunks)
  -> payload-manifest.json               (payload digest and asset digests)
  -> participant-workspace-contract.json (every pinned digest)
```

The tool recomputes all of it so no pin is ever transcribed by hand.

Fabric interactive execution enforces a 500k cell limit. Consecutive cells tagged
`furusato-provisioning-payload` each remain below 450,000 UTF-8 bytes. The final
payload cell joins and decompresses them, so the notebook is still self-contained.
Runtime sources are located by declarations, not fixed physical cell indexes.

### Usage

```powershell
python tools/provisioning/reseal_runtime.py            # rewrite the chain
python tools/provisioning/reseal_runtime.py --check    # fail if v2.7.0 output changes
python tools/provisioning/test_runtime_safety.py       # regressions found in live execution
```

**`--check` is not read-only.** It detects drift after regeneration; when
regeneration succeeds but drift returns exit code 1, the changes remain.
This differs from rollback after a gate raises an exception. For deployment
verification, extract the pinned commit to a fresh temporary directory and run
the check only in that copy. Stop on drift; never distribute or deploy the
regenerated copy.

A run with no source edit produces byte-identical output. `--check` compares
`workshop/v2.7.0` directly before and after the run, so unrelated worktree changes
are ignored and only runtime files changed by the reseal count as drift. It therefore
works the same way in a dirty worktree and as a drift gate in CI.

Unchanged bytes are not rewritten. Changed files use a same-directory temporary
file and bounded atomic replacement, avoiding transient Windows truncating-open
failures during checks and rollback.

### Live runtime regression guarantees

- Bind the chosen participant ID in the generated Notebook 01 parameter cell.
- Stage increments under `Files/_provisioning/furusato/<PID>/increment`, leaving
  `Files/increment` empty until the real FileCreated trigger is running.
- Verify full CSV bytes using `fs.cp` to a temporary driver file, not a preview
  returned by `fs.head`.
- For schema-enabled Lakehouses, verify Delta directories and `_delta_log` in
  the discovered default schema instead of retrying an unsupported legacy API.
- Bind Ontology tables to the real `dbo` schema; wait for graph compilation and
  discover registered `Refresh` jobs before issuing any new refresh.
- Data Agent comparison preserves resource IDs, effective selections,
  descriptions and instructions while distinguishing UI-generated schema IDs
  and unselected branches. Omitted default `false` never equals enabled `true`.
- Optional `gold.donation_agent` mixes static rows and accepted increments; it
  is not the Core `ot_*` static snapshot. Filter its physical column with
  `DataSource = 'StaticSeed'` for static questions or
  `DataSource = 'RealtimeIncrement'` for accepted, deduplicated increments.
  Keep raw Eventhouse observations separate. Use an isolated evaluation
  configuration and the same before/after questions without changing Core.
- `test_runtime_safety.py` exercises these positive and fail-closed cases.
- Kusto v1 results use the table of contents' `Kind` and `Ordinal` to separate
  data from metadata. A metadata `Name` column is not a function inventory, and
  partial failures in numbered QueryStatus tables are rejected.

### What it does

| Step | Detail |
|---|---|
| Notebook embeds | Regenerates `ONTOLOGY_METADATA` / `ONTOLOGY_DEFINITION_TEMPLATE` in Notebooks 02 and 03 from the ontology sources |
| Rank description sync | Overwrites the description of every `*Rank` column in the Data Agent Lakehouse source with the ontology semantic-metadata description |
| Bundle manifest | Rewrites per-file SHA-256, the few-shot and stage-config semantic digests, and the global-instruction character count, byte count and limit |
| Payload | Builds the payload from the bundle, dataset CSVs, Notebook 01, the ontology template and the KQL management commands, then writes it back into bounded Notebook 04 cells |
| Payload manifest | Rewrites the payload digest and size, the asset digests and the runtime hashes |
| Participant contract | Rewrites the payload, notebook, manifest, source description, source instruction, few-shot, ontology, dataset and KQL digests |
| Analytics pins | Recomputes Notebook 05, Power BI project/tree/deployment-tool and Variable Library template hashes |

### Gates

The tool stops with exit code 1 and restores every file changed during the run
to its exact starting bytes when:

- draft and published few-shots or stage configs disagree;
- `stage_config.aiInstructions` does not mirror `agent-instructions.txt`;
- the global instructions exceed 15,000 characters (this distribution's sealed safety budget);
- `definitionTemplateSha256` in `ontology-full-definition-template.json` is stale;
- any sealed file contains a carriage return;
- the bundle text placed in the payload does not equal the bytes on disk;
- an embedded description, instruction block or few-shot array in the contract
  disagrees with the bundle value or with its own declared digest.

### Why line endings are pinned to LF

The runtime pins files by the SHA-256 of their raw bytes. `Path.write_text`
translates `\n` to `os.linesep`, so resealing on Windows wrote CRLF and produced
different digests than the same sources resealed on Linux. The payload side was
folded back to LF by `read_text`'s universal newlines, so a participant who
unpacked the payload wrote LF files and could not verify them against the CRLF
digests in the bundle manifest. The tool now writes encoded bytes through
`write_lf()`, removing the translation layer entirely. `runtime.lfDeterminism`,
`runtime.payloadBundleParity` and `runtime.resealDeterminism` enforce it.

### Determinism tests

    python tools/provisioning/test_determinism.py

Plants four real defects - a CRLF sealed file, a payload that no longer matches
disk, a hand-edited contract text, and the return of the retired
`globalInstructionsChars` / `globalInstructionsBytes` aliases - and checks that
the matching gate reports each one. It also proves that an unrelated dirty file
outside the workshop does not make `reseal_runtime.py --check` fail and that a
gate failure rolls back every partial write.

### Explicit automated execution

Notebooks 04 and 05 still default to interactive-only writes. Before previewing
an intended Jobs API apply, explicitly set `ALLOW_AUTOMATED_APPLY=True` and the
exact `EXPECTED_WORKSPACE_NAME`. The automation choice changes the plan hash.
The matching preview hash, exclusive execution window, and existing data,
definition, and permission checks remain mandatory. Notebooks 02 and 03 retain
their interactive-only write restriction.

Notebook display names must be unique even across folders in the same workspace.
For multiple participants in one workspace, suffix imported notebook names with
`_<PID>` and set Notebook 04's `USE_PARTICIPANT_NOTEBOOK_NAMES=True` before preview.
The generated Notebook 01 uses that suffix rather than reusing or overwriting
another participant's notebook. Default naming remains unchanged.

### Live API compatibility

Ontology wire JSON puts `sourceType` first without changing the canonical
semantic hash. The same maintained serializer is embedded in Notebooks 02–04.
The separate AIPath gets its own workspace-scoped platform logical ID and
retains 11 graph sources: 10 entity tables plus the supplier/gift relationship
bridge. A service-started `GraphNotRefreshable` failure may be retried only
after complete compilation is proved and no refresh is active.

Data Agent verification recognizes the native materialized-view and table-valued
function groups, preserves selected children under unselected grouping nodes,
and treats missing/null optional instructions as unset, not as arbitrary text.
Published datasource reads use the item-root `/datasources` endpoint; staging
reads use `/staging/datasources`.

For programmatic FileCreated tests, verify an actual automatic Pipeline job
and exact Eventhouse totals after each upload. In the validated deployment,
an atomic OneLake Blob `PutBlob` generated the event; a successful DFS
create/append/flush sequence alone did not prove event delivery. Never silently
substitute a manual Pipeline run or repeat an upload when observations or a
pending job already exist.

### Opt-in AI reference sources and explicit sealing

`workshop_runtime.py` is the canonical Notebook 04 executable source. Edit that
file and its runtime helpers, then run the resealer; never hand-edit the generated
notebook cells. `reference_assets.py` builds `bundle/ai-reference` from existing
SQL/KQL sources, the `path_ontology.py` transformation, and existing source
instructions. It does not consume private candidate definitions, evaluation
records, current tenant IDs, or credentials.

`ENABLE_AI_REFERENCE_ARCHITECTURE=False` remains the default. Enabling it requires
an explicitly packaged reference GLOBAL with an exact byte hash and a declared
`candidate` or `accepted` status. An incomplete bundle fails before authentication;
the released GLOBAL is never substituted. Status is the operator's declaration,
not quality acceptance established by packaging.

The distribution includes `ai-reference/global-instructions.txt` and
`ai-reference/global-profile.json`. The instruction file's SHA-256 is
`e52c3acf2578f180ff8a78576e3fb1f9ddb9563dac92b9ca49acae6bfbcaefb4`,
and its declared status remains `candidate`. Its 14,998 characters stay within
this distribution's sealed 15,000-character budget. Completion claims require
three successful current-turn same-ID source queries; purely static SQL guidance
must not suppress required Ontology work. Safe alternatives are limited to
Static 2025 UTC donation amount and rank, and tables retain actual attribution.
Do not transfer a previous profile's perfect run to this configuration.
See [Data Agent response checks](../../docs/single-agent-workshop.md)
for the current course's configuration and evidence boundaries. The teaching Core remains
separate; finite success is not production-wide `accepted`.

```powershell
python tools/provisioning/reseal_runtime.py --reference-global <explicit-file> --reference-global-sha256 <exact-sha256> --reference-global-status candidate
```

The opt-in Agent is `DA_Furusato_AIReference_<PID>` and its separate path Ontology
is `ONT_Furusato_AIPath_<PID>`. The teaching `ONT_Furusato_<PID>` retains
10 entities / 72 static properties / 1 time-series property / 15 relationships;
the path model retains 10 / 21 / 0 / 15. To reuse an authorized existing candidate,
set `REFERENCE_AGENT_ROLE="authorized-candidate"`, its exact `REFERENCE_AGENT_NAME`
and actual `REFERENCE_AGENT_EXPECTED_ID`. Existing configuration must match
exactly. Core promotion or replacement is deliberately not implemented.

SQL executes through a portable notebook helper, not a Windows PowerShell child
process. `reference_sql.py` documents the exact driver, token audience, and
connection prerequisites. No library is installed automatically; missing drivers
produce an actionable prerequisite error. Agent selections use discovered public
element IDs only, keeping serialized UUIDs, native SQL/KQL interfaces, and selected
leaves distinct. The three KQL helper bodies remain authoritative in
`tools/data-agent/operational-functions`; the legacy leader is neither required on
fresh installs nor selected or deleted automatically.

### Why rank descriptions are synced

A rank is the one column family where the Lakehouse column and the Ontology
property describe exactly the same measurement. If the two carry different
sentences, the agent reads both "equal amounts share a rank" (dense) and "equal
amounts never share a rank" (row_number) at once, and nothing in the prompt
resolves the contradiction. The wording is therefore copied rather than restated,
and `runtime.rankDescriptionParity` and `runtime.noDenseRankWording` in
`tools/docs/validate_docs.py` assert the equality.
