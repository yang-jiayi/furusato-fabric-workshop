"""Scoped v3 Preview source deployment; invoked only after a frozen write gate.

This module reuses the released Notebook 01 data-generation logic unchanged.
It does not invoke the generation-1 Ontology provisioner, replay increments, or
promote an Activator's Running state to automatic-delivery success.
"""
from __future__ import annotations

import base64
import copy
import hashlib
import json
from pathlib import Path
import re
import time
from typing import Any
from urllib.parse import urlparse, quote

from preview30_runtime import (
    API, BASE, PREVIEW, EvidenceClient, SafetyError, digest, load, now,
    REPO, immutable_baseline, candidate_fingerprint, live_receipt_summary, private_directory, save, scope_fingerprint, scope_from_document, validate_gate,
)


def part(path: str, content: bytes) -> dict[str, str]:
    return {"path": path, "payload": base64.b64encode(content).decode("ascii"),
            "payloadType": "InlineBase64"}


class Deployment:
    def __init__(self, args: Any):
        self.evidence = private_directory(args.evidence_dir)
        self.scope = scope_from_document(load(args.scope), args.environment)
        self.plan = load(self.evidence / "resource-plan.json")
        if not args.write_gate or not args.confirm:
            raise SafetyError("--write-gate and --confirm are required before authentication.")
        gate = load(args.write_gate)
        validate_gate(self.scope, self.plan, gate, args.confirm)
        if self.plan["blockers"]:
            raise SafetyError("The frozen resource plan has unresolved blockers.")
        if candidate_fingerprint() != self.plan.get("candidateSourceSha256"):
            raise SafetyError("Candidate implementation/templates changed after approval; rebuild and re-preview.")
        if (REPO / ".git").exists():
            actual_baseline = immutable_baseline()
        else:
            # Notebook frontend extracted a fingerprint-verified release bundle.
            actual_baseline = load(PREVIEW / "provisioning/baseline-hashes.json")
            for relative, sha in actual_baseline["files"].items():
                path = BASE / relative
                if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest() != sha:
                    raise SafetyError("Extracted immutable baseline bytes changed.")
        if actual_baseline["treeSha256"] != self.plan["immutableBaselineTreeSha256"]:
            raise SafetyError("Immutable source baseline differs from the approved plan.")
        self.client = EvidenceClient(self.scope, self.evidence, credential=getattr(args, "credential", None))
        self.client.gate = gate
        self.prefix = f"/workspaces/{self.scope['workspaceId']}"
        self.state_path = self.evidence / "deployment-state.json"
        self.state = load(self.state_path) if self.state_path.exists() else {
            "scopeSha256": scope_fingerprint(self.scope), "items": {}, "jobs": {},
            "uploads": {}, "pendingCreates": {}, "commands": {},
        }
        if self.state["scopeSha256"] != scope_fingerprint(self.scope):
            raise SafetyError("Deployment state belongs to a different frozen scope.")
        self.resources = {r["key"]: r for r in self.plan["resources"]}

    def checkpoint(self) -> None:
        self.state["timestampUtc"] = now()
        save(self.state_path, self.state)

    def allow(self, path: str, preview: dict[str, Any]) -> None:
        """Record exact intent before making a single authorized request."""
        save(self.evidence / "write-previews" / (digest(preview) + ".json"),
             {"timestampUtc": now(), "scopeSha256": self.state["scopeSha256"],
              "path": path, "delta": preview})
        parsed = urlparse(API + path)
        self.client.allowed_writes[("POST", parsed.path, parsed.query)] = digest(preview.get("body"))

    def poll_lro(self, operation_id: str, *, skill: str, timeout: int = 900) -> dict[str, Any]:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            r = self.client.request("GET", f"/operations/{operation_id}", skill=skill)
            value = r.json()
            status = value.get("status")
            if status == "Succeeded":
                return value
            if status in {"Failed", "Cancelled", "Canceled"}:
                raise SafetyError(f"LRO {status}; inspect exact private response. No automatic retry.")
            time.sleep(min(max(int(r.headers.get("Retry-After", 10)), 2), 60))
        raise SafetyError("LRO timed out; reconcile operation before any retry.")

    def definition(self, item_id: str, *, skill: str, format_name: str | None = None):
        known = next((item for item in self.state["items"].values() if item["id"] == item_id), {})
        if known.get("type") == "Ontology":
            collection = "ontologies"
            format_name = None  # Native generation2 readback uses default-format TMDL parts.
        else:
            collection = "reflexes" if known.get("type") == "Reflex" else "items"
        path = self.prefix + f"/{collection}/{item_id}/getDefinition"
        if format_name:
            path += "?format=" + quote(format_name, safe="")
        response = self.client.request("POST", path, body={}, skill=skill,
                                       read_only_post=True, expected=(200, 202),
                                       label="get-definition")
        if response.status_code == 202:
            op = response.headers.get("x-ms-operation-id")
            if not op:
                raise SafetyError("Definition LRO lacks operation ID.")
            self.poll_lro(op, skill=skill)
            response = self.client.request("GET", f"/operations/{op}/result", skill=skill)
        value = response.json()
        return value.get("definition", value)

    def verify_definition(self, key: str, item: dict[str, Any], definition: dict[str, Any],
                          *, skill: str) -> dict[str, Any]:
        actual = self.definition(item["id"], skill=skill, format_name=definition.get("format"))
        save(self.evidence / "definitions" / f"{key}-readback.json", actual)
        resource = self.resources[key]
        if resource["type"] == "Notebook":
            desired = next(p for p in definition["parts"] if p["path"] == "notebook-content.ipynb")
            found = next((p for p in actual["parts"] if p["path"] == "notebook-content.ipynb"), None)
            if found is None:
                raise SafetyError("Notebook content absent from readback.")
            before = json.loads(base64.b64decode(desired["payload"]))
            after = json.loads(base64.b64decode(found["payload"]))
            sources = lambda n: ["".join(c.get("source", [])) for c in n["cells"]]
            if sources(before) != sources(after):
                raise SafetyError("Notebook readback cell code differs from supplied definition.")
            left = before.get("metadata", {}).get("dependencies", {}).get("lakehouse", {})
            right = after.get("metadata", {}).get("dependencies", {}).get("lakehouse", {})
            for field in ("default_lakehouse", "default_lakehouse_workspace_id"):
                if left.get(field) != right.get(field):
                    raise SafetyError("Notebook Lakehouse binding differs on readback.")
        elif resource["type"] in {"DataPipeline", "Reflex", "DataAgent"}:
            from workshop_runtime import definitions_equal
            compared = actual
            if resource["type"] == "DataAgent" and self.state.get("dataAgentVerification", {}).get("published"):
                # A published agent legitimately has extra published-stage parts.
                # Protect every requested Draft part without stripping or rewriting
                # the published state as a side effect of a deployment recheck.
                wanted = {p["path"] for p in definition["parts"]}
                compared = {**actual, "parts": [p for p in actual["parts"] if p["path"] in wanted]}
            if not definitions_equal(compared, definition):
                raise SafetyError(f"{key}: effective definition differs after readback; reconcile without overwrite.")
        self.state["items"][key]["definitionReadbackCaptured"] = True
        self.checkpoint()
        return actual

    def create(self, key: str, *, definition: dict[str, Any] | None = None,
               creation_payload: dict[str, Any] | None = None,
               skill: str = "spark-cli") -> dict[str, Any]:
        resource = self.resources[key]
        matches = [i for i in self.client.paged(self.prefix + "/items", skill=skill)
                   if i.get("type") == resource["type"]
                   and i.get("displayName") == resource["displayName"]]
        known = self.state["items"].get(key)
        if matches:
            if len(matches) != 1 or not known or matches[0]["id"] != known["id"]:
                raise SafetyError(f"{key}: name exists without an owned receipt; reconcile, never adopt blindly.")
            if matches[0].get("folderId") != self.scope["folderId"]:
                raise SafetyError(f"{key}: owned item moved outside target folder.")
            if definition is not None:
                if known.get("desiredDefinitionSha256") != digest(definition):
                    raise SafetyError(f"{key}: desired definition changed; creation is not an update operation.")
                self.verify_definition(key, matches[0], definition, skill=skill)
            return matches[0]
        if known:
            raise SafetyError(f"{key}: owned item disappeared; no automatic replacement.")
        if key in self.state["pendingCreates"]:
            raise SafetyError(f"{key}: prior create outcome requires reconciliation, not a second POST.")
        recovered = [i for i in self.client.paged(self.prefix + "/recoverableItems", skill=skill)
                     if i.get("displayName") == resource["displayName"]
                     and i.get("type") == resource["type"]]
        if recovered:
            raise SafetyError(f"{key}: recoverable name collision; no restore or purge is authorized.")
        body = {"displayName": resource["displayName"], "type": resource["type"],
                "folderId": self.scope["folderId"]}
        if definition is not None:
            body["definition"] = definition
        if creation_payload is not None:
            body["creationPayload"] = creation_payload
        path = self.prefix + ("/reflexes" if resource["type"] == "Reflex" else "/items")
        if resource["type"] == "Reflex":
            body.pop("type")
        self.allow(path, {"key": key, "action": "create", "body": body})
        self.state["pendingCreates"][key] = {"startedUtc": now(), "bodySha256": digest(body)}
        self.checkpoint()
        response = self.client.request("POST", path, body=body, skill=skill,
                                       expected=(200, 201, 202), label=f"create-{key}")
        if response.status_code == 202:
            op = response.headers.get("x-ms-operation-id")
            self.state["pendingCreates"][key]["operationId"] = op
            self.checkpoint()
            if not op:
                raise SafetyError("Create accepted without operation ID; reconcile manually.")
            time.sleep(max(1, int(response.headers.get("Retry-After", 5))))
            self.poll_lro(op, skill=skill)
        deadline = time.monotonic() + 180
        while time.monotonic() < deadline:
            matches = [i for i in self.client.paged(self.prefix + "/items", skill=skill)
                       if i.get("type") == resource["type"]
                       and i.get("displayName") == resource["displayName"]]
            if len(matches) == 1:
                break
            if len(matches) > 1:
                raise SafetyError("Create produced ambiguous same-name items.")
            time.sleep(5)
        if len(matches) != 1 or matches[0].get("folderId") != self.scope["folderId"]:
            raise SafetyError("Create readback did not prove the exact target folder.")
        item = matches[0]
        self.state["items"][key] = {**item, "createdUtc": now(),
                                   "desiredDefinitionSha256": digest(definition) if definition else None}
        self.state["pendingCreates"].pop(key)
        self.checkpoint()
        if definition is not None:
            self.verify_definition(key, item, definition, skill=skill)
        return item

    def require_owned(self, key: str) -> dict[str, Any]:
        item = self.state["items"].get(key)
        if not item or item["id"] in self.scope["forbiddenItemIds"]:
            raise SafetyError(f"An owned {key} receipt is required.")
        current = self.client.request("GET", self.prefix + f"/items/{item['id']}").json()
        if current.get("folderId") != self.scope["folderId"] or current.get("displayName") != self.resources[key]["displayName"]:
            raise SafetyError(f"{key} is no longer in its frozen scope.")
        return current

    def upload_staged(self, lakehouse: dict[str, Any]) -> None:
        """Put complete immutable bytes, never into the watched increment folder."""
        from workshop_runtime import dataset_target_relative_path
        lh_id = lakehouse["id"]
        self.ensure_watch_directory(lh_id)
        files = sorted((BASE / "data").glob("*/*.csv"))
        if len(files) != 11 or sum(p.parent.name == "seed" for p in files) != 8:
            raise SafetyError("The complete released 8-seed/3-increment inventory is required.")
        for file in files:
            relative = file.relative_to(BASE / "data").as_posix()
            target = dataset_target_relative_path(relative, self.scope["participantId"])
            if target.startswith("increment/"):
                raise SafetyError("Deployment must not deliver watched increment events.")
            content = file.read_bytes()
            sha = hashlib.sha256(content).hexdigest()
            url = (f"https://onelake.blob.fabric.microsoft.com/{self.scope['workspaceId']}"
                   f"/{lh_id}/Files/{target}")
            token = self.client.credential.get_token("https://storage.azure.com/.default").token
            read_headers = {"Authorization": "Bearer " + token, "x-ms-version": "2023-11-03"}
            before = self.client.session.get(url, headers=read_headers,
                                             timeout=(20, 90), allow_redirects=False)
            if before.status_code == 200:
                if before.content != content:
                    raise SafetyError(f"Existing staged file differs: {relative}")
                self.state["uploads"][relative] = {"sha256": sha, "bytes": len(content),
                                                   "verifiedUtc": now(), "state": "reused-identical"}
                self.checkpoint()
                continue
            if before.status_code != 404:
                raise SafetyError(f"Cannot inspect staged file: HTTP {before.status_code}")
            prior = self.state["uploads"].get(relative)
            if prior and prior.get("state") == "pending":
                raise SafetyError("Previous upload was ambiguous; inspect before retry.")
            preview = {"timestampUtc": now(), "api": "PutBlob", "url": url, "sha256": sha,
                       "bytes": len(content), "If-None-Match": "*", "scopeSha256": self.state["scopeSha256"]}
            save(self.evidence / "uploads" / f"{file.name}-preview.json", preview)
            self.state["uploads"][relative] = {**preview, "state": "pending"}
            self.checkpoint()
            reply = self.client.session.put(
                url, data=content,
                headers={**read_headers, "x-ms-blob-type": "BlockBlob",
                         "Content-Type": "text/csv", "If-None-Match": "*"},
                timeout=(20, 90), allow_redirects=False,
            )
            save(self.evidence / "uploads" / f"{file.name}-response.json",
                 {"statusCode": reply.status_code, "requestId": reply.headers.get("x-ms-request-id"),
                  "bodyText": reply.text, "timestampUtc": now()})
            if reply.status_code != 201:
                raise SafetyError("Staged PutBlob not confirmed; never overwrite or blindly retry.")
            after = self.client.session.get(url, headers=read_headers,
                                            timeout=(20, 90), allow_redirects=False)
            if after.status_code != 200 or after.content != content:
                raise SafetyError("Staged upload failed complete-byte readback.")
            self.state["uploads"][relative] = {"sha256": sha, "bytes": len(content),
                                               "verifiedUtc": now(), "state": "created-verified"}
            self.checkpoint()

    def ensure_watch_directory(self, lakehouse_id: str) -> None:
        """Prepare the empty watched directory before any native subscription."""
        if self.state.get("items", {}).get("lakehouse", {}).get("id") != lakehouse_id:
            raise SafetyError("Watch directory must belong to the exact owned Lakehouse receipt.")
        url = (f"https://onelake.dfs.fabric.microsoft.com/{self.scope['workspaceId']}"
               f"/{lakehouse_id}/Files/increment")
        token = self.client.credential.get_token("https://storage.azure.com/.default").token
        headers = {"Authorization": "Bearer " + token, "x-ms-version": "2023-11-03"}
        before = self.client.session.head(url, headers=headers, timeout=(20, 60), allow_redirects=False)
        if before.status_code == 200:
            if before.headers.get("x-ms-resource-type") != "directory":
                raise SafetyError("The watch path exists but is not a directory.")
            return
        if before.status_code != 404:
            raise SafetyError("Cannot safely inspect the watch directory.")
        save(self.evidence / "watch-directory-preview.json", {
            "timestampUtc": now(), "url": url, "resource": "directory",
            "scopeSha256": self.state["scopeSha256"], "fileWrite": False,
            "reason": "Prepare watch directory before creating the native OneLake source."})
        response = self.client.session.put(url + "?resource=directory", data=b"",
                                            headers={**headers, "If-None-Match": "*"},
                                            timeout=(20, 60), allow_redirects=False)
        save(self.evidence / "watch-directory-response.json", {
            "timestampUtc": now(), "statusCode": response.status_code,
            "requestId": response.headers.get("x-ms-request-id"), "bodyText": response.text})
        if response.status_code != 201:
            raise SafetyError("Watch directory creation not confirmed; reconcile before retry.")
        after = self.client.session.head(url, headers=headers, timeout=(20, 60), allow_redirects=False)
        if after.status_code != 200 or after.headers.get("x-ms-resource-type") != "directory":
            raise SafetyError("Watch directory readback is not confirmed.")

    def run_notebook01_once(self) -> dict[str, Any]:
        item = self.state["items"]["notebook01"]
        jobs_path = self.prefix + f"/items/{item['id']}/jobs/instances"
        jobs = [j for j in self.client.paged(jobs_path)
                if j.get("jobType") == "RunNotebook"]
        if any(j.get("status") == "Completed" for j in jobs):
            completed = next(j for j in jobs if j.get("status") == "Completed")
            self.state["jobs"]["notebook01"] = completed
            self.checkpoint()
            return completed
        active = [j for j in jobs if j.get("status") in
                  {"NotStarted", "Queued", "InProgress", "Running"}]
        if len(active) > 1:
            raise SafetyError("Multiple active Notebook01 jobs; stop.")
        if active:
            job_id = active[0]["id"]
        else:
            if jobs or "notebook01" in self.state["jobs"]:
                raise SafetyError("Notebook01 has prior execution evidence; corrective rerun needs separate approval.")
            path = self.prefix + f"/items/{item['id']}/jobs/RunNotebook/instances"
            lh = self.state["items"]["lakehouse"]
            body = {"executionData": {"configuration": {
                "defaultLakehouse": {"id": lh["id"], "name": lh["displayName"],
                                     "workspaceId": self.scope["workspaceId"]}
            }}}
            self.allow(path, {"action": "run-once", "notebook": item["id"], "body": body})
            self.state["jobs"]["notebook01"] = {"state": "submission-pending", "timestampUtc": now()}
            self.checkpoint()
            response = self.client.request("POST", path, body=body, expected=(202,),
                                           label="run-notebook01")
            location = response.headers.get("Location", "")
            match = re.search(r"/jobs/instances/([0-9a-fA-F-]{36})(?:[?]|$)", location)
            self.state["jobs"]["notebook01"].update({"location": location,
                                                    "status": "Accepted",
                                                    "retryAfter": response.headers.get("Retry-After")})
            self.checkpoint()
            if not match:
                raise SafetyError("Notebook job accepted without concrete job ID; reconcile, never resubmit.")
            job_id = match.group(1)
            self.state["jobs"]["notebook01"]["id"] = job_id
            self.checkpoint()
            time.sleep(max(1, int(response.headers.get("Retry-After", 10))))
        deadline = time.monotonic() + 1800
        while time.monotonic() < deadline:
            job = self.client.request("GET", jobs_path + "/" + job_id).json()
            self.state["jobs"]["notebook01"] = job
            self.checkpoint()
            if job.get("status") == "Completed":
                return job
            if job.get("status") in {"Failed", "Cancelled", "Canceled", "Deduped"}:
                raise SafetyError("Notebook01 failed; exact reason preserved. No automatic rerun.")
            time.sleep(15)
        raise SafetyError("Notebook01 bounded wait elapsed. Monitor the existing job, never rerun it.")


