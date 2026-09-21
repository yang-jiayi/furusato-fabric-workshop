CREATE FUNCTION agent_ref.MunicipalityById
(
    @RequestedMunicipalityId varchar(64)
)
RETURNS TABLE
AS
RETURN
(
    SELECT
        CAST(@RequestedMunicipalityId AS varchar(64)) AS RequestedMunicipalityId,
        CAST('exact-ID lookup' AS varchar(32)) AS RetrievalMode,
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
        DefaultPopularityMetric,
        DefaultPopularityValue,
        DatasetName,
        SourceSystem,
        DatasetScope,
        CountUnit,
        AmountUnit,
        NationwideRankScope,
        PrefectureRankScope
    FROM agent_ref.MunicipalityStatic
    WHERE DATALENGTH(@RequestedMunicipalityId) = 6
      AND @RequestedMunicipalityId COLLATE Latin1_General_100_BIN2_UTF8
          NOT LIKE '%[^0-9]%' COLLATE Latin1_General_100_BIN2_UTF8
      AND MunicipalityId = @RequestedMunicipalityId
);
GO
