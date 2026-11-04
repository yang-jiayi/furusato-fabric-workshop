"""Current-only, source-backed semantic-model preparation instructions."""
from __future__ import annotations

import json
from pathlib import Path

from furusato_html.model import Block, Text

PAYLOAD = Path("workshop/v3.0.0-preview/powerbi/prep-for-ai")


def append_sections(chapter, root, *, figures=None):
    from .participant30 import add_section, bullet_list, paragraph, text_table

    assets = Path(root) / PAYLOAD
    contract = json.loads((assets / "schema.json").read_bytes())
    instructions = (assets / contract["instructionsFile"]).read_text(encoding="utf-8")
    agent = (assets / contract["agentGuidanceFile"]).read_text(encoding="utf-8")
    if not 0 < len(instructions) <= contract["characterLimit"]:
        raise ValueError("Semantic-model AI instructions exceed the model character limit")
    rows = [
        [Text(name, name), Text("、".join(value["columns"]), ", ".join(value["columns"])),
         Text("、".join(value["dependencyColumns"]), ", ".join(value["dependencyColumns"])),
         Text("、".join(value["measures"]) or "なし", ", ".join(value["measures"]) or "None")]
        for name, value in contract["tables"].items()
    ]
    add_section(chapter, "6", ("モデルを Prep for AI で準備する", "Prepare the model for AI"), [
        paragraph((
            "DAX 生成は Semantic model の metadata と Prep for AI を参照し、Agent 全体の Instructions に書いたモデル固有の計算・フィルター指示を参照しません。既存の日本語名、5テーブルの単方向スター型関係、10個の明示メジャーを使います。寄附金額は明示メジャーで集計し、数値キー・年齢・年・月番号は合計しません。追加の Agent、モデル、MCP、ライブラリの導入は不要です。",
            "DAX generation uses semantic-model metadata and Prep for AI, not model-specific calculation/filter rules in Agent-wide Instructions. Use the existing Japanese names, five-table single-direction star schema and ten explicit measures. Aggregate donation amounts with explicit measures; do not sum numeric keys, age, year or month number. No additional agent, model, MCP server or library installation is needed.")),
        paragraph((
            f"`{PAYLOAD.as_posix()}/schema.json` は版管理された選択契約です。`model-instructions.txt` はモデル用の本文、`agent-instructions.txt` は共通の応答形式・ソース振り分け用の別候補です。ファイルの同梱、Notebook の配置、SDK の実行だけでは Prep for AI は有効になりません。この教材の自動配置はこれらを native 設定として適用せず、以下の許可された手動設定と確認が必要です。既存 Agent の frozen profile 適用手順と、この候補を混在させません。",
            f"`{PAYLOAD.as_posix()}/schema.json` is the versioned selection contract. `model-instructions.txt` contains model-level guidance; `agent-instructions.txt` is a separate candidate for common response formatting and source routing. Shipping files, deploying notebooks or running the SDK does not activate Prep for AI. Automated deployment does not apply these as native settings; authorized manual setup and verification below are required. Do not mix this candidate with the existing Agent's frozen-profile apply procedure.")),
        paragraph((
            "AI instructions と AI data schema は LSDL に保存されます。公式の Copilot/ 定義スキーマと REST の定義例、Git・deployment pipeline 経由の編集に関する説明はありますが、この教材では定義経由の適用・読み戻しを検証していません。非対応と断定もせず、以下の native UI を確認済みの参加者経路とします。schema.json は公式 Copilot/ part そのものではありません。",
            "AI instructions and AI data schemas are saved to the LSDL. Official Copilot/ definition schemas, a REST definition example and guidance on edits through Git/deployment pipelines exist, but definition-based application/readback is unvalidated here, not declared unsupported. Use the native UI below as the proven participant route. schema.json is not itself an official Copilot/ definition part.")),
        bullet_list([
            ("自分のモデルで変更が許可されていること、モデルの編集権限と組織の Copilot 利用条件を確認します。同じ Semantic model を Power BI service で開き、Viewing から Editing に切り替え、Home リボンの Copilot のドロップダウンから Prep data for AI を選びます。狭いリボンでは右の送りボタンで Copilot を表示します。Viewing mode の「changes will not be saved」表示中は編集・保存できず、そこで無効な項目があっても機能の不存在や Q&A の無効を意味しません。編集できない場合は停止して担当者に確認します。モデルの Q&A は前提条件なので有効状態を担当者と確認し、無効化する同意欄は選択しません。組織・テナント設定を勝手に変更せず、Q&A 廃止後の代替設定も推測しません。",
             "Confirm authorization to change your model, model authoring permission and organizational Copilot prerequisites. Open the same semantic model in the Power BI service, switch Viewing to Editing, then choose Home > Copilot dropdown > Prep data for AI. On a narrow ribbon, use the right paddle to bring Copilot into view. A Viewing mode banner saying changes will not be saved means edits cannot be saved; a disabled control there proves neither feature absence nor disabled Q&A. Stop and consult the owner if editing is unavailable. Q&A is a model prerequisite: confirm its enabled state with the owner and do not select a consent box that disables it. Do not change organization/tenant settings or guess a replacement after Q&A retirement."),
            ("開始画面の Simplify the data schema カードを選び、下表の業務列・メジャーに加え、依存列も確認・選択します。依存列には明示メジャー、関係、月の並べ替えに必要な非表示列を含みます。表示設定を一括変更したり、依存列を除いたりしません。寄附日時 UTC と日付キーだけを今回の優先スキーマから除外します。全5テーブルの41項目中39項目を、件数だけでなく名前で照合して Apply で保存します。狭いダイアログでは Back で開始画面のカードに戻ります。表示されていない横のタブを探す必要はありません。",
             "Choose the Simplify the data schema card on the landing screen. Review/select the business columns and measures below together with their dependency columns, including hidden fields needed by explicit measures, relationships and month sorting. Do not bulk-unhide fields or omit dependencies. Exclude only 寄附日時 UTC and 日付キー from this prioritized schema. Match all five tables' 39 selected fields out of 41 by name, not just count, then select Apply. In a narrow dialog, use Back to return to the landing cards; do not assume side-navigation tabs are visible."),
            ("開始画面の Add AI instructions カードを選び、下の本文をそのまま貼り付け、Apply で保存します。モデル用本文は改行をLFに揃えると2,310文字で、上限10,000文字以内です。Close で閉じ、同じ経路から開き直してスキーマの項目名・選択状態と本文全文を照合します。本文が長いのでスクロールし、画面の先頭や文字数だけで一致と判断しません。Agent の Instructions や semantic-model source の非対応 Instructions/Description 欄には貼り付けません。画面が利用できなければ「native 設定未適用」と記録して停止します。",
             "Choose the Add AI instructions card, paste the exact model text below and select Apply. With LF line endings it contains 2,310 characters, below the 10,000-character limit. Select Close, reopen through the same route and compare the schema field names/selections and the entire instruction text. Scroll through the long text; its opening lines or character count alone do not prove equality. Do not paste it into Agent Instructions or unsupported semantic-model-source Instructions/Description fields. If the surface is unavailable, record native configuration as not applied and stop."),
            ("Data Agent の直接 Semantic model ソースで、同じ5テーブルと必要な列・メジャーの選択を照合します。現在の選択と異なる場合は差分をレビューし、許可なく拡張・上書きしません。AI schema は優先順位付けであって、認可境界でも全クエリの制限でもありません。RLS・OLS・権限は別途有効なまま維持します。",
             "Reconcile the same five tables and required column/measure selections in the Agent's direct semantic-model source. Review differences from current selections; do not expand or overwrite them without authorization. The AI schema is prioritization, not an authorization boundary or a restriction on every query. Preserve RLS, OLS and permissions independently."),
        ], numbered=True),
        *([figures.block(ident) for ident in (
            "pc-12-prep-navigation", "pc-12-prep-donation-schema",
            "pc-12-prep-date-schema", "pc-12-prep-model-instructions",
        )] if figures is not None else []),
        paragraph((
            "図は実際の保存後の画面を使った操作例です。寄附・日付の図は表示中の一部の項目、本文の図はスクロール領域の一部を示します。全項目・本文全文の照合は自分の環境で行ってください。Apply が無効なことだけで保存内容の一致を判断せず、設定の保存を AI への反映や回答精度の合格と同一視しません。12.7と19章の検証を別に行います。",
            "These actual saved-state screenshots are navigation examples. The donation/date views show only the visible subset of fields; the instructions view shows part of a scrollable text area. Compare every field and the complete text in your own environment. A disabled Apply button alone does not establish equality. Configuration persistence is not proof of effective AI serving or passing answer quality; perform the separate checks in 12.7 and Chapter 19.")),
        text_table(
            [("テーブル", "Table"), ("業務列", "Business columns"),
             ("依存列も含める", "Include dependency columns"), ("明示メジャー", "Explicit measures")],
            rows, ("Prep for AI の選択契約", "Prep for AI selection contract")),
        Block("code", {"text": instructions, "language": Text("モデル用 AI instructions", "Model AI instructions"),
                       "canonicalLiteral": True}),
        paragraph((
            "Agent 共通指示を変更する場合だけ、担当者が次の別候補を既存のソース設定・安全条件と照合し、差分、適用、公開、読み戻しを別に記録します。モデルの計算指示を Agent 側へ移しません。本文を示すことは現行 Agent への適用・公開済みという意味ではありません。",
            "Only when changing common Agent guidance, have the owner review this separate candidate against existing source settings and safeguards, then separately record the diff, application, publication and readback. Do not move model calculation instructions into the Agent. Showing this text does not mean it is applied or published on the current Agent.")),
        Block("code", {"text": agent, "language": Text("Agent 共通指示の候補", "Common Agent guidance candidate"),
                       "canonicalLiteral": True}),
    ])
    add_section(chapter, "7", ("AI 設定の確認と任意の Verified answers", "Verify AI preparation and optional verified answers"), [
        paragraph((
            "Apply・開き直し・設定の読み戻しだけで即時反映を仮定しません。Copilot pane を閉じて開き直し、反映待ちと確認時刻を記録します。Git・deployment pipeline で LSDL/tooling を変更した場合は Import・DirectQuery・Direct Lake とも Power BI service 側のモデル refresh が必要で、DirectQuery・Direct Lake の同期は1日1回です。Direct Lake の再索引は publish/republish、または索引が24時間より古く直近14日間に Copilot/Q&A が使われた場合に行われます。これらの操作は別途許可が必要で、本手順だけでは refresh/republish を実行しません。同期・索引の状態が未確認なら回答評価を開始せず、未確認と記録します。",
            "Do not assume immediate effect from Apply, reopening and settings readback alone. Close/reopen the Copilot pane and record propagation waits and verification times. After Git/deployment-pipeline LSDL/tooling edits, Import, DirectQuery and Direct Lake models require a model refresh in the Power BI service; DirectQuery/Direct Lake sync only once a day. Direct Lake reindexes on publish/republish, or when its index is older than 24 hours and Copilot/Q&A was used within the last 14 days. Such actions require separate authorization; this procedure does not itself run refresh/republish. If sync/index state is unverified, record that and do not start answer evaluation.")),
        paragraph((
            "設定・読み戻しと回答品質は別に確認します。まず12.2の直接 DAX を同じ母集団・期間・フィルターで照合し、モデル用指示の追加前後で19章の固定質問を別の会話から実行します。回答ごとに実際の DAX、ソース、フィルター、結果、エラーを保存します。Gold全体、静的、受入増分、Eventhouse観測を区別し、KEEPFILTERS の交差・BLANK、居住/寄附先都道府県、日付範囲、単位を確認します。指示に固定の正解合計を書かず、採点条件も変更しません。",
            "Separate configuration/readback checks from answer quality. First compare direct DAX in 12.2 under the same population, period and filters, then run Chapter 19's fixed questions in separate conversations before/after model guidance. Save actual DAX, source, filters, result and errors for each answer. Distinguish all Gold, static, accepted increments and Eventhouse observations; check KEEPFILTERS intersection/BLANK, residence versus recipient prefecture, date range and units. Do not put expected totals in instructions or change scoring conditions.")),
        paragraph((
            "スキーマ内の業務列と、優先スキーマ外の UTC 日時の両方を質問し、生成クエリと参照元を確認します。除外列に関する回答の拒否をセキュリティ保証とは扱いません。Data Agent Python SDK は評価に利用できますが、モデルの Prep for AI は設定できません。Copilot を使う場合は pane を閉じて開き直します。Agent のプレビュー runtime が既に有効でも、これらの確認を省略しません。",
            "Test a business field inside the schema and the UTC timestamp outside it; inspect the generated query and source. Do not treat refusal for an excluded field as a security guarantee. The Data Agent Python SDK can evaluate responses but cannot configure model Prep for AI. Close/reopen the Copilot pane when using Copilot. An already-enabled Agent preview runtime does not replace these checks.")),
        paragraph((
            "Verified answers は任意・未設定です。同じモデルに接続した既存レポート、Copilot 対応 workspace と編集権限がある場合だけ検討します。配布レポートの「月別寄附総額 — 当年と前年同期間」は、日付[年月]、寄附[寄附総額]、寄附[寄附総額 前年同期間] を使う候補です。schema.json の6個の完全な質問を trigger の候補とし、visual・page・report の保存フィルターと適用対象を先に確認します。非表示列に依存する visual は使用せず、スライサーが引き継がれると推定しません。柔軟フィルターは実際に対応するものを最大3個までとし、設定後は exact/semantic match と実際の DAX を確認します。レポートが無ければ作成して埋め合わせず、この任意手順を未実施と記録します。",
            "Verified answers are optional and unconfigured. Consider them only with an existing report bound to the same model, a Copilot-enabled workspace and authoring permission. The supplied report's 月別寄附総額 — 当年と前年同期間 visual is a candidate using 日付[年月], 寄附[寄附総額] and 寄附[寄附総額 前年同期間]. Use the six complete questions in schema.json as candidate triggers; first inspect saved visual/page/report filters and scope. Do not use a visual dependent on hidden columns or assume slicers carry over. Configure at most three genuinely supported flexible filters; then verify exact/semantic matching and actual DAX. If no report exists, record this optional step as unperformed rather than create a report to fill the gap.")),
        paragraph((
            "Verified answers の CI/CD は Git integration・REST API・deployment pipeline を含め非対応です。6個の質問は native authoring 用の候補で、配布・Notebook 配置では設定されません。Fabric IQ が有効な Copilot では Verified answers の visual は返されません。対象の Copilot が Fabric IQ 経路かを担当者が別途確認し、IQ 有効なら visual 応答の検証は対象外、未確認なら未確認と記録します。この制限だけで Data Agent の visual metadata による DAX grounding も不可とは判断せず、その利用可否と効果は別途実測します。教材の Data Agent/Ontology 経路の改善や合格を保証しません。",
            "Verified answers do not support CI/CD, including Git integration, REST APIs and deployment pipelines. The six questions are native-authoring-only candidates, not configuration applied by packaging/notebook deployment. Copilot does not return verified answers when Fabric IQ is enabled. Have the owner separately verify whether the target Copilot uses Fabric IQ: if enabled, the visual-response check is not applicable; if unknown record it as unverified. This restriction alone does not establish that Data Agent DAX grounding from visual metadata is unavailable; verify that support and effect separately. It guarantees neither improvement nor passing evaluation in this workshop's Data Agent/Ontology flow.")),
        paragraph((
            "同期・索引と任意機能の公式条件: https://learn.microsoft.com/en-us/power-bi/create-reports/copilot-prepare-data-ai / https://learn.microsoft.com/en-us/power-bi/create-reports/copilot-prepare-data-ai-faq",
            "Official sync/index and optional-feature conditions: https://learn.microsoft.com/en-us/power-bi/create-reports/copilot-prepare-data-ai / https://learn.microsoft.com/en-us/power-bi/create-reports/copilot-prepare-data-ai-faq")),
        paragraph((
            "既存レポートのタイトル・使用列・メジャー・フィルターは DAX 生成の参考情報になりますが、Verified answers の設定済み証拠ではありません。Best Practice Analyzer、Memory Analyzer、Performance Analyzer や Semantic Link Labs の get_measure_dependencies は任意の追加診断です。本手順では未実行で、依存パッケージの導入や Notebook の実行を伴う診断は別途許可と実行記録が必要です。",
            "Existing report titles, columns, measures and filters can inform DAX generation; they do not prove verified answers are configured. Best Practice Analyzer, Memory Analyzer, Performance Analyzer and Semantic Link Labs get_measure_dependencies are optional further diagnostics. They have not been run by this procedure; diagnostics requiring package installation or notebook execution need separate authorization and execution records.")),
        paragraph((
            "公式資料: " + " / ".join(contract["references"]),
            "Official references: " + " / ".join(contract["references"]))),
    ])
