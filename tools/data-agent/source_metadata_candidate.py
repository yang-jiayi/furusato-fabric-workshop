"""Compile a pinned, offline source-metadata candidate; never submit it."""
from __future__ import annotations

import base64
import copy
import hashlib
import json
import re
from typing import Any

from evaluate_native import definition_digest
from measured_contract_profile import LIMIT, stage_sources
from source_grounded_profile import inline_part

PREVIOUS_AGENT_SHA256 = "e3fff7d4ee3c257726fb0cf202e8df06f57aa056eddfe4a208bbcebd968d5060"
EXPECTED_AGENT_SHA256 = "0936122c5fa15b4e5f70da9cae8827cdff6782961a7fd56772318151f0370329"
EXPECTED_MODEL_SHA256 = "8803a08b804557218d42e4a02f95af31eebbacf834c6d3fc12d0ec01f9efd8fc"
MODEL_PATH = "definition/tables/寄附.tmdl"
GLOBAL_SCOPE_REWRITE_BEFORE = (
    "- Before delegation, carry shared payment/category/geography/period/population constraints into "
    "EVERY applicable subquestion, including rankings, unless the user explicitly changes scope. Send "
    "each subquestion with those constraints, grain and required ID/name pairs; do not request an "
    "unfiltered stored rank for a filtered population. A separate filtered total does not scope another "
    "query. Check returned predicates; report missing constraints instead of substituting a nationwide aggregate."
)
GLOBAL_SCOPE_REWRITE_AFTER = (
    "- Before splitting a source-scoped answer, define one specification of requested "
    "payment/category/geography/period/population filters and grain. Send that same source, specification "
    "and required ID/name pairs to every delegated query, including totals and rankings. Filter facts "
    "before aggregation. A filtered total does not scope a ranking. Check each query/result against the "
    "specification; report missing filters, never substitute broader aggregates or unfiltered stored ranks."
)
FILTERED_FACT_GUIDANCE = """\
FILTERED FACT RANKINGS
- Carry every requested payment, category, geography and period predicate into EACH delegated SQL query. Apply them to dbo.ot_donation before aggregation; a separately filtered total does not constrain a separate ranking query.
- For a filtered Municipality ranking, aggregate DonationAmountYen (and DonationId count when requested) from that same filtered Donation fact set by MunicipalityId, then join dbo.ot_municipality for names. Do not rank using MunicipalityStaticTotalYen, MunicipalityStaticCount or MunicipalityAmountRank: those stored fields summarize the full StaticSeed snapshot across all payment methods, not the filtered transaction population.
"""
KUSTO_SOURCE_GUIDANCE = """\
TIME FORMAT AND SOURCE AVAILABILITY
- For every returned FirstObservedAt/LastObservedAt value, format the actual UTC instant as `yyyy-MM-dd HH:mm:ss` with `format_datetime`, label it UTC, and copy the returned 24-hour value exactly. Do not transcribe an unformatted timestamp or infer AM/PM.
- When asked which configured sources can provide a metric, distinguish their declared scopes: this Eventhouse view provides August observation metrics at aggregate-bucket granularity, not one raw event per row; Lakehouse tables provide the independent static 2025 snapshot; the semantic model provides Notebook 05 Gold, including only accepted quality-processed increments rather than raw Eventhouse observations; Ontology is modeled context, not a numeric substitute unless an actual query returns the requested metric. Name each applicable source and limitation without inferring numeric availability from configuration alone.
"""
MODEL_FILTER_SEMANTICS = (
    "KEEPFILTERS intersects this measure's inner predicate with the calling query's outer "
    "filter on the same column; it does not overwrite the outer filter. If the outer filter "
    "excludes the inner value, the intersection is empty; other caller filters still apply. "
    "Do not interpret a returned BLANK as zero."
)
HIGH_VALUE_PROVENANCE = (
    "Notebook 05 provenance: IsHighValue is DonationAmountYen > 57000; exactly JPY 57,000 "
    "is excluded. This is an analytical flag, not a notification rule."
)
NOTEBOOK_THRESHOLD = 'F.col("DonationAmountYen") > F.lit(57000)'


def _parts(definition: dict[str, Any]) -> list[dict[str, Any]]:
    parts = definition.get("definition", definition)["parts"]
    paths = [part["path"] for part in parts]
    if len(paths) != len(set(paths)):
        raise ValueError("Duplicate definition part paths must be reconciled.")
    if any(part.get("payloadType") != "InlineBase64" for part in parts):
        raise ValueError("Every definition part must use the observed inline encoding.")
    return parts


