"""Gate-aware adapter around the unchanged, regression-tested native lifecycle."""
from __future__ import annotations
import base64
import hashlib
import json
import csv
from pathlib import Path
from typing import Any
from preview30_deploy import Deployment, kusto_call
from preview30_runtime import BASE, SafetyError, load, now, save


def _targets(d: Deployment, *, require_delivery_ready: bool = False) -> tuple[dict, str]:
    activator = d.require_owned("activator")
    pipeline = d.require_owned("pipeline")
    lakehouse = d.require_owned("lakehouse")
    definition = d.definition(activator["id"], skill="activator-cli")
    encoded = next(p["payload"] for p in definition["parts"] if p["path"] == "ReflexEntities.json")
    entities = json.loads(base64.b64decode(encoded))
    rules = [e for e in entities if e.get("payload", {}).get("definition", {}).get("type") == "Rule"]
    sources = [e for e in entities if e.get("type") == "realTimeHubSource-v1"]
    actions = [e for e in entities if e.get("type") == "fabricItemAction-v1"]
    if len(rules) != 1 or len(sources) != 1 or len(actions) != 1:
        raise SafetyError("The owned Activator must have exactly one rule/source/action.")
    connection = sources[0]["payload"]["connection"]
    target = actions[0]["payload"]["fabricItem"]
    if (connection["artifactId"] != lakehouse["id"] or connection["workspaceId"] != d.scope["workspaceId"]
            or target["itemId"] != pipeline["id"] or target["workspaceId"] != d.scope["workspaceId"]):
        raise SafetyError("Native lifecycle target differs from the frozen Lakehouse/Pipeline.")
    if require_delivery_ready:
        settings = rules[0]["payload"]["definition"].get("settings", {})
        delay = settings.get("delayToleranceMs")
        if (settings.get("shouldRun") is not True
                or settings.get("shouldApplyRuleOnUpdate") is not False
                or type(delay) is not int or delay < 120000):
            raise SafetyError(
                "Native delivery settings are not ready: confirm Edit action > Apply > Save, "
                "formal Start, historical application disabled, and explicit delay tolerance "
                "of at least 120000 ms. These settings are not delivery proof; do not upload yet."
            )
    return activator, rules[0]["uniqueIdentifier"]


def lifecycle(args: Any, *, start: bool) -> dict[str, Any]:
    from activation_runtime import ActivatorLifecycle
    d = Deployment(args)
    activator, rule_id = _targets(d)
    action = "start" if start else "stop"
    previous = d.state.get("nativeLifecycle")
    if previous and previous.get("action") == action:
        if previous.get("status") == "verified":
            raise SafetyError("This lifecycle action already has a receipt; use status/readback rather than repeating it.")
        raise SafetyError("Previous native lifecycle write is uncertain. Reconcile; no automatic retry.")
    d.state["nativeLifecycle"] = {"action": action, "status": "pending", "timestampUtc": now()}
    d.checkpoint()
    private = d.evidence / "activation" / (action + "-" + now().replace(":", "").replace("+", "_"))
    token = lambda: d.client.credential.get_token("https://api.fabric.microsoft.com/.default").token
    native = ActivatorLifecycle(d.scope["workspaceId"], activator["id"], token, private)
    # Keep legacy lifecycle code byte-for-byte; attribution is supplied by this adapter.
    native.headers["x-ms-fabric-skill"] = "activator-cli"
    try:
        native.connect()
        result = native.set_running(rule_id, start)
    finally:
        native.close()
    d.state["nativeLifecycle"] = {"action": action, "status": "verified",
                                 "timestampUtc": now(), "result": result}
    d.checkpoint()
    return result  # start returns armed_unverified, never delivery success.


def deliver_increment(args: Any) -> dict[str, Any]:
    from activation_runtime import PrivateStore, put_complete_increment
    d = Deployment(args)
    _, rule_id = _targets(d, require_delivery_ready=True)
    number = getattr(args, "increment", None)
    if number not in {1, 2, 3}:
        raise SafetyError("Select exactly one increment (1, 2, or 3).")
    lifecycle_receipt = d.state.get("nativeLifecycle", {})
    if lifecycle_receipt.get("action") != "start" or lifecycle_receipt.get("status") != "verified":
        raise SafetyError("A verified formal native start receipt is required before PutBlob.")
    if lifecycle_receipt.get("result", {}).get("state") != "armed_unverified":
        raise SafetyError("The formal start state is not armed_unverified.")
    deliveries = d.state.setdefault("incrementDeliveries", {})
    filename = f"donation_events_{number:03d}.csv"
    if filename in deliveries:
        raise SafetyError("This increment already has an intent/receipt. Inspect, never replay.")
    if number > 1:
        prior = deliveries.get(f"donation_events_{number - 1:03d}.csv", {})
        if prior.get("state") != "native-copy-kql-verified":
            raise SafetyError("Previous increment lacks native FileCreated/activation/job/Copy/KQL proof.")
    pipeline = d.state["items"]["pipeline"]
    before = d.client.paged(d.prefix + f"/items/{pipeline['id']}/jobs/instances")
    lh = d.state["items"]["lakehouse"]
    details = d.client.request("GET", d.prefix + f"/lakehouses/{lh['id']}").json()
    raw = (BASE / "data/increment" / filename).read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    private = d.evidence / "increments" / filename
    save(private / "jobs-before.json", before)
    deliveries[filename] = {"state": "pending", "timestampUtc": now(), "ruleId": rule_id,
                            "sha256": sha, "bytes": len(raw)}
    d.checkpoint()
    result = put_complete_increment(
        one_lake_files_path=details["properties"]["oneLakeFilesPath"],
        workspace_id=d.scope["workspaceId"], lakehouse_id=lh["id"], filename=filename,
        content=raw, expected_sha256=sha,
        token_provider=lambda: d.client.credential.get_token("https://storage.azure.com/.default").token,
        store=PrivateStore(private / "upload"), session=d.client.session,
    )
    deliveries[filename].update({"state": "uploaded-unverified", "upload": result})
    d.checkpoint()
    return {**result, "nextStep": "Capture native event/activation/new Completed job/Copy/KQL; do not upload next file yet.",
            "manualPipelineFallbackAllowed": False}


