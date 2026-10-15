"""Public, reproducible participant evaluation materials.

Only public source questions and scoring keys are read. This module performs
neither cloud calls nor answer grading. The original rubric stays verbatim.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib
import io
import json
import sys
from pathlib import Path

ASSET_RELATIVE = Path("workshop/v3.0.0-preview/data-agent/participant-evaluation")
SCHEMA = "furusato-participant-public-evaluation/v1"
ORIGINAL_COUNTS = (7, 6, 6, 11, 14, 10, 8, 7, 8, 7)
NA_IDS = ("T03.evidence.1", "T03.evidence.2", "T03.pass_criteria.2")


def execution_review(case):
    """A separate participant diagnostic policy, never a historical rubric edit."""
    ident = case["id"]
    if ident in {"B05", "B06", "B07", "B19"}:
        return ("Semantic model の実DAXと結果。空の言語一覧を実行不要と読みません。",
                "Actual Semantic model DAX and results. An empty legacy language list does not waive execution.")
    if ident == "B09":
        return ("Lakehouse SQL または Ontology GQL のいずれかの実行と、全事業者の結果。",
                "Actual Lakehouse SQL or Ontology GQL execution with the complete supplier result.")
    if ident in {"B02", "B17"}:
        return ("実モデルのメジャー定義を確認して説明を採点。照会を実行していなければNOT_REQUIREDで、実行成功に数えません。",
                "Check the actual model measure definition and grade the explanation. If no query ran, use NOT_REQUIRED and do not count execution success.")
    if ident == "B11":
        return ("現在のOntologyの実定義で関係名と向きを確認。定義の参照をGQL実行成功と数えません。",
                "Verify relationship names and direction against the current actual ontology definition; reading a definition is not successful GQL execution.")
    if ident == "T03":
        return ("数値回答なら実SQLと結果。妥当な確認質問だけの分岐はNOT_REQUIRED。",
                "Actual SQL and results for a numerical answer; NOT_REQUIRED only for a valid clarification-only branch.")
    if ident in {"T08", "T10"}:
        return ("正しい業務上の拒否なら実行不要。任意で数値を述べるならその実ソースの根拠も確認。サービスブロックを業務上の拒否に置き換えません。",
                "A correct business refusal needs no query. Verify actual source evidence for optional numerical claims. A service block is not a business refusal.")
    languages = ", ".join(case["required_query_languages"])
    return (f"{languages} の全経路で実ソース・実クエリ・成功結果と回答の対応を確認。",
            f"Verify actual sources, queries, successful results and answer correspondence for every route: {languages}.")


def _json(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def _csv(headers, rows):
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(headers)
    writer.writerows(rows)
    return stream.getvalue().encode("utf-8-sig")


def _sha(value):
    return hashlib.sha256(value).hexdigest()


def public_suite(root: Path):
    """Extract the same frozen public questions used by the native evaluator."""
    directory = root / "tools/data-agent"
    sys.path.insert(0, str(directory))
    try:
        native = importlib.import_module("native_evaluation")
        regression = importlib.import_module("regression_suite")
        for module in (native, regression):
            if not Path(module.__file__).resolve().is_relative_to(directory.resolve()):
                raise ValueError("Evaluation module was loaded from another checkout")
        original = native.original_suite(root)
        extended = regression.build_suite(root)
    finally:
        sys.path.pop(0)
    committed = json.loads((directory / "regression/extended-suite.json").read_bytes())
    if extended != committed:
        raise ValueError("The public regression source does not reproduce its committed suite")
    suite = {
        "schemaVersion": SCHEMA,
        "questionLanguage": "ja (verbatim; do not translate a comparison run)",
        "publicNotUnseen": True,
        "original": original,
        "regression": extended,
        "protocol": {
            "practice": {"originalRepeats": 1, "regressionRepeats": 0,
                         "slotsPerPhase": 10, "conditionsPerPhase": 84},
            "extended": {"originalRepeats": 3, "regressionRepeats": 1,
                         "slotsPerPhase": 49, "conditionsPerPhase": 290},
            "phases": ["baseline", "final"],
            "newConversationPerSlot": True,
            "submissionsPerSlot": 1,
            "timeoutSeconds": 600,
            "unknownOutcome": "UNCLEAR; retain registered slot; do not resubmit",
            "conditionalNaIds": list(NA_IDS),
            "historicalPrivateQuestionsIncluded": False,
        },
        "executionReviewPolicy": {
            "separateFromFrozenContentCriteria": True,
            "notTheHistoricalStrictGrader": True,
            "cases": {case["id"]: {"ja": execution_review(case)[0], "en": execution_review(case)[1]}
                      for case in original["cases"] + extended["cases"]},
        },
    }
    _validate(suite)
    return suite


def _validate(suite):
    if suite.get("schemaVersion") != SCHEMA or suite.get("publicNotUnseen") is not True:
        raise ValueError("Unexpected participant evaluation schema")
    original, extended = suite["original"]["cases"], suite["regression"]["cases"]
    if [case["id"] for case in original] != [f"T{i:02}" for i in range(1, 11)]:
        raise ValueError("Original question IDs changed")
    if tuple(len(case["conditions"]) for case in original) != ORIGINAL_COUNTS:
        raise ValueError("Original ten/84 conditions changed")
    if [case["id"] for case in extended] != [f"B{i:02}" for i in range(1, 20)]:
        raise ValueError("Extended question IDs changed")
    if any(len(case["conditions"]) != 2 for case in extended):
        raise ValueError("Extended nineteen/38 conditions changed")
    ids = [condition["id"] for case in original + extended for condition in case["conditions"]]
    if len(ids) != len(set(ids)) or len(ids) != 122:
        raise ValueError("Public condition identifiers must be unique")


def load_suite(root: Path):
    path = root / ASSET_RELATIVE / "canonical-public-suite.json"
    suite = json.loads(path.read_bytes())
    _validate(suite)
    return suite


def _slots(suite):
    # The first ten slots are also the short practice course.
    for repeat in range(1, 4):
        for case in suite["original"]["cases"]:
            yield "original", repeat, case
    for case in suite["regression"]["cases"]:
        yield "regression", 1, case


def _registration(suite):
    return {
        "schemaVersion": "furusato-participant-evaluation-registration/v1",
        "campaignLabel": "FILL-BEFORE-FIRST-QUESTION",
        "protocol": "extended-public-49",
        "registeredAtUtc": "",
        "frozenQuestionAndRubricSha256": _sha(_json(suite)),
        "questionLanguage": "ja",
        "interface": "Fabric published Data Agent chat",
        "timeoutSeconds": 600,
        "oneSubmissionPerSlot": True,
        "newConversationPerSlot": True,
        "slotsPerPhase": 49,
        "conditionsPerPhase": 290,
        "phaseLabels": ["baseline", "final"],
        "privateDeploymentRecordFile": "",
        "dataManifestSha256": "",
        "liveDataChecksFile": "",
        "baselinePublishedDefinitionSha256": "",
        "finalPublishedDefinitionSha256": "",
        "baselineProfileLabel": "",
        "finalProfileLabel": "",
        "instructionChangeHypothesis": "",
        "permittedChangedFields": [],
        "sourceSelectionRecordFile": "",
        "selectedTablesAndColumnsRecordFile": "",
        "schemaAndMeasureRecordFile": "",
        "modelAndCapacityObservationFile": "",
        "reviewer": "",
        "adoptionRule": {
            "minimumNewFailToPass": 1,
            "maximumNewPassToFail": 0,
            "strictSourceExecutionMustNotDeteriorate": True,
            "unsupportedOrInventedFactsMustNotIncrease": True,
            "unresolvedPlatformLimitationsRemainDisclosed": True,
            "unknownToPassIsNewEvidenceNotKnownErrorCorrection": True,
        },
        "notEquivalentToHistorical51QuestionCampaign": True,
        "separateUnseenEvaluation": {
            "enabled": False,
            "privateFrozenSpecificationFile": "",
            "registeredSlots": 0,
            "registeredConditions": 0,
            "reportSeparately": True,
        },
    }


README = """# 参加者の評価キット / Participant evaluation kit

