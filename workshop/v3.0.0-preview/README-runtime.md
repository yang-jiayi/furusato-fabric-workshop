# v3.0.0 Preview runtime — portable candidate

**Current course/Notebook edition: 3.0.0**, from `WORKSHOP_VERSION`.
The directory name remains a technical runtime profile. See
[the explicit component versions](edition.json) and
[the current artifact-set procedure](../../docs/v3.0.0/current/README.md).
Production targets the approved folder directly; **Temp is not a default
deployment dependency**. Explicit evaluation-only folders must be cleaned up
after adopted dependencies and the formal Agent are verified.

This compatibility-stable source path is also shipped by the
[Workshop3.0.0 course release](../../docs/v3.0.0/README.md). The course version
does not change the preview status of Fabric features or qualify a new deployment.
Evaluation adapters may evolve, but the originalv2.7 data, ten/84 rubric and
reference assets remain protected. Current adapter/runtime bytes are separately
pinned in each new candidate plan and resealed Notebook02–04 package.

This directory is **not a claim of successful cloud deployment, UI validation, AI accuracy, or general availability**. The generation2 contract and safety code have offline checks. The exact tenant's native feature availability must still be observed.

## Stable source paths

| Artifact | Source |
|---|---|
| Immutable synthetic CSVs | `data/seed/`, `data/increment/` |
| Static data / quality runtimes | `notebooks/Notebook_01_*.ipynb`, `notebooks/Notebook_05_*.ipynb` |
| Metadata / generation2 / staged deployment | `notebooks/Notebook_02_*.ipynb` through `Notebook_04_*.ipynb` |
| Generation2 TMDL | `ontology/definition/` |
| Actual portable entity/property/relationship inventory | `ontology/generation2-contract.json` |
| Optional static Relationships companion (create-only) | `ontology/relationships/definition/`, `ontology/relationships/contract.json` |
| Explicit legacy consumer bridge (offline handoff only) | `ontology/agent-compat/definition-template.json`, `ontology/agent-compat/contract.json` |
| Source-owned Direct Lake DAX | `powerbi/Furusato_Analytics.SemanticModel/` |
| Metric source contract | `powerbi/native-metrics-contract.json` |
| Four directly configured Data Agent sources | `data-agent/definition/` |
| Candidate status and scope boundaries | `data-agent/candidate-contract.json` |
| Gold publication catalog | `provisioning/gold-contract.json` |
| Notebook package fingerprints | `provisioning/notebook-bundle-manifest.json` |

Notebook01 and Notebook05 retain the tested v2.7 data-processing code. The only
Notebook01 code delta is its explicit `NOTEBOOK_VERSION` audit/display value,
which identifies the current distributed3.0.0 Notebook. Existing run audit
records are not rewritten. Their data contract and technical generation identifiers retain their original v2.7 names. This is distinct from the **Ontology generation**, which must be **2** for this edition. The original v2.7 directory and standard 10-question/84-condition benchmark remain untouched.

The 10 core entity types, 72 **explicitly modeled static properties**, 15 relationships and 11 static backing tables are preserved as business definitions, but are emitted as **new TMDL**, not as old `EntityTypes/.../definition.json` parts. Do not confuse those entity declarations with the 14 additional relationship-key column occurrences in entity backing tables or the junction table's two columns. See [property-versus-column counts](ontology/PROPERTY-COUNTS.md) for the native inventory and the 86/88 backing-column distinction. Four native natural-language Business Rules are included. The sole operational time-series property is explicitly **unbound** in the portable candidate until its native Eventhouse source contract is captured and validated.

## Required native boundaries