def source_notebook(number: str, plan: dict[str, Any] | None = None) -> dict[str, Any]:
    path = next((PREVIEW / "notebooks").glob(f"Notebook_{number}_*.ipynb"), None)
    if path is None:
        if number not in {"01", "05"}:
            raise SafetyError("This v3 notebook has not been built.")
        path = next((BASE / "notebooks").glob(f"Notebook_{number}_*.ipynb"))
    if plan is not None and hashlib.sha256(path.read_bytes()).hexdigest() != plan.get("notebookSourceSha256", {}).get(number):
        raise SafetyError(f"Notebook{number} bytes changed after the exact resource plan was frozen.")
    return load(path)


def deploy_sources(args: Any) -> dict[str, Any]:
    from workshop_runtime import bind_notebook_to_lakehouse
    d = Deployment(args)
    workspace = d.client.request("GET", d.prefix).json()
    if workspace.get("displayName") != d.scope["workspaceName"]:
        raise SafetyError("Workspace name changed after approval.")
    lakehouse = d.create("lakehouse", creation_payload={"enableSchemas": True})
    d.upload_staged(lakehouse)
    notebook = bind_notebook_to_lakehouse(
        source_notebook("01", d.plan), d.scope["workspaceId"], lakehouse["id"],
        lakehouse["displayName"], participant_id=d.scope["participantId"])
    definition = {"format": "ipynb", "parts": [part("notebook-content.ipynb",
                                                   json.dumps(notebook, ensure_ascii=False).encode("utf-8"))]}
    d.create("notebook01", definition=definition)
    eventhouse = d.create("eventhouse", skill="eventhouse-cli")
    deadline = time.monotonic() + 240
    while time.monotonic() < deadline:
        matches = [v for v in d.client.paged(d.prefix + "/kqlDatabases")
                   if v.get("properties", {}).get("parentEventhouseItemId") == eventhouse["id"]]
        if len(matches) == 1:
            break
        time.sleep(10)
    if len(matches) != 1 or matches[0].get("folderId") != d.scope["folderId"]:
        raise SafetyError("Generated KQL database not uniquely resolved in target folder.")
    d.state["items"]["kqlDatabase"] = matches[0]
    d.checkpoint()
    if args.run_notebook01:
        d.run_notebook01_once()
    result = {
        "timestampUtc": now(), "edition": "v3.0.0-preview",
        "status": "sources-deployed", "deployed": True,
        "items": d.state["items"], "jobs": d.state["jobs"],
        "incrementsDelivered": d.state.get("incrementDeliveries", {}),
        **live_receipt_summary(d.state),
        "actualReadiness": ("Source stage completed/reconciled. Current cross-stage receipt facts are retained; "
                            "a source-stage resume does not erase later Ontology/Gold/model/Agent completion."),
    }
    save(d.evidence / "result.json", result)
    return result


