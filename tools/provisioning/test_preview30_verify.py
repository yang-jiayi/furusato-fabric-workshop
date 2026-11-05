"""Offline tests for strict OneLake Delta/Parquet Gold qualification."""
from __future__ import annotations

import json
import unittest

from preview30_runtime import scope_fingerprint, SafetyError
from preview30_verify import (
    GOLD_EXPECTED_BY_SOURCE, _resolve_delta_active_files, assess_gold_parquet,
    validate_owned_gold_lakehouse,
)


WORKSPACE = "22222222-2222-4222-8222-222222222222"
FOLDER = "33333333-3333-4333-8333-333333333333"
LAKEHOUSE = "44444444-4444-4444-8444-444444444444"
GENERATION = "55555555-5555-4555-8555-555555555555"
TABLES = [
    "bronze.prefectures_raw", "bronze.municipalities_raw", "bronze.donors_raw",
    "bronze.gift_categories_raw", "bronze.gifts_raw", "bronze.suppliers_raw",
    "bronze.supplier_gifts_raw", "bronze.donations_raw", "bronze.donation_events_raw",
    "silver.prefecture", "silver.municipality", "silver.donor", "silver.gift_category",
    "silver.gift", "silver.supplier", "silver.supplier_gift", "silver.donation",
    "silver.donation_event", "gold.prefecture", "gold.municipality", "gold.donor",
    "gold.gift_category", "gold.gift", "gold.date", "gold.donations",
    "gold.donation_agent", "ops.dq_rule_results", "ops.run_telemetry",
    "quarantine.donation_events_rejected",
]
JOB = {"generationId": GENERATION, "runId": "completed-run", "planSha256": "a" * 64}


def _file_receipt():
    return {"path": "part-00000.parquet", "sha256": "b" * 64, "requestId": "request-1"}


def observations():
    result = {}
    for table in TABLES:
        result[table] = {
            "table": table, "deltaVersion": 0, "deltaLogs": [
                {"version": 0, "sha256": "c" * 64, "requestId": "log-request-1"}],
            "files": [_file_receipt()], "rowCount": 1, "generationIds": [GENERATION],
        }
    result["bronze.donation_events_raw"].update(rowCount=15000, DonationAmountYen=253886000)
    result["silver.donation_event"].update(rowCount=14900, DonationAmountYen=252058000)
    result["quarantine.donation_events_rejected"].update(rowCount=100, DonationAmountYen=1828000)
    result["gold.donations"].update(
        rowCount=94900,
        byDataSource={
            name: {"rows": rows, "donationAmountYen": yen}
            for name, (rows, yen) in GOLD_EXPECTED_BY_SOURCE.items()
        },
    )
    result["ops.analytics_publish_control"] = {
        "table": "ops.analytics_publish_control", "deltaVersion": 0,
        "deltaLogs": [{"version": 0, "sha256": "c" * 64, "requestId": "log-request-1"}],
        "files": [_file_receipt()], "rowCount": 1,
        "controlRows": [{
            "ControlKey": "furusato-analytics-extension", "State": "Ready",
            "GenerationId": JOB["generationId"], "RunId": JOB["runId"],
            "PlanSha256": JOB["planSha256"],
        }],
    }
    return result


class GoldParquetAssessmentTests(unittest.TestCase):
    def test_exact_generation_and_reconciliation_pass(self):
        result = assess_gold_parquet(observations(), TABLES, JOB)
        self.assertEqual(result["generationId"], GENERATION)
        self.assertEqual((result["rawRows"], result["rawYen"]), (15000, 253886000))
        self.assertEqual((result["acceptedRows"], result["acceptedYen"]), (14900, 252058000))
        self.assertEqual((result["quarantinedRows"], result["quarantinedYen"]), (100, 1828000))
        self.assertEqual((result["goldRows"], result["goldYen"]), (94900, 1596157000))

    def test_missing_table_is_rejected(self):
        data = observations()
        del data[TABLES[-1]]
        with self.assertRaises(SafetyError):
            assess_gold_parquet(data, TABLES, JOB)

    def test_stale_and_mixed_generations_are_rejected(self):
        for generation_ids in (["stale-generation"], [GENERATION, "other-generation"]):
            data = observations()
            data["gold.donations"]["generationIds"] = generation_ids
            with self.subTest(generation_ids=generation_ids), self.assertRaises(SafetyError):
                assess_gold_parquet(data, TABLES, JOB)

    def test_total_mismatch_is_rejected(self):
        data = observations()
        data["bronze.donation_events_raw"]["DonationAmountYen"] += 1
        with self.assertRaises(SafetyError):
            assess_gold_parquet(data, TABLES, JOB)

    def test_control_not_ready_is_rejected(self):
        data = observations()
        data["ops.analytics_publish_control"]["controlRows"][0]["State"] = "Publishing"
        with self.assertRaises(SafetyError):
            assess_gold_parquet(data, TABLES, JOB)

    def test_receipt_only_input_is_rejected(self):
        data = observations()
        for value in data.values():
            value.pop("files", None)
            value.pop("deltaLogs", None)
        with self.assertRaises(SafetyError):
            assess_gold_parquet(data, TABLES, JOB)

    def test_delta_removes_superseded_files_from_active_snapshot(self):
        logs = [
            (0, (json.dumps({"add": {"path": "old.parquet", "size": 1}}) + "\n").encode()),
            (1, (json.dumps({"remove": {"path": "old.parquet"}}) + "\n"
                 + json.dumps({"add": {"path": "new.parquet", "size": 2}}) + "\n").encode()),
        ]
        active = _resolve_delta_active_files(logs)
        self.assertEqual(set(active), {"new.parquet"})

    def test_delta_version_gap_is_rejected(self):
        logs = [(0, b'{"add":{"path":"a.parquet"}}\n'), (2, b'{"add":{"path":"b.parquet"}}\n')]
        with self.assertRaises(SafetyError):
            _resolve_delta_active_files(logs)

    def test_wrong_workspace_and_folder_are_rejected(self):
        scope = {
            "workspaceId": WORKSPACE, "folderId": FOLDER,
            "tenantId": "11111111-1111-4111-8111-111111111111",
            "workspaceName": "test", "environment": "dev",
            "portalSubfolderId": "1", "participantId": "001",
            "forbiddenItemIds": [], "folderMappingVerified": True,
        }
        state = {"scopeSha256": scope_fingerprint(scope)}
        with self.assertRaises(SafetyError):
            validate_owned_gold_lakehouse(
                {**scope, "workspaceId": "66666666-6666-4666-8666-666666666666"},
                state, LAKEHOUSE, {"id": LAKEHOUSE, "folderId": FOLDER},
            )
        with self.assertRaises(SafetyError):
            validate_owned_gold_lakehouse(
                scope, state, LAKEHOUSE,
                {"id": LAKEHOUSE, "folderId": "77777777-7777-4777-8777-777777777777"},
            )


if __name__ == "__main__":
    unittest.main()