Word / HTML の第19章と付録Cで、準備、操作、採点、前後比較を説明します。
このフォルダーは公開の質問・採点基準と空の記録用紙です。採点基準や期待値を
Data Agent の指示、例、ソース説明へコピーしません。実際の回答、実環境のID、
クエリ、画面、認証は Git 外の作業用フォルダーへ保存します。

Chapter 19 and Appendix C of Word / HTML contain the complete manual procedure.
This folder supplies public questions, scoring criteria and blank records. Never
put questions, answer keys or grading criteria in Agent instructions, examples or
source descriptions. Save actual answers, live identifiers, queries, screenshots
and authentication outside Git.

| File | 内容 / Contents |
|---|---|
| canonical-public-suite.json | 原典と同一の29問・122条件、期待値、由来 / 29 verbatim questions, 122 unique criteria, keys and provenance |
| questions.csv | 送信する日本語の質問文だけをコピー / Copy only the Japanese question text into chat |
| rubric.csv | 条件ID・原文・必要な実行言語 / Condition IDs, verbatim criteria and required query languages |
| registration-template.json | 開始前に固定する構成、仮説、分母、採用条件 / Freeze configuration, hypothesis, denominators and adoption rule before starting |
| slots-template.csv | baseline と final の各49枠、計98行 / 49 slots per phase, 98 rows total |
| conditions-template.csv | 各290条件、計580行 / 290 conditions per phase, 580 rows total |
| paired-template.csv | 前後の同じ290条件を対応付ける用紙 / Pair the same 290 conditions across phases |
| SHA256SUMS.txt | 配布ファイルのSHA-256 / Distribution file checksums |

## 手順 / Steps

1. フォルダーを Git 外へコピーします。各 template を複製し、ファイル名の
   `-template` を外します。用紙には実測値を記入し、元の空用紙は保持します。
2. 完全評価は T01–T10 を3周（毎回別の会話）、続いて B01–B19 を1周です。
   49質問枠・290条件を baseline と final のそれぞれで実施します。
   演習だけなら original / repeat=1 の10枠・84条件を使い、registration の
   protocol を practice-10、slotsPerPhase を10、conditionsPerPhase を84にし、
   空用紙から他の予定行を開始前に除きます。途中で短縮しません。
3. 現在の公開済み設定を baseline として保存し、データ、ソース、選択列、例、
   スキーマ、メジャー、公開版、実行方法、タイムアウトを記録します。
   今回の採用済み構成を初めて適用した後の確認は「再現確認」です。
   過去のbaselineに戻す必要はなく、同じ構成を2回測って「改善」と呼びません。
4. 1枠ごとに Clear chat / 新しい会話で、questions.csv の質問セルだけを1回送信。
   600秒まで待ち、タイムアウト・送信不明・フィルタ停止もその枠で記録します。
   回答全文、実行詳細の実クエリ・結果、時刻を保存します。よい回答が出るまで
   再送したり、期待値をヒントにしたりしません。
5. rubric.csv の1条件ずつを PASS / FAIL / UNCLEAR / NA として記録します。
   判定理由、回答や実行結果の保存先・位置を記入します。NA は T03 の確認質問分岐
   により適用外となる3条件だけです。T10 のサービスブロックは7条件ともFAIL。
   内容と実行の根拠は別々に判定します。HTTP200、完成した文章、提示したクエリだけで
   実行成功とはしません。クエリや結果が見えなければ実行根拠をUNCLEARにします。
