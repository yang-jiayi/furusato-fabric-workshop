# 11.2 操作手順（2）

[Lab 目次](../README.md) · [この章の目次](README.md)

3. 同じ Lakehouse に書き込む他のセッションを閉じてから、APPLY_CHANGES = True、CONFIRMED_PLAN_SHA256 = コピーした値、EXCLUSIVE_APPLY_WINDOW_CONFIRMED = True に設定し、もう一度すべてのセルを実行します。
4. 出力に ANALYTICS_MODE=applied と「ANALYTICS_READY: Direct Lake and AI consumption tables are published.」が表示されることを確認します。出力テーブルは29です。

![Notebook のセルの出力。schemas、sourceTables=13、outputTables=29、ANALYTICS_MODE=applied、ANALYTICS_READY の行が並ぶ](../assets/p30-11-executed-output.png)

Notebook 05 の適用の実行後の出力。ANALYTICS_MODE=applied、outputTables=29、ANALYTICS_READY の行を確認する

<details>
<summary>English</summary>

## 11.2 Steps

3. Close any other sessions that write to the same Lakehouse, then set APPLY_CHANGES = True, CONFIRMED_PLAN_SHA256 = the copied value and EXCLUSIVE_APPLY_WINDOW_CONFIRMED = True, and run all cells again.
4. Confirm that the output shows ANALYTICS_MODE=applied and "ANALYTICS_READY: Direct Lake and AI consumption tables are published." There are 29 output tables.

![Notebook cell output listing schemas, sourceTables=13, outputTables=29, ANALYTICS_MODE=applied and ANALYTICS_READY.](../assets/p30-11-executed-output.png)

Output after the Notebook 05 apply run: check ANALYTICS_MODE=applied, outputTables=29 and the ANALYTICS_READY line.

</details>
