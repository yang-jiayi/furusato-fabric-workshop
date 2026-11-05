# Furusato Workshop 3.1.0 — downloads

The bilingual [HTML textbook](furusato-workshop-v3-1-0-complete.html?raw=true) is the primary participant manual. The numbered [GitHub Lab](../Lab/README.md) is its Markdown companion. Download the matching [participant ZIP](Furusato_Workshop_v3.1.0_current.zip?raw=true) for runtime assets and offline use.

| File | Download | Contents |
|---|---|---|
| HTML textbook | [Save the HTML](furusato-workshop-v3-1-0-complete.html?raw=true) | All 24 chapters and five appendices; Japanese/English switch, search, progress checklist and responsive layout |
| Participant ZIP | [Save the ZIP](Furusato_Workshop_v3.1.0_current.zip?raw=true) | HTML, Lab, notebooks, data, configuration, tools and text-based reference attachments |
| SHA-256 | [SHA256SUMS.txt](SHA256SUMS.txt) | Verify the downloaded HTML and ZIP |
| HTML validation | [DOCUMENT_VALIDATION.json](DOCUMENT_VALIDATION.json) | Static and browser checks for the exact HTML bytes; not Fabric deployment or AI-answer certification |
| Lab validation | [LAB_VALIDATION.json](LAB_VALIDATION.json) | Source-text, image and link coverage for the numbered Lab |

The current participant delivery contains no Word or PDF manuals or exports. The Chapter 15 business requirements attachment is plain text. The upstream icon terms are preserved in the [source notice](assets/architecture/upstream/NOTICE.txt); the upstream terms PDF is not included in the participant package.

## Get started

1. Compare the downloaded ZIP's SHA-256 with the value for the same filename in `SHA256SUMS.txt`.
2. Extract the ZIP. Use the GitHub [Lab index](../Lab/README.md), or open the HTML textbook locally for offline reading.
3. Begin with Chapter 4 to verify prerequisites, authorized scope and safe execution.
4. Follow Chapters 24 and 5–13 to deploy or inspect resources, data and models without duplicating successful work.
5. Configure and read back the Data Agent in Chapter 17, then evaluate it using Chapter 19 and Appendix C.

Run commands from the repository root in a Git checkout. In the participant ZIP, use its extracted `source/` directory. Feature availability depends on the Fabric tenant, region, capacity and permissions. Configuration alone does not establish execution or answer quality; record actual sources, queries and results.

All workshop data is synthetic. Keep static donations separate from operational observations and quality-processed Gold. The published guide and package do not guarantee AI accuracy or live Fabric behavior.

## 日本語

日英HTMLの[手順書](furusato-workshop-v3-1-0-complete.html?raw=true)を参加者向けの主教材として提供します。番号付きの[GitHub Lab](../Lab/README.md)は各手順のMarkdown版です。Notebook・データ・設定・ツールなどを含む[参加者用ZIP](Furusato_Workshop_v3.1.0_current.zip?raw=true)も利用できます。ダウンロード後は同じファイル名の値を[SHA256SUMS.txt](SHA256SUMS.txt)で照合してください。

現在の参加者向け配布物にはWordやPDFの手順書・出力を含めません。第15章の業務要件資料はテキスト形式です。上流アイコンの利用条件は[ソース通知](assets/architecture/upstream/NOTICE.txt)に残し、利用条件の原本PDFは参加者用パッケージに含めません。

最初に第4章で前提条件、許可された範囲、安全な実行を確認します。第24章と第5〜13章で配置・データ・モデルを確認し、第17章でData Agentの構成を読み戻した後、第19章と付録Cで回答を評価します。コマンドはGitリポジトリのルート、ZIP利用時は展開先の`source/`から実行してください。

Fabricの機能提供はテナント、リージョン、容量、権限によって異なります。設定表示だけで実行や回答精度が確認できたとは判断せず、実際のソース、問い合わせ、結果を記録してください。データは合成データです。静的寄付、運用観測、品質処理後のGoldを混同しません。
