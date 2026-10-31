# Furusato Workshop 3.0.0 — 参加者用教材 / Participant materials

[画面ごとのLab手順書](../../../Lab/README.md) · [単一ファイルの日英HTML](guide/furusato-workshop-v3-0-0-complete.html) · [参加者用ZIP](Furusato_Workshop_v3.0.0_current.zip) · [SHA-256](SHA256SUMS.txt)

LabとHTMLには、準備から配置・取り込み・モデル・Data Agentの設定・回答評価まで、24章・5付録の全手順を収録しています。Labは操作やキャプチャごとのMarkdownで読み、HTMLはファイルを保存してオフラインで使えます。どちらかを操作手順書にして、同じ版のZIPを合わせて使います。

Lab and HTML contain the complete 24 chapters and five appendices, from preparation and deployment through ingestion, models, Agent configuration and answer evaluation. Read Lab as Markdown pages organized by operation and capture, or save the standalone bilingual HTML for offline use. Use either guide with the matching participant ZIP.

## 始め方 / Start

1. ZIPのSHA-256を、配布元の[SHA256SUMS.txt](SHA256SUMS.txt)と照合してから展開します。
2. `guide/`の日英HTML、または`Lab/README.md`を開きます。Notebook・データ・実行ツールのコマンドは`source/`から実行します。
3. 第4章でワークスペース、容量、権限、空の作業フォルダー、参加者IDを確認します。
4. 第24章の配置手順と各章の操作・完了条件を、順番に進めます。

Verify the ZIP's external SHA-256, extract every file, open the HTML in `guide/` or `Lab/README.md`, and run source commands from `source/`. Start with Chapter 4's prerequisites and follow Chapter 24's deployment stages together with the corresponding chapter procedures.

| 順序 / Order | 箇所 / Sections | 実施すること / Work |
| --- | --- | --- |
| 1 | 第4章 → 24.4–24.6 | 認証、フォルダー照合、配置計画、基盤の作成 / Authentication, folder mapping, plan and core creation |
| 2 | 第5–8章 | Lakehouse、Notebook、主Ontology、Eventhouseの確認 / Inspect the created resources |
| 3 | 24.7 → 第9–11章 | 3ファイルの各1回の取り込み、品質処理とGold / Ingest each file once, verify quality and Gold |
| 4 | 24.8 → 第12–13章 | Semantic model、意味、モデル、主Agentの作成と確認 / Create and inspect the model and main Agent |
| 5 | 第17章 | SQLビュー、ソース選択、指示、例、公開・読み戻し / Views, selections, instructions, examples, publication and readback |
| 6 | 第19章・付録C | 固定問題による採点と改善案の比較 / Score fixed questions and compare improvements |

主OntologyとData Agentは各1件です。ソース接続、設定の一致、実際の回答品質を別々に確認します。まず10回・84条件の基本演習を実施し、必要に応じて公開評価49回・290条件／段階へ進みます。改善前後で質問・条件・データを固定し、採点基準や期待値をAgentの指示へ入れません。設定が一致しても、同じ点数を保証するものではありません。

Keep one main Ontology and one Data Agent. Check source connectivity, configuration parity and actual answer quality separately. Start with ten practice attempts and 84 conditions, then use the full public 49-attempt, 290-condition evaluation per phase when needed. Keep questions, criteria and data fixed across comparisons; do not put scoring criteria or expected answers into Agent instructions. Matching configuration does not guarantee a score.

## 配布ファイルの確認 / Delivery verification

[検査記録](DOCUMENT_VALIDATION.json)は、このHTMLの実際のハッシュ、共有モデルの内容照合、Chromiumの日英操作・モバイル表示・印刷PDF検査を記録します。ZIPは同じHTML、全Lab、実行ソースとハッシュ一覧を収録します。ローカル文書検査は、Fabricの配置やAI回答品質の合格を意味しません。印刷PDFの生成と、全ページの目視確認も区別します。

The [validation receipt](DOCUMENT_VALIDATION.json) records the exact HTML digest, shared-model coverage, and actual Chromium bilingual, mobile and print-PDF checks. The ZIP includes that HTML, the complete Lab, executable sources and checksum inventories. Local document checks do not certify Fabric deployment or AI answer quality; PDF generation is distinct from visual review of every page.

[現行配布物の生成方法](../../../tools/docs/CURRENT_HTML_LAB.md)
