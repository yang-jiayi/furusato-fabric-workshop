# 3.2 操作手順

[Lab 目次](../README.md) · [この章の目次](README.md)

1. 付録Aの表で、基幹の7つ（マスター6つと取引1つ）と、集計用の3つ（MunicipalityCategoryMetric、PrefectureCategoryMetric、PrefectureDonationFlow）を確認します。
2. 2つの地域の経路を区別します。居住地は Donor -DonorLivesInPrefecture-&gt; Prefecture、受入地は Donation -DonationToMunicipality-&gt; Municipality -MunicipalityInPrefecture-&gt; Prefecture です。東京都の場合、受け入れた寄付は 2,661件・45,930,000円、在住者の寄付は 8,784件・146,543,000円で、値が違います。
3. 事業者に関する意味を確認します。SupplierInPrefecture は事業者の登録地、SupplierProvidesGift は返礼品のカタログ登録、DonationSelectedGift は寄付者が選んだ返礼品です。どれも発送や受け取りを表しません。Donor と Supplier を直接結ぶ関係はなく、Supplier → Gift ← Donation ← Donor とたどります。
4. 静的データと8月の観測データを分けます。静的データは2025年の寄付 80,000件・1,344,099,000円です。8月の観測データは2026年8月の3ファイル・15,000行で、001 の末尾 100行が 002 の先頭にもう一度含まれるため、EventID の重複が 100件あります。重複を除くと 14,900件です。2つを足した値には意味がありません。
5. 集計用の Entity の意味を確認します。これらは Notebook 01 が作った保存済みの集計です。たとえば 452025-01（都城市 × 肉・肉加工品）の 1,147件・28,901,000円は、都城市全体の 1,813件・41,151,000円の一部です。PrefectureDonationFlow の 13-01（東京都→北海道、637件・9,918,000円）と 01-13（北海道→東京都、108件・1,876,000円）は別のインスタンスです。集計値どうしを足しません。
6. Metrics（12章）は Semantic model の DAX メジャーを参照するもので、保存済みの集計 Entity とは別物です。また、8月の観測データは新しい Entity にはせず、10章で Municipality の時系列 Property（IncomingDonationAmountYen）としてバインドします。

> 8月の観測データの日時は UTC です。日本時間に変換すると、2026-08-31T15:00:05Z 以降の 178行が9月1日になりますが、これは正常です。

<details>
<summary>English</summary>

## 3.2 Steps

1. Using the tables in Appendix A, identify the seven core entity types (six masters and one transaction) and the three summary entity types (MunicipalityCategoryMetric, PrefectureCategoryMetric and PrefectureDonationFlow).
2. Distinguish the two geographic paths. Residence is Donor -DonorLivesInPrefecture-&gt; Prefecture; the recipient is Donation -DonationToMunicipality-&gt; Municipality -MunicipalityInPrefecture-&gt; Prefecture. For Tokyo, donations received are 2,661 / JPY 45,930,000, while donations by residents are 8,784 / JPY 146,543,000.
3. Check the meanings around suppliers. SupplierInPrefecture is where a supplier is registered, SupplierProvidesGift is a catalog registration of a gift, and DonationSelectedGift is the gift a donor selected. None of them shows that a gift was shipped or delivered. There is no direct relationship between Donor and Supplier; the path is Supplier → Gift ← Donation ← Donor.
4. Separate the static data from the August observation data. The static data is 80,000 donations in 2025 totaling JPY 1,344,099,000. The August observation data is three files with 15,000 rows from August 2026; the last 100 rows of file 001 appear again at the start of file 002, so 100 EventIDs are duplicated. Without duplicates there are 14,900. Adding the two datasets together has no meaning.
5. Check the meaning of the summary entities. They are stored totals created by Notebook 01. For example, 452025-01 (Miyakonojo × meat and meat products) with 1,147 donations / JPY 28,901,000 is part of Miyakonojo's overall 1,813 / JPY 41,151,000. In PrefectureDonationFlow, 13-01 (Tokyo → Hokkaido, 637 / JPY 9,918,000) and 01-13 (Hokkaido → Tokyo, 108 / JPY 1,876,000) are different instances. Never add summary values together.
6. Metrics (Chapter 12) refer to DAX measures in the semantic model and are different from stored summary entities. The August observation data does not become a new entity; in Chapter 10 you bind it to the time-series property IncomingDonationAmountYen on Municipality.

> Timestamps in the August observation data are UTC. Converted to Japan time, the 178 rows from 2026-08-31T15:00:05Z onward fall on 1 September; this is expected.

</details>
