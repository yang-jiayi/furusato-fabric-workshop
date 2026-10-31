# 19.7 49枠を実行して条件ごとに採点する

[Lab 目次](../README.md) · [この章の目次](README.md)

1. 公開版Data Agentを開きます。T01–T10を順に1周し、同じ順序で2周目・3周目、その後B01–B19を1周します。1問の反復も毎回Clear chatまたは新しい会話を使います。質問セルだけを1回貼り付けて送信し、開始時刻をslots.csvへ記録します。
2. 600秒まで回答を待ちます。回答全文と、実行詳細に表示された実ソース、クエリ、実行状態、完全な結果を保存します。表示されない実行情報は不明です。通常のUIで取得できる根拠だけで判定し、記載されたSQLを自分で実行した結果をAgentの実行証拠にしません。
3. 終了時刻、送信状態、応答状態、保存先、実行言語をslots.csvに記入します。送信したか不明、タイムアウト、製品エラー、フィルター停止でもその枠を残します。再送して置き換えず、期待値や補足質問を追加しません。
4. conditions.csvの同じphase/slot_idの行を開き、付録Cの各条件を原文どおり判定します。status、理由、根拠ファイルと該当箇所、採点者を記入します。B系のfactは列挙された値の全体、contentは要求要素の全体で1条件です。一部が合うだけでPASSにしません。
5. slots.csvのnative_statusを内容の採点と別に判定します。必要な全ソースで実クエリの成功、十分な結果、回答との対応が確認できた場合だけPASSです。実行失敗はFAIL、根拠不足はUNCLEAR、事前定義された実行不要の説明・確認質問はNOT_REQUIREDです。

**条件の判定。エラーをNAへ振り替えません。**

| 判定 | 使う条件 |
| --- | --- |
| PASS | その条件全体を裏付ける根拠がある。 |
| FAIL | 条件を満たさない、数値が誤る、必要要素が欠ける。T10のサービスブロックは全7条件FAIL。 |
| UNCLEAR | 送信や回答が不明、または必要な根拠を取得できない。分母には残す。 |
| NA | T03で妥当な確認質問だけを返した場合の T03.evidence.1、T03.evidence.2、T03.pass_criteria.2 のみ。選択した分岐と回答を保存する。 |

固定条件には、通常の観測用ビューにEventIDがないことを、選択済みソース全体へ広く表現した箇所があります。品質処理用bronze/silver/quarantineにはEventIDがあります。原文の条件は変更せず、相違を記録し、満たさない条件はFAILとします。通常の観測質問へ品質処理の別母集団を代用しません。採点条件の外に見つかった誤記もextra_factual_errorsへ残します。

<details>
<summary>English</summary>

## 19.7 Run all 49 slots and judge each condition

1. Open the published Agent. Run T01–T10 in order for three rounds, then B01–B19 once. Start a fresh chat for every slot, including repeats. Send only the question cell once and record its start time in slots.csv.
2. Wait up to 600 seconds. Save the complete answer and the actual source, query, status and complete results shown in execution details. Missing details are unknown. Judge only evidence actually available; your own execution of a displayed SQL query is not proof that the Agent executed it.
3. Fill in end time, submission/response status, private evidence locations and actual languages in slots.csv. Retain uncertain submissions, timeouts, product errors and content blocks. Never replace a slot by resubmitting or provide expected values or follow-up hints.
4. In conditions.csv, judge each row for the same phase/slot_id against the verbatim Appendix C criterion. Record verdict, reason, evidence file/location and reviewer. A B-case fact criterion covers all stated values; content covers every required element. Partial matches do not pass.
5. Judge native_status separately from content. PASS requires successful actual queries on every required source, complete results and correspondence with the answer. Failed execution is FAIL, missing evidence is UNCLEAR, and preregistered explanation/clarification branches are NOT_REQUIRED.

**Condition verdicts. Never relabel an error NA.**

| Verdict | When to use it |
| --- | --- |
| PASS | Evidence supports the entire condition. |
| FAIL | Incorrect, incomplete or missing required elements. A T10 service block is seven FAILs. |
| UNCLEAR | Uncertain submission/answer or unavailable necessary evidence; retain in the denominator. |
| NA | Only T03.evidence.1, T03.evidence.2 and T03.pass_criteria.2 in a valid clarification-only branch. Preserve the branch evidence. |

Some frozen criteria describe EventID absence more broadly than the physical schema: the ordinary observation view lacks it, while quality-processing bronze/silver/quarantine tables contain it. Retain the original criterion, record the discrepancy and keep unmet criteria FAIL. Do not substitute a quality-processing population for an ordinary observation question. Record additional factual errors outside the fixed criteria in extra_factual_errors.

</details>
