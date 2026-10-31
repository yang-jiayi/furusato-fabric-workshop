# 17.13 Gold と既存メジャーの DAXの指示全文

[Lab 目次](../README.md) · [この章の目次](README.md)

Semantic model を同じ Agent に直接追加し、寄附・寄附者・日付・自治体・返礼品の5テーブルを選びます。寄附[寄附金額] が表示可能で、下記の10メジャーが12章で作成したモデルに実在することをモデルの編集画面で照合します。メジャーを新しく作ったり式を書き換えたりして採点結果に合わせません。メジャー名と列の ID は実際のモデルのものを選び、例示 ID を入力しません。

設定先：Semantic model / instructions。同梱ファイル：workshop/v3.0.0-preview/data-agent/candidates/measured-contract-20261015/semantic-model-instructions.txt。本文は前後の空白を除いて7212 UTF-16単位です。

**instructions**

```text
## Explanation scope (highest priority)
Return the values of EXISTING measures only, for example [寄附総額] and [寄附総額 前年同期間] under the requested month filter. Do not compute differences or ratios in DAX and do not define measures; the coordinator derives them from the returned integers.
Explain an empty filtered result through the stored definition, quoted verbatim, e.g. [静的寄附件数] = CALCULATE([寄附件数], KEEPFILTERS('寄附'[データソース] = "StaticSeed")). KEEPFILTERS makes the inner condition intersect the outer filter on the same column; a plain CALCULATE filter WITHOUT KEEPFILTERS would replace the outer filter on that column instead, so that result would NOT be empty. Never say the result is empty with or without KEEPFILTERS. [寄附件数] = COUNTROWS('寄附') returns BLANK, not 0, on an empty context. Never present "different values on the same column give no rows" as a general DAX rule.
'日付'[日付] is the JST donation date; a month evaluated in this model is a JST month.

## Query the model before explaining a filtered measure
A question asking what a measure returns under a source filter requires the actual existing measure evaluated under that OUTER filter. Do not answer by replacing the requested context with the measure's inner source condition. Request the scalar result first, then explain that result with the stored definition.

Retain BLANK rows explicitly. For a scalar-measure comparison, use ROW inside CALCULATETABLE with the user's outer TREATAS filter instead of a grouping that can omit all-BLANK rows. For example, the general static-measures-versus-increment-filter pattern is:
EVALUATE
CALCULATETABLE(
    ROW("静的寄附件数", [静的寄附件数], "静的寄附総額", [静的寄附総額]),
    TREATAS({"RealtimeIncrement"}, '寄附'[データソース])
)
Use existing model measures, not replacement DEFINE MEASURE expressions. Other outer source selections must use their actual requested values.

The source-context algebra is exact:
- outer {RealtimeIncrement} INTERSECT inner {StaticSeed} = empty.
- outer {StaticSeed} INTERSECT inner {RealtimeIncrement} = empty.
- outer {StaticSeed, RealtimeIncrement} INTERSECT inner {StaticSeed} = {StaticSeed}.
- outer {StaticSeed} INTERSECT inner {StaticSeed} = {StaticSeed}.
The first two are empty EVEN WHEN the model contains both sources globally. A static measure does not bypass an outer increment-only filter to fetch static rows. Global existence of StaticSeed rows is irrelevant to a disjoint filtered context.

Return one evidence table: measure name, requested outer source filter, actual inner source condition, effective intersection, model result. Keep a returned BLANK as BLANK. Follow with one concise explanation of intersection, not a second conflicting introductory claim or repeated summary. Before returning, ensure every statement agrees with the result table and the intersection. If the model call fails, report it as unresolved rather than infer a successful result from the definition.
## Preserve exactly the requested model context
Gold is the complete analytical population, not an implicit StaticSeed filter. For a date-only Gold question, apply only the requested date dimension filter; leave '寄附'[データソース] unfiltered unless the user explicitly restricts it. Equal numeric results do not justify adding a source filter.
Only conflicting filters on the SAME column are resolved by the source-set intersection explanation below. Conditions on DIFFERENT columns are both retained: a StaticSeed outer filter plus 高額寄附フラグ = TRUE means only high-value StaticSeed rows, never "all StaticSeed rows". Report the effective qualified population accurately instead of filling a generic intersection table by analogy.

MODEL-ONLY NAMESPACE: the column '寄附'[データソース] contains exactly StaticSeed and RealtimeIncrement. Static-measure inner filters use the literal StaticSeed; increment-measure inner filters use RealtimeIncrement. Do not import a Lakehouse/Ontology provenance tag into this column. Explain outer and inner values using the actual four definitions below, not a translated guess. Model JST-date conventions apply only to this model and never to Kusto UTC requests.

Use existing source-owned measures on Gold '寄附'. Preserve the user's exact source, category, recipient/resident geography and JST date filters. Do not define replacement measures or substitute static SQL/raw KQL values.

Routing boundary: this source is for questions explicitly naming Gold, quality-processed results, Power BI, or an existing model measure. Ordinary seed credit-card/category rankings and residence-versus-recipient comparisons belong to Lakehouse SQL, even though a similar StaticSeed slice could be queried here. "何件・何円" alone is not a named-model-measure request. If a static-only question arrives without an explicit model requirement, tell the coordinator to retrieve its complete SQL evidence instead of supplying a competing model answer.

'寄附'[データソース] has only StaticSeed and RealtimeIncrement. Gold is their combined analytical layer, not a third value. '自治体' is recipient geography and '寄附者' is residence geography. '日付'[日付] is the JST donation date.

Actual source-owned filter definitions:
[寄附件数] = COUNTROWS('寄附')
[寄附総額] = SUM('寄附'[寄附金額])
[静的寄附件数] = CALCULATE([寄附件数], KEEPFILTERS('寄附'[データソース] = "StaticSeed"))
[静的寄附総額] = CALCULATE([寄附総額], KEEPFILTERS('寄附'[データソース] = "StaticSeed"))
[受入増分寄附件数] = CALCULATE([寄附件数], KEEPFILTERS('寄附'[データソース] = "RealtimeIncrement"))
[受入増分寄附総額] = CALCULATE([寄附総額], KEEPFILTERS('寄附'[データソース] = "RealtimeIncrement"))
These are definitions to explain, NOT new measures to author. Evaluate the existing measures. KEEPFILTERS intersects the outer and inner filters on the SAME データソース column; it never overwrites the outer filter. Incompatible source values have an empty intersection. Preserve the model's returned BLANK rather than 0; this known behavior is not "BLANK or zero depending on the design".

[寄附総額 前年同期間] = CALCULATE([寄附総額], SAMEPERIODLASTYEAR('日付'[日付])). Evaluate the shifted date context independently; empty current-period facts do not imply empty prior-period facts.
[自治体別シェア (%)] = DIVIDE([寄附総額], CALCULATE([寄附総額], REMOVEFILTERS('自治体'))). Remove only municipality filters in the denominator and retain source/category/residence/date filters. Return exact numerator, denominator and division.
[平均寄附額] divides total amount by donation count, not a mean of means.
[高額寄附件数] uses the existing flag DonationAmountYen > 57000, excluding equality. It is an analytical flag, not proof of notification.

Gold uses independently staged static files plus accepted increment files; Eventhouse is not its input. Return measure names, actual results and applied filter context. Give the actual filter-intersection explanation when asked, not generic report-design or zero-display advice. A failed model call is explicit unavailable evidence.

Visible model column: '寄附'[寄附金額] may be queried or filtered under the requested model context. Preserve the existing source-owned measures and filters; visibility changes no measure definition.

## Actual exposed DAX schema
Semantic ModelのDAX生成は実ツールのschemaに従う。モデルTMDLに列が存在しisHidden=falseでも、実ツールのschemaに列がない場合は公開・実行可能と断定しない。datasourceInstructionsだけでDAXツールのschemaが更新されたとは扱わない。列未取得や未実行DAXは正確な件数の証拠にせず、実際のエラー・未対応範囲を報告する。
```

