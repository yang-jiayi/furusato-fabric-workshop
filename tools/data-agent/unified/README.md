# Offline unified Data Agent profile

**Opt-in candidate; this offline builder does not claim native acceptance,
deployment or publication.** **Profile revision 13** retains confirmation-first
donation-data proposals for person wealth/poverty/tax rankings, reconfirms scope
corrections and clears cancelled proposals. It retains the helper-specific UTC
examples, answer evidence/rank scope, row-preserving KQL helpers and source-first
CI input/export checks, with explicit trace identities and raw count/JPY retention. Revision is tracked
separately from the schema identifiers and runtime version `2.7.0`; this is not
an accuracy promotion. Participant setup and response boundaries are described
in [the single-Agent workshop](../../../docs/single-agent-workshop.md).
This profile consolidates the teaching, AI Reference and Code Interpreter roles
in an existing primary Data Agent. It does not create another agent, replace
physical data, change source IDs or authorize a live migration.

Revision 13 tightens selected-gift wording and native result fidelity. A later
disclaimer cannot justify an earlier gift-receipt or delivery claim. Bounded SQL
TVFs retain their complete 22/30-column results without aliases; derived count
ranks are never renamed as stored ranks. KQL helpers retain their 14/17/15-column
contracts, using the same packaged UTC wrappers without fabricated capability
columns or filtering away invalid-window evidence. Additional attributes require
their actual approved owner query. Safety, consent and CI instruction blocks are
byte-identical to revision 12; data, helper definitions, selections and examples
are unchanged. These instructions still require native response verification.

## Scope

| Selected source | Contract |
| --- | --- |
| Lakehouse | The existing 11 `dbo.ot_*` tables / 88 columns, `agent_ref.MunicipalityStatic`, `MunicipalityById` and `DonationTraceById`; unchanged interfaces and Lakehouse few-shots |
| Eventhouse | `DonationObservationSummaryForAgent` / 10 columns and `AgentRawObservationTotals`, `AgentFileRunSummary`, `AgentMunicipalityLeaders` |
| Ontology | **One full teaching Ontology**: 10 entities, 72 static properties, one time-series property, 15 relationships; selected metadata from the released Core `datasource.json` |
| Code Interpreter | Preview enabled for appropriate **post-query** calculations, charts and files; not another data source |

The full Ontology contract also retains 54 definition parts, 11 bindings,
15 contextualizations and one overview. Its numeric mirrors do not change
SQL/KQL ownership. There is no AIPath template or `reference_ontology` creation
module in the returned assets. Never bind both Ontologies.

No benchmark answers, instance IDs, workspace IDs or connection hosts are
embedded in these instructions. Full static scope is a dataset label, not a
calendar filter. Operational counts remain raw observations with possible
duplicates, never stored bucket counts or unique-event metrics. Static and
operational populations cannot be added. Synthetic-ID lookup is allowed;
private-attribute inference and platform-limit bypass are not.

## Confirmation before a reinterpreted question

GLOBAL asks for one filled donation-data proposal with population, period and
metric before any SQL/KQL/GQL/CI call. Person wealth, poverty and tax rankings
always require clarification: donation amount does not establish those attributes.
The default proposed population is all donors; a named geography means donor
residence unless the user specifies recipient municipalities.

An explicit yes applies only to the latest pending proposal. A correction requires
a new proposal and confirmation; no/cancel clears it, and a later bare yes must
not execute the cancelled request. An unrelated clear question may run directly
and clears the older proposal. A generic refusal is not a pending proposal.

This is an author-instruction policy inside the same native Agent, **not an
enforced external consent state machine**. Platform safety may still refuse.
Inspect actual native tool calls and query scope when evaluating it; the offline
builder and finite successful conversations do not establish universal compliance.

## Builder

`tools\provisioning\unified_agent.py` uses only the standard library. Importing
it performs no reads or network operations. All transformations are deep-copy,
deterministic and read-only.

