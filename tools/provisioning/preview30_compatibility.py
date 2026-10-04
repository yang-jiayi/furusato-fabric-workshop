"""Explicit, OFFLINE generation1 consumer-bridge plans; never a gen2 fallback.

No credentials, HTTP client, deployment, refresh, Agent question or publication
is implemented here. Only supplied snapshots and private output files are used.
"""
from __future__ import annotations

import argparse
import base64
import copy
import hashlib
from functools import lru_cache
import json
from pathlib import Path
import sys
import types
from typing import Any

from preview30_runtime import (
    API, BASE, GUID, REPO, SafetyError, canonical, digest, load, private_directory,
    scope_fingerprint, scope_from_document,
)

CREATOR = BASE / "notebooks" / "Notebook_03_Furusato_Create_Complete_Ontology.ipynb"
TEMPLATE = BASE / "ontology" / "ontology-full-definition-template.json"
DESCRIPTION = (
    "Explicit generation1 static consumer bridge over the same owned Lakehouse. "
    "Not a replacement, downgrade or generation2 connector fix; the operational core remains primary."
)
COUNTS = {
    "definitionParts": 53, "entityTypes": 10, "staticProperties": 72,
    "timeseriesProperties": 0, "dataBindings": 10, "relationshipTypes": 15,
    "contextualizations": 15, "overviews": 1,
}
PACKAGED_INPUTS = (
    "tools/provisioning/preview30_compatibility.py",
    "workshop/v2.7.0/notebooks/Notebook_03_Furusato_Create_Complete_Ontology.ipynb",
    "workshop/v2.7.0/ontology/ontology-full-definition-template.json",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SafetyError(message)


@lru_cache(maxsize=1)
def legacy_helpers():
    """Load the released definitions-only cell, never Notebook03 action cells."""
    import ast
    cells = ["".join(cell.get("source", [])) for cell in load(CREATOR)["cells"]
             if cell["cell_type"] == "code"]
    matches = [text for text in cells if "def build_creation_plan(" in text and "def validate_template(" in text]
    require(len(matches) == 1, "Expected one released Ontology creator definitions cell.")
    code = matches[0]
    require(all(isinstance(node, (ast.Import, ast.ImportFrom, ast.Assign, ast.ClassDef, ast.FunctionDef))
                for node in ast.parse(code).body), "Unexpected executable statement in released helper cell.")
    module = types.ModuleType("furusato_preview30_released_legacy_helpers")
    sys.modules[module.__name__] = module
    exec(compile(code, str(CREATOR) + ":definitions-only", "exec"), module.__dict__)
    return module


def build_template(original: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    helper = legacy_helpers()
    require(helper.validate_template(original) == {
        **COUNTS, "definitionParts": 54, "timeseriesProperties": 1, "dataBindings": 11,
    }, "The immutable released 54-part business model is required.")
    template = copy.deepcopy(original)
    removed = []
    omitted = []
    for part in template["parts"]:
        value = part["content"]
        if helper.ENTITY_PART_PATTERN.fullmatch(part["path"]) and value.get("timeseriesProperties"):
            omitted.extend((value["name"], prop["name"]) for prop in value["timeseriesProperties"])
            value["timeseriesProperties"] = []
        if value.get("dataBindingConfiguration", {}).get("dataBindingType") == "TimeSeries":
            removed.append(part["path"])
        if part["path"] == ".platform":
            value["metadata"]["description"] = DESCRIPTION
    require(omitted == [("Municipality", "IncomingDonationAmountYen")] and len(removed) == 1,
            "Only the original operational TS property and its binding may be omitted.")
    template["parts"] = [part for part in template["parts"] if part["path"] not in removed]
    template["ontologyDisplayNameTemplate"] = "ONT_Furusato_AgentCompat_<PID>"
    template["description"] = DESCRIPTION
    template["sourceSelectors"] = {"lakehouse": template["sourceSelectors"]["lakehouse"]}
    template["expectedSourceTables"] = {"lakehouse": template["expectedSourceTables"]["lakehouse"]}
    template["expectedContract"] = dict(COUNTS)
    template["placeholders"] = sorted(helper._collect_placeholders(template["parts"]))
    template["definitionTemplateSha256"] = helper.sha256_json(template["parts"])
    require(helper.validate_template(template) == COUNTS, "Static generation1 bridge contract differs.")
    contract = {
        "schemaVersion": "furusato-explicit-generation1-consumer-bridge/v1",
        "expectedGeneration": 1, "wireFormat": "EntityTypes/RelationshipTypes JSON",
        "defaultEnabled": False, "implicitFallback": False, "primaryGeneration2Unchanged": True,
        "relationshipsGeneration2CompanionUnchanged": True, "counts": dict(COUNTS),
        "ontologyName": template["ontologyDisplayNameTemplate"],
        "candidateAgentName": "DA_Furusato_AgentCompat_<PID>",
        "sourceTables": template["expectedSourceTables"]["lakehouse"],
        "sourceContract": {"sameOwnedLakehouse": True, "schema": "dbo", "staticSourceObjects": 25,
                           "entityTables": 10, "catalogBridgeTables": 1, "copyBusinessData": False,
                           "businessIdsKeysTypesAndMappingsPreserved": True,
                           "legacyMetadataIdsPreserved": True, "metadataIdsNeedNotEqualGen2LineageTags": True,
                           "omittedProperty": "Municipality.IncomingDonationAmountYen",
                           "omittedBindingParts": removed, "emptyOverviewRetained": True},
        "deployment": {"mode": "offline-private-handoff-only", "createOnly": True,
                       "defaultPlacement": "specified-folder-direct",
                       "explicitEvaluationTempAllowed": True, "newItemOwnershipReadbackRequired": True,
                       "rerunNotebooks": False, "sourceDdlAllowed": False, "policiesOrRolesChanged": False},
        "graph": {"automaticRefreshByHelper": False, "actualManagedChildDiscoveryRequired": True,
                  "possibleServiceManagedChildren": ["GraphModel", "Lakehouse", "SQLEndpoint"],
                  "derivedProjectionStorageAndCapacityCost": True, "zeroCopyClaimed": False,
                  "nativeInitialization": "Open only the new managed Graph in the native editor when loading infrastructure requires initialization; Save can ingest data.",
                  "refreshMethod": "POST", "refreshBody": None,
                  "refreshUrl": API + "/workspaces/{workspaceId}/graphModels/{actualManagedGraphId}/jobs/refreshGraph/instances",
                  "reuseExistingActiveOrMatchingCompletedJob": True, "maximumExplicitRefreshAttempts": 1,
                  "graphNotRefreshableBlindRetryAllowed": False, "terminalJobAndGqlProofRequired": True,
                  "acceptance": {"nodeTypes": 10, "edgeTypes": 15, "nodes": 109592, "directedEdges": 297303,
                                 "gqlChecks": 3, "maximumWithOneSyntaxCorrection": 4,
                                 "checks": ["all node/edge labels and totals", "Prefecture 45 reverse Municipality path",
                                            "Donation 5000001 donor/geography/gift/category/catalog path"],
                                 "catalogRelationshipIsFulfillment": False}},
        "agent": {"mode": "new-isolated-draft-handoff-only",
                  "onlyChangedOntologyFields": ["artifactId", "displayName", "userDescription"],
                  "preserve": ["Lakehouse", "KQL", "direct SemanticModel", "Code Interpreter",
                               "GLOBAL exact bytes", "all datasource instructions", "entity/property selections"],
                  "publicCandidateFilesChanged": False, "automaticPublication": False, "automaticPromotion": False},
        "evidenceBoundary": {
            "boundedPriorObservation": "An isolated source-only candidate executed native ontology-backed GQL without the generation API-version error.",
            "strictOriginalQuestionAcceptedByThisObservation": False,
            "full10Question84ConditionAcceptanceImplied": False,
            "newEnvironmentAcceptanceProvenByBuild": False,
        },
        "creator": {"notebook": CREATOR.relative_to(BASE).as_posix(), "definitionsOnly": True,
                    "template": TEMPLATE.relative_to(BASE).as_posix(),
                    "originalTemplateSha256": original["definitionTemplateSha256"],
                    "creatorFileSha256": hashlib.sha256(CREATOR.read_bytes()).hexdigest()},
    }
    return template, contract


def render_definition(template: dict[str, Any], scope: dict[str, Any], lakehouse_id: str) -> dict[str, Any]:
    require(GUID.fullmatch(lakehouse_id) is not None, "Use the owned Lakehouse GUID.")
    helper = legacy_helpers()
    require(helper.validate_template(template) == COUNTS, "Expected the explicit static compatibility template.")
    name = helper.expand_participant_name(template["ontologyDisplayNameTemplate"], scope["participantId"])
    replacements = {"{{ontology.displayName}}": name, "{{workspace.id}}": scope["workspaceId"],
                    "{{source.lakehouse.id}}": lakehouse_id}
    parts = []
    for part in template["parts"]:
        value = helper._replace_placeholders(copy.deepcopy(part["content"]), replacements)
        require(not helper._collect_placeholders(value), "An environment placeholder remains.")
        parts.append({"path": part["path"], "payloadType": "InlineBase64", "payload": helper._encode_part_json(value)})
    return {"parts": parts}


def check_scope(scope, inventory, owned_state, temp_folder_id):
    require(GUID.fullmatch(temp_folder_id) is not None, "Destination folder must be an externalized GUID.")
    require(owned_state.get("scopeSha256") == scope_fingerprint(scope), "Owned receipts belong to another scope.")
    require(scope["folderMappingVerified"] is True, "Explicit root folder mapping proof is required.")
    require(inventory["workspace"]["id"] == scope["workspaceId"]
            and inventory["workspace"].get("displayName") == scope["workspaceName"], "Inventory workspace differs.")
    require(inventory.get("capturedUtc"), "A timestamped read-only inventory is required.")
    folders = [f for f in inventory["folders"] if f["id"] == temp_folder_id]
    require(len(folders) == 1, "Destination folder must resolve exactly once.")
    if temp_folder_id != scope["folderId"]:
        require(folders[0].get("displayName") == "Temp"
                and folders[0].get("parentFolderId") == scope["folderId"],
                "An explicitly selected evaluation folder must be the approved root's Temp child.")
    require(any(f["id"] == scope["folderId"] for f in inventory["folders"]), "Approved root is absent.")
    for key, kind, prefix in (("lakehouse", "Lakehouse", "LH_Furusato_"), ("ontology", "Ontology", "ONT_Furusato_")):
        receipt = owned_state.get("items", {}).get(key, {})
        matches = [i for i in inventory["items"] if i.get("id") == receipt.get("id")]
        require(len(matches) == 1 and matches[0].get("type") == kind
                and matches[0].get("folderId") == scope["folderId"]
                and matches[0].get("displayName") == prefix + scope["participantId"], "Owned core/source no longer resolves in scope.")
    require(owned_state.get("sourceVerification", {}).get("verified") is True, "Verified existing source receipts are required.")
    generation = owned_state.get("ontologyVerification", {}).get("generation")
    require(type(generation) is int and generation == 2, "The primary must remain a verified generation2 core.")


def require_absent(name, inventory):
    require(not any(i.get("displayName", "").casefold() == name.casefold()
                    for i in inventory["items"] + inventory["recoverableItems"]),
            "Active/recoverable name collision; no adoption, update, restore or purge.")


def prepare(scope, inventory, owned_state, temp_folder_id=None):
    temp_folder_id = temp_folder_id or scope["folderId"]
    check_scope(scope, inventory, owned_state, temp_folder_id)
    template, contract = build_template(load(TEMPLATE))
    definition = render_definition(template, scope, owned_state["items"]["lakehouse"]["id"])
    name = "ONT_Furusato_AgentCompat_" + scope["participantId"]
    require_absent(name, inventory)
    body = {"displayName": name, "type": "Ontology", "folderId": temp_folder_id,
            "description": DESCRIPTION, "definition": definition}
    plan = {
        "schemaVersion": "furusato-generation1-offline-handoff/v1",
        "status": "prepared-not-approved-not-deployed", "scope": scope,
        "scopeSha256": scope_fingerprint(scope), "inventorySha256": digest(inventory),
        "ownedStateSha256": digest(owned_state), "contract": contract,
        "inputFilesSha256": {name: hashlib.sha256((REPO / name).read_bytes()).hexdigest()
                            for name in PACKAGED_INPUTS},
        "newItem": {"displayName": name, "folderId": temp_folder_id, "expectedGeneration": 1},
        "sourceLakehouseId": owned_state["items"]["lakehouse"]["id"],
        "preservedCoreId": owned_state["items"]["ontology"]["id"],
        "protectedPreexistingItemIds": sorted(i["id"] for i in inventory["items"]),
        "create": {"method": "POST", "url": API + "/workspaces/" + scope["workspaceId"] + "/items",
                   "bodyFile": "compat-create-body.json", "bodySha256": digest(body),
                   "headers": {"Content-Type": "application/json", "x-ms-fabric-skill": "fabriciq-ontology-cli"}},
        "allowCloudMutations": False,
        "requiredBeforeWrite": [
            "Obtain approval of this exact plan hash, body hash and target folder; production defaults directly to the approved folder.",
            "Re-read the destination, owned primary/source metadata and protected definitions; recheck active/recoverable name absence. Any explicit evaluation Temp must retain its approved ancestry.",
            "Acquire an exclusive operation window; persist an exclusive create-intent BEFORE one exact-body POST. Never repeat an ambiguous or failed request.",
            "Send the exact saved UTF-8 body bytes. Capture HTTP status, headers and response. For 202 poll the original public operations/{x-ms-operation-id}; honor Retry-After and bound the wait.",
            "Discover the actual new item ID and verify exact name/type/Temp folder, new ownership and properties.generation == 1. Reject missing/2; never retry another format/name.",
            "Read back all 53 JSON parts and exact static keys/property types/source mappings. Recheck protected gen2/native Metrics/TS and source guards without updateDefinition.",
        ],
        "forbidden": ["gen2 downgrade or guard relaxation", "implicit legacy fallback", "existing-definition replacement",
                      "Notebook runs", "source data/DDL copies or writes", "role/policy/capacity changes", "Agent mutation by this helper"],
    }
    plan["planSha256"] = digest(plan)
    return body, plan


def verify_readback(scope, owned_state, temp_folder_id, metadata, definition):
    generation = metadata.get("properties", {}).get("generation")
    require(type(generation) is int and generation == 1, "Native properties.generation must be exactly integer 1.")
    require(GUID.fullmatch(str(metadata.get("id", ""))) is not None and metadata.get("type") == "Ontology",
            "Expected a native Ontology identity.")
    require(metadata.get("workspaceId") == scope["workspaceId"] and metadata.get("folderId") == temp_folder_id
            and metadata.get("displayName") == "ONT_Furusato_AgentCompat_" + scope["participantId"], "Compatibility item scope differs.")
    require(metadata["id"] not in {i["id"] for i in owned_state["items"].values()}, "Compatibility item cannot be an existing core/source item.")
    template, _ = build_template(load(TEMPLATE))
    expected = render_definition(template, scope, owned_state["items"]["lakehouse"]["id"])
    helper = legacy_helpers()
    # getDefinition echoes the actual item's top-level description in .platform.
    platform = next(p for p in expected["parts"] if p["path"] == ".platform")
    value = helper._decode_part_json(platform)
    value["metadata"]["description"] = metadata.get("description", "")
    platform["payload"] = helper._encode_part_json(value)
    comparison = helper.verify_complete_definition(definition, expected)
    require(comparison["verified"] and comparison["partCount"] == 53, "Native static definition differs from the approved source contract.")
    return comparison


def agent_handoff(scope, inventory, owned_state, temp_folder_id, receipt, definition, graph, frozen, stage):
    check_scope(scope, inventory, owned_state, temp_folder_id)
    metadata = receipt["typedMetadata"]
    require(receipt["item"]["id"] == metadata["id"] and receipt.get("bodySha256")
            and receipt.get("planSha256"), "An owned create receipt with frozen hashes is required.")
    verification = verify_readback(scope, owned_state, temp_folder_id, metadata, definition)
    matches = [i for i in inventory["items"] if i.get("id") == metadata["id"]]
    require(len(matches) == 1 and all(matches[0].get(k) == metadata.get(k) for k in
                                    ("id", "type", "displayName", "folderId")), "Owned bridge moved or disappeared.")
    require(graph.get("graphQueryAcceptance") is True and graph.get("gqlChecksPassed") == 3
            and graph["scope"]["ontologyId"] == metadata["id"]
            and graph["scope"]["workspaceId"] == scope["workspaceId"]
            and graph["scope"]["folderId"] == temp_folder_id
            and graph["scope"]["sourceLakehouseId"] == owned_state["items"]["lakehouse"]["id"],
            "Exact scoped native Graph acceptance is required before the Agent handoff.")
    require(graph["refreshJob"]["status"] == "Completed"
            and not graph["refreshJob"].get("failureReason")
            and GUID.fullmatch(str(graph["scope"]["graphModelId"])) is not None
            and graph["refreshJob"]["itemId"] == graph["scope"]["graphModelId"],
            "A matching actual Completed Graph job is required.")
    require(all(graph.get("nativeCounts", {}).get(key) == value for key, value in
                {"nodeTypes": 10, "edgeTypes": 15, "nodes": 109592, "directedEdges": 297303}.items())
            and graph.get("postGqlGuards", {}).get("passed") is True,
            "Full native Graph counts and post-query protection checks are required.")
    candidate_name = "DA_Furusato_AgentCompat_" + scope["participantId"]
    require_absent(candidate_name, inventory)
    require(stage in {"draft", "published"}, "Choose the frozen source stage explicitly.")
    frozen = frozen.get("definition", frozen)
    by_path = {}
    for part in frozen["parts"]:
        require(part.get("payloadType") == "InlineBase64" and part["path"] not in by_path, "Duplicate or unsupported Agent part.")
        by_path[part["path"]] = copy.deepcopy(part)
    root = "Files/Config/" + stage + "/"
    selected = {path[len(root):]: part for path, part in by_path.items() if path.startswith(root)}
    require("stage_config.json" in selected and "Files/Config/data_agent.json" in by_path, "Unsupported frozen Agent layout.")
    decode = lambda part: json.loads(base64.b64decode(part["payload"], validate=True))
    sources = {path: decode(part) for path, part in selected.items() if path.endswith("/datasource.json")}
    require(sorted(value.get("type", "") for value in sources.values())
            == ["kusto", "lakehouse_tables", "ontology", "semantic_model"], "Exactly four direct sources are required.")
    require(all(value.get("workspaceId") == scope["workspaceId"] for value in sources.values()), "Cross-workspace Agent sources require a separate plan.")
    require(all(GUID.fullmatch(str(value.get("artifactId", ""))) for value in sources.values()),
            "Freeze concrete source identities before the handoff; no unresolved placeholders.")
    require(next(value["artifactId"] for value in sources.values() if value["type"] == "lakehouse_tables")
            == owned_state["items"]["lakehouse"]["id"], "The frozen direct Lakehouse differs from the owned source.")
    settings = decode(selected["stage_config.json"])
    require(settings.get("experimental", {}).get("codeInterpreterEnabled") is True, "CI must already be enabled in the supplied freeze; it is not enabled automatically.")
    require(isinstance(settings.get("aiInstructions"), str), "Frozen GLOBAL text is required.")
    source_path = next(path for path, value in sources.items() if value["type"] == "ontology")
    ontology = sources[source_path]
    require(ontology["artifactId"] != metadata["id"], "This source is already selected; reconcile instead of creating another candidate.")
    helper = legacy_helpers()
    model = helper.definition_model(definition)
    entities = {v["name"]: {p["name"] for p in v["properties"]}
                for path, v in model.items() if helper.ENTITY_PART_PATTERN.fullmatch(path)}
    elements = ontology["elements"]
    require(len(elements) == 10 and {e["display_name"] for e in elements} == set(entities), "Frozen entity selection differs.")
    for element in elements:
        require(element.get("is_selected") is True and element.get("type") == "ontology.entity"
                and {p.strip() for p in element.get("description", "").split(",")} == entities[element["display_name"]],
                "Use an explicitly frozen 72-static-property selection; no automatic TS removal or selection repair.")
    replacement = copy.deepcopy(ontology)
    replacement.update({
        "artifactId": metadata["id"], "displayName": metadata["displayName"],
        "userDescription": DESCRIPTION + " Static catalog relationships describe eligibility, not donation fulfillment.",
    })
    draft = {"parts": [copy.deepcopy(by_path["Files/Config/data_agent.json"])]}
    preserved = {}
    for path, part in selected.items():
        before = part["payload"]
        part["path"] = "Files/Config/draft/" + path
        if path == source_path:
            part["payload"] = base64.b64encode(canonical(replacement)).decode("ascii")
        else:
            require(part["payload"] == before, "An unrelated frozen payload changed.")
            preserved[path] = hashlib.sha256(base64.b64decode(before)).hexdigest()
        draft["parts"].append(part)
    changes = [{"field": key, "before": ontology.get(key), "after": replacement[key]}
               for key in ("artifactId", "displayName", "userDescription")]
    restored = copy.deepcopy(replacement)
    for change in changes:
        if change["field"] in ontology:
            restored[change["field"]] = change["before"]
        else:
            restored.pop(change["field"])
    require(restored == ontology, "Change escaped the three Ontology source fields.")
    handoff = {
        "schemaVersion": "furusato-generation1-agent-source-handoff/v1",
        "status": "prepared-not-created-not-published", "candidateName": candidate_name,
        "workspaceId": scope["workspaceId"], "folderId": temp_folder_id,
        "selectedOntologyId": metadata["id"], "selectedOntologyGeneration": 1,
        "sourceStage": stage, "frozenDefinitionSha256": digest(frozen),
        "candidateDraftSha256": digest(draft), "onlyChangedOntologyFields": changes,
        "preservedDatasourceRelativePath": source_path, "unchangedPayloadSha256": preserved,
        "globalUtf8Sha256": hashlib.sha256(settings["aiInstructions"].encode("utf-8")).hexdigest(),
        "sourceInstructionsSha256": digest({path: value.get("dataSourceInstructions") for path, value in sources.items()}),
        "nativeOntologyVerification": verification, "graphEvidenceSha256": digest(graph),
        "globalGenerationWording": "Existing GLOBAL wording is preserved exactly, even if it references generation2; the actual source and userDescription explicitly identify this generation1 bridge.",
        "allowCloudMutations": False, "publicationAllowedByPreparation": False,
        "promotionAllowed": False, "consumerOrBenchmarkAcceptanceClaimed": False,
        "requiredNextSteps": [
            "Freeze and re-read the selected source Agent stage; compare its exact hash before cloning. Never update the main/other existing candidates.",
            "Preview/approve one isolated candidate create after fresh Temp ancestry and active/recoverable name checks; persist its exact body and exclusive intent before any write.",
            "Apply only the prepared Draft to the NEW owned candidate, preserving the datasource relative paths. Do not copy an existing published stage into an automatic publication.",
            "Read back the four direct sources, exact selections, GLOBAL, source instructions and CI. Require only the three declared Ontology fields to differ.",
            "Any publication and native UI questions require separate explicit approval. A successful ontology-backed GQL execution does not imply strict question/10-question/84-condition acceptance or main promotion.",
        ],
    }
    return draft, handoff


def persist(directory: Path, name: str, value: Any) -> None:
    raw = canonical(value)
    path = directory / name
    if path.exists():
        require(path.read_bytes() == raw, "Existing handoff differs; use a new reviewed output directory.")
        return
    with path.open("xb") as stream:
        stream.write(raw)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["prepare", "agent-handoff"])
    parser.add_argument("--environment", required=True, choices=["dev", "test", "prod"])
    for name in ("scope", "inventory", "owned-state", "output-dir"):
        parser.add_argument("--" + name, required=True, type=Path)
    destination = parser.add_mutually_exclusive_group()
    destination.add_argument("--target-folder-id", help="Defaults to the explicitly approved root folder.")
    destination.add_argument("--temp-folder-id", help="Legacy explicit evaluation-only Temp placement; not the production default.")
    for name in ("compat-receipt", "compat-definition", "graph-evidence", "frozen-agent-definition"):
        parser.add_argument("--" + name, type=Path)
    parser.add_argument("--stage", choices=["draft", "published"])
    args = parser.parse_args()
    try:
        scope = scope_from_document(load(args.scope), args.environment)
        inventory, owned = load(args.inventory), load(args.owned_state)
        target_folder_id = args.target_folder_id or args.temp_folder_id or scope["folderId"]
        output = private_directory(args.output_dir)
        require(not any((output / name).exists() for name in ("approval.json", "create-intent.json", "created.json")),
                "An approved/attempted output directory is immutable; do not regenerate.")
        if args.command == "prepare":
            body, plan = prepare(scope, inventory, owned, target_folder_id)
            persist(output, "compat-create-body.json", body)
            persist(output, "compat-plan.json", plan)
            print(json.dumps({"status": plan["status"], "planSha256": plan["planSha256"],
                              "bodySha256": plan["create"]["bodySha256"], "cloudCalls": 0}, indent=2))
        else:
            require(all((args.compat_receipt, args.compat_definition, args.graph_evidence,
                         args.frozen_agent_definition, args.stage)), "Agent handoff requires all explicit frozen readbacks and --stage.")
            draft, handoff = agent_handoff(
                scope, inventory, owned, target_folder_id, load(args.compat_receipt),
                load(args.compat_definition), load(args.graph_evidence), load(args.frozen_agent_definition), args.stage)
            persist(output, "compat-agent-draft-definition.json", draft)
            persist(output, "compat-agent-handoff.json", handoff)
            print(json.dumps({"status": handoff["status"], "candidateDraftSha256": handoff["candidateDraftSha256"],
                              "globalUtf8Sha256": handoff["globalUtf8Sha256"], "cloudCalls": 0}, indent=2))
        return 0
    except (SafetyError, ValueError, KeyError) as exc:
        print("STOP: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
