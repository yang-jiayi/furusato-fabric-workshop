"""Compute offline truth from immutable packaged data, never from AI answers."""

from __future__ import annotations

import csv
import importlib.util
import subprocess
from collections import Counter
from pathlib import Path

from preview_contract import EvidenceError, digest, file_hash, load_json, timestamp

TABLE_KEYS = {
    "ot_prefecture": ("prefectures.csv", "PrefectureID"),
    "ot_municipality": ("municipalities.csv", "MunicipalityID"),
    "ot_donor": ("donors.csv", "DonorID"),
    "ot_gift_category": ("categories.csv", "CategoryID"),
    "ot_gift": ("gifts.csv", "GiftID"),
    "ot_supplier": ("businesses.csv", "BusinessID"),
    "ot_donation": ("donation_orders.csv", "DonationID"),
}
EDGE_ENDPOINTS = {
    "MunicipalityInPrefecture": ("ot_municipality", "ot_prefecture"),
    "DonorLivesInPrefecture": ("ot_donor", "ot_prefecture"),
    "SupplierInPrefecture": ("ot_supplier", "ot_prefecture"),
    "GiftInCategory": ("ot_gift", "ot_gift_category"),
    "MunicipalityCatalogsGift": ("ot_municipality", "ot_gift"),
    "SupplierProvidesGift": ("ot_supplier", "ot_gift"),
    "DonorMadeDonation": ("ot_donor", "ot_donation"),
    "DonationToMunicipality": ("ot_donation", "ot_municipality"),
    "DonationSelectedGift": ("ot_donation", "ot_gift"),
    "MunHasCategoryMetric": ("ot_municipality", "ot_mun_category_metric"),
    "MunMetricForCategory": ("ot_mun_category_metric", "ot_gift_category"),
    "PrefHasCategoryMetric": ("ot_prefecture", "ot_pref_category_metric"),
    "PrefMetricForCategory": ("ot_pref_category_metric", "ot_gift_category"),
    "ResidencePrefHasFlow": ("ot_prefecture", "ot_pref_donation_flow"),
    "FlowToRecipientPref": ("ot_pref_donation_flow", "ot_prefecture"),
}


def _csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise EvidenceError(message)


