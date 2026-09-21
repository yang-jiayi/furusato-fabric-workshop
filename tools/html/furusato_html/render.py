"""Render the bilingual document model as one self-contained HTML file."""

from __future__ import annotations

import html
import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any, Iterable

from furusato_docs.typography import ascii_parentheses

from .assets import AssetLibrary, sanitize_svg
from .model import Block, Document, Section, Text

CALLOUT_TONES = {
    "note": ("note", "callout.note"),
    "gate": ("gate", "callout.gate"),
    "stop": ("stop", "callout.stop"),
    "design": ("design", "callout.design"),
}

ICONS = {
    "search": '<svg class="search__icon" viewBox="0 0 16 16" aria-hidden="true" focusable="false"><path fill="currentColor" d="M11.74 10.34 15 13.6 13.6 15l-3.26-3.26a5.5 5.5 0 1 1 1.4-1.4ZM6.5 10.5a4 4 0 1 0 0-8 4 4 0 0 0 0 8Z"/></svg>',
    "copy": '<svg viewBox="0 0 16 16" aria-hidden="true" focusable="false"><path fill="currentColor" d="M5 1.5A1.5 1.5 0 0 1 6.5 0h6A1.5 1.5 0 0 1 14 1.5v9a1.5 1.5 0 0 1-1.5 1.5H11v1.5A1.5 1.5 0 0 1 9.5 15h-6A1.5 1.5 0 0 1 2 13.5v-9A1.5 1.5 0 0 1 3.5 3H5V1.5ZM6.5 1a.5.5 0 0 0-.5.5V3h3.5A1.5 1.5 0 0 1 11 4.5V11h1.5a.5.5 0 0 0 .5-.5v-9a.5.5 0 0 0-.5-.5h-6ZM3 4.5v9a.5.5 0 0 0 .5.5h6a.5.5 0 0 0 .5-.5v-9a.5.5 0 0 0-.5-.5h-6a.5.5 0 0 0-.5.5Z"/></svg>',
    "zoom": '<svg viewBox="0 0 16 16" aria-hidden="true" focusable="false"><path fill="currentColor" d="M6.5 1a5.5 5.5 0 0 1 4.38 8.84L15 13.94 13.94 15l-4.1-4.12A5.5 5.5 0 1 1 6.5 1Zm0 1.5a4 4 0 1 0 0 8 4 4 0 0 0 0-8ZM6 4h1v2h2v1H7v2H6V7H4V6h2V4Z"/></svg>',
    "print": '<svg class="pill__icon" viewBox="0 0 16 16" aria-hidden="true" focusable="false"><path fill="currentColor" d="M4 1h8a1 1 0 0 1 1 1v2h1a2 2 0 0 1 2 2v4a2 2 0 0 1-2 2h-1v2a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1v-2H2a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h1V2a1 1 0 0 1 1-1Zm8 3V2.5H4V4h8ZM4 11v2.5h8V11H4Zm9.5-4a.75.75 0 1 0 0-1.5.75.75 0 0 0 0 1.5Z"/></svg>',
    "top": '<svg viewBox="0 0 16 16" aria-hidden="true" focusable="false"><path fill="currentColor" d="m8 2.6 5.7 5.7-1.06 1.06L8.75 6.1V14h-1.5V6.1L3.36 9.36 2.3 8.3 8 2.6Z"/></svg>',
    "menu": '<svg class="pill__icon" viewBox="0 0 16 16" aria-hidden="true" focusable="false"><path fill="currentColor" d="M1 3h14v1.6H1V3Zm0 4.2h14v1.6H1V7.2ZM1 11.4h14V13H1v-1.6Z"/></svg>',
    "note": '<svg viewBox="0 0 16 16" aria-hidden="true" focusable="false"><path fill="currentColor" d="M8 0a8 8 0 1 1 0 16A8 8 0 0 1 8 0Zm.75 6.5h-1.5V12h1.5V6.5ZM8 3.5a1 1 0 1 0 0 2 1 1 0 0 0 0-2Z"/></svg>',
    "gate": '<svg viewBox="0 0 16 16" aria-hidden="true" focusable="false"><path fill="currentColor" d="M8 0.6 15.4 14H0.6L8 0.6Zm-.75 5v4.2h1.5V5.6h-1.5Zm0 5.4v1.5h1.5V11h-1.5Z"/></svg>',
    "stop": '<svg viewBox="0 0 16 16" aria-hidden="true" focusable="false"><path fill="currentColor" d="M5.2 0h5.6L16 5.2v5.6L10.8 16H5.2L0 10.8V5.2L5.2 0Zm2.05 3.6v5.2h1.5V3.6h-1.5Zm0 6.6v1.8h1.5v-1.8h-1.5Z"/></svg>',
    "design": '<svg viewBox="0 0 16 16" aria-hidden="true" focusable="false"><path fill="currentColor" d="M2 1h6.5L14 6.5V15H2V1Zm6 1.6V7h4.4L8 2.6ZM4.5 9h7v1.4h-7V9Zm0 2.8h7v1.4h-7v-1.4Z"/></svg>',
}

