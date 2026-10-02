"""Explicit isolated quality candidate; no cloud calls or baseline mutation."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import re
from typing import Any
import uuid

from preview30_runtime import PREVIEW, SafetyError

PROFILE = PREVIEW / "data-agent" / "candidates" / "evidence-first"
FEWSHOT_SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item/dataAgent/definition/fewShots/1.0.0/schema.json"
SOURCES = {"lakehouse_tables", "kusto", "ontology", "semantic_model"}
GLOBAL_LIMIT = 15000


def _examples(rows: list[tuple[str, str]]) -> dict[str, Any]:
    return {
        "$schema": FEWSHOT_SCHEMA,
        "fewShots": [{
            "id": str(uuid.uuid5(uuid.NAMESPACE_URL, "furusato:evidence-first:" + question)),
            "question": question, "query": query,
        } for question, query in rows],
    }


def query_examples() -> dict[str, dict[str, Any]]:
    coverage = """DonationObservationSummaryForAgent
| summarize AvailableRows=sum(ObservationCount) by AvailableYear=getyear(EventMinute), AvailableMonth=getmonth(EventMinute)
| order by AvailableYear asc, AvailableMonth asc"""
    window = """// Substitute the requested calendar month; do not inherit a static dataset year.
let RequestedMonth = 7;
let CandidateYears = DonationObservationSummaryForAgent
    | where getmonth(EventMinute) == RequestedMonth
    | distinct ObservationYear=getyear(EventMinute);
let YearCount = toscalar(CandidateYears | count);
let SelectedYear = toscalar(CandidateYears | summarize max(ObservationYear));
let Scoped = DonationObservationSummaryForAgent
    | where YearCount == 1 and getyear(EventMinute) == SelectedYear and getmonth(EventMinute) == RequestedMonth;
"""
    files = window + """Scoped
| summarize RawObservationCount=sum(ObservationCount), RawObservedAmountYen=sum(ObservedAmountYen),
    FirstObservedAtUtc=min(FirstObservedAt), LastObservedAtUtc=max(LastObservedAt)
    by SourceFile, WorkshopRunId, ParticipantAlias
| extend FirstObservedAtUtc=strcat(replace_string(format_datetime(FirstObservedAtUtc, 'yyyy-MM-dd HH:mm:ss'), ' ', 'T'), 'Z'),
    LastObservedAtUtc=strcat(replace_string(format_datetime(LastObservedAtUtc, 'yyyy-MM-dd HH:mm:ss'), ' ', 'T'), 'Z')
| order by SourceFile asc, WorkshopRunId asc, ParticipantAlias asc"""
    raw = window + """Scoped
| summarize RawObservationCount=sum(ObservationCount), RawObservedAmountYen=sum(ObservedAmountYen),
    FirstObservedAtUtc=min(FirstObservedAt), LastObservedAtUtc=max(LastObservedAt)
| where YearCount == 1
| extend FirstObservedAtUtc=strcat(replace_string(format_datetime(FirstObservedAtUtc, 'yyyy-MM-dd HH:mm:ss'), ' ', 'T'), 'Z'),
    LastObservedAtUtc=strcat(replace_string(format_datetime(LastObservedAtUtc, 'yyyy-MM-dd HH:mm:ss'), ' ', 'T'), 'Z')
| extend RawIdentityAvailable=false"""
    leaders = window + """let Totals = materialize(Scoped
    | summarize RawObservationCount=sum(ObservationCount), RawObservedAmountYen=sum(ObservedAmountYen) by MunicipalityID);
union (Totals | sort by RawObservedAmountYen desc, MunicipalityID asc | take 1 | extend Metric='amount'),
    (Totals | sort by RawObservationCount desc, MunicipalityID asc | take 1 | extend Metric='count')
| project Metric, MunicipalityID, RawObservationCount, RawObservedAmountYen"""
    trace = """-- Substitute the exact requested DonationId, not a name or geographic label.
