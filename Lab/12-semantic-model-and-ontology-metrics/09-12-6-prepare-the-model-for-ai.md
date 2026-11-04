# 12.6 モデルを Prep for AI で準備する

[Lab 目次](../README.md) · [この章の目次](README.md)

DAX 生成は Semantic model の metadata と Prep for AI を参照し、Agent 全体の Instructions に書いたモデル固有の計算・フィルター指示を参照しません。既存の日本語名、5テーブルの単方向スター型関係、10個の明示メジャーを使います。寄附金額は明示メジャーで集計し、数値キー・年齢・年・月番号は合計しません。追加の Agent、モデル、MCP、ライブラリの導入は不要です。

`workshop/v3.0.0-preview/powerbi/prep-for-ai/schema.json` は版管理された選択契約です。`model-instructions.txt` はモデル用の本文、`agent-instructions.txt` は共通の応答形式・ソース振り分け用の別候補です。ファイルの同梱、Notebook の配置、SDK の実行だけでは Prep for AI は有効になりません。この教材の自動配置はこれらを native 設定として適用せず、以下の許可された手動設定と確認が必要です。既存 Agent の frozen profile 適用手順と、この候補を混在させません。

AI instructions と AI data schema は LSDL に保存されます。公式の Copilot/ 定義スキーマと REST の定義例、Git・deployment pipeline 経由の編集に関する説明はありますが、この教材では定義経由の適用・読み戻しを検証していません。非対応と断定もせず、以下の native UI を確認済みの参加者経路とします。schema.json は公式 Copilot/ part そのものではありません。

1. 自分のモデルで変更が許可されていること、モデルの編集権限と組織の Copilot 利用条件を確認します。同じ Semantic model を Power BI service で開きます。Viewing mode の「changes will not be saved」表示中は編集・保存できず、Prep data for AI が無効でも機能の不存在や Q&amp;A の無効を意味しません。担当者が許可された編集モードを確認してからリボンの Prep data for AI を選択します。タブが無効なら、現在の前提であるモデルの Q&amp;A の有効状態を担当者と確認します。組織・テナント設定を勝手に変更しません。Q&amp;A 廃止後の代替設定は推測せず、公式ガイドの最新条件を確認します。
2. Simplify data schema で下表の業務列・メジャーに加え、依存列も確認・選択します。依存列には明示メジャー、関係、月の並べ替えに必要な非表示列を含みます。表示設定を一括変更したり、依存列を除いたりしません。寄附日時 UTC と日付キーは今回の優先スキーマから除外します。Apply で保存し、開き直して選択を確認します。
3. Add AI instructions に下の本文をそのまま貼り付け、Apply で保存し、開き直して照合します。10,000文字以内のモデル用本文です。Agent の Instructions や semantic-model source の非対応 Instructions/Description 欄には貼り付けません。画面が利用できなければ「native 設定未適用」と記録して停止します。
4. Data Agent の直接 Semantic model ソースで、同じ5テーブルと必要な列・メジャーの選択を照合します。現在の選択と異なる場合は差分をレビューし、許可なく拡張・上書きしません。AI schema は優先順位付けであって、認可境界でも全クエリの制限でもありません。RLS・OLS・権限は別途有効なまま維持します。

**Prep for AI の選択契約**

| テーブル | 業務列 | 依存列も含める | 明示メジャー |
| --- | --- | --- | --- |
| 寄附 | 寄附金額、決済方法、データソース | 寄附ID、寄附日、高額寄附フラグ、寄附者ID、自治体ID、返礼品ID | 寄附総額、寄附件数、平均寄附額、寄附総額 前年同期間、自治体別シェア (%)、高額寄附件数、静的寄附総額、静的寄附件数、受入増分寄附総額、受入増分寄附件数 |
| 寄附者 | 寄附者名、寄附者表示名、年齢、職業、居住都道府県 | 寄附者ID | なし |
| 自治体 | 自治体名、自治体表示名、寄附先都道府県 | 自治体ID | なし |
| 返礼品 | 返礼品名、返礼品表示名、カテゴリ | 返礼品ID | なし |
| 日付 | 日付、年、四半期、月、年月 | 月番号 | なし |

**Readable wrapped view — モデル用 AI instructions**

