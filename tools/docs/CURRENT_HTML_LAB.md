# 現行のHTMLとLabを生成する / Build current HTML and Lab

参加者向けの配布物は、単一ファイルの日英HTMLと、GitHubで読む`Lab/`です。24章・5付録を同じ参加者用モデルから生成します。現在の経路はOffice文書を生成せず、以前の文書ペア用コマンドとは別です。

The current participant delivery is one standalone bilingual HTML file and the complete GitHub `Lab/` guide. Both are generated from the same 24-chapter, five-appendix participant model. This route does not generate an Office document; the historical paired-document commands remain separate.

既存の完全版Labを共有原稿 `tools/docs/furusato_docs/participant30_text.py` で修正します。既存Wordは移行時の比較・レビュー用に保持し、現行手順の正本にはしません。教材リリースは **3.0.0** のままで、文書の修正やローカル検査は実環境への配置の承認ではありません。

Revise the existing complete Lab through the shared source `tools/docs/furusato_docs/participant30_text.py`. Keep the existing Word for transition comparison/review, not as the authoritative current instructions. The course release remains **3.0.0**; documentation edits and local checks are not authorization for live deployment.

## 準備 / Setup

Python 3.13を用意し、リポジトリのルートで次を実行します。Labの共有モデルもOffice用ライブラリをインポートします。文書用とprovisioning用の依存関係に加え、現行HTMLの解析に `lxml`、ブラウザー検査に `playwright` と `pypdf` が必要です。HTML用requirementsの任意test指定だけでは、これらの検査依存関係の導入を保証できません。

With Python 3.13 available, run from the repository root. The shared Lab model also imports Office libraries. Install the documented docs/provisioning requirements plus `lxml` for current HTML parsing and `playwright`/`pypdf` for browser checks. The optional test markers in the HTML requirements alone do not ensure these validation dependencies are installed.

```bash
python -m pip install -r tools/docs/requirements.txt \
  -r tools/provisioning/requirements-preview30.txt \
  "lxml>=5.0" "playwright>=1.44" "pypdf>=4.0"
```

ブラウザー検査は、Linuxで `/usr/bin/chromium` が存在すれば従来どおり使い、それ以外は同じPython環境のPlaywright管理Chromiumを使います。Windowsを含む環境では次のコマンドで管理ブラウザーを準備できます。ブラウザーが未導入なら依存関係エラーで停止し、検査やパッケージ化を省略しません。

Browser validation preserves the existing Linux `/usr/bin/chromium` preference when that file exists; otherwise it uses Playwright-managed Chromium from the same Python environment. Prepare the managed browser on Windows or other platforms with the following command. A missing browser is a dependency error, not permission to skip validation or packaging checks.

```text
python -m playwright install chromium
```

Debian/Ubuntu互換LinuxでシステムChromiumを使う場合は、従来どおりパスを確認します。

For system Chromium on Debian/Ubuntu-compatible Linux, verify the existing path as before.

```bash
sudo apt-get update
sudo apt-get install -y chromium
test -x /usr/bin/chromium
/usr/bin/chromium --version
```

既存のChromium実行ファイルを明示する場合、`validate` の `--browser` とともに `--browser-executable` を指定します。次はPowerShellの例で、`$Stage` は後述の要件を満たす新しい非公開出力先です。実際の既存ファイルのパスへ置き換えてください。ディレクトリや存在しないパス、`--browser` なしの指定は拒否されます。

To select an existing Chromium executable explicitly, use `--browser-executable` only on `validate` together with `--browser`. This PowerShell example assumes `$Stage` is a fresh private output destination meeting the requirements below. Replace the executable path with a real existing file. Directories, missing files and use without `--browser` are rejected.

```powershell
python -B tools\docs\current_delivery.py validate --out "$Stage\guide" --browser `
  --browser-executable "C:\Browsers\Chromium\chrome.exe"
