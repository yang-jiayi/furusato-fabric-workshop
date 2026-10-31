# 17.7 17オブジェクト・143列を選択する

[Lab 目次](../README.md) · [この章の目次](README.md)

Data Agent の Add data / Sources で、自分の Lakehouse の SQL endpoint を選びます。下表の17オブジェクトだけを選び、展開して計143列を選びます。全テーブルを一括選択しません。6つの dbo.agent_* は Views、ほかは該当スキーマの Tables にあります。画面が更新されていなければソースのスキーマを再取得してから、実在する項目を選びます。ID を手入力で作りません。

**dbo.ot_prefecture：選択する9列**

| 列名 | SQL の型 |
| --- | --- |
| PrefectureId | bigint |
| PrefectureName | varchar |
| PrefectureNameEn | varchar |
| PrefReceivedStaticCount | bigint |
| PrefReceivedTotalYen | bigint |
| PrefReceivedAmountRank | bigint |
| PrefResidentStaticCount | bigint |
| PrefResidentTotalYen | bigint |
| PrefResidentAmountRank | bigint |

**dbo.ot_donor：選択する12列**

| 列名 | SQL の型 |
| --- | --- |
| DonorId | bigint |
| DonorName | varchar |
| DonorDisplayName | varchar |
| DonorAge | bigint |
| DonorOccupation | varchar |
| DonorOccupationEn | varchar |
| DonorStaticCount | bigint |
| DonorStaticTotalYen | bigint |
| DonorStaticMaxYen | bigint |
| DonorOverallAmountRank | bigint |
| DonorResidenceAmountRank | bigint |
| PrefectureId | bigint |

**dbo.ot_gift_category：選択する7列**

| 列名 | SQL の型 |
| --- | --- |
| CategoryId | bigint |
| CategoryName | varchar |
| CategoryNameEn | varchar |
| CategorySearchTerms | varchar |
| CategoryStaticCount | bigint |
| CategoryStaticTotalYen | bigint |
| CategoryAmountRank | bigint |

**dbo.ot_gift：選択する10列**

| 列名 | SQL の型 |
| --- | --- |
| GiftId | bigint |
| GiftName | varchar |
| GiftDisplayName | varchar |
| GiftSearchTerms | varchar |
| GiftNotes | varchar |
| GiftStaticCount | bigint |
| GiftStaticTotalYen | bigint |
| GiftAmountRank | bigint |
| CategoryId | bigint |
| MunicipalityId | varchar |

**dbo.ot_mun_category_metric：選択する6列**

| 列名 | SQL の型 |
| --- | --- |
| MunCategoryMetricId | varchar |
| MunCategoryStaticCount | bigint |
| MunCategoryTotalYen | bigint |
| MunCategoryAmountRank | bigint |
| MunicipalityId | varchar |
| CategoryId | bigint |

**dbo.ot_pref_donation_flow：選択する7列**

| 列名 | SQL の型 |
| --- | --- |
| PrefDonationFlowId | varchar |
| PrefFlowStaticCount | bigint |
| PrefFlowTotalYen | bigint |
| PrefFlowOriginRank | bigint |
| PrefFlowDestinationRank | bigint |
| ResidencePrefectureId | bigint |
| RecipientPrefectureId | bigint |

**dbo.agent_donation_detail：選択する19列**

| 列名 | SQL の型 |
| --- | --- |
| DonationId | bigint |
| DonationAmountYen | bigint |
| DonationPaymentMethod | varchar |
| DonatedAtUtc | datetime2 |
| DonatedAtJstText | varchar |
| DonationDateJst | varchar |
| DonationYearMonthJst | varchar |
| DonorId | bigint |
| DonorName | varchar |
| ResidentPrefectureId | bigint |
| ResidentPrefectureName | varchar |
| MunicipalityId | varchar |
| MunicipalityName | varchar |
| RecipientPrefectureId | bigint |
| RecipientPrefectureName | varchar |
| GiftId | bigint |
| GiftName | varchar |
| CategoryId | bigint |
| CategoryName | varchar |

