# 17.1 この章で行うこと

[Lab 目次](../README.md) · [この章の目次](README.md)

この章では既存 Data Agent の設定を確認し、回答品質を評価する際の限界を整理します。設定の一致だけで回答精度が承認・保証されるわけではありません。

準備するもの・確認すること

- 既存 Agent と4つの論理ソースを確認し、Workspace・フォルダー・Agent の各 ID は自分の許可された環境から取得します。別 Agent や Schema を作成する手順ではありません。
- 現在の live definition と selection を読み取り、実際の source definition で ID-only binding を解決できることを確認します。対象の mirroring が部分的か完全性を確認できない場合は、関連する変更や時系列作業を行わず停止します。

<details>
<summary>English</summary>

## 17.1 What you will do

Review the existing Data Agent configuration and the limits of answer-quality evaluation. Configuration parity alone does not approve or guarantee answer accuracy.

Before you start

- Confirm the existing agent and its four logical sources. Obtain workspace, folder and agent IDs from your authorized environment. This procedure does not create another agent or schema if one is missing.
- Read the live definition and selections, and confirm ID-only bindings can be resolved against actual source definitions. Mirroring and time-series work in the shared environment require separate completeness checks.

</details>
