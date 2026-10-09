# 精度の校正と資料の校正手順 / Calibration and proofreading procedure

現行教材、[portable profile](../../../workshop/v3.0.0-preview/data-agent/candidates/measured-contract-20261009/README.md)、Word、HTML、配布ZIPは、同じソース契約と同じ手順を使用します。[実測要約](README.md)の内容判定とnative実行判定を分けたまま、以下を実施します。

The current course, [portable profile](../../../workshop/v3.0.0-preview/data-agent/candidates/measured-contract-20261009/README.md), Word, HTML and distribution ZIP use the same source contracts and procedures. Apply the steps below while keeping the [measured summary](README.md)'s content judgments separate from native-execution judgments.

## 1. 導入先とソースを固定する / Freeze the destination and sources

1. 対象Workspace・フォルダ・各Itemと、公開済みAgentの定義を確認します。同じWorkshopにOntology 1つ、Agent 1つを使用します。互換Ontologyを追加してconsumerの失敗を隠しません。
2. 実在する4ソースのnative schemaと選択状態、SQL metadata、Semantic ModelのTMDLを読み戻します。ビュー・品質テーブルを、ソース別に必要な範囲で選択します。古いItem IDや別ソースの列を転用しません。
3. 同じReadyの処理RunとGeneration、粒度・期間・件数・金額を直接SQL/KQL/DAXで照合し、前後で業務データが変わっていないことを記録します。CSVのrunラベルと処理Runは区別します。完了済み取り込みやNotebookの再実行で比較の母集団を変えません。
4. ソース定義・選択・指示・回答例・業務データfingerprintをハッシュで固定します。元の記録は変更せず、後続修正は別revisionとして保存します。

1. Confirm the destination Workspace, folder, Items and published Agent definition. Use one Ontology and one Agent for the workshop; an additional compatibility Ontology must not hide a failed consumer route.
2. Read back all four actual source schemas and selections, SQL metadata and Semantic Model TMDL. Select the required views and quality tables for their respective sources. Do not reuse stale Item IDs or columns from another source.
3. Reconcile the same Ready processing run and generation, grain, periods, counts and amounts through direct SQL/KQL/DAX. Record unchanged business data. Distinguish CSV run labels from processing runs. Do not change the comparison population by repeating completed ingestion or Notebook runs.
4. Hash source definitions, selections, instructions, examples and the business-data fingerprint. Preserve originals; store subsequent changes as separate revisions.

## 2. 検証計画を回答取得前に固定する / Freeze the evaluation before collecting answers

1. 質問集合、固定rubric、適用条件、試行回数、ソース要件、timeout、取得期限、未取得・NA・UNCLEARの扱いを記録します。変更の対象を確認する限定検証と、全体回帰を分けます。
2. 学習・修正用の質問と未使用検証を分けます。未使用の質問や期待解答を指示・回答例に含めません。実在スキーマやメジャーの定義はソース情報として利用できます。
3. 元10問・84条件を使う場合はその質問・条件を変えず、3回なら252条件として全試行を残します。確認質問のNAや、ソースの利用可能性が変わった条件は元判定を保持し、対応のある比較の除外理由・件数を別に示します。
4. 新しい会話へ計画どおりに1回送信します。途中エラー・取得不能を残し、良い回答の再試行だけを選びません。送信済みの結果回収は既存Responseの確認とし、質問の再送とは区別します。

1. Record the question sets, frozen rubric, applicable conditions, repetitions, source requirements, timeouts, collection deadline and treatment of missing, NA and UNCLEAR outcomes. Separate targeted checks from full regression.
2. Keep development questions separate from unused validation. Do not add unused questions or expected answers to instructions or examples. Actual schemas and measure definitions are legitimate source metadata.
3. If using the original ten-question, 84-condition suite, preserve its questions and conditions. Three repetitions retain all 252 judgments. Preserve original NA and changed-source-premise judgments; report any paired-comparison exclusions separately with reasons and counts.
4. Submit each planned question once in a new conversation. Retain intermediate errors and unavailable outcomes; do not select favorable retries. Retrieval of an existing Response is distinct from resubmitting a question.

