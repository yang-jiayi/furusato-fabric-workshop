"""Inline every image exactly once.

The deliverable must render with no network and no sibling files, so each
diagram is inlined as sanitized SVG and each Fabric UI screenshot as a lossless
WebP data URI. Lossless WebP is pixel-identical to the source PNG and roughly
half the size, which keeps a 90-screenshot single-file guide practical.

Every asset is embedded once and referenced by id; the builder refuses to embed
the same source twice.
"""

from __future__ import annotations

import base64
import hashlib
import io
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import diagrams

from PIL import Image
from furusato_docs.typography import ascii_parentheses

_XML_DECL = re.compile(r"<\?xml[^>]*\?>\s*", re.I)
_DOCTYPE = re.compile(r"<!DOCTYPE[^>]*>\s*", re.I)
_COMMENT = re.compile(r"<!--.*?-->", re.S)
_SCRIPT = re.compile(r"<script.*?</script>", re.S | re.I)
_ID_ATTR = re.compile(r'\bid="([^"]+)"')
_ARIA_REF = re.compile(r'\b(aria-labelledby|aria-describedby)="([^"]*)"')
_ROOT_A11Y = re.compile(r'\s(?:role|aria-labelledby|aria-describedby|aria-label|aria-hidden)="[^"]*"', re.I)
_WIDTH_HEIGHT = re.compile(r'^(<svg\b[^>]*?)\s(width|height)="[^"]*"', re.I)
_EXTERNAL = re.compile(r'(?:href|src)\s*=\s*"(?!#)(?!data:)([^"]+)"', re.I)

#: A diagram that bakes its own "figure 3" label into the artwork would compete
#: with the caption numbering this page assigns. The token is removed from the
#: inlined copy -- conservatively, only where it stands alone or is followed by a
#: separator -- so the figcaption stays the single source of the figure number.
_BAKED_FIGURE_NUMBER = re.compile(
    r"(?:^|(?<=[\s>（(\[]))"
    r"(?:図|Diagram|Figure|Fig\.?)\s*\d+"
    r"(?:\s*(?:[—–\-/·:：、,]|\s)\s*)?",
    re.I,
)
_TEXT_NODE = re.compile(r"(<(?:text|tspan)\b[^>]*>)(.*?)(</(?:text|tspan)>)", re.S | re.I)


def strip_baked_figure_numbers(svg: str) -> tuple[str, int]:
    """Remove self-assigned figure numbers from a diagram's own text nodes."""
    removed = 0

    def scrub(match: "re.Match[str]") -> str:
        nonlocal removed
        opening, body, closing = match.group(1), match.group(2), match.group(3)
        if "<" in body:  # nested markup: leave the wrapper, inner nodes are visited too
            return match.group(0)
        cleaned, count = _BAKED_FIGURE_NUMBER.subn("", body)
        if count and cleaned.strip():
            removed += count
            return opening + cleaned + closing
        return match.group(0)

    return _TEXT_NODE.sub(scrub, svg), removed


@dataclass
class AssetLibrary:
    """Holds every inlined asset and guarantees single embedding."""

    diagrams: dict[str, str] = field(default_factory=dict)
    diagrams_en: dict[str, str] = field(default_factory=dict)
    screenshots: dict[str, str] = field(default_factory=dict)
    #: Intrinsic pixel size of each screenshot, so the page can reserve the box
    #: before a lazily decoded image arrives. Without it the document grows by
    #: about a sixth while the reader scrolls and anchor navigation overshoots.
    screenshot_sizes: dict[str, tuple[int, int]] = field(default_factory=dict)
    logo: str = ""
    _digests: dict[str, str] = field(default_factory=dict)

    def register_digest(self, key: str, blob: bytes) -> None:
        digest = hashlib.sha256(blob).hexdigest()
        for existing, value in self._digests.items():
            if value == digest and existing != key:
                raise ValueError(f"asset {key} duplicates {existing}; embed it once and reference it")
        self._digests[key] = digest

    @property
    def digests(self) -> dict[str, str]:
        return dict(self._digests)


