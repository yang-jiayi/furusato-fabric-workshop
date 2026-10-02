"""Reproduce sanitized public progress/evaluation reports from approved source evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "tools" / "docs"), str(ROOT / "tools" / "html")]
from furusato_docs import preview30_public_evidence as public
from furusato_docs import preview30_reporting as reporting
from furusato_docs.preview30_content import PREVIEW_NOTICE_EN, PREVIEW_NOTICE_JA

REPORT_NAMES = ("evaluation-summary.json", "evaluation-report.md", "progress-report.md")
FINAL_RUN_ID = public.LEGACY_ORIGINAL_SUITE_RUN_ID
CASE_ROWS = reporting.LEGACY_CASE_ROWS
REMEDIATIONS = (
    ("T04", "親集約grain・表現", "Parent aggregation grain/presentation",
     "親粒度でengine集約し、child rowsを親集計として扱わない。必要な関係/方向の説明を確認。",
     "Aggregate at the requested parent grain; do not substitute child rows. Check required relationship/direction presentation."),
    ("T05", "ID・source証拠", "Identifiers/source evidence",
     "必要なbusiness IDsとlabelsを選択projectionへ含め、実sourceの根拠を示す。",
     "Include needed business IDs with labels and actual-source attribution."),
    ("T06/T07", "operational期間", "Operational time window",
     "実sourceの年/月を照会し、static年を仮定しない。観測時刻と取込時刻を分ける。",
     "Discover source year/month rather than assuming the static year. Separate observation from ingestion timestamps."),
    ("T08", "指標とモデル経路", "Measures and modeled path",
     "件数・金額・scopeを別々に明示し、モデルのDonation経路と照合する。",
     "Label counts, amounts and scope separately and reconcile against the modeled Donation path."),
    ("T09", "cross-source回答", "Cross-source answer",
     "定義済みscopeの横断回答を、clarificationだけへ置換しない。",
     "Do not replace the defined-scope cross-source result with a clarification-only response."),
    ("T10", "native content gate", "Native content gate",
     "失敗を保持し、公式診断/supportへ渡す。bypassせず、contextual refusal成功としない。",
     "Retain the failure and use official diagnostics/support. Do not bypass it or count it as successful contextual refusal."),
)


def publication_link(value, kind):
    if value is None:
        return None
    parsed = urlsplit(value)
    parts = parsed.path.strip("/").split("/")
    suffix = ["tree"] if kind == "branch" else ["releases", "tag"]
    if parsed.scheme != "https" or parsed.netloc != "github.com" or parsed.query or parsed.fragment or len(parts) <= 2 + len(suffix) or parts[2:2 + len(suffix)] != suffix:
        raise ValueError("Supply an actual parent-verified GitHub branch/release URL, or leave it unset")
    return value


def markdown_table(headers, rows):
    def cell(value):
        if isinstance(value, tuple):
            return "<br>".join(cell(part) for part in value)
        return str(value).replace("|", r"\|").replace("\n", "<br>")
    return "\n".join([
        "| " + " | ".join(cell(value) for value in headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
        *["| " + " | ".join(cell(value) for value in row) + " |" for row in rows],
    ])


def selected_report_payloads(evidence, *, branch_url=None, release_url=None):
    selected = reporting.selection_metadata(evidence)
    final = selected["finalEvaluation"]
    runs = evidence["originalSuiteRuns"]
    context = selected["selectedRunContext"]
    publication = {
        "previewBranchUrl": publication_link(branch_url, "branch"),
        "previewReleaseUrl": publication_link(release_url, "release"),
        "stableVersion": "v2.7.0 / unified-20260923", "stableArtifactsReplaced": False,
    }
    summary = {
        "kind": "sanitized-preview-evaluation-and-progress",
        "presentation": selected["previewPresentation"],
        "scope": public.SCOPE, "reviewedAt": evidence["reviewedAt"],
        "evidenceProjectionSha256": evidence["projectionSha256"],
        "freezeStatus": evidence["freezeStatus"],
        "pairBuildAuthorized": evidence["freezeStatus"] == "frozen-for-build",
        "selectedOriginalSuiteRunId": final["id"], "finalEvaluation": final,
        "historicalRuns": [run for run in runs if run["id"] != final["id"]],
        "caseAggregates": final["caseAggregates"],
        "executionEvidence": selected["selectedSuiteExecutionEvidence"],
        "originalSuiteAccepted": final["accepted"], "qualityAccepted": final["accepted"],
        "mainPromoted": final["promoted"], "allFeaturesPassedClaimed": False,
        "finalUserAcceptanceCertified": False, "generalPopulationAccuracyClaimed": False,
        "directCausalMcpAbClaimed": False,
        **context,
        "labStates": {lab: value["status"] for lab, value in evidence["labs"].items()},
        "labEvidence": {
            lab: {key: value[key] for key in ("status", "reason", "evidenceIds")}
            for lab, value in evidence["labs"].items()
        },
        "nativeCapturePlacements": len(evidence["captures"]),
        "uniqueSanitizedImages": len({value["sha256"] for value in evidence["captures"].values()}),
        "publication": publication,
        "privacy": {
            "rawAnswersIncluded": False, "answerKeysIncluded": False, "privateCriterionTextIncluded": False,
            "liveIdsEndpointsMachinePathsIncluded": False, "internalReasoningIncluded": False,
        },
    }
    public.public_strings({key: value for key, value in summary.items() if key != "publication"}, "public report")
    notice_ja, notice_en = reporting.selection_notice(final)
    run_table = markdown_table(
        [("run / 選択", "Run / selection"), ("送信/前提blocked", "Submitted/preblocked questions"),
         "PASS / FAIL / U / B / N/A", ("受入/promotion（審査記録）", "Accepted/promoted, reviewed record")],
        [
            [(run["label"]["ja"], run["label"]["en"]),
             f"{run['submittedQuestions']} / {run['preblockedQuestions']}",
             " / ".join(str(run["counts"][key]) for key in reporting.VERDICT_KEYS),
             f"{run['accepted']} / {run['promoted']}"]
            for run in runs
        ],
    )
    method_table = markdown_table([("記録", "Record"), ("値", "Value")], reporting.method_rows(final))
    source_table = markdown_table(
        [("言語", "Language"), ("試行", "Attempts"), ("成功", "Successes"), ("拒否", "Rejections")],
        reporting.source_rows(final),
    )
    case_table = markdown_table(
        ["Case", "PASS", "FAIL", ("未検証", "Unverified"), "BLOCKED", "N/A", ("native gate", "Native gate")],
        reporting.case_verdict_rows(final),
    )
    execution_table = markdown_table(
        ["Case", ("試行", "Attempts"), ("成功", "Successes"), ("拒否", "Rejections"),
         ("native応答終端", "Native response terminal state"), ("成功query言語", "Successful query languages")],
        reporting.case_execution_rows(final),
    )
    context_text = "\n\n".join(
        f"**{key} — {value['status']}**\n\n{value['reason']['ja']}\n\n{value['reason']['en']}"
        for key, value in context.items()
    )
    applicability = ""
    if "notApplicableReason" in final:
        applicability = f"\nN/A: {final['notApplicableReason']['ja']}\n\n{final['notApplicableReason']['en']}\n"
    completeness_ja, completeness_en = reporting.execution_completeness_notice()
    evaluation_md = f"""# 明示選択したPreview評価 / Explicitly selected Preview evaluation

