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
        "Complete static snapshot DATA, including every catalog supplier, registered dimension, ranking and stored metric business key. Use this source for the data part of relationship questions; Ontology supplies edge declarations separately.",
    ),
    "kusto": (
        "kusto-instructions.txt",
        "Raw duplicate-inclusive operational observations. Five-field bucket grain without donors or EventID. Recorded publication is synthetic CSV metadata, not actual ingestion or processing telemetry.",
    ),
    "semantic_model": (
        "semantic-model-instructions.txt",
        "Source-owned Gold measures and their exact filter semantics. StaticSeed/RealtimeIncrement same-column KEEPFILTERS intersection, independent prior-period dates and genuine BLANK results.",
    ),
    "ontology": (
        "ontology-instructions.txt",
        "Declared STATIC compatibility relationship schema and traversal directions. For mixed data/path questions obtain complete values and business keys from Lakehouse, then verify edges here. Not a complete transaction-list preview or live operations source.",
    ),
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