_CODE_SPAN = re.compile(r"`([^`]+)`")
_URL = re.compile(r"(https://[^\s、。（）()\]】]+)")

#: Lines of code that still fit inside one A4 page at the print type size, and
#: how many monospace characters fit one printed line at that size. Long source
#: lines wrap, so both are needed to predict the printed height.
PRINTABLE_CODE_LINES = 40
PRINT_CODE_COLUMNS = 96


def _integrity(text: str, ctx: RenderContext) -> str:
    """Append a verification footer under the Data Agent instruction block.

    Participants paste these instructions into Fabric verbatim, so the HTML
    states exactly what "verbatim" means: the character count, the UTF-8 byte
    count and the SHA-256 of the shipped file.
    """
    instructions = getattr(ctx.context, "agent_instructions", "")
    paste_text = text.rstrip("\r\n")
    expected_paste = instructions.rstrip("\r\n")
    if not instructions or paste_text != expected_paste:
        return ""
    characters = len(paste_text)
    byte_count = len(paste_text.encode("utf-8"))
    digest = hashlib.sha256(paste_text.encode("utf-8")).hexdigest()
    label = ctx.ui_text("agent.integrity.label")
    detail = Text(
        ja=f"{characters:,} 文字 / {byte_count:,} バイト（UTF-8） / SHA-256",
        en=f"{characters:,} characters / {byte_count:,} bytes (UTF-8) / SHA-256",
    )
    return (
        '<p class="codeblock__integrity">'
        f'<strong>{plain_bilingual(label)}</strong> '
        f"{plain_bilingual(detail)} "
        f'<code>{esc(digest)}</code></p>'
    )


def esc(text: str) -> str:
    return html.escape(ascii_parentheses(str(text)), quote=True)


def rich(text: str) -> str:
    """Render backtick code spans and bare URLs as HTML."""
    out: list[str] = []
    for index, segment in enumerate(str(text).split("`")):
        if index % 2 == 1:
            out.append(f"<code>{esc(segment)}</code>")
            continue
        escaped = esc(segment)
        escaped = _URL.sub(
            lambda match: f'<a href="{match.group(1)}" rel="noreferrer noopener">{match.group(1)}</a>',
            escaped,
        )
        out.append(escaped)
    return "".join(out)


SYNONYM_MARKERS = ("同義語（NB02 が登録）：", "Synonyms (registered by NB02): ")
JAPANESE_RE = re.compile(r"[\u3040-\u309f\u30a0-\u30ff\u4e00-\u9fff]")


def _synonym_markup(value: str) -> str | None:
    """Presentation for an Ontology synonym list, or None if this is not one.

    Two things differ from plain text. English joins the tokens with a comma and
    a space, because an English screen-reader voice does not read the ideographic
    comma as a list separator. Japanese tokens carry their own ``lang="ja"`` in
    both languages, so those same voices pronounce them correctly instead of
    spelling them out. The runtime synonym array itself is untouched: only the
    presentation of the identical values changes.
    """
    for marker in SYNONYM_MARKERS:
        if not value.startswith(marker):
            continue
        tail = value[len(marker) :]
        tokens = [token.strip() for token in tail.split("、") if token.strip()]
        if not tokens:
            return None
        joiner = ", " if marker.endswith(": ") else "、"
        parts = [
            f'<span lang="ja">{esc(token)}</span>' if JAPANESE_RE.search(token) else esc(token)
            for token in tokens
        ]
        return esc(marker) + joiner.join(parts)
    return None


DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")


