# A.1 期待値

[Lab 目次](../README.md) · [この章の目次](README.md)

この付録の期待値は、配布の静的データ（8つの CSV）と、8月の観測データ（3ファイル、それぞれ1回の取り込み）に対するものです。

Graph の一部だけを実体化した場合、別の期間を使った場合、同じファイルを複数回取り込んだ場合には、そのままでは当てはまりません。Notebook 05 の Gold には、最後の表（品質処理後の Gold の期待値）を使います。

**Entity type ごとの件数**

| Entity type | ソーステーブル | キー | 件数（ノード数） |
| --- | --- | --- | --- |
| Prefecture | ot_prefecture | PrefectureId | 47 |
| Municipality | ot_municipality | MunicipalityId | 1,741 |
| Donor | ot_donor | DonorId | 12,000 |
| GiftCategory | ot_gift_category | CategoryId | 30 |
| Gift | ot_gift | GiftId | 6,000 |
| Supplier | ot_supplier | SupplierId | 2,500 |
| Donation | ot_donation | DonationId | 80,000 |
| MunicipalityCategoryMetric | ot_mun_category_metric | MunCategoryMetricId | 4,403 |
| PrefectureCategoryMetric | ot_pref_category_metric | PrefCategoryMetricId | 662 |
| PrefectureDonationFlow | ot_pref_donation_flow | PrefDonationFlowId | 2,209 |
| 合計 | — | — | 109,592 |

**Relationship ごとの件数**

| Relationship | Origin → Target | キー列を持つテーブル | 件数（エッジ数） |
| --- | --- | --- | --- |
| MunicipalityInPrefecture | Municipality → Prefecture | ot_municipality | 1,741 |
| DonorLivesInPrefecture | Donor → Prefecture | ot_donor | 12,000 |
| SupplierInPrefecture | Supplier → Prefecture | ot_supplier | 2,500 |
| GiftInCategory | Gift → GiftCategory | ot_gift | 6,000 |
| MunicipalityCatalogsGift | Municipality → Gift | ot_gift | 6,000 |
| SupplierProvidesGift | Supplier → Gift | ot_supplier_gift | 14,514 |
| DonorMadeDonation | Donor → Donation | ot_donation | 80,000 |
| DonationToMunicipality | Donation → Municipality | ot_donation | 80,000 |
| DonationSelectedGift | Donation → Gift | ot_donation | 80,000 |
| MunHasCategoryMetric | Municipality → MunicipalityCategoryMetric | ot_mun_category_metric | 4,403 |
| MunMetricForCategory | MunicipalityCategoryMetric → GiftCategory | ot_mun_category_metric | 4,403 |
| PrefHasCategoryMetric | Prefecture → PrefectureCategoryMetric | ot_pref_category_metric | 662 |
| PrefMetricForCategory | PrefectureCategoryMetric → GiftCategory | ot_pref_category_metric | 662 |
| ResidencePrefHasFlow | Prefecture → PrefectureDonationFlow | ot_pref_donation_flow | 2,209 |
| FlowToRecipientPref | PrefectureDonationFlow → Prefecture | ot_pref_donation_flow | 2,209 |
| 合計 | — | — | 297,303 |

**回答の確認に使う代表値**

| 項目 | 期待値 |
| --- | --- |
| 静的データの寄付件数 | 80,000 |
| 静的データの寄付金額の合計 | 1,344,099,000 円 |
| 受入件数が1位の自治体 | 452025 都城市（宮崎県） 1,813 件 / 41,151,000 円 |
| その自治体で1位のカテゴリ | CategoryId 1 肉・肉加工品 1,147 件 / 28,901,000 円 |
| 東京都の自治体が受け入れた寄付 | 2,661 件 / 45,930,000 円 |
| 東京都に住む寄付者の寄付 | 8,784 件 / 146,543,000 円 |
| 東京都に住み、累計が1位の寄付者 | DonorId 2005075 野口啓介 8 件 / 383,000 円 |
| 寄付が0件の寄付者 | 18 |
| 受け入れた寄付が0件の自治体 | 10 |
| 登録された返礼品が0件の事業者 | 0 |

