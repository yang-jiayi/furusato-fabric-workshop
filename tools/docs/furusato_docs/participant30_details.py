"""Pixel-preserving detail views for retained participant screenshots.

Each recipe names an authentic capture, its digest and intrinsic dimensions.
Rendering crops in memory; no canonical screenshot or source asset is rewritten.
"""

from __future__ import annotations

import hashlib
import io
import re
import xml.etree.ElementTree as ET
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
PARTICIPANT_ASSETS = ROOT / "docs" / "assets" / "current-participant"
ARCHITECTURE_SHA256 = "47aaeda3ec2d57524a4279407499b34db683cd32bf8531a74ebab00a00a2798d"
SVG_NAMESPACE = "http://www.w3.org/2000/svg"
JAPANESE = re.compile(r"[\u3040-\u309f\u30a0-\u30ff\u4e00-\u9fff]")

DETAILS = {
    "pc-05-notebook01-ready": {
        "parent": "pc-05-notebook01-ready",
        "primary": True,
        "sourceAsset": "notebook01-ready-output.png",
        "sha256": "545f7a0d6e06a4b548af02c6b6b33364d13ba6fcec23ea25449259e7d48b2c65",
        "size": (1470, 400),
        "crop": (45, 22, 1345, 280),
        "purpose": "version-neutral final-cell code only; no execution status or result",
        "limitations": "the crop omits the surrounding UI; it is not fresh execution evidence or proof of output parity",
    },
    "pc-05-notebook01-ready-detail": {
        "parent": "pc-05-notebook01-ready",
        "source": "pc-05-notebook01-ready.png",
        "sha256": "545f7a0d6e06a4b548af02c6b6b33364d13ba6fcec23ea25449259e7d48b2c65",
        "size": (1470, 400),
        "crop": (45, 338, 745, 378),
        "purpose": "left panel of control-evidence and consumer-warning lines only",
        "limitations": "the first output line is outside this contiguous crop; this example is not fresh execution evidence",
    },
    "pc-05-notebook01-ready-detail-continuation": {
        "parent": "pc-05-notebook01-ready",
        "source": "pc-05-notebook01-ready.png",
        "sha256": "545f7a0d6e06a4b548af02c6b6b33364d13ba6fcec23ea25449259e7d48b2c65",
        "size": (1470, 400),
        "crop": (645, 338, 1345, 378),
        "purpose": "right continuation of the same two lines, overlapping the left panel by 100 pixels",
        "limitations": "original source is retained unchanged; no cross-table multi-ACID atomicity or fresh execution is established",
    },
    "p30-09-copy-002-output-detail": {
        "parent": "p30-09-copy-002",
        "source": "p30-09-copy-002.png",
        "sha256": "9f52acb6e8a07d2c355bc3730e603be56f8749df55bc4ef16050ceae40378153",
        "size": (1372, 780),
        "crop": (671, 416, 1118, 690),
        "purpose": "the visible Copy data1 Output JSON, including rowsRead and rowsCopied",
        "limitations": "the crop stays within the Output panel and leaves adjacent redacted run details outside; the illustrated 5,000-row result does not prove a fresh or automatic 001 chain",
    },
    "p30-15-noattachment-preview": {
        "parent": "p30-15-noattachment-preview",
        "primary": True,
        "source": "p30-15-noattachment-preview.png",
        "sha256": "c61a78fcce1e1131639ba7cf82902f842410e7a4c51da8b8848bcf03bb3f7e98",
        "size": (1372, 891),
        "crop": (1084, 120, 1354, 744),
        "purpose": "response-only excerpt with validation and missing-context explanation, without the proposal canvas, input composer or mode toggle",
        "limitations": "mode cannot be established from this crop or inferred from button color in the preserved original; no saved changes or participant mode selection are established",
    },
    "p30-11-executed-output-detail": {
        "parent": "p30-11-executed-output",
        "source": "p30-11-executed-output.png",
        "sha256": "e9de3d299d1ca31b05a9ab94cd150736523360cda5c0d17eee04dfc0e61f1820",
        "size": (1082, 758),
        "crop": (82, 155, 720, 410),
        "purpose": "the complete visible APPLY_REQUESTED through ANALYTICS_READY output block",
        "limitations": "the generation value remains redacted; this illustration is not a fresh run or Gold-count proof",
    },
    "p30-11-gold-dq-detail": {
        "parent": "p30-11-gold",
        "source": "p30-11-gold.png",
        "sha256": "7362dcbd83633336b836ae0fa607cb764e88884a234b52f0bd459b4f67d6918f",
        "size": (1357, 787),
        "crop": (286, 148, 1337, 358),
        "purpose": "the visible DQ header and all seven result rows and columns",
        "limitations": "RunId/generation remain redacted; RuleName and EvaluatedAtUtc remain ellipsized; rows do not establish this participant's current Gold access",
    },
    "p30-11-gold-dq-left-detail": {
        "parent": "p30-11-gold",
        "source": "p30-11-gold.png",
        "sha256": "7362dcbd83633336b836ae0fa607cb764e88884a234b52f0bd459b4f67d6918f",
        "size": (1357, 787),
        "crop": (286, 148, 986, 358),
        "purpose": "left DQ panel with row indexes, RunId, RuleName, Severity, ExpectedValue and ActualValue; all seven rows",
        "limitations": "example values and source redactions/ellipsis remain; read with the full grid and overlapping right panel",
    },
    "p30-11-gold-dq-right-detail": {
        "parent": "p30-11-gold",
        "source": "p30-11-gold.png",
        "sha256": "7362dcbd83633336b836ae0fa607cb764e88884a234b52f0bd459b4f67d6918f",
        "size": (1357, 787),
        "crop": (856, 148, 1337, 358),
        "purpose": "right DQ panel with ActualValue overlap, Status, EvaluatedAtUtc and the redacted final column; same seven rows",
        "limitations": "align the unchanged row order/heights and overlapping ActualValue column with the left panel; hidden text is not recovered",
    },
    "p30-12-metric-list-detail": {
        "parent": "p30-12-metric-list",
        "source": "p30-12-metric-list.png",
        "sha256": "fb77670b9bac49787bdc5e26fc40a0f0a99aba19c9df5ac7d62103df569f0068",
        "size": (1322, 867),
        "crop": (0, 342, 665, 858),
        "purpose": "the complete visible Metrics panel, including its 10-metric count",
        "limitations": "only visible rows are shown; some names/descriptions are ellipsized and Source values are redacted",
    },
    "p30-12-metrics-expression-detail": {
        "parent": "p30-12-metrics",
        "source": "p30-12-metrics.png",
        "sha256": "d8a86d6a963ab25caa00fc89c68e82239f3f7ebbaa762313b2fae8ebaecf83fe",
        "size": (1356, 866),
        "crop": (0, 0, 982, 782),
        "purpose": "the visible expression, Applies to and description fields",
        "limitations": "the Source remains redacted and synonyms are unavailable; DAX remains copyable in the source text",
    },
    "p30-09-activation-detail-001": {
        "parent": "p30-09-native-delivery",
        "sourceAsset": "activator-001-row-parameters-crop.png",
        "sha256": "23620fa8ec92d732e23d9f2ad757c4df35236fb5e068338f64644b706f6b4fd6",
        "size": (737, 72),
        "crop": (0, 0, 737, 72),
        "purpose": "privacy-safe Subject and Type fields from one retained 001 activation row",
        "limitations": (
            "exact contiguous crop from activator-001-history-20261102-r1-right.jpg "
            "(SHA-256 056b5081e1b9fcefebb388550ee8bca3f3e573dd889150e12afbb44a8e116acd; "
            "1536x821; crop 688,560-1425,632); no stitching or reconstruction. The separate "
            "left capture (SHA-256 de208a3a9e07b61ce7a599c184a5e560a7279396b4c6acabae79984c2a931dcd) "
            "and receipt (SHA-256 2f6a80987067c421b3635a39925d79bec4ddfe129e65dfb75de910de8a03bbb6) "
            "record that it was one of three UUID-filtered rows and show its time; neither is "
            "shown in this crop. Explanatory "
            "example only, not participant-102 or full-pipeline evidence."
        ),
    },
}

