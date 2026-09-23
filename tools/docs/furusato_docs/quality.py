"""Quality-pass validators: content gates, OOXML layout and rendered pages.

The checks in this module were added by the consolidated quality fix pass. They
fall into three groups:

* *content* - the participant guide actually says the things the workshop needs
  it to say, with values taken from the shipped runtime rather than transcribed.
* *layout* - the package really is A4, really carries a Word field for the table
  of contents, and marks callouts, listings and captions so they cannot be torn
  across a page break.
* *render* - the pages that Word actually produces contain no blank page and no
  page holding nothing but a caption. Markup alone cannot prove either.
"""

from __future__ import annotations

import math
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree

from . import guide_content as gc
from .docx_kit import (
    CELL_PADDING_PT,
    CODE_BLOCK_UNBREAKABLE_LINES,
    MIN_CODE_PT,
    MONO_ADVANCE_RATIO,
)
from .oox import (
    A4_HEIGHT_TWIPS,
    A4_WIDTH_TWIPS,
    CHARACTER_SPACING_CONTROL,
    EAST_ASIAN_LANGUAGE,
    JAPANESE_PARAGRAPH_DEFAULTS,
)
from .parameters import (
    APPLIES_ALWAYS,
    APPLIES_STALE_LEASE,
    PARAMETER_SECTION,
    STALE_LEASE_GROUP,
    build_parameter_rows,
)
from .validators import Report
from .typography import ascii_parentheses

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

#: The published-agent smoke set is fixed; both chapter 18 and appendix C.5 must
#: name the same three tests.
SMOKE_TESTS = ("T03", "T07", "T08")

#: Wording that must not reappear: the layer vocabulary the pass replaced, and
#: the KQL projection layer the runtime removed.
RETIRED_WORDING = (
    ("明細層", "the superseded layer name"),
    ("詳細層", "the ambiguous layer name"),
    ("DonationObservationsForAgent", "the removed projection table"),
    ("ProjectDonationObservationsForAgent", "the removed projection function"),
    ("policy update", "the removed update policy"),
)


def _num(value: int) -> str:
    return f"{value:,}"


def _yen(value: int) -> str:
    return f"{value:,} 円"


def _plain(text: str) -> str:
    return ascii_parentheses(text.replace("`", ""))


def _require(text: str, report: Report, check: str, items: list[tuple[str, str]]) -> None:
    text = ascii_parentheses(text)
    missing = [label for label, needle in items if _plain(needle) not in text]
    if missing:
        report.fail(check, f"missing from the document: {missing}")
    else:
        report.ok(check, f"all {len(items)} expected statements present")


# --------------------------------------------------------------------- content
def check_guide_content(text: str, context, facts, report: Report, path: Path | None = None) -> None:
    """Every actionable statement the quality pass added must be present."""
    static = facts.static
    objects = context.kql_objects
    materialized = [entry for entry in objects if entry.command == "create-or-alter materialized-view"]
    raw_tables = [entry for entry in objects if entry.command == "create-merge table"]
    lakehouse_tables = len(context.expected["outputTableCounts"])
    if getattr(context, "is_unified_guide", False):
        check_unified_guide(context, text, report)

    # A2 - the KQL chapter is generated from the shipped script.
    _require(
        text,
        report,
        "content.kqlObjects",
        [(f"kql object {entry.name}", entry.name) for entry in objects]
        + [("management command count", f"{len(objects)} 個の管理オブジェクト")],
    )
    stale = [phrase for phrase, _ in RETIRED_WORDING if phrase in text]
    if stale:
        report.fail("content.retiredWording", f"retired wording still present: {stale}")
    else:
        report.ok("content.retiredWording", f"none of the {len(RETIRED_WORDING)} retired phrases appear")

    # A1 - the Data Agent must see the materialized view only.
    _require(
        text,
        report,
        "content.sourceSelection",
        [
            ("materialized view name", materialized[0].name),
            ("raw table name", raw_tables[0].name),
            ("materialized views menu", "Materialized views"),
            ("raw table deselection", "チェックは必ず外します"),
            ("T07 dependency", "T07"),
            ("lakehouse element count", str(lakehouse_tables)),
            ("ontology element count", str(context.ontology_contract["entityTypes"])),
        ],
    )

    # A3 - the English semantic fields belong to Notebook 02, not to the UI.
    _require(
        text,
        report,
        "content.nb02Ownership",
        [
            ("businessRole column", "業務上の役割（NB02 が登録）"),
            ("grain column", "粒度（NB02 が登録）"),
            ("synonym ownership", "同義語（NB02 が登録）"),
            ("semanticEnrichment", "semanticEnrichment"),
            ("not a UI field", "UI に入力欄がありません"),
        ],
    )

    # A4 - the time-series binding has a verifiable outcome.
    _require(
        text,
        report,
        "content.timeseriesGate",
        [
            ("observed municipality", facts.observation.top_observed_municipality_id),
            ("observed count", _num(facts.observation.top_observed_count)),
            ("observed amount", _yen(facts.observation.top_observed_amount_yen)),
            ("timestamp column", "DonatedAt"),
            ("key case mismatch", "MunicipalityID"),
            ("metadata gate", _num(context.metadata_object_count)),
        ],
    )

    # A5 - the layer model claims separated abstraction, not zero duplication.
    if "重複を排除しています" in text or "重複はありません" in text:
        report.fail("content.layerModel", "the guide still claims the three layers have zero duplication")
    else:
        report.ok("content.layerModel", "no zero-duplication claim")
    _require(
        text,
        report,
        "content.layerAbstraction",
        [
            ("abstraction wording", "抽象度の分担"),
            ("verbatim recopy", "一字一句の再掲"),
            ("global layer role", "抽象（判断基準）"),
            ("source layer role", "具体（列と関数）"),
        ],
    )

    # A6 - source CSV columns are not the published Delta columns.
    supplier_gift = context.relationship("SupplierProvidesGift")
    _require(
        text,
        report,
        "content.businessGiftsColumns",
        [
            ("source csv", "business_gifts.csv"),
            ("source columns", "BusinessID"),
            ("published table", supplier_gift.mapping_table),
            ("published origin key", supplier_gift.origin_key_column),
            ("published target key", supplier_gift.target_key_column),
        ],
    )

    # A7 - cardinality is declared metadata, and every relationship carries one.
    undeclared = [item.name for item in context.relationships if not item.cardinality]
    if undeclared:
        report.fail("content.cardinalityDeclared", f"relationships without cardinality: {undeclared}")
    else:
        report.ok(
            "content.cardinalityDeclared",
            f"{len(context.relationships)} / {len(context.relationships)} relationships declare a cardinality",
        )
    missing_cardinality = [
        item.name for item in context.relationships if _plain(item.cardinality) not in text
    ]
    if missing_cardinality:
        report.fail("content.cardinalityDocumented", f"cardinality missing for: {missing_cardinality}")
    else:
        report.ok("content.cardinalityDocumented", "every declared cardinality is printed in the guide")
    _require(
        text,
        report,
        "content.cardinalityGate",
        [
            ("no UI field", "UI にはカーディナリティの入力欄がありません"),
            ("gate heading", "カーディナリティを実データで確かめる"),
            ("many-to-one", "many-to-one"),
        ],
    )

    # A8 - the metric and flow entities are validated even though T01-T10 skip them.
    _require(
        text,
        report,
        "content.metricFlowGate",
        [
            ("metric instance id", static.metric_id),
            ("metric count", _num(static.metric_static_count)),
            ("metric amount", _yen(static.metric_total_yen)),
            ("municipality total count", _num(static.metric_municipality_total_count)),
            ("flow instance id", static.flow_id),
            ("flow reverse id", static.flow_reverse_id),
            ("flow count", _num(static.flow_static_count)),
            ("flow amount", _yen(static.flow_total_yen)),
            ("flow reverse count", _num(static.flow_reverse_static_count)),
            ("flow reverse amount", _yen(static.flow_reverse_total_yen)),
        ],
    )

    # A9 - troubleshooting is chapter-indexed and covers the new failure modes.
    rows = gc.troubleshooting_rows(context)
    chapters = [row[0] for row in rows]
    order = [int(re.search(r"[0-9]+", chapter).group()) for chapter in chapters]
    if order != sorted(order):
        report.fail("content.troubleshootingOrder", "troubleshooting rows are not in chapter order")
    else:
        report.ok("content.troubleshootingOrder", f"{len(rows)} troubleshooting rows in chapter order")
    _require(
        text,
        report,
        "content.troubleshootingRows",
        [
            ("mapping drift", "取り込んだ列が 1 つずつずれている"),
            ("pre-existing files", "トリガー作成直後に実行が走った"),
            ("subject empty", "Subject` が空のまま実行され"),
            ("raw table selection", "T07 で一意 EventID の件数が返ってくる"),
            ("activator naming", "Activator の名前が既定のままで判別できない"),
        ],
    )

    # A10 - the stale-lease trio is conditional, everything else always applies.
    _require(
        text,
        report,
        "content.staleLease",
        [(f"stale lease {name}", name) for name in STALE_LEASE_GROUP]
        + [("condition wording", "3 つを同時に設定")],
    )

    # A12 - the layer vocabulary matches the final diagram.
    _require(
        text,
        report,
        "content.layerVocabulary",
        [
            ("core entity layer", "基幹エンティティ層"),
            ("master count", f"マスタ {len(gc.MASTER_ENTITIES)}"),
            ("transaction count", f"トランザクション {len(gc.TRANSACTION_ENTITIES)}"),
            ("aggregate layer", "集計層"),
            ("seven plus three", "7 + 3"),
        ],
    )

    # A13 / A17 - the Activator is renamed and IncrementFileName stays diagnostic.
    _require(
        text,
        report,
        "content.activator",
        [
            ("activator name", context.names["activator"]),
            ("rename step", "Activator をリネームする"),
            ("first run gate", "導出されたファイル名"),
            ("subject empty warning", "Subject` が空のまま実行される"),
        ],
    )
    _require(
        text,
        report,
        "content.incrementFileName",
        [
            ("diagnostic wording", "ファシリテーター向けの診断"),
            ("parameter name", "IncrementFileName"),
        ],
    )

    # A15 - the published smoke set is fixed.
    for label in SMOKE_TESTS:
        if text.count(label) < 2:
            report.fail("content.smokeSet", f"{label} is not named in both chapter 18 and appendix C")
            break
    else:
        report.ok("content.smokeSet", f"the fixed smoke set {'/'.join(SMOKE_TESTS)} appears in both places")

    # A16 - the four production gates map onto workshop chapters.
    _require(
        text,
        report,
        "content.gateMapping",
        [
            ("mapping column", "本ワークショップでの対応"),
            ("gate 1 chapter", "第 4 章（設計根拠と意味の境界）"),
            ("gate 2 chapters", "第 10 章（件数・方向・カーディナリティ）"),
            ("gate 3 chapters", "第 16 章（3 層の設定）"),
            ("gate 4 chapter", "第 18 章（公開・固定スモーク"),
        ],
    )

    # A18 - the analytics union does not contradict T08.
    accepted = int(context.workspace_contract["analyticsExtension"]["dataQuality"]["acceptedDistinctEventIds"])
    static_rows = int(context.expected["donationRows"])
    _require(
        text,
        report,
        "content.analyticsUnion",
        [
            ("gold total", _num(static_rows + accepted)),
            ("rejected total", _num(static_rows + int(context.expected_increment["rawRows"]))),
            ("data source column", "DataSource"),
            ("t08 reference", "T08"),
            ("quarantine", "quarantine"),
        ],
    )

    # A19 - the optional UDF is named and bounded.
    _require(
        text,
        report,
        "content.udf",
        [
            ("udf path", context.udf_relative_path),
            ("self payment", "annualSelfPaymentYen"),
            ("before personal cap", "deductibleBeforePersonalCapYen"),
            ("not tax advice", "税務アドバイスではない"),
            ("t10 unchanged", "T10 は拒否のまま"),
        ],
    )

    # A20 - optional and reference paths are discoverable.
    _require(
        text,
        report,
        "content.optionalPaths",
        [
            ("ontology definitions", f"workshop/v{context.version}/ontology/"),
            ("provisioning", f"workshop/v{context.version}/provisioning/"),
            ("power bi project", f"workshop/v{context.version}/powerbi/"),
            ("variable library", f"workshop/v{context.version}/variable-library-template/"),
            ("tools powerbi", "tools/powerbi/"),
        ],
    )

    # A21 - each parameter table appears exactly once.
    duplicated: list[str] = []
    for key in sorted(context.notebooks):
        for row in build_parameter_rows(context, key):
            occurrences = text.count(row[0])
            if occurrences == 0:
                duplicated.append(f"{key}.{row[0]} missing")
    if duplicated:
        report.fail("content.parameterCoverage", f"{duplicated[:3]}")
    else:
        report.ok("content.parameterCoverage", "every notebook parameter is documented")
    _require(
        text,
        report,
        "content.appendixBIndex",
        [
            ("index title", "パラメーター索引"),
            ("location column", "完全な仕様表の場所"),
            ("nb01 location", "第 6.4 節"),
            ("nb02 location", "第 15.2 節"),
            ("nb03 location", "付録 D.1"),
            ("action column", "実施節"),
        ],
    )
    if "章" in text and "実施節" not in text:
        report.fail("content.parameterColumnRename", "the parameter table still uses the 章 column heading")
    else:
        report.ok("content.parameterColumnRename", "the parameter tables use the 実施節 column heading")

    # A14 - the variable library steps are Japanese, and the literal columns are labelled.
    english_steps = [
        step
        for step in context.workspace_contract["analyticsExtension"]["variableLibraryTemplate"]["manualSteps"]
        if step in text
    ]
    if english_steps:
        report.fail("content.variableLibrarySteps", f"untranslated manual steps: {english_steps}")
    else:
        report.ok("content.variableLibrarySteps", "every manual step is rendered in Japanese")
    _require(
        text,
        report,
        "content.variableLibraryOriginals",
        [("original label", "配布物の原文")],
    )

    # A22 - artefact noun and action verb are used consistently. バインド is a verb
    # stem here, so it is only wrong when a particle or terminator follows it
    # directly, which means it was used as a noun.
    noun_use = re.compile(r"バインド(?=[、。」）\s]|$)")
    offenders = [match.group(0) for match in noun_use.finditer(text)]
    if offenders:
        sample = next(iter(noun_use.finditer(text)))
        report.fail(
            "content.bindingVocabulary",
            f"バインド is used as a noun {len(offenders)} time(s), e.g. "
            f"…{text[max(0, sample.start() - 20):sample.end() + 8]}…",
        )
    else:
        report.ok("content.bindingVocabulary", "バインディング is the artefact noun, バインドする the action")

    check_v3_corrections(context, facts, text, report)
    check_diagram_vocabulary(context, text, report)
    if path is not None:
        check_typography(prose_paragraphs(path), report, canvas_phrases(context))


