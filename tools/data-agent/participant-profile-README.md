# Participant profile reproduction

現行の参加者向け手順は、既存の完全版 [Labの17章](../../Lab/17-fabric-data-agent-and-code-interpreter/README.md) と
[currentの日英HTML](../../docs/v3.0.0/current/README.md) です。既存Wordは移行レビュー用であり、
正本ではありません。このヘルパーは構成を再現するだけで、回答品質を保証しません。
参加者自身の実行履歴・実クエリ・結果による評価が必要です。この手順の掲載は実環境への変更の承認ではありません。

`participant_profile.py` configures one **existing** workshop Data Agent with the fixed `measured-contract-20261015` profile. The participant [complete Lab, chapter 17](../../Lab/17-fabric-data-agent-and-code-interpreter/README.md) and [current bilingual HTML](../../docs/v3.0.0/current/README.md) contain the preparation, SQL view definitions, instructions, examples and evaluation steps. The retained Word is for transition review, not current authority. Run this helper from the extracted package's `source/` directory, or the repository root. It does not require the instructor's private scripts, approval files or credentials. These instructions do not authorize live changes; apply and publish require separate approval.

This reproduces a configuration. It does not establish Ontology availability, successful business query execution or an answer-quality score. No quality guarantee or score can be inferred without the participant's own execution history, actual queries and results. Historical comparison results remain in their dated reports, not as participant targets.

## Before running

1. Complete the workshop data, quality-table and Semantic Model steps, and create the six `agent_*` SQL views using the SQL analytics endpoint, as shown in chapter 17. The actual SQL inventory can contain **more than 143 physical columns**: the profile selects 143 columns across 17 objects.
2. Use one existing Gen2 Ontology and one existing Agent in your own workspace. In the Agent Draft, add its Lakehouse, KQL Database, Semantic Model and the separate Ontology context. Select the required source objects/columns using the chapter 17 checklist so that the native definition contains their real discovered nodes. Keep the model's donation amount column visible and select that column plus all ten existing workshop measures. Enable Code Interpreter. Do not add model few-shots or extra topics.
3. Run each of the nine supplied KQL examples directly in the workshop KQL Database and retain the query and actual result. Later, also check their Data Agent validation status is `Valid`. A `Valid` label alone does not prove these direct query results or answer quality.
4. Install Python 3.11 or later and Azure CLI. In a terminal at the source root:

   ```text
   python -m pip install -r tools/provisioning/requirements-preview30.txt
   az login --tenant YOUR_TENANT_ID --use-device-code --allow-no-subscriptions
   ```

   Sign in as the workshop user with permission to read all four bound sources, read SQL schema metadata and update/publish this Agent. The helper uses Azure CLI's current delegated authentication and never writes a token into its evidence. A later expired login requires authentication again.
5. Obtain the **observed** regional routing origin. Open the existing main Ontology in Fabric. Open browser Developer Tools → Network, filter `metadata/artifacts`, then reload the Ontology. Select the request for that Ontology item and read **Request URL**. For `https://<observed-region-host>.analysis.windows.net/metadata/artifacts/<your-ontology-id>`, copy only `https://<observed-region-host>.analysis.windows.net`. Do not copy request headers, cookies, tokens, “Copy as cURL” or a HAR file. Do not derive a hostname from a region name. If the matching request is absent, stop and retain the observed UI state; the helper cannot invent this service route.

The default SQL transport uses the existing read-only Fabric SQL endpoint MCP over HTTPS; no ODBC driver is needed. The native Ontology metadata route is an **observed preview UI contract**, not a stable public REST guarantee. An unavailable route, permission failure or changed definition schema stops preparation without modifying Fabric. Optional `--sql-transport odbc` requires `pyodbc`, Microsoft ODBC Driver 18 for SQL Server, its OS dependencies, and TLS/TDS connectivity on port 1433; installing the Python wheel alone is insufficient.

## Prepare, apply, publish and verify

Replace every uppercase placeholder with your own value. `PRIVATE_DIRECTORY` must be a new absolute directory **outside all Git checkouts**, for example `C:\Users\YourName\FurusatoEvidence\profile-01` on Windows or `/home/yourname/FurusatoEvidence/profile-01` on Linux. Keep that directory private: it contains actual item IDs, definitions and query metadata. Run all four commands against the same IDs and directory.

```text
python tools/data-agent/participant_profile.py prepare --workspace-id YOUR_WORKSPACE_ID --agent-id YOUR_AGENT_ID --profile measured-contract-20261015 --routing-origin https://YOUR_OBSERVED_HOST.analysis.windows.net --private-root PRIVATE_DIRECTORY
```

