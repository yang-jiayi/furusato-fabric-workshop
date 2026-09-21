# Native Data Agent SQL reference models

This folder defines the opt-in reference runtime's read-side SQL contract under the
`agent_ref` schema. It does not alter `dbo.ot_*` user tables, permissions,
Fabric items, the Data Agent, the Ontology, or any evaluation input.

## Objects and business grain

| Object | Columns | Grain | Reference Agent selection |
|---|---:|---|---|
| `agent_ref.MunicipalityStatic` | 20 | One row per municipality, including zero-donation municipalities | Direct: static municipality ranking, count, amount, and name |
| `agent_ref.DonationAttributes` | 40 | One row per donation | Internal dependency; not directly selected |
| `agent_ref.GiftCatalogSuppliers` | 29 | One registered `GiftId`/`SupplierId` pair | Internal dependency; not directly selected |
| `agent_ref.MunicipalityById(varchar(64))` | 22 | Zero or one municipality row for a validated exact ID | Direct: exact municipality-ID lookup |
| `agent_ref.DonationById(bigint)` | 42 | Zero or one donation row for an exact ID | Internal reference object; not directly selected |
| `agent_ref.DonationTraceById(bigint)` | 30 | One exact Donation x registered Supplier row; a null-Supplier row when none is registered | Direct: exact Donation trace |

`MunicipalityStatic` explicitly treats donation count as the default
popularity metric. Its nationwide count rank is derived with
`ROW_NUMBER()` over count descending and stable municipality ID ascending.
Stored amount ranks remain separately named amount ranks.

`DonationAttributes` never joins the supplier bridge, so one donation cannot
be multiplied by supplier registrations. It exposes the Donation fact amount,
date, and payment attributes plus donor, residence, recipient, Gift, and
Category identities and descriptive attributes. It intentionally excludes
dimension-level counts, totals, maxima, and ranks because repeating those
aggregates on every Donation row would make them unsafe to sum.

`GiftCatalogSuppliers` preserves every bridge registration and makes no
manufacturing, fulfillment, or shipment claim. It intentionally excludes
Gift and Supplier aggregate metrics repeated at the registration grain.

`DonationTraceById` retains the exact Donation and every matching catalog
registration with a `LEFT JOIN`. `DonationAmountYen` repeats across Supplier
rows and is **non-additive** at this grain. It must not be summed across those
rows, and registration still proves no manufacture, delivery, or fulfillment.

All three lookup functions return the source-generated request echo
(`RequestedMunicipalityId` or `RequestedDonationId`) and
`RetrievalMode='exact-ID lookup'` before the actual entity columns. These
fields are runtime request lineage, not source facts or evaluation answers.
The ranking view has no request-provenance fields.

Municipality lookup input is intentionally `varchar(64)`, not `varchar(6)`,
so a longer malformed value cannot become a valid ID through parameter
truncation. The function requires `DATALENGTH(...) = 6` and six ASCII digits
under a binary UTF-8 collation before comparing with the actual
`MunicipalityId`. Malformed, `NULL`, and unknown municipality IDs return no
rows. Donation callers must validate that input is a non-negative SQL
`bigint`; `NULL` and unknown valid bigint IDs return no rows. The Python
`validate_municipality_lookup_id` and `validate_donation_lookup_id` helpers
implement the client-side syntax/type checks without performing a query.

The static 2025 UTC snapshot is independent of any August 2026 operational
source. No arbitrary JST-year filter is applied.

## Reference corpus scope

These are six **new read-side objects**, not a complete replacement for the
existing Core corpus. Selecting only these objects would omit, among other
things, registered donors with no Donations, catalog entities with no matching
registration or Donation, and broader source dimensions and facts needed by
the original Core question surface. The opt-in reference configuration selects
only `MunicipalityStatic`, `MunicipalityById`, and `DonationTraceById` directly,
while retaining the necessary existing dimensions and facts: the original
11 `dbo` tables and 88 selected columns. The other three objects remain available as governed internal dependencies/reference
definitions, not additional Agent entrypoints. Structural deployment does not
establish native answer-quality acceptance.

The maintained [entrypoint schema](../source-contract/entrypoint-schema.json)
describes the SQL column and parameter interfaces; `trace-schema.json` defines
the trace function. These schemas do not select Agent objects. Selection belongs
to the runtime contract, separately from native catalog verification.

## Safe deployment

`deploy_reference_models.ps1` is plan-only unless `-Apply` is explicitly
provided. All target coordinates and expected identity values are runtime
parameters. The script:

1. validates local DDL and runtime identifiers without authentication in plan-only mode;
2. validates Azure CLI and SQL identities only after explicit `-Apply`;
3. creates all six objects when absent, retains the owner/permissions of an empty existing schema, reuses an entirely exact set, and rejects partial/foreign/mismatched sets;
4. verifies required sources are `USER_TABLE` objects with the native columns/types;
5. checks key uniqueness and source foreign-key integrity;
6. rejects destructive, security, DML, and transaction statements;
7. requires a fresh evidence directory outside the repository, with link/path checks and exclusive file creation;
8. records exact SHA-256 hashes and sanitized before/after catalog evidence, verifying native definitions, all ordered return columns, and input parameters immediately after creation.

Lakehouse SQL analytics endpoints do not provide transactional DDL. If any view
or function deployment fails, the script records completed operations and stops
with an error without dropping anything. Partial deployment is never returned as
success. Review the retained evidence before choosing a separate recovery action;
only an entirely exact object set is reused, and an evidence directory is never
silently reused. Native SQL types are separate provenance; blank serialized
Agent return-type fields must not be filled from this catalog.

Print the deterministic local plan without connecting:

```powershell
python tools/data-agent/reference-models/reference_models.py
```

The PowerShell dry plan is also entirely local and does not claim a live catalog
inspection. An explicitly authorized `-Apply` requires all runtime values.
Notebook 04 instead uses `tools/provisioning/reference_sql.py`, with an injected
SQL-audience token provider, discovered endpoint/database, and preconfigured
pyodbc plus ODBC Driver 18. Its opt-in pre-DDL readiness wait handles missing
source-column propagation only; permission/type conflicts and DDL failures are
not retried. Never store live endpoint, workspace, tenant, subscription, or user
values in this folder.
