# 5.2 操作手順（2）

[Lab 目次](../README.md) · [この章の目次](README.md)

7. 11の ot_* テーブルの件数を付録Aと照合します（ot_donation 80,000、ot_municipality 1,741、ot_supplier_gift 14,514 など）。寄付が0件の Donor 18件と、受け入れが0件の Municipality 10件が残っているのが正しい状態です。
8. SQL analytics endpoint に反映されてから同じテーブルを SQL で読み、ot_donation が 80,000件、DonationAmountYen の合計が 1,344,099,000円であることを確認します。MunicipalityId の先頭のゼロが残っていることも確かめます。

> Notebook 01 は、検証済みのテーブルを安全に置き換える仕組みを持っています。完了した Notebook 01 を理由なく何度も実行しないでください。

<details>
<summary>English</summary>

## 5.2 Steps

7. Check the counts of the 11 ot_* tables against Appendix A (ot_donation 80,000, ot_municipality 1,741, ot_supplier_gift 14,514 and so on). It is correct that 18 donors with no donations and 10 municipalities that received none are kept.
8. Once the SQL analytics endpoint has synchronized, read the same tables with SQL and confirm that ot_donation has 80,000 rows and that DonationAmountYen totals JPY 1,344,099,000. Also confirm that MunicipalityId keeps its leading zeros.

> Notebook 01 has a safe mechanism for replacing validated tables. Do not rerun a completed Notebook 01 without a reason.

</details>
