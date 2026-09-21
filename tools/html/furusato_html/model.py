"""Turn the captured Word content model into a bilingual document tree.

The capture is a flat node stream in document order. This module

* pairs every Japanese string with its English mirror,
* folds the stream into a section tree using the heading levels,
* derives a stable, human-meaningful id for every section,
* derives the participant progress checklist from the Core hands-on chapters.

Every id is derived from the chapter numbering that the canonical Word guide
already uses, so anchors stay stable across rebuilds and are readable in a URL.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Iterable

from .capture import Node
from .mirror import Mirror

#: Chapters whose steps make up the participant progress checklist. Chapter 5
#: is the first chapter with participant actions; chapter 18 ends the Core flow.
CHECKLIST_CHAPTERS = tuple(range(5, 19))

#: Chapters that are conceptual reading rather than hands-on steps.
CONCEPT_CHAPTERS = (1, 2, 3, 4)


@dataclass(frozen=True)
class Text:
    """One string in both languages."""

    ja: str
    en: str

    def get(self, lang: str) -> str:
        return self.ja if lang == "ja" else self.en

    def __bool__(self) -> bool:
        return bool(self.ja.strip() or self.en.strip())


@dataclass
class Block:
    """A rendered element inside a section."""

    kind: str
    payload: dict[str, Any] = field(default_factory=dict)

    def __getitem__(self, key: str) -> Any:
        return self.payload[key]

    def get(self, key: str, default: Any = None) -> Any:
        return self.payload.get(key, default)


@dataclass
class Section:
    ident: str
    level: int
    number: str
    title: Text
    blocks: list[Block] = field(default_factory=list)
    children: list["Section"] = field(default_factory=list)
    chapter: int | None = None
    appendix: str | None = None
    optional: bool = False
    checklist_id: str | None = None

    def walk(self) -> Iterable["Section"]:
        yield self
        for child in self.children:
            yield from child.walk()

    def iter_blocks(self) -> Iterable[Block]:
        for section in self.walk():
            yield from section.blocks

    def title_without_number(self) -> Text:
        """The heading text with its leading chapter/appendix number removed."""
        return Text(
            ja=_JA_NUMBER_PREFIX.sub("", self.title.ja).strip() or self.title.ja,
            en=_EN_NUMBER_PREFIX.sub("", self.title.en).strip() or self.title.en,
        )


@dataclass
class Document:
    sections: list[Section]
    figures: list[Block]
    tables: list[Block]
    checklist: list[tuple[str, Section]]

    def walk(self) -> Iterable[Section]:
        for section in self.sections:
            yield from section.walk()


# ------------------------------------------------------------------ helpers
_CHAPTER_HEADING = re.compile(r"^(\d+)\.\s")
_SUB_HEADING = re.compile(r"^(\d+(?:\.\d+)+)\s")
_APPENDIX_HEADING = re.compile(r"^付録\s*([A-E])")
_APPENDIX_SUB = re.compile(r"^([A-E])\.(\d+)\s")
_JA_NUMBER_PREFIX = re.compile(r"^(?:\d+(?:\.\d+)*\.?|付録\s*[A-E]|[A-E]\.\d+)[\u3000\s]*")
_EN_NUMBER_PREFIX = re.compile(r"^(?:\d+(?:\.\d+)*\.?|Appendix\s+[A-E]|[A-E]\.\d+)[\u3000\s]*")


def _slug(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text)
    ascii_only = re.sub(r"[^A-Za-z0-9]+", "-", normalized).strip("-").lower()
    return ascii_only or "section"


def _identify(title_ja: str) -> tuple[str, str, int | None, str | None]:
    """Return ``(id, display number, chapter, appendix)`` for a heading."""
    match = _SUB_HEADING.match(title_ja)
    if match:
        number = match.group(1)
        chapter = int(number.split(".")[0])
        return "sec-" + number.replace(".", "-"), number, chapter, None
    match = _CHAPTER_HEADING.match(title_ja)
    if match:
        number = match.group(1)
        return f"ch-{number}", number, int(number), None
    match = _APPENDIX_HEADING.match(title_ja)
    if match:
        letter = match.group(1)
        return f"appendix-{letter.lower()}", letter, None, letter
    match = _APPENDIX_SUB.match(title_ja)
    if match:
        letter, index = match.group(1), match.group(2)
        return f"sec-{letter.lower()}-{index}", f"{letter}.{index}", None, letter
    return "sec-" + _slug(title_ja)[:48], "", None, None


def _text(mirror: Mirror, japanese: str) -> Text:
    return Text(ja=japanese, en=mirror.get(japanese))


def _texts(mirror: Mirror, items: Iterable[str]) -> list[Text]:
    return [_text(mirror, item) for item in items]


# -------------------------------------------------------------- conversion
def _block_from_node(node: Node, mirror: Mirror) -> Block:
    kind = node.kind
    if kind in ("body", "paragraph"):
        return Block("paragraph", {"text": _text(mirror, node["text"]), "lead": bool(node.get("lead"))})
    if kind == "bullets":
        return Block("list", {"items": _texts(mirror, node["items"]), "numbered": bool(node["numbered"])})
    if kind == "callout":
        title = node.get("title")
        return Block(
            "callout",
            {
                "tone": node["tone"],
                "text": _text(mirror, node["text"]),
                "title": _text(mirror, title) if title else None,
            },
        )
    if kind == "code":
        return Block(
            "code",
            {
                "text": node["text"],
                "language": _text(mirror, node["language"]) if node["language"] else None,
            },
        )
    if kind == "table":
        return Block(
            "table",
            {
                "number": node["number"],
                "headers": _texts(mirror, node["headers"]),
                "rows": [_texts(mirror, row) for row in node["rows"]],
                "caption": _text(mirror, node["caption"]),
                "wide": len(node["headers"]) >= 5,
            },
        )
    if kind == "figure":
        return Block(
            "figure",
            {
                "number": node["number"],
                "source_kind": node["source_kind"],
                "source_key": node["source_key"],
                "caption": _text(mirror, node["caption"]),
                "alt": _text(mirror, node["alt"]),
            },
        )
    raise ValueError(f"unsupported captured node kind: {kind}")


def build_document(nodes: list[Node], mirror: Mirror) -> Document:
    """Fold the captured node stream into a bilingual section tree."""
    roots: list[Section] = []
    stack: list[Section] = []
    seen_ids: dict[str, int] = {}
    figures: list[Block] = []
    tables: list[Block] = []

    for node in nodes:
        if node.kind == "heading":
            level = node["level"]
            title_ja = node["text"]
            ident, number, chapter, appendix = _identify(title_ja)
            if ident in seen_ids:
                seen_ids[ident] += 1
                ident = f"{ident}-{seen_ids[ident]}"
            else:
                seen_ids[ident] = 1
            while stack and stack[-1].level >= level:
                stack.pop()
            parent = stack[-1] if stack else None
            inherited_chapter = chapter if chapter is not None else (parent.chapter if parent else None)
            inherited_appendix = appendix if appendix is not None else (parent.appendix if parent else None)
            section = Section(
                ident=ident,
                level=level,
                number=number,
                title=_text(mirror, title_ja),
                chapter=inherited_chapter,
                appendix=inherited_appendix,
                optional=bool(inherited_appendix == "D"),
            )
            if parent is None:
                roots.append(section)
            else:
                parent.children.append(section)
            stack.append(section)
            continue

        if not stack:
            raise ValueError("captured content appeared before the first heading")
        block = _block_from_node(node, mirror)
        stack[-1].blocks.append(block)
        if block.kind == "figure":
            figures.append(block)
        elif block.kind == "table":
            tables.append(block)

    checklist = _build_checklist(roots)
    return Document(sections=roots, figures=figures, tables=tables, checklist=checklist)


def _build_checklist(roots: list[Section]) -> list[tuple[str, Section]]:
    """One checklist step per Core hands-on task.

    A chapter with numbered sub-sections contributes one step per sub-section;
    a chapter without them contributes a single step for the chapter itself.
    Ids are derived from the section anchor, so they stay stable as long as the
    canonical chapter numbering does.
    """
    steps: list[tuple[str, Section]] = []
    for chapter_section in roots:
        if chapter_section.chapter not in CHECKLIST_CHAPTERS:
            continue
        subsections = [child for child in chapter_section.children if child.level == 2]
        targets = subsections or [chapter_section]
        for target in targets:
            step_id = f"step-{target.ident}"
            target.checklist_id = step_id
            steps.append((step_id, target))
    return steps
