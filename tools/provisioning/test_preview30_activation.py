import base64
import json
import unittest
from types import SimpleNamespace

from preview30_activation import _targets
from preview30_runtime import SafetyError


def deployment(settings):
    entities = [
        {
            "uniqueIdentifier": "rule",
            "type": "timeSeriesView-v1",
            "payload": {"definition": {"type": "Rule", "settings": settings}},
        },
        {
            "uniqueIdentifier": "source",
            "type": "realTimeHubSource-v1",
            "payload": {"connection": {"artifactId": "lakehouse", "workspaceId": "workspace"}},
        },
        {
            "uniqueIdentifier": "action",
            "type": "fabricItemAction-v1",
            "payload": {"fabricItem": {"itemId": "pipeline", "workspaceId": "workspace"}},
        },
    ]
    encoded = base64.b64encode(json.dumps(entities).encode()).decode()
    return SimpleNamespace(
        scope={"workspaceId": "workspace"},
        require_owned=lambda key: {"id": key},
        definition=lambda item_id, **kwargs: {
            "parts": [{"path": "ReflexEntities.json", "payload": encoded}]
        },
    )


class NativeDeliveryReadinessTests(unittest.TestCase):
    def test_observed_native_settings_are_ready_for_a_future_probe(self):
        d = deployment({"shouldRun": True, "shouldApplyRuleOnUpdate": False, "delayToleranceMs": 120000})
        self.assertEqual(_targets(d, require_delivery_ready=True)[1], "rule")

    def test_running_without_explicit_tolerance_does_not_allow_upload(self):
        d = deployment({"shouldRun": True, "shouldApplyRuleOnUpdate": False})
        with self.assertRaisesRegex(SafetyError, "do not upload"):
            _targets(d, require_delivery_ready=True)

    def test_lifecycle_inspection_and_stop_remain_available(self):
        d = deployment({"shouldRun": True, "shouldApplyRuleOnUpdate": False})
        self.assertEqual(_targets(d)[1], "rule")

    def test_stopped_rule_does_not_allow_upload(self):
        d = deployment({"shouldRun": False, "shouldApplyRuleOnUpdate": False, "delayToleranceMs": 120000})
        with self.assertRaises(SafetyError):
            _targets(d, require_delivery_ready=True)

    def test_historical_replay_is_rejected(self):
        d = deployment({"shouldRun": True, "shouldApplyRuleOnUpdate": True, "delayToleranceMs": 120000})
        with self.assertRaises(SafetyError):
            _targets(d, require_delivery_ready=True)

    def test_missing_replay_setting_is_rejected(self):
        d = deployment({"shouldRun": True, "delayToleranceMs": 120000})
        with self.assertRaises(SafetyError):
            _targets(d, require_delivery_ready=True)

    def test_insufficient_or_noninteger_tolerance_is_rejected(self):
        for delay in (0, 119999, "120000", True, None):
            with self.subTest(delay=delay):
                d = deployment({"shouldRun": True, "shouldApplyRuleOnUpdate": False, "delayToleranceMs": delay})
                with self.assertRaises(SafetyError):
                    _targets(d, require_delivery_ready=True)

    def test_a_longer_explicit_tolerance_is_allowed(self):
        d = deployment({"shouldRun": True, "shouldApplyRuleOnUpdate": False, "delayToleranceMs": 180000})
        self.assertEqual(_targets(d, require_delivery_ready=True)[1], "rule")


if __name__ == "__main__":
    unittest.main()
