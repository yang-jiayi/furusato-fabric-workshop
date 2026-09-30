"""Local screenshot and document integrity checks; no browser or network."""

from __future__ import annotations

import hashlib
import base64
import binascii
import posixpath
import struct
import zlib
import math
from io import BytesIO
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlsplit
from xml.etree import ElementTree as ET
from zipfile import BadZipFile, ZipFile

from preview_contract import EvidenceError, file_hash, load_json


def image_pixel_signature(content: bytes) -> dict:
    """Decode publication PNG/WebP with the existing optional image toolchain."""
    try:
        from PIL import Image
    except ImportError as error:
        raise EvidenceError("image_decoder_unavailable") from error
    try:
        with Image.open(BytesIO(content)) as image:
            if image.format not in {"PNG", "WEBP"} or not 0 < image.width * image.height <= 25_000_000:
                raise EvidenceError("Unsupported publication image format or size.")
            pixels = image.convert("RGBA").tobytes()
            return {"format": image.format, "width": image.width, "height": image.height,
                    "rgba_sha256": hashlib.sha256(pixels).hexdigest()}
    except (OSError, ValueError) as error:
        raise EvidenceError("Publication image cannot be decoded.") from error


def rendered_image_geometry(documents: list[dict], tolerance: float = 0.01) -> dict:
    """Detect display distortion that byte/pixel equality cannot detect."""
    rows = []
    for document in documents:
        for image in document.get("matching_capture_placements", []):
            width, height = image.get("native_width"), image.get("native_height")
            if not isinstance(width, int) or not isinstance(height, int) or width <= 0 or height <= 0:
                raise EvidenceError("Native image dimensions are required for geometry checks.")
            for rectangle in image.get("display_rects_points", []):
                if (len(rectangle) != 4 or any(type(value) not in {int, float} or not math.isfinite(value) for value in rectangle)
                        or rectangle[2] <= rectangle[0] or rectangle[3] <= rectangle[1]):
                    raise EvidenceError("Invalid rendered image bounds.")
                sx = (rectangle[2] - rectangle[0]) / width
                sy = (rectangle[3] - rectangle[1]) / height
                distortion = abs(sx / sy - 1)
                rows.append({
                    "document": document["document"], "page": image["page"], "capture_id": image["capture_id"],
                    "native_width": width, "native_height": height,
                    "display_width_points": rectangle[2] - rectangle[0],
                    "display_height_points": rectangle[3] - rectangle[1],
                    "horizontal_to_vertical_scale_ratio": sx / sy,
                    "state": "pass" if distortion <= tolerance else "fail",
                })
    return {"schema_version": "furusato-preview30-render-geometry/v1",
            "state": "pass" if rows and all(row["state"] == "pass" for row in rows) else "fail",
            "tolerance_fraction": tolerance, "images": rows,
            "pixel_equality_alone_does_not_prove_faithful_display": True,
            "legibility_still_requires_visual_review": True}


