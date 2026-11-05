# 6.4 参照表

[Lab 目次](../README.md) · [この章の目次](README.md)

**作成する10個の Entity type**

| Entity type | キー | キーの型 | ソーステーブル | 静的 Property の数 |
| --- | --- | --- | --- | --- |
| `Prefecture` | `PrefectureId` | `Integer` | `ot_prefecture` | 9 |
| `Municipality` | `MunicipalityId` | `String` | `ot_municipality` | 7 |
| `Donor` | `DonorId` | `Integer` | `ot_donor` | 11 |
| `GiftCategory` | `CategoryId` | `Integer` | `ot_gift_category` | 7 |
| `Gift` | `GiftId` | `Integer` | `ot_gift` | 8 |
| `Supplier` | `SupplierId` | `Integer` | `ot_supplier` | 6 |
| `Donation` | `DonationId` | `Integer` | `ot_donation` | 11 |
| `MunicipalityCategoryMetric` | `MunCategoryMetricId` | `String` | `ot_mun_category_metric` | 4 |
| `PrefectureCategoryMetric` | `PrefCategoryMetricId` | `String` | `ot_pref_category_metric` | 4 |
| `PrefectureDonationFlow` | `PrefDonationFlowId` | `String` | `ot_pref_donation_flow` | 5 |

**配布する ontology-full-definition-template.json から生成した静的 Property の期待マッピング。実際の Bind data 画面は別途確認します。**

