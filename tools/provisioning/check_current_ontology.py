"""Offline integrity and seed-cardinality check for the current v3 preview ontology."""
from __future__ import annotations

import csv
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
from typing import Any


CURRENT_EDITION = "v3.0.0-preview"
EDITION_PATH = f"workshop/{CURRENT_EDITION}/edition.json"
ARTIFACT_SET_PATH = "artifact-set.json"
CHECKOUT_ARTIFACT_SET_PATH = "docs/SOURCE_ARTIFACT_SET.json"
GEN2_CONTRACT_PATH = f"workshop/{CURRENT_EDITION}/ontology/generation2-contract.json"
COMPAT_CONTRACT_PATH = f"workshop/{CURRENT_EDITION}/ontology/agent-compat/contract.json"
COMPAT_TEMPLATE_PATH = f"workshop/{CURRENT_EDITION}/ontology/agent-compat/definition-template.json"
DATASET_MANIFEST_PATH = f"workshop/{CURRENT_EDITION}/data/dataset-manifest.json"


class ValidationError(ValueError):
    """Raised when a current-edition input is missing or inconsistent."""


def _read_bytes(source_root: Path, relative_path: str) -> bytes:
    path = source_root.joinpath(*PurePosixPath(relative_path).parts)
    try:
        return path.read_bytes()
    except OSError as exc:
        raise ValidationError(f"Required current-edition file is unavailable: {relative_path}") from exc


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValidationError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def _read_json(source_root: Path, relative_path: str) -> tuple[dict[str, Any], bytes]:
    raw = _read_bytes(source_root, relative_path)
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValidationError(f"Invalid UTF-8 JSON: {relative_path}") from exc
    if not isinstance(value, dict):
        raise ValidationError(f"Expected a JSON object: {relative_path}")
    return value, raw


def _canonical_digest(value: Any) -> str:
    canonical = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _check_artifact_hash(
    source_root: Path, artifact_files: dict[str, str], relative_path: str,
) -> bytes:
    expected = artifact_files.get(relative_path)
    if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
        raise ValidationError(f"Current artifact-set has no valid SHA-256 entry for {relative_path}")
    raw = _read_bytes(source_root, relative_path)
    actual = hashlib.sha256(raw).hexdigest()
    if actual != expected:
        raise ValidationError(f"Current artifact SHA-256 mismatch: {relative_path}")
    return raw


def _compare_count_mapping(label: str, declared: Any, actual: dict[str, int]) -> None:
    if not isinstance(declared, dict):
        raise ValidationError(f"{label} is not an object")
    try:
        normalized = {str(key): int(value) for key, value in declared.items()}
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"{label} contains a non-integer count") from exc
    if normalized != actual:
        raise ValidationError(f"{label} differs from current seed CSVs: declared={normalized}, actual={actual}")


def _read_seed_rows(
    source_root: Path, artifact_files: dict[str, str], manifest: dict[str, Any],
) -> dict[str, list[dict[str, str]]]:
    entries = manifest.get("files")
    if not isinstance(entries, list):
        raise ValidationError("Current dataset manifest files must be a list")
    rows_by_file: dict[str, list[dict[str, str]]] = {}
    seen_names: set[str] = set()
    for item in entries:
        if not isinstance(item, dict):
            raise ValidationError("Current dataset manifest contains an invalid file entry")
        filename = item.get("file")
        if not isinstance(filename, str) or PurePosixPath(filename).name != filename or not filename.endswith(".csv"):
            raise ValidationError(f"Invalid current seed CSV name: {filename!r}")
        if filename in seen_names:
            raise ValidationError(f"Duplicate current seed CSV entry: {filename}")
        seen_names.add(filename)
        relative = f"workshop/{CURRENT_EDITION}/data/seed/{filename}"
        raw = _check_artifact_hash(source_root, artifact_files, relative)
        if hashlib.sha256(raw).hexdigest() != item.get("sha256"):
            raise ValidationError(f"Dataset-manifest SHA-256 mismatch: {filename}")
        if len(raw) != item.get("bytes"):
            raise ValidationError(f"Dataset-manifest byte-length mismatch: {filename}")
        if raw.startswith(b"\xef\xbb\xbf"):
            raise ValidationError(f"Unexpected UTF-8 BOM in current seed CSV: {filename}")
        try:
            text = raw.decode("utf-8")
            reader = csv.reader(io.StringIO(text, newline=""), strict=True)
            header = next(reader)
            if header != item.get("header", "").split(","):
                raise ValidationError(f"Dataset-manifest header mismatch: {filename}")
            if len(header) != len(set(header)):
                raise ValidationError(f"Duplicate column name in current seed CSV: {filename}")
            rows = []
            for row_number, fields in enumerate(reader, start=2):
                if len(fields) != len(header):
                    raise ValidationError(f"Malformed CSV row {row_number} in {filename}")
                rows.append(dict(zip(header, fields)))
        except (UnicodeDecodeError, csv.Error, StopIteration) as exc:
            raise ValidationError(f"Could not parse current seed CSV: {filename}") from exc
        if len(rows) != item.get("rows"):
            raise ValidationError(f"Dataset-manifest row-count mismatch: {filename}")
        rows_by_file[filename] = rows
    required = {
        "business_gifts.csv", "businesses.csv", "categories.csv", "donation_orders.csv",
        "donors.csv", "gifts.csv", "municipalities.csv", "prefectures.csv",
    }
    if seen_names != required:
        raise ValidationError(f"Unexpected current seed CSV inventory: {sorted(seen_names)}")
    return rows_by_file


