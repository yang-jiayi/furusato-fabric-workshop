"""Offline tests for the read-only Data Agent service check; no network."""

from __future__ import annotations

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import agent_service_check as asc


def fake_service():
    elements = {
        None: [{"id": "root", "displayName": "LH", "type": "Lakehouse", "hasSubElements": True}],
        "root": [{"id": "dbo", "displayName": "dbo", "type": "Schema", "hasSubElements": True}],
        "dbo": [
            {"id": "views", "displayName": "Views", "type": "ViewGrouping", "hasSubElements": True},
            {"id": "t1", "displayName": "ot_donation", "type": "Table", "isSelected": False},
        ],
        "views": [{"id": "v1", "displayName": "agent_view", "type": "View", "state": "Available",
                   "isSelected": True, "hasSubElements": True}],
        "v1": [{"id": "c1", "displayName": "A", "isSelected": True},
               {"id": "c2", "displayName": "B", "isSelected": False}],
    }
    fewshots = [
        {"id": "1", "validationStatus": {"value": "Valid"}},
        {"id": "2", "validationStatus": {"value": "Invalid", "reason":
            "Failed to connect to server abc-def.datawarehouse.fabric.microsoft.com "
            "for 12345678-1234-1234-1234-123456789abc"}},
    ]

    def get(path):
        if path.endswith("/datasources"):
            return {"value": [{"id": "ds", "type": "LakehouseTables", "displayName": "LH"}]}
        if "/fewshots" in path:
            return {"value": fewshots}
        root = path.split("rootId=")[1] if "rootId=" in path else None
        return {"value": elements[root]}

    return get


class AgentServiceCheckTests(unittest.TestCase):
    def test_summary_reports_validation_and_views_without_hosts_or_ids(self):
        summary, raw = asc.check(fake_service(), "ws", "agent", "published",
                                 {"agent_view": {"A", "B"}})
        source = summary["datasources"][0]
        self.assertEqual(source["examples"]["status"], {"Invalid": 1, "Valid": 1})
        reason = source["examples"]["nonValidReasons"][0]["reason"]
        self.assertIn("<host>", reason)
        self.assertIn("<id>", reason)
        self.assertNotIn("datawarehouse", reason)
        view = source["views"]["agent_view"]
        self.assertEqual((view["state"], view["selected"], view["columnsSelected"]), ("Available", True, 1))
        self.assertEqual(view["unselectedColumns"], ["B"])
        self.assertTrue(view["matchesInformationSchema"])
        self.assertEqual(source["selectedTables"], [])
        self.assertEqual(len(raw["datasource-0"]["elements"]), 7)

    def test_column_mismatch_is_reported(self):
        summary, _ = asc.check(fake_service(), "ws", "agent", "staging", {"agent_view": {"A"}})
        self.assertFalse(summary["datasources"][0]["views"]["agent_view"]["matchesInformationSchema"])

    def test_multi_label_service_hosts_are_fully_redacted(self):
        text = asc.redact("connect https://trd-6a1b2c3d4e5f6g7h8i.z9.kusto.fabric.microsoft.com/x failed")
        self.assertNotIn("trd-", text)
        self.assertIn("https://<host>/x", text)


if __name__ == "__main__":
    unittest.main()
