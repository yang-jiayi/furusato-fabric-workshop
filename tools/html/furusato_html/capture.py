"""Capture the Word participant-guide content model as a language-neutral tree.

The Word deliverable is canonical. Rather than transcribing its prose a second
time, this module implements a builder that duck-types
:class:`furusato_docs.docx_kit.DocumentBuilder` and records every call the
chapter builders make. Running the *same* chapter functions therefore yields a
node stream that is, by construction, the participant guide -- headings,
paragraphs, bullets, callouts, code blocks, tables, figures and captions in
document order.

Nothing here renders HTML. The stream is consumed by :mod:`furusato_html.model`,
which pairs every Japanese string with its English counterpart.
"""

from __future__ import annotations

import io
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Sequence


@dataclass(frozen=True)
class ScreenshotRef:
    """Sentinel returned by :class:`CapturingCarrier` in place of image bytes."""

    tag: str


class CapturingCarrier:
    """Wraps a style carrier so screenshot requests are recorded, not decoded."""

    def __init__(self, carrier: Any):
        self._carrier = carrier
        self.requested: list[str] = []

    def screenshot(self, tag: str) -> ScreenshotRef:
        # Ask the real carrier too, so a missing or retired tag still fails loudly.
        self._carrier.screenshot(tag)
        self.requested.append(tag)
        return ScreenshotRef(tag)

    def __getattr__(self, item: str) -> Any:  # pragma: no cover - passthrough
        return getattr(self._carrier, item)


# --------------------------------------------------------------------- nodes
@dataclass
class Node:
    kind: str
    payload: dict[str, Any] = field(default_factory=dict)

    def __getitem__(self, key: str) -> Any:
        return self.payload[key]

    def get(self, key: str, default: Any = None) -> Any:
        return self.payload.get(key, default)


class CaptureBuilder:
    """Records the participant-guide content model instead of writing OOXML."""

    def __init__(self, carrier: Any, shell_path: Any = None, diagram_index: dict[Path, str] | None = None):
        self.carrier = CapturingCarrier(carrier)
        self.nodes: list[Node] = []
        self.figure_number = 0
        self.table_number = 0
        self.figures: list[str] = []
        self.tables: list[str] = []
        self.cover: dict[str, Any] = {}
        self._diagram_index = {Path(k).resolve(): v for k, v in (diagram_index or {}).items()}

    # ---------------------------------------------------------- primitives
    def _add(self, kind: str, **payload: Any) -> Node:
        node = Node(kind=kind, payload=payload)
        self.nodes.append(node)
        return node

    def paragraph(self, text: str = "", **kwargs: Any) -> Node:
        size = kwargs.get("size")
        return self._add(
            "paragraph",
            text=str(text),
            style=kwargs.get("style"),
            bold=bool(kwargs.get("bold", False)),
            lead=size is not None and float(size) >= 11.5,
        )

    def heading(self, text: str, level: int, **_: Any) -> Node:
        return self._add("heading", text=str(text), level=int(level))

    def body(self, text: str, **_: Any) -> Node:
        return self._add("body", text=str(text))

    def bullets(self, items: Iterable[str], *, numbered: bool = False, **_: Any) -> Node:
        return self._add("bullets", items=[str(i) for i in items], numbered=bool(numbered))

    def callout(self, kind: str, text: str, *, title: str | None = None, **_: Any) -> Node:
        return self._add("callout", tone=str(kind), text=str(text), title=title)

    def code_block(self, text: str, *, language: str = "", **_: Any) -> Node:
        return self._add("code", text=str(text).rstrip("\n"), language=str(language or ""))

    # ---------------------------------------------------------- structures
    def table(
        self,
        headers: Sequence[str],
        rows: Sequence[Sequence[str]],
        *,
        caption: str,
        widths: Sequence[float] | None = None,
        font_size: float = 9.0,
        header_size: float = 9.0,
        **_: Any,
    ) -> Node:
        self.table_number += 1
        self.tables.append(f"表 {self.table_number}　{caption}")
        return self._add(
            "table",
            number=self.table_number,
            headers=[str(h) for h in headers],
            rows=[["" if cell is None else str(cell) for cell in row] for row in rows],
            caption=str(caption),
            widths=list(widths) if widths else None,
        )

    def figure(
        self,
        image: Path | io.BytesIO | ScreenshotRef,
        *,
        caption: str,
        alt_text: str,
        width_ratio: float = 1.0,
        max_height_cm: float | None = None,
        **_: Any,
    ) -> Node:
        self.figure_number += 1
        self.figures.append(f"図 {self.figure_number}　{caption}")
        if isinstance(image, ScreenshotRef):
            source_kind, source_key = "screenshot", image.tag
        elif isinstance(image, Path):
            resolved = image.resolve()
            if resolved not in self._diagram_index:
                raise ValueError(f"figure source {image} is not a known v2.7 diagram")
            source_kind, source_key = "diagram", self._diagram_index[resolved]
        else:  # pragma: no cover - the Word build only passes the two forms above
            raise TypeError(f"unsupported figure source: {type(image)!r}")
        return self._add(
            "figure",
            number=self.figure_number,
            source_kind=source_kind,
            source_key=source_key,
            caption=str(caption),
            alt=str(alt_text),
        )

    # ------------------------------------------------------------- no-ops
    def page_break(self, *_: Any, **__: Any) -> None:
        return None

    def table_of_contents(self, **_: Any) -> None:
        return None

    def update_fields_on_open(self, *_: Any, **__: Any) -> None:  # pragma: no cover - Word only
        return None

    def save(self, path: Any, *_: Any, **__: Any) -> Any:
        """Never writes: the capture exists precisely to avoid a second DOCX."""
        return path


