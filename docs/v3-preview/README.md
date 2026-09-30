# Furusato Workshop 3.0 Preview

[日本語](#日本語) · [English](#english)

## 日本語

**実装・検証結果を収録したPreviewです。AI回答品質は未合格、GA・全機能合格ではありません。**
**[Word・205ページ](guide/Fabric_IQ_Ontology_Workshop_Furusato_Participant_v3.0.0-preview.docx) ·
[対応する日英HTML](guide/furusato-workshop-v3-0-0-preview-complete.html) ·
[SHA-256](guide/SHA256SUMS.txt)**。HTMLはダウンロードしてローカルで開いてください。
Wordを同じフォルダーに置くと、HTML内のWordリンクも利用できます。
**[公開Previewリリース](https://github.com/yang-jiayi/furusato-fabric-workshop/releases/tag/v3.0.0-preview.1-20260930)**には、
一括ZIPと単体ファイル、公開ダウンロードの一致を確認したチェックサムを掲載しています。

Wordと日英HTMLは同じ共有原稿から実ファイルを生成します。v2.7の全19章・5付録の本文、
表、コード、元の10問・84条件は、比較・移行参考として保持します。元の合成データも変更しません。
旧UIの写真を新UI演習の成功証拠に流用しません。

新機能は実機でのreadbackや独立評価が必要です。ローカル文書・添付テスト合格は、
Ontology Copilotの実添付・利用、Graph実行、native配送などの合格ではありません。
有効な新UI証拠が無いビルドは、表紙と各演習に **DRAFT / not-run** を明示します。
blocked / unsupportedはそのまま表示し、合格へ置き換えません。

観測runでは自動002/003＋native UI手動001で全15,000行を実query照合しました。
primary coreはreview済み**73 static + 1 TS**で、native operational KQLを機能検証済みです。
TS GraphはEligibleでもInvalidPropertyTypeで失敗し、同じLakehouseの別static companion
**10Entity/72 static/15Relationship**でnative GQL・109,592 nodes/297,303 edgesを確認しました。
追加Lakehouse/source datasetのcopy、TS削除、Agent routingの自動変更はありません。
**Graph実体化は派生projectionを保存するため、Graph自体をzero-copyとは呼びません。**

CI smoke、別typed intentのkeyless Entity追加、bound Version restore、RDF構造往復は
それぞれの範囲だけの成功です。旧metadata-only Act失敗は保持し、Rule→Relationship誤提案も
保存前に拒否しました。baseline **9/23/1/51** とStaticFirst **22/10/1/51** は履歴で、
Context published-MCPは元10問を各1回、**39 PASS / 38 FAIL / 実行未検証4 / N/A3 / 前提blocked0**で完了しました。
main未変更・未promotionです。後続native UI T04では正しいgen2 itemに対しAPI-version非対応の
実connector errorを確認しました。Graph/data不在ではなく、consumer互換性を別に検証します。
新Gold-aware 4添付runは確認済みですが、UI/SDK診断や添付smokeをMCP84条件へ加点しません。

最終Compat **NativeUI / sandbox / preview / recorded model gpt-5.6-terra** は元10問を各1回、
**48 PASS / 36 FAIL / N/A0 / 実行未検証0 / 前提blocked0**でした。
coordinatorのmanual fixed-rubric offline判定で、FAIL29は内容/要求証拠、7はT10 native gateです。
異なる10 backend会話、9 source実行（SQL5/GQL2/KQL2、実行証拠は7質問slot）を確認しました。
mainは未promotion、過去MCPとの直接因果A/Bではありません。

gen1 opt-in bridgeの別consumer pathではGQLが動作しましたが、gen2 connector修正の証明ではなく、
親集約grain等の品質失敗を残します。4つのpublicationは不変、Compat draftのcatalog拡張も
parent-gatedなKQL11/LH99の実選択scopeを変えておらず、再Publishしていません。
[PUBLIC評価レポート](reports/evaluation-report.md)・[PUBLIC進捗レポート](reports/progress-report.md)を参照してください。

The observed architecture separates functional operational TS from the static Graph companion
over the same Lakehouse. Delivery is **two automatic files plus one manual recovery**, never
three automatic successes. CI, additive Plan/Act, bound restore and structural RDF observations
are scoped results, not blanket course acceptance. Original AI histories remain separate from
the completed Context MCP run (39/38/4 plus3 N/A, zero preblocked). Its subsequent native UI
connector error is separate evidence—not a missing-Graph/data diagnosis or score correction.
The isolated generation1 bridge enabled actual Data Agent GQL; full answer quality remains unaccepted
and the generation2 connector is not fixed. There is no automatic downgrade. Multi-namespace UI/direct-dashboard availability and negative
identity tests retain explicit conditions. **Preview is not GA.**

The same Lakehouse/source is reused without an extra source dataset, but Graph
materialization **stores a derived projection**. It is not zero-copy Graph.
The reviewed right-pane crops for the four-file Gold-aware run are available in
[`v3-preview-gold-attachments`](../assets/v3-preview-gold-attachments/manifest.json);
[`capture-review.json`](../assets/v3-preview-gold-attachments/capture-review.json) records
original hashes, crop rectangles and sanitized hashes. This approved **partial**
projection is not the default final-course projection or release freeze.

### 審査済み公開projection / Reviewed public projection

[正確な証拠形式・public export・最終freeze手順](evidence-contract.md)を参照してください。
厳密なprivate original/sanitized path+hash gateは維持し、審査済みの画像だけを
`docs/assets/v3-preview-evidence/manifest.json` へ明示projectionします。
原本・実ID・endpoint・UPN・machine path・回答/正解キー・内部reasoningは収録しません。
この公開projectionがあれば、配布sourceだけで同じ内容・画像・status集計を再生成できます。
観測runは新配置のreadinessを保証せず、runtime契約も変更しません。

Keep private original/sanitized validation intact. The explicit reviewed public projection
contains only sanitized images, original-hash provenance, bilingual captions, review dates
and safe aggregate/status records. Default source-only build/validation/packaging consume it
without private files; it does not certify a new environment's readiness.

The [full-course historical projection](../assets/v3-preview-evidence/manifest.json)
is now the default source-only evidence input:23 native capture placements,
including every prior reviewed image and the newly reviewed completion images.
Its status is **frozen-for-build**: the final evidence and sealed runtime inputs
were used for the reviewed pair linked below. The narrow
382px attachment panes remain partial; additive-entity success does not change the
old failed metadata-only Act. The package presentation is
**Preview with implementation and verification results—AI answer quality not accepted, not GA**.

<a id="preview-verification-files"></a>
### Preview verification files / 明示v3 Previewファイル

The reviewed files are separate from the stable v2.7 distribution. The course
contains 24 chapters and five appendices; Word has 205 pages. Keep Word and HTML
together when downloading the individual files.

| Deliverable | Download / contents |
|---|---|
| Full 24-chapter Word | [Fabric_IQ_Ontology_Workshop_Furusato_Participant_v3.0.0-preview.docx](guide/Fabric_IQ_Ontology_Workshop_Furusato_Participant_v3.0.0-preview.docx) |
| Matching JA/EN HTML | [furusato-workshop-v3-0-0-preview-complete.html](guide/furusato-workshop-v3-0-0-preview-complete.html) |
| Pair integrity | [SHA256SUMS.txt](guide/SHA256SUMS.txt) |
| Preview bundle, visibly DRAFT where strict gates require | [Furusato_Workshop_v3.0.0-preview_DRAFT.zip](https://github.com/yang-jiayi/furusato-fabric-workshop/releases/download/v3.0.0-preview.1-20260930/Furusato_Workshop_v3.0.0-preview_DRAFT.zip): guide pair, four exercise attachments and public reports |
| Source-owned public reports | [evaluation](reports/evaluation-report.md), [progress](reports/progress-report.md), [aggregate JSON](reports/evaluation-summary.json) |
| Portable deployment assets | [v3 runtime, notebooks and explicit optional compatibility handoff](../../workshop/v3.0.0-preview/README-runtime.md) |

The builder and QA procedures below reproduce the pair from the approved public
source projection. Stable v2.7 files/links are not repointed or overwritten.
The evaluation/progress reports retain their pre-publication freeze state; the
[published prerelease](https://github.com/yang-jiayi/furusato-fabric-workshop/releases/tag/v3.0.0-preview.1-20260930)
is the current distribution record. It does not change the recorded quality verdict.

### 教材と実ファイル

| 項目 | 場所 |
|---|---|
| 全文共有原稿（日英） | [preview30_content.py](../../tools/docs/furusato_docs/preview30_content.py) |
| Word + HTML builder | [build_preview30.py](../../tools/docs/build_preview30.py) |
| 実ファイル検証・Word描画・ローカルHTML操作 | [validate_preview30.py](../../tools/docs/validate_preview30.py) |
| 合成業務要件PDF | [business-requirements.pdf](../../workshop/v3.0.0-preview/attachments/business-requirements.pdf) |
| 実スキーマの可搬TXT | [data-dictionary.txt](../../workshop/v3.0.0-preview/attachments/data-dictionary.txt) |
| 日英の方向付き業務モデルPNG | [domain-model.png](../../workshop/v3.0.0-preview/attachments/domain-model.png) |
| 改訂・曖昧要求の追加TXT | [revision-requirements.txt](../../workshop/v3.0.0-preview/attachments/revision-requirements.txt) |
| 添付の生成・検証・操作 | [tools/preview30-attachments](../../tools/preview30-attachments/README.md) |
| 新UI撮影要求・掲載章 | [preview30-capture-requests.json](../../tools/docs/assets/preview30-capture-requests.json) |
| 保持する比較版 | [v2.7 Word](../Fabric_IQ_Ontology_Workshop_Furusato_Participant_v2.7.0_unified-20260923.docx) · [v2.7 日英HTML](../furusato-workshop-v2-7-0-complete_unified-20260923.html) |

原本、build途中、PDF描画、評価、実ID、会話、非公開draftはリポジトリ外のPRIVATE stagingへ置きます。
最終Word/HTMLを審査するまで、既存の `RELEASE_SHA256SUMS.txt` はv2.7検証済み配布物を指すままです。
未審査のdraftをこの公開docsへコピーするコマンドはbuilderにありません。

### 24章

| 章 | テーマ |
|---|---|
| 1 | シナリオ・学習目標・完成アーキテクチャ |
| 2 | DBA・BIエンジニアのためのOntology設計 |
| 3 | Furusato業務モデルの設計根拠 |
| 4 | 前提条件・配置範囲・安全な実行 |
| 5 | LakehouseとNotebook 01 |
| 6 | 新UIでのOntology・Entity・Property作成 |
| 7 | Relationshipと静的モデルの検証 |
| 8 | EventhouseとKQLスキーマ |
| 9 | PipelineとOneLakeイベント連携 |
| 10 | 増分取り込みと時系列バインディング |
| 11 | Notebook 05による品質処理とGold |
| 12 | Semantic ModelとOntology Metrics |
| 13 | Metadata・Business Rules・Notebook 02 |
| 14 | Namespaces・継承・共有プロパティ |
| 15 | Ontology Copilot（組み込みOntology Agent）による設計・改善・照会 |
| 16 | 選択的Graph実体化とGQL |
| 17 | Fabric Data AgentとCode Interpreter |
| 18 | 業務シナリオによる横断演習 |
| 19 | AI回答品質の評価と改善 |
| 20 | MCPと可視化による外部利用 |
| 21 | Version historyによる変更管理 |
| 22 | RDF／OWLのImport・Export |
| 23 | Publish・共有・ガバナンス |
| 24 | 自動配置・旧版移行・運用・クリーンアップ |

付録Aはデータ・モデル・期待値、Bは全Notebook設定、Cは固定問題/採点/記録、DはOptional、
Eは移行対応表・トラブルシューティング・公式資料です。

### 仕様上の重要な境界（2026-09-29公式資料確認）

- 新experienceの正式definitionはTMDL/TMSL++（compatibilityLevel 1000000）です。
  旧EntityTypes JSONをv3と呼び替えません。[新定義契約と往復損失の注意](definition-contract.md)を参照してください。
- Graphはoptional・opt-in。キー必須。semantic-model-backed、keyless、unbound、
  multiple-backing-tableのEntityは不適格になり得ます。実Status/tooltipを確認します。
- MetricsはソースSemantic model所有のDAXを参照します。Ontologyの編集はmodelのDAXを変えません。
  Fabric Data AgentでDAXを使うなら同じ主Agentにmodelを直接source構成します。
  DAX-backed Metricの `backingMeasure` は現在TMDL往復で保持できないため、native Metrics追加後の全文再送を禁止します。
- Business Rulesは自然言語contextで、制約実行やactionではありません。新Ontologyは直接Activator連携なし。
  9月23日の独立Activator `start_rule` / `stop_rule`、完成PutBlob、native配送証拠を保持します。
- CopilotのPDF/TXT/PNGは会話文脈で、取り込み・RDF import・権限ではありません。
  最大10ファイル/会話・5MB/ファイル。添付なし/ありは同一baselineの別会話で比較します。
- Version historyは定義の復元であり、sourceデータの復元ではありません。
- native importは空Ontologyのみ、TTL/RDF/OWL対応。exportはTTL/RDFのみ。
  v2.7 RDFのcustom annotationはlosslessなnative round-tripを保証しません。
- Agentが生成したテスト質問は独立評価ではありません。標準10問/84条件と追加評価を別に記録します。

### Build・検証

`$PrivateDocuments` をリポジトリ外の承認済みPRIVATE stagingに設定してください。
Pythonと既存 `tools/docs/requirements.txt`、HTML操作検査のPlaywright、描画検査のPyMuPDF、
Word COM、ローカルheadless Edgeを使用します。HTMLの操作テストはローカルfileだけを読み、
外部HTTP(S)を遮断し、Fabricブラウザーへ接続しません。

```powershell
$Stage = Join-Path $PrivateDocuments 'preview30-build-01'
# Use the owner's already frozen attachment pack; do not regenerate it in document preparation.
python .\tools\preview30-attachments\test_attachments.py
python -m unittest discover -s .\tools\docs\tests -p test_preview30_content.py
python .\tools\docs\build_preview30.py `
  --out (Join-Path $Stage 'pair') --review (Join-Path $Stage 'build')
python .\tools\docs\validate_preview30.py `
  --pair (Join-Path $Stage 'pair') --review (Join-Path $Stage 'review') `
  --render --interactions --print-html
```

非ゼロ終了で停止してください。再buildは新しいstageを使用し、既存pairを上書きしません。
pairには以下の**実2ファイルだけ**が生成されます。SHA256とレポートはpair外のreviewへ保存します。

- `Fabric_IQ_Ontology_Workshop_Furusato_Participant_v3.0.0-preview.docx`
- `furusato-workshop-v3-0-0-preview-complete.html`

### 1コマンドの完全ローカル実行と可搬DRAFT

既に用意した添付教材を検査し、Word/HTMLを生成、Word・日英HTMLを描画、ローカル操作を検証し、
可搬DRAFT ZIPまで作成するコマンドです。Fabricのサインインやクラウドwriteは一切行いません。
`-PublicEvidenceManifest` は任意です。省略時はsource-owned default projectionがあれば使い、
なければ実UI写真なしのDRAFTです。private作業の`-EvidenceManifest`とは排他的です。
**source準備phaseでは実行せず、最終AI・添付・runtime resealの承認後に1回だけbuildします。**

```powershell
.\tools\docs\Build-Preview30.ps1 `
  -Stage (Join-Path $PrivateDocuments 'offline-draft-01') `
  -PublicEvidenceManifest .\docs\assets\v3-preview-evidence\manifest.json
```

stage内は `pair`（正確な2ファイル）、`review`、`checks`、`package` に分かれます。
`package\Furusato_Workshop_v3.0.0-preview_DRAFT.zip` は次のallowlistのみを収録します。

- `guide/` のWordと日英HTML（同じフォルダーなのでダウンロードリンクが成立）
- `attachments/` の4教材とそのmanifest・SHA256一覧
- `START_HERE.txt`、`DRAFT_STATUS.json`、内容の `SHA256SUMS.txt`
- `reports/` のsanitized progress/evaluation Markdown・集計JSON・SHA256（最終runを含む場合）

原本画像、実環境ID、raw評価、会話、privateログはZIPへ入れません。local検査数はAI正答率ではありません。
ZIPはローカルで展開して利用し、ZIP自体をCopilotへの添付やRDF importとして扱いません。

PUBLIC reportsはsourceのapproved projectionだけから再生成できます。これはWord/HTML/ZIP buildではありません:

```powershell
python -B .\tools\docs\build_preview30_reports.py
python -B .\tools\docs\build_preview30_reports.py --check
```

配布ZIPは教材・添付・レポートを収録します。デプロイ用コードとNotebookはリポジトリの
`workshop/v3.0.0-preview` にあります。Previewと安定版を混同しないでください。
stable v2.7の配布ペアと既存linksは置換しません。
過去の実画面は撮影UTCを明示し、現在の認証成功や演習全体の合格とは区別します。
現在の認証がFIDO/Windows Helloで停止している場合は、利用者の通常認証が完了するまでblockedです。
token/cookie抽出・注入や認証迂回によって進めません。

すでに完全ローカル検証済みのpairを再buildせずZIP化する場合:

```powershell
python .\tools\docs\package_preview30.py `
  --pair $ReviewedPair --validation $FullLocalValidationJson `
  --public-evidence .\docs\assets\v3-preview-evidence\manifest.json --out $FreshPrivatePackageDirectory
```

packagerは保存済みの完全検査と現在のWord/HTML hashを照合し、共有原稿、画像位置・実pixelを再検証します。
認証やscopeは承認しません。常にDRAFTとして作成し、public releaseへ自動昇格しません。

### 独立評価レポートの安全な取り込み

評価担当が生成した既存 `furusato-preview30-report/v1` を、
`Build-Preview30.ps1 -EvaluationReport <private-report.json>` または各Pythonコマンドの
`--evaluation-report <private-report.json>` で任意に取り込めます。
private build/validate/packageすべてに同じ凍結snapshotを渡してください。
source-only再現には既存の許可済みprojectionをpublic manifestへexportし、private overrideは渡しません。
元84条件の新run集計は[evidence contract](evidence-contract.md)の厳格なaggregate形式を使います。

`furusato_docs/preview30_evaluation.py` が公開許可された集計、生成日時、state_counts、
AIの要求/採点数・nullを含むaccuracy、case_id/repeat/category/critical/state/supportだけへ投影します。
元10問/84条件のsummaryは `independent_hidden=false` を保持します。
context、reasons/errors、raw証拠、private path/ID、prompt、trace、held-out corpusは出力しません。

- support=pendingがある場合、supported_requested_slots=0は**UNKNOWN**で、対応機能0件ではありません。
- scored_questions=0、accuracy=nullは**未採点**であり、0%正答率でも合格でもありません。
- planned/implemented/deployed、local_validation pass、ローカルunit testsをlive AI/UIのpassへ変換しません。
- blocked/unsupported/unverifiedを黙って分母から除外せず、snapshotの生成日時をそのまま表示します。
- 独立held-outの質問・鍵は読み込まず、guide/添付/few-shot/例へ転用しません。

The optional `-EvaluationReport` / `--evaluation-report` hook consumes only the
existing evaluator report contract and publishes its explicitly approved projection.
Private context, prompts, reasons, traces and held-out content are excluded. Pending
applicability with zero confirmed-supported slots means **UNKNOWN**; unscored null
accuracy is not 0%. Local tests never become live AI acceptance. Supply the same
frozen report to build, validate and package.

### 実UI証拠の受渡

コーディネーターのPRIVATE `manifest.json` は `furusato-preview30-evidence/v1`。
`captures` 配列と全対象の `labs` オブジェクトを持ちます。
各captureは要求ID、原本/加工版のmanifest相対path、双方SHA256、撮影日時、new experience、
実画面フラグ、審査者、redactions、privacy審査、日英captionを持ちます。
形式と強制条件は [preview30_evidence.py](../../tools/docs/furusato_docs/preview30_evidence.py)。

Word/HTMLは同じ審査済み画像だけを使います。画像の状態や結果を加工して合格にしてはいけません。
`observed` は部分的な実画面の観測で、合格ではありません。`passed` は全要求captureの
`completionEvidence=true` と実行/readbackを要求します。縦長の部分抜粋はcompletion用の解像度ゲートを迂回しません。
Copilot Actのpassはさらに、ID・Entity/property集合・型・key・binding・継承・shared-referenceの保持と
承認metadata差分だけであることを、authoritative readbackの `invariants` で全て確認します。
synonym追加で `reusableProperty` が予期せず削除された観測例はfailedです。成功メッセージやID一致で上書きしません。
PaymentMethod追加は別`copilot-additive-entity`のtyped intent/approvedDelta/observedDeltaと
既存partsの厳密保持で判定します。旧失敗の修正合格ではありません。既知問題laneもfailedを保持します。
`blocked` / `unsupported` も実際の
非提供/エラー画面と理由を記録します。画像なしのまま最終検証済みと主張しません。

コーディネーター形式の審査済み抜粋は `tools/docs/import_preview30_evidence.py` で
許可したprivate原本rootから別のfresh private snapshotへ複製できます。hash、privacy review、
実new-experienceを確認し、**常にobservedとして取り込み、合格は推定しません**。
未対応のcapture IDは掲載位置を明示的にレビューするまで拒否します。

```powershell
python .\tools\docs\build_preview30.py `
  --out (Join-Path $FreshStage 'pair') --review (Join-Path $FreshStage 'build') `
  --evidence $PrivateEvidenceManifest --require-evidence
python .\tools\docs\validate_preview30.py `
  --pair (Join-Path $FreshStage 'pair') --review (Join-Path $FreshStage 'review') `
  --evidence $PrivateEvidenceManifest --render --interactions --print-html
```

最終描画・目視・日英操作検査後の2ファイルだけを審査して公開配置します。
このツールはcommit/push/release/PRやクラウド変更を実行しません。

## English

This is the **complete 24-chapter / five-appendix new-experience curriculum**, not a
proposal or skeleton. The builder generates actual Word and bilingual offline HTML
from one model. All substantive v2.7 prose, tables and code remain explicitly
labelled comparison/migration references; old screenshots are never new-UI evidence.
Original synthetic data and the ten questions / 84 conditions are unchanged.

The public baseline remains v2.7 until a reviewed new pair is ready. Builds without
reviewed actual UI evidence visibly say **DRAFT / not-run**. Local documentation
tests cannot prove live Copilot attachment use, graph queries or native delivery.
Blocked/unsupported features and the reviewed metadata-only Act known issue are recorded
honestly, not converted to passes. The positive additive entity has its own typed intent
and exact-delta contract; the original ACT_INVARIANTS are unchanged.

Use the commands above with a **fresh external PRIVATE stage**. `pair` contains
exactly the named DOCX and HTML. Reports, hashes, PDF renders and screenshots are
outside that pair. Word fields/TOC are refreshed with the existing COM renderer;
the approved General label and generic author are normalized after the last save.
The HTML records the exact Word SHA256. Local automated interactions run in a new
headless browser against file URLs only, with external HTTP(S) blocked.

The [attachment pack](../../tools/preview30-attachments/README.md) contains an actual
Japanese-font-embedded bilingual PDF, a dictionary generated from public CSV/schema
contracts, a legible directed-domain PNG and optional revision text. Attach them in a
new Plan conversation and compare against a separate no-attachment conversation on
the same baseline. Attachments are conversation-local context, not ingestion or RDF.
Review draft/validation/preview, explicitly authorize Act on the lab copy, and read
the applied definition back without replacing stable IDs.

Important current boundaries:

- New-experience definitions use **TMDL/TMSL++**, not renamed old entity-type JSON.
  Read the [official new-definition contract findings](definition-contract.md),
  including the current loss of DAX `backingMeasure` on TMDL round trips.
- Graph is optional and requires eligible keyed, bound, supported Delta entities;
  semantic-model-backed entities cannot be projected.
- Metrics proxy source-owned DAX. Configure the semantic model directly on the one
  main Fabric Data Agent for DAX; it does not inherit ontology-carried grounding.
- Business Rules are natural-language context, not enforcement or actions, and new
  ontology has no direct Activator integration.
- Preserve separate formal Activator start/stop, complete-file PutBlob and native
  delivery evidence. A manual fallback is not a native-delivery pass.
- Restore versions restores definitions, not source data. Native import needs an
  empty item and accepts TTL/RDF/OWL; export accepts TTL/RDF only. Custom v2.7 RDF
  annotations do not imply a lossless round trip.
- Agent-generated questions are exploratory, not independent evaluation.

Current procedures cover every chapter listed above, including scoped source
discovery, actual bindings, source reconciliation, failure/corrective checks and
evidence status. The [26 required capture requests and optional response excerpts](../../tools/docs/assets/preview30-capture-requests.json)
specify exact placements and required UI states. Only the coordinator supplies
genuine captures and private originals/sanitization provenance. A final source-only build uses
the approved default public projection or `--public-evidence ...`, followed by complete local
and visual review. `--require-evidence` is an explicit review-coverage gate, not an all-feature
pass claim; it does not transform failed/conditional lanes or runtime readiness.
Reviewed partial excerpts can be imported privately with
`tools/docs/import_preview30_evidence.py`. They remain `observed`, never inferred
passes; narrow excerpts cannot satisfy the stricter completion-image size gate.
Copilot Act acceptance additionally requires every strict readback invariant,
including shared-property references. An observed synonym-only Act that removed
`reusableProperty` remains failed despite preserved IDs and an AI success claim.
No command commits, publishes, creates releases, or mutates Fabric.

For a complete one-command **local-only** run, use `tools/docs/Build-Preview30.ps1`
with a fresh private `-Stage` and approved `-PublicEvidenceManifest` (or the default
source-owned projection). Private `-EvidenceManifest` remains supported as a separate mode.
It builds the pair, performs Word/JA/EN rendering and interaction checks, verifies
actual capture pixels and creates a deterministic **DRAFT ZIP**. The ZIP contains
only guides, portable attachments, checksums and explicit draft status—not original
captures, private transcripts, evaluation logs or private AI scores. Unpack it
locally; the ZIP itself is not an ontology import or a supported lab attachment.
Past screenshots are timestamped historical observations, never proof of current
FIDO/Windows Hello authentication. Authentication and scope blockers remain blockers.
