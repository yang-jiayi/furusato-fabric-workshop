# 明示選択したPreview進捗 / Explicitly selected Preview progress

実装・検証結果を収録したPreview — AI回答品質は未合格／GAではありません

Preview with implementation and verification results — AI answer quality not accepted; not GA

明示選択: provenance-native-ui-20261001 — 76 PASS / 8 FAIL / 0 execution-unverified / 0 BLOCKED / 0 N/A = 84。AI回答品質は未合格。main未promotion（記録）。元10問/84条件と履歴を保持。全機能合格・公開・操作許可ではありません。

Explicit selection: provenance-native-ui-20261001 — 76 PASS / 8 FAIL / 0 execution-unverified / 0 BLOCKED / 0 N/A = 84. AI answer quality is not accepted; main is not promoted in the record. Original ten/84 and historical ledgers are retained. Not all-feature acceptance, publication or authorization to act.

source実行成功でも不完全・打切り結果が返る場合があり、成功回数は返却行/query結果の完全性を証明しません。同じcaseの後続aggregateが完全でも、先の返却結果が完全になるわけではありません。native応答の終端完了は別のproofで、打切り数の未掲載は打切り0を意味しません。

Successful source calls can return incomplete/truncated results; their counts do not prove that all returned rows or query results are complete. A later complete aggregate in the same case does not retroactively complete an earlier result. Terminal native-response completion is separate proof; omitted truncation counts never imply zero.

Content scope: **24 chapters / 5 appendices**; original ten questions /84 conditions,
synthetic data and stable v2.7 remain unchanged. Source-reviewed native placements:
**48**, unique sanitized images: **46**.

## source-owned lab状態 / Source-owned lab status

| Lab | 状態<br>State | sourceのscope<br>Source scope |
| --- | --- | --- |
| copilot-act | failed | 旧metadata-only patchはreusablePropertyを失いFAILED。native rollbackは確認済みだがbug修正合格ではない。known issueとして保持。<br>The old metadata-only patch lost reusableProperty and remains FAILED. Native rollback is verified, not a passed bug fix; retained as a known issue. |
| copilot-additive-entity | passed | 別typed intentのPaymentMethod/String property追加だけをPlan/Act/readbackで確認。既存semantic parts・IDs/keys/bindings/shared refsを保持し、model ref以外の既存変更なし。<br>Separate typed PaymentMethod/String-property Plan/Act/readback verified: existing semantic parts/IDs/keys/bindings/shared refs preserved, with only the approved model reference changed. |
| copilot-attachments | observed | 審査済みの実画面を配置。各captionの範囲だけを示し、部分表示や別の接続検査を演習全体の合格へ変更しません。<br>Reviewed native captures placed with their exact captioned scope. Partial views and separate connectivity checks do not confer whole-lab acceptance. |
| copilot-baseline | observed | 審査済みの実画面を配置。各captionの範囲だけを示し、部分表示や別の接続検査を演習全体の合格へ変更しません。<br>Reviewed native captures placed with their exact captioned scope. Partial views and separate connectivity checks do not confer whole-lab acceptance. |
| dashboard | blocked | direct Ontology→RTdashboard entryを観測できず、環境条件付き。TS探索はnative Ontology agent KQLで検証済みだがdirect dashboardではない。<br>Direct Ontology→RTdashboard entry is unobserved and environment-conditional. Native Ontology agent KQL verifies TS exploration, not direct-dashboard integration. |
| data-agent | failed | 審査済みの実画面を配置。各captionの範囲だけを示し、部分表示や別の接続検査を演習全体の合格へ変更しません。<br>Reviewed native captures placed with their exact captioned scope. Partial views and separate connectivity checks do not confer whole-lab acceptance. |
| entities | observed | primary core10Entity、73 static+1TSとMunicipality sampleの機能照合は確認。全EntityのUI完成captureは未網羅。<br>Primary core ten entities,73 static+one TS and functional Municipality sample are verified; complete UI coverage of every entity remains incomplete. |
| evaluation | failed | 元10問各1回/84条件のmanual fixed-rubric offline判定は48 PASS/36 FAIL、N/A/実行未検証/前提blocked0。FAIL29内容/要求証拠＋7nativeT10gate。過去MCPと合算/因果A/Bにしない。<br>Manual fixed-rubric offline judgment of original ten once/84 conditions:48 PASS/36 FAIL, zero N/A/unverified/preblocked.29 content/required-evidence failures plus seven native T10 gates. Do not merge or claim causal A/B with historical MCP. |
| gold | observed | 審査済みの実画面を配置。各captionの範囲だけを示し、部分表示や別の接続検査を演習全体の合格へ変更しません。<br>Reviewed native captures placed with their exact captioned scope. Partial views and separate connectivity checks do not confer whole-lab acceptance. |
| graph | observed | 審査済みの実画面を配置。各captionの範囲だけを示し、部分表示や別の接続検査を演習全体の合格へ変更しません。<br>Reviewed native captures placed with their exact captioned scope. Partial views and separate connectivity checks do not confer whole-lab acceptance. |
| inheritance | observed | Municipalityの実名・key/binding・AdministrativeArea継承を確認。stored/effective metadataとoverride/revertの全試験は未網羅。<br>Municipality business name/key/binding and AdministrativeArea inheritance verified; complete stored/effective/override/revert testing remains incomplete. |
| mcp | observed | 審査済みの実画面を配置。各captionの範囲だけを示し、部分表示や別の接続検査を演習全体の合格へ変更しません。<br>Reviewed native captures placed with their exact captioned scope. Partial views and separate connectivity checks do not confer whole-lab acceptance. |
| metrics | observed | 審査済みの実画面を配置。各captionの範囲だけを示し、部分表示や別の接続検査を演習全体の合格へ変更しません。<br>Reviewed native captures placed with their exact captioned scope. Partial views and separate connectivity checks do not confer whole-lab acceptance. |
| namespaces | blocked | wide new UI ribbonで管理entry未確認。RDF namespace URI/default namespace保持は実証済みだがUI管理ではない。全製品非対応とはしない。<br>Management entry is unconfirmed in the wide new-UI ribbon. RDF URI/default-namespace preservation is verified, not UI management or universal product unsupported status. |
| native-delivery | observed | 審査済みの実画面を配置。各captionの範囲だけを示し、部分表示や別の接続検査を演習全体の合格へ変更しません。<br>Reviewed native captures placed with their exact captioned scope. Partial views and separate connectivity checks do not confer whole-lab acceptance. |
| publish | unverified | 公開設定/role件数はread-onlyで確認、変更なし。第2の承認済み低権限principalがなくRLS/OLS/CLS negative testsは未証明。候補main promotionも未成立。<br>Publication configuration/role counts read only, without changes. No authorized second low-privilege principal for proven RLS/OLS/CLS negative tests; candidate main promotion is not established. |
| rdf | observed | standards-only native import/export/reimportとnamespace保持、14/14 normalized partsを確認。label/type/header損失は保持。480px export dialogはcompletion解像度不足で非掲載、runtime無損失ではない。<br>Standards-only native cycle/namespace preservation and14/14 normalized parts verified with label/type/header losses retained. The480px export dialog is not embedded as completion evidence; no runtime losslessness claim. |
| relationships | observed | static companion10/72/15・全labels/件数・要求pathをnative GQLとsourceへ照合。全mapping UI/全edge pairの網羅検査ではない。<br>Static companion10/72/15 labels/counts and requested paths reconcile through native GQL/source checks; not exhaustive mapping-UI/every-edge-pair validation. |
| rules | observed | 審査済みの実画面を配置。各captionの範囲だけを示し、部分表示や別の接続検査を演習全体の合格へ変更しません。<br>Reviewed native captures placed with their exact captioned scope. Partial views and separate connectivity checks do not confer whole-lab acceptance. |
| shared-properties | observed | Global表示、unsafe ActでのLocal化、native rollbackを保持。共有機能の全override/revert/detach受入れとは別。<br>Global display, unsafe Act localization and native rollback retained; separate from complete shared override/revert/detach acceptance. |
| timeseries | observed | native Planのbounded KQL実行と独立照合を確認、定義不変。73 static+1TSを保持。機能TS query成功でありTS Graph成功ではなく、追加query画面captureは未収録。<br>Native Plan bounded KQL execution and independent reconciliation are verified with unchanged definition and73 static+one TS. Functional TS querying, not TS Graph; the additional query-screen capture is not included. |
| version-history | observed | 審査済みの実画面を配置。各captionの範囲だけを示し、部分表示や別の接続検査を演習全体の合格へ変更しません。<br>Reviewed native captures placed with their exact captioned scope. Partial views and separate connectivity checks do not confer whole-lab acceptance. |

