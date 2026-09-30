"""Create a deterministic private DRAFT bundle, never a release or live pass."""

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
from furusato_docs.validators import Report  # noqa: E402
from validate_preview30 import inspect_word, inspect_html, check_capture_fidelity  # noqa: E402

PACKAGE_NAME = "Furusato_Workshop_v3.0.0-preview_DRAFT.zip"
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


def load_validated_inputs(pair, validation_path):
    if {p.name for p in pair.iterdir()} != {WORD_NAME, HTML_NAME}:
        raise ValueError("Guide input must be the exact two-file pair")
    validation = require_full_validation(json.loads(validation_path.read_text(encoding="utf-8")))
    files = {}
    for name in (WORD_NAME, HTML_NAME):
        data = (pair / name).read_bytes()
        if sha(data) != validation.get("files", {}).get(name):
            raise ValueError("The pair changed since full validation: " + name)
        files["guide/" + name] = data
    return validation, files


def collect_public_reports(metadata, root=ROOT):
    final_runs = [run for run in metadata.get("originalSuiteRuns", []) if run["id"] == "compat-native-ui-final"]
    if not final_runs:
        return {}
    reports = root / "docs" / "v3-preview" / "reports"
    summary = json.loads((reports / "evaluation-summary.json").read_text(encoding="utf-8"))
    if summary["evidenceProjectionSha256"] != metadata.get("publicEvidenceProjectionSha256"):
        raise ValueError("Public reports do not match the selected source evidence projection")
    if summary["finalEvaluation"] != final_runs[0] or summary["qualityAccepted"] is not False or summary["mainPromoted"] is not False:
        raise ValueError("Public report acceptance/method differs from the paired guide")
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


def package(pair: Path, validation_path: Path, output: Path, evidence_path: Path | None, evaluation_path: Path | None = None, *, public_evidence_path: Path | None = None):
    pair, validation_path, output = pair.resolve(), validation_path.resolve(), output.resolve()
    if any(path.is_relative_to(ROOT) for path in (pair, validation_path, output)):
        raise ValueError("Builds, validation and DRAFT package must remain in external private staging")
    if output.exists():
        raise ValueError("Refusing to overwrite an existing package directory")
    validation, files = load_validated_inputs(pair, validation_path)
    document, _, _, _, evidence, metadata = build(ROOT, evidence_path, evaluation_path, public_evidence_path=public_evidence_path)
    report = Report(target="DRAFT package input recheck")
    inspect_word(pair / WORD_NAME, document, metadata, report)
    inspect_html(pair, document, metadata, report)
    check_capture_fidelity(pair, document, evidence, report)
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
    public_reports = collect_public_reports(metadata)
    files.update(public_reports)
    files["START_HERE.txt"] = START_HERE.encode("utf-8")
    state = {
        "schemaVersion": "furusato-local-draft-package/v1",
        "edition": "3.0.0-preview", "kind": "DRAFT",
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
    if metadata.get("evaluationProjection") is not None:
        state["independentEvaluationApprovedProjection"] = metadata["evaluationProjection"]
    if metadata.get("originalSuiteRuns") is not None:
        state["approvedOriginalSuiteAggregates"] = metadata["originalSuiteRuns"]
    files["DRAFT_STATUS.json"] = (json.dumps(state, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    files["SHA256SUMS.txt"] = "".join(f"{sha(blob)}  {name}\n" for name, blob in sorted(files.items())).encode("utf-8")
    for name in (WORD_NAME, HTML_NAME):
        if (pair / name).read_bytes() != files["guide/" + name]:
            raise ValueError("Source pair changed during packaging")
    output.mkdir(parents=True)
    archive_path = output / PACKAGE_NAME
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
    (output / "SHA256SUMS.txt").write_text(f"{digest}  {PACKAGE_NAME}\n", encoding="utf-8")
    result = {
        "archive": PACKAGE_NAME, "bytes": archive_path.stat().st_size, "sha256": digest,
        "kind": "DRAFT", "entries": len(files),
        "localInputRechecks": len(report.findings), "liveVerificationCertified": False,
        "rawEvidenceIncluded": False, "privateAIScoresIncluded": False,
    }
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
    args = parser.parse_args()
    print(json.dumps(package(args.pair, args.validation, args.out, args.evidence, args.evaluation_report, public_evidence_path=args.public_evidence), ensure_ascii=False, indent=2))