{selected['previewPresentation']['ja']}

{selected['previewPresentation']['en']}

**{notice_ja}**

**{notice_en}**

## 選択と方法 / Selection and method

観測時刻 / Observed: **{final['observedAt']}**。source projectionの審査済みIDだけを選択します。
最高点・最新時刻で選ばず、選択はpromotion・再実行・公開ではありません。

Only the explicitly reviewed source-projection ID is selected, never the highest score or latest
timestamp. Selection does not promote, rerun or publish anything.

{method_table}

{source_table}

試行・成功・拒否、独立trace付きQUESTION slot、別backend会話、native応答完了は別の分母です。
未提供は未検証で、ゼロや旧runの値を補いません。DAXはSQL/GQL/KQLへ合算しません。

Attempts, successes, rejections, independently traced QUESTION slots, distinct backend
conversations and completed native responses are separate denominators. Missing facts are
unverified, not zero or values borrowed from the old run. DAX is not folded into SQL/GQL/KQL.
These counts do not establish general-population accuracy or a direct causal MCP A/B.

{completeness_ja}

{completeness_en}

## 元10問/84条件の履歴 / Original ten/84 ledgers

{run_table}

sourceの履歴順・集計は不変で、選択runだけを下に詳述します。UI/SDK/smoke証拠を合算しません。
Source history order and aggregates are unchanged. Only the selected run is detailed below;
separate UI/SDK/smoke evidence does not rewrite those ledgers.

