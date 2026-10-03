"""Compile an opt-in Data Agent profile without changing source identities."""

from __future__ import annotations

import base64
import copy
import json
from pathlib import Path
import uuid

PROFILE = Path(__file__).resolve().parents[2] / "workshop/v3.0.0-preview/data-agent/candidates/source-grounded"
INSTRUCTIONS = {
    "lakehouse_tables": "lakehouse-instructions.txt",
    "kusto": "kusto-instructions.txt",
    "semantic_model": "semantic-model-instructions.txt",
    "ontology": "ontology-instructions.txt",
}
DESCRIPTIONS = {
    "lakehouse_tables": "Authoritative complete static seed: donation facts, recipient/residence geography, registered dimensions, catalog eligibility and stored pair metrics. Use for static aggregates and registry counts. No operational observations or actual fulfillment/revenue.",
    "kusto": "Authoritative duplicate-inclusive operational observations, not donations or Gold. Query DonationObservationSummaryForAgent; sum its metrics at the requested UTC/JST grouping. No DataSource, EventID, donor, gift or supplier columns.",
    "semantic_model": "Authoritative source-owned DAX on analytical Gold. Preserve StaticSeed/RealtimeIncrement, category, recipient/residence and JST date filters. Gold is not a DataSource value. BLANK and independently shifted prior-period results retain their meanings.",
    "ontology": "Explicit STATIC generation1 compatibility bridge for declared entity paths and directions, not a repair or replacement of the primary generation2 item. Ordinary static aggregates use Lakehouse. Supplier links are catalog eligibility, not actual fulfillment.",
}
VIEW_DESCRIPTIONS = {
    "agent_municipality_snapshot": "One registered municipality, including those with zero donations. Complete static-snapshot DonationCount/AmountYen and resolved names/prefecture. No date filter columns. Repeated RegisteredMunicipalitiesInPrefecture is not additive.",
    "agent_donation_detail": "One static donation per DonationId with all donor/residence, recipient/prefecture and gift/category names. No supplier fan-out. Use for exact IDs, payment/category and explicit JST-date filters.",
    "agent_supplier_catalog": "One unique supplier/gift catalog pair, with type and prefecture. CatalogGiftCount is the whole supplier catalog count, independent of TOP. No donation money, revenue or actual fulfillment.",
    "agent_donor_catalog_supplier": "One distinct DonorId/SupplierId pair through Donation and Gift. Names/type/prefectures resolved. CatalogSupplierCount is computed from the complete distinct set, not a preview list. Eligibility only.",
}


def decoded_parts(definition: dict) -> dict[str, dict]:
    value = definition.get("definition", definition)
    parts = value["parts"]
    result = {}
    for part in parts:
        path = part["path"]
        if path in result or part.get("payloadType") != "InlineBase64":
            raise ValueError("Duplicate path or unsupported definition encoding.")
        result[path] = json.loads(base64.b64decode(part["payload"], validate=True))
    return result


def inline_part(path: str, value: dict) -> dict:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8")
    return {"path": path, "payload": base64.b64encode(payload).decode("ascii"), "payloadType": "InlineBase64"}


def examples(profile: Path = PROFILE) -> list[dict[str, str]]:
    rows = json.loads((profile / "example-queries.json").read_bytes())["examples"]
    questions = set()
    for row in rows:
        if set(row) != {"sourceType", "question", "query"}:
            raise ValueError("Unexpected example field.")
        if row["sourceType"] not in {"lakehouse_tables", "kusto"}:
            raise ValueError("Examples are unsupported for this source type.")
        if not row["question"].strip() or not row["query"].strip() or row["question"] in questions:
            raise ValueError("Empty or duplicate example.")
        questions.add(row["question"])
    return rows


def compile_draft(original: dict, profile: Path = PROFILE) -> tuple[dict, dict]:
    """Build only draft parts; callers own preview, approval, publication and readback."""
    documents = decoded_parts(original)
    root_path = "Files/Config/data_agent.json"
    published_path = "Files/Config/published/stage_config.json"
    if root_path not in documents or published_path not in documents:
        raise ValueError("An existing complete published definition is required.")
    source_docs = [(path, value) for path, value in documents.items()
                   if path.startswith("Files/Config/published/") and path.endswith("/datasource.json")]
    if len(source_docs) != 4 or {value["type"] for _, value in source_docs} != set(INSTRUCTIONS):
        raise ValueError("Exactly the four expected direct sources are required.")
    expected_published = {published_path, *(path for path, _ in source_docs)}
    if any(path.startswith("Files/Config/published/") and path not in expected_published for path in documents):
        raise ValueError("Existing examples/topics or other published parts need explicit reconciliation.")
    text = (profile / "global-instructions.txt").read_text(encoding="utf-8").strip()
    if not 0 < len(text) <= 10000:
        raise ValueError("Agent instructions must fit the supported limit.")
    stage = copy.deepcopy(documents[published_path])
    stage["aiInstructions"] = text
    output = [inline_part(root_path, documents[root_path]),
              inline_part(published_path.replace("/published/", "/draft/"), stage)]
    changes = []
    query_examples = examples(profile)
    for path, old in source_docs:
        value = copy.deepcopy(old)
        kind = value["type"]
        value["dataSourceInstructions"] = (profile / INSTRUCTIONS[kind]).read_text(encoding="utf-8").strip()
        value["userDescription"] = DESCRIPTIONS[kind]
        draft_path = path.replace("/published/", "/draft/", 1)
        output.append(inline_part(draft_path, value))
        added = [row for row in query_examples if row["sourceType"] == kind]
        if added:
            example_path = draft_path.removesuffix("datasource.json") + "fewshots.json"
            output.append(inline_part(example_path, {
                "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/dataAgent/definition/fewShots/1.0.0/schema.json",
                "fewShots": [
                    {"id": str(uuid.uuid5(uuid.NAMESPACE_URL, "furusato-source-grounded:" + row["question"])),
                     "question": row["question"], "query": row["query"]}
                    for row in added
                ],
            }))
        unchanged = set(old) - {"dataSourceInstructions", "userDescription"}
        if any(value.get(key) != old[key] for key in unchanged):
            raise ValueError("Source identity, metadata or selection changed.")
        changes.append({"sourceType": kind, "instructionFieldsChanged": ["dataSourceInstructions", "userDescription"],
                        "sourceIdentityAndSelectionPreserved": True, "exampleCount": len(added)})
    return {"parts": output}, {"globalInstructionsCharacters": len(text), "sources": changes,
                              "publishedByCompiler": False, "cloudCalls": 0}


