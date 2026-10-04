"""Package an explicitly selected document edition, never a live or AI pass."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "tools" / "docs"), str(ROOT / "tools" / "html")]

from furusato_docs.preview30_content import HTML_NAME, WORD_NAME, build  # noqa: E402
from furusato_docs import preview30_public_evidence as public  # noqa: E402
from furusato_docs import preview30_reporting as reporting  # noqa: E402
from furusato_docs import preview30_release as release  # noqa: E402
from furusato_docs import preview30_evaluation100 as study100  # noqa: E402
from furusato_docs.preview30_acceptance import require_public_acceptance  # noqa: E402
from furusato_docs.validators import Report  # noqa: E402
from validate_preview30 import inspect_word, inspect_html, check_capture_fidelity  # noqa: E402

PACKAGE_NAME = release.PREVIEW.package_name
ATTACHMENTS = (
    "business-requirements.pdf", "data-dictionary.txt", "domain-model.png",
    "revision-requirements.txt", "manifest.json", "SHA256SUMS.txt",
)
PUBLIC_REPORTS = ("evaluation-summary.json", "evaluation-report.md", "progress-report.md", "SHA256SUMS.txt")
REQUIRED_FULL_CHECKS = {
    "word.renderAvailable", "word.persistentTOC", "word.noBlankPages", "word.noClippedText",
    "html-ja.noBlankPages", "html-ja.noClippedText", "html-en.noBlankPages", "html-en.noClippedText",
    "interaction.noScriptErrors", "interaction.noExternalRequests", "interaction.languagePersists",
    "interaction.ja.viewport390", "interaction.en.viewport390",
}
START_HERE = """Furusato Workshop 3.0 Preview — 実装・検証結果を収録したPreview

AI回答品質は未合格。GA・全機能合格・main promotionの主張ではありません。
AI answer quality is not accepted. Not GA, all-feature acceptance or main promotion.

Open guide/furusato-workshop-v3-0-0-preview-complete.html locally.
Word and HTML are together in guide/; the HTML Word-download link stays local.
Use the Japanese/English switch, search, progress checklist, zoom and print.
attachments/ contains synthetic business PDF, dictionary TXT, domain PNG and
optional revision TXT. These are conversation context, not data ingestion.

これは既知の制約と実装・検証結果を収録したPreviewです。認証成功・write承認ではありません。
過去の部分的な実UI観測は撮影日時の状態だけを表し、現在の認証を証明しません。
通常のMicrosoft認証と配置scopeの確認を省略せず、token/cookieを注入しないでください。
添付有無の比較は新しい別会話で実施し、承認したlab-copyへのActだけを行います。

This package does not certify live lab completion, authentication or write scope.
Normal Microsoft authentication and proven deployment scope remain prerequisites.
Never bypass authentication or extract/inject tokens or cookies.
Historical partial captures remain observations, not current sign-in or lab passes.
No private raw evidence, original screenshots, transcripts or private AI scores
are included. Local validation counts are document checks, not AI accuracy scores.

