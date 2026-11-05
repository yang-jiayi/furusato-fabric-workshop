# Documentation maintenance

The current participant release is the bilingual standalone HTML textbook and
the numbered GitHub Lab. Both are generated from the same model in
`furusato_docs/participant30_text.py`; participant-facing UI captions are in
`participant30_figures.py`. The supported current route produces no Word or PDF
manuals and packages neither format.

Follow [CURRENT_HTML_LAB.md](CURRENT_HTML_LAB.md) for setup, source freezing,
generation, browser validation, packaging and publication checks. Keep release
version labels synchronized with `WORKSHOP_VERSION`; the versioned runtime
profile paths under `workshop/` are compatibility identifiers and are not the
participant edition.

Add a screenshot only when it is a genuine, reviewed UI capture. Keep identity,
private answer records and environment-specific data out of source manifests
and generated participant files. Local build checks do not prove Fabric
deployment, feature readiness or Data Agent answer accuracy.
