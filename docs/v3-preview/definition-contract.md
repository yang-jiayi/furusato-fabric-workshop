# New-experience definition contract / 新experience定義の契約

**Reviewed 2026-09-29. Official documentation discovery, not a deployment result.**
The numeric portal folder/API folder mapping and explicit scoped approval remain
separate preconditions. An empty folder, available participant ID and Active
capacity do **not** open the write gate.

## 正本 / Authority

- [Ontology **(new)** item definition](https://learn.microsoft.com/en-us/rest/api/fabric/articles/item-management/definitions/ontology-definition)
  — updated 2026-09-29, source revision
  `04fe25496ed190acd17fc4af639599d887f9dd00`.
- [Create Ontology](https://learn.microsoft.com/en-us/rest/api/fabric/ontology/items/create-ontology)
  — explicitly distinguishes generation 1 and 2.
- [Get Ontology Definition](https://learn.microsoft.com/en-us/rest/api/fabric/ontology/items/get-ontology-definition)
  and [Update Ontology Definition](https://learn.microsoft.com/en-us/rest/api/fabric/ontology/items/update-ontology-definition)
  — these operation pages still contain old JSON examples. Their example presence
  is not proof that the example produces generation 2.

新形式は **TMDL/TMSL++** です。同じ `Ontology` item typeでも、
旧 `EntityTypes/{id}/definition.json` 形式とは互換payloadではありません。
古いCLI skillのJSON tree、`namespace: usertypes`、`valueType: BigInt`、
`DataBindings` / `Contextualizations` を名前だけv3へ変更してはいけません。

The installed CLI skill's older entity-type JSON tree is useful only as an old
generation-1 contract reference. It does not override the updated new-format
definition article or become generation2 by relabelling.

## Consumer compatibility is a separate qualification

The published Context MCP run retained its own original-ten/84 ledger:
**39 PASS / 38 FAIL / 4 execution-unverified / 3 N/A / 0 preblocked**.
It is not accepted or promoted. A separate native-UI T04 connector diagnostic,
against the correct generation2 Relationships item about40 minutes after publication,
returned:

> Unable to generate code: The request is invalid. This API version is not supported for the specified Ontology item.

Direct Graph and native Ontology-agent routes already worked. **Graph readiness is
not Data Agent consumer compatibility**; do not explain this observation as missing
Graph/data, generalize it to every tenant, or use UI/SDK diagnostics to overwrite the
published-MCP scores.

The explicitly isolated **generation1 consumer-compatibility projection** was created
once and actual generation1/readback verified:53 parts, ten entities,72 static
properties, zero TS, fifteen relationships, the same Lakehouse and no extra source
dataset. A later worker receipt also records managed Graph refresh Completed and
three successful native GQL checks. This is creation/readback/Graph acceptance,
not by itself Data Agent consumer compatibility. The final separate Compat
NativeUI run later executed GQL through that generation1 bridge and returned the
reconciled child-row set. This demonstrates a **scoped consumer benefit**, not a
repair of the generation2 connector; parent aggregation/presentation still failed.

There is **no implicit generation1 fallback or default downgrade**. Preserve the
generation2 new-UI items, native Metrics and TS. Do not claim compatibility passed
unless the actual consumer call is evidenced. The observed gen1 route is opt-in
only; do not migrate every course item or promote the main agent on connection
success. The final fixed-rubric result remains48 PASS/36 FAIL, quality not accepted.
SDK qualification remains separate: the supplied external environment was blocked
by a missing Fabric runtime service-discovery module and submitted zero questions,
not proof that every external SDK environment fails.
For native UI isolation, clicking Clear chat is insufficient: confirm the dialog,
then verify a new conversation ID and one user message in private diagnostics.
Fresh T06 captured three actual KQL steps (wrong-year empty result, range discovery,
correct-year query), with21 cells verified. Its arrival-period wording is not proven,
and neither this diagnostic nor its recorded model/runtime may be inferred from the
UI banner or merged into the published-MCP scores.

## 必須parts・世代 / Parts and generation

| Topic | New contract |
|---|---|
| Create without `definition` | Defaults to generation 2 |
| Create with `definition` | The supplied parts determine the generation |
| Readback identity | `properties.generation` is read-only; verify it, do not send it as an authoring selector |
| Minimal supplied definition | `.platform` and `database.tmdl` |
| Compatibility | `compatibilityLevel: 1000000`, not a Power BI semantic model's ordinary compatibility level |
| Synthesized parts | Service adds omitted `model.tmdl` and `namespaces/default.tmdl`; new empty readback contains four parts |
| Ref semantics | `ref namespace default` belongs in the model; omitting another ref does not exclude a supplied part |
| Envelope | `definition.parts[]` with `path`, UTF-8 `InlineBase64` `payload`, and `payloadType` |

Authoring paths include `tables/*.tmdl`, `entities/{namespace}#{name}.tmdl`,
`entityRelationships.tmdl`, `relationships.tmdl`, `expressions.tmdl`,
`namespaces/*.tmdl`, `rules/*.tmdl` and applicable `metrics/*.tmdl`.
Use names rather than server-derived display names for filenames. Platform metadata
is separate. `updateDefinition` overrides the current definition; this is not a
safe partial-patch assumption.

API/TMDL support is not UI availability proof. The observed Add Entity /
Additional Configuration exposed inheritance, but no namespace selector or
Namespace ribbon command was confirmed in that environment. Keep namespace UI
**unverified**, not globally unsupported, until actual controls and saved results
are captured. Never invent a click path from `namespaces/default.tmdl`.

## 意味を保つ変換 / Semantic mapping

| Old/reference concept | New definition |
|---|---|
| Numeric entity/property IDs | Existing new-format `lineageTag` is the stable identity to preserve; do not infer live identity from a name |
| `entityIdParts` | Singular scalar `keyProperty` in this TMDL surface |
| `valueType: BigInt` / `DateTime` | `dataType: int64` / `dateTime` |
| Flat column binding | `backingConfiguration` containing `valueColumn: table.column` |
| Time-series property | `TimeSeries<T>` plus `type: timeSeries`, `orderingColumn` and exactly one value form |
| Additional backing table | Unnamed `additionalBackingTable` block plus an existing TOM relationship |
| Entity relationship | Either TOM-relationship-backed or junction-table-backed, not a mixture |
| Junction table | Cannot simultaneously be an entity's `backingTable`; both endpoint TOM relationships must exist |
| Entity/relationship namespace | Qualified name and filename; `namespace` and `displayName` are server-derived, not authoring keywords |
| Description | `///` doc-comment, not a `description:` keyword |
| Business rule | `statement` plus correctly indented `ruleReferencedEntity`, `ruleReferencedProperty`, `ruleReferencedRelationship` |

The documented time-series syntax does not prove the physical Eventhouse/KQL
partition/authentication binding is available or correct. Keep a pending-native-
binding status until a real native binding and query are read back. Never transplant
old `KustoTable` JSON into TMDL.

## Metrics: important round-trip limitation

**DAX-backed enrichment/projected metrics require `backingMeasure`, which current
TMDL cannot represent.** The parser rejects the keyword; omitting it is invalid for
those metric kinds, and TMDL round-tripping loses it. `targetScopes` also lacks a
TMDL keyword representation.

- A DAX table `measure` alone does not create an ontology Metric.
- TMDL-authored `explicit` metrics use KQL/SQL/Generic/NaturalLanguage, **not DAX**.
- The course's DAX lab uses native semantic-model generation/grounding and source
  reconciliation, not a fabricated TMDL `backingMeasure` field.
- **Do not blindly replay the full TMDL definition after native Metrics are added.**
- Equal TMDL before/after Version history restore or export/reimport does **not**
  prove projected-metric link restoration. Check native Metric-to-source-model/
  table/measure associations and actual source-owned DAX results separately.
  Do not guess internal V4 endpoints to fill a missing public contract.

Metric種類とDAX ownershipは区別します。public UIのDAX-backed Metrics演習と、
RESTのnon-DAX explicit metricは別の形です。TMDLのparser受理だけでUI接続成功を主張しません。

## Inheritance, reuse and metadata

- `baseEntityType` and `redefines` are immutable after creation. Reparenting through
  Git deploys as delete/recreate, not an in-place stable-ID patch.
- Inheritance/metadata-override/reuse rollout is target-dependent; import can reject
  those fields when the feature is unavailable.
- A model-level `reusableProperty` holds shared metadata, **no independent datatype**.
  The referencing entity property holds its datatype.
- Current UI how-to pages expose synonym editing differently from the richer REST
  definition. UI availability and serializer capability are distinct.
- The current inheritance how-to says entity-level metadata is not inherited, but
  this workshop's actual derived-entity UI labelled Description, Synonyms and
  Additional metadata **Inherited from AdministrativeArea** and prefilled the base
  description. Keep that observation scoped: separately compare stored definition,
  effective UI metadata, explicit overrides/revert and query behavior. Do not repeat
  the non-inheritance statement unqualified or leave an unbound-base description on
  a data-bound child without review.
- Defaults are omitted on readback. Missing default-valued fields are not, by
  themselves, unsupported features.
- Rule `description` and `synonym` may parse but are not re-emitted. Do not promise
  their preservation through TMDL.

## Readback and permission gates

Even though `getDefinition` reads state, the current ontology-specific operation
requires **read and write** permission plus `Item.ReadWrite.All`. Do not follow the
older CLI skill's Reader-only assumption and do not alter permissions to bypass it.
An LRO's 202 is acceptance, not completion. A successful local parse is not service
acceptance, and service acceptance is not a working data binding or actual UI run.

Keep distinct evidence for:

1. Offline source/schema/reference checks.
2. Approved scope and proven portal/API folder mapping.
3. Successful operation and generation-2 readback.
4. Returned native parts and stable lineage.
5. Actual source binding and executed queries.
6. Actual UI controls, screenshots and independent evaluation.

No cloud calls or writes are required to read this reference. The workshop's Word
and bilingual HTML include these constraints in Chapters 4, 12, 14 and 24.
