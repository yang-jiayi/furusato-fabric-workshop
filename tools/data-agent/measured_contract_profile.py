"""Compile a versioned measured contract from actual workshop metadata.

This pure compiler does not authenticate, query, stage or publish. Native SQL/KQL
selection nodes must already exist in the supplied service definition. Missing
objects require service discovery; their IDs and types are never manufactured.
Both historical four-datasource definitions and native Gen2 definitions with
three datasources plus a separate ontology context are supported. Native context
payloads are retained exactly; legacy Ontology instruction fields are not added.
The caller owns source verification, publication/readback and a new evaluation.
"""
from __future__ import annotations

import argparse
import base64
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import uuid

from source_grounded_profile import decoded_parts, inline_part
from standard_contract_restoration import _answer_values_in

REPO = Path(__file__).resolve().parents[2]
CURRENT_PROFILE = "measured-contract-20261015"
SUPPORTED_PROFILES = (CURRENT_PROFILE, "measured-contract-20261009")
PROFILE_ROOT = REPO / "workshop/v3.0.0-preview/data-agent/candidates"
PROFILE = PROFILE_ROOT / CURRENT_PROFILE
LIMIT = 10000
KINDS = {"lakehouse_tables", "kusto", "semantic_model", "ontology"}
DIRECT_KINDS = KINDS - {"ontology"}
ONTOLOGY_SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item/dataAgent/definition/ontology/1.0.0/schema.json"
FILES = {"lakehouse_tables": "lakehouse-instructions.txt", "kusto": "kusto-instructions.txt",
         "semantic_model": "semantic-model-instructions.txt", "ontology": "ontology-instructions.txt"}
MEASURES = {
    "寄附件数": "COUNTROWS('寄附')",
    "寄附総額": "SUM('寄附'[寄附金額])",
    "静的寄附件数": 'CALCULATE([寄附件数], KEEPFILTERS(\'寄附\'[データソース] = "StaticSeed"))',
    "静的寄附総額": 'CALCULATE([寄附総額], KEEPFILTERS(\'寄附\'[データソース] = "StaticSeed"))',
    "受入増分寄附件数": 'CALCULATE([寄附件数], KEEPFILTERS(\'寄附\'[データソース] = "RealtimeIncrement"))',
    "受入増分寄附総額": 'CALCULATE([寄附総額], KEEPFILTERS(\'寄附\'[データソース] = "RealtimeIncrement"))',
    "平均寄附額": "DIVIDE([寄附総額], [寄附件数])",
    "寄附総額 前年同期間": "CALCULATE([寄附総額], SAMEPERIODLASTYEAR('日付'[日付]))",
    "自治体別シェア (%)": "DIVIDE([寄附総額], CALCULATE([寄附総額], REMOVEFILTERS('自治体')))",
    "高額寄附件数": "CALCULATE([寄附件数], KEEPFILTERS('寄附'[高額寄附フラグ] = TRUE()))",
}
FEWSHOT_SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item/dataAgent/definition/fewShots/1.0.0/schema.json"


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(",", ":")).encode()).hexdigest()