def _unique_index(rows: list[dict[str, str]], key: str, label: str) -> dict[str, dict[str, str]]:
    index: dict[str, dict[str, str]] = {}
    for row in rows:
        value = row.get(key, "")
        if not value or value in index:
            raise ValidationError(f"Missing or duplicate {label} key: {value!r}")
        index[value] = row
    return index


def _require_foreign_keys(
    rows: list[dict[str, str]], field: str, target: dict[str, Any], label: str,
) -> None:
    for row in rows:
        value = row.get(field, "")
        if value not in target:
            raise ValidationError(f"Unresolved {label} key: {value!r}")


def _measure_seed_graph(rows: dict[str, list[dict[str, str]]]) -> dict[str, Any]:
    prefectures = _unique_index(rows["prefectures.csv"], "PrefectureID", "PrefectureID")
    municipalities = _unique_index(rows["municipalities.csv"], "MunicipalityID", "MunicipalityID")
    donors = _unique_index(rows["donors.csv"], "DonorID", "DonorID")
    categories = _unique_index(rows["categories.csv"], "CategoryID", "CategoryID")
    gifts = _unique_index(rows["gifts.csv"], "GiftID", "GiftID")
    businesses = _unique_index(rows["businesses.csv"], "BusinessID", "BusinessID")
    donations = _unique_index(rows["donation_orders.csv"], "DonationID", "DonationID")

    _require_foreign_keys(rows["municipalities.csv"], "PrefectureID", prefectures, "municipality prefecture")
    _require_foreign_keys(rows["donors.csv"], "PrefectureID", prefectures, "donor prefecture")
    _require_foreign_keys(rows["businesses.csv"], "PrefectureID", prefectures, "business prefecture")
    _require_foreign_keys(rows["gifts.csv"], "CategoryID", categories, "gift category")
    _require_foreign_keys(rows["gifts.csv"], "MunicipalityID", municipalities, "gift municipality")
    _require_foreign_keys(rows["business_gifts.csv"], "BusinessID", businesses, "catalog business")
    _require_foreign_keys(rows["business_gifts.csv"], "GiftID", gifts, "catalog gift")
    _require_foreign_keys(rows["donation_orders.csv"], "DonorID", donors, "donation donor")
    _require_foreign_keys(rows["donation_orders.csv"], "MunicipalityID", municipalities, "donation municipality")
    _require_foreign_keys(rows["donation_orders.csv"], "GiftID", gifts, "donation gift")

    municipality_categories: set[tuple[str, str]] = set()
    prefecture_categories: set[tuple[str, str]] = set()
    prefecture_flows: set[tuple[str, str]] = set()
    donors_with_donations: set[str] = set()
    municipalities_with_donations: set[str] = set()
    for donation in rows["donation_orders.csv"]:
        municipality_id = donation["MunicipalityID"]
        donor_id = donation["DonorID"]
        category_id = gifts[donation["GiftID"]]["CategoryID"]
        recipient_prefecture = municipalities[municipality_id]["PrefectureID"]
        residence_prefecture = donors[donor_id]["PrefectureID"]
        municipality_categories.add((municipality_id, category_id))
        prefecture_categories.add((recipient_prefecture, category_id))
        prefecture_flows.add((residence_prefecture, recipient_prefecture))
        donors_with_donations.add(donor_id)
        municipalities_with_donations.add(municipality_id)

    suppliers_with_gifts: set[str] = set()
    gifts_with_suppliers: set[str] = set()
    for pair in rows["business_gifts.csv"]:
        suppliers_with_gifts.add(pair["BusinessID"])
        gifts_with_suppliers.add(pair["GiftID"])

    business_gift_count = len(rows["business_gifts.csv"])
    donation_count = len(rows["donation_orders.csv"])
    node_counts = {
        "ot_prefecture": len(prefectures),
        "ot_municipality": len(municipalities),
        "ot_donor": len(donors),
        "ot_gift_category": len(categories),
        "ot_gift": len(gifts),
        "ot_supplier": len(businesses),
        "ot_donation": donation_count,
        "ot_mun_category_metric": len(municipality_categories),
        "ot_pref_category_metric": len(prefecture_categories),
        "ot_pref_donation_flow": len(prefecture_flows),
    }
    edge_counts = {
        "MunicipalityInPrefecture": len(municipalities),
        "DonorLivesInPrefecture": len(donors),
        "SupplierInPrefecture": len(businesses),
        "GiftInCategory": len(gifts),
        "MunicipalityCatalogsGift": len(gifts),
        "SupplierProvidesGift": business_gift_count,
        "DonorMadeDonation": donation_count,
        "DonationToMunicipality": donation_count,
        "DonationSelectedGift": donation_count,
        "MunHasCategoryMetric": len(municipality_categories),
        "MunMetricForCategory": len(municipality_categories),
        "PrefHasCategoryMetric": len(prefecture_categories),
        "PrefMetricForCategory": len(prefecture_categories),
        "ResidencePrefHasFlow": len(prefecture_flows),
        "FlowToRecipientPref": len(prefecture_flows),
    }
    participation = {
        "donorsWithoutDonations": len(donors) - len(donors_with_donations),
        "municipalitiesWithoutDonations": len(municipalities) - len(municipalities_with_donations),
        "suppliersWithoutGifts": len(businesses) - len(suppliers_with_gifts),
        "giftsWithoutSuppliers": len(gifts) - len(gifts_with_suppliers),
    }
    orphan_sources = {
        "DonorMadeDonation": participation["donorsWithoutDonations"],
        "MunHasCategoryMetric": participation["municipalitiesWithoutDonations"],
        "SupplierProvidesGift": participation["suppliersWithoutGifts"],
        "MunicipalityCatalogsGift": len(municipalities) - len({gift["MunicipalityID"] for gift in gifts.values()}),
        "PrefHasCategoryMetric": len(prefectures) - len({pref for pref, _ in prefecture_categories}),
        "ResidencePrefHasFlow": len(prefectures) - len({pref for pref, _ in prefecture_flows}),
    }
    return {
        "nodeCounts": node_counts,
        "edgeCounts": edge_counts,
        "participation": participation,
        "orphanSources": orphan_sources,
        "bridgeRows": business_gift_count,
    }


