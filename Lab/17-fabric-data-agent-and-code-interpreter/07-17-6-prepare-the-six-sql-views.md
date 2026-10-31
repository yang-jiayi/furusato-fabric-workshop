# 17.6 SQL の6つのビューを用意する

[Lab 目次](../README.md) · [この章の目次](README.md)

Lakehouse の SQL analytics endpoint を開き、New SQL query を選びます。下の6つの CREATE VIEW を上から順に、各ブロックごとに1回ずつ実行します。5番目の agent_relationship_dictionary を先に作成し、それを参照する6番目の agent_prefecture_category_metric はその後に作成します。これらは読み取り用のビューで、CSV や基礎テーブルの値は変更しません。既にあるビューは再作成せず、定義を下記と照合します。異なる場合は現在の定義を保存してから、同じ名前のビューの定義だけを変更します。別の参加者のビューやテーブルを削除しません。

テーブルが見えなければ、5章の Notebook 01 と11章の Notebook 05 の完了、SQL endpoint の同期状態、接続先 Lakehouse を確認します。CREATE VIEW 権限がなければ、その Lakehouse の管理者に権限または下記の実行を依頼します。ビュー名だけがある状態では完了ではありません。

実行するファイル：workshop/v3.0.0-preview/data-agent/candidates/source-grounded/views/agent_donation_detail.sql

**SQL**

```sql
CREATE VIEW dbo.agent_donation_detail AS
SELECT
    d.DonationId,
    d.DonationAmountYen,
    d.DonationPaymentMethod,
    d.DonatedAtUtc,
    d.DonatedAtJstText,
    d.DonationDateJst,
    d.DonationYearMonthJst,
    d.DonationDataLayer,
    n.DonorId,
    n.DonorName,
    n.PrefectureId AS ResidentPrefectureId,
    rp.PrefectureName AS ResidentPrefectureName,
    m.MunicipalityId,
    m.MunicipalityName,
    m.PrefectureId AS RecipientPrefectureId,
    mp.PrefectureName AS RecipientPrefectureName,
    g.GiftId,
    g.GiftName,
    c.CategoryId,
    c.CategoryName
FROM dbo.ot_donation AS d
JOIN dbo.ot_donor AS n ON n.DonorId = d.DonorId
JOIN dbo.ot_prefecture AS rp ON rp.PrefectureId = n.PrefectureId
JOIN dbo.ot_municipality AS m ON m.MunicipalityId = d.MunicipalityId
JOIN dbo.ot_prefecture AS mp ON mp.PrefectureId = m.PrefectureId
JOIN dbo.ot_gift AS g ON g.GiftId = d.GiftId
JOIN dbo.ot_gift_category AS c ON c.CategoryId = g.CategoryId
```

実行するファイル：workshop/v3.0.0-preview/data-agent/candidates/source-grounded/views/agent_donor_catalog_supplier.sql

**SQL**

```sql
CREATE VIEW dbo.agent_donor_catalog_supplier AS
SELECT
    pairs.DonorId,
    pairs.DonorName,
    pairs.ResidentPrefectureId,
    pairs.ResidentPrefectureName,
    pairs.SupplierId,
    pairs.SupplierName,
    pairs.SupplierType,
    pairs.SupplierPrefectureId,
    pairs.SupplierPrefectureName,
    COUNT_BIG(*) OVER (PARTITION BY pairs.DonorId) AS CatalogSupplierCount
FROM (
    SELECT DISTINCT
        n.DonorId,
        n.DonorName,
        n.PrefectureId AS ResidentPrefectureId,
        rp.PrefectureName AS ResidentPrefectureName,
        s.SupplierId,
        s.SupplierName,
        s.SupplierType,
        s.PrefectureId AS SupplierPrefectureId,
        sp.PrefectureName AS SupplierPrefectureName
    FROM dbo.ot_donation AS d
    JOIN dbo.ot_donor AS n ON n.DonorId = d.DonorId
    JOIN dbo.ot_prefecture AS rp ON rp.PrefectureId = n.PrefectureId
    JOIN dbo.ot_supplier_gift AS sg ON sg.GiftId = d.GiftId
    JOIN dbo.ot_supplier AS s ON s.SupplierId = sg.SupplierId
    JOIN dbo.ot_prefecture AS sp ON sp.PrefectureId = s.PrefectureId
) AS pairs
```

実行するファイル：workshop/v3.0.0-preview/data-agent/candidates/source-grounded/views/agent_municipality_snapshot.sql