## case判定と実行 / Case decisions and executions

{case_table}

{execution_table}
{applicability}
native固定blockはFAILのまま保持し、適切なcontextual refusalや成功queryへ置換しません。
完了応答だけでは内容の合格・source実行・fresh backendを証明しません。

A native fixed block remains FAIL, not a successful contextual refusal or query. Native
completion alone proves neither content acceptance, source execution nor a fresh backend.

## contextの再確認境界 / Context recheck boundaries

{context_text}

## 残る確認と受入の境界 / Remaining checks and acceptance boundary

失敗・未検証・blocked・N/Aを削除せず、元の固定rubricで審査します。集計だけから欠陥原因や
T04/SDK修復を推測しません。元suiteの受入flagは審査記録の値で、84 PASSから自動設定しません。
全機能と最終user受入には、残る演習の実証と別の明示承認が必要です。

Retain every FAIL, unverified, blocked and N/A cell under the unchanged rubric. Aggregate
counts do not diagnose a defect or prove T04/SDK repair. Original-suite acceptance is the
reviewed flag, never inferred from84 PASS. All-feature and final user acceptance require
actual remaining-feature evidence and separate explicit approval.

See [source-scoped progress](progress-report.md) and [approved summary](evaluation-summary.json).
"""
    lab_table = markdown_table(
        ["Lab", ("状態", "State"), ("sourceのscope", "Source scope")],
        [[lab, value["status"], (value["reason"]["ja"], value["reason"]["en"])]
         for lab, value in evidence["labs"].items()],
    )
    publication_rows = [
        f"- {label}: [{url}]({url})" if url else
        f"- {label}: 未確認のためlinkなし / no verified URL supplied; no link is fabricated."
        for label, url in (("Preview branch", publication["previewBranchUrl"]),
                           ("Preview release", publication["previewReleaseUrl"]))
    ]
    progress_md = f"""# 明示選択したPreview進捗 / Explicitly selected Preview progress

{selected['previewPresentation']['ja']}

{selected['previewPresentation']['en']}

{notice_ja}

{notice_en}

{completeness_ja}

{completeness_en}

Content scope: **24 chapters / 5 appendices**; original ten questions /84 conditions,
synthetic data and stable v2.7 remain unchanged. Source-reviewed native placements:
**{summary['nativeCapturePlacements']}**, unique sanitized images: **{summary['uniqueSanitizedImages']}**.

## source-owned lab状態 / Source-owned lab status

{lab_table}

各状態はsource projectionに記録されたscopeだけです。選択runによる新しいUI/SDK/postcheckや
残る演習の再確認を推定しません。部分観測・失敗・blockedを保持します。

