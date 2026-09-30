"""Prepare, never apply, the observed native Lakehouse source contract.

This is a narrow brownfield patch builder. It preserves the actual downloaded
tree and all lineage identities, changing only one M expression and partition
provenance. It has no network, credentials, write-gate bypass, or deployment call.
Native Instances verification and a separate exclusive repair lease are required.
"""
from __future__ import annotations
import base64
import copy
import hashlib
import json
import re
from typing import Any
from uuid import UUID
from urllib.parse import urlparse

ANNOTATIONS = (
    "ONT_WorkspaceId", "ONT_ItemId", "ONT_ItemKind", "ONT_ItemName",
    "ONT_WorkspaceName", "ONT_SqlEndpoint", "ONT_SqlDatabase", "ONT_PinnedAtUtc",
)


def _text(value: str) -> str:
    if not isinstance(value, str) or not value or any(c in value for c in "\r\n\t"):
        raise ValueError("Native annotation values must be explicit single-line text.")
    return value


def _name(value: str) -> str:
    _text(value)
    return value if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value) else "'" + value.replace("'", "''") + "'"


def _decode(definition: dict[str, Any]) -> dict[str, str]:
    result = {}
    for part in definition["parts"]:
        path = part["path"]
        if path in result or part["payloadType"] != "InlineBase64":
            raise ValueError("Duplicate or unsupported definition part.")
        result[path] = base64.b64decode(part["payload"], validate=True).decode("utf-8")
    return result


def _lineages(parts: dict[str, str]) -> dict[str, list[str]]:
    return {path: re.findall(r"(?m)^\s*lineageTag:\s*([^\r\n]+)", text)
            for path, text in parts.items()}


def native_annotations(*, workspace_id: str, lakehouse_id: str, lakehouse_name: str,
                       workspace_name: str, sql_endpoint: str, pinned_at_utc: str) -> dict[str, str]:
    UUID(workspace_id)
    UUID(lakehouse_id)
    if not re.fullmatch(r"[A-Za-z0-9.-]+", sql_endpoint):
        raise ValueError("SQL endpoint must be a discovered hostname, not a connection command.")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T[0-9:.]+(?:Z|\+00:00)", pinned_at_utc):
        raise ValueError("PinnedAtUtc must be an explicit UTC timestamp.")
    return dict(zip(ANNOTATIONS, (
        workspace_id, lakehouse_id, "Lakehouse", _text(lakehouse_name),
        _text(workspace_name), sql_endpoint, _text(lakehouse_name), pinned_at_utc,
    )))


