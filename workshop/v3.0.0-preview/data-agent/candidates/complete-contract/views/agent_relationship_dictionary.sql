CREATE VIEW dbo.agent_relationship_dictionary AS
SELECT
    CAST('MunicipalityInPrefecture' AS varchar(64)) AS RelationshipName,
    CAST('Municipality' AS varchar(64)) AS DeclaredFromEntity,
    CAST('Prefecture' AS varchar(64)) AS DeclaredToEntity
UNION ALL SELECT 'DonorMadeDonation','Donor','Donation'
UNION ALL SELECT 'DonationSelectedGift','Donation','Gift'
UNION ALL SELECT 'SupplierProvidesGift','Supplier','Gift'
UNION ALL SELECT 'DonorLivesInPrefecture','Donor','Prefecture'
UNION ALL SELECT 'SupplierInPrefecture','Supplier','Prefecture'
UNION ALL SELECT 'DonationToMunicipality','Donation','Municipality'
UNION ALL SELECT 'MunicipalityCatalogsGift','Municipality','Gift'
UNION ALL SELECT 'GiftInCategory','Gift','GiftCategory'
UNION ALL SELECT 'MunHasCategoryMetric','Municipality','MunicipalityCategoryMetric'
UNION ALL SELECT 'MunMetricForCategory','MunicipalityCategoryMetric','GiftCategory'
UNION ALL SELECT 'PrefHasCategoryMetric','Prefecture','PrefectureCategoryMetric'
UNION ALL SELECT 'PrefMetricForCategory','PrefectureCategoryMetric','GiftCategory'
UNION ALL SELECT 'ResidencePrefHasFlow','Prefecture','PrefectureDonationFlow'
UNION ALL SELECT 'FlowToRecipientPref','PrefectureDonationFlow','Prefecture'