def _digest_markup(value: str) -> str | None:
    """Wrap a bare SHA-256 cell value in semantic code so it can wrap when printed.

    A 64-character hex string has no break opportunity, so in a narrow appendix
    column the paginator emits only the part that fits and the printed page shows
    a shorter string that still looks like a digest. These values arrive as plain
    text rather than a backtick span, so the `td code` print rule never reached
    them; giving them a real `<code class="digest">` fixes that without applying
    `overflow-wrap: anywhere` to ordinary table prose or headers.
    """
    stripped = value.strip()
    if not DIGEST_RE.match(stripped):
        return None
    return f'<code class="digest">{esc(stripped)}</code>'


def bilingual(text: Text, *, tag: str = "span", extra: str = "") -> str:
    """Emit one Japanese and one English inline span for the same string."""
    space = f" {extra}" if extra else ""
    ja = _digest_markup(text.ja) or _synonym_markup(text.ja) or rich(text.ja)
    en = _digest_markup(text.en) or _synonym_markup(text.en) or rich(text.en)
    return (
        f'<{tag} data-l="ja" lang="ja"{space}>{ja}</{tag}>'
        f'<{tag} data-l="en" lang="en"{space}>{en}</{tag}>'
    )


def plain_bilingual(text: Text, *, tag: str = "span") -> str:
    return (
        f'<{tag} data-l="ja" lang="ja">{esc(text.ja)}</{tag}>'
        f'<{tag} data-l="en" lang="en">{esc(text.en)}</{tag}>'
    )


@dataclass
class RenderContext:
    ui: dict[str, dict[str, str]]
    assets: AssetLibrary
    version: str
    fingerprint: str
    runtime_fingerprint: str
    facts: Any
    context: Any
    stats: dict[str, Any]

    def ui_text(self, key: str) -> Text:
        entry = self.ui[key]
        return Text(ja=entry["ja"], en=entry["en"])

    def label(self, key: str, *, tag: str = "span") -> str:
        return plain_bilingual(self.ui_text(key), tag=tag)