def check_v3_corrections(context, facts, text: str, report: Report) -> None:
    """The nine content corrections from the final focused pass."""
    files = context.increment_files
    contract = context.ontology_contract
    flat = re.sub(r"\s+", " ", text)

    # 1 - the first increment file is ingested once, in chapter 12.4.
    upload_first = len(re.findall(rf"{re.escape(files[0]['file'])} をアップロード", text))
    if upload_first:
        report.fail(
            "content.singleIngestion",
            f"{files[0]['file']} still has {upload_first} upload instruction(s) after chapter 12.4",
        )
    else:
        report.ok("content.singleIngestion", f"{files[0]['file']} is uploaded only once, in chapter 12.4")
    _require(
        text,
        report,
        "content.alreadyIngestedWarning",
        [
            ("already ingested", f"第 12.4 節で `{files[0]['file']}` は取り込み済み"),
            ("do not re-upload", "再アップロードしないでください"),
            ("upload 002", f"{files[1]['file']} をアップロードし"),
            ("upload 003", f"{files[2]['file']} をアップロードし"),
        ],
    )

    # 2 - Notebook 02 is fail-closed, so a missing time-series property means zero
    # registered objects, not a partial 97.
    partial = re.search(r"登録件数[^。]{0,20}97", flat)
    if partial or "97 件になります" in flat:
        report.fail("content.failClosed", "the guide still implies a partial 97-object registration")
    else:
        report.ok("content.failClosed", "no partial-registration claim")
    _require(
        text,
        report,
        "content.failClosedMessage",
        [
            (
                "preflight message",
                f"Count mismatch for timeseriesProperties: Ontology has 0, manifest expects "
                f"{contract['timeseriesProperties']}",
            ),
            ("zero registered", "登録件数は 0 件"),
            ("precondition total", f"= {context.metadata_object_count - contract['timeseriesProperties']}"),
            ("required total", f"= {context.metadata_object_count}"),
            ("no partial apply", "部分適用はありません"),
        ],
    )

    # 3 - the metric entity count is observed pairs, not the cross product.
    possible = context.node_count("Prefecture") * context.node_count("GiftCategory")
    _require(
        text,
        report,
        "content.metricPairs",
        [
            ("observed pairs", _num(context.node_count("PrefectureCategoryMetric"))),
            ("possible pairs", _num(possible)),
            ("at least one donation", "寄付が 1 件以上あったもの"),
            ("not a cross product", "あり得る組"),
        ],
    )

    # 4 - the stale-lease callout lives with Notebook 01.
    lease_index = text.rfind("stale lease 回復用の 3 パラメーター")
    section_64 = text.rfind("6.4 Notebook 01 のパラメーター")
    chapter_7 = text.rfind("7. Ontology を作成する")
    if lease_index < 0:
        report.fail("content.staleLeasePlacement", "the stale-lease callout is missing")
    elif not (section_64 >= 0 and section_64 < lease_index < chapter_7):
        report.fail(
            "content.staleLeasePlacement",
            "the stale-lease callout is not inside section 6.4",
        )
    else:
        report.ok("content.staleLeasePlacement", "the stale-lease callout sits with the Notebook 01 parameters")
    if "それ以外は常に適用" in flat:
        report.fail("content.staleLeaseWording", "the confusing それ以外は常に適用 sentence is still present")
    else:
        report.ok("content.staleLeaseWording", "no それ以外は常に適用 wording")

    # 5 - every parameter points at the section that holds its full table.
    wrong: list[str] = []
    for key in sorted(context.notebooks):
        section = PARAMETER_SECTION[key]
        for row in build_parameter_rows(context, key):
            if row[7] != section:
                wrong.append(f"{key}.{row[0]}={row[7]!r}")
    if wrong:
        report.fail("content.parameterSections", f"wrong 実施節: {wrong[:5]}")
    else:
        total = sum(len(build_parameter_rows(context, key)) for key in context.notebooks)
        report.ok(
            "content.parameterSections",
            f"all {total} parameters point at the section holding their full table",
        )
    for stale_section in ("付録 B", ):
        if any(
            row[7] == stale_section
            for key in context.notebooks
            for row in build_parameter_rows(context, key)
        ):
            report.fail("content.parameterSectionStale", f"a parameter still points at {stale_section}")
            break
    else:
        report.ok("content.parameterSectionStale", "no parameter points at 付録 B or a bare 付録 D")

    # 6 - all seven decisions, including the associative-entity branch.
    _require(
        text,
        report,
        "content.decisionTree",
        [
            ("audit only", "監査・制御・技術メタデータ専用か"),
            ("one value", "既存エンティティに対し 1 件 1 値か"),
            ("pure bridge", "2 つの外部キーだけの純粋な中間表か"),
            ("associative", "独自の属性・ライフサイクルを持つ中間表か"),
            ("associative outcome", "連関エンティティ（Associative Entity）"),
            ("composite grain", "複合粒度の事前集計か"),
            ("transaction", "安定した識別子・金額・時刻・状態を持つ取引か"),
            ("timed observation", "既存エンティティへの時刻付き観測か"),
            ("event entity", "イベントエンティティ（Event Entity）"),
            ("property outcome", "Property（既存 Entity Type の属性）"),
        ],
    )

    # 7 - source selection is the second triage step.
    triage = text.rfind("17.11 不合格時の修正順序")
    window = text[triage : triage + 1200] if triage >= 0 else ""
    if "第 16.2 節の選択表" in window and "チェックが外れているか" in window:
        report.ok("content.triageSourceSelection", "chapter 17.11 checks the source selection before the instructions")
    else:
        report.fail("content.triageSourceSelection", "chapter 17.11 does not check the source selection second")

    check_v4_corrections(context, text, report)


#: Wording the final micro pass removed. Each entry is (phrase, why it is wrong).
STALE_V4_PHRASES = (
    ("Notebook 01 / 02 共通", "the lease parameters exist only in Notebook 01"),
    ("Notebook 02 にもあり、扱いは同じ", "Notebook 02 has no lease parameters"),
    ("増分 3 ファイルの順次アップロードと KQL 検証", "chapter 13 covers only the remaining two files"),
    ("0 件も登録されません", "Japanese counts a zero result as 1 件も登録されません"),
    ("の2 通り", "a digit needs a space before it in Japanese body text"),
)


def check_v4_corrections(context, text: str, report: Report) -> None:
    """The final micro corrections: factual wording, roadmap split and spacing."""
    present = [f"{phrase!r} ({why})" for phrase, why in STALE_V4_PHRASES if phrase in text]
    if present:
        report.fail("content.staleWordingV4", f"retired wording still present: {present}")
    else:
        report.ok(
            "content.staleWordingV4",
            f"none of the {len(STALE_V4_PHRASES)} retired phrases appear",
        )
    _require(
        text,
        report,
        "content.leaseScope",
        [
            ("title scope", "stale lease 回復用の 3 パラメーター（Notebook 01 のみ）"),
            ("only in NB01", "この 3 つは Notebook 01 にしかありません"),
            ("NB02 has none", "Notebook 02 に lease のパラメーターはなく"),
            ("NB02 alternative", "EXCLUSIVE_APPLY_WINDOW_CONFIRMED"),
            ("NB02 section", "第 15.2 節"),
        ],
    )
    _require(
        text,
        report,
        "content.roadmapSplit",
        [
            ("first file row", "増分 1 本目の取り込みと導出結果の確認"),
            ("first file section", "第 12.4 節"),
            ("remaining files row", "残り 2 ファイルの取り込みと KQL 検証"),
        ],
    )
    _require(text, report, "content.t03Spacing", [("two readings", "の 2 通りに読める")])
    _require(text, report, "content.zeroGrammar", [("zero registered", "1 件も登録されません")])
    check_v5_corrections(context, text, report)


#: Spacing defects that a Japanese technical document must not contain.
#:
#: ``SPACE_PAREN`` catches an ASCII token separated from a fullwidth parenthesis
#: by a space. The fullwidth glyph already carries its own side bearing, so the
#: extra space renders as a visible gap. ``KANA_DIGIT`` catches an ASCII digit
#: glued to the preceding kana or kanji; Japanese body text puts a space there.
#: ``・`` lives in the katakana block but is a list separator, and the
#: ``年月日`` counters are written closed, so both are excluded.
#: ``KANA_DIGIT`` catches an ASCII digit glued to the preceding kana or kanji;
#: Japanese body text puts a space there. ``年月日`` are counters written closed
#: onto the next number (2025年12月), and ``・`` lives in the katakana block but
#: is a list separator, so both are excluded from the leading character.
SPACE_PAREN = re.compile(r"[A-Za-z0-9_)\]] +（")
KANA_DIGIT = re.compile(r"(?![年月日・])[\u3040-\u30f9\u3400-\u4dbf\u4e00-\u9fff]\d")


