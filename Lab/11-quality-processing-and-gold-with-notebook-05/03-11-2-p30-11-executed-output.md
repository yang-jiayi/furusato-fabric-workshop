# 11.2 操作手順（2）

[Lab 目次](../README.md) · [この章の目次](README.md)

3. 同じ Lakehouse に書き込む他のセッションを閉じてから、APPLY_CHANGES = True、CONFIRMED_PLAN_SHA256 = コピーした値、EXCLUSIVE_APPLY_WINDOW_CONFIRMED = True に設定し、もう一度すべてのセルを実行します。
4. Notebook05 の apply/job が成功し、出力に ANALYTICS_MODE=applied と「ANALYTICS_READY: Direct Lake and AI consumption tables are published.」が表示されることを確認します。成功画面の図が示すのは Notebook05 job の成功だけで、Gold の件数・金額や公開先の可読性は証明しません。SQL catalog の現状と、利用可能な許可済み検証手段は次の手順で区別します。

![Notebook のセルの出力。schemas、sourceTables=13、outputTables=29、ANALYTICS_MODE=applied、ANALYTICS_READY の行が並ぶ](../assets/p30-11-executed-output.png)

Notebook 05 の適用出力の参考例。ANALYTICS_MODE=applied、outputTables=29、ANALYTICS_READY を確認する箇所を示します。自分の最新ジョブと出力で確認してください。この図は自分の実行の成功や Gold 件数を証明しません。

![applied 出力の参考例。PLAN_SHA256、sourceTables、outputTables、generation の伏せ字と ANALYTICS_READY を含む。](../assets/p30-11-executed-output-detail.png)

同じ参考例の APPLY_REQUESTED から ANALYTICS_READY までの連続した出力部分の拡大。generation は伏せられています。自分のジョブと出力を別に確認し、この図を自分の成功や Gold 件数の証拠として扱いません。

<details>
<summary>English</summary>

## 11.2 Steps

3. Close any other sessions that write to the same Lakehouse, then set APPLY_CHANGES = True, CONFIRMED_PLAN_SHA256 = the copied value and EXCLUSIVE_APPLY_WINDOW_CONFIRMED = True, and run all cells again.
4. Confirm that the Notebook05 apply/job succeeded and its output shows ANALYTICS_MODE=applied and "ANALYTICS_READY: Direct Lake and AI consumption tables are published." The success-screen figure proves only the Notebook05 job succeeded; it does not prove Gold counts/amounts or that the published tables are readable. The next steps check SQL endpoint access on your participant-owned target separately from the Explorer preview and Notebook output.

![Notebook cell output listing schemas, sourceTables=13, outputTables=29, ANALYTICS_MODE=applied and ANALYTICS_READY.](../assets/p30-11-executed-output.png)

Illustrative Notebook 05 apply output showing where to check ANALYTICS_MODE=applied, outputTables=29 and ANALYTICS_READY. Verify your own latest job and output; this image does not establish your execution success or Gold counts.

![Illustrative applied-output block, including PLAN_SHA256, sourceTables, outputTables, the redacted generation and ANALYTICS_READY.](../assets/p30-11-executed-output-detail.png)

Enlarged contiguous APPLY_REQUESTED-through-ANALYTICS_READY output from the same example, with generation redacted. Independently check your own job and output; do not treat this image as evidence of your success or Gold counts.

</details>