Each state retains its own source-projection scope, not a new UI/SDK/postcheck or
remaining-feature recheck inferred from selection. Partial observations, failures and blocked lanes remain.

## context / Context

{context_text}

## 再現・公開の境界 / Reproduction and publication boundary

- Explicit selected original-suite run: **{final['id']}**.
- Evidence projection SHA-256: `{evidence['projectionSha256']}`.
- Freeze state: **{evidence['freezeStatus']}**; this is not publication or final user acceptance.
- No Word/HTML/ZIP build, cloud call, question, data/model/instruction change, promotion or publication is performed by report generation.
- [Input contract](../evidence-contract.md) / [selected evaluation](evaluation-report.md).

{chr(10).join(publication_rows)}
- Stable **v2.7.0 / unified-20260923** is retained, not replaced.
"""
    return {
        "evaluation-summary.json": (json.dumps(summary, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8"),
        "evaluation-report.md": evaluation_md.encode("utf-8"),
        "progress-report.md": progress_md.encode("utf-8"),
    }


def report_payloads(projection: Path, *, root=ROOT, branch_url=None, release_url=None):
    evidence = public.load(projection, root=root)
    if "selectedOriginalSuiteRunId" in evidence:
        selected = public.selected_original_suite_run(evidence, required=True)
        if selected["id"] != FINAL_RUN_ID:
            return selected_report_payloads(evidence, branch_url=branch_url, release_url=release_url)
    runs = evidence["originalSuiteRuns"]
    matches = [run for run in runs if run["id"] == FINAL_RUN_ID]
    if len(matches) != 1:
        raise ValueError("The approved final NativeUI aggregate is required")
    final = matches[0]
    reporting.require_legacy_run(final)
    publication = {
        "previewBranchUrl": publication_link(branch_url, "branch"),
        "previewReleaseUrl": publication_link(release_url, "release"),
        "stableVersion": "v2.7.0 / unified-20260923", "stableArtifactsReplaced": False,
    }
    cases = [
        {"case": ident, "pass": passed, "fail": failed, "sourceExecutions": count, "nativeGate": gate}
        for ident, passed, failed, count, gate in CASE_ROWS
    ]
    assert sum(row["pass"] for row in cases) == 48 and sum(row["fail"] for row in cases) == 36
    assert sum(row["sourceExecutions"] for row in cases) == 9
    assert sum(row["sourceExecutions"] > 0 for row in cases) == 7
    summary = {
        "kind": "sanitized-preview-evaluation-and-progress",
        "presentation": {"ja": PREVIEW_NOTICE_JA, "en": PREVIEW_NOTICE_EN},
        "scope": public.SCOPE, "reviewedAt": evidence["reviewedAt"],
        "evidenceProjectionSha256": evidence["projectionSha256"],
        "freezeStatus": evidence["freezeStatus"], "pairBuildAuthorized": evidence["freezeStatus"] == "frozen-for-build",
        "finalEvaluation": final, "historicalRuns": [run for run in runs if run["id"] != FINAL_RUN_ID],
        "caseAggregates": cases,
        "qualityAccepted": False, "mainPromoted": False, "generalPopulationAccuracyClaimed": False,
        "directCausalMcpAbClaimed": False,
        "scopedCompatibility": {
            "generation1BridgeConsumerGqlObserved": True,
            "generation2ConnectorFixed": False,
            "t04AggregationAndPresentationStillFailed": True,
            "implicitFallbackOrDefaultDowngrade": False,
            "newGeneration2MetricsAndTsPreserved": True,
        },
        "postcheck": {
            "unchangedPublications": 4, "mainStaticFirstContextFullDefinitionsUnchanged": True,
            "compatDraftCatalogMetadataExpanded": True,
            "effectiveSelectionCounts": {"kql": 11, "lakehouse": 99},
            "effectiveSelectedTablesAndColumnsUnchanged": True,
            "unselectedRawEventIdExposed": False, "republished": False,
            "sourceGlobalAndCiSettingsStable": True,
        },
        "externalSdk": {
            "status": "blocked-in-observed-environment", "questionsSubmitted": 0,
            "blocker": "Missing Fabric runtime service-discovery module",
            "universalSdkFailureClaimed": False,
        },
        "labStates": {lab: value["status"] for lab, value in evidence["labs"].items()},
        "nativeCapturePlacements": len(evidence["captures"]),
        "uniqueSanitizedImages": len({value["sha256"] for value in evidence["captures"].values()}),
        "publication": publication,
        "privacy": {
            "rawAnswersIncluded": False, "answerKeysIncluded": False, "privateCriterionTextIncluded": False,
            "liveIdsEndpointsMachinePathsIncluded": False, "internalReasoningIncluded": False,
        },
    }
    if "selectedOriginalSuiteRunId" in evidence:
        summary["selectedOriginalSuiteRunId"] = final["id"]
        summary["originalSuiteAccepted"] = final["accepted"]
    public.public_strings({key: value for key, value in summary.items() if key != "publication"}, "public report")
    run_rows = "\n".join(
        f"| {run['label']['en']} | {run['submittedQuestions']} | "
        + " | ".join(str(run["counts"][key]) for key in ("pass", "fail", "executionUnverified", "blocked", "notApplicable"))
        + f" | {run.get('method', {}).get('surface', 'recorded historical method')} |"
        for run in runs
    )
    case_rows = "\n".join(f"| {row['case']} | {row['pass']} | {row['fail']} | {row['sourceExecutions']} | {'native gate' if row['nativeGate'] else '—'} |" for row in cases)
    remediation_rows = "\n".join(f"| {ident} | {ja} / {en} | {recommend_ja}<br>{recommend_en} |" for ident, ja, en, recommend_ja, recommend_en in REMEDIATIONS)
    evaluation_md = f"""# 実装・検証結果を収録したPreview — 評価結果 / Evaluation