def check_v5_corrections(context, text: str, report: Report) -> None:
    """Procedure re-audit: localisation, triage order, labelling and spacing."""
    increment = context.expected_increment
    files = context.increment_files

    # 1 - the duplicate layout is stated in Japanese, not pasted from the manifest.
    layout = increment["duplicateLayout"]
    if layout in text:
        report.fail(
            "content.duplicateLayoutLocalised",
            f"the English manifest sentence {layout!r} is pasted into the Japanese guide",
        )
    else:
        report.ok(
            "content.duplicateLayoutLocalised",
            "table 51 states the duplicate layout in Japanese instead of pasting the manifest sentence",
        )
    _require(
        text,
        report,
        "content.duplicateLayoutSentence",
        [
            ("file names", f"`{files[0]['file']}` の末尾"),
            ("reappearance", f"`{files[1]['file']}` の先頭"),
        ],
    )

    # 2 - chapter 19 no longer over-claims, and 17.11 checks the service before a rerun.
    if "各章の末尾にも" in text:
        report.fail("content.chapter19Scope", "the chapter 19 preamble still claims every chapter has a pointer")
    else:
        report.ok("content.chapter19Scope", "the chapter 19 preamble says 該当する章 rather than 各章")
    triage = text.rfind("17.11 不合格時の修正順序")
    window = text[triage : triage + 2000] if triage >= 0 else ""
    service = window.find("サービス側の要因")
    rerun = window.find("10 問すべてを最初からやり直す")
    if service >= 0 and rerun > service and "最大 2 回" in window:
        report.ok(
            "content.triageServiceStep",
            "chapter 17.11 checks the service-side factor, with the retry bound, before the full rerun",
        )
    else:
        report.fail(
            "content.triageServiceStep",
            "chapter 17.11 does not place a bounded service-side retry step before the full rerun",
        )

    # 3 - the appendix A.4 leader is labelled as a raw, duplicate-retaining value.
    _require(
        text,
        report,
        "content.appendixRawLeader",
        [
            ("raw heading", "観測 1 位の自治体（raw）"),
            ("raw count", "raw 観測"),
            ("raw amount", "raw 観測金額"),
            ("duplicates retained", "重複 EventID を保持したままの raw 値"),
        ],
    )

    # 5 - spacing defects. A table-of-contents entry is the heading text with the
    # page number appended straight onto it, so every entry looks like a missing
    # space. Word writes that leader, not the document source; the trailing page
    # number is removed before the line is scanned.
    defects: list[str] = []
    for raw_line in text.splitlines():
        line = re.sub(r"\d+$", "", raw_line.rstrip())
        for label, pattern in (("ascii-space-fullwidth-paren", SPACE_PAREN), ("kana-digit", KANA_DIGIT)):
            for match in pattern.finditer(line):
                start = max(0, match.start() - 20)
                defects.append(f"{label}: ...{line[start:match.end() + 10]}...")
    if defects:
        report.fail("content.spacingDefects", f"{len(defects)} spacing defects: {defects[:4]}")
    else:
        report.ok("content.spacingDefects", "no ASCII/fullwidth spacing defects in the guide body")

    # 6 - chapter 16.2 covers creation, so every figure maps to a numbered step.
    _require(
        text,
        report,
        "content.agentCreationSteps",
        [
            ("heading", "16.2 Data Agent と共有ソースを確認する"),
            ("existing target safety", "既存なら一致確認または承認された移行を先に完了"),
            ("create only when absent", "未作成の場合だけ"),
            ("new dialog", "Create data agent ダイアログ"),
            ("discovery identity", "実際に discovery された名前・type・path"),
            ("tool verification", "［Tools］で Code Interpreter を有効"),
        ] if getattr(context, "is_unified_guide", False) else [
            ("heading", "16.2 Data Agent を作成してソースを追加する"),
            ("new menu", "［新規］→［Data agent］を選びます"),
            ("create dialog", "Create data agent ダイアログ"),
            ("post-create screen", "作成直後の画面"),
            ("explorer runtime", "追加後の Explorer で 3 ソースが並び"),
        ],
    )

    # 8 - the record sheet and the guide use one label for the route field.
    if "期待するソースルート" in text:
        report.fail("content.routeLabel", "the guide still uses the old 期待するソースルート label")
    else:
        report.ok("content.routeLabel", "the route field is labelled 期待するルート")

    check_preview_material_handling(context, text, report)


#: Wording that would turn unpublished preview material, or a volatile platform
#: figure, into something the guide appears to warrant. Each entry is a pattern
#: plus why it is refused, so a failure explains itself.
#:
#: ``UNPUBLISHED_LABELS`` is matched against the document as written: a product
#: mode name or a confidentiality marking is wrong wherever it appears, quoted or
#: not. ``UNPUBLISHED_ASSERTIONS`` is matched with Japanese quotation spans
#: blanked, because the guide deliberately quotes the sentences it refuses to
#: make -- 「プレビュー中は無償」と説明しない is the instruction, not the claim.
UNPUBLISHED_LABELS = (
    (re.compile(r"\bPlan mode\b|\bAct mode\b", re.I), "an unpublished product mode label"),
    (
        re.compile(r"Confidential|Internal Only|機密|社外秘|社内限り|部外秘|社内環境の識別子|取扱注意", re.I),
        "a confidentiality marking, or a characterisation of supplied material as confidential",
    ),
)

UNPUBLISHED_ASSERTIONS = (
    (re.compile(r"プレビュー(?:中|期間中)は無償|プレビュー(?:中|期間中)は無料|free during (?:the )?preview", re.I),
     "a preview pricing concession that is not published"),
    (re.compile(r"(?:1 ?)?(?:操作|リクエスト|クエリ)(?:あたり|ごと)の(?:課金額|料金|価格)は[^。]*?[0-9]"),
     "a per-operation price for an unpublished feature"),
    (re.compile(r"(?:EU Data Boundary|EU データ境界|EUDB)[^。]*?(?:準拠|適合|非準拠|不適合)"),
     "a per-feature EU Data Boundary conformance claim"),
    (re.compile(r"(?:最大|上限)[^。]{0,12}?[0-9][0-9,]*\s*(?:行|ファイル|MB|GB)[^。]{0,8}?(?:まで|が上限|の上限)"),
     "an unpublished row, file or size ceiling"),
    (re.compile(r"明示的な同意[^。]{0,24}?(?:収集|送信|テレメトリ)|(?:収集|送信|テレメトリ)[^。]{0,24}?明示的な同意"),
     "an explicit-consent telemetry claim that is not published"),
)

_QUOTED_SPAN = re.compile(r"[「『][^」』]*[」』]")

#: Retention wording for a *conversation* must never sit next to a duration. The
#: guide states that retention differs by feature and tenant setting and stops
#: there. The Eventhouse table retention policy is a runtime contract with its
#: own published number, so only conversational retention is matched here.
_RETENTION_CONTEXT = re.compile(
    r"[^。]*(?:プロンプト|対話|会話)[^。]*(?:保持|保存期間)[^。]*。"
    r"|[^。]*(?:保持|保存期間)[^。]*(?:プロンプト|対話|会話)[^。]*。"
)
_DURATION = re.compile(r"[0-9][0-9,]*\s*(?:日|日間|時間|か月|ヶ月)")

#: The Word section boundaries used to isolate D.6 from the rest of the guide.
#: ``rfind`` picks the body heading rather than the contents listing entry. D.7
#: now follows D.6, so the section ends where D.7 begins.
_D6_START = "D.6 Ontology の編集を生成 AI に任せる場合の評価観点"
_D6_END = "D.7 Semantic Model を Data Agent ソースとして追加する場合"
_D6_AUTHORING_HISTORY = (
    re.compile(r"この節のもとになった資料|提供された資料|資料に含まれていた情報"),
    re.compile(r"\d{4}\s*年\s*\d{1,2}\s*月\s*\d{1,2}\s*日に提供された"),
    re.compile(r"読んだうえで採用|採用しなかった|この節はすべて書き下ろし"),
    re.compile(r"(?:materials?|pages|documents?)\b[^.!?\n]{0,100}\b(?:were|was)\s+(?:supplied|provided|received)\s+on\b", re.I),
    re.compile(r"deliberately not adopted|reviewed but not adopted|read (?:it |them )?but (?:did )?not adopt", re.I),
)


def _section(text: str, start: str, end: str) -> str:
    text = ascii_parentheses(text)
    head = text.rfind(ascii_parentheses(start))
    if head < 0:
        return ""
    tail = text.find(ascii_parentheses(end), head)
    return text[head:tail] if tail > head else text[head:]


