# B.1 パラメーター

[Lab 目次](../README.md) · [この章の目次](README.md)

Notebook 01〜05 のパラメーターと、配布時の初期値の一覧です。通常の手作業の演習で変更するのは、Notebook 01 と 05 の PARTICIPANT_ID と、Notebook 05 の適用時の設定だけです。

Notebook 02〜04 は自動配置の別インターフェイスです。標準経路は24.4以降のCLIを使います。書き込みは、実際の計画と作業範囲を確認し、24.5で承認してから行います。

**Notebook のパラメーター**

| Notebook | パラメーター | 既定値 | 意味 |
| --- | --- | --- | --- |
| Notebook 01 | NOTEBOOK_VERSION | '3.0.0' | Notebook の配布版（3.0.0）。出力の READY の行に記録されます。変更しません。 |
| Notebook 01 | PARTICIPANT_ID | '001' | 自分の3桁の参加者ID（001〜999）。アイテム名や対象の特定に使います。既定の 001 が自分の ID でなければ、そのまま実行しません。 |
| Notebook 01 | INPUT_DIR | 'Files/furusato/seed' | 静的データの8つの CSV を読む Lakehouse のフォルダー（Files/furusato/seed）。変更しません。 |
| Notebook 01 | RUN_OPTIMIZE_VORDER | False | 書き込み後の最適化の要求。False のままにします。 |
| Notebook 01 | PUBLISH_LEASE_MINUTES | 30 | テーブルを発行している間のロック（リース）の有効時間（分、15〜1440）。変更しません。 |
| Notebook 01 | OPERATOR_RECOVER_STALE_LEASE | False | 前回の実行が途中で止まり、ロックが残っている場合の復旧の許可。通常は False です。講師と一緒に、次の2つのパラメーターと同時に設定します。 |
| Notebook 01 | STALE_LEASE_OWNER_RUN_ID | '' | 復旧のときだけ、エラーに表示された OwnerRunId の値を貼り付けます。通常は空欄です。 |
| Notebook 01 | STALE_LEASE_GENERATION | -1 | 復旧のときだけ、エラーに表示された Generation の値（世代番号）を貼り付けます。通常は -1 です。 |
| Notebook 02 | PARTICIPANT_ID | '001' | 自分の3桁の参加者ID（001〜999）。アイテム名や対象の特定に使います。既定の 001 が自分の ID でなければ、そのまま実行しません。 |
| Notebook 02 | ENVIRONMENT | '' | dev・test・prod のいずれかを明示します。空欄のままでは実行されません。 |
| Notebook 02 | EXPECTED_WORKSPACE_NAME | '' | 実行するワークスペースの正確な表示名。Notebook 02〜04 では必須です。Notebook 05 では、自動実行（ALLOW_AUTOMATED_APPLY = True）のときに指定します。 |
| Notebook 02 | SCOPE_FILE | '' | 配置の範囲（ワークスペース、フォルダー、参加者ID）を記した JSON ファイルのパス。講師から受け取り、Notebook のリソース（builtin フォルダー）に置きます（24章）。共有しません。 |
| Notebook 02 | PLAN_FILE | '' | preflight で作られた resource-plan.json のパス。古い計画を使い回しません。 |
| Notebook 02 | WRITE_GATE_FILE | '' | 24.5で実際の計画を確認して承認した write-gate.json のパス。計画・範囲のハッシュを変更しません。 |
| Notebook 02 | PRIVATE_EVIDENCE_DIR | '' | 実行記録（計画や結果）を保存するフォルダー。段階をまたいで同じフォルダーを使い、共有しません。 |
| Notebook 02 | ACTION | 'preview-metadata' | 実行する段階。既定は Notebook 02 が preview-metadata、03 が deploy-core、04 が preflight です。Notebook 02 では apply-metadata、03 では verify-sources も指定できます。04 の段階は24章を参照します。 |
| Notebook 02 | APPLY_CHANGES | False | False ならプレビューだけを行います。確認した計画を適用するときだけ True にします。 |
| Notebook 02 | ALLOW_AUTOMATED_APPLY | False | Jobs API などによる自動実行で、適用を許可する追加の設定。画面から実行する場合は False のままにします。 |
| Notebook 02 | CONFIRMED_PLAN_SHA256 | '' | 確認した計画のハッシュを、そのまま貼り付けます。Notebook 02〜04 では preflight の planSha256、Notebook 05 ではプレビューの PLAN_SHA256 です。計画が変わったら、やり直します。 |
| Notebook 02 | RUN_NOTEBOOK01 | False | deploy-sources で Notebook 01 を実行するかどうか。完了済みの Notebook 01 は再実行されません。 |
| Notebook 02 | EXPECTED_DEFINITION_SHA256 | '' | 適用前に確認した Ontology の定義のハッシュ。Notebook 02 のプレビューの出力にある beforeDefinitionSha256 を貼り付けます。定義が変わっていた場合は、適用せずに止まります。 |
| Notebook 02 | RULE_STATEMENT_OVERRIDES | {} | 講師が承認した Rule の文の変更だけを指定します。通常は空（{}）です。Rules は通知や処理を実行しません。 |
| Notebook 03 | PARTICIPANT_ID | '001' | 自分の3桁の参加者ID（001〜999）。アイテム名や対象の特定に使います。既定の 001 が自分の ID でなければ、そのまま実行しません。 |
| Notebook 03 | ENVIRONMENT | '' | dev・test・prod のいずれかを明示します。空欄のままでは実行されません。 |
| Notebook 03 | EXPECTED_WORKSPACE_NAME | '' | 実行するワークスペースの正確な表示名。Notebook 02〜04 では必須です。Notebook 05 では、自動実行（ALLOW_AUTOMATED_APPLY = True）のときに指定します。 |
| Notebook 03 | SCOPE_FILE | '' | 配置の範囲（ワークスペース、フォルダー、参加者ID）を記した JSON ファイルのパス。講師から受け取り、Notebook のリソース（builtin フォルダー）に置きます（24章）。共有しません。 |
| Notebook 03 | PLAN_FILE | '' | preflight で作られた resource-plan.json のパス。古い計画を使い回しません。 |
| Notebook 03 | WRITE_GATE_FILE | '' | 24.5で実際の計画を確認して承認した write-gate.json のパス。計画・範囲のハッシュを変更しません。 |
| Notebook 03 | PRIVATE_EVIDENCE_DIR | '' | 実行記録（計画や結果）を保存するフォルダー。段階をまたいで同じフォルダーを使い、共有しません。 |
| Notebook 03 | ACTION | 'deploy-core' | 実行する段階。既定は Notebook 02 が preview-metadata、03 が deploy-core、04 が preflight です。Notebook 02 では apply-metadata、03 では verify-sources も指定できます。04 の段階は24章を参照します。 |
| Notebook 03 | APPLY_CHANGES | False | False ならプレビューだけを行います。確認した計画を適用するときだけ True にします。 |
| Notebook 03 | ALLOW_AUTOMATED_APPLY | False | Jobs API などによる自動実行で、適用を許可する追加の設定。画面から実行する場合は False のままにします。 |
| Notebook 03 | CONFIRMED_PLAN_SHA256 | '' | 確認した計画のハッシュを、そのまま貼り付けます。Notebook 02〜04 では preflight の planSha256、Notebook 05 ではプレビューの PLAN_SHA256 です。計画が変わったら、やり直します。 |
| Notebook 03 | RUN_NOTEBOOK01 | False | deploy-sources で Notebook 01 を実行するかどうか。完了済みの Notebook 01 は再実行されません。 |
| Notebook 03 | EXPECTED_DEFINITION_SHA256 | '' | 適用前に確認した Ontology の定義のハッシュ。Notebook 02 のプレビューの出力にある beforeDefinitionSha256 を貼り付けます。定義が変わっていた場合は、適用せずに止まります。 |
| Notebook 03 | RULE_STATEMENT_OVERRIDES | {} | 講師が承認した Rule の文の変更だけを指定します。通常は空（{}）です。Rules は通知や処理を実行しません。 |
| Notebook 04 | PARTICIPANT_ID | '001' | 自分の3桁の参加者ID（001〜999）。アイテム名や対象の特定に使います。既定の 001 が自分の ID でなければ、そのまま実行しません。 |
| Notebook 04 | ENVIRONMENT | '' | dev・test・prod のいずれかを明示します。空欄のままでは実行されません。 |
| Notebook 04 | EXPECTED_WORKSPACE_NAME | '' | 実行するワークスペースの正確な表示名。Notebook 02〜04 では必須です。Notebook 05 では、自動実行（ALLOW_AUTOMATED_APPLY = True）のときに指定します。 |
| Notebook 04 | SCOPE_FILE | '' | 配置の範囲（ワークスペース、フォルダー、参加者ID）を記した JSON ファイルのパス。講師から受け取り、Notebook のリソース（builtin フォルダー）に置きます（24章）。共有しません。 |
| Notebook 04 | PLAN_FILE | '' | preflight で作られた resource-plan.json のパス。古い計画を使い回しません。 |
| Notebook 04 | WRITE_GATE_FILE | '' | 24.5で実際の計画を確認して承認した write-gate.json のパス。計画・範囲のハッシュを変更しません。 |
| Notebook 04 | PRIVATE_EVIDENCE_DIR | '' | 実行記録（計画や結果）を保存するフォルダー。段階をまたいで同じフォルダーを使い、共有しません。 |
| Notebook 04 | ACTION | 'preflight' | 実行する段階。既定は Notebook 02 が preview-metadata、03 が deploy-core、04 が preflight です。Notebook 02 では apply-metadata、03 では verify-sources も指定できます。04 の段階は24章を参照します。 |
| Notebook 04 | APPLY_CHANGES | False | False ならプレビューだけを行います。確認した計画を適用するときだけ True にします。 |
| Notebook 04 | ALLOW_AUTOMATED_APPLY | False | Jobs API などによる自動実行で、適用を許可する追加の設定。画面から実行する場合は False のままにします。 |
| Notebook 04 | CONFIRMED_PLAN_SHA256 | '' | 確認した計画のハッシュを、そのまま貼り付けます。Notebook 02〜04 では preflight の planSha256、Notebook 05 ではプレビューの PLAN_SHA256 です。計画が変わったら、やり直します。 |
| Notebook 04 | RUN_NOTEBOOK01 | False | deploy-sources で Notebook 01 を実行するかどうか。完了済みの Notebook 01 は再実行されません。 |
| Notebook 04 | EXPECTED_DEFINITION_SHA256 | '' | 適用前に確認した Ontology の定義のハッシュ。Notebook 02 のプレビューの出力にある beforeDefinitionSha256 を貼り付けます。定義が変わっていた場合は、適用せずに止まります。 |
| Notebook 04 | RULE_STATEMENT_OVERRIDES | {} | 講師が承認した Rule の文の変更だけを指定します。通常は空（{}）です。Rules は通知や処理を実行しません。 |
| Notebook 05 | PARTICIPANT_ID | '001' | 自分の3桁の参加者ID（001〜999）。アイテム名や対象の特定に使います。既定の 001 が自分の ID でなければ、そのまま実行しません。 |
| Notebook 05 | EXPECTED_WORKSPACE_NAME | '' | 実行するワークスペースの正確な表示名。Notebook 02〜04 では必須です。Notebook 05 では、自動実行（ALLOW_AUTOMATED_APPLY = True）のときに指定します。 |
| Notebook 05 | INCREMENT_PATH | 'Files/increment' | 8月の観測データの3つの CSV を読む Lakehouse のフォルダー（Files/increment）。変更しません。 |
| Notebook 05 | APPLY_CHANGES | False | False ならプレビューだけを行います。確認した計画を適用するときだけ True にします。 |
| Notebook 05 | ALLOW_AUTOMATED_APPLY | False | Jobs API などによる自動実行で、適用を許可する追加の設定。画面から実行する場合は False のままにします。 |
| Notebook 05 | CONFIRMED_PLAN_SHA256 | '' | 確認した計画のハッシュを、そのまま貼り付けます。Notebook 02〜04 では preflight の planSha256、Notebook 05 ではプレビューの PLAN_SHA256 です。計画が変わったら、やり直します。 |
| Notebook 05 | EXCLUSIVE_APPLY_WINDOW_CONFIRMED | False | 同じ Lakehouse に書き込む他のセッションが無いことの確認。他のセッションを閉じてから True にします。 |
| Notebook 05 | STRICT_SYNTHETIC_CONTRACT | True | 配布データの観測期間（2026年8月、UTC）で時刻を検証します。配布データでは True のままにします。 |
| Notebook 05 | OPERATOR_RECOVER_INTERRUPTED_RUN | False | 前回の実行が途中で止まった場合の復旧の許可。通常は False です。前のセッションが止まっていることを確認してから使います。 |
| Notebook 05 | INTERRUPTED_RUN_ID | '' | 復旧のときだけ、エラーに表示された RunId を貼り付けます。通常は空欄です。 |

