"""Offline source-layer qualification over the immutable dependency compiler."""
from __future__ import annotations

import copy

import decomposition_candidate as base
import dependency_candidate as prior
from measured_contract_profile import LIMIT, stage_sources
from source_grounded_profile import inline_part

SOURCE_PATH = "Files/Config/draft/lakehouse-tables-LH_Furusato_101/datasource.json"
BEFORE = (
    "- Lakehouse relationship-key columns may support SQL joins, but Ontology owns modeled "
    "connectivity. In a multi-source question that explicitly asks for a Prefecture relationship, "
    "return the Municipality stable ID and static metrics only; do not use Lakehouse Prefecture "
    "fields as the relationship answer."
)
AFTER = (
    "- Ontology owns modeled connectivity; Lakehouse keys alone do not verify a relationship. "
    "For an identified entity, only after an actual local Ontology query has returned the "
    "requested relationship predicate and related stable ID, a separate exact-key SQL lookup "
    "may return that related entity's requested ID/name attributes. Correlate and state both "
    "sources' exact keys; cite Ontology for the verified relationship and SQL for attributes. "
    "Schema/context alone or a local-only federation response is not that evidence. If the "
    "local relationship is unavailable or unverified, return supported static metrics and "
    "state the relationship limitation; never infer a fallback from foreign keys. This "
    "attribute lookup does not answer membership/containment sets or relationship-backed "
    "counts, and does not satisfy requested GQL/Graph execution. Preserve those runtime "
    "requirements and report a limitation when unavailable; never relabel SQL as GQL."
)


def compile_candidate(agent_definition, model_definition, **pins):
    """Keep r1 global/model bytes; change one qualified Lakehouse policy field."""
    agent, model, receipt = prior.compile_candidate(agent_definition, model_definition, **pins)
    docs, sources, _ = stage_sources(agent, "draft")
    if SOURCE_PATH not in docs:
        raise ValueError("Reviewed Lakehouse source path changed.")
    config = copy.deepcopy(docs[SOURCE_PATH])
    original = config["dataSourceInstructions"]
    if original.count(BEFORE) != 1:
        raise ValueError("Reviewed Lakehouse relationship anchor changed.")
    revised = original.replace(BEFORE, AFTER, 1)
    units = base._units(revised)
    if not 0 < units <= LIMIT:
        raise ValueError("Qualified source instructions exceed the service limit.")
    config["dataSourceInstructions"] = revised
    next(p for p in base._parts(agent) if p["path"] == SOURCE_PATH).update(
        inline_part(SOURCE_PATH, config)
    )
    source_units = {
        kind: base._units(source["dataSourceInstructions"])
        for kind, (_, source) in sources.items() if kind != "ontology"
    }
    return agent, model, {
        **receipt,
        "candidate": "dependency-order-relationship-qualified-offline",
        "changedAgentFields": receipt["changedAgentFields"] + [SOURCE_PATH + ":dataSourceInstructions"],
        "unchangedSourceInstructionUtf16Units": {
            kind: n for kind, n in source_units.items() if kind != "lakehouse_tables"
        },
        "changedSourceInstructionUtf16Units": {"lakehouse_tables": units},
        "sourceIdentitiesSelectionsAndInstructionsPreserved": False,
        "sourceIdentitiesSelectionsAndOtherInstructionsPreserved": True,
        "priorDependencyGlobalBytePreserved": True,
        "priorModelCandidateBytePreserved": True,
        "compactionAndDependencyEditsOnly": False,
        "additionalQualifiedSourceInstructionEdit": True,
        "qualificationIsNotCausalAttributionOrRuntimeProof": True,
    }
