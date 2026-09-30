"""Read-only native SQL MCP checks; no fabricated rows or inferred readiness."""
from __future__ import annotations
import csv
import io
import json
from pathlib import Path
import re
import time
from typing import Any

from preview30_runtime import EvidenceClient, SafetyError, PREVIEW, load, now, save, scope_from_document
from workshop_runtime import EXPECTED_TABLES


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


def verify_gold(args: Any) -> dict[str, Any]:
    scope = scope_from_document(load(args.scope), args.environment)
    state_path = args.evidence_dir / "deployment-state.json"
    state = load(state_path)
    client = EvidenceClient(scope, args.evidence_dir, credential=getattr(args, "credential", None))
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
