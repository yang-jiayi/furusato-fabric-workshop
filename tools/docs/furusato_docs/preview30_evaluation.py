"""Safe projection of the evaluator's existing furusato-preview30-report/v1.

Never reads a held-out corpus, runs scoring, or publishes report context/evidence.
"""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from datetime import datetime
from pathlib import Path

SCHEMA = "furusato-preview30-report/v1"
STATES = ("planned", "implemented", "deployed", "pass", "fail", "blocked", "unsupported", "unverified")
SUPPORT = {"pending", "supported", "unsupported"}
CATEGORIES = {"ai", "capability", "data", "document", "structural"}
COUNTS = (
    "case_count", "requested_slots", "supported_requested_slots",
    "supported_pass", "supported_fail", "supported_missing_evidence",
)
AI_COUNTS = (
    "requested_questions", "supported_requested_questions", "scored_questions",
    "pass", "missing_supported_questions",
)
INVENTORY_FIELDS = ("case_id", "repeat", "category", "critical", "state", "support")


def _integer(value, name, minimum=0):
    if type(value) is not int or value < minimum:
        raise ValueError("Invalid evaluator count: " + name)
    return value


def project(raw):
    if raw.get("schema_version") != SCHEMA:
        raise ValueError("Use the evaluator's normalized report/v1, never a manifest or held-out corpus")
    stamp = raw["generated_at_utc"]
    if not isinstance(stamp, str) or len(stamp) > 50 or datetime.fromisoformat(stamp.replace("Z", "+00:00")).tzinfo is None:
        raise ValueError("Evaluator snapshot needs its original timezone-aware timestamp")
    safe = {"schema_version": SCHEMA, "generated_at_utc": stamp}
    safe.update({name: _integer(raw[name], name) for name in COUNTS})
    states = raw["state_counts"]
    if set(states) != set(STATES):
        raise ValueError("Evaluator state vocabulary changed; review before publication")
    safe["state_counts"] = {name: _integer(states[name], name) for name in STATES}
    inventory = []
    for entry in raw["inventory"]:
        row = {name: entry[name] for name in INVENTORY_FIELDS}
        if not isinstance(row["case_id"], str) or not re.fullmatch(r"[A-Z][A-Z0-9_-]{0,63}", row["case_id"]):
            raise ValueError("Only portable public case identifiers may be projected")
        _integer(row["repeat"], "repeat", 1)
        if row["category"] not in CATEGORIES or row["state"] not in STATES or row["support"] not in SUPPORT or type(row["critical"]) is not bool:
            raise ValueError("Invalid evaluator inventory row")
        inventory.append(row)
    if len(inventory) != safe["requested_slots"] or len({(r["case_id"], r["repeat"]) for r in inventory}) != len(inventory):
        raise ValueError("Evaluator requested-slot inventory is incomplete or duplicated")
    if len({r["case_id"] for r in inventory}) != safe["case_count"]:
        raise ValueError("Evaluator case count does not match its inventory")
    counted = Counter(row["state"] for row in inventory)
    if any(counted[state] != safe["state_counts"][state] for state in STATES):
        raise ValueError("Evaluator state counts do not match inventory")
    supported = [row for row in inventory if row["support"] == "supported"]
    if len(supported) != safe["supported_requested_slots"]:
        raise ValueError("Evaluator supported denominator does not match inventory")
    if (
        sum(r["state"] == "pass" for r in supported) != safe["supported_pass"]
        or sum(r["state"] == "fail" for r in supported) != safe["supported_fail"]
        or sum(r["state"] not in {"pass", "fail"} for r in supported) != safe["supported_missing_evidence"]
    ):
        raise ValueError("Evaluator supported-state aggregate is inconsistent")
    safe["inventory"] = inventory
    ai = raw["ai"]
    safe_ai = {name: _integer(ai[name], "ai." + name) for name in AI_COUNTS}
    withheld = ai["aggregate_withheld_until_supported_inventory_complete"]
    if type(withheld) is not bool:
        raise ValueError("Evaluator aggregate-withheld flag must be explicit")
    accuracy = ai["accuracy"]
    if accuracy is not None and (type(accuracy) not in (int, float) or not math.isfinite(accuracy) or not 0 <= accuracy <= 1):
        raise ValueError("Evaluator accuracy must be null or a valid ratio")
    if withheld and accuracy is not None:
        raise ValueError("A withheld aggregate must not publish an accuracy")
    if not 0 <= safe_ai["pass"] <= safe_ai["scored_questions"] <= safe_ai["supported_requested_questions"] <= safe_ai["requested_questions"]:
        raise ValueError("Evaluator AI denominators are inconsistent")
    if safe_ai["missing_supported_questions"] != safe_ai["supported_requested_questions"] - safe_ai["scored_questions"]:
        raise ValueError("Evaluator AI missing-evidence count is inconsistent")
    if safe_ai["scored_questions"] == 0 and accuracy is not None:
        raise ValueError("Unscored AI must not have an accuracy")
    if any(row["category"] == "ai" and row["support"] == "pending" for row in inventory) and not withheld:
        raise ValueError("Pending AI applicability requires a withheld aggregate")
    if (accuracy is None) != withheld:
        raise ValueError("Evaluator accuracy and withheld flag disagree")
    if accuracy is not None and abs(accuracy - safe_ai["pass"] / safe_ai["scored_questions"]) > 1e-12:
        raise ValueError("Evaluator accuracy does not match its stated scored denominator")
    safe_ai.update({
        "accuracy": accuracy,
        "aggregate_withheld_until_supported_inventory_complete": withheld,
    })
    safe["ai"] = safe_ai
    original = raw["original_inventory"]
    if (original.get("question_count"), original.get("condition_count")) != (10, 84) or original.get("independent_hidden") is not False:
        raise ValueError("The original public ten/84 summary must remain unchanged")
    if original.get("state") not in STATES:
        raise ValueError("Invalid original inventory state")
    safe["original_inventory"] = {
        key: original[key] for key in ("question_count", "condition_count", "independent_hidden", "state")
    }
    return safe


def load(path: Path | None):
    if path is None:
        return None
    root = Path(__file__).resolve().parents[3]
    path = path.resolve()
    if path.is_relative_to(root):
        raise ValueError("Read the evaluator report from private staging, not a public source path")
    return project(json.loads(path.read_text(encoding="utf-8")))
