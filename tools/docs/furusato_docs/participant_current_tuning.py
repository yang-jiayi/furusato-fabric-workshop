"""Participant instructions for the current experimental Data Agent profile.

This source is used by the GitHub Lab only. It reads the exact current profile
assets and performs no Fabric or network operation.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from furusato_html.model import Block, Section, Text

PROFILE = "current-experimental"
PROFILE_REL = Path("workshop/v3.0.0-preview/data-agent/profiles") / PROFILE
INSTRUCTION_LIMIT = 10_000
TESTED_GLOBAL_UNITS = 9_422


def _text(ja, en=None):
    return Text(ja, ja if en is None else en)


def _paragraph(ja, en):
    return Block("paragraph", {"text": _text(ja, en), "lead": False})


def _code(value, label="text", *, canonical=False):
    payload = {"text": value, "language": _text(label)}
    if canonical:
        payload["canonicalLiteral"] = True
    return Block("code", payload)


def _steps(rows):
    return Block("list", {"numbered": True, "items": [_text(*row) for row in rows]})

def _profile_command(action, *extra):
    lines = [
        rf".venv\Scripts\python.exe -B tools/data-agent/current_profile.py {action}",
        "  --workspace-id $WorkspaceId",
        "  --folder-id $FolderId",
        "  --agent-id $AgentId",
        "  --private-root $PrivateRoot",
        *("  " + option for option in extra),
    ]
    return " `\n".join(lines)


def _append(chapter: Section, suffix: int, title, blocks):
    number = f"{chapter.number}.{suffix}"
    section = Section(
        ident=f"{chapter.ident}-{suffix}",
        level=2,
        number=number,
        title=_text(f"{number} {title[0]}", f"{number} {title[1]}"),
        blocks=blocks,
        chapter=chapter.chapter,
        appendix=chapter.appendix,
    )
    if any(child.ident == section.ident for child in chapter.children):
        raise ValueError("Duplicate current-profile section: " + section.ident)
    chapter.children.append(section)


def _selected_rows(contract):
    rows = []
    for kind, entries in contract.items():
        if not isinstance(entries, list):
            raise ValueError("Current selection contract must contain per-source lists")
        for item in entries:
            if not isinstance(item, dict) or not {"path", "type", "is_selected"} <= item.keys():
                raise ValueError("Malformed current selection-contract entry")
            path = item["path"]
            if isinstance(path, list):
                path = " / ".join(str(part) for part in path)
            rows.append((
                kind,
                str(path),
                str(item["type"]),
                str(item["is_selected"]).lower(),
                str(item.get("display_name", "")),
                str(item.get("description") or ""),
            ))
    if not rows:
        raise ValueError("Current selection contract has no flat path/type/is_selected entries")
    return rows


def _active_example_count(manifest):
    files = manifest.get("definitionFewshotFiles")
    required = manifest.get("requiredActiveExamples")
    if not isinstance(files, int) or not isinstance(required, int) or files != required:
        raise ValueError("Profile manifest must specify the active few-shot file and example counts")
    if files != 0:
        raise ValueError("Current experimental profile requires zero definition few-shot files/examples")
    return required


def _inventory_rows(manifest):
    counts = manifest.get("counts")
    if not isinstance(counts, dict):
        raise ValueError("Current profile manifest is missing source counts")
    labels = {
        "lakehouse_tables": ("Lakehouse / SQL", "lakehouse_tables.table", "lakehouse_tables.column"),
        "kusto": ("KQL Database", "kusto.table", "kusto.column"),
        "semantic_model": ("Semantic model", "semantic_model.table", "semantic_model.column"),
        "ontology": ("Ontology", "ontology.entity", None),
    }
    rows = []
    for key, (label, object_type, column_type) in labels.items():
        source = counts.get(key, {})
        objects = source.get(object_type, 0)
        columns = source.get(column_type, 0) if column_type else "—"
        measures = source.get("semantic_model.measure", "—") if key == "semantic_model" else "—"
        rows.append((label, str(objects), str(columns), str(measures)))
    return rows


def _assets(root: Path):
    profile = Path(root) / PROFILE_REL
    manifest_path = profile / "profile-manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError("Current experimental profile assets are not present: " + str(profile))
    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes.decode("utf-8"))
    if manifest.get("profile") != PROFILE or not isinstance(manifest.get("sha256"), dict):
        raise ValueError("Unexpected current experimental profile manifest")
    if manifest.get("status") != "experimental" or manifest.get("answerAccuracyAccepted") is not False:
        raise ValueError("Current profile must remain explicitly experimental and unaccepted")
    if (manifest.get("logicalSources"), manifest.get("directSources"),
            manifest.get("nativeOntologyContexts")) != (4, 3, 1):
        raise ValueError("Current profile source-count contract changed")
    for name, expected in manifest["sha256"].items():
        path = profile / name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError("Current profile asset hash mismatch: " + name)

    required = ("global-instructions.txt", "source-instructions.json", "selection-contract.json")
    for name in required:
        if name not in manifest["sha256"]:
            raise ValueError("Current profile manifest does not cover " + name)
    global_instructions = (profile / "global-instructions.txt").read_bytes().decode("utf-8")
    global_units = len(global_instructions.encode("utf-16-le")) // 2
    if global_units != TESTED_GLOBAL_UNITS:
        raise ValueError(f"Expected the exact tested global text ({TESTED_GLOBAL_UNITS} UTF-16 units), got {global_units}")
    source_instructions = json.loads((profile / "source-instructions.json").read_bytes().decode("utf-8"))
    selection_contract = json.loads((profile / "selection-contract.json").read_bytes().decode("utf-8"))
    definition_files = sorted((profile / "definition").glob("*.json"), key=lambda path: path.name)
    if len(definition_files) != 5:
        raise ValueError("Current profile must contain its five portable definition parts")
    if any("definition/" + path.name not in manifest["sha256"] for path in definition_files):
        raise ValueError("Manifest does not cover every portable definition part")
    return {
        "root": Path(root),
        "profile": profile,
        "manifest": manifest,
        "global": global_instructions,
        "global_units": global_units,
        "source_instructions": source_instructions,
        "selection_contract": selection_contract,
        "selection_rows": _selected_rows(selection_contract),
        "active_example_count": _active_example_count(manifest),
        "definition_files": definition_files,
    }


def current_chapter_spec():
    return {
        "intro": [
            (
                "この章では、自分が利用を許可された環境の既存Gen2 Data Agentに、実測・照合済みの実験プロファイルを適用し、Draftと公開版を読み戻します。設定の一致は、回答精度や採用を意味しません。",
                "Apply the measured and reconciled experimental profile to an existing Gen2 Data Agent in an environment you are authorized to use, then read back Draft and Published. Configuration equality does not establish accuracy or adoption.",
            ),
            (
                "4つの論理ソース（Lakehouse、KQL Database、Semantic model、Ontology）を区別します。Ontologyのcontextはsource instructionとは別で、Ontology-groundingがGQL実行を意味するわけではありません。実際のsource・query language・query・resultを対応させて確認します。",
                "Distinguish the four logical sources: Lakehouse, KQL Database, semantic model and Ontology. Ontology context is separate from source instructions, and ontology grounding does not imply GQL execution. Match the actual source, query language, query and result.",
            ),
        ],
        "before": [
            (
                "既存Agentとその4つの論理ソースを確認し、Workspace・フォルダー・Agentの各IDは自分の許可された環境から取得します。未作成の場合に別AgentやSchemaを作る手順ではありません。",
                "Confirm the existing agent and its four logical sources. Obtain workspace, folder and agent IDs from your authorized environment. This procedure does not create another agent or schema if one is missing.",
            ),
            (
                "現在のlive definitionとselectionを読み取り、実際のsource definitionでID-only bindingを解決できることを確認します。共有環境のmirror・時系列作業には別の完全性確認が必要です。",
                "Read the live definition and selections, and confirm ID-only bindings can be resolved against actual source definitions. Mirroring and time-series work in the shared environment require separate completeness checks.",
            ),
        ],
        "steps": [
            {
                "text": (
                    "Add data / Sourcesで既存のLakehouse、KQL Database、Semantic model、主Ontologyを確認します。論理ソース4つと物理datasourceレコード数を取り違えず、ソースを追加しません。",
                    "In Add data / Sources, confirm the existing Lakehouse, KQL Database, semantic model and main Ontology. Do not confuse four logical sources with physical datasource record count, and do not add sources.",
                )
            },
            {
                "text": (
                    "Data AgentのToolsでCode Interpreterの状態を記録します。この章のprofile適用を回避するため、別のAgentやToolを作成しません。",
                    "Record the Code Interpreter state under Data Agent Tools. Do not create another agent or tool as a workaround for applying this profile.",
                )
            },
            {
                "text": (
                    "既存definition、source selections、Ontology context、各stageを先に読み取ります。期待するselectionとの意味差分、schema drift、native type drift、曖昧なbindingを見つけたら停止します。",
                    "Read the existing definition, source selections, Ontology context and stages first. Stop on semantic differences from the expected selections, schema drift, native type drift or ambiguous bindings.",
                )
            },
        ],
        "checks": [
            (
                ("既存の同一Agentと4論理ソースを確認した", "The existing same agent and four logical sources are verified"),
                ("不足するsourceを追加せず、所有者・講師に確認します。", "Do not add a missing source; ask the owner or instructor."),
            ),
            (
                ("現在のdefinitionを読み、未解決binding・schema差分がない", "The live definition is read with no unresolved bindings or schema differences"),
                ("準備処理を止め、現在の定義を確認してから再開します。", "Stop preparation and inspect the live definition before continuing."),
            ),
            (
                ("実際のWorkspace・Folder・Agent IDと許可範囲が一致する", "Actual workspace, folder and agent IDs match the authorized scope"),
                ("IDを推測せず、対象環境の所有者へ確認します。", "Do not guess IDs; confirm them with the environment owner."),
            ),
        ],
        "links": [
            "https://learn.microsoft.com/en-us/fabric/iq/ontology/how-to-use-ontology-agent",
            "https://learn.microsoft.com/en-us/fabric/data-science/concept-data-agent",
        ],
    }


def append_current_tuning_sections(chapter: Section, root: Path):
    """Append current-profile instructions in the stable 17.5–17.16 slots."""
    if chapter.chapter != 17:
        raise ValueError("Current-profile instructions belong to Chapter 17")
    assets = _assets(root)
    profile_rel = PROFILE_REL.as_posix()

    _append(chapter, 5, ("対象と準備", "Scope and prerequisites"), [
        _paragraph(
            "この実験プロファイルを、参加者自身が所有し利用を許可された Workspace とフォルダー内の既存 Gen2 Data Agent に適用し、Draft と公開版を確認します。自分の Workspace ID、Folder ID、Agent ID、PrivateRoot を設定します。別の Agent を作成せず、ソースの追加・選択範囲の拡大・Schema変更も行いません。このプロファイルは実験用で、回答精度の採用・保証を意味しません。",
            "Apply this experimental profile to an existing Gen2 Data Agent in a workspace and folder you own and are authorized to use, then inspect Draft and the published version. Set your own Workspace ID, Folder ID, Agent ID and PrivateRoot. Do not create another agent, add sources, expand selections or change the schema. This profile is experimental; it is not an accepted or guaranteed accuracy result."),
        _steps([
            ("4章のアクセス・容量・権限の確認を済ませます。対象 Agent が既にあり、自分の担当する4つの論理ソース（Lakehouse、KQL Database、Semantic model、Ontology）を含むことを確認します。既存の公開版がある場合は、変更前の状態を PrivateRoot に保存できる手順を確認してから進みます。",
             "Complete the access, capacity and permission checks in Chapter 4. Confirm the existing agent has the four assigned logical sources: Lakehouse, KQL Database, semantic model and Ontology. If a published version exists, first confirm that the procedure can preserve its pre-change state under PrivateRoot."),
            ("現在のソース定義を読み取り、実際の ID と選択状態を記録します。IDだけの binding を実定義に照合できない場合、または想定外の意味差分が見つかった場合は停止し、選択を推測・拡張せず担当者に確認します。",
             "Read the current source definition and record actual IDs and selection state. Stop and consult the instructor if ID-only bindings cannot be resolved against the live definition or an unexpected semantic difference appears; do not guess or expand selections."),
        ]),
        _paragraph(
            "共有環境の部分的な mirroring は、mirror の変更・再取り込み・時系列作業の前提を満たしません。Ontology の静的 SQL は独立したソース・言語・クエリ・結果として扱います。Graph model の存在・準備状態と実際の GQL は別途確認し、どちらも推定しません。",
            "Partial mirroring in the shared environment does not satisfy prerequisites for mirror changes, re-ingestion or time-series work. Treat static Ontology SQL as independent evidence for its own source, language, query and result. Verify Graph-model presence/readiness and actual GQL separately; infer neither."),
    ])
    _append(chapter, 6, ("プロファイル資産と事前確認", "Profile assets and preflight"), [
        _paragraph(
            f"同梱の `{profile_rel}` にある profile-manifest.json、global-instructions.txt、source-instructions.json、selection-contract.json、定義と portable stage template を確認します。manifest の SHA-256 と実ファイルを照合し、プロファイル名が current-experimental であることを確認します。global-instructions.txt は末尾を含めてそのまま使用し、Trimや編集をしません。",
            f"Inspect profile-manifest.json, global-instructions.txt, source-instructions.json, selection-contract.json, the definition and portable stage template under `{profile_rel}`. Compare manifest SHA-256 values with the files and confirm the profile name is current-experimental. Use global-instructions.txt exactly as stored, including its ending; do not trim or edit it."),
        _table(
            [("論理ソース", "Logical source"), ("オブジェクト", "Objects"),
             ("列", "Columns"), ("メジャー", "Measures")],
            _inventory_rows(assets["manifest"]),
            "manifest の選択資産件数",
            "Manifest selection inventory",
        ),
        _paragraph(
            f"この版の definition few-shot file は {assets['manifest']['definitionFewshotFiles']} 件、読み戻しで必要な active example は {assets['active_example_count']} 件です。9件の例を前提にせず、資産や実定義にない例を追加しません。Global 指示本文は実測 {assets['global_units']} UTF-16 単位で、上限 {INSTRUCTION_LIMIT} 単位以下です。実際に選択した別プロファイルの長さも測り、固定の長さを全候補へ当てはめません。",
            f"This profile has {assets['manifest']['definitionFewshotFiles']} definition few-shot files and requires {assets['active_example_count']} active examples on readback. Do not assume nine examples or add examples absent from the assets and live definition. The global instructions measure {assets['global_units']} UTF-16 units, within the {INSTRUCTION_LIMIT}-unit maximum. Measure any other selected profile's actual length instead of applying a fixed length to every candidate."),
    ])
    _append(chapter, 7, ("現在の Agent と選択契約を読み取る", "Read the current agent and selection contract"), [
        _paragraph(
            "既存 Agent の実定義から ID-only binding を解決し、selection-contract.json の path・type・is_selected と照合します。対象は資産ファイルに列挙された選択だけです。欠落・曖昧・予期しない差分があれば停止します。UI で親を再選択して子要素を増やしたり、存在しない ID を作ったりしません。",
            "Resolve ID-only bindings from the existing agent's live definition and compare them with path, type and is_selected in selection-contract.json. Only selections listed in the asset are in scope. Stop on missing, ambiguous or unexpected differences. Do not reselect parent items to expand children or invent IDs."),
        _table(
            [("論理ソース", "Source kind"), ("Semantic path", "Semantic path"),
             ("Type", "Type"), ("is_selected", "is_selected"),
             ("表示名", "Display name"), ("説明", "Description")],
            assets["selection_rows"],
            "実際の flat selection contract",
            "Actual flat selection contract",
            canonical=True,
        ),
    ])
    _append(chapter, 8, ("全体指示を確認する", "Review the global instructions"), [
        _paragraph(
            "次の全体指示は参照用の正確な全文です。この段階では画面上の欄を変更しません。prepare で対象・差分・readback を確認してから、許可された apply 手順だけで適用します。本文・末尾の空白・改行を編集せず、readback は元ファイルと照合します。",
            "The global instructions below are the exact reference text. Do not edit the UI field at this step. After reviewing the target, diffs and readbacks in prepare, apply changes only through the authorized apply procedure. Do not edit the text or its trailing whitespace/line endings; compare readback with the source file."),
        _code(assets["global"], "Agent-wide instructions", canonical=True),
    ])
    _append(chapter, 9, ("ソース指示・説明と Ontology context を確認する", "Review source instructions, descriptions and Ontology context"), [
        _paragraph(
            "次の source-instructions.json は各実ソース欄の正確な参照値です。この段階では画面上の指示・説明・Ontology context を変更しません。prepare で照合し、対象と差分を確認後、許可された apply 手順だけで各値を対応する同じ欄へ適用します。本文を翻訳・短縮したり、他ソースへ移したり、Ontology 用 source instruction を作ったりしません。",
            "The source-instructions.json below contains the exact reference values for each actual source field. Do not edit UI instructions, descriptions or Ontology context at this step. Reconcile them in prepare; after reviewing the target and diffs, apply values only through the authorized apply procedure to their corresponding fields. Do not translate, shorten or move text to another source, or invent an Ontology source instruction."),
        _code(json.dumps(assets["source_instructions"], ensure_ascii=False, indent=2), "JSON", canonical=True),
        _steps([
            ("UI と現在の definition の両方で、4つの論理ソースが同じ対象であることを読み取り確認します。通常の物理 datasource 表示数を、論理ソース数と取り違えません。この段階では変更せず、適用は確認後の apply 手順で行います。",
             "Read-only confirm in both the UI and current definition that the same four logical sources are present. Do not confuse the displayed physical datasource count with the logical source count. Make no changes at this step; apply only through the apply procedure after review."),
            ("Ontology を選択できることは、Ontology の native query や GQL の実行成功を意味しません。SQL・KQL・DAX・GQLは実際のsource/language/query/resultsを照合して別々に記録します。",
             "Ontology selection does not prove a successful native Ontology query or GQL execution. Match and record actual source, language, query and results separately for SQL, KQL, DAX and GQL."),
        ]),
    ])
    _append(chapter, 10, ("現行の Semantic 選択を確認する", "Verify current semantic selections"), [
        _paragraph(
            "selection-contract.json は path/type/is_selected のフラットな契約です。表示された全項目を確認し、記載された選択値を変えません。現在の構成は実際に選択済みの SQL テーブル、KQL 集計、モデルテーブル、Ontology entity に限られます。ソース探索により項目を追加したり、契約外の候補を展開したりしません。",
            "selection-contract.json is a flat path/type/is_selected contract. Inspect every listed item and preserve its specified selection state. The current configuration is limited to the actually selected SQL tables, KQL summary, model tables and Ontology entities. Do not add items through source discovery or expand beyond the contract."),
        _paragraph(
            "テーブル名や件数だけでなく各 path と type を実定義に照合します。IDを直接比較できない場合は現在の定義で binding を解決し、意味の差分が残れば停止します。選択状態の表示だけで、実際の問い合わせや回答品質を確認済みとは扱いません。",
            "Reconcile every path and type against the live definition, not only table names or counts. If IDs cannot be compared directly, resolve bindings from the current definition and stop if semantic differences remain. A visible selection does not verify actual queries or answer quality."),
    ])
    _append(chapter, 11, ("適用候補を安全に準備する", "Prepare the candidate safely"), [
        _paragraph(
            "prepare はリモートの変更を行わず、対象の既存 Agent を読み取り、ID-only binding を実定義と照合して、候補と private evidence を作成します。shared-field の実際の readback と complete-stage を確認し、予期しない意味差分があれば失敗として止まることを確認します。prepare の結果を見ずに apply へ進みません。",
            "prepare makes no remote changes. It reads the existing agent, resolves ID-only bindings against its live definition and writes the candidate and private evidence. Check actual shared-field readback and complete-stage; verify unexpected semantic drift causes a fail-closed stop. Do not proceed to apply without inspecting prepare output."),
        _steps([
            ("WorkspaceId・FolderId・AgentId は実際の許可済み環境から取得したGUIDを使います。PrivateRoot は絶対パスで指定し、全てのGit checkoutの外に置きます。RoutingOrigin は対象から観測した HTTPS regional analysis.windows.net のoriginだけを指定し、地域名やホストを推測しません。",
             "Use actual GUIDs for WorkspaceId, FolderId and AgentId from the authorized environment. Set PrivateRoot to an absolute path outside every Git checkout. RoutingOrigin must be the observed HTTPS regional analysis.windows.net origin for the target; never guess its region or host."),
            ("値は共有資料でなく、作業中の PowerShell 変数だけに設定します。PrivateRoot は新規で一意にし、既存の intent や記録を再利用・削除しません。prepare を実行し、出力された対象と候補を確認します。",
             "Set these values only in local PowerShell variables, not shared documents. Use a new unique PrivateRoot; do not reuse or delete existing intents or records. Run prepare and inspect the reported target and candidate."),
        ]),
        _code(
            '$WorkspaceId = "<authorized-workspace-guid>"\n'
            '$FolderId = "<authorized-folder-guid>"\n'
            '$AgentId = "<existing-agent-guid>"\n'
            '$PrivateRoot = "C:\\Users\\<you>\\Documents\\Furusato-private\\<unique-run>"\n'
            '$RoutingOrigin = "https://<observed-region>.analysis.windows.net"',
            "PowerShell",
        ),
        _code(
            _profile_command("prepare", "--routing-origin $RoutingOrigin"),
            "PowerShell",
        ),
    ])
    _append(chapter, 12, ("指示・選択・定義の差分を確認する", "Review instruction, selection and definition diffs"), [
        _paragraph(
            f"PrivateRoot 内の prepare receipt、candidate、definition/readback artifacts を確認し、manifest の全ファイルハッシュ、global の{assets['global_units']} UTF-16単位、各 source text/description、Ontology context、各 flat selection の path/type/is_selected、active few-shot file/example 数が資産に一致することを確かめます。readback では4つの論理ソースと3つの通常形式の物理 datasource record を区別し、native Ontology context を別に確認します。",
            f"Inspect the prepare receipt, candidate and definition/readback artifacts under PrivateRoot. Verify all manifest hashes, the {assets['global_units']}-UTF-16-unit global text, each source text/description, Ontology context, every flat selection path/type/is_selected and active few-shot file/example counts against the assets. Distinguish the four logical sources from three standard-format physical datasource records, and verify the natively serialized Ontology context separately."),
        _paragraph(
            "shared-field readbacks と complete-stage が全て一致し、停止条件がない場合だけ続行します。項目不足や意味差分を手で埋めず、Selection contractを書き換えて通過させません。",
            "Continue only when all shared-field readbacks and complete-stage checks match and no stop condition remains. Do not manually fill missing items or edit the selection contract to make checks pass."),
        _paragraph(
            "portable stage template は definition/ の5部品だけです。root・resource ID/name の token と、実際の path/type から解決する target token 以外は置き換えません。SQL の異なる列 path 間で native node ID が重複する場合があるため、UUID の一意性を前提にしません。schema、metadata、text、selection semantics の予期しない差分があれば helper は fail-closed で停止します。",
            "The portable stage template contains only the five parts under definition/. Replace only root/resource ID/name tokens and target tokens resolved from actual path/type. Native SQL node IDs can repeat across different column paths, so do not assume globally unique UUIDs. The helper fails closed on unexpected schema, metadata, text or selection-semantic differences."),
        *[
            _paragraph(f"Portable stage template: definition/{path.name}",
                       f"Portable stage template: definition/{path.name}")
            for path in assets["definition_files"]
        ],
        *[
            _code(path.read_text(encoding="utf-8"), "JSON", canonical=True)
            for path in assets["definition_files"]
        ],
    ])
    _append(chapter, 13, ("Draft へ一度だけ適用する", "Apply once to Draft"), [
        _paragraph(
            "直前の prepare で対象・差分・readback を確認してから、同じ既存 Agent の Draft に候補を一度だけ適用します。明示的な --apply がなければ書き込みません。apply intent は使い切りです。送信後に失敗・timeout・不明状態が起きても再送せず、intentを保持して読み取り専用 verify で実状態を調べます。",
            "After reviewing the target, diffs and readbacks from prepare, apply the candidate exactly once to Draft on the same existing agent. No write occurs without explicit --apply. The apply intent is single-use. After a failed, timed-out or uncertain submission, do not resend; preserve the intent and inspect live state with read-only verify."),
        _code(_profile_command("apply", "--apply"), "PowerShell"),
        _paragraph(
            "Draft の完全な shared-field readback と complete-stage の結果を確認します。失敗や不一致がある場合は停止し、公開しません。既存の Agent、Schema、Selection を作成・拡張する回避策を試しません。",
            "Inspect complete shared-field readback and complete-stage results for Draft. Stop and do not publish on failure or mismatch. Do not work around the problem by creating or expanding agents, schema or selections."),
    ])
    _append(chapter, 14, ("公開を一度だけ実施する", "Publish once"), [
        _paragraph(
            "Draft が完全に一致し、全ての事前条件と readback が通った場合に限り、同じ既存 Agent の公開を一度だけ実行します。明示的な --apply が必要です。publish intent を再利用・削除せず、応答不明や timeout のときは再送しません。",
            "Only after Draft fully matches and all prerequisites and readbacks pass, publish the same existing agent once. Explicit --apply is required. Do not reuse or delete the publish intent, and never resend after an uncertain response or timeout."),
        _code(_profile_command("publish", "--apply"), "PowerShell"),
    ])
    _append(chapter, 15, ("Draft と公開版を読み取り専用で検証する", "Verify Draft and publication read-only"), [
        _paragraph(
            "verify は read-only で、Draft または Published を明示して確認します。両方の段階を読み戻し、intent 結果、shared-field readbacks、complete-stage、4論理ソース、実指示全文・説明・Ontology context・全selectionを照合します。verifyの成功も、回答精度、Graph/GQL、時系列、mirror完全性を証明しません。",
            "verify is read-only and explicitly targets Draft or Published. Read back both stages and reconcile intent results, shared-field readbacks, complete-stage, four logical sources, exact instructions/descriptions/Ontology context and all selections. Successful verify does not establish answer accuracy, Graph/GQL, time-series support or mirror completeness."),
        _code(
            _profile_command("verify", "--stage draft") + "\n"
            + _profile_command("verify", "--stage published"),
            "PowerShell",
        ),
        _paragraph(
            "記録には自分の作業で得た実際の stage、状態、読み戻し、理由だけを残します。設定の readback と、実際に観測したSQL/KQL/DAX/GQL実行・結果・Agent回答を別にします。回答品質の採用・正確性・保証を主張しません。",
            "Record only the actual stage, status, readbacks and reasons from your own run. Keep configuration readback separate from observed SQL/KQL/DAX/GQL executions, results and Agent answers. Do not claim accepted, accurate or guaranteed answer quality."),
    ])
    _append(chapter, 16, ("復旧・制約・評価", "Recovery, limitations and evaluation"), [
        _steps([
            ("apply/publish の後に結果が不明なら、書込みを再送せず、その intent を保持して verify を読み取り専用で実行します。新しい変更が必要と判明しても、使用済みintentを再利用しません。所有者と現在の定義を確認した別手順に従います。",
             "If the outcome after apply/publish is uncertain, preserve the intent and run read-only verify; never resend the write. If a new change is needed, do not reuse the spent intent. Follow a separate procedure after confirming ownership and the live definition."),
            ("現在の実験では、ファイルごとの時刻の12時間転記が誤ることがあります。fixture 001 の最終時刻は 11:54:30 UTC（現地表記 11:54:30 AM）で、23:54:30 ではありません。fixture 003 の開始時刻は 14:18:14 UTC（2:18:14 PM）で、02:18:14 ではありません。集計 join が誤って全体合計を各ファイルの合計として扱い、誤った「データなし」を返すこともあります。回答を独立に評価するときは、各 fixture の開始・終了時刻、UTC表示、期間と分母の定義、集計の粒度と各ファイルの合計が混同されていないことを確認します。",
             "Current experimental responses can transpose timestamps by 12 hours. Fixture 001 ends at 11:54:30 UTC (native 11:54:30 AM), not 23:54:30. Fixture 003 starts at 14:18:14 UTC (2:18:14 PM), not 02:18:14. A generated aggregate join can also mistake a grand total for per-file totals and return a false “no data.” In an independent answer review, check each fixture's start/end time, UTC labeling, period and denominator definitions, aggregation grain, and that per-file totals are not confused."),
            ("高額寄付フラグの定義は寄付額が57,000円を超える場合（> 57,000円）であり、57,000円以上ではありません。回答がこの定義や、実際の measure にある KEEPFILTERS の説明を省くことがあります。支払方法ランキングでは filter が落ちる場合があります。回答が閾値の厳密な不等号、measure 所有の filter の適用、ランキング対象の filter を説明・適用しているかを独立に確認します。GQL・structured output・DAX の十分な実行根拠もありません。正確さを示すために指示へ答えを追加せず、実際の source/query/result と説明を照合し、未確認または誤りはそのまま記録します。",
             "The high-value flag means donation amount > JPY 57,000, not >= JPY 57,000. An answer may omit this definition or an explanation of the actual measure-owned KEEPFILTERS. A payment-method ranking can also drop its filter. Independently check the strict threshold predicate, whether the measure-owned filter is applied and explained, and whether the ranking's filter is retained. Sufficient GQL, structured-output and DAX execution evidence is also missing. Do not add answers to the instructions to make them seem correct; reconcile actual sources/queries/results and explanations, and record unknowns or errors as observed."),
            ("全ての回答を19章・付録Cで公開問題と条件により評価します。設定が一致しても、正確性や採用が示されたとは限りません。別の実環境におけるGraph model、GQL、時系列、mirroringは、それぞれ独立に前提と実行結果を確認します。",
             "Evaluate answers using the public questions and criteria in Chapter 19 and Appendix C. Matching configuration does not establish correctness or adoption. In any other environment, check Graph-model, GQL, time-series and mirroring prerequisites and execution results independently."),
        ]),
    ])
    return {
        "profile": PROFILE,
        "globalUtf16Units": assets["global_units"],
        "kqlFewshotCount": assets["active_example_count"],
        "selectionCount": len(assets["selection_rows"]),
        "logicalSources": assets["manifest"]["logicalSources"],
        "directSources": assets["manifest"]["directSources"],
    }


def _table(headers, rows, ja, en, *, canonical=False):
    payload = {
        "number": 0,
        "headers": [_text(str(value)) if isinstance(value, str) else _text(*value) for value in headers],
        "rows": [[_text(str(value)) if isinstance(value, str) else _text(*value) for value in row] for row in rows],
        "caption": _text(ja, en),
        "wide": True,
    }
    if canonical:
        payload["canonicalLiteral"] = True
    return Block("table", payload)
