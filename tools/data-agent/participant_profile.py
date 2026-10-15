"""Apply the fixed workshop profile to one participant's existing Gen2 Agent.

prepare is read-only in Fabric; apply and publish each require --apply. Every
write has an exclusive intent file and is submitted once. verify is read-only.
This tool does not provision resources or establish answer quality. See the
adjacent participant-profile-README.md for prerequisites and recovery steps.
"""
from __future__ import annotations

import argparse
import copy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sys
import time
from urllib.parse import urlencode, urlsplit
from uuid import UUID, uuid4

import measured_contract_profile as measured
from source_grounded_profile import decoded_parts, inline_part

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools/provisioning"))
from reference_agent import discover_tree, effective_selected, index_tree
import reference_sql

API = "https://api.fabric.microsoft.com/v1"
FABRIC_SCOPE = "https://api.fabric.microsoft.com/.default"
PBI_SCOPE = "https://analysis.windows.net/powerbi/api/.default"


class ProfileError(ValueError):
    """A credential-free diagnostic suitable for participants."""


def require(condition, message):
    if not condition:
        raise ProfileError(message)


def guid(value):
    try:
        return str(UUID(value))
    except (ValueError, TypeError, AttributeError):
        raise ProfileError("Supply an actual workspace/item GUID.") from None


def routing_origin(value):
    parsed = urlsplit(value)
    require(parsed.scheme == "https" and parsed.netloc == parsed.hostname
            and parsed.path in ("", "/") and not parsed.query and not parsed.fragment
            and re.fullmatch(r"[a-z0-9-]+\.analysis\.windows\.net", parsed.hostname or ""),
            "Use the observed HTTPS regional analysis.windows.net origin; never guess it.")
    return value.rstrip("/")


def private_root(path, *, create=False):
    path = Path(path)
    require(path.is_absolute(), "Use an absolute private directory outside every Git checkout.")
    require(not any(p.is_symlink() for p in (path, *path.parents)), "Private paths may not traverse symlinks.")
    require(path.resolve() != REPO.resolve() and REPO.resolve() not in path.resolve().parents,
            "Keep actual definitions outside the source distribution, even when it has no .git directory.")
    require(not any((p / ".git").exists() for p in (path, *path.parents)), "Keep actual definitions outside Git.")
    if create:
        path.mkdir(parents=True, exist_ok=False, mode=0o700)
    require(path.is_dir(), "Private directory does not exist; run prepare first.")
    path.chmod(0o700)
    return path


def save(root, name, value):
    path = root / name
    require(not path.is_symlink(), "Evidence path must not be a symlink.")
    with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def load(root, name):
    path = root / name
    require(path.is_file() and not path.is_symlink(), "Required private evidence is missing or is a symlink: " + name)
    return json.loads(path.read_text(encoding="utf-8"))


