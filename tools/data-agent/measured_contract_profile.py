"""Compile the measured 2026-10-09 contract from actual workshop metadata.

This pure compiler does not authenticate, query, stage or publish. Native SQL/KQL
selection nodes must already exist in the supplied service definition. Missing
objects require service discovery; their IDs and types are never manufactured.
The caller owns source verification, publication/readback and a new evaluation.
"""
from __future__ import annotations

import argparse
import base64
import copy
import hashlib
import json
from pathlib import Path
import re
import uuid

from source_grounded_profile import decoded_parts, inline_part
from standard_contract_restoration import _answer_values_in

REPO = Path(__file__).resolve().parents[2]
PROFILE = REPO / "workshop/v3.0.0-preview/data-agent/candidates/measured-contract-20261009"
LIMIT = 10000
KINDS = {"lakehouse_tables", "kusto", "semantic_model", "ontology"}
FILES = {"lakehouse_tables": "lakehouse-instructions.txt", "kusto": "kusto-instructions.txt",
         "semantic_model": "semantic-model-instructions.txt", "ontology": "ontology-instructions.txt"}
MEASURES = {
    "寄附件数": "COUNTROWS('寄附')",
    "寄附総額": "SUM('寄附'[寄附金額])",
    "静的寄附件数": 'CALCULATE([寄附件数], KEEPFILTERS(\'寄附\'[データソース] = "StaticSeed"))',
    "静的寄附総額": 'CALCULATE([寄附総額], KEEPFILTERS(\'寄附\'[データソース] = "StaticSeed"))',
    "受入増分寄附件数": 'CALCULATE([寄附件数], KEEPFILTERS(\'寄附\'[データソース] = "RealtimeIncrement"))',
    "受入増分寄附総額": 'CALCULATE([寄附総額], KEEPFILTERS(\'寄附\'[データソース] = "RealtimeIncrement"))',
    "平均寄附額": "DIVIDE([寄附総額], [寄附件数])",
    "寄附総額 前年同期間": "CALCULATE([寄附総額], SAMEPERIODLASTYEAR('日付'[日付]))",
    "自治体別シェア (%)": "DIVIDE([寄附総額], CALCULATE([寄附総額], REMOVEFILTERS('自治体')))",
    "高額寄附件数": "CALCULATE([寄附件数], KEEPFILTERS('寄附'[高額寄附フラグ] = TRUE()))",
}
FEWSHOT_SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item/dataAgent/definition/fewShots/1.0.0/schema.json"


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(",", ":")).encode()).hexdigest()


def walk(nodes, path=()):
    if not isinstance(nodes, list):
        raise ValueError("Native element children must be arrays.")
    for node in nodes:
        if not isinstance(node, dict) or not isinstance(node.get("display_name"), str):
            raise ValueError("Native elements require their observed display_name.")
        current = path + (node["display_name"],)
        yield current, node
        yield from walk(node.get("children", []), current)


