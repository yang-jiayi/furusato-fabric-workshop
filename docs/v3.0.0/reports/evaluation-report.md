# 明示選択したPreview評価 / Explicitly selected Preview evaluation

実装・検証結果を収録したPreview — AI回答品質は未合格／GAではありません

Preview with implementation and verification results — AI answer quality not accepted; not GA

**明示選択: provenance-native-ui-20261001 — 76 PASS / 8 FAIL / 0 execution-unverified / 0 BLOCKED / 0 N/A = 84。AI回答品質は未合格。main未promotion（記録）。元10問/84条件と履歴を保持。全機能合格・公開・操作許可ではありません。**

**Explicit selection: provenance-native-ui-20261001 — 76 PASS / 8 FAIL / 0 execution-unverified / 0 BLOCKED / 0 N/A = 84. AI answer quality is not accepted; main is not promoted in the record. Original ten/84 and historical ledgers are retained. Not all-feature acceptance, publication or authorization to act.**

## 選択と方法 / Selection and method

観測時刻 / Observed: **2026-09-30T23:39:57.195000+00:00**。source projectionの審査済みIDだけを選択します。
最高点・最新時刻で選ばず、選択はpromotion・再実行・公開ではありません。

Only the explicitly reviewed source-projection ID is selected, never the highest score or latest
timestamp. Selection does not promote, rerun or publish anything.

| 記録<br>Record | 値<br>Value |
| --- | --- |
| 評価surface<br>Evaluation surface | native-ui |
| transport<br>Transport | responses |
| stage<br>Stage | sandbox |
| runtime<br>Runtime | preview |
| 記録model<br>Recorded model | gpt-5.6-terra |
| 固定rubric判定方法<br>Fixed-rubric judgment | manual-fixed-rubric-offline |
| 送信/前提blocked質問<br>Submitted/preblocked questions | 10 / 0 |
| 内容/要求証拠FAIL / native受入FAIL<br>Content/required-evidence FAIL / native-acceptance FAIL | 1 / 7 |
| source試行 / 成功 / 拒否<br>Source attempts / successes / rejections | 16 / 16 / 0 |
| 独立trace付き質問slot<br>Independently traced QUESTION slots | 8 |
| 証明された別backend会話<br>Proven distinct backend conversations | 10 |
| fresh backend proof<br>Fresh-backend proof | True |
| native応答の終端 完了 / 未完了 / 未検証<br>Terminal native responses completed / not completed / unverified | 10 / 0 / 0 |

| 言語<br>Language | 試行<br>Attempts | 成功<br>Successes | 拒否<br>Rejections |
| --- | --- | --- | --- |
| SQL | 5 | 5 | 0 |
| GQL | 3 | 3 | 0 |
| KQL | 8 | 8 | 0 |
| DAX | 0 | 0 | 0 |

試行・成功・拒否、独立trace付きQUESTION slot、別backend会話、native応答完了は別の分母です。
未提供は未検証で、ゼロや旧runの値を補いません。DAXはSQL/GQL/KQLへ合算しません。

Attempts, successes, rejections, independently traced QUESTION slots, distinct backend
conversations and completed native responses are separate denominators. Missing facts are
unverified, not zero or values borrowed from the old run. DAX is not folded into SQL/GQL/KQL.
These counts do not establish general-population accuracy or a direct causal MCP A/B.

source実行成功でも不完全・打切り結果が返る場合があり、成功回数は返却行/query結果の完全性を証明しません。同じcaseの後続aggregateが完全でも、先の返却結果が完全になるわけではありません。native応答の終端完了は別のproofで、打切り数の未掲載は打切り0を意味しません。

Successful source calls can return incomplete/truncated results; their counts do not prove that all returned rows or query results are complete. A later complete aggregate in the same case does not retroactively complete an earlier result. Terminal native-response completion is separate proof; omitted truncation counts never imply zero.

## 元10問/84条件の履歴 / Original ten/84 ledgers

| run / 選択<br>Run / selection | 送信/前提blocked<br>Submitted/preblocked questions | PASS / FAIL / U / B / N/A | 受入/promotion（審査記録）<br>Accepted/promoted, reviewed record |
| --- | --- | --- | --- |
| Main baseline（別個の観測記録）<br>Main baseline | 5 / 5 | 9 / 23 / 1 / 51 / 0 | False / False |
| Isolated StaticFirst（別個の観測記録）<br>Isolated StaticFirst | 5 / 5 | 22 / 10 / 1 / 51 / 0 | False / False |
| Context published-MCP（別個の観測記録）<br>Context published-MCP | 10 / 0 | 39 / 38 / 4 / 0 / 3 | False / False |
| 最終Compat NativeUI（品質未合格・未promotion）<br>Final Compat NativeUI (quality not accepted, not promoted) | 10 / 0 | 48 / 36 / 0 / 0 / 0 | False / False |
| Evidence<br>Evidence | 10 / 0 | 68 / 16 / 0 / 0 / 0 | False / False |
| EvidenceRefined<br>EvidenceRefined | 10 / 0 | 71 / 13 / 0 / 0 / 0 | False / False |
| Answerable<br>Answerable | 10 / 0 | 80 / 4 / 0 / 0 / 0 | False / False |
| Scoped recovery campaign<br>Scoped recovery campaign | 10 / 0 | 76 / 8 / 0 / 0 / 0 | False / False |
| Provenance<br>Provenance | 10 / 0 | 76 / 8 / 0 / 0 / 0 | False / False |

