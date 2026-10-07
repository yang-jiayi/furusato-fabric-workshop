# Furusato Workshop 3.0.0 — 現行成果物の整合性

このディレクトリは現行mainの整合版用です。元の`v3.0.0`タグ・配布物と日付付き過去評価は
変更せず保持します。教材版、データ仕様、FabricのgenerationやAPI versionを混同しません。

[Word（232ページ）](guide/Fabric_IQ_Ontology_Workshop_Furusato_Participant_v3.0.0.docx) ·
[日英HTML](guide/furusato-workshop-v3-0-0-complete.html) ·
[Notebook・CSV・モデル等を含むZIP](Furusato_Workshop_v3.0.0_current-20261007.zip) ·
[Artifact-set](artifact-set.json) · [検証結果](deployment-verification.md) ·
[検証JSON](verification.json) · [SHA-256](SHA256SUMS.txt) ·
[回答精度の改善（2026-10-07）](../tuning-20261007/README.md) ·
[第3報: 逸脱の完了と対策](../followup-20261007/README.md) ·
[2026-10-04の記録](history/20261004/README.md)

**成果物整合性と旧フォルダの整理は確認済みです。** 2026-10-07の正式配置は22 Items（第3報で任意の
Power BIレポートを追加）・Agent1件・Temp0件です。
正式Agentの標準10問・84条件は、配置直後の**36/84・34/84**から、回答契約の復元後に
**74/84・73/84**（T10のnative遮断により上限77）となりました。事前登録holdout12問は
11 PASS／1 FAILです。AI回答品質の0 FAILではなく、文書203検査の成功はAI回答のPASSに加算していません。
第3報の残件候補R7・R8は事前に記録した採用規則を満たさず、正式Agentは上記の構成のままです。

## 版の正本

| 成果物・識別子 | 正本と扱い |
|---|---|
| 教材・Notebook01–05 | [`WORKSHOP_VERSION`](../../../WORKSHOP_VERSION) = **3.0.0**。見出し・metadata・Notebook01の配布版表示を一致させます |
| 配置用ディレクトリ | [`workshop/v3.0.0-preview`](../../../workshop/v3.0.0-preview/README-runtime.md)。技術的パスは既存互換のため維持 |
| 版の対応表 | [`edition.json`](../../../workshop/v3.0.0-preview/edition.json) |
| CSV | [`data`](../../../workshop/v3.0.0-preview/data)。`2.7.0-realistic.1`の値・行数・hashを保持。版表示のために再生成しません |
| 再利用する処理コード | `2.7.0`基線。Notebook01/05の処理ロジックと内部publication keyは維持 |
| 修正版Agent | [`standard-contract-restoration`](../../../workshop/v3.0.0-preview/data-agent/candidates/standard-contract-restoration/README.md)（4段階compilerの最終段。前段は[`time-layer-isolation`](../../../workshop/v3.0.0-preview/data-agent/candidates/time-layer-isolation/README.md)）。6 SQL views・全体/ソース指示・SQL17/KQL9例を同じ入力セットに含めます |
| Word / HTML | 同じ共有原稿から生成し、同じartifact-set SHAを本文とmetadataに記録。HTMLは対応するWordの実hashも保持 |

Notebook01の`NOTEBOOK_VERSION`は監査・表示用で、現行配布物では3.0.0です。
過去に実行されたロード監査の2.7.0を、実行し直さず3.0.0へ書き換えることはしません。
これは過去の来歴を保存するためです。データ仕様、内部control key、generation ID、
Power BI互換性レベルを教材版に合わせて一括置換すると、参照や再実行防止を壊します。

## 整合性の検査と再生成

```powershell
python tools\provisioning\build_preview30.py
python -m unittest discover -s tools\provisioning -p "test_preview30*.py"
python tools\provisioning\v3_artifacts.py `
  --out workshop\v3.0.0-preview\provisioning\artifact-set.json