def check_preview_material_handling(context, text: str, report: Report) -> None:
    """Appendix C.6 / D.6 coverage, isolation and the claims they must not make.

    D.6 is a general reference for evaluating AI-assisted Ontology editing, not
    an authoring record or a product-capability promise. Keep its design and
    source boundaries outside the Core verdict, require verification against
    current public documentation, and reject volatile or confidential claims.
    """
    # 1 - appendix C.6 covers the ten platform prerequisites.
    _require(
        text,
        report,
        "content.appendixC6Coverage",
        [
            ("heading", "C.6 ガバナンス・責任ある AI・コストの前提"),
            ("published basis", "公開されている Microsoft のドキュメントに基づきます"),
            ("no residency warranty", "個別のコンプライアンス適合を保証するものではありません"),
            ("preview terms", "Azure プレビュー補足条項"),
            ("identity", "Entra ID のサインイン"),
            ("underlying source access", "参照元 Lakehouse・Eventhouse・Ontology の読み取り権限"),
            ("no model training", "顧客データは基盤モデルの学習に使われず"),
            ("human review", "内容を評価できる人が使う前に確認する必要がある"),
            ("english first", "英語で最もよく動作し"),
            ("japanese caveat", "日本語で不安定に見えたときは"),
            ("retention varies", "機能とテナント設定によって異なる"),
            ("no day count", "本書は日数を書かない"),
            ("capacity region", "処理される地域は容量のリージョンで決まる"),
            ("tenant control described", "リージョン外処理を許可する Copilot テナント設定"),
            ("exact name deferred to appendix E", "設定の正確な名称は付録 E の Copilot tenant settings を参照する"),
            ("purview", "Purview の情報保護・保護ポリシー・DLP"),
            ("cmk matrix", "対応するアイテム種別が一覧で公開されている"),
            ("cmk not assumed", "CMK に対応していると仮定しない"),
            ("token based", "処理されたトークン量に応じた容量ユニット"),
            ("conversation length", "対話や文脈が長いほど消費は増える"),
            ("metrics app", "Fabric Capacity Metrics アプリの `Copilot in Fabric`"),
            ("no rate printed", "本書には変わりうるレートを書かない"),
            ("no free preview claim", "「プレビュー中は無償」と説明しない"),
            ("gate count unchanged", "C.6 はゲートを増やしません"),
        ],
    )

    # 2 - appendix D.6 covers the participant's evaluation and verification needs.
    _require(
        text,
        report,
        "content.appendixD6Coverage",
        [
            ("heading", "D.6 Ontology の編集を生成 AI に任せる場合の評価観点（実施対象外）"),
            ("evaluation reference", "生成 AI による Ontology 編集支援を評価するための参考情報です"),
            ("not a capability promise", "特定の製品機能の提供や動作を保証するものではありません"),
            ("human scope and review", "変更してよい範囲を先に決め、人が変更案の根拠と影響を確認します"),
            ("not a procedure", "ここに書いてあるのは手順ではなく、この節に実施する操作はありません"),
            ("optional exercises are D.1-D.5", "D.1 から D.5 は、Core の外にある実習です"),
            ("D.6 is not an exercise", "D.6 だけは実習ではありません。読んで評価の観点を持ち帰るための参考情報であり、実施する操作は含みません"),
            ("no impact", "Core の流れ、ランタイムの選択、第 10 章と第 17 章の判定、付録 A、"
                          "および数値契約のいずれにも影響しません"),
            ("conceptual diagram", "図は評価工程を示す概念図であり、製品の UI や機能一覧ではありません"),
            ("consumer vs author", "D.6.1 Data Agent と Ontology 編集支援は別物"),
            ("lifecycle", "D.6.2 安全なライフサイクルと評価の観点"),
            ("phase 1", "1. 証拠の発見"),
            ("phase 2", "2. ドメイン設計"),
            ("phase 3", "3. 構造とグラウンディングの検証"),
            ("phase 4", "4. 読み取り専用プレビューと確認"),
            ("phase 5", "5. 明示的な書き込みゲートで適用"),
            ("no product mode names", "未公開の名称は契約になりません"),
            ("categories", "評価の切り口。特定製品がこの 3 つを提供すると主張するものではない"),
            ("matrix", "本ワークショップに関係する 4 つのソースと、その評価上の境界"),
            ("gql", "ISO GQL"),
            ("generate vs ground vs bind", "生成・グラウンディング・バインディングは別"),
            ("generate source cited", "https://learn.microsoft.com/en-us/fabric/iq/ontology/concepts-generate"),
            ("routing is its own contract", "どのソースを使うかは Data Agent 側の設定であり"),
            ("best practices", "D.6.3 実務での保護と公開情報の確認"),
            ("standard-track example", "標準コースの教材用 Ontology"),
            (
                "reference-track boundary",
                "旧プロファイルの扱いは第 16.9 節で確認してください"
                if getattr(context, "is_unified_guide", False)
                else "AI 参照構成の別モデルとソース選択は第 16.9 節で確認してください",
            ),
            ("composite keys supported", "複合キーはプラットフォームとしてサポートされています"),
            ("scenario", "このシナリオで、人の確認なしに変えてはいけない 4 つの境界"),
            ("manifest canonical", "Notebook 02 の manifest が正本です"),
            ("other authoring tools", "別の編集手段から同じ Ontology を書き換えないでください"),
            ("troubleshooting", "評価時の切り分け。上限値のような未公開の数値は使わない"),
            ("availability triage", "公開プレビューの提供状況・テナント設定・リージョン"),
            ("zero rows triage", "グラフモデルを手動で更新する"),
            ("draft triage", "未適用の下書きが残る前提を置かない"),
            ("public verification topics", "公開ドキュメントで確認する 8 つの主題"),
            ("current feature conditions", "対象機能と条件が現行の公式ドキュメントに記載されていることを確認します"),
            ("no unsupported assumptions", "確認できない能力や数値は未確認として扱い、利用者への約束や適用の根拠にしません"),
        ],
    )

    # 3 - D.6 stays an appendix: it never touches a test identifier or a verdict.
    section = _section(text, _D6_START, _D6_END)
    if not section:
        report.fail("content.appendixD6Isolation", "appendix D.6 not found in the guide")
    else:
        leaks = sorted(set(re.findall(r"\bT(?:0[1-9]|10)\b", section)))
        verdicts = [word for word in ("PASS", "FAIL", "UNCLEAR", "EXECUTION_ERROR") if word in section]
        contracts = [
            phrase
            for phrase in ("DRY_RUN_COMPLETE", "APPLY_CHANGES", "PARTICIPANT_ID")
            if phrase in section
        ]
        if leaks or verdicts or contracts:
            report.fail(
                "content.appendixD6Isolation",
                f"D.6 references Core test ids {leaks}, verdicts {verdicts} or runtime parameters {contracts}",
            )
        else:
            report.ok(
                "content.appendixD6Isolation",
                f"D.6 ({len(section)} chars) names no held-out test, verdict or runtime parameter",
            )

    history = [
        match.group(0)
        for pattern in _D6_AUTHORING_HISTORY
        for match in pattern.finditer(section)
    ]
    if history:
        report.fail("content.appendixD6AuthoringHistory", f"D.6 contains authoring history: {history}")
    else:
        report.ok("content.appendixD6AuthoringHistory", "D.6 contains participant reference, not material-provenance or adoption history")

    # 4 - no volatile or confidential claims are presented as product facts.
    unquoted = _QUOTED_SPAN.sub("「」", text)
    hits = [
        f"{match.group(0)!r} ({why})"
        for pattern, why in UNPUBLISHED_LABELS
        for match in [pattern.search(text)]
        if match
    ]
    hits += [
        f"{match.group(0)!r} ({why})"
        for pattern, why in UNPUBLISHED_ASSERTIONS
        for match in [pattern.search(unquoted)]
        if match
    ]
    retention_with_duration = [
        sentence.strip()
        for sentence in _RETENTION_CONTEXT.findall(text)
        if _DURATION.search(sentence)
    ]
    if hits or retention_with_duration:
        report.fail(
            "content.noUnpublishedClaims",
            f"{hits}; retention sentences carrying a duration: {retention_with_duration[:2]}",
        )
    else:
        report.ok(
            "content.noUnpublishedClaims",
            f"none of the {len(UNPUBLISHED_LABELS) + len(UNPUBLISHED_ASSERTIONS)} unpublished-claim "
            "patterns appear, and no conversation-retention sentence carries a duration",
        )

    # 5 - the two public-safe Core corrections are actually in the Core chapters.
    _require(
        text,
        report,
        "content.namingRuleAndRefresh",
        [
            ("rule covers both kinds", "Entity Type の名前とカスタム Property の名前には、同じ公式の規則があります"),
            ("naming rule", "1〜26 文字で、英数字・ハイフン・アンダースコアだけを使い、先頭と末尾は英数字にします"),
            ("rule basis cited", "付録 E の Create entity types と Bind data"),
            ("entity type at the ceiling", "MunicipalityCategoryMetric"),
            ("property at the ceiling 1", "MunicipalityPrefAmountRank"),
            ("property at the ceiling 2", "MunicipalityStaticTotalYen"),
            ("all three at the published ceiling", "がいずれも 26 文字で、現在公開されている上限ちょうどです"),
            ("schema refresh is automatic", "downstream へ自動的に反映される一方"),
            ("manual refresh", "［Schedule］から［Refresh now］を選びます"),
            ("batch refreshes", "まとめてから 1 回実行してください"),
            ("chapter 7 pointer", "評価の観点として読みたい場合は付録 D.6 にまとめてあります"),
            ("chapter 16 boundary", "Ontology の定義そのものを書き換える編集支援ではありません"),
        ],
    )
    # The published rule covers entity type names *and* custom property names, and
    # both how-to pages state it. Narrowing it back to entity types, or claiming a
    # documentation gap for property names, is the regression this gate catches.
    narrowed = [
        phrase
        for phrase in (
            "公開ドキュメントに長さの上限が示されていない",
            "本書でも上限は主張しません",
            "名前の規則が公式に決まっているのは Entity Type の名前です",
            "Entity Type の名前には公式の規則があります",
        )
        if _plain(phrase) in text
    ]
    scoped_to_properties = [
        phrase
        for phrase in (
            "カスタム Property の名前",
            "Entity Type の名前とカスタム Property の名前の両方に適用されます",
        )
        if _plain(phrase) not in text
    ]
    if narrowed or scoped_to_properties:
        report.fail(
            "content.namingRuleScope",
            f"the 1-26 rule is narrowed away from property names: retired wording {narrowed}, "
            f"missing property scope {scoped_to_properties}",
        )
    else:
        report.ok(
            "content.namingRuleScope",
            "the 1-26 rule is stated for entity type names and custom property names alike, "
            "with both published how-to pages cited",
        )

    # 6 - reference links stay first-party, current and in the /en-us/ form.
    urls = [url for _title, url in gc.REFERENCE_LINKS]
    problems: list[str] = []
    problems += [url for url in urls if url.startswith("https://learn.microsoft.com") and "/en-us/" not in url]
    problems += [url for url in urls if "get-started/copilot-" in url]
    problems += [
        url
        for url in urls
        if not url.startswith(
            ("https://learn.microsoft.com/", "https://azure.microsoft.com/", "https://www.microsoft.com/")
        )
    ]
    printed = set(re.findall(r"https?://[^\s、。（）「」]+", text))
    unprinted = [url for url in urls if url not in printed]
    if problems or unprinted:
        report.fail(
            "content.referenceLinkHygiene",
            f"malformed or third-party: {problems}; declared but not printed: {unprinted}",
        )
    else:
        report.ok(
            "content.referenceLinkHygiene",
            f"all {len(urls)} reference URLs are first-party, /en-us/ where applicable, and printed in appendix E",
        )


#: Section boundaries for the public-source Data Agent practice update. Each new
#: block is isolated by its own heading so a gate can scan exactly that block
#: rather than the whole guide.
PRACTICE_SECTIONS = (
    ("16.6.1", "16.6.1 例クエリの品質ゲート", "16.7 ランタイムと Core の既定設定"),
    ("16.8", "16.8 指示で守る境界と、応答時間の変数", "16.9 AI 参照アーキテクチャ（明示 opt-in）"),
    ("17.12", "17.12 実行証跡と、やり直す条件", "18. Publish・スモークテスト・共有"),
    ("18.2", "18.2 公開説明に書く 5 項目", "19. トラブルシューティング"),
    ("C.7", "C.7 継続評価と ALM", "付録 D\u3000Optional"),
    ("D.7", "D.7 Semantic Model を Data Agent ソースとして追加する場合", "付録 E\u3000参考リンク"),
)

#: Sections whose subject is configuration or lifecycle, never a Core verdict.
#: 17.12 and 18.2 are deliberately absent: chapter 17 owns the verdicts and
#: chapter 18 owns the fixed smoke set, so naming them there is the point.
PRACTICE_ISOLATED = ("16.6.1", "16.8", "C.7", "D.7")

#: A held-out test identifier. ``\b`` is not used: a Japanese character is a word
#: character, so ``\bT07\b`` would silently miss ``…ゲートT07``. The class-based
#: guards match the identifier wherever it is embedded.
PRACTICE_TEST_ID = re.compile(r"(?<![0-9A-Za-z])T(?:0[1-9]|10)(?![0-9A-Za-z])")

#: Claims the new sections must not make. Forward-looking release language and
#: roadmap directives age badly; CU arithmetic and per-token rates are volatile
#: and already refused by C.6; API, SDK and MCP fragments would turn a reading
#: section into an unmaintainable code sample.
PRACTICE_FORBIDDEN = (
    (re.compile(r"近日|まもなく提供|今後提供|将来のリリース|次期リリース"), "forward-looking release language"),
    (re.compile(r"ロードマップ|roadmap", re.I), "roadmap directive"),
    (re.compile(r"プライベート\s*プレビュー|private preview", re.I), "private-preview reference"),
    (re.compile(r"一般提供(?:予定|開始)|generally available", re.I), "GA-date language"),
    (re.compile(r"\d[\d,]*\s*CU|CU\s*(?:秒|分)"), "capacity-unit arithmetic"),
    (re.compile(r"1[,，]?000\s*(?:トークン|tokens)", re.I), "per-token rate arithmetic"),
    (re.compile(r"%pip|\bimport\s+[a-z_]+|\bdef\s+[a-z_]+\(", re.I), "code snippet"),
    (re.compile(r"\bSDK\b|\bMCP\b|REST API|\bcurl\b", re.I), "API, SDK or MCP fragment"),
    (re.compile(r"サービス\s*プリンシパル|service principal", re.I), "service-principal detail"),
)