**dbo.agent_donor_catalog_supplier：選択する10列**

| 列名 | SQL の型 |
| --- | --- |
| DonorId | bigint |
| DonorName | varchar |
| ResidentPrefectureId | bigint |
| ResidentPrefectureName | varchar |
| SupplierId | bigint |
| SupplierName | varchar |
| SupplierType | varchar |
| SupplierPrefectureId | bigint |
| SupplierPrefectureName | varchar |
| CatalogSupplierCount | bigint |

**dbo.agent_municipality_snapshot：選択する8列**

| 列名 | SQL の型 |
| --- | --- |
| MunicipalityId | varchar |
| MunicipalityName | varchar |
| PrefectureId | bigint |
| PrefectureName | varchar |
| DonationCount | bigint |
| AmountYen | bigint |
| AmountRank | bigint |
| RegisteredMunicipalitiesInPrefecture | bigint |

**dbo.agent_prefecture_category_metric：選択する13列**

| 列名 | SQL の型 |
| --- | --- |
| PrefCategoryMetricId | varchar |
| PrefectureId | bigint |
| PrefectureName | varchar |
| CategoryId | bigint |
| CategoryName | varchar |
| DonationCount | bigint |
| AmountYen | bigint |
| PrefectureMetricRelationship | varchar |
| PrefectureMetricDeclaredFrom | varchar |
| PrefectureMetricDeclaredTo | varchar |
| MetricCategoryRelationship | varchar |
| MetricCategoryDeclaredFrom | varchar |
| MetricCategoryDeclaredTo | varchar |

**dbo.agent_relationship_dictionary：選択する3列**

| 列名 | SQL の型 |
| --- | --- |
| RelationshipName | varchar |
| DeclaredFromEntity | varchar |
| DeclaredToEntity | varchar |

**dbo.agent_supplier_catalog：選択する10列**

| 列名 | SQL の型 |
| --- | --- |
| SupplierId | bigint |
| SupplierName | varchar |
| SupplierType | varchar |
| PrefectureId | bigint |
| PrefectureName | varchar |
| GiftId | bigint |
| GiftName | varchar |
| CategoryId | bigint |
| CategoryName | varchar |
| CatalogGiftCount | bigint |

**bronze.donation_events_raw：選択する6列**

| 列名 | SQL の型 |
| --- | --- |
| EventID | varchar |
| WorkshopRunId | varchar |
| ParticipantAlias | varchar |
| SourceFile | varchar |
| BatchId | varchar |
| _AnalyticsGenerationId | varchar |

**ops.analytics_publish_control：選択する4列**

| 列名 | SQL の型 |
| --- | --- |
| ControlKey | varchar |
| RunId | varchar |
| State | varchar |
| GenerationId | varchar |

**ops.dq_rule_results：選択する6列**

| 列名 | SQL の型 |
| --- | --- |
| RunId | varchar |
| RuleName | varchar |
| Severity | varchar |
| ActualValue | bigint |
| Status | varchar |
| _AnalyticsGenerationId | varchar |

**quarantine.donation_events_rejected：選択する7列**

| 列名 | SQL の型 |
| --- | --- |
| EventID | varchar |
| WorkshopRunId | varchar |
| ParticipantAlias | varchar |
| SourceFile | varchar |
| BatchId | varchar |
| RejectReason | varchar |
| _AnalyticsGenerationId | varchar |

**silver.donation_event：選択する6列**

| 列名 | SQL の型 |
| --- | --- |
| EventID | varchar |
| WorkshopRunId | varchar |
| ParticipantAlias | varchar |
| SourceFile | varchar |
| BatchId | varchar |
| _AnalyticsGenerationId | varchar |

