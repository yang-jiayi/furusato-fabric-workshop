# 17.1 この章で行うこと

[Lab 目次](../README.md) · [この章の目次](README.md)

同梱の portable profile は、現在の公開版で確認した指示本文と170個の選択済みノードを保持し、配置先に必要なIDだけを置換します。既存の Gen2 Data Agent で Draft と公開版を照合します。設定の一致は、回答精度の承認を意味しません。

4つの論理ソース（Lakehouse、KQL Database、Semantic model、Ontology）を区別します。Ontologyのcontextはsource instructionとは別で、Ontology-groundingがGQL実行を意味するわけではありません。実際のsource・query language・query・resultを対応させて確認します。

準備するもの・確認すること

- 既存Agentとその4つの論理ソースを確認し、Workspace・フォルダー・Agentの各IDは自分の許可された環境から取得します。未作成の場合に別AgentやSchemaを作る手順ではありません。
- 現在のlive definitionとselectionを読み取り、実際のsource definitionでID-only bindingを解決できることを確認します。共有環境のmirror・時系列作業には別の完全性確認が必要です。

<details>
<summary>English</summary>

## 17.1 What you will do

The portable profile preserves the instruction text and 170 selected nodes verified in the current Published configuration, substituting only IDs required by the target environment. Reconcile Draft and Published on the existing Gen2 Data Agent. Configuration parity is not accuracy acceptance.

Distinguish the four logical sources: Lakehouse, KQL Database, semantic model and Ontology. Ontology context is separate from source instructions, and ontology grounding does not imply GQL execution. Match the actual source, query language, query and result.

Before you start

- Confirm the existing agent and its four logical sources. Obtain workspace, folder and agent IDs from your authorized environment. This procedure does not create another agent or schema if one is missing.
- Read the live definition and selections, and confirm ID-only bindings can be resolved against actual source definitions. Mirroring and time-series work in the shared environment require separate completeness checks.

</details>
