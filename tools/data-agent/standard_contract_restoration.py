"""Restore the standard workshop answer contracts on top of the time-layer profile.

The 2026-10-07 evaluation showed that the corrected profile chain replaced the
original unified instructions and lost several standard-question contracts:
the operational year for a year-less "August", composite source routing,
both prefecture readings, popularity on both metrics, Ontology membership
COUNT, donation-trace completeness, file/run headers, the incompatible-addition
refusal and numeric/DAX explanation fidelity. This overlay adds them as the
highest-priority sections without changing source identities, selections,
runtime switches, published parts, base data or model measures.

It makes no cloud calls and contains no benchmark answer values.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
import uuid

from source_grounded_profile import decoded_parts, inline_part

PROFILE = Path(__file__).resolve().parents[2] / "workshop/v3.0.0-preview/data-agent/candidates/standard-contract-restoration"
TYPES = {"lakehouse_tables", "semantic_model", "kusto", "ontology"}
# Documented Fabric data agent instruction limit. The earlier time-layer stage
# keeps its own conservative 10,000-character check on its input.
GLOBAL_LIMIT = 15000
CONTRACT_MARKER = "## 最優先: 口語の対象・期間・ソースを先に確定する（標準ワークショップ契約）"
SOURCE_CONTRACTS = {
    "kusto": "kusto-contract.txt",
    "lakehouse_tables": "lakehouse-contract.txt",
    "ontology": "ontology-contract.txt",
    "semantic_model": "semantic-model-contract.txt",
}
GLOBAL_REPLACEMENTS = (
    (
        "全登録自治体数をCOUNT(DISTINCT MunicipalityId)で取得するか、単一県のRegisteredMunicipalitiesInPrefectureを一度読む。",
        "「名簿」「seed」「Lakehouse」と明示された登録自治体数は、COUNT(DISTINCT MunicipalityId)で取得するか、"
        "単一県のRegisteredMunicipalitiesInPrefectureを一度読む。県に属する・ぶら下がる自治体の数は冒頭の契約どおりOntologyで数える。",
    ),
    (
        "ファイルごとの質問: SourceFile | ObservationCount | ObservedAmountYen | FirstObservedAtUtc | LastObservedAtUtc | SyntheticCsvPublishedAtUtc。",
        "ファイルごとの質問: SourceFile | WorkshopRunId | ParticipantAlias | ObservationCount | ObservedAmountYen | "
        "FirstObservedAtUtc | LastObservedAtUtc。配信時刻を問われた時だけSyntheticCsvPublishedAtUtcを加える。",
    ),
)
# Public standard ten/84 expected values. The overlay must teach contracts, not answers.
ANSWER_VALUE_GUARD = (
    "80,000", "1,344,099,000", "1344099000", "452025", "1,813", "41,151,000", "272132",
    "2,661", "45,930,000", "8,784", "146,543,000", "5000001", "2008242", "222097", "3002512",
    "4000341", "85,098,000", "84,687,000", "84,101,000", "253,886,000", "253886000",
    "increment-run-00", "2026-08-01T00:02:47Z", "2026-08-31T23:58:20Z", "14,900", "14900",
    "5,737,000", "藤田", "島田市", "熱海商店", "都城市", "泉佐野市", "95,000", "95000",
)


def _replace_once(text: str, old: str, new: str) -> str:
    if text.count(old) != 1:
        raise ValueError("Expected base instruction context is missing or ambiguous; reconcile the base profile.")
    return text.replace(old, new, 1)


def _walk(nodes, names=()):
    for node in nodes:
        path = names + (node.get("display_name", node.get("type", "?")),)
        yield path, node
        yield from _walk(node.get("children", []), path)


def overlay_inputs(profile: Path = PROFILE) -> dict[str, str]:
    """Return every overlay input as text after the answer-value guard."""
    inputs = {path.name: path.read_text(encoding="utf-8") for path in sorted(profile.iterdir())
              if path.suffix in {".txt", ".json"}}
    for name, text in inputs.items():
        leaked = [value for value in ANSWER_VALUE_GUARD if value in text]
        if leaked:
            raise ValueError(f"{name} embeds benchmark answer values: {leaked}")
    return inputs


def compile_restored_draft(original: dict, profile: Path = PROFILE) -> tuple[dict, dict]:
    """Return the complete definition with only Draft parts changed."""
    overlay_inputs(profile)
    documents = decoded_parts(original)
    stage_path = "Files/Config/draft/stage_config.json"
    if stage_path not in documents or "Files/Config/data_agent.json" not in documents:
        raise ValueError("A complete Draft definition is required.")
    sources = {value["type"]: path for path, value in documents.items()
               if path.startswith("Files/Config/draft/") and path.endswith("/datasource.json")}
    if set(sources) != TYPES or sum(p.startswith("Files/Config/draft/") and p.endswith("/datasource.json")
                                    for p in documents) != 4:
        raise ValueError("Exactly the existing four direct sources are required.")
    wanted = copy.deepcopy(documents)
    stage = wanted[stage_path]
    text = stage["aiInstructions"]
    if CONTRACT_MARKER in text:
        raise ValueError("The standard contract is already present; compile from the time-layer Draft.")
    for old, new in GLOBAL_REPLACEMENTS:
        text = _replace_once(text, old, new)
    contract = (profile / "global-contract.txt").read_text(encoding="utf-8").strip()
    if not contract.startswith(CONTRACT_MARKER):
        raise ValueError("The global contract must start with its marker heading.")
    text = contract + "\n\n" + text
    if not 0 < len(text) <= GLOBAL_LIMIT:
        raise ValueError("Global instructions exceed the documented 15,000-character limit.")
    stage["aiInstructions"] = text
    source_lengths = {}
    for kind, filename in SOURCE_CONTRACTS.items():
        source = wanted[sources[kind]]
        addition = (profile / filename).read_text(encoding="utf-8").strip()
        if addition in (source.get("dataSourceInstructions") or ""):
            raise ValueError("A source contract is already present.")
        source["dataSourceInstructions"] = addition + "\n\n" + (source.get("dataSourceInstructions") or "")
        source_lengths[kind] = len(source["dataSourceInstructions"])
        if source_lengths[kind] > GLOBAL_LIMIT:
            raise ValueError("A data source instruction exceeds the documented limit.")
    overrides = json.loads((profile / "description-overrides.json").read_bytes())
    for kind, description in overrides["userDescriptions"].items():
        if kind not in SOURCE_CONTRACTS or not description.strip():
            raise ValueError("Unsupported source description override.")
        wanted[sources[kind]]["userDescription"] = description
    described = []
    for key, description in overrides["columnDescriptions"].items():
        view_name, column_name = key.split(".")
        hits = [node for path, node in _walk(wanted[sources["lakehouse_tables"]]["elements"])
                if node.get("type") == "lakehouse_tables.column" and node.get("display_name") == column_name
                and len(path) >= 2 and path[-2] == view_name]
        if len(hits) != 1 or not hits[0].get("is_selected"):
            raise ValueError(f"Described column must exist once and be selected: {key}")
        hits[0]["description"] = description
        described.append(key)
    examples = json.loads((profile / "example-changes.json").read_bytes())
    changes = []
    for row in examples["replacements"] + examples["additions"]:
        kind = row["sourceType"]
        if kind not in {"lakehouse_tables", "kusto"} or not row["question"].strip() or not row["query"].strip():
            raise ValueError("Only nonempty SQL/KQL example changes are supported.")
        bundle_path = sources[kind].removesuffix("datasource.json") + "fewshots.json"
        rows = wanted.setdefault(bundle_path, {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/dataAgent/definition/fewShots/1.0.0/schema.json",
            "fewShots": []})["fewShots"]
        generated = {"id": str(uuid.uuid5(uuid.NAMESPACE_URL, "furusato-standard-contract:" + row["question"])),
                     "question": row["question"], "query": row["query"]}
        if row in examples["replacements"]:
            match = [(key[5:].lower(), value) for key, value in row.items() if key.startswith("match")]
            if len(match) != 1 or match[0][0] not in {"question", "query"}:
                raise ValueError("Each replacement needs one exact question/query match.")
            field, value = match[0]
            positions = [i for i, item in enumerate(rows) if item[field] == value]
            if len(positions) != 1:
                raise ValueError("An existing example is missing or ambiguous.")
            rows[positions[0]] = generated
            changes.append({"sourceType": kind, "action": "replace", "question": row["question"]})
        else:
            if any(item["question"] == row["question"] for item in rows):
                raise ValueError("An additional example already exists.")
            rows.append(generated)
            changes.append({"sourceType": kind, "action": "add", "question": row["question"]})
    for path, value in wanted.items():
        if not path.startswith("Files/Config/draft/") or "/published/" in path:
            continue
        if path.startswith("Files/Config/draft/") and path not in documents and not path.endswith("fewshots.json"):
            raise ValueError("Unexpected new Draft part.")
    unchanged = [p for p in documents if not p.startswith("Files/Config/draft/")]
    if any(wanted[p] != documents[p] for p in unchanged):
        raise ValueError("A non-Draft part changed.")
    for kind, path in sources.items():
        for key in ("artifactId", "workspaceId", "displayName", "type"):
            if wanted[path].get(key) != documents[path].get(key):
                raise ValueError("A source identity changed.")
    counts = {kind: len(wanted[sources[kind].removesuffix("datasource.json") + "fewshots.json"]["fewShots"])
              for kind in ("lakehouse_tables", "kusto")}
    return {"parts": [inline_part(path, value) for path, value in wanted.items()]}, {
        "globalInstructionsCharacters": len(text), "globalLimit": GLOBAL_LIMIT,
        "sourceInstructionCharacters": source_lengths, "replacedGlobalClauses": len(GLOBAL_REPLACEMENTS),
        "userDescriptionsOverridden": sorted(overrides["userDescriptions"]), "describedColumns": described,
        "exampleChanges": changes, "exampleCounts": counts,
        "sourceIdentitiesPreserved": True, "selectionsChanged": False, "publishedPartsPreserved": True,
        "baseDataAndModelMeasuresChanged": False, "cloudCalls": 0,
    }