def _utf16_units(value: str) -> int:
    return len(value.encode("utf-16-le")) // 2


def _rewrite_shared_scope(stage_config: dict[str, Any]) -> bool:
    instructions = stage_config.get("aiInstructions")
    if not isinstance(instructions, str) or instructions.count(GLOBAL_SCOPE_REWRITE_BEFORE) != 1:
        raise ValueError("Current shared delegation constraint changed; inspect before compiling.")
    revised = instructions.replace(GLOBAL_SCOPE_REWRITE_BEFORE, GLOBAL_SCOPE_REWRITE_AFTER, 1)
    if not 0 < _utf16_units(revised) <= LIMIT:
        raise ValueError("Candidate global instructions exceed the service limit.")
    stage_config["aiInstructions"] = revised
    return revised != instructions


def _append_once(original: str, addition: str, label: str) -> str:
    if addition in original:
        return original
    return original.rstrip() + "\n\n" + addition.rstrip() + "\n"


def _walk(nodes: list[dict[str, Any]]):
    for node in nodes:
        yield node
        yield from _walk(node.get("children", []))


def _measure_metadata(model_definition: dict[str, Any], notebook: dict[str, Any]) -> dict[str, dict[str, str]]:
    parts = _parts(model_definition)
    matches = [part for part in parts if part["path"] == MODEL_PATH]
    if len(matches) != 1:
        raise ValueError("The pinned model must contain one owning donation table.")
    raw = base64.b64decode(matches[0]["payload"], validate=True)
    text = raw.decode("utf-8-sig")
    lines = text.splitlines()
    metadata: dict[str, dict[str, str]] = {}
    for index, line in enumerate(lines):
        match = re.fullmatch(r"\tmeasure (.+?) = (.+)", line)
        if not match:
            continue
        comments = []
        previous = index - 1
        while previous >= 0 and lines[previous].startswith("\t/// "):
            comments.insert(0, lines[previous].removeprefix("\t/// "))
            previous -= 1
        metadata[match[1]] = {"expression": match[2], "comments": "\n".join(comments)}
    keepfilters = {
        name: value for name, value in metadata.items()
        if "KEEPFILTERS(" in value["expression"]
    }
    expected = {
        "静的寄附総額", "静的寄附件数", "受入増分寄附総額",
        "受入増分寄附件数", "高額寄附件数",
    }
    if set(keepfilters) != expected:
        raise ValueError("The owning model must expose the five verified KEEPFILTERS measures.")
    expected_predicates = {
        "静的寄附総額": ("データソース", '"StaticSeed"'),
        "静的寄附件数": ("データソース", '"StaticSeed"'),
        "受入増分寄附総額": ("データソース", '"RealtimeIncrement"'),
        "受入増分寄附件数": ("データソース", '"RealtimeIncrement"'),
        "高額寄附件数": ("高額寄附フラグ", "TRUE()"),
    }
    for name, value in keepfilters.items():
        match = re.search(
            r"KEEPFILTERS\(\s*'寄附'\[(?P<column>[^\]]+)\]\s*=\s*(?P<value>TRUE\(\)|[^,\)]+)\s*\)",
            value["expression"],
        )
        if match is None or (match["column"], match["value"]) != expected_predicates[name]:
            raise ValueError("A KEEPFILTERS measure has an unexpected inner predicate: " + name)
        value["filter_semantics"] = (
            MODEL_FILTER_SEMANTICS + " Actual inner predicate: '寄附'["
            + match["column"] + "] = " + match["value"] + "."
        )
    cells = notebook.get("cells", [])
    source = "\n".join(
        "".join(cell.get("source", []))
        for cell in cells if isinstance(cell, dict) and isinstance(cell.get("source", []), list)
    )
    if source.count(NOTEBOOK_THRESHOLD) < 2:
        raise ValueError("Notebook 05 does not verify the strict DonationAmountYen threshold twice.")
    metadata["高額寄附件数"]["threshold_provenance"] = HIGH_VALUE_PROVENANCE
    return keepfilters | {"高額寄附件数": metadata["高額寄附件数"]}


def _source_nodes(source: dict[str, Any], kind: str) -> list[dict[str, Any]]:
    if not isinstance(source.get("elements"), list):
        raise ValueError("The source selection has no element tree: " + kind)
    return list(_walk(source["elements"]))