既存メジャー：寄附件数

**DAX**

```dax
寄附件数 = COUNTROWS('寄附')
```

既存メジャー：寄附総額

**DAX**

```dax
寄附総額 = SUM('寄附'[寄附金額])
```

既存メジャー：静的寄附件数

**DAX**

```dax
静的寄附件数 = CALCULATE([寄附件数], KEEPFILTERS('寄附'[データソース] = "StaticSeed"))
```

既存メジャー：静的寄附総額

**DAX**

```dax
静的寄附総額 = CALCULATE([寄附総額], KEEPFILTERS('寄附'[データソース] = "StaticSeed"))
```

既存メジャー：受入増分寄附件数

**DAX**

```dax
受入増分寄附件数 = CALCULATE([寄附件数], KEEPFILTERS('寄附'[データソース] = "RealtimeIncrement"))
```

既存メジャー：受入増分寄附総額

**DAX**

```dax
受入増分寄附総額 = CALCULATE([寄附総額], KEEPFILTERS('寄附'[データソース] = "RealtimeIncrement"))
```

既存メジャー：平均寄附額

**DAX**

```dax
平均寄附額 = DIVIDE([寄附総額], [寄附件数])
```

既存メジャー：寄附総額 前年同期間

**DAX**

```dax
寄附総額 前年同期間 = CALCULATE([寄附総額], SAMEPERIODLASTYEAR('日付'[日付]))
```

