# measured-contract-20261015

このプロファイルは、Data Agent の global、Lakehouse SQL、Semantic Model の指示を更新した版です。実測評価の結果と未解消の制約は [2026-10-15 作業レポート](../../../../../docs/v3.0.0/tuning-20261015/README.md)、再評価と資料校正の手順は [校正手順](../../../../../docs/v3.0.0/tuning-20261015/calibration-and-proofreading.md) を参照してください。指示だけで回答精度やネイティブ Ontology 接続の成功を保証するものではありません。

- 寄付明細では、寄付者の在住県・受入自治体の県・業者の県を別の役割として ID と名前で示します。カタログ登録を製造・発送・履行と同一視しません。
- 暦月は要求されたタイムゾーンで開始日以上・翌月開始日未満の区間にし、時刻の表示と抽出範囲を区別します。JST と UTC が混在する回答には一律の UTC 表記を付けません。
- 取得した必要項目、件数・金額、ソースと粒度を省略せず、異なる母集団を合算できないときはその境界を説明します。Semantic Model の列・メジャー契約は、そのソースの指示に配置します。

KQL 指示、9 件の KQL 例、選択契約、ソース説明、SQL スキーマ照合用クエリは旧版と同一です。旧版 [measured-contract-20261009](../measured-contract-20261009/README.md) の入力と過去の評価は維持しています。`profile-manifest.json` は 8 個のコンパイラ入力を SHA-256 で固定します。各指示は 10,000 UTF16 単位以内です。

`tools/data-agent/measured_contract_profile.py` は、この版を既定とし、`--profile measured-contract-20261009` で旧版も明示的に選べます。現在の配置から取得した定義・SQL 列・Semantic Model・Ontology メタデータを入力し、既存オブジェクト、選択列、メジャーと照合してローカル Draft を生成します。実データや定義、認証情報、評価トレースは Git に保存しません。適用・公開・読み戻し・評価は別の実操作です。

ネイティブ Gen2 定義では、3 個の datasource と 1 個の主 Ontology コンテキストを保持します。global と 3 ソースの対応する指示フィールドだけに設定し、旧 Ontology 指示を global に移したり、未対応のフィールドを追加したりしません。`ontology-instructions.txt` は旧形式との互換性のため保持し、ネイティブ Ontology コンテキストには挿入しません。新しい Ontology は増やしません。物理的な選択は 17 SQL オブジェクト・143 列、既存のモデルメジャーは 10 件です。実際の接続可否と実行証拠はレポートを確認してください。

## 参加者による再現

参加者用Word／日英HTMLの第17章に、6つのSQLビュー、選択する17オブジェクト・143列、4つの指示全文、9件のKQL例、公開と読み戻しを収録しています。第19章と付録Cには、公開29問を使う49枠・290条件の評価と記録方法があります。教材と同じ版のZIPを使い、過去の非公開問題や過去の得点を新しい環境の結果として扱いません。

同梱の [`participant_profile.py`](../../../../../tools/data-agent/participant_profile.py) は、本人認証で既存Agentの定義と実スキーマを取得し、固定profileを準備・適用・公開・照合するための補助ツールです。`prepare` と `verify` は読み取り専用、`apply` と `publish` はそれぞれ `--apply` が必要です。[コマンド仕様と復旧](../../../../../tools/data-agent/participant-profile-README.md)に実行条件を記載しています。独自の指示変更を比較するときにこの固定profile用ツールを再実行すると、採用済み指示に戻ります。独自の変更は参加者用第19章の編集・公開・再評価の手順で扱います。

## English

This version updates the supported global, Lakehouse SQL and Semantic Model instructions. Consult the [2026-10-15 work report](../../../../../docs/v3.0.0/tuning-20261015/README.md) for measured results and unresolved limitations, and the [calibration procedure](../../../../../docs/v3.0.0/tuning-20261015/calibration-and-proofreading.md) for reevaluation and document checks. Instructions alone do not guarantee answer accuracy or native Ontology connectivity.

The changes separate resident, recipient and supplier prefecture roles; preserve requested IDs and names; distinguish catalog registration from manufacturing or fulfillment; use half-open calendar-month ranges in the requested timezone; and avoid applying an all-UTC footer to mixed-timezone answers. Required fetched fields, counts, amounts, source and grain must remain visible, and incompatible populations must remain separate. The Semantic Model schema contract resides in that source's instructions.

KQL instructions, nine KQL examples, source selections, descriptions and the SQL schema-inventory query retain their historical bytes. The [2026-10-09 profile](../measured-contract-20261009/README.md) and its evaluation remain available. The manifest binds all eight compiler inputs, and each instruction is limited to 10,000 UTF16 units.

The compiler defaults to this profile and supports explicit historical selection with `--profile measured-contract-20261009`. It checks actual deployment metadata and produces a local Draft; applying, publishing, reading back and evaluating remain separate operations. Keep actual definitions, credentials and traces outside Git. Native Gen2 retains three datasources and one main Ontology context, without inventing legacy fields or another ontology. Legacy Ontology instructions remain available for historical serialization but are not inserted into native context or global instructions. The selection contract covers 17 SQL objects, 143 columns and the ten existing model measures; availability and execution evidence must be assessed separately.

The participant Word/HTML includes the complete configuration procedure in Chapter 17 and the reproducible public evaluation in Chapter 19 / Appendix C. The bundled participant helper prepares, applies, publishes and verifies this fixed profile; do not use it to publish a customized tuning candidate because it restores the fixed instruction texts. See the [command reference](../../../../../tools/data-agent/participant-profile-README.md).
