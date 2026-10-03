"""Build a separately dated Word/HTML pair from a sanitized native tuning study."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
from pathlib import Path
import re
import tempfile

from furusato_docs.docx_kit import DocumentBuilder
from furusato_docs.oox import StyleCarrier, apply_japanese_typography, normalise_package_metadata

ROOT = Path(__file__).resolve().parents[2]
VERDICTS = ("PASS", "FAIL", "UNKNOWN")


def validate_study(study):
    if study.get("schemaVersion") != "furusato-native-tuning-study/v1":
        raise ValueError("Unsupported study schema.")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", study["date"]) or not study["rounds"]:
        raise ValueError("A dated, measured study is required.")
    for run in [study["baseline"], *study["rounds"], *([study["unseen"]] if study["unseen"] else [])]:
        size = run["caseCount"]
        if type(size) is not int or size <= 0:
            raise ValueError("Every cohort needs its actual positive denominator.")
        for axis in ("content", "factual"):
            counts = run[axis]
            if set(counts) != set(VERDICTS) or any(type(v) is not int or v < 0 for v in counts.values()):
                raise ValueError("Every PASS/FAIL/UNKNOWN count must be explicit.")
            if sum(counts.values()) != size:
                raise ValueError("A cohort denominator was changed.")
        if run["content"]["PASS"] > run["factual"]["PASS"] or run["content"]["FAIL"] < run["factual"]["FAIL"]:
            raise ValueError("Complete-content counts contradict the factual judgments.")
    if any(run["caseCount"] != study["baseline"]["caseCount"] for run in study["rounds"]):
        raise ValueError("Development comparisons must use the same case count.")
    if study["mainPromoted"] or study["oldStudiesChanged"] or study["humanSignoff"]:
        raise ValueError("This addendum does not authorize promotion, historical rewrites or human signoff.")
    return study


def count_text(counts):
    return " / ".join(str(counts[key]) for key in VERDICTS)


def all_pass(run):
    return run["content"]["PASS"] == run["caseCount"]


def sections(study):
    validate_study(study)
    latest = study["rounds"][-1]
    notice = (
        "最新の固定開発セットは全問PASSです。未使用セットの結果と区別して評価します。"
        if all_pass(latest) else
        "最新の固定開発セットにもFAILまたはUNKNOWNが残っています。0 FAIL達成・品質受入とは扱いません。"
    )
    rows = [[run["label"], str(run["caseCount"]), count_text(run["factual"]), count_text(run["content"])]
            for run in [study["baseline"], *study["rounds"]]]
    result = [
        {"title": "評価結果 / Measured results", "paragraphs": [
            notice, study["cohortNoteJa"],
            "P / F / U = PASS / FAIL / UNKNOWN。表の値は各構成の全回答であり、異なるラウンドの正答を選び集めていません。",
        ], "table": {"headers": ["構成 / Configuration", "問数", "事実 P / F / U", "内容 P / F / U"], "rows": rows}},
        {"title": "未使用セット / Previously unused questions", "paragraphs": [
            ("未使用セットは未実施です。開発セットの結果だけでは未知の質問への品質を主張しません。"
             if study["unseen"] is None else
             f"未使用{study['unseen']['caseCount']}問: 事実 {count_text(study['unseen']['factual'])}、"
             f"内容 {count_text(study['unseen']['content'])}。開発セットとは別の分母です。"),
            "Previously unused questions are separate from the known development cohort. These measured results do not guarantee correctness for arbitrary future questions.",
        ]},
        {"title": "実装した改善 / Implemented changes", "paragraphs": study["changesJa"] + study["changesEn"]},
        {"title": "適用と確認 / Apply and verify", "paragraphs": [
            "比較用Agentを使い、既存の主Agentと履歴を保持します。データ取得先・関係スキーマ・最終回答列を分けて設定します。",
            "SQL/KQL例は実ソースで確認した後、Setup > 各データソース > Example queries でエラーと検証待ちがないことを確認します。直接SQLが成功しただけではAgent内の例の参照を証明しません。",
            "設定の前後と公開後に定義を読み戻します。質問・期待値・必須条件を固定し、構成ごとに各問1回だけ送信します。通信エラー、不明、未送信を分母から除外しません。",
            "一覧はソース側の全件数と表示ID集合を照合し、ランキングは安定IDで順序を確定します。暦年とsnapshot名、観測時刻と合成配信メタデータ、BLANKと0を区別します。",
        ]},
        {"title": "残る事項 / Remaining findings", "paragraphs": study["remainingJa"] + study["remainingEn"]},
        {"title": "証拠と採用境界 / Evidence and adoption boundary", "paragraphs": [
            "主Agentへは昇格していません。元3.0.0と2026-10-02のWord・HTML、100問評価、release tagは変更していません。本資料は別日付の追補です。",
            "判定は固定期待値と実回答を照合したAI補助審査です。独立した人間のsign-offではありません。内部SQL/KQL/GQL/DAXとbackend会話IDはUNOBSERVABLEです。",
            "元100問の33 PASS /57 FAIL /10 UNKNOWNを本資料の小さい分母で置き換えていません。構成テストや例の検証成功をAI回答のPASSへ加算しません。",
            "The main Agent, original studies and existing releases are preserved. No general-population accuracy, native execution-trace proof, product GA or independent human acceptance is claimed.",
        ]},
    ]
    return result


def render_html(study, input_sha):
    title = f"Furusato Data Agent tuning — {study['date']}"
    body = []
    for section in sections(study):
        body.append("<section><h2>" + html.escape(section["title"]) + "</h2>")
        body.extend("<p>" + html.escape(text) + "</p>" for text in section["paragraphs"])
        if "table" in section:
            table = section["table"]
            body.append("<div class='scroll'><table><thead><tr>" + "".join(
                "<th scope='col'>" + html.escape(cell) + "</th>" for cell in table["headers"]) + "</tr></thead><tbody>")
            body.extend("<tr>" + "".join("<td>" + html.escape(cell) + "</td>" for cell in row) + "</tr>"
                        for row in table["rows"])
            body.append("</tbody></table></div>")
        body.append("</section>")
    return f"""<!doctype html>
