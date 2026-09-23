"""Reseal the v2.7 provisioning chain after a runtime source edit.

The workshop ships one provisioner notebook that carries the whole runtime as a
deterministic gzip+base64 payload, plus two manifests and a participant contract
that pin the same bytes. Editing any bundle source therefore invalidates a chain
of hashes. This tool recomputes the whole chain from the files on disk so the
pins can never be transcribed by hand:

    bundle sources
      -> bundle-manifest.json                (per-file and semantic digests)
      -> Notebook_04 embedded payload        (gzip+base64 chunks)
      -> payload-manifest.json               (payload digest and asset digests)
      -> participant-workspace-contract.json (every pinned digest)

Every serialisation choice below reproduces the committed bytes exactly, so a
run with no source edit leaves the working tree clean.

    python tools/provisioning/reseal_runtime.py            # rewrite the chain
    python tools/provisioning/reseal_runtime.py --check    # fail if resealing changes v2.7.0
"""

from __future__ import annotations

import argparse
import ast
import base64
import gzip
import hashlib
import inspect
import json
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

# Document validators also load this entry point directly through importlib.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import reference_assets
import reference_kql
import reference_ontology

VERSION = "2.7.0"
#: Fabric's interactive editor rejects a code cell larger than 500k. Chunk the
#: payload into several deterministic cells, rather than only splitting lines.
CHUNK = 100_000
CHUNKS_PER_CELL = 4
PAYLOAD_CELL_MAX_BYTES = 450_000
PAYLOAD_CELL_TAG = "furusato-provisioning-payload"
#: The character budget this distribution seals for the global instructions. It
#: matches the guard the v2.7.0 Data agent screen showed, but it is sealed here
#: as this workshop's own safety contract rather than as a product warranty.
INSTRUCTION_CHAR_LIMIT = 15000


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def tree_sha256(folder: Path) -> str:
    entries = [
        {"path": path.relative_to(folder).as_posix(), "sha256": sha_bytes(path.read_bytes())}
        for path in sorted(
            (p for p in folder.rglob("*") if p.is_file()),
            key=lambda p: p.relative_to(folder).as_posix(),
        )
    ]
    return sha_text(canonical(entries))


