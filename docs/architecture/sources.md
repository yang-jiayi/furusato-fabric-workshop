# Architecture evidence / アーキテクチャの根拠

[Architecture home](README.md) · [日本語](overview.ja.md) · [English](overview.en.md)

**Participant edition / 参加者向け版:** Workshop 3.1.0.
Paths such as `workshop/v2.7.0/` and `workshop/v3.0.0-preview/` below are the repository's
actual runtime directories, not the participant-edition number. Links refer to repository
files, not a tenant or deployment.
JSON keys and notebook symbols are stable search anchors within those files.
Public diagrams contain logical labels, `{PID}` placeholders and synthetic dataset contracts.

## Implementation anchors / 実装の参照箇所

| ID | File and anchor | What it establishes / 確認できる内容 |
|---|---|---|
| **S1** | [Single-Agent workshop](../single-agent-workshop.md); [Chapter 17 Lab](../../Lab/17-fabric-data-agent-and-code-interpreter/README.md) | The participant contract has four logical sources: Lakehouse, KQL Database, semantic model and Ontology. Code Interpreter is a tool, not a source; actual query execution must be verified separately from configuration or grounding. |
| **S2** | [Dataset description](../../workshop/v2.7.0/data/DATASET.md), “ファイル一覧”, “増分イベント”, “Ontology 出力テーブル”; [dataset manifest](../../workshop/v2.7.0/data/dataset-manifest.json), `files`, `expected`, `incrementFiles`, `expectedIncrement` | Synthetic classification; eight static CSVs, three increment CSVs; 80,000 static donations; 15,000 raw increment rows, 14,900 distinct EventIDs, 100 duplicates. |
| **S3** | [Current profile-selected Notebook 01](../../workshop/v3.0.0-preview/notebooks/Notebook_01_Furusato_Prepare_Ontology_Data.ipynb), “Typed staging frames and relational validation”, “Ontology-ready derivations”, `stages`, `STAGE_PRIMARY_KEYS` | Static inputs → `stg_*` → eleven `ot_*`; supplier–gift mapping is an edge bridge; validated publication. |
| **S4** | [Full Ontology definition](../../workshop/v2.7.0/ontology/ontology-full-definition-template.json), `expectedContract`, `expectedSourceTables`, `parts`; `IncomingDonationAmountYen`, `SupplierProvidesGift`, `DonorMadeDonation`, `DonationToMunicipality` | 10 entities / 72 static properties / 1 time-series property / 15 relationships / 11 bindings. Exact directed roles and raw `DonationEvents` time-series binding. |
| **S5** | [Pipeline definition](../../workshop/v2.7.0/provisioning/bundle/data-pipeline/pipeline-content.json), `properties.activities[0].typeProperties`; [Eventhouse setup](../../workshop/v2.7.0/kql/Furusato_Eventhouse_Setup_v2.7.0.kql), “agent-safe summary”; [participant contract](../../workshop/v2.7.0/participant-workspace-contract.json), `pipeline`, `activator` | FileCreated → Activator → Pipeline invocation; CSV bytes from `Files/increment` to `DonationEvents`; raw-count MV; trigger initial/final state Off. |
| **S6** | [Current participant tuning contract](../../tools/docs/furusato_docs/participant_current_tuning.py), `current_chapter_spec` and source checks; [unified profile guide](../../tools/data-agent/unified/README.md); [Chapter 17 Lab](../../Lab/17-fabric-data-agent-and-code-interpreter/README.md) | The current participant configuration distinguishes four logical sources and the same-Agent Code Interpreter tool. The packaged provisioning profile is an input bundle, not evidence that its source list is the final tuned Agent configuration. Ontology grounding alone does not establish GQL execution. |
| **S7** | [Current profile-selected Notebook 05](../../workshop/v3.0.0-preview/notebooks/Notebook_05_Furusato_Analytics_Quality_and_BI.ipynb), parameter `INCREMENT_PATH`; runtime `LEGACY_SOURCE_TABLES`, `LEGACY_GOLD_TABLES`, `_build_frames`, `EXPECTED_INCREMENT_CONTRACT`, `CONTROL_TABLE`; [participant contract](../../workshop/v2.7.0/participant-workspace-contract.json), `analyticsExtension` | Actual Lakehouse inputs, same-Lakehouse schemas, deterministic EventID dedupe, quarantine, DQ rules, `DataSource`, publication gate. `LEGACY_GOLD_TABLES` maps to selected `ot_*` inputs. |
| **S8** | [Power BI deployment guide](../../tools/powerbi/README.md); [model tables](../../workshop/v2.7.0/powerbi/Furusato_Analytics.SemanticModel/definition/tables); [relationships](../../workshop/v2.7.0/powerbi/Furusato_Analytics.SemanticModel/definition/relationships.tmdl); [participant contract](../../workshop/v2.7.0/participant-workspace-contract.json), `analyticsExtension.powerBi` | Direct Lake over five `gold` tables; four relationships, six measures, one report page, nine visuals; independent preview/apply and Ready prerequisite. |
| **S9** | [Provisioning guide](../../tools/provisioning/README.md), “Workshop の1体構成” / “Single-Agent workshop mode”; [participant contract](../../workshop/v2.7.0/participant-workspace-contract.json), `workshopProvisioningAutomation`, `analyticsExtension.variableLibraryTemplate`; [current profile-selected Notebook 04](../../workshop/v3.0.0-preview/notebooks/Notebook_04_Furusato_Provision_Complete_Workshop.ipynb), parameter cell | Unified mode, explicit participant scope, preview and exact plan-hash consent, eight planned targets, optional environment configuration. Notebook 02/03 are supporting alternatives. |
| **S10** | [Chapter 24 deployment and client procedures](../../Lab/24-automated-deployment-operations-and-cleanup/README.md); [Activator lifecycle](../../tools/provisioning/activation.md) | The intended trigger route is distinct from an explicitly approved manual fallback. Runtime state is contextual evidence, not a fresh service check. |
| **S11** | [Activator lifecycle](../../tools/provisioning/activation.md), [operator CLI](../../tools/provisioning/manage_activation.py), [runtime and evidence gates](../../tools/provisioning/activation_runtime.py); participant contract `workshopProvisioningAutomation.activationLifecycle` | Official first-start/stop, Running versus verified delivery, complete-file PutBlob/no-overwrite, native event/activation/new Completed Job matching, and separate Copy/KQL gates. |