def compute_oracle(repo: Path, data_relative: str = r"workshop\v2.7.0\data") -> dict:
    data = repo / data_relative
    manifest = load_json(data / "dataset-manifest.json")
    checksums = {}
    for line in (data / "SHA256SUMS.txt").read_text(encoding="utf-8-sig").splitlines():
        checksum, name = line.split(maxsplit=1)
        checksums[name.strip().replace("/", "\\")] = checksum
    files, tables, increments = {}, {}, []
    for field, folder in (("files", "seed"), ("incrementFiles", "increment")):
        for entry in manifest[field]:
            relative = str(Path(folder) / entry["file"])
            path = data / relative
            observed_hash = file_hash(path)
            _require(observed_hash == entry["sha256"] == checksums[relative],
                     f"Immutable CSV checksum differs: {entry['file']}")
            _require(path.stat().st_size == entry["bytes"], f"CSV byte count differs: {entry['file']}")
            rows = _csv(path)
            _require(len(rows) == entry["rows"], f"CSV row count differs: {entry['file']}")
            _require(bool(rows) and list(rows[0]) == entry["header"].split(","),
                     f"CSV header differs: {entry['file']}")
            files[relative] = observed_hash
            if folder == "seed":
                tables[entry["file"]] = rows
            else:
                increments.extend(rows)
    _require(set(files) == set(checksums), "Checksum inventory differs from dataset contract.")
    indexed = {}
    for table, (filename, key) in TABLE_KEYS.items():
        indexed[table] = {row[key]: row for row in tables[filename]}
        _require(len(indexed[table]) == len(tables[filename]), f"Duplicate static entity key: {table}")
    donations = tables["donation_orders.csv"]
    for row in donations + increments:
        _require(len(row["MunicipalityID"]) == 6 and row["MunicipalityID"].isascii()
                 and row["MunicipalityID"].isdigit(), "MunicipalityID must preserve six-digit text.")
        for key in ("DonationID", "DonorID", "GiftID", "DonationAmountYen"):
            _require(row[key].isascii() and row[key].isdigit(), f"Invalid integer source type: {key}")
        _require(row["DonatedAt"].endswith("Z"), "Source timestamps must remain UTC.")
        timestamp(row["DonatedAt"])
        for key, table in (("DonorID", "ot_donor"), ("MunicipalityID", "ot_municipality"), ("GiftID", "ot_gift")):
            _require(row[key] in indexed[table], f"Orphan source key: {key}")
    static = {
        "rows": len(donations), "amount_yen": sum(int(row["DonationAmountYen"]) for row in donations),
        "unique_donation_ids": len(indexed["ot_donation"]),
        "from_utc": min(row["DonatedAt"] for row in donations),
        "to_utc": max(row["DonatedAt"] for row in donations),
        "grain": "one donation; never donation x supplier",
        "source_types": {"MunicipalityID": "six ASCII digits preserved as text",
                         "DonationAmountYen": "integer yen", "DonatedAt": "UTC timestamp"},
    }
    _require(static["rows"] == manifest["expected"]["donationRows"]
             and static["amount_yen"] == manifest["expected"]["totalDonationAmountYen"],
             "Static source totals disagree with dataset contract.")
    _require(all(row["DonatedAt"].startswith("2025-") for row in donations), "Static source period changed.")
    by_event, business_columns = {}, ("DonationID", "DonorID", "MunicipalityID", "GiftID", "DonationAmountYen", "DonatedAt", "PaymentMethod")
    for row in increments:
        previous = by_event.get(row["EventID"])
        if previous:
            _require(all(row[key] == previous[key] for key in business_columns), "Duplicate event payload conflict.")
        by_event.setdefault(row["EventID"], row)
    counts = Counter(row["EventID"] for row in increments)
    increment = {
        "raw_rows": len(increments), "unique_event_ids": len(by_event),
        "duplicate_event_ids": sum(count > 1 for count in counts.values()),
        "duplicate_extra_rows": len(increments) - len(by_event),
        "raw_amount_yen": sum(int(row["DonationAmountYen"]) for row in increments),
        "accepted_amount_yen": sum(int(row["DonationAmountYen"]) for row in by_event.values()),
        "from_utc": min(row["DonatedAt"] for row in increments),
        "to_utc": max(row["DonatedAt"] for row in increments),
        "grain": "raw observation versus accepted unique EventID; never minute-bucket count",
        "file_count": len(manifest["incrementFiles"]),
    }
    expected_increment = manifest["expectedIncrement"]
    for actual, expected in (("raw_rows", "rawRows"), ("unique_event_ids", "uniqueEventIds"),
                             ("duplicate_event_ids", "duplicateEventIds"), ("raw_amount_yen", "rawAmountYen"),
                             ("accepted_amount_yen", "deduplicatedAmountYen")):
        _require(increment[actual] == expected_increment[expected], f"Increment contract differs: {actual}")
    _require(increment["from_utc"] == expected_increment["observationWindowUtc"]["from"]
             and increment["to_utc"] == expected_increment["observationWindowUtc"]["to"],
             "Operational UTC observation window differs.")
    _require(all(count in {1, expected_increment["duplicateMultiplicity"]} for count in counts.values()),
             "Event duplicate multiplicity changed.")
    municipalities, donors, gifts = (indexed[key] for key in ("ot_municipality", "ot_donor", "ot_gift"))
    mun_category, pref_category, flows = set(), set(), set()
    for row in donations:
        recipient = municipalities[row["MunicipalityID"]]["PrefectureID"]
        category = gifts[row["GiftID"]]["CategoryID"]
        mun_category.add((row["MunicipalityID"], category))
        pref_category.add((recipient, category))
        flows.add((donors[row["DonorID"]]["PrefectureID"], recipient))
    nodes = {table: len(values) for table, values in indexed.items()}
    nodes.update(ot_mun_category_metric=len(mun_category), ot_pref_category_metric=len(pref_category),
                 ot_pref_donation_flow=len(flows))
    edges = {
        "MunicipalityInPrefecture": nodes["ot_municipality"], "DonorLivesInPrefecture": nodes["ot_donor"],
        "SupplierInPrefecture": nodes["ot_supplier"], "GiftInCategory": nodes["ot_gift"],
        "MunicipalityCatalogsGift": nodes["ot_gift"], "SupplierProvidesGift": len(tables["business_gifts.csv"]),
        "DonorMadeDonation": len(donations), "DonationToMunicipality": len(donations),
        "DonationSelectedGift": len(donations), "MunHasCategoryMetric": len(mun_category),
        "MunMetricForCategory": len(mun_category), "PrefHasCategoryMetric": len(pref_category),
        "PrefMetricForCategory": len(pref_category), "ResidencePrefHasFlow": len(flows),
        "FlowToRecipientPref": len(flows),
    }
    _require(nodes == manifest["expected"]["nodeCounts"] and edges == manifest["expected"]["edgeCounts"],
             "Recomputed original graph contract differs.")
    _require(sum(nodes.values()) == manifest["expected"]["nodeTotal"]
             and sum(edges.values()) == manifest["expected"]["edgeTotal"], "Original graph totals differ.")
    return {
        "schema_version": "furusato-preview30-source-oracle/v1",
        "dataset_version": manifest["datasetVersion"],
        "static": static, "increment": increment,
        "graph": {"node_counts": nodes, "edge_counts": edges,
                  "full_original_nodes": sum(nodes.values()), "full_original_edges": sum(edges.values()),
                  "full_totals_only_apply_to_full_original_projection": True},
        "csv_sha256": files, "dataset_manifest_sha256": file_hash(data / "dataset-manifest.json"),
        "checksum_file_sha256": file_hash(data / "SHA256SUMS.txt"),
        "live_data_verified": False, "ai_accuracy_claimed": False,
    }


