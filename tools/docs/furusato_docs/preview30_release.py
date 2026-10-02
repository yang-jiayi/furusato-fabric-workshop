"""Explicit document editions; known-limitations release approval is not acceptance."""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType

from . import preview30_public_evidence as public
from . import preview30_reporting as reporting


@dataclass(frozen=True)
class ReleaseProfile:
    name: str
    version: str
    display_version: str
    evidence_directory: str
    document_directory: str

    @property
    def is_release(self):
        return self.name == "v3.0.0"

    @property
    def title(self):
        return "Furusato Workshop " + self.display_version

    @property
    def word_name(self):
        return f"Fabric_IQ_Ontology_Workshop_Furusato_Participant_v{self.version}.docx"

    @property
    def html_name(self):
        return f"furusato-workshop-v{self.version.replace('.', '-')}-complete.html"

    @property
    def package_name(self):
        suffix = "" if self.is_release else "_DRAFT"
        return f"Furusato_Workshop_v{self.version}{suffix}.zip"

    @property
    def status_name(self):
        return "RELEASE_STATUS.json" if self.is_release else "DRAFT_STATUS.json"

    @property
    def kind(self):
        return "user-authorized-known-limitations-release" if self.is_release else "DRAFT"

    @property
    def evidence_relative(self):
        return Path("docs") / "assets" / self.evidence_directory / "manifest.json"

    @property
    def guide_relative(self):
        return Path("docs") / self.document_directory / "guide"

    @property
    def reports_relative(self):
        return Path("docs") / self.document_directory / "reports"


PREVIEW = ReleaseProfile("preview", "3.0.0-preview", "3.0 Preview", "v3-preview-evidence", "v3-preview")
V300 = ReleaseProfile("v3.0.0", "3.0.0", "3.0.0", "v3.0.0-evidence", "v3.0.0")
PROFILES = MappingProxyType({profile.name: profile for profile in (PREVIEW, V300)})
SOURCE_ASSET_PROFILE = "v3.0.0-preview"
SOURCE_ASSET_FOLDER = "workshop/" + SOURCE_ASSET_PROFILE
RELEASE_RUN_ID = "provenance-native-ui-20261001"
RELEASE_COUNTS = MappingProxyType(dict(zip(reporting.VERDICT_KEYS, (76, 8, 0, 0, 0))))
APPROVAL_SCHEMA = "furusato-document-release-approval/v1"
RELEASE_SCHEMA = "furusato-document-release/v1"
APPROVAL_FIELDS = {
    "schemaVersion", "approved", "userAuthorized", "version", "selectedOriginalSuiteRunId",
    "evidenceProjectionSha256", "knownLimitationsAcknowledged", "originalCounts",
}


def get_profile(value=PREVIEW):
    name = value.name if isinstance(value, ReleaseProfile) else value
    if not isinstance(name, str) or name not in PROFILES:
        raise ValueError("Unknown document release profile")
    profile = PROFILES[name]
    if isinstance(value, ReleaseProfile) and value != profile:
        raise ValueError("Document release profiles cannot be overridden")
    return profile


def add_arguments(parser):
    parser.add_argument(
        "--release-profile", choices=tuple(PROFILES), default=PREVIEW.name,
        help="Explicit document edition; Preview/DRAFT remains the default",
    )
    parser.add_argument(
        "--release-approval", type=Path,
        help="External private, hash-bound v3.0.0 known-limitations approval; not strict acceptance",
    )


def check_options(profile, approval_path, *, evidence_path=None, evaluation_path=None):
    profile = get_profile(profile)
    if not profile.is_release and approval_path is not None:
        raise ValueError("--release-approval requires --release-profile v3.0.0")
    if profile.is_release:
        if approval_path is None:
            raise ValueError("v3.0.0 requires an explicit known-limitations release approval")
        if evidence_path is not None or evaluation_path is not None:
            raise ValueError("v3.0.0 requires the source-owned public projection without private overrides")