```

## 作成・レビュー・検証 / Author, review and validate

日英原稿を修正した後、正確なファイルパラメーターと実行証拠の対応、講師が事前設定するnative機能の前提、未設定・失敗・未確認の区別をレビューします。新しい画面は実環境で取得・確認した場合だけ追加します。`Stage`と`Review`は毎回新しい非公開出力先にし、共有・コミットしません。生成、検証、パッケージ化の間はソースを変更しません。

After editing both languages, review exact file-parameter/run-evidence correlation, instructor-provisioned native prerequisites, and distinctions between unconfigured, failed and unverified states. Add screenshots only after real capture and review. Choose fresh private `Stage` and `Review` directories for each build; do not share or commit them. Keep source inputs unchanged through generation, validation and packaging.

管理されたクラウド環境では、`/workspace`や`/tmp`などのプラットフォーム用Gitマーカーのあるツリーを避け、Gitの管理外にある `/var/tmp` 内に毎回新しい非公開ステージとレビュー先を作ります。次はBash用のレシピです。作成失敗やGit管理下の判定時には明示的に停止し、そのまま生成を続けません。出力はレビュー後に安全に削除し、共有・コミットしません。

In managed cloud environments, avoid platform Git-marker trees such as `/workspace` and `/tmp`. Create fresh private stage and review directories below `/var/tmp`, outside Git. The following Bash recipe stops explicitly on creation failure or a Git-managed destination; do not continue generation after a failure. Safely remove private outputs after review; never share or commit them.

```bash
# Run this entire recipe in one Bash shell from the repository root.
set -euo pipefail
umask 077
fail() { printf '%s\n' "$*" >&2; exit 1; }
PrivateRoot="$(cd /var/tmp && pwd -P)" || fail "Cannot access /var/tmp"
if git -C "$PrivateRoot" rev-parse --show-toplevel >/dev/null 2>&1; then
  fail "Private output root is inside Git; choose an approved root outside Git"
fi
Stage="$(mktemp -d "$PrivateRoot/furusato-stage.XXXXXXXXXX")" \
  || fail "Cannot create private Stage"
Review="$(mktemp -d "$PrivateRoot/furusato-review.XXXXXXXXXX")" \
  || fail "Cannot create private Review; unused Stage remains at $Stage"
for Output in "$Stage" "$Review"; do
  test -d "$Output" && test -w "$Output" || fail "Output is not writable: $Output"
  if git -C "$Output" rev-parse --show-toplevel >/dev/null 2>&1; then
    fail "Output is inside Git: $Output"
  fi
done
python -B tools/docs/build_lab.py --out "$Stage/Lab" --receipt "$Review/lab-coverage.json"
python -B tools/docs/build_lab.py --out "$Stage/Lab" --receipt "$Review/lab-coverage.json" --check
python -B tools/docs/current_delivery.py build --out "$Stage/guide"
python -B tools/docs/current_delivery.py validate --out "$Stage/guide" --browser
python -B tools/docs/current_delivery.py package --out "$Stage/guide" \
  --lab "$Stage/Lab" --package "$Stage/Furusato_Workshop_v3.0.0_current.zip"
```

`build_lab.py --help`でレビュー出力先の指定を確認してください。生成したLabの全章・付録を既存完全版および移行用Wordと比較し、同じ原稿のHTMLも確認します。Chromiumは選択したHTMLだけを一時的にループバック配信します。他のネットワーク要求は拒否され、検査後にサーバーを停止します。

Use `build_lab.py --help` for its review output options. Compare all generated Lab chapters/appendices with the existing complete edition and transition Word, and review the HTML from the same source. Browser checks temporarily serve only the selected HTML on loopback. Other network requests are blocked and the server is stopped after validation.

静的検査は全セクション、日英本文、コードと質問の原文、図、アンカー、単一ファイル内のリソースを照合します。ブラウザー検査は日英切替・検索・学習記録・コードコピー・拡大・390px幅・印刷PDFを確認し、実際のHTMLハッシュに結び付けます。パッケージはこれらの検査結果が一致したファイルだけを受け付けます。ソースの保護対象と実行ツールはハッシュを維持して同梱し、過去の文書レポートは配布しません。

Static validation checks sections, bilingual content, literal code/prompts, figures, anchors and embedded resources. Browser validation checks language, search, progress, copy, zoom, 390px layout and printed PDFs against the exact HTML digest. Packaging requires matching passed receipts and preserves the protected runtime/source hashes. Historical document reports are excluded from the participant package.

この検査はFabricの配置やAgentの回答品質を認定しません。印刷PDFの生成は全ページの目視確認を意味しません。新しい画面キャプチャは実環境で取得・確認した後に共有モデルへ追加し、LabとHTMLの両方を再生成します。

These checks do not certify Fabric deployment or Agent answer quality. PDF generation does not imply visual review of every printed page. Add new screenshots only after capturing and reviewing the real environment, then regenerate both Lab and HTML.
