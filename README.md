# Furusato Workshop 3.1.0

Microsoft Fabric の Lakehouse・Eventhouse・Ontology・Semantic model・Data Agent を組み合わせ、合成データから業務の意味を共有できる分析基盤を作るハンズオンです。

[**Labで始める（GitHub上の正本）**](Lab/README.md) · [**日英HTML手順書**](docs/furusato-workshop-v3-1-0-complete.html) · [**参加者用ZIP**](docs/Furusato_Workshop_v3.1.0_current.zip) · [ダウンロードとSHA-256](docs/README.md)

![Furusato Workshopの完成アーキテクチャ](Lab/assets/pc-01-architecture.png)

## 進め方

1. [第4章](Lab/04-prerequisites-deployment-scope-and-safe-execution/README.md)で、利用できるワークスペース・容量・権限・自分の作業フォルダーと参加者IDを確認します。
2. [第24章](Lab/24-automated-deployment-operations-and-cleanup/README.md)の24.4〜24.6で基盤を配置し、第5〜8章で作成済みの設定とデータを確認します。
3. 第24.7節と第9〜11章で3つの増分ファイルを順に取り込み、品質処理とGoldを確認します。成功した取り込みやNotebookを重複して実行しません。
4. 第24.8節でSemantic modelとData Agentを配置し、[第17章](Lab/17-fabric-data-agent-and-code-interpreter/README.md)で指示・選択状態・Code Interpreter・公開状態を確認します。設定の読み戻しだけで、実行や回答精度が確認できたとは判断しません。
5. [第19章](Lab/19-evaluate-and-improve-ai-answer-quality/README.md)と[付録C](Lab/appendix-c-evaluation-questions-scoring-and-recording-forms/README.md)で回答を評価し、根拠となる問い合わせと結果を調べて改善します。

Labは24章・5付録の全手順を収録しています。キャプチャごとの操作ページに加え、準備、コマンド、設定の全文、参照表、完了条件、評価問題と採点基準を掲載しています。各ページの **English** を開くと英語の手順を読めます。HTMLはファイルとして保存し、ブラウザーで日英切替・検索・進捗チェック・印刷を利用できます。

## 作成するもの

1件のOntologyと1件のData Agentを中心に、Lakehouseの静的データ、Eventhouseの観測データ、品質処理後のGold、Semantic modelを接続します。Data Agentの構成にはLakehouse、KQL Database、Ontology、Semantic modelの4つの論理ソースを使い、Code Interpreterは同じAgentのツールとして設定します。Ontologyの定義・context登録は、データへのbindingや実行可能な query の証明ではありません。

利用にはFabricの有効な容量と必要な権限が必要です。機能の提供条件はテナント・リージョンによって異なります。設定画面の表示、実際の実行、公開後の動作はそれぞれ確認します。同じ設定の再現が、同じ回答精度を保証するわけではありません。

第17章の `current-experimental` profile は実験用です。設定の読み戻しは回答精度の採用・保証を意味しません。ソース、Graph、時系列、mirroring の完全性と実行結果は個別に確認し、自分の公開版を第19章・付録Cで評価してください。

Ontologyのnative Metricsは講師による事前設定が必要です。未設定の場合は設定済みと扱わず、講師に確認します。[第4章](Lab/04-prerequisites-deployment-scope-and-safe-execution/README.md)の容量画面は実環境の例であり、表示されたF16は最小要件ではありません。増分取り込みの確認では、対象ファイル・イベント・Activator・Pipelineの実行を対応付けます。成功表示や行数だけで自動配信の完了とは判定しません。