**AI回答品質は未合格。main未promotion。GA・全機能合格・一般母集団の正確性の主張ではありません。**
**AI answer quality is not accepted. Main is not promoted. Not GA, all-feature acceptance, or a general-population accuracy claim.**

## Frozen method / 固定した方法

元10問を各1回、84条件は不変。coordinatorがmanual fixed-rubric offline judgmentを完了しました。
再質問・追加AI criticはありません。NativeUI / responses / sandbox / preview、
diagnostics記録modelは **gpt-5.6-terra**。UI bannerから推測していません。

Ten original questions once each; the84 conditions are unchanged. The coordinator completed
manual fixed-rubric offline judgment, with no resubmissions or new AI-critic calls.
The observed method is **NativeUI / responses / sandbox / preview / gpt-5.6-terra**,
as recorded in official diagnostics—not inferred from the UI banner.

Distinct backend conversations: **10**. Actual source executions: **9 (SQL5, GQL2, KQL2)**,
covering **7 question slots** with execution evidence. These are different denominators.

## Results / 判定

Final: **48 PASS / 36 FAIL / 0 execution-unverified / 0 N/A / 0 preblocked = 84**.
FAIL36 = **29 content/required-evidence failures + 7 T10 native-gate acceptance failures**.
Zero unverified cells does not turn missing required evidence into a pass; those failures
remain in FAIL. A native content block is not a correct contextual refusal or seven false claims.

| Run | Submitted | PASS | FAIL | Unverified | Preblocked | N/A | Surface |
|---|---:|---:|---:|---:|---:|---:|---|
{run_rows}

Historical published-MCP scores are retained unchanged. The final native-UI candidate,
consumer generation, transport and observed runtime differ: **not a direct causal MCP A/B**.
Operator Graph/TS/CI smoke or separate UI/SDK diagnostics do not rewrite these ledgers.

