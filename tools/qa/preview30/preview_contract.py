"""Offline, fail-closed acceptance of privately captured Preview evidence.

This module never connects, submits a question, or changes a Fabric resource.
Provenance checks do not replace a reviewer's inspection of real service/UI
evidence. A signed-off checkbox without the referenced bytes is insufficient.
"""

from __future__ import annotations

import hashlib
import base64
import binascii
import json
import math
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

SCHEMA = "furusato-preview30-evaluation/v1"
STATES = ("planned", "implemented", "deployed", "pass", "fail", "blocked", "unsupported", "unverified")
SUPPORT = ("supported", "blocked", "unsupported", "pending")
SHA = re.compile(r"[0-9a-f]{64}\Z")
LIVE_ORIGINS = {"authenticated_api", "native_tool", "coordinator_browser"}
CONTEXT_KEYS = ("scope_sha256", "identity_sha256", "data_sha256", "prompts_sha256")


class EvidenceError(ValueError):
    pass


def encode(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(encode(value)).hexdigest()


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def timestamp(value: str) -> datetime:
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if result.tzinfo is None:
            raise ValueError("timezone missing")
        return result.astimezone(timezone.utc)
    except (AttributeError, TypeError, ValueError) as error:
        raise EvidenceError("A timezone-aware capture timestamp is required.") from error


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as error:
        raise EvidenceError(f"Cannot read evidence JSON: {path.name}") from error


def pointer(value: Any, path: str) -> Any:
    """JSON pointer; /@json decodes a native JSON-serialized argument/result."""
    if not isinstance(path, str) or not path.startswith("/") or path == "/":
        raise EvidenceError("An exact non-root JSON pointer is required.")
    try:
        for part in path[1:].split("/"):
            part = part.replace("~1", "/").replace("~0", "~")
            if part == "@json":
                value = json.loads(value)
            else:
                value = value[int(part)] if isinstance(value, list) else value[part]
    except (KeyError, IndexError, TypeError, ValueError) as error:
        raise EvidenceError("The cited JSON value does not exist.") from error
    return value


class PrivateStore:
    def __init__(self, root: Path):
        if not root.is_absolute():
            raise EvidenceError("Use an absolute private root outside every Git checkout.")
        self.root = root.resolve()
        self._outside_git(self.root)

    @staticmethod
    def _outside_git(path: Path) -> None:
        if any((parent / ".git").exists() for parent in (path, *path.parents)):
            raise EvidenceError("Live evidence and held-out material must stay outside Git.")

    def path(self, relative: str) -> Path:
        if not isinstance(relative, str) or not relative:
            raise EvidenceError("Missing private artifact path.")
        supplied = Path(relative)
        if supplied.is_absolute() or ".." in supplied.parts or ":" in relative:
            raise EvidenceError("Evidence paths must be contained relative paths.")
        target = (self.root / supplied).resolve()
        if not target.is_relative_to(self.root):
            raise EvidenceError("Artifact escapes the private evidence root.")
        self._outside_git(target)
        return target

    def write(self, relative: str, value: Any) -> str:
        target = self.path(relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as handle:
            handle.write(encode(value))
        return file_hash(target)

    def artifact(self, reference: dict) -> Path:
        path = self.path(reference.get("path", ""))
        if not SHA.fullmatch(str(reference.get("sha256", ""))) or not path.is_file():
            raise EvidenceError("Artifact or its SHA-256 is missing.")
        if file_hash(path) != reference["sha256"]:
            raise EvidenceError("Artifact SHA-256 does not match the captured bytes.")
        return path


def load_catalog(path: Path | None = None) -> dict:
    result = load_json(path or Path(__file__).with_name("cases.json"))
    if result.get("schema_version") != "furusato-preview30-cases/v1":
        raise EvidenceError("Unsupported case catalog.")
    seen = set()
    for case in result["cases"]:
        if case["id"] in seen or not case.get("checks") or not case.get("roles"):
            raise EvidenceError("Duplicate or incomplete case.")
        if len(set(case["checks"])) != len(case["checks"]):
            raise EvidenceError("Duplicate rubric check.")
        seen.add(case["id"])
    return result


def validator_fingerprint() -> str:
    root = Path(__file__).parent
    return digest({path.name: file_hash(path) for path in sorted(root.glob("*.py"))} | {
        name: file_hash(root / name) for name in ("cases.json", "evidence.schema.json")
    })


def scope_fingerprint(readiness: dict) -> str:
    return digest({key: readiness.get(key) for key in (
        "workspace_id", "folder_id", "portal_folder_id", "items", "folders", "forbidden_item_ids"
    )})


def verified_folder_scope(readiness: dict, store: PrivateStore) -> tuple[set, list[str]]:
    root, workspace = readiness.get("folder_id"), readiness.get("workspace_id")
    allowed, errors, pending = {root}, [], {}
    try:
        UUID(root)
    except (ValueError, TypeError, AttributeError):
        return set(), ["approved_root_folder_missing"]
    folders = readiness.get("folders", {})
    if not isinstance(folders, dict):
        return allowed, ["child_folder_registry_invalid"]
    for folder_id, folder in folders.items():
        try:
            UUID(folder_id)
            if folder_id == root or folder.get("workspace_id") != workspace or folder.get("newly_created") is not True:
                raise EvidenceError("Child folder is not an approved new scoped folder.")
            receipt = load_json(store.artifact(folder.get("receipt", {})))
            if (receipt.get("id") != folder_id or receipt.get("workspaceId") != workspace
                    or receipt.get("parentFolderId") != folder.get("parent_id")):
                raise EvidenceError("Native folder readback differs from its declared ancestry.")
            pending[folder_id] = folder["parent_id"]
        except (ValueError, KeyError, TypeError, EvidenceError):
            errors.append(f"child_folder_proof_invalid:{folder_id}")
    while pending:
        ready = [folder_id for folder_id, parent in pending.items() if parent in allowed]
        if not ready:
            errors.append("child_folder_ancestry_unproven_or_cyclic")
            break
        for folder_id in ready:
            allowed.add(folder_id)
            del pending[folder_id]
    return allowed, errors


def readiness_errors(readiness: dict, store: PrivateStore, *, questions: bool = False) -> list[str]:
    errors = []
    gate_path = store.path("live-gate.json")
    if gate_path.is_file():
        gate = load_json(gate_path)
        if gate.get("state") != "open" or gate.get("scope_sha256") != scope_fingerprint(readiness):
            errors.append("latest_live_gate_closed_or_unverified")
    for field in ("folder_mapping_verified", "read_only_queries_ready"):
        if readiness.get(field) is not True:
            errors.append(field)
    if questions and readiness.get("questions_authorized") is not True:
        errors.append("questions_not_authorized")
    try:
        for key in ("workspace_id", "folder_id"):
            UUID(readiness[key])
        timestamp(readiness["approved_at_utc"])
    except (KeyError, ValueError, TypeError, EvidenceError):
        errors.append("exact_scope_identity_or_approval_missing")
    if not readiness.get("portal_folder_id") or not readiness.get("approved_by"):
        errors.append("folder_mapping_approval_missing")
    items, ids = readiness.get("items", {}), {}
    if not isinstance(items, dict) or not items:
        return errors + ["allowlisted_items_missing"]
    forbidden = set(readiness.get("forbidden_item_ids", []))
    allowed_folders, folder_errors = verified_folder_scope(readiness, store)
    errors += folder_errors
    for role, item in items.items():
        try:
            UUID(item["id"])
            identity = (item.get("workspace_id"), item.get("folder_id"), item.get("type"))
            if item["id"] in forbidden or (item["id"] in ids and ids[item["id"]] != identity):
                raise ValueError()
            ids[item["id"]] = identity
            if (item.get("workspace_id") != readiness["workspace_id"]
                    or item.get("folder_id") not in allowed_folders
                    or not item.get("type") or item.get("ready") is not True):
                raise ValueError()
        except (KeyError, TypeError, ValueError):
            errors.append(f"item_scope_or_readiness:{role}")
    for field in ("scope_receipt", "source_readiness_receipt"):
        try:
            receipt = load_json(store.artifact(readiness.get(field, {})))
            if receipt.get("status") != "observed" or receipt.get("scope_sha256") != scope_fingerprint(readiness):
                errors.append(f"unobserved_or_wrong_scope:{field}")
            if timestamp(receipt.get("captured_at_utc")) < timestamp(readiness["approved_at_utc"]):
                errors.append(f"stale_receipt:{field}")
        except (EvidenceError, KeyError):
            errors.append(f"missing_readiness_receipt:{field}")
    if not SHA.fullmatch(str(readiness.get("identity_sha256", ""))):
        errors.append("identity_fingerprint_missing")
    return errors


def missing_data(value: Any) -> bool:
    if isinstance(value, dict):
        for key, item in value.items():
            field = key.lower()
            if field in {"request", "query", "question", "prompt", "input", "arguments"}:
                continue
            if field in {"error", "errors", "errorcode", "error_code"}:
                if "datanotavailable" in json.dumps(item, ensure_ascii=False).lower().replace(" ", ""):
                    return True
            if missing_data(item):
                return True
        return False
    if isinstance(value, list):
        return any(missing_data(v) for v in value)
    if isinstance(value, str):
        text = value.strip()
        if text.startswith(("{", "[")):
            try:
                return missing_data(json.loads(text))
            except ValueError:
                pass
        return (text.casefold() == "datanotavailable"
                or re.match(r"^(?:error\s*:\s*)?DataNotAvailable\s*[:\-]", text, re.I) is not None)
    return False


def truncated(value: Any) -> bool:
    if isinstance(value, dict):
        return any((key.lower() in {"truncated", "is_truncated", "has_more"} and item is True)
                   or truncated(item) for key, item in value.items())
    if isinstance(value, list):
        return any(truncated(item) for item in value)
    return False


def _nonempty(value: Any) -> bool:
    return value is not None and value != "" and value != [] and value != {}


def _success(value: Any, names: tuple[str, ...]) -> bool:
    return value is True or (isinstance(value, str) and value in names)


def gen2_definition_check(generation: Any, parts: Any) -> dict:
    """Check the documented readback shape, not a guessed authoring payload."""
    errors, limitations, decoded = [], [], {}
    if type(generation) is not int or generation != 2:
        errors.append("source_truth_mismatch:ontology_generation_not_two")
    if not isinstance(parts, list) or not parts:
        return {"errors": errors + ["gen2_definition_parts_missing"], "roundtrip_limitations": []}
    for part in parts:
        path = part.get("path", "") if isinstance(part, dict) else ""
        if not isinstance(path, str) or not path or path in decoded or part.get("payloadType") != "InlineBase64":
            errors.append("invalid_or_duplicate_native_definition_part")
            continue
        if path.casefold().startswith(("entitytypes/", "relationshiptypes/")):
            errors.append("source_truth_mismatch:legacy_entitytypes_json_is_not_gen2")
        try:
            text = base64.b64decode(part["payload"], validate=True).decode("utf-8-sig")
        except (binascii.Error, KeyError, TypeError, UnicodeError):
            errors.append("definition_part_not_valid_native_base64_text")
            continue
        decoded[path] = text
        if path.startswith("metrics/") and path.endswith(".tmdl"):
            if re.search(r"^\s*dialect\s*:\s*DAX\s*$", text, re.I | re.M):
                errors.append("source_truth_mismatch:explicit_dax_metric_forbidden")
            if re.search(r"^\s*(?:type\s*:\s*(?:enrichment|projected)|backingMeasure\b)", text, re.I | re.M):
                limitations.append({"path": path, "reason": "projected_or_enrichment_backingMeasure_lost_on_tmdl_roundtrip"})
    required = {".platform", "database.tmdl", "model.tmdl", "namespaces/default.tmdl"}
    if not required.issubset(decoded):
        errors.append("required_gen2_readback_parts_missing")
    if not re.search(r"^\s*compatibilityLevel\s*:\s*1000000\s*$", decoded.get("database.tmdl", ""), re.M):
        errors.append("source_truth_mismatch:gen2_compatibility_level")
    try:
        platform = json.loads(decoded.get(".platform", ""))
        if (not isinstance(platform, dict) or platform.get("metadata", {}).get("type") != "Ontology"
                or platform.get("config", {}).get("version") != "2.0"):
            errors.append("gen2_platform_metadata_mismatch")
    except ValueError:
        errors.append("gen2_platform_metadata_missing")
    if not re.search(r"^\s*ref namespace (?:default|'default')\s*$", decoded.get("model.tmdl", ""), re.M):
        errors.append("gen2_default_namespace_reference_missing")
    return {"errors": errors, "roundtrip_limitations": limitations}


def _trace_errors(proof: dict, body: Any) -> list[str]:
    trace, errors = proof.get("trace", {}), []
    if trace.get("executed") is not True or trace.get("scope_reviewed") is not True:
        errors.append("execution_or_scope_not_reviewed")
    if trace.get("language") not in {"SQL", "KQL", "DAX", "GQL"}:
        errors.append("executed_query_language_missing")
    if not trace.get("call_id") or not trace.get("reviewer"):
        errors.append("execution_call_identity_or_reviewer_missing")
    try:
        query_path = trace.get("query_pointer", "")
        if not query_path.startswith(("/request/", "/result/", "/response/", "/output/")):
            raise EvidenceError("Query must cite the actual request or native tool substep.")
        query = pointer(body, query_path)
        result_path = trace.get("result_pointer", "")
        if not result_path.startswith(("/response/", "/result/", "/output/")):
            raise EvidenceError("Result must be native output, not final prose.")
        if re.search(r"/(content|output_text|final_text|answer)(/|$)", result_path):
            raise EvidenceError("Final-answer prose cannot prove query execution.")
        result = pointer(body, result_path)
        if not isinstance(query, str) or not query.strip() or not isinstance(result, (dict, list)):
            raise EvidenceError("Executed query and structured native result required.")
        if trace.get("complete") is not True or truncated(result):
            errors.append("incomplete_returned_result")
        if missing_data(result):
            errors.append("DataNotAvailable_missing_evidence")
        if pointer(body, trace.get("call_id_pointer", "")) != trace.get("call_id"):
            errors.append("executed_call_id_not_in_native_evidence")
        execution = pointer(body, trace.get("execution_pointer", ""))
        if not _success(execution, ("completed", "Succeeded", "succeeded", "success")):
            errors.append("query_execution_not_observed")
    except EvidenceError as error:
        errors.append(str(error))
    return errors


def evidence_errors(proof: dict, kind: str, context: dict, readiness: dict, store: PrivateStore) -> tuple[list[str], Any]:
    errors, body = [], None
    if proof.get("kind") != kind:
        errors.append("wrong_evidence_kind")
    if proof.get("origin") not in LIVE_ORIGINS and kind not in {
        "artifact_check", "document_review", "rdf_file", "graph_scope", "comparison"
    }:
        errors.append("not_live_evidence")
    if proof.get("origin") in {"mock", "test_fixture", "legacy_ui"}:
        errors.append("mock_fixture_or_old_ui")
    if proof.get("context_sha256") != digest(context):
        errors.append("stale_or_different_context")
    try:
        captured = timestamp(proof.get("captured_at_utc"))
        if captured < timestamp(context["frozen_at_utc"]) or captured > datetime.now(timezone.utc):
            errors.append("stale_or_future_capture")
        path = store.artifact(proof.get("artifact", {}))
        if path.suffix.lower() == ".json":
            body = load_json(path)
            if missing_data(body):
                errors.append("DataNotAvailable_missing_evidence")
            if truncated(body):
                errors.append("truncated_evidence")
    except (EvidenceError, KeyError) as error:
        errors.append(str(error))
    ids = proof.get("item_ids", [])
    allowed = {value["id"] for value in readiness.get("items", {}).values() if "id" in value}
    if (kind not in {"artifact_check", "document_review", "rdf_file", "comparison", "graph_scope"}
            and not ids):
        errors.append("item_identity_missing")
    if not set(ids).issubset(allowed) or set(ids) & set(readiness.get("forbidden_item_ids", [])):
        errors.append("unapproved_or_forbidden_item")
    review = proof.get("review", {})
    if (not review.get("reviewer") or not review.get("note")
            or review.get("artifact_sha256") != proof.get("artifact", {}).get("sha256")):
        errors.append("review_not_bound_to_artifact")
    if kind in {"source_query", "execution_trace"}:
        errors += _trace_errors(proof, body)
    elif kind == "native_response":
        try:
            answer_path = proof.get("final_text_pointer", "")
            if not answer_path.startswith(("/response/", "/result/", "/output/")):
                raise EvidenceError("Final answer must come from the returned native response.")
            answer = pointer(body, answer_path)
            if not isinstance(answer, str) or not answer.strip():
                errors.append("native_answer_missing")
            if proof.get("terminal_status") != "completed":
                errors.append("native_answer_not_completed")
        except EvidenceError as error:
            errors.append(str(error))
    elif kind == "ui_capture":
        from proof_files import capture_errors
        errors += capture_errors(proof, store)
    elif kind == "upload_receipt":
        attachments = proof.get("attachments", [])
        if not 1 <= len(attachments) <= 10:
            errors.append("attachment_count_out_of_bounds")
        if (not proof.get("conversation_id") or proof.get("actual_upload") is not True
                or review.get("no_heldout_or_secrets") is not True):
            errors.append("upload_session_or_content_review_missing")
        for item in attachments:
            try:
                artifact = store.artifact(item)
                if not 0 < artifact.stat().st_size <= 5242880:
                    errors.append("attachment_size_out_of_bounds")
                if item.get("size_bytes") != artifact.stat().st_size or not item.get("upload_id"):
                    errors.append("uploaded_bytes_or_receipt_missing")
            except EvidenceError as error:
                errors.append(str(error))
    elif kind == "mcp_tools":
        try:
            tools = pointer(body, proof.get("tools_pointer", ""))
            if (proof.get("origin") != "native_tool" or not isinstance(tools, list)
                    or not tools or any(not tool.get("name") for tool in tools)):
                errors.append("native_tool_list_missing")
        except (EvidenceError, TypeError, AttributeError) as error:
            errors.append(str(error))
    elif kind == "artifact_check":
        try:
            document = store.artifact(proof.get("document_artifact", {}))
            if (not isinstance(body, dict) or body.get("document_sha256") != file_hash(document)
                    or body.get("local_state") != "pass"):
                errors.append("document_integrity_check_not_passed")
            if body.get("external_unverified"):
                errors.append("external_links_unverified")
        except (EvidenceError, AttributeError) as error:
            errors.append(str(error))
    return errors, body


def _feature_errors(case: dict, record: dict, proofs: dict, bodies: dict, oracle: dict) -> list[str]:
    """Extra numerical/structural checks, never a substitute for the rubric."""
    errors, key = [], case["id"]
    if key == "UI01":
        try:
            generation = pointer(bodies["item"], record.get("generation_pointer", ""))
            parts = pointer(bodies["readback"], record.get("definition_parts_pointer", ""))
            errors += gen2_definition_check(generation, parts)["errors"]
        except EvidenceError as error:
            errors.append(f"gen2_native_identity_unverified:{error}")
    if key == "UI02":
        try:
            functional = record.get("functional_readback", {})
            status = pointer(bodies["functional"], functional.get("status_pointer", ""))
            if not _success(status, ("completed", "Succeeded", "succeeded", "success")):
                errors.append("source_truth_mismatch:native_binding_instances_failed")
            else:
                returned = pointer(bodies["functional"], functional.get("rows_pointer", ""))
                if not isinstance(returned, (list, dict)) or not returned:
                    errors.append("native_bound_instance_rows_unverified")
        except (EvidenceError, KeyError, TypeError) as error:
            errors.append(f"native_instances_readback_unverified:{error}")
    if key in {"GRAPH01", "GRAPH02"}:
        from source_oracle import graph_expectations
        try:
            scope = bodies["scope"]["scope"]
            expected = graph_expectations(oracle, scope)
            if key == "GRAPH02":
                for metric in ("node_count", "edge_count"):
                    actual = pointer(bodies["gql"], record.get("graph_assertions", {}).get(metric, ""))
                    if type(actual) is not int or actual != expected[metric]:
                        errors.append(f"source_truth_mismatch:graph.{metric}")
        except (EvidenceError, KeyError, TypeError) as error:
            errors.append(f"graph_scope_or_result_unverified:{error}")
    if key == "GRAPH03":
        try:
            values = record.get("freshness", {})
            source = pointer(bodies["source"], values.get("source_watermark_pointer", ""))
            materialized = pointer(bodies["materialization"], values.get("graph_watermark_pointer", ""))
            if not _nonempty(source) or source != materialized:
                errors.append("source_truth_mismatch:graph_watermark")
            ready = pointer(bodies["ready"], values.get("ready_pointer", ""))
            if not _success(ready, ("Ready", "Succeeded", "SucceededWithWarnings")):
                errors.append("graph_not_ready")
            if timestamp(proofs["gql"]["captured_at_utc"]) < timestamp(proofs["materialization"]["captured_at_utc"]):
                errors.append("gql_predates_materialization")
        except (EvidenceError, KeyError, TypeError) as error:
            errors.append(f"graph_freshness_unverified:{error}")
    if key == "VERSION01":
        try:
            selector = record.get("definition_content_pointer", "")
            definitions = [pointer(bodies[role], selector) for role in ("saved", "modified", "restored")]
            if not all(isinstance(value, (list, dict)) for value in definitions):
                errors.append("version_definition_content_missing")
            elif definitions[0] == definitions[1] or definitions[0] != definitions[2]:
                errors.append("source_truth_mismatch:version_restore")
        except EvidenceError as error:
            errors.append(str(error))
    if key in {"RDF01", "RDF02"}:
        try:
            options = record.get("rdf", {})
            if pointer(bodies["empty"], options.get("empty_entities_pointer", "")) != []:
                errors.append("rdf_target_not_empty")
            summary = pointer(bodies["summary"], options.get("summary_pointer", ""))
            if not isinstance(summary, dict) or any(
                not isinstance(summary.get(field), list) for field in ("preserved", "transformed", "unsupported")
            ):
                errors.append("rdf_loss_transform_inventory_missing")
            if key == "RDF02" and proofs["export"].get("format") not in {"TTL", "RDF"}:
                errors.append("owl_export_not_supported")
        except (EvidenceError, KeyError, TypeError) as error:
            errors.append(f"rdf_import_unverified:{error}")
    if key == "METRIC01":
        try:
            options = record.get("metric_reconciliation", {})
            model_result = pointer(bodies["dax"], options.get("dax_pointer", ""))
            source_result = pointer(bodies["source"], options.get("source_pointer", ""))
            if not _nonempty(model_result) or model_result != source_result:
                errors.append("source_truth_mismatch:metric")
            binding = record.get("metric_binding", {})
            surface = binding.get("surface")
            if surface not in {"native_ui", "documented_public_contract"}:
                errors.append("tmdl_export_is_not_projected_metric_link_evidence")
            if surface == "native_ui" and proofs["metric"].get("origin") != "coordinator_browser":
                errors.append("native_ui_metric_not_captured_by_coordinator")
            if surface == "documented_public_contract":
                reference = binding.get("contract_reference", "")
                if not reference.startswith("https://learn.microsoft.com/"):
                    errors.append("public_metric_contract_reference_missing")
            metric_type = pointer(bodies["metric"], binding.get("metric_type_pointer", ""))
            if not isinstance(metric_type, str) or metric_type.casefold() not in {"enrichment", "projected"}:
                errors.append("source_truth_mismatch:dax_backed_metric_not_projection_or_enrichment")
            backing = pointer(bodies["metric"], binding.get("backing_measure_pointer", ""))
            table = pointer(bodies["model"], binding.get("source_table_pointer", ""))
            measure = pointer(bodies["model"], binding.get("source_measure_pointer", ""))
            expression = pointer(bodies["model"], binding.get("source_dax_pointer", ""))
            if (not isinstance(backing, dict) or not table or not measure
                    or backing.get("table") != table or backing.get("measure") != measure
                    or not isinstance(expression, str) or not expression.strip()):
                errors.append("source_truth_mismatch:metric_backing_measure_identity")
        except EvidenceError as error:
            errors.append(str(error))
    if key in {"ATTACH01", "ATTACH02"}:
        answer = proofs.get("answer", proofs.get("read", {}))
        if not answer.get("conversation_id") or proofs["upload"].get("conversation_id") != answer.get("conversation_id"):
            errors.append("attachment_read_not_in_upload_conversation")
    return errors


def assess_case(case: dict, record: dict, manifest: dict, readiness: dict, store: PrivateStore, oracle: dict) -> dict:
    state, support = record.get("state"), record.get("support")
    result = {
        "case_id": case["id"], "repeat": record.get("repeat"),
        "category": case["category"], "critical": case["critical"],
        "requested_state": state, "state": state, "support": support,
        "reason": record.get("reason", ""), "errors": [], "ai_scored": False,
    }
    errors = result["errors"]
    if state not in STATES or support not in SUPPORT:
        errors.append("invalid_state_or_support")
    if not record.get("reason"):
        errors.append("state_reason_required")
    if state in {"blocked", "unsupported", "unverified"} and not record.get("blocker"):
        errors.append("missing_explicit_blocker")
    if state == "unsupported" and support != "unsupported":
        errors.append("unsupported_case_must_remain_in_inventory")
    if state == "unsupported":
        proof = manifest.get("evidence", {}).get(record.get("support_evidence"), {})
        problems, body = evidence_errors(proof, "capability_probe", manifest["context"], readiness, store)
        errors += [f"unsupported_claim:{problem}" for problem in problems]
        try:
            observed = pointer(body, record.get("unsupported_pointer", ""))
            if observed is not False and observed not in ("NotSupported", "FeatureNotSupported", "Unsupported"):
                errors.append("unsupported_capability_not_observed")
        except EvidenceError as error:
            errors.append(str(error))
        if errors:
            result["support"] = "pending"
    if state not in {"pass", "fail"}:
        if errors:
            result["state"] = "unverified"
        return result
    context = manifest["context"]
    errors += readiness_errors(readiness, store, questions=case["category"] == "ai")
    if support != "supported":
        errors.append("cannot_score_unsupported_case")
    if context.get("scope_sha256") != scope_fingerprint(readiness):
        errors.append("scope_fingerprint_mismatch")
    if context.get("identity_sha256") != readiness.get("identity_sha256"):
        errors.append("principal_fingerprint_mismatch")
    for field in (*CONTEXT_KEYS, "configuration_sha256"):
        if not SHA.fullmatch(str(context.get(field, ""))):
            errors.append(f"missing_context_fingerprint:{field}")
    if context.get("data_sha256") != digest(oracle):
        errors.append("oracle_fingerprint_mismatch")
    required_items = set(case.get("required_items", []))
    if not required_items.issubset(readiness.get("items", {})):
        errors.append("required_item_not_ready")
    roles, bodies, proofs, languages = record.get("evidence", {}), {}, {}, set()
    if set(roles) != set(case["roles"]):
        errors.append("evidence_roles_missing_or_changed")
    for role, kind in case["roles"].items():
        proof = manifest.get("evidence", {}).get(roles.get(role), {})
        proofs[role] = proof
        problems, bodies[role] = evidence_errors(proof, kind, context, readiness, store)
        errors += [f"{role}:{problem}" for problem in problems]
        if kind in {"source_query", "execution_trace"}:
            languages.add(proof.get("trace", {}).get("language"))
    observed_ids = {identity for proof in proofs.values() for identity in proof.get("item_ids", [])}
    expected_ids = {readiness.get("items", {}).get(role, {}).get("id") for role in required_items}
    if not expected_ids.issubset(observed_ids):
        errors.append("required_item_identity_not_in_case_evidence")
    if not set(case.get("required_languages", [])).issubset(languages):
        errors.append("required_executed_language_missing")
    checks = record.get("checks", {})
    if set(checks) != set(case["checks"]):
        errors.append("rubric_checks_missing_or_changed")
    decisions = []
    for name in case["checks"]:
        check = checks.get(name, {})
        verdict = check.get("state")
        decisions.append(verdict)
        if verdict not in {"pass", "fail"} or not check.get("reason") or not check.get("citations"):
            errors.append(f"unreviewed_check:{name}")
        for citation in check.get("citations", []):
            role = citation.get("role")
            try:
                if role not in proofs:
                    raise EvidenceError("Citation role is not part of the case.")
                if proofs[role].get("kind") in {"ui_capture", "rdf_file"}:
                    if citation.get("sha256") != proofs[role].get("artifact", {}).get("sha256"):
                        raise EvidenceError("Byte-artifact citation does not bind the reviewed file.")
                elif not _nonempty(pointer(bodies[role], citation.get("pointer", ""))):
                    raise EvidenceError("Cited evidence is empty.")
            except EvidenceError as error:
                errors.append(f"{name}:{error}")
    for key in case.get("oracle_assertions", []):
        claim = record.get("oracle_assertions", {}).get(key, {})
        try:
            role = claim.get("role")
            if case["roles"].get(role) != "source_query":
                raise EvidenceError("Oracle assertion must cite a live source query.")
            expected: Any = oracle
            for part in key.split("."):
                expected = expected[part]
            actual = pointer(bodies[role], claim.get("pointer", ""))
            if type(actual) is not type(expected) or actual != expected:
                errors.append(f"source_truth_mismatch:{key}")
        except (EvidenceError, KeyError, TypeError):
            errors.append(f"oracle_evidence_missing:{key}")
    errors += _feature_errors(case, record, proofs, bodies, oracle)
    if case["category"] == "ai":
        answer = proofs.get("answer", {})
        if (record.get("fresh_conversation") is not True or not record.get("conversation_id")
                or record.get("conversation_id") != answer.get("conversation_id")
                or answer.get("conversation_identity_kind") != "backend_conversation"
                or record.get("submission_count") != 1):
            errors.append("fresh_backend_conversation_unproven")
        if (record.get("prompt_sha256") != manifest.get("prompt_hashes", {}).get(case["id"])
                or not SHA.fullmatch(str(record.get("prompt_sha256", "")))):
            errors.append("frozen_prompt_not_verified")
        if context.get("prompts_sha256") != digest(manifest.get("prompt_hashes", {})):
            errors.append("prompt_inventory_fingerprint_mismatch")
        try:
            actual_prompt = pointer(bodies.get("answer"), answer.get("question_pointer", ""))
            if (not isinstance(actual_prompt, str)
                    or hashlib.sha256(actual_prompt.encode("utf-8")).hexdigest() != record.get("prompt_sha256")):
                errors.append("submitted_prompt_differs_from_frozen_prompt")
            if pointer(bodies.get("answer"), answer.get("conversation_id_pointer", "")) != record.get("conversation_id"):
                errors.append("conversation_identity_not_in_native_evidence")
            response_id = pointer(bodies.get("answer"), answer.get("response_id_pointer", ""))
            trace_response_id = pointer(bodies.get("trace"), proofs.get("trace", {}).get("response_id_pointer", ""))
            if not _nonempty(response_id) or response_id != trace_response_id:
                errors.append("query_trace_not_correlated_with_native_answer")
            if proofs.get("trace", {}).get("trace", {}).get("all_native_calls_reviewed") is not True:
                errors.append("native_trace_review_incomplete")
        except EvidenceError as error:
            errors.append(str(error))
        if proofs.get("upload") and proofs["upload"].get("conversation_id") != answer.get("conversation_id"):
            errors.append("attachment_not_in_answer_conversation")
        if (record.get("configuration_before_sha256") != context.get("configuration_sha256")
                or record.get("configuration_after_sha256") != context.get("configuration_sha256")):
            errors.append("configuration_drift")
    if not record.get("reviewer"):
        errors.append("case_reviewer_missing")
    if state == "fail" and "fail" not in decisions and not any(e.startswith("source_truth_mismatch:") for e in errors):
        errors.append("failure_without_failed_check")
    if errors:
        # Numeric mismatches are actual failures only when all evidence gates
        # succeeded; missing source data is never converted into a zero score.
        if all(item.startswith("source_truth_mismatch:") for item in errors):
            result["state"] = "fail"
        else:
            result["state"] = "unverified"
    else:
        result["state"] = "fail" if "fail" in decisions else "pass"
    result["ai_scored"] = case["category"] == "ai" and result["state"] in {"pass", "fail"}
    return result


def report(manifest: dict, readiness: dict, store: PrivateStore, oracle: dict, catalog: dict | None = None) -> dict:
    catalog = catalog or load_catalog()
    if manifest.get("schema_version") != SCHEMA or manifest.get("catalog_sha256") != digest(catalog):
        raise EvidenceError("Manifest schema or frozen catalog hash differs.")
    if not isinstance(manifest.get("context"), dict):
        raise EvidenceError("Manifest context is required.")
    timestamp(manifest["context"].get("frozen_at_utc"))
    repeats = manifest["context"].get("ai_repeats")
    if type(repeats) is not int or repeats < catalog["policy"]["ai_repeats"]:
        raise EvidenceError("Freeze at least three repetitions for every stochastic case.")
    cases = {case["id"]: case for case in catalog["cases"]}
    expected = {(key, repeat) for key, case in cases.items()
                for repeat in range(1, (repeats if case["category"] == "ai" else 1) + 1)}
    supplied = [(record.get("case_id"), record.get("repeat")) for record in manifest.get("records", [])]
    if len(supplied) != len(set(supplied)) or set(supplied) != expected:
        raise EvidenceError("Every case/repeat slot must remain present exactly once.")
    original = manifest.get("original_inventory", {})
    if (original.get("question_count") != 10 or original.get("condition_count") != 84
            or original.get("independent_hidden") is not False):
        raise EvidenceError("Keep the public original 10/84 inventory intact and labelled.")
    routes = original.get("routing_applicability", {})
    if set(routes) != {f"T{index:02}" for index in range(1, 11)}:
        raise EvidenceError("Disclose routing applicability for every original question.")
    for route in routes.values():
        if route.get("support") not in SUPPORT or not route.get("reason"):
            raise EvidenceError("Do not silently exclude original engine-routing requirements.")
    assessments = [assess_case(cases[r["case_id"]], r, manifest, readiness, store, oracle)
                   for r in manifest["records"]]
    current_validator = validator_fingerprint()
    validator_matches = manifest.get("validator_sha256") == current_validator
    if not validator_matches:
        for assessment in assessments:
            if assessment["requested_state"] in {"pass", "fail"}:
                assessment["errors"].append("validator_changed_after_freeze")
                assessment.update(state="unverified", ai_scored=False)
    conversations = Counter(r.get("conversation_id") for r in manifest["records"]
                            if cases[r["case_id"]]["category"] == "ai" and r.get("conversation_id"))
    for raw, assessment in zip(manifest["records"], assessments):
        if conversations.get(raw.get("conversation_id"), 0) > 1:
            assessment["errors"].append("conversation_reused_across_independent_slots")
            assessment.update(state="unverified", ai_scored=False)
    states = {state: sum(a["state"] == state for a in assessments) for state in STATES}
    scored = [a for a in assessments if a["ai_scored"]]
    ai_pass = sum(a["state"] == "pass" for a in scored)
    measurements, source_failures, unavailable = [], [], []
    allowed_ids = {item.get("id") for item in readiness.get("items", {}).values()}
    for proof in manifest.get("evidence", {}).values():
        relevant = (
            proof.get("context_sha256") == digest(manifest["context"])
            and proof.get("origin") in LIVE_ORIGINS
            and bool(proof.get("item_ids"))
            and set(proof.get("item_ids", [])).issubset(allowed_ids)
        )
        try:
            relevant = relevant and timestamp(proof.get("captured_at_utc")) >= timestamp(manifest["context"]["frozen_at_utc"])
            artifact = store.artifact(proof.get("artifact", {}))
        except EvidenceError:
            continue
        if not relevant:
            continue
        if artifact.suffix.lower() == ".json":
            body = load_json(artifact)
            if missing_data(body):
                unavailable.append(proof["artifact"]["sha256"])
            error_pointer = proof.get("trace", {}).get("error_pointer")
            if error_pointer:
                try:
                    actual_error = pointer(body, error_pointer)
                    if _nonempty(actual_error) and not missing_data(actual_error):
                        source_failures.append({
                            "artifact_sha256": proof["artifact"]["sha256"],
                            "error_pointer": error_pointer, "language": proof["trace"].get("language"),
                        })
                except EvidenceError:
                    pass
        measurement = proof.get("measurement", {})
        if measurement:
            value = measurement.get("latency_ms")
            if (measurement.get("kind") == "observed"
                    and type(value) in {int, float} and math.isfinite(value) and value >= 0):
                measurements.append({"kind": "client_elapsed", "latency_ms": value,
                                     "artifact_sha256": proof["artifact"]["sha256"]})
    # Capacity is absent unless actual independently correlated telemetry is
    # supplied. No CU is inferred from elapsed time, token counts or SKU.
    capacity = []
    for sample in manifest.get("capacity_measurements", []):
        if sample.get("kind") != "observed" or not sample.get("unit") or not sample.get("operation_id"):
            raise EvidenceError("Only measured, correlated capacity telemetry is admissible.")
        artifact = store.artifact(sample.get("artifact", {}))
        if type(sample.get("value")) not in {int, float} or not math.isfinite(sample["value"]) or sample["value"] < 0:
            raise EvidenceError("Invalid measured capacity value.")
        body = load_json(artifact)
        if (sample.get("context_sha256") != digest(manifest["context"])
                or pointer(body, sample.get("value_pointer", "")) != sample["value"]
                or pointer(body, sample.get("unit_pointer", "")) != sample["unit"]
                or pointer(body, sample.get("operation_id_pointer", "")) != sample["operation_id"]):
            raise EvidenceError("Capacity measurement is not bound to actual current-run telemetry.")
        capacity.append(sample)
    supported = [a for a in assessments if a["support"] == "supported"]
    supported_ai = [a for a in supported if a["category"] == "ai"]
    ai_support_pending = any(a["category"] == "ai" and a["support"] == "pending" for a in assessments)
    ai_complete = bool(scored) and len(scored) == len(supported_ai) and not ai_support_pending
    return {
        "schema_version": "furusato-preview30-report/v1", "generated_at_utc": utc_now(),
        "context": manifest["context"], "catalog_sha256": digest(catalog),
        "validator_sha256": current_validator, "validator_matches_frozen_plan": validator_matches,
        "original_inventory": original, "case_count": len(cases), "requested_slots": len(expected),
        "supported_requested_slots": len(supported), "state_counts": states,
        "supported_pass": sum(a["state"] == "pass" for a in supported),
        "supported_fail": sum(a["state"] == "fail" for a in supported),
        "supported_missing_evidence": sum(a["state"] not in {"pass", "fail"} for a in supported),
        "ai": {"scored_questions": len(scored), "pass": ai_pass,
               "accuracy": ai_pass / len(scored) if ai_complete else None,
               "supported_requested_questions": len(supported_ai),
               "missing_supported_questions": len(supported_ai) - len(scored),
               "aggregate_withheld_until_supported_inventory_complete": not ai_complete,
               "requested_questions": sum(c["category"] == "ai" for c in cases.values()) * repeats,
               "score_label": "evidence-complete factual acceptance; not structural tests"},
        "latency_measurements": measurements, "capacity_measurements": capacity,
        "source_query_failures": source_failures,
        "data_not_available_artifacts": sorted(set(unavailable)),
        "inventory": assessments, "workstream_complete": False,
    }


def compare(baseline: dict, candidate: dict, history: list[dict] | None = None) -> dict:
    errors, regression = [], []
    for key in (*CONTEXT_KEYS, "ai_repeats"):
        if baseline["context"].get(key) != candidate["context"].get(key):
            errors.append(f"comparison_context_changed:{key}")
    if baseline.get("catalog_sha256") != candidate.get("catalog_sha256"):
        errors.append("comparison_rubric_changed")
    if (baseline.get("validator_sha256") != candidate.get("validator_sha256")
            or not baseline.get("validator_matches_frozen_plan")
            or not candidate.get("validator_matches_frozen_plan")):
        errors.append("comparison_validator_changed")
    for key in ("question_count", "condition_count", "independent_hidden", "routing_applicability", "suite_sha256"):
        if baseline.get("original_inventory", {}).get(key) != candidate.get("original_inventory", {}).get(key):
            errors.append(f"original_inventory_or_applicability_changed:{key}")
    old = {(r["case_id"], r["repeat"]): r for r in baseline["inventory"]}
    new = {(r["case_id"], r["repeat"]): r for r in candidate["inventory"]}
    if set(old) != set(new):
        errors.append("comparison_inventory_changed")
    for key, row in new.items():
        previous = old.get(key, {})
        if row["support"] != previous.get("support"):
            errors.append(f"supported_denominator_changed:{key}")
        if previous.get("state") == "pass" and row["state"] != "pass":
            regression.append(list(key))
        if row.get("critical") and row["state"] == "fail":
            errors.append(f"critical_truth_failure:{key}")
    for arm in (baseline, candidate):
        if not arm["ai"]["scored_questions"]:
            errors.append("no_evidence_complete_questions")
        if arm["supported_missing_evidence"]:
            errors.append("incomplete_supported_inventory")
        if arm.get("original_inventory", {}).get("state") not in {"pass", "fail"}:
            errors.append("original_regression_not_evaluated")
    if (baseline.get("original_inventory", {}).get("state") == "pass"
            and candidate.get("original_inventory", {}).get("state") != "pass"):
        regression.append(["original10", "all84conditions"])
    previous_failures = [r.get("failure_fingerprint") for r in (history or [])]
    stop = len(history or []) >= 2 or any(
        value and previous_failures.count(value) >= 2 for value in previous_failures
    )
    if stop:
        errors.append("bounded_improvement_stop")
    return {
        "decision": "stop" if stop else "reject" if regression or any(
            e.startswith("critical_truth_failure:") for e in errors
        ) else "blocked" if errors else "eligible_for_coordinator_review",
        "errors": sorted(set(errors)), "regressions": regression,
        "candidate_changes_owned_by": "coordinator", "automatic_promotion": False,
    }


def empty_manifest(catalog: dict, oracle: dict, frozen_at_utc: str | None = None) -> dict:
    return {
        "schema_version": SCHEMA, "catalog_sha256": digest(catalog),
        "validator_sha256": validator_fingerprint(),
        "context": {"frozen_at_utc": frozen_at_utc or utc_now(), "campaign_id": "readiness-pending",
                    "scope_sha256": None, "identity_sha256": None, "data_sha256": digest(oracle),
                    "prompts_sha256": None, "configuration_sha256": None,
                    "ai_repeats": catalog["policy"]["ai_repeats"]},
        "original_inventory": {
            "question_count": 10, "condition_count": 84, "independent_hidden": False,
            "state": "blocked",
            "routing_applicability": {f"T{i:02}": {
                "support": "pending", "reason": "Architecture and native query observability not yet verified."
            } for i in range(1, 11)},
        },
        "prompt_hashes": {}, "evidence": {}, "capacity_measurements": [],
        "records": [{
            "case_id": case["id"], "repeat": repeat, "state": "blocked", "support": "pending",
            "reason": "Implementation is locally testable; no live acceptance is claimed.",
            "blocker": "Exact authorized scope, runtime readiness and native/UI evidence pending.",
            "evidence": {}, "checks": {},
        } for case in catalog["cases"]
            for repeat in range(1, (catalog["policy"]["ai_repeats"] if case["category"] == "ai" else 1) + 1)],
    }


def capture_plan_report(plan: dict, store: PrivateStore, manifest: dict | None = None,
                        readiness: dict | None = None) -> dict:
    """Track real-view coverage separately; a checklist entry is not proof."""
    if plan.get("schemaVersion") != 1:
        raise EvidenceError("Unsupported private capture-plan schema.")
    requested, supplied = plan.get("requestedCaptures", []), plan.get("verifiedCaptures", [])
    if not isinstance(requested, list) or not requested or not isinstance(supplied, list):
        raise EvidenceError("A capture plan requires an explicit requested-view inventory.")
    identities = [item.get("id") for item in requested]
    if any(not isinstance(key, str) or not key for key in identities) or len(set(identities)) != len(identities):
        raise EvidenceError("Requested capture IDs must be unique and nonempty.")
    declared, supplementary, seen = {}, [], set()
    for item in supplied:
        key = item.get("id") if isinstance(item, dict) else item
        if not isinstance(key, str) or not key or key in seen:
            raise EvidenceError("Capture declarations must have unique nonempty identities.")
        seen.add(key)
        if key in identities:
            declared[key] = item
        else:
            supplementary.append({
                "capture_id": key, "state": "unverified",
                "declared_status": item.get("status") if isinstance(item, dict) else None,
                "counts_toward_required_views": False,
                "reason": "Supplementary observation; it does not replace an approved required view.",
            })
    views = []
    for request in requested:
        key, errors = request["id"], []
        row = {"capture_id": key, "chapter": request.get("chapter"), "state": "blocked", "errors": errors}
        declaration = declared.get(key)
        if declaration is None:
            errors.append("real_capture_action_outcome_and_readback_missing")
        elif not isinstance(declaration, dict):
            errors.append("verified_label_is_not_native_evidence")
            row["state"] = "unverified"
        elif manifest is None or readiness is None:
            errors.append("frozen_context_and_readiness_missing")
            row["state"] = "unverified"
        else:
            errors += readiness_errors(readiness, store)
            context = manifest.get("context", {})
            if (context.get("scope_sha256") != scope_fingerprint(readiness)
                    or context.get("identity_sha256") != readiness.get("identity_sha256")):
                errors.append("capture_context_identity_mismatch")
            bodies, proofs = {}, {}
            for role, kind in (("capture", "ui_capture"), ("readback", "definition"), ("action", "operation_receipt")):
                proof = manifest.get("evidence", {}).get(declaration.get(f"{role}_proof"), {})
                proofs[role] = proof
                problems, bodies[role] = evidence_errors(proof, kind, context, readiness, store)
                errors += [f"{role}:{problem}" for problem in problems]
            try:
                if not _nonempty(pointer(bodies["readback"], declaration.get("readback_pointer", ""))):
                    errors.append("authoritative_readback_empty")
                outcome = pointer(bodies["action"], declaration.get("action_outcome_pointer", ""))
                if not _success(outcome, ("observed", "completed", "Succeeded", "succeeded", "success")):
                    errors.append("associated_action_outcome_not_observed")
                target_id = declaration.get("item_id")
                if not target_id or any(target_id not in proof.get("item_ids", []) for proof in proofs.values()):
                    errors.append("capture_action_readback_item_identity_mismatch")
            except EvidenceError as error:
                errors.append(str(error))
            row["state"] = "unverified" if errors else "pass"
        views.append(row)
    verified = sum(row["state"] == "pass" for row in views)
    return {
        "schema_version": "furusato-preview30-capture-inventory/v1",
        "generated_at_utc": utc_now(), "plan_sha256": digest(plan),
        "declared_plan_state": plan.get("state"), "required_views": len(requested),
        "declared_verified_entries": len(supplied), "verified_views": verified,
        "declared_required_entries": len(declared),
        "supplementary_observations": supplementary,
        "missing_or_unverified_views": len(requested) - verified,
        "state": "pass" if verified == len(requested) else "blocked",
        "authentication_surfaces": {
            "top_level_canvas": plan.get("canvasAuthentication", "unverified"),
            "isolated_capture_browser": plan.get("isolatedPlaywrightAuthentication", "unverified"),
            "canvas_limitations": plan.get("canvasLimitation", ""),
            "top_level_authentication_is_not_ontology_ui_evidence": True,
        },
        "views": views, "ai_accuracy": None,
        "coverage_only_not_full_lab_acceptance": True, "workstream_complete": False,
    }
