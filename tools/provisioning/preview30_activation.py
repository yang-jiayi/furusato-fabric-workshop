"""Gate-aware adapter around the unchanged, regression-tested native lifecycle."""
from __future__ import annotations
import base64
import hashlib
import json
import csv
from collections import Counter
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
    activator, rule_id = _targets(d, require_delivery_ready=True)
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
    from preview30_activation_readiness import capture_readiness
    readiness = capture_readiness(d, activator, rule_id)
    private = d.evidence / "increments" / filename
    save(private / "jobs-before.json", before)
    deliveries[filename] = {"state": "pending", "timestampUtc": now(), "ruleId": rule_id,
                            "sha256": sha, "bytes": len(raw), "backendReadiness": readiness}
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


def _expected_increment_reconciliation(number: int) -> dict[str, int]:
    records: list[dict[str, str]] = []
    for index in range(1, number + 1):
        path = BASE / "data/increment" / f"donation_events_{index:03d}.csv"
        with path.open(encoding="utf-8", newline="") as handle:
            records.extend(csv.DictReader(handle))
    multiplicities = Counter(row["EventID"] for row in records)
    return {
        "RawRows": len(records),
        "RawYen": sum(int(row["DonationAmountYen"]) for row in records),
        "UniqueEventIDs": len(multiplicities),
        "DuplicateKeys": sum(count > 1 for count in multiplicities.values()),
        "DuplicateRows": sum(count - 1 for count in multiplicities.values() if count > 1),
        "MissingEventIDs": sum(not row["EventID"] for row in records),
    }


def _verify_cumulative_kql(d: Deployment, number: int) -> dict[str, int]:
    from reference_kql import kusto_result_rows
    expected = _expected_increment_reconciliation(number)
    conditions = []
    for index in range(1, number + 1):
        filename = f"donation_events_{index:03d}.csv"
        with (BASE / "data/increment" / filename).open(encoding="utf-8", newline="") as handle:
            source = list(csv.DictReader(handle))
        source_files = {row["SourceFile"] for row in source}
        runs = {row["WorkshopRunId"] for row in source}
        if len(source_files) != 1 or len(runs) != 1:
            raise SafetyError("Canonical increments have ambiguous cumulative provenance.")
        conditions.append(
            "(SourceFile == " + json.dumps(next(iter(source_files)))
            + " and WorkshopRunId == " + json.dumps(next(iter(runs))) + ")"
        )
    scoped = "DonationEvents | where " + " or ".join(conditions)
    totals = kusto_result_rows(
        kusto_call(
            d, scoped + " | summarize RawRows=count(), RawYen=sum(DonationAmountYen), "
            "MissingEventIDs=countif(isempty(EventID))",
        ),
        required_columns=("RawRows", "RawYen", "MissingEventIDs"),
    )
    multiplicities = kusto_result_rows(
        kusto_call(
            d, scoped + " | summarize Multiplicity=count() by EventID "
            "| summarize UniqueEventIDs=count(), DuplicateKeys=countif(Multiplicity > 1), "
            "DuplicateRows=sumif(Multiplicity - 1, Multiplicity > 1)",
        ),
        required_columns=("UniqueEventIDs", "DuplicateKeys", "DuplicateRows"),
    )
    if len(totals) != 1 or len(multiplicities) != 1:
        raise SafetyError("Fresh cumulative KQL did not return one exact reconciliation row.")
    actual = {**totals[0], **multiplicities[0]}
    if actual != expected:
        raise SafetyError("Exact cumulative KQL rows, amount, EventIDs, or duplicates differ from released increments.")
    return actual


