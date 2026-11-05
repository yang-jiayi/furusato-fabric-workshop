"""Offline routing and model-description candidate; no transport or acceptance."""
from __future__ import annotations

import base64
import copy
import hashlib
import re

from evaluate_native import definition_digest
from measured_contract_profile import LIMIT, stage_sources
from quality_candidate import GLOBAL_REPLACEMENTS, model_contract
from source_grounded_profile import inline_part

BASE_AGENT = "fbc6a41460a47fa0432b7f223fb7d0c20de04a24776668867a04ac04759ad133"
BASE_MODEL_PART = "6aaeb1483570299e241b07475cd94cba9fa49f7c3dbc7075951c7e6f54ea50a0"
MODEL_PATH = "definition/tables/\u5bc4\u9644.tmdl"
ANCHOR = GLOBAL_REPLACEMENTS[1][1]
DECOMPOSITION = (
    "- Before delegation, carry shared payment/category/geography/period/population constraints "
    "into EVERY applicable subquestion, including rankings, unless the user explicitly changes "
    "scope. Send each subquestion with those constraints, grain and required ID/name pairs; "
    "do not request an unfiltered stored rank for a filtered population. A separate filtered "
    "total does not scope another query. Check returned predicates; "
    "report missing constraints instead of substituting a nationwide aggregate."
)
FILTER_DESCRIPTION = (
    "Filter semantics: this measure's own KEEPFILTERS intersects an existing filter on the "
    "same column; it does not replace that filter. Empty-intersection behavior follows the "
    "executable expression. Distinguish this definition from filters added by a calling query."
)
CAPABILITY_URL = "https://learn.microsoft.com/en-us/fabric/data-science/data-agent-add-datasources#tab/dax"
CAPABILITY_COMMIT = "0461abfa67edba6d3cdcef5d74d5efe0d43deca3"


def _parts(definition):
    parts = definition.get("definition", definition)["parts"]
    paths = [part["path"] for part in parts]
    if len(paths) != len(set(paths)):
        raise ValueError("Duplicate definition part paths.")
    return parts


def _units(value):
    return len(value.encode("utf-16-le")) // 2


def _measures(text):
    rows = re.findall(r"(?m)^\tmeasure (.+?) = ([^\r\n]+)\r?$", text)
    if len(rows) != 10 or len({name for name, _ in rows}) != 10:
        raise ValueError("Require ten unique single-line executable measures.")
    return rows