def png_pixels(path: Path | bytes) -> tuple[int, int, int, list[bytes]]:
    """Decode ordinary 8-bit browser PNGs to check every unmasked pixel."""
    data = path if isinstance(path, bytes) else path.read_bytes()
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise EvidenceError("Screenshot must be an actual PNG.")
    offset, image, compressed, ended = 8, None, bytearray(), False
    while offset + 12 <= len(data):
        length = struct.unpack(">I", data[offset:offset + 4])[0]
        kind = data[offset + 4:offset + 8]
        end = offset + 8 + length
        if end + 4 > len(data):
            raise EvidenceError("Truncated PNG chunk.")
        payload = data[offset + 8:end]
        if zlib.crc32(kind + payload) & 0xFFFFFFFF != struct.unpack(">I", data[end:end + 4])[0]:
            raise EvidenceError("PNG checksum mismatch.")
        if kind == b"IHDR":
            if image is not None or length != 13:
                raise EvidenceError("Invalid PNG header.")
            image = struct.unpack(">IIBBBBB", payload)
        elif kind == b"IDAT":
            compressed.extend(payload)
        elif kind == b"IEND":
            ended = True
            offset = end + 4
            break
        offset = end + 4
    if image is None or not ended or offset != len(data):
        raise EvidenceError("Incomplete or ambiguous PNG.")
    width, height, depth, colour, compression, filtering, interlace = image
    channels = {0: 1, 2: 3, 4: 2, 6: 4}.get(colour)
    if not channels or depth != 8 or compression or filtering or interlace:
        raise EvidenceError("Unsupported PNG encoding; do not silently skip pixel verification.")
    if not 0 < width * height <= 25_000_000:
        raise EvidenceError("Screenshot size outside decoder safety bounds.")
    stride = width * channels
    expected = (stride + 1) * height
    try:
        decoder = zlib.decompressobj()
        unpacked = decoder.decompress(bytes(compressed), expected + 1)
        if len(unpacked) != expected or not decoder.eof or decoder.unused_data:
            raise EvidenceError("PNG pixel data length differs.")
    except zlib.error as error:
        raise EvidenceError("Invalid PNG compressed pixels.") from error
    rows, previous = [], bytearray(stride)
    for number in range(height):
        start = number * (stride + 1)
        mode = unpacked[start]
        row = bytearray(unpacked[start + 1:start + stride + 1])
        if mode > 4:
            raise EvidenceError("Unknown PNG row filter.")
        for index in range(stride):
            a = row[index - channels] if index >= channels else 0
            b = previous[index]
            c = previous[index - channels] if index >= channels else 0
            if mode == 1:
                prediction = a
            elif mode == 2:
                prediction = b
            elif mode == 3:
                prediction = (a + b) // 2
            elif mode == 4:
                value = a + b - c
                distances = (abs(value - a), abs(value - b), abs(value - c))
                prediction = (a, b, c)[distances.index(min(distances))]
            else:
                prediction = 0
            row[index] = (row[index] + prediction) % 256
        rows.append(bytes(row))
        previous = row
    return width, height, channels, rows


def redaction_errors(raw: Path, published: Path, masks: list[dict], crop_box: list[int] | None = None) -> list[str]:
    width, height, channels, before = png_pixels(raw)
    if crop_box is not None:
        if (not isinstance(crop_box, (list, tuple)) or len(crop_box) != 4
                or any(type(value) is not int for value in crop_box)):
            return ["invalid_capture_crop_box"]
        left, top, right, bottom = crop_box
        if not (0 <= left < right <= width and 0 <= top < bottom <= height):
            return ["invalid_capture_crop_box"]
        before = [row[left * channels:right * channels] for row in before[top:bottom]]
        width, height = right - left, bottom - top
    w2, h2, ch2, after = png_pixels(published)
    if (width, height, channels) != (w2, h2, ch2):
        return ["capture_resized_cropped_or_reencoded"]
    for mask in masks:
        if (set(mask) != {"x", "y", "width", "height"}
                or any(type(mask[key]) is not int for key in mask)
                or not (0 <= mask["x"] < width and 0 <= mask["y"] < height)
                or not (0 < mask["width"] <= width - mask["x"])
                or not (0 < mask["height"] <= height - mask["y"])):
            return ["invalid_redaction_rectangle"]
    covered = 0
    for y in range(height):
        allowed = bytearray(width)
        for mask in masks:
            if mask["y"] <= y < mask["y"] + mask["height"]:
                allowed[mask["x"]:mask["x"] + mask["width"]] = b"\x01" * mask["width"]
        covered += sum(allowed)
        for x, masked in enumerate(allowed):
            if not masked and before[y][x * channels:(x + 1) * channels] != after[y][x * channels:(x + 1) * channels]:
                return ["pixels_changed_outside_declared_redactions"]
    return ["redaction_obscures_too_much_evidence"] if covered > width * height * 0.25 else []


