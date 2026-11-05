# 10.1 この章で行うこと

[Lab 目次](../README.md) · [この章の目次](README.md)

KQL の集計結果と対象 OneLake Delta の内容を別々に確認します。参照 KQL 結果は3ファイル計15,000観測ですが、それだけでは対象 Delta の完全性を示しません。時系列 Property の定義・binding 表示、native query の利用可否、実行した query と結果も個別に確認します。

KQL の DonationEvents は15,000観測・253,886,000円、EventID は14,900件が一意で、重複行は100件です。これは OneLake Delta の内容や Notebook 05 の Gold とは別の母集団です。

準備するもの・確認すること

- 9章で001の取り込み5,000行を確認します。標準の自動経路ではルールの開始と24.7の readiness を確認してから、002へ進みます。手動回復を行った場合はその記録を残し、自動実行と重ねません。

<details>
<summary>English</summary>

## 10.1 What you will do

Check the KQL summary and the target OneLake Delta contents separately. The reference KQL result covers 15,000 observations across three files, but does not establish that the target Delta is complete. Separately check the time-series property definition/binding, native-query availability, and any executed query and result.

KQL DonationEvents has 15,000 observations / JPY 253,886,000, with 14,900 unique EventIDs and 100 duplicate rows. This is separate from OneLake Delta contents and Notebook 05 Gold.

Before you start

- Confirm the 5,000 rows ingested for 001 in Chapter 9. For the standard automatic route, verify the started rule and readiness in 24.7 before proceeding to 002. Retain any manual-recovery record and do not overlap manual and automatic runs.

</details>
