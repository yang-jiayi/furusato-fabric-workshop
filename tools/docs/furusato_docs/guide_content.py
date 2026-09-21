"""Content model for the v2.7.0 participant guide (chapters 1-4: concepts)."""

from __future__ import annotations

from .context import RuntimeContext, num, yen

REFERENCE_LINKS: tuple[tuple[str, str], ...] = (
    ("Fabric IQ overview", "https://learn.microsoft.com/en-us/fabric/iq/overview"),
    ("Workspace folders", "https://learn.microsoft.com/en-us/fabric/fundamentals/workspaces-folders"),
    ("Ontology overview", "https://learn.microsoft.com/en-us/fabric/iq/ontology/overview"),
    (
        "Ontology tenant settings",
        "https://learn.microsoft.com/en-us/fabric/iq/ontology/overview-tenant-settings",
    ),
    (
        "Create entity types",
        "https://learn.microsoft.com/en-us/fabric/iq/ontology/how-to-create-entity-types",
    ),
    ("Bind data", "https://learn.microsoft.com/en-us/fabric/iq/ontology/how-to-bind-data"),
    (
        "Create relationship types",
        "https://learn.microsoft.com/en-us/fabric/iq/ontology/how-to-create-relationship-types",
    ),
    (
        "Semantic enrichment",
        "https://learn.microsoft.com/en-us/fabric/iq/ontology/how-to-add-semantic-enrichment",
    ),
    (
        "Entity type details / refresh",
        "https://learn.microsoft.com/en-us/fabric/iq/ontology/how-to-view-entity-type-details",
    ),
    ("Graph overview / GQL", "https://learn.microsoft.com/en-us/fabric/graph/overview"),
    ("Graph schema best practices", "https://learn.microsoft.com/en-us/fabric/graph/design-graph-schema"),
    ("Graph limitations", "https://learn.microsoft.com/en-us/fabric/graph/limitations"),
    (
        "Fabric Data Agent concept",
        "https://learn.microsoft.com/en-us/fabric/data-science/concept-data-agent",
    ),
    (
        "Create a Fabric Data Agent",
        "https://learn.microsoft.com/en-us/fabric/data-science/how-to-create-data-agent",
    ),
    (
        "Data Agent source capability matrix",
        "https://learn.microsoft.com/en-us/fabric/data-science/data-agent-add-datasources",
    ),
    (
        "Data Agent configuration best practices",
        "https://learn.microsoft.com/en-us/fabric/data-science/data-agent-configuration-best-practices",
    ),
    (
        "Data Agent example queries",
        "https://learn.microsoft.com/en-us/fabric/data-science/data-agent-example-queries",
    ),
    (
        "Semantic model best practices for Data Agent",
        "https://learn.microsoft.com/en-us/fabric/data-science/semantic-model-best-practices",
    ),
    (
        "Power BI date-table design guidance",
        "https://learn.microsoft.com/en-us/power-bi/guidance/model-date-tables",
    ),
    (
        "Evaluate a Data Agent",
        "https://learn.microsoft.com/en-us/fabric/data-science/evaluate-data-agent",
    ),
    (
        "Data Agent source control, CI/CD and ALM",
        "https://learn.microsoft.com/en-us/fabric/data-science/data-agent-source-control",
    ),
    (
        "Data Agent sharing",
        "https://learn.microsoft.com/en-us/fabric/data-science/data-agent-sharing",
    ),
    (
        "Data Agent consumption",
        "https://learn.microsoft.com/en-us/fabric/fundamentals/data-agent-consumption",
    ),
    ("Data Agent runtime", "https://learn.microsoft.com/en-us/fabric/data-science/data-agent-runtime"),
    (
        "Ontology as a Data Agent source (troubleshooting)",
        "https://learn.microsoft.com/en-us/fabric/iq/ontology/resources-troubleshooting",
    ),
    ("Ontology glossary", "https://learn.microsoft.com/en-us/fabric/iq/ontology/resources-glossary"),
    (
        "Agent integration options for Ontology",
        "https://learn.microsoft.com/en-us/fabric/iq/ontology/concepts-agent-integration",
    ),
    (
        "Generate an ontology from a semantic model",
        "https://learn.microsoft.com/en-us/fabric/iq/ontology/concepts-generate",
    ),
    ("Eventhouse overview", "https://learn.microsoft.com/en-us/fabric/real-time-intelligence/eventhouse"),
    (
        "Materialized views (KQL)",
        "https://learn.microsoft.com/en-us/kusto/management/materialized-views/materialized-view-overview",
    ),
    (
        "Copy activity (Data pipeline)",
        "https://learn.microsoft.com/en-us/fabric/data-factory/copy-data-activity",
    ),
    (
        "OneLake event triggers for pipelines",
        "https://learn.microsoft.com/en-us/fabric/data-factory/pipeline-storage-event-triggers",
    ),
    ("Fabric Activator overview", "https://learn.microsoft.com/en-us/fabric/real-time-intelligence/data-activator/activator-introduction"),
    (
        "Copilot in Fabric overview",
        "https://learn.microsoft.com/en-us/fabric/fundamentals/copilot-fabric-overview",
    ),
    (
        "Copilot privacy, security and responsible AI",
        "https://learn.microsoft.com/en-us/fabric/fundamentals/copilot-privacy-security",
    ),
    (
        "Copilot consumption and billing",
        "https://learn.microsoft.com/en-us/fabric/fundamentals/copilot-fabric-consumption",
    ),
    (
        "Copilot tenant settings",
        "https://learn.microsoft.com/en-us/fabric/admin/service-admin-portal-copilot",
    ),
    (
        "Capacity Metrics app (compute page)",
        "https://learn.microsoft.com/en-us/fabric/enterprise/metrics-app-compute-page",
    ),
    (
        "Workspace customer-managed keys",
        "https://learn.microsoft.com/en-us/fabric/security/workspace-customer-managed-keys",
    ),
    (
        "Microsoft Purview and Fabric",
        "https://learn.microsoft.com/en-us/fabric/governance/microsoft-purview-fabric",
    ),
    (
        "Azure Preview Supplemental Terms",
        "https://azure.microsoft.com/en-us/support/legal/preview-supplemental-terms/",
    ),
    (
        "Microsoft AI principles and approach",
        "https://www.microsoft.com/en-us/ai/principles-and-approach",
    ),
)


