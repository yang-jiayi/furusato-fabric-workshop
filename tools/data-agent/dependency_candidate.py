"""Separate offline dependency-order candidate; preserves the earlier compiler."""
from __future__ import annotations

import copy

import decomposition_candidate as prior
from evaluate_native import definition_digest
from measured_contract_profile import LIMIT, stage_sources
from source_grounded_profile import inline_part

DEPENDENCY = (
    "- Order dependent subquestions: retrieve the first source's key before querying the next. "
    "Use an exact returned-ID predicate, preserving type, leading zeros and full representation; "
    "verify shared-key identity. Do not fetch all entities or raise caps. "
    "When traversal is needed, supply nonempty target_entities; required_fields is not a target. "
    "A local relationship traversal is not cross-source correlation; a local-only federation "
    "response does not block separate supported source queries. State source-field "
    "key mapping in the final answer. Keep source-specific populations: an operational window "
    "does not filter a static snapshot. For stored national rank, look up the ID without "
    "reranking its single row; if deriving rank, rank the full intended population before "
    "the ID lookup. Keep applicable user filters on that ranking population."
)

# Explicit reviewed rewrites, not whitespace truncation or arbitrary shortening.
COMPACTIONS = (
    (
        "- Source-specific instructions resolve defaults before clarification. Carry their declared "
        "period, timezone, grain and output requirements into the delegated query. An explicit year "
        "for a static-data clause does not set the year for a separate observation clause. Ask for "
        "the year only when the requested source has no applicable default or contains genuinely "
        "ambiguous periods.",
        "- Resolve source defaults before clarification; delegate their period/timezone/grain/output "
        "requirements. A static-clause year never sets an observation-clause year. Ask the year "
        "only if that source has no applicable default or genuinely ambiguous periods.",
    ),
    (
        "- The generation2 Ontology supplies business vocabulary, entity/property/relationship "
        "mappings, metadata and natural-language rules. Its Business Rules are contextual guidance, "
        "not executable validation constraints or Activator actions. A missing source binding is a "
        "limitation, not zero data. Semantic-model grounding attached only to Ontology is NOT "
        "inherited by this Data Agent; use its direct SemanticModel source for DAX.",
        "- Gen2 Ontology supplies vocabulary, entity/property/relationship mappings, metadata and "
        "natural-language rules. Business Rules are context, not executable validation or Activator "
        "actions. Missing binding means limitation, not zero data. Ontology-only model grounding "
        "is NOT inherited; use direct SemanticModel for DAX.",
    ),
    (
        "- The directly configured SemanticModel is the source for governed DAX calculations over "
        "quality-processed Gold. Its DAX measures remain owned by that model. StaticSeed and "
        "RealtimeIncrement are separate DataSource values; never mix them silently. Use "
        "静的寄附総額 and 静的寄附件数 for the static scope, 受入増分寄附総額 and 受入増分寄附件数 for accepted "
        "deduplicated increments. General 寄附総額/寄附件数 include the currently selected sources "
        "and must be labelled accordingly.",
        "- Direct SemanticModel owns governed DAX over quality-processed Gold. Keep DataSource "
        "StaticSeed/RealtimeIncrement separate: 静的寄附総額/静的寄附件数 are static; "
        "受入増分寄附総額/受入増分寄附件数 are accepted deduplicated increments. General 寄附総額/寄附件数 "
        "include selected sources; label that scope. Never silently mix populations.",
    ),
    (
        "- Keep date-window boundaries separate from actual observed extrema. Copy each returned "
        "timestamp without inferring AM/PM: use 24-hour UTC yyyy-MM-dd HH:mm:ss, not a 12-hour "
        "transcription. Never attach a whole-window aggregate to a per-file row by joining on "
        "count or amount. Return both when requested. Preserve source-required UTC headers and "
        "the literal timezone statement when every reported timestamp is UTC. For operational "
        "file summaries preserve WorkshopRunId, SourceFile, ParticipantAlias, raw count, raw "
        "amount, FirstObservedAtUtc and LastObservedAtUtc in the final output. When every "
        "timestamp is UTC, include `All timestamps are UTC.` A correct query alone does not "
        "excuse omitted answer columns.",
        "- Distinguish window boundaries from observed extrema; return both when requested. "
        "Copy timestamps as 24-hour UTC yyyy-MM-dd HH:mm:ss, never infer AM/PM. Never join a "
        "whole-window total to file rows on count/amount. Final operational file summaries "
        "must retain WorkshopRunId, SourceFile, ParticipantAlias, raw count, raw amount, "
        "FirstObservedAtUtc, LastObservedAtUtc and source-required UTC headers. If all timestamps "
        "are UTC, include `All timestamps are UTC.` Correct queries do not excuse omitted columns.",
    ),
    (
        "- Raw observations and the static snapshot have different populations and grains. "
        "Refuse their combined count or amount without calculating or repeating a proposed "
        "combined number. Query and present each requested period separately. For operational "
        "EventID uniqueness or file overlap, when the event identity is unavailable, do not "
        "query or return Gold/DAX accepted counts as the answer or as a possible unique count. "
        "Do not calculate raw-minus-Gold differences as evidence of which events duplicated. "
        "Gold increments are a separate analysis scope and are appropriate only for a separately "
        "explicit Gold question.",
        "- Raw observations and static data differ in population/grain. Refuse combined counts/"
        "amounts without computing or repeating a proposed sum; query/present requested periods "
        "separately. For operational EventID uniqueness/file overlap without event identity, "
        "do not query/return Gold/DAX accepted counts as answers or possible unique counts, "
        "or infer duplicated events from raw-minus-Gold. Analyze Gold increments only for a "
        "separately explicit Gold question.",
    ),
    (
        "- Ontology schema/context and selected entities do not prove an instance query. Claim "
        "GQL or graph traversal only with actual GQL execution and returned results. Other native "
        "Ontology SQL/KQL/DAX results must identify their actual language and source with real "
        "query/result evidence; do not relabel them GQL. A requested relationship-backed count "
        "cannot be silently replaced by a Lakehouse foreign-key count. IncomingDonationAmountYen "
        "remains unavailable as an executed time-series measure unless its source binding and "
        "runtime are verified; static success does not qualify it.",
        "- Schema/context/selected entities do not prove instance queries. Claim GQL/graph "
        "traversal only with executed GQL and returned results. Identify actual source/language "
        "and query/result evidence for native Ontology SQL/KQL/DAX; never relabel them GQL. "
        "Do not silently replace a requested relationship-backed count with a Lakehouse FK "
        "count. IncomingDonationAmountYen is not an executed time-series measure without "
        "verified binding/runtime; static success does not qualify it.",
    ),
)


