"""Build a separately dated Ontology V2 evaluation report from reviewed public aggregates.

This is a NEW contract; it does not read, alter or relax the historical 20261010
report schema. Inputs contain counts, hashes and approved bilingual prose only.
The renderer never grades answers or calls Fabric. Ledger hashes are references,
not independent proof that the underlying private reviews are correct.
"""
from __future__ import annotations

import argparse
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
import hashlib
import html
import json
import os
from pathlib import Path
import re
import sys
import zipfile

SCHEMA = "furusato-ontology-v2-evaluation-summary/v2"
ARTIFACT_SCHEMA = "furusato-ontology-v2-report-artifacts/v1"
VERDICTS = ("PASS", "FAIL", "UNCLEAR", "NA")
MATCHED_VERDICTS = ("PASS", "FAIL", "UNCLEAR")
GROUPS = {"original": (30, 252, 3), "regression": (19, 38, 1), "heldout": (2, 6, 1)}
NATIVE_RECORD_STATUSES = ("completed", "platform_error", "native_failure_captured", "evidence_incomplete",
                          "pre_submission_blocked", "submission_outcome_unknown", "unfinished_timeout",
                          "configuration_changed", "configuration_unverified")
MATCHING_KEY = ["suite", "repeat", "case_id", "condition_id"]
EQUAL_FIELDS = ["questionSha256", "conditionSha256", "sourceBusinessSha256", "eligiblePremise"]
REPO = next((parent for parent in Path(__file__).resolve().parents
             if (parent / "WORKSHOP_VERSION").is_file() and (parent / "tools/docs").is_dir()), Path.cwd())


def fail(message):
    raise ValueError(message)


def exact_keys(value, required, optional=()):
    if not isinstance(value, dict):
        fail("Expected a structured object.")
    missing = set(required) - value.keys()
    extra = value.keys() - set(required) - set(optional)
    if missing or extra:
        fail("Summary structure has missing or unsupported fields.")


def count(value, label="count"):
    if type(value) is not int or value < 0:
        fail(label + " must be a nonnegative integer.")
    return value


def digest(value):
    if not isinstance(value, str) or not re.fullmatch(r"[a-f0-9]{64}", value):
        fail("An exact SHA-256 evidence fingerprint is required.")
    return value


def public_text(value):
    """Inspect decoded values, including escaped JSON strings; never echo a secret."""
    texts = [json.dumps(value, ensure_ascii=False)]
    def decoded_strings(item):
        if isinstance(item, str):
            texts.append(item)
        elif isinstance(item, dict):
            for key, child in item.items():
                decoded_strings(key)
                decoded_strings(child)
        elif isinstance(item, (list, tuple)):
            for child in item:
                decoded_strings(child)
    decoded_strings(value)
    patterns = (
        r"/workspace/", r"/var/tmp/", r"/tmp/", r"(?i)[a-z]:[\\/]",
        r"(?i)\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b",
        r"(?i)bearer\s+[A-Za-z0-9_.-]{20,}",
        r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+",
        r"\b(?:T|B|Q|OQ)\d{2}\b", r"\b(?:HA|HB)\b",
        r"(?i)https?://(?:app\.(?:fabric\.microsoft|powerbi)\.com|[^/]+\.analysis\.windows\.net)/",
    )
    if any(re.search(pattern, text) for pattern in patterns for text in texts):
        fail("Public summary contains a private path, resource identifier, credential or evaluation marker.")


def bilingual(value):
    exact_keys(value, ("ja", "en"))
    for language in ("ja", "en"):
        if not isinstance(value[language], str) or not value[language].strip():
            fail("Both Japanese and English prose are required.")
        if len(value[language]) > 12000:
            fail("A report paragraph exceeds the reviewable text budget.")


def verdicts(value, total):
    exact_keys(value, VERDICTS)
    if sum(count(value[key], key) for key in VERDICTS) != total:
        fail("Verdict counts do not preserve the registered condition denominator.")
    return value


def sum_verdicts(groups, field="content"):
    return {key: sum(group[field][key] for group in groups) for key in VERDICTS}


