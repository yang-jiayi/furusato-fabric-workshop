"""Read-only native SQL MCP checks; no fabricated rows or inferred readiness."""
from __future__ import annotations
import csv
import hashlib
import io
import json
from pathlib import Path
from pathlib import PurePosixPath
import re
import time
from typing import Any
from urllib.parse import quote

from preview30_runtime import (
    EvidenceClient, SafetyError, PREVIEW, load, now, save, scope_fingerprint, scope_from_document,
)
from workshop_runtime import EXPECTED_TABLES


GOLD_GENERATION_COLUMN = "_AnalyticsGenerationId"
GOLD_CONTROL_KEY = "furusato-analytics-extension"
GOLD_EXPECTED_TOTALS = {
    "bronze.donation_events_raw": (15000, 253886000),
    "silver.donation_event": (14900, 252058000),
    "quarantine.donation_events_rejected": (100, 1828000),
}
GOLD_EXPECTED_BY_SOURCE = {
    "StaticSeed": (80000, 1344099000),
    "RealtimeIncrement": (14900, 252058000),
}
GOLD_EXPECTED_OUTPUT_TOTALS = (94900, 1596157000)


class ReadOnlySqlMcp:
    """Documented item-scoped SQL endpoint MCP with tool discovery and CSV results."""

    def __init__(self, client: EvidenceClient, sql_endpoint_id: str):
        self.client = client
        self.url = (f"https://api.fabric.microsoft.com/v1/mcp/dataPlane/workspaces/"
                    f"{client.scope['workspaceId']}/items/{sql_endpoint_id}/sqlEndpoint")
        self.counter = 0
        self.headers = {"Content-Type": "application/json",
                        "Accept": "application/json, text/event-stream",
                        "x-ms-fabric-skill": "sqldw-cli"}
        self.tool_name: str | None = None

    def rpc(self, method: str, params: dict[str, Any], *, notification: bool = False) -> Any:
        self.counter += 1
        body = {"jsonrpc": "2.0", "method": method, "params": params}
        if not notification:
            body["id"] = self.counter
        log = self.client.evidence / "sql-mcp" / f"{time.time_ns()}-{self.counter:03d}"
        save(log.with_suffix(".request.json"), body)
        token = self.client.credential.get_token("https://api.fabric.microsoft.com/.default").token
        reply = self.client.session.post(
            self.url, json=body, headers={**self.headers, "Authorization": "Bearer " + token},
            timeout=(20, 320), allow_redirects=False, stream=True)
        if reply.headers.get("Mcp-Session-Id"):
            self.headers["Mcp-Session-Id"] = reply.headers["Mcp-Session-Id"]
        if notification and reply.status_code in {200, 202, 204}:
            reply.close()
            return None
        if reply.status_code != 200:
            save(log.with_suffix(".response.json"),
                 {"statusCode": reply.status_code, "bodyText": reply.text})
            reply.close()
            raise SafetyError("Native SQL MCP returned HTTP failure; see exact private evidence.")
        result = None
        if "text/event-stream" in reply.headers.get("Content-Type", ""):
            frame: list[bytes] = []
            wire = bytearray()
            deadline = time.monotonic() + 320
            for line in reply.iter_lines(chunk_size=1024):
                if time.monotonic() > deadline or len(wire) > 16 * 1024 * 1024:
                    reply.close()
                    raise SafetyError("SQL MCP reply exceeded the bounded response limit.")
                wire.extend(line + b"\n")
                if line:
                    frame.append(line)
                    continue
                data = b"\n".join(v[5:].lstrip() for v in frame if v.startswith(b"data:"))
                frame = []
                if data and data != b"[DONE]":
                    candidate = json.loads(data)
                    if candidate.get("id") == self.counter:
                        result = candidate
                        break
            log.with_suffix(".response.body").write_bytes(bytes(wire))
        else:
            data = reply.content
            log.with_suffix(".response.body").write_bytes(data)
            result = json.loads(data)
        reply.close()
        if not isinstance(result, dict) or result.get("id") != self.counter or result.get("error"):
            raise SafetyError("SQL MCP did not return a matching successful JSON-RPC response.")
        value = result.get("result")
        if not isinstance(value, dict) or value.get("isError"):
            raise SafetyError("SQL tool reported failure; missing data is not successful zero rows.")
        return value

    def discover(self) -> None:
        init = self.rpc("initialize", {"protocolVersion": "2025-03-26",
                                      "capabilities": {},
                                      "clientInfo": {"name": "furusato-preview30-readonly", "version": "3.0.0-preview"}})
        if init.get("protocolVersion"):
            self.headers["MCP-Protocol-Version"] = init["protocolVersion"]
        self.rpc("notifications/initialized", {}, notification=True)
        tools = self.rpc("tools/list", {}).get("tools", [])
        matches = [v for v in tools if str(v.get("name", "")).endswith("execute_query")]
        if len(matches) != 1:
            raise SafetyError("Native SQL execute_query tool was not uniquely discovered.")
        props = matches[0].get("inputSchema", {}).get("properties", {})
        if not {"workspaceId", "itemId", "query"}.issubset(props):
            raise SafetyError("Native SQL input contract differs; do not invent arguments.")
        self.tool_name = matches[0]["name"]

    def query(self, sql_endpoint_id: str, query: str) -> list[dict[str, str]]:
        if not query.lstrip().upper().startswith("SELECT") or re.search(
                r"\b(?:INSERT|UPDATE|DELETE|MERGE|TRUNCATE|DROP|ALTER|CREATE|EXEC|INTO|GRANT|DENY)\b",
                query, re.IGNORECASE):
            raise SafetyError("Only fixed read-only SELECT validation is supported.")
        if not self.tool_name:
            self.discover()
        result = self.rpc("tools/call", {"name": self.tool_name, "arguments": {
            "workspaceId": self.client.scope["workspaceId"], "itemId": sql_endpoint_id,
            "query": query}})
        resources = [p.get("resource", {}) for p in result.get("content", [])
                     if p.get("type") == "resource"]
        csvs = [r["text"] for r in resources
                if "csv" in r.get("mimeType", "").lower() and isinstance(r.get("text"), str)]
        if len(csvs) != 1:
            raise SafetyError("Expected a single native embedded CSV resource; unsupported result shape.")
        rows = list(csv.DictReader(io.StringIO(csvs[0])))
        if len(rows) >= 10000:
            raise SafetyError("Native result may be truncated.")
        return rows