def profile_inputs(profile=PROFILE):
    manifest = json.loads((profile / "profile-manifest.json").read_bytes())
    if manifest.get("schemaVersion") != 1 or manifest.get("instructionLimitUtf16Units") != LIMIT:
        raise ValueError("Unknown measured-contract manifest.")
    expected = {"global-instructions.txt", *FILES.values(), "source-descriptions.json",
                "selection-contract.json", "kusto-examples.json"}
    if set(manifest.get("sha256", {})) != expected:
        raise ValueError("The manifest must bind every compiler input.")
    for name, expected_hash in manifest["sha256"].items():
        raw = (profile / name).read_bytes()
        if hashlib.sha256(raw).hexdigest() != expected_hash:
            raise ValueError("Measured-contract input drift: " + name)
        text = raw.decode("utf-8")
        # Inspect decoded values so JSON Unicode escapes cannot hide a case ID,
        # benchmark value or live identity from the publication guard.
        if name.endswith(".json"):
            text = json.dumps(json.loads(text), ensure_ascii=False)
        if _answer_values_in(text) or re.search(r"\b[TBHQ][0-9]{2}\b|[0-9a-f]{8}-[0-9a-f-]{27,}", text, re.I):
            raise ValueError("Profile assets must not contain benchmark answers, case IDs or live identities.")
    instructions = {"global": (profile / "global-instructions.txt").read_text(encoding="utf-8").strip()}
    instructions.update({kind: (profile / name).read_text(encoding="utf-8").strip()
                         for kind, name in FILES.items()})
    if any(not text or len(text.encode("utf-16-le")) // 2 > LIMIT for text in instructions.values()):
        raise ValueError("Every instruction section must fit 10,000 UTF16 units.")
    descriptions = json.loads((profile / "source-descriptions.json").read_bytes())
    selections = json.loads((profile / "selection-contract.json").read_bytes())
    examples = json.loads((profile / "kusto-examples.json").read_bytes())["examples"]
    if (set(descriptions) != KINDS or not all(isinstance(v, str) and v.strip() for v in descriptions.values())
            or selections.get("schemaVersion") != 1):
        raise ValueError("Invalid source description/selection contract.")
    if set(selections.get("sources", {})) != {"lakehouse_tables", "kusto"}:
        raise ValueError("Only SQL/KQL selections may be aligned.")
    if len(examples) != 9 or len({row.get("question") for row in examples}) != 9:
        raise ValueError("Exactly nine distinct source-owned KQL examples are required.")
    for row in examples:
        if set(row) != {"question", "query"} or not all(isinstance(v, str) and v.strip() for v in row.values()):
            raise ValueError("Malformed KQL example.")
    return instructions, descriptions, selections["sources"], examples, manifest


def source_model_contract(native_model):
    """Read every existing workshop measure and the visible amount column."""
    model = native_model.get("definition", native_model)
    if model.get("format") != "TMDL" or not isinstance(model.get("parts"), list):
        raise ValueError("Actual Semantic Model TMDL readback is required.")
    found, amount, paths = {}, [], set()
    for part in model["parts"]:
        path = part.get("path")
        if not isinstance(path, str) or path in paths or part.get("payloadType") != "InlineBase64":
            raise ValueError("TMDL requires unique paths and actual InlineBase64 payloads.")
        paths.add(path)
        text = base64.b64decode(part["payload"], validate=True).decode("utf-8")
        if not path.startswith("definition/tables/") or not path.endswith(".tmdl"):
            continue
        for name, expected in MEASURES.items():
            for match in re.finditer(r"^\tmeasure '?" + re.escape(name) + r"'? = (.+)$", text, re.M):
                if name in found or match.group(1).strip() != expected:
                    raise ValueError("Source-owned workshop measure differs or is duplicated: " + name)
                found[name] = match.group(1).strip()
        if re.search(r"^table '?寄附'?\s*$", text, re.M):
            amount.extend(re.findall(r"^\tcolumn '?寄附金額'?\s*\n((?:\t\t[^\n]*\n|\s*\n)*)", text, re.M))
    if found != MEASURES or len(amount) != 1:
        raise ValueError("All ten unique existing measures and the actual donation amount column are required.")
    if re.search(r"^\t\tisHidden(?:\s*:\s*true)?\s*$", amount[0], re.M):
        raise ValueError("The measured contract requires 寄附金額 to be visible in the actual model.")
    return found


def sql_metadata(rows):
    if not isinstance(rows, list) or not rows:
        raise ValueError("Independent INFORMATION_SCHEMA.COLUMNS results are required.")
    columns = {}
    for row in rows:
        keys = ("TABLE_SCHEMA", "TABLE_NAME", "COLUMN_NAME", "DATA_TYPE")
        if not isinstance(row, dict) or not all(isinstance(row.get(k), str) and row[k] for k in keys):
            raise ValueError("SQL metadata requires schema, object, column and native type.")
        key = tuple(row[k] for k in keys[:3])
        if key in columns:
            raise ValueError("Duplicate independent SQL metadata column.")
        columns[key] = row["DATA_TYPE"]
    return columns


def verify_ontology_item(item, source):
    """Verify actual generation evidence without relabeling a public item.

    The measured service lists Gen2 items as public type ``Ontology``. Its actual
    native metadata identifies FeatureLevel=2 and the two managed child roles.
    A plain public Ontology row alone cannot establish that generation.
    """
    if item.get("type") == "Gen2Ontology":
        if item.get("id") != source["artifactId"] or ("workspaceId" in item and item["workspaceId"] != source["workspaceId"]):
            raise ValueError("Generation-specific Ontology metadata is bound to a different source.")
        return
    properties = item.get("extendedProperties", {})
    if (item.get("objectId") != source["artifactId"] or item.get("artifactType") != "Ontology"
            or not isinstance(properties, dict) or properties.get("FeatureLevel") != 2):
        raise ValueError("Actual bound Ontology generation-2 feature-level metadata is required; a public Ontology label alone is insufficient.")
    children = properties.get("ChildItems")
    if not isinstance(children, str):
        raise ValueError("Actual Gen2 managed child metadata is missing.")
    children = json.loads(children)
    if not isinstance(children, dict) or set(children) != {"GraphInstance", "OntologyEventhouse"}:
        raise ValueError("Unknown Gen2 managed child roles.")
    if not all(isinstance(value, str) and str(uuid.UUID(value)) == value.lower() for value in children.values()):
        raise ValueError("Gen2 managed child identities must be real GUIDs.")


def align_selection(source, contract, sql_columns=None):
    """Align only observed native nodes, checking IDs, paths and source types."""
    current = list(walk(source["elements"]))
    nodes = {}
    for path, node in current:
        identity = node.get("id")
        if path in nodes or not isinstance(identity, str) or not identity:
            raise ValueError("Ambiguous native element path or missing observed ID.")
        nodes[path] = node
    expected = {}
    selected_ids = set()
    for item in contract:
        path = tuple(item["path"])
        if path in expected or path not in nodes:
            raise ValueError("Required object is missing/ambiguous; refresh native service schema: " + "/".join(path))
        node = nodes[path]
        # Native exports can reuse a grouping ID across different node kinds.
        # The admitted objects/columns still require unique kind/ID identities.
        identity = (node.get("type"), node["id"])
        if identity in selected_ids:
            raise ValueError("Duplicate observed selected element kind/ID.")
        selected_ids.add(identity)
        if node.get("type") != item["type"] or ("dataType" in item and node.get("data_type") != item["dataType"]):
            raise ValueError("Native element kind/type differs from measured contract: " + "/".join(path))
        if item["type"] == "lakehouse_tables.column":
            key = (path[1], path[-2], path[-1])
            if sql_columns.get(key) != node.get("data_type"):
                raise ValueError("Native SQL column differs from independent metadata: " + ".".join(key))
        expected[path] = item
    changed = []
    for path, node in current:
        selected = path in expected
        if node.get("is_selected") is not selected:
            changed.append({"path": list(path), "selected": selected})
        node["is_selected"] = selected
        if selected and "description" in expected[path]:
            node["description"] = expected[path]["description"]
    return changed


def compile_measured_draft(original, *, input_stage, sql_columns, native_model, ontology_item, profile=PROFILE):
    """Return Draft plus unchanged Published parts; no external side effects."""
    if input_stage not in {"draft", "published"}:
        raise ValueError("Choose the actual input stage explicitly.")
    docs = decoded_parts(original)
    prefix = "Files/Config/" + input_stage + "/"
    stage_path = prefix + "stage_config.json"
    entries = [(p, v) for p, v in docs.items() if p.startswith(prefix) and p.endswith("/datasource.json")]
    sources = {v.get("type"): (p, v) for p, v in entries}
    if stage_path not in docs or "Files/Config/data_agent.json" not in docs or len(entries) != 4 or set(sources) != KINDS:
        raise ValueError("A complete actual stage with exactly four direct sources is required.")
    workspaces, artifacts = set(), set()
    for _, source in entries:
        for key in ("workspaceId", "artifactId"):
            value = source.get(key)
            if not isinstance(value, str) or str(uuid.UUID(value)) != value.lower():
                raise ValueError("Real source workspace/item GUIDs are required.")
        workspaces.add(source["workspaceId"])
        artifacts.add(source["artifactId"])
    if len(workspaces) != 1 or len(artifacts) != 4:
        raise ValueError("Four distinct workshop sources in the same actual workspace are required.")
    ontology = sources["ontology"][1]
    verify_ontology_item(ontology_item, ontology)
    if docs[stage_path].get("experimental", {}).get("codeInterpreterEnabled") is not True:
        raise ValueError("Enable Code Interpreter in the actual stage before compiling this contract.")
    allowed_paths = {stage_path, *(p for p, _ in entries), *(p.removesuffix("datasource.json") + "fewshots.json"
                    for kind, (p, _) in sources.items() if kind in {"lakehouse_tables", "kusto"})}
    if any(p.startswith(prefix) and p not in allowed_paths for p in docs):
        raise ValueError("Extra stage topics/examples require explicit reconciliation before using this profile.")
    source_model_contract(native_model)
    model_nodes = list(walk(sources["semantic_model"][1].get("elements", [])))
    for name in ("寄附金額", *MEASURES):
        matches = [n for path, n in model_nodes if len(path) >= 2 and path[-2:] == ("寄附", name)]
        kind = "semantic_model.column" if name == "寄附金額" else "semantic_model.measure"
        if (len(matches) != 1 or matches[0].get("is_selected") is not True or matches[0].get("type") != kind
                or not isinstance(matches[0].get("id"), str) or not matches[0]["id"]):
            raise ValueError("The actual native model amount/all ten measures must be selected with observed IDs/kinds: " + name)
    instructions, descriptions, selections, examples, manifest = profile_inputs(profile)
    wanted = copy.deepcopy(docs)
    # Derive Draft exclusively from the explicitly selected input stage. Published
    # payloads, agent identity and service metadata in the input remain untouched.
    for path in list(wanted):
        if path.startswith("Files/Config/draft/"):
            del wanted[path]
    for path, value in docs.items():
        if path.startswith(prefix):
            wanted[path.replace(prefix, "Files/Config/draft/", 1)] = copy.deepcopy(value)
    draft_stage = "Files/Config/draft/stage_config.json"
    wanted[draft_stage]["aiInstructions"] = instructions["global"]
    selection_changes = {}
    metadata = sql_metadata(sql_columns)
    for kind, (path, source) in sources.items():
        draft_path = path.replace(prefix, "Files/Config/draft/", 1)
        target = wanted[draft_path]
        target["dataSourceInstructions"] = instructions[kind]
        target["userDescription"] = descriptions[kind]
        if kind in selections:
            selection_changes[kind] = align_selection(target, selections[kind], metadata)
        else:
            if target["elements"] != source["elements"]:
                raise ValueError("Ontology/model selection changed unexpectedly.")
    # The measured native publication excludes the 17 SQL examples whose staging
    # validations failed. Keep them in historical candidate folders, not active
    # fewshots. No source execution success is inferred from these local templates.
    for path in list(wanted):
        if path.startswith("Files/Config/draft/") and path.endswith("/fewshots.json"):
            del wanted[path]
    kusto_path = sources["kusto"][0].replace(prefix, "Files/Config/draft/", 1)
    fewshot_path = kusto_path.removesuffix("datasource.json") + "fewshots.json"
    wanted[fewshot_path] = {"$schema": FEWSHOT_SCHEMA, "fewShots": [
        {"id": str(uuid.uuid5(uuid.NAMESPACE_URL, "furusato-measured-contract:" + row["question"])), **row}
        for row in examples]}
    # Keep every non-Draft part byte-identical, including actual Published evidence.
    parts = [copy.deepcopy(part) for part in original.get("definition", original)["parts"]
             if not part["path"].startswith("Files/Config/draft/")]
    parts.extend(inline_part(path, value) for path, value in sorted(wanted.items())
                 if path.startswith("Files/Config/draft/"))
    result = {"parts": parts}
    before = {p: v for p, v in docs.items() if not p.startswith("Files/Config/draft/")}
    after = {p: v for p, v in decoded_parts(result).items() if not p.startswith("Files/Config/draft/")}
    if before != after:
        raise ValueError("A non-Draft definition part changed.")
    receipt = {
        "profile": "measured-contract-20261009", "inputStage": input_stage,
        "inputDefinitionSha256": digest(original), "outputDefinitionSha256": digest(result),
        "profileManifestSha256": digest(manifest), "inputModelDefinitionSha256": digest(native_model),
        "inputSqlColumnsSha256": digest(sql_columns), "inputOntologyMetadataSha256": digest(ontology_item),
        "instructionUtf16Units": {key: len(text.encode("utf-16-le")) // 2 for key, text in instructions.items()},
        "instructionLimitUtf16Units": LIMIT, "sourceOwnedCountMeasuresVerified": True,
        "sourceOwnedWorkshopMeasuresVerified": 10,
        "modelAmountVisible": True, "sourceIdentitiesPreserved": True, "ontologyCount": 1,
        "ontologyGeneration": 2, "ontologyAndModelSelectionsPreserved": True,
        "sqlKqlSelectionChanges": selection_changes, "codeInterpreterPreserved": True,
        "publishedPartsPreservedByteIdentical": True, "activeSqlExamples": 0, "activeKqlExamples": 9,
        "businessDataAndMeasuresChanged": False, "cloudCalls": 0, "stagedOrPublished": False,
        "freshDeploymentOrAnswerAccuracyVerified": False,
    }
    return result, receipt


def private_path(path):
    if not path.is_absolute() or path.is_symlink():
        raise ValueError("Use absolute private output paths outside Git.")
    resolved = path.resolve()
    if resolved == REPO or REPO in resolved.parents or any((parent / ".git").exists() for parent in resolved.parents):
        raise ValueError("Actual definitions and receipts must remain outside Git checkouts.")
    if path.exists():
        raise ValueError("Use fresh outputs; do not overwrite prior definitions/evidence.")
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--definition", type=Path, required=True)
    parser.add_argument("--input-stage", choices=("draft", "published"), required=True)
    parser.add_argument("--sql-columns", type=Path, required=True)
    parser.add_argument("--model-definition", type=Path, required=True)
    parser.add_argument("--ontology-item", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    out, receipt_path = private_path(args.output), private_path(args.receipt)
    if out.resolve() == receipt_path.resolve():
        raise ValueError("Definition and receipt require different paths.")
    read = lambda path: json.loads(path.read_text(encoding="utf-8-sig"))
    definition, receipt = compile_measured_draft(read(args.definition), input_stage=args.input_stage,
        sql_columns=read(args.sql_columns), native_model=read(args.model_definition), ontology_item=read(args.ontology_item))
    for path, value in ((out, definition), (receipt_path, receipt)):
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with path.open("x", encoding="utf-8") as handle:
            path.chmod(0o600)
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
    print(json.dumps({"status": "local-draft-only", "instructionUtf16Units": receipt["instructionUtf16Units"],
                      "cloudCalls": 0, "stagedOrPublished": False}))


if __name__ == "__main__":
    main()