def verify_delivery(args: Any) -> dict[str, Any]:
    """Validate provided native event/Copy exports against fresh activation, job and KQL reads."""
    from activation_runtime import ActivatorLifecycle, verify_automatic_delivery
    from reference_kql import kusto_result_rows
    if not getattr(args, "native_events", None) or not getattr(args, "native_copy", None):
        raise SafetyError("Actual native FileCreated events and Copy activity exports are mandatory; screenshots alone are insufficient.")
    d = Deployment(args)
    number = getattr(args, "increment", None)
    if number not in {1, 2, 3}:
        raise SafetyError("Select one increment (1..3).")
    filename = f"donation_events_{number:03d}.csv"
    delivery = d.state.get("incrementDeliveries", {}).get(filename)
    if not delivery or delivery.get("state") != "uploaded-unverified":
        raise SafetyError("No unverified complete-file receipt exists for this increment.")
    native_events = load(args.native_events)
    native_copy = load(args.native_copy)
    if not isinstance(native_events, list) or not isinstance(native_copy, dict):
        raise SafetyError("Expected native events array and native Copy activity record.")
    activator, rule_id = _targets(d)
    pipeline = d.state["items"]["pipeline"]
    before = load(d.evidence / "increments" / filename / "jobs-before.json")
    after = d.client.paged(d.prefix + f"/items/{pipeline['id']}/jobs/instances")
    token = lambda: d.client.credential.get_token("https://api.fabric.microsoft.com/.default").token
    native = ActivatorLifecycle(d.scope["workspaceId"], activator["id"], token,
                                d.evidence / "increments" / filename / "native-history")
    native.headers["x-ms-fabric-skill"] = "activator-cli"
    try:
        native.connect()
        history = native.history(rule_id, delivery["timestampUtc"], now())
    finally:
        native.close()
    matching = [e for e in native_events if e.get("___subject") == "/Files/increment/" + filename]
    if len(matching) != 1:
        raise SafetyError("Native FileCreated export lacks one exact subject.")
    source = matching[0].get("___source", "")
    lh = d.state["items"]["lakehouse"]
    if not source.endswith(f"/workspaces/{d.scope['workspaceId']}/items/{lh['id']}"):
        raise SafetyError("Native FileCreated event references a different source Lakehouse.")
    result = verify_automatic_delivery(
        workspace_id=d.scope["workspaceId"], pipeline_id=pipeline["id"], rule_id=rule_id,
        subject="/Files/increment/" + filename, source=source, expected_bytes=delivery["bytes"],
        uploaded_bytes_verified=delivery["upload"].get("uploadedBytesVerified") is True,
        events=native_events, history=history, jobs_before=before, jobs_after=after,
        manual_job_ids=set(d.state.get("manualPipelineJobIds", [])),
    )
    if (native_copy.get("pipelineRunId") != result["pipelineJobId"]
            or native_copy.get("activityType") != "Copy" or native_copy.get("status") != "Succeeded"
            or int(native_copy.get("output", {}).get("rowsRead", -1)) != 5000
            or int(native_copy.get("output", {}).get("rowsCopied", -1)) != 5000):
        raise SafetyError("Native Copy activity does not prove the correlated 5,000-row copy.")
    with (BASE / "data/increment" / filename).open(encoding="utf-8", newline="") as handle:
        raw = list(csv.DictReader(handle))
    source_files = {r["SourceFile"] for r in raw}
    runs = {r["WorkshopRunId"] for r in raw}
    if len(source_files) != 1 or len(runs) != 1:
        raise SafetyError("Canonical increment has ambiguous provenance.")
    csl = ("DonationEvents | where SourceFile == " + json.dumps(next(iter(source_files)))
           + " and WorkshopRunId == " + json.dumps(next(iter(runs)))
           + " | summarize RawRows=count(), RawYen=sum(DonationAmountYen)")
    rows = kusto_result_rows(kusto_call(d, csl), required_columns=("RawRows", "RawYen"))
    if len(rows) != 1 or rows[0] != {"RawRows": len(raw), "RawYen": sum(int(r["DonationAmountYen"]) for r in raw)}:
        raise SafetyError("KQL did not reconcile the exact native file/run scope to its immutable CSV.")
    result.update({"timestampUtc": now(), "copyAndDataVerified": True,
                   "copyEvidenceKind": "provided-native-export-validated",
                   "kql": rows[0], "state": "native-copy-kql-verified"})
    private = d.evidence / "increments" / filename
    save(private / "native-events-validated.json", native_events)
    save(private / "native-copy-validated.json", native_copy)
    save(private / "jobs-after.json", after)
    save(private / "verification.json", result)
    d.state["incrementDeliveries"][filename].update({"state": result["state"], "verification": result})
    d.checkpoint()
    return result
