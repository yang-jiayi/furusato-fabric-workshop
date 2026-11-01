# 11.2 操作手順（5）

[Lab 目次](../README.md) · [この章の目次](README.md)

7. 現在の読み取り専用 SQL catalog では gold.donations が公開されていないため、この環境の SQL から Gold の行数・金額を確認できません。テーブルが別の許可された実行結果で実際に確認できる場合だけ、DataSource 別の値と集計条件を記録し、期待値と照合します。94,900件・1,596,157,000円等の fixture 期待値を、未確認の SQL 実測値や現在の成功結果として記載しません。

![Lakehouse の Explorer で gold.donations を選んだ画面。DonationId、金額、日時、支払方法、DataSource、IsHighValue、DonorId などの列の表](../assets/p30-11-schema-preview.png)

gold.donations の列と先頭の行。DataSource で静的データと増分を区別し、IsHighValue は 57,000円を超える寄付で true

<details>
<summary>English</summary>

## 11.2 Steps

7. gold.donations is not exposed in the current read-only SQL catalog, so Gold row counts and amounts cannot be verified from SQL in this environment. Only if the table is actually available through another authorized run output, record its values by DataSource and aggregation scope, then compare them with expected values. Do not present fixture expectations such as 94,900 / JPY 1,596,157,000 as unverified SQL measurements or current successful results.

![gold.donations in Lakehouse Explorer: a table with columns such as DonationId, amount, dates, payment method, DataSource, IsHighValue and DonorId.](../assets/p30-11-schema-preview.png)

gold.donations columns and first rows: DataSource separates static data from increments, and IsHighValue is true for donations over JPY 57,000.

</details>
