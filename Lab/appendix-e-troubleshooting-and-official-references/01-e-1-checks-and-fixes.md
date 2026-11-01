# E.1 確認と対処

[Lab 目次](../README.md) · [この章の目次](README.md)

よくある症状と、確認すること・対処を示します。設定や権限を自分で変更せず、解決しない場合は講師に伝えてください。

**うまくいかないときの確認**

| 症状 | 確認と対処 |
| --- | --- |
| Ontology、Ontology agent、Data Agent が表示されない | プレビュー機能の提供状況、地域、権限を確認します。管理者の設定は変更せず、講師に伝えて、その演習を省略します。 |
| Notebook 01 が PARTICIPANT_ID で停止する | 001〜999 の3桁の文字列か確認します（000、空欄、4桁以上は使えません）。 |
| Notebook 02〜04 が、実行前の確認で停止する | ENVIRONMENT（dev・test・prod）、SCOPE_FILE、PRIVATE_EVIDENCE_DIR（実行記録の保存先）、EXPECTED_WORKSPACE_NAME（正確な表示名）が設定されているかを確認します。Notebook が、範囲のファイルに書かれたフォルダーにあるかも確認します。書き込みを伴う段階では、APPLY_CHANGES、CONFIRMED_PLAN_SHA256、WRITE_GATE_FILE（承認のファイル）も必要です。 |
| Notebook 05 の適用が、ハッシュの不一致で止まる | プレビューをやり直し、新しい PLAN_SHA256 をコピーします。プレビューと適用で PARTICIPANT_ID、INCREMENT_PATH、ALLOW_AUTOMATED_APPLY（True の場合は EXPECTED_WORKSPACE_NAME も）の値が違うと、ハッシュも変わります。 |
| SQL analytics endpoint でテーブルが見えない、または件数が古い | 同期を待ってから再確認します。Notebook 01 を再実行しません。 |
| Instances に行が表示されない | バインド先のテーブル・列・キーと、SQL analytics endpoint の同期を確認します。 |
| Activator の activation が記録されない | ルールが停止している間に Edit action → Apply → Save を行ったか、ルールを Start したか、ファイルが Files/increment にあり、Live feed に FileCreated が届いているかを確認します。再アップロードせず、ルールを Stop して講師に伝えます。 |
| KQL の行数が想定の2倍になる | 同じファイルを2回取り込んでいます（再アップロード、または自動と手動の両方）。それ以上の取り込みを止めて講師に伝えます。データを消すには講師の承認が必要です。 |
| 時系列の観測が0件になる | 所有範囲・schema・RLS、DonationEvents の mirroring policy の安全な読み取り、実際の Delta add と parquet、KQL との件数・金額・キー・UTC 時刻・重複の照合を確認します。その後、DonatedAt、MunicipalityID → MunicipalityId、DonationEvents テーブル（ビューではない）の native バインドと実行クエリを確認します。Delta が無い、不一致、Backfill=true の HTTP 400、RLS や policy が互換でない場合は停止し、再試行・reset・off/on・再取り込みやセキュリティ無効化をしません。CompletionPercentage=100% や定義の読み取りだけでは、native 時系列・Metrics の照会成功にはなりません。 |
| Notebook 02 が停止する | 24章の自動配置で作成した Ontology か、handoff-ontology の実行前か、Metrics を追加していないかを確認します。適用が「Explicit expected-definition SHA differs」で止まった場合は、プレビューをやり直し、出力の beforeDefinitionSha256 を EXPECTED_DEFINITION_SHA256 に設定します。 |
| Metrics が表示されない | 主 Ontology で Metrics が設定済みか、メジャーを持つテーブルと Read・Build 権限を確認します。未設定の場合は未設定として記録します。2件目を作成せず、直接 Semantic model の DAX を別に確認します。 |
| Graph で Ineligible と表示される | ツールチップの理由を読みます。キー、バインド、ソースの種類（Semantic model から作った Entity は対象外）、バインド先のテーブルの数を確認します。 |
| Eligible なのに Materialize が失敗する | 時系列 Property などの型の対応を確認し、エラーを記録してその機能を停止します。主 Ontology や時系列は変更せず、別の Ontology も作りません。 |
| Rule を登録しても通知されない | 仕様どおりです。Rules は AI が説明に使う文脈で、通知や処理は行いません。ファイルの到着による処理は Activator（9章）で行います。 |
| 添付ファイルの内容が回答に使われない | 同じ会話で添付したか、ファイル名を挙げて依頼したか、1会話10ファイル・1ファイル 5 MB 以内かを確認します。ページを更新すると、添付は使えなくなります。 |
| RDF に注釈・同義語・バインドが無い | 配布の TTL は構造の参照資料です。主 Ontology のバインドや native 機能は、その定義と実際の照会で別に確認します。 |
| Data Agent に Ontology を追加できない（No data added のまま） | 新しいエクスペリエンスの Ontology に関する既知の問題の可能性があります。設定を変えず、講師に伝えます。 |
| T10 に「There's content here I can't work with」と表示される | プラットフォームの安全フィルターです。ブロックとして記録し、言い換えなどで回避しません。 |
| グラフの日本語が □ になる | 日本語フォントを使って、同じデータからグラフを作り直すよう依頼します。 |
| Version history に、保存した版が表示されない（No versions yet のまま） | 保存を繰り返さず、Restore の演習を省略して講師に伝えます。 |
| Data Agent の SQL の例が Invalid と表示される | 実際の質問で SQL が実行できるかを確認します。表示を変えるために例を書き換えず、講師に伝えます。 |
| クリーンアップで Eventhouse を削除できない | 繰り返し削除せず、講師に伝えます。削除済みの別のアイテムが参照している場合があります。 |

