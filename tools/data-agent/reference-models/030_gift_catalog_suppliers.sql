CREATE VIEW agent_ref.GiftCatalogSuppliers
AS
SELECT
    bridge.GiftId AS GiftCatalogGiftId,
    gift.GiftName,
    gift.GiftDisplayName,
    gift.GiftSearchTerms,
    gift.GiftNotes,

    gift.CategoryId AS GiftCategoryId,
    category.CategoryName AS GiftCategoryName,
    category.CategoryNameEn AS GiftCategoryNameEn,
    category.CategorySearchTerms AS GiftCategorySearchTerms,

    CAST(gift.MunicipalityId AS varchar(6)) AS GiftCatalogMunicipalityId,
    catalog_mun.MunicipalityName AS GiftCatalogMunicipalityName,
    catalog_mun.MunicipalityDisplayName AS GiftCatalogMunicipalityDisplayName,
    catalog_mun.PrefectureId AS GiftCatalogPrefectureId,
    catalog_pref.PrefectureName AS GiftCatalogPrefectureName,
    catalog_pref.PrefectureNameEn AS GiftCatalogPrefectureNameEn,

    bridge.SupplierId AS RegisteredSupplierId,
    supplier.SupplierName AS RegisteredSupplierName,
    supplier.SupplierDisplayName AS RegisteredSupplierDisplayName,
    supplier.SupplierType AS RegisteredSupplierType,
    supplier.SupplierTypeEn AS RegisteredSupplierTypeEn,
    supplier.PrefectureId AS SupplierLocationPrefectureId,
    supplier_pref.PrefectureName AS SupplierLocationPrefectureName,
    supplier_pref.PrefectureNameEn AS SupplierLocationPrefectureNameEn,

    CAST('RegisteredCatalogSupplier' AS varchar(64)) AS RelationshipMeaning,
    CAST('OneGiftSupplierRegistration' AS varchar(64)) AS RowGrain,
    CAST('NoManufactureOrShipmentClaim' AS varchar(64)) AS ProvenanceLimit,
    CAST('FurusatoStatic2025' AS varchar(64)) AS DatasetName,
    CAST('LakehouseSqlEndpoint' AS varchar(64)) AS SourceSystem,
    CAST('Static2025UtcSnapshot' AS varchar(64)) AS DatasetScope
FROM dbo.ot_supplier_gift AS bridge
LEFT JOIN dbo.ot_gift AS gift
    ON gift.GiftId = bridge.GiftId
LEFT JOIN dbo.ot_gift_category AS category
    ON category.CategoryId = gift.CategoryId
LEFT JOIN dbo.ot_municipality AS catalog_mun
    ON catalog_mun.MunicipalityId = gift.MunicipalityId
LEFT JOIN dbo.ot_prefecture AS catalog_pref
    ON catalog_pref.PrefectureId = catalog_mun.PrefectureId
LEFT JOIN dbo.ot_supplier AS supplier
    ON supplier.SupplierId = bridge.SupplierId
LEFT JOIN dbo.ot_prefecture AS supplier_pref
    ON supplier_pref.PrefectureId = supplier.PrefectureId;
GO
