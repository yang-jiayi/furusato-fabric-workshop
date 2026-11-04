# 12.7 AI 設定の確認と任意の Verified answers

[Lab 目次](../README.md) · [この章の目次](README.md)

Apply・開き直し・設定の読み戻しだけで即時反映を仮定しません。Copilot pane を閉じて開き直し、反映待ちと確認時刻を記録します。Git・deployment pipeline で LSDL/tooling を変更した場合は Import・DirectQuery・Direct Lake とも Power BI service 側のモデル refresh が必要で、DirectQuery・Direct Lake の同期は1日1回です。Direct Lake の再索引は publish/republish、または索引が24時間より古く直近14日間に Copilot/Q&amp;A が使われた場合に行われます。これらの操作は別途許可が必要で、本手順だけでは refresh/republish を実行しません。同期・索引の状態が未確認なら回答評価を開始せず、未確認と記録します。

設定・読み戻しと回答品質は別に確認します。まず12.2の直接 DAX を同じ母集団・期間・フィルターで照合し、モデル用指示の追加前後で19章の固定質問を別の会話から実行します。回答ごとに実際の DAX、ソース、フィルター、結果、エラーを保存します。Gold全体、静的、受入増分、Eventhouse観測を区別し、KEEPFILTERS の交差・BLANK、居住/寄附先都道府県、日付範囲、単位を確認します。指示に固定の正解合計を書かず、採点条件も変更しません。

スキーマ内の業務列と、優先スキーマ外の UTC 日時の両方を質問し、生成クエリと参照元を確認します。除外列に関する回答の拒否をセキュリティ保証とは扱いません。Data Agent Python SDK は評価に利用できますが、モデルの Prep for AI は設定できません。Copilot を使う場合は pane を閉じて開き直します。Agent のプレビュー runtime が既に有効でも、これらの確認を省略しません。

Verified answers は任意・未設定です。同じモデルに接続した既存レポート、Copilot 対応 workspace と編集権限がある場合だけ検討します。配布レポートの「月別寄附総額 — 当年と前年同期間」は、日付[年月]、寄附[寄附総額]、寄附[寄附総額 前年同期間] を使う候補です。schema.json の6個の完全な質問を trigger の候補とし、visual・page・report の保存フィルターと適用対象を先に確認します。非表示列に依存する visual は使用せず、スライサーが引き継がれると推定しません。柔軟フィルターは実際に対応するものを最大3個までとし、設定後は exact/semantic match と実際の DAX を確認します。レポートが無ければ作成して埋め合わせず、この任意手順を未実施と記録します。

Verified answers の CI/CD は Git integration・REST API・deployment pipeline を含め非対応です。6個の質問は native authoring 用の候補で、配布・Notebook 配置では設定されません。Fabric IQ が有効な Copilot では Verified answers の visual は返されません。対象の Copilot が Fabric IQ 経路かを担当者が別途確認し、IQ 有効なら visual 応答の検証は対象外、未確認なら未確認と記録します。この制限だけで Data Agent の visual metadata による DAX grounding も不可とは判断せず、その利用可否と効果は別途実測します。教材の Data Agent/Ontology 経路の改善や合格を保証しません。

同期・索引と任意機能の公式条件: https://learn.microsoft.com/en-us/power-bi/create-reports/copilot-prepare-data-ai / https://learn.microsoft.com/en-us/power-bi/create-reports/copilot-prepare-data-ai-faq

既存レポートのタイトル・使用列・メジャー・フィルターは DAX 生成の参考情報になりますが、Verified answers の設定済み証拠ではありません。Best Practice Analyzer、Memory Analyzer、Performance Analyzer や Semantic Link Labs の get_measure_dependencies は任意の追加診断です。本手順では未実行で、依存パッケージの導入や Notebook の実行を伴う診断は別途許可と実行記録が必要です。