def percentage(passed, total):
    if total == 0:
        return None
    return str((Decimal(passed) * 100 / Decimal(total)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def validate_group(group, name, phase):
    exact_keys(group, ("name", "questions", "conditions", "repetitions", "suiteSha256", "content", "strictNativeConditions"),
               ("naEligibilityEvidenceSha256",))
    if group["name"] != name:
        fail("Unexpected or duplicated question group.")
    if phase in ("baseline", "final"):
        expected = GROUPS[name]
    elif phase == "qualification":
        expected = (2, 5, 1)
    else:
        expected = (count(group["questions"]), count(group["conditions"]), 1)
        if not 1 <= expected[0] <= 8 or expected[1] < 1:
            fail("A targeted wave must have one to eight questions and explicit conditions.")
    if tuple(group[key] for key in ("questions", "conditions", "repetitions")) != expected:
        fail("The pre-registered question/condition/repetition contract changed.")
    for key in ("questions", "conditions", "repetitions"):
        count(group[key], key)
    digest(group["suiteSha256"])
    for field in ("content", "strictNativeConditions"):
        verdicts(group[field], group["conditions"])
        na = group[field]["NA"]
        if na:
            if name != "original" or na > 9:
                fail("Only the predeclared original clarification branch may have NA conditions.")
            digest(group.get("naEligibilityEvidenceSha256"))
    if "naEligibilityEvidenceSha256" in group:
        digest(group["naEligibilityEvidenceSha256"])


def validate_phase(phase):
    exact_keys(phase, ("name", "publicationDefinitionSha256", "sourceDefinitionSha256", "sourceBusinessSha256",
                       "captureLedgerSha256", "contentReviewLedgerSha256", "strictNativeReviewLedgerSha256",
                       "independentContentReviewSha256", "phaseClosureSha256", "groups", "collection", "captures"))
    name = phase["name"]
    if name not in ("qualification", "baseline", "targeted-01", "targeted-02", "final"):
        fail("Unexpected evaluation phase.")
    for key in phase:
        if key.endswith("Sha256"):
            digest(phase[key])
    expected_names = list(GROUPS) if name in ("baseline", "final") else ["qualification" if name == "qualification" else "targeted"]
    if not isinstance(phase["groups"], list) or [g.get("name") for g in phase["groups"]] != expected_names:
        fail("Each phase must preserve the exact ordered question groups.")
    for group in phase["groups"]:
        validate_group(group, group["name"], name)
    collection = phase["collection"]
    exact_keys(collection, ("httpTimeoutSeconds", "captureTimeoutSeconds", "definitionTimeoutSeconds", "newConversationPerQuestion", "retryPolicy"))
    if (collection["httpTimeoutSeconds"], collection["captureTimeoutSeconds"], collection["definitionTimeoutSeconds"]) != (300, 900, 600):
        fail("Every phase must use the pre-frozen 300/900/600-second transport policy.")
    if collection["newConversationPerQuestion"] is not True or collection["retryPolicy"] != "never-resubmit-consumed-slot":
        fail("Conversation initialization or consumed-slot policy changed.")
    captures = phase["captures"]
    exact_keys(captures, ("registeredQuestions", "questionPOSTs", "notSubmitted", "unfinalizedCaptures",
                         "uncertainQuestionPOSTUpperBound", "knownTerminalResponses", "retainedFailures", "nativeRecordStatuses",
                         "completed", "failed", "cancelled", "incomplete", "unknownResponseStatus",
                         "responsesWithInternalErrors", "responsesWithIncompleteEvidence", "responsesWithSuccessfulSourceExecution",
                         "strictNativeAcceptedResponses"))
    for key, value in captures.items():
        if key != "nativeRecordStatuses":
            count(value, key)
    statuses = captures["nativeRecordStatuses"]
    exact_keys(statuses, (), NATIVE_RECORD_STATUSES)
    for key, value in statuses.items():
        count(value, key)
    questions = sum(group["questions"] for group in phase["groups"])
    ordinary = captures["questionPOSTs"] + captures["notSubmitted"]
    if captures["registeredQuestions"] != questions or ordinary + captures["unfinalizedCaptures"] != questions:
        fail("Registered question and submission denominators differ.")
    if sum(statuses.values()) != ordinary:
        fail("Native record statuses must account for every ordinary finalized record.")
    if captures["retainedFailures"] != questions - statuses.get("completed", 0):
        fail("Closure failures must retain every non-completed native record and unfinalized capture.")
    if captures["uncertainQuestionPOSTUpperBound"] > captures["unfinalizedCaptures"]:
        fail("An uncertain submission upper bound cannot exceed unfinalized captures.")
    if sum(captures[key] for key in ("completed", "failed", "cancelled", "incomplete", "unknownResponseStatus")) != captures["questionPOSTs"]:
        fail("Each known submitted question needs an independently observed Response status or unknown status.")
    if captures["knownTerminalResponses"] != sum(captures[key] for key in ("completed", "failed", "cancelled", "incomplete")):
        fail("Only actually observed terminal Responses enter the known-terminal count.")
    for key in ("responsesWithInternalErrors", "responsesWithIncompleteEvidence", "responsesWithSuccessfulSourceExecution"):
        if captures[key] > captures["questionPOSTs"]:
            fail("Native observation counts exceed submitted questions.")
    if captures["strictNativeAcceptedResponses"] > min(captures["completed"], statuses.get("completed", 0)):
        fail("Unchanged-strict-grader question passes require completed records and completed Responses.")
    # These are separate reviewed observations, not disjoint populations. A
    # justified clarification/refusal can require no query, and a separately
    # observed recovered/nested error need not be a global unchanged-grader gate.
    # Never redefine that grader or infer intersections from aggregate marginals.


def validate_paired(comparison, phases):
    exact_keys(comparison, ("scope", "registeredConditionsPerPhase", "matchingKey", "equalFields", "matchedLedgerSha256",
                           "baselineContentReviewLedgerSha256", "finalContentReviewLedgerSha256", "matchedConditions", "exclusions", "transitions"))
    if comparison["scope"] != ["original", "regression"] or comparison["registeredConditionsPerPhase"] != 290:
        fail("Held-out questions cannot enter the 290-condition paired comparison.")
    if comparison["matchingKey"] != MATCHING_KEY or comparison["equalFields"] != EQUAL_FIELDS:
        fail("Exact condition pairing and equal question/source-premise contracts are required.")
    digest(comparison["matchedLedgerSha256"])
    for phase_name in ("baseline", "final"):
        field = phase_name + "ContentReviewLedgerSha256"
        digest(comparison[field])
        if comparison[field] != phases[phase_name]["contentReviewLedgerSha256"]:
            fail("Paired comparison points to another phase's content ledger.")
    matched = count(comparison["matchedConditions"])
    if matched > 290:
        fail("Paired conditions exceed the original plus regression population.")
    excluded = {name: {key: 0 for key in VERDICTS} for name in ("baseline", "final")}
    exclusions = comparison["exclusions"]
    if not isinstance(exclusions, list):
        fail("Symmetric exclusions need an explicit list.")
    reasons = set()
    for exclusion in exclusions:
        exact_keys(exclusion, ("reasonCode", "reason", "conditions", "baseline", "final", "evidenceSha256"))
        code = exclusion["reasonCode"]
        if not isinstance(code, str) or not re.fullmatch(r"[a-z][a-z0-9-]{2,80}", code) or code in reasons:
            fail("Every exclusion requires a unique, stable reason code.")
        reasons.add(code)
        bilingual(exclusion["reason"])
        n = count(exclusion["conditions"])
        if n == 0:
            fail("Zero-count exclusions are not evidence.")
        digest(exclusion["evidenceSha256"])
        for phase_name in ("baseline", "final"):
            verdicts(exclusion[phase_name], n)
            for verdict in VERDICTS:
                excluded[phase_name][verdict] += exclusion[phase_name][verdict]
    excluded_n = sum(item["conditions"] for item in exclusions)
    if matched + excluded_n != 290:
        fail("Symmetric exclusions must preserve all 290 registered conditions.")
    transitions = comparison["transitions"]
    expected = {(before, after) for before in MATCHED_VERDICTS for after in MATCHED_VERDICTS}
    if not isinstance(transitions, list) or len(transitions) != len(expected):
        fail("The complete three-by-three paired transition matrix is required.")
    actual = set()
    matrix = {}
    for row in transitions:
        exact_keys(row, ("baseline", "final", "conditions"))
        key = (row["baseline"], row["final"])
        if key not in expected or key in actual:
            fail("The paired transition matrix has invalid or duplicated verdicts.")
        actual.add(key)
        matrix[key] = count(row["conditions"])
    if sum(matrix.values()) != matched:
        fail("Paired transition counts do not equal the matched population.")
    for phase_name, axis in (("baseline", 0), ("final", 1)):
        full = sum_verdicts(phases[phase_name]["groups"][:2])
        for verdict in VERDICTS:
            retained = sum(n for key, n in matrix.items() if key[axis] == verdict)
            if retained + excluded[phase_name][verdict] != full[verdict]:
                fail("Paired transitions and symmetric exclusions do not reconcile to full source judgments.")
    return matrix


def validate_summary(study, *, allow_synthetic_fixture=False):
    exact_keys(study, ("schema", "date", "timeZone", "inputKind", "artifactSourceDateEpoch", "protocolSha256", "method",
                       "phases", "pairedComparison", "changes", "findings", "limitations", "calibrationSteps", "recommendation"))
    if study["schema"] != SCHEMA:
        fail("Unsupported new evaluation-summary schema.")
    if not isinstance(study["date"], str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", study["date"]):
        fail("The report date must use the exact ISO YYYY-MM-DD form.")
    try:
        date.fromisoformat(study["date"])
    except (ValueError, TypeError):
        fail("A valid separately dated report is required.")
    if study["date"] < "2026-10-15" or study["timeZone"] != "Asia/Tokyo":
        fail("This schema starts with the separately dated 2026-10-15 JST study.")
    if study["inputKind"] not in ("observed-reviewed-aggregate", "synthetic-fixture"):
        fail("Explicit observed or synthetic input provenance is required.")
    if study["inputKind"] == "synthetic-fixture" and not allow_synthetic_fixture:
        fail("Synthetic fixtures require an explicit fixture-only flag; they are never actual evaluation reports.")
    if count(study["artifactSourceDateEpoch"]) < 315532800:
        fail("A valid reproducible artifact epoch is required.")
    digest(study["protocolSha256"])
    public_text(study)
    method = study["method"]
    exact_keys(method, ("contentReview", "independentHumanSignoff", "strictGradersChanged", "originalVerdictsPreserved",
                        "favorableRetrySelection", "platformWideBugFixClaimed", "heldoutComparison", "unknownPolicy", "evidenceReferences"))
    if method["contentReview"] != "codex-supplemental-with-separate-review":
        fail("Identify supplemental content review and its separate review explicitly.")
    for key in ("independentHumanSignoff", "strictGradersChanged", "favorableRetrySelection", "platformWideBugFixClaimed"):
        if method[key] is not False:
            fail("Review/acceptance boundaries changed.")
    if method["originalVerdictsPreserved"] is not True:
        fail("All original judgments must be retained.")
    if method["heldoutComparison"] != "disjoint-groups-not-paired" or method["unknownPolicy"] != "retain-in-denominator-not-pass":
        fail("Held-out or unclear-verdict handling changed.")
    if method["evidenceReferences"] != "private-ledger-digests-not-public-evidence":
        fail("Hashes must not imply that private evidence is publicly available.")
    if not isinstance(study["phases"], list):
        fail("Phases must be an ordered list.")
    names = [phase.get("name") for phase in study["phases"]]
    allowed = ["qualification", "baseline", "targeted-01", "targeted-02", "final"]
    if len(names) != len(set(names)) or names != [name for name in allowed if name in names] or not {"qualification", "baseline", "final"}.issubset(names):
        fail("The required qualification/baseline/final phases or their order changed.")
    if "targeted-02" in names and "targeted-01" not in names:
        fail("A second targeted wave requires a first wave.")
    for phase in study["phases"]:
        validate_phase(phase)
    phases = {phase["name"]: phase for phase in study["phases"]}
    targeted_questions = sum(phase["captures"]["registeredQuestions"] for name, phase in phases.items() if name.startswith("targeted-"))
    if targeted_questions > 8:
        fail("The total targeted-question budget is eight.")
    if phases["baseline"]["groups"][2]["suiteSha256"] == phases["final"]["groups"][2]["suiteSha256"]:
        fail("Baseline and final held-out cases must be independently frozen disjoint sets.")
    validate_paired(study["pairedComparison"], phases)
    for field in ("changes", "findings", "limitations", "calibrationSteps"):
        if not isinstance(study[field], list):
            fail("Narrative sections must contain bilingual paragraph lists.")
        if field in ("limitations", "calibrationSteps") and not study[field]:
            fail("Report limitations and calibration steps must be explicit.")
        for paragraph in study[field]:
            bilingual(paragraph)
    bilingual(study["recommendation"])
    return study


def shared_blocks(study):
    """One content model renders both formats; all score tables derive from validated counts."""
    blocks = []
    def paragraph(ja, en):
        blocks.extend([{"kind": "paragraph", "lang": "ja", "text": ja}, {"kind": "paragraph", "lang": "en", "text": en}])
    def heading(ja, en):
        blocks.append({"kind": "heading", "text": ja + " / " + en})
    def table(headers, rows):
        blocks.append({"kind": "table", "headers": headers, "rows": rows})
    if study["inputKind"] == "synthetic-fixture":
        paragraph("合成テスト用fixture — 実際の評価結果ではありません。", "SYNTHETIC TEST FIXTURE — NOT ACTUAL EVALUATION RESULTS.")
    heading("評価の範囲", "Evaluation scope")
    paragraph("この別冊は " + study["date"] + "（日本時間）の個別配置に対する評価を扱います。回答内容はCodexによる補足判定と別レビューで確認し、厳格なnative実行判定と分けます。独立した人間のsign-off、将来の回答保証、サービス全体のバグ修正証明は含みません。",
              "This dated report covers the individual deployment evaluated on " + study["date"] + " (Japan time). Codex supplemental content judgments and a separate review remain distinct from strict native-execution judgments. It provides no independent human sign-off, future-answer guarantee or service-wide bug-fix certification.")
    paragraph("標準構成はOntology 1件・Data Agent 1件です。資格確認2問5条件、初期51問296条件、必要に応じた限定確認最大8問、最終51問296条件を別フェーズとして扱います。未確認は分母に残して不合格側に数え、既定の確認質問分岐だけをNAとして扱います。",
              "The standard configuration contains one Ontology and one Data Agent. Qualification (two questions/five conditions), baseline (51/296), up to eight targeted questions and final (51/296) are separate phases. Unclear conditions remain in the denominator as non-passes; only the predeclared clarification branch may be NA.")
    heading("補助条件とnative条件の集計", "Supplemental and native-condition counts")
    rows = []
    for phase in study["phases"]:
        for group in phase["groups"]:
            for field, label in (("content", "補助条件 / Supplemental conditions"), ("strictNativeConditions", "厳格native / Strict native")):
                v = group[field]
                applicable = group["conditions"] - v["NA"]
                pct = percentage(v["PASS"], applicable)
                rows.append([phase["name"] + " / " + group["name"], label,
                             str(group["questions"]) + " / " + str(group["conditions"]),
                             "/".join(str(v[key]) for key in VERDICTS),
                             str(v["PASS"]) + "/" + str(applicable) + (" (" + pct + "%)" if pct is not None else " (N/A)")])
    table(["フェーズ・群 / Phase and group", "判定 / Review", "質問/条件 / Questions/conditions", "PASS/FAIL/UNCLEAR/NA", "PASS/適用条件 / Applicable"], rows)
    paragraph("補助条件の集計は、事実の正しさに加えて、指定されたID・見出し・説明などの必須項目と、条件で求めたソースやOntology経路の利用を含みます。この指標は回答内容・必須項目・取得経路の条件充足率であり、純粋な事実の正答率ではありません。事実誤り、回答項目の不足、取得経路の未達、取得中断や実行証拠の不足を区別して記録します。",
              "Supplemental conditions cover factual correctness, required IDs, headings and explanations, and any required source or Ontology route. The metric is condition fulfillment across answer content, required elements and retrieval routes, not pure factual accuracy. Factual errors, omitted answer elements, unmet routes, interrupted captures and incomplete execution evidence are recorded separately.")
    paragraph("資格確認の補助5条件には、回答の事実だけでなく、指定したOntologyの文脈とバインド先を実際に使う条件も含まれます。この達成率は純粋な事実の正答率ではありません。SQLへの代替経路で数値が正しくても、指定したOntology経路の条件は未達となる場合があります。元質問・回帰質問の採点条件は変更していません。",
              "The five supplemental qualification conditions cover both factual content and requested use of the specified Ontology context and its bound source. Their fulfillment rate is not a pure factual-accuracy rate. Correct values through a SQL fallback can still leave the requested Ontology-route condition unmet. Original and regression scoring conditions are unchanged.")
    heading("対応する条件だけの比較", "Exact paired-condition comparison")
    comp = study["pairedComparison"]
    before = sum(row["conditions"] for row in comp["transitions"] if row["baseline"] == "PASS")
    after = sum(row["conditions"] for row in comp["transitions"] if row["final"] == "PASS")
    n = comp["matchedConditions"]
    before_pct, after_pct = percentage(before, n), percentage(after, n)
    delta = percentage(after - before, n)
    table(["対象 / Scope", "初期 / Baseline", "最終 / Final", "差 / Change"],
          [[str(n) + " conditions", str(before) + "/" + str(n) + " (" + (before_pct + "%" if before_pct is not None else "N/A") + ")",
            str(after) + "/" + str(n) + " (" + (after_pct + "%" if after_pct is not None else "N/A") + ")", (delta + " pp") if delta is not None else "N/A"]])
    paragraph("対応比較の元母集団は元質問と回帰質問の290条件です。質問・条件・業務データと前提が一致する条件を正確なキーで対応付け、除外は両フェーズに同じように適用します。別々の未使用問題群6条件は、この比較に含めません。数値は補助条件の充足を観測したもので、指示修正の因果効果を証明しません。同じ構成の前後比較は反復確認として扱います。",
              "The paired population starts with 290 original and regression conditions. Exact keys match equal questions, criteria, business data and eligible premises; exclusions are symmetric. The two disjoint held-out sets (six conditions each) do not enter this comparison. These observations measure supplemental-condition fulfillment, not a causal effect of instruction changes. An unchanged-configuration comparison measures repeatability.")
    table(["初期→最終 / Baseline→final", "条件数 / Conditions"], [[row["baseline"] + " → " + row["final"], str(row["conditions"])] for row in comp["transitions"]])
    for exclusion in comp["exclusions"]:
        paragraph(str(exclusion["conditions"]) + "条件を両側から除外: " + exclusion["reason"]["ja"],
                  "Symmetrically excluded " + str(exclusion["conditions"]) + " conditions: " + exclusion["reason"]["en"])
    heading("取得と内部実行の状態", "Capture and internal-execution status")
    table(["フェーズ / Phase", "登録 / Registered", "既知POST / Known POST", "不明POST上限 / Uncertain upper bound", "未確定取得 / Unfinalized", "終端応答 / Terminal", "保持失敗 / Retained failures"],
          [[phase["name"]] + [str(phase["captures"][key]) for key in
            ("registeredQuestions", "questionPOSTs", "uncertainQuestionPOSTUpperBound", "unfinalizedCaptures", "knownTerminalResponses", "retainedFailures")]
           for phase in study["phases"]])
    table(["フェーズ / Phase", "応答: 完了/失敗/取消/不完全/不明 / Response status", "内部エラー / Internal errors", "証拠不完全 / Incomplete evidence", "ソース実行成功 / Source execution", "厳格採点の質問合格 / Strict question passes"],
          [[phase["name"], "/".join(str(phase["captures"][key]) for key in ("completed", "failed", "cancelled", "incomplete", "unknownResponseStatus")),
            str(phase["captures"]["responsesWithInternalErrors"]), str(phase["captures"]["responsesWithIncompleteEvidence"]),
            str(phase["captures"]["responsesWithSuccessfulSourceExecution"]),
            str(phase["captures"]["strictNativeAcceptedResponses"])] for phase in study["phases"]])
    paragraph("登録枠、通常のnative recordに残った送信数、不明な送信の上限、未確定の取得、終端応答を区別します。未確定の取得から送信や成功を推定しません。native recordの状態とResponseの状態は別に集計し、未送信・不明・失敗も全条件の母数に残します。",
              "Registered slots, submission counts in ordinary native records, uncertain submission upper bounds, unfinalized captures and terminal Responses are separate. Unfinalized captures never imply submission or success. Native record statuses and Response statuses are counted independently; unsubmitted, unknown and failed slots remain in the full condition denominator.")
    paragraph("全フェーズでHTTP 300秒、capture 900秒、定義取得600秒を固定し、質問ごとに新しい会話を使用します。消費済み枠を再送して良い回答だけを採用しません。HTTP成功やResponse完了と、内部クエリ成功は別です。内部エラーと証拠不完全の件数は重複する場合があり、合計して質問数とはしません。",
              "All phases freeze HTTP/capture/definition timeouts at 300/900/600 seconds and use a new conversation per question. Consumed slots are never resubmitted to select favorable answers. HTTP or Response completion does not prove internal-query success. Internal-error and evidence-incomplete counts may overlap and must not be summed into question counts.")
    paragraph("厳格採点の質問合格は、変更していない採点器が質問全体を合格とした数です。正当な確認質問や拒否ではクエリが不要な場合があります。ソース実行成功、回復済みを含む内部エラー、証拠不完全は別の観測件数であり、合計や差から合格との重なりを推定しません。元の条件別判定とエラーを保持します。",
              "Strict question passes count whole-question passes from the unchanged grader. A justified clarification or refusal can require no query. Successful source execution, observed internal errors including recovered errors, and incomplete evidence are separate observations; their totals or differences do not establish overlap with passes. Original condition judgments and errors are retained.")
    for field, ja, en in (("changes", "検証した修正", "Verified changes"), ("findings", "観測した結果", "Observed findings"),
                          ("limitations", "残る制約", "Remaining limitations"), ("calibrationSteps", "校正と再評価の手順", "Calibration and reevaluation procedure")):
        heading(ja, en)
        if not study[field]:
            paragraph("この欄に報告する変更はありません。", "No changes are reported in this section.")
        for index, value in enumerate(study[field], 1):
            prefix = str(index) + ". " if field == "calibrationSteps" else ""
            paragraph(prefix + value["ja"], prefix + value["en"])
    heading("推奨と資料の整合性", "Recommendation and artifact consistency")
    paragraph(study["recommendation"]["ja"], study["recommendation"]["en"])
    paragraph("WordとHTMLは同一の共有本文・集計JSONから生成します。本文・表の一致、公開情報検査、General分類と対応SHAを確認します。Microsoft Wordの描画・ページ割りとブラウザー操作は、別の実検証receiptがない限り未確認です。資料検証とmainへのマージは、AI回答や全native機能の受入証明ではありません。",
              "Word and HTML are generated from the same shared content and summary JSON. Text/table parity, public-information checks, General classification and paired hashes are checked. Microsoft Word rendering/pagination and browser interaction remain unverified without separate actual receipts. Artifact validation and merging main do not certify AI-answer or all-native-feature acceptance.")
    heading("構成と証跡の指紋", "Configuration and evidence fingerprints")
    paragraph("以下は私有記録を照合するSHA-256です。私有証跡の公開や独立検証を意味しません。実際のWorkspace/Item ID、質問本文、正解、実回答、生trace、認証は含めません。",
              "These SHA-256 values reconcile private records; they do not publish or independently verify the evidence. Live workspace/item identifiers, question text, answer keys, actual responses, raw traces and credentials are omitted.")
    table(["対象 / Record", "SHA-256"], [["Protocol", study["protocolSha256"]], ["Exact paired ledger", comp["matchedLedgerSha256"]]] +
          [[phase["name"] + " / " + key, phase[key]] for phase in study["phases"] for key in ("publicationDefinitionSha256", "sourceDefinitionSha256", "sourceBusinessSha256", "captureLedgerSha256", "contentReviewLedgerSha256", "strictNativeReviewLedgerSha256", "independentContentReviewSha256")])
    return blocks


def text_content(blocks):
    for block in blocks:
        if block["kind"] == "table":
            yield from block["headers"]
            for row in block["rows"]:
                yield from row
        else:
            yield block["text"]


def canonical(text):
    return re.sub(r"\s+", "", text).translate(str.maketrans({"（": "(", "）": ")"}))


def private_output(path, repo):
    path = Path(path).resolve()
    if path == repo or path.is_relative_to(repo):
        fail("Build into a fresh private directory outside every Git checkout.")
    for parent in (path, *path.parents):
        if (parent / ".git").exists():
            fail("Build output must remain outside every Git checkout.")
    if path.exists() and any(path.iterdir()):
        raise FileExistsError("Use a fresh output directory; previous artifacts remain immutable.")
    ancestor = path
    while not ancestor.exists():
        ancestor = ancestor.parent
    if ancestor.stat().st_uid != os.getuid() or ancestor.stat().st_mode & 0o077:
        fail("The output parent must be owned private storage with mode 0700.")
    return path


def build(summary_path, output, *, repo=REPO, allow_synthetic_fixture=False):
    summary_path = Path(summary_path).resolve()
    repo = Path(repo).resolve()
    raw = summary_path.read_bytes()
    study = validate_summary(json.loads(raw), allow_synthetic_fixture=allow_synthetic_fixture)
    output = private_output(output, repo)
    sys.path.insert(0, str(repo / "tools/docs"))
    from furusato_docs.docx_kit import DocumentBuilder
    from furusato_docs.oox import StyleCarrier, apply_japanese_typography, normalise_package_metadata
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from lxml import etree
    from lxml import html as lhtml
    output.mkdir(parents=True, mode=0o700)
    os.chmod(output, 0o700)
    blocks = shared_blocks(study)
    marker = "SYNTHETIC-FIXTURE-" if study["inputKind"] == "synthetic-fixture" else ""
    stem = marker + "furusato-ontology-v2-evaluation-" + study["date"].replace("-", "")
    word, web = output / (stem + ".docx"), output / (stem + ".html")
    source_sha = hashlib.sha256(raw).hexdigest()
    shared_sha = hashlib.sha256(json.dumps(blocks, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    previous_epoch = os.environ.get("SOURCE_DATE_EPOCH")
    os.environ["SOURCE_DATE_EPOCH"] = str(study["artifactSourceDateEpoch"])
    try:
        builder = DocumentBuilder(StyleCarrier.resolve(repo), output / "shell.docx")
        doc = builder.document
        for section in doc.sections:
            for part in (section.header, section.footer, section.first_page_header, section.first_page_footer):
                for child in list(part._element):
                    part._element.remove(child)
                part._element.append(OxmlElement("w:p"))
        for field in list(doc.settings.element.findall(qn("w:updateFields"))):
            doc.settings.element.remove(field)
        title = marker + "Ontology V2・Data Agent 実評価と校正手順"
        builder.paragraph(title, style="Title")
        builder.paragraph("Ontology V2 and Data Agent evaluation and calibration", size=14)
        builder.paragraph(study["date"] + " · Asia/Tokyo · Furusato Workshop 3.0.0")
        for block in blocks:
            if block["kind"] == "heading":
                builder.heading(block["text"], 1, new_page=False)
            elif block["kind"] == "table":
                widths = {2: [2.8, 6.8], 4: [2.8, 2.1, 2.1, 2.6], 5: [2.4, 1.7, 1.5, 2.2, 1.8],
                          6: [1.5, 1.1, 2.3, 1.5, 1.7, 1.5], 7: [1.4, 1.0, 1.4, 1.8, 1.4, 1.3, 1.3]}[len(block["headers"])]
                builder.table(block["headers"], block["rows"], caption="評価・校正 / Evaluation and calibration", widths=widths, font_size=8, header_size=8)
            else:
                builder.paragraph(block["text"], size=10, space_after=7)
        builder.paragraph("Source summary SHA-256: " + source_sha, size=8)
        builder.paragraph("Shared content SHA-256: " + shared_sha, size=8)
        doc.core_properties.title = title + " — " + study["date"]
        doc.core_properties.subject = "Counts-only, separately dated evaluation; content/native judgments remain distinct"
        for style in doc.styles:
            if hasattr(style, "font"):
                style.font.name = "Noto Sans CJK JP"
                properties = style.element.get_or_add_rPr()
                fonts = properties.find(qn("w:rFonts"))
                if fonts is None:
                    fonts = OxmlElement("w:rFonts")
                    properties.append(fonts)
                for attr in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
                    fonts.set(qn(attr), "Noto Sans CJK JP")
        for run in doc.element.iter(qn("w:r")):
            properties = run.find(qn("w:rPr"))
            if properties is None:
                properties = OxmlElement("w:rPr")
                run.insert(0, properties)
            fonts = properties.find(qn("w:rFonts"))
            if fonts is None:
                fonts = OxmlElement("w:rFonts")
                properties.append(fonts)
            for attr in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
                fonts.set(qn(attr), "Noto Sans CJK JP")
        builder.save(word)
        apply_japanese_typography(word)
        normalise_package_metadata(word)
    finally:
        if previous_epoch is None:
            os.environ.pop("SOURCE_DATE_EPOCH", None)
        else:
            os.environ["SOURCE_DATE_EPOCH"] = previous_epoch
    with zipfile.ZipFile(word) as archive:
        parts = {name: archive.read(name) for name in archive.namelist()}
    for name, blob in parts.items():
        if name.startswith("word/") and name.endswith(".xml") and (b"fldChar" in blob or b"instrText" in blob):
            fail("The report must be field-free.")
    if re.search(rb"<(?:\w+:)?Pages\b", parts["docProps/app.xml"]):
        fail("A cached Office page count is not verified pagination.")
    if b"General" not in parts["docProps/custom.xml"]:
        fail("General classification is missing.")
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    word_text = "".join(etree.fromstring(parts["word/document.xml"]).xpath("//w:t/text()", namespaces=ns))
    word_sha = hashlib.sha256(word.read_bytes()).hexdigest()
    body, toc = [], []
    index = 0
    for block in blocks:
        if block["kind"] == "heading":
            index += 1
            anchor = "section-" + str(index)
            body.append('<h2 id="' + anchor + '">' + html.escape(block["text"]) + '</h2>')
            toc.append('<a href="#' + anchor + '">' + html.escape(block["text"]) + '</a>')
        elif block["kind"] == "table":
            body.append('<div class="table-wrap"><table><thead><tr>' + ''.join('<th scope="col">' + html.escape(value) + '</th>' for value in block["headers"]) + '</tr></thead><tbody>')
            body.extend('<tr>' + ''.join('<td>' + html.escape(value) + '</td>' for value in row) + '</tr>' for row in block["rows"])
            body.append('</tbody></table></div>')
        else:
            body.append('<p lang="' + block["lang"] + '">' + html.escape(block["text"]) + '</p>')
    css = """:root{font-family:'Noto Sans CJK JP','Yu Gothic UI',sans-serif;line-height:1.75;color:#203048;background:#eef3f9}*{box-sizing:border-box}body{max-width:1160px;margin:0 auto;padding:24px}header,main,nav{background:#fff;padding:26px;margin:0 0 20px;border-radius:10px}header{border-top:6px solid #174c88}h1{font-size:1.8rem}h2{font-size:1.35rem;color:#174c88;margin-top:30px}p,td{overflow-wrap:anywhere}nav{display:grid;gap:7px}a{color:#175c9b}.table-wrap{overflow-x:auto;margin:20px 0}table{width:100%;min-width:680px;border-collapse:collapse;font-size:.82rem;line-height:1.6}th,td{border:1px solid #d6dfea;padding:9px;text-align:left;vertical-align:top}th{background:#174c88;color:white}tbody tr:nth-child(even){background:#eef3f9}footer{font-size:.75rem;overflow-wrap:anywhere}button{font:inherit;background:#174c88;color:white;border:0;padding:8px 14px;border-radius:5px}@media(max-width:600px){body{padding:10px}header,main,nav{padding:16px}h1{font-size:1.4rem}}@media print{@page{size:A4;margin:16mm}body{max-width:none;padding:0;background:white}header,main{padding:0;margin:0;border-radius:0}nav,.print{display:none}header{border-top:0}h2{break-after:avoid}tr{break-inside:avoid}table{min-width:0;font-size:7.5pt}th,td{padding:5px}.table-wrap{overflow:visible}a{color:inherit}}"""
    document = '<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="icon" href="data:,"><title>' + html.escape(title) + '</title><meta name="source-summary-sha256" content="' + source_sha + '"><meta name="shared-content-sha256" content="' + shared_sha + '"><meta name="paired-word-sha256" content="' + word_sha + '"><style>' + css + '</style></head><body><header><h1>' + html.escape(title) + '</h1><p>' + study["date"] + ' · Asia/Tokyo · Furusato Workshop 3.0.0</p><button class="print" onclick="window.print()">印刷 / Print</button></header><nav aria-label="目次 / Contents">' + ''.join(toc) + '</nav><main>' + ''.join(body) + '</main><footer>Source summary SHA-256: ' + source_sha + '<br>Shared content SHA-256: ' + shared_sha + '<br>Paired Word SHA-256: ' + word_sha + '</footer></body></html>'
    web.write_text(document, encoding="utf-8")
    html_text = ''.join(lhtml.fromstring(document).xpath("//main//text()"))
    for value in text_content(blocks):
        if canonical(value) not in canonical(word_text) or canonical(value) not in canonical(html_text):
            fail("Shared content was omitted from a rendered format.")
    public_text(word_text)
    public_text(html_text)
    validation = {"schema": ARTIFACT_SCHEMA, "date": study["date"], "inputKind": study["inputKind"],
                  "syntheticFixtureIsNotActualEvidence": study["inputKind"] == "synthetic-fixture",
                  "sourceSummarySha256": source_sha, "sharedContentSha256": shared_sha,
                  "sourceDateEpoch": study["artifactSourceDateEpoch"], "contentBlocks": len(blocks),
                  "conditionDenominatorsValidated": True, "pairedTransitionsReconciled": True,
                  "wordHtmlSharedContentParity": True, "publicTextLeakageChecksPassed": True,
                  "generalClassificationNormalized": True, "dynamicWordFields": 0, "fakeOfficePageCountPresent": False,
                  "microsoftWordRenderChecked": False, "libreOfficeRenderChecked": False, "htmlBrowserChecked": False,
                  "artifactValidationIsAnswerQualityAcceptance": False, "privateLedgerContentsIndependentlyVerifiedByRenderer": False,
                  "outputs": {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in (word, web)}}
    (output / "artifact-validation.json").write_text(json.dumps(validation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output / "shared-content.json").write_text(json.dumps(blocks, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output / "shell.docx").unlink(missing_ok=True)
    return validation


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--repo", type=Path, default=REPO)
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--allow-synthetic-fixture", action="store_true")
    args = parser.parse_args()
    if args.validate_only:
        study = validate_summary(json.loads(args.summary.read_text(encoding="utf-8")), allow_synthetic_fixture=args.allow_synthetic_fixture)
        print(json.dumps({"schema": study["schema"], "valid": True, "inputKind": study["inputKind"], "actualLedgerVerificationPerformed": False}))
    elif args.out is None:
        parser.error("--out is required unless --validate-only is selected")
    else:
        print(json.dumps(build(args.summary, args.out, repo=args.repo, allow_synthetic_fixture=args.allow_synthetic_fixture), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
