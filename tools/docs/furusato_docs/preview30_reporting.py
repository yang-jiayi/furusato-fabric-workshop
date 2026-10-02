"""Shared, source-only presentation of an explicitly reviewed original-suite run."""

from __future__ import annotations

from . import preview30_public_evidence as public

VERDICT_KEYS = ("pass", "fail", "executionUnverified", "blocked", "notApplicable")
SOURCE_LANGUAGES = ("sql", "gql", "kql", "dax")
UNVERIFIED = ("未検証", "unverified")
LEGACY_CASE_ROWS = (
    ("T01", 7, 0, 1, False), ("T02", 6, 0, 1, False), ("T03", 6, 0, 2, False),
    ("T04", 6, 5, 1, False), ("T05", 9, 5, 2, False), ("T06", 2, 8, 1, False),
    ("T07", 5, 3, 1, False), ("T08", 5, 2, 0, False), ("T09", 2, 6, 0, False),
    ("T10", 0, 7, 0, True),
)


def require_legacy_run(run):
    if run["counts"] != dict(zip(VERDICT_KEYS, (48, 36, 0, 0, 0))) or run["accepted"] or run["promoted"]:
        raise ValueError("This frozen Preview decision is48 PASS/36 FAIL, quality-unaccepted and unpromoted")
    method = run.get("method", {})
    if (
        method.get("surface") != "native-ui" or method.get("transport") != "responses"
        or method.get("stage") != "sandbox" or method.get("runtime") != "preview"
        or method.get("recordedModel") != "gpt-5.6-terra"
        or method.get("judgment") != "manual-fixed-rubric-offline"
        or method.get("sourceExecutions") != {"sql": 5, "gql": 2, "kql": 2}
        or method.get("distinctBackendConversationsProven") != 10
        or run["independentExecutionTraces"] != 7
    ):
        raise ValueError("Final method/evidence changed; review before regenerating public reports")
    if "caseAggregates" in run:
        cases = run["caseAggregates"]
        if tuple(
            (case["case"], case["counts"]["pass"], case["counts"]["fail"], case["sourceAttempts"], case["nativeGate"])
            for case in cases
        ) != LEGACY_CASE_ROWS or any(
            case["counts"][key] for case in cases for key in ("executionUnverified", "blocked", "notApplicable")
        ):
            raise ValueError("Legacy case aggregates differ from the frozen report rows; select a new reviewed run id")


def counts_text(run):
    return " / ".join(
        f"{run['counts'][key]} {label}"
        for key, label in zip(VERDICT_KEYS, ("PASS", "FAIL", "execution-unverified", "BLOCKED", "N/A"))
    ) + " = 84"


def acceptance_text(run):
    return (
        ("元suiteの受入済み（審査記録のみ）", "original suite accepted in the reviewed record only")
        if run["accepted"] else ("AI回答品質は未合格", "AI answer quality is not accepted")
    )


def presentation(run):
    if run["accepted"]:
        return {
            "ja": "実装・検証結果を収録したPreview — 元suiteの審査記録上の受入のみ／全機能合格・GAではありません",
            "en": "Preview with implementation and verification results — reviewed original-suite acceptance only; not all-feature acceptance or GA",
        }
    return {
        "ja": "実装・検証結果を収録したPreview — AI回答品質は未合格／GAではありません",
        "en": "Preview with implementation and verification results — AI answer quality not accepted; not GA",
    }


def metadata_presentation(metadata):
    return metadata.get("previewPresentation", presentation({"accepted": False}))


def selection_notice(run):
    accepted_ja, accepted_en = acceptance_text(run)
    promotion_ja, promotion_en = (
        ("promotionあり（審査記録のみ）", "promotion recorded only")
        if run["promoted"] else ("main未promotion（記録）", "main is not promoted in the record")
    )
    return (
        f"明示選択: {run['id']} — {counts_text(run)}。{accepted_ja}。{promotion_ja}。元10問/84条件と履歴を保持。全機能合格・公開・操作許可ではありません。",
        f"Explicit selection: {run['id']} — {counts_text(run)}. {accepted_en}; {promotion_en}. Original ten/84 and historical ledgers are retained. Not all-feature acceptance, publication or authorization to act.",
    )


def execution_evidence(run):
    method = run.get("method", {})
    cases = run.get("caseAggregates", [])
    completion = {
        "completed": sum(case.get("completedNativeResponse") is True for case in cases),
        "notCompleted": sum(case.get("completedNativeResponse") is False for case in cases),
        "unverified": 10 - sum("completedNativeResponse" in case for case in cases),
    }
    result = {
        "sourceAttempts": method.get("sourceExecutions"),
        "successfulSourceExecutions": method.get("successfulSourceExecutions"),
        "rejectedSourceAttempts": method.get("rejectedSourceAttempts"),
        "independentlyTracedQuestionSlots": run["independentExecutionTraces"],
        "distinctBackendConversationsProven": method.get("distinctBackendConversationsProven"),
        "freshBackendProof": run["freshBackendProof"],
        "nativeResponseCompletion": completion,
    }
    for field, output in (
        ("sourceAttempts", "sourceAttemptCount"),
        ("successfulSourceExecutions", "successfulSourceExecutionCount"),
        ("rejectedSourceAttempts", "rejectedSourceAttemptCount"),
    ):
        result[output] = sum(result[field].values()) if result[field] is not None else None
    return result