def read_parts(root: Path) -> dict[str, str]:
    return {p.relative_to(root).as_posix(): p.read_text(encoding="utf-8")
            for p in sorted(root.rglob("*")) if p.is_file()}


def bindings(d: Deployment) -> dict[str, str]:
    values = {"workspace.id": d.scope["workspaceId"], "tenant.id": d.scope["tenantId"]}
    for key, item in d.state["items"].items():
        values["item." + key + ".id"] = item["id"]
        values["name." + key] = item["displayName"]
    if "activator" in d.state["items"]:
        values["name.reflex"] = d.state["items"]["activator"]["displayName"]
    else:
        values["name.reflex"] = d.resources["activator"]["displayName"]
    db = d.state["items"].get("kqlDatabase")
    if db:
        values["item.kqlDatabase.queryServiceUri"] = db["properties"]["queryServiceUri"]
    for key in ("pipeline", "ontology", "dataAgent", "semanticModel"):
        values.setdefault("name." + key, d.resources[key]["displayName"])
    return values


def encode_files(files: dict[str, str], replacements: dict[str, str]) -> dict[str, Any]:
    from workshop_runtime import render_placeholders
    result = []
    for path, text in sorted(files.items()):
        path = render_placeholders(path, replacements)
        text = render_placeholders(text, replacements)
        result.append(part(path, text.encode("utf-8")))
    return {"parts": result}