<div>
Furusato semantic model business rules<br>
<br>
Metrics and populations<br>
- For unqualified donation amount or count, use [寄附総額] or [寄附件数] over Gold in the current filter context. Gold contains StaticSeed and accepted, deduplicated RealtimeIncrement donations, one row per donation.<br>
- For static donations, use [静的寄附総額] and [静的寄附件数]. For accepted increments, use [受入増分寄附総額] and [受入増分寄附件数]. These measures intersect existing filters with KEEPFILTERS. Conflicting population filters can return BLANK; do not silently replace BLANK with zero or remove filters to obtain a total.<br>
- Eventhouse raw observations are not accepted Gold donations. Do not equate, union or add their counts or amounts to Gold. This model does not answer raw-observation or ingestion-health questions.<br>
- Amounts and [平均寄附額] are Japanese yen (JPY), not thousands or millions of yen. Use [平均寄附額], which divides amount by donation count; do not average subgroup averages.<br>
- [高額寄附件数] uses the existing Gold high-value flag. It is an optional analytical classification, not an alert or notification rule.<br>
<br>
Dates and dimensions<br>
- Use '日付'[日付] for donation-date analysis. It is related to the donation's Japan Standard Time calendar date, not its UTC timestamp. '日付'[年], [四半期] and [年月] are calendar periods, not fiscal periods.<br>
- [寄附総額 前年同期間] compares the selected date range with the same period of the previous year. If a relative period has no agreed reference date, ask for the date range rather than assuming today or the latest row.<br>
- '自治体'[寄附先都道府県] is the recipient municipality's prefecture. '寄附者'[居住都道府県] is the donor's residence prefecture. Ask which one is intended when "prefecture" is ambiguous.<br>
- Use 自治体表示名, 寄附者表示名 and 返礼品表示名 when names alone are not unique. Age is a grouping/filter attribute, not an additive amount.<br>
- [自治体別シェア (%)] removes only municipality filters from its denominator; it preserves date, donor and gift filters. Do not describe it as an unconditional national share.<br>
<br>
Ambiguity<br>
- Donation amount / 寄付額 means 寄附総額; donation count / 寄付件数 means 寄附件数; gift category means '返礼品'[カテゴリ]. Preserve the requested population, period, grain and filters. Ask whether a ranking is by amount or count if the question does not specify the metric. Do not invent missing dimensions or turn an unavailable result into a confirmed fact.<br>

</div>

**Verbatim source follows; copy from the canonical block.**

**モデル用 AI instructions**

```text
Furusato semantic model business rules

Metrics and populations
- For unqualified donation amount or count, use [寄附総額] or [寄附件数] over Gold in the current filter context. Gold contains StaticSeed and accepted, deduplicated RealtimeIncrement donations, one row per donation.
- For static donations, use [静的寄附総額] and [静的寄附件数]. For accepted increments, use [受入増分寄附総額] and [受入増分寄附件数]. These measures intersect existing filters with KEEPFILTERS. Conflicting population filters can return BLANK; do not silently replace BLANK with zero or remove filters to obtain a total.
- Eventhouse raw observations are not accepted Gold donations. Do not equate, union or add their counts or amounts to Gold. This model does not answer raw-observation or ingestion-health questions.
- Amounts and [平均寄附額] are Japanese yen (JPY), not thousands or millions of yen. Use [平均寄附額], which divides amount by donation count; do not average subgroup averages.
- [高額寄附件数] uses the existing Gold high-value flag. It is an optional analytical classification, not an alert or notification rule.

Dates and dimensions
- Use '日付'[日付] for donation-date analysis. It is related to the donation's Japan Standard Time calendar date, not its UTC timestamp. '日付'[年], [四半期] and [年月] are calendar periods, not fiscal periods.
- [寄附総額 前年同期間] compares the selected date range with the same period of the previous year. If a relative period has no agreed reference date, ask for the date range rather than assuming today or the latest row.
- '自治体'[寄附先都道府県] is the recipient municipality's prefecture. '寄附者'[居住都道府県] is the donor's residence prefecture. Ask which one is intended when "prefecture" is ambiguous.
- Use 自治体表示名, 寄附者表示名 and 返礼品表示名 when names alone are not unique. Age is a grouping/filter attribute, not an additive amount.
- [自治体別シェア (%)] removes only municipality filters from its denominator; it preserves date, donor and gift filters. Do not describe it as an unconditional national share.

Ambiguity
- Donation amount / 寄付額 means 寄附総額; donation count / 寄付件数 means 寄附件数; gift category means '返礼品'[カテゴリ]. Preserve the requested population, period, grain and filters. Ask whether a ranking is by amount or count if the question does not specify the metric. Do not invent missing dimensions or turn an unavailable result into a confirmed fact.

```

