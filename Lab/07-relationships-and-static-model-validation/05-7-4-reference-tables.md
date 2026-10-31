# 7.4 参照表

[Lab 目次](../README.md) · [この章の目次](README.md)

**作成する15個の Relationship**

| Relationship | Origin → Target | キー列を持つテーブル | このテーブルで Origin を表す列 / Target を表す列 |
| --- | --- | --- | --- |
| MunicipalityInPrefecture | Municipality → Prefecture | ot_municipality | MunicipalityId / PrefectureId |
| DonorLivesInPrefecture | Donor → Prefecture | ot_donor | DonorId / PrefectureId |
| SupplierInPrefecture | Supplier → Prefecture | ot_supplier | SupplierId / PrefectureId |
| GiftInCategory | Gift → GiftCategory | ot_gift | GiftId / CategoryId |
| MunicipalityCatalogsGift | Municipality → Gift | ot_gift | MunicipalityId / GiftId |
| SupplierProvidesGift | Supplier → Gift | ot_supplier_gift | SupplierId / GiftId |
| DonorMadeDonation | Donor → Donation | ot_donation | DonorId / DonationId |
| DonationToMunicipality | Donation → Municipality | ot_donation | DonationId / MunicipalityId |
| DonationSelectedGift | Donation → Gift | ot_donation | DonationId / GiftId |
| MunHasCategoryMetric | Municipality → MunicipalityCategoryMetric | ot_mun_category_metric | MunicipalityId / MunCategoryMetricId |
| MunMetricForCategory | MunicipalityCategoryMetric → GiftCategory | ot_mun_category_metric | MunCategoryMetricId / CategoryId |
| PrefHasCategoryMetric | Prefecture → PrefectureCategoryMetric | ot_pref_category_metric | PrefectureId / PrefCategoryMetricId |
| PrefMetricForCategory | PrefectureCategoryMetric → GiftCategory | ot_pref_category_metric | PrefCategoryMetricId / CategoryId |
| ResidencePrefHasFlow | Prefecture → PrefectureDonationFlow | ot_pref_donation_flow | ResidencePrefectureId / PrefDonationFlowId |
| FlowToRecipientPref | PrefectureDonationFlow → Prefecture | ot_pref_donation_flow | PrefDonationFlowId / RecipientPrefectureId |

<details>
<summary>English</summary>

## 7.4 Reference tables

**The fifteen relationships to create**

| Relationship | Origin → Target | Table with the key columns | Column for the origin / column for the target in that table |
| --- | --- | --- | --- |
| MunicipalityInPrefecture | Municipality → Prefecture | ot_municipality | MunicipalityId / PrefectureId |
| DonorLivesInPrefecture | Donor → Prefecture | ot_donor | DonorId / PrefectureId |
| SupplierInPrefecture | Supplier → Prefecture | ot_supplier | SupplierId / PrefectureId |
| GiftInCategory | Gift → GiftCategory | ot_gift | GiftId / CategoryId |
| MunicipalityCatalogsGift | Municipality → Gift | ot_gift | MunicipalityId / GiftId |
| SupplierProvidesGift | Supplier → Gift | ot_supplier_gift | SupplierId / GiftId |
| DonorMadeDonation | Donor → Donation | ot_donation | DonorId / DonationId |
| DonationToMunicipality | Donation → Municipality | ot_donation | DonationId / MunicipalityId |
| DonationSelectedGift | Donation → Gift | ot_donation | DonationId / GiftId |
| MunHasCategoryMetric | Municipality → MunicipalityCategoryMetric | ot_mun_category_metric | MunicipalityId / MunCategoryMetricId |
| MunMetricForCategory | MunicipalityCategoryMetric → GiftCategory | ot_mun_category_metric | MunCategoryMetricId / CategoryId |
| PrefHasCategoryMetric | Prefecture → PrefectureCategoryMetric | ot_pref_category_metric | PrefectureId / PrefCategoryMetricId |
| PrefMetricForCategory | PrefectureCategoryMetric → GiftCategory | ot_pref_category_metric | PrefCategoryMetricId / CategoryId |
| ResidencePrefHasFlow | Prefecture → PrefectureDonationFlow | ot_pref_donation_flow | ResidencePrefectureId / PrefDonationFlowId |
| FlowToRecipientPref | PrefectureDonationFlow → Prefecture | ot_pref_donation_flow | PrefDonationFlowId / RecipientPrefectureId |

</details>