def execution_completeness_notice():
    return (
        "source実行成功でも不完全・打切り結果が返る場合があり、成功回数は返却行/query結果の完全性を証明しません。同じcaseの後続aggregateが完全でも、先の返却結果が完全になるわけではありません。native応答の終端完了は別のproofで、打切り数の未掲載は打切り0を意味しません。",
        "Successful source calls can return incomplete/truncated results; their counts do not prove that all returned rows or query results are complete. A later complete aggregate in the same case does not retroactively complete an earlier result. Terminal native-response completion is separate proof; omitted truncation counts never imply zero.",
    )


def selected_context():
    reasons = {
        "scopedCompatibility": (
            "選択runに紐づくUI/connector互換性の追加審査記録なし。未検証・新規再確認なし。旧T04結果を流用しません。",
            "No separately reviewed UI/connector compatibility facts are bound to this selected run. Unverified / not newly rechecked; do not reuse the old T04 outcome.",
        ),
        "postcheck": (
            "選択runに紐づくpostcheckの追加審査記録なし。定義・公開・選択scopeの状態は未検証・新規再確認なし。",
            "No separately reviewed postcheck is bound to this selected run. Definitions, publications and selected scope are unverified / not newly rechecked.",
        ),
        "externalSdk": (
            "選択runに紐づく外部SDKの追加審査記録なし。送信数・blocker・修復は未検証・新規再確認なし。",
            "No separately reviewed external SDK qualification is bound to this selected run. Submission count, blocker and repair are unverified / not newly rechecked.",
        ),
    }
    return {
        key: {
            "status": "unverified-not-newly-rechecked",
            "reason": {"ja": ja, "en": en},
        }
        for key, (ja, en) in reasons.items()
    }


def selection_metadata(evidence):
    run = public.selected_original_suite_run(evidence, required=True)
    if run["id"] == public.LEGACY_ORIGINAL_SUITE_RUN_ID:
        require_legacy_run(run)
    result = {
        "selectedOriginalSuiteRunId": run["id"],
        "finalEvaluation": run,
        "originalSuiteAccepted": run["accepted"],
        "aiAnswerQualityAccepted": run["accepted"],
        "mainPromoted": run["promoted"],
        "previewPresentation": presentation(run),
    }
    if run["id"] != public.LEGACY_ORIGINAL_SUITE_RUN_ID:
        result["selectedSuiteExecutionEvidence"] = execution_evidence(run)
        result["selectedRunContext"] = selected_context()
    return result


def method_rows(run):
    method = run.get("method", {})
    proof = execution_evidence(run)
    rows = [
        [label, method.get(key) if method.get(key) is not None else UNVERIFIED]
        for key, label in (
            ("surface", ("評価surface", "Evaluation surface")),
            ("transport", ("transport", "Transport")),
            ("stage", ("stage", "Stage")),
            ("runtime", ("runtime", "Runtime")),
            ("recordedModel", ("記録model", "Recorded model")),
            ("judgment", ("固定rubric判定方法", "Fixed-rubric judgment")),
        )
    ]
    rows += [
        [("送信/前提blocked質問", "Submitted/preblocked questions"), f"{run['submittedQuestions']} / {run['preblockedQuestions']}"],
        [("内容/要求証拠FAIL / native受入FAIL", "Content/required-evidence FAIL / native-acceptance FAIL"),
         f"{run['failureCounts']['content']} / {run['failureCounts']['nativeAcceptance']}"],
        [("source試行 / 成功 / 拒否", "Source attempts / successes / rejections"),
         " / ".join(
             str(proof[key]) if proof[key] is not None else "未検証 (unverified)"
             for key in ("sourceAttemptCount", "successfulSourceExecutionCount", "rejectedSourceAttemptCount")
         )],
        [("独立trace付き質問slot", "Independently traced QUESTION slots"), str(run["independentExecutionTraces"])],
        [("証明された別backend会話", "Proven distinct backend conversations"),
         proof["distinctBackendConversationsProven"] if proof["distinctBackendConversationsProven"] is not None else UNVERIFIED],
        [("fresh backend proof", "Fresh-backend proof"), str(run["freshBackendProof"])],
        [("native応答の終端 完了 / 未完了 / 未検証", "Terminal native responses completed / not completed / unverified"),
         " / ".join(str(proof["nativeResponseCompletion"][key]) for key in ("completed", "notCompleted", "unverified"))],
    ]
    return rows


def source_rows(run):
    method = run.get("method", {})
    return [
        [
            language.upper(),
            *[
                method.get(field, {}).get(language, UNVERIFIED) if method.get(field) is not None else UNVERIFIED
                for field in ("sourceExecutions", "successfulSourceExecutions", "rejectedSourceAttempts")
            ],
        ]
        for language in SOURCE_LANGUAGES
    ]


def case_verdict_rows(run):
    return [
        [
            case["case"], *[str(case["counts"][key]) for key in VERDICT_KEYS],
            ("固定block失敗", "fixed-block failure") if case["nativeGate"] else "—",
        ]
        for case in run["caseAggregates"]
    ]


def case_execution_rows(run):
    rows = []
    for case in run["caseAggregates"]:
        completion = (
            ("完了", "completed") if case["completedNativeResponse"] else ("未完了", "not completed")
        ) if "completedNativeResponse" in case else UNVERIFIED
        languages = UNVERIFIED
        if "successfulQueryLanguages" in case:
            languages = ", ".join(language.upper() for language in case["successfulQueryLanguages"])
            if not languages:
                languages = UNVERIFIED if case["successfulSourceExecutions"] else "—"
        rows.append([
            case["case"], str(case["sourceAttempts"]), str(case["successfulSourceExecutions"]),
            str(case["rejectedSourceAttempts"]), completion, languages,
        ])
    return rows
