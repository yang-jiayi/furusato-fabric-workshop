"""Fail-closed deployment entry point for Furusato Workshop v3 Preview.

Environment identities and every service response belong in a private evidence
directory, never in the distributable workshop.  ``preflight`` is read-only.
The generation-1 v2.7 provisioner is deliberately NOT an apply fallback.
"""
from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse
import uuid

EDITION = "v3.0.0-preview"
BASELINE_COMMIT = "40921a0006394340f1284fd25c2824549d430c1c"
REPO = Path(__file__).resolve().parents[2]
BASE = REPO / "workshop" / "v2.7.0"
PREVIEW = REPO / "workshop" / EDITION
WORKSHOP_VERSION = (REPO / "WORKSHOP_VERSION").read_text(encoding="utf-8").strip()
API = "https://api.fabric.microsoft.com/v1"
OFFICIAL_DEFINITION = (
    "https://learn.microsoft.com/en-us/rest/api/fabric/articles/"
    "item-management/definitions/ontology-definition"
)
GUID = re.compile(r"^[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}$")
RUNTIME_INPUT_FILES = (
    "WORKSHOP_VERSION", "VERSION", "workshop/v3.0.0-preview/edition.json",
    "tools/provisioning/v3_artifacts.py",
    "tools/provisioning/preview30_runtime.py", "tools/provisioning/preview30_deploy.py",
    "tools/provisioning/preview30_verify.py", "tools/provisioning/preview30_ontology.py",
    "tools/provisioning/preview30_activation.py", "tools/provisioning/preview30_agent.py",
    "tools/provisioning/workshop_runtime.py", "tools/provisioning/activation_runtime.py",
    "tools/provisioning/reference_kql.py", "tools/data-agent/native_evaluation.py",
    "tools/data-agent/native_mcp.py",
    "tools/data-agent/source_grounded_profile.py", "tools/data-agent/answer_contract_profile.py",
    "tools/data-agent/time_layer_isolation.py", "tools/data-agent/fresh_grounded_profile.py",
    "tools/data-agent/standard_contract_restoration.py",
    "tools/data-agent/measured_contract_profile.py",
)
CORRECTED_PROFILE_DIRECTORIES = ("source-grounded", "complete-contract", "time-layer-isolation",
                                 "standard-contract-restoration", "measured-contract-20261009")
BASELINE_PROTECTED_PATHS = (
    "workshop/v2.7.0",
    "tools/docs/furusato_docs/tests10.py",
    "tools/data-agent/reference-models",
    "tools/data-agent/operational-functions",
    "tools/data-agent/source-contract",
    "tools/data-agent/path_ontology.py",
)