MENTAL_MODEL_ROWS = (
    (
        "第一の目的",
        "データを正しく保存・更新し、整合性を守ること",
        "集計・フィルター・レポートを高速かつ一貫して行うこと",
        "業務上の意味・同一性・たどれる関係を宣言すること",
    ),
    (
        "基本単位",
        "テーブル / 主キー / 外部キー",
        "ファクト / ディメンション / メジャー",
        "Entity Type / Property / Relationship Type",
    ),
    (
        "設計原則",
        "正規化（重複排除と更新異常の回避）",
        "スタースキーマ（分析しやすい非正規化）",
        "ビジネスグラフ（概念と関係の明示）",
    ),
    (
        "つながりの意味",
        "JOIN は実装手段。どの列で結べるかを表す",
        "リレーションシップはフィルター伝播の経路",
        "Relationship は「何を主張し、何を主張しないか」を表す",
    ),
    (
        "曖昧さの扱い",
        "アプリケーション側のロジックで吸収する",
        "レポート作者の合意とドキュメントで吸収する",
        "同義語・説明・境界としてモデルに埋め込む",
    ),
    (
        "利用者",
        "アプリケーションと開発者",
        "レポート作成者とアナリスト",
        "人・レポート・エージェントの三者が同じ定義を共有する",
    ),
)