def source_queries() -> dict[str, str]:
    counts = " UNION ALL ".join(
        f"SELECT '{name}' AS TableName, COUNT_BIG(*) AS [RowCount], "
        f"COUNT(DISTINCT [_WorkshopGenerationId]) AS GenerationCount, "
        f"MIN([_WorkshopGenerationId]) AS MinGeneration, MAX([_WorkshopGenerationId]) AS MaxGeneration "
        f"FROM dbo.[{name}]" for name in EXPECTED_TABLES)
    return {
        "catalog": "SELECT TABLE_SCHEMA, TABLE_NAME FROM INFORMATION_SCHEMA.TABLES "
                   "WHERE TABLE_SCHEMA = 'dbo' ORDER BY TABLE_NAME",
        "generationCounts": counts,
        "publishControl": "SELECT TOP 100 RecordType, TableName, Generation, PublicationRunId, "
                          "PublishState, FailureReason FROM dbo.audit_furusato_publish_control "
                          "WHERE ControlKey = 'furusato-canonical-v2.7.0' ORDER BY Generation DESC, RecordType, TableName",
        "staticTotals": "SELECT COUNT_BIG(*) AS DonationRows, SUM(DonationAmountYen) AS DonationYen "
                        "FROM dbo.ot_donation",
    }


def assess_sources(results: dict[str, list[dict[str, str]]]) -> dict[str, Any]:
    counts = results["generationCounts"]
    if {r["TableName"] for r in counts} != set(EXPECTED_TABLES) or len(counts) != 20:
        raise SafetyError("Twenty final data tables were not all observed.")
    control = results["publishControl"]
    leases = [r for r in control if r["RecordType"] == "Lease"]
    if len(leases) != 1 or leases[0]["PublishState"] != "Ready":
        raise SafetyError("Global publication lease is not uniquely Ready.")
    generation = int(leases[0]["Generation"])
    generation_id = f"furusato-v2.7.0-generation-{generation:020d}"
    table_control = [r for r in control if r["RecordType"] == "Table" and int(r["Generation"]) == generation]
    if len(table_control) != 20 or {r["TableName"] for r in table_control} != set(EXPECTED_TABLES):
        raise SafetyError("Current generation lacks its twenty table readiness records.")
    if any(r["PublishState"] != "Ready" or r.get("FailureReason") for r in table_control):
        raise SafetyError("At least one table publication is incomplete/failed.")
    if any(int(r["GenerationCount"]) != 1 or r["MinGeneration"] != generation_id
           or r["MaxGeneration"] != generation_id or int(r["RowCount"]) < 1 for r in counts):
        raise SafetyError("Table data contains stale/mixed/empty generations.")
    row_counts = {r["TableName"]: int(r["RowCount"]) for r in counts}
    if row_counts["ot_donation"] != 80000 or row_counts["stg_donation_orders"] != 80000:
        raise SafetyError("Static fact and typed staging row counts do not match the immutable 80,000-row source.")
    totals = results["staticTotals"]
    if len(totals) != 1 or int(totals[0]["DonationRows"]) != 80000 or int(totals[0]["DonationYen"]) != 1344099000:
        raise SafetyError("Live static count/amount differ from the immutable source.")
    return {"verified": True, "timestampUtc": now(), "finalTableCount": 20,
            "generation": generation, "generationId": generation_id,
            "staticDonationRows": 80000, "staticDonationYen": 1344099000}


