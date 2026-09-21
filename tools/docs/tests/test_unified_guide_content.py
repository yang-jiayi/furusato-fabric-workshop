"""Offline consumer tests; no Notebook, Agent, Office file or HTML is written."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import sys
import unittest
from dataclasses import asdict, replace
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools" / "docs"))
sys.path.insert(0, str(ROOT / "tools" / "html"))

from furusato_docs import quality  # noqa: E402
from furusato_docs.context import (  # noqa: E402
    UNIFIED_DOCUMENT_EDITION, _load_sealed_unified_assets, load_context,
    runtime_fingerprint, with_document_edition,
)
from furusato_docs.facts import compute_facts  # noqa: E402
from furusato_docs.guide_agent import chapter_16_data_agent  # noqa: E402
from furusato_docs.guide_unified import CI_HEADING, MIGRATION_HEADING, native_evidence  # noqa: E402
from furusato_docs.oox import StyleCarrier  # noqa: E402
from furusato_docs.parameters import build_parameter_rows  # noqa: E402
from furusato_docs.tests10 import build_tests  # noqa: E402
from furusato_docs.validators import Report  # noqa: E402
from furusato_html.capture import CaptureBuilder, capture_participant_guide  # noqa: E402
from furusato_html import mirror as mirrors  # noqa: E402
from furusato_html.model import build_document  # noqa: E402
from sync_i18n import _strings, collect  # noqa: E402


def build_local_assets(base):
    """Exercise the real pure profile builder, without requiring a resealed Notebook."""
    bundle = ROOT / "workshop" / "v2.7.0" / "provisioning" / "bundle" / "ai-reference"

    def text(relative):
        return (bundle / relative).read_bytes().decode("utf-8")

    contract = json.loads(text("contract.json"))
    stage = copy.deepcopy(base.agent_stage_config)
    stage["aiInstructions"] = text("global-instructions.txt")
    reference = {
        "contract": contract,
        "globalProfile": json.loads(text("global-profile.json")),
        "stageConfig": stage,
        "sources": json.loads(text("source-metadata.json")),
        "sqlDdl": tuple((name, text("sql/" + name)) for name in contract["sqlDdlOrder"]),
        "kqlFunctions": {name: text("kql/" + name + ".kql") for name in contract["kqlFunctions"]},
        "moduleSources": {name: text("modules/" + name + ".py") for name in contract["modules"]},
    }
    path = ROOT / "tools" / "provisioning" / "unified_agent.py"
    spec = importlib.util.spec_from_file_location("_unified_docs_test_builder", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.build_unified_assets(
        reference, base.agent_sources["ontology"], profile_files=module.load_profile_files(ROOT)
    )


def make_context():
    base = load_context(ROOT)
    assets = build_local_assets(base)
    context = with_document_edition(base, UNIFIED_DOCUMENT_EDITION, unified_assets=assets)
    # This is a parameter-consumer fixture, not a claim that Notebook 04 is sealed.
    # The missing-parameter test below proves the production guard still rejects it.
    notebooks = dict(context.notebooks)
    notebook = notebooks["Notebook_04"]
    notebooks["Notebook_04"] = replace(
        notebook, parameters={**notebook.parameters, "ENABLE_UNIFIED_DATA_AGENT": False}
    )
    return base, replace(context, notebooks=notebooks), assets


def capture_text(nodes):
    return "\n".join(text for node in nodes for text, _role in _strings(node))


def sealed_fixture(base, assets):
    """The parent's bundle shape, held in memory; no release files are created."""
    bundle = ROOT / "workshop" / "v2.7.0" / "provisioning" / "bundle"
    core_path = next(
        path for path in (bundle / "data-agent" / "Files" / "Config" / "published").glob("*/datasource.json")
        if json.loads(path.read_bytes()).get("type") == "ontology"
    )
    encode = lambda value: (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    files = {
        "unified-agent/profile.json": encode({
            name: assets[name] for name in ("stageConfig", "sources", "globalProfile", "publicationDescription")
        }),
        "unified-agent/modules/unified_agent.py": (ROOT / "tools" / "provisioning" / "unified_agent.py").read_bytes(),
        "unified-agent/inputs/manifest.json": encode(assets["profileManifest"]),
        "unified-agent/inputs/global-instructions.txt": assets["stageConfig"]["aiInstructions"].encode("utf-8"),
        "unified-agent/inputs/kusto-fewshots.json": encode(assets["sources"]["kusto"]["fewShots"]),
    }
    for kind, stem in (("lakehouse_tables", "lakehouse"), ("kusto", "kusto")):
        files[f"unified-agent/inputs/{stem}-instructions.txt"] = assets["sources"][kind]["instructions"].encode("utf-8")
    contract = {
        "schemaVersion": "furusato-unified-agent-runtime/v1",
        "teachingOntologyShape": [10, 72, 1, 15],
        "createsAIPath": False,
        "codeInterpreterEnabled": True,
        "acceptanceClaimed": False,
        "agentNameTemplate": base.names["dataAgent"],
        "referenceContractSha256": hashlib.sha256((bundle / "ai-reference" / "contract.json").read_bytes()).hexdigest(),
        "coreOntologySourcePath": core_path.relative_to(bundle).as_posix(),
        "coreOntologySourceSha256": hashlib.sha256(core_path.read_bytes()).hexdigest(),
        "files": {name: hashlib.sha256(raw).hexdigest() for name, raw in files.items()},
    }
    files["unified-agent/contract.json"] = encode(contract)
    return {bundle / name: raw for name, raw in files.items()}


class UnifiedGuideContentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base, cls.context, cls.assets = make_context()
        cls.facts = compute_facts(cls.context)
        cls.tests = build_tests(cls.context, cls.facts)
        carrier = StyleCarrier.resolve(ROOT)
        cls.carrier = carrier
        cls.captures = {
            public: capture_participant_guide(
                cls.context, cls.facts, cls.tests, carrier, public_documents_only=public
            )
            for public in (False, True)
        }
        cls.text = capture_text(cls.captures[False].nodes)

    def test_profile_is_explicit_and_does_not_overwrite_core_context(self):
        self.assertEqual(self.context.version, "2.7.0")
        self.assertEqual(self.context.document_edition, UNIFIED_DOCUMENT_EDITION)
        self.assertEqual(self.context.agent_sources, self.base.agent_sources)
        self.assertEqual(self.context.agent_instructions, self.base.agent_instructions)
        self.assertFalse(self.context.agent_stage_config["experimental"]["codeInterpreterEnabled"])
        self.assertTrue(self.context.guide_agent_stage_config["experimental"]["codeInterpreterEnabled"])
        self.assertNotEqual(self.context.guide_agent_instructions, self.base.agent_instructions)
        self.assertLess(len(self.context.guide_agent_instructions), 15_000)

    def test_obsolete_instruction_captures_are_not_unified_configuration_evidence(self):
        captions = (
            "［Agent instructions］画面。ここにグローバル指示の全文を貼り付ける。",
            "公開完了後。version menu を Published に切り替え",
        )
        legacy = capture_participant_guide(self.base, self.facts, self.tests, self.carrier)
        legacy_text = capture_text(legacy.nodes)
        for caption in captions:
            with self.subTest(caption=caption):
                self.assertIn(caption, legacy_text)
                for capture in self.captures.values():
                    self.assertNotIn(caption, capture_text(capture.nodes))

    def test_real_ui_illustration_preserves_provenance_and_omits_obsolete_instructions(self):
        from furusato_docs.capture_policy import capture_problems

        registry = json.loads((ROOT / "tools" / "docs" / "assets" / "unified-ui-captures.json").read_text("utf-8"))
        tags = {"16-30", "18-30", "17-40"}
        self.assertEqual(set(registry["captures"]), tags)
        self.assertFalse(registry["pixelsEdited"])
        self.assertFalse(registry["usage"]["currentConfigurationCaptured"])
        self.assertEqual(registry["usage"]["activeTags"], ["17-40"])
        carrier_hashes = {}
        for tag in tags:
            entry = registry["captures"][tag]
            self.assertEqual(entry["sha256"], entry["originalSha256"])
            carrier_hashes[tag] = hashlib.sha256(self.carrier.screenshot(tag).getvalue()).hexdigest()
            self.assertEqual(carrier_hashes[tag], entry["sha256"])
        for capture in self.captures.values():
            used = {node["source_key"] for node in capture.nodes
                    if node.kind == "figure" and node["source_kind"] == "screenshot"}
            self.assertIn("17-40", used)
            self.assertFalse({"13-12", "13-33", "16-30", "18-30"} & used)
            self.assertEqual(capture_problems(
                registry, self.context.guide_agent_instructions, carrier_hashes,
                {carrier_hashes[tag] for tag in used if tag in carrier_hashes},
                code_interpreter_enabled=True, preview_enabled=True,
            ), [])
        for tag in ("13-12", "13-33"):
            self.assertTrue(self.carrier.screenshot(tag).getvalue())

    def test_missing_or_tampered_profile_never_falls_back(self):
        with self.assertRaisesRegex(ValueError, "not a fallback"):
            with_document_edition(self.base, UNIFIED_DOCUMENT_EDITION)
        with self.assertRaisesRegex(ValueError, "require the unified"):
            with_document_edition(self.base, "", unified_assets=self.assets)
        broken = copy.deepcopy(self.assets)
        broken["stageConfig"]["experimental"]["codeInterpreterEnabled"] = False
        with self.assertRaises(ValueError):
            with_document_edition(self.base, UNIFIED_DOCUMENT_EDITION, unified_assets=broken)

    def test_original_questions_conditions_and_facts_are_unchanged(self):
        old_tests = build_tests(self.base, compute_facts(self.base))
        self.assertEqual(len(self.tests), 10)
        self.assertEqual([asdict(t) for t in self.tests], [asdict(t) for t in old_tests])
        self.assertEqual(self.context.expected, self.base.expected)
        self.assertEqual(self.context.expected_increment, self.base.expected_increment)
        self.assertIn("選択した分岐に適用されない条件だけを NA", self.text)
        self.assertIn("厳密な 10/10 を反復", self.text)
        self.assertIn("再実行を未見評価と呼びません", self.text)

    def test_full_model_and_physical_counts_are_not_path_profile_counts(self):
        self.assertEqual(self.context.guide_profile.contract["expectedOntologyContract"], self.base.ontology_contract)
        self.assertEqual(self.context.ontology_contract["staticProperties"], 72)
        self.assertEqual(self.context.ontology_contract["timeseriesProperties"], 1)
        self.assertEqual(len(self.context.expected["outputTableCounts"]), 11)
        self.assertEqual(len(self.context.guide_profile.sources), 3)
        self.assertIn("14（11 テーブル + 1 view + 2 関数）", self.text)
        self.assertIn("4（1 MV + 3 関数）", self.text)
        self.assertNotIn("21 static Property", self.text)

    def test_all_profile_instructions_are_reproduced_verbatim(self):
        code = [node["text"] for node in self.captures[False].nodes if node.kind == "code"]
        self.assertIn(self.context.guide_agent_instructions.rstrip("\r\n"), code)
        self.assertNotIn(self.base.agent_instructions.rstrip("\r\n"), code)
        for kind in ("lakehouse_tables", "kusto", "ontology"):
            description, instructions = self.context.guide_source_text(kind)
            self.assertIn(description, self.text)
            if kind == "ontology":
                self.assertEqual(instructions, "")
                self.assertIsNone(self.context.guide_profile.sources[kind]["instructions"])
                self.assertIn("Ontology ソース指示は null のまま保持", self.text)
            else:
                self.assertIn(instructions.strip(), code)

    def test_kql_examples_match_the_profile_without_changing_original_sql_examples(self):
        shots = self.context.guide_kql_fewshots
        self.assertEqual(len(shots), 3)
        self.assertEqual(shots, self.assets["sources"]["kusto"]["fewShots"]["fewShots"])
        self.assertEqual(self.base.guide_kql_fewshots, [])
        self.assertEqual(self.context.agent_fewshots, self.base.agent_fewshots)
        code = [node["text"] for node in self.captures[False].nodes if node.kind == "code"]
        for shot in shots:
            with self.subTest(question=shot["question"]):
                self.assertIn(shot["question"], self.text)
                self.assertIn(shot["query"].strip(), code)
                self.assertIn("ISO-8601", shot["question"])
                for original in self.tests:
                    self.assertNotIn(original.question, shot["question"])
        self.assertNotIn("本教材では Eventhouse の例クエリは別途登録せず", self.text)

    def test_sources_are_prepared_before_discovery_and_agent_selection(self):
        self.assertLess(self.text.index("001_create_schema.sql"), self.text.index("16.2.2 主 Agent"))
        self.assertLess(self.text.index("060_donation_trace_by_id.sql"), self.text.index("16.2.2 主 Agent"))
        for name in ("AgentRawObservationTotals", "AgentFileRunSummary", "AgentMunicipalityLeaders"):
            self.assertIn(name + ".kql", self.text)
        self.assertIn("共有スクリプトの ai-reference というフォルダー名は資産の由来", self.text)
        self.assertIn("agent_ref が存在すると仮定して", self.text)

    def test_no_ontology_instruction_box_can_be_rendered(self):
        languages = [node["language"] for node in self.captures[False].nodes if node.kind == "code"]
        self.assertNotIn("Ontology のソース指示", languages)
        for value in ("unsupported Ontology instructions", "", "missing"):
            sources = copy.deepcopy(self.context.guide_profile.sources)
            if value == "missing":
                del sources["ontology"]["instructions"]
            else:
                sources["ontology"]["instructions"] = value
            profile = replace(self.context.guide_profile, sources=sources)
            builder = CaptureBuilder(self.carrier)
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "must remain null"):
                    chapter_16_data_agent(builder, replace(self.context, unified_profile=profile))
                self.assertEqual(builder.nodes, [])

    def test_same_primary_and_staged_migration_are_not_blind_overwrites(self):
        for marker in (
            "既に完全一致する場合だけ", "Published は検証が完了するまで旧版を保持",
            "旧 Agent 2 件だけを実 ID", "過去に保持した Eventhouse",
            "別名 Agent を追加して回避しません", "AIPath は作りません",
            "両方 True は禁止", "自動 resume・自動 rollback とみなさず",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, self.text)

    def test_runtime_parameter_default_and_guide_setup_are_distinct(self):
        rows = {row[0]: row for row in build_parameter_rows(self.context, "Notebook_04")}
        self.assertEqual(rows["ENABLE_UNIFIED_DATA_AGENT"][2], "False")
        self.assertIn("preview 前に True", rows["ENABLE_UNIFIED_DATA_AGENT"][3])
        self.assertIn("False のまま", rows["ENABLE_AI_REFERENCE_ARCHITECTURE"][3])
        self.assertIn("enable_unified_data_agent", rows["ENABLE_UNIFIED_DATA_AGENT"][4])

    def test_missing_parameter_is_a_real_dependency_failure(self):
        notebooks = dict(self.context.notebooks)
        params = dict(notebooks["Notebook_04"].parameters)
        params.pop("ENABLE_UNIFIED_DATA_AGENT")
        notebooks["Notebook_04"] = replace(notebooks["Notebook_04"], parameters=params)
        with self.assertRaisesRegex(ValueError, "requires Notebook 04"):
            build_parameter_rows(replace(self.context, notebooks=notebooks), "Notebook_04")
        legacy = replace(self.base, notebooks=notebooks)
        self.assertEqual(len(build_parameter_rows(legacy, "Notebook_04")), 18)
        self.assertEqual(sum(len(n.parameters) for n in legacy.notebooks.values()), 50)
        params["UNRECOGNIZED_FLAG"] = True
        with self.assertRaisesRegex(ValueError, "undocumented"):
            build_parameter_rows(replace(self.base, notebooks=notebooks), "Notebook_04")

    def test_chapter_and_appendix_structure_is_preserved(self):
        for public, capture in self.captures.items():
            with self.subTest(public=public):
                headings = [n["text"] for n in capture.nodes if n.kind == "heading" and n["level"] == 1]
                self.assertEqual(len(headings), 24)
                self.assertEqual([s.split(".")[0] for s in headings[:19]], [str(n) for n in range(1, 20)])
                self.assertTrue(all(h.startswith("付録 " + letter) for letter, h in zip("ABCDE", headings[19:])))

    def test_ci_is_an_actual_separate_exercise_not_a_graph_substitute(self):
        self.assertLess(self.text.index("17.10 T10"), self.text.index(CI_HEADING))
        for marker in (
            "SQL の全母集団", "KQL の file/run 内訳", "実行した Python と実際の入力",
            "stdout / stderr", "report_specs", "実際に生成された CSV / 画像ファイル",
            "bounded な結果はその範囲", "GQL の count/path を Python へ置き換えていない",
            "失敗・欠落を 0 として埋めません", "全件を取得できない場合は停止",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, self.text)

    def test_same_run_native_identity_and_missing_evidence_escalation(self):
        for marker in (
            "UI Export", "実際の同一 run", "conversation ID", "request / activity ID",
            "別会話の export", "実行証跡を取得できない場合",
            "別の会話・別の照会や回答本文だけで不足分を補いません",
            "native 証跡が揃わない範囲は保留",
            "T10 ではプラットフォームのブロックが残る可能性",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, self.text)
        self.assertNotIn("SDK の 403", self.text)
        self.assertNotIn("この版は ISO UTC の出力", self.text)

    def test_core_names_the_current_course_not_a_legacy_agent_profile(self):
        self.assertIn("本文の Core はこの版の標準手順", self.text)
        self.assertIn("旧プロファイルへ切り替える指示ではありません", self.text)
        self.assertIn("設定の完了と応答品質の確認は別", self.text)
        self.assertTrue(self.context.guide_agent_stage_config["experimental"]["codeInterpreterEnabled"])
        self.assertFalse(self.context.agent_stage_config["experimental"]["codeInterpreterEnabled"])

    def test_daily_distribution_does_not_deny_the_packaged_duplicate_spike(self):
        paragraph = next(
            node["text"] for node in self.captures[False].nodes
            if node.kind == "body" and node["text"].startswith("raw 15,000 行の UTC 日次内訳")
        )
        calendar = self.facts.observation.calendar
        self.assertEqual(calendar.duplicate_day, "2026-08-11")
        self.assertEqual(calendar.duplicate_extra_rows_on_day, 100)
        self.assertEqual(calendar.duplicate_day_raw_rows - calendar.duplicate_day_dedup_rows, 100)
        self.assertIn(f"{calendar.duplicate_day} には追加重複 100 行が集中", paragraph)
        self.assertIn("欠測日はありません", paragraph)
        self.assertNotIn("特定の日に偏ったり", paragraph)

    def test_global_guidance_preserves_its_concrete_owner_and_relationship_rules(self):
        section = self.text.split("16.1 設定の 3 層と責務", 1)[1].split(
            "16.2 Data Agent と共有ソースを確認する", 1
        )[0]
        self.assertNotIn("個々のテーブル名・列名・クエリの書き方", section)
        self.assertIn("テーブル・関数・列名と、Ontology の関係名・方向も含まれます", section)
        self.assertIn("配布 GLOBAL を削ったり、指示を別の層へ移したりしません", section)
        for concrete_rule in ("agent_ref.DonationTraceById", "AgentRawObservationTotals", "MunicipalityInPrefecture"):
            with self.subTest(rule=concrete_rule):
                self.assertIn(concrete_rule, self.context.guide_agent_instructions)

    def test_distinct_entry_tables_remain_a_workshop_rule_not_a_product_restriction(self):
        section = self.text.split("16.6.1 例クエリの品質ゲート", 1)[1].split(
            "16.7 ランタイムと Core の既定設定", 1
        )[0]
        self.assertIn("入口のテーブルは重複させない", section)
        self.assertIn("この教材の 3 例を区別しやすくするための規則", section)
        self.assertIn("製品制約ではありません", section)
        self.assertIn("同じ意図に対して異なる指標・粒度・絞り込み", section)
        self.assertIn("配布された例をそのまま使い、追加・変更しません", section)
        self.assertNotIn("どちらが選ばれたかで結果が変わり", section)

    def test_hydration_requires_native_source_evidence_not_one_ui_step(self):
        table = next(
            node for node in self.captures[False].nodes
            if node.kind == "table" and node["caption"] == "Ontology time-series hydration の機能ゲート"
        )
        source_gate = dict(table["rows"])["使用ソース"]
        self.assertIn("Ontology だけ", source_gate)
        self.assertIn("全 step と実 query・返却結果", source_gate)
        self.assertIn("step 数は固定しない", source_gate)
        self.assertNotIn("1 step", source_gate)
        self.assertIn("Eventhouse KQL owns", self.context.guide_agent_instructions)
        self.assertIn("同じ設定で必ず実行されるとは保証しません", self.text)
        self.assertIn("掲載画面は操作例であり、現在の同一 run の成功証跡ではありません", self.text)
        self.assertIn("KQL へのルーティングや拒否だけでバインディング破損と断定せず", self.text)
        self.assertIn("機能確認をブロックとして記録します", self.text)
        self.assertIn("GLOBAL・ソース選択を変更したり、別 Agent・Python で代用したりせず", self.text)
        self.assertIn("Eventhouse を直接使った場合は held-out 10 問へ進みません", self.text)

    def test_deduplication_limit_applies_to_agent_selection_not_the_raw_queryset(self):
        section = self.text.split("17.0 構成別の query capability pretest", 1)[1].split(
            "17.1 T01", 1
        )[0]
        self.assertNotIn("重複を除いた値はどのソースからも証明できません", section)
        self.assertIn("Agent で選択したソースには EventID がない", section)
        self.assertIn("第 13 章の KQL Queryset による raw データの検証とは参照範囲が異なります", section)
        selected = self.context.guide_profile.sources["kusto"]["elements"]
        self.assertFalse(any(entry["path"][-1][1] in {"DonationEvents", "EventID"} for entry in selected))
        self.assertIn("EventID", self.context.kql_setup)

    def test_semantic_cleanup_keeps_all_held_out_content_and_both_ci_prompts_byte_exact(self):
        original_tests_sha256 = "56a951dee770083a9d2d04d1019084bd63c62dc7183362d47dab048950baa366"
        encoded = json.dumps([asdict(test) for test in self.tests], ensure_ascii=False, sort_keys=True).encode("utf-8")
        self.assertEqual(hashlib.sha256(encoded).hexdigest(), original_tests_sha256)
        expected_prompts = {
            "CI 演習 1：SQL の全母集団から分布を描く":
                "5aeba5aeea794ad02cd7c93555ed70490ccf6e2f6e3a28562730441a88731d85",
            "CI 演習 2：KQL の file/run 内訳を可視化する":
                "294d6c4839223962378456c6ccf11e56241f4bb33e4e0181c7a41d5edd97510f",
        }
        for public, capture in self.captures.items():
            with self.subTest(public=public):
                questions = [
                    node["text"] for node in capture.nodes
                    if node.kind == "callout" and node.get("title") == "質問（そのまま貼り付ける）"
                ]
                self.assertEqual(questions, [test.question for test in self.tests])
                prompts = {
                    node["title"]: hashlib.sha256(node["text"].encode("utf-8")).hexdigest()
                    for node in capture.nodes
                    if node.kind == "callout" and node.get("title") in expected_prompts
                }
                self.assertEqual(prompts, expected_prompts)

    def test_unified_and_original_practice_validators_both_pass(self):
        for public, capture in self.captures.items():
            report = Report(target="unified in-memory content")
            text = capture_text(capture.nodes)
            quality.check_guide_content(quality._plain(text), self.context, self.facts, report)
            quality.check_unified_guide(self.context, text, report)
            quality.check_data_agent_practice(self.context, text, report)
            with self.subTest(public=public):
                self.assertTrue(report.passed, [(f.check, f.message) for f in report.failures])

    def test_negative_unified_guards_are_not_vacuous(self):
        for marker, check in (
            ("72 static Property", "content.unifiedProfile"),
            ("ENABLE_UNIFIED_DATA_AGENT=True", "content.unifiedMigration"),
            ("実際の同一 run", "content.unifiedNativeEvidence"),
            ("実行した Python と実際の入力", "content.unifiedNativeEvidence"),
            ("kusto-fewshots.json", "content.unifiedKqlExamples"),
        ):
            report = Report(target="negative unified fixture")
            quality.check_unified_guide(self.context, self.text.replace(marker, ""), report)
            with self.subTest(marker=marker):
                self.assertIn(check, {f.check for f in report.failures})
        report = Report(target="legacy route injection")
        quality.check_unified_guide(
            self.context, self.text + "\nAIPath と Data Agent を構築します", report
        )
        self.assertIn("content.unifiedNoLegacyRouting", {f.check for f in report.failures})

    def test_practice_boundary_still_rejects_runtime_and_sdk_fragments(self):
        for marker, injected, check in (
            ("16.8 指示で守る境界と、応答時間の変数", "APPLY_CHANGES", "content.practiceSectionIsolation"),
            (CI_HEADING, "SDK", "content.practiceSectionClaims"),
        ):
            report = Report(target="practice injection")
            quality.check_data_agent_practice(
                self.context, self.text.replace(marker, marker + "\n" + injected), report
            )
            with self.subTest(marker=marker):
                self.assertIn(check, {f.check for f in report.failures})
        self.assertIn(MIGRATION_HEADING, self.text)

    def test_sealed_loader_checks_real_inputs_without_requiring_aipath(self):
        files = sealed_fixture(self.base, self.assets)
        original = Path.read_bytes

        def read(path):
            if path in files:
                return files[path]
            if path.name == "ontology-template.json":
                raise AssertionError("The unified guide must not depend on an AIPath definition.")
            return original(path)

        with patch.object(Path, "read_bytes", read):
            self.assertEqual(_load_sealed_unified_assets(self.base), self.assets)

    def test_sealed_loader_rejects_tampered_global_and_missing_bundle(self):
        files = sealed_fixture(self.base, self.assets)
        original = Path.read_bytes
        global_path = next(path for path in files if path.name == "global-instructions.txt")
        files[global_path] += b"tampered\n"
        with patch.object(Path, "read_bytes", lambda path: files[path] if path in files else original(path)):
            with self.assertRaisesRegex(ValueError, "asset hash mismatch"):
                _load_sealed_unified_assets(self.base)

        def missing(path):
            if path.name == "contract.json" and path.parent.name == "unified-agent":
                raise FileNotFoundError(path)
            return original(path)

        with patch.object(Path, "read_bytes", missing):
            with self.assertRaisesRegex(ValueError, "parent reseal first"):
                load_context(ROOT, document_edition=UNIFIED_DOCUMENT_EDITION)

    def test_profile_identity_is_in_document_fingerprint(self):
        old = runtime_fingerprint(self.base)
        new = runtime_fingerprint(self.context)
        self.assertEqual(old["files"], new["files"])
        self.assertNotEqual(old["combinedSha256"], new["combinedSha256"])
        self.assertEqual(new["guideProfileSha256"], self.assets["contract"]["sha256"])
        self.assertEqual(new["documentEdition"], UNIFIED_DOCUMENT_EDITION)

    def test_both_unified_mirrors_are_complete_with_no_unused_entries(self):
        for public in (False, True):
            delta = collect(ROOT, context=self.context, public_documents_only=public)
            with self.subTest(public=public):
                self.assertEqual(delta["missing"], [])
                self.assertEqual(delta["unused"], [])
                self.assertEqual(delta["suspicious"], [])
                mirror = mirrors.load_mirror(context=self.context, public_documents_only=public)
                build_document(self.captures[public].nodes, mirror)
                self.assertFalse(mirror.unused())

    def test_legacy_mirror_also_documents_the_new_default_false_flag(self):
        legacy = replace(self.base, notebooks=self.context.notebooks)
        for public in (False, True):
            delta = collect(ROOT, context=legacy, public_documents_only=public)
            with self.subTest(public=public):
                self.assertEqual(delta["missing"], [])
                self.assertEqual(delta["unused"], [])
                self.assertEqual(delta["suspicious"], [])

    def test_mirror_templates_derive_hashes_not_temporary_profile_constants(self):
        mirror = mirrors.load_mirror(context=self.context)
        ja = next(text for text in mirror.entries if text.startswith("画面へ貼り付ける本文"))
        english = mirror.get(ja)
        instructions = self.context.guide_agent_instructions
        self.assertIn(hashlib.sha256(instructions.encode("utf-8")).hexdigest(), english)
        self.assertIn(hashlib.sha256(instructions.rstrip("\r\n").encode("utf-8")).hexdigest(), english)
        self.assertIn(f"{len(instructions):,}", english)

    def test_strict_mirror_does_not_ignore_unknown_or_unused_content(self):
        mirror = mirrors.load_mirror(context=self.context)
        with self.assertRaises(mirrors.TranslationError):
            mirror.get("翻訳のない新しい本文")
        mirror.entries["未使用の合成テスト項目"] = "Unused synthetic test entry"
        build_document(self.captures[False].nodes, mirror)
        self.assertEqual(mirror.unused(), ["未使用の合成テスト項目"])
        merge = mirrors._merge

        def ambiguous(paths):
            entries = merge(paths)
            entries["16.2 Data Agent を作成してソースを追加する（合成テスト）"] = "Synthetic ambiguous key"
            return entries

        with patch.object(mirrors, "_merge", ambiguous):
            with self.assertRaisesRegex(mirrors.TranslationError, "exactly one legacy key"):
                mirrors.load_mirror(context=self.context)

    def test_unified_html_chrome_does_not_advertise_the_old_three_agent_path(self):
        ui = mirrors.load_ui_strings(context=self.context, public_documents_only=True)
        self.assertIn("統合モードの Notebook 04", ui["howto.scope.core"]["ja"])
        self.assertIn("not use the legacy separate Agents", ui["howto.scope.optional"]["en"])
        self.assertIn("unified-20260914", ui["meta.description"]["en"])
        self.assertNotIn("Code Interpreter are Optional", ui["howto.scope.optional"]["en"])


