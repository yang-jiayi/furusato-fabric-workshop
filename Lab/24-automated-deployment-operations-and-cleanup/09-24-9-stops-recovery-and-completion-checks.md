# 24.9 途中で止まった場合と完了確認

[Lab 目次](../README.md) · [この章の目次](README.md)

**失敗を保持して再開するための確認**

| 状況 | 次の操作 |
| --- | --- |
| preflight に blockers | 計画を承認しない。権限、フォルダー対応、名前衝突を確認。新しい範囲は新しい記録フォルダーで計画。 |
| 作成の応答が不明 | 作成を再送せず、作業フォルダーと実行記録の pendingCreates / operation を確認。チェックポイントを書き換えない。 |
| 取り込みが遅い | 最大10分という公式目安と2分の遅延待機を踏まえ、履歴を読む。再送や手動実行を重ねない。 |
| 配布物が変わった | 途中でハッシュを更新しない。承認した版と同じ記録を保持し、元の版から状態を確認。 |
| Notebook 05 のプレビュー不一致 | 参加者ID・入力パス・実行モードを揃えてプレビューし直し、実出力のハッシュだけを使う。 |
| Ontology native 機能が利用不可 | 対象・エラー・日時を記録。SQLやDAXの成功を代用せず、追加のOntologyを作らない。 |

完了時は、作業フォルダー、DeploymentPrivate/deployment-state.json、17章の公開定義の確認、19章の評価記録を対応付けます。容量・ロール・テナント設定や他人のデータは変更しません。ワークショップ後の削除は24.2の順に、自分の参加者IDのアイテムだけを対象にします。評価記録を保存する前に削除しません。

<details>
<summary>English</summary>

## 24.9 Stops, recovery and completion checks

**Checks for recovery while retaining failures**

| Situation | Next action |
| --- | --- |
| Preflight blockers | Do not approve. Check access, folder mapping and name conflicts; a new scope needs a new record folder and plan. |
| Uncertain create response | Do not resend creation. Inspect the folder and pendingCreates/operation evidence without editing checkpoints. |
| Delayed ingestion | Inspect history, considering the ten-minute published guidance and two-minute late-arrival wait; do not overlap retries/manual runs. |
| Source distribution changed | Do not refresh hashes mid-deployment. Preserve the approved source version and records and inspect the state from that version. |
| Notebook 05 preview mismatch | Align participant ID, input path and execution mode, preview again and use only the actual output hash. |
| Unavailable native ontology feature | Record target, error and time. Do not substitute SQL/DAX success or create another ontology. |

At completion, reconcile the work folder, DeploymentPrivate/deployment-state.json, Chapter 17 published-definition verification and Chapter 19 evaluation records. Do not change capacity, roles, tenant settings or others' data. After the workshop, use the cleanup order in 24.2 for only your participant ID's items; preserve evaluation records first.

</details>
