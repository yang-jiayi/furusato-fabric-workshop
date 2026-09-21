# tools/html — 日英 2 言語の単一ファイル HTML 配布物 / bilingual single-file HTML deliverable

[日本語](#日本語) | [English](#english)

---

## 日本語

最新版は
[furusato-workshop-v2-7-0-complete_unified-20260914.html](../../docs/furusato-workshop-v2-7-0-complete_unified-20260914.html)
です。[同じ版の参加者 Word](../../docs/Fabric_IQ_Ontology_Workshop_Furusato_Participant_v2.7.0_unified-20260914.docx)
を日英で完全にミラーした自己完結の 1 ファイルで、現行の文書配布対象はこの 2 点だけです。
検証済みペアをこの名前で配置しています。

統合プロファイルは revision 13 です。選択／受領と元の返却列・出典の保持、照会可能な質問への言い直し・同意待ち・再確認・取消と、
出典・順位範囲・KQL / CI の確認手順を日英で同期します。古い設定画像は掲載せず、
未変更のCI指示・設定に対応する実UI画像だけを、撮影時の来歴を保った操作例として使います。

Word ガイドが記録の正本です。このツールチェーンはその文章を**書き直しません**。
DOCX を生成するのと*同じ*章 builder を、キャプチャ用の builder に対して実行するため、
HTML は同一のコンテンツモデル（すべての見出し、段落、リスト、コールアウト、
コードブロック、テーブル、図、キャプションを文書順で）を持ちます。英語は、日本語の
文字列そのものをキーとする保守済みのミラーから供給されるため、2 つの言語が静かに
乖離することはありません。

### 公開文書ペア用のモード

既定の 3 Office ハッシュ・3 ダウンロードは内部編集用で、現行ダウンロードではありません。
公開用には、先に同じ版の Word を新しい外部 PRIVATE ステージング `$Stage` へ作り、
以下の指定で HTML を同じ場所へ生成します。非ゼロ終了なら次へ進みません。

```powershell
$Edition = 'unified-20260914'
python .\tools\html\sync_i18n.py --public-documents-only --edition $Edition
python .\tools\html\build_html.py --public-documents-only --edition $Edition --out $Stage
python .\tools\html\validate_html.py --public-documents-only --edition $Edition --out $Stage
```

`$Stage` はリポジトリ外の参加者 Word がある新規ディレクトリです。validation / export の
対象は正確な 2 ファイルだけの外部ディレクトリです。assets / checklist がある `docs` は
直接渡せません。配置後もその 2 ファイルだけを新しい外部 staging へコピーして原本の
コピー前後とコピー先のハッシュ一致を証明し、パス検査を迂回しません。
HTML のリンクと provenance はその Word 1 点の同じファイル名・実バイトの SHA-256 だけを使います。
別冊 Word、XLSX、旧版へのリンクやフォールバックはありません。`--release-digest` は使えません。
本文・全章・元の 10 問／84 要件・記録方法・全パラメーターは削りません。公開版だけの表紙注記・記録方法・仕様表参照を、
`i18n/public-documents.json` の明示的な差分で対訳します。両モードの missing / unused 検査は有効です。
公開モードの `sync_i18n.py` は読み取り専用で、`--prune` / `--rewrite` と併用できません。

`Build-Html.ps1` / `Finalize-Html.ps1` も `-PublicDocumentsOnly -Edition ... -Out ...` を受け付けます。
最終化にはその版の `-ParticipantSha` と 5 種類の構造件数を明示します。別冊ハッシュは渡しません。
pin はレビュー済みの実 Word から取得し、旧版の固定値や HTML 自身の件数を使いません。
`Finalize-Html.ps1` は HTML を生成するため、新しい Word-only stage での代替 build 手順です。
HTML が既にあるペアや配置済みペアの読み取り専用再検証には使いません。
画面写真、テスト結果、manifest は `-Out` の外へ置いてください。
原本や既存 HTML を上書きせず、再 build は新しいステージングから始めます。
[export ツール](../publication/README.md)が公開ペアの 2 ファイル allowlist と実バイトを再検証します。
生成・Word 描画・hash/shape pin・browser / print 検査・別の新しい外部ペアへの export の
一連の手順も同じ文書にあります。
完全な build は構成・評価・画面写真の凍結後に行います。
キャプチャの承認・伏せ字・原本保存の手順は [tools/docs](../docs/README.md) を参照してください。
旧画面を新構成の証明に流用せず、既存の carrier / assets は承認前に変更しません。
配布 Word／HTML は主 Agent 1 件、完全な教材用 Ontology、共有 SQL/KQL ヘルパー、
同じ Agent の Code Interpreter 演習を同期した `unified-20260914` です。
古い指示が写る `13-12`・`13-33`・`16-30`・`18-30` は現行版から除外し、原本を保持します。
`17-40` は互換性を検査したCI操作例で、新しい設定や評価の証拠ではありません。
正常な本人認証による新規撮影なしに、旧画像の設定版やハッシュを現行版へ付け替えません。
作業ログ・実環境のバックアップ・詳細な実行記録は配布リポジトリの外で管理します。
品質合格はデプロイ・文書の準備完了と別で、
[Data Agent の回答確認](../../docs/single-agent-workshop.md)を参照してください。
Notebook・データ・コード・図版・style 資産は保持します。この配布版は公開用の新規履歴を使い、
旧 Private の履歴や証跡は取り込みません。HTML build は hosting や公開変更の承認ではありません。
旧履歴を公開側へ merge／push せず、[SECURITY.md](../../SECURITY.md) に従ってください。

### 前提

- Python 3 と `tools/html/requirements.txt`。
- `Pillow`（WebP エンコードと英語図版のフォント計測用）と
  `python-docx`（`tools/docs` が import するため）。
- 対話テストにのみ `playwright`（および `python -m playwright install chromium`）。
- 同梱された `workshop/v2.7.0` runtime、`docs/assets/v2.7.0`、
  `tools/docs/assets/style-carrier.zip`。

### 構成

```
tools/html/
  build_html.py              エントリポイント: 配布物を build する
  validate_html.py           エントリポイント: 検証する（FAIL があれば exit 1）
  sync_i18n.py               保守: Word 変更後のミラー乖離を報告する
  Build-Html.ps1             PowerShell ラッパー（build + validate + interaction）
  Finalize-Html.ps1          pin 付きの最終化（drift → build → validate → interaction）
  requirements.txt
  assets/
    app.css                  Fabric IQ のハウススタイル。build 時にインライン化
    app.js                   振る舞い層。build 時にインライン化
  furusato_html/
    capture.py               DocumentBuilder を duck-type してモデルを記録する
    mirror.py                日本語 → 英語の参照。失敗は大きな音で知らせる
    model.py                 日英のセクションツリー、id、チェックリストの導出
    assets.py                単一埋め込みの SVG / WebP インライナー
    diagrams.py              build 時に SVG 図版の英語版を導出する
    render.py                ブロックとセクションの描画
    page.py                  ページの外枠: head、chrome、表紙、目次、フッター
    i18n/
      GLOSSARY.md            翻訳ルールと用語集
      guide-*.json          ガイドのミラー。レビューしやすさのために番号付きファイルへ分割
      public-documents.json 公開モードだけの明示的な文言差分
      diagrams.json          図版ラベルのミラー
      ui.json                chrome、コントロール、状態の文字列
  tests/
    test_interaction.py      ヘッドレス Chromium による対話テスト
```

### 正本の所在

| 値 | 読み取り元 |
|---|---|
| コンテンツモデル（第 1〜19 章、付録 A〜E） | `tools/docs/furusato_docs/{participant_guide,guide_handson,guide_agent}.py` |
| 件数、金額、観測窓、ハッシュ、パラメーター、テスト | 同梱の `workshop/v2.7.0` runtime。`furusato_docs.context` / `facts` / `parameters` / `tests10` 経由 |
| 図版 | `docs/assets/v2.7.0/*.svg`。サニタイズ済み SVG としてインライン化 |
| Fabric UI の画面写真 | `tools/docs/assets/style-carrier.zip`。可逆 WebP へ再エンコード |
| 英語テキスト | `furusato_html/i18n/guide-*.json` と `ui.json` |

公開モードは staging にある同じ版の参加者 Word だけを解決し、旧配布物へフォールバックしません。
runtime・図版・style carrier は保持します。旧 Office/HTML は非公開アーカイブ／履歴で保持し、
再 build のために release HEAD へ戻す必要はありません。

### 最新版と内部編集用モードを分ける

最新版は Word / HTML とも `--public-documents-only --edition unified-20260914` を使います。
`source.downloadEdition` は版の混在を検出します。版名は識別子であり、Fabric の品質合格ではありません。
版名なし・出力先なしの互換用既定コマンドは使わず、再 build は fresh stage から行います。

内部編集用の全 Office build は [tools/docs](../docs/README.md) の named edition と外部 PRIVATE
staging で継続できます。ただし既存の**全編集用 HTML** は Office 入力をリポジトリの `docs` から
解決し、`--out` は HTML 出力先だけを変えます。この経路は latest-only checkout の公開手順ではありません。
必要なら同版の全 Office セットを持つ別の非公開 authoring tree でだけ使い、別冊や旧版を
release HEAD へ戻して成立させません。新しい private HTML 出力先と named edition を必ず指定します。
その内部経路の `Finalize-Html.ps1` は 3 Office ハッシュと全 5 構造件数を必要とします。
公開経路へ `-TestRecordSha` / `-WorkbookSha` を渡してはいけません。

### Build

```powershell
python .\tools\html\build_html.py --public-documents-only --edition unified-20260914 --out $Stage --json
```

`$Stage` には同じ版のレビュー済み参加者 Word だけを置き、既存 HTML がある場所へ再生成しません。
JSON レポートを保存する場合もペア外の `$Review` を使います。build は決定的です。

* 実時刻は出力に入りません。記録される build 指紋は、runtime の入力ダイジェストと
  `tools/html` のソースダイジェストのダイジェストです。
* すべての画像はちょうど 1 回だけ埋め込まれ、ソースの重複は hard error です。
* ファイルは出力先フォルダー内の一時ファイルを経由して原子的に書き出されます。

次の場合、乖離した配布物を出力する代わりに失敗します。

* キャプチャした日本語文字列に英語ミラーが無い、
* ミラーのエントリがコンテンツモデルから使われなくなっている、
* 英語の値が未翻訳に見える、
* 正本の `DocumentBuilder` に、キャプチャがモデル化していないメンバーが増えた、
* `VERSION` が、このソースツリーが対象とするリリースと一致しなくなった。

Word ガイドの変更後は、両モードの `sync_i18n.py` で乖離を読み取り専用で検査します。
通常モードの `--prune` / `--rewrite` は明示的な翻訳保守だけに使う変更操作で、
この release 検査では実行しません。

```powershell
python .\tools\html\sync_i18n.py
python .\tools\html\sync_i18n.py --public-documents-only
```

### Validate

`$PairCheck` は [公開ペアの手順](../publication/README.md)で作成した外部の正確な 2 ファイル用
ディレクトリです。`$WordSha` と `$Shape` は実 Word のレビューで確定した値です。

```powershell
$Edition = 'unified-20260914'
python .\tools\html\validate_html.py --public-documents-only --edition $Edition --out $PairCheck `
  --expect-source "Fabric_IQ_Ontology_Workshop_Furusato_Participant_v2.7.0_${Edition}.docx=$WordSha" `
  --expect-shape "chapters=$($Shape.chapters)" --expect-shape "headings=$($Shape.headings)" `
  --expect-shape "tables=$($Shape.tables)" --expect-shape "figures=$($Shape.figures)" `
  --expect-shape "tests=$($Shape.tests)"
```

`--expect-source` は、HTML がミラーしたはずの Office 配布物のダイジェストを pin し、
`--expect-shape` は、ミラーが再現すべき Word の構造的合計値（`chapters`、
`headings`、`tables`、`figures`、`tests`）を pin します。両者により、
「これは最終ガイドをミラーしている」という主張が検査に変わります。旧版の
コンテンツモデルから build されたミラーは、出荷される代わりに失敗します。
なお Word は field を更新してページを組み直すたびに DOCX パッケージを書き換えるため、
内容が変わらなくても配布物のバイトダイジェストは変わります。フッターは実際に
ミラーしたダイジェストを記録し、`source.matchesDisk` がファイルを読み直して
HTML が古くないことを証明します。

受入条件は `0 failed` です。検査数・実測値は今回の版から記録し、旧版の結果を転用しません。
`--json` も指定できますが保存先はペア外です。`Finalize-Html.ps1` を新規生成の代わりに使うときは
`-PublicDocumentsOnly -Edition unified-20260914 -Out $Stage -ParticipantSha $WordSha` と
当該 Word の `-Chapters`・`-Headings`・`-Tables`・`-Figures`・`-Tests`、ペア外の `-Artifacts` を
すべて明示します。既存ペアの再検証は上の validator を使います。

#### 日英 2 言語の図版

`docs/assets/v2.7.0` にある 7 つの図版は日本語で作成されています。ページを英語に
切り替えると、以前は英語のキャプションの下に日本語の絵が残っていました。そこで
`furusato_html/diagrams.py` が、`i18n/diagrams.json`（297 ラベル）から各 SVG の
英語版を build 時に導出します。同梱 asset は決して変更されません。日本語版が記録の
正本であり続け、`diagrams.fresh` は日本語の図版がディスク上とバイト単位で同一で
あることを引き続き証明し、両方の版が同じ `<figure>` の中に存在して、有効な言語だけが
表示されます。

図版が持つ 3 つの性質が実装を決めました。いずれも推測ではなく SVG を実際に見て
判明したものです。

* **日本語の原図では、長いラベルは兄弟の `<text>` 要素にまたがって手で折り返されています**。
  原図に `tspan` はありません。生成する英語版は別で、必要な行を `tspan` で表現します。
  原図を行ごとに翻訳すると `を辿る。` のような
  断片が生じたため、x 座標とフォントサイズを共有し、およそ 1 行分ずつ下がる行を
  結合し、1 文として翻訳してから折り返し直します。
* **一部の見出しには作者自身の英語が既に付いています。** それらは再翻訳せずに
  再利用し、実際に生成されたテキストを隣の行と比較して重複を取り除きます。以前の
  版は位置と文字サイズから推測して両方向に誤りました。ある図は訳を日本語より
  *小さく*、別の図は*大きく*設定し、3 つ目は説明の次に次項目の見出しが続くために
  訳のように見えるだけでした。6 図すべてに通用する規則は、内容の比較だけです。
* **英語は日本語より多くの行を必要とする場合があります。** 元の行数で折り返しを
  打ち切ると、最終行が隣の箱へはみ出します。そこでインストール済みフォントを
  Pillow で計測し、ラベルが所属する図形の内側に収まるように `tspan` へ折り返します。
  全体を一律縮小したり本文を切り捨てたりせず、必要な場合だけラベル背面の小さな
  背景図形を限定的に拡張します。接続線の経路と矢印の定義は変えません。

英語図版の再現にはフォントの選択と計測結果も関係します。比較用 build では
同じフォント版、Pillow / FreeType を使い、生成物の SHA-256 とブラウザーでの
ラベル収まりを確認します。利用可能な場合は Yu Gothic UI Regular / Bold の
TTC face 1 を使い、無い場合は Meiryo → Segoe UI → DejaVu Sans → Arial の順で
選択します。対応フォントが無ければ明示的に停止します。生成 SVG は計測した
family を先頭に置き、原図の fallback stack も残します。フォントファイルや
ホストのパスは埋め込みません。閲覧側で代替フォントが使われる場合は、対象環境で
図形の収まりを再確認してください。

`diagrams.englishArtworkIsEnglish` は、固有名詞の明示的な許可リストを除き、英語版に
日本語が残っていれば失敗します。build 自体も、ラベルがすべて対応付けられていない
図版の出力を拒否します。

#### レイアウトのみの Office 再発行

以下は別の非公開 authoring tree でのみ使う全編集用の互換機能です。**公開ペアでは
`--release-digest` を拒否します。** Word の実バイトが変われば、新しい外部 stage で HTML を
再生成して実ハッシュを検証し、フッターだけを再刻印しません。

Word がページ組みの修正のためだけに再発行されることがあります。本文、テーブル、
runtime は同一で、DOCX のバイトだけが動きます。再ミラーは無意味ですが、フッターは
配布された相手が手にしているダイジェストを示すべきです。`--release-digest` がそれを
行い、`--content-fingerprint` がその主張を検証します。

この内部経路でも named edition と新しい外部 PRIVATE 出力先を指定し、
`--release-digest NAME=SHA256` は同版の実際の対象名、`--content-fingerprint` はレビュー済みの値を使います。
release HEAD の旧版や暗黙の既定値は参照しません。

コンテンツ指紋はキャプチャしたコンテンツモデルだけをハッシュします。asset、CSS、JS、
Office のダイジェストは含みません。したがってページ組みの変更に対して不変で、
語が 1 つ変わった瞬間に動きます。一致しなければ build は拒否し、
`--content-fingerprint` の無い `--release-digest` も拒否します。これにより
「レイアウトのみ」は信じるものではなく検証されるものになります。フッターは 2 つの
ダイジェスト、すなわち人が引用するリリースダイジェストと、実際にディスク上にある
ダイジェストを、レイアウトのみの再発行であると両言語で明示して記載します。
`source.layoutReissue` はどのファイルがその状態かを報告し、`source.matchesDisk` は
ディスクと観測されたダイジェストを比較するため、本当に古いミラーは依然として失敗します。
build レポートの `--json` は `contentFingerprint` を出力します。

#### 実施する検査

* **マークアップ** — 厳密なタグスタックリーダーで解析すること、`<!DOCTYPE html>` が
  1 つ、`html`／`head`／`body`／`main`／`footer` が各 1 つ、想定どおりの前書きと後書き。
* **構造** — 1〜19 のあと A〜E と番号付けされた 24 のトップレベルセクション、
  飛びのない順序付き見出しレベル、一意な要素 id、すべての内部アンカーと
  `aria-controls`／`aria-labelledby` 参照が解決すること。
* **日英 parity** — すべての日本語 span が同じ親の下に英語の兄弟を持つこと、
  どちらも正しい `lang` を持つこと、どちらも空でないこと、孤立したミラーエントリが
  無いこと、日本語のままの英語値が無いこと。
* **Runtime の事実** — 件数、金額、観測窓、ファイル別の行数と金額、run id、公開時刻、
  JST の繰り上がり、ノード／エッジ合計、メタデータのオブジェクト数、すべての Entity と
  Relationship 名、43 の Notebook パラメーター、hold-out した 10 問、8 月の 31 日分の日付。
* **Data Agent** — グローバル指示の逐語再現とその文字数、バイト数、SHA-256。
  すべての source description。Lakehouse と Kusto の source 指示。Ontology の source は
  description のみを持つこと。3 件の SQL few-shot の逐語再現。curated view の KQL 形状が
  2 つ以上。さらに provisioning bundle から、
  Eventhouse の source が `DonationObservationSummaryForAgent` **だけ**を公開すること
  （raw イベントテーブルは決して公開しないこと）、Lakehouse の source が ontology の
  backing テーブルだけを公開すること、Ontology の source が 10 の Entity Type すべてを
  公開すること、そしてガイドがその 3 つの要素数を明記していること。
* **hold-out の分離** — 10 問のセクション内に実行可能な SQL/KQL/GQL が無いこと。
* **古い概念** — Eventstream、custom endpoint、Core-5、Test 100、内部 QA 資産、
  高額通知、旧バージョンへの参照が無いこと。いずれも参加者向け成果物から
  取り除かれた語であり、ここでは禁止対象として列挙しています。
* **承認済みの明確化** — `validate_docs` と同じく、重複した日が追加 100 行と重複
  グループの 200 行を別々の量として述べ（どちらの言語でも決して混同しないこと）、
  T09 が別々に照会する 3 つの source と `MunicipalityId` という照合キーを挙げ、
  T08 の設問が 95,000 という合計を主張しつつ指示対象の無い指示語を持たないこと。
  それぞれ日本語*と*英語の両方で検証します。
* **ミラー元** — フッターが 3 つの Office 配布物すべてを、ミラーした SHA-256 とともに
  挙げること、それらのダイジェストがディスク上のファイルと今も一致すること、
  ミラーした文書が pin された Word の構造的合計値を再現すること。
* **Runtime V2 契約** — 5 つの KQL 管理コマンド（`payload-manifest.json` と相互検査）、
  廃止された `DonationObservationsForAgent` /
  `ProjectDonationObservationsForAgent` への参加者向け参照が無いこと、15 の
  Relationship カーディナリティがすべて存在し文書化されていること、ガイドが挙げる
  返礼品がすべて現行 runtime の名前を持つこと、高額の例が Activator と結び付けられて
  いないこと。
* **レビュー済みの回帰** — 可読性レビューの各指摘は注記ではなく常設の検査です。
  最初の増分ファイルは 1 度だけアップロードされ取り込み済みと明記されること、
  Notebook 02 に関する「件数が一致しない」という主張が「書き込みは行われない」という
  記述なしに現れないこと、`10 + 72 + 0 + 15` という前提条件の合計が登録結果として
  提示されないこと、すべての `第 N 章`／`第 N.M 節` の相互参照が解決すること、
  メトリックのインスタンス数が組み合わせの上限に対する観測済みの組として説明される
  こと、3 つの stale-lease パラメーターが名指しされ Notebook 01 に限定されること、
  判断ツリーが説明されるすべての箇所で 7 ステップで一致すること、第 17.11 節が
  source の*指示*より先に source の*選択*を切り分け、curated view と raw テーブルの
  両方を名指しすること。
* **図** — 想定される図、画面写真、図版の数。すべての図にキャプションがあること。
  すべての画像に代替テキストがあること。すべての画像が `data:` URI であること。
  すべての図版が `<title>`／`<desc>` を持つこと。すべての図がキーボード操作可能な
  ライトボックスボタンを開くこと。廃止した画面写真が埋め込まれていないこと。
  各図版がサニタイズ後に現行の `docs/assets/v2.7.0` の SVG とバイト単位で一致すること。
  そして、このページが割り当てるキャプション番号と競合する `図 n`／`Diagram n` の
  ラベルを図版自身が焼き込んでいないこと。
* **テーブル** — テーブルごとにキャプション 1 つ、すべてのヘッダーセルに `scope`、
  テーブルごとにラベル付きでフォーカス可能なスクロール領域。
* **オフライン** — 外部 `src` が無いこと、スタイルシートのリンクが無いこと、
  `@import` が無いこと、リモート CSS url が無いこと、Web フォントが無いこと。
  ドキュメントへのハイパーリンクは一次情報の 3 ホスト（`learn.microsoft.com`、
  `azure.microsoft.com`、`www.microsoft.com`）のみ。
* **提供されたプレビュー資料** — 付録 C.6 と付録 D.6 が日英どちらにも存在すること。
  D.6 が held-out のテスト ID・判定値・runtime パラメーターを参照しないこと。
  未公開のモード名、機密表示、「プレビュー中は無償」、EU Data Boundary の準拠主張、
  未公開の上限値、明示的な同意によるテレメトリの主張が、どちらの言語にも
  現れないこと。対話の保持を述べる文が日数を含まないこと。D.6 のライフサイクル図が
  埋め込まれていること。参照 URL の集合が Word ガイドと一致し `/en-us/` 形式で
  あること。命名規則と手動でのグラフモデル更新がミラーされていること。
* **Data Agent の実務** — 第 16.6.1・16.8・17.12・18.2 節と付録 C.7・D.7 の記述が
  日英どちらにも存在すること。文字数上限と KQL の例パターンの説明が、
  どちらの言語でも製品全体の主張に戻っていないこと。設定に関する 4 つの節が
  held-out のテスト ID・判定値・runtime パラメーターを参照しないこと。
* **コントロールと状態** — すべてのボタンにラベル、検索ボックスにラベル、すべての
  チェックリストのチェックボックスにラベル、モーダルダイアログ 1 つ、進捗メーター 1 つ、
  想定される形の一意なチェックリスト id、バージョン付きの `localStorage` キー、
  旧版の完了状態を取り込まないこと。
* **CSS/JS の健全性** — インラインスクリプトがちょうど 2 つとインラインスタイルが 1 つ、
  波括弧の対応、`document.write` が無いこと、`eval` が無いこと、印刷、動きの抑制、
  ハイコントラスト、focus-visible、言語切替、日本語の行分割、見出しの均衡の各ルールが
  存在すること。
* **サイズ** — GitHub の 100 MB ファイル上限を下回ること。

### 対話テスト

```powershell
python .\tools\html\tests\test_interaction.py `
  --target (Join-Path $PairCheck 'furusato-workshop-v2-7-0-complete_unified-20260914.html') `
  --artifacts $Review
```

ヘッドレス Chromium が build 済みファイルを操作します。コンソールエラーもページ
エラーも無く読み込むこと、言語の既定値／切替／永続化、強調表示とキーボード操作を
伴う検索ヒット、チェックリストの永続化、再読み込み時の復元とリセット、旧版の言語
設定の移行と完了状態を取り込まないこと、コピーのフィードバックとクリップボードの
内容、ライトボックスの開閉・Escape・フォーカス復帰、目次のナビゲーションと現在
セクションの表示、読書進捗、トップへ戻る、すべて展開／折りたたみ、幅の広い
テーブルでの固定行ヘッダーとスクロールヒント、言語切替の時間予算、
1440／1024／768／390 px での横方向オーバーフローが無いこと、モバイルのドロワー、
そして印刷メディア（chrome を隠す、図とテーブルを保つ、Optional を展開する、
有効な言語だけを印刷する）を検証します。

受入条件は `0 failed` で、`$Review` はペア外の非公開記録先です。件数・機能・性能・印刷の結果は
今回の実測で別々に残します。旧 `deployment-review-20260905` の 803 ms／500 ms 未達は
別成果物の履歴であり、最新版の測定ではありません。現行版にも同じ 500 ms ゲートと
82 項目の検査を適用し、後の再実行にも同じ上限を使います。

このうち 3 つは、静的解析では決着しない主張を検査するため、特筆に値します。

* **オフラインは推測ではなく証明される。** `offline.noSubresourceRequests` は
  ブラウザーが行うすべてのリクエストを記録し、唯一のリクエストが文書自身であることを
  表明します。マークアップ内の外部 URL を禁止するだけでは CSS の `@import` や
  実行時の `fetch` を見逃しますが、この方法は見逃しません。
* **検索は表示中の言語に限定される。** 両言語が DOM に存在するため、
  `search.activeLanguageOnly` は日本語にしか存在しない語を検索し、英語表示中は
  ヒットが 0 件であることを要求します。その探索語が日本語専用であることは先に
  検証します（`search.probeIsJapaneseOnly`）。多くの日本語は英語テキストの中にも
  正当に現れます。`寄付者、寄附者、支援者、納税者` のような Ontology のシノニム
  一覧や、貼り付けた ［UI ラベル］ は両言語で同一であり、それらに一致するのは
  漏れではなく正しい動作です。
* **印刷されるダイジェストは DOM ではなく PDF で検査する。** `print.pdf.*` は両言語で
  実際の A4 PDF を描画し、64 文字のダイジェストがすべて抽出テキストに欠けずに現れる
  ことを要求します。DOM の測定ではこれを決着できません。付録 B の 5 つのダイジェストが
  紙面上で切り詰められていたにもかかわらず `scrollWidth` はオーバーフローを報告して
  いませんでした。テーブルが印刷可能領域より広く、ページ分割器が最後の列を切り落として
  いたためです。ダイジェストは ASCII なので、周囲の日本語がサブセットフォントを
  使っていても確実に抽出できます。pypdf の既定モードを意図的に使っています。
  `extraction_mode="layout"`、pdfplumber、PyMuPDF はいずれもここで測定し、回収できる
  ダイジェストが少なくなりました。

#### 意図的なトレードオフ

* **図番号の所有者は 1 つ。** `figcaption` が `図 n / Figure n` を割り当てます。
  図版が自身の番号を絵に焼き込んだ場合、インライナーはその字句を図版のテキスト
  ノードから取り除き（保守的に、単独で立っているか区切り文字が続く場合だけなので、
  `15 リレーションシップ` のような件数、`v2.7.0` のようなバージョン、
  `PrefectureId 45` のような id は影響を受けません）、残っていれば
  `figures.noBakedFigureNumber` が失敗します。現行の図版に対してこの除去処理は
  何もしません。
* **コードと設問のコールアウトは印刷時に不可分。** すべての `.codeblock` と
  `.callout` が `break-inside: avoid` を宣言します。A4 の正確な本文領域
  （688 x 1002 px）で測定したところ、89 ブロック中 88 が 1 ページに収まり
  （最も高いものでページの 79%）、エンジンはそれらを分割できません。唯一の例外である
  4,965 文字の Agent instructions 全文はページの 207% に達するため、折り返し後の
  行数から build 時に検出して `data-long` を付け、1 行だけで黙って分割される代わりに
  `orphans`／`widows` を 4 として流し込むことを許します。
* **日本語のタイポグラフィは仮定ではなく測定する。** `line-break: strict` は小書きの
  仮名、長音記号、閉じ括弧類が行頭に来ないようにします（行頭禁則）。対話テスト一式は
  折り返されたすべての日本語テキスト run を `Range` で走査し、実際の行頭違反を
  数えます。ブラウザー既定では 17 件、`strict` では 1,136 の折り返し run に対して
  **0** 件でした。見出しは `text-wrap: balance`、本文は `text-wrap: pretty` を使います。
  これは Word 版に施した「間の空いたページ」の仕上げに相当する CSS です。
* 両言語を DOM に残し、CSS で片方を隠します。これにより JavaScript を無効にしても
  ページが機能し、ブラウザーのページ内検索が正直に働き、支援技術に対して 1 つの
  セマンティックツリーを保てます。代償は切替時のフルスタイル再計算です。章への
  `content-visibility: auto` は測定し（切替 148 ms → 24 ms）**却下**しました。
  これほど不揃いな章では固有サイズの推定が大きく外れ、報告される文書高さがほぼ
  半分になり、アンカーのナビゲーションが目的の見出しから数千 px 離れた場所に
  着地するためです。
* 画面写真は可逆 WebP として埋め込みます。元の PNG とピクセル単位で同一のまま、
  おおよそ半分のサイズになります。単一ファイルで 17 MB と 10 MB の差です。

成果物は指定したディレクトリにだけ書き出され、リポジトリには何も残りません。

### 必要なもの

WebP エンコードと英語図版のフォント計測のための `Pillow` と、`tools/docs` が import するための
`python-docx`。`playwright`（および `python -m playwright install chromium`）は
対話テストにのみ必要です。

---

## English

The latest HTML is
[furusato-workshop-v2-7-0-complete_unified-20260914.html](../../docs/furusato-workshop-v2-7-0-complete_unified-20260914.html),
a complete Japanese/English mirror of the
[same-edition participant Word](../../docs/Fabric_IQ_Ontology_Workshop_Furusato_Participant_v2.7.0_unified-20260914.docx)
in one self-contained file. Only this pair is the current document download set.
The validated pair is installed under these names.

The matching Word uses unified profile revision13. Both languages synchronize
answerable rephrasing, consent, reconfirmation and cancellation, alongside source,
selected-gift wording, original field/provenance retention,
rank-scope, KQL and CI checks. Obsolete configuration images are excluded; a genuine
CI interaction illustration retains its original provenance and is reused only
with matching CI instructions/settings, not as new configuration or evaluation proof.

The Word guide is the source of truth. This toolchain does **not** re-author
its prose: it runs the *same* chapter builders that produce the DOCX against a
capturing builder, so the HTML carries the identical content model — every
heading, paragraph, list, callout, code block, table, figure and caption, in
document order. English is supplied by a maintained mirror keyed on the exact
Japanese string, so the two languages cannot drift apart silently.

### Public-pair mode

The default three Office hashes/downloads are internal authoring, not current downloads.
First build the same-edition participant Word in fresh external PRIVATE `$Stage`, then
generate HTML there. Stop on each nonzero exit:

```powershell
$Edition = 'unified-20260914'
python .\tools\html\sync_i18n.py --public-documents-only --edition $Edition
python .\tools\html\build_html.py --public-documents-only --edition $Edition --out $Stage
python .\tools\html\validate_html.py --public-documents-only --edition $Edition --out $Stage
```

The output directory must match the staged Word. Validation/export use an external
directory containing exactly the two files. Repository `docs` also holds assets/checklist
and is invalid input. After installation, copy only the two files to fresh external
staging and prove source-before/source-after/copy hash equality; do not bypass path checks.
Exactly one
download and one provenance entry use that Word's actual filename and byte hash.
There is no companion/old-edition fallback and `--release-digest` is rejected.
Every chapter, the original ten questions / 84 rubric requirements, recording guidance and
all parameters remain; `i18n/public-documents.json` explicitly replaces only
publication/companion wording. Both modes retain strict missing/unused translation checks.
Public-mode drift reporting is read-only; `--prune` and `--rewrite` are rejected.

Both PowerShell wrappers support `-PublicDocumentsOnly -Edition ... -Out ...`.
Finalization requires the edition's `-ParticipantSha` and all five structural counts,
not companion hashes. Derive pins from the actual reviewed Word, not older fixed values or
the HTML's own counts. `Finalize-Html.ps1` creates HTML: it is an alternative build step
in fresh Word-only staging, not read-only revalidation of an existing/installed pair.
Put interaction artifacts and reports outside `-Out`. Existing
HTML is never overwritten; rebuild in fresh staging. The [export tool](../publication/README.md)
rechecks the exact two-file allowlist and bytes. That document also covers the complete
build, Word render, hash/shape pin, browser/print and separate fresh external-pair export
sequence. Wait for configuration, results and
captures to freeze before complete builds. Follow the [capture handoff](../docs/README.md)
for private originals, disclosed crop/redaction and approval; do not reuse old screens
as proof of a changed configuration or replace current assets before approval.
The released `unified-20260914` pair synchronizes one primary Agent, the complete
teaching Ontology, shared SQL/KQL helpers and same-Agent Code Interpreter exercises.
Two obsolete instruction screenshots are omitted; accurate existing captures are reused.
Three required new views were captured through the authenticated Fabric Web UI
and included in Word/HTML without post-capture pixel edits.
Work logs, live backups and detailed execution records stay outside
the distributable repository. Quality acceptance is separate from deployment/
document readiness; see [Data Agent response checks](../../docs/single-agent-workshop.md).
Keep notebooks, data, code, diagrams and style assets. This distribution uses fresh
public-only history without former private history or evidence. An HTML build does
not authorize hosting or visibility changes. Never merge/push private archive history
here; follow [SECURITY.md](../../SECURITY.md).

### Prerequisites

- Python 3 and `tools/html/requirements.txt`.
- `Pillow` (for WebP encoding and English-diagram font measurement) and `python-docx` (because `tools/docs` imports
  it).
- `playwright` (plus `python -m playwright install chromium`) only for the
  interaction tests.
- The shipped `workshop/v2.7.0` runtime, `docs/assets/v2.7.0` and
  `tools/docs/assets/style-carrier.zip`.

### Layout

```
tools/html/
  build_html.py              entry point: build the deliverable
  validate_html.py           entry point: validate it (exit 1 on FAIL)
  sync_i18n.py               maintenance: report mirror drift after a Word change
  Build-Html.ps1             PowerShell wrapper (build + validate + interaction)
  Finalize-Html.ps1          pinned finalization (drift, build, validate, interaction)
  requirements.txt
  assets/
    app.css                  the Fabric IQ house style, inlined at build time
    app.js                   the behaviour layer, inlined at build time
  furusato_html/
    capture.py               duck-types DocumentBuilder and records the model
    mirror.py                Japanese -> English lookup with loud failures
    model.py                 bilingual section tree, ids, checklist derivation
    assets.py                single-embedding SVG/WebP inliner
    diagrams.py              derives the English SVG variants at build time
    render.py                block and section rendering
    page.py                  page shell: head, chrome, cover, contents, footer
    i18n/
      GLOSSARY.md            translation rules and glossary
      guide-*.json          the guide mirror, split into numbered files for reviewability
      public-documents.json explicit public-mode wording changes only
      diagrams.json          the diagram-label mirror
      ui.json                chrome, control and status strings
  tests/
    test_interaction.py      headless Chromium interaction tests
```

### Sources of truth

| Value | Read from |
|---|---|
| Content model (chapters 1-19, appendices A-E) | `tools/docs/furusato_docs/{participant_guide,guide_handson,guide_agent}.py` |
| Counts, amounts, windows, hashes, parameters, tests | the shipped `workshop/v2.7.0` runtime, through `furusato_docs.context` / `facts` / `parameters` / `tests10` |
| Diagrams | `docs/assets/v2.7.0/*.svg`, inlined as sanitized SVG |
| Fabric UI screenshots | `tools/docs/assets/style-carrier.zip`, re-encoded as lossless WebP |
| English text | `furusato_html/i18n/guide-*.json` and `ui.json` |

Public mode resolves only the same-edition participant Word in staging, with no old-file
fallback. Retain runtime, diagrams and the style carrier. Old Office/HTML belongs in
private archive/history, not back in release HEAD as a rebuild dependency.

### Separate latest-only and internal authoring modes

Use `--public-documents-only --edition unified-20260914` for both latest Word and
HTML. `source.downloadEdition` rejects mixed editions. An edition identifies an artifact,
not Fabric quality acceptance. Do not use edition-free/output-free compatibility
defaults; rebuild in fresh staging.

Full Office authoring remains available through [tools/docs](../docs/README.md) with a
named edition and external PRIVATE staging. However, the existing **full-authoring HTML**
path resolves Office inputs under repository `docs`; `--out` changes only its HTML
destination. That path is not the public workflow in a latest-only checkout. If needed,
use it only in a separate private authoring tree containing a complete same-edition Office
set; do not restore companions or old files to release HEAD to satisfy it. Always supply
a fresh private HTML output directory and named edition. Its internal `Finalize-Html.ps1`
path needs all three Office hashes and all five structural totals.
Never pass `-TestRecordSha` / `-WorkbookSha` to the public path.

### Build

```powershell
python .\tools\html\build_html.py --public-documents-only --edition unified-20260914 --out $Stage --json
```

`$Stage` must hold only the reviewed same-edition participant Word; do not rebuild where
HTML already exists. Keep saved JSON reports in `$Review`, outside the pair. The build is deterministic:

* no wall-clock time enters the output — the recorded build fingerprint is a
  digest of the runtime input digests plus the `tools/html` source digests;
* every image is embedded exactly once and a duplicate source is a hard error;
* the file is written atomically through a temporary file in the target folder.

It fails instead of emitting a drifted deliverable when:

* a captured Japanese string has no English mirror,
* a mirror entry is no longer used by the content model,
* an English value still looks untranslated,
* the canonical `DocumentBuilder` grows a member the capture does not model,
* `VERSION` no longer matches the release this source tree targets.

After Word changes, run read-only `sync_i18n.py` drift checks in both modes.
Normal-mode `--prune` / `--rewrite` are mutating translation-maintenance operations,
not part of this release check:

```powershell
python .\tools\html\sync_i18n.py
python .\tools\html\sync_i18n.py --public-documents-only
```

### Validate

`$PairCheck` is the external exact two-file directory prepared by the
[pair procedure](../publication/README.md). `$WordSha` and `$Shape` are values
established by reviewing the actual Word.

```powershell
$Edition = 'unified-20260914'
python .\tools\html\validate_html.py --public-documents-only --edition $Edition --out $PairCheck `
  --expect-source "Fabric_IQ_Ontology_Workshop_Furusato_Participant_v2.7.0_${Edition}.docx=$WordSha" `
  --expect-shape "chapters=$($Shape.chapters)" --expect-shape "headings=$($Shape.headings)" `
  --expect-shape "tables=$($Shape.tables)" --expect-shape "figures=$($Shape.figures)" `
  --expect-shape "tests=$($Shape.tests)"
```

`--expect-source` pins the digest of an Office deliverable the HTML must have
mirrored, and `--expect-shape` pins the Word structural totals the mirror must
reproduce (`chapters`, `headings`, `tables`, `figures`, `tests`). Together they
turn "this mirrors the final guide" from an assertion into a check: a mirror
built from a superseded content model fails instead of shipping. Note that Word
rewrites a DOCX package every time it refreshes fields and repaginates, so a
deliverable's byte digest changes even when its content does not — the footer
records the digest that was actually mirrored and `source.matchesDisk` re-reads
the files to prove the HTML is not stale.

Acceptance requires `0 failed`. Record counts and measurements for this edition;
do not reuse historical results. Add `--json` if needed, keeping output outside the pair.
As an alternative fresh build, `Finalize-Html.ps1` requires
`-PublicDocumentsOnly -Edition unified-20260914 -Out $Stage -ParticipantSha $WordSha`,
that Word's `-Chapters`, `-Headings`, `-Tables`, `-Figures`, `-Tests`, and external
`-Artifacts`. Use the validator above for an existing pair's read-only revalidation.

#### Bilingual diagram artwork

The seven diagrams under `docs/assets/v2.7.0` are authored in Japanese. Switching
the page to English used to leave a Japanese picture under an English caption, so
`furusato_html/diagrams.py` derives an English variant of each SVG at build time
from `i18n/diagrams.json` (297 labels). The shipped assets are never modified:
they remain the Japanese source of truth, `diagrams.fresh` still proves the
Japanese artwork is byte-identical to disk, and both variants live inside the
same `<figure>` with only the active language displayed.

Three properties of the artwork shaped the implementation, and each was found by
looking at the SVGs rather than assumed:

* **The original Japanese artwork wraps long labels by hand across sibling
  `<text>` elements**, with no `tspan`. Generated English artwork is different:
  it uses `tspan` when extra wrapped lines are needed. Translating the originals
  line by line produced fragments such as
  `を辿る。`, so lines that share an x coordinate and font size and step down by
  about one line height are joined, translated as one sentence, and re-wrapped.
* **Some headings already carry the author's own English.** Those are reused
  rather than re-translated, and the duplicate is removed by comparing the text
  actually produced against the neighbouring line. An earlier version guessed
  from position and type size and got it wrong in both directions: one diagram
  sets its translation *smaller* than the Japanese, another sets it *larger*, and
  a third follows a description with the next item's heading, which merely looks
  like a translation. Comparing content is the only rule that holds for all six.
* **English can require more lines than the Japanese it replaces.** Capping the
  wrap at the original line count lets the final line spill into its neighbour.
  The generator instead measures installed fonts with Pillow and wraps `tspan`
  lines within the label's owning shape. It neither globally shrinks type nor
  drops text. Small label backplates grow only where necessary and within
  limited bounds; connector paths and arrow definitions stay unchanged.

Reproducing English artwork also depends on font selection and metrics. Use the
same font versions and Pillow/FreeType for comparison builds, check output
SHA-256 values, and measure label containment in the browser. When available,
metrics use Yu Gothic UI Regular/Bold, TTC face 1; fallback selection is Meiryo,
Segoe UI, DejaVu Sans, then Arial. Missing every supported font is an explicit
failure. Generated SVGs put the measured family first and retain the original
fallback stack. Neither font files nor host paths are embedded. If a reader uses
a fallback font, revalidate containment in that target environment.

`diagrams.englishArtworkIsEnglish` fails on any Japanese left visible in the
English variant apart from an explicit allowlist of proper nouns, and the build
itself refuses to emit a diagram whose labels are not all mapped.

#### Layout-only Office reissues

This is a full-authoring compatibility feature for a separate private authoring tree
only. **Public pairs reject `--release-digest`.** If Word bytes change, rebuild HTML
in fresh external staging and validate the actual hash; do not restamp only its footer.

Sometimes Word is reissued purely to fix pagination: text, tables and runtime are
identical, only the DOCX bytes move. Re-mirroring is pointless, but the footer
should still name the digest people were given. `--release-digest` does that, and
`--content-fingerprint` keeps it honest:

Even on this internal path, explicitly supply a named edition and a fresh external
PRIVATE output directory. `--release-digest NAME=SHA256` uses the actual same-edition
target name, and `--content-fingerprint` uses the reviewed value. Do not resolve old
release-HEAD files or implicit defaults.

The content fingerprint hashes the captured content model alone — no assets, CSS,
JS or Office digests — so it is invariant under repagination and moves the instant
a word changes. The build refuses if it does not match, and refuses
`--release-digest` outright without it, so "layout only" is verified rather than
believed. The footer then carries both digests: the release digest people cite,
and the digest actually on disk, labelled as a layout-only reissue in both
languages. `source.layoutReissue` reports which files are in that state and
`source.matchesDisk` compares disk against the observed digest, so a genuinely
stale mirror still fails. The build's `--json` report prints `contentFingerprint`.

#### Checks performed

* **Markup** — parses with a strict tag-stack reader, one `<!DOCTYPE html>`, one
  `html`/`head`/`body`/`main`/`footer`, expected prologue and epilogue.
* **Structure** — 24 top-level sections numbered 1-19 then A-E, ordered heading
  levels with no skips, unique element ids, every internal anchor and every
  `aria-controls`/`aria-labelledby` reference resolves.
* **Bilingual parity** — every Japanese span has an English sibling under the
  same parent, both carry the right `lang`, neither is empty, no mirror entry is
  orphaned and no English value is still Japanese.
* **Runtime facts** — counts, amounts, observation window, per-file rows and
  amounts, run ids, publication times, JST rollover, node/edge totals, metadata
  object count, all entity and relationship names, all 43 notebook parameters,
  all 10 held-out tests, and 31 distinct August dates.
* **Data Agent** — the global instructions verbatim plus their character count,
  byte count and SHA-256; every source description; the Lakehouse and Kusto
  source instructions; that the Ontology source carries a description only; both
  three SQL few-shots verbatim; at least two curated-view KQL shapes; and, from the
  provisioning bundle, that the Eventhouse source exposes **only**
  `DonationObservationSummaryForAgent` (never the raw event table), the Lakehouse
  source exposes exactly the ontology-backing tables, the Ontology source exposes
  all ten entity types, and the guide states those three element counts.
* **Held-out isolation** — no executable SQL/KQL/GQL inside the ten-test
  section.
* **Stale concepts** — no Eventstream, custom endpoint, Core-5, Test 100,
  internal QA asset, high-value notification or superseded-version reference.
  Each of these was removed from the participant materials; they are listed here
  as the banned terms.
* **Approved clarifications** — mirroring `validate_docs`: the duplicated day
  states the 100 extra rows and the 200 duplicate-group rows as distinct
  quantities (and never conflates them, in either language), T09 names all three
  separately queried sources plus the `MunicipalityId` reconciliation key, and
  the T08 question carries no unbound demonstrative while asserting the 95,000
  total — each verified in Japanese *and* English.
* **Mirrored source** — the footer names all three Office deliverables with the
  SHA-256 that was mirrored, those digests still match the files on disk, and
  the mirrored document reproduces the pinned Word structural totals.
* **Runtime V2 contract** — five KQL management commands (cross-checked against
  `payload-manifest.json`), no participant-facing reference to the retired
  `DonationObservationsForAgent` / `ProjectDonationObservationsForAgent`, all
  fifteen relationship cardinalities present and documented, every gift the
  guide names carries its current runtime name, and the high-value example is
  never tied to Activator.
* **Reviewed regressions** — each finding from the readability passes is a
  standing check rather than a note: the first increment file is uploaded once
  and marked already-ingested, a "the count will not match" claim about
  Notebook 02 never stands without the zero-write statement, the
  `10 + 72 + 0 + 15` precondition total is never presented as a registration
  result, every `第 N 章` / `第 N.M 節` cross-reference resolves, the metric
  instance counts are explained as observed pairs against the combinatorial
  ceiling, the three stale-lease parameters are named and scoped to Notebook 01,
  the decision tree agrees on seven steps everywhere it is described, and
  chapter 17.11 triages source *selection* before source *instructions* while
  naming both the curated view and the raw table.
* **Figures** — expected figure, screenshot and diagram counts; every figure has
  a caption; every image has alt text; every image is a `data:` URI; every
  diagram carries `<title>`/`<desc>`; every figure opens a keyboard-operable
  lightbox button; no retired screenshot is embedded; each diagram matches the
  current `docs/assets/v2.7.0` SVG byte for byte after sanitizing; and no
  diagram carries its own baked-in `図 n` / `Diagram n` label, which would
  compete with the caption numbering this page assigns.
* **Tables** — a caption per table, `scope` on every header cell, and a labelled,
  focusable scroll region per table.
* **Offline** — no external `src`, no stylesheet link, no `@import`, no remote
  CSS url, no web font; documentation hyperlinks only to the three first-party
  Microsoft hosts (`learn.microsoft.com`, `azure.microsoft.com`,
  `www.microsoft.com`).
* **Supplied preview material** — appendix C.6 and appendix D.6 survive the
  mirror in *both* languages; D.6 names no held-out test id, verdict or runtime
  parameter; no unpublished mode label, confidentiality marking,
  free-during-preview claim, EU Data Boundary conformance claim, unpublished
  ceiling or explicit-consent telemetry claim appears in either language; no
  conversation-retention sentence carries a duration; the D.6 lifecycle diagram
  is embedded; the reference URL set matches the Word guide and keeps the
  `/en-us/` form; the naming rule and the manual graph-model refresh are mirrored.
* **Data Agent practice** — sections 16.6.1, 16.8, 17.12 and 18.2 and appendices
  C.7 and D.7 survive the mirror in *both* languages; neither language restores
  the superseded product-wide claim about the character budget or about where
  the KQL shapes live; the four configuration sections name no held-out test id,
  verdict or runtime parameter.
* **Controls and state** — every button labelled, the search box labelled, every
  checklist checkbox labelled, one modal dialog, one progress meter, unique
  checklist ids in the expected shape, the versioned `localStorage` key, and no
  import of superseded completion state.
* **CSS/JS sanity** — exactly two inline scripts and one inline style, balanced
  braces, no `document.write`, no `eval`, and the presence of the print,
  reduced-motion, high-contrast, focus-visible, language-toggle, Japanese
  line-breaking and balanced-heading rules.
* **Size** — below the 100 MB GitHub file limit.

### Interaction tests

```powershell
python .\tools\html\tests\test_interaction.py `
  --target (Join-Path $PairCheck 'furusato-workshop-v2-7-0-complete_unified-20260914.html') `
  --artifacts $Review
```

Headless Chromium drives the built file: load without console or page errors,
language default/toggle/persistence, search hits with highlighting and keyboard
navigation, checklist persistence, reload restore and reset, migration of the
old language preference *without* importing old completion, copy feedback and
clipboard content, lightbox open/escape/focus restore, table-of-contents
navigation and current-section indicator, reading progress, back-to-top, expand
and collapse all, the sticky row header and scroll hint on wide tables, a
language-toggle time budget, no horizontal overflow at 1440/1024/768/390 px, the
mobile drawer, and print media (chrome hidden, figures and tables kept, Optional
expanded, only the active language printed).

Acceptance requires `0 failed`; `$Review` is a private report directory outside the pair.
Record actual counts, functionality, performance and print results separately.
The historical `deployment-review-20260905` miss of 803 ms against 500 ms belongs to
a different artifact, not the latest measurement. Apply the same 500 ms gate and
all 82 checks to the current pair, and retain that limit for subsequent runs.

Three of these deserve a note because they check claims that static analysis
cannot settle:

* **Offline is proved, not inferred.** `offline.noSubresourceRequests` records
  every request the browser makes and asserts the only one is the document
  itself. Banning external URLs in the markup misses a CSS `@import` or a
  runtime `fetch`; this does not.
* **Search is scoped to the visible language.** Both languages live in the DOM,
  so `search.activeLanguageOnly` searches a Japanese-only term and requires zero
  hits while English is shown. The probe term is verified Japanese-only first
  (`search.probeIsJapaneseOnly`): a lot of Japanese legitimately appears inside
  English text — Ontology synonym lists such as `寄付者、寄附者、支援者、納税者`
  and pasted ［UI ラベル］ are identical in both languages — and matching those
  is correct behaviour, not a leak.
* **Printed digests are checked in the PDF, not the DOM.** `print.pdf.*` renders
  real A4 PDFs in both languages and requires every 64-character digest to appear
  intact in the extracted text. A DOM measurement cannot settle this: five
  Appendix B digests were reaching paper truncated while `scrollWidth` reported
  no overflow, because the table was wider than the printable area and the
  paginator sliced the last column off the page. The digests are ASCII, so they
  extract reliably even though the surrounding Japanese uses a subset font.
  pypdf's default mode is used deliberately: `extraction_mode="layout"`,
  pdfplumber and PyMuPDF were all measured here and recover fewer digests.

#### Deliberate trade-offs

* **Figure numbering has one owner.** The `figcaption` assigns `図 n / Figure n`.
  If a diagram ever bakes its own number into the artwork, the inliner strips
  that token from the diagram's text nodes (conservatively: only where it stands
  alone or is followed by a separator, so counts such as
  `15 リレーションシップ`, versions such as `v2.7.0` and ids such as
  `PrefectureId 45` are untouched) and `figures.noBakedFigureNumber` fails if one
  survives. Against the current diagrams the stripper is a no-op.
