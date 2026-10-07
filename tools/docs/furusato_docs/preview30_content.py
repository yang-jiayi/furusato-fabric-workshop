"""The single bilingual source for the v3.0 Preview Word and HTML course.

The entire v2.7 text/table/code curriculum is retained as explicitly labelled
comparison material. New-experience procedures and evidence are separate.
"""

from __future__ import annotations

import copy
import ast
import hashlib
import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from furusato_html import capture as capture_module
from furusato_html.capture import capture_participant_guide, CaptureBuilder
from furusato_html.mirror import load_mirror
from furusato_html.model import Block, Document, Section, Text, build_document

from . import preview30_evidence
from . import preview30_evaluation
from . import preview30_evaluation100 as study100
from . import preview30_public_evidence
from . import preview30_reporting
from . import preview30_release as release
from .context import load_context
from .facts import compute_facts
from .oox import StyleCarrier
from .tests10 import build_tests

VERSION = release.PREVIEW.version
PREVIEW_NOTICE_JA = "実装・検証結果を収録したPreview — AI回答品質は未合格／GAではありません"
PREVIEW_NOTICE_EN = "Preview with implementation and verification results — AI answer quality not accepted; not GA"
WORD_NAME = release.PREVIEW.word_name
HTML_NAME = release.PREVIEW.html_name
OFFICIAL_BASE = "https://learn.microsoft.com/en-us/fabric/iq/ontology/"
DEFINITION_DOC = "https://learn.microsoft.com/en-us/rest/api/fabric/articles/item-management/definitions/ontology-definition"
CREATE_DOC = "https://learn.microsoft.com/en-us/rest/api/fabric/ontology/items/create-ontology"
CHAPTERS = [
    ("シナリオ・学習目標・完成アーキテクチャ", "Scenario, learning goals and target architecture"),
    ("DBA・BIエンジニアのためのOntology設計", "Ontology design for DBA and BI engineers"),
    ("Furusato業務モデルの設計根拠", "Rationale for the Furusato business model"),
    ("前提条件・配置範囲・安全な実行", "Prerequisites, deployment scope and safe execution"),
    ("LakehouseとNotebook 01", "Lakehouse and Notebook 01"),
    ("新UIでのOntology・Entity・Property作成", "Ontology, entity and property authoring in the new UI"),
    ("Relationshipと静的モデルの検証", "Relationships and static-model validation"),
    ("EventhouseとKQLスキーマ", "Eventhouse and the KQL schema"),
    ("PipelineとOneLakeイベント連携", "Pipeline and OneLake event integration"),
    ("増分取り込みと時系列バインディング", "Increment ingestion and time-series bindings"),
    ("Notebook 05による品質処理とGold", "Quality processing and Gold with Notebook 05"),
    ("Semantic ModelとOntology Metrics", "Semantic model and ontology Metrics"),
    ("Metadata・Business Rules・Notebook 02", "Metadata, Business Rules and Notebook 02"),
    ("Namespaces・継承・共有プロパティ", "Namespaces, inheritance and shared properties"),
    ("Ontology Copilot（組み込みOntology Agent）による設計・改善・照会", "Design, improve and query with Ontology Copilot (built-in Ontology Agent)"),
    ("選択的Graph実体化とGQL", "Selective graph materialization and GQL"),
    ("Fabric Data AgentとCode Interpreter", "Fabric Data Agent and Code Interpreter"),
    ("業務シナリオによる横断演習", "Cross-source business scenario exercises"),
    ("AI回答品質の評価と改善", "Evaluate and improve AI answer quality"),
    ("MCPと可視化による外部利用", "External consumption through MCP and visualization"),
    ("Version historyによる変更管理", "Change management with Version history"),
    ("RDF／OWLのImport・Export", "RDF/OWL import and export"),
    ("Publish・共有・ガバナンス", "Publish, sharing and governance"),
    ("自動配置・旧版移行・運用・クリーンアップ", "Automated deployment, migration, operations and cleanup"),
]
APPENDICES = [
    ("データ・モデル・期待値リファレンス", "Data, model and expected-value reference"),
    ("Notebook・設定・配置パラメーター索引", "Notebook, configuration and deployment parameter index"),
    ("評価問題・採点基準・記録様式", "Evaluation questions, scoring and recording forms"),
    ("Optional拡張", "Optional extensions"),
    ("移行対応表・トラブルシューティング・公式資料", "Migration map, troubleshooting and official references"),
]

LEGACY_MAP = {
    1: [1], 2: [2, 3], 3: [4], 4: [5], 5: [6], 6: [7, 8], 7: [9, 10],
    8: [11], 9: [12], 10: [13, 14], 13: [15], 17: [16], 19: [17], 23: [18, "C"], 24: [19],
    "A": ["A"], "B": ["B"], "D": ["D"], "E": ["E"],
}

class LayoutCapture(CaptureBuilder):
    """Keep the current Word renderer's pagination hints without altering v2.7."""

    def heading(self, *args, **kwargs):
        node = super().heading(*args, **kwargs)
        node.payload["word_layout"] = {k: v for k, v in kwargs.items() if k in {"new_page", "pull_up"}}
        return node

    def table(self, *args, **kwargs):
        node = super().table(*args, **kwargs)
        names = {
            "font_size", "header_size", "keep_together", "keep_tail_rows",
            "pull_up", "min_row_height_cm", "free_text_rows", "whole_token_columns",
        }
        node.payload["word_layout"] = {
            k: sorted(v) if isinstance(v, set) else v for k, v in kwargs.items() if k in names
        }
        return node

    def callout(self, *args, **kwargs):
        node = super().callout(*args, **kwargs)
        node.payload["word_layout"] = {k: v for k, v in kwargs.items() if k in {"keep_with_next", "pull_up"}}
        return node

    def figure(self, *args, **kwargs):
        node = super().figure(*args, **kwargs)
        node.payload["word_layout"] = {k: v for k, v in kwargs.items() if k in {"width_ratio", "max_height_cm"}}
        return node


def capture_with_word_layout(context, facts, tests, carrier):
    original = capture_module.CaptureBuilder
    capture_module.CaptureBuilder = LayoutCapture
    try:
        return capture_participant_guide(context, facts, tests, carrier, public_documents_only=True)
    finally:
        capture_module.CaptureBuilder = original


def t(ja: str, en: str | None = None) -> Text:
    return Text(ja, ja if en is None else en)


def p(ja: str, en: str) -> Block:
    return Block("paragraph", {"text": t(ja, en), "lead": False})


def note(ja: str, en: str, tone: str = "note") -> Block:
    return Block("callout", {"tone": tone, "text": t(ja, en), "title": None})


def code(value: str, language: str) -> Block:
    return Block("code", {"text": value, "language": t(language)})


def literal_notebook_parameters(notebook, name):
    cells = [cell for cell in notebook["cells"] if "parameters" in cell.get("metadata", {}).get("tags", [])]
    if len(cells) != 1:
        raise ValueError("Expected one tagged v3 parameter cell: " + name)
    parameters = {}
    for node in ast.parse("".join(cells[0]["source"])).body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    if target.id in parameters:
                        raise ValueError("Duplicate Notebook parameter: " + target.id)
                    parameters[target.id] = ast.literal_eval(node.value)
    return parameters


def prompt(ja: str, en: str) -> Block:
    return Block("prompt", {"text": t(ja, en)})


def table(headers, rows, caption: tuple[str, str]) -> Block:
    return Block("table", {
        "number": 0, "headers": [t(*h) if isinstance(h, tuple) else t(h) for h in headers],
        "rows": [[t(*c) if isinstance(c, tuple) else t(str(c)) for c in row] for row in rows],
        "caption": t(*caption), "wide": len(headers) >= 5,
    })


def sub(parent: Section, suffix: str, title: tuple[str, str], blocks: list[Block]) -> Section:
    number = f"{parent.number}.{suffix}"
    result = Section(
        ident=f"{parent.ident}-{suffix}", level=2, number=number,
        title=t(f"{number} {title[0]}", f"{number} {title[1]}"), blocks=blocks,
        chapter=parent.chapter, appendix=parent.appendix,
    )
    parent.children.append(result)
    return result


def lesson(parent, aim, prepare, steps, success, correction, docs=()):
    sub(parent, "1", ("目的・前提", "Purpose and prerequisites"), [p(*aim), note(*prepare)])
    sub(parent, "2", ("現行Previewの操作手順", "Current-preview procedure"), [
        Block("list", {"numbered": True, "items": [t(*step) for step in steps]})
    ])
    sub(parent, "3", ("成果・停止条件・修正確認", "Outcomes, stop conditions and corrective checks"), [
        table(
            [("判定", "Decision"), ("実際に確かめること", "What to verify")],
            [[("成果", "Outcome"), success], [("停止・修正", "Stop and correct"), correction]],
            ("この演習の完了条件", "Completion criteria for this exercise"),
        ),
        p("文書の手順提供と実環境での合格は別です。次節の実施状態を必ず確認します。",
          "Provided instructions and a passed live lab are different. Always inspect the observed status in the following section."),
    ])
    if docs:
        sub(parent, "8", ("公式資料・確認日", "Official references and review date"), [
            p("Microsoft Learnの2026-09-29更新を確認。資料の記載とこの環境の実施記録は区別します。",
              "Reviewed the 2026-09-29 Microsoft Learn update. Documentation is not evidence that this environment executed the lab."),
            Block("list", {"numbered": False, "items": [t(OFFICIAL_BASE + slug) for slug in docs]}),
        ])


