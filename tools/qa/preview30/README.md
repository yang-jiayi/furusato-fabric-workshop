# Preview 3.0 evidence gates

An **offline validator**, not a deployment tool, browser, automatic judge, or
source of fabricated test results. It makes no network calls. All live capture,
answers, query traces, exact IDs, candidate snapshots and held-out prompts stay
in an explicitly selected **private directory outside every Git checkout**.
Core checks use the standard library. Publication-image decoding/pixel matching
also supports the existing Word/HTML toolchain's Pillow (optional requirements
in `requirements-image-checks.txt`). Missing WebP decoding is **unverified**, not
silently passed and not misreported as a corrupt document.

## Boundaries and inventory

- Keep the original public ten questions and 84 conditions unchanged. They are
  a transparent regression suite, **not an independent hidden test**.
- `cases.json` adds 26 separate feature cases. Five factual-AI cases require at
  least three predeclared repetitions: 36 slots in the initial inventory.
- Keep structural, source-data, capability, document and AI results separate.
  A successful deployment, schema check or Plan/Act definition change is not AI
  accuracy.
- States are `planned`, `implemented`, `deployed`, `pass`, `fail`, `blocked`,
  `unsupported`, and `unverified`. Local test success is recorded separately,
  not by marking live cases `pass`.
- Every case/repetition remains in the report. Report both the requested
  inventory and the supported denominator, including failures, blockers and
  unsupported features. An `unsupported` claim needs an actual negative
  capability probe. A guess is `unverified`.
- Preserve original engine-routing criteria even if a new architecture cannot
  satisfy them. Record applicability and the reason for every original question;
  do not erase criteria or silently count an alternate engine as original PASS.
- A native DataNotAvailable error is missing evidence, not an empty result, zero,
  or success. Merely discussing that term in a question/explanation is not an
  observed source error.
  Zero submitted/evidence-complete questions means `accuracy: null`.
  Aggregate accuracy also stays null while supported AI inventory is incomplete.
  Source execution failures remain in a separate technical-failure inventory.

| Cases | Evidence gate |
|---|---|
| SCOPE01, DATA01–02 | Verified folder/item/principal scope; static versus raw/accepted observations; native types, dates and grain |
| UI01–03 | Genuine new experience; saved binding identities; all relationship keys/directions; fanout |
| METRIC01 | Semantic-model-owned DAX, named connection, executed DAX and matching source result |
| RULE01–02 | Definition delta separately from factual effect; no executable constraint or Activator-action claim |
| NAMESPACE01 | Qualified names, single-parent is-a, shared-property identity, inherited keys and graph eligibility |
| COPILOT01–02 | Plan/validation/preview/Act/readback separately from factually grounded answers |
| ATTACH01–02 | Actual upload and read/use in that conversation; at most 10 files, each at most 5 MiB; no held-out answers |
| GRAPH01–03 | Explicit selected scope, eligibility, completed materialization, actual GQL, source reconciliation and freshness |
| VERSION01 | Saved/modified/restored definition content; no claim of source-data rollback |
| RDF01–02 | Empty target, import preservation/transformation/loss inventory; TTL/RDF export and scoped re-import, not OWL export |
| MCP01–02, AGENT01 | Actual native discovery, correlated query/response trace; model grounding configured directly on Data Agent |
| DASHBOARD01 | Actual direct integration capability; unavailable is explicitly blocked/unsupported, not a mock lab |
| SCREENSHOT01, DOCUMENT01 | Capture provenance, exact redaction bounds, delivery-size review, real Word/HTML image/link relationships |

## Offline verification

Run from the public source checkout, with a private root provided by the
coordinator. These examples use placeholders, not a live environment.

```powershell
$private = '<absolute private evaluation directory outside Git>'
$env:PREVIEW30_TEST_ROOT = Join-Path $private 'unit-test-runs'
python -B -m unittest discover -s .\tools\qa\preview30\tests -p 'test_*.py'

python -B .\tools\qa\preview30\evaluate.py --private-root $private offline `
  --baseline '<exact public baseline commit>' --label offline-001
