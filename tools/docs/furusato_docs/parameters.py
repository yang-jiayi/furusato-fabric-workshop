"""Curated participant-facing documentation for every Notebook parameter.

The *default value* is never written here: it is read from the notebook parameter
cell at build time and injected into the table. This module only owns the prose
columns (participant action, meaning, default behaviour, safety gate, chapter).

``build_parameter_rows`` raises if a notebook gains or loses a parameter, so the
deliverables can never drift away from the shipped runtime.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .context import RuntimeContext

PARAMETER_COLUMNS = (
    "Parameter",
    "Type",
    "Default",
    "参加者の操作",
    "意味",
    "既定動作",
    "安全ゲート",
    "実施節",
)

#: When each Core parameter applies. ``always`` parameters are set on every run;
#: the stale-lease trio is only used during an explicit recovery and must be set
#: together, so the workbook and the guide state that condition next to them.
APPLIES_ALWAYS = "常に適用"
STALE_LEASE_GROUP = ("OPERATOR_RECOVER_STALE_LEASE", "STALE_LEASE_OWNER_RUN_ID", "STALE_LEASE_GENERATION")
APPLIES_STALE_LEASE = "stale lease 回復時のみ（3 つ同時に設定）"


def application_condition(name: str) -> str:
    """Return when a Core parameter applies."""
    return APPLIES_STALE_LEASE if name in STALE_LEASE_GROUP else APPLIES_ALWAYS


#: Where each notebook's full parameter table lives. The section is a property of
#: the notebook, not of the individual parameter, so it is declared once here and
#: printed into every row. That keeps the guide, the workbook and the appendix-B
#: index pointing at exactly the same place.
PARAMETER_SECTION = {
    "Notebook_01": "第 6.4 節",
    "Notebook_02": "第 15.2 節",
    "Notebook_03": "付録 D.1",
    "Notebook_04": "付録 D.2",
    "Notebook_05": "付録 D.3",
}


@dataclass(frozen=True)
class ParameterDoc:
    name: str
    type_label: str
    action: str
    meaning: str
    default_behaviour: str
    safety_gate: str


AUTOMATED_APPLY_DOC = ParameterDoc(
    "ALLOW_AUTOMATED_APPLY",
    "bool",
    "Jobs API で適用する場合だけ、preview 前に True",
    "対話実行に加えて、明示的に承認した自動実行を許可する。",
    "False のとき非対話実行からの書き込みを拒否する。",
    "正確な EXPECTED_WORKSPACE_NAME、変更後のプランハッシュ、排他宣言が必要。既存の検査は省略しない。",
)

UNIFIED_AGENT_DOC = ParameterDoc(
    "ENABLE_UNIFIED_DATA_AGENT",
    "bool",
    "統合文書版では最終 preview 前に True",
    "主 Agent 1 件・教材用 full Ontology・共有 SQL/KQL・Code Interpreter の統合モード。"
    "ProvisioningConfig の enable_unified_data_agent に対応する。",
    "False は旧呼び出し元との互換性を維持する。文書版 unified-20260923 は True を明示する。",
    "ENABLE_AI_REFERENCE_ARCHITECTURE と相互排他。固定済み profile・計画ハッシュ・排他作成を要求する。"
    "既存主 Agent は完全一致だけ再利用。不一致の旧 Core は別承認の段階的移行で扱い、自動上書き・自動 resume しない。",
)

UNIFIED_REFERENCE_DOCS = {
    "ENABLE_AI_REFERENCE_ARCHITECTURE": ParameterDoc(
        "ENABLE_AI_REFERENCE_ARCHITECTURE", "bool", "False のまま",
        "旧 AIReference / AIPath の独立プロファイル用。統合文書版の経路ではない。",
        "False のまま ENABLE_UNIFIED_DATA_AGENT=True を明示する。",
        "両方 True は拒否する。旧プロファイルへの切替や別 Agent の追加で統合モードの失敗を回避しない。",
    ),
    **{
        name: ParameterDoc(
            name, "str", "変更しない（旧参照モード専用）",
            "旧独立参照プロファイルの対象指定。統合モードの主 Agent を改名・移行するための値ではない。",
            "配布された既定値を保持し、この文書版では使用しない。",
            "主 Agent の実 ID と完全一致を別に確認する。不一致は停止し、第 16.9 節の承認工程へ戻る。",
        )
        for name in ("REFERENCE_AGENT_NAME", "REFERENCE_AGENT_ROLE", "REFERENCE_AGENT_EXPECTED_ID")
    },
}


NB01: tuple[ParameterDoc, ...] = (
    ParameterDoc(
        "NOTEBOOK_VERSION",
        "str",
        "変更しない",
        "Notebook が宣言する Workshop 契約バージョン。出力の READY 行と監査表に記録される。",
        "パッケージ版数と一致した状態で検証と発行を実行する。",
        "配布物と異なる値にすると版数不一致として扱われ、成果物の再現性が失われる。",
    ),
    ParameterDoc(
        "PARTICIPANT_ID",
        "str",
        "自分の 3 桁 PID に変更する",
        "参加者ごとの Lakehouse / Ontology / Eventhouse 名と一時テーブル接頭辞に使う識別子。",
        "既定値のままだと参加者 001 の資産名で実行してしまう。",
        "`(?!000$)[0-9]{3}` に一致しない値（000・空文字・4 桁以上）は assert で即停止する。",
    ),
    ParameterDoc(
        "INPUT_DIR",
        "str",
        "変更しない",
        "静的 8 CSV を読み取る Lakehouse の相対パス。",
        "`Files/furusato/seed` を検査し、8 ファイルの実在・UTF-8・ヘッダー・SHA-256 を照合する。",
        "`Files/` 配下の相対パス以外、および `..` を含むパスは assert で停止する。",
    ),
    ParameterDoc(
        "RUN_OPTIMIZE_VORDER",
        "bool",
        "変更しない（False のまま）",
        "発行後に OPTIMIZE / V-Order を実行するかどうかの要求フラグ。",
        "False のとき最適化を実行せず、検証済みの Delta を素早く公開する。",
        "True にしても意図的に最適化は実行されず、要求が拒否された旨を出力する。",
    ),
    ParameterDoc(
        "PUBLISH_LEASE_MINUTES",
        "int",
        "変更しない",
        "発行リースの有効期間（分）。同時実行から発行シーケンスを保護する。",
        "30 分のリースを取得し、長時間セルの間は自動更新する。",
        "15〜1440 の整数以外は assert で停止する。",
    ),
    ParameterDoc(
        "OPERATOR_RECOVER_STALE_LEASE",
        "bool",
        "通常は変更しない",
        "期限切れリースを引き継ぐ復旧モードの明示的な許可。",
        "False のとき、他 run のリースが残っていれば発行せず停止する。",
        "True でも OwnerRunId と Generation の完全一致が必要で、推測値では復旧できない。",
    ),
    ParameterDoc(
        "STALE_LEASE_OWNER_RUN_ID",
        "str",
        "復旧時のみ、出力された値を貼り付ける",
        "引き継ぐ対象リースの所有 run ID。",
        "空文字のとき復旧経路には入らない。",
        "復旧時に空文字だと停止し、リース行の OwnerRunId と一致しなければ復旧を拒否する。",
    ),
    ParameterDoc(
        "STALE_LEASE_GENERATION",
        "int",
        "復旧時のみ、出力された値を貼り付ける",
        "引き継ぐ対象リースの発行世代番号。",
        "-1 のとき復旧経路には入らない。",
        "1 以上かつ制御行の Generation と一致しなければ復旧を拒否する。",
    ),
)

NB02: tuple[ParameterDoc, ...] = (
    ParameterDoc(
        "PARTICIPANT_ID",
        "str",
        "自分の 3 桁 PID に変更する",
        "対象 Ontology 表示名を組み立てる参加者 ID。",
        "`ONT_Furusato_<PID>` を解決して、その 1 件だけを更新対象にする。",
        "Workspace 全体で解決できない、または複数一致する場合は更新せず停止する。Folder だけでは対象を限定しない。",
    ),
    ParameterDoc(
        "ONTOLOGY_DISPLAY_NAME",
        "str (f-string)",
        "変更しない",
        "更新対象 Ontology の表示名。PARTICIPANT_ID から自動生成される。",
        "現在の Workspace 内で表示名一致の Ontology を 1 件だけ解決する。",
        "名前を直接書き換えると、意図しない Ontology を更新する危険があるため PID 経由で指定する。",
    ),
    ParameterDoc(
        "EXPECTED_WORKSPACE_NAME",
        "str",
        "任意。自分の Workspace 名を入れると安全",
        "実行中の Workspace 名を突き合わせるガード。",
        "空文字のとき Workspace 名の照合を行わない。",
        "値を設定すると、実行中 Workspace 名と不一致の場合に更新前で停止する。",
    ),
    ParameterDoc(
        "APPLY_CHANGES",
        "bool",
        "1 回目は False、preview 確認後に True",
        "定義書き込みを行うかどうかの主スイッチ。",
        "False のとき `DRY_RUN_COMPLETE` を出力し、Fabric 定義を一切書き換えない。",
        "True 単独では書き込めない。確認フレーズと排他実行の宣言が同時に必要。",
    ),
    ParameterDoc(
        "APPLY_CONFIRMATION",
        "str",
        "適用時のみ `APPLY ONTOLOGY METADATA` を入力",
        "適用意図を示す完全一致の確認フレーズ。",
        "空文字のとき適用経路に入らない。",
        "定義済みフレーズと完全一致しなければ、書き込み直前で停止する。",
    ),
    ParameterDoc(
        "EXCLUSIVE_APPLY_WINDOW_CONFIRMED",
        "bool",
        "他の編集セッションを閉じてから True",
        "同じ Ontology を同時編集していないことの申告。",
        "False のとき適用経路に入らない。",
        "他タブでの Ontology 編集と競合すると更新が失われるため、明示宣言を必須にしている。",
    ),
    ParameterDoc(
        "OPERATION_TIMEOUT_SECONDS",
        "int",
        "変更しない",
        "getDefinition / updateDefinition の長時間操作を待つ上限秒数。",
        "600 秒まで完了をポーリングし、超過時は失敗として扱う。",
        "上限を超えた場合は成功と見なさず、成果を検証してから再実行させる。",
    ),
)

NB03: tuple[ParameterDoc, ...] = (
    ParameterDoc(
        "PARTICIPANT_ID",
        "str",
        "自分の 3 桁 PID に変更する",
        "作成する Ontology・参照する Lakehouse / Eventhouse 名の解決に使う。",
        "`ONT_Furusato_<PID>` を新規作成する計画を組み立てる。",
        "同名 Ontology は Workspace 全体で確認する。完全一致の定義なら no-op、異なる定義や複数一致なら停止する。",
    ),
    ParameterDoc(
        "EXPECTED_WORKSPACE_NAME",
        "str",
        "任意。自分の Workspace 名を入れると安全",
        "実行中の Workspace 名を突き合わせるガード。",
        "空文字のとき照合しない。",
        "不一致なら作成前に停止する。",
    ),
    ParameterDoc(
        "TARGET_FOLDER_NAME",
        "str",
        "通常は空のまま",
        "Ontology の作成先 Folder 名。参照元 item の検索範囲を Folder 内に限定する指定ではない。",
        "空文字のとき、この Notebook 自身と同じ場所に作成する。Notebook が Workspace 直下なら作成先も直下になる。",
        "Notebook ID を解決できない環境では Folder 名の明示指定が必要。指定名が Workspace 全体で一意でなければ停止する。",
    ),
    ParameterDoc(
        "CREATE_ONTOLOGY",
        "bool",
        "1 回目は False、preview 確認後に True",
        "createItem を実行するかどうかの主スイッチ。",
        "False のとき作成計画だけを出力する。",
        "True 単独では作成できない。確認値と排他実行の宣言が同時に必要。",
    ),
    ParameterDoc(
        "CREATE_CONFIRMATION",
        "str",
        "作成時のみ `yes` を入力",
        "作成意図を示す完全一致の確認値。",
        "空文字のとき作成経路に入らない。",
        "`yes` と完全一致しなければ作成前に停止する。",
    ),
    ParameterDoc(
        "EXCLUSIVE_CREATE_WINDOW_CONFIRMED",
        "bool",
        "他の作成操作がないことを確認して True",
        "同時作成による重複 Ontology を防ぐ申告。",
        "False のとき作成経路に入らない。",
        "重複作成は後段の解決を壊すため、明示宣言を必須にしている。",
    ),
    ParameterDoc(
        "OPERATION_TIMEOUT_SECONDS",
        "int",
        "変更しない",
        "createItem の長時間操作を待つ上限秒数。",
        "900 秒まで完了をポーリングする。",
        "超過時は成功と見なさず、Workspace 側の実体を確認させる。",
    ),
)

NB04: tuple[ParameterDoc, ...] = (
    ParameterDoc(
        "PARTICIPANT_ID",
        "str",
        "自分の 3 桁 PID に変更する",
        "一括構築するすべての item 名に付与する参加者 ID。",
        "対象 Folder 内で `<item>_<PID>` 名の item を計画する。",
        "対象 Folder 内に同名 item が重複していると fail-closed で停止する。",
    ),
    ParameterDoc(
        "EXPECTED_WORKSPACE_NAME",
        "str",
        "任意。自分の Workspace 名を入れると安全",
        "実行中の Workspace 名を突き合わせるガード。",
        "空文字のとき照合しない。",
        "不一致なら構築前に停止する。",
    ),
    ParameterDoc(
        "APPLY_CHANGES",
        "bool",
        "1 回目は False、preview 確認後に True",
        "実書き込みを行うかどうかの主スイッチ。",
        "False のとき計画と PLAN_SHA256 だけを出力する。",
        "計画ハッシュ・排他宣言・5 つの構成要素フラグがすべて揃わない限り書き込まない。",
    ),
    ParameterDoc(
        "CONFIRMED_PLAN_SHA256",
        "str",
        "preview で出力された値をそのまま貼り付ける",
        "承認した構築計画の指紋。",
        "空文字のとき適用経路に入らない。",
        "計画が 1 文字でも変われば不一致となり、再 preview を要求して停止する。",
    ),
    ParameterDoc(
        "EXCLUSIVE_CREATE_WINDOW_CONFIRMED",
        "bool",
        "他の構築操作がないことを確認して True",
        "同時構築による重複 item を防ぐ申告。",
        "False のとき適用経路に入らない。",
        "重複 item は後段の解決を壊すため、明示宣言を必須にしている。",
    ),
    ParameterDoc(
        "EXECUTE_NOTEBOOK_01",
        "bool",
        "最終 preview の前に True",
        "指定した PID と Default Lakehouse を設定した Notebook 01 のコピーを、子ジョブとして実行するかどうか。",
        "False のとき Lakehouse テーブルを生成しない。",
        "フラグの組み合わせは PLAN_SHA256 に含まれるため、変更すると計画ハッシュが変わる。",
    ),
    ParameterDoc(
        "CREATE_PIPELINE",
        "bool",
        "最終 preview の前に True",
        "増分取り込み用 Data Pipeline を作成するかどうか。",
        "False のとき Pipeline を作成しない。",
        "作成のみで実行はしない。Pipeline の起動は常に明示操作。",
    ),
    ParameterDoc(
        "REFRESH_GRAPH",
        "bool",
        "最終 preview の前に True",
        "Ontology の Graph モデルを更新するかどうか。",
        "False のとき Graph 更新を実行しない。",
        "更新は長時間操作として上限時間内で検証される。",
    ),
    ParameterDoc(
        "CREATE_DATA_AGENT",
        "bool",
        "最終 preview の前に True",
        "3 source の Data Agent を作成するかどうか。",
        "False のとき Data Agent を作成しない。",
        "参照先・選択済み要素・指示・説明が配布バンドルと一致することを確認する。UI 内部 ID だけの変化と混同しない。",
    ),
    ParameterDoc(
        "CREATE_REFLEX",
        "bool",
        "最終 preview の前に True",
        "OneLake FileCreated トリガー用の Reflex（Activator）を作成するかどうか。",
        "False のとき Reflex を作成しない。",
        "作成されるのは Pipeline を起動する FileCreated トリガーのみ。無効状態・通知先なしで出荷され、有効化は参加者の明示操作。",
    ),
    ParameterDoc(
        "OPERATION_TIMEOUT_SECONDS",
        "int",
        "初回構築では preview 前に 2700 を指定する",
        "Notebook 01 の子ジョブ、SQL 同期、Graph 更新など、各長時間操作を待つ上限秒数。",
        "各操作を設定値までポーリングする。初回構築は 15 分を超える場合があるため、2700 秒 (45 分) を目安に実行環境へ合わせる。",
        "POLL_INTERVAL_SECONDS より小さい値は拒否される。タイムアウトしてもジョブは自動キャンセルされないため、既存ジョブ ID の状態を確認し、実行中のジョブを再送しない。",
    ),
    ParameterDoc(
        "POLL_INTERVAL_SECONDS",
        "int",
        "変更しない",
        "長時間操作の状態を確認する間隔（秒）。",
        "10 秒ごとに状態を確認する。",
        "許容範囲外の値、および timeout より大きい値は拒否される。",
    ),
    ParameterDoc(
        "ENABLE_AI_REFERENCE_ARCHITECTURE",
        "bool",
        "通常は False。承認した参照候補だけ True",
        "教材用 full Ontology を残し、別 AIPath と SQL/KQL 参照ソースを使う検証用構成の opt-in。",
        "False のとき参照構成を有効にせず、Core 基線を使う。",
        "True では固定済み GLOBAL の SHA-256 と candidate / accepted 宣言が必須。"
        "不足は認証前に停止し、Core へフォールバックしない。宣言は品質承認ではない。",
    ),
    ParameterDoc(
        "REFERENCE_AGENT_NAME",
        "str",
        "通常は空。許可された既存候補の再利用時だけ正確な名前",
        "参照候補 Data Agent の表示名。教材用 Core とは別の対象。",
        "空文字の参照モードでは `DA_Furusato_AIReference_<PID>` を使う。",
        "Core 名・前後空白・制御文字は拒否。独自名は `authorized-candidate` と実 GUID が必要で、"
        "構成不一致は上書きしない。",
    ),
    ParameterDoc(
        "REFERENCE_AGENT_ROLE",
        "str",
        "通常は `isolated-reference`。許可済み既存候補だけ `authorized-candidate`",
        "既定の独立候補と、明示的に許可された既存候補の再利用を区別する。",
        "`isolated-reference` は既定名だけを使い、ID の上書きを受け付けない。",
        "未定義 role は拒否。`authorized-candidate` は名前・実 GUID・構成の完全一致を要求。"
        "Core 昇格は対象外。",
    ),
    ParameterDoc(
        "REFERENCE_AGENT_EXPECTED_ID",
        "str",
        "通常は空。再利用時だけ discovery で得た実 GUID を設定",
        "許可された既存候補の item ID を固定し、名前だけの一致を防ぐ。",
        "空文字の `isolated-reference` では既定の独立候補を対象にする。",
        "`authorized-candidate` は正確な名前・実 GUID が必須。"
        "参照モード False や `isolated-reference` で ID を指定すると停止。",
    ),
    AUTOMATED_APPLY_DOC,
    ParameterDoc(
        "USE_PARTICIPANT_NOTEBOOK_NAMES",
        "bool",
        "同一 Workspace に複数参加者を配置するとき、preview 前に True",
        "生成する Notebook 01 の名前に参加者 ID の接尾辞を付ける。",
        "False のとき配布版の Notebook 01 名を使う。",
        "名前の変更はプランハッシュに含まれる。既存参加者の同名 Notebook を上書きしない。",
    ),
    UNIFIED_AGENT_DOC,
)

NB05: tuple[ParameterDoc, ...] = (
    ParameterDoc(
        "PARTICIPANT_ID",
        "str",
        "自分の 3 桁 PID に変更する",
        "対象 Lakehouse と生成する分析 item の解決に使う参加者 ID。",
        "自分の Lakehouse に bronze/silver/gold/ops/quarantine を追加する計画を組み立てる。",
        "既存の `stg_*` / `ot_*` テーブルは保持され、上書きされない。",
    ),
    ParameterDoc(
        "EXPECTED_WORKSPACE_NAME",
        "str",
        "任意。自分の Workspace 名を入れると安全",
        "実行中の Workspace 名を突き合わせるガード。",
        "空文字のとき照合しない。",
        "不一致なら実行前に停止する。",
    ),
    ParameterDoc(
        "INCREMENT_PATH",
        "str",
        "変更しない",
        "増分 CSV を読み取る Lakehouse パス。",
        "`Files/increment` の 3 ファイルを読み、重複 EventID を quarantine する。",
        "`Files/` 配下以外、および `..` を含むパスは拒否される。",
    ),
    ParameterDoc(
        "APPLY_CHANGES",
        "bool",
        "1 回目は False、preview 確認後に True",
        "実テーブル生成を行うかどうかの主スイッチ。",
        "False のとき計画と PLAN_SHA256 だけを出力する。",
        "計画ハッシュと排他宣言が揃わない限り書き込まない。",
    ),
    AUTOMATED_APPLY_DOC,
    ParameterDoc(
        "CONFIRMED_PLAN_SHA256",
        "str",
        "preview で出力された値をそのまま貼り付ける",
        "承認した実行計画の指紋。",
        "空文字のとき適用経路に入らない。",
        "計画が変わると不一致で停止し、再 preview を要求する。",
    ),
    ParameterDoc(
        "EXCLUSIVE_APPLY_WINDOW_CONFIRMED",
        "bool",
        "他の書き込みセッションを閉じてから True",
        "同一 Lakehouse への同時書き込みがないことの申告。",
        "False のとき適用経路に入らない。",
        "同時書き込みは公開状態を壊すため、明示宣言を必須にしている。",
    ),
    ParameterDoc(
        "STRICT_SYNTHETIC_CONTRACT",
        "bool",
        "配布データではそのまま True",
        "時刻ルールを合成データの承認済み観測窓で検証するかどうか。",
        "True のとき dataset-manifest.json の 2026 年 8 月 UTC 窓で検証し、配布行を quarantine しない。",
        "False にすると実行時の壁時計を基準にした未来時刻ガードへ切り替わる。",
    ),
    ParameterDoc(
        "OPERATOR_RECOVER_INTERRUPTED_RUN",
        "bool",
        "通常は変更しない",
        "中断した run の後始末を許可する復旧モード。",
        "False のとき、中断世代が残っていれば実行せず停止する。",
        "制御テーブルが中断を証明する場合にのみ使用し、値の推測は禁止。",
    ),
    ParameterDoc(
        "INTERRUPTED_RUN_ID",
        "str",
        "復旧時のみ、制御行の値を貼り付ける",
        "引き継ぐ中断 run の ID。",
        "空文字のとき復旧経路には入らない。",
        "制御行の RunId と完全一致しなければ復旧を拒否する。",
    ),
)

CATALOG: dict[str, tuple[ParameterDoc, ...]] = {
    "Notebook_01": NB01,
    "Notebook_02": NB02,
    "Notebook_03": NB03,
    "Notebook_04": NB04,
    "Notebook_05": NB05,
}


def format_default(value: Any) -> str:
    if isinstance(value, bool):
        return "True" if value else "False"
    if isinstance(value, str):
        if value == "":
            return '"" (空文字)'
        if value.startswith("f\"") or value.startswith("f'"):
            return value
        return f'"{value}"'
    return str(value)


def build_parameter_rows(context: RuntimeContext, notebook_key: str) -> list[list[str]]:
    """Return one documentation row per parameter, with defaults taken from the notebook."""
    notebook = context.notebooks[notebook_key]
    docs = CATALOG[notebook_key]
    if notebook_key == "Notebook_04":
        if UNIFIED_AGENT_DOC.name not in notebook.parameters:
            if context.is_unified_guide:
                raise ValueError("The unified guide requires Notebook 04 with ENABLE_UNIFIED_DATA_AGENT.")
            docs = tuple(doc for doc in docs if doc.name != UNIFIED_AGENT_DOC.name)
        if context.is_unified_guide:
            docs = tuple(UNIFIED_REFERENCE_DOCS.get(doc.name, doc) for doc in docs)
    documented = {doc.name for doc in docs}
    actual = set(notebook.parameters)
    if documented != actual:
        missing = sorted(actual - documented)
        extra = sorted(documented - actual)
        raise ValueError(
            f"{notebook_key} parameter documentation drift; undocumented={missing} stale={extra}"
        )
    rows: list[list[str]] = []
    section = PARAMETER_SECTION[notebook_key]
    for doc in docs:
        rows.append(
            [
                doc.name,
                doc.type_label,
                format_default(notebook.parameters[doc.name]),
                doc.action,
                doc.meaning,
                doc.default_behaviour,
                doc.safety_gate,
                section,
            ]
        )
    return rows