DETAILS_BY_PARENT: dict[str, tuple[str, ...]] = {}
SUPPRESSED_PARTICIPANT_DETAILS = {
    "pc-05-notebook01-ready-detail",
    "pc-05-notebook01-ready-detail-continuation",
    "p30-09-copy-002-output-detail",
    "p30-11-gold-dq-detail",
    "p30-11-gold-dq-left-detail",
    "p30-11-gold-dq-right-detail",
}
for _ident, _spec in DETAILS.items():
    if _spec.get("primary") or _ident in SUPPRESSED_PARTICIPANT_DETAILS:
        continue
    DETAILS_BY_PARENT.setdefault(_spec["parent"], ())
    DETAILS_BY_PARENT[_spec["parent"]] += (_ident,)


def number_figures(figures) -> None:
    """Keep retained figure anchors stable; supplements share their parent's number."""
    numbers = {}
    for block in figures:
        key = block["source_key"]
        if key not in DETAILS or DETAILS[key].get("primary"):
            numbers[key] = len(numbers) + 1
            block.payload["number"] = numbers[key]
    for block in figures:
        key = block["source_key"]
        if key in DETAILS and not DETAILS[key].get("primary"):
            parent = DETAILS[key]["parent"]
            siblings = DETAILS_BY_PARENT[parent]
            index = siblings.index(key)
            suffix = "-detail" if index == 0 else f"-detail-{index + 1}"
            block.payload["number"] = f"{numbers[parent]}{suffix}"


