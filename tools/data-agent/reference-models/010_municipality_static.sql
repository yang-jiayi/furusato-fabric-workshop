CREATE VIEW agent_ref.MunicipalityStatic
AS
WITH ranked AS
(
    SELECT
        CAST(m.MunicipalityId AS varchar(6)) AS MunicipalityId,
        m.MunicipalityName,
        m.MunicipalityDisplayName,
        m.PrefectureId,
        p.PrefectureName,
        p.PrefectureNameEn,
        CAST(m.MunicipalityStaticCount AS bigint) AS MunicipalityStaticCount,
        CAST(m.MunicipalityStaticTotalYen AS bigint) AS MunicipalityStaticTotalYen,
        CAST(m.MunicipalityAmountRank AS bigint) AS MunicipalityStoredNationwideAmountRank,
        CAST(m.MunicipalityPrefAmountRank AS bigint) AS MunicipalityStoredPrefectureAmountRank,
        CAST(
            ROW_NUMBER() OVER
            (
                ORDER BY
                    CAST(m.MunicipalityStaticCount AS bigint) DESC,
                    CAST(m.MunicipalityId AS varchar(6)) ASC
            )
            AS bigint
        ) AS MunicipalityDerivedNationwideCountRank
    FROM dbo.ot_municipality AS m
    LEFT JOIN dbo.ot_prefecture AS p
        ON p.PrefectureId = m.PrefectureId
)
SELECT
    MunicipalityId,
    MunicipalityName,
    MunicipalityDisplayName,
    PrefectureId,
    PrefectureName,
    PrefectureNameEn,
    MunicipalityStaticCount,
    MunicipalityStaticTotalYen,
    MunicipalityStoredNationwideAmountRank,
    MunicipalityStoredPrefectureAmountRank,
    MunicipalityDerivedNationwideCountRank,
    CAST('DonationCount' AS varchar(32)) AS DefaultPopularityMetric,
    MunicipalityStaticCount AS DefaultPopularityValue,
    CAST('FurusatoStatic2025' AS varchar(64)) AS DatasetName,
    CAST('LakehouseSqlEndpoint' AS varchar(64)) AS SourceSystem,
    CAST('Static2025UtcSnapshot' AS varchar(64)) AS DatasetScope,
    CAST('DonationRows' AS varchar(32)) AS CountUnit,
    CAST('JPY' AS varchar(8)) AS AmountUnit,
    CAST('AllMunicipalitiesIncludingZeroDonation' AS varchar(64)) AS NationwideRankScope,
    CAST('MunicipalitiesWithinPrefectureIncludingZeroDonation' AS varchar(64)) AS PrefectureRankScope
FROM ranked;
GO