PATTERN_ROWS = (
    (
        "独立した同一性を持つマスタ / ディメンション",
        "Entity Type",
        "業務側が名前と ID で会話でき、それ自体が主語になる。",
        "Prefecture / Municipality / Donor / GiftCategory / Gift / Supplier",
    ),
    (
        "同一性・金額・時刻・状態を持つトランザクションファクト",
        "トランザクション Entity Type",
        "1 行が業務イベントとして参照・追跡され、他概念の交差点になる。",
        "Donation",
    ),
    (
        "外部キー 2 本だけのブリッジ",
        "Relationship のコンテキスト表（Entity にしない）",
        "行そのものに業務的な名前・属性・ライフサイクルがない。",
        "business_gifts → SupplierProvidesGift",
    ),
    (
        "独立した属性やライフサイクルを持つブリッジ",
        "連関 Entity Type",
        "契約日・状態・金額など、関係そのものに問い合わせたい属性がある。",
        "本データセットには該当なし（判断基準として提示）",
    ),
    (
        "1 エンティティにつき 1 値の属性",
        "Property",
        "単独では主語にならず、常に親エンティティの説明に使われる。",
        "MunicipalityName / DonorAge / DonationPaymentMethod",
    ),
    (
        "複合粒度の事前集計",
        "メトリック / フロー Entity Type",
        "「A×B の集計値」を安定した ID で参照させ、二重集計を構造的に防ぐ。",
        "MunicipalityCategoryMetric / PrefectureCategoryMetric / PrefectureDonationFlow",
    ),
    (
        "既存エンティティに対する時刻付き観測",
        "time-series バインディング",
        "観測はエンティティを増やさない。既存エンティティの時間軸の測定値になる。",
        "Municipality の IncomingDonationAmountYen",
    ),
    (
        "イベント自体が業務上の主語になる",
        "イベント Entity Type",
        "「そのイベント」を ID で参照し、状態遷移や関係を辿る要求がある。",
        "本ワークショップでは採用しない（観測は集約ビューのみ）",
    ),
    (
        "監査・制御・技術メタデータ",
        "Ontology から除外",
        "業務語彙ではなく実装都合の情報。意味層に持ち込むと質問空間が汚れる。",
        "audit_* / publish control テーブル",
    ),
)


ANTIPATTERN_ROWS = (
    (
        "テーブルをそのまま Entity にする",
        "正規化・非正規化の都合がそのまま業務語彙になり、質問が実装に依存する。",
        "業務上の主語だけを Entity にし、残りは Property か Relationship のコンテキストにする。",
    ),
    (
        "外部キーをすべて Relationship にする",
        "意味のない経路が増え、エージェントが誤った多段経路を選ぶ。",
        "業務的に意味のある FK 経路だけを Relationship にする。",
    ),
    (
        "Relationship に向きの意味を与えない",
        "「登録している」と「受け取った」が同じ経路として扱われ、集計が壊れる。",
        "方向・カーディナリティ・否定的意味（何を証明しないか）を宣言する。",
    ),
    (
        "多対多の橋を通して金額を集計する",
        "1 つの Gift に複数 Supplier がいると金額が重複計上される。",
        "集計ガードを宣言し、配賦ルールがない限り橋越しの金額集計を禁止する。",
    ),
    (
        "複合粒度の集計を明細から毎回計算させる",
        "粒度の取り違えと二重集計が起きやすく、回答が不安定になる。",
        "複合粒度だけをメトリック Entity として独立させ、再集計を禁止する。",
    ),
    (
        "観測イベントを明細エンティティとして追加する",
        "静的スナップショットと観測が合算され、件数が意味を失う。",
        "観測は time-series バインディングにとどめ、粒度を明示的に分離する。",
    ),
    (
        "表示名をキーとして使う",
        "同名の自治体・返礼品が存在すると、部分一致で誤ったインスタンスに到達する。",
        "安定 ID をキーにし、表示名は表示専用 Property として分離する。",
    ),
    (
        "設計より先にバインドする",
        "物理列の都合で概念が歪み、後からの変更コストが跳ね上がる。",
        "概念モデルが安定してから物理ソースへバインドする。",
    ),
)


DESIGN_STEPS = (
    "ビジネス上の問いと意思決定から始める。テーブル一覧から始めない。",
    "候補となる概念ごとに粒度（1 行が何を表すか）を 1 文で書き出す。",
    "安定した業務識別子と、表示用ラベルを分離する。",
    "エンティティの境界を決める（どこまでが同じ概念か）。",
    "属性にするか、独立したエンティティにするかを判断する。",
    "業務的に意味のある外部キー経路だけを Relationship に変換する。",
    "Relationship の方向・カーディナリティ・否定的意味を宣言する。",
    "複合粒度の事前集計はメトリック / フロー Entity として切り出す。",
    "時刻付き観測は time-series バインディングか、イベント Entity かを選ぶ。",
    "概念モデルが安定してから、物理ソースへバインドする。",
    "簡潔なセマンティック補足（説明・同義語・集計ガード）を加える。",
    "キー・FK 解決・件数・経路・曖昧性・境界を検証する。",
)