Preparation reads the actual Agent Draft, independently queries `INFORMATION_SCHEMA.COLUMNS`, obtains the bound Semantic Model's TMDL and checks native Ontology generation metadata. It compiles locally, preserving the existing single Ontology context, model selection, Code Interpreter and Published content. It writes `inputs.json`, `candidate.json`, `compile-receipt.json` and `prepared.json`; it makes **zero Fabric configuration writes**. The expected status is `prepared`, with `selectedSqlObjects: 17`, `selectedSqlColumns: 143` and `answerAccuracyVerified: false`.

Review the receipt. Confirm the intended workspace/Agent and four source item identities in the private files. Close other Agent editing sessions before the next command.

```text
python tools/data-agent/participant_profile.py apply --workspace-id YOUR_WORKSPACE_ID --agent-id YOUR_AGENT_ID --profile measured-contract-20261015 --private-root PRIVATE_DIRECTORY --apply
```

This re-reads the live sources, rejects concurrent changes and saves `apply-backup.json`. It submits one `updateDefinition` to this same Agent, then checks the complete Draft and preservation of Published content. Expected status: `draft-matches`, with `published: false`. The update includes the global and three source instructions, descriptions, SQL/KQL selections and examples; pasting four instruction text boxes alone does not cover that configuration.

```text
python tools/data-agent/participant_profile.py verify --workspace-id YOUR_WORKSPACE_ID --agent-id YOUR_AGENT_ID --profile measured-contract-20261015 --private-root PRIVATE_DIRECTORY --stage draft
```

This is read-only. It checks the complete Draft, public source bindings/instructions/descriptions, exactly 17 selected SQL objects and 143 selected columns, and the nine unchanged KQL examples all marked `Valid` (zero SQL/model examples). If validation is still pending, wait for the service to finish and rerun **verify**, not apply. If an example is `Invalid`, retain its reason and investigate the underlying KQL query/schema; do not label it successful or publish it.

```text
python tools/data-agent/participant_profile.py publish --workspace-id YOUR_WORKSPACE_ID --agent-id YOUR_AGENT_ID --profile measured-contract-20261015 --private-root PRIVATE_DIRECTORY --apply
```

Publication checks Draft again, refuses a concurrent Published change, saves `publish-backup.json`, submits one publish request, and reads Published back. Expected status: `published-matches`, `directSources: 3`, `selectedSqlObjects: 17`, `selectedSqlColumns: 143`, `activeKqlExamples: 9`. It writes `published.json` only after these checks pass.

```text
python tools/data-agent/participant_profile.py verify --workspace-id YOUR_WORKSPACE_ID --agent-id YOUR_AGENT_ID --profile measured-contract-20261015 --private-root PRIVATE_DIRECTORY --stage published
```

This final command is read-only and may be repeated. The receipt deliberately reports `ontologyContextAvailabilityVerified: false` and `answerAccuracyVerified: false`: a retained native Ontology configuration is not execution proof. Finish the current Lab/HTML's Ontology connection checks and fresh-chat evaluation, retaining unsupported/failed/unknown cases in the denominator.

## If a step stops

- **Preparation fails:** nothing was applied. Inspect private evidence and correct the described prerequisite using the guide. Use a new private directory for the next preparation; preserve the failed run. Missing SQL nodes are not synthesized. Blank native SQL type strings can be filled only when fresh public Available-column metadata and independent SQL metadata agree; nonblank mismatches stop.
- **Apply has an uncertain response:** keep `apply-intent.json` and `apply-backup.json`. Run `verify --stage draft`. If the Draft matches and the examples are valid, proceed to the separately authorized publish command. If it differs, inspect the saved input, candidate and current definition. Do not delete the intent file or repeat the write blindly.
- **Publish has an uncertain response:** keep `publish-intent.json` and `publish-backup.json`. Run `verify --stage published`. A matching readback establishes the published configuration even if the original response was lost. A failed/pending readback remains unresolved; do not publish again blindly.
- **Concurrent edit or changed schema/profile:** retain both participants' work and compare it before choosing a new preparation. Do not bypass the drift check by editing hashes or receipts.
- **Restore is needed:** this helper has no automatic restore command. Its private backups preserve the pre-write definitions, including existing Published content. Inspect the current state and backup first; use the existing Agent UI or a separately reviewed `updateDefinition` restoration. Restoring Draft alone does not restore a prior publication. Never remove/recreate the Ontology to work around a connection failure.

HTTP bodies and operation IDs are saved privately. Write intent files prevent automatic resubmission. Resource creation, deletion, source registration and business-data changes are outside this helper.

## Validation of this helper

```text
python -m unittest discover -s tools/data-agent/tests -p test_participant_profile.py -v
```

Tests use synthetic IDs and mocked transport, including concurrent edits, uncertain writes, publication failure, exact public selection/examples, private evidence paths, redirects and long-running operations. They do not establish that a tenant's current preview rollout is supported; the participant's read-only preparation and subsequent readback provide that evidence.