def compile_view_backed_draft(original: dict, columns: list[dict], profile: Path = PROFILE) -> tuple[dict, dict]:
    """Explicitly replace overlapping selections only after all four views exist."""
    documents = decoded_parts(original)
    wanted = copy.deepcopy(documents)
    paths = [path for path, value in wanted.items() if path.startswith("Files/Config/draft/")
             and path.endswith("/datasource.json") and value["type"] == "lakehouse_tables"]
    if len(paths) != 1 or {row["TABLE_NAME"] for row in columns} != set(VIEW_DESCRIPTIONS):
        raise ValueError("One static source and metadata for exactly four verified views are required.")
    path = paths[0]
    source = wanted[path]

    def walk(items):
        for item in items:
            yield item
            yield from walk(item.get("children", []))

    schemas = [node for node in walk(source["elements"]) if node.get("type") == "lakehouse_tables.schema"
               and node.get("display_name") == "dbo"]
    if len(schemas) != 1:
        raise ValueError("The dbo selection is not unique.")
    schema = schemas[0]
    retired = {"ot_municipality", "ot_donation", "ot_supplier", "ot_supplier_gift"}
    nodes = list(walk(schema.get("children", [])))
    retired_nodes = [node for node in nodes if node.get("type") == "lakehouse_tables.table"
                     and node.get("display_name") in retired]
    if {node["display_name"] for node in retired_nodes} != retired:
        raise ValueError("The overlapping base-table selections are incomplete.")
    for table in retired_nodes:
        for node in walk([table]):
            node["is_selected"] = False
    views = [node for node in nodes if node.get("type") == "lakehouse_tables.view"
             and node.get("display_name") in VIEW_DESCRIPTIONS]
    if len(views) != 4 or {node["display_name"] for node in views} != set(VIEW_DESCRIPTIONS):
        raise ValueError("Use the four service-discovered view identities; do not fabricate table nodes.")
    for view in views:
        name = view["display_name"]
        actual_columns = {node["display_name"]: node.get("data_type") for node in view.get("children", [])}
        expected_columns = {row["COLUMN_NAME"]: row["DATA_TYPE"] for row in columns if row["TABLE_NAME"] == name}
        if not expected_columns or len(actual_columns) != len(view["children"]) or actual_columns != expected_columns:
            raise ValueError("Discovered view columns differ from independently verified SQL metadata.")
        view["description"] = VIEW_DESCRIPTIONS[name]
        for node in walk([view]):
            node["is_selected"] = True
    for node in nodes:
        if node.get("type") == "view_grouping":
            node["is_selected"] = any(child.get("is_selected") for child in node.get("children", []))
    source["dataSourceInstructions"] = (profile / "view-backed-instructions.txt").read_text(encoding="utf-8").strip()
    source["userDescription"] = "Static snapshot with verified, source-owned read-side views: complete names, one-donation grain, whole-snapshot municipality metrics, distinct catalog relationships and precomputed full catalog counts. Not operational data, Gold or fulfillment."
    global_text = (profile / "global-instructions.txt").read_text(encoding="utf-8").strip()
    if not 0 < len(global_text) <= 10000:
        raise ValueError("Agent instruction limit exceeded.")
    wanted["Files/Config/draft/stage_config.json"]["aiInstructions"] = global_text
    rows = json.loads((profile / "view-example-queries.json").read_bytes())["examples"]
    if any(row["sourceType"] != "lakehouse_tables" for row in rows):
        raise ValueError("Only the static example bundle is replaced.")
    wanted[path.removesuffix("datasource.json") + "fewshots.json"] = {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/dataAgent/definition/fewShots/1.0.0/schema.json",
        "fewShots": [{"id": str(uuid.uuid5(uuid.NAMESPACE_URL, "furusato-view-grounded:" + row["question"])),
                      "question": row["question"], "query": row["query"]} for row in rows],
    }
    return {"parts": [inline_part(p, v) for p, v in wanted.items()]}, {
        "viewsSelected": sorted(VIEW_DESCRIPTIONS), "overlappingBaseTablesUnselected": sorted(retired),
        "sourceIdentitiesUnchanged": True, "publishedPartsUnchanged": True,
        "onlyDraftChanged": True, "cloudCalls": 0,
    }