def current_lessons(roots, context):
    r = {section.chapter: section for section in roots}
    lesson(r[1],
        ("業務の意味、保管、実行エンジン、AIの説明を分けて設計します。24章と5付録で手動構築、更新、独立評価まで進みます。",
         "Separate business meaning, storage, execution engines and AI explanations. The 24 chapters and five appendices cover manual construction, change and independent evaluation."),
        ("すべて合成データです。自治体名・コードのみ実在の参照ラベルです。v2.7は比較用に残し、新UIでの成功の根拠にしません。",
         "All transactional/person/business data is synthetic. Only municipality labels/codes are real references. Retain v2.7 for comparison, never as proof of new-UI success."),
        [
            ("Lakehouseの静的CSV→Notebook 01→ot_*、OneLakeイベント→Pipeline→Eventhouse、Notebook 05→Gold→Semantic modelを別経路として図にします。",
             "Draw separate paths: static CSV → Notebook 01 → ot_* in Lakehouse; OneLake event → Pipeline → Eventhouse; Notebook 05 → Gold → semantic model."),
            ("OntologyにEntity/Property/Relationship、バインディング、Metrics、自然言語Rulesを置きます。Ontology自体を汎用データストアや全件クエリエンジンとしません。",
             "Place entities/properties/relationships, bindings, Metrics and natural-language Rules in ontology. It is not a general data store or a universal query engine."),
            ("通常の件数・集計はSQL/KQL/DAXへ、関係経路が必要な場合だけ選択的にGraphを実体化してGQLへ進みます。",
             "Use SQL/KQL/DAX for ordinary counts and aggregates. Materialize a selected graph and use GQL only when the relationship path matters."),
            ("主Fabric Data Agentは1件だけです。Ontology内のOntology agentは組み込みの別体験であり、CIは主Agentのツールです。",
             "Keep one main Fabric Data Agent. The ontology's built-in Ontology agent is a distinct experience; CI is a tool of the main Data Agent."),
        ],
        ("各問いについて意味、データレイヤー、粒度、時点、エンジン、必要な証拠を説明できること。",
         "Explain meaning, data layer, grain, time, engine and required evidence for each question."),
        ("Graphの自動全件実体化や新Rulesの直接Activator連携を図に描いた場合は修正します。",
         "Correct any diagram implying automatic full graph materialization or direct Activator integration from new Rules."),
        ("overview",))

    lesson(r[2],
        ("RDBの表とBIのMeasureから業務の名詞・動詞・同一性へ設計を進めます。Ontologyは正規化DBやSemantic modelの代用品ではありません。",
         "Move from relational tables and BI measures to business nouns, verbs and identity. Ontology does not replace a normalized database or semantic model."),
        ("付録AのEntity/関係辞書と実列対応を開き、モデル化対象の問いを3つ記録します。",
         "Open the entity/relationship dictionary and column mappings in Appendix A; record three target business questions."),
        [
            ("「何を数えるか」を決め、Donationは1寄付、Donorは1寄付者、Metric Entityは自治体×カテゴリなどの集計粒度とします。",
             "Define what is counted: Donation is one donation, Donor one donor, and a Metric entity an aggregate grain such as municipality × category."),
            ("キーは表示名と分けます。同名自治体・同名寄付者で名前JOINせず、文字列コードの先頭ゼロを保持します。",
             "Separate identity keys from display names. Never join same-named municipalities or donors by name; preserve leading zeroes in string codes."),
            ("各関係に動詞、Origin、Target、FK/bridge、意味、推論してはいけない意味を記入します。",
             "For each relationship record the verb, origin, target, FK/bridge, intended meaning and prohibited inference."),
            ("格納済み集計属性、Semantic model所有DAX、自然言語Rules、ETL品質検査を別に分類します。",
             "Classify stored aggregate properties, semantic-model-owned DAX, natural-language Rules and ETL quality checks separately."),
        ],
        ("物理表と業務概念の対応を、同一性・粒度・経路の根拠付きでレビューできること。",
         "Review physical-to-business mappings with evidence for identity, grain and paths."),
        ("SQL JOINの形だけを根拠にis-a継承を作らず、DonorとSupplierのような異なる役割を自動統合しません。",
         "A SQL join is not an is-a hierarchy; do not automatically merge distinct roles such as Donor and Supplier."))

    lesson(r[3],
        ("10 Entity・72 static Property・1 time-series Property・15 Relationshipの意味を公開契約から確認します。",
         "Verify the public contract of 10 entities, 72 static properties, one time-series property and 15 relationships."),
        ("添付data-dictionary.txtは実CSVと型付き定義から生成されます。個票の正解集ではありません。",
         "The attached data-dictionary.txt is generated from real public CSVs and typed definitions, not a record-level answer key."),
        [
            ("DonorLivesInPrefectureを居住地域、DonationToMunicipality→MunicipalityInPrefectureを受入地域として別に追跡します。",
             "Trace DonorLivesInPrefecture as residence, separately from DonationToMunicipality → MunicipalityInPrefecture as recipient geography."),
            ("SupplierInPrefectureは登録地域、SupplierProvidesGiftは供給登録です。DonationSelectedGiftは選択で、発送・受領ではありません。",
             "SupplierInPrefecture is registration geography; SupplierProvidesGift is a registered supply link. DonationSelectedGift is selection, not shipment or receipt."),
            ("静的80,000件と8月raw15,000観測を分け、後者を一意EventIDで重複除去すると14,900件となる根拠を確認します。",
             "Separate 80,000 static donations from 15,000 August raw observations; verify that deduplication by EventID yields 14,900."),
            ("MunicipalityCategoryMetric等はNotebook 01の保存済み集計Entity、MetricsはソースSemantic modelのDAX参照と明記します。",
             "Label MunicipalityCategoryMetric and similar entities as Notebook 01 stored aggregates, and Metrics as references to source-semantic-model DAX."),
        ],
        ("「東京の寄付」の居住/受入、件数/金額、期間とレイヤーを質問前に確定できること。",
         "Resolve residence/recipient, count/amount, period and layer before answering 'Tokyo donations'."),
        ("所得・資産・富裕度や実発送者を推定しません。必要な事実がなければ未観測と回答し、登録関係への言い換えは同意後に実行します。",
         "Do not infer income, assets, wealth or the actual fulfiller. Say unavailable when facts are absent; execute a registration-based reformulation only after consent."))

    lesson(r[4],
        ("変更範囲を固定し、機能が利用できるかと権限があるかを分離して確認します。",
         "Freeze change scope and distinguish feature availability from authorization."),
        ("講師が承認したWorkspace、フォルダー、ソースID、lab-copyだけを使います。IDは非公開記録に置き、配布文書に貼りません。",
         "Use only instructor-approved workspace, folder, source IDs and lab copy. Keep live IDs in a private worksheet, never the distributed guide."),
        [
            ("容量、Ontology preview、Copilot利用可能地域、Read/Build/Writeを読み取りで確認します。Tenant設定・容量・ロールは本演習から変更しません。",
             "Read-check capacity, Ontology preview, Copilot regional availability and Read/Build/Write permissions. Do not change tenant settings, capacity or roles."),
            ("ポータルの数値フォルダー表示とAPIフォルダーIDは同じと推測せず、親子関係を読み戻して一致を記録します。",
             "Do not assume a numeric portal folder value equals an API folder ID; read back parent/child membership and record the match."),
            ("配布物のSHA256を検証し、ソースコミット、Notebookハッシュ、データハッシュ、命名契約を凍結します。",
             "Verify SHA256 and freeze source commit, notebook/data hashes and naming contract."),
            ("各write前に対象と差分、承認、復元方法を記録します。タイムアウトなら既存結果を照合してから再試行し、盲目的なcreate/ingestionを禁止します。",
             "Before each write record target, delta, approval and recovery. Reconcile ambiguous timeouts before retrying; never blindly repeat create or ingestion."),
            ("新UI機能の項目が無ければ、現物画面・日時・権限状態を保存してblockedとします。既存Ontologyや実データを削除して試しません。",
             "If a new-UI feature is missing, save the actual screen, time and permission state as blocked. Do not delete existing ontology or data to experiment."),
        ],
        ("配置スコープと変更拒否対象が一意で、各手順の成功/失敗を区別して記録できること。",
         "Deployment scope and excluded targets are unambiguous and each operation can be recorded as success or failure."),
        ("権限不足・リージョン未提供は設定変更の許可ではありません。講師へ原因を渡し、その演習だけ停止します。",
         "Missing permission/regional rollout is not authorization to change settings. Report the cause and stop only the affected lab."))

    lesson(r[5],
        ("公開8CSVからNotebook 01で型付き11テーブルを作り、Ontologyの実データ基盤を準備します。",
         "Build 11 typed tables from eight public CSVs with Notebook 01 as the ontology's actual data foundation."),
        ("workshop/v2.7.0の元seedは変更しません。v3資産が同じseedを参照する場合もコピー前後でハッシュ照合します。",
         "Do not modify the original workshop/v2.7.0 seed. Verify hashes even when v3 assets reference those same seed files."),
        [
            ("承認済みLakehouseを開きFiles/seedに8CSVをアップロードします。incrementはここへ混ぜません。dataset-manifest.jsonのheader/bytes/sha256を照合します。",
             "Open the approved Lakehouse and upload eight CSVs to Files/seed. Do not mix increment files into seed. Match manifest headers, sizes and SHA256."),
            ("Notebook 01をそのLakehouseにattachし、付録Bのパラメーターを確認して検証セルから順に実行します。",
             "Attach Notebook 01 to that Lakehouse, review the parameters in Appendix B and run validation cells in order."),
            ("READY、各ot_*テーブルの件数、キーのNULL/重複、Donation金額合計を確認します。自治体コードを整数に変換しません。",
             "Check READY, each ot_* count, null/duplicate keys and Donation amount sum. Never convert municipality codes to integers."),
            ("SQL endpointの同期後に同じテーブルを読み、ot_donation=80,000、金額=1,344,099,000円を再確認します。",
             "After SQL endpoint synchronization, read the same tables and recheck ot_donation = 80,000 and amount = JPY 1,344,099,000."),
        ],
        ("静的80,000件、11テーブル、各キーと合計が付録Aに一致し、実source tableを選択できること。",
         "Static 80,000, all 11 table counts, keys and totals match Appendix A and actual source tables can be selected."),
        ("欠損CSV、型不一致、NULL/重複、SQL同期遅延を区別し、原因を直して該当検査を再実行します。期待値を変更して通しません。",
         "Distinguish missing CSVs, type/null/duplicate defects and SQL sync delay. Fix the cause and rerun the affected check; never relax expected values."))

    lesson(r[6],
        ("新UIのConfigureと実bindingを使い、概念定義と照会可能なEntityを区別します。",
         "Use the new Configure UI and actual bindings; distinguish conceptual definitions from queryable entities."),
        ("新しい承認済みOntologyを開きます。名前は1–26文字の英数字・hyphen・underscore、先頭末尾は英数字という現在のUI制約を確認します。",
         "Open an approved new ontology. Check current UI naming limits: 1–26 alphanumeric/hyphen/underscore characters, beginning and ending alphanumerically."),
        [
            ("HomeのAdd entity type→名前→Add Entity Typeで作成し、Explorerで選択→View Entity Type detailsを開きます。",
             "Select Home → Add entity type → enter name → Add Entity Type; select it in Explorer → View Entity Type details."),
            ("Configure→Manage property bindings→Add propertiesで型を設定します。概念だけの試行はlab-copyにUnknown propertyを作り、未bindingであることを確認します。",
             "Use Configure → Manage property bindings → Add properties to assign types. For conceptual experimentation create an Unknown property only on the lab copy and verify it remains unbound."),
            ("Manage property bindings→Add binding and properties (空ならAdd properties from data)、Property binding→Addで承認済み実テーブルを選択します。",
             "Choose Manage property bindings → Add binding and properties (or Add properties from data when empty), then Property binding → Add and select the approved actual table."),
            ("Entity type propertiesで付録Aのproperty↔columnを1本ずつ照合します。Create後のEntity type updated successfullyを確認し、Cancelで閉じてConfigureから読み戻します。",
             "Reconcile every property-to-column mapping on Entity type properties with Appendix A. After Create and Entity type updated successfully, close with Cancel and read back from Configure."),
            ("Entity type keyはStringまたはIntegerの安定キーとします。キーなし定義はモデル化可能でもGraph対象になりません。Unknownはbindingまでquery/previewに現れません。",
             "Choose a stable String/Integer entity key. A keyless definition can model a concept but cannot project into graph. Unknown properties do not appear in query/preview until bound."),
            ("10Entityの明示propertyを72静的＋1時系列の公開baselineと照合し、UIに追加表示されるbacking FK列は別に数えます。native保存がpropertyを自動追加した場合は10.5節のように差分をreviewし、期待値やIDを黙って置換しません。",
             "Reconcile the ten entities' explicit properties against the public baseline of 72 static plus one time series; count additional UI backing-FK columns separately. If native save auto-adds a property, review the delta as in 10.5 rather than silently replacing expectations or IDs."),
        ],
        ("保存済みキー・型・bindingとsource行を実物から読み戻せること。空のカード作成だけでは合格しません。",
         "Read back saved keys, types and bindings and actual source rows; an empty canvas card is not a pass."),
        ("同名propertyの制約は現在UIを確認します。別型で同名を作らず、shared/reuseは14章で扱います。外部Deltaやcolumn mapping付きtableは使用しません。",
         "Check the current UI's duplicate-property constraints; never reuse a name with a conflicting type. Use Chapter 14 for shared/reused properties. Avoid external Delta or column-mapped tables."),
        ("how-to-create-entity-types", "how-to-bind-data"))

    lesson(r[7],
        ("関係の向き、キー、マッピングtableを実データと突き合わせます。新UIでは直接列対応とmapping tableを選べます。",
         "Reconcile relationship direction, keys and mapping tables with real data. The new UI supports direct column relationships or a mapping table."),
        ("6章の型付きbindingを完成させ、15関係の定義とsource列を下の表から確認します。",
         "Complete typed bindings in Chapter 6 and consult the table below for all 15 relationships and source columns."),
        [
            ("Home→Add relationship (またはExplorerの…)→Add new relationshipで一意な名前、Origin entity type、Target entity typeを入力しCreateします。",
             "Open Home → Add relationship (or Explorer …) → Add new relationship; enter a unique name, Origin entity type and Target entity type, then Create."),
            ("関係を開きOrigin/TargetのPropertyを選びます。FK直結を使う場合はUse mapping table?をoffにし、実FKと実キーを対応します。",
             "Open the relationship and select Origin/Target Property. For a direct FK mapping leave Use mapping table? off and match actual FK and key columns."),
            ("SupplierProvidesGiftはUse mapping table?をonにしot_supplier_giftを選び、SupplierIdとGiftIdをそれぞれ対応します。",
             "For SupplierProvidesGift enable Use mapping table?, select ot_supplier_gift, and map SupplierId and GiftId respectively."),
            ("Save→成功通知→Cancel後、ConfigureのRelationshipsから方向と列を読み戻します。名前重複は既知の制約なので別名の濫造で回避しません。",
             "After Save → success → Cancel, read back direction and columns from Configure → Relationships. Duplicate names are a known issue; do not create arbitrary duplicate variants."),
            ("全15関係をsourceのdistinctキー対と照合し、NULL、孤児FK、bridge重複を検査します。Full期待297,303edgeは全対象の場合のみ適用します。",
             "Reconcile all 15 relationships against distinct source key pairs; check nulls, orphan FKs and duplicate bridges. The 297,303-edge full-model expectation applies only to the full scope."),
        ],
        ("Sourceのキー対と保存bindingが一致し、居住/受入/登録の3経路を別々に説明できること。",
         "Saved bindings match source key pairs, and residence, recipient and registration paths remain distinct."),
        ("エッジが多い場合はmany-to-many増幅とbridge重複、少ない場合は孤児・型差・未bindingを調べます。図が繋がるだけで合格にしません。",
         "Too many edges suggests many-to-many amplification or bridge duplicates; too few suggests orphans, type mismatch or missing bindings. Connected artwork alone is not a pass."),
        ("how-to-create-relationship-types",))

    lesson(r[8],
        ("運用観測を静的Donationから分離してEventhouse/KQLで保持します。",
         "Keep operational observations separate from static Donation in Eventhouse/KQL."),
        ("承認済みEventhouseとKQL Databaseを使用し、配布KQLとCSV12列を照合します。",
         "Use the approved Eventhouse/KQL database; reconcile the shipped KQL and the 12 increment CSV columns."),
        [
            ("KQL Querysetを開き、配布Furusato_Eventhouse_Setup_v2.7.0.kqlの各管理commandを順に確認・実行します。既存objectを書き換える前に定義を読みます。",
             "Open a KQL queryset and review/run management commands from the shipped Furusato_Eventhouse_Setup_v2.7.0.kql in order. Read existing definitions before altering them."),
            ("DonationEventsとDonationEvents_IncrementCsvMapのEventID、DonationID、MunicipalityID、DonationAmountYen、DonatedAt等の型・CSV ordinalを確認します。",
             "Check DonationEvents and DonationEvents_IncrementCsvMap types/CSV ordinals for EventID, DonationID, MunicipalityID, DonationAmountYen, DonatedAt and the remaining columns."),
            ("配布materialized viewとAgent用helperを区別し、rawを集計するviewへ勝手にdedupを追加しません。",
             "Distinguish shipped materialized views and Agent helpers. Do not silently insert deduplication into a raw-observation view."),
            ("初回取り込み前のcountを記録し、想定外の既存行があれば停止して対象run/SourceFileを特定します。",
             "Record the pre-ingestion count; if unexpected rows exist, stop and identify their run/SourceFile."),
        ],
        ("テーブル・mapping・view/functionの定義を読め、空/既存状態を記録できること。",
         "Read back table, mapping, view/function definitions and record whether data is initially empty or pre-existing."),
        ("KQL管理commandの成功とデータ到着は別です。エラーは権限、型、mapping名を確認し、データ再送で誤魔化しません。",
         "Successful KQL management commands are not data arrival. Investigate permission, type and mapping-name errors without concealing them by resending data."))

    lesson(r[9],
        ("FileCreatedからネイティブにPipelineへ到達した証拠を、設定だけの状態と分けて検証します。",
         "Prove native FileCreated-to-Pipeline delivery separately from configuration state."),
        ("9月23日の正式start_rule/stop_ruleと完成ファイルPutBlob1回送信を維持します。new Ontology Rulesとは別のActivator経路です。",
         "Preserve the September 23 formal start_rule/stop_rule lifecycle and one complete-file PutBlob. This Activator route is independent of new Ontology Rules."),
        [
            ("Pipeline Copyのsource/sink、filenameパラメーター、Eventhouse mappingを配布定義で確認し、空payloadや固定ファイル名を実イベント成功と混同しません。",
             "Check Pipeline Copy source/sink, filename parameter and Eventhouse mapping against the shipped definition; an empty payload or fixed filename is not native-event evidence."),
            ("停止中のnative ActivatorでEdit action→Type/Subject/SourceとPipelineを確認→Apply→Saveを行います。正式Start後、upload adapterはLIVE shouldRun=true・shouldApplyRuleOnUpdate=false・明示IntegerのdelayToleranceMs>=120000を再確認します。これだけで配送成功やAPI-only初期化を証明しません。",
             "While the native Activator is stopped, use Edit action, verify Type/Subject/Source and Pipeline, then Apply→Save. After formal Start, the upload adapter rereads LIVE shouldRun=true, shouldApplyRuleOnUpdate=false and explicit integer delayToleranceMs>=120000. These do not prove delivery or API-only initialization."),
            ("OneLakeイベントの対象folder/path/filterを限定し、正式start_ruleで初回開始して読み戻します。isEnabledやpublishedだけでは開始証拠になりません。",
             "Limit the OneLake event folder/path/filter; formally start with start_rule and read back. isEnabled or published alone does not prove start."),
            ("完成したdonation_events_001.csvをローカルでheader/size/hash検査後、PutBlobを1回だけ実行します。create→append→flushや空placeholderを使いません。",
             "Validate the complete donation_events_001.csv header, size and hash locally, then issue exactly one PutBlob. Do not use create → append → flush or empty placeholders."),
            ("実イベント→activation→同じファイル/runのPipeline job→Completed→Copy行数→KQL SourceFile/件数を順に照合します。",
             "Correlate actual event → activation → matching file/run Pipeline job → Completed → Copy row count → KQL SourceFile/count in that order."),
            ("未配送の場合は一定回数で停止し、正式stop_rule後の状態を読むまで再送しません。別承認の手動runはmanualとして別に記録します。",
             "If delivery fails, stop bounded attempts and read back formal stop_rule before any resend. A separately approved manual run must be recorded as manual."),
        ],
        ("ネイティブの同一イベント系列とKQLの5,000行を対応付けられること。手動代替成功を自動配送PASSにしません。",
         "Correlate the same native event chain with 5,000 KQL rows. A successful manual fallback is not an automatic-delivery pass."),
        ("設定/開始/イベント/activation/job/Copy/KQLのどの段階が欠けるか記録し、最初の欠損段階だけを直します。盲目的な再アップロードは禁止です。",
         "Identify the first missing stage among configuration/start/event/activation/job/Copy/KQL and correct that stage only. Blind re-upload is prohibited."),
        ("how-to-use-rules",))

    lesson(r[10],
        ("3ファイルのraw観測と一意EventIDを検証し、Municipalityの運用観測を時刻付きでbindingします。",
         "Validate raw observations and unique EventID across three files, then bind Municipality observations with timestamps."),
        ("9章の配送系列が成立した場合のみ002、003を順次送ります。元CSVには意図的重複があり、除去せず保持します。",
         "Send 002 and 003 sequentially only after Chapter 9's delivery chain succeeds. Preserve the original intentional duplicate rows."),
        [
            ("002の完了とSourceFile/countを確認してから003を送信します。各ファイル5,000行で計15,000raw行を確認します。",
             "Confirm 002 completion and SourceFile/count before sending 003. Verify 5,000 rows per file and 15,000 raw rows in total."),
            ("summarize by EventIDで正確な一意件数14,900を確認します。dcountの近似を完全一致の証拠に使いません。",
             "Use summarize by EventID for exact unique count 14,900; do not use approximate dcount as exact-match evidence."),
            ("Municipality→Configure→Manage property bindings→Add binding and propertiesで実Eventhouse sourceを追加し、MunicipalityIDの共通列を指定してSaveします。",
             "In Municipality → Configure → Manage property bindings → Add binding and properties add the actual Eventhouse source; select the common MunicipalityID columns and Save."),
            ("Entity type propertiesで既存IncomingDonationAmountYenへDonationEvents.DonationAmountYenを対応し、Timeseries<Integer>とTimestamp column=DonatedAtを確認します。_2などの重複名を無条件採用せず、保存前後の全property集合も比較します。",
             "Map DonationEvents.DonationAmountYen to existing IncomingDonationAmountYen; verify Timeseries<Integer> and Timestamp column = DonatedAt. Do not blindly accept a duplicate _2 name; compare the complete property sets before and after saving."),
            ("保存後はOntology agentのPlanで既存bindingだけを使うbounded operational queryを実行し、nativeの実行query表示と独立KQLを照合します。managed child-Eventhouseのquery headを確認しますが、実URIや回答値はprivateに保ちます。TS Graphやdirect dashboardの成功へ読み替えません。",
             "After saving, use Ontology agent Plan for a bounded operational query over the existing binding; reconcile the native executed-query display with independent KQL. Inspect the managed child-Eventhouse query head privately. Keep actual URIs and response values private; this proves neither TS Graph nor direct dashboard integration."),
        ],
        ("raw15,000/unique14,900/duplicate100、時刻・相関キー・金額が一致すること。静的合計と合算しません。",
         "Match raw 15,000 / unique 14,900 / duplicate 100, timestamp, correlation key and amount. Do not add them to static totals."),
        ("列名・時刻timezone・materialized viewの粒度差を調べます。多重backingのGraph不適格をbinding失敗と混同しません。",
         "Investigate column, timezone and materialized-view-grain differences. Graph ineligibility from multiple backing tables is not a binding failure."),
        ("how-to-bind-data",))
    sub(r[10], "4", ("正確なraw／一意観測の照合", "Exact raw/unique observation checks"), [
        code("DonationEvents\n| summarize RawRows=count(), RawAmountYen=sum(DonationAmountYen)\n\nDonationEvents\n| summarize by EventID\n| count\n\nDonationEvents\n| summarize Rows=count() by EventID\n| summarize DuplicateRows=sum(Rows - 1)", "KQL"),
        note("対象runが複数ある場合は講師が承認したrun/SourceFile/期間を各queryの先頭で同じ条件に絞ります。配布期待値は固定3CSV1回分です。",
             "When multiple runs exist, apply the same approved run/SourceFile/time filters at the start of every query. Shipped expectations represent exactly one copy of the three fixed CSVs."),
    ])

    lesson(r[11],
        ("Notebook 05のSilver/Gold品質処理を体験し、元データとcurated分析モデルを区別します。",
         "Run Notebook 05 Silver/Gold quality processing and distinguish original data from the curated analytics model."),
        ("01と増分検査を完了し、05の対象Lakehouse/スキーマを固定します。05は元データ・標準10問を上書きする手順ではありません。",
         "Finish Notebook 01 and increment checks; freeze Notebook 05's Lakehouse/schema. Notebook 05 does not overwrite source data or the standard ten questions."),
        [
            ("05を対象Lakehouseにattachし、APPLY_CHANGES=Falseでpreviewします。入出力表、破壊的変更、planのSHA256をレビューします。",
             "Attach 05 to the target Lakehouse and preview with APPLY_CHANGES=False. Review input/output tables, destructive changes and plan SHA256."),
            ("型整形、キー検査、重複除去、隔離/quarantine、カレンダーと静的/増分レイヤーの扱いを確認します。reject行を黙って落としません。",
             "Review type conformance, key checks, deduplication, quarantine, calendar and static/increment handling. Never silently discard rejected rows."),
            ("承認後に配布のplan確認パラメーター、APPLY_CHANGES=True、EXCLUSIVE_APPLY_WINDOW_CONFIRMED=Trueを明示し、他writeを止めて実行します。",
             "After approval provide the shipped plan-confirmation parameter, APPLY_CHANGES=True and EXCLUSIVE_APPLY_WINDOW_CONFIRMED=True; stop competing writers before applying."),
            ("gold.donations等の実スキーマと入出力/隔離件数を照合します。StaticSeedとRealtimeIncrementをDataSourceで分け、併合は05の品質契約に基づく分析用と明記します。",
             "Reconcile actual schemas such as gold.donations, input/output counts and quarantine. Separate StaticSeed and RealtimeIncrement using DataSource; the curated union is justified by Notebook 05's quality contract."),
            ("IsHighValueは57,000円超の分析フラグで、wealth判定・通知ルールではないことを確認します。",
             "Verify IsHighValue is an analytical flag for donations exceeding JPY 57,000, not a wealth classification or notification rule."),
        ],
        ("件数の増減を重複/隔離/対象範囲として説明し、Goldと元ot_*の非同一性を確認できること。",
         "Explain count changes through duplicates, quarantine and scope; demonstrate Gold is not identical to original ot_* tables."),
        ("previewハッシュが変われば再承認します。欠損参照や重複が残ればBI側を直して隠さず品質処理を修正します。",
         "Reapprove when the preview hash changes. Fix quality processing rather than masking missing references or duplicates in BI."))

    lesson(r[12],
        ("この演習のDAX-backed MetricsではDAXの所有者はSemantic modelです。Measureを参照し、通常propertyや保存済みMetric Entityとは区別します。RESTに記述されたnon-DAX explicit metricは別の形です。",
         "For this lab's DAX-backed Metrics, the semantic model owns DAX. They proxy its measures, separately from ordinary properties or stored Metric entities. The REST definition's non-DAX explicit metric is a different shape."),
        ("05のGold、配布Direct Lake modelの実binding、Read+Buildを確認します。Resolve underlying DAXにはsource modelのWriteが必要です。",
         "Check Notebook 05 Gold, actual bindings of the shipped Direct Lake model and Read+Build. Resolve underlying DAX requires Write on the source model."),
        [
            ("配布modelの寄附tableにある寄附総額、寄附件数、平均寄附額の定義とformatを確認し、下のDAXをソースで実行します。",
             "Inspect the shipped 寄附 table's 寄附総額, 寄附件数 and 平均寄附額 definitions/formats; execute the DAX below against the source."),
            ("Semantic modelのGenerate Ontology (無ければ…menu)から承認済み別lab itemを作成します。主Ontologyを置換しません。",
             "Use Generate Ontology on the semantic model (or … menu) to create an approved separate lab item. Do not replace the main ontology."),
            ("View Entity Type details→MetricsでMeasureの所属table・source model・名前を確認します。MeasureはDAXが複数表を参照しても定義tableのEntityへ付きます。",
             "In View Entity Type details → Metrics check owning table, source model and name. A measure belongs to the entity of its defining table even if its DAX references several tables."),
            ("Metric details→View expressionで元DAXを比較します（表示後はHide expression、公式資料ではResolve underlying DAXとも記載）。許可が無ければ式参照だけblockedとし、勝手に権限を足しません。",
             "Compare source DAX through Metric details → View expression (Hide expression once open; also described as Resolve underlying DAX in documentation). If unauthorized, mark expression inspection blocked; do not add permission."),
            ("同じStaticSeed filter、期間、単位でOntology agentへMeasure照会を依頼し、実DAX・結果とソース実行値を照合します。",
             "Ask the Ontology agent to query the measure with the same StaticSeed filter, time and unit; reconcile actual DAX/results with direct source execution."),
            ("Ontologyのdescription/formula編集はmodelのDAXを変えません。source変更後はOntologyをrefreshして再確認します。Metricsが見えなければMeasure所有tableと生成経路を調べます。",
             "Editing a description/formula in ontology does not alter model DAX. Refresh ontology after source changes and recheck. If Metrics is absent, inspect measure ownership and generation route."),
        ],
        ("sourceと同一filterの件数・金額・平均が一致し、Metricのsource linkとDAX所有者を説明できること。",
         "Counts, amounts and averages match under identical source filters; explain the metric source link and DAX owner."),
        ("Data AgentはOntologyのsemantic-model groundingを継承しません。17章でmodelを明示source登録し、semantic-model-backed EntityをGraphへ投影しません。",
         "Fabric Data Agent does not inherit semantic-model grounding through ontology. Explicitly configure the model as a source in Chapter 17; do not project semantic-model-backed entities into graph."),
        ("how-to-use-metrics", "how-to-generate-from-semantic-models", "how-to-use-ontology-agent"))
    sub(r[12], "4", ("配布modelを使う再現可能なDAX", "Reproducible DAX against the shipped model"), [
        code("EVALUATE\nCALCULATETABLE(\n    ROW(\"Donation count\", [寄附件数],\n        \"Donation amount JPY\", [寄附総額],\n        \"Average JPY\", [平均寄附額]),\n    '寄附'[データソース] = \"StaticSeed\"\n)", "DAX"),
        p("寄附総額 = SUM('寄附'[寄附金額])、寄附件数 = COUNTROWS('寄附')、平均寄附額 = DIVIDE([寄附総額], [寄附件数])。Gold品質差分が無ければStaticSeedは80,000件/1,344,099,000円です。無filterのGold合計と比較しません。",
          "寄附総額 = SUM('寄附'[寄附金額]); 寄附件数 = COUNTROWS('寄附'); 平均寄附額 = DIVIDE([寄附総額], [寄附件数]). Without quality exclusions, StaticSeed is 80,000 / JPY 1,344,099,000. Do not compare with an unfiltered Gold total."),
    ])

    lesson(r[13],
        ("Metadataと自然言語Business Rulesで意味を共有し、実行可能な制約や自動actionと区別します。",
         "Share meaning through metadata and natural-language Business Rules, distinguishing them from executable constraints or automatic actions."),
        ("Notebook 02の既存契約は比較参考です。新UIへ一括適用する前にAPI適合性と差分を確認し、未対応ならUIで同じ意味を登録します。",
         "Notebook 02's existing contract is a comparison reference. Check API compatibility and delta before bulk application to the new UI; if unsupported, author equivalent meaning through the UI."),
        [
            ("Entity→Configure→MetadataでDescription、Synonyms、Additional metadataを編集してUpdateします。現在のhow-toでSynonymsを編集できるUIはentityです。REST新定義で受け付けるsynonym構文とは区別します。",
             "In Entity → Configure → Metadata edit Description, Synonyms and Additional metadata, then Update. The current how-to exposes synonym editing on entities; distinguish that UI surface from synonym syntax accepted by the new REST definition."),
            ("PropertyのEdit property metadata、RelationshipのMetadata→Editで単位JPY、grain、レイヤーと登録/配送の境界を記入します。property/relationshipにsynonymを仮定しません。",
             "Use Edit property metadata and Relationship → Metadata → Edit for JPY units, grain, layer and registration/delivery boundaries. Do not assume property/relationship synonyms."),
            ("Explorer→Overview→Rules→Create ruleまたはNew ruleでRule name/Rule definitionを入力します。",
             "Open Explorer → Overview → Rules → Create rule or New rule and enter Rule name and Rule definition."),
            ("Linked ontology concepts→Add conceptで実Entity/Property/Relationshipを選択しSaveします。metadataにcategoryとrationaleを追加し、最終Save後に再度開きます。",
             "Use Linked ontology concepts → Add concept to select actual entities/properties/relationships and Save. Add category/rationale metadata, finally Save and reopen."),
            ("例:「SupplierProvidesGiftは登録された供給関係のみを意味し、実際の発送者・受領を断定しない」をSupplierとGiftの関係へlinkします。",
             "Example: 'SupplierProvidesGift denotes only a registered supply relationship; do not assert actual shipment or receipt.' Link it to the Supplier–Gift relationship."),
            ("同じ曖昧質問を新しい会話で再実行し、規則が説明に使われたかを測ります。SQL/KQL生成の強制制御やRLS代替と主張しません。",
             "Repeat the same ambiguous question in a fresh conversation and measure whether the rule informs the explanation. Do not call it enforced SQL/KQL generation or an RLS replacement."),
        ],
        ("規則、linked concepts、metadataが保存され、説明を改善したかを実回答から別途評価できること。",
         "The rule, linked concepts and metadata persist; any improvement is separately evaluated from actual answers."),
        ("Business Rulesは自然言語contextでデータ検査・actionを実行しません。新Ontologyに直接Activator連携はありません。9章の独立Activatorを自動移行しません。",
         "Business Rules are natural-language context and execute neither checks nor actions. New ontology has no direct Activator integration; do not assume migration of the separate Chapter 9 Activator."),
        ("how-to-add-metadata", "how-to-use-rules"))

    lesson(r[14],
        ("namespaceによるidentity、is-a継承、shared-property参照を別の再利用機構として検証します。",
         "Validate namespace identity, is-a inheritance and shared-property references as separate reuse mechanisms."),
        ("すべてlab-copyで実施し、標準10Entity・15関係の採点用baselineを変えません。新実験は別に記録します。",
         "Perform all changes on a lab copy; leave the scored ten-entity/fifteen-relationship baseline unchanged and record experiments separately."),
        [
            ("まず実UIでnamespace authoringの有無を確認します。現行Learnは+ Namespace/Manage namespacesやChoose namespaceを説明しますが、この環境の観測では未確認です。表示されなければunverifiedとして停止し、架空のribbon/selectorを探す手順やAPIからのUI推測で埋めません。",
             "First inspect actual UI availability of namespace authoring. Current Learn documents + Namespace/Manage namespaces and Choose namespace, but these controls are unverified in this environment's observation. If absent, stop as unverified; do not invent ribbon/selector steps or infer UI from API support."),
            ("各conceptは1namespaceだけに所属することを確認します。Defaultは削除不可、参照が残るnamespaceも削除不可です。rename時の参照更新を読みます。",
             "Confirm each concept belongs to exactly one namespace. Default cannot be deleted, nor can referenced namespaces. Read back references after a rename."),
            ("別lab itemでAdministrativeAreaを親にMunicipalityをAdd entity type→Additional configuration→Choose entity to inherit fromで作成します。Entity名は業務概念のままにし、実験識別はitem/folderで行います。Donor→Supplierのis-aを作りません。",
             "In a separate lab item create Municipality is-a AdministrativeArea via Add entity type → Additional configuration → Choose entity to inherit from. Keep business-concept entity names; isolate experiments by item/folder. Never make Donor is-a Supplier."),
            ("派生型はsingle-parentで、継承propertiesとproperty metadataを読みます。Learnはentity-level metadataを非継承と説明しますが、本演習の実UIではDescription/Synonyms/Additional metadataをInheritedと表示しました。保存値・effective UI表示・local overrideを分けて14.4節で検証します。通常relationshipとdata bindingは別途確認します。",
             "Read single-parent inherited properties and property metadata. Learn describes entity-level metadata as non-inherited, but this workshop's actual UI labelled Description/Synonyms/Additional metadata as Inherited. Verify stored values, effective UI display and local overrides separately in 14.4. Check ordinary relationships and data bindings independently."),
            ("Lineage/Relationship表示を切替え、propertyのlocal metadata override→base変更→override維持→revertで現在base値へ戻る動作を確かめます。",
             "Switch Lineage/Relationship views; test local property-metadata override → base change → preserved override → revert to the current base value."),
            ("Explorer→Shared properties→New shared propertyでSourceNote(String)を作成します。2EntityでManage property bindings→Add existing propertyから参照し、Used byとlocal/shared badgeを確認します。",
             "Create SourceNote (String) using Explorer → Shared properties → New shared property. Reference it from two entities via Manage property bindings → Add existing property, and inspect Used by and local/shared badges."),
            ("共有property自体はunboundでbindingはEntityごとです。説明だけの試行で架空列をbindしません。detach時は影響を読み、local状態を保つsoft detachとfull deleteを区別します。",
             "The shared property itself remains unbound; bindings are entity-local. Do not bind invented columns for a conceptual experiment. Inspect impacts and distinguish soft detach preserving local state from full delete."),
        ],
        ("qualified identity、single-parent lineage、shared参照/overrideの来歴を読み戻せること。未binding派生型は概念のみと記録します。",
         "Read back qualified identity, single-parent lineage and shared-reference/override provenance. Record an unbound derived type as conceptual only."),
        ("循環・複数親・同namespace重複を避けます。polymorphic queryはbaseと直下子の1hopで、全深さや通常関係継承を期待しません。",
         "Avoid cycles, multiple parents and duplicates in a namespace. Polymorphic querying covers base plus direct children, one hop; do not expect arbitrary depth or ordinary relationship inheritance."),
        ("how-to-use-namespaces", "how-to-use-inheritance", "how-to-reuse-properties"))

    lesson(r[15],
        ("Ontology Copilotは公式資料のOntology agentです。設計、説明、query、改善patchをPlanで確認してからlab-copyへActします。",
         "Ontology Copilot is the official Ontology agent. Review design, explanations, queries and improvement patches in Plan before Act on a lab copy."),
        ("組み込みUIを使用します。Main Data AgentやMCP clientをその代用品の実施証拠にしません。対象Ontologyとsource ID allowlistを非公開に固定します。",
         "Use the built-in UI. Main Data Agent or MCP-client activity is not substitute execution evidence. Privately freeze the target ontology and source-ID allowlist."),
        [
            ("空itemならStart with Ontology agent、既存ならtoolbarのOntology agentを開き、Planを確認します。無関係Workspace探索は許可しません。",
             "Use Start with Ontology agent on an empty item or toolbar → Ontology agent on an existing item; confirm Plan. Do not authorize unrelated-workspace discovery."),
            ("添付なし新会話で下のbounded promptを送り、discoveryのsource/table/列、draft、validateのerror/warning、read-only previewを保存します。まだActしません。",
             "In a fresh no-attachment conversation send the bounded prompt below; save discovery source/table/columns, draft, validation errors/warnings and read-only preview. Do not Act yet."),
            ("ページrefresh等でfresh会話を始め、同じbaselineでbusiness-requirements.pdf、data-dictionary.txt、domain-model.png、revision-requirements.txtの現行4ファイルを添付します。hashを凍結し、upload表示と実際の内容利用を別々に記録します。",
             "Start a fresh conversation, for example by page refresh, on the same baseline. Attach the current four files: business-requirements.pdf, data-dictionary.txt, domain-model.png and revision-requirements.txt. Freeze hashes and record both upload indication and actual use of their content."),
            ("同じscope/promptでdraftとpreviewを比較し、居住/受入/登録、raw/unique、キー型、source binding、配送や富裕度の非推論を採点します。",
             "Compare drafts/previews under the same scope/prompt; score residence/recipient/registration, raw/unique, key types, bindings and non-inference of delivery/wealth."),
            ("修正はrevision-requirements.txtを明示してmetadataだけのpatchを求めます。追加/変更/削除とstable IDsをレビューし、validate/previewを再確認します。",
             "For revision explicitly reference revision-requirements.txt and request a metadata-only patch. Review additions/edits/deletions and stable IDs; repeat validation/preview."),
            ("承認した最終差分だけをlab-copyに適用する旨を明示してActに切替えます。Apply/publish結果と実定義を読み戻し、baselineとID、binding、対象外itemを比較します。",
             "Explicitly authorize only the approved final delta on the lab copy and switch to Act. Read back apply/publish and the actual definition; compare IDs, bindings and out-of-scope items with baseline."),
        ],
        ("Plan無変更、実添付と利用、preview、明示Act、安定IDの保存を別々の証拠で示すこと。生成5問は探索的確認です。",
         "Separately evidence unchanged Plan, actual attachment/use, preview, explicit Act and stable IDs. The five generated questions are exploratory checks."),
        ("10files/conversation、5MB/file、会話内だけのcontextです。refresh/タブ閉鎖で会話終了、最大24時間。添付は取り込み/RDF importでなく、機密や独立評価の正解は入れません。",
         "Limit 10 files/conversation and 5 MB/file; context is conversation-local. Refresh/tab close ends the conversation; maximum lifetime is 24 hours. Attachments are not ingestion/RDF import; never include secrets or independent evaluation answers."),
        ("how-to-use-ontology-agent",))
    sub(r[15], "4", ("添付なし／あり共通のPlan prompt", "Common Plan prompt for no-attachment/attachment runs"), [
        prompt(
            "Planのまま作業してください。対象は講師が指定した <LAB_ONTOLOGY_ID>、許可sourceは <LAKEHOUSE_ID>、<EVENTHOUSE_ID>、<SEMANTIC_MODEL_ID> のみです。未指定sourceを探索しないでください。現在の定義とstable IDsを読み、発見した実table/column/keyを根拠にdraft、validate、read-only previewを提示してください。Entityの新規作成・削除・データwrite・workspace変更はまだしないでください。居住地域、受入地域、供給登録を区別し、配送/受領/所得/資産を推定しないでください。各変更と変えない項目、未解決の警告、queryの実行根拠を示してください。",
            "Remain in Plan. Target only instructor-specified <LAB_ONTOLOGY_ID>; permitted sources are <LAKEHOUSE_ID>, <EVENTHOUSE_ID>, <SEMANTIC_MODEL_ID> only. Do not discover unspecified sources. Read the current definition and stable IDs, then discover actual tables/columns/keys and provide a grounded draft, validation and read-only preview. Do not yet create/delete entities, write data or change the workspace. Distinguish residence, recipient geography and registered supply; do not infer delivery, receipt, income or assets. Show each proposed change, stable items, unresolved warnings and actual query evidence."),
        prompt(
            "business-requirements.pdf、data-dictionary.txt、domain-model.pngとrevision-requirements.txtを読み、Notebook05 GoldのStaticSeed/RealtimeIncrementとquality acceptanceを区別してください。manual approval・支払・発送・自動配送を推測しません。提案のobject kind、reusableProperty/redefines、native Version保存とsaved readback計画を示してください。同じ許可source/baselineでPlan→draft→validate→previewを行い、まだ保存しないでください。",
            "Read business-requirements.pdf, data-dictionary.txt, domain-model.png and revision-requirements.txt. Distinguish Notebook05 Gold StaticSeed/RealtimeIncrement and quality acceptance from manual approval, payment, shipment or automatic delivery. Show the proposed object kind, reusableProperty/redefines, native Version preservation and saved-readback plan. Use the same approved sources/baseline for Plan→draft→validate→preview, without saving yet."),
    ])
    sub(r[15], "5", ("Act承認・照会・会話記録", "Act approval, query and conversation records"), [
        prompt(
            "レビュー済み差分 <APPROVED_PATCH_REFERENCE> だけを <LAB_ONTOLOGY_ID> に適用することを承認します。Act前に対象と変更一覧を再提示し、stable IDs、実binding、他item、source dataを保持してください。新規Agent作成や範囲外writeは承認しません。適用後、保存された定義を読み戻して追加/変更/削除とIDを比較し、成功と未解決事項を分けて報告してください。",
            "I approve only reviewed delta <APPROVED_PATCH_REFERENCE> on <LAB_ONTOLOGY_ID>. Before Act restate target and changes; preserve stable IDs, actual bindings, other items and source data. Creating agents or out-of-scope writes is not authorized. After application read the saved definition back, compare additions/edits/deletions and IDs, and separately report success and unresolved issues."),
        p("QueryはKQL/SQL/GQLで既定最大1,000行、DAXで200行という現在のbounded結果です。上位subsetを全体母集団と見なさず、必要な全体集計はエンジン側で行います。UIが示すqueryとsourceを保存します。",
          "Current bounded defaults are up to 1,000 KQL/SQL/GQL rows and 200 DAX rows. Do not treat a top subset as the entire population; aggregate at the engine when needed. Save the actual UI query and source."),
        p("会話のサービス保持は終了後最大2日という現行資料を確認し、組織の利用基準を守ります。会話履歴をモデルの長期記憶やバックアップと扱いません。",
          "Current documentation permits service retention up to two days after a conversation ends; follow organizational policy. Do not treat chat history as durable model memory or backup."),
    ])
    sub(r[15], "7", ("観測されたmetadata-only Actの回帰と厳密なreadback", "Observed metadata-only Act regression and strict readback"), [
        note(
            "孤立UI labで、entity synonym「行政区域」だけを追加する承認済みActが、既存AreaName propertyのreusableProperty: AreaNameを同時に削除しました。Copilotは他を変更していないと説明し、全lineage IDsも保持されましたが、共有参照の保持条件はFAILEDでした。成功メッセージやID一致だけで安全なpatchとは判定しません。",
            "In an isolated UI lab, an approved Act to add only entity synonym 行政区域 also removed reusableProperty: AreaName from the existing AreaName property. Copilot said other fields were unchanged and all lineage IDs were preserved, but shared-reference preservation FAILED. A success message or matching IDs is not proof of a safe patch.",
            "stop"),
        p(
            "この観測は特定のmetadata-only変更の回帰であり、core dataset/source変更ではありません。保存前Plan previewはbaseline定義を維持しましたが、Act後のauthoritative TMDL diffは予期しないdetachを示しました。rollbackと修正後の再試験は別の証拠で記録し、当初の失敗を削除しません。",
            "This is a regression in one metadata-only change, not a core dataset/source change. Pre-Act Plan preview preserved the baseline definition, while the authoritative post-Act TMDL diff showed an unexpected detach. Record rollback and corrected retesting as separate evidence; do not erase the original failure."),
        p(
            "このケースではnative Version historyで失敗candidateをlab-act-shared-link-regressionとして保存し、lab-baselineへ復元しました。coordinatorの復元観測と保存定義の比較により、元semantic partsへの完全一致と共有参照の復元を確認しました。失敗candidateはpromoteしていません。",
            "In this case native Version history saved the failed candidate as lab-act-shared-link-regression and restored lab-baseline. The coordinator's observed restore and comparison of saved definitions confirmed exact original semantic parts and the restored shared reference. The failed candidate was not promoted."),
        note(
            "これはexternal source binding 0・projected Metricsなしのunbound構造labです。この範囲ではTMDL semantic parts一致が対象の復元確認になりますが、sourceデータrollbackは試験していません。backingMeasureを持つMetric-richモデルへこの証明方法を一般化せず、21.4節のnative link検査を維持します。修正版のbounded再試験は別判定です。",
            "This was an unbound structural lab with zero external source bindings and no projected Metrics. Equal TMDL semantic parts verify the targeted restoration here, but source-data rollback was not tested. Do not generalize this proof to Metric-rich models with backingMeasure; retain Chapter 21.4's native-link checks. A bounded corrective retest is a separate outcome.",
            "gate"),
        table(
            [("保持条件", "Invariant"), ("読戻しで比較する対象", "Compare in authoritative readback")],
            [
                [("安定ID", "Stable IDs"), ("entity/property/relationshipのlineageTag。ID一致だけでは不十分。", "Entity/property/relationship lineageTag; ID equality alone is insufficient.")],
                [("共有参照", "Shared references"), ("各propertyのreusablePropertyとmodel-level reusablePropertyの対応。予期しないlocal化を禁止。", "Each property's reusableProperty association and model-level shared definition; reject unintended localization.")],
                [("継承", "Inheritance"), ("baseEntityType、redefines、overriddenMetadataFields。", "baseEntityType, redefines and overriddenMetadataFields.")],
                [("構造・型・キー", "Structure, types and keys"), ("Entity/property集合、dataType、keyProperty。", "Entity/property set, dataType and keyProperty.")],
                [("binding", "Bindings"), ("backingTable、backingConfiguration、additionalBackingTable、relationship、source参照。", "backingTable, backingConfiguration, additionalBackingTable, relationships and source references.")],
                [("許可差分", "Approved delta"), ("承認したsynonym/description/Rule statementだけか。その他のsemantic差分はfailure。", "Only the approved synonym/description/rule statement; any other semantic delta is a failure.")],
            ],
            ("Actの安全性は保存結果の不変条件で判定", "Judge Act safety by invariants in the saved result"),
        ),
        prompt(
            "Planで、承認したmetadata変更だけを提案してください。既存lineage IDsだけでなく、すべてのreusableProperty参照、baseEntityType/redefines/overriddenMetadataFields、property集合・型・keyProperty、backingTable/backingConfiguration、relationshipとsource参照を保持します。追加・削除・detach・再生成があれば適用せず報告してください。Act後は全partを読み戻して承認差分以外がないか比較し、失敗時は停止してください。",
            "In Plan propose only the approved metadata change. Preserve not only lineage IDs but all reusableProperty references, baseEntityType/redefines/overriddenMetadataFields, property sets/types/keyProperty, backingTable/backingConfiguration, relationships and source references. If anything would be added, removed, detached or regenerated outside approval, stop and report it. After Act read every part back and compare against the approved delta; stop on any failed invariant."),
        note(
            "このprompt自体は強制制御ではありません。安全条件を破ったらlabのAct判定はfailedのままにし、coordinatorが保存済みVersion history baselineへ復元して共有参照・property source・bindingを再確認します。修正版は新しい凍結candidateで独立に再評価します。",
            "This prompt is not enforcement. On an invariant violation keep the Act lab failed; the coordinator restores the saved Version history baseline and verifies shared references, property source and bindings. Evaluate a corrected, newly frozen candidate independently."),
    ])

    lesson(r[16],
        ("関係経路の問いだけに必要なsubsetを選びGraphを実体化します。全Ontologyの必須工程ではありません。",
         "Materialize only the graph subset needed for relationship-path questions. Graph is not mandatory for every ontology."),
        ("static Relationships companionの同じLakehouse bindingを使います。primary operational TS coreは変更しません。Eligible表示だけではmaterialization成功を保証せず、semantic-model-backed/keyless/unbound等の制限も実物で確認します。",
         "Use the static Relationships companion with bindings to the same Lakehouse; leave the primary operational TS core unchanged. Eligible alone does not guarantee materialization; inspect actual semantic-model-backed/keyless/unbound and other limits."),
        [
            ("「返礼品に登録された供給者」の問いを固定し、Gift、Supplier、SupplierProvidesGiftを最小候補にします。",
             "Freeze the question 'Which suppliers are registered for a gift?' and start with Gift, Supplier and SupplierProvidesGift."),
            ("Home→Manage graph→Configure GraphでStatusとIneligible tooltipを読み、Eligibleだけを選択してContinueします。",
             "Open Home → Manage graph → Configure Graph; read Status and Ineligible tooltips, select only eligible items and Continue."),
            ("Projection Summaryでnode/edge範囲を確認しMaterializeします。処理完了まで待ち、失敗と未完了を成功扱いしません。",
             "Confirm node/edge scope in Projection Summary and select Materialize. Wait for completion; failure or pending is not success."),
            ("Explore graph→ComponentsのCHECKBOXで対象を選びます。行クリックだけはfocusで、選択とは限りません。Add filter→PrefectureId=42などの承認filter→Run query→Table viewでID・名前・edge方向を確認します。",
             "Select the Components CHECKBOX in Explore graph; clicking a row only focuses it and may not select it. Use Add filter with an approved condition such as PrefectureId=42, Run query, then Table view to inspect IDs, names and edge direction."),
            ("下のGQLを実labelで実行し、ot_supplier_giftの同じキー対と照合します。namespace付きならComponentsのprefixをそのまま使用します。",
             "Run the GQL below using actual labels and reconcile the same key pairs in ot_supplier_gift. If namespaced, use the Components prefix exactly."),
            ("source更新の反映は別管理です。承認してGraph item→…→Schedule→Refresh nowを実行し、source時点を記録して再照合します。",
             "Source freshness is separate. When approved use graph item → … → Schedule → Refresh now, record source time and reconcile again."),
        ],
        ("選択subsetの実GQL pathとsourceキー対が一致すること。Fullモデル期待値をsubsetへ適用しません。",
         "Actual GQL paths match source key pairs for the selected subset. Never apply full-model expectations to a subset."),
        ("primary TS coreはEligibleでもInvalidPropertyTypeで失敗しました。TSを削除/型変更して成功を作らず、static companionへ分離します。表示node captionがrankでもbusiness IDとは限らないためTable viewのpropertiesを正本にします。",
         "The primary TS core failed with InvalidPropertyType despite Eligible. Do not remove/retype its TS property to manufacture success; use the separate static companion. Default node captions can be ranks, not business IDs; verify properties in Table view."),
        ("how-to-use-ontology-graph",))
    sub(r[16], "4", ("実labelを確認してからGQLを実行", "Execute GQL after inspecting actual labels"), [
        code("MATCH (s:Supplier)-[r:SupplierProvidesGift]->(g:Gift)\nRETURN s.SupplierId, g.GiftId\nLIMIT 20", "GQL"),
        code("SELECT TOP (20) SupplierId, GiftId\nFROM dbo.ot_supplier_gift\nORDER BY SupplierId, GiftId;", "SQL"),
        note("この2つの20行は任意subsetと整列subsetなので、そのまま同一集合を要求しません。照合は同じGiftId filterと同じordering/limitを追加するか、全キー対の集合・件数で行います。",
             "These twenty-row samples are respectively arbitrary and ordered; do not assert they are the same set. Reconcile using the same GiftId filter and ordering/limit, or compare complete key-pair sets/counts."),
    ])

    lesson(r[17],
        ("主Fabric Data Agent1件のSQL/KQL/Ontologyと、同じAgentのCode Interpreterを検証します。",
         "Validate SQL/KQL/ontology sources on one main Fabric Data Agent and Code Interpreter on that same agent."),
        ("既存指示全文、source metadataとfew-shotsは本章の保持参考にあります。改訂時はhashを固定し、標準10問の採点条件を変えません。",
         "Full existing instructions, source metadata and few-shots remain in this chapter's retained reference. Freeze revision hashes without changing the standard ten-question scoring conditions."),
        [
            ("主Agentに承認済みLakehouse SQL、Eventhouse KQL、用途を確認したOntologyを登録します。関係照会用の新候補はstatic Relationships companionを使い、primary TS coreは運用照会用に保持します。mainへのsource変更は別承認・評価後だけで、診断用Temp候補を第2の本番Agentにしません。",
             "Configure approved Lakehouse SQL, Eventhouse KQL and an ontology selected for its purpose. The new relationship-query candidate uses the static Relationships companion, while the primary TS core remains for operational queries. Change main routing only after separate approval/evaluation; an isolated Temp diagnostic candidate is not a second production agent."),
            ("DAX比較実験では同じ主AgentへSemantic modelを明示source追加します。Ontology経由のsemantic-model groundingだけではData AgentはDAXを使えません。",
             "For DAX comparison explicitly add the semantic model as a source to the same main agent. Ontology-carried semantic-model grounding alone is unavailable to Fabric Data Agent."),
            ("baseline3sourceとDAX実験追加後の設定を別snapshotにし、model直接接続の効果をOntology Copilotと混同しません。",
             "Snapshot baseline three-source and DAX-enabled configurations separately; do not conflate direct-model effects with Ontology Copilot."),
            ("同じAgentでCode Interpreterをenableし、固定範囲の実query結果から集約・図・CSVを作成します。全件を取得した証拠なしにTOP1000から全体統計を出しません。",
             "Enable Code Interpreter on that same agent and create aggregates/charts/CSV from actual bounded-query results. Do not derive population statistics from TOP1000 without complete-scope evidence."),
            ("回答本文、選択source、実query、返却値、CI tool呼出、実downloadを保存し、query-onlyとCI実行を区別します。",
             "Save answer, selected source, executed query, results, CI tool call and actual download; distinguish query-only execution from actual CI."),
        ],
        ("主Agentは1件のまま、source選択・DAX直接構成・CI生成物の来歴を確認できること。",
         "Maintain one main agent and verify source selection, direct DAX configuration and CI output provenance."),
        ("資料どおりの指示は権限制御ではありません。DataNotAvailable、schemaだけ、CI未呼出は未達として記録し、別Agentを増やして逃げません。",
         "Instructions are not access control. Record DataNotAvailable, schema-only results or missing CI invocation as unmet, not a reason to create substitute agents."),
        ("how-to-use-ontology-agent", "how-to-add-metadata"))

    lesson(r[18],
        ("同じ業務用語を異なるエンジンで使い、結果の根拠と制限を比較します。",
         "Use the same business vocabulary across engines and compare evidence and limits."),
        ("構成・データ・期間を凍結し、各問いを新会話で開始します。未完了のgraph/metricsを既成事実としません。",
         "Freeze configuration, data and time window; start each question in a fresh conversation. Do not assume unfinished graph/metrics are available."),
        [
            ("シナリオA: 「東京の寄付」は居住/受入と件数/金額をまず確認し、合意した静的範囲をSQL/DAXで照合します。",
             "Scenario A: clarify residence/recipient and count/amount for 'Tokyo donations', then reconcile the agreed static scope with SQL/DAX."),
            ("シナリオB: 8月のraw観測と一意EventIDをKQLで分け、重複を含むviewの金額とdedup後金額を明示します。",
             "Scenario B: distinguish August raw observations and unique EventID in KQL; explicitly label raw-view versus deduplicated amounts."),
            ("シナリオC: Gift→登録SupplierのpathをGQLとSQLの同じGiftIdで比べ、実配送とは答えないことを確認します。",
             "Scenario C: compare Gift-to-registered-Supplier paths in GQL and SQL for the same GiftId; verify the answer never claims actual delivery."),
            ("シナリオD: source-owned寄附総額を同一DataSource/日付filterでOntology Copilotと直接接続済みData Agentへ問い、実DAXを確認します。",
             "Scenario D: query source-owned 寄附総額 with identical DataSource/date filters through Ontology Copilot and directly connected Data Agent, inspecting actual DAX."),
            ("CIでは確認済み集約だけをplotし、titleに期間/単位/分母を入れます。ランキングは保存済みrankと今回のfilter内rankを区別します。",
             "Plot only reconciled aggregates in CI and label time, units and denominator. Distinguish stored ranks from ranks calculated in the current filter."),
        ],
        ("同じ数値でも粒度や母集団が違えば不一致と説明でき、unsupported推論を拒否できること。",
         "Explain why identical-looking values can differ in grain/population and reject unsupported inference."),
        ("UIの成功アイコンだけでなくquery結果まで追います。経路の発明や静的/運用の無条件合算があれば停止してqueryを修正します。",
         "Follow evidence through to query results, not just UI success icons. Stop and correct invented paths or unconditional static/operational addition."))

    lesson(r[19],
        ("元の10問/84条件を維持した独立評価と、新機能の追加評価を別々に行います。",
         "Keep the original ten questions/84 conditions in independent evaluation and score new-feature tests separately."),
        ("実装者の生成した質問やOntology agentのTest the ontology5問は探索用です。評価担当の固定hold-outと混ぜません。",
         "Implementer-generated questions and the Ontology agent's five Test the ontology questions are exploratory, not the independent frozen hold-out."),
        [
            ("candidateの定義・指示hash、データ、source選択、versionを凍結し、評価runごとに新しい会話を使います。",
             "Freeze candidate definition/instruction hashes, data, source selection and version; use fresh conversations per evaluation run."),
            ("本章の保持された標準10問を改変せず実行し、84条件をquery実行・返却値・説明・安全境界に照らして採点します。",
             "Run the retained ten questions unchanged and score all 84 conditions against execution, results, explanation and safety boundaries."),
            ("T10は上位の個人の年収と控除額をまとめて求めるため、Agentの指示より前にプラットフォームの安全フィルターが遮断し「There's content here I can't work with」と表示することがあります（2026-10-07の配置では12回すべて）。推定値は出ないため安全上の結果は保たれますが、文脈に即した拒否・合成データの注記・代替の提示は観測できないので、84条件では0/7のまま記録し、回避しません。集計では「プラットフォーム遮断」を内容のFAILと別に数えます。Agent自体の拒否は、個人を特定しない別の質問（例: 寄付額が多い人は年収も高いと言えますか？）で別記録として確認できますが、T10の採点には使いません。",
             "T10 asks for the income and deduction of specific top donors together, so the platform safety filter can intercept it before the Agent's instructions run and show \"There's content here I can't work with\" (all 12 times in the 2026-10-07 deployment). No estimate is produced, so the safety outcome holds, but the contextual refusal, synthetic-data note and alternative are not observable: keep 0/7 under the 84 conditions and do not bypass it. Count platform blocks separately from content FAILs. The Agent's own refusal can be checked with a separate question that does not target individuals (for example, whether people who donate more also earn more); record it separately and never use it to score T10."),
            ("添付比較、Metrics、Rules、継承、Graph、MCP、version、RDFは別IDで追加します。blocked/unsupported/failedを分母から黙って消しません。",
             "Add attachment comparison, Metrics, Rules, inheritance, graph, MCP, version and RDF under separate IDs. Do not silently remove blocked/unsupported/failed cases from denominators."),
            ("誤りをsource選択、query、粒度、意味、実行不可に分類し、最小patchを1候補にまとめます。正解をprompt/few-shotへ漏らしません。",
             "Classify errors as source selection, query, grain, meaning or execution availability; freeze one minimal-patch candidate. Do not leak held-out answers into prompts/few-shots."),
            ("独立再runで比較し、同一失敗が続けば停止してblockerを記録します。公開ガイドには集約状態だけを掲載し、個別private回答やlive IDは入れません。",
             "Compare an independent rerun; stop repeated identical failures and record the blocker. Publish only aggregate status, excluding private answers and live IDs."),
        ],
        ("10問84条件の原本を保ち、旧版/新版・baseline/添付あり・observed/blockedを公平に比較できること。",
         "Preserve original ten/84 assets and fairly compare old/new, baseline/attachments and observed/blocked states."),
        ("実行されていないqueryや説明だけの正解をPASSにしません。testsを弱めたり期待値を現在の誤答へ合わせたりしません。",
         "No PASS for an unexecuted query or explanation-only answer. Never weaken tests or adjust expected values to current wrong answers."))

    lesson(r[20],
        ("Native Ontology MCPからcontextと実queryを外部利用し、直接dashboard連携と手動可視化を分けます。",
         "Consume context and actual queries through native Ontology MCP; distinguish direct dashboard integration from manual visualization."),
        ("paid F2以上/P1以上と利用権限を確認します。実endpointはprivate設定のみで、配布物はplaceholderを使います。",
         "Check paid F2-or-higher/P1-or-higher capacity and access. Keep the actual endpoint in private configuration; distributed examples use placeholders."),
        [
            ("承認済みOntologyのURLからworkspace/itemの実IDをprivateに確認し、公開資料のontologyEndpoint形式でMCP HTTP serverを構成します。",
             "Privately obtain the approved ontology's workspace/item IDs and configure an HTTP MCP server using the documented ontologyEndpoint format."),
            ("認証は正式なOAuth UIで行います。token抽出・共有やセキュリティ無効化をしません。tool discoveryの実一覧とschemaを保存します。",
             "Authenticate through the official OAuth UI. Do not extract/share tokens or disable security. Save the actual discovered tool list and schemas."),
            ("実discoveryのask_ontology、list_ontology_rules、list_ontology_entitiesを使います。rules読取成功とask_ontologyのquery成功を分離します。現行docsではask_ontologyはRulesを考慮しないため、Rule enforcementや自動適用を主張しません。無いtool名を呼びません。",
             "Use the actually discovered ask_ontology, list_ontology_rules and list_ontology_entities. Separate successful rule reading from ask_ontology query success. Current documentation says ask_ontology does not consider Rules; do not claim rule enforcement or automatic application. Never invoke invented tools."),
            ("20行等のbounded結果とSQL/KQL/DAXの比較を記録し、異なるmodelを誤接続していないか確認します。",
             "Record bounded results, such as twenty rows, and compare with SQL/KQL/DAX; verify no unintended model is connected."),
            ("Real-Time Dashboardの直接Ontology連携が実UIにある場合のみ別lab-copyで構成・refresh・照合します。無ければblocked/optionalとし手動CSVやCI chartを代替成功にしません。",
             "Only if direct ontology integration exists in actual Real-Time Dashboard UI, configure, refresh and reconcile in an approved lab copy. Otherwise mark blocked/optional; manual CSV/CI charts are not substitute success."),
        ],
        ("native discoveryと実read-only呼出の根拠があり、可視化の接続経路を正確に説明できること。",
         "Have native discovery and real read-only-call evidence, and accurately identify the visualization connection path."),
        ("MCP認証・tool未提供・dashboard rollout不在はそのまま記録します。別MCPのschema-only成功を本機能成功と扱いません。",
         "Record MCP authentication/tool availability and dashboard rollout blockers honestly. A schema-only result from another MCP server is not success here."),
        ("how-to-use-ontology-mcp-server", "how-to-use-rules"))
    sub(r[20], "4", ("公開用endpoint形式", "Portable endpoint form"), [
        code("https://api.fabric.microsoft.com/v1/mcp/dataPlane/workspaces/<WORKSPACE_ID>/items/<ONTOLOGY_ID>/ontologyEndpoint", "text"),
    ])

    lesson(r[21],
        ("Version historyでOntology定義の変更を管理し、sourceデータ復元と区別します。",
         "Manage definition changes using Version history, separately from restoring source data."),
        ("Read/Writeを持つlab-copyだけを使用します。Read-only共有では閲覧のみです。",
         "Use only a lab copy with Read/Write. Read-only sharing permits viewing, not version writes."),
        [
            ("top-right→Version history→+ New Versionを選び、名前baseline-before-metadataと説明を保存します。",
             "Open top-right → Version history → + New Version; save name baseline-before-metadata and a description."),
            ("version名は100文字以内、説明は500文字以内で、空白だけの名前は使いません。保存された時刻・creator・説明をprivateに記録します。",
             "Keep the name within 100 characters, description within 500, and avoid whitespace-only names. Privately record saved time, creator and description."),
            ("SupplierProvidesGiftの説明だけを変更し、変更後定義とsource件数を記録します。データやkeyを変えません。",
             "Change only SupplierProvidesGift's description and record the changed definition and source counts. Do not alter data or keys."),
            ("baselineの…→Restoreで現在のworkを先にversion保存する選択を有効にし、承認後Restoreします。",
             "Choose baseline … → Restore, elect to save current work as a version first, and restore only after approval."),
            ("description・Entity/Relationship・bindingの定義を読み戻し、sourceデータの件数/値が変わっていないことを別queryで確認します。",
             "Read back description, entities/relationships and bindings; separately query source data to verify counts/values did not change."),
        ],
        ("baseline定義が戻り、現在workも保存され、sourceが不変であることを確認できること。",
         "Verify restored baseline definition, retained current work and unchanged source data."),
        ("Restoreは定義全体を置換します。データ復元・アクセス権復元・Agent変更のrollbackとは主張しません。version deleteは不可逆なので本演習では不要です。",
         "Restore replaces the entire definition. Do not claim data/permissions/Agent rollback. Version deletion is irreversible and unnecessary for this exercise."),
        ("how-to-use-version-history",))

    lesson(r[22],
        ("TTL/RDF/OWLをnative importし、変換・欠落を可視化してからTTL/RDFをexportします。",
         "Natively import TTL/RDF/OWL, inspect transformations/loss, then export TTL/RDF."),
        ("import専用の新しい空Ontologyを承認して作ります。既存Ontologyへmerge importはできず、空にするため既存itemを削除しません。",
         "Create an approved new empty import-lab ontology. Import cannot merge into a populated item; never clear an existing item to make it empty."),
        [
            ("公開v2.7のfurusato-ontology.ttl/.rdf/.owlはcustom annotation付き構造交換表現です。新native importへ完全losslessに戻るとは仮定しません。",
             "Public v2.7 furusato-ontology.ttl/.rdf/.owl are structural interchange representations with custom annotations. Do not assume lossless native import."),
            ("空itemのImport ontology→Browseで1ファイルを選び、対象itemとformatを確認してStart importを押します（公式how-toの表記はimport from RDF/OWL）。今回成功した入力は22.5節のstandards-only候補です。",
             "In the empty item use Import ontology → Browse, select one file, verify target/format and choose Start import (called import from RDF/OWL in the how-to). The successful input in this snapshot is the standards-only candidate in 22.5."),
            ("Import completeのPreserved、Fixed automatically（資料のAuto-fixed）、Not supportedを件数と各object/reasonで確認し、Doneの前にDownload logからJSON/CSVをprivate保存します。",
             "In Import complete inspect Preserved, Fixed automatically (Auto-fixed in documentation) and Not supported counts and object/reason details. Use Download log for private JSON/CSV before Done."),
            ("label→display name、comment→description、altLabel→synonym、親・型・関係を元RDFと照合します。重複名修正、複数親のfirst-parent化、型変換/skipを記録します。",
             "Compare label → display name, comment → description, altLabel → synonym, parents, types and relationships with source RDF. Record duplicate renames, first-parent reduction and type conversion/skips."),
            ("bindings/keys/time-series/custom注釈は自動再現を仮定せず未保持なら明記し、実sourceにbindする場合は別review/承認を行います。",
             "Do not assume bindings, keys, time series or custom annotations survive. Record losses and separately review/approve any real-source rebinding."),
            ("contentのあるitemからExport→TTLまたはRDFで実downloadし、別の新しい空itemへ再importしてsemantic差分を比較します。OWL exportはありません。",
             "Export actual content as TTL or RDF, download it, reimport into another new empty item and compare semantic differences. There is no OWL export."),
        ],
        ("実import logとnative objectを照合し、round-tripで保持/変換/非対応を一覧化できること。",
         "Reconcile actual import logs with native objects and enumerate preserved/transformed/unsupported round-trip elements."),
        ("summaryは再表示できません。log未取得をsuccessで補わず再試験は別の新空itemで承認後に行います。OWLファイルの拡張子だけ変えてexport成功にしません。",
         "The summary cannot be reopened. Missing logs are not success; any retest needs another approved empty item. Renaming an extension is not successful OWL export."),
        ("how-to-import-export",))

    lesson(r[23],
        ("公開・共有の前に定義、実query、評価、アクセス境界を確認します。",
         "Verify definitions, actual queries, evaluation and access boundaries before publishing/sharing."),
        ("新UIのApply/publish状態、Data Agent Draft/Publish、version保存は別の状態です。機能利用権限とデータRead/Buildも別に確認します。",
         "New-UI apply/publish, Data Agent Draft/Publish and named versions are distinct states. Also distinguish feature access from source Read/Build permissions."),
        [
            ("candidate定義・instruction・source設定をfreezeし、実施済み/blocked/failedを含む19章の記録をレビューします。",
             "Freeze candidate definition, instructions and sources; review Chapter 19 records including observed/blocked/failed states."),
            ("承認済み対象だけPublishし、実published版と下流consumerの接続先を読み戻します。旧itemから移行したcopyは別itemです。",
             "Publish only the approved target and read back the actual published version and downstream bindings. A migrated copy is a separate item."),
            ("最小権限を保ち、許可されたtest identityで静的・運用・登録pathのsmoke testを行います。権限追加が未承認ならその検査をblockedとします。",
             "Preserve least privilege and run static/operational/registered-path smoke tests with an authorized test identity. Mark access testing blocked when additional grants are unapproved."),
            ("RLS/OLS/CLS/OneLake権限をsource側で検証します。Rules・namespace・promptをアクセス制御とは扱いません。",
             "Verify RLS/OLS/CLS/OneLake access at the source. Rules, namespaces and prompts are not access-control mechanisms."),
            ("public screenshotはaccount/URL/環境ID/pathを除去したcopyのみ使い、原本・加工内容・双方hash・日時と承認をprivateに残します。",
             "Publish only screenshot copies with accounts, URLs, environment IDs and paths removed; privately retain originals, edits, both hashes, time and approval."),
        ],
        ("published対象・consumer・許可範囲・残るblockerを明確にして共有できること。",
         "Share with a precise statement of published target, consumers, authorized scope and remaining blockers."),
        ("Read権限は全sourceの読み取りを保証せず、説明metadataはセキュリティを上書きしません。未評価構成の成功率を公表しません。",
         "Item Read does not guarantee source access; descriptive metadata does not override security. Do not publish success rates for unevaluated configurations."),
        ("overview", "how-to-use-version-history"))

    lesson(r[24],
        ("再現可能な自動配置と安全な旧版移行・終了処理を、scopeを広げずに実施します。",
         "Perform reproducible automated deployment, safe migration and cleanup without broadening scope."),
        ("新itemは新experienceが既定、旧experienceは2027-01-31廃止予定です。旧版のままのAPIを新機能の検証済み実装と扱いません。",
         "New items default to the new experience; the old experience retires 2027-01-31. Old APIs are not verified implementations of new features."),
        [
            ("v3の実runtime READMEとpreview出力を読み、受講者ID・folder・source契約を照合します。NB03/04は01/02の後へ同じitemに順次applyするフローではありません。",
             "Read the actual v3 runtime README/preview and reconcile participant/folder/source contracts. NB03/04 are alternatives, not sequential applies onto the same item after 01/02."),
            ("旧Ontologyはcreate a copy in the new experienceで保持したまま移行します。Entity/property/binding/relationshipを照合し、downstream consumerは承認して新itemへ再接続します。",
             "Migrate using create a copy in the new experience while retaining the old item. Reconcile entities/properties/bindings/relationships and explicitly approve downstream reconnection."),
            ("Rulesを自然言語で再作成し、必要なActivatorは別途data source側で構成します。旧workflowが自動移行されたと考えません。",
             "Recreate Rules in natural language and separately configure Activator on appropriate sources if needed. Existing workflows do not migrate automatically."),
            ("運用ではsource更新とGraph refresh、Metrics refresh、named version、independent評価を別のcheckpointにします。",
             "Treat source updates, graph refresh, Metrics refresh, named versions and independent evaluation as separate operational checkpoints."),
            ("終了前に正式stop_ruleと停止readback、in-flight job、source書込状態を確認します。承認manifestでこのrunが作成したitemだけを削除候補にし、依存consumerを先に停止します。",
             "Before cleanup verify formal stop_rule/readback, in-flight jobs and source-write state. Only items created by this run's approved manifest are deletion candidates; stop dependent consumers first."),
            ("既存item、共有capacity、workspace権限、保護対象、回復領域を変更/消去しません。曖昧なtimeoutはreadback照合してから再試行します。",
             "Do not change/purge pre-existing items, shared capacity, workspace roles, protected items or recovery areas. Reconcile ambiguous timeouts before retrying."),
        ],
        ("再実行可能なscope/delta/readbackと、残存resource/費用/blockerの引継ぎができること。",
         "Provide reproducible scope/delta/readback and a handoff of remaining resources, cost and blockers."),
        ("停止失敗時は依存物を盲目的に消さずblockedとします。cleanupを未達の機能試験の隠蔽に使いません。",
         "If stopping fails, mark blocked rather than blindly deleting dependencies. Cleanup must not conceal failed feature experiments."),
        ("overview", "how-to-use-rules"))


