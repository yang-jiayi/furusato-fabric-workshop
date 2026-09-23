# Public document pair / 公開文書ペア

This tool prepares files; it does **not** publish to GitHub or change repositories,
visibility, history, hosting, runtime, code or data. A clean document export does not
make old repository history safe to publish. This distribution uses fresh public-only
history; former private commits, tags, Releases and evidence are not imported.
The document-export procedure itself does not authorize hosting or visibility changes.
Follow [SECURITY.md](../../SECURITY.md); never merge or push private archive history here.

このツールはファイルの検証と複製だけを行います。GitHub の公開範囲・履歴・hosting は変更しません。
この配布版は公開用の新規履歴を使い、旧 Private のコミット・タグ・Release・証跡は取り込みません。
HEAD の旧ファイルを除くだけでは過去の情報は秘匿化されません。文書 export 自体は hosting や
公開範囲の変更を承認しません。[SECURITY.md](../../SECURITY.md) に従い、旧履歴を merge／push しないでください。

## Latest-only inventory / 最新版だけの文書一覧

For version `2.7.0` and edition `unified-20260923`, the release document pair is:

1. [Participant Word](../../docs/Fabric_IQ_Ontology_Workshop_Furusato_Participant_v2.7.0_unified-20260923.docx)
2. [Matching bilingual HTML](../../docs/furusato-workshop-v2-7-0-complete_unified-20260923.html)

This correction synchronizes formal Activator first-start/stop, single complete-file
PutBlob uploads and separate native event/activation/job/Copy/KQL checks across all
public entry points. The dataset, full Ontology, Agent profile revision13 and original
ten questions/84 conditions are unchanged. Historical private diagnostic evidence is
not part of the release.

The validated pair is installed under `docs`. The eight former HEAD Office/HTML artifacts
and the immediately preceding Word/HTML pair were archived privately byte-for-byte;
superseded documents are no longer current downloads. Preserve
notebooks, data, code, diagrams, the checklist and style assets. Old artifacts remain
in the private archive/history, not as current downloads.

The current participant Word and bilingual HTML synchronize profile revision13,
including rephrasing, consent, correction/reconfirmation and cancellation.
Selected-gift wording and preservation of native field names/provenance are also synchronized.
The original ten questions/84 conditions remain intact. Obsolete instruction
screenshots are excluded; the genuine CI illustration keeps its original provenance.
Instruction-driven behavior is not claimed as enforced or universally reliable.

最新版は上の参加者 Word と対応する日英 HTML の 2 点で、検証済みペアを `docs` へ配置しています。
旧 HEAD の Office/HTML 8 点と直前版の Word／HTML を非公開にバイト一致で退避し、
現行ダウンロードは検証済みの新ペアだけに揃えています。
Notebook・データ・コード・図版・チェックリスト・style 資産は保持します。
旧文書は非公開アーカイブ／履歴で保持し、現行ダウンロードにはしません。

現行ペアは profile revision 13 の言い直し・同意待ち・訂正時の再確認・取消を同期した
参加者 Word と日英 HTML です。元の10問・84条件を維持し、古い指示画像は掲載しません。
実UIのCI操作例は撮影時の来歴を保持し、指示による動作を強制制御や常時成功とは扱いません。
返礼品の選択と受領の区別、元の返却列名・出典を保持する確認も同期しています。

The existing naming rule is unchanged: append `_<edition>` immediately before the
extension; HTML replaces version dots with hyphens. No additional `public` suffix or
renaming occurs. Edition must be nonempty, at most 40 characters, using lowercase
letters/digits separated by hyphens/underscores.

No older Word/HTML, validation-record Word, XLSX, ZIP, README, hash manifest, screenshot
directory or runtime bundle belongs in this two-file directory. The entire participant
guide stays: 19 chapters, five appendices, the original ten questions / 84 rubric
requirements, recording guidance and all parameter specifications. Public-mode recording
instructions replace mandatory companion references.

外部のペア用ディレクトリには上の正確な 2 ファイルだけを置きます。旧文書・別冊 Word・XLSX・
ZIP・README・manifest・画像・runtime は入れません。全 19 章・付録 A〜E・元の 10 問／84 要件・
記録方法・全パラメーターを参加者ガイドに保持します。

## Build, review and pin / 生成・レビュー・pin

The following is a later release procedure, not authorization to generate or publish
an unfinished candidate. Freeze the content, configuration evidence and approved captures
first. **Production-wide Data Agent quality acceptance remains unverified; finite
test outcomes are separate from deployment or document readiness.** The current pair contains
one-Agent procedures, full teaching Ontology, shared SQL/KQL helpers and same-Agent
Code Interpreter exercises, without work logs, historical scores or authoring narratives. See
[Data Agent response checks](../../docs/single-agent-workshop.md); keep detailed
execution records outside the distributable repository.

