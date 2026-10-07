"""Export a pipeline run's Copy activity record from the Fabric activity-runs API.

Read-only. Writes the JSON shape that `preview30_runtime.py verify-delivery
--native-copy` validates: pipelineRunId, activityType, status and the
service's own output (rowsRead / rowsCopied). Nothing is inferred: if the
service returns no single Copy activity for the run, the export stops.

    python tools/provisioning/export_copy_activity.py --workspace-id <ws> \
        --pipeline-job-id <job> --out <private path>.json
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

API = "https://api.fabric.microsoft.com/v1"


def copy_record(runs: list[dict[str, Any]], job_id: str) -> dict[str, Any]:
    copies = [r for r in runs if str(r.get("activityType", "")).lower() == "copy"]
    if len(copies) != 1:
        raise ValueError(f"Expected exactly one Copy activity in run {job_id}, found {len(copies)}.")
    run = copies[0]
    output = run.get("output")
    if isinstance(output, str):
        output = json.loads(output)
    if not isinstance(output, dict) or "rowsRead" not in output or "rowsCopied" not in output:
        raise ValueError("The Copy activity output lacks rowsRead/rowsCopied.")
    run_id = run.get("pipelineRunId") or run.get("pipelineRunID")
    if str(run_id).lower() != job_id.lower():
        raise ValueError("The activity belongs to a different pipeline run.")
    return {
        "pipelineRunId": job_id, "activityType": "Copy", "activityName": run.get("activityName"),
        "activityRunId": run.get("activityRunId"), "status": run.get("status"),
        "activityRunStart": run.get("activityRunStart"), "activityRunEnd": run.get("activityRunEnd"),
        "output": {key: output[key] for key in ("rowsRead", "rowsCopied", "dataRead", "dataWritten") if key in output},
        "exportedFrom": "POST /workspaces/{workspaceId}/datapipelines/pipelineruns/{jobId}/queryactivityruns",
    }


def query_runs(post: Callable[[str, dict], dict], workspace: str, job_id: str) -> list[dict[str, Any]]:
    now = datetime.now(timezone.utc)
    body = {
        "filters": [],
        "orderBy": [{"orderBy": "ActivityRunStart", "order": "DESC"}],
        "lastUpdatedAfter": (now - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "lastUpdatedBefore": (now + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    reply = post(f"{API}/workspaces/{workspace}/datapipelines/pipelineruns/{job_id}/queryactivityruns", body)
    return reply.get("value", reply if isinstance(reply, list) else [])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--workspace-id", required=True)
    parser.add_argument("--pipeline-job-id", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.out.exists():
        raise SystemExit("Refusing to overwrite an existing export.")
    import requests
    from azure.identity import AzureCliCredential

    session = requests.Session()
    session.headers["Authorization"] = "Bearer " + AzureCliCredential().get_token(
        "https://api.fabric.microsoft.com/.default").token

    def post(url: str, body: dict) -> dict:
        response = session.post(url, json=body, timeout=60)
        if response.status_code != 200:
            raise SystemExit(f"Activity-runs query failed with HTTP {response.status_code}.")
        return response.json()

    try:
        record = copy_record(query_runs(post, args.workspace_id, args.pipeline_job_id), args.pipeline_job_id)
    finally:
        session.close()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": record["status"], "rowsRead": record["output"].get("rowsRead"),
                      "rowsCopied": record["output"].get("rowsCopied")}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