| Entity type | ソーステーブル | Property | ソース列 | Property の型 |
| --- | --- | --- | --- | --- |
| `Prefecture` | `ot_prefecture` | `PrefectureId` | `PrefectureId` | `Integer` |
| `Prefecture` | `ot_prefecture` | `PrefectureName` | `PrefectureName` | `String` |
| `Prefecture` | `ot_prefecture` | `PrefectureNameEn` | `PrefectureNameEn` | `String` |
| `Prefecture` | `ot_prefecture` | `PrefReceivedStaticCount` | `PrefReceivedStaticCount` | `Integer` |
| `Prefecture` | `ot_prefecture` | `PrefReceivedTotalYen` | `PrefReceivedTotalYen` | `Integer` |
| `Prefecture` | `ot_prefecture` | `PrefReceivedAmountRank` | `PrefReceivedAmountRank` | `Integer` |
| `Prefecture` | `ot_prefecture` | `PrefResidentStaticCount` | `PrefResidentStaticCount` | `Integer` |
| `Prefecture` | `ot_prefecture` | `PrefResidentTotalYen` | `PrefResidentTotalYen` | `Integer` |
| `Prefecture` | `ot_prefecture` | `PrefResidentAmountRank` | `PrefResidentAmountRank` | `Integer` |
| `Municipality` | `ot_municipality` | `MunicipalityId` | `MunicipalityId` | `String` |
| `Municipality` | `ot_municipality` | `MunicipalityName` | `MunicipalityName` | `String` |
| `Municipality` | `ot_municipality` | `MunicipalityDisplayName` | `MunicipalityDisplayName` | `String` |
| `Municipality` | `ot_municipality` | `MunicipalityStaticCount` | `MunicipalityStaticCount` | `Integer` |
| `Municipality` | `ot_municipality` | `MunicipalityStaticTotalYen` | `MunicipalityStaticTotalYen` | `Integer` |
| `Municipality` | `ot_municipality` | `MunicipalityAmountRank` | `MunicipalityAmountRank` | `Integer` |
| `Municipality` | `ot_municipality` | `MunicipalityPrefAmountRank` | `MunicipalityPrefAmountRank` | `Integer` |
| `Donor` | `ot_donor` | `DonorId` | `DonorId` | `Integer` |
| `Donor` | `ot_donor` | `DonorName` | `DonorName` | `String` |
| `Donor` | `ot_donor` | `DonorDisplayName` | `DonorDisplayName` | `String` |
| `Donor` | `ot_donor` | `DonorAge` | `DonorAge` | `Integer` |
| `Donor` | `ot_donor` | `DonorOccupation` | `DonorOccupation` | `String` |
| `Donor` | `ot_donor` | `DonorOccupationEn` | `DonorOccupationEn` | `String` |
| `Donor` | `ot_donor` | `DonorStaticCount` | `DonorStaticCount` | `Integer` |
| `Donor` | `ot_donor` | `DonorStaticTotalYen` | `DonorStaticTotalYen` | `Integer` |
| `Donor` | `ot_donor` | `DonorStaticMaxYen` | `DonorStaticMaxYen` | `Integer` |
| `Donor` | `ot_donor` | `DonorOverallAmountRank` | `DonorOverallAmountRank` | `Integer` |
| `Donor` | `ot_donor` | `DonorResidenceAmountRank` | `DonorResidenceAmountRank` | `Integer` |
| `GiftCategory` | `ot_gift_category` | `CategoryId` | `CategoryId` | `Integer` |
| `GiftCategory` | `ot_gift_category` | `CategoryName` | `CategoryName` | `String` |
| `GiftCategory` | `ot_gift_category` | `CategoryNameEn` | `CategoryNameEn` | `String` |
| `GiftCategory` | `ot_gift_category` | `CategorySearchTerms` | `CategorySearchTerms` | `String` |
| `GiftCategory` | `ot_gift_category` | `CategoryStaticCount` | `CategoryStaticCount` | `Integer` |
| `GiftCategory` | `ot_gift_category` | `CategoryStaticTotalYen` | `CategoryStaticTotalYen` | `Integer` |
| `GiftCategory` | `ot_gift_category` | `CategoryAmountRank` | `CategoryAmountRank` | `Integer` |
| `Gift` | `ot_gift` | `GiftId` | `GiftId` | `Integer` |
| `Gift` | `ot_gift` | `GiftName` | `GiftName` | `String` |
| `Gift` | `ot_gift` | `GiftDisplayName` | `GiftDisplayName` | `String` |
| `Gift` | `ot_gift` | `GiftSearchTerms` | `GiftSearchTerms` | `String` |
| `Gift` | `ot_gift` | `GiftNotes` | `GiftNotes` | `String` |
| `Gift` | `ot_gift` | `GiftStaticCount` | `GiftStaticCount` | `Integer` |
| `Gift` | `ot_gift` | `GiftStaticTotalYen` | `GiftStaticTotalYen` | `Integer` |
| `Gift` | `ot_gift` | `GiftAmountRank` | `GiftAmountRank` | `Integer` |
| `Supplier` | `ot_supplier` | `SupplierId` | `SupplierId` | `Integer` |
| `Supplier` | `ot_supplier` | `SupplierName` | `SupplierName` | `String` |
| `Supplier` | `ot_supplier` | `SupplierDisplayName` | `SupplierDisplayName` | `String` |
| `Supplier` | `ot_supplier` | `SupplierType` | `SupplierType` | `String` |
| `Supplier` | `ot_supplier` | `SupplierTypeEn` | `SupplierTypeEn` | `String` |
| `Supplier` | `ot_supplier` | `SupplierProvidedGiftCount` | `SupplierProvidedGiftCount` | `Integer` |
| `Donation` | `ot_donation` | `DonationId` | `DonationId` | `Integer` |
| `Donation` | `ot_donation` | `DonationDisplayName` | `DonationDisplayName` | `String` |
| `Donation` | `ot_donation` | `DonationAmountYen` | `DonationAmountYen` | `Integer` |
| `Donation` | `ot_donation` | `DonatedAtUtc` | `DonatedAtUtc` | `DateTime` |
| `Donation` | `ot_donation` | `DonatedAtJstText` | `DonatedAtJstText` | `String` |
| `Donation` | `ot_donation` | `DonationDateJst` | `DonationDateJst` | `String` |
| `Donation` | `ot_donation` | `DonationYearMonthJst` | `DonationYearMonthJst` | `String` |
| `Donation` | `ot_donation` | `DonationYearMonthJaShort` | `DonationYearMonthJaShort` | `String` |
| `Donation` | `ot_donation` | `DonationPaymentMethod` | `DonationPaymentMethod` | `String` |
| `Donation` | `ot_donation` | `DonationPaymentMethodEn` | `DonationPaymentMethodEn` | `String` |
| `Donation` | `ot_donation` | `DonationDataLayer` | `DonationDataLayer` | `String` |
| `MunicipalityCategoryMetric` | `ot_mun_category_metric` | `MunCategoryMetricId` | `MunCategoryMetricId` | `String` |
| `MunicipalityCategoryMetric` | `ot_mun_category_metric` | `MunCategoryStaticCount` | `MunCategoryStaticCount` | `Integer` |
| `MunicipalityCategoryMetric` | `ot_mun_category_metric` | `MunCategoryTotalYen` | `MunCategoryTotalYen` | `Integer` |
| `MunicipalityCategoryMetric` | `ot_mun_category_metric` | `MunCategoryAmountRank` | `MunCategoryAmountRank` | `Integer` |
| `PrefectureCategoryMetric` | `ot_pref_category_metric` | `PrefCategoryMetricId` | `PrefCategoryMetricId` | `String` |
| `PrefectureCategoryMetric` | `ot_pref_category_metric` | `PrefCategoryStaticCount` | `PrefCategoryStaticCount` | `Integer` |
| `PrefectureCategoryMetric` | `ot_pref_category_metric` | `PrefCategoryTotalYen` | `PrefCategoryTotalYen` | `Integer` |
| `PrefectureCategoryMetric` | `ot_pref_category_metric` | `PrefCategoryAmountRank` | `PrefCategoryAmountRank` | `Integer` |
| `PrefectureDonationFlow` | `ot_pref_donation_flow` | `PrefDonationFlowId` | `PrefDonationFlowId` | `String` |
| `PrefectureDonationFlow` | `ot_pref_donation_flow` | `PrefFlowStaticCount` | `PrefFlowStaticCount` | `Integer` |
| `PrefectureDonationFlow` | `ot_pref_donation_flow` | `PrefFlowTotalYen` | `PrefFlowTotalYen` | `Integer` |
| `PrefectureDonationFlow` | `ot_pref_donation_flow` | `PrefFlowOriginRank` | `PrefFlowOriginRank` | `Integer` |
| `PrefectureDonationFlow` | `ot_pref_donation_flow` | `PrefFlowDestinationRank` | `PrefFlowDestinationRank` | `Integer` |

