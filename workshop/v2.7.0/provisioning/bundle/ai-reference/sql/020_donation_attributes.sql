CREATE VIEW agent_ref.DonationAttributes
AS
SELECT
    d.DonationId,
    d.DonationDisplayName,
    CAST(d.DonationAmountYen AS bigint) AS DonationAmountYen,
    d.DonatedAtUtc,
    d.DonatedAtJstText,
    d.DonationDateJst,
    d.DonationYearMonthJst,
    d.DonationYearMonthJaShort,
    d.DonationPaymentMethod,
    d.DonationPaymentMethodEn,
    d.DonationDataLayer,

    d.DonorId AS DonationDonorId,
    donor.DonorName,
    donor.DonorDisplayName,
    donor.DonorAge,
    donor.DonorOccupation,
    donor.DonorOccupationEn,

    donor.PrefectureId AS DonorResidencePrefectureId,
    residence_pref.PrefectureName AS DonorResidencePrefectureName,
    residence_pref.PrefectureNameEn AS DonorResidencePrefectureNameEn,

    CAST(d.MunicipalityId AS varchar(6)) AS DonationRecipientMunicipalityId,
    recipient_mun.MunicipalityName AS RecipientMunicipalityName,
    recipient_mun.MunicipalityDisplayName AS RecipientMunicipalityDisplayName,

    recipient_mun.PrefectureId AS RecipientPrefectureId,
    recipient_pref.PrefectureName AS RecipientPrefectureName,
    recipient_pref.PrefectureNameEn AS RecipientPrefectureNameEn,

    d.GiftId AS DonationSelectedGiftId,
    gift.GiftName,
    gift.GiftDisplayName,
    gift.GiftSearchTerms,
    gift.GiftNotes,
    CAST(gift.MunicipalityId AS varchar(6)) AS GiftCatalogMunicipalityId,

    gift.CategoryId AS GiftCategoryId,
    category.CategoryName AS GiftCategoryName,
    category.CategoryNameEn AS GiftCategoryNameEn,
    category.CategorySearchTerms AS GiftCategorySearchTerms,

    CAST('FurusatoStatic2025' AS varchar(64)) AS DatasetName,
    CAST('LakehouseSqlEndpoint' AS varchar(64)) AS SourceSystem,
    CAST('Static2025UtcSnapshot' AS varchar(64)) AS DatasetScope,
    CAST('JPY' AS varchar(8)) AS DonationAmountUnit
FROM dbo.ot_donation AS d
LEFT JOIN dbo.ot_donor AS donor
    ON donor.DonorId = d.DonorId
LEFT JOIN dbo.ot_prefecture AS residence_pref
    ON residence_pref.PrefectureId = donor.PrefectureId
LEFT JOIN dbo.ot_municipality AS recipient_mun
    ON recipient_mun.MunicipalityId = d.MunicipalityId
LEFT JOIN dbo.ot_prefecture AS recipient_pref
    ON recipient_pref.PrefectureId = recipient_mun.PrefectureId
LEFT JOIN dbo.ot_gift AS gift
    ON gift.GiftId = d.GiftId
LEFT JOIN dbo.ot_gift_category AS category
    ON category.CategoryId = gift.CategoryId;
GO
