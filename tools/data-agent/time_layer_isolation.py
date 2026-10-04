"""Isolate temporal roles and source-scoped enums in an existing native Agent."""

from __future__ import annotations

import copy
import json
from pathlib import Path
import uuid

from source_grounded_profile import decoded_parts, inline_part

PROFILE = Path(__file__).resolve().parents[2] / "workshop/v3.0.0-preview/data-agent/candidates/time-layer-isolation"
TYPES = {"lakehouse_tables", "semantic_model", "kusto", "ontology"}
PROVENANCE_LITERAL = "StaticSyntheticSnapshot"
MODEL_STATIC = "KEEPFILTERS('寄附'[データソース] = \"StaticSeed\")"
MODEL_INCREMENT = "KEEPFILTERS('寄附'[データソース] = \"RealtimeIncrement\")"


def _replace_once(text: str, old: str, new: str) -> str:
    if text.count(old) != 1:
        raise ValueError("Expected context is missing or ambiguous; reconcile the base profile.")
    return text.replace(old, new, 1)


def compile_isolated_draft(original: dict, profile: Path = PROFILE) -> tuple[dict, dict]:
    documents = decoded_parts(original)
    stage_path = "Files/Config/published/stage_config.json"
    if stage_path not in documents or "Files/Config/data_agent.json" not in documents:
        raise ValueError("A complete published Agent is required.")
    sources = {documents[p]["type"]: p for p in documents
               if p.startswith("Files/Config/published/") and p.endswith("/datasource.json")}
    if set(sources) != TYPES or sum(p.endswith("/datasource.json") and "/published/" in p for p in documents) != 4:
        raise ValueError("Exactly the existing four direct sources are required.")
    wanted = {p: copy.deepcopy(v) for p, v in documents.items() if "/draft/" not in p}
    for path, value in documents.items():
        if path.startswith("Files/Config/published/"):
            wanted[path.replace("/published/", "/draft/", 1)] = copy.deepcopy(value)
    draft_stage = wanted[stage_path.replace("/published/", "/draft/")]
    text = draft_stage["aiInstructions"]
    tag_lines = [line for line in text.splitlines() if PROVENANCE_LITERAL in line]
    if len(tag_lines) != 1:
        raise ValueError("Expected one coordinator provenance clause; do not remove unrelated instructions.")
    text = _replace_once(text, tag_lines[0], (
        "「No data found」だけで対象なしと結論しない。カテゴリ・支払方法の実際のDISTINCT値を確認し、"
        "無指定の日付・未選択列・他ソースの条件を足していないかを点検する。"
        "ユーザーの条件は緩めず、正しい選択済み列と値で得たCOUNT=0だけを真の0として示す。"
    ))
    text = _replace_once(text, (
        "生観測の配布月はUTCを既定とする。JST/日本時間の日が指定された時だけUTCの半開区間に換算する。"
        "Goldの明示日付はモデルの日付dimension（JST）。"
    ), "生観測の期間と表示は冒頭のFilterTimezone/DisplayTimezone契約に従う。モデルの日付規則はGoldソースの指示だけに適用する。")
    text = (profile / "time-layer-contract.txt").read_text(encoding="utf-8").strip() + "\n\n" + text
    if not 0 < len(text) <= 10000:
        raise ValueError("Global instructions exceed the native supported range.")
    draft_stage["aiInstructions"] = text
    paths = {kind: path.replace("/published/", "/draft/", 1) for kind, path in sources.items()}
    sql = wanted[paths["lakehouse_tables"]]
    sql_lines = sql["dataSourceInstructions"].splitlines()
    if sum(PROVENANCE_LITERAL in line for line in sql_lines) != 1:
        raise ValueError("Expected one SQL provenance rule.")
    sql["dataSourceInstructions"] = "\n".join(
        "This source is physically scoped to static seed. The fixed provenance-tag column is not selected: "
        "do not add a provenance/layer predicate or borrow a model DataSource value."
        if PROVENANCE_LITERAL in line else line for line in sql_lines
    )
    ontology = wanted[paths["ontology"]]
    ontology_lines = ontology["dataSourceInstructions"].splitlines()
    if sum(PROVENANCE_LITERAL in line for line in ontology_lines) != 1:
        raise ValueError("Expected one Ontology provenance rule.")
    ontology["dataSourceInstructions"] = "\n".join(
        '"2025年seed" means the whole static snapshot, not a calendar predicate. '
        "Use selected business keys and names; a source-owned stored key must be read, not invented."
        if PROVENANCE_LITERAL in line else line for line in ontology_lines
    )
    wanted[paths["kusto"]]["dataSourceInstructions"] = (
        (profile / "kusto-time-contract.txt").read_text(encoding="utf-8").strip()
        + "\n\n" + wanted[paths["kusto"]]["dataSourceInstructions"]
    )
    model = wanted[paths["semantic_model"]]
    if MODEL_STATIC not in model["dataSourceInstructions"] or MODEL_INCREMENT not in model["dataSourceInstructions"]:
        raise ValueError("The existing source-owned measure definitions differ.")
    model["dataSourceInstructions"] = (
        "MODEL-ONLY NAMESPACE: the column '寄附'[データソース] contains exactly StaticSeed and RealtimeIncrement. "
        "Static-measure inner filters use the literal StaticSeed; increment-measure inner filters use RealtimeIncrement. "
        "Do not import a Lakehouse/Ontology provenance tag into this column. Explain outer and inner values using "
        "the actual four definitions below, not a translated guess. Model JST-date conventions apply only to this "
        "model and never to Kusto UTC requests.\n\n" + model["dataSourceInstructions"]
    )
    deselected, descriptions = [], []

    def walk(items, names=()):
        for node in items:
            path = names + (node.get("display_name", node.get("type", "?")),)
            if node.get("type") == "lakehouse_tables.column" and node.get("display_name") == "DonationDataLayer":
                if node.get("is_selected"):
                    deselected.append(list(path))
                node["is_selected"] = False
            if isinstance(node.get("description"), str) and PROVENANCE_LITERAL in node["description"]:
                node["description"] = "Static-source provenance metadata; not a selected business filter or a semantic-model DataSource value."
                descriptions.append(list(path))
            walk(node.get("children", []), path)

    walk(sql["elements"])
    expected = ["Schemas", "dbo", "Views", "agent_donation_detail", "DonationDataLayer"]
    if deselected != [expected]:
        raise ValueError("Only the known static detail provenance column may be deselected.")
    override = json.loads((profile / "example-overrides.json").read_bytes())
    replacements, additions = override["replacements"], override["additions"]
    changes = []
    for row in replacements + additions:
        kind = row["sourceType"]
        if kind not in {"lakehouse_tables", "kusto"} or not row["question"].strip() or not row["query"].strip():
            raise ValueError("Only nonempty SQL/KQL example overrides are supported.")
        bundle_path = paths[kind].removesuffix("datasource.json") + "fewshots.json"
        rows = wanted[bundle_path]["fewShots"]
        generated = {"id": str(uuid.uuid5(uuid.NAMESPACE_URL, "furusato-time-layer:" + row["question"])),
                     "question": row["question"], "query": row["query"]}
        if row in replacements:
            match_fields = [(key[5:].lower(), value) for key, value in row.items() if key.startswith("match")]
            if len(match_fields) != 1 or match_fields[0][0] not in {"query", "question"}:
                raise ValueError("Each replacement needs one exact query/question match.")
            field, value = match_fields[0]
            matches = [i for i, item in enumerate(rows) if item[field] == value]
            if len(matches) != 1:
                raise ValueError("An existing example is missing or ambiguous.")
            rows[matches[0]] = generated
        else:
            if any(item["question"] == row["question"] for item in rows):
                raise ValueError("An additional example already exists.")
            rows.append(generated)
        changes.append({"sourceType": kind, "question": row["question"], "query": row["query"]})
    if any(PROVENANCE_LITERAL in json.dumps(value, ensure_ascii=False)
           for path, value in wanted.items() if path.startswith("Files/Config/draft/")):
        raise ValueError("The source-specific provenance literal still leaks into Draft context.")
    return {"parts": [inline_part(path, value) for path, value in wanted.items()]}, {
        "sourceIdentitiesPreserved": True, "baseDataAndModelMeasuresChanged": False,
        "publishedPartsPreserved": True, "runtimeSwitchesPreserved": True,
        "deselectedSqlColumns": deselected, "sanitizedDescriptions": descriptions,
        "globalInstructionsCharacters": len(text), "changedExamples": changes,
        "exampleCounts": {
            kind: len(wanted[path.removesuffix("datasource.json") + "fewshots.json"]["fewShots"])
            for kind, path in paths.items() if kind in {"lakehouse_tables", "kusto"}
        }, "cloudCalls": 0,
    }
