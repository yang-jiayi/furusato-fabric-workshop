"""Negative tests for the public-source Data Agent practice gates.

The v2.7.0 documentation update added six blocks written from first-party
Microsoft documentation: the example-query quality gate (16.6.1), the
instruction-boundary and latency section (16.8), the evidence and re-run section
(17.12), the publish-description contract (18.2), continuous evaluation and ALM
(C.7), and the semantic-model reference appendix (D.7). Two earlier statements
were reframed at the same time: the character budget for the global instructions
and the reason the KQL shapes live in the source instructions.

Each case below plants exactly the defect one gate exists to catch and asserts
that the gate reports it. A gate that cannot be made to fail proves nothing.

Every identifier used here is synthetic: the mail address is on the reserved
``example.invalid`` domain and the security identifier is a placeholder. No real
person, tenant or machine is named anywhere in this file or in the validators.
"""

from __future__ import annotations

import argparse
import importlib.util
import pathlib
import sys
import zipfile
from xml.etree import ElementTree

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools" / "docs"))
sys.path.insert(0, str(ROOT / "tools" / "html"))

from furusato_docs import quality  # noqa: E402
from furusato_docs.context import load_context  # noqa: E402
from furusato_docs.deliverables import deliverable_names, validate_edition  # noqa: E402
from furusato_docs.validators import Report, _document_text  # noqa: E402

spec = importlib.util.spec_from_file_location("vd", ROOT / "tools" / "docs" / "validate_docs.py")
vd = importlib.util.module_from_spec(spec)
sys.modules["vd"] = vd
spec.loader.exec_module(vd)

GUIDE = ROOT / "docs" / "Fabric_IQ_Ontology_Workshop_Furusato_Participant_v2.7.0.docx"

#: Synthetic authoring-trail values. They exist only to prove the scan fires;
#: neither identifies anything real.
SYNTHETIC_MAIL = "someone@synthetic.example"
SYNTHETIC_SID = "S-1-5-21-1111111111-2222222222-3333333333-4444"


def guide_text(path: pathlib.Path = GUIDE) -> str:
    with zipfile.ZipFile(path) as archive:
        tree = ElementTree.fromstring(archive.read("word/document.xml"))
    return _document_text(tree)


def failed(report: Report) -> set[str]:
    return {finding.check for finding in report.findings if finding.level == "FAIL"}


def run_text(context, text: str) -> set[str]:
    report = Report(target="negative test")
    quality.check_data_agent_practice(context, text, report)
    return failed(report)


def drop(text: str, needle: str) -> str:
    """Remove every occurrence, so a contents-listing copy cannot mask the defect."""
    if needle not in text:
        raise AssertionError(f"the guide no longer contains {needle!r}; update the test")
    return text.replace(needle, "")


def replace_required(text: str, needle: str, replacement: str) -> str:
    if needle not in text:
        raise AssertionError(f"the guide no longer contains {needle!r}; update the test")
    return text.replace(needle, replacement)


def inject(text: str, marker: str, sentence: str) -> str:
    index = text.rfind(marker)
    if index < 0:
        raise AssertionError(f"{marker!r} is missing; update the test")
    return text[: index + len(marker)] + sentence + text[index + len(marker) :]


def drop_example_delivery_claim(text: str) -> str:
    markers = (
        "本教材では Eventhouse の例クエリは別途登録せず",
        "この統合プロファイルでは Eventhouse の例クエリも登録します",
    )
    present = [marker for marker in markers if marker in text]
    if len(present) != 1:
        raise AssertionError("Expected one unambiguous edition-specific example-delivery statement.")
    return drop(text, present[0])


