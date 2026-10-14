-- Read-only independent schema evidence for the measured profile.
-- Save the result privately as a JSON array of these four column names.
SELECT [TABLE_SCHEMA], [TABLE_NAME], [COLUMN_NAME], [DATA_TYPE]
FROM [INFORMATION_SCHEMA].[COLUMNS]
WHERE ([TABLE_SCHEMA] = 'dbo' AND [TABLE_NAME] IN (
    'ot_prefecture', 'ot_donor', 'ot_gift_category', 'ot_gift',
    'ot_mun_category_metric', 'ot_pref_donation_flow',
    'agent_donation_detail', 'agent_donor_catalog_supplier',
    'agent_municipality_snapshot', 'agent_prefecture_category_metric',
    'agent_relationship_dictionary', 'agent_supplier_catalog'))
   OR ([TABLE_SCHEMA] = 'bronze' AND [TABLE_NAME] = 'donation_events_raw')
   OR ([TABLE_SCHEMA] = 'silver' AND [TABLE_NAME] = 'donation_event')
   OR ([TABLE_SCHEMA] = 'quarantine' AND [TABLE_NAME] = 'donation_events_rejected')
   OR ([TABLE_SCHEMA] = 'ops' AND [TABLE_NAME] IN ('analytics_publish_control', 'dq_rule_results'))
ORDER BY [TABLE_SCHEMA], [TABLE_NAME], [ORDINAL_POSITION];