def check_data_agent_practice(context, text: str, report: Report) -> None:
    """The public-source Data Agent practice update is present and stays public-safe.

    Six blocks were added from first-party Microsoft documentation: the example
    query quality gate, the instruction-boundary and latency section, the
    evidence and re-run section, the publish-description contract, the continuous
    evaluation and ALM appendix, and the semantic-model reference appendix. These
    gates prove each block is present, that the two reframed statements no longer
    claim more than the sources support, and that none of the blocks smuggles in
    a volatile figure, a roadmap promise or a code sample.
    """
    shots = context.agent_fewshots

    # 1 - chapter 16.3 states the character budget as this workshop's own
    #     contract rather than as a platform warranty.
    _require(
        text,
        report,
        "content.instructionBudgetFraming",
        [
            ("workshop budget", "グローバル指示の上限は、本ワークショップでは"),
            ("safety side", "これは本ワークショップが自分に課した安全側の上限であり"),
            ("complete supplied instructions", "この上限の内側に収まっています"),
            ("not a warranty", "製品スキーマとして公開された保証値や、将来にわたって変わらない値として引用しないでください"),
            ("check current docs", "その時点の製品ドキュメントと画面表示で現在値を確認してください"),
        ],
    )
    universal = [
        phrase
        for phrase in (
            "Fabric の Data agent 画面が受け付ける上限は 15,000 文字",
            "Fabric の上限は 15,000 文字",
        )
        if _plain(phrase) in text
    ]
    if universal:
        report.fail(
            "content.instructionBudgetNotUniversal",
            f"the guide still states the budget as a universal Fabric limit: {universal}",
        )
    else:
        report.ok(
            "content.instructionBudgetNotUniversal",
            "the character budget is never stated as a universal, permanent Fabric limit",
        )

    # 2 - chapter 16.5 explains the KQL shapes as a fact about this bundle.
    _require(
        text,
        report,
        "content.kustoShapeRationale",
        ([
            ("profile examples", "この統合プロファイルでは Eventhouse の例クエリも登録します"),
            ("pinned example artifact", "kusto-fewshots.json"),
            ("same-version instructions", "ソース指示を同じ版で照合"),
        ] if getattr(context, "is_unified_guide", False) else [
            ("distribution fact", "本教材では Eventhouse の例クエリは別途登録せず"),
            ("colocation reason", "列名・粒度の規則と同じ場所に形を置くことで"),
        ]) + [
            ("not a capability claim", "という製品全体の能力の説明ではありません"),
            ("defer to appendix E", "付録 E の Data Agent source capability matrix"),
        ],
    )
    retired_capability = [
        phrase
        for phrase in ("定義形式に例クエリの領域が無いため", "定義形式に例クエリの領域がないため")
        if _plain(phrase) in text
    ]
    if retired_capability:
        report.fail(
            "content.kustoShapeNotCapability",
            f"the guide still claims the definition format has no example-query area: {retired_capability}",
        )
    else:
        report.ok(
            "content.kustoShapeNotCapability",
            "the KQL shape placement is stated as a property of the shipped bundle, not of the product",
        )

    # 3 - the example-query quality gate covers every published best practice.
    _require(
        text,
        report,
        "content.exampleQueryGate",
        [
            ("heading", "16.6.1 例クエリの品質ゲート"),
            ("question maps to query", "質問文が求める指標・期間・絞り込みが、そのままクエリの列と述語に現れている"),
            ("distinct shapes", "例ごとに入口のテーブルと集計の形を変え、言い換えただけの例を増やさない"),
            ("no conflicting intent", "同じ意図の問いに対して、違うテーブルや違う集計を返す例を同居させない"),
            ("stored value formats", "絞り込みの値は、実際に格納されている表記と形式のまま書く"),
            ("schema existence", "参照するテーブルと列が、選択済みのスキーマの中に実在する"),
            ("validate", "登録した例が検証を通ることを確認する"),
            ("run details", "回答の［実行詳細］で、その質問にどの例が使われたかを確認する"),
            ("held-out", "評価に使う問いの文・期待値・安定 ID を、例クエリに含めない"),
            ("entry table gate", "入口のテーブルは重複させない"),
            ("no top-n promise", "上位いくつが渡されるかは本書では固定しません"),
            ("sources disagree", "公開ドキュメントの記述も一致していないため"),
        ],
    )
    entry_tables = [_first_from(shot.get("query", "")) for shot in shots]
    stated = [table for table in entry_tables if _plain(f"`{table}`") in text]
    if entry_tables and len(set(entry_tables)) == len(entry_tables) and len(stated) == len(entry_tables):
        report.ok(
            "content.exampleEntryTablesStated",
            f"the guide names all {len(entry_tables)} distinct example entry tables read from the runtime",
        )
    else:
        report.fail(
            "content.exampleEntryTablesStated",
            f"entry tables {entry_tables} are not distinct, or are not printed in the guide",
        )
    top_n = re.findall(r"上位\s*[0-9０-９]+\s*件の例", text)
    if top_n:
        report.fail("content.noRetrievalCount", f"the guide prints a top-N retrieval count: {top_n[:3]}")
    else:
        report.ok(
            "content.noRetrievalCount",
            "no top-N example retrieval count is printed; the published pages disagree on it",
        )

    # 4 - instructions are not access control, and latency is directional only.
    _require(
        text,
        report,
        "content.instructionBoundary",
        [
            ("heading", "16.8 指示で守る境界と、応答時間の変数"),
            ("not access control", "指示はアクセス制御ではありません"),
            ("identity and source permissions", "サインインした ID、参照元ソースの読み取り権限"),
            ("source side controls", "各アイテム種別がソース側で提供する制御によって決まります"),
            ("no uniform rls claim", "行単位・列単位の制御がどのソースでも同じように使えると仮定しないでください"),
            ("onelake security reason", "Ontology の静的バインディングが managed Delta テーブルを前提とするためです"),
            ("not because unnecessary", "本番でアクセス制御が不要だという意味ではありません"),
            ("no timings", "ここでは秒数や倍率は示しません"),
            ("scope factor", "選択したテーブル（とその全列）とエンティティが多いほど"),
            ("instruction size factor", "指示が長いほど、また矛盾する指示や例が混ざるほど"),
            ("question context factor", "質問が曖昧なほど、また会話が長いほど"),
            ("engine factor", "生成されたクエリが重いほど、またデータモデルが複雑なほど"),
            ("capacity factor", "容量が混雑しているほど、また 1 問で複数ソースを使うほど"),
            ("consumption cross reference", "消費の考え方は付録 C.6 にまとめてあります。ここでは繰り返しません"),
        ],
    )

    # 5 - the evidence ladder and the re-run triggers.
    _require(
        text,
        report,
        "content.evidenceAndRerun",
        [
            ("heading", "17.12 実行証跡と、やり直す条件"),
            ("level 1", "1. 回答本文"),
            ("level 2", "2.［実行詳細］"),
            ("level 3", "3. エンジン側の実行履歴"),
            ("engine history optional", "見られないソースがあることを理由に不合格にはしません"),
            ("no query text in the record", "記録票の回答欄にクエリ本文を書き写さないでください"),
            ("wrong route", "ルートが違う（別のソースが使われた）"),
            ("wrong query", "ソースは正しいがクエリが違う"),
            ("engine failure", "EXECUTION_ERROR として扱い"),
            ("incomplete answer", "クエリは正しいが回答が不足している"),
            ("trigger heading", "17.12.1 再評価の引き金"),
            ("does not weaken", "この節はそれを弱めません"),
            ("config change", "3 層の設定または例クエリの変更"),
            ("schema change", "選択したスキーマまたはソース構成の変更"),
            ("runtime change", "Preview runtime の更新、または runtime の切り替え"),
            ("data refresh", "参照元データの更新・再作成"),
            ("promotion", "別ワークスペースへの移送、または参照先の張り替え"),
            ("periodic smoke", "変更なしの定期確認"),
            ("full rerun", "落ちた問いだけを直して再実行する運用は認めません"),
            ("manual verdict", "採点は人が行います。UNCLEAR は FAIL に数えます"),
            # Chapter 19 has to route a failure through both non-chapter-order
            # sections, in the order they are meant to be used.
            ("ch19 names both orders", "章順で並んでいないのは第 17.11 節と第 17.12 節の 2 つです"),
            ("ch19 layer order", "という設定層の順に並べ、第 17.12 節は"),
            ("ch19 evidence order", "「回答本文 → ［実行詳細］ → エンジン側の実行履歴」"),
            ("ch19 route starts at evidence", "まず第 17.12 節で証跡を確認し"),
            ("ch19 route then layers", "次に第 17.11 節の設定層の順で原因を切り分け"),
            ("ch19 route ends at rerun scope", "最後に第 17.12.1 節でやり直す範囲を決めます"),
            ("unclear row points at the evidence", "第 17.12 節の証跡でどこが期待と違うかを見てから"),
        ],
    )
    retired_ch19 = [
        phrase
        for phrase in ("第 17.11 節だけは順序が異なり", "10 問のどれかが落ちたときは第 17.11 節を使ってください")
        if _plain(phrase) in text
    ]
    if retired_ch19:
        report.fail(
            "content.chapter19DualOrder",
            f"chapter 19 still describes a single non-chapter-order section: {retired_ch19}",
        )
    else:
        report.ok(
            "content.chapter19DualOrder",
            "chapter 19 names both non-chapter-order sections and routes a failure through them in order",
        )

    # 6 - the publish description is a contract and a routing signal.
    _require(
        text,
        report,
        "content.publishDescription",
        [
            ("heading", "18.2 公開説明に書く 5 項目"),
            ("human contract", "公開説明は利用者に対する約束であり"),
            ("routing signal", "この Data Agent に回すかどうかの判断材料にもなります"),
            ("domain row", "対象ドメイン"),
            ("supported questions row", "答えられる問い"),
            ("sources row", "参照するソースと権威"),
            ("exclusions row", "答えない範囲"),
            ("synthetic row", "学習用の合成データ。実在の個人・事業者・寄付実績は含まない"),
            ("refusal is by design", "拒否は仕様であり、その仕様を先に伝えるのが公開説明の役割です"),
            ("agent store stays off", "Agent Store は Off"),
        ],
    )

    # 7 - appendix C.7 adds a loop, not a gate.
    _require(
        text,
        report,
        "content.appendixC7Coverage",
        [
            ("heading", "C.7 継続評価と ALM"),
            ("no new gate", "C.7 はゲートを増やしません"),
            ("bridges C.2 and C.5", "C.2 のゲート 3 と 4 は、公開までの 1 回の通過を決めます"),
            ("step 1 freeze", "設定・ソース選択・ランタイム・評価データセットを固定し、版を付ける"),
            ("step 2 fixed ground truth", "固定した held-out の正解セットを実行する"),
            ("step 3 inspect", "回答本文と実行詳細を見る"),
            ("step 4 human review", "人が確認する"),
            ("step 5 publish after pass", "合格したときにだけ公開・昇格する"),
            ("step 6 monitor", "公開後も監視し、引き金が起きたら固定した版から輪に戻る"),
            ("manual is canonical", "正本は人の採点"),
            ("programmatic is optional", "補助的な証拠として任意。実施しなくても Core は成立する"),
            ("no package names", "本書ではパッケージ名・クラス名・メソッド名・コード例を書きません"),
            ("true false unclear", "真・偽・判定不能の記録と、その集計"),
            ("does not replace", "critic の基準がルートと境界を明示的に含まない限り、人の確認を置き換えない"),
            ("calibrate separately", "第 17 章とは別に人が採点した集合で較正し"),
            ("three kinds", "良い回答・悪い回答・正しく拒否した回答の 3 種類を含めます"),
            ("repeat for variance", "同じ集合を複数回実行して、判定のばらつきを表に出します"),
            ("inspect disagreements", "人の判定と食い違った事例は、必ず中身を読みます"),
            ("version the critic", "critic のプロンプトと採点基準には版を付けます"),
            ("no thresholds", "合格とみなす水準は案件ごとに決めるものであり、本書では数値を示しません"),
            ("alm heading", "C.7.3 ALM：どこで直し、どこへ運ぶか"),
            ("draft not published", "公開済みフォルダーを直接編集しない"),
            ("branch review", "作業用のブランチで変更し、レビューを経て統合する"),
            ("test workspace", "テスト用のワークスペースへ運び、そこで確認する"),
            ("target data", "運んだ先のデータに対して評価する"),
            ("production access", "利用者は本番ワークスペースの公開版だけを使う"),
            ("current best practice", "現時点で文書化されている推奨です"),
            ("rebinding triggers rerun", "移送は評価をやり直す引き金です"),
        ],
    )

    # 8 - appendix D.7 is a reference, not a fifth exercise.
    _require(
        text,
        report,
        "content.appendixD7Coverage",
        [
            ("heading", "D.7 Semantic Model を Data Agent ソースとして追加する場合（Optional）"),
            ("appendix D intro", "D.7 も実習ではなく、ソースを増やす場合に読む参考情報です"),
            ("no operation unless extended", "参加者が自分の判断でソース構成を広げないかぎり、実施する操作はありません"),
            ("d3 notebook creates tables", "D.3 の Notebook 05 は分析用のテーブルを作成します"),
            ("d3 separate model deployment", "セマンティックモデルとレポートは、別工程の Deploy-FurusatoPowerBI.ps1 でデプロイします"),
            ("d7 is a source", "Data Agent の 4 つ目のソースとして登録し"),
            ("single authority", "静的な指標の権威を Lakehouse 1 つに固定しています"),
            ("second owner cost", "ルーティングの規則と権威の宣言を設計し直す必要が出ます"),
            ("full re-evaluation", "設計を変えれば、第 17 章の 10 問は全部やり直しです"),
            ("workshop decision", "これは製品上の制約ではなく、本ワークショップの設計上の判断です"),
            ("optimize the model", "モデル自体を整理して最適化する"),
            ("ai data schema", "AI 向けのデータスキーマを、関係する要素とその依存先だけに絞る"),
            ("verified answers", "よく聞かれる問いと、間違えやすい複雑な問いに検証済みの回答を用意する"),
            ("test before instructions", "Data Agent にモデルを追加し、まず素の状態で試す"),
            ("model instructions belong to prep", "モデル固有の指示は AI 向けの準備設定側に書く"),
            ("agent instructions stay cross source", "エージェント側の指示は、ソースをまたいで成立する規則"),
            ("inspect dax", "生成された DAX と実行詳細を読む"),
            ("validate with users", "利用者を巻き込んで検証する。プログラムによる評価は任意で足す"),
            ("no capability matrix", "本書では対応表を固定しません"),
            ("defer to appendix E", "Semantic model best practices for Data Agent"),
        ],
    )

    # 9 - the new blocks stay inside their remit and print nothing volatile.
    isolation: list[str] = []
    forbidden: list[str] = []
    scanned: list[str] = []
    for label, start, end in PRACTICE_SECTIONS:
        if label == "16.8" and getattr(context, "is_unified_guide", False):
            from .guide_unified import MIGRATION_HEADING
            end = MIGRATION_HEADING
        block = _section(text, start, end)
        if not block:
            isolation.append(f"{label}: section not found")
            continue
        scanned.append(f"{label} ({len(block)} chars)")
        for pattern, why in PRACTICE_FORBIDDEN:
            match = pattern.search(block)
            if match:
                forbidden.append(f"{label}: {match.group(0)!r} ({why})")
        if label not in PRACTICE_ISOLATED:
            continue
        leaks = sorted(set(PRACTICE_TEST_ID.findall(block)))
        verdicts = [word for word in ("PASS", "FAIL", "UNCLEAR", "EXECUTION_ERROR") if word in block]
        runtime = [
            name
            for name in ("DRY_RUN_COMPLETE", "APPLY_CHANGES", "PARTICIPANT_ID")
            if name in block
        ]
        if leaks or verdicts or runtime:
            isolation.append(f"{label}: tests={leaks} verdicts={verdicts} runtime={runtime}")
    if isolation:
        report.fail("content.practiceSectionIsolation", "; ".join(isolation))
    else:
        report.ok(
            "content.practiceSectionIsolation",
            f"the {len(PRACTICE_ISOLATED)} configuration sections name no held-out test, verdict "
            f"or runtime parameter ({', '.join(scanned)})",
        )
    if forbidden:
        report.fail("content.practiceSectionClaims", "; ".join(forbidden[:5]))
    else:
        report.ok(
            "content.practiceSectionClaims",
            f"none of the {len(PRACTICE_FORBIDDEN)} volatile or forward-looking patterns appears in "
            f"the {len(PRACTICE_SECTIONS)} new sections",
        )