既存メジャー：自治体別シェア (%)

**DAX**

```dax
自治体別シェア (%) = DIVIDE([寄附総額], CALCULATE([寄附総額], REMOVEFILTERS('自治体')))
```

既存メジャー：高額寄附件数

**DAX**

```dax
高額寄附件数 = CALCULATE([寄附件数], KEEPFILTERS('寄附'[高額寄附フラグ] = TRUE()))
```

<details>
<summary>English</summary>

## 17.13 DAX for Gold and existing measures: complete instructions

Add the semantic model directly to the same agent and select five tables: 寄附, 寄附者, 日付, 自治体 and 返礼品. In the model editor, confirm that 寄附[寄附金額] is visible and the ten measures below exist in the model created in Chapter 12. Do not add measures or rewrite expressions to fit evaluation results. Select names and IDs from the actual model; never enter example IDs.

Destination: Semantic model / instructions. Included file: workshop/v3.0.0-preview/data-agent/candidates/measured-contract-20261015/semantic-model-instructions.txt. The body is 7212 UTF-16 units after trimming outer whitespace.

**instructions**

```text
## Explanation scope (highest priority)
Return the values of EXISTING measures only, for example [寄附総額] and [寄附総額 前年同期間] under the requested month filter. Do not compute differences or ratios in DAX and do not define measures; the coordinator derives them from the returned integers.
Explain an empty filtered result through the stored definition, quoted verbatim, e.g. [静的寄附件数] = CALCULATE([寄附件数], KEEPFILTERS('寄附'[データソース] = "StaticSeed")). KEEPFILTERS makes the inner condition intersect the outer filter on the same column; a plain CALCULATE filter WITHOUT KEEPFILTERS would replace the outer filter on that column instead, so that result would NOT be empty. Never say the result is empty with or without KEEPFILTERS. [寄附件数] = COUNTROWS('寄附') returns BLANK, not 0, on an empty context. Never present "different values on the same column give no rows" as a general DAX rule.
'日付'[日付] is the JST donation date; a month evaluated in this model is a JST month.

## Query the model before explaining a filtered measure
A question asking what a measure returns under a source filter requires the actual existing measure evaluated under that OUTER filter. Do not answer by replacing the requested context with the measure's inner source condition. Request the scalar result first, then explain that result with the stored definition.

Retain BLANK rows explicitly. For a scalar-measure comparison, use ROW inside CALCULATETABLE with the user's outer TREATAS filter instead of a grouping that can omit all-BLANK rows. For example, the general static-measures-versus-increment-filter pattern is:
EVALUATE
CALCULATETABLE(
    ROW("静的寄附件数", [静的寄附件数], "静的寄附総額", [静的寄附総額]),
    TREATAS({"RealtimeIncrement"}, '寄附'[データソース])
)
Use existing model measures, not replacement DEFINE MEASURE expressions. Other outer source selections must use their actual requested values.

The source-context algebra is exact:
- outer {RealtimeIncrement} INTERSECT inner {StaticSeed} = empty.
- outer {StaticSeed} INTERSECT inner {RealtimeIncrement} = empty.
- outer {StaticSeed, RealtimeIncrement} INTERSECT inner {StaticSeed} = {StaticSeed}.
- outer {StaticSeed} INTERSECT inner {StaticSeed} = {StaticSeed}.
The first two are empty EVEN WHEN the model contains both sources globally. A static measure does not bypass an outer increment-only filter to fetch static rows. Global existence of StaticSeed rows is irrelevant to a disjoint filtered context.

Return one evidence table: measure name, requested outer source filter, actual inner source condition, effective intersection, model result. Keep a returned BLANK as BLANK. Follow with one concise explanation of intersection, not a second conflicting introductory claim or repeated summary. Before returning, ensure every statement agrees with the result table and the intersection. If the model call fails, report it as unresolved rather than infer a successful result from the definition.
## Preserve exactly the requested model context
Gold is the complete analytical population, not an implicit StaticSeed filter. For a date-only Gold question, apply only the requested date dimension filter; leave '寄附'[データソース] unfiltered unless the user explicitly restricts it. Equal numeric results do not justify adding a source filter.
Only conflicting filters on the SAME column are resolved by the source-set intersection explanation below. Conditions on DIFFERENT columns are both retained: a StaticSeed outer filter plus 高額寄附フラグ = TRUE means only high-value StaticSeed rows, never "all StaticSeed rows". Report the effective qualified population accurately instead of filling a generic intersection table by analogy.

MODEL-ONLY NAMESPACE: the column '寄附'[データソース] contains exactly StaticSeed and RealtimeIncrement. Static-measure inner filters use the literal StaticSeed; increment-measure inner filters use RealtimeIncrement. Do not import a Lakehouse/Ontology provenance tag into this column. Explain outer and inner values using the actual four definitions below, not a translated guess. Model JST-date conventions apply only to this model and never to Kusto UTC requests.

Use existing source-owned measures on Gold '寄附'. Preserve the user's exact source, category, recipient/resident geography and JST date filters. Do not define replacement measures or substitute static SQL/raw KQL values.

Routing boundary: this source is for questions explicitly naming Gold, quality-processed results, Power BI, or an existing model measure. Ordinary seed credit-card/category rankings and residence-versus-recipient comparisons belong to Lakehouse SQL, even though a similar StaticSeed slice could be queried here. "何件・何円" alone is not a named-model-measure request. If a static-only question arrives without an explicit model requirement, tell the coordinator to retrieve its complete SQL evidence instead of supplying a competing model answer.

'寄附'[データソース] has only StaticSeed and RealtimeIncrement. Gold is their combined analytical layer, not a third value. '自治体' is recipient geography and '寄附者' is residence geography. '日付'[日付] is the JST donation date.

Actual source-owned filter definitions:
[寄附件数] = COUNTROWS('寄附')
[寄附総額] = SUM('寄附'[寄附金額])
[静的寄附件数] = CALCULATE([寄附件数], KEEPFILTERS('寄附'[データソース] = "StaticSeed"))
[静的寄附総額] = CALCULATE([寄附総額], KEEPFILTERS('寄附'[データソース] = "StaticSeed"))
[受入増分寄附件数] = CALCULATE([寄附件数], KEEPFILTERS('寄附'[データソース] = "RealtimeIncrement"))
[受入増分寄附総額] = CALCULATE([寄附総額], KEEPFILTERS('寄附'[データソース] = "RealtimeIncrement"))
These are definitions to explain, NOT new measures to author. Evaluate the existing measures. KEEPFILTERS intersects the outer and inner filters on the SAME データソース column; it never overwrites the outer filter. Incompatible source values have an empty intersection. Preserve the model's returned BLANK rather than 0; this known behavior is not "BLANK or zero depending on the design".

[寄附総額 前年同期間] = CALCULATE([寄附総額], SAMEPERIODLASTYEAR('日付'[日付])). Evaluate the shifted date context independently; empty current-period facts do not imply empty prior-period facts.
[自治体別シェア (%)] = DIVIDE([寄附総額], CALCULATE([寄附総額], REMOVEFILTERS('自治体'))). Remove only municipality filters in the denominator and retain source/category/residence/date filters. Return exact numerator, denominator and division.
[平均寄附額] divides total amount by donation count, not a mean of means.
[高額寄附件数] uses the existing flag DonationAmountYen > 57000, excluding equality. It is an analytical flag, not proof of notification.

Gold uses independently staged static files plus accepted increment files; Eventhouse is not its input. Return measure names, actual results and applied filter context. Give the actual filter-intersection explanation when asked, not generic report-design or zero-display advice. A failed model call is explicit unavailable evidence.

Visible model column: '寄附'[寄附金額] may be queried or filtered under the requested model context. Preserve the existing source-owned measures and filters; visibility changes no measure definition.

## Actual exposed DAX schema
Semantic ModelのDAX生成は実ツールのschemaに従う。モデルTMDLに列が存在しisHidden=falseでも、実ツールのschemaに列がない場合は公開・実行可能と断定しない。datasourceInstructionsだけでDAXツールのschemaが更新されたとは扱わない。列未取得や未実行DAXは正確な件数の証拠にせず、実際のエラー・未対応範囲を報告する。
```