def deploy_core(args: Any) -> dict[str, Any]:
    from preview30_ontology import encode_definition, lineage
    d = Deployment(args)
    if d.state.get("ontologyNativeUiHandoff"):
        raise SafetyError("Core Ontology writer was handed to native UI. Do not round-trip TMDL after native Metrics.")
    if d.state.get("sourceVerification", {}).get("verified") is not True:
        raise SafetyError("Run verify-sources and prove all twenty generations before core binding.")
    lh = d.require_owned("lakehouse")
    detail = d.client.request("GET", d.prefix + f"/lakehouses/{lh['id']}").json()
    sql = detail["properties"]["sqlEndpointProperties"]
    server = str(sql["connectionString"])
    if not re.fullmatch(r"[A-Za-z0-9.-]+", server):
        raise SafetyError("Unexpected SQL endpoint representation; inspect, do not interpolate.")
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", lh["displayName"]):
        raise SafetyError("Unexpected Lakehouse name for the native binding expression.")
    if any(c in d.scope["workspaceName"] for c in "\r\n\t"):
        raise SafetyError("Workspace name cannot inject native annotation lines.")
    pinned = d.state.setdefault("ontologySourcePinnedAtUtc", now())
    d.checkpoint()
    values = {"ontology.displayName": d.resources["ontology"]["displayName"],
              "ontology.logicalId": lineage("item", d.scope["workspaceId"] + "/" + d.resources["ontology"]["displayName"]),
              "workspace.id": d.scope["workspaceId"],
              "workspace.name": d.scope["workspaceName"],
              "source.lakehouse.id": lh["id"],
              "source.lakehouse.displayName": lh["displayName"],
              "source.lakehouse.oneLakeRootUrl": detail["properties"]["oneLakeFilesPath"].removesuffix("/Files"),
              "source.binding.pinnedAtUtc": pinned,
              "source.lakehouse.sqlEndpoint": server,
              }
    definition = encode_definition(read_parts(PREVIEW / "ontology/definition"), values)
    item = d.create("ontology", definition=definition, skill="fabriciq-ontology-cli")
    current = d.client.request("GET", d.prefix + f"/ontologies/{item['id']}",
                               skill="fabriciq-ontology-cli").json()
    if current.get("properties", {}).get("generation") != 2:
        raise SafetyError("Service did not prove generation2. Never deploy a legacy fallback.")
    actual = d.definition(item["id"], skill="fabriciq-ontology-cli", format_name="TMDL")
    decoded = {p["path"]: base64.b64decode(p["payload"]).decode("utf-8")
               for p in actual["parts"]}
    entities = [v for p, v in decoded.items() if p.startswith("entities/")]
    static_bindings = sum(bool(re.search(r"^\tbackingTable:", v, re.MULTILINE)) for v in entities)
    properties = sum(len(re.findall(r"^\tproperty ", v, re.MULTILINE)) for v in entities)
    relationships = len(re.findall(r"^entityRelationship ", decoded.get("entityRelationships.tmdl", ""), re.MULTILINE))
    if (len(entities), properties, static_bindings, relationships) != (10, 73, 10, 15):
        raise SafetyError("Generation2 readback lost entity/property/static-binding/relationship content.")
    result = {"timestampUtc": now(), "generation": 2, "entityTypes": 10,
              "staticProperties": 72, "staticBindings": 10, "relationships": 15,
              "schemaReadbackVerified": True, "complete": False,
              "timeSeriesBinding": "pending-native-contract",
              "metrics": "pending-native-semantic-model-binding",
              "graphMaterialized": False, "nativeUiObserved": False}
    d.state["ontologyVerification"] = result
    d.checkpoint()
    save(d.evidence / "verification/ontology-static.json", result)
    return result