The caller first obtains **verified reference assets**, for example from the
existing `workshop_runtime.load_reference_assets(payload)` offline verifier.
It must not pass raw, unverified bundle text as the first argument.

```python
from unified_agent import (
    build_unified_assets,
    load_profile_files,
    verify_unified_assets,
)

# Explicit local loading of the profile and released Core Ontology metadata:
assets = build_unified_assets(verified_reference_assets, repo_root=repo_root)
report = verify_unified_assets(assets)

# Entirely in memory, suitable for an already sealed Notebook payload:
assets = build_unified_assets(
    verified_reference_assets,
    core_datasource_metadata,
    profile_files,
)
```

The three-positional-argument call above is filesystem-free, including when
the module is embedded without `__file__`. Keyword arguments remain supported.
The first two inputs are parsed asset/JSON mappings; the third contains exact
file text. Only an explicitly supplied `repo_root` enables local loading when
an input is omitted.

`profile_files` maps these **basenames** to exact UTF-8/LF text:
`manifest.json`, `global-instructions.txt`, `lakehouse-instructions.txt`,
`kusto-instructions.txt`, `kusto-fewshots.json`. Exactly three instruction texts
are applied: GLOBAL, Lakehouse SQL and Eventhouse KQL. The extra JSON file holds
KQL query examples, not a fourth source instruction.
`load_profile_files(repo_root)` loads and validates that mapping explicitly.
There is no implicit repository search or fallback GLOBAL.

The second argument accepts either the complete released Core serialized
Ontology datasource or its portable `{description, instructions, elements}`
form. Serialized source/item/workspace IDs are not copied into portable
assets. Core's explicitly present `dataSourceInstructions: null` is required
and preserved. Non-null or missing Ontology instructions are rejected rather
than silently changed or assumed supported. GLOBAL carries the graph policy.

When needed, the explicit `repo_root` loads:

```text
tools\data-agent\unified\*
workshop\v2.7.0\provisioning\bundle\data-agent\Files\Config\published\
  ontology-{{name.ontology}}\datasource.json
```

Neither the reference path template nor a full Ontology definition is read or
materialized by this builder. The canonical full definition is compared in
offline tests, not used as a new deployment template.

### Ontology instruction support is not assumed

There is **no verified public-documentation or native-capability evidence in
this offline package** establishing non-null Ontology datasource instructions.
This is not a claim that the platform forbids them; support is unverified.

The released Core datasource has `dataSourceInstructions: null`. The generic
`reference_agent.optional_text` normalizer and datasource PATCH construction
accept text/null without checking per-source capabilities. Its synthetic
service fixture also accepts either. Passing those offline tests therefore
does not establish that the real Ontology source supports or consumes text.

The explicit, hash-bound policy is `preserve-null-use-global`:

- Keep `sources["ontology"]["instructions"]` explicitly `None` (JSON `null`).
- Preserve the existing Core source description and selected property metadata.
- Deliver native GQL counting/path rules, all 15 relationship declarations,
  scope/role/zero handling and CI boundaries through GLOBAL.
- Keep all graph guidance in GLOBAL, including exact integer IDs and the full
  Donation trace path roles. There is no separate Ontology instruction file
  or non-null datasource instruction payload.

The offline builder does not fetch documentation or run native capability probes.
The separate live profile evaluation does not establish support for non-null
Ontology-specific instructions. Revisiting this conservative policy requires
separate support verification, an explicit profile change and a new seal, not a
silent loader fallback.

## Returned asset schema and seals

The explicit output contract is `furusato-unified-data-agent/v1`. Its fields
are compatible with `reference_agent.draft_with_runtime`,
`verify_definition` and selection/discovery helpers:

- `stageConfig`: copied reference runtime settings; only `aiInstructions` and
  `experimental.codeInterpreterEnabled` /
  `experimental.enableExperimentalFeatures` are replaced. Both flags are
  explicitly `true`.