**SQL**

```sql
CREATE VIEW dbo.agent_municipality_snapshot AS
SELECT
    m.MunicipalityId,
    m.MunicipalityName,
    m.PrefectureId,
    p.PrefectureName,
    m.MunicipalityStaticCount AS DonationCount,
    m.MunicipalityStaticTotalYen AS AmountYen,
    m.MunicipalityAmountRank AS AmountRank,
    COUNT_BIG(*) OVER (PARTITION BY m.PrefectureId) AS RegisteredMunicipalitiesInPrefecture
FROM dbo.ot_municipality AS m
JOIN dbo.ot_prefecture AS p ON p.PrefectureId = m.PrefectureId
```

実行するファイル：workshop/v3.0.0-preview/data-agent/candidates/source-grounded/views/agent_supplier_catalog.sql

**SQL**

```sql
CREATE VIEW dbo.agent_supplier_catalog AS
SELECT
    s.SupplierId,
    s.SupplierName,
    s.SupplierType,
    s.PrefectureId,
    p.PrefectureName,
    g.GiftId,
    g.GiftName,
    g.CategoryId,
    c.CategoryName,
    COUNT_BIG(*) OVER (PARTITION BY s.SupplierId) AS CatalogGiftCount
FROM dbo.ot_supplier_gift AS sg
JOIN dbo.ot_supplier AS s ON s.SupplierId = sg.SupplierId
JOIN dbo.ot_prefecture AS p ON p.PrefectureId = s.PrefectureId
JOIN dbo.ot_gift AS g ON g.GiftId = sg.GiftId
JOIN dbo.ot_gift_category AS c ON c.CategoryId = g.CategoryId
```

実行するファイル：workshop/v3.0.0-preview/data-agent/candidates/complete-contract/views/agent_relationship_dictionary.sql

**SQL**

```sql
CREATE VIEW dbo.agent_relationship_dictionary AS
SELECT
    CAST('MunicipalityInPrefecture' AS varchar(64)) AS RelationshipName,
    CAST('Municipality' AS varchar(64)) AS DeclaredFromEntity,
    CAST('Prefecture' AS varchar(64)) AS DeclaredToEntity
UNION ALL SELECT 'DonorMadeDonation','Donor','Donation'
UNION ALL SELECT 'DonationSelectedGift','Donation','Gift'
UNION ALL SELECT 'SupplierProvidesGift','Supplier','Gift'
UNION ALL SELECT 'DonorLivesInPrefecture','Donor','Prefecture'
UNION ALL SELECT 'SupplierInPrefecture','Supplier','Prefecture'
UNION ALL SELECT 'DonationToMunicipality','Donation','Municipality'
UNION ALL SELECT 'MunicipalityCatalogsGift','Municipality','Gift'
UNION ALL SELECT 'GiftInCategory','Gift','GiftCategory'
UNION ALL SELECT 'MunHasCategoryMetric','Municipality','MunicipalityCategoryMetric'
UNION ALL SELECT 'MunMetricForCategory','MunicipalityCategoryMetric','GiftCategory'
UNION ALL SELECT 'PrefHasCategoryMetric','Prefecture','PrefectureCategoryMetric'
UNION ALL SELECT 'PrefMetricForCategory','PrefectureCategoryMetric','GiftCategory'
UNION ALL SELECT 'ResidencePrefHasFlow','Prefecture','PrefectureDonationFlow'
UNION ALL SELECT 'FlowToRecipientPref','PrefectureDonationFlow','Prefecture'
```

実行するファイル：workshop/v3.0.0-preview/data-agent/candidates/complete-contract/views/agent_prefecture_category_metric.sql

**SQL**

```sql
CREATE VIEW dbo.agent_prefecture_category_metric AS
SELECT
    m.PrefCategoryMetricId,
    m.PrefectureId,
    p.PrefectureName,
    m.CategoryId,
    c.CategoryName,
    m.PrefCategoryStaticCount AS DonationCount,
    m.PrefCategoryTotalYen AS AmountYen,
    r1.RelationshipName AS PrefectureMetricRelationship,
    r1.DeclaredFromEntity AS PrefectureMetricDeclaredFrom,
    r1.DeclaredToEntity AS PrefectureMetricDeclaredTo,
    r2.RelationshipName AS MetricCategoryRelationship,
    r2.DeclaredFromEntity AS MetricCategoryDeclaredFrom,
    r2.DeclaredToEntity AS MetricCategoryDeclaredTo
FROM dbo.ot_pref_category_metric AS m
JOIN dbo.ot_prefecture AS p ON p.PrefectureId=m.PrefectureId
JOIN dbo.ot_gift_category AS c ON c.CategoryId=m.CategoryId
CROSS JOIN dbo.agent_relationship_dictionary AS r1
CROSS JOIN dbo.agent_relationship_dictionary AS r2
WHERE r1.RelationshipName='PrefHasCategoryMetric'
  AND r2.RelationshipName='PrefMetricForCategory'
```