def capture_errors(proof: dict, store) -> list[str]:
    errors, review = [], proof.get("review", {})
    for key in ("new_ui_verified", "not_mock_or_legacy", "legible_at_delivery_size",
                "redaction_preserves_evidence", "privacy_checked"):
        if review.get(key) is not True:
            errors.append(f"image_review_missing:{key}")
    if proof.get("ui_experience") != "new" or proof.get("origin") != "coordinator_browser":
        errors.append("not_a_genuine_new_ui_capture")
    try:
        raw = store.artifact(proof.get("raw_artifact", {}))
        published = store.artifact(proof.get("artifact", {}))
        receipt = load_json(store.artifact(proof.get("capture_receipt", {})))
        if (receipt.get("origin") != "coordinator_browser" or not receipt.get("tool")
                or receipt.get("raw_sha256") != file_hash(raw)
                or receipt.get("captured_at_utc") != proof.get("captured_at_utc")
                or receipt.get("item_id") not in proof.get("item_ids", [])):
            errors.append("screenshot_receipt_provenance_mismatch")
        page = urlsplit(receipt.get("page_url", ""))
        if page.scheme != "https" or page.hostname not in {"app.fabric.microsoft.com", "app.powerbi.com"}:
            errors.append("screenshot_page_provenance_missing")
        # Tight, unchanged crops can be clearer than a large full desktop.
        # Legibility is reviewed at the actual Word/HTML display size above.
        errors += redaction_errors(raw, published, proof.get("redactions", []), proof.get("crop_box"))
    except (EvidenceError, OSError, ValueError, TypeError) as error:
        errors.append(str(error))
    return errors


class _HTML(HTMLParser):
    def __init__(self):
        super().__init__()
        self.references, self.anchors = [], set()

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        for key in ("id", "name"):
            if attrs.get(key):
                self.anchors.add(attrs[key])
        for key in ("src", "href", "poster"):
            if key in attrs:
                self.references.append((tag, key, attrs[key] or ""))
        if attrs.get("srcset"):
            self.references += [(tag, "src", part.strip().split()[0])
                                for part in attrs["srcset"].split(",") if part.strip()]


def _html(path: Path) -> _HTML:
    parser = _HTML()
    parser.feed(path.read_text(encoding="utf-8-sig"))
    return parser


def check_html(path: Path, document_root: Path) -> dict:
    path, root = path.resolve(), document_root.resolve()
    if not path.is_relative_to(root):
        raise EvidenceError("HTML must be inside the declared document root.")
    parser, errors, external, images, cache = _html(path), [], [], [], {}
    for tag, attribute, value in parser.references:
        target = urlsplit(value)
        if not value:
            errors.append("empty_reference")
            continue
        if target.scheme in {"https", "http"}:
            external.append(value)
            continue
        if target.scheme in {"mailto", "tel"}:
            continue
        if target.scheme == "data" and tag == "img" and attribute == "src":
            try:
                header, payload = value.split(",", 1)
                content = base64.b64decode(payload, validate=True)
                if header.casefold() == "data:image/png;base64":
                    width, height, _, _ = png_pixels(content)
                    mime = "image/png"
                elif header.casefold() == "data:image/webp;base64":
                    signature = image_pixel_signature(content)
                    if signature["format"] != "WEBP":
                        raise EvidenceError("Inline image MIME type does not match its bytes.")
                    width, height, mime = signature["width"], signature["height"], "image/webp"
                else:
                    raise EvidenceError("Unsupported inline image format.")
                images.append({"path": f"inline-image-{len(images) + 1}", "mime": mime,
                               "sha256": hashlib.sha256(content).hexdigest(), "bytes": len(content),
                               "width": width, "height": height})
            except EvidenceError as error:
                errors.append("image_decoder_unavailable" if str(error) == "image_decoder_unavailable"
                              else "invalid_or_unsupported_inline_image")
            except (ValueError, binascii.Error):
                errors.append("invalid_or_unsupported_inline_image")
            continue
        if target.scheme or target.netloc:
            errors.append(f"unsupported_reference:{value}")
            continue
        local = (path.parent / unquote(target.path)).resolve() if target.path else path
        if not local.is_relative_to(root) or not local.is_file():
            errors.append(f"missing_or_external_local_target:{value}")
            continue
        if target.fragment:
            if local.suffix.lower() not in {".htm", ".html"}:
                errors.append(f"unverified_non_html_anchor:{value}")
            else:
                if local not in cache:
                    cache[local] = parser if local == path else _html(local)
                if unquote(target.fragment) not in cache[local].anchors:
                    errors.append(f"missing_anchor:{value}")
        if tag == "img" and attribute == "src":
            images.append({"path": str(local.relative_to(root)), "sha256": file_hash(local)})
    state = "unverified" if errors and set(errors) == {"image_decoder_unavailable"} else "fail" if errors else "pass"
    return {"format": "html", "document_sha256": file_hash(path), "local_state": state,
            "errors": errors, "images": images, "external_unverified": sorted(set(external)),
            "visual_review_required": True, "live_screenshot_provenance_implied": False}


