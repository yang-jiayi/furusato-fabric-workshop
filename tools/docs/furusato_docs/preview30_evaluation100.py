"""Counts-only frozen100 disclosure; never reads the private suite or ledger."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
from datetime import date
from pathlib import Path

from .preview30_public_evidence import exact_fields, integer, timestamp

SCHEMA = "furusato100-public-study/v1"
REVIEW_POLICY_TIMING = "method-preregistered-tooling-finalized-during-capture"
REVIEW_FIELDS = {
    "mode", "policySha256", "reviewPolicyTiming", "fullReviewPolicyPreregistered",
    "methodIntentSha256", "timingAdmissionReceiptSha256",
    "methodTimingEvidence", "methodTimingIndependentlyCertified", "methodPreregistered",
    "methodPreregistrationClaim", "originalMethodTimingCorroborated", "reviewToolingPreregistered",
    "methodEvidenceHashProvenance", "timingAdmissionBeforeContentGrading",
    "rubricUnchanged", "noIndependentHumanSignoff", "automaticSemanticPass",
}
MAX_BYTES = 256 * 1024
SHA = re.compile(r"[0-9a-f]{64}")
LABEL = re.compile(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*")
IDENTITY = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}|[0-9a-f]{32}", re.I)
AXES = {
    "factualCorrectness": ("pass", "fail", "unknown", "notApplicable"),
    "contextualHelpfulness": ("pass", "fail", "unknown"),
    "protectiveBoundary": ("pass", "fail", "unknown", "notApplicable", "nativeServiceBlock", "retainedServiceBlock"),
    "answerContent": ("pass", "fail", "unknown"),
}
TERMINALS = (
    "answerCaptured", "nativeServiceBlocked", "nativeErrorReply",
    "protectedNotResubmitted", "notSubmitted", "submissionUncertain", "captureFailed",
)
METRIC_FIELDS = {
    "uniqueCases", "terminalCases", "submissionIntents", "capturedResponses",
    "nativeBlocks", "unknownOutcomes", "terminalCounts", "axes",
}
RUN_FIELDS = {
    "candidate", "bindingSha256", "reviewPolicySha256", "sourceReportSha256", "metrics",
}
ROOT_FIELDS = {
    "schemaVersion", "evidenceKind", "snapshotDate", "projectedAtUtc", "denominators",
    "bindings", "bindingSha256", "review", "observability", "final",
    "baseline", "intervention", "heldout", "combined",
}
CONTINUATION_PLAN_SHA256 = "7083551695d1fbc3689748517f64b1c50365fc864c64e04f7d43ba202fecbf20"
ORIGINAL_HELDOUT_PLAN_SHA256 = "3201eead130d96a2be84e2d503a4e1f016f31407ef3f28f86d07aae2df2e4ef2"
CONTINUATION_CANDIDATE_SHA256 = "3c225b426acdfb782495a19000bc0ce41a69b1853f829a6ba227f30675a4f25f"
CONTINUATION_DEFINITION_SHA256 = "ebdf70c2bff27fb3542e969bfd73db44a5a31f7cc5de19c4bf222b22dd58a007"
EXECUTION_HASH_FIELDS = (
    "originalPlanSha256", "continuationPlanSha256", "originalStoppedBatchSha256",
    "reconciliationSha256", "reportSha256",
)
EXECUTION_TRUE_FIELDS = (
    "originalNoResumePolicyAmended", "originalClaimsRemainSpent", "noBestOf", "stopOnNextFailure",
)
EXECUTION_FALSE_FIELDS = (
    "executionAmendmentPreregistered", "originalProtocolWasFullyFollowed",
    "retrySubmittedOrUncertainCases", "sourceTransportCandidateOrQuestionChanges", "heldoutFeedbackTuning",
)
EXECUTION_FIELDS = set(EXECUTION_HASH_FIELDS + EXECUTION_TRUE_FIELDS + EXECUTION_FALSE_FIELDS) | {
    "label", "priorCaptured", "priorUnknown", "eligibleUnsent", "priorUnknownHttpStatus",
    "continuationInvocations", "outcome", "continuationTerminalCounts",
}


def require(condition, message):
    if not condition:
        raise ValueError("frozen100: " + message)


def fields(value, required, name, optional=()):
    exact_fields(value, set(required) | set(optional), "frozen100 " + name, required)


def digest(value):
    """Canonical object hash; exact input-file hashes are computed separately."""
    return hashlib.sha256(json.dumps(
        value, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")).hexdigest()


def sha256(value):
    require(isinstance(value, str) and SHA.fullmatch(value) is not None, "invalid SHA256")
    return value


def label(value):
    require(
        isinstance(value, str) and 1 <= len(value) <= 64
        and LABEL.fullmatch(value) is not None and IDENTITY.search(value) is None,
        "public labels must be short lowercase slugs, not identities, URLs, paths or prose",
    )


def _unique_fields(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "duplicate JSON field")
        result[key] = value
    return result


def _invalid_constant(_):
    raise ValueError("frozen100: non-finite JSON numbers are forbidden")


def _sum_metrics(left, right):
    return {
        key: _sum_metrics(left[key], right[key]) if isinstance(left[key], dict) else left[key] + right[key]
        for key in left
    }


def _metrics(value, denominator):
    fields(value, METRIC_FIELDS, "metrics")
    for key in METRIC_FIELDS - {"terminalCounts", "axes"}:
        integer(value[key], "frozen100 " + key, denominator)
    require(value["uniqueCases"] == value["terminalCases"] == denominator, "every selected slot needs a terminal accounting record")
    terminal = value["terminalCounts"]
    fields(terminal, TERMINALS, "terminal counts")
    require(sum(integer(terminal[key], key, denominator) for key in TERMINALS) == denominator, "terminal counts must partition the denominator")
    captured = terminal["answerCaptured"] + terminal["nativeServiceBlocked"] + terminal["nativeErrorReply"]
    uncertain = terminal["submissionUncertain"] + terminal["captureFailed"]
    require(value["capturedResponses"] == captured, "captured response count disagrees with terminal counts")
    require(value["submissionIntents"] == captured + uncertain, "submission intents must retain uncertain/failed submissions, without retries")
    require(value["nativeBlocks"] == terminal["nativeServiceBlocked"], "native blocks must remain separate from answers and retained blocks")
    require(value["unknownOutcomes"] == uncertain, "unknown outcomes cannot be silently removed")
    fields(value["axes"], AXES, "result axes")
    for axis, verdicts in AXES.items():
        counts = value["axes"][axis]
        fields(counts, verdicts, axis)
        require(sum(integer(counts[key], axis + "." + key, denominator) for key in verdicts) == denominator, "each result axis must retain its entire denominator")
    factual, helpful, protection, content = (value["axes"][axis] for axis in AXES)
    answer_count = terminal["answerCaptured"]
    blocks = terminal["nativeServiceBlocked"] + terminal["protectedNotResubmitted"]
    unavailable = terminal["notSubmitted"] + uncertain
    require(factual["unknown"] >= denominator - answer_count, "uncaptured/error/blocked answers cannot prove factual correctness or non-applicability")
    require(helpful["pass"] <= answer_count and helpful["fail"] >= blocks and helpful["unknown"] >= unavailable, "helpfulness cannot promote absent or native-blocked answers")
    require(
        protection["nativeServiceBlock"] == terminal["nativeServiceBlocked"]
        and protection["retainedServiceBlock"] == terminal["protectedNotResubmitted"]
        and protection["unknown"] >= denominator - answer_count - blocks,
        "protective service blocks must be explicit, not content/protection passes",
    )
    require(
        content["pass"] <= min(answer_count, helpful["pass"], factual["pass"] + factual["notApplicable"],
                               protection["pass"] + protection["notApplicable"])
        and content["fail"] >= max(blocks, factual["fail"], helpful["fail"], protection["fail"])
        and content["unknown"] >= terminal["notSubmitted"] + terminal["submissionUncertain"],
        "content cannot pass without captured, reviewed supporting axes; unknown is not zero accuracy",
    )


def _run(value, denominator, binding_sha, policy_sha, *, combined=False):
    extra = {"finalDevelopmentReportSha256", "heldoutReportSha256"} if combined else set()
    fields(value, RUN_FIELDS | extra, "run", {"buckets"})
    candidate = value["candidate"]
    fields(candidate, {"profileLabel", "candidateSha256", "definitionSha256"}, "candidate")
    label(candidate["profileLabel"])
    sha256(candidate["candidateSha256"])
    sha256(candidate["definitionSha256"])
    for key in ("bindingSha256", "reviewPolicySha256", "sourceReportSha256", *extra):
        sha256(value[key])
    require(value["bindingSha256"] == binding_sha and value["reviewPolicySha256"] == policy_sha, "run must bind the same suite, source files, rubric and admitted review policy, not claim full-policy preregistration")
    _metrics(value["metrics"], denominator)
    if "buckets" not in value:
        return
    buckets = value["buckets"]
    require(isinstance(buckets, list) and 1 <= len(buckets) <= 100, "invalid bucket inventory")
    names, total = set(), None
    for bucket in buckets:
        fields(bucket, {"label", "metrics"}, "bucket")
        label(bucket["label"])
        require(bucket["label"] not in names, "duplicate bucket label")
        names.add(bucket["label"])
        fields(bucket["metrics"], METRIC_FIELDS, "bucket metrics")
        count = integer(bucket["metrics"]["uniqueCases"], "bucket denominator", denominator)
        _metrics(bucket["metrics"], count)
        total = copy.deepcopy(bucket["metrics"]) if total is None else _sum_metrics(total, bucket["metrics"])
    require(total == value["metrics"], "bucket metrics must add exactly to the run")


def _execution_protocol(data):
    value = data["executionProtocol"]
    fields(value, EXECUTION_FIELDS, "execution protocol amendment")
    require(value["label"] == "post-stop-unsent-slots-only", "unknown execution amendment")
    for key in EXECUTION_HASH_FIELDS:
        sha256(value[key])
    require(len({value[key] for key in EXECUTION_HASH_FIELDS}) == len(EXECUTION_HASH_FIELDS), "execution artifacts need distinct actual hashes")
    require(
        value["continuationPlanSha256"] == CONTINUATION_PLAN_SHA256
        and value["originalPlanSha256"] == ORIGINAL_HELDOUT_PLAN_SHA256,
        "amendment must bind the exact authorized continuation and original heldout plans",
    )
    require(
        data["final"]["developmentRound"] == "intervention"
        and data["final"]["candidateSha256"] == CONTINUATION_CANDIDATE_SHA256
        and data["heldout"]["candidate"]["definitionSha256"] == CONTINUATION_DEFINITION_SHA256,
        "amendment cannot change the actual frozen final candidate or definition",
    )
    require(value["reportSha256"] == data["combined"]["sourceReportSha256"], "execution report hash must bind the disclosed combined100 amendment report")
    require(all(value[key] is True for key in EXECUTION_TRUE_FIELDS), "original claims stay spent; at most one unsent-only invocation, no best-of, stop on the next failure")
    require(all(value[key] is False for key in EXECUTION_FALSE_FIELDS), "post-stop amendment is not preregistered or original-protocol compliance; no replay, tuning or binding changes")
    for key, count in (("priorCaptured", 2), ("priorUnknown", 1), ("eligibleUnsent", 17)):
        require(integer(value[key], key, 20) == count, "heldout amendment requires2 prior captures +1 prior unknown +17 eligible unsent slots")
    require(sum(value[key] for key in ("priorCaptured", "priorUnknown", "eligibleUnsent")) == data["denominators"]["heldout"], "amendment must retain all20 heldout slots")
    require(integer(value["priorUnknownHttpStatus"], "prior unknown HTTP status", 599) == 500, "the prior HTTP500 remains an unknown submission outcome, not a native service block")
    require(integer(value["continuationInvocations"], "continuation invocations", 1) == 1, "the single invocation must be terminal; no pending or second continuation")
    require(value["outcome"] in ("completed", "stopped-fail-closed"), "only durable reconciled terminal continuation outcomes are accepted")
    continued = value["continuationTerminalCounts"]
    fields(continued, TERMINALS, "continuation terminal counts")
    require(sum(integer(continued[key], key, 17) for key in TERMINALS) == 17, "continuation must account for exactly17 original unsent slots")
    require(continued["protectedNotResubmitted"] == 0, "the17 eligible slots cannot borrow prior blocks or completed records")
    failure_outcomes = sum(continued[key] for key in (
        "nativeServiceBlocked", "nativeErrorReply", "submissionUncertain", "captureFailed",
    ))
    require(failure_outcomes <= 1, "continuation must stop at the first new failed, blocked or uncertain submission")
    if value["outcome"] == "completed":
        require(continued["answerCaptured"] == 17, "completed continuation requires17 answer captures, not17 successful answers or waived unknowns")
    expected = dict(continued)
    expected["answerCaptured"] += value["priorCaptured"]
    expected["submissionUncertain"] += value["priorUnknown"]
    require(expected == data["heldout"]["metrics"]["terminalCounts"], "heldout metrics must reconcile prior2 captures, the unreplayed HTTP500 unknown and only17 first-submission slots")


def execution_binding(study, *, required=False):
    """Exact amendment bindings for an already validated study."""
    if "executionProtocol" not in study:
        require(not required, "dated snapshot requires explicit post-stop executionProtocol disclosure")
        return {}
    value = study["executionProtocol"]
    return {
        "executionProtocolSha256": digest(value),
        "executionProtocolHashes": {key: value[key] for key in EXECUTION_HASH_FIELDS},
    }


def validate(data):
    fields(data, ROOT_FIELDS, "study", {"executionProtocol"})
    require(data["schemaVersion"] == SCHEMA, "not a counts-only public study")
    require(data["evidenceKind"] in ("observed-live", "synthetic-private-test"), "invalid evidence kind")
    day = data["snapshotDate"]
    require(isinstance(day, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", day) is not None, "invalid snapshot date")
    date.fromisoformat(day)
    projected = timestamp(data["projectedAtUtc"], "frozen100 projection")
    require(projected.date() >= date.fromisoformat(day), "projection predates the snapshot")
    fields(data["denominators"], {"unique", "development", "heldout"}, "denominators")
    for key, expected in (("unique", 100), ("development", 80), ("heldout", 20)):
        require(integer(data["denominators"][key], key, 100) == expected, "denominators must remain 100 unique / 80 development / 20 heldout")
    binding = data["bindings"]
    fields(binding, {
        "suiteManifestSha256", "inputManifestSha256", "splitLockSha256", "rubricSha256",
        "sourceFileHashes", "sourceFilesSha256",
    }, "bindings")
    for key in set(binding) - {"sourceFileHashes"}:
        sha256(binding[key])
    source_hashes = binding["sourceFileHashes"]
    require(isinstance(source_hashes, dict) and 1 <= len(source_hashes) <= 128, "source-file hash inventory is required")
    for key, value in source_hashes.items():
        label(key)
        sha256(value)
    require(binding["sourceFilesSha256"] == digest(source_hashes), "source-file inventory digest mismatch")
    require(sha256(data["bindingSha256"]) == digest(binding), "suite/source/rubric binding digest mismatch")
    review = data["review"]
    fields(review, REVIEW_FIELDS, "review")
    require(review["mode"] == "ai-assisted", "this contract discloses AI-assisted review, not human sign-off")
    for key in ("policySha256", "methodIntentSha256", "timingAdmissionReceiptSha256"):
        sha256(review[key])
    require(
        len({review[key] for key in ("policySha256", "methodIntentSha256", "timingAdmissionReceiptSha256")}) == 3,
        "method intent, finalized policy and timing admission need distinct actual receipt hashes",
    )
    require(
        review["reviewPolicyTiming"] == REVIEW_POLICY_TIMING
        and review["methodTimingEvidence"] == "operator-receipt-and-filesystem-corroboration"
        and review["methodPreregistrationClaim"] == "corroborated-not-independently-proven"
        and review["methodEvidenceHashProvenance"] == "computedAtAdmission",
        "method timing is operator/filesystem corroboration only; hashes computed at admission are not preregistration proof",
    )
    require(all(review[key] is False for key in (
        "methodTimingIndependentlyCertified", "methodPreregistered",
        "fullReviewPolicyPreregistered", "reviewToolingPreregistered",
    )), "corroborated timing cannot certify method, policy or tooling preregistration")
    require(
        review["originalMethodTimingCorroborated"] is True
        and review["timingAdmissionBeforeContentGrading"] is True,
        "original timing corroboration and admission before content grading are required; do not rewrite capture records",
    )
    require(all(review[key] is True for key in (
        "rubricUnchanged", "noIndependentHumanSignoff",
    )) and review["automaticSemanticPass"] is False, "review mode cannot rewrite the rubric or certify semantic truth/human sign-off")
    fields(data["observability"], {"internalQueries", "backendConversations"}, "observability")
    require(all(value == "UNOBSERVABLE" for value in data["observability"].values()), "answer text is not native query or backend-conversation proof")
    final = data["final"]
    fields(final, {
        "stage", "developmentRound", "candidateSha256", "freezeReceiptSha256",
        "heldoutClaimSha256", "frozenAtUtc", "heldoutReservedAtUtc",
        "frozenBeforeHeldout", "heldoutIrreversiblySpent", "heldoutUsedForTuning",
        "bestOfPooling", "baselineAnswersBorrowed", "selectionPolicy",
    }, "final freeze")
    require(final["stage"] == "final-frozen" and final["developmentRound"] in ("baseline", "intervention"), "only the final frozen stage may disclose combined100")
    require(final["selectionPolicy"] == "all_once_declared_cases_no_best_of", "one attempt per declared slot, no retry or best-of pooling")
    require(final["frozenBeforeHeldout"] is True and final["heldoutIrreversiblySpent"] is True, "heldout must be irreversibly reserved after final freeze")
    require(all(final[key] is False for key in ("heldoutUsedForTuning", "bestOfPooling", "baselineAnswersBorrowed")), "heldout tuning, best-of pooling and borrowed baseline answers are forbidden")
    for key in ("candidateSha256", "freezeReceiptSha256", "heldoutClaimSha256"):
        sha256(final[key])
    require(
        timestamp(final["frozenAtUtc"], "final freeze") <= timestamp(final["heldoutReservedAtUtc"], "heldout reservation") <= projected,
        "freeze must precede the irreversible heldout reservation and final projection",
    )
    baseline, heldout, combined = data["baseline"], data["heldout"], data["combined"]
    _run(baseline, 80, data["bindingSha256"], review["policySha256"])
    _run(heldout, 20, data["bindingSha256"], review["policySha256"])
    _run(combined, 100, data["bindingSha256"], review["policySha256"], combined=True)
    runs = [baseline, heldout, combined]
    for run in (baseline, heldout):
        require(run["metrics"]["terminalCounts"]["protectedNotResubmitted"] == 0, "baseline and heldout cannot borrow prior-round native blocks")
    intervention = data["intervention"]
    if intervention is not None:
        fields(intervention, {"authorizationSha256", "baselineReportSha256", "meaningfulChange", "noSafetyBypass", "run"}, "single intervention")
        sha256(intervention["authorizationSha256"])
        require(intervention["baselineReportSha256"] == baseline["sourceReportSha256"], "intervention must refer to the exact baseline")
        require(intervention["meaningfulChange"] is True and intervention["noSafetyBypass"] is True, "intervention requires an authorized meaningful change, never a safety bypass")
        changed = intervention["run"]
        _run(changed, 80, data["bindingSha256"], review["policySha256"])
        require(all(changed["candidate"][key] != baseline["candidate"][key] for key in ("candidateSha256", "definitionSha256")), "intervention cannot rename or retry the unchanged candidate")
        require(changed["metrics"]["terminalCounts"]["protectedNotResubmitted"] == baseline["metrics"]["nativeBlocks"], "every baseline native block must remain protected and unsubmitted")
        runs.append(changed)
    require(final["developmentRound"] != "intervention" or intervention is not None, "selected final intervention is absent")
    development = baseline if final["developmentRound"] == "baseline" else intervention["run"]
    require(
        final["candidateSha256"] == development["candidate"]["candidateSha256"]
        and development["candidate"] == heldout["candidate"] == combined["candidate"],
        "combined100 must use the same final candidate for final development80 and heldout20",
    )
    require(
        combined["finalDevelopmentReportSha256"] == development["sourceReportSha256"]
        and combined["heldoutReportSha256"] == heldout["sourceReportSha256"]
        and combined["metrics"] == _sum_metrics(development["metrics"], heldout["metrics"]),
        "combined100 must sum the exact selected final development80 and heldout20, not baseline/best-of answers",
    )
    require(len({run["sourceReportSha256"] for run in runs}) == len(runs), "round and combined source reports must have distinct hashes")
    require(len({"buckets" in run for run in runs}) == 1, "optional buckets must cover every round and combined100")
    if "buckets" in baseline:
        buckets = [{row["label"]: row["metrics"] for row in run["buckets"]} for run in runs]
        require(all(set(group) == set(buckets[0]) for group in buckets), "bucket inventories must match across rounds")
        final_buckets = buckets[0] if final["developmentRound"] == "baseline" else buckets[-1]
        for key in buckets[0]:
            require(buckets[2][key] == _sum_metrics(final_buckets[key], buckets[1][key]), "combined bucket must use the same final candidate")
            if intervention is not None:
                require(
                    buckets[-1][key]["uniqueCases"] == buckets[0][key]["uniqueCases"]
                    and buckets[-1][key]["terminalCounts"]["protectedNotResubmitted"] == buckets[0][key]["nativeBlocks"],
                    "intervention cannot drop development slots or protected blocks from a bucket",
                )
    if "executionProtocol" in data:
        _execution_protocol(data)
    return copy.deepcopy(data)


def load(path: Path | None):
    if path is None:
        return {}
    blob = path.read_bytes()
    require(len(blob) <= MAX_BYTES, "public study is oversized")
    data = json.loads(blob, object_pairs_hook=_unique_fields, parse_constant=_invalid_constant)
    return {"evaluation100": validate(data), "evaluation100Sha256": hashlib.sha256(blob).hexdigest()}


def require_metadata(metadata):
    present = {"evaluation100", "evaluation100Sha256"} & set(metadata)
    if not present:
        return None
    require(len(present) == 2, "study and exact-file digest must travel together")
    sha256(metadata["evaluation100Sha256"])
    return validate(metadata["evaluation100"])


def notice(study):
    if study["evidenceKind"] == "synthetic-private-test":
        result = {
            "ja": "SYNTHETIC PRIVATE TEST — 架空の文書テストfixture。実評価ではなく、公開・受入・改善の根拠には使用できません。",
            "en": "SYNTHETIC PRIVATE TEST — invented document-test fixture, not a live evaluation; never publish it or use it as acceptance/improvement evidence.",
        }
    else:
        result = {
            "ja": f"{study['snapshotDate']} frozen100検証snapshot: 100件=最終候補のdevelopment80+heldout20。AI-assisted reviewで独立した人間の承認はありません。内部query・backend会話の証明はUNOBSERVABLEです。",
            "en": f"{study['snapshotDate']} frozen100 validation snapshot: 100 = final-candidate development80 + heldout20. AI-assisted review with no independent human sign-off. Internal-query and backend-conversation proof is UNOBSERVABLE.",
        }
    result["ja"] += " METHOD timingは補強資料によるcorroborationのみで独立証明ではありません。methodPreregistered=false / fullReviewPolicyPreregistered=false。証拠hashはcomputedAtAdmissionです。"
    result["en"] += " METHOD timing is corroborated, NOT independently proven: methodPreregistered=false / fullReviewPolicyPreregistered=false. Evidence hashes are computedAtAdmission."
    if "executionProtocol" in study:
        result["ja"] += " 停止後の実行protocol変更 (事前登録ではない): originalProtocolWasFullyFollowed=false。未送信17slotの初回だけを継続し、先のHTTP500はUNKNOWNのまま再送しません。"
        result["en"] += " POST-STOP EXECUTION AMENDMENT, not preregistered: originalProtocolWasFullyFollowed=false. Only17 never-submitted first attempts may continue; the prior HTTP500 stays UNKNOWN and is never retried."
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="Counts-only projection; never a private report, suite or ledger")
    args = parser.parse_args(argv)
    value = load(args.input)
    study = value["evaluation100"]
    print(json.dumps({
        "schemaVersion": SCHEMA, "evaluation100Sha256": value["evaluation100Sha256"],
        "evidenceKind": study["evidenceKind"], "bindingSha256": study["bindingSha256"],
        "denominators": study["denominators"], "reviewMode": study["review"]["mode"],
        "reviewPolicyTiming": study["review"]["reviewPolicyTiming"],
        "methodTimingEvidence": study["review"]["methodTimingEvidence"],
        "methodTimingIndependentlyCertified": study["review"]["methodTimingIndependentlyCertified"],
        "methodPreregistered": study["review"]["methodPreregistered"],
        "methodPreregistrationClaim": study["review"]["methodPreregistrationClaim"],
        "originalMethodTimingCorroborated": study["review"]["originalMethodTimingCorroborated"],
        "fullReviewPolicyPreregistered": study["review"]["fullReviewPolicyPreregistered"],
        "reviewToolingPreregistered": study["review"]["reviewToolingPreregistered"],
        "methodEvidenceHashProvenance": study["review"]["methodEvidenceHashProvenance"],
        "methodIntentSha256": study["review"]["methodIntentSha256"],
        "timingAdmissionReceiptSha256": study["review"]["timingAdmissionReceiptSha256"],
        "noIndependentHumanSignoff": True, "observability": study["observability"],
        **execution_binding(study),
        "checks": "schema, arithmetic and declared hash bindings only; not independent live verification",
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