6つとも作成または照合できたら、各ビューを SELECT TOP (5) * FROM dbo.&lt;ビュー名&gt; で開き、エラーなく結果が返ることを確認します。続いて次の照会を実行し、17.7の選択対象の全列名・型と照合します。実テーブルに追加の列がある場合でも、選択するのは17.7の143列だけです。たとえば agent_donation_detail の DonationDataLayer は選択しません。品質管理テーブルが未作成の場合は11章に戻り、空の表を代わりに作りません。

**SQL**

```sql
-- Read-only independent schema evidence for the measured profile.
-- Save the result privately as a JSON array of these four column names.
SELECT [TABLE_SCHEMA], [TABLE_NAME], [COLUMN_NAME], [DATA_TYPE]
FROM [INFORMATION_SCHEMA].[COLUMNS]
WHERE ([TABLE_SCHEMA] = 'dbo' AND [TABLE_NAME] IN (
    'ot_prefecture', 'ot_donor', 'ot_gift_category', 'ot_gift',
    'ot_mun_category_metric', 'ot_pref_donation_flow',
    'agent_donation_detail', 'agent_donor_catalog_supplier',
    'agent_municipality_snapshot', 'agent_prefecture_category_metric',
    'agent_relationship_dictionary', 'agent_supplier_catalog'))
   OR ([TABLE_SCHEMA] = 'bronze' AND [TABLE_NAME] = 'donation_events_raw')
   OR ([TABLE_SCHEMA] = 'silver' AND [TABLE_NAME] = 'donation_event')
   OR ([TABLE_SCHEMA] = 'quarantine' AND [TABLE_NAME] = 'donation_events_rejected')
   OR ([TABLE_SCHEMA] = 'ops' AND [TABLE_NAME] IN ('analytics_publish_control', 'dq_rule_results'))
ORDER BY [TABLE_SCHEMA], [TABLE_NAME], [ORDINAL_POSITION];
```

<details>
<summary>English</summary>

## 17.6 Prepare the six SQL views

Open the Lakehouse SQL analytics endpoint and select New SQL query. Run the six CREATE VIEW blocks from top to bottom, once each and separately. Create the fifth view, agent_relationship_dictionary, before the sixth view, agent_prefecture_category_metric, which references it. These are read-only views and do not change CSV or base-table values. For existing views, compare their definitions with the blocks instead of creating them again. Save any differing definition before changing only that same view's definition. Do not delete other participants' views or tables.

If tables are absent, check completion of Notebook 01 in Chapter 5 and Notebook 05 in Chapter 11, SQL endpoint synchronization and the selected Lakehouse. If CREATE VIEW permission is missing, request permission or execution of the blocks from that Lakehouse's administrator. A view name alone does not establish completion.

File to run: workshop/v3.0.0-preview/data-agent/candidates/source-grounded/views/agent_donation_detail.sql

**SQL**

```sql
CREATE VIEW dbo.agent_donation_detail AS
SELECT
    d.DonationId,
    d.DonationAmountYen,
    d.DonationPaymentMethod,
    d.DonatedAtUtc,
    d.DonatedAtJstText,
    d.DonationDateJst,
    d.DonationYearMonthJst,
    d.DonationDataLayer,
    n.DonorId,
    n.DonorName,
    n.PrefectureId AS ResidentPrefectureId,
    rp.PrefectureName AS ResidentPrefectureName,
    m.MunicipalityId,
    m.MunicipalityName,
    m.PrefectureId AS RecipientPrefectureId,
    mp.PrefectureName AS RecipientPrefectureName,
    g.GiftId,
    g.GiftName,
    c.CategoryId,
    c.CategoryName
FROM dbo.ot_donation AS d
JOIN dbo.ot_donor AS n ON n.DonorId = d.DonorId
JOIN dbo.ot_prefecture AS rp ON rp.PrefectureId = n.PrefectureId
JOIN dbo.ot_municipality AS m ON m.MunicipalityId = d.MunicipalityId
JOIN dbo.ot_prefecture AS mp ON mp.PrefectureId = m.PrefectureId
JOIN dbo.ot_gift AS g ON g.GiftId = d.GiftId
JOIN dbo.ot_gift_category AS c ON c.CategoryId = g.CategoryId
```