def verify_sources(args: Any) -> dict[str, Any]:
    scope = scope_from_document(load(args.scope), args.environment)
    state_path = args.evidence_dir / "deployment-state.json"
    state = load(state_path)
    lakehouse = state["items"].get("lakehouse")
    if not lakehouse:
        raise SafetyError("No owned Lakehouse receipt exists.")
    client = EvidenceClient(scope, args.evidence_dir, credential=getattr(args, "credential", None))
    detail = client.request("GET", f"/workspaces/{scope['workspaceId']}/lakehouses/{lakehouse['id']}",
                            skill="sqldw-cli").json()
    if detail.get("folderId") != scope["folderId"]:
        raise SafetyError("Owned Lakehouse is outside the frozen folder.")
    endpoint = detail["properties"]["sqlEndpointProperties"]["id"]
    mcp = ReadOnlySqlMcp(client, endpoint)
    results = {}
    for key, query in source_queries().items():
        results[key] = mcp.query(endpoint, query)
        time.sleep(3)
    save(args.evidence_dir / "verification" / "sources-rows.json", results)
    assessment = assess_sources(results)
    state["sourceVerification"] = assessment
    save(state_path, state)
    save(args.evidence_dir / "verification" / "sources.json", assessment)
    return assessment


def _validate_delta_relative_path(path: Any) -> str:
    if not isinstance(path, str) or not path or "\\" in path:
        raise SafetyError("Delta log contains an invalid relative file path.")
    candidate = PurePosixPath(path)
    if candidate.is_absolute() or any(part in {"", ".", ".."} for part in candidate.parts):
        raise SafetyError("Delta log file path escapes its owned table.")
    return candidate.as_posix()


def _resolve_delta_active_files(logs: list[tuple[int, bytes]]) -> dict[str, dict[str, Any]]:
    """Apply ordered Delta add/remove actions from version zero through latest."""
    if not logs or [version for version, _ in logs] != list(range(logs[-1][0] + 1)):
        raise SafetyError("Delta log versions are missing, stale, or non-contiguous.")
    active: dict[str, dict[str, Any]] = {}
    for version, content in logs:
        try:
            lines = content.decode("utf-8").splitlines()
            actions = [json.loads(line) for line in lines if line.strip()]
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise SafetyError(f"Delta version {version} is not valid UTF-8 JSONL.") from exc
        if not actions:
            raise SafetyError(f"Delta version {version} contains no actions.")
        for action in actions:
            if not isinstance(action, dict):
                raise SafetyError("Delta log action is malformed.")
            if "add" in action:
                add = action["add"]
                if not isinstance(add, dict):
                    raise SafetyError("Delta add action is malformed.")
                path = _validate_delta_relative_path(add.get("path"))
                active[path] = add
            if "remove" in action:
                remove = action["remove"]
                if not isinstance(remove, dict):
                    raise SafetyError("Delta remove action is malformed.")
                active.pop(_validate_delta_relative_path(remove.get("path")), None)
    if not active:
        raise SafetyError("Latest Delta snapshot has no active Parquet files.")
    return active


