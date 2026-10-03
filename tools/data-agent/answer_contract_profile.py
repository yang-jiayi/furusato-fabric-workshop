"""Compile a complete-answer contract into an existing isolated Agent draft."""

from __future__ import annotations

import copy
import json
from pathlib import Path
import uuid

from source_grounded_profile import decoded_parts, inline_part

PROFILE = Path(__file__).resolve().parents[2] / "workshop/v3.0.0-preview/data-agent/candidates/complete-contract"
SOURCES = {
    "lakehouse_tables": (
        "lakehouse-instructions.txt",
        "PRIMARY source for every ordinary seed/static question, including payment/category rankings and residence-versus-recipient comparisons. Complete static facts, registered counts, donation/gift/catalog identities and stored metric keys. Get complete data here even when relationships are also requested; Ontology supplies declarations.",
    ),
    "kusto": (
        "kusto-instructions.txt",
        "Raw duplicate-inclusive operational observations. Five-field bucket grain without donors or EventID. Recorded publication is synthetic CSV metadata, not actual ingestion or processing telemetry.",
    ),
    "semantic_model": (
        "semantic-model-instructions.txt",
        "ONLY for explicitly requested Gold, quality-processed analytical results, Power BI or an explicitly named model measure. Do not route ordinary seed payment/category/count/amount questions here; they use Lakehouse SQL. StaticSeed/RealtimeIncrement same-column KEEPFILTERS, independently shifted periods and BLANK retain their model meaning.",
    ),
    "ontology": (
        "ontology-instructions.txt",
        "Declared STATIC compatibility relationship schema and traversal directions only. Mixed data/path questions obtain complete values, names, prefectures and business keys from Lakehouse first. Do not substitute graph previews for complete donation/catalog data or render an ID-only graph result as the final business answer.",
    ),
}
SCHEMA_VIEWS = {
    "agent_relationship_dictionary": "Exact declared relationship names and source/target entity types mirrored from the verified static Ontology definition. These are declared arrows, not SQL foreign-key dependency directions. Refresh only after rechecking the source Ontology.",
    "agent_prefecture_category_metric": "One existing stored recipient-prefecture/category metric. The actual PrefCategoryMetricId, names, count and yen are joined to the two source-declared relationship names and directions. Never infer or reverse those declared directions from foreign keys.",
}


def query_examples(profile: Path = PROFILE) -> list[dict[str, str]]:
    rows = json.loads((profile / "examples.json").read_bytes())["examples"]
    seen = set()
    for row in rows:
        if set(row) != {"sourceType", "question", "query"} or row["sourceType"] not in {"lakehouse_tables", "kusto"}:
            raise ValueError("Only explicit SQL/KQL example entries are supported.")
        if not row["question"].strip() or not row["query"].strip() or row["question"] in seen:
            raise ValueError("Examples must have nonempty unique questions and queries.")
        seen.add(row["question"])
    if {row["sourceType"] for row in rows} != {"lakehouse_tables", "kusto"}:
        raise ValueError("Both source example bundles must be supplied.")
    return rows


def compile_contract_draft(original: dict, profile: Path = PROFILE) -> tuple[dict, dict]:
    before = decoded_parts(original)
    stage_path = "Files/Config/published/stage_config.json"
    if stage_path not in before or "Files/Config/data_agent.json" not in before:
        raise ValueError("A complete published definition is required.")
    source_paths = [path for path in before if path.startswith("Files/Config/published/")
                    and path.endswith("/datasource.json")]
    if len(source_paths) != len(SOURCES) or {before[path]["type"] for path in source_paths} != set(SOURCES):
        raise ValueError("Exactly the four existing sources are required.")
    wanted = {path: copy.deepcopy(value) for path, value in before.items()
              if not path.startswith("Files/Config/draft/")}
    for path, value in before.items():
        if path.startswith("Files/Config/published/"):
            wanted[path.replace("/published/", "/draft/", 1)] = copy.deepcopy(value)
    text = (profile / "global-instructions.txt").read_text(encoding="utf-8").strip()
    if not 0 < len(text) <= 10000:
        raise ValueError("Global instruction length is outside the supported range.")
    wanted[stage_path.replace("/published/", "/draft/")]["aiInstructions"] = text
    descriptions = json.loads((profile / "schema-descriptions.json").read_bytes())
    matches = {key: 0 for key in descriptions}
    examples = query_examples(profile)

    def describe(items, object_name=None):
        for node in items:
            kind = node.get("type")
            name = node.get("display_name")
            table = name if kind in {"lakehouse_tables.table", "lakehouse_tables.view"} else object_name
            key = f"{table}.{name}"
            if kind == "lakehouse_tables.column" and key in descriptions:
                if not node.get("is_selected"):
                    raise ValueError(f"Cannot describe an unselected contract column: {key}")
                node["description"] = descriptions[key]
                matches[key] += 1
            describe(node.get("children", []), table)

    counts = {}
    for published_path in source_paths:
        path = published_path.replace("/published/", "/draft/", 1)
        source = wanted[path]
        kind = source["type"]
        filename, description = SOURCES[kind]
        source["dataSourceInstructions"] = (profile / filename).read_text(encoding="utf-8").strip()
        source["userDescription"] = description
        if kind == "lakehouse_tables":
            describe(source["elements"])
        rows = [row for row in examples if row["sourceType"] == kind]
        if rows:
            wanted[path.removesuffix("datasource.json") + "fewshots.json"] = {
                "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/dataAgent/definition/fewShots/1.0.0/schema.json",
                "fewShots": [{"id": str(uuid.uuid5(uuid.NAMESPACE_URL, "furusato-complete-contract:" + row["question"])),
                             "question": row["question"], "query": row["query"]} for row in rows],
            }
        counts[kind] = len(rows)
    if any(count != 1 for count in matches.values()):
        raise ValueError("Every described column must exist exactly once in the native selected schema.")
    return {"parts": [inline_part(path, value) for path, value in wanted.items()]}, {
        "globalInstructionsCharacters": len(text), "exampleCounts": counts,
        "describedColumns": sorted(descriptions), "sourceIdentitiesAndSelectionsPreserved": True,
        "publishedPartsPreserved": True, "runtimeSwitchesPreserved": True, "cloudCalls": 0,
    }


