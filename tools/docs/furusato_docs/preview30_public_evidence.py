"""Reviewed, sanitized source-owned projection; private originals never enter it."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path, PurePosixPath

from PIL import Image

from . import preview30_evaluation as evaluation
from . import preview30_evidence as private

SCHEMA = "furusato-preview30-public-evidence/v1"
DEFAULT_RELATIVE = Path("docs") / "assets" / "v3-preview-evidence" / "manifest.json"
SCOPE = "historical-observed-run"
ROOT_FIELDS = {"schemaVersion", "scope", "approved", "reviewedAt", "reviewer", "freezeStatus", "captures", "labs", "originalSuiteRuns", "evaluationReport"}
FREEZE_STATUSES = {"awaiting-final-consumer-proof", "evidence-frozen-awaiting-runtime-seal", "frozen-for-build"}
CAPTURE_FIELDS = {"id", "file", "sha256", "originalSha256", "capturedAt", "reviewedAt", "actualUI", "experience", "privacyReview", "completionEvidence", "caption"}
LAB_FIELDS = {"status", "reason", "evidenceIds", "executionAndReadbackObserved", "functionalBindingVerified", "intent", "invariants", "approvedDelta", "observedDelta", "knownIssue"}
RUN_FIELDS = {"id", "label", "observedAt", "questionCount", "conditionCount", "submittedQuestions", "preblockedQuestions", "counts", "failureCounts", "independentExecutionTraces", "freshBackendProof", "promoted", "accepted", "summary"}
RUN_OPTIONAL_FIELDS = {"notApplicableReason", "method"}
VERDICTS = {"pass", "fail", "executionUnverified", "blocked", "notApplicable"}
PRIVATE_TEXT = re.compile(
    private.PRIVATE_TEXT.pattern + r"|https?://|\\\\[^\\\s]+\\|/(?:Users|home|tmp|mnt|var)/|"
    r"\b(?:Bearer\s+\S+|eyJ[A-Za-z0-9_-]{20,}|AccountKey=|SharedAccessSignature=)", re.I
)


def exact_fields(value, allowed, field, required=()):
    if not isinstance(value, dict) or set(value) - allowed or not set(required).issubset(value):
        raise ValueError(field + " contains unknown/private fields or is incomplete")


def safe_text(text, field):
    if not isinstance(text, str) or not text.strip() or len(text) > 5000 or PRIVATE_TEXT.search(text):
        raise ValueError(field + " is empty, oversized or contains private text")
    return text


def pair(value, field):
    exact_fields(value, {"ja", "en"}, field, {"ja", "en"})
    return {language: safe_text(value[language], field) for language in ("ja", "en")}


def timestamp(value, field):
    if not isinstance(value, str) or len(value) > 50:
        raise ValueError(field + " needs a timezone-aware timestamp")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError(field + " needs a timezone-aware timestamp")
    return parsed


def public_strings(value, field):
    if isinstance(value, str):
        safe_text(value, field)
    elif isinstance(value, dict):
        for child in value.values():
            public_strings(child, field)
    elif isinstance(value, list):
        for child in value:
            public_strings(child, field)


def integer(value, field, maximum=84):
    if type(value) is not int or not 0 <= value <= maximum:
        raise ValueError("Invalid aggregate count: " + field)
    return value


def run_method(value, submitted, traced_questions, fresh_backend):
    fields = {"surface", "transport", "stage", "runtime", "recordedModel", "judgment", "distinctBackendConversationsProven", "sourceExecutions", "causalAbClaimed"}
    exact_fields(value, fields, "run method", fields)
    if value["surface"] not in {"published-mcp", "native-ui"} or value["transport"] not in {"mcp", "responses"}:
        raise ValueError("Unknown evaluation surface/transport; diagnostics are separate records")
    if value["judgment"] not in {"recorded-rubric-assessment", "manual-fixed-rubric-offline"}:
        raise ValueError("Unknown fixed-rubric judgment method")
    for key in ("stage", "runtime", "recordedModel"):
        if value[key] is not None:
            safe_text(value[key], "method " + key)
    distinct = integer(value["distinctBackendConversationsProven"], "distinct backend conversations", submitted)
    if fresh_backend and distinct != submitted:
        raise ValueError("Fresh-backend proof requires distinct conversation proof for every submitted question")
    executions = value["sourceExecutions"]
    if executions is not None:
        exact_fields(executions, {"sql", "gql", "kql"}, "source executions", {"sql", "gql", "kql"})
        if sum(integer(executions[key], key, 1000) for key in executions) < traced_questions:
            raise ValueError("Execution-call counts cannot be smaller than independently traced question slots")
    elif traced_questions:
        raise ValueError("Traced questions require actual execution counts in the method record")
    if value["causalAbClaimed"] is not False:
        raise ValueError("These differently routed/transported runs do not establish a causal A/B")
    return value


def suite_runs(values):
    if not isinstance(values, list) or len(values) > 10:
        raise ValueError("Original-suite runs must be a bounded aggregate list")
    result = []
    seen = set()
    for value in values:
        exact_fields(value, RUN_FIELDS | RUN_OPTIONAL_FIELDS, "original-suite run", RUN_FIELDS)
        ident = value["id"]
        if not isinstance(ident, str) or not re.fullmatch(r"[a-z][a-z0-9-]{0,63}", ident) or ident in seen:
            raise ValueError("Duplicate/non-portable original-suite run id")
        safe_text(ident, "run id")
        seen.add(ident)
        pair(value["label"], "run label")
        pair(value["summary"], "run summary")
        timestamp(value["observedAt"], "run observedAt")
        if (integer(value["questionCount"], "questionCount", 10), integer(value["conditionCount"], "conditionCount")) != (10, 84):
            raise ValueError("Original ten/84 denominators cannot be replaced")
        submitted = integer(value["submittedQuestions"], "submittedQuestions", 10)
        blocked = integer(value["preblockedQuestions"], "preblockedQuestions", 10)
        if submitted + blocked != 10:
            raise ValueError("All original question slots must remain in the denominator")
        exact_fields(value["counts"], VERDICTS, "run counts", VERDICTS - {"notApplicable"})
        counts = {key: integer(value["counts"].get(key, 0), key) for key in sorted(VERDICTS)}
        if sum(counts.values()) != 84:
            raise ValueError("All 84 conditions must remain in the denominator")
        if counts["notApplicable"]:
            pair(value.get("notApplicableReason"), "not-applicable rationale")
        elif "notApplicableReason" in value:
            pair(value["notApplicableReason"], "not-applicable rationale")
        exact_fields(value["failureCounts"], {"content", "nativeAcceptance"}, "failureCounts", {"content", "nativeAcceptance"})
        failures = {key: integer(value["failureCounts"][key], key) for key in ("content", "nativeAcceptance")}
        if sum(failures.values()) != counts["fail"]:
            raise ValueError("Content/native acceptance failures must reconcile to FAIL")
        traces = integer(value["independentExecutionTraces"], "independentExecutionTraces", submitted)
        if any(type(value[key]) is not bool for key in ("freshBackendProof", "promoted", "accepted")):
            raise ValueError("Run proof/promotion/acceptance flags must be explicit booleans")
        if value["accepted"] and (counts["pass"] < 1 or counts["pass"] + counts["notApplicable"] != 84 or submitted != 10 or traces != 10 or not value["freshBackendProof"]):
            raise ValueError("Aggregate agreement without complete execution proof is not original-suite acceptance")
        if "method" in value:
            run_method(value["method"], submitted, traces, value["freshBackendProof"])
        result.append({**value, "counts": counts, "failureCounts": failures})
    return result


def public_file(base: Path, value: str, expected: str, root: Path):
    if not isinstance(value, str) or "\\" in value or ":" in value:
        raise ValueError("Public evidence uses portable relative content-addressed paths")
    relative = PurePosixPath(value)
    if relative.is_absolute() or relative.parts != ("captures", expected + ".png"):
        raise ValueError("Public capture must be captures/<sanitized-sha256>.png")
    path = (base / value).resolve()
    if not path.is_relative_to(base.resolve()) or not path.is_relative_to(root.resolve()) or not path.is_file():
        raise ValueError("Public capture escapes the approved source projection or is missing")
    if private.digest(path) != expected:
        raise ValueError("Public sanitized-image digest mismatch")
    return path


def load(path: Path, *, root: Path | None = None):
    root = (root or private.ROOT).resolve()
    path = path.resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise ValueError("Public projection must be an existing file inside the clean source root")
    data = json.loads(path.read_text(encoding="utf-8"))
    required_root = {"schemaVersion", "scope", "approved", "reviewedAt", "reviewer", "captures", "labs"}
    exact_fields(data, ROOT_FIELDS, "public projection", required_root)
    if data["schemaVersion"] != SCHEMA or data["scope"] != SCOPE or data["approved"] is not True:
        raise ValueError("Only an explicitly approved historical public projection may be loaded")
    freeze_status = data.get("freezeStatus", "awaiting-final-consumer-proof")
    if freeze_status not in FREEZE_STATUSES:
        raise ValueError("Unknown source-evidence freeze status")
    reviewed_at = timestamp(data["reviewedAt"], "reviewedAt")
    if not isinstance(data["reviewer"], str) or not re.fullmatch(r"[a-z][a-z0-9-]{0,63}", data["reviewer"]):
        raise ValueError("Use a portable reviewer role, not a person/account identifier")
    safe_text(data["reviewer"], "reviewer role")
    requested = {item["id"]: item for item in private.requests()}
    if not isinstance(data["captures"], list):
        raise ValueError("Public captures must be a list")
    captures = {}
    for capture in data["captures"]:
        exact_fields(capture, CAPTURE_FIELDS, "public capture", CAPTURE_FIELDS)
        ident = capture["id"]
        if ident not in requested or ident in captures:
            raise ValueError("Unknown/duplicate public capture id")
        if capture["actualUI"] is not True or capture["experience"] != "new" or capture["privacyReview"] != "accounts-urls-ids-paths-removed":
            raise ValueError("Only actual privacy-reviewed new UI may be published")
        if type(capture["completionEvidence"]) is not bool:
            raise ValueError("Completion evidence must be explicit")
        for key in ("sha256", "originalSha256"):
            if not isinstance(capture[key], str) or not private.SHA.fullmatch(capture[key]):
                raise ValueError("Invalid public capture provenance digest")
        captured_at = timestamp(capture["capturedAt"], "capturedAt")
        capture_review = timestamp(capture["reviewedAt"], "capture reviewedAt")
        if captured_at > capture_review or capture_review > reviewed_at:
            raise ValueError("Capture/review chronology is inconsistent")
        caption = pair(capture["caption"], "public caption")
        image_path = public_file(path.parent, capture["file"], capture["sha256"], root)
        with Image.open(image_path) as image:
            if image.format != "PNG":
                raise ValueError("Public evidence requires the reviewed PNG bytes")
            image.verify()
        with Image.open(image_path) as image:
            if image.getexif() or any(isinstance(value, (str, bytes)) for value in image.info.values()):
                raise ValueError("Strip image metadata before approving a public projection")
            if capture["completionEvidence"]:
                if image.width < 600 or image.height < 250:
                    raise ValueError("Completion UI capture too small to be legible")
            elif min(image.size) < 320 or max(image.size) < 500 or image.width * image.height < 200000:
                raise ValueError("Partial UI excerpt too small even for orientation")
        captures[ident] = {
            "path": image_path, "sha256": capture["sha256"], "caption": caption,
            "capturedAt": capture["capturedAt"], "originalSha256": capture["originalSha256"],
            "completionEvidence": capture["completionEvidence"],
        }
    if not isinstance(data["labs"], dict) or set(data["labs"]) != {item["lab"] for item in requested.values()}:
        raise ValueError("Public projection must list every requested lab and no unknown labs")
    for lab, value in data["labs"].items():
        exact_fields(value, LAB_FIELDS, "public lab", {"status", "reason", "evidenceIds"})
        pair(value["reason"], "public lab reason")
        if "invariants" in value:
            permitted = set(private.ADDITIVE_INVARIANTS if lab == "copilot-additive-entity" else private.ACT_INVARIANTS)
            if not isinstance(value["invariants"], dict) or set(value["invariants"]) - permitted or any(type(v) is not bool for v in value["invariants"].values()):
                raise ValueError("Public invariants contain unknown/private fields")
        for key in ("executionAndReadbackObserved", "functionalBindingVerified"):
            if key in value and type(value[key]) is not bool:
                raise ValueError("Public lab proof flags must be booleans")
        if lab != "copilot-additive-entity" and any(key in value for key in ("approvedDelta", "observedDelta")):
            raise ValueError("Typed additive delta belongs only to the additive lab")
        if "intent" in value or "approvedDelta" in value or "observedDelta" in value:
            if lab == "copilot-additive-entity":
                private.validate_additive(value)
            elif lab != "copilot-act" or value["intent"] != {"kind": "metadata-only"}:
                raise ValueError("Unknown public intent")
    labs, complete = private.validate_labs(data, requested, captures)
    runs = suite_runs(data.get("originalSuiteRuns", []))
    if any(timestamp(run["observedAt"], "run observedAt") > reviewed_at for run in runs):
        raise ValueError("A run observed after the public review cannot be approved by that review")
    if labs["evaluation"]["status"] == "passed" and not any(run["accepted"] for run in runs):
        raise ValueError("Evaluation cannot pass while all supplied original-suite runs are unaccepted")
    projected_evaluation = None
    if data.get("evaluationReport") is not None:
        projected_evaluation = evaluation.project(data["evaluationReport"])
        if projected_evaluation != data["evaluationReport"]:
            raise ValueError("Public evaluator projection contains private/unapproved fields")
        public_strings(projected_evaluation, "public evaluator text")
        if timestamp(projected_evaluation["generated_at_utc"], "evaluator timestamp") > reviewed_at:
            raise ValueError("Evaluator snapshot postdates the public review")
    return {
        "captures": captures, "labs": labs, "complete": complete,
        "scope": SCOPE, "publicProjection": True, "reviewedAt": data["reviewedAt"],
        "freezeStatus": freeze_status,
        "projectionSha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "originalSuiteRuns": runs, "evaluationProjection": projected_evaluation,
    }


def resolve(private_path=None, public_path=None, *, root=None):
    root = root or private.ROOT
    if private_path is not None and public_path is not None:
        raise ValueError("Choose private evidence OR an approved public projection, never both")
    if private_path is not None:
        return private.load(private_path)
    if public_path is not None:
        return load(public_path, root=root)
    default = root / DEFAULT_RELATIVE
    return load(default, root=root) if default.exists() else private.load()