- `sources`: exactly `lakehouse_tables`, `kusto`, `ontology`. SQL/KQL selection
  descriptions, field contracts and Lakehouse few-shots are unchanged. Source
  instructions are replaced only for SQL/KQL; Ontology selection/description
  and explicit null instructions come from Core. The parsed KQL examples are
  attached only at `sources["kusto"]["fewShots"]`.
- `sqlDdl`, `kqlFunctions`, `moduleSources`: unchanged verified helper text,
  except that the AIPath creation module is deliberately omitted.
- `globalProfile`: hash-pinned `furusato-unified-global/v1`, always `candidate`,
  even if the input reference GLOBAL was accepted; `profileRevision` is `13`.
- `profileManifest`: `furusato-unified-profile/v1`, `offline-only` status,
  revision `13`, expected counts, `preserve-null-use-global` policy and
  text/selection/few-shot fingerprints.
- `publicationDescription`: optional text for the caller's later authorized
  publication step; this builder does not consume it as an operation.
- `contract`: explicit unified mode, `existing-primary` target role,
  `teachingOntology` binding role, `reuse-only` Ontology action, helper inventory,
  profile revision, provenance fingerprints and `sha256` over the complete
  output excluding that one digest field.

Text hashes bind exact UTF-8/LF bytes and character counts; all three applied
instruction texts, including GLOBAL, must be nonempty and at most 15,000
characters. Selection hashes bind canonical JSON excluding source instructions:
sorted keys, UTF-8, `ensure_ascii=False`, compact separators, no non-finite
numbers. This includes source descriptions, element descriptions, native SQL
interface contracts and unchanged Lakehouse few-shots. Core's full property
inventory therefore cannot silently degrade to the 21-property AIPath model.

The base KQL selection fingerprint is unchanged. Only the newly attached KQL
`fewShots` field is excluded when comparing the **unified output** selection;
the reference input still has its original strict precondition. Lakehouse
few-shots and every other selection field remain covered by their original
selection fingerprints.

`files["kusto-fewshots.json"]` separately pins exact UTF-8/LF `sha256`, parsed
`canonicalSha256` and `exampleCount: 3`. Verification checks the parsed examples
even after the enclosing asset seal is recomputed. The bounded query contract
permits only the three actual helper calls followed by null-preserving UTC
extensions of their existing datetime columns, without extra arguments,
invented fields, sampling or additional sources.

Queryable selection verification expects 14 objects / 162 leaves for SQL,
4 objects / 10 leaves for KQL, and 10 entity objects / zero separately selected
leaves for Ontology. Ontology properties remain entity-description inventories,
not invented discovery children. KQL functions remain Available leaf objects;
their actual signatures accept only optional datetime `StartUtc`, `EndUtc`.
SQL `MunicipalityById` has one `varchar(64)` input validated as six ASCII digits;
`DonationTraceById` has one `bigint` input.

Hashes provide reproducible integrity, not a signature, live binding proof or
answer-quality acceptance. The integration must still verify the intended
existing teaching Ontology's actual full definition and source IDs.

## Output and CI evidence

Successful answers retain Source, Scope, Metric and Unit, with explicit
RankScope for rankings. Mixed answers name each actual owner. Supplied-example
refusals and clarifications do not acquire fabricated source-execution claims.
Helper results are already aggregated; use their packaged UTC wrappers rather
than regrouping unique leader rows or aggregating Boolean/metadata fields.
This restriction does not prohibit supported direct-MV custom aggregation.

CI follows completed owner queries and uses actual current-turn inputs.
Missing files are not completed analysis, while a valid empty query result is
not a query failure. CSV/JSON and PNG are the default exports; Office output is
requested explicitly and its downloadability is not assumed. Do not bypass
MIP or other protection to retrieve an output.

These are instructional controls, not a hard orchestration or output-schema
guarantee. Inspect native executed-cell records rather than treating an exported
`.py` reconstruction as execution proof. Validate chart labels as well as data:
Japanese glyphs or dense annotations can still fail even when the CSV values
are correct. Validate the original identity and source-evidence requirements
after any instruction change, not only the specific chart being improved.