GRAIN_ROWS = (
    (
        "粒度（grain）",
        "1 行 / 1 インスタンスが表す業務上の単位。",
        "「1 寄付申込」「1 自治体」「1 自治体 × 1 カテゴリ」「1 分バケットの観測」",
        "粒度を書けない概念は、まだ設計が決まっていない。",
    ),
    (
        "業務識別子",
        "業務側が会話で使い、時間が経っても変わらない ID。",
        "MunicipalityId（全国地方公共団体コード）、DonationId",
        "Ontology の Entity type key には業務識別子を使う。",
    ),
    (
        "代理キー",
        "実装都合で採番された内部キー。業務会話には現れない。",
        "ロード時の連番、ハッシュキー",
        "Entity type key にはしない。必要なら Property として保持する。",
    ),
    (
        "表示名",
        "人間が読むためのラベル。一意とは限らない。",
        "MunicipalityDisplayName（{自治体名} / {都道府県名}）",
        "キーにしない。曖昧な場合は ID を併記させる。",
    ),
)


RELATIONSHIP_SEMANTICS_ROWS = (
    (
        "RDB の外部キー",
        "参照整合性の制約。「この値は親表に存在する」だけを保証する。",
        "向きは制約の向きであり、業務上の意味は持たない。",
    ),
    (
        "BI のフィルター方向",
        "フィルターがどちらへ伝播するかという計算上の設定。",
        "単方向 / 双方向はレポートの都合であり、業務の主張ではない。",
    ),
    (
        "Ontology の Relationship 方向",
        "「誰が何に対して何をしたか」という業務上の主張。",
        "逆方向トラバースは可能だが、宣言された向きは保持される。",
    ),
    (
        "カーディナリティ",
        "1 側と多側の業務的な制約。データ品質の期待値でもある。",
        "「1 自治体は必ず 1 都道府県に属する」は業務ルールとして宣言する。",
    ),
    (
        "否定的意味",
        "その関係が「証明しないこと」。エージェントの飛躍を止める。",
        "SupplierProvidesGift はカタログ登録であり、発送も売上配賦も証明しない。",
    ),
)


#: The layer vocabulary used across the guide, the diagrams and the checklist.
#: "基幹エンティティ層" is deliberately explicit about its composition, because
#: "明細層" and "詳細層" were read as "the raw fact table" by RDB practitioners.
CORE_ENTITY_LAYER = "基幹エンティティ層（マスタ 6 + トランザクション 1）"
METRIC_LAYER = "集計層（メトリック）"
FLOW_LAYER = "集計層（フロー）"
MASTER_ENTITIES = ("Prefecture", "Municipality", "Donor", "GiftCategory", "Gift", "Supplier")
TRANSACTION_ENTITIES = ("Donation",)
AGGREGATE_ENTITIES = (
    "MunicipalityCategoryMetric",
    "PrefectureCategoryMetric",
    "PrefectureDonationFlow",
)


def entity_layer(name: str) -> str:
    """Return the layer label for an entity type."""
    if name in AGGREGATE_ENTITIES:
        return FLOW_LAYER if name.endswith("Flow") else METRIC_LAYER
    if name in TRANSACTION_ENTITIES:
        return "基幹エンティティ層（トランザクション）"
    return "基幹エンティティ層（マスタ）"


def metric_decision_rows() -> tuple[tuple[str, str, str], ...]:
    return (
        (
            "単一エンティティの集計値",
            "親エンティティの Property にする",
            "MunicipalityStaticCount / MunicipalityStaticTotalYen は Municipality の Property。",
        ),
        (
            "2 つ以上のエンティティの交差による集計値",
            "メトリック Entity にする",
            "自治体 × カテゴリ、都道府県 × カテゴリ、居住地 × 受入先。",
        ),
        (
            "順位（ランク）",
            "スコープ付きの Property にする",
            "全国スコープと都道府県内スコープを別 Property に分け、足し算を禁止する。",
        ),
        (
            "明細から毎回計算できる値",
            "原則として明細に任せる",
            "ただし粒度の取り違えが起きやすい場合は、事前集計を独立させる。",
        ),
    )


def timeseries_decision_rows() -> tuple[tuple[str, str, str], ...]:
    return (
        (
            "観測に独立した業務上の同一性がない",
            "time-series バインディング",
            "観測はエンティティを増やさず、既存エンティティの測定値になる。",
        ),
        (
            "観測を ID で参照し、他の概念と関係を結びたい",
            "イベント Entity",
            "イベント自体が主語になり、状態や関係を持つ。",
        ),
        (
            "観測はダッシュボードと監視のためだけに使う",
            "time-series バインディング",
            "基幹エンティティ層を汚さず、Ontology の質問空間を小さく保てる。",
        ),
        (
            "重複排除・履歴補正が業務要件にある",
            "イベント Entity または別レイヤー",
            "集約ビューだけでは重複排除を証明できない点に注意する。",
        ),
    )