## Reading rules / 読み取りの要点

1. **Data, signal and query are different paths.** A FileCreated event carries a file reference.
   Pipeline Copy reads its bytes. Agent arrows are query/result exchanges. Ontology binding arrows
   describe model/data associations, including the raw Municipality time series.
2. **The data populations have explicit meanings.** Static `ot_donation` is the teaching snapshot.
   Eventhouse retains raw observations. Optional Gold combines static data with accepted,
   deduplicated increments and keeps `DataSource`.
3. **Configuration, expected counts and runtime observations are separate evidence.** Numerical
   counts here are packaged-data contracts, not a new live execution or an Agent quality score.
   The diagram shows the intended formal-start/verification/formal-stop lifecycle, not live state.

## Directed relationship inventory / 有向関係

The stored direction is shown below. A GQL traversal can follow the appropriate forward or reverse
direction while preserving source and target roles.

| Relationship | Source → target |
|---|---|
| `MunicipalityInPrefecture` | Municipality → Prefecture |
| `DonorLivesInPrefecture` | Donor → Prefecture |
| `SupplierInPrefecture` | Supplier → Prefecture |
| `GiftInCategory` | Gift → GiftCategory |
| `SupplierProvidesGift` | Supplier → Gift |
| `DonorMadeDonation` | Donor → Donation |
| `DonationToMunicipality` | Donation → Municipality |
| `DonationSelectedGift` | Donation → Gift |
| `MunicipalityCatalogsGift` | Municipality → Gift |
| `MunHasCategoryMetric` | Municipality → MunicipalityCategoryMetric |
| `MunMetricForCategory` | MunicipalityCategoryMetric → GiftCategory |
| `PrefHasCategoryMetric` | Prefecture → PrefectureCategoryMetric |
| `PrefMetricForCategory` | PrefectureCategoryMetric → GiftCategory |
| `ResidencePrefHasFlow` | Prefecture → PrefectureDonationFlow |
| `FlowToRecipientPref` | PrefectureDonationFlow → Prefecture |

`SupplierProvidesGift` uses `ot_supplier_gift` for many-to-many catalog registration.
`IncomingDonationAmountYen` uses `DonationEvents` for Municipality-level time-series context.
The latter binds `MunicipalityID`, `DonatedAt` and `DonationAmountYen`, preserving raw observation grain.

## Scope of this documentation work / 今回の作業範囲

This is a static repository architecture map. It makes no claim of live Fabric state,
deployment, ingestion, permission changes or query success. The participant edition is
identified by the current 3.1.0 guide and package, while runtime paths retain their actual names.