When present, reports/ contains sanitized public progress/evaluation reports, not
raw answers, private criterion text or internal reasoning. Stable v2.7 is retained.
Inspect DRAFT_STATUS.json and SHA256SUMS.txt. For example in PowerShell:
Get-FileHash .\\guide\\Fabric_IQ_Ontology_Workshop_Furusato_Participant_v3.0.0-preview.docx -Algorithm SHA256
Get-FileHash .\\guide\\furusato-workshop-v3-0-0-preview-complete.html -Algorithm SHA256
"""


def sha(blob):
    return hashlib.sha256(blob).hexdigest()


def require_full_validation(validation):
    if validation.get("passedLocalChecks") is not True:
        raise ValueError("Local validation did not pass")
    passed = {row["check"] for row in validation.get("findings", []) if row.get("level") == "PASS"}
    if not REQUIRED_FULL_CHECKS <= passed:
        raise ValueError("Full Word rendering, bilingual print or interaction evidence is missing")
    if any(row.get("level") == "FAIL" for row in validation.get("findings", [])):
        raise ValueError("Validation contains failures")
    return validation


def load_validated_inputs(pair, validation_path, *, release_profile=release.PREVIEW):
    profile = release.get_profile(release_profile)
    if {p.name for p in pair.iterdir()} != {profile.word_name, profile.html_name}:
        raise ValueError("Guide input must be the exact two-file pair")
    validation = require_full_validation(json.loads(validation_path.read_text(encoding="utf-8")))
    identity = validation.get("documentIdentity")
    if profile.is_release or identity is not None:
        if not isinstance(identity, dict) or identity.get("releaseProfile") != profile.name or identity.get("version") != profile.version:
            raise ValueError("Validation receipt does not match the explicit document release profile")
    files = {}
    for name in (profile.word_name, profile.html_name):
        data = (pair / name).read_bytes()
        if sha(data) != validation.get("files", {}).get(name):
            raise ValueError("The pair changed since full validation: " + name)
        files["guide/" + name] = data
    return validation, files


def collect_public_reports(metadata, root=ROOT, *, reports_path=None, release_profile=release.PREVIEW):
    profile = release.get_profile(release_profile)
    if profile.is_release:
        release.require_metadata_profile(metadata, profile)
    final = public.selected_original_suite_run(metadata)
    if final is None:
        return {}
    reports = release.reports_directory(root, profile, reports_path)
    for name in PUBLIC_REPORTS:
        path = (reports / name).resolve()
        if not path.is_relative_to(reports) or not path.is_file():
            raise ValueError("Public report files must remain inside the approved reports directory")
    summary = json.loads((reports / "evaluation-summary.json").read_text(encoding="utf-8"))
    if summary["evidenceProjectionSha256"] != metadata.get("publicEvidenceProjectionSha256"):
        raise ValueError("Public reports do not match the selected source evidence projection")
    if summary["finalEvaluation"] != final or summary["qualityAccepted"] is not final["accepted"] or summary["mainPromoted"] is not final["promoted"]:
        raise ValueError("Public report acceptance/method differs from the paired guide")
    if summary["historicalRuns"] != [run for run in metadata["originalSuiteRuns"] if run["id"] != final["id"]]:
        raise ValueError("Public reports changed or mixed historical original-suite ledgers")
    if "selectedOriginalSuiteRunId" in metadata:
        expected = reporting.selection_metadata(metadata)
        if (
            summary.get("selectedOriginalSuiteRunId") != final["id"]
            or summary.get("originalSuiteAccepted") is not final["accepted"]
            or any(metadata.get(key) != value for key, value in expected.items())
            or summary.get("presentation") != expected["previewPresentation"]
        ):
            raise ValueError("Public reports and paired guide disagree on the explicit selected run")
        if final["id"] != public.LEGACY_ORIGINAL_SUITE_RUN_ID and (
            summary.get("caseAggregates") != final["caseAggregates"]
            or summary.get("executionEvidence") != expected["selectedSuiteExecutionEvidence"]
            or any(summary.get(key) != value for key, value in expected["selectedRunContext"].items())
            or summary.get("labStates") != metadata["labStates"]
            or summary.get("allFeaturesPassedClaimed") is not False
            or summary.get("finalUserAcceptanceCertified") is not False
            or summary.get("generalPopulationAccuracyClaimed") is not False
            or summary.get("directCausalMcpAbClaimed") is not False
        ):
            raise ValueError("Public report cases, counters or context differ from the selected projection")
    entries = (reports / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines()
    expected_names = set(PUBLIC_REPORTS) - {"SHA256SUMS.txt"}
    seen = set()
    for line in entries:
        digest, name = line.split("  ", 1)
        if name not in expected_names or name in seen or sha((reports / name).read_bytes()) != digest:
            raise ValueError("Public report allowlist/digest check failed")
        seen.add(name)
    if seen != expected_names:
        raise ValueError("Public report checksum inventory is incomplete")
    return {"reports/" + name: (reports / name).read_bytes() for name in PUBLIC_REPORTS}


def selected_package_status(metadata, *, release_profile=release.PREVIEW):
    profile = release.get_profile(release_profile)
    if profile.is_release:
        release.require_metadata_profile(metadata, profile)
    result = {}
    if "selectedOriginalSuiteRunId" in metadata:
        selected = reporting.selection_metadata(metadata)
        result.update({
            "selectedOriginalSuiteRunId": selected["selectedOriginalSuiteRunId"],
            "originalSuiteAccepted": selected["originalSuiteAccepted"],
            "aiAnswerQualityAccepted": selected["aiAnswerQualityAccepted"],
            "mainPromoted": selected["mainPromoted"],
            "finalUserAcceptanceCertified": False,
            "publicEvidenceProjectionSha256": metadata["publicEvidenceProjectionSha256"],
        })
    if profile.is_release:
        result["documentIdentity"] = release.document_identity(metadata, profile)
        result["documentRelease"] = result["documentIdentity"]["documentRelease"]
    if "evaluation100" in metadata:
        result["evaluation100"] = study100.require_metadata(metadata)
        result["evaluation100Sha256"] = metadata["evaluation100Sha256"]
        result["documentIdentity"] = release.document_identity(metadata, profile)
        if "executionProtocol" in result["evaluation100"]:
            result["executionProtocol"] = result["evaluation100"]["executionProtocol"]
            result.update(study100.execution_binding(result["evaluation100"]))
    return result


def start_here(metadata, *, release_profile=release.PREVIEW):
    profile = release.get_profile(release_profile)
    if profile.is_release:
        notice = release.presentation(metadata, profile)
        snapshot_notice = ""
        if profile.is_snapshot:
            snapshot_notice = f"""