def sanitize_svg(raw: str, prefix: str, title: str, description: str) -> str:
    """Return page-safe inline SVG: no prolog, no scripts, namespaced ids."""
    svg = _SCRIPT.sub("", _COMMENT.sub("", _DOCTYPE.sub("", _XML_DECL.sub("", raw)))).strip()
    if not svg.startswith("<svg"):
        start = svg.find("<svg")
        if start < 0:
            raise ValueError(f"{prefix}: no <svg> root element")
        svg = svg[start:]

    external = [match for match in _EXTERNAL.findall(svg) if not match.startswith("#")]
    if external:
        raise ValueError(f"{prefix}: SVG references external resources {external}")

    svg, _ = strip_baked_figure_numbers(svg)

    ids = sorted(set(_ID_ATTR.findall(svg)), key=len, reverse=True)
    for ident in ids:
        namespaced = f"{prefix}-{ident}"
        svg = svg.replace(f'id="{ident}"', f'id="{namespaced}"')
        svg = svg.replace(f'href="#{ident}"', f'href="#{namespaced}"')
        svg = svg.replace(f"url(#{ident})", f"url(#{namespaced})")

    # ARIA references point at ids too, so they have to move with them.
    known = set(ids)

    def _namespace_refs(match: "re.Match[str]") -> str:
        tokens = [f"{prefix}-{t}" if t in known else t for t in match.group(2).split()]
        return f'{match.group(1)}="{" ".join(tokens)}"'

    svg = _ARIA_REF.sub(_namespace_refs, svg)

    # Let CSS control the rendered size; keep viewBox for the aspect ratio.
    while _WIDTH_HEIGHT.search(svg):
        svg = _WIDTH_HEIGHT.sub(r"\1", svg, count=1)

    # The page supplies the accessible name, so drop whatever the file declared.
    root_end = svg.index(">")
    root_tag = _ROOT_A11Y.sub("", svg[:root_end])
    svg = root_tag + svg[root_end:]

    svg = svg.replace(
        "<svg",
        '<svg role="img" focusable="false" '
        f'aria-labelledby="{prefix}-title {prefix}-desc"',
        1,
    )
    closing = svg.index(">") + 1
    inline_title = f'<title id="{prefix}-title">{_escape(title)}</title>'
    inline_desc = f'<desc id="{prefix}-desc">{_escape(description)}</desc>'
    return svg[:closing] + inline_title + inline_desc + svg[closing:]


def _escape(text: str) -> str:
    return (
        ascii_parentheses(text).replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def encode_screenshot(blob: bytes) -> str:
    """Return a lossless WebP data URI for a PNG screenshot."""
    with Image.open(io.BytesIO(blob)) as image:
        rgb = image.convert("RGB")
        buffer = io.BytesIO()
        rgb.save(buffer, format="WEBP", lossless=True, quality=100, method=6)
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/webp;base64,{encoded}"


def screenshot_size(blob: bytes) -> tuple[int, int]:
    """Return the intrinsic (width, height) of a screenshot in pixels."""
    with Image.open(io.BytesIO(blob)) as image:
        return int(image.width), int(image.height)


def encode_png(blob: bytes) -> str:
    encoded = base64.b64encode(blob).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def build_library(context: Any, carrier: Any, diagram_keys: list[str], screenshot_tags: list[str]) -> AssetLibrary:
    library = AssetLibrary()
    diagram_map = diagrams.load_map()

    for key in diagram_keys:
        variants = context.diagrams.get(key)
        if not variants or "svg" not in variants:
            raise ValueError(f"diagram {key} has no SVG in docs/assets/v{context.version}")
        path = Path(variants["svg"])
        raw = path.read_text(encoding="utf-8")
        library.register_digest(f"diagram:{key}", raw.encode("utf-8"))
        library.diagrams[key] = raw

        english, missing = diagrams.to_english(raw, diagram_map)
        if missing:
            raise ValueError(
                f"diagram {key} has {len(missing)} label(s) with no English in "
                "tools/html/furusato_html/i18n/diagrams.json:\n  "
                + "\n  ".join(repr(item) for item in missing[:10])
            )
        residual = diagrams.residual_japanese(english)
        if residual:
            raise ValueError(
                f"the English variant of diagram {key} still shows Japanese:\n  "
                + "\n  ".join(repr(item) for item in residual[:10])
            )
        library.diagrams_en[key] = english

    for tag in screenshot_tags:
        blob = carrier.screenshot(tag).getvalue()
        library.register_digest(f"screenshot:{tag}", blob)
        library.screenshots[tag] = encode_screenshot(blob)
        library.screenshot_sizes[tag] = screenshot_size(blob)

    logo = carrier.cover_logo().getvalue()
    library.register_digest("logo", logo)
    library.logo = encode_screenshot(logo)
    return library