def deploy_relationships(args: Any) -> dict[str, Any]:
    """Create/reconcile only the opted-in static companion; Graph remains native."""
    from preview30_ontology import encode_definition, lineage, verify_relationships_readback
    d = Deployment(args)
    key = "relationshipsOntology"
    if key not in d.resources or not d.plan.get("relationshipsCompanion", {}).get("createOnly"):
        raise SafetyError("Re-preflight with --include-relationships and approve the new exact plan.")
    if d.state.get("sourceVerification", {}).get("verified") is not True:
        raise SafetyError("The existing static Lakehouse must already have verified source receipts.")
    if getattr(args, "run_notebook01", False):
        raise SafetyError("Companion creation never runs Notebook01 or Notebook05.")
    # Native ownership of the core is deliberately not an obstacle: it is read,
    # not exported, updated or re-created by this separate-item operation.
    core = d.require_owned("ontology")
    lh = d.require_owned("lakehouse")
    if core.get("type") != "Ontology" or lh.get("type") != "Lakehouse":
        raise SafetyError("The owned operational core and Lakehouse types must match.")
    workspace = d.client.request("GET", d.prefix).json()
    folder = d.client.request("GET", d.prefix + f"/folders/{d.scope['folderId']}").json()
    if (workspace.get("displayName") != d.scope["workspaceName"]
            or folder.get("id") != d.scope["folderId"]):
        raise SafetyError("Workspace or approved folder no longer resolves exactly.")
    core_metadata = d.client.request("GET", d.prefix + f"/ontologies/{core['id']}",
                                     skill="fabriciq-ontology-cli").json()
    if core_metadata.get("properties", {}).get("generation") != 2:
        raise SafetyError("The preserved operational core must already be generation2.")
    name = d.resources[key]["displayName"]
    known = d.state["items"].get(key, {})
    for collection in ("items", "recoverableItems"):
        matches = [item for item in d.client.paged(d.prefix + "/" + collection,
                                                  skill="fabriciq-ontology-cli")
                   if item.get("displayName", "").casefold() == name.casefold()]
        if matches and (collection == "recoverableItems" or len(matches) != 1
                        or matches[0].get("id") != known.get("id")
                        or matches[0].get("type") != "Ontology"
                        or matches[0].get("folderId") != d.scope["folderId"]):
            raise SafetyError("Companion name collision; no adoption, restore, purge or replacement.")

    detail = d.client.request("GET", d.prefix + f"/lakehouses/{lh['id']}").json()
    server = str(detail["properties"]["sqlEndpointProperties"]["connectionString"])
    root_url = detail["properties"]["oneLakeFilesPath"].removesuffix("/Files")
    locator = urlparse(root_url)
    if (locator.scheme != "https" or locator.netloc != "onelake.dfs.fabric.microsoft.com"
            or locator.path != f"/{d.scope['workspaceId']}/{lh['id']}"
            or locator.query or locator.fragment):
        raise SafetyError("OneLake locator must identify the same owned workspace/Lakehouse.")
    if (not re.fullmatch(r"[A-Za-z0-9.-]+", server)
            or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", lh["displayName"])
            or any(c in d.scope["workspaceName"] for c in "\r\n\t")):
        raise SafetyError("Unexpected native binding locator; do not interpolate.")
    pinned = d.state.setdefault("relationshipsSourcePinnedAtUtc", now())
    d.checkpoint()
    values = {
        "ontology.displayName": name,
        "ontology.logicalId": lineage("item", d.scope["workspaceId"] + "/" + name),
        "workspace.id": d.scope["workspaceId"], "workspace.name": d.scope["workspaceName"],
        "source.lakehouse.id": lh["id"], "source.lakehouse.displayName": lh["displayName"],
        "source.lakehouse.oneLakeRootUrl": root_url, "source.lakehouse.sqlEndpoint": server,
        "source.binding.pinnedAtUtc": pinned,
    }
    definition = encode_definition(read_parts(PREVIEW / "ontology/relationships/definition"), values)
    verify_relationships_readback(definition, definition)
    item = d.create(key, definition=definition, skill="fabriciq-ontology-cli")
    current = d.client.request("GET", d.prefix + f"/ontologies/{item['id']}",
                               skill="fabriciq-ontology-cli").json()
    save(d.evidence / "verification/relationships-metadata.json", current)
    if current.get("properties", {}).get("generation") != 2:
        raise SafetyError("Companion generation2 was not proved by service readback.")
    actual = d.definition(item["id"], skill="fabriciq-ontology-cli")
    save(d.evidence / "definitions/relationships-readback.json", actual)
    verify_relationships_readback(actual, definition)
    contract = load(PREVIEW / "ontology/relationships/contract.json")
    handoff = {
        "schemaVersion": "furusato-relationships-native-handoff/v1",
        "timestampUtc": now(), "environment": d.scope["environment"],
        "workspaceId": d.scope["workspaceId"], "folderId": d.scope["folderId"],
        "ontologyId": item["id"], "ontologyName": name,
        "preservedOperationalOntologyId": core["id"], "sourceLakehouseId": lh["id"],
        "generation": 2, "entityTypes": 10, "staticProperties": 72,
        "timeseriesProperties": 0, "relationshipTypes": 15, "staticBindings": 10,
        "schemaReadbackVerified": True, "definitionSha256": digest(actual),
        "entitySelection": [entity["name"] for entity in contract["entities"]],
        "relationshipSelection": [rel["name"] for rel in contract["relationships"]],
        "copiedBusinessData": False, "operationalCoreAndKqlBindingUnchanged": True,
        "dataAgentSourceRoutingChanged": False, "automaticGraphMaterialization": False,
        # The public Ontology GET contract documents generation, not a Graph ID.
        "managedGraphId": None, "managedGraphIdStatus": "native-readback-required",
        "graphQueryAcceptance": "required-not-assessed",
        "nativeSteps": [
            "Obtain separate explicit Graph opt-in for this exact ontologyId, workspaceId and folderId; the create gate does not authorize materialization.",
            "Open ontologyName and verify its ID and the same sourceLakehouseId. Preserve preservedOperationalOntologyId and its Eventhouse binding.",
            "In native Graph materialization choose all entitySelection and relationshipSelection entries (10 keyed static entities / 15 relations); never choose the operational core or invent a Graph REST endpoint.",
            "Inspect existing refresh/job history first. Reuse a proven Completed materialization; wait for an active job and reconcile any uncertain prior attempt. Do not submit duplicate refreshes.",
            "Capture the actual managed Graph ID from the native supported response/UI and its association with this ontologyId, plus the terminal materialization job ID/state and source/selection readback. Never infer Graph ID from the Ontology ID or display name.",
            "Execute the existing Graph acceptance queries against that exact managed Graph. Retain actual numerical results and business paths; Eligible, schema readback and Completed refresh alone are not query acceptance.",
            "Use static Donation once. Do not add companion amounts to core amounts or raw operational observations; SupplierProvidesGift remains catalog eligibility, not order fulfillment.",
            "Any future Data Agent source-routing change is a separate frozen, approved, evaluated candidate. This command does not edit or publish an Agent.",
        ],
    }
    d.state["relationshipsVerification"] = {
        k: v for k, v in handoff.items() if k not in {"nativeSteps", "entitySelection", "relationshipSelection"}}
    d.checkpoint()
    save(d.evidence / "relationships-native-handoff.json", handoff)
    return handoff


