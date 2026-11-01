"""Strict hash-bound validation for native Fabric event-detail observations."""
from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Mapping

from activation_runtime import ActivationError, FILE_CREATED, PrivateStore, guid, parse_time


EXPECTED_RECEIPTS = {
    "activation/readiness-1793506889686561800/definition.json",
    "increments/donation_events_001.csv/observation-01/history.json",
    "increments/donation_events_001.csv/upload/upload-result.json",
    "increments/donation_events_001.csv/bounded-monitor-01/native-copy-001.json",
}
EXPECTED_SCREENSHOT_COVERAGE = {
    "rowCount", "timeUtc", "eventId", "subject", "type", "api", "contentLength", "contentType",
}


def _read_bound_file(root: Path, relative: Any, expected_hash: Any) -> bytes:
    if not isinstance(relative, str) or not relative:
        raise ActivationError("A hash-bound evidence path is missing.")
    relative = relative.replace("\\", "/")
    path_value = Path(relative)
    if path_value.is_absolute() or any(part in {"", ".", ".."} for part in path_value.parts):
        raise ActivationError("Evidence paths must be clean relative paths.")
    if not isinstance(expected_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_hash):
        raise ActivationError("Evidence SHA-256 is missing or malformed.")
    root = root.resolve()
    PrivateStore._reject_git_path(root)
    path = (root / path_value).resolve()
    if not path.is_relative_to(root):
        raise ActivationError("Evidence path escapes its declared root.")
    PrivateStore._reject_git_path(path)
    try:
        content = path.read_bytes()
    except OSError as exc:
        raise ActivationError("A hash-bound evidence file is missing or unreadable.") from exc
    if hashlib.sha256(content).hexdigest() != expected_hash:
        raise ActivationError("Hash-bound evidence changed after observation.")
    return content


def _decode_entities(definition: Mapping[str, Any]) -> list[dict[str, Any]]:
    parts = definition.get("parts")
    if not isinstance(parts, list):
        raise ActivationError("Native definition parts are missing.")
    matches = [part for part in parts if isinstance(part, dict) and part.get("path") == "ReflexEntities.json"]
    if len(matches) != 1 or matches[0].get("payloadType") != "InlineBase64":
        raise ActivationError("Native definition entity part is absent or ambiguous.")
    try:
        entities = json.loads(base64.b64decode(matches[0]["payload"], validate=True))
    except (KeyError, ValueError, TypeError, json.JSONDecodeError) as exc:
        raise ActivationError("Native definition entity payload is invalid.") from exc
    if not isinstance(entities, list) or any(not isinstance(item, dict) for item in entities):
        raise ActivationError("Native definition entities are malformed.")
    return entities


