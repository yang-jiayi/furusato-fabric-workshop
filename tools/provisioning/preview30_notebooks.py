"""Build output-free Fabric Notebook02–04 frontends with a sealed offline bundle."""
from __future__ import annotations
import base64
import gzip
import hashlib
import json
from pathlib import Path

from preview30_runtime import (
    BASE, PREVIEW, REPO, WORKSHOP_VERSION, RUNTIME_INPUT_FILES,
    CORRECTED_PROFILE_DIRECTORIES, immutable_baseline,
)

MODULES = (
    "preview30_runtime.py", "preview30_deploy.py", "preview30_verify.py",
    "preview30_ontology.py", "preview30_agent.py", "preview30_activation.py",
    "preview30_compatibility.py", "v3_artifacts.py",
    "workshop_runtime.py", "reference_kql.py", "activation_runtime.py",
)
DATA_AGENT_MODULES = (
    "source_grounded_profile", "answer_contract_profile", "time_layer_isolation",
    "fresh_grounded_profile", "native_evaluation", "native_mcp",
)
PARAMETERS = '''# Fabric parameter cell — environment identities remain in private JSON files.
PARTICIPANT_ID = "001"
ENVIRONMENT = ""  # Explicitly choose dev, test or prod.
EXPECTED_WORKSPACE_NAME = ""
SCOPE_FILE = ""  # Private scope JSON; use notebookutils.nbResPath + "/builtin/scope.json".
PLAN_FILE = ""  # Private resource-plan.json from preflight.
WRITE_GATE_FILE = ""  # Explicit folder mapping/write approval; never generated as approved.
PRIVATE_EVIDENCE_DIR = ""  # Outside the extracted source package; preserve between stages.
ACTION = "{action}"
APPLY_CHANGES = False
ALLOW_AUTOMATED_APPLY = False
CONFIRMED_PLAN_SHA256 = ""
RUN_NOTEBOOK01 = False
EXPECTED_DEFINITION_SHA256 = ""
RULE_STATEMENT_OVERRIDES = {{}}
'''
RUNNER = '''from pathlib import Path
from types import SimpleNamespace
import json
import shutil
import preview30_runtime as rt
import preview30_deploy as deploy
import preview30_verify as verify

context = notebookutils.runtime.context
if ENVIRONMENT not in ("dev", "test", "prod") or not SCOPE_FILE or not PRIVATE_EVIDENCE_DIR:
    raise ValueError("Set explicit environment, private scope file and private evidence directory. No cloud call made.")
scope_document = rt.load(Path(SCOPE_FILE))
scope = rt.scope_from_document(scope_document, ENVIRONMENT)
if scope["participantId"] != PARTICIPANT_ID:
    raise ValueError("Participant parameter differs from the private frozen scope.")
if scope["workspaceId"] != context["currentWorkspaceId"] or scope["workspaceName"] != context["currentWorkspaceName"]:
    raise ValueError("Notebook context differs from the private frozen workspace.")
if not EXPECTED_WORKSPACE_NAME or EXPECTED_WORKSPACE_NAME != context["currentWorkspaceName"]:
    raise ValueError("Set the exact expected workspace name before execution.")

class NotebookCredential:
    def get_token(self, scope_uri):
        audiences = {
            "https://api.fabric.microsoft.com/.default": "pbi",
            "https://storage.azure.com/.default": "storage",
            "https://kusto.kusto.windows.net/.default": "kusto",
            "https://analysis.windows.net/powerbi/api/.default": "pbi",
        }
        if scope_uri not in audiences:
            raise ValueError("Unsupported token audience.")
        return SimpleNamespace(token=notebookutils.credentials.getToken(audiences[scope_uri]))

credential = NotebookCredential()
evidence = rt.private_directory(Path(PRIVATE_EVIDENCE_DIR))
client = rt.EvidenceClient(scope, evidence, credential=credential)
current_notebook = client.request("GET", "/workspaces/" + scope["workspaceId"] + "/items/" + context["currentNotebookId"]).json()
if current_notebook.get("folderId") != scope["folderId"]:
    raise ValueError("The current Notebook is outside the explicitly selected folder.")

if ACTION == "preflight":
    if APPLY_CHANGES:
        raise ValueError("Preflight is read-only; APPLY_CHANGES must be False.")
    prefix = "/workspaces/" + scope["workspaceId"]
    inventory = {
        "workspace": client.request("GET", prefix).json(),
        "items": client.paged(prefix + "/items"),
        "folders": client.paged(prefix + "/folders"),
        "recoverableItems": client.paged(prefix + "/recoverableItems"),
    }
    baseline = rt.load(rt.PREVIEW / "provisioning/baseline-hashes.json")
    for relative, expected_sha in baseline["files"].items():
        path = rt.BASE / relative
        if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest() != expected_sha:
            raise ValueError("Extracted baseline byte mismatch: " + relative)
    state_file = evidence / "deployment-state.json"
    owned_state = rt.load(state_file) if state_file.exists() else None
    plan = rt.build_plan(scope, inventory, baseline, owned_state)
    rt.save(evidence / "resource-plan.json", plan)
    rt.save(evidence / "inventory-preflight.json", inventory)
    RESULT = {"mode": "read-only-preflight", "planSha256": plan["planSha256"],
              "blockers": plan["blockers"], "folderMappingVerified": scope["folderMappingVerified"],
              "cloudMutationPerformed": False}
else:
    read_only = ACTION.startswith("verify-") or ACTION == "preview-metadata"
    if not read_only and not APPLY_CHANGES:
        raise ValueError("No write made. Review the private plan, then explicitly enable APPLY_CHANGES.")
    if not read_only and context.get("isForPipeline", False) and not ALLOW_AUTOMATED_APPLY:
        raise ValueError("Automated mutation is not explicitly enabled.")
    if PLAN_FILE:
        external_plan = rt.load(Path(PLAN_FILE))
        rt.save(evidence / "resource-plan.json", external_plan)
    args = SimpleNamespace(
        environment=ENVIRONMENT, scope=Path(SCOPE_FILE), evidence_dir=evidence,
        write_gate=Path(WRITE_GATE_FILE) if WRITE_GATE_FILE else None,
        confirm=CONFIRMED_PLAN_SHA256, run_notebook01=RUN_NOTEBOOK01,
        expected_definition_sha256=EXPECTED_DEFINITION_SHA256,
        rule_statement_overrides=RULE_STATEMENT_OVERRIDES, credential=credential,
    )
    actions = {
        "deploy-sources": deploy.deploy_sources, "deploy-notebooks": deploy.deploy_notebooks,
        "verify-sources": verify.verify_sources, "deploy-realtime": deploy.deploy_realtime,
        "deploy-core": deploy.deploy_core, "preview-metadata": deploy.metadata_change,
        "apply-metadata": lambda a: deploy.metadata_change(a, apply=True),
        "handoff-ontology": deploy.handoff_ontology, "verify-gold": verify.verify_gold,
        "deploy-semantic-model": deploy.deploy_semantic_model, "verify-model": verify.verify_model,
        "refresh-model": deploy.refresh_model_once,
        "deploy-agent": deploy.deploy_agent,
        "publish-agent": deploy.publish_agent_candidate,
    }
    if ACTION not in actions:
        raise ValueError("Unsupported action; no private endpoint fallback.")
    RESULT = actions[ACTION](args)
print(json.dumps(RESULT, ensure_ascii=False, indent=2))
'''


