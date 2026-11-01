# Furusato Workshop — ダウンロード

GitHub上の[Lab](../Lab/README.md)を参加者手順の正本とし、保存して使える日英HTMLをオフライン用に提供します。参加者用ZIPは実行資産にも使います。ZIP内の案内コピーと異なる場合は、このLabとHTMLの現行リンクを使ってください。

| ファイル | ダウンロード | 内容 |
|---|---|---|
| 日英HTML手順書 | [HTMLを保存](https://github.com/yang-jiayi/furusato-fabric-workshop/raw/refs/heads/main/docs/furusato-workshop-v3-1-0-complete.html) | 24章・5付録の全手順。日英切替、検索、進捗チェック、印刷に対応 |
| 参加者用ZIP | [ZIPを保存](https://github.com/yang-jiayi/furusato-fabric-workshop/raw/refs/heads/main/docs/Furusato_Workshop_v3.1.0_current.zip) | HTML・Lab、Notebook、CSV、SQL、モデル、ツール、添付資料、評価用紙 |
| 配布SHA-256 | [SHA256SUMS.txt](SHA256SUMS.txt) | HTMLとZIPの取得後の照合用 |
| HTML検証記録 | [DOCUMENT_VALIDATION.json](DOCUMENT_VALIDATION.json) | 同じHTMLバイト列の日英静的・Chromium検査。Fabricの配置・Agent回答品質は認定しません |
| Lab検証記録 | [LAB_VALIDATION.json](LAB_VALIDATION.json) | 24章・5付録、ソース本文・画像・リンクの対応確認 |

## 始め方

1. 保存したZIPのSHA-256を、上の配布一覧にある同じファイル名の値と照合します。
2. ZIPをすべて展開します。手順はGitHubの[Labの目次](../Lab/README.md)を使い、オフラインの場合はこのページから現行HTMLを保存して開きます。
3. 第4章の前提確認を終え、第24.4〜24.6節で自分の作業フォルダーへ配置します。
4. 第5〜8章でデータと設定を確認し、第24.7節と第9〜11章で取り込みと品質処理を進めます。
5. 第24.8節と第17章でモデルとAgentを構成・公開し、第19章と付録Cで回答を評価します。

まず標準10問で操作と採点方法を確認し、その後、公開29問による改善前後の比較へ進みます。回答、実際の問い合わせ、返された値、未確認の内容を区別して記録します。同じ設定を適用しても、回答精度の再現を保証するものではありません。

Labはキャプチャごとの操作ページに、準備、設定の全文、コマンド、参照表、完了条件を収録しています。キャプチャがない操作も手順を省略していません。HTMLはブラウザーで直接開ける単一ファイルです。

初回の増分取り込みより前に、`DonationEvents` だけの OneLake mirroring を安全に確認します。policy の設定確認は実際の Delta データ到着や native Ontology 時系列の実行証明ではありません。手順書の照合条件を満たしてから進めてください。

## English

The [GitHub Lab guide](../Lab/README.md) is the authoritative participant procedure; save the standalone bilingual HTML linked here for offline use. Use the participant ZIP for runtime assets, and use these current guide links if its bundled guide copy differs. Verify the ZIP against [SHA256SUMS.txt](SHA256SUMS.txt) before extraction.

The [HTML validation receipt](DOCUMENT_VALIDATION.json) records static and Chromium checks for the exact document bytes, not Fabric deployment or Agent answer quality. The [Lab receipt](LAB_VALIDATION.json) records source-text, image and link coverage. Before the first increment, safely verify OneLake mirroring for `DonationEvents` only; policy readback alone does not prove Delta data arrival or native Ontology time-series execution.

The complete procedure covers 24 chapters and five appendices. Start with Chapters 4/24 for deployment, inspect data and models in Chapters 5–13, configure and publish the same Data Agent in Chapter 17, then evaluate and improve answers in Chapter 19 and Appendix C. Start with ten practice questions before the public 29-question comparison. Record actual queries and results separately from unsupported or unobserved behavior; matching configuration does not guarantee matching accuracy.