def compile_schema_grounded_draft(original: dict, columns: list[dict], profile: Path = PROFILE) -> tuple[dict, dict]:
    """Admit only service-discovered schema views with independently checked SQL types."""
    compiled, receipt = compile_contract_draft(original, profile)
    wanted, before = decoded_parts(compiled), decoded_parts(original)
    paths = [p for p, value in wanted.items() if "/draft/" in p
             and p.endswith("/datasource.json") and value["type"] == "lakehouse_tables"]
    if len(paths) != 1 or {row["TABLE_NAME"] for row in columns} != set(SCHEMA_VIEWS):
        raise ValueError("Exactly the two verified grounding view schemas are required.")
    path = paths[0]

    def walk(items):
        for node in items:
            yield node
            yield from walk(node.get("children", []))

    actual = [node for node in walk(before[path]["elements"])
              if node.get("type") == "lakehouse_tables.view" and node.get("display_name") in SCHEMA_VIEWS]
    if len(actual) != 2 or {n["display_name"] for n in actual} != set(SCHEMA_VIEWS):
        raise ValueError("Native Draft view identities are missing or ambiguous.")
    schemas = [node for node in walk(wanted[path]["elements"])
               if node.get("type") == "lakehouse_tables.schema" and node.get("display_name") == "dbo"]
    if len(schemas) != 1:
        raise ValueError("The existing dbo schema must be unique.")
    groups = [n for n in schemas[0]["children"] if n.get("type") == "view_grouping"]
    if len(groups) != 1:
        raise ValueError("Preserve the native grouped Views hierarchy.")
    for native in actual:
        name = native["display_name"]
        expected = {r["COLUMN_NAME"]: r["DATA_TYPE"] for r in columns if r["TABLE_NAME"] == name}
        observed = {n["display_name"]: n["data_type"] for n in native.get("children", [])}
        if not expected or observed != expected or len(observed) != len(native["children"]):
            raise ValueError("Native grounding-view columns differ from verified SQL metadata.")
        existing = [n for n in groups[0]["children"] if n.get("display_name") == name]
        if len(existing) > 1 or (existing and existing[0]["id"] != native["id"]):
            raise ValueError("A grounding view has conflicting native identities.")
        view = copy.deepcopy(native)
        view["description"] = SCHEMA_VIEWS[name]
        for node in walk([view]):
            node["is_selected"] = True
        if existing:
            groups[0]["children"][groups[0]["children"].index(existing[0])] = view
        else:
            groups[0]["children"].append(view)
    retired = [node for node in walk(schemas[0]["children"])
               if node.get("type") == "lakehouse_tables.table" and node.get("display_name") == "ot_pref_category_metric"]
    if len(retired) != 1:
        raise ValueError("The overlapping base metric must be uniquely identified.")
    for node in walk(retired):
        node["is_selected"] = False
    for node in schemas[0]["children"]:
        if node.get("type") in {"table_grouping", "view_grouping"}:
            node["is_selected"] = any(c.get("is_selected") for c in node.get("children", []))
    wanted[path]["userDescription"] += (
        " Also query agent_relationship_dictionary for exact source-declared arrows and "
        "agent_prefecture_category_metric for existing metric keys plus both declared edges; "
        "do not infer relation direction from foreign-key layout."
    )
    published_path = path.replace("/draft/", "/published/")
    published_nodes = list(walk(before[published_path]["elements"]))
    selection_map = lambda items: {n["id"]: n.get("is_selected") for n in walk(items) if "id" in n}
    added = [name for name in SCHEMA_VIEWS if not any(
        n.get("type") == "lakehouse_tables.view" and n.get("display_name") == name and n.get("is_selected")
        for n in published_nodes)]
    retired_names = ["ot_pref_category_metric"] if any(
        n.get("type") == "lakehouse_tables.table" and n.get("display_name") == "ot_pref_category_metric"
        and n.get("is_selected") for n in published_nodes) else []
    receipt.update(sourceIdentitiesAndSelectionsPreserved=(
                       selection_map(before[published_path]["elements"]) == selection_map(wanted[path]["elements"])),
                   sourceIdentitiesPreserved=True, addedViewSelections=sorted(added),
                   retiredTableSelections=retired_names, groundingViewsVerified=sorted(SCHEMA_VIEWS),
                   serviceOwnedViewIdsPreserved=True)
    return {"parts": [inline_part(p, v) for p, v in wanted.items()]}, receipt