def verify_delivery(args: Any) -> dict[str, Any]:
    """Validate native event exports or explicitly tagged UI evidence against fresh reads."""
    from activation_runtime import (
        ActivatorLifecycle, PrivateStore, parse_time, verify_automatic_delivery,
        verify_automatic_delivery_fields,
    )
    from reference_kql import kusto_result_rows
    if not getattr(args, "native_events", None) or not getattr(args, "native_copy", None):
        raise SafetyError("Provide native FileCreated evidence and a native Copy activity receipt.")
    PrivateStore._reject_git_path(args.native_events.resolve())
    PrivateStore._reject_git_path(args.native_copy.resolve())
    d = Deployment(args)
    number = getattr(args, "increment", None)
    if number not in {1, 2, 3}:
        raise SafetyError("Select one increment (1..3).")
    filename = f"donation_events_{number:03d}.csv"
    delivery = d.state.get("incrementDeliveries", {}).get(filename)
    if not delivery or delivery.get("state") != "uploaded-unverified":
        raise SafetyError("No unverified complete-file receipt exists for this increment.")
    native_input = load(args.native_events)
    native_copy = load(args.native_copy)
    if not isinstance(native_copy, dict):
        raise SafetyError("Expected one native Copy activity record.")
    is_ui_observation = (
        isinstance(native_input, dict)
        and native_input.get("kind") == "native-ui-observation-not-csv-export"
    )
    if not isinstance(native_input, list) and not is_ui_observation:
        raise SafetyError("Expected the unchanged native event array or a tagged native UI observation.")
    if is_ui_observation and (not getattr(args, "native_ui_receipt_root", None)
                              or not getattr(args, "native_ui_control_classification", None)):
        raise SafetyError("Tagged UI evidence requires its receipt root and control classification.")
    if is_ui_observation:
        PrivateStore._reject_git_path(args.native_ui_control_classification.resolve())
        correlation_candidate = None
        visual_review = None
        correlation_path = getattr(args, "native_ui_correlation", None)
        if number == 1:
            if correlation_path:
                raise SafetyError("001 correlation remains embedded in its original observation.")
        else:
            if not correlation_path:
                raise SafetyError("002/003 require a separate hash-bound correlation sidecar.")
            PrivateStore._reject_git_path(correlation_path.resolve())
            correlation = load(correlation_path)
            observation_sha256 = hashlib.sha256(args.native_events.read_bytes()).hexdigest()
            if (not isinstance(correlation, dict)
                    or correlation.get("kind") != "native-ui-correlation-sidecar/v1"
                    or correlation.get("filename") != filename
                    or correlation.get("sourceObservationSha256") != observation_sha256
                    or not isinstance(correlation.get("scope"), dict)
                    or not isinstance(correlation.get("correlationCandidate"), dict)
                    or not isinstance(correlation.get("visualReview"), dict)):
                raise SafetyError("Correlation sidecar does not bind this exact observation and increment.")
            correlation_candidate = correlation["correlationCandidate"]
            visual_review = correlation["visualReview"]
    activator, rule_id = _targets(d)
    pipeline = d.state["items"]["pipeline"]
    lakehouse = d.state["items"]["lakehouse"]
    if is_ui_observation and number > 1:
        expected_scope = {
            "workspaceId": d.scope["workspaceId"],
            "tenantId": d.scope["tenantId"],
            "folderId": d.scope["folderId"],
            "activatorId": activator["id"],
            "pipelineId": pipeline["id"],
            "lakehouseId": lakehouse["id"],
            "modelId": native_input["modelId"],
        }
        if correlation["scope"] != expected_scope:
            raise SafetyError("Correlation sidecar scope differs from the frozen deployment items.")
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
    subject = "/Files/increment/" + filename
    private = d.evidence / "increments" / filename
    if is_ui_observation:
        from native_ui_observation import validate_control_classification, validate_observation
        current_definition = d.definition(activator["id"], skill="activator-cli")
        proof = validate_observation(
            native_input, screenshot_root=args.native_events.resolve().parent,
            receipt_root=args.native_ui_receipt_root, workspace_id=d.scope["workspaceId"],
            tenant_id=d.scope["tenantId"], activator_id=activator["id"],
            model_id=native_input["modelId"],
            rule_id=rule_id, pipeline_id=pipeline["id"], lakehouse_id=lakehouse["id"],
            subject=subject, expected_bytes=delivery["bytes"],
            expected_upload_sha256=delivery["upload"].get("sha256"),
            current_definition=current_definition,
            expected_filename=filename, expected_visible_row_count=number,
            correlation_candidate=correlation_candidate, visual_review=visual_review,
        )
        classification = load(args.native_ui_control_classification)
        known_manual_ids = set(d.state.get("manualPipelineJobIds", []))
        classified = validate_control_classification(
            classification, known_manual_job_ids=known_manual_ids,
        )
        copy_receipt_path = proof["copyReceiptPath"]
        copy_sha = proof["receiptSha256"][copy_receipt_path]
        if hashlib.sha256(args.native_copy.read_bytes()).hexdigest() != copy_sha or native_copy != proof["copyReceipt"]:
            raise SafetyError("Provided Copy receipt differs from the original hash-bound native Copy receipt.")
        if history.get("isError") or not isinstance(history.get("activations"), list):
            raise SafetyError("Fresh native activation history is unavailable or malformed.")
        current_matches = [
            row for row in history["activations"]
            if row.get("properties", {}).get("System.Action.FabricItem.Parameters.Subject.String") == subject
        ]
        if (len(current_matches) != 1
                or current_matches[0].get("properties", {}).get("___id") != proof["activationId"]
                or current_matches[0].get("properties", {}).get("System.RuleVersion") != proof["activationRuleVersion"]
                or current_matches[0].get("properties", {}).get("System.Action.FabricItem.Parameters.Source.String")
                != proof["sourceFromBoundActivation"]
                or current_matches[0].get("properties", {}).get("System.Action.FabricItem.Parameters.Type.String")
                != proof["eventType"]
                or current_matches[0].get("properties", {}).get("System.Action.FabricItem.WorkspaceId")
                != d.scope["workspaceId"]
                or current_matches[0].get("properties", {}).get("System.Action.FabricItem.ItemId")
                != pipeline["id"]
                or current_matches[0].get("properties", {}).get("System.Action.FabricItem.ItemType")
                != "Pipeline"
                or current_matches[0].get("properties", {}).get("System.Action.FabricItem.JobType")
                != "Pipeline"
                or parse_time(current_matches[0].get("activationTime")) != parse_time(proof["eventTimeUtc"])):
            raise SafetyError("Fresh activation history differs from the unique hash-bound event-time activation.")
        result = verify_automatic_delivery_fields(
            workspace_id=d.scope["workspaceId"], pipeline_id=pipeline["id"], rule_id=rule_id,
            subject=subject, source=proof["sourceFromBoundActivation"], expected_bytes=delivery["bytes"],
            uploaded_bytes_verified=delivery["upload"].get("uploadedBytesVerified") is True,
            event_id=proof["eventId"], event_type=proof["eventType"],
            event_source=proof["sourceFromBoundActivation"], event_api=proof["eventApi"],
            event_content_length=proof["contentLength"], event_time=proof["eventTimeUtc"],
            history=history, jobs_before=before, jobs_after=after,
            manual_job_ids=set(classified["knownManualControlJobIds"]),
        )
        classification_sha = hashlib.sha256(args.native_ui_control_classification.read_bytes()).hexdigest()
        evidence_kind = "native-ui-observation-correlated-not-direct-id"
        result.update({
            "eventEvidenceKind": evidence_kind,
            "directEventIdInActivation": False,
            "eventCorrelation": "unique timestamp and event fields, current/event-time EventReference and EventFieldReference wiring, scoped operating-session classification",
            "ruleDefinitionSha256": hashlib.sha256(
                json.dumps(current_definition, sort_keys=True, ensure_ascii=False).encode("utf-8")
            ).hexdigest(),
            "controlClassificationSha256": classification_sha,
            "controlClassification": classified,
            "observedJobInvokeType": next(
                (job.get("invokeType") for job in after if job.get("id") == result["pipelineJobId"]), None,
            ),
            "screenshotSha256": proof["screenshotSha256"],
            "sourceReceiptSha256": proof["receiptSha256"],
            "uploadSha256": proof["uploadSha256"],
            "nativeUiObservationSha256": hashlib.sha256(args.native_events.read_bytes()).hexdigest(),
            "nativeUiCorrelationSha256": (
                hashlib.sha256(correlation_path.read_bytes()).hexdigest() if correlation_path else None
            ),
            "jobsBeforeSha256": hashlib.sha256(
                json.dumps(before, sort_keys=True, ensure_ascii=False).encode("utf-8")
            ).hexdigest(),
            "jobsAfterSha256": hashlib.sha256(
                json.dumps(after, sort_keys=True, ensure_ascii=False).encode("utf-8")
            ).hexdigest(),
            "freshActivationHistorySha256": hashlib.sha256(
                json.dumps(history, sort_keys=True, ensure_ascii=False).encode("utf-8")
            ).hexdigest(),
        })
        copy_evidence_kind = "hash-bound-native-copy-receipt-validated"
    else:
        matching = [event for event in native_input if event.get("___subject") == subject]
        if len(matching) != 1:
            raise SafetyError("Native FileCreated export lacks one exact subject.")
        source = matching[0].get("___source", "")
        if not source.endswith(f"/workspaces/{d.scope['workspaceId']}/items/{lakehouse['id']}"):
            raise SafetyError("Native FileCreated event references a different source Lakehouse.")
        result = verify_automatic_delivery(
            workspace_id=d.scope["workspaceId"], pipeline_id=pipeline["id"], rule_id=rule_id,
            subject=subject, source=source, expected_bytes=delivery["bytes"],
            uploaded_bytes_verified=delivery["upload"].get("uploadedBytesVerified") is True,
            events=native_input, history=history, jobs_before=before, jobs_after=after,
            manual_job_ids=set(d.state.get("manualPipelineJobIds", [])),
        )
        evidence_kind = "provided-native-export-validated"
        copy_evidence_kind = evidence_kind
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
    if is_ui_observation:
        expected_totals = {"RawRows": len(raw), "RawYen": sum(int(r["DonationAmountYen"]) for r in raw)}
        if number == 1:
            before_path = private / "observation-01" / "kql-totals.json"
            after_path = private / "bounded-monitor-01" / "kql-totals.json"
            before_kql = load(before_path)
            after_kql = load(after_path)
            before_value = before_kql[0] if isinstance(before_kql, list) and len(before_kql) == 1 else None
            after_value = after_kql[0] if isinstance(after_kql, list) and len(after_kql) == 1 else None
            before_sha = hashlib.sha256(before_path.read_bytes()).hexdigest()
            after_sha = hashlib.sha256(after_path.read_bytes()).hexdigest()
            if before_value != {"RawRows": 0, "RawYen": 0} or after_value != expected_totals:
                raise SafetyError("Hash-bound 001 before/after KQL receipts do not reconcile.")
        else:
            before_value = proof["kqlBefore"]["kqlTotals"]
            after_value = proof["kqlAfter"][0]
            before_sha = proof["receiptSha256"][proof["kqlBeforeReceiptPath"]]
            after_sha = proof["receiptSha256"][proof["kqlAfterReceiptPath"]]
            if after_value != expected_totals:
                raise SafetyError("Hash-bound post-increment KQL receipt differs from the selected increment.")
        if rows[0] != expected_totals:
            raise SafetyError("Hash-bound before/after KQL receipts do not reconcile to current KQL and source CSV.")
        cumulative = _verify_cumulative_kql(d, number)
        result.update({
            "kqlEvidenceKind": "fresh-read-matched-to-hash-bound-before-after-receipts",
            "kqlBefore": before_value,
            "kqlBeforeSha256": before_sha,
            "kqlAfter": after_value,
            "kqlAfterSha256": after_sha,
            "kqlFresh": rows[0],
            "kqlFreshSha256": hashlib.sha256(
                json.dumps(rows[0], sort_keys=True, ensure_ascii=False).encode("utf-8")
            ).hexdigest(),
            "kqlCumulativeExact": cumulative,
        })
    result.update({"timestampUtc": now(), "copyAndDataVerified": True,
                   "copyEvidenceKind": copy_evidence_kind,
                   "kql": rows[0], "state": "native-copy-kql-verified"})
    if not is_ui_observation:
        save(private / "native-events-validated.json", native_input)
    else:
        save(private / "native-ui-observation-validated.json", {
            "kind": native_input["kind"], "result": result,
        })
    save(private / "native-copy-validated.json", native_copy)
    save(private / "jobs-after.json", after)
    save(private / "verification.json", result)
    d.state["incrementDeliveries"][filename].update({"state": result["state"], "verification": result})
    d.checkpoint()
    return result


def check_readiness(args: Any) -> dict[str, Any]:
    """Read-only backend capture; does not create a watched file."""
    from preview30_activation_readiness import capture_readiness
    d = Deployment(args)
    activator, rule_id = _targets(d, require_delivery_ready=True)
    return capture_readiness(d, activator, rule_id)
