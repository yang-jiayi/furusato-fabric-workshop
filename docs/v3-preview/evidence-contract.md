# Reviewed evidence and source-only reproduction

This contract is for **historical observed runs**, not readiness of a new deployment.
Preview is not GA. Review coverage can include supported passed labs, explicit
unavailable lanes and the preserved metadata-only Act known issue; it is not an
all-features-passed or original-84 acceptance claim.

The final evidence/acceptance decision is frozen as an explicit Preview with known
limitations:48 PASS/36 FAIL, not AI-quality accepted or GA. Runtime optional-bridge
code and Notebook reseal plus the parent's GO now authorize one fresh
`documents/build-024-completion-review` build/QA. Evidence review alone does **not** authorize
a build, cloud action, publication, or a new Agent question.

## 1. Private review input

Keep the existing `furusato-preview30-evidence/v1` manifest outside the clean
source tree. Every requested lab must occur in `labs`, including unperformed,
conditional and failed cases. Each capture retains **both** original and sanitized
files beneath that private manifest directory, their actual SHA-256 digests,
timezone-aware capture date, reviewer, redaction description and bilingual caption.
The existing private loader still rejects missing originals, path escapes, source-tree
image paths, digest mismatches, unreviewed/old UI, private identifiers and inadequate
image dimensions. Public projection is a separate path, not an exception to that gate.

Copy the [all-lab private-input template](../../tools/docs/assets/preview30-private-evidence-template.json)
to a fresh private review directory, then populate it from actual receipts. Its empty
captures and `not-run` states are deliberately not completion evidence.

Capture shape (replace placeholders with reviewed evidence; this example is not evidence):

```json
{
  "id": "p30-15-additive-readback",
  "original": "originals/native-applied.png",
  "sanitized": "reviewed/native-applied.png",
  "originalSha256": "<64 lowercase hexadecimal characters>",
  "sanitizedSha256": "<64 lowercase hexadecimal characters>",
  "capturedAt": "<actual ISO timestamp with timezone>",
  "actualUI": true,
  "experience": "new",
  "reviewed": true,
  "reviewer": "<private reviewer>",
  "redactions": "<actual crop/opaque-mask rectangles; never alter UI values>",
  "redactionReview": "accounts-urls-ids-paths-removed",
  "completionEvidence": true,
  "caption": {
    "ja": "<観測した範囲だけを記載>",
    "en": "<Only the observed scope>"
  }
}
```

Only declare `completionEvidence: true` after the complete required operation and
readback are reviewed. Unknown, unsupported and negative results must not be painted
into successes. The two new additive captures raise the required inventory from
24 to **26** without removing any original requirement:

- `p30-15-additive-plan`
- `p30-15-additive-readback`

Use `preview30-capture-requests.json` as the exact ID/lab/chapter inventory.
Optional `p30-09-manual-recovery` and `p30-10-native-query` placements retain manual
recovery/functional-query scope without replacing automatic-delivery or binding requirements.
The final public artifact need not expose every private diagnostic image. Keep
the native graph image containing the private Source header, raw TS values/query
URIs, Agent answers, benchmark keys and internal reasoning private.

## 2. Separate additive-entity intent

`copilot-act` remains the metadata-only case. Its original eight `ACT_INVARIANTS`
are unchanged; preserving IDs alone cannot pass a lost shared-property reference.
The successful additive lab is **`copilot-additive-entity`**, never a relabelled
metadata-only pass.

```json
{
  "status": "passed",
  "reason": {
    "ja": "承認したEntity/Propertyとmodel refだけを追加。既存partsを保持。",
    "en": "Only the approved entity/property and model reference were added; existing parts preserved."
  },
  "evidenceIds": ["p30-15-additive-plan", "p30-15-additive-readback"],
  "executionAndReadbackObserved": true,
  "intent": {
    "kind": "add-unbound-keyless-entity",
    "entityName": "PaymentMethod",
    "propertyName": "PaymentMethodName",
    "dataType": "string",
    "keyless": true,
    "unbound": true
  },
  "approvedDelta": {
    "addedParts": ["entities/PaymentMethod.tmdl"],
    "removedParts": [],
    "changedExistingParts": ["model.tmdl"],
    "modelReferencesAdded": ["PaymentMethod"],
    "newProperties": [{"name": "PaymentMethodName", "dataType": "string"}]
  },
  "observedDelta": {
    "addedParts": ["entities/PaymentMethod.tmdl"],
    "removedParts": [],
    "changedExistingParts": ["model.tmdl"],
    "modelReferencesAdded": ["PaymentMethod"],
    "newProperties": [{"name": "PaymentMethodName", "dataType": "string"}]
  },
  "invariants": {
    "planLeftDefinitionUnchanged": true,
    "existingPartsExceptModelByteIdentical": true,
    "existingIdsTypesKeysBindingsSharedRefsInheritancePreserved": true,
    "modelOnlyAddsApprovedReference": true,
    "newEntityMatchesApprovedIntent": true,
    "sourceDataUnchanged": true
  }
}
```