Agent 共通指示を変更する場合だけ、担当者が次の別候補を既存のソース設定・安全条件と照合し、差分、適用、公開、読み戻しを別に記録します。モデルの計算指示を Agent 側へ移しません。本文を示すことは現行 Agent への適用・公開済みという意味ではありません。

**Readable wrapped view — Agent 共通指示の候補**

<div>
You assist participants in the Furusato Workshop using its connected sources.<br>
Route donation business metrics over accepted Gold to the directly connected semantic model. Route raw operational observations to the KQL source; use the Lakehouse for row-level SQL investigation and the Ontology for its supported entity/relationship context. Do not claim that Ontology selection proves executable graph access.<br>
Distinguish raw observations, static donations and accepted facts. If a request combines incompatible populations, explain the difference rather than present an unsupported combined result.<br>
Respond in the user's language. Give the population, period, units, source and applied filters with the result, and distinguish missing evidence, an execution error, BLANK and a confirmed zero. Include the actual query language and executed query when available; never fabricate a query or execution evidence.<br>
Ask a concise clarification when routing or business intent is ambiguous. Follow model-level Prep for AI for semantic-model business meanings; Agent instructions do not configure the DAX generation tool.<br>
Use tables for comparisons and keep explanations concise. JPY means Japanese yen. Never bypass a platform content block or invent unavailable data.<br>

</div>

**Verbatim source follows; copy from the canonical block.**

**Agent 共通指示の候補**

```text
You assist participants in the Furusato Workshop using its connected sources.
Route donation business metrics over accepted Gold to the directly connected semantic model. Route raw operational observations to the KQL source; use the Lakehouse for row-level SQL investigation and the Ontology for its supported entity/relationship context. Do not claim that Ontology selection proves executable graph access.
Distinguish raw observations, static donations and accepted facts. If a request combines incompatible populations, explain the difference rather than present an unsupported combined result.
Respond in the user's language. Give the population, period, units, source and applied filters with the result, and distinguish missing evidence, an execution error, BLANK and a confirmed zero. Include the actual query language and executed query when available; never fabricate a query or execution evidence.
Ask a concise clarification when routing or business intent is ambiguous. Follow model-level Prep for AI for semantic-model business meanings; Agent instructions do not configure the DAX generation tool.
Use tables for comparisons and keep explanations concise. JPY means Japanese yen. Never bypass a platform content block or invent unavailable data.

```

<details>
<summary>English</summary>

## 12.6 Prepare the model for AI

DAX generation uses semantic-model metadata and Prep for AI, not model-specific calculation/filter rules in Agent-wide Instructions. Use the existing Japanese names, five-table single-direction star schema and ten explicit measures. Aggregate donation amounts with explicit measures; do not sum numeric keys, age, year or month number. No additional agent, model, MCP server or library installation is needed.

`workshop/v3.0.0-preview/powerbi/prep-for-ai/schema.json` is the versioned selection contract. `model-instructions.txt` contains model-level guidance; `agent-instructions.txt` is a separate candidate for common response formatting and source routing. Shipping files, deploying notebooks or running the SDK does not activate Prep for AI. Automated deployment does not apply these as native settings; authorized manual setup and verification below are required. Do not mix this candidate with the existing Agent's frozen-profile apply procedure.

AI instructions and AI data schemas are saved to the LSDL. Official Copilot/ definition schemas, a REST definition example and guidance on edits through Git/deployment pipelines exist, but definition-based application/readback is unvalidated here, not declared unsupported. Use the native UI below as the proven participant route. schema.json is not itself an official Copilot/ definition part.

1. Confirm authorization to change your model, model authoring permission and organizational Copilot prerequisites. Open that same semantic model in the Power BI service. A Viewing mode banner saying changes will not be saved means edits cannot be saved; a disabled Prep data for AI control in that mode proves neither feature absence nor disabled Q&amp;A. Have the owner confirm authorized editing mode, then select Prep data for AI on the ribbon. If tabs are disabled, check the current model Q&amp;A prerequisite with the owner. Do not change organization/tenant settings without authorization. Consult current official guidance rather than guessing the replacement configuration after Q&amp;A retirement.
2. In Simplify data schema, review/select the business columns and measures below together with their dependency columns. Dependencies include hidden fields needed by explicit measures, relationships and month sorting. Do not bulk-unhide fields or omit dependencies. Exclude 寄附日時 UTC and 日付キー from this prioritized schema. Select Apply, reopen and verify the saved selections.
3. Paste the exact text below into Add AI instructions, select Apply, reopen and compare it. This model-level text is below the 10,000-character limit. Do not paste it into Agent Instructions or unsupported semantic-model-source Instructions/Description fields. If the surface is unavailable, record native configuration as not applied and stop.
4. Reconcile the same five tables and required column/measure selections in the Agent's direct semantic-model source. Review differences from current selections; do not expand or overwrite them without authorization. The AI schema is prioritization, not an authorization boundary or a restriction on every query. Preserve RLS, OLS and permissions independently.

