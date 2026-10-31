# 5.1 この章で行うこと

[Lab 目次](../README.md) · [この章の目次](README.md)

Lakehouse に静的データの8つの CSV を置き、Notebook 01 で検証して、Ontology のデータ基盤になる11の ot_* テーブルを作ります。

Notebook 01 は、ファイル名・文字コード・ヘッダー・SHA-256・キー・件数をすべて確認してからテーブルを書き込みます。最終的に、ステージング用8、Ontology 用11、ロード監査用1の合計20テーブルができます。

準備するもの・確認すること

- 標準経路では24.6で作成した Lakehouse（LH_Furusato_&lt;PID&gt;）と実行済み Notebook 01 を確認します。この章のファイル配置・インポート・Run all は構築方法の説明として読み、再実行せず、末尾の件数と SQL の確認を行います。別の手動構築を行う場合だけ、作業フォルダーの New item → Lakehouse でこの名前を指定し、Lakehouse schemas を有効にします。
- 配布フォルダー workshop/v3.0.0-preview/data/seed にある8つの CSV を用意します（prefectures.csv、municipalities.csv、categories.csv、gifts.csv、businesses.csv、business_gifts.csv、donors.csv、donation_orders.csv）。
- 配布フォルダーの notebooks にある Notebook 01（Notebook_01_Furusato_Prepare_Ontology_Data.ipynb）を用意します。

<details>
<summary>English</summary>

## 5.1 What you will do

Upload the eight static-data CSV files to the Lakehouse, then run Notebook 01 to validate them and create the 11 ot_* tables that become the data foundation of the ontology.

Notebook 01 checks file names, encoding, headers, SHA-256 values, keys and counts before writing any table. In the end it produces 20 tables: 8 staging tables, 11 ontology tables and 1 load audit table.

Before you start

- In the standard route, inspect the Lakehouse (LH_Furusato_&lt;PID&gt;) and completed Notebook 01 created in 24.6. Read the upload, import and Run all steps as an explanation of construction; do not repeat them, and perform the final count and SQL checks. Only for a separate manual build, use New item → Lakehouse in the work folder, enter this name and enable Lakehouse schemas.
- Prepare the eight CSV files in workshop/v3.0.0-preview/data/seed of the distribution (prefectures.csv, municipalities.csv, categories.csv, gifts.csv, businesses.csv, business_gifts.csv, donors.csv and donation_orders.csv).
- Prepare Notebook 01 (Notebook_01_Furusato_Prepare_Ontology_Data.ipynb) from the notebooks folder of the distribution.

</details>