def _compatibility_relationships(template: dict[str, Any]) -> dict[str, dict[str, str]]:
    parts = template.get("parts")
    if not isinstance(parts, list):
        raise ValidationError("Current compatibility definition template has no parts list")
    entities: dict[str, str] = {}
    relationships: dict[str, dict[str, str]] = {}
    for part in parts:
        if not isinstance(part, dict) or not isinstance(part.get("path"), str):
            raise ValidationError("Malformed current compatibility definition part")
        path, content = part["path"], part.get("content", {})
        if not isinstance(content, dict):
            continue
        if path.startswith("EntityTypes/") and path.count("/") == 2 and path.endswith("/definition.json"):
            if content.get("id") in entities or not content.get("id") or not content.get("name"):
                raise ValidationError("Duplicate or incomplete entity in current compatibility template")
            entities[str(content["id"])] = str(content["name"])
        if path.startswith("RelationshipTypes/") and path.count("/") == 2 and path.endswith("/definition.json"):
            name = content.get("name")
            attrs = content.get("semanticEnrichment", {}).get("customAttributes", {})
            if not isinstance(name, str) or name in relationships:
                raise ValidationError("Duplicate or incomplete relationship in current compatibility template")
            relationships[name] = {
                "fromEntity": entities.get(str(content.get("source", {}).get("entityTypeId")), ""),
                "toEntity": entities.get(str(content.get("target", {}).get("entityTypeId")), ""),
                "cardinality": str(attrs.get("cardinality", "")),
            }
    if len(entities) != 10 or len(relationships) != 15:
        raise ValidationError("Unexpected current compatibility template inventory")
    return relationships