- **Business names:** entity types are real domain concepts such as `Municipality`, `AdministrativeArea`, `Prefecture` and `Donation`. Do not add Demo/Test/Sample/Example suffixes to entity names. Isolate experiments by item, folder or namespace instead. Preserve historical raw evidence unchanged; final teaching screenshots must be genuine recaptures after a verified rename, never edited pixels masquerading as a native state.
- **Native rename boundaries:** a native entity rename can preserve an older internal backing-table identifier. That identifier is not the business entity-type name; do not globally replace it or rewrite preserved bindings just to make strings match. Verify the entity/model reference, stable lineage IDs, inherited/shared references, keys and source mapping, then refresh/revalidate graph projection labels before final GQL. Historical before/after captures retain their original names.
- **Metrics:** source-owned DAX lives in the semantic model. The current official ontology REST contract says projected/enrichment `backingMeasure` cannot round-trip in TMDL. Creating a table measure alone does not create an Ontology Metric. Use native semantic-model binding/UI and prove the metric is visible and used. Never author an explicit DAX metric as a substitute.
- **Time series:** the generation2 `backingConfiguration` shape is documented; this candidate does not invent the Eventhouse partition/source expression. Capture it from a real supported binding. An unbound property is not a successful lab.
- **Graph:** no default materialization. Opt in only to eligible keyed entities with one managed Lakehouse backing table. Semantic-model-backed, keyless, unbound or multiple-backing-table entities can be ineligible.
- **Business Rules:** contextual natural-language guidance, not executable constraints or Activator actions.
- **Data Agent:** configure the semantic model directly. Its grounding is not inherited through the Ontology source. Code Interpreter configuration is not proof of execution or answer quality.
- **Native UI handoff:** run `handoff-ontology` before the coordinator adds native Metrics or other native-only state. This disables subsequent automated TMDL mutations. Do not round-trip an ontology after native Metrics have been added.

## Local build and tests

Run from the clean public source checkout, not an old/private archive:

```powershell
python -m pip install -r tools/provisioning/requirements-preview30.txt
python tools/provisioning/build_preview30.py
python -m unittest discover -s tools/provisioning -p "test_preview30*.py" -v
```

The builder never deletes or overwrites `attachments/`. It emits output-free Notebook02–04 frontends with fingerprint-checked embedded packages and code cells below 450,000 UTF-8 bytes. Source identities remain placeholders.

## Private scope and preflight

Copy `provisioning/scope.example.json` **outside this source checkout** and fill it using read-only discovery. Explicitly choose `dev`, `test` or `prod`.

```powershell
$Private = "<private-evidence-directory-outside-source>"
$Scope = "<private-scope-json>"
python tools/provisioning/preview30_runtime.py preflight `
  --environment dev --scope $Scope --evidence-dir $Private --online
```

Offline mode instead accepts `--inventory <private-inventory.json>`. Preflight recalculates:

- static: **80,000 donations / 1,344,099,000 yen**;
- increments: **3 × 5,000 raw rows / 14,900 unique / 100 duplicates**;
- protected baseline fingerprints and active/recoverable name conflicts.

Preflight writes `resource-plan.json`, `write-gate.template.json`, `result.json`, and `progress-ja.md` privately. It does **not** approve the gate. The plan pins the implementation/templates, individual Notebook bytes, and the immutable baseline. A subsequent source change requires a new build, preview and approval; it is not an implicit corrective retry.

**A numeric portal subfolder reference is not a folder GUID.** A matching folder date/name is not proof of the mapping. Without actual mapping evidence and explicit approval, keep both `folderMappingVerified` and `allowCloudMutations` false. Authentication prompts must be completed by the user; never inject browser tokens/cookies or bypass FIDO/Windows Hello.

## Staged execution after explicit approval

Create the private `write-gate.json` from the emitted template only after reviewing the exact resource plan and obtaining the required mapping/approval. Keep its exact scope and plan fingerprints. Never edit checkpoints to force a stage past a failed proof.

```powershell
$Gate = Join-Path $Private "write-gate.json"
$PlanSha = (Get-Content (Join-Path $Private "resource-plan.json") -Raw | ConvertFrom-Json).planSha256
$Common = @("--environment", "dev", "--scope", $Scope, "--evidence-dir", $Private)
$Write = $Common + @("--write-gate", $Gate, "--confirm", $PlanSha)

