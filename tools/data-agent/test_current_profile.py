"""Offline identity binding and single-write/readback tests; never authenticate."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
from uuid import NAMESPACE_URL, uuid5

import current_profile as current
from source_grounded_profile import decoded_parts, inline_part

WORKSPACE = "00000000-0000-0000-0000-000000000001"
AGENT = "00000000-0000-0000-0000-000000000002"
FOLDER = "00000000-0000-0000-0000-000000000003"


def fixture():
    _, stage, templates = current.load_profile()
    identities = {"{{workspace:id}}": WORKSPACE}
    for kind, source in templates.items():
        identities["{{resource:" + kind + ":id}}"] = str(uuid5(NAMESPACE_URL, kind))
        identities["{{resource:" + kind + ":name}}"] = "Participant_" + kind
        for path, _ in current.native.walk(source["elements"]):
            token = current.node_token(kind, path)
            identities[token] = str(uuid5(NAMESPACE_URL, token))
    stage = {**stage, "aiInstructions": "Existing participant instructions"}
    parts = [inline_part("Files/Config/data_agent.json", {"shared": "keep"}),
             inline_part(".platform", {"identity": AGENT})]
    for status in ("draft", "published"):
        prefix = "Files/Config/" + status + "/"
        parts.append(inline_part(prefix + "stage_config.json", stage))
        for kind, template in templates.items():
            source = current.substitute(template, identities)
            dirname = ("ontologies/" if kind == "ontology" else kind + "-") + source["displayName"]
            parts.append(inline_part(prefix + dirname + ("/ontology.json" if kind == "ontology" else "/datasource.json"), source))
    return {"parts": parts}


def changed(definition, path, callback):
    parts = decoded_parts(definition)
    callback(parts[path])
    return {"parts": [inline_part(name, value) for name, value in parts.items()]}


class CurrentProfileTests(unittest.TestCase):
    def setUp(self):
        self.definition = fixture()
        self.candidate, self.receipt = current.compile_draft(self.definition, WORKSPACE)

    def test_exact_global_and_four_logical_sources(self):
        docs, sources, serialization = current.native.stage_sources(self.candidate, "draft")
        self.assertEqual(serialization, "native-ontology-context")
        self.assertEqual(len(sources), 4)
        text = docs["Files/Config/draft/stage_config.json"]["aiInstructions"]
        self.assertEqual(text.encode(), (current.PROFILE / "global-instructions.txt").read_bytes())
        self.assertEqual(len(text.encode("utf-16-le")) // 2, 9422)
        self.assertFalse(self.receipt["answerAccuracyAccepted"])
        self.assertEqual(self.receipt["counts"]["lakehouse_tables"]["lakehouse_tables.table"], 11)
        self.assertEqual(self.receipt["counts"]["lakehouse_tables"]["lakehouse_tables.column"], 88)

    def test_target_identity_nodes_and_published_shared_parts_are_preserved(self):
        before, after = decoded_parts(self.definition), decoded_parts(self.candidate)
        for path, value in before.items():
            if not path.startswith("Files/Config/draft/"):
                self.assertEqual(after[path], value)
        _, initial, _ = current.native.stage_sources(self.definition, "draft")
        _, actual, _ = current.native.stage_sources(self.candidate, "draft")
        for kind, (_, source) in actual.items():
            self.assertEqual(source["artifactId"], initial[kind][1]["artifactId"])
            self.assertEqual(source["displayName"], initial[kind][1]["displayName"])
            self.assertEqual([node["id"] for _, node in current.native.walk(source["elements"])],
                             [node["id"] for _, node in current.native.walk(initial[kind][1]["elements"])])
        self.assertNotIn("{{node:", json.dumps(after))
        self.assertNotIn("dataSourceInstructions", actual["ontology"][1])

    def test_unknown_selection_and_schema_drift_stop(self):
        _, sources, _ = current.native.stage_sources(self.definition, "draft")
        path = sources["lakehouse_tables"][0]
        for mutation in (
            lambda value: value["elements"].clear(),
            lambda value: value.update(metadata={"unknown": True}),
            lambda value: value["elements"][0].update(newServiceField=True),
            lambda value: value.update(workspaceId=AGENT),
        ):
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                current.compile_draft(changed(self.definition, path, mutation), WORKSPACE)
        extra = copy.deepcopy(self.definition)
        extra["parts"].append(inline_part("Files/Config/draft/unreviewed/fewshots.json", {"fewShots": []}))
        with self.assertRaisesRegex(ValueError, "Unexpected Draft"):
            current.compile_draft(extra, WORKSPACE)

    def test_semantically_identical_duplicate_ids_at_different_paths_are_bound(self):
        _, sources, _ = current.native.stage_sources(self.definition, "draft")
        path = sources["lakehouse_tables"][0]
        def duplicate(value):
            for _, node in current.native.walk(value["elements"]):
                node["id"] = WORKSPACE
        candidate, _ = current.compile_draft(changed(self.definition, path, duplicate), WORKSPACE)
        _, actual, _ = current.native.stage_sources(candidate, "draft")
        self.assertTrue(all(node["id"] == WORKSPACE
                            for _, node in current.native.walk(actual["lakehouse_tables"][1]["elements"])))

    def test_profile_hash_tamper_stops(self):
        with tempfile.TemporaryDirectory() as temp:
            import shutil
            profile = Path(temp) / "profile"
            shutil.copytree(current.PROFILE, profile)
            (profile / "global-instructions.txt").write_text("different", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Profile input changed"):
                current.compile_draft(self.definition, WORKSPACE, profile=profile)

    def test_complete_readback_rejects_source_or_shared_drift(self):
        current.compare_stage(self.candidate, self.candidate, "draft")
        for path in ("Files/Config/draft/stage_config.json", "Files/Config/data_agent.json"):
            with self.subTest(path=path), self.assertRaises(ValueError):
                current.compare_stage(changed(self.candidate, path, lambda value: value.update(unexpected=True)),
                                      self.candidate, "draft")
        extra = copy.deepcopy(self.candidate)
        extra["parts"].append(inline_part("Files/Config/unknown.json", {}))
        with self.assertRaises(ValueError):
            current.compare_stage(extra, self.candidate, "draft")

    def test_apply_single_submission_and_exclusive_recovery_intent(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            inputs = {"definition": self.definition}
            client = Mock(workspace=WORKSPACE)
            client.base = "https://api.fabric.microsoft.com/v1/workspaces/" + WORKSPACE + "/dataAgents/" + AGENT
            client.definition.return_value = self.candidate
            with patch.object(current, "gather", return_value=inputs), patch.object(current, "verify", return_value={"status": "draft-matches"}):
                current.apply(client, root, FOLDER, inputs, self.candidate)
                self.assertEqual(client.request.call_count, 1)
                self.assertTrue((root / "apply-backup.json").is_file())
                with self.assertRaisesRegex(ValueError, "intent exists"):
                    current.apply(client, root, FOLDER, inputs, self.candidate)
                self.assertEqual(client.request.call_count, 1)

    def test_apply_blocks_concurrent_changes_without_submission(self):
        with tempfile.TemporaryDirectory() as temp:
            client = Mock()
            with patch.object(current, "gather", return_value={"definition": self.candidate}):
                with self.assertRaisesRegex(ValueError, "changed since prepare"):
                    current.apply(client, Path(temp), FOLDER, {"definition": self.definition}, self.candidate)
            client.request.assert_not_called()

    def test_prepare_bundle_is_scope_and_source_bound(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            client = Mock(workspace=WORKSPACE, agent=AGENT, origin="https://example.analysis.windows.net")
            inputs = {"definition": self.definition}
            with patch.object(current, "gather", return_value=inputs):
                result = current.prepare(client, root, FOLDER)
            self.assertEqual(result["cloudWrites"], 0)
            current.prepared(root, WORKSPACE, AGENT, FOLDER)
            with self.assertRaisesRegex(ValueError, "scope/profile differs"):
                current.prepared(root, WORKSPACE, AGENT, WORKSPACE)
            value = json.loads((root / "inputs.json").read_bytes())
            value["unknown"] = True
            (root / "inputs.json").write_text(json.dumps(value), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "changed"):
                current.prepared(root, WORKSPACE, AGENT, FOLDER)
            client.request.assert_not_called()

    def test_verification_requires_exact_public_instructions_and_no_extra_examples(self):
        with tempfile.TemporaryDirectory() as temp:
            root, client = Path(temp), Mock()
            client.base = "https://api.fabric.microsoft.com/v1/workspaces/" + WORKSPACE + "/dataAgents/" + AGENT
            _, sources, _ = current.native.stage_sources(self.candidate, "draft")
            public = {kind: {"id": kind, "instructions": source["dataSourceInstructions"],
                             "description": source["userDescription"]}
                      for kind, (_, source) in sources.items() if kind != "ontology"}
            inputs = {"definition": self.candidate, "publicSources": public}
            with patch.object(current, "gather", return_value=inputs):
                client.pages.return_value = []
                result = current.verify(client, root, self.candidate, FOLDER, "draft")
                self.assertTrue(result["completeStageReadbackVerified"])
                self.assertFalse(result["sourceAvailabilityVerified"])
                self.assertFalse(result["answerAccuracyAccepted"])
                self.assertEqual(client.pages.call_count, 3)
                client.pages.return_value = [{"id": "unreviewed-example"}]
                with self.assertRaisesRegex(ValueError, "Unexpected active examples"):
                    current.verify(client, root, self.candidate, FOLDER, "draft")
                client.pages.return_value = []
                public["kusto"]["instructions"] = "changed"
                with self.assertRaisesRegex(ValueError, "Public instructions"):
                    current.verify(client, root, self.candidate, FOLDER, "draft")

    def test_uncertain_write_keeps_intent_and_is_never_replayed(self):
        with tempfile.TemporaryDirectory() as temp:
            root, client = Path(temp), Mock(workspace=WORKSPACE)
            client.base = "https://api.fabric.microsoft.com/v1/workspaces/" + WORKSPACE + "/dataAgents/" + AGENT
            client.completed.side_effect = ValueError("outcome uncertain")
            inputs = {"definition": self.definition}
            with patch.object(current, "gather", return_value=inputs):
                with self.assertRaisesRegex(ValueError, "outcome uncertain"):
                    current.apply(client, root, FOLDER, inputs, self.candidate)
                self.assertTrue((root / "apply-intent.json").exists())
                with self.assertRaisesRegex(ValueError, "intent exists"):
                    current.apply(client, root, FOLDER, inputs, self.candidate)
            self.assertEqual(client.request.call_count, 1)

    def test_publish_single_submission_and_full_readback(self):
        with tempfile.TemporaryDirectory() as temp:
            root, client = Path(temp), Mock()
            client.base = "https://api.fabric.microsoft.com/v1/workspaces/" + WORKSPACE + "/dataAgents/" + AGENT
            client.definition.return_value = self.candidate
            with patch.object(current, "verify", return_value={"status": "matches"}) as verify:
                current.publish(client, root, FOLDER, {"definition": self.definition}, self.candidate)
                self.assertEqual(client.request.call_count, 1)
                self.assertEqual([call.args[-1] for call in verify.call_args_list], ["draft", "published"])
                with self.assertRaisesRegex(ValueError, "intent exists"):
                    current.publish(client, root, FOLDER, {"definition": self.definition}, self.candidate)
                self.assertEqual(client.request.call_count, 1)

    def test_actual_folder_and_item_type_are_required_before_compile(self):
        client = Mock()
        client.agent, client.workspace = AGENT, WORKSPACE
        client.get.side_effect = [{"id": FOLDER}, {"id": AGENT, "type": "DataAgent", "folderId": WORKSPACE}]
        with self.assertRaisesRegex(ValueError, "explicitly scoped folder"):
            current.gather(client, FOLDER)
        client.definition.assert_not_called()

    def test_write_authorization_is_checked_before_client_or_auth(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(current.safety, "Client") as client:
            args = ["apply", "--workspace-id", WORKSPACE, "--folder-id", FOLDER,
                    "--agent-id", AGENT, "--private-root", temp]
            self.assertEqual(current.main(args), 2)
            client.assert_not_called()


if __name__ == "__main__":
    unittest.main()