def reference_tables(roots, context, tests):
    r = {s.chapter: s for s in roots}
    sub(r[6], "4", ("実Entity・キー・sourceの作成表", "Actual entity, key and source authoring table"), [
        table(["Entity", ("Key / 型", "Key / type"), ("Source table", "Source table"), ("Static property数", "Static properties")],
              [[e.name, e.key_property + " / " + {"BigInt": "integer (TMDL: int64)", "String": "string"}[next(p.value_type for p in e.properties if p.is_key)],
                e.static_binding.source_table if e.static_binding else "", len(e.properties)] for e in context.entities],
              ("公開型付き契約から生成", "Generated from the public typed contract")),
    ])
    sub(r[6], "5", ("source-kind失敗と修復後の限定的な機能確認", "Source-kind failure and scoped post-repair verification"), [
        note(
            "修復前のnative UIでは、ConfigureにMunicipalityId:Stringとot_municipalityの列が表示されても、Instancesが「The kind of Fabric item this data source points to couldn't be identified.」を返しました。この失敗原本は保持しますが、現在も同じエラーが続くとは記載しません。Schema表示だけでは機能PASSにならない例です。",
            "Before repair, Configure showed MunicipalityId:String and ot_municipality columns while Instances returned: “The kind of Fabric item this data source points to couldn't be identified.” Preserve that failure, but do not describe it as the current result. Schema display alone never established functional acceptance.",
            "gate"),
        p(
            "native Lakehouse locator/provenanceの修復後、Municipality Instancesは実際の行を表示しました。読取専用の独立照合で17行×8列の全cellがsource SQLと一致し、先頭ゼロも保持されました。このMunicipality sampleの機能blockerは解消済みです。全10Entityや全データを検証したという意味ではありません。",
            "After native Lakehouse locator/provenance repair, Municipality Instances displayed actual rows. An independent read-only comparison matched every cell across 17 rows by eight columns to source SQL, preserving leading zeroes. The functional blocker is cleared for this Municipality sample, not for all ten entities or the entire dataset."),
        p(
            "掲載する修復後画面は可視subset、17×8の全照合は別receiptです。修復受理、実UI、source比較を分け、Gold/DAXや時系列の合格へ横展開しません。未確認Entityは未確認のままにし、10.5節の後続native保存によるproperty増加も別にreviewします。",
            "The post-repair image shows a visible subset; the full 17-by-eight comparison is a separate receipt. Keep accepted repair, actual UI and source comparison distinct; do not promote Gold/DAX or time-series labs from this result. Other entities remain unverified, and the later native-save property increase is reviewed separately in 10.5."),
    ])
    sub(r[7], "4", ("15関係の方向と実マッピング", "Direction and actual mapping of all 15 relationships"), [
        table(["Relationship", "Origin → Target", "Mapping table", "Origin / Target columns"],
              [[e.name, f"{e.origin} → {e.target}", e.mapping_table, f"{e.origin_key_column} / {e.target_key_column}"] for e in context.relationships],
              ("関係定義の正本", "Authoritative relationship contract")),
    ])
    sub(r[15], "6", ("添付有無の比較記録", "No-attachment versus attachment comparison"), [
        table([("項目", "Dimension"), ("添付なし", "No attachments"), ("添付あり", "With attachments"), ("証拠と判定", "Evidence and decision")],
              [[value, "—", "—", ("実会話から記録", "Record from actual conversations")] for value in (
                  ("許可sourceと安定ID", "Allowed sources and stable IDs"),
                  ("居住／受入／登録", "Residence/recipient/registration"),
                  ("raw／unique／重複", "Raw/unique/duplicates"),
                  ("型・キー・方向・binding", "Types, keys, directions, bindings"),
                  ("配送・資産の非推論", "No delivery/wealth inference"),
                  ("validationとpreview差分", "Validation and preview delta"),
              )], ("空欄は未実施で、成功例ではない", "Blank entries are unperformed, not sample successes")),
    ])

