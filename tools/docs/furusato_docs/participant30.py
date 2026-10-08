"""Participant edition of the Furusato Workshop 3.0.0 guide.

The participant edition contains only what participants need to carry out the
workshop: purpose, preparation, numbered steps, completion checks, reference
tables and official references. Prose comes from ``participant30_text``,
figure captions from ``participant30_figures``; tables are generated from the
same repository sources as the rest of the guide so values cannot drift.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from pathlib import Path

from furusato_html.model import Block, Section, Text

from . import participant30_figures as figure_source
from . import participant30_text as text_source

LEARN_BASE = "https://learn.microsoft.com/en-us/fabric/iq/ontology/"
PARTICIPANT_ASSETS = Path(__file__).resolve().parents[3] / "docs" / "assets" / "v3.0.0-participant"


def participant_figures() -> dict:
    """Participant-only images (new screenshots and diagrams), separate from the evidence projection."""
    path = PARTICIPANT_ASSETS / "manifest.json"
    if not path.is_file():
        return {}
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("schemaVersion") != "furusato-participant-figures/v1":
        raise ValueError("Unexpected participant figure manifest")
    return {entry["id"]: entry for entry in manifest["figures"]}


def figure_path(ident: str) -> Path:
    entry = participant_figures()[ident]
    path = (PARTICIPANT_ASSETS / entry["file"]).resolve()
    if not path.is_relative_to(PARTICIPANT_ASSETS.resolve()) or not path.is_file():
        raise ValueError("Participant figure path is invalid: " + ident)
    if hashlib.sha256(path.read_bytes()).hexdigest() != entry["sha256"]:
        raise ValueError("Participant figure changed after its manifest was written: " + ident)
    return path

TAGLINE = {
    "ja": "合成データを使い、Lakehouse・Eventhouse・Ontology・Data Agent を順に構築して確かめるハンズオン教材です。",
    "en": "A hands-on guide that builds and checks Lakehouse, Eventhouse, Ontology and Data Agent step by step with synthetic data.",
}

SECTION_TITLES = {
    "intro": ("この章で行うこと", "What you will do"),
    "steps": ("操作手順", "Steps"),
    "checks": ("完了の確認", "Check your work"),
    "tables": ("参照表", "Reference tables"),
    "links": ("参考資料", "References"),
}

#: Plain wording for protected evaluation text reused from the shared source.
#: Only uncommon words change; questions, values and conditions keep their meaning.
PLAIN_JA = (
    ("静的 2025 スナップショット", "2025年の静的データ"),
    ("静的2025スナップショット", "2025年の静的データ"),
    ("2025 スナップショット", "2025年の静的データ"),
    ("静的スナップショット", "静的データ"),
    ("スナップショット", "静的データ"),
    ("静的 seed", "静的データ"),
    ("静的seed", "静的データ"),
    ("raw 観測値", "観測値"),
    ("raw 集計", "重複を含む集計"),
    ("raw 観測金額", "観測金額（重複を含む）"),
    ("raw 観測", "観測（重複を含む）"),
    ("raw 行数", "観測行数（重複を含む）"),
    ("raw 金額", "観測金額（重複を含む）"),
    ("raw 値", "重複を含む値"),
    ("raw", "重複を含む観測"),
)
PLAIN_EN = (
    ("a raw aggregate", "an aggregate"),
    ("the raw aggregate of", "the aggregate, including duplicates, of"),
    ("Raw observation values", "Observation values"),
    ("raw aggregate", "aggregate including duplicates"),
    ("Required evidence", "What the answer must show"),
    ("is a static snapshot", "is the static data"),
    ("a static snapshot", "static data"),
    ("static 2025 snapshot", "2025 static data"),
    ("Static 2025 snapshot", "2025 static data"),
    ("2025 snapshot", "2025 static data"),
    ("static snapshot", "static data"),
    ("Static snapshot", "Static data"),
    ("snapshot", "static data"),
    ("static seed", "static data"),
    ("raw observed amount", "observed amount (including duplicates)"),
    ("raw observations", "observations (including duplicates)"),
    ("raw observation", "observation (including duplicates)"),
    ("raw rows", "observed rows (including duplicates)"),
    ("raw amount", "observed amount (including duplicates)"),
    ("raw values", "values including duplicates"),
    ("raw value", "value including duplicates"),
)
JARGON = re.compile(r"(?i)\bseed\b|snapshot|スナップショット|\braw\b")
LITERAL_NAMES = re.compile(r"(?:Files|data)(?:/furusato)?/seed|StaticSeed|/seed/|\\seed\\")


def pair(value) -> Text:
    ja, en = value
    if not isinstance(ja, str) or not isinstance(en, str) or not ja.strip() or not en.strip():
        raise ValueError("Participant text must be a pair of non-empty strings: " + repr(value)[:80])
    return Text(ja, en)


def paragraph(value) -> Block:
    return Block("paragraph", {"text": pair(value), "lead": False})


def callout(value, tone="note", title=None) -> Block:
    return Block("callout", {"tone": tone, "text": pair(value), "title": pair(title) if title else None})


def bullet_list(values, *, numbered=False, start=1) -> Block:
    payload = {"numbered": numbered, "items": [value if isinstance(value, Text) else pair(value) for value in values]}
    if numbered and start > 1:
        payload["start"] = start
    return Block("list", payload)


def text_table(headers, rows, caption, widths=None) -> Block:
    def cell(value):
        if isinstance(value, Text):
            return value
        if isinstance(value, tuple):
            return pair(value)
        return Text(str(value), str(value))
    payload = {
        "number": 0, "headers": [cell(h) for h in headers],
        "rows": [[cell(c) for c in row] for row in rows],
        "caption": cell(caption), "wide": len(headers) >= 5,
    }
    if widths:
        if len(widths) != len(headers):
            raise ValueError("Table widths must match the number of columns")
        payload["widths"] = list(widths)
    return Block("table", payload)


def add_section(parent: Section, suffix: str, title, blocks) -> Section:
    number = f"{parent.number}.{suffix}"
    ja, en = title
    section = Section(
        ident=f"{parent.ident}-{suffix}", level=2, number=number,
        title=Text(f"{number} {ja}", f"{number} {en}"), blocks=blocks,
        chapter=parent.chapter, appendix=parent.appendix,
    )
    parent.children.append(section)
    return section


def plain(value: Text) -> Text:
    ja, en = value.ja, value.en
    for old, new in PLAIN_JA:
        ja = ja.replace(old, new)
    for old, new in PLAIN_EN:
        en = en.replace(old, new)
    return Text(ja, en)


def plain_block(block: Block) -> Block:
    value = copy.deepcopy(block)
    if value.kind in {"prompt", "code"}:
        return value
    payload = value.payload
    for key in ("text", "caption", "title", "alt"):
        if isinstance(payload.get(key), Text):
            payload[key] = plain(payload[key])
    if "items" in payload:
        payload["items"] = [plain(item) for item in payload["items"]]
    if "headers" in payload:
        payload["headers"] = [plain(item) for item in payload["headers"]]
    if "rows" in payload:
        payload["rows"] = [[plain(item) for item in row] for row in payload["rows"]]
    return value


class FigureFactory:
    def __init__(self, context, evidence):
        self.context = context
        self.evidence = evidence
        self.used = []

    def block(self, ident: str) -> Block:
        spec = figure_source.FIGURES.get(ident)
        if spec is None:
            raise ValueError("Figure has no participant caption: " + ident)
        if ident.startswith("diagram:"):
            key = ident.split(":", 1)[1]
            if key not in self.context.diagrams:
                raise ValueError("Unknown diagram: " + key)
            source_kind, source_key = "diagram", key
        elif ident in participant_figures():
            figure_path(ident)
            source_kind, source_key = "participant-capture", ident
        else:
            if ident not in self.evidence["captures"]:
                raise ValueError("Capture is not in the reviewed public projection: " + ident)
            source_kind, source_key = "reviewed-capture", ident
        self.used.append(ident)
        return Block("figure", {
            "number": 0, "source_kind": source_kind, "source_key": source_key,
            "caption": pair(spec["caption"]), "alt": pair(spec["alt"]),
        })


def step_blocks(steps, figures: FigureFactory):
    blocks, pending, start = [], [], 1

    def flush():
        nonlocal pending, start
        if pending:
            blocks.append(bullet_list([step["text"] for step in pending], numbered=True, start=start))
            start += len(pending)
            pending = []

    for step in steps:
        unknown = set(step) - {"text", "figures", "code", "prompt"}
        if unknown:
            raise ValueError("Unknown step keys: " + ", ".join(sorted(unknown)))
        pending.append(step)
        extras = [figures.block(ident) for ident in step.get("figures", ())]
        if step.get("code"):
            label, value = step["code"]
            extras.append(Block("code", {"text": value, "language": Text(label, label)}))
        if step.get("prompt"):
            extras.append(Block("prompt", {"text": pair(step["prompt"])}))
        if extras:
            flush()
            blocks.extend(extras)
    flush()
    return blocks


def link_list(links):
    urls = [link if link.startswith("https://") else LEARN_BASE + link for link in links]
    return bullet_list([Text(url, url) for url in urls])


def num(value) -> str:
    return f"{value:,}"


def yen(value) -> tuple[str, str]:
    return (f"{value:,} 円", f"JPY {value:,}")


class Tables:
    """Reference tables generated from repository sources."""

    #: Word column widths in inches (the printable width is about 6.6 inches).
    WIDTHS = {
        "entities": (1.9, 1.5, 0.8, 1.6, 0.8),
        "relationships": (1.9, 2.1, 1.2, 1.4),
        "layer-measures": (0.6, 1.3, 3.8, 0.9),
        "expected-entities": (2.2, 1.6, 1.6, 1.2),
        "expected-relationships": (1.9, 2.3, 1.2, 1.2),
        "expected-values": (2.6, 4.0),
        "expected-august": (2.6, 4.0),
        "expected-gold": (2.6, 4.0),
        "parameters": (0.9, 2.1, 1.2, 2.4),
        "questions": (0.4, 0.8, 4.6, 0.8),
        "record-form": (0.8, 1.0, 2.6, 1.0, 1.2),
    }

    def __init__(self, root: Path, context, facts, manifest):
        self.root, self.context, self.facts, self.manifest = root, context, facts, manifest

    def build(self, name: str) -> list[Block]:
        method = getattr(self, name.replace("-", "_"), None)
        if method is None:
            raise ValueError("Unknown generated table: " + name)
        blocks = method()
        for block in blocks:
            if block.kind == "table" and name in self.WIDTHS:
                if len(self.WIDTHS[name]) != len(block["headers"]):
                    raise ValueError("Table widths must match the number of columns: " + name)
                block.payload["widths"] = list(self.WIDTHS[name])
        return blocks

    def entities(self):
        kinds = {"BigInt": "Integer", "String": "String"}
        rows = []
        for entity in self.context.entities:
            key_type = next(p.value_type for p in entity.properties if p.is_key)
            rows.append([entity.name, entity.key_property, kinds[key_type],
                         entity.static_binding.source_table if entity.static_binding else "—",
                         str(len(entity.properties))])
        return [text_table(
            ["Entity type", ("キー", "Key"), ("キーの型", "Key type"), ("ソーステーブル", "Source table"),
             ("静的 Property の数", "Static properties")],
            rows, ("作成する10個の Entity type", "The ten entity types to create"))]

    def relationships(self):
        rows = [[r.name, f"{r.origin} → {r.target}", r.mapping_table, f"{r.origin_key_column} / {r.target_key_column}"]
                for r in self.context.relationships]
        return [text_table(
            ["Relationship", "Origin → Target", ("キー列を持つテーブル", "Table with the key columns"),
             ("このテーブルで Origin を表す列 / Target を表す列", "Column for the origin / column for the target in that table")],
            rows, ("作成する15個の Relationship", "The fifteen relationships to create"))]

    def layer_measures(self):
        metrics = json.loads((self.root / "workshop" / "v3.0.0-preview" / "powerbi" / "native-metrics-contract.json")
                             .read_text(encoding="utf-8"))
        rows = [[m["table"], m["name"], m["dax"], m["formatString"]] for m in metrics["measures"]]
        return [text_table(
            [("テーブル", "Table"), ("メジャー", "Measure"), "DAX", ("書式", "Format")],
            rows, ("データの種類ごとのメジャー", "Measures for each kind of data"))]

    def expected_entities(self):
        context = self.context
        rows = [[e.name, e.static_binding.source_table if e.static_binding else "—", e.key_property,
                 num(context.node_count(e.name))] for e in context.entities]
        rows.append([("合計", "Total"), "—", "—", num(context.expected["nodeTotal"])])
        return [text_table(
            ["Entity type", ("ソーステーブル", "Source table"), ("キー", "Key"), ("件数（ノード数）", "Count (nodes)")],
            rows, ("Entity type ごとの件数", "Count per entity type"))]

    def expected_relationships(self):
        context = self.context
        rows = [[r.name, f"{r.origin} → {r.target}", r.mapping_table, num(context.edge_count(r.name))]
                for r in context.relationships]
        rows.append([("合計", "Total"), "—", "—", num(context.expected["edgeTotal"])])
        return [text_table(
            ["Relationship", "Origin → Target", ("キー列を持つテーブル", "Table with the key columns"), ("件数（エッジ数）", "Count (edges)")],
            rows, ("Relationship ごとの件数", "Count per relationship"))]

    def expected_values(self):
        s, e = self.facts.static, self.context.expected
        category, donor = e["topMunicipalityCategory"], e["tokyoRank1Donor"]

        def count_amount(count, amount):
            return (f"{num(count)} 件 / {num(amount)} 円", f"{num(count)} donations / JPY {num(amount)}")
        rows = [
            [("静的データの寄付件数", "Donations in the static data"), num(s.donation_rows)],
            [("静的データの寄付金額の合計", "Total amount in the static data"), yen(s.donation_total_yen)],
            [("受入件数が1位の自治体", "Municipality with the most donations received"),
             (f"{s.top_municipality_id} {s.top_municipality_name}（{s.top_municipality_prefecture_name}） "
              f"{num(s.top_municipality_count)} 件 / {num(s.top_municipality_total_yen)} 円",
              f"{s.top_municipality_id} {s.top_municipality_name} ({s.top_municipality_prefecture_name}) "
              f"{num(s.top_municipality_count)} donations / JPY {num(s.top_municipality_total_yen)}")],
            [("その自治体で1位のカテゴリ", "Top category for that municipality"),
             (f"CategoryId {category['CategoryId']} {category['CategoryName']} "
              f"{num(category['Count'])} 件 / {num(category['TotalYen'])} 円",
              f"CategoryId {category['CategoryId']} {category['CategoryName']} "
              f"{num(category['Count'])} donations / JPY {num(category['TotalYen'])}")],
            [("東京都の自治体が受け入れた寄付", "Donations received by Tokyo municipalities"),
             count_amount(s.tokyo_received_count, s.tokyo_received_yen)],
            [("東京都に住む寄付者の寄付", "Donations made by Tokyo residents"),
             count_amount(s.tokyo_resident_count, s.tokyo_resident_yen)],
            [("東京都に住み、累計が1位の寄付者", "Tokyo resident with the highest total"),
             (f"DonorId {donor['DonorId']} {donor['DonorName']} {num(donor['DonorStaticCount'])} 件 / "
              f"{num(donor['DonorStaticTotalYen'])} 円",
              f"DonorId {donor['DonorId']} {donor['DonorName']} {num(donor['DonorStaticCount'])} donations / "
              f"JPY {num(donor['DonorStaticTotalYen'])}")],
            [("寄付が0件の寄付者", "Donors with no donations"), num(e["donorsWithoutDonations"])],
            [("受け入れた寄付が0件の自治体", "Municipalities that received no donations"),
             num(e["municipalitiesWithoutDonations"])],
            [("登録された返礼品が0件の事業者", "Suppliers with no registered gifts"), num(e["suppliersWithoutGifts"])],
        ]
        return [text_table([("項目", "Item"), ("期待値", "Expected value")], rows,
                           ("回答の確認に使う代表値", "Key values for checking answers"))]

    def expected_august(self):
        inc, cal, obs = self.context.expected_increment, self.facts.observation.calendar, self.facts.observation
        window = inc["observationWindowUtc"]
        rows = [
            [("観測行数（重複を含む）", "Observed rows (including duplicates)"), num(inc["rawRows"])],
            [("EventID の種類数（重複を除いた件数）", "Distinct EventIDs (rows without duplicates)"), num(inc["uniqueEventIds"])],
            [("重複したEventID", "Duplicated EventIDs"), num(inc["duplicateEventIds"])],
            [("観測金額の合計（重複を含む）", "Observed amount (including duplicates)"), yen(inc["rawAmountYen"])],
            [("重複を除いた金額の合計", "Amount without duplicates"), yen(inc["deduplicatedAmountYen"])],
            [("観測期間（UTC）", "Observation period (UTC)"), f"{window['from']} 〜 {window['to']}"],
            [("UTC での日数", "Days in UTC"),
             (f"{cal.utc_day_count} 日（{cal.first_utc_day} 〜 {cal.last_utc_day}、欠けている日なし）",
              f"{cal.utc_day_count} days ({cal.first_utc_day} to {cal.last_utc_day}, no missing day)")],
            [("UTC の1日あたりの行数（重複を含む）", "Rows per UTC day (including duplicates)"),
             (f"{num(cal.min_rows)} 〜 {num(cal.max_rows)} 行（最少 {cal.min_rows_day} / 最多 {cal.max_rows_day}）",
              f"{num(cal.min_rows)} to {num(cal.max_rows)} rows (fewest {cal.min_rows_day}, most {cal.max_rows_day})")],
            [("UTC の1日あたりの行数（重複を除く）", "Rows per UTC day (without duplicates)"),
             (f"{num(cal.dedup_min_rows)} 〜 {num(cal.dedup_max_rows)} 行", f"{num(cal.dedup_min_rows)} to {num(cal.dedup_max_rows)} rows")],
            [("日本時間での日数", "Days in Japan time"),
             (f"{cal.jst_day_count} 日（{cal.first_jst_day} 〜 {cal.last_jst_day}）",
              f"{cal.jst_day_count} days ({cal.first_jst_day} to {cal.last_jst_day})")],
            [(f"日本時間で {cal.last_jst_day} になる行", f"Rows that fall on {cal.last_jst_day} in Japan time"),
             (f"{num(cal.jst_rollover_rows)} 行（UTC {cal.jst_rollover_from_utc} 〜 {cal.jst_rollover_to_utc}）",
              f"{num(cal.jst_rollover_rows)} rows (UTC {cal.jst_rollover_from_utc} to {cal.jst_rollover_to_utc})")],
            [("3つ目のファイルの公開時刻（PublishedAtUtc）", "Publish time of the third file (PublishedAtUtc)"),
             inc["publishedAtUtc"][2]],
            [("観測件数が1位の自治体（重複を含む）", "Municipality with the most observations (including duplicates)"),
             (f"{obs.top_observed_municipality_id} {num(obs.top_observed_count)} 件 / {num(obs.top_observed_amount_yen)} 円",
              f"{obs.top_observed_municipality_id} {num(obs.top_observed_count)} observations / JPY {num(obs.top_observed_amount_yen)}")],
        ]
        return [text_table([("指標", "Measure"), ("期待値", "Expected value")], rows,
                           ("8月の観測データの期待値", "Expected values for the August observation data"))]

    def expected_gold(self):
        inc, s = self.context.expected_increment, self.facts.static
        gold_rows = s.donation_rows + inc["uniqueEventIds"]
        gold_yen = s.donation_total_yen + inc["deduplicatedAmountYen"]
        rows = [
            [("受け入れた増分（RealtimeIncrement）", "Accepted increments (RealtimeIncrement)"),
             (f"{num(inc['uniqueEventIds'])} 件 / {num(inc['deduplicatedAmountYen'])} 円",
              f"{num(inc['uniqueEventIds'])} rows / JPY {num(inc['deduplicatedAmountYen'])}")],
            [("隔離した重複行", "Quarantined duplicate rows"), num(inc["duplicateEventIds"])],
            [("静的データ（StaticSeed）", "Static data (StaticSeed)"),
             (f"{num(s.donation_rows)} 件 / {num(s.donation_total_yen)} 円",
              f"{num(s.donation_rows)} rows / JPY {num(s.donation_total_yen)}")],
            [("Gold 全体（gold.donations）", "All Gold rows (gold.donations)"),
             (f"{num(gold_rows)} 件 / {num(gold_yen)} 円", f"{num(gold_rows)} rows / JPY {num(gold_yen)}")],
        ]
        return [text_table([("指標", "Measure"), ("期待値", "Expected value")], rows,
                           ("品質処理後の Gold の期待値", "Expected values after quality processing (Gold)"))]

    def parameters(self):
        from .preview30_content import literal_notebook_parameters
        notes = getattr(text_source, "PARAMETER_NOTES", {})
        rows = []
        for number, item in self.manifest["notebooks"].items():
            notebook = json.loads((self.root / item["path"]).read_bytes())
            for name, value in literal_notebook_parameters(notebook, item["path"]).items():
                meaning = notes.get(name)
                rows.append([f"Notebook {number}", name, repr(value),
                             pair(meaning) if meaning else Text("—", "—")])
        return [text_table(["Notebook", ("パラメーター", "Parameter"), ("既定値", "Default"), ("意味", "Meaning")],
                           rows, ("Notebook のパラメーター", "Notebook parameters"))]

    def questions(self):
        rows = [[str(q.number), q.test_id, Text(q.question, q.question), str(len(q.evidence) + len(q.pass_criteria))]
                for q in self.tests]
        return [text_table(["No.", ("質問ID", "Question ID"), ("質問（そのまま貼り付けます）", "Question (paste as is)"),
                            ("条件数", "Conditions")], rows, ("評価に使う10問", "The ten evaluation questions"))]

    def record_form(self):
        rows = [[q.test_id, "", "", f"/ {len(q.evidence) + len(q.pass_criteria)}", ""] for q in self.tests]
        return [text_table([("質問ID", "Question ID"), ("実施日時", "Date and time"), ("回答の要点", "Answer summary"),
                            ("満たした条件", "Conditions met"), ("メモ", "Notes")],
                           rows, ("記録用紙", "Record form"))]


def evaluation_sections(appendix: Section, legacy_chapter: Section, start: int):
    """Reuse the protected ten questions and their scoring tables with plain wording."""
    questions = [child for child in legacy_chapter.children if re.match(r"^\d+\.(\d+)\s+T\d\d", child.title.ja)]
    if len(questions) != 10:
        raise ValueError("Expected ten evaluation question sections in the shared source")
    for offset, source in enumerate(questions):
        title_ja = re.sub(r"^\d+\.\d+\s+", "", source.title.ja)
        title_en = re.sub(r"^\d+\.\d+\s+", "", source.title.en)
        blocks = [plain_block(block) for block in source.blocks if block.kind != "figure"]
        add_section(appendix, str(start + offset), (title_ja, title_en), blocks)


def compose(roots, *, root: Path, context, facts, tests, evidence, manifest, legacy_original):
    figures = FigureFactory(context, evidence)
    tables = Tables(root, context, facts, manifest)
    tables.tests = tests
    chapters = {s.chapter: s for s in roots if s.chapter}
    appendices = {s.appendix: s for s in roots if s.appendix}
    if set(text_source.CHAPTERS) != set(range(1, 25)):
        raise ValueError("Participant text must define all 24 chapters")
    for number, section in chapters.items():
        ja, en = text_source.CHAPTER_TITLES[number]
        section.title = Text(f"{number}. {ja}", f"{number}. {en}")
        spec = text_source.CHAPTERS[number]
        intro = [paragraph(value) for value in spec["intro"]]
        if spec.get("before"):
            intro.append(paragraph(("準備するもの・確認すること", "Before you start")))
            intro.append(bullet_list(spec["before"]))
        add_section(section, "1", SECTION_TITLES["intro"], intro)
        steps = step_blocks(spec["steps"], figures) + [callout(value) for value in spec.get("tips", ())]
        add_section(section, "2", SECTION_TITLES["steps"], steps)
        suffix = 3
        if spec.get("checks"):
            add_section(section, str(suffix), SECTION_TITLES["checks"], [text_table(
                [("確認すること", "What to check"), ("うまくいかないとき", "If it does not work")],
                [[pair(check), pair(fix)] for check, fix in spec["checks"]],
                ("この章の完了条件", "Completion checks for this chapter"), widths=(2.4, 4.2))])
            suffix += 1
        if spec.get("tables"):
            add_section(section, str(suffix), SECTION_TITLES["tables"],
                        [block for name in spec["tables"] for block in tables.build(name)])
            suffix += 1
        if spec.get("links"):
            add_section(section, str(suffix), SECTION_TITLES["links"], [link_list(spec["links"])])
    for letter, section in appendices.items():
        ja, en = text_source.APPENDIX_TITLES[letter]
        section.title = Text(f"付録 {letter}　{ja}", f"Appendix {letter} — {en}")
        spec = text_source.APPENDICES[letter]
        blocks = [paragraph(value) for value in spec.get("intro", ())]
        if spec.get("steps"):
            blocks.append(bullet_list([step["text"] for step in spec["steps"]], numbered=True))
        if spec.get("items"):
            blocks.append(text_table([("名前", "Name"), ("内容", "What it is")],
                                     [[pair(a), pair(b)] for a, b in spec["items"]],
                                     ("追加で試せる演習", "Optional exercises"), widths=(2.0, 4.6)))
        if spec.get("troubleshooting"):
            blocks.append(text_table([("症状", "Symptom"), ("確認と対処", "Check and fix")],
                                     [[pair(a), pair(b)] for a, b in spec["troubleshooting"]],
                                     ("うまくいかないときの確認", "Troubleshooting"), widths=(2.2, 4.4)))
        table_names = [name for name in spec.get("tables", ()) if name != "criteria"]
        for name in table_names:
            blocks.extend(tables.build(name))
        blocks.extend(callout(value) for value in spec.get("tips", ()))
        if spec.get("links"):
            blocks.append(link_list(spec["links"]))
        add_section(section, "1", ({"A": ("期待値", "Expected values"), "B": ("パラメーター", "Parameters"),
                                    "C": ("使い方", "How to use this appendix"), "D": ("一覧", "List"),
                                    "E": ("確認と対処", "Checks and fixes")}[letter]), blocks)
        if letter == "C" and "criteria" in spec.get("tables", ()):
            evaluation_sections(section, legacy_original[17], 2)
    leftovers = []
    for section in roots:
        for item in section.walk():
            for block in item.blocks:
                for value in _texts(block):
                    stripped = LITERAL_NAMES.sub("", value.ja + " " + value.en)
                    if JARGON.search(stripped):
                        leftovers.append((item.number, JARGON.search(stripped).group(0), value.ja[:60]))
    if leftovers:
        raise ValueError("Uncommon terms remain in the participant edition: " + repr(leftovers[:8]))
    return {"figures": figures.used}


def _texts(block: Block):
    payload = block.payload
    for key in ("text", "caption", "title", "alt"):
        if isinstance(payload.get(key), Text):
            yield payload[key]
    for item in payload.get("items", ()):
        yield item
    for item in payload.get("headers", ()):
        yield item
    for row in payload.get("rows", ()):
        yield from row
