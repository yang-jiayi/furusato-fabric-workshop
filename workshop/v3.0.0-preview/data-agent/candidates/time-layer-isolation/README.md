# Time and source-layer isolation

Focused, opt-in native correction for the two remaining
[2026-10-03 failures](../../../../../docs/v3.0.0/tuning-20261003/README.md):
an explicitly UTC day interpreted as JST, and a Gold measure explanation borrowing
a static-SQL provenance value.

## Narrow changes

- Resolve **filter timezone** separately from **display timezone**. A UTC hour/day
  request does not become a JST day because its wording is Japanese. An explicitly
  JST target day may still request UTC display.
- Pair UTC and JST examples for the same calendar date. Their KQL returns the actual
  UTC filter boundaries and both timezone roles alongside the aggregates.
- Keep query-window boundaries separate from actual observation extrema.
  `WindowStartUtc`/`WindowEndUtc` cannot replace `FirstObservedAtUtc`/
  `LastObservedAtUtc` in a requested observation-range answer.
- Deselect only `dbo.agent_donation_detail.DonationDataLayer` in the isolated Agent.
  This constant provenance tag is not needed for the supported business questions.
  Its physical SQL column and data are not deleted or changed.
- Remove that source-specific literal from coordinator, SQL and Ontology guidance
  and inherited column descriptions. Keep the model's actual `StaticSeed` and
  `RealtimeIncrement` values scoped to `'寄附'[データソース]`.
- Replace the static value-domain example with a payment-only query. Existing
  payment filters, schema-grounding views, source-owned measures and all other
  business fields remain available.
- Require actual scalar model results under the requested outer filter before
  explaining a measure. Preserve all-BLANK rows and make the conclusion agree with
  the effective source-set intersection, not with global source-row existence.
- Keep recipient-municipality rankings at one row per municipality; donor-residence
  components must not become separate recipient municipalities.

[`time_layer_isolation.py`](../../../../../tools/data-agent/time_layer_isolation.py)
compiles a Draft from the existing Published definition. It preserves source IDs,
runtime flags, model definitions and Published parts during preparation, rejects
ambiguous base context, and reports the exact single deselection.
It contains no cloud calls or benchmark answer values.

This is an overlay for the existing complete-contract candidate, not a standalone
empty-Agent bootstrap. Apply it to a reviewed compatible definition and inspect the
diff before staging. Source provenance is intentionally not an exposed query field
in this lane; do not restore it through an instruction-only shortcut.

## Apply and verify

1. Read the current isolated Agent definition and preserve it.
2. Compile the Draft; require unchanged source identities and the one named column
   deselection only.
3. Execute the three changed examples read-only. The paired hour examples must each
   return complete hours, with different correct UTC day boundaries.
4. Stage without changing Published. Inspect native example admission: SQL 15,
   KQL 6, no error or pending status. Direct source-query success does not replace
   this check or prove which example a later answer used.
5. Publish and compare the actual Published parts with the planned Draft.
6. Evaluate the original two failing questions and timezone/source contrast cases
   under unchanged criteria. Keep service failures and uncertainty visible.
   In particular, check that an explicitly JST target day still displays its actual
   observed UTC minimum/maximum, not just the converted midnight boundaries.

No Eventhouse function/table, base data, Power BI measure, role, main Agent or
historical evaluation is changed by the compiler. The previous uncertain question
must not be replayed. A focused passing regression is not a full 32-case rerun,
independent human acceptance or a guarantee for arbitrary future questions.