SELECT 'Lakehouse SQL' AS AttributeSource,
    'static 2025 snapshot' AS AttributeDataset,
    'Donation x catalog Supplier; amount belongs to one Donation' AS AttributeGrain,
    d.DonationId, d.DonationAmountYen,
    donor.DonorId, donor.DonorName,
    donor.PrefectureId AS DonorResidencePrefectureId, donor_pref.PrefectureName AS DonorResidencePrefectureName,
    municipality.MunicipalityId, municipality.MunicipalityName,
    municipality.PrefectureId AS RecipientPrefectureId, recipient_pref.PrefectureName AS RecipientPrefectureName,
    gift.GiftId, gift.GiftName, category.CategoryId, category.CategoryName,
    supplier.SupplierId, supplier.SupplierName,
    supplier.PrefectureId AS SupplierPrefectureId, supplier_pref.PrefectureName AS SupplierPrefectureName
FROM dbo.ot_donation AS d
INNER JOIN dbo.ot_donor AS donor ON donor.DonorId=d.DonorId
INNER JOIN dbo.ot_prefecture AS donor_pref ON donor_pref.PrefectureId=donor.PrefectureId
INNER JOIN dbo.ot_municipality AS municipality ON municipality.MunicipalityId=d.MunicipalityId
INNER JOIN dbo.ot_prefecture AS recipient_pref ON recipient_pref.PrefectureId=municipality.PrefectureId
INNER JOIN dbo.ot_gift AS gift ON gift.GiftId=d.GiftId
INNER JOIN dbo.ot_gift_category AS category ON category.CategoryId=gift.CategoryId
LEFT JOIN dbo.ot_supplier_gift AS catalog ON catalog.GiftId=gift.GiftId
LEFT JOIN dbo.ot_supplier AS supplier ON supplier.SupplierId=catalog.SupplierId
LEFT JOIN dbo.ot_prefecture AS supplier_pref ON supplier_pref.PrefectureId=supplier.PrefectureId
WHERE d.DonationId=5000422
ORDER BY supplier.SupplierId;"""
    return {
        "kusto": _examples([
            ("List the available operational observation years and months before resolving a year-free period.", coverage),
            ("Show file and workshop-run raw observations for July, resolving the sole available observation year.", files),
            ("Show raw observation totals for July and whether the selected view exposes raw deduplication identity.", raw),
            ("Show both count and amount municipality leaders for July, resolving the sole available operational year.", leaders),
        ]),
        "lakehouse_tables": _examples([
            ("Retrieve the complete SQL attribute ledger for donation 5000422, including every catalog supplier ID/name and explicit source/dataset/grain, separately from Ontology connectivity. Catalog registration is not fulfillment.", trace),
        ]),
    }


def canonical_relationship_grounding() -> str:
    """Project names/direction from the existing contract, never instance data."""
    contract = json.loads((PREVIEW / "ontology" / "relationships" / "contract.json").read_text(encoding="utf-8"))
    relations = contract["relationships"]
    if len(relations) != contract["relationshipTypes"] or len({row["name"] for row in relations}) != len(relations):
        raise SafetyError("Canonical relationship declarations are incomplete or duplicate.")
    lines = []
    for row in relations:
        names = [row["fromEntity"], row["name"], row["toEntity"]]
        if any(not isinstance(name, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", name) for name in names):
            raise SafetyError("Non-portable canonical relationship label.")
        lines.append(f"- {names[0]} -{names[1]}-> {names[2]}")
    return (
        "\nCANONICAL SAVED RELATIONSHIP DECLARATIONS\n"
        "The following case-sensitive names/directions are projected from the portable ontology contract. "
        "Require matching connected-source grounding before use. They are schema metadata, not evidence of an instance query. "
        "Pass actual declarations in the source request; never derive an entity or relation label from a result alias.\n"
        + "\n".join(lines) + "\n"
    )


def build_candidate(stage: dict[str, Any], *, profile: Path = PROFILE) -> tuple[dict[str, Any], dict[str, Any]]:
    """Replace only guidance/examples; preserve sources, selections and runtime."""
    if not isinstance(stage, dict) or "stage_config.json" not in stage:
        raise SafetyError("Provide a decoded frozen stage, not a full live definition.")
    sources = [(path, value) for path, value in stage.items() if path.endswith("/datasource.json")]
    if any(not isinstance(value, dict) for _, value in sources):
        raise SafetyError("Each source must be a decoded datasource object.")
    if len(sources) != 4 or {value.get("type") for _, value in sources} != SOURCES:
        raise SafetyError("The frozen four-source selection is required.")
    config = stage["stage_config.json"]
    if not isinstance(config, dict) or not isinstance(config.get("experimental"), dict):
        raise SafetyError("Provide the frozen stage configuration and runtime settings.")
    if config.get("experimental", {}).get("codeInterpreterEnabled") is not True:
        raise SafetyError("Preserve the existing CI-enabled runtime.")
    global_text = (profile / "global-instructions.txt").read_text(encoding="utf-8") + canonical_relationship_grounding()
    if "\r" in global_text or not 0 < len(global_text) <= GLOBAL_LIMIT:
        raise SafetyError("GLOBAL must use LF and remain within its existing budget.")
    result = copy.deepcopy(stage)
    result["stage_config.json"]["aiInstructions"] = global_text
    instructions = {
        "kusto": "kusto-instructions.txt",
        "ontology": "ontology-instructions.txt",
        "lakehouse_tables": "lakehouse-instructions.txt",
        "semantic_model": "semantic-model-instructions.txt",
    }
    examples = query_examples()
    changed = ["stage_config.json:aiInstructions"] if global_text != config.get("aiInstructions") else []
    for path, source in sources:
        kind = source["type"]
        if kind not in instructions:
            continue
        text = (profile / instructions[kind]).read_text(encoding="utf-8")
        if "\r" in text or not text.strip():
            raise SafetyError("Source guidance must be nonempty LF text.")
        result[path]["dataSourceInstructions"] = text
        if text != source.get("dataSourceInstructions"):
            changed.append(path + ":dataSourceInstructions")
        if kind == "semantic_model":
            result[path]["userDescription"] = (
                "Governed Gold analytics for explicitly requested semantic measures, accepted increments or combined Gold. "
                "Default workshop totals, popularity and geographic donation questions belong to Lakehouse SQL static 2025. "
                "If a static question reaches this model, use its source-owned static-scoped measures/StaticSeed context; "
                "generic all-source measures are not the static snapshot."
            )
            if result[path]["userDescription"] != source.get("userDescription"):
                changed.append(path + ":userDescription")
        if kind in examples:
            example_path = path.removesuffix("datasource.json") + "fewshots.json"
            result[example_path] = examples[kind]
            if result[example_path] != stage.get(example_path):
                changed.append(example_path)
    for path, source in sources:
        original = copy.deepcopy(source)
        observed = copy.deepcopy(result[path])
        original.pop("dataSourceInstructions", None)
        observed.pop("dataSourceInstructions", None)
        if source["type"] == "semantic_model":
            original.pop("userDescription", None)
            observed.pop("userDescription", None)
        if original != observed:
            raise SafetyError("A source identity, description or selection changed.")
    original_config = copy.deepcopy(config)
    observed_config = copy.deepcopy(result["stage_config.json"])
    original_config.pop("aiInstructions", None)
    observed_config.pop("aiInstructions", None)
    if original_config != observed_config:
        raise SafetyError("Runtime/CI or another stage field changed.")
    semantic_path = next(path for path, source in sources if source["type"] == "semantic_model")
    semantic_guidance_preserved = all(
        result[semantic_path].get(field) == stage[semantic_path].get(field)
        for field in ("dataSourceInstructions", "userDescription")
    )
    contract = {
        "kind": "explicit-isolated-evidence-first-candidate",
        "changedFields": changed,
        "sourceIdentitiesAndSelectionsPreserved": True,
        "runtimeAndCiPreserved": True,
        "semanticModelGuidancePreserved": semantic_guidance_preserved,
        "semanticModelGuidanceChanged": None if semantic_guidance_preserved else "explicit StaticSeed/source-owned static measures and explicit-only combined Gold",
        "donationAttributeProvenance": "complete SQL attribute ledger including all catalog suppliers; separate native GQL connectivity",
        "canonicalRelationshipGrounding": "names/directions from existing portable contract; connected-source verification required",
        "globalCharacters": len(global_text),
        "exampleCounts": {kind: len(value["fewShots"]) for kind, value in examples.items()},
        "nativeExamplesValidated": False,
        "answerQualityAccepted": False,
        "automaticPromotion": False,
        "nativeSafetyBypass": False,
        "defaultOntologyGenerationChanged": False,
    }
    return result, contract
