# 現行のHTMLとLabを生成する / Build current HTML and Lab

参加者向けの配布物は、単一ファイルの日英HTMLと、GitHubで読む`Lab/`です。24章・5付録を同じ参加者用モデルから生成します。現在の経路はOffice文書を生成せず、以前の文書ペア用コマンドとは別です。

The current participant delivery is one standalone bilingual HTML file and the complete GitHub `Lab/` guide. Both are generated from the same 24-chapter, five-appendix participant model. This route does not generate an Office document; the historical paired-document commands remain separate.

リポジトリのルートで、Python 3.13と依存関係を準備してから実行します。`Stage`は毎回新しい出力先にします。生成、検証、パッケージ化の間はソースを変更しません。

Run from the repository root with Python 3.13 and the documented dependencies. Choose a fresh stage for each build and keep source inputs unchanged through validation and packaging.

```bash
python -B tools/docs/build_lab.py --out "$Stage/Lab" --receipt "$Review/lab-coverage.json"
python -B tools/docs/current_delivery.py build --out "$Stage/guide"
python -B tools/docs/current_delivery.py validate --out "$Stage/guide" --browser
python -B tools/docs/current_delivery.py package --out "$Stage/guide" \
  --lab "$Stage/Lab" --package "$Stage/Furusato_Workshop_v3.0.0_current.zip"
```

`build_lab.py --help`でレビュー出力先の指定を確認してください。管理されたクラウド環境では`/workspace`や`/tmp`のプラットフォーム用Gitマーカーを避け、`/var/tmp`内の非公開ステージを使います。Chromiumは`/usr/bin/chromium`を使い、選択したHTMLだけを一時的にループバック配信します。他のネットワーク要求は拒否され、検査後にサーバーを停止します。

Use `build_lab.py --help` for its review output options. In managed cloud environments, use a private stage below `/var/tmp`, outside platform Git-marker trees. Browser checks use `/usr/bin/chromium` and temporarily serve only the selected HTML on loopback. Other network requests are blocked and the server is stopped after validation.

静的検査は全セクション、日英本文、コードと質問の原文、図、アンカー、単一ファイル内のリソースを照合します。ブラウザー検査は日英切替・検索・学習記録・コードコピー・拡大・390px幅・印刷PDFを確認し、実際のHTMLハッシュに結び付けます。パッケージはこれらの検査結果が一致したファイルだけを受け付けます。ソースの保護対象と実行ツールはハッシュを維持して同梱し、過去の文書レポートは配布しません。

Static validation checks sections, bilingual content, literal code/prompts, figures, anchors and embedded resources. Browser validation checks language, search, progress, copy, zoom, 390px layout and printed PDFs against the exact HTML digest. Packaging requires matching passed receipts and preserves the protected runtime/source hashes. Historical document reports are excluded from the participant package.

この検査はFabricの配置やAgentの回答品質を認定しません。印刷PDFの生成は全ページの目視確認を意味しません。新しい画面キャプチャは実環境で取得・確認した後に共有モデルへ追加し、LabとHTMLの両方を再生成します。

These checks do not certify Fabric deployment or Agent answer quality. PDF generation does not imply visual review of every printed page. Add new screenshots only after capturing and reviewing the real environment, then regenerate both Lab and HTML.