The exact deltas must agree with the typed intent. A relationship substituted for
a Business Rule, an extra property/reference, removal, changed existing part, lost
binding/shared reference, or unsupported type rejects a pass. Authoritative private
before/after definitions and approval records remain the evidence behind these
review assertions; no public screenshot or Boolean alone performs that comparison.

The old failed `copilot-act` can be explicitly reviewed as a **known-issue teaching
lane** while retaining `status: "failed"` and actual negative readback:

```json
{
  "knownIssue": {
    "reviewed": true,
    "rollbackVerified": true,
    "failedInvariants": ["sharedPropertyReferencesPreserved", "onlyApprovedMetadataDelta"]
  }
}
```

This is an addition to the failed lab record, which must have actual evidence IDs,
`executionAndReadbackObserved: true`, and `false` for each listed invariant.
Only the metadata-only Act lab permits this coverage disposition. It cannot turn
the original failure into `passed`, excuse AI evaluation failures, or certify
source-data/Metric-rich rollback.
All required negative-case captures must still be present and reviewed as completion
evidence for the observed failure/rollback; an optional preview excerpt alone is insufficient.

## 3. Original-suite aggregate input

Optional `--original-suite-runs` points to a **private, manually reviewed JSON
array** of aggregate records. Never pass the raw result JSON, question/answer
capture, condition matrix or instruction diff. These are the exact allowed fields:

```json
[
  {
    "id": "reviewed-run-id",
    "label": {"ja": "<審査済みrun名>", "en": "<Reviewed portable run label>"},
    "observedAt": "<actual ISO timestamp with timezone>",
    "questionCount": 10,
    "conditionCount": 84,
    "submittedQuestions": 5,
    "preblockedQuestions": 5,
    "counts": {"pass": 22, "fail": 10, "executionUnverified": 1, "blocked": 51, "notApplicable": 0},
    "failureCounts": {"content": 3, "nativeAcceptance": 7},
    "independentExecutionTraces": 0,
    "freshBackendProof": false,
    "promoted": false,
    "accepted": false,
    "summary": {
      "ja": "<失敗種別と分母を区別した公開可能な要約>",
      "en": "<Public-safe summary distinguishing failure kinds and denominators>"
    }
  }
]
```

The illustrated counts describe the historical StaticFirst comparison, **not**
the Context published-MCP result. Replace the label/date only with reviewed provenance.
Context retains `pass:39`, `fail:38`, `executionUnverified:4`, `blocked:0`,
`notApplicable:3`, `submittedQuestions:10`, `preblockedQuestions:0`, and failure
counts `content:31` / `nativeAcceptance:7`; it is not accepted or promoted.
Its later native-UI connector/API-version error is separate diagnostic evidence,
not grounds to change the MCP ledger or blame Graph/data absence.

`notApplicable` is optional only for backwards-compatible zero-NA inputs and is
normalized to zero. Any nonzero value requires a public-safe bilingual
`notApplicableReason`, describing applicability without question text or answers.
For example:

```json
"notApplicableReason": {
  "ja": "記録された回答branchでは3条件が非該当。元84条件の分母に保持。",
  "en": "Three conditions are inapplicable to the recorded answer branches; retained in the original84 denominator."
}
```

Counts must sum to 84, submitted plus preblocked questions to 10, and failure types
to FAIL. Native content-block acceptance failures are not successful contextual
refusals or adjudicated false claims. N/A must not be dropped to claim an81-condition
pass rate. `accepted: true` requires all84 conditions accounted for, every applicable
condition passed, nonempty applicable coverage, ten submitted questions, ten
independently traced executions and fresh-backend proof. Reviewed N/A is not a
passed condition and this flag never means every platform feature passed. No absent
result is invented; UI/SDK diagnostic fields are rejected from these aggregate records.