**8月の観測データの期待値**

| 指標 | 期待値 |
| --- | --- |
| 観測行数（重複を含む） | 15,000 |
| EventID の種類数（重複を除いた件数） | 14,900 |
| 重複したEventID | 100 |
| 観測金額の合計（重複を含む） | 253,886,000 円 |
| 重複を除いた金額の合計 | 252,058,000 円 |
| 観測期間（UTC） | 2026-08-01T00:02:47Z 〜 2026-08-31T23:58:20Z |
| UTC での日数 | 31 日（2026-08-01 〜 2026-08-31、欠けている日なし） |
| UTC の1日あたりの行数（重複を含む） | 450 〜 582 行（最少 2026-08-30 / 最多 2026-08-11） |
| UTC の1日あたりの行数（重複を除く） | 450 〜 540 行 |
| 日本時間での日数 | 32 日（2026-08-01 〜 2026-09-01） |
| 日本時間で 2026-09-01 になる行 | 178 行（UTC 2026-08-31T15:00:05Z 〜 2026-08-31T23:58:20Z） |
| 3つ目のファイルの公開時刻（PublishedAtUtc） | 2026-09-01T00:03:20Z |
| 観測件数が1位の自治体（重複を含む） | 452025 331 件 / 5,737,000 円 |

**品質処理後の Gold の期待値**

| 指標 | 期待値 |
| --- | --- |
| 受け入れた増分（RealtimeIncrement） | 14,900 件 / 252,058,000 円 |
| 隔離した重複行 | 100 |
| 静的データ（StaticSeed） | 80,000 件 / 1,344,099,000 円 |
| Gold 全体（gold.donations） | 94,900 件 / 1,596,157,000 円 |

> 東京都が受け入れた寄付（2,661件・45,930,000円）と、東京都の在住者の寄付（8,784件・146,543,000円）は別の値です。

> 静的データの 80,000件と8月の 15,000行を足した 95,000 という値には、意味がありません。

> 8月の観測データの値（452025 の 331件・5,737,000円など）は重複を含みます。重複を除いた全体は 14,900件・252,058,000円です。

<details>
<summary>English</summary>

## A.1 Expected values

The expected values in this appendix apply to the distributed static data (eight CSV files) and the August observation data (three files, each ingested once).

They do not apply as they stand to a partly materialized graph, to other periods or when the same file has been ingested more than once. For Notebook 05 Gold, use the last table (expected values after quality processing).

**Count per entity type**

| Entity type | Source table | Key | Count (nodes) |
| --- | --- | --- | --- |
| Prefecture | ot_prefecture | PrefectureId | 47 |
| Municipality | ot_municipality | MunicipalityId | 1,741 |
| Donor | ot_donor | DonorId | 12,000 |
| GiftCategory | ot_gift_category | CategoryId | 30 |
| Gift | ot_gift | GiftId | 6,000 |
| Supplier | ot_supplier | SupplierId | 2,500 |
| Donation | ot_donation | DonationId | 80,000 |
| MunicipalityCategoryMetric | ot_mun_category_metric | MunCategoryMetricId | 4,403 |
| PrefectureCategoryMetric | ot_pref_category_metric | PrefCategoryMetricId | 662 |
| PrefectureDonationFlow | ot_pref_donation_flow | PrefDonationFlowId | 2,209 |
| Total | — | — | 109,592 |

**Count per relationship**

