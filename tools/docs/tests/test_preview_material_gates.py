"""Negative tests for participant-reference and preview-claim gates.

Appendix C.6 states platform prerequisites from published sources. Appendix D.6
offers general evaluation considerations without authorship history or product
promises. Neither may restate a volatile figure or a confidentiality marking.

Each case here plants exactly the defect one gate exists to catch and asserts
that the gate reports it. A gate that cannot be made to fail proves nothing. The
gates run against text, so nothing on disk is modified.
"""

from __future__ import annotations

import argparse
import importlib.util
import pathlib
import re
import sys
import zipfile
from xml.etree import ElementTree

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools" / "docs"))
sys.path.insert(0, str(ROOT / "tools" / "html"))

from furusato_docs import guide_content, quality  # noqa: E402
from furusato_docs.context import load_context  # noqa: E402
from furusato_docs.deliverables import deliverable_names, validate_edition  # noqa: E402
from furusato_docs.validators import Report, W, _document_text  # noqa: E402

spec = importlib.util.spec_from_file_location("vh", ROOT / "tools" / "html" / "validate_html.py")
vh = importlib.util.module_from_spec(spec)
sys.modules["vh"] = vh
spec.loader.exec_module(vh)

GUIDE = ROOT / "docs" / "Fabric_IQ_Ontology_Workshop_Furusato_Participant_v2.7.0.docx"
D6_TABLE_CELL_MARKER = (
    "Ontology の定義そのものに変更を提案し、承認後に適用する編集側の体験"
)


def guide_text(path: pathlib.Path = GUIDE) -> str:
    """Use the production validator's document-order extraction."""
    with zipfile.ZipFile(path) as archive:
        tree = ElementTree.fromstring(archive.read("word/document.xml"))
    if not any(
        D6_TABLE_CELL_MARKER in _document_text(cell)
        for cell in tree.iter(f"{W}tc")
    ):
        raise AssertionError("the D.6 table-cell marker is not inside a w:tc element")
    return _document_text(tree)


def failed(report: Report) -> set[str]:
    return {finding.check for finding in report.findings if finding.level == "FAIL"}


def run(context, text: str) -> set[str]:
    report = Report(target="negative test")
    quality.check_preview_material_handling(context, text, report)
    return failed(report)


def drop(text: str, needle: str) -> str:
    """Remove every occurrence, so a contents-listing copy cannot mask the defect."""
    if needle not in text:
        raise AssertionError(f"the guide no longer contains {needle!r}; update the test")
    return text.replace(needle, "")


def inject_into_d6(text: str, sentence: str) -> str:
    marker = "D.6.3 実務での保護と公開情報の確認"
    index = text.rfind(marker)
    if index < 0:
        raise AssertionError("D.6.3 is missing; update the test")
    return text[:index] + sentence + text[index:]


def inject_into_d6_table(text: str, sentence: str) -> str:
    """Plant a defect in a D.6 table cell, not only in surrounding prose."""
    start = text.rfind("D.6 Ontology の編集を生成 AI に任せる場合の評価観点")
    end = text.find("付録 E　参考リンク", start)
    index = text.find(D6_TABLE_CELL_MARKER, start, end)
    if index < 0:
        raise AssertionError("the D.6 table cell is missing; update the test")
    index += len(D6_TABLE_CELL_MARKER)
    return text[:index] + sentence + text[index:]


