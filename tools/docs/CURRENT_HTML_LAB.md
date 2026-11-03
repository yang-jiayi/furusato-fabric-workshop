# 現行HTMLとLabの生成・検証 / Build and validate current HTML and Lab

参加者向けの主教材は、検索・日英切替に対応した単一ファイルHTMLです。番号付きのGitHub Labは同じ24章・5付録の原稿から作るMarkdown版です。この現行経路はWordやPDFを生成せず、配布ZIPにもそれらの出力を含めません。

The primary participant handbook is a searchable, bilingual, standalone HTML file. The numbered GitHub Lab is the Markdown companion, generated from the same 24-chapter, five-appendix source. This current route generates no Word or PDF and includes neither format in the participant ZIP.

日英原稿は `tools/docs/furusato_docs/participant30_text.py`、画面説明は `participant30_figures.py` で管理します。新しい画面は実環境で取得・確認した場合だけ追加し、未確認のUIや機能完了を示す説明を作りません。教材版は `WORKSHOP_VERSION` に従い、データ処理の基準版 `VERSION` は変更しません。文書の生成・検証は実環境への配置や回答精度の承認ではありません。

Maintain bilingual prose in `tools/docs/furusato_docs/participant30_text.py` and figure descriptions in `participant30_figures.py`. Add screenshots only after capturing and checking the real UI; do not invent UI states or imply an unverified feature is complete. The course edition follows `WORKSHOP_VERSION`; preserve the data-processing baseline in `VERSION`. Document generation and validation do not authorize deployment or certify answer accuracy.

## 準備 / Setup

リポジトリルートで、文書モデル、HTML解析、ブラウザー検査の依存関係を用意します。現在の検査経路はChromiumでHTMLの操作・レイアウト・ネットワーク境界を確認し、PDFを生成しません。

From the repository root, prepare the document-model, HTML-parsing and browser-validation dependencies. Current browser checks verify HTML interaction, layout and network boundaries in Chromium; they do not generate PDFs.

```powershell
python -m pip install -r tools\docs\requirements.txt `
  -r tools\provisioning\requirements-preview30.txt `
  "lxml>=5.0" "playwright>=1.44"
python -m playwright install chromium
```

システムにあるChromiumを明示する場合は、`validate` に `--browser` と `--browser-executable <既存の実行ファイル>` を指定します。存在しないファイルやディレクトリ、`--browser` なしの指定は拒否されます。ブラウザーが使えない場合は検証を省略せず、依存関係の問題として記録します。

To select an existing Chromium executable explicitly, pass `--browser` and `--browser-executable <existing executable>` to `validate`. Missing files, directories and use without `--browser` are rejected. If a browser is unavailable, record the dependency blocker rather than skipping validation.

## 生成・検証・パッケージ / Build, validate and package

毎回新しい非公開ステージと検証記録先を使い、Git管理外に配置します。生成、検証、パッケージ化の間はソースを変更しません。出力先を既存の作業物へ重ねず、共有・コミットしないでください。

Use fresh private stage and receipt directories outside the Git worktree. Keep source inputs unchanged through build, validation and packaging. Do not overwrite existing work or share/commit staging outputs.

```powershell
$Stage = Join-Path $env:TEMP ("furusato-stage-" + [guid]::NewGuid())
$Review = Join-Path $env:TEMP ("furusato-review-" + [guid]::NewGuid())
New-Item -ItemType Directory -Path $Stage, $Review | Out-Null
$Version = (Get-Content WORKSHOP_VERSION -Raw).Trim()
$HtmlName = "furusato-workshop-v$($Version.Replace('.', '-'))-complete.html"
$PackageName = "Furusato_Workshop_v${Version}_current.zip"
python -B tools\docs\current_delivery.py build --out "$Stage\guide"
python -B tools\docs\current_delivery.py validate --out "$Stage\guide" --browser
python -B tools\docs\build_lab.py --out "$Stage\Lab" --receipt "$Review\lab-coverage.json"
python -B tools\docs\build_lab.py --out "$Stage\Lab" --receipt "$Review\lab-coverage.json" --check
Copy-Item -LiteralPath "$Stage\guide\$HtmlName" -Destination "docs\$HtmlName"
python -B tools\docs\current_delivery.py package --out "$Stage\guide" `
  --lab "$Stage\Lab" --package "$Stage\$PackageName"
```

ブラウザー検査は実際のHTMLハッシュに結び付き、日英切替、検索、進捗チェック、コピー、画像拡大、320/390/768/1440px幅、スクリプトエラー、外部ネットワーク要求のないことを確認します。静的検査は全セクション、日英本文、コマンド・質問、図、アンカー、単一HTML内のリソースを検査します。画面サイズの確認はFabric上の表示や全ての利用環境を認定するものではありません。

Browser validation binds to the exact HTML digest and checks language switching, search, progress, copy, image zoom, 320/390/768/1440px widths, script errors and absence of external network requests. Static validation checks all sections, bilingual text, commands/prompts, figures, anchors and embedded resources. Viewport checks do not certify Fabric rendering or every user environment.

パッケージ処理は生成HTML・Lab・参照添付・実行ソースの各バイトを照合し、全ファイル名を検査して、`.docx`または`.pdf`の項目が1つでもあれば失敗します。第15章の業務要件資料は `business-requirements.txt` です。Microsoftアイコンの利用条件は `docs/assets/architecture/upstream/NOTICE.txt` に記載し、原本PDFはパッケージに含めません。配布前に、SHA-256、ZIPのCRC、Labリンク、HTMLの全内容、および文書形式の在庫を確認します。

Packaging verifies the HTML, Lab, reference attachments and executable source bytes. It rejects the package if any `.docx` or `.pdf` entry exists. Chapter 15 uses `business-requirements.txt`. Microsoft icon usage terms are recorded in `docs/assets/architecture/upstream/NOTICE.txt`; the source terms PDF is excluded from the package. Before distribution, check SHA-256, ZIP CRC, Lab links, full HTML content and the document-format inventory.

## 公開時の確認 / Publication checks

`docs/README.md`、ルートREADME、Lab目次、現行成果物一覧のリンク・版・ファイル名は同じ検証済み成果物を指す必要があります。GitHub上のREADMEはダウンロードとナビゲーションを提供するものであり、Pages等の公開Webサイトが設定済みであることを意味しません。HTMLは取得してブラウザーで開けます。

Keep the root README, `docs/README.md`, Lab index and current artifact links/version/file names aligned with the same validated artifacts. GitHub README links provide download and navigation; they do not imply that a hosted website such as GitHub Pages is configured. Download and open the HTML in a browser.

これらのローカル検査はFabricの配置、Ontology/Graphの準備状態、Data Agentの正答率や100%スコアを証明しません。公開版を第19章・付録Cで実際のソース、問い合わせ、結果を使って評価し、未実施・失敗・未確認を区別して記録してください。

Local checks do not prove Fabric deployment, Ontology/Graph readiness, Data Agent accuracy or a 100% score. Evaluate the actual publication with Chapter 19 and Appendix C using real sources, queries and results; report unrun, failed and unverified checks distinctly.