python tools/provisioning/preview30_runtime.py deploy-sources @Write --run-notebook01
python tools/provisioning/preview30_runtime.py verify-sources @Common
python tools/provisioning/preview30_runtime.py deploy-notebooks @Write
python tools/provisioning/preview30_runtime.py deploy-realtime @Write
python tools/provisioning/preview30_runtime.py deploy-core @Write
```

Stop on any nonzero exit code. These are deliberate separate stages, not an unattended shell chain. All created items are participant-suffixed and folder-scoped. The runtime refuses preexisting unowned items, recoverable conflicts, forbidden items, deletes, capacity changes, role changes, or tenant changes.

`deploy-sources` stages the increment CSVs outside `Files/increment`. It checks Notebook01 job history and never re-runs a completed job. `verify-sources` uses the documented native SQL Endpoint MCP tool, discovers its actual schema, and requires all 20 final tables to match the Ready publication generation plus static source totals.

`deploy-notebooks` imports Notebook02–05 but does not execute them. Notebook04 is a parameterized frontend; the CLI remains the primary cross-machine orchestration path. Preserve the same private plan and `deployment-state.json` across stages. Notebook02 previews/applies only the four declared rule statements, requires an exact current-definition SHA for apply, and refuses post-native-Metrics TMDL replacement.

`deploy-core` produces **generation2 static-core readback**, not full native-feature completion. Complete the Eventhouse binding using the verified native contract/UI before claiming the time-series lab passed.

## Optional static Relationships companion

This is a **new, opt-in item**, not a replacement or repair of the operational core.
The portable original has **10 entities / 72 static + 1 time-series property /
15 relationships**. After native binding promoted `Municipality.PrefectureId`,
the observed operational core has **10 / 73 static + 1 time-series / 15**.
Keep that core and its KQL time-series binding untouched. These counts describe
different snapshots, not a request to remove the native promoted property.

An observed core Graph materialization failed with HTTP400
`InvalidPropertyType: IncomingDonationAmountYen` despite an **Eligible** UI badge.
The supported workaround is `ONT_Furusato_Relationships_<PID>`, built from the
**portable original** by excluding only `Municipality.IncomingDonationAmountYen`.
It has **10 entities / 72 static properties / 0 time-series properties /
15 relationships**, with 10 entity bindings and the same 11 managed Lakehouse
backing tables. The original entity/property/relationship lineage identities and
relationship-key columns remain stable. It does not copy business data, create
another Lakehouse, rerun Notebook01/05, or rewrite either existing ontology.

Build just these portable assets without rebuilding Agent or notebook inputs:

```powershell
python tools\provisioning\build_preview30.py --relationships-only
```

The full `build_preview30.py` also includes them in the sealed Notebook02–04
packages. After all concurrent source work is frozen, reseal Notebook02–04 before
freezing deployment fingerprints. This narrower command preserves already-built
Agent definitions and Notebook01/05 instead of regenerating them:

```powershell
python -c "import sys; sys.path.insert(0, r'tools\provisioning'); from preview30_notebooks import build_notebooks; from preview30_runtime import PREVIEW, save; save(PREVIEW / 'provisioning' / 'notebook-bundle-manifest.json', build_notebooks())"
```

The companion stage is deliberately **CLI only**; the normal Notebook/core
actions do not opt in.

For an already verified, runtime-owned core and Lakehouse, use the **same private
scope and evidence directory** so their owned receipts are retained. Re-preview
the plan with the additional item, review fresh active/recoverable inventory, and
approve the new plan hash and exact folder mapping. An old core-only gate cannot
authorize it:

```powershell
python tools\provisioning\preview30_runtime.py preflight @Common --online --include-relationships
# Review resource-plan.json and explicitly approve a NEW write-gate.json.
$PlanSha = (Get-Content (Join-Path $Private "resource-plan.json") -Raw | ConvertFrom-Json).planSha256
$Write = $Common + @("--write-gate", $Gate, "--confirm", $PlanSha)
python tools\provisioning\preview30_runtime.py deploy-relationships @Write
```

Offline preflight may use `--inventory <private-inventory.json>` instead of
`--online`; deployment still checks fresh ownership, folder and name collisions.
Only the separately planned companion can be created. The existing one-shot
write previews, pending-create receipts, bounded LRO polling and owned-ID
readback rules apply. An ambiguous request or disappeared/moved owned item is a
stop, never permission to repeat CREATE, adopt an unowned item, overwrite a
definition or purge a recoverable item.

The command reads back **generation2**, the complete static structure, stable
identities and same-source bindings, then emits private
`relationships-native-handoff.json`. It supplies the exact workspace, folder,
new ontology and preserved core IDs, Lakehouse ID, all ten entity names and all
fifteen relationship names. Use its `nativeSteps` as the native materialization
prompt after **separate Graph opt-in**. Capture the actual managed Graph ID and
its association with that ontology, then the materialization job ID and terminal
state. The public [Ontology GET contract](https://learn.microsoft.com/en-us/rest/api/fabric/ontology/items/get-ontology)
documents `properties.generation`, not a managed Graph identity: the runtime
leaves `managedGraphId` null and requires supported native readback rather than
guessing an ID, endpoint, or refresh API.

**Eligible is not refresh or query proof.** A native static-companion full Graph
materialization has been observed to reach Completed, but this does not establish
numerical GQL acceptance in another deployment (or prove the current queries).
Retain actual Graph query results and the existing numerical/business-path
acceptance checks; the source contract deliberately says `required-not-assessed`.
The core and companion describe the **same static donations**: never add their
amounts together or add raw operational observations. Supplier catalog fan-out
must not double count donations. Data Agent source routing remains unchanged;
using this companion for a future Agent is a separate controlled source choice,
with its own frozen preview, approval and actual evaluation—not an automatic
promotion or publication.

## Explicit generation1 consumer bridge — optional, not a gen2 fix

A successfully queried **generation2** static Graph does not prove that a
particular Data Agent consumer API supports its Ontology generation. A native
consumer returned `This API version is not supported for the specified Ontology
item.` despite verified source rows and GQL paths. A separate **generation1**
source-only candidate subsequently completed native `analyze.database.execute`
with `datasource_type: Ontology` and actual GQL, without that version error.
This is bounded compatibility evidence: returning the expected count does
**not** accept every original question format/grain criterion or the full
10-question/84-condition benchmark. It does not authorize main promotion.

`ONT_Furusato_AgentCompat_<PID>` is therefore an explicit **legacy consumer
bridge**, not an implicit fallback, a generation2 connector fix or a primary
downgrade. Keep both generation2 Ontologies, the operational TS binding and native
Metrics unchanged. Default `preview30_runtime.py` resources/actions and its
generation2 checks are unchanged; it has no legacy fallback/apply switch.

The new helper reuses the **unmodified definitions-only engine in released
Notebook03**, and `workshop/v2.7.0/ontology/ontology-full-definition-template.json`.
There is no `provisioning/bundle/ontology` directory. It never runs Notebook03
actions or Notebook01/05. The derived JSON definition contains **53 parts**:
10 entities, 72 static properties, zero TS, 10 static bindings, 15 relationships,
15 contextualizations, one retained empty overview, `.platform` and
`definition.json`. Only the new bridge omits `IncomingDonationAmountYen` and its
TS binding. Business keys/types/mappings and released legacy metadata IDs remain
stable over the **same 11 `dbo.ot_*` tables**, including the catalog bridge;
legacy metadata IDs need not equal generation2 lineage tags.

```powershell
python tools\provisioning\build_preview30.py --agent-compat-only

