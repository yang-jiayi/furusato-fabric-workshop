# Furusato Workshop Lab

Microsoft Fabric の Lakehouse・Eventhouse・Ontology・Semantic model・Data Agent を、合成データで順に構築して確かめます。この Lab と [HTML 手順書](../docs/furusato-workshop-v3-0-0-complete.html) は、最新版の操作手順を提供します。

初回は **4章 → 24.4〜24.6 → 5〜8章の確認 → 24.7と9〜11章 → 24.8 → 17章 → 19章・付録C** の順で進めます。作成済みのデータやアイテムを重複して作成・取り込みしません。各章の目次から操作ページへ進み、完了条件を確認してください。

各画面キャプチャは1つの操作ページにまとめ、キャプチャが不要な説明・コマンド・参照表も省略せずに収録しています。各ページ末尾の **English** を開くと同じ内容を英語で読めます。

- [1. シナリオ・学習目標・完成アーキテクチャ](01-scenario-learning-goals-and-target-architecture/README.md)
- [2. DBA・BI エンジニアのための Ontology 設計](02-ontology-design-for-dba-and-bi-engineers/README.md)
- [3. Furusato 業務モデルの設計根拠](03-rationale-for-the-furusato-business-model/README.md)
- [4. 前提条件・配置範囲・安全な実行](04-prerequisites-deployment-scope-and-safe-execution/README.md)
- [5. Lakehouse と Notebook 01](05-lakehouse-and-notebook-01/README.md)
- [6. Ontology・Entity・Property の作成](06-creating-the-ontology-entity-types-and-properties/README.md)
- [7. Relationship と静的モデルの検証](07-relationships-and-static-model-validation/README.md)
- [8. Eventhouse と KQL スキーマ](08-eventhouse-and-the-kql-schema/README.md)
- [9. Pipeline と OneLake イベント連携](09-pipeline-and-onelake-event-integration/README.md)
- [10. 増分取り込みと時系列バインディング](10-increment-ingestion-and-time-series-bindings/README.md)
- [11. Notebook 05 による品質処理と Gold](11-quality-processing-and-gold-with-notebook-05/README.md)
- [12. Semantic model と Ontology の Metrics](12-semantic-model-and-ontology-metrics/README.md)
- [13. Metadata・Business Rules・Notebook 02](13-metadata-business-rules-and-notebook-02/README.md)
- [14. Namespace・継承・共有プロパティ](14-namespaces-inheritance-and-shared-properties/README.md)
- [15. Ontology Copilot（組み込みの Ontology agent）による設計・改善・照会](15-design-improve-and-query-with-ontology-copilot-the-built-in-ontol/README.md)
- [16. 選択的な Graph の実体化と GQL](16-selective-graph-materialization-and-gql/README.md)
- [17. Fabric Data Agent と Code Interpreter](17-fabric-data-agent-and-code-interpreter/README.md)
- [18. 業務シナリオによる横断演習](18-cross-source-business-scenario-exercises/README.md)
- [19. AI の回答品質の評価と改善](19-evaluate-and-improve-ai-answer-quality/README.md)
- [20. MCP と可視化による外部利用](20-external-consumption-through-mcp-and-visualization/README.md)
- [21. Version history による変更管理](21-change-management-with-version-history/README.md)
- [22. RDF／OWL の Import・Export](22-rdf-owl-import-and-export/README.md)
- [23. Publish・共有・ガバナンス](23-publish-sharing-and-governance/README.md)
- [24. 自動配置・運用・クリーンアップ](24-automated-deployment-operations-and-cleanup/README.md)
- [付録 A　データ・モデル・期待値リファレンス](appendix-a-data-model-and-expected-value-reference/README.md)
- [付録 B　Notebook・設定・配置パラメーター索引](appendix-b-notebook-configuration-and-deployment-parameter-index/README.md)
- [付録 C　評価問題・採点基準・記録様式](appendix-c-evaluation-questions-scoring-and-recording-forms/README.md)
- [付録 D　任意の追加演習](appendix-d-optional-extensions/README.md)
- [付録 E　トラブルシューティング・公式資料](appendix-e-troubleshooting-and-official-references/README.md)

Notebook・CSV・モデル・Agent 設定は [`workshop/v3.0.0-preview/`](../workshop/v3.0.0-preview/) にあります。ローカルコマンドはリポジトリのルート、参加者用 ZIP では展開先の `source/` を起点に実行します。
