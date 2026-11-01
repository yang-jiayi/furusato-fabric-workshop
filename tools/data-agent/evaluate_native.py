"""Native, single-submission Data Agent evaluator; use --help for entry commands.

Offline: freeze -> plan -> report. Online (explicit opt-in): run one complete
predeclared batch. Never call evaluate_data_agent: its remote answer-key upload,
critic scoring and output-table writes are inappropriate for this workstream.

Runtime: the public MCP endpoint, FabricOpenAIResponses, or an SDK-aligned
HTTP client with a privately supplied, observed workload host. Optional runtime
paths require live qualification; local tests alone are not qualification.
MCP needs no regional host, capacity ID or full SDK.
MCP exposes native answer text only: source query execution/results and backend
conversation IDs are unobservable, so strict quality acceptance stays blocked.
Official protocol/provenance:
https://learn.microsoft.com/fabric/data-science/fabric-data-agent-sdk
https://github.com/microsoft/fabric-samples/tree/main/docs-samples/data-science/data-agent-sdk/responses-api
https://learn.microsoft.com/fabric/data-science/evaluate-data-agent

Private deployment JSON:
{"configurations": [{"label": "...", "workspace_id": "...", "data_agent_id": "...",
 "stage": "production", "data_fingerprint_file": "deployment/data-fingerprint.json"}]}
To avoid the full SDK's notebook/Spark dependencies, add transport="responses-http",
capacity_id and workload_host to each configuration. These values are private.
Prefer transport="mcp", or plan --transport mcp, for the verified public endpoint.
It supports only published/production agents. No browser authentication or
system ODBC driver is used by this transport.
The fingerprint file must document the new deployment's independently verified
source/data state. It is provenance, NEVER replacement native query evidence.

Review schema is generated alongside each capture. All conditions start UNCLEAR.
Each data call needs queries containing language, source, query_pointer,
result_pointer, executed_not_merely_generated=true, complete_returned_result=true.
Pointers address the native response; /@json explicitly opens an encoded JSON
string. Query/result pairing, every call's scope and complete rows need human
review. Unsupported/missing Graph trace shapes remain failures, not guessed SQL.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import importlib.metadata
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse
from uuid import UUID

from native_evaluation import (
    EvaluationError, PrivateStore, TERMINAL, digest, encode, file_digest,
    freeze_suite, grade_case, label, load_suite, native_view, now_utc,
    original_suite, parse_native_body, read_json, review_template, summarize,
)
from native_responses_http import (
    PROTOCOL_VERSION, NativeEvidenceError, RawReply, ResponsesHttpClient,
    diagnostics_feature_unavailable, runtime_config,
)
from native_mcp import (
    CONTRACT as MCP_CONTRACT, PROTOCOL as MCP_PROTOCOL, QUESTION_RPC_ID,
    NativeMcpClient, discover_question_tool, native_view as mcp_view,
    observability as mcp_observability, parse_rpc,
    validate_config as validate_mcp_config,
)
from regression_suite import build_suite as regression_suite


REPO = Path(__file__).resolve().parents[2]
FABRIC_SCOPE = "https://api.fabric.microsoft.com/.default"


def harness_sources() -> dict[str, str]:
    return {
        name: file_digest(Path(__file__).resolve().parent / name)
        for name in (
            "evaluate_native.py", "native_evaluation.py", "native_responses_http.py",
            "native_mcp.py", "mcp_grading.py", "regression_suite.py",
        )
    }


def unpack_raw(reply: Any) -> RawReply:
    http = reply.http_response
    return RawReply(
        body=http.content, status=http.status_code,
        request_body=http.request.content,
    )


def credential_for(name: str):
    from azure.identity import AzureCliCredential, DefaultAzureCredential
    if name == "azure-cli":
        return AzureCliCredential()
    return DefaultAzureCredential(exclude_interactive_browser_credential=True)


class NativeClient:
    """Supported SDK, raw-body access, no query retries or instruction overrides."""

    def __init__(self, config: dict[str, Any], credential: Any, timeout: float):
        from fabric.analytics.environment.credentials import (
            SetFabricAnalyticsDefaultTokenCredentialsGlobally,
        )
        from fabric.dataagent.client import FabricOpenAIResponses

        SetFabricAnalyticsDefaultTokenCredentialsGlobally(credential)
        self.client = FabricOpenAIResponses(
            artifact_name=config["data_agent_id"],
            workspace_name=config["workspace_id"],
            ai_skill_stage=config["stage"], max_retries=0, timeout=timeout,
            credential=credential,
        )
        if (str(self.client.artifact_id).lower() != config["data_agent_id"].lower()
                or str(self.client.workspace_id).lower() != config["workspace_id"].lower()
                or self.client.ai_skill_stage != config["stage"]
                or self.client.api_type != "responses"):
            self.client.close()
            raise EvaluationError("The SDK resolved a different agent, workspace or stage.")

    def new_conversation(self) -> RawReply:
        return unpack_raw(self.client.conversations.with_raw_response.create())

    def submit(self, question: str, conversation_id: str) -> RawReply:
        return unpack_raw(self.client.responses.with_raw_response.create(
            input=question, conversation=conversation_id,
            model=self.client.default_model, stream=False,
        ))

    def retrieve(self, response_id: str) -> RawReply:
        return unpack_raw(self.client.responses.with_raw_response.retrieve(response_id))

    def diagnostics(self, conversation_id: str, response_id: str) -> dict[str, Any]:
        from httpx import HTTPStatusError

        try:
            return self.client.diagnostics.get(
                conversation_id=conversation_id, response_id=response_id,
            )
        except HTTPStatusError as exc:
            response = exc.response
            raise NativeEvidenceError(
                f"Native diagnostics HTTP {response.status_code}; no question retry.",
                response.content,
                response.status_code,
            ) from exc

    def close(self) -> None:
        self.client.close()


class DefinitionReader:
    """Only getDefinition and its read-only LRO: never update, publish or deploy."""

    def __init__(self, credential: Any, timeout: float = 120):
        import requests
        self.session = requests.Session()
        self.credential, self.timeout = credential, timeout

    def request(self, method: str, url: str):
        if (urlparse(url).scheme != "https"
                or urlparse(url).netloc != "api.fabric.microsoft.com"):
            raise EvaluationError("Refusing a cross-host authenticated definition request.")
        for attempt in range(3):
            headers = {"Authorization": f"Bearer {self.credential.get_token(FABRIC_SCOPE).token}"}
            response = self.session.request(
                method, url, headers=headers, timeout=self.timeout, allow_redirects=False,
            )
            if response.status_code not in (429, 500, 502, 503, 504) or attempt == 2:
                return response
            # These requests only READ definitions. Never retry question POSTs.
            response.close()
            time.sleep(2 ** attempt)
        raise AssertionError("unreachable")

    def read(self, config: dict[str, Any]) -> dict[str, Any]:
        url = (
            f"https://api.fabric.microsoft.com/v1/workspaces/{config['workspace_id']}"
            f"/dataAgents/{config['data_agent_id']}/getDefinition"
        )
        with self.request("POST", url) as response:
            if response.status_code == 200:
                return response.json()
            if response.status_code != 202:
                raise EvaluationError(f"Definition read failed with HTTP {response.status_code}.")
            operation_id = response.headers.get("x-ms-operation-id")
            if operation_id:
                # Fabric may return a regional Location. Its documented
                # operation ID also works on the public operations API, so
                # keep authenticated definition reads on the original host.
                location = f"https://api.fabric.microsoft.com/v1/operations/{UUID(operation_id)}"
            else:
                location = response.headers.get("Location", "")
        deadline = time.monotonic() + self.timeout
        while time.monotonic() < deadline:
            with self.request("GET", location) as response:
                if response.status_code != 200:
                    raise EvaluationError(f"Definition LRO read failed with HTTP {response.status_code}.")
                state = response.json()
            if state.get("status") == "Succeeded":
                with self.request("GET", location.rstrip("/") + "/result") as response:
                    if response.status_code != 200:
                        raise EvaluationError("Definition LRO result unavailable.")
                    return response.json()
            if state.get("status") not in ("NotStarted", "Running"):
                raise EvaluationError("Definition LRO failed or had an unknown status.")
            time.sleep(2)
        raise EvaluationError("Definition LRO timed out.")

    def close(self) -> None:
        self.session.close()


def definition_digest(value: dict[str, Any]) -> str:
    """Canonicalize definition part ordering/JSON, not instructions or text."""
    parts = value.get("definition", value).get("parts")
    if not isinstance(parts, list) or not parts:
        raise EvaluationError("Agent definition parts are missing.")
    decoded, names = [], set()
    try:
        for part in parts:
            path = part["path"]
            if path in names or part.get("payloadType") != "InlineBase64":
                raise EvaluationError("Duplicate/unsupported definition part.")
            names.add(path)
            raw = base64.b64decode(part["payload"], validate=True)
            try:
                content = {"json": json.loads(raw)}
            except (ValueError, UnicodeError):
                content = {"bytes_base64": base64.b64encode(raw).decode("ascii")}
            decoded.append({"path": path, "content": content})
    except (KeyError, TypeError, ValueError) as exc:
        raise EvaluationError("Malformed native definition.") from exc
    return digest(sorted(decoded, key=lambda p: p["path"]))


def validate_deployment(store: PrivateStore, value: dict[str, Any]) -> list[dict[str, Any]]:
    configurations = value.get("configurations", [])
    if not configurations:
        raise EvaluationError("Deployment must list ready configurations.")
    labels, identities = set(), set()
    result = []
    for source in configurations:
        config = dict(source)
        key = label(config["label"])
        for field in ("workspace_id", "data_agent_id"):
            config[field] = str(UUID(config[field]))
        if config.get("stage") not in {"production", "sandbox"}:
            raise EvaluationError("Explicit production or sandbox stage required.")
        config["transport"] = config.get("transport", "sdk")
        if config["transport"] == "mcp":
            config.update(validate_mcp_config(config))
            config["native_protocol_contract"] = MCP_CONTRACT
            config["observability"] = mcp_observability()
        elif config["transport"] == "responses-http":
            config.update(runtime_config(config))
            config["native_protocol_contract"] = PROTOCOL_VERSION
        elif config["transport"] != "sdk":
            raise EvaluationError("Unknown native transport.")
        identity = (config["workspace_id"], config["data_agent_id"], config["stage"])
        if key in labels or identity in identities:
            raise EvaluationError("Duplicate configuration label or agent/stage.")
        labels.add(key)
        identities.add(identity)
        path = store.path(config["data_fingerprint_file"])
        config["data_fingerprint_sha256"] = file_digest(path)
        result.append(config)
    return result


def create_plan(
    store: PrivateStore, name: str, deployment: dict[str, Any],
    original_file: str, heldout_file: str | None, repeats: int, heldout_repeats: int,
    transport: str | None = None, regression_file: str | None = None,
    regression_repeats: int = 1,
) -> str:
    label(name)
    if (repeats < 1 or regression_repeats < 1
            or (heldout_file is not None and heldout_repeats < 1)):
        raise EvaluationError("All suite repetition counts must be positive.")
    suites = {"original": load_suite(store, original_file)}
    if heldout_file is not None:
        suites["heldout"] = load_suite(store, heldout_file)
    if regression_file is not None:
        suites["regression"] = load_suite(store, regression_file)
    if len(suites) == 1:
        raise EvaluationError("A held-out or regression suite is required.")
    if any(suite["kind"] != kind for kind, suite in suites.items()):
        raise EvaluationError("Original, held-out and regression suites cannot be interchanged.")
    if transport is not None:
        # Transport is chosen before registration, never changed at run time.
        deployment = {**deployment, "configurations": [
            {**c, "transport": transport} for c in deployment.get("configurations", [])
        ]}
    configurations = validate_deployment(store, deployment)
    defaults = {"original": repeats}
    if heldout_file is not None:
        defaults["heldout"] = heldout_repeats
    if regression_file is not None:
        defaults["regression"] = regression_repeats
    schedules = {
        c["label"]: {kind: c.get(f"{kind}_repeats", defaults[kind]) for kind in suites}
        for c in configurations
    }
    if any(type(n) is not int or n < 1 for schedule in schedules.values() for n in schedule.values()):
        raise EvaluationError("Per-configuration repetition counts must be positive integers.")
    files = {"original": original_file}
    if heldout_file is not None:
        files["heldout"] = heldout_file
    if regression_file is not None:
        files["regression"] = regression_file
    plan = {
        "schema_version": 1, "name": name, "created_at_utc": now_utc(),
        "harness_sources": harness_sources(),
        "configurations": configurations,
        "suite_files": files,
        "suite_sha256": {k: digest(v) for k, v in suites.items()},
        "repetitions": {kind: defaults[kind] for kind in suites},
        "per_configuration_repetitions": schedules,
        "slots": [
            {"configuration": c["label"], "suite": suite, "repeat": repeat}
            for c in configurations for suite, n in schedules[c["label"]].items()
            for repeat in range(1, n + 1)
        ],
        "selection_policy": "all predeclared batches; never best-per-question",
    }
    relative = f"campaigns/{name}/plan.json"
    store.write(relative, {"plan": plan, "plan_sha256": digest(plan)})
    return relative


def _record_artifact(record: dict[str, Any], name: str) -> dict[str, str]:
    matches = [
        item for item in record.get("artifacts", [])
        if Path(item.get("path", "")).name == name
    ]
    if len(matches) != 1:
        raise EvaluationError(f"Expected one captured {name} artifact.")
    return matches[0]


def _continuation_entry(
    store: PrivateStore, source_plan: dict[str, Any], slot: dict[str, Any],
    case_id: str, diagnostics_receipt_path: str,
) -> dict[str, Any]:
    if not isinstance(diagnostics_receipt_path, str) or not diagnostics_receipt_path:
        raise EvaluationError("Diagnostics readback receipt path is required.")
    if slot not in source_plan.get("slots", []):
        raise EvaluationError("Continuation source slot was not predeclared.")
    suite = load_suite(store, source_plan["suite_files"][slot["suite"]])
    if case_id not in {case["id"] for case in suite["cases"]}:
        raise EvaluationError("Continuation case is not in the frozen source suite.")
    source_record_path = f"{slot_path(source_plan, slot)}/{label(case_id)}/record.json"
    record, record_sha = _read_capture_record(store, source_record_path)
    if (record.get("status") != "evidence_incomplete"
            or record.get("error_type") != "HTTPStatusError"
            or record.get("submission_count") != 1
            or record.get("fresh_conversation") is not True
            or record.get("response", {}).get("status") != "completed"
            or record.get("native_structure_issues") != []
            or record.get("diagnostics_status") is not None
            or record.get("configuration_before_sha256")
            != record.get("configuration_after_sha256")):
        raise EvaluationError("Continuation source is not the exact consumed T01 diagnostics-only capture.")
    verify_record(store, record)
    source_batch_path = f"{slot_path(source_plan, slot)}/batch.json"
    source_batch = store.read(source_batch_path)
    if (source_batch.get("status") != "stopped_fail_closed"
            or source_batch.get("slot") != slot
            or source_batch.get("case_statuses") != [
                {"case_id": case_id, "status": "evidence_incomplete"},
            ]):
        raise EvaluationError("Continuation source batch is not the expected stopped T01 capture.")

    response_artifact = _record_artifact(record, Path(record["response_artifact"]).name)
    configuration_before = _record_artifact(record, "configuration-before.json")
    configuration_after = _record_artifact(record, "configuration-after.json")
    native_error = _record_artifact(record, "native-error.body")
    diagnostics_receipt_sha = file_digest(store.path(diagnostics_receipt_path))
    diagnostics_receipt = store.read(diagnostics_receipt_path)
    diagnostics_body_path = diagnostics_receipt.get("body_path")
    if not isinstance(diagnostics_body_path, str):
        raise EvaluationError("Diagnostics readback body path is missing.")
    diagnostics_body_sha = file_digest(store.path(diagnostics_body_path))
    native_error_body = store.path(native_error["path"]).read_bytes()
    diagnostics_body = store.path(diagnostics_body_path).read_bytes()
    if (not diagnostics_feature_unavailable(
                diagnostics_body, diagnostics_receipt.get("http_status"))
            or diagnostics_body != native_error_body
            or diagnostics_receipt.get("classification") != "feature_unavailable"
            or diagnostics_receipt.get("matches_original_error_body") is not True
            or diagnostics_receipt.get("source_record_path") != source_record_path
            or diagnostics_receipt.get("source_record_sha256") != record_sha
            or diagnostics_receipt.get("source_response_artifact_sha256")
            != response_artifact["sha256"]
            or diagnostics_receipt.get("response_id") != record["response"]["id"]
            or diagnostics_receipt.get("conversation_id") != record["conversation_id"]
            or diagnostics_receipt.get("body_sha256") != diagnostics_body_sha):
        raise EvaluationError("Diagnostics readback is not bound to the exact feature-unavailable response.")
    return {
        "slot": slot,
        "case_id": case_id,
        "source_record_path": source_record_path,
        "source_record_sha256": record_sha,
        "source_batch_path": source_batch_path,
        "source_batch_sha256": file_digest(store.path(source_batch_path)),
        "source_response_artifact_path": response_artifact["path"],
        "source_response_artifact_sha256": response_artifact["sha256"],
        "source_configuration_before_artifact_path": configuration_before["path"],
        "source_configuration_before_artifact_sha256": configuration_before["sha256"],
        "source_configuration_after_artifact_path": configuration_after["path"],
        "source_configuration_after_artifact_sha256": configuration_after["sha256"],
        "source_definition_sha256": record["configuration_before_sha256"],
        "source_native_error_artifact_path": native_error["path"],
        "source_native_error_artifact_sha256": native_error["sha256"],
        "diagnostics_receipt_path": diagnostics_receipt_path,
        "diagnostics_receipt_sha256": diagnostics_receipt_sha,
        "diagnostics_body_path": diagnostics_body_path,
        "diagnostics_body_sha256": diagnostics_body_sha,
        "diagnostics_http_status": diagnostics_receipt["http_status"],
    }


def _captured_slot_entry(
    store: PrivateStore, source_plan: dict[str, Any], slot: dict[str, Any],
    case_id: str,
) -> dict[str, Any]:
    if slot not in source_plan.get("slots", []):
        raise EvaluationError("Captured continuation source slot was not predeclared.")
    suite = load_suite(store, source_plan["suite_files"][slot["suite"]])
    case = next((item for item in suite["cases"] if item["id"] == case_id), None)
    if case is None:
        raise EvaluationError("Captured continuation case is not in the frozen source suite.")
    base = slot_path(source_plan, slot)
    case_path = f"{base}/{label(case_id)}"
    source_record_path = f"{case_path}/record.json"
    record, record_sha = _read_capture_record(store, source_record_path)
    if (record.get("case_id") != case_id or record.get("question") != case["question"]
            or not captured_terminal_outcome(record)):
        raise EvaluationError("Only one verified terminal question capture can be continued.")
    verify_record(store, record)

    source_batch_path = f"{base}/batch.json"
    source_batch = store.read(source_batch_path)
    matching = [
        item for item in source_batch.get("case_statuses", [])
        if item.get("case_id") == case_id
    ]
    if (source_batch.get("slot") != slot
            or source_batch.get("status") not in {
                "captured_pending_human_review", "stopped_fail_closed",
            }
            or len(matching) != 1
            or matching[0].get("status") != record.get("status")):
        raise EvaluationError("Captured continuation record differs from its source batch.")

    baseline_path = f"campaigns/{source_plan['name']}/{slot['configuration']}/baseline-definition.json"
    baseline = store.read(baseline_path)
    baseline_sha = definition_digest(baseline)
    if (baseline_sha != source_batch.get("configuration_sha256")
            or record.get("configuration_before_sha256") != baseline_sha
            or record.get("configuration_after_sha256") != baseline_sha):
        raise EvaluationError("Captured continuation configuration differs from its frozen batch.")
    response_artifact = _record_artifact(record, Path(record["response_artifact"]).name)
    configuration_before = _record_artifact(record, "configuration-before.json")
    configuration_after = _record_artifact(record, "configuration-after.json")
    review_path = f"{case_path}/review.json"
    review = store.read(review_path)
    if not isinstance(review, dict) or review.get("case_id") != case_id:
        raise EvaluationError("Captured continuation review is missing or belongs to another case.")
    case_status = matching[0]
    return {
        "mode": "captured-slot",
        "slot": slot,
        "case_id": case_id,
        "source_plan_sha256": digest(source_plan),
        "source_record_path": source_record_path,
        "source_record_sha256": record_sha,
        "source_record_status": record["status"],
        "source_batch_path": source_batch_path,
        "source_batch_sha256": file_digest(store.path(source_batch_path)),
        "source_response_artifact_path": response_artifact["path"],
        "source_response_artifact_sha256": response_artifact["sha256"],
        "source_configuration_before_artifact_path": configuration_before["path"],
        "source_configuration_before_artifact_sha256": configuration_before["sha256"],
        "source_configuration_after_artifact_path": configuration_after["path"],
        "source_configuration_after_artifact_sha256": configuration_after["sha256"],
        "source_definition_sha256": baseline_sha,
        "source_review_path": review_path,
        "source_review_sha256": file_digest(store.path(review_path)),
        "source_capture_mode": case_status.get("capture_mode", "fresh_submission"),
        "source_new_question_submissions": case_status.get(
            "new_question_submissions", record.get("submission_count", 0),
        ),
    }


def _validate_continuation_entry(
    store: PrivateStore, source_plan: dict[str, Any], entry: dict[str, Any],
) -> None:
    if entry.get("mode") == "captured-slot":
        source_slot = entry.get("slot")
        case_id = entry.get("case_id")
        if not isinstance(source_slot, dict) or not isinstance(case_id, str):
            raise EvaluationError("Captured continuation entry lacks its slot or case.")
        if _captured_slot_entry(store, source_plan, source_slot, case_id) != entry:
            raise EvaluationError("Captured continuation mapping differs from its source evidence.")
        return
    source_slot = entry.get("slot")
    case_id = entry.get("case_id")
    if not isinstance(source_slot, dict) or not isinstance(case_id, str):
        raise EvaluationError("Continuation entry lacks its exact source slot and case.")
    rebuilt = _continuation_entry(
        store, source_plan, source_slot, case_id, entry.get("diagnostics_receipt_path", ""),
    )
    if rebuilt != entry:
        raise EvaluationError("Continuation mapping differs from the immutable source evidence.")


def create_recovery_plan(
    store: PrivateStore, name: str, source_plan_path: str,
    configuration: str, suite_name: str, repeat: int, case_id: str,
    diagnostics_receipt_path: str,
) -> str:
    label(name)
    if type(repeat) is not int or repeat < 1:
        raise EvaluationError("Continuation repeat must be a positive integer.")
    source_plan = load_plan(store, source_plan_path, for_execution=False)
    source_plan_sha = digest(source_plan)
    slot = {"configuration": label(configuration), "suite": label(suite_name), "repeat": repeat}
    entry = _continuation_entry(store, source_plan, slot, label(case_id), diagnostics_receipt_path)
    continuation_path = f"campaigns/{name}/continuation-map.json"
    continuation = {
        "schema_version": 1,
        "source_plan_path": source_plan_path,
        "source_plan_sha256": source_plan_sha,
        "entries": [entry],
    }
    continuation_sha = store.write(continuation_path, continuation)
    plan = {
        **source_plan,
        "name": name,
        "created_at_utc": now_utc(),
        "harness_sources": harness_sources(),
        "continuation_manifest_path": continuation_path,
        "continuation_manifest_sha256": continuation_sha,
        "continuation_source_plan_path": source_plan_path,
        "continuation_source_plan_sha256": source_plan_sha,
    }
    _validate_continuation_plan(store, plan)
    relative = f"campaigns/{name}/plan.json"
    store.write(relative, {"plan": plan, "plan_sha256": digest(plan)})
    return relative


def create_continuation_plan(
    store: PrivateStore, name: str, source_plan_path: str,
) -> str:
    label(name)
    source_plan = load_plan(store, source_plan_path, for_execution=False)
    source_plan_sha = digest(source_plan)
    entries = []
    for slot in source_plan["slots"]:
        suite = load_suite(store, source_plan["suite_files"][slot["suite"]])
        base = slot_path(source_plan, slot)
        for case in suite["cases"]:
            case_path = store.path(f"{base}/{case['id']}")
            record_path = case_path / "record.json"
            if record_path.is_file():
                entries.append(_captured_slot_entry(store, source_plan, slot, case["id"]))
            elif any((case_path / name).exists() for name in (
                "started.json", "submission-intent.json",
            )):
                raise EvaluationError(
                    "A started source case has no immutable record; refusing to resubmit it.",
                )
    if not entries:
        raise EvaluationError("No verified terminal captures are available to continue.")
    continuation_path = f"campaigns/{name}/continuation-map.json"
    continuation = {
        "schema_version": 1,
        "mode": "captured-slots",
        "source_plan_path": source_plan_path,
        "source_plan_sha256": source_plan_sha,
        "entries": entries,
    }
    continuation_sha = store.write(continuation_path, continuation)
    plan = {
        **source_plan,
        "name": name,
        "created_at_utc": now_utc(),
        "harness_sources": harness_sources(),
        "continuation_manifest_path": continuation_path,
        "continuation_manifest_sha256": continuation_sha,
        "continuation_source_plan_path": source_plan_path,
        "continuation_source_plan_sha256": source_plan_sha,
    }
    _validate_continuation_plan(store, plan)
    relative = f"campaigns/{name}/plan.json"
    store.write(relative, {"plan": plan, "plan_sha256": digest(plan)})
    return relative


def _continuation_entries(
    store: PrivateStore, plan: dict[str, Any],
) -> dict[tuple[str, str, int, str], dict[str, Any]]:
    manifest_path = plan.get("continuation_manifest_path")
    if manifest_path is None:
        if any(key in plan for key in (
            "continuation_manifest_sha256", "continuation_source_plan_path",
            "continuation_source_plan_sha256",
        )):
            raise EvaluationError("Continuation plan metadata is incomplete.")
        return {}
    if (not isinstance(manifest_path, str) or not manifest_path
            or not store.path(manifest_path).is_file()
            or file_digest(store.path(manifest_path))
            != plan.get("continuation_manifest_sha256")):
        raise EvaluationError("Continuation manifest hash mismatch.")
    manifest = store.read(manifest_path)
    source_path = plan.get("continuation_source_plan_path")
    if (not isinstance(manifest, dict)
            or not isinstance(source_path, str) or not source_path
            or manifest.get("schema_version") != 1
            or manifest.get("source_plan_path") != source_path
            or manifest.get("source_plan_sha256")
            != plan.get("continuation_source_plan_sha256")):
        raise EvaluationError("Continuation manifest is not bound to its source plan.")
    source_plan = load_plan(store, source_path, for_execution=False)
    if digest(source_plan) != plan.get("continuation_source_plan_sha256"):
        raise EvaluationError("Continuation source plan changed after registration.")
    if any(key not in source_plan or plan.get(key) != source_plan[key] for key in (
        "configurations", "suite_files", "suite_sha256", "repetitions",
        "per_configuration_repetitions", "slots", "selection_policy",
    )):
        raise EvaluationError("Recovery plan changed the original evaluation scope.")
    entries = manifest.get("entries")
    if not isinstance(entries, list) or not entries:
        raise EvaluationError("Continuation manifest must contain at least one carried slot.")
    result = {}
    mode = manifest.get("mode", "diagnostics-normalization")
    if mode not in {"diagnostics-normalization", "captured-slots"}:
        raise EvaluationError("Unknown continuation manifest type.")
    for entry in entries:
        if not isinstance(entry, dict):
            raise EvaluationError("Malformed continuation entry.")
        entry_mode = entry.get("mode", "diagnostics-normalization")
        if entry_mode != mode and not (
            mode == "captured-slots" and entry_mode == "captured-slot"
        ):
            raise EvaluationError("Continuation entry type differs from its manifest.")
        _validate_continuation_entry(store, source_plan, entry)
        slot = entry["slot"]
        key = (slot["configuration"], slot["suite"], slot["repeat"], entry["case_id"])
        if key in result:
            raise EvaluationError("A predeclared slot cannot be carried more than once.")
        if slot not in plan["slots"]:
            raise EvaluationError("Continuation slot is not present in the recovery plan.")
        result[key] = entry
    return result


def _validate_continuation_plan(store: PrivateStore, plan: dict[str, Any]) -> None:
    _continuation_entries(store, plan)


def load_plan(
    store: PrivateStore, relative: str, *, for_execution: bool = True,
) -> dict[str, Any]:
    frozen = store.read(relative)
    plan = frozen["plan"]
    if digest(plan) != frozen.get("plan_sha256"):
        raise EvaluationError("Campaign plan hash mismatch.")
    if for_execution and plan.get("harness_sources") != harness_sources():
        raise EvaluationError("Evaluation harness changed; pre-register a new campaign.")
    for kind, path in plan["suite_files"].items():
        if digest(load_suite(store, path)) != plan["suite_sha256"][kind]:
            raise EvaluationError("Campaign suite changed after pre-registration.")
    _validate_continuation_plan(store, plan)
    return plan


def slot_path(plan: dict[str, Any], slot: dict[str, Any]) -> str:
    return (
        f"campaigns/{label(plan['name'])}/{label(slot['configuration'])}/"
        f"{label(slot['suite'])}/repeat-{slot['repeat']:03}"
    )


def capture_case(
    store: PrivateStore, relative: str, case: dict[str, Any], client: Any,
    read_definition: Callable[[], dict[str, Any]], expected_definition: str,
    used_conversations: set[str], timeout: float, *,
    previous_record_path: str | Path | None = None,
    sleep: Callable[[float], None] = time.sleep,
    monotonic: Callable[[], float] = time.monotonic,
) -> dict[str, Any]:
    """One POST per turn; only an explicit verified predecessor reuses context."""
    relative = store.path(relative).relative_to(store.root).as_posix()
    store.write(f"{relative}/started.json", {"at_utc": now_utc(), "case_id": case["id"]})
    record: dict[str, Any] = {
        "schema_version": 1, "case_id": case["id"], "question": case["question"],
        "started_at_utc": now_utc(), "submission_count": 0, "fresh_conversation": False,
        "turn_index": 1, "record_path": f"{relative}/record.json",
        "status": "pre_submission_blocked", "artifacts": [],
    }

    def save(name: str, body: bytes) -> str:
        path = f"{relative}/{name}"
        sha = store.write_bytes(path, body)
        record["artifacts"].append({"path": path, "sha256": sha})
        return path

    try:
        before = read_definition()
        record["configuration_before_sha256"] = definition_digest(before)
        save("configuration-before.json", encode(before))
        if record["configuration_before_sha256"] != expected_definition:
            raise EvaluationError("Configuration drift before submission.")
        previous_responses: set[str] = set()
        if previous_record_path is None:
            conversation = client.new_conversation()
            save("conversation.body", conversation.body)
            if not 200 <= conversation.status < 300:
                raise EvaluationError("Fresh conversation creation failed.")
            native_conversation = json.loads(conversation.body)
            conversation_id = native_conversation.get("id")
            if (not isinstance(conversation_id, str) or not conversation_id
                    or conversation_id in used_conversations):
                raise EvaluationError("Fresh conversation ID is missing or reused.")
            used_conversations.add(conversation_id)
            record["fresh_conversation"] = True
        else:
            previous_path = store.path(previous_record_path)
            previous, previous_sha = _read_capture_record(store, previous_record_path)
            previous_responses = _verify_dialogue_record(store, previous)
            _verify_predecessor(store, previous, expected_definition, previous_path)
            conversation_id = previous["conversation_id"]
            if conversation_id not in used_conversations:
                raise EvaluationError("Predecessor conversation is not registered in this capture session.")
            record["turn_index"] = previous.get("turn_index", 1) + 1
            record["previous_record"] = {
                "path": previous_path.relative_to(store.root).as_posix(),
                "sha256": previous_sha, "response_id": previous["response"]["id"],
            }
        record["conversation_id"] = conversation_id
        # Intent is durable BEFORE the sole question POST. If interrupted,
        # the started slot is never reused, even when receipt is unknowable.
        intent = {
            "input": case["question"], "conversation": conversation_id, "at_utc": now_utc(),
            "record_path": record["record_path"], "turn_index": record["turn_index"],
            "fresh_conversation": record["fresh_conversation"],
        }
        if "previous_record" in record:
            intent["previous_record"] = record["previous_record"]
        intent_body = encode(intent)
        save("submission-intent.json", intent_body)
        if previous_record_path is not None:
            if file_digest(previous_path) != previous_sha:
                raise EvaluationError("Predecessor record changed before submission.")
            # Exclusive-create consumes this predecessor even if the next POST
            # is ambiguous or interrupted. Another slot cannot replay/fork it.
            claim = (previous_path.parent / "continuation-claim.json").relative_to(store.root).as_posix()
            try:
                claim_sha = store.write_bytes(claim, intent_body)
            except FileExistsError as exc:
                raise EvaluationError("Predecessor already has a continuation attempt; no replay.") from exc
            record["artifacts"].append({"path": claim, "sha256": claim_sha})
        record["submission_count"] = 1
        record["status"] = "submission_outcome_unknown"
        deadline = monotonic() + timeout
        reply = client.submit(case["question"], conversation_id)
        record["request_artifact"] = save("request.body", reply.request_body)
        response_id = None
        index = 0
        while True:
            artifact = save(f"response-{index:04}.body", reply.body)
            record["response_artifact"] = artifact
            record["last_http_status"] = reply.status
            if index == 0:
                outbound = json.loads(reply.request_body)
                if (outbound.get("input") != case["question"]
                        or outbound.get("conversation") != conversation_id
                        or set(outbound) - {"input", "conversation", "model", "stream"}):
                    raise EvaluationError("Wire request does not match the exact original question.")
            if not 200 <= reply.status < 300:
                record["status"] = "platform_error"
                raise EvaluationError("Native response HTTP error.")
            response = parse_native_body(reply.body)
            record["response"] = response
            native_id = response.get("id")
            if not isinstance(native_id, str) or not native_id:
                raise EvaluationError("Missing native response ID.")
            if native_id in previous_responses:
                raise EvaluationError("Native response ID was reused from a previous turn.")
            if response_id is not None and response_id != native_id:
                raise EvaluationError("Response identity changed while polling.")
            response_id = native_id
            native_context = response.get("conversation")
            if isinstance(native_context, dict):
                native_context = native_context.get("id")
            if native_context is not None and native_context != conversation_id:
                raise EvaluationError("Native response belongs to a different conversation.")
            if (previous_record_path is not None
                    and response.get("previous_response_id") not in (
                        None, record["previous_record"]["response_id"],
                    )):
                raise EvaluationError("Native response identifies a different predecessor.")
            if response.get("status") in TERMINAL:
                break
            if response.get("status") not in {"queued", "in_progress"}:
                raise EvaluationError("Unknown native response state.")
            if monotonic() >= deadline:
                record["status"] = "unfinished_timeout"
                raise EvaluationError("Native run remains unfinished.")
            sleep(min(2, max(0, deadline - monotonic())))
            # Only retrieval is retried; never repeat the question.
            for retry in range(3):
                try:
                    reply = client.retrieve(response_id)
                    if reply.status not in {429, 500, 502, 503, 504}:
                        break
                    save(f"poll-{index:04}-retry-{retry}.body", reply.body)
                except Exception:
                    if retry == 2:
                        raise
                if retry < 2:
                    if monotonic() >= deadline:
                        raise EvaluationError("Native polling deadline exceeded.")
                    sleep(min(2 ** retry, max(0, deadline - monotonic())))
            index += 1
        record["status"] = "completed" if response["status"] == "completed" else "platform_error"
        view, issues = native_view(response)
        record["native_structure_issues"] = issues
        record["native_final_texts"] = view["final_texts"]
        # A failed diagnostics read never triggers a second question.
        try:
            diagnostics = client.diagnostics(conversation_id, response_id)
        except NativeEvidenceError as exc:
            if not diagnostics_feature_unavailable(exc.native_body, exc.http_status):
                raise
            record["diagnostics_status"] = "feature_unavailable"
            save("diagnostics-unavailable.body", exc.native_body)
            save("diagnostics-unavailable.json", encode({
                "status": "feature_unavailable",
                "http_status": exc.http_status,
                "conversation_id": conversation_id,
                "response_id": response_id,
                "source_evidence": "Only the unchanged native response output may establish execution.",
            }))
        else:
            record["diagnostics_status"] = "available"
            save("diagnostics.json", encode(diagnostics))
        if (response["status"] in {"failed", "incomplete", "cancelled"}
                or "native_platform_content_block" in issues):
            # The failed native answer remains a failed question. Its complete
            # terminal/error evidence lets the batch continue to the other
            # original questions without resending this one.
            record["status"] = "native_failure_captured"
        elif issues:
            record["status"] = "evidence_incomplete"
    except Exception as exc:
        # Do not print exception text that can contain tokens, request URLs or
        # raw answers. Native error bodies (when available) stay private.
        record["error_type"] = type(exc).__name__
        if isinstance(exc, EvaluationError):
            record["failure_reason"] = str(exc)
        native_error = getattr(exc, "response", None)
        if native_error is not None and isinstance(getattr(native_error, "content", None), bytes):
            save("native-error.body", native_error.content)
        elif isinstance(getattr(exc, "native_body", None), bytes):
            save("native-error.body", exc.native_body)
        if record["status"] == "completed":
            record["status"] = "evidence_incomplete"
    finally:
        try:
            after = read_definition()
            record["configuration_after_sha256"] = definition_digest(after)
            save("configuration-after.json", encode(after))
            if record["configuration_after_sha256"] != record.get("configuration_before_sha256"):
                record["status"] = "configuration_changed"
        except Exception as exc:
            record["configuration_after_error_type"] = type(exc).__name__
            record["status"] = "configuration_unverified"
        record["finished_at_utc"] = now_utc()
        store.write(f"{relative}/record.json", record)
        store.write(f"{relative}/review.json", review_template(case, record))
    return record


def captured_terminal_outcome(record: dict[str, Any]) -> bool:
    """A terminal captured response can be reviewed even when native evidence is incomplete."""
    response = record.get("response")
    return (
        record.get("status") in {"completed", "native_failure_captured", "evidence_incomplete"}
        and record.get("submission_count") == 1
        and isinstance(record.get("response_artifact"), str)
        and isinstance(response, dict) and response.get("status") in TERMINAL
        and type(record.get("last_http_status")) is int
        and 200 <= record["last_http_status"] < 300
        and isinstance(record.get("configuration_before_sha256"), str)
        and record["configuration_before_sha256"]
        == record.get("configuration_after_sha256")
        and not record.get("configuration_after_error_type")
    )


def carry_forward_case(
    store: PrivateStore, relative: str, case: dict[str, Any],
    entry: dict[str, Any], plan_sha256: str, expected_definition: str,
) -> dict[str, Any]:
    """Derive a reviewable record without resubmitting its already captured question."""
    relative = store.path(relative).relative_to(store.root).as_posix()
    source_path = entry["source_record_path"]
    source_record, source_record_sha = _read_capture_record(store, source_path)
    if source_record_sha != entry["source_record_sha256"]:
        raise EvaluationError("Continuation source record changed before carry-forward.")
    verify_record(store, source_record)
    if (source_record.get("case_id") != case["id"]
            or source_record.get("question") != case["question"]
            or source_record.get("configuration_before_sha256") != expected_definition
            or source_record.get("configuration_after_sha256") != expected_definition
            or source_record.get("status") != "evidence_incomplete"):
        raise EvaluationError("Continuation source differs from the frozen case or configuration.")

    original_error = store.path(entry["source_native_error_artifact_path"]).read_bytes()
    diagnostics_body = store.path(entry["diagnostics_body_path"]).read_bytes()
    if (hashlib.sha256(original_error).hexdigest()
            != entry["source_native_error_artifact_sha256"]
            or hashlib.sha256(diagnostics_body).hexdigest()
            != entry["diagnostics_body_sha256"]
            or original_error != diagnostics_body
            or not diagnostics_feature_unavailable(
                diagnostics_body, entry["diagnostics_http_status"])):
        raise EvaluationError("Continuation diagnostics evidence changed before carry-forward.")

    store.write(f"{relative}/started.json", {
        "at_utc": now_utc(), "case_id": case["id"], "plan_sha256": plan_sha256,
        "capture_mode": "carried_forward", "source_record_path": source_path,
        "source_record_sha256": source_record_sha,
    })
    body_path = f"{relative}/diagnostics-unavailable.body"
    body_sha = store.write_bytes(body_path, original_error)
    receipt_path = f"{relative}/diagnostics-unavailable.json"
    receipt = {
        "status": "feature_unavailable",
        "http_status": entry["diagnostics_http_status"],
        "conversation_id": source_record["conversation_id"],
        "response_id": source_record["response"]["id"],
        "source_evidence": "Only the unchanged native response output may establish execution.",
        "source_record_path": source_path,
        "source_record_sha256": source_record_sha,
        "source_native_error_artifact_sha256": entry["source_native_error_artifact_sha256"],
        "diagnostics_readback_receipt_path": entry["diagnostics_receipt_path"],
        "diagnostics_readback_receipt_sha256": entry["diagnostics_receipt_sha256"],
    }
    receipt_sha = store.write(receipt_path, receipt)
    interpretation_path = f"{relative}/derived-interpretation.json"
    interpretation = {
        "schema_version": 1,
        "interpretation": (
            "The original single question submission and terminal response are preserved. "
            "The SDK raised HTTPStatusError only because its diagnostics GET returned the "
            "exact 403 optional-feature-disabled response. This adapter interpretation "
            "does not award any rubric condition or infer query execution."
        ),
        "source_record_path": source_path,
        "source_record_sha256": source_record_sha,
        "source_batch_path": entry["source_batch_path"],
        "source_batch_sha256": entry["source_batch_sha256"],
        "source_response_artifact_path": entry["source_response_artifact_path"],
        "source_response_artifact_sha256": entry["source_response_artifact_sha256"],
        "source_configuration_before_artifact_path":
            entry["source_configuration_before_artifact_path"],
        "source_configuration_before_artifact_sha256":
            entry["source_configuration_before_artifact_sha256"],
        "source_configuration_after_artifact_path":
            entry["source_configuration_after_artifact_path"],
        "source_configuration_after_artifact_sha256":
            entry["source_configuration_after_artifact_sha256"],
        "source_definition_sha256": entry["source_definition_sha256"],
        "source_native_error_artifact_path": entry["source_native_error_artifact_path"],
        "source_native_error_artifact_sha256": entry["source_native_error_artifact_sha256"],
        "diagnostics_receipt_path": entry["diagnostics_receipt_path"],
        "diagnostics_receipt_sha256": entry["diagnostics_receipt_sha256"],
        "diagnostics_http_status": entry["diagnostics_http_status"],
        "derived_diagnostics_body_path": body_path,
        "derived_diagnostics_body_sha256": body_sha,
        "derived_diagnostics_receipt_path": receipt_path,
        "derived_diagnostics_receipt_sha256": receipt_sha,
    }
    interpretation_sha = store.write(interpretation_path, interpretation)

    record = dict(source_record)
    record["source_capture_status"] = source_record["status"]
    record["source_error_type"] = source_record.get("error_type")
    record.pop("error_type", None)
    record["status"] = "completed"
    record["diagnostics_status"] = "feature_unavailable"
    record["derived_interpretation"] = {
        "path": interpretation_path,
        "sha256": interpretation_sha,
        "source_record_path": source_path,
        "source_record_sha256": source_record_sha,
    }
    record["artifacts"] = [
        *source_record["artifacts"],
        {"path": body_path, "sha256": body_sha},
        {"path": receipt_path, "sha256": receipt_sha},
        {"path": interpretation_path, "sha256": interpretation_sha},
    ]
    store.write(f"{relative}/record.json", record)
    store.write(f"{relative}/review.json", review_template(case, record))
    return record


def carry_forward_captured_case(
    store: PrivateStore, relative: str, case: dict[str, Any],
    entry: dict[str, Any], plan_sha256: str, expected_definition: str,
) -> dict[str, Any]:
    """Copy one verified terminal capture with its outcome and review unchanged."""
    relative = store.path(relative).relative_to(store.root).as_posix()
    source_path = entry["source_record_path"]
    source_record, source_record_sha = _read_capture_record(store, source_path)
    if (source_record_sha != entry["source_record_sha256"]
            or source_record.get("case_id") != case["id"]
            or source_record.get("question") != case["question"]
            or source_record.get("status") != entry["source_record_status"]
            or source_record.get("configuration_before_sha256") != expected_definition
            or source_record.get("configuration_after_sha256") != expected_definition
            or not captured_terminal_outcome(source_record)):
        raise EvaluationError("Captured continuation source changed or differs from its frozen case.")
    verify_record(store, source_record)
    review_body = store.path(entry["source_review_path"]).read_bytes()
    if hashlib.sha256(review_body).hexdigest() != entry["source_review_sha256"]:
        raise EvaluationError("Captured continuation review changed after registration.")
    review = json.loads(review_body)
    if not isinstance(review, dict) or review.get("case_id") != case["id"]:
        raise EvaluationError("Captured continuation review is invalid.")

    store.write(f"{relative}/started.json", {
        "at_utc": now_utc(), "case_id": case["id"], "plan_sha256": plan_sha256,
        "capture_mode": "carried_forward", "source_record_path": source_path,
        "source_record_sha256": source_record_sha,
    })
    interpretation_path = f"{relative}/continuation-interpretation.json"
    interpretation = {
        "schema_version": 1,
        "interpretation": (
            "This is an immutable carry-forward of an already submitted question. "
            "Its source record status, terminal response and review are preserved; "
            "carrying evidence does not award or alter a rubric judgment."
        ),
        "source_record_path": source_path,
        "source_record_sha256": source_record_sha,
        "source_record_status": source_record["status"],
        "source_batch_path": entry["source_batch_path"],
        "source_batch_sha256": entry["source_batch_sha256"],
        "source_response_artifact_path": entry["source_response_artifact_path"],
        "source_response_artifact_sha256": entry["source_response_artifact_sha256"],
        "source_configuration_before_artifact_path":
            entry["source_configuration_before_artifact_path"],
        "source_configuration_before_artifact_sha256":
            entry["source_configuration_before_artifact_sha256"],
        "source_configuration_after_artifact_path":
            entry["source_configuration_after_artifact_path"],
        "source_configuration_after_artifact_sha256":
            entry["source_configuration_after_artifact_sha256"],
        "source_definition_sha256": entry["source_definition_sha256"],
        "source_review_path": entry["source_review_path"],
        "source_review_sha256": entry["source_review_sha256"],
        "source_capture_mode": entry["source_capture_mode"],
        "source_new_question_submissions": entry["source_new_question_submissions"],
        "previous_derived_interpretation": source_record.get("derived_interpretation"),
        "previous_continuation_provenance": source_record.get("continuation_provenance"),
    }
    interpretation_sha = store.write(interpretation_path, interpretation)
    record = dict(source_record)
    record["continuation_provenance"] = {
        "path": interpretation_path,
        "sha256": interpretation_sha,
        "source_record_path": source_path,
        "source_record_sha256": source_record_sha,
        "source_plan_sha256": entry.get("source_plan_sha256"),
        "source_record_status": source_record["status"],
    }
    record["artifacts"] = [
        *source_record["artifacts"],
        {"path": interpretation_path, "sha256": interpretation_sha},
    ]
    store.write(f"{relative}/record.json", record)
    store.write_bytes(f"{relative}/review.json", review_body)
    return record


def capture_mcp_case(
    store: PrivateStore, relative: str, case: dict[str, Any], client: NativeMcpClient,
    read_definition: Callable[[], dict[str, Any]], expected_definition: str,
) -> dict[str, Any]:
    """Capture one new MCP session without inventing a backend conversation."""
    store.write(f"{relative}/started.json", {"at_utc": now_utc(), "case_id": case["id"]})
    record: dict[str, Any] = {
        "schema_version": 1, "protocol": MCP_PROTOCOL,
        "case_id": case["id"], "question": case["question"],
        "started_at_utc": now_utc(), "submission_count": 0,
        "fresh_mcp_session": False, "history_supplied": False,
        "observability": mcp_observability(), "status": "pre_submission_blocked",
        "artifacts": [], "rpc_question_id": QUESTION_RPC_ID,
        "mcp_endpoint": client.url,
    }

    def save(name: str, body: bytes) -> str:
        path = f"{relative}/{name}"
        sha = store.write_bytes(path, body)
        record["artifacts"].append({"path": path, "sha256": sha})
        if name == "question-request.body":
            record["request_artifact"] = path
        elif name == "question-reply.body":
            record["response_artifact"] = path
        return path

    def before_submit() -> None:
        if record["submission_count"]:
            raise EvaluationError("A second question submission is forbidden.")
        save("submission-intent.json", encode({"at_utc": now_utc(), "question": case["question"]}))
        record["submission_count"] = 1
        record["fresh_mcp_session"] = True
        record["status"] = "submission_outcome_unknown"

    try:
        before = read_definition()
        record["configuration_before_sha256"] = definition_digest(before)
        save("configuration-before.json", encode(before))
        if record["configuration_before_sha256"] != expected_definition:
            raise EvaluationError("Configuration drift before submission.")
        result = client.ask(case["question"], save, before_submit)
        record["response"] = result.response
        record["tool_name"] = result.tool_name
        record["question_argument"] = result.question_argument
        record["mcp_session_id"] = result.mcp_session_id
        view, issues = mcp_view(result.response)
        record["native_final_texts"] = view["final_texts"]
        record["native_structure_issues"] = issues
        record["status"] = "native_failure_captured" if issues else "completed"
    except Exception as exc:
        record["error_type"] = type(exc).__name__
        if isinstance(exc, EvaluationError):
            record["failure_reason"] = str(exc)
        if getattr(exc, "http_status", None) is not None:
            record["last_http_status"] = exc.http_status
            if record["submission_count"] and record.get("response_artifact"):
                record["status"] = "native_failure_captured"
    finally:
        try:
            after = read_definition()
            record["configuration_after_sha256"] = definition_digest(after)
            save("configuration-after.json", encode(after))
            if record["configuration_after_sha256"] != record.get("configuration_before_sha256"):
                record["status"] = "configuration_changed"
        except Exception as exc:
            record["configuration_after_error_type"] = type(exc).__name__
            record["status"] = "configuration_unverified"
        record["finished_at_utc"] = now_utc()
        store.write(f"{relative}/record.json", record)
        store.write(f"{relative}/review.json", review_template(case, record))
    return record


def _verify_record_evidence(
    store: PrivateStore, record: dict[str, Any], *, completed_evidence: bool = False,
) -> None:
    is_mcp = record.get("protocol") == MCP_PROTOCOL
    artifacts = record.get("artifacts", [])
    paths = [entry["path"] for entry in artifacts]
    if len(paths) != len(set(paths)):
        raise EvaluationError("Duplicate raw artifact path.")
    for artifact in artifacts:
        if file_digest(store.path(artifact["path"])) != artifact["sha256"]:
            raise EvaluationError("Raw native artifact hash mismatch.")
    if record.get("response_artifact"):
        if record["response_artifact"] not in paths:
            raise EvaluationError("Native response body not bound to artifact manifest.")
        body = store.path(record["response_artifact"]).read_bytes()
        response = parse_rpc(body, QUESTION_RPC_ID) if is_mcp else parse_native_body(body)
        if response != record.get("response"):
            raise EvaluationError("Parsed native response was edited after capture.")
    if record.get("status") == "completed" or completed_evidence:
        request_path = record.get("request_artifact")
        if request_path not in paths:
            raise EvaluationError("Wire request evidence is missing.")
        request = store.read(request_path)
        if is_mcp:
            by_name = {Path(p).name: p for p in paths}
            if len(by_name) != len(paths):
                raise EvaluationError("Duplicate MCP artifact name.")
            for phase in ("initialize", "initialized", "tools-list", "question"):
                required = [f"{phase}-request.body", f"{phase}-reply.body", f"{phase}-http.json"]
                if any(name not in by_name for name in required):
                    raise EvaluationError("MCP handshake/request/reply evidence is incomplete.")
                meta = store.read(by_name[f"{phase}-http.json"])
                accepted = {200, 202, 204} if phase == "initialized" else {200}
                if (meta.get("status") not in accepted or meta.get("method") != "POST"
                        or meta.get("url") != record.get("mcp_endpoint")):
                    raise EvaluationError("Native MCP HTTP evidence disagrees with its target/status.")
            initialize = store.read(by_name["initialize-request.body"])
            if initialize.get("method") != "initialize" or initialize.get("id") != 1:
                raise EvaluationError("Fresh MCP initialization request is missing.")
            initial = parse_rpc(store.path(by_name["initialize-reply.body"]).read_bytes(), 1)
            if "error" in initial or "protocolVersion" not in initial.get("result", {}):
                raise EvaluationError("Fresh MCP initialization did not complete.")
            notification = store.read(by_name["initialized-request.body"])
            if notification != {"jsonrpc": "2.0", "method": "notifications/initialized"}:
                raise EvaluationError("Native MCP initialization notification changed.")
            discovery = [p for p in paths if p.endswith("/tools-list-reply.body")]
            if len(discovery) != 1:
                raise EvaluationError("Native tool/schema discovery evidence missing.")
            tool, argument = discover_question_tool(parse_rpc(store.path(discovery[0]).read_bytes(), 2))
            expected = {
                "jsonrpc": "2.0", "id": QUESTION_RPC_ID, "method": "tools/call",
                "params": {"name": tool, "arguments": {argument: record["question"]}},
            }
            if (request != expected or record.get("tool_name") != tool
                    or record.get("question_argument") != argument):
                raise EvaluationError("Wire question does not match the discovered native tool/schema.")
            if (record.get("conversation_id") or record.get("backend_conversation_id")
                    or record.get("fresh_conversation") is True):
                raise EvaluationError("MCP does not expose a backend conversation to assert.")
        elif (request.get("input") != record["question"]
              or request.get("conversation") != record.get("conversation_id")
              or set(request) - {"input", "conversation", "model", "stream"}):
            raise EvaluationError("Wire question or conversation mismatch.")
        for stage in ("before", "after"):
            matches = [p for p in paths if p.endswith(f"/configuration-{stage}.json")]
            if (len(matches) != 1
                    or definition_digest(store.read(matches[0])) != record.get(f"configuration_{stage}_sha256")):
                raise EvaluationError("Configuration digest is not backed by its native definition.")
        if not is_mcp:
            diagnostics = [p for p in paths if p.endswith("/diagnostics.json")]
            if record.get("diagnostics_status") == "feature_unavailable":
                bodies = [p for p in paths if p.endswith("/diagnostics-unavailable.body")]
                receipts = [p for p in paths if p.endswith("/diagnostics-unavailable.json")]
                if diagnostics or len(bodies) != 1 or len(receipts) != 1:
                    raise EvaluationError("Diagnostic feature unavailability lacks unique native evidence.")
                receipt = store.read(receipts[0])
                if (receipt.get("status") != "feature_unavailable"
                        or receipt.get("conversation_id") != record.get("conversation_id")
                        or receipt.get("response_id") != record.get("response", {}).get("id")
                        or not diagnostics_feature_unavailable(
                            store.path(bodies[0]).read_bytes(), receipt.get("http_status"))):
                    raise EvaluationError("Diagnostic feature unavailability is not backed by its native error.")
            elif len(diagnostics) != 1:
                raise EvaluationError("Native diagnostics are missing.")


def _read_capture_record(
    store: PrivateStore, relative: str | Path,
) -> tuple[dict[str, Any], str]:
    body = store.path(relative).read_bytes()
    try:
        record = json.loads(body)
    except (ValueError, UnicodeError) as exc:
        raise EvaluationError("Predecessor record is not valid JSON.") from exc
    if not isinstance(record, dict):
        raise EvaluationError("Predecessor record must be an object.")
    return record, hashlib.sha256(body).hexdigest()


def _capture_artifact(store: PrivateStore, record: dict[str, Any], name: str) -> Path:
    matches = [a["path"] for a in record.get("artifacts", []) if Path(a["path"]).name == name]
    if len(matches) != 1:
        raise EvaluationError("Native turn evidence is missing or ambiguous.")
    return store.path(matches[0])


def _verify_turn_identity(
    store: PrivateStore, record: dict[str, Any], record_path: Path | None = None,
) -> None:
    conversation_id = record.get("conversation_id")
    turn = record.get("turn_index", 1)
    if (not isinstance(conversation_id, str) or not conversation_id
            or type(turn) is not int or turn < 1):
        raise EvaluationError("Native turn or conversation identity is invalid.")
    intent_path = _capture_artifact(store, record, "submission-intent.json")
    intent = read_json(intent_path)
    actual_path = intent_path.with_name("record.json")
    if record_path is not None and record_path != actual_path:
        raise EvaluationError("Predecessor path does not identify its captured turn.")
    if (intent.get("input") != record.get("question")
            or intent.get("conversation") != conversation_id):
        raise EvaluationError("Native submission intent does not match its turn.")
    previous = record.get("previous_record")
    if "turn_index" in record:
        if (intent.get("turn_index") != turn
                or intent.get("fresh_conversation") is not record.get("fresh_conversation")
                or intent.get("previous_record") != previous
                or intent.get("record_path") != record.get("record_path")
                or not isinstance(record.get("record_path"), str)
                or store.path(record["record_path"]) != actual_path):
            raise EvaluationError("Native turn identity differs from its durable submission intent.")
    elif any(key in intent for key in ("turn_index", "fresh_conversation", "previous_record", "record_path")):
        raise EvaluationError("Native turn metadata was removed from its record.")
    response = record.get("response", {})
    native_context = response.get("conversation")
    if isinstance(native_context, dict):
        native_context = native_context.get("id")
    if native_context is not None and native_context != conversation_id:
        raise EvaluationError("Native response belongs to a different conversation.")
    if previous is None:
        if turn != 1 or record.get("fresh_conversation") is not True:
            raise EvaluationError("A root turn must have a fresh native conversation.")
        conversation = read_json(_capture_artifact(store, record, "conversation.body"))
        if conversation.get("id") != conversation_id or response.get("previous_response_id"):
            raise EvaluationError("Root turn has a foreign or previously used native context.")
    else:
        if (turn <= 1 or record.get("fresh_conversation") is not False
                or not isinstance(previous, dict)
                or set(previous) != {"path", "sha256", "response_id"}
                or any(not isinstance(value, str) or not value for value in previous.values())):
            raise EvaluationError("Follow-up lacks an explicit predecessor identity.")
        if any(Path(a["path"]).name == "conversation.body" for a in record["artifacts"]):
            raise EvaluationError("A follow-up cannot claim a new native conversation receipt.")
        if response.get("previous_response_id") not in (None, previous["response_id"]):
            raise EvaluationError("Native response identifies a different predecessor.")
        previous_path = store.path(previous["path"])
        claim = _capture_artifact(store, record, "continuation-claim.json")
        if (claim != previous_path.with_name("continuation-claim.json")
                or claim.read_bytes() != intent_path.read_bytes()):
            raise EvaluationError("Follow-up is not bound to its exclusive predecessor claim.")


def _verify_predecessor(
    store: PrivateStore, record: dict[str, Any], expected_definition: str,
    record_path: Path,
) -> None:
    if (record.get("protocol") == MCP_PROTOCOL
            or record.get("status") not in {"completed", "evidence_incomplete"}
            or type(record.get("submission_count")) is not int
            or record["submission_count"] != 1):
        raise EvaluationError("Only a single completed native submission can be continued.")
    _verify_record_evidence(store, record, completed_evidence=True)
    _verify_turn_identity(store, record, record_path)
    response = record.get("response", {})
    if (not record.get("response_artifact")
            or response.get("status") != "completed"
            or not isinstance(response.get("id"), str) or not response["id"]
            or type(record.get("last_http_status")) is not int
            or not 200 <= record["last_http_status"] < 300
            or record.get("configuration_before_sha256") != expected_definition
            or record.get("configuration_after_sha256") != expected_definition):
        raise EvaluationError("Predecessor is not terminal completed under the frozen configuration.")
    view, issues = native_view(response)
    # A terminal final answer can recover from an internal planning/tool error;
    # retain those evidence issues, but never waive a native failure or block.
    allowed = {"tool_error", "unfinished_tool_item"}
    if record.get("previous_record") is not None:
        allowed.add("native_previous_response_context")
    if (set(issues) - allowed
            or record.get("native_structure_issues") != issues
            or record.get("native_final_texts") != view["final_texts"]):
        raise EvaluationError("Predecessor contains an unrecovered native failure or incomplete evidence.")


def _verify_dialogue_record(store: PrivateStore, record: dict[str, Any]) -> set[str]:
    """Iteratively verify links; never recurse through untrusted record paths."""
    _verify_record_evidence(store, record)
    if record.get("protocol") == MCP_PROTOCOL:
        return set()
    current = record
    seen_paths: set[Path] = set()
    seen_responses: set[str] = set()
    while True:
        if current.get("submission_count") == 1:
            _verify_turn_identity(store, current)
        if current.get("record_path"):
            current_path = store.path(current["record_path"])
            if current_path in seen_paths:
                raise EvaluationError("Native dialogue chain contains a cycle.")
            seen_paths.add(current_path)
        response_id = current.get("response", {}).get("id")
        if response_id:
            if response_id in seen_responses:
                raise EvaluationError("Native response identity was reused across turns.")
            seen_responses.add(response_id)
        previous = current.get("previous_record")
        if previous is None:
            return seen_responses
        if (not isinstance(previous, dict) or set(previous) != {"path", "sha256", "response_id"}
                or any(not isinstance(value, str) or not value for value in previous.values())):
            raise EvaluationError("Follow-up lacks an explicit predecessor identity.")
        previous_path = store.path(previous["path"])
        if previous_path in seen_paths:
            raise EvaluationError("Native dialogue chain contains a cycle.")
        predecessor, sha = _read_capture_record(store, previous["path"])
        if sha != previous["sha256"]:
            raise EvaluationError("Predecessor record hash mismatch.")
        _verify_predecessor(
            store, predecessor, current.get("configuration_before_sha256"), previous_path,
        )
        if (predecessor["response"]["id"] != previous["response_id"]
                or predecessor["conversation_id"] != current.get("conversation_id")
                or current.get("turn_index") != predecessor.get("turn_index", 1) + 1):
            raise EvaluationError("Native dialogue turn does not match its exact predecessor.")
        # Legacy roots lack record_path, but still get a path-based cycle guard.
        if "record_path" not in predecessor:
            seen_paths.add(previous_path)
        current = predecessor


def verify_record(store: PrivateStore, record: dict[str, Any]) -> None:
    """Verify native artifacts and every explicitly linked predecessor."""
    _verify_dialogue_record(store, record)


def verify_data_fingerprint(store: PrivateStore, configuration: dict[str, Any]) -> None:
    try:
        actual = file_digest(store.path(configuration["data_fingerprint_file"]))
    except OSError as exc:
        raise EvaluationError("Frozen deployment/data evidence is unavailable.") from exc
    if actual != configuration["data_fingerprint_sha256"]:
        raise EvaluationError("Deployment/data evidence changed after plan freeze.")


def run_batch(
    store: PrivateStore, plan: dict[str, Any], slot: dict[str, Any],
    credential_name: str, timeout: float,
) -> dict[str, Any]:
    if slot not in plan["slots"]:
        raise EvaluationError("Batch was not predeclared.")
    configuration = next(c for c in plan["configurations"] if c["label"] == slot["configuration"])
    verify_data_fingerprint(store, configuration)
    suite = load_suite(store, plan["suite_files"][slot["suite"]])
    # The original prompts/rubric remain bound to the current shared source.
    if digest(original_suite(REPO)) != plan["suite_sha256"]["original"]:
        raise EvaluationError("Original guide/data changed; freeze and pre-register a new campaign.")
    if slot["suite"] == "regression" and digest(regression_suite(REPO)) != plan["suite_sha256"]["regression"]:
        raise EvaluationError("Regression suite sources changed; freeze and pre-register a new campaign.")
    continuation_by_case = _continuation_entries(store, plan)
    relative = slot_path(plan, slot)
    store.write(f"{relative}/started.json", {
        "plan_sha256": digest(plan), "slot": slot, "at_utc": now_utc(),
    })
    credentials = reader = client = None
    report: dict[str, Any] = {"slot": slot, "case_statuses": [], "status": "pre_submission_blocked"}
    try:
        credentials = credential_for(credential_name)
        reader = DefinitionReader(credentials)
        initial = reader.read(configuration)
        baseline_file = f"campaigns/{plan['name']}/{configuration['label']}/baseline-definition.json"
        if store.path(baseline_file).exists():
            baseline = store.read(baseline_file)
            if definition_digest(initial) != definition_digest(baseline):
                raise EvaluationError("Agent changed between repetitions.")
        else:
            store.write(baseline_file, initial)
        baseline_hash = definition_digest(initial)
        report["transport"] = configuration.get("transport", "sdk")
        if report["transport"] == "mcp":
            if configuration.get("native_protocol_contract") != MCP_CONTRACT:
                raise EvaluationError("MCP contract changed since plan freeze.")
            client = NativeMcpClient(configuration, credentials, timeout)
            report["native_protocol_contract"] = MCP_CONTRACT
            report["observability"] = mcp_observability()
        elif report["transport"] == "responses-http":
            if configuration.get("native_protocol_contract") != PROTOCOL_VERSION:
                raise EvaluationError("Native protocol changed since plan freeze.")
            client = ResponsesHttpClient(configuration, credentials, min(timeout, 120))
            report["native_protocol_contract"] = PROTOCOL_VERSION
            report["requests_version"] = importlib.metadata.version("requests")
        else:
            client = NativeClient(configuration, credentials, min(timeout, 120))
            report["sdk_version"] = importlib.metadata.version("fabric-data-agent-sdk")
        report["configuration_sha256"] = baseline_hash
        if slot["suite"] == "heldout":
            exposed_file = f"heldout-exposure/{plan['suite_sha256']['heldout']}.json"
            report["heldout_exposure"] = (
                "previously_exposed_regression" if store.path(exposed_file).exists()
                else "first_exposure"
            )
            if not store.path(exposed_file).exists():
                store.write(exposed_file, {"at_utc": now_utc(), "plan_sha256": digest(plan), "slot": slot})
        used = set()
        for case in suite["cases"]:
            continuation = continuation_by_case.get((
                slot["configuration"], slot["suite"], slot["repeat"], case["id"],
            ))
            if continuation is not None:
                if continuation.get("mode") == "captured-slot":
                    record = carry_forward_captured_case(
                        store, f"{relative}/{case['id']}", case,
                        continuation, digest(plan), baseline_hash,
                    )
                else:
                    record = carry_forward_case(
                        store, f"{relative}/{case['id']}", case,
                        continuation, digest(plan), baseline_hash,
                    )
                capture_mode = "carried_forward"
                new_submissions = 0
            elif report["transport"] == "mcp":
                record = capture_mcp_case(
                    store, f"{relative}/{case['id']}", case, client,
                    lambda: reader.read(configuration), baseline_hash,
                )
                capture_mode = "fresh_submission"
                new_submissions = record.get("submission_count", 0)
            else:
                record = capture_case(
                    store, f"{relative}/{case['id']}", case, client,
                    lambda: reader.read(configuration), baseline_hash, used, timeout,
                )
                capture_mode = "fresh_submission"
                new_submissions = record.get("submission_count", 0)
            report["case_statuses"].append({
                "case_id": case["id"], "status": record["status"],
                "capture_mode": capture_mode,
                "new_question_submissions": new_submissions,
            })
            has_terminal_capture = (
                captured_terminal_outcome(record)
                if report["transport"] != "mcp"
                else record["status"] in {"completed", "native_failure_captured"}
            )
            if not has_terminal_capture:
                report["status"] = "stopped_fail_closed"
                break
        else:
            report["status"] = "captured_pending_human_review"
    except Exception as exc:
        report["error_type"] = type(exc).__name__
        if isinstance(exc, EvaluationError):
            report["failure_reason"] = str(exc)
    finally:
        for resource in (client, reader, credentials):
            if resource is not None:
                try:
                    resource.close()
                except Exception as exc:
                    report["close_error_type"] = type(exc).__name__
                    report["status"] = "resource_cleanup_unverified"
        report["finished_at_utc"] = now_utc()
        store.write(f"{relative}/batch.json", report)
    return report


def report_campaign(store: PrivateStore, plan: dict[str, Any]) -> dict[str, Any]:
    batches, seen_responses, seen_conversations = [], set(), set()
    continuation_by_case = _continuation_entries(store, plan)
    for slot in plan["slots"]:
        path = slot_path(plan, slot)
        config = next(c for c in plan["configurations"] if c["label"] == slot["configuration"])
        suite = load_suite(store, plan["suite_files"][slot["suite"]])
        batch = store.read(f"{path}/batch.json") if store.path(f"{path}/batch.json").exists() else {}
        started = store.read(f"{path}/started.json") if store.path(f"{path}/started.json").exists() else {}
        batch_errors = []
        try:
            verify_data_fingerprint(store, config)
        except EvaluationError:
            batch_errors.append("batch_data_fingerprint_missing_or_changed")
        if started.get("plan_sha256") != digest(plan) or started.get("slot") != slot:
            batch_errors.append("batch_not_bound_to_preregistered_plan")
        statuses = batch.get("case_statuses", [])
        if (batch.get("status") != "captured_pending_human_review"
                or batch.get("slot") != slot
                or [c.get("case_id") for c in statuses] != [c["id"] for c in suite["cases"]]
                or any(c.get("status") not in {"completed", "native_failure_captured"} for c in statuses)):
            batch_errors.append("batch_unfinished_or_incomplete")
        baseline_file = f"campaigns/{plan['name']}/{slot['configuration']}/baseline-definition.json"
        baseline_sha = None
        if store.path(baseline_file).exists():
            baseline_sha = definition_digest(store.read(baseline_file))
        if not baseline_sha or baseline_sha != batch.get("configuration_sha256"):
            batch_errors.append("batch_configuration_baseline_missing_or_changed")
        results = []
        for case in suite["cases"]:
            case_path = f"{path}/{case['id']}"
            record = store.read(f"{case_path}/record.json") if store.path(f"{case_path}/record.json").exists() else None
            review = store.read(f"{case_path}/review.json") if store.path(f"{case_path}/review.json").exists() else None
            case_status = next(
                (item for item in statuses if item.get("case_id") == case["id"]), {},
            )
            continuation = continuation_by_case.get((
                slot["configuration"], slot["suite"], slot["repeat"], case["id"],
            ))
            # Preserve valid per-question measurements from a partial batch,
            # but never call the unfinished batch accepted.
            integrity = [e for e in batch_errors if e != "batch_unfinished_or_incomplete"]
            if record is not None:
                try:
                    verify_record(store, record)
                    if record.get("protocol") == MCP_PROTOCOL:
                        expected_endpoint = (
                            f"https://api.fabric.microsoft.com/v1/mcp/workspaces/{config['workspace_id']}"
                            f"/dataagents/{config['data_agent_id']}/agent"
                        )
                        if config.get("transport") != "mcp" or record.get("mcp_endpoint") != expected_endpoint:
                            raise EvaluationError("Native MCP evidence differs from the frozen target/transport.")
                    if record.get("configuration_before_sha256") != baseline_sha:
                        raise EvaluationError("Question configuration differs from its campaign baseline.")
                    # An MCP RPC id (often 3) is not a backend response id.
                    backend_keys = () if record.get("protocol") == MCP_PROTOCOL else (
                        (record.get("response", {}).get("id"), seen_responses),
                        (record.get("conversation_id"), seen_conversations),
                    )
                    for key, collection in backend_keys:
                        if key:
                            if key in collection:
                                raise EvaluationError("Native conversation/response reused across questions or repetitions.")
                            collection.add(key)
                    if continuation is not None:
                        if continuation.get("mode") == "captured-slot":
                            provenance = record.get("continuation_provenance", {})
                            carried_review = store.path(
                                f"{path}/{case['id']}/review.json",
                            ).read_bytes()
                            if (not isinstance(provenance, dict)
                                    or provenance.get("source_record_path")
                                    != continuation["source_record_path"]
                                    or provenance.get("source_record_sha256")
                                    != continuation["source_record_sha256"]
                                    or provenance.get("source_record_status")
                                    != continuation["source_record_status"]
                                    or record.get("status")
                                    != continuation["source_record_status"]
                                    or hashlib.sha256(carried_review).hexdigest()
                                    != continuation["source_review_sha256"]
                                    or case_status.get("capture_mode") != "carried_forward"
                                    or case_status.get("new_question_submissions") != 0):
                                raise EvaluationError(
                                    "Carried case differs from its immutable source capture or review.",
                                )
                        else:
                            derived = record.get("derived_interpretation", {})
                            if (not isinstance(derived, dict)
                                    or record.get("source_capture_status") != "evidence_incomplete"
                                    or record.get("source_error_type") != "HTTPStatusError"
                                    or derived.get("source_record_path")
                                    != continuation["source_record_path"]
                                    or derived.get("source_record_sha256")
                                    != continuation["source_record_sha256"]
                                    or case_status.get("capture_mode") != "carried_forward"
                                    or case_status.get("new_question_submissions") != 0):
                                raise EvaluationError(
                                    "Carried case lacks its explicit no-resubmission derivation.",
                                )
                    elif case_status.get("capture_mode") == "carried_forward":
                        raise EvaluationError("An undeclared case was marked as carried forward.")
                except (EvaluationError, OSError) as exc:
                    integrity.append(type(exc).__name__ + ": evidence_integrity_failed")
            result = grade_case(case, record, review)
            result["capture_provenance"] = (
                "carried_forward_unchanged_capture"
                if continuation is not None
                and continuation.get("mode") == "captured-slot"
                else "carried_forward_diagnostics_normalization"
                if continuation is not None
                else "fresh_submission_or_missing_capture"
            )
            result["new_question_submissions"] = case_status.get("new_question_submissions", 0)
            if integrity:
                result.update(question_pass=False, **{"pass": 0, "fail": len(case["conditions"]), "na": 0})
                result["gate_errors"] += integrity
            results.append(result)
        summary = summarize(results)
        batches.append({
            **slot, "capture_status": batch.get("status", "not_run_or_interrupted"),
            "heldout_exposure": batch.get("heldout_exposure"),
            "batch_gate_errors": batch_errors,
            "summary": summary, "cases": results,
            "batch_pass": summary["all_questions_pass"] and not batch_errors,
            "observability": mcp_observability() if config.get("transport") == "mcp" else batch.get("observability"),
        })
    groups = []
    for config in plan["configurations"]:
        for suite in plan["suite_files"]:
            matching = [b for b in batches if b["configuration"] == config["label"] and b["suite"] == suite]
            best = max(matching, key=lambda b: (
                b["summary"]["question_pass"], b["summary"]["condition_pass"]
            ))
            groups.append({
                "configuration": config["label"], "suite": suite, "planned_runs": len(matching),
                "fully_passing_runs": sum(b["batch_pass"] for b in matching),
                "strict_question_pass": sum(
                    b["summary"]["question_pass"] for b in matching
                ),
                "all_repeats": summarize([c for b in matching for c in b["cases"]]),
                "best_single_run_only_not_repeatability": {
                    "repeat": best["repeat"], **best["summary"],
                },
                "observability_blocked_questions": sum(
                    bool(c.get("observability_blockers")) for b in matching for c in b["cases"]
                ),
                "condition_judgments_are_not_strict_acceptance": True,
            })
    return {
        "schema_version": 1, "plan_sha256": digest(plan), "at_utc": now_utc(),
        "selection_policy": plan["selection_policy"], "groups": groups, "batches": batches,
        "acceptance": bool(batches) and all(b["batch_pass"] for b in batches),
        "harness_sources_match_current": plan.get("harness_sources") == harness_sources(),
        "score_interpretation": (
            "Strict acceptance and reviewed condition evidence are separate. "
            "Zero strict passes caused by unobservable execution are not 0% factual accuracy."
        ),
        "limitations": [
            "Human condition grading is authoritative; UNCLEAR is FAIL.",
            "Definition stability and deployment/data-fixture verification are separate from answer correctness.",
            "No selected-best or best-per-question result establishes repeatability.",
            "An exposed held-out suite is regression material for subsequent improvement.",
            "Finite evaluation is not a guarantee for all future questions.",
            "MCP is answer-only. Zero strict question passes caused by unobservable execution are not 0% factual accuracy.",
            "MCP condition PASS refers only to reviewed, provable answer content; native execution conditions remain FAIL.",
            "A question whose native answer is the platform content block stays FAIL in every strict denominator; "
            "platform_blocked_* and observable_condition_applicable are a diagnostic breakdown, never acceptance.",
        ],
        "continuation": (
            {
            "source_plan_sha256": plan["continuation_source_plan_sha256"],
            "carried_question_slots": len(continuation_by_case),
            "new_question_submissions": sum(
                item.get("new_question_submissions", 0)
                for batch in batches for item in batch["cases"]
            ),
            "scope_preserved": True,
            }
            if continuation_by_case else None
        ),
    }


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    root.add_argument("--private-root", type=Path, default=os.environ.get("EVALUATION_PRIVATE_ROOT"))
    commands = root.add_subparsers(dest="command", required=True)
    freeze = commands.add_parser("freeze", help="Offline: extract unchanged guide rubric into private storage.")
    freeze.add_argument("--original-out", default="suites/original.json")
    freeze.add_argument("--held-out-input", help="Private JSON specification, not an agent instruction.")
    freeze.add_argument("--held-out-out", default="suites/heldout.json")
    freeze.add_argument("--regression", action="store_true",
                        help="Also freeze the public extended regression suite rebuilt from sources.")
    freeze.add_argument("--regression-out", default="suites/regression.json")
    plan = commands.add_parser("plan", help="Offline: freeze all configurations, suites and repetitions.")
    plan.add_argument("--name", required=True)
    plan.add_argument("--deployment", required=True, help="Private relative path to ready deployment JSON.")
    plan.add_argument("--original-suite", default="suites/original.json")
    plan.add_argument("--held-out-suite", default="suites/heldout.json")
    plan.add_argument(
        "--without-heldout", action="store_true",
        help="Plan original plus regression only; do not relabel regression as held-out.",
    )
    plan.add_argument("--regression-suite", help="Frozen regression suite; omit to plan without it.")
    plan.add_argument("--repeats", type=int, default=3)
    plan.add_argument("--held-out-repeats", type=int, default=1)
    plan.add_argument("--regression-repeats", type=int, default=1)
    plan.add_argument("--transport", choices=["mcp", "sdk", "responses-http"],
                      help="Freeze this transport for all configurations; no run-time override.")
    recovery = commands.add_parser(
        "recover-plan",
        help="Pre-register an unchanged evaluation with a hash-bound prior capture carried once.",
    )
    recovery.add_argument("--name", required=True)
    recovery.add_argument("--source-plan", required=True)
    recovery.add_argument("--configuration", required=True)
    recovery.add_argument("--suite", choices=["original", "heldout", "regression"], required=True)
    recovery.add_argument("--repeat", type=int, required=True)
    recovery.add_argument("--case-id", required=True)
    recovery.add_argument("--diagnostics-receipt", required=True)
    continuation_plan = commands.add_parser(
        "continue-plan",
        help="Pre-register remaining cases while carrying all verified terminal captures once.",
    )
    continuation_plan.add_argument("--name", required=True)
    continuation_plan.add_argument("--source-plan", required=True)
    run = commands.add_parser("run", help="ONLINE: submit one fresh complete batch, once only.")
    run.add_argument("--plan", required=True)
    run.add_argument("--configuration", required=True)
    run.add_argument("--suite", choices=["original", "heldout", "regression"], required=True)
    run.add_argument("--repeat", type=int, required=True)
    run.add_argument("--credential", choices=["azure-cli", "default"], default="azure-cli")
    run.add_argument("--timeout", type=float, default=600)
    run.add_argument("--allow-submit-native-questions", action="store_true")
    report = commands.add_parser("report", help="Offline: score every predeclared slot, including missing ones.")
    report.add_argument("--plan", required=True)
    report.add_argument("--out", required=True, help="New private output path; never overwrites.")
    doctor = commands.add_parser("doctor", help="Offline: verify dependency imports without creating a client.")
    doctor.add_argument("--transport", choices=["mcp", "sdk", "responses-http"], default="mcp")
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "doctor":
            from azure.identity import AzureCliCredential, DefaultAzureCredential
            result = {
                "transport": args.transport,
                "authentication": [AzureCliCredential.__name__, DefaultAzureCredential.__name__],
                "network_calls": 0,
            }
            if args.transport == "sdk":
                from fabric.dataagent.client import FabricOpenAIResponses
                result.update(
                    sdk_version=importlib.metadata.version("fabric-data-agent-sdk"),
                    api_type=FabricOpenAIResponses.api_type,
                )
            else:
                import requests
                result.update(requests_version=requests.__version__)
                if args.transport == "mcp":
                    result.update(native_protocol_contract=MCP_CONTRACT, observability=mcp_observability())
                else:
                    result.update(native_protocol_contract=PROTOCOL_VERSION)
            print(json.dumps(result))
            return 0
        if args.private_root is None:
            raise EvaluationError("--private-root or EVALUATION_PRIVATE_ROOT is required.")
        store = PrivateStore(Path(args.private_root))
        if args.command == "freeze":
            suite = original_suite(REPO)
            freeze_suite(store, args.original_out, suite)
            if args.held_out_input:
                freeze_suite(store, args.held_out_out, store.read(args.held_out_input))
            if args.regression:
                regression = regression_suite(REPO)
                freeze_suite(store, args.regression_out, regression)
            print("Frozen original: 10 questions / 84 conditions"
                  + (f"; regression: {len(regression['cases'])} questions / "
                     f"{sum(len(c['conditions']) for c in regression['cases'])} conditions" if args.regression else "")
                  + ". No questions submitted.")
        elif args.command == "plan":
            if args.without_heldout and not args.regression_suite:
                raise EvaluationError("--without-heldout requires --regression-suite.")
            path = create_plan(
                store, args.name, store.read(args.deployment), args.original_suite,
                None if args.without_heldout else args.held_out_suite,
                args.repeats, args.held_out_repeats,
                transport=args.transport, regression_file=args.regression_suite,
                regression_repeats=args.regression_repeats,
            )
            print(f"Pre-registered {path}. No questions submitted.")
        elif args.command == "recover-plan":
            path = create_recovery_plan(
                store, args.name, args.source_plan, args.configuration,
                args.suite, args.repeat, args.case_id, args.diagnostics_receipt,
            )
            plan = load_plan(store, path, for_execution=False)
            continuation_count = len(_continuation_entries(store, plan))
            print(
                f"Pre-registered {path} with {continuation_count} hash-bound carried slot(s). "
                "The source capture is unchanged; no questions submitted."
            )
        elif args.command == "continue-plan":
            path = create_continuation_plan(store, args.name, args.source_plan)
            plan = load_plan(store, path, for_execution=False)
            continuation_count = len(_continuation_entries(store, plan))
            print(
                f"Pre-registered {path} with {continuation_count} verified captured slot(s) "
                f"carried once across {len(plan['slots'])} unchanged evaluation slots. "
                "The source captures are unchanged; no questions submitted."
            )
        elif args.command == "run":
            if not args.allow_submit_native_questions:
                raise EvaluationError("No question submitted: explicit --allow-submit-native-questions required.")
            if not 1 <= args.timeout <= 3600:
                raise EvaluationError("Timeout must be between 1 and 3600 seconds.")
            plan = load_plan(store, args.plan)
            batch = run_batch(store, plan, {
                "configuration": args.configuration, "suite": args.suite, "repeat": args.repeat,
            }, args.credential, args.timeout)
            print(json.dumps({
                "status": batch["status"], "captured_cases": len(batch["case_statuses"]),
                "new_question_submissions": sum(
                    item.get("new_question_submissions", 0)
                    for item in batch["case_statuses"]
                ),
                "observability": batch.get("observability"), "quality_acceptance": "not established by capture",
            }))
            return 0 if batch["status"] == "captured_pending_human_review" else 2
        elif args.command == "report":
            report = report_campaign(store, load_plan(store, args.plan, for_execution=False))
            store.write(args.out, report)
            # No raw answers, IDs, keys, exception messages or instructions to stdout.
            print(json.dumps({
                "acceptance": report["acceptance"], "groups": report["groups"],
                "score_interpretation": report["score_interpretation"],
            }))
            return 0 if report["acceptance"] else 2
        return 0
    except (EvaluationError, FileExistsError, FileNotFoundError, ImportError, KeyError, ValueError) as exc:
        print(f"Stopped ({type(exc).__name__}); no automatic resubmission.", file=sys.stderr)
        if isinstance(exc, EvaluationError):
            print(str(exc), file=sys.stderr)
        elif isinstance(exc, ImportError) and getattr(exc, "name", None):
            print(f"Missing dependency module: {exc.name}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