class Client:
    """Observed public endpoints plus one explicitly observed native metadata origin.

    The native metadata route is an observed UI contract, not a stable public API.
    Changed shapes fail closed. No redirects, hidden write retries or token files.
    """
    def __init__(self, workspace, agent, origin, root, *, credential=None, session=None, sleeper=time.sleep, sql_transport="mcp"):
        if credential is None:
            from azure.identity import AzureCliCredential
            credential = AzureCliCredential()
        if session is None:
            import requests
            session = requests.Session()
        self.workspace, self.agent = guid(workspace), guid(agent)
        self.origin, self.root = routing_origin(origin), root
        self.credential, self.session, self.sleeper = credential, session, sleeper
        require(sql_transport in {"mcp", "odbc"}, "Choose mcp or odbc for SQL metadata reads.")
        self.sql_transport = sql_transport
        self.base = API + f"/workspaces/{self.workspace}/dataAgents/{self.agent}"
        self.counter = 0
        self.run_id = uuid4().hex

    def request(self, method, url, body=None, *, expected=(200,)):
        parsed = urlsplit(url)
        require(parsed.scheme == "https" and not parsed.username and not parsed.password
                and not parsed.fragment and ((parsed.netloc == "api.fabric.microsoft.com"
                and parsed.path.startswith("/v1/")) or
                (url.startswith(self.origin + "/metadata/artifacts/")
                 and parsed.netloc == urlsplit(self.origin).netloc)), "Unapproved API route or redirect.")
        scope = FABRIC_SCOPE if parsed.netloc == "api.fabric.microsoft.com" else PBI_SCOPE
        self.counter += 1
        record = {"method": method, "url": url, "atUtc": datetime.now(timezone.utc).isoformat()}
        token = None
        response = None
        try:
            token = self.credential.get_token(scope).token
            response = self.session.request(method, url, json=body,
                headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"},
                timeout=(20, 120), allow_redirects=False)
            require(len(response.content) <= 32 * 1024 * 1024, "API response exceeds evidence limit.")
            text = response.text.replace(token, "[REDACTED_TOKEN]")
            record.update(status=response.status_code, body=text,
                headers={k: v for k, v in response.headers.items()
                         if k.lower() in {"x-ms-operation-id", "retry-after"}})
            require(response.status_code in expected,
                    f"API returned HTTP {response.status_code}; inspect private evidence. No automatic retry.")
            return response
        except ProfileError:
            raise
        except Exception:
            record["outcome"] = "failed-or-uncertain"
            raise ProfileError("API/authentication outcome is uncertain; inspect private evidence before further action.") from None
        finally:
            save(self.root, f"http-{self.run_id}-{self.counter:04d}.json", record)
            token = None

    def completed(self, response, *, result=False):
        if response.status_code == 202:
            operation = guid(response.headers.get("x-ms-operation-id"))
            for _ in range(120):
                reply = self.request("GET", API + "/operations/" + operation)
                status = reply.json().get("status")
                if status == "Succeeded":
                    return self.request("GET", API + "/operations/" + operation + "/result").json() if result else None
                require(status in {"NotStarted", "Running"}, "Operation failed/cancelled or has an unknown status; do not resubmit.")
                self.sleeper(5)
            raise ProfileError("Operation is still pending. Retain its ID; verify before any new write.")
        return response.json() if result else None

    def definition(self, kind, item, *, format_name=None):
        url = API + f"/workspaces/{self.workspace}/{kind}/{guid(item)}/getDefinition"
        if format_name:
            url += "?" + urlencode({"format": format_name})
        value = self.completed(self.request("POST", url, {}, expected=(200, 202)), result=True)
        return value.get("definition", value)

    def get(self, path):
        return self.request("GET", API + f"/workspaces/{self.workspace}/" + path).json()

    def pages(self, url):
        original, rows, seen = url, [], set()
        for _ in range(200):
            require(url not in seen, "Repeated pagination token/URL.")
            seen.add(url)
            page = self.request("GET", url).json()
            require(isinstance(page.get("value"), list), "Unexpected collection response.")
            rows.extend(page["value"])
            continuation = page.get("continuationUri")
            token = page.get("continuationToken")
            if not continuation and not token:
                return rows
            if continuation:
                expected_path = urlsplit(original).path
                actual = urlsplit(continuation)
                require(actual.scheme == "https" and actual.netloc == "api.fabric.microsoft.com"
                        and actual.path == expected_path, "Continuation left the original collection.")
                url = continuation
            else:
                url = original + ("&" if "?" in original else "?") + urlencode({"continuationToken": token})
        raise ProfileError("Pagination exceeded its limit.")

    def sql_columns(self, lakehouse):
        if self.sql_transport == "mcp":
            from types import SimpleNamespace
            from preview30_verify import ReadOnlySqlMcp
            endpoint = guid(lakehouse.get("properties", {}).get("sqlEndpointProperties", {}).get("id"))
            item = self.get("items/" + endpoint)
            require(item.get("id") == endpoint and item.get("type") == "SQLEndpoint", "Bound Lakehouse SQL endpoint is not verified.")
            evidence = self.root / ("sql-mcp-" + uuid4().hex)
            evidence.mkdir(mode=0o700)
            adapter = SimpleNamespace(scope={"workspaceId": self.workspace}, evidence=evidence,
                                      session=self.session, credential=self.credential)
            query = "\n".join(line for line in (measured.PROFILE / "sql-schema-inventory.sql").read_text(encoding="utf-8").splitlines()
                              if not line.lstrip().startswith("--"))
            try:
                return ReadOnlySqlMcp(adapter, endpoint).query(endpoint, query)
            except Exception:
                raise ProfileError("SQL MCP metadata read failed; inspect private evidence. No SQL write or fallback was issued.") from None
        driver = reference_sql.require_odbc_driver()
        endpoint = reference_sql.resolve_sql_endpoint(lakehouse)
        connection = cursor = None
        try:
            token = self.credential.get_token("https://database.windows.net/.default").token
            connection = driver.connect(reference_sql.odbc_connection_string(endpoint),
                attrs_before={1256: reference_sql.pack_sql_access_token(token)}, autocommit=True, timeout=30)
            token = None
            connection.timeout = 120
            cursor = connection.cursor()
            return reference_sql._query(cursor, (measured.PROFILE / "sql-schema-inventory.sql").read_text(encoding="utf-8"))
        except Exception:
            raise ProfileError("SQL metadata read failed. Check ODBC Driver 18, SQL permissions and port 1433; no SQL write was issued.") from None
        finally:
            for item in (cursor, connection):
                if item is not None:
                    try:
                        item.close()
                    except Exception:
                        pass

    def close(self):
        self.session.close()
        self.credential.close()


