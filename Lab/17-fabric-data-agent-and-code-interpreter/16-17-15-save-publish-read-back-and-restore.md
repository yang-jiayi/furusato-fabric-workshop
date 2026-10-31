# 17.15 保存・公開・読み戻し・復元

[Lab 目次](../README.md) · [この章の目次](README.md)

次の手順は、保存・公開・復元で確認する内容です。参加者の標準操作は17.16のコマンドで実施します。コマンドが公開済みの場合に、以下を読んでもう一度 Publish を押す必要はありません。

1. Agent の保存状態を確認します。編集画面を開き直し、4つの指示をそれぞれ元ファイルと照合します。全体指示は上限ちょうどなので、末尾に別の注記を追記しません。17オブジェクト・143列、KQL の10列、5つのモデルテーブルと10メジャー、主 Ontology の選択を再確認します。
2. KQL の9例がすべて Valid か確認します。SQL と Semantic model に評価問題の例を追加していないことも確認します。Draft のテストをした場合は、Draft と明記して公開版の結果と混同しません。
3. 同じ Data Agent の Publish を1回実行し、完了を待ちます。失敗やタイムアウトがあれば状態を確認してから判断し、成功したことにしません。公開リンクの Agent が同じアイテムかを確認し、公開版で新しい会話を開始します。
4. 公開日時・Agent URL・プロファイル名・データ確認値を記録します。UI から公開版の設定を直接読めない場合、Draft を開き直しただけで「公開定義一致」と書きません。次の表では UI 確認と公開定義の読み戻しを別々に判定します。厳密な構成再現は、公開版の指示・選択・説明・例を実際に読み戻して照合できた場合にだけ達成とします。
5. 17.2の SQL・Code Interpreter を確認してから、19章の固定問題で評価します。回答の値だけでなく実行ソース・クエリ・結果を保存します。うまくいかない問題を成功するまで送り直して採点しません。
6. 変更が原因で悪化した場合は、変更前に保存した同じ Agent の指示・選択・例へ戻し、再保存・再公開・読み戻しを行います。SQL ビューを変更した場合は保存した定義に戻します。新しい Agent や Ontology を増やしたり、データを削除したりして復元しません。変更前の設定がない初回構築では、推測した旧版へ戻さず、問題の設定とエラーを保存して修正します。

**構成と回答を別々に判定する完了表**

| 確認項目 | 合格条件 |
| --- | --- |
| データと SQL schema | 5・10・11章の値と17.7の全列が一致 |
| UI での設定確認 | 4指示・SQL17/143・KQL10列・モデル・主 Ontology を記録 |
| KQL 例 | 9件とも同じ質問・クエリで Valid |
| 公開定義の一致 | 読み戻した実定義の指示・選択・説明・例が一致。未取得は未確認 |
| Ontology の利用 | 選択状態とは別に、実際の native query と結果を確認 |
| 回答の評価 | 19章の全問題・失敗・未確認を含む記録がある |

<details>
<summary>English</summary>

## 17.15 Save, publish, read back and restore

These steps explain what saving, publication and restoration must verify. Participants use the commands in 17.16 for the standard procedure. Do not press Publish again merely because you read these steps after the command already published.

1. Check the agent's save state. Reopen the editor and compare each of the four instruction bodies with its original file. The global instruction fills the limit, so do not append notes. Recheck 17 objects and 143 SQL columns, ten KQL columns, five model tables and ten measures, and the main ontology selection.
2. Confirm that all nine KQL examples are Valid and that no evaluation-question examples have been added to SQL or the semantic model. Label Draft tests as Draft and keep them distinct from published-version results.
3. Publish the same Data Agent once and wait for completion. On failure or timeout, inspect the state before deciding what to do; do not assume success. Confirm that the published link targets the same item and start a new conversation in the published version.
4. Record the publication time, agent URL, profile name and data checks. If the UI cannot show published configuration directly, reopening Draft is not evidence of published-definition equality. Grade UI inspection and published-definition readback separately in the table below. Claim exact configuration reproduction only after actually reading back and comparing published instructions, selections, descriptions and examples.
5. Run the SQL and Code Interpreter checks in 17.2, then evaluate the fixed questions in Chapter 19. Save the source, query and results as well as answer values. Do not grade by repeatedly sending failed questions until one succeeds.
6. If a change causes regression, restore the instructions, selections and examples saved from this same agent, then save, republish and read back. Restore a changed SQL view from its saved definition. Do not restore by adding agents or ontologies or deleting data. On first construction without a previous configuration, preserve the failing configuration and error and repair them instead of inventing a prior version.

**Completion table separating configuration from answers**

| Check | Pass condition |
| --- | --- |
| Data and SQL schema | Chapter 5/10/11 data checks and every column in 17.7 match |
| UI configuration check | Record four instructions, SQL17/143, KQL10 columns, model and main ontology |
| KQL examples | All nine exact question/query pairs are Valid |
| Published-definition equality | Read-back instructions, selections, descriptions and examples match; unavailable readback is unverified |
| Ontology use | Verify actual native query/results separately from selection |
| Answer evaluation | Chapter 19 records include all questions, failures and unknowns |

</details>