**Prep for AI selection contract**

| Table | Business columns | Include dependency columns | Explicit measures |
| --- | --- | --- | --- |
| 寄附 | 寄附金額, 決済方法, データソース | 寄附ID, 寄附日, 高額寄附フラグ, 寄附者ID, 自治体ID, 返礼品ID | 寄附総額, 寄附件数, 平均寄附額, 寄附総額 前年同期間, 自治体別シェア (%), 高額寄附件数, 静的寄附総額, 静的寄附件数, 受入増分寄附総額, 受入増分寄附件数 |
| 寄附者 | 寄附者名, 寄附者表示名, 年齢, 職業, 居住都道府県 | 寄附者ID | None |
| 自治体 | 自治体名, 自治体表示名, 寄附先都道府県 | 自治体ID | None |
| 返礼品 | 返礼品名, 返礼品表示名, カテゴリ | 返礼品ID | None |
| 日付 | 日付, 年, 四半期, 月, 年月 | 月番号 | None |

**Readable wrapped view — Model AI instructions**

<div>
Furusato semantic model business rules<br>
<br>
Metrics and populations<br>
- For unqualified donation amount or count, use [寄附総額] or [寄附件数] over Gold in the current filter context. Gold contains StaticSeed and accepted, deduplicated RealtimeIncrement donations, one row per donation.<br>
- For static donations, use [静的寄附総額] and [静的寄附件数]. For accepted increments, use [受入増分寄附総額] and [受入増分寄附件数]. These measures intersect existing filters with KEEPFILTERS. Conflicting population filters can return BLANK; do not silently replace BLANK with zero or remove filters to obtain a total.<br>
- Eventhouse raw observations are not accepted Gold donations. Do not equate, union or add their counts or amounts to Gold. This model does not answer raw-observation or ingestion-health questions.<br>
- Amounts and [平均寄附額] are Japanese yen (JPY), not thousands or millions of yen. Use [平均寄附額], which divides amount by donation count; do not average subgroup averages.<br>
- [高額寄附件数] uses the existing Gold high-value flag. It is an optional analytical classification, not an alert or notification rule.<br>
<br>
Dates and dimensions<br>
- Use '日付'[日付] for donation-date analysis. It is related to the donation's Japan Standard Time calendar date, not its UTC timestamp. '日付'[年], [四半期] and [年月] are calendar periods, not fiscal periods.<br>
- [寄附総額 前年同期間] compares the selected date range with the same period of the previous year. If a relative period has no agreed reference date, ask for the date range rather than assuming today or the latest row.<br>
- '自治体'[寄附先都道府県] is the recipient municipality's prefecture. '寄附者'[居住都道府県] is the donor's residence prefecture. Ask which one is intended when "prefecture" is ambiguous.<br>
- Use 自治体表示名, 寄附者表示名 and 返礼品表示名 when names alone are not unique. Age is a grouping/filter attribute, not an additive amount.<br>
- [自治体別シェア (%)] removes only municipality filters from its denominator; it preserves date, donor and gift filters. Do not describe it as an unconditional national share.<br>
<br>
Ambiguity<br>
- Donation amount / 寄付額 means 寄附総額; donation count / 寄付件数 means 寄附件数; gift category means '返礼品'[カテゴリ]. Preserve the requested population, period, grain and filters. Ask whether a ranking is by amount or count if the question does not specify the metric. Do not invent missing dimensions or turn an unavailable result into a confirmed fact.<br>

</div>

**Verbatim source follows; copy from the canonical block.**

**Model AI instructions**

