# Data Agent configuration and response checks

The current participant procedure is the [3.1.0 bilingual HTML guide](furusato-workshop-v3-1-0-complete.html#ch-17), with the numbered [Chapter 17 GitHub Lab](../Lab/17-fabric-data-agent-and-code-interpreter/README.md) and matching [participant ZIP](Furusato_Workshop_v3.1.0_current.zip).

## 日本語

主 Agent **`DA_Furusato_<PID>` 1件**で4つの論理ソース（Lakehouse、KQL Database、Semantic model、Ontology）を確認します。Code Interpreter は同じ Agent で使うツールであり、ソースではありません。正確な選択と読戻しは[参加者ガイド第17章](furusato-workshop-v3-1-0-complete.html#ch-17)を参照してください。

| ソース・ツール | 使う対象 | 確認する境界 |
|---|---|---|
| Lakehouse SQL | 11 `ot_*` テーブル、参照 view 1件、TVF 2件 | 静的データの属性・寄付件数・金額・順位。寄付者居住地と受取自治体を区別する |
| Eventhouse KQL | 承認済み MV 1件、集計関数 3件 | raw観測件数・金額・期間・ファイル／実行単位の内訳。重複を含む可能性を保持する |
| Semantic model | 選択済みのモデル、関係、メジャー | DAX を使う場合は実際のモデル名と返却列を確認し、他ソースの結果と混同しない |
| Ontology | 完全な教材モデル1件：10 Entity、72 static Property、1 time-series Property、15 Relationship | 実際の関係経路・向き・識別子・関係に基づく件数を確認する |
| Code Interpreter（ツール） | 成功したソース結果の分析・図・CSV／JSON出力 | ソースではなく、未取得データや未実行の関係経路を補わない |

新規一括構築は、Notebook 04 の最終 preview 前に
`ENABLE_UNIFIED_DATA_AGENT=True`、`ENABLE_AI_REFERENCE_ARCHITECTURE=False` を設定します。
データとヘルパーを同じ Lakehouse／Eventhouse で共有し、別の Agent や AIPath を追加しません。
既存 Agent の設定が配布定義と異なる場合は停止し、バックアップ・Draft 検証・公開の順に変更します。
完了済み環境で Notebook 04 を再実行して、指示だけを更新しようとしないでください。

### 回答を確認するポイント

- **出典と対象範囲:** Source・Scope・Metric・Unit を確認します。順位は全国か県内か、件数か金額かを区別します。
- **粒度と時刻:** Static 2025 UTC snapshot はデータセットのラベルで、JST 暦年フィルターではありません。静的寄付と raw 観測を合算せず、UTC の実観測時刻と指定期間を区別します。
- **ゼロと取得不能:** 有効な照会が返した0は保持します。失敗や未取得を0にせず、分単位の集約から秒単位の厳密値を推測しません。
- **関係の証拠:** 所属件数や経路は同じ実行の Ontology 結果で確認します。カタログ登録を製造・配送実績と解釈せず、返礼品の選択を受領済みとも断定しません。属性と ID は正しい役割で保持します。
- **列名と出典:** SQL helper の22／30列、KQL helper の14／17／15列は元の名前・値を保持します。導出した件数順位を保存済み順位へ改名せず、`HasMatches` などの存在しない返却列や、手作りの能力判定を証拠にしません。追加属性は実際に照会した所有ソースへ帰属させます。
- **安全な拒否:** 寄付額から個人の年収・控除額を推定しないことは期待する動作です。拒否文の形式と、禁止された推論を行わないことは分けて確認します。

「お金持ち」「貧しい人」「納税額の順位」は寄付額から判断できません。Agent には、照会できる寄付データの質問へ言い直し、**対象・期間・指標を埋めた1つの案**を提示して同意を待つよう指示しています。

「はい」は直前の有効な提案にだけ同意します。対象を変更する場合は案を再確認し、取消後の「はい」で古い照会を再開しません。別の明確な質問は通常どおり扱います。一般的な拒否だけで具体的な案がない場合、同意する対象もありません。

この動きは Agent の指示によるもので、外部の強制制御ではありません。[第17章の同意手順](furusato-workshop-v3-1-0-complete.html#ch-17)に従い、確認前に実際のソース照会・CI 実行がないこと、同意後の条件が最後の案と一致することを実行詳細で確認してください。サービス側の安全判断で拒否される場合もあります。

### 図とファイルを確認する

ソース照会が成功してから、実際に返されたファイル・行・列を Code Interpreter へ渡します。全母集団の図は、必要な全行が揃っている場合だけ作成します。日本語グリフ・軸・単位・全点の保持を確認し、名前が読めない場合は ID と CSV の名称対応を使います。

`Succeeded` やリンクの表示だけでは、ファイル取得成功とは判定しません。必要な CSV／JSON・PNG を実際に開き、値・列・時刻・出典を照合します。Office 出力は明示的に必要な場合に限り、取得制限があれば記録し、保護を回避しません。実行証跡には native の実行済み Python・入力・出力を使い、再構成されたコード概要を代用しません。

入力ファイルのアップロードだけで取り込み成功と判断せず、Pipeline の実行履歴と実データの件数・金額を確認します。初期化済みファイルを無断で再投入しないでください。

元の10問・84条件と CI 演習を、参加者ガイドに従って別々に記録します。同じ実行の証拠がない項目は未確認とし、設定変更後は元の10問すべてと CI 演習を再評価します。製品の応答や機能は更新されるため、教材はすべての環境での成功や全問正答を保証しません。

## English

Use **one primary `DA_Furusato_<PID>`** with four logical sources (Lakehouse,
KQL Database, semantic model and Ontology). Code Interpreter is a tool in the same
Agent, not a source. Follow the exact selections and readback in the
[Chapter 17 guide](furusato-workshop-v3-1-0-complete.html#ch-17) and
[Chapter 17 Lab](../Lab/17-fabric-data-agent-and-code-interpreter/README.md).

| Source or tool | Purpose | Boundary |
|---|---|---|
| Lakehouse SQL | 11 `ot_*` tables, one reference view and two TVFs | Static attributes, donation counts, amounts and ranks; distinguish donor residence from recipients |
| Eventhouse KQL | One approved MV and three aggregate functions | Raw observations, amounts, periods and file/run breakdowns; preserve the possible-duplicates qualification |
| Semantic model | The selected model, relationships and measures | When using DAX, verify actual model names and returned columns; keep results distinct from other sources |
| Ontology | One complete teaching model: 10 entities, 72 static properties, one time-series property and 15 relationships | Actual relationship paths, directions, IDs and relationship counts |
| Code Interpreter (tool) | Analysis, charts and CSV/JSON from successful source results | Not a source or a replacement for missing data or unexecuted paths |

For new deployment, explicitly set `ENABLE_UNIFIED_DATA_AGENT=True` and
`ENABLE_AI_REFERENCE_ARCHITECTURE=False` before Notebook 04's final preview.
Reuse the same data and helpers; do not create extra Agents or AIPath.
Stop if an existing Agent differs from the distributed definition. Back it up,
validate a Draft, and publish only after checking results. Do not rerun the
full provisioning Notebook merely to update instructions.

Check Source, Scope, Metric and Unit in answers; distinguish nationwide from
within-prefecture ranks and count from amount. The Static 2025 UTC snapshot
label is not a JST calendar-year filter. Never add static donations to raw
observations. Distinguish actual observation times from requested UTC bounds,
valid zero results from unavailable queries, and minute aggregates from
unsupported exact sub-minute allocations.

Verify relationship counts and paths using the same run's actual Ontology
results. Catalog registration does not prove manufacturing or delivery, and gift
selection does not prove receipt. Retain IDs and attributes in their proper roles.
Refusing to infer personal income or deductions is expected; assess refusal
wording separately from whether prohibited inference was prevented.

Preserve the SQL helpers' 22/30-column and KQL helpers' 14/17/15-column results
with their original names and values. Do not rename a derived count rank as a
stored rank, invent a returned `HasMatches` field, or treat authored capability
labels as evidence. Attribute extra properties to the owner actually queried.

For person wealth, poverty or tax rankings, the Agent is instructed to propose
one answerable donation-data question with a filled population, period and metric,
then wait for consent. A yes approves only the latest valid proposal. Changing
the request requires a revised proposal and confirmation. Cancellation clears it;
a later bare yes must not resume that query. Unrelated clear questions run
normally, and a generic refusal alone does not establish a pending proposal.
This is an instruction-driven policy, not external enforcement. Follow the
consent procedure in [Chapter 17](furusato-workshop-v3-1-0-complete.html#ch-17)
to inspect that no source query or CI runs before consent and that the actual
conditions after consent match the last proposal.

After a successful source query, pass only the returned files, rows and columns
to Code Interpreter. Create a full-population chart only when all required rows
are present. Verify glyphs, axes, units and point coverage; use IDs and CSV
name mappings when names are unreadable. A `Succeeded` label or link alone does
not prove file retrieval; open the CSV/JSON or PNG and verify values, columns,
times and sources. Do not bypass output protection or replay initialized inputs.

Record the standard 10 questions/84 conditions and CI exercises separately.
Mark conditions without evidence from the same run as unverified. After a
configuration change, reevaluate all standard questions and CI exercises.
Product behavior changes; the workshop does not guarantee success in every
environment or perfect answers.