def compile_candidate(
    agent_definition, model_definition, *,
    expected_agent_sha256=prior.BASE_AGENT, expected_model_part_sha256=prior.BASE_MODEL_PART,
):
    """Build from the same pinned base, retaining r2 model bytes and filter policy."""
    agent, model, prior_receipt = prior.compile_candidate(
        agent_definition, model_definition,
        expected_agent_sha256=expected_agent_sha256,
        expected_model_part_sha256=expected_model_part_sha256,
    )
    docs, _, _ = stage_sources(agent, "draft")
    path = "Files/Config/draft/stage_config.json"
    original = docs[path]["aiInstructions"]
    revised = original
    for before, after in COMPACTIONS:
        if revised.count(before) != 1:
            raise ValueError("Dependency candidate compaction anchor changed.")
        revised = revised.replace(before, after, 1)
    if revised.count(prior.DECOMPOSITION) != 1:
        raise ValueError("Reviewed shared-constraint inheritance changed.")
    inherited_line = next(line for line in revised.splitlines() if line.startswith(prior.DECOMPOSITION))
    revised = revised.replace(inherited_line, inherited_line + "\n" + DEPENDENCY, 1)
    units = prior._units(revised)
    if not 0 < units <= LIMIT:
        raise ValueError("Combined dependency policy exceeds the service limit.")
    config = copy.deepcopy(docs[path])
    config["aiInstructions"] = revised
    next(p for p in prior._parts(agent) if p["path"] == path).update(inline_part(path, config))
    return agent, model, {
        **prior_receipt,
        "candidate": "dependency-order-offline",
        "priorCandidateGlobalUtf16Units": prior_receipt["globalInstructionUtf16Units"],
        "globalInstructionUtf16Units": units,
        "explicitCompactionCount": len(COMPACTIONS),
        "priorModelOutputCanonicalSha256": definition_digest(model),
        "priorModelCandidateBytePreserved": True,
        "priorFilterInheritanceVerbatimPreserved": True,
        "compactionAndDependencyEditsOnly": True,
        "runtimeBehaviorVerified": False,
    }
