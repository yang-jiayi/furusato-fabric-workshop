"""Portable four-source Data Agent candidate; no accuracy claim or implicit publish."""
from __future__ import annotations
import copy
import json
import re
import uuid
from pathlib import Path
from typing import Any
from preview30_runtime import BASE, PREVIEW, load
from preview30_ontology import lineage


def build_profile() -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    source_root = BASE / "provisioning/bundle/data-agent/Files/Config/published"
    files: dict[str, dict[str, Any]] = {}
    instructions = (PREVIEW / "data-agent/global-instructions.txt").read_text(encoding="utf-8")
    if len(instructions) > 15000 or "\r" in instructions:
        raise ValueError("GLOBAL exceeds its safe 15,000-character/LF budget.")
    stage = {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/dataAgent/definition/stageConfiguration/1.0.0/schema.json",
        "aiInstructions": instructions,
        "experimental": {"enableExperimentalFeatures": True, "codeInterpreterEnabled": True},
    }
    files["Files/Config/data_agent.json"] = {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/dataAgent/definition/dataAgent/2.1.0/schema.json"}
    files["Files/Config/draft/stage_config.json"] = stage
    for path in source_root.rglob("datasource.json"):
        relative = path.relative_to(source_root).as_posix()
        files["Files/Config/draft/" + relative] = load(path)
    metrics = load(PREVIEW / "powerbi/native-metrics-contract.json")
    model_source = {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/dataAgent/definition/dataSource/1.0.0/schema.json",
        "artifactId": "{{item.semanticModel.id}}", "workspaceId": "{{workspace.id}}",
        "displayName": "{{name.semanticModel}}", "type": "semantic_model",
        "userDescription": "Governed source-owned DAX over Notebook05 Gold. StaticSeed and accepted RealtimeIncrement remain explicitly separated.",
        "dataSourceInstructions": "Use source-owned DAX measures. Preserve current dimension filters and label StaticSeed versus RealtimeIncrement. Do not infer raw Eventhouse counts from Gold.",
        "metadata": {}, "elements": [],
    }
    table_root = PREVIEW / "powerbi/Furusato_Analytics.SemanticModel/definition/tables"
    for path in sorted(table_root.glob("*.tmdl")):
        table_name = path.stem
        children = []
        for line in path.read_text(encoding="utf-8").splitlines():
            match = re.match(r"\t(column|measure)\s+('(?:[^']|'')+'|[^=\s]+)(?:\s*=.*)?$", line)
            if match:
                kind, name = match.groups()
                name = name[1:-1].replace("''", "'") if name.startswith("'") else name
                children.append({"id": lineage("agent-element", table_name + "/" + kind + "/" + name),
                                 "display_name": name, "is_selected": True,
                                 "type": "semantic_model." + kind, "description": None, "children": []})
        model_source["elements"].append({
            "id": lineage("agent-table", table_name), "display_name": table_name,
            "type": "semantic_model.table", "description": None, "is_selected": True, "children": children})
    files["Files/Config/draft/semantic-model-{{name.semanticModel}}/datasource.json"] = model_source
    contract = {
        "edition": "v3.0.0-preview", "status": "candidate", "validationStatus": "offline-only",
        "accuracyAccepted": False, "publishedByBuild": False,
        "sourceTypes": ["lakehouse_tables", "kusto", "ontology", "semantic_model"],
        "codeInterpreterConfigured": True, "codeInterpreterObserved": False,
        "directSemanticModelSourceRequired": True,
        "ontologyGenerationRequired": 2,
        "nativeMetricProjectionInherited": False,
        "graphRequiredByDefault": False,
        "globalInstructionsCharacters": len(instructions),
        "sourceOwnedMeasures": metrics["measures"],
    }
    return files, contract
