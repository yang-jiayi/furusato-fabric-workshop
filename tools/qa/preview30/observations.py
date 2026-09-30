"""Read-only checks for handed-off native discovery and definition snapshots."""

from __future__ import annotations

import base64
import binascii
import difflib
import json
import re

from preview_contract import EvidenceError, digest, timestamp


def inspect_mcp_discovery(capture: dict) -> dict:
    responses, errors = {}, []
    for request in capture.get("requests", []):
        method = request.get("method")
        if method in responses:
            raise EvidenceError("Duplicate discovery method; do not choose the best result.")
        if method not in {"initialize", "notifications/initialized", "tools/list"}:
            errors.append("non_discovery_request_present")
        if method == "notifications/initialized" and request.get("status") not in {200, 202, 204}:
            errors.append("initialized_notification_failed")
        body = request.get("body", "")
        try:
            body = json.loads(body) if isinstance(body, str) and body else body
        except ValueError as error:
            raise EvidenceError("Native MCP body is not intact JSON.") from error
        responses[method] = (request, body)
    for method in ("initialize", "tools/list"):
        request, body = responses.get(method, ({}, {}))
        if (request.get("status") != 200 or not request.get("requestId")
                or not isinstance(body, dict) or body.get("jsonrpc") != "2.0"
                or "error" in body or not isinstance(body.get("result"), dict)):
            errors.append(f"native_discovery_response_missing_or_failed:{method}")
    initialized = responses.get("initialize", ({}, {}))[1]
    listed = responses.get("tools/list", ({}, {}))[1]
    initialized = initialized.get("result", {}) if isinstance(initialized, dict) else {}
    listed = listed.get("result", {}) if isinstance(listed, dict) else {}
    tools = listed.get("tools", [])
    if not isinstance(tools, list) or not tools:
        errors.append("native_tool_catalog_empty")
        tools = []
    names = [tool.get("name") for tool in tools]
    if any(not isinstance(name, str) or not name for name in names) or len(names) != len(set(names)):
        errors.append("native_tool_names_missing_or_duplicated")
    protocol = initialized.get("protocolVersion")
    if not protocol or not initialized.get("serverInfo", {}).get("name"):
        errors.append("negotiated_protocol_or_native_server_missing")
    if capture.get("aiQuestionsSent") != 0 or capture.get("mutations") != 0:
        errors.append("capture_is_not_discovery_only")
    return {
        "schema_version": "furusato-preview30-mcp-discovery-check/v1",
        "discovery_state": "unverified" if errors else "pass", "errors": errors,
        "protocol_version": protocol, "server_info": initialized.get("serverInfo", {}),
        "tools": {tool["name"]: tool.get("inputSchema", {}) for tool in tools if tool.get("name")},
        "advertised_tool_names": names,
        "endpoint_url_recorded": bool(capture.get("endpoint")),
        "ai_questions": 0 if capture.get("aiQuestionsSent") == 0 else None,
        "query_execution_proven": False, "copilot_feature_pass": False, "ai_accuracy": None,
        "notes": [
            "Successful discovery is not a returned answer, source-query trace or UI action.",
            "Invoke only advertised names; a fallback mentioned in prose is not an advertised tool.",
            "Code generation/validation is not evidence that the generated query executed.",
        ],
    }


def decode_definition_snapshot(snapshot: dict) -> dict[str, str]:
    parts = snapshot.get("definition", {}).get("parts")
    if not isinstance(parts, list) or not parts or not snapshot.get("itemId"):
        raise EvidenceError("An item-bound native definition snapshot is required.")
    if snapshot.get("readOnly") is not True:
        raise EvidenceError("The handoff must distinguish readback from a proposed write.")
    timestamp(snapshot.get("capturedUtc"))
    decoded = {}
    for part in parts:
        path = part.get("path")
        if not isinstance(path, str) or not path or path in decoded or part.get("payloadType") != "InlineBase64":
            raise EvidenceError("Duplicate, missing or non-native definition part.")
        try:
            text = base64.b64decode(part["payload"], validate=True).decode("utf-8-sig").replace("\r\n", "\n")
        except (binascii.Error, KeyError, TypeError, UnicodeError) as error:
            raise EvidenceError("Invalid definition payload.") from error
        decoded[path] = text
    return decoded