class OneLakeDeltaReader:
    """Resolve and read a fresh OneLake Delta snapshot using storage-scoped GETs only."""

    def __init__(self, client: EvidenceClient, lakehouse_id: str):
        self.client = client
        self.scope = client.scope
        self.lakehouse_id = lakehouse_id
        self.workspace_id = self.scope["workspaceId"]
        self.token = client.credential.get_token("https://storage.azure.com/.default").token
        self.headers = {"Authorization": "Bearer " + self.token, "x-ms-version": "2023-11-03"}
        self.pages: list[dict[str, Any]] = []
        self.file_receipts: list[dict[str, Any]] = []

    def _get(self, host: str, path: str, *, params: dict[str, Any] | None = None) -> bytes:
        url = f"https://{host}/{self.workspace_id}/{self.lakehouse_id}/{path}"
        response = self.client.session.get(
            url, params=params, headers=self.headers, timeout=(20, 120), allow_redirects=False)
        receipt = {
            "method": "GET", "url": response.url, "statusCode": response.status_code,
            "requestId": response.headers.get("x-ms-request-id"),
            "bytes": len(response.content), "sha256": hashlib.sha256(response.content).hexdigest(),
        }
        if response.status_code != 200:
            self.file_receipts.append(receipt)
            raise SafetyError(f"OneLake read failed with HTTP {response.status_code}; see private evidence.")
        self.file_receipts.append(receipt)
        if not receipt["requestId"]:
            raise SafetyError("OneLake did not provide a request ID for a Delta/parquet read.")
        return response.content

    def list_table_paths(self) -> list[str]:
        url = f"https://onelake.dfs.fabric.microsoft.com/{self.workspace_id}"
        params: dict[str, Any] = {
            "resource": "filesystem", "directory": f"{self.lakehouse_id}/Tables",
            "recursive": "true", "maxResults": 5000,
        }
        paths: list[str] = []
        seen_tokens: set[str] = set()
        for _ in range(1000):
            response = self.client.session.get(
                url, params=params, headers=self.headers, timeout=(20, 120), allow_redirects=False)
            request_receipt = {
                "method": "GET", "url": response.url, "statusCode": response.status_code,
                "requestId": response.headers.get("x-ms-request-id"),
                "bytes": len(response.content), "sha256": hashlib.sha256(response.content).hexdigest(),
            }
            self.pages.append(request_receipt)
            if response.status_code != 200:
                raise SafetyError(f"OneLake path listing failed with HTTP {response.status_code}.")
            try:
                page = response.json()
            except ValueError as exc:
                raise SafetyError("OneLake path listing did not return JSON.") from exc
            entries = page.get("paths")
            if not isinstance(entries, list):
                raise SafetyError("OneLake path listing omitted its paths array.")
            for entry in entries:
                if not isinstance(entry, dict) or not isinstance(entry.get("name"), str):
                    raise SafetyError("OneLake returned a malformed path entry.")
                name = entry["name"].replace("\\", "/").lstrip("/")
                prefix = f"{self.lakehouse_id}/Tables/"
                if not name.startswith(prefix):
                    raise SafetyError("OneLake listing returned a path outside the selected Lakehouse Tables.")
                _validate_delta_relative_path(name)
                paths.append(name[len(self.lakehouse_id) + 1:])
                if len(paths) > 100000:
                    raise SafetyError("OneLake table listing exceeded the bounded path count.")
            continuation = response.headers.get("x-ms-continuation") or page.get("ContinuationToken")
            if not continuation:
                return paths
            if continuation in seen_tokens:
                raise SafetyError("OneLake path-list continuation token repeated.")
            seen_tokens.add(continuation)
            params["continuation"] = continuation
        raise SafetyError("OneLake path listing exceeded the bounded page count.")

    def table_observation(self, table_name: str, table_paths: list[str]) -> dict[str, Any]:
        if table_name.count(".") != 1:
            raise SafetyError(f"Gold contract table name is malformed: {table_name}")
        schema, name = table_name.split(".", 1)
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", schema) or not re.fullmatch(
                r"[A-Za-z_][A-Za-z0-9_]*", name):
            raise SafetyError(f"Gold contract table name is not a safe Delta identifier: {table_name}")
        table_path = f"Tables/{schema}/{name}"
        log_prefix = f"{table_path}/_delta_log/"
        versions: dict[int, str] = {}
        checkpoints = []
        for path in table_paths:
            if not path.startswith(log_prefix):
                continue
            name = path[len(log_prefix):]
            match = re.fullmatch(r"(\d{20})\.json", name)
            if match:
                version = int(match.group(1))
                if version in versions:
                    raise SafetyError(f"{table_name} has an ambiguous Delta version {version}.")
                versions[version] = name
            elif "checkpoint" in name:
                checkpoints.append(name)
        if checkpoints:
            raise SafetyError(f"{table_name} uses a Delta checkpoint; this verifier requires the bounded JSON log chain.")
        if not versions:
            raise SafetyError(f"Required Delta table is missing: {table_name}")
        ordered = sorted(versions)
        log_contents: list[tuple[int, bytes]] = []
        log_receipts = []
        for version in ordered:
            relative = f"{log_prefix}{versions[version]}"
            content = self._get("onelake.blob.fabric.microsoft.com",
                                quote(relative, safe="/"))
            log_contents.append((version, content))
            log_receipts.append(self.file_receipts[-1])
        active = _resolve_delta_active_files(log_contents)
        parquet_receipts = []
        row_count = 0
        generation_ids: set[str] = set()
        aggregate: dict[str, Any] = {}
        for relative, add in sorted(active.items()):
            full_path = f"{table_path}/{relative}"
            content = self._get("onelake.blob.fabric.microsoft.com", quote(full_path, safe="/"))
            if add.get("size") is not None and int(add["size"]) != len(content):
                raise SafetyError(f"Delta size metadata does not match downloaded bytes for {table_name}.")
            try:
                import pyarrow as pa
                import pyarrow.parquet as pq
                parquet = pq.read_table(pa.BufferReader(content))
            except (ImportError, OSError, ValueError) as exc:
                raise SafetyError(f"Active Delta file for {table_name} is not readable Parquet.") from exc
            required = [GOLD_GENERATION_COLUMN] if table_name != "ops.analytics_publish_control" else [
                "ControlKey", "State", "GenerationId", "RunId", "PlanSha256"]
            if table_name in GOLD_EXPECTED_TOTALS:
                required.append("DonationAmountYen")
            if table_name == "gold.donations":
                required.extend(["DataSource", "DonationAmountYen"])
            missing = set(required) - set(parquet.column_names)
            if missing:
                raise SafetyError(f"{table_name} Parquet lacks required columns: {sorted(missing)}")
            if table_name == "ops.analytics_publish_control":
                for column in required:
                    values = parquet[column].to_pylist()
                    aggregate.setdefault(column, []).extend(values)
            else:
                generation_ids.update(str(value) for value in parquet[GOLD_GENERATION_COLUMN].to_pylist()
                                      if value is not None)
                if any(value is None for value in parquet[GOLD_GENERATION_COLUMN].to_pylist()):
                    raise SafetyError(f"{table_name} has null generation values.")
                if table_name in GOLD_EXPECTED_TOTALS:
                    values = parquet["DonationAmountYen"].to_pylist()
                    if any(value is None for value in values):
                        raise SafetyError(f"{table_name} has null donation amounts.")
                    aggregate["DonationAmountYen"] = aggregate.get("DonationAmountYen", 0) + sum(map(int, values))
                if table_name == "gold.donations":
                    sources = parquet["DataSource"].to_pylist()
                    amounts = parquet["DonationAmountYen"].to_pylist()
                    if any(source is None or amount is None for source, amount in zip(sources, amounts)):
                        raise SafetyError("gold.donations has null source or amount values.")
                    by_source = aggregate.setdefault("byDataSource", {})
                    for source, amount in zip(sources, amounts):
                        source = str(source)
                        entry = by_source.setdefault(source, {"rows": 0, "donationAmountYen": 0})
                        entry["rows"] += 1
                        entry["donationAmountYen"] += int(amount)
            if parquet.num_rows < 0:
                raise SafetyError("Parquet reader returned an invalid row count.")
            row_count += parquet.num_rows
            parquet_receipts.append({
                "path": relative, "bytes": len(content), "sha256": self.file_receipts[-1]["sha256"],
                "requestId": self.file_receipts[-1]["requestId"], "rowCount": parquet.num_rows,
            })
        if table_name == "ops.analytics_publish_control":
            control_rows = [
                {column: values[index] for column, values in aggregate.items()}
                for index in range(row_count)
            ]
            return {
                "table": table_name, "deltaVersion": ordered[-1],
                "deltaLogSha256": log_receipts[-1]["sha256"],
                "deltaLogs": [
                    {"version": version, "sha256": receipt["sha256"],
                     "requestId": receipt["requestId"]}
                    for version, receipt in zip(ordered, log_receipts)
                ],
                "files": parquet_receipts, "rowCount": row_count, "controlRows": control_rows,
            }
        return {
            "table": table_name, "deltaVersion": ordered[-1],
            "deltaLogSha256": log_receipts[-1]["sha256"],
            "deltaLogs": [
                {"version": version, "sha256": receipt["sha256"],
                 "requestId": receipt["requestId"]}
                for version, receipt in zip(ordered, log_receipts)
            ],
            "files": parquet_receipts, "rowCount": row_count,
            "generationIds": sorted(generation_ids), **aggregate,
        }


