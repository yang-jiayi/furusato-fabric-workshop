# 17.5 ここから始める：教材と実施順

[Lab 目次](../README.md) · [この章の目次](README.md)

この章の到達点は、配布版と同じ指示・データ選択・クエリ例を自分の1件の Data Agent に設定し、公開後に確認して、19章で再評価できることです。同じ数値の評価結果を保証するものではありません。17.5〜17.8で準備し、17.11の KQL 選択、17.12の9例の直接実行、17.13のモデル選択、17.14の Ontology を確認したら、17.16のコマンドを実施します。17.9〜17.14の指示原文は設定の確認用です。その後17.2の SQL と Code Interpreter の確認へ戻ります。

1. 参加者用 ZIP をすべて展開します。展開先の START_HERE.txt、guide、attachments、source を確認します。以下の workshop/ と tools/ のパスは、展開先の source フォルダーを起点とします。Lab または HTML を操作手順書にして、長い指示や SQL は同梱ファイルを UTF-8 のテキストとしてコピーできます。別の README を探して手順を補う必要はありません。
2. 4章で作業フォルダーと自分の参加者IDを確認し、5〜13章を実施します。Lakehouse の静的データ、Notebook 05 の Gold と品質管理テーブル、Eventhouse の集計ビュー、Semantic model、主 Ontology が必要です。未完了の時系列・Metrics は別欄に記録します。これらの警告を SQL の成功で完了扱いにしません。
3. 自分の DA_Furusato_&lt;PID&gt; を開き、ワークスペースとアイテムの URL を記録します。まだ無い場合は、指定フォルダーで New item から Data agent を作成し、この名前を付けます。既存の Agent があれば同じアイテムを使います。公開版がある場合は変更前の4つの指示、選択、クエリ例、公開状態を自分の記録フォルダーに保存します。
4. 公開前に Explorer の Tools を確認し、Code Interpreter が無い場合は Add tools から同じ Agent に追加して保存します。既にある場合は変更しません。17.16の prepare より前にこの操作を完了し、公開後の確認で初めて追加することがないようにします。
5. 編集権限がない場合はワークスペース管理者に自分の作業範囲の権限を依頼します。テナント設定や容量が機能を許可していない場合は、その前提条件を解消してから再開します。管理権限を持たない参加者が設定を書き換える必要はありません。

**この章で使う同梱ファイル**

| 用途 | ZIP 内の場所 |
| --- | --- |
| 今回採用した指示・選択・例 | workshop/v3.0.0-preview/data-agent/candidates/measured-contract-20261015 |
| 前半4つの SQL ビュー | workshop/v3.0.0-preview/data-agent/candidates/source-grounded/views |
| 後半2つの SQL ビュー | workshop/v3.0.0-preview/data-agent/candidates/complete-contract/views |
| 既存モデルの照合元 | tools/data-agent/measured_contract_profile.py / MEASURES |
| 評価の問題・記録方法 | 本書19章と付録C |

<details>
<summary>English</summary>

## 17.5 Start here: materials and order

The goal is to configure your one Data Agent with the distributed instructions, data selection and query examples, verify the published configuration, and evaluate it in Chapter 19. An identical evaluation score is not guaranteed. Prepare in 17.5–17.8, check KQL selection in 17.11, directly execute all nine examples in 17.12, check model selection in 17.13 and ontology in 17.14, then run the commands in 17.16. The original instruction text in 17.9–17.14 is a configuration reference. Afterwards return to the SQL and Code Interpreter checks in 17.2.

1. Extract the entire participant ZIP and locate START_HERE.txt, guide, attachments and source. All workshop/ and tools/ paths below start at the extracted source folder. Use Lab or HTML as the procedure; long instructions and SQL can be copied from the supplied UTF-8 files. No separate README search is needed to fill in these steps.
2. Confirm your folder and participant ID in Chapter 4 and complete Chapters 5–13. You need the static Lakehouse data, Notebook 05 Gold and quality tables, Eventhouse aggregate view, semantic model and main ontology. Record incomplete time-series or Metrics setup separately; SQL success does not resolve those warnings.
3. Open your DA_Furusato_&lt;PID&gt; and record its workspace and item URL. If absent, use New item in the assigned folder to create a Data agent with this name. Reuse an existing agent. If a published version exists, save the four current instruction fields, selections, query examples and publication state in your own record folder before editing.
4. Before publication, inspect Tools in Explorer. If Code Interpreter is absent, use Add tools to add it to this same agent and save; leave it unchanged if already present. Finish this before prepare in 17.16 so that you do not first add it during post-publication checks.
5. If you cannot edit, ask the workspace administrator for access to your assigned scope. Resolve tenant or capacity prerequisites before continuing when they disable a feature. Participants without administrative permissions do not need to change tenant settings.

**Included files used in this chapter**

| Purpose | Location in ZIP |
| --- | --- |
| Adopted instructions, selections and examples | workshop/v3.0.0-preview/data-agent/candidates/measured-contract-20261015 |
| First four SQL views | workshop/v3.0.0-preview/data-agent/candidates/source-grounded/views |
| Last two SQL views | workshop/v3.0.0-preview/data-agent/candidates/complete-contract/views |
| Existing-model contract source | tools/data-agent/measured_contract_profile.py / MEASURES |
| Evaluation questions and recording procedure | Chapter 19 and Appendix C in this guide |

</details>
