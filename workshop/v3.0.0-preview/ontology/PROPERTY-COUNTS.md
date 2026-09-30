# Count entity properties and backing columns separately

The initial v3 core has **72 explicitly modeled static entity properties** plus
**one explicitly modeled time-series property**. This is the preserved teaching
contract, not a count of every field visible in a binding editor.

The deployed core was also checked through the native `list_ontology_entities`
metadata tool and a fresh generation2 `getDefinition` readback. At that
observation, both returned the same **72 static + 1 time-series** declarations.
No count is substituted for a later edited model: repeat the native inventory
after any UI, Copilot, namespace, inheritance, or binding change.

The backing tables intentionally contain relationship-key columns that are not
additional explicitly declared business properties:

| Entity | Explicit static properties | Explicit time-series | Declared backing-table columns | Relationship-key columns beyond explicit entity properties |
|---|---:|---:|---:|---|
| Prefecture | 9 | 0 | 9 | None |
| Municipality | 7 | 1 | 8 | `PrefectureId` |
| Donor | 11 | 0 | 12 | `PrefectureId` |
| GiftCategory | 7 | 0 | 7 | None |
| Gift | 8 | 0 | 10 | `CategoryId`, `MunicipalityId` |
| Supplier | 6 | 0 | 7 | `PrefectureId` |
| Donation | 11 | 0 | 14 | `DonorId`, `MunicipalityId`, `GiftId` |
| MunicipalityCategoryMetric | 4 | 0 | 6 | `MunicipalityId`, `CategoryId` |
| PrefectureCategoryMetric | 4 | 0 | 6 | `PrefectureId`, `CategoryId` |
| PrefectureDonationFlow | 5 | 0 | 7 | `ResidencePrefectureId`, `RecipientPrefectureId` |
| **Total across entity backing tables** | **72** | **1** | **86** | **14 column occurrences** |

The separate junction table `ot_supplier_gift` contributes two more declared
columns (`SupplierId`, `GiftId`), for **88 columns across all 11 backing tables**.
It is not an eleventh entity. These numbers count the ontology's declared
backing-table columns, not every physical Lakehouse column; technical
publication-generation columns are not included.

For Municipality, the native entity-property response contained the original
seven static properties and `IncomingDonationAmountYen`, which was explicitly
unbound at the observation. Its backing-table definition additionally contained
`PrefectureId` for `MunicipalityInPrefecture`. The binding UI can display that
source/FK field. Do not infer from a visible binding column that a new persistent
entity property was declared, nor label an 86/88-column total as a 72-property
catalog. Capture the exact UI pane and reconcile it with the current native
entity response and TMDL.

## Copilot and shared references

Before approving a Copilot rewrite, compare the complete before/after definition,
not only the requested synonym or description. Preserve reusable-property
definitions, every entity property's reusable-property reference, inheritance
parents, keys, backing bindings and relationship references. A small requested
change is not evidence of a small actual change.

If a shared definition or reference disappears, reject the draft or use a
verified named-version rollback and compare the restored definition to its
baseline. A matching TMDL file set alone still cannot prove restoration of
projected/enrichment Metric `backingMeasure` links, because the current TMDL
serialization does not preserve those links. Native Metric proof remains a
separate gate.
