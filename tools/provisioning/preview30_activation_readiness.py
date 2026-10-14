"""Read actual backend readiness before creating a watched increment.

This diagnostic adapter uses the current first-party Fabric web client's native
Semantics and GraphQL contracts. These are not public documented Fabric REST
APIs. A changed, unavailable or unhealthy response blocks upload; it does not
trigger a fallback. Native action credentials must already be configured using
Edit action / Apply / Save. No rule/action writes or Pipeline invocations occur.
MWC tokens remain in memory. Reuse the deployment session's explicit proxy and
CA configuration without enabling ambient authentication or disabling TLS.
"""
from __future__ import annotations
import base64
import json
import time
from urllib.parse import urlsplit

from activation_runtime import guid, parse_time
from preview30_runtime import SafetyError, digest, now, save

PBI_SCOPE = "https://analysis.windows.net/powerbi/api/.default"
CLUSTER_URL = "https://api.powerbi.com/powerbi/globalservice/v201606/clusterDetails"
ACTION_STATE_QUERY = """
  query getFabricItemActionRefreshTokenState($uniqueIdentifier: String) {
    fabricItemAction(uniqueIdentifier: $uniqueIdentifier) {
      system {
        refreshToken {
          state
          _id
        }
      }
    }
  }
"""
CONTRACT = "first-party-reflex-native-readiness/2026-10-14"


def require(value, message):
    if not value:
        raise SafetyError(message)


def approved_origin(value):
    require(isinstance(value, str), "Native discovery did not return an origin.")
    parsed = urlsplit(value)
    require(parsed.scheme == "https" and parsed.hostname
            and parsed.hostname.endswith((".analysis.windows.net", ".pbidedicated.windows.net"))
            and parsed.port is None and not parsed.username and not parsed.password
            and parsed.path in {"", "/"} and not parsed.query and not parsed.fragment,
            "Native discovery returned an unsupported origin.")
    return value.rstrip("/")


def check_responses(state_body, health_body, action_body, rule_id, delay):
    require(all(isinstance(value, dict) for value in (state_body, health_body, action_body)),
            "Native readiness response shape changed. No file uploaded.")
    state = state_body.get("timeSeriesViewState", {})
    require(isinstance(state, dict) and state.get("type") == "rule" and state.get("backendRunningState") == "Running"
            and state.get("isRuleInSync") is True
            and type(state.get("ruleDelayToleranceInMs")) is int
            and state["ruleDelayToleranceInMs"] == delay
            and state.get("watermarkType") == "DelayTolerance",
            "Actual Activator backend is not Running and in sync at the configured tolerance. No file uploaded.")
    health = health_body.get("rules")
    require(isinstance(health, list) and len(health) == 1 and isinstance(health[0], dict)
            and health[0].get("ruleId") == rule_id and health[0].get("notifications") == [],
            "Native rule health is unavailable, incomplete or reports notifications. No file uploaded.")
    actions = action_body.get("fabricItemAction")
    require(isinstance(actions, list) and len(actions) == 1 and isinstance(actions[0], dict),
            "Native action credential response shape changed. No file uploaded.")
    system = actions[0].get("system")
    refresh = system.get("refreshToken") if isinstance(system, dict) else None
    require(isinstance(refresh, dict) and refresh.get("state") == "Initialized",
            "Native action credentials are not Initialized; use Edit action / Apply / Save. No file uploaded.")
    return {"backendRunningState": "Running", "isRuleInSync": True,
            "ruleDelayToleranceInMs": delay, "healthNotifications": [],
            "actionRefreshTokenState": "Initialized"}