def prepare_patch(
    definition: dict[str, Any], *, workspace_id: str, lakehouse_id: str,
    lakehouse_name: str, workspace_name: str, sql_endpoint: str,
    pinned_at_utc: str, one_lake_root_url: str, table_names: list[str],
    expression_name: str = "DatabaseQuery",
    target_expression_name: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return a full preview envelope; caller must NOT treat this as persistence."""
    values = native_annotations(
        workspace_id=workspace_id, lakehouse_id=lakehouse_id,
        lakehouse_name=lakehouse_name, workspace_name=workspace_name,
        sql_endpoint=sql_endpoint, pinned_at_utc=pinned_at_utc)
    url = urlparse(one_lake_root_url)
    if (url.scheme != "https" or url.hostname != "onelake.dfs.fabric.microsoft.com"
            or url.path.rstrip("/") != f"/{workspace_id}/{lakehouse_id}"
            or url.query or url.fragment or url.username or url.port):
        raise ValueError("OneLake locator must match the exact discovered workspace/Lakehouse.")
    if not table_names or len(set(table_names)) != len(table_names):
        raise ValueError("An explicit unique backing-table inventory is required.")
    before = _decode(definition)
    if any(path.startswith("metrics/") for path in before):
        raise ValueError("Native Metrics may lose backingMeasure on TMDL roundtrip; this patch is blocked.")
    expressions = before.get("expressions.tmdl", "")
    endings = "\r\n" if "\r\n" in expressions else "\n"
    lines = expressions.splitlines()
    header = f"expression {_name(expression_name)} ="
    target_expression_name = target_expression_name or expression_name
    matches = [i for i, line in enumerate(lines) if line == header]
    if len(matches) != 1:
        raise ValueError("Expected one exact existing expression; no rename or ID regeneration.")
    start = matches[0]
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("expression ")), len(lines))
    block = lines[start:end]
    # Retain every identity/annotation/other metadata line after the M body.
    metadata_start = next((i for i, line in enumerate(block[1:], 1)
                           if line.startswith("\t") and not line.startswith("\t\t") and line.strip()), len(block))
    retained = block[metadata_start:]
    replacement = [f"expression {_name(target_expression_name)} =", "\t\tlet",
                   "\t\t    Source = AzureStorage.DataLake("
                   + json.dumps(one_lake_root_url.rstrip("/")) + ", [HierarchicalNavigation=true])",
                   "\t\tin", "\t\t    Source", *retained]
    after = dict(before)
    after["expressions.tmdl"] = endings.join(lines[:start] + replacement + lines[end:]) + endings
    changed = ["expressions.tmdl"]
    for name in table_names:
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
            raise ValueError("Unsupported backing table name.")
        path = f"tables/{name}.tmdl"
        text = before[path]
        eol = "\r\n" if "\r\n" in text else "\n"
        table_lines = text.splitlines()
        partitions = [i for i, line in enumerate(table_lines) if line.startswith("\tpartition ")]
        if len(partitions) != 1:
            raise ValueError("Only one existing entity partition per backing table is supported.")
        body = table_lines[partitions[0]:]
        if (not body[0].endswith(" = entity")
                or "\t\tmode: directLake" not in body
                or f"\t\t\texpressionSource: {_name(expression_name)}" not in body):
            raise ValueError("Existing partition differs; no blind source rewrite.")
        if any(line.startswith("\t") and not line.startswith("\t\t") and line.strip()
               for line in body[1:]):
            raise ValueError("A later table-level object would make annotation insertion ambiguous.")
        kept = [line for line in table_lines if not re.match(r"^\t\tannotation ONT_[A-Za-z]+ =", line)]
        kept = [f"\t\t\texpressionSource: {_name(target_expression_name)}"
                if line == f"\t\t\texpressionSource: {_name(expression_name)}" else line for line in kept]
        while kept and not kept[-1].strip():
            kept.pop()
        for key in ANNOTATIONS:
            kept.extend(["", f"\t\tannotation {key} = {values[key]}"])
        after[path] = eol.join(kept) + eol + eol
        changed.append(path)
    if _lineages(before) != _lineages(after):
        raise ValueError("Patch changed lineage identities.")
    untouched = set(before) - set(changed)
    if any(before[path] != after[path] for path in untouched):
        raise ValueError("Patch changed a protected entity/rule/relationship/model part.")
    candidate = copy.deepcopy(definition)
    candidate.pop("format", None)  # Actual Ontology service accepts default format.
    for part in candidate["parts"]:
        if part["path"] in changed:
            part["payload"] = base64.b64encode(after[part["path"]].encode("utf-8")).decode("ascii")
    evidence = {
        "status": "prepared-not-applied", "changedParts": changed,
        "lineageIdsPreserved": True, "untouchedPartsByteIdentical": sorted(untouched),
        "staticDataWrites": False, "nativeInstancesProofRequired": True,
        "explicitRepairLeaseRequired": True, "sourceContract": "observed-native-ui-lakehouse-binding",
        "metricBackingLinkPreservationClaimed": False,
        "expressionNameBefore": expression_name, "expressionNameAfter": target_expression_name,
        "beforeSha256": hashlib.sha256(json.dumps(definition, sort_keys=True).encode()).hexdigest(),
        "afterSha256": hashlib.sha256(json.dumps(candidate, sort_keys=True).encode()).hexdigest(),
    }
    return candidate, evidence
