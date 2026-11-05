"""Compile an unmeasured follow-up candidate without changing the frozen profile.

Offline only. Publication, actual queries and answer-quality acceptance require
separate scoped authorization and new evidence. No model or source is modified.
"""
from __future__ import annotations

import copy
import base64
import hashlib
import re

from measured_contract_profile import DIRECT_KINDS, LIMIT, stage_sources
from source_grounded_profile import inline_part

NAME = "result-fidelity-candidate"
RUN_ANCHOR = (
    "`summarize sum(ObservationCount), sum(ObservedAmountYen), min(FirstObservedAt), "
    "max(LastObservedAt) by WorkshopRunId, SourceFile`, order by run then source file,"
)
RUN_REPLACEMENT = (
    "`summarize sum(ObservationCount), sum(ObservedAmountYen), min(FirstObservedAt), "
    "max(LastObservedAt) by WorkshopRunId, SourceFile, ParticipantAlias`, "
    "order by run, source file, then participant alias,"
)

GLOBAL_REPLACEMENTS = (
    (
        "- Keep date-window boundaries separate from actual observed extrema.",
        "- Keep date-window boundaries separate from actual observed extrema. Copy each returned timestamp "
        "without inferring AM/PM: use 24-hour UTC yyyy-MM-dd HH:mm:ss, not a 12-hour transcription. "
        "Never attach a whole-window aggregate to a per-file row by joining on count or amount.",
    ),
    (
        "- Apply every requested payment, category, geography and period filter to the same transaction population before aggregation and ranking.",
        "- Carry a constraint checklist (payment, category, geography, period, grain, required ID/name pairs) "
        "into each delegated query and compare it with the returned answer. Apply those filters before "
        "aggregation/ranking; stored unfiltered ranks cannot answer a filtered ranking.",
    ),
)

SOURCE_ADDITIONS = {
    "kusto": """
RESULT FIDELITY AND SCOPE
- Preserve actual FirstObservedAt/LastObservedAt values in 24-hour UTC. Project their aggregates as
  FirstObservedAtUtc=min(FirstObservedAt), LastObservedAtUtc=max(LastObservedAt). To remove locale
  ambiguity, format these already-aggregated values with format_datetime(value, 'yyyy-MM-dd HH:mm:ss')
  and retain UTC in headers. Never add/subtract twelve hours or infer time from the file sequence.
- Apply the requested EventMinute window and optional exact SourceFile/WorkshopRunId/ParticipantAlias
  predicates BEFORE summarize. File rows group by WorkshopRunId, SourceFile, ParticipantAlias and
  sum ObservationCount/ObservedAmountYen within each group. Compute a TOTAL row separately from
  the SAME filtered input and union it with the file rows; do not join the total back to every file.
- Count and amount are metrics, not identity keys. Never join a whole-source summary to a per-file
  summary on matching totals, and never conclude that files are missing because such a join is empty.
- Before final output, reconcile the returned file components against the returned TOTAL for the
  same predicates. A mismatch is an explicit unresolved discrepancy, not permission to change a value.
""",
    "lakehouse_tables": """
FILTERED QUERY AND ANSWER FIDELITY
- For a payment/category/geography/date-filtered count or amount ranking, query ot_donation at
  transaction grain, join only owning dimensions on their exact keys, and apply every requested
  predicate before GROUP BY. Resolve the actual PaymentMethod/category literal first. A stored
  nationwide all-payment count/amount/rank is not the filtered result; derive that ranking instead.
- Project stable ID and display name from the SAME dimension row in every named grouping/trace.
  Keep both through final composition; do not trim names or IDs because a table is wide. If a
  requested name cannot be retrieved, retain the exact ID and state that specific unresolved field.
- Audit the final answer against the requested output fields and all query predicates. Do not repair
  a missing filter by changing only the prose or borrow a value from a differently filtered query.
""",
    "semantic_model": """
MEASURE-DEFINITION FIDELITY
- When the question asks why a measure behaves that way, retrieve/inspect its actual definition,
  name the actual DAX function and same-column filter semantics, and quote the relevant expression.
  KEEPFILTERS intersects an existing same-column filter; an ordinary CALCULATE filter can replace it.
  Do not omit KEEPFILTERS from that explanation, coerce BLANK to zero, or generalize its behavior
  to a measure lacking that function. Explain limitations if the definition is unavailable.
- A flag's selected rows and its business predicate are different evidence. When its condition is
  requested, inspect the model column/measure description and owning transformation; report the
  actual operator and threshold, including whether equality is excluded. Do not infer the predicate
  from observed counts or invent a threshold when the metadata cannot establish it.
- Return the requested source components and actual total, with current dimension filters preserved;
  no raw operational result substitutes for a Gold component.
""",
}


