"""Import coordinator-reviewed excerpts privately; never infer a lab pass."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "docs"))
from furusato_docs import preview30_evidence as evidence  # noqa: E402

CAPTIONS = {
    "ui-home": (
        "p30-06-entities",
        "新experienceの実Home画面。Entity未作成の操作導入で、10Entity/実bindingの完成証拠ではありません。アカウント・URL・環境IDを含まないiframe領域の原画を使用しています。",
        "Actual new-experience Home before entity creation. UI orientation only, not proof of ten completed entities or data bindings. The original iframe-region capture contains no account, URL or environment ID.",
    ),
    "shared-property": (
        "p30-14-shared",
        "実ConfigureのAdministrativeArea/AreaName。Property sourceはGlobal、String型、Data sourceはUnboundで、keyも未設定です。共有propertyの表示例であり、binding/override/実データ検証の合格ではありません。公開用に元画面から切り抜いています。",
        "Actual Configure for AdministrativeArea/AreaName: Global property source, String type, Unbound data source and no entity key. This illustrates shared-property UI, not passed binding/override/data validation. Cropped from the original for publication.",
    ),
    "attachment-control-A": (
        "p30-15-noattachment",
        "親セッションの添付なし対照会話の実抜粋。資料がないため判定不能と答えた画面です。promptではPlanを要求していますが、この画像・テキスト抜粋だけでは当時のactive modeを確定しません。document-only対照で、実source discovery・独立データ評価・添付あり比較の完成証拠ではありません。縦長の部分証拠です。",
        "Actual no-attachment control excerpt: the agent cannot determine the requested facts without documents. The prompt requested Plan, but the active UI mode is not established by this image/text excerpt alone. Document-only control, not completed source discovery, independent data evaluation or attachment comparison. A narrow partial observation, not completion evidence.",
    ),
    "attachment-upload-B": (
        "p30-15-attachments",
        "実B会話へのbusiness-requirements.pdf、data-dictionary.txt、domain-model.pngの添付表示。uploadの部分観測であり、modelによる全内容の利用・比較結果・実データquery・Act/readbackの合格ではありません。使用した教材版は凍結staging receiptに従い、現在の配布版と同一とは推測しません。",
        "Actual B-conversation attachment display for business-requirements.pdf, data-dictionary.txt and domain-model.png. Partial upload observation only, not completed model use, comparison, live-data querying or Act/readback. The tested revision is the frozen staging receipt, not assumed identical to the current distributed pack.",
    ),
    "attachment-response-B": (
        "p30-15-attachment-response",
        "凍結B質問に対する実応答の抜粋。errorや不足も観測のまま保持し、ファイル名だけで内容利用を合格にしません。document-groundedな説明をsource探索・データquery・Ontology変更や独立AI正答率と混同しません。",
        "Actual response excerpt for the frozen B question. Errors or gaps remain as observed; filenames alone do not prove content use. Document-grounded explanations are not source discovery, data queries, ontology changes or independent AI accuracy.",
    ),
    "attachment-response-B-bottom": (
        "p30-15-attachment-response-bottom",
        "同じB応答の続き。別の質問・追加run・3回再現性の証拠として数えません。document-onlyの結果と未確立事項をそのまま示す部分観測です。",
        "Continuation of the same B response, not another question, an additional run or evidence of three-run repeatability. A partial observation preserving the document-only result and its unestablished outcomes.",
    ),
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def capture_caption(item, requested):
    if item["id"] in CAPTIONS:
        return CAPTIONS[item["id"]]
    if item["id"] in requested:
        caption = evidence._pair(item.get("caption"), "caption")
        return item["id"], caption["ja"], caption["en"]
    raise ValueError("Unmapped capture: " + item["id"] + "; explicitly review its placement before import")


def import_reviewed(source: Path, original_root: Path, output: Path, *, new_experience_confirmed: bool):
    source, original_root, output = source.resolve(), original_root.resolve(), output.resolve()
    if not new_experience_confirmed:
        raise ValueError("Confirm actual new-experience imagery after reviewing the coordinator's screenshots")
    if source.is_relative_to(ROOT) or original_root.is_relative_to(ROOT) or output.is_relative_to(ROOT):
        raise ValueError("All evidence inputs and output must be private, outside the public source tree")
    if output.exists():
        raise ValueError("Refusing to overwrite an evidence snapshot")
    source_raw = source.read_bytes()
    data = json.loads(source_raw)
    if data.get("schemaVersion") != 1 or not isinstance(data.get("captures"), list):
        raise ValueError("Unsupported coordinator review manifest")
    requested = {row["id"]: row for row in evidence.requests()}
    prepared = []
    seen = set()
    for item in data["captures"]:
        ident, ja, en = capture_caption(item, requested)
        if ident in seen:
            raise ValueError("Duplicate capture placement")
        seen.add(ident)
        review = item.get("visualReview", {})
        if (
            review.get("authenticNativeUi") is not True
            or review.get("identifyingAccountOrEndpointVisible") is not False
            or review.get("contentAltered") is not False
            or not review.get("reviewer")
        ):
            raise ValueError("Capture lacks required actual-UI/privacy review")
        original, sanitized = Path(item["originalPath"]).resolve(), Path(item["reviewedPath"]).resolve()
        if not original.is_relative_to(original_root) or not sanitized.is_relative_to(source.parent):
            raise ValueError("Capture escapes explicitly approved evidence roots")
        for path, expected in ((original, item["originalSha256"]), (sanitized, item["reviewedSha256"])):
            if path.suffix.lower() != ".png" or digest(path) != expected:
                raise ValueError("Capture source/hash mismatch: " + ident)
        prepared.append((item, ident, ja, en, original, sanitized))
    output.mkdir(parents=True)
    (output / "originals").mkdir()
    (output / "reviewed").mkdir()
    normalized = {
        "schemaVersion": "furusato-preview30-evidence/v1",
        "captures": [],
        "labs": evidence.load()["labs"],
    }
    for item, ident, ja, en, original, sanitized in prepared:
        original_target = output / "originals" / f"{ident}.png"
        sanitized_target = output / "reviewed" / f"{ident}.png"
        shutil.copyfile(original, original_target)
        shutil.copyfile(sanitized, sanitized_target)
        if digest(original_target) != item["originalSha256"] or digest(sanitized_target) != item["reviewedSha256"]:
            raise ValueError("Capture changed while copying; obtain a new review: " + ident)
        normalized["captures"].append({
            "id": ident, "original": original_target.relative_to(output).as_posix(),
            "sanitized": sanitized_target.relative_to(output).as_posix(),
            "originalSha256": digest(original_target), "sanitizedSha256": digest(sanitized_target),
            "capturedAt": item["capturedUtc"], "experience": "new", "actualUI": True,
            "reviewed": True, "reviewer": item["visualReview"]["reviewer"],
            "redactions": json.dumps({
                "cropBox": item.get("cropBox"), "masks": item.get("redactionMasks", []),
                "regionCaptureExcludesIdentities": True, "contentAltered": False,
            }),
            "redactionReview": "accounts-urls-ids-paths-removed",
            "completionEvidence": False, "caption": {"ja": ja, "en": en},
        })
        lab = requested[ident]["lab"]
        evidence_ids = normalized["labs"][lab]["evidenceIds"] + [ident]
        normalized["labs"][lab] = {
            "status": "observed",
            "reason": {
                "ja": "実UIの部分的な操作・表示を観測。演習全体の実行/readbackと完成条件は未確認です。",
                "en": "Partial native UI/configuration observed; full lab execution/readback and completion criteria remain unverified.",
            },
            "evidenceIds": evidence_ids, "executionAndReadbackObserved": False,
        }
    destination = output / "manifest.json"
    destination.write_text(json.dumps(normalized, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output / "coordinator-review-private.json").write_bytes(source_raw)
    checked = evidence.load(destination)
    if checked["complete"] or any(v["status"] == "passed" for v in checked["labs"].values()):
        raise AssertionError("An orientation import must not promote a lab")
    return {"manifest": str(destination), "captures": len(prepared), "evidenceComplete": False, "labPassesInferred": 0}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--original-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--new-experience-confirmed", action="store_true")
    args = parser.parse_args()
    print(json.dumps(import_reviewed(
        args.source, args.original_root, args.out, new_experience_confirmed=args.new_experience_confirmed,
    ), ensure_ascii=False, indent=2))