This is a dated post-release validation snapshot, not a replacement release.
Original v3.0.0 tag/assets and docs/v3.0.0/guide remain byte-for-byte unchanged.
Public placement: {profile.guide_relative.parent.as_posix()} only.
reports/evaluation100.json is the exact counts-only frozen100 projection;
its SHA256 is {metadata["evaluation100Sha256"]}.
Baseline/intervention80 and final-candidate development80+heldout20 are separate.
AI-assisted review has no independent human sign-off; internal-query/backend
conversation proof remains UNOBSERVABLE. UNKNOWN is not zero-percent accuracy.
METHOD timing is corroborated by an operator receipt and filesystem metadata,
not independently proven; methodTimingIndependentlyCertified=false and
methodPreregistered=false. Preserve the original prep result/intent verbatim:
method-evidence hashes are computedAtAdmission, not backdated.
Review tooling and policy-code binding were finalized DURING capture:
reviewPolicyTiming={metadata["evaluation100"]["review"]["reviewPolicyTiming"]};
this retained string is a compatibility label, not preregistration certification.
fullReviewPolicyPreregistered=false; reviewToolingPreregistered=false.
The separate timing admission precedes
content grading and does not rewrite the original capture plan/candidate/claims.
EXECUTION AMENDMENT: post-stop-unsent-slots-only, not preregistered.
The original blanket no-resume policy WAS amended; originalProtocolWasFullyFollowed=false.
Keep the old stopped batch, original plan/claims/records and the prior2 captures
unchanged. The prior HTTP500 outcome remains UNKNOWN and is never replayed.
Only the17 never-submitted original first attempts may continue, once; stop on
the next failure. Original claims remain spent; no source/transport/candidate/
question changes, heldout-feedback tuning or best-of pooling are authorized.
Even completed continuation means at most19 captured answers +1 unknown, not20
successful answers. A failed invocation may leave additional unsent/unknown slots.
Inspect executionProtocol in {profile.status_name} and reports/evaluation100.json;
executionProtocolSha256={metadata["documentRelease"]["executionProtocolSha256"]}.
The original84 reports below are historical and are not pooled with frozen100.
"""
        heading = "Dated validation snapshot with known limitations" if profile.is_snapshot else "User-authorized document release with known limitations"
        return f"""{profile.title} — {heading}