def assess_gold_parquet(
    observations: dict[str, dict[str, Any]], output_tables: list[str],
    expected_job: dict[str, Any],
) -> dict[str, Any]:
    control_table = "ops.analytics_publish_control"
    expected_names = set(output_tables) | {control_table}
    if set(observations) != expected_names:
        raise SafetyError("Fresh OneLake observations do not contain the exact required Delta table set.")
    control = observations[control_table]
    control_rows = control.get("controlRows")
    if not isinstance(control_rows, list) or len(control_rows) != 1 or control.get("rowCount") != 1:
        raise SafetyError("Analytics publish control must contain exactly one Parquet row.")
    if not control.get("files") or any(
            not re.fullmatch(r"[0-9a-f]{64}", str(file.get("sha256", "")))
            or not file.get("requestId") or not file.get("path")
            for file in control["files"]):
        raise SafetyError("Publish control lacks fresh hash-bound OneLake Parquet evidence.")
    if not control.get("deltaLogs") or any(
            not re.fullmatch(r"[0-9a-f]{64}", str(log.get("sha256", "")))
            or not log.get("requestId") for log in control["deltaLogs"]):
        raise SafetyError("Publish control lacks hash-bound OneLake Delta log evidence.")
    row = control_rows[0]
    if (row.get("ControlKey") != GOLD_CONTROL_KEY or row.get("State") != "Ready"
            or row.get("GenerationId") != expected_job.get("generationId")
            or row.get("RunId") != expected_job.get("runId")
            or row.get("PlanSha256") != expected_job.get("planSha256")):
        raise SafetyError("Gold control row is not Ready for the exact completed Notebook05 job.")
    generation = row["GenerationId"]
    for table_name in output_tables:
        table = observations[table_name]
        if table.get("generationIds") != [generation] or table.get("rowCount", 0) < 1:
            raise SafetyError(f"{table_name} is empty, stale, mixed, or from another generation.")
        if not table.get("files") or any(
                not re.fullmatch(r"[0-9a-f]{64}", str(file.get("sha256", "")))
                or not file.get("requestId") or not file.get("path")
                for file in table["files"]):
            raise SafetyError(f"{table_name} lacks fresh hash-bound OneLake Parquet evidence.")
        if not table.get("deltaLogs") or any(
                not re.fullmatch(r"[0-9a-f]{64}", str(log.get("sha256", "")))
                or not log.get("requestId") for log in table["deltaLogs"]):
            raise SafetyError(f"{table_name} lacks hash-bound OneLake Delta log evidence.")
    row_counts = {name: observations[name]["rowCount"] for name in output_tables}
    for table_name, expected in GOLD_EXPECTED_TOTALS.items():
        table = observations[table_name]
        actual = (table["rowCount"], table.get("DonationAmountYen"))
        if actual != expected:
            raise SafetyError(f"{table_name} row count/yen differs from the Gold reconciliation contract.")
    raw = observations["bronze.donation_events_raw"]
    silver = observations["silver.donation_event"]
    quarantine = observations["quarantine.donation_events_rejected"]
    if silver["DonationAmountYen"] + quarantine["DonationAmountYen"] != raw["DonationAmountYen"]:
        raise SafetyError("Silver plus quarantine donation amount does not reconcile to raw.")
    gold = observations["gold.donations"]
    by_source = gold.get("byDataSource")
    if not isinstance(by_source, dict) or {
            key: (value.get("rows"), value.get("donationAmountYen"))
            for key, value in by_source.items()} != GOLD_EXPECTED_BY_SOURCE:
        raise SafetyError("Gold source-level row counts or yen totals differ from contract.")
    if (gold["rowCount"], sum(item["donationAmountYen"] for item in by_source.values())) != GOLD_EXPECTED_OUTPUT_TOTALS:
        raise SafetyError("Gold overall row count or yen total does not reconcile.")
    if by_source["RealtimeIncrement"]["donationAmountYen"] != silver["DonationAmountYen"]:
        raise SafetyError("Gold increment yen does not reconcile to Silver accepted yen.")
    return {
        "generationId": generation, "runId": expected_job["runId"],
        "planSha256": expected_job["planSha256"], "outputTables": len(output_tables),
        "rawRows": raw["rowCount"], "rawYen": raw["DonationAmountYen"],
        "acceptedRows": silver["rowCount"], "acceptedYen": silver["DonationAmountYen"],
        "quarantinedRows": quarantine["rowCount"], "quarantinedYen": quarantine["DonationAmountYen"],
        "goldRows": gold["rowCount"], "goldYen": sum(
            item["donationAmountYen"] for item in by_source.values()),
        "totalsByDataSource": by_source, "tableRowCounts": row_counts,
    }