File to run: workshop/v3.0.0-preview/data-agent/candidates/source-grounded/views/agent_donor_catalog_supplier.sql

**SQL**

```sql
CREATE VIEW dbo.agent_donor_catalog_supplier AS
SELECT
    pairs.DonorId,
    pairs.DonorName,
    pairs.ResidentPrefectureId,
    pairs.ResidentPrefectureName,
    pairs.SupplierId,
    pairs.SupplierName,
    pairs.SupplierType,
    pairs.SupplierPrefectureId,
    pairs.SupplierPrefectureName,
    COUNT_BIG(*) OVER (PARTITION BY pairs.DonorId) AS CatalogSupplierCount
FROM (
    SELECT DISTINCT
        n.DonorId,
        n.DonorName,
        n.PrefectureId AS ResidentPrefectureId,
        rp.PrefectureName AS ResidentPrefectureName,
        s.SupplierId,
        s.SupplierName,
        s.SupplierType,
        s.PrefectureId AS SupplierPrefectureId,
        sp.PrefectureName AS SupplierPrefectureName
    FROM dbo.ot_donation AS d
    JOIN dbo.ot_donor AS n ON n.DonorId = d.DonorId
    JOIN dbo.ot_prefecture AS rp ON rp.PrefectureId = n.PrefectureId
    JOIN dbo.ot_supplier_gift AS sg ON sg.GiftId = d.GiftId
    JOIN dbo.ot_supplier AS s ON s.SupplierId = sg.SupplierId
    JOIN dbo.ot_prefecture AS sp ON sp.PrefectureId = s.PrefectureId
) AS pairs
```

File to run: workshop/v3.0.0-preview/data-agent/candidates/source-grounded/views/agent_municipality_snapshot.sql

**SQL**

```sql
CREATE VIEW dbo.agent_municipality_snapshot AS
SELECT
    m.MunicipalityId,
    m.MunicipalityName,
    m.PrefectureId,
    p.PrefectureName,
    m.MunicipalityStaticCount AS DonationCount,
    m.MunicipalityStaticTotalYen AS AmountYen,
    m.MunicipalityAmountRank AS AmountRank,
    COUNT_BIG(*) OVER (PARTITION BY m.PrefectureId) AS RegisteredMunicipalitiesInPrefecture
FROM dbo.ot_municipality AS m
JOIN dbo.ot_prefecture AS p ON p.PrefectureId = m.PrefectureId
```

File to run: workshop/v3.0.0-preview/data-agent/candidates/source-grounded/views/agent_supplier_catalog.sql

**SQL**

```sql
CREATE VIEW dbo.agent_supplier_catalog AS
SELECT
    s.SupplierId,
    s.SupplierName,
    s.SupplierType,
    s.PrefectureId,
    p.PrefectureName,
    g.GiftId,
    g.GiftName,
    g.CategoryId,
    c.CategoryName,
    COUNT_BIG(*) OVER (PARTITION BY s.SupplierId) AS CatalogGiftCount
FROM dbo.ot_supplier_gift AS sg
JOIN dbo.ot_supplier AS s ON s.SupplierId = sg.SupplierId
JOIN dbo.ot_prefecture AS p ON p.PrefectureId = s.PrefectureId
JOIN dbo.ot_gift AS g ON g.GiftId = sg.GiftId
JOIN dbo.ot_gift_category AS c ON c.CategoryId = g.CategoryId
```

File to run: workshop/v3.0.0-preview/data-agent/candidates/complete-contract/views/agent_relationship_dictionary.sql

**SQL**