#: (label, mutation, the check that must fail)
TEXT_CASES = (
    (
        "the character budget goes back to being a universal Fabric limit",
        lambda text: text + "\nFabric の Data agent 画面が受け付ける上限は 15,000 文字です。",
        "content.instructionBudgetNotUniversal",
    ),
    (
        "the budget stops being described as this workshop's own ceiling",
        lambda text: drop(text, "これは本ワークショップが自分に課した安全側の上限であり"),
        "content.instructionBudgetFraming",
    ),
    (
        "the budget stops telling the reader to check the current product docs",
        lambda text: drop(text, "その時点の製品ドキュメントと画面表示で現在値を確認してください"),
        "content.instructionBudgetFraming",
    ),
    (
        "the KQL shapes go back to a product-wide capability claim",
        lambda text: text + "\n定義形式に例クエリの領域が無いためです。",
        "content.kustoShapeNotCapability",
    ),
    (
        "the KQL shape rationale stops being scoped to the shipped bundle",
        drop_example_delivery_claim,
        "content.kustoShapeRationale",
    ),
    (
        "the KQL shape note stops deferring to the capability matrix",
        lambda text: drop(text, "付録 E の Data Agent source capability matrix"),
        "content.kustoShapeRationale",
    ),
    (
        "the example-query gate loses its heading",
        lambda text: drop(text, "16.6.1 例クエリの品質ゲート"),
        "content.exampleQueryGate",
    ),
    (
        "the example-query gate stops requiring stored value formats",
        lambda text: drop(text, "絞り込みの値は、実際に格納されている表記と形式のまま書く"),
        "content.exampleQueryGate",
    ),
    (
        "the example-query gate stops pointing at the run details",
        lambda text: drop(text, "回答の［実行詳細］で、その質問にどの例が使われたかを確認する"),
        "content.exampleQueryGate",
    ),
    (
        "the guide starts promising a top-N retrieval count",
        lambda text: text + "\n毎回、上位 4 件の例が渡されます。",
        "content.noRetrievalCount",
    ),
    (
        "the instruction-boundary section stops saying instructions are not access control",
        lambda text: drop(text, "指示はアクセス制御ではありません"),
        "content.instructionBoundary",
    ),
    (
        "the guide starts claiming uniform row and column control",
        lambda text: drop(
            text, "行単位・列単位の制御がどのソースでも同じように使えると仮定しないでください"
        ),
        "content.instructionBoundary",
    ),
    (
        "the OneLake Security rationale disappears",
        lambda text: drop(text, "本番でアクセス制御が不要だという意味ではありません"),
        "content.instructionBoundary",
    ),
    (
        "the latency table stops refusing to print timings",
        lambda text: drop(text, "ここでは秒数や倍率は示しません"),
        "content.instructionBoundary",
    ),
    (
        "the evidence ladder loses its engine-history caveat",
        lambda text: drop(text, "見られないソースがあることを理由に不合格にはしません"),
        "content.evidenceAndRerun",
    ),
    (
        "the record sheet stops refusing query text",
        lambda text: drop(text, "記録票の回答欄にクエリ本文を書き写さないでください"),
        "content.evidenceAndRerun",
    ),
    (
        "the re-run rule stops saying it does not weaken the existing one",
        lambda text: drop(text, "この節はそれを弱めません"),
        "content.evidenceAndRerun",
    ),
    (
        "partial re-testing becomes acceptable again",
        lambda text: drop(text, "落ちた問いだけを直して再実行する運用は認めません"),
        "content.evidenceAndRerun",
    ),
    (
        "chapter 19 stops naming both non-chapter-order sections",
        lambda text: drop(text, "章順で並んでいないのは第 17.11 節と第 17.12 節の 2 つです"),
        "content.evidenceAndRerun",
    ),
    (
        "chapter 19 stops stating the evidence order",
        lambda text: drop(text, "「回答本文 → ［実行詳細］ → エンジン側の実行履歴」"),
        "content.evidenceAndRerun",
    ),
    (
        "chapter 19 stops routing a failure through the evidence first",
        lambda text: drop(text, "まず第 17.12 節で証跡を確認し"),
        "content.evidenceAndRerun",
    ),
    (
        "chapter 19 stops ending at the rerun scope",
        lambda text: drop(text, "最後に第 17.12.1 節でやり直す範囲を決めます"),
        "content.evidenceAndRerun",
    ),
    (
        "the UNCLEAR troubleshooting row stops pointing at the evidence",
        lambda text: drop(text, "第 17.12 節の証跡でどこが期待と違うかを見てから"),
        "content.evidenceAndRerun",
    ),
    (
        "chapter 19 goes back to describing a single non-chapter-order section",
        lambda text: text + "\n第 17.11 節だけは順序が異なり、章順ではありません。",
        "content.chapter19DualOrder",
    ),
    (
        "the latency row claims column-level selection again",
        lambda text: replace_required(
            text, "選択したテーブル(とその全列)とエンティティが多いほど",
            "選択したテーブル・列・エンティティが多いほど",
        ),
        "content.instructionBoundary",
    ),
    (
        "the publish description stops being called a routing signal",
        lambda text: drop(text, "この Data Agent に回すかどうかの判断材料にもなります"),
        "content.publishDescription",
    ),
    (
        "the publish description stops naming the synthetic nature of the data",
        lambda text: drop(text, "学習用の合成データ。実在の個人・事業者・寄付実績は含まない"),
        "content.publishDescription",
    ),
    (
        "C.7 stops saying it adds no gate",
        lambda text: drop(text, "C.7 はゲートを増やしません"),
        "content.appendixC7Coverage",
    ),
    (
        "C.7 stops calling the manual scoring canonical",
        lambda text: drop(text, "正本は人の採点"),
        "content.appendixC7Coverage",
    ),
    (
        "C.7 stops requiring the critic to be calibrated on a separate set",
        lambda text: drop(text, "第 17 章とは別に人が採点した集合で較正し"),
        "content.appendixC7Coverage",
    ),
    (
        "C.7 stops refusing to print a pass threshold",
        lambda text: drop(
            text, "合格とみなす水準は案件ごとに決めるものであり、本書では数値を示しません"
        ),
        "content.appendixC7Coverage",
    ),
    (
        "C.7 stops saying the published folder is not edited directly",
        lambda text: drop(text, "公開済みフォルダーを直接編集しない"),
        "content.appendixC7Coverage",
    ),
    (
        "D.7 stops distinguishing Notebook 05 table creation",
        lambda text: drop(text, "D.3 の Notebook 05 は分析用のテーブルを作成します"),
        "content.appendixD7Coverage",
    ),
    (
        "D.7 omits the separate model and report deployment",
        lambda text: drop(
            text, "セマンティックモデルとレポートは、別工程の Deploy-FurusatoPowerBI.ps1 でデプロイします"
        ),
        "content.appendixD7Coverage",
    ),
    (
        "D.7 stops explaining why Core keeps a single authority",
        lambda text: drop(text, "静的な指標の権威を Lakehouse 1 つに固定しています"),
        "content.appendixD7Coverage",
    ),
    (
        "D.7 stops separating model instructions from agent instructions",
        lambda text: drop(text, "モデル固有の指示は AI 向けの準備設定側に書く"),
        "content.appendixD7Coverage",
    ),
    (
        "D.7 starts pinning a capability matrix",
        lambda text: drop(text, "本書では対応表を固定しません"),
        "content.appendixD7Coverage",
    ),
    (
        "the appendix D gate stops separating D.7 from the exercises",
        lambda text: drop(text, "D.7 も実習ではなく、ソースを増やす場合に読む参考情報です"),
        "content.appendixD7Coverage",
    ),
    (
        "a configuration section starts naming a held-out test",
        lambda text: inject(text, "16.6.1 例クエリの品質ゲート", "T07 の判定にも使います。"),
        "content.practiceSectionIsolation",
    ),
    (
        "a lifecycle appendix starts quoting a Core verdict",
        lambda text: inject(text, "C.7.1 評価の輪", "結果は PASS として記録します。"),
        "content.practiceSectionIsolation",
    ),
    (
        "a new section starts making a forward-looking release promise",
        lambda text: inject(text, "16.8 指示で守る境界と、応答時間の変数", "近日、上限が緩和されます。"),
        "content.practiceSectionClaims",
    ),
    (
        "a new section starts printing capacity-unit arithmetic",
        lambda text: inject(text, "C.7.1 評価の輪", "1 回の実行は 400 CU 秒です。"),
        "content.practiceSectionClaims",
    ),
    (
        "a new section starts printing a per-token rate",
        lambda text: inject(text, "D.7.1 Core が追加しない理由", "1,000 トークンあたりで課金されます。"),
        "content.practiceSectionClaims",
    ),
    (
        "a new section starts carrying a code snippet",
        lambda text: inject(text, "C.7.2 プログラムによる評価の位置づけ", "%pip install を実行します。"),
        "content.practiceSectionClaims",
    ),
    (
        "a new section starts naming an SDK",
        lambda text: inject(text, "D.7.2 追加するときに整える順序", "評価は SDK から実行します。"),
        "content.practiceSectionClaims",
    ),
    (
        "a new section starts giving a roadmap directive",
        lambda text: inject(text, "17.12.1 再評価の引き金", "ロードマップに沿って対応します。"),
        "content.practiceSectionClaims",
    ),
    (
        "a new section starts citing a private preview",
        lambda text: inject(text, "C.7.3 ALM", "プライベートプレビューで先行提供されます。"),
        "content.practiceSectionClaims",
    ),
)


