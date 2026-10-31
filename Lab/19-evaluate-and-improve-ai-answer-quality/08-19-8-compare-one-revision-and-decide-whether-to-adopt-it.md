# 19.8 1つの修正を比較し、採用を判断する

[Lab 目次](../README.md) · [この章の目次](README.md)

1. baseline全体の失敗をソース、期間、粒度、意味、実行に分類します。1つの仮説を決め、変更前後の指示全文と理由を保存します。Global指示は配布時点で10,000 UTF-16単位の上限を使っているため、追記ではなく既存の文を必要な範囲で置き換えます。第17章の長さ確認を行い、保存エラーを無視しません。製品のSchemaUnavailableや認証エラーを、答えを暗記させる指示で回避しません。
2. 自分の候補はData AgentのDraft画面で対象の指示欄だけを変更し、Save、Publish、画面を開き直して公開版を確認します。変更後の全文と設定名・ハッシュを保存し、ソースなど他の欄が変わっていないことを確認します。第17章の固定profile用helperを再実行すると、今回の候補を配布設定へ戻す、または一致確認に失敗するため、独自候補の適用・認定には使いません。
3. データ、ソース選択、例、メジャー、実行方法、質問、条件を同じに保ち、finalの全49枠を実施します。限定的な事前確認をした場合は正式枠とは別に記録し、全体の代用にしません。
4. paired.csvでsuite/repeat/case_id/condition_idをキーに前後の判定を転記します。質問・条件・業務データが同じか確認します。片側が妥当なT03のNAである条件は、両側同じキーをincluded=noとして除き、元判定と理由を残します。他の失敗や不明は除外しません。
5. 共通分母は290−実際の除外数です。両段階のPASS/共通分母と差を計算し、PASS→PASS、PASS→FAIL、FAIL→PASS、FAIL→FAIL、UNCLEARの遷移をすべて数えます。不明→PASSは新たに根拠が得られた結果で、既知の誤答を直した証拠とは区別します。
6. 採用条件を確認し、内容の充足、実行根拠、条件外の誤記をまとめて判断します。満たさなければ修正案を採用せず、今回のbaselineとして保存した指示全文をDraftの同じ欄へ戻し、Save、Publish、公開版の確認を行います。元のbaselineが配布profileと同一と確認済みの場合に限り、固定helperでの復元も使えます。結果を見て採用条件や採点基準を緩めず、次の仮説は新しい版で始めます。

報告には構成・データ・評価日時、予定49枠と実施状態、全290条件のPASS/FAIL/UNCLEAR/NA、除外理由、対応比較、退行、実行根拠、未解決の製品制約、採用判断を含めます。一般的な正答率や全文章の正しさと呼ばず、補助条件充足率として示します。

過去の51枠・296条件には非公開の未使用2問・6条件が含まれます。この教材は公開49枠・290条件を再現します。過去の結果は保証値ではなく、今回の共通分母は実際の適用条件から求めます。公開29問はすでに既知の問題です。未使用問題を追加するなら別の人が新規の質問と基準を事前固定し、調整者へ開示せず、その結果は別集計にします。

<details>
<summary>English</summary>

## 19.8 Compare one revision and decide whether to adopt it

1. Classify baseline failures by source, time, grain, meaning and execution. Save the full before/after instruction text and one hypothesis. The distributed global instructions already use the 10,000 UTF-16-unit limit, so replace the relevant existing wording rather than appending notes. Check length as in Chapter 17 and never ignore a save error. Do not bypass SchemaUnavailable or authentication errors by teaching memorized answers.
2. For your own candidate, edit only the intended instruction field in the Agent Draft UI, Save, Publish, then reopen and inspect the publication. Save its complete text, configuration label and hash, and confirm other fields stayed fixed. Do not use the Chapter 17 fixed-profile helper to apply or certify a custom candidate: it restores the distributed profile or reports a mismatch.
3. Keep data, selections, examples, measures, execution method, questions and criteria fixed, then run all 49 final slots. Record any targeted checks separately; they do not replace the full phase.
4. Pair verdicts in paired.csv by suite/repeat/case_id/condition_id. Confirm equal questions, criteria and business data. For a valid T03 NA on either side, mark the same key excluded on both sides and retain original verdicts/reasons. Do not exclude other failures or unknowns.
5. The matched denominator is 290 minus actual exclusions. Compute PASS/that denominator for each phase and their difference. Count all transitions, including regressions and unknowns. UNCLEAR→PASS is new evidence, not proof that a known wrong answer was corrected.
6. Apply the preregistered adoption rule using content fulfillment, query execution records and errors outside the criteria. If it fails, restore the full instructions saved for this baseline into the same Draft fields, Save, Publish and inspect the publication. Use the fixed helper for restoration only when the saved baseline is confirmed identical to that distributed profile. Do not relax rules after seeing results; register the next hypothesis as a new revision.

Report configuration, data, dates, all 49 registered slot outcomes, PASS/FAIL/UNCLEAR/NA across all 290 conditions, exclusions, paired changes, regressions, query execution records, unresolved service limits and the adoption decision. Label the ratio supplemental condition fulfillment, not general accuracy or correctness of every sentence.

The historical 51-slot/296-condition campaign included two private unused questions with six criteria. This course reproduces the public 49-slot/290-condition portion. Historical results are not guarantees; calculate your denominator from actual applicability. The 29 public questions are already known. For an unseen test, another person must preregister new private questions and keys, withhold them from the tuner and report results separately.

</details>
