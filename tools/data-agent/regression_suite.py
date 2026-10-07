"""Public extended regression suite (B01-B14) for the formal Data Agent.

The 14 development questions were exposed during the 2026-10-07 tuning, so
they are regression material, not a held-out set. Every expected value is
recomputed here from the packaged workshop CSVs and source definitions, and
the committed ``regression/extended-suite.json`` must equal ``build_suite``.

Expected values are grading keys for reviewers. Never copy them into Agent
instructions, examples or profiles. ``screen`` only lists which expected
tokens appear in a captured answer; it is not a verdict.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from native_evaluation import EvaluationError, digest, file_digest, validate_suite

REPO = Path(__file__).resolve().parents[2]
VERSION_ROOT = Path("workshop") / "v3.0.0-preview"
SUITE_FILE = Path(__file__).resolve().parent / "regression" / "extended-suite.json"
JST = timezone(timedelta(hours=9))
UTC = timezone.utc


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _utc(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)


def _iso(value: datetime) -> str:
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _yen(value: int) -> str:
    return f"{value:,}円"


def _count(value: int) -> str:
    return f"{value:,}件"


def _window(rows: list[dict[str, str]], start: datetime, end: datetime) -> dict[str, Any]:
    hits = [r for r in rows if start <= _utc(r["DonatedAt"]) < end]
    times = sorted(_utc(r["DonatedAt"]) for r in hits)
    return {
        "count": len(hits),
        "amount_yen": sum(int(r["DonationAmountYen"]) for r in hits),
        "window_utc": [_iso(start), _iso(end)],
        "first_observed_utc": _iso(times[0]) if times else None,
        "last_observed_utc": _iso(times[-1]) if times else None,
    }


def _measure(tmdl: str, name: str) -> str:
    match = re.search(rf"^\s*measure {re.escape(name)} = (.+)$", tmdl, re.MULTILINE)
    if not match:
        raise EvaluationError(f"Semantic model measure is missing: {name}")
    return match.group(1).strip()


def compute_facts(repo: Path = REPO) -> tuple[dict[str, Any], list[Path]]:
    """Recompute every expected value from repository sources only."""
    root = repo / VERSION_ROOT
    data = root / "data"
    seed = {name: _rows(data / "seed" / f"{name}.csv") for name in (
        "donation_orders", "municipalities", "prefectures", "gifts", "categories",
        "businesses", "business_gifts",
    )}
    increment_files = sorted((data / "increment").glob("donation_events_*.csv"))
    raw = [row for path in increment_files for row in _rows(path)]
    seen, accepted = set(), []
    for row in raw:
        if row["EventID"] not in seen:
            seen.add(row["EventID"])
            accepted.append(row)

    tmdl_path = root / "powerbi" / "Furusato_Analytics.SemanticModel" / "definition" / "tables" / "寄附.tmdl"
    tmdl = tmdl_path.read_text(encoding="utf-8")
    static_measure = _measure(tmdl, "静的寄附件数")
    labels = re.findall(r"'寄附'\[データソース\] = \"(\w+)\"", tmdl)
    if not {"StaticSeed", "RealtimeIncrement"} <= set(labels):
        raise EvaluationError("Semantic model data-source labels changed.")

    notebook_path = root / "notebooks" / "Notebook_05_Furusato_Analytics_Quality_and_BI.ipynb"
    notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
    code = "".join("".join(cell.get("source", [])) for cell in notebook["cells"]
                   if cell.get("cell_type") == "code")
    thresholds = set(re.findall(
        r'F\.col\("DonationAmountYen"\) > F\.lit\((\d+)\)\)\.alias\("IsHighValue"\)', code))
    if len(thresholds) != 1:
        raise EvaluationError("Notebook05 high-value threshold is missing or ambiguous.")
    threshold = int(thresholds.pop())

    contract_path = root / "ontology" / "generation2-contract.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    relationships = {
        item["name"]: (item["fromEntity"], item["toEntity"])
        for item in _walk(contract)
        if isinstance(item, dict) and {"name", "fromEntity", "toEntity"} <= set(item)
    }

    municipalities = {m["MunicipalityID"]: m for m in seed["municipalities"]}
    gifts = {g["GiftID"]: g for g in seed["gifts"]}
    categories = {c["CategoryID"]: c for c in seed["categories"]}
    businesses = {b["BusinessID"]: b for b in seed["businesses"]}
    donors = {d["DonorID"]: d for d in _rows(data / "seed" / "donors.csv")}
    static = seed["donation_orders"]

    def ranked(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
        totals: dict[str, list[int]] = defaultdict(lambda: [0, 0])
        for row in rows:
            totals[row["MunicipalityID"]][0] += 1
            totals[row["MunicipalityID"]][1] += int(row["DonationAmountYen"])
        order = sorted(totals.items(), key=lambda kv: (-kv[1][1], kv[0]))
        return [{
            "rank": index, "municipality_id": key,
            "municipality_name": municipalities[key]["MunicipalityName"],
            "prefecture_name": municipalities[key]["PrefectureName"],
            "count": value[0], "amount_yen": value[1],
        } for index, (key, value) in enumerate(order, 1)]

    def totals(rows: list[dict[str, str]]) -> dict[str, int]:
        return {"count": len(rows), "amount_yen": sum(int(r["DonationAmountYen"]) for r in rows)}

    facts: dict[str, Any] = {}
    facts["B01"] = _window(raw, datetime(2026, 8, 31, 15, tzinfo=UTC), datetime(2026, 9, 1, 15, tzinfo=UTC))
    day = [r for r in raw if _utc(r["DonatedAt"]).date().isoformat() == "2026-08-17"]
    hours: dict[int, list[int]] = {hour: [0, 0] for hour in range(24)}
    for row in day:
        hour = _utc(row["DonatedAt"]).hour
        hours[hour][0] += 1
        hours[hour][1] += int(row["DonationAmountYen"])
    facts["B03"] = {
        **totals(day),
        "hours_utc": [{"hour": h, "count": c, "amount_yen": a} for h, (c, a) in hours.items()],
    }
    facts["B04"] = _window(raw, datetime(2026, 8, 11, 15, tzinfo=UTC), datetime(2026, 8, 12, 15, tzinfo=UTC))

    gold = [("StaticSeed", r) for r in static] + [("RealtimeIncrement", r) for r in accepted]
    by_layer = {label: [r for layer, r in gold if layer == label] for label in ("StaticSeed", "RealtimeIncrement")}
    facts["B02"] = {"result": "BLANK", "measure": "静的寄附件数", "definition": static_measure,
                    "outer_filter": "RealtimeIncrement"}
    facts["B05"] = {
        "static_seed": totals(by_layer["StaticSeed"]),
        "accepted_increment": totals(by_layer["RealtimeIncrement"]),
        "gold_total": totals([r for _, r in gold]),
        "raw_increment_not_gold": totals(raw),
    }
    high = {label: sum(int(r["DonationAmountYen"]) > threshold for r in rows) for label, rows in by_layer.items()}
    facts["B06"] = {"threshold_yen_exclusive": threshold, "total": sum(high.values()),
                    "static_seed": high["StaticSeed"], "accepted_increment": high["RealtimeIncrement"]}

    def jst_month(month: str) -> dict[str, int]:
        return totals([r for _, r in gold if _utc(r["DonatedAt"]).astimezone(JST).strftime("%Y-%m") == month])

    current, previous = jst_month("2026-08"), jst_month("2025-08")
    facts["B07"] = {
        "current_2026_08_jst": current, "previous_2025_08_jst": previous,
        "difference_yen": current["amount_yen"] - previous["amount_yen"],
        "ratio": round(current["amount_yen"] / previous["amount_yen"], 2),
        "growth_percent": round((current["amount_yen"] / previous["amount_yen"] - 1) * 100, 1),
    }
    convenience = [r for r in static if r["PaymentMethod"] == "コンビニ決済"]
    facts["B08"] = {"payment_method": "コンビニ決済", **totals(convenience), "top3": ranked(convenience)[:3]}

    gift = gifts["3001234"]
    suppliers = sorted(bg["BusinessID"] for bg in seed["business_gifts"] if bg["GiftID"] == "3001234")
    facts["B09"] = {
        "gift_id": "3001234", "gift_name": gift["GiftName"],
        "suppliers": [{"business_id": b, "business_name": businesses[b]["BusinessName"]} for b in suppliers],
    }
    osaka_received = [r for r in static if municipalities[r["MunicipalityID"]]["PrefectureName"] == "大阪府"]
    osaka_resident = [r for r in static if donors[r["DonorID"]]["PrefectureName"] == "大阪府"]
    facts["B10"] = {"received_by_osaka_municipalities": totals(osaka_received),
                    "donated_by_osaka_residents": totals(osaka_resident)}
    facts["B11"] = {name: {"from": relationships[name][0], "to": relationships[name][1]}
                    for name in ("DonorLivesInPrefecture", "DonationToMunicipality")}
    national = ranked(static)
    izumisano = next(r for r in national if r["municipality_id"] == "272132")
    prefecture_rank = 1 + sum(
        r["amount_yen"] > izumisano["amount_yen"] for r in national
        if r["prefecture_name"] == izumisano["prefecture_name"]
    )
    facts["B12"] = {**izumisano, "national_rank": izumisano["rank"], "prefecture_rank": prefecture_rank}
    del facts["B12"]["rank"]
    hokkaido_fish = [r for r in static
                     if municipalities[r["MunicipalityID"]]["PrefectureID"] == "1"
                     and gifts[r["GiftID"]]["CategoryID"] == "2"]
    facts["B13"] = {"metric_key": "01-02", "prefecture_name": "北海道",
                    "category_name": categories["2"]["CategoryName"], **totals(hokkaido_fish)}
    facts["B14"] = {"top5": national[:5]}

    sources = sorted((data / "seed").glob("*.csv")) + increment_files + [
        data / "dataset-manifest.json", data / "SHA256SUMS.txt", tmdl_path, notebook_path, contract_path,
    ]
    return facts, sources


def _walk(value: Any):
    if isinstance(value, dict):
        yield value
        for item in value.values():
            yield from _walk(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk(item)


def _municipality(row: dict[str, Any]) -> str:
    return (f"{row['municipality_id']} {row['municipality_name']} "
            f"{_count(row['count'])} / {_yen(row['amount_yen'])}")


QUESTIONS = {
    "B01": ("time-JST-boundary", "Eventhouse", ["KQL"],
            "日本時間で2026年9月1日に当たる生の観測データはありますか？あれば件数と金額、実際に観測されたUTCの最初と最後の時刻も教えてください。"),
    "B02": ("model-DAX-explanation", "SemanticModel", [],
            "Power BIモデル（Gold）で、データソースをRealtimeIncrementに絞った状態で［静的寄附件数］を評価すると、結果はどうなりますか？メジャー定義に基づいて理由も説明してください。"),
    "B03": ("time-UTC-hourly", "Eventhouse", ["KQL"],
            "2026年8月17日（UTCの日付）の生観測を、UTCの1時間ごとに件数と金額で、全ファイル合算して出してください。日本時間には変換しないでください。"),
    "B04": ("time-JST-day", "Eventhouse", ["KQL"],
            "日本時間の2026年8月12日の生観測は何件で、金額はいくらですか？検索に使ったUTCの区間と、実際の最初と最後の観測時刻（UTC）も示してください。"),
    "B05": ("model-gold-layers", "SemanticModel", [],
            "品質処理後のGoldモデルで、静的seedと受入済みの増分を、それぞれ件数と金額で教えてください。合計も出して。"),
    "B06": ("model-flag", "SemanticModel", [],
            "Goldモデルの高額寄附フラグが付いた寄附は何件ありますか？静的seedと受入増分の内訳と、フラグの判定条件も教えてください。"),
    "B07": ("model-time-intelligence", "SemanticModel", [],
            "Goldモデルで2026年8月の寄附総額はいくらですか？前年同期間（2025年8月）と比べてください。"),
    "B08": ("static-filter-ranking", "Lakehouse", ["SQL"],
            "静的seedで、コンビニで支払われた寄付は何件・いくら？受入金額が多い自治体の上位3つもIDと名前つきで教えて。"),
    "B09": ("static-catalog", "Lakehouse or Ontology", [],
            "返礼品3001234をカタログに載せている事業者をすべて教えてください。実際に発送した事業者かどうかの区別もお願いします。"),
    "B10": ("static-ambiguity", "Lakehouse", ["SQL"], "大阪の寄付ってどれくらいですか。"),
    "B11": ("ontology-schema", "Ontology", [],
            "Ontologyで、寄附者と都道府県、寄附と自治体をつなぐ関係の名前と向きを教えてください。"),
    "B12": ("static-entity", "Lakehouse", ["SQL"], "泉佐野市の静的データでの受入件数と金額、全国順位と府内順位を教えて。"),
    "B13": ("static-metric", "Lakehouse", ["SQL"],
            "北海道の自治体が受け入れた「魚介類・海産物」カテゴリの寄付を、県別カテゴリ指標で件数と金額を教えて。"),
    "B14": ("static-ranking", "Lakehouse", ["SQL"], "静的seedで受入金額が多い自治体トップ5を、件数も一緒に教えて。"),
}

FACT_RULE = "回答に書いた数値・ID・名称・時刻・結論がすべて期待値と一致し、誤った断定がない。期待値: "


def _content(case_id: str, f: dict[str, Any]) -> tuple[str, str]:
    """Return (expected-value statement, content requirement) per case."""
    if case_id in {"B01", "B04"}:
        expected = (f"{_count(f['count'])} / {_yen(f['amount_yen'])}。検索区間 UTC [{f['window_utc'][0]}, "
                    f"{f['window_utc'][1]})。実観測 UTC {f['first_observed_utc']}〜{f['last_observed_utc']}。")
        need = ("件数・金額、UTCの検索区間、実際の最初と最後の観測時刻（UTC）をすべて示す。"
                "「存在しない」「0件」と断定しない。")
        return expected, need
    if case_id == "B02":
        return (f"BLANK（空）。［{f['measure']}］= {f['definition']}。外側のデータソース={f['outer_filter']}と交差して空集合。",
                "BLANKの理由を当該メジャーのKEEPFILTERSと外側フィルターの交差で説明する。"
                "KEEPFILTERSなしのCALCULATEも同じく空になる等と一般化しない（なしなら同一列の外側フィルターは置き換えられる）。"
                "80,000などの値を返すとしない。")
    if case_id == "B03":
        first = "、".join(f"{h['hour']:02}時台 {_count(h['count'])}/{_yen(h['amount_yen'])}" for h in f["hours_utc"][:3])
        return (f"UTC 24時間すべて。合計 {_count(f['count'])} / {_yen(f['amount_yen'])}。{first}…（全24時間は expected_values）。",
                "UTCの00時〜23時の24時間すべてを全ファイル合算で示し、日本時間に変換しない。")
    if case_id == "B05":
        return (f"StaticSeed {_count(f['static_seed']['count'])}/{_yen(f['static_seed']['amount_yen'])}、"
                f"RealtimeIncrement {_count(f['accepted_increment']['count'])}/{_yen(f['accepted_increment']['amount_yen'])}、"
                f"合計 {_count(f['gold_total']['count'])}/{_yen(f['gold_total']['amount_yen'])}。",
                f"静的・受入増分・合計の3つを件数と金額で示し、raw {_count(f['raw_increment_not_gold']['count'])}/"
                f"{_yen(f['raw_increment_not_gold']['amount_yen'])}をGoldとして示さない。")
    if case_id == "B06":
        return (f"{_count(f['total'])}（StaticSeed {_count(f['static_seed'])}、RealtimeIncrement "
                f"{_count(f['accepted_increment'])}）。条件は寄附金額 > {f['threshold_yen_exclusive']:,}円。",
                f"合計と2つの内訳、判定条件（{f['threshold_yen_exclusive']:,}円ちょうどは含まない）を示す。")
    if case_id == "B07":
        return (f"2026年8月（JST日付）{_yen(f['current_2026_08_jst']['amount_yen'])}（{_count(f['current_2026_08_jst']['count'])}）、"
                f"2025年8月 {_yen(f['previous_2025_08_jst']['amount_yen'])}（{_count(f['previous_2025_08_jst']['count'])}）。"
                f"差 {_yen(f['difference_yen'])}、倍率 約{f['ratio']}倍、増加率 約{f['growth_percent']}%。",
                "両期間の金額を示し、差・倍率・増減率を取り違えない（増加率を倍率として書かない）。")
    if case_id == "B08":
        return (f"{f['payment_method']} {_count(f['count'])} / {_yen(f['amount_yen'])}。上位3: "
                + "、".join(_municipality(r) for r in f["top3"]) + "。",
                "件数・金額と、上位3自治体のID・名前・金額を示す。")
    if case_id == "B09":
        names = "、".join(f"{s['business_id']} {s['business_name']}" for s in f["suppliers"])
        return (f"{len(f['suppliers'])}社: {names}。返礼品 {f['gift_id']} {f['gift_name']}。",
                "全事業者をIDと名前で示し、カタログ登録は実際の発送・履行の証明ではないと区別する。")
    if case_id == "B10":
        a, b = f["received_by_osaka_municipalities"], f["donated_by_osaka_residents"]
        return (f"受入（大阪府の自治体が受け取った）{_count(a['count'])}/{_yen(a['amount_yen'])}、"
                f"在住（大阪府在住者が寄付した）{_count(b['count'])}/{_yen(b['amount_yen'])}。",
                "受入と在住の両方を区別して示すか、どちらかを確認する。2つを合算しない。")
    if case_id == "B11":
        text = "。".join(f"{name}: {v['from']} → {v['to']}" for name, v in f.items())
        return text + "。", "2つの関係の名前と向き（from → to）を両方示す。"
    if case_id == "B12":
        return (f"{f['municipality_id']} {f['municipality_name']}（{f['prefecture_name']}）: {_count(f['count'])} / "
                f"{_yen(f['amount_yen'])}、全国金額順位{f['national_rank']}位、府内{f['prefecture_rank']}位。",
                "件数・金額・全国順位・府内順位をすべて示す。")
    if case_id == "B13":
        return (f"格納キー {f['metric_key']}、{f['prefecture_name']}×{f['category_name']}: "
                f"{_count(f['count'])} / {_yen(f['amount_yen'])}。",
                "県別カテゴリ指標の件数と金額を示す。")
    if case_id == "B14":
        return ("; ".join(f"{r['rank']} {_municipality(r)}" for r in f["top5"]) + "。",
                "上位5自治体を順位・ID・名前・件数・金額で示す。")
    raise EvaluationError(f"Unknown regression case: {case_id}")


def build_suite(repo: Path = REPO) -> dict[str, Any]:
    facts, sources = compute_facts(repo)
    cases = []
    for case_id, (area, source, languages, question) in QUESTIONS.items():
        expected, need = _content(case_id, facts[case_id])
        cases.append({
            "id": case_id, "area": area, "question": question,
            "expected_source": source, "required_query_languages": languages,
            "expected": expected, "expected_values": facts[case_id],
            "conditions": [
                {"id": f"{case_id}.fact", "text": FACT_RULE + expected},
                {"id": f"{case_id}.content", "text": need},
            ],
        })
    suite = {
        "schema_version": 1, "kind": "regression", "cases": cases,
        "provenance": {
            "builder": "tools/data-agent/regression_suite.py::build_suite",
            "origin": "2026-10-07 development questions B01-B14 (exposed; not a held-out set)",
            "rubric": "fact = every stated value matches; content = every listed element present",
            "files": {path.relative_to(repo).as_posix(): file_digest(path) for path in sources},
        },
    }
    validate_suite(suite)
    return suite


def _tokens(case: dict[str, Any]) -> list[str]:
    """Distinctive expected numbers/IDs for screening only (never a verdict)."""
    found = re.findall(r"\d{1,3}(?:,\d{3})+|\d{6,7}|\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", case["expected"])
    return list(dict.fromkeys(found))


def screen(suite: dict[str, Any], answers: dict[str, str]) -> list[dict[str, Any]]:
    result = []
    for case in suite["cases"]:
        text = answers.get(case["id"])
        if text is None:
            result.append({"case_id": case["id"], "captured": False})
            continue
        compact = text.replace("，", ",")
        tokens = _tokens(case)
        missing = [t for t in tokens if t not in compact and t.replace(",", "") not in compact]
        result.append({
            "case_id": case["id"], "captured": True,
            "expected_tokens": len(tokens), "missing_tokens": missing,
            "note": "screening aid only; a human/AI-assisted review decides PASS/FAIL",
        })
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=["check", "write", "screen"])
    parser.add_argument("--answers", type=Path, help="screen: private JSON {case_id: final answer text}")
    args = parser.parse_args(argv)
    suite = build_suite(REPO)
    if args.command == "write":
        SUITE_FILE.parent.mkdir(parents=True, exist_ok=True)
        SUITE_FILE.write_text(json.dumps(suite, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote {SUITE_FILE.relative_to(REPO).as_posix()} ({len(suite['cases'])} cases).")
        return 0
    if args.command == "check":
        committed = json.loads(SUITE_FILE.read_text(encoding="utf-8"))
        same = digest(committed) == digest(suite)
        print(json.dumps({"suite_sha256": digest(suite), "committed_matches_sources": same}))
        return 0 if same else 2
    if args.answers is None:
        parser.error("screen requires --answers")
    answers = json.loads(args.answers.read_text(encoding="utf-8"))
    print(json.dumps(screen(suite, answers), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