<html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title><style>
:root{{font-family:"Yu Gothic UI","Segoe UI",sans-serif;color:#223047;background:#f1f5fa;line-height:1.7}}
body{{max-width:1060px;margin:32px auto;padding:0 24px}}header,section{{background:white;padding:24px 32px;margin:20px 0;border-radius:12px}}
header{{border-top:8px solid #174c88}}h1{{font-size:1.8rem}}h2{{font-size:1.3rem;color:#174c88}}.eyebrow{{color:#52667f;font-size:.9rem}}
table{{border-collapse:collapse;width:100%;font-size:.95rem}}th,td{{border:1px solid #d6dfea;padding:10px;text-align:left}}
th{{background:#174c88;color:white}}tbody tr:nth-child(even){{background:#eef3f9}}.scroll{{overflow-x:auto}}
footer{{font-size:.8rem;overflow-wrap:anywhere}}@media print{{body{{max-width:none;margin:0;padding:0;background:white}}
header,section{{margin:0 0 12pt;padding:12pt;border-radius:0}}h2{{break-after:avoid}}tr{{break-inside:avoid}}}}
</style></head><body><header><p class="eyebrow">3.0.0 · separately dated addendum</p>
<h1>{html.escape(title)}</h1><p>回答品質の追加チューニング / Native answer-quality tuning</p></header>
{''.join(body)}<footer>Source study SHA-256: {input_sha}</footer></body></html>
"""


def build(study_path, output):
    study_bytes = study_path.read_bytes()
    study = validate_study(json.loads(study_bytes))
    input_sha = hashlib.sha256(study_bytes).hexdigest()
    output.mkdir(parents=True, exist_ok=True)
    stem = "furusato-data-agent-tuning-" + study["date"].replace("-", "")
    word, webpage = output / (stem + ".docx"), output / (stem + ".html")
    if word.exists() or webpage.exists():
        raise FileExistsError("Use a fresh output directory; preserve earlier rendered evidence.")
    with tempfile.TemporaryDirectory(prefix="tuning-doc-", dir=output) as temporary:
        builder = DocumentBuilder(StyleCarrier.resolve(ROOT), Path(temporary) / "shell.docx")
        builder.paragraph("Furusato Data Agent tuning", style="Title")
        builder.paragraph(study["date"] + " — 3.0.0 別日付追補 / Separately dated addendum")
        for section in sections(study):
            builder.heading(section["title"], 1, new_page=False)
            for text in section["paragraphs"]:
                builder.paragraph(text)
            if "table" in section:
                table = section["table"]
                builder.table(table["headers"], table["rows"], caption=section["title"],
                              widths=[2.8, 0.5, 1.4, 1.4], font_size=9)
        builder.paragraph("Source study SHA-256: " + input_sha, size=8)
        builder.save(word)
    apply_japanese_typography(word)
    normalise_package_metadata(word)
    webpage.write_text(render_html(study, input_sha), encoding="utf-8")
    return {"studySha256": input_sha, "outputs": {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (word, webpage)}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--study", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(build(args.study, args.out), indent=2))


if __name__ == "__main__":
    main()
