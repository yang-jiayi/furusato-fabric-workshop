# Standards-only native RDF import candidate

`furusato-business-ontology.ttl` is a **local input-correction hypothesis**, not
evidence of a product root cause or a successful native import. The native UI
owner must perform the separate import/readback. Nothing here deploys, binds,
refreshes, or publishes an ontology.

The generator parses the immutable
`workshop/v2.7.0/ontology/rdf/furusato-ontology.ttl` with RDFLib and checks its
SHA-256 before producing this candidate. It never rewrites that original.
`manifest.json` records source/output hashes, counts, retained business classes,
and removed predicates. Generated files have no timestamps, absolute paths,
environment IDs, private evaluation answers, or instance data.

## Preserved schema

All **10 named business classes, 73 datatype properties, and 15 directed object
properties** retain their original IRIs, business labels, descriptions, domains,
and ranges. All 88 property domains/ranges are explicit and resolve. The 73
datatype declarations include 72 static properties and the one property whose
source metadata designated it as time-series; retaining its datatype does not
retain temporal behavior.

The 10 classes are Donation, Donor, Gift, GiftCategory, Municipality,
MunicipalityCategoryMetric, Prefecture, PrefectureCategoryMetric,
PrefectureDonationFlow, and Supplier. No stand-in entity names are introduced.

## Deliberate losses

- All legacy `fabric:*` mapping predicates, opaque JSON/ALM content and
  annotation-property declarations are removed.
- Connectors, table/column bindings, contextualizations, native IDs, ordered
  keys, display-property selection, cardinality hints, overviews and source
  configuration are not reconstructable from this candidate.
- SKOS alternative labels are deliberately omitted to keep the input vocabulary
  to RDF, RDFS, OWL and XSD. Business `rdfs:label` and `rdfs:comment` values remain.
- Metric-named classes are ordinary business schema classes, not executable
  Metrics/DAX definitions. Time-series bindings and timestamp behavior are lost.
- The ontology header label/comment now describe this reduced profile. Its
  original ontology IRI and version are retained.

This preserves the complete **declared business schema**, not full Fabric
runtime equivalence or lossless ALM round-tripping. Unsupported or ambiguous
domain/range mappings cause an explicit error rather than a fabricated subset.
An unchanged input does not imply that the native importer accepts this profile.

## Reproduce locally

Use a Python environment with the repository's existing RDFLib dependency.
From the source root:

```powershell
python -B .\tools\provisioning\preview30_native_rdf.py
python -B .\tools\provisioning\preview30_native_rdf.py --check
python -B -m unittest discover -s .\tools\provisioning -p test_preview30_native_rdf.py
```

The checks cover Turtle parsing/round-trip, deterministic bytes, exact core
semantic counts, labels/descriptions, dangling or ambiguous endpoints, datatype
ranges, explicit omissions and the unchanged original hash. They make no
network calls and do not assert native import success.