# ------------------------------------------------------------------- blocks
def render_block(block: Block, ctx: RenderContext, counter: dict[str, int]) -> str:
    kind = block.kind
    if kind == "paragraph":
        classes = ' class="lead"' if block.get("lead") else ""
        return f'<p{classes} data-search-block>{bilingual(block["text"])}</p>'

    if kind == "list":
        tag = "ol" if block["numbered"] else "ul"
        items = "".join(f"<li>{bilingual(item)}</li>" for item in block["items"])
        return f"<{tag} data-search-block>{items}</{tag}>"

    if kind == "callout":
        tone, default_key = CALLOUT_TONES[block["tone"]]
        title = block.get("title")
        title_html = bilingual(title) if title else ctx.label(default_key)
        return (
            f'<aside class="callout callout--{tone}" data-search-block>'
            f'<p class="callout__title">{ICONS[tone]}{title_html}</p>'
            f"<p>{bilingual(block['text'])}</p>"
            "</aside>"
        )

    if kind == "code":
        counter["code"] += 1
        block_id = f"code-{counter['code']}"
        language = block["language"]
        language_html = (
            plain_bilingual(language) if language else plain_bilingual(Text("text", "text"))
        )
        integrity = _integrity(block["text"], ctx)
        # A block this tall cannot honour break-inside:avoid on A4, so it is
        # marked instead of silently splitting: print CSS then lets it flow and
        # keeps at least four lines together on each side of the break.
        lines = block["text"].splitlines() or [""]
        # Long lines wrap in print, so estimate rendered lines rather than
        # counting newlines: a source line of 300 characters is four printed
        # lines, and only the rendered height decides whether a page fits.
        rendered = sum(max(1, -(-len(line) // PRINT_CODE_COLUMNS)) for line in lines)
        long_attr = ' data-long="true"' if rendered > PRINTABLE_CODE_LINES else ""
        return (
            f'<div class="codeblock"{long_attr}>'
            '<div class="codeblock__bar">'
            f'<span class="codeblock__lang">{language_html}</span>'
            f'<button type="button" class="codeblock__copy" data-copy-target="{block_id}" '
            f'data-i18n-label="copy.aria" aria-label="{esc(ctx.ui["copy.aria"]["ja"])}">'
            f'{ICONS["copy"]}<span data-copy-label data-i18n="copy.label">{esc(ctx.ui["copy.label"]["ja"])}</span>'
            "</button></div>"
            f'<pre><code id="{block_id}">{esc(block["text"])}</code></pre>'
            f"{integrity}"
            "</div>"
        )

    if kind == "table":
        return render_table(block, ctx)

    if kind == "figure":
        return render_figure(block, ctx)

    raise ValueError(f"unsupported block: {kind}")


def render_table(block: Block, ctx: RenderContext) -> str:
    number = block["number"]
    caption = block["caption"]
    label = ctx.ui_text("table.label")
    caption_html = (
        f'<span class="caption__num">{plain_bilingual(label)} {number}</span> '
        f"{bilingual(caption)}"
    )
    head = "".join(f'<th scope="col">{bilingual(cell)}</th>' for cell in block["headers"])
    body_rows: list[str] = []
    for row in block["rows"]:
        cells: list[str] = []
        for column, cell in enumerate(row):
            if column == 0:
                cells.append(f'<th scope="row">{bilingual(cell)}</th>')
            else:
                cells.append(f"<td>{bilingual(cell)}</td>")
        body_rows.append("<tr>" + "".join(cells) + "</tr>")
    hint = ctx.label("table.scroll")
    return (
        '<div class="table-wrap" data-search-block>'
        f'<div class="table-scroll" tabindex="0" role="region" '
        f'aria-label="{esc(caption.ja)}">'
        f'<table class="cols-{len(block["headers"])}">'
        f"<caption>{caption_html}</caption>"
        f"<thead><tr>{head}</tr></thead>"
        f"<tbody>{''.join(body_rows)}</tbody>"
        "</table></div>"
        f'<p class="table-hint">{hint}</p>'
        "</div>"
    )


def diagram_title(label: Text, number: int) -> str:
    """Accessible name for an inline diagram, in both languages.

    An inline SVG cannot switch language with CSS the way the paired spans do,
    so -- exactly like the bilingual ``alt`` on a screenshot -- it names itself
    in both at once rather than picking one.
    """
    return f"{label.ja} {number} / {label.en} {number}"


def render_figure(block: Block, ctx: RenderContext) -> str:
    number = block["number"]
    caption = block["caption"]
    alt = block["alt"]
    label = ctx.ui_text("figure.label")
    figure_label = f"{label.ja} {number} / {label.en} {number}"
    kind_class = "figure--diagram" if block["source_kind"] == "diagram" else "figure--shot"
    if block["source_kind"] == "diagram":
        key = block["source_key"]
        # One figure, two artworks. The Japanese SVG is the shipped asset; the
        # English one is derived at build time from the maintained translation
        # map, so an English reader gets English artwork instead of a Japanese
        # picture under an English caption. Only the active language is
        # displayed, and only it is exposed to assistive technology.
        media = (
            f'<span class="figure__art" data-l="ja" lang="ja">'
            + sanitize_svg(
                ctx.assets.diagrams[key],
                prefix=f"dg{number}",
                title=diagram_title(label, number),
                description=f"{alt.ja} / {alt.en}",
            )
            + "</span>"
            f'<span class="figure__art" data-l="en" lang="en">'
            + sanitize_svg(
                ctx.assets.diagrams_en[key],
                prefix=f"dge{number}",
                title=diagram_title(label, number),
                description=f"{alt.en} / {alt.ja}",
            )
            + "</span>"
        )
    else:
        uri = ctx.assets.screenshots[block["source_key"]]
        width, height = ctx.assets.screenshot_sizes[block["source_key"]]
        # Screenshots are inline data URIs, so nothing is fetched over the
        # network and lazy loading buys nothing. It does cost something: a lazy
        # image that has never entered the viewport may still be undecoded when
        # the print pipeline snapshots the page, which drops the screenshot from
        # the PDF. Marking them eager keeps every figure present when printing
        # straight from the top of the document.
        media = (
            f'<img src="{uri}" loading="eager" decoding="async" '
            f'width="{width}" height="{height}" '
            f'alt="{esc(alt.ja)} / {esc(alt.en)}">'
        )
    zoom = ctx.label("lightbox.open")
    return (
        f'<figure class="{kind_class}" id="figure-{number}" data-search-block>'
        f'<button type="button" class="figure__frame" data-lightbox '
        f'data-figure-label="{esc(figure_label)}" '
        f'data-i18n-label="lightbox.open" aria-label="{esc(ctx.ui["lightbox.open"]["ja"])}">'
        f"{media}</button>"
        "<figcaption>"
        f'<span class="caption__num">{plain_bilingual(label)} {number}</span> '
        f"{bilingual(caption)}"
        f'<span class="figure__zoom no-print">{ICONS["zoom"]}{zoom}</span>'
        "</figcaption></figure>"
    )


# ----------------------------------------------------------------- sections
def render_section(section: Section, ctx: RenderContext, counter: dict[str, int]) -> str:
    heading_tag = {1: "h2", 2: "h3", 3: "h4", 4: "h5"}[section.level]
    title_html = f'<{heading_tag} data-section-title>{plain_bilingual(section.title)}</{heading_tag}>'

    if section.checklist_id:
        check_label = ctx.label("checklist.step")
        title_html = (
            '<div class="section-head">'
            f"{title_html}"
            f'<label class="step-check no-print">'
            f'<input type="checkbox" data-step-id="{section.checklist_id}" '
            f'aria-labelledby="{section.ident}-check-label">'
            f'<span id="{section.ident}-check-label">{check_label}</span>'
            "</label></div>"
        )

    blocks = "".join(render_block(block, ctx, counter) for block in section.blocks)
    children = "".join(render_section(child, ctx, counter) for child in section.children)

    if section.level == 1:
        chapter_check = ""
        if section.checklist_id:
            chapter_check = (
                f'<label class="step-check no-print">'
                f'<input type="checkbox" data-step-id="{section.checklist_id}" '
                f'aria-labelledby="{section.ident}-check-label">'
                f'<span id="{section.ident}-check-label">{ctx.label("checklist.step")}</span>'
                "</label>"
            )
        return (
            f'<section class="chapter" id="{section.ident}" data-section-id="{section.ident}" '
            f'data-chapter-anchor aria-labelledby="{section.ident}-title">'
            '<div class="section-head">'
            f'<h2 id="{section.ident}-title" data-section-title>{plain_bilingual(section.title)}</h2>'
            f"{chapter_check}</div>"
            f"{blocks}{children}</section>"
        )

    body = f"{title_html}{blocks}"
    if section.optional and section.level >= 2 and section.blocks:
        optional_badge = ctx.label("details.optional")
        body = (
            '<details class="optional-details" open>'
            f'<summary><{heading_tag} data-section-title>{plain_bilingual(section.title)}</{heading_tag}>'
            f'<span class="badge badge--optional">{optional_badge}</span></summary>'
            f'<div class="optional-details__body">{blocks}</div>'
            "</details>"
        )
    return (
        f'<section class="section" id="{section.ident}" data-section-id="{section.ident}">'
        f"{body}{children}</section>"
    )


# ---------------------------------------------------------------------- TOC
def render_toc(document: Document, ctx: RenderContext) -> str:
    groups: list[tuple[str, list[Section]]] = []
    core = [s for s in document.sections if s.chapter is not None]
    reference = [s for s in document.sections if s.appendix in ("A", "B", "C", "E")]
    optional = [s for s in document.sections if s.appendix == "D"]
    groups.append(("toc.core", core))
    groups.append(("toc.optional", optional))
    groups.append(("toc.reference", reference))

    parts: list[str] = []
    for key, sections in groups:
        if not sections:
            continue
        parts.append(f'<p class="toc__group">{ctx.label(key)}</p>')
        parts.append("<ol>")
        for section in sections:
            parts.append(_toc_item(section, ctx))
        parts.append("</ol>")
    return "".join(parts)


def _toc_item(section: Section, ctx: RenderContext) -> str:
    number = esc(section.number)
    link = (
        f'<a class="toc__link" href="#{section.ident}">'
        f'<span class="toc__num" aria-hidden="true">{number}</span>'
        f"<span>{plain_bilingual(section.title_without_number())}</span>"
        "</a>"
    )
    subs = [child for child in section.children if child.level == 2]
    sub_html = ""
    if subs:
        items = []
        for child in subs:
            done_marker = ""
            if child.checklist_id:
                done_marker = (
                    f'<span class="toc__done" data-toc-step="{child.checklist_id}" hidden '
                    f'aria-hidden="true">✓</span>'
                )
            items.append(
                f'<li><a class="toc__link" href="#{child.ident}">'
                f'<span class="toc__num" aria-hidden="true">{esc(child.number)}</span>'
                f"<span>{plain_bilingual(child.title_without_number())}</span>"
                f"{done_marker}</a></li>"
            )
        sub_html = f'<ol class="toc--sub">{"".join(items)}</ol>'
    return f"<li>{link}{sub_html}</li>"