def _relationship_cardinalities(
    generation2: dict[str, Any], compat: dict[str, dict[str, str]], measured: dict[str, Any],
) -> dict[str, str]:
    table_for_entity = {
        str(entity["name"]): str(entity["sourceTable"])
        for entity in generation2.get("entities", [])
        if isinstance(entity, dict) and entity.get("name") and entity.get("sourceTable")
    }
    count_for_table = measured["nodeCounts"]
    actual_relationships = generation2.get("relationships")
    if not isinstance(actual_relationships, list) or len(actual_relationships) != 15:
        raise ValidationError("Unexpected current generation-2 relationship inventory")
    declarations: dict[str, str] = {}
    for relationship in actual_relationships:
        if not isinstance(relationship, dict):
            raise ValidationError("Malformed current generation-2 relationship entry")
        name = relationship.get("name")
        source = relationship.get("fromEntity")
        target = relationship.get("toEntity")
        details = compat.get(str(name))
        if details is None or (details["fromEntity"], details["toEntity"]) != (source, target):
            raise ValidationError(f"Current relationship endpoints disagree: {name}")
        if not details["cardinality"]:
            raise ValidationError(f"Current relationship has no cardinality declaration: {name}")
        source_table = table_for_entity.get(str(source))
        target_table = table_for_entity.get(str(target))
        if source_table not in count_for_table or target_table not in count_for_table:
            raise ValidationError(f"Relationship endpoint has no current node count: {name}")
        edges = measured["edgeCounts"].get(str(name))
        if edges is None:
            raise ValidationError(f"Relationship has no recomputed edge count: {name}")
        source_nodes, target_nodes = count_for_table[source_table], count_for_table[target_table]
        if edges == source_nodes == target_nodes:
            expected = "one-to-one"
        elif edges == target_nodes:
            orphans = measured["orphanSources"].get(str(name), 0)
            expected = ("zero-to-many from " if orphans else "one-to-many from ") + str(source)
        elif edges == source_nodes:
            expected = "many-to-one"
        else:
            expected = "many-to-many"
        declared = details["cardinality"]
        if expected == "many-to-many":
            valid = declared.startswith("many-to-many")
        elif expected == "many-to-one":
            valid = declared.startswith("many-to-one")
        elif expected == "one-to-one":
            valid = declared.startswith("one-to-one")
        else:
            valid = declared.startswith(expected)
        if not valid:
            raise ValidationError(
                f"Current cardinality disagrees with seed rows for {name}: declared={declared!r}, derived={expected!r}"
            )
        declarations[str(name)] = declared
    if set(declarations) != set(compat):
        raise ValidationError("Current generation-2 and compatibility relationship inventories differ")
    return declarations


