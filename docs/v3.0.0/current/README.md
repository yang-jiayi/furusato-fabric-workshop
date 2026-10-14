# Furusato Workshop 3.0.0 — 現行教材 / Current workshop

2026-10-15整合版。再配置した構成と採用済み指示を、Notebook・可搬profile・参加者Word・日英HTMLへ反映しました。

[参加者用Word](guide/Fabric_IQ_Ontology_Workshop_Furusato_Participant_v3.0.0.docx) ·
[参加者用日英HTML](guide/furusato-workshop-v3-0-0-complete.html) ·
[Notebook・CSV・モデルを含むZIP](Furusato_Workshop_v3.0.0_current-20261015.zip) ·
[Artifact-set](artifact-set.json) · [検証結果](deployment-verification.md) ·
[検証JSON](verification.json) · [SHA-256](SHA256SUMS.txt) ·
[作業・実測レポート](../tuning-20261015/README.md) ·
[精度校正・資料校正](../tuning-20261015/calibration-and-proofreading.md)

標準構成は**Ontology 1件・Data Agent 1件**です。通常ソースはLakehouse・KQL Database・Semantic Modelの3件で、同じOntologyを独立したcontextとして登録します。
Ontology consumerのSchemaUnavailableを別のOntologyの追加で置き換えません。

同じ条件で対応付けた281条件の補助条件充足率は189/281（67.26%）から217/281（77.22%）へ9.96ポイント上がりました。既定の確認質問分岐の9条件だけを両側から除外しています。厳密な受理1件→2件はすべて確認質問で、ソース照会を伴う完成回答の厳密な受理は両方0件です。
回答内容の補助条件、厳密なnative判定、確認できたソース実行を分けて示します。固定条件を満たしても追加説明が誤る例があり、全文章の正確性を保証しません。
3ファイルの自動取り込みと公式埋め込みによるReport表示は検証済みです。Time Seriesは保存済みバインドと実行証拠を分け、native Metrics0件とOntology consumerの制約を保持しています。

## 版とソースの対応

| 対象 | 正本と役割 |
|---|---|
| 教材・Notebook01–05 | [`WORKSHOP_VERSION`](../../../WORKSHOP_VERSION) = 3.0.0 |
| 配置パス | [`workshop/v3.0.0-preview`](../../../workshop/v3.0.0-preview/README-runtime.md)、互換パス |
| 版の対応表 | [`edition.json`](../../../workshop/v3.0.0-preview/edition.json)、標準Ontology数1 |
| CSV | 2.7.0-realistic.1、11ファイルの値・行数・hashを保持 |
| 処理コード基線 | 2.7.0、Notebook01/05の処理を維持。完了済み処理を再実行しない |
| 現行profile | [`measured-contract-20261015`](../../../workshop/v3.0.0-preview/data-agent/candidates/measured-contract-20261015/README.md) |
| モデル | 金額列を表示。既存10メジャーの式は維持。Agent native schemaへの露出は別検証 |
| Word・HTML | 共有原稿、同じartifact-set SHA、HTMLに対応するWordの実SHA |

profile compilerは、実際のnative選択要素、独立SQL metadata、公開modelのTMDLとOntology
metadataからDraftだけを生成します。欠けたschema IDを作らず、1区画10,000 UTF-16単位を
超える指示を拒否します。呼び出し側はサービスの回答例検証、staging、公開読戻しと実回答評価を行います。

参加者版は構造・日英ブラウザー検査152件が成功（FAIL 0）し、LibreOfficeで描画したWord92ページ、Chromiumで印刷した日本語100ページ・英語102ページの全294ページを実画像で確認しました。Word本文・表の可視テキスト1,878断片のうち単純連結診断で2断片が未一致となりましたが、いずれもページ境界に挟まるヘッダー・フッターによるもので、実画像と実PDFテキストで全文の保持を確認しました。