各状態はsource projectionに記録されたscopeだけです。選択runによる新しいUI/SDK/postcheckや
残る演習の再確認を推定しません。部分観測・失敗・blockedを保持します。

Each state retains its own source-projection scope, not a new UI/SDK/postcheck or
remaining-feature recheck inferred from selection. Partial observations, failures and blocked lanes remain.

## context / Context

**scopedCompatibility — unverified-not-newly-rechecked**

選択runに紐づくUI/connector互換性の追加審査記録なし。未検証・新規再確認なし。旧T04結果を流用しません。

No separately reviewed UI/connector compatibility facts are bound to this selected run. Unverified / not newly rechecked; do not reuse the old T04 outcome.

**postcheck — unverified-not-newly-rechecked**

選択runに紐づくpostcheckの追加審査記録なし。定義・公開・選択scopeの状態は未検証・新規再確認なし。

No separately reviewed postcheck is bound to this selected run. Definitions, publications and selected scope are unverified / not newly rechecked.

**externalSdk — unverified-not-newly-rechecked**

選択runに紐づく外部SDKの追加審査記録なし。送信数・blocker・修復は未検証・新規再確認なし。

No separately reviewed external SDK qualification is bound to this selected run. Submission count, blocker and repair are unverified / not newly rechecked.

## 再現・公開の境界 / Reproduction and publication boundary

- Explicit selected original-suite run: **provenance-native-ui-20261001**.
- Evidence projection SHA-256: `60338bc1461e1a14e6ae72e93ef1ed5871923bdd122e28db23acd96a84bcff03`.
- Freeze state: **frozen-for-build**; this is not publication or final user acceptance.
- No Word/HTML/ZIP build, cloud call, question, data/model/instruction change, promotion or publication is performed by report generation.
- [Input contract](../evidence-contract.md) / [selected evaluation](evaluation-report.md).

- Preview branch: 未確認のためlinkなし / no verified URL supplied; no link is fabricated.
- Preview release: 未確認のためlinkなし / no verified URL supplied; no link is fabricated.
- Stable **v2.7.0 / unified-20260923** is retained, not replaced.