python tools\provisioning\preview30_compatibility.py prepare `
  --environment dev --scope $Scope `
  --inventory "<private-timestamped-inventory.json>" `
  --owned-state "<private-deployment-state.json>" `
  --target-folder-id "<same-approved-root-folder-GUID>" `
  --output-dir "<NEW-private-compat-plan-directory>"
```

This is **offline preparation**, not deployment. Inventory uses the existing
preflight shape: `capturedUtc`, `workspace` (`id`, `displayName`), `folders`
(`id`, `displayName`, `parentFolderId`), `items` and `recoverableItems`. The helper
requires matching runtime-owned source/core receipts, verified static sources,
a generation2 primary receipt, the approved root folder, and no
active/recoverable name collision. It writes private `compat-plan.json` and
`compat-create-body.json`; the plan pins exact body and input hashes. A stored
snapshot is not a fresh cloud ownership check or mutation approval.

Omitting `--target-folder-id` uses the approved root directly. The legacy
`--temp-folder-id` option is only for an explicitly requested isolated evaluation.
Any adopted dependencies must be retained in the production folder before
unused evaluation Items and the empty Temp are removed.

Before any write, separately approve the exact plan/body/scope, refresh all
ownership/absence/protection checks, and persist an exclusive one-attempt intent.
Use the documented generic **Create Item** endpoint with `folderId` and the
complete **legacy JSON** definition—not bare create, which defaults to generation2.
Capture 201/202 status/headers; poll the original public operation ID with bounded
waits and `Retry-After`. Missing IDs, ambiguity or rejection mean stop, not another
format/name or a second POST. Read back **integer `properties.generation == 1`**,
all 53 parts and the exact static source contract. Reject generation2 or missing
generation. `.platform` may echo the approved top-level description; the released
comparator normalizes service-owned logical IDs, never business/schema drift.