{notice["ja"]}
{notice["en"]}
Selected original suite: {metadata["selectedOriginalSuiteRunId"]}.
Original ten questions/84 conditions and complete historical ledgers are retained.
Partial captures and blocked/failed labs remain partial, blocked or failed.
This release does not pass the independent --require-acceptance gate.
{snapshot_notice}
Open guide/{profile.html_name} locally.
Word and HTML are together in guide/; the Word-download link stays local.
Use the Japanese/English switch, search, progress checklist, zoom and print.
attachments/ contains the synthetic business PDF, dictionary TXT, domain PNG,
and optional revision TXT: conversation context, not data ingestion.
Source asset references to {release.SOURCE_ASSET_FOLDER} are intentional;
the document edition does not relabel Preview product features or runtime APIs as GA.

通常のMicrosoft認証と配置scope確認は引き続き必須です。この文書リリースは
Fabric Agent promotion、write承認、新規認証、全lab完了を証明しません。
Normal Microsoft authentication and proven deployment scope remain prerequisites.
Never bypass authentication or extract/inject tokens or cookies.
Historical captures describe their capture time, not current sign-in or a live pass.
No private approval record, raw answers, original screenshots or private AI scores
are included. Local document checks are not AI accuracy scores.

reports/ contains only sanitized public progress/evaluation reports.
Stable v2.7 and the historical Preview assets are retained, not replaced.
Inspect {profile.status_name} for the document/source profiles, selected run,
exact projection hash and unaccepted release status. Verify SHA256SUMS.txt:
Get-FileHash .\\guide\\{profile.word_name} -Algorithm SHA256
Get-FileHash .\\guide\\{profile.html_name} -Algorithm SHA256
"""
    result = START_HERE
    if "selectedOriginalSuiteRunId" in metadata:
        selected = public.selected_original_suite_run(metadata, required=True)
        ja, en = reporting.selection_notice(selected)
        result = result.replace(
            "AI回答品質は未合格。GA・全機能合格・main promotionの主張ではありません。\n"
            "AI answer quality is not accepted. Not GA, all-feature acceptance or main promotion.",
            ja + "\n" + en,
        )
    if "evaluation100" in metadata:
        notice = study100.notice(study100.require_metadata(metadata))
        result += "\n" + notice["ja"] + "\n" + notice["en"] + "\n"
        result += "Separate counts-only study: reports/evaluation100.json\nSHA256: " + metadata["evaluation100Sha256"] + "\n"
    return result


def package(
    pair: Path, validation_path: Path, output: Path, evidence_path: Path | None,
    evaluation_path: Path | None = None, *, public_evidence_path: Path | None = None,
    public_reports_path: Path | None = None, require_acceptance: bool = False,
    acceptance_approval: Path | None = None, release_profile=release.PREVIEW,
    release_approval: Path | None = None,
    evaluation100_path: Path | None = None,
    artifact_manifest_path: Path | None = None,
):
    profile = release.get_profile(release_profile)
    release.check_options(
        profile, release_approval, evidence_path=evidence_path, evaluation_path=evaluation_path,
        evaluation100_path=evaluation100_path,
    )
    if acceptance_approval and not require_acceptance:
        raise ValueError("Publication approval cannot be supplied without the acceptance gate.")
    if require_acceptance:
        if evidence_path:
            raise ValueError("Final admission requires a reviewed public projection.")
        require_public_acceptance(public_evidence_path or ROOT / profile.evidence_relative,
                                  acceptance_approval, root=ROOT)
    pair, validation_path, output = pair.resolve(), validation_path.resolve(), output.resolve()
    if any(path.is_relative_to(ROOT) for path in (pair, validation_path, output)):
        raise ValueError("Builds, validation and package must remain in external private staging")
    if output.exists():
        raise ValueError("Refusing to overwrite an existing package directory")
    document, _, _, _, evidence, metadata = build(
        ROOT, evidence_path, evaluation_path, public_evidence_path=public_evidence_path,
        release_profile=profile, release_approval=release_approval,
        evaluation100_path=evaluation100_path,
        **({"artifact_manifest_path": artifact_manifest_path} if artifact_manifest_path else {}),
    )
    if metadata.get("evaluation100", {}).get("evidenceKind") == "synthetic-private-test":
        raise ValueError("Synthetic private study fixtures cannot be packaged or published")
    validation, files = load_validated_inputs(pair, validation_path, release_profile=profile)
    release.require_validation_identity(validation, metadata, profile)
    report = Report(target=profile.kind + " package input recheck")
    inspect_word(pair / profile.word_name, document, metadata, report, release_profile=profile)
    inspect_html(pair, document, metadata, report, release_profile=profile)
    check_capture_fidelity(pair, document, evidence, report, release_profile=profile)
    if not report.passed:
        raise ValueError("Current model/input recheck failed: " + "; ".join(f.check for f in report.failures))
    attachment_root = ROOT / "workshop" / "v3.0.0-preview" / "attachments"
    attachment_manifest = json.loads((attachment_root / "manifest.json").read_text(encoding="utf-8"))
    for name in ATTACHMENTS:
        payload = (attachment_root / name).read_bytes()
        if name in attachment_manifest["files"]:
            if sha(payload) != attachment_manifest["files"][name]["sha256"]:
                raise ValueError("Attachment digest mismatch: " + name)
            if len(payload) > 5 * 1024 * 1024:
                raise ValueError("Attachment exceeds the documented upload limit")
        files["attachments/" + name] = payload
    public_reports = collect_public_reports(metadata, root=ROOT, reports_path=public_reports_path, release_profile=profile)
    files.update(public_reports)
    if artifact_manifest_path is not None:
        artifact_blob = artifact_manifest_path.read_bytes()
        binding = metadata["currentArtifactSet"]
        if sha(artifact_blob) != binding["manifestSha256"]:
            raise ValueError("Current artifact manifest changed during packaging.")
        artifact_set = json.loads(artifact_blob)
        for relative, expected in artifact_set["files"].items():
            path = (ROOT / relative).resolve()
            if not path.is_relative_to(ROOT) or not path.is_file():
                raise ValueError("Current artifact path is invalid.")
            payload = path.read_bytes()
            if sha(payload) != expected:
                raise ValueError("Current artifact bytes changed: " + relative)
            files["source/" + relative] = payload
        files["source/artifact-set.json"] = artifact_blob
    if evaluation100_path is not None:
        study_blob = evaluation100_path.read_bytes()
        if sha(study_blob) != metadata.get("evaluation100Sha256"):
            raise ValueError("Public frozen100 study changed during packaging")
        files["reports/evaluation100.json"] = study_blob
    files["START_HERE.txt"] = start_here(metadata, release_profile=profile).encode("utf-8")
    if "currentArtifactSet" in metadata:
        files["START_HERE.txt"] += (
            "\nCURRENT V3 ARTIFACT SET\nCourse: " + metadata["currentArtifactSet"]["workshopVersion"]
            + "\nSource commit: " + metadata["currentArtifactSet"]["sourceCommit"]
            + "\nManifest: source/artifact-set.json\nProduction: specified folder directly, no Temp."
            + "\nCSV/runtime2.7 compatibility identifiers are intentional, not the course edition."
            + "\nUse the pinned Git checkout for CLI preflight, or the sealed Notebook04 package."
            + "\nHistorical evaluation is not new-environment acceptance.\n"
        ).encode("utf-8")
    state = {
        "schemaVersion": "furusato-document-release-package/v1" if profile.is_release else "furusato-local-draft-package/v1",
        "edition": profile.version, "kind": profile.kind,
        "liveVerificationCertified": False, "writeAuthorizationGranted": False,
        "authenticationVerifiedByPackage": False, "privateAIScoresIncluded": False,
        "rawEvidenceIncluded": False, "originalScreenshotsIncluded": False,
        "contentSha256": metadata["contentSha256"], "documentCounts": metadata["counts"],
        "labStates": metadata["labStates"],
        "evidenceScope": metadata["evidenceScope"],
        "newDeploymentReadinessCertified": False,
        "knownIssueLabs": metadata["knownIssueLabs"],
        "releaseFreezeStatus": metadata.get("releaseFreezeStatus", "not-frozen"),
        "previewPresentation": metadata["previewPresentation"],
        "aiAnswerQualityAccepted": False,
        "approvedPublicReportsIncluded": bool(public_reports),
        "historicalPartialUICaptures": sum(not value["completionEvidence"] for value in evidence["captures"].values()),
        "localDocumentValidationChecks": len(validation["findings"]),
        "localDocumentValidationFailures": 0,
        "note": "Local file checks are not live execution, current authentication or AI accuracy scores.",
        "contentFiles": {name: {"bytes": len(blob), "sha256": sha(blob)} for name, blob in sorted(files.items())},
    }
    state.update(selected_package_status(metadata, release_profile=profile))
    if metadata.get("evaluationProjection") is not None:
        state["independentEvaluationApprovedProjection"] = metadata["evaluationProjection"]
    if metadata.get("originalSuiteRuns") is not None:
        state["approvedOriginalSuiteAggregates"] = metadata["originalSuiteRuns"]
    if profile.is_snapshot:
        state["schemaVersion"] = "furusato-document-validation-snapshot-package/v1"
    files[profile.status_name] = (json.dumps(state, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    files["SHA256SUMS.txt"] = "".join(f"{sha(blob)}  {name}\n" for name, blob in sorted(files.items())).encode("utf-8")
    for name in (profile.word_name, profile.html_name):
        if (pair / name).read_bytes() != files["guide/" + name]:
            raise ValueError("Source pair changed during packaging")
    output.mkdir(parents=True)
    archive_path = output / profile.package_name
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, data in sorted(files.items()):
            info = zipfile.ZipInfo(name, date_time=(2026, 9, 29, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data, compresslevel=9)
    with zipfile.ZipFile(archive_path) as archive:
        if archive.testzip() or set(archive.namelist()) != set(files):
            raise ValueError("Package ZIP integrity failure")
        for name, blob in files.items():
            if archive.read(name) != blob:
                raise ValueError("Package bytes changed: " + name)
    digest = sha(archive_path.read_bytes())
    (output / "SHA256SUMS.txt").write_text(f"{digest}  {profile.package_name}\n", encoding="utf-8")
    result = {
        "archive": profile.package_name, "bytes": archive_path.stat().st_size, "sha256": digest,
        "kind": profile.kind, "entries": len(files),
        "localInputRechecks": len(report.findings), "liveVerificationCertified": False,
        "rawEvidenceIncluded": False, "privateAIScoresIncluded": False,
    }
    if profile.is_release:
        result["documentIdentity"] = release.document_identity(metadata, profile)
    (output / "package-result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pair", required=True, type=Path)
    parser.add_argument("--validation", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    inputs = parser.add_mutually_exclusive_group()
    inputs.add_argument("--evidence", type=Path)
    inputs.add_argument("--public-evidence", type=Path)
    parser.add_argument("--evaluation-report", type=Path)
    parser.add_argument("--artifact-manifest", type=Path)
    parser.add_argument("--public-reports", type=Path, help="Reviewed source reports within the selected document profile's reports directory")
    parser.add_argument("--require-acceptance", action="store_true")
    parser.add_argument("--acceptance-approval", type=Path)
    release.add_arguments(parser)
    args = parser.parse_args()
    print(json.dumps(package(
        args.pair, args.validation, args.out, args.evidence, args.evaluation_report,
        public_evidence_path=args.public_evidence, public_reports_path=args.public_reports,
        require_acceptance=args.require_acceptance, acceptance_approval=args.acceptance_approval,
        release_profile=args.release_profile, release_approval=args.release_approval,
        evaluation100_path=args.evaluation100,
        artifact_manifest_path=args.artifact_manifest,
    ), ensure_ascii=False, indent=2))
