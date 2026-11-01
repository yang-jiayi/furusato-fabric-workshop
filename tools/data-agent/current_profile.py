"""Bind the source-exact experimental profile to an existing participant Agent.

prepare/verify only read Fabric. apply/publish each submit one explicitly
authorized write, with exclusive intent, backup and complete stage readback.
No resource, schema, permission, Ontology mapping or example is created.
"""
from __future__ import annotations

import argparse
import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
from uuid import uuid4

import measured_contract_profile as native
import participant_profile as safety
from source_grounded_profile import decoded_parts, inline_part

PROFILE = Path(__file__).resolve().parents[2] / "workshop/v3.0.0-preview/data-agent/profiles/current-experimental"
NAME = "current-experimental"
KINDS = {"lakehouse_tables", "kusto", "semantic_model", "ontology"}
TYPES = {"lakehouse_tables": "Lakehouse", "kusto": "KQLDatabase",
         "semantic_model": "SemanticModel", "ontology": "Ontology"}
require = safety.require


def load_profile(profile=PROFILE):
    manifest = json.loads((profile / "profile-manifest.json").read_bytes())
    expected = {"global-instructions.txt", "source-instructions.json", "selection-contract.json",
                "definition/stage_config.json", *("definition/" + kind + ".json" for kind in KINDS)}
    require(manifest.get("schemaVersion") == 1 and manifest.get("profile") == NAME
            and manifest.get("status") == "experimental" and manifest.get("answerAccuracyAccepted") is False
            and set(manifest.get("sha256", {})) == expected, "Unknown or incomplete experimental profile.")
    for path, digest in manifest["sha256"].items():
        require(hashlib.sha256((profile / path).read_bytes()).hexdigest() == digest,
                "Profile input changed: " + path)
    stage = json.loads((profile / "definition/stage_config.json").read_bytes())
    raw = (profile / "global-instructions.txt").read_bytes()
    require(raw.decode("utf-8") == stage["aiInstructions"]
            and len(raw.decode("utf-8").encode("utf-16-le")) // 2 == manifest["instructionUtf16Units"] == 9422
            and manifest["instructionLimitUtf16Units"] == 10000, "Exact global instructions changed.")
    templates = {kind: json.loads((profile / ("definition/" + kind + ".json")).read_bytes()) for kind in KINDS}
    selections = json.loads((profile / "selection-contract.json").read_bytes())
    instructions = json.loads((profile / "source-instructions.json").read_bytes())
    for kind, source in templates.items():
        require(selections[kind] == [{"path": list(path), **{
            key: value for key, value in node.items() if key not in {"id", "children"}
        }} for path, node in native.walk(source["elements"])], "Selection documentation differs from template.")
        require(instructions[kind] == {"instructions": source.get("dataSourceInstructions"),
                                       "description": source.get("userDescription")},
                "Source instructions differ from template.")
    return manifest, stage, templates


def node_token(kind, path):
    return "{{node:" + kind + ":" + "|".join(path) + "}}"


def substitute(value, identities):
    if isinstance(value, dict):
        return {key: substitute(child, identities) for key, child in value.items()}
    if isinstance(value, list):
        return [substitute(child, identities) for child in value]
    if isinstance(value, str) and value.startswith(("{{node:", "{{resource:", "{{workspace:")):
        require(value in identities, "Unresolved profile identity token.")
        return identities[value]
    return value


