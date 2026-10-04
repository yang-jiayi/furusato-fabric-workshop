"""Compose the current workshop profile over verified native source metadata."""

import copy

from source_grounded_profile import (
    VIEW_DESCRIPTIONS, compile_draft, compile_view_backed_draft, decoded_parts, inline_part,
)
from answer_contract_profile import SCHEMA_VIEWS, compile_schema_grounded_draft
from time_layer_isolation import compile_isolated_draft


def compiler_snapshot(definition):
    """Project an intermediate draft for pure compilation, not cloud publication."""
    documents = decoded_parts(definition)
    stage = "draft" if "Files/Config/draft/stage_config.json" in documents else "published"
    output = {"Files/Config/data_agent.json": copy.deepcopy(documents["Files/Config/data_agent.json"])}
    for path, value in documents.items():
        if path.startswith("Files/Config/" + stage + "/"):
            published = path.replace("/" + stage + "/", "/published/", 1)
            output[published] = copy.deepcopy(value)
            output[published.replace("/published/", "/draft/", 1)] = copy.deepcopy(value)
    return {"parts": [inline_part(path, value) for path, value in output.items()]}


def compile_fresh_profile(service_definition, columns):
    """Return a draft; caller owns source verification, staging and publication."""
    before = decoded_parts(service_definition)
    stage = "draft" if "Files/Config/draft/stage_config.json" in before else "published"
    sources = {value["type"]: value for path, value in before.items()
               if path.startswith(f"Files/Config/{stage}/") and path.endswith("/datasource.json")}
    if set(sources) != {"lakehouse_tables", "kusto", "semantic_model", "ontology"}:
        raise ValueError("Exactly four explicitly bound sources are required.")
    if {row["TABLE_NAME"] for row in columns} != set(VIEW_DESCRIPTIONS) | set(SCHEMA_VIEWS):
        raise ValueError("Independently verified schemas for all six views are required.")
    initial = compiler_snapshot(service_definition)
    source, source_receipt = compile_draft(initial)
    views, view_receipt = compile_view_backed_draft(
        source, [row for row in columns if row["TABLE_NAME"] in VIEW_DESCRIPTIONS])
    contract, contract_receipt = compile_schema_grounded_draft(
        compiler_snapshot(views), [row for row in columns if row["TABLE_NAME"] in SCHEMA_VIEWS])
    isolated, isolation_receipt = compile_isolated_draft(compiler_snapshot(contract))
    output = decoded_parts(isolated)
    for path, value in output.items():
        if path.startswith("Files/Config/draft/") and path.endswith("/datasource.json"):
            original = sources[value["type"]]
            for key in ("artifactId", "workspaceId", "displayName", "type"):
                if value.get(key) != original.get(key):
                    raise ValueError("A source identity changed during compilation.")
    return {"parts": [inline_part(path, value) for path, value in output.items()
                      if "/published/" not in path]}, {
        "compilerStages": [source_receipt, view_receipt, contract_receipt, isolation_receipt],
        "sourceIdentitiesPreserved": True, "publishedByCompiler": False, "cloudCalls": 0,
    }