## 3. 指示を校正し、適用結果を確認する / Calibrate instructions and verify application

1. [portable profileの手順](../../../workshop/v3.0.0-preview/data-agent/candidates/measured-contract-20261009/README.md)に従い、導入先の証明済みmetadataからDraftを生成します。指示長のサービス上限、4ソース、Ontology数、選択、回答例、Code Interpreter、変更対象外の定義を確認します。
2. SQLでは識別子・別名を引用し、名称dimensionから名前を取得し、集計と順位に同じ明細filterを適用します。SQLの回答例は実サービスのvalidation結果を確認し、Invalidは公開成功に数えません。
3. 時刻は結果のUTC ISOを優先し、12 AMは00時、12 PMは12時、1–11 PMは12を加えます。元タイムゾーンを確認せず `Z` を付けません。JSTは+09:00と日付繰越を確認します。区間の重なりとEventIDの同一性を分けます。
4. DAXは選択済みソースの実在TMDL定義を参照します。以下の既存定義では、内部 `KEEPFILTERS` が外側の同じ列filterと交差します。外側 `CALCULATE` の通常の置換動作だけでBLANKを説明しません。

```dax
[静的寄附件数] = CALCULATE([寄附件数], KEEPFILTERS('寄附'[データソース] = "StaticSeed"))
[受入増分寄附件数] = CALCULATE([寄附件数], KEEPFILTERS('寄附'[データソース] = "RealtimeIncrement"))
```

5. 公開後に定義を読み戻し、候補とサービスが正規化した実公開定義のハッシュを区別します。定義の一致は回答精度の受入ではありません。取得中に設定を変えず、次の修正は別フェーズで取得します。

1. Follow the [portable profile procedure](../../../workshop/v3.0.0-preview/data-agent/candidates/measured-contract-20261009/README.md) to compile a Draft from verified destination metadata. Check service instruction-length limits, four sources, Ontology count, selections, examples, Code Interpreter and preserved definitions.
2. Quote SQL identifiers and aliases, obtain names from real name dimensions, and apply identical fact filters to totals and rankings. Check example validation in the actual service; an Invalid example is not a publication success.
3. Prefer source-returned UTC ISO timestamps. Convert 12 AM to 00, keep 12 PM as 12, and add 12 to 1–11 PM. Do not append `Z` without confirming the source timezone. For JST, check +09:00 and date rollover. Keep interval overlap separate from EventID identity.
4. Use actual TMDL from the selected source. In the definitions above, internal `KEEPFILTERS` intersects the outer filter on the same column. The ordinary outer `CALCULATE` replacement behavior alone does not explain BLANK.
5. Read back the published definition and distinguish the candidate hash from the service-normalized published hash. Matching definitions do not establish answer-quality acceptance. Keep configuration fixed during collection; evaluate the next revision in a separate phase.

## 4. 内容とnative実行を別々に採点する / Score content and native execution separately

| 確認項目 / Check | 必要な根拠 / Required evidence |
|---|---|
| 回答内容 / Answer content | 固定条件、実回答、独立したソース照合。PASS／FAIL／UNCLEAR／NAを保持 / Frozen conditions, actual answers and independent source reconciliation; retain all verdicts |
| 必要ソース / Required source | 実際に呼び出されたソースとnative ID、必要な経路 / Actual invoked source and native identity, required route |
| 実行結果 / Execution result | 実行クエリと構造化返却結果、エラー、tool完了状態 / Executed queries, structured returned results, errors and tool completion |
| 定義と出力 / Definition and output | 公開読戻しのハッシュ、capture件数、送信／未送信／結果不明の件数 / Published readback hash, capture counts and submitted/unsubmitted/unknown counts |

回答に書かれたSQL/DAX/GQLは、それだけでは実行証拠になりません。直接エンジンの成功はAgent経由の成功を代替せず、HTTP 200／Response completedも内部query成功を意味しません。証拠不完全の正しい最終回答は、内容の一致とnative制約を両方報告します。未解決のconsumer、schema、native機能、UIの状態を残します。