def compile_draft(definition, workspace, *, profile=PROFILE):
    """Replace identities only in templates; never synthesize service nodes."""
    manifest, stage, templates = load_profile(profile)
    workspace = safety.guid(workspace)
    docs, sources, serialization = native.stage_sources(definition, "draft")
    require(serialization == "native-ontology-context", "An existing Gen2 native Ontology context is required.")
    prefix = "Files/Config/draft/"
    require({path for path in docs if path.startswith(prefix)} ==
            {prefix + "stage_config.json", *(path for path, _ in sources.values())},
            "Unexpected Draft parts/examples; reconcile them instead of silently removing them.")
    original_stage = docs[prefix + "stage_config.json"]
    require(set(original_stage) == set(stage) and original_stage["$schema"] == stage["$schema"],
            "Unknown stage configuration schema.")
    require(len({value.get("artifactId") for _, value in sources.values()}) == 4,
            "Four distinct actual source identities are required.")
    identities = {"{{workspace:id}}": workspace}
    for kind, (_, source) in sources.items():
        template = templates[kind]
        name = source.get("displayName")
        require(source.get("workspaceId") == workspace and isinstance(name, str) and name
                and "/" not in name and "\\" not in name, "Source identity/workspace differs.")
        identities["{{resource:" + kind + ":id}}"] = safety.guid(source.get("artifactId"))
        identities["{{resource:" + kind + ":name}}"] = name
        require(set(source) == set(template)
                and all(source.get(key) == template.get(key) for key in ("$schema", "type", "metadata")),
                "Unknown native source schema/type/metadata; no write was prepared.")
        actual_nodes = {(path, node["type"]): node for path, node in native.walk(source["elements"])}
        expected_nodes = {(path, node["type"]): node for path, node in native.walk(template["elements"])}
        require(len(actual_nodes) == len(list(native.walk(source["elements"])))
                and set(actual_nodes) == set(expected_nodes),
                "Missing, extra or duplicate source node paths; refresh the actual selection without inventing IDs.")
        for key, expected in expected_nodes.items():
            actual = actual_nodes[key]
            require(set(actual) == set(expected)
                    and actual.get("data_type") == expected.get("data_type")
                    and isinstance(actual.get("id"), str) and bool(actual["id"]),
                    "Native node shape/type/identity drift; inspect current metadata.")
            identities[node_token(kind, key[0])] = actual["id"]
    replacements = {prefix + "stage_config.json": stage}
    for kind, (path, _) in sources.items():
        replacements[path] = substitute(templates[kind], identities)
    parts = definition.get("definition", definition)["parts"]
    candidate = {"parts": [inline_part(part["path"], replacements[part["path"]])
                           if part["path"] in replacements else copy.deepcopy(part) for part in parts]}
    receipt = {"profile": NAME, "status": "experimental", "answerAccuracyAccepted": False,
               "identitySubstitutionOnly": True, "instructionUtf16Units": 9422,
               "profileManifestSha256": hashlib.sha256((profile / "profile-manifest.json").read_bytes()).hexdigest(),
               "counts": manifest["counts"], "candidateSha256": native.digest(candidate)}
    return candidate, receipt


def compare_stage(actual, candidate, stage):
    safety.compare_stage(actual, candidate, stage)
    current, wanted = decoded_parts(actual), decoded_parts(candidate)
    shared = lambda docs: {p: v for p, v in docs.items()
                           if not p.startswith(("Files/Config/draft/", "Files/Config/published/"))
                           and p not in {".platform", "Files/Config/publish_info.json"}}
    require(shared(current) == shared(wanted), "Complete shared runtime configuration changed.")


def gather(client, folder, *, stage="draft"):
    folder_item = client.get("folders/" + folder)
    require(folder_item.get("id") == folder, "The explicit target folder was not resolved.")
    agent = client.get("items/" + client.agent)
    require(agent.get("id") == client.agent and agent.get("type") == "DataAgent"
            and agent.get("folderId") == folder, "Existing Agent is not in the explicitly scoped folder.")
    definition = client.definition("dataAgents", client.agent)
    _, sources = safety.bound_sources(definition, client.workspace, stage)
    items = {}
    for kind, (_, source) in sources.items():
        item = client.get("items/" + safety.guid(source["artifactId"]))
        require(item.get("id") == source["artifactId"] and item.get("type") == TYPES[kind]
                and item.get("folderId") == folder, "A bound source is outside the explicit folder or has the wrong type.")
        items[kind] = item
    ontology = client.get("ontologies/" + sources["ontology"][1]["artifactId"])
    require(ontology.get("properties", {}).get("generation") == 2, "Ontology must be an existing Gen2 item.")
    public = safety.public_sources(client, definition, stage)
    return {"definition": definition, "items": items, "ontology": ontology, "publicSources": public}


def verify(client, root, candidate, folder, stage):
    actual = gather(client, folder, stage=stage)
    safety.save(root, "verify-" + stage + "-" + uuid4().hex + ".json", actual)
    compare_stage(actual["definition"], candidate, stage)
    _, wanted, _ = native.stage_sources(candidate, "draft")
    base = client.base + ("/staging" if stage == "draft" else "")
    for kind, source in actual["publicSources"].items():
        expected = wanted[kind][1]
        require(source.get("instructions") == expected["dataSourceInstructions"]
                and source.get("description") == expected["userDescription"],
                "Public instructions/description differ from the full definition.")
        examples = client.pages(base + "/datasources/" + source["id"] + "/fewshots")
        require(examples == [], "Unexpected active examples; configuration is not the exact experimental snapshot.")
    result = {"status": stage + "-matches", "profile": NAME, "experimental": True,
              "instructionUtf16Units": 9422, "logicalSources": 4,
              "completeStageReadbackVerified": True, "sourceAvailabilityVerified": False,
              "answerAccuracyAccepted": False}
    safety.save(root, "verification-" + stage + "-" + uuid4().hex + ".json", result)
    return result


def prepare(client, root, folder):
    inputs = gather(client, folder)
    candidate, receipt = compile_draft(inputs["definition"], client.workspace)
    safety.save(root, "inputs.json", inputs)
    safety.save(root, "candidate.json", candidate)
    safety.save(root, "compile-receipt.json", receipt)
    safety.save(root, "prepared.json", {
        "workspaceId": client.workspace, "agentId": client.agent, "folderId": folder,
        "routingOrigin": client.origin, "profile": NAME,
        "inputsSha256": native.digest(inputs), "candidateSha256": native.digest(candidate),
        "profileManifestSha256": receipt["profileManifestSha256"]})
    return {"status": "prepared", "cloudWrites": 0, "experimental": True, "answerAccuracyAccepted": False}