class SafetyError(RuntimeError):
    """No cloud write is permissible until the named safety gate passes."""


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def save(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_bytes(raw)
    os.replace(temporary, path)


def private_directory(path: Path) -> Path:
    path = path.resolve()
    if path == REPO or REPO in path.parents:
        raise SafetyError("Evidence must be outside the source checkout.")
    path.mkdir(parents=True, exist_ok=True)
    return path


def scope_from_document(document: dict[str, Any], environment: str) -> dict[str, Any]:
    """Accept the private handoff or a frozen scope; never infer portal mapping."""
    s = document.get("scope", document)
    scope = {
        "environment": environment,
        "tenantId": s.get("tenantId"),
        "workspaceId": s.get("workspaceId"),
        "workspaceName": s.get("workspaceName"),
        "folderId": s.get("folderId") or s.get("candidateFolderId"),
        "portalSubfolderId": str(s.get("portalSubfolderId", "")),
        "participantId": str(s.get("participantId", "")),
        "forbiddenItemIds": sorted(s.get("forbiddenItemIds", [])),
        "folderMappingVerified": s.get("folderMappingVerified") is True,
    }
    if environment not in {"dev", "test", "prod"}:
        raise SafetyError("An explicit dev/test/prod environment is required.")
    for field in ("tenantId", "workspaceId", "folderId"):
        if not GUID.fullmatch(str(scope[field])):
            raise SafetyError(f"{field} must be an externalized GUID.")
    if not re.fullmatch(r"(?!000)\d{3}", scope["participantId"]):
        raise SafetyError("participantId must be 001..999.")
    if not scope["workspaceName"] or not scope["portalSubfolderId"]:
        raise SafetyError("Exact workspace name and portal folder reference are required.")
    return scope


def scope_fingerprint(scope: dict[str, Any]) -> str:
    return digest({k: v for k, v in scope.items() if k != "folderMappingVerified"})


def plan_fingerprint(plan: dict[str, Any]) -> str:
    value = json.loads(json.dumps(plan))
    value.pop("planSha256", None)
    value.get("scope", {}).pop("folderMappingVerified", None)
    return digest(value)


def candidate_fingerprint() -> str:
    paths = [REPO / p for p in RUNTIME_INPUT_FILES]
    for relative in ("ontology/definition", "ontology/relationships/definition", "data-agent/definition",
                     "powerbi/Furusato_Analytics.SemanticModel"):
        paths.extend(p for p in (PREVIEW / relative).rglob("*") if p.is_file())
    for profile in CORRECTED_PROFILE_DIRECTORIES:
        paths.extend(p for p in (PREVIEW / "data-agent/candidates" / profile).rglob("*")
                     if p.is_file() and p.suffix in {".json", ".txt", ".sql"})
    paths.extend(PREVIEW / p for p in (
        "provisioning/gold-contract.json", "powerbi/native-metrics-contract.json",
        "ontology/relationships/contract.json"))
    if any(not p.is_file() for p in paths):
        raise SafetyError("Build the complete v3 candidate before freezing its resource plan.")
    return digest({p.relative_to(REPO).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                   for p in sorted(set(paths))})


def notebook_source_hashes() -> dict[str, str]:
    return {p.name.split("_")[1]: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (PREVIEW / "notebooks").glob("Notebook_*.ipynb")}


def planned_resources(pid: str, *, include_relationships: bool = False) -> list[dict[str, Any]]:
    items = [
        ("lakehouse", "Lakehouse", f"LH_Furusato_{pid}", "core"),
        ("eventhouse", "Eventhouse", f"EH_Furusato_{pid}", "core"),
        ("kqlDatabase", "KQLDatabase", f"EH_Furusato_{pid}", "generated"),
        ("pipeline", "DataPipeline", f"PL_Furusato_{pid}", "core"),
        ("ontology", "Ontology", f"ONT_Furusato_{pid}", "generation2"),
        ("semanticModel", "SemanticModel", f"SM_Furusato_Analytics_{pid}", "core"),
        ("dataAgent", "DataAgent", f"DA_Furusato_{pid}", "core"),
        ("activator", "Reflex", f"My activator_{pid}", "core"),
    ]
    titles = {
        "01": "Prepare_Ontology_Data",
        "02": "Apply_Ontology_Metadata",
        "03": "Create_Complete_Ontology",
        "04": "Provision_Complete_Workshop",
        "05": "Analytics_Quality_and_BI",
    }
    items += [(f"notebook{k}", "Notebook", f"Notebook_{k}_Furusato_{v}_{pid}", "core")
              for k, v in titles.items()]
    if include_relationships:
        items.append(("relationshipsOntology", "Ontology",
                      f"ONT_Furusato_Relationships_{pid}", "optional-static-relationships"))
    return [{"key": key, "type": kind, "displayName": name, "purpose": purpose}
            for key, kind, name, purpose in items]


def immutable_baseline() -> dict[str, Any]:
    """Hash the complete baseline, and independently reconcile source CSVs."""
    files = {p.relative_to(BASE).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
             for p in sorted(BASE.rglob("*")) if p.is_file()}
    seed = BASE / "data" / "seed" / "donation_orders.csv"
    with seed.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    amount_column = next((key for key in rows[0] if key.casefold() in
                          {"amount", "donationamount", "donationamountyen"}), None)
    if amount_column is None:
        raise SafetyError("Canonical donation amount column is missing.")
    total = sum(int(row[amount_column]) for row in rows)
    if len(rows) != 80000 or total != 1344099000:
        raise SafetyError("Immutable static donation totals differ from 80000 / 1344099000.")
    increments = {}
    ids: list[str] = []
    for p in sorted((BASE / "data" / "increment").glob("*.csv")):
        with p.open(encoding="utf-8", newline="") as handle:
            inc = list(csv.DictReader(handle))
        key = next((name for name in inc[0] if name.casefold() == "donationid"), None)
        if key is None:
            raise SafetyError("Canonical increment DonationId column is missing.")
        increments[p.name] = len(inc)
        ids.extend(row[key] for row in inc)
    if list(increments.values()) != [5000, 5000, 5000] or len(set(ids)) != 14900:
        raise SafetyError("Immutable increment contract differs from 3x5000 / 14900.")
    dirty = subprocess.run(
        ["git", "-C", str(REPO), "--no-pager", "diff", "--name-only",
         BASELINE_COMMIT, "--", *BASELINE_PROTECTED_PATHS],
        capture_output=True, text=True, check=True,
    ).stdout.strip().splitlines()
    if dirty:
        raise SafetyError("Protected baseline changed: " + ", ".join(dirty[:10]))
    return {"treeSha256": digest(files), "files": files,
            "staticDonationRows": len(rows), "staticDonationYen": total,
            "increments": increments, "rawIncrementRows": len(ids),
            "acceptedUniqueRows": len(set(ids)), "duplicateRows": len(ids) - len(set(ids))}


class EvidenceClient:
    """No ambient proxy auth, no token logging, no automatic write retry."""

    def __init__(self, scope: dict[str, Any], evidence: Path, *, credential: Any = None):
        import requests
        self.scope = scope
        self.evidence = private_directory(evidence)
        self.session = requests.Session()
        self.session.trust_env = False
        if credential is None:
            from azure.identity import AzureCliCredential
            credential = AzureCliCredential(tenant_id=scope["tenantId"])
        self.credential = credential
        self.allowed_writes: dict[tuple[str, str, str], str] = {}
        self.gate: dict[str, Any] | None = None

    def request(self, method: str, path: str, *, body: Any = None,
                skill: str = "spark-cli", read_only_post: bool = False,
                expected: tuple[int, ...] = (200,), label: str = "request"):
        method = method.upper()
        url = path if path.startswith("https://") else API + path
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.netloc != "api.fabric.microsoft.com":
            raise SafetyError("Fabric control-plane host is not authorized.")
        allowed_read = method in {"GET", "HEAD"} or (
            read_only_post and method == "POST" and parsed.path.endswith("/getDefinition")
        )
        if not allowed_read:
            if self.gate is None:
                raise SafetyError("Write gate has not been released.")
            if not parsed.path.startswith(f"/v1/workspaces/{self.scope['workspaceId']}/"):
                raise SafetyError("Mutation is outside the frozen workspace.")
            if method == "DELETE":
                raise SafetyError("Deletion is not authorized by this deployment.")
            if any(x in url or x in canonical(body).decode("utf-8")
                   for x in self.scope["forbiddenItemIds"]):
                raise SafetyError("Attempt to mutate a forbidden preexisting item.")
            approval_key = (method, parsed.path, parsed.query)
            if self.allowed_writes.get(approval_key) != digest(body):
                raise SafetyError("No exact persisted write preview exists for this endpoint.")
            self.allowed_writes.pop(approval_key)
        operation = f"{datetime.now(timezone.utc):%Y%m%dT%H%M%S%fZ}-{uuid.uuid4().hex[:8]}-{label}"
        record = {"timestampUtc": now(), "method": method, "url": url,
                  "skill": skill, "readOnly": allowed_read}
        if not allowed_read:
            record["body"] = body
            record["scopeSha256"] = scope_fingerprint(self.scope)
            save(self.evidence / "writes" / f"{operation}-preview.json", record)
        token = self.credential.get_token("https://api.fabric.microsoft.com/.default").token
        try:
            response = self.session.request(
                method, url, json=body,
                headers={"Authorization": "Bearer " + token,
                         "Content-Type": "application/json", "x-ms-fabric-skill": skill},
                timeout=(20, 90), allow_redirects=False,
            )
        except Exception as exc:
            record.update({"outcome": "ambiguous" if not allowed_read else "failed",
                           "errorType": type(exc).__name__})
            save(self.evidence / "responses" / f"{operation}.json", record)
            raise SafetyError("Transport outcome uncertain; reconcile before retry.") from exc
        record.update({"statusCode": response.status_code,
                       "headers": {k: v for k, v in response.headers.items()
                                   if k.lower() in {"location", "retry-after", "requestid",
                                                    "x-ms-operation-id", "x-ms-request-id"}},
                       "bodyText": response.text})
        save(self.evidence / "responses" / f"{operation}.json", record)
        if response.status_code not in expected:
            raise SafetyError(f"{label}: HTTP {response.status_code}; exact error saved in private evidence.")
        return response

    def paged(self, path: str, *, skill: str = "spark-cli") -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        seen: set[str] = set()
        initial_path = path
        while path:
            if path in seen or len(seen) >= 1000:
                raise SafetyError("Pagination did not converge.")
            seen.add(path)
            document = self.request("GET", path, skill=skill).json()
            result.extend(document.get("value", []))
            path = document.get("continuationUri", "")
            if not path and document.get("continuationToken"):
                from urllib.parse import urlencode
                path = initial_path.split("?")[0] + "?" + urlencode({
                    "continuationToken": document["continuationToken"]})
        return result


def validate_gate(scope: dict[str, Any], plan: dict[str, Any],
                  gate: dict[str, Any], confirmation: str) -> None:
    if plan_fingerprint(plan) != plan.get("planSha256"):
        raise SafetyError("Resource plan content changed after its fingerprint was approved.")
    if not scope["folderMappingVerified"] or gate.get("folderMappingVerified") is not True:
        raise SafetyError("Portal numeric folder to GUID mapping has not been confirmed.")
    expected = {"workspaceId": scope["workspaceId"], "folderId": scope["folderId"],
                "participantId": scope["participantId"],
                "scopeSha256": scope_fingerprint(scope), "planSha256": plan["planSha256"]}
    if any(gate.get(k) != v for k, v in expected.items()):
        raise SafetyError("Gate does not match the frozen scope and exact resource plan.")
    if confirmation != plan["planSha256"] or gate.get("allowCloudMutations") is not True:
        raise SafetyError("Explicit plan confirmation and mutation authorization are required.")
    if not gate.get("approvedAt") or not gate.get("folderMappingEvidence"):
        raise SafetyError("Gate lacks approval timestamp or portal mapping evidence.")


def build_plan(scope: dict[str, Any], inventory: dict[str, Any],
               baseline: dict[str, Any], owned_state: dict[str, Any] | None = None,
               *, include_relationships: bool = False) -> dict[str, Any]:
    resources = planned_resources(scope["participantId"], include_relationships=include_relationships)
    blockers = []
    owned = (owned_state or {}).get("items", {})
    if owned_state and owned_state.get("scopeSha256") != scope_fingerprint(scope):
        raise SafetyError("Owned-item receipts belong to a different frozen scope.")
    for r in resources:
        active = [i for i in inventory.get("items", [])
                  if i.get("type", "").casefold() == r["type"].casefold()
                  and i.get("displayName", "").casefold() == r["displayName"].casefold()]
        recoverable = [i for i in inventory.get("recoverableItems", [])
                       if i.get("type", "").casefold() == r["type"].casefold()
                       and i.get("displayName", "").casefold() == r["displayName"].casefold()]
        receipt = owned.get(r["key"], {})
        owned_match = (len(active) == 1 and receipt.get("id") == active[0].get("id")
                       and active[0].get("folderId") == scope["folderId"])
        if recoverable or (active and not owned_match):
            blockers.append(f"Name collision (active/recoverable): {r['displayName']}")
        if owned_match:
            r["ownedItemId"] = active[0]["id"]
            r["existingState"] = "owned-receipt-verified"
        elif receipt:
            blockers.append(f"Owned item receipt no longer resolves: {r['displayName']}")
    plan = {
        "schemaVersion": "furusato-preview30-plan/v1", "edition": EDITION,
        "workshopVersion": WORKSHOP_VERSION,
        "sourceBaselineCommit": BASELINE_COMMIT, "scope": scope,
        "scopeSha256": scope_fingerprint(scope), "resources": resources,
        "generatedResources": ["Lakehouse SQL endpoint", "Eventhouse KQL database"],
        "folders": [],
        "productionPlacement": "specified-folder-direct",
        "correctedAgentProfile": "data-agent/candidates/measured-contract-20261009",
        "evaluationArtifacts": "Explicit opt-in only; remove after evaluation without deleting adopted dependencies.",
        "immutableBaselineTreeSha256": baseline["treeSha256"],
        "candidateSourceSha256": candidate_fingerprint(),
        "notebookSourceSha256": notebook_source_hashes(),
        "dataGates": {k: v for k, v in baseline.items() if k not in {"files", "treeSha256"}},
        "requiredGeneration": 2,
        "graph": {"default": "off", "optIn": True,
                  "eligibility": "keyed, one-backing-managed-Lakehouse-table entities only"},
        "ontologyWriteOrder": ["runtime creates core generation2", "runtime reads back",
                              "release core lock", "coordinator native metric/UI changes"],
        "forbiddenOperations": ["preexisting item mutation", "permanent purge", "role changes",
                                "capacity changes", "tenant changes", "blind create retry",
                                "replay of uncertain increments", "rerun completed Notebook01"],
        "compatibilityGaps": [
            {"id": "legacy-runtime", "status": "must-replace",
             "detail": "The v2.7 Ontology EntityTypes JSON definition is generation1; not a v3 deploy fallback."},
            {"id": "metrics-tmdl", "status": "native-ui-required",
             "detail": "Projected/enrichment backingMeasure has no TMDL representation. Source-owned DAX metrics require native semantic-model binding, not explicit DAX metrics."},
            {"id": "timeseries-source", "status": "contract-verification-required",
             "detail": "Gen2 time-series backingConfiguration is documented; Eventhouse-backed partition shape must be verified before deployment."},
            {"id": "data-agent-semantic-model", "status": "direct-source-required",
             "detail": "Ontology semantic-model grounding is not inherited; configure SemanticModel directly in the main Data Agent."},
            {"id": "native-activator", "status": "lifecycle-and-evidence-required",
             "detail": "Keep supported start/stop plus correlated FileCreated/activation/new Completed job/Copy/KQL evidence. Running alone is not success."},
        ],
        "officialDefinition": OFFICIAL_DEFINITION,
        "blockers": blockers,
    }
    if include_relationships:
        plan["relationshipsCompanion"] = {
            "contract": "ontology/relationships/contract.json",
            "createOnly": True, "sameOwnedLakehouse": True, "operationalCoreUnchanged": True,
            "automaticGraphMaterialization": False, "dataAgentSourceRoutingChanged": False,
            "requiresNativeGraphHandoffAndQueryAcceptance": True,
        }
    # Confirmation is stable across gate release; mapping proof remains a separate gate.
    plan["planSha256"] = plan_fingerprint(plan)
    return plan


def preflight(args: argparse.Namespace) -> dict[str, Any]:
    evidence = private_directory(args.evidence_dir)
    scope = scope_from_document(load(args.scope), args.environment)
    baseline = immutable_baseline()
    if args.online:
        client = EvidenceClient(scope, evidence)
        prefix = f"/workspaces/{scope['workspaceId']}"
        workspace = client.request("GET", prefix).json()
        if workspace.get("displayName") != scope["workspaceName"]:
            raise SafetyError("Workspace name differs from the explicit frozen scope.")
        inventory = {"capturedUtc": now(), "workspace": workspace,
                     "items": client.paged(prefix + "/items"),
                     "folders": client.paged(prefix + "/folders"),
                     "recoverableItems": client.paged(prefix + "/recoverableItems")}
        capacity = [v for v in client.paged("/capacities")
                    if v.get("id") == workspace.get("capacityId")]
        inventory["capacity"] = capacity
        if len(capacity) != 1 or capacity[0].get("state") != "Active":
            raise SafetyError("Assigned capacity was not verifiably Active.")
        save(evidence / "inventory-preflight.json", inventory)
    elif args.inventory:
        inventory = load(args.inventory)
    else:
        raise SafetyError("Offline preflight requires an explicit inventory snapshot.")
    if inventory["workspace"]["id"] != scope["workspaceId"]:
        raise SafetyError("Inventory is not for the requested workspace.")
    if not any(f["id"] == scope["folderId"] for f in inventory["folders"]):
        raise SafetyError("Candidate folder GUID is not present in inventory.")
    state_file = evidence / "deployment-state.json"
    owned_state = load(state_file) if state_file.exists() else None
    plan = build_plan(scope, inventory, baseline, owned_state,
                      include_relationships=getattr(args, "include_relationships", False))
    save(evidence / "immutable-baseline.json", baseline)
    save(evidence / "resource-plan.json", plan)
    gate_template = {
        "allowCloudMutations": False, "folderMappingVerified": False,
        "approvedAt": None, "folderMappingEvidence": None,
        **{k: scope[k] for k in ("workspaceId", "folderId", "participantId")},
        "scopeSha256": plan["scopeSha256"], "planSha256": plan["planSha256"],
    }
    save(evidence / "write-gate.template.json", gate_template)
    status = "blocked" if plan["blockers"] else "preflight-passed-write-gated"
    prior_result_path = evidence / "result.json"
    prior_result = load(prior_result_path) if prior_result_path.exists() else {}
    result = {
        **prior_result,
        "timestampUtc": now(), "edition": EDITION, "status": status,
        "implemented": ["read-only preflight", "immutable baseline verification",
                        "externalized environment/scope", "per-write evidence client",
                        "exact scope/plan write gate"],
        "locallyTested": baseline["dataGates"] if "dataGates" in baseline else plan["dataGates"],
        "deployed": bool((owned_state or {}).get("items")),
        "items": (owned_state or {}).get("items", {}),
        "jobs": (owned_state or {}).get("jobs", {}),
        "observed": {**prior_result.get("observed", {}), "onlineDiscovery": bool(args.online)},
        "planSha256": plan["planSha256"],
        "resourcePlanPath": str(evidence / "resource-plan.json"),
        "blockers": plan["blockers"], "compatibilityGaps": plan["compatibilityGaps"],
        "actualReadiness": ("Read-only preflight completed; existing owned deployment receipts retained. "
                            "New writes require the exact revised plan gate; remaining native features are not inferred."),
    }
    result.update(live_receipt_summary(owned_state or {}))
    result.pop("cloudMutationCount", None)
    result.pop("cloudMutations", None)
    result.pop("cloudWrites", None)
    save(evidence / "result.json", result)
    lines = [
        "", "## Read-only preflight", "", f"- 更新 UTC: {now()}",
        f"- 状態: `{status}`", "- 旧 PRIVATE archive は未変更。公開 clone のみ使用。",
        "- v2.7 全ファイルと元の標準評価ソースは変更なし。",
        "- 静的データ 80,000 件・1,344,099,000 円を CSV から再計算済み。",
        "- 増分 5,000 × 3、生 15,000・unique 14,900・duplicate 100 を再計算済み。",
        f"- 既存runtime所有item数: {result['runtimeOwnedItemCount']}。"
        f"Cloud mutation実績: {str(result['cloudMutationsOccurred']).lower()}。",
        f"- Folder mapping確認: {str(scope['folderMappingVerified']).lower()}。"
        "このpreflight自体はread-onlyで、新規writeは一致する明示gateを必要とします。",
        "- Gen2 は TMDL / compatibilityLevel 1000000。旧 EntityTypes JSON は使用しない。",
        "- native Metrics の backingMeasure は TMDL round-trip 非対応。UI 接続が必要。",
        "- Notebook05 は Lakehouse static/staging と Files のみを入力とする。",
        "", f"resource-plan.json: `{plan['planSha256']}`", "",
    ]
    progress_path = evidence / "progress-ja.md"
    if not progress_path.exists():
        progress_path.write_bytes("# v3.0 Preview 配置・実行 進捗\n".encode("utf-8"))
    with progress_path.open("ab") as handle:
        handle.write(("\n".join(lines)).encode("utf-8"))
    return result


def live_receipt_summary(state: dict[str, Any]) -> dict[str, Any]:
    """Current deployment facts, independent of the most recent command's scope."""
    items = state.get("items", {})
    return {
        "deployed": bool(items),
        "runtimeOwnedItemCount": len(items),
        "cloudMutationsOccurred": bool(items or state.get("uploads") or state.get("jobs")),
        "ontologyDeployed": "ontology" in items,
        "ontologyGenerationVerified": state.get("ontologyVerification", {}).get("generation"),
        "ontologyWriterHandoff": state.get("ontologyNativeUiHandoff"),
        "staticSourceVerified": state.get("sourceVerification", {}).get("verified") is True,
        "goldVerified": state.get("goldVerification", {}).get("verified") is True,
        "goldInputBranch": state.get("qualityBranch", {}).get("branch"),
        "semanticModelDeployed": "semanticModel" in items,
        "sourceOwnedDaxVerified": state.get("modelDaxVerification", {}).get("verified") is True,
        "dataAgentDeployed": "dataAgent" in items,
        "dataAgentPublished": state.get("dataAgentVerification", {}).get("published") is True,
        "nativeAutomaticDeliveryVerified": (
            len(state.get("incrementDeliveries", {})) == 3
            and all(v.get("state") == "native-copy-kql-verified"
                    for v in state.get("incrementDeliveries", {}).values())
        ),
        "aiAnswerQualityVerified": False,
    }


def record_command(evidence: Path, command: str, status: str, value: Any) -> None:
    evidence = private_directory(evidence)
    path = evidence / "result.json"
    result = load(path) if path.exists() else {"edition": EDITION, "deployed": False}
    result["timestampUtc"] = now()
    result.setdefault("phases", {})[command] = {
        "timestampUtc": now(), "status": status, "result": value,
    }
    if status == "blocked":
        result["status"] = "blocked"
        result["actualReadiness"] = "Current stage blocked; earlier receipts do not prove end-to-end readiness."
    else:
        result["status"] = "stage-completed"
        result["actualReadiness"] = f"{command} completed; inspect its actual result and remaining gates. This is not an end-to-end or AI-quality success claim."
    result["lastCommand"] = command
    state_path = evidence / "deployment-state.json"
    if state_path.exists():
        result.update(live_receipt_summary(load(state_path)))
        # Historical zero-count fields must not survive a later real deployment.
        # Explicit resource counts are not mislabeled as counts of HTTP writes.
        result.pop("cloudMutationCount", None)
        result.pop("cloudMutations", None)
        result.pop("cloudWrites", None)
    save(path, result)
    with (evidence / "progress-ja.md").open("ab") as handle:
        handle.write(f"\n- UTC {now()} — `{command}`: **{status}**。段階別の実結果は result.json を参照。AI/UI 完了の推定はしません。\n".encode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=[
        "preflight", "deploy-sources", "verify-sources", "deploy-notebooks",
        "deploy-realtime", "deploy-core", "deploy-relationships", "preview-metadata", "apply-metadata",
        "handoff-ontology", "verify-gold", "deploy-semantic-model", "refresh-model", "verify-model",
        "deploy-agent", "publish-agent", "start-activator", "stop-activator", "deliver-increment", "verify-delivery",
    ])
    parser.add_argument("--environment", required=True, choices=["dev", "test", "prod"])
    parser.add_argument("--scope", required=True, type=Path)
    parser.add_argument("--evidence-dir", required=True, type=Path)
    parser.add_argument("--inventory", type=Path)
    parser.add_argument("--online", action="store_true")
    parser.add_argument("--include-relationships", action="store_true",
                        help="Preflight only: explicitly include the create-only static companion.")
    parser.add_argument("--write-gate", type=Path)
    parser.add_argument("--confirm")
    parser.add_argument("--run-notebook01", action="store_true")
    parser.add_argument("--expected-definition-sha256")
    parser.add_argument("--increment", type=int, choices=[1, 2, 3])
    parser.add_argument("--native-events", type=Path)
    parser.add_argument("--native-copy", type=Path)
    args = parser.parse_args()
    try:
        if args.include_relationships and args.command != "preflight":
            raise SafetyError("--include-relationships belongs to preflight; approve its new exact plan first.")
        if args.command == "preflight":
            result = preflight(args)
        elif args.command in {"start-activator", "stop-activator", "deliver-increment", "verify-delivery"}:
            from preview30_activation import lifecycle, deliver_increment, verify_delivery
            if args.command in {"start-activator", "stop-activator"}:
                result = lifecycle(args, start=args.command == "start-activator")
            else:
                result = {"deliver-increment": deliver_increment, "verify-delivery": verify_delivery}[args.command](args)
        elif args.command.startswith("verify-"):
            from preview30_verify import verify_sources, verify_gold, verify_model
            result = {"verify-sources": verify_sources, "verify-gold": verify_gold,
                      "verify-model": verify_model}[args.command](args)
        else:
            from preview30_deploy import (
                deploy_sources, deploy_notebooks, deploy_realtime, deploy_core, deploy_relationships,
                deploy_semantic_model, refresh_model_once, deploy_agent, publish_agent_candidate,
                metadata_change, handoff_ontology,
            )
            actions = {"deploy-sources": deploy_sources, "deploy-notebooks": deploy_notebooks,
                       "deploy-realtime": deploy_realtime, "deploy-core": deploy_core,
                       "deploy-relationships": deploy_relationships,
                       "deploy-semantic-model": deploy_semantic_model, "deploy-agent": deploy_agent,
                       "refresh-model": refresh_model_once,
                       "publish-agent": publish_agent_candidate,
                       "preview-metadata": metadata_change,
                       "apply-metadata": lambda value: metadata_change(value, apply=True),
                       "handoff-ontology": handoff_ontology}
            result = actions[args.command](args)
        record_command(args.evidence_dir, args.command,
                       "blocked" if result.get("blockers") else "completed", result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if result.get("blockers") else 0
    except Exception as exc:
        try:
            record_command(args.evidence_dir, args.command, "blocked",
                           {"errorType": type(exc).__name__, "message": str(exc)})
        except Exception:
            pass  # Never turn a reporting failure into a write retry.
        print(f"STOP: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
