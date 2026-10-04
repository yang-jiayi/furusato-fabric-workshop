# Furusato Workshop 3.0.0 — 現行成果物の整合性

このディレクトリは現行mainの整合版用です。元の`v3.0.0`タグ・配布物と日付付き過去評価は
変更せず保持します。教材版、データ仕様、FabricのgenerationやAPI versionを混同しません。

## 版の正本

| 成果物・識別子 | 正本と扱い |
|---|---|
| 教材・Notebook01–05 | [`WORKSHOP_VERSION`](../../../WORKSHOP_VERSION) = **3.0.0**。見出し・metadata・Notebook01の配布版表示を一致させます |
| 配置用ディレクトリ | [`workshop/v3.0.0-preview`](../../../workshop/v3.0.0-preview/README-runtime.md)。技術的パスは既存互換のため維持 |
| 版の対応表 | [`edition.json`](../../../workshop/v3.0.0-preview/edition.json) |
| CSV | [`data`](../../../workshop/v3.0.0-preview/data)。`2.7.0-realistic.1`の値・行数・hashを保持。版表示のために再生成しません |
| 再利用する処理コード | `2.7.0`基線。Notebook01/05の処理ロジックと内部publication keyは維持 |
| 修正版Agent | [`time-layer-isolation`](../../../workshop/v3.0.0-preview/data-agent/candidates/time-layer-isolation/README.md)。6 SQL views・全体/ソース指示・SQL15/KQL6例を同じ入力セットに含めます |
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