sourceの履歴順・集計は不変で、選択runだけを下に詳述します。UI/SDK/smoke証拠を合算しません。
Source history order and aggregates are unchanged. Only the selected run is detailed below;
separate UI/SDK/smoke evidence does not rewrite those ledgers.

## case判定と実行 / Case decisions and executions

| Case | PASS | FAIL | 未検証<br>Unverified | BLOCKED | N/A | native gate<br>Native gate |
| --- | --- | --- | --- | --- | --- | --- |
| T01 | 7 | 0 | 0 | 0 | 0 | — |
| T02 | 6 | 0 | 0 | 0 | 0 | — |
| T03 | 6 | 0 | 0 | 0 | 0 | — |
| T04 | 11 | 0 | 0 | 0 | 0 | — |
| T05 | 13 | 1 | 0 | 0 | 0 | — |
| T06 | 10 | 0 | 0 | 0 | 0 | — |
| T07 | 8 | 0 | 0 | 0 | 0 | — |
| T08 | 7 | 0 | 0 | 0 | 0 | — |
| T09 | 8 | 0 | 0 | 0 | 0 | — |
| T10 | 0 | 7 | 0 | 0 | 0 | 固定block失敗<br>fixed-block failure |

| Case | 試行<br>Attempts | 成功<br>Successes | 拒否<br>Rejections | native応答終端<br>Native response terminal state | 成功query言語<br>Successful query languages |
| --- | --- | --- | --- | --- | --- |
| T01 | 1 | 1 | 0 | 完了<br>completed | SQL |
| T02 | 1 | 1 | 0 | 完了<br>completed | SQL |
| T03 | 1 | 1 | 0 | 完了<br>completed | SQL |
| T04 | 1 | 1 | 0 | 完了<br>completed | GQL |
| T05 | 2 | 2 | 0 | 完了<br>completed | GQL, SQL |
| T06 | 2 | 2 | 0 | 完了<br>completed | KQL |
| T07 | 2 | 2 | 0 | 完了<br>completed | KQL |
| T08 | 0 | 0 | 0 | 完了<br>completed | — |
| T09 | 6 | 6 | 0 | 完了<br>completed | GQL, KQL, SQL |
| T10 | 0 | 0 | 0 | 完了<br>completed | — |

native固定blockはFAILのまま保持し、適切なcontextual refusalや成功queryへ置換しません。
完了応答だけでは内容の合格・source実行・fresh backendを証明しません。

A native fixed block remains FAIL, not a successful contextual refusal or query. Native
completion alone proves neither content acceptance, source execution nor a fresh backend.

## contextの再確認境界 / Context recheck boundaries

**scopedCompatibility — unverified-not-newly-rechecked**

選択runに紐づくUI/connector互換性の追加審査記録なし。未検証・新規再確認なし。旧T04結果を流用しません。

No separately reviewed UI/connector compatibility facts are bound to this selected run. Unverified / not newly rechecked; do not reuse the old T04 outcome.

**postcheck — unverified-not-newly-rechecked**

選択runに紐づくpostcheckの追加審査記録なし。定義・公開・選択scopeの状態は未検証・新規再確認なし。

No separately reviewed postcheck is bound to this selected run. Definitions, publications and selected scope are unverified / not newly rechecked.

**externalSdk — unverified-not-newly-rechecked**

選択runに紐づく外部SDKの追加審査記録なし。送信数・blocker・修復は未検証・新規再確認なし。

No separately reviewed external SDK qualification is bound to this selected run. Submission count, blocker and repair are unverified / not newly rechecked.

## 残る確認と受入の境界 / Remaining checks and acceptance boundary

失敗・未検証・blocked・N/Aを削除せず、元の固定rubricで審査します。集計だけから欠陥原因や
T04/SDK修復を推測しません。元suiteの受入flagは審査記録の値で、84 PASSから自動設定しません。
全機能と最終user受入には、残る演習の実証と別の明示承認が必要です。

Retain every FAIL, unverified, blocked and N/A cell under the unchanged rubric. Aggregate
counts do not diagnose a defect or prove T04/SDK repair. Original-suite acceptance is the
reviewed flag, never inferred from84 PASS. All-feature and final user acceptance require
actual remaining-feature evidence and separate explicit approval.

See [source-scoped progress](progress-report.md) and [approved summary](evaluation-summary.json).