def check_docx(path: Path) -> dict:
    errors, external, images = [], [], []
    rel_namespace = "http://schemas.openxmlformats.org/package/2006/relationships"
    ref_namespace = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    try:
        with ZipFile(path) as archive:
            names = set(archive.namelist())
            if "word/document.xml" not in names:
                raise EvidenceError("Word document.xml missing.")
            relationships = {}
            for name in sorted(names):
                if not name.endswith(".rels"):
                    continue
                part = PurePosixPath(name)
                source = str(part.parent.parent / part.name.removesuffix(".rels"))
                refs = {}
                for item in ET.fromstring(archive.read(name)).findall(f"{{{rel_namespace}}}Relationship"):
                    identity, target = item.get("Id"), item.get("Target", "")
                    if not identity or identity in refs or not target:
                        errors.append(f"invalid_relationship:{name}")
                        continue
                    refs[identity] = target
                    if item.get("TargetMode") == "External":
                        external.append(target)
                    else:
                        local = posixpath.normpath(posixpath.join(str(PurePosixPath(source).parent), unquote(target)))
                        if local not in names:
                            errors.append(f"missing_zip_target:{local}")
                relationships[source] = refs
            for name in sorted(names):
                if name.startswith("word/media/"):
                    content = archive.read(name)
                    if not content:
                        errors.append(f"empty_media:{name}")
                    images.append({"path": name, "sha256": hashlib.sha256(content).hexdigest()})
                if name.startswith("word/") and name.endswith(".xml"):
                    document = ET.fromstring(archive.read(name))
                    for node in document.iter():
                        for attribute, identity in node.attrib.items():
                            if attribute in {f"{{{ref_namespace}}}{key}" for key in ("id", "embed", "link")}:
                                if identity not in relationships.get(name, {}):
                                    errors.append(f"unresolved_relationship:{name}:{identity}")
    except (BadZipFile, ET.ParseError, KeyError) as error:
        raise EvidenceError("Invalid Word package.") from error
    return {"format": "docx", "document_sha256": file_hash(path), "local_state": "fail" if errors else "pass",
            "errors": errors, "images": images, "external_unverified": sorted(set(external)),
            "visual_review_required": True, "live_screenshot_provenance_implied": False}


