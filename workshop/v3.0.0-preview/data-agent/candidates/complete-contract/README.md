# Complete-answer source contract

Opt-in native Data Agent tuning after the [2026-10-03 source-grounded experiment](../source-grounded/report-20261003.md).
This configuration is not an external answering service, answer cache, benchmark-answer lookup or automatic promotion.

## Changes

- Separate complete static data retrieval from Ontology relationship-schema explanation.
- Normalize the Japanese seed-year label to the whole snapshot before sending a SQL question.
- Require complete business identity/context columns and reconcile exhaustive supplier lists with the source-owned distinct count.
- Put exact observation grain, synthetic-publication semantics and source-owned filter intersection in both retrieval and response guidance.
- Add selected SQL column descriptions and fifteen SQL/five KQL examples using reusable patterns, not development-case expected answers.
- Use closed response blocks, source-layer captions and the declared relationship dictionary rather than optional narrative that can contradict correct data.
- Preserve the original donation through a gift-key catalog join, distinguish registry counts from donation counts, and require consecutive ordinal positions for tied ranking rows.
- Expose verified Ontology declarations as queryable schema data, rather than asking query generation to infer declared arrows from foreign-key dependencies.
- Preserve the actual static-layer/payment value domains and verify suspicious empty results before reporting that a population does not exist.
- Retain donor identity/residence for short as well as long supplier lists, and explain the source-owned high-value flag as strictly greater than 57,000 yen, excluding equality. This is a business rule, not an embedded answer count.

[`answer_contract_profile.py`](../../../../../tools/data-agent/answer_contract_profile.py)
contains a pure instruction compiler and a structural compiler. Both rebase the isolated Agent's Draft from its Published definition, replace the instruction/example bundles and update the named selected column descriptions.
`compile_contract_draft()` preserves existing selections. The latest `compile_schema_grounded_draft()` additionally selects the two verified views below and deselects the overlapping `ot_pref_category_metric` base table.
Both preserve source identities, runtime flags and all Published parts during Draft preparation.
The compiler makes no cloud calls. The operator must separately validate example queries, inspect native example admission, stage, publish and verify readback.

The SQL examples require the four existing [read-side views](../source-grounded/views/).
The coordinator and source instructions are not Power BI Prep data for AI metadata and do not modify source-owned measures.

## Schema-grounded read-side model

The two additional [SQL view definitions](views/) are additive; they do not change base tables or the four earlier views.

| View | Meaning |
|---|---|
| `agent_relationship_dictionary` | The 15 relationship names and declared source/target entity types, checked against the actual selected STATIC compatibility Ontology definition. It is model metadata, not a table of expected answers or graph-instance execution evidence. |
| `agent_prefecture_category_metric` | Existing stored metric key, recipient prefecture/category identities, count/amount, and both declared relationship names/directions. No test-specific key, filter or numeric answer is embedded. |

Before creating the dictionary, fetch the actual Ontology definition and resolve relationship source/target entity IDs to names. Require exact agreement with all dictionary rows. If the source model changes, reconcile the mirror explicitly; the SQL view does not refresh itself from the Ontology API.
Create the dictionary first, then the metric view. Read back both SQL definitions and compare all metric keys/values with the original table, including row count, distinct-key count and totals. A successful DDL response alone is insufficient.

Use the service-discovered `lakehouse_tables.view` objects and column metadata from the Agent's native Draft. Do not fabricate table nodes, IDs or column types. On the native Data tree, expand the actual view expansion controls, then select only these two views in the isolated Draft to persist the service's identities. Do not click a whole schema row to expand it: that can toggle its selection.
Pass the independently verified `INFORMATION_SCHEMA.COLUMNS` rows to `compile_schema_grounded_draft()`. It rejects missing/duplicate identities or type mismatches and preserves the existing grouped `Schemas > dbo > Tables/Views` hierarchy.

The dictionary is an explicit schema-grounding mirror, not a repair of the primary generation2 connector, a new Ontology item or a claim that native graph queries ran.

## Acceptance boundary

Configuration tests and successful source queries do not establish AI-answer accuracy.
Each materially changed candidate is evaluated with the same frozen development questions and criteria, once per case/configuration.
Every failure, unknown and incomplete delivery stays in the denominator; answers are never pooled across rounds.
Only a complete passing development round permits a new, unused source-derived holdout evaluation.
Historical evaluations, release tags and the main Agent remain unchanged until an explicit adoption decision.

If a previously unused question exposes a failure and is then used to tune a later configuration, it becomes a **known development case**. Preserve its first validation result and re-evaluate the complete expanded cohort on the new configuration. Do not call that rerun independent validation, add earlier passing answers to it, or omit any failed case.