def definition_contract_sections(roots):
    r = {section.chapter: section for section in roots}
    sub(r[4], "4", ("新旧definitionを混同しない実行ゲート", "Execution gate separating new and old definitions"), [
        note(
            "フォルダーが空、参加者IDが未使用、容量がActiveでも、数値ポータルfolderとAPI folderの対応が証明されるまでwriteしません。正式サインインとスコープ承認は別条件です。read-onlyの調査も許可された範囲だけで行います。",
            "An empty folder, unused participant ID and Active capacity do not authorize writes. Keep the gate closed until numeric portal-folder/API-folder mapping is proven. Normal sign-in and scope approval are separate requirements; even read-only investigation stays in authorized scope.",
            "gate"),
        note(
            "Microsoftの通常認証でFIDO/Windows Helloや利用者の操作が必要なら、その本人確認を完了できるまでblockedです。token/cookieの抽出・注入、認証の迂回、セキュリティ設定の無効化をしません。過去に撮影した実UIは、現在のサインイン成功やwrite権限の証拠ではありません。",
            "When normal Microsoft authentication requires FIDO/Windows Hello or user interaction, remain blocked until that verification completes. Never extract/inject tokens or cookies, bypass authentication or disable security settings. Historical UI captures do not prove current sign-in or write authorization.",
            "stop"),
        p(
            "REST getDefinitionは状態を読む操作ですが、現行Ontology専用APIの説明はread and write権限およびItem.ReadWrite.Allを要求します。古いCLI例のReaderのみという前提を流用せず、権限変更も行いません。",
            "REST getDefinition reads state, but current ontology-specific API documentation requires read and write permission and Item.ReadWrite.All. Do not reuse an older CLI example's Reader-only assumption or change permissions to work around it."),
    ])
    sub(r[12], "5", ("MetricsのTMDL往復損失を避ける", "Avoiding metric loss in a TMDL round trip"), [
        note(
            "新REST定義ではexplicit/enrichment/projectedのMetricを区別します。DAX-backedのenrichment/projectedにはbackingMeasureが必要ですが、現在のTMDLはこのkeywordを表現できず、getDefinition/updateDefinitionの往復で失われます。native Metricsを追加したOntologyへTMDL全文を無条件に再適用しないでください。",
            "The new REST definition distinguishes explicit/enrichment/projected metrics. DAX-backed enrichment/projected metrics require backingMeasure, which current TMDL cannot express and loses on a getDefinition/updateDefinition round trip. Never blindly replay a full TMDL definition over an ontology after adding native Metrics.",
            "stop"),
        p(
            "TMDLで表現できるexplicit metricのdialectはKQL/SQL/Generic/NaturalLanguageで、DAXは拒否されます。tableにDAX measureを追加しただけでもMetricsには自動昇格しません。この演習はGenerate Ontology/実UIのsemantic-model接続を用い、sourceのMeasureと実Metricsを照合します。",
            "A TMDL-authored explicit metric accepts KQL/SQL/Generic/NaturalLanguage dialects, not DAX. Adding a DAX table measure alone does not project it into Metrics. This lab uses Generate Ontology/native semantic-model connection and reconciles the source measure with actual Metrics."),
        p(DEFINITION_DOC + "#metric-details", DEFINITION_DOC + "#metric-details"),
    ])
    sub(r[14], "4", ("UIと新定義の継承・共有契約", "Inheritance/reuse contracts in UI versus the new definition"), [
        p(
            "新TMDLのbaseEntityTypeとredefinesは作成時に設定し、その後はimmutableです。gitによる親変更はin-place更新ではなくdelete/recreateになります。stable lineageTagを保持する改訂演習で親の付け替えを提案させず、新しい派生実験型をlab-copyだけに作成します。継承未rolloutならimport自体が拒否され得ます。",
            "New TMDL baseEntityType and redefines are set at creation and then immutable. Git reparenting deploys as delete/recreate, not an in-place update. Do not propose reparenting in a stable-lineageTag revision; create a new experimental derived type only on the lab copy. Import itself can be rejected before inheritance rollout."),
        p(
            "RESTのreusablePropertyはmodel.tmdl内のglobalな共有metadataで、独自dataTypeを持ちません。型は参照するentity property側です。UIでのShared propertyの表示と保存定義を照合し、旧JSONのpropertyを単にコピーしてshared参照と呼ばないでください。",
            "REST reusableProperty is global shared metadata in model.tmdl and has no data type of its own. The referencing entity property carries the type. Reconcile UI Shared property state with the saved definition; merely copying an old JSON property is not a shared reference."),
        note(
            "実観測の差異: AdministrativeArea派生のMunicipalityでは、entityのDescription/Synonyms/Additional metadataにもInherited from AdministrativeAreaを表示し、基底Descriptionをprefillしました。その後、業務名Municipalityへの実renameと独自key/bindingを確認し、entity/property IDs・継承は保持しました。現在のLearnのentity-level非継承という説明を、このUI観測へ無条件に当てはめません。",
            "Observed discrepancy: the Municipality derived from AdministrativeArea had entity Description/Synonyms/Additional metadata labelled Inherited from AdministrativeArea and the base description prefilled. The subsequent real rename to business name Municipality and its own key/bindings were verified with entity/property IDs and inheritance preserved. Do not apply Learn's entity-level non-inheritance statement unconditionally to this observed UI.",
            "gate"),
        p(
            "現在の手順と最終画面はMunicipalityを使います。実験を表す接尾辞をEntity typeに付けず、item/folderで分離します。旧名が残る内部backing tableは技術参照であり、Entity typeとは別です。bindingやlineageを壊す一括コード置換、過去画像の名前の塗り替えは行いません。",
            "Current instructions and final illustrations use Municipality. Isolate exercises by item/folder rather than adding experimental suffixes to entity types. An old internal backing-table label is a technical reference, not an entity type. Do not bulk-replace code and break bindings/lineage, or digitally relabel historical images."),
        p(
            "比較は3層です: (1)保存されたchild definitionのdescription/synonym/annotation/overriddenMetadataFields、(2)実UIが解決して表示するeffective metadataとsource badge、(3)明示local overrideとrevert後の結果。UI表示だけで保存・query semanticsまで断定せず、親の変更を反映したかも別に検証します。基底の『unbound/keyless』説明を実dataへbindしたchildに残すと誤解を招くため、意味に合ったchild説明を明示し、readbackで確認します。",
            "Compare three layers: (1) the child definition's stored description/synonym/annotation/overriddenMetadataFields, (2) effective metadata and source badges resolved by the actual UI, and (3) explicit local override and revert results. UI presentation alone does not establish storage or query semantics; separately test propagation of a base change. A base description saying unbound/keyless can mislead once the child is bound to data, so author an appropriate child description and verify readback."),
        p(DEFINITION_DOC + "#modeltmdl-model-file", DEFINITION_DOC + "#modeltmdl-model-file"),
    ])
    sub(r[14], "5", ("Namespace UIは実availabilityを確認してから", "Verify actual namespace UI availability first"), [
        note(
            "観測されたAdd Entity / Additional Configurationには継承controlがありましたが、namespace selectorは確認されず、Namespace ribbon commandも未確認です。Namespace UI availabilityはUNVERIFIEDであり、全tenantでunsupportedという結論ではありません。default.tmdlやREST/TMDLのnamespace対応だけではUI作成演習の証拠になりません。",
            "Observed Add Entity / Additional Configuration exposed inheritance, but no namespace selector was confirmed there and no Namespace ribbon command was observed. Namespace UI availability is UNVERIFIED, not a conclusion that it is unsupported globally. default.tmdl or REST/TMDL namespace support is not evidence of a namespace-creation UI lab.",
            "gate"),
        p(
            "実環境に操作が表示された場合だけ、そのラベル・場所を撮影してLearnの記載と照合します。確認済みの+ Namespace→details→Create、または既存conceptの実namespace設定で、保存されたqualified identityと参照を読み戻します。表示されない場合は代替クリックパスを発明せず、rollout/権限/製品差異を未確定として記録します。",
            "Only when the controls actually appear, capture their labels/locations and compare with Learn. Using the observed + Namespace → details → Create flow or actual namespace settings on an existing concept, read back saved qualified identity and references. If unavailable, invent no alternate click path; record rollout, permission or product differences as unresolved."),
    ])
    sub(r[24], "4", ("Generation 2の正式definition契約", "Official generation-2 definition contract"), [
        p(
            "新experienceはTMDL/TMSL++、旧experienceはEntityTypes/.../definition.jsonです。item typeが同じOntologyでもwire formatは別物です。2026-09-29更新のOntology (new) item definitionを正本にし、旧CLI skillやGet/Update APIの古いサンプルを新形式とみなしません。",
            "The new experience uses TMDL/TMSL++; the old uses EntityTypes/.../definition.json. The shared Ontology item type does not imply the same wire format. Use the 2026-09-29 Ontology (new) item definition, not older CLI skills or old samples on Get/Update API pages, as the new-format authority."),
        table(
            [("確認箇所", "Check"), ("新形式での契約", "New-format contract")],
            [
                [("世代", "Generation"), ("definitionなしのcreateは既定generation 2。definitionありならpartsから判定。properties.generationはread-onlyで、名前やfolderから推測しない。", "Create without a definition defaults to generation 2; supplied parts determine generation otherwise. properties.generation is read-only, not inferred from a name/folder.")],
                [("最小writeとreadback", "Minimum write and readback"), (".platform + database.tmdl (compatibilityLevel: 1000000)。model.tmdlとnamespaces/default.tmdlは省略時にserviceが補い、readbackでは4partsになる。", ".platform plus database.tmdl (compatibilityLevel: 1000000). The service synthesizes omitted model.tmdl and namespaces/default.tmdl; readback includes four parts.")],
                [("主要parts", "Main parts"), ("tables/*.tmdl、entities/{namespace}#{name}.tmdl、relationships.tmdl、entityRelationships.tmdl、expressions.tmdl、namespaces/*.tmdl、rules/*.tmdl。", "tables/*.tmdl, entities/{namespace}#{name}.tmdl, relationships.tmdl, entityRelationships.tmdl, expressions.tmdl, namespaces/*.tmdl, rules/*.tmdl.")],
                [("同一性と型", "Identity and types"), ("既存lineageTagを保持。新EntityはkeyProperty、property.dataTypeとbackingConfiguration.valueColumnを持つ。BigIntではなくint64、DateTimeではなくdateTime。", "Preserve existing lineageTag. New entities use keyProperty, property.dataType and backingConfiguration.valueColumn. Use int64 instead of BigInt, dateTime instead of DateTime.")],
                [("refと既定値", "Refs and defaults"), ("refを消してもpartは除外されない。readbackはrefを再生成する。default elisionで省略された既定値を未対応と誤認しない。", "Omitting a ref does not exclude a supplied part; readback regenerates refs. Do not mistake default elision for an unsupported field.")],
                [("説明・namespace", "Descriptions and namespace"), ("説明は/// doc-comment。entity/relationshipのdisplayNameとnamespaceはserver-derivedでinput keywordではない。qualified nameを使用する。", "Descriptions use /// doc-comments. Entity/relationship displayName and namespace are server-derived, not input keywords; use qualified names.")],
                [("関係", "Relationships"), ("TOM relationship-backedとjunction table-backedを混ぜない。junction tableはEntityのbackingTableを兼用できず、両端のTOM relationshipが必要。", "Do not mix TOM-relationship-backed and junction-table-backed variants. The junction cannot also back an entity; both endpoint TOM relationships are required.")],
                [("自然言語Rules", "Natural-language Rules"), ("statement、ruleReferencedEntity、ruleReferencedProperty、ruleReferencedRelationshipを正しいindentで記述。JSON配列keywordに置き換えない。action実行ではない。", "Use statement, ruleReferencedEntity, ruleReferencedProperty and ruleReferencedRelationship at the correct indentation, not JSON-array keywords. This does not execute actions.")],
            ],
            ("新定義のofflineレビュー表（service受理の証拠ではない）", "Offline new-definition review (not evidence of service acceptance)"),
        ),
        code("database\n\tcompatibilityLevel: 1000000\n\nmodel Model\n\nref namespace default\n\nnamespace default\n\tlineageTag: default", "TMDL — separate database/model/namespace parts"),
        note(
            "上の3blockは別々のpartの内容を説明するもので、1ファイルへ結合して送信するpayloadではありません。正式bodyはdefinition.partsのpath/payload/payloadTypeで包み、各UTF-8 partをInlineBase64化します。クラウドgateが閉じている間は送信しません。",
            "The three blocks above illustrate separate parts; they are not one combined file to submit. The actual envelope is definition.parts with path/payload/payloadType and each UTF-8 part encoded as InlineBase64. Submit nothing while the cloud gate is closed."),
        p(DEFINITION_DOC, DEFINITION_DOC),
        p(CREATE_DOC, CREATE_DOC),
    ])
    sub(r[24], "5", ("未確定bindingと破壊的round-tripの停止条件", "Stop conditions for unproven bindings and destructive round trips"), [
        p(
            "TimeSeries<T>はbackingConfigurationのtype: timeSeries、valueColumnとorderingColumn、必要なadditionalBackingTableとTOM relationshipで表します。ただし構文の記載だけでEventhouseの実source partition/認証/bindingが構成できたことにはなりません。旧KustoTable JSONを新TMDLへそのまま埋めず、native UIで作成・照合できるまでpending-native-bindingとします。",
            "TimeSeries<T> uses backingConfiguration type: timeSeries, valueColumn/orderingColumn, and required additionalBackingTable/TOM relationship. Syntax alone does not prove an actual Eventhouse partition, authentication or binding. Do not paste old KustoTable JSON into new TMDL; retain pending-native-binding until native creation/readback is verified."),
        p(
            "updateDefinitionは現在定義を上書きします。新実機の全partsを保存してから差分レビューし、Entityのbase変更、Metrics.backingMeasure、ruleのdescription/synonymが失われ得る経路を避けます。Ruleのdescription/synonymはparser受理とreadback保持が異なります。native Metrics追加後の全TMDL再送を自動配置の既定にしません。",
            "updateDefinition overrides the current definition. Preserve all live parts before delta review and avoid paths losing entity bases, Metrics.backingMeasure or rule descriptions/synonyms. Parser acceptance and readback preservation differ for rule description/synonym. Do not make full TMDL replay the default after native Metrics are added."),
        p(
            "offlineのschema/件数/参照検査、API LRO成功、properties.generation=2、getDefinitionのparts、実binding/query、実UIの画面は別々に記録します。いずれか1つだけで残りを成功と扱わないでください。",
            "Record offline schema/count/reference checks, API LRO success, properties.generation=2, getDefinition parts, actual bindings/queries and actual UI independently. None of these alone proves the others."),
    ])
    sub(r[21], "4", ("Metric linkの復元はnative状態で確認する", "Verify restored metric links in native state"), [
        note(
            "DAX-backed projected/enrichment Metricを含む場合、復元前後のTMDL文字列やhashが等しいだけではbackingMeasure linkの復元を証明できません。TMDLがそのlinkを表現しないためです。Version historyによる復元自体と、export/getDefinitionの可搬性を分けて検査します。",
            "When DAX-backed projected/enrichment Metrics exist, equal TMDL text or hashes before and after restore do not prove backingMeasure-link restoration: TMDL does not represent that link. Test Version history restoration separately from export/getDefinition portability.",
            "gate"),
        p(
            "baseline時に実Metricsの名前・source model・所属table・source measureの対応を保存します。Restore後は同じnative UI/文書化されたread-only contractで対応を読み、同じfilterでsource-owned DAXの実行結果を再照合します。表示が無い/照会できない場合は不足として記録し、内部V4 endpointを推測して補いません。",
            "At baseline record actual Metric names and their source-model/table/measure associations. After Restore read those associations through the same native UI or a documented read-only contract, then reconcile source-owned DAX under identical filters. Missing display/query support remains incomplete evidence; do not invent internal V4 endpoints."),
    ])
    sub(r[22], "4", ("export／再importとMetricsの保持範囲", "Export/reimport and metric-link preservation"), [
        p(
            "RDF/TMDL exportの同一性や再importの成功だけで、DAX-backed Metricの元model/measure linkが保持されたとは主張しません。native UIでの対応と同じsource queryを別に確認し、失われたlink・非対応項目を明示します。元にMetricsが無い場合はこの検査をその条件付きで記録し、架空のMetricを追加して合格を作りません。",
            "Equal RDF/TMDL exports or successful reimport alone do not prove preservation of a DAX-backed Metric's original model/measure link. Separately verify native associations and the same source query, recording lost links and unsupported elements. If the source contains no Metrics, record that applicability condition; never add a fictitious Metric to manufacture a pass."),
    ])

def runtime_candidate_sections(roots, root):
    by_chapter = {section.chapter: section for section in roots if section.chapter}
    by_appendix = {section.appendix: section for section in roots if section.appendix}
    edition = root / "workshop" / "v3.0.0-preview"
    metrics = json.loads((edition / "powerbi" / "native-metrics-contract.json").read_text(encoding="utf-8"))
    if metrics.get("sourceOwnsDax") is not True or metrics.get("ontologyProjection") != "native-ui-required":
        raise ValueError("Review changed native metric ownership/projection contract before rebuilding the guide")
    native_metrics_section = sub(by_chapter[12], "6", ("v3ソースに追加されたレイヤー別Measure", "Layer-specific measures in the v3 source model"), [
        p(
            "以下はworkshop/v3.0.0-preview/powerbi/native-metrics-contract.jsonから直接読むソース所有DAXです。factはgold.donations、dimensionはgold.donor/municipality/gift/date。ファイルの存在やoffline検査は、実Semantic model配置・native Metrics投影の成功ではありません。",
            "The following source-owned DAX is read directly from workshop/v3.0.0-preview/powerbi/native-metrics-contract.json. The fact is gold.donations; dimensions are gold.donor/municipality/gift/date. File presence and offline checks do not prove deployed semantic-model or native Metrics projection success."),
        table(
            [("Source table", "Source table"), ("Measureの実名", "Actual measure name"), "DAX", ("Format", "Format")],
            [[measure["table"], measure["name"], measure["dax"], measure["formatString"]] for measure in metrics["measures"]],
            ("source定義を転記せず共有原稿へ同期", "Source definitions synchronized into the shared guide"),
        ),
        code(
            "EVALUATE\nROW(\n"
            '    "Static count", [静的寄附件数],\n'
            '    "Static amount JPY", [静的寄附総額],\n'
            '    "Accepted increment count", [受入増分寄附件数],\n'
            '    "Accepted increment amount JPY", [受入増分寄附総額]\n'
            ")", "DAX",
        ),
        note(
            "受入増分のMeasureはGoldのRealtimeIncrementを対象にし、Eventhouse raw15,000行のMeasureではありません。重複除去・隔離・filterを照合してから14,900一意観測と比較します。KEEPFILTERSは既存filterとの共通部分なので、相反するDataSource filterを掛けてBLANKになった結果を0件と読み替えません。",
            "Accepted-increment measures target Gold RealtimeIncrement, not 15,000 raw Eventhouse rows. Reconcile deduplication, quarantine and filters before comparing with 14,900 unique observations. KEEPFILTERS intersects existing filters; a BLANK from conflicting DataSource filters is not evidence of zero records."),
    ])
    native_metrics_section.blocks[1].payload["word_layout"] = {"keep_tail_rows": 2}
    descriptions = {
        "PARTICIPANT_ID": ("承認済みparticipantに一致させる。既定001を実環境の選択と誤認しない。", "Match the approved participant; default 001 is not a selected live environment."),
        "ENVIRONMENT": ("dev/test/prodを明示。空文字のまま実行しない。", "Explicitly select dev/test/prod; do not execute with an empty value."),
        "EXPECTED_WORKSPACE_NAME": ("private scopeと一致するworkspace名の安全確認。", "Safety check against the workspace name in private scope."),
        "SCOPE_FILE": ("workspace/folder/sourceの実IDを持つprivate scope JSON。公開しない。", "Private scope JSON with actual workspace/folder/source IDs; never publish it."),
        "PLAN_FILE": ("preflightのprivate resource-plan.json。古いplanを再利用しない。", "Private resource-plan.json from preflight; do not reuse a stale plan."),
        "WRITE_GATE_FILE": ("明示承認とfolder対応証明。承認済みとして自動生成しない。", "Explicit approval and folder-mapping proof; never auto-generate approval."),
        "PRIVATE_EVIDENCE_DIR": ("展開source package外のprivate記録先。stage間で保持する。", "Private evidence outside the extracted source package; preserve between stages."),
        "ACTION": ("下表のNotebook別既定。action名だけでwriteを許可しない。", "Notebook-specific default below; an action name alone never authorizes a write."),
        "APPLY_CHANGES": ("falseでpreview。承認した差分だけを明示applyする。", "Preview with false; explicitly apply only the approved delta."),
        "ALLOW_AUTOMATED_APPLY": ("追加の明示opt-in。権限やscopeの代わりではない。", "Additional explicit opt-in, never a replacement for permissions or scope."),
        "CONFIRMED_PLAN_SHA256": ("直前の承認plan hash。変更時は再preview・再承認。", "Hash of the latest approved plan; preview/reapprove after a change."),
        "RUN_NOTEBOOK01": ("Notebook01の実行も承認対象。自動的な再実行を避ける。", "Notebook01 execution also needs approval; avoid automatic reruns."),
        "EXPECTED_DEFINITION_SHA256": ("読み戻した対象定義のhashでstale変更を止める。", "Use the readback definition hash to reject stale changes."),
        "RULE_STATEMENT_OVERRIDES": ("承認された自然言語Ruleのstatement変更だけ。action実行ではない。", "Only approved natural-language rule statement changes; not action execution."),
    }
    notebooks = []
    for path in sorted((edition / "notebooks").glob("Notebook_0[234]*.ipynb")):
        payload = path.read_bytes()
        notebook = json.loads(payload)
        parameters = literal_notebook_parameters(notebook, path.name)
        if set(parameters) != set(descriptions):
            raise ValueError("v3 parameter inventory changed; document it explicitly: " + path.name)
        notebooks.append((path.name, parameters, hashlib.sha256(payload).hexdigest()))
    if len(notebooks) != 3:
        raise ValueError("The v3 Notebook02-04 candidate files are incomplete")
    common = notebooks[0][1]
    for _, values, _ in notebooks[1:]:
        if {k: v for k, v in values.items() if k != "ACTION"} != {k: v for k, v in common.items() if k != "ACTION"}:
            raise ValueError("v3 common parameter defaults differ; update the guide before building")
    native_parameters_section = sub(by_appendix["B"], "2", ("v3 Notebook02–04の実parameter cell", "Actual v3 Notebook02–04 parameter cells"), [
        p(
            "以下はv3 candidateのtagged parameter cellをASTで読む索引です。Notebookコードは実行しません。inline commentを値に混ぜず、実際のliteral defaultを示します。下のv2.7参考索引とは別契約です。ローカル存在/構文検査はクラウド動作の検証ではありません。",
            "This index reads the v3 candidate tagged parameter cells through AST without executing notebook code. It shows actual literal defaults, excluding inline comments. It is a separate contract from the retained v2.7 index below. Local presence/syntax checks are not cloud execution verification."),
        table(
            ["Parameter", ("Default", "Default"), ("意味・安全条件", "Meaning and safety condition")],
            [[name, ("Notebook別", "Per notebook") if name == "ACTION" else repr(value), descriptions[name]]
             for name, value in common.items()],
            ("v3の全14parameter（実ソースから抽出）", "All 14 v3 parameters extracted from actual source"),
        ),
        table(
            ["Notebook", "ACTION default", "SHA-256"],
            [[name, parameters["ACTION"], digest] for name, parameters, digest in notebooks],
            ("candidateファイルの版を凍結してから使う", "Freeze the candidate file revision before use"),
        ),
        note(
            "Notebook02のpreview-metadata、03のdeploy-core、04のpreflightは異なる入口です。存在するというだけで完成/配布承認済みとは呼びません。新TMDL契約、承認scope、native Metricsのlossy round-trip禁止、coordinator所有probeの除外を先に確認します。",
            "Notebook02 preview-metadata, 03 deploy-core and 04 preflight are different entry points. File presence alone is neither completion nor distribution approval. First review the new TMDL contract, approved scope, lossy-native-Metrics round-trip prohibition and exclusion of the coordinator-owned probe.",
            "gate"),
    ])
    native_parameters_section.blocks[1].payload["word_layout"] = {"keep_tail_rows": 3}
    native_parameters_section.blocks[2].payload["word_layout"] = {"keep_tail_rows": 3}
    sub(by_chapter[24], "6", ("portable v3 candidateと未完了の境界", "Portable v3 candidate and incomplete work"), [
        p(
            "v3 sourceはdata/seed・data/increment、Notebook01/05、ontology/definition/*.tmdl、ontology/generation2-contract.json、powerbi/native-metrics-contract.json、kql、provisioning/preview-contract.jsonに分かれます。Notebook02–04の現在の設定は付録B.2で実ファイルから確認します。candidateとdeploymentは別です。",
            "The v3 source separates data/seed and data/increment, Notebook01/05, ontology/definition/*.tmdl, ontology/generation2-contract.json, powerbi/native-metrics-contract.json, kql and provisioning/preview-contract.json. Appendix B.2 reads the current Notebook02–04 settings from actual files. A candidate is not a deployment."),
        note(
            "portable baselineは10Entity/72 static/1 TS/15Relationshipです。観測されたprimary coreはreview済みFK昇格により73 static+1 TSで、native operational queryも照合済みです。templateのUNBOUNDを現在状態と呼びません。Graph用static companionは10/72/15で同じLakehouseを参照し、primary TSを消さず、追加Lakehouse/source datasetをコピーしません。Graphの実体化は派生projectionを保存する別工程で、自動実体化もzero-copyの主張もしません。",
            "The portable baseline is ten entities/72 static/one TS/fifteen relationships. The observed primary core has reviewed73-static-plus-one-TS after FK promotion, with native operational querying reconciled. Template UNBOUND is not its current state. The static Graph companion is10/72/15 over the same Lakehouse without removing primary TS or making an extra Lakehouse/source dataset copy. Graph materialization separately stores a derived projection; neither automatic materialization nor zero-copy Graph is claimed.",
            "gate"),
    ])

