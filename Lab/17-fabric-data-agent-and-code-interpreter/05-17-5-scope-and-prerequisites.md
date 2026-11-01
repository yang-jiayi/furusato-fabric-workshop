# 17.5 対象と準備

[Lab 目次](../README.md) · [この章の目次](README.md)

この実験プロファイルを、参加者自身が所有し利用を許可された Workspace とフォルダー内の既存 Gen2 Data Agent に適用し、Draft と公開版を確認します。自分の Workspace ID、Folder ID、Agent ID、PrivateRoot を設定します。別の Agent を作成せず、ソースの追加・選択範囲の拡大・Schema変更も行いません。このプロファイルは実験用で、回答精度の採用・保証を意味しません。

1. 4章のアクセス・容量・権限の確認を済ませます。対象 Agent が既にあり、自分の担当する4つの論理ソース（Lakehouse、KQL Database、Semantic model、Ontology）を含むことを確認します。既存の公開版がある場合は、変更前の状態を PrivateRoot に保存できる手順を確認してから進みます。
2. 現在のソース定義を読み取り、実際の ID と選択状態を記録します。IDだけの binding を実定義に照合できない場合、または想定外の意味差分が見つかった場合は停止し、選択を推測・拡張せず担当者に確認します。

共有環境の部分的な mirroring は、mirror の変更・再取り込み・時系列作業の前提を満たしません。Ontology の静的 SQL は独立したソース・言語・クエリ・結果として扱います。Graph model の存在・準備状態と実際の GQL は別途確認し、どちらも推定しません。

<details>
<summary>English</summary>

## 17.5 Scope and prerequisites

Apply this experimental profile to an existing Gen2 Data Agent in a workspace and folder you own and are authorized to use, then inspect Draft and the published version. Set your own Workspace ID, Folder ID, Agent ID and PrivateRoot. Do not create another agent, add sources, expand selections or change the schema. This profile is experimental; it is not an accepted or guaranteed accuracy result.

1. Complete the access, capacity and permission checks in Chapter 4. Confirm the existing agent has the four assigned logical sources: Lakehouse, KQL Database, semantic model and Ontology. If a published version exists, first confirm that the procedure can preserve its pre-change state under PrivateRoot.
2. Read the current source definition and record actual IDs and selection state. Stop and consult the instructor if ID-only bindings cannot be resolved against the live definition or an unexpected semantic difference appears; do not guess or expand selections.

Partial mirroring in the shared environment does not satisfy prerequisites for mirror changes, re-ingestion or time-series work. Treat static Ontology SQL as independent evidence for its own source, language, query and result. Verify Graph-model presence/readiness and actual GQL separately; infer neither.

</details>
