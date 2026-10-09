# Furusato Workshop 3.0.0 — 現行教材 / Current workshop

2026-10-10整合版。教材の手順、可搬profile、Notebookの同梱資産、Word・日英HTML・ZIPを同じソースでそろえます。

[参加者用 Word](guide/Fabric_IQ_Ontology_Workshop_Furusato_Participant_v3.0.0.docx) ·
[参加者用 日英HTML](guide/furusato-workshop-v3-0-0-complete.html) ·
[Notebook・CSV・モデルを含むZIP](Furusato_Workshop_v3.0.0_current-20261010.zip) ·
[Artifact-set](artifact-set.json) · [検証結果](deployment-verification.md) ·
[検証JSON](verification.json) · [SHA-256](SHA256SUMS.txt) ·
[実測した改善・残件](../tuning-20261010/README.md) ·
[精度校正と資料校正の手順](../tuning-20261010/calibration-and-proofreading.md)

標準構成は**Ontology 1件・Data Agent 1件**です。必要な4ソースはLakehouse、KQL Database、
この同じGen2 Ontology、直接のSemantic Modelです。consumerのAPI version unsupportedや
native Metrics／Time Seriesの未完了を、別のOntologyを作って置き換えません。

同じ219条件の実回答比較で、回答内容の一致は50.68%から73.97%へ改善しました。
SQL修正の19条件、既存メジャーのフィルター説明の4条件は別の限定検証です。
最新profileで全51質問を再評価していません。実測範囲、取得条件の差、native失敗と
未確認事項は[実測資料](../tuning-20261010/README.md)に残します。

## 版とソースの対応

| 対象 | 正本と役割 |
|---|---|
| 教材・Notebook01–05 | [`WORKSHOP_VERSION`](../../../WORKSHOP_VERSION) = 3.0.0 |
| 配置パス | [`workshop/v3.0.0-preview`](../../../workshop/v3.0.0-preview/README-runtime.md)、互換パス |
| 版の対応表 | [`edition.json`](../../../workshop/v3.0.0-preview/edition.json)、標準Ontology数1 |
| CSV | 2.7.0-realistic.1、11ファイルの値・行数・hashを保持 |
| 処理コード基線 | 2.7.0、Notebook01/05の処理を維持。完了済み処理を再実行しない |
| 現行profile | [`measured-contract-20261009`](../../../workshop/v3.0.0-preview/data-agent/candidates/measured-contract-20261009/README.md) |
| モデル | 金額列を表示。既存10メジャーの式は維持。Agent native schemaへの露出は別検証 |
| Word・HTML | 共有原稿、同じartifact-set SHA、HTMLに対応するWordの実SHA |

profile compilerは、実際のnative選択要素、独立SQL metadata、公開modelのTMDLとOntology
metadataからDraftだけを生成します。欠けたschema IDを作らず、1区画10,000 UTF-16単位を
超える指示を拒否します。呼び出し側はサービスの回答例検証、staging、公開読戻しと実回答評価を行います。

## 再生成と校正

まずソースを固定し、可搬資産とNotebookの同梱packageを生成します。

```bash
python -B tools/provisioning/build_preview30.py
python -B -m unittest discover -s tools/provisioning -p 'test_preview30*.py'
python -B tools/provisioning/v3_artifacts.py --out workshop/v3.0.0-preview/provisioning/artifact-set.json
```

Word・HTMLの生成先はcheckout外の新しい私有ディレクトリとします。既存版・過去の評価を上書きしません。
`$Approval`には、使用するpublic projectionと保持する元76/8 runの実hashに結び付く文書配布承認を
指定します。これは新しい回答品質の合格証明ではありません。今回の文書配布・main統合はユーザーの指示によります。

```powershell
$Manifest = "workshop/v3.0.0-preview/provisioning/artifact-set.json"
$Options = @("--release-profile", "v3.0.0", "--participant-edition", "--word-navigation", "headings",
             "--release-approval", $Approval, "--artifact-manifest", $Manifest)
python -B tools/docs/build_preview30.py --out "$Stage/pair" --review "$Stage/build" @Options
python -B tools/docs/validate_preview30.py --pair "$Stage/pair" --review "$Stage/checks" `
  --interactions --print-html @Options
python -B tools/docs/package_preview30.py --pair "$Stage/pair" `
  --validation "$Stage/checks/validation.json" --out "$Stage/package" @Options
```

Linuxではvalidateに `--browser-executable /usr/bin/chromium` など実際のbrowser pathを指定できます。
Wordは29章・付録への内部リンク目次を持ち、Officeの動的fieldと古いページ番号を含みません。
この生成方法には Noto Sans CJK JP と Noto Sans Mono CJK JP を用意します。本文・表とコードに
それぞれ明示して、日本語の字体の欠落を防ぎます。
Microsoft Wordによるページ割り検証は行っていません。ZIPの `DOCUMENT_VALIDATION.json` は
構造・日英ブラウザー検査とWord未確認の範囲を明記します。
既定の `--word-navigation fields` と厳密な `--require-acceptance` の検査は別に維持しています。
LibreOfficeによるPDF確認は追加の描画観測で、Microsoft Wordの検証とは区別します。

各章は目的、操作、完了確認、参照表、参考資料で構成します。精度校正・資料校正は19章、
単一Ontologyの配置は24章にあります。参加者用パッケージに私有の実回答・trace・認証情報を含めません。
元のタグ・日付付き過去成果物は保持します。
[前回の整合版（固定コミット）](https://github.com/yang-jiayi/furusato-fabric-workshop/tree/fa103f0ff99d6259b9a208c924320908ae4a1b66/docs/v3.0.0/current)
は新しい結果と分けて参照します。

## English

The 2026-10-10 current materials use one Ontology and one Data Agent. The portable
measured profile, sealed Notebook inputs and paired participant guides share the
same source contracts. The matched measured improvement is +23.29 percentage
points; later targeted checks remain separate from the earlier full campaign.
The latest combined profile has not undergone a full 51-question rerun.

The explicit participant-only heading-navigation export contains real internal
chapter links and no dynamic Office fields or cached page numbers. Structural,
bilingual print/browser checks and optional LibreOffice rendering are distinguished
from Microsoft Word pagination. Default full Word/acceptance gates remain intact.
See the verification JSON for actual artifact hashes and completed checks.
