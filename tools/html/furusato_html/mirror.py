"""Japanese -> English mirror lookup.

The Japanese participant guide is canonical. Every Japanese string the captured
content model produces must have exactly one English counterpart, so the two
languages can never drift apart silently: an unknown key is a hard build error,
and an unused key is reported as drift too.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path

I18N_DIR = Path(__file__).resolve().parent / "i18n"

#: A string containing any of these needs a hand-written English mirror. The set
#: is deliberately wide (CJK punctuation and full-width forms included) so that
#: "80,000 件" or "1・2" is treated as Japanese while "Core" or "ot_donation" is
#: recognised as language-neutral and passed through unchanged.
NEEDS_MIRROR = re.compile(r"[\u3000-\u303f\u3040-\u30ff\u4e00-\u9fff\uff00-\uffef]")

#: Characters that mean "this string still needs a human translation".
JAPANESE = re.compile(r"[\u3040-\u309f\u30a0-\u30ff\u4e00-\u9fff]")

#: Strings whose English mirror legitimately keeps Japanese text: ontology
#: synonym lists that participants paste verbatim, colloquial test prompts that
#: quote the original question, and glosses of Japanese domain terms.
_JAPANESE_ALLOWED_MARKERS = (
    "Synonyms:",
    "Japanese original:",
    "(",
)


class TranslationError(RuntimeError):
    """Raised when the English mirror is incomplete or inconsistent."""


@dataclass(frozen=True)
class Mirror:
    """An immutable Japanese -> English map with loud lookup failures."""

    entries: dict[str, str]
    strict: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "_used", set())
        object.__setattr__(self, "_neutral", set())
        object.__setattr__(self, "_missing", {})

    def __contains__(self, japanese: str) -> bool:
        return japanese in self.entries

    def get(self, japanese: str) -> str:
        """Return the English mirror of ``japanese``; raise when it is missing.

        Language-neutral strings -- identifiers, numbers, product names, KQL
        fragments -- are the same in both languages and pass straight through.
        """
        text = str(japanese)
        if not text.strip():
            return text
        if not NEEDS_MIRROR.search(text):
            self._neutral.add(text)  # type: ignore[attr-defined]
            return text
        try:
            english = self.entries[text]
        except KeyError as error:
            if self.strict:
                raise TranslationError(
                    "No English mirror for a captured Japanese string. Add it to "
                    f"tools/html/furusato_html/i18n/. Missing key:\n  {text!r}"
                ) from error
            self._missing[text] = None  # type: ignore[attr-defined]
            return text
        self._used.add(text)  # type: ignore[attr-defined]
        return english

    @property
    def used(self) -> set[str]:
        return set(self._used)  # type: ignore[attr-defined]

    @property
    def neutral(self) -> set[str]:
        return set(self._neutral)  # type: ignore[attr-defined]

    @property
    def missing(self) -> list[str]:
        return list(self._missing)  # type: ignore[attr-defined]

    def unused(self) -> list[str]:
        return sorted(set(self.entries) - self.used)


def _merge(paths: list[Path]) -> dict[str, str]:
    merged: dict[str, str] = {}
    for path in paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise TranslationError(f"{path.name} must be a JSON object")
        for key, value in payload.items():
            if not isinstance(value, str) or not value.strip():
                raise TranslationError(f"{path.name}: empty English mirror for {key!r}")
            if key in merged and merged[key] != value:
                raise TranslationError(
                    f"{path.name}: conflicting English mirror for {key!r}\n"
                    f"  existing: {merged[key]!r}\n  new:      {value!r}"
                )
            merged[key] = value
    return merged


def load_mirror(
    directory: Path | None = None, *, strict: bool = True, public_documents_only: bool = False,
    context=None,
) -> Mirror:
    """Load and merge every ``guide-*.json`` chunk into one mirror."""
    directory = directory or I18N_DIR
    if context is None and directory == I18N_DIR:
        from furusato_docs.context import load_context
        context = load_context()
    chunks = sorted(directory.glob("guide-*.json"))
    if not chunks:
        raise TranslationError(f"No guide-*.json translation chunks under {directory}")
    entries = _merge(chunks)
    if public_documents_only:
        overlay = json.loads((directory / "public-documents.json").read_text(encoding="utf-8"))
        for text in overlay["remove"]:
            if text not in entries:
                raise TranslationError(f"Public-mode replacement is stale: {text!r}")
            del entries[text]
        for text, translation in overlay["add"].items():
            if text in entries or not isinstance(translation, str) or not translation.strip():
                raise TranslationError(f"Conflicting or empty public-mode mirror: {text!r}")
            entries[text] = translation
    if context is not None and context.is_unified_guide:
        overlay = json.loads((directory / "unified-documents.json").read_text(encoding="utf-8"))
        for text in overlay.get("removeExact", []):
            if text not in entries:
                raise TranslationError(f"Stale unified replacement: {text!r}")
            del entries[text]
        prefixes = list(overlay["removePrefixes"])
        if not public_documents_only:
            prefixes.extend(overlay.get("removeFullPrefixes", []))
        for prefix in prefixes:
            matches = [text for text in entries if text.startswith(prefix)]
            if len(matches) != 1:
                raise TranslationError(f"Unified replacement must match exactly one legacy key: {prefix!r}")
            del entries[matches[0]]
        additions = dict(overlay["add"])
        if not public_documents_only:
            additions.update(overlay.get("addFull", {}))
        values = _unified_values(context)
        templates = list(overlay.get("templates", []))
        if not public_documents_only:
            templates.extend(overlay.get("templatesFull", []))
        for pair in templates:
            key = pair["ja"].format_map(values)
            if key in additions:
                raise TranslationError(f"Duplicate unified template: {key!r}")
            additions[key] = pair["en"].format_map(values)
        for text, translation in additions.items():
            if text in entries or not isinstance(translation, str) or not translation.strip():
                raise TranslationError(f"Conflicting or empty unified mirror: {text!r}")
            entries[text] = translation
    elif context is not None and "ENABLE_UNIFIED_DATA_AGENT" in context.notebooks["Notebook_04"].parameters:
        _add_compatibility_parameter(entries, context, directory, public_documents_only)
    return Mirror(entries=entries, strict=strict)


def _add_compatibility_parameter(entries, context, directory, public_documents_only) -> None:
    """The new default-False flag is also documented in retained legacy editions."""
    from furusato_docs.parameters import UNIFIED_AGENT_DOC

    overlay = json.loads((directory / "unified-documents.json").read_text(encoding="utf-8"))
    for text in (
        UNIFIED_AGENT_DOC.action, UNIFIED_AGENT_DOC.meaning,
        UNIFIED_AGENT_DOC.default_behaviour, UNIFIED_AGENT_DOC.safety_gate,
    ):
        if text in entries or text not in overlay["add"]:
            raise TranslationError(f"Conflicting or missing compatibility-parameter mirror: {text!r}")
        entries[text] = overlay["add"][text]
    count = sum(len(notebook.parameters) for notebook in context.notebooks.values())
    prefixes = ["Notebook 01–05 のパラメーター索引"]
    if not public_documents_only:
        prefixes.append("全 50 パラメーターは")
    for prefix in prefixes:
        matches = [text for text in entries if text.startswith(prefix)]
        if len(matches) != 1:
            raise TranslationError(f"Parameter total must have one mirror: {prefix!r}")
        old = matches[0]
        new = old.replace("50 パラメーター", f"{count} パラメーター")
        english = entries.pop(old).replace("50 parameters", f"{count} parameters")
        if new in entries:
            raise TranslationError(f"Conflicting parameter total: {new!r}")
        entries[new] = english


def _unified_values(context) -> dict[str, str]:
    instructions = context.guide_agent_instructions
    pasted = instructions.rstrip("\r\n")
    return {
        "paste_chars": f"{len(pasted):,}",
        "paste_bytes": f"{len(pasted.encode('utf-8')):,}",
        "paste_sha": hashlib.sha256(pasted.encode("utf-8")).hexdigest(),
        "file_chars": f"{len(instructions):,}",
        "file_bytes": f"{len(instructions.encode('utf-8')):,}",
        "file_sha": hashlib.sha256(instructions.encode("utf-8")).hexdigest(),
        "instruction_limit": f"{context.workspace_contract['dataAgent']['globalInstructionsCharLimit']:,}",
        "parameter_count": str(sum(len(notebook.parameters) for notebook in context.notebooks.values())),
    }


def load_ui_strings(
    directory: Path | None = None, *, public_documents_only: bool = False, context=None
) -> dict[str, dict[str, str]]:
    """Load the HTML-only chrome strings (``{key: {"ja": ..., "en": ...}}``)."""
    directory = directory or I18N_DIR
    payload = json.loads((directory / "ui.json").read_text(encoding="utf-8"))
    if public_documents_only:
        overlay = json.loads((directory / "public-documents.json").read_text(encoding="utf-8"))
        if set(overlay["ui"]) - set(payload):
            raise TranslationError("Public-mode UI overrides unknown keys")
        payload.update(overlay["ui"])
    if context is not None and context.is_unified_guide:
        overlay = json.loads((directory / "unified-documents.json").read_text(encoding="utf-8"))
        if set(overlay["ui"]) - set(payload):
            raise TranslationError("Unified-mode UI overrides unknown keys")
        payload.update(overlay["ui"])
    for key, value in payload.items():
        if set(value) != {"ja", "en"}:
            raise TranslationError(f"ui.json[{key}] must define exactly 'ja' and 'en'")
        for lang, text in value.items():
            if not str(text).strip():
                raise TranslationError(f"ui.json[{key}][{lang}] is empty")
    return payload


def suspicious_english(entries: dict[str, str]) -> list[str]:
    """Return English values that still look untranslated."""
    bad: list[str] = []
    for japanese, english in entries.items():
        if not JAPANESE.search(english):
            continue
        if any(marker in english for marker in _JAPANESE_ALLOWED_MARKERS):
            continue
        bad.append(japanese)
    return sorted(bad)
