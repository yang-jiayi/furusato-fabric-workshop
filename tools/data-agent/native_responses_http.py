"""Small HTTP transport matching the published Fabric Responses SDK protocol.

This is an SDK-aligned *native workload* transport, not a claim that the
regional /webapi routes are a stable Fabric public REST contract. The protocol
was checked against fabric-data-agent-sdk 0.1.31a0 (_fabric_openai_responses.py,
_fabric_openai.py and _diagnostics.py). Requalify it when that contract changes.

Use only a privately supplied, observed workload host and real deployment IDs.
Never derive a workload host from a Fabric capacity's region. No metadata
discovery, authentication or HTTP calls occur merely by importing this module.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote, urlparse
from uuid import UUID, uuid4

from native_evaluation import EvaluationError, encode


PBI_SCOPE = "https://analysis.windows.net/powerbi/api/.default"
PROTOCOL_VERSION = "fabric-data-agent-sdk/0.1.31a0"
API_VERSION = "2024-05-01-preview"
DEFAULT_MODEL = "gpt-5.1"  # The published Responses SDK's protocol default.


@dataclass(frozen=True)
class RawReply:
    """Body bytes only: never an authorization header, token, cookie or HAR."""

    body: bytes
    status: int = 200
    request_body: bytes = b""


class NativeEvidenceError(EvaluationError):
    """Retain a failed native body for private capture, never for console output."""

    def __init__(self, message: str, native_body: bytes, http_status: int | None = None):
        super().__init__(message)
        self.native_body = native_body
        self.http_status = http_status


def diagnostics_feature_unavailable(body: bytes, http_status: int | None) -> bool:
    """Recognize only the observed optional diagnostic feature gate, not auth/query failures."""
    if http_status != 403:
        return False
    try:
        payload = json.loads(body)
    except (ValueError, UnicodeError):
        return False
    return isinstance(payload, dict) and all(
        payload.get(key) == value for key, value in {
            "Message": "Data Agent diagnostics feature is not enabled.",
            "Source": "AISKILL",
            "error_code": "PERMISSION_DENIED",
        }.items()
    )


def workload_host(value: str) -> str:
    """Accept an explicit HTTPS Microsoft workload origin, never a URL override."""
    if not isinstance(value, str):
        raise EvaluationError("An observed private workload_host is required.")
    parsed = urlparse(value)
    if (
        parsed.scheme != "https"
        or parsed.username is not None or parsed.password is not None
        or parsed.path not in ("", "/") or parsed.query or parsed.fragment
        or parsed.netloc != parsed.hostname
        or not re.fullmatch(
            r"(?:[a-z0-9-]+\.analysis\.windows\.net|[0-9a-f]{32}\.pbidedicated\.windows\.net)",
            parsed.hostname or "",
        )
    ):
        raise EvaluationError("workload_host must be an observed HTTPS Microsoft workload origin.")
    return value.rstrip("/")


def runtime_config(config: dict[str, Any]) -> dict[str, str]:
    """Validate required identifiers before acquiring any token."""
    result = {"workload_host": workload_host(config.get("workload_host"))}
    try:
        for key in ("workspace_id", "data_agent_id", "capacity_id"):
            result[key] = str(UUID(config[key]))
    except (KeyError, ValueError, TypeError, AttributeError) as exc:
        raise EvaluationError("Native HTTP requires workspace_id, data_agent_id and capacity_id.") from exc
    host = urlparse(result["workload_host"]).hostname
    if host.endswith(".pbidedicated.windows.net") and host.split(".")[0] != UUID(result["capacity_id"]).hex:
        raise EvaluationError("Observed dedicated workload host belongs to a different capacity.")
    if config.get("stage") not in {"production", "sandbox"}:
        raise EvaluationError("Native HTTP requires an explicit production/sandbox stage.")
    result["stage"] = config["stage"]
    return result


def native_id(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,256}", value):
        raise EvaluationError("Unsupported native resource ID; refusing to guess its URL.")
    return quote(value, safe="")


class ResponsesHttpClient:
    """One request per invocation, no hidden retries, redirects or query rewriting."""

    def __init__(
        self, config: dict[str, Any], credential: Any, timeout: float, *, session: Any = None,
    ):
        self.config = runtime_config(config)
        self.credential, self.timeout = credential, timeout
        if session is None:
            import requests
            from requests.adapters import HTTPAdapter
            session = requests.Session()
            session.mount("https://", HTTPAdapter(max_retries=0))
        self.session = session
        # Do not allow .netrc to replace a bearer header. Proxy/certificate
        # exceptions are not guessed; any connectivity failure remains a block.
        self.session.trust_env = False
        self.moniker = str(uuid4())
        cfg = self.config
        self.base = (
            f"{cfg['workload_host']}/webapi/capacities/{cfg['capacity_id']}"
            f"/workloads/ML/AISkill/Automatic/v1/workspaces/{cfg['workspace_id']}"
        )
        self.artifact = f"{self.base}/artifacts/{cfg['data_agent_id']}"

    def _request(
        self, method: str, path: str, *, payload: dict[str, Any] | None = None,
        params: dict[str, str] | None = None,
    ) -> RawReply:
        # Paths are built only by the methods below. Never accept arbitrary
        # response-provided URLs and never forward bearer tokens on redirects.
        if not path.startswith(self.base + "/"):
            raise EvaluationError("Refusing a cross-origin/workspace native request.")
        token = self.credential.get_token(PBI_SCOPE)
        headers = {
            "Authorization": f"Bearer {token.token}",
            "Accept": "application/json", "Content-Type": "application/json",
            "ActivityId": str(uuid4()),
            "x-ms-workload-resource-moniker": self.moniker,
            "x-ms-ai-assistant-scenario": "aiskill",
            "x-ms-ai-aiskill-stage": self.config["stage"],
            "X-Taxonomy-TrafficType": "Production",
            "x-llm-service-tier": "default",
        }
        body = encode(payload) if payload is not None else None
        with self.session.request(
            method, path, data=body, params=params, headers=headers,
            timeout=self.timeout, allow_redirects=False,
        ) as response:
            wire_body = response.request.body or b""
            if isinstance(wire_body, str):
                wire_body = wire_body.encode("utf-8")
            return RawReply(response.content, response.status_code, wire_body)

    def new_conversation(self) -> RawReply:
        return self._request(
            "POST", f"{self.artifact}/conversations",
            payload={}, params={"api-version": API_VERSION},
        )

    def submit(self, question: str, conversation_id: str) -> RawReply:
        native_id(conversation_id)
        if not isinstance(question, str) or not question.strip():
            raise EvaluationError("A nonempty exact question is required.")
        return self._request(
            "POST", f"{self.artifact}/responses",
            payload={
                "input": question, "conversation": conversation_id,
                "model": DEFAULT_MODEL, "stream": False,
            },
            params={"api-version": API_VERSION},
        )

    def retrieve(self, response_id: str) -> RawReply:
        return self._request(
            "GET", f"{self.artifact}/responses/{native_id(response_id)}",
            params={"api-version": API_VERSION},
        )

    def file_content(self, file_id: str) -> RawReply:
        """Read an actual returned file ID through the SDK's scoped files route."""
        return self._request(
            "GET", f"{self.artifact}/aiassistant/openai/files/{native_id(file_id)}/content",
            params={"api-version": API_VERSION},
        )

    def diagnostics(self, conversation_id: str, response_id: str) -> dict[str, Any]:
        native_id(response_id)
        reply = self._request(
            "GET",
            f"{self.base}/dataagents/{self.config['data_agent_id']}"
            f"/conversations/{native_id(conversation_id)}/diagnostics",
            params={"responseId": response_id},
        )
        if reply.status != 200:
            raise NativeEvidenceError(
                f"Native diagnostics HTTP {reply.status}; no question retry.", reply.body, reply.status,
            )
        try:
            result = json.loads(reply.body)
            if not isinstance(result, dict):
                raise NativeEvidenceError("Native diagnostics must be an object.", reply.body)
            return result
        except ValueError as exc:
            raise NativeEvidenceError("Malformed native diagnostics.", reply.body) from exc

    def close(self) -> None:
        self.session.close()