def snapshot_tree(root: Path) -> dict[str, str]:
    """Return content digests for every file under the reseal boundary."""
    return {
        path.relative_to(root).as_posix(): sha_bytes(path.read_bytes())
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def snapshot_bytes(root: Path) -> dict[str, bytes]:
    """Capture the reseal boundary so a failed gate can roll back every write."""
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def restore_tree(root: Path, snapshot: dict[str, bytes]) -> None:
    """Restore a byte snapshot after a gate aborts partway through a reseal."""
    current = {
        path.relative_to(root).as_posix(): path
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }
    for relative in current.keys() - snapshot.keys():
        current[relative].unlink()
    for relative, data in snapshot.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        write_bytes_if_changed(path, data)


def canonical(value: Any) -> str:
    """Canonical compact JSON used by every semantic digest in the runtime."""
    return json.dumps(value, separators=(",", ":"), ensure_ascii=False, sort_keys=True)


def dumps2(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text("utf-8"))


def write_bytes_if_changed(path: Path, data: bytes) -> None:
    """Avoid reopening identical sealed files; replace changed bytes atomically.

    On Windows an editor/indexer can briefly deny a truncating open of a file.
    Rewriting every unchanged file made even ``--check`` intermittently fail and
    could also prevent rollback. No-op writes now remain read-only; real changes
    use a same-directory temporary file and a bounded replacement retry.
    """
    if path.is_file() and path.read_bytes() == data:
        return
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(prefix=f".{path.name}.", suffix=".reseal.tmp", dir=path.parent, delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(data)
        for attempt in range(6):
            try:
                os.replace(temporary, path)
                return
            except OSError as exc:
                if attempt == 5 or exc.errno not in {13, 22}:
                    raise
                time.sleep(0.1 * (2 ** attempt))
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def notebook_code_source(notebook: dict[str, Any], marker: str) -> str:
    """Find a runtime by its declaration, not a fragile physical cell index."""
    matches = [
        "".join(cell.get("source", []))
        for cell in notebook["cells"]
        if cell.get("cell_type") == "code" and marker in "".join(cell.get("source", []))
    ]
    if len(matches) != 1:
        raise SystemExit(f"expected exactly one notebook runtime containing {marker!r}")
    return matches[0]


def is_payload_cell(cell: dict[str, Any]) -> bool:
    return (
        PAYLOAD_CELL_TAG in cell.get("metadata", {}).get("tags", [])
        or (
            cell.get("cell_type") == "code"
            and "_PAYLOAD_CHUNKS = [" in "".join(cell.get("source", []))
        )
    )


def write_lf(path: Path, text: str) -> None:
    """Write UTF-8 with LF endings on every platform.

    ``Path.write_text`` opens the file in text mode with ``newline=None``, which
    translates every ``\\n`` to ``os.linesep``. On Windows that silently produced
    CRLF files, and the runtime hashes are not newline-agnostic: the bundle
    manifest pins the SHA-256 of each file's raw bytes, while the payload carried
    the same file read back through universal newlines. A participant unpacking
    the payload therefore wrote LF files and then failed to verify them against
    CRLF digests, and a reseal run on Linux produced different manifest digests
    from the same sources. Writing the encoded bytes removes the translation
    layer entirely, so the sealed bytes are identical on every platform.
    """
    if "\r" in text:
        raise SystemExit(f"refusing to write {path.name}: authored text contains a carriage return")
    write_bytes_if_changed(path, text.encode("utf-8"))


def extract_kql_management_commands(script: str) -> list[str]:
    """Seal only the released five; extension functions have their own safe loader."""
    return reference_kql.compose_kql_management_commands(script)


def terminology_rule_count(instructions: str) -> int:
    """Bullets under the TERMINOLOGY heading of the global instructions."""
    count = 0
    inside = False
    for line in instructions.splitlines():
        if line.strip() == "TERMINOLOGY":
            inside = True
            continue
        if inside:
            if not line.strip():
                break
            if line.startswith("- "):
                count += 1
    return count


def ontology_property_descriptions(workshop: Path) -> dict[str, str]:
    """Property name -> semantic-metadata description, the single source of truth."""
    metadata = load_json(workshop / "ontology" / "ontology-semantic-metadata.json")
    descriptions: dict[str, str] = {}
    for entity in metadata["entities"].values():
        for bucket in ("properties", "timeseriesProperties"):
            for name, node in entity.get(bucket, {}).items():
                descriptions[name] = node["semanticEnrichment"]["description"]
    return descriptions


def sync_rank_descriptions(root: Path) -> list[str]:
    """Mirror the ontology rank wording onto the Data Agent's Lakehouse columns.

    A rank is the one column family where the Lakehouse column and the Ontology
    property mean exactly the same thing, so the Agent must read exactly the same
    sentence from both. Left to drift, the Lakehouse copy kept calling four ranks
    "Dense" long after Notebook 01 had been shown to emit ``row_number``, which
    told the Agent that equal amounts share a rank. The wording is therefore
    copied rather than restated, and validate_docs.py asserts the equality.
    """
    workshop = root / "workshop" / f"v{VERSION}"
    config = workshop / "provisioning" / "bundle" / "data-agent" / "Files" / "Config"
    descriptions = ontology_property_descriptions(workshop)
    changed: list[str] = []

    for stage in ("draft", "published"):
        path = next((config / stage).glob("lakehouse-tables-*/datasource.json"))
        payload = load_json(path)
        updated: list[str] = []

        def visit(node: dict) -> None:
            if node.get("type") == "lakehouse_tables.column":
                name = node.get("display_name", "")
                wanted = descriptions.get(name)
                if name.endswith("Rank") and wanted and node.get("description") != wanted:
                    node["description"] = wanted
                    updated.append(name)
            for child in node.get("children", []):
                visit(child)

        for element in payload.get("elements", []):
            visit(element)
        if updated:
            write_lf(path, dumps2(payload))
            changed.append(f"{stage}: {len(updated)} rank column(s) resynced")
    return changed


def sync_reflex_pipeline_default(root: Path) -> bool:
    """Match the explicit fallback parameter emitted by the live trigger editor.

    Dynamic Type/Subject/Source bindings remain untouched. UI Save followed by
    runtime Start was the measured activation path; this normalization alone is
    not claimed to start a rule or prove that an event has executed the pipeline.
    """
    bundle = root / "workshop" / f"v{VERSION}" / "provisioning" / "bundle"
    pipeline = load_json(bundle / "data-pipeline" / "pipeline-content.json")
    parameter = pipeline["properties"]["parameters"]["IncrementFileName"]
    if parameter["type"] != "String" or not isinstance(parameter["defaultValue"], str):
        raise SystemExit("IncrementFileName must retain its documented String default")
    path = bundle / "reflex" / "ReflexEntities.json"
    entities = load_json(path)
    changed = False
    for entity in entities:
        definition = entity.get("payload", {}).get("definition", {})
        if definition.get("type") != "Rule":
            continue
        instance = json.loads(definition["instance"])
        for step in instance["steps"]:
            for row in step.get("rows", []):
                if row.get("kind") != "FabricItemInvocation":
                    continue
                parameters = next(a for a in row["arguments"] if a.get("name") == "parameters")["values"]
                names = [
                    next(a["value"] for a in p["arguments"] if a["name"] == "parameterName")
                    for p in parameters
                ]
                if "IncrementFileName" not in names:
                    parameters.append({
                        "arguments": [
                            {"name": "parameterName", "type": "string", "value": "IncrementFileName"},
                            {"name": "parameterValue", "type": "complexArray", "values": [
                                {"type": "string", "value": parameter["defaultValue"]}
                            ]},
                            {"name": "parameterType", "type": "string", "value": parameter["type"]},
                        ],
                        "kind": "FabricItemParameter",
                        "type": "complex",
                    })
                    changed = True
        definition["instance"] = json.dumps(instance, ensure_ascii=False, separators=(",", ":"))
    if changed:
        write_lf(path, dumps2(entities))
    return changed


def build_bundle_manifest(root: Path, instructions: str) -> None:
    workshop = root / "workshop" / f"v{VERSION}"
    bundle_root = workshop / "provisioning" / "bundle"
    manifest_path = bundle_root / "bundle-manifest.json"
    manifest = load_json(manifest_path)

    files = sorted(
        path
        for path in bundle_root.rglob("*")
        if path.is_file() and path.name != "bundle-manifest.json"
    )
    manifest["files"] = [
        {"path": path.relative_to(bundle_root).as_posix(), "sha256": sha_bytes(path.read_bytes())}
        for path in files
    ]
    manifest["counts"]["files"] = len(files)

    config = bundle_root / "data-agent" / "Files" / "Config"
    few_shot_counts: dict[str, int] = {}
    few_shot_digests: set[str] = set()
    for stage in ("draft", "published"):
        shots = load_json(next((config / stage).glob("lakehouse-tables-*/fewshots.json")))["fewShots"]
        few_shot_counts[stage] = len(shots)
        few_shot_digests.add(sha_text(canonical(shots)))
    manifest["counts"]["lakehouseFewShots"] = few_shot_counts
    if len(few_shot_digests) != 1:
        raise SystemExit("draft and published few-shots differ; refusing to seal a split bundle")

    stage_configs = {
        stage: load_json(config / stage / "stage_config.json") for stage in ("draft", "published")
    }
    if stage_configs["draft"] != stage_configs["published"]:
        raise SystemExit("draft and published stage configs differ; refusing to seal a split bundle")
    if stage_configs["published"]["aiInstructions"] != instructions:
        raise SystemExit("stage_config.aiInstructions does not mirror agent-instructions.txt")
    if len(instructions) > INSTRUCTION_CHAR_LIMIT:
        raise SystemExit(
            f"global instructions are {len(instructions)} characters; this distribution's sealed "
            f"budget is at most {INSTRUCTION_CHAR_LIMIT}"
        )

    kusto = load_json(next((config / "published").glob("kusto-*/datasource.json")))
    shape_count = kusto["dataSourceInstructions"].count("summarize sum(ObservationCount)")

    contract = manifest["contracts"]["dataAgent"]
    contract["globalInstructionsSha256"] = sha_text(instructions)
    contract["portableStageTemplateSha256"] = sha_text(stage_configs["published"]["aiInstructions"])
    contract["lakehouseFewShotsSha256"] = few_shot_digests.pop()
    contract["terminologyRuleCount"] = terminology_rule_count(instructions)
    contract["globalInstructionsChars"] = len(instructions)
    contract["globalInstructionsBytes"] = len(instructions.encode("utf-8"))
    contract["globalInstructionsCharLimit"] = INSTRUCTION_CHAR_LIMIT
    contract["kustoQueryShapeCount"] = shape_count
    contract["kustoExampleDelivery"] = (
        "The legacy Core bundle carries fewshots.json for lakehouse_tables only; "
        f"its {shape_count} KQL query shapes are encoded in kusto dataSourceInstructions. "
        "Unified profiles may also register native KQL examples."
    )
    manifest["contracts"]["dataAgent"] = dict(sorted(contract.items()))
    reference_contract = load_json(bundle_root / "ai-reference" / "contract.json")
    manifest["contracts"]["aiReference"] = {
        "enabledByDefault": False,
        "contractSha256": sha_bytes((bundle_root / "ai-reference" / "contract.json").read_bytes()),
        "sqlObjectCount": len(reference_contract["sqlObjects"]),
        "kqlFunctionCount": len(reference_contract["kqlFunctions"]),
        "globalProfileRequired": True,
        "acceptanceClaimed": False,
    }
    unified_contract = load_json(bundle_root / "unified-agent" / "contract.json")
    manifest["contracts"]["unifiedAgent"] = {
        "enabledByDefault": False,
        "contractSha256": sha_bytes((bundle_root / "unified-agent" / "contract.json").read_bytes()),
        "agentCount": 1,
        "teachingOntologyShape": unified_contract["teachingOntologyShape"],
        "codeInterpreterEnabled": True,
        "acceptanceClaimed": False,
    }
    write_lf(manifest_path, dumps2(manifest))


def build_payload(root: Path) -> dict[str, Any]:
    workshop = root / "workshop" / f"v{VERSION}"
    bundle_root = workshop / "provisioning" / "bundle"
    data_root = workshop / "data"

    bundle: dict[str, str] = {}
    for path in sorted(bundle_root.rglob("*")):
        if not path.is_file():
            continue
        blob = path.read_bytes()
        text = blob.decode("utf-8")
        # read_text() would fold CRLF to LF here, so the payload a participant
        # unpacks would not reproduce the bytes the bundle manifest pins. Decoding
        # the raw bytes keeps payload text and disk bytes the same object, and the
        # assertion makes that a build failure rather than a silent divergence.
        if text.encode("utf-8") != blob:
            raise SystemExit(
                f"bundle file {path.relative_to(bundle_root).as_posix()} does not round-trip; "
                "payload text would not reproduce the sealed bytes"
            )
        if "\r" in text:
            raise SystemExit(
                f"bundle file {path.relative_to(bundle_root).as_posix()} carries a carriage return; "
                "the sealed bundle must be LF so the digests are platform independent"
            )
        bundle[path.relative_to(bundle_root).as_posix()] = text

    dataset_gzip: dict[str, str] = {}
    for folder in ("increment", "seed"):
        for path in sorted((data_root / folder).glob("*.csv")):
            dataset_gzip[f"{folder}/{path.name}"] = base64.b64encode(
                gzip.compress(path.read_bytes(), compresslevel=9, mtime=0)
            ).decode("ascii")

    dataset_manifest_path = data_root / "dataset-manifest.json"
    notebook01_path = workshop / "notebooks" / "Notebook_01_Furusato_Prepare_Ontology_Data.ipynb"
    ontology_template_path = workshop / "ontology" / "ontology-full-definition-template.json"
    bundle_manifest_path = bundle_root / "bundle-manifest.json"
    kql_path = workshop / "kql" / f"Furusato_Eventhouse_Setup_v{VERSION}.kql"

    commands = extract_kql_management_commands(kql_path.read_text("utf-8"))

    notebook04 = load_json(
        workshop / "notebooks" / "Notebook_04_Furusato_Provision_Complete_Workshop.ipynb"
    )
    runtime_hashes = {
        "ontologyCreatorCore": sha_text(
            notebook_code_source(notebook04, "class OntologyCreatorError(") + "\n"
        ),
        "provisionerCore": sha_text(
            notebook_code_source(notebook04, "class WorkshopFabricClient:") + "\n"
        ),
    }

    def group_digest(prefix: str) -> str:
        entries = [
            {"path": rel, "sha256": sha_text(text)}
            for rel, text in sorted(bundle.items())
            if rel.startswith(prefix)
        ]
        return sha_text(canonical(entries))

    #: The two simple item specs are stable creation-spec digests that no source
    #: file owns, so they are carried through from the sealed manifest.
    sealed = load_json(workshop / "provisioning" / "payload-manifest.json")["assetHashes"]

    return {
        "assetHashes": {
            "aiReference": group_digest("ai-reference/"),
            "unifiedAgent": sha_text(canonical({
                "profile": group_digest("unified-agent/"),
                "queryHelpers": group_digest("ai-reference/"),
            })),
            "bundleManifest": sha_bytes(bundle_manifest_path.read_bytes()),
            "dataAgent": group_digest("data-agent/"),
            "datasetManifest": sha_bytes(dataset_manifest_path.read_bytes()),
            "eventhouseSpec": sealed["eventhouseSpec"],
            "kqlSchema": sha_text(canonical(commands)),
            "lakehouseSpec": sealed["lakehouseSpec"],
            "notebook01": sha_bytes(notebook01_path.read_bytes()),
            "ontologyTemplate": sha_bytes(ontology_template_path.read_bytes()),
            "pipeline": group_digest("data-pipeline/"),
            "reflex": group_digest("reflex/"),
        },
        "bundle": bundle,
        "bundleManifest": load_json(bundle_manifest_path),
        "datasetGzipBase64": dataset_gzip,
        "datasetManifest": load_json(dataset_manifest_path),
        "kqlManagementCommands": commands,
        "notebook01": load_json(notebook01_path),
        "ontologyTemplate": load_json(ontology_template_path),
        "packageVersion": VERSION,
        "runtimeHashes": runtime_hashes,
        "schemaVersion": "furusato-workshop-provisioner/v1",
    }


def payload_cells(chunks: list[str]) -> list[dict[str, Any]]:
    """Keep the entire sealed payload inline, below the live editor cell limit."""
    groups = [chunks[index:index + CHUNKS_PER_CELL] for index in range(0, len(chunks), CHUNKS_PER_CELL)]
    cells = []
    for index, group in enumerate(groups):
        first, last = index == 0, index == len(groups) - 1
        lines = [f"# Sealed provisioning payload, part {index + 1}/{len(groups)}.\n"]
        if first:
            lines += ["import base64\n", "import gzip\n", "import json\n", "\n"]
        lines.append("_PAYLOAD_CHUNKS = [\n" if first else "_PAYLOAD_CHUNKS.extend([\n")
        lines += [f'  "{chunk}",\n' for chunk in group]
        lines.append("]\n" if first else "])\n")
        if last:
            lines += [
                "PROVISIONING_PAYLOAD = json.loads(\n",
                "    gzip.decompress(base64.b64decode(''.join(_PAYLOAD_CHUNKS))).decode('utf-8')\n",
                ")\n",
                "del _PAYLOAD_CHUNKS\n",
            ]
        if len("".join(lines).encode("utf-8")) > PAYLOAD_CELL_MAX_BYTES:
            raise SystemExit("embedded payload cell exceeds the safe Fabric editor budget")
        cells.append({
            "cell_type": "code",
            "execution_count": None,
            "metadata": {"tags": [PAYLOAD_CELL_TAG]},
            "outputs": [],
            "source": lines,
        })
    return cells


def replace_payload_cells(notebook: dict[str, Any], chunks: list[str]) -> None:
    indexes = [index for index, cell in enumerate(notebook["cells"]) if is_payload_cell(cell)]
    if not indexes or indexes != list(range(indexes[0], indexes[-1] + 1)):
        raise SystemExit("payload cells must be a single contiguous block")
    notebook["cells"][indexes[0]:indexes[-1] + 1] = payload_cells(chunks)


def embed_json_cell(path: Path, cell_index: int, variable: str, data: Any) -> bool:
    """Rewrite an ``import json`` + ``NAME = json.loads(r'''...''')`` embed cell.

    Notebooks 02 and 03 ship the semantic-metadata manifest and the deployable
    definition template inline so a participant can run them without the repo.
    The embed must therefore be regenerated whenever the source file changes.
    """
    notebook = load_json(path)
    body = json.dumps(data, ensure_ascii=False, indent=2)
    source = f"import json\n\n{variable} = json.loads(r'''{body}''')"
    lines = source.splitlines(keepends=True)
    wanted = json.dumps(notebook, ensure_ascii=False, indent=1) + "\n"
    if notebook["cells"][cell_index]["source"] == lines and path.read_bytes() == wanted.encode("utf-8"):
        return False
    notebook["cells"][cell_index]["source"] = lines
    write_lf(path, json.dumps(notebook, ensure_ascii=False, indent=1) + "\n")
    return True


def refresh_notebook_embeds(root: Path) -> list[str]:
    workshop = root / "workshop" / f"v{VERSION}"
    notebooks = workshop / "notebooks"
    changed = []
    if embed_json_cell(
        notebooks / "Notebook_02_Furusato_Apply_Ontology_Metadata.ipynb",
        3,
        "ONTOLOGY_METADATA",
        load_json(workshop / "ontology" / "ontology-semantic-metadata.json"),
    ):
        changed.append("Notebook_02 ONTOLOGY_METADATA")
    if embed_json_cell(
        notebooks / "Notebook_03_Furusato_Create_Complete_Ontology.ipynb",
        3,
        "ONTOLOGY_DEFINITION_TEMPLATE",
        load_json(workshop / "ontology" / "ontology-full-definition-template.json"),
    ):
        changed.append("Notebook_03 ONTOLOGY_DEFINITION_TEMPLATE")
    return changed


def refresh_provisioner_source(root: Path) -> None:
    """Generate Notebook 04 runtime/parameter wiring from canonical source."""
    path = root / "workshop" / f"v{VERSION}" / "notebooks" / "Notebook_04_Furusato_Provision_Complete_Workshop.ipynb"
    notebook = load_json(path)
    runtime = (root / "tools/provisioning/workshop_runtime.py").read_bytes().decode("utf-8")
    matches = [
        cell for cell in notebook["cells"]
        if cell.get("cell_type") == "code" and "class WorkshopFabricClient:" in "".join(cell.get("source", []))
    ]
    if len(matches) != 1:
        raise SystemExit("Notebook 04 must contain exactly one provisioner runtime cell")
    matches[0]["source"] = runtime.splitlines(keepends=True)
    parameter_cells = [
        cell for cell in notebook["cells"]
        if "# Fabric parameter cell" in "".join(cell.get("source", []))
    ]
    if len(parameter_cells) != 1:
        raise SystemExit("Notebook 04 parameter cell is ambiguous")
    parameters = "".join(parameter_cells[0]["source"]).rstrip("\n") + "\n"
    if "ALLOW_AUTOMATED_APPLY =" not in parameters:
        parameters += "\nALLOW_AUTOMATED_APPLY = False\n"
    if "USE_PARTICIPANT_NOTEBOOK_NAMES =" not in parameters:
        parameters += "USE_PARTICIPANT_NOTEBOOK_NAMES = False\n"
    if "ENABLE_AI_REFERENCE_ARCHITECTURE =" not in parameters:
        parameters += (
            "\n# Opt-in requires an explicitly packaged, hash-pinned reference GLOBAL.\n"
            "ENABLE_AI_REFERENCE_ARCHITECTURE = False\n"
            'REFERENCE_AGENT_NAME = ""\n'
            'REFERENCE_AGENT_ROLE = "isolated-reference"\n'
            'REFERENCE_AGENT_EXPECTED_ID = ""\n'
        )
    if "ENABLE_UNIFIED_DATA_AGENT =" not in parameters:
        parameters += (
            "\n# One primary Agent: reference SQL/KQL helpers + teaching Ontology + Code Interpreter.\n"
            "# Mutually exclusive with ENABLE_AI_REFERENCE_ARCHITECTURE.\n"
            "ENABLE_UNIFIED_DATA_AGENT = False\n"
        )
    parameter_cells[0]["source"] = parameters.splitlines(keepends=True)
    execution = [
        cell for cell in notebook["cells"]
        if "CONFIG = ProvisioningConfig(" in "".join(cell.get("source", []))
    ]
    if len(execution) != 1:
        raise SystemExit("Notebook 04 execution cell is ambiguous")
    text = "".join(execution[0]["source"])
    if "allow_automated_apply=" not in text:
        marker = "    apply_changes=APPLY_CHANGES,\n"
        if text.count(marker) != 1:
            raise SystemExit("Notebook 04 apply configuration changed")
        text = text.replace(marker, marker + "    allow_automated_apply=ALLOW_AUTOMATED_APPLY,\n")
    if "use_participant_notebook_names=" not in text:
        marker = "    participant_id=PARTICIPANT_ID,\n"
        if text.count(marker) != 1:
            raise SystemExit("Notebook 04 participant configuration changed")
        text = text.replace(marker, marker + "    use_participant_notebook_names=USE_PARTICIPANT_NOTEBOOK_NAMES,\n")
    if "enable_ai_reference_architecture=" not in text:
        marker = "    poll_interval_seconds=POLL_INTERVAL_SECONDS,\n"
        if text.count(marker) != 1:
            raise SystemExit("Notebook 04 config constructor changed")
        text = text.replace(marker, marker + (
            "    enable_ai_reference_architecture=ENABLE_AI_REFERENCE_ARCHITECTURE,\n"
            "    reference_agent_name=REFERENCE_AGENT_NAME,\n"
            "    reference_agent_role=REFERENCE_AGENT_ROLE,\n"
            "    reference_agent_expected_id=REFERENCE_AGENT_EXPECTED_ID,\n"
        ))
    if "enable_unified_data_agent=" not in text:
        marker = "    enable_ai_reference_architecture=ENABLE_AI_REFERENCE_ARCHITECTURE,\n"
        if text.count(marker) != 1:
            raise SystemExit("Notebook 04 reference/unified configuration changed")
        text = text.replace(marker, marker + "    enable_unified_data_agent=ENABLE_UNIFIED_DATA_AGENT,\n")
    execution[0]["source"] = text.splitlines(keepends=True)
    write_lf(path, json.dumps(notebook, indent=2) + "\n")


def refresh_ontology_wire_sources(root: Path) -> None:
    """Embed one maintained serializer in the three standalone ontology runtimes."""
    helper = inspect.getsource(reference_ontology.ontology_json_bytes).rstrip() + "\n"
    encoder = (
        "def _encode_part_json(value: dict[str, Any]) -> str:\n"
        "    return base64.b64encode(ontology_json_bytes(value)).decode(\"ascii\")\n"
    )
    for number in (2, 3, 4):
        path = next((root / "workshop" / f"v{VERSION}" / "notebooks").glob(f"Notebook_{number:02}_*.ipynb"))
        notebook = load_json(path)
        matches = [
            cell for cell in notebook["cells"]
            if cell.get("cell_type") == "code" and "def _encode_part_json(" in "".join(cell.get("source", []))
        ]
        if len(matches) != 1:
            raise SystemExit(f"Notebook {number:02} ontology encoder is ambiguous")
        source = "".join(matches[0]["source"])
        functions = {
            node.name: node for node in ast.parse(source).body
            if isinstance(node, ast.FunctionDef)
        }
        if "_encode_part_json" not in functions:
            raise SystemExit("Ontology encoder is not a top-level function")
        replacements = [("_encode_part_json", encoder)]
        if "ontology_json_bytes" in functions:
            replacements.append(("ontology_json_bytes", helper))
        else:
            replacements = [("_encode_part_json", helper + "\n\n" + encoder)]
        lines = source.splitlines(keepends=True)
        for name, replacement in sorted(replacements, key=lambda item: functions[item[0]].lineno, reverse=True):
            node = functions[name]
            lines[node.lineno - 1:node.end_lineno] = replacement.splitlines(keepends=True)
        matches[0]["source"] = lines
        write_lf(path, json.dumps(notebook, ensure_ascii=number == 4, indent=2 if number == 4 else 1) + "\n")


def refresh_reference_assets(root: Path) -> None:
    bundle = root / "workshop" / f"v{VERSION}" / "provisioning" / "bundle"
    for relative, text in reference_assets.build_assets(root).items():
        path = bundle / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        write_lf(path, text)
    text_path = bundle / "ai-reference/global-instructions.txt"
    profile_path = bundle / "ai-reference/global-profile.json"
    if text_path.is_file() != profile_path.is_file():
        raise SystemExit("reference GLOBAL and its hash/status profile must be packaged together")
    if text_path.is_file():
        profile = load_json(profile_path)
        raw = text_path.read_bytes()
        text = raw.decode("utf-8")
        if (
            profile.get("schemaVersion") != "furusato-reference-global/v1"
            or profile.get("status") not in {"candidate", "accepted"}
            or profile.get("sha256") != sha_bytes(raw)
            or not text.strip() or text.startswith("\ufeff") or "\r" in text
            or len(text) > INSTRUCTION_CHAR_LIMIT
        ):
            raise SystemExit("packaged reference GLOBAL hash, format or declared status is invalid")


def refresh_unified_assets(root: Path) -> None:
    """Seal a portable one-Agent profile while retaining legacy bundle inputs."""
    from unified_agent import build_unified_assets
    import workshop_runtime

    bundle_root = root / "workshop" / f"v{VERSION}" / "provisioning" / "bundle"
    existing = {
        path.relative_to(bundle_root).as_posix(): path.read_bytes().decode("utf-8")
        for path in bundle_root.rglob("*") if path.is_file()
    }
    reference = workshop_runtime.load_reference_assets({"bundle": existing})
    core_paths = [
        name for name, text in existing.items()
        if name.startswith("data-agent/Files/Config/published/")
        and name.endswith("/datasource.json")
        and json.loads(text).get("type") == "ontology"
    ]
    if len(core_paths) != 1:
        raise SystemExit("Canonical teaching Ontology datasource is ambiguous")
    core_path = core_paths[0]
    profile_root = root / "tools" / "data-agent" / "unified"
    profile_files = {
        path.name: path.read_bytes().decode("utf-8")
        for path in profile_root.iterdir()
        if path.is_file() and path.suffix in {".txt", ".json"}
    }
    assets = build_unified_assets(reference, json.loads(existing[core_path]), profile_files)
    profile = {name: assets[name] for name in (
        "stageConfig", "sources", "globalProfile", "publicationDescription",
    )}
    files = {
        "unified-agent/profile.json": dumps2(profile),
        "unified-agent/modules/unified_agent.py": (root / "tools/provisioning/unified_agent.py").read_text(encoding="utf-8"),
        **{"unified-agent/inputs/" + name: text for name, text in profile_files.items()},
    }
    contract = {
        "schemaVersion": "furusato-unified-agent-runtime/v1",
        "teachingOntologyShape": [10, 72, 1, 15],
        "referenceContractSha256": sha_text(existing["ai-reference/contract.json"]),
        "coreOntologySourcePath": core_path,
        "coreOntologySourceSha256": sha_text(existing[core_path]),
        "codeInterpreterEnabled": True,
        "agentNameTemplate": "DA_Furusato_<PID>",
        "createsAIPath": False,
        "acceptanceClaimed": False,
        "files": {name: sha_text(text) for name, text in sorted(files.items())},
    }
    files["unified-agent/contract.json"] = dumps2(contract)
    for name, text in files.items():
        if "\r" in text:
            raise SystemExit(f"Unified asset is not LF: {name}")
        target = bundle_root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        write_lf(target, text)


def freeze_reference_global(root: Path, path: Path, expected_sha256: str, status: str) -> None:
    """Package an explicit operator-owned profile, never promote it to Core."""
    raw = path.read_bytes()
    if sha_bytes(raw) != expected_sha256 or status not in {"candidate", "accepted"}:
        raise SystemExit("reference GLOBAL requires its exact SHA-256 and candidate/accepted status")
    text = raw.decode("utf-8")
    if not text.strip() or "\r" in text or text.startswith("\ufeff") or len(text) > INSTRUCTION_CHAR_LIMIT:
        raise SystemExit("reference GLOBAL must be nonempty UTF-8/LF, without BOM, and at most 15000 characters")
    bundle = root / "workshop" / f"v{VERSION}" / "provisioning" / "bundle" / "ai-reference"
    bundle.mkdir(parents=True, exist_ok=True)
    write_lf(bundle / "global-instructions.txt", text)
    write_lf(bundle / "global-profile.json", dumps2({
        "schemaVersion": "furusato-reference-global/v1",
        "sha256": expected_sha256,
        "status": status,
        "statusProvenance": "Explicit operator declaration; packaging is not an evaluation or acceptance proof.",
    }))


def sealed_paths(root: Path, workshop: Path) -> list[Path]:
    """Every file this tool authors or hashes by raw bytes.

    A digest over raw bytes is only reproducible if the bytes are, so each of
    these has to be LF on every platform. The bundle is enumerated rather than
    listed so a new bundle file is covered the moment it is added.
    """
    bundle_root = workshop / "provisioning" / "bundle"
    paths = [
        workshop / "provisioning" / "payload-manifest.json",
        workshop / "participant-workspace-contract.json",
        workshop / "ontology" / "ontology-semantic-metadata.json",
        workshop / "ontology" / "ontology-full-definition-template.json",
        workshop / "data" / "dataset-manifest.json",
        workshop / "data" / "SHA256SUMS.txt",
        workshop / "kql" / f"Furusato_Eventhouse_Setup_v{VERSION}.kql",
        root / "tools" / "ontology" / "Test-OntologyCardinality.ps1",
        root / "tools" / "data" / "Test-IncrementConsistency.ps1",
    ]
    paths += sorted(workshop.glob("notebooks/*.ipynb"))
    paths += sorted(path for path in bundle_root.rglob("*") if path.is_file())
    paths += [root / "tools/provisioning/workshop_runtime.py"]
    paths += [root / relative for relative in reference_assets.MODULE_PATHS.values()]
    return paths


def _assert_authored_files_are_lf(root: Path, workshop: Path) -> None:
    offenders = [
        path.relative_to(root).as_posix()
        for path in sealed_paths(root, workshop)
        if path.is_file() and b"\r" in path.read_bytes()
    ]
    if offenders:
        raise SystemExit(
            "these sealed files carry CRLF, so their digests would differ per platform: "
            + ", ".join(offenders)
        )


def _assert_source_parity(sources: list[dict], by_type: dict[str, dict], few_shots: list) -> None:
    """Every embedded text equals the bundle value and its own declared digest.

    Three things have to agree for each of the three sources: the text the bundle
    ships, the copy the contract embeds, and the digest the contract declares. The
    check is written as an assertion rather than left to the reseal order so that a
    future edit to the loop above cannot quietly reintroduce the drift.
    """
    for source in sources:
        definition = by_type[source["type"]]
        label = source["type"]
        pairs: list[tuple[str, str, str, str]] = [
            ("description", source["description"], definition["userDescription"], source["descriptionSha256"])
        ]
        if source.get("instructionsSha256") is not None:
            pairs.append(
                (
                    "instructions",
                    source["instructions"],
                    definition["dataSourceInstructions"],
                    source["instructionsSha256"],
                )
            )
        for field, embedded, bundle_value, declared in pairs:
            if embedded != bundle_value:
                raise SystemExit(f"{label}.{field}: contract copy differs from the bundle text")
            if sha_text(embedded) != declared:
                raise SystemExit(f"{label}.{field}: declared digest does not hash the embedded text")
        if source.get("fewShotsSha256") is not None:
            if source["fewShots"] != few_shots:
                raise SystemExit(f"{label}.fewShots: contract copy differs from the bundle few-shots")
            if sha_text(canonical(source["fewShots"])) != source["fewShotsSha256"]:
                raise SystemExit(f"{label}.fewShots: declared digest does not hash the embedded array")


def _reseal_in_place(root: Path, check: bool, reference_global: tuple[Path, str, str] | None = None) -> int:
    workshop = root / "workshop" / f"v{VERSION}"
    before = snapshot_tree(workshop) if check else {}
    instructions = (workshop / "data-agent" / "agent-instructions.txt").read_text("utf-8")

    if reference_global:
        freeze_reference_global(root, *reference_global)
    refresh_ontology_wire_sources(root)
    refresh_provisioner_source(root)
    for label in refresh_notebook_embeds(root):
        print(f"refreshed embed: {label}")
    for label in sync_rank_descriptions(root):
        print(f"rank descriptions {label}")
    if sync_reflex_pipeline_default(root):
        print("refreshed Reflex explicit IncrementFileName default; dynamic Subject preserved")
    refresh_reference_assets(root)
    refresh_unified_assets(root)
    build_bundle_manifest(root, instructions)
    payload = build_payload(root)
    raw = (json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
    digest = sha_bytes(raw)
    encoded = base64.b64encode(gzip.compress(raw, compresslevel=9, mtime=0)).decode("ascii")
    chunks = [encoded[index : index + CHUNK] for index in range(0, len(encoded), CHUNK)]

    notebook_path = workshop / "notebooks" / "Notebook_04_Furusato_Provision_Complete_Workshop.ipynb"
    notebook = load_json(notebook_path)
    replace_payload_cells(notebook, chunks)
    notebook_blob = (json.dumps(notebook, indent=2) + "\n").encode("utf-8")
    write_bytes_if_changed(notebook_path, notebook_blob)

    manifest_path = workshop / "provisioning" / "payload-manifest.json"
    manifest = load_json(manifest_path)
    manifest["assetHashes"] = payload["assetHashes"]
    manifest["bundleFiles"] = len(payload["bundle"])
    manifest["datasetFiles"] = len(payload["datasetGzipBase64"])
    manifest["embeddedGzipBase64Bytes"] = len(encoded)
    manifest["kqlManagementCommands"] = len(payload["kqlManagementCommands"])
    manifest["ontologyDefinitionParts"] = len(payload["ontologyTemplate"]["parts"])
    manifest["payloadBytes"] = len(raw)
    manifest["payloadSha256"] = digest
    manifest["runtimeHashes"] = payload["runtimeHashes"]
    write_lf(manifest_path, dumps2(manifest))

    contract_path = workshop / "participant-workspace-contract.json"
    contract = load_json(contract_path)
    template = load_json(workshop / "ontology" / "ontology-full-definition-template.json")
    metadata = load_json(workshop / "ontology" / "ontology-semantic-metadata.json")
    if template["definitionTemplateSha256"] != sha_text(canonical(template["parts"])):
        raise SystemExit("ontology-full-definition-template.json definitionTemplateSha256 is stale")
    automation = contract["workshopProvisioningAutomation"]
    import workshop_runtime
    automation["activationLifecycle"] = workshop_runtime.activation_handoff()
    automation["activationLifecycle"]["sourceSha256"] = {
        relative: sha_bytes((root / relative).read_bytes())
        for relative in (
            "tools/provisioning/activation_runtime.py",
            "tools/provisioning/manage_activation.py",
        )
    }
    automation["participantIncrementFlow"] = (
        "Explicitly start the scoped rule using official start_rule or the portal Start control; "
        "setting shouldRun=true or reading Running is not execution proof. Upload each complete "
        "released CSV once with OneLake Blob PutBlob and If-None-Match: *. Match the native "
        "FileCreated event, activation Type/Subject/Source, exactly one Completed Pipeline job, "
        "Copy output and per-file KQL totals before proceeding. Stop with stop_rule or portal Stop; "
        "never silently substitute manual ingestion or re-upload an attempted file."
    )
    automation["payloadSha256"] = digest
    automation["bundleManifestSha256"] = payload["assetHashes"]["bundleManifest"]
    automation["payloadManifestSha256"] = sha_bytes(manifest_path.read_bytes())
    automation["notebookSha256"] = sha_bytes(notebook_blob)
    automation["lakehouseFewShotCount"] = len(
        load_json(
            next(
                (
                    workshop
                    / "provisioning"
                    / "bundle"
                    / "data-agent"
                    / "Files"
                    / "Config"
                    / "published"
                ).glob("lakehouse-tables-*/fewshots.json")
            )
        )["fewShots"]
    )
    automation["kqlManagementCommandCount"] = len(payload["kqlManagementCommands"])
    automation["portableBundleFileCount"] = len(payload["bundle"])
    contract["participantNames"]["agent_ontology"] = "ONT_Furusato_AIPath_<PID>"
    contract["participantNames"]["referenceDataAgent"] = "DA_Furusato_AIReference_<PID>"
    reference_contract = load_json(workshop / "provisioning/bundle/ai-reference/contract.json")
    global_profile_path = workshop / "provisioning/bundle/ai-reference/global-profile.json"
    contract["aiReferenceArchitecture"] = {
        "enabledByDefault": False,
        "flag": "ENABLE_AI_REFERENCE_ARCHITECTURE",
        "assetSha256": payload["assetHashes"]["aiReference"],
        "contractPath": "provisioning/bundle/ai-reference/contract.json",
        "globalProfile": load_json(global_profile_path) if global_profile_path.is_file() else None,
        "incompleteBundleBehavior": "Enabling without an explicit hash-pinned candidate/accepted GLOBAL fails before authentication.",
        "targetRole": "isolated-reference",
        "authorizedCandidateReuse": "Explicit REFERENCE_AGENT_NAME, REFERENCE_AGENT_ROLE=authorized-candidate and exact REFERENCE_AGENT_EXPECTED_ID; exact existing configuration only.",
        "corePromotion": "Not implemented; separate explicit operator-owned procedure required.",
        "sqlObjects": reference_contract["sqlObjects"],
        "selectedSqlObjects": reference_contract["selectedSqlObjects"],
        "kqlFunctionNames": reference_contract["kqlFunctions"],
        "kqlManagementCommandCount": reference_contract["kqlReferenceManagementCommandCount"],
        "teachingOntology": {"entities": 10, "staticProperties": 72, "timeseriesProperties": 1, "relationships": 15},
        "agentOntology": {"entities": 10, "staticProperties": 21, "timeseriesProperties": 0, "relationships": 15},
        "nativeSchemaProvenance": reference_contract["nativeSchemaProvenance"],
        "oneLakeSecurity": "UNKNOWN unless a Boolean setting is explicitly returned; successful refresh is a scoped functional probe only.",
        "acceptanceClaimed": False,
    }
    unified_profile = load_json(workshop / "provisioning/bundle/unified-agent/profile.json")
    contract["unifiedAgentArchitecture"] = {
        "enabledByDefault": False,
        "flag": "ENABLE_UNIFIED_DATA_AGENT",
        "mutuallyExclusiveWith": "ENABLE_AI_REFERENCE_ARCHITECTURE",
        "assetSha256": payload["assetHashes"]["unifiedAgent"],
        "contractPath": "provisioning/bundle/unified-agent/contract.json",
        "profilePath": "provisioning/bundle/unified-agent/profile.json",
        "globalProfile": unified_profile["globalProfile"],
        "agentNameTemplate": "DA_Furusato_<PID>",
        "agentCount": 1,
        "codeInterpreterEnabled": True,
        "teachingOntology": {"entities": 10, "staticProperties": 72, "timeseriesProperties": 1, "relationships": 15},
        "createsAIPath": False,
        "sqlObjects": reference_contract["sqlObjects"],
        "selectedSqlObjects": reference_contract["selectedSqlObjects"],
        "kqlFunctionNames": reference_contract["kqlFunctions"],
        "existingAgentBehavior": "Read-only exact-match reuse; explicit staged migration is required for a different existing primary definition.",
        "acceptanceClaimed": False,
    }

    agent = contract["dataAgent"]
    agent["globalInstructions"] = instructions
    agent["globalInstructionsSha256"] = sha_text(instructions)
    agent["globalInstructionsCharacters"] = len(instructions)
    agent["globalInstructionsUtf8Bytes"] = len(instructions.encode("utf-8"))
    agent["globalInstructionsCharLimit"] = INSTRUCTION_CHAR_LIMIT
    # The contract used to carry a second name for the same two numbers. Two
    # aliases can only ever agree by accident - they were last seen holding the
    # pre-refactor 19,493 while the canonical pair had moved on - so the shorter
    # pair is deleted rather than kept in sync.
    for alias in ("globalInstructionsChars", "globalInstructionsBytes"):
        agent.pop(alias, None)

    # The KQL shape count is stated in four places; all of them are derived from
    # the shipped instructions rather than maintained by hand.
    manifest_contract = load_json(
        workshop / "provisioning" / "bundle" / "bundle-manifest.json"
    )["contracts"]["dataAgent"]
    shape_count = int(manifest_contract["kustoQueryShapeCount"])
    shape_word = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five"}[shape_count]
    automation["kustoQueryShapeCount"] = shape_count
    automation["kustoExampleDelivery"] = (
        "The legacy Core bundle carries fewshots.json for lakehouse_tables only; "
        f"its {shape_word} KQL query shapes are encoded in kusto dataSourceInstructions. "
        "Unified profiles may also register native KQL examples."
    )
    agent["kustoExamplePolicy"] = (
        "The definition format carries no fewshots.json part for the kusto source, so the "
        f"{shape_word} supported KQL query shapes are described in the kusto dataSourceInstructions "
        "instead. None of them reproduces a participant evaluation question."
    )

    config = workshop / "provisioning" / "bundle" / "data-agent" / "Files" / "Config" / "published"
    by_type = {}
    for folder in sorted(config.iterdir()):
        if folder.is_dir() and (folder / "datasource.json").is_file():
            definition = load_json(folder / "datasource.json")
            by_type[definition["type"]] = definition
    few_shots = load_json(next(config.glob("lakehouse-tables-*/fewshots.json")))["fewShots"]
    for source in agent["sources"]:
        definition = by_type[source["type"]]
        # The contract embeds the description and the instructions so a reader can
        # see what the Agent was told without opening the bundle. Recomputing only
        # the digests left that embedded copy behind whenever a source text moved:
        # the file then declared a hash of text it no longer contained. The text is
        # therefore refreshed from the bundle first, and hashed second.
        source["description"] = definition["userDescription"]
        source["descriptionSha256"] = sha_text(definition["userDescription"])
        if "instructions" in source:
            source["instructions"] = definition["dataSourceInstructions"]
        if source.get("instructionsSha256") is not None:
            source["instructionsSha256"] = sha_text(definition["dataSourceInstructions"])
        if source.get("fewShotsSha256") is not None:
            source["fewShots"] = few_shots
            source["fewShotsSha256"] = sha_text(canonical(few_shots))

    _assert_source_parity(agent["sources"], by_type, few_shots)

    contract["ontology"]["creationAutomation"]["templateSha256"] = template["definitionTemplateSha256"]
    contract["ontology"]["creationAutomation"]["templateHashConvention"] = (
        "SHA-256 of the canonical compact JSON of the template's parts array "
        "(separators=(',',':'), sort_keys, ensure_ascii=False), which is the value the template "
        "carries as definitionTemplateSha256; it is not the SHA-256 of the file bytes"
    )
    contract["ontology"]["metadataAutomation"]["manifestSha256"] = sha_text(canonical(metadata))
    contract["ontology"]["metadataAutomation"]["manifestHashConvention"] = (
        "SHA-256 of the canonical compact JSON of the whole manifest object "
        "(separators=(',',':'), sort_keys, ensure_ascii=False); it is not the SHA-256 of the file bytes"
    )
    # Relationship cardinality is owned by the semantic-metadata manifest; the
    # contract mirrors it so Test-OntologyCardinality.ps1 can compare five copies.
    coverage = contract["ontology"]["relationshipCardinalityCoverage"]
    coverage["requiredAttributes"] = [
        "direction",
        "cardinality",
        "grain",
        "sourceParticipation",
        "targetParticipation",
    ]
    coverage["derivationMode"] = "actual data (default)"
    coverage["derivedFrom"] = (
        "Default actual-data mode: the packaged seed CSVs are streamed and every node count, edge "
        "count and participation figure is recomputed from the rows, the dataset manifest is checked "
        "against that recomputation, and only then is cardinality derived. One edge is emitted per "
        "binding-table row, so the side whose instance count equals the edge count carries the "
        "unique key. Optionality is decided separately by counting source instances that emit no "
        "edge: none means one-to-many from the source, one or more means zero-to-many from it."
    )
    coverage["declaredCountFallback"] = (
        "Test-OntologyCardinality.ps1 -FromData:$false derives the same shapes from "
        "dataset-manifest expected.nodeCounts and expected.edgeCounts instead. Those are declared "
        "values, so the fallback proves only that the ontology agrees with the manifest; it cannot "
        "detect a manifest that disagrees with the CSVs, and it accepts either optionality word "
        "because participation is not recomputed."
    )
    for entry in contract["ontology"]["relationships"]:
        enrichment = metadata["relationships"][entry["name"]]["semanticEnrichment"]
        attributes = enrichment.get("customAttributes", {})
        entry["cardinality"] = attributes["cardinality"]
        entry["sourceParticipation"] = attributes["sourceParticipation"]
        entry["targetParticipation"] = attributes["targetParticipation"]
    contract["ontology"]["relationshipCardinalityCoverage"]["validatorSha256"] = sha_bytes(
        (root / "tools" / "ontology" / "Test-OntologyCardinality.ps1").read_bytes()
    )
    contract["ontology"]["relationshipCardinalityCoverage"]["validatorHashConvention"] = (
        "SHA-256 of the raw validator file bytes"
    )
    contract["dataset"]["manifestSha256"] = sha_bytes(
        (workshop / "data" / "dataset-manifest.json").read_bytes()
    )
    contract["dataset"]["checksumsSha256"] = sha_bytes(
        (workshop / "data" / "SHA256SUMS.txt").read_bytes()
    )
    contract["dataset"]["validatorSha256"] = sha_bytes(
        (root / "tools" / "data" / "Test-IncrementConsistency.ps1").read_bytes()
    )
    contract["dataset"]["validatorHashConvention"] = "SHA-256 of the raw validator file bytes"
    contract["kql"]["sha256"] = sha_bytes(
        (workshop / "kql" / f"Furusato_Eventhouse_Setup_v{VERSION}.kql").read_bytes()
    )
    contract["analyticsExtension"]["notebook"]["sha256"] = sha_bytes(
        (workshop / "notebooks" / "Notebook_05_Furusato_Analytics_Quality_and_BI.ipynb").read_bytes()
    )
    power_bi = contract["analyticsExtension"]["powerBi"]
    power_bi["projectSha256"] = sha_bytes((workshop / power_bi["projectPath"]).read_bytes())
    power_bi["semanticModelTreeSha256"] = tree_sha256(workshop / power_bi["semanticModelPath"])
    power_bi["reportTreeSha256"] = tree_sha256(workshop / power_bi["reportPath"])
    power_bi["deploymentToolSha256"] = sha_bytes((root / power_bi["deploymentTool"]).read_bytes())
    library = contract["analyticsExtension"]["variableLibraryTemplate"]
    library["treeSha256"] = tree_sha256(workshop / library["path"])
    write_lf(contract_path, dumps2(contract))
    _assert_authored_files_are_lf(root, workshop)

    print(f"payload      {len(raw):,} bytes  sha256 {digest}")
    print(f"notebook 04  {len(notebook_blob):,} bytes  sha256 {sha_bytes(notebook_blob)}")
    print(
        f"instructions {len(instructions):,} chars / "
        f"{len(instructions.encode('utf-8')):,} bytes  sha256 {sha_text(instructions)}"
    )
    if check:
        after = snapshot_tree(workshop)
        drift = sorted(
            path for path in before.keys() | after.keys() if before.get(path) != after.get(path)
        )
        if drift:
            print("drift:\n" + "\n".join(drift))
            return 1
    return 0


def reseal(root: Path, check: bool, reference_global: tuple[Path, str, str] | None = None) -> int:
    """Reseal transactionally, restoring the workshop if any gate aborts."""
    workshop = root / "workshop" / f"v{VERSION}"
    original = snapshot_bytes(workshop)
    try:
        return _reseal_in_place(root, check, reference_global)
    except BaseException:
        restore_tree(workshop, original)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail when the reseal changes a file under workshop/v2.7.0",
    )
    parser.add_argument("--reference-global", type=Path, help="Explicit frozen reference GLOBAL file; never changes released Core")
    parser.add_argument("--reference-global-sha256", help="Exact SHA-256 of the provided reference GLOBAL bytes")
    parser.add_argument("--reference-global-status", choices=("candidate", "accepted"), help="Operator-declared profile status, not inferred quality")
    args = parser.parse_args()
    fields = (args.reference_global, args.reference_global_sha256, args.reference_global_status)
    if any(fields) and (not all(fields) or args.check):
        parser.error("freeze requires all three --reference-global options and cannot be combined with --check")
    return reseal(repo_root(), args.check, fields if all(fields) else None)


if __name__ == "__main__":
    sys.exit(main())