def _lines(text: str) -> list[str]:
    return [line.rstrip() for line in text.splitlines() if line.strip()]


def _synonym_name(line: str) -> str | None:
    match = re.fullmatch(r"(?:\t| {4})synonym\s+(.+?)\s*", line)
    if not match:
        return None
    value = match.group(1)
    if value.startswith("'") and value.endswith("'"):
        value = value[1:-1].replace("''", "'")
    return value


def check_synonym_only_delta(before: dict, after: dict, entity_part: str, synonym: str,
                             restored: dict | None = None) -> dict:
    """Remove only the one authorized addition; every other line is protected."""
    if not synonym or any(character in synonym for character in "\r\n"):
        raise EvidenceError("Declare one exact, single-line synonym.")
    if before.get("itemId") != after.get("itemId"):
        raise EvidenceError("Before/after item identity differs.")
    left, right = decode_definition_snapshot(before), decode_definition_snapshot(after)
    if entity_part not in left or not entity_part.startswith("entities/") or not entity_part.endswith(".tmdl"):
        raise EvidenceError("The approved existing entity part is required.")
    if timestamp(before["capturedUtc"]) > timestamp(after["capturedUtc"]):
        raise EvidenceError("Definition snapshots are in the wrong temporal order.")
    paths_equal = set(left) == set(right)
    before_occurrences = sum(_synonym_name(line) == synonym for line in left[entity_part].splitlines())
    after_lines = right.get(entity_part, "").splitlines()
    occurrences = [index for index, line in enumerate(after_lines) if _synonym_name(line) == synonym]
    expected_addition = before_occurrences == 0 and len(occurrences) == 1
    stripped_after = dict(right)
    if expected_addition:
        stripped_after[entity_part] = "\n".join(
            line for index, line in enumerate(after_lines) if index != occurrences[0]
        )
    protected_changes = sorted(path for path in set(left) | set(stripped_after)
                               if _lines(left.get(path, "")) != _lines(stripped_after.get(path, "")))
    changed = sorted(path for path in set(left) | set(right) if _lines(left.get(path, "")) != _lines(right.get(path, "")))
    diffs = {path: list(difflib.unified_diff(left.get(path, "").splitlines(), right.get(path, "").splitlines(),
                                          fromfile="before/" + path, tofile="after/" + path, lineterm=""))
             for path in changed}
    restoration_equal = None
    if restored is not None:
        if restored.get("itemId") != before["itemId"]:
            raise EvidenceError("Restore readback targets a different item.")
        restored_parts = decode_definition_snapshot(restored)
        if timestamp(restored["capturedUtc"]) < timestamp(after["capturedUtc"]):
            raise EvidenceError("Restore readback predates the changed state.")
        restoration_equal = {path: _lines(text) for path, text in restored_parts.items()} == {
            path: _lines(text) for path, text in left.items()
        }
    return {
        "schema_version": "furusato-preview30-synonym-delta-check/v1",
        "structural_delta_state": "pass" if expected_addition and paths_equal and not protected_changes else "fail",
        "same_part_paths": paths_equal, "expected_synonym_addition_observed": expected_addition,
        "protected_content_changes": protected_changes, "changed_parts": diffs,
        "independent_before_digest": digest(left), "independent_after_digest": digest(right),
        "restored_definition_equals_before": restoration_equal,
        "restore_does_not_erase_failed_candidate": True,
        "version_history_ui_action_proven": False, "source_data_restore_proven": False,
        "ai_accuracy": None,
    }