def bound_sources(definition, workspace, stage="draft"):
    docs, sources, serialization = measured.stage_sources(definition, stage)
    require(serialization == "native-ontology-context", "This participant workflow requires Gen2: three sources and one native Ontology context.")
    require(all(value.get("workspaceId") == workspace for _, value in sources.values()), "Source belongs to another workspace.")
    require(len({value.get("artifactId") for _, value in sources.values()}) == 4, "Four distinct bound items are required.")
    return docs, sources


def public_sources(client, definition, stage="draft"):
    _, wanted = bound_sources(definition, client.workspace, stage)
    base = client.base + ("/staging" if stage == "draft" else "")
    sources = client.pages(base + "/datasources")
    require(len(sources) == 3, "Exactly three public direct sources are required; Ontology is a separate context.")
    found = {}
    for source in sources:
        kind = "lakehouse_tables" if source.get("type") == "LakehouseTables" else {
            "KQLDatabase": "kusto", "SemanticModel": "semantic_model"}.get(source.get("fabricItemType")) if source.get("type") == "FabricItem" else None
        require(kind in measured.DIRECT_KINDS and kind not in found and isinstance(source.get("id"), str), "Unexpected or duplicate public datasource.")
        reference = source.get("lakehouseReference" if kind == "lakehouse_tables" else "itemReference", {})
        target = wanted[kind][1]
        require(reference == {"referenceType": "ById", "itemId": target["artifactId"], "workspaceId": client.workspace}, "Public source differs from actual definition binding.")
        found[kind] = source
    return found


def tree(client, source, stage="draft"):
    base = client.base + ("/staging" if stage == "draft" else "") + "/datasources/" + source["id"] + "/elements"
    return discover_tree(lambda root: client.pages(base + ("?" + urlencode({"rootId": root}) if root is not None else "")))


def normalize_sql_types(definition, rows, records):
    """Fill only blank native types using TWO independent current observations.

    Public opaque IDs and serialized IDs are different; correspondence is by exact
    schema/object/column path and type. No node, ID, or nonblank type is invented.
    """
    metadata, public = measured.sql_metadata(rows), index_tree(records)
    docs, sources, _ = measured.stage_sources(definition, "draft")
    path, source = sources["lakehouse_tables"]
    source = copy.deepcopy(source)
    proof = []
    for ancestry, node in measured.walk(source["elements"]):
        if node.get("type") != "lakehouse_tables.column":
            continue
        require(len(ancestry) == 5 and ancestry[0] == "Schemas" and ancestry[2] in {"Tables", "Views"}, "Unknown native SQL column ancestry.")
        key = ancestry[1], ancestry[3], ancestry[4]
        if key not in metadata:
            continue
        public_key = (("Schema", key[0]), ("View" if ancestry[2] == "Views" else "Table", key[1]), ("Column", key[2]))
        actual = public.get(public_key, {}).get("element", {})
        require(actual.get("state") == "Available" and actual.get("dataType") == metadata[key], "Independent SQL/public type mismatch or unavailable column.")
        require(node.get("data_type") in (None, "", metadata[key]), "Nonblank native SQL type differs; do not overwrite it.")
        if not node.get("data_type"):
            proof.append({"path": ancestry, "nativeId": node.get("id"), "publicId": actual.get("id"), "type": metadata[key]})
            node["data_type"] = metadata[key]
    parts = [inline_part(path, source) if part["path"] == path else copy.deepcopy(part)
             for part in definition.get("definition", definition)["parts"]]
    return {"parts": parts}, proof