def check_unified_guide(context, text: str, report: Report) -> None:
    """Additional one-Agent gates; the legacy profile and its gates are unchanged."""
    from .guide_unified import CI_HEADING, MIGRATION_HEADING

    _require(
        text, report, "content.unifiedProfile",
        [
            ("edition", "unified-20260923"),
            ("primary agent", context.names["dataAgent"]),
            ("full ontology", context.names["ontology"]),
            ("full structure", "10 Entity / 72 static Property / 1 time-series Property / 15 Relationship"),
            ("supported Ontology instruction policy", "Ontology ソース指示は null のまま保持"),
            ("one connection", "唯一の connectedOntology"),
            ("global path", context.guide_instruction_relative_path),
            ("CI enabled", "codeInterpreterEnabled = true"),
            ("Preview evaluation", "Core 記録は Preview runtime で実施しなければなりません"),
            ("selection units", "14（11 テーブル + 1 view + 2 関数）"),
            ("KQL functions", "4（1 MV + 3 関数）"),
            ("shared helper ordering", "ヘルパー作成 → native schema 確認 → Agent の discovery"),
            ("raw stays hidden", "raw DonationEvents と EventID は非選択"),
        ],
    )
    _require(
        text, report, "content.unifiedMigration",
        [
            ("migration section", MIGRATION_HEADING),
            ("opt in", "ENABLE_UNIFIED_DATA_AGENT=True"),
            ("legacy off", "ENABLE_AI_REFERENCE_ARCHITECTURE=False"),
            ("exclusive flags", "両方 True は禁止"),
            ("preview first", "CONFIRMED_PLAN_SHA256"),
            ("exclusive create", "EXCLUSIVE_CREATE_WINDOW_CONFIRMED"),
            ("no resume", "no-auto-resume"),
            ("publish preservation", "Published は検証が完了するまで旧版を保持"),
            ("narrow deletion", "旧 Agent 2 件だけを実 ID で照合"),
            ("shared retention", "過去に保持した Eventhouse"),
        ],
    )
    _require(
        text, report, "content.unifiedNativeEvidence",
        [
            ("original rubric", "元の 10 問／84 要件は変更せず"),
            ("same run", "実際の同一 run"),
            ("UI export", "UI Export"),
            ("identity", "conversation ID"),
            ("native ownership", "根拠 3 種と CI の追加成果物"),
            ("GQL not Python", "Graph の件数・path・identity を Python で作りません"),
            ("CI section", CI_HEADING),
            ("actual execution", "実行した Python と実際の入力"),
            ("actual output", "stdout / stderr"),
            ("bounded input", "bounded な結果はその範囲の分析にしか使いません"),
            ("no chart-spec proxy", "report_specs"),
            ("no imputation", "失敗・欠落を 0 として埋めません"),
            ("possible platform block", "T10 ではプラットフォームのブロックが残る可能性"),
        ],
    )
    _require(
        text, report, "content.unifiedKqlExamples",
        [
            ("profile count", f"{len(context.guide_kql_fewshots)} 件（KQL、固定済み JSON）"),
            ("pinned examples", "unified-agent/inputs/kusto-fewshots.json"),
            ("original question text", "以下は配布物の英語原文です"),
            ("SQL gate scope", "以下の入口テーブルの検査は SQL の例を対象にします"),
            *[(f"KQL example {index}", shot["question"]) for index, shot in enumerate(context.guide_kql_fewshots, 1)],
        ],
    )
    retired = [
        phrase for phrase in (
            "Core は Code Interpreter を使わない",
            "AI 参照構成を選ぶ場合は、第 16.9 節の別 Agent",
            "AIPath と Data Agent を構築します",
            "検証用と分かる名前の別 Agent を作る",
            "Data Agent が参照するのはこのビューだけです",
        )
        if phrase in text
    ]
    if retired:
        report.fail("content.unifiedNoLegacyRouting", f"Legacy-only main-path instructions: {retired}")
    else:
        report.ok("content.unifiedNoLegacyRouting", "No three-Agent setup, AIPath route or CI-off main path.")


#: The first table an example query reads. Mirrors the builder so the gate and
#: the printed table cannot disagree about what "entry table" means.
_FIRST_FROM_TABLE = re.compile(r"\bFROM\s+(dbo\.[A-Za-z0-9_]+)", re.IGNORECASE)


def _first_from(query: str) -> str:
    match = _FIRST_FROM_TABLE.search(query or "")
    return match.group(1) if match else ""


def check_workbook_v3(path: Path, context, report: Report) -> None:
    """Workbook-side corrections: the four Core rows and the new contract gates."""
    from openpyxl import load_workbook

    workbook = load_workbook(path)
    core = workbook["Parameters_Core"]
    names = {
        core.cell(row=row, column=2).value
        for row in range(5, core.max_row + 1)
        if core.cell(row=row, column=2).value
    }
    required = {"PARTICIPANT_ID", *STALE_LEASE_GROUP}
    missing = sorted(required - names)
    if missing:
        report.fail("workbook.coreRows", f"Parameters_Core is missing: {missing}")
    else:
        report.ok(
            "workbook.coreRows",
            f"Parameters_Core lists all {len(required)} settable parameters including the stale-lease trio",
        )
    sections = {
        core.cell(row=row, column=7).value
        for row in range(5, core.max_row + 1)
        if core.cell(row=row, column=7).value
    }
    expected_sections = {PARAMETER_SECTION["Notebook_01"], PARAMETER_SECTION["Notebook_02"]}
    if sections != expected_sections:
        report.fail("workbook.coreSections", f"unexpected 実施節 values: {sorted(sections)}")
    else:
        report.ok("workbook.coreSections", f"Parameters_Core points at {sorted(sections)}")

    contracts = workbook["Contracts"]
    if (contracts.column_dimensions["D"].width or 0) < 34:
        report.fail(
            "workbook.contractRuleColumn",
            f"the Rule column is only {contracts.column_dimensions['D'].width} wide; long identifiers wrap badly",
        )
    else:
        report.ok(
            "workbook.contractRuleColumn",
            f"the Rule column is {contracts.column_dimensions['D'].width:.0f} wide",
        )
    unformatted = [
        contracts.cell(row=row, column=1).value
        for row in range(5, contracts.max_row + 1)
        if isinstance(contracts.cell(row=row, column=2).value, int)
        and not isinstance(contracts.cell(row=row, column=2).value, bool)
        and contracts.cell(row=row, column=2).number_format != "#,##0"
    ]
    if unformatted:
        report.fail("workbook.contractNumberFormat", f"numeric gates without #,##0: {unformatted[:4]}")
    else:
        report.ok("workbook.contractNumberFormat", "every numeric contract value uses a thousands separator")

    labels = {
        contracts.cell(row=row, column=1).value
        for row in range(1, contracts.max_row + 1)
        if contracts.cell(row=row, column=1).value
    }
    gates = {
        "KQL 管理コマンド数",
        "Data Agent: Lakehouse で選択するテーブル数",
        "Data Agent: KQL で選択する要素数",
        "Data Agent: Ontology で選択する Entity 数",
        "many-to-one の Relationship 数",
        "452025 の 8 月観測数",
        "452025 の 8 月観測金額 (JPY)",
        "Notebook 05 gold fact 行数",
        "公開版スモークセット",
    }
    absent = sorted(gates - labels)
    if absent:
        report.fail("workbook.qualityGates", f"Contracts is missing: {absent}")
    else:
        report.ok("workbook.qualityGates", f"Contracts carries all {len(gates)} quality-pass gates")

    daily = workbook["IncrementDaily"]
    merged = {str(entry) for entry in daily.merged_cells.ranges}
    for wanted in ("A3:E3", "A4:E4"):
        if wanted not in merged:
            report.fail("workbook.dailyNotes", f"{wanted} is not merged: {sorted(merged)}")
            break
    else:
        tall = [
            index
            for index, dimension in daily.row_dimensions.items()
            if dimension.height and dimension.height > 60
        ]
        if tall:
            report.fail("workbook.dailyNotes", f"rows with a forced tall height remain: {tall}")
        else:
            report.ok("workbook.dailyNotes", "the two notes span A:E and no row is forced taller than 60 pt")


#: Punctuation and spacing mistakes that read as sloppy in Japanese body text.
#: Only prose is scanned: verbatim listings keep their own indentation and blank
#: lines, and rewriting them would break the fidelity the guide depends on.
TYPOGRAPHY_DEFECTS = (
    (re.compile(r"[ \u3000]+[。、]"), "space before a Japanese full stop or comma"),
    (re.compile(r"[。、][ \u3000]+"), "space after a Japanese full stop or comma"),
    (re.compile(r"。。|、、"), "doubled Japanese punctuation"),
    (re.compile(r"（[ \u3000]|[ \u3000]）"), "space inside Japanese parentheses"),
    (
        re.compile(r"[\u3040-\u30ff\u4e00-\u9fff][ \u3000][\u3040-\u30ff\u4e00-\u9fff]"),
        "space between two Japanese characters",
    ),
)


def prose_paragraphs(path: Path) -> list[str]:
    """Return the document's prose, with verbatim listings removed.

    Code blocks and the quoted agent instructions are reproduced byte for byte, so
    their indentation and blank lines must not be judged as Japanese typography.
    Every run rendered in the monospace face is dropped, which removes listings and
    inline code without needing to model the table structure.
    """
    tree = ElementTree.fromstring(_parts(path)["word/document.xml"])
    body = tree.find(f"{W}body")
    paragraphs: list[str] = []
    for paragraph in body.iter(f"{W}p"):
        pieces: list[str] = []
        for run in paragraph.findall(f"{W}r"):
            run_pr = run.find(f"{W}rPr")
            fonts = run_pr.find(f"{W}rFonts") if run_pr is not None else None
            if fonts is not None and fonts.get(f"{W}ascii") == "Consolas":
                # Substitute a Latin placeholder rather than dropping the run, so
                # the characters either side keep their real adjacency.
                pieces.append("code")
                continue
            pieces.extend(node.text or "" for node in run.iter(f"{W}t"))
        line = "".join(pieces).strip()
        if line and line != "code":
            paragraphs.append(line.replace("\u2060", ""))
    return paragraphs