```

`offline` exclusively creates a source oracle, byte-preservation receipt, frozen
original suite and **unscored/blocked** feature manifest/report. It verifies all
11 CSV hashes, rows, headers and sizes; computes static/increment totals,
duplicate semantics, periods and derived original graph counts from the CSVs;
and compares the 15 immutable dataset/rubric assets with the supplied Git commit.
Its exit code 0 proves local contracts, not deployment or AI acceptance.

The original harness is reused only for offline extraction:
`tools\data-agent\native_evaluation.py::original_suite`. No original files are
edited. The additional corpus must never enter the participant guides, agent
instructions, few-shots, attachments, public fixtures or answer examples.

## Required live handoff

The evaluator must receive a verified scope before source queries or question
submission. A private readiness JSON contains:

- `workspace_id`, `folder_id`, `portal_folder_id`, `approved_at_utc`,
  `approved_by`, `folder_mapping_verified`, `identity_sha256`;
- `items`: role → `{id, type, workspace_id, folder_id, ready}` using the exact
  authorized identities; `forbidden_item_ids` from the coordinator;
- `read_only_queries_ready` and a separate `questions_authorized`;
- hash-bound `scope_receipt` and `source_readiness_receipt`. Each refers to JSON
  containing `status: "observed"`, the exact `scope_sha256` generated by
  `scope_fingerprint`, and a post-approval `captured_at_utc`;
- private connection metadata: observed SQL/KQL endpoints, database identity,
  named semantic-model connection, actual native MCP/Agent surface, graph scope,
  source watermarks, and frozen baseline/candidate configuration digests.

Items must belong to the exact approved folder or an explicitly registered new
child. A private `folders` map uses each child GUID as its key and records
`workspace_id`, `parent_id`, `newly_created: true`, and a hash-bound `receipt`
containing the native folder's `id`, `workspaceId`, and `parentFolderId`.
Every ancestor must resolve to the approved root; unrelated, old, cyclic or
unproven folders fail closed. Scope fingerprints include this registry.
Ancestry is never inferred from a name, date, participant label or item GUID.
The readiness flag itself is not proof of current source values: execute scoped
read-only source queries before any factual evaluation.
If the private root contains `live-gate.json`, its latest state must be `open`
and its `scope_sha256` must match the current handoff. A closed/unverified gate
overrides older readiness snapshots. An authentication or scope revocation
cannot be undone by simply pointing at an earlier file. Only a fresh coordinator
confirmation of normal authentication and verified scope can reopen that gate.

```powershell
python -B .\tools\qa\preview30\evaluate.py --private-root $private ready `
  --readiness readiness.json --questions --out readiness-check-001.json
```

Only the coordinator/runtime owns writes. Evaluation never creates definitions,
data, roles, settings or capacity changes. Use supported authenticated query
tools and normal permissions; name model connections explicitly. A collector
calling `api.fabric.microsoft.com` must include
`x-ms-fabric-skill: fabriciq-ontology-cli` on every request, LRO poll and retry.
Do not record authorization headers, cookies, tokens or unredacted secrets.
Do not use an old participant's capture, an unrelated Eventhouse or a guessed
endpoint. Reconcile an ambiguous submission; never blindly repeat it.

## Evidence contract

`evidence.schema.json` documents the wire structure; `preview_contract.py`
performs the semantic checks. Start with the manifest produced by `offline`,
then freeze a **new campaign**, actual scope, data, principal, configuration and
prompt inventory before capturing. Do not overwrite the initial campaign.

Each proof includes its kind, actual origin, capture time, `context_sha256`,
allowlisted item IDs, `{path, sha256}` for the original bytes, and an independent
review bound to that hash. Each case must cite every rubric check, with a reason
and exact JSON pointers into those files (or the exact hash for PNG/RDF bytes).
Pointers support `/@json` for native JSON-serialized arguments/results.
Screenshots alone cannot establish numeric source truth.

For `source_query` and `execution_trace`, preserve the unmodified request and
returned body in a capture envelope. `trace` records actual call identity and
JSON pointers to the executed query, structured result, call ID and execution
status. `executed`, `scope_reviewed`, `complete` and `reviewer` are mandatory.
`error_pointer` retains an actual source execution error; it does not produce
invented result rows. Final-answer prose, a suggested query, a source label,
or a merely generated plan is not an executed result.

For factual AI proofs, preserve actual final response text, sent question and
backend conversation/response identity pointers. The trace must correlate to
that same native response, and every native call must be reviewed. An MCP
session ID is **not** a backend conversation ID. The existing answer-only MCP
transport cannot satisfy strict execution observability by itself; retain its
answer evidence but mark strict factual acceptance unverified.

Some semantic checks still require an honest human review. Byte hashes and
JSON attestations cannot independently prove first-party authenticity or the
meaning of an arbitrary UI/API response. Review the native capture and its
source, not only a normalized summary or validator output.

Additional machine checks:

- UI01 requires `generation_pointer` into the actual Get Ontology response
  (`properties.generation` must be integer 2), and `definition_parts_pointer`
  into the actual getDefinition readback. Required gen2 readback parts include
  `.platform`, `database.tmdl` (`compatibilityLevel: 1000000`), `model.tmdl`, and
  `namespaces/default.tmdl`. Legacy `EntityTypes/.../definition.json` remains a
  logical teaching/data reference only, never proof of the new experience.