def capture_readiness(d, activator, rule_id):
    """Fresh reads only; no configured-state substitute, sleep or automatic retry."""
    wid, aid, rule_id = guid(d.scope["workspaceId"]), guid(activator["id"]), guid(rule_id)
    receipt = d.state.get("nativeLifecycle", {})
    require(receipt.get("action") == "start" and receipt.get("status") == "verified"
            and receipt.get("result", {}).get("state") == "armed_unverified",
            "Formal native Start must precede backend readiness capture.")
    require(parse_time(receipt.get("timestampUtc")) <= parse_time(now()), "Formal Start time is invalid.")
    private = d.evidence / "activation" / ("readiness-" + str(time.time_ns()))
    definition = d.definition(aid, skill="activator-cli")
    parts = [p for p in definition["parts"] if p["path"] == "ReflexEntities.json"]
    require(len(parts) == 1, "Actual native definition is incomplete.")
    entities = json.loads(base64.b64decode(parts[0]["payload"]))
    rules = [e for e in entities if e.get("payload", {}).get("definition", {}).get("type") == "Rule"]
    actions = [e for e in entities if e.get("type") == "fabricItemAction-v1"]
    require(len(rules) == len(actions) == 1 and rules[0]["uniqueIdentifier"] == rule_id,
            "Actual native rule/action scope changed.")
    settings = rules[0]["payload"]["definition"].get("settings", {})
    delay = settings.get("delayToleranceMs")
    require(settings.get("shouldRun") is True and settings.get("shouldApplyRuleOnUpdate") is False
            and type(delay) is int and delay >= 120000, "Actual rule settings are not ready.")
    action_id = guid(actions[0]["uniqueIdentifier"])
    target = actions[0]["payload"]["fabricItem"]
    require(target.get("workspaceId") == wid and target.get("itemId") == d.state["items"]["pipeline"]["id"],
            "Actual native action targets a different Pipeline.")
    save(private / "definition.json", definition)
    workspace = d.client.request("GET", d.prefix, skill="activator-cli").json()
    require(workspace.get("id") == wid and workspace.get("displayName") == d.scope["workspaceName"],
            "Fresh workspace identity differs.")
    capacity = guid(workspace.get("capacityId"))
    session = d.client.session
    require(session.verify is not False, "Native diagnostics require verified TLS.")
    # Do not replace this session: its caller configured the managed proxy/CA.
    session.trust_env = False

    def request(name, method, url, headers, body=None, *, token_response=False):
        save(private / (name + "-request.json"), {"atUtc": now(), "method": method, "url": url, "body": body})
        try:
            response = session.request(method, url, json=body, headers=headers,
                                       timeout=(20, 120), allow_redirects=False)
        except Exception as error:
            save(private / (name + "-transport.json"), {"atUtc": now(), "exceptionType": type(error).__name__,
                                                       "retryPerformed": False})
            raise SafetyError("Native readiness transport failed; no file uploaded.") from error
        try:
            value = response.json()
        except ValueError:
            value = None
        if token_response:
            # Never retain the raw body, Authorization header or credential.
            safe = {"tokenPresent": isinstance(value, dict) and bool(value.get("Token")),
                    "targetUriHost": value.get("TargetUriHost") if isinstance(value, dict) else None,
                    "capacityObjectId": value.get("CapacityObjectId") if isinstance(value, dict) else None,
                    "tokenPersisted": False}
        else:
            safe = {"body": value, "nativeResponseUnmodified": True}
            if value is None:
                safe["bodyText"] = response.text
        save(private / (name + "-response.json"), {"atUtc": now(), "status": response.status_code,
                                                   "retryPerformed": False, **safe})
        require(response.status_code == 200 and isinstance(value, dict)
                and not value.get("error") and not value.get("errors"),
                "Native readiness response failed or changed; inspect private evidence. No file uploaded.")
        return value

    bearer = {"Authorization": "Bearer " + d.client.credential.get_token(PBI_SCOPE).token,
              "Content-Type": "application/json"}
    cluster = request("cluster-discovery", "GET", CLUSTER_URL, bearer)
    origin = approved_origin(cluster.get("clusterUrl"))
    token = request("mwc", "POST", origin + "/metadata/v201606/generatemwctoken", bearer,
                    {"artifactObjectIds": [aid], "workloadType": "Reflex", "workspaceObjectId": wid},
                    token_response=True)
    require(isinstance(token.get("Token"), str) and bool(token["Token"])
            and token.get("CapacityObjectId") == capacity,
            "Native token capacity differs from the fresh owned workspace.")
    host = token.get("TargetUriHost")
    require(isinstance(host, str) and "/" not in host, "Native token returned an invalid host.")
    base = approved_origin("https://" + host) + "/webapi/capacities/" + capacity + "/workloads/Reflex"
    headers = {"Authorization": "Bearer " + token["Token"], "Content-Type": "application/json"}
    prefix = base + "/Semantics/Automatic/v1/workspaces/" + wid + "/reflexes/" + aid
    state = request("rule-state", "POST", prefix + "/semantics/analyze?engineEnabled=true", headers,
                    {"timeSeriesViewId": rule_id, "options": {"includeRuleState": True}})
    health = request("rule-health", "POST", prefix + "/semantics/health", headers, {"rules": []})
    action = request("action-credentials-state", "POST", base + "/Config/Automatic/GraphQL", headers,
                     {"query": ACTION_STATE_QUERY, "operationName": "getFabricItemActionRefreshTokenState",
                      "variables": json.dumps({"uniqueIdentifier": action_id})})
    checked = check_responses(state, health, action.get("data", {}), rule_id, delay)
    require(d.definition(aid, skill="activator-cli") == definition,
            "Native rule definition changed during readiness capture. No file uploaded.")
    result = {"atUtc": now(), "contract": CONTRACT, "scopeSha256": d.state["scopeSha256"],
              "workspaceId": wid, "activatorId": aid, "ruleId": rule_id,
              "formalStartAtUtc": receipt["timestampUtc"], "definitionSha256": digest(definition),
              **checked, "automaticDeliveryVerified": False, "cloudMutationsPerformed": False,
              "tokenPersisted": False, "priorEventExhaustionProven": False,
              "evidence": str(private),
              "note": "Readiness is not delivery proof. Verify the actual event, activation, new Completed job, Copy and KQL before the next file."}
    save(private / "result.json", result)
    return result
