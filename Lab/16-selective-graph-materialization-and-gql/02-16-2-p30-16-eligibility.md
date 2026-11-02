# 16.2 操作手順（1）

[Lab 目次](../README.md) · [この章の目次](README.md)

1. 問いを決め、必要な最小の範囲（Gift、Supplier、SupplierProvidesGift）を書き出します。講師の指示で全体を使う場合は、10 Entity・15 Relationship を選びます。
2. Home の Manage graph から Configure Graph を開き、各項目の Status を確認します。Ineligible の項目は、ツールチップで理由を読みます。講師の指示で全体を使う場合を除き、Use the entire Ontology を Yes のままにせず、手順1で決めた範囲の Eligible な項目だけを選びます（Entity を展開すると、その Relationship を選べます）。Semantic model binding や複数の backing table が理由なら、その組合せは Graph projection の対象外です。汎用的な binding 表示から source の種類を推定したり、根拠のない修復・再 binding をしません。必要な Entity/Relationship が Ineligible の場合は理由を記録し、その範囲の新規実体化を止めます。Continue は選んだ必須範囲がすべて Eligible で有効な場合だけ進みます。未実体化なら GQL は未実施として記録し、独立して実施可能な SQL・KQL・DAX の確認と区別します。

![Choose what to project の画面。Use the entire Ontology は Yes で、10の Entity がすべて選ばれて Eligible、Source は ot_* テーブル。右に関係のグラフ、左下に Continue](../assets/p30-16-eligibility.png)

Configure Graph の Choose what to project。各 Entity の Status と Source を確認する（図は全体を選んだ状態。演習では必要な範囲だけを選ぶ）

<details>
<summary>English</summary>

## 16.2 Steps

1. Fix the question and write down the smallest scope it needs (Gift, Supplier and SupplierProvidesGift). If the instructor tells you to use the whole model, select all 10 entities and 15 relationships.
2. Open Configure Graph from Manage graph on Home and check each item's Status. For Ineligible items, read the reason in the tooltip. Unless the instructor tells you to use the whole model, do not leave Use the entire Ontology at Yes; select only Eligible items in the scope from step 1 (expand an entity to select its relationships). If semantic-model binding or multiple backing tables is the reason, that combination is unsupported for Graph projection. Do not infer the source category from a generic binding display or attempt an unsupported repair or rebind. If a required entity or relationship is Ineligible, record the reason and stop new materialization for that scope. Continue only when the entire required scope is Eligible and the button is enabled. If the graph is not materialized, record GQL as unrun and distinguish it from independent SQL, KQL and DAX checks.

![Choose what to project: Use the entire Ontology is Yes and all ten entities are checked and Eligible, with ot_* sources; a relationship graph and a Continue button.](../assets/p30-16-eligibility.png)

Choose what to project in Configure Graph: check each entity's Status and Source. The figure shows the whole model selected; in this lab, select only what you need.

</details>
