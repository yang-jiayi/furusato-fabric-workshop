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

143列は業務列だけの選択契約で、システムの世代管理列は含みません。サービスが親テーブルの選択を展開した結果、最初のソース探索に無かった _WorkshopGenerationId が選択される場合があります。17テーブルを選んだだけで143列と判断せず、現在の列の選択状態を読み直します。

**143業務列の対象外となる6つの世代管理列**

| 親テーブル（選択を残す） | 表示された場合に外すシステム列 |
| --- | --- |
| dbo.ot_donor | _WorkshopGenerationId |
| dbo.ot_gift | _WorkshopGenerationId |
| dbo.ot_gift_category | _WorkshopGenerationId |
| dbo.ot_mun_category_metric | _WorkshopGenerationId |
| dbo.ot_pref_donation_flow | _WorkshopGenerationId |
| dbo.ot_prefecture | _WorkshopGenerationId |

1. SQL ソースを開き直し、必要ならスキーマを更新して、上の6テーブルの列を展開します。実際のソース探索・読戻しで得られたノードと列を確認します。表示されない列の ID を推測したり、新しい項目を作ったりしません。
2. _WorkshopGenerationId が選択されている場合は、その6つの列のチェックだけを外します。17親オブジェクトと、この節に列挙した143業務列の選択を残します。親を一括選択し直してシステム列を再選択しないようにします。
3. 保存後に実際のソースと選択状態を読み戻し、17オブジェクト・143業務列と、表示された6つのシステム列が未選択であることを確認します。149列のまま公開へ進まず、143の条件や選択契約を書き換えて検査を通しません。
4. 選択を修正した場合は、17.16で新しい記録先を使って読み取り専用 prepare を実行し直します。変更前の記録と使用済みの apply-intent / publish-intent を保持し、同じ書き込みを再送しません。新しい読戻しと143列の確認が成功してから、その構成に対応する後続の操作へ進みます。

この確認はソースの構成を一致させるためのものです。設定の一致や公開の成功を、回答精度や実際のソース問い合わせの成功と扱いません。17.2と19章で実回答を別に評価します。

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

The 143-column contract contains business columns only, excluding system generation metadata. When the service expands selected parent tables, it may select _WorkshopGenerationId leaves absent from the initial source discovery. Selecting 17 parent objects alone does not establish 143 selected columns; read the current leaf selections back.

**Six generation-metadata leaves outside the 143 business columns**

| Parent table (keep selected) | System column to uncheck if displayed |
| --- | --- |
| dbo.ot_donor | _WorkshopGenerationId |
| dbo.ot_gift | _WorkshopGenerationId |
| dbo.ot_gift_category | _WorkshopGenerationId |
| dbo.ot_mun_category_metric | _WorkshopGenerationId |
| dbo.ot_pref_donation_flow | _WorkshopGenerationId |
| dbo.ot_prefecture | _WorkshopGenerationId |

1. Reopen the SQL source, refresh its schema if needed, and expand columns under the six tables above. Inspect nodes and columns returned by actual discovery/readback. Never guess an ID or create a synthetic item for an undisplayed column.
2. If _WorkshopGenerationId is selected, uncheck only those six leaves. Keep the 17 parent objects and all 143 business columns listed in this section selected. Do not select all parent contents again and reselect the metadata leaves.
3. After saving, read the actual source and selections back. Confirm 17 objects and 143 business columns, with the six displayed metadata leaves unselected. Do not proceed to publication with 149 columns or change the 143-column contract to make validation pass.
4. After a selection correction, run read-only prepare again in a new record directory as described in 17.16. Retain prior evidence and spent apply-intent/publish-intent records; do not replay the same write. Continue with operations for the newly prepared configuration only after fresh readback and the 143-column check succeed.

This check aligns source configuration. Configuration equality or publication success does not establish answer accuracy or actual source-query success. Evaluate real answers separately in 17.2 and Chapter 19.

The selection contract also contains table and column descriptions. Where an editing field is available, use the description at the same path in selection-contract.json. Do not invent JSON fields for properties without an editor. Copying instructions alone does not verify these descriptions or actual selections; distinguish UI checks from definition checks in the configuration record in 17.15.

</details>