| Case | PASS | FAIL | Source executions | Native gate |
|---|---:|---:|---:|---|
{case_rows}

## Compatibility and limits / 互換性と制限

The explicit generation1 bridge enabled actual T04 GQL and returned the reconciled child-row
set on this separate consumer path. The earlier gen2 API-version error was absent here.
**This does not fix the generation2 connector.** T04 still failed parent aggregation/grain
and required presentation. Connection/Graph success is not answer-quality acceptance.
No implicit generation1 fallback or default downgrade is allowed; the generation2 new UI,
native Metrics and operational TS remain intact.

## Residual remediation / 残る課題と改善提案

These are recommendations, not changes executed in this freeze. No further candidate
iterations are planned; any future work needs separate authorization and the same rubric.
No private answer values or verbatim private criteria are included.

| Scope | Residual category | Recommendation |
|---|---|---|
{remediation_rows}

## Snapshot integrity / snapshotの区別

All **four publications** stayed unchanged. Main/StaticFirst/Context full definitions
stayed unchanged. Only Compat **draft catalog metadata** expanded through UI.
Effective parent-gated selected tables/columns remained **KQL11 / Lakehouse99**,
with no exposure of unselected raw EventID, and **no republish**.
GLOBAL/source instructions and CI settings remained stable. Candidate snapshot,
published snapshot and generated documentation artifact are not interchangeable.

External Responses SDK qualification submitted **zero questions**: a missing Fabric
runtime service-discovery module blocked that external environment. Metadata
authentication/import success is not Responses runtime qualification, and this is
not a universal SDK-failure claim.

See [progress and publication status](progress-report.md) and
[machine-readable approved summary](evaluation-summary.json).
"""
    publication_rows = []
    for label, url in (("Preview branch", publication["previewBranchUrl"]), ("Preview release", publication["previewReleaseUrl"])):
        publication_rows.append(f"- {label}: [{url}]({url})" if url else f"- {label}: forthcoming; no verified URL supplied, so no link is fabricated.")
    lab_rows = "\n".join(f"| {lab} | {value['status']} | {value['reason']['ja']}<br>{value['reason']['en']} |" for lab, value in evidence["labs"].items())
    build_gate = (
        "Evaluation records and runtime/Notebook inputs are frozen for reproducible document generation. Editorial corrections do not change scores or establish quality acceptance."
        if evidence["freezeStatus"] == "frozen-for-build"
        else "Runtime, optional-bridge and Notebook inputs must be frozen and reviewed before the final pair build."
    )
    progress_md = f"""# 実装・検証結果を収録したPreview — Progress

{PREVIEW_NOTICE_JA}

{PREVIEW_NOTICE_EN}

Content scope: **24 chapters / 5 appendices**, preserving the original ten questions,
84 conditions, synthetic data and v2.7 comparison material. The frozen evidence
projection has **{len(evidence['captures'])} native placements** and
**{summary['uniqueSanitizedImages']} unique sanitized images**, plus six preserved reference diagrams.

## Verified scope, not blanket acceptance

- Primary generation2 operational TS:73 static + one TS; native bounded KQL reconciliation verified.
- Static Relationships companion:10/72/15 over the same Lakehouse/source, with native Graph checks.
  No extra source dataset copy; Graph materialization **stores a derived projection**.
- Two automatic increment files plus one separately approved manual native-UI recovery;
  not three automatic deliveries. Actual queries, not stale extent statistics, establish rows.
- Native Metrics links, structural RDF cycle with explicit losses, bound version restore,
  Gold-aware four-file context, CI smoke and native rule readback have their own scoped evidence.
- The additive keyless/unbound entity is a separate typed intent. The original metadata-only
  shared-reference regression stays failed/rolled back, not silently fixed.
- Explicit opt-in generation1 **consumer** bridge now has scoped GQL benefit, but original84
  quality is not accepted and the gen2 connector is not claimed fixed.