Creation can generate owned **GraphModel, managed Lakehouse and SQLEndpoint**
children. Discover their actual new identities; never infer a Graph ID or adopt
an existing item. Graph materialization ingests a **derived projection/cache** and
consumes capacity/storage—it is not a zero-copy claim. Open only the new managed
Graph in the native editor if one-time loading initialization is needed. Inspect
fresh compilation/source mappings and job history; wait/reuse an active or
matching Completed refresh. Any separately approved explicit refresh is at most
one null-body `POST .../graphModels/{actualId}/jobs/refreshGraph/instances`.
Record `GraphNotRefreshable` or other failures without blind retries.
Completed is not query acceptance: retain three native GQL checks (at most four
with one syntax correction) for all **10/15 labels, 109,592 nodes / 297,303 directed
edges**, Prefecture 45's reverse path and Donation 5000001's catalog path. Catalog
eligibility is not fulfillment; never add amounts across duplicate supplier paths
or across these Ontologies describing the same static donations.

### Source-only Data Agent handoff

After exact generation1 and native Graph acceptance, supply an owned receipt
(`item`, `typedMetadata`, `bodySha256`, `planSha256`), the actual definition, and
Graph evidence containing `scope`, matching `refreshJob`, `graphQueryAcceptance`,
`gqlChecksPassed: 3`, `nativeCounts` and `postGqlGuards.passed`.
Use a frozen **four-direct-source static candidate stage** whose ten selected
entities already contain exactly the 72 static property names. A core profile
still selecting the TS property is refused, not silently filtered or repaired.

```powershell
python tools\provisioning\preview30_compatibility.py agent-handoff `
  --environment dev --scope $Scope `
  --inventory "<private-current-inventory.json>" `
  --owned-state "<private-deployment-state.json>" `
  --temp-folder-id "<approved-Temp-folder-GUID>" `
  --compat-receipt "<private-owned-create-receipt.json>" `
  --compat-definition "<private-native-compat-definition.json>" `
  --graph-evidence "<private-native-graph-result.json>" `
  --frozen-agent-definition "<private-frozen-Agent-definition.json>" `
  --stage published --output-dir "<NEW-private-Agent-handoff-directory>"
```

The helper emits only private `compat-agent-draft-definition.json` and
`compat-agent-handoff.json` for a **new isolated candidate**. Exactly three
Ontology fields change: `artifactId`, `displayName`, `userDescription`. The
datasource relative path, all selections/source instructions, Lakehouse/KQL/
direct SemanticModel parts, CI and exact GLOBAL payload remain unchanged.
Even existing GLOBAL wording mentioning generation2 is preserved; the actual
source and its description explicitly identify the generation1 bridge.
No published stage is emitted, and no Agent is created, queried, published or
promoted. Fresh candidate absence/ownership/readback, publication approval and
native original-benchmark evaluation remain separate gates.

The full build packages the optional helper and its unchanged released inputs,
but no Notebook frontend opts in. Use the targeted build above during concurrent
candidate work; reseal Notebook02–04 only after all owners finish. Neither this
build nor the historical bounded consumer observation proves a new environment
or its current candidate has passed the benchmark.

## Activator and increments

This edition reuses the unchanged tested native lifecycle and upload utilities. `shouldRun` definition metadata is not used as a substitute for formal native `start_rule`/`stop_rule`.

Before the first watched upload, inspect the new rule in the native Activator UI.
While stopped, open **Edit action**, verify the intended Pipeline and dynamic
`Type`/`Subject`/`Source` mappings, then **Apply** and **Save** once. Keep historical
application disabled. Read back the definition: `shouldApplyRuleOnUpdate` must be
`false`, and an explicit `delayToleranceMs` of at least `120000` must be present
before delivery. The v3 delivery adapter now refuses an upload if these live
settings are missing, insufficient, or the rule is stopped; stopping a rule
remains available independently of this readiness check.

In the observed correction, native action persistence added a 120-second
tolerance, and subsequent fresh file events completed the native
event/activation/Pipeline/Copy/KQL chain. This does **not** isolate delay tolerance
as the sole cause or prove that setting it through an API alone initializes every
action. A `Running` badge and these settings remain readiness evidence, not
delivery acceptance. Never replay an earlier unverified file to manufacture a
successful first-run result; a diagnostic run and any separately approved
recovery must retain their own receipts and be reported separately.

```powershell
python tools/provisioning/preview30_runtime.py start-activator @Write
python tools/provisioning/preview30_runtime.py deliver-increment @Write --increment 1
```

The start result is **armed_unverified**. Each increment is one complete Blob **PutBlob**, with `If-None-Match: *` and complete-byte readback. A timeout, existing path, prior intent or uncertain outcome is a stop condition, not permission to overwrite, retry CREATE, replay a CSV, or manually run the Pipeline.

Capture actual native FileCreated events and the correlated Copy activity export, then validate them against **fresh** native Activator history, new Pipeline job history, and KQL:

```powershell
python tools/provisioning/preview30_runtime.py verify-delivery @Write --increment 1 `
  --native-events "<private-native-events-array.json>" `
  --native-copy "<private-native-copy-activity.json>"