def gather(client):
    agent = client.get("items/" + client.agent)
    require(agent.get("id") == client.agent and agent.get("type") == "DataAgent", "Target is not the specified existing Data Agent.")
    definition = client.definition("dataAgents", client.agent)
    _, sources = bound_sources(definition, client.workspace)
    items = {kind: client.get("items/" + source["artifactId"]) for kind, (_, source) in sources.items()}
    expected = {"lakehouse_tables": "Lakehouse", "kusto": "KQLDatabase", "semantic_model": "SemanticModel", "ontology": "Ontology"}
    for kind, item in items.items():
        require(item.get("id") == sources[kind][1]["artifactId"] and item.get("type") == expected[kind], "Bound item type or identity differs.")
    ontology_id = sources["ontology"][1]["artifactId"]
    typed = client.get("ontologies/" + ontology_id)
    require(typed.get("id") == ontology_id and typed.get("properties", {}).get("generation") == 2, "Typed Ontology API must report generation 2.")
    ontology = client.request("GET", client.origin + "/metadata/artifacts/" + ontology_id).json()
    require(ontology.get("folderObjectId") == client.workspace, "Native Ontology metadata belongs to another workspace.")
    measured.verify_ontology_item(ontology, sources["ontology"][1])
    model = client.definition("semanticModels", sources["semantic_model"][1]["artifactId"], format_name="TMDL")
    lakehouse = client.get("lakehouses/" + sources["lakehouse_tables"][1]["artifactId"])
    rows = client.sql_columns(lakehouse)
    direct = public_sources(client, definition)
    records = tree(client, direct["lakehouse_tables"])
    normalized, proof = normalize_sql_types(definition, rows, records)
    return {"definition": definition, "normalized": normalized, "sql_columns": rows, "model": model,
            "ontology": ontology, "typed_ontology": typed, "sql_tree": records, "normalization_proof": proof}


def compile_inputs(inputs):
    return measured.compile_measured_draft(inputs["normalized"], input_stage="draft",
        sql_columns=inputs["sql_columns"], native_model=inputs["model"], ontology_item=inputs["ontology"], profile=measured.PROFILE)


def compare_stage(actual, candidate, stage):
    current, wanted = decoded_parts(actual), decoded_parts(candidate)
    expected = {p.replace("/draft/", "/" + stage + "/", 1): value for p, value in wanted.items() if p.startswith("Files/Config/draft/")}
    require({p: value for p, value in current.items() if p.startswith("Files/Config/" + stage + "/")} == expected,
            "Complete service stage differs from compiled content. Preserve evidence; do not repeat the write.")
    for path, value in wanted.items():
        if path not in {"Files/Config/publish_info.json", ".platform"} and not path.startswith(("Files/Config/draft/", "Files/Config/published/")):
            require(current.get(path) == value, "Shared Agent identity or runtime configuration changed.")


