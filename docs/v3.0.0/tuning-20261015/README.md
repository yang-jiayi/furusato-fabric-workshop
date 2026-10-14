# Ontology V2 再配置・実測評価 / Redeployment and evaluation — 2026-10-15

[作業レポート Word](furusato-ontology-v2-evaluation-20261015.docx) · [作業レポート HTML](furusato-ontology-v2-evaluation-20261015.html) · [確定集計 JSON](result-20261015.json)

[精度校正・資料校正 Markdown](calibration-and-proofreading.md) · [Word](calibration-and-proofreading.docx) · [HTML](calibration-and-proofreading.html) · [SHA-256](SHA256SUMS.txt)

指定フォルダーを整理し、18アイテムを再配置しました。OntologyとData Agentは各1件です。通常ソース3件と同じOntologyの独立context登録を持つ構成を確認し、採用済みの指示を `measured-contract-20261015` として可搬化しました。

同一条件281件の補助条件充足率は、**189/281（67.26%）から217/281（77.22%）へ9.96ポイント上昇**しました。元の290条件から、既定の確認質問分岐に伴う適用外9条件を両側同じキーで除外しています。これは事実、必要な回答要素・見出し、ソース経路を含む条件の充足です。有限回の回答の差から、確実な因果的改善や全文章の正しさは保証しません。

| 対応する条件の変化 | 件数 |
|---|---:|
| PASS → PASS | 187 |
| PASS → FAIL | 2 |
| FAIL → PASS | 28 |
| FAIL → FAIL | 62 |
| UNCLEAR → PASS | 2 |

PASSからFAILになった2条件は、必要な金額の省略と、回答で使わないよう明示された母集団の件数への言及です。

UNCLEARからの2条件は、送信・結果が不明だったbaselineの1枠に対応します。過去の不明を成功へ書き換えず、確認済みの誤答の改善とも扱いません。調整に用いない保留問題はbaselineと最終で別の集合であり、両方PASS 5・FAIL 1ですが、対応比較には含めません。

| 全51問・296条件 | PASS | FAIL | UNCLEAR | NA |
|---|---:|---:|---:|---:|
| baseline | 200 | 91 | 2 | 3 |
| 最終評価 | 225 | 65 | 0 | 6 |

厳密なnative受理は51問中1件から2件になりましたが、すべて確認質問の分岐です。ソース照会を伴う完成回答の厳密な受理は両方0件でした。成功したソース実行を1つ以上観測できた回答は28件から27件で、内容の充足率とは別の指標です。正式評価は111回の確認済みPOSTと1枠の送信不明を区別し、登録112枠を保持しています。最終評価後のCode Interpreter追加確認1問は、この分母に含めません。

ファイル別観測を問う最終回答3回のうち2回では、記載時刻が3分12秒の空きを示すのに観測期間が重なると誤って説明しました。月別比較では数値・順序を満たしても、Code Interpreterエラーで差・倍率・増減率を計算できない例もありました。固定条件外の誤りと要求全体の未完了を記録し、採点条件を後から変更していません。

別枠のCode Interpreter確認では、実SQLとダウンロードしたCSV・グラフの整合性を確認しました。ただし暦年範囲とnative実行証拠が不足し、厳密判定はinconclusiveです。最終回答が実行SQLを正確に再掲しなかった誤りも残しています。

3ファイルの自動取り込みと公式埋め込みによるReport表示は検証しました。直接静的GQLの成功、保存済みTime Seriesバインド、native Time Series実行のinconclusive、Ontology Metrics 0件、AgentのOntology contextのSchemaUnavailableは区別しています。別Ontologyの追加や、プラットフォーム全体のバグ解消は主張しません。

## 文書と検証

WordとHTMLは同じ確定集計から生成しています。LibreOfficeで変換したWordのPDF全15ページと、Chromiumで印刷したHTML全18ページを実際に目視確認し、デスクトップ・モバイル表示と全表も確認しました。Microsoft Wordアプリでの描画は未検証です。[生成検査](artifact-validation.json)と[実描画検査](report-render-validation.json)は、回答品質の合格証明とは別の記録です。Microsoft Wordによる描画は未検証です。

集計SHA-256: `935191c15a9a8505c2f7bf880f64f17d483210c5654331b058a86ccdb148e64c`。
過去の[2026-10-10レポート](../tuning-20261010/README.md)は当時の条件・結果として保持します。

## English

The requested folders were cleaned and redeployed with 18 items, including exactly one Ontology and one Data Agent. The adopted portable profile is `measured-contract-20261015`, with three ordinary sources and separate context for that same Ontology.

Supplemental condition fulfillment on 281 matched conditions increased from 189/281 (67.26%) to 217/281 (77.22%), a 9.96 percentage-point difference. Nine predeclared clarification-branch conditions were excluded symmetrically from 290. The transitions were 187 PASS→PASS, 2 PASS→FAIL, 28 FAIL→PASS, 62 FAIL→FAIL and 2 UNCLEAR→PASS. The two regressions were omission of a required amount and mention of an expressly prohibited population count. The two unknown-to-pass conditions represent newly obtained evidence in the corresponding final response; the baseline submission and outcome remain unknown. They are not a proven correction of a known wrong answer. Disjoint heldout sets each scored 5 PASS and 1 FAIL and were not paired.

Across all 51 registered questions and 296 conditions, baseline outcomes were 200 PASS, 91 FAIL, 2 UNCLEAR and 3 NA; final outcomes were 225 PASS, 65 FAIL, 0 UNCLEAR and 6 NA. Strict acceptance was 1/51 then 2/51, exclusively clarification responses; neither phase had a strictly accepted completed source-query answer. Responses with at least one observed successful source execution changed from 28 to 27. Formal accounting retains 111 known POSTs and one uncertain slot within 112 registered slots; the separate post-final Code Interpreter question is excluded.

These measurements do not establish guaranteed causal improvement or correctness of every sentence. Two of three final file-interval answers included a false overlap claim. A monthly answer omitted requested calculations after a Code Interpreter error. The separate capability probe returned SQL-consistent CSV/chart artifacts but remained inconclusive for calendar scope and full native execution, and its final answer reproduced the executed SQL inaccurately.

Automatic ingestion and official Report rendering were verified. Ontology consumption remains SchemaUnavailable; saved Time Series configuration is separate from inconclusive native execution, and native Ontology Metrics remain zero. All 15 pages of the LibreOffice-exported Word PDF and all 18 pages of Chromium HTML print output were visually checked, together with desktop/mobile views and every table. Document generation and rendering records are separate from AI-answer acceptance. Microsoft Word rendering remains unverified. Historical reports retain their original scope and results.
