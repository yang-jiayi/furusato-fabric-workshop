# tools/docs — Office 配布物の build と validation / Office deliverable build and validation

[日本語](#日本語) | [English](#english)

---

## 日本語

内部編集用の Office 成果物 3 点と、選択式の公開文書モードに対する、決定的な builder と validator です。
数値、名称、パス、パラメーター既定値、ハッシュ、指示文、クエリ断片のすべてを、
同梱された v2.7.0 の runtime から build 時に読み取ります。手で書き写す値はありません。
runtime が変わりドキュメントが乖離する状況になった場合、build は古い成果物を
出力せずに失敗します。

Word と HTML の表示テキストでは、括弧を半角の `(` / `)` に統一します。
`furusato_docs/typography.py` を生成境界で共用し、本文・表・見出し・代替テキストと
HTML の動的な日英 UI に適用します。元の runtime、評価問題・条件、URL の接続先、
画像の画素は変更しません。内容検証は括弧の表示差だけを正規化し、
生成物に全角括弧が残っている場合は別の typography ゲートで失敗します。

### 最新版の文書ペア

release edition は `unified-20260914` です。現在の文書配布対象は次の 2 点だけです。
検証済みペアをこの名前で配置しています。

現在のペアは profile revision 13 を反映した Word と対応 HTML です。
照会可能な質問への言い直し・同意待ち・訂正時の再確認・取消を同期しています。
指示による動作と強制制御を区別し、出典・KQL・CI・安全な拒否の確認も保持します。
返礼品の選択と受領、導出順位と保存済み順位、実際の返却列・出典と説明用ラベルを区別します。

| 文書 | 生成元 |
|---|---|
| [参加者 Word](../../docs/Fabric_IQ_Ontology_Workshop_Furusato_Participant_v2.7.0_unified-20260914.docx) | `furusato_docs/participant_guide.py`（＋ `guide_content`、`guide_handson`、`guide_agent`、`guide_unified`） |
| [対応する日英 HTML](../../docs/furusato-workshop-v2-7-0-complete_unified-20260914.html) | `tools/html`（同じ内容モデル） |

別冊の検証票 Word と処理仕様 XLSX は現行ダウンロードではありません。内部編集用の全 Office
build は、別の新しい外部 PRIVATE ステージングへ named edition を明示して生成する場合に限り
継続します。参加者 Word に加え、`validation_doc.py` と `workbook.py` が同じ
`_redeploy-20260913` 接尾辞の内部補助資料を生成します。これらを HEAD の公開一覧へ戻しません。

`docs/data-validation-checklist.md` は手で保守しますが、同じ runtime の値に対して
`validate_docs.py` が検証します。

### 公開文書は Word + HTML の 2 ファイルだけ

公開用には `--public-documents-only --edition unified-20260914 --out <外部の非公開ステージング>` を
build / validation の両方へ指定します。PowerShell は
`-PublicDocumentsOnly -Edition <版名> -OutputDirectory <外部パス>` です。
このモードは参加者 Word だけを生成・検証し、別冊 Word と XLSX の生成・COM 処理・検査を行いません。
全 19 章・付録 A〜E、元の 10 問／84 要件、全パラメーターを保持し、記録方法と仕様表はガイド内で案内します。
別冊は任意の内部補助資料です。HTML も同じフラグ・edition・出力先で後から生成します。

非空の edition と、リポジトリ外の新しい出力先が必須です。旧 HEAD の Office/HTML 8 点は
非公開にバイト一致で退避し、新ペアの検証後にその 8 点だけを HEAD から除きました。
原本は非公開アーカイブ／履歴に保持し、Notebook・データ・コード・図版・style 資産は残します。
既存ファイルや想定外のファイルがあれば停止し、清掃しません。`--skip-workbook` との併用は不可です。
公開モードの validator は参加者本文・OOXML・図版・キャプチャ品質を検査する読み取り専用の文書検査であり、
リポジトリ全体の配布・履歴・runtime の reseal 検査とは別です。既定モードの検査は従来どおり残ります。
公開 validator / exporter は外部のペア用ディレクトリを使います。`docs` は assets と checklist を
含むため直接渡せません。配置後の検証でも、正確な 2 ファイルだけを新しい外部ディレクトリへ
コピーし、原本のコピー前後とコピー先のハッシュ一致を証明します。パス検査や選択範囲を緩めません。

[公開ペアの export 手順](../publication/README.md)で、独立した新規ディレクトリへ
Word と HTML だけを複製し、必要なら SHA-256 manifest をペアの**外**へ保存します。
この配布版は公開用の新規履歴を使い、旧 Private の履歴や証跡は取り込みません。
文書 export 自体は GitHub の公開範囲・履歴・hosting の変更を実施・承認しません。
旧履歴を公開側へ merge／push せず、[SECURITY.md](../../SECURITY.md) に従ってください。
構成・結果・画面写真のレビューが凍結するまで、新版の完全なバイナリ build は実行しないでください。
配布 Word／HTML は主 Agent 1 件、完全な教材用 Ontology、SQL/KQL ヘルパーと同じ Agent の
Code Interpreter 演習を同期した `unified-20260914` です。従来 Core の入力は保持しています。
作業ログ・実環境のバックアップ・詳細な実行記録は配布リポジトリの外で管理します。
Data Agent の品質合格はデプロイ・文書の準備完了と別であり、
評価履歴は受講者向け資料に含めません。[Data Agent の回答確認](../../docs/single-agent-workshop.md)を参照してください。

#### 構成変更時の画面写真の受け渡し

未加工原本は非公開の `$PrivateDocuments\captures\originals`、レビュー用コピーは
`$PrivateDocuments\captures\reviewed`、レビュー記録は
`$PrivateDocuments\captures\review.json` に分け、文書ペアへ入れません。
現在の `style-carrier.zip` と `docs/assets` は、別途承認されるまで変更しません。
候補の設定・画像は候補と明示し、Core の説明・指示を置き換える承認と解釈しません。
統合版では有効な既存画像を再利用し、古い指示が写る `13-12`・`13-33` は掲載しません。
原本は保持します。`assets/unified-ui-captures.json` は `16-30`・`18-30`・`17-40` の
実UI原本ハッシュと撮影時の構成を保持します。古い指示が見える `16-30`・`18-30` も現行版には
掲載せず、`17-40` だけを操作例として使います。CI指示部分のハッシュとPreview／CI設定の
一致、旧設定画像が本文にないことを検査し、過去の画像を新構成・新評価の証拠にしません。
現行設定の画像を加えるには正常な本人認証で実画面を撮影し、本文・台帳・検査を再レビューします。
`make_style_carrier.py` は台帳の3枚も保持します。古いstyled DOCXにそれらがない場合は、
欠落したまま上書きせず停止するため、現行carrierに対する `--prune` を使います。

| 内容 | レビュー後の配置先 |
|---|---|
| 修正したグローバル指示 | 第 16.3 節の全文とハッシュ。旧 `16-30` は非掲載、legacy 版は `13-12`。新しい実画面の承認後だけ差し替える |
| ソース説明・Lakehouse / Eventhouse のソース指示 | 第 16.4 / 16.5 節。新しいキャプチャキーと掲載位置は承認時に決める。旧画像や架空画像で穴埋めしない |
| ソース選択・runtime・公開状態 | 第 16.2 / 16.7 / 18 章。旧 `18-30` は非掲載。現在の設定は本文の手順で実環境から読み戻す |
| hydration または回答の実行証跡 | 第 17 章。`17-40` はCI操作例のみ。`17-1` や過去の回答を新しい評価の成功証拠として流用しない |

レビュー記録には構成版と指示のハッシュ、撮影日時、原本・加工版のハッシュ、切り抜き領域、
伏せた情報の種類、本文との一致、承認状態を残します。アカウント・URL・内部 ID は公開用コピーで
切り抜きまたは伏せ字にし、その加工をキャプション等で明記します。関連する元の UI 内容は残します。
回答原本・判定・失敗を修正して PASS にしません。Word と HTML は同じ承認済み画像を使い、
本文・対訳・キャプション・ハッシュをまとめて再検証します。画面未取得は未取得のまま記録します。

### 前提

- Python 3 と `tools/docs/requirements.txt`（`python-docx`、`openpyxl`、`Pillow`）。
- Word の field / TOC 更新と Excel の再計算には `pywin32` と Office が必要ですが、
  どちらも任意です。`--render` には `PyMuPDF` が必要で、これも任意です。
- 同梱された `workshop/v2.7.0` runtime、`docs/assets/v2.7.0`、
  `tools/docs/assets/style-carrier.zip`。

### 構成

```
tools/docs/
  build_docs.py            エントリポイント: 3 つの配布物をすべて build する
  validate_docs.py         エントリポイント: 検証する（FAIL があれば exit 1）
  make_style_carrier.py    assets/style-carrier.zip を再生成する
  Build-Docs.ps1           build + validate の PowerShell ラッパー
  requirements.txt
  assets/style-carrier.zip ブランド適用済み OOXML シェルパートと再利用する画面写真
  furusato_docs/
    context.py             v2.7.0 runtime を唯一の正本として読み込む
    facts.py               同梱 CSV から Test 10 の期待値を再計算する
    parameters.py          Notebook の全パラメーターに対する参加者向け説明文
    tests10.py             hold-out した 10 問の口語・意地悪テスト
    oox.py                 style carrier、パッケージメタデータ、Purview ラベル処理
    docx_kit.py            Word 用の共通 Fabric IQ ビジュアル言語
    guide_content.py       第 1〜4 章のコンテンツモデル（概念と根拠）
    guide_handson.py       第 6〜15 章（ハンズオン）
    guide_agent.py         第 16〜19 章と付録 A〜E
    participant_guide.py   参加者ガイドを組み立てる
    validation_doc.py      Test 10 の記録票を組み立てる
    workbook.py            処理仕様ワークブックを組み立てる
    validators.py          再利用可能な OOXML / アクセシビリティ / 内容 validator
    quality.py             品質ゲート: 内容、OOXML レイアウト、ワークブックの印刷設定
    render_audit.py        Word で全ページを描画して結果を検査する
    word_refresh.py        任意: Word COM による field、TOC、ページ数の更新
    excel_refresh.py       任意: Excel COM による数式の再計算
```

### 正本の所在

| 値 | 読み取り元 |
|---|---|
| バージョン | `VERSION` |
| 件数、金額、観測窓、チェックサム | `workshop/v2.7.0/data/dataset-manifest.json`、`SHA256SUMS.txt`、同梱 CSV |
| Entity / Property / Relationship / binding の定義 | `workshop/v2.7.0/ontology/ontology-full-definition-template.json` |
| シノニムと time-series Property | `workshop/v2.7.0/ontology/ontology-semantic-metadata.json` |
| アイテム命名と provisioning 契約 | `workshop/v2.7.0/participant-workspace-contract.json` |
| Notebook のハッシュ、cell 一覧、パラメーター既定値 | `workshop/v2.7.0/notebooks/*.ipynb` |
| KQL オブジェクトと検証クエリ | `workshop/v2.7.0/kql/Furusato_Eventhouse_Setup_v2.7.0.kql` |
| Pipeline のパラメーターとファイル名の式 | `workshop/v2.7.0/provisioning/bundle/data-pipeline/pipeline-content.json` |
| Data Agent のグローバル指示 | `workshop/v2.7.0/data-agent/agent-instructions.txt` |
| Data Agent の description、source 指示、few-shot | `workshop/v2.7.0/provisioning/bundle/data-agent/Files/Config/published/**` |
| 図版 | `docs/assets/v2.7.0/*.png`（300 dpi） |
| スタイル、ヘッダー / フッター、ページ設定、Purview ラベル、再利用画面写真 | `tools/docs/assets/style-carrier.zip` |

#### 自己完結性

build と validator は、v2.7 runtime、`docs/assets/v2.7.0`、
`tools/docs/assets/style-carrier.zip` **のみ**に依存します。旧版の配布物は必要とも
参照ともしないため、クリーンな v2.7 チェックアウトからすべてを再 build・再検証できます。
これは `validate_docs.py` の `toolchain.*` 検査が強制します。

- 保守対象の asset が存在し、開くことができ、必要なシェルパートと画面写真一式を持つこと。
- `StyleCarrier.resolve()` がその asset を返し、フォールバック経路を持たないこと。
- どの builder / validator も旧版の配布物をファイルパスとして解決しないこと。

`tools/docs/assets/style-carrier.zip` は、ブランド適用済みの OOXML シェルパート
（styles、theme、numbering、settings、header、footer、section / page 設定、
Purview ラベルのパート、ロゴ）と、現行の内容が再利用する Fabric UI の画面写真だけを
保持します。画面写真は旧版のアイテムタブ列を除去するように切り抜き済みです。
本文は一切引き継ぎません。廃止した画面写真は理由付きで
`guide_handson.RETIRED_SCREENSHOTS` に列挙し、build はそれらの埋め込みを拒否します。

asset の再生成は build の一部ではなく**保守**作業です。再利用する画面写真の集合か
ハウススタイルが変わったときにだけ実行してください。スタイル適用済みソース DOCX は
非公開アーカイブ／履歴から承認済みの外部ファイル `$CarrierSource` へ復元し、HEAD に戻しません。

```powershell
python .\tools\docs\make_style_carrier.py --source $CarrierSource
```

`--source` は必須です。このツールが削除済みファイルへ暗黙に手を伸ばすことはありません。

### 版名と検証対象を固定する

Word と HTML の build / validation / export に同じ `--edition unified-20260914` を渡します。
公開ペアの生成・描画・実 Word の SHA-256 と構造件数の pin は
[公開ペアの手順](../publication/README.md)に従います。旧版のハッシュや構造件数を使いません。

```powershell
python .\tools\docs\build_docs.py --public-documents-only --edition unified-20260914 --out $Stage
python .\tools\html\build_html.py --public-documents-only --edition unified-20260914 --out $Stage
```

`$Stage` は新しい外部 PRIVATE ディレクトリです。生成コマンドの非ゼロ終了で停止し、
再 build は別の fresh stage から始めます。検証・export 後の正確なペアだけを `docs` へ配置します。
HTML のダウンロード名と SHA-256 は同じ Word を指し、指定した版がなければ旧版へ戻らず停止します。
edition は小文字英数字、ハイフン、アンダースコアの 40 文字以内です。版名は合格証明ではありません。

`test_preview_material_gates.py`・`test_data_agent_practice_gates.py`・`test_capture_quality.py` は
`--edition unified-20260914` で `docs` 内の参加者 Word を解決するため、配置後だけ実行します。
`test_workbook_print.py` と `compare_semantics.py` は内部の全 Office セット用で、公開ペアの検査ではありません。
`test_deliverable_editions.py` の命名・保存・リンク検査は edition 引数を必要としません。

### Build

以下は**内部編集用の全 Office build** です。公開ペア用 `$Stage` とは別に、まだ存在しない
外部の絶対パス `$FullStage` を指定します。版名なし・出力先なしの互換用既定値は使いません。

```powershell
$Edition = 'unified-20260914'
if (Test-Path -LiteralPath $FullStage) { throw 'Choose a fresh external PRIVATE stage' }
python .\tools\docs\build_docs.py --edition $Edition --out $FullStage --keep-legacy
```

必要なローカル検査ではこの 1 回の呼び出しに `--skip-word` / `--skip-excel` を追加できますが、
省略した Office 更新は成功扱いにしません。再生成には別の新規 `$FullStage` を使います。
旧 HEAD の 8 点を除く release 作業を builder の自動清掃で代用しません。

Word の手順は best-effort です。各 DOCX を開き、すべての field と目次を更新し、
ページを組み直し、ページ数と語数の統計を記録して保存します。Word が使えない場合でも
build は成功し、その制限を報告します。Word は保存時に `docDefaults` を正規化し、
暗黙の既定値と一致する段落プロパティを落とすため、日本語の禁則・ぶら下げ宣言は
その後に書き戻します。

Excel の手順も best-effort です。ワークブックを再計算して、集計数式がキャッシュ済みの
結果とともに出荷されるようにします（そうしないと Explorer、SharePoint、PDF の
プレビューでそれらのセルが空で表示されます）。Excel はパッケージを書き換えるため、
そのあとで Purview ラベルのパートを再付与します。

#### 再現可能な出力

ソースが変わっていなければ 2 回の build はバイト単位で同一のファイルを生成します。
したがって、公開済みの配布物は再 build して SHA-256 を比較することで検証できます。
そのために、3 種類の build ノイズを `furusato_docs/reproducible.py` で除去しています。

| ノイズの発生源 | 除去方法 |
| --- | --- |
| `dcterms:created` / `dcterms:modified`、および Word の `TotalTime` カウンター | 宣言した build 時刻に固定する |
| ZIP メンバーのタイムスタンプ、圧縮、パーミッション、順序 | すべてのメンバーを明示的な `ZipInfo` で `write_package()` 経由で書き出す |
| Word と Excel が保存ごとに付与するランダム識別子 | `canonicalise_office_identifiers()` が文書順で採番し直す |

最後の項目は `w14:paraId`、`w14:textId`、`w14:docId`、`wp14:anchorId`、
`wp14:editId`、`w16cid:durableId`、`w:rsid*` テーブル、`_Toc*` ブックマーク名、
Excel の `xr:uid` を対象とします。これらは内容を表さず、リビジョンのマージ、
共同編集、相互参照のための記録にすぎませんが、Office は保存のたびに新しい
ランダム値を割り当てます。削除ではなく採番し直すことで一意性と整形式を保ちます。
`_Toc*` 名はハイパーリンクと `PAGEREF` field が参照するため、全体で対応付けを
張り替えます。

build 時刻は宣言済みの `RELEASE_EPOCH`（2026-08-14T00:00:00Z。Purview ラベルの
`SetDate` が持つ時刻と同じ）です。再現可能ビルドの標準である `SOURCE_DATE_EPOCH`
を設定すると上書きできます。

```powershell
$env:SOURCE_DATE_EPOCH = "1800000000"   # seconds since the Unix epoch
if (Test-Path -LiteralPath $FullStage) { throw 'Choose another fresh external PRIVATE stage' }
python .\tools\docs\build_docs.py --edition redeploy-20260913 --out $FullStage --keep-legacy
```

不正な値や 1980 年より前の値（ZIP が表現できません）は、不安定な出力を黙って
生成する代わりに無視され、`RELEASE_EPOCH` が使われます。検証は build に使ったのと
同じ値で行ってください。`properties.zipTimestamps`、`properties.coreTimestamps`、
`workbook.*` は、環境が宣言する時刻に対してパッケージを検査します。

書き込みはすべてステージングファイルを経由して所定の位置へ移動します。したがって、
build が書いたばかりのファイルを読むオンアクセス型ウイルススキャナーや、解放が
終わっていない Office COM サーバーによる一時的なロックが起きても、build を失敗させて
直前の出力を壊すのではなく再試行します。

### レイアウトとタイポグラフィ

配布物は A4 です。style carrier は US Letter で作成されているため、`StyleCarrier` が
ページサイズを書き換え、ヘッダーとフッターの右タブ位置を A4 の余白へ移動し、
日本語の段落既定値（`kinsoku`、`wordWrap`、`overflowPunct`、`topLinePunct`、
`autoSpaceDE`、`autoSpaceDN`）と `characterSpacingControl` を明示的に書き込みます。
表紙は先頭ページのヘッダーとフッターを空にしているため、ヘッダーもページ番号も
表示されません。

改ページの安全性は、期待ではなく構造で担保します。

- `CODE_BLOCK_UNBREAKABLE_LINES` 行までのコールアウトとリスティングは
  `cantSplit` を設定した 1 行のテーブルにしているため、ページ間で分断されません。
- 図の段落とデータテーブルの最終行は `keepNext` にしているため、キャプションだけが
  次ページの先頭に取り残されることはありません。
- 各番号付きリストは `startOverride` を持つ独自の numbering インスタンスを得るため、
  手順リストは前のリストの続きではなく 1 から始まります。
- 目次は本物の Word field です。各 `fldChar` と `instrText` はそれぞれ独自の run に
  存在し、field の `end` マーカーを担う段落は削除せずヘアラインへ潰しています。

### Validate

公開用は外部の正確なペア `$PairCheck` を指定します。生成済み `$Stage`、または配置済み 2 ファイルを
ハッシュ照合してコピーした新規外部ディレクトリを使い、`docs` は直接指定しません。

```powershell
python .\tools\docs\validate_docs.py --public-documents-only --edition unified-20260914 --out $PairCheck --render --check-urls
```

内部編集用の 3 Office 成果物は `--public-documents-only` を付けず、
`--edition redeploy-20260913 --out $FullStage` で別途検査します。欠けた別冊を旧版で代用しません。
`--render` は Office、`--check-urls` はネットワークが必要です。未実施は明記し、
JSON が必要なら `--json` を追加して記録をペア外へ保存します。
受入条件は `0 failure(s), 0 warning(s)` で、検査数は版とモードで変わります。
HTML の実 Word ハッシュ・構造件数 pin と export は [公開ペアの手順](../publication/README.md)に従います。

以下は共通／全編集用の検査一覧です。公開モードは参加者の本文・図版・元の rubric と仕様を保ち、
内部別冊・workbook・checklist・runtime 再封印の検査とは分離します。

- OOXML: ZIP の CRC、すべてのパートに content type があること、すべての内部
  リレーションシップが解決すること、パッケージが暗号化されていないこと、マクロパートが
  ないこと、変更履歴がないこと。
- Purview: `docMetadata/LabelInfo.xml` がラベルをちょうど 1 つ宣言していること
  （承認済み id、site id、`Privileged` メソッド、`contentBits="0"`）。パッケージの
  リレーションシップが存在すること。ラベルが非保護のままであること。レガシーな MSIP
  カスタムプロパティが、存在しないか、同一テナント上の同一ラベルを記述していること。
  他のラベル、site、action GUID がどのパートにも現れないこと。
- 来歴: `dc:creator` と `cp:lastModifiedBy` がいずれも `Furusato Fabric Workshop`
  であり、どのパートもローカルのファイルパスや作業者の識別情報を漏らさないこと。
  Office は COM 保存のたびに両方を刻むため、最後の更新後に正規化します。
- 再現性: すべての ZIP メンバーが宣言済みの build 時刻を持ち、2 つの core 日付が
  それと一致すること。style carrier の asset も同じ方法で検査します。
- プロパティ: タイトルが現行バージョンを含み、古いバージョン文字列を含まないこと。
- アクセシビリティ: すべてのインライン画像に代替テキストがあり、すべてのデータ
  テーブルにタイトルと説明があり、すべての図とデータテーブルにキャプションがあること。
- メディア: すべての `a:blip` 参照が解決すること、孤立した画像パートがないこと、
  同じ画像が 2 か所で再利用されていないこと。
- 内容: 禁止パターン（旧フロー名、内部 QA 資産、古いバージョン）が存在しないこと。
  すべての Entity、Relationship、Notebook パラメーター、Notebook ハッシュが
  存在すること。Agent instructions が逐語的に再現され、provisioning bundle と
  一致すること。
- 内部 QA の分離: 内部用の評価コーパスは配布リポジトリの外で管理し、参加者向け成果物で
  名前を出すことも、リンクすることも、ほのめかすこともできません。この禁止は
  抽出テキスト**と**生の著作 XML（`document.xml`、ヘッダー、フッター、注釈、
  `docProps`、`docMetadata`、すべての `.rels` パート）の両方に対して二重に強制するため、
  画像の代替テキスト、テーブルの説明、ハイパーリンクの宛先、文書プロパティに隠れた
  参照も検出されます。
- ワークブック: シートの順序、ファイルハッシュ、cell 数、Notebook ごとのソース行数と
  cell ハッシュ、Notebook のパラメーター cell に対するパラメーター行、主要な
  ファイル間契約、数式セルの存在。
- Test 10: すべての期待値を同梱 CSV から再計算すること。SQL/KQL/GQL のテキストが
  hold-out した記録票へ漏れていないこと。
- チェックリスト: Markdown のチェックリストが、同じ再計算値と一致すること。
- Toolchain: build の入力が自己完結であること（上記「自己完結性」を参照）。
- 品質ゲート（`quality.py`）: KQL の章が、同梱スクリプトが作成する管理コマンドを
  過不足なく列挙していること。Data Agent がマテリアライズドビューだけを選択すること。
  英語のセマンティックフィールドが Notebook 02 に帰属していること。time-series
  バインディング、カーディナリティ、メトリック / フローのエンティティがいずれも
  検証可能な期待値を持つこと。3 つの構成レイヤーが「重複ゼロ」ではなく「抽象の分離」
  として説明されていること。トラブルシューティングが章ごとに索引されていること。
  付録 B が 5 つの表の複製ではなく索引であること。
- 提供資料の扱い（`quality.py` / `validate_docs.py`）: 付録 C.6 と D.6 が必要な論点をすべて扱っていること。D.6 が held-out のテスト ID・判定値・runtime パラメーターを一切参照しないこと。未公開のモード名、機密表示、「プレビュー中は無償」、操作ごとの課金額、機能単位の EU Data Boundary 準拠、未公開の行数・ファイル数の上限、明示的な同意によるテレメトリの主張が本文に現れないこと。対話の保持を述べる文が日数を含まないこと。命名規則（1〜26 文字）と手動でのグラフモデル更新が Core の章にあること。参照 URL がすべて一次情報で `/en-us/` 形式であること。
- 出典（`validate_docs.py`）: 追跡対象のどのファイルにも機密表示がないこと。URL のホストが許可一覧の範囲内であること。すべての図が自作のベクター図であり、PNG が SVG のアスペクト比と一致すること。追跡対象にプレゼン・録画・アニメーションのコンテナがないこと。ガイダンスのモジュールに Office の編集痕跡（作成者名の組、セキュリティ識別子、メールアドレス、サードパーティ アドインの目印）がないこと。`docs/assets/` に SVG と対応する PNG 以外の資産がないこと。
- Data Agent の実務（`quality.py` / `validate_docs.py`）: グローバル指示の文字数上限が、本配布物の封印済み契約として書かれており、プラットフォームの保証値として書かれていないこと。KQL の例パターンの置き場所が、出荷した定義の事実として書かれており、製品の能力の主張になっていないこと。第 16.6.1・16.8・17.12・18.2 節と付録 C.7・D.7 が、公開情報で裏の取れる記述とともに存在すること。設定に関する節が held-out のテスト ID・判定値・runtime パラメーターを参照しないこと。将来のリリースに関する表現、CU の計算、トークン単価、API / SDK / MCP の断片、ロードマップの指示がいずれの新規節にも現れないこと。出荷した例クエリの質問が一意で、クエリが空でなく、入口テーブルが重複せず、いずれも選択済みテーブルであること。
- レイアウト: すべての section が A4 であること。日本語タイポグラフィが明示されて
  いること。本物の TOC field（Word 上で `TablesOfContents.Count == 1`）であること。
  先頭ページのヘッダーとフッターが空であること。短いコールアウトとリスティングの
  すべてに `cantSplit` があること。すべてのキャプションの直前に `keepNext` があること。
  8 pt 未満のインラインコード run がないこと。
- 日本語タイポグラフィ: `。`／`、` の前後に空白がないこと、句読点が重複しないこと、
  `（）` の内側に空白がないこと、日本語文字どうしの間に空白がないこと。逐語的な
  リスティングと引用した runtime の値は対象外です。
- 描画したページ（`--render`）: 各文書を Word で PDF へ書き出し、全ページを検査します。
  空白のページがないこと、キャプションだけのページがないこと、hold-out した各テストが
  判定基準の表と記録欄を 1 ページに収めていること。
- ワークブックの体裁: 印刷タイトル行の繰り返し、A4 のページ設定、シート／バージョン／
  ページのフッター、契約検査への緑／赤の条件付き書式、全幅の編集上の注記、
  切り詰められない結合済み集計ラベル、`Parameters_Core` の適用条件列、キャッシュ済みの
  数式結果。

### 2 つの build の比較

`compare_semantics.py` は各配布物を内容の指紋へ還元します。対象は段落、テーブルの
セル、メディアのハッシュ、代替テキスト、目次エントリ、そしてワークブックのすべての
セル、書式、結合、幅、印刷範囲、条件付き書式です。これにより、ある変更が
メタデータだけの変更であることを、思い込みではなく提示できます。

この既存ツールは `--edition` を受け取りますが `--out` はなく、リポジトリの `docs` にある
同じ版の Office 3 点を解決します。latest-only HEAD や外部 `$FullStage` のペア検査としては使えません。
必要なら完全な同版セットを持つ別の非公開 authoring tree でのみ使い、旧ファイルを release HEAD へ
戻して成立させません。公開ペアは外部ステージングの実バイトと Word/HTML の pin 付き検査で比較します。

既定の比較はメタデータ以外のすべての OOXML パートも対象にします。
`--content-only` はそれらの生ダイジェストを外すもので、比較そのものがツール側の
変更をまたぐときの正しい選択です。スナップショットは呼び出し側が指定した場所へ
書き出され、リポジトリには何も残りません。

### 必要なもの

`python-docx`、`openpyxl`、`Pillow`。`pywin32` は任意で、Word の field / TOC 更新と
Excel の再計算に使います。`PyMuPDF` は任意で、`--render` でのみ使います。

---

## English

Word and HTML use ASCII `(` / `)` in displayed text. The shared
`furusato_docs/typography.py` applies this at generation boundaries, including
stories, tables, headings, accessibility labels and dynamic bilingual HTML UI.
Runtime inputs, original evaluation criteria, hyperlink targets and image pixels
remain unchanged. Content comparisons normalize only this display difference;
separate typography gates reject any fullwidth parentheses left in editable output.

Deterministic builders and validators for three internal authoring Office
artifacts and an opt-in public-document mode. Every number, name, path, parameter default, hash, instruction text
and query snippet is read from the shipped v2.7.0 runtime at build time; nothing
is transcribed by hand. If the runtime changes and the documentation would drift,
the build fails instead of emitting a stale deliverable.

### Latest document pair

The release edition is `unified-20260914`. Only these two documents are current
downloads. The validated pair is installed under these names.

The current Word/HTML pair uses profile revision13 and synchronizes answerable
rephrasing, consent, correction/reconfirmation and cancellation. It distinguishes
instructions from enforced control and retains source, KQL, CI and refusal checks.
It also separates selected gifts from receipt, derived ranks from stored ranks,
and actual returned fields/provenance from authored labels.

| Document | Built by |
|---|---|
| [Participant Word](../../docs/Fabric_IQ_Ontology_Workshop_Furusato_Participant_v2.7.0_unified-20260914.docx) | `furusato_docs/participant_guide.py` (+ `guide_content`, `guide_handson`, `guide_agent`, `guide_unified`) |
| [Matching bilingual HTML](../../docs/furusato-workshop-v2-7-0-complete_unified-20260914.html) | `tools/html` (the same content model) |

The separate validation Word and specification XLSX are not current downloads.
Full Office authoring remains supported only with an explicit named edition in a
separate fresh external PRIVATE stage. In addition to participant Word,
`validation_doc.py` and `workbook.py` generate internal companions with the same
`_redeploy-20260913` suffix. Do not restore them to the current HEAD download list.

`docs/data-validation-checklist.md` is hand-maintained but validated by
`validate_docs.py` against the same runtime values.

### Public documents: exactly one Word and one matching HTML

Pass `--public-documents-only --edition unified-20260914 --out <external-private-staging>`
to both Python entry points, or use
`Build-Docs.ps1 -PublicDocumentsOnly -Edition <edition> -OutputDirectory <path>`.
Only the participant Word is built, refreshed and validated. The separate validation Word
and XLSX are not required, created or inspected. All 19 chapters, five appendices, the
original ten questions / 84 rubric requirements and parameter specifications remain. Recording instructions and the
parameter index point inside the guide; companions are optional internal material.
Build the HTML afterward with the same mode, edition and staging directory.

Public mode requires a nonempty edition and a fresh directory outside the repository.
The eight former HEAD Office/HTML artifacts were archived privately byte-for-byte and only
those eight were removed from HEAD after the new pair passed. Keep originals in private archive/history and retain
notebooks, data, code, diagrams and style assets.
Existing files and unexpected entries cause failure, never cleanup. It cannot be combined
with `--skip-workbook`. Public validation retains participant content, OOXML, visual and
capture checks, but does not run the repository-wide packaging/history audit or runtime
reseal. The full-authoring default keeps its existing checks and legacy behavior.
Public validators/exporter use an external pair directory. Repository `docs` contains
assets/checklist and is invalid input. Even after installation, copy only the two exact
files to fresh external staging and prove matching source-before/source-after/copy hashes.
Do not weaken path or inventory checks.

Use the [public-pair export procedure](../publication/README.md) to copy only Word and HTML
into a separate fresh destination, with any hash manifest **outside** the pair. This is
not GitHub publication or authorization to change visibility/history/hosting.
This distribution uses fresh public-only history without former private history or
evidence. Never merge/push private archive history here; follow [SECURITY.md](../../SECURITY.md).
Wait for the configuration, results and capture review to freeze before full binary builds.
The released `unified-20260914` pair synchronizes one primary Agent, the full
teaching Ontology, shared SQL/KQL helpers and same-Agent Code Interpreter exercises.
Legacy Core inputs remain intact. Work logs, live backups and detailed execution records are maintained
outside the distributable repository. Data Agent quality acceptance is separate from
deployment/document readiness; see [Data Agent response checks](../../docs/single-agent-workshop.md).

Capture handoff remains private: `$PrivateDocuments\captures\originals` holds untouched
UI originals, `captures\reviewed` holds cropped/redacted copies, and `captures\review.json`
records configuration/instruction hashes, capture time, original/reviewed image hashes,
crop bounds, redaction categories, text parity and approval. Global instructions belong in
section 16.3 as full text and a hash (`13-12` for legacy); source descriptions/instructions belong in
16.4/16.5, with new keys assigned only after review. Old unified configuration images
`16-30` and `18-30` are retained in the carrier but excluded from the current guide.
Only `17-40` is reused as a CI interaction illustration, with its original capture
identity, an unchanged CI-section digest and matching Preview/CI settings.
Validation rejects embedded obsolete configuration images. New configuration
captures require normal authenticated UI access and a fresh content/provenance review. Existing images
are not proof of the new configuration. Do not modify the carrier or current assets before
explicit approval. Preserve relevant UI content, redact accounts/URLs/internal IDs with
disclosure, and never edit evaluated answers or verdicts to manufacture PASS. Missing
captures remain pending; Word and HTML must later share the same approved images.
Label candidate settings/images as candidates; capture review does not authorize replacing
Core's descriptions or instructions.

### Prerequisites

- Python 3 and `tools/docs/requirements.txt` (`python-docx`, `openpyxl`, `Pillow`).
- `pywin32` and Office for the Word field/TOC refresh and the Excel
  recalculation, both optional. `PyMuPDF` for `--render`, also optional.
- The shipped `workshop/v2.7.0` runtime, `docs/assets/v2.7.0` and
  `tools/docs/assets/style-carrier.zip`.

### Layout

```
tools/docs/
  build_docs.py            entry point: build all three deliverables
  validate_docs.py         entry point: validate them (exit 1 on FAIL)
  make_style_carrier.py    regenerate assets/style-carrier.zip
  Build-Docs.ps1           PowerShell wrapper for build + validate
  requirements.txt
  assets/style-carrier.zip branded OOXML shell parts + reusable screenshots
  furusato_docs/
    context.py             loads the v2.7.0 runtime as the single source of truth
    facts.py               recomputes the Test 10 expectations from the packaged CSVs
    parameters.py          participant-facing prose for every notebook parameter
    tests10.py             the ten held-out colloquial/adversarial tests
    oox.py                 style carrier, package metadata, Purview label handling
    docx_kit.py            shared Fabric IQ visual language for Word
    guide_content.py       chapter 1-4 content model (concepts and rationale)
    guide_handson.py       chapter 6-15 (hands-on)
    guide_agent.py         chapter 16-19 and appendices A-E
    participant_guide.py   assembles the participant guide
    validation_doc.py      assembles the Test 10 record
    workbook.py            assembles the processing specification workbook
    validators.py          reusable OOXML / accessibility / content validators
    quality.py             quality-pass gates: content, OOXML layout, workbook print setup
    render_audit.py        renders every page with Word and inspects the result
    word_refresh.py        optional Word COM field, TOC and page-count refresh
    excel_refresh.py       optional Excel COM formula recalculation
```

### Sources of truth

| Value | Read from |
|---|---|
| Version | `VERSION` |
| Counts, amounts, observation window, checksums | `workshop/v2.7.0/data/dataset-manifest.json`, `SHA256SUMS.txt`, the packaged CSVs |
| Entity / Property / Relationship / binding definitions | `workshop/v2.7.0/ontology/ontology-full-definition-template.json` |
| Synonyms and the time-series Property | `workshop/v2.7.0/ontology/ontology-semantic-metadata.json` |
| Item naming and provisioning contract | `workshop/v2.7.0/participant-workspace-contract.json` |
| Notebook hashes, cell inventory, parameter defaults | `workshop/v2.7.0/notebooks/*.ipynb` |
| KQL objects and verification queries | `workshop/v2.7.0/kql/Furusato_Eventhouse_Setup_v2.7.0.kql` |
| Pipeline parameters and the file-name expression | `workshop/v2.7.0/provisioning/bundle/data-pipeline/pipeline-content.json` |
| Unified Agent instructions, sources and examples | `workshop/v2.7.0/provisioning/bundle/unified-agent/profile.json` and `inputs/` |
| Retained legacy Core global instructions | `workshop/v2.7.0/data-agent/agent-instructions.txt` |
| Retained legacy Core source settings | `workshop/v2.7.0/provisioning/bundle/data-agent/Files/Config/published/**` |
| Diagrams | `docs/assets/v2.7.0/*.png` (300 dpi) |
| Styles, header/footer, page setup, Purview label, reusable screenshots | `tools/docs/assets/style-carrier.zip` |

#### Self-sufficiency

The build and the validators depend **only** on the v2.7 runtime, `docs/assets/v2.7.0`
and `tools/docs/assets/style-carrier.zip`. No superseded deliverable is required or
resolved, so a clean v2.7 checkout can rebuild and revalidate everything. This is
enforced by the `toolchain.*` checks in `validate_docs.py`:

- the maintained asset exists, opens, and carries every required shell part plus
  the full screenshot set;
- `StyleCarrier.resolve()` returns that asset and has no fallback path;
- no builder or validator resolves a superseded deliverable as a file path.

`tools/docs/assets/style-carrier.zip` holds only the branded OOXML shell parts
(styles, theme, numbering, settings, header, footer, section/page setup, the
Purview label parts, the logos) and exactly the Fabric UI screenshots the current
content reuses, already cropped to remove the superseded item tab strip. No body
content is carried over. Retired screenshots are listed with a reason in
`guide_handson.RETIRED_SCREENSHOTS` and the build refuses to embed them.

Regenerating the asset is a **maintenance** step, not part of the build. Run it
only when the reusable screenshot set or the house style changes. Restore the styled
source DOCX from private archive/history to an approved external `$CarrierSource`,
not to release HEAD:

```powershell
python .\tools\docs\make_style_carrier.py --source $CarrierSource
```

`--source` is required: the tool never silently reaches for a deleted file.

### Pin the edition and validation target

Pass the same `--edition redeploy-20260913` to Word/HTML build, validation and
export. Follow the [pair procedure](../publication/README.md) for rendering and
actual Word SHA-256/structural pins. Never reuse older-edition hashes or counts.

```powershell
python .\tools\docs\build_docs.py --public-documents-only --edition redeploy-20260913 --out $Stage
python .\tools\html\build_html.py --public-documents-only --edition redeploy-20260913 --out $Stage
```

`$Stage` is a fresh external PRIVATE directory. Stop on each nonzero exit; rebuild
in another fresh stage. Install only the exact validated/exported pair under `docs`.
HTML downloads and SHA-256 refer to that Word; a missing edition source is an error,
never old-file fallback. Edition names accept lowercase letters, digits, hyphens and
underscores up to 40 characters. The name is not an acceptance certificate.

`test_preview_material_gates.py`, `test_data_agent_practice_gates.py` and
`test_capture_quality.py` resolve the participant Word under `docs` with
`--edition unified-20260914`; run them only after installation.
`test_workbook_print.py` and `compare_semantics.py` require the internal full Office
set, not the public pair. Naming/preservation/link checks in
`test_deliverable_editions.py` need no edition argument.

### Build

This is the **internal full Office authoring** build. Set `$FullStage` to a new,
absent external absolute PRIVATE path, separate from the public `$Stage`.
Do not use edition-free or output-free compatibility defaults.

```powershell
$Edition = 'redeploy-20260913'
if (Test-Path -LiteralPath $FullStage) { throw 'Choose a fresh external PRIVATE stage' }
python .\tools\docs\build_docs.py --edition $Edition --out $FullStage --keep-legacy
```

For local checks, add `--skip-word` / `--skip-excel` to this single invocation if
needed, but do not mark skipped Office refreshes as passed. Use another fresh
`$FullStage` for each rebuild. The release's narrow removal of eight old HEAD
artifacts is not delegated to automatic builder cleanup.

The Word step is best-effort: it opens each DOCX, updates all fields and the
table of contents, repaginates, records page and word statistics, and saves. If
Word is unavailable the build still succeeds and reports the limitation. Word
normalises `docDefaults` on save and drops paragraph properties that already
match its implicit defaults, so the Japanese kinsoku / overflow-punctuation
declarations are written back afterwards.

The Excel step is best-effort too: it recalculates the workbook so the summary
formulas ship with cached results (otherwise Explorer, SharePoint and PDF
previews render those cells empty), then the Purview label parts are re-attached
because Excel rewrites the package.

#### Reproducible output

Two builds of unchanged sources produce byte-identical files, so a published
deliverable can be verified by rebuilding it and comparing SHA-256. Three classes
of build noise are removed to get there, all in `furusato_docs/reproducible.py`:

| Source of noise | How it is removed |
| --- | --- |
| `dcterms:created` / `dcterms:modified`, and Word's `TotalTime` counter | Fixed to the declared build instant |
| ZIP member timestamps, compression, permissions and order | Every member written through `write_package()` with an explicit `ZipInfo` |
| Word's and Excel's per-save random identifiers | Renumbered in document order by `canonicalise_office_identifiers()` |

The last one covers `w14:paraId`, `w14:textId`, `w14:docId`, `wp14:anchorId`,
`wp14:editId`, `w16cid:durableId`, the `w:rsid*` table, the `_Toc*` bookmark names
and Excel's `xr:uid`. None of them describe content — they are bookkeeping for
revision merging, co-authoring and cross-references — but Office assigns fresh
random values on every save. They are renumbered rather than deleted, so they stay
unique and well-formed; `_Toc*` names are remapped globally because hyperlinks and
`PAGEREF` fields reference them.

The build instant is the declared `RELEASE_EPOCH` (2026-08-14T00:00:00Z, the same
instant the Purview label `SetDate` carries). Set the reproducible-builds standard
`SOURCE_DATE_EPOCH` to override it:

```powershell
$env:SOURCE_DATE_EPOCH = "1800000000"   # seconds since the Unix epoch
if (Test-Path -LiteralPath $FullStage) { throw 'Choose another fresh external PRIVATE stage' }
python .\tools\docs\build_docs.py --edition redeploy-20260913 --out $FullStage --keep-legacy
```

A malformed value, or one before 1980 (which ZIP cannot represent), is ignored in
favour of `RELEASE_EPOCH` rather than silently producing unstable output. Validate
with the same value you built with: `properties.zipTimestamps`,
`properties.coreTimestamps` and `workbook.*` check the packages against whatever
instant the environment declares.

Every write also goes through a staging file that is moved into place, so a
transient lock — an on-access virus scanner reading the file the build just wrote,
or an Office COM server that has not finished releasing it — retries instead of
failing the build and destroying the previous output.

### Layout and typography

The deliverables are A4. The style carrier was authored on US Letter, so
`StyleCarrier` rewrites the page size, moves the header and footer right tab
stops onto the A4 margin, and writes the Japanese paragraph defaults
(`kinsoku`, `wordWrap`, `overflowPunct`, `topLinePunct`, `autoSpaceDE`,
`autoSpaceDN`) plus `characterSpacingControl` explicitly. The cover uses a blank
first-page header and footer so it carries no running header and no page number.

Page-break safety is structural rather than hopeful:

- callouts and listings up to `CODE_BLOCK_UNBREAKABLE_LINES` lines are single-row
  tables marked `cantSplit`, so they can never be torn across a page;
- a figure paragraph and the last row of a data table are `keepNext`, so a
  caption can never be stranded at the top of the next page;
- each numbered list gets its own numbering instance with `startOverride`, so a
  step list opens at 1 rather than continuing the previous list;
- the table of contents is a real Word field: each `fldChar` and the `instrText`
  live in their own run, and the paragraph that carries the field's `end` marker
  is collapsed to a hairline rather than deleted.

### Validate

For public documents, use external exact-pair `$PairCheck`: the completed `$Stage`
or a fresh external hash-verified copy of only the installed two files. Never point
these public checks directly at repository `docs`.

```powershell
python .\tools\docs\validate_docs.py --public-documents-only --edition redeploy-20260913 --out $PairCheck --render --check-urls
```

Validate the three internal Office outputs separately without `--public-documents-only`,
using `--edition redeploy-20260913 --out $FullStage`. Never substitute old companions.
`--render` needs Office; `--check-urls` needs network access. Record unexecuted checks.
Add `--json` for a machine-readable report kept outside the pair.
Acceptance requires `0 failure(s), 0 warning(s)`; counts vary by edition and mode.
Follow the [pair procedure](../publication/README.md) for HTML's actual Word hash/shape
pins and export.

The following lists common/full-authoring checks. Public mode retains participant
content, visuals, the original rubric and specifications, separately from internal
companion/workbook/checklist/runtime-reseal checks.

- OOXML: ZIP CRC, every part has a content type, every internal relationship
  resolves, package is not encrypted, no macro parts, no tracked changes.
- Purview: `docMetadata/LabelInfo.xml` states exactly one label — the approved
  id, site id, `Privileged` method and `contentBits="0"` — the package
  relationship is present, the label stays non-protective, and the legacy MSIP
  custom properties are either absent or describe that same label on that same
  tenant. No other label, site or action GUID may appear in any part.
- Provenance: `dc:creator` and `cp:lastModifiedBy` both read
  `Furusato Fabric Workshop`, and no part leaks a local filesystem path or the
  operator's identity. Office stamps both on every COM save, so they are
  normalised after the last refresh.
- Reproducibility: every ZIP member carries the declared build instant, and both
  core dates equal it. The style carrier asset is checked the same way.
- Properties: title carries the current version and no stale version strings.
- Accessibility: every inline image has alt text, every data table has a title
  and description, every figure and data table has a caption.
- Media: every `a:blip` reference resolves, no orphan image parts, no image
  reused in two places.
- Content: no forbidden pattern (superseded flow names, internal QA assets,
  stale versions), every entity, relationship, notebook parameter and notebook
  hash is present, the agent instructions are reproduced verbatim and match the
  provisioning bundle.
- Internal QA isolation: internal evaluation corpora are kept outside this distribution and
  must never be named, linked or hinted at in a participant artifact. The ban is
  enforced twice — over the extracted text *and* over the raw authored XML
  (`document.xml`, headers, footers, notes, `docProps`, `docMetadata` and every
  `.rels` part), so a reference hidden in image alt text, a table description, a
  hyperlink target or a document property is caught too.
- Workbook: sheet order, file hash, cell count, source line count and cell hash
  per notebook, parameter rows against the notebook parameter cells, the key
  cross-file contracts, and the presence of formula cells.
- Test 10: every expected value is recomputed from the packaged CSVs, and no
  SQL/KQL/GQL text leaks into the held-out record.
- Checklist: the markdown checklist agrees with the same recomputed values.
- Toolchain: the build inputs are self-sufficient (see **Self-sufficiency** above).
- Quality gates (`quality.py`): the KQL chapter lists exactly the management
  commands the shipped script creates and nothing else; the Data Agent selects
  only the materialized view; the English semantic fields are attributed to
  Notebook 02; the time-series binding, cardinality and metric/flow entities all
  have verifiable expected values; the three configuration layers are described
  as separated abstraction rather than zero duplication; troubleshooting is
  chapter-indexed; appendix B is an index, not a duplicate of five tables.
- Supplied-material handling (`quality.py` / `validate_docs.py`): appendices C.6
  and D.6 cover every topic they must; D.6 names no held-out test id, verdict or
  runtime parameter; no unpublished mode label, confidentiality marking,
  free-during-preview claim, per-operation price, per-feature EU Data Boundary
  conformance, unpublished row/file ceiling or explicit-consent telemetry claim
  appears; no conversation-retention sentence carries a duration; the 1-26
  naming rule and the manual graph-model refresh are in the Core chapters; every
  reference URL is first-party and uses the `/en-us/` form.
- Provenance (`validate_docs.py`): no tracked file carries a confidentiality
  marking, every URL host is on the allow list, and every diagram is
  author-created vector art whose PNG matches the SVG aspect ratio. No tracked
  path is a presentation, recording or animation container; the guidance modules
  carry no Office authoring trail (author tuple, security identifier, mail
  address, third-party add-in marker); `docs/assets/` holds SVG originals with a
  matching PNG and nothing else.
- Data Agent practice (`quality.py` / `validate_docs.py`): the character budget
  for the global instructions is stated as this distribution's sealed contract
  rather than a platform warranty; the KQL shape placement is a fact about the
  shipped bundle rather than a product capability claim; sections 16.6.1, 16.8,
  17.12 and 18.2 and appendices C.7 and D.7 are present with the statements the
  published sources support; the configuration sections name no held-out test,
  verdict or runtime parameter; none of them prints forward-looking release
  language, capacity-unit arithmetic, a per-token rate, an API/SDK/MCP fragment
  or a roadmap directive; and the shipped example queries have unique questions,
  non-empty bodies, distinct entry tables and entry tables the Agent selects.
- Layout: A4 in every section, explicit Japanese typography, a real TOC field
  (`TablesOfContents.Count == 1` in Word), a blank first-page header and footer,
  `cantSplit` on every short callout and listing, `keepNext` in front of every
  caption, and no inline-code run below 8 pt.
- Japanese typography: no space before or after `。`/`、`, no doubled punctuation,
  no space inside `（）`, no space between two Japanese characters. Verbatim
  listings and quoted runtime values are excluded.
- Rendered pages (`--render`): each document is exported to PDF with Word and
  every page is inspected. No page may be blank, no page may hold nothing but a
  caption, and each held-out test must keep its criteria table and record form on
  one page.
- Workbook presentation: repeating print-title rows, an A4 page setup, a
  sheet/version/page footer, green/red conditional formatting on the contract
  checks, a full-width editing note, merged summary labels that cannot be
  clipped, an application-condition column in `Parameters_Core`, and cached
  formula results.

### Comparing two builds

`compare_semantics.py` reduces each deliverable to a content fingerprint —
paragraphs, table cells, media hashes, alt text, contents entries, and every
workbook cell, format, merge, width, print area and conditional format — so a
change can be shown to be metadata-only rather than merely assumed to be:

This existing tool accepts `--edition` but has no `--out`; it resolves all three
same-edition Office files under repository `docs`. It cannot validate a latest-only
HEAD or a pair in external `$FullStage`. If needed, use it only in a separate private
authoring tree holding a complete same-edition set; do not restore old files to
release HEAD to satisfy it. Compare the public pair through external staged bytes
and pinned Word/HTML validation instead.

The default comparison also covers every non-metadata OOXML part; `--content-only`
drops those raw digests and is the right choice when the comparison itself spans a
change to the tooling. Snapshots are written wherever the caller asks and nothing
is left in the repository.

### Requirements

`python-docx`, `openpyxl`, `Pillow`. `pywin32` is optional and used for the Word
field/TOC refresh and the Excel recalculation. `PyMuPDF` is optional and only
used by `--render`.