- DATA01/02 require every `oracle_assertions` key in the catalog to cite the
  corresponding live source value.
- UI02 additionally requires `functional_readback.status_pointer` and
  `rows_pointer` into an actual native Instances/ontology-bound operation receipt.
  Correct Configure labels, binding metadata and successful direct SQL cannot
  substitute for functional source resolution. A native source-kind error is
  a binding-functional failure, not proof that the underlying data is absent.
- METRIC01 uses `metric_reconciliation.dax_pointer` and `source_pointer`.
  `metric_binding` must cite the actual native metric type/backingMeasure,
  source table/measure/DAX expression, and identify `native_ui` or an actually
  `documented_public_contract` surface. A TMDL export alone is not a backing
  measure link, and adding a table measure does not itself create a Metric.
- GRAPH01/02 read `scope` from the graph-scope JSON. `graph_assertions` maps
  `node_count`/`edge_count` to actual GQL-result pointers.
- GRAPH03's `freshness` contains source/graph watermark and readiness pointers;
  the GQL capture must follow materialization.
- VERSION01 uses the same `definition_content_pointer` for saved, modified and
  restored bytes: saved differs from modified, restored equals saved.
- RDF cases' `rdf` field gives `empty_entities_pointer` and `summary_pointer`.
  The latter preserves `preserved`, `transformed`, and `unsupported` arrays,
  including empty arrays rather than omitted categories.
- ATTACH proofs contain actual upload IDs, byte sizes/hashes and conversation
  identity. File generation alone cannot pass.

### Current gen2 serialization limit