6. 失敗をソース・期間・粒度・意味・実行に分類し、1つの原因に対する指示変更を
   決めます。変更前後の全文を保存し、Draftの対象指示欄だけを変更してSave、Publish、
   公開版を開き直して確認します。配布Globalは10,000 UTF-16単位の上限のため、
   追記でなく対象の文を置き換え、長さを確認します。固定profile用helperは独自候補を
   配布設定へ戻すか一致確認に失敗するため、候補の適用・認定に使いません。同じ全49枠を
   final として実施します。データや選択を変えた比較は別の実験として扱います。
7. suite / repeat / case_id / condition_id をキーに前後を結合します。質問、条件、
   データが同一であることを確認し、T03で片側が有効なNAとなった条件だけを両側
   同じキーで除外し理由を残します。分母は290から実際の除外数を引いて求め、281に
   固定しません。PASS / 適用可能な共通分母を算出します。FAILとUNCLEARは分母に残します。
   改善・退行・不明から新たな根拠が得られた条件をすべて報告します。
8. 登録した採用条件を満たす場合だけ新しい変更を採用します。推奨の初期条件は、
   FAIL→PASSが1件以上、PASS→FAILが0件、実行根拠と事実の正しさが悪化しないことです。
   満たさなければ候補を採用せず、今回のbaselineの全文を同じDraft欄へ戻して
   Save、Publish、公開版の確認をします。固定helperで戻すのは、baselineが配布profileと
   同一と確認済みの場合だけです。
   採用条件を結果を見てから緩めません。次の案は別の版として登録します。

1. Copy this folder outside Git, duplicate each template and remove `-template`
   from the working copy's name. Keep the supplied blanks unchanged.
2. The full public protocol sends T01–T10 three times in fresh conversations,
   followed by B01–B19 once: 49 slots and 290 conditions per phase. For practice,
   preregister practice-10, 10 slots and 84 conditions, and retain only original /
   repeat=1 rows before beginning. Do not shorten a campaign after seeing results.
3. Save the current publication as baseline. Freeze data, source IDs, selections,
   examples, schema, measures, interface and timeout. Verifying the already adopted
   configuration is reproduction testing; two runs of unchanged instructions do
   not establish an improvement. Restoring a historical baseline is unnecessary.
4. Start a fresh chat for every slot and send only its question once. Wait up to
   600 seconds; retain timeouts, uncertain submissions and content blocks. Preserve
   the complete answer, actual executed query/results and timestamps. Never resend
   to select a better response or provide answer-key hints.
5. Judge each condition PASS / FAIL / UNCLEAR / NA with a reason and evidence
   location. NA is limited to the three T03 numerical conditions made inapplicable
   by a valid clarification branch. A service block on T10 is seven FAILs. Score
   content and actual execution separately; HTTP200, prose or displayed query
   text alone is not execution proof. Missing execution details are UNCLEAR.
6. Classify source, time, grain, meaning or execution failures. Propose one scoped
   instruction change and save both complete texts. Edit only the intended Draft
   field, Save, Publish, reopen and inspect the publication. The distributed global
   instructions already use 10,000 UTF-16 units; replace wording rather than append
   notes, and check length. Do not use the fixed-profile helper to apply or certify
   a custom candidate: it restores the distributed profile or reports mismatch. Run all 49
   final slots. A changed dataset or selection constitutes a different experiment.
7. Pair suite / repeat / case_id / condition_id. Confirm equal questions, criteria
   and data. Exclude the same keys on both sides only for valid T03 NA branches,
   preserving reasons. Compute the denominator from 290 minus actual exclusions;
   never force 281. Report PASS divided by that denominator, retaining FAIL and
   UNCLEAR, every gain, regression and unknown-to-pass transition.
8. Adopt a new candidate only if the preregistered rule holds. Suggested defaults:
   at least one FAIL→PASS, no PASS→FAIL and no deterioration in query execution records
   or factual correctness. Otherwise restore this baseline's full text in the same
   Draft fields, Save, Publish and inspect the publication. Use the fixed helper for
   restoration only if that baseline is confirmed identical to its distributed
   profile. Do not relax the rule after observing outcomes.

## 判定を混同しない / Keep judgments separate

- `status`: 補助的な回答条件の判定。値が合うことだけでは、
  実行したという証明にはなりません。 / Supplemental answer-condition verdicts;
  a correct number does not prove a query ran.
- `native_status`: 付録Cの独立した実行確認方針について、正しい実ソース、
  実行成功、十分な結果、回答との対応がそろえば PASS。必要な実行が失敗したら
  FAIL、根拠が取れなければ UNCLEAR。実行不要と事前定義された説明・確認質問は
  NOT_REQUIRED とし、実行成功件数に足しません。 / PASS requires all required routes,
  correct actual sources, successful executions, complete results and correspondence
  with the answer. Failed required execution is FAIL; unavailable evidence is
  UNCLEAR. Preregistered explanation/clarification branches are NOT_REQUIRED and
  never counted as successful source execution. The separate policy in Appendix C
  adds actual DAX evidence for numerical Semantic model cases and SQL-or-GQL
  evidence for B09; an empty legacy required_query_languages list does not waive
  execution. This diagnostic policy does not change the frozen content rubric or
  claim equivalence with the historical strict grader.
- 固定基準を満たしても、基準外の文章が誤る場合があります。追加の誤りを
  extra_factual_errors として記録し、固定採点条件を後から変更しません。 /
  Record errors beyond the fixed criteria separately; never rewrite the rubric.