def kusto_call(d: Deployment, csl: str, *, mutation: bool = False) -> dict[str, Any]:
    from reference_kql import _tables
    db = d.state["items"]["kqlDatabase"]
    if db["id"] in d.scope["forbiddenItemIds"]:
        raise SafetyError("Forbidden KQL database.")
    uri = db["properties"]["queryServiceUri"]
    parsed = urlparse(uri)
    if parsed.scheme != "https" or not parsed.hostname or not parsed.hostname.endswith(".kusto.fabric.microsoft.com"):
        raise SafetyError("Discovered Kusto endpoint host is not supported by this runtime.")
    endpoint = "/v1/rest/mgmt" if csl.lstrip().startswith(".") else "/v1/rest/query"
    url = uri.rstrip("/") + endpoint
    sha = digest({"database": db["id"], "csl": csl})
    record = {"timestampUtc": now(), "databaseId": db["id"], "url": url, "csl": csl,
              "mutation": mutation, "scopeSha256": d.state["scopeSha256"]}
    if mutation:
        prior = d.state["commands"].get(sha)
        if prior:
            if prior.get("state") == "verified":
                return load(d.evidence / "kql" / (sha + "-response.json"))["body"]
            raise SafetyError("Prior KQL management outcome uncertain; reconcile before retry.")
        save(d.evidence / "kql" / (sha + "-preview.json"), record)
        d.state["commands"][sha] = {"state": "pending", "timestampUtc": now()}
        d.checkpoint()
    token = d.client.credential.get_token("https://kusto.kusto.windows.net/.default").token
    response = d.client.session.post(url, json={"db": db["displayName"], "csl": csl},
                                     headers={"Authorization": "Bearer " + token,
                                              "Content-Type": "application/json"},
                                     timeout=(20, 120), allow_redirects=False)
    try:
        body = response.json()
    except ValueError:
        body = {"bodyText": response.text}
    save(d.evidence / "kql" / (sha + "-response.json"),
         {**record, "statusCode": response.status_code, "body": body})
    if response.status_code != 200:
        raise SafetyError("Kusto request failed; exact response saved, no automatic retry.")
    _tables(body)  # Reject partial failures and metadata-only pseudo-results.
    if mutation:
        d.state["commands"][sha] = {"state": "verified", "timestampUtc": now()}
        d.checkpoint()
    return body


def deploy_realtime(args: Any) -> dict[str, Any]:
    from workshop_runtime import extract_kql_management_commands, verify_reflex_fail_closed
    d = Deployment(args)
    d.require_owned("lakehouse")
    d.require_owned("eventhouse")
    d.require_owned("kqlDatabase")
    scripts = list((BASE / "kql").glob("*.kql"))
    schema = next((p for p in scripts if "// Pipeline ingestion verification." in p.read_text(encoding="utf-8")), None)
    if schema is None:
        raise SafetyError("Released KQL management schema is missing.")
    commands = extract_kql_management_commands(schema.read_text(encoding="utf-8"))
    before = kusto_call(d, ".show tables")
    save(d.evidence / "kql/inventory-before-management.json", before)
    for command in commands:
        kusto_call(d, command, mutation=True)
    checks = {}
    for name, query in {
        "schema": ".show table DonationEvents schema as json",
        "mapping": ".show table DonationEvents ingestion csv mappings",
        "view": ".show materialized-view DonationObservationSummaryForAgent",
        "retention": ".show table DonationEvents policy retention",
        "cache": ".show table DonationEvents policy caching",
    }.items():
        checks[name] = kusto_call(d, query)
    save(d.evidence / "kql/readback.json", checks)
    for name, required in {"schema": "EventID", "mapping": "DonationEvents_IncrementCsvMap",
                           "view": "DonationObservationSummaryForAgent",
                           "retention": "90.00:00:00", "cache": "7.00:00:00"}.items():
        if required not in json.dumps(checks[name]):
            raise SafetyError(f"KQL {name} readback did not contain the required contract.")
    bundle = BASE / "provisioning/bundle"
    pipeline = d.create("pipeline", definition=encode_files(read_parts(bundle / "data-pipeline"), bindings(d)))
    d.state["items"]["pipeline"] = {**d.state["items"]["pipeline"], **pipeline}
    reflex_definition = encode_files(read_parts(bundle / "reflex"), bindings(d))
    verify_reflex_fail_closed(reflex_definition)
    # The source is intentionally future FileCreated events; it has not emitted
    # watched increments yet. Rule creation is stopped, not assumed to be armed.
    reflex = d.create("activator", definition=reflex_definition, skill="activator-cli")
    reflex_parts = {p["path"]: base64.b64decode(p["payload"]).decode("utf-8") for p in reflex_definition["parts"]}
    entities = json.loads(reflex_parts["ReflexEntities.json"])
    rules = [x for x in entities if x.get("payload", {}).get("definition", {}).get("type") == "Rule"]
    if len(rules) != 1 or rules[0]["payload"]["definition"]["settings"].get("shouldRun") is not False:
        raise SafetyError("New Activator must remain stopped until its native lifecycle gate.")
    result = {"timestampUtc": now(), "kqlSchemaReadback": True, "pipelineDefinitionReadback": True,
              "activatorId": reflex["id"], "state": "created-stopped-unverified",
              "formalStartPerformed": False, "automaticDeliveryVerified": False,
              "incrementsUploadedToWatchFolder": False}
    d.state["realtime"] = result
    d.checkpoint()
    save(d.evidence / "verification/realtime-prepared.json", result)
    return result


