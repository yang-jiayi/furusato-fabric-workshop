# 11.3 完了の確認

[Lab 目次](../README.md) · [この章の目次](README.md)

**この章の完了条件**

| 確認すること | うまくいかないとき |
| --- | --- |
| Gold 94,900件・1,596,157,000円、受け入れた増分 14,900件・252,058,000円、quarantine 100件 | 合わない場合は dq_rule_results と quarantine を確認し、Files/increment の3ファイルが配布のものと同じかを確かめます。BI の側で数字を隠して合わせることはしません。 |
| 適用の実行が、ハッシュの不一致で止まらない | プレビューをやり直し、新しい PLAN_SHA256 をコピーします。プレビューと適用で PARTICIPANT_ID、INCREMENT_PATH、ALLOW_AUTOMATED_APPLY（True の場合は EXPECTED_WORKSPACE_NAME も）の値が違うと、ハッシュも変わります。 |
| ot_* テーブルが変わっていない（ot_donation は 80,000件のまま） | 変わっている場合は作業を止めて講師に伝えます。Notebook 05 は ot_* テーブルを上書きしない設計です。 |
| 前回の実行が途中で止まったことを示すエラーが出ない | 出た場合は、前のセッションが止まっていることを確認し、エラーに表示された RunId を INTERRUPTED_RUN_ID に、OPERATOR_RECOVER_INTERRUPTED_RUN を True に設定して実行します。値は推測しません。 |

<details>
<summary>English</summary>

## 11.3 Check your work

**Completion checks for this chapter**

| What to check | If it does not work |
| --- | --- |
| Gold 94,900 / JPY 1,596,157,000, accepted increments 14,900 / JPY 252,058,000 and quarantine 100 | If they do not match, check dq_rule_results and quarantine, and confirm that the three files in Files/increment are identical to the distributed ones. Never hide differences on the BI side. |
| The apply run does not stop on a hash mismatch | Run the preview again and copy the new PLAN_SHA256. If PARTICIPANT_ID, INCREMENT_PATH or ALLOW_AUTOMATED_APPLY (and, when it is True, EXPECTED_WORKSPACE_NAME) differ between the preview and the apply run, the hash changes. |
| The ot_* tables are unchanged (ot_donation is still 80,000) | If they changed, stop and tell the instructor. Notebook 05 is designed not to overwrite the ot_* tables. |
| No error says that an earlier run was interrupted | If one does, confirm that the earlier session is no longer running, set INTERRUPTED_RUN_ID to the RunId shown in the error and OPERATOR_RECOVER_INTERRUPTED_RUN to True, then run. Never guess the value. |

</details>
