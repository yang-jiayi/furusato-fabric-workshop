"""Pre-ingestion policy gates, not live Delta or Ontology acceptance."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import preview30_deploy as deploy
from preview30_runtime import SafetyError

UNSET = {"IsEnabled": None, "Format": "", "TargetLatencyInMinutes": None, "Backfill": None}
ENABLED = {"IsEnabled": 1, "Format": "parquet", "TargetLatencyInMinutes": 5, "Backfill": 0}
SCHEMA = {"OrderedColumns": [
    {"Name": name, "CslType": kind} for name, kind in (
        ("EventID", "string"), ("DonationID", "long"), ("DonorID", "long"),
        ("MunicipalityID", "string"), ("GiftID", "long"), ("DonationAmountYen", "long"),
        ("DonatedAt", "datetime"), ("PaymentMethod", "string"), ("WorkshopRunId", "string"),
        ("ParticipantAlias", "string"), ("PublishedAtUtc", "datetime"), ("SourceFile", "string"))]}


def result(row):
    return {"Tables": [{"Columns": [{"ColumnName": name} for name in row],
                        "Rows": [list(row.values())]}]}


class MirroringTests(unittest.TestCase):
    def run_preparation(self, *, policy=None, rls=None, rows=0, after=None, schema=None):
        d = Mock(evidence=Path(self.tmp.name))
        mutations = []
        current = dict(UNSET if policy is None else policy)

        def kusto(_d, csl, **kwargs):
            if kwargs.get("mutation"):
                self.assertTrue(kwargs["sensitive_policy"])
                self.assertEqual(csl, ".alter-merge table DonationEvents policy mirroring "
                                 "dataformat=parquet with (IsEnabled=true,TargetLatencyInMinutes=5);")
                mutations.append(csl)
                current.clear()
                current.update(ENABLED if after is None else after)
                return result({"Policy": '{"ConnectionStrings":["private"]}'})
            if "row_level_security" in csl:
                return result({"Policy": rls})
            if "schema as json" in csl:
                return result({"Schema": json.dumps(SCHEMA if schema is None else schema)})
            if "summarize RawRows" in csl:
                return result({"RawRows": rows})
            return result(current)

        with patch.object(deploy, "kusto_call", side_effect=kusto):
            self.outcome = deploy.prepare_donation_mirroring(d)
        d.require_owned.assert_called_once_with("kqlDatabase")
        return mutations

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def test_enables_exact_own_table_before_ingestion(self):
        self.assertEqual(len(self.run_preparation()), 1)
        self.assertEqual(self.outcome["state"], "enabled-before-first-ingestion")
        self.assertFalse(self.outcome["oneLakeDataReady"])
        self.assertFalse(self.outcome["nativeTimeSeriesAccepted"])

    def test_reuses_exact_policy_without_write_even_with_existing_rows(self):
        self.assertEqual(self.run_preparation(policy=ENABLED, rows=5000), [])
        self.assertEqual(self.outcome["state"], "reused-enabled")

    def test_refuses_security_existing_rows_or_conflicting_policy(self):
        for kwargs in ({"rls": '{"IsEnabled":true}'}, {"rows": 5000},
                       {"policy": {**ENABLED, "IsEnabled": 0}},
                       {"policy": {**ENABLED, "Backfill": 1}},
                       {"schema": {"OrderedColumns": []}}):
            with self.subTest(kwargs=kwargs), self.assertRaises(SafetyError):
                self.run_preparation(**kwargs)

    def test_wrong_readback_stops_before_ingestion(self):
        with self.assertRaises(SafetyError):
            self.run_preparation(after=UNSET)

    def test_failed_preparation_precedes_pipeline_or_activator_creation(self):
        d = Mock(evidence=Path(self.tmp.name))
        with patch.object(deploy, "Deployment", return_value=d), \
             patch.object(deploy, "kusto_call", return_value={}), \
             patch.object(deploy, "prepare_donation_mirroring", side_effect=SafetyError("unverified")):
            with self.assertRaisesRegex(SafetyError, "unverified"):
                deploy.deploy_realtime(Mock())
        d.create.assert_not_called()

    def test_policy_response_preserves_diagnostics_without_credentials(self):
        body = {"Tables": [{"Columns": [{"ColumnName": "Policy"}], "Rows": [
            ['{"IsEnabled":true,"ConnectionStrings":["AccountKey=private"]}']]}],
                "error": {"code": "BadRequest", "message": 'Rejected; password="private"'}}
        safe = deploy._safe_policy_response(body)
        self.assertNotIn("private", json.dumps(safe))
        self.assertEqual(safe["error"]["code"], "BadRequest")
        self.assertIn("Rejected", safe["error"]["message"])


if __name__ == "__main__":
    unittest.main()
