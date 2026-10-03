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
