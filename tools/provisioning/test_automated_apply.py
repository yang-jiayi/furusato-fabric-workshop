"""Explicit headless execution must preserve the interactive safety defaults."""
from __future__ import annotations

import dataclasses
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys
import types
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import workshop_runtime as runtime


class AutomatedApplyTests(unittest.TestCase):
    def config(self, **overrides):
        values = dict(
            participant_id="912",
            expected_workspace_name="Workshop",
            apply_changes=True,
            exclusive_create_window_confirmed=True,
            execute_notebook_01=True,
            refresh_graph=True,
            create_data_agent=True,
            create_pipeline=True,
            create_reflex=True,
        )
        values.update(overrides)
        return runtime.ProvisioningConfig(**values)

    def plan(self, config):
        payload = {
            "assetHashes": {name: "digest" for name in (
                "lakehouseSpec", "eventhouseSpec", "kqlSchema", "notebook01",
                "pipeline", "ontologyTemplate", "dataAgent", "reflex",
            )},
        }
        from unittest.mock import patch
        with patch.object(runtime, "provisioning_payload_digest", return_value="payload"):
            return runtime.build_preview_plan(
                config, payload, workspace_name="Workshop",
                folder_id="confirmed-folder", existing_items=[],
            )

    def test_interactive_default_rejects_jobs(self):
        config = self.config()
        plan = self.plan(config)
        config.confirmed_plan_sha256 = plan.sha256
        with self.assertRaisesRegex(runtime.ProvisioningError, "interactively"):
            runtime.validate_apply_gates(config, plan, {"isForInteractive": False})
        runtime.validate_apply_gates(config, plan, {"isForInteractive": True})

    def test_automation_is_part_of_the_confirmed_plan(self):
        original = self.config()
        automatic = self.config(allow_automated_apply=True)
        self.assertNotEqual(self.plan(original).sha256, self.plan(automatic).sha256)
        automatic.confirmed_plan_sha256 = self.plan(original).sha256
        with self.assertRaisesRegex(runtime.ProvisioningError, "preview"):
            runtime.validate_apply_gates(automatic, self.plan(automatic), {})
        automatic.confirmed_plan_sha256 = self.plan(automatic).sha256
        runtime.validate_apply_gates(automatic, self.plan(automatic), {})

    def test_shared_workspace_notebook_names_are_opt_in_and_plan_bound(self):
        original = self.config()
        isolated = self.config(use_participant_notebook_names=True)
        self.assertEqual(self.plan(original).names.notebook01, "Notebook_01_Furusato_Prepare_Ontology_Data")
        self.assertEqual(self.plan(isolated).names.notebook01, "Notebook_01_Furusato_Prepare_Ontology_Data_912")
        self.assertNotEqual(self.plan(original).sha256, self.plan(isolated).sha256)
        with self.assertRaises(runtime.ProvisioningError):
            runtime.validate_config(self.config(use_participant_notebook_names="true"))

    def test_automation_keeps_workspace_exclusivity_and_component_guards(self):
        for changes in (
            {"exclusive_create_window_confirmed": False},
            {"create_pipeline": False},
            {"expected_workspace_name": "Different"},
        ):
            config = self.config(allow_automated_apply=True, **changes)
            plan = self.plan(config)
            config.confirmed_plan_sha256 = plan.sha256
            with self.subTest(changes=changes), self.assertRaises(runtime.ProvisioningError):
                runtime.validate_apply_gates(config, plan, {})
        for changes in (
            {"allow_automated_apply": "true"},
            {"allow_automated_apply": True, "expected_workspace_name": ""},
        ):
            with self.subTest(changes=changes), self.assertRaises(runtime.ProvisioningError):
                runtime.validate_config(self.config(**changes))

    def test_analytics_automation_is_explicit_and_workspace_bound(self):
        path = ROOT / "workshop" / "v2.7.0" / "notebooks" / "Notebook_05_Furusato_Analytics_Quality_and_BI.ipynb"
        notebook = json.loads(path.read_text(encoding="utf-8"))
        module = types.ModuleType("_furusato_automation_analytics")
        sys.modules[module.__name__] = module
        source = next(
            "".join(cell["source"]) for cell in notebook["cells"]
            if "class AnalyticsExtensionConfig:" in "".join(cell["source"])
        )
        exec(compile(source, str(path), "exec"), module.__dict__)
        base = module.AnalyticsExtensionConfig(participant_id="912")
        self.assertFalse(base.allow_automated_apply)
        enabled = dataclasses.replace(
            base, allow_automated_apply=True, expected_workspace_name="Workshop",
        )
        self.assertNotEqual(module.build_plan(base)["sha256"], module.build_plan(enabled)["sha256"])
        other = dataclasses.replace(enabled, expected_workspace_name="Different")
        self.assertNotEqual(module.build_plan(enabled)["sha256"], module.build_plan(other)["sha256"])
        for changes in (
            {"allow_automated_apply": "true"},
            {"allow_automated_apply": True},
            {"allow_automated_apply": True, "expected_workspace_name": "Workshop", "apply_changes": True},
        ):
            with self.subTest(changes=changes), self.assertRaises(module.AnalyticsExtensionError):
                module.validate_config(dataclasses.replace(base, **changes))

    def test_only_precompilation_refresh_failure_is_recoverable(self):
        current = [datetime(2026, 1, 1, tzinfo=timezone.utc)]
        client = runtime.WorkshopFabricClient(
            lambda: "unused", lambda: "unused",
            clock=lambda: current[0],
            sleeper=lambda seconds: current.__setitem__(0, current[0] + timedelta(seconds=seconds)),
            timeout_seconds=60, poll_interval_seconds=10,
        )
        compiled = []
        client.wait_for_graph_compilation = lambda *args: compiled.append(True)
        failure = {"id": "initial", "status": "Failed", "failureReason": {"errorCode": "GraphNotRefreshable"}}
        client.recent_jobs = lambda *args, **kwargs: [failure]
        submitted = []
        def request(*args, **kwargs):
            self.assertEqual(compiled, [True])
            submitted.append(True)
            return types.SimpleNamespace(
                status_code=202, headers={"Location": "https://api.fabric.microsoft.com/jobs/instances/recovered"},
            )
        client._request = request
        client.poll_job = lambda workspace, graph, job: {"id": job, "status": "Completed"}
        result, state = client.run_or_reuse_graph_refresh("workspace", "graph")
        self.assertEqual((result["id"], state, len(submitted)), ("recovered", "STARTED", 1))
        failure["failureReason"]["errorCode"] = "AccessDenied"
        result, state = client.run_or_reuse_graph_refresh("workspace", "graph")
        self.assertEqual((result["id"], state, len(submitted)), ("initial", "RECENT_REUSED", 1))


if __name__ == "__main__":
    unittest.main()
