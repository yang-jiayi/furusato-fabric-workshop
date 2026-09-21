# Architecture evidence / アーキテクチャの根拠

[Architecture home](README.md) · [日本語](overview.ja.md) · [English](overview.en.md)

**Baseline / 基準:** `32d296ebd673df4f180ac56670542cc0eaf350db`, reviewed 2026-09-21.
Links below refer to repository files, not a tenant or deployment.
JSON keys and notebook symbols are stable search anchors within those files.
Public diagrams contain logical labels, `{PID}` placeholders and synthetic dataset contracts.

## Implementation anchors / 実装の参照箇所

| ID | File and anchor | What it establishes / 確認できる内容 |
|---|---|---|
| **S1** | [Single-Agent workshop](../single-agent-workshop.md), “ソースの役割” / English source table | One primary Agent, three sources, post-query Code Interpreter; static, operational and relationship evidence boundaries. |
| **S2** | [Dataset description](../../workshop/v2.7.0/data/DATASET.md), “ファイル一覧”, “増分イベント”, “Ontology 出力テーブル”; [dataset manifest](../../workshop/v2.7.0/data/dataset-manifest.json), `files`, `expected`, `incrementFiles`, `expectedIncrement` | Synthetic classification; eight static CSVs, three increment CSVs; 80,000 static donations; 15,000 raw increment rows, 14,900 distinct EventIDs, 100 duplicates. |
| **S3** | [Notebook 01](../../workshop/v2.7.0/notebooks/Notebook_01_Furusato_Prepare_Ontology_Data.ipynb), “Typed staging frames and relational validation”, “Ontology-ready derivations”, `stages`, `STAGE_PRIMARY_KEYS` | Static inputs → `stg_*` → eleven `ot_*`; supplier–gift mapping is an edge bridge; validated publication. |
| **S4** | [Full Ontology definition](../../workshop/v2.7.0/ontology/ontology-full-definition-template.json), `expectedContract`, `expectedSourceTables`, `parts`; `IncomingDonationAmountYen`, `SupplierProvidesGift`, `DonorMadeDonation`, `DonationToMunicipality` | 10 entities / 72 static properties / 1 time-series property / 15 relationships / 11 bindings. Exact directed roles and raw `DonationEvents` time-series binding. |
| **S5** | [Pipeline definition](../../workshop/v2.7.0/provisioning/bundle/data-pipeline/pipeline-content.json), `properties.activities[0].typeProperties`; [Eventhouse setup](../../workshop/v2.7.0/kql/Furusato_Eventhouse_Setup_v2.7.0.kql), “agent-safe summary”; [participant contract](../../workshop/v2.7.0/participant-workspace-contract.json), `pipeline`, `activator` | FileCreated → Activator → Pipeline invocation; CSV bytes from `Files/increment` to `DonationEvents`; raw-count MV; trigger initial/final state Off. |
| **S6** | [Unified profile guide](../../tools/data-agent/unified/README.md), “Scope”, “Returned asset schema and seals”; [packaged profile](../../workshop/v2.7.0/provisioning/bundle/unified-agent/profile.json), `sources`; [unified contract](../../workshop/v2.7.0/provisioning/bundle/unified-agent/contract.json), `teachingOntologyShape`, `codeInterpreterEnabled`, `createsAIPath` | SQL `ot_*` + three `agent_ref` objects; KQL approved MV + three functions; full teaching Ontology; same-Agent CI preview; exact three-source selection. The unrelated legacy reference bundle is not a fourth active branch. |
| **S7** | [Notebook 05](../../workshop/v2.7.0/notebooks/Notebook_05_Furusato_Analytics_Quality_and_BI.ipynb), parameter `INCREMENT_PATH`; runtime `LEGACY_SOURCE_TABLES`, `LEGACY_GOLD_TABLES`, `_build_frames`, `EXPECTED_INCREMENT_CONTRACT`, `CONTROL_TABLE`; [participant contract](../../workshop/v2.7.0/participant-workspace-contract.json), `analyticsExtension` | Actual Lakehouse inputs, same-Lakehouse schemas, deterministic EventID dedupe, quarantine, DQ rules, `DataSource`, publication gate. `LEGACY_GOLD_TABLES` maps to selected `ot_*` inputs. |
| **S8** | [Power BI deployment guide](../../tools/powerbi/README.md); [model tables](../../workshop/v2.7.0/powerbi/Furusato_Analytics.SemanticModel/definition/tables); [relationships](../../workshop/v2.7.0/powerbi/Furusato_Analytics.SemanticModel/definition/relationships.tmdl); [participant contract](../../workshop/v2.7.0/participant-workspace-contract.json), `analyticsExtension.powerBi` | Direct Lake over five `gold` tables; four relationships, six measures, one report page, nine visuals; independent preview/apply and Ready prerequisite. |
| **S9** | [Provisioning guide](../../tools/provisioning/README.md), “Workshop の1体構成” / “Single-Agent workshop mode”; [participant contract](../../workshop/v2.7.0/participant-workspace-contract.json), `workshopProvisioningAutomation`, `analyticsExtension.variableLibraryTemplate`; [Notebook 04](../../workshop/v2.7.0/notebooks/Notebook_04_Furusato_Provision_Complete_Workshop.ipynb), parameter cell | Unified mode, explicit participant scope, preview and exact plan-hash consent, eight planned targets, optional environment configuration. Notebook 02/03 are supporting alternatives. |
| **S10** | [Existing README](../../README.md), “共通の Fabric 実行経路”, “時間・費用の参考値” / “Common Fabric execution path”; user-provided handoff dated 2026-09-21 | The intended trigger route is distinct from a recorded approved manual fallback. The handoff states Activator was stopped after verified ingestion. Runtime state is contextual evidence, not a fresh service check. |

## Three reading rules / 読み取りの要点

1. **Data, signal and query are different paths.** A FileCreated event carries a file reference.
   Pipeline Copy reads its bytes. Agent arrows are query/result exchanges. Ontology binding arrows
   describe model/data associations, including the raw Municipality time series.
2. **The three populations have explicit meanings.** Static `ot_donation` is the teaching snapshot.
   Eventhouse retains raw observations. Optional Gold combines static data with accepted,
   deduplicated increments and keeps `DataSource`.
3. **Configuration, expected counts and runtime observations are separate evidence.** Numerical
   counts here are packaged-data contracts, not a new live execution or an Agent quality score.
   The diagram shows the supplied stopped-trigger state with that scope.

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

The work read repository files and public icon guidance, authored these documentation assets,
and tested them in a local unauthenticated browser. It performed no Fabric query, ingestion,
deployment, permission change, trigger operation or publication. The parent workflow owns
README integration, video recording, Git synchronization and release publication.