The KQL examples call `AgentRawObservationTotals`, `AgentFileRunSummary` and
`AgentMunicipalityLeaders` with their actual `StartUtc, EndUtc` parameters.
Both example bounds are `datetime(null)` for explicitly full-available scope;
no benchmark question, expected value or data-instance key is embedded.
Few-shot UUIDs identify the portable authored examples, not data entities.

**After the helper call**, each query extends every returned datetime column
using `iff(isnull(...), "", strcat(replace_string(format_datetime(...,
"yyyy-MM-dd HH:mm:ss.fffffff"), " ", "T"), "Z"))`. All native column names and
other fields remain present; no underlying function definition changes.
For requested windows, adapt only the bound values and keep the UTC extension.
Examples are structurally verified offline; native execution remains unverified
until the parent performs its separate validation.

File results retain file/run/participant provenance. A successful valid scoped
aggregate zero stays zero with source/scope/units; a missing grouped row or an
unavailable query is not zero. Invalid-window helper zeros are rejected.
Incompatible-addition refusals use a literal two-component frame: copy supplied
numbers unchanged with attribution, source/scope/metric/unit for each component,
the recipient `DonationToMunicipality` declaration, and duplicate/independence
qualification. Query only missing components; never calculate or echo the
combined value, including while refusing it.
CI may use retrieved bounded/full-scope aggregates, never invent complete data
from a preview. An explicit demonstration requires **executed Python and its
output or produced artifact**, not a chart specification. Native GQL paths and
relationship counts remain mandatory where requested.

## Small parent-owned integration hooks

1. Package the module and the five profile files (manifest, three instruction
   texts and KQL few-shot JSON) under an explicit unified
   bundle mode. `ProvisioningConfig.enable_unified_data_agent` defaults to
   `False` and is mutually exclusive with `enable_ai_reference_architecture`;
   the Notebook flag also defaults to `False`. Unified mode uses the existing
   primary `names.data_agent`. Leave legacy Core bytes, reference assets and
   runtime version `2.7.0` unchanged: this is profile consolidation, not an
   accuracy/version promotion. Call `build_unified_assets` with verified inputs
   before any live work, and recheck `verify_unified_assets` before consumption.
2. Bind `bindings["ontology"]` to the verified existing **teaching Ontology**.
   Reuse the same Lakehouse/Eventhouse and their helper surfaces. Do not follow
   the legacy AIPath template/materialization branch or create a test agent.
   Preserve the Ontology's explicit null instructions; do not send non-null
   Ontology source instructions.
3. Existing-primary draft migration belongs to the authorized controller.
   `configure_reference_agent(initialize=True)` still means **new target only**;
   `initialize=False` is exact read-only verification, not a migration API.
   The builder does not weaken either guard. Apply the separate draft migration,
   then use `draft_with_runtime` / `verify_definition(..., stages=("draft",))`
   with the unified assets before the separately gated validation/publication.
4. Use the existing optional `sources["kusto"]["fewShots"]` hook in
   `reference_agent.draft_with_runtime` and `verify_definition`; it adds a KQL
   few-shot part per configured stage. The runtime helper must include that
   hook; this builder does not rewrite helper modules. For publication, consume
   `assets["publicationDescription"]` when present; otherwise retain the legacy
   description. No additional function keyword or source-selection change is
   needed. Do not change existing-target or publication guards.
5. Native validation, publishing and deletion of exactly the obsolete Ref/CI
   agents remain separate parent-owned steps. No such operation is performed
   or authorized by the offline artifact.

## Focused offline validation

```powershell
python -B -m unittest discover -s tools\provisioning -p test_unified_agent.py
```

Tests check counts, full-model selection, immutable helper signatures and
fields, post-helper UTC examples, literal output/safety contracts, independently
sealed few-shots, fail-closed hashes/required fields,
filesystem-free import/transformation and existing reference helpers against
an entirely synthetic in-memory service fixture. They make no live queries.