def _check_generation2_definition(
    source_root: Path, artifact_files: dict[str, str], contract: dict[str, Any],
    cardinalities: dict[str, str],
) -> int:
    definition_prefix = f"workshop/{CURRENT_EDITION}/ontology/definition/"
    expected_paths = {
        path for path in artifact_files
        if path.startswith(definition_prefix)
    }
    definition_root = source_root.joinpath(*PurePosixPath(definition_prefix).parts)
    actual_paths = {
        path.relative_to(source_root).as_posix()
        for path in definition_root.rglob("*")
        if path.is_file()
    } if definition_root.is_dir() else set()
    if not expected_paths or actual_paths != expected_paths:
        raise ValidationError("Current generation-2 definition file inventory differs from artifact-set")
    for relative_path in sorted(expected_paths):
        _check_artifact_hash(source_root, artifact_files, relative_path)

    entities = contract.get("entities")
    relationships = contract.get("relationships")
    if not isinstance(entities, list) or len(entities) != 10:
        raise ValidationError("Current generation-2 contract must declare 10 entities")
    if not isinstance(relationships, list) or len(relationships) != 15:
        raise ValidationError("Current generation-2 contract must declare 15 relationships")
    entity_names = [entity.get("name") for entity in entities if isinstance(entity, dict)]
    if len(entity_names) != 10 or len(set(entity_names)) != 10:
        raise ValidationError("Current generation-2 entity names are incomplete or duplicated")
    tables = set()
    static_properties = 0
    time_series = contract.get("timeSeriesBinding", {})
    for entity in entities:
        name, table, key = entity.get("name"), entity.get("sourceTable"), entity.get("keyProperty")
        props = entity.get("properties")
        if not isinstance(props, list) or not any(prop.get("name") == key for prop in props):
            raise ValidationError(f"Current generation-2 key property is missing: {name}")
        static_properties += len(props)
        tables.add(table)
        path = f"{definition_prefix}entities/{name}.tmdl"
        raw = _check_artifact_hash(source_root, artifact_files, path)
        text = raw.decode("utf-8")
        if (f"entity {name}\n" not in text or f"\tbackingTable: {table}\n" not in text
                or f"\tkeyProperty: {key}\n" not in text):
            raise ValidationError(f"Current entity definition disagrees with its contract: {name}")
        declared_properties = set(re.findall(r"^\tproperty (.+)$", text, re.MULTILINE))
        time_series_property = (
            {str(time_series["property"])}
            if time_series.get("entity") == name and time_series.get("property")
            else set()
        )
        if declared_properties != {str(prop.get("name")) for prop in props} | (
                time_series_property):
            raise ValidationError(f"Current property definitions disagree with contract: {name}")
    for relationship in relationships:
        table = relationship.get("sourceTable")
        if not table:
            raise ValidationError(f"Current relationship has no backing table: {relationship.get('name')}")
        tables.add(table)
    if (contract.get("generation") != 2 or contract.get("entityTypes") != 10
            or contract.get("staticProperties") != static_properties
            or contract.get("staticBindings") != len(entities)
            or contract.get("timeseriesProperties") != 1
            or contract.get("relationshipTypes") != 15
            or contract.get("backingTables") != len(tables)):
        raise ValidationError("Current generation-2 summary counts disagree with its definition contract")

    relationship_file = f"{definition_prefix}entityRelationships.tmdl"
    relationship_text = _check_artifact_hash(source_root, artifact_files, relationship_file).decode("utf-8")
    blocks = re.split(r"(?m)^entityRelationship ", relationship_text)[1:]
    parsed: dict[str, tuple[str, str, str]] = {}
    for block in blocks:
        lines = block.splitlines()
        name = lines[0].strip()
        from_match = re.search(r"(?m)^\tfromEntity: (.+)$", block)
        to_match = re.search(r"(?m)^\ttoEntity: (.+)$", block)
        annotation = re.search(r'(?m)^\tannotation Furusato_cardinality = ("(?:[^"\\]|\\.)*")$', block)
        if not (from_match and to_match and annotation):
            raise ValidationError(f"Incomplete current relationship definition: {name}")
        parsed[name] = (from_match.group(1), to_match.group(1), json.loads(annotation.group(1)))
    if set(parsed) != set(cardinalities):
        raise ValidationError("Current relationship definitions differ from current contracts")
    for relationship in relationships:
        name = relationship["name"]
        expected = (relationship["fromEntity"], relationship["toEntity"], cardinalities[name])
        if parsed.get(name) != expected:
            raise ValidationError(f"Current relationship definition disagrees with contract: {name}")
    return len(actual_paths)