- https://learn.microsoft.com/en-us/fabric/iq/ontology/overview
- https://learn.microsoft.com/en-us/fabric/iq/ontology/how-to-create-entity-types
- https://learn.microsoft.com/en-us/fabric/iq/ontology/how-to-bind-data
- https://learn.microsoft.com/en-us/fabric/iq/ontology/how-to-create-relationship-types
- https://learn.microsoft.com/en-us/fabric/iq/ontology/how-to-add-metadata
- https://learn.microsoft.com/en-us/fabric/iq/ontology/how-to-use-rules
- https://learn.microsoft.com/en-us/fabric/iq/ontology/how-to-use-metrics
- https://learn.microsoft.com/en-us/fabric/iq/ontology/how-to-generate-from-semantic-models
- https://learn.microsoft.com/en-us/fabric/iq/ontology/how-to-use-namespaces
- https://learn.microsoft.com/en-us/fabric/iq/ontology/how-to-use-inheritance
- https://learn.microsoft.com/en-us/fabric/iq/ontology/how-to-reuse-properties
- https://learn.microsoft.com/en-us/fabric/iq/ontology/how-to-use-ontology-agent
- https://learn.microsoft.com/en-us/fabric/iq/ontology/how-to-use-ontology-graph
- https://learn.microsoft.com/en-us/fabric/iq/ontology/how-to-use-ontology-mcp-server
- https://learn.microsoft.com/en-us/fabric/iq/ontology/how-to-use-version-history
- https://learn.microsoft.com/en-us/fabric/iq/ontology/how-to-import-export
- https://learn.microsoft.com/en-us/fabric/iq/ontology/how-to-use-ontology-agent
- https://learn.microsoft.com/en-us/fabric/data-science/concept-data-agent
- https://learn.microsoft.com/en-us/fabric/data-science/data-agent-ontology-sources
- https://learn.microsoft.com/en-us/fabric/data-engineering/lakehouse-overview
- https://learn.microsoft.com/en-us/fabric/data-engineering/how-to-use-notebook
- https://learn.microsoft.com/en-us/fabric/real-time-intelligence/eventhouse
- https://learn.microsoft.com/en-us/fabric/real-time-intelligence/data-activator/activator-introduction
- https://learn.microsoft.com/en-us/fabric/data-factory/pipeline-runs

<details>
<summary>English</summary>

## E.1 Checks and fixes

Common symptoms, with what to check and how to fix them. Do not change settings or permissions yourself; if a problem is not solved, tell the instructor.

**Troubleshooting**