公式資料: https://learn.microsoft.com/en-us/fabric/data-science/semantic-model-best-practices / https://learn.microsoft.com/en-us/power-bi/create-reports/copilot-prepare-data-ai-instructions / https://learn.microsoft.com/en-us/power-bi/create-reports/copilot-prepare-data-ai-data-schema / https://learn.microsoft.com/en-us/power-bi/create-reports/copilot-prepare-data-ai-verified-answers

<details>
<summary>English</summary>

## 12.7 Verify AI preparation and optional verified answers

Do not assume immediate effect from Apply, reopening and settings readback alone. Close/reopen the Copilot pane and record propagation waits and verification times. After Git/deployment-pipeline LSDL/tooling edits, Import, DirectQuery and Direct Lake models require a model refresh in the Power BI service; DirectQuery/Direct Lake sync only once a day. Direct Lake reindexes on publish/republish, or when its index is older than 24 hours and Copilot/Q&amp;A was used within the last 14 days. Such actions require separate authorization; this procedure does not itself run refresh/republish. If sync/index state is unverified, record that and do not start answer evaluation.

Separate configuration/readback checks from answer quality. First compare direct DAX in 12.2 under the same population, period and filters, then run Chapter 19's fixed questions in separate conversations before/after model guidance. Save actual DAX, source, filters, result and errors for each answer. Distinguish all Gold, static, accepted increments and Eventhouse observations; check KEEPFILTERS intersection/BLANK, residence versus recipient prefecture, date range and units. Do not put expected totals in instructions or change scoring conditions.

Test a business field inside the schema and the UTC timestamp outside it; inspect the generated query and source. Do not treat refusal for an excluded field as a security guarantee. The Data Agent Python SDK can evaluate responses but cannot configure model Prep for AI. Close/reopen the Copilot pane when using Copilot. An already-enabled Agent preview runtime does not replace these checks.

Verified answers are optional and unconfigured. Consider them only with an existing report bound to the same model, a Copilot-enabled workspace and authoring permission. The supplied report's 月別寄附総額 — 当年と前年同期間 visual is a candidate using 日付[年月], 寄附[寄附総額] and 寄附[寄附総額 前年同期間]. Use the six complete questions in schema.json as candidate triggers; first inspect saved visual/page/report filters and scope. Do not use a visual dependent on hidden columns or assume slicers carry over. Configure at most three genuinely supported flexible filters; then verify exact/semantic matching and actual DAX. If no report exists, record this optional step as unperformed rather than create a report to fill the gap.

Verified answers do not support CI/CD, including Git integration, REST APIs and deployment pipelines. The six questions are native-authoring-only candidates, not configuration applied by packaging/notebook deployment. Copilot does not return verified answers when Fabric IQ is enabled. Have the owner separately verify whether the target Copilot uses Fabric IQ: if enabled, the visual-response check is not applicable; if unknown record it as unverified. This restriction alone does not establish that Data Agent DAX grounding from visual metadata is unavailable; verify that support and effect separately. It guarantees neither improvement nor passing evaluation in this workshop's Data Agent/Ontology flow.

Official sync/index and optional-feature conditions: https://learn.microsoft.com/en-us/power-bi/create-reports/copilot-prepare-data-ai / https://learn.microsoft.com/en-us/power-bi/create-reports/copilot-prepare-data-ai-faq

Existing report titles, columns, measures and filters can inform DAX generation; they do not prove verified answers are configured. Best Practice Analyzer, Memory Analyzer, Performance Analyzer and Semantic Link Labs get_measure_dependencies are optional further diagnostics. They have not been run by this procedure; diagnostics requiring package installation or notebook execution need separate authorization and execution records.

Official references: https://learn.microsoft.com/en-us/fabric/data-science/semantic-model-best-practices / https://learn.microsoft.com/en-us/power-bi/create-reports/copilot-prepare-data-ai-instructions / https://learn.microsoft.com/en-us/power-bi/create-reports/copilot-prepare-data-ai-data-schema / https://learn.microsoft.com/en-us/power-bi/create-reports/copilot-prepare-data-ai-verified-answers

</details>
