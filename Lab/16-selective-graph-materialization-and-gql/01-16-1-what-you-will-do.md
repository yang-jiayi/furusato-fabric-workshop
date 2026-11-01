# 16.1 この章で行うこと

[Lab 目次](../README.md) · [この章の目次](README.md)

Graph は、関係の経路そのものを問う質問のために、必要な Entity と Relationship だけを選んで実体化するものです。すべての Ontology に必要な工程ではなく、自動では作られません。

Ontology の SQL 問い合わせが成功しても、Graph model の存在や準備状態、GQL の実行成功は証明されません。逆に、他のデータ経路の部分状態だけから Graph model が存在しないとも判断しません。Graph の状態と実際の GQL query/result を別々に確認します。Microsoft Learn は Graph model が存在する場合の関係 traversal に GQL を示しています。

この章では「この返礼品を登録している事業者はどこか」という問いのために Gift・Supplier・SupplierProvidesGift を実体化し、GQL の結果を SQL の対応表と照らし合わせます。講師が全体を実体化済みの場合は、まず現在 load 済みのモデルを照会します。

準備するもの・確認すること

- 主 Ontology と、それに付属する Graph だけを使います。時系列やソースの型によって実体化ができない場合は、その状態を記録します。関係照会用の2件目の Ontology は作りません。
- Graph の実体化では、Graph 用のデータが元データとは別に保存され、容量を使います。

<details>
<summary>English</summary>

## 16.1 What you will do

A graph is materialized from only the entities and relationships you select, for questions about the relationship path itself. It is not required for every ontology and is not created automatically.

Successful SQL against an ontology does not prove that a graph model exists or is ready, or that GQL has executed successfully. Conversely, a partial state in another data path does not prove that no graph model exists. Check graph state and actual GQL queries/results separately. Microsoft Learn describes GQL for relationship traversals when a graph model exists.

In this chapter you materialize Gift, Supplier and SupplierProvidesGift for the question "Which suppliers are registered for this gift?", and check the GQL results against the mapping table in SQL. If the instructor already materialized the full model, query the currently loaded model first.

Before you start

- Use only the main ontology and its managed graph. If time-series or source types prevent materialization, record the state. Do not create a second relationship-query ontology.
- Materializing a graph stores graph data separately from the source data and consumes capacity.

</details>
