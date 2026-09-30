"""Build a standards-only native-import hypothesis locally; never call Fabric."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sys

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import OWL, RDF, RDFS, SKOS

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "ontology"))
import export_ontology_rdf as rdf_export

SOURCE = ROOT / "workshop" / "v2.7.0" / "ontology" / "rdf" / "furusato-ontology.ttl"
OUTPUT = ROOT / "workshop" / "v3.0.0-preview" / "ontology" / "native-import"
SOURCE_SHA256 = "1e225be41e27dc51ea1ece225f8fa0ed5f66b00a8b21db4b9ee5869ec1a5f64b"
TTL_NAME = "furusato-business-ontology.ttl"
KINDS = (OWL.Class, OWL.DatatypeProperty, OWL.ObjectProperty)
BUSINESS_PREDICATES = {RDF.type, RDFS.label, RDFS.comment, RDFS.domain, RDFS.range}
PREFIXES = {key: value for key, value in rdf_export.PREFIXES.items()
            if key in {"rdf", "rdfs", "owl", "xsd", "furusato"}}
GUID = re.compile(r"\b[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\b", re.I)


class CandidateError(ValueError):
    pass


def require(condition: object, message: str) -> None:
    if not condition:
        raise CandidateError(message)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def counts(graph: Graph) -> dict[str, int]:
    values = {
        "triples": len(graph),
        "classes": len(set(graph.subjects(RDF.type, OWL.Class))),
        "datatype_properties": len(set(graph.subjects(RDF.type, OWL.DatatypeProperty))),
        "object_properties": len(set(graph.subjects(RDF.type, OWL.ObjectProperty))),
        "annotation_property_declarations": len(set(graph.subjects(RDF.type, OWL.AnnotationProperty))),
    }
    for name, predicate in (
        ("domains", RDFS.domain), ("ranges", RDFS.range),
        ("labels", RDFS.label), ("comments", RDFS.comment),
        ("skos_alternative_labels", SKOS.altLabel),
        ("data_bindings", rdf_export.M.hasDataBinding),
        ("contextualizations", rdf_export.M.hasContextualization),
        ("key_annotations", rdf_export.M.keyProperty),
        ("display_property_annotations", rdf_export.M.displayNameProperty),
        ("cardinality_annotations", rdf_export.M.cardinality),
    ):
        values[name] = len(list(graph.triples((None, predicate, None))))
    values["fabric_predicate_triples"] = sum(
        str(predicate).startswith(str(rdf_export.M)) for _, predicate, _ in graph
    )
    return values


def build_candidate(source: Graph) -> Graph:
    candidate = Graph(bind_namespaces="none")
    for prefix, namespace in PREFIXES.items():
        candidate.bind(prefix, namespace)
    classes = set(source.subjects(RDF.type, OWL.Class))
    require(classes, "The source has no declared business classes.")
    subjects: set[URIRef] = set()
    for kind in KINDS:
        for subject in sorted(set(source.subjects(RDF.type, kind)), key=str):
            require(isinstance(subject, URIRef) and str(subject).startswith(str(rdf_export.F)),
                    "Business schema resources must have named workshop IRIs.")
            require(subject not in subjects, "A resource has ambiguous schema kinds.")
            subjects.add(subject)
            if kind == OWL.Class:
                local = str(subject).removeprefix(str(rdf_export.F))
                require(not re.search(r"demo|test|sample", local, re.I),
                        "Non-business entity names are not allowed.")
            labels = set(source.objects(subject, RDFS.label))
            require(labels and all(isinstance(label, Literal) and str(label).strip() for label in labels),
                    f"Missing/nonliteral business label: {subject}")
            candidate.add((subject, RDF.type, kind))
            for predicate in (RDFS.label, RDFS.comment):
                for value in source.objects(subject, predicate):
                    require(isinstance(value, Literal), "Labels and descriptions must be literals.")
                    candidate.add((subject, predicate, value))
            if kind != OWL.Class:
                domains = set(source.objects(subject, RDFS.domain))
                ranges = set(source.objects(subject, RDFS.range))
                require(len(domains) == len(ranges) == 1,
                        f"Domain/range must each be explicit and unambiguous: {subject}")
                domain, range_ = next(iter(domains)), next(iter(ranges))
                require(domain in classes, f"Dangling property domain: {subject}")
                allowed = classes if kind == OWL.ObjectProperty else set(rdf_export.DATATYPES.values())
                require(range_ in allowed, f"Dangling/unsupported property range: {subject}")
                candidate.add((subject, RDFS.domain, domain))
                candidate.add((subject, RDFS.range, range_))
    unexpected = [
        (subject, predicate, value) for subject in subjects
        for predicate, value in source.predicate_objects(subject)
        if not str(predicate).startswith(str(rdf_export.M))
        and predicate not in BUSINESS_PREDICATES | {SKOS.altLabel}
    ]
    require(not unexpected, "Unmapped business axioms require an explicit conversion, not silent loss.")
    original_core = {(s, p, o) for s, p, o in source if s in subjects and p in BUSINESS_PREDICATES}
    require(set(candidate) == original_core, "Business schema projection is not lossless for the selected predicates.")
    ontology = rdf_export.ONTOLOGY_IRI
    require(set(source.subjects(RDF.type, OWL.Ontology)) == {ontology}, "Unexpected ontology identity.")
    candidate.add((ontology, RDF.type, OWL.Ontology))
    candidate.add((ontology, RDFS.label, Literal("Furusato business ontology")))
    candidate.add((ontology, RDFS.comment, Literal(
        "Standards-only business schema derived from the workshop ontology. No data instances, "
        "executable bindings, metrics, keys, temporal behavior or Fabric ALM metadata are included. "
        "Native import compatibility is unverified."
    )))
    for version in source.objects(ontology, OWL.versionInfo):
        candidate.add((ontology, OWL.versionInfo, version))
    return candidate


def turtle_bytes(graph: Graph) -> bytes:
    lines = ["# Generated standards-only native-import candidate; import success is unverified."]
    lines.extend(f"@prefix {prefix}: <{namespace}> ." for prefix, namespace in PREFIXES.items())
    lines.append("")
    lines.extend(" ".join(rdf_export.term_text(term) for term in triple) + " ."
                 for triple in rdf_export.sorted_triples(graph))
    return ("\n".join(lines) + "\n").encode("utf-8")


def artifacts() -> dict[str, bytes]:
    raw = SOURCE.read_bytes()
    require(sha256(raw) == SOURCE_SHA256, "Immutable v2.7.0 RDF changed; do not silently regenerate its replacement.")
    source = Graph().parse(data=raw, format="turtle")
    candidate = build_candidate(source)
    before, after = counts(source), counts(candidate)
    for key, expected in (("classes", 10), ("datatype_properties", 73), ("object_properties", 15),
                          ("domains", 88), ("ranges", 88)):
        require(before[key] == after[key] == expected, f"Source/candidate semantic count mismatch: {key}")
    data = turtle_bytes(candidate)
    require(set(Graph().parse(data=data, format="turtle")) == set(candidate), "Turtle round-trip changed semantics.")
    require(not GUID.search(data.decode("utf-8")), "Candidate contains an environment-shaped identifier.")
    require(str(rdf_export.M).encode() not in data and b"fabric:" not in data,
            "Legacy Fabric vocabulary leaked into the candidate.")
    removed = set(source) - set(candidate)
    added = set(candidate) - set(source)
    business_subjects = {subject for kind in KINDS for subject in source.subjects(RDF.type, kind)}
    manifest = {
        "schema_version": "furusato-native-rdf-candidate/v1",
        "profile": "named OWL classes/properties with RDF/RDFS labels, comments, domain/range and XSD datatypes",
        "source": {"path": SOURCE.relative_to(ROOT).as_posix(), "bytes": len(raw), "sha256": sha256(raw)},
        "candidate": {"file": TTL_NAME, "bytes": len(data), "sha256": sha256(data)},
        "generator": {"path": Path(__file__).relative_to(ROOT).as_posix(),
                      "sha256": sha256(Path(__file__).read_bytes())},
        "source_counts": before, "candidate_counts": after,
        "business_classes": sorted(str(value).removeprefix(str(rdf_export.F))
                                   for value in source.subjects(RDF.type, OWL.Class)),
        "business_schema": {
            "retained_named_subjects": len(business_subjects),
            "all_declared_classes_datatypes_relationships_preserved": True,
            "all_business_labels_comments_domains_ranges_preserved": True,
            "dangling_domains": 0, "dangling_object_ranges": 0, "unsupported_datatype_ranges": 0,
        },
        "omissions": {
            "removed_triples": len(removed),
            "removed_predicates": dict(sorted(Counter(str(p) for _, p, _ in removed).items())),
            "added_triples": len(added),
            "ontology_header": "Label and comment replaced to describe the reduced profile; source ontology IRI/version retained.",
            "legacy_fabric_metadata": "All Fabric mapping predicates and their annotation-property declarations omitted; no opaque JSON/ALM parts.",
            "skos": "Alternative labels and their annotation declaration omitted to keep a minimal RDF/RDFS/OWL/XSD profile.",
            "runtime": [
                "No workspace/item IDs, source connectors, table/column bindings or contextualizations.",
                "No native entity/property IDs, key ordering, display-property selection, relationship cardinality or ALM reconstruction.",
                "The one time-series property's datatype declaration remains; temporal binding and timestamp behavior do not.",
                "Metric-named business classes remain ordinary schema classes, not executable Metrics/DAX definitions.",
                "No overview configuration, instance data, materialization or data refresh behavior.",
            ],
        },
        "native_import": {"attempted": False, "success_proven": False, "product_root_cause_proven": False},
    }
    return {TTL_NAME: data, "manifest.json": (json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")}


def generate(*, check: bool = False) -> dict[str, str]:
    files = artifacts()
    if check:
        require(all((OUTPUT / name).is_file() and (OUTPUT / name).read_bytes() == data
                    for name, data in files.items()), "Missing/stale native-import artifacts.")
    else:
        require(not OUTPUT.is_symlink(), "Refusing a symlink output directory.")
        for name in files:
            target = OUTPUT / name
            require(not target.is_symlink() and (not target.exists() or
                    (target.is_file() and target.stat().st_nlink == 1)), "Unsafe output target.")
        OUTPUT.mkdir(parents=True, exist_ok=True)
        for name, data in files.items():
            (OUTPUT / name).write_bytes(data)
    require(sha256(SOURCE.read_bytes()) == SOURCE_SHA256, "Original RDF changed during generation.")
    return {name: sha256(data) for name, data in files.items()}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Read-only deterministic artifact comparison.")
    args = parser.parse_args()
    try:
        hashes = generate(check=args.check)
    except (CandidateError, OSError) as exc:
        print(f"Native RDF candidate failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({"mode": "check" if args.check else "generate", "sha256": hashes}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
