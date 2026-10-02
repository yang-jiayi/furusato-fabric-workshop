"""Public Fabric MCP consumption, with an honest answer-only evidence contract.

Protocol: https://learn.microsoft.com/fabric/data-science/data-agent-mcp-server
The public endpoint was exercised successfully; it returns native final text,
not source SQL/KQL/GQL, returned rows or a backend conversation identifier.
JSON-RPC IDs and MCP session IDs are NEVER backend conversation/response IDs.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import hashlib
import json
import math
import re
from typing import Any, Callable
from uuid import UUID

from native_evaluation import EvaluationError, encode, platform_content_block


PROTOCOL = "fabric-mcp"
CONTRACT = "public-fabric-mcp/answer-only-v1"
PROTOCOL_VERSION = "2025-06-18"
SCOPE = "https://api.fabric.microsoft.com/.default"
QUESTION_RPC_ID = 3
OBSERVABILITY_BLOCKERS = (
    "native_source_queries_and_results_unobservable",
    "backend_conversation_identity_unobservable",
)
SAFE_HEADERS = frozenset({
    "content-type", "requestid", "x-ms-request-id", "activityid", "traceparent",
    "x-ms-root-activity-id", "x-ms-operation-id", "mcp-session-id",
    "mcp-protocol-version",
})
SKILL = "fabriciq-ontology-cli"


def observability() -> dict[str, Any]:
    return {
        "mode": "answer_only",
        "source_queries": "unobservable",
        "source_query_results": "unobservable",
        "backend_conversation_identity": "unobservable",
        "source_query_count": None,
        "strict_acceptance_eligible": False,
        "blockers": list(OBSERVABILITY_BLOCKERS),
    }


def validate_config(config: dict[str, Any]) -> dict[str, str]:
    try:
        result = {key: str(UUID(config[key])) for key in ("workspace_id", "data_agent_id")}
    except (KeyError, TypeError, AttributeError, ValueError) as exc:
        raise EvaluationError("MCP requires workspace_id and data_agent_id.") from exc
    if config.get("stage") != "production":
        raise EvaluationError("The public MCP endpoint requires a published production agent; no stage fallback.")
    return {**result, "stage": "production"}


def parse_rpc(body: bytes, request_id: int) -> dict[str, Any]:
    """Decode one complete JSON-RPC reply, retaining the original wire separately."""
    try:
        text = body.decode("utf-8-sig")
        if text.lstrip().startswith("{"):
            payloads = [json.loads(text)]
        else:
            payloads = []
            for block in text.replace("\r\n", "\n").replace("\r", "\n").split("\n\n"):
                data = "\n".join(
                    line[5:].lstrip() for line in block.splitlines() if line.startswith("data:")
                )
                if data and data != "[DONE]":
                    payloads.append(json.loads(data))
        replies = [
            p for p in payloads
            if isinstance(p, dict) and p.get("id") == request_id
            and ("result" in p or "error" in p)
        ]
        if len(replies) != 1:
            raise EvaluationError("No unique complete native RPC reply; no partial-text reconstruction.")
        reply = replies[0]
        if reply.get("jsonrpc") != "2.0" or (("result" in reply) == ("error" in reply)):
            raise EvaluationError("Malformed native JSON-RPC reply.")
        return reply
    except (ValueError, UnicodeError) as exc:
        raise EvaluationError("Malformed or incomplete native MCP reply.") from exc


def discover_question_tool(reply: dict[str, Any]) -> tuple[str, str]:
    """Require the verified single-tool, single-string-input contract."""
    result = reply.get("result")
    if not isinstance(result, dict) or result.get("nextCursor"):
        raise EvaluationError("MCP tool discovery is incomplete.")
    tools = result.get("tools")
    if not isinstance(tools, list) or len(tools) != 1 or not isinstance(tools[0], dict):
        raise EvaluationError("Expected exactly one native Data Agent tool.")
    tool = tools[0]
    schema = tool.get("inputSchema", {})
    if not isinstance(schema, dict):
        raise EvaluationError("Unsupported native question tool schema.")
    properties = schema.get("properties", {})
    if (not isinstance(tool.get("name"), str) or not tool["name"].strip()
            or schema.get("type") != "object"
            or not isinstance(properties, dict) or len(properties) != 1):
        raise EvaluationError("Unsupported native question tool schema.")
    argument, definition = next(iter(properties.items()))
    if (not isinstance(argument, str) or not argument
            or not isinstance(definition, dict) or definition.get("type") != "string"
            or schema.get("required") != [argument]
            or schema.get("additionalProperties", False) is not False):
        raise EvaluationError("Expected one required string question argument.")
    return tool["name"], argument


def validate_notification(status: int, body: bytes, headers: dict[str, str]) -> None:
    if status not in (200, 202, 204):
        raise McpFailure("Native MCP initialized notification failed.", "initialized", status)
    if not body.strip():
        return
    mime = next((value for key, value in headers.items() if key.lower() == "content-type"), "")
    if status == 202 and mime.split(";", 1)[0].strip().lower() == "text/plain" and body == b"Accepted":
        return
    raise McpFailure("Unexpected native notification body; raw reply retained.", "initialized", status)


@dataclass(frozen=True)
class NotebookToken:
    token: str


class NotebookMcpCredential:
    """Use the documented managed token only after exact owned-runtime checks."""

    def __init__(self, notebook_module: Any, *, notebook_id: str, notebook_name: str, workspace_id: str):
        self.module = notebook_module
        try:
            self.notebook_id, self.workspace_id = str(UUID(notebook_id)), str(UUID(workspace_id))
        except (AttributeError, TypeError, ValueError) as exc:
            raise EvaluationError("Expected notebook and workspace GUIDs are required.") from exc
        if not isinstance(notebook_name, str) or not notebook_name.strip():
            raise EvaluationError("Expected notebook name is required.")
        self.notebook_name = notebook_name

    def get_token(self, scope: str) -> NotebookToken:
        if scope != SCOPE:
            raise EvaluationError("Notebook MCP credentials are limited to the Fabric API.")
        context = self.module.runtime.context
        if not isinstance(context, Mapping):
            raise EvaluationError("A normal Fabric runtime Mapping is required.")
        required = (
            "productType", "currentNotebookId", "currentNotebookName", "currentWorkspaceId",
            "isForPipeline", "isReferenceRun", "isForInteractive", "defaultLakehouseId",
        )
        try:
            values = {key: context[key] for key in required}
        except KeyError as exc:
            raise EvaluationError("A required runtime field is unavailable; no default is assumed.") from exc
        if (
            any(type(values[key]) is not str for key in (
                "productType", "currentNotebookId", "currentNotebookName", "currentWorkspaceId",
            ))
            or values["productType"] != "Fabric"
            or values["currentNotebookId"] != self.notebook_id
            or values["currentNotebookName"] != self.notebook_name
            or values["currentWorkspaceId"] != self.workspace_id
            or values["isForPipeline"] is not False
            or values["isReferenceRun"] is not False
            or type(values["isForInteractive"]) is not bool
            or not (values["defaultLakehouseId"] is None
                    or type(values["defaultLakehouseId"]) is str and values["defaultLakehouseId"] == "")
        ):
            raise EvaluationError("Runtime identity, execution flags or no-default-Lakehouse guard failed.")
        token = self.module.credentials.getToken("pbi")
        if not isinstance(token, str) or not token.strip() or "\r" in token or "\n" in token:
            raise EvaluationError("Managed notebook authentication returned no usable token.")
        return NotebookToken(token)


@dataclass(frozen=True)
class McpDiscovery:
    tool_name: str
    question_argument: str
    input_schema_sha256: str
    mcp_session_id: str | None
    question_submissions: int = 0
    strict_acceptance_eligible: bool = False


def native_view(reply: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Extract only native text, without inventing internal calls, rows or IDs."""
    problems: list[str] = []
    texts = []
    if reply.get("jsonrpc") != "2.0" or reply.get("id") != QUESTION_RPC_ID:
        problems.append("native_rpc_identity_invalid")
    if "error" in reply:
        problems.append("native_rpc_error")
    result = reply.get("result")
    if not isinstance(result, dict):
        return {"final_texts": []}, problems + ["native_tool_result_missing"]
    # MCP's isError is optional; an omitted field defaults to false. This
    # says nothing about internal source execution observability.
    if result.get("isError", False) is not False:
        problems.append("native_tool_error_or_status_missing")
    content = result.get("content")
    if not isinstance(content, list):
        return {"final_texts": []}, problems + ["native_content_missing"]
    for index, block in enumerate(content):
        if isinstance(block, dict) and block.get("type") == "text" and isinstance(block.get("text"), str):
            if block["text"].strip():
                texts.append({"pointer": f"/result/content/{index}/text", "text": block["text"]})
                if platform_content_block(block["text"]):
                    problems.append("native_platform_content_block")
    if not texts:
        problems.append("native_final_answer_missing")
    return {"final_texts": texts}, problems


