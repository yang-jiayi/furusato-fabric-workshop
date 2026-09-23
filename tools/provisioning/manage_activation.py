"""Discover, formally start or stop one workshop FileCreated rule.

Start/stop are preview-only without --apply and an exact confirmation phrase.
This command never uploads data, runs a Pipeline, changes a definition or resumes
capacity. Running metadata produces armed_unverified, not ingestion success.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any

from activation_runtime import (
    ActivationError, ActivatorLifecycle, CONTRACT, FILE_CREATED, PrivateStore,
    encode, guid, utc_now, verify_automatic_delivery,
)
from workshop_runtime import ProvisioningError, WorkshopFabricClient, build_names


def resolve_scope(client: WorkshopFabricClient, workspace_id: str, folder_id: str, participant_id: str, expected_workspace_name: str):
    workspace_id, folder_id = guid(workspace_id), guid(folder_id)
    names = build_names(participant_id)
    base = f"https://api.fabric.microsoft.com/v1/workspaces/{workspace_id}"
    workspace = client._request("GET", base).json()
    if not expected_workspace_name or workspace.get("displayName") != expected_workspace_name:
        raise ActivationError("Workspace name does not match the explicitly selected workspace.")
    client._request("GET", base + "/folders/" + folder_id)
    items = client.list_items(workspace_id, folder_id=folder_id)
    selected = {}
    for key, item_type, name in (
        ("lakehouse", "Lakehouse", names.lakehouse),
        ("pipeline", "DataPipeline", names.pipeline),
        ("activator", "Reflex", names.reflex),
    ):
        matches = [item for item in items if item.get("type") == item_type and item.get("displayName") == name]
        if len(matches) != 1:
            raise ActivationError(f"Expected exactly one {item_type} with the participant name in the selected folder.")
        selected[key] = client.require_item_in_folder(
            workspace_id, matches[0], folder_id=folder_id, item_type=item_type, display_name=name,
        )
    definition = client.get_definition(workspace_id, selected["activator"]["id"])
    parts = [part for part in definition.get("parts", []) if part.get("path") == "ReflexEntities.json"]
    if len(parts) != 1 or parts[0].get("payloadType") != "InlineBase64":
        raise ActivationError("Activator definition is not the supported complete entity graph.")
    try:
        entities = json.loads(base64.b64decode(parts[0]["payload"], validate=True))
    except (ValueError, UnicodeError) as exc:
        raise ActivationError("Activator definition is malformed.") from exc
    if not isinstance(entities, list):
        raise ActivationError("Activator entities are not an array.")
    rules = [entity for entity in entities if entity.get("payload", {}).get("definition", {}).get("type") == "Rule"]
    events = [entity for entity in entities if entity.get("payload", {}).get("definition", {}).get("type") == "Event"]
    containers = [entity for entity in entities if entity.get("type") == "container-v1"]
    sources = [entity for entity in entities if entity.get("type") == "realTimeHubSource-v1"]
    actions = [entity for entity in entities if entity.get("type") == "fabricItemAction-v1"]
    if len(entities) != 5 or any(len(group) != 1 for group in (rules, events, containers, sources, actions)):
        raise ActivationError("Expected the single released FileCreated rule/source/action; inspect other graphs manually.")
    rule, source, action = rules[0], sources[0]["payload"], actions[0]
    connection = source.get("connection", {})
    if (
        connection.get("scope") != "Artifact" or connection.get("workspaceId") != workspace_id
        or connection.get("artifactId") != selected["lakehouse"]["id"]
        or connection.get("eventGroupType") != "Microsoft.Fabric.OneLakeEvents"
    ):
        raise ActivationError("The event source does not match the selected participant lakehouse.")
    filters = source.get("filterSettings", {})
    if filters.get("eventTypes") != [{"name": FILE_CREATED}]:
        raise ActivationError("The rule is not scoped exclusively to FileCreated.")
    expected_filters = {
        ("subject", "StringBeginsWith", ("/Files/increment",)),
        ("subject", "StringEndsWith", (".csv",)),
    }
    observed_filters = {
        (item.get("key"), item.get("operatorType"), tuple(item.get("values", [])))
        for item in filters.get("filters", [])
    }
    if observed_filters != expected_filters or len(filters.get("filters", [])) != 2:
        raise ActivationError("The watched folder or CSV filter differs from the released contract.")
    fabric_item = action["payload"].get("fabricItem", {})
    if (
        fabric_item.get("workspaceId") != workspace_id or fabric_item.get("itemId") != selected["pipeline"]["id"]
        or fabric_item.get("itemType") != "Pipeline" or action["payload"].get("jobType") != "Pipeline"
    ):
        raise ActivationError("The action does not target the selected participant Pipeline.")
    if rule["payload"]["definition"].get("settings", {}).get("shouldApplyRuleOnUpdate") is not False:
        raise ActivationError("Historical rule reprocessing is not authorized by this workflow.")
    instance = json.loads(rule["payload"]["definition"]["instance"])
    event_instance = json.loads(events[0]["payload"]["definition"]["instance"])
    source_selectors = [row for step in event_instance.get("steps", []) for row in step.get("rows", [])]
    if (
        len(source_selectors) != 1 or source_selectors[0].get("kind") != "SourceReference"
        or source_selectors[0].get("arguments") != [{"name": "entityId", "type": "string", "value": sources[0]["uniqueIdentifier"]}]
    ):
        raise ActivationError("The source event does not resolve to the selected event subscription.")
    event_selectors = [
        row for step in instance.get("steps", []) if step.get("name") == "FieldsDefaultsStep"
        for row in step.get("rows", [])
    ]
    if len(event_selectors) != 1:
        raise ActivationError("The rule's source-event selection is ambiguous.")
    selectors = event_selectors[0].get("arguments", [])
    if len(selectors) != 1 or selectors[0].get("arguments") != [
        {"name": "entityId", "type": "string", "value": events[0]["uniqueIdentifier"]}
    ]:
        raise ActivationError("The rule refers to a different source event.")
    action_rows = [row for step in instance.get("steps", []) if step.get("name") == "ActStep" for row in step.get("rows", [])]
    invocations = [row for step in instance.get("steps", []) for row in step.get("rows", []) if row.get("kind") == "FabricItemInvocation"]
    if instance.get("templateId") != "EventTrigger" or len(invocations) != 1 or action_rows != invocations:
        raise ActivationError("The rule action is not the supported EventTrigger.")
    arguments = {argument["name"]: argument for argument in invocations[0].get("arguments", [])}
    for key, expected in (
        ("workspaceId", workspace_id), ("itemId", selected["pipeline"]["id"]),
        ("itemType", "Pipeline"), ("jobType", "Pipeline"),
        ("fabricJobConnectionDocumentId", action["uniqueIdentifier"]),
    ):
        if arguments.get(key, {}).get("value") != expected:
            raise ActivationError("The rule's action reference is inconsistent.")
    parameters = arguments.get("parameters", {}).get("values", [])
    for name, field_name in (("Type", "___type"), ("Subject", "___subject"), ("Source", "___source")):
        matches = [
            parameter for parameter in parameters
            if any(arg.get("name") == "parameterName" and arg.get("value") == name for arg in parameter.get("arguments", []))
        ]
        if len(matches) != 1:
            raise ActivationError("Required dynamic event parameters are missing or duplicated.")
        args = {arg["name"]: arg for arg in matches[0]["arguments"]}
        values = args.get("parameterValue", {}).get("values", [])
        if (
            args.get("parameterType", {}).get("value") != "String" or len(values) != 1
            or values[0].get("kind") != "EventFieldReference" or values[0].get("type") != "complexReference"
            or values[0].get("arguments") != [{"name": "fieldName", "type": "string", "value": field_name}]
        ):
            raise ActivationError("An event argument is not mapped to its native event field.")
    scope = {
        "contract": CONTRACT, "workspaceId": workspace_id, "workspaceName": expected_workspace_name,
        "folderId": folder_id, "participantId": participant_id,
        "lakehouseId": selected["lakehouse"]["id"], "pipelineId": selected["pipeline"]["id"],
        "activatorId": selected["activator"]["id"], "ruleId": guid(rule["uniqueIdentifier"]),
        "definitionSha256": hashlib.sha256(encode(definition)).hexdigest(),
        "configuredShouldRun": rule["payload"]["definition"]["settings"].get("shouldRun"),
    }
    return scope, definition


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    doctor = subparsers.add_parser("doctor", help="Offline dependency check; no authentication or network.")
    verify = subparsers.add_parser("verify", help="Offline native automatic-delivery evidence validation.")
    verify.add_argument("--private-root", type=Path, required=True)
    verify.add_argument("--input", required=True, help="JSON path relative to the private evidence root.")
    verify.add_argument("--out", required=True, help="New result path relative to the private evidence root.")
    for command in ("status", "start", "stop"):
        child = subparsers.add_parser(command)
        child.add_argument("--workspace-id", required=True)
        child.add_argument("--expected-workspace-name", required=True)
        child.add_argument("--folder-id", required=True, help="Folder GUID, not the portal numeric subfolderId.")
        child.add_argument("--participant-id", required=True)
        child.add_argument("--private-root", type=Path, required=True)
        child.add_argument("--run", required=True, help="Fresh ASCII operation label; never reused.")
        child.add_argument("--tenant-id")
        if command != "status":
            child.add_argument("--apply", action="store_true")
            child.add_argument("--confirmation", default="")
    args = parser.parse_args(argv)
    try:
        if args.command == "doctor":
            import requests
            import azure.identity
            print(json.dumps({"contract": CONTRACT, "requests": requests.__version__, "authentication": "AzureCliCredential", "networkCalls": 0}))
            return 0
        store = PrivateStore(args.private_root)
        if args.command == "verify":
            evidence = store.read(args.input)
            evidence["manual_job_ids"] = set(evidence["manual_job_ids"])
            result = verify_automatic_delivery(**evidence)
            store.write(args.out, result)
            print(json.dumps(result, ensure_ascii=False))
            return 0
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,63}", args.run):
            raise ActivationError("Use a fresh short ASCII run label, not a path.")
        guid(args.workspace_id)
        guid(args.folder_id)
        build_names(args.participant_id)
        mutation = args.command != "status" and args.apply
        if mutation and args.confirmation != f"{args.command.upper()} ACTIVATOR {args.participant_id}":
            raise ActivationError("Explicit confirmation does not match the selected operation and participant.")
        operation_root = store.path(f"operations/{args.run}")
        operation = PrivateStore(operation_root)
        operation.write("intent.json", {
            "atUtc": utc_now(), "command": args.command, "apply": mutation,
            "workspaceId": args.workspace_id, "expectedWorkspaceName": args.expected_workspace_name,
            "folderId": args.folder_id, "participantId": args.participant_id,
        })
        from azure.identity import AzureCliCredential
        import requests
        credential = AzureCliCredential(process_timeout=45, **({"tenant_id": guid(args.tenant_id)} if args.tenant_id else {}))
        session = requests.Session()
        session.trust_env = False
        tokens = lambda: credential.get_token("https://api.fabric.microsoft.com/.default").token
        try:
            client = WorkshopFabricClient(tokens, tokens, session=session, timeout_seconds=120)
            scope, definition = resolve_scope(client, args.workspace_id, args.folder_id, args.participant_id, args.expected_workspace_name)
            operation.write("scope.json", scope)
            operation.write("definition-before.json", definition)
            if not mutation:
                result = {"mode": "ReadOnly", "scope": scope, "requestedOperation": args.command, "automaticDeliveryVerified": False}
            else:
                workspace = client._request("GET", f"https://api.fabric.microsoft.com/v1/workspaces/{args.workspace_id}").json()
                capacities = client._paged("https://api.fabric.microsoft.com/v1/capacities")
                capacity = [item for item in capacities if item.get("id") == workspace.get("capacityId")]
                if len(capacity) != 1 or capacity[0].get("state") != "Active":
                    raise ActivationError("The selected workspace capacity is not verifiably Active; no lifecycle write was sent.")
                lifecycle = ActivatorLifecycle(args.workspace_id, scope["activatorId"], tokens, operation_root / "mcp")
                try:
                    lifecycle.connect()
                    result = {"scope": scope, **lifecycle.set_running(scope["ruleId"], args.command == "start")}
                finally:
                    lifecycle.close()
            operation.write("result.json", result)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        finally:
            session.close()
    except (ActivationError, ProvisioningError, OSError, KeyError, TypeError, ValueError) as exc:
        print(f"Activation workflow failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