def cell(kind: str, source: str, tags: list[str] | None = None) -> dict:
    value = {"cell_type": kind, "metadata": {}, "source": source.splitlines(keepends=True)}
    if tags:
        value["metadata"]["tags"] = tags
    if kind == "code":
        value.update({"execution_count": None, "outputs": []})
    return value


def package(*, data: bool) -> bytes:
    from preview30_compatibility import PACKAGED_INPUTS
    files: dict[str, str] = {}
    for name in MODULES:
        path = REPO / "tools/provisioning" / name
        files[path.relative_to(REPO).as_posix()] = base64.b64encode(path.read_bytes()).decode("ascii")
    for relative in (*RUNTIME_INPUT_FILES, *PACKAGED_INPUTS):
        path = REPO / relative
        files[relative] = base64.b64encode(path.read_bytes()).decode("ascii")
    folders = [
        PREVIEW / "ontology/definition", PREVIEW / "ontology/relationships", PREVIEW / "ontology/agent-compat",
        PREVIEW / "powerbi/Furusato_Analytics.SemanticModel",
        PREVIEW / "data-agent/definition", PREVIEW / "provisioning",
        BASE / "kql", BASE / "provisioning/bundle/data-pipeline", BASE / "provisioning/bundle/reflex",
    ]
    if data:
        folders.append(BASE / "data")
    for folder in folders:
        for path in sorted(folder.rglob("*")):
            if path.is_file() and path.name not in {"notebook-bundle-manifest.json", "artifact-set.json"}:
                files[path.relative_to(REPO).as_posix()] = base64.b64encode(path.read_bytes()).decode("ascii")
    for profile in CORRECTED_PROFILE_DIRECTORIES:
        for path in sorted((PREVIEW / "data-agent/candidates" / profile).rglob("*")):
            if path.is_file() and path.suffix in {".json", ".txt", ".sql"}:
                files[path.relative_to(REPO).as_posix()] = base64.b64encode(path.read_bytes()).decode("ascii")
    for number in ("01", "05"):
        for root in (BASE, PREVIEW):
            path = next((root / "notebooks").glob(f"Notebook_{number}_*.ipynb"))
            files[path.relative_to(REPO).as_posix()] = base64.b64encode(path.read_bytes()).decode("ascii")
    path = PREVIEW / "powerbi/native-metrics-contract.json"
    files[path.relative_to(REPO).as_posix()] = base64.b64encode(path.read_bytes()).decode("ascii")
    raw = json.dumps(files, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return gzip.compress(raw, mtime=0)


def build_notebooks() -> dict:
    baseline = immutable_baseline()
    baseline_path = PREVIEW / "provisioning/baseline-hashes.json"
    baseline_path.parent.mkdir(parents=True, exist_ok=True)
    baseline_path.write_bytes((json.dumps(baseline, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    small, full = package(data=False), package(data=True)
    specs = {
        "02": ("Apply_Ontology_Metadata", "preview-metadata",
               "Preview/apply native natural-language Business Rule metadata before native Metrics/UI handoff. "
               "Never use this notebook to round-trip an ontology after native Metrics were added."),
        "03": ("Create_Complete_Ontology", "deploy-core",
               "Create/read back the generation2 static core. The historical filename is retained for navigation, "
               "but this candidate is NOT complete until native Eventhouse binding and source-owned Metrics are observed. "
               "Legacy generation1 creation is not a fallback."),
        "04": ("Provision_Complete_Workshop", "preflight",
               "Run one explicit stage at a time. Default is read-only preflight. "
               "Native Activator start/stop and correlated complete-file delivery remain separate gates. "
               "Run Notebook05 only after the three increments; it reads Lakehouse/Files, not Eventhouse."),
    }
    manifest = {}
    for number, (title, action, note) in specs.items():
        compressed = full if number == "04" else small
        sha = hashlib.sha256(compressed).hexdigest()
        encoded = base64.b64encode(compressed).decode("ascii")
        name = f"Notebook_{number}_Furusato_{title}"
        cells = [
            cell("markdown", f"# Furusato Workshop {WORKSHOP_VERSION} — {name}\n\n"
                 f"**Workshop version / 教材版:** {WORKSHOP_VERSION}\n\n"
                 "**Runtime profile:** v3.0.0-preview. **Data contract:** 2.7.0-realistic.1 (unchanged CSVs).\n\n"
                 "**Production placement:** the specified folder directly; no Temp folder is required.\n\n"
                 f"{note}\n\n"
                 "Use the same private resource plan, gate and deployment-state evidence across stages. "
                 "Environment identities are parameters, never embedded in this notebook. "
                 "CLI deployment is the primary cross-machine orchestration path; this frontend uses normal NotebookUtils authentication. "
                 "The sealed package includes the source-grounded, complete-contract and time-layer-isolation compilers, "
                 "their SQL views and query examples. Apply the corrected profile only to verified fresh sources; "
                 "the historical four-source baseline alone is not the corrected Agent.\n"),
            cell("code", PARAMETERS.format(action=action), ["parameters"]),
            cell("code", "import base64, gzip, hashlib, json, sys, tempfile\nfrom pathlib import Path\n_PAYLOAD_CHUNKS = []\n"),
        ]
        for offset in range(0, len(encoded), 360000):
            cells.append(cell("code", '_PAYLOAD_CHUNKS.append("' + encoded[offset:offset + 360000] + '")\n',
                              ["furusato-preview30-payload"]))
        loader = f'''_COMPRESSED = base64.b64decode("".join(_PAYLOAD_CHUNKS), validate=True)
if hashlib.sha256(_COMPRESSED).hexdigest() != "{sha}":
    raise ValueError("Embedded package fingerprint mismatch; no authentication attempted.")
_FILES = json.loads(gzip.decompress(_COMPRESSED))
_ROOT = Path(tempfile.gettempdir()) / "furusato-preview30-{sha[:16]}"
for _relative, _encoded in _FILES.items():
    _path = (_ROOT / _relative).resolve()
    if _ROOT.resolve() not in _path.parents:
        raise ValueError("Unsafe embedded package path.")
    _raw = base64.b64decode(_encoded, validate=True)
    _path.parent.mkdir(parents=True, exist_ok=True)
    if _path.exists() and _path.read_bytes() != _raw:
        raise ValueError("Existing package bytes changed; use a clean driver session.")
    _path.write_bytes(_raw)
sys.path.insert(0, str(_ROOT / "tools/provisioning"))
sys.path.insert(0, str(_ROOT / "tools/data-agent"))
for _module, _directory in {repr({**{name[:-3]: "tools/provisioning" for name in MODULES}, **{name: "tools/data-agent" for name in DATA_AGENT_MODULES}})}.items():
    if _module in sys.modules and Path(sys.modules[_module].__file__).resolve().parent != (_ROOT / _directory).resolve():
        del sys.modules[_module]
print("Sealed portable package loaded. No Fabric mutation has occurred.")
'''
        cells.append(cell("code", loader))
        allowed_actions = {
            "02": ("preview-metadata", "apply-metadata"),
            "03": ("verify-sources", "deploy-core"),
            "04": ("preflight", "deploy-sources", "verify-sources", "deploy-realtime",
                   "deploy-core", "handoff-ontology", "verify-gold",
                   "deploy-semantic-model", "refresh-model", "verify-model", "deploy-agent", "publish-agent"),
        }[number]
        action_gate = (f"if ACTION not in {allowed_actions!r}:\n"
                       "    raise ValueError(\"Action is outside this notebook's bounded role. Use the CLI for importing notebooks.\")\n")
        cells.append(cell("code", action_gate + RUNNER))
        notebook = {"nbformat": 4, "nbformat_minor": 5, "cells": cells,
                    "metadata": {"kernelspec": {"display_name": "Synapse PySpark", "language": "Python",
                                                "name": "synapse_pyspark"},
                                 "language_info": {"name": "python"},
                                 "furusato": {"edition": "v" + WORKSHOP_VERSION, "version": WORKSHOP_VERSION,
                                              "runtimeProfile": "v3.0.0-preview", "sourceRuntimeEdition": "2.7.0",
                                              "dataContract": "2.7.0-realistic.1", "outputFree": True,
                                              "defaultMutation": False, "bundleSha256": sha}}}
        path = PREVIEW / "notebooks" / (name + ".ipynb")
        path.write_bytes((json.dumps(notebook, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))
        maximum = max(len("".join(c["source"]).encode("utf-8")) for c in cells if c["cell_type"] == "code")
        if maximum > 450000:
            raise ValueError("Fabric code-cell size exceeds the safe budget.")
        manifest[number] = {"path": path.relative_to(PREVIEW).as_posix(), "payloadSha256": sha,
                            "compressedBytes": len(compressed), "maximumCodeCellBytes": maximum,
                            "defaultAction": action, "cloudTested": False}
    return manifest