def furusato_entity_rationale(context: RuntimeContext) -> list[list[str]]:
    reasons = {
        "Prefecture": "全国 47 の行政区分。受入側と在住側の 2 つの読み方を 1 つのエンティティで区別して保持する。",
        "Municipality": "寄付の受入先であり、返礼品カタログの主体でもある。唯一 time-series 観測のキーにもなる。",
        "Donor": "寄付の主体。合成データだが、人物に関する推論は行わない境界を明示する。",
        "GiftCategory": "返礼品の分類。カテゴリ単位の分析要求が多いため独立させる。",
        "Gift": "返礼品そのもの。自治体がカタログ登録し、寄付が選択する対象。",
        "Supplier": "返礼品を供給する事業者。カタログ登録の主体であり、履行の主体ではない。",
        "Donation": "唯一のトランザクション粒度。ID・金額・時刻・支払方法・寄付者・受入先・選択返礼品を持つ。",
        "MunicipalityCategoryMetric": "自治体 × カテゴリという複合粒度の事前集計。明細からの再集計を防ぐ。",
        "PrefectureCategoryMetric": "都道府県（受入側）× カテゴリの複合粒度の事前集計。",
        "PrefectureDonationFlow": "居住地都道府県 → 受入先都道府県のフロー。方向を持つ集計を独立させる。",
    }
    layers = {
        "MunicipalityCategoryMetric": "メトリック層",
        "PrefectureCategoryMetric": "メトリック層",
        "PrefectureDonationFlow": "フロー層",
    }
    rows: list[list[str]] = []
    for entity in context.entities:
        rows.append(
            [
                entity.name,
                entity_layer(entity.name),
                entity.key_property,
                num(context.node_count(entity.name)),
                reasons[entity.name],
            ]
        )
    return rows


def furusato_relationship_rationale(context: RuntimeContext) -> list[list[str]]:
    reasons = {
        "MunicipalityInPrefecture": "受入側の行政包含。受入地理をたどる唯一の経路。",
        "DonorLivesInPrefecture": "寄付者の居住地。受入地理とは別の意味を持つため分離する。",
        "SupplierInPrefecture": "事業者の所在地。寄付の受入先とは無関係であることを明示する。",
        "GiftInCategory": "返礼品の分類。カテゴリ集計の入口。",
        "MunicipalityCatalogsGift": "自治体によるカタログ掲載。受入金額の集計経路ではない。",
        "SupplierProvidesGift": "事業者によるカタログ登録。多対多のため金額集計を禁止する。",
        "DonorMadeDonation": "寄付の実行主体。金額集計は Donation 側で行う。",
        "DonationToMunicipality": "受入先の確定経路。受入件数・金額の正式な集計経路。",
        "DonationSelectedGift": "選択された返礼品。購入・発送ではない。",
        "MunHasCategoryMetric": "自治体から複合粒度メトリックへの入口。",
        "MunMetricForCategory": "複合粒度メトリックからカテゴリへの参照。",
        "PrefHasCategoryMetric": "受入都道府県から複合粒度メトリックへの入口。",
        "PrefMetricForCategory": "複合粒度メトリックからカテゴリへの参照。",
        "ResidencePrefHasFlow": "居住地側（フローの起点）。方向を持つ集計の入口。",
        "FlowToRecipientPref": "受入側（フローの終点）。起点と終点を入れ替えない。",
    }
    rows: list[list[str]] = []
    for relationship in context.relationships:
        rows.append(
            [
                relationship.name,
                f"{relationship.origin} → {relationship.target}",
                relationship.cardinality or relationship.attributes.get("grain", ""),
                relationship.mapping_table,
                num(context.edge_count(relationship.name)),
                reasons[relationship.name],
            ]
        )
    return rows