def stage_sources(definition, input_stage):
    """Read four logical bindings from either observed definition serialization.

    Native ``ontology.json`` does not define ``type``, source instructions or a
    source description. Its existing selections and authored entity descriptions
    must be preserved, not converted into a legacy datasource. Unknown/mixed
    serializations require a new service readback and explicit reconciliation.
    This parser does not establish service availability or answer correctness.
    """
    if input_stage not in {"draft", "published"}:
        raise ValueError("Choose the actual input stage explicitly.")
    docs = decoded_parts(definition)
    prefix = "Files/Config/" + input_stage + "/"
    entries = [(path, value) for path, value in docs.items()
               if path.startswith(prefix) and path.endswith("/datasource.json")]
    contexts = [(path, value) for path, value in docs.items()
                if path.startswith(prefix) and path.endswith("/ontology.json")]
    if not all(isinstance(value, dict) for _, value in entries + contexts):
        raise ValueError("Actual source definition parts must contain objects.")
    if any(not isinstance(value.get("type"), str) for _, value in entries):
        raise ValueError("Actual datasource types must be strings.")
    sources = {value.get("type"): (path, value) for path, value in entries}
    if len(entries) == 4 and set(sources) == KINDS and not contexts:
        return docs, sources, "legacy-datasources"
    if len(entries) != 3 or set(sources) != DIRECT_KINDS or len(contexts) != 1:
        raise ValueError("Require four legacy datasources or three direct datasources and one native Ontology context.")
    path, context = contexts[0]
    fields = {"$schema", "workspaceId", "artifactId", "displayName", "elements",
              "entitiesWithUserAuthoredDescriptions"}
    name = context.get("displayName")
    if (set(context) != fields or context.get("$schema") != ONTOLOGY_SCHEMA
            or not isinstance(name, str) or not name or "/" in name or "\\" in name
            or path != prefix + "ontologies/" + name + "/ontology.json"
            or not isinstance(context.get("elements"), list) or not context["elements"]
            or not isinstance(context.get("entitiesWithUserAuthoredDescriptions"), list)):
        raise ValueError("Unknown native Ontology context schema, fields, path or selections; reconcile actual service shape first.")
    sources["ontology"] = contexts[0]
    return docs, sources, "native-ontology-context"


def walk(nodes, path=()):
    if not isinstance(nodes, list):
        raise ValueError("Native element children must be arrays.")
    for node in nodes:
        if not isinstance(node, dict) or not isinstance(node.get("display_name"), str):
            raise ValueError("Native elements require their observed display_name.")
        current = path + (node["display_name"],)
        yield current, node
        yield from walk(node.get("children", []), current)


