# Source-grounded candidate

[2026-10-03 measured results](report-20261003.md) ·
[Counts and hashes](result-20261003.json).
Final targeted regression: **12 PASS /7 FAIL /1 UNKNOWN on20 prior-development
cases**, not zero-FAIL, independent heldout, original100 acceptance or promotion.

Experimental configuration for a new, isolated Data Agent. It is not applied by
the default deployment and does not replace the frozen2026-10-02 candidate or
its published evaluation.

The previous source guidance simultaneously required supplier fan-out in every
donation projection and forbade that bridge in aggregates. It also prohibited
ordinary SQL registry counts while global guidance recommended them. This
profile replaces those conflicting instructions rather than appending another
global warning.

The instruction-only compiler preserves the four source IDs, selected fields,
underlying data and source-owned model measures. Use an explicitly declared STATIC compatibility
Ontology only; do not silently downgrade the primary generation2 item.
`semantic-model-instructions.txt` is Data Agent source guidance, **not** direct
editing of Power BI Prep data for AI instructions, synonyms or Verified Answers.

SQL/KQL example queries belong only to supported Lakehouse/Eventhouse sources.
Do not add few-shot bundles to Semantic Model or Ontology sources, which do not
support that feature. Validate examples against the live schema/results before
publication; a persisted example is not proof the runtime retrieved it.

## Optional verified read-side model

The `views/` scripts add four SQL analytics endpoint views, not new base data:

| View | Grain and purpose |
|---|---|
| `agent_municipality_snapshot` | One registered municipality, full-snapshot donation metrics and resolved prefecture names; no calendar column to accidentally filter |
| `agent_donation_detail` | One donation with donor/residence, recipient/prefecture and gift/category names; no supplier multiplication |
| `agent_supplier_catalog` | One supplier/gift catalogue pair with the complete supplier catalogue count |
| `agent_donor_catalog_supplier` | One distinct donor/supplier pair through donations and gifts, with the source-computed distinct supplier count |

This is a separate, explicit schema-selection change, not the instruction-only
profile. `compile_view_backed_draft()` selects the four **service-discovered view
objects** and deselects overlapping `ot_donation`, `ot_municipality`, `ot_supplier`
and `ot_supplier_gift` only in the isolated Agent. The base tables, source item
IDs, other sources, original Agent and released evaluations are not replaced.
It respects native `Tables` / `Views` grouping nodes and the observed
`lakehouse_tables.view` type; it must not fabricate a table node for a view.

Create only absent, explicitly scoped view names. Read back each definition and
verify row counts, distinct identities and sums before selecting it. In particular,
the donation detail must preserve one row per donation, catalogue counts must
not shrink with a TOP sample, and donor/supplier pairs must be distinct before
the count is calculated. No GRANT, base-table write or Notebook rerun is needed.

Pass the actual Draft definition and independently retrieved SQL column metadata
(`TABLE_NAME`, `COLUMN_NAME`, `DATA_TYPE`) to the compiler. The function rejects
missing view identities or mismatched columns. Use `view-backed-instructions.txt`
and `view-example-queries.json` for this variant. Preview the complete definition
diff, apply to Draft, verify native readback, then inspect the actual example-query
validation UI before publishing. Direct SQL success does not prove Data Agent
example admission; a SQL connection/validation error can make the agent ignore
an otherwise valid example. Never manually mark a failed example valid.

These scripts and compilers do not publish automatically or certify answer
accuracy. A dedicated candidate and separately frozen evaluation are required.

The new tuning cycle must preserve all old questions, verdicts, spent intents,
uncertain deliveries and safety blocks. Former held-out results cannot be used
for tuning or presented as new independent validation. Any new experiment needs
its own explicit, pre-execution questions, scoring rules and error accounting.
Zero failures on a limited test is not universal accuracy or proof that the old
100-case result reached zero failures.

References:
- [Configuration layers](https://learn.microsoft.com/fabric/data-science/data-agent-configurations)
- [Query-generation best practices](https://learn.microsoft.com/fabric/data-science/data-agent-configuration-best-practices)
- [Supported example-query sources](https://learn.microsoft.com/fabric/data-science/data-agent-example-queries)
- [Public definition format](https://learn.microsoft.com/rest/api/fabric/articles/item-management/definitions/data-agent-definition)
