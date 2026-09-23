/* Shared diagram renderer for the local explorer and the SVG/PNG exports.
 * No framework, network request, tracking, storage or service connection.
 * Microsoft SVG artwork lives unchanged in ../assets/architecture/icons/.
 */
(() => {
  "use strict";

  const ICONS = "../assets/architecture/icons/";
  const FLOWS = ["overview", "static", "events", "agent", "analytics", "control", "outcomes"];
  const esc = value => String(value).replace(/[&<>"']/g, char => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;", "'": "&apos;"
  }[char]));
  const ui = {
    ja: {
      skip: "解説へ移動", appTitle: "アーキテクチャを読み解く",
      localBadge: "合成データ · ローカル解説", expand: "図を広く表示", collapse: "図と解説を並べる",
      navOverview: "全体像", navStatic: "事実と意味", navEvents: "運用の観測", navAgent: "1 件の Agent",
      navAnalytics: "品質と BI", navControl: "承認付き構築", navOutcomes: "学びのまとめ",
      focusOverview: "全体像 · クリックして経路を選択", focusPrefix: "フォーカス",
      diagramHint: "経路とカードをクリック。Tab / Enter / Space で操作できます。",
      fullGuide: "詳しい解説", sourceLink: "実装の根拠", iconLink: "アイコン出典・利用条件", helpLink: "使い方",
      footerScope: "現行 v2.7.0 · 説明用の構成図 · サービスへの接続なし",
      shortcuts: "0–6: 経路 · J/E: 言語 · Esc: 全体像", evidence: "実装の参照",
      diagramTitle: "Furusato Fabric Workshop の全体アーキテクチャ",
      diagramDesc: "単一の Lakehouse に静的データと任意の分析スキーマ。FileCreated、Activator、Pipeline が Eventhouse へ増分を取り込み、主 Data Agent は SQL、KQL、完全な Ontology の GQL を照会します。Notebook 05 は Lakehouse のテーブルと CSV を読み、Gold から Direct Lake と Power BI へつなぎます。構築制御と任意の Code Interpreter は別に示します。",
    },
    en: {
      skip: "Skip to explanation", appTitle: "Explore the architecture",
      localBadge: "Synthetic data · local explorer", expand: "Expand diagram", collapse: "Diagram + details",
      navOverview: "Overview", navStatic: "Facts & meaning", navEvents: "Observations", navAgent: "One Agent",
      navAnalytics: "Quality & BI", navControl: "Approved setup", navOutcomes: "Learning outcomes",
      focusOverview: "Overview · select a flow to explore", focusPrefix: "Focus",
      diagramHint: "Select a flow or diagram card. Keyboard: Tab / Enter / Space.",
      fullGuide: "Full explanation", sourceLink: "Implementation evidence", iconLink: "Icon source & terms", helpLink: "How to use",
      footerScope: "Current v2.7.0 · explanatory architecture · no service connection",
      shortcuts: "0–6: flows · J/E: language · Esc: overview", evidence: "Source anchors",
      diagramTitle: "Furusato Fabric Workshop overall architecture",
      diagramDesc: "One Lakehouse contains the static teaching data and optional analytics schemas. FileCreated, Activator and Pipeline ingest incremental CSVs into Eventhouse. One primary Data Agent queries SQL, KQL and the full teaching Ontology with GQL. Notebook 05 reads Lakehouse tables and CSV files directly and feeds Gold, Direct Lake and Power BI. Provisioning controls and optional Code Interpreter are shown separately.",
    }
  };

  const details = {
    ja: {
      overview: {
        kicker: "BUSINESS FIRST", title: "寄付の事実を、意味と根拠でつなぐ",
        lead: "誰が、どこへ寄付し、どの返礼品を選んだか。登録事業者と運用の状況まで、問いに合う根拠で読み解きます。",
        stat: "主 Agent 1 件 · 選択ソース 3 件",
        points: [
          "静的データは SQL、関係の意味は Ontology / GQL、運用観測は KQL で確認。",
          "単一のスキーマ対応 Lakehouse に、教材データと任意の分析レイヤーを整理。",
          "品質を確認した Gold は、Direct Lake の Power BI 分析へ。",
        ],
        note: "寄付・寄付者・事業者は合成データ。図は現行教材の構成を説明する、ローカルの対話型ページです。",
        evidence: "S1–S10",
      },
      static: {
        kicker: "01 / FACTS & MEANING", title: "行と列を、業務の関係へ",
        lead: "静的 CSV 8 本を Notebook 01 が検証し、11 個の ot_* を作成。SQL と完全な教材用 Ontology が同じ事実を使います。",
        stat: "10 Entity · 72 静的属性 · 時系列 1\n関係 15 · バインディング 11",
        points: [
          "Donation が寄付の単位。Donor の居住地と、受取 Municipality の地理を分けます。",
          "Supplier → Gift は登録の関係。ot_supplier_gift が多対多の橋渡しを担います。",
          "GQL で経路・方向・関係件数を確認。返礼品の選択と受領・配送は、それぞれ別の業務事実です。",
        ],
        note: "11 個の ot_* のうち、10 個が Entity の入力、1 個が登録関係の入力です。11 Binding は静的 10 件と時系列 1 件。",
        evidence: "S2 · S3 · S4 · S6",
      },
      events: {
        kicker: "02 / OPERATIONAL OBSERVATIONS", title: "到着を通知し、CSV を取り込む",
        lead: "OneLake FileCreated → Activator → Pipeline Copy。イベントが起動を伝え、Pipeline が CSV 本体を DonationEvents へ運びます。",
        stat: "15,000 raw 行 · 14,900 一意 EventID\n配布 3 ファイルの期待値",
        points: [
          "入力は各 5,000 行の CSV。100 行の再掲で、producer の再送を学びます。",
          "DonationObservationSummaryForAgent と 3 関数が、raw 件数・金額・UTC 期間・ファイル／実行を説明。",
          "Municipality の時系列は raw DonationEvents にバインド。静的 Donation と別の集団として扱います。",
        ],
        note: "初回は start_rule / Start で正式開始。完成CSVをPutBlobで1回作成し、イベント・activation・Job・Copy/KQLを照合して stop_rule / Stop。図は設計経路で、手動fallbackは別承認です。",
        evidence: "S2 · S4 · S5 · S10",
      },
      agent: {
        kicker: "03 / ONE AGENT, THREE SOURCES", title: "問いに合うエンジンと根拠",
        lead: "主 Data Agent は、SQL・KQL・ネイティブ GQL の役割を保ち、必要なソースを照会して回答します。",
        stat: "Source · Scope · Metric · Unit\n順位には RankScope",
        points: [
          "SQL：11 ot_* と agent_ref の view 1 件・TVF 2 件。静的属性・件数・金額の根拠。",
          "KQL：承認済み MV と 3 関数。GQL：完全な教材用 Ontology の経路と関係。",
          "Code Interpreter は同じ Agent の照会後ツール。取得した結果から計算・図・CSV／JSON を作成。",
        ],
        note: "Gold と Power BI は独立した分析経路です。統合 Agent のソース数は 3 件。各質問で必要な照会と、実際の実行結果を確認します。",
        evidence: "S1 · S6",
      },
      analytics: {
        kicker: "04 / OPTIONAL QUALITY & BI", title: "品質を説明できる分析へ",
        lead: "Notebook 05 は、同じ Lakehouse の stg_*、選択した ot_*、Files/increment/*.csv を直接読み取ります。",
        stat: "14,900 行を受入 · 100 行を隔離\n品質検査 → Ready → Direct Lake",
        points: [
          "bronze に元データ、silver に適合・重複排除後の行。quarantine と ops に理由・検査・実行を記録。",
          "Gold は StaticSeed と RealtimeIncrement を DataSource で区別し、整理した集団として公開。",
          "5 つの Gold テーブルから Direct Lake モデルへ。4 関係・6 メジャー・1 ページ／9 visual。",
        ],
        note: "この処理の入力は Lakehouse 側です。Eventhouse は並行する raw 観測経路。gold.donation_agent は任意の評価用成果物です。",
        evidence: "S7 · S8",
      },
      control: {
        kicker: "00 / PROVISIONING CONTROL PLANE", title: "構築は、確認と同意を経て",
        lead: "Notebook 04 が参加者の範囲で構築を計画。preview と plan hash を確認し、同意してから apply します。",
        stat: "Preview → PLAN_SHA256 → 同意\n参加者 Folder · {PID}",
        points: [
          "配置先・既存アイテム・競合を確認。データや照会の矢印と、構築制御を分けて読みます。",
          "環境ごとの ID・接続先・秘密情報は外部設定。dev / test / prod の配置先を明示。",
          "Notebook 02 / 03 は補助手順。Variable Library と UDF は任意で、外部アクションは個別に設定・承認。",
        ],
        note: "統合コースは ENABLE_UNIFIED_DATA_AGENT=True と ENABLE_AI_REFERENCE_ARCHITECTURE=False。現行の完全な教材モデルを選択します。",
        evidence: "S9",
      },
      outcomes: {
        kicker: "TAKE THE CONNECTIONS WITH YOU", title: "データ・意味・分析がつながる",
        lead: "ひとつの Workshop で、取り込みから品質、関係の設計、根拠のある回答までを説明できるようになります。",
        stat: "正しい範囲で読み、関係をたどり、\n確かな根拠で伝える。",
        points: [
          "業務の役割と、データの粒度をモデル化する。",
          "SQL・KQL・GQL を、問いに合わせて使い分ける。",
          "品質検査と公開ゲートを、分析の信頼につなぐ。",
          "指標・図・回答を、出典と対象範囲で説明する。",
        ],
        note: "この全体像を、実習で見たクエリ・Ontology・レポートへ結び付けて振り返ります。",
        evidence: "S1–S9",
      },
    },
    en: {
      overview: {
        kicker: "BUSINESS FIRST", title: "Connect facts, meaning and evidence",
        lead: "Who donated, where did it go, and which gift was selected? Follow registered suppliers and operational observations with the right evidence.",
        stat: "One primary Agent · three selected sources",
        points: [
          "SQL for static facts, Ontology / GQL for modeled relationships, KQL for operational observations.",
          "One schema-enabled Lakehouse organizes teaching data and optional analytics layers.",
          "Quality-checked Gold feeds the Direct Lake Power BI branch.",
        ],
        note: "Donations, donors and suppliers are synthetic. This local explorer explains the current workshop implementation.",
        evidence: "S1–S10",
      },
      static: {
        kicker: "01 / FACTS & MEANING", title: "Turn rows into business relationships",
        lead: "Notebook 01 validates eight static CSVs and produces eleven ot_* tables. SQL and the full teaching Ontology use those same facts.",
        stat: "10 entities · 72 static properties · 1 time series\n15 relationships · 11 bindings",
        points: [
          "Donation is the transaction grain. Donor residence and recipient Municipality geography have separate roles.",
          "Supplier → Gift means registration. The ot_supplier_gift bridge supplies the many-to-many edges.",
          "GQL verifies paths, direction and relationship counts. Gift selection, receipt and delivery are distinct business facts.",
        ],
        note: "Ten ot_* tables supply entities; the eleventh supplies the registration edges. Eleven bindings means ten static entity bindings plus one time-series binding.",
        evidence: "S2 · S3 · S4 · S6",
      },
      events: {
        kicker: "02 / OPERATIONAL OBSERVATIONS", title: "Signal arrival, then copy the CSV",
        lead: "OneLake FileCreated → Activator → Pipeline Copy. The event starts the job; Pipeline reads the CSV bytes into DonationEvents.",
        stat: "15,000 raw rows · 14,900 distinct EventIDs\nExpected for the three packaged files",
        points: [
          "Three 5,000-row CSVs include 100 repeated events to teach producer retransmission.",
          "DonationObservationSummaryForAgent and three functions explain raw counts, JPY amounts, UTC windows and file/run provenance.",
          "The Municipality time series binds raw DonationEvents. Static Donation remains a separate population.",
        ],
        note: "Formally start_rule / Start, create each complete CSV with one PutBlob, verify event, activation, Job and Copy/KQL, then stop_rule / Stop. This is a design view; manual fallback needs separate approval.",
        evidence: "S2 · S4 · S5 · S10",
      },
      agent: {
        kicker: "03 / ONE AGENT, THREE SOURCES", title: "Use the engine that owns the evidence",
        lead: "The primary Data Agent chooses the relevant SQL, KQL and native GQL sources while preserving their different roles.",
        stat: "Source · Scope · Metric · Unit\nAdd RankScope for rankings",
        points: [
          "SQL: eleven ot_* tables and agent_ref's one view plus two TVFs for static facts and exact lookups.",
          "KQL: the approved MV and three functions. GQL: the full teaching Ontology's paths and relationships.",
          "Code Interpreter is a post-query tool in the same Agent: calculate, chart and export actual returned data.",
        ],
        note: "Gold and Power BI form the separate analytics branch. The unified Agent selects three sources. Verify the queries and results actually used for each answer.",
        evidence: "S1 · S6",
      },
      analytics: {
        kicker: "04 / OPTIONAL QUALITY & BI", title: "Make analytical quality explainable",
        lead: "Notebook 05 reads stg_*, selected ot_* dimensions and Files/increment/*.csv directly from the same Lakehouse.",
        stat: "14,900 accepted · 100 quarantined\nQuality checks → Ready → Direct Lake",
        points: [
          "Bronze retains inputs; Silver conforms and deduplicates. Quarantine and ops retain rejection reasons, checks and run evidence.",
          "Gold preserves StaticSeed and RealtimeIncrement in DataSource and publishes the curated analytical population.",
          "Five Gold tables feed the model: four relationships, six measures, one report page and nine visuals.",
        ],
        note: "These are Lakehouse reads. Eventhouse is the parallel raw-observation path. gold.donation_agent is an optional evaluation artifact.",
        evidence: "S7 · S8",
      },
      control: {
        kicker: "00 / PROVISIONING CONTROL PLANE", title: "Review and approve the destination",
        lead: "Notebook 04 plans the participant-scoped items. Inspect the preview and exact plan hash, consent, then apply and verify.",
        stat: "Preview → PLAN_SHA256 → consent\nParticipant Folder · {PID}",
        points: [
          "Check destination, existing items and conflicts. Read provisioning control separately from data and queries.",
          "Keep environment IDs, endpoints and secrets external. Select dev / test / prod destinations explicitly.",
          "Notebook 02 / 03 are supporting alternatives. Variable Library and UDF are optional; external actions need separate configuration and approval.",
        ],
        note: "Unified course: ENABLE_UNIFIED_DATA_AGENT=True and ENABLE_AI_REFERENCE_ARCHITECTURE=False. Select the current full teaching model.",
        evidence: "S9",
      },
      outcomes: {
        kicker: "TAKE THE CONNECTIONS WITH YOU", title: "Connect data, meaning and analysis",
        lead: "One workshop makes ingestion, quality, relationship modeling and evidence-backed answers part of an explainable whole.",
        stat: "Read the right scope. Follow the relationships.\nCommunicate with evidence.",
        points: [
          "Model business roles and data grain.",
          "Choose SQL, KQL and GQL for the question.",
          "Turn quality checks and publication gates into trustworthy analytics.",
          "Explain metrics, charts and answers with source and scope.",
        ],
        note: "Use this map to connect the queries, Ontology and report you explored in the workshop.",
        evidence: "S1–S9",
      },
    }
  };

  const svgStyles = `
    text{font-family:"Segoe UI","Yu Gothic UI",Meiryo,sans-serif;fill:#203348}
    .muted{fill:#506275}.teal{fill:#086f68}.purple{fill:#634892}.amber{fill:#8d5716}
    .bold{font-weight:650}.mono{font-family:Consolas,"Yu Gothic UI",Meiryo,monospace}
    .edge{fill:none;stroke-width:3.5;stroke-linejoin:round;stroke-linecap:round}
    .edge.data{stroke:#16817a}.edge.control{stroke:#a66819;stroke-dasharray:11 8}
    .edge.binding{stroke:#3c719d;stroke-dasharray:3 8}
    .edge.query{stroke:#7754a4;stroke-dasharray:10 7}
    .node-bg{fill:#fff;stroke:#d8e2e8;stroke-width:2}
    .optional{stroke-dasharray:9 6}
    [data-focus]{cursor:pointer}
    [data-focus]:focus{outline:none}
    [data-focus]:focus-visible .node-bg{stroke:#a44819;stroke-width:5}
    [data-focus]:focus-visible .selection-band{stroke:#a44819;stroke-width:5}
    [data-focus]:hover .node-bg{stroke:#7ca7a4;stroke-width:3}
    .is-selected .node-bg{stroke:#086f68;stroke-width:5}
    .is-selected .edge{stroke-width:6}
    .is-selected .selection-band{stroke:#086f68;stroke-width:4}
    .selection-band{fill:transparent;stroke:transparent;stroke-width:4;pointer-events:all}
  `;

  function buildDiagram(lang = "ja", interactive = true) {
    const ja = lang === "ja";
    const choose = (j, e) => ja ? j : e;
    const parts = [];
    const txt = (x, y, content, size = 28, css = "", extra = "") => {
      parts.push(`<text x="${x}" y="${y}" font-size="${size}" class="${css}" ${extra}>${esc(content)}</text>`);
    };
    const rect = (x, y, w, h, fill, stroke = "none", radius = 16, css = "") => {
      parts.push(`<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="${radius}" fill="${fill}" stroke="${stroke}" class="${css}"/>`);
    };
    const image = (file, x, y, size) => {
      parts.push(`<image href="${ICONS}${file}" x="${x}" y="${y}" width="${size}" height="${size}" preserveAspectRatio="xMidYMid meet" aria-hidden="true"/>`);
    };
    const start = (focus, label, activeFlows = focus) => {
      parts.push(`<g data-focus="${focus}" data-flows="${activeFlows}"${interactive ? ` tabindex="0" role="button" aria-pressed="false" aria-label="${esc(label)}"` : ""}>`);
      parts.push(`<title>${esc(label)}</title>`);
    };
    const end = () => parts.push("</g>");
    const card = (x, y, w, h, optional = false) => rect(x, y, w, h, "#ffffff", "#d8e2e8", 16, `node-bg${optional ? " optional" : ""}`);
    const edge = (d, type, flows) => {
      parts.push(`<g data-flows="${flows}"><path d="${d}" class="edge ${type}" marker-end="url(#arrow-${type})"${type === "query" ? ' marker-start="url(#arrow-query)"' : ""}/></g>`);
    };
    const label = (x, y, content, size = 24, color = "#506275", width = null) => {
      const w = width || Math.max(40, content.length * size * (ja ? .77 : .53) + 16);
      rect(x - 8, y - size + 1, w, size + 10, "#fbfcfd", "none", 6);
      txt(x, y, content, size, "", `style="fill:${color}"`);
    };
    const section = (x, y, number, text) => {
      rect(x, y - 29, 47, 39, "#edf5f5", "none", 11);
      txt(x + 9, y, number, 24, "teal bold");
      txt(x + 61, y, text, 30, "bold");
    };

    parts.push(`<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 2560 1440" width="2560" height="1440" role="${interactive ? "group" : "img"}" aria-labelledby="architecture-title architecture-desc" xml:lang="${lang}">`);
    parts.push(`<title id="architecture-title">${esc(ui[lang].diagramTitle)}</title><desc id="architecture-desc">${esc(ui[lang].diagramDesc)}</desc>`);
    parts.push(`<defs><style>${svgStyles}</style>`);
    for (const [name, color] of Object.entries({data: "#16817a", control: "#a66819", binding: "#3c719d", query: "#7754a4"})) {
      parts.push(`<marker id="arrow-${name}" markerWidth="15" markerHeight="15" refX="12" refY="7" orient="auto-start-reverse" markerUnits="userSpaceOnUse"><path d="M1 1 L13 7 L1 13" fill="none" stroke="${color}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/></marker>`);
    }
    parts.push("</defs>");
    rect(0, 0, 2560, 1440, "#f7f9fb", "none", 0);
    image("microsoft-fabric.svg", 64, 40, 56);
    txt(140, 64, "FURUSATO / FABRIC WORKSHOP", 26, "teal bold", 'letter-spacing="2"');
    txt(140, 97, "CURRENT ARCHITECTURE", 21, "muted", 'letter-spacing="2"');
    txt(64, 151, choose("寄付データから、根拠のある回答へ", "From donation data to evidence-backed answers"), 48, "bold");
    txt(66, 192, choose("事実・業務のつながり・運用の観測を、目的に合うエンジンで読み解く。", "Static facts, business relationships and operational observations—each with the right engine."), 28, "muted");
    rect(1982, 42, 504, 46, "#e8f3eb", "none", 23);
    txt(2006, 74, choose("合成データ · 主 Agent 1 件 / 3 ソース", "Synthetic data · 1 Agent / 3 sources"), 26, "bold", 'style="fill:#366342"');
    txt(2484, 130, "v2.7.0 / unified-20260923", 24, "muted", 'text-anchor="end"');
    txt(2484, 169, choose("制御手順を更新 · 2026-09-23", "Lifecycle updated · 2026-09-23"), 24, "muted", 'text-anchor="end"');

    // Provisioning has its own visual lane and uses control, not data, arrows.
    start("control", ui[lang].navControl);
    rect(48, 222, 2464, 106, "#fff7eb", "#e8d5b6", 18, "node-bg");
    rect(48, 222, 2464, 106, "#fff7eb", "none", 18);
    txt(76, 279, "00", 29, "amber bold");
    image("fabric-notebook.svg", 135, 247, 48);
    txt(200, 269, "Notebook 04", 32, "bold");
    txt(200, 306, choose("構築・制御プレーン", "Provisioning control plane"), 24, "amber");
    txt(574, 282, "Preview", 32, "bold");
    txt(866, 267, "PLAN_SHA256", 32, "bold mono");
    txt(866, 303, choose("内容の確認 + 明示的な同意", "Review + explicit consent"), 25, "amber");
    txt(1390, 267, choose("参加者 Folder · {PID}", "Participant Folder · {PID}"), 31, "bold");
    txt(1390, 303, choose("承認したアイテムを構築・検証", "Create and verify approved items"), 25, "amber");
    image("fabric-item-variable-library.svg", 1974, 241, 38);
    txt(2024, 272, "Variable Library", 26, "bold");
    image("fabric-item-user-data-function.svg", 2310, 241, 38);
    txt(2358, 272, "UDF", 27, "bold");
    txt(1974, 309, choose("任意の補助成果物 · 外部アクションは別承認", "Optional · external actions need approval"), 22, "amber");
    end();
    edge("M470 278 H538", "control", "control");
    edge("M767 278 H832", "control", "control");
    edge("M1286 278 H1354", "control", "control");

    rect(48, 354, 2464, 838, "#ffffff", "#dce5ec", 22);
    rect(628, 354, 582, 823, "#edf7f5", "#b3d2cb", 22);
    image("fabric-lakehouse.svg", 654, 374, 47);
    txt(718, 407, "Lakehouse", 36, "bold");
    txt(654, 442, choose("単一のスキーマ対応 Lakehouse · {PID}", "One schema-enabled Lakehouse · {PID}"), 24, "teal");
    section(80, 428, "01", choose("静的データ", "Static facts"));
    section(80, 674, "02", choose("運用の観測", "Observations"));
    section(2004, 428, "03", choose("回答と根拠", "Answers & evidence"));

    // Edges are under cards. Read and write arrows for Notebook 05 share the
    // Lakehouse data surface but do not connect to Eventhouse.
    edge("M298 539 H354", "data", "static");
    edge("M582 539 H654", "data", "static");
    edge("M1184 574 H1326", "binding", "static");
    edge("M1184 495 H1250 V383 H1964 V490 H2004", "query", "agent");
    edge("M1872 550 H2004", "query", "agent");
    edge("M298 779 H654", "data", "events");
    edge("M1150 713 V687 H1444 V714", "control", "events");
    edge("M1562 758 H1640", "control", "events");
    edge("M1184 807 H1242 V854 H1622 V792 H1640", "data", "events");
    edge("M1756 830 V880", "data", "events");
    edge("M1872 920 H1912 V620 H1872", "binding", "static events");
    edge("M1872 974 H1970 V900 H2004", "query", "agent");
    edge("M654 966 H610 V1070 H582", "data", "analytics");
    edge("M582 1139 H654", "data", "analytics");
    edge("M1184 1115 H1326", "data", "analytics");
    edge("M1578 1115 H1640", "data", "analytics");
    edge("M2232 957 V1031", "data", "agent");

    start("static", choose("静的 CSV 8 本", "Eight static CSV files"));
    card(80, 478, 218, 130);
    txt(100, 518, choose("静的 CSV", "Static CSVs"), 31, "bold");
    txt(100, 565, choose("8 本 · 2025", "8 files · 2025"), 29, "muted");
    txt(100, 596, choose("教材 snapshot", "Teaching snapshot"), 22, "muted");
    end();
    start("static", "Notebook 01");
    card(354, 478, 228, 130);
    image("fabric-notebook.svg", 372, 499, 37);
    txt(422, 522, "Notebook", 29, "bold");
    txt(422, 557, "01", 32, "teal bold");
    txt(377, 592, "PySpark", 25, "muted");
    end();
    start("static", choose("Lakehouse の静的 SQL ソース", "Lakehouse static SQL source"), "static agent");
    card(654, 466, 530, 155);
    txt(680, 505, "dbo · 11 ot_*", 32, "bold");
    txt(680, 547, "SQL endpoint + agent_ref", 29, "purple");
    txt(680, 591, choose("Notebook 01: stg_* と ot_*", "Notebook 01: stg_* and ot_*"), 26, "muted");
    end();
    start("static", choose("完全な教材用 Ontology", "Full teaching Ontology"), "static agent");
    card(1326, 466, 546, 188);
    image("fabric-item-ontology.svg", 1350, 486, 54);
    txt(1422, 513, "Ontology", 37, "bold");
    txt(1422, 549, choose("完全な教材モデル", "Full teaching model"), 26, "teal");
    txt(1352, 596, choose("10 Entity · 72 静的属性", "10 entities · 72 static properties"), 28, "bold");
    txt(1352, 636, choose("時系列 1 · 関係 15 · バインド 11", "1 time series · 15 edges · 11 bindings"), 25, "muted");
    end();

    start("events", choose("3 本の増分 CSV", "Three incremental CSV files"));
    card(80, 714, 218, 126);
    txt(100, 754, choose("増分 CSV", "Increment CSV"), 26, "bold");
    txt(100, 797, choose("3 本 × 5,000 行", "3 × 5,000 rows"), 27, "muted");
    txt(100, 827, "2026-08 · UTC", 22, "muted");
    end();
    start("events", choose("同じ Lakehouse の OneLake ファイル", "OneLake files in the same Lakehouse"));
    card(654, 714, 530, 126);
    image("onelake.svg", 681, 735, 46);
    txt(746, 766, "Files/increment", 32, "bold");
    txt(682, 815, choose("同じ Lakehouse の OneLake ファイル", "OneLake files in the same Lakehouse"), 26, "muted");
    end();
    start("events", "Activator / Reflex");
    card(1326, 714, 236, 116);
    txt(1348, 757, "Activator", 34, "bold");
    txt(1348, 804, choose("正式開始後に通知", "Start → file signal"), 26, "muted");
    end();
    start("events", "Data Pipeline / Copy");
    card(1640, 714, 232, 116);
    image("fabric-data-pipeline.svg", 1661, 734, 34);
    txt(1706, 762, "Pipeline", 31, "bold");
    txt(1661, 803, choose("Copy 処理", "Copy activity"), 27, "muted");
    end();
    start("events", "Eventhouse / DonationEvents", "events agent");
    card(1326, 880, 546, 132);
    image("fabric-eventhouse.svg", 1347, 891, 47);
    txt(1408, 920, "Eventhouse", 33, "bold");
    image("fabric-kql-database.svg", 1708, 890, 30);
    txt(1745, 914, "KQL DB", 23, "muted");
    txt(1350, 962, "DonationEvents → agent MV", 28, "bold");
    txt(1350, 997, choose("raw 観測 + KQL 参照関数 3 本", "Raw observations + 3 KQL functions"), 26, "muted");
    end();

    // Optional analytics uses a separate, clearly bounded output path.
    txt(682, 883, choose("NOTEBOOK 05 の入力", "NOTEBOOK 05 INPUTS"), 22, "teal bold", 'letter-spacing="1"');
    txt(682, 920, choose("stg_* + 対応する ot_* + CSV", "stg_* + selected ot_* + CSV"), 27, "bold");
    txt(682, 955, choose("この Lakehouse から直接読み取り", "Read directly from this Lakehouse"), 25, "muted");
    start("analytics", choose("Notebook 05 の品質・分析拡張", "Notebook 05 quality and analytics"));
    card(354, 1048, 228, 120, true);
    image("fabric-notebook.svg", 372, 1069, 37);
    txt(422, 1094, "Notebook", 29, "bold");
    txt(422, 1128, "05", 32, "teal bold");
    txt(377, 1157, choose("品質検査", "Quality checks"), 23, "muted");
    end();
    txt(80, 1048, "04", 29, "teal bold");
    txt(80, 1090, choose("品質と BI", "Quality & BI"), 31, "bold");
    rect(80, 1110, 148, 38, "#fff5e4", "none", 19);
    txt(102, 1137, choose("任意の拡張", "Optional"), 24, "amber");
    start("analytics", choose("同じ Lakehouse の medallion schemas", "Medallion schemas in the same Lakehouse"));
    card(654, 989, 530, 179, true);
    txt(678, 1030, "bronze → silver → gold", 31, "bold");
    txt(678, 1071, choose("ops + quarantine · Ready 後に利用", "ops + quarantine · Ready gate"), 25, "muted");
    txt(678, 1111, choose("14,900 行受入 / 100 行隔離", "14,900 accepted / 100 quarantined"), 26, "teal bold");
    txt(678, 1151, choose("静的 seed + 受入済み増分", "Static seed + accepted increments"), 25, "muted");
    end();
    start("analytics", "Direct Lake / Semantic model");
    card(1326, 1060, 252, 108, true);
    image("fabric-semantic-model.svg", 1346, 1079, 36);
    txt(1395, 1095, choose("Semantic", "Semantic"), 29, "bold");
    txt(1395, 1126, "model", 29, "bold");
    txt(1346, 1158, choose("Direct Lake · 5 表", "Direct Lake · 5 tables"), 23, "muted");
    end();
    start("analytics", "Power BI / Report");
    card(1640, 1060, 232, 108, true);
    image("fabric-power-bi-report.svg", 1660, 1080, 36);
    txt(1711, 1105, "Power BI", 30, "bold");
    txt(1660, 1150, choose("レポート", "Report"), 28, "muted");
    end();

    start("agent", choose("主 Data Agent 1 件、3 ソース", "One primary Data Agent, three sources"));
    card(2004, 466, 456, 491);
    rect(2005, 467, 454, 490, "#f7f3fc", "none", 15);
    image("fabric-data-agent.svg", 2036, 494, 62);
    txt(2120, 539, "Data Agent", 38, "bold");
    txt(2036, 588, "DA_Furusato_{PID}", 27, "purple mono");
    ["SQL", "KQL", "GQL"].forEach((name, index) => {
      rect(2036 + index * 130, 618, 116, 52, "#ffffff", "#d9cde9", 12);
      txt(2094 + index * 130, 654, name, 30, "purple bold", 'text-anchor="middle"');
    });
    txt(2036, 717, choose("根拠をそろえて回答", "Evidence-backed answers"), 30, "bold");
    txt(2036, 765, "Source · Scope", 29, "purple");
    txt(2036, 807, "Metric · Unit · RankScope", 27, "purple");
    txt(2036, 861, choose("質問に合うソースを照会", "Query the relevant sources"), 27, "muted");
    txt(2036, 918, choose("主 Agent 1 件 · 選択ソース 3 件", "1 primary · 3 selected sources"), 26, "bold");
    end();
    start("agent", choose("照会後の任意ツール Code Interpreter", "Code Interpreter, optional post-query tool"));
    card(2004, 1031, 456, 137, true);
    txt(2036, 1074, "Code Interpreter", 33, "bold");
    txt(2036, 1114, choose("照会後の任意ツール", "Optional · after source queries"), 25, "muted");
    txt(2036, 1152, "Charts · CSV / JSON / PNG", 26, "purple");
    end();

    label(1645, 373, choose("SQL · 静的な事実", "SQL · static facts"), 25, "#634892", 267);
    label(1223, 561, choose("静的", "Static"), 23, "#3c719d", 87);
    label(1890, 539, "GQL", 26, "#634892", 76);
    label(364, 759, choose("OneLake へ配置", "Upload to OneLake"), 26, "#086f68", 250);
    label(1218, 677, "FileCreated", 24, "#8d5716", 154);
    label(1375, 862, choose("CSV 本体", "CSV bytes"), 23, "#086f68", 148);
    label(1887, 752, choose("時系列", "1 TS"), 26, "#3c719d", 96);
    label(1887, 784, choose("bind 1", "binding"), 22, "#3c719d", 102);
    label(1902, 1004, "KQL", 26, "#634892", 72);
    label(1228, 1098, "Delta", 23, "#086f68", 76);
    label(2264, 1002, choose("取得した結果", "Returned results"), 23, "#086f68", 190);

    // Line styles and text labels provide redundant, color-independent meaning.
    txt(80, 1238, choose("凡例", "LEGEND"), 23, "muted bold");
    edge("M240 1229 H328", "data", "");
    txt(347, 1238, choose("データ", "Data"), 26, "muted");
    edge("M610 1229 H698", "control", "");
    txt(717, 1238, choose("イベント / 制御", "Event / control"), 26, "muted");
    edge("M1110 1229 H1198", "binding", "");
    txt(1217, 1238, choose("バインディング", "Binding"), 26, "muted");
    edge("M1570 1229 H1658", "query", "");
    txt(1677, 1238, choose("照会 / 結果", "Query / result"), 26, "muted");
    rect(2128, 1210, 60, 37, "#ffffff", "#8797a6", 8, "optional");
    txt(2207, 1238, choose("任意の機能", "Optional"), 26, "muted");
    rect(64, 1271, 2432, 2, "#dce6ed", "none", 0);
    start("outcomes", ui[lang].navOutcomes);
    rect(58, 1282, 2444, 142, "none", "none", 16, "selection-band");
    txt(80, 1323, choose("データ・意味・分析をつなぎ、根拠をもって伝える。", "Connect data, meaning and analysis. Communicate with evidence."), 35, "teal bold");
    txt(80, 1370, choose("設計上の取り込み経路 · 正式開始 → 実配送を確認 → 正式停止 · Gold / BI は任意の別経路", "Design route · formal start → verify actual delivery → formal stop · Gold / BI is a separate optional branch"), 25, "muted");
    txt(80, 1410, choose("Microsoft の元アイコンを使用 · 出典: AzureDiagarm · 原画・色・縦横比を保持", "Original Microsoft icons · source: AzureDiagarm · artwork, colors and proportions preserved"), 21, "muted");
    end();
    parts.push("</svg>");
    return parts.join("\n");
  }

  let lang = new URLSearchParams(location.search).get("lang") === "en" ? "en" : "ja";
  let focus = new URLSearchParams(location.search).get("focus") || "overview";
  if (!FLOWS.includes(focus)) focus = "overview";
  let expanded = false;

  function updateLocation() {
    try {
      const url = new URL(location.href);
      url.searchParams.set("lang", lang);
      url.searchParams.set("focus", focus);
      history.replaceState(null, "", url);
    } catch (_) {
      // Some file:// policies disallow replacing history; interaction still works.
    }
  }

  function renderDetails() {
    const content = details[lang][focus];
    document.getElementById("details-content").innerHTML =
      `<p class="detail-kicker">${esc(content.kicker)}</p>
       <h2 id="detail-title">${esc(content.title)}</h2>
       <p class="detail-lead">${esc(content.lead)}</p>
       <p class="detail-stat">${esc(content.stat).replace(/\n/g, "<br>")}</p>
       <ul class="detail-points${focus === "outcomes" ? " outcome-list" : ""}">${content.points.map(point => `<li>${esc(point)}</li>`).join("")}</ul>
       <p class="detail-note">${esc(content.note)}</p>
       <p class="detail-evidence">${esc(ui[lang].evidence)}: ${esc(content.evidence)}</p>`;
    document.getElementById("focus-label").textContent = focus === "overview"
      ? ui[lang].focusOverview
      : `${ui[lang].focusPrefix}: ${content.kicker}`;
    document.getElementById("guide-link").href = `overview.${lang}.md`;
    document.getElementById("svg-link").href = `../assets/architecture/furusato-architecture.${lang}.svg`;
    document.getElementById("png-link").href = `../assets/architecture/furusato-architecture.${lang}.png`;
  }

  function highlight() {
    document.querySelectorAll("[data-flow]").forEach(button => {
      button.setAttribute("aria-pressed", String(button.dataset.flow === focus));
    });
    document.querySelectorAll("#diagram [data-flows]").forEach(group => {
      const selected = focus !== "overview" && group.dataset.flows.split(" ").includes(focus);
      group.classList.toggle("is-selected", selected);
      if (group.hasAttribute("role")) group.setAttribute("aria-pressed", String(group.dataset.focus === focus));
    });
    // Icons are never dimmed, filtered, recolored or stretched during focus.
  }

  function setFocus(next) {
    if (!FLOWS.includes(next)) return;
    focus = next;
    renderDetails();
    highlight();
    updateLocation();
  }

  function setLanguage(next) {
    lang = next === "en" ? "en" : "ja";
    document.documentElement.lang = lang;
    document.title = `Furusato Fabric Workshop · ${lang === "ja" ? "アーキテクチャ" : "Architecture"}`;
    document.querySelectorAll("[data-i18n]").forEach(element => {
      element.textContent = ui[lang][element.dataset.i18n];
    });
    document.getElementById("lang-ja").setAttribute("aria-pressed", String(lang === "ja"));
    document.getElementById("lang-en").setAttribute("aria-pressed", String(lang === "en"));
    document.getElementById("expand").textContent = ui[lang][expanded ? "collapse" : "expand"];
    document.getElementById("diagram").innerHTML = buildDiagram(lang);
    renderDetails();
    highlight();
    updateLocation();
  }

  document.getElementById("lang-ja").addEventListener("click", () => setLanguage("ja"));
  document.getElementById("lang-en").addEventListener("click", () => setLanguage("en"));
  document.getElementById("flow-nav").addEventListener("click", event => {
    const button = event.target.closest("[data-flow]");
    if (button) setFocus(button.dataset.flow);
  });
  document.getElementById("diagram").addEventListener("click", event => {
    const group = event.target.closest("[data-focus]");
    if (group) setFocus(group.dataset.focus);
  });
  document.getElementById("diagram").addEventListener("keydown", event => {
    const group = event.target.closest("[data-focus]");
    if (group && ["Enter", " "].includes(event.key)) {
      event.preventDefault();
      setFocus(group.dataset.focus);
    }
  });
  document.getElementById("expand").addEventListener("click", () => {
    expanded = !expanded;
    document.body.classList.toggle("expanded", expanded);
    document.getElementById("expand").setAttribute("aria-pressed", String(expanded));
    document.getElementById("expand").textContent = ui[lang][expanded ? "collapse" : "expand"];
  });
  document.addEventListener("keydown", event => {
    if (event.ctrlKey || event.altKey || event.metaKey || event.repeat) return;
    if (event.target.closest("button,a,input,textarea,select,[contenteditable=true],[role=button]")) return;
    const key = event.key.toLowerCase();
    const index = Number(key);
    if (/^[0-6]$/.test(key)) {
      event.preventDefault();
      setFocus(FLOWS[index]);
    } else if (key === "j" || key === "e") {
      setLanguage(key === "j" ? "ja" : "en");
    } else if (key === "escape") {
      setFocus("overview");
    }
  });

  // Read-only export surface for reproducible local SVG/PNG generation.
  window.FurusatoArchitecture = Object.freeze({
    exportSVG: requestedLanguage => buildDiagram(requestedLanguage === "en" ? "en" : "ja", false),
    getState: () => Object.freeze({ lang, focus, expanded }),
    flowIds: Object.freeze([...FLOWS]),
  });
  setLanguage(lang);
})();