The official [new ontology definition contract](https://learn.microsoft.com/en-us/rest/api/fabric/articles/item-management/definitions/ontology-definition)
and [Get Ontology](https://learn.microsoft.com/en-us/rest/api/fabric/ontology/items/get-ontology)
document the generation distinction. The definition page updated September 29,
2026 states that `enrichment`/`projected` metrics require `backingMeasure`, which
has **no TMDL representation** and is lost on the TMDL round trip. A DAX
`explicit` metric is rejected (`ExplicitMetricDaxNotAllowed`). DAX belongs on the
source table/model measure and must be surfaced by a real projection/enrichment
operation. Only explicit non-DAX metrics are currently round-trippable through
getDefinition/updateDefinition.

Require native UI evidence or an evidence-supported public contract for that
link. Merely mentioning V4/ALM JSON in documentation does **not** authorize
guessing internal endpoints. Record this scope/serialization limit in Version
and export/restore evidence; matching TMDL exports alone cannot prove a projected
metric's backing link was restored. Service-elided defaults are not automatically
unsupported fields.

## Selected graphs, screenshots and final documents

The total 109,592 nodes / 297,303 edges is valid **only for the complete original
projection**. `graph_expectations` calculates unfiltered selected-table totals,
requiring both endpoints of every selected relationship. A custom/filtered
graph is blocked until it has its own executed scoped source oracle; it never
falls back to full counts.

For screenshots, retain the original PNG privately and its browser-capture
receipt (tool, exact time, page URL, item ID, raw hash). The published redacted
PNG must have identical channels and identical pixels outside declared
rectangles. An explicitly recorded `crop_box: [left, top, right, bottom]` may
select an unchanged original region; output dimensions must equal that region,
and masks use cropped-image coordinates. Resizing and unrecorded cropping fail.
Masks covering more than 25% are not accepted automatically.
Unsupported PNG encodings fail closed. A reviewer must inspect new-UI identity,
privacy and legibility **at final delivery size**. This does not synthesize
images or label diagrams as live evidence.

An independent capture checklist can be audited without opening a browser:

```powershell
python -B .\tools\qa\preview30\evaluate.py --private-root $private captures `
  --plan '<absolute private screenshots\capture-plan.json>' --out capture-inventory-001.json
```

The plan uses `schemaVersion: 1`, `requestedCaptures` with unique `id`/`chapter`,
and `verifiedCaptures`. Empty verification keeps every required view blocked.
A genuine supplementary observation is retained separately, never counted as
a replacement for an approved required view; duplicate IDs still fail.
A string/checkbox saying “verified” proves nothing. For genuine verification,
also supply `--manifest` and `--readiness`; each verified entry must name
`capture_proof`, `readback_proof`, and `action_proof` from that manifest, their
shared `item_id`, and actual `readback_pointer` / `action_outcome_pointer`.
Normal authentication in a top-level canvas is not evidence that a cross-origin
ontology editor was captured or that a persistable screenshot exists.
Even complete screenshot coverage is not full lab or AI acceptance.

```powershell
python -B .\tools\qa\preview30\evaluate.py --private-root $private document `
  --file '.\docs\<guide>.html' --document-root . --out html-check-001.json
python -B .\tools\qa\preview30\evaluate.py --private-root $private document `
  --file '.\docs\<guide>.docx' --document-root . --out word-check-001.json
```

Local broken targets/anchors, empty media and missing Word relationships fail.
Self-contained PNG and WebP image data URIs are decoded and hashed. Publication
re-encoding must preserve actual image pixels, not merely dimensions or captions.
Also check the actual rendered image geometry: matching image pixels can still
be displayed with distorted proportions (for example, a print CSS height cap
without proportional width adjustment). `rendered_image_geometry` checks native
dimensions against measured PDF image bounds; it does not replace visual review
of final-size text or completeness.
External URLs remain explicitly `external_unverified`; this offline command
does not claim remote link health or visual layout acceptance.

Check the actual generated attachment package independently:

```powershell
python -B .\tools\qa\preview30\evaluate.py --private-root $private attachments `
  --pack-root .\workshop\v3.0.0-preview\attachments `
  --dataset-manifest .\workshop\v2.7.0\data\dataset-manifest.json `
  --private-benchmark heldout\unseen-v1.frozen.json --out attachment-check-001.json
```

This verifies declared file counts/sizes/hashes, PNG decoding, the PDF envelope,
checksum inventory and each actual public CSV's dictionary header. Private
benchmark prompts/keys are scanned for exact normalized matches in plaintext
attachments without copying those terms into the report. This is not OCR,
complete secret detection or PDF/image visual review. Those remain explicitly
unverified, as do actual upload and model read/use.

## Native discovery and exact metadata changes

These commands inspect already-captured private responses; neither makes a
network request or submits an AI question:

```powershell
python -B .\tools\qa\preview30\evaluate.py --private-root $private mcp-discovery `
  --capture handoff\native-mcp-discovery.json --out mcp-discovery-check.json
python -B .\tools\qa\preview30\evaluate.py --private-root $private synonym-diff `
  --before handoff\before.json --after handoff\after.json --restored handoff\restored.json `
  --entity-part 'entities/AdministrativeArea.tmdl' --synonym '行政区域' --out synonym-delta-check.json
```

`--entity-part` is a native definition-part identifier, not a host filesystem
path. Discovery checks negotiated protocol, returned tool names/schemas and
every recorded handshake result. Only advertised names may be invoked: a
fallback mentioned in a tool description is not automatically available.
Initialization and tool discovery establish neither source-query execution nor
Copilot/AI success. Generated/validated runnable code also is not execution.

For the narrowly declared **one entity-synonym addition** experiment, the delta
check removes only that exact authorized addition and protects every other
definition line (including existing description, shared/reusable-property
references, bindings, keys, names and lineage). Stable IDs alone are insufficient
to show that a change preserved the model. A restored baseline is reported
separately and never erases an observed failed candidate. Matching definition
readbacks do not by themselves prove the UI Version-history action or source-data
restoration. Other kinds of metadata edits require their own frozen delta contract.
Use actual business entity names; do not append Demo/Test/Sample/Example merely
to mark an exercise. Isolate experiments by item/folder/namespace instead.
Preserve old raw evidence unchanged after a real rename, then capture new final
screenshots; never digitally replace labels in a historical screenshot.

## Bounded correction and reporting

Freeze the same source data, scope, principal, prompts, rubric and repetition
inventory for baseline and candidate. Use fresh conversations and retain all
predeclared runs (at least three for stochastic cases). A held-out variant used
to choose a change is no longer hidden: move it to regression and use a
separately frozen unseen set. The coordinator selects changes; evaluation only
reads. Stop after two candidates or two identical failures.

```powershell
python -B .\tools\qa\preview30\evaluate.py --private-root $private report `
  --manifest candidate\manifest.json --readiness readiness.json `
  --oracle offline-001\source-oracle.json --out candidate\report-001.json
python -B .\tools\qa\preview30\evaluate.py --private-root $private compare `
  --baseline-manifest baseline\manifest.json --candidate-manifest candidate\manifest.json `
  --readiness readiness.json --oracle offline-001\source-oracle.json `
  --history comparison-history.json --out comparison-001.json
```

Comparison revalidates raw evidence. Changed denominators/context block a
comparison; critical truth failures or baseline regressions reject promotion.
The original 10/84 must also be actually evaluated, not left pending.
No automatic promotion is performed. Actual client latency may be reported
with its capture; CU requires correlated measured native telemetry with value,
unit and operation-ID pointers. Never derive measured CU from time, tokens or
SKU. Reports intentionally do not declare the whole multi-agent workstream
complete; the coordinator must verify all runtime, UI and document deliverables.
