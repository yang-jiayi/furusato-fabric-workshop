"""Negative tests for the runtime determinism gates.

Each planted defect is the exact drift the corresponding gate exists to catch.
The originals are restored in a finally block, so the working tree is unchanged
whether the run passes or fails.
"""

import contextlib
import importlib.util
import io
import json
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "docs"))

spec = importlib.util.spec_from_file_location("vd", ROOT / "tools" / "docs" / "validate_docs.py")
vd = importlib.util.module_from_spec(spec)
sys.modules["vd"] = vd
spec.loader.exec_module(vd)

reseal_spec = importlib.util.spec_from_file_location(
    "rr", ROOT / "tools" / "provisioning" / "reseal_runtime.py"
)
rr = importlib.util.module_from_spec(reseal_spec)
sys.modules["rr"] = rr
reseal_spec.loader.exec_module(rr)

WORKSHOP = ROOT / "workshop" / "v2.7.0"
CONTRACT = WORKSHOP / "participant-workspace-contract.json"
BUNDLE = WORKSHOP / "provisioning" / "bundle"
TEMPLATE = WORKSHOP / "ontology" / "ontology-full-definition-template.json"


class Collector:
    def __init__(self):
        self.failures = []

    def ok(self, name, detail=""):
        pass

    def fail(self, name, detail=""):
        self.failures.append(name)


def crlf_a_sealed_file():
    path = BUNDLE / "data-agent" / "Files" / "Config" / "published" / "stage_config.json"
    original = path.read_bytes()
    path.write_bytes(original.replace(b"\n", b"\r\n"))
    return path, original


def desync_contract_text():
    original = CONTRACT.read_bytes()
    contract = json.loads(original.decode("utf-8"))
    contract["dataAgent"]["sources"][0]["description"] += " (edited by hand)"
    CONTRACT.write_bytes((json.dumps(contract, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    return CONTRACT, original


def reintroduce_alias():
    original = CONTRACT.read_bytes()
    contract = json.loads(original.decode("utf-8"))
    contract["dataAgent"]["globalInstructionsChars"] = 19493
    contract["dataAgent"]["globalInstructionsBytes"] = 19623
    CONTRACT.write_bytes((json.dumps(contract, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    return CONTRACT, original


def stale_template_hash():
    original = TEMPLATE.read_bytes()
    template = json.loads(original.decode("utf-8"))
    template["definitionTemplateSha256"] = "0" * 64
    TEMPLATE.write_bytes((json.dumps(template, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    return TEMPLATE, original


CASES = (
    ("a sealed file is written with CRLF", crlf_a_sealed_file, vd._validate_lf_determinism, "runtime.lfDeterminism"),
    (
        "a bundle file no longer matches the payload",
        crlf_a_sealed_file,
        vd._validate_payload_bundle_parity,
        "runtime.payloadBundleParity",
    ),
    (
        "an embedded source text is edited without resealing",
        desync_contract_text,
        vd._validate_contract_source_parity,
        "runtime.contractSourceParity",
    ),
    (
        "a retired instruction-count alias comes back",
        reintroduce_alias,
        vd._validate_contract_source_parity,
        "runtime.noDuplicateInstructionAliases",
    ),
)


def main() -> int:
    failures = 0
    for label, plant, gate, expected in CASES:
        path, original = plant()
        try:
            report = Collector()
            gate(ROOT, report)
            if expected in report.failures:
                print(f"  ok   detected: {label}")
            else:
                print(f"  FAIL undetected: {label} (expected {expected}, got {report.failures})")
                failures += 1
        finally:
            rr.write_bytes_if_changed(path, original)

    report = Collector()
    for gate in (vd._validate_lf_determinism, vd._validate_payload_bundle_parity, vd._validate_contract_source_parity):
        gate(ROOT, report)
    if report.failures:
        print(f"  FAIL clean tree reports failures: {report.failures}")
        failures += 1
    else:
        print("  ok   clean tree passes every gate")

    with tempfile.NamedTemporaryFile(prefix=".reseal-unrelated-", dir=ROOT, delete=False) as handle:
        probe = pathlib.Path(handle.name)
    try:
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            reseal_result = rr.reseal(ROOT, True)
        if reseal_result == 0:
            print("  ok   reseal check ignores an unrelated dirty worktree file")
        else:
            print(f"  FAIL reseal check reported unrelated drift:\n{output.getvalue()}")
            failures += 1
    finally:
        probe.unlink(missing_ok=True)

    original_tree = rr.snapshot_bytes(WORKSHOP)
    stale_template_hash()
    try:
        before = rr.snapshot_tree(WORKSHOP)
        aborted = False
        try:
            rr.reseal(ROOT, True)
        except SystemExit:
            aborted = True
        after = rr.snapshot_tree(WORKSHOP)
        changed = sorted(
            relative
            for relative in before.keys() | after.keys()
            if before.get(relative) != after.get(relative)
        )
        if aborted and after == before:
            print("  ok   a failed reseal rolls back every partial write")
        else:
            print(
                "  FAIL failed reseal did not roll back cleanly "
                f"(aborted={aborted}, changed={changed})"
            )
            failures += 1
    finally:
        rr.restore_tree(WORKSHOP, original_tree)

    print(f"\n{len(CASES) + 3} determinism tests, {failures} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