```

artifact-setは、5 Notebook、sealed packageの中身、全CSV、モデル・Ontology・Agent profileと
構築コードの実SHAを記録します。Notebook02–04の埋め込みpackageにも最新の修正compiler、
6 SQL views、SQL/KQL例を含め、外側のファイルだけが新しい状態を拒否します。
Notebook01/05は、明示したNotebook01の監査・表示用versionを除き、処理コードの一致を検査します。

Word/HTMLのbuild・validate・packageには、同じ
`--artifact-manifest workshop\v3.0.0-preview\provisioning\artifact-set.json`を渡します。
manifest生成後に構築コード、Notebook、CSV、profileが変われば拒否されます。
現在の成果物検査はAI回答や全機能の合格判定とは別です。

2026-10-07の整合版は、次の分割実行で生成しました。`$Stage`はリポジトリ外の新しい
ディレクトリ、`$Approval`はリポジトリ外のprivateな文書配布承認（3.0.0の公開projectionと
76/8 runに結び付くもの。AI品質の受入ではありません）です。描画とHTML操作の検査には
Word、Edge、`python-docx`・`pymupdf`・`playwright`が必要です。

```powershell
$Manifest = "workshop\v3.0.0-preview\provisioning\artifact-set.json"
$Release = @("--release-profile", "v3.0.0", "--release-approval", $Approval, "--artifact-manifest", $Manifest)
python -B tools\docs\build_preview30.py --out "$Stage\pair" --review "$Stage\review" @Release
python -B tools\docs\validate_preview30.py --pair "$Stage\pair" --review "$Stage\checks" `
  --render --interactions --print-html @Release
python -B tools\docs\package_preview30.py --pair "$Stage\pair" `
  --validation "$Stage\checks\validation.json" --out "$Stage\package" @Release
```

## Tempを使わない本デプロイ

指定フォルダに必要なItemsを直接作成し、同じ承認済みplan・入力fingerprintを使って
Lakehouse/Notebook → KQL/Pipeline → 品質処理/Gold → Model → Ontology/Agentの
依存順に一括実行します。これは複数APIをまとめた一連の手順であり、1回のHTTP呼び出しや
ワークスペース全体の単一トランザクションではありません。

正式に必要な静的consumer Ontologyとmanaged Graphは、一時評価物ではありません。
generation2の主Ontologyとは用途を明示して、正式Agentと同じ指定フォルダへ置きます。
互換性helperの配置先は既定で承認済みrootです。`--temp-folder-id`は明示的な評価時だけの
旧互換オプションで、本デプロイでは使用しません。

修正版の新規構成は[`fresh_grounded_profile.py`](../../../tools/data-agent/fresh_grounded_profile.py)
で、実サービスから取得した4ソースと、独立に検証した6 viewsのschemaを使って生成します。
最終段の`standard-contract-restoration`が、標準10問の回答契約（年なしの8月＝2026年8月の観測、
3ソースの分担、受入/在住、人気の両指標、Ontologyの所属COUNT、合算拒否、数値の忠実性）を復元します。
このcompilerは書き込みを行いません。呼び出し側が実ソース、native例検証、staging/publicationの
読み戻しと回答評価を完了させます。未検証のschema IDを作ったり、旧環境のItem IDを流用したりしません。

評価用の比較AgentやTempを作った場合は、採用した構成を正式Agentへ反映し、
依存・参照・実回答を確認した後に削除します。必要なOntologyごとTempを消して
正式Agentの参照を切ることはしません。既存CSVの再投入や完了済みNotebookの再実行も行いません。

## English

The course and current distributed Notebooks are **3.0.0**. The unchanged CSV
contract and compatible processing baseline intentionally retain their2.7
identifiers. A source-artifact manifest binds the actual files, embedded packages,
profiles, models and paired Word/HTML; changing only an outer label is insufficient.

Production uses the approved target folder directly, not Temp. Required consumer
Ontology/Graph resources remain explicit production dependencies. Temporary
comparison Agents and evaluation folders are removed after the adopted Agent's
references and behavior are verified. Historical records and release assets are
not rewritten, and file-integrity checks are not AI-answer acceptance.

The 2026-10-07 deployment restored the standard answer contracts in the formal
Agent: the protected ten/84 moved from 36/84 and 34/84 to 74/84 and 73/84 (ceiling
77; T10 is blocked natively and never bypassed), and a pre-registered author-written
holdout returned 11 PASS /1 FAIL. See the dated addendum for every configuration.
The same-day follow-up completed the remaining deviations where an API path exists
(service-verified views; the optional Power BI report, now 22 items), documented
UI-only hand-offs, added the public regression gate and runbook tools, and kept this
configuration because candidates R7 and R8 missed the pre-recorded adoption rule.
