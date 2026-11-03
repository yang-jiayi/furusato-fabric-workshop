# 17.1 この章で行うこと

[Lab 目次](../README.md) · [この章の目次](README.md)

この章の学習目標は、既存 Agent の設定と実際の回答・実行経路を区別して検証することです。設定の一致は回答精度の承認や保証を意味しません。

4つの論理ソース（Lakehouse、KQL Database、Semantic model、Ontology）を区別します。Ontology context は source instruction とは別で、Ontology grounding は GQL 実行を意味しません。実際の source、query language、query、result を対応させて確認します。

準備するもの・確認すること

- 既存 Agent と4つの論理ソースを確認し、Workspace・フォルダー・Agent の各 ID は自分の許可された環境から取得します。別 Agent や Schema を作成する手順ではありません。
- 現在の live definition と selection を読み取り、実際の source definition で ID-only binding を解決できることを確認します。対象の mirroring が部分的か完全性を確認できない場合は、関連する変更や時系列作業を行わず停止します。

<details>
<summary>English</summary>

## 17.1 What you will do

The learning goal is to verify the existing Agent's configuration while distinguishing it from evidence of actual answers and execution paths. Configuration parity does not approve or guarantee answer accuracy.

Distinguish the four logical sources: Lakehouse, KQL Database, semantic model and Ontology. Ontology context is separate from source instructions, and ontology grounding does not imply GQL execution. Match the actual source, query language, query and result.

Before you start

- Confirm the existing agent and its four logical sources. Obtain workspace, folder and agent IDs from your authorized environment. This procedure does not create another agent or schema if one is missing.
- Read the live definition and selections, and confirm ID-only bindings can be resolved against actual source definitions. Mirroring and time-series work in the shared environment require separate completeness checks.

</details>