def canvas_phrases(context) -> tuple[str, ...]:
    """Labels printed on a diagram canvas that the prose is allowed to quote verbatim.

    A compound such as ``メトリック / フロー エンティティ`` carries spaces because the
    canvas does; reproducing it exactly is what lets a reader match caption to
    picture, so it must not be judged as a Japanese spacing defect.
    """
    label = re.compile(r">([^<>]{2,60})<")
    spaced = re.compile(r"[\u3040-\u30ff\u4e00-\u9fff][ \u3000][\u3040-\u30ff\u4e00-\u9fff]")
    phrases: set[str] = set()
    for _, variants in sorted(context.diagrams.items()):
        svg = variants.get("svg")
        if svg is None:
            continue
        for value in label.findall(svg.read_text(encoding="utf-8")):
            value = value.strip()
            if 2 <= len(value) <= 60 and spaced.search(value):
                phrases.add(value)
    return tuple(sorted(phrases, key=len, reverse=True))


def check_typography(paragraphs: list[str], report: Report, allowed: tuple[str, ...] = ()) -> None:
    """Reject the spacing and punctuation slips a Japanese reader notices first.

    Text inside Japanese quotation marks is skipped: those spans quote runtime
    values such as a gift name, and their spacing belongs to the data, not to the
    prose this pass owns. ``allowed`` phrases - diagram canvas labels the prose
    quotes verbatim - are skipped for the same reason.
    """
    quoted = re.compile(r"[「『][^」』]*[」』]")
    cleaned: list[str] = []
    for line in paragraphs:
        line = quoted.sub("「」", line)
        for phrase in allowed:
            # Substitute rather than delete, or removing a phrase would push the
            # punctuation on either side together and look like a doubled mark.
            line = line.replace(phrase, "X")
        cleaned.append(line)
    findings: list[str] = []
    for pattern, description in TYPOGRAPHY_DEFECTS:
        hits = [line for line in cleaned if pattern.search(line)]
        if hits:
            match = pattern.search(hits[0])
            excerpt = hits[0][max(0, match.start() - 18) : match.end() + 18]
            findings.append(f"{description} ({len(hits)}x, e.g. …{excerpt}…)")
    if findings:
        report.fail("content.typography", "; ".join(findings))
    else:
        report.ok(
            "content.typography",
            f"none of the {len(TYPOGRAPHY_DEFECTS)} spacing defects appear in {len(paragraphs)} prose paragraphs",
        )


def check_validation_doc_content(text: str, tests, report: Report, path: Path | None = None) -> None:
    """The Test 10 record must state what is held out and how it is scored."""
    total = len(tests)
    # The record sheet and the guide must name the route field identically, or a
    # grader transcribing from one into the other has to guess they are the same.
    if "期待するソースルート" in text:
        report.fail("content.recordRouteLabel", "the record sheet still uses the old 期待するソースルート label")
    else:
        report.ok("content.recordRouteLabel", "the record sheet labels the route field 期待するルート, matching the guide")
    _require(
        text,
        report,
        "content.heldOutSemantics",
        [
            ("held out from the agent", "Data Agent に与えない"),
            ("grader copy", "採点する人には期待値が必要"),
            ("query text withheld", "実行可能なクエリ文"),
            ("do not copy into config", "設定（グローバル指示"),
        ],
    )
    _require(
        text,
        report,
        "content.scoring",
        [
            ("pass threshold", f"{total} 問中 {total} 問が PASS"),
            ("unclear is fail", "FAIL と同じ"),
            ("retry budget", "最大 2 回まで再実行"),
            ("escalation", "エスカレーション"),
            ("no config change", "設定・ソース選択・指示を変更しない"),
        ],
    )
    for value in ("PASS", "FAIL", "UNCLEAR", "EXECUTION_ERROR"):
        if value not in text:
            report.fail("content.resultValues", f"{value} missing from the record")
            break
    else:        report.ok("content.resultValues", "all four result values are preserved")

    if path is not None:
        check_typography(prose_paragraphs(path), report)


#: Terms a reviewer flagged as unpleasant when broken across a line. Japanese
#: allows a break at almost any character, so this is reported rather than
#: enforced; it is here so a regression is visible.
KEEP_TOGETHER_TERMS = ("メタデータ", "持って", "バインディング", "カーディナリティ")

#: Vocabulary the diagrams and the prose must agree on. Each term is required in
#: the guide when a diagram uses it, and rejected when no diagram does - so a
#: rename on the canvas surfaces as a documentation failure in both directions.
DIAGRAM_VOCABULARY = (
    "基幹エンティティ",
    "集計層",
    "Core entities",
    "Metric / Flow",
    "マスタ",
    "トランザクション",
)


def check_diagram_vocabulary(context, text: str, report: Report) -> None:
    """Captions and prose must use the wording that is on the diagram canvas."""
    canvas = "\n".join(
        variants["svg"].read_text(encoding="utf-8")
        for _, variants in sorted(context.diagrams.items())
        if "svg" in variants
    )
    if not canvas:
        report.warn("content.diagramVocabulary", "no SVG source available to compare wording against")
        return
    flat = re.sub(r"\s+", " ", text)
    missing = [term for term in DIAGRAM_VOCABULARY if term in canvas and term not in flat]
    stale = [term for term in DIAGRAM_VOCABULARY if term not in canvas and term in flat]
    if missing or stale:
        report.fail(
            "content.diagramVocabulary",
            f"missing from the guide: {missing}; no longer on any canvas: {stale}",
        )
    else:
        used = [term for term in DIAGRAM_VOCABULARY if term in canvas]
        report.ok(
            "content.diagramVocabulary",
            f"the guide uses the same {len(used)} structural terms as the diagrams",
        )


# ---------------------------------------------------------------------- layout
def _parts(path: Path) -> dict[str, bytes]:
    with zipfile.ZipFile(path) as archive:
        return {name: archive.read(name) for name in archive.namelist()}


def check_layout(path: Path, report: Report, *, expect_toc: bool = True) -> dict[str, object]:
    """A4 page setup, Japanese typography, a real TOC field and page-break safety."""
    parts = _parts(path)
    document = parts["word/document.xml"].decode("utf-8")
    styles = parts["word/styles.xml"].decode("utf-8")
    settings = parts["word/settings.xml"].decode("utf-8")

    sizes = re.findall(r'<w:pgSz w:w="([0-9]+)" w:h="([0-9]+)"', document)
    wrong = [pair for pair in sizes if pair != (str(A4_WIDTH_TWIPS), str(A4_HEIGHT_TWIPS))]
    if not sizes:
        report.fail("layout.pageSize", "no page size found")
    elif wrong:
        report.fail("layout.pageSize", f"sections that are not A4: {wrong}")
    else:
        report.ok("layout.pageSize", f"all {len(sizes)} sections are A4 ({A4_WIDTH_TWIPS}x{A4_HEIGHT_TWIPS} twips)")

    missing_typography = [
        name
        for name, value in JAPANESE_PARAGRAPH_DEFAULTS
        if f'<{name} w:val="{value}"/>' not in styles
    ]
    kinsoku_lists: list[str] = []
    if "<w:strictFirstAndLastChars" not in settings:
        kinsoku_lists.append("w:strictFirstAndLastChars")
    if missing_typography:
        report.fail("layout.kinsoku", f"paragraph defaults missing from raw XML: {missing_typography}")
    elif f'w:val="{CHARACTER_SPACING_CONTROL}"' not in settings:
        report.fail("layout.kinsoku", f"characterSpacingControl is not {CHARACTER_SPACING_CONTROL}")
    elif kinsoku_lists:
        report.fail("layout.kinsoku", f"missing from settings.xml: {kinsoku_lists}")
    elif f'w:eastAsia="{EAST_ASIAN_LANGUAGE}"' not in styles:
        report.fail("layout.kinsoku", f"the East Asian language is not {EAST_ASIAN_LANGUAGE}")
    else:
        report.ok(
            "layout.kinsoku",
            f"raw XML declares {len(JAPANESE_PARAGRAPH_DEFAULTS)} paragraph defaults, "
            f"strictFirstAndLastChars, {CHARACTER_SPACING_CONTROL} and eastAsia={EAST_ASIAN_LANGUAGE}",
        )

    tree = ElementTree.fromstring(parts["word/document.xml"])
    toc_instructions = [
        (node.text or "").strip()
        for node in tree.iter(f"{W}instrText")
        if "TOC" in (node.text or "")
    ]
    if expect_toc:
        if not toc_instructions:
            report.fail("layout.tocField", "no TOC field instruction found")
        elif any("TOC" in (node.text or "") for node in tree.iter(f"{W}t")):
            report.fail("layout.tocField", "the TOC field instruction is printed as literal body text")
        else:
            report.ok("layout.tocField", f"a real TOC field is present: {toc_instructions[0]!r}")
        _check_field_runs(tree, report)

    if "<w:titlePg/>" in document:
        report.ok("layout.coverPage", "the cover uses a blank first-page header and footer")
    else:
        report.fail("layout.coverPage", "the cover still prints the running header and page number")
    first_refs = re.findall(r'<w:(?:header|footer)Reference w:type="first"', document)
    if len(first_refs) != 2:
        report.fail("layout.coverReferences", f"expected 2 first-page references, found {len(first_refs)}")
    else:
        report.ok("layout.coverReferences", "the cover section references a blank header and footer")

    return _check_page_break_safety(tree, report)


def _check_field_runs(tree, report: Report) -> None:
    """Each fldChar and instrText must sit in its own run, or Word unlinks the field."""
    offenders = 0
    for run in tree.iter(f"{W}r"):
        markers = len(run.findall(f"{W}fldChar")) + len(run.findall(f"{W}instrText"))
        if markers and len(list(run)) - len(run.findall(f"{W}rPr")) > markers:
            offenders += 1
        if len(run.findall(f"{W}fldChar")) and len(run.findall(f"{W}instrText")):
            offenders += 1
    if offenders:
        report.fail("layout.fieldRuns", f"{offenders} runs mix field markers with other content")
    else:
        report.ok("layout.fieldRuns", "every field marker sits in its own run")


def _code_chars_per_row(body) -> int:
    """Monospace characters that fit on one line inside a full-width code cell."""
    section = body.find(f"{W}sectPr")
    page = section.find(f"{W}pgSz") if section is not None else None
    margins = section.find(f"{W}pgMar") if section is not None else None
    if page is None or margins is None:
        return 100
    usable_pt = (
        int(page.get(f"{W}w"))
        - int(margins.get(f"{W}left"))
        - int(margins.get(f"{W}right"))
    ) / 20
    text_pt = max(usable_pt - 2 * CELL_PADDING_PT, 1.0)
    return max(int(text_pt / (8.5 * MONO_ADVANCE_RATIO)), 1)


def _rendered_row_count(row, chars_per_row: int) -> int:
    """Lines the cell occupies once its paragraphs wrap.

    Counting ``w:p`` elements counts logical lines. A source-instruction listing
    carries a few lines several hundred characters long, so the logical count
    understates the height by an order of magnitude and would demand ``cantSplit``
    on a listing that cannot fit a page at all.
    """
    total = 0
    for paragraph in row.iter(f"{W}p"):
        text = "".join(node.text or "" for node in paragraph.iter(f"{W}t"))
        total += max(1, math.ceil(len(text) / chars_per_row))
    return total


