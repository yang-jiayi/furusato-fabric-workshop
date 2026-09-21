"""Portable materialization of the separately derived AI path Ontology.

The resealer derives this template with tools/data-agent/path_ontology.py.
Runtime code only substitutes discovered bindings; it never prunes the teaching
Ontology, adds graph facts, changes security, or infers answer-quality acceptance.
"""

from __future__ import annotations

import base64
import copy
import hashlib
import json
import re
import uuid
from typing import Any, Mapping

PATH_COUNTS = {
    "definitionParts": 52,
    "entityTypes": 10,
    "staticProperties": 21,
    "timeseriesProperties": 0,
    "dataBindings": 10,
    "relationshipTypes": 15,
    "contextualizations": 15,
    "overviews": 0,
}
PATH_GRAPH_COUNTS = {
    "nodeTypes": 10, "edgeTypes": 15, "dataSources": 11,
    "nodeTables": 10, "edgeTables": 15,
}


def canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")


def ontology_json_bytes(value: Any) -> bytes:
    """Keep the Fabric polymorphic discriminator first, independently of hash order."""
    def ordered(node):
        if isinstance(node, dict):
            keys = (["sourceType"] if "sourceType" in node else []) + [
                key for key in node if key != "sourceType"
            ]
            return {key: ordered(node[key]) for key in keys}
        if isinstance(node, list):
            return [ordered(child) for child in node]
        return node

    return json.dumps(
        ordered(value), ensure_ascii=False, separators=(",", ":"), sort_keys=False,
    ).encode("utf-8")


def materialize_path_definition(
    template: Mapping[str, Any],
    *,
    workspace_id: str,
    lakehouse_id: str,
    display_name: str,
) -> dict[str, Any]:
    """Bind a sealed source-faithful template without regenerating any model ID."""
    if template.get("expectedContract") != PATH_COUNTS:
        raise ValueError("AI path Ontology must retain the 10/21/0/15 contract.")
    if hashlib.sha256(canonical(template["parts"])).hexdigest() != template.get(
        "definitionTemplateSha256"
    ):
        raise ValueError("AI path Ontology template digest mismatch.")
    for value, label in ((workspace_id, "workspace"), (lakehouse_id, "lakehouse")):
        if not re.fullmatch(
            r"[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}", value
        ):
            raise ValueError(f"Discovered {label} ID must be a GUID.")
    if not re.fullmatch(r"ONT_Furusato_AIPath_(?!000$)[0-9]{3}", display_name):
        raise ValueError("AI path Ontology requires its separate participant name.")
    replacements = {
        "{{workspace.id}}": workspace_id,
        "{{source.lakehouse.id}}": lakehouse_id,
        "{{ontology.displayName}}": display_name,
    }

    def bind(value: Any) -> Any:
        if isinstance(value, dict):
            result = {key: bind(child) for key, child in value.items()}
            if "sourceSchema" in result and result["sourceSchema"] != "dbo":
                raise ValueError("AI path Ontology must bind the managed dbo schema.")
            return result
        if isinstance(value, list):
            return [bind(child) for child in value]
        if isinstance(value, str):
            for token, replacement in replacements.items():
                value = value.replace(token, replacement)
            if "{{" in value or "}}" in value:
                raise ValueError("Unresolved AI path Ontology binding.")
        return value

    parts = []
    for part in template["parts"]:
        content = bind(copy.deepcopy(part["content"]))
        if part["path"] == ".platform":
            content["config"]["logicalId"] = str(uuid.uuid5(
                uuid.NAMESPACE_URL, f"urn:furusato:{workspace_id}:{display_name}",
            ))
        parts.append({
            "path": part["path"],
            "payloadType": "InlineBase64",
            "payload": base64.b64encode(ontology_json_bytes(content)).decode("ascii"),
        })
    return {"parts": parts}


def compatibility_observation(lakehouse: Mapping[str, Any]) -> dict[str, str]:
    """Report only observed settings, never equate a successful probe to disabled security."""
    properties = lakehouse.get("properties", {})
    values = [
        properties[key]
        for key in ("oneLakeSecurityEnabled", "isOneLakeSecurityEnabled")
        if key in properties and type(properties[key]) is bool
    ]
    if len(set(values)) > 1:
        raise ValueError("Lakehouse returned contradictory OneLake security settings.")
    state = "UNKNOWN" if not values else ("ENABLED" if values[0] else "DISABLED")
    return {
        "oneLakeSecurity": state,
        "compatibilityScope": (
            "Managed dbo bindings and the two generated graph refresh lifecycles only; "
            "not a general OneLake security compatibility guarantee."
        ),
    }