def verify_public(client, candidate, stage):
    docs, wanted = bound_sources(candidate, client.workspace)
    sources = public_sources(client, candidate if stage == "draft" else client.definition("dataAgents", client.agent), stage)
    base = client.base + ("/staging" if stage == "draft" else "")
    counts = {}
    for kind, source in sources.items():
        target = wanted[kind][1]
        require(source.get("instructions") == target.get("dataSourceInstructions")
                and source.get("description") == target.get("userDescription"), "Public source instructions/description differ from compiled profile.")
        shots = client.pages(base + "/datasources/" + source["id"] + "/fewshots")
        expected = docs.get(wanted[kind][0].replace("datasource.json", "fewshots.json"), {}).get("fewShots", [])
        pick = lambda values: sorted((v["id"], v["question"], v["query"]) for v in values)
        require(pick(shots) == pick(expected), "Public few-shots differ from the compiled profile.")
        require(all(row.get("validationStatus", {}).get("value") == "Valid" for row in shots), "Few-shots are not all Valid. Wait, then run verify; do not publish yet.")
        counts[kind] = len(shots)
    require(counts == {"lakehouse_tables": 0, "kusto": 9, "semantic_model": 0}, "Unexpected active example counts.")
    records = tree(client, sources["lakehouse_tables"], stage)
    actual = {tuple(tuple(p) for p in row["path"]): row["element"] for row in records
              if effective_selected(row) and row["element"]["type"] in {"Table", "View", "Column"}}
    _, _, selections, _, _ = measured.profile_inputs()
    expected = {}
    for node in selections["lakehouse_tables"]:
        if node["type"].split(".")[-1] not in {"table", "view", "column"}:
            continue
        p = node["path"]
        key = (("Schema", p[1]), ("View" if p[2] == "Views" else "Table", p[3]))
        if node["type"].endswith(".column"):
            key += (("Column", p[4]),)
        expected[key] = node
    require(set(actual) == set(expected) and all(v.get("state") == "Available" for v in actual.values()),
            "Public SQL selection is not exactly the required 17 objects and 143 columns.")
    require(all(actual[key].get("description") == value.get("description") for key, value in expected.items() if "description" in value),
            "Public selected SQL descriptions differ from the compiled profile.")
    return {"directSources": 3, "selectedSqlObjects": 17, "selectedSqlColumns": 143, "activeKqlExamples": 9,
            "ontologyContextPreserved": True, "ontologyContextAvailabilityVerified": False, "answerAccuracyVerified": False}


def prepare(client, root):
    inputs = gather(client)
    save(root, "inputs.json", inputs)
    candidate, receipt = compile_inputs(inputs)
    save(root, "candidate.json", candidate)
    save(root, "compile-receipt.json", receipt)
    manifest = {"schemaVersion": 1, "workspaceId": client.workspace, "agentId": client.agent,
                "routingOrigin": client.origin, "profile": measured.CURRENT_PROFILE,
                "sqlTransport": client.sql_transport,
                "inputsSha256": measured.digest(inputs), "candidateSha256": measured.digest(candidate),
                "profileManifestSha256": receipt["profileManifestSha256"], "cloudWrites": 0}
    save(root, "prepared.json", manifest)
    return {"status": "prepared", "cloudWrites": 0, "selectedSqlObjects": 17, "selectedSqlColumns": 143,
            "answerAccuracyVerified": False}


def prepared(root, workspace, agent, profile):
    manifest, inputs, candidate = (load(root, name) for name in ("prepared.json", "inputs.json", "candidate.json"))
    require((manifest.get("workspaceId"), manifest.get("agentId"), manifest.get("profile")) == (workspace, agent, profile), "Prepared bundle belongs to different IDs/profile.")
    require(manifest["inputsSha256"] == measured.digest(inputs) and manifest["candidateSha256"] == measured.digest(candidate), "Prepared evidence changed.")
    rebuilt, receipt = compile_inputs(inputs)
    require(rebuilt == candidate and receipt["profileManifestSha256"] == manifest["profileManifestSha256"], "Profile/compiler changed after prepare; use a fresh preparation.")
    return manifest, inputs, candidate


def apply(client, root, inputs, candidate):
    require(not (root / "apply-intent.json").exists(), "An apply intent already exists. Run verify --stage draft; never replay an uncertain write.")
    fresh = gather(client)
    rebuilt, _ = compile_inputs(fresh)
    require(decoded_parts(fresh["definition"]) == decoded_parts(inputs["definition"]), "Agent changed since prepare; no overwrite was issued.")
    require(rebuilt == candidate, "Source schema/model/Ontology changed since prepare; no overwrite was issued.")
    save(root, "apply-backup.json", fresh["definition"])
    save(root, "apply-intent.json", {"candidateSha256": measured.digest(candidate), "operation": "updateDefinition", "submittedAtUtc": datetime.now(timezone.utc).isoformat()})
    client.completed(client.request("POST", client.base + "/updateDefinition", {"definition": candidate}, expected=(200, 202)))
    actual = client.definition("dataAgents", client.agent)
    save(root, "draft-readback.json", actual)
    compare_stage(actual, candidate, "draft")
    before = decoded_parts(inputs["definition"])
    after = decoded_parts(actual)
    require({p: v for p, v in before.items() if "/published/" in p} == {p: v for p, v in after.items() if "/published/" in p}, "Published content changed during Draft update.")
    save(root, "applied.json", {"status": "draft-matches", "publishedUnchanged": True, "answerAccuracyVerified": False})
    return {"status": "draft-matches", "published": False, "answerAccuracyVerified": False}


