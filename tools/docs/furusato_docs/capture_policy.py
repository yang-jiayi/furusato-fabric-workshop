"""Validate real UI provenance without treating an older illustration as current configuration."""

from __future__ import annotations

import hashlib
import re

TAGS = {"16-30", "18-30", "17-40"}
CONFIGURATION_TAGS = {"16-30", "18-30"}
CI_TAG = "17-40"


def ci_instruction_digest(instructions: str) -> str:
    start = "CODE INTERPRETER: BOUNDED, EXECUTED, SECONDARY\n"
    end = "\nFINAL CHECK"
    if instructions.count(start) != 1 or instructions.count(end) != 1:
        raise ValueError("The exact CI instruction section is not identifiable.")
    section, separator, _ = instructions.split(start, 1)[1].partition(end)
    if not separator:
        raise ValueError("FINAL CHECK must follow the CI instruction section.")
    return hashlib.sha256(section.encode("utf-8")).hexdigest()


def capture_problems(
    registry: dict,
    instructions: str,
    carrier_hashes: dict[str, str],
    embedded_hashes: set[str],
    *,
    code_interpreter_enabled: bool,
    preview_enabled: bool,
) -> list[str]:
    entries = registry.get("captures", {})
    problems: list[str] = []
    if (
        registry.get("schemaVersion") != "furusato-real-ui-captures/v1"
        or set(entries) != TAGS or registry.get("pixelsEdited") is not False
        or type(registry.get("instructionRevision")) is not int
        or registry["instructionRevision"] < 1
        or not re.fullmatch(r"[0-9a-f]{64}", str(registry.get("globalInstructionsSha256", "")))
    ):
        return ["capture inventory or original-pixel policy differs"]
    usage = registry.get("usage")
    active = TAGS
    if usage is None:
        if registry.get("globalInstructionsSha256") != hashlib.sha256(instructions.encode("utf-8")).hexdigest():
            problems.append("current-configuration captures do not match the current instructions")
    else:
        if not isinstance(usage, dict):
            return ["unsupported capture usage policy"]
        if (
            usage.get("mode") != "ci-illustration-only"
            or usage.get("activeTags") != [CI_TAG]
            or set(usage.get("retainedOnlyTags", [])) != CONFIGURATION_TAGS
            or usage.get("currentConfigurationCaptured") is not False
        ):
            return ["unsupported capture usage policy"]
        active = {CI_TAG}
        if (
            not code_interpreter_enabled or not preview_enabled
            or usage.get("ciInstructionsSha256") != ci_instruction_digest(instructions)
        ):
            problems.append("the retained CI illustration is not compatible with the current CI instructions/settings")
    for tag, entry in entries.items():
        original = entry.get("originalSha256")
        if (
            entry.get("path") != f"screenshots/{tag}.png"
            or not original
            or entry.get("sha256") != original
            or carrier_hashes.get(tag) != original
        ):
            problems.append(f"{tag}: original capture/registry/carrier mismatch")
        if tag in active and original not in embedded_hashes:
            problems.append(f"{tag}: active illustration is missing from the document")
        if tag not in active and original in embedded_hashes:
            problems.append(f"{tag}: obsolete configuration capture is embedded")
    return problems