確認済みの共有ワークスペースでは、KQL の `DonationEvents` は3ファイル分の15,000行ですが、OneLake Delta の Parquet は002・003に一致する10,000行（168,788,000円）で、その2ファイルについてソースレコード単位で完全照合しています。001由来の5,000行がありません。したがってOneLake export は部分状態です。この部分状態を理由に、共有環境では mirroring policy の変更・再取り込みや時系列 binding を行いません。この制限は時系列／mirror作業に関するもので、Ontology の静的データに対する SQL probe は独立に成功しています。Microsoft Learn によると Ontology agent は対応する Lakehouse・Eventhouse・Semantic model のソースに SQL・KQL・DAX で問い合わせ、GQL は Graph model がある場合の関係 traversal に使います（[Microsoft Learn: Use an ontology agent](https://learn.microsoft.com/en-us/fabric/iq/ontology/how-to-use-ontology-agent)）。この SQL 成功はそのソース・言語・クエリ・結果に限られ、Graph model の存在・準備状態や GQL 実行を証明しません。反対に、部分 mirror から Graph model が未存在とは推定できません。Graph model の存在・準備状態と実際の GQL 結果は別々に確認し、Ontology の文脈付けを GQL 実行と同一視せず、SQL の実行を GQL と呼び替えません。参加者自身の別環境では、Labに従い実データと Delta の完全照合が通った場合だけ mirroring や時系列作業へ進みます。policy の読み戻しだけではデータ到着や native query の成功は証明されません。

公開された構成だけでは回答精度は保証されません。自分の公開版を第19章・付録Cで評価し、回答だけでなく実際のソース・実行言語・クエリ・結果を確認してください。関連する GraphModel item が存在しても、公開 definition の node/edge 型・データソース・node/edge table mapping が null なら scaffold 状態であり、実行可能な空グラフとはみなしません。準備済みの schema と mapping を確認できるまで GQL の成功を主張しないでください。静的 Ontology SQL の成功も、Graph・GQL・時系列・mirror完全性や Agent 精度を証明しません。Gold/semantic model の期待値は94,900行・¥1,596,157,000です。件数や単一dimensionの一致だけで複数軸の交差、時系列機能、source自体の正しさまで確認できたとはみなさず、用途に応じて別に検証します。

データはすべて学習用の合成データです。自治体名と自治体コードだけが実在の参照ラベルで、寄付・寄付者・事業者・返礼品は架空です。静的寄付と増分の観測は母集団と粒度が異なるため、混同して集計しません。

## 実行資産

| 場所 | 内容 |
|---|---|
| [Lab/](Lab/README.md) | 最新版の参加者用Markdown手順書と画面キャプチャ |
| [docs/](docs/README.md) | 保存して使える日英HTML、参加者用ZIP、SHA-256 |
| [workshop/v3.0.0-preview/](workshop/v3.0.0-preview/) | Notebook、CSV、Ontology、モデル、Agent設定、添付資料 |
| [tools/](tools/) | 配置、データ検証、回答評価、教材生成のツール |

参加者用ZIPはすべて展開し、同じ版の手順書と実行資産を使ってください。ローカルのコマンドはリポジトリのルート、ZIPでは展開先の `source/` を起点に実行します。資格情報、環境固有の接続情報、非公開の回答ログはGitHubへ追加しません。[SECURITY.md](SECURITY.md)も確認してください。

## English

Build and inspect a Microsoft Fabric solution with synthetic data, one Ontology and one Data Agent. The GitHub [Lab guide](Lab/README.md) is the authoritative participant path; save the [bilingual HTML](docs/furusato-workshop-v3-1-0-complete.html) for offline use. Download the matching [participant ZIP](docs/Furusato_Workshop_v3.1.0_current.zip) and verify its [SHA-256](docs/SHA256SUMS.txt).

Follow Chapters 4 and 24 for scoped deployment, Chapters 5–13 for data and model checks, Chapter 17 to configure and read back the current experimental profile on the same Data Agent, and Chapter 19 plus Appendix C for evaluation and improvement. Each Lab operation has its own Markdown page; expand **English** for the equivalent procedure. All 24 chapters and five appendices include the preparation, commands, full settings, reference tables and completion checks.

Use an authorized workspace and folder with active capacity and the required feature permissions. Verify actual execution and published behavior separately from configuration. Matching a configuration does not guarantee an identical answer score. All data is synthetic training material, and static donations must remain distinct from operational observations.

Chapter 17's `current-experimental` profile is experimental. Configuration readback is not accepted or guaranteed answer accuracy. Verify source, Graph, time-series and mirroring completeness and execution results separately, then evaluate your own publication using Chapter 19 and Appendix C.

Native Ontology Metrics require instructor setup; an unconfigured feature is not a verified configuration. The Chapter 4 capacity screenshot is a real environment example, not an F16 minimum requirement. Correlate the exact increment file, event, Activator and Pipeline run before accepting automatic delivery; a success label or row count alone is insufficient.

In the verified shared workspace, KQL `DonationEvents` contains 15,000 rows across the three files, while OneLake Delta Parquet contains 10,000 rows / JPY 168,788,000 exactly reconciled at source-record level for files 002 and 003; 5,000 file-001-specific rows are absent. The OneLake export is partial. This restricts mirroring changes/backfill and time-series work in this shared environment; it does not universally block Ontology queries or GQL. A static-data SQL probe against the Ontology succeeded independently. Microsoft Learn describes Ontology-agent queries against corresponding Lakehouse, Eventhouse and semantic-model sources using SQL, KQL and DAX, and GQL for relationship traversals when a graph model exists ([Use an ontology agent](https://learn.microsoft.com/en-us/fabric/iq/ontology/how-to-use-ontology-agent)). The verified SQL result applies only to its source, language, query and result: it does not establish Graph-model presence/readiness or GQL execution. The partial mirror does not establish Graph-model absence. Verify Graph-model presence/readiness and actual GQL results separately; ontology grounding is not necessarily GQL, and SQL execution must not be relabeled as GQL. In a separate participant-owned environment, follow the Lab and reconcile actual Delta files with all source data before mirroring or time-series work. Policy readback alone proves neither data arrival nor native-query success.

A published configuration does not guarantee answer quality. Evaluate your own publication using Chapter 19 and Appendix C, checking the actual sources, execution languages, queries and results as well as final answers. A companion GraphModel item whose public definition has null node/edge types, data sources and node/edge table mappings is a scaffold, not a ready zero-row graph. Do not claim GQL success until populated schema and mappings are verified. Static Ontology SQL success does not establish Graph/GQL readiness, time-series support, mirror completeness or Agent accuracy. Expected Gold/semantic-model totals are 94,900 rows / JPY 1,596,157,000. Counts or single-dimension reconciliation alone do not establish multi-axis intersections, time intelligence or source correctness; verify these separately for the intended use.
