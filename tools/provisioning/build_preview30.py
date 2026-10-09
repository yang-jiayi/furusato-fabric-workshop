"""Build portable v3 inputs without modifying v2.7 or document-owned attachments."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import ast
from preview30_ontology import generate, generate_relationships
from preview30_runtime import BASE, PREVIEW, WORKSHOP_VERSION, immutable_baseline, load, save


def write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists() or path.read_bytes() != data:
        path.write_bytes(data)


def build_relationships() -> dict:
    """Rebuild only the optional companion; no Agent, notebook or evidence writes."""
    parts, contract = generate_relationships(
        load(BASE / "ontology" / "ontology-full-definition-template.json"))
    root = PREVIEW / "ontology" / "relationships"
    for path, text in parts.items():
        write(root / "definition" / path, text.encode("utf-8"))
    save(root / "contract.json", contract)
    return {"tmdlParts": len(parts), "entityTypes": 10, "staticProperties": 72,
            "timeseriesProperties": 0, "relationshipTypes": 15, "deployed": False}


def build_agent_compatibility() -> dict:
    """Only portable legacy bridge inputs; never edit a candidate Agent profile."""
    from preview30_compatibility import build_template
    template, contract = build_template(load(BASE / "ontology/ontology-full-definition-template.json"))
    root = PREVIEW / "ontology/agent-compat"
    save(root / "definition-template.json", template)
    save(root / "contract.json", contract)
    return {"expectedGeneration": 1, **contract["counts"], "deployed": False,
            "implicitFallback": False, "agentConfigurationChanged": False}


V3_FACT_DESCRIPTIONS = (
    ("/// 静的seed寄附と重複排除済み増分イベントを統合した1寄附1行のファクト。金額・件数・時系列分析の基点です。",
     "/// 静的データ（配布した寄付データ全体）と、品質処理で重複を除いた受入済みの増分を合わせた、1寄付1行のファクトです。金額・件数・時系列分析の基点です。"),
    ("\t/// 現在のフィルター条件に含まれる寄附件数。静的seedと重複排除済み増分イベントを含みます。",
     "\t/// 現在のフィルター条件に含まれる寄附件数です。静的データと、重複を除いた受入済みの増分を含みます。"),
    ("\t/// StaticSeedまたはRealtimeIncrement。静的スナップショットと増分イベントを区別します。",
     "\t/// StaticSeed（静的データ）または RealtimeIncrement（受入済みの増分）。データの種類を区別します。"),
)


def build() -> dict:
    baseline = immutable_baseline()
    # No recursive destination delete/copy: attachments is another workstream's.
    for folder in ("data", "kql", "powerbi"):
        for path in sorted((BASE / folder).rglob("*")):
            if path.is_file():
                write(PREVIEW / path.relative_to(BASE), path.read_bytes())
    fact_path = PREVIEW / "powerbi/Furusato_Analytics.SemanticModel/definition/tables/寄附.tmdl"
    fact = fact_path.read_text(encoding="utf-8")
    native_metrics = [
        ("静的寄附総額", 'CALCULATE([寄附総額], KEEPFILTERS(\'寄附\'[データソース] = "StaticSeed"))',
         "¥#,##0", "静的データ（StaticSeed）の寄附だけを集計します。Eventhouse の観測データや受入済みの増分は含めません。"),
        ("静的寄附件数", 'CALCULATE([寄附件数], KEEPFILTERS(\'寄附\'[データソース] = "StaticSeed"))',
         "#,##0", "静的データ（StaticSeed）の寄附件数です。現在のディメンションのフィルターを保ちます。"),
        ("受入増分寄附総額", 'CALCULATE([寄附総額], KEEPFILTERS(\'寄附\'[データソース] = "RealtimeIncrement"))',
         "¥#,##0", "Notebook05 で品質を確認し、重複を除いた受入済みの増分（RealtimeIncrement）だけを集計します。Eventhouse の観測データ（重複を含む）とは別です。"),
        ("受入増分寄附件数", 'CALCULATE([寄附件数], KEEPFILTERS(\'寄附\'[データソース] = "RealtimeIncrement"))',
         "#,##0", "Notebook05 で品質を確認し、重複を除いた受入済みの増分（RealtimeIncrement）の件数です。"),
    ]
    # Plain wording for descriptions inherited from the immutable 2.7.0 model (v3 copy only).
    for old, new in V3_FACT_DESCRIPTIONS:
        if fact.count(old) != 1:
            raise ValueError("Expected one inherited description to reword: " + old)
        fact = fact.replace(old, new)
    measure_text = ""
    for name, dax, fmt, text in native_metrics:
        measure_text += (f"\t/// {text}\n\tmeasure {name} = {dax}\n"
                         f"\t\tformatString: {fmt}\n\t\tdisplayFolder: Metrics検証\n\n")
    insertion = fact.index("\n\t///")
    fact = fact[:insertion] + "\n\n" + measure_text + fact[insertion:]
    # The amount is a participant-facing filter; expose only this column.
    # This does not certify the Data Agent's independently cached native schema.
    amount = "\tcolumn 寄附金額\n\t\tdataType: int64\n\t\tisHidden\n"
    if fact.count(amount) != 1:
        raise ValueError("Expected exactly one inherited amount visibility declaration")
    fact = fact.replace(amount, "\tcolumn 寄附金額\n\t\tdataType: int64\n")
    write(fact_path, fact.encode("utf-8"))
    save(PREVIEW / "powerbi" / "native-metrics-contract.json", {
        "source": "Furusato_Analytics.SemanticModel",
        "storageMode": "DirectLake", "factSource": "gold.donations",
        "dimensionSources": ["gold.donor", "gold.municipality", "gold.gift", "gold.date"],
        "measures": [{"table": "寄附", "name": name, "dax": dax, "formatString": fmt}
                     for name, dax, fmt, _ in native_metrics],
        "sourceOwnsDax": True, "ontologyProjection": "native-ui-required",
        "dataAgentRequiresDirectSemanticModelSource": True,
        "validationState": "offline-only-not-executed",
    })
    for number in ("01", "05"):
        path = next((BASE / "notebooks").glob(f"Notebook_{number}_*.ipynb"))
        notebook = load(path)
        notebook["metadata"].setdefault("furusato", {}).update({
            "edition": "v" + WORKSHOP_VERSION, "version": WORKSHOP_VERSION,
            "runtimeProfile": "v3.0.0-preview", "sourceRuntimeEdition": "2.7.0",
            "dataContract": "2.7.0-realistic.1", "dataContractPreserved": True,
        })
        notebook["cells"][0]["source"] = [
            "# Furusato Workshop " + WORKSHOP_VERSION + " — " + path.stem + "\n", "\n",
            "**Workshop version / 教材版:** " + WORKSHOP_VERSION + "\n",
            "**Runtime profile / 技術的な配置識別子:** v3.0.0-preview\n",
            "**Compatible processing baseline / 処理基線:** 2.7.0. The data-processing algorithm is preserved.\n",
            "**Data contract / 不変のデータ仕様:** 2.7.0-realistic.1. CSV values and publication keys are unchanged.\n",
            "**Input boundary:** Lakehouse static/staging tables and released CSV files; never Eventhouse-to-Gold.\n",
            "**Deployment:** the specified folder directly; no Temp folder is required for production.\n",
        ]
        if number == "01":
            parameters = [cell for cell in notebook["cells"]
                          if "parameters" in cell.get("metadata", {}).get("tags", [])]
            if len(parameters) != 1 or parameters[0]["source"].count('NOTEBOOK_VERSION = "2.7.0"\n') != 1:
                raise ValueError("Expected one presentation/audit version assignment in Notebook01.")
            parameters[0]["source"] = [
                f'NOTEBOOK_VERSION = "{WORKSHOP_VERSION}"\n' if line == 'NOTEBOOK_VERSION = "2.7.0"\n' else line
                for line in parameters[0]["source"]
            ]
        write(PREVIEW / "notebooks" / path.name,
              (json.dumps(notebook, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))
        if number == "05":
            runtime_tree = ast.parse("".join(notebook["cells"][3]["source"]))
            outputs = next(ast.literal_eval(n.value) for n in runtime_tree.body
                           if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "OUTPUT_TABLES" for t in n.targets))
            save(PREVIEW / "provisioning/gold-contract.json", {
                "outputTables": outputs, "generationColumn": "_AnalyticsGenerationId",
                "controlTable": "ops.analytics_publish_control", "readyState": "Ready",
                "inputs": ["Lakehouse static/staging tables", "Files/increment/*.csv"],
                "eventhouseToGold": False,
            })
    original = load(BASE / "ontology" / "ontology-full-definition-template.json")
    tmdl, contract = generate(original)
    for path, text in tmdl.items():
        write(PREVIEW / "ontology" / "definition" / path, text.encode("utf-8"))
    save(PREVIEW / "ontology" / "generation2-contract.json", contract)
    build_relationships()
    build_agent_compatibility()
    from preview30_agent import build_profile
    agent_files, agent_contract = build_profile()
    for path, content in agent_files.items():
        save(PREVIEW / "data-agent/definition" / path, content)
    save(PREVIEW / "data-agent/candidate-contract.json", agent_contract)
    save(PREVIEW / "provisioning" / "preview-contract.json", {
        "edition": "v3.0.0-preview", "workshopVersion": WORKSHOP_VERSION, "baselineEdition": "2.7.0",
        "baselineTreeSha256": baseline["treeSha256"],
        "dataContract": {k: v for k, v in baseline.items() if k not in {"files", "treeSha256"}},
        "generation2": True, "legacyFallback": False,
        "ontologyContract": "../ontology/generation2-contract.json",
        "environmentParameterRequired": ["dev", "test", "prod"],
        "privateEvidenceRequired": True, "cloudStatus": "not-deployed-by-build",
        "productionPlacement": "specified-folder-direct", "createTempByDefault": False,
        "correctedAgentProfile": "data-agent/candidates/measured-contract-20261009",
        "attachmentsOwner": "documents-workstream",
    })
    from preview30_notebooks import build_notebooks
    notebook_manifest = build_notebooks()
    save(PREVIEW / "provisioning/notebook-bundle-manifest.json", notebook_manifest)
    immutable_baseline()
    return {"edition": "v3.0.0-preview", "tmdlParts": len(tmdl),
            "dataPreserved": True, "attachmentsPreserved": True,
            "timeSeriesBinding": contract["timeSeriesBinding"]["status"],
            "nativeMetrics": contract["nativeMetrics"]["status"]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--relationships-only", action="store_true",
                       help="Build only the opt-in static companion TMDL and contract.")
    group.add_argument("--agent-compat-only", action="store_true",
                       help="Build only the explicit generation1 consumer-bridge inputs.")
    args = parser.parse_args()
    action = build_relationships if args.relationships_only else build_agent_compatibility if args.agent_compat_only else build
    print(json.dumps(action(),
                     ensure_ascii=False, indent=2))