選択契約には各テーブル・列の説明も含まれます。同じ説明を設定できる画面では、selection-contract.json の同じ path の description を使います。編集欄がない項目に独自の JSON フィールドを作りません。指示のコピーだけでは、この説明と実際の選択の一致まで確認したことにはなりません。17.15の構成確認で、UI 確認済みと定義照合済みを区別して記録します。

<details>
<summary>English</summary>

## 17.7 Select 17 objects and 143 columns

In the Data Agent Add data / Sources area, select your Lakehouse SQL endpoint. Select exactly the 17 objects below and expand them to select all 143 listed columns. Do not select every table. The six dbo.agent_* objects are under Views; the others are under their schema's Tables. If the UI is stale, refresh source schema before selecting actual objects. Never manufacture an ID.

**dbo.ot_prefecture: select 9 columns**

| Column | SQL type |
| --- | --- |
| PrefectureId | bigint |
| PrefectureName | varchar |
| PrefectureNameEn | varchar |
| PrefReceivedStaticCount | bigint |
| PrefReceivedTotalYen | bigint |
| PrefReceivedAmountRank | bigint |
| PrefResidentStaticCount | bigint |
| PrefResidentTotalYen | bigint |
| PrefResidentAmountRank | bigint |

**dbo.ot_donor: select 12 columns**

| Column | SQL type |
| --- | --- |
| DonorId | bigint |
| DonorName | varchar |
| DonorDisplayName | varchar |
| DonorAge | bigint |
| DonorOccupation | varchar |
| DonorOccupationEn | varchar |
| DonorStaticCount | bigint |
| DonorStaticTotalYen | bigint |
| DonorStaticMaxYen | bigint |
| DonorOverallAmountRank | bigint |
| DonorResidenceAmountRank | bigint |
| PrefectureId | bigint |

**dbo.ot_gift_category: select 7 columns**

| Column | SQL type |
| --- | --- |
| CategoryId | bigint |
| CategoryName | varchar |
| CategoryNameEn | varchar |
| CategorySearchTerms | varchar |
| CategoryStaticCount | bigint |
| CategoryStaticTotalYen | bigint |
| CategoryAmountRank | bigint |

**dbo.ot_gift: select 10 columns**

| Column | SQL type |
| --- | --- |
| GiftId | bigint |
| GiftName | varchar |
| GiftDisplayName | varchar |
| GiftSearchTerms | varchar |
| GiftNotes | varchar |
| GiftStaticCount | bigint |
| GiftStaticTotalYen | bigint |
| GiftAmountRank | bigint |
| CategoryId | bigint |
| MunicipalityId | varchar |

**dbo.ot_mun_category_metric: select 6 columns**

| Column | SQL type |
| --- | --- |
| MunCategoryMetricId | varchar |
| MunCategoryStaticCount | bigint |
| MunCategoryTotalYen | bigint |
| MunCategoryAmountRank | bigint |
| MunicipalityId | varchar |
| CategoryId | bigint |

**dbo.ot_pref_donation_flow: select 7 columns**

| Column | SQL type |
| --- | --- |
| PrefDonationFlowId | varchar |
| PrefFlowStaticCount | bigint |
| PrefFlowTotalYen | bigint |
| PrefFlowOriginRank | bigint |
| PrefFlowDestinationRank | bigint |
| ResidencePrefectureId | bigint |
| RecipientPrefectureId | bigint |

**dbo.agent_donation_detail: select 19 columns**

| Column | SQL type |
| --- | --- |
| DonationId | bigint |
| DonationAmountYen | bigint |
| DonationPaymentMethod | varchar |
| DonatedAtUtc | datetime2 |
| DonatedAtJstText | varchar |
| DonationDateJst | varchar |
| DonationYearMonthJst | varchar |
| DonorId | bigint |
| DonorName | varchar |
| ResidentPrefectureId | bigint |
| ResidentPrefectureName | varchar |
| MunicipalityId | varchar |
| MunicipalityName | varchar |
| RecipientPrefectureId | bigint |
| RecipientPrefectureName | varchar |
| GiftId | bigint |
| GiftName | varchar |
| CategoryId | bigint |
| CategoryName | varchar |

