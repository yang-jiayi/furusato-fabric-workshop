CREATE FUNCTION agent_ref.DonationTraceById
(
    @RequestedDonationId bigint
)
RETURNS TABLE
AS
RETURN
(
    SELECT
        CAST(@RequestedDonationId AS bigint) AS RequestedDonationId,
        CAST('exact-ID lookup' AS varchar(32)) AS RetrievalMode,
        donation.DonationId,
        donation.DonationDisplayName,
        donation.DonationAmountYen,
        donation.DonationDonorId AS DonorId,
        donation.DonorName,
        donation.DonorDisplayName,
        donation.DonorResidencePrefectureId,
        donation.DonorResidencePrefectureName,
        donation.DonationRecipientMunicipalityId AS MunicipalityId,
        donation.RecipientMunicipalityName AS MunicipalityName,
        donation.RecipientMunicipalityDisplayName AS MunicipalityDisplayName,
        donation.RecipientPrefectureId,
        donation.RecipientPrefectureName,
        donation.DonationSelectedGiftId AS GiftId,
        donation.GiftName,
        donation.GiftDisplayName,
        donation.GiftCategoryId AS CategoryId,
        donation.GiftCategoryName AS CategoryName,
        supplier.RegisteredSupplierId AS SupplierId,
        supplier.RegisteredSupplierName AS SupplierName,
        supplier.RegisteredSupplierDisplayName AS SupplierDisplayName,
        supplier.RegisteredSupplierType AS SupplierType,
        supplier.RegisteredSupplierTypeEn AS SupplierTypeEn,
        donation.DatasetName,
        donation.SourceSystem,
        donation.DatasetScope,
        donation.DonationAmountUnit,
        CAST(
            'DonationId x SupplierId registration; DonationAmountYen is non-additive'
            AS varchar(96)
        ) AS RowGrain
    FROM agent_ref.DonationAttributes AS donation
    LEFT JOIN agent_ref.GiftCatalogSuppliers AS supplier
        ON supplier.GiftCatalogGiftId = donation.DonationSelectedGiftId
    WHERE @RequestedDonationId IS NOT NULL
      AND donation.DonationId = @RequestedDonationId
);
GO