一部の元UI画像には周辺操作部の切れや密なGraphラベルの重なりが残りますが、手順本文・キャプション・必要な証拠は読めます。余白の多い参照ページや表見出しから次ページへの継続も記録しました。fieldを含まない目次方式のためページ番号はなく、フッターの「Page」だけが残る点は体裁上の制約です。29章・付録への内部リンクを利用できます。

ZIPの383エントリーをCRC・SHA-256で全件確認し、371ソース成果物を固定ソースcommitのGit blobと照合しました。Notebook01–05・CSV・モデル・採用profile・校正手順・実測レポートを同梱します。 [文書検査](DOCUMENT_VALIDATION.json)・[全ページ確認](participant-render-validation.json)。

## 再生成と校正

まずソースを固定し、可搬資産とNotebookの同梱packageを生成します。

```bash
python -B tools/provisioning/build_preview30.py
python -B -m unittest discover -s tools/provisioning -p 'test_preview30*.py'
python -B tools/provisioning/v3_artifacts.py --out workshop/v3.0.0-preview/provisioning/artifact-set.json
```

Word・HTMLの生成先はcheckout外の新しい私有ディレクトリとします。既存版・過去の評価を上書きしません。
`$Approval`には、使用するpublic projectionと保持する元76/8 runの実hashに結び付く文書配布承認を
指定します。文書identityの `provenance-native-ui-20261001` と76 PASS／8 FAILは保持した過去runの記録で、現在の回答評価ではありません。現在の281条件の比較は別の日付付き2026-10-15レポートを参照します。これは新しい回答品質の合格証明ではありません。今回の文書配布・main統合はユーザーの指示によります。

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
browserがfile URLを開けない場合は `--browser-transport loopback` を追加します。
選んだHTMLだけを一時的なローカルHTTPで配信し、それ以外の通信は遮断して検査します。
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
[前回の整合版（固定コミット）](https://github.com/yang-jiayi/furusato-fabric-workshop/tree/f255989351b418fe99f9ee8ef3d562233adfd9f7/docs/v3.0.0/current)
は新しい結果と分けて参照します。

## English

The 2026-10-15 current materials describe 18 deployed items, one Ontology and one Data Agent, with three ordinary sources plus separate context for the same Ontology. The adopted portable profile is `measured-contract-20261015`.
Supplemental condition fulfillment on 281 matched conditions rose from 189/281 (67.26%) to 217/281 (77.22%), a 9.96 percentage-point difference. Only nine predeclared clarification-branch conditions were excluded symmetrically. Strict acceptance changed from one to two clarification responses; neither phase had a strictly accepted completed source-query answer.
Supplemental condition fulfillment, strict native acceptance and verified source execution remain separate. Additional prose can be wrong outside the fixed conditions.
Automatic ingestion of three files and official Report rendering were verified; Ontology consumption, native Time Series evidence and Metrics retain explicit limits.

The participant edition passed 152 structure and bilingual browser checks with zero failures. Every one of the 294 actual page images was inspected: 92 LibreOffice Word pages, 100 Japanese Chromium print pages and 102 English print pages. Of 1,878 visible Word paragraph/table-cell text fragments, two did not match the raw concatenated PDF text because repeated headers/footers interrupted paragraphs across page boundaries; actual images and PDF text confirmed that both complete paragraphs were retained.

Some retained UI screenshots show cropped peripheral controls or overlapping dense graph labels; the instructions, captions and required evidence remain readable. Sparse reference pages and table continuations are documented. The field-free navigation edition intentionally has no page numbers and retains a cosmetic bare “Page” footer label; 29 chapter/appendix links provide navigation.

All 383 ZIP entries were checked by CRC and SHA-256, and all 371 source artifacts matched Git blobs at the pinned source commit. The package includes Notebooks01–05, CSV data, models, the adopted profile, calibration procedure and measured report. See [document checks](DOCUMENT_VALIDATION.json) and [all-page review](participant-render-validation.json).
The package retains the historical document identity `provenance-native-ui-20261001` (76 PASS / 8 FAIL); current answer evaluation is the separate dated 2026-10-15 report with 281 matched conditions. Microsoft Word pagination and rendering remain unverified. The fixed previous release is retained independently.