- 固定の EventID 不在条件には、選択済み品質テーブルを含めると範囲が広すぎる
  記述があります。通常の観測集計ビューにはEventIDがありませんが、品質処理用の
  bronze/silver/quarantineにはあります。原典の基準を保持し、矛盾を記録します。
  品質処理用の母集団を通常の観測の回答へ置き換えません。 / Some frozen criteria
  describe EventID absence too broadly. The ordinary observation summary lacks it;
  selected quality-processing tables contain it. Retain the original criterion,
  record the caveat and do not substitute the quality population for observations.

## 過去結果との関係 / Relation to historical results

2026-10-15の51枠・296条件には非公開の未使用2問・6条件が含まれました。
このキットは公開49枠・290条件を再現します。過去の対応比較281条件の
189→217 PASS（67.26→77.22%）は補助条件充足率で、一般的な正答率や保証値では
ありません。今回の分岐、失敗、製品状態で分母と結果は変わります。
公開済みの29問を新しい「未使用問題」と呼びません。未知の問題への一般化を
調べる場合は、別の人が新しい問題と基準を事前固定し、調整者に見せず実施し、
その結果はこの49枠と別に報告します。過去の非公開問題は配布しません。

The historical 51-slot / 296-condition phases included two private unused
questions with six conditions. This kit reproduces the public 49-slot / 290-condition
portion. The historical 189→217 PASS on 281 paired applicable conditions
(67.26→77.22%) is supplemental condition fulfillment, not general accuracy or a
guarantee. Your branches, failures and service state determine your denominator
and result. Published questions are not new unseen tests. For generalization,
have another person freeze new private questions and keys before tuning and report
them separately. Historical private questions are not distributed.

## 保守担当者向けの確認 / Maintainer verification

From the repository root (no Fabric calls):

```sh
PYTHONPATH=tools/docs:tools/html python -m furusato_docs.participant30_evaluation --check-assets
```