def check_attachment_pack(pack: Path, dataset_manifest: Path, private_terms: list[str] | None = None) -> dict:
    """Check packaging and plaintext leakage, not actual upload/use or OCR."""
    pack = pack.resolve()
    manifest = load_json(pack / "manifest.json")
    data = load_json(dataset_manifest)
    errors, observed, dictionary_checks = [], [], 0
    expected_flags = {
        "synthetic": True, "conversationScoped": True, "dataIngestion": False,
        "rdfImport": False, "containsPrivateEvaluationAnswers": False,
        "uploadObserved": False, "modelUseObserved": False,
    }
    for field, expected in expected_flags.items():
        if manifest.get(field) is not expected:
            errors.append(f"package_claim_incorrect:{field}")
    if (manifest.get("schemaVersion") != "furusato-attachments/v1"
            or manifest.get("maxFilesPerConversation") != 10
            or manifest.get("maxBytesPerFile") != 5242880):
        errors.append("attachment_contract_or_limits_changed")
    if manifest.get("sourceDatasetVersion") != data.get("datasetVersion"):
        errors.append("source_dataset_version_mismatch")
    files = manifest.get("files", {})
    if not isinstance(files, dict) or not 1 <= len(files) <= 10:
        raise EvidenceError("Attachment inventory must contain 1–10 declared files.")
    normalized_terms = [" ".join(term.split()).casefold() for term in (private_terms or []) if term]
    for name, expected in files.items():
        path = (pack / name).resolve()
        if not path.is_relative_to(pack) or Path(name).name != name or not path.is_file():
            errors.append("missing_or_escaping_attachment")
            continue
        size, checksum = path.stat().st_size, file_hash(path)
        if not 0 < size <= 5242880 or size != expected.get("bytes") or checksum != expected.get("sha256"):
            errors.append(f"attachment_size_or_hash_mismatch:{name}")
        entry = {"name": name, "bytes": size, "sha256": checksum}
        if path.suffix.lower() == ".txt":
            text = " ".join(path.read_text(encoding="utf-8-sig").split()).casefold()
            if any(term in text for term in normalized_terms):
                errors.append(f"private_benchmark_text_detected:{name}")
        elif path.suffix.lower() == ".png":
            try:
                width, height, _, _ = png_pixels(path)
                entry.update(width=width, height=height, kind="generated_domain_diagram_not_ui_evidence")
            except EvidenceError:
                errors.append(f"invalid_attachment_png:{name}")
        elif path.suffix.lower() == ".pdf":
            content = path.read_bytes()
            if not content.startswith(b"%PDF-") or not content.rstrip().endswith(b"%%EOF"):
                errors.append(f"invalid_attachment_pdf_envelope:{name}")
            entry["embedded_font_stream_marker"] = b"/FontFile" in content
        else:
            errors.append(f"unreviewed_attachment_format:{name}")
        observed.append(entry)
    checksum_path = pack / "SHA256SUMS.txt"
    if checksum_path.is_file():
        declared = {}
        for line in checksum_path.read_text(encoding="utf-8-sig").splitlines():
            if not line.strip():
                continue
            checksum, name = line.split(maxsplit=1)
            declared[name.strip().lstrip("*")] = checksum
        for name in files:
            if declared.get(name) != files[name].get("sha256"):
                errors.append(f"checksum_inventory_mismatch:{name}")
        for name, checksum in declared.items():
            path = (pack / name).resolve()
            if not path.is_relative_to(pack) or not path.is_file() or file_hash(path) != checksum:
                errors.append("checksum_target_missing_changed_or_escaping")
    else:
        errors.append("checksum_inventory_missing")
    dictionary = pack / "data-dictionary.txt"
    if dictionary.is_file():
        lines = dictionary.read_text(encoding="utf-8-sig").splitlines()
        for source in [*data.get("files", []), *data.get("incrementFiles", [])]:
            heading = f"{source['file']} | rows={source['rows']}"
            if heading not in lines:
                errors.append(f"dictionary_source_missing:{source['file']}")
                continue
            index = lines.index(heading)
            actual = lines[index + 1] if index + 1 < len(lines) else ""
            if actual != "Columns: " + ", ".join(source["header"].split(",")):
                errors.append(f"dictionary_header_mismatch:{source['file']}")
            else:
                dictionary_checks += 1
    else:
        errors.append("data_dictionary_missing")
    return {
        "schema_version": "furusato-preview30-attachment-check/v1",
        "local_state": "fail" if errors else "pass", "errors": errors,
        "manifest_sha256": file_hash(pack / "manifest.json"),
        "dataset_manifest_sha256": file_hash(dataset_manifest),
        "files": observed, "dictionary_schemas_verified": dictionary_checks,
        "plaintext_private_term_scan": "performed" if normalized_terms else "not_requested",
        "pdf_text_and_image_ocr_review": "unverified",
        "visual_legibility_review": "unverified",
        "upload_state": "unverified", "model_read_use_state": "unverified",
        "ai_accuracy": None, "new_ui_evidence": False,
    }
