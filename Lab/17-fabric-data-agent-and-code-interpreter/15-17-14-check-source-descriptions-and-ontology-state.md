# 17.14 ソース説明と Ontology の状態を確認する

[Lab 目次](../README.md) · [この章の目次](README.md)

通常ソースに Description の編集欄がある場合は、対応する以下の原文を設定します。入力欄が表示されない場合は無理に別の欄へ貼らず、17.15の確認記録にその状態を残します。Gen2 Ontology は、このソース説明を挿入する対象ではありません。6〜7章で作成した同じ Entity・Relationship と、13章の Entity の説明をそのまま保持します。

Lakehouse SQL：Description

**description**

```text
PRIMARY source for every ordinary seed/static question, including payment/category rankings and residence-versus-recipient comparisons. Complete static facts, registered counts, donation/gift/catalog identities and stored metric keys. Get complete data here even when relationships are also requested; Ontology supplies declarations. Also query agent_relationship_dictionary for exact source-declared arrows and agent_prefecture_category_metric for existing metric keys plus both declared edges; do not infer relation direction from foreign-key layout. Also the explicitly selected source for quality-processing requests: unique Ready control generation/run, actual raw/accepted/quarantine table counts, CSV file/run/alias provenance and source DQ judgments. These quality populations are separate from the ordinary static views and Eventhouse observations.
```

KQL Database：Description

**description**

```text
Raw duplicate-inclusive operational observations of the distributed August 2026 increments (UTC). A year-less 8月/August question, or one about data that flowed in, observations, events or municipality activity, means this source and the year 2026. Five-field bucket grain without donors or EventID. Recorded publication is synthetic CSV metadata, not actual ingestion or processing telemetry.
```

Semantic model：Description

**description**

```text
ONLY for explicitly requested Gold, quality-processed analytical results, Power BI or an explicitly named model measure. Do not route ordinary seed payment/category/count/amount questions here; they use Lakehouse SQL. StaticSeed/RealtimeIncrement same-column KEEPFILTERS, independently shifted periods and BLANK retain their model meaning.
```

Ontology の文脈が開けない場合は、主 Ontology 自体を開き、Entity とデータバインドが存在するか、選択したアイテムが自分の作業範囲かを確認します。No data added、SchemaUnavailable、502、definition.json 欠落などは、そのままエラー本文と日時を記録します。通常 SQL が動いても Ontology 接続の成功にはせず、追加の Ontology やダミー定義で回避しません。

<details>
<summary>English</summary>

## 17.14 Check source descriptions and ontology state

Where an ordinary source exposes a Description editor, set the corresponding original text below. If no editor is shown, do not paste it into another field; record that state in 17.15. Gen2 ontology is not a destination for these source descriptions. Retain the same entities and relationships from Chapters 6–7 and the authored entity descriptions from Chapter 13.

Lakehouse SQL: Description

**description**

```text
PRIMARY source for every ordinary seed/static question, including payment/category rankings and residence-versus-recipient comparisons. Complete static facts, registered counts, donation/gift/catalog identities and stored metric keys. Get complete data here even when relationships are also requested; Ontology supplies declarations. Also query agent_relationship_dictionary for exact source-declared arrows and agent_prefecture_category_metric for existing metric keys plus both declared edges; do not infer relation direction from foreign-key layout. Also the explicitly selected source for quality-processing requests: unique Ready control generation/run, actual raw/accepted/quarantine table counts, CSV file/run/alias provenance and source DQ judgments. These quality populations are separate from the ordinary static views and Eventhouse observations.
```

KQL Database: Description

**description**

```text
Raw duplicate-inclusive operational observations of the distributed August 2026 increments (UTC). A year-less 8月/August question, or one about data that flowed in, observations, events or municipality activity, means this source and the year 2026. Five-field bucket grain without donors or EventID. Recorded publication is synthetic CSV metadata, not actual ingestion or processing telemetry.
```

Semantic model: Description

**description**

```text
ONLY for explicitly requested Gold, quality-processed analytical results, Power BI or an explicitly named model measure. Do not route ordinary seed payment/category/count/amount questions here; they use Lakehouse SQL. StaticSeed/RealtimeIncrement same-column KEEPFILTERS, independently shifted periods and BLANK retain their model meaning.
```

If ontology context cannot be opened, open the main ontology itself and check its entities and data bindings and whether the selected item belongs to your assigned scope. Record No data added, SchemaUnavailable, 502, missing definition.json and similar errors with timestamps. Ordinary SQL success does not prove ontology connectivity; do not work around these errors by creating another ontology or a dummy definition.

</details>
