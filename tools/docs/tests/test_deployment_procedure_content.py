"""Read-only regression checks for folder-scoped deployment procedures."""

from __future__ import annotations

import json
import pathlib
import re
import sys
import unittest

from docx import Document
from docx.oxml.ns import qn

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools" / "docs"))
sys.path.insert(0, str(ROOT / "tools" / "html"))

from furusato_docs import quality, validation_doc  # noqa: E402
from furusato_docs.context import load_context  # noqa: E402
from furusato_docs.docx_kit import DocumentBuilder  # noqa: E402
from furusato_docs.facts import compute_facts  # noqa: E402
from furusato_docs.oox import StyleCarrier  # noqa: E402
from furusato_docs.parameters import build_parameter_rows, format_default  # noqa: E402
from furusato_docs.tests10 import build_tests  # noqa: E402
from furusato_html.capture import CaptureBuilder, capture_participant_guide  # noqa: E402
from furusato_html.mirror import load_mirror  # noqa: E402
from sync_i18n import _strings, collect  # noqa: E402


def captured_text(builder: CaptureBuilder) -> str:
    return "\n".join(text for node in builder.nodes for text, _role in _strings(node))


class DeploymentProcedureContentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.context = load_context(ROOT)
        facts = compute_facts(cls.context)
        tests = build_tests(cls.context, facts)
        carrier = StyleCarrier.resolve(ROOT)
        guide = capture_participant_guide(cls.context, facts, tests, carrier)
        cls.guide = captured_text(guide)
        cls.guide_nodes = guide.nodes
        cls.tests = tests
        record = CaptureBuilder(carrier)
        validation_doc._how_to_use(record, cls.context, tests)
        validation_doc._summary_sheet(record, tests)
        validation_doc._summary_notes(record, cls.context, tests)
        cls.record = captured_text(record)

    def test_alternative_provisioning_is_not_a_sequential_upgrade(self) -> None:
        self.assertIn("同じ成果物に 01 → 02 → 03 → 04 → 05 を順番に適用する手順ではありません", self.guide)
        self.assertIn("Notebook 05 は既存データへの分析拡張", self.guide)
        self.assertIn("no-op の確認は、新規作成の実証とは区別して記録", self.guide)
        self.assertNotIn("同じ結果に別経路で到達するための Optional", self.guide)

    def test_folder_scope_and_runtime_identity_are_explicit(self) -> None:
        for marker in (
            "5.2.1 既存 Workspace の指定 Folder",
            "Folder は Workspace の権限を継承",
            "Notebook 02 と単独の Notebook 03",
            "Workspace 全体から完全一致で解決",
            "TARGET_FOLDER_NAME は作成先だけの指定",
            "作成後の item ID、親 item ID、最終 Folder",
            "安全ガードを外しません",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, self.guide)
        self.assertNotIn("同名 Ontology が対象 Folder に既にあると作成せず停止", self.guide)

    def test_deployment_target_is_resolved_from_the_participant_environment(self) -> None:
        for marker in (
            "実行先の Workspace / Folder は、配布物の参照例から推測せず",
            "自分に割り当てられた場所を確認",
            "現在選んだ Workspace の実際の表示名",
            "`subfolderId` が数値の場合は REST の `folderId`（GUID）として使わず",
            "一意に確定できるまで書き込まず",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, self.guide)
        self.assertNotIn("workspaceReference", self.context.workspace_contract)
        self.assertNotIn("`workspaceReference`", self.guide)

    def test_complete_flags_precede_final_provisioning_preview(self) -> None:
        flags = (
            "APPLY_CHANGES=False のままEXECUTE_NOTEBOOK_01・CREATE_PIPELINE・"
            "REFRESH_GRAPH・CREATE_DATA_AGENT・CREATE_REFLEX をすべて True"
        )
        preview = "この最終構成で preview を実行"
        approval = "CONFIRMED_PLAN_SHA256 に直前の値を貼り"
        self.assertLess(self.guide.index(flags), self.guide.index(preview))
        self.assertLess(self.guide.index(preview), self.guide.index(approval))
        self.assertIn("最終 preview の前に True", self.guide)

    def test_first_build_timeout_preserves_existing_job_identity(self) -> None:
        for marker in (
            "初回構築では preview 前に 2700 を指定する",
            "Notebook 01 の子ジョブ、SQL 同期、Graph 更新",
            "初回構築は 15 分を超える場合がある",
            "タイムアウトしてもジョブは自動キャンセルされない",
            "既存ジョブ ID の状態を確認",
            "実行中のジョブを再送しない",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, self.guide)

    def test_mcp_observability_is_not_confused_with_factual_accuracy(self) -> None:
        for marker in (
            "MCP の回答比較と完全な native 受入を分ける",
            "クライアント側の RPC ID を実行証跡の代わりにしません",
            "native 証跡ゲートの未達を分けて報告",
            "事実回答の正答率が 0% という意味ではありません",
            "元の 10 問／84 要件や受入ゲートは緩めず",
            "完全な品質受入は保留",
            "見えていない query の欠陥を推測して修正しません",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, self.guide)
        self.assertGreater(
            self.guide.index("MCP の回答比較と完全な native 受入を分ける"),
            self.guide.index("D.4 User data functions と Code Interpreter"),
        )
        self.assertLess(
            self.guide.index("MCP の回答比較と完全な native 受入を分ける"),
            self.guide.index("D.5 Variable Library"),
        )

    def test_practice_sections_preserve_the_core_optional_boundary(self) -> None:
        report = quality.Report(target="captured practice sections")
        quality.check_data_agent_practice(self.context, self.guide, report)
        self.assertTrue(
            report.passed,
            [(finding.check, finding.message) for finding in report.failures],
        )

    def test_reference_rules_require_real_completion_and_narrow_safe_alternatives(self) -> None:
        for marker in (
            "照合完了の宣言と、安全な代替の範囲",
            "今回の同一 ID に対する 3 ソースの query がすべて成功",
            "Ontology の実 instance path を得た場合だけ宣言",
            "未使用・失敗・必須項目の欠落があれば未完了",
            "クロスソース照合で必要な Ontology 処理を止めません",
            "Static 2025 UTC と明示した寄付額と順位だけに限定",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, self.guide)

    def test_staged_files_preserve_trigger_first_ingestion(self) -> None:
        for marker in (
            "`Files/_provisioning/furusato/<PID>/increment` に待機",
            "監視先の `Files/increment` は作成するだけで、増分 CSV は置きません",
            "INCREMENTS_STAGED",
            "対象 Reflex が Off",
            "DonationEvents にまだ行がない",
            "公式 MCP の `start_rule` またはポータルの［Start］で既存ルールを正式に開始",
            "対象 Pipeline の最新の実行履歴で run が 0 件",
            "配布原本と SHA-256 が一致する未取り込みファイル",
            "ファイルや履歴の削除・上書きはしません",
            "同じファイルを重ねて置きません",
            "既に取り込み済みの行がある場合はこの初期化を行わず",
            "OneLake → Activator → Pipeline の自動起動を確認したことにはなりません",
            "トリガー未検証",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, self.guide)

    def test_ingestion_recovery_does_not_assume_rollback(self) -> None:
        self.assertIn("実行の中止やファイルの削除では取り込み済み行は戻らない", self.guide)
        self.assertIn("他の実習のテーブルを作り直さない", self.guide)
        self.assertNotIn("空なら実行を破棄して再アップロードする", self.guide)

    def test_trigger_proof_uses_activation_not_invocation_label(self) -> None:
        for marker in (
            "新規ルールを追加せず",
            "公式 MCP の `start_rule`、またはポータルの正式な［Start］操作",
            "`Type`・`Subject`・`Source` は OneLake イベントからの動的な対応付けを保持",
            "`invokeType` が `Manual` と表示されても",
            "Activator の activation / アクション実行記録",
            "イベントの受信だけ、定義の有効フラグだけ",
            "実行履歴の集計グラフ",
            "第 12.4 節の実行証拠の照合",
            "公式 MCP の `stop_rule` またはポータルの［Stop］",
            "作成済みの run もすべて終了",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, self.guide)

    def test_formal_first_start_and_complete_upload_are_distinct_gates(self) -> None:
        for marker in (
            "`shouldRun=true` への変更だけを初回起動の代わりにしません",
            "`isRunning=true` と画面の Running も設定状態の確認",
            "armed_unverified",
            "automatic_delivery_verified",
            "uploaded_unverified",
            "`If-None-Match: *`",
            "CreateFile し、Append → FlushWithClose",
            "native activation 1 件・新しい Completed Job 1 件",
            "`DataNotAvailable`",
            "activation 0 件という成功結果に置き換えません",
            "ACTIVATOR_REQUIRES_FORMAL_START",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, self.guide)

    def test_child_notebook_identity_is_not_inferred_from_lakehouse(self) -> None:
        for marker in (
            "Notebook 01 のコピーへ指定した PARTICIPANT_ID と Default Lakehouse を設定",
            "配布元の Notebook 01 自体は書き換えません",
            "子 Notebook の PID が正しい証拠にはなりません",
            "不一致なら先へ進まず",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, self.guide)

    def test_oversized_payload_refusal_preserves_interactive_gate(self) -> None:
        for marker in (
            "`exceeds the 500k limit`",
            "Notebook 04 のジョブはまだ始まっていません",
            "配布 Notebook を取り込み直し",
            "完全なインライン payload を複数セルに分け",
            "対話実行ゲートの解除で回避しません",
            "パラメーターセルと見出しを確認",
            "起動後に error 出力がある実行は未開始と区別",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, self.guide)

    def test_missing_parameter_execution_restarts_read_only_preview(self) -> None:
        for marker in (
            "`NameError`",
            "APPLY_CHANGES=False に戻して",
            "パラメーターセルを明示的に実行してから preview",
            "起動後のエラーであり、実行前のセルサイズ拒否とは区別",
            "古い計画ハッシュや成功結果で補完",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, self.guide)

    def test_failed_apply_preserves_full_byte_gate_and_history(self) -> None:
        for marker in (
            "OneLake の全バイト検証と schema 対応",
            "`fs.head` の部分表示で代用せず",
            "`fs.cp` でドライバーへバイトを保持してコピー",
            "全バイトの SHA-256",
            "検証エラーだけを理由に正しい CSV を削除・再アップロードしない",
            "ファイル検証や計画ハッシュの不一致で停止した場合",
            "preview を取り直します",
            "旧 checkpoint",
            "既存資産や履歴を削除しません",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, self.guide)

    def test_statement_metadata_is_not_job_success(self) -> None:
        for marker in (
            "今回の実行のジョブが最終成功状態",
            "全セルの出力に error がない",
            "finished / available だけでは成功を証明できません",
            "InProgress の実行や古い preview 出力",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, self.guide)

    def test_schema_aware_recovery_keeps_schema_and_data_gates(self) -> None:
        for marker in (
            "`UnsupportedOperationForSchemasEnabledLakehouse`",
            "schemas を Off にしたり",
            "Lakehouse を作り直して回避しません",
            "defaultSchema",
            "`Tables/<schema>`",
            "`_delta_log`",
            "ディレクトリの存在だけで合格にせず",
            "第 6.5 節の件数・金額も照合",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, self.guide)

    def test_metadata_gate_counts_existing_complete_definition(self) -> None:
        self.assertIn("第 14 章のバインディングと Ontology の更新完了を先に確認", self.guide)
        self.assertIn(f"{self.context.metadata_object_count} 件のsemanticEnrichment が既に含まれます", self.guide)
        self.assertIn("Notebook 02 の差分が 0 件でも異常ではありません", self.guide)
        self.assertIn('APPLY_CONFIRMATION="APPLY ONTOLOGY METADATA"', self.guide)

    def test_graph_item_creation_is_not_functional_acceptance(self) -> None:
        for marker in (
            "`GraphNotRefreshable`",
            "Graph の機能は未確認",
            "Property source / Data source",
            "Graph のコンパイルと更新ジョブが完了してから",
            "item の存在だけで合格にしません",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, self.guide)

    def test_lakehouse_schema_does_not_rewrite_kql_bindings(self) -> None:
        for marker in (
            "`sourceSchema` を `dbo` として保存",
            "ID・メタデータ・無関係の定義を保持",
            "Eventhouse の time-series バインディングまで一律に `dbo` へ変更してはいけません",
            "schema やバインディングの修復には使いません",
            "同じ完全定義を使う Notebook 04",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, self.guide)

    def test_missing_false_flag_requires_effective_state_evidence(self) -> None:
        for marker in (
            "`codeInterpreterEnabled=false` が省略される場合",
            "キーの欠落だけで有効・無効や定義の一致を判定しません",
            "Code Interpreter が無効であることを記録",
            "無効を確認せずに省略を受け入れません",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, self.guide)

    def test_analytics_ready_is_not_power_bi_deployment(self) -> None:
        for marker in (
            "配置先 Folder と Default Lakehouse は別の設定",
            "Eventhouse に行があるだけでは",
            "ANALYTICS_READY",
            "Preparing / Publishing",
            "Notebook 05 が作るのは分析テーブルであり、SemanticModel / Report item ではありません",
            "Power BI Desktop の Publish で代用しません",
            "FolderId は対象 Lakehouse と同じ Folder の実 GUID",
            "実際の LakehouseId",
            "Direct Lake の接続・DAX の結果・レポート表示",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, self.guide)
        self.assertNotIn(
            "D.3 の Notebook 05 が作るのは、Direct Lake でレポートを描くためのセマンティックモデルです",
            self.guide,
        )
        self.assertNotIn("FolderId パラメーターがなく", self.guide)

    def test_power_bi_updates_require_explicit_scope_and_identity(self) -> None:
        for marker in (
            "SQL analytics endpoint で必要な gold テーブルが参照できる",
            "メタデータの反映・更新を待ってから進みます",
            "配置スクリプトが `ops.analytics_publish_control` を自動検査するわけではありません",
            "ExpectedUserPrincipalName と ExpectedTenantId",
            "これらの実値は配布物へ書き込みません",
            "`-UpdateExisting` を明示",
            "他の Folder の同名 item の更新を許可するものではありません",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, self.guide)

    def test_calendar_coverage_and_prior_year_ranges_are_explicit(self) -> None:
        for marker in (
            "各暦年の年初から年末まで日付が連続",
            "最後の寄付日・観測日で打ち切らず",
            "DAX の期間補正で隠しません",
            "その日付に寄付・観測があることは意味しません",
            "`SAMEPERIODLASTYEAR`",
            "前年の開始日・終了日を明示した SQL 集計",
            "意図せず月末まで拡張されていないか",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, self.guide)

    def test_hydration_does_not_change_selection_count_units(self) -> None:
        for marker in (
            "件数の単位は順にテーブル・マテリアライズドビュー・Entity Type",
            "列などの子要素を含む総数ではありません",
            "内部の element ID や未選択の枝",
            "選択違い・参照先違い・説明の変更を無視して一致扱いにしません",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, self.guide)

    def test_reference_architecture_preserves_the_full_teaching_model(self) -> None:
        for marker in (
            "16.9 AI 参照アーキテクチャ（明示 opt-in）",
            "教材用 full Ontology を使う標準コース（Core）",
            "標準コースの教材用モデルを置き換えません",
            "10 Entity / 72 static Property / 1 time-series Property / 15 Relationship",
            "10 Entity / 21 static Property / 0 time-series Property / 15 Relationship",
            "52 parts", "`ONT_Furusato_AIPath_<PID>`",
            "この手順や Notebook 02 の対象にしません",
            "`MunicipalityCatalogsGift` を含む正規の 15 関係をすべて残します",
            "元の 11 dbo テーブル / 88 選択列",
            "金額を含む静的属性は SQL",
            "JST では 2026-01-01 に達する行があり得る",
            "任意の JST 暦年フィルターで切り捨てません",
            "モデル件数は設計契約であり、応答品質を保証するものではありません",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, self.guide)
        code = [n["text"] for n in self.guide_nodes if n.kind == "code"]
        self.assertIn(self.context.agent_instructions.rstrip("\r\n"), code)

    def test_reference_sql_selection_and_trace_grain_are_explicit(self) -> None:
        table = next(
            n for n in self.guide_nodes
            if n.kind == "table"
            and n["caption"] == "6 SQL オブジェクトの存在と 3 個の直接選択を区別する"
        )
        self.assertEqual(
            {row[0]: int(row[1].split()[0]) for row in table["rows"]},
            {
                "agent_ref.MunicipalityStatic": 20,
                "agent_ref.DonationAttributes": 40,
                "agent_ref.GiftCatalogSuppliers": 29,
                "agent_ref.MunicipalityById": 22,
                "agent_ref.DonationById": 42,
                "agent_ref.DonationTraceById": 30,
            },
        )
        self.assertEqual(
            {row[0] for row in table["rows"] if row[2] == "選択"},
            {
                "agent_ref.MunicipalityStatic",
                "agent_ref.MunicipalityById",
                "agent_ref.DonationTraceById",
            },
        )
        for marker in (
            "行をまたいで加算できません", "LEFT JOIN", "null-Supplier 行",
            "Donor・在住 Prefecture・受入 Municipality・受入 Prefecture・Gift・Category・すべての登録 Supplier",
            "名前は ID の代わりではなく", "製造・発送・履行の実績を証明しません",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, self.guide)

    def test_reference_kql_functions_keep_approved_observation_semantics(self) -> None:
        table = next(
            n for n in self.guide_nodes
            if n.kind == "table" and n["caption"] == "承認済み MV に基づく 3 KQL 関数"
        )
        self.assertEqual(
            [(row[0], re.search(r"(\d+) fields", row[1]).group(1)) for row in table["rows"]],
            [
                ("AgentRawObservationTotals", "14"),
                ("AgentFileRunSummary", "17"),
                ("AgentMunicipalityLeaders", "15"),
            ],
        )
        for marker in (
            "SourceFile × WorkshopRunId × ParticipantAlias",
            "FirstObservedAt / LastObservedAt の実時刻",
            "一意 MunicipalityID の 0〜2 行",
            "件数首位と金額首位が同じなら 1 行で両 flag",
            "この節で指定した関数以外は直接選択しません",
            "WindowIsValid=false は有効な 0 件として受け入れません",
            "イベント識別子も一意イベント指標もありません",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, self.guide)

    def test_reference_opt_in_requires_bundled_pins_without_rewriting_core(self) -> None:
        for marker in (
            "`ENABLE_AI_REFERENCE_ARCHITECTURE=False` が既定",
            "`ai-reference/global-instructions.txt` と `global-profile.json`",
            "必要なファイルがない場合は停止",
            "profile の `sha256` と一致することを確認",
            "`status` の candidate / accepted は設定の宣言",
            "認証・Workspace discovery より前に停止",
            "Core の GLOBAL へのフォールバック",
            "`DA_Furusato_AIReference_<PID>`",
            "`REFERENCE_AGENT_ROLE='authorized-candidate'`",
            "`REFERENCE_AGENT_NAME`・実 GUID の `REFERENCE_AGENT_EXPECTED_ID`",
            "構成の完全一致",
            "不一致を上書きや別 Agent の追加で解消せず停止",
            "既存 Core の設定変更はこの手順に含めません",
            "`accepted` を指定するだけでは受入になりません",
            "最終 preview より前に確定",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, self.guide)
        command = next(
            n["text"] for n in self.guide_nodes
            if n.kind == "code" and "Get-FileHash" in n["text"]
        )
        for marker in (
            f".\\workshop\\v{self.context.version}\\provisioning\\bundle",
            "Get-Content -Raw", r"$bundle\ai-reference\global-profile.json",
            r"$bundle\ai-reference\global-instructions.txt", "-Algorithm SHA256",
        ):
            self.assertIn(marker, command)
        self.assertNotIn("Set-Content", command)
        self.assertNotIn("reseal_runtime.py", command)

    def test_reference_discovery_does_not_fabricate_schema_or_selection(self) -> None:
        for marker in (
            "SQL オブジェクトと KQL 関数は metadata discovery より先に定義",
            "対象 Lakehouse の実 metadata",
            "`staging/datasources/{id}/elements`",
            "opaque ID を PATCH", "serialized UUID は代用しません",
            "`Available` かつ `hasSubElements=false`",
            "未選択表示の `Functions` grouping",
            "SQL の返却型が Agent metadata では空",
            "native SQL/KQL の実 schema は別に照合・保存",
            "空欄を推測した型や children で埋めません",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, self.guide)

    def test_reference_adapters_preflight_and_preserve_partial_state(self) -> None:
        for marker in (
            "`pyodbc`", "`Microsoft ODBC Driver 18 for SQL Server`",
            "`msodbcsql18`", "`unixODBC`", "Linux の Notebook driver host",
            "自動インストールはしません",
            "token 要求前に停止", "最初の remote 書き込みより前",
            "https://database.windows.net/", "メモリ内だけで扱います",
            "`properties.sqlEndpointProperties.connectionString`",
            "正式な `displayName` または明示的な endpoint DB field",
            "schema を含む 7 DDL", "既存の空 schema では owner・権限を保持",
            "完全に一致する 6 オブジェクトは再利用",
            "部分作成・管理対象外・不一致は削除や上書きをせず停止",
            "基線の 5 コマンド", "3 関数を加えた 8 コマンド",
            "CREATE を盲目的に再実行しません",
            "上限時間付きの読み取り専用照会", "権限・型の不一致や DDL 失敗は再試行せず",
            "必須・直接選択の対象にはせず、自動削除しません",
            "全体成功や自動ロールバックと見なさず",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, self.guide)

    def test_reference_parameter_rows_match_the_committed_notebook(self) -> None:
        notebook = self.context.notebooks["Notebook_04"]
        rows = build_parameter_rows(self.context, "Notebook_04")
        self.assertEqual([row[0] for row in rows], list(notebook.parameters))
        self.assertEqual(len(rows), 19)
        self.assertIs(notebook.parameters["ENABLE_UNIFIED_DATA_AGENT"], False)
        names = {
            "ENABLE_AI_REFERENCE_ARCHITECTURE",
            "REFERENCE_AGENT_NAME",
            "REFERENCE_AGENT_ROLE",
            "REFERENCE_AGENT_EXPECTED_ID",
        }
        for row in rows:
            with self.subTest(parameter=row[0]):
                self.assertEqual(row[2], format_default(notebook.parameters[row[0]]))
                if row[0] in names:
                    self.assertTrue(all(row[3:7]))
                    self.assertEqual(row[7], "付録 D.2")
        self.assertEqual(
            {name: notebook.parameters[name] for name in names},
            {
                "ENABLE_AI_REFERENCE_ARCHITECTURE": False,
                "REFERENCE_AGENT_NAME": "",
                "REFERENCE_AGENT_ROLE": "isolated-reference",
                "REFERENCE_AGENT_EXPECTED_ID": "",
            },
        )

    def test_reference_token_audience_is_a_real_hyperlink_in_both_languages(self) -> None:
        audience = "https://database.windows.net/"
        text = next(
            n["text"] for n in self.guide_nodes
            if n.kind == "callout" and n.get("title") == "参照 SQL の依存関係を先に満たす"
        )
        for label, content in (("ja", text), ("en", load_mirror().get(text))):
            with self.subTest(language=label):
                self.assertIn(audience, content)
                self.assertNotIn(f"`{audience}`", content)
                builder = DocumentBuilder.__new__(DocumentBuilder)
                builder.hyperlinks = []
                paragraph = Document().add_paragraph()
                builder._rich(paragraph, content)
                links = paragraph._p.findall(qn("w:hyperlink"))
                self.assertEqual(
                    [paragraph.part.rels[link.get(qn("r:id"))].target_ref for link in links],
                    [audience],
                )
                self.assertEqual(builder.hyperlinks, [audience])

    def test_parameter_index_uses_current_counts_and_notebook_hash(self) -> None:
        total = sum(len(notebook.parameters) for notebook in self.context.notebooks.values())
        table = next(
            node for node in self.guide_nodes
            if node.kind == "table"
            and node["caption"] == f"Notebook 01–05 のパラメーター索引（合計 {total} パラメーター）"
        )
        notebook = self.context.notebooks["Notebook_04"]
        row = next(row for row in table["rows"] if row[0] == notebook.name)
        self.assertEqual(total, 51)
        self.assertEqual(row[3], str(len(notebook.parameters)))
        self.assertEqual(row[5], notebook.sha256)

    def test_reference_item_plan_is_not_workspace_inventory(self) -> None:
        note = next(
            node["text"] for node in self.guide_nodes
            if node.kind == "callout"
            and node.get("title") == "一括構築後も機能ゲートは省略しない"
        )
        for marker in (
            "参照モード False は計画上 8 点",
            "True は別 AIPath を 1 点加えた 9 点",
            "自動生成 GraphModel はこの計画数に含めず",
            "False は 1 点、True は 2 点",
            "対象外の既存アイテムを含む Workspace 全体の inventory 件数とは区別",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, note)

    def test_configuration_pretests_do_not_replace_the_original_ten(self) -> None:
        for marker in (
            "17.0 構成別の query capability pretest",
            "`IncomingDonationAmountYen` 確認質問は教材用 full Ontology 専用",
            "AIPath に接続した Agent へ送信しません",
            "SQL の exact-ID 取得、承認済み KQL 関数、AIPath の count・path・identity",
            "元の 10 問／84 要件を追加・削除・置換するものではありません",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, self.guide)
        self.assertEqual(len(self.tests), 10)
        for test in self.tests:
            with self.subTest(test=test.test_id):
                self.assertIn(test.question, self.guide)
                self.assertIn(test.expected, self.guide)
                for criterion in (*test.evidence, *test.pass_criteria):
                    self.assertIn(criterion, self.guide)

    def test_native_evidence_and_acceptance_remain_strict(self) -> None:
        for marker in (
            "実際の全 query・全返却結果・analysis steps・native 最終回答の全文を非公開で保存",
            "元の Unicode 質問を読み戻して正確に 1 回だけ Send",
            "画面に見えない行の推測",             "回答の後編集による補完を native 品質に数えません",
            "独立したレビューで全 query を 1 本ずつ確認",
            "必要な証跡の取得失敗は免除しません",
            "評価中に設定やソース選択が変わった場合は停止",
            "SQL にあるだけ、名前だけの回答では不足",
            "その literal ID を SQL と Graph に引き渡して", "実 Graph path",
            "代替は静的スナップショットの寄付額と順位だけ",
            "応答待ちで中断した実行", "送信前に停止した実行を区別",
            "完了した 10 問の評価とは扱いません",
            "厳密な 10/10 を反復", "未使用 holdout",
            "有限回の正答率は普遍的な精度保証ではありません",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, self.guide)
        self.assertNotIn("クエリ本文は held-out の前提を壊します", self.guide)
        self.assertNotIn("10 問はコード実行なしで合格します", self.guide)

    def test_shared_t09_does_not_require_reference_only_tvf(self) -> None:
        table = next(
            node for node in self.guide_nodes
            if node.kind == "table"
            and node["caption"] == "新しい採点項目ではなく、元の条件の見落としを防ぐ"
        )
        t09 = next(row[1] for row in table["rows"] if row[0] == "T09 のクロスソース照合")
        self.assertIn("その literal ID を SQL と Graph に引き渡して", t09)
        self.assertNotIn("MunicipalityById", t09)
        for public in (False, True):
            with self.subTest(public=public):
                english = load_mirror(public_documents_only=public).get(t09)
                self.assertIn("literal ID to SQL and Graph", english)
                self.assertNotIn("MunicipalityById", english)
        start = next(
            i for i, node in enumerate(self.guide_nodes)
            if node.kind == "heading"
            and node["text"] == "16.9 AI 参照アーキテクチャ（明示 opt-in）"
        )
        end = next(
            i for i, node in enumerate(self.guide_nodes)
            if node.kind == "heading" and node["text"] == "17. 10 問の held-out テスト"
        )
        reference = "\n".join(
            text for node in self.guide_nodes[start:end] for text, _role in _strings(node)
        )
        self.assertIn("`agent_ref.MunicipalityById` に渡す方法を優先", reference)
        self.assertIn("この TVF は共通の T09 合格条件ではありません", reference)
        self.assertIn("Core は選択済みの元の dbo テーブルへの通常 SQL で照合できます", reference)

    def test_security_state_and_owned_window_recovery_are_qualified(self) -> None:
        for marker in (
            "対象 Workspace の設定は管理者と確認します",
            "設定の欠落や import・refresh の成功から、OneLake Security が無効だと推測しません",
            "互換性を通すためにセキュリティを変更しません",
            "表示だけで原因を断定せず",
            "全ブラウザーの終了、共有 cache の削除、セキュリティ機構の迂回はしません",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, self.guide)
        self.assertNotIn("OneLake Security と Delta column mapping は有効にしません", self.guide)
        recovery = next(
            n["text"] for n in self.guide_nodes
            if n.kind == "callout"
            and n.get("title") == "本文と対象 Agent を確認してから質問を送る"
        )
        self.assertLess(
            recovery.index("自分のウィンドウの位置とサイズを確認してリサイズ"),
            recovery.index("アカウント・対象 Agent・評価に使う Draft / Published・Runtime を確認"),
        )
        for marker in (
            "空白・Sleeping", "必要に応じて再読み込み",
            "決めた待機上限", "本文・アカウント・実行モード",
            "質問を Send せず状態を記録して停止",
            "Published の選択肢がない場合も Draft を代用しません",
            "所有していないウィンドウやアイテムは変更しません",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, recovery)

    def test_reference_english_preserves_literals_and_numbers(self) -> None:
        entries = json.loads(
            (ROOT / "tools" / "html" / "furusato_html" / "i18n" / "guide-20.json")
            .read_text(encoding="utf-8")
        )
        for japanese, english in entries.items():
            with self.subTest(text=japanese):
                self.assertCountEqual(
                    re.findall(r"`([^`]+)`", japanese),
                    re.findall(r"`([^`]+)`", english),
                )
                self.assertCountEqual(re.findall(r"\d+", japanese), re.findall(r"\d+", english))

    def test_qualified_schema_names_keep_the_target_guard(self) -> None:
        for marker in (
            "`SHOW SCHEMAS`",
            "`<Workspace>.<Lakehouse>.dbo`",
            "Default Lakehouse の実 ID",
            "末尾の schema 名とバッククォート・大小文字を正規化",
            "非 schema Lakehouse を拒否するガードを外したりして通しません",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, self.guide)

    def test_evaluation_requires_explanation_without_answer_leakage(self) -> None:
        for text in (self.guide, self.record):
            for marker in (
                "期間・スコープ・指標名・根拠",
                "サービスの汎用的なコンテンツブロック",
                "期待する拒否の説明がないものを自動的に PASS にしません",
                "テスト固有の質問文・ID・期待値を与えてはいけません",
            ):
                with self.subTest(marker=marker):
                    self.assertIn(marker, text)

    def test_configuration_errors_are_not_excluded_by_verdict(self) -> None:
        for text in (self.guide, self.record):
            self.assertIn("EXECUTION_ERROR", text)
            self.assertIn("断定できません", text)
            self.assertIn("設定や参照先を修正したら、10 問すべてをやり直します", text)
            self.assertNotIn("設定に起因しないため", text)
            self.assertNotIn("Agent の設定ではなくサービス側", text)
        self.assertEqual(
            validation_doc.RESULT_VALUES,
            ("PASS", "FAIL", "UNCLEAR", "EXECUTION_ERROR"),
        )

    def test_unexecuted_steps_remain_ungraded(self) -> None:
        self.assertIn("新規 Agent の既定は Standard runtime", self.guide)
        self.assertIn("Preview を明示的に選びます", self.guide)
        self.assertIn("定義の作成成功だけで、Core の応答確認を済ませたことにしません", self.guide)
        self.assertIn("判定欄を埋めず", self.guide)
        self.assertIn("未実施 / ブロック", self.record)
        self.assertIn("判定欄を空欄のまま", self.record)
        self.assertIn("Data Agent の実 ID", self.record)

    def test_optional_configuration_requires_runtime_verification(self) -> None:
        self.assertIn("関数単体のテストと公開を先に行います", self.guide)
        self.assertIn("Python ファイルを置いただけで接続済みとはしません", self.guide)
        self.assertIn("Agent から対象関数が呼ばれたことも確認", self.guide)
        self.assertIn("関数単体の成功で代用しません", self.guide)
        self.assertIn("回答に Python コードがあることだけでは実行を証明できません", self.guide)
        self.assertIn("UI と MCP などの経路を分けて評価", self.guide)
        self.assertIn("確認できない経路は未確認と記録", self.guide)
        self.assertIn("日本語の図はラベルの欠落も確認", self.guide)
        self.assertIn("テンプレートの取り込みだけでは Notebook のパラメーターや Pipeline に値は自動接続されません", self.guide)

    def test_optional_tool_availability_is_not_universal(self) -> None:
        for marker in (
            "両方が必ず提供されるとはみなしません",
            "User data functions がメニューに表示されない場合",
            "接続後の 10 問をブロックとして記録",
            "表示されない理由を推測してテナント設定や権限を変更しません",
            "単発の前後比較だけで改善や因果関係を結論づけません",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, self.guide)
        self.assertNotIn("Data Agent には、User data functions と Code Interpreter をツールとして追加できます", self.guide)
        self.assertIn("構成区分（Core / Optional）", self.record)
        self.assertIn("追加ツールと実行確認（Core は追加ツールなし）", self.record)
        self.assertIn("Core とは別の記録票", self.record)
        self.assertIn("単発の結果差を改善の証明とせず", self.record)

    def test_gold_evaluation_keeps_partitions_and_core_separate(self) -> None:
        for marker in (
            "D.3.4 Gold を Data Agent で評価する場合",
            "実際の区分列は `DataSource`",
            "`StaticSeed` と `RealtimeIncrement` が同居",
            "`SourceDataset` は SQL 出力の別名",
            "このテーブルの実列名ではありません",
            "Core Eventhouse の raw 観測と同じ指標ではありません",
            "Core の指示・選択テーブル・few-shot は変更せず",
            "実施していない障害試験は未実施と記録",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, self.guide)

    def test_workbook_reference_is_edition_neutral(self) -> None:
        self.assertIn("このガイドと同じ配布版の処理仕様ワークブック", self.guide)
        self.assertIn("`Parameters_Core` シート", self.guide)
        self.assertNotIn(
            f"Furusato_Notebook_01-05_Processing_Specification_v{self.context.version}.xlsx",
            self.guide,
        )

    def test_exact_english_mirror_has_no_drift(self) -> None:
        delta = collect(ROOT)
        self.assertEqual(delta["missing"], [])
        self.assertEqual(delta["unused"], [])
        self.assertEqual(delta["suspicious"], [])

    def test_participant_content_excludes_authoring_history_but_keeps_the_contract(self) -> None:
        headings = [
            node["text"] for node in self.guide_nodes
            if node.kind == "heading" and node["level"] == 1
        ]
        self.assertEqual(len(headings), 24)
        self.assertEqual(
            [int(re.match(r"(\d+)\.", text).group(1)) for text in headings[:19]],
            list(range(1, 20)),
        )
        self.assertEqual([text.split("　")[0] for text in headings[19:]], [
            "付録 A", "付録 B", "付録 C", "付録 D", "付録 E",
        ])
        self.assertEqual(
            sum(len(test.evidence) + len(test.pass_criteria) for test in self.tests),
            84,
        )
        self.assertIn("合格条件は 10/10 です。9/10 は不合格", self.guide)
        self.assertIn("T03 は確認質問の分岐も許容", self.guide)
        self.assertIn("選択した分岐に適用されない要件だけを NA", self.guide)
        for pattern in (
            r"quality-v\d+", r"atomic-v\d+", r"Core は未昇格", r"Core への昇格",
            r"本節の確定済み比較記録", r"採点未確定", r"A/B の実行記録",
            r"reseal・contract・validator", r"毎回の full build", r"style.?carrier",
            r"修正前の Notebook", r"画面写真は.*取得が無いため",
        ):
            with self.subTest(pattern=pattern):
                self.assertNotRegex(self.guide, pattern)
        code = "\n".join(n["text"] for n in self.guide_nodes if n.kind == "code")
        self.assertNotIn("reseal_runtime.py", code)
        self.assertNotIn("quality_profile.py", code)

    def test_teaching_screens_remain_and_history_screens_are_not_relabelled(self) -> None:
        figures = {n["source_key"]: n for n in self.guide_nodes if n.kind == "figure"}
        for tag in ("13-6", "13-7", "13-12", "13-33", "17-1"):
            self.assertIn(tag, figures)
        self.assertFalse({"17-2", "17-3", "17-4"} & figures.keys())
        self.assertIn("教材用 full Ontology", figures["17-1"]["caption"])
        self.assertNotIn("過去", figures["17-1"]["caption"])

    def test_ontology_editing_reference_has_no_material_provenance_in_either_language(self) -> None:
        start = next(
            i for i, n in enumerate(self.guide_nodes)
            if n.kind == "heading" and n["text"].startswith(quality._D6_START)
        )
        end = next(
            i for i, n in enumerate(self.guide_nodes[start + 1:], start + 1)
            if n.kind == "heading" and n["text"].startswith(quality._D6_END)
        )
        nodes = self.guide_nodes[start:end]
        strings = [text for n in nodes for text, _ in _strings(n)]
        table = next(
            n for n in nodes
            if n.kind == "table" and n["caption"] == "公開ドキュメントで確認する 8 つの主題"
        )
        self.assertEqual(len(table["rows"]), 8)
        self.assertIn("特定の製品機能の提供や動作を保証するものではありません", "\n".join(strings))
        self.assertIn("標準コースの教材用 Ontology", "\n".join(strings))
        self.assertIn("AI 参照構成の別モデルとソース選択は第 16.9 節", "\n".join(strings))
        for public in (False, True):
            mirror = load_mirror(public_documents_only=public)
            languages = {
                "ja": "\n".join(strings),
                "en": "\n".join(mirror.get(text) for text in strings),
            }
            for language, text in languages.items():
                with self.subTest(public=public, language=language):
                    for pattern in quality._D6_AUTHORING_HISTORY:
                        self.assertNotRegex(text, pattern)
                    for phrase in (
                        "2026 年 8 月 19 日", "19 August 2026", "August 19, 2026",
                        "supplied material", "provided material", "資料に対する評価記録",
                        "Microsoft Learn では公開されておらず", "公開され次第",
                    ):
                        self.assertNotIn(phrase, text)

    def test_preview_reference_source_passes_all_content_guards(self) -> None:
        report = quality.Report(target="participant reference source")
        quality.check_preview_material_handling(self.context, quality._plain(self.guide), report)
        self.assertEqual(
            [(f.check, f.message) for f in report.findings if f.level == "FAIL"],
            [],
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
