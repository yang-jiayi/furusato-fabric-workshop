"""Read-only Data Agent service checks through the public management API.

Lists each data source's example queries with the service ``validationStatus``
and walks the service's element tree to report SQL views (state, selection,
columns). Nothing is written to the Agent. Raw responses go to a private root
outside Git; stdout carries counts, names and redacted reasons only.

    python -B tools/data-agent/agent_service_check.py --private-root <dir> \
        --workspace-id <id> --agent-id <id> [--stage staging] [--view-columns <json>]

``--view-columns`` is a private JSON list of INFORMATION_SCHEMA.COLUMNS rows
(TABLE_NAME, COLUMN_NAME) for the verified views; each view's service columns
are compared with it. Examples that fail validation are reported, never
re-labelled: the service does not send them to the Agent.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlencode

from native_evaluation import EvaluationError, PrivateStore, now_utc

API = "https://api.fabric.microsoft.com"
SCOPE = "https://api.fabric.microsoft.com/.default"
HOST = re.compile(r"\b[\w.-]+\.fabric\.microsoft\.com\b")
GUID = re.compile(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b")


def redact(text: str, limit: int = 240) -> str:
    return GUID.sub("<id>", HOST.sub("<host>", str(text)))[:limit]


def paged(get: Callable[[str], dict[str, Any]], path: str, **query: str) -> list[dict[str, Any]]:
    items, token = [], None
    while True:
        params = {k: v for k, v in {**query, "continuationToken": token}.items() if v}
        page = get(path + (f"?{urlencode(params)}" if params else ""))
        items += page.get("value", [])
        token = page.get("continuationToken")
        if not token:
            return items


def summarize_fewshots(fewshots: list[dict[str, Any]]) -> dict[str, Any]:
    states = Counter(str((f.get("validationStatus") or {}).get("value", "Unknown")) for f in fewshots)
    reasons = Counter(
        redact((f.get("validationStatus") or {}).get("reason", ""), 400)
        for f in fewshots if (f.get("validationStatus") or {}).get("value") != "Valid"
    )
    return {"total": len(fewshots), "status": dict(sorted(states.items())),
            "nonValidReasons": [{"reason": r, "count": n} for r, n in reasons.most_common()]}


def element_tree(get_children: Callable[[str | None], list[dict[str, Any]]]) -> list[dict[str, Any]]:
    tree: list[dict[str, Any]] = []

    def walk(node: dict[str, Any], path: list[str]) -> None:
        tree.append({**node, "path": path})
        if node.get("hasSubElements"):
            for child in get_children(node["id"]):
                walk(child, path + [child.get("displayName")])

    for root in get_children(None):
        walk(root, [root.get("displayName")])
    return tree


def summarize_views(tree: list[dict[str, Any]], expected: dict[str, set[str]] | None) -> dict[str, Any]:
    views = {}
    for view in (n for n in tree if n.get("type") == "View"):
        depth = len(view["path"])
        columns = [n for n in tree if len(n["path"]) == depth + 1 and n["path"][:depth] == view["path"]]
        entry = {
            "state": view.get("state"), "selected": view.get("isSelected"),
            "columns": len(columns), "columnsSelected": sum(bool(c.get("isSelected")) for c in columns),
            "unselectedColumns": sorted(c.get("displayName") for c in columns if not c.get("isSelected")),
        }
        if expected is not None:
            entry["matchesInformationSchema"] = (
                {c.get("displayName") for c in columns} == expected.get(view.get("displayName"), set()))
        views[view.get("displayName")] = entry
    selected_tables = sorted(n.get("displayName") for n in tree if n.get("type") == "Table" and n.get("isSelected"))
    return {"views": views, "selectedTables": selected_tables}


def expected_columns(rows: list[dict[str, str]]) -> dict[str, set[str]]:
    result: dict[str, set[str]] = {}
    for row in rows:
        result.setdefault(row["TABLE_NAME"], set()).add(row["COLUMN_NAME"])
    return result


def check(
    get: Callable[[str], dict[str, Any]], workspace: str, agent: str, stage: str,
    expected: dict[str, set[str]] | None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    base = f"/v1/workspaces/{workspace}/dataAgents/{agent}" + ("/staging" if stage == "staging" else "")
    raw: dict[str, Any] = {"stage": stage, "datasources": paged(get, f"{base}/datasources")}
    summary: dict[str, Any] = {"stage": stage, "checkedAtUtc": now_utc(), "datasources": []}
    for index, source in enumerate(raw["datasources"]):
        path = f"{base}/datasources/{source['id']}"
        fewshots = paged(get, f"{path}/fewshots")
        tree = element_tree(lambda root, p=path: paged(get, f"{p}/elements", rootId=root or ""))
        raw[f"datasource-{index}"] = {"fewshots": fewshots, "elements": tree}
        entry = {
            "index": index,
            "type": source.get("type") or source.get("datasourceType"),
            "displayName": source.get("displayName"),
            "examples": summarize_fewshots(fewshots),
            "elements": len(tree),
        }
        if any(n.get("type") == "View" for n in tree):
            entry.update(summarize_views(tree, expected))
        summary["datasources"].append(entry)
    return summary, raw


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--private-root", type=Path, required=True)
    parser.add_argument("--workspace-id", required=True)
    parser.add_argument("--agent-id", required=True)
    parser.add_argument("--stage", choices=["published", "staging"], default="published")
    parser.add_argument("--view-columns", type=Path, help="Private INFORMATION_SCHEMA.COLUMNS JSON list.")
    args = parser.parse_args(argv)
    store = PrivateStore(args.private_root)
    expected = None
    if args.view_columns:
        expected = expected_columns(json.loads(args.view_columns.read_text(encoding="utf-8")))
    import requests
    from azure.identity import AzureCliCredential

    token = AzureCliCredential().get_token(SCOPE).token
    session = requests.Session()
    session.headers["Authorization"] = f"Bearer {token}"

    def get(path: str) -> dict[str, Any]:
        response = session.get(API + path, timeout=60)
        if response.status_code != 200:
            raise EvaluationError(f"GET failed with HTTP {response.status_code}.")
        return response.json()

    try:
        summary, raw = check(get, args.workspace_id, args.agent_id, args.stage, expected)
    finally:
        session.close()
    stamp = summary["checkedAtUtc"].replace(":", "").replace("-", "")[:15]
    store.write(f"agent-service-check/{args.stage}-{stamp}-raw.json", raw)
    store.write(f"agent-service-check/{args.stage}-{stamp}-summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
