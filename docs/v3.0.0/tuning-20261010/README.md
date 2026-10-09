# Data Agent の実測改善と適用範囲 / Measured Data Agent improvements

2026-10-10 公開資料。実測の参照時点は 2026-10-09 UTC です。

同じ条件で比較できる219条件の回答内容の一致率は、改善前の **111/219（50.68%）から R8 の162/219（73.97%）へ、23.29ポイント改善**しました。最新 R11 の限定検証では、既存メジャーのフィルターとその説明を対象にした **2問4条件すべてが一致**し、2件とも取得完了、内部エラーなしでした。この結果を再利用可能な指示と手順へ反映します。将来の全質問に対する精度保証や、全機能の受入完了とは扱いません。

Measured answer-content agreement improved from **111/219 (50.68%) to 162/219 (73.97%) in R8**, an increase of **23.29 percentage points**, for the matched conditions. The latest R11 targeted check passed **all four conditions across two questions**, covering existing measure filters and their explanations; both captures completed without internal errors. The workshop incorporates the reusable instructions and procedure supported by those observations. These results do not guarantee future answers or establish acceptance of every feature.

## 利用する資料 / Workshop materials

- [現行参加者資料 / Current participant materials](../current/README.md)
- [実測を反映した portable profile / Portable measured-contract profile](../../../workshop/v3.0.0-preview/data-agent/candidates/measured-contract-20261009/README.md)
- [精度の校正と資料の校正手順 / Calibration and proofreading procedure](calibration-and-proofreading.md)
- [公開用の集計と証跡ハッシュ / Public aggregates and evidence hashes](result-20261010.json)
- [実測要約・校正手順 Word / Summary and procedure in Word](furusato-data-agent-tuning-20261010.docx)
- [実測要約・校正手順 日英HTML / Bilingual summary and procedure in HTML](furusato-data-agent-tuning-20261010.html)

公開用 JSON は集計と不変の証跡ハッシュだけを収録します。ケース本文、期待解答、実回答、native trace、認証情報、対象 Workspace のIDは含めません。ハッシュは私有証跡の照合用であり、その証跡が公開されていることを意味しません。

The public JSON contains aggregates and immutable evidence hashes. It omits case text, expected answers, actual answers, native traces, authentication information and deployment Workspace IDs. Hashes support authorized reconciliation with retained private evidence; they do not make that evidence publicly available.

## 測定結果 / Measured results

すべて、固定条件と実回答・ソース結果を照合した **Codex による補足内容判定**です。独立した人間の sign-off はありません。native 実行の厳格な判定は別に保持しています。

All rows are **supplemental content judgments by Codex** against fixed conditions, actual answers and source results. There is no independent human sign-off. Strict native-execution judgments remain separate.

| 対象 / Scope | 改善前 / Baseline | 実測した改善版 / Measured revision | 読み方 / Interpretation |
|---|---:|---:|---|
| 元10問を3回、各フェーズの適用条件 / Original ten questions, three repetitions, phase-specific applicable conditions | 125/243 (51.44%), NA 9 | R8: 192/252 (76.19%), FAIL 60 | 分母が異なる / Different denominators |
| 共通219条件 / Matched 219 conditions | 111/219 (50.68%), FAIL 108 | R8: 162/219 (73.97%), FAIL 57 | +23.29ポイント / +23.29 percentage points |
| 回帰19問38条件 / Regression: 19 questions, 38 conditions | PASS 17 / FAIL 18 / UNCLEAR 3 | R8: PASS 30 / FAIL 7 / UNCLEAR 1 | UNCLEARも分母に残す。44.74% → 78.95% / Keep UNCLEAR in the denominator |
| SQLの限定検証 / Targeted SQL check | 別フェーズ / Separate phase | R9: 19/19; 4 questions | 1 capture は証拠不完全 / One capture retained as evidence-incomplete |
| 時刻とフィルター説明 / Targeted time and filter-explanation check | 別フェーズ / Separate phase | R10: 4/6; 3 questions | FAIL 2、証拠不完全1件を保持 / Two FAIL conditions and one evidence-incomplete capture retained |
| 実在メジャーの内部フィルター説明 / Existing measure filter explanation | 別フェーズ / Separate phase | R11: 4/4; 2 questions | 2 captures completed、内部エラーなし / Both captures completed without internal errors |

共通条件の比較では、確認質問分岐により改善前で NA だった9条件と、承認済みソースの利用可能性が変わった24条件を、両フェーズから同じように除きました。元の252条件の判定は変更していません。採点前提が変わった条件を、正答率の改善として数えていません。

The matched comparison excludes the same nine baseline clarification-branch NA conditions and 24 conditions whose approved-source availability premise changed, from both phases. The original 252 judgments remain unchanged. A changed scoring premise is not counted as an accuracy improvement.

改善前の取得条件は、初期の HTTP 120秒／capture 600秒と、未着手枠の HTTP 300秒／capture 900秒が混在します。R8 は300秒／900秒です。業務データは同じですが、内容の改善と取得可能性の改善を分離した因果効果とは断定できません。異なる未使用問題群の結果は別群の測定であり、対応のある改善率として扱いません。

Baseline collection mixed HTTP 120-second / capture 600-second settings with HTTP 300-second / capture 900-second settings for previously unstarted slots. R8 used 300/900 seconds. Business data was unchanged, but content improvement cannot be causally isolated from collection availability. Results for disjoint previously unused question sets are separate measurements, not a paired improvement estimate.