### Final run method is explicit, not inferred from a banner

An optional `method` object records the actual evaluation surface separately from
historical scores. All fields are required when the object is supplied:

```json
"method": {
  "surface": "native-ui",
  "transport": "responses",
  "stage": "sandbox",
  "runtime": "preview",
  "recordedModel": "gpt-5.6-terra",
  "judgment": "manual-fixed-rubric-offline",
  "distinctBackendConversationsProven": 10,
  "sourceExecutions": {"sql": 5, "gql": 2, "kql": 2},
  "causalAbClaimed": false
}
```

For the final Compat run, `independentExecutionTraces` is **7 question slots**,
not nine calls. The method records **9 actual source executions** across those slots
and ten distinct conversations. The final counts are48/36/0/0/0, with failure
counts `content:29` (content **or required evidence**) and `nativeAcceptance:7`.
`accepted` and `promoted` remain false. Zero unverified cells does not turn missing
required evidence into passes: those failures are in FAIL.

Historical method records may use `surface: "published-mcp"`, `transport: "mcp"`,
`judgment: "recorded-rubric-assessment"`, null stage/runtime/model and null execution
counts where not observed. A null execution count means unknown, not zero.
Native UI and published MCP are not a direct causal A/B. A standalone SDK diagnostic
with zero questions is not an original-suite run and must not be added to this ledger.

## 4. Explicit public projection export

After **authorized visual/privacy and historical-status review**, a full historical
projection may be exported before the final build freeze:

```powershell
python -B .\tools\docs\export_preview30_evidence.py `
  --private-evidence $PrivateReviewedManifest `
  --original-suite-runs $PrivateApprovedRunAggregates `
  --reviewed-at "<actual review ISO timestamp with timezone>" `
  --reviewer "release-review" `
  --freeze-status evidence-frozen-awaiting-runtime-seal `
  --approve-public-projection `
  --out .\docs\assets\v3-preview-evidence
```

The destination must be a **fresh** directory under clean-source `docs\assets`.
It refuses existing output. An optional `--evaluation-report` accepts only the
existing normalized evaluator contract and exports its established approved
projection, not private context/evidence. Rebuild from the published projection
without a private `--evaluation-report` override.

The output is:

```text
docs\assets\v3-preview-evidence\
  manifest.json
  captures\
    <sanitized-sha256>.png
