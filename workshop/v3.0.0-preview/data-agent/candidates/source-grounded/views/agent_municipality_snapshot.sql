CREATE VIEW dbo.agent_municipality_snapshot AS
SELECT
    m.MunicipalityId,
    m.MunicipalityName,
    m.PrefectureId,
    p.PrefectureName,
    m.MunicipalityStaticCount AS DonationCount,
    m.MunicipalityStaticTotalYen AS AmountYen,
    m.MunicipalityAmountRank AS AmountRank,
    COUNT_BIG(*) OVER (PARTITION BY m.PrefectureId) AS RegisteredMunicipalitiesInPrefecture
FROM dbo.ot_municipality AS m
JOIN dbo.ot_prefecture AS p ON p.PrefectureId = m.PrefectureId