def _update_lakehouse(source: dict[str, Any]) -> list[str]:
    source["dataSourceInstructions"] = _append_once(
        source["dataSourceInstructions"], FILTERED_FACT_GUIDANCE, "Lakehouse guidance"
    )
    changed = ["dataSourceInstructions"]
    nodes = _source_nodes(source, "lakehouse_tables")
    additions = {
        ("lakehouse_tables.table", "ot_donation"): (
            " Filter every requested payment, category, geography and period predicate on this "
            "transaction-grain fact before grouping or ranking; apply the same predicates in every "
            "delegated query and rank from the filtered Donation rows."
        ),
        ("lakehouse_tables.column", "DonationPaymentMethod"): (
            " Apply this predicate to dbo.ot_donation before aggregation; a dimension's stored "
            "all-payment totals or rank are not the filtered result."
        ),
        ("lakehouse_tables.column", "MunicipalityStaticCount"): (
            " This stored count covers the full StaticSeed snapshot and all payment methods; it "
            "cannot answer a filtered transaction ranking."
        ),
        ("lakehouse_tables.column", "MunicipalityStaticTotalYen"): (
            " This stored total covers the full StaticSeed snapshot and all payment methods; it "
            "cannot answer a filtered transaction ranking."
        ),
        ("lakehouse_tables.column", "MunicipalityAmountRank"): (
            " This stored rank covers the full StaticSeed snapshot and all payment methods; derive "
            "a filtered ranking from dbo.ot_donation after applying every requested predicate."
        ),
    }
    for (node_type, name), addition in additions.items():
        found = [node for node in nodes if node.get("type") == node_type and node.get("display_name") == name]
        if len(found) != 1 or found[0].get("is_selected") is not True:
            raise ValueError("Expected one selected Lakehouse metadata node: " + name)
        description = found[0].get("description")
        if not isinstance(description, str):
            raise ValueError("Expected a text description on selected Lakehouse node: " + name)
        revised = _append_once(description, addition, name)
        if revised != description:
            found[0]["description"] = revised
            changed.append("elements:" + name + ":description")
    return changed


def _update_kusto(source: dict[str, Any]) -> list[str]:
    before = source["dataSourceInstructions"]
    revised = _append_once(before, KUSTO_SOURCE_GUIDANCE, "Kusto guidance")
    if _utf16_units(revised) > LIMIT:
        raise ValueError("Kusto source instructions exceed the service limit.")
    source["dataSourceInstructions"] = revised
    return ["dataSourceInstructions"] if revised != before else []


def _update_semantic_model(source: dict[str, Any], metadata: dict[str, dict[str, str]]) -> list[str]:
    nodes = _source_nodes(source, "semantic_model")
    changes = []
    for name in sorted(metadata):
        found = [node for node in nodes
                 if node.get("type") == "semantic_model.measure" and node.get("display_name") == name]
        if len(found) != 1 or found[0].get("is_selected") is not True:
            raise ValueError("Expected one selected semantic-model measure: " + name)
        row = metadata[name]
        comments = row["comments"].splitlines()
        business = next((comment for comment in comments
                         if not comment.startswith(("Filter semantics:", "Executable definition:"))), "")
        description = "\n".join(
            value for value in (
                business,
                "Verified DAX expression: " + row["expression"],
                row.get("filter_semantics", ""),
                row.get("threshold_provenance", ""),
            ) if value
        )
        current = found[0].get("description")
        if current not in (None, description):
            raise ValueError("Refusing to overwrite an existing measure description: " + name)
        if current != description:
            found[0]["description"] = description
            changes.append("elements:" + name + ":description")

    flag = [node for node in nodes
            if node.get("type") == "semantic_model.column" and node.get("display_name") == "高額寄附フラグ"]
    if len(flag) != 1 or flag[0].get("is_selected") is not True:
        raise ValueError("Expected one selected high-value flag column.")
    flag_description = (
        "Notebook 05 derives IsHighValue from DonationAmountYen > 57000; exactly JPY 57,000 "
        "is excluded. The 高額寄附件数 measure counts rows where this flag is TRUE(). "
        "This is an analytical flag, not a notification rule."
    )
    if flag[0].get("description") not in (None, flag_description):
        raise ValueError("Refusing to overwrite an existing high-value flag description.")
    if flag[0].get("description") != flag_description:
        flag[0]["description"] = flag_description
        changes.append("elements:高額寄附フラグ:description")
    return changes


