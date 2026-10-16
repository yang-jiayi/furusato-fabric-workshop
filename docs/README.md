# Workshop 3.0.0 — 配布ファイル / Downloads

最新版の **Word・日英HTML・ZIPの実ファイルを、この `docs` フォルダー直下に公開しています。**
以下のダウンロードリンクから取得してください。

| ファイル | ダウンロード | 内容 |
|---|---|---|
| 参加者用Word | [Wordをダウンロード](https://github.com/yang-jiayi/furusato-fabric-workshop/raw/refs/heads/main/docs/Fabric_IQ_Ontology_Workshop_Furusato_Participant_v3.0.0.docx) | 配置、採用済み設定の適用、公開確認、チューニングと評価の手順書 |
| 参加者用日英HTML | [HTMLをダウンロード](https://github.com/yang-jiayi/furusato-fabric-workshop/raw/refs/heads/main/docs/furusato-workshop-v3-0-0-complete.html) | Wordと対応する手順書。保存後にブラウザーで開き、日英切替・検索・印刷が可能 |
| Workshop一式 | [ZIPをダウンロード](https://github.com/yang-jiayi/furusato-fabric-workshop/raw/refs/heads/main/docs/Furusato_Workshop_v3.0.0_current-20261015.zip) | Word・HTML、Notebook、CSV、SQL、モデル、ツール、評価用紙を収録 |

**参加者への配布はZIP一式を推奨します。** 手順はWordまたはHTMLを使用し、実行資産は同じ版のZIPから取得します。HTMLからWordを開く場合は、両方を同じフォルダーへ保存してください。

[配布SHA-256](SHA256SUMS.txt)でファイルを確認できます。ZIPのファイル名にある `20261015` は教材一式の版を識別する日付です。この場所への配置日とは区別します。

## 始め方

1. ZIPのSHA-256を照合し、すべて展開します。
2. `guide/`内のWordまたはHTMLを開き、第4章・第24章に沿って環境を準備し、配置します。
3. 第17章で採用済みData Agent設定を適用・公開・確認します。
4. 第19章・付録Cで回答を評価します。まず10問で操作と採点を練習し、その後、公開29問による改善前後の比較へ進めます。

[教材の構成と詳しい進め方](v3.0.0/current/README.md) ·
[検証範囲・既知の制約](v3.0.0/current/deployment-verification.md) ·
[チューニング実測レポート](v3.0.0/tuning-20261015/README.md)

## 版と検証

この3ファイルは、検証済みの [現行教材](v3.0.0/current/README.md) とバイト単位で同一です。今回の配置では文書やZIPを再生成していません。元の文書・ツール検証と、新規環境での通し実行・AI回答評価は別の確認です。同じ設定の再現は、同じ回答精度の保証ではありません。

`v2.7.0`、`v3-preview`、日付付きフォルダーなどは過去の版・検証記録です。新規参加者には上の3.0.0一式を配布してください。

教材更新時は、検証済みの `v3.0.0/current/` からこの3ファイルを同期し、`SHA256SUMS.txt` とダウンロードリンクも同時に更新します。元のファイル、直下のコピー、ZIP内のWord・HTMLが一致することを確認してください。

## English

The current Word guide, bilingual HTML and full workshop ZIP are actual files directly in this directory. Use the download links above. Give participants the complete ZIP, which includes the guides, data, Notebooks, tools and evaluation forms. Keep the standalone Word and HTML in the same directory if using the HTML's local Word link.

Verify downloads against [SHA256SUMS.txt](SHA256SUMS.txt). These three files are byte-identical to the verified [current materials](v3.0.0/current/README.md); this placement does not regenerate them or establish a new deployment or AI evaluation. The ZIP filename's `20261015` identifies the package edition. Retained older versions are historical references.

Follow Chapters 4/24 for deployment, Chapter 17 for configuration and publication, and Chapter 19 plus Appendix C for evaluation. Start with ten practice questions before comparing results with the public 29-question evaluation. Matching configuration does not guarantee matching answer accuracy. See the [verification record](v3.0.0/current/deployment-verification.md) for scope and limitations.
