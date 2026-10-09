"""Verify and fingerprint the complete current v3 source-artifact set."""

import argparse
import ast
import base64
import copy
import gzip
import hashlib
import json
from pathlib import Path
import subprocess

import preview30_runtime as rt


def sha(data):
    return hashlib.sha256(data).hexdigest()


def verify_notebook(notebook, baseline=None):
    metadata = notebook["metadata"]["furusato"]
    if (metadata.get("version") != rt.WORKSHOP_VERSION
            or metadata.get("edition") != "v" + rt.WORKSHOP_VERSION
            or metadata.get("runtimeProfile") != rt.EDITION
            or metadata.get("dataContract") != "2.7.0-realistic.1"):
        raise ValueError("Notebook edition, runtime or dataset identity is inconsistent.")
    if "Furusato Workshop " + rt.WORKSHOP_VERSION not in "".join(notebook["cells"][0]["source"]):
        raise ValueError("The participant-facing Notebook title is not the current workshop version.")
    for cell in notebook["cells"]:
        if cell["cell_type"] == "code":
            text = "".join(cell["source"])
            if cell.get("outputs") or cell.get("execution_count") is not None:
                raise ValueError("Distributable notebooks must not include execution outputs.")
            if len(text.encode("utf-8")) > 450000:
                raise ValueError("A code cell exceeds the supported package budget.")
            compile(text, "v3-notebook", "exec")
    if baseline is not None:
        normalized = copy.deepcopy(notebook)
        parameters = next(c for c in normalized["cells"] if "parameters" in c["metadata"].get("tags", []))
        current = f'NOTEBOOK_VERSION = "{rt.WORKSHOP_VERSION}"\n'
        if current in parameters["source"]:
            if parameters["source"].count(current) != 1:
                raise ValueError("Ambiguous Notebook audit-version assignment.")
            parameters["source"] = [
                'NOTEBOOK_VERSION = "2.7.0"\n' if line == current else line for line in parameters["source"]]
        code = lambda value: [c["source"] for c in value["cells"] if c["cell_type"] == "code"]
        if code(normalized) != code(baseline):
            raise ValueError("A data-processing code cell changed beyond the declared audit/display version.")
    return True


def verify_bundle(notebook):
    chunks = []
    for cell in notebook["cells"]:
        if "furusato-preview30-payload" in cell["metadata"].get("tags", []):
            expression = ast.parse("".join(cell["source"])).body[0]
            chunks.append(ast.literal_eval(expression.value.args[0]))
    compressed = base64.b64decode("".join(chunks), validate=True)
    if sha(compressed) != notebook["metadata"]["furusato"]["bundleSha256"]:
        raise ValueError("Embedded notebook package fingerprint differs.")
    files = json.loads(gzip.decompress(compressed))
    for name, encoded in files.items():
        path = (rt.REPO / name).resolve()
        if Path(name).is_absolute() or ".." in Path(name).parts or not path.is_relative_to(rt.REPO):
            raise ValueError("Unsafe embedded path.")
        if not path.is_file() or base64.b64decode(encoded, validate=True) != path.read_bytes():
            raise ValueError("Embedded content is stale: " + name)
    required = set(rt.RUNTIME_INPUT_FILES)
    for profile in rt.CORRECTED_PROFILE_DIRECTORIES:
        required.update(p.relative_to(rt.REPO).as_posix()
                        for p in (rt.PREVIEW / "data-agent/candidates" / profile).rglob("*")
                        if p.is_file() and p.suffix in {".json", ".txt", ".sql"})
    if not required.issubset(files):
        raise ValueError("The sealed package lacks current correction-profile inputs.")
    return {"fileCount": len(files), "payloadSha256": sha(compressed),
            "currentCorrectionProfilesIncluded": True}