@dataclass(frozen=True)
class McpResult:
    response: dict[str, Any]
    tool_name: str
    question_argument: str
    # This is a transport session handle, never a backend conversation ID.
    mcp_session_id: str | None


class McpFailure(EvaluationError):
    def __init__(self, message: str, phase: str, http_status: int | None = None):
        super().__init__(message)
        self.phase, self.http_status = phase, http_status


class NativeMcpClient:
    """A new HTTP client/session per case; exactly one non-retried question POST."""

    def __init__(
        self, config: dict[str, Any], credential: Any, timeout: float,
        *, session_factory: Callable[[], Any] | None = None, skill_name: str = SKILL,
    ):
        self.config = validate_config(config)
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or timeout <= 0:
            raise EvaluationError("MCP timeout must be a positive finite number.")
        if not isinstance(skill_name, str) or re.fullmatch(r"[a-z][a-z0-9-]{0,63}", skill_name) is None:
            raise EvaluationError("A portable skill attribution name is required.")
        self.credential, self.timeout = credential, timeout
        self.skill_name = skill_name
        self.session_factory = session_factory
        self.url = (
            f"https://api.fabric.microsoft.com/v1/mcp/workspaces/{self.config['workspace_id']}"
            f"/dataagents/{self.config['data_agent_id']}/agent"
        )

    def _session(self):
        if self.session_factory:
            session = self.session_factory()
        else:
            import requests
            from requests.adapters import HTTPAdapter
            session = requests.Session()
            session.mount("https://", HTTPAdapter(max_retries=0))
        session.trust_env = False  # .netrc must never replace the bearer token.
        return session

    def preflight(self, emit: Callable[[str, bytes], Any]) -> McpDiscovery:
        """Discover the published tool without creating a question or scoring it."""
        result = self._exchange(None, emit, None)
        if not isinstance(result, McpDiscovery):
            raise AssertionError("Preflight cannot return a question response.")
        return result

    def ask(
        self, question: str, emit: Callable[[str, bytes], Any],
        before_submit: Callable[[], None],
    ) -> McpResult:
        if not isinstance(question, str) or not question.strip():
            raise EvaluationError("A nonempty exact question is required.")
        result = self._exchange(question, emit, before_submit)
        if not isinstance(result, McpResult):
            raise AssertionError("A submitted question must return its native response.")
        return result

    def _exchange(
        self, question: str | None, emit: Callable[[str, bytes], Any],
        before_submit: Callable[[], None] | None,
    ) -> McpResult | McpDiscovery:
        # No auth/network work occurs in the constructor or offline CLI paths.
        token = self.credential.get_token(SCOPE)
        headers = {
            "Authorization": "Bearer " + token.token,
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "x-ms-fabric-skill": self.skill_name,
        }
        session = self._session()
        session_id = None
        failed = False
        try:
            def send(phase: str, message: dict[str, Any]):
                body = encode(message)
                emit(f"{phase}-request.body", body)
                if phase == "question":
                    # Caller journals the sole submission intent before network IO.
                    if before_submit is None:
                        raise McpFailure("No question submission journal supplied.", phase)
                    before_submit()
                with session.post(
                    self.url, headers=headers, data=body,
                    timeout=self.timeout if phase == "question" else min(self.timeout, 90),
                    allow_redirects=False,
                ) as response:
                    emit(f"{phase}-reply.body", response.content)
                    safe = {k: v for k, v in response.headers.items() if k.lower() in SAFE_HEADERS}
                    emit(f"{phase}-http.json", encode({
                        "method": "POST", "url": self.url,
                        "status": response.status_code, "headers": safe,
                        "skill": self.skill_name,
                    }))
                    actual = response.request.body or b""
                    if isinstance(actual, str):
                        actual = actual.encode("utf-8")
                    if actual != body:
                        raise McpFailure("Native wire request differs from the frozen request.", phase)
                    return response.status_code, response.content, safe

            status, body, safe = send("initialize", {
                "jsonrpc": "2.0", "id": 1, "method": "initialize",
                "params": {
                    "protocolVersion": PROTOCOL_VERSION, "capabilities": {},
                    "clientInfo": {"name": "furusato-native-evaluator", "version": "1"},
                },
            })
            if status != 200:
                raise McpFailure("Native MCP initialization failed.", "initialize", status)
            initial = parse_rpc(body, 1)
            result = initial.get("result")
            if not isinstance(result, dict) or not isinstance(result.get("protocolVersion"), str):
                raise McpFailure("Native MCP initialization result is incomplete.", "initialize")
            headers["MCP-Protocol-Version"] = result["protocolVersion"]
            session_id = next((v for k, v in safe.items() if k.lower() == "mcp-session-id"), None)
            if session_id:
                headers["Mcp-Session-Id"] = session_id
            status, body, safe = send("initialized", {"jsonrpc": "2.0", "method": "notifications/initialized"})
            validate_notification(status, body, safe)
            status, body, _ = send("tools-list", {
                "jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {},
            })
            if status != 200:
                raise McpFailure("Native MCP tool discovery failed.", "tools-list", status)
            listed = parse_rpc(body, 2)
            tool, argument = discover_question_tool(listed)
            if question is None:
                schema = listed["result"]["tools"][0]["inputSchema"]
                return McpDiscovery(tool, argument, hashlib.sha256(encode(schema)).hexdigest(), session_id)
            status, body, _ = send("question", {
                "jsonrpc": "2.0", "id": QUESTION_RPC_ID, "method": "tools/call",
                "params": {"name": tool, "arguments": {argument: question}},
            })
            if status != 200:
                raise McpFailure("Native question HTTP failure; not resubmitted.", "question", status)
            return McpResult(parse_rpc(body, QUESTION_RPC_ID), tool, argument, session_id)
        except BaseException:
            failed = True
            raise
        finally:
            try:
                if question is None and session_id:
                    try:
                        with session.delete(
                            self.url, headers=headers, timeout=min(self.timeout, 10),
                            allow_redirects=False,
                        ) as response:
                            emit("session-close-reply.body", response.content)
                            emit("session-close-http.json", encode({
                                "method": "DELETE", "url": self.url, "status": response.status_code,
                                "skill": self.skill_name,
                                "headers": {k: v for k, v in response.headers.items() if k.lower() in SAFE_HEADERS},
                            }))
                            if response.status_code not in (200, 202, 204, 405):
                                raise McpFailure("Native MCP session cleanup failed.", "session-close", response.status_code)
                    except Exception as exc:
                        emit("session-close-error.json", encode({"error_type": type(exc).__name__}))
                        if not failed:
                            raise
            finally:
                session.close()

    def close(self) -> None:
        """Sessions are case-local and already closed by ask()."""