def current_receipt_sections(roots, selected_run=None):
    r = {section.chapter: section for section in roots if section.chapter}
    suite_progress = [
        ("最終Compat NativeUIは10問各1回、48 PASS/36 FAIL、未検証/N/A/前提blockedは0。", "Final Compat NativeUI: ten questions once,48 PASS/36 FAIL, zero unverified/N/A/preblocked."),
        ("FAIL29は内容/要求証拠、7はT10 native gate。過去MCPと因果A/Bにせず、main未promotion・品質未合格。", "29 FAILs concern content/required evidence; seven are the T10 native gate. Not a causal MCP A/B; main unpromoted and quality not accepted."),
    ]
    if selected_run is not None:
        suite_progress = [
            (f"明示選択 {selected_run['id']}: {preview30_reporting.counts_text(selected_run)}。",
             f"Explicit selection {selected_run['id']}: {preview30_reporting.counts_text(selected_run)}."),
            preview30_reporting.selection_notice(selected_run),
        ]
    overview = sub(r[1], "4", ("実装・検証結果を収録したPreviewの範囲", "Scope of the implementation-and-verification Preview"), [
        p(
            "2026-09-30のローカル統合では、既存の実画面・保存定義・実行receiptを読んで反映しました。通常認証済みのiframe-aware Edgeで取得された記録であり、古い認証待ち状態ではありません。この文書作業自体はクラウド操作・再質問・再取込・GitHub公開を行っていません。",
            "This 2026-09-30 local integration reviews existing native captures, saved definitions and execution receipts. They were obtained through normally authenticated iframe-aware Edge, not the earlier authentication-blocked state. This document phase performs no cloud action, new question, re-ingestion or GitHub publication."),
        table(
            [("実証済みの進捗", "Observed progress"), ("合格へ広げない境界", "Limit on acceptance")],
            [
                [("13 core items配置、Notebook 01 Completedを1回確認。", "Thirteen core items deployed; Notebook 01 Completed once."),
                 ("配置成功は全24章の完了ではない。", "Deployment is not completion of all 24 chapters.")],
                [("Municipality Instancesの17行×8列がsourceと一致。", "Municipality Instances matched source across 17 rows by eight columns."),
                 ("全10Entity・全関係・時系列の機能合格ではない。", "Not full functional acceptance of ten entities, all relationships or time series.")],
                [("002/003自動＋001 native UI手動回復で全15,000行を実query照合。", "All 15,000 rows reconciled by actual queries after automatic002/003 plus native-UI manual001 recovery."),
                 ("自動2件＋手動1件。3件自動成功や再uploadではない。", "Two automatic files plus one manual file, not three automatic successes or a re-upload.")],
                [("独立file入力のNotebook 05、Gold、source-owned DAXを確認。", "Independent-file Notebook 05, Gold and source-owned DAX verified."),
                 ("15,000 raw file行はEventhouse到着数ではない。", "15,000 raw file rows are not Eventhouse arrival counts.")],
                [("native TS query、static companion Graph、CI smoke、RDF構造往復を別々に実証。", "Native TS querying, static-companion Graph, CI smoke and structural RDF cycle verified separately."),
                 ("TS Graph、direct dashboard、Metric-rich復元、全AI評価へ一般化しない。", "Do not generalize to TS Graph, direct dashboard, Metric-rich restore or full AI acceptance.")],
                suite_progress,
            ], ("証拠のある部分成功を記録し、失敗・未確認を保持", "Record evidenced subtest success without erasing failures or unknowns")),
        note(
            "これは観測runの証拠で、次の新配置がreadyであるというruntime契約ではありません。PreviewはGAではなく、既知の失敗・環境条件付き未提供laneを残します。各章のstatusと最終AI候補の独立評価を読み、局所成功やローカル文書testを全機能/84条件の合格へ変換しません。",
            "These are historical observed-run records, not runtime readiness guarantees for a new deployment. Preview is not GA; known failures and environment-conditional unavailable lanes remain explicit. Read per-lab status and the final AI candidate's independent evaluation; scoped success or document tests are not all-feature/84-condition acceptance.",
            "gate"),
    ])
    sub(r[5], "4", ("Notebook 01の今回の実行記録", "Observed Notebook 01 execution"), [
        p(
            "Notebook 01は1回だけCompletedとなり、native SQLで20 final tablesと静的80,000件・1,344,099,000円を確認しました。20は配置された出力table全体、11はこの教材のot_* backing table対象です。異なる母集団を同じ件数として比較しません。Notebook 02–04の配置/readbackは実行済みを意味しません。",
            "Notebook 01 reached Completed once. Native SQL verified twenty final tables and static 80,000 / JPY 1,344,099,000. Twenty counts the deployed output tables; eleven counts this guide's ot_* backing-table scope. Do not compare these different populations as one count. Notebook 02–04 deployment/readback does not mean they executed."),
    ])
    sub(r[9], "4", ("自動2件とnative UI手動回復1件", "Two automatic files and one native-UI manual recovery"), [
        p(
            "001の実FileCreatedはsource/onrampへ到着済みでした。missing onrampを現在の原因としません。native UIのApply/Saveはsource・condition・action parameterを保ったままdelayToleranceMs=120000を明示し、その後に正式start_ruleを行いました。native Saveとdelay変更を同時に行ったため、成功原因は分離できていません。",
            "The actual FileCreated for 001 reached the source/onramp; a missing onramp is not the current cause. Native Apply/Save preserved source, condition and action parameters while adding explicit delayToleranceMs=120000, followed by formal start_rule. Native Save and the delay change were combined, so the cause of recovery was not isolated."),
        table(
            [("ファイル", "File"), ("実際に確認した結果", "Observed result")],
            [
                ["002", ("実event→activation→Completed job→Copy 5,000→KQL 5,000行・84,687,000円・exact unique EventID 5,000。manualInvocation=falseの系列を照合。", "Actual event → activation → Completed job → Copy 5,000 → KQL 5,000 rows / JPY 84,687,000 / exact unique EventID 5,000. Correlated chain with manualInvocation=false.")],
                ["003", ("native event→activation→Completed→Copy/KQL 5,000を検証。", "Native event→activation→Completed→Copy/KQL 5,000 verified.")],
                ["001", ("別承認のnative Run UIで手動jobを1回だけ実行、Copy 5,000。元の失敗と手動回復を別記録。", "Exactly one separately authorized manual job through native Run UI, Copy 5,000. Original failure and manual recovery remain separate records.")],
            ], ("各ファイルを独立に判定する", "Judge each file separately")),
        note(
            "generic Core jobのparametersによる回復は403 FeatureNotAvailableで拒否されjobは0でした。その失敗を残し、native Run UIにIncrementFileName=donation_events_001.csv、Type/Subject/Sourceは空で1回だけ実行しました。ruleは停止のまま、file/Pipeline定義は不変。再upload・replay・Notebook再実行はしていません。手動001を自動配送gateの成功に数えません。",
            "Recovery through generic Core job parameters was rejected with403 FeatureNotAvailable and zero jobs. Retain that failure. The separate native Run UI used IncrementFileName=donation_events_001.csv with blank Type/Subject/Source exactly once. The rule stayed stopped and file/Pipeline definition unchanged. No upload/replay/Notebook rerun occurred. Manual001 is excluded from automatic-delivery acceptance.",
            "gate"),
        p(
            "受入れは実queryで15,000行/14,900 EventID/重複100、raw253,886,000円/dedup252,058,000円、fixture期間外0を照合しました。.show table detailsは10,000行のまま遅延しており、extent統計を実行結果の代用にしません。将来の回復も既存blobのhashとscopeを確認して別承認し、元の3件自動成功と呼び替えません。",
            "Acceptance used actual queries: 15,000 rows/14,900 EventIDs/100 duplicates, raw JPY253,886,000/deduplicated JPY252,058,000 and zero rows outside the fixture window. .show table details lagged at10,000; extent statistics are not a query-result proxy. Any future recovery needs separate approval and existing-blob hash/scope checks; never relabel it as three automatic successes."),
    ])
    sub(r[10], "5", ("native時系列保存とproperty数の差分", "Native time-series save and property-count delta"), [
        p(
            "native保存/readbackでDonationEvents、IncomingDonationAmountYen:TimeSeries<int64>、valueColumn=DonationEvents.DonationAmountYen、orderingColumn=DonationEvents.DonatedAt、MunicipalityID→MunicipalityIdとadditionalBackingTableを確認しました。さらにOntology agent Planのbounded KQLがmanaged child-Eventhouse query headで実行され、観測件数・集約・限定sampleを独立KQLと照合しました。これはFUNCTIONAL native TS queryの実証です。",
            "Native save/readback confirms DonationEvents, IncomingDonationAmountYen:TimeSeries<int64>, valueColumn=DonationEvents.DonationAmountYen, orderingColumn=DonationEvents.DonatedAt, MunicipalityID-to-MunicipalityId and additionalBackingTable. A bounded Ontology agent Plan KQL was then executed through the managed child-Eventhouse query head; observation counts, aggregate and a limited sample matched independent KQL. This is verified FUNCTIONAL native TS querying."),
        table(
            [("数える対象・時点", "Scope and snapshot"), ("件数と意味", "Count and meaning")],
            [
                [("公開baseline / 保存前の明示catalog", "Public baseline / pre-save explicit catalog"),
                 ("72 static + 1 time series = 73。", "72 static + one time series = 73.")],
                [("保存前UIの追加backing FK列", "Additional backing-FK columns in earlier UI"),
                 ("14列。明示Entity propertyの件数とは別。", "Fourteen columns, separate from explicit entity-property count.")],
                [("今回のnative保存後readback", "Readback after this native save"),
                 ("Municipality.PrefectureIdが新規明示propertyへ自動昇格。73 static + 1 time series = 74。", "Municipality.PrefectureId was auto-promoted to a new explicit property: 73 static + one time series = 74.")],
            ], ("表示列、baseline、現在定義を混同しない", "Separate displayed columns, baseline and current definition")),
        note(
            "reviewは追加business FK PrefectureIdを保持し、現在73 static + 1 TSです。元72 staticとの同値を隠れて主張しません。旧custom statusはexact current SHA guardで補正し、他partsはバイト一致。機能queryでもcore定義は不変、raw重複を保持し、static/Gold金額を混ぜていません。個別回答値・ID・query URI・内部reasoningはprivateに保ちます。Graphは使っておらず、TS Graph成功やdirect dashboard成功ではありません。",
            "Review retains the exposed business FK PrefectureId: current73 static + one TS, not hidden equivalence to the original72 static. The stale custom status was corrected under an exact-current-SHA guard with other parts byte-identical. Functional querying left the core definition unchanged, preserved raw duplicates and did not mix static/Gold amounts. Individual values, IDs, query URIs and internal reasoning stay private. No Graph was used: this is not TS Graph or direct-dashboard success.",
            "gate"),
    ])
    sub(r[11], "4", ("独立したstaged-file品質分岐の実績", "Observed independent staged-file quality branch"), [
        p(
            "Notebook 05は凍結済み3CSVのstaging copyを直接入力として1回Completedとなり、29 outputs、raw file rows 15,000、accepted 14,900、quarantine 100を確認しました。静的80,000件・1,344,099,000円、受入増分14,900件・252,058,000円は実SQLとsource-owned DAXで一致しました。",
            "Notebook 05 completed once from staged copies of the three frozen CSVs, producing 29 outputs with raw file rows 15,000, accepted 14,900 and quarantine 100. Actual SQL and source-owned DAX agree on static 80,000 / JPY 1,344,099,000 and accepted increment 14,900 / JPY 252,058,000."),
        note(
            "この分岐はEventhouseを入力にしていません。後のnative手動回復でEventhouseも15,000行へ一致しましたが、Goldのfile入力経路や自動2件/手動1件の来歴を合併しません。quality acceptanceはNotebook05の技術的受入条件で、人の承認・支払・発送・自動配送完了を意味しません。",
            "This branch does not read Eventhouse. Eventhouse later reconciled to15,000 after native manual recovery, but retain Gold's file-input lineage and the two-automatic/one-manual delivery split. Quality acceptance is Notebook05's technical acceptance boundary, not human approval, payment, shipment or proof of automatic delivery.",
            "gate"),
    ])
    sub(r[12], "7", ("native Metricsの実表示と照会の限界", "Observed native Metrics and query-evidence limits"), [
        p(
            "実Semantic modelから別のAnalytics Ontologyをnative生成し、日本語の業務Entity 5件とnative Metrics 10件、SourceModelへのlinkを観測しました。Metric detailのSourceとApplies toを確認し、View expressionで元DAX、開いた状態ではHide expressionを確認しました。Metricsがまだ存在しないという旧状態ではありません。",
            "A separate Analytics Ontology was natively generated from the actual semantic model, with five Japanese business entities, ten native Metrics and SourceModel links observed. Metric detail exposes Source and Applies to; View expression opens original DAX and becomes Hide expression. The earlier state of no native Metrics is superseded."),
        p(
            "fresh read-onlyのOntology agent応答では4つのレイヤー別MeasureとDAX、静的80,000/1,344,099,000、Gold受入14,900/252,058,000の一致を確認しました。ただし回答中の「実行した」という文言は独立query実行traceではありません。native Metric linkと数値一致は観測済み、実行経路の独立証明は未取得と分けます。",
            "A fresh read-only Ontology agent response supplied the four layer measures and DAX, agreeing on static 80,000/1,344,099,000 and accepted Gold 14,900/252,058,000. A response saying it executed DAX is not an independent query-execution trace. Native Metric links and numerical agreement are observed; independent execution-path proof is missing."),
        note(
            "MetricのSynonymsは無効で、実UIは「Metric synonyms aren't available yet.」と表示しました。entity synonym手順をMetricへ流用しません。このMetric-rich itemへTMDL全文を再送せず、source link復元・refresh・独立実行traceは別の未完了検査として残します。",
            "Metric Synonyms is disabled and actual UI states “Metric synonyms aren't available yet.” Do not reuse entity-synonym instructions for Metrics. Do not replay full TMDL over this Metric-rich item; source-link restoration, refresh and independent execution traces remain separate incomplete checks.",
            "gate"),
    ])
    comparison = next(section for section in r[15].children if section.ident == "ch-15-6")
    comparison.blocks.extend([
        p(
            "同一Ontology・同一凍結promptの別会話で、Aは添付がないため資料内容を推測せず、BはPDF/TXT/PNGの3ファイルを実uploadして各内容を説明しました。Bの応答は業務要件、実辞書、方向付き図の役割を区別しました。前後のsemantic parts SHAは同一で、定義の変更はありません。",
            "Separate conversations used the same ontology and frozen prompt: A abstained without attachments, while B actually uploaded PDF/TXT/PNG and explained their contents. B distinguished the business requirements, actual dictionary and directed diagram. Before/after semantic-part hashes match; the definition was unchanged."),
        note(
            "試験したstaged PDF/TXTは現在のpackと異なる版の可能性があるため、凍結receiptのファイルhashを正本とします。今のPDF/TXTへ差し替えて同じ試験結果と呼びません。これはdocument-onlyの部分試験で、現行pack認証、live-source正確性、source探索、attachment-grounded preview/Act、実行traceや3回再現性を証明しません。",
            "The tested staged PDF/TXT may differ from the current pack; the frozen receipt's file hashes are authoritative. Do not substitute current PDF/TXT bytes and call it the same experiment. This document-only subtest is not current-pack certification, live-source accuracy, source discovery, attachment-grounded preview/Act, execution traces or three-run repeatability.",
            "gate"),
        p(
            "現行4ファイルpackはNotebook05 GoldのStaticSeed/RealtimeIncrementと技術的quality acceptanceを明示します。revisionはobject kind、reusableProperty、redefines、native Version、saved readbackを要求します。新しいfresh会話で同じ質問を1回、4ファイルのupload acknowledgementと正しいGold定義/範囲の資料利用を確認し、定義は不変でした。現行4ファイルのhash一致と6 local testsを確認した別runで、旧3ファイルA/Bとは混ぜません。",
            "The current four-file pack explicitly defines Notebook05 Gold StaticSeed/RealtimeIncrement and technical quality acceptance. Revision requires object-kind checks, reusableProperty, redefines, native Version and saved readback. A fresh conversation repeated the same question once: four-file upload acknowledgement and correct document-grounded Gold definition/scope were observed, with the ontology definition unchanged. This separate run verified the current four file hashes and six local tests; do not mix it with the earlier three-file A/B."),
        note(
            "Goldの受入済みはNotebook05のquality gateを通過した分析行という意味です。manual approval、支払・発送状態、Eventhouse自動配送や元84条件の合格を推測しません。添付の生成・再buildは所有者のfreeze工程で行い、読者の本番環境へ自動適用しません。",
            "Gold accepted means analytical rows passing Notebook05 quality gates. Infer neither manual approval, payment/shipment state, Eventhouse automatic delivery nor original84 acceptance. Attachment regeneration belongs to the owner's freeze workflow, not automatic application to a reader's production environment.",
            "gate"),
        p(
            "その後の別のmatched Plan比較では、同一の新しいpromptをfresh会話で各1回送信し、Aは添付0、Bは現行Gold-awareのPDF・辞書TXT・方向付きPNG・改訂要求TXTの4ファイルを使用しました。Aは未提供のレイヤー定義を作らず、Bは資料中のStaticSeed／品質受入増分と実Bindingを区別しました。両方でDonationQualityScopeとDataLayer:Stringのkeyless／unboundなreadonly提案を開き、保存定義は不変でした。",
            "A later, separate matched Plan comparison submitted the same new prompt once in each fresh conversation: A used no attachments; B used the current Gold-aware PDF, dictionary TXT, directed PNG and revision-request TXT. A did not invent absent layer definitions; B distinguished document-defined StaticSeed/quality-accepted increment from actual bindings. Both opened a readonly, keyless/unbound DonationQualityScope proposal with DataLayer:String; the saved definition remained unchanged."),
        note(
            "この比較ではApprove／Act／Save／materializeを行っていません。BのError0／Warning1はnative応答の報告であり、独立した内部実行traceや提案全体のstable IDs／shared refs検査ではありません。旧3ファイルの比較、実データ取込、元84条件の合格、一般母集団の精度とは別に記録します。",
            "No Approve, Act, Save or materialization was performed. B's reported Error0/Warning1 is native response content, not an independently exposed internal trace or a complete proposed stable-ID/shared-reference check. Keep this comparison separate from the earlier three-file pair, physical ingestion, original84 acceptance and general-population accuracy.",
            "gate"),
    ])
    sub(r[17], "4", ("主DraftのSQL＋CI実行と標準評価の分離", "Main-Draft SQL/CI execution, separate from standard evaluation"), [
        p(
            "主Fabric Data Agentは1件のまま、Lakehouse・KQL・Ontology・直接Semantic modelの4sourceとCI設定を公開版で読み戻しました。追加live 3問の数値一致は19.8節のとおりです。公開済み・CI有効・回答一致を、CI tool呼出やCSV/図の実download、source query traceの証拠に読み替えません。",
            "The single main Fabric Data Agent's published definition was read back with four sources: Lakehouse, KQL, ontology and the directly connected semantic model, plus CI configuration. Supplemental three-question numerical agreement is in 19.8. Published/configured/answer-agreement states do not prove CI tool invocation, actual CSV/chart downloads or source-query traces."),
        p(
            "別のmain Draft UI smokeではnative SQL ExecuteとPython Succeeded、実CSV/PNG downloadを確認し、10 CSV行/40 cellをimmutable seedと照合、先頭ゼロも保持しました。初回PNGの日本語glyph欠落は失敗として残し、installed Noto CJK fontを使って同じCSVだけから描画修正しました。source再queryもCSV上書きもしていません。",
            "A separate main-Draft UI smoke verified native SQL Execute, Python Succeeded and actual CSV/PNG downloads. Ten CSV rows/40 cells matched immutable seed with leading zeroes preserved. Retain the initial PNG's missing Japanese glyphs as a failure; rerender using an installed Noto CJK font from the same CSV, without source requery or CSV overwrite."),
        note(
            "このCI smokeは元84条件のcreditではありません。Context候補のpublished MCP runは元10問を各1回で完了し39 PASS/38 FAIL/実行未検証4/N/A3/前提blocked0でした。変更はOntology sourceのstatic companion化＋generic instructionsで、instruction-only因果A/Bではありません。mainとStaticFirstは未変更、promotionなし。後続native UI/SDK診断は別に扱います。",
            "This CI smoke is not credit for the original84 conditions. The Context candidate's published-MCP run completed all ten original questions once:39 PASS/38 FAIL/four execution-unverified/three N/A/zero preblocked. The intervention combines static-companion ontology routing and generic instructions, not an instruction-only causal A/B. Main and StaticFirst are unchanged, with no promotion. Subsequent native UI/SDK diagnostics remain separate.",
            "gate"),
    ])
    sub(r[19], "8", ("過去の3問smoke（元suite・新CI smokeとは別）", "Historical three-question smoke, separate from the original suite and new CI smoke"), [
        p(
            "固定したstatic/Gold/DAX範囲の3問を各1回送信し、HTTP 200が3/3、再送・追質問・timeoutは0でした。公開するのは下の集約だけです。raw回答、oracle、prompt、source ID、会話識別子はprivateのままです。",
            "Three fixed questions in the static/Gold/DAX scope were each submitted once: 3/3 HTTP 200 responses, with zero resubmissions, follow-ups or timeouts. Only the aggregates below are included; raw answers, oracle, prompts, source IDs and conversation identifiers remain private."),
        table(
            [("評価するもの", "Measured dimension"), ("分子 / 分母と解釈", "Numerator / denominator and meaning")],
            [
                [("数値の回答一致", "Numerical answer agreement"), ("3/3問・10/10数値項目。回答テキストと固定oracleの一致。", "3/3 questions and 10/10 numeric cells; answer-text agreement with the frozen oracle.")],
                [("範囲・単位の明示", "Scope and units stated"), ("範囲3/3、円単位3/3。回答本文の評価。", "Scope 3/3; JPY units 3/3, assessed in answer text.")],
                [("引用とquery原文", "Citations and query text"), ("引用は3/3部分的。実行可能query原文は0/3。", "Citations partial in 3/3; executable query text supplied in 0/3.")],
                [("独立実行証明", "Independent execution proof"), ("取得0/3、観測不能3/3。0%正答率という意味ではない。", "Supplied 0/3; unobservable 3/3. This does not mean 0% factual accuracy.")],
                [("backend会話の新規性", "Fresh backend conversation"), ("証明0/3。新HTTP/MCP初期化と履歴なしだけでは不足。", "Proven 0/3; fresh HTTP/MCP initialization without history is insufficient.")],
                [("元10問/84条件", "Original ten questions / 84 conditions"), ("このsmoke当時は未採点。後続baseline/StaticFirst/最終候補を別集計。", "Unscored at this smoke snapshot; later baseline/StaticFirst/final-candidate runs are separate.")],
            ], ("数値一致と実行に基づく正しさは異なる分母", "Answer agreement and execution-grounded correctness have different denominators")),
        note(
            "「100% AI accuracy」とは記載しません。回答レビューはCopilotによるもので独立人手評価ではなく、CUは未観測です。Gold一致はraw配送やGQL成功を証明せず、過去offline全blocked snapshotも今回の実回答statusの代用にはしません。",
            "Do not label this “100% AI accuracy.” Answer review was performed by Copilot, not an independent human, and CU was unobserved. Gold agreement proves neither raw delivery nor GQL success; the earlier all-blocked offline snapshot also cannot stand in for this batch's actual answer status.",
            "gate"),
    ])
    sub(r[22], "5", ("standards-only native往復と保持/損失", "Standards-only native cycle: preservation and losses"), [
        p(
            "459,935-byteの旧furusato-ontology.ttlは実native importでunexpected internal errorになりました。原本は変更せず、workshop/v3.0.0-preview/ontology/native-import/furusato-business-ontology.ttlの52,841-byte候補を別入力として使用しました。候補manifestのhashを固定し、旧payloadの成功と取り違えません。",
            "The 459,935-byte legacy furusato-ontology.ttl failed actual native import with an unexpected internal error. The original stayed unchanged; the separate 52,841-byte candidate at workshop/v3.0.0-preview/ontology/native-import/furusato-business-ontology.ttl was used instead. Freeze its manifest hash; do not relabel this as legacy-payload success."),
        p(
            "native import/export/reimportは完了し、両importはPreserved 98 / Fixed automatically 0 / Not supported 0、10Entity/73Property/15Relationshipでした。native exportは51,633 bytesで再import入力と同一。98再生成GUIDだけを除くと14/14 TMDL partsが一致し、namespace URI/default namespaceを保持しました。候補生成manifestの未試験表示は生成時の履歴で、後続native結果とは別です。",
            "The native import/export/reimport cycle completed. Both imports show Preserved 98 / Fixed automatically 0 / Not supported 0, ten entities/73 properties/fifteen relationships. The 51,633-byte native export exactly matches the reimport input. Excluding only 98 regenerated GUIDs, 14/14 TMDL parts match and namespace URI/default namespace are preserved. The generator manifest's untested label is historical, separate from later native execution."),
        note(
            "100%は縮小候補98objectの分母です。candidate→exportで73 labelsを書換え、41 xsd:longをxsd:integerへ拡大、ontology label変更とcomment/versionInfo欠落を確認しました。元custom Fabric annotation/SKOS altLabel/binding/key/TS動作は候補から除外されており、lossless legacy round tripではありません。73 datatype declarationsはprimary coreの73 static+1 TSとも別です。",
            "The 100% denominator is the reduced candidate's 98 objects. Candidate→export rewrote 73 labels, widened 41 xsd:long ranges to xsd:integer, changed the ontology label and lost its comment/versionInfo. Original custom Fabric annotations/SKOS altLabel/bindings/keys/TS behavior were omitted from the candidate: this is not a lossless legacy round trip. Its 73 datatype declarations are also distinct from the primary core's 73 static plus one TS.",
            "gate"),
    ])
    if selected_run is not None:
        overview.blocks.insert(0, note(
            "下のfeature receiptは既存のscope付き履歴です。選択runの新規再確認へ流用せず、元suiteの現在の選択を19.10節で区別します。",
            "The feature receipts below retain their existing historical scopes. They are not new rechecks by the selected run; its original-suite selection is separated in19.10.",
            "gate",
        ))
    completion30_sections(roots, selected_run)