def snapshot():
    edition = rt.load(rt.PREVIEW / "edition.json")
    dataset = rt.load(rt.PREVIEW / "data/dataset-manifest.json")
    if edition["workshopVersion"] != rt.WORKSHOP_VERSION or edition["runtimeProfile"] != rt.EDITION:
        raise ValueError("The workshop version and edition descriptor disagree.")
    if edition["baselineRuntimeVersion"] != (rt.REPO / "VERSION").read_text(encoding="utf-8").strip():
        raise ValueError("The legacy runtime version no longer matches its declared role.")
    if edition["datasetVersion"] != dataset["datasetVersion"] or edition["createTempByDefault"] is not False:
        raise ValueError("Dataset or production placement contract differs.")
    baseline = rt.immutable_baseline()
    csv_files = []
    for path in (rt.BASE / "data").rglob("*"):
        if path.is_file():
            current = rt.PREVIEW / path.relative_to(rt.BASE)
            if not current.is_file() or current.read_bytes() != path.read_bytes():
                raise ValueError("A current data artifact differs from the immutable baseline: " + path.name)
            if path.suffix == ".csv":
                csv_files.append(current)
    notebooks = {}
    for number in ("01", "02", "03", "04", "05"):
        path = next((rt.PREVIEW / "notebooks").glob(f"Notebook_{number}_*.ipynb"))
        value = rt.load(path)
        old = rt.load(next((rt.BASE / "notebooks").glob(f"Notebook_{number}_*.ipynb"))) if number in {"01", "05"} else None
        verify_notebook(value, old)
        notebooks[number] = {"path": path.relative_to(rt.REPO).as_posix(), "sha256": sha(path.read_bytes()),
                             "workshopVersion": rt.WORKSHOP_VERSION}
        if number in {"02", "03", "04"}:
            notebooks[number]["bundle"] = verify_bundle(value)
    paths = {rt.REPO / name for name in rt.RUNTIME_INPUT_FILES}
    paths.update({Path(__file__), rt.REPO / "tools/provisioning/build_preview30.py",
                  rt.REPO / "tools/provisioning/preview30_notebooks.py",
                  rt.REPO / "tools/provisioning/preview30_compatibility.py"})
    paths.update(rt.REPO / name for name in (
        "tools/docs/build_preview30.py", "tools/docs/validate_preview30.py",
        "tools/docs/package_preview30.py", "tools/docs/furusato_docs/preview30_content.py",
        "tools/docs/furusato_docs/context.py", "tools/docs/furusato_docs/preview30_release.py",
        "tools/docs/furusato_docs/participant30.py", "tools/docs/furusato_docs/participant30_text.py",
        "tools/docs/furusato_docs/participant30_figures.py",
        "tools/docs/furusato_docs/participant_word.py",
        "tools/html/furusato_html/preview30.py",
        "tools/html/furusato_html/diagrams.py",
        "workshop/v3.0.0-preview/README-runtime.md",
        "workshop/v3.0.0-preview/data-agent/candidates/measured-contract-20261009/README.md",
        "tools/data-agent/README.md",
        "docs/v3.0.0/tuning-20261010/calibration-and-proofreading.md",
        "docs/v3.0.0/tuning-20261010/README.md",
        "docs/v3.0.0/tuning-20261010/result-20261010.json",
        "tools/docs/build_measured_tuning_report.py",
        "tools/docs/README.md", "tools/html/README.md",
    ))
    for folder in ("data", "kql", "notebooks", "ontology", "powerbi", "data-agent", "provisioning"):
        paths.update(p for p in (rt.PREVIEW / folder).rglob("*")
                     if p.is_file() and p.suffix != ".md" and p.name != "artifact-set.json")
    participant_assets = rt.REPO / "docs" / "assets" / "v3.0.0-participant"
    if participant_assets.is_dir():
        paths.update(p for p in participant_assets.rglob("*") if p.is_file())
    paths.update(p for p in rt.BASE.rglob("*") if p.is_file())
    files = {p.relative_to(rt.REPO).as_posix(): sha(p.read_bytes()) for p in sorted(paths)}
    source_commit = subprocess.check_output(["git", "-C", str(rt.REPO), "rev-parse", "HEAD"], text=True).strip()
    return {"schemaVersion": "furusato-v3-artifact-set/v1", "workshopVersion": rt.WORKSHOP_VERSION,
            "runtimeProfile": rt.EDITION, "sourceCommit": source_commit, "edition": edition,
            "sourceTreeSha256": rt.digest(files), "candidateSourceSha256": rt.candidate_fingerprint(),
            "files": files, "notebooks": notebooks, "csvFiles": len(csv_files),
            "immutableBaselineTreeSha256": baseline["treeSha256"],
            "dataChecks": {key: baseline[key] for key in (
                "staticDonationRows", "staticDonationYen", "rawIncrementRows", "acceptedUniqueRows", "duplicateRows")},
            "productionPlacement": "specified-folder-direct", "tempRequired": False,
            "declaredCodeDelta": "Notebook01 audit/display NOTEBOOK_VERSION only; Notebook01/05 data-processing code is otherwise unchanged.",
            "historicalRunMetadataMustNotBeRewritten": True, "cloudDeploymentProvenByThisManifest": False,
            "documentationBinding": "Paired Word/HTML must embed this manifest SHA; an outer package inventory hashes the documents separately."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, help="Write the verified manifest; omit for read-only validation.")
    args = parser.parse_args()
    value = snapshot()
    if args.out:
        rt.save(args.out, value)
    print(json.dumps({key: value[key] for key in (
        "workshopVersion", "runtimeProfile", "sourceTreeSha256", "csvFiles", "dataChecks", "tempRequired")}, indent=2))