def validate_owned_gold_lakehouse(
    scope: dict[str, Any], state: dict[str, Any], lakehouse_id: str,
    detail: dict[str, Any],
) -> None:
    if state.get("scopeSha256") != scope_fingerprint(scope):
        raise SafetyError("Deployment state scope fingerprint is missing or inconsistent.")
    if (detail.get("id", lakehouse_id) != lakehouse_id
            or detail.get("folderId") != scope["folderId"]):
        raise SafetyError("Gold source Lakehouse is outside the exact owned folder/workspace.")


def verify_gold_onelake(args: Any, scope: dict[str, Any], state_path: Path,
                        state: dict[str, Any], client: EvidenceClient) -> dict[str, Any]:
    lakehouse = state.get("items", {}).get("lakehouse")
    notebook = state.get("items", {}).get("notebook05")
    if not isinstance(lakehouse, dict) or not isinstance(notebook, dict):
        raise SafetyError("Owned Lakehouse and Notebook05 receipts are required.")
    lakehouse_id = lakehouse.get("id")
    if lakehouse.get("folderId") != scope["folderId"]:
        raise SafetyError("Deployment state Lakehouse receipt is outside the frozen folder.")
    detail = client.request("GET", f"/workspaces/{scope['workspaceId']}/lakehouses/{lakehouse_id}",
                            skill="sqldw-cli").json()
    validate_owned_gold_lakehouse(scope, state, lakehouse_id, detail)
    job_receipt_path = getattr(args, "gold_job_receipt", None)
    if job_receipt_path is None or not Path(job_receipt_path).is_file():
        raise SafetyError("A completed Notebook05 job receipt is required; receipts cannot replace fresh Delta reads.")
    job_receipt = load(Path(job_receipt_path))
    job_id = job_receipt.get("id")
    if not isinstance(job_id, str) or not job_id:
        raise SafetyError("Notebook05 job receipt lacks its completed execution ID.")
    current_job = client.request(
        "GET",
        f"/workspaces/{scope['workspaceId']}/notebooks/{notebook['id']}"
        f"/jobs/execute/instances/{job_id}?beta=true",
        skill="spark-cli",
    ).json()
    properties = current_job.get("properties", {})
    exit_value = properties.get("exitValue", current_job.get("exitValue"))
    if isinstance(exit_value, str):
        try:
            exit_value = json.loads(exit_value)
        except json.JSONDecodeError as exc:
            raise SafetyError("Notebook05 job exitValue is not valid JSON.") from exc
    expected_tables = load(PREVIEW / "provisioning/gold-contract.json")["outputTables"]
    if (current_job.get("id", job_id) != job_id
            or current_job.get("itemId") != notebook.get("id")
            or current_job.get("jobType") != "execute"
            or current_job.get("status") != "Completed"
            or current_job.get("failureReason") is not None
            or not isinstance(exit_value, dict)
            or exit_value.get("mode") != "applied"
            or exit_value.get("outputTables") != expected_tables):
        raise SafetyError("Notebook05 receipt is not a successful apply for the owned notebook.")
    expected_job = {
        "generationId": exit_value.get("generationId"),
        "runId": exit_value.get("runId"),
        "planSha256": exit_value.get("planSha256"),
    }
    if any(not isinstance(value, str) or not value for value in expected_job.values()):
        raise SafetyError("Completed Notebook05 exitValue lacks generation, run, or plan identity.")
    reader = OneLakeDeltaReader(client, lakehouse_id)
    paths = reader.list_table_paths()
    table_names = [*expected_tables, "ops.analytics_publish_control"]
    observations = {
        name: reader.table_observation(name, paths)
        for name in table_names
    }
    latest_paths = reader.list_table_paths()
    for name in table_names:
        schema, table = name.split(".", 1)
        prefix = f"Tables/{schema}/{table}/_delta_log/"
        versions_before = sorted(
            path[len(prefix):] for path in paths if path.startswith(prefix)
            and re.fullmatch(r"\d{20}\.json", path[len(prefix):])
        )
        versions_after = sorted(
            path[len(prefix):] for path in latest_paths if path.startswith(prefix)
            and re.fullmatch(r"\d{20}\.json", path[len(prefix):])
        )
        if not versions_before or versions_before != versions_after:
            raise SafetyError(
                f"{name} Delta snapshot changed during verification "
                f"(before={versions_before}, after={versions_after}); no Gold receipt was written."
            )
    reconciliation = assess_gold_parquet(observations, expected_tables, expected_job)
    totals = [
        {"DataSource": key, "DonationRows": value["rows"],
         "DonationYen": value["donationAmountYen"]}
        for key, value in sorted(observations["gold.donations"]["byDataSource"].items())
    ]
    result = {
        "timestampUtc": now(), "verified": True, "method": "onelake-delta-parquet",
        **reconciliation, "totals": totals, "sqlEndpointObserved": False,
        "nativeAutomaticDeliveryVerified": (
            len(state.get("incrementDeliveries", {})) == 3
            and all(value.get("state") == "native-copy-kql-verified"
                    for value in state.get("incrementDeliveries", {}).values())
        ),
        "deltaVersions": {name: observations[name]["deltaVersion"] for name in observations},
    }
    state["goldVerification"] = result
    save(state_path, state)
    save(args.evidence_dir / "verification/gold-rows.json", {
        "control": observations["ops.analytics_publish_control"],
        "tables": observations, "pathListingRequests": reader.pages,
        "fileRequests": reader.file_receipts,
    })
    save(args.evidence_dir / "verification/gold.json", result)
    return result