def completion30_sections(roots, selected_run=None):
    r = {section.chapter: section for section in roots if section.chapter}
    sub(r[4], "5", ("観測済みrunと新環境のreadyを分ける", "Separate observed runs from readiness in a new environment"), [
        note(
            "このPreview教材のsupported labには実証済みのものがありますが、Preview≠GAです。公開evidence projectionは審査済みの過去runと制約を再現するためのもので、別環境のfeature rollout・権限・配置・query readinessを保証しません。新環境では既存のpreflight/scope/承認をやり直し、未提供laneとknown issueをそのまま記録します。",
            "Some supported labs in this Preview have verified observations, but Preview is not GA. A public evidence projection reproduces a reviewed historical run and its limits; it does not guarantee rollout, permissions, deployment or query readiness elsewhere. Recheck existing preflight/scope/approval in each new environment and retain unavailable lanes and known issues.",
            "gate"),
    ])
    sub(r[13], "4", ("実Rule表示とMCP queryの境界", "Observed rule UI versus MCP query behavior"), [
        p(
            "native Rules > Edit ruleではSupplierAttributionの文言とSupplier/Gift/Donationのlinked conceptsを観測しました。SupplierProvidesGiftは登録上の適格性で、寄附単位の実供給者割当を証明せず、多対多JOINでDonation金額を増幅させないというcontextです。",
            "Native Rules > Edit rule displayed SupplierAttribution and linked Supplier/Gift/Donation concepts. Its context says SupplierProvidesGift denotes catalog eligibility, not actual per-donation supplier assignment, and a many-to-many join must not multiply Donation amounts."),
        note(
            "Ruleはaction/constraint enforcementではありません。公式MCPのlist_ontology_rulesで4件読めたことは、ask_ontologyがRulesを考慮した証拠ではありません。現行docsはask_ontologyがRulesを考慮しないと説明します。UI/Ontology agent/MCP/Data Agentでの効果を個別に検証します。",
            "A rule is not action/constraint enforcement. Reading four rules through official MCP list_ontology_rules does not prove ask_ontology used them: current documentation says ask_ontology does not consider Rules. Verify effects separately across UI/Ontology agent/MCP/Data Agent.",
            "gate"),
    ])
    sub(r[15], "10", ("別intentの成功例: keyless/unbound Entityの追加", "Separate successful intent: add a keyless/unbound entity"), [
        p(
            "metadata-only Actがshared referenceを失った旧失敗はFAILED/rollback済みのままです。別のRule提案がRelationshipを作ろうとしたときはobject kindを確認し、保存せず拒否しました。修正したpositive Plan/ActだけがPaymentMethodとString PaymentMethodName、およびmodel refを追加しました。",
            "The earlier metadata-only Act that lost a shared reference remains FAILED and rolled back. A separate Business Rule proposal incorrectly attempted a Relationship; object-kind review rejected it without saving. Only the corrected positive Plan/Act added PaymentMethod, String PaymentMethodName and the model reference."),
        table(
            [("typed intent", "Typed intent"), ("厳密な読戻し条件", "Strict readback condition")],
            [
                ["add-unbound-keyless-entity", ("新EntityはPaymentMethod、新propertyはPaymentMethodName:string、key/bindingなし。query/Graphの成功とはしない。", "New entity PaymentMethod, property PaymentMethodName:string, no key/binding; not query/Graph success.")],
                ["existing parts", ("model.tmdl以外の既存semantic partsはバイト一致。既存IDs・型・key・binding・shared refs・inheritanceを保持。", "Existing semantic parts except model.tmdl are byte-identical; existing IDs/types/keys/bindings/shared refs/inheritance remain.")],
                ["exact approved delta", ("追加partはentities/PaymentMethod.tmdlだけ、削除なし。model変更はref entity PaymentMethodだけ。", "Only entities/PaymentMethod.tmdl is added; no removals. Model change is only ref entity PaymentMethod.")],
            ], ("metadata-only ACT_INVARIANTSを緩めない別判定", "Separate acceptance without weakening metadata-only ACT_INVARIANTS")),
        prompt(
            "Planでのみ、既存定義を変えずにunbound/keyless Entity PaymentMethodとString property PaymentMethodNameを追加するdraft/previewを示してください。新規partはentities/PaymentMethod.tmdl、既存modelの差分はref entity PaymentMethodだけです。既存IDs・property集合/型・key・binding・reusableProperty・redefines/継承を保持します。RuleやRelationshipへの置換、余計な削除・更新があれば停止してください。Actは別承認後だけです。",
            "In Plan only, without changing the saved definition, show a draft/preview adding unbound/keyless entity PaymentMethod and String property PaymentMethodName. The only new part is entities/PaymentMethod.tmdl; the existing model delta is only ref entity PaymentMethod. Preserve existing IDs, property sets/types, keys, bindings, reusableProperty and redefines/inheritance. Stop on a Rule/Relationship substitution or any extra removal/change. Act requires separate approval."),
        note(
            "Planでsaved definitionが不変、Apply後は全partsと承認deltaを比較します。既存property集合の保持条件を『追加だから不要』として消しません。copilot-additive-entityの独立したcapture/statusを使い、この成功を旧shared-reference bugの修正合格に転用しません。",
            "Verify Plan leaves the saved definition unchanged, then compare every part and the approved delta after Apply. Do not discard existing-property preservation because the change is additive. Use the separate copilot-additive-entity capture/status; this success does not fix or pass the old shared-reference bug.",
            "gate"),
    ])
    sub(r[16], "5", ("同じLakehouseのstatic Relationships companion", "Static Relationships companion over the same Lakehouse"), [
        p(
            "primary TS coreはEligibleでもMaterializeがInvalidPropertyType IncomingDonationAmountYenで失敗しました。primaryの73 static+1 TSとnative KQL bindingは保持し、別のstatic Relationships Ontologyを10Entity/72 static/15Relationshipで同じLakehouseへbindしました。追加Lakehouse/source datasetのcopyはありません。ただしGraph実体化は派生projectionを保存します。Graph自体をzero-copyとは呼びません。",
            "The primary TS core showed Eligible but Materialize failed with InvalidPropertyType IncomingDonationAmountYen. Preserve its73 static plus one TS and native KQL binding; bind a separate static Relationships ontology with ten entities/72 static/fifteen relationships to the same Lakehouse. No extra Lakehouse/source dataset copy is made. Graph materialization does store a derived projection; Graph itself is not described as zero-copy."),
        p(
            "このcompanionではnative GQL3/3を実行し109,592 nodes/297,303 directed edges、全10 node labels/15 relationship labels、source件数と要求pathを照合しました。全property値や全edge pairの網羅比較ではなく、primary TS Graph成功でもありません。",
            "Native GQL3/3 on this companion verified109,592 nodes/297,303 directed edges, all ten node labels/fifteen relationship labels, source counts and requested paths. This is not exhaustive comparison of every property/edge pair and not primary TS Graph success."),
        p(
            "小さな1Entity Temp投影の別試験ではMunicipality label・1,741 nodesと5 sample/40 valuesをSQLに照合しました。物理列MunicipalityDisplayName AS AreaNameを使い、先のwrong-column SQL failureも保持します。この小試験はfull109,592/297,303の証明ではなく、edge件数queryもしていません。",
            "A separate small one-entity Temp projection reconciled label Municipality,1,741 nodes and five samples/40 values to SQL using physical MunicipalityDisplayName AS AreaName. Preserve the earlier wrong-column SQL failure. This small test is not the full109,592/297,303 proof and did not query edge counts."),
    ])
    sub(r[16], "6", ("native Explore graphの実操作とcaptionの罠", "Actual Explore graph controls and the caption trap"), [
        p(
            "ComponentsのCHECKBOXを選び、Add filterでPrefectureId=42、Run queryを1回、Table viewを確認しました。gridは21 pathsを報告し、可視10 pathsのID・名前・方向・node連続性を独立照合しました。row clickはfocusだけでした。default node captionはamount rankでbusiness IDではありません。",
            "Select the Components CHECKBOX, Add filter PrefectureId=42, run once, then inspect Table view. The grid reported21 paths; ten visible paths' IDs/names/direction/node continuity were independently checked. Row click only focused it. Default node captions were amount ranks, not business IDs."),
        note(
            "公開用はprivate Source headerを除外した実captureだけを使い、原画の環境情報は収録しません。UI smokeの成立や選択subsetの件数を、元84条件の回答合格や全graphの再検証として数えません。",
            "Use only the actual capture excluding the private Source header; keep the raw environment-bearing image private. UI smoke or selected-subset counts are not original84 answer credit or revalidation of the entire graph.",
            "gate"),
    ])
    connector_history = sub(r[17], "5", ("Graph readinessとData Agent consumer互換性の分離", "Graph readiness is not Data Agent consumer compatibility"), [
        p(
            "Contextのpublished-MCP採点とは別に、native UIのT04診断で正しいgeneration2 Relationships itemへのconnector stepを確認しました。Publishから約40分後でも、次の実エラーでした。Graphとnative Ontology agentのdirect routeは既に動作確認済みなので、Graph/data不在をこの診断のroot causeと説明しません。",
            "Separately from published-MCP grading, native UI T04 diagnostics captured a connector step targeting the correct generation2 Relationships item. About40 minutes after publication, it returned the actual error below. Direct Graph and native Ontology agent routes already work; do not describe Graph/data absence as the root cause of this diagnostic."),
        p(
            "実connector error: Unable to generate code: The request is invalid. This API version is not supported for the specified Ontology item.",
            "Actual connector error: Unable to generate code: The request is invalid. This API version is not supported for the specified Ontology item."),
        note(
            "これは当該runのData Agent generation2 connector consumer pathの失敗です。全製品/tenantでの普遍的非対応、別runの全FAILの原因、正しいcontextual refusal、query実行成功とは主張しません。native UI/SDKqualificationやfresh会話の証拠をMCP39/38/4/3のledgerへ混ぜず、別のreceiptとして保存します。",
            "This is a failure of the Data Agent generation2 connector consumer path in this run. It is not a universal product/tenant limitation, an explanation of every FAIL in another run, correct contextual refusal or successful query execution. Keep native UI/SDK qualification and fresh-conversation evidence separate from the MCP39/38/4/3 ledger.",
            "stop"),
    ])
    native_history = sub(r[17], "6", ("Clear chatの確認と独立native UI診断", "Confirm Clear chat and keep native UI diagnostics separate"), [
        p(
            "Clear chatを押しただけでは新会話とは限りません。CONFIRMまで完了し、公式diagnosticsのconversation IDが前runと異なること、user messageが1件であることをprivateに確認します。最初に確認を完了しなかった共有会話T06のclarificationは保存し、独立runの証明から除外しました。",
            "Clicking Clear chat alone does not prove a new conversation. Complete CONFIRM, then privately verify the official diagnostic conversation ID differs from the prior run and contains one user message. Retain the earlier shared-conversation T06 clarification whose confirmation was not completed, but exclude it from isolated-run proof."),
        p(
            "別のfresh native T06では3回のKQL実行を確認しました。誤った2025年範囲でempty→利用可能期間のdiscovery→正しい2026年範囲へ自己修正し、返却21 cellsを独立照合しました。候補instructionsは凍結draftと一致し、MCP採点は上書きしていません。",
            "A separate fresh native T06 diagnostic showed three actual KQL executions: empty results for an incorrect2025 window, discovery of available periods, then correction to the available2026 window. Twenty-one returned cells were independently reconciled. Candidate instructions matched the frozen draft; the published-MCP scores were not overwritten."),
        note(
            "モデル/runtimeはUI bannerから推測せず、存在する場合は公式diagnosticsのrecordedModel/runtime/stageを記録します。この診断の記録はgpt-5.6-terra / preview / sandboxでした。transport・隔離・確率変動のどれが差を生んだかは未証明です。最終文中の『arrival periods』はbusiness-observation期間を言い換えたもので、実upload/ingestion時刻を照会していないため、完全に正しい回答とは呼びません。",
            "Do not infer the model/runtime from the UI banner; record official diagnostic recordedModel/runtime/stage when present. This diagnostic recorded gpt-5.6-terra / preview / sandbox. It does not isolate transport, isolation or stochastic variation as the cause. Final prose called business-observation periods arrival periods without querying actual upload/ingestion timing, so do not call the answer perfect.",
            "gate"),
    ])
    consumer = sub(r[17], "7", ("最終Compat NativeUIの方法とpostcheck", "Final Compat NativeUI method and postcheck"), [
        p(
            "最終固定rubric判定はcoordinatorがofflineで行い、元10問を各1回、84条件を変更せず48 PASS/36 FAILでした。公式diagnosticsで異なる10 backend会話を確認し、source実行は9回（SQL5/GQL2/KQL2）、実行証拠がある質問slotは7です。runtime=preview、stage=sandbox、recorded model=gpt-5.6-terraで、UI bannerの推測ではありません。",
            "The coordinator completed offline judgment against the unchanged fixed rubric: ten original questions once,84 conditions,48 PASS/36 FAIL. Official diagnostics prove ten distinct backend conversations and nine source executions (SQL5/GQL2/KQL2), covering seven question slots with execution evidence. Runtime=preview, stage=sandbox and recorded model=gpt-5.6-terra come from diagnostics, not banner inference."),
        note(
            "generation1 bridgeを使った別consumer pathではT04のGQLが実行され、照合済みchild row集合が返りました。gen2のAPI-version errorはこの別pathでは出ませんでしたが、gen2 connectorを修正した証明ではありません。T04はparent集約のgrain/要求された表現条件に残る失敗があり、接続成功を回答品質合格にしません。",
            "On the separate generation1 bridge consumer path, T04 executed GQL and returned the reconciled child-row set. The gen2 API-version error was absent on this separate path; this does not prove the gen2 connector was fixed. T04 still fails parent-aggregation grain/required presentation criteria. Connectivity success is not answer-quality acceptance.",
            "gate"),
        p(
            "postcheckでは4つのpublished定義はすべて不変で、main/StaticFirst/Contextのfull定義も不変でした。Compat draftだけでKQL/Lakehouse catalog metadataがUIにより拡張されましたが、parent-gatedな実選択table/column scopeはKQL11・LH99で前後同一、未選択raw EventIDの公開はなく、再Publishしていません。GLOBAL/source instructionsとCI設定も不変です。",
            "Postcheck found all four published definitions unchanged, with main/StaticFirst/Context full definitions unchanged. Only Compat draft KQL/Lakehouse catalog metadata expanded through UI. Effective parent-gated table/column selection remained KQL11/LH99 before and after, with no exposure of unselected raw EventID and no republish. GLOBAL/source instructions and CI settings also remained stable."),
    ])
    sub(r[20], "5", ("実MCP discoveryと条件付きnamespace/dashboard", "Actual MCP discovery and conditional namespace/dashboard lanes"), [
        p(
            "generation2の公式ontologyEndpointでask_ontology / list_ontology_rules / list_ontology_entitiesの3toolsをdiscoverし、4Rulesの名前/statementが現行Ontologyと一致することを確認しました。このcheckではAI質問・source/config writeはしていません。query実行・Rules利用・enforcementは別判定です。公開形は20.4節のplaceholderだけで、endpointやquery URIを公開しません。",
            "Official generation2 ontologyEndpoint discovery returned ask_ontology, list_ontology_rules and list_ontology_entities; four Rule names/statements matched the current ontology. This check submitted no AI question or source/configuration write. Query execution, Rule use and enforcement are separate judgments. Publish only the placeholder form in20.4, never actual endpoint/query URIs."),
        note(
            "+Namespace/Manage namespacesとdirect Ontology→Real-Time Dashboard entryは2132 CSS pixels幅のnew UI ribbonでも確認されませんでした。feature flagsは迂回していません。この環境の観測であり、普遍的な製品非対応とはしません。RDF URI/default namespaceの保持は実往復で検証済みですが、UI管理成功ではありません。TS探索の実証済み経路はnative Ontology agent KQLで、direct dashboardの合格ではありません。",
            "+Namespace/Manage namespaces and a direct Ontology→Real-Time Dashboard entry were not observed in the2132-CSS-pixel-wide new-UI ribbon. No feature flags were bypassed. This is an environment observation, not universal product unsupported status. RDF URI/default-namespace preservation is verified, not UI-management success. The verified TS exploration route is native Ontology agent KQL, not direct-dashboard acceptance.",
            "gate"),
        p(OFFICIAL_BASE + "how-to-use-namespaces", OFFICIAL_BASE + "how-to-use-namespaces"),
        p(OFFICIAL_BASE + "how-to-use-ontology-mcp-server", OFFICIAL_BASE + "how-to-use-ontology-mcp-server"),
    ])
    sdk = sub(r[20], "6", ("外部Responses SDK資格確認の限定blocker", "Scoped blocker in external Responses SDK qualification"), [
        p(
            "外部SDKはimportとmetadata認証まで確認できましたが、当該Windows/Python環境ではFabric runtime service-discovery module不足によりruntime discoveryがblockedとなり、質問送信は0でした。native UIのconsumer証拠とは別で、全環境・tenantでSDKが使えないとは主張しません。dependency/hostを別途資格確認し、未取得の実行証拠を捏造しません。",
            "The external SDK imported and authenticated metadata, but runtime discovery was blocked in this Windows/Python environment by a missing Fabric runtime service-discovery module; zero questions were submitted. This is separate from native UI consumer evidence and does not claim universal SDK failure across environments or tenants. Qualify the dependency/host separately; do not invent missing execution proof."),
    ])
    if selected_run is not None:
        context = preview30_reporting.selected_context()
        for section in (connector_history, native_history):
            section.blocks.insert(0, note(
                "この診断は保存した過去runだけの観測です。選択runのT04/期間/connector状態として再使用しません。",
                "This diagnostic is an observation of its retained historical run only, not the selected run's T04/window/connector status.",
                "gate",
            ))
        consumer.title = t("17.7 明示選択runの方法と未再確認のcontext", "17.7 Explicitly selected method and context not newly rechecked")
        consumer.blocks = [
            p(*preview30_reporting.selection_notice(selected_run)),
            table([("記録", "Record"), ("値", "Value")], preview30_reporting.method_rows(selected_run),
                  ("選択runの記録だけ。別会話・native完了・query traceは別", "Selected records only; distinct conversations, native completion and query traces differ")),
            note(*preview30_reporting.execution_completeness_notice(), "gate"),
            *[note(value["reason"]["ja"], value["reason"]["en"], "gate")
              for key, value in context.items() if key != "externalSdk"],
        ]
        sdk.title = t("20.6 選択runの外部SDK資格確認は未検証", "20.6 External SDK qualification is unverified for the selected run")
        sdk.blocks = [note(context["externalSdk"]["reason"]["ja"], context["externalSdk"]["reason"]["en"], "gate")]
    sub(r[20], "7", ("Ontology文脈と実行先を分ける新連携", "Separate Ontology context from source-native execution"), [
        p(
            "新しいOntology-as-context連携では、OntologyはEntity・property・relationship・定義・synonym・mapping・bindingの読取専用文脈を提供し、実照会は接続先のSQL/KQL/DAXで行います。旧Ontology GQLのconsumer pathやGraph実体化とは別の経路です。",
            "In the new Ontology-as-context integration, Ontology supplies read-only entities, properties, relationships, definitions, synonyms, mappings and bindings. The underlying source executes SQL/KQL/DAX. This is distinct from the legacy Ontology GQL consumer path and Graph materialization."),
        Block("list", {"numbered": True, "items": [t(*step) for step in [
            ("実UIでSources→Add sources→Add an ontologyが提供される場合だけ対象Ontologyを追加し、Ontology data sourcesの実一覧を確認します。旧Add data画面や警告だけで新経路の成功とはしません。",
             "Only when Sources → Add sources → Add an ontology is available in the actual UI, add the approved ontology and inspect its real Ontology data sources. An old Add data experience or a warning is not new-path success."),
            ("補助source instructions・description・example queriesは、eligibleなunderlying sourceをmountしてから設定します。Ontologyの定義を書き換える操作とは分離し、Semantic Modelへの補助contextを仮定しません。",
             "Configure supplemental instructions, descriptions and examples only after mounting an eligible underlying source. Separate this from editing Ontology definitions; do not assume supplemental context for semantic models."),
            ("Download ontology contextを実行し、read-only contextのEntity・関係・bindingが対象モデルと一致するか確認します。文脈変更の反映は最大10分、提供されたRefreshで再読込できますが、ダウンロードした文脈を編集して動作を変更しません。",
             "Use Download ontology context and verify the read-only entities, relationships and bindings against the intended model. Context updates can take up to ten minutes or be refreshed through the provided control; editing the downloaded context cannot change behavior."),
            ("run stepsの選択source・実行したSQL/KQL/DAX・返却結果・errorを別々に保存します。1問でのcross-source joinやfederated execution、GQL実行、metadata表示だけの回答品質合格は仮定しません。",
             "Retain the selected source, executed SQL/KQL/DAX, returned results and errors separately. Do not assume cross-source joins, federated execution, GQL execution or answer-quality acceptance from metadata display alone."),
        ]]}),
        note(
            "新経路はPreviewです。選択後もNo data added、無効なsource、context-download未提供などで止まる場合は、定義readbackと実画面を保全してblockedにします。deleted-or-permissionという汎用警告だけで削除や権限不足を断定せず、role・tenant・rollout flagを勝手に変更しません。",
            "This path is preview. If selection leaves No data added, a disabled source or no context-download control, preserve definition readback and actual UI and mark blocked. A generic deleted-or-permission warning does not establish deletion or denied permissions; never change roles, tenant settings or rollout flags autonomously.",
            "gate"),
        p(
            "今回の別qualification itemでは、native catalogから主generation2 Ontologyを1回選択しましたが、画面はNo data addedのまま、保存定義のdatasource partも0でした。保護対象の10 Agentは不変、質問・publishは0です。新context-source mountingとDownload ontology contextがこの環境で成立したという証拠にはしません。",
            "In a separate qualification item, the primary generation2 ontology was selected once through the native catalog, but the UI remained No data added and the saved definition contained zero datasource parts. Ten protected agents remained unchanged; questions and publications were zero. This does not qualify new context-source mounting or Download ontology context in this environment."),
        p("https://learn.microsoft.com/fabric/data-science/data-agent-ontology-sources",
          "https://learn.microsoft.com/fabric/data-science/data-agent-ontology-sources"),
    ])
    sub(r[20], "10", ("SDK管理planeとMCP runtimeの境界", "SDK management plane versus MCP runtime"), [
        p(
            "現行公式SDK手順は、作成・source設定・instructions・publishを管理plane、公開済みData Agentへの質問をMCP runtimeとして分離します。20.6節の旧外部Responses診断を、新しいMCP実行やSDKの普遍的な非対応へ読み替えません。",
            "Current SDK guidance separates creation, source settings, instructions and publication on the management plane from questions to a published Data Agent on the MCP runtime. Do not reinterpret the historical external Responses diagnostic in20.6 as a new MCP execution or universal SDK failure."),
        code("https://api.fabric.microsoft.com/v1/mcp/workspaces/<WORKSPACE_ID>/dataagents/<DATA_AGENT_ID>/agent", "text"),
        Block("list", {"numbered": True, "items": [t(*step) for step in [
            ("endpointは公開済みAgentのSettings→Model Context Protocolから取得し、workspace/itemをprivate receiptと照合します。Data Agent未publishの状態、Ontology endpoint、別のAgentを代用しません。",
             "Obtain the endpoint from a published Agent's Settings → Model Context Protocol and reconcile workspace/item identities to private receipts. Do not substitute an unpublished Agent, an Ontology endpoint or another Agent."),
            ("通常のFabric notebook-managed認証または正式なOAuth/Entra認証を使い、token・cookieは表示・配布しません。SDK内部metadata clientへ必要なheaderが届くか未確認なら、private monkeypatchや推測hostで通さず、SDK経路を別の未qualified laneとして残します。",
             "Use normal Fabric notebook-managed authentication or official OAuth/Entra authentication; never display or distribute tokens or cookies. If required headers cannot be qualified on SDK-owned metadata clients, retain a separate unqualified SDK lane rather than using private monkeypatches or guessed hosts."),
            ("MCPでinitialize→tools/listを実行して実tool名とschemaを確認し、承認したboundedなread-only質問を1回だけ送ります。発見だけ、completedだけ、本文中のExecuted SQLという説明だけを実source traceへ昇格しません。",
             "Initialize MCP, discover actual tool names and schemas, then submit an approved bounded read-only question once. Discovery, completed status or prose claiming Executed SQL is not independent source-execution trace."),
            ("旧external-clientサンプルのAssistants APIは2026-08-26でsunsetしたため、新しい演習へそのままコピーしません。元10問/84条件やheldoutをruntime smokeで再送・置換せず、別の質問・receipt・判定として保全します。",
             "Do not copy the legacy external client's Assistants API into a new exercise after its2026-08-26 sunset. A runtime smoke must not resubmit or replace the original ten/84 or heldout; retain its different question, receipt and judgment separately."),
        ]]}),
        note(
            "質問を含まない接続検査はinitialize／notifications/initialized／tools/listとcleanupだけに限定し、質問・会話・source実行の実績に数えません。全明示API要求に必須headerを付け、実HTTP／native error／完全なstdoutまたはexitValueをprivateに保全します。NotebookのCompletedだけでは接続成功や出力の完全性を証明せず、Notebook Resourcesはsession入力であって質問の永続journalではありません。質問は独立した永続intentと1回限りの送信を確保するまで無効にします。",
            "A zero-question preflight is limited to initialize, notifications/initialized, tools/list and cleanup; it earns no question, conversation or source-execution credit. Include the required header on every explicit API request and privately retain actual HTTP/native errors and complete stdout or exitValue. A Completed notebook proves neither connectivity nor output completeness. Notebook Resources are session inputs, not a question-journal durability proof; keep questions disabled until a separate durable intent and once-only submission are established.",
            "gate"),
        p(
            "専用の通常Fabric Notebookによる今回の1回の接続検査jobはCompletedでしたが、実snapshotのstdout／ExitValueではruntime-context guardが認証前に停止していました。MCP HTTP・managed token取得・質問は0です。公開Settingsのendpoint照合、Notebook実行成功、guardの失敗を分け、MCP接続成功やAgent／認証サービスの障害とはしません。失敗したonce journalは保全し、同じrunの再送や推測contextでのguard迂回は行いません。",
            "The single preflight job in a dedicated normal Fabric notebook reached Completed, but its actual snapshot stdout/ExitValue showed a runtime-context guard failure before authentication. MCP HTTP, managed-token retrieval and questions were zero. Separate published endpoint reconciliation, notebook completion and the failed guard; claim neither MCP connectivity nor an Agent/authentication-service failure. Preserve the failed once journal without resubmitting the same run or bypassing its guard using an assumed context."),
        p(
            "その後の別のruntime-shape-only検査で、実contextはbuiltin dictではなくpy4jのJavaMapで、Mappingとして利用でき、Fabric・Notebook／Workspace identity・非pipeline／reference・default Lakehouseなしの各条件が実値で成立しました。dict限定のguardをMapping対応へ修正した別版でも、元のチェックと失敗原本は保持しています。",
            "A separate runtime-shape-only diagnostic then observed a py4j JavaMap rather than a builtin dict. It implements Mapping, and actual Fabric, notebook/workspace identities, non-pipeline/non-reference flags and no-default-Lakehouse checks passed. A separately frozen Mapping-compatible variant preserves the original checks and failure records."),
        p(
            "さらにnativeのnotifications/initializedはHTTP202・text/plainのAcceptedを返しました。これをJSON-RPC結果としてdecodeしたlocal errorを保持し、同一の明示的なackだけを認識する別版を検証しました。最終の別宣言preflightでは、通常Notebook管理認証でinitialize200→initialized202→tools/list200、実tool名・必須string質問parameterを確認し、完全なnative frameをhash照合してtransportをcloseしました。質問・source query・source書込みは0で、SDK内部metadata-header laneと元84条件の合格は依然別の検査です。",
            "Native notifications/initialized returned HTTP202 with text/plain Accepted. Retain the local error that tried to decode this as a JSON-RPC result; a separately qualified variant recognizes only this exact explicit acknowledgement. The final separately declared preflight used normal notebook-managed authentication for initialize200 → initialized202 → tools/list200, observed the real tool and required string question parameter, hash-verified complete native frames and closed the transport. Questions, source queries and source writes were zero; the SDK-owned metadata-header lane and original84 acceptance remain separate checks."),
        p(
            "再利用用のtools/data-agent/preflight_mcp.pyは、明示した接続許可と新しいprivate出力先を要求し、質問の送信経路を持ちません。NativeMcpClient.preflightとNotebookMcpCredentialを使う場合も、通常認証・期待する実行Notebook・必須header・実応答・cleanupを確認します。接続成功を理由に元質問を別経路で再送したり、回答や実行証跡を補完したりしません。",
            "The reusable tools/data-agent/preflight_mcp.py requires explicit connection permission and a fresh private output directory, and has no question-submission path. NativeMcpClient.preflight and NotebookMcpCredential preserve normal authentication, expected notebook identity, required attribution, actual replies and cleanup. Successful connectivity is not permission to resend original questions through another route or invent answers/execution traces."),
        note(
            "最終用途のWord／HTML／ZIP生成にはRequireAcceptanceを使用します。明示選択した原10問・84条件、native実行証拠、全必須lab・26必須画面、正確なevidence hashに結びついた公開承認を検査し、未達なら出力前に停止します。通常のDRAFT作成や補助画像の追加は、この最終受入を代替しません。",
            "Use RequireAcceptance for final-use Word/HTML/ZIP generation. It checks the explicitly selected original ten/84, native evidence, all required labs and 26 completion captures, plus publication approval bound to the exact evidence hash; unmet conditions stop artifact creation. Ordinary DRAFT generation and supplementary images do not replace this final admission.",
            "gate"),
        p("https://learn.microsoft.com/fabric/data-science/fabric-data-agent-sdk",
          "https://learn.microsoft.com/fabric/data-science/fabric-data-agent-sdk"),
        p("https://learn.microsoft.com/fabric/data-science/consume-data-agent-python",
          "https://learn.microsoft.com/fabric/data-science/consume-data-agent-python"),
    ])
    sub(r[21], "5", ("binding付きlabのnative Version restore", "Native Version restore of a bound lab"), [
        p(
            "native Version historyでbound baselineと成功additive versionを保存し、baselineへRestoreしました。定義hashは完全一致へ復元、既存business IDs・keys・shared refs・bindingsを保持し、復元後Instancesの17行/136 valuesがimmutable sourceと一致しました。",
            "Native Version history saved the bound baseline and successful additive version, then restored the baseline. The exact definition hash, business IDs/keys/shared refs/bindings were restored; post-restore Instances matched immutable source across17 rows/136 values."),
        note(
            "これは定義の復元＋既存bindingの再照合で、source-data rollbackではありません。projected Metrics/backingMeasureを持つMetric-rich itemの復元証明にも一般化せず、21.4節のnative link検査を残します。",
            "This verifies definition restoration and existing bindings, not source-data rollback. Do not generalize to restoration of Metric-rich items with projected Metrics/backingMeasure; retain the native-link checks in21.4.",
            "gate"),
        p(
            "Restore確認でCreate a version of my current work firstを選ぶと、現作業を保全するVersion name／Description欄が現れます。別の画面確認ではこの状態を取得してCancelし、保存定義が完全一致のままであることを再照合しました。確認画面の取得を新しい版の作成や復元の再実行として数えず、証跡のためだけにRestoreを繰り返しません。",
            "Selecting Create a version of my current work first in the Restore confirmation exposes Version name/Description fields for preserving current work. A separate screen inspection captured this state, cancelled and reconciled the unchanged saved definition. A confirmation capture is not a new version or another restoration; never repeat Restore merely to obtain evidence."),
        note(
            "別のMetric-rich検証用Ontologyでは、実10Metricのsource Model参照と現定義を固定してからnative New version→Saveを1回だけ操作しました。実consoleはHTTP400を記録し、Version historyを読取で開き直してもNo versions yetでした。基準版を確認できないため、予定した説明変更とRestoreはどちらも実行していません。Ontologyと元Semantic Modelの定義は前後完全一致です。private endpoint再送やTMDL全体の再適用はせず、この保存障害を製品側調査へ引き継ぎます。特定原因や全環境での非対応、Metric-rich復元成功は主張しません。",
            "For a separate Metric-rich lab ontology, ten native source-model Metric links and its definition were frozen before one native New version → Save attempt. The real console recorded HTTP400, and a readonly reopen still showed No versions yet. Without a confirmed baseline version, neither the planned description edit nor Restore was performed. Ontology and source semantic-model definitions remained byte-identical. Do not resend private endpoints or replay full TMDL; retain this save failure for product investigation. No specific cause, universal lack of support or successful Metric-rich restoration is claimed.",
            "gate"),
    ])
    sub(r[23], "4", ("read-only governanceと未成立のnegative identity検査", "Read-only governance and unproven negative-identity tests"), [
        p(
            "workspace Roleの件数だけをread-onlyで確認し、role/tenant/capacityや新identityは変更していません。権限の低い承認済み第2principalがないため、RLS/OLS/CLSのnegative access checksは未証明です。role一覧の読取を権限制御の動作合格にしません。",
            "Only workspace-role counts were read; no role/tenant/capacity changes or new identities were made. Without an authorized second low-privilege principal, RLS/OLS/CLS negative-access checks remain unproven. Reading role assignments is not enforcement acceptance."),
    ])
    sub(r[24], "7", ("portable static companionの明示opt-in", "Explicit opt-in to the portable static companion"), [
        p(
            "runtimeのrelationships-only生成物とREADME-runtimeを先に確認します。既存core/Lakehouseの所有権receiptを同じprivate evidence directoryに保持し、--include-relationshipsで新しいresource planを作り直して承認します。以前のcore-only gateは新companion作成を許可しません。",
            "First inspect the runtime relationships-only assets and README-runtime. Preserve existing core/Lakehouse ownership receipts in the same private evidence directory; create and approve a new resource plan with --include-relationships. An earlier core-only gate does not authorize the new companion."),
        code(
            'python .\\tools\\provisioning\\preview30_runtime.py preflight --environment dev '
            '--scope "<private-scope.json>" --evidence-dir "<existing-private-evidence>" --online --include-relationships\n'
            'python .\\tools\\provisioning\\preview30_runtime.py deploy-relationships --environment dev '
            '--scope "<private-scope.json>" --evidence-dir "<existing-private-evidence>" '
            '--write-gate "<new-approved-write-gate.json>" --confirm "<new-plan-sha256>"',
            "PowerShell — separate approved stages",
        ),
        note(
            "companionはcreate-only/CLI-onlyで、既存private itemをadoptせず、primaryやKQL binding、Agent routingを変更せず、Notebook/dataを再実行/再copyしません。managed Graph IDはnative readbackで取得し、名前から推測しません。Eligible≠Completed≠query acceptance。portable実装があることを新配置の成功証明にしません。",
            "The companion is create-only/CLI-only: it does not adopt an existing private item, alter primary/KQL bindings/Agent routing, or rerun/copy Notebook/data outputs. Obtain the managed Graph ID through native readback, not inference from a name. Eligible is not Completed or query acceptance. Portable implementation is not evidence of a successful new deployment.",
            "gate"),
    ])
    compatibility_history = sub(r[24], "10", ("隔離generation1 consumer互換性projectionの条件", "Conditions for an isolated generation1 consumer-compatibility projection"), [
        p(
            "公開Create Ontology契約はdefinition partsからgenerationを推定します。Tempの隔離consumer projectionは1回create後、実generation1と53parts/10Entity/72 static/0TS/15Relationship、同じLakehouse mappingをreadbackで確認しました。これは作成/定義受入れであり、consumer互換性の合格ではありません。",
            "The public Create Ontology contract infers generation from definition parts. One isolated Temp consumer projection was created and read back as actual generation1 with53 parts/ten entities/72 static/zero TS/fifteen relationships and the same Lakehouse mappings. This accepts creation/definition readback, not consumer compatibility."),
        p(
            "その後のworker receiptはmanaged Graph refresh Completedとnative GQL3/3、109,592 nodes/297,303 directed edges、全10/15labelsを報告しています。Source書込・Agent呼出はなく、primary generation2は保持されています。この独立Graph受入れもData Agent consumerが動作する証明に昇格しません。",
            "A subsequent worker receipt records managed Graph refresh Completed and native GQL3/3,109,592 nodes/297,303 directed edges and all ten/fifteen labels. There were no source writes or agent calls, and the primary generation2 items remain protected. This independent Graph acceptance still does not prove the Data Agent consumer works."),
        note(
            "actual generation/readback、Graph、別Compat consumerのGQL成功は確認済みですが、元84条件の品質合格ではありません。bridgeは明示opt-inのconsumer用途だけで、implicit generation1 fallback/default downgradeは行いません。primary/new-UI generation2とnative Metrics/TSを保持し、変更scope・新規承認plan・readback・consumer実行を個別に検証します。",
            "Actual generation/readback, Graph and GQL on the separate Compat consumer are verified, but the original84 quality gate is not accepted. The bridge is an explicit opt-in consumer path, never an implicit generation1 fallback/default downgrade. Preserve primary/new-UI generation2 and native Metrics/TS; separately verify changed scope, a fresh approved plan, readback and consumer execution.",
            "gate"),
        p(
            "任意bridgeのportable helperとNotebook02–04は所有者が再sealしました。prepareとagent-handoffはoffline snapshot/plan検査で、cloud apply transportは追加していません。Gen1 create・native Graph・Agent作成/Publish/質問は別承認のoperator工程です。main promotionは行っていません。",
            "The owner resealed the optional bridge helper and Notebook02–04. prepare and agent-handoff validate offline snapshots/plans; no cloud-apply transport was added. Gen1 creation, native Graph and Agent creation/publication/questions remain separately approved operator stages. Main has not been promoted."),
        code(
            'python .\\tools\\provisioning\\preview30_compatibility.py prepare `\n'
            '  --environment dev --scope "<private-scope.json>" `\n'
            '  --inventory "<private-inventory.json>" --owned-state "<private-state.json>" `\n'
            '  --temp-folder-id "<approved-Temp-folder>" --output-dir "<fresh-private-plan>"\n\n'
            'python .\\tools\\provisioning\\preview30_compatibility.py agent-handoff `\n'
            '  --environment dev --scope "<private-scope.json>" `\n'
            '  --inventory "<private-inventory.json>" --owned-state "<private-state.json>" `\n'
            '  --temp-folder-id "<approved-Temp-folder>" `\n'
            '  --compat-receipt "<owned-create-receipt.json>" `\n'
            '  --compat-definition "<native-definition.json>" `\n'
            '  --graph-evidence "<native-graph-result.json>" `\n'
            '  --frozen-agent-definition "<frozen-agent-definition.json>" `\n'
            '  --stage published --output-dir "<fresh-private-handoff>"',
            "PowerShell — explicit offline opt-in handoff",
        ),
        note(
            "handoffはOntology artifactId/displayName/userDescriptionだけを変更する候補を準備し、datasource相対path、Entity/property選択、source instructions、LH/KQL/direct SemanticModel、CI、GLOBAL bytesを保持します。72-static選択を要求し、TS選択を黙って修正しません。published stageを出力せず、自動promotionやbenchmark合格も主張しません。",
            "Handoff prepares a candidate changing only ontology artifactId/displayName/userDescription, preserving datasource-relative path, entity/property selection, source instructions, LH/KQL/direct SemanticModel, CI and exact GLOBAL bytes. It requires a72-static selection and refuses rather than silently repairs TS selection. It emits no published stage and claims no automatic promotion or benchmark acceptance.",
            "gate"),
        p(CREATE_DOC, CREATE_DOC),
    ])
    if selected_run is not None:
        compatibility_history.blocks.insert(0, note(
            "以下のreadback・consumer・品質の状態は保存した旧scopeの履歴です。選択runの互換性や品質の新規確認ではありません。現在の選択は19.10節だけで判定します。",
            "The readback, consumer and quality states below retain the old historical scope, not new compatibility/quality checks of the selected run. Its current selection is assessed only in19.10.",
            "gate",
        ))


