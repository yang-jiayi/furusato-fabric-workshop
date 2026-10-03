# Complete-answer source contract

Opt-in native Data Agent tuning after the [2026-10-03 source-grounded experiment](../source-grounded/report-20261003.md).
This configuration is not an external answering service, answer cache, benchmark-answer lookup or automatic promotion.

## Changes

- Separate complete static data retrieval from Ontology relationship-schema explanation.
- Normalize the Japanese seed-year label to the whole snapshot before sending a SQL question.
- Require complete business identity/context columns and reconcile exhaustive supplier lists with the source-owned distinct count.
- Put exact observation grain, synthetic-publication semantics and source-owned filter intersection in both retrieval and response guidance.
- Add selected SQL column descriptions and ten SQL/five KQL examples using reusable patterns, not development-case expected answers.
- Use closed response blocks, source-layer captions and the declared relationship dictionary rather than optional narrative that can contradict correct data.
- Preserve the original donation through a gift-key catalog join, distinguish registry counts from donation counts, and require consecutive ordinal positions for tied ranking rows.

[`answer_contract_profile.py`](../../../../../tools/data-agent/answer_contract_profile.py)
rebases the isolated Agent's Draft from its Published definition, replaces the instruction/example bundles and updates only the named selected column descriptions.
It preserves source identities, selections, runtime flags and all Published parts.
The compiler makes no cloud calls. The operator must separately validate example queries, inspect native example admission, stage, publish and verify readback.

The SQL examples require the four existing [read-side views](../source-grounded/views/).
The coordinator and source instructions are not Power BI Prep data for AI metadata and do not modify source-owned measures.

## Acceptance boundary

Configuration tests and successful source queries do not establish AI-answer accuracy.
Each materially changed candidate is evaluated with the same frozen development questions and criteria, once per case/configuration.
Every failure, unknown and incomplete delivery stays in the denominator; answers are never pooled across rounds.
Only a complete passing development round permits a new, unused source-derived holdout evaluation.
Historical evaluations, release tags and the main Agent remain unchanged until an explicit adoption decision.