def model_contract(model_definition: dict) -> tuple[str, dict]:
    """Extract actual single-line measures and their authored descriptions.

    This deliberately supports only the observed workshop TMDL shape. Unknown
    layouts need review rather than silently losing metadata.
    """
    parts = model_definition.get("definition", model_definition)["parts"]
    measures = []
    provenance = {}
    seen = set()
    for part in parts:
        path = part["path"]
        if path in seen:
            raise ValueError("Duplicate model part path.")
        seen.add(path)
        if not path.startswith("definition/tables/") or not path.endswith(".tmdl"):
            continue
        if part.get("payloadType") != "InlineBase64":
            raise ValueError("Model metadata must be inline TMDL.")
        raw = base64.b64decode(part["payload"], validate=True)
        text = raw.decode("utf-8-sig")
        lines = text.splitlines()
        table_measures = []
        for index, line in enumerate(lines):
            if not line.startswith("\tmeasure "):
                continue
            match = re.fullmatch(r"\tmeasure (.+?) = (.+)", line)
            if not match:
                raise ValueError("Unsupported multiline measure expression.")
            if index + 1 < len(lines) and lines[index + 1].startswith("\t\t\t"):
                raise ValueError("Unsupported multiline measure expression.")
            comments = []
            previous = index - 1
            while previous >= 0 and lines[previous].startswith("\t/// "):
                comments.insert(0, lines[previous].removeprefix("\t/// "))
                previous -= 1
            table_measures.append(line.strip() + ("\nDescription: " + " ".join(comments) if comments else ""))
        if table_measures:
            measures.extend(table_measures)
            provenance[path] = hashlib.sha256(raw).hexdigest()
    if len(measures) != 10 or len(provenance) != 1:
        raise ValueError("Require the observed ten workshop measures in one table.")
    if len({line.splitlines()[0].split(" = ", 1)[0] for line in measures}) != 10:
        raise ValueError("Duplicate model measure names.")
    return (
        "\nACTUAL MODEL METADATA (definition snapshot, not query results)\n"
        + "\n".join(measures)
        + "\nUse these expressions/descriptions for definition questions; execute queries for values. "
        "Descriptions are authored metadata, not proof of executed transformation or fresh data.\n",
        provenance,
    )


def compile_candidate(definition: dict, model_definition: dict) -> tuple[dict, dict]:
    """Clone the full published stage to Draft; retain all other parts exactly."""
    docs, sources, serialization = stage_sources(definition, "published")
    if serialization != "native-ontology-context":
        raise ValueError("This candidate requires the reviewed native Ontology context shape.")
    parts = definition.get("definition", definition)["parts"]
    paths = [part["path"] for part in parts]
    if len(paths) != len(set(paths)):
        raise ValueError("Duplicate definition part paths must be reconciled.")
    prefixes = ("Files/Config/draft/", "Files/Config/published/")
    published = {p for p in paths if p.startswith(prefixes[1])}
    expected = {prefixes[1] + "stage_config.json", *(p for p, _ in sources.values())}
    if published != expected:
        raise ValueError("Unexpected published parts/examples; do not remove or reinterpret them.")
    expected_draft = {p.replace("/published/", "/draft/", 1) for p in expected}
    if {p for p in paths if p.startswith(prefixes[0])} != expected_draft:
        raise ValueError("Unexpected Draft parts/examples; reconcile instead of overwriting.")
    stage = copy.deepcopy(docs[prefixes[1] + "stage_config.json"])
    text = stage["aiInstructions"]
    for anchor, replacement in GLOBAL_REPLACEMENTS:
        if text.count(anchor) != 1:
            raise ValueError("Frozen instruction anchor changed; inspect before compiling.")
        text = text.replace(anchor, replacement, 1)
    if not 0 < len(text.encode("utf-16-le")) // 2 <= LIMIT:
        raise ValueError("Candidate global instructions exceed the service limit.")
    stage["aiInstructions"] = text
    edits = {prefixes[0] + "stage_config.json": stage}
    metadata, model_hashes = model_contract(model_definition)
    for kind in sorted(DIRECT_KINDS):
        source_path, source = sources[kind]
        updated = copy.deepcopy(source)
        instructions = source["dataSourceInstructions"]
        if kind == "kusto":
            if instructions.count(RUN_ANCHOR) != 1:
                raise ValueError("Run-grain instruction anchor changed.")
            instructions = instructions.replace(RUN_ANCHOR, RUN_REPLACEMENT, 1)
        updated["dataSourceInstructions"] = instructions.rstrip() + "\n" + SOURCE_ADDITIONS[kind].strip() + "\n"
        if kind == "semantic_model":
            updated["dataSourceInstructions"] += metadata
        if len(updated["dataSourceInstructions"].encode("utf-16-le")) // 2 > LIMIT:
            raise ValueError("Candidate source instructions exceed the service limit: " + kind)
        edits[source_path.replace("/published/", "/draft/", 1)] = updated
    # Copy original bytes for shared/Published parts and native Ontology context.
    result = []
    for part in parts:
        if not part["path"].startswith(prefixes[0]):
            result.append(copy.deepcopy(part))
    for part in parts:
        if part["path"].startswith(prefixes[1]):
            draft_path = part["path"].replace("/published/", "/draft/", 1)
            if draft_path in edits:
                result.append(inline_part(draft_path, edits[draft_path]))
            else:
                copied = copy.deepcopy(part)
                copied["path"] = draft_path
                result.append(copied)
    return {"parts": result}, {
        "candidate": NAME, "status": "offline-unmeasured", "answerAccuracyAccepted": False,
        "globalInstructionUtf16Units": len(text.encode("utf-16-le")) // 2,
        "changedDraftPaths": sorted(edits), "publishedPartsBytePreserved": True,
        "sourceIdentitiesAndSelectionsPreserved": True, "nativeOntologyPayloadBytePreserved": True,
        "modelOrDataChanges": 0, "cloudCalls": 0, "fewshotsAdded": 0,
        "modelMetadataPartSha256": model_hashes,
    }