This recomputes the public keys from the packaged synthetic sources and checks
every distributed file. It does not grade a participant's answers.
"""


def build_assets(root: Path):
    suite = public_suite(root)
    cases = [(kind, case) for kind in ("original", "regression") for case in suite[kind]["cases"]]
    files = {
        "canonical-public-suite.json": _json(suite),
        "README.md": README.encode("utf-8"),
        "registration-template.json": _json(_registration(suite)),
        "questions.csv": _csv(["suite", "case_id", "question_ja", "conditions_per_repeat"],
                              [[kind, case["id"], case["question"], len(case["conditions"])] for kind, case in cases]),
        "rubric.csv": _csv(["suite", "case_id", "condition_id", "criterion_ja", "required_query_languages"],
                           [[kind, case["id"], condition["id"], condition["text"],
                             ";".join(case["required_query_languages"])]
                            for kind, case in cases for condition in case["conditions"]]),
    }
    slot_rows, condition_rows, pair_rows = [], [], []
    for kind, repeat, case in _slots(suite):
        for condition in case["conditions"]:
            pair_rows.append([kind, repeat, case["id"], condition["id"], "", "", "", "", "", "", "", ""])
        for phase in ("baseline", "final"):
            slot_id = f"{phase}-{case['id']}-{repeat}"
            slot_rows.append([phase, slot_id, kind, repeat, case["id"], case["question"],
                              *([""] * 15)])
            for condition in case["conditions"]:
                condition_rows.append([phase, slot_id, kind, repeat, case["id"], condition["id"],
                                       condition["text"], "", "", "", "", ""])
    files["slots-template.csv"] = _csv([
        "phase", "slot_id", "suite", "repeat", "case_id", "question_ja", "started_at_utc",
        "ended_at_utc", "submission_status", "response_status", "private_answer_file",
        "private_execution_file", "actual_sources", "actual_query_languages", "native_status",
        "native_reason", "extra_factual_errors", "failure_category", "configuration_record",
        "reviewer", "notes",
    ], slot_rows)
    files["conditions-template.csv"] = _csv([
        "phase", "slot_id", "suite", "repeat", "case_id", "condition_id", "criterion_ja",
        "status", "reason", "private_evidence_file_and_location", "na_branch_evidence", "reviewer",
    ], condition_rows)
    files["paired-template.csv"] = _csv([
        "suite", "repeat", "case_id", "condition_id", "baseline_status", "final_status",
        "equal_question", "equal_criterion", "equal_data", "included", "exclusion_reason", "transition",
    ], pair_rows)
    files["SHA256SUMS.txt"] = "".join(f"{_sha(value)}  {name}\n" for name, value in sorted(files.items())).encode("ascii")
    return files


def append_chapter_sections(parent, root: Path):
    """Append self-contained manual instructions to participant Chapter 19."""
    from furusato_html.model import Block, Text
    from .participant30 import add_section, bullet_list, paragraph, text_table

    sections = [
        (("評価用ファイルと進め方を選ぶ", "Choose the evaluation files and scope"), [
            paragraph((
                "配布ZIPを展開し、source/workshop/v3.0.0-preview/data-agent/participant-evaluation を開きます。Gitで取得した場合はリポジトリ直下のworkshop/v3.0.0-preview/data-agent/participant-evaluationです。この節と付録Cだけで手動評価を進められます。実際の回答や実環境のIDは、Gitの外の自分専用フォルダーへ保存します。各templateを複製し、作業用ファイル名から -template を外します。JSONはテキストエディター、CSVはExcelなどで開けます。CSVのIDと時刻は文字列として取り込みます。",
                "Extract the distribution ZIP and open source/workshop/v3.0.0-preview/data-agent/participant-evaluation. In a Git checkout, use workshop/v3.0.0-preview/data-agent/participant-evaluation from the repository root. This section and Appendix C contain the complete manual evaluation procedure. Keep actual answers and live IDs in your own folder outside Git. Duplicate each template and remove -template from the working filename. Open JSON in a text editor and CSV in a spreadsheet; import IDs and timestamps as text.")),
            text_table([("選択", "Choice"), ("1段階の実施範囲", "Scope per phase"), ("用途", "Use")], [
                [("基本演習", "Practice"), "T01–T10 × 1 = 10 / 84", ("操作と採点を学ぶ。全体の改善を断定しない。", "Learn the process; do not infer full-suite improvement.")],
                [("公開問題の完全評価", "Full public evaluation"), "T01–T10 × 3 + B01–B19 × 1 = 49 / 290", ("今回の採用済み構成の再現確認と、次の修正の前後比較。", "Verify the adopted configuration and compare subsequent revisions.")],
            ], ("質問枠 / 条件数（1段階）", "Question slots / conditions per phase"), widths=(1.2, 2.7, 2.7)),
            paragraph((
                "今回の設定を初めて適用した後は、まず再現確認として測定します。次の変更を試す場合は、その現在の公開版をbaselineとして保存し、変更後をfinalとして測ります。過去の未調整設定へ戻す必要はありません。同じ構成を2回測った差を指示変更の効果と呼びません。",
                "After first applying the adopted configuration, measure it as reproduction testing. For a subsequent change, save the current publication as baseline and measure the changed publication as final. Restoring a historical untuned configuration is unnecessary. Differences between unchanged configurations do not establish an instruction-change effect.")),
            paragraph((
                "完全評価のslots.csvは前後合計98行、conditions.csvは580行、paired.csvは290行です。行はbaseline/finalが交互に並ぶため、最初にphase=baselineでフィルターし、候補を公開してからphase=finalへ切り替えます。フィルターした行を削除しません。最初の再現確認だけならbaselineを実施し、finalは未実施の予定として残します。改善を報告するときは両段階を完了します。",
                "The full templates contain 98 slot rows, 580 condition rows and 290 paired rows. Baseline/final rows are interleaved: first filter phase=baseline, then switch to phase=final after publishing the candidate. Do not delete filtered rows. For initial reproduction testing, run baseline and retain final as planned but unrun; an improvement comparison requires both phases.")),
        ]),
        (("開始前に記録を固定する", "Freeze the registration before starting"), [
            bullet_list([
                ("registration.json に日時、実施者、baseline/finalの設定名、仮説、変更する指示欄だけを記入します。完全評価の初期値は49枠・290条件・600秒です。基本演習なら開始前にpractice-10、10、84へ変更し、用紙からoriginal / repeat=1以外の予定行を外します。", "Fill in registration.json with date, reviewer, phase configuration labels, hypothesis and permitted instruction fields. Defaults are 49 slots, 290 conditions and 600 seconds. For practice, change to practice-10, 10 and 84 and remove other planned rows before beginning."),
                ("第17章で確認した公開版の指示、ソースID、選択テーブル・列、例、Ontology、スキーマ、メジャーを保存し、registrationに保存先と公開定義のSHA-256を記入します。モデル名や容量が表示される場合も記録し、見えない値を推測しません。", "Save the published instructions, source IDs, table/column selections, examples, ontology, schema and measures verified in Chapter 17. Record private file locations and the published-definition SHA-256. Record visible model/capacity information without guessing unavailable values."),
                ("データ配布版のSHA-256と、付録Aの件数・金額を実環境で確認した記録を保存します。同じCSVでも二重取り込みなら同じデータではありません。評価中はデータ更新、指示編集、モデル変更を止めます。変化した場合は比較不能と記録して新しい評価を登録します。", "Save the data-distribution SHA-256 and live checks of Appendix A counts and amounts. Duplicate ingestion changes the data even when CSVs match. Freeze data, instructions and model during evaluation; record any drift and register a new comparison."),
                ("questions.csv、rubric.csv、canonical-public-suite.jsonは変更しません。日本語の固定質問を翻訳せず送ります。付録Cは同じ原文と期待値を掲載しています。採点基準と期待値をAgentの指示、例、ソース説明に追加しません。", "Keep questions.csv, rubric.csv and canonical-public-suite.json unchanged. Send the fixed Japanese question without translation; Appendix C contains the same wording and answer keys. Never put criteria or expected answers into Agent instructions, examples or source descriptions."),
                ("新しい修正の採用条件も先に固定します。初期案は、FAIL→PASSが1件以上、PASS→FAILが0件、実ソースの実行根拠と事実の正しさが悪化しないことです。過去の採用判断をこの条件で再採点せず、これからの変更に使います。", "Preregister the adoption rule for new revisions. Suggested defaults are at least one FAIL→PASS, zero PASS→FAIL, and no deterioration in actual-source query execution records or factual correctness. This is a rule for future changes, not a regrading of historical adoption."),
            ], numbered=True),
            paragraph((
                "baselineの公開定義は最初の質問より前に保存します。finalの公開定義とそのSHA-256は、候補を適用・公開・読み戻した後、finalの最初の質問より前に追記します。未来のハッシュを推測しません。完全な公開定義を取得できない場合はその不足を記録し、画面から保存できた指示と選択の一致だけを確認済みとします。",
                "Save the baseline publication before its first question. Add the final publication and its SHA-256 after applying, publishing and reading back the candidate, before the first final question. Never invent a future hash. If the complete published definition is unavailable, record that gap and claim only the instruction/selection checks actually made from the UI.")),
            paragraph((
                "ファイルのSHA-256を調べるには、第17章で使ったPythonのターミナルをZIP内のsourceフォルダー（Gitならリポジトリ直下）で開き、次を実行します。最初のコマンドの出力をdataManifestSha256へ記録します。2つ目は最後の引用符内を実際に保存した公開定義JSONのパスへ置き換え、該当する段階のPublishedDefinitionSha256へ記録します。公開定義が取得できなければ空欄と理由を残します。",
                "To calculate SHA-256, use the Chapter 17 Python terminal from the ZIP's source folder or the Git repository root. Record the first command's output as dataManifestSha256. In the second command, replace the final quoted path with your saved published-definition JSON and record its hash for that phase. If the publication cannot be obtained, leave its hash blank with the reason.")),
            Block("code", {"text": 'python -c "import hashlib,pathlib,sys; print(hashlib.sha256(pathlib.Path(sys.argv[1]).read_bytes()).hexdigest())" "workshop/v3.0.0-preview/data/dataset-manifest.json"', "language": Text("Python: データ配布版", "Python: data distribution")}),
            Block("code", {"text": 'python -c "import hashlib,pathlib,sys; print(hashlib.sha256(pathlib.Path(sys.argv[1]).read_bytes()).hexdigest())" "<published-definition-json-path>"', "language": Text("Python: 保存した公開定義", "Python: saved publication")}),
            text_table([("用紙の欄", "Record fields"), ("記入する値", "What to enter")], [
                ["phase / slot_id / suite / repeat / case_id", ("配布済みの値を保持。1行が1質問枠です。", "Keep the supplied values. Each slot row represents one planned submission.")],
                ["started_at_utc / ended_at_utc", ("UTCのISO 8601時刻。例の形式: YYYY-MM-DDTHH:MM:SSZ。", "UTC ISO 8601 timestamps, in YYYY-MM-DDTHH:MM:SSZ form.")],
                ["submission_status", "sent / not_sent / unknown"],
                ["response_status", "completed / failed / timeout / blocked / unknown / not_run"],
                ["private_answer_file / private_execution_file", ("Git外に保存した回答全文と実行詳細のファイル名。未取得は空欄にして理由をnotesへ。", "Private files containing the entire answer and execution details. If unavailable, leave blank and explain in notes.")],
                ["actual_sources / actual_query_languages", ("実際に使われたソースとSQL/KQL/GQL/DAX。期待経路を転記しません。", "Sources and SQL/KQL/GQL/DAX actually observed; do not copy expected routes.")],
                ["status / reason / private_evidence_file_and_location", ("条件のPASS/FAIL/UNCLEAR/NA、理由、ファイル名と該当する行や画面。", "Condition verdict, reason, and file plus line/screenshot location.")],
                ["native_status / native_reason", ("独立した実行確認のPASS/FAIL/UNCLEAR/NOT_REQUIREDと理由。これは過去の厳密な審査ツールと同一の判定ではありません。", "Separate execution-review PASS/FAIL/UNCLEAR/NOT_REQUIRED with reason. This is not the historical strict-grader verdict.")],
                ["failure_category / extra_factual_errors", ("source / time / grain / meaning / execution。固定条件外の誤記も本文と根拠を記入。", "source / time / grain / meaning / execution. Preserve errors beyond fixed criteria with supporting text/evidence.")],
                ["equal_question / equal_criterion / equal_data / included", ("前後比較用のyes/no。included=noには除外理由と元の判定を残します。", "yes/no for pairing. An excluded row retains the reason and original verdicts.")],
                ["transition", ("例: PASS→FAIL。全290行を対応付け、採用した行だけ残す操作はしません。", "For example, PASS→FAIL. Pair all 290 rows; do not retain only favorable outcomes.")],
            ], ("空の記録用紙の記入方法", "How to fill the blank records"), widths=(2.3, 4.3)),
        ]),
        (("49枠を実行して条件ごとに採点する", "Run all 49 slots and judge each condition"), [
            bullet_list([
                ("公開版Data Agentを開きます。T01–T10を順に1周し、同じ順序で2周目・3周目、その後B01–B19を1周します。1問の反復も毎回Clear chatまたは新しい会話を使います。質問セルだけを1回貼り付けて送信し、開始時刻をslots.csvへ記録します。", "Open the published Agent. Run T01–T10 in order for three rounds, then B01–B19 once. Start a fresh chat for every slot, including repeats. Send only the question cell once and record its start time in slots.csv."),
                ("600秒まで回答を待ちます。回答全文と、実行詳細に表示された実ソース、クエリ、実行状態、完全な結果を保存します。表示されない実行情報は不明です。通常のUIで取得できる根拠だけで判定し、記載されたSQLを自分で実行した結果をAgentの実行証拠にしません。", "Wait up to 600 seconds. Save the complete answer and the actual source, query, status and complete results shown in execution details. Missing details are unknown. Judge only evidence actually available; your own execution of a displayed SQL query is not proof that the Agent executed it."),
                ("終了時刻、送信状態、応答状態、保存先、実行言語をslots.csvに記入します。送信したか不明、タイムアウト、製品エラー、フィルター停止でもその枠を残します。再送して置き換えず、期待値や補足質問を追加しません。", "Fill in end time, submission/response status, private evidence locations and actual languages in slots.csv. Retain uncertain submissions, timeouts, product errors and content blocks. Never replace a slot by resubmitting or provide expected values or follow-up hints."),
                ("conditions.csvの同じphase/slot_idの行を開き、付録Cの各条件を原文どおり判定します。status、理由、根拠ファイルと該当箇所、採点者を記入します。B系のfactは列挙された値の全体、contentは要求要素の全体で1条件です。一部が合うだけでPASSにしません。", "In conditions.csv, judge each row for the same phase/slot_id against the verbatim Appendix C criterion. Record verdict, reason, evidence file/location and reviewer. A B-case fact criterion covers all stated values; content covers every required element. Partial matches do not pass."),
                ("slots.csvのnative_statusを内容の採点と別に判定します。必要な全ソースで実クエリの成功、十分な結果、回答との対応が確認できた場合だけPASSです。実行失敗はFAIL、根拠不足はUNCLEAR、事前定義された実行不要の説明・確認質問はNOT_REQUIREDです。", "Judge native_status separately from content. PASS requires successful actual queries on every required source, complete results and correspondence with the answer. Failed execution is FAIL, missing evidence is UNCLEAR, and preregistered explanation/clarification branches are NOT_REQUIRED."),
            ], numbered=True),
            text_table([("判定", "Verdict"), ("使う条件", "When to use it")], [
                ["PASS", ("その条件全体を裏付ける根拠がある。", "Evidence supports the entire condition.")],
                ["FAIL", ("条件を満たさない、数値が誤る、必要要素が欠ける。T10のサービスブロックは全7条件FAIL。", "Incorrect, incomplete or missing required elements. A T10 service block is seven FAILs.")],
                ["UNCLEAR", ("送信や回答が不明、または必要な根拠を取得できない。分母には残す。", "Uncertain submission/answer or unavailable necessary evidence; retain in the denominator.")],
                ["NA", ("T03で妥当な確認質問だけを返した場合の T03.evidence.1、T03.evidence.2、T03.pass_criteria.2 のみ。選択した分岐と回答を保存する。", "Only T03.evidence.1, T03.evidence.2 and T03.pass_criteria.2 in a valid clarification-only branch. Preserve the branch evidence.")],
            ], ("条件の判定。エラーをNAへ振り替えません。", "Condition verdicts. Never relabel an error NA."), widths=(1.0, 5.6)),
            paragraph((
                "固定条件には、通常の観測用ビューにEventIDがないことを、選択済みソース全体へ広く表現した箇所があります。品質処理用bronze/silver/quarantineにはEventIDがあります。原文の条件は変更せず、相違を記録し、満たさない条件はFAILとします。通常の観測質問へ品質処理の別母集団を代用しません。採点条件の外に見つかった誤記もextra_factual_errorsへ残します。",
                "Some frozen criteria describe EventID absence more broadly than the physical schema: the ordinary observation view lacks it, while quality-processing bronze/silver/quarantine tables contain it. Retain the original criterion, record the discrepancy and keep unmet criteria FAIL. Do not substitute a quality-processing population for an ordinary observation question. Record additional factual errors outside the fixed criteria in extra_factual_errors.")),
        ]),
        (("1つの修正を比較し、採用を判断する", "Compare one revision and decide whether to adopt it"), [
            bullet_list([
                ("baseline全体の失敗をソース、期間、粒度、意味、実行に分類します。1つの仮説を決め、変更前後の指示全文と理由を保存します。Global指示は配布時点で10,000 UTF-16単位の上限を使っているため、追記ではなく既存の文を必要な範囲で置き換えます。第17章の長さ確認を行い、保存エラーを無視しません。製品のSchemaUnavailableや認証エラーを、答えを暗記させる指示で回避しません。", "Classify baseline failures by source, time, grain, meaning and execution. Save the full before/after instruction text and one hypothesis. The distributed global instructions already use the 10,000 UTF-16-unit limit, so replace the relevant existing wording rather than appending notes. Check length as in Chapter 17 and never ignore a save error. Do not bypass SchemaUnavailable or authentication errors by teaching memorized answers."),
                ("自分の候補はData AgentのDraft画面で対象の指示欄だけを変更し、Save、Publish、画面を開き直して公開版を確認します。変更後の全文と設定名・ハッシュを保存し、ソースなど他の欄が変わっていないことを確認します。第17章の固定profile用helperを再実行すると、今回の候補を配布設定へ戻す、または一致確認に失敗するため、独自候補の適用・認定には使いません。", "For your own candidate, edit only the intended instruction field in the Agent Draft UI, Save, Publish, then reopen and inspect the publication. Save its complete text, configuration label and hash, and confirm other fields stayed fixed. Do not use the Chapter 17 fixed-profile helper to apply or certify a custom candidate: it restores the distributed profile or reports a mismatch."),
                ("データ、ソース選択、例、メジャー、実行方法、質問、条件を同じに保ち、finalの全49枠を実施します。限定的な事前確認をした場合は正式枠とは別に記録し、全体の代用にしません。", "Keep data, selections, examples, measures, execution method, questions and criteria fixed, then run all 49 final slots. Record any targeted checks separately; they do not replace the full phase."),
                ("paired.csvでsuite/repeat/case_id/condition_idをキーに前後の判定を転記します。質問・条件・業務データが同じか確認します。片側が妥当なT03のNAである条件は、両側同じキーをincluded=noとして除き、元判定と理由を残します。他の失敗や不明は除外しません。", "Pair verdicts in paired.csv by suite/repeat/case_id/condition_id. Confirm equal questions, criteria and business data. For a valid T03 NA on either side, mark the same key excluded on both sides and retain original verdicts/reasons. Do not exclude other failures or unknowns."),
                ("共通分母は290−実際の除外数です。両段階のPASS/共通分母と差を計算し、PASS→PASS、PASS→FAIL、FAIL→PASS、FAIL→FAIL、UNCLEARの遷移をすべて数えます。不明→PASSは新たに根拠が得られた結果で、既知の誤答を直した証拠とは区別します。", "The matched denominator is 290 minus actual exclusions. Compute PASS/that denominator for each phase and their difference. Count all transitions, including regressions and unknowns. UNCLEAR→PASS is new evidence, not proof that a known wrong answer was corrected."),
                ("採用条件を確認し、内容の充足、実行根拠、条件外の誤記をまとめて判断します。満たさなければ修正案を採用せず、今回のbaselineとして保存した指示全文をDraftの同じ欄へ戻し、Save、Publish、公開版の確認を行います。元のbaselineが配布profileと同一と確認済みの場合に限り、固定helperでの復元も使えます。結果を見て採用条件や採点基準を緩めず、次の仮説は新しい版で始めます。", "Apply the preregistered adoption rule using content fulfillment, query execution records and errors outside the criteria. If it fails, restore the full instructions saved for this baseline into the same Draft fields, Save, Publish and inspect the publication. Use the fixed helper for restoration only when the saved baseline is confirmed identical to that distributed profile. Do not relax rules after seeing results; register the next hypothesis as a new revision."),
            ], numbered=True),
            paragraph((
                "報告には構成・データ・評価日時、予定49枠と実施状態、全290条件のPASS/FAIL/UNCLEAR/NA、除外理由、対応比較、退行、実行根拠、未解決の製品制約、採用判断を含めます。一般的な正答率や全文章の正しさと呼ばず、補助条件充足率として示します。",
                "Report configuration, data, dates, all 49 registered slot outcomes, PASS/FAIL/UNCLEAR/NA across all 290 conditions, exclusions, paired changes, regressions, query execution records, unresolved service limits and the adoption decision. Label the ratio supplemental condition fulfillment, not general accuracy or correctness of every sentence.")),
            paragraph((
                "過去の51枠・296条件には非公開の未使用2問・6条件が含まれます。この教材は公開49枠・290条件を再現します。過去の結果は保証値ではなく、今回の共通分母は実際の適用条件から求めます。公開29問はすでに既知の問題です。未使用問題を追加するなら別の人が新規の質問と基準を事前固定し、調整者へ開示せず、その結果は別集計にします。",
                "The historical 51-slot/296-condition campaign included two private unused questions with six criteria. This course reproduces the public 49-slot/290-condition portion. Historical results are not guarantees; calculate your denominator from actual applicability. The 29 public questions are already known. For an unseen test, another person must preregister new private questions and keys, withhold them from the tuner and report results separately.")),
        ]),
    ]
    for title, blocks in sections:
        suffix = str(len(parent.children) + 1)
        add_section(parent, suffix, title, blocks)


def _value_rows(value, prefix=""):
    if isinstance(value, dict):
        for key, child in value.items():
            yield from _value_rows(child, f"{prefix}.{key}" if prefix else key)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _value_rows(child, f"{prefix}[{index}]")
    else:
        yield [prefix, str(value) if value is not None else "null"]


def append_rubric_sections(parent, root: Path, start=2):
    """Render all public cases verbatim, including complete expected-value tables.

    These sections intentionally retain canonical wording even when it contains
    terms discouraged in ordinary participant prose. Never apply ``plain_block``.
    """
    from furusato_html.model import Block, Text
    from .participant30 import add_section, paragraph, text_table

    suite = load_suite(root)
    cases = [case for kind in ("original", "regression") for case in suite[kind]["cases"]]
    for index, case in enumerate(cases, start):
        blocks = [
            paragraph(("固定質問（この文だけを送信します）", "Fixed Japanese question (send only this text)")),
            Block("code", {"text": case["question"], "language": Text("質問（日本語）", "Question (Japanese)")}),
            text_table([("項目", "Field"), ("内容（原文）", "Canonical content")], [
                [("期待するソース・経路", "Expected source / route"), case.get("route", case.get("expected_source", ""))],
                [("原典の実行言語一覧", "Original execution-language list"), ", ".join(case["required_query_languages"]) or ("原典の一覧は空。下記の実行確認方針を使います。", "The original list is empty; use the execution review policy below.")],
                [("期待値", "Expected answer"), case["expected"]],
            ] + ([("Query shape", case["query_shape"])] if "query_shape" in case else []),
                ("採点用の参照。Agentの指示へ貼り付けません。", "Grading reference. Never paste into Agent instructions."), widths=(1.6, 5.0)),
            text_table([("条件ID", "Condition ID"), ("採点基準（原文を変更しません）", "Verbatim scoring criterion")],
                       [[condition["id"], condition["text"]] for condition in case["conditions"]],
                       (f"{case['id']} の全{len(case['conditions'])}条件", f"All {len(case['conditions'])} criteria for {case['id']}"), widths=(1.7, 4.9)),
        ]
        if "expected_values" in case:
            blocks.append(text_table([("参照キー", "Reference key"), ("値", "Value")],
                                     list(_value_rows(case["expected_values"])),
                                     ("期待値の完全な内訳（省略なし）", "Complete expected-value breakdown"), widths=(3.4, 3.2)))
        for block in blocks:
            if block.kind in {"code", "table"}:
                block.payload["canonicalLiteral"] = True
        blocks.append(paragraph((
            "実行確認（固定の内容採点とは別）: " + execution_review(case)[0],
            "Execution review (separate from fixed content scoring): " + execution_review(case)[1])))
        section = add_section(parent, str(index), (case["id"], case["id"]), blocks)
        # A visible, stable marker lets validators preserve frozen rubric wording.
        section.ident += "-canonical-evaluation"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write-assets", action="store_true")
    group.add_argument("--check-assets", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    files = build_assets(root)
    directory = root / ASSET_RELATIVE
    if args.write_assets:
        directory.mkdir(parents=True, exist_ok=True)
        for name, value in files.items():
            (directory / name).write_bytes(value)
    else:
        different = [name for name, value in files.items()
                     if not (directory / name).is_file() or (directory / name).read_bytes() != value]
        if different:
            raise SystemExit("Public evaluation assets differ: " + ", ".join(different))
    print(f"Verified {len(files)} public evaluation files: 29 questions / 122 unique conditions; 49 slots / 290 conditions per phase.")


if __name__ == "__main__":
    main()