```

The Copy export must identify the actual `pipelineRunId`, `activityType: Copy`, `status: Succeeded`, and native `output.rowsRead`/`output.rowsCopied`. Unsupported shapes are blockers, not values to invent. The native event array must retain the service fields consumed by `activation_runtime.verify_automatic_delivery`, including exact source, subject, event ID, PutBlob API and complete content length.

Only after increment 1 reaches `native-copy-kql-verified` may increment 2 be delivered; repeat for increment 3. No manual Pipeline control can prove automatic delivery. Stop formally when instructed:

```powershell
python tools/provisioning/preview30_runtime.py stop-activator @Write
```

## Quality, semantic model and Data Agent

Run Notebook05 against the selected Lakehouse with `INCREMENT_PATH = "Files/increment"`. Review its real preview hash, then use its existing explicit apply gate. It reads **Lakehouse static/staging tables and files**, never Eventhouse-to-Gold.

```powershell
python tools/provisioning/preview30_runtime.py verify-gold @Common
python tools/provisioning/preview30_runtime.py deploy-semantic-model @Write
python tools/provisioning/preview30_runtime.py refresh-model @Write
python tools/provisioning/preview30_runtime.py verify-model @Common
python tools/provisioning/preview30_runtime.py deploy-agent @Write
python tools/provisioning/preview30_runtime.py publish-agent @Write
python tools/provisioning/preview30_runtime.py handoff-ontology @Write
```

Gold verification checks its publication control and all output generations, raw/accepted/quarantined rows, and static/accepted source separation. An independent quality run may explicitly select the already-staged immutable CSV directory instead of the watch directory; record that exact input in the preview and never count it as Eventhouse automatic-delivery proof. The source code still reads Lakehouse tables/files, not Eventhouse.

Initial Direct Lake framing is separate from definition import. `refresh-model` reuses an existing successful refresh, submits at most one initial refresh with zero automatic retries, and records its terminal state. DAX verification must then return actual results reconciling to observed Gold totals. If refresh/credentials/SSO or a native query surface prevents verification, stop and report the exact error—do not change permissions or configure a fake data source.

The Data Agent is created as a **candidate draft** with Lakehouse, KQL, generation2 Ontology and **direct SemanticModel** sources plus Code Interpreter configuration. `publish-agent` uses the documented staging/publish API and reads back all four published sources; publication is explicitly a preview-candidate operation, not an accuracy promotion. Native feature use, actual tool execution, fresh-conversation comparisons and original/new-feature evaluation remain separate checks. A successful definition import or publication is not proof of answer accuracy.

UI labs—Copilot attachments, namespaces/inheritance/shared properties, native Metrics, versions, import/export and selective Graph/GQL—belong in isolated items under **Temp** within the target tree. Only their assigned coordinator writes those items. The runtime never edits their definitions or substitutes schema-only tests for native lab evidence.

### Formal Agent profile (standard-contract restoration)

`publish-agent` publishes the base candidate only. Apply the formal profile afterwards
with [`fresh_grounded_profile.py`](../../tools/data-agent/fresh_grounded_profile.py),
which chains four offline compilers: source-grounded → complete-contract →
time-layer-isolation → [standard-contract-restoration](data-agent/candidates/standard-contract-restoration/README.md).
The last stage restores the standard ten/84 answer contracts; without it a clean
2026-10-07 deployment scored only 36/84 and 34/84.

1. Read the published Agent definition and the `INFORMATION_SCHEMA.COLUMNS` rows of the
   six verified SQL views; keep both privately.
2. `compile_fresh_profile(definition, columns)` returns the Draft and a receipt. Require
   `globalInstructionsCharacters` ≤ 15,000, SQL 17 / KQL 9 examples, unchanged source
   identities and `cloudCalls: 0`.
3. Execute every SQL/KQL example read-only against the real sources; each must return rows.
4. `updateDefinition` with the compiled Draft plus the unchanged Published parts, read it
   back, then publish through the staging API and confirm Published equals Draft. The
   service may rename the Ontology datasource folder to the source display name; map
   the compiled part to the live path instead of creating a second source.
5. Evaluate the unchanged ten/84 at least twice
   ([`evaluate_native.py`](../../tools/data-agent/evaluate_native.py) supports the public
   MCP transport) and keep every failure. T10 may be blocked by the native content filter;
   report it, never bypass it. Run any holdout once, on the final configuration only.

### API-only operation notes (observed 2026-10-07)

- When the portal requires Windows Hello, the runtime CLI with Azure CLI tokens is
  sufficient. Never inject browser tokens or cookies.
- A numeric portal `subfolderId` is not a folder GUID. Resolve it from the workspace
  folder metadata that returns both identifiers, record the mapping privately, and only
  then target the folder.
- An Eventhouse hard delete can fail with a non-retriable `UnknownError` while a
  soft-deleted Item still references it; the portal's metadata delete reported
  `AssociationPreventsArtifactDeletion`. Permanently delete the referencing recoverable
  Items first (here a probe Pipeline and Notebook), then retry once.
- If the Activator is not armed and verified, deliver each increment once with PutBlob
  and run the Pipeline manually once per file. Record this as manual ingestion, not
  automatic delivery.
- Generated queries: KQL `top` accepts one sort key (use `order by … | take N`); GQL
  reserved words such as `nodes`/`edges` cannot be aliases; in the static consumer graph
  `MunicipalityId` is a STRING and `PrefectureName` is the Japanese suffixed name.

### Stages after the repository changed

Every write stage is bound to the source fingerprint recorded by preflight
(`candidateSourceSha256` in the private plan). A newer checkout is refused for an
existing deployment. Run the remaining stages from a temporary worktree of the
approved commit with the same private evidence directory, then remove it. Never
edit the plan, state or checkpoints, and never rerun preflight to "refresh" the hash.

```powershell
git worktree add ..\approved-runtime <approved-commit>
python ..\approved-runtime\tools\provisioning\preview30_runtime.py handoff-ontology @Write
git worktree remove ..\approved-runtime
```

### Notebook05 plan hash

`PLAN_SHA256` covers `ALLOW_AUTOMATED_APPLY` and, when it is true,
`EXPECTED_WORKSPACE_NAME`. A preview run with different values prints a different
hash, and the apply run then refuses it. Compute the hash offline with the
notebook's own `build_plan` (no Spark or network), compare it with the real preview
output, and only then apply with `APPLY_CHANGES=True`, `CONFIRMED_PLAN_SHA256=<hash>`
and `EXCLUSIVE_APPLY_WINDOW_CONFIRMED=True`:

```powershell
python tools/provisioning/notebook05_plan_sha.py --participant-id 107 --workspace-name "<exact workspace name>"
# add --manual-apply when the apply runs in the portal with ALLOW_AUTOMATED_APPLY=False
```

### Data Agent service checks (views and example validation)

The service owns the element tree of each source. After `publish-agent` and after
any profile change, read it through the public Data Agent management API instead
of trusting the submitted definition:

```powershell
python tools/data-agent/agent_service_check.py --private-root <private dir> `
  --workspace-id <workspace> --agent-id <agent> --view-columns <private INFORMATION_SCHEMA.COLUMNS json>
```