def verify_gold(args: Any, method: str = "sql-mcp") -> dict[str, Any]:
    scope = scope_from_document(load(args.scope), args.environment)
    state_path = args.evidence_dir / "deployment-state.json"
    state = load(state_path)
    client = EvidenceClient(scope, args.evidence_dir, credential=getattr(args, "credential", None))
    if method == "onelake-delta-parquet":
        return verify_gold_onelake(args, scope, state_path, state, client)
    if method != "sql-mcp":
        raise SafetyError("Unsupported Gold verification method.")
    lh_id = state["items"]["lakehouse"]["id"]
    detail = client.request("GET", f"/workspaces/{scope['workspaceId']}/lakehouses/{lh_id}",
                            skill="sqldw-cli").json()
    if detail.get("folderId") != scope["folderId"]:
        raise SafetyError("Gold source Lakehouse is outside the frozen folder.")
    endpoint = detail["properties"]["sqlEndpointProperties"]["id"]
    mcp = ReadOnlySqlMcp(client, endpoint)
    contract = load(PREVIEW / "provisioning/gold-contract.json")
    tables = contract["outputTables"]
    control = mcp.query(endpoint, "SELECT TOP 10 ControlKey, RunId, PlanSha256, State, "
                        "GenerationId FROM ops.analytics_publish_control")
    if len(control) != 1 or control[0]["State"] != "Ready" or not control[0]["GenerationId"]:
        raise SafetyError("Notebook05 publication is not uniquely Ready.")
    rows = mcp.query(endpoint, " UNION ALL ".join(
        f"SELECT '{table}' AS TableName, COUNT_BIG(*) AS [RowCount], "
        "COUNT(DISTINCT [_AnalyticsGenerationId]) AS GenerationCount, "
        "MIN([_AnalyticsGenerationId]) AS MinGeneration, MAX([_AnalyticsGenerationId]) AS MaxGeneration "
        f"FROM [{table.split('.')[0]}].[{table.split('.')[1]}]" for table in tables))
    if len(rows) != len(tables) or {r["TableName"] for r in rows} != set(tables):
        raise SafetyError("Not all Notebook05 output tables were observed.")
    if any(int(r["GenerationCount"]) != 1 or r["MinGeneration"] != control[0]["GenerationId"]
           or r["MaxGeneration"] != control[0]["GenerationId"] for r in rows):
        raise SafetyError("Notebook05 output tables contain mixed/empty generations.")
    counts = {r["TableName"]: int(r["RowCount"]) for r in rows}
    if (counts["bronze.donation_events_raw"], counts["silver.donation_event"],
            counts["quarantine.donation_events_rejected"], counts["gold.donations"]) != (15000, 14900, 100, 94900):
        raise SafetyError("Live Notebook05 raw/accepted/quarantine/serving reconciliation failed.")
    totals = mcp.query(endpoint, "SELECT DataSource, COUNT_BIG(*) AS DonationRows, "
                       "SUM(DonationAmountYen) AS DonationYen FROM gold.donations "
                       "GROUP BY DataSource ORDER BY DataSource")
    by_source = {r["DataSource"]: r for r in totals}
    if set(by_source) != {"StaticSeed", "RealtimeIncrement"} or len(totals) != 2:
        raise SafetyError("Gold fact source labels are missing or ambiguous.")
    if int(by_source["StaticSeed"]["DonationRows"]) != 80000 or int(by_source["StaticSeed"]["DonationYen"]) != 1344099000:
        raise SafetyError("Gold static baseline no longer reconciles to the immutable seed.")
    if int(by_source["RealtimeIncrement"]["DonationRows"]) != 14900:
        raise SafetyError("Gold accepted increment count is wrong.")
    result = {"timestampUtc": now(), "verified": True, "generationId": control[0]["GenerationId"],
              "runId": control[0]["RunId"], "planSha256": control[0]["PlanSha256"],
              "outputTables": len(tables), "rawRows": 15000, "acceptedRows": 14900,
              "quarantinedRows": 100, "totals": totals,
              "nativeAutomaticDeliveryVerified": False}
    save(args.evidence_dir / "verification/gold-rows.json", {"control": control, "tables": rows, "totals": totals})
    save(args.evidence_dir / "verification/gold.json", result)
    state["goldVerification"] = result
    save(state_path, state)
    return result


