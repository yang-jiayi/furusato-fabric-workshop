# 現行教材の整合性確認 / Current material verification — 2026-10-10

参加者教材24章・付録5件、可搬チューニングprofile、Notebook01–05、Word・日英HTML・ZIPを同じソースでそろえました。
精度校正と資料校正の詳しい手順は[校正手順](../tuning-20261010/calibration-and-proofreading.md)、
実回答の改善と残件は[実測レポート](../tuning-20261010/README.md)をご確認ください。

| 項目 | 確認結果 |
|---|---|
| ソース固定 | `a93899fc4209976aee77f79dcf1c1288415ff7ac`、345ファイルすべての実SHAとGit blobが一致 |
| Artifact manifest | `efaa2e4daf3537c5c501d6538d023dd0414317ba396513155e92091d847c3cc0`、参加者Word・HTMLとZIPのsourceに同じmanifestを結合 |
| 標準構成 | Ontology 1件・Data Agent 1件。Lakehouse、KQL Database、同じGen2 Ontology、直接のSemantic Model |
| 可搬profile | `measured-contract-20261009`。実native選択、独立SQL metadata、Ontology metadata、TMDLでDraft生成を検証。新しい導入先の公開・回答品質は別検証 |
| データ・モデル | CSV 11ファイルのbytes保持。Notebook01/05の処理保持。金額列を表示し、既存10メジャーの式を保持 |
| 文書検査 | 152 PASS / 0 FAIL。構造、目次、画像、日英切替、検索、保存済み進捗、図の拡大、390/768/1440幅、日英印刷を検証 |
| Word | 29章・付録へのリンク目次、動的Office fieldsと古いページ番号なし、Noto CJKフォント指定。Microsoft Wordによるページ割り・描画は未検証 |
| LibreOffice描画 | 99ページ、1,877本文・表段落すべて保持。空白・ページ外文字・文字化け0件。10ページを目視確認。485表行のうち285行を固有テキストで追跡し、ページ跨ぎ候補0件 |
| 配布ZIP | 全357 entriesとSHA-256を照合。参加者Word/HTML、Notebook/CSV/モデル/profile、別冊Word/HTMLと校正手順を同梱 |
| ユニット検査 | runtime 103、data-agent 335、文書 407が成功。文書検査の未実行・skipは0 |

## 実回答の改善と確認範囲

同じ219条件で、baseline **111/219（50.68%）**からR8 **162/219（73.97%）**へ、**+23.29ポイント**改善しました。
元の質問・採点基準・失敗記録は維持しています。baselineには取得条件の差があり、純粋なチューニングだけの因果効果は分離できません。
R9のSQL修正は別の限定19条件がPASS、R11の既存メジャー定義・フィルター説明は別の限定4条件がPASSでした。
**最新R9/R10/R11を合わせた全51質問の再評価は未実施**です。未使用の異なる問題セットも同一問題の改善率に合算しません。

クラウドの直近観測は2026-10-09（配置元ソース `fa103f0ff99d6259b9a208c924320908ae4a1b66`）です。
標準18 Items、Ontology 1件、Agent 1件、公開profile R11を保持しています。
今回の資料整合性作業ではAgent質問、Notebook実行、データ取込み、クラウド再配置を行っていません。
新しいソースmanifestが過去の実行記録を置き換えることはありません。

未解決事項は、AgentのGen2 Ontology consumerでのunsupported API version、Agent native DAX schemaへの金額列の露出、
native Metrics／Time SeriesのbindingとManage graphのUI確認です。Report画面表示とActivator自動配送も未検証です。
直接Graph/GQL・DAXの成功とAgent経由の成功は別に扱います。資料検査やmainへのマージで、これらを合格へ変更しません。

[機械可読の検証結果](verification.json)・[配布SHA-256](SHA256SUMS.txt)・[現行教材](README.md)
に実hashと検査範囲を記録しています。
旧版の同名レポートは[固定コミット](https://github.com/yang-jiayi/furusato-fabric-workshop/tree/fa103f0ff99d6259b9a208c924320908ae4a1b66/docs/v3.0.0/current)
から参照できます。現在のレポートのR8/R11は2026-10-09の測定phaseです。

## English

The 24-chapter/five-appendix participant course, portable measured profile, five Notebooks,
Word, bilingual HTML and ZIP share the fixed source above. All 345 source hashes match
Git blobs. The pair passed 152 local checks with zero failures; the ZIP entries and hashes also match.
The standard path uses one Ontology and one Data Agent, preserving all 11 CSV files and the ten measure expressions.

Word contains persistent chapter links and explicit Noto CJK fonts. LibreOffice rendered 99 pages,
retaining all 1,877 paragraph/cell texts with no blank pages or out-of-page/replacement characters;
ten pages were visually inspected. Row locality was checked for 285 of 485 uniquely identifiable table rows.
Microsoft Word pagination/rendering remains unverified.

The matched 219-condition content comparison improved from 50.68% to 73.97% (+23.29 percentage points).
Later SQL and measure-definition checks are targeted checks, and the latest combined profile has not had
a full 51-question rerun. Baseline capture settings differed, so a pure causal tuning effect is not claimed.
Native failures, unchanged graders and unverified features are retained separately from supplemental content review.
The live deployment observation dates to 2026-10-09; this material sync made no cloud writes or new Agent calls.
See the dated report and machine-readable verification for remaining platform limitations.