Set `$PrivateDocuments` and `$ExportRoot` to approved absolute directories **outside the
repository**. The fresh `$Stage`, fresh `$PublicPair` and `$Review` must be disjoint;
reports, raw/reviewed screenshots and hashes remain outside both two-file directories.
Never use repository `docs` as public-mode validator/exporter input: its assets and
checklist make it invalid. Do not relax the directory checks.

以下は原稿・構成証跡・承認済みキャプチャの凍結後の手順です。**本番全般の品質保証は未確認で、
有限の評価結果もデプロイや文書の準備完了とは別です。** 配布文書は主 Agent 1 件、完全な教材用 Ontology、
共有 SQL/KQL ヘルパー、同じ Agent の Code Interpreter 演習を同期し、
作業履歴・過去の採点・資料作成の経緯を含めません。
[Data Agent の回答確認](../../docs/single-agent-workshop.md)を参照し、
詳細な実行記録は配布リポジトリの外で管理します。
`$PrivateDocuments` と `$ExportRoot` は承認済みのリポジトリ外の絶対パスを指定し、
新しい `$Stage`・`$PublicPair`・`$Review` を分離します。公開モードの validator / exporter に
`docs` を直接渡してはいけません。assets と checklist を含むため、ペアの検査に適合しません。

```powershell
$Edition = 'unified-20260923'
$Run = [guid]::NewGuid().ToString('N')
$Stage = Join-Path $PrivateDocuments "stage-$Edition-$Run"
$PublicPair = Join-Path $ExportRoot "$Edition-$Run"
$Review = Join-Path $PrivateDocuments "review-$Edition-$Run"
$Hashes = Join-Path $Review "$Edition.sha256"
$WordName = "Fabric_IQ_Ontology_Workshop_Furusato_Participant_v2.7.0_$Edition.docx"
$HtmlName = "furusato-workshop-v2-7-0-complete_$Edition.html"
New-Item -ItemType Directory -Path $Review -ErrorAction Stop | Out-Null

python .\tools\docs\build_docs.py --public-documents-only --edition $Edition --out $Stage
if ($LASTEXITCODE -ne 0) { throw 'Word build failed' }
python .\tools\html\sync_i18n.py --public-documents-only
if ($LASTEXITCODE -ne 0) { throw 'Translation drift' }
$WordSha = (Get-FileHash -LiteralPath (Join-Path $Stage $WordName) -Algorithm SHA256).Hash.ToLowerInvariant()
python .\tools\html\build_html.py --public-documents-only --edition $Edition --out $Stage
if ($LASTEXITCODE -ne 0) { throw 'HTML build failed' }
python .\tools\docs\validate_docs.py --public-documents-only --edition $Edition --out $Stage --render
if ($LASTEXITCODE -ne 0) { throw 'Word validation/render failed' }
if ((Get-FileHash -LiteralPath (Join-Path $Stage $WordName) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $WordSha) {
  throw 'Word bytes changed; restart in fresh staging'
}
```

After reviewing that Word, record its five structural totals as `$Shape.chapters`,
`$Shape.headings`, `$Shape.tables`, `$Shape.figures` and `$Shape.tests`. Obtain them
from the reviewed Word and its content model, not from an older edition or the HTML
being tested. Do not invent fixed totals. Pin the actual final Word hash and all five
reviewed totals, then run browser/print checks; their reports belong in `$Review`.
Word rendering needs Office; browser checks need Chromium. Record unavailable checks
as pending, not passed. Stop at every nonzero exit.

その Word をレビューして、構造件数 5 種類を `$Shape.chapters`・`headings`・`tables`・
`figures`・`tests` として記録します。旧版の値や検査対象 HTML 自身の件数ではなく、
レビューした Word と内容モデルから求めます。最終 Word の実ハッシュと全 5 件数を pin し、
ブラウザー／印刷検査を行います。Word 描画には Office、ブラウザー検査には Chromium が必要です。
未実施は保留として残し、非ゼロ終了なら直ちに停止します。

```powershell
python .\tools\html\validate_html.py --public-documents-only --edition $Edition --out $Stage `
  --expect-source "${WordName}=$WordSha" `
  --expect-shape "chapters=$($Shape.chapters)" --expect-shape "headings=$($Shape.headings)" `
  --expect-shape "tables=$($Shape.tables)" --expect-shape "figures=$($Shape.figures)" `
  --expect-shape "tests=$($Shape.tests)"
if ($LASTEXITCODE -ne 0) { throw 'Pinned HTML validation failed' }
python .\tools\html\tests\test_interaction.py --target (Join-Path $Stage $HtmlName) --artifacts $Review
if ($LASTEXITCODE -ne 0) { throw 'Browser/print checks failed' }
python .\tools\publication\export_public_documents.py `
  --source $Stage --out $PublicPair --edition $Edition --manifest $Hashes