#: Members of the canonical Word builder that carry no content and therefore
#: need no capture counterpart.
_WORD_ONLY_MEMBERS = frozenset({"carrier", "document", "field", "figures", "tables", "figure_number", "table_number"})


def assert_builder_coverage(document_builder: type) -> None:
    """Fail loudly when the canonical Word builder grows a member we ignore.

    The HTML mirror is only complete because it records every call the chapter
    builders make. A new public method on ``DocumentBuilder`` could silently
    drop content from the mirror, so it has to be modelled here first.
    """
    canonical = {
        name
        for name in dir(document_builder)
        if not name.startswith("_") and name not in _WORD_ONLY_MEMBERS
    }
    missing = sorted(name for name in canonical if not hasattr(CaptureBuilder, name))
    if missing:
        raise RuntimeError(
            "furusato_docs.DocumentBuilder gained members the HTML capture does not model: "
            + ", ".join(missing)
            + ". Add them to furusato_html/capture.py so the bilingual mirror stays complete."
        )


def capture_participant_guide(
    context: Any, facts: Any, tests: list[Any], carrier: Any, *, public_documents_only: bool = False
) -> CaptureBuilder:
    """Capture the canonical participant guide by driving its own builder.

    ``participant_guide.build`` owns the chapter order, the argument each
    chapter needs and the cover copy. Rather than duplicating that call list --
    which would silently fall behind when a chapter is added, removed or given
    another parameter -- the real entry point is executed with the Word
    primitives swapped for recording ones. Whatever the DOCX would contain is
    what the capture returns.
    """
    from furusato_docs import oox
    from furusato_docs import participant_guide as pg

    assert_builder_coverage(pg.DocumentBuilder)

    diagram_index: dict[Path, str] = {}
    for key, variants in context.diagrams.items():
        for path in variants.values():
            diagram_index[Path(path)] = key

    captured: dict[str, CaptureBuilder] = {}

    def builder_factory(carrier_argument: Any, shell_path: Any) -> CaptureBuilder:
        builder = CaptureBuilder(carrier_argument, shell_path, diagram_index)
        captured["builder"] = builder
        return builder

    def cover_stub(builder: CaptureBuilder, **kwargs: Any) -> None:
        builder.cover = dict(kwargs)

    def metadata_stub(*args: Any, **kwargs: Any) -> None:
        return None

    originals = {
        "DocumentBuilder": pg.DocumentBuilder,
        "cover_page": pg.cover_page,
        "apply_package_metadata": pg.apply_package_metadata,
    }
    pg.DocumentBuilder = builder_factory  # type: ignore[assignment]
    pg.cover_page = cover_stub  # type: ignore[assignment]
    pg.apply_package_metadata = metadata_stub  # type: ignore[assignment]
    try:
        # All writing primitives are replaced above; these paths are never created.
        scratch = Path(context.root) / "tools" / "html" / "capture-only"
        pg.build(
            context, facts, tests, carrier, scratch / "capture-only.docx", scratch,
            public_documents_only=public_documents_only,
        )
    finally:
        pg.DocumentBuilder = originals["DocumentBuilder"]  # type: ignore[assignment]
        pg.cover_page = originals["cover_page"]  # type: ignore[assignment]
        pg.apply_package_metadata = originals["apply_package_metadata"]  # type: ignore[assignment]

    builder = captured.get("builder")
    if builder is None:  # pragma: no cover - only if the Word entry point changes shape
        raise RuntimeError("participant_guide.build did not construct a document builder")
    if not builder.nodes:
        raise RuntimeError("the participant guide capture produced no content")
    return builder
