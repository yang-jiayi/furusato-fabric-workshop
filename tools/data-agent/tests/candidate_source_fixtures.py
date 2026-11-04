"""Build deterministic candidate tests from the compiler's introduction inputs."""
import hashlib
import json
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

import current_profile as current
from source_grounded_profile import inline_part
from test_current_profile import AGENT, WORKSPACE


FIXTURE = Path(__file__).resolve().parent / "fixtures" / "candidate-source-profile-v1"
SOURCE_KINDS = ("kusto", "lakehouse_tables", "ontology", "semantic_model")


def agent_fixture():
    manifest = json.loads((FIXTURE / "fixture-manifest.json").read_bytes())
    if manifest.get("schemaVersion") != 1 or manifest.get("purpose", "").find("test-only") < 0:
        raise ValueError("Unknown candidate source fixture.")
    if set(manifest.get("sha256", {})) != {
            "definition/" + name for name in (
                "stage_config.json", "kusto.json", "lakehouse_tables.json",
                "ontology.json", "semantic_model.json")}:
        raise ValueError("Incomplete candidate source fixture manifest.")
    for path, digest in manifest["sha256"].items():
        if hashlib.sha256((FIXTURE / path).read_bytes()).hexdigest() != digest:
            raise ValueError("Candidate source fixture drift: " + path)

    stage = json.loads((FIXTURE / "definition/stage_config.json").read_bytes())
    templates = {
        kind: json.loads((FIXTURE / ("definition/" + kind + ".json")).read_bytes())
        for kind in SOURCE_KINDS
    }
    identities = {"{{workspace:id}}": WORKSPACE}
    for kind, source in templates.items():
        identities["{{resource:" + kind + ":id}}"] = str(uuid5(NAMESPACE_URL, "candidate-source-v1/" + kind))
        identities["{{resource:" + kind + ":name}}"] = "Participant_" + kind
        for path, _ in current.native.walk(source["elements"]):
            token = current.node_token(kind, path)
            identities[token] = str(uuid5(NAMESPACE_URL, token))

    parts = [
        inline_part("Files/Config/data_agent.json", {"shared": "keep"}),
        inline_part(".platform", {"identity": AGENT}),
    ]
    for status in ("draft", "published"):
        prefix = "Files/Config/" + status + "/"
        parts.append(inline_part(prefix + "stage_config.json", stage))
        for kind, template in templates.items():
            source = current.substitute(template, identities)
            dirname = ("ontologies/" if kind == "ontology" else kind + "-") + source["displayName"]
            suffix = "/ontology.json" if kind == "ontology" else "/datasource.json"
            parts.append(inline_part(prefix + dirname + suffix, source))
    return {"parts": parts}
