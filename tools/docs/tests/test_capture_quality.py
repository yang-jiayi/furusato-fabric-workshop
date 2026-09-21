"""Negative tests for the capture-quality gates.

Each case plants the exact defect the gate exists to catch, runs the gate against
the shipped guide, and restores the original bytes. A gate that cannot be made to
fail is a gate that proves nothing.
"""

import argparse
import importlib.util
import io
import hashlib
import pathlib
import subprocess
import sys
import tempfile
import zipfile

from pathlib import Path

from PIL import Image, ImageDraw

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools" / "docs"))

from furusato_docs.deliverables import deliverable_names, validate_edition

spec = importlib.util.spec_from_file_location("vd", ROOT / "tools" / "docs" / "validate_docs.py")
vd = importlib.util.module_from_spec(spec)
sys.modules["vd"] = vd
spec.loader.exec_module(vd)

CANONICAL_GUIDE = ROOT / "docs" / "Fabric_IQ_Ontology_Workshop_Furusato_Participant_v2.7.0.docx"
GUIDE = CANONICAL_GUIDE

#: The repaired Activator Rules capture, so the test can find its placed copy.
RULES_DIGEST = "8681118a2136fcf8f257b3c04c8d61513807ad558d9b8866ba5e2c7832026611"


def failed_checks(report) -> set[str]:
    return {finding.check for finding in report.findings if finding.level == "FAIL"}


def _rewrite_docx(replace) -> None:
    """Rewrite the guide package through a callback."""
    with zipfile.ZipFile(io.BytesIO(GUIDE.read_bytes())) as archive:
        entries = [(item, archive.read(item.filename)) for item in archive.infolist()]
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for info, data in entries:
            archive.writestr(info, replace(info.filename, data))
    GUIDE.write_bytes(buffer.getvalue())


def blank_the_capture_bodies() -> None:
    """Repaint every placed image as a frame whose body never rendered."""

    def replace(name, data):
        if not name.startswith("word/media/") or not name.endswith(".png"):
            return data
        image = Image.open(io.BytesIO(data)).convert("RGB")
        draw = ImageDraw.Draw(image)
        draw.rectangle((0, int(image.height * 0.18), image.width, image.height), fill=(250, 250, 250))
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        return buffer.getvalue()

    _rewrite_docx(replace)


def leak_a_name_into_a_caption() -> None:
    def replace(name, data):
        if name != "word/document.xml":
            return data
        return data.replace("Instances".encode("utf-8"), "Jiayi".encode("utf-8"), 1)

    _rewrite_docx(replace)


def revert_the_rules_capture() -> None:
    """Put the blank Activator Rules frame back where the repaired one is.

    This is the exact regression that shipped: a 25 KB frame whose body is 0.17 %
    ink under a caption promising a rule in the Running state. It passes a
    band-only test at 56 %, so it exists to prove the ink floor is doing work.
    """
    blob = subprocess.run(
        ["git", "show", "d4f483c:tools/docs/assets/style-carrier.zip"],
        cwd=ROOT,
        capture_output=True,
    ).stdout
    with zipfile.ZipFile(io.BytesIO(blob)) as archive:
        blank = archive.read("screenshots/11-24.png")
    with zipfile.ZipFile(io.BytesIO(GUIDE.read_bytes())) as archive:
        repaired = {
            name: archive.read(name)
            for name in archive.namelist()
            if name.startswith("word/media/")
        }
    target = next(
        name for name, data in repaired.items() if hashlib.sha256(data).hexdigest() == RULES_DIGEST
    )

    def replace(name, data):
        return blank if name == target else data

    _rewrite_docx(replace)


def revert_a_repaired_capture() -> tuple[bytes, Path]:
    """Put an unrepaired capture back into the carrier."""
    carrier = ROOT / "tools" / "docs" / "assets" / "style-carrier.zip"
    original = carrier.read_bytes()
    blob = subprocess.run(
        ["git", "show", "d4f483c:tools/docs/assets/style-carrier.zip"],
        cwd=ROOT,
        capture_output=True,
    ).stdout
    with zipfile.ZipFile(io.BytesIO(blob)) as archive:
        blank = archive.read("screenshots/11-24.png")
    with zipfile.ZipFile(io.BytesIO(original)) as archive:
        entries = [(item, archive.read(item.filename)) for item in archive.infolist()]
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for info, data in entries:
            archive.writestr(info, blank if info.filename == "screenshots/11-24.png" else data)
    carrier.write_bytes(buffer.getvalue())
    return original, carrier


CASES = (
    ("a placed capture never painted its body", blank_the_capture_bodies, "visual.settledCaptures"),
    ("the blank Activator Rules frame comes back", revert_the_rules_capture, "visual.settledCaptures"),
    ("a caption names a person", leak_a_name_into_a_caption, "visual.captionPrivacy"),
)


def main() -> int:
    global GUIDE
    from furusato_docs.context import load_context

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--edition", default="", type=validate_edition)
    arguments = parser.parse_args()
    context = load_context(ROOT, document_edition=arguments.edition)
    source = ROOT / "docs" / deliverable_names(context.version, arguments.edition).participant
    failures = 0
    with tempfile.TemporaryDirectory(prefix="furusato-capture-quality-") as scratch:
        GUIDE = Path(scratch) / source.name
        original_guide = source.read_bytes()
        GUIDE.write_bytes(original_guide)
        try:
            for label, plant, expected in CASES:
                plant()
                observed = failed_checks(vd.validate_visual(ROOT, GUIDE.parent, context, arguments.edition))
                if expected in observed:
                    print(f"  ok   detected: {label}")
                else:
                    print(f"  FAIL undetected: {label} (expected {expected}, got {sorted(observed)})")
                    failures += 1
                GUIDE.write_bytes(original_guide)

            observed = failed_checks(vd.validate_visual(ROOT, GUIDE.parent, context, arguments.edition))
            if observed:
                print(f"  FAIL clean guide reports: {sorted(observed)}")
                failures += 1
            else:
                print("  ok   clean guide passes every capture gate")

            # The carrier gate is the one that stops a rebuild reverting the repairs.
            original, carrier = revert_a_repaired_capture()
            try:
                observed = failed_checks(vd.validate_visual(ROOT, GUIDE.parent, context, arguments.edition))
                if "visual.repairedCaptures" in observed:
                    print("  ok   detected: a carrier rebuild reverted a repaired capture")
                else:
                    print(f"  FAIL undetected: carrier revert (got {sorted(observed)})")
                    failures += 1
            finally:
                carrier.write_bytes(original)
        finally:
            GUIDE = CANONICAL_GUIDE

    print(f"\n{len(CASES) + 2} capture tests, {failures} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