def graph_expectations(oracle: dict, scope: dict) -> dict:
    """Unfiltered selected-table projections only; never guess filtered counts."""
    _require(scope.get("projection") in {"full_original", "selected_original_tables"},
             "Filtered/custom graphs require a separate executed scoped source oracle.")
    _require(not scope.get("filters"), "Filtered graphs cannot reuse unfiltered table counts.")
    nodes, edges = scope.get("tables", []), scope.get("relationships", [])
    _require(bool(nodes) and len(set(nodes)) == len(nodes) and len(set(edges)) == len(edges),
             "Declare each selected table/relationship exactly once.")
    graph = oracle["graph"]
    _require(set(nodes).issubset(graph["node_counts"]) and set(edges).issubset(graph["edge_counts"]),
             "Graph scope includes entities outside the original source oracle.")
    for edge in edges:
        _require(set(EDGE_ENDPOINTS[edge]).issubset(nodes), "Graph relationship endpoint was not selected.")
    full = set(nodes) == set(graph["node_counts"]) and set(edges) == set(graph["edge_counts"])
    _require(scope["projection"] != "full_original" or full, "Full graph label has only a partial projection.")
    return {"scope_sha256": digest(scope), "projection": "full_original" if full else "selected_original_tables",
            "node_count": sum(graph["node_counts"][key] for key in nodes),
            "edge_count": sum(graph["edge_counts"][key] for key in edges),
            "node_counts": {key: graph["node_counts"][key] for key in nodes},
            "edge_counts": {key: graph["edge_counts"][key] for key in edges}}


def immutable_baseline(repo: Path, baseline: str, oracle: dict) -> dict:
    _require(len(baseline) == 40 and all(char in "0123456789abcdef" for char in baseline),
             "Supply an exact public baseline commit.")
    relative = [
        r"tools\docs\furusato_docs\tests10.py", r"tools\docs\furusato_docs\facts.py",
        r"workshop\v2.7.0\data\dataset-manifest.json", r"workshop\v2.7.0\data\SHA256SUMS.txt",
        *(str(Path(r"workshop\v2.7.0\data") / name) for name in oracle["csv_sha256"]),
    ]
    files = {}
    import hashlib
    for name in relative:
        result = subprocess.run(["git", "-C", str(repo), "--no-pager", "show",
                                 f"{baseline}:{name.replace(chr(92), '/')}"],
                                capture_output=True, check=False)
        _require(result.returncode == 0, f"Baseline asset unavailable: {name}")
        actual = file_hash(repo / name)
        _require(actual == hashlib.sha256(result.stdout).hexdigest(), f"Immutable baseline asset changed: {name}")
        files[name] = actual
    return {"baseline": baseline, "files": files, "all_byte_identical": True}


def original_suite(repo: Path) -> dict:
    path = repo / "tools" / "data-agent" / "native_evaluation.py"
    spec = importlib.util.spec_from_file_location("_preview30_native_evaluation", path)
    if spec is None or spec.loader is None:
        raise EvidenceError("Original native evaluation harness unavailable.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    suite = module.original_suite(repo)
    _require(len(suite["cases"]) == 10 and sum(len(c["conditions"]) for c in suite["cases"]) == 84,
             "Original ten-question / 84-condition inventory differs.")
    return {"suite": suite, "suite_sha256": digest(suite), "published_not_independent_hidden": True}
