# 参加者の評価キット / Participant evaluation kit

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