R8 は登録51枠について51 POSTと51 terminal Responseを保存し、native失敗や証拠不完全を持つ19枠を保持しています。Response が completed でも内部クエリの成功を意味しません。R9・R10・R11 はそれぞれ別の限定検証です。**最新 R11 で全51枠を再評価していません**。R8 の全体スコアを R11 の全体スコアと読み替えません。

R8 retained 51 POSTs and 51 terminal Responses for its 51 registered slots, including 19 slots with native failures or incomplete evidence. A completed Response does not establish successful internal queries. R9, R10 and R11 are separate targeted checks. **The latest R11 has not been retested across all 51 slots.** R8's overall scores are not R11 overall scores.

## 再利用する対策 / Reusable changes

| 観測した問題 / Observed problem | Workshopで適用する対策 / Workshop change |
|---|---|
| ソース・粒度・データ期間の混同 / Mixed sources, grain and time periods | ソース契約、必要なビューと品質テーブルの選択、raw／accepted／Gold、静的ラベルと暦年の区別 / Source contracts, required views and quality-table selections, separate raw/accepted/Gold and static labels/calendar years |
| SQL識別子・名前検索・順位の絞り込み / SQL identifiers, name lookups and ranking scope | 識別子・別名の引用、実在する名称dimension、集計と順位で同じ明細filter / Quote identifiers and aliases, use real name dimensions, apply identical fact filters to totals and rankings |
| 12時間表記の転記・区間比較 / Twelve-hour time transcription and interval comparison | ソース結果のUTC ISOを使用し、AM/PMとUTC/JSTを明示、実UTC区間で比較 / Use source-returned UTC ISO values, make AM/PM and UTC/JST explicit, compare actual UTC intervals |
| BLANKの理由と内部KEEPFILTERSの説明不足 / Missing explanation of BLANK and internal KEEPFILTERS | 選択済みソースの実在TMDL定義を引用し、内部KEEPFILTERSと外側filterの交差を説明 / Quote existing selected-source TMDL definitions and explain the intersection of internal KEEPFILTERS with outer filters |

指示には、実在するソース契約・スキーマ・メジャー定義を用います。テストの解答、未使用問題、特定の期待数値を埋め込みません。portable profile は導入先の native schema、SQL metadata、TMDL を確認して Draft を生成します。新しい導入先の公開・実回答の検証は[校正手順](calibration-and-proofreading.md)で別途行います。

Instructions use actual source contracts, schemas and measure definitions. They do not embed test answers, unused questions or case-specific expected values. The portable profile verifies the destination native schema, SQL metadata and TMDL before compiling a Draft. Publication and actual-answer validation in a new destination follow the separate [calibration procedure](calibration-and-proofreading.md).

## 残る範囲 / Remaining limitations

- Gen2 Ontology の Data Agent consumer は API version unsupported を返す経路が残ります。直接 Graph/GQL の成功はこの経路の成功を代替しません。
- Semantic Model の金額列を表示・選択した後の試験でも、Data Agent の native DAX schema に金額列が出ず、金額条件の実行結果を取得できませんでした。R11 の限定検証には schema 取得がなく、この経路の解決確認はできていません。
- native Ontology Time Series／Metrics、Manage graph UI の projection、Report のブラウザ描画、Activator の自動配信は未検証または未設定です。
- サービスの content block と必要なデータ制限の説明不足は、元の失敗として保持しています。

The Data Agent Gen2 Ontology consumer retains an unsupported-API-version route; direct Graph/GQL success does not validate it. Even after making the amount column visible and selected, the tested Agent route omitted that column from its native DAX schema and produced no executed amount-filtered result. R11 did not retrieve the schema, so resolution of that route is unconfirmed. Native Ontology Time Series/Metrics, Manage graph UI projection, Report browser rendering and Activator automatic delivery remain unverified or unconfigured. Service content blocks and missing data-limit explanations remain recorded failures.

元の版・評価・失敗記録は保持します。資料の整合性チェック成功、mainへのマージ、Draftの生成は、これらの未解決事項の合格判定を変更しません。

Previous editions, evaluations and failure records remain intact. Passing document-consistency checks, merging main or compiling a Draft does not change acceptance of these unresolved features.

## 別冊の再生成 / Rebuild this report

[専用builder](../../../tools/docs/build_measured_tuning_report.py)は、このREADME、校正手順、公開集計JSONを単一の入力組合せとして検証し、別日付Word・HTMLと構造検証JSONを生成します。公開集計の再採点やクラウド操作は行いません。出力先には新しい私有stageを指定します。`PATH_TO_FRESH_PRIVATE_STAGE`を実際の新規ディレクトリに置き換えて実行します。描画確認の結果は公開された`artifact-validation.json`に記録します。

The [dedicated builder](../../../tools/docs/build_measured_tuning_report.py) validates this README, the procedure and public counts JSON as one input set, then generates the separately dated Word/HTML pair and structural validation JSON. It neither regrades the study nor calls the cloud. Replace `PATH_TO_FRESH_PRIVATE_STAGE` with a fresh private staging directory. Rendering checks are recorded in the published `artifact-validation.json`.

```sh
python tools/docs/build_measured_tuning_report.py \
  --input-dir docs/v3.0.0/tuning-20261010 \
  --out PATH_TO_FRESH_PRIVATE_STAGE
```