def semantic_boundaries(context: RuntimeContext) -> tuple[tuple[str, str, str], ...]:
    return (
        (
            "SupplierProvidesGift",
            "事業者がその返礼品をカタログに登録している。",
            "製造・発送・履行・売上配賦・特定の寄付との紐付けは証明しない。",
        ),
        (
            "DonationSelectedGift",
            "その寄付で選択された返礼品。",
            "購入・出荷・受領・満足度は証明しない。",
        ),
        (
            "MunicipalityCatalogsGift",
            "自治体が掲載している返礼品。",
            "受入金額の集計経路ではない（DonationToMunicipality を使う）。",
        ),
        (
            "DonorLivesInPrefecture",
            "寄付者の登録上の居住都道府県。",
            "受入都道府県ではない。両者を足し合わせない。",
        ),
        (
            "IncomingDonationAmountYen（time-series）",
            "運用観測として記録された金額。raw の DonationEvents をそのまま束ねた値。",
            "静的 Donation の件数・金額には加算しない。Donor / Gift / Supplier は特定できない。"
            "重複排除はされていない（deduplication = none）ため、"
            "重複した EventID の行も残ったまま合計される。"
            "「重複なし」「確定値」として扱わない。",
        ),
        (
            "メトリック Entity の各値",
            "宣言された複合粒度における事前集計値。",
            "異なるスコープで再集計しない。ランクは合算しない。",
        ),
        (
            "Donor の年齢・職業・居住地",
            "合成データ上の属性値。",
            "収入・資産・生活水準・税額・性別・動機の推論には使わない。",
        ),
    )


EVALUATION_EVIDENCE_NOTE = (
    "数値が一致していても、各問の評価基準で必要とする期間・スコープ・指標名・根拠の提示が足りなければ合格条件を満たしません。"
    "サービスの汎用的なコンテンツブロックは、業務上の意味やデータの限界を説明できた証拠ではありません。"
    "ブロック文やエラーは秘密情報を除いて記録し、期待する拒否の説明がないものを自動的に PASS にしません。"
    "指示の修正は一般化し、テスト固有の質問文・ID・期待値を与えてはいけません。"
)


def core_scope_rows(context: RuntimeContext | None = None) -> tuple[tuple[str, str, str], ...]:
    rows = (
        ("Lakehouse と静的 8 CSV", "Core", "第 6 章"),
        ("Notebook 01（検証済み Delta テーブルの発行）", "Core", "第 6 章"),
        ("Ontology の作成", "Core", "第 7 章"),
        ("10 Entity Type の手動作成と静的バインディング", "Core", "第 8 章"),
        ("15 Relationship Type の手動作成とバインディング", "Core", "第 9 章"),
        ("静的ゲート（件数・キー・方向・カーディナリティ）", "Core", "第 10 章"),
        ("Eventhouse と KQL スキーマ", "Core", "第 11 章"),
        ("Data Pipeline と OneLake FileCreated トリガー", "Core", "第 12 章"),
        ("増分 1 本目の取り込みと導出結果の確認", "Core", "第 12.4 節"),
        ("残り 2 ファイルの取り込みと KQL 検証", "Core", "第 13 章"),
        ("Municipality への time-series バインディング", "Core", "第 14 章"),
        ("Notebook 02（セマンティックメタデータ一括登録）", "Core", "第 15 章"),
        ("Data Agent の構成と 10 問テスト", "Core", "第 16〜17 章"),
        ("Publish・スモークテスト・共有", "Core", "第 18 章"),
        ("Notebook 03（Ontology 一括作成）", "Optional", "付録 D"),
        ("Notebook 04（Workshop 一括構築）", "Optional", "付録 D"),
        ("Notebook 05（Analytics / DQ / Direct Lake）", "Optional", "付録 D"),
        ("User data functions / Code Interpreter", "Optional", "付録 D"),
        ("Variable Library の手動演習", "Optional", "付録 D"),
    )
    if context is None or not context.is_unified_guide:
        return rows
    return tuple(
        (
            ("共有 SQL/KQL ヘルパーと主 Agent 1 件の構成・元の 10 問", kind, chapter)
            if label == "Data Agent の構成と 10 問テスト"
            else ("同じ Agent の Code Interpreter（Preview）追加演習", "追加演習", "第 17.13 節")
            if label == "User data functions / Code Interpreter"
            else (label, kind, chapter)
        )
        for label, kind, chapter in rows
    )


