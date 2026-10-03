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
