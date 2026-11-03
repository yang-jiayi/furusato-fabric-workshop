# 17.2 対象と準備

[Lab 目次](../README.md) · [この章の目次](README.md)

同梱の portable profile は、現行の公開設定で確認した指示本文と170個の選択済みノードを保持し、配置先に必要な ID だけを置換します。自分が所有し利用を許可された Workspace とフォルダー内の既存 Gen2 Data Agent で Draft と Published を照合します。自分の Workspace ID、Folder ID、Agent ID、PrivateRoot を設定してください。別の Agent を作成せず、source を追加したり selection や schema を広げたりしません。

1. 4章のアクセス・容量・権限の確認を済ませます。対象 Agent が既にあり、自分の担当する4つの論理ソース（Lakehouse、KQL Database、Semantic model、Ontology）を含むことを確認します。既存の公開版がある場合は、変更前の状態を PrivateRoot に保存できる手順を確認してから進みます。
2. 現在のソース定義を読み取り、実際の ID と選択状態を記録します。IDだけの binding を実定義に照合できない場合、または想定外の意味差分が見つかった場合は停止し、選択を推測・拡張せず担当者に確認します。

対象の OneLake mirroring が部分的か、完全性を確認できない場合は、mirror の変更・再取り込み・時系列作業を行わず停止します。Ontology の静的 SQL は独立した source・言語・query・result として扱います。Graph model の存在・準備状態と実際の GQL は別途確認し、どちらも推定しません。

<details>
<summary>English</summary>

## 17.2 Scope and prerequisites

The portable profile preserves the instruction text and 170 selected nodes verified in the current published configuration, substituting only IDs required by the target environment. Reconcile Draft and Published on an existing Gen2 Data Agent in a workspace and folder you own and are authorized to use. Set your own Workspace ID, Folder ID, Agent ID and PrivateRoot. Do not create another agent, add sources, expand selections or change the schema.

1. Complete the access, capacity and permission checks in Chapter 4. Confirm the existing agent has the four assigned logical sources: Lakehouse, KQL Database, semantic model and Ontology. If a published version exists, first confirm that the procedure can preserve its pre-change state under PrivateRoot.
2. Read the current source definition and record actual IDs and selection state. Stop and consult the instructor if ID-only bindings cannot be resolved against the live definition or an unexpected semantic difference appears; do not guess or expand selections.

If OneLake mirroring on the target is partial or cannot be verified as complete, stop without changing the mirror, re-ingesting data or starting time-series work. Treat static Ontology SQL as a separate source, language, query and result. Verify Graph-model presence/readiness and actual GQL separately; infer neither.

</details>