> 値を推測して入力しません。ハッシュや RunId などは、出力やエラーに表示された値をそのままコピーします。

> 範囲のファイル、承認のファイル、実行記録には、ワークスペースやアイテムの ID が含まれます。共有する資料に含めません。

<details>
<summary>English</summary>

## B.1 Parameters

This is the list of Notebook 01–05 parameters and their distributed defaults. In the normal manual labs you change only PARTICIPANT_ID in Notebooks 01 and 05 and the apply settings in Notebook 05.

Notebooks 02–04 are alternative interfaces to automated deployment. The standard route uses the CLI from 24.4 onward. Writes require review of the actual plan and scope and authorization in 24.5.

**Notebook parameters**

| Notebook | Parameter | Default | Meaning |
| --- | --- | --- | --- |
| Notebook 01 | NOTEBOOK_VERSION | '3.0.0' | Distributed Notebook edition (3.0.0), recorded in the READY output line. Do not change it. |
| Notebook 01 | PARTICIPANT_ID | '001' | Your three-digit participant ID (001–999), used to name and identify items. Do not run with the default 001 unless it is your ID. |
| Notebook 01 | INPUT_DIR | 'Files/furusato/seed' | Lakehouse folder from which the eight static-data CSV files are read (Files/furusato/seed). Do not change it. |
| Notebook 01 | RUN_OPTIMIZE_VORDER | False | Request for optimization after writing. Leave it False. |
| Notebook 01 | PUBLISH_LEASE_MINUTES | 30 | How long the publishing lock (lease) is valid, in minutes (15–1440). Do not change it. |
| Notebook 01 | OPERATOR_RECOVER_STALE_LEASE | False | Permission to recover when an interrupted run left a lock behind. Normally False. Set it together with the next two parameters, with the instructor. |
| Notebook 01 | STALE_LEASE_OWNER_RUN_ID | '' | Only for recovery: paste the OwnerRunId value shown in the error. Normally empty. |
| Notebook 01 | STALE_LEASE_GENERATION | -1 | Only for recovery: paste the Generation value (generation number) shown in the error. Normally -1. |
| Notebook 02 | PARTICIPANT_ID | '001' | Your three-digit participant ID (001–999), used to name and identify items. Do not run with the default 001 unless it is your ID. |
| Notebook 02 | ENVIRONMENT | '' | Explicitly dev, test or prod. Nothing runs while it is empty. |
| Notebook 02 | EXPECTED_WORKSPACE_NAME | '' | Exact display name of the workspace where the Notebook runs. Required in Notebooks 02–04; in Notebook 05, set it for automated runs (ALLOW_AUTOMATED_APPLY = True). |
| Notebook 02 | SCOPE_FILE | '' | Path of the JSON file that describes the deployment scope (workspace, folder and participant ID). Received from the instructor and placed in the Notebook's resources (builtin folder; Chapter 24). Do not share it. |
| Notebook 02 | PLAN_FILE | '' | Path of the resource-plan.json created by preflight. Do not reuse an old plan. |
| Notebook 02 | WRITE_GATE_FILE | '' | Path of write-gate.json authorized after reviewing the actual plan in 24.5. Never change plan or scope hashes. |
| Notebook 02 | PRIVATE_EVIDENCE_DIR | '' | Folder where run records (plans and results) are saved. Use the same folder across stages and do not share it. |
| Notebook 02 | ACTION | 'preview-metadata' | Stage to run. Defaults: preview-metadata in Notebook 02, deploy-core in 03 and preflight in 04. Notebook 02 also accepts apply-metadata, and 03 also accepts verify-sources. See Chapter 24 for the stages of Notebook 04. |
| Notebook 02 | APPLY_CHANGES | False | False runs a preview only. Set it to True only to apply a plan you have checked. |
| Notebook 02 | ALLOW_AUTOMATED_APPLY | False | Additional setting that allows applying in automated runs, such as through the Jobs API. Leave it False when you run from the portal. |
| Notebook 02 | CONFIRMED_PLAN_SHA256 | '' | Paste the hash of the plan you checked, exactly: planSha256 from preflight for Notebooks 02–04, or PLAN_SHA256 from the preview for Notebook 05. If the plan changes, start again. |
| Notebook 02 | RUN_NOTEBOOK01 | False | Whether deploy-sources runs Notebook 01. A completed Notebook 01 is not run again. |
| Notebook 02 | EXPECTED_DEFINITION_SHA256 | '' | Hash of the ontology definition checked before applying: paste beforeDefinitionSha256 from the Notebook 02 preview output. If the definition has changed, the run stops without applying. |
| Notebook 02 | RULE_STATEMENT_OVERRIDES | {} | Specify only rule statement changes approved by the instructor. Normally empty ({}). Rules do not run notifications or actions. |
| Notebook 03 | PARTICIPANT_ID | '001' | Your three-digit participant ID (001–999), used to name and identify items. Do not run with the default 001 unless it is your ID. |
| Notebook 03 | ENVIRONMENT | '' | Explicitly dev, test or prod. Nothing runs while it is empty. |
| Notebook 03 | EXPECTED_WORKSPACE_NAME | '' | Exact display name of the workspace where the Notebook runs. Required in Notebooks 02–04; in Notebook 05, set it for automated runs (ALLOW_AUTOMATED_APPLY = True). |
| Notebook 03 | SCOPE_FILE | '' | Path of the JSON file that describes the deployment scope (workspace, folder and participant ID). Received from the instructor and placed in the Notebook's resources (builtin folder; Chapter 24). Do not share it. |
| Notebook 03 | PLAN_FILE | '' | Path of the resource-plan.json created by preflight. Do not reuse an old plan. |
| Notebook 03 | WRITE_GATE_FILE | '' | Path of write-gate.json authorized after reviewing the actual plan in 24.5. Never change plan or scope hashes. |
| Notebook 03 | PRIVATE_EVIDENCE_DIR | '' | Folder where run records (plans and results) are saved. Use the same folder across stages and do not share it. |
| Notebook 03 | ACTION | 'deploy-core' | Stage to run. Defaults: preview-metadata in Notebook 02, deploy-core in 03 and preflight in 04. Notebook 02 also accepts apply-metadata, and 03 also accepts verify-sources. See Chapter 24 for the stages of Notebook 04. |
| Notebook 03 | APPLY_CHANGES | False | False runs a preview only. Set it to True only to apply a plan you have checked. |
| Notebook 03 | ALLOW_AUTOMATED_APPLY | False | Additional setting that allows applying in automated runs, such as through the Jobs API. Leave it False when you run from the portal. |
| Notebook 03 | CONFIRMED_PLAN_SHA256 | '' | Paste the hash of the plan you checked, exactly: planSha256 from preflight for Notebooks 02–04, or PLAN_SHA256 from the preview for Notebook 05. If the plan changes, start again. |
| Notebook 03 | RUN_NOTEBOOK01 | False | Whether deploy-sources runs Notebook 01. A completed Notebook 01 is not run again. |
| Notebook 03 | EXPECTED_DEFINITION_SHA256 | '' | Hash of the ontology definition checked before applying: paste beforeDefinitionSha256 from the Notebook 02 preview output. If the definition has changed, the run stops without applying. |
| Notebook 03 | RULE_STATEMENT_OVERRIDES | {} | Specify only rule statement changes approved by the instructor. Normally empty ({}). Rules do not run notifications or actions. |
| Notebook 04 | PARTICIPANT_ID | '001' | Your three-digit participant ID (001–999), used to name and identify items. Do not run with the default 001 unless it is your ID. |
| Notebook 04 | ENVIRONMENT | '' | Explicitly dev, test or prod. Nothing runs while it is empty. |
| Notebook 04 | EXPECTED_WORKSPACE_NAME | '' | Exact display name of the workspace where the Notebook runs. Required in Notebooks 02–04; in Notebook 05, set it for automated runs (ALLOW_AUTOMATED_APPLY = True). |
| Notebook 04 | SCOPE_FILE | '' | Path of the JSON file that describes the deployment scope (workspace, folder and participant ID). Received from the instructor and placed in the Notebook's resources (builtin folder; Chapter 24). Do not share it. |
| Notebook 04 | PLAN_FILE | '' | Path of the resource-plan.json created by preflight. Do not reuse an old plan. |
| Notebook 04 | WRITE_GATE_FILE | '' | Path of write-gate.json authorized after reviewing the actual plan in 24.5. Never change plan or scope hashes. |
| Notebook 04 | PRIVATE_EVIDENCE_DIR | '' | Folder where run records (plans and results) are saved. Use the same folder across stages and do not share it. |
| Notebook 04 | ACTION | 'preflight' | Stage to run. Defaults: preview-metadata in Notebook 02, deploy-core in 03 and preflight in 04. Notebook 02 also accepts apply-metadata, and 03 also accepts verify-sources. See Chapter 24 for the stages of Notebook 04. |
| Notebook 04 | APPLY_CHANGES | False | False runs a preview only. Set it to True only to apply a plan you have checked. |
| Notebook 04 | ALLOW_AUTOMATED_APPLY | False | Additional setting that allows applying in automated runs, such as through the Jobs API. Leave it False when you run from the portal. |
| Notebook 04 | CONFIRMED_PLAN_SHA256 | '' | Paste the hash of the plan you checked, exactly: planSha256 from preflight for Notebooks 02–04, or PLAN_SHA256 from the preview for Notebook 05. If the plan changes, start again. |
| Notebook 04 | RUN_NOTEBOOK01 | False | Whether deploy-sources runs Notebook 01. A completed Notebook 01 is not run again. |
| Notebook 04 | EXPECTED_DEFINITION_SHA256 | '' | Hash of the ontology definition checked before applying: paste beforeDefinitionSha256 from the Notebook 02 preview output. If the definition has changed, the run stops without applying. |
| Notebook 04 | RULE_STATEMENT_OVERRIDES | {} | Specify only rule statement changes approved by the instructor. Normally empty ({}). Rules do not run notifications or actions. |
| Notebook 05 | PARTICIPANT_ID | '001' | Your three-digit participant ID (001–999), used to name and identify items. Do not run with the default 001 unless it is your ID. |
| Notebook 05 | EXPECTED_WORKSPACE_NAME | '' | Exact display name of the workspace where the Notebook runs. Required in Notebooks 02–04; in Notebook 05, set it for automated runs (ALLOW_AUTOMATED_APPLY = True). |
| Notebook 05 | INCREMENT_PATH | 'Files/increment' | Lakehouse folder from which the three August observation CSV files are read (Files/increment). Do not change it. |
| Notebook 05 | APPLY_CHANGES | False | False runs a preview only. Set it to True only to apply a plan you have checked. |
| Notebook 05 | ALLOW_AUTOMATED_APPLY | False | Additional setting that allows applying in automated runs, such as through the Jobs API. Leave it False when you run from the portal. |
| Notebook 05 | CONFIRMED_PLAN_SHA256 | '' | Paste the hash of the plan you checked, exactly: planSha256 from preflight for Notebooks 02–04, or PLAN_SHA256 from the preview for Notebook 05. If the plan changes, start again. |
| Notebook 05 | EXCLUSIVE_APPLY_WINDOW_CONFIRMED | False | Confirmation that no other session writes to the same Lakehouse. Set it to True after closing other sessions. |
| Notebook 05 | STRICT_SYNTHETIC_CONTRACT | True | Validates timestamps against the observation window of the distributed data (August 2026, UTC). Leave it True for the distributed data. |
| Notebook 05 | OPERATOR_RECOVER_INTERRUPTED_RUN | False | Permission to recover after an interrupted run. Normally False. Use it only after confirming that the earlier session has stopped. |
| Notebook 05 | INTERRUPTED_RUN_ID | '' | Only for recovery: paste the RunId shown in the error. Normally empty. |

> Never guess values. Copy hashes, RunIds and similar values exactly as shown in outputs or errors.

> Scope files, approval files and run records contain workspace and item IDs. Keep them out of shared documents.

</details>