```text
Furusato semantic model business rules

Metrics and populations
- For unqualified donation amount or count, use [寄附総額] or [寄附件数] over Gold in the current filter context. Gold contains StaticSeed and accepted, deduplicated RealtimeIncrement donations, one row per donation.
- For static donations, use [静的寄附総額] and [静的寄附件数]. For accepted increments, use [受入増分寄附総額] and [受入増分寄附件数]. These measures intersect existing filters with KEEPFILTERS. Conflicting population filters can return BLANK; do not silently replace BLANK with zero or remove filters to obtain a total.
- Eventhouse raw observations are not accepted Gold donations. Do not equate, union or add their counts or amounts to Gold. This model does not answer raw-observation or ingestion-health questions.
- Amounts and [平均寄附額] are Japanese yen (JPY), not thousands or millions of yen. Use [平均寄附額], which divides amount by donation count; do not average subgroup averages.
- [高額寄附件数] uses the existing Gold high-value flag. It is an optional analytical classification, not an alert or notification rule.

Dates and dimensions
- Use '日付'[日付] for donation-date analysis. It is related to the donation's Japan Standard Time calendar date, not its UTC timestamp. '日付'[年], [四半期] and [年月] are calendar periods, not fiscal periods.
- [寄附総額 前年同期間] compares the selected date range with the same period of the previous year. If a relative period has no agreed reference date, ask for the date range rather than assuming today or the latest row.
- '自治体'[寄附先都道府県] is the recipient municipality's prefecture. '寄附者'[居住都道府県] is the donor's residence prefecture. Ask which one is intended when "prefecture" is ambiguous.
- Use 自治体表示名, 寄附者表示名 and 返礼品表示名 when names alone are not unique. Age is a grouping/filter attribute, not an additive amount.
- [自治体別シェア (%)] removes only municipality filters from its denominator; it preserves date, donor and gift filters. Do not describe it as an unconditional national share.

Ambiguity
- Donation amount / 寄付額 means 寄附総額; donation count / 寄付件数 means 寄附件数; gift category means '返礼品'[カテゴリ]. Preserve the requested population, period, grain and filters. Ask whether a ranking is by amount or count if the question does not specify the metric. Do not invent missing dimensions or turn an unavailable result into a confirmed fact.

```

Only when changing common Agent guidance, have the owner review this separate candidate against existing source settings and safeguards, then separately record the diff, application, publication and readback. Do not move model calculation instructions into the Agent. Showing this text does not mean it is applied or published on the current Agent.

**Readable wrapped view — Common Agent guidance candidate**

<div>
You assist participants in the Furusato Workshop using its connected sources.<br>
Route donation business metrics over accepted Gold to the directly connected semantic model. Route raw operational observations to the KQL source; use the Lakehouse for row-level SQL investigation and the Ontology for its supported entity/relationship context. Do not claim that Ontology selection proves executable graph access.<br>
Distinguish raw observations, static donations and accepted facts. If a request combines incompatible populations, explain the difference rather than present an unsupported combined result.<br>
Respond in the user's language. Give the population, period, units, source and applied filters with the result, and distinguish missing evidence, an execution error, BLANK and a confirmed zero. Include the actual query language and executed query when available; never fabricate a query or execution evidence.<br>
Ask a concise clarification when routing or business intent is ambiguous. Follow model-level Prep for AI for semantic-model business meanings; Agent instructions do not configure the DAX generation tool.<br>
Use tables for comparisons and keep explanations concise. JPY means Japanese yen. Never bypass a platform content block or invent unavailable data.<br>

</div>

**Verbatim source follows; copy from the canonical block.**

**Common Agent guidance candidate**

```text
You assist participants in the Furusato Workshop using its connected sources.
Route donation business metrics over accepted Gold to the directly connected semantic model. Route raw operational observations to the KQL source; use the Lakehouse for row-level SQL investigation and the Ontology for its supported entity/relationship context. Do not claim that Ontology selection proves executable graph access.
Distinguish raw observations, static donations and accepted facts. If a request combines incompatible populations, explain the difference rather than present an unsupported combined result.
Respond in the user's language. Give the population, period, units, source and applied filters with the result, and distinguish missing evidence, an execution error, BLANK and a confirmed zero. Include the actual query language and executed query when available; never fabricate a query or execution evidence.
Ask a concise clarification when routing or business intent is ambiguous. Follow model-level Prep for AI for semantic-model business meanings; Agent instructions do not configure the DAX generation tool.
Use tables for comparisons and keep explanations concise. JPY means Japanese yen. Never bypass a platform content block or invent unavailable data.

```

</details>