Require all six `agent_*` views as `View`, `Available`, selected, with service
columns equal to `INFORMATION_SCHEMA.COLUMNS` (`agent_donation_detail` keeps
`DonationDataLayer` unselected) and the overlapping `ot_*` tables unselected. If a
view is missing or unavailable, select it in the Agent's Explorer; do not invent
element IDs. The same report lists each example's service `validationStatus`.
Examples that fail validation are not sent to the Agent. On 2026-10-07 all 17
Lakehouse SQL examples were `Invalid` ("Failed to connect to server …") although the
SQL endpoint and the Agent's runtime SQL worked, while all 9 KQL examples were
`Valid`; this is filed as a product issue
([support drafts](../../docs/v3.0.0/followup-20261007/platform-support-cases.md)).
Never mark a failed example valid.

### Optional Power BI report without the portal

`tools/powerbi/Deploy-FurusatoPowerBI.ps1` creates the model and the report. When
the model already exists, create only the report from the same definition with a
`byConnection` reference to the existing model (never re-import the model), read
the definition back, and render it. If the tenant disables report image export,
export to PDF instead, check the page visually, and reconcile its totals with DAX
(Gold 94,900 rows / 1,596,157,000 JPY; high-value 1,392).

### Hand-off: Activator native action (UI, required for automatic delivery)