def troubleshooting_rows(context: RuntimeContext) -> tuple[tuple[str, str, str, str], ...]:
    """Symptom / cause / fix rows, each tied to the chapter it belongs to.

    The rows are returned in chapter order so a participant who is stuck in a
    chapter can scan straight to the block that applies to them.
    """
    names = context.names
    rows: list[tuple[str, str, str, str]] = [
        (
            "第 6 章",
            "Notebook 01 が PARTICIPANT_ID で停止する",
            "000・空文字・4 桁以上の値、または数字以外が含まれている。",
            '`"001"` 〜 `"999"` の 3 桁文字列に修正して先頭セルから再実行する。',
        ),
        (
            "第 6 章",
            "Notebook 01 が SHA-256 不一致で停止する",
            "アップロードした CSV が配布物と異なる、または転送時に改変された。",
            "`SHA256SUMS.txt` と照合し、一致するファイルを再アップロードする。",
        ),
        (
            "第 8 章",
            "Entity type の Instances が 0 件",
            "バインディング先テーブルが未発行、またはキー列の対応付けが誤っている。",
            "Notebook 01 の完了を確認し、Entity type key mapping を見直す。",
        ),
        (
            "第 8 章",
            "自動追加された `_WorkshopGenerationId` が Property に現れる",
            "バインディングの作成時に管理列が自動的に取り込まれた。",
            "保存前に trash アイコンで削除し、表に記載した Property だけを残す。",
        ),
        (
            "第 8 章",
            "英語の Description や businessRole が UI に見当たらない",
            "これらは UI の入力欄ではなく、Notebook 02 が登録する semanticEnrichment の値。",
            "第 8 章では入力しない。第 15 章の適用後に Entity type details で確認する。",
        ),
        (
            "第 9 章",
            "Relationship の件数が期待値と異なる",
            "Mapping table または Matched key の指定が誤っている。",
            "第 9 章の表で Mapping table・Origin key・Target key を再確認する。",
        ),
        (
            "第 9 章",
            "UI にカーディナリティの入力欄がない",
            "UI が持つのは Origin / Target とキーだけ。カーディナリティは宣言メタデータ。",
            "第 15 章の Notebook 02 で 15 件すべてに登録される。第 10 章で登録前後を区別して確認する。",
        ),
        (
            "第 10 章",
            "ソースを更新したのに Instances が古いまま、または 0 件のまま",
            "上流のソースだけが変わり、グラフモデルが再取り込みされていない。",
            "グラフモデルの［Schedule］→［Refresh now］で手動更新する。変更はまとめてから 1 回実行する。",
        ),
        (
            "第 11 章",
            "マテリアライズドビューが空",
            "取り込みが未完了、ビューが未作成、またはビュー作成前の行が対象になっていない可能性がある。",
            f"第 11 章の {len(context.kql_objects)} 個の管理コマンドと raw の SourceFile 別件数を確認する。"
            "既存行を確認せず再取り込みしない。復旧が必要なら対象 KQL Database を特定してファシリテーターと対応する。",
        ),
        (
            "第 12 章",
            "Pipeline が起動しない",
            "ルールが未保存・未起動、アクションの実行エラー、または監視対象パスの不一致。",
            "受信イベントとアクション実行記録を別々に確認する。UI の保存・Start、動的な引数の対応付け、"
            "監視先を確認し、受信済みイベントがあるだけで成功と見なさない。",
        ),
        (
            "第 12 章",
            "トリガー作成直後に実行が走った",
            "準備中のイベント、別のルール、または手動実行の可能性がある。",
            "トリガーを Off にし、イベント時刻・Subject・起動元と `SourceFile` 別件数を確認する。"
            "原因と既存行を確認するまではファイルの削除・再アップロードをしない。",
        ),
        (
            "第 12 章",
            "1 本目のアップロードで `donation_events_001.csv` が二重に入る",
            "再送・重複起動、または空の `Subject` による `IncrementFileName` へのフォールバックが考えられる。",
            "トリガーを Off にし、各 run の `Subject`・導出ファイル名・`SourceFile` 別件数を確認する。"
            "実行の中止やファイルの削除では取り込み済み行は戻らないため、単純に再アップロードしない。",
        ),
        (
            "第 12 章",
            "Activator の名前が既定のままで判別できない",
            "トリガー作成時に Activator が自動生成された。",
            f"`{names['activator']}` にリネームし、ワークスペース内で自分の item を識別できるようにする。",
        ),
        (
            "第 13 章",
            "同じファイルの行が二重に入った",
            "同じ CSV を再アップロードした、またはトリガーが二重に発火した。",
            "トリガーを Off にし、`SourceFile` 単位で期待件数と実行履歴を照合する。"
            "復旧は対象 KQL Database と影響範囲を確認してから行い、他の実習のテーブルを作り直さない。",
        ),
        (
            "第 13 章",
            "取り込んだ列が 1 つずつずれている",
            "取り込みマッピングを指定していない、または既定のマッピングが使われた。",
            "Copy activity で `DonationEvents_IncrementCsvMap` を指定し直す。序数はテーブル定義順とは一致しない。",
        ),
        (
            "第 14 章",
            "time-series バインディングで［Timeseries data］が出ない",
            "Eventhouse テーブルではなく Lakehouse テーブルを選択している。",
            "［Add data binding］→［Eventhouse table or materialized view］から選び直す。",
        ),
        (
            "第 14 章",
            "time-series の観測が 0 件",
            "`DonatedAt` 以外を timestamp column に指定した、またはキー列の対応付けが `MunicipalityID` → `MunicipalityId` になっていない。",
            "timestamp column と列マッピングを修正し、Ontology の更新完了後に再確認する。",
        ),
        (
            "第 14 章",
            "time-series の観測値が 1 分バケットの集約値になっている",
            "ソーステーブルに raw の `DonationEvents` ではなく "
            "`DonationObservationSummaryForAgent` を選択した。",
            "raw の `DonationEvents` を選び直す。Ontology の time-series は raw を読む設計で、"
            "curated ビューを見るのは Data Agent だけ。",
        ),
        (
            "第 15 章",
            "Notebook 02 が DRY_RUN_COMPLETE のまま",
            "`APPLY_CHANGES` が False のまま、または確認フレーズが未入力。",
            "preview 内容を確認したうえで 3 つのゲートをすべて満たす。",
        ),
        (
            "第 15 章",
            f"登録件数が {context.metadata_object_count} にならない",
            "time-series Property が未作成、または Ontology の更新が未完了。",
            "第 14 章のバインディングと更新完了を確認してから再実行する。",
        ),
        (
            "第 15 章",
            "preview では差分 0 だったのに apply で停止する",
            "preview と apply のあいだに、別の編集手段から Ontology が書き換えられた。",
            "編集を止めてから preview をやり直す。manifest が正本であり、合わせるのは Ontology 側。",
        ),
        (
            "第 16 章",
            "Data Agent が Ontology を使わない",
            "ソース追加後に Ontology 側の更新が反映されていない。",
            f"Ontology の更新完了を確認し、{names['dataAgent']} でソースを再読み込みする。",
        ),
        (
            "第 16 章",
            "Data Agent が静的値と観測値を合算する",
            "粒度の分離が指示に反映されていない、またはソース説明が空。",
            "第 16 章のグローバル指示とソース説明を貼り直し、再テストする。",
        ),
        (
            "第 17 章",
            "T07 で一意 EventID の件数が返ってくる",
            "KQL ソースで raw の `DonationEvents` テーブルを選択したままになっている。",
            (
                "第 16.2 節に従い承認済み MV と 3 関数をすべて選択する。raw DonationEvents と EventID は"
                "非選択を保持し、元の 10 問をすべて再テストする。"
            ) if context.is_unified_guide else
            "第 16.2 節に従い Materialized views の 1 件だけを選択し、raw テーブルのチェックを外して再テストする。",
        ),
        (
            "第 17 章",
            "回答が曖昧で PASS か FAIL か判定できない",
            "回答に指標・スコープ・安定 ID のいずれかが欠けている。",
            "UNCLEAR は FAIL として扱う。第 17.12 節の証跡でどこが期待と違うかを見てから、"
            "第 17.11 節の設定層の順で原因を切り分ける。",
        ),
        (
            "第 17 章",
            "質問を送っても Agent が応答せずエラーになる",
            "権限・参照先・構成の問題、またはサービス側の一時的な失敗（EXECUTION_ERROR）。",
            "設定を変えずに同じ質問を最大 2 回まで再実行する。3 回目も失敗したら記録してエスカレーションする。",
        ),
        (
            "第 18 章",
            "公開版のスモークテストが Core と違う結果になる",
            "公開後に version menu が Draft のままか、Runtime が Standard に切り替わっている。",
            "version menu を Published にし、Runtime=Preview と 3 ソースを確認してから再実行する。",
        ),
    ]
    return tuple(rows)
