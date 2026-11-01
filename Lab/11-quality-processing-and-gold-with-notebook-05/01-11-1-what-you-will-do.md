# 11.1 この章で行うこと

[Lab 目次](../README.md) · [この章の目次](README.md)

Notebook 05 は、Lakehouse の静的テーブルと Files/increment の3つの CSV を読み、bronze・silver・gold・ops・quarantine の5つのスキーマに、品質処理済みのテーブルを作ります。Eventhouse は読みません。

3つの増分 fixture がそろい、Notebook 05 の実行と出力を確認できた場合の想定では、重複100件を quarantine に分け、14,900件を受け入れます。Gold の「受け入れ」は Notebook 05 の品質チェックを通ったという意味で、人による承認や支払い・発送の完了を意味しません。実行結果の証拠がない場合は実績として記載しません。

準備するもの・確認すること

- 5章（Notebook 01）が完了し、Files/increment に3つの CSV がそろっていることを確認します（9〜10章）。
- 24.6で取り込んだ Notebook 05 を開き、LH_Furusato_&lt;PID&gt; を接続します。まだ無い場合だけ source/workshop/v3.0.0-preview/notebooks の Notebook 05 を作業フォルダーにインポートします。

<details>
<summary>English</summary>

## 11.1 What you will do

Notebook 05 reads the static Lakehouse tables and the three CSV files in Files/increment, and creates quality-processed tables in five schemas: bronze, silver, gold, ops and quarantine. It does not read the Eventhouse.

With all three increment fixtures present and a verified Notebook 05 run/output, the expected processing separates 100 duplicates into quarantine and accepts 14,900 records. In Gold, "accepted" means a row passed Notebook 05 quality checks, not human approval, payment or shipment. Do not describe the expected result as observed unless you have checked the actual run output.

Before you start

- Confirm that Chapter 5 (Notebook 01) is complete and that the three CSV files are in Files/increment (Chapters 9–10).
- Open Notebook 05 imported in 24.6 and attach LH_Furusato_&lt;PID&gt;. Only if absent, import Notebook 05 from source/workshop/v3.0.0-preview/notebooks into the work folder.

</details>