def prepared(root, workspace, agent, folder):
    manifest, inputs, candidate = [safety.load(root, name) for name in
                                    ("prepared.json", "inputs.json", "candidate.json")]
    require((manifest.get("workspaceId"), manifest.get("agentId"), manifest.get("folderId"), manifest.get("profile"))
            == (workspace, agent, folder, NAME), "Prepared scope/profile differs.")
    rebuilt, receipt = compile_draft(inputs["definition"], workspace)
    require(native.digest(inputs) == manifest["inputsSha256"]
            and native.digest(candidate) == manifest["candidateSha256"]
            and rebuilt == candidate and receipt["profileManifestSha256"] == manifest["profileManifestSha256"],
            "Inputs, compiler or profile changed; use a new private preparation.")
    return manifest, inputs, candidate


def apply(client, root, folder, inputs, candidate):
    require(not (root / "apply-intent.json").exists(), "Apply intent exists; reconcile with verify, never replay.")
    fresh = gather(client, folder)
    require(fresh == inputs, "Source bindings/metadata or Agent changed since prepare; no overwrite was issued.")
    rebuilt, _ = compile_draft(fresh["definition"], client.workspace)
    require(rebuilt == candidate, "Candidate changed since prepare.")
    safety.save(root, "apply-backup.json", fresh)
    safety.save(root, "apply-intent.json", {"operation": "updateDefinition",
                "candidateSha256": native.digest(candidate), "submittedAtUtc": datetime.now(timezone.utc).isoformat()})
    client.completed(client.request("POST", client.base + "/updateDefinition", {"definition": candidate}, expected=(200, 202)))
    actual = client.definition("dataAgents", client.agent)
    safety.save(root, "draft-readback.json", actual)
    compare_stage(actual, candidate, "draft")
    published = lambda value: {p: v for p, v in decoded_parts(value).items() if p.startswith("Files/Config/published/")}
    require(published(actual) == published(inputs["definition"]), "Published configuration changed during Draft update.")
    return verify(client, root, candidate, folder, "draft")


def publish(client, root, folder, inputs, candidate):
    require(not (root / "publish-intent.json").exists(), "Publish intent exists; reconcile with verify, never replay.")
    verify(client, root, candidate, folder, "draft")
    latest = client.definition("dataAgents", client.agent)
    compare_stage(latest, candidate, "draft")
    published = lambda value: {p: v for p, v in decoded_parts(value).items() if p.startswith("Files/Config/published/")}
    require(published(latest) == published(inputs["definition"]), "Concurrent Published change; no publish was issued.")
    safety.save(root, "publish-backup.json", latest)
    safety.save(root, "publish-intent.json", {"operation": "publish",
                "candidateSha256": native.digest(candidate), "submittedAtUtc": datetime.now(timezone.utc).isoformat()})
    client.completed(client.request("POST", client.base + "/staging/publish", {
        "publishedDescription": "Furusato experimental profile; exact configuration readback is not answer-quality acceptance."
    }, expected=(200, 202)))
    return verify(client, root, candidate, folder, "published")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("prepare", "apply", "publish", "verify"))
    for name in ("workspace-id", "folder-id", "agent-id"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--private-root", type=Path, required=True)
    parser.add_argument("--routing-origin", help="Observed regional analysis.windows.net origin; prepare only.")
    parser.add_argument("--stage", choices=("draft", "published"), default="published")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    client = None
    try:
        workspace, agent, folder = map(safety.guid, (args.workspace_id, args.agent_id, args.folder_id))
        require(args.apply == (args.phase in {"apply", "publish"}),
                "Only apply/publish require --apply; prepare/verify must remain read-only.")
        root = safety.private_root(args.private_root, create=args.phase == "prepare")
        if args.phase == "prepare":
            origin = safety.routing_origin(args.routing_origin or "")
            inputs = candidate = None
        else:
            manifest, inputs, candidate = prepared(root, workspace, agent, folder)
            origin = manifest["routingOrigin"]
        client = safety.Client(workspace, agent, origin, root)
        if args.phase == "prepare":
            result = prepare(client, root, folder)
        elif args.phase == "apply":
            result = apply(client, root, folder, inputs, candidate)
        elif args.phase == "publish":
            result = publish(client, root, folder, inputs, candidate)
        else:
            result = verify(client, root, candidate, folder, args.stage)
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (ValueError, OSError, KeyError, TypeError) as error:
        print("Stopped: " + str(error), file=sys.stderr)
        return 2
    finally:
        if client is not None:
            client.close()


if __name__ == "__main__":
    raise SystemExit(main())