#: (label, mutation, the check that must fail)
CASES = (
    (
        "appendix C.6 loses its heading",
        lambda text: drop(text, "C.6 ガバナンス・責任ある AI・コストの前提"),
        "content.appendixC6Coverage",
    ),
    (
        "the appendix D gate stops separating the exercises from D.6",
        lambda text: drop(
            text,
            "D.6 だけは実習ではありません。読んで評価の観点を持ち帰るための参考情報であり、実施する操作は含みません",
        ),
        "content.appendixD6Coverage",
    ),
    (
        "D.6 stops distinguishing evaluation from a product-capability promise",
        lambda text: drop(text, "特定の製品機能の提供や動作を保証するものではありません"),
        "content.appendixD6Coverage",
    ),
    (
        "D.6 stops identifying its conceptual diagram as distinct from product UI",
        lambda text: drop(
            text, "図は評価工程を示す概念図であり、製品の UI や機能一覧ではありません"
        ),
        "content.appendixD6Coverage",
    ),
    (
        "D.6 stops requiring current published feature conditions",
        lambda text: drop(text, "対象機能と条件が現行の公式ドキュメントに記載されていることを確認します"),
        "content.appendixD6Coverage",
    ),
    (
        "D.6 loses the eight public-verification topics",
        lambda text: drop(text, "公開ドキュメントで確認する 8 つの主題"),
        "content.appendixD6Coverage",
    ),
    (
        "D.6 reintroduces its material-provenance date",
        lambda text: inject_into_d6(text, "この節のもとになった資料は 2026 年 8 月 19 日に提供されたものです。"),
        "content.appendixD6AuthoringHistory",
    ),
    (
        "D.6 reintroduces the author's adoption narrative",
        lambda text: inject_into_d6(text, "読んだうえで採用しないという判断です。"),
        "content.appendixD6AuthoringHistory",
    ),
    (
        "D.6 reintroduces its material-provenance date in English",
        lambda text: inject_into_d6(text, "The material behind this section was supplied on 19 August 2026."),
        "content.appendixD6AuthoringHistory",
    ),
    (
        "a D.6 table describes the author's supplied material",
        lambda text: inject_into_d6_table(text, "資料に含まれていた情報の種類"),
        "content.appendixD6AuthoringHistory",
    ),
    (
        "C.6 stops saying it prints no retention day count",
        lambda text: drop(text, "本書は日数を書かない"),
        "content.appendixC6Coverage",
    ),
    (
        "D.6 loses the statement that it changes no Core verdict",
        lambda text: drop(
            text,
            "Core の流れ、ランタイムの選択、第 10 章と第 17 章の判定、付録 A、および数値契約のいずれにも影響しません",
        ),
        "content.appendixD6Coverage",
    ),
    (
        "D.6 starts naming a held-out test",
        lambda text: inject_into_d6(text, "この観点は T07 の判定に影響します。"),
        "content.appendixD6Isolation",
    ),
    (
        "D.6 starts quoting a Core verdict value",
        lambda text: inject_into_d6(text, "評価の結果は PASS として記録します。"),
        "content.appendixD6Isolation",
    ),
    (
        "a D.6 table starts naming a held-out test",
        lambda text: inject_into_d6_table(text, "この表は T07 の判定にも使います。"),
        "content.appendixD6Isolation",
    ),
    (
        "an unpublished product mode label appears",
        lambda text: text + "\n提案は Plan mode で確認してから適用します。",
        "content.noUnpublishedClaims",
    ),
    (
        "a confidentiality marking is copied in",
        lambda text: text + "\nMicrosoft Confidential",
        "content.noUnpublishedClaims",
    ),
    (
        "the supplied material is characterised as confidential in Japanese",
        lambda text: text + "\n提供された資料には機密の表示が含まれていました。",
        "content.noUnpublishedClaims",
    ),
    (
        "the supplied material is characterised as internal-only in Japanese",
        lambda text: text + "\nこの資料は社外秘であり、社内限りの取扱注意でした。",
        "content.noUnpublishedClaims",
    ),
    (
        "the supplied material is said to carry internal environment identifiers",
        lambda text: text + "\n画面には社内環境の識別子が写っていました。",
        "content.noUnpublishedClaims",
    ),
    (
        "the guide asserts the preview is free",
        lambda text: text + "\nこの機能はプレビュー中は無償で利用できます。",
        "content.noUnpublishedClaims",
    ),
    (
        "a conversation-retention duration is printed",
        lambda text: text + "\n対話の履歴は 30 日間保持されます。",
        "content.noUnpublishedClaims",
    ),
    (
        "an unpublished row ceiling is printed",
        lambda text: text + "\n1 回の取り込みは最大 1,000 行までが上限です。",
        "content.noUnpublishedClaims",
    ),
    (
        "the naming rule leaves the Core chapters",
        lambda text: drop(
            text,
            "1〜26 文字で、英数字・ハイフン・アンダースコアだけを使い、先頭と末尾は英数字にします",
        ),
        "content.namingRuleAndRefresh",
    ),
    (
        "the naming rule stops covering custom property names",
        lambda text: drop(text, "カスタム Property の名前"),
        "content.namingRuleScope",
    ),
    (
        "the rule is narrowed back to entity type names only",
        lambda text: text.replace(
            "Entity Type の名前とカスタム Property の名前には、同じ公式の規則があります",
            "Entity Type の名前には公式の規則があります",
        ),
        "content.namingRuleScope",
    ),
    (
        "the false documentation-gap claim comes back",
        lambda text: text + "\nProperty の名前については、公開ドキュメントに長さの上限が示されていない。",
        "content.namingRuleScope",
    ),
    (
        "the guide stops citing the two how-to pages the rule comes from",
        lambda text: drop(text, "付録 E の Create entity types と Bind data"),
        "content.namingRuleAndRefresh",
    ),
    (
        "the three names stop being called out as at the published ceiling",
        lambda text: drop(text, "がいずれも 26 文字で、現在公開されている上限ちょうどです"),
        "content.namingRuleAndRefresh",
    ),
    (
        "the manual graph-model refresh guidance is removed",
        lambda text: drop(text, "［Schedule］から［Refresh now］を選びます"),
        "content.namingRuleAndRefresh",
    ),
)

