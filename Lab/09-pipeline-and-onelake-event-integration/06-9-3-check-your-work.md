# 9.3 完了の確認

[Lab 目次](../README.md) · [この章の目次](README.md)

**この章の完了条件**

| 確認すること | うまくいかないとき |
| --- | --- |
| イベント1件、activation 1件、Pipeline の実行1件（Succeeded）、Copy 5,000行、KQL 5,000行がそろっている | 欠けている最初の段階（設定、開始、イベント、activation、実行、Copy、KQL）を特定し、その段階だけを直します。むやみに再アップロードしません。 |
| Pipeline の実行の Subject に /Files/increment/donation_events_001.csv が入っている | Subject が空だと、ファイル名が既定値の donation_events_001.csv になり、後のファイルでも同じ行が重複して入ります。止めて講師に伝えます。 |
| 手動で実行した場合、それを自動の取り込みとして記録していない | 手動の実行は、イベントによる自動起動の確認にはなりません。記録を分けます。 |

<details>
<summary>English</summary>

## 9.3 Check your work

**Completion checks for this chapter**

| What to check | If it does not work |
| --- | --- |
| One event, one activation, one Pipeline run (Succeeded), 5,000 copied rows and 5,000 KQL rows are all present | Identify the first missing stage (settings, start, event, activation, run, Copy or KQL) and fix only that stage. Never re-upload blindly. |
| The Pipeline run has /Files/increment/donation_events_001.csv in Subject | If Subject is empty, the file name falls back to the default donation_events_001.csv, and the same rows are duplicated for later files. Stop and tell the instructor. |
| If you ran the Pipeline manually, it is not recorded as automatic ingestion | A manual run does not confirm automatic triggering by events. Keep the records separate. |

</details>