def _check_page_break_safety(tree, report: Report) -> dict[str, object]:
    """Callouts and short listings must not split; captions must bind to their object."""
    body = tree.find(f"{W}body")
    chars_per_row = _code_chars_per_row(body)
    single_row_tables = 0
    unsplittable = 0
    splittable_long_code = 0
    for table in body.iter(f"{W}tbl"):
        rows = table.findall(f"{W}tr")
        if len(rows) != 1:
            continue
        single_row_tables += 1
        lines = _rendered_row_count(rows[0], chars_per_row)
        has_cant_split = rows[0].find(f"{W}trPr/{W}cantSplit") is not None
        if has_cant_split:
            unsplittable += 1
        elif lines <= CODE_BLOCK_UNBREAKABLE_LINES:
            splittable_long_code += 1
    if splittable_long_code:
        report.fail(
            "layout.cantSplit",
            f"{splittable_long_code} short callouts or listings may be split across a page break",
        )
    else:
        report.ok(
            "layout.cantSplit",
            f"{unsplittable} of {single_row_tables} single-row containers are marked cantSplit",
        )

    children = list(body)
    stranded: list[str] = []
    for index, element in enumerate(children):
        if element.tag != f"{W}p":
            continue
        style = element.find(f"{W}pPr/{W}pStyle")
        if style is None or style.get(f"{W}val") != "Caption":
            continue
        previous = children[index - 1] if index else None
        if previous is None:
            continue
        if previous.tag == f"{W}tbl":
            continue
        if previous.tag == f"{W}p":
            keep = previous.find(f"{W}pPr/{W}keepNext")
            if keep is not None and keep.get(f"{W}val") not in ("0", "false"):
                continue
            text = "".join(node.text or "" for node in previous.iter(f"{W}t"))
            stranded.append(text[:30] or "(empty)")
    if stranded:
        report.fail("layout.captionBinding", f"{len(stranded)} captions are not bound to their object: {stranded[:3]}")
    else:
        report.ok("layout.captionBinding", "every caption is bound to the object above it")

    small_code = 0
    joiner_in_code = 0
    for run in body.iter(f"{W}r"):
        run_pr = run.find(f"{W}rPr")
        if run_pr is None:
            continue
        fonts = run_pr.find(f"{W}rFonts")
        if fonts is None or fonts.get(f"{W}ascii") != "Consolas":
            continue
        if any("\u2060" in (node.text or "") for node in run.iter(f"{W}t")):
            joiner_in_code += 1
        size = run_pr.find(f"{W}sz")
        if size is not None and int(size.get(f"{W}val")) < int(MIN_CODE_PT * 2):
            small_code += 1
    if small_code:
        report.fail("layout.codeSize", f"{small_code} inline-code runs are smaller than {MIN_CODE_PT} pt")
    else:
        report.ok("layout.codeSize", f"every inline-code run is at least {MIN_CODE_PT} pt")
    if joiner_in_code:
        report.fail(
            "layout.copyableCode",
            f"{joiner_in_code} monospace runs contain a zero-width word joiner and would paste badly",
        )
    else:
        report.ok("layout.copyableCode", "no monospace run contains a zero-width joiner")

    return {"singleRowTables": single_row_tables, "unsplittable": unsplittable}


def chapter_titles(path: Path) -> list[str]:
    """Every level-1 heading in the document, in order."""
    tree = ElementTree.fromstring(_parts(path)["word/document.xml"])
    titles: list[str] = []
    for paragraph in tree.iter(f"{W}p"):
        style = paragraph.find(f"{W}pPr/{W}pStyle")
        if style is None or style.get(f"{W}val") != "Heading1":
            continue
        text = "".join(node.text or "" for node in paragraph.iter(f"{W}t")).strip()
        if text:
            titles.append(text)
    return titles


def table_headers(path: Path) -> list[str]:
    """The first cell of every data-table header row, used to spot continuations."""
    tree = ElementTree.fromstring(_parts(path)["word/document.xml"])
    headers: list[str] = []
    for table in tree.iter(f"{W}tbl"):
        rows = table.findall(f"{W}tr")
        if not rows or rows[0].find(f"{W}trPr/{W}tblHeader") is None:
            continue
        cells = rows[0].findall(f"{W}tc")
        if not cells:
            continue
        text = "".join(node.text or "" for node in cells[0].iter(f"{W}t")).strip()
        if text:
            headers.append(text)
    return headers


def check_render(path: Path, scratch: Path, report: Report, *, first_body_page: int = 1) -> dict[str, object]:
    """Render every page and reject blank, caption-only or stranded-note pages."""
    from .render_audit import audit

    result = audit(path, scratch)
    if not result.ok:
        report.warn("render.audit", f"page render skipped: {result.detail}")
        return {"rendered": False, "detail": result.detail}
    if result.blank_pages:
        report.fail("render.blankPages", f"blank pages: {result.blank_pages}")
    else:
        report.ok("render.blankPages", f"none of the {len(result.pages)} pages are blank")
    if result.caption_only_pages:
        report.fail("render.captionOnlyPages", f"caption-only pages: {result.caption_only_pages}")
    else:
        report.ok("render.captionOnlyPages", "no page holds nothing but a caption")
    violations = result.kinsoku_violations
    if violations:
        report.fail(
            "render.kinsoku",
            f"{len(violations)} lines start with a forbidden character, e.g. {violations[:3]}",
        )
    else:
        report.ok("render.kinsoku", "no rendered line starts with a forbidden Japanese character")
    kana = result.kana_line_starts
    if kana:
        report.fail(
            "render.kinsokuKana",
            f"{len(kana)} lines start with a small kana or long-vowel mark: {kana[:3]}",
        )
    else:
        report.ok("render.kinsokuKana", "no rendered line starts with a small kana or long-vowel mark")
    orphans = result.orphaned_code_captions()
    if orphans:
        report.fail(
            "render.codeBlocks",
            f"{len(orphans)} listing captions open a page, so the listing was split: {orphans[:3]}",
        )
    else:
        report.ok("render.codeBlocks", "no listing is split from its caption across a page break")
    sparse = result.sparse_pages(skip_before=first_body_page)
    if sparse:
        report.fail(
            "render.sparsePages",
            f"{len(sparse)} body pages carry only a stranded note: {sparse[:3]}",
        )
    else:
        report.ok("render.sparsePages", "no body page carries only a stranded callout")
    orphan_headings = result.orphan_headings(chapter_titles(path))
    if orphan_headings:
        report.fail(
            "render.orphanHeadings",
            f"{len(orphan_headings)} chapter headings end a page with no text under them: {orphan_headings[:3]}",
        )
    else:
        report.ok("render.orphanHeadings", "no chapter heading is stranded at the foot of a page")
    thin = result.thin_table_continuations(table_headers(path))
    if thin:
        report.fail(
            "render.tableContinuations",
            f"{len(thin)} pages continue a table with a single row: {thin[:3]}",
        )
    else:
        report.ok("render.tableContinuations", "no table continues onto a page holding a single row")
    broken = result.split_terms(KEEP_TOGETHER_TERMS)
    # Word offers no supported way to hold a Japanese term together across a line:
    # a run-level word joiner, an en-US East Asian language and wordWrap were all
    # measured and none of them changed the break. It is reported, not enforced.
    report.ok(
        "render.termSplits",
        f"{len(broken)} of the {len(KEEP_TOGETHER_TERMS)} watched terms break across a line"
        + (f" ({sorted(set(broken))[:4]}) - not preventable in Word" if broken else ""),
    )
    return {"rendered": True, "pages": len(result.pages), "result": result}


def check_test_record_pages(result, tests, report: Report) -> None:
    """Every held-out test must own a page whose record form is not split.

    A grader fills the record in while reading the criteria, so the criteria
    table, the 記録欄 heading and the whole record form have to be visible on the
    same page as the test title.
    """
    problems: list[str] = []
    for test in tests:
        heading = f"{test.test_id}"
        pages = [
            page
            for page in result.pages
            if heading in page.body_text and "記録項目" in page.body_text
        ]
        if not pages:
            problems.append(f"{test.test_id}: title and record form are on different pages")
            continue
        page = pages[0]
        for needle in ("記録項目", "記入欄", "判定", "所見・再テストの要否"):
            if needle not in page.body_text:
                problems.append(f"{test.test_id}: record form row {needle!r} is not on page {page.number}")
    if problems:
        report.fail("render.testRecords", f"{problems[:3]}")
    else:
        report.ok(
            "render.testRecords",
            f"all {len(tests)} tests keep their criteria table and record form on one page",
        )


# -------------------------------------------------------------------- workbook
def check_workbook_presentation(path: Path, context, report: Report) -> None:
    """Print setup, footers, conditional formatting and the preserved label."""
    from openpyxl import load_workbook

    workbook = load_workbook(path)
    missing_titles = [
        sheet.title for sheet in workbook.worksheets if not sheet.print_title_rows
    ]
    if missing_titles:
        report.fail("workbook.printTitles", f"sheets without a repeating header row: {missing_titles}")
    else:
        report.ok("workbook.printTitles", f"all {len(workbook.worksheets)} sheets repeat their header row")

    missing_footer = [
        sheet.title
        for sheet in workbook.worksheets
        if "&P" not in (sheet.oddFooter.right.text or "")
        or f"v{context.version}" not in (sheet.oddFooter.left.text or "")
    ]
    if missing_footer:
        report.fail("workbook.footer", f"sheets without a sheet/version/page footer: {missing_footer}")
    else:
        report.ok("workbook.footer", "every sheet prints its name, the version and the page number")

    wrong_paper = [
        sheet.title
        for sheet in workbook.worksheets
        if int(sheet.page_setup.paperSize or 0) != int(sheet.PAPERSIZE_A4)
    ]
    if wrong_paper:
        report.fail("workbook.paperSize", f"sheets that are not A4: {wrong_paper}")
    else:
        report.ok("workbook.paperSize", f"all {len(workbook.worksheets)} sheets print on A4")

    contracts = workbook["Contracts"]
    rules = list(contracts.conditional_formatting)
    if not rules:
        report.fail("workbook.conditionalFormatting", "the contract checks have no pass/fail colouring")
    else:
        report.ok(
            "workbook.conditionalFormatting",
            f"{sum(len(entry.rules) for entry in rules)} conditional formats colour the contract checks",
        )

    overview = workbook["Overview"]
    merged = {str(entry) for entry in overview.merged_cells.ranges}
    if "B4:I4" not in merged:
        report.fail("workbook.overviewNote", f"the editing note is not merged full width: {sorted(merged)}")
    else:
        report.ok("workbook.overviewNote", "the editing note spans the full sheet width")

    daily = workbook["IncrementDaily"]
    labels = [
        daily.cell(row=row, column=1).value
        for row in range(1, daily.max_row + 1)
        if isinstance(daily.cell(row=row, column=1).value, str)
    ]
    if not any("dedup が除去した追加重複行数" in str(label) for label in labels):
        report.fail("workbook.dailySummary", "the daily summary labels are missing")
    else:
        merged_daily = {str(entry) for entry in daily.merged_cells.ranges}
        unmerged = [
            label
            for label in labels
            if label.startswith(("合計", "1 UTC", "対象 UTC", "dedup"))
            and not merged_daily
        ]
        if unmerged:
            report.fail("workbook.dailySummary", "the daily summary labels are not merged and will be clipped")
        else:
            report.ok(
                "workbook.dailySummary",
                f"{len(merged_daily)} merged label ranges keep the daily summary readable",
            )

    core = workbook["Parameters_Core"]
    headers = [core.cell(row=4, column=index).value for index in range(1, core.max_column + 1)]
    if "適用条件" not in headers:
        report.fail("workbook.applicationCondition", f"Parameters_Core has no application-condition column: {headers}")
    else:
        column = headers.index("適用条件") + 1
        conditions = {
            core.cell(row=row, column=column).value
            for row in range(5, core.max_row + 1)
            if core.cell(row=row, column=column).value
        }
        expected = {APPLIES_ALWAYS, APPLIES_STALE_LEASE}
        if not conditions <= expected:
            report.fail("workbook.applicationCondition", f"unexpected conditions: {conditions - expected}")
        elif APPLIES_STALE_LEASE not in conditions:
            report.fail("workbook.applicationCondition", "the stale-lease condition is never used")
        else:
            report.ok(
                "workbook.applicationCondition",
                f"Parameters_Core states when each parameter applies ({len(conditions)} distinct conditions)",
            )

    cached = load_workbook(path, data_only=True)
    total = cached["IncrementDaily"]
    values = [
        total.cell(row=row, column=3).value
        for row in range(1, total.max_row + 1)
        if isinstance(total.cell(row=row, column=1).value, str)
        and str(total.cell(row=row, column=1).value).startswith("合計")
    ]
    if any(value is None for value in values) or not values:
        report.warn(
            "workbook.cachedValues",
            "formula results are not cached; previews stay blank until Excel recalculates",
        )
    else:
        report.ok("workbook.cachedValues", f"{len(values)} summary formulas ship with cached results")
