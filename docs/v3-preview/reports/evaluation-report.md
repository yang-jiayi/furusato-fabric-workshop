# 実装・検証結果を収録したPreview — 評価結果 / Evaluation

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
| Main baseline | 5 | 9 | 23 | 1 | 51 | 0 | published-mcp |
| Isolated StaticFirst | 5 | 22 | 10 | 1 | 51 | 0 | published-mcp |
| Context published-MCP | 10 | 39 | 38 | 4 | 0 | 3 | published-mcp |
| Final Compat NativeUI (quality not accepted, not promoted) | 10 | 48 | 36 | 0 | 0 | 0 | native-ui |

Historical published-MCP scores are retained unchanged. The final native-UI candidate,
consumer generation, transport and observed runtime differ: **not a direct causal MCP A/B**.
Operator Graph/TS/CI smoke or separate UI/SDK diagnostics do not rewrite these ledgers.

| Case | PASS | FAIL | Source executions | Native gate |
|---|---:|---:|---:|---|
| T01 | 7 | 0 | 1 | — |
| T02 | 6 | 0 | 1 | — |
| T03 | 6 | 0 | 2 | — |
| T04 | 6 | 5 | 1 | — |
| T05 | 9 | 5 | 2 | — |
| T06 | 2 | 8 | 1 | — |
| T07 | 5 | 3 | 1 | — |
| T08 | 5 | 2 | 0 | — |
| T09 | 2 | 6 | 0 | — |
| T10 | 0 | 7 | 0 | native gate |

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
| T04 | 親集約grain・表現 / Parent aggregation grain/presentation | 親粒度でengine集約し、child rowsを親集計として扱わない。必要な関係/方向の説明を確認。<br>Aggregate at the requested parent grain; do not substitute child rows. Check required relationship/direction presentation. |
| T05 | ID・source証拠 / Identifiers/source evidence | 必要なbusiness IDsとlabelsを選択projectionへ含め、実sourceの根拠を示す。<br>Include needed business IDs with labels and actual-source attribution. |
| T06/T07 | operational期間 / Operational time window | 実sourceの年/月を照会し、static年を仮定しない。観測時刻と取込時刻を分ける。<br>Discover source year/month rather than assuming the static year. Separate observation from ingestion timestamps. |
| T08 | 指標とモデル経路 / Measures and modeled path | 件数・金額・scopeを別々に明示し、モデルのDonation経路と照合する。<br>Label counts, amounts and scope separately and reconcile against the modeled Donation path. |
| T09 | cross-source回答 / Cross-source answer | 定義済みscopeの横断回答を、clarificationだけへ置換しない。<br>Do not replace the defined-scope cross-source result with a clarification-only response. |
| T10 | native content gate / Native content gate | 失敗を保持し、公式診断/supportへ渡す。bypassせず、contextual refusal成功としない。<br>Retain the failure and use official diagnostics/support. Do not bypass it or count it as successful contextual refusal. |

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
