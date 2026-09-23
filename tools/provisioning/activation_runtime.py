"""Explicit Activator lifecycle, complete-file upload and native delivery gates.

Definition import and Running metadata are not proof of first-time execution.
All evidence belongs outside Git. No function here manually runs a Pipeline.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
import time
from typing import Any, Callable, Mapping, Sequence
from urllib.parse import urlsplit, urlunsplit
from uuid import UUID

DATA_AGENT_TOOLS = Path(__file__).resolve().parents[1] / "data-agent"
if str(DATA_AGENT_TOOLS) not in sys.path:
    sys.path.insert(0, str(DATA_AGENT_TOOLS))
from native_evaluation import EvaluationError, PrivateStore, encode
from native_mcp import parse_rpc


CONTRACT = "furusato-activation/v1"
FABRIC_SCOPE = "https://api.fabric.microsoft.com/.default"
STORAGE_SCOPE = "https://storage.azure.com/.default"
FILE_CREATED = "Microsoft.Fabric.OneLake.FileCreated"
MAX_REPLY_BYTES = 4 * 1024 * 1024
MAX_FILE_BYTES = 8 * 1024 * 1024
LIFECYCLE_TOOLS = {
    "list_rules": "listRulesParams",
    "start_rule": "startRuleParams",
    "stop_rule": "stopRuleParams",
    "get_activations_for_rule": "getActivationsParams",
}


class ActivationError(EvaluationError):
    """An activation, scope, upload or native evidence gate failed."""


class AmbiguousActivationError(ActivationError):
    """A submitted write has no unambiguous receipt; inspect before recovery."""


def guid(value: str) -> str:
    try:
        return str(UUID(value))
    except (ValueError, TypeError, AttributeError) as exc:
        raise ActivationError("An explicit valid resource GUID is required.") from exc


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def tool_result(reply: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(reply, dict) or reply.get("error"):
        raise ActivationError("Native MCP RPC failed; inspect the private reply.")
    result = reply.get("result")
    if not isinstance(result, dict) or result.get("isError", False) is not False:
        raise ActivationError("Native MCP tool failed; unavailable history is not zero successful activations.")
    return result


def structured_result(result: Mapping[str, Any]) -> dict[str, Any]:
    structured = result.get("structuredContent")
    if isinstance(structured, dict):
        return structured
    texts = [
        part["text"] for part in result.get("content", [])
        if isinstance(part, dict) and part.get("type") == "text" and isinstance(part.get("text"), str)
    ]
    try:
        value = json.loads(texts[0]) if len(texts) == 1 else None
    except ValueError as exc:
        raise ActivationError("Native tool text is not a structured result.") from exc
    if not isinstance(value, dict):
        raise ActivationError("Expected one structured native tool result.")
    return value


class ActivatorLifecycle:
    """One scoped MCP connection; journal writes before sending, never retry them."""

    def __init__(
        self, workspace_id: str, activator_id: str, token_provider: Callable[[], str],
        evidence_root: Path, *, session: Any | None = None,
        sleeper: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
        timeout_seconds: int = 60,
    ):
        self.workspace_id, self.activator_id = guid(workspace_id), guid(activator_id)
        if not 10 <= timeout_seconds <= 180:
            raise ActivationError("MCP timeout must be between 10 and 180 seconds.")
        self.url = (
            f"https://api.fabric.microsoft.com/v1/mcp/workspaces/{self.workspace_id}"
            f"/reflexes/{self.activator_id}"
        )
        self.store = PrivateStore(evidence_root)
        self.token_provider, self.sleeper, self.clock = token_provider, sleeper, clock
        self.timeout = timeout_seconds
        if session is None:
            import requests
            from requests.adapters import HTTPAdapter
            session = requests.Session()
            session.mount("https://", HTTPAdapter(max_retries=0))
        self.session = session
        self.session.trust_env = False
        self.headers = {"Accept": "application/json, text/event-stream", "Content-Type": "application/json"}
        self.sequence = 0
        self.tools: set[str] = set()

    def _rpc(self, method: str, params: dict[str, Any] | None = None, *, notification=False):
        self.sequence += 1
        number = self.sequence
        body: dict[str, Any] = {"jsonrpc": "2.0", "method": method}
        if not notification:
            body["id"] = number
        if params is not None:
            body["params"] = params
        raw = encode(body)
        prefix = f"rpc/{number:03d}"
        self.store.write_bytes(prefix + "-request.json", raw)
        write = method == "tools/call" and (params or {}).get("name") in {"start_rule", "stop_rule"}
        headers = {**self.headers, "Authorization": "Bearer " + self.token_provider()}
        import requests
        started = self.clock()
        try:
            with self.session.post(
                self.url, headers=headers, data=raw, stream=True,
                timeout=(min(15, self.timeout), self.timeout), allow_redirects=False,
            ) as response:
                self.store.write(prefix + "-http.json", {
                    "atUtc": utc_now(), "status": response.status_code,
                    "contentType": response.headers.get("Content-Type", ""),
                    "requestId": response.headers.get("x-ms-request-id"),
                })
                actual = getattr(getattr(response, "request", None), "body", raw)
                if isinstance(actual, str):
                    actual = actual.encode("utf-8")
                if actual != raw:
                    raise ActivationError("The transmitted MCP body differs from the journal.")
                if response.status_code not in ((200, 202, 204) if notification else (200,)):
                    self.store.write_bytes(prefix + "-reply.body", response.content[:MAX_REPLY_BYTES])
                    if write and response.status_code in (408, 429, 500, 502, 503, 504):
                        raise AmbiguousActivationError("Native lifecycle write returned an uncertain HTTP result; inspect, do not resubmit.")
                    raise ActivationError(f"Native MCP HTTP {response.status_code}; inspect private evidence.")
                if response.headers.get("Mcp-Session-Id"):
                    self.headers["Mcp-Session-Id"] = response.headers["Mcp-Session-Id"]
                if notification:
                    self.store.write_bytes(prefix + "-reply.body", b"")
                    return None
                if "text/event-stream" in response.headers.get("Content-Type", ""):
                    wire = bytearray()
                    frame = bytearray()
                    reply = None
                    for line in response.iter_lines(chunk_size=1024):
                        if self.clock() - started > self.timeout:
                            raise TimeoutError("MCP response deadline exceeded.")
                        if isinstance(line, str):
                            line = line.encode("utf-8")
                        wire.extend(line + b"\n")
                        frame.extend(line + b"\n")
                        if len(wire) > MAX_REPLY_BYTES:
                            raise ActivationError("MCP response exceeded the evidence limit.")
                        if not line:
                            data = b"\n".join(
                                entry[5:].lstrip() for entry in frame.splitlines() if entry.startswith(b"data:")
                            )
                            frame.clear()
                            if data and data != b"[DONE]":
                                candidate = json.loads(data)
                                if isinstance(candidate, dict) and candidate.get("id") == number:
                                    reply = parse_rpc(data, number)
                                    break
                    self.store.write_bytes(prefix + "-reply.body", bytes(wire))
                    if reply is None:
                        raise ActivationError("Native MCP stream ended without a complete matching response.")
                else:
                    content = response.content
                    if len(content) > MAX_REPLY_BYTES:
                        raise ActivationError("MCP response exceeded the evidence limit.")
                    self.store.write_bytes(prefix + "-reply.body", content)
                    reply = parse_rpc(content, number)
                return reply
        except (requests.RequestException, TimeoutError) as exc:
            self.store.write(prefix + "-transport-error.json", {
                "atUtc": utc_now(), "errorType": type(exc).__name__, "writeOutcomeUnknown": write,
            })
            if write:
                raise AmbiguousActivationError("Lifecycle outcome is unknown; inspect actual state before any retry.") from exc
            raise ActivationError("Read-only MCP transport failed; inspect private evidence.") from exc
        except (ValueError, EvaluationError) as exc:
            if write and not isinstance(exc, ActivationError):
                raise AmbiguousActivationError("Lifecycle reply was not verifiable; inspect actual state before any retry.") from exc
            raise

    def connect(self):
        result = tool_result(self._rpc("initialize", {
            "protocolVersion": "2025-03-26", "capabilities": {},
            "clientInfo": {"name": "furusato-activator-lifecycle", "version": "1"},
        }))
        if result.get("protocolVersion") not in {"2024-11-05", "2025-03-26", "2025-06-18"}:
            raise ActivationError("Unsupported MCP protocol version.")
        self.headers["MCP-Protocol-Version"] = result["protocolVersion"]
        self._rpc("notifications/initialized", notification=True)
        cursor = None
        visited: set[str] = set()
        schemas = {}
        for _ in range(20):
            result = tool_result(self._rpc("tools/list", {"cursor": cursor} if cursor else {}))
            for tool in result.get("tools", []):
                if tool.get("name") in schemas:
                    raise ActivationError("MCP catalogue contains duplicate tool names.")
                schemas[tool["name"]] = tool.get("inputSchema", {})
            cursor = result.get("nextCursor")
            if not cursor:
                break
            if not isinstance(cursor, str):
                raise ActivationError("MCP catalogue cursor is malformed.")
            if cursor in visited:
                raise ActivationError("MCP catalogue repeated a continuation cursor.")
            visited.add(cursor)
        else:
            raise ActivationError("MCP catalogue exceeded the paging limit.")
        for name, argument in LIFECYCLE_TOOLS.items():
            schema = schemas.get(name, {})
            if argument not in schema.get("properties", {}) or argument not in schema.get("required", []):
                raise ActivationError("Required official Activator tools are unavailable or changed.")
        self.tools = set(LIFECYCLE_TOOLS)

    def _call(self, name: str, parameters: dict[str, Any]):
        if name not in self.tools:
            raise ActivationError("Unapproved or undiscovered Activator operation.")
        args = {"workspaceId": self.workspace_id, "artifactId": self.activator_id, **parameters}
        return tool_result(self._rpc("tools/call", {
            "name": name, "arguments": {LIFECYCLE_TOOLS[name]: args},
        }))

    def rules(self) -> list[dict[str, Any]]:
        rules = structured_result(self._call("list_rules", {})).get("rules")
        if not isinstance(rules, list) or not all(isinstance(rule, dict) for rule in rules):
            raise ActivationError("Rule listing is not a complete structured result.")
        return rules

    def set_running(self, rule_id: str, enabled: bool) -> dict[str, Any]:
        rule_id = guid(rule_id)
        if type(enabled) is not bool:
            raise ActivationError("Run state must be Boolean.")
        if len([rule for rule in self.rules() if rule.get("uniqueIdentifier") == rule_id]) != 1:
            raise ActivationError("The rule is not unique in the selected Activator.")
        action = "start_rule" if enabled else "stop_rule"
        self.store.write(f"{action}-{rule_id}-intent.json", {"atUtc": utc_now(), "operation": action, "ruleId": rule_id})
        # Running metadata can predate first-time execution initialization.
        acknowledgement = self._call(action, {"ruleId": rule_id})
        if not acknowledgement.get("content") and not acknowledgement.get("structuredContent"):
            raise AmbiguousActivationError("Official lifecycle acknowledgement is empty; inspect before continuing.")
        observations = []
        consistent = 0
        deadline = self.clock() + self.timeout
        while self.clock() < deadline:
            matches = [rule for rule in self.rules() if rule.get("uniqueIdentifier") == rule_id]
            if len(matches) != 1:
                raise ActivationError("The rule changed during lifecycle verification.")
            observations.append(matches[0])
            consistent = consistent + 1 if matches[0].get("isRunning") is enabled else 0
            if consistent == 2:
                result = {
                    "contract": CONTRACT, "atUtc": utc_now(), "workspaceId": self.workspace_id,
                    "activatorId": self.activator_id, "ruleId": rule_id, "operation": action,
                    "state": "armed_unverified" if enabled else "stopped",
                    "automaticDeliveryVerified": False, "acknowledgement": acknowledgement,
                    "observations": observations,
                }
                self.store.write(f"{action}-{rule_id}-result.json", result)
                return result
            self.sleeper(5)
        raise ActivationError("Lifecycle state did not stabilize within the bounded window.")

    def history(self, rule_id: str, start: str, end: str) -> dict[str, Any]:
        if parse_time(start) >= parse_time(end):
            raise ActivationError("Activation history needs an increasing UTC time window.")
        result = structured_result(self._call("get_activations_for_rule", {
            "ruleId": guid(rule_id), "startTime": start, "endTime": end, "maxResults": 1000,
        }))
        if not isinstance(result.get("activations"), list) or result.get("totalCount") != len(result["activations"]):
            raise ActivationError("Activation history is incomplete.")
        if result["totalCount"] >= 1000:
            raise ActivationError("Activation history may be truncated; narrow the time window.")
        return result

    def close(self):
        self.session.close()


def parse_time(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, TypeError, AttributeError) as exc:
        raise ActivationError("Native UTC timestamps are missing or invalid.") from exc
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)


def complete_blob_url(one_lake_files_path: str, workspace_id: str, lakehouse_id: str, filename: str) -> str:
    workspace_id, lakehouse_id = guid(workspace_id), guid(lakehouse_id)
    if filename not in {f"donation_events_{number:03d}.csv" for number in (1, 2, 3)}:
        raise ActivationError("Only a released increment filename is accepted.")
    parsed = urlsplit(one_lake_files_path)
    if (
        parsed.scheme != "https" or parsed.hostname != "onelake.dfs.fabric.microsoft.com"
        or parsed.port is not None or parsed.username is not None or parsed.password is not None
        or parsed.query or parsed.fragment or parsed.path.rstrip("/") != f"/{workspace_id}/{lakehouse_id}/Files"
    ):
        raise ActivationError("The discovered OneLake Files URL does not match the selected items.")
    return urlunsplit(("https", "onelake.blob.fabric.microsoft.com", parsed.path.rstrip("/") + "/increment/" + filename, "", ""))


def put_complete_increment(
    *, one_lake_files_path: str, workspace_id: str, lakehouse_id: str, filename: str,
    content: bytes, expected_sha256: str, token_provider: Callable[[], str],
    store: PrivateStore, session: Any | None = None,
) -> dict[str, Any]:
    if not isinstance(content, bytes) or not 0 < len(content) <= MAX_FILE_BYTES:
        raise ActivationError("The released complete CSV must fit the small-file upload limit.")
    digest = hashlib.sha256(content).hexdigest()
    if not re.fullmatch(r"[0-9a-f]{64}", expected_sha256) or digest != expected_sha256:
        raise ActivationError("CSV bytes do not match the released hash.")
    url = complete_blob_url(one_lake_files_path, workspace_id, lakehouse_id, filename)
    store.write("upload-intent.json", {
        "contract": CONTRACT, "atUtc": utc_now(), "url": url, "api": "PutBlob",
        "filename": filename, "sha256": digest, "bytes": len(content), "overwrite": False,
    })
    import requests
    owned = session is None
    client = session or requests.Session()
    client.trust_env = False
    headers = {
        "Authorization": "Bearer " + token_provider(), "x-ms-version": "2023-11-03",
        "x-ms-blob-type": "BlockBlob", "If-None-Match": "*", "Content-Type": "text/csv",
    }
    try:
        with client.put(url, data=content, headers=headers, timeout=(15, 60), allow_redirects=False) as reply:
            store.write("upload-response.json", {
                "atUtc": utc_now(), "status": reply.status_code, "requestId": reply.headers.get("x-ms-request-id"),
                "etag": reply.headers.get("ETag"), "body": reply.text[:3000] if reply.status_code != 201 else "",
            })
            if reply.status_code == 412:
                raise ActivationError("The file already exists. It was not overwritten; inspect prior delivery.")
            if reply.status_code != 201:
                raise AmbiguousActivationError("PutBlob did not produce a verifiable create receipt; inspect, never re-upload.")
        with client.get(
            url, headers={"Authorization": headers["Authorization"], "x-ms-version": "2023-11-03"},
            timeout=(15, 60), allow_redirects=False,
        ) as readback:
            if readback.status_code != 200 or readback.content != content:
                raise AmbiguousActivationError("Uploaded bytes were not verified; inspect, never re-upload.")
        result = {
            "contract": CONTRACT, "atUtc": utc_now(), "state": "uploaded_unverified",
            "filename": filename, "api": "PutBlob", "bytes": len(content), "sha256": digest,
            "uploadedBytesVerified": True, "automaticDeliveryVerified": False,
        }
        store.write("upload-result.json", result)
        return result
    except requests.RequestException as exc:
        store.write("upload-transport-error.json", {"atUtc": utc_now(), "type": type(exc).__name__, "outcomeUnknown": True})
        raise AmbiguousActivationError("Upload outcome is unknown; inspect file, events, jobs and data before any recovery.") from exc
    finally:
        if owned:
            client.close()


def verify_automatic_delivery(
    *, workspace_id: str, pipeline_id: str, rule_id: str, subject: str, source: str,
    expected_bytes: int, uploaded_bytes_verified: bool, events: Sequence[Mapping[str, Any]],
    history: Mapping[str, Any], jobs_before: Sequence[Mapping[str, Any]],
    jobs_after: Sequence[Mapping[str, Any]], manual_job_ids: set[str],
) -> dict[str, Any]:
    workspace_id, pipeline_id, rule_id = guid(workspace_id), guid(pipeline_id), guid(rule_id)
    if uploaded_bytes_verified is not True or type(expected_bytes) is not int or expected_bytes <= 0:
        raise ActivationError("Complete uploaded bytes are not proven.")
    matches = [event for event in events if event.get("___subject") == subject]
    if len(matches) != 1:
        raise ActivationError("Expected exactly one native file event for the exact subject.")
    event = matches[0]
    if (
        event.get("___type") != FILE_CREATED or event.get("___source") != source
        or event.get("api") != "PutBlob" or str(event.get("contentLength")) != str(expected_bytes)
        or not event.get("___id")
    ):
        raise ActivationError("The native event does not match the complete-file upload.")
    if history.get("isError") or not isinstance(history.get("activations"), list):
        raise ActivationError("Activation history is unavailable, not an empty successful result.")
    prefix = "System.Action.FabricItem."
    activations = [
        row for row in history["activations"]
        if row.get("properties", {}).get(prefix + "Parameters.Subject.String") == subject
    ]
    if len(activations) != 1:
        raise ActivationError("Expected exactly one native activation for this file.")
    activation = activations[0]["properties"]
    expected = {
        "System.RuleId": rule_id, prefix + "WorkspaceId": workspace_id, prefix + "ItemId": pipeline_id,
        prefix + "ItemType": "Pipeline", prefix + "JobType": "Pipeline",
        prefix + "Parameters.Type.String": FILE_CREATED, prefix + "Parameters.Source.String": source,
    }
    if any(activation.get(key) != value for key, value in expected.items()) or not activation.get("___id"):
        raise ActivationError("The native activation target or event parameters differ.")
    if not isinstance(subject, str) or not subject.startswith("/Files/") or not subject.endswith(".csv"):
        raise ActivationError("The evidence subject is not a scoped CSV file.")
    if not isinstance(source, str) or f"/workspaces/{workspace_id}/items/" not in source:
        raise ActivationError("The event source is outside the selected workspace.")
    previous = {job["id"] for job in jobs_before}
    new = [job for job in jobs_after if job["id"] not in previous]
    if len(new) != 1:
        raise ActivationError("Expected exactly one new pipeline job.")
    job = new[0]
    if job["id"] in manual_job_ids:
        raise ActivationError("A manual control cannot prove automatic delivery.")
    if job.get("itemId") != pipeline_id or job.get("status") != "Completed" or job.get("failureReason"):
        raise ActivationError("The matching Pipeline did not complete successfully.")
    started, ended = parse_time(job.get("startTimeUtc")), parse_time(job.get("endTimeUtc"))
    activated = parse_time(activations[0].get("activationTime"))
    if not -5 <= (started - activated).total_seconds() <= 900 or ended < started:
        raise ActivationError("Pipeline execution is outside the correlated activation window.")
    return {
        "contract": CONTRACT, "state": "automatic_delivery_verified", "eventId": event["___id"],
        "activationId": activation["___id"], "pipelineJobId": job["id"],
        "subject": subject, "pipelineId": pipeline_id, "manualInvocation": False,
        "copyAndDataVerified": False,
    }