def verify(client, root, candidate, stage):
    actual = client.definition("dataAgents", client.agent)
    save(root, f"verify-{stage}-{uuid4().hex}.json", actual)
    compare_stage(actual, candidate, stage)
    summary = verify_public(client, candidate, stage)
    summary.update(status=stage + "-matches", profile=measured.CURRENT_PROFILE)
    save(root, f"verification-{stage}-{uuid4().hex}.json", summary)
    return summary


def publish(client, root, inputs, candidate):
    require(not (root / "publish-intent.json").exists(), "A publish intent already exists. Run verify --stage published; never replay an uncertain write.")
    verify(client, root, candidate, "draft")
    # Re-read immediately before publication, after all source checks.
    latest = client.definition("dataAgents", client.agent)
    compare_stage(latest, candidate, "draft")
    before, after = decoded_parts(inputs["definition"]), decoded_parts(latest)
    require({p: v for p, v in before.items() if "/published/" in p} ==
            {p: v for p, v in after.items() if "/published/" in p},
            "Published content changed since preparation; reconcile concurrent work before publishing.")
    save(root, "publish-backup.json", latest)
    save(root, "publish-intent.json", {"candidateSha256": measured.digest(candidate), "operation": "publish", "submittedAtUtc": datetime.now(timezone.utc).isoformat()})
    response = client.request("POST", client.base + "/staging/publish", {
        "publishedDescription": "Furusato measured-contract-20261015; three direct sources and one existing Gen2 Ontology context. Configuration readback is separate from source availability and answer-quality evaluation."}, expected=(200, 202))
    client.completed(response)
    summary = verify(client, root, candidate, "published")
    save(root, "published.json", summary)
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("prepare", "apply", "publish", "verify"))
    parser.add_argument("--workspace-id", required=True)
    parser.add_argument("--agent-id", required=True)
    parser.add_argument("--profile", choices=(measured.CURRENT_PROFILE,), required=True)
    parser.add_argument("--private-root", type=Path, required=True)
    parser.add_argument("--routing-origin", help="Observed UI regional origin; required only for prepare.")
    parser.add_argument("--sql-transport", choices=("mcp", "odbc"), default="mcp", help="prepare only; default uses Fabric HTTPS, optional ODBC needs Driver 18")
    parser.add_argument("--stage", choices=("draft", "published"), default="published", help="verify only")
    parser.add_argument("--apply", action="store_true", help="Explicitly authorize this apply or publish command.")
    args = parser.parse_args(argv)
    client = None
    try:
        workspace, agent = guid(args.workspace_id), guid(args.agent_id)
        require(args.phase not in {"apply", "publish"} or args.apply, "This phase requires explicit --apply; no request was issued.")
        require(not args.apply or args.phase in {"apply", "publish"}, "--apply is only for the two write phases.")
        if args.phase == "prepare":
            origin = routing_origin(args.routing_origin or "")
            root = private_root(args.private_root, create=True)
            inputs = candidate = None
            sql_transport = args.sql_transport
        else:
            root = private_root(args.private_root)
            manifest, inputs, candidate = prepared(root, workspace, agent, args.profile)
            origin = manifest["routingOrigin"]
            sql_transport = manifest["sqlTransport"]
        client = Client(workspace, agent, origin, root, sql_transport=sql_transport)
        if args.phase == "prepare":
            result = prepare(client, root)
        elif args.phase == "apply":
            result = apply(client, root, inputs, candidate)
        elif args.phase == "publish":
            result = publish(client, root, inputs, candidate)
        else:
            result = verify(client, root, candidate, args.stage)
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (ValueError, OSError, KeyError) as error:
        print("Stopped: " + str(error), file=sys.stderr)
        return 2
    finally:
        if client is not None:
            client.close()


if __name__ == "__main__":
    raise SystemExit(main())
