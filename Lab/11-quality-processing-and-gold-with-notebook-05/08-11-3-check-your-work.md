# 11.3 完了の確認

[Lab 目次](../README.md) · [この章の目次](README.md)

**この章の完了条件**

| 確認すること | うまくいかないとき |
| --- | --- |
| 実行結果にアクセスできた場合だけ Gold・受入増分・quarantine の実測値を記録し、fixture の期待値と区別した | 現行の読み取り専用 SQL catalog は static dbo.ot_donation のみを公開し、ops.analytics_publish_control と gold.donations は公開しません。Gold 結果を SQL 実測として記載せず、他の許可済み証拠が無ければ未検証とします。 |
| 適用の実行が、ハッシュの不一致で止まらない | プレビューをやり直し、新しい PLAN_SHA256 をコピーします。プレビューと適用で PARTICIPANT_ID、INCREMENT_PATH、ALLOW_AUTOMATED_APPLY（True の場合は EXPECTED_WORKSPACE_NAME も）の値が違うと、ハッシュも変わります。 |
| ot_* テーブルが変わっていない（ot_donation は 80,000件のまま） | 変わっている場合は作業を止めて講師に伝えます。Notebook 05 は ot_* テーブルを上書きしない設計です。 |
| 前回の実行が途中で止まったことを示すエラーが出ない | 出た場合は、前のセッションが止まっていることを確認し、エラーに表示された RunId を INTERRUPTED_RUN_ID に、OPERATOR_RECOVER_INTERRUPTED_RUN を True に設定して実行します。値は推測しません。 |

<details>
<summary>English</summary>

## 11.3 Check your work

**Completion checks for this chapter**

| What to check | If it does not work |
| --- | --- |
| You recorded observed Gold, accepted-increment and quarantine values only when run output was accessible, separately from fixture expectations | The current read-only SQL catalog exposes only static dbo.ot_donation, not ops.analytics_publish_control or gold.donations. Do not report Gold as a SQL measurement; mark it unverified if no other authorized evidence is available. |
| The apply run does not stop on a hash mismatch | Run the preview again and copy the new PLAN_SHA256. If PARTICIPANT_ID, INCREMENT_PATH or ALLOW_AUTOMATED_APPLY (and, when it is True, EXPECTED_WORKSPACE_NAME) differ between the preview and the apply run, the hash changes. |
| The ot_* tables are unchanged (ot_donation is still 80,000) | If they changed, stop and tell the instructor. Notebook 05 is designed not to overwrite the ot_* tables. |
| No error says that an earlier run was interrupted | If one does, confirm that the earlier session is no longer running, set INTERRUPTED_RUN_ID to the RunId shown in the error and OPERATOR_RECOVER_INTERRUPTED_RUN to True, then run. Never guess the value. |

</details>
