"""Offline tests for the Copy activity exporter (no network)."""

from __future__ import annotations

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import export_copy_activity as exporter

JOB = "00000000-0000-4000-8000-000000000001"


def run(activity_type="Copy", job=JOB, output=None):
    return {"activityType": activity_type, "activityName": "Copy data1", "pipelineRunId": job,
            "activityRunId": "a", "status": "Succeeded",
            "output": output if output is not None else {"rowsRead": 5000, "rowsCopied": 5000, "dataRead": 1}}


class CopyRecordTests(unittest.TestCase):
    def test_single_copy_activity_is_exported_verbatim(self):
        record = exporter.copy_record([run(), run("Wait")], JOB)
        self.assertEqual((record["activityType"], record["status"]), ("Copy", "Succeeded"))
        self.assertEqual(record["output"], {"rowsRead": 5000, "rowsCopied": 5000, "dataRead": 1})
        self.assertEqual(record["pipelineRunId"], JOB)

    def test_string_output_is_decoded(self):
        record = exporter.copy_record([run(output='{"rowsRead": 3, "rowsCopied": 3}')], JOB)
        self.assertEqual(record["output"]["rowsCopied"], 3)

    def test_missing_ambiguous_or_foreign_runs_stop(self):
        for runs in ([], [run(), run()], [run(output={"rowsRead": 1})], [run(job="other")]):
            with self.subTest(runs=len(runs)), self.assertRaises(ValueError):
                exporter.copy_record(runs, JOB)


if __name__ == "__main__":
    unittest.main()