class ScreenshotProvenanceContentTests(unittest.TestCase):
    def test_screenshot_evidence_requires_actual_fabric_ui(self):
        builder = CaptureBuilder(None)
        native_evidence(builder)
        text = capture_text(builder.nodes)
        for marker in (
            "証跡用の画面写真",
            "対象 Agent・質問・実行を記録",
            "実際の Fabric Web UI を操作して取得",
            "画面を HTML で再構成",
            "画像内のラベルを差し替え",
            "保存ログの表示を UI の実行証跡として",
            "CI の図ファイルは分析成果物として区別",
            "配布ガイドの画像や自分の画面写真だけでは",
            "元の native 証跡も保持",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, text)
        for authoring_detail in ("Word / HTML に載せる", "再撮影", "全画像の更新"):
            self.assertNotIn(authoring_detail, text)
        source = next(
            node["text"] for node in builder.nodes
            if node.kind == "body" and node["text"].startswith("証跡用の画面写真")
        )
        overlay = json.loads(
            (ROOT / "tools" / "html" / "furusato_html" / "i18n" / "unified-documents.json").read_text("utf-8")
        )
        english = overlay["add"][source]
        self.assertIn("recording the Agent, question and run", english)
        self.assertIn("Neither distributed-guide images nor your own screenshots alone prove", english)
        self.assertIn("operating the actual Fabric Web UI", english)
        self.assertIn("Do not reconstruct screens in HTML", english)
        self.assertIn("rendered saved logs", english)


if __name__ == "__main__":
    unittest.main()