**dbo.agent_donor_catalog_supplier: select 10 columns**

| Column | SQL type |
| --- | --- |
| DonorId | bigint |
| DonorName | varchar |
| ResidentPrefectureId | bigint |
| ResidentPrefectureName | varchar |
| SupplierId | bigint |
| SupplierName | varchar |
| SupplierType | varchar |
| SupplierPrefectureId | bigint |
| SupplierPrefectureName | varchar |
| CatalogSupplierCount | bigint |

**dbo.agent_municipality_snapshot: select 8 columns**

| Column | SQL type |
| --- | --- |
| MunicipalityId | varchar |
| MunicipalityName | varchar |
| PrefectureId | bigint |
| PrefectureName | varchar |
| DonationCount | bigint |
| AmountYen | bigint |
| AmountRank | bigint |
| RegisteredMunicipalitiesInPrefecture | bigint |

**dbo.agent_prefecture_category_metric: select 13 columns**

| Column | SQL type |
| --- | --- |
| PrefCategoryMetricId | varchar |
| PrefectureId | bigint |
| PrefectureName | varchar |
| CategoryId | bigint |
| CategoryName | varchar |
| DonationCount | bigint |
| AmountYen | bigint |
| PrefectureMetricRelationship | varchar |
| PrefectureMetricDeclaredFrom | varchar |
| PrefectureMetricDeclaredTo | varchar |
| MetricCategoryRelationship | varchar |
| MetricCategoryDeclaredFrom | varchar |
| MetricCategoryDeclaredTo | varchar |

**dbo.agent_relationship_dictionary: select 3 columns**

| Column | SQL type |
| --- | --- |
| RelationshipName | varchar |
| DeclaredFromEntity | varchar |
| DeclaredToEntity | varchar |

**dbo.agent_supplier_catalog: select 10 columns**

| Column | SQL type |
| --- | --- |
| SupplierId | bigint |
| SupplierName | varchar |
| SupplierType | varchar |
| PrefectureId | bigint |
| PrefectureName | varchar |
| GiftId | bigint |
| GiftName | varchar |
| CategoryId | bigint |
| CategoryName | varchar |
| CatalogGiftCount | bigint |

**bronze.donation_events_raw: select 6 columns**

| Column | SQL type |
| --- | --- |
| EventID | varchar |
| WorkshopRunId | varchar |
| ParticipantAlias | varchar |
| SourceFile | varchar |
| BatchId | varchar |
| _AnalyticsGenerationId | varchar |

**ops.analytics_publish_control: select 4 columns**

| Column | SQL type |
| --- | --- |
| ControlKey | varchar |
| RunId | varchar |
| State | varchar |
| GenerationId | varchar |

**ops.dq_rule_results: select 6 columns**

| Column | SQL type |
| --- | --- |
| RunId | varchar |
| RuleName | varchar |
| Severity | varchar |
| ActualValue | bigint |
| Status | varchar |
| _AnalyticsGenerationId | varchar |

**quarantine.donation_events_rejected: select 7 columns**

| Column | SQL type |
| --- | --- |
| EventID | varchar |
| WorkshopRunId | varchar |
| ParticipantAlias | varchar |
| SourceFile | varchar |
| BatchId | varchar |
| RejectReason | varchar |
| _AnalyticsGenerationId | varchar |

**silver.donation_event: select 6 columns**

| Column | SQL type |
| --- | --- |
| EventID | varchar |
| WorkshopRunId | varchar |
| ParticipantAlias | varchar |
| SourceFile | varchar |
| BatchId | varchar |
| _AnalyticsGenerationId | varchar |

The selection contract also contains table and column descriptions. Where an editing field is available, use the description at the same path in selection-contract.json. Do not invent JSON fields for properties without an editor. Copying instructions alone does not verify these descriptions or actual selections; distinguish UI checks from definition checks in the configuration record in 17.15.

</details>