def verify_model(args: Any) -> dict[str, Any]:
    scope = scope_from_document(load(args.scope), args.environment)
    state_path = args.evidence_dir / "deployment-state.json"
    state = load(state_path)
    model = state["items"]["semanticModel"]
    gold = state.get("goldVerification", {})
    if gold.get("verified") is not True:
        raise SafetyError("DAX verification requires the independently observed Gold source totals.")
    client = EvidenceClient(scope, args.evidence_dir, credential=getattr(args, "credential", None))
    current = client.request("GET", f"/workspaces/{scope['workspaceId']}/items/{model['id']}",
                             skill="semantic-model-authoring").json()
    if current.get("folderId") != scope["folderId"]:
        raise SafetyError("Semantic model is outside the frozen folder.")
    query = ('EVALUATE ROW("StaticCount", [静的寄附件数], "StaticYen", [静的寄附総額], '
             '"IncrementCount", [受入増分寄附件数], "IncrementYen", [受入増分寄附総額])')
    body = {"queries": [{"query": query}], "serializerSettings": {"includeNulls": True}}
    url = f"https://api.powerbi.com/v1.0/myorg/groups/{scope['workspaceId']}/datasets/{model['id']}/executeQueries"
    save(args.evidence_dir / "verification/model-dax-request.json",
         {"timestampUtc": now(), "url": url, "body": body, "readOnly": True})
    token = client.credential.get_token("https://analysis.windows.net/powerbi/api/.default").token
    response = client.session.post(url, json=body, headers={"Authorization": "Bearer " + token},
                                   timeout=(20, 180), allow_redirects=False)
    save(args.evidence_dir / "verification/model-dax-response.json",
         {"timestampUtc": now(), "statusCode": response.status_code, "bodyText": response.text})
    if response.status_code != 200:
        raise SafetyError("DAX execution unavailable/failed. Do not change permissions or credentials as a workaround.")
    value = response.json()
    if value.get("error") or any(r.get("error") for r in value.get("results", [])):
        raise SafetyError("DAX returned an error, not successful query data.")
    rows = value["results"][0]["tables"][0].get("rows", [])
    if len(rows) != 1:
        raise SafetyError("DAX did not return exactly one aggregate row.")
    row = {k.strip("[]"): v for k, v in rows[0].items()}
    increment_yen = int(next(r["DonationYen"] for r in gold["totals"] if r["DataSource"] == "RealtimeIncrement"))
    expected = {"StaticCount": 80000, "StaticYen": 1344099000,
                "IncrementCount": 14900, "IncrementYen": increment_yen}
    if row != expected:
        raise SafetyError("Source-owned DAX did not reconcile to observed Lakehouse source totals.")
    result = {"timestampUtc": now(), "verified": True, "values": row,
              "sourceOwnsDax": True, "ontologyMetricsVisible": False,
              "dataAgentDaxExecutionObserved": False}
    state["modelDaxVerification"] = result
    save(state_path, state)
    save(args.evidence_dir / "verification/model-dax.json", result)
    return result