<details>
<summary>English</summary>

## 6.4 Reference tables

**The ten entity types to create**

| Entity type | Key | Key type | Source table | Static properties |
| --- | --- | --- | --- | --- |
| `Prefecture` | `PrefectureId` | `Integer` | `ot_prefecture` | 9 |
| `Municipality` | `MunicipalityId` | `String` | `ot_municipality` | 7 |
| `Donor` | `DonorId` | `Integer` | `ot_donor` | 11 |
| `GiftCategory` | `CategoryId` | `Integer` | `ot_gift_category` | 7 |
| `Gift` | `GiftId` | `Integer` | `ot_gift` | 8 |
| `Supplier` | `SupplierId` | `Integer` | `ot_supplier` | 6 |
| `Donation` | `DonationId` | `Integer` | `ot_donation` | 11 |
| `MunicipalityCategoryMetric` | `MunCategoryMetricId` | `String` | `ot_mun_category_metric` | 4 |
| `PrefectureCategoryMetric` | `PrefCategoryMetricId` | `String` | `ot_pref_category_metric` | 4 |
| `PrefectureDonationFlow` | `PrefDonationFlowId` | `String` | `ot_pref_donation_flow` | 5 |

**Expected static-property mappings generated from the distributed ontology-full-definition-template.json. Verify the actual Bind data screen separately.**

