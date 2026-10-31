# 5.3 完了の確認

[Lab 目次](../README.md) · [この章の目次](README.md)

**この章の完了条件**

| 確認すること | うまくいかないとき |
| --- | --- |
| READY の出力と20テーブルの確認が表示される | 途中で停止した場合は、表示されたエラー（足りない CSV、ヘッダーや文字コードの違い、PARTICIPANT_ID の形式など）を直し、Notebook 01 を先頭から実行し直します。 |
| 静的データ 80,000件・1,344,099,000円と、11テーブルの件数が付録Aと一致する | 期待値を書き換えて合わせることはしません。件数が違う場合は、アップロードした CSV が配布のものと同じかを確認します。 |
| SQL で同じ件数と合計が読める | テーブルが見えない、または古い件数が出る場合は、SQL analytics endpoint の同期を待ってから再確認します。Notebook 01 をむやみに再実行しません。 |
| 「前回の実行が途中で止まり、発行のロック（リース）が残っている」というエラーが出ない | 出た場合は、付録Bの復旧用の3つのパラメーターに、エラーに表示された値を設定して実行します。推測した値は使わず、講師と一緒に行います。 |

<details>
<summary>English</summary>

## 5.3 Check your work

**Completion checks for this chapter**

| What to check | If it does not work |
| --- | --- |
| The READY output and the confirmation for 20 tables appear | If it stops, fix the reported error (missing CSV file, header or encoding difference, PARTICIPANT_ID format and so on) and rerun Notebook 01 from the top. |
| Static data of 80,000 donations / JPY 1,344,099,000 and all 11 table counts match Appendix A | Never edit the expected values to make them match. If a count differs, check that the uploaded CSV files are identical to the distributed ones. |
| SQL returns the same counts and totals | If tables are missing or counts look old, wait for the SQL analytics endpoint to synchronize and check again. Do not rerun Notebook 01 needlessly. |
| No error says that a publishing lock (lease) remains from an interrupted run | If it does, set the three recovery parameters in Appendix B to the values shown in the error and run again. Never use guessed values, and do this together with the instructor. |

</details>
