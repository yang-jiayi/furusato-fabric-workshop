# 11.1 この章で行うこと

[Lab 目次](../README.md) · [この章の目次](README.md)

Notebook 05 は、Lakehouse の静的テーブルと Files/increment の3つの CSV を読み、bronze・silver・gold・ops・quarantine の5つのスキーマに、品質処理済みのテーブルを作ります。Eventhouse は読みません。

8月の観測データの重複 100件は quarantine に分けられ、14,900件が受け入れられます。Gold の「受け入れ」は Notebook 05 の品質チェックを通ったという意味で、人による承認や、支払い・発送の完了を意味しません。

準備するもの・確認すること

- 5章（Notebook 01）が完了し、Files/increment に3つの CSV がそろっていることを確認します（9〜10章）。
- 24.6で取り込んだ Notebook 05 を開き、LH_Furusato_&lt;PID&gt; を接続します。まだ無い場合だけ source/workshop/v3.0.0-preview/notebooks の Notebook 05 を作業フォルダーにインポートします。

<details>
<summary>English</summary>

## 11.1 What you will do

Notebook 05 reads the static Lakehouse tables and the three CSV files in Files/increment, and creates quality-processed tables in five schemas: bronze, silver, gold, ops and quarantine. It does not read the Eventhouse.

The 100 duplicates in the August observation data are moved to quarantine, and 14,900 are accepted. In Gold, "accepted" means that a row passed the Notebook 05 quality checks; it does not mean human approval, payment or shipment.

Before you start

- Confirm that Chapter 5 (Notebook 01) is complete and that the three CSV files are in Files/increment (Chapters 9–10).
- Open Notebook 05 imported in 24.6 and attach LH_Furusato_&lt;PID&gt;. Only if absent, import Notebook 05 from source/workshop/v3.0.0-preview/notebooks into the work folder.

</details>