```

`freezeStatus` is now `frozen-for-build` following the recorded runtime/Notebook seal
and parent GO. `evidence-frozen-awaiting-runtime-seal` and
`awaiting-final-consumer-proof` remain recognized earlier states.
It is independent of `approved` (privacy/status review) and of per-lab acceptance.
Only an explicitly reviewed final source freeze may set `frozen-for-build`.
`--require-evidence` rejects a public projection that is not finally frozen even
if its review coverage were otherwise complete. A normal build remains a DRAFT.
The exporter never overwrites a projection: export later revisions to a fresh
source-owned directory, review the exact diff, and let the parent explicitly
promote the reviewed manifest/content-addressed images or select that frozen path.

Public manifest root:

```json
{
  "schemaVersion": "furusato-preview30-public-evidence/v1",
  "scope": "historical-observed-run",
  "approved": true,
  "reviewedAt": "<review ISO timestamp>",
  "reviewer": "release-review",
  "freezeStatus": "frozen-for-build",
  "captures": [],
  "labs": {},
  "originalSuiteRuns": []
}
```

`captures` contains only `id`, relative content-addressed `file`, sanitized
`sha256`, `originalSha256`, `capturedAt`, `reviewedAt`, `actualUI`, `experience`,
`privacyReview`, `completionEvidence`, and `caption: {ja,en}`. `labs` contains the
reviewed safe fields described above for **every** requested lab. Empty arrays in
the root illustration are schematic, not a completed evidence package.

No original image, original path, transcript, endpoint, live UUID, UPN, machine
path, answer, answer key, individual condition text, internal reasoning or raw
instruction is copied. The public loader rejects unknown fields, unsafe strings,
path escapes/symlinks outside the projection, image metadata, mismatched hashes,
inconsistent timestamps and false pass claims. Review roles are portable slugs,
not accounts. Identical sanitized images share one file while preserving distinct
capture provenance and captions. Export bytes are deterministic for frozen inputs.

The public loader verifies **sanitized bytes and reviewed provenance**; it cannot
recheck absent private originals. The export step validates original and sanitized
hashes through the unchanged private boundary before projecting.

### Full-course historical projection now supplied

The default `docs/assets/v3-preview-evidence/manifest.json` now contains the
full-course reviewed historical inventory, not just the attachment subset.
It retains all fifteen native capture placements from build023 plus the six
unchanged source reference diagrams (the prior **21 visuals**), and adds eight
reviewed placements: additive Plan/readback, manual recovery parameters, native
Graph, current four-file upload/Gold context and two conditional ribbon observations.
There are **23 native capture records / 21 unique sanitized PNGs**.

Earlier three-file attachment images remain under explicit historical IDs;
the current four-file panes use the primary attachment IDs. Their actual width is
382 pixels and `completionEvidence` stays false. Nothing was enlarged or padded
to satisfy the600-pixel completion gate. The metadata-only Act remains failed/
rolled back; the separately typed additive intent is the positive case.

The full manifest lists every lab, including receipt-verified progress whose
complete UI capture is still missing. Three original84 aggregate histories are
kept distinct from the final Compat NativeUI evaluation and T04/T06/SDK diagnostics.
The fourth approved aggregate records final48 PASS/36 FAIL with its actual method,
not a rewrite of MCP history. The evidence decision is frozen, but this is **not**
new-deployment readiness or permission to build before runtime/Notebook reseal and GO.

### Public reports

`build_preview30_reports.py` reproducibly generates the sanitized public
`docs/v3-preview/reports/evaluation-summary.json`, `evaluation-report.md`,
`progress-report.md` and their checksums from this source projection. It does not
build Word/HTML/ZIP or read private answers, criterion text or reasoning.
`--check` compares the existing files with those deterministic outputs.
The final package allowlist includes these public reports only when their evidence
hash and final aggregate match the guide.

Future branch/release URLs remain null until actual parent-verified URLs are supplied.
There are no fabricated Preview links, and stable v2.7 artifacts remain unchanged.

### Reviewed attachment-only subset

`docs/assets/v3-preview-gold-attachments/manifest.json` is an approved **partial**
historical projection of the final four-file document-context run. The two native
wide images were cropped to the right pane without resizing or modifying UI
values/states. `capture-review.json` records original filenames/hashes, original
dimensions, crop rectangles, empty mask lists, review dates and sanitized hashes;
raw originals remain private and unchanged. The subset is not the default final
course projection and cannot certify Act, business-query success or original84
accuracy. The parent must preserve this provenance when incorporating it in the
final frozen projection.

## 5. One final build after approval

Do **not** run this during source preparation. After the parent supplies final
AI/attachment receipts, reviews the public projection, and reseals the other
worker's runtime/Notebook outputs:

```powershell
.\tools\docs\Build-Preview30.ps1 -Stage $FreshExternalPrivateStage
```

The default consumes the approved source-owned
`docs\assets\v3-preview-evidence\manifest.json` when it exists, with no private
inputs. For an explicitly selected source-owned projection:

```powershell
.\tools\docs\Build-Preview30.ps1 `
  -Stage $FreshExternalPrivateStage `
  -PublicEvidenceManifest .\docs\assets\v3-preview-evidence\manifest.json
```

Python build/validate/package all accept the same `--public-evidence` option.
It is mutually exclusive with private `--evidence`. Word/HTML/reports use the same
projection and shared content. Outputs remain outside source and existing pairs
are never overwritten. Office/fonts/tool versions still need to match for byte
comparison of rendered binaries; this is source/input determinism, not a promise
that different Word versions paginate identically.

`--require-evidence` remains a separate completeness check. Missing evidence,
unreviewed failures or unperformed lanes reject it. A reviewed known issue remains
failed and unavailable lanes remain unavailable, even when review coverage is complete.
No source-only build certifies a new environment's cloud readiness, performs cloud
operations, promotes an Agent, or publishes a release.

## Focused preparation checks — no document build

```powershell
python -B -m unittest discover -s .\tools\docs\tests -p "test_preview30*.py"
```

Tests use temporary synthetic fixtures and in-memory content models. They verify
privacy/path/hash gates, preserved original ten/84 content, deterministic projection,
private-free source loading, identical-pixel aliases, typed additive intent, and the
unchanged metadata-only Act invariants. They do not generate a Word/HTML/ZIP pair.