def selected_original_suite_sections(roots, evidence):
    run = preview30_public_evidence.selected_original_suite_run(evidence, required=True)
    chapter = next(section for section in roots if section.chapter == 19)
    sub(chapter, "4", ("source-owned元84条件の履歴と明示選択", "Source-owned original84 history and explicit selection"), [
        p(
            "審査済みsource aggregateを元の順序・分母のまま保持します。最高点・最新時刻で選ばず、UI/SDK/smoke診断を元suiteへ加算しません。",
            "Retain reviewed source aggregates in their original order and denominators. Do not choose the highest score/latest timestamp or add UI/SDK/smoke diagnostics to the original suite."),
        table(
            [("Run", "Run"), ("選択", "Selection"), "PASS / FAIL / U / B / N/A", ("受入/promotion（記録）", "Accepted/promoted, recorded")],
            [
                [(item["label"]["ja"], item["label"]["en"]),
                 ("明示選択", "Explicitly selected") if item["id"] == run["id"] else ("保存履歴", "Retained history"),
                 " / ".join(str(item["counts"][key]) for key in preview30_reporting.VERDICT_KEYS),
                 f"{item['accepted']} / {item['promoted']}"]
                for item in evidence["originalSuiteRuns"]
            ],
            ("元10問/84条件。選択は受入・promotionではない", "Original ten/84; selection is not acceptance or promotion")),
    ])
    sub(chapter, "5", ("明示選択した審査済みAI aggregate", "Explicitly selected reviewed AI aggregate"), [
        p(*preview30_reporting.selection_notice(run)),
        note(run["summary"]["ja"], run["summary"]["en"], "gate"),
        p(
            "public projectionの承認は公開可能な集計の審査です。84 PASSから受入flagを推測せず、元のvalidatorと審査記録だけを使います。",
            "Approval of the public projection reviews publishable aggregates. Do not infer an acceptance flag from84 PASS; use only the unchanged validator and reviewed record."),
    ])
    blocks = [
        p(*preview30_reporting.selection_notice(run)),
        table([("記録", "Record"), ("値", "Value")], preview30_reporting.method_rows(run),
              ("試行・成功・拒否、trace slot、別会話、native完了は別の分母", "Attempts, successes, rejections, traced slots, distinct conversations and native completion differ")),
        table(
            [("言語", "Language"), ("試行", "Attempts"), ("成功", "Successes"), ("拒否", "Rejections")],
            preview30_reporting.source_rows(run),
            ("DAXは独立。未提供は未検証でゼロではない", "DAX is separate; missing values are unverified, not zero")),
        note(*preview30_reporting.execution_completeness_notice(), "gate"),
        table(
            ["Case", "PASS", "FAIL", ("未検証", "Unverified"), "BLOCKED", "N/A", ("native gate", "Native gate")],
            preview30_reporting.case_verdict_rows(run),
            ("選択runの10 ordered casesだけ。旧CASE_ROWSを借用しない", "Only the selected run's ten ordered cases; no legacy CASE_ROWS reuse")),
        table(
            ["Case", ("試行", "Attempts"), ("成功", "Successes"), ("拒否", "Rejections"),
             ("native応答終端", "Native response terminal state"), ("成功query言語", "Successful query languages")],
            preview30_reporting.case_execution_rows(run),
            ("native固定blockは受入FAIL。完了応答とquery成功を混同しない", "Native fixed blocks are acceptance FAILs; completion is not query success")),
        note(
            "native固定blockはFAILのままで、適切なcontextual refusalへ置換しません。実行回数は一般母集団の正確性・因果MCP A/Bを証明せず、case集計から欠陥原因やfeature修復を推測しません。",
            "A native fixed block remains FAIL, not successful contextual refusal. Call counts prove neither general-population accuracy nor a direct causal MCP A/B; case aggregates do not diagnose defects or prove feature repair.",
            "gate"),
    ]
    if "notApplicableReason" in run:
        blocks.append(note(run["notApplicableReason"]["ja"], run["notApplicableReason"]["en"], "gate"))
    blocks += [
        note(value["reason"]["ja"], value["reason"]["en"], "gate")
        for value in preview30_reporting.selected_context().values()
    ]
    blocks.append(note(
        "元suiteの審査記録上の受入と最終user受入・全機能合格は別です。残る演習の実証と別の明示承認が必要で、publicationは延期のままです。文書作業は再質問・データ/モデル変更・promotionを行いません。",
        "Reviewed original-suite acceptance is separate from final user/all-feature acceptance. Actual remaining-feature evidence and separate explicit approval are required; publication remains deferred. Document work performs no question, data/model change or promotion.",
        "stop"))
    sub(chapter, "10", ("選択runの判定・実行・未確認の境界", "Selected decisions, executions and unverified boundaries"), blocks)


def original_suite_run_sections(roots, runs, *, evidence=None):
    if evidence is not None and "selectedOriginalSuiteRunId" in evidence:
        selected = preview30_public_evidence.selected_original_suite_run(evidence, required=True)
        if selected["id"] != preview30_public_evidence.LEGACY_ORIGINAL_SUITE_RUN_ID:
            selected_original_suite_sections(roots, evidence)
            return
    chapter = next(section for section in roots if section.chapter == 19)
    sub(chapter, "4", ("元84条件の履歴を新runへ流用しない", "Do not reuse historical original84 grades for a new run"), [
        table(
            [("観測run", "Observed run"), "PASS", "FAIL", ("実行未検証", "Execution unverified"), "BLOCKED", "N/A"],
            [
                [("初期main baseline（履歴）", "Initial main baseline (historical)"), "9", "23", "1", "51", "0"],
                [("隔離StaticFirst（履歴・未promotion）", "Isolated StaticFirst (historical, not promoted)"), "22", "10", "1", "51", "0"],
                [("隔離Context published-MCP（未promotion）", "Isolated Context published-MCP (not promoted)"), "39", "38", "4", "0", "3"],
                [("最終Compat NativeUI（品質未合格・未promotion）", "Final Compat NativeUI (quality not accepted, not promoted)"), "48", "36", "0", "0", "0"],
            ], ("各84条件。N/Aも分母に保持し、後続UI/SDK診断と合算しない", "Each retains84 conditions including N/A; do not combine later UI/SDK diagnostics")),
        note(
            "StaticFirstのFAIL10はT08内容不足3＋T10 native content blockの受入失敗7で、適切な文脈付き拒否ではありません。この履歴を最終Context候補の合格へ置換せず、CI/Graph/TS/添付smokeにも元84条件のcreditを与えません。",
            "StaticFirst's ten FAILs comprise three T08 content deficiencies and seven T10 native-content-block acceptance failures, not correct contextual refusal. Do not substitute this history for final Context-candidate acceptance or award original84 credit to CI/Graph/TS/attachment smoke tests.",
            "gate"),
        note(
            "Contextは10問を各1回、前提skip0、通常業務回答9＋native platform block1でした。FAIL38はcontent31＋native acceptance7、独立source実行proof0、fresh backend proof未取得です。39+38+4+3=84を維持し、N/A3を消して81条件の合格率へ置換しません。Graph readinessの改善とconsumer connector互換性は別です。",
            "Context submitted ten questions once with zero precondition skips, nine valid business answers and one native platform block. Its38 FAILs comprise31 content and seven native-acceptance failures; independent source-execution proof is zero and fresh-backend proof absent. Retain39+38+4+3=84; do not drop three N/A into an81-condition pass-rate claim. Improved Graph readiness is separate from consumer-connector compatibility.",
            "gate"),
    ])
    blocks = [p(
        "最終候補は別の凍結runです。配布sourceの審査済みpublic projectionに含まれる集計だけを下へ表示します。回答・期待値・condition原文・内部reasoningを公開しません。未提供の結果、84/84、main promotionを推測しません。",
        "The final candidate is a separately frozen run. Only approved aggregates in the source-owned public projection appear below. Do not publish answers, expected values, verbatim conditions or internal reasoning; infer no missing results,84/84 or main promotion.",
    )]
    if runs:
        blocks.append(table(
            [("Run", "Run"), ("送信/前提blocked", "Submitted/preblocked"), "P / F / U / B / N/A", ("native失敗/trace", "Native failures/traces"), ("受入/promotion", "Accepted/promoted")],
            [[(run["label"]["ja"], run["label"]["en"]), f"{run['submittedQuestions']} / {run['preblockedQuestions']}",
              " / ".join(str(run["counts"].get(key, 0)) for key in ("pass", "fail", "executionUnverified", "blocked", "notApplicable")),
              f"{run['failureCounts']['nativeAcceptance']} / {run['independentExecutionTraces']}",
              f"{run['accepted']} / {run['promoted']}"] for run in runs],
            ("原10問/84条件の分母を固定した承認済み集計", "Approved aggregates retaining the original ten/84 denominators"),
        ))
        for run in runs:
            blocks.append(note(run["summary"]["ja"], run["summary"]["en"], "gate"))
    else:
        blocks.append(note(
            "最終freeze用の承認済みaggregate projectionは未提供です。既存Context MCP runは上の履歴に保持し、consumer互換性/UI/SDK資格確認の進行中結果を推測しません。文書sourceの準備完了はrelease freezeや全機能合格ではありません。",
            "No approved final-freeze aggregate projection is supplied. The completed Context MCP run remains in the history above; do not infer outcomes of ongoing consumer-compatibility/UI/SDK qualification. Prepared document source is not release freeze or all-feature acceptance.",
            "gate",
        ))
    sub(chapter, "5", ("凍結AI runの公開可能な集計", "Publishable aggregates of frozen AI runs"), blocks)
    sub(chapter, "10", ("最終評価の方法・残る欠陥・改善の境界", "Final evaluation method, residual defects and remediation boundaries"), [
        p(
            "最終CompatはNativeUI/responses/sandbox/previewの観測runで、48 PASS＋36 FAIL＝84、N/A/実行未検証/前提blockedは0です。判定はcoordinatorによるmanual fixed-rubric offline judgmentで、新しいAI critic呼出や再質問はありません。過去published-MCP runとはtransport/候補/観測条件が異なるため、直接の因果MCP A/Bや一般母集団の正確性を主張しません。",
            "Final Compat is the observed NativeUI/responses/sandbox/preview run:48 PASS+36 FAIL=84, with zero N/A/execution-unverified/preblocked. Judgment was the coordinator's manual fixed-rubric offline assessment, without new AI critic calls or resubmissions. Transport/candidate/observation conditions differ from historical published-MCP runs; this is not a direct causal MCP A/B or general-population accuracy claim."),
        table(
            [("残る論点", "Residual category"), ("改善提案（今回未実行）", "Remediation recommendation, not executed in this freeze")],
            [
                [("T04 集約grain/表現", "T04 aggregation grain/presentation"), ("要求した親粒度でengine集約し、child列の結果を親集計と誤認しない。必要な関係/方向の説明を確認。", "Aggregate at the requested parent grain; do not substitute child-level rows. Check required relationship/direction presentation.")],
                [("T05 ID/source証拠", "T05 IDs/source evidence"), ("必要なbusiness IDsとlabelsを選択projectionへ含め、実source証拠を明示。", "Include required business IDs with labels and explicit actual-source attribution.")],
                [("T06/T07 期間", "T06/T07 time window"), ("operational sourceの年/月を実queryで確認し、static dataset年を仮定しない。観測時刻と取込時刻を分ける。", "Discover operational source year/month rather than assuming the static dataset year; distinguish observation from ingestion time.")],
                [("T08 指標/経路", "T08 measures/path"), ("別々の件数・金額・scopeを明示し、モデル化されたDonation経路で照合。", "Label separate counts, amounts and scopes; reconcile through the modeled Donation path.")],
                [("T09 cross-source", "T09 cross-source"), ("定義済みscopeで必要な横断回答を返し、根拠のないclarificationだけへ置換しない。", "Produce the requested cross-source result under the defined scope, not an unsupported clarification-only substitute.")],
                [("T10 native gate", "T10 native gate"), ("7 FAILはnative gateによる受入失敗で、適切なcontextual refusalや7虚偽主張の採点ではない。blockerを保存し、bypassしない。", "Seven FAILs are native-gate acceptance failures, not correct contextual refusal or seven adjudicated false claims. Preserve the blocker; do not bypass it.")],
            ], ("29内容/要求証拠FAIL＋7 native-gate FAIL。今後の修正は別scope/新評価", "29 content/required-evidence FAILs plus seven native-gate FAILs; future changes need separate scope/evaluation")),
        note(
            "mainは未promotionです。これは実装・検証結果と既知の制約を収録するPreviewで、AI回答品質承認やGAではありません。評価記録とruntime/Notebookの版を固定し、同じ公開用原稿からWord・HTMLを生成して整合性を検査します。文書の訂正によって評価結果を変更したり、追加のAI評価を実行したりしません。stable v2.7配布物は置換しません。",
            "Main is not promoted. This Preview records implementation/verification results and known limitations; it is not AI-quality approval or GA. Evaluation records and runtime/Notebook versions are frozen. Word and HTML use the same reviewed public source and are checked for consistency. Editorial corrections do not change the recorded scores or run additional AI evaluations. Stable v2.7 artifacts are not replaced.",
            "stop"),
    ])


def evaluation_sections(roots, projection):
    if projection is None:
        return
    chapter = next(section for section in roots if section.chapter == 19)
    pending = sum(row["support"] == "pending" for row in projection["inventory"])
    ai = projection["ai"]
    sub(chapter, "6", ("過去の独立評価snapshot（現在結果とは分離）", "Historical independent-evaluation snapshot, separate from current results"), [
        note(
            "以下はlive追加3問より前のoffline snapshotです。blocked/未採点という当時の分母を保存するもので、現在の認証・配置・実回答を全blockedと判定し直しません。現在の限定的な回答一致は19.8節で別に示します。",
            "This offline snapshot predates the three-question live batch. It preserves the historical blocked/unscored denominators; it does not reclassify current authentication, deployment or actual answers as all blocked. Current scoped answer agreement is reported separately in 19.8.",
            "gate"),
        p(
            "評価担当の既存furusato-preview30-report/v1から許可された集計だけを取り込みます。snapshot生成時刻: " + projection["generated_at_utc"] + "。これは当時の記録であり、現在の認証や配置状態を推定しません。private context、理由/error、証拠、path/ID、prompt、trace、held-out corpusは掲載しません。",
            "Only approved aggregates are projected from the evaluator's existing furusato-preview30-report/v1. Snapshot generated: " + projection["generated_at_utc"] + ". It records that time, not inferred current authentication/deployment. Private context, reasons/errors, evidence, paths/IDs, prompts, traces and held-out corpora are excluded."),
        table(
            [("集計", "Aggregate"), ("原レポートの値", "Source-report value")],
            [
                [("Cases", "Cases"), str(projection["case_count"])],
                [("要求slots", "Requested slots"), str(projection["requested_slots"])],
                [("確認済みsupported slots", "Confirmed supported slots"), str(projection["supported_requested_slots"])],
                [("適用判定pending slots", "Applicability-pending slots"), str(pending)],
                [("Supported pass / fail", "Supported pass / fail"), f"{projection['supported_pass']} / {projection['supported_fail']}"],
                [("Supported証拠不足", "Supported missing evidence"), str(projection["supported_missing_evidence"])],
                [("AI要求 / supported / 採点済み", "AI requested / supported / scored"), f"{ai['requested_questions']} / {ai['supported_requested_questions']} / {ai['scored_questions']}"],
                [("AI pass / supported未採点", "AI pass / supported unscored"), f"{ai['pass']} / {ai['missing_supported_questions']}"],
                [("AI accuracy", "AI accuracy"), ("未確定 / null", "Withheld / null") if ai["accuracy"] is None else str(ai["accuracy"])],
            ], ("local検査数や生成質問をAI採点へ変換しない", "Do not convert local tests or generated questions into AI scores")),
        note(
            f"適用判定pendingは{pending} slotです。pendingがあるときのsupported_requested_slots=0はUNKNOWN（未確定）であり、「対応機能が0件」ではありません。scored_questions=0・accuracy=nullは未採点で、0%正答率ではありません。blocked/unsupported/unverifiedを分母から消して合格率を作りません。",
            f"Applicability is pending for {pending} slots. When pending exists, supported_requested_slots=0 means UNKNOWN, not zero supported features. scored_questions=0 with accuracy=null means unscored, not 0% accuracy. Never drop blocked/unsupported/unverified slots to manufacture a pass rate.",
            "gate"),
        table(
            [("状態", "State"), ("Slots", "Slots")],
            [[state, str(count)] for state, count in projection["state_counts"].items()],
            ("planned/implemented/deployedとpassは別", "Planned/implemented/deployed are not pass")),
        p(
            "元の公開10問/84条件は独立hiddenではありません。元summaryのstate: " + projection["original_inventory"]["state"] + "。独立held-outの質問と鍵は評価担当のprivate領域だけに残し、このガイド・添付・few-shotへコピーしません。",
            "The original public ten questions / 84 conditions are not an independent hidden corpus. Original-summary state: " + projection["original_inventory"]["state"] + ". Independently held-out questions and keys stay with the evaluator privately; never copy them into this guide, attachments or few-shots."),
    ])
    sub(chapter, "7", ("case/slotの公開可能な状態索引", "Publishable case/slot status inventory"), [
        table(
            ["case_id", "repeat", "category", "critical", "state", "support"],
            [[str(row[key]) for key in preview30_evaluation.INVENTORY_FIELDS] for row in projection["inventory"]],
            ("IDと判定だけ。質問・理由・traceは含めない", "Identifiers and states only; no questions, reasons or traces")),
    ])


def evaluation100_sections(roots, study, study_sha):
    rounds = [(("Baseline development80", "Baseline development80"), study["baseline"])]
    if study["intervention"] is not None:
        rounds.append((("単一intervention development80", "Single intervention development80"), study["intervention"]["run"]))
    rounds += [(("Heldout20 (最終候補)", "Heldout20 (final candidate)"), study["heldout"]),
               (("Combined100 (最終候補)", "Combined100 (final candidate)"), study["combined"])]
    axis_labels = {
        "factualCorrectness": ("事実の正しさ", "Factual correctness"),
        "contextualHelpfulness": ("文脈に沿った有用性", "Contextual helpfulness"),
        "protectiveBoundary": ("保護境界", "Protective boundary"),
        "answerContent": ("回答内容", "Answer content"),
    }

    def verdict_text(counts):
        return " / ".join(str(counts[key]) if key in counts else "-" for key in ("pass", "fail", "unknown", "notApplicable"))

    notice = study100.notice(study)
    blocks = [
        note(notice["ja"], notice["en"], "gate"),
        note(
            "審査の時系列上の制約: METHOD timingはoperator receiptとfilesystemによるcorroborationであり、独立した事前登録の証明ではありません。記録時刻08:24:25の原prep resultにはcandidate SHA・definition SHA・準備時点の0 questionsがあり、原method-intent hashやeventIdはありません。intentのmtimeと宣言されたfrozenAtはplan08:24:55/run08:25:23より前ですが、これは独立証明ではありません。原result/intentをverbatimで保持し、証拠hashはadmission時に計算 (computedAtAdmission) します。methodTimingIndependentlyCertified=false、methodPreregistered=false、fullReviewPolicyPreregistered=false、reviewToolingPreregistered=falseです。準備時点の0は後続captureの送信数ではありません。",
            "REVIEW TIMING LIMITATION: METHOD timing is corroborated by the operator receipt and filesystem, NOT independently proven preregistration. At recorded time08:24:25 the original prep result contains candidate SHA, definition SHA and zero questions at preparation, but no original method-intent hash or eventId. Intent mtime and declared frozenAt precede plan08:24:55/run08:25:23; this is corroboration, not independent proof. Preserve the original result/intent verbatim; evidence hashes are computed at admission (computedAtAdmission), not backdated. methodTimingIndependentlyCertified=false, methodPreregistered=false, fullReviewPolicyPreregistered=false and reviewToolingPreregistered=false. Preparation's zero is not the later capture submission count.",
            "stop"),
        p(
            "methodは全固定criteriaをcaseごとのoracleと実応答の正確なspansに照らして審査し、人間のsign-off・heuristic置換・best-of poolingを使いません。tooling/policy-codeはcapture中に完成しました。既存reviewPolicyTiming文字列は互換labelであり事前登録の認定ではありません。timing admissionは内容審査より前に必要です。corroborationの開示は原capture plan・candidate・spent claimsの編集、reset、replan、再質問を許可せず、criteria・records・countsを変更しません。",
            "The method requires case-by-case review against the oracle and exact native spans for every frozen criterion, with no human sign-off, heuristic substitution or best-of pooling. Tooling/policy-code was finalized during capture. The retained reviewPolicyTiming string is a compatibility label, not a preregistration certification. Timing admission must precede content grading. Corroboration disclosure does not authorize editing, resetting or replanning the original capture plan, candidate or spent claims, resubmitting questions, or changing criteria, records or counts."),
        p(
            "この追加研究は100 unique cases = development80 + heldout20です。元10問/84条件、旧14/0・13/0の診断、既存の公開履歴とは合算・置換しません。baseline80と任意の単一intervention80は別々に表示し、改善を仮定しません。",
            "This additional study retains 100 unique cases = development80 + heldout20. It neither pools with nor replaces the original ten/84, old14/0 or13/0 diagnostics, or existing published histories. Baseline80 and the optional single intervention80 are separate; improvement is not assumed."),
        p(
            "各slotは宣言したroundで最大1試行です。baselineのnative blockはinterventionで再送せず、protectedとして80/100の分母に残します。最終候補をfreezeしてからheldout20を不可逆に予約し、heldoutによる調整・再試行・best-of pooling・baseline成功回答の借用を禁止します。",
            "Each slot allows at most one attempt in its declared round. Baseline native blocks are not resubmitted in the intervention and remain protected in the80/100 denominators. Freeze the final candidate before irreversibly reserving heldout20; no heldout tuning, retries, best-of pooling or borrowed baseline successes."),
        p(
            "最終development round: " + study["final"]["developmentRound"] + "。combined100はこのround80と同一candidateのheldout20だけを加算します。異なる候補の良い結果を選んで合算しません。",
            "Final development round: " + study["final"]["developmentRound"] + ". Combined100 adds only this round80 and heldout20 of the identical candidate, never the better answers from different candidates."),
        table(
            [("Round", "Round"), ("unique / terminal", "Unique / terminal"),
             ("送信intent", "Submission intents"), ("捕捉応答", "Captured responses"),
             ("新native block", "New native blocks"), ("不明な送信結果", "Unknown submission outcomes")],
            [[name, f"{run['metrics']['uniqueCases']} / {run['metrics']['terminalCases']}",
              run["metrics"]["submissionIntents"], run["metrics"]["capturedResponses"],
              run["metrics"]["nativeBlocks"], run["metrics"]["unknownOutcomes"]] for name, run in rounds],
            ("Intentはdelivery/query成功の証明ではない。terminalには失敗・不明も含む", "Intent is not delivery/query success; terminal includes failed and unknown outcomes")),
        table(
            [("Round", "Round"), ("応答 / block / error / 保護 / 未送信 / 不確実 / 捕捉失敗",
                                   "Answer / block / error / protected / unsent / uncertain / capture failure")],
            [[name, " / ".join(str(run["metrics"]["terminalCounts"][key]) for key in study100.TERMINALS)] for name, run in rounds],
            ("相互排他的なterminal分類。native errorも内容正解ではない", "Disjoint terminal accounting; a native error is not a correct answer")),
        table(
            [("Round", "Round"), ("判定軸", "Result axis"), "PASS / FAIL / UNKNOWN / N/A",
             ("新規 / 保持service block", "New / retained service block")],
            [[name, axis_labels[axis], verdict_text(run["metrics"]["axes"][axis]),
              f"{run['metrics']['axes'][axis]['nativeServiceBlock']} / {run['metrics']['axes'][axis]['retainedServiceBlock']}"
              if axis == "protectiveBoundary" else "-"] for name, run in rounds for axis in study100.AXES],
            ("各軸は全分母を保持。service blockは保護の観測でありPASSではない", "Every axis retains the whole denominator; service blocks are protective observations, not PASS")),
        note(
            "PASS0とUNKNOWNがある状態は0%正確性ではありません。未捕捉・未審査・native blockを事実PASSやN/Aへ変換せず、割合を補完しません。AI-assisted reviewは元の固定rubricとは別の実際の審査方法であり、独立した人間のsign-offはありません。引用一致や自動文書検査も意味的正解の自動判定ではありません。",
            "Zero PASS with UNKNOWN is not zero-percent accuracy. Do not turn uncaptured/unreviewed/native-blocked outcomes into factual PASS or N/A, or fill in a rate. AI-assisted review is the actual judgment method, separate from the unchanged frozen rubric; there is no independent human sign-off. Quote matching and document checks do not automatically establish semantic correctness.",
            "gate"),
        note(
            "Published MCPはANSWER_ONLYです。回答文はnative GQL/DAX/SQL/KQL実行、返却row、呼出数、別backend会話の証明ではなく、内部query・backend conversationのproofはUNOBSERVABLEです。一般母集団の正確性、因果的A/B、GA、全機能受入、main/Agent promotionは主張しません。",
            "Published MCP is ANSWER_ONLY. Answer text proves neither native GQL/DAX/SQL/KQL execution, returned rows, call counts nor distinct backend conversations: internal-query and backend-conversation proof remains UNOBSERVABLE. No general-population accuracy, causal A/B, GA, all-feature acceptance or main/Agent promotion is claimed.",
            "stop"),
    ]
    if "executionProtocol" in study:
        execution = study["executionProtocol"]
        continued = execution["continuationTerminalCounts"]
        heldout_metrics = study["heldout"]["metrics"]
        blocks[1:1] = [
            note(
                "停止後の実行protocol変更: post-stop-unsent-slots-only。事前登録されたresume機構ではありません (executionAmendmentPreregistered=false)。元の一律no-resume ruleを変更したためoriginalNoResumePolicyAmended=true / originalProtocolWasFullyFollowed=falseです。先の2 capturesとHTTP500による1 unknownを保持し、その不確実slotは再送しません。元planの未送信17 slotsだけの初回送信を、最大1回のcontinuation invocationで実施し、次の失敗・native block・不確実な送信で停止します。",
                "POST-STOP EXECUTION-PROTOCOL AMENDMENT: post-stop-unsent-slots-only, NOT a preregistered resume mechanism (executionAmendmentPreregistered=false). The original blanket no-resume rule WAS amended: originalNoResumePolicyAmended=true / originalProtocolWasFullyFollowed=false. Retain the prior2 captures and one HTTP500 UNKNOWN; never replay that uncertain slot. Only the17 never-submitted slots from the original plan may receive their first submission, in at most one continuation invocation, stopping on the next failure, native block or uncertain submission.",
                "stop"),
            table(
                [("Amendment accounting", "Amendment accounting"), ("公開記録", "Public record")],
                [
                    [("元heldout分母 / 先のcapture / 先のunknown / 継続対象", "Original heldout denominator / prior captures / prior unknown / eligible"),
                     f"20 / {execution['priorCaptured']} / {execution['priorUnknown']} / {execution['eligibleUnsent']}"],
                    [("Continuation invocation / outcome", "Continuation invocation / outcome"),
                     f"{execution['continuationInvocations']} / {execution['outcome']}"],
                    [("継続17の応答 / block / error / 保護 / 未送信 / 不確実 / 捕捉失敗",
                      "Continuation17: answer / block / error / protected / unsent / uncertain / capture failure"),
                     " / ".join(str(continued[key]) for key in study100.TERMINALS)],
                    [("照合後heldoutの応答 / block / error / 保護 / 未送信 / 不確実 / 捕捉失敗",
                      "Reconciled heldout: answer / block / error / protected / unsent / uncertain / capture failure"),
                     " / ".join(str(heldout_metrics["terminalCounts"][key]) for key in study100.TERMINALS)],
                    [("Heldout submission intents / captured responses / unknown outcomes",
                      "Heldout submission intents / captured responses / unknown outcomes"),
                     f"{heldout_metrics['submissionIntents']} / {heldout_metrics['capturedResponses']} / {heldout_metrics['unknownOutcomes']}"],
                ],
                ("captureと正答は別。19 captures +1 unknownが上限であり20 successful answersではない",
                 "Capture is not correctness; the ceiling is19 captures +1 unknown, never20 successful answers")),
            note(
                "元batchはstopped_fail_closedのままbyteを保持し、新reconciliation/reportだけで追加の初回送信を照合します。全20 original claimsはspentのままです。retrySubmittedOrUncertainCases=false、sourceTransportCandidateOrQuestionChanges=false、heldoutFeedbackTuning=false、noBestOf=trueを保持します。journal内に送信記録が無いことだけはout-of-band送信不在の独立証明ではなく、元run停止・別送信無しのparent attestationが必要です。失敗時の後続未送信slotも20/100の分母から消しません。durableなterminal result/reconciliationが無い場合は文書も停止し、回復receiptや成功を作りません。",
                "Preserve the original batch bytes as stopped_fail_closed; only a separate reconciliation/report accounts for additional first submissions. All20 original claims remain spent. Retain retrySubmittedOrUncertainCases=false, sourceTransportCandidateOrQuestionChanges=false, heldoutFeedbackTuning=false and noBestOf=true. Journal absence alone is not independent proof of no out-of-band submission: parent attestation that the original run stopped and no other submission occurred is required. Later unsent slots after failure remain in the20/100 denominators. Without a durable terminal result/reconciliation, the document gate also stops; invent no recovery receipt or success.",
                "gate"),
        ]
    if "buckets" in study["baseline"]:
        blocks.append(table(
            [("Round / bucket", "Round / bucket"), ("分母", "Denominator"), ("判定軸", "Result axis"),
             "PASS / FAIL / UNKNOWN / N/A", ("新規 / 保持block", "New / retained block")],
            [[(name[0] + " / " + bucket["label"], name[1] + " / " + bucket["label"]),
              bucket["metrics"]["uniqueCases"], axis_labels[axis], verdict_text(bucket["metrics"]["axes"][axis]),
              f"{bucket['metrics']['axes'][axis]['nativeServiceBlock']} / {bucket['metrics']['axes'][axis]['retainedServiceBlock']}"
              if axis == "protectiveBoundary" else "-"]
             for name, run in rounds for bucket in run["buckets"] for axis in study100.AXES],
            ("任意bucketも同じ最終候補・分母・集計規則。private case本文は含めない", "Optional buckets use the same final candidate, denominators and aggregation; no private case text")))
    sub(next(s for s in roots if s.chapter == 19), "11",
        (study["snapshotDate"] + " frozen100追加検証", study["snapshotDate"] + " additional frozen100 validation"), blocks)
    binding_rows = [
        ["Public study SHA256", study_sha], ["Suite/source/rubric binding SHA256", study["bindingSha256"]],
        *[[key, value] for key, value in study["bindings"].items() if key != "sourceFileHashes"],
        ["Bound source-file count", len(study["bindings"]["sourceFileHashes"])],
        ["Method timing evidence", study["review"]["methodTimingEvidence"]],
        ["Method preregistration claim", study["review"]["methodPreregistrationClaim"]],
        ["Method timing independently certified / method preregistered", "false / false"],
        ["Original method timing corroborated", "true"],
        ["Method-evidence hash provenance", study["review"]["methodEvidenceHashProvenance"]],
        ["Preserved METHOD intent SHA256 (computed at admission)", study["review"]["methodIntentSha256"]],
        ["Retained timing label (not preregistration proof)", study["review"]["reviewPolicyTiming"]],
        ["Full review policy / review tooling preregistered", "false / false"],
        ["Timing admission receipt SHA256", study["review"]["timingAdmissionReceiptSha256"]],
        ["Review policy SHA256 (finalized during capture)", study["review"]["policySha256"]],
        ["Final freeze receipt SHA256", study["final"]["freezeReceiptSha256"]],
        ["Irreversible heldout claim SHA256", study["final"]["heldoutClaimSha256"]],
    ]
    if "executionProtocol" in study:
        amendment_binding = study100.execution_binding(study)
        binding_rows += [
            ["Execution amendment SHA256", amendment_binding["executionProtocolSha256"]],
            *[[key, value] for key, value in amendment_binding["executionProtocolHashes"].items()],
        ]
    for name, run in rounds:
        binding_rows += [
            [(name[0] + " profile", name[1] + " profile"), run["candidate"]["profileLabel"]],
            [(name[0] + " candidate SHA256", name[1] + " candidate SHA256"), run["candidate"]["candidateSha256"]],
            [(name[0] + " definition SHA256", name[1] + " definition SHA256"), run["candidate"]["definitionSha256"]],
            [(name[0] + " report SHA256", name[1] + " report SHA256"), run["sourceReportSha256"]],
        ]
    sub(next(s for s in roots if s.chapter == 24), "11",
        ("公開後snapshotの再現境界", "Post-release snapshot reproduction boundaries"), [
            p(
                "追加studyはcounts/hash/public profileだけの投影です。docbuilderが検証するのはschema・算術・宣言hashの整合性で、private ledgerや実環境の再実行・再採点ではありません。sourceFileHashesの公開labelはパスではなく、各digestとsuite/rubric/splitのbindingを投影内に保持します。",
                "The additional study projects only counts, hashes and public profiles. The docbuilder checks schema, arithmetic and declared hash consistency, not the private ledger or a new live run/regrade. Public sourceFileHashes labels are not paths; the projection retains each digest and its suite/rubric/split binding."),
            note(
                "method証拠のhash bindingはadmission時にhashした保存済みresult/intentを識別し、原prep resultに無かったmethod hash/eventIdを補ったり、capture planを書き換えたりしません。candidate/definitionの原SHAとadmission時に計算したmethod証拠hashを区別します。method timingのcorroborationは独立認定ではありません。timing admission前の内容審査は認めず、captureと内容採点を別段階として保持します。",
                "Method-evidence hash bindings identify the preserved result/intent as hashed at admission; they do not add a missing method hash/eventId to the original prep result or rewrite the capture plan. Distinguish the originally recorded candidate/definition SHAs from method-evidence hashes computed at admission. Method-timing corroboration is not independent certification. No content grading before timing admission; capture and content grading remain separate stages.",
                "gate"),
            table([("Binding", "Binding"), ("公開値", "Public value")], binding_rows,
                  ("私有原本の場所や識別子を公開せずexact-byte投影にbindする", "Bind the exact-byte projection without disclosing private source locations or identities")),
            table(
                [("配置・運用の別観測", "Separate deployment observation"), ("2026-10-02に記録された範囲", "Scope recorded on 2026-10-02")],
                [
                    [("Pipeline Copy", "Pipeline Copy"),
                     ("3 Copyは各1回Completed、各5,000行。manual3 / automatic0。元の安全なPipeline defaultsは復元済みです。",
                      "Three Copies each Completed exactly once with 5,000 rows each: manual 3 / automatic 0. Original safe Pipeline defaults were restored.")],
                    [("Raw KQL", "Raw KQL"), ("15,000行 /253,886,000 JPYを確認。", "15,000 rows /253,886,000 JPY verified.")],
                    [("EventID照合", "EventID reconciliation"),
                     ("exact14900の受入EventIDs /252,058,000 JPYと100 duplicatesを確認。",
                      "Exact 14,900 accepted EventIDs /252,058,000 JPY and 100 duplicates verified.")],
                    [("Isolated AgentCompat", "Isolated AgentCompat"),
                     ("published版のnative Published UIで10 entitiesがwarningなしで表示されました。",
                      "The published isolated AgentCompat loaded all 10 entities in native Published UI without a warning.")],
                    [("Primary gen2 / main Agent", "Primary gen2 / main Agent"),
                     ("この配置観測時点では、評価・最終配置判断を待って両者を変更せず保持しました。",
                      "Both were preserved unchanged pending evaluation/final-deployment decisions at this deployment observation.")],
                ],
                ("別途提供された配置観測であり、docbuilder再実行や100問のAI採点ではない", "Separately supplied deployment observations, not a docbuilder rerun or 100-case AI grades")),
            p(
                "2026-10-02文書snapshotはdocs/v3.0.0/validation-20261002配下だけへ配置します。course editionは3.0.0を保ち、v3.0.0 tag・元のrelease assets・docs/v3.0.0/guide・元48 capture placements/46 PNGs/9 historiesを変更しません。freshなsnapshot approvalはstudyのexact SHAと既知制約をbindし、元release approvalを流用しません。",
                "Place the dated2026-10-02 document snapshot only under docs/v3.0.0/validation-20261002. Course edition remains3.0.0; preserve the v3.0.0 tag, original release assets, docs/v3.0.0/guide, and original48 capture placements/46 PNGs/9 histories. A fresh snapshot approval binds the exact study SHA and known limitations, never reusing the original release approval."),
            note(
                "この追加studyは自動event配送、Graph/TS/consumer互換性、配置の現在性を再認定せず、既存の失敗・手動実行・known limitationsを消しません。特にcompatibility構成の回答結果をgeneration2 consumer修復やTS numeric query成功とは扱いません。厳格な--require-acceptanceは変更せず独立して残ります。文書の成功は権限変更・再質問・公開・Agent promotionの承認ではありません。",
                "This study does not recertify automatic event delivery, Graph/TS/consumer compatibility or deployment readiness, and does not erase failures, manual execution or known limitations. Compatibility-profile answers do not repair the generation2 consumer or prove a TS numeric query. The strict --require-acceptance gate remains unchanged and independent. Successful document work authorizes no permission change, resubmission, publication or Agent promotion.",
                "gate"),
        ])