The deployed rule's action already references this deployment's Pipeline: its
`fabricJobConnectionDocumentId` is the `fabricItemAction` entity inside the same
Activator definition, whose `itemId` is the deployed Pipeline. What the API cannot do
is the native persistence the adapter requires before delivery (an explicit
`delayToleranceMs`); do it in the native Activator UI:

1. Keep the rule stopped. Open the rule → **Edit action**, confirm this deployment's
   Pipeline and the dynamic `Type`/`Subject`/`Source` mappings, **Apply**, **Save**.
2. Read the definition back: the action still targets the deployed Pipeline,
   `shouldApplyRuleOnUpdate` is `false` and `delayToleranceMs` ≥ `120000`.
3. Run `start-activator`, then for increments 1–3 in order: `deliver-increment`,
   export the native FileCreated events from the Activator UI, export the Copy
   activity record with the read-only API helper below, `verify-delivery`. Finish
   with `stop-activator`.

```powershell
python tools/provisioning/export_copy_activity.py --workspace-id <workspace> `
  --pipeline-job-id <new pipeline job id> --out <private dir>\copy-001.json
```

The helper writes the service's own activity-runs record (`pipelineRunId`,
`activityType`, `status`, `rowsRead`, `rowsCopied`) and stops unless the run has
exactly one Copy activity. The FileCreated events (`___subject`, `___type`,
`___source`, `api`, `contentLength`, `___id`) have no public API and must come from
the Activator UI.

If the increments were already ingested manually, `deliver-increment` stops (the
CSV exists, PutBlob `If-None-Match: *` returns 412) and re-delivery would double the
KQL rows because the Pipeline does not de-duplicate. A fresh delivery then needs an
explicitly approved reset first: with the rule stopped, run
`.clear table DonationEvents data` and
`.clear materialized-view DonationObservationSummaryForAgent data`, delete the three
CSVs under `Files/increment`, and confirm 0 rows. After `verify-delivery` of all
three files, reconcile KQL again (15,000 rows / 253,886,000 JPY) and re-run the
Data Agent checks for T06/T07. Without that approval, keep the manual ingestion and
report it as manual, not automatic.

### Hand-off: time-series binding, Notebook02 and native Metrics (UI)

`handoff-ontology` records that automated TMDL writes stop at the generation2
static core. The Eventhouse time-series binding has no documented definition
format, so it is configured in the Ontology editor:

1. Municipality → **Manage property bindings**: TimeSeries from Eventhouse
   `DonationEvents`, timestamp `DonatedAt` (UTC), key `MunicipalityID` →
   `MunicipalityId`, measure `DonationAmountYen` → `IncomingDonationAmountYen`.
2. Wait for the Ontology update, then confirm 452025 shows 331 observations /
   5,737,000 JPY for August 2026 UTC
   ([checklist §6](../../docs/data-validation-checklist.md#6-municipality-time-series-binding-chapter-14)).
3. Run Notebook02 preview/apply; it expects 10 + 72 + 1 + 15 = 98 objects and stops
   with 97 if the binding is missing (checklist §7).
4. Native Metrics (**Generate Ontology** from the semantic model) and other UI labs
   go into isolated items under **Temp**; do not overwrite the main Ontology.
