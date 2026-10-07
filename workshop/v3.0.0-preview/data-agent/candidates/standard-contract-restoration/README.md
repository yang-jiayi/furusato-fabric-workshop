# Standard workshop contract restoration

Opt-in native correction found by the
[2026-10-07 fresh deployment evaluation](../../../../../docs/v3.0.0/tuning-20261007/README.md).
On a clean deployment, the `time-layer-isolation` formal Agent scored only
**36/84 and 34/84** on the protected standard ten/84 benchmark. The corrected
profile chain had replaced the original unified instructions and several
standard-question contracts were no longer present.

After six measured configurations the adopted profile returned **74/84 and 73/84**
(ceiling 77/84: T10 is stopped by the native platform content filter and is never
bypassed). The extended development set reached 14/14 factual and 13/14 complete
content. One pre-registered, author-written holdout run returned
**11 PASS / 1 FAIL / 0 UNKNOWN**. This is not an independent human acceptance or
a guarantee for arbitrary questions; see the dated addendum for every round.

Follow-up candidates R7 and R8 (same day) targeted the remaining T09 provenance,
duplicate-existence, completeness and KEEPFILTERS issues. Neither met the adoption
rule recorded before their results. The user then reviewed the results and approved
**adopting R8**, so the files in this folder are now the R8 profile (standard ten/84:
**76/84 and 74/84**; T09 complete in both runs). Two plain-wording candidates (R9,
R10) were evaluated afterwards and not adopted under their pre-recorded rules; their
scores, the R8→R10 diff and a fresh held-out run on R8 are in the
[follow-up record](../../../../../docs/v3.0.0/followup-20261007/README.md).

R8 adds to the R6 contracts: the composite question runs three separate queries
(Eventhouse leader, Lakehouse values and national ranks **without** prefecture
columns, Ontology forward lookup) and starts with the matching-key line; duplicate
existence inside or across files is undecidable without EventID; a final
completeness check before answering; popularity answers carry the values; and the
KEEPFILTERS explanation states that a plain CALCULATE would not return an empty result.

## Root causes and the restored contracts

| Root cause (round 1) | Restored contract |
|---|---|
| A year-less 「8月」 was resolved to the static label 2025, so the August 2026 raw observations returned 0 | Year-less August, “flowed in”, observations, events, files and increments mean the **August 2026 UTC** raw observations; 2025 is used only when written. A zero/contradictory raw result triggers an extent check before any “does not exist” claim |
| Composite questions used one source for everything | Observed values from Eventhouse (duplicate-inclusive), static values and national ranks from Lakehouse, prefecture membership from the Ontology, joined on `MunicipalityId`, never added |
| Standard contracts were lost | Both readings for a bare prefecture (received/resident), popularity on count **and** amount with ID and national scope, Ontology membership `COUNT` with literal relationship/traversal lines, complete donation trace with catalog-vs-fulfillment boundary, file/run headers, no deduplicated count without EventID |
| Incompatible additions were restated | Static + observed addition is refused through a fixed answer form that never writes the user's sum and shows `Recipient schema: Donation -DonationToMunicipality-> Municipality` |
| Numeric and explanation drift | Values copied verbatim (no 約/万/億 paraphrase); ratios computed from returned integers in a fixed three-line form (difference, multiple, growth rate); `CatalogGiftCount` described correctly; DAX explanations limited to the actual `KEEPFILTERS` measure |
| Fragile generated queries | KQL leaders take both metrics from one per-municipality `summarize`; graph lookups use the Japanese suffixed name (never translated) and retry before reporting absence; `MunicipalityId` is a string in the graph |

## Files

| File | Purpose |
|---|---|
| [`global-contract.txt`](global-contract.txt) | Highest-priority coordinator contract, prepended to the existing instructions |
| [`kusto-contract.txt`](kusto-contract.txt), [`lakehouse-contract.txt`](lakehouse-contract.txt), [`ontology-contract.txt`](ontology-contract.txt), [`semantic-model-contract.txt`](semantic-model-contract.txt) | Source-level contracts prepended to each data source's instructions |
| [`description-overrides.json`](description-overrides.json) | Kusto/Ontology source descriptions used for tool routing, and the `CatalogGiftCount` column meaning |
| [`example-changes.json`](example-changes.json) | One KQL replacement (file/run grouping) and five additions (year-less August, observed leaders, view extent, both prefecture readings, static leaders on both metrics) |

[`standard_contract_restoration.py`](../../../../../tools/data-agent/standard_contract_restoration.py)
is the last of the four Agent compilers chained by
[`fresh_grounded_profile.py`](../../../../../tools/data-agent/fresh_grounded_profile.py)
(source-grounded → complete-contract → time-layer-isolation →
standard-contract-restoration). It changes Draft parts only, preserves source IDs,
selections, runtime switches, Published parts, base data and model measures, makes
no cloud calls, enforces the documented 15,000-character instruction limit and
refuses benchmark answer values (`ANSWER_VALUE_GUARD`). Numbers are matched as whole
tokens after normalizing thousands separators and full-width forms, and JSON inputs are
checked as the compiler loads them, so `80,000`, `80000` or an escaped name cannot slip
through. Two existing coordinator
clauses that contradicted the contracts are replaced exactly once or the compile
stops.

## Apply and verify

1. Read the deployed Agent definition and keep it privately.
2. Compile with `compile_fresh_profile` from the actual four sources and the
   verified six-view schema. Expect `globalInstructionsCharacters` ≤ 15,000,
   SQL 17 / KQL 9 examples, unchanged identities and `cloudCalls: 0`.
3. Execute every SQL/KQL example read-only against the real sources
   (26/26 returned rows in the 2026-10-07 deployment).
4. `updateDefinition` with the compiled Draft plus the unchanged Published parts,
   read back, publish through the staging API and confirm Published equals Draft.
5. Evaluate the standard ten/84 twice and keep every failure. Do not tune on a
   holdout; run it once on the final configuration.

The 2026-10-07 tuning used the public Data Agent MCP endpoint, which returns answer
text only: internal SQL/KQL/GQL/DAX remain **UNOBSERVABLE**, so a source named in an
answer is not proof that the tool executed. Platform content-filter blocks (T10) are
reported as failures and escalated, not bypassed.
