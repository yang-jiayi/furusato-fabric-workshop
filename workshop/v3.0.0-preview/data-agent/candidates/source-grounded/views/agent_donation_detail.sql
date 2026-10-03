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