def compile_candidate(
    agent_definition, model_definition, *,
    expected_agent_sha256=BASE_AGENT, expected_model_part_sha256=BASE_MODEL_PART,
):
    """Return separate review-only Agent Draft and model metadata definitions.

    Explicit alternative pins support offline fixtures or separately reviewed
    states; callers must never infer a new pin from an unverified live read.
    """
    for pin in (expected_agent_sha256, expected_model_part_sha256):
        if not isinstance(pin, str) or not re.fullmatch(r"[a-f0-9]{64}", pin):
            raise ValueError("An explicit SHA-256 input pin is required.")
    if definition_digest(agent_definition) != expected_agent_sha256:
        raise ValueError("Agent differs from the reviewed input pin.")
    _parts(agent_definition)
    model_parts = _parts(model_definition)
    docs, sources, serialization = stage_sources(agent_definition, "published")
    if serialization != "native-ontology-context":
        raise ValueError("Require the observed native Ontology context.")
    published_path = "Files/Config/published/stage_config.json"
    draft_path = published_path.replace("/published/", "/draft/")
    if docs[draft_path]["aiInstructions"] != docs[published_path]["aiInstructions"]:
        raise ValueError("Draft instructions differ; do not overwrite concurrent work.")
    original = docs[draft_path]["aiInstructions"]
    if original.count(ANCHOR) != 1:
        raise ValueError("Current decomposition anchor changed.")
    revised = original.replace(ANCHOR, DECOMPOSITION, 1)
    if not 0 < _units(revised) <= LIMIT:
        raise ValueError("Candidate global instructions exceed the service limit.")
    # Unsupported semantic-model source instructions are preserved, not treated
    # as a tuning surface. Supported SQL/KQL source instructions also stay exact.
    source_units = {}
    for kind, (_, source) in sources.items():
        if kind != "ontology":
            source_units[kind] = _units(source["dataSourceInstructions"])
            if source_units[kind] > LIMIT:
                raise ValueError("Existing source instructions exceed the limit: " + kind)
    agent = copy.deepcopy(agent_definition)
    config = copy.deepcopy(docs[draft_path])
    config["aiInstructions"] = revised
    target = next(part for part in _parts(agent) if part["path"] == draft_path)
    target.update(inline_part(draft_path, config))

    model_contract(model_definition)  # Reject unknown/multiline measure layouts.
    part = next((p for p in model_parts if p["path"] == MODEL_PATH), None)
    if part is None or part["payloadType"] != "InlineBase64":
        raise ValueError("Missing inline owning model table.")
    raw = base64.b64decode(part["payload"], validate=True)
    if hashlib.sha256(raw).hexdigest() != expected_model_part_sha256:
        raise ValueError("Model owning table differs from the reviewed input pin.")
    text = raw.decode("utf-8")
    expressions = _measures(text)
    edited = []
    added_lines = []
    descriptions = []
    for line in text.splitlines(keepends=True):
        match = re.fullmatch(r"\tmeasure (.+?) = ([^\r\n]+)(\r\n|\n)?", line)
        if match and "KEEPFILTERS(" in match[2]:
            ending = match[3] or "\n"
            comments = [
                "\t/// " + FILTER_DESCRIPTION + ending,
                "\t/// Executable definition: " + match[2] + ending,
            ]
            edited.extend(comments)
            added_lines.append("".join(comments))
            descriptions.append(match[1])
        edited.append(line)
    if len(descriptions) != 5:
        raise ValueError("Require the observed five KEEPFILTERS measure definitions.")
    revised_text = "".join(edited)
    if _measures(revised_text) != expressions:
        raise ValueError("Executable measure expression changed.")
    restored = revised_text
    for line in added_lines:
        if restored.count(line) != 1:
            raise ValueError("Description insertion is ambiguous.")
        restored = restored.replace(line, "", 1)
    if restored.encode("utf-8") != raw:
        raise ValueError("Non-description model bytes changed.")
    model = copy.deepcopy(model_definition)
    next(p for p in _parts(model) if p["path"] == MODEL_PATH)["payload"] = (
        base64.b64encode(revised_text.encode("utf-8")).decode("ascii")
    )
    return agent, model, {
        "status": "offline-unmeasured-review-only",
        "inputAgentCanonicalSha256": expected_agent_sha256,
        "inputOwningModelPartSha256": expected_model_part_sha256,
        "changedAgentFields": [draft_path + ":aiInstructions"],
        "changedModelFields": [
            {"part": MODEL_PATH, "measure": name, "field": "description"} for name in descriptions
        ],
        "globalInstructionUtf16Units": _units(revised),
        "unchangedSourceInstructionUtf16Units": source_units,
        "allTenExecutableMeasuresBytePreserved": True,
        "modelOtherBytesAndPartsPreserved": True,
        "sourceIdentitiesSelectionsAndInstructionsPreserved": True,
        "publishedAndNativeOntologyPartsPreserved": True,
        "semanticModelSourceInstructionsSupported": False,
        "modelSemanticsSurface": "Existing TMDL measure descriptions; not invented Prep for AI annotations.",
        "capabilityReference": {"url": CAPABILITY_URL, "commit": CAPABILITY_COMMIT},
        "supportedSurfaceIsNotProofOfRuntimeConsumption": True,
        "cloudCalls": 0, "dataChanges": 0, "fewshotsAdded": 0, "answerAccuracyAccepted": False,
    }