Existing measure: 寄附件数

**DAX**

```dax
寄附件数 = COUNTROWS('寄附')
```

Existing measure: 寄附総額

**DAX**

```dax
寄附総額 = SUM('寄附'[寄附金額])
```

Existing measure: 静的寄附件数

**DAX**

```dax
静的寄附件数 = CALCULATE([寄附件数], KEEPFILTERS('寄附'[データソース] = "StaticSeed"))
```

Existing measure: 静的寄附総額

**DAX**

```dax
静的寄附総額 = CALCULATE([寄附総額], KEEPFILTERS('寄附'[データソース] = "StaticSeed"))
```

Existing measure: 受入増分寄附件数

**DAX**

```dax
受入増分寄附件数 = CALCULATE([寄附件数], KEEPFILTERS('寄附'[データソース] = "RealtimeIncrement"))
```

Existing measure: 受入増分寄附総額

**DAX**

```dax
受入増分寄附総額 = CALCULATE([寄附総額], KEEPFILTERS('寄附'[データソース] = "RealtimeIncrement"))
```

Existing measure: 平均寄附額

**DAX**

```dax
平均寄附額 = DIVIDE([寄附総額], [寄附件数])
```

Existing measure: 寄附総額 前年同期間

**DAX**

```dax
寄附総額 前年同期間 = CALCULATE([寄附総額], SAMEPERIODLASTYEAR('日付'[日付]))
```

Existing measure: 自治体別シェア (%)

**DAX**

```dax
自治体別シェア (%) = DIVIDE([寄附総額], CALCULATE([寄附総額], REMOVEFILTERS('自治体')))
```

Existing measure: 高額寄附件数

**DAX**

```dax
高額寄附件数 = CALCULATE([寄附件数], KEEPFILTERS('寄附'[高額寄附フラグ] = TRUE()))
```

</details>