def mutate_shots(shots, changes):
    """Return a copy of the shipped few-shots with the given index overrides."""
    clone = [dict(shot) for shot in shots]
    for index, payload in changes.items():
        clone[index].update(payload)
    return clone


def run_runtime(context, shots) -> set[str]:
    report = Report(target="negative test")
    vd._validate_example_query_quality(report, context, shots)
    return failed(report)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--edition", default="", type=validate_edition)
    arguments = parser.parse_args()
    context = load_context(ROOT, document_edition=arguments.edition)
    text = guide_text(ROOT / "docs" / deliverable_names(context.version, arguments.edition).participant)
    failures = 0
    checks = 0

    clean = run_text(context, text)
    checks += 1
    if clean:
        print(f"  FAIL the shipped guide already fails: {sorted(clean)}")
        failures += 1
    else:
        print("  ok   the shipped guide passes every Data Agent practice gate")

    for label, mutate, expected in TEXT_CASES:
        checks += 1
        observed = run_text(context, mutate(text))
        if expected in observed:
            print(f"  ok   detected: {label}")
        else:
            print(f"  FAIL undetected: {label} (expected {expected}, got {sorted(observed)})")
            failures += 1

    # ---------------------------------------------------------------- runtime
    shots = context.agent_fewshots
    checks += 1
    if run_runtime(context, shots):
        print(f"  FAIL the shipped example queries already fail: {sorted(run_runtime(context, shots))}")
        failures += 1
    else:
        print("  ok   the shipped example queries pass every mechanical gate")

    runtime_cases = (
        (
            "two example queries ask the same question",
            mutate_shots(shots, {1: {"question": shots[0]["question"]}}),
            "runtime.exampleQueries.uniqueQuestions",
        ),
        (
            "an example query has no body",
            mutate_shots(shots, {2: {"query": "   "}}),
            "runtime.exampleQueries.nonEmpty",
        ),
        (
            "two example queries start from the same table",
            mutate_shots(shots, {1: {"query": "SELECT 1 FROM dbo.ot_prefecture AS p;"}}),
            "runtime.exampleQueries.distinctEntryTables",
        ),
        (
            "an example query reads a table the Agent does not select",
            mutate_shots(shots, {1: {"query": "SELECT 1 FROM dbo.stg_donation AS s;"}}),
            "runtime.exampleQueries.entryTableSelected",
        ),
    )
    for label, shot_set, expected in runtime_cases:
        checks += 1
        observed = run_runtime(context, shot_set)
        if expected in observed:
            print(f"  ok   detected: {label}")
        else:
            print(f"  FAIL undetected: {label} (expected {expected}, got {sorted(observed)})")
            failures += 1

    # ------------------------------------------------------------- provenance
    provenance_cases = (
        (
            "a presentation deck is tracked",
            ["README.md", "docs/source-deck.pptx"],
            "provenance.noDeckOrVideoAssets",
        ),
        (
            "a screen recording is tracked",
            ["README.md", "docs/walkthrough.mp4"],
            "provenance.noDeckOrVideoAssets",
        ),
        (
            "an animation is tracked",
            ["README.md", "docs/assets/v2.7.0/demo.gif"],
            "provenance.noDeckOrVideoAssets",
        ),
        (
            "a raster asset appears beside the diagrams",
            ["README.md", "docs/assets/v2.7.0/screenshot.jpg"],
            "provenance.noNewRasterAssets",
        ),
    )
    tracked = [
        line
        for line in vd.subprocess.run(
            ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=False
        ).stdout.splitlines()
        if line.strip()
    ]
    checks += 1
    report = Report(target="negative test")
    vd._validate_authoring_source_provenance(ROOT, tracked, report)
    if failed(report):
        print(f"  FAIL the tracked tree already fails provenance: {sorted(failed(report))}")
        failures += 1
    else:
        print("  ok   the tracked tree carries no deck, recording or authoring trail")

    for label, names, expected in provenance_cases:
        checks += 1
        report = Report(target="negative test")
        vd._validate_authoring_source_provenance(ROOT, tracked + names[1:], report)
        if expected in failed(report):
            print(f"  ok   detected: {label}")
        else:
            print(f"  FAIL undetected: {label} (got {sorted(failed(report))})")
            failures += 1

    # The authoring-trail patterns must fire on synthetic values, so the scan is
    # proven to work without any real identifier ever entering the repository.
    trail_cases = (
        ("a Windows security identifier", SYNTHETIC_SID),
        ("a mail address", SYNTHETIC_MAIL),
        ("an OOXML author tuple", "dc:creator"),
        ("a third-party add-in marker", "thinkcell"),
    )
    for label, sample in trail_cases:
        checks += 1
        hits = [why for pattern, why in vd._AUTHORING_TRAIL if pattern.search(sample)]
        if hits:
            print(f"  ok   detected: {label} in a synthetic sample")
        else:
            print(f"  FAIL undetected: {label} in a synthetic sample")
            failures += 1

    checks += 1
    if any(pattern.search("someone@example.invalid") for pattern, _ in vd._AUTHORING_TRAIL):
        print("  FAIL the reserved example.invalid domain is treated as a leak")
        failures += 1
    else:
        print("  ok   allowed: the reserved example.invalid domain is not a leak")

    print(f"\n{checks} Data Agent practice gate tests, {failures} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