def _decode_instance(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    try:
        return json.loads(value)
    except ValueError:
        return value


def _walk(value: Any):
    value = _decode_instance(value)
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def _arguments(node: Mapping[str, Any]) -> dict[str, Any]:
    arguments = node.get("arguments")
    if not isinstance(arguments, list):
        return {}
    return {
        argument["name"]: argument.get("value", argument.get("values"))
        for argument in arguments
        if isinstance(argument, dict) and isinstance(argument.get("name"), str)
    }


def _definition_projection(
    definition: Mapping[str, Any], *, rule_id: str, model_id: str,
    workspace_id: str, lakehouse_id: str, pipeline_id: str,
) -> tuple[dict[str, Any], dict[str, str]]:
    entities = _decode_entities(definition)
    by_id: dict[str, list[dict[str, Any]]] = {}
    for entity in entities:
        if isinstance(entity.get("uniqueIdentifier"), str):
            by_id.setdefault(entity["uniqueIdentifier"], []).append(entity)
    selected: dict[str, dict[str, Any]] = {}
    for identifier, label in ((rule_id, "rule"), (model_id, "event model")):
        matches = by_id.get(identifier, [])
        if len(matches) != 1:
            raise ActivationError(f"Native definition lacks one owned {label}.")
        selected[label] = matches[0]

    model = selected["event model"]
    model_definition = model.get("payload", {}).get("definition", {})
    if model.get("type") != "timeSeriesView-v1" or model_definition.get("type") != "Event":
        raise ActivationError("Referenced source model is not a native Event.")
    model_nodes = list(_walk(_decode_instance(model_definition.get("instance"))))
    source_ids = [
        _arguments(node).get("entityId") for node in model_nodes
        if node.get("kind") == "SourceReference"
    ]
    if len(source_ids) != 1 or not isinstance(source_ids[0], str):
        raise ActivationError("Native Event source reference is missing or ambiguous.")
    source_id = source_ids[0]
    source_entities = by_id.get(source_id, [])
    if len(source_entities) != 1 or source_entities[0].get("type") != "realTimeHubSource-v1":
        raise ActivationError("Native Event does not reference one supported source entity.")
    connection = source_entities[0].get("payload", {}).get("connection", {})
    if (connection.get("workspaceId") != workspace_id
            or connection.get("artifactId") != lakehouse_id):
        raise ActivationError("Native Event source points outside the owned Lakehouse.")

    rule = selected["rule"]
    rule_definition = rule.get("payload", {}).get("definition", {})
    if rule.get("type") != "timeSeriesView-v1" or rule_definition.get("type") != "Rule":
        raise ActivationError("Owned native definition is not the expected Rule.")
    nodes = list(_walk(_decode_instance(rule_definition.get("instance"))))
    event_references = [
        _arguments(node).get("entityId") for node in nodes
        if node.get("kind") == "EventReference"
    ]
    if event_references != [model_id]:
        raise ActivationError("Rule EventReference is not unique or does not target the observed model.")

    bindings: dict[str, str] = {}
    for parameter in (node for node in nodes if node.get("kind") == "FabricItemParameter"):
        arguments = _arguments(parameter)
        name, value = arguments.get("parameterName"), arguments.get("parameterValue")
        if name not in {"Source", "Subject", "Type"}:
            continue
        fields = [
            _arguments(node).get("fieldName") for node in _walk(value)
            if node.get("kind") == "EventFieldReference"
        ]
        if len(fields) != 1 or name in bindings:
            raise ActivationError("Native event field binding is missing or ambiguous.")
        bindings[name] = fields[0]
    if bindings != {"Source": "___source", "Subject": "___subject", "Type": "___type"}:
        raise ActivationError("Native action parameters are not nonconstant event-field references.")
    invocations = [node for node in nodes if node.get("kind") == "FabricItemInvocation"]
    if len(invocations) != 1:
        raise ActivationError("Rule does not contain one native Pipeline action.")
    invocation = _arguments(invocations[0])
    if any(invocation.get(name) != expected for name, expected in {
        "workspaceId": workspace_id, "itemId": pipeline_id,
        "itemType": "Pipeline", "jobType": "Pipeline",
    }.items()):
        raise ActivationError("Native rule action differs from the owned Pipeline.")
    if rule_definition.get("settings", {}).get("shouldRun") is not True:
        raise ActivationError("Native rule is not enabled for execution.")
    projection = {identifier: by_id[identifier][0] for identifier in (rule_id, model_id, source_id)}
    return projection, bindings


def validate_observation(
    observation: Mapping[str, Any], *, screenshot_root: Path, receipt_root: Path,
    workspace_id: str, tenant_id: str, activator_id: str, model_id: str, rule_id: str,
    pipeline_id: str, lakehouse_id: str, subject: str, expected_bytes: int,
    expected_upload_sha256: str, current_definition: Mapping[str, Any],
) -> dict[str, Any]:
    """Return observed event fields and verified provenance; never returns a synthetic event row."""
    if not isinstance(observation, Mapping) or observation.get("kind") != "native-ui-observation-not-csv-export":
        raise ActivationError("Input must be the explicitly tagged native UI observation.")
    if (observation.get("workspaceId") != workspace_id
            or observation.get("activatorId") != activator_id
            or observation.get("visibleRowCount") != 1):
        raise ActivationError("Native UI observation is outside scope or not unique.")
    if (not isinstance(expected_upload_sha256, str)
            or not re.fullmatch(r"[0-9a-f]{64}", expected_upload_sha256)):
        raise ActivationError("The owned upload receipt SHA-256 is missing or malformed.")
    capture = observation.get("captureMethod", {})
    review = observation.get("visualReview", {})
    if (capture.get("originalDisplayRestored") is not True
            or capture.get("cloudWrites") is not False
            or capture.get("eventReplayed") is not False
            or capture.get("valuesInferredFromOtherReceipts") is not False
            or review.get("observedFieldsMatchOriginalPixels") is not True
            or review.get("humanAttestationObtained") is not False
            or review.get("unseenFieldsReconstructed") is not False):
        raise ActivationError("UI capture or review provenance is incomplete.")

    screenshots = observation.get("screenshots")
    if not isinstance(screenshots, list) or len(screenshots) != 4:
        raise ActivationError("Exactly four original screenshot records are required.")
    screenshot_paths: set[str] = set()
    coverage: set[str] = set()
    screenshot_hashes: dict[str, str] = {}
    for screenshot in screenshots:
        if not isinstance(screenshot, Mapping):
            raise ActivationError("Screenshot receipt is malformed.")
        path = screenshot.get("path")
        if not isinstance(path, str) or path in screenshot_paths:
            raise ActivationError("Screenshot path is missing or duplicated.")
        screenshot_paths.add(path)
        content = _read_bound_file(screenshot_root, path, screenshot.get("sha256"))
        if not content.startswith(b"\x89PNG\r\n\x1a\n"):
            raise ActivationError("Original screenshot bytes are not PNG data.")
        supports = screenshot.get("supports")
        if not isinstance(supports, list) or any(not isinstance(value, str) for value in supports):
            raise ActivationError("Screenshot field coverage is malformed.")
        coverage.update(supports)
        screenshot_hashes[path] = screenshot["sha256"]
    if not EXPECTED_SCREENSHOT_COVERAGE <= coverage:
        raise ActivationError("Original screenshots do not cover the observed fields.")

    candidate = observation.get("correlationCandidate")
    if not isinstance(candidate, Mapping):
        raise ActivationError("Native UI correlation metadata is missing.")
    receipt_list = candidate.get("receipts")
    if (not isinstance(receipt_list, list) or len(receipt_list) != len(EXPECTED_RECEIPTS)
            or {str(item.get("path", "")).replace("\\", "/") for item in receipt_list if isinstance(item, Mapping)}
            != EXPECTED_RECEIPTS):
        raise ActivationError("Exactly the four reviewed source receipts must be referenced.")
    receipt_bytes: dict[str, bytes] = {}
    receipt_hashes: dict[str, str] = {}
    for entry in receipt_list:
        path = str(entry["path"]).replace("\\", "/")
        content = _read_bound_file(receipt_root, path, entry.get("sha256"))
        receipt_bytes[path] = content
        receipt_hashes[path] = entry["sha256"]
    try:
        saved_definition = json.loads(receipt_bytes["activation/readiness-1793506889686561800/definition.json"])
        saved_history = json.loads(receipt_bytes["increments/donation_events_001.csv/observation-01/history.json"])
        upload = json.loads(receipt_bytes["increments/donation_events_001.csv/upload/upload-result.json"])
        copy = json.loads(receipt_bytes["increments/donation_events_001.csv/bounded-monitor-01/native-copy-001.json"])
    except (ValueError, KeyError) as exc:
        raise ActivationError("A hash-bound source receipt is malformed.") from exc

    values = observation.get("observations")
    if (not isinstance(values, Mapping) or values.get("timeUtc") != candidate.get("activationTimeUtc")
            or values.get("subject") != subject or values.get("type") != FILE_CREATED
            or values.get("api") != "PutBlob" or type(values.get("contentLength")) is not int
            or values.get("contentLength") != expected_bytes or values.get("contentType") != "text/csv"
            or not isinstance(values.get("eventId"), str)):
        raise ActivationError("Displayed native event fields do not match the upload contract.")
    guid(values["eventId"])
    if (candidate.get("nativeRuleId") != rule_id or candidate.get("eventReferenceEntityId") != model_id
            or candidate.get("pipelineId") != pipeline_id
            or candidate.get("sourceParameterBinding") != {
                "kind": "EventFieldReference", "fieldName": "___source", "constant": False,
            }
            or candidate.get("subjectParameterBinding") != {
                "kind": "EventFieldReference", "fieldName": "___subject", "constant": False,
            }
            or candidate.get("typeParameterBinding") != {
                "kind": "EventFieldReference", "fieldName": "___type", "constant": False,
            }):
        raise ActivationError("Candidate metadata differs from the owned event/rule contract.")

    saved_projection, saved_bindings = _definition_projection(
        saved_definition, rule_id=rule_id, model_id=model_id, workspace_id=workspace_id,
        lakehouse_id=lakehouse_id, pipeline_id=pipeline_id,
    )
    current_projection, current_bindings = _definition_projection(
        current_definition, rule_id=rule_id, model_id=model_id, workspace_id=workspace_id,
        lakehouse_id=lakehouse_id, pipeline_id=pipeline_id,
    )
    if saved_projection != current_projection or saved_bindings != current_bindings:
        raise ActivationError("Fresh source/rule definition differs from the event-time definition.")

    activations = saved_history.get("activations")
    if (saved_history.get("totalCount") != 1 or not isinstance(activations, list)
            or len(activations) != 1):
        raise ActivationError("Event-time history does not prove one activation.")
    activation = activations[0]
    properties = activation.get("properties", {})
    prefix = "System.Action.FabricItem."
    source = properties.get(prefix + "Parameters.Source.String")
    activation_time = parse_time(activation.get("activationTime"))
    event_time = parse_time(values["timeUtc"])
    expected_source = f"/tenants/{tenant_id}/workspaces/{workspace_id}/items/{lakehouse_id}"
    if (activation_time != event_time or candidate.get("activationHistoryTotalCount") != 1
            or properties.get("System.RuleId") != rule_id
            or properties.get(prefix + "WorkspaceId") != workspace_id
            or properties.get(prefix + "ItemId") != pipeline_id
            or properties.get(prefix + "ItemType") != "Pipeline"
            or properties.get(prefix + "JobType") != "Pipeline"
            or properties.get(prefix + "Parameters.Subject.String") != subject
            or properties.get(prefix + "Parameters.Type.String") != FILE_CREATED
            or source != expected_source or not properties.get("System.RuleVersion")
            or properties.get("___id") != candidate.get("activationId")):
        raise ActivationError("Saved activation does not uniquely correlate to the displayed event.")
    if (upload.get("state") != "uploaded_unverified" or upload.get("filename") != "donation_events_001.csv"
            or upload.get("bytes") != expected_bytes or upload.get("uploadedBytesVerified") is not True
            or upload.get("sha256") != candidate.get("uploadedFileSha256")
            or upload.get("sha256") != expected_upload_sha256):
        raise ActivationError("Hash-bound upload receipt differs from the displayed file event.")
    if (copy.get("pipelineRunId") != candidate.get("pipelineRunId")
            or copy.get("activityRunId") != candidate.get("copyActivityRunId")
            or copy.get("status") != "Succeeded" or copy.get("activityType") != "Copy"
            or copy.get("output", {}).get("rowsRead") != 5000
            or copy.get("output", {}).get("rowsCopied") != 5000
            or copy.get("output", {}).get("dataRead") != expected_bytes):
        raise ActivationError("Hash-bound Copy receipt differs from the observed delivery.")
    return {
        "eventId": values["eventId"],
        "eventTimeUtc": values["timeUtc"],
        "eventType": values["type"],
        "eventApi": values["api"],
        "contentLength": values["contentLength"],
        "contentType": values["contentType"],
        "subject": values["subject"],
        "sourceFromBoundActivation": source,
        "activationId": properties["___id"],
        "activationRuleVersion": properties["System.RuleVersion"],
        "directEventIdInActivation": False,
        "definitionMatchedEventTimeAndCurrent": True,
        "fieldBindings": saved_bindings,
        "uploadSha256": upload["sha256"],
        "copyReceipt": copy,
        "screenshotSha256": screenshot_hashes,
        "receiptSha256": receipt_hashes,
    }


def validate_control_classification(
    classification: Mapping[str, Any], *, known_manual_job_ids: set[str],
) -> dict[str, Any]:
    """Require a separately recorded operating-session classification, not invokeType inference."""
    if (not isinstance(classification, Mapping)
            or classification.get("kind") != "coordinator-operational-attestation"
            or classification.get("scope") != "coordinator-session-only"
            or classification.get("manualPipelineRunTriggered") is not False
            or classification.get("incrementUploadOrReplayPerformed") is not False
            or classification.get("readOnlyInspectionOnly") is not True
            or classification.get("humanAttestation") is not False):
        raise ActivationError("Controlled-run classification is missing or out of scope.")
    if not isinstance(classification.get("coordinatorSessionId"), str) or not re.fullmatch(
        r"[0-9a-fA-F-]{36}", classification["coordinatorSessionId"],
    ):
        raise ActivationError("Coordinator session provenance is missing.")
    if not isinstance(classification.get("sourceMessageId"), str) or not classification["sourceMessageId"]:
        raise ActivationError("Coordinator classification source message is missing.")
    manual_ids = classification.get("knownManualControlJobIds")
    if (classification.get("manualControlIdsReviewed") is not True
            or not isinstance(manual_ids, list)
            or any(not isinstance(value, str) or not re.fullmatch(r"[0-9a-fA-F-]{36}", value)
                   for value in manual_ids)
            or len(set(manual_ids)) != len(manual_ids)
            or set(manual_ids) != known_manual_job_ids):
        raise ActivationError("Known manual-control job IDs were not explicitly reviewed.")
    return {
        "kind": classification["kind"],
        "scope": classification["scope"],
        "coordinatorSessionId": classification["coordinatorSessionId"],
        "sourceMessageId": classification["sourceMessageId"],
        "manualControlIdsReviewed": True,
        "knownManualControlJobIds": sorted(manual_ids),
        "manualPipelineRunTriggered": False,
        "incrementUploadOrReplayPerformed": False,
        "readOnlyInspectionOnly": True,
        "humanAttestation": False,
    }
