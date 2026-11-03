# 17.1 この章で行うこと

[Lab 目次](../README.md) · [この章の目次](README.md)

この章の学習目標は、既存Agentの設定と実際の回答・実行経路の証拠を区別して検証することです。設定の一致は、回答精度の承認や保証を意味しません。

4つの論理ソース（Lakehouse、KQL Database、Semantic model、Ontology）を区別します。Ontologyのcontextはsource instructionとは別で、Ontology-groundingがGQL実行を意味するわけではありません。実際のsource・query language・query・resultを対応させて確認します。

準備するもの・確認すること

- 既存Agentとその4つの論理ソースを確認し、Workspace・フォルダー・Agentの各IDは自分の許可された環境から取得します。未作成の場合に別AgentやSchemaを作る手順ではありません。
- 現在のlive definitionとselectionを読み取り、実際のsource definitionでID-only bindingを解決できることを確認します。共有環境のmirror・時系列作業には別の完全性確認が必要です。

<details>
<summary>English</summary>

## 17.1 What you will do

The learning goal is to verify the existing Agent's configuration while distinguishing it from evidence of actual answers and execution paths. Configuration parity does not approve or guarantee answer accuracy.

Distinguish the four logical sources: Lakehouse, KQL Database, semantic model and Ontology. Ontology context is separate from source instructions, and ontology grounding does not imply GQL execution. Match the actual source, query language, query and result.

Before you start

- Confirm the existing agent and its four logical sources. Obtain workspace, folder and agent IDs from your authorized environment. This procedure does not create another agent or schema if one is missing.
- Read the live definition and selections, and confirm ID-only bindings can be resolved against actual source definitions. Mirroring and time-series work in the shared environment require separate completeness checks.

</details>