def validate_source_root(source_root: Path) -> dict[str, Any]:
    """Validate current v3 seed counts and ontology artifact bytes without writes or network."""
    root = Path(source_root).resolve()
    edition, _ = _read_json(root, EDITION_PATH)
    if (edition.get("runtimeProfile") != CURRENT_EDITION
            or edition.get("primaryOntologyGeneration") != 2
            or edition.get("standardOntologyCount") != 1):
        raise ValidationError(f"Expected current generation-2 edition {CURRENT_EDITION}; legacy defaults are not used")

    outer = root / ARTIFACT_SET_PATH
    if outer.is_symlink():
        raise ValidationError("Outer publication manifest must not be a symlink")
    manifest_path = (ARTIFACT_SET_PATH if outer.exists()
                     else CHECKOUT_ARTIFACT_SET_PATH)
    artifact_set, _ = _read_json(root, manifest_path)
    artifact_files = artifact_set.get("files")
    if not isinstance(artifact_files, dict) or artifact_set.get("sourceTreeSha256") != _canonical_digest(artifact_files):
        raise ValidationError("Current artifact-set sourceTreeSha256 does not match its file map")
    if artifact_set.get("runtimeProfile") != CURRENT_EDITION:
        raise ValidationError("Current artifact-set runtime profile does not match edition.json")
    if (artifact_set.get("workshopVersion") != edition.get("workshopVersion")
            or artifact_set.get("edition") != edition
            or _read_bytes(root, "WORKSHOP_VERSION").decode("utf-8").strip() != edition.get("workshopVersion")):
        raise ValidationError("Current publication manifest edition/version bindings differ")
    _check_artifact_hash(root, artifact_files, EDITION_PATH)

    for relative_path in (
        GEN2_CONTRACT_PATH, COMPAT_CONTRACT_PATH, COMPAT_TEMPLATE_PATH, DATASET_MANIFEST_PATH,
    ):
        _check_artifact_hash(root, artifact_files, relative_path)
    generation2, _ = _read_json(root, GEN2_CONTRACT_PATH)
    compat_contract, _ = _read_json(root, COMPAT_CONTRACT_PATH)
    compat_template, _ = _read_json(root, COMPAT_TEMPLATE_PATH)
    dataset, _ = _read_json(root, DATASET_MANIFEST_PATH)
    compat_counts = compat_contract.get("counts", {})
    if (compat_contract.get("expectedGeneration") != 1
            or compat_contract.get("defaultEnabled") is not False
            or compat_contract.get("implicitFallback") is not False
            or compat_contract.get("primaryGeneration2Unchanged") is not True
            or compat_counts.get("entityTypes") != 10
            or compat_counts.get("relationshipTypes") != 15):
        raise ValidationError("Current optional compatibility bridge contract is inconsistent")

    definition_prefix = f"workshop/{CURRENT_EDITION}/ontology/definition/"
    if not any(path.startswith(definition_prefix) for path in artifact_files):
        raise ValidationError("Current generation-2 definition files are absent from artifact-set")
    rows = _read_seed_rows(root, artifact_files, dataset)
    measured = _measure_seed_graph(rows)
    expected = dataset.get("expected", {})
    _compare_count_mapping("dataset expected.nodeCounts", expected.get("nodeCounts"), measured["nodeCounts"])
    _compare_count_mapping("dataset expected.edgeCounts", expected.get("edgeCounts"), measured["edgeCounts"])
    actual_output_counts = dict(measured["nodeCounts"])
    actual_output_counts["ot_supplier_gift"] = measured["bridgeRows"]
    _compare_count_mapping("dataset expected.outputTableCounts", expected.get("outputTableCounts"), actual_output_counts)
    if expected.get("donationRows") != measured["nodeCounts"]["ot_donation"]:
        raise ValidationError("Dataset donationRows disagrees with current seed CSVs")
    for key in ("donorsWithoutDonations", "municipalitiesWithoutDonations", "suppliersWithoutGifts"):
        if expected.get(key) != measured["participation"][key]:
            raise ValidationError(f"Dataset expected.{key} disagrees with current seed CSVs")
    if measured["participation"]["giftsWithoutSuppliers"] != 0:
        raise ValidationError("At least one current gift has no registered supplier")
    if expected.get("nodeTotal") != sum(measured["nodeCounts"].values()):
        raise ValidationError("Dataset nodeTotal disagrees with current seed CSVs")
    if expected.get("edgeTotal") != sum(measured["edgeCounts"].values()):
        raise ValidationError("Dataset edgeTotal disagrees with current seed CSVs")

    compat_relationships = _compatibility_relationships(compat_template)
    cardinalities = _relationship_cardinalities(generation2, compat_relationships, measured)
    definition_files = _check_generation2_definition(root, artifact_files, generation2, cardinalities)
    return {
        "edition": CURRENT_EDITION,
        "mode": "offline current-edition source validation",
        "generation2DefinitionFiles": definition_files,
        "nodeCounts": measured["nodeCounts"],
        "edgeCounts": measured["edgeCounts"],
        "participation": measured["participation"],
        "nodeTotal": sum(measured["nodeCounts"].values()),
        "edgeTotal": sum(measured["edgeCounts"].values()),
    }


def main() -> int:
    source_root = Path(__file__).resolve().parents[2]
    try:
        result = validate_source_root(source_root)
    except ValidationError as exc:
        print(f"FAIL  current ontology check: {exc}")
        return 1
    print("PASS  offline current v3 generation-2 ontology and seed validation")
    print("      No network or Fabric runtime was used.")
    print(f"      Definition files: {result['generation2DefinitionFiles']}")
    print(f"      Recomputed from current seed CSVs: {result['nodeTotal']} nodes, {result['edgeTotal']} directed edges")
    for name in sorted(result["participation"]):
        print(f"      {name}: {result['participation'][name]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
