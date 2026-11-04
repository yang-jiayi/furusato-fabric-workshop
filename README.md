# Furusato Workshop 3.1.0

合成データを使い、Microsoft Fabric の Lakehouse・Eventhouse・Ontology・Semantic model・Data Agent をつなぐ日英ハンズオンです。

[日英HTML手順書をダウンロード](docs/furusato-workshop-v3-1-0-complete.html?raw=true)して、ブラウザーで開いてください。HTMLは必要なスタイル・動作・図を含む単一ファイルで、教材を読むだけならZIPやWebサイトは不要です。[GitHub Lab](Lab/README.md)は各手順の番号付きMarkdown版です。Notebook・データ・設定・コマンドなど、実習を実行する資産には同じ版の[参加者用ZIP](docs/Furusato_Workshop_v3.1.0_current.zip?raw=true)を使い、[SHA-256一覧](docs/SHA256SUMS.txt)で照合してください。[配布物と検証記録](docs/README.md)で現行ファイルを確認できます。リポジトリを使う場合はZIPの代わりにこのGitHub上の資産を利用できます。

![Furusato Workshopの構成図](Lab/assets/pc-01-architecture-ja.svg)

## 進め方

1. [第4章](Lab/04-prerequisites-deployment-scope-and-safe-execution/README.md)で前提条件と安全なデプロイ範囲を確認します。
2. [第24章](Lab/24-automated-deployment-operations-and-cleanup/README.md)と第5〜13章に沿って対象リソースをデプロイまたは確認します。既存リソースを重複作成したり、処理済み入力を再処理したりしません。
3. [第17章](Lab/17-fabric-data-agent-and-code-interpreter/README.md)でモデルとData Agentを構成し、同じAgentのCode Interpreterを確認して、公開内容を読み戻します。
4. [第19章](Lab/19-evaluate-and-improve-ai-answer-quality/README.md)と[付録C](Lab/appendix-c-evaluation-questions-scoring-and-recording-forms/README.md)の固定質問・根拠要件で回答を評価します。

本教材は24章・5付録で構成されています。HTML教科書を参加者向けの主教材とし、番号付きの各手順へGitHub上から移動するにはLabを使います。どちらも日本語と英語に対応しています。

第12章では、明示メジャー・依存列を含む AI schema と、モデル側の Prep for AI の設定・確認を行います。モデル用本文と共通の Agent 指示は [版管理された設定資産](workshop/v3.0.0-preview/powerbi/prep-for-ai/schema.json)で分離しています。ファイルを配布・配置するだけではモデルの Prep for AI は有効になりません。許可された環境で Apply・読み戻し・生成 DAX の検証を行い、未適用と未評価を区別してください。

設定後は Copilot pane を開き直し、LSDL 同期・Direct Lake 索引の反映を確認してから評価します。Git/pipeline での tooling 変更には別途許可された service refresh が必要で、Direct Lake/DirectQuery の同期は1日1回です。Verified answers は native authoring の任意候補で CI/CD 非対応、Fabric IQ 有効時は返されません。未確認の状態を適用済み・合格とは扱いません。

第12.6節の現行共通 Agent 指示は、明示された母集団・ソース・期間を優先します。指定のない通常の Workshop 概要・静的ランキングは Lakehouse の静的2025スナップショットを使い、人気は件数・金額の両方を示します。明示的な Gold・受入増分・モデルメジャーの分析は直接 Semantic model、年を省略した8月の運用観測は KQL の2026年8月 UTC が対象です。寄附先と居住地などの曖昧さは確認し、異なる母集団を合算しません。共通指示はLFで3,394 UTF-16単位、SHA256 `7edbd1657c49f19db27dfeeaa23a1d9b720717cdb22b90263017aa2c3f238f26` で、Draft と Published の公開設定の読み戻しは確認済みです。回答品質の測定は未実施です。参加者は17.9の prepare コマンドの `--common-guidance` を含む経路で同じ本文を固定し、17.10以降も同じ候補を使います。不変な source profile は必須の比較入力であり、モデル用本文とソース固有の手順は変更しません。公開設定の確認はモデルPrep・ソース準備完了・実効的なAI反映・回答精度の証明ではなく、GQL実行やMetricsの利用可能性も証明しません。

## 前提条件と根拠

利用が許可されたFabricワークスペースとフォルダー、稼働中の容量、必要な権限を用意します。機能の利用可否はテナント、リージョン、容量によって異なる場合があります。設定だけではクエリの実行、機能の準備完了、AI回答の正しさは確認できないため、実行結果と読み戻しを別々に確認してください。

データは合成データです。自治体名とコードは参照ラベルであり、寄付、寄付者、事業者、返礼品は架空です。静的レコード、運用観測、品質処理後のGoldデータは、母集団と粒度が異なるため区別してください。実際に公開したWorkshopを、記録したソース、クエリ、結果に基づいて評価します。本READMEは評価スコアや回答品質を保証しません。