SQL/DAX/GQL written in an answer is not execution evidence on its own. Direct-engine success does not replace Agent-route success, and HTTP 200 or a completed Response does not establish internal-query success. When a correct final answer has incomplete evidence, report both content agreement and native limitations. Retain unresolved consumer, schema, native-feature and UI states.

## 5. Word・HTML・配布物を校正する / Proofread Word, HTML and the package

1. 現行教材の共通日英原稿とportable profileの手順を修正します。WordとHTMLを直接別々に編集せず、同じ原稿・artifact manifestから新しいstageへ生成します。[Office build手順](../../../tools/docs/README.md)と[HTML検証手順](../../../tools/html/README.md)を使用します。
2. 両形式で、章・番号・完了条件・Item名・既定値・ソース選択・時刻・DAX説明・リンク・用語・既知の制約を照合します。履歴のスコアを現行版の結果に転用しません。参加者本文には実験履歴や私有評価の本文を入れず、別冊の本要約へ案内します。
3. DOCXの構造・段落・表・図・スタイル・改ページ、HTMLの日本語／英語切替・目次・リンク・図の表示を検証します。実際に行った描画確認と、未実施のMicrosoft Wordのページ／field更新は区別して記録します。
4. artifact manifest、Word／HTMLの対応ハッシュ、ZIP内容、SHA256SUMS、READMEのリンクを更新して同じ組合せを確認します。生成物のチェック成功はAI精度やnative全機能合格とは別です。
5. 私有パス・認証・Workspace／Item ID・ケース本文・期待解答・生traceが公開差分やZIPに含まれないことを確認します。ソース所有のスキーマ・DAX定義と、非公開評価入力は区別します。
6. 関連するコンパイラ・runtime・ドキュメント検証を実行し、差分をレビューしてGitHub mainへマージします。旧版の版付き資料と元の失敗記録は保持します。mainのcommit・配布物ハッシュ・検証範囲を記録します。

1. Edit the shared bilingual course source and portable-profile procedure. Generate Word and HTML together into a fresh stage from that source and artifact manifest, following the [Office build](../../../tools/docs/README.md) and [HTML validation](../../../tools/html/README.md) procedures.
2. Reconcile chapters, numbering, completion checks, Item names, defaults, source selections, timestamps, DAX explanations, links, terminology and limitations in both formats. Do not relabel historical scores as current results. Keep experiment history and private evaluation text outside the participant body; link to this separate summary.
3. Validate DOCX structure, paragraphs, tables, figures, styles and page breaks; validate HTML language switching, contents, links and image display. Record actual render checks separately from any unperformed Microsoft Word page/field refresh.
4. Update and reconcile the artifact manifest, paired Word/HTML hashes, ZIP contents, SHA256SUMS and README links. Artifact validation is separate from AI accuracy and acceptance of all native features.
5. Check public diffs and ZIP contents for private paths, authentication information, Workspace/Item IDs, case text, expected answers and raw traces. Distinguish source-owned schemas and DAX definitions from private evaluation inputs.
6. Run relevant compiler, runtime and document validation, review the diff, and merge GitHub main. Preserve versioned historical materials and original failures. Record the main commit, package hashes and validation scope.

## 完了の記録 / Completion record

記録は「どの設定を、どの母集団・何問・何条件で、どの取得条件と採点方法により確認したか」を含めます。R11の限定4/4を全体スコアに広げず、新しいWorkspaceでは実回答で同じ範囲を再確認します。全体の精度を主張する場合は、最新の公開定義を固定して全体回帰を実施し、全失敗と取得制約を残します。

Record the exact configuration, population, question and condition counts, collection settings and review method. Do not generalize R11's targeted four-of-four result into an overall score. Revalidate the same scope with actual answers in a new Workspace. An overall-quality claim requires a full regression against the frozen latest published definition, retaining every failure and collection limitation.