def profile_inputs(profile=PROFILE):
    manifest = json.loads((profile / "profile-manifest.json").read_bytes())
    if (manifest.get("schemaVersion") != 1 or manifest.get("instructionLimitUtf16Units") != LIMIT
            or manifest.get("profile") not in SUPPORTED_PROFILES):
        raise ValueError("Unknown measured-contract manifest.")
    expected = {"global-instructions.txt", *FILES.values(), "source-descriptions.json",
                "selection-contract.json", "kusto-examples.json"}
    if set(manifest.get("sha256", {})) != expected:
        raise ValueError("The manifest must bind every compiler input.")
    for name, expected_hash in manifest["sha256"].items():
        raw = (profile / name).read_bytes()
        if hashlib.sha256(raw).hexdigest() != expected_hash:
            raise ValueError("Measured-contract input drift: " + name)
        text = raw.decode("utf-8")
        # Inspect decoded values so JSON Unicode escapes cannot hide a case ID,
        # benchmark value or live identity from the publication guard.
        if name.endswith(".json"):
            text = json.dumps(json.loads(text), ensure_ascii=False)
        if _answer_values_in(text) or re.search(r"\b[TBHQ][0-9]{2}\b|[0-9a-f]{8}-[0-9a-f-]{27,}", text, re.I):
            raise ValueError("Profile assets must not contain benchmark answers, case IDs or live identities.")
    instructions = {"global": (profile / "global-instructions.txt").read_text(encoding="utf-8").strip()}
    instructions.update({kind: (profile / name).read_text(encoding="utf-8").strip()
                         for kind, name in FILES.items()})
    if any(not text or len(text.encode("utf-16-le")) // 2 > LIMIT for text in instructions.values()):
        raise ValueError("Every instruction section must fit 10,000 UTF16 units.")
    descriptions = json.loads((profile / "source-descriptions.json").read_bytes())
    selections = json.loads((profile / "selection-contract.json").read_bytes())
    examples = json.loads((profile / "kusto-examples.json").read_bytes())["examples"]
    if (set(descriptions) != KINDS or not all(isinstance(v, str) and v.strip() for v in descriptions.values())
            or selections.get("schemaVersion") != 1):
        raise ValueError("Invalid source description/selection contract.")
    if set(selections.get("sources", {})) != {"lakehouse_tables", "kusto"}:
        raise ValueError("Only SQL/KQL selections may be aligned.")
    if len(examples) != 9 or len({row.get("question") for row in examples}) != 9:
        raise ValueError("Exactly nine distinct source-owned KQL examples are required.")
    for row in examples:
        if set(row) != {"question", "query"} or not all(isinstance(v, str) and v.strip() for v in row.values()):
            raise ValueError("Malformed KQL example.")
    return instructions, descriptions, selections["sources"], examples, manifest


def source_model_contract(native_model):
    """Read every existing workshop measure and the visible amount column."""
    model = native_model.get("definition", native_model)
    if model.get("format") != "TMDL" or not isinstance(model.get("parts"), list):
        raise ValueError("Actual Semantic Model TMDL readback is required.")
    found, amount, paths = {}, [], set()
    for part in model["parts"]:
        path = part.get("path")
        if not isinstance(path, str) or path in paths or part.get("payloadType") != "InlineBase64":
            raise ValueError("TMDL requires unique paths and actual InlineBase64 payloads.")
        paths.add(path)
        text = base64.b64decode(part["payload"], validate=True).decode("utf-8")
        if not path.startswith("definition/tables/") or not path.endswith(".tmdl"):
            continue
        for name, expected in MEASURES.items():
            for match in re.finditer(r"^\tmeasure '?" + re.escape(name) + r"'? = (.+)$", text, re.M):
                if name in found or match.group(1).strip() != expected:
                    raise ValueError("Source-owned workshop measure differs or is duplicated: " + name)
                found[name] = match.group(1).strip()
        if re.search(r"^table '?寄附'?\s*$", text, re.M):
            amount.extend(re.findall(r"^\tcolumn '?寄附金額'?\s*\n((?:\t\t[^\n]*\n|\s*\n)*)", text, re.M))
    if found != MEASURES or len(amount) != 1:
        raise ValueError("All ten unique existing measures and the actual donation amount column are required.")
    if re.search(r"^\t\tisHidden(?:\s*:\s*true)?\s*$", amount[0], re.M):
        raise ValueError("The measured contract requires 寄附金額 to be visible in the actual model.")
    return found


def sql_metadata(rows):
    if not isinstance(rows, list) or not rows:
        raise ValueError("Independent INFORMATION_SCHEMA.COLUMNS results are required.")
    columns = {}
    for row in rows:
        keys = ("TABLE_SCHEMA", "TABLE_NAME", "COLUMN_NAME", "DATA_TYPE")
        if not isinstance(row, dict) or not all(isinstance(row.get(k), str) and row[k] for k in keys):
            raise ValueError("SQL metadata requires schema, object, column and native type.")
        key = tuple(row[k] for k in keys[:3])
        if key in columns:
            raise ValueError("Duplicate independent SQL metadata column.")
        columns[key] = row["DATA_TYPE"]
    return columns


def verify_ontology_item(item, source):
    """Verify actual generation evidence without relabeling a public item.

    The measured service lists Gen2 items as public type ``Ontology``. Its actual
    native metadata identifies FeatureLevel=2 and the two managed child roles.
    A plain public Ontology row alone cannot establish that generation.
    """
    if item.get("type") == "Gen2Ontology":
        if item.get("id") != source["artifactId"] or ("workspaceId" in item and item["workspaceId"] != source["workspaceId"]):
            raise ValueError("Generation-specific Ontology metadata is bound to a different source.")
        return
    properties = item.get("extendedProperties", {})
    if (item.get("objectId") != source["artifactId"] or item.get("artifactType") != "Ontology"
            or not isinstance(properties, dict) or properties.get("FeatureLevel") != 2):
        raise ValueError("Actual bound Ontology generation-2 feature-level metadata is required; a public Ontology label alone is insufficient.")
    children = properties.get("ChildItems")
    if not isinstance(children, str):
        raise ValueError("Actual Gen2 managed child metadata is missing.")
    children = json.loads(children)
    if not isinstance(children, dict) or set(children) != {"GraphInstance", "OntologyEventhouse"}:
        raise ValueError("Unknown Gen2 managed child roles.")
    if not all(isinstance(value, str) and str(uuid.UUID(value)) == value.lower() for value in children.values()):
        raise ValueError("Gen2 managed child identities must be real GUIDs.")


def align_selection(source, contract, sql_columns=None):
    """Align only observed native nodes, checking IDs, paths and source types."""
    current = list(walk(source["elements"]))
    nodes = {}
    for path, node in current:
        identity = node.get("id")
        if path in nodes or not isinstance(identity, str) or not identity:
            raise ValueError("Ambiguous native element path or missing observed ID.")
        nodes[path] = node
    expected = {}
    selected_ids = set()
    for item in contract:
        path = tuple(item["path"])
        if path in expected or path not in nodes:
            raise ValueError("Required object is missing/ambiguous; refresh native service schema: " + "/".join(path))
        node = nodes[path]
        # Native exports can reuse a grouping ID across different node kinds.
        # The admitted objects/columns still require unique kind/ID identities.
        identity = (node.get("type"), node["id"])
        if identity in selected_ids:
            raise ValueError("Duplicate observed selected element kind/ID.")
        selected_ids.add(identity)
        if node.get("type") != item["type"] or ("dataType" in item and node.get("data_type") != item["dataType"]):
            raise ValueError("Native element kind/type differs from measured contract: " + "/".join(path))
        if item["type"] == "lakehouse_tables.column":
            key = (path[1], path[-2], path[-1])
            if sql_columns.get(key) != node.get("data_type"):
                raise ValueError("Native SQL column differs from independent metadata: " + ".".join(key))
        expected[path] = item
    changed = []
    for path, node in current:
        selected = path in expected
        if node.get("is_selected") is not selected:
            changed.append({"path": list(path), "selected": selected})
        node["is_selected"] = selected
        if selected and "description" in expected[path]:
            node["description"] = expected[path]["description"]
    return changed


def compile_measured_draft(original, *, input_stage, sql_columns, native_model, ontology_item, profile=PROFILE):
    """Return Draft plus unchanged Published parts; no external side effects."""
    docs, sources, serialization = stage_sources(original, input_stage)
    native_context = serialization == "native-ontology-context"
    prefix = "Files/Config/" + input_stage + "/"
    stage_path = prefix + "stage_config.json"
    if stage_path not in docs or "Files/Config/data_agent.json" not in docs:
        raise ValueError("A complete actual stage and shared agent configuration are required.")
    workspaces, artifacts = set(), set()
    for _, source in sources.values():
        for key in ("workspaceId", "artifactId"):
            value = source.get(key)
            if not isinstance(value, str) or str(uuid.UUID(value)) != value.lower():
                raise ValueError("Real source workspace/item GUIDs are required.")
        workspaces.add(source["workspaceId"])
        artifacts.add(source["artifactId"])
    if len(workspaces) != 1 or len(artifacts) != 4:
        raise ValueError("Four distinct workshop sources in the same actual workspace are required.")
    ontology = sources["ontology"][1]
    verify_ontology_item(ontology_item, ontology)
    if docs[stage_path].get("experimental", {}).get("codeInterpreterEnabled") is not True:
        raise ValueError("Enable Code Interpreter in the actual stage before compiling this contract.")
    allowed_paths = {stage_path, *(p for p, _ in sources.values()), *(p.removesuffix("datasource.json") + "fewshots.json"
                    for kind, (p, _) in sources.items() if kind in {"lakehouse_tables", "kusto"})}
    if any(p.startswith(prefix) and p not in allowed_paths for p in docs):
        raise ValueError("Extra stage topics/examples require explicit reconciliation before using this profile.")
    source_model_contract(native_model)
    model_nodes = list(walk(sources["semantic_model"][1].get("elements", [])))
    for name in ("寄附金額", *MEASURES):
        matches = [n for path, n in model_nodes if len(path) >= 2 and path[-2:] == ("寄附", name)]
        kind = "semantic_model.column" if name == "寄附金額" else "semantic_model.measure"
        if (len(matches) != 1 or matches[0].get("is_selected") is not True or matches[0].get("type") != kind
                or not isinstance(matches[0].get("id"), str) or not matches[0]["id"]):
            raise ValueError("The actual native model amount/all ten measures must be selected with observed IDs/kinds: " + name)
    instructions, descriptions, selections, examples, manifest = profile_inputs(profile)
    wanted = copy.deepcopy(docs)
    # Derive Draft exclusively from the explicitly selected input stage. Published
    # payloads, agent identity and service metadata in the input remain untouched.
    for path in list(wanted):
        if path.startswith("Files/Config/draft/"):
            del wanted[path]
    for path, value in docs.items():
        if path.startswith(prefix):
            wanted[path.replace(prefix, "Files/Config/draft/", 1)] = copy.deepcopy(value)
    draft_stage = "Files/Config/draft/stage_config.json"
    wanted[draft_stage]["aiInstructions"] = instructions["global"]
    selection_changes = {}
    metadata = sql_metadata(sql_columns)
    for kind, (path, source) in sources.items():
        draft_path = path.replace(prefix, "Files/Config/draft/", 1)
        target = wanted[draft_path]
        if native_context and kind == "ontology":
            if target != source:
                raise ValueError("Native Ontology context changed unexpectedly.")
            continue
        target["dataSourceInstructions"] = instructions[kind]
        target["userDescription"] = descriptions[kind]
        if kind in selections:
            selection_changes[kind] = align_selection(target, selections[kind], metadata)
        else:
            if target["elements"] != source["elements"]:
                raise ValueError("Ontology/model selection changed unexpectedly.")
    # The measured native publication excludes the 17 SQL examples whose staging
    # validations failed. Keep them in historical candidate folders, not active
    # fewshots. No source execution success is inferred from these local templates.
    for path in list(wanted):
        if path.startswith("Files/Config/draft/") and path.endswith("/fewshots.json"):
            del wanted[path]
    kusto_path = sources["kusto"][0].replace(prefix, "Files/Config/draft/", 1)
    fewshot_path = kusto_path.removesuffix("datasource.json") + "fewshots.json"
    wanted[fewshot_path] = {"$schema": FEWSHOT_SCHEMA, "fewShots": [
        {"id": str(uuid.uuid5(uuid.NAMESPACE_URL, "furusato-measured-contract:" + row["question"])), **row}
        for row in examples]}
    # Keep every non-Draft part byte-identical, including actual Published evidence.
    original_parts = original.get("definition", original)["parts"]
    parts = [copy.deepcopy(part) for part in original_parts
             if not part["path"].startswith("Files/Config/draft/")]
    ontology_path = sources["ontology"][0]
    draft_ontology_path = ontology_path.replace(prefix, "Files/Config/draft/", 1)
    for path, value in sorted(wanted.items()):
        if not path.startswith("Files/Config/draft/"):
            continue
        if native_context and path == draft_ontology_path:
            # Copy the actual payload bytes and any service part metadata, even
            # when Published is the explicit input and only its path changes.
            part = copy.deepcopy(next(p for p in original_parts if p["path"] == ontology_path))
            part["path"] = path
            parts.append(part)
        else:
            parts.append(inline_part(path, value))
    result = {"parts": parts}
    before = {p: v for p, v in docs.items() if not p.startswith("Files/Config/draft/")}
    after = {p: v for p, v in decoded_parts(result).items() if not p.startswith("Files/Config/draft/")}
    if before != after:
        raise ValueError("A non-Draft definition part changed.")
    applied_instructions = {key: text for key, text in instructions.items()
                            if not native_context or key != "ontology"}
    receipt = {
        "profile": manifest["profile"], "inputStage": input_stage,
        "inputDefinitionSha256": digest(original), "outputDefinitionSha256": digest(result),
        "profileManifestSha256": digest(manifest), "inputModelDefinitionSha256": digest(native_model),
        "inputSqlColumnsSha256": digest(sql_columns), "inputOntologyMetadataSha256": digest(ontology_item),
        "instructionUtf16Units": {key: len(text.encode("utf-16-le")) // 2 for key, text in applied_instructions.items()},
        "instructionLimitUtf16Units": LIMIT, "sourceOwnedCountMeasuresVerified": True,
        "sourceOwnedWorkshopMeasuresVerified": 10,
        "modelAmountVisible": True, "sourceIdentitiesPreserved": True, "ontologyCount": 1,
        "ontologyGeneration": 2, "ontologyAndModelSelectionsPreserved": True,
        "sqlKqlSelectionChanges": selection_changes, "codeInterpreterPreserved": True,
        "publishedPartsPreservedByteIdentical": True, "activeSqlExamples": 0, "activeKqlExamples": 9,
        "businessDataAndMeasuresChanged": False, "cloudCalls": 0, "stagedOrPublished": False,
        "freshDeploymentOrAnswerAccuracyVerified": False,
        "sourceSerialization": serialization, "logicalBindingCount": 4,
        "physicalDatasourceCount": 3 if native_context else 4,
    }
    if native_context:
        receipt.update({
            "nativeOntologyPart": draft_ontology_path,
            "nativeOntologyPartPreservedByteIdentical": True,
            "nativeOntologySchema": ONTOLOGY_SCHEMA,
            "unchangedPortableInstructions": ["global", *sorted(DIRECT_KINDS)],
            "unsupportedLegacyOntologyInstructionSha256": digest(instructions["ontology"]),
            "unsupportedLegacyOntologyDescriptionSha256": digest(descriptions["ontology"]),
            "legacyOntologyInstructionsInsertedIntoGlobal": False,
            "legacyOntologyFieldsSynthesized": False,
        })
    return result, receipt


def reject_links(path):
    for candidate in (Path(path), *Path(path).parents):
        try:
            attributes = candidate.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(attributes.st_mode) or (
            getattr(attributes, "st_file_attributes", 0)
            & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
        ):
            raise ValueError("Private output paths may not traverse links or reparse points.")


def _windows_create(path):
    import ctypes
    from ctypes import wintypes as w
    import msvcrt

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    security = ctypes.WinDLL("advapi32", use_last_error=True)

    def api(library, name, args, result):
        function = getattr(library, name)
        function.argtypes, function.restype = args, result
        return function

    close = api(kernel, "CloseHandle", [w.HANDLE], w.BOOL)
    free = api(kernel, "LocalFree", [w.HLOCAL], w.HLOCAL)
    process = api(kernel, "GetCurrentProcess", [], w.HANDLE)
    token_open = api(security, "OpenProcessToken", [w.HANDLE, w.DWORD, ctypes.POINTER(w.HANDLE)], w.BOOL)
    token_info = api(security, "GetTokenInformation",
                     [w.HANDLE, ctypes.c_int, w.LPVOID, w.DWORD, ctypes.POINTER(w.DWORD)], w.BOOL)
    sid_string = api(security, "ConvertSidToStringSidW", [w.LPVOID, ctypes.POINTER(w.LPWSTR)], w.BOOL)
    from_sddl = api(security, "ConvertStringSecurityDescriptorToSecurityDescriptorW",
                    [w.LPCWSTR, w.DWORD, ctypes.POINTER(w.LPVOID), ctypes.POINTER(w.DWORD)], w.BOOL)
    to_sddl = api(security, "ConvertSecurityDescriptorToStringSecurityDescriptorW",
                  [w.LPVOID, w.DWORD, w.DWORD, ctypes.POINTER(w.LPWSTR), ctypes.POINTER(w.DWORD)], w.BOOL)
    get_security = api(security, "GetSecurityInfo",
                       [w.HANDLE, ctypes.c_int, w.DWORD, w.LPVOID, w.LPVOID,
                        ctypes.POINTER(w.LPVOID), w.LPVOID, ctypes.POINTER(w.LPVOID)], w.DWORD)

    class Attributes(ctypes.Structure):
        _fields_ = [("length", w.DWORD), ("descriptor", w.LPVOID), ("inherit", w.BOOL)]

    create = api(kernel, "CreateFileW",
                 [w.LPCWSTR, w.DWORD, w.DWORD, ctypes.POINTER(Attributes), w.DWORD, w.DWORD, w.HANDLE], w.HANDLE)

    def checked(value):
        if not value:
            raise ctypes.WinError(ctypes.get_last_error())
        return value

    def descriptor_text(descriptor):
        text = w.LPWSTR()
        checked(to_sddl(descriptor, 1, 4, ctypes.byref(text), None))
        try:
            return text.value
        finally:
            free(ctypes.cast(text, w.HLOCAL))

    token = w.HANDLE()
    checked(token_open(process(), 0x0008, ctypes.byref(token)))  # TOKEN_QUERY
    try:
        size = w.DWORD()
        token_info(token, 1, None, 0, ctypes.byref(size))  # TokenUser
        if ctypes.get_last_error() != 122:
            raise ctypes.WinError(ctypes.get_last_error())
        buffer = ctypes.create_string_buffer(size.value)
        checked(token_info(token, 1, buffer, size, ctypes.byref(size)))
        sid = ctypes.cast(buffer, ctypes.POINTER(w.LPVOID))[0]
        text = w.LPWSTR()
        checked(sid_string(sid, ctypes.byref(text)))
        try:
            sddl = "D:P(A;;FA;;;" + text.value + ")"
        finally:
            free(ctypes.cast(text, w.HLOCAL))
    finally:
        close(token)

    descriptor = w.LPVOID()
    checked(from_sddl(sddl, 1, ctypes.byref(descriptor), None))
    try:
        expected_dacl = descriptor_text(descriptor)
        attributes = Attributes(ctypes.sizeof(Attributes), descriptor, False)
        # CREATE_NEW applies the protected DACL atomically, before any content exists.
        handle = create(str(path), 0x40000000 | 0x00020000, 0, ctypes.byref(attributes), 1, 0x80, None)
        create_error = ctypes.get_last_error()
    finally:
        free(descriptor)
    if handle == w.HANDLE(-1).value:
        error = create_error
        if error in (80, 183):
            raise FileExistsError(error, "Private output already exists", str(path))
        raise ctypes.WinError(error)
    try:
        actual = w.LPVOID()
        dacl = w.LPVOID()
        error = get_security(handle, 1, 4, None, None, ctypes.byref(dacl), None, ctypes.byref(actual))
        if error:
            raise ctypes.WinError(error)
        try:
            if descriptor_text(actual) != expected_dacl:
                raise PermissionError("The filesystem did not preserve the current-user-only protected DACL.")
        finally:
            free(actual)
        fd = msvcrt.open_osfhandle(handle, os.O_WRONLY)
    except BaseException:
        close(handle)
        raise
    return fd


def private_text(path):
    """Create exclusively with POSIX0600 or a verified current-user-only Windows DACL."""
    path = Path(path)
    reject_links(path)
    fd = (_windows_create(path) if os.name == "nt" else
          os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600))
    try:
        return os.fdopen(fd, "w", encoding="utf-8")
    except BaseException:
        os.close(fd)
        raise


def private_path(path):
    if not path.is_absolute() or path.is_symlink():
        raise ValueError("Use absolute private output paths outside Git.")
    reject_links(path)
    resolved = path.resolve()
    if resolved == REPO or REPO in resolved.parents or any((parent / ".git").exists() for parent in resolved.parents):
        raise ValueError("Actual definitions and receipts must remain outside Git checkouts.")
    if path.exists():
        raise ValueError("Use fresh outputs; do not overwrite prior definitions/evidence.")
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=SUPPORTED_PROFILES, default=CURRENT_PROFILE,
                        help="Versioned portable instructions; the historical profile remains explicitly available.")
    parser.add_argument("--definition", type=Path, required=True)
    parser.add_argument("--input-stage", choices=("draft", "published"), required=True)
    parser.add_argument("--sql-columns", type=Path, required=True)
    parser.add_argument("--model-definition", type=Path, required=True)
    parser.add_argument("--ontology-item", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    out, receipt_path = private_path(args.output), private_path(args.receipt)
    if out.resolve() == receipt_path.resolve():
        raise ValueError("Definition and receipt require different paths.")
    read = lambda path: json.loads(path.read_text(encoding="utf-8-sig"))
    definition, receipt = compile_measured_draft(read(args.definition), input_stage=args.input_stage,
        sql_columns=read(args.sql_columns), native_model=read(args.model_definition), ontology_item=read(args.ontology_item),
        profile=PROFILE_ROOT / args.profile)
    for path, value in ((out, definition), (receipt_path, receipt)):
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with private_text(path) as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
    print(json.dumps({"status": "local-draft-only", "instructionUtf16Units": receipt["instructionUtf16Units"],
                      "cloudCalls": 0, "stagedOrPublished": False}))


if __name__ == "__main__":
    main()