```sql
CREATE VIEW dbo.agent_relationship_dictionary AS
SELECT
    CAST('MunicipalityInPrefecture' AS varchar(64)) AS RelationshipName,
    CAST('Municipality' AS varchar(64)) AS DeclaredFromEntity,
    CAST('Prefecture' AS varchar(64)) AS DeclaredToEntity
UNION ALL SELECT 'DonorMadeDonation','Donor','Donation'
UNION ALL SELECT 'DonationSelectedGift','Donation','Gift'
UNION ALL SELECT 'SupplierProvidesGift','Supplier','Gift'
UNION ALL SELECT 'DonorLivesInPrefecture','Donor','Prefecture'
UNION ALL SELECT 'SupplierInPrefecture','Supplier','Prefecture'
UNION ALL SELECT 'DonationToMunicipality','Donation','Municipality'
UNION ALL SELECT 'MunicipalityCatalogsGift','Municipality','Gift'
UNION ALL SELECT 'GiftInCategory','Gift','GiftCategory'
UNION ALL SELECT 'MunHasCategoryMetric','Municipality','MunicipalityCategoryMetric'
UNION ALL SELECT 'MunMetricForCategory','MunicipalityCategoryMetric','GiftCategory'
UNION ALL SELECT 'PrefHasCategoryMetric','Prefecture','PrefectureCategoryMetric'
UNION ALL SELECT 'PrefMetricForCategory','PrefectureCategoryMetric','GiftCategory'
UNION ALL SELECT 'ResidencePrefHasFlow','Prefecture','PrefectureDonationFlow'
UNION ALL SELECT 'FlowToRecipientPref','PrefectureDonationFlow','Prefecture'
```

File to run: workshop/v3.0.0-preview/data-agent/candidates/complete-contract/views/agent_prefecture_category_metric.sql

**SQL**

```sql
CREATE VIEW dbo.agent_prefecture_category_metric AS
SELECT
    m.PrefCategoryMetricId,
    m.PrefectureId,
    p.PrefectureName,
    m.CategoryId,
    c.CategoryName,
    m.PrefCategoryStaticCount AS DonationCount,
    m.PrefCategoryTotalYen AS AmountYen,
    r1.RelationshipName AS PrefectureMetricRelationship,
    r1.DeclaredFromEntity AS PrefectureMetricDeclaredFrom,
    r1.DeclaredToEntity AS PrefectureMetricDeclaredTo,
    r2.RelationshipName AS MetricCategoryRelationship,
    r2.DeclaredFromEntity AS MetricCategoryDeclaredFrom,
    r2.DeclaredToEntity AS MetricCategoryDeclaredTo
FROM dbo.ot_pref_category_metric AS m
JOIN dbo.ot_prefecture AS p ON p.PrefectureId=m.PrefectureId
JOIN dbo.ot_gift_category AS c ON c.CategoryId=m.CategoryId
CROSS JOIN dbo.agent_relationship_dictionary AS r1
CROSS JOIN dbo.agent_relationship_dictionary AS r2
WHERE r1.RelationshipName='PrefHasCategoryMetric'
  AND r2.RelationshipName='PrefMetricForCategory'
```

Once all six views are created or checked, run SELECT TOP (5) * FROM dbo.&lt;view name&gt; for each and verify successful results. Then run the following inventory query and compare every selected column name and type with 17.7. Physical objects may have additional columns; select only the 143 listed columns. For example, leave DonationDataLayer in agent_donation_detail unselected. If quality tables are absent, return to Chapter 11; do not create empty substitutes.

**SQL**

```sql
-- Read-only independent schema evidence for the measured profile.
-- Save the result privately as a JSON array of these four column names.
SELECT [TABLE_SCHEMA], [TABLE_NAME], [COLUMN_NAME], [DATA_TYPE]
FROM [INFORMATION_SCHEMA].[COLUMNS]
WHERE ([TABLE_SCHEMA] = 'dbo' AND [TABLE_NAME] IN (
    'ot_prefecture', 'ot_donor', 'ot_gift_category', 'ot_gift',
    'ot_mun_category_metric', 'ot_pref_donation_flow',
    'agent_donation_detail', 'agent_donor_catalog_supplier',
    'agent_municipality_snapshot', 'agent_prefecture_category_metric',
    'agent_relationship_dictionary', 'agent_supplier_catalog'))
   OR ([TABLE_SCHEMA] = 'bronze' AND [TABLE_NAME] = 'donation_events_raw')
   OR ([TABLE_SCHEMA] = 'silver' AND [TABLE_NAME] = 'donation_event')
   OR ([TABLE_SCHEMA] = 'quarantine' AND [TABLE_NAME] = 'donation_events_rejected')
   OR ([TABLE_SCHEMA] = 'ops' AND [TABLE_NAME] IN ('analytics_publish_control', 'dq_rule_results'))
ORDER BY [TABLE_SCHEMA], [TABLE_NAME], [ORDINAL_POSITION];
```

</details>
