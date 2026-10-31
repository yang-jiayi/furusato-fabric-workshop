# 10.1 この章で行うこと

[Lab 目次](../README.md) · [この章の目次](README.md)

残りの2ファイル（002 と 003）を1本ずつ取り込み、8月の観測データ全体（15,000行）を KQL で確認します。そのうえで、Municipality の時系列 Property を Eventhouse の DonationEvents にバインドします。

配布データには、意図的な重複が 100件あります。DonationEvents と時系列 Property は重複を含んだまま扱い、重複を除いた値（14,900件）は、KQL での確認と Notebook 05 の Gold で別に扱います。

準備するもの・確認すること

- 9章で001の取り込み5,000行を確認します。標準の自動経路ではルールの開始と24.7の readiness を確認してから、002へ進みます。手動回復を行った場合はその記録を残し、自動実行と重ねません。

<details>
<summary>English</summary>

## 10.1 What you will do

Ingest the remaining two files (002 and 003) one at a time and check the whole August observation data (15,000 rows) with KQL. Then bind the time-series property of Municipality to DonationEvents in the Eventhouse.

The distributed data contains 100 intentional duplicates. DonationEvents and the time-series property keep the duplicates; the deduplicated value (14,900) is handled separately in KQL checks and in Notebook 05 Gold.

Before you start

- Confirm the 5,000 rows ingested for 001 in Chapter 9. For the standard automatic route, verify the started rule and readiness in 24.7 before proceeding to 002. Retain any manual-recovery record and do not overlap manual and automatic runs.

</details>