if ($LASTEXITCODE -ne 0) { throw 'Pair export failed' }
```

`Build-Docs.ps1 -PublicDocumentsOnly` uses
`-OutputDirectory`; HTML wrappers use `-Out`. Public Word build automatically excludes
validation Word and Excel (including their COM refreshes). It cannot use `--skip-workbook`.
HTML reads its participant source from **the same `--out` directory**, not repository
`docs`. The participant Word must already exist and be built in public mode.
The footer and download use its actual name/hash; layout-only release restamping is
not accepted in this mode.

Full Office authoring remains supported with its companion, checklist and runtime
checks intact. Always give it a named edition and a separate fresh external **PRIVATE**
`--out` directory; do not invoke edition-free overwrite/legacy-cleanup defaults.
Its companion Word/XLSX are not current downloads. See [tools/docs](../docs/README.md).
Public validation checks document
content, OOXML, visuals, screenshots, mirror coverage and live on-disk hashes. It does
not reseal runtime or claim repository-wide publication approval, live evaluation
success, screenshot approval or browser/Word rendering approval. Perform those
separate reviews before release; the existing rendering/interaction tools remain
available. Keep their outputs outside the pair.

内部編集用の全 Office build も、検査を弱めずに維持します。ただし named edition と、
公開ペアとは別の新しい外部 **PRIVATE** `--out` を必ず指定します。版名なしの暗黙の上書き・
旧版清掃は使わず、別冊 Word/XLSX を現行ダウンロードには戻しません。
文書の検証成功は、履歴の公開承認・実環境の品質合格・画面承認・描画成功を代替しません。

## Export and read-only revalidation / export と読み取り専用の再検証

`export_public_documents.py` validates both the policy and the existing document
content gates before copying. It verifies destination bytes afterward. There is no
content-validation bypass flag. The source must already contain exactly the chosen
pair; it is not a mixed directory that the exporter filters or cleans.

The source and export directories must be outside the repository and disjoint.
Files must be regular, not symbolic links, junctions/reparse points or hardlinks.
Parent traversal is rejected before path resolution. Unexpected files (including
hidden files/subdirectories) fail validation and are **not deleted**. A destination
cannot use Windows device/extended namespace aliases, alternate data streams,
reserved device names or ambiguous trailing dots/spaces. A destination
must be absent or empty. Exclusive file creation never overwrites an existing file,
even if one appears while validation runs. A failed copy can leave an incomplete
directory; that is a failure, not a publishable result, and no cleanup is performed.

`--manifest` is optional. When supplied, it must name a new file outside both the
source and public-pair directories and outside the repository. It contains the two
actual SHA-256 hashes with LF line endings. It is never silently put inside the pair.
Without it, hashes are returned on stdout only.

For an already assembled pair, use the explicit read-only path:

```powershell
python .\tools\publication\export_public_documents.py `
  --validate-only --out $PublicPair --edition $Edition --manifest $Hashes
```

Omit `--source` in this mode. If a manifest is supplied it must exist and match; it
is not rewritten. Keep JSON/stdout logs outside the pair too.

公開版は Word / HTML ともに同じ `--public-documents-only`・edition・出力先で生成します。
export は参加者 Word と HTML のみのディレクトリを検証し、新しい別ディレクトリへ実バイトのまま複製します。
既存ファイルや余分なファイルを削除・上書きしません。manifest と記録・画像は 2 ファイルの外へ保存します。
既存 export の再確認は `--validate-only` で行い、ファイルを書き換えません。

### Revalidating the installed pair / 配置済みペアの再検証

After installation, copy **only the two exact files** from `docs` to a new external
directory. Prove that each source hash is unchanged during the copy and equals its
copy, then compare with the approved export manifest. Never copy `docs` wholesale,
use links, or validate repository `docs` directly. The release Word hash and reviewed
`$Shape` remain the pins; copying is not a new build.

配置後も `docs` を直接検証しません。正確な 2 ファイルだけを新しい外部ディレクトリへ通常の
ファイルとして複製し、コピー前後の原本とコピーのハッシュ一致を確認します。
`docs` 全体やリンクを複製せず、承認済み export manifest とも照合します。
pin は承認済み Word のハッシュと `$Shape` のままです。

