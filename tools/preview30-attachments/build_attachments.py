"""Build portable, synthetic context files. Never connects to Fabric."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "docs"))

from furusato_docs.context import load_context  # noqa: E402

MAX_BYTES = 5 * 1024 * 1024
PACK_NAMES = (
    "business-requirements.pdf",
    "data-dictionary.txt",
    "domain-model.png",
    "revision-requirements.txt",
)
GUID = re.compile(r"\b[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\b", re.I)
PRIVATE = re.compile(
    r"(?:https?://|[A-Z]:[\\/]|[\\/]Users[\\/]|Bearer\s|sig=|"
    r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})",
    re.I,
)

REQUIREMENTS = [
    (
        "目的と合成データ",
        "架空の寄付・寄付者・事業者を使い、自治体の受入、寄付者の居住地、返礼品の登録関係を説明する。"
        "自治体名・コードのみ実在する参照ラベルであり、現実の人物や自治体の業績ではない。",
        "Purpose and synthetic data",
        "Explain recipient geography, donor residence, and registered gift-supplier relationships using synthetic donations, "
        "donors and businesses. Only municipality names and codes are real reference labels, not evidence about real people or performance.",
    ),
    (
        "静的データと運用観測",
        "静的 Donation は80,000件。8月の運用観測はraw 15,000行、一意EventID 14,900件、重複100件。"
        "別レイヤーなので無条件に加算しない。rawと重複除去後の件数・金額を同じ分母で比較する。",
        "Static facts and operational observations",
        "Static Donation contains 80,000 records. August observations have 15,000 raw rows, 14,900 unique EventID values "
        "and 100 duplicates. These are separate layers: never add them blindly. Use the same raw or deduplicated denominator for counts and amounts.",
    ),
    (
        "Goldと品質受入の意味",
        "GoldはNotebook05が入力ファイルの品質検証・EventID重複除去を行って作る別の分析層。"
        "DataSource=StaticSeedは静的データ、RealtimeIncrementは品質チェックを通過した増分で、"
        "直接接続したSemantic ModelのDAXで区別する。Goldの品質受入は決済・発送の確定や手動承認を意味しない。"
        "Goldの完成だけではFileCreatedからPipelineへの自動取り込み成功を証明しない。",
        "Gold and quality acceptance",
        "Gold is a separate analytical layer produced by Notebook05 after validating the input files and deduplicating EventID. "
        "DataSource=StaticSeed identifies static data; RealtimeIncrement identifies quality-accepted increments. "
        "Keep these scopes explicit in the directly connected Semantic Model's source-owned DAX. Quality acceptance is not payment, "
        "shipment confirmation or manual business approval. A completed Gold build does not prove automatic FileCreated-to-Pipeline ingestion.",
    ),
    (
        "地理的な意味",
        "DonorLivesInPrefectureは寄付者の居住地。DonationToMunicipalityからMunicipalityInPrefectureは受入地域。"
        "SupplierInPrefectureは事業者の登録地域。「東京の寄付」には居住地か受入地かを確認する。",
        "Geographic meaning",
        "DonorLivesInPrefecture is donor residence. DonationToMunicipality followed by MunicipalityInPrefecture is recipient geography. "
        "SupplierInPrefecture is supplier registration. Clarify residence versus recipient when asked about donations in Tokyo.",
    ),
    (
        "関係の根拠",
        "DonationSelectedGiftは選択された返礼品、SupplierProvidesGiftは登録された供給関係。"
        "配送済み・受領済み・実際の発送者と解釈しない。寄付金額から所得・資産・富裕度を推定しない。",
        "Relationship evidence",
        "DonationSelectedGift means a selected gift; SupplierProvidesGift means a registered supply relationship. "
        "Neither proves delivery, receipt or the actual fulfiller. Donation amounts do not establish income, assets or wealth.",
    ),
    (
        "モデルと同一性",
        "公開辞書の10 Entity・72 static Property・1 time-series Property・15 Relationshipを基準にする。"
        "キーと型を保持し、MunicipalityIdの文字列と先頭ゼロを守る。計算結果のMetric EntityとDAXのMetricsを区別する。"
        "新定義はTMDL/TMSL++であり、旧EntityTypes JSONを新形式とみなさない。",
        "Model and identity",
        "Use the public dictionary's 10 entity types, 72 static properties, one time-series property and 15 relationships as the baseline. "
        "Preserve keys and types, including string MunicipalityId and leading zeroes. Distinguish aggregate Metric entities from source-owned DAX Metrics. "
        "The new definition uses TMDL/TMSL++; old EntityTypes JSON is not the new format.",
    ),
    (
        "Planから明示Actへ",
        "講師が別途指定したソースIDだけを調べる。Planで発見、draft、validate、previewし、追加・変更・削除を示す。"
        "安定IDを保ち、既存本番や比較用モデルを変更しない。承認したlab-copyに限りActし、その後定義を読み戻す。",
        "Plan before explicit Act",
        "Inspect only the source IDs supplied separately by the instructor. Discover, draft, validate and preview in Plan; list additions, edits and deletions. "
        "Preserve stable IDs and leave production and comparison items untouched. Act only on the approved lab copy, then read the definition back.",
    ),
    (
        "添付の境界",
        "この教材は会話内の設計文脈であり、データ取り込み・RDF import・アクセス許可ではない。"
        "1会話10ファイル以下、各5MB以下。ファイル名を明示して利用を依頼し、新しい会話には再添付する。",
        "Attachment boundary",
        "These files are conversation context, not ingestion, RDF import or access grants. Use at most 10 files per conversation, each at most 5 MB. "
        "Name each file in the prompt and attach it again in a new conversation.",
    ),
    (
        "検証と限界",
        "出典、query、返却値、警告を記録する。キーなし・semantic-model-backed EntityはGraph対象にしない。"
        "Business Rulesは自然言語文脈で、制約強制やActivator動作ではない。生成した質問だけで独立評価に合格したと主張しない。",
        "Validation and limits",
        "Record sources, executed queries, results and warnings. Do not project keyless or semantic-model-backed entities into graph. "
        "Business Rules provide natural-language context, not enforced constraints or Activator actions. Agent-generated questions are not independent evaluation.",
    ),
]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def font_path(explicit: str | None = None) -> Path:
    candidates = [Path(explicit)] if explicit else [
        Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts" / "meiryo.ttc",
        Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts" / "YuGothM.ttc",
    ]
    for path in candidates:
        if path.is_file():
            return path
    raise FileNotFoundError("Supply --font with an embeddable Japanese TrueType font; no glyph fallback is permitted.")


def assert_portable(text: str) -> None:
    if GUID.search(text) or PRIVATE.search(text):
        raise ValueError("Attachment contains a GUID, URL, account, secret marker or machine path.")


def dictionary(context) -> str:
    lines = [
        "Furusato Workshop 3.0 Preview | portable data dictionary / データ辞書",
        "Synthetic context only / 合成データの設計文脈。No private benchmark answers.",
        "Dataset contract: " + context.dataset_manifest["datasetVersion"],
        "Do not treat this file as source data ingestion, RDF import, or authorization.",
        "Raw 15000 / unique EventID 14900 / duplicate rows 100. Never mix raw and deduplicated denominators.",
        "Donor residence != recipient municipality geography != supplier registration.",
        "SupplierProvidesGift means registration, NOT delivery; DonationSelectedGift means selection, NOT receipt.",
        "Do not infer income, assets or wealth from donation amounts.",
        "Definition boundary: this is a business/source dictionary, NOT a generation-2 definition payload.",
        "New definitions use TMDL/TMSL++ with compatibilityLevel 1000000, not old EntityTypes JSON.",
        "Source-contract BigInt maps to TMDL int64, DateTime to dateTime, String to string.",
        "Native target types below describe intended meaning; they do not prove native binding or service acceptance.",
        "",
        "1. ACTUAL CSV SCHEMAS / 公開CSV実スキーマ",
    ]
    base = ROOT / "workshop" / "v2.7.0" / "data"
    for kind, folder in (("files", "seed"), ("incrementFiles", "increment")):
        for spec in context.dataset_manifest[kind]:
            source = base / folder / spec["file"]
            with source.open(encoding="utf-8-sig", newline="") as handle:
                reader = csv.reader(handle)
                headers = next(reader)
                count = sum(1 for _ in reader)
            if count != spec["rows"] or ",".join(headers) != spec["header"] or sha(source) != spec["sha256"]:
                raise ValueError("Public dataset drift: " + source.name)
            lines.extend([f"{source.name} | rows={count}", "Columns: " + ", ".join(headers)])
    lines.extend(["", "2. NOTEBOOK 01 ENTITY BINDINGS / 型・キー・実列対応"])
    for entity in context.entities:
        lines += [
            "",
            f"{entity.name} | key={entity.key_property} | display={entity.display_name_property}",
            entity.description,
        ]
        for prop in entity.properties + entity.timeseries_properties:
            mapped = {
                "BigInt": "int64", "String": "string", "Boolean": "boolean",
                "DateTime": "dateTime", "Double": "double", "Object": "complex (shape review required)",
            }[prop.value_type]
            target_type = f"TimeSeries<{mapped}>" if prop in entity.timeseries_properties else mapped
            lines.append(
                f"  {prop.name} : {prop.value_type}" + (" [KEY]" if prop.is_key else "")
                + f" | new TMDL target type={target_type} | " + prop.description
            )
        for binding in entity.bindings:
            lines.append(f"  {binding.binding_type} {binding.source_type} table={binding.source_table}")
            if binding.timestamp_column:
                lines.append("  timestamp=" + binding.timestamp_column)
            for left, right in binding.column_map:
                lines.append(f"    {left} -> {right}")
    lines.extend(["", "3. DIRECTED RELATIONSHIPS / 向きとマッピング列"])
    for relationship in context.relationships:
        lines.extend([
            f"{relationship.name}: {relationship.origin} -> {relationship.target}",
            f"  mapping={relationship.mapping_table}; origin={relationship.origin_key_column}; target={relationship.target_key_column}",
            "  " + relationship.description,
        ])
    lines.extend([
        "",
        "4. INTERPRETATION / 解釈",
        "Original donation_orders.csv uses DonatedAt. Ontology uses DonatedAtUtc and explicit JST-derived display fields.",
        "MunicipalityId is String; keep leading zeroes. SupplierId derives from raw BusinessID.",
        "MunicipalityCategoryMetric and PrefectureCategoryMetric are stored aggregate entities, not ontology DAX Metrics.",
        "DAX Metrics remain owned and executed by their source semantic model. Ontology descriptions do not edit the source DAX.",
        "Graph is optional. Keys, supported Delta source and eligible single backing table are required.",
        "A time-series binding does not establish Graph compatibility. Preserve the operational binding; use a separately reviewed static-only companion for relationship Graph queries.",
        "Time-series semantics do not imply live graph refresh. Record the actual source and freshness.",
        "The Eventhouse mapping above is an intended source mapping, pending native binding verification; do not embed old KustoTable JSON as new TMDL.",
        "DAX projected/enrichment metric backingMeasure does not survive the current TMDL round trip; avoid wholesale replay after native Metrics are added.",
        "Use only instructor-supplied source IDs; this portable pack deliberately contains no environment identifiers.",
        "",
        "5. V3 GOLD SERVING SCOPE / 品質受入済み分析層",
        "Gold is built by Notebook05 from the immutable static seed and staged increment files, with validation and EventID deduplication.",
        "DataSource=StaticSeed is the static population; DataSource=RealtimeIncrement is the quality-accepted, deduplicated increment population.",
        "Raw DonationEvents still contains every ingested observation, including duplicates; the one-minute summary has an aggregate, not transaction, grain.",
        "Gold acceptance means passing data-quality checks, NOT payment/shipment confirmation, manual business approval, or a newly inferred real donation.",
        "Static Donation is an immutable synthetic snapshot, NOT evidence of confirmed payment or shipment.",
        "The direct Semantic Model owns and executes DAX measures. Use static-scoped measures for StaticSeed and accepted-increment measures for RealtimeIncrement.",
        "A combined Gold view is valid only when explicitly requested and labelled; it is not a raw-observation-plus-static sum.",
        "Gold build completion is independent of FileCreated/Activator/Pipeline delivery. Verify automatic delivery separately using event, activation, job, Copy and KQL evidence.",
        "These are design definitions only. This attachment proves neither live deployment nor data-query execution.",
    ])
    text = "\n".join(lines) + "\n"
    assert_portable(text)
    return text


def requirements_pdf(output: Path, font: Path) -> None:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer

    pdfmetrics.registerFont(TTFont("WorkshopJP", str(font), subfontIndex=0))
    normal = ParagraphStyle("normal", fontName="WorkshopJP", fontSize=10, leading=16, wordWrap="CJK", alignment=TA_LEFT)
    title = ParagraphStyle("title", parent=normal, fontSize=19, leading=28, textColor=colors.HexColor("#075e54"), spaceAfter=12)
    heading = ParagraphStyle("heading", parent=normal, fontSize=12, leading=18, textColor=colors.HexColor("#075e54"), spaceAfter=6)
    doc = SimpleDocTemplate(
        str(output), pagesize=A4, rightMargin=45, leftMargin=45, topMargin=48, bottomMargin=46,
        title="Furusato synthetic business requirements / 合成業務要件",
        author="Furusato Fabric Workshop", subject="Conversation-local ontology design context", invariant=1,
    )
    story = [
        Paragraph("Furusato 業務要件 / Business requirements", title),
        Paragraph("3.0 Preview · Synthetic training context · 2026-09-30", normal),
        Spacer(1, 14),
    ]
    for number, (ja_title, ja, en_title, en) in enumerate(REQUIREMENTS, 1):
        assert_portable(ja + en)
        story.append(KeepTogether([
            Paragraph(f"{number}. {escape(ja_title)} / {escape(en_title)}", heading),
            Paragraph(escape(ja), normal),
            Spacer(1, 5),
            Paragraph(escape(en), normal),
            Spacer(1, 13),
        ]))

    def footer(canvas, _doc):
        canvas.setFont("WorkshopJP", 8)
        canvas.setFillColor(colors.HexColor("#3f5550"))
        canvas.drawString(45, 26, "Synthetic / 合成教材 · Context only / 会話文脈のみ")
        canvas.drawRightString(A4[0] - 45, 26, str(_doc.page))

    doc.build(story, onFirstPage=footer, onLaterPages=footer)


def domain_png(output: Path, context, font: Path) -> None:
    from PIL import Image, ImageDraw, ImageFont, PngImagePlugin

    width, height = 2800, 1900
    image = Image.new("RGB", (width, height), "#f5faf8")
    draw = ImageDraw.Draw(image)
    fonts = {n: ImageFont.truetype(str(font), n, index=0) for n in (25, 27, 32, 40, 58)}
    draw.text((90, 55), "Furusato domain model / 業務モデル", font=fonts[58], fill="#075e54")
    draw.text((90, 142), "10 entity types · 15 directed relationships · Synthetic / 合成教材", font=fonts[32], fill="#263f39")
    groups = [
        ("Residence / 寄付者の居住地", ["DonorLivesInPrefecture"]),
        ("Recipient / 寄付の受入地域", ["DonationToMunicipality", "MunicipalityInPrefecture"]),
        ("Selection / 寄付と選択返礼品", ["DonorMadeDonation", "DonationSelectedGift", "GiftInCategory"]),
        ("Registration / 登録・供給関係 (配送の証明ではない)", ["SupplierInPrefecture", "MunicipalityCatalogsGift", "SupplierProvidesGift"]),
        ("Aggregate categories / カテゴリ別の集計", ["MunHasCategoryMetric", "MunMetricForCategory", "PrefHasCategoryMetric", "PrefMetricForCategory"]),
        ("Flow / 居住地から受入地への寄付の流れ", ["ResidencePrefHasFlow", "FlowToRecipientPref"]),
    ]
    by_name = {r.name: r for r in context.relationships}
    y = 225
    for title, relationships in groups:
        box_height = 64 + len(relationships) * 63
        draw.rounded_rectangle((70, y, width - 70, y + box_height), radius=18, fill="white", outline="#b8d7cc", width=3)
        draw.text((95, y + 12), title, font=fonts[32], fill="#075e54")
        for row, name in enumerate(relationships):
            r = by_name[name]
            line_y = y + 62 + row * 63
            draw.text((100, line_y), r.origin, font=fonts[27], fill="#173f36")
            draw.line((640, line_y + 33, 1310, line_y + 33), fill="#167d63", width=4)
            draw.polygon([(1310, line_y + 33), (1287, line_y + 22), (1287, line_y + 44)], fill="#167d63")
            draw.text((680, line_y - 8), name, font=fonts[25], fill="#354f48")
            draw.text((1350, line_y), r.target, font=fonts[27], fill="#173f36")
            draw.text((1920, line_y), r.mapping_table, font=fonts[25], fill="#354f48")
        y += box_height + 20
    draw.text((90, y + 12), "Residence ≠ recipient ≠ supplier registration. Selection ≠ receipt. No delivery or wealth inference.", font=fonts[27], fill="#784017")
    draw.text((90, y + 57), "Graph is optional. DAX Metrics ≠ stored Metric entities. Stable keys and bindings: data-dictionary.txt", font=fonts[27], fill="#263f39")
    if y + 100 > height:
        raise ValueError("Domain diagram would clip its footer")
    metadata = PngImagePlugin.PngInfo()
    metadata.add_text("Title", "Synthetic domain paths; not a Fabric UI screenshot")
    metadata.add_text("Author", "Furusato Fabric Workshop")
    metadata.add_text("Description", "\n".join(f"{r.origin} --{r.name}--> {r.target}" for r in context.relationships))
    image.save(output, pnginfo=metadata, optimize=True, dpi=(144, 144))


def build(out: Path, font: Path) -> dict:
    context = load_context(ROOT, document_edition="unified-20260923", source_version="2.7.0")
    out.mkdir(parents=True, exist_ok=True)
    (out / "data-dictionary.txt").write_text(dictionary(context), encoding="utf-8", newline="\n")
    requirements_pdf(out / "business-requirements.pdf", font)
    domain_png(out / "domain-model.png", context, font)
    revision = (
        "Revision exercise / 改訂演習 (Plan only until explicit approval)\n"
        "Ambiguous request: 東京の寄付が多い地域と、実際に発送した業者を教えて。\n"
        "Clarify whether Tokyo means donor residence or recipient geography. Ask count versus amount and the data layer/time window.\n"
        "Actual shipment/delivery is not represented. Offer registered suppliers for a selected gift instead, await consent, and preserve source labels.\n"
        "Propose metadata-only clarifications for DonorLivesInPrefecture, DonationToMunicipality and SupplierProvidesGift.\n"
        "Keep existing entity/property/relationship IDs, names, data types, keys, bindings, inheritance, shared-property references and redefines. "
        "No deletions, no source data writes, no new data agents.\n"
        "Check the proposed object kind: a Business Rule is not a relationship. If the requested operation is unsupported, stop and state that limitation.\n"
        "Show changed versus stable items, validate, and provide a read-only draft preview. Apply only to the approved lab copy in Act.\n"
        "Before Act, save a native version. After Act, compare the saved definition, including reusableProperty links, with the baseline; "
        "a success message is not proof. Restore the baseline if any protected structure changed.\n"
        "This file contains scenario requirements, not benchmark answers or evidence of execution.\n"
    )
    assert_portable(revision)
    (out / "revision-requirements.txt").write_text(revision, encoding="utf-8", newline="\n")
    files = {}
    for name in PACK_NAMES:
        path = out / name
        if not 0 < path.stat().st_size <= MAX_BYTES:
            raise ValueError("Invalid attachment size: " + name)
        files[name] = {"bytes": path.stat().st_size, "sha256": sha(path)}
    manifest = {
        "schemaVersion": "furusato-attachments/v1", "edition": "3.0.0-preview",
        "synthetic": True, "conversationScoped": True, "dataIngestion": False,
        "rdfImport": False, "containsPrivateEvaluationAnswers": False,
        "uploadObserved": False, "modelUseObserved": False,
        "definitionContext": {
            "newFormat": "TMDL/TMSL++", "compatibilityLevel": 1000000,
            "generation2Payload": False, "nativeBindingVerified": False,
        },
        "maxFilesPerConversation": 10, "maxBytesPerFile": MAX_BYTES,
        "sourceDatasetVersion": context.dataset_manifest["datasetVersion"],
        "font": {"name": font.name, "sha256": sha(font)},
        "files": files,
    }
    (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out / "SHA256SUMS.txt").write_text("".join(f"{files[n]['sha256']}  {n}\n" for n in PACK_NAMES), encoding="utf-8")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "workshop" / "v3.0.0-preview" / "attachments")
    parser.add_argument("--font")
    args = parser.parse_args()
    print(json.dumps(build(args.out, font_path(args.font)), ensure_ascii=False, indent=2))