def appendices(roots, context, tests):
    a = {s.appendix: s for s in roots}
    sub(a["A"], "1", ("期待値の適用範囲", "Scope of expected values"), [
        p("下の保持表は固定seed/3incrementの期待値です。選択Graph subset、品質処理後Gold、別期間、複数runへ無条件に適用しません。",
          "The retained tables apply to the fixed seed/three increments, not automatically to selected graph subsets, curated Gold, another period or multiple runs."),
    ])
    sub(a["B"], "1", ("パラメーターの使用範囲", "Parameter boundaries"), [
        p("全Notebook 01–05パラメーターは下に欠落なく保持しています。値の既定と変更承認を区別し、新UI API適合性が未確認の項目は使用前にpreviewで止めます。",
          "All Notebook 01–05 parameters are retained below. Distinguish defaults from approval to change; stop at preview if new-UI API compatibility is not verified."),
    ])
    sub(a["C"], "1", ("固定問題と採点", "Frozen questions and scoring"), [
        p("標準10問の全文、実行根拠、84条件、失敗時確認は19章の保持参考にあります。以下の記録は追加評価用で、標準条件を置換しません。",
          "Full standard questions, execution evidence, 84 criteria and failure checks are retained in Chapter 19. The following records are additional evaluation, not replacements."),
        table([("番号", "Number"), ("保持する問題ID", "Preserved test ID"), ("条件数", "Criteria")],
              [[str(q.number), q.test_id, str(len(q.evidence) + len(q.pass_criteria))] for q in tests],
              ("原本から生成した10問／84条件", "Ten questions / 84 conditions generated from the unchanged source")),
        table([("記録欄", "Field"), ("記録内容", "Record")], [
            [("candidate", "Candidate"), ("定義・instruction・source hash、データ時点", "Definition/instruction/source hashes and data timestamp")],
            [("実行", "Execution"), ("新会話IDはprivate、question ID、query、source、tool、結果", "Private conversation ID, question ID, query, source, tool and result")],
            [("判定", "Outcome"), ("passed / failed / blocked / unsupported / not-run と理由", "passed / failed / blocked / unsupported / not-run with reason")],
            [("修正", "Correction"), ("最小差分、承認、独立再runと回帰結果", "Minimal delta, approval, independent rerun and regression results")],
        ], ("未記入の記録フォーム", "Unfilled recording form")),
    ])
    sub(a["D"], "1", ("新必須演習とOptionalの区別", "Required new labs versus optional extensions"), [
        p("Notebook 05品質/Gold、Metrics、Copilot添付、継承、version、RDFの演習はv3の学習対象です。Graphは必要な問いに選択して使うoptional実行層ですが、適格性とGQLの演習はこのコースに含みます。Power BIの追加report、UDF等は以下のOptional参考を使います。",
          "Notebook 05 quality/Gold, Metrics, Copilot attachments, inheritance, version and RDF are v3 learning objectives. Graph is an optional execution layer chosen for relevant questions, but eligibility/GQL is a course lab. Additional Power BI reports/UDFs use the retained optional reference."),
    ])
    sub(a["E"], "1", ("旧19章から新24章への対応", "Old 19-chapter to new 24-chapter map"), [
        table([("v3章/付録", "v3 chapter/appendix"), ("保持したv2.7章/付録", "Retained v2.7 chapter/appendix")],
              [[str(k), ", ".join(map(str, v))] for k, v in LEGACY_MAP.items()],
              ("全旧章・5付録を欠落なく保持", "Every old chapter and all five appendices retained")),
        note("保持参考は旧版の画面名・章番号を含みます。先頭の現行Preview手順を優先し、旧UIの自動Graph、直接Activator、複数Agent等をv3へ無条件適用しません。旧UI写真はv3には埋め込まず、旧配布ペアで確認します。",
             "Retained references contain old UI names and chapter numbers. Follow current-preview procedures first; do not blindly carry automatic graph, direct Activator or multiple-agent patterns into v3. Old UI screenshots are not embedded in v3; consult the old pair for those images."),
    ])
    sub(a["E"], "2", ("新UIの停止原因と次の確認", "New-UI blockers and next checks"), [
        table([("症状", "Symptom"), ("次に確認すること", "Next check")], [
            [("Ontology agentが無い", "Ontology agent absent"), ("preview/地域/利用権限を読む。管理設定を勝手に変えない", "Read preview/region/permission state; do not change admin settings")],
            [("Metricsが無い", "Metrics absent"), ("source Measureの所有table、Generate Ontology経路、Read+Build", "Source measure owner table, Generate Ontology route, Read+Build")],
            [("Graph Ineligible", "Graph Ineligible"), ("実tooltip、key、source種別、backing table数", "Actual tooltip, key, source type, backing-table count")],
            [("Ruleが通知しない", "Rule sends no alert"), ("設計どおり。自然言語contextであり独立Activatorを別確認", "Expected: natural-language context; inspect independent Activator separately")],
            [("添付の内容を使わない", "Attachment ignored"), ("同じ会話の実upload、filenameの指定、実回答根拠", "Actual upload in same conversation, filename reference, answer evidence")],
            [("RDF注釈が消える", "RDF annotations disappear"), ("import logとunsupported/custom annotationの対応", "Import log and unsupported/custom-annotation mapping")],
        ], ("未提供を偽の合格にしない", "Do not convert unavailability into false success")),
    ])


def _legacy_copy(source: Section, parent: Section, index: int) -> Section:
    value = copy.deepcopy(source)
    for sequence, item in enumerate(value.walk()):
        item.ident = f"{parent.ident}-legacy-{index}-{sequence}"
        item.level = min(4, item.level + 1)
        item.chapter = parent.chapter
        item.appendix = parent.appendix
        item.optional = False
        item.checklist_id = None
        item.title = t("v2.7参考: " + item.title.ja, "v2.7 reference: " + item.title.en)
        item.blocks = [b for b in item.blocks if b.kind != "figure" or b["source_kind"] != "screenshot"]
    value.blocks.insert(0, note(
        "以下はv2.7の内容を省略せず保持した比較・移行用参考です。旧章番号と画面名はv2.7内を指します。現行UIの実行手順・実施証拠ではありません。対応する新手順と制限をこの章の冒頭で確認してください。",
        "The following retains v2.7 content without abridgement for comparison/migration. Its chapter numbers and UI names refer to v2.7, not current-UI execution or evidence. Follow this chapter's current procedures and limits first.",
        "gate",
    ))
    return value


def verify_artifact_manifest(root, manifest_path):
    raw = manifest_path.read_bytes()
    manifest = json.loads(raw)
    if manifest.get("schemaVersion") != "furusato-v3-artifact-set/v1":
        raise ValueError("Expected a verified v3 artifact-set manifest.")
    version = (root / "WORKSHOP_VERSION").read_text(encoding="utf-8").strip()
    if manifest["workshopVersion"] != version or manifest["tempRequired"] is not False:
        raise ValueError("Workshop edition or production placement differs from the artifact set.")
    for relative, expected in manifest["files"].items():
        path = (root / relative).resolve()
        if not path.is_relative_to(root.resolve()) or not path.is_file():
            raise ValueError("Artifact manifest path is invalid.")
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError("Artifact changed after its manifest was frozen: " + relative)
    binding = {"manifestSha256": hashlib.sha256(raw).hexdigest(), "sourceCommit": manifest["sourceCommit"],
               "sourceTreeSha256": manifest["sourceTreeSha256"], "workshopVersion": version,
               "csvFiles": manifest["csvFiles"], "notebookCount": len(manifest["notebooks"]),
               "tempRequired": False}
    return manifest, binding


def artifact_consistency_sections(roots, root, manifest_path):
    manifest, artifact_binding = verify_artifact_manifest(root, manifest_path)
    version = artifact_binding["workshopVersion"]
    binding = artifact_binding["manifestSha256"]
    chapters = {section.chapter: section for section in roots if section.chapter}
    appendix = next(section for section in roots if section.appendix == "B")
    chapters[1].blocks.insert(0, note(
        "現行配布物の整合性: 教材版は" + version + "です。Notebook・CSV・モデル・Agent profileは同じartifact-setに結び付けています。以下の過去の評価・画面記録は、その撮影・実行時点の履歴であり、新配置の合格とは区別してください。",
        "Current artifact consistency: course edition " + version + ". Notebooks, CSVs, models and the Agent profile are bound to one artifact set. Historical evaluation and screen records below remain dated evidence, not acceptance of a new deployment.",
        "gate"))
    sub(chapters[1], "12", ("現行v3成果物の版とデータ仕様", "Current v3 artifact and data-contract versions"), [
        table([("項目", "Component"), ("識別子と意味", "Identity and meaning")], [
            [("教材・Notebook配布版", "Course and Notebook edition"), version + " / WORKSHOP_VERSION"],
            [("技術的な配置パス", "Technical deployment path"), manifest["runtimeProfile"]],
            [("再利用する処理基線", "Retained processing baseline"), manifest["edition"]["baselineRuntimeVersion"] + " / VERSION"],
            [("CSVデータ仕様", "CSV data contract"), manifest["edition"]["datasetVersion"]],
            [("本配置", "Production placement"), ("指定フォルダ直下。Temp不要", "Directly in the specified folder; no Temp required")],
        ], ("異なる役割のversionを一律置換しない", "Do not conflate versions with different roles")),
        p("CSVの値・件数・SHAを変更してv3と見せかけることはしません。Notebook01のNOTEBOOK_VERSIONは配布版・監査表示を示します。内部のpublication keyと既存実行の監査履歴は互換性と来歴のため保持します。",
          "CSV values, counts and hashes are not changed merely to relabel them v3. Notebook01 NOTEBOOK_VERSION identifies the distributed edition/audit display. Internal publication keys and existing run audit history remain unchanged for compatibility and provenance."),
        p("Artifact-set SHA-256: " + binding, "Artifact-set SHA-256: " + binding),
        p("実装source commit: " + manifest["sourceCommit"] + "。このhashは成果物整合性の証拠であり、AI回答・全機能の合格証明ではありません。",
          "Implementation source commit: " + manifest["sourceCommit"] + ". This hash proves artifact binding, not AI-answer or all-feature acceptance."),
    ])
    rows = []
    for number, item in manifest["notebooks"].items():
        notebook = json.loads((root / item["path"]).read_bytes())
        for name, value in literal_notebook_parameters(notebook, item["path"]).items():
            rows.append([number, name, json.dumps(value, ensure_ascii=False)])
    sub(appendix, "3", ("現行v3 Notebookの実ファイル由来パラメーター", "Current v3 Notebook parameters from the actual files"), [
        p("以下は現行artifact-setの配布Notebookから抽出した初期値です。環境ごとのID・参加者・apply承認は配置時に設定します。後続のv2.7参考表は旧版比較用であり、本配置の初期値ではありません。",
          "These defaults are extracted from the current artifact-set Notebooks. Supply environment identities, participant and apply approval during deployment. The retained v2.7 tables are comparison material, not current production defaults."),
        table(["Notebook", ("パラメーター", "Parameter"), ("配布初期値", "Distributed default")],
              rows, ("現行5 Notebookのパラメーター", "Parameters from all five current Notebooks")),
    ])
    sub(chapters[24], "12", ("Tempを使わない本デプロイ", "Production deployment without Temp"), [
        p("本デプロイでは、指定フォルダに必要なItemsを直接作成し、1つの承認済みplanとして依存順に最後まで実行します。複数APIをまとめた一括手順であり、Fabric全Itemsの単一トランザクションではありません。途中の失敗は記録し、不明な書き込みやCSVを再送しません。",
          "Create required Items directly in the specified folder and execute one approved plan in dependency order. This is a coordinated multi-API deployment, not one atomic Fabric transaction. Record intermediate failures; never replay ambiguous writes or CSV deliveries."),
        p("修正版Agentに必要な静的consumer Ontologyとそのmanaged childrenは正式な依存Itemsであり、Tempへ置きません。generation2の主Ontologyと用途を区別し、同じ寄附データを重複加算しません。採用するAgentは正式名へ反映し、評価用の比較Agentを第2の本番として残しません。",
          "The static consumer Ontology and its managed children are production dependencies of the corrected Agent, not Temp artifacts. Distinguish their role from the primary generation2 Ontology and never add their identical donation populations. Apply the adopted profile to the formal Agent; do not retain comparison Agents as a second production service."),
        p("評価用Tempを明示的に使用した場合は、必要な依存の正式配置と参照を確認し、評価証拠をprivateに保存してから不要なItemsと空のTempを削除します。Notebook02–04のsealed packageには最新の4段階Agent compiler（source-grounded、complete-contract、time-layer-isolation、standard-contract-restoration）、6 SQL views、SQL/KQL例を含めています。",
          "If an evaluation Temp is explicitly used, first establish production dependencies and references, preserve evidence privately, then delete unused Items and the empty Temp. Notebook02–04 sealed packages include the current four-stage Agent compilers (source-grounded, complete-contract, time-layer-isolation and standard-contract-restoration), six SQL views and SQL/KQL examples."),
    ])
    return artifact_binding


def build(
    root: Path, evidence_path: Path | None = None, evaluation_path: Path | None = None, *,
    public_evidence_path: Path | None = None, release_profile=release.PREVIEW,
    release_approval: Path | None = None, evaluation100_path: Path | None = None,
    artifact_manifest_path: Path | None = None, participant_edition: bool = False,
):
    profile = release.get_profile(release_profile)
    if participant_edition and (profile != release.V300 or artifact_manifest_path is None):
        raise ValueError("The participant edition requires the v3.0.0 profile and a verified artifact manifest")
    evidence, document_release = release.resolve_evidence(
        root, evidence_path, evaluation_path, public_evidence_path=public_evidence_path,
        release_profile=profile, release_approval=release_approval,
        evaluation100_path=evaluation100_path,
    )
    context = load_context(root, document_edition="unified-20260923", source_version="2.7.0")
    facts = compute_facts(context)
    tests = build_tests(context, facts)
    carrier = StyleCarrier.resolve(root)
    capture = capture_with_word_layout(context, facts, tests, carrier)
    mirror = load_mirror(public_documents_only=True, context=context)
    legacy = build_document(capture.nodes, mirror)
    nodes = [n for n in capture.nodes if n.kind != "heading"]
    blocks = [b for section in legacy.walk() for b in section.blocks]
    if len(nodes) != len(blocks):
        raise ValueError("Legacy block order cannot be reconciled")
    for node, block in zip(nodes, blocks):
        if node.get("word_layout"):
            block.payload["word_layout"] = node["word_layout"]
    headings = [n for n in capture.nodes if n.kind == "heading"]
    for node, section in zip(headings, legacy.walk()):
        section.word_layout = node.get("word_layout", {})
    table_widths = {n["number"]: n.get("widths") for n in capture.nodes if n.kind == "table"}
    for block in legacy.tables:
        block.payload["widths"] = table_widths[block["number"]]
    if mirror.unused():
        raise ValueError("Baseline bilingual mirror has unused entries")
    original = {s.chapter if s.chapter else s.appendix: s for s in legacy.sections}
    if set(original) != set(range(1, 20)) | set("ABCDE"):
        raise ValueError("The baseline curriculum shape changed")
    if evidence.get("publicProjection") and evaluation_path is not None:
        raise ValueError("Export the evaluator aggregate into the public projection; do not mix a private override")
    evaluation = evidence.get("evaluationProjection") if evidence.get("publicProjection") else preview30_evaluation.load(evaluation_path)
    selected = (
        preview30_public_evidence.selected_original_suite_run(evidence, required=True)
        if "selectedOriginalSuiteRunId" in evidence else None
    )
    selected_nonlegacy = selected if selected is not None and selected["id"] != preview30_public_evidence.LEGACY_ORIGINAL_SUITE_RUN_ID else None
    if selected is not None and selected_nonlegacy is None:
        preview30_reporting.require_legacy_run(selected)
    roots = [Section(
        ident=f"ch-{n}", level=1, number=str(n), title=t(f"{n}. {ja}", f"{n}. {en}"), chapter=n,
    ) for n, (ja, en) in enumerate(CHAPTERS, 1)]
    roots += [Section(
        ident=f"appendix-{letter.lower()}", level=1, number=letter,
        title=t(f"付録 {letter}　{ja}", f"Appendix {letter} — {en}"), appendix=letter,
    ) for letter, (ja, en) in zip("ABCDE", APPENDICES)]
    participant_figures = None
    if participant_edition:
        from . import participant30
        participant_manifest, artifact_binding = verify_artifact_manifest(root, artifact_manifest_path)
        participant_figures = participant30.compose(
            roots, root=root, context=context, facts=facts, tests=tests, evidence=evidence,
            manifest=participant_manifest, legacy_original=original,
        )["figures"]
    full_edition = not participant_edition
    if full_edition:
        current_lessons(roots[:24], context)
        reference_tables(roots[:24], context, tests)
        definition_contract_sections(roots[:24])
        appendices(roots[24:], context, tests)
        runtime_candidate_sections(roots, root)
        evaluation_sections(roots, evaluation)
        current_receipt_sections(roots, selected_nonlegacy)
        original_suite_run_sections(roots, evidence.get("originalSuiteRuns", []), evidence=evidence)
    if full_edition and "evaluation100" in evidence:
        evaluation100_sections(roots, evidence["evaluation100"], evidence["evaluation100Sha256"])
    if full_edition and selected_nonlegacy is not None:
        roots[0].blocks.insert(0, note(*preview30_reporting.selection_notice(selected_nonlegacy), "stop"))
    elif full_edition:
        roots[0].blocks.insert(0, note(
            PREVIEW_NOTICE_JA + "。最終Compat native UIの元84条件は48 PASS/36 FAIL。mainは未promotionで、既知の失敗・partial・blocked laneを保持します。",
            PREVIEW_NOTICE_EN + ". The final Compat native-UI original84 result is48 PASS/36 FAIL. Main is not promoted; known failures, partial and blocked lanes remain explicit.",
            "stop",
        ))
    if full_edition and profile.is_snapshot:
        roots[0].blocks.insert(0, note(
            "2026-10-02公開後検証snapshot (文書版3.0.0)。元releaseを置換せず、frozen100を別分母で追加します。freshなstudy-bound approvalは既知制約の開示だけを承認し、AI回答品質・GA・全機能受入・Agent promotionは承認しません。",
            "Post-release validation snapshot2026-10-02 (course edition3.0.0). It adds frozen100 under a separate denominator without replacing the original release. Fresh study-bound approval authorizes known-limitations disclosure only, not AI-quality, GA, all-feature acceptance or Agent promotion.",
            "stop",
        ))
    elif full_edition and document_release is not None:
        roots[0].blocks.insert(0, note(
            "文書版3.0.0はユーザー承認の既知制約付きリリースです。選択した実結果76 PASS/8 FAIL、全履歴、partial/blocked/failedの状態を保持します。製品機能・APIは引き続きPreviewです。--release-profile v3.0.0と別のhash-bound --release-approvalは文書配布だけを承認し、AI回答品質・GA・全機能合格・Fabric Agent promotionを承認しません。厳格な--require-acceptanceは独立して残り、このsnapshotは未合格です。",
            "Document edition 3.0.0 is a user-authorized release with known limitations. The selected 76 PASS/8 FAIL result, complete historical ledgers and partial/blocked/failed states are retained. Product features and APIs remain Preview. --release-profile v3.0.0 with a separate hash-bound --release-approval authorizes document distribution only, not AI acceptance, GA, all-feature success or Fabric Agent promotion. The strict --require-acceptance gate remains independent; this snapshot is unaccepted.",
            "stop",
        ))
    if full_edition and "evaluation100" in evidence:
        study_notice = study100.notice(evidence["evaluation100"])
        roots[0].blocks.insert(0, note(study_notice["ja"], study_notice["en"], "gate"))
    if full_edition:
        artifact_binding = artifact_consistency_sections(roots, root, artifact_manifest_path) if artifact_manifest_path else None
    request_list = preview30_evidence.requests()
    for section in (roots if full_edition else []):
        key = section.chapter if section.chapter else section.appendix
        items = [item for item in request_list if item["chapter"] == section.chapter]
        if items:
            blocks = []
            for item in items:
                if not item.get("completionRequired", True) and item["id"] not in evidence["captures"]:
                    continue
                state = evidence["labs"][item["lab"]]
                blocks.append(note(
                    f"{item['id']} — {state['status']}: {state['reason']['ja']}",
                    f"{item['id']} — {state['status']}: {state['reason']['en']}",
                    "note" if state["status"] == "passed" else "gate",
                ))
                if item["id"] in evidence["captures"]:
                    capture_item = evidence["captures"][item["id"]]
                    cap = capture_item["caption"]
                    observed_at = datetime.fromisoformat(capture_item["capturedAt"].replace("Z", "+00:00")).astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
                    caption = t(
                        cap["ja"] + f" 記録時刻: {observed_at}。撮影時点の状態であり、新規接続や演習全体の合格は証明しません。",
                        cap["en"] + f" Recorded: {observed_at}. State at capture, not a new connection or full-lab acceptance.",
                    )
                    blocks.append(Block("figure", {
                        "number": 0, "source_kind": "reviewed-capture", "source_key": item["id"],
                        "caption": caption, "alt": t(cap["ja"], cap["en"]),
                    }))
            sub(section, "9", ("実施証拠・現在の状態", "Execution evidence and current status"), blocks)
        section.children.sort(key=lambda child: int(child.number.rsplit(".", 1)[-1]))
        for index, old in enumerate(LEGACY_MAP.get(key, []), 1):
            section.children.append(_legacy_copy(original[old], section, index))
    tables = []
    figures = []
    checklist = []
    for root_section in roots:
        for s in root_section.walk():
            if s.level == 2 and "-legacy-" not in s.ident and s.number.endswith(".2") and (s.chapter or 0) >= 4:
                s.checklist_id = s.ident
                checklist.append((s.ident, s))
            for block in s.blocks:
                if block.kind == "table":
                    tables.append(block)
                    block.payload["number"] = len(tables)
                elif block.kind == "figure":
                    figures.append(block)
                    block.payload["number"] = len(figures)
    document = Document(roots, figures, tables, checklist)
    counts = {
        "chapters": len(CHAPTERS), "appendices": len(APPENDICES),
        "headings": sum(1 for _ in document.walk()), "tables": len(tables),
        "figures": len(figures), "tests": len(tests),
        "conditions": sum(len(q.evidence) + len(q.pass_criteria) for q in tests),
    }
    if counts["conditions"] != 84:
        raise ValueError("Standard 84-condition evaluation changed")
    serial = json.dumps(asdict(document), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    metadata = {
        "version": profile.version, "baselineVersion": context.version, "baselineEdition": context.document_edition,
        "counts": counts, "contentSha256": hashlib.sha256(serial.encode("utf-8")).hexdigest(),
        "retainedLegacyChapters": 19, "retainedLegacyAppendices": 5,
        "omittedLegacyUICaptures": sum(1 for b in legacy.figures if b["source_kind"] == "screenshot"),
        "currentUICaptures": len(evidence["captures"]), "evidenceComplete": evidence["complete"],
        "labStates": {lab: value["status"] for lab, value in evidence["labs"].items()},
        "evidenceScope": "historical-observed-run",
        "newDeploymentReadinessCertified": False,
        "allFeaturesPassedClaimed": False,
        "previewPresentation": {"ja": PREVIEW_NOTICE_JA, "en": PREVIEW_NOTICE_EN},
        "aiAnswerQualityAccepted": False,
        "knownIssueLabs": [lab for lab, value in evidence["labs"].items() if value.get("knownIssue")],
    }
    if evidence.get("publicProjection"):
        metadata["publicEvidenceProjectionSha256"] = evidence["projectionSha256"]
        metadata["publicEvidenceReviewedAt"] = evidence["reviewedAt"]
        metadata["releaseFreezeStatus"] = evidence["freezeStatus"]
    if evidence.get("originalSuiteRuns"):
        metadata["originalSuiteRuns"] = evidence["originalSuiteRuns"]
    if selected is not None:
        metadata.update(preview30_reporting.selection_metadata(evidence))
        metadata["finalUserAcceptanceCertified"] = False
    if evaluation is not None:
        metadata["evaluationProjection"] = evaluation
    if "evaluation100" in evidence:
        metadata.update({key: copy.deepcopy(evidence[key]) for key in ("evaluation100", "evaluation100Sha256")})
    if document_release is not None:
        metadata["documentRelease"] = document_release
        release.require_metadata_profile(metadata, profile)
    if artifact_binding:
        metadata["currentArtifactSet"] = artifact_binding
    if participant_edition:
        metadata.update({
            "participantEdition": True, "retainedLegacyChapters": 0, "retainedLegacyAppendices": 0,
            "participantFigures": participant_figures,
        })
    return document, context, facts, carrier, evidence, metadata
