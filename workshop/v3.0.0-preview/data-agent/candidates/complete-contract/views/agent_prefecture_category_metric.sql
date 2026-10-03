CREATE VIEW dbo.agent_prefecture_category_metric AS
SELECT
    m.PrefCategoryMetricId,
    m.PrefectureId,
    p.PrefectureName,
    m.CategoryId,
    c.CategoryName,
    m.PrefCategoryStaticCount AS DonationCount,
    m.PrefCategoryTotalYen AS AmountYen,
    r1.RelationshipName AS PrefectureMetricRelationship,
    r1.DeclaredFromEntity AS PrefectureMetricDeclaredFrom,
    r1.DeclaredToEntity AS PrefectureMetricDeclaredTo,
    r2.RelationshipName AS MetricCategoryRelationship,
    r2.DeclaredFromEntity AS MetricCategoryDeclaredFrom,
    r2.DeclaredToEntity AS MetricCategoryDeclaredTo
FROM dbo.ot_pref_category_metric AS m
JOIN dbo.ot_prefecture AS p ON p.PrefectureId=m.PrefectureId
JOIN dbo.ot_gift_category AS c ON c.CategoryId=m.CategoryId
CROSS JOIN dbo.agent_relationship_dictionary AS r1
CROSS JOIN dbo.agent_relationship_dictionary AS r2
WHERE r1.RelationshipName='PrefHasCategoryMetric'
  AND r2.RelationshipName='PrefMetricForCategory'