def deploy_semantic_model(args: Any) -> dict[str, Any]:
    d = Deployment(args)
    if d.state.get("goldVerification", {}).get("verified") is not True:
        raise SafetyError("Notebook05 and live Gold source verification must precede the semantic model.")
    d.require_owned("lakehouse")
    root = PREVIEW / "powerbi/Furusato_Analytics.SemanticModel"
    files = read_parts(root)
    files.pop(".platform", None)
    definition = encode_files(files, bindings(d))
    definition["format"] = "TMDL"
    item = d.create("semanticModel", definition=definition, skill="semantic-model-authoring")
    actual = d.definition(item["id"], skill="semantic-model-authoring", format_name="TMDL")
    text = "\n".join(base64.b64decode(p["payload"]).decode("utf-8") for p in actual["parts"])
    metrics = load(PREVIEW / "powerbi/native-metrics-contract.json")
    for measure in metrics["measures"]:
        if measure["name"] not in text or measure["dax"] not in text:
            raise SafetyError("Source-owned DAX expression missing or changed on model readback.")
    result = {"timestampUtc": now(), "id": item["id"], "definitionReadback": True,
              "sourceOwnedDax": True, "daxExecutionVerified": False,
              "ontologyMetricsVisible": False}
    d.state["semanticModelVerification"] = result
    d.checkpoint()
    return result


def deploy_notebooks(args: Any) -> dict[str, Any]:
    from workshop_runtime import bind_notebook_to_lakehouse
    d = Deployment(args)
    lh = d.require_owned("lakehouse")
    result = {}
    for number in ("02", "03", "04", "05"):
        notebook = bind_notebook_to_lakehouse(
            source_notebook(number, d.plan), d.scope["workspaceId"], lh["id"], lh["displayName"],
            participant_id=d.scope["participantId"])
        definition = {"format": "ipynb", "parts": [
            part("notebook-content.ipynb", json.dumps(notebook, ensure_ascii=False).encode("utf-8"))]}
        item = d.create("notebook" + number, definition=definition)
        result["notebook" + number] = {"id": item["id"], "executed": False, "definitionReadback": True}
    return {"timestampUtc": now(), "items": result, "jobsAutomaticallyStarted": False}


def metadata_change(args: Any, *, apply: bool = False) -> dict[str, Any]:
    """Only default-namespace Business Rule metadata, before native UI handoff."""
    d = Deployment(args)
    if d.state.get("ontologyNativeUiHandoff"):
        raise SafetyError("Native UI owns the Ontology; full TMDL roundtrip is blocked.")
    item = d.require_owned("ontology")
    details = d.client.request("GET", d.prefix + f"/ontologies/{item['id']}",
                               skill="fabriciq-ontology-cli").json()
    if details.get("properties", {}).get("generation") != 2:
        raise SafetyError("Notebook02 supports generation2 only.")
    current = d.definition(item["id"], skill="fabriciq-ontology-cli", format_name="TMDL")
    if any(p["path"].startswith("metrics/") for p in current["parts"]):
        raise SafetyError("Native Metrics may lose backingMeasure during TMDL roundtrip; stop.")
    before = digest(current)
    rules = read_parts(PREVIEW / "ontology/definition/rules")
    overrides = getattr(args, "rule_statement_overrides", {}) or {}
    if any(name + ".tmdl" not in rules for name in overrides):
        raise SafetyError("Only the four declared rules may be overridden.")
    for name, statement in overrides.items():
        if not isinstance(statement, str) or not statement.strip() or len(statement) > 4000 or "\n" in statement:
            raise SafetyError("Rule statement must be one natural-language line, <=4000 characters.")
        rules[name + ".tmdl"] = re.sub(r"(?m)^\tstatement:.*$", lambda _: "\tstatement: " + statement,
                                      rules[name + ".tmdl"])
    updated = copy.deepcopy(current)
    for p in updated["parts"]:
        if p["path"].startswith("rules/") and p["path"][6:] in rules:
            p["payload"] = base64.b64encode(rules[p["path"][6:]].encode("utf-8")).decode("ascii")
    preview = {"timestampUtc": now(), "beforeDefinitionSha256": before,
               "afterDefinitionSha256": digest(updated), "ruleFiles": sorted(rules),
               "sourceDataChanged": False, "nativeMetricsRoundtripAllowed": False}
    save(d.evidence / "metadata-preview.json", preview)
    if not apply:
        return {**preview, "mode": "preview", "cloudWritePerformed": False}
    if getattr(args, "expected_definition_sha256", None) != before:
        raise SafetyError("Explicit expected-definition SHA differs; redo the metadata preview.")
    if digest(updated) == before:
        return {**preview, "mode": "unchanged", "cloudWritePerformed": False}
    # Platform metadata is not a metadata-rule change and is never replaced here.
    updated["parts"] = [p for p in updated["parts"] if p["path"] != ".platform"]
    body = {"definition": updated}
    path = d.prefix + f"/items/{item['id']}/updateDefinition"
    d.allow(path, {"action": "replace-owned-rule-metadata", "body": body,
                   "beforeDefinitionSha256": before})
    response = d.client.request("POST", path, body=body, skill="fabriciq-ontology-cli",
                                 expected=(200, 202), label="ontology-rule-metadata")
    if response.status_code == 202:
        d.poll_lro(response.headers["x-ms-operation-id"], skill="fabriciq-ontology-cli")
    actual = d.definition(item["id"], skill="fabriciq-ontology-cli", format_name="TMDL")
    save(d.evidence / "definitions/ontology-after-rule-metadata.json", actual)
    by_path = {p["path"]: base64.b64decode(p["payload"]).decode("utf-8") for p in actual["parts"]}
    for name, statement in overrides.items():
        if statement not in by_path.get(f"rules/{name}.tmdl", ""):
            raise SafetyError("Rule statement did not survive native readback.")
    return {**preview, "mode": "applied", "cloudWritePerformed": True, "readbackCaptured": True}


def handoff_ontology(args: Any) -> dict[str, Any]:
    d = Deployment(args)
    item = d.require_owned("ontology")
    result = {"timestampUtc": now(), "id": item["id"], "writer": "native-ui-coordinator",
              "automatedTmdlWritesDisabled": True,
              "reason": "Native Metrics backingMeasure must not be lost by TMDL roundtrip."}
    d.state["ontologyNativeUiHandoff"] = result
    d.checkpoint()
    save(d.evidence / "ontology-writer-handoff.json", result)
    return result


def deploy_agent(args: Any) -> dict[str, Any]:
    d = Deployment(args)
    for key in ("lakehouse", "kqlDatabase", "ontology", "semanticModel"):
        d.require_owned(key)
    if d.state.get("ontologyVerification", {}).get("generation") != 2:
        raise SafetyError("Data Agent requires a service-proven generation2 Ontology.")
    if d.state.get("modelDaxVerification", {}).get("verified") is not True:
        raise SafetyError("Run actual DAX measure checks before configuring the direct semantic model source.")
    files = read_parts(PREVIEW / "data-agent/definition")
    definition = encode_files(files, bindings(d))
    item = d.create("dataAgent", definition=definition, skill="fabriciq-ontology-cli")
    actual = d.definition(item["id"], skill="fabriciq-ontology-cli")
    documents = {p["path"]: json.loads(base64.b64decode(p["payload"]))
                 for p in actual["parts"] if p["path"].endswith(".json")}
    sources = [v for k, v in documents.items() if k.endswith("/datasource.json")]
    if {s.get("type") for s in sources} != {"lakehouse_tables", "kusto", "ontology", "semantic_model"}:
        raise SafetyError("Data Agent does not contain all four direct sources.")
    model_source = next(s for s in sources if s["type"] == "semantic_model")
    if model_source["artifactId"] != d.state["items"]["semanticModel"]["id"]:
        raise SafetyError("Direct semantic model source points at a different item.")
    stage = documents["Files/Config/draft/stage_config.json"]
    if stage.get("experimental", {}).get("codeInterpreterEnabled") is not True:
        raise SafetyError("Code Interpreter was not configured in the actual draft.")
    result = {"timestampUtc": now(), "id": item["id"], "draftConfigured": True,
              "directSemanticModelConfigured": True, "codeInterpreterConfigured": True,
              "published": False, "aiAnswerQualityVerified": False,
              "codeInterpreterObserved": False}
    d.state["dataAgentVerification"] = result
    d.checkpoint()
    return result