def detail_source_path(ident: str) -> Path:
    """Resolve verified authoring assets, independently of generated Lab output."""
    spec = DETAILS[ident]
    if "sourceAsset" in spec:
        path = (PARTICIPANT_ASSETS / spec["sourceAsset"]).resolve()
        if not path.is_relative_to(PARTICIPANT_ASSETS.resolve()) or not path.is_file():
            raise ValueError(f"Detail-crop source is missing or outside its asset directory: {ident}")
        return path
    from .participant30 import figure_path, participant_figures
    parent = spec["parent"]
    if parent in participant_figures():
        return figure_path(parent)
    from .preview30_public_evidence import load_current_captures
    evidence = load_current_captures(
        ROOT / "docs" / "assets" / "current-participant-captures" / "manifest.json", root=ROOT)
    return evidence["captures"][parent]["path"]


def crop_png(ident: str) -> bytes:
    """Render one verified contiguous crop in memory without touching source files."""
    spec = DETAILS[ident]
    source = detail_source_path(ident)
    blob = source.read_bytes()
    if hashlib.sha256(blob).hexdigest() != spec["sha256"]:
        raise ValueError(f"Detail-crop source changed: {ident}")
    with Image.open(io.BytesIO(blob)) as image:
        if image.format != "PNG" or image.size != spec["size"]:
            raise ValueError(f"Detail-crop source dimensions or format changed: {ident}")
        left, top, right, bottom = spec["crop"]
        if not (0 <= left < right <= image.width and 0 <= top < bottom <= image.height):
            raise ValueError(f"Detail-crop bounds are outside the source: {ident}")
        crop = image.crop(spec["crop"])
        output = io.BytesIO()
        crop.save(output, format="PNG")
    return output.getvalue()


def architecture_svg_path() -> Path:
    """Return the editable participant architecture source, never the PNG."""
    path = (PARTICIPANT_ASSETS / "architecture.svg").resolve()
    if not path.is_relative_to(PARTICIPANT_ASSETS.resolve()) or not path.is_file():
        raise ValueError("Participant architecture SVG is missing or outside its asset directory")
    if hashlib.sha256(path.read_bytes()).hexdigest() != ARCHITECTURE_SHA256:
        raise ValueError("Participant architecture SVG changed without updating its source digest")
    return path


def architecture_svg_variants(translations: dict[str, str]) -> tuple[str, str]:
    """Return Japanese and translated English SVG panels from the checked source."""
    raw = architecture_svg_path().read_bytes()
    root = ET.fromstring(raw)
    for node in root.iter(f"{{{SVG_NAMESPACE}}}text"):
        label = node.text or ""
        if not JAPANESE.search(label):
            continue
        translated = translations.get(label)
        if not translated:
            raise ValueError(f"Participant architecture has no English translation for {label!r}")
        node.text = translated
    ET.register_namespace("", SVG_NAMESPACE)
    return raw.decode("utf-8"), ET.tostring(root, encoding="unicode")