def compile_candidate(
    agent_definition: dict[str, Any],
    model_definition: dict[str, Any],
    notebook: dict[str, Any],
    *,
    expected_agent_sha256: str = EXPECTED_AGENT_SHA256,
    expected_model_sha256: str = EXPECTED_MODEL_SHA256,
    expected_part_count: int = 13,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return a review-only Agent definition and receipt from exact pinned readbacks."""
    for value in (expected_agent_sha256, expected_model_sha256):
        if not re.fullmatch(r"[a-f0-9]{64}", value):
            raise ValueError("An explicit SHA-256 input pin is required.")
    actual_agent = definition_digest(agent_definition)
    actual_model = definition_digest(model_definition)
    if expected_agent_sha256 == PREVIOUS_AGENT_SHA256:
        raise ValueError("The previous prepublication Agent pin is stale; use the fresh current readback.")
    if actual_agent != expected_agent_sha256:
        raise ValueError("Agent differs from the reviewed readback pin.")
    if actual_model != expected_model_sha256:
        raise ValueError("Semantic model differs from the reviewed readback pin.")
    parts = _parts(agent_definition)
    if not isinstance(expected_part_count, int) or expected_part_count < 1:
        raise ValueError("An explicit positive Agent part-count expectation is required.")
    if len(parts) != expected_part_count:
        raise ValueError("Agent part count differs from the reviewed input shape.")
    draft_docs, sources, serialization = stage_sources(agent_definition, "draft")
    published_docs, published_sources, published_serialization = stage_sources(agent_definition, "published")
    if serialization != "native-ontology-context" or published_serialization != serialization:
        raise ValueError("Require the reviewed native Ontology context.")
    if set(sources) != set(published_sources) or any(
        sources[kind][0].replace("/draft/", "/published/", 1) != published_sources[kind][0]
        or sources[kind][1].get("workspaceId") != published_sources[kind][1].get("workspaceId")
        or sources[kind][1].get("artifactId") != published_sources[kind][1].get("artifactId")
        for kind in sources
    ):
        raise ValueError("Draft and Published source identities differ; reconcile before compiling.")
    draft_stage_path = "Files/Config/draft/stage_config.json"
    published_stage_path = "Files/Config/published/stage_config.json"
    if (draft_stage_path not in draft_docs or published_stage_path not in published_docs
            or draft_docs[draft_stage_path].get("aiInstructions")
            != published_docs[published_stage_path].get("aiInstructions")):
        raise ValueError("Draft and Published global instructions differ; do not overwrite a distinct Draft.")
    metadata = _measure_metadata(model_definition, notebook)
    result = copy.deepcopy(agent_definition)
    result_parts = _parts(result)
    changed_fields = {}
    target_paths = {sources[kind][0] for kind in ("lakehouse_tables", "kusto", "semantic_model")}
    target_paths.add(draft_stage_path)
    for part in result_parts:
        if part["path"] not in target_paths:
            continue
        source = copy.deepcopy(json.loads(base64.b64decode(part["payload"], validate=True)))
        if part["path"] == draft_stage_path:
            fields = ["aiInstructions"] if _rewrite_shared_scope(source) else []
        elif source.get("type") == "lakehouse_tables":
            fields = _update_lakehouse(source)
        elif source.get("type") == "kusto":
            fields = _update_kusto(source)
        elif source.get("type") == "semantic_model":
            fields = _update_semantic_model(source, metadata)
        else:
            raise ValueError("Unexpected source type at a pinned source path.")
        if fields:
            changed_fields[part["path"]] = fields
            revised = inline_part(part["path"], source)
            part.update(revised)
    if not changed_fields:
        raise ValueError("The candidate produced no source metadata changes.")
    instruction_units = {}
    for path in (draft_stage_path, *(sources[kind][0] for kind in ("lakehouse_tables", "kusto", "semantic_model"))):
        decoded = json.loads(base64.b64decode(next(p for p in result_parts if p["path"] == path)["payload"], validate=True))
        value = decoded.get("aiInstructions") if path == draft_stage_path else decoded.get("dataSourceInstructions")
        if not isinstance(value, str) or not 0 < _utf16_units(value) <= LIMIT:
            raise ValueError("Candidate instruction field exceeds the UTF-16 service limit: " + path)
        instruction_units[path] = _utf16_units(value)
    changed_paths = {
        path for path in {p["path"] for p in parts}
        if next(p for p in parts if p["path"] == path) != next(
            p for p in result_parts if p["path"] == path
        )
    }
    if changed_paths != set(changed_fields) or not changed_paths <= target_paths:
        raise ValueError("Candidate changed an unapproved definition part.")
    request_body = {"definition": {"parts": copy.deepcopy(result_parts)}}
    request_bytes = json.dumps(
        request_body, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    receipt = {
        "status": "offline-unmeasured-review-only",
        "inputAgentCanonicalSha256": actual_agent,
        "inputModelCanonicalSha256": actual_model,
        "inputAgentPartCount": len(parts),
        "candidateAgentCanonicalSha256": definition_digest(result),
        "candidateUpdateRequestBodySha256": hashlib.sha256(request_bytes).hexdigest(),
        "candidateUpdateRequestBodyEncoding": "compact UTF-8 JSON, sorted object keys",
        "changedDraftFields": changed_fields,
        "instructionUtf16Units": instruction_units,
        "previousReviewedAgentInputSha256": PREVIOUS_AGENT_SHA256,
        "previousReviewedAgentInputRejectedAsStale": True,
        "sourceSelectionsAndIdentitiesPreserved": True,
        "publishedAndNativeOntologyPartsPreserved": True,
        "semanticModelDefinitionChanged": False,
        "notebookDataChanged": False,
        "fewshotsAdded": 0,
        "cloudCalls": 0,
        "answerAccuracyAccepted": False,
        "liveSubmissionOrPublication": "not performed",
    }
    return result, receipt


def compile_fresh_candidate(
    agent_definition: dict[str, Any],
    model_definition: dict[str, Any],
    notebook: dict[str, Any],
    *,
    expected_agent_sha256: str,
    expected_model_sha256: str,
    expected_scope: dict[str, Any],
    fresh_readback_receipt: dict[str, Any],
    fresh_readback_receipt_sha256: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Compile only from a separately verified, identity-bound full readback."""
    if not re.fullmatch(r"[a-f0-9]{64}", fresh_readback_receipt_sha256):
        raise ValueError("The fresh readback receipt must be pinned by SHA-256.")
    scope_keys = {
        "tenantId", "workspaceId", "folderId", "agentId", "semanticModelId",
        "agentType", "agentParentFolderId", "draftSourceIds", "publishedSourceIds",
    }
    if (set(expected_scope) != scope_keys
            or fresh_readback_receipt.get("result") != "fresh-read-only-definition-snapshot"
            or fresh_readback_receipt.get("identityVerified") is not True
            or {key: fresh_readback_receipt.get(key) for key in scope_keys} != expected_scope):
        raise ValueError("Fresh-read identity, parent folder or source bindings differ from the expected scope.")
    if (fresh_readback_receipt.get("agentCanonicalSha256") != expected_agent_sha256
            or fresh_readback_receipt.get("modelCanonicalSha256") != expected_model_sha256
            or fresh_readback_receipt.get("agentParts") != 13
            or fresh_readback_receipt.get("modelParts") != len(_parts(model_definition))
            or fresh_readback_receipt.get("agentAdjacentFreshReadSame") is not True
            or fresh_readback_receipt.get("modelAdjacentFreshReadSame") is not True
            or fresh_readback_receipt.get("cloudWrites") != 0
            or fresh_readback_receipt.get("updateDefinitionRequests") != 0
            or fresh_readback_receipt.get("publishRequests") != 0
            or fresh_readback_receipt.get("questionSubmissions") != 0):
        raise ValueError("Fresh full-definition readback is incomplete or does not match the candidate pins.")
    if (expected_agent_sha256 != EXPECTED_AGENT_SHA256
            or expected_model_sha256 != EXPECTED_MODEL_SHA256):
        raise ValueError("Fresh readback differs from the specifically reviewed current Agent/model pins.")
    for stage, key in (("draft", "draftSourceIds"), ("published", "publishedSourceIds")):
        _, sources, serialization = stage_sources(agent_definition, stage)
        if serialization != "native-ontology-context":
            raise ValueError("Fresh readback no longer has the reviewed native Ontology context.")
        actual_ids = {kind: source[1].get("artifactId") for kind, source in sources.items()}
        if (actual_ids != expected_scope[key]
                or any(source[1].get("workspaceId") != expected_scope["workspaceId"]
                       for source in sources.values())
                or sources["semantic_model"][1].get("artifactId") != expected_scope["semanticModelId"]):
            raise ValueError("Fresh Agent source selections/IDs differ from the expected definition bindings.")
    result, receipt = compile_candidate(
        agent_definition,
        model_definition,
        notebook,
        expected_agent_sha256=expected_agent_sha256,
        expected_model_sha256=expected_model_sha256,
        expected_part_count=13,
    )
    receipt.update(
        candidate="r5-fresh-rebased-offline",
        freshReadbackReceiptSha256=fresh_readback_receipt_sha256,
        freshReadbackIdentityAndParentFolderVerified=True,
        inputStageIsFreshCurrentDefinition=True,
    )
    return result, receipt


def candidate_request_body(agent_definition: dict[str, Any]) -> dict[str, Any]:
    """Wrap the local candidate in the service updateDefinition body shape."""
    return {"definition": {"parts": copy.deepcopy(_parts(agent_definition))}}