```powershell
$InstalledCheck = Join-Path $PrivateDocuments "installed-$Edition-$([guid]::NewGuid().ToString('N'))"
New-Item -ItemType Directory -Path $InstalledCheck -ErrorAction Stop | Out-Null
foreach ($Name in @($WordName, $HtmlName)) {
  $Source = Get-Item -LiteralPath (Join-Path '.\docs' $Name) -ErrorAction Stop
  $Before = (Get-FileHash -LiteralPath $Source.FullName -Algorithm SHA256).Hash
  $Copy = $Source.CopyTo((Join-Path $InstalledCheck $Name), $false)
  $After = (Get-FileHash -LiteralPath $Source.FullName -Algorithm SHA256).Hash
  $Copied = (Get-FileHash -LiteralPath $Copy.FullName -Algorithm SHA256).Hash
  if ($Before -ne $After -or $Before -ne $Copied) { throw "Copy hash mismatch: $Name" }
}
python .\tools\publication\export_public_documents.py `
  --validate-only --out $InstalledCheck --edition $Edition --manifest $Hashes
if ($LASTEXITCODE -ne 0) { throw 'Installed pair differs or fails validation' }
```

This read-only export check invokes both document-content validators. For the pinned
HTML or Word rendering checks, repeat the commands above with `--out $InstalledCheck`,
not `--out .\docs`. Keep all reports outside the pair. Missing installed files block
this procedure; do not fall back to the private archive or another edition.

この読み取り専用 export 検査は Word/HTML 両方の内容 validator を呼び出します。
pin 付き HTML 検査や Word 描画は上のコマンドの出力先を `$InstalledCheck` に置き換えて行い、
記録はペア外へ保存します。配置済みファイルが欠けていれば停止し、旧版で代用しません。

## Hands-on assets and captures / 実習資産と画面写真

The HTML is self-contained for **reading**. This pair is not a complete executable
hands-on distribution: notebooks, datasets and deployment code need an explicitly
approved separate delivery/hosting policy. No ZIP, runtime or third download is
automatically embedded or uploaded. The guide states this boundary.

Configuration changes require a fresh review of the matching Word/HTML text and
real UI captures. Original answers and captures remain private and untouched.
Crop/redact accounts, URLs and internal IDs only in publication copies, disclose
the crop/redaction, and preserve relevant UI content. Never alter evaluated answers
to produce PASS, fabricate captures or treat a previous screen as new evidence.
Do not replace the current style carrier/assets until explicitly assigned.

For `unified-20260923`, accurate captures are reused without pixel changes.
The obsolete visible instruction captures `13-12`, `13-33`, `16-30` and `18-30` are excluded from
this edition, not relabelled as unified configuration evidence. Their originals
remain in the carrier. `17-40` is an interaction illustration, not evidence of
the current configuration or new evaluation. The original capture identity and
hashes remain in `tools/docs/assets/unified-ui-captures.json`. Its usage policy
requires matching CI-section bytes and Preview/CI settings; validation rejects
obsolete configuration images embedded in the current Word. New configuration
captures require normal authenticated UI access and a fresh provenance review.
No post-capture pixel edit, reconstructed screenshot or standalone generated plot
is substituted for an actual Fabric UI capture.

統合版は古い指示が写る `13-12`・`13-33`・`16-30`・`18-30` を除外し、原本を保持します。
`17-40` は未変更のCI指示部分・Preview／CI設定との一致を検査した操作例で、新設定・新評価の
証拠ではありません。新設定のキャプチャには正常な本人認証と来歴の再レビューが必要です。
旧画像の設定版を現行版へ付け替えず、画素編集やログ・生成グラフでの代用もしません。

HTML の自己完結性は閲覧のためです。Notebook・データ・配置コードの提供方針は別途承認し、
ZIP や第 3 の download を自動で追加しません。構成が変われば本文と実 UI 画像を再レビューし、
原回答・原画像は非公開で保持します。公開コピーだけに開示付きの切り抜き／伏せ字を行い、
関連内容・失敗を改変しません。画面承認や carrier / assets の更新は別担当の作業です。

## Focused regression tests / 小さな回帰検査

These checks need no Office COM or WebP build. Read-only source capture/drift checks
are sufficient during README editing; do not rebuild binaries on every edit.
README 編集時は読み取り専用の source capture / drift 検査を使い、毎回バイナリを再生成しません。

```powershell
python .\tools\html\sync_i18n.py
python .\tools\html\sync_i18n.py --public-documents-only
python -m unittest tools.docs.tests.test_public_document_mode tools.publication.tests.test_public_export
```

Tests use small local fixtures and read-only content capture. They cover the full
authoring default, single-source provenance, companion links, complete guide/rubric/
parameter retention, exact file allowlists, overwrite/path safety and immutable
originals. No new test framework is required.