- Namespace/direct-dashboard UI availability and authorized second-identity negative checks
  remain conditional/unproven. Do not manufacture controls, permissions or pass evidence.

## Per-lab status / 演習状態

| Lab | State | Scope / boundary |
|---|---|---|
{lab_rows}

`passed` is scoped to the reviewed lab; historical observations, partial captures,
failed known issues and blocked lanes retain their own meanings.
The382px Gold panes were not enlarged to satisfy a600px completion gate.

## Reproduction and freeze / 再現とfreeze

- Public evidence: [source-owned manifest](../../assets/v3-preview-evidence/manifest.json).
- Evidence projection SHA-256: `{evidence['projectionSha256']}`.
- Freeze state: **{evidence['freezeStatus']}**.
- {build_gate}
- This report generation did not build Word/HTML/ZIP, call cloud services, change instructions,
  promote an Agent, or publish a branch/release.
- [Input contract and final build procedure](../evidence-contract.md).
- [Evaluation results and residual remediation](evaluation-report.md).

## Publication / 公開先

{chr(10).join(publication_rows)}
- Stable **v2.7.0 / unified-20260923** is retained, not replaced:
  [Word](../../Fabric_IQ_Ontology_Workshop_Furusato_Participant_v2.7.0_unified-20260923.docx) /
  [JA/EN HTML](../../furusato-workshop-v2-7-0-complete_unified-20260923.html).
"""
    return {
        "evaluation-summary.json": (json.dumps(summary, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8"),
        "evaluation-report.md": evaluation_md.encode("utf-8"),
        "progress-report.md": progress_md.encode("utf-8"),
    }


def generate(projection, output, *, check=False, root=ROOT, branch_url=None, release_url=None):
    output = output.resolve()
    report_roots = ((root / "docs" / "v3-preview").resolve(), (root / "docs" / "v3.0.0").resolve())
    if not any(output.is_relative_to(base) for base in report_roots):
        raise ValueError("Public reports must remain under source docs/v3-preview or docs/v3.0.0")
    payloads = report_payloads(projection, root=root, branch_url=branch_url, release_url=release_url)
    hashes = {name: hashlib.sha256(blob).hexdigest() for name, blob in sorted(payloads.items())}
    payloads["SHA256SUMS.txt"] = "".join(f"{digest}  {name}\n" for name, digest in hashes.items()).encode("utf-8")
    summary = json.loads(payloads["evaluation-summary.json"])
    if check:
        if any(not (output / name).is_file() or (output / name).read_bytes() != blob for name, blob in payloads.items()):
            raise ValueError("Public reports do not match the frozen source projection")
    else:
        if "selectedOriginalSuiteRunId" in summary and any((output / name).exists() for name in payloads):
            if any(not (output / name).is_file() or (output / name).read_bytes() != blob for name, blob in payloads.items()):
                raise ValueError("Selected-run reports need a fresh reviewed directory; existing historical reports are not overwritten")
        output.mkdir(parents=True, exist_ok=True)
        for name, blob in payloads.items():
            (output / name).write_bytes(blob)
    result = {
        "files": hashes, "sourceOnly": True, "wordHtmlZipBuilds": 0,
        "qualityAccepted": summary["qualityAccepted"], "mainPromoted": summary["mainPromoted"],
    }
    if "selectedOriginalSuiteRunId" in summary:
        result["selectedOriginalSuiteRunId"] = summary["selectedOriginalSuiteRunId"]
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--public-evidence", type=Path, default=ROOT / public.DEFAULT_RELATIVE)
    parser.add_argument("--out", type=Path, default=ROOT / "docs" / "v3-preview" / "reports")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--preview-branch-url")
    parser.add_argument("--preview-release-url")
    args = parser.parse_args()
    print(json.dumps(generate(args.public_evidence, args.out, check=args.check, branch_url=args.preview_branch_url, release_url=args.preview_release_url), indent=2))