#: Mirror-side cases. These run against the shared claim scanner rather than the
#: rendered page, so they cover the English half of the bilingual deliverable.
MIRROR_CASES = (
    ("english preview-pricing claim", "This feature is free during preview.", True),
    ("english prohibition of the same claim", "Do not describe it as free during preview.", False),
    ("japanese prohibition of the same claim", "「プレビュー中は無償」と説明しない。", False),
    ("english EU Data Boundary claim", "The feature conforms to the EU Data Boundary.", True),
    ("english mode label", "Switch to Act mode to apply the change.", True),
    ("english consent claim", "Prompts are collected only with explicit consent.", True),
    ("english confidentiality characterisation", "The pages carried a confidentiality marking.", True),
    ("japanese confidentiality characterisation", "資料には機密の表示がありました。", True),
    ("japanese internal-only characterisation", "この資料は部外秘の取扱注意でした。", True),
    ("behaviour-only wording is allowed", "No wording from the supplied material is reproduced.", False),
)

RETENTION_CASES = (
    ("english conversation retention duration", "Conversations are retained for 30 days.", True),
    ("english retention without a duration", "Conversation retention differs by tenant setting.", False),
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--edition", default="", type=validate_edition)
    parser.add_argument(
        "--source", action="store_true",
        help="Validate the captured participant source without building or reading a Word artifact",
    )
    arguments = parser.parse_args()
    context = load_context(ROOT, document_edition=arguments.edition)
    if arguments.source:
        from furusato_docs.facts import compute_facts
        from furusato_docs.oox import StyleCarrier
        from furusato_docs.tests10 import build_tests
        from furusato_html.capture import capture_participant_guide
        from sync_i18n import _strings

        facts = compute_facts(context)
        capture = capture_participant_guide(context, facts, build_tests(context, facts), StyleCarrier.resolve(ROOT))
        if not any(
            D6_TABLE_CELL_MARKER == cell
            for node in capture.nodes if node.kind == "table"
            for row in node["rows"] for cell in row
        ):
            raise AssertionError("the D.6 table-cell marker is not inside a captured table")
        text = quality._plain("\n".join(s for node in capture.nodes for s, _ in _strings(node)))
    else:
        text = guide_text(ROOT / "docs" / deliverable_names(context.version, arguments.edition).participant)
    failures = 0
    checks = 0

    target_label = "participant source" if arguments.source else "shipped guide"
    clean = run(context, text)
    checks += 1
    if clean:
        print(f"  FAIL the {target_label} already fails: {sorted(clean)}")
        failures += 1
    else:
        print(f"  ok   the {target_label} passes every participant-reference gate")

    for label, mutate, expected in CASES:
        checks += 1
        observed = run(context, mutate(text))
        if expected in observed:
            print(f"  ok   detected: {label}")
        else:
            print(f"  FAIL undetected: {label} (expected {expected}, got {sorted(observed)})")
            failures += 1

    # A reference link that leaves the /en-us/ convention has to be caught too.
    checks += 1
    original = guide_content.REFERENCE_LINKS
    guide_content.REFERENCE_LINKS = original + (
        ("stale copilot page", "https://learn.microsoft.com/fabric/get-started/copilot-fabric-overview"),
    )
    try:
        observed = run(context, text)
    finally:
        guide_content.REFERENCE_LINKS = original
    if "content.referenceLinkHygiene" in observed:
        print("  ok   detected: a reference URL drops /en-us/ and points at a retired page")
    else:
        print(f"  FAIL undetected: stale reference URL (got {sorted(observed)})")
        failures += 1

    for label, sentence, should_fire in MIRROR_CASES:
        checks += 1
        hits = vh.unpublished_claim_hits(sentence)
        if bool(hits) == should_fire:
            print(f"  ok   {'detected' if should_fire else 'allowed'}: {label}")
        else:
            print(f"  FAIL {label}: hits={hits}")
            failures += 1

    for label, sentence, should_fire in RETENTION_CASES:
        checks += 1
        hits = vh.retention_with_duration(sentence)
        if bool(hits) == should_fire:
            print(f"  ok   {'detected' if should_fire else 'allowed'}: {label}")
        else:
            print(f"  FAIL {label}: hits={hits}")
            failures += 1

    print(f"\n{checks} participant-reference gate tests, {failures} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
