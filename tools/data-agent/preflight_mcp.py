"""Explicit, once-journaled published MCP discovery; this command cannot ask questions."""

import argparse
from dataclasses import asdict
import json
from pathlib import Path

from native_evaluation import PrivateStore, now_utc
from native_mcp import NativeMcpClient


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace-id", required=True)
    parser.add_argument("--data-agent-id", required=True)
    parser.add_argument("--out", required=True, type=Path, help="Fresh absolute private directory outside Git")
    parser.add_argument("--allow-connect", action="store_true")
    args = parser.parse_args(argv)
    if not args.allow_connect:
        parser.error("No connection attempted. Explicit --allow-connect is required.")
    if not args.out.is_absolute() or args.out.exists():
        parser.error("Choose a fresh absolute private output directory; never reuse a spent intent.")
    config = {"workspace_id": args.workspace_id, "data_agent_id": args.data_agent_id, "stage": "production"}
    from azure.identity import AzureCliCredential
    credential = AzureCliCredential()
    try:
        client = NativeMcpClient(config, credential, 30)
        store = PrivateStore(args.out)
        try:
            store.write("intent.json", {
                "createdAtUtc": now_utc(), "config": client.config, "mode": "preflight",
                "maximumConnectAttempts": 1, "questionSubmissionsAllowed": 0, "retryAllowed": False,
            })
        except FileExistsError:
            parser.error("The intent was reserved concurrently; no authentication or request was attempted.")
        try:
            discovery = client.preflight(store.write_bytes)
        except Exception as exc:
            store.write("result.json", {
                "status": "preflight-failed", "errorType": type(exc).__name__,
                "phase": getattr(exc, "phase", None), "httpStatus": getattr(exc, "http_status", None),
                "questionSubmissions": 0, "strictAcceptanceEligible": False, "retryAllowed": False,
            })
            raise
        result = {"status": "preflight-completed", **asdict(discovery)}
        store.write("result.json", result)
        print(json.dumps({"status": result["status"], "questionSubmissions": 0,
                          "strictAcceptanceEligible": False}))
        return 0
    finally:
        credential.close()


if __name__ == "__main__":
    raise SystemExit(main())
