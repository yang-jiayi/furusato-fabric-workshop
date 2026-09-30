"""Strict private-to-public evidence boundary for the new-experience guide."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
REQUESTS = ROOT / "tools" / "docs" / "assets" / "preview30-capture-requests.json"
STATUSES = {"passed", "blocked", "unsupported", "not-run", "failed", "observed", "unverified"}
ACT_INVARIANTS = (
    "lineageIdsPreserved", "entityPropertySetPreserved", "propertyTypesPreserved",
    "keysPreserved", "bindingsPreserved", "inheritancePreserved",
    "sharedPropertyReferencesPreserved", "onlyApprovedMetadataDelta",
)
ADDITIVE_INVARIANTS = (
    "planLeftDefinitionUnchanged", "existingPartsExceptModelByteIdentical",
    "existingIdsTypesKeysBindingsSharedRefsInheritancePreserved",
    "modelOnlyAddsApprovedReference", "newEntityMatchesApprovedIntent",
    "sourceDataUnchanged",
)
SHA = re.compile(r"^[0-9a-f]{64}$")
PRIVATE_TEXT = re.compile(
    r"\b[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\b|"
    r"https?://(?:app\.fabric|app\.powerbi)|[A-Z]:[\\/]|"
    r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", re.I
)


def requests() -> list[dict]:
    return json.loads(REQUESTS.read_text(encoding="utf-8"))["requests"]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _pair(value, field: str) -> dict[str, str]:
    if not isinstance(value, dict) or set(value) != {"ja", "en"}:
        raise ValueError(f"{field} requires explicit ja/en text")
    for text in value.values():
        if not isinstance(text, str) or not text.strip() or PRIVATE_TEXT.search(text):
            raise ValueError(f"{field} is empty or contains private identifiers")
    return value


def _private_file(base: Path, value: str) -> Path:
    path = (base / value).resolve()
    if path.is_relative_to(ROOT):
        raise ValueError("Original/sanitized evidence must remain outside the public source tree")
    if not path.is_relative_to(base.resolve()):
        raise ValueError("Evidence path escapes its private manifest directory")
    if not path.is_file():
        raise ValueError("Evidence file is missing: " + path.name)
    return path


def validate_additive(value: dict) -> None:
    intent = value.get("intent", {})
    if set(intent) != {"kind", "entityName", "propertyName", "dataType", "keyless", "unbound"}:
        raise ValueError("Additive entity pass requires an explicit typed intent")
    if intent["kind"] != "add-unbound-keyless-entity" or intent["dataType"] != "string" or intent["keyless"] is not True or intent["unbound"] is not True:
        raise ValueError("Unsupported additive intent; this lab adds one unbound keyless String property")
    for field in ("entityName", "propertyName"):
        if not isinstance(intent[field], str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,63}", intent[field]):
            raise ValueError("Additive intent requires portable business names")
    if re.search(r"(?:Demo|Test|Sample|Example)$", intent["entityName"], re.I):
        raise ValueError("Use business entity names, not experimental suffixes")
    expected = {
        "addedParts": [f"entities/{intent['entityName']}.tmdl"],
        "removedParts": [], "changedExistingParts": ["model.tmdl"],
        "modelReferencesAdded": [intent["entityName"]],
        "newProperties": [{"name": intent["propertyName"], "dataType": intent["dataType"]}],
    }
    if value.get("approvedDelta") != expected or value.get("observedDelta") != expected:
        raise ValueError("Additive pass requires the exact approved delta, not a relationship or extra changes")
    if any(value.get("invariants", {}).get(name) is not True for name in ADDITIVE_INVARIANTS):
        raise ValueError("Additive pass requires strict preservation of existing parts and the exact approved delta")


def validate_labs(data: dict, required: dict, captures: dict) -> tuple[dict, bool]:
    result = {}
    covered = []
    for lab in sorted({item["lab"] for item in required.values()}):
        value = data.get("labs", {}).get(lab)
        if not value or value.get("status") not in STATUSES:
            raise ValueError("Each requested lab needs an explicit status: " + lab)
        reason = _pair(value.get("reason"), "lab reason")
        identifiers = value.get("evidenceIds", [])
        if not isinstance(identifiers, list) or any(not isinstance(ident, str) for ident in identifiers) or len(set(identifiers)) != len(identifiers):
            raise ValueError("Evidence IDs must be a unique list: " + lab)
        if any(ident not in captures or required[ident]["lab"] != lab for ident in identifiers):
            raise ValueError("Lab refers to missing or another lab's evidence: " + lab)
        if value["status"] == "observed" and not identifiers:
            raise ValueError("Observed UI status requires an actual reviewed capture: " + lab)
        if value["status"] == "passed":
            if lab == "entities" and value.get("functionalBindingVerified") is not True:
                raise ValueError("Entity/binding pass requires functional Instances/query readback, not schema or column labels")
            if lab == "copilot-act":
                if value.get("intent", {"kind": "metadata-only"}) != {"kind": "metadata-only"}:
                    raise ValueError("Metadata-only Act cannot be passed by an additive intent")
                if any(value.get("invariants", {}).get(name) is not True for name in ACT_INVARIANTS):
                    raise ValueError("Copilot Act pass requires every strict readback invariant, including shared-property references")
            if lab == "copilot-additive-entity":
                validate_additive(value)
            needed = {item["id"] for item in required.values() if item["lab"] == lab and item.get("completionRequired", True)}
            if not needed.issubset(identifiers) or value.get("executionAndReadbackObserved") is not True:
                raise ValueError("Passed lab needs all captures and actual execution/readback: " + lab)
            if not all(captures[ident]["completionEvidence"] for ident in needed):
                raise ValueError("Partial/orientation excerpts cannot complete a lab: " + lab)
        known_issue = value.get("knownIssue")
        if known_issue is not None:
            required_negative = {item["id"] for item in required.values() if item["lab"] == lab and item.get("completionRequired", True)}
            if (
                lab != "copilot-act" or value["status"] != "failed"
                or not isinstance(known_issue, dict)
                or set(known_issue) != {"reviewed", "rollbackVerified", "failedInvariants"}
                or known_issue["reviewed"] is not True or known_issue["rollbackVerified"] is not True
                or not isinstance(known_issue["failedInvariants"], list)
                or not known_issue["failedInvariants"]
                or any(not isinstance(name, str) for name in known_issue["failedInvariants"])
                or not set(known_issue["failedInvariants"]).issubset(ACT_INVARIANTS)
                or not identifiers or value.get("executionAndReadbackObserved") is not True
                or not required_negative.issubset(identifiers)
                or not all(captures[ident]["completionEvidence"] for ident in required_negative if ident in captures)
                or any(value.get("invariants", {}).get(name) is not False for name in known_issue["failedInvariants"])
            ):
                raise ValueError("Known-issue teaching lane requires the failed metadata-only Act, negative readback and verified rollback")
        result[lab] = {"status": value["status"], "reason": reason, "evidenceIds": identifiers}
        if known_issue is not None:
            result[lab]["knownIssue"] = known_issue
        covered.append(bool(identifiers) and (value["status"] in {"passed", "blocked", "unsupported"} or known_issue is not None))
    return result, all(covered)


def load(path: Path | None = None) -> dict:
    required = {item["id"]: item for item in requests()}
    labs = {item["lab"] for item in required.values()}
    if path is None:
        return {
            "captures": {},
            "labs": {lab: {"status": "not-run", "reason": {
                "ja": "新UIの実施証拠未提供。教材の準備と実行合格は別です。",
                "en": "No new-UI execution evidence supplied. Prepared material is not a passed lab.",
            }, "evidenceIds": []} for lab in sorted(labs)},
            "complete": False,
        }
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schemaVersion") != "furusato-preview30-evidence/v1":
        raise ValueError("Unsupported evidence manifest schema")
    captures = {}
    for capture in data.get("captures", []):
        ident = capture["id"]
        if ident not in required or ident in captures:
            raise ValueError("Unknown or duplicate capture id: " + ident)
        if capture.get("actualUI") is not True or capture.get("reviewed") is not True:
            raise ValueError("Only reviewed actual UI captures may be embedded")
        if capture.get("experience") != "new":
            raise ValueError("Old UI/marketing imagery is not v3 evidence")
        original = _private_file(path.parent, capture["original"])
        sanitized = _private_file(path.parent, capture["sanitized"])
        for key, file in (("originalSha256", original), ("sanitizedSha256", sanitized)):
            if not SHA.fullmatch(capture.get(key, "")) or digest(file) != capture[key]:
                raise ValueError("Evidence digest mismatch: " + ident + " " + key)
        if not capture.get("capturedAt") or not capture.get("reviewer") or not capture.get("redactions"):
            raise ValueError("Capture needs timestamp, reviewer and explicit redaction provenance")
        timestamp = datetime.fromisoformat(capture["capturedAt"].replace("Z", "+00:00"))
        if timestamp.tzinfo is None:
            raise ValueError("Capture timestamp must include its timezone")
        if capture.get("redactionReview") != "accounts-urls-ids-paths-removed":
            raise ValueError("Required privacy review is missing")
        caption = _pair(capture["caption"], "caption")
        completion_evidence = capture.get("completionEvidence") is True
        with Image.open(sanitized) as image:
            image.verify()
        with Image.open(sanitized) as image:
            if completion_evidence:
                if image.width < 600 or image.height < 250:
                    raise ValueError("Completion UI capture too small to be legible")
            elif min(image.size) < 320 or max(image.size) < 500 or image.width * image.height < 200000:
                raise ValueError("Partial UI excerpt too small even for orientation")
            for value in list(image.info.values()) + list(image.getexif().values()):
                if isinstance(value, str) and PRIVATE_TEXT.search(value):
                    raise ValueError("Private identity remains in image metadata")
        captures[ident] = {
            "path": sanitized, "sha256": capture["sanitizedSha256"], "caption": caption,
            "capturedAt": capture["capturedAt"], "originalSha256": capture["originalSha256"],
            "completionEvidence": completion_evidence,
        }
    result_labs, complete = validate_labs(data, required, captures)
    return {
        "captures": captures, "labs": result_labs,
        "complete": complete,
    }
