# 2.2 操作手順

[Lab 目次](../README.md) · [この章の目次](README.md)

1. RDB・Semantic model・Ontology の役割の違いを確認し、「JOIN できる」ことと「関係が業務上の意味を持つ」ことの違いを説明できるようにします。
2. 「何を数えるか」を決めます。Donation は1件の寄付、Donor は1人の寄付者、MunicipalityCategoryMetric は「自治体 × カテゴリ」の集計の単位です。各概念の粒度（1行が何を表すか）を1文で書きます。
3. キーと表示名を分けます。同じ名前の自治体や寄付者がありうるので、名前で結合しません。MunicipalityId のような文字列のコードは、先頭のゼロを含めてそのまま扱い、数値に変換しません。
4. 元のテーブルを、次の順に判断して分類します。①監査・制御用のテーブルは対象外にします。②1件に1つの値は Property にします。③外部キー2本だけの中間表（business_gifts）は、Relationship の対応表にします。④複合粒度の事前集計は、Metric／Flow の Entity にします。⑤時刻付きの観測は、既存の Entity への時系列バインドにします。
5. Relationship ごとに、動詞、Origin、Target、外部キーか対応表か、意味、そして「推論してはいけない意味」を書きます。例：SupplierProvidesGift はカタログへの登録であり、発送や売上の配分ではありません。
6. 数値の置き場所を分類します。次の4つを、別々のものとして表に書きます。保存済みの集計値（MunicipalityStaticTotalYen などの Property）、Semantic model が持つ DAX メジャー（寄附総額など）、自然言語の Business Rules、Notebook 05 の品質チェックです。

> 同義語や説明は後から足すものではなく、設計の一部です。曖昧な言葉（人気、東京の寄付など）を見つけたら、この段階でメモしておきます（13章で登録します）。

<details>
<summary>English</summary>

## 2.2 Steps

1. Review how a relational database, a semantic model and an ontology differ, and be ready to explain the difference between "can be joined" and "the relationship has business meaning".
2. Decide what is counted. A Donation is one donation, a Donor is one donor, and MunicipalityCategoryMetric is a total for one municipality and one category. Write the grain (what one row represents) of each concept in one sentence.
3. Separate keys from display names. Municipalities and donors can share names, so never join on names. Keep string codes such as MunicipalityId as they are, including leading zeros, and never convert them to numbers.
4. Classify the source tables by deciding in this order: (1) audit and control tables are excluded; (2) one value per instance becomes a property; (3) a bridge with only two foreign keys (business_gifts) becomes the mapping table of a relationship; (4) pre-calculated totals at a composite grain become metric or flow entities; (5) timestamped observations become a time-series binding on an existing entity.
5. For each relationship, write the verb, origin, target, whether it uses a foreign key or a mapping table, its meaning, and what must not be inferred from it. Example: SupplierProvidesGift is a catalog registration, not shipment or revenue allocation.
6. Classify where each number lives. List these four as separate things: stored totals (properties such as MunicipalityStaticTotalYen), DAX measures owned by the semantic model (such as 寄附総額), natural-language Business Rules and Notebook 05 quality checks.

> Synonyms and descriptions are part of the design, not an afterthought. When you find ambiguous words (popular, Tokyo donations and so on), note them now; you register them in Chapter 13.

</details>