| Symptom | Check and fix |
| --- | --- |
| Ontology, Ontology agent or Data Agent does not appear | Check preview availability, region and permissions. Do not change admin settings; tell the instructor and skip that lab. |
| Notebook 01 stops on PARTICIPANT_ID | Check that it is a three-digit string from 001 to 999 (000, an empty value and four or more digits are not allowed). |
| Notebooks 02–04 stop at the checks before running | Check that ENVIRONMENT (dev, test or prod), SCOPE_FILE, PRIVATE_EVIDENCE_DIR (the run-record folder) and EXPECTED_WORKSPACE_NAME (the exact display name) are set. Also check that the Notebook is in the folder named in the scope file. Stages that write also need APPLY_CHANGES, CONFIRMED_PLAN_SHA256 and WRITE_GATE_FILE (the approval file). |
| The Notebook 05 apply run stops on a hash mismatch | Run the preview again and copy the new PLAN_SHA256. If PARTICIPANT_ID, INCREMENT_PATH or ALLOW_AUTOMATED_APPLY (and, when it is True, EXPECTED_WORKSPACE_NAME) differ between the preview and the apply run, the hash changes. |
| Tables are missing or counts look old in the SQL analytics endpoint | Wait for synchronization and check again. Do not rerun Notebook 01. |
| Instances shows no rows | Check the bound table, columns and key, and the SQL analytics endpoint synchronization. |
| No Activator activation is recorded | Check that you did Edit action → Apply → Save while the rule was stopped, that you started the rule, that the file is in Files/increment and that FileCreated arrived in Live feed. Do not re-upload; stop the rule and tell the instructor. |
| KQL row counts are twice the expected value | The same file was ingested twice (re-uploaded, or both automatic and manual). Stop further ingestion and tell the instructor. Deleting data requires the instructor's approval. |
| The time series shows zero observations | Check ownership scope, schema and RLS, safe DonationEvents mirroring policy readback, actual Delta add/parquet, and reconciliation with KQL for counts, amounts, keys, UTC timestamps and duplicates. Then verify the native binding to DonatedAt, MunicipalityID → MunicipalityId and the DonationEvents table (not the view), plus the executed query. Stop for missing Delta, mismatches, Backfill=true HTTP 400, or incompatible RLS/policy; do not retry, reset, toggle off/on, replay or disable security. CompletionPercentage=100% or definition readback alone is not successful native time-series or Metrics query execution. |
| Notebook 02 stops | Check that the ontology was created by the automated deployment in Chapter 24, that handoff-ontology has not run yet and that no Metrics were added. If the apply run stops with "Explicit expected-definition SHA differs", run the preview again and set EXPECTED_DEFINITION_SHA256 to the beforeDefinitionSha256 value in its output. |
| Metrics are not shown | Check whether Metrics are configured on the main ontology, the measure-owning table, and Read and Build permissions. Record unconfigured state as such, retain one ontology, and check direct semantic-model DAX separately. |
| Graph shows Ineligible | Read the reason in the tooltip. Check the key, the bindings, the source type (entities generated from a semantic model are not eligible) and the number of bound tables. |
| Materialize fails although items are Eligible | Check time-series and other type support, record the error and stop that feature. Keep the main ontology and time series unchanged without creating another ontology. |
| A registered rule sends no alerts | This is expected. Rules are context for AI explanations and do not send alerts or run actions. Processing on file arrival is done by the Activator (Chapter 9). |
| Attached file content is not used in answers | Check that you attached the files in the same conversation, referred to them by name, and stayed within 10 files per conversation and 5 MB per file. Refreshing the page makes attachments unavailable. |
| RDF lacks annotations, synonyms or bindings | The distributed TTL is a structural reference. Verify main-ontology bindings and native capabilities separately through their definitions and actual queries. |
| An ontology cannot be added to the Data Agent (it stays at No data added) | This may be a known issue with ontologies in the new experience. Do not change settings; tell the instructor. |
| T10 shows "There's content here I can't work with" | This is the platform's safety filter. Record it as blocked and do not try to get around it by rephrasing. |
| Japanese text in a chart appears as boxes | Ask for the chart to be created again from the same data with a Japanese font. |
| A saved version does not appear in Version history (it still shows No versions yet) | Do not repeat the save; skip the Restore exercise and tell the instructor. |
| SQL examples in the Data Agent show Invalid | Check whether SQL runs for actual questions. Do not rewrite the examples to change the status; tell the instructor. |
| The Eventhouse cannot be deleted during cleanup | Do not keep retrying; tell the instructor. Another deleted item may still refer to it. |

- https://learn.microsoft.com/en-us/fabric/iq/ontology/overview
- https://learn.microsoft.com/en-us/fabric/iq/ontology/how-to-create-entity-types
- https://learn.microsoft.com/en-us/fabric/iq/ontology/how-to-bind-data
- https://learn.microsoft.com/en-us/fabric/iq/ontology/how-to-create-relationship-types
- https://learn.microsoft.com/en-us/fabric/iq/ontology/how-to-add-metadata
- https://learn.microsoft.com/en-us/fabric/iq/ontology/how-to-use-rules
- https://learn.microsoft.com/en-us/fabric/iq/ontology/how-to-use-metrics
- https://learn.microsoft.com/en-us/fabric/iq/ontology/how-to-generate-from-semantic-models
- https://learn.microsoft.com/en-us/fabric/iq/ontology/how-to-use-namespaces
- https://learn.microsoft.com/en-us/fabric/iq/ontology/how-to-use-inheritance
- https://learn.microsoft.com/en-us/fabric/iq/ontology/how-to-reuse-properties
- https://learn.microsoft.com/en-us/fabric/iq/ontology/how-to-use-ontology-agent
- https://learn.microsoft.com/en-us/fabric/iq/ontology/how-to-use-ontology-graph
- https://learn.microsoft.com/en-us/fabric/iq/ontology/how-to-use-ontology-mcp-server
- https://learn.microsoft.com/en-us/fabric/iq/ontology/how-to-use-version-history
- https://learn.microsoft.com/en-us/fabric/iq/ontology/how-to-import-export
- https://learn.microsoft.com/en-us/fabric/iq/ontology/how-to-use-ontology-agent
- https://learn.microsoft.com/en-us/fabric/data-science/concept-data-agent
- https://learn.microsoft.com/en-us/fabric/data-science/data-agent-ontology-sources
- https://learn.microsoft.com/en-us/fabric/data-engineering/lakehouse-overview
- https://learn.microsoft.com/en-us/fabric/data-engineering/how-to-use-notebook
- https://learn.microsoft.com/en-us/fabric/real-time-intelligence/eventhouse
- https://learn.microsoft.com/en-us/fabric/real-time-intelligence/data-activator/activator-introduction
- https://learn.microsoft.com/en-us/fabric/data-factory/pipeline-runs

</details>
