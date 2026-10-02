# Furusato Workshop 3.0.0

**既知の制約を開示した教材リリースです。AI回答品質・全機能の合格、Fabric機能のGAを意味しません。**

[Word](guide/Fabric_IQ_Ontology_Workshop_Furusato_Participant_v3.0.0.docx) ·
[日英HTML](guide/furusato-workshop-v3-0-0-complete.html) ·
[SHA-256](guide/SHA256SUMS.txt) ·
[GitHub Release / ZIP](https://github.com/yang-jiayi/furusato-fabric-workshop/releases/tag/v3.0.0)

WordとHTMLは同じフォルダーへ保存してください。HTMLは自己完結型で、日英切替・検索・
実習チェック・印刷・ローカルWordリンクを利用できます。

## 収録内容 / Contents

24章・5付録、審査済みの実画面48配置、Ontology CopilotのPDF/TXT/PNG添付、Metrics、
Business Rules、継承・共有property、Graph、MCP、Code Interpreter、Version history、
RDF/OWL import/export、配置・運用・評価手順を収録します。
元の合成データと固定10問・84条件は保持しています。

The released course contains 24 chapters and five appendices, with 48 reviewed
native capture placements and reproducible portable assets. The original
synthetic data and ten-question/84-condition rubric are unchanged. Partial
images remain partial; historical observations are not new-deployment guarantees.

## 評価結果 / Evaluation

| 評価 / Evaluation | 結果 / Result | 範囲 / Scope |
|---|---:|---|
| 明示選択したProvenance全run / Selected complete original run | **76 PASS / 8 FAIL** | 元10問・84条件。9つの履歴を個別に保持 / Original ten/84; nine ledgers retained |
| FieldLedger限定診断 / Targeted FieldLedger diagnostic | 14 PASS / 0 FAIL | 出典分担の1問のみ。全84条件の置換ではない / One attribution case, not a full-suite replacement |
| 別値heldout / Different-value heldout | 13 PASS / 0 FAIL | 4問。チューニング・全run合算なし / Four cases, not tuned or combined |

[評価レポート](reports/evaluation-report.md) · [進捗と証拠](reports/progress-report.md) ·
[公開集計JSON](reports/evaluation-summary.json)

新たな100問・口語評価と再デプロイは、このリリース後の別工程です。
この版の結果に未実行の100問を加えず、将来の改善版は別の版・記録として扱います。

The requested new 100-case colloquial evaluation and redeployment follow this
release. They are not completed results in this snapshot. Later tuning must
retain a separate version, frozen cases and before/after evidence.

## 既知の制約 / Known limitations

- 最新全runの8 FAILは、出典分担1条件とnative固定ブロック7条件です。
  固定ブロックを文脈付きの適切な拒否へ読み替えません。
- metadata-only Copilot Actで共有参照が消失した実失敗を保持します。通常metadata
  editorの安全な更新や別のEntity追加成功は、この不具合の修復ではありません。
- 新generation2 Ontology-context追加は当該環境で保存されませんでした。
  旧consumerのgen1 bridgeは明示的な別の互換経路であり、暗黙のダウングレードではありません。
- Metric付き検証用Ontologyの基準版Saveはnative HTTP400。保存された版がないため、
  説明変更やRestoreを行わず、元OntologyとSemantic Modelを保持しました。
- 主Ontologyの時系列Graphは失敗。時系列queryと別の静的Graphの成功は別の証拠です。
  増分は自動2件＋手動補完1件で、3件自動とはしません。
- Namespaces・直接Dashboard・soft detachのUIや低権限本人での否定テストは、
  条件付き／未確認のままです。RDF label・型・headerの損失も記録します。

The release preserves every failure and unavailable lane. It does not imply
zero FAIL, blanket feature acceptance, permission enforcement, lossless RDF
round-tripping or main-Agent promotion. Source-owned DAX, actual data queries,
configuration displays and response prose are distinct evidence.

## デプロイする / Deploy

可搬runtimeは互換性のため既存の
[`workshop/v3.0.0-preview/`](../../workshop/v3.0.0-preview/README-runtime.md)
に保持しています。`preview`はFabric機能・runtime profileの技術的識別子であり、
教材リリース版は**3.0.0**です。パスやgeneration識別子を一括置換しないでください。

1. 通常のMicrosoft認証を行い、Workspaceと対象folder GUIDを実際に確認します。
2. [runtime手順](../../workshop/v3.0.0-preview/README-runtime.md)でprivate scopeとread-only
   preflightを作成し、対象・名前衝突・元データhashを確認します。
3. 明示承認した新しい配置だけを段階実行します。既存Itemや同じ増分ファイルを
   無条件に上書き・再送しません。
4. 実データ、source-owned Model、Ontology binding、Agentの回答と実行証拠を確認します。
   過去の配置成功・このリリースの存在を、新環境のready判定に流用しません。

The portable source path remains `workshop/v3.0.0-preview` for compatibility.
Use its explicit scope, fingerprint, confirmation and native-UI handoff gates.
Notebook01/05 code retains the established source-data contract. Root `VERSION`
continues to identify the retainedv2.7 runtime baseline used by legacy tooling;
the current course release is identified by this directory and thev3.0.0 tag.

## 再生成と保護 / Reproduction and safeguards

公開projectionは
[`docs/assets/v3.0.0-evidence/manifest.json`](../assets/v3.0.0-evidence/manifest.json)です。
匿名化済みPNG、原画hash、caption、集計だけを収録し、private原画・実環境ID・生回答・
内部reasoning・追加評価の正解・旧private repository履歴を含めません。

原稿は[共有日英モデル](../../tools/docs/furusato_docs/preview30_content.py)、
操作入口は[文書builder手順](../../tools/docs/README.md)です。3.0.0の公開は、
既知の制約を認める明示的なrelease approvalに基づきます。厳密な全機能・0 FAILの
`RequireAcceptance`は変更せず、教材公開の許可と品質合格を区別します。

The release is explicitly authorized with disclosed limitations. The strict
all-feature/zero-FAIL admission remains unchanged and is not represented as
passed. Builders operate in fresh private staging; rendered output and package
hashes are checked before publication.

```powershell
.\tools\docs\Build-Preview30.ps1 `
  -Stage '<fresh absolute private release stage>' `
  -ReleaseProfile v3.0.0 `
  -ReleaseApproval '<private, explicit known-limitations approval JSON>'
```

The explicit approval binds version3.0.0, the selected original run, actual
76/8 counts and the exact public-projection SHA256. It is not distributed
inside the ZIP. Omitting or mismatching it stops before output creation.
Use `-RequireAcceptance` only for a genuine strict all-feature acceptance check;
it correctly remains blocked for this known-limitations release.

## 保持する公開版 / Retained public editions

[Preview1](https://github.com/yang-jiayi/furusato-fabric-workshop/releases/tag/v3.0.0-preview.1-20260930) ·
[v2.7.0](https://github.com/yang-jiayi/furusato-fabric-workshop/releases/tag/v2.7.0-unified-20260923)

以前の公開tag・assets・評価結果は変更しません。