def _unique_fields(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate release approval field")
        result[key] = value
    return result


def _release_binding(profile, projection_sha256, selected):
    if (
        selected["id"] != RELEASE_RUN_ID or selected["counts"] != RELEASE_COUNTS
        or selected["accepted"] is not False or selected["promoted"] is not False
    ):
        raise ValueError("v3.0.0 is bound to the disclosed unaccepted, unpromoted 76 PASS/8 FAIL run")
    if not isinstance(projection_sha256, str) or not public.private.SHA.fullmatch(projection_sha256):
        raise ValueError("v3.0.0 requires the exact public projection SHA256")
    return {
        "schemaVersion": RELEASE_SCHEMA, "profile": profile.name, "version": profile.version,
        "kind": profile.kind, "userAuthorized": True, "knownLimitationsAcknowledged": True,
        "sourceAssetProfile": SOURCE_ASSET_PROFILE, "sourceAssetFolder": SOURCE_ASSET_FOLDER,
        "publicGuideDirectory": profile.guide_relative.as_posix(),
        "publicReportsDirectory": profile.reports_relative.as_posix(),
        "publicEvidenceProjection": profile.evidence_relative.as_posix(),
        "evidenceProjectionSha256": projection_sha256,
        "selectedOriginalSuiteRunId": selected["id"], "originalCounts": dict(selected["counts"]),
        "originalSuiteAccepted": False, "aiAnswerQualityAccepted": False, "mainPromoted": False,
        "allFeaturesPassedClaimed": False, "generalAvailabilityClaimed": False,
        "finalUserAcceptanceCertified": False,
    }


def resolve_evidence(
    root, evidence_path=None, evaluation_path=None, *, public_evidence_path=None,
    release_profile=PREVIEW, release_approval=None,
):
    """Validate permission before the model builder or any output directory is created."""
    profile = get_profile(release_profile)
    check_options(profile, release_approval, evidence_path=evidence_path, evaluation_path=evaluation_path)
    if not profile.is_release:
        return public.resolve(evidence_path, public_evidence_path, root=root), None
    root = root.resolve()
    approval_path = release_approval.resolve()
    if approval_path.is_relative_to(root) or not approval_path.is_file():
        raise ValueError("Release approval must be an existing external private JSON record")
    approval = json.loads(approval_path.read_text(encoding="utf-8"), object_pairs_hook=_unique_fields)
    public.exact_fields(approval, APPROVAL_FIELDS, "release approval", APPROVAL_FIELDS)
    if (
        approval["schemaVersion"] != APPROVAL_SCHEMA or approval["version"] != profile.version
        or any(approval[key] is not True for key in ("approved", "userAuthorized", "knownLimitationsAcknowledged"))
    ):
        raise ValueError("Explicit user-authorized v3.0.0 known-limitations approval is required")
    public.exact_fields(approval["originalCounts"], public.VERDICTS, "approved original counts", public.VERDICTS)
    for key, value in approval["originalCounts"].items():
        public.integer(value, "approved " + key)
    projection_path = (public_evidence_path or root / profile.evidence_relative).resolve()
    if projection_path != (root / profile.evidence_relative).resolve() or not projection_path.is_relative_to(root):
        raise ValueError("v3.0.0 requires source docs/assets/v3.0.0-evidence/manifest.json")
    evidence = public.load(projection_path, root=root)
    if evidence.get("selectedOriginalSuiteRunId") != RELEASE_RUN_ID:
        raise ValueError("v3.0.0 requires the explicit disclosed selectedOriginalSuiteRunId")
    selected = public.selected_original_suite_run(evidence, required=True)
    binding = _release_binding(profile, evidence["projectionSha256"], selected)
    if any(approval[key] != binding[key] for key in (
        "selectedOriginalSuiteRunId", "evidenceProjectionSha256", "originalCounts",
    )):
        raise ValueError("Release approval does not match the exact projection, selected run and current counts")
    return evidence, binding


def require_metadata_profile(metadata, release_profile=PREVIEW):
    profile = get_profile(release_profile)
    if metadata.get("version") != profile.version:
        raise ValueError("Document metadata and explicit release profile disagree")
    if not profile.is_release:
        if metadata.get("documentRelease") is not None:
            raise ValueError("Release metadata cannot be used by the Preview/DRAFT profile")
        return profile
    selected = public.selected_original_suite_run(metadata, required=True)
    expected = _release_binding(profile, metadata.get("publicEvidenceProjectionSha256"), selected)
    if metadata.get("documentRelease") != expected or metadata.get("finalEvaluation") != selected:
        raise ValueError("Document release metadata does not match its source profile, selected run and projection")
    if any(metadata.get(key) is not False for key in (
        "originalSuiteAccepted", "aiAnswerQualityAccepted", "mainPromoted",
        "allFeaturesPassedClaimed", "finalUserAcceptanceCertified",
    )):
        raise ValueError("Known-limitations release cannot claim AI acceptance, promotion or all-feature success")
    return profile


def presentation(metadata, release_profile=PREVIEW):
    profile = require_metadata_profile(metadata, release_profile)
    if not profile.is_release:
        return reporting.metadata_presentation(metadata)
    counts = metadata["documentRelease"]["originalCounts"]
    score = f"{counts['pass']} PASS/{counts['fail']} FAIL"
    return {
        "ja": f"ユーザー承認の文書リリース3.0.0（既知の制約付き）— 元84条件{score}。AI回答品質は未合格／製品機能はPreview／GA・全機能合格・Agent promotionではありません",
        "en": f"User-authorized document release 3.0.0 with known limitations — original84: {score}. AI answer quality unaccepted; product features remain Preview; not GA, all-feature acceptance or Agent promotion",
    }


def document_identity(metadata, release_profile=PREVIEW):
    profile = require_metadata_profile(metadata, release_profile)
    result = {
        "releaseProfile": profile.name, "version": profile.version,
        "sourceAssetProfile": SOURCE_ASSET_PROFILE, "sourceAssetFolder": SOURCE_ASSET_FOLDER,
        "contentSha256": metadata["contentSha256"],
        "selectedOriginalSuiteRunId": metadata.get("selectedOriginalSuiteRunId"),
        "publicEvidenceProjectionSha256": metadata.get("publicEvidenceProjectionSha256"),
    }
    if profile.is_release:
        result["documentRelease"] = copy.deepcopy(metadata["documentRelease"])
    return result


def require_validation_identity(validation, metadata, release_profile=PREVIEW):
    profile = get_profile(release_profile)
    identity = validation.get("documentIdentity")
    # Older Preview validation receipts remain usable; releases always require the binding.
    if profile.is_release or identity is not None:
        if identity != document_identity(metadata, profile):
            raise ValueError("Validation and package inputs disagree on document profile, source, run or projection")


def reports_directory(root, release_profile=PREVIEW, reports_path=None):
    profile = get_profile(release_profile)
    root = root.resolve()
    allowed = root / "docs" / profile.document_directory
    if profile.is_release:
        allowed /= "reports"
    allowed = allowed.resolve()
    reports = (reports_path or root / profile.reports_relative).resolve()
    if not allowed.is_relative_to(root) or not reports.is_relative_to(allowed):
        location = "docs/v3.0.0/reports" if profile.is_release else "docs/v3-preview"
        raise ValueError("Public reports must remain under source " + location)
    return reports