def refresh_model_once(args: Any) -> dict[str, Any]:
    """Initial Direct Lake framing is distinct from a successful TMDL import."""
    d = Deployment(args)
    model = d.require_owned("semanticModel")
    url = (f"https://api.powerbi.com/v1.0/myorg/groups/{d.scope['workspaceId']}"
           f"/datasets/{model['id']}/refreshes")

    def request(method: str, body: Any = None):
        token = d.client.credential.get_token("https://analysis.windows.net/powerbi/api/.default").token
        response = d.client.session.request(
            method, url + ("?$top=5" if method == "GET" else ""), json=body,
            headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"},
            timeout=(20, 120), allow_redirects=False)
        rt_path = d.evidence / "model-refresh" / (str(time.time_ns()) + ".json")
        save(rt_path, {"timestampUtc": now(), "method": method, "url": url,
                       "body": body, "statusCode": response.status_code,
                       "bodyText": response.text,
                       "location": response.headers.get("Location")})
        if response.status_code != (200 if method == "GET" else 202):
            raise SafetyError("Initial model refresh failed; inspect private response. Do not alter credentials/permissions as a workaround.")
        return response

    history = request("GET").json().get("value", [])
    if history and history[0].get("status") == "Completed":
        result = {"timestampUtc": now(), "status": "Completed", "existingRefreshReused": True,
                  "refresh": history[0], "daxExecutionStillRequired": True}
        d.state["semanticModelRefresh"] = result
        d.checkpoint()
        return result
    if history:
        if history[0].get("status") in {"Failed", "Cancelled", "Disabled"}:
            raise SafetyError("A prior refresh failed; inspect its exact outcome instead of blind retry.")
    else:
        if d.state.get("semanticModelRefresh"):
            raise SafetyError("A prior refresh intent has an uncertain outcome; reconcile before retry.")
        body = {"type": "full", "commitMode": "transactional", "retryCount": 0, "maxParallelism": 1}
        d.state["semanticModelRefresh"] = {"status": "submission-pending", "timestampUtc": now(),
                                          "body": body, "modelId": model["id"]}
        d.checkpoint()
        save(d.evidence / "model-refresh/preview.json", {
            "timestampUtc": now(), "scopeSha256": d.state["scopeSha256"], "url": url,
            "body": body, "credentialOrPermissionChange": False})
        request("POST", body)
    deadline = time.monotonic() + 900
    while time.monotonic() < deadline:
        time.sleep(10)
        history = request("GET").json().get("value", [])
        if history and history[0].get("status") in {"Completed", "Failed", "Cancelled", "Disabled"}:
            result = {"timestampUtc": now(), "status": history[0]["status"],
                      "refresh": history[0], "daxExecutionStillRequired": True}
            d.state["semanticModelRefresh"] = result
            d.checkpoint()
            if result["status"] != "Completed":
                raise SafetyError("Initial model refresh did not complete; no automatic retry.")
            return result
    raise SafetyError("Refresh has no terminal status within 900 seconds; do not resubmit.")


def publish_agent_candidate(args: Any) -> dict[str, Any]:
    """Documented staging/publish, never an implicit answer-quality promotion."""
    d = Deployment(args)
    agent = d.require_owned("dataAgent")
    was_published = d.state.get("dataAgentVerification", {}).get("published") is True
    if (d.state.get("modelDaxVerification", {}).get("verified") is not True
            or d.state.get("dataAgentVerification", {}).get("directSemanticModelConfigured") is not True):
        raise SafetyError("Verified DAX and direct model configuration are required before candidate publication.")
    intent_path = d.evidence / "agent-publication-intent.json"
    if intent_path.exists() and not was_published:
        raise SafetyError("A publication intent exists; reconcile outcome rather than retrying publish.")
    path = d.prefix + f"/dataAgents/{agent['id']}/staging/publish"
    body = {"publishedDescription": (
        "Furusato v3 Preview candidate. Static and independent file-derived Gold/DAX are verified; "
        "native operational event delivery and AI answer-quality acceptance remain unverified.")}
    if not was_published:
        save(intent_path, {"timestampUtc": now(), "path": path, "body": body,
                           "scopeSha256": d.state["scopeSha256"], "accuracyAccepted": False})
        d.allow(path, {"action": "publish-owned-preview-candidate-not-accuracy-promotion", "body": body})
        d.client.request("POST", path, body=body, skill="fabriciq-ontology-cli",
                         expected=(200,), label="publish-preview-agent")
    actual = d.definition(agent["id"], skill="fabriciq-ontology-cli")
    save(d.evidence / "definitions/dataAgent-published-readback.json", actual)
    documents = {p["path"]: json.loads(base64.b64decode(p["payload"])) for p in actual["parts"]
                 if p["path"].endswith(".json")}
    sources = [v for p, v in documents.items() if p.startswith("Files/Config/published/")
               and p.endswith("/datasource.json")]
    if {v.get("type") for v in sources} != {"lakehouse_tables", "kusto", "ontology", "semantic_model"}:
        raise SafetyError("Published source inventory is incomplete.")
    if next(v for v in sources if v["type"] == "semantic_model")["artifactId"] != d.state["items"]["semanticModel"]["id"]:
        raise SafetyError("Published direct SemanticModel source differs.")
    if documents["Files/Config/published/stage_config.json"].get("experimental", {}).get("codeInterpreterEnabled") is not True:
        raise SafetyError("Published Code Interpreter configuration missing.")
    result = {"timestampUtc": now(), "id": agent["id"], "published": True,
              "existingPublicationReused": was_published,
              "publishedDefinitionReadback": True, "directSemanticModelConfigured": True,
              "codeInterpreterConfigured": True, "codeInterpreterObserved": False,
              "aiAnswerQualityVerified": False}
    d.state["dataAgentVerification"].update(result)
    d.checkpoint()
    return result