参加者用ZIPにはHTML、Lab、実行資産、テキスト形式の参照添付ファイルが含まれます。WordまたはPDF形式の手順書・出力ファイルは含まれません。業務要件の添付ファイルはプレーンテキストです。上流アイコンの利用条件は[ソース通知](docs/assets/architecture/upstream/NOTICE.txt)に記載しています。

Git checkoutではリポジトリのルートからコマンドを実行します。ZIPを使う場合は展開し、`source/`ディレクトリから実行してください。資格情報、環境固有の接続情報、非公開の回答ログをGitHubへ追加しないでください。[SECURITY.md](SECURITY.md)も参照してください。

## English

This bilingual, hands-on Microsoft Fabric workshop uses synthetic data to connect a Lakehouse, Eventhouse, Ontology, semantic model and Data Agent.

Download the **[HTML textbook](docs/furusato-workshop-v3-1-0-complete.html?raw=true)** and open it in a browser. It is a single file containing its required styles, interactions and figures, so reading the manual does not require the ZIP or a hosted website. The [GitHub Lab](Lab/README.md) is the numbered Markdown companion. For hands-on execution, use the same-edition [participant ZIP](docs/Furusato_Workshop_v3.1.0_current.zip?raw=true) for notebooks, data, configuration and commands, and verify it with [SHA-256](docs/SHA256SUMS.txt). See the [download and validation index](docs/README.md) for the current files. If you work from the repository, its GitHub assets can be used instead of the ZIP.

![Furusato Workshop architecture](Lab/assets/pc-01-architecture-en.svg)

Follow [Chapter 4](Lab/04-prerequisites-deployment-scope-and-safe-execution/README.md) for prerequisites and scope, [Chapter 24](Lab/24-automated-deployment-operations-and-cleanup/README.md) and Chapters 5–13 for deployment and data/model checks, [Chapter 17](Lab/17-fabric-data-agent-and-code-interpreter/README.md) to configure the Agent, confirm Code Interpreter on that same agent and read back the published setup, and [Chapter 19](Lab/19-evaluate-and-improve-ai-answer-quality/README.md) plus [Appendix C](Lab/appendix-c-evaluation-questions-scoring-and-recording-forms/README.md) for answer evaluation.

The course has 24 chapters and five appendices. Use the HTML as the primary participant manual and the Lab for direct GitHub navigation to each numbered step. The participant ZIP contains HTML, Lab, runtime assets and plain-text reference attachments; it contains no Word or PDF manuals or exports. The business requirements attachment is plain text, and the upstream icon usage terms are retained in the [source notice](docs/assets/architecture/upstream/NOTICE.txt).

Chapter 12 covers explicit measures, dependency-inclusive AI schema and model-level Prep for AI setup/verification. The [versioned configuration assets](workshop/v3.0.0-preview/powerbi/prep-for-ai/schema.json) separate model business rules from common Agent guidance. Shipping or deploying files does not activate model Prep for AI. Apply only in an authorized environment, reopen/read back the settings and validate generated DAX; distinguish not applied from not evaluated.

Reopen the Copilot pane and verify LSDL sync/Direct Lake indexing before evaluation. Git/pipeline tooling edits require a separately authorized service refresh; Direct Lake/DirectQuery sync only once a day. Verified answers are optional native-authoring candidates with no CI/CD support and are not returned when Fabric IQ is enabled. Do not label unverified settings as applied or passing.

The current common Agent guidance in 12.6 prioritizes explicit population, source and period. Otherwise ordinary workshop overviews and static rankings use the Lakehouse static 2025 snapshot, with both count and amount for popularity. Explicit Gold/accepted-increment/model-measure analysis uses the direct semantic model; August operational observations without a year use KQL's August 2026 UTC context. Clarify recipient-versus-residence ambiguity and never add incompatible populations. The common text has3,394 UTF-16 units with LF line endings and SHA256 `7edbd1657c49f19db27dfeeaa23a1d9b720717cdb22b90263017aa2c3f238f26`; Draft and Published configuration readbacks have been verified. Answer-quality measurement is pending. The participant path includes `--common-guidance` in the17.9 prepare command to bind this text and retains the same candidate from17.10 onward. The immutable source profile remains required comparison input; model text and source-owned recipes remain unchanged. Published configuration verification does not establish model Prep, source readiness, effective AI serving or answer accuracy, nor does it prove GQL execution or Metrics availability.

Use an authorized Fabric workspace and folder with active capacity and the required permissions. Feature availability may vary by tenant, region and capacity. Configuration is not proof of execution, feature readiness or answer correctness. All workshop data is synthetic. Static donations, operational observations and quality-processed Gold have different populations and grains and must remain distinct. Verify actual sources, queries and results; no evaluation score or answer-quality guarantee is made.

Run commands from the repository root in a Git checkout, or from the extracted ZIP’s `source/` directory. Never add credentials, environment-specific connection details or private answer logs to GitHub. Review [SECURITY.md](SECURITY.md).