* **Code and question callouts are atomic in print.** Every `.codeblock` and
  `.callout` declares `break-inside: avoid`. Measured at exact A4 content
  geometry (688 x 1002 px), 88 of 89 blocks fit inside one page — the tallest of
  them at 79% — so the engine cannot split them. The one exception, the full
  4,965-character Agent instructions at 207% of a page, is detected at build
  time from its wrapped line count, marked `data-long`, and allowed to flow with
  `orphans`/`widows` of 4 rather than splitting silently after one line.
* **Japanese typography is measured, not assumed.** `line-break: strict` keeps
  small kana, the prolonged sound mark and closing punctuation off the start of
  a line (行頭禁則). The interaction suite walks every wrapped Japanese text run
  with a `Range` and counts real line-start violations: 17 under the browser
  default, **0** with `strict` across 1,136 wrapped runs. Headings use
  `text-wrap: balance` and body text `text-wrap: pretty`, which is the CSS
  equivalent of the sparse-page polish applied to the Word edition.
* Both languages stay in the DOM and CSS hides one. That keeps the page working
  with JavaScript disabled, keeps browser find-in-page honest and keeps a single
  semantic tree for assistive technology, at the cost of a full style recalc on
  toggle. `content-visibility: auto` on chapters was measured (toggle 148 ms →
  24 ms) and **rejected**: with chapters this uneven the intrinsic-size estimate
  is far off, the reported document height nearly halves and anchor navigation
  lands thousands of pixels from the target heading.
* Screenshots are embedded as lossless WebP, which is pixel-identical to the
  source PNG at roughly half the size — the difference between a 17 MB and a
  10 MB single file.

Artifacts are written only to the directory you pass; nothing lands in the
repository.

### Requirements

`Pillow` for WebP encoding and English-diagram font measurement, and `python-docx`
because `tools/docs` imports it.
`playwright` (plus `python -m playwright install chromium`) only for the
interaction tests.