| Entity type | Source table | Property | Source column | Property type |
| --- | --- | --- | --- | --- |
| `Prefecture` | `ot_prefecture` | `PrefectureId` | `PrefectureId` | `Integer` |
| `Prefecture` | `ot_prefecture` | `PrefectureName` | `PrefectureName` | `String` |
| `Prefecture` | `ot_prefecture` | `PrefectureNameEn` | `PrefectureNameEn` | `String` |
| `Prefecture` | `ot_prefecture` | `PrefReceivedStaticCount` | `PrefReceivedStaticCount` | `Integer` |
| `Prefecture` | `ot_prefecture` | `PrefReceivedTotalYen` | `PrefReceivedTotalYen` | `Integer` |
| `Prefecture` | `ot_prefecture` | `PrefReceivedAmountRank` | `PrefReceivedAmountRank` | `Integer` |
| `Prefecture` | `ot_prefecture` | `PrefResidentStaticCount` | `PrefResidentStaticCount` | `Integer` |
| `Prefecture` | `ot_prefecture` | `PrefResidentTotalYen` | `PrefResidentTotalYen` | `Integer` |
| `Prefecture` | `ot_prefecture` | `PrefResidentAmountRank` | `PrefResidentAmountRank` | `Integer` |
| `Municipality` | `ot_municipality` | `MunicipalityId` | `MunicipalityId` | `String` |
| `Municipality` | `ot_municipality` | `MunicipalityName` | `MunicipalityName` | `String` |
| `Municipality` | `ot_municipality` | `MunicipalityDisplayName` | `MunicipalityDisplayName` | `String` |
| `Municipality` | `ot_municipality` | `MunicipalityStaticCount` | `MunicipalityStaticCount` | `Integer` |
| `Municipality` | `ot_municipality` | `MunicipalityStaticTotalYen` | `MunicipalityStaticTotalYen` | `Integer` |
| `Municipality` | `ot_municipality` | `MunicipalityAmountRank` | `MunicipalityAmountRank` | `Integer` |
| `Municipality` | `ot_municipality` | `MunicipalityPrefAmountRank` | `MunicipalityPrefAmountRank` | `Integer` |
| `Donor` | `ot_donor` | `DonorId` | `DonorId` | `Integer` |
| `Donor` | `ot_donor` | `DonorName` | `DonorName` | `String` |
| `Donor` | `ot_donor` | `DonorDisplayName` | `DonorDisplayName` | `String` |
| `Donor` | `ot_donor` | `DonorAge` | `DonorAge` | `Integer` |
| `Donor` | `ot_donor` | `DonorOccupation` | `DonorOccupation` | `String` |
| `Donor` | `ot_donor` | `DonorOccupationEn` | `DonorOccupationEn` | `String` |
| `Donor` | `ot_donor` | `DonorStaticCount` | `DonorStaticCount` | `Integer` |
| `Donor` | `ot_donor` | `DonorStaticTotalYen` | `DonorStaticTotalYen` | `Integer` |
| `Donor` | `ot_donor` | `DonorStaticMaxYen` | `DonorStaticMaxYen` | `Integer` |
| `Donor` | `ot_donor` | `DonorOverallAmountRank` | `DonorOverallAmountRank` | `Integer` |
| `Donor` | `ot_donor` | `DonorResidenceAmountRank` | `DonorResidenceAmountRank` | `Integer` |
| `GiftCategory` | `ot_gift_category` | `CategoryId` | `CategoryId` | `Integer` |
| `GiftCategory` | `ot_gift_category` | `CategoryName` | `CategoryName` | `String` |
| `GiftCategory` | `ot_gift_category` | `CategoryNameEn` | `CategoryNameEn` | `String` |
| `GiftCategory` | `ot_gift_category` | `CategorySearchTerms` | `CategorySearchTerms` | `String` |
| `GiftCategory` | `ot_gift_category` | `CategoryStaticCount` | `CategoryStaticCount` | `Integer` |
| `GiftCategory` | `ot_gift_category` | `CategoryStaticTotalYen` | `CategoryStaticTotalYen` | `Integer` |
| `GiftCategory` | `ot_gift_category` | `CategoryAmountRank` | `CategoryAmountRank` | `Integer` |
| `Gift` | `ot_gift` | `GiftId` | `GiftId` | `Integer` |
| `Gift` | `ot_gift` | `GiftName` | `GiftName` | `String` |
| `Gift` | `ot_gift` | `GiftDisplayName` | `GiftDisplayName` | `String` |
| `Gift` | `ot_gift` | `GiftSearchTerms` | `GiftSearchTerms` | `String` |
| `Gift` | `ot_gift` | `GiftNotes` | `GiftNotes` | `String` |
| `Gift` | `ot_gift` | `GiftStaticCount` | `GiftStaticCount` | `Integer` |
| `Gift` | `ot_gift` | `GiftStaticTotalYen` | `GiftStaticTotalYen` | `Integer` |
| `Gift` | `ot_gift` | `GiftAmountRank` | `GiftAmountRank` | `Integer` |
| `Supplier` | `ot_supplier` | `SupplierId` | `SupplierId` | `Integer` |
| `Supplier` | `ot_supplier` | `SupplierName` | `SupplierName` | `String` |
| `Supplier` | `ot_supplier` | `SupplierDisplayName` | `SupplierDisplayName` | `String` |
| `Supplier` | `ot_supplier` | `SupplierType` | `SupplierType` | `String` |
| `Supplier` | `ot_supplier` | `SupplierTypeEn` | `SupplierTypeEn` | `String` |
| `Supplier` | `ot_supplier` | `SupplierProvidedGiftCount` | `SupplierProvidedGiftCount` | `Integer` |
| `Donation` | `ot_donation` | `DonationId` | `DonationId` | `Integer` |
| `Donation` | `ot_donation` | `DonationDisplayName` | `DonationDisplayName` | `String` |
| `Donation` | `ot_donation` | `DonationAmountYen` | `DonationAmountYen` | `Integer` |
| `Donation` | `ot_donation` | `DonatedAtUtc` | `DonatedAtUtc` | `DateTime` |
| `Donation` | `ot_donation` | `DonatedAtJstText` | `DonatedAtJstText` | `String` |
| `Donation` | `ot_donation` | `DonationDateJst` | `DonationDateJst` | `String` |
| `Donation` | `ot_donation` | `DonationYearMonthJst` | `DonationYearMonthJst` | `String` |
| `Donation` | `ot_donation` | `DonationYearMonthJaShort` | `DonationYearMonthJaShort` | `String` |
| `Donation` | `ot_donation` | `DonationPaymentMethod` | `DonationPaymentMethod` | `String` |
| `Donation` | `ot_donation` | `DonationPaymentMethodEn` | `DonationPaymentMethodEn` | `String` |
| `Donation` | `ot_donation` | `DonationDataLayer` | `DonationDataLayer` | `String` |
| `MunicipalityCategoryMetric` | `ot_mun_category_metric` | `MunCategoryMetricId` | `MunCategoryMetricId` | `String` |
| `MunicipalityCategoryMetric` | `ot_mun_category_metric` | `MunCategoryStaticCount` | `MunCategoryStaticCount` | `Integer` |
| `MunicipalityCategoryMetric` | `ot_mun_category_metric` | `MunCategoryTotalYen` | `MunCategoryTotalYen` | `Integer` |
| `MunicipalityCategoryMetric` | `ot_mun_category_metric` | `MunCategoryAmountRank` | `MunCategoryAmountRank` | `Integer` |
| `PrefectureCategoryMetric` | `ot_pref_category_metric` | `PrefCategoryMetricId` | `PrefCategoryMetricId` | `String` |
| `PrefectureCategoryMetric` | `ot_pref_category_metric` | `PrefCategoryStaticCount` | `PrefCategoryStaticCount` | `Integer` |
| `PrefectureCategoryMetric` | `ot_pref_category_metric` | `PrefCategoryTotalYen` | `PrefCategoryTotalYen` | `Integer` |
| `PrefectureCategoryMetric` | `ot_pref_category_metric` | `PrefCategoryAmountRank` | `PrefCategoryAmountRank` | `Integer` |
| `PrefectureDonationFlow` | `ot_pref_donation_flow` | `PrefDonationFlowId` | `PrefDonationFlowId` | `String` |
| `PrefectureDonationFlow` | `ot_pref_donation_flow` | `PrefFlowStaticCount` | `PrefFlowStaticCount` | `Integer` |
| `PrefectureDonationFlow` | `ot_pref_donation_flow` | `PrefFlowTotalYen` | `PrefFlowTotalYen` | `Integer` |
| `PrefectureDonationFlow` | `ot_pref_donation_flow` | `PrefFlowOriginRank` | `PrefFlowOriginRank` | `Integer` |
| `PrefectureDonationFlow` | `ot_pref_donation_flow` | `PrefFlowDestinationRank` | `PrefFlowDestinationRank` | `Integer` |

</details>