| Relationship | Origin → Target | Table with the key columns | Count (edges) |
| --- | --- | --- | --- |
| MunicipalityInPrefecture | Municipality → Prefecture | ot_municipality | 1,741 |
| DonorLivesInPrefecture | Donor → Prefecture | ot_donor | 12,000 |
| SupplierInPrefecture | Supplier → Prefecture | ot_supplier | 2,500 |
| GiftInCategory | Gift → GiftCategory | ot_gift | 6,000 |
| MunicipalityCatalogsGift | Municipality → Gift | ot_gift | 6,000 |
| SupplierProvidesGift | Supplier → Gift | ot_supplier_gift | 14,514 |
| DonorMadeDonation | Donor → Donation | ot_donation | 80,000 |
| DonationToMunicipality | Donation → Municipality | ot_donation | 80,000 |
| DonationSelectedGift | Donation → Gift | ot_donation | 80,000 |
| MunHasCategoryMetric | Municipality → MunicipalityCategoryMetric | ot_mun_category_metric | 4,403 |
| MunMetricForCategory | MunicipalityCategoryMetric → GiftCategory | ot_mun_category_metric | 4,403 |
| PrefHasCategoryMetric | Prefecture → PrefectureCategoryMetric | ot_pref_category_metric | 662 |
| PrefMetricForCategory | PrefectureCategoryMetric → GiftCategory | ot_pref_category_metric | 662 |
| ResidencePrefHasFlow | Prefecture → PrefectureDonationFlow | ot_pref_donation_flow | 2,209 |
| FlowToRecipientPref | PrefectureDonationFlow → Prefecture | ot_pref_donation_flow | 2,209 |
| Total | — | — | 297,303 |

**Key values for checking answers**

| Item | Expected value |
| --- | --- |
| Donations in the static data | 80,000 |
| Total amount in the static data | JPY 1,344,099,000 |
| Municipality with the most donations received | 452025 都城市 (宮崎県) 1,813 donations / JPY 41,151,000 |
| Top category for that municipality | CategoryId 1 肉・肉加工品 1,147 donations / JPY 28,901,000 |
| Donations received by Tokyo municipalities | 2,661 donations / JPY 45,930,000 |
| Donations made by Tokyo residents | 8,784 donations / JPY 146,543,000 |
| Tokyo resident with the highest total | DonorId 2005075 野口啓介 8 donations / JPY 383,000 |
| Donors with no donations | 18 |
| Municipalities that received no donations | 10 |
| Suppliers with no registered gifts | 0 |

**Expected values for the August observation data**

| Measure | Expected value |
| --- | --- |
| Observed rows (including duplicates) | 15,000 |
| Distinct EventIDs (rows without duplicates) | 14,900 |
| Duplicated EventIDs | 100 |
| Observed amount (including duplicates) | JPY 253,886,000 |
| Amount without duplicates | JPY 252,058,000 |
| Observation period (UTC) | 2026-08-01T00:02:47Z 〜 2026-08-31T23:58:20Z |
| Days in UTC | 31 days (2026-08-01 to 2026-08-31, no missing day) |
| Rows per UTC day (including duplicates) | 450 to 582 rows (fewest 2026-08-30, most 2026-08-11) |
| Rows per UTC day (without duplicates) | 450 to 540 rows |
| Days in Japan time | 32 days (2026-08-01 to 2026-09-01) |
| Rows that fall on 2026-09-01 in Japan time | 178 rows (UTC 2026-08-31T15:00:05Z to 2026-08-31T23:58:20Z) |
| Publish time of the third file (PublishedAtUtc) | 2026-09-01T00:03:20Z |
| Municipality with the most observations (including duplicates) | 452025 331 observations / JPY 5,737,000 |

**Expected values after quality processing (Gold)**

| Measure | Expected value |
| --- | --- |
| Accepted increments (RealtimeIncrement) | 14,900 rows / JPY 252,058,000 |
| Quarantined duplicate rows | 100 |
| Static data (StaticSeed) | 80,000 rows / JPY 1,344,099,000 |
| All Gold rows (gold.donations) | 94,900 rows / JPY 1,596,157,000 |

> Donations received by Tokyo (2,661 / JPY 45,930,000) and donations by Tokyo residents (8,784 / JPY 146,543,000) are different values.

> Adding the 80,000 static donations and the 15,000 August rows into 95,000 has no meaning.

> Values from the August observation data (such as 331 / JPY 5,737,000 for 452025) include duplicates. Without duplicates, the totals are 14,900 / JPY 252,058,000.

</details>
