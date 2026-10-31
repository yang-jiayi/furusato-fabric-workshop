# 10.3 完了の確認

[Lab 目次](../README.md) · [この章の目次](README.md)

**この章の完了条件**

| 確認すること | うまくいかないとき |
| --- | --- |
| 重複を含む 15,000行・253,886,000円、一意な EventID 14,900件、重複 100件 | 合わない場合は SourceFile ごとの件数を確認します。1ファイルが 10,000行なら二重に取り込まれています。送り直さずに講師に伝えます。 |
| 452025 の8月の観測が 331件・5,737,000円 | 0件の場合は、Timestamp column が DonatedAt か、キーの対応が MunicipalityID → MunicipalityId か、選んだのが DonationEvents テーブルかを確認します。Ontology の更新が終わってから再確認します。 |
| 観測の値を静的データの値と足していない | 452025 の静的データは 1,813件・41,151,000円で、別の値です。合計しません。 |

<details>
<summary>English</summary>

## 10.3 Check your work

**Completion checks for this chapter**

| What to check | If it does not work |
| --- | --- |
| 15,000 rows / JPY 253,886,000 including duplicates, 14,900 unique EventIDs and 100 duplicates | If they do not match, check the counts per SourceFile. If one file has 10,000 rows, it was ingested twice. Do not resend; tell the instructor. |
| August observations for 452025 are 331 / JPY 5,737,000 | If the result is zero, check that the Timestamp column is DonatedAt, that the key mapping is MunicipalityID → MunicipalityId and that you chose the DonationEvents table. Check again after the ontology update has finished. |
| Observation values are not added to static values | The static data for 452025 is 1,813 / JPY 41,151,000, a separate value. Never add them together. |

</details>
