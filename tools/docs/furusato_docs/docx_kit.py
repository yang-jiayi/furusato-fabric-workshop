"""Shared Microsoft Fabric IQ visual language for the Word deliverables."""

from __future__ import annotations

import io
import math
import re
from pathlib import Path
from typing import Iterable, Sequence

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.oxml.ns import qn
from docx.shared import Emu, Pt, RGBColor

from .oox import StyleCarrier, set_alt_text
from .reproducible import save_atomically
from .typography import normalize_word_parentheses

JP_FONT = "Yu Gothic UI"
MONO_FONT = "Consolas"

#: Inline code must stay legible in dense parameter tables.
MIN_CODE_PT = 8.0

#: Longest inline-code token that may be protected from a mid-token line break.
#: Only full-width contexts (body text, bullets, callouts) are protected: inside a
#: narrow table cell an unbreakable token would overflow the column instead.
MAX_PROTECTED_TOKEN = 16

#: Bare http(s) URLs in prose and reference tables become real Word hyperlinks.
_URL_PATTERN = re.compile(r"https?://[^\s、。（）「」`]+")

#: Smallest printed resolution a UI capture may have. Below roughly 180 dpi the
#: small type inside a Fabric dialog stops being legible on paper, so a capture is
#: printed smaller rather than upscaled past this floor.
MIN_FIGURE_DPI = 180


def _pixel_width(image) -> int | None:
    """Pixel width of a figure source, without depending on Pillow being present."""
    try:
        from PIL import Image as _Image
    except Exception:  # pragma: no cover - Pillow is a declared requirement
        return None
    try:
        if isinstance(image, Path):
            with _Image.open(image) as opened:
                return int(opened.width)
        position = image.tell()
        try:
            with _Image.open(image) as opened:
                return int(opened.width)
        finally:
            image.seek(position)
    except Exception:
        return None

BRAND_BLUE = RGBColor(0x17, 0x4C, 0x88)
BRAND_TEAL = RGBColor(0x0F, 0x6C, 0xBD)
BRAND_GRAY = RGBColor(0x7A, 0x86, 0x9A)
BODY_GRAY = RGBColor(0x4B, 0x55, 0x63)
CAPTION_GRAY = RGBColor(0x5B, 0x66, 0x74)

SHADE_HEADER = "174C88"
SHADE_BAND = "EEF3F9"
SHADE_NOTE = "F2F7FC"
SHADE_WARN = "FFF6E5"
SHADE_STOP = "FDEEEE"
SHADE_CODE = "F5F7FA"

CALLOUT_STYLES = {
    "note": (SHADE_NOTE, "0F6CBD", "ポイント"),
    "gate": (SHADE_WARN, "B26B00", "ゲート"),
    "stop": (SHADE_STOP, "A4262C", "注意"),
    "design": (SHADE_BAND, "174C88", "設計判断"),
}

#: A code listing up to this many *rendered* rows is kept on one page by default;
#: longer listings are allowed to break so they do not push a blank page in front
#: of themselves. A caller that has measured the listing can override this.
CODE_BLOCK_UNBREAKABLE_LINES = 24

#: Opening lines of a splittable listing that must stay under their label. Fewer
#: than this at the foot of a page is an orphan stub rather than a listing.
CODE_BLOCK_MIN_LEAD_LINES = 4

#: A splittable listing is laid out as unbreakable rows of this many lines, so
#: Word breaks between chunks instead of slicing one tall row wherever the page
#: happens to end. Twelve lines is roughly a third of an A4 body column.
CODE_BLOCK_CHUNK_LINES = 12

#: Advance width of one monospace character as a fraction of its point size.
MONO_ADVANCE_RATIO = 0.60

#: Word's default left and right cell margin, in points.
TABLE_CELL_MARGIN_PT = 5.4

#: A named column may shrink to this size, but no further: below it an identifier
#: is no longer readable on paper and a wrapped token would be the lesser evil.
TOKEN_FIT_MIN_PT = 6.6

#: 8.5 pt monospace at single spacing, plus the cell padding.
CODE_LINE_HEIGHT_PT = 10.6

#: A4 height minus the top and bottom margins, in points.
BODY_HEIGHT_PT = (16838 - 1134 - 1020) / 20

#: Consolas advance width as a fraction of the point size (1126/2048 em).
MONO_ADVANCE_RATIO = 0.55

#: Word's default table cell margin on each side, in points (0.19 cm).
CELL_PADDING_PT = 5.4


def _shade(element, fill: str) -> None:
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    element.append(shd)


def _borders(element, color: str, size: int = 4, sides: Sequence[str] = ("top", "left", "bottom", "right")) -> None:
    borders = OxmlElement("w:pBdr") if element.tag == qn("w:pPr") else OxmlElement("w:tcBorders")
    for side in sides:
        edge = OxmlElement(f"w:{side}")
        edge.set(qn("w:val"), "single")
        edge.set(qn("w:sz"), str(size))
        edge.set(qn("w:space"), "0")
        edge.set(qn("w:color"), color)
        borders.append(edge)
    element.append(borders)


def _cant_split(table) -> None:
    """Keep a single-row container (callout, code block) on one page."""
    for row in table.rows:
        row_pr = row._tr.get_or_add_trPr()
        if row_pr.find(qn("w:cantSplit")) is None:
            flag = OxmlElement("w:cantSplit")
            flag.set(qn("w:val"), "true")
            row_pr.append(flag)


def _cant_split_row(row) -> None:
    """Keep one row whole; used for the label row above a splittable listing."""
    row_pr = row._tr.get_or_add_trPr()
    if row_pr.find(qn("w:cantSplit")) is None:
        flag = OxmlElement("w:cantSplit")
        flag.set(qn("w:val"), "true")
        row_pr.append(flag)


def _repeat_header_row(row) -> None:
    """Reprint this row at the top of every page the table continues onto."""
    row_pr = row._tr.get_or_add_trPr()
    if row_pr.find(qn("w:tblHeader")) is None:
        repeat = OxmlElement("w:tblHeader")
        repeat.set(qn("w:val"), "true")
        row_pr.append(repeat)


def _keep_with_next(element) -> None:
    """Mark a paragraph (or every paragraph in a table) as ``keepNext``."""
    paragraphs = element.paragraphs if hasattr(element, "paragraphs") else None
    if paragraphs is None:
        targets = [element]
    else:
        targets = list(paragraphs)
        for row in getattr(element, "rows", []):
            for cell in row.cells:
                targets.extend(cell.paragraphs)
    for paragraph in targets:
        paragraph.paragraph_format.keep_with_next = True


def _no_mid_token_break(paragraph) -> None:
    """Forbid Latin mid-word line breaks so a path or regex stays in one piece."""
    p_pr = paragraph._p.get_or_add_pPr()
    if p_pr.find(qn("w:wordWrap")) is None:
        wrap = OxmlElement("w:wordWrap")
        wrap.set(qn("w:val"), "0")
        p_pr.append(wrap)


class DocumentBuilder:
    """Thin, opinionated wrapper that keeps every document visually consistent."""

    def __init__(self, carrier: StyleCarrier, shell_path: Path):
        carrier.build_shell(shell_path)
        self.carrier = carrier
        self.document = Document(str(shell_path))
        self.figure_number = 0
        self.hyperlinks: list[str] = []
        self.table_number = 0
        self.figures: list[str] = []
        self.tables: list[str] = []
        self._chapter_started = False
        self._configure_defaults()

    # ------------------------------------------------------------- base setup
    def _configure_defaults(self) -> None:
        normal = self.document.styles["Normal"]
        normal.font.name = JP_FONT
        normal.font.size = Pt(10.5)
        rpr = normal.element.get_or_add_rPr()
        rfonts = rpr.find(qn("w:rFonts"))
        if rfonts is None:
            rfonts = OxmlElement("w:rFonts")
            rpr.append(rfonts)
        for attribute in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
            rfonts.set(qn(attribute), JP_FONT)
        for name, size, color in (
            ("Heading 1", 19, BRAND_BLUE),
            ("Heading 2", 14.5, BRAND_BLUE),
            ("Heading 3", 12, BRAND_TEAL),
            ("Heading 4", 11, BODY_GRAY),
            ("Title", 30, BRAND_BLUE),
            ("Caption", 9, CAPTION_GRAY),
        ):
            style = self.document.styles[name]
            style.font.name = JP_FONT
            style.font.size = Pt(size)
            style.font.color.rgb = color
            style_rpr = style.element.get_or_add_rPr()
            style_rfonts = style_rpr.find(qn("w:rFonts"))
            if style_rfonts is None:
                style_rfonts = OxmlElement("w:rFonts")
                style_rpr.append(style_rfonts)
            for attribute in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
                style_rfonts.set(qn(attribute), JP_FONT)

        section = self.document.sections[0]
        section.header.is_linked_to_previous = False
        section.footer.is_linked_to_previous = False

    # --------------------------------------------------------------- primitives
    def _rich(self, paragraph, text: str, *, size: float | None = None, protect: bool = False) -> None:
        """Add text to a paragraph, rendering `backtick` spans as inline code."""
        segments = str(text).split("`")
        code_tokens = [segment for index, segment in enumerate(segments) if index % 2 == 1 and segment]
        for index, segment in enumerate(segments):
            if not segment:
                continue
            is_code = index % 2 == 1
            if not is_code and _URL_PATTERN.search(segment):
                self._rich_with_links(paragraph, segment, size)
                continue
            run = paragraph.add_run(segment)
            if size:
                run.font.size = Pt(size)
            if is_code:
                run.font.name = MONO_FONT
                run.font.size = Pt(max(MIN_CODE_PT, (size or 10.5) - 0.7))
                run.font.color.rgb = RGBColor(0x0B, 0x45, 0x78)
                rpr = run._element.get_or_add_rPr()
                rfonts = rpr.find(qn("w:rFonts"))
                if rfonts is None:
                    rfonts = OxmlElement("w:rFonts")
                    rpr.append(rfonts)
                for attribute in ("w:ascii", "w:hAnsi", "w:cs"):
                    rfonts.set(qn(attribute), MONO_FONT)
        if protect and code_tokens and max(len(token) for token in code_tokens) <= MAX_PROTECTED_TOKEN:
            _no_mid_token_break(paragraph)

    def _rich_with_links(self, paragraph, text: str, size: float | None) -> None:
        """Split ``text`` on URLs and emit each URL as a real Word hyperlink.

        A reference table whose URLs are plain text forces a reader to retype
        them, and a PDF export produces nothing clickable at all. Word needs an
        explicit ``w:hyperlink`` element bound to an external relationship, which
        python-docx does not create for us.
        """
        position = 0
        for match in _URL_PATTERN.finditer(text):
            before = text[position : match.start()]
            if before:
                run = paragraph.add_run(before)
                if size:
                    run.font.size = Pt(size)
            url = match.group(0).rstrip(").,;")
            trailing = match.group(0)[len(url) :]
            self._hyperlink(paragraph, url, size)
            if trailing:
                run = paragraph.add_run(trailing)
                if size:
                    run.font.size = Pt(size)
            position = match.end()
        tail = text[position:]
        if tail:
            run = paragraph.add_run(tail)
            if size:
                run.font.size = Pt(size)

    def _hyperlink(self, paragraph, url: str, size: float | None) -> None:
        part = paragraph.part
        relationship_id = part.relate_to(url, RT.HYPERLINK, is_external=True)
        hyperlink = OxmlElement("w:hyperlink")
        hyperlink.set(qn("r:id"), relationship_id)
        run = OxmlElement("w:r")
        properties = OxmlElement("w:rPr")
        style = OxmlElement("w:rStyle")
        style.set(qn("w:val"), "Hyperlink")
        properties.append(style)
        colour = OxmlElement("w:color")
        colour.set(qn("w:val"), "0F6CBD")
        properties.append(colour)
        underline = OxmlElement("w:u")
        underline.set(qn("w:val"), "single")
        properties.append(underline)
        if size:
            size_element = OxmlElement("w:sz")
            size_element.set(qn("w:val"), str(int(round(size * 2))))
            properties.append(size_element)
        run.append(properties)
        text_element = OxmlElement("w:t")
        text_element.text = url
        text_element.set(qn("xml:space"), "preserve")
        run.append(text_element)
        hyperlink.append(run)
        paragraph._p.append(hyperlink)
        self.hyperlinks.append(url)

    def paragraph(
        self,
        text: str = "",
        *,
        style: str | None = None,
        size: float | None = None,
        bold: bool = False,
        color: RGBColor | None = None,
        align: WD_ALIGN_PARAGRAPH | None = None,
        space_after: float | None = None,
        space_before: float | None = None,
    ):
        paragraph = self.document.add_paragraph(style=style)
        if text:
            run = paragraph.add_run(text)
            run.bold = bold
            if size:
                run.font.size = Pt(size)
            if color is not None:
                run.font.color.rgb = color
        if align is not None:
            paragraph.alignment = align
        if space_after is not None:
            paragraph.paragraph_format.space_after = Pt(space_after)
        if space_before is not None:
            paragraph.paragraph_format.space_before = Pt(space_before)
        return paragraph

    def heading(self, text: str, level: int, *, new_page: bool = True, pull_up: bool = False):
        """Add a heading.

        ``new_page`` controls only the chapter-level behaviour: a level-1 heading
        normally starts a page, but a chapter that follows a short closing block
        can be allowed to flow onto the same page instead of leaving 80 % of it
        blank. ``keepNext`` is always set, so a heading that does flow can never be
        stranded at the foot of a page without its first paragraph.

        ``pull_up`` additionally binds the block above the heading to it, so a
        short closing note travels with the section that follows instead of
        clinging to a page that has no room for anything else.
        """
        if pull_up:
            self._keep_previous_with_next()
        paragraph = self.document.add_paragraph(style=f"Heading {level}")
        paragraph.add_run(text)
        paragraph.paragraph_format.space_before = Pt(16 if level == 1 else 11)
        paragraph.paragraph_format.space_after = Pt(6)
        paragraph.paragraph_format.keep_with_next = True
        if level == 1:
            # The contents section already ends with a next-page section break, so the
            # first chapter must not add a second break and leave an empty page behind.
            paragraph.paragraph_format.page_break_before = new_page and self._chapter_started
            if not (new_page and self._chapter_started):
                # A flowing chapter needs breathing room from the block above it.
                paragraph.paragraph_format.space_before = Pt(26)
            self._chapter_started = True
            _borders(paragraph._p.get_or_add_pPr(), "D0D7DE", 6, ("bottom",))
        return paragraph

    def body(self, text: str):
        paragraph = self.document.add_paragraph()
        self._rich(paragraph, text, protect=True)
        paragraph.paragraph_format.space_after = Pt(6)
        paragraph.paragraph_format.line_spacing = 1.12
        return paragraph

    def bullets(self, items: Iterable[str], *, numbered: bool = False):
        style = "List Number" if numbered else "List Bullet"
        num_id = self._restart_numbering() if numbered else None
        for item in items:
            paragraph = self.document.add_paragraph(style=style)
            if num_id is not None:
                self._apply_num_id(paragraph, num_id)
            self._rich(paragraph, item, protect=True)
            paragraph.paragraph_format.space_after = Pt(2)
            paragraph.paragraph_format.line_spacing = 1.1

    def _restart_numbering(self) -> int:
        """Return a fresh numbering instance so each numbered list starts at 1.

        The ``List Number`` style points at a single numbering instance, so every
        numbered list in the document would otherwise continue the previous one
        and a step list in chapter 6 would open at "16.".
        """
        numbering = self.document.part.numbering_part.element
        abstract_id = self._list_number_abstract_id(numbering)
        used = [
            int(node.get(qn("w:numId")))
            for node in numbering.findall(qn("w:num"))
            if node.get(qn("w:numId"))
        ]
        num_id = max(used, default=0) + 1
        num = OxmlElement("w:num")
        num.set(qn("w:numId"), str(num_id))
        abstract = OxmlElement("w:abstractNumId")
        abstract.set(qn("w:val"), str(abstract_id))
        num.append(abstract)
        override = OxmlElement("w:lvlOverride")
        override.set(qn("w:ilvl"), "0")
        start = OxmlElement("w:startOverride")
        start.set(qn("w:val"), "1")
        override.append(start)
        num.append(override)
        numbering.append(num)
        return num_id

    def _list_number_abstract_id(self, numbering) -> int:
        style = self.document.styles["List Number"].element
        num_id_node = style.find(f"{qn('w:pPr')}/{qn('w:numPr')}/{qn('w:numId')}")
        if num_id_node is None:
            raise RuntimeError("The List Number style declares no numbering instance.")
        wanted = num_id_node.get(qn("w:val"))
        for node in numbering.findall(qn("w:num")):
            if node.get(qn("w:numId")) == wanted:
                abstract = node.find(qn("w:abstractNumId"))
                return int(abstract.get(qn("w:val")))
        raise RuntimeError(f"Numbering instance {wanted} is not defined.")

    @staticmethod
    def _apply_num_id(paragraph, num_id: int) -> None:
        p_pr = paragraph._p.get_or_add_pPr()
        num_pr = OxmlElement("w:numPr")
        ilvl = OxmlElement("w:ilvl")
        ilvl.set(qn("w:val"), "0")
        num_pr.append(ilvl)
        node = OxmlElement("w:numId")
        node.set(qn("w:val"), str(num_id))
        num_pr.append(node)
        style = p_pr.find(qn("w:pStyle"))
        if style is not None:
            style.addnext(num_pr)
        else:
            p_pr.insert(0, num_pr)

    def callout(
        self,
        kind: str,
        text: str,
        *,
        title: str | None = None,
        keep_with_next: bool = False,
        pull_up: bool = False,
    ):
        fill, border, default_title = CALLOUT_STYLES[kind]
        if pull_up:
            # Bind the preceding block to this callout so a short note at the end of
            # a section is never left alone on a page of its own.
            self._keep_previous_with_next()
        table = self.document.add_table(rows=1, cols=1)
        table.alignment = WD_TABLE_ALIGNMENT.LEFT
        cell = table.cell(0, 0)
        properties = cell._tc.get_or_add_tcPr()
        _shade(properties, fill)
        _borders(properties, border, 4, ("left",))
        cell.text = ""
        heading_paragraph = cell.paragraphs[0]
        run = heading_paragraph.add_run(f"{title or default_title}")
        run.bold = True
        run.font.size = Pt(9.5)
        run.font.color.rgb = RGBColor.from_string(border)
        heading_paragraph.paragraph_format.space_after = Pt(1)
        heading_paragraph.paragraph_format.keep_with_next = True
        body_paragraph = cell.add_paragraph()
        self._rich(body_paragraph, text, size=9.5, protect=True)
        body_paragraph.paragraph_format.space_after = Pt(0)
        # A callout is one visual unit: it must never be split across a page.
        _cant_split(table)
        if keep_with_next:
            body_paragraph.paragraph_format.keep_with_next = True
        spacer = self.document.add_paragraph()
        self._collapse(spacer)
        if keep_with_next:
            spacer.paragraph_format.keep_with_next = True
        return table

    def _keep_previous_with_next(self) -> None:
        """Mark the block before the insertion point as ``keepNext``.

        Used to pull a short trailing callout up onto the page that holds the
        content it belongs to, instead of letting it start a page of its own.
        """
        body = self.document.element.body
        for element in reversed(list(body)):
            if element.tag == qn("w:p"):
                text = "".join(node.text or "" for node in element.iter(qn("w:t"))).strip()
                if not text:
                    # A collapsed spacer: keep it with the callout and look further back.
                    self._set_keep_next(element)
                    continue
                self._set_keep_next(element)
                return
            if element.tag == qn("w:tbl"):
                for cell_paragraph in element.iter(qn("w:p")):
                    self._set_keep_next(cell_paragraph)
                return

    @staticmethod
    def _set_keep_next(paragraph_element) -> None:
        p_pr = paragraph_element.find(qn("w:pPr"))
        if p_pr is None:
            p_pr = OxmlElement("w:pPr")
            paragraph_element.insert(0, p_pr)
        if p_pr.find(qn("w:keepNext")) is None:
            keep = OxmlElement("w:keepNext")
            style = p_pr.find(qn("w:pStyle"))
            if style is not None:
                style.addnext(keep)
            else:
                p_pr.insert(0, keep)

    def _rendered_code_rows(self, lines: Sequence[str]) -> int:
        """Rows a listing occupies once its long lines wrap inside the code cell.

        ``len(lines)`` counts logical lines. A source-instruction listing carries
        a handful of lines several hundred characters long, so the logical count
        understates the height by an order of magnitude: the listing would be
        marked unbreakable, Word would push the whole block onto a fresh page and
        strand the heading above it on a page of its own.
        """
        section = self.document.sections[0]
        usable_pt = section.page_width.pt - section.left_margin.pt - section.right_margin.pt
        text_pt = max(usable_pt - 2 * CELL_PADDING_PT, 1.0)
        per_row = max(int(text_pt / (8.5 * MONO_ADVANCE_RATIO)), 1)
        return sum(max(1, math.ceil(len(line) / per_row)) for line in lines)

    def code_block(self, text: str, *, language: str = "", keep_together: bool | None = None):
        lines = text.rstrip("\n").split("\n")
        # The label used to sit under the listing, so a listing that broke across a
        # page opened with unlabelled code and the reader met the label only at the
        # end. Carrying it as a repeating header row puts it above the block and
        # reprints it at the top of every continuation page, which is the only cue
        # Word can place automatically on a page it decides to create.
        labelled = bool(language)
        if keep_together is None:
            keep_together = self._rendered_code_rows(lines) <= CODE_BLOCK_UNBREAKABLE_LINES
        # A single tall row splits wherever the page happens to end, which can leave
        # a sliver - or nothing but the repeated label - on the continuation page.
        # A listing that has to break is therefore laid out as several unbreakable
        # rows, so Word can only break between chunks and every continuation page
        # carries at least one full chunk under its label.
        chunks = (
            [lines]
            if keep_together
            else [
                lines[start : start + CODE_BLOCK_CHUNK_LINES]
                for start in range(0, len(lines), CODE_BLOCK_CHUNK_LINES)
            ]
        )
        table = self.document.add_table(rows=(1 if labelled else 0) + len(chunks), cols=1)
        if labelled:
            header = table.cell(0, 0)
            header.text = ""
            header_paragraph = header.paragraphs[0]
            header_run = header_paragraph.add_run(language)
            header_run.bold = True
            header_run.font.size = Pt(8.5)
            header_paragraph.paragraph_format.space_after = Pt(0)
            header_paragraph.paragraph_format.space_before = Pt(0)
            _shade(header._tc.get_or_add_tcPr(), SHADE_HEADER)
            header_run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
            _borders(header._tc.get_or_add_tcPr(), "D0D7DE", 4)
            _repeat_header_row(table.rows[0])
            _cant_split_row(table.rows[0])
        for chunk_index, chunk in enumerate(chunks):
            cell = table.cell((1 if labelled else 0) + chunk_index, 0)
            properties = cell._tc.get_or_add_tcPr()
            _shade(properties, SHADE_CODE)
            # Only the outer edges are drawn, so consecutive chunks read as one
            # continuous listing rather than a stack of boxes.
            _borders(
                properties,
                "D0D7DE",
                4,
                sides=("left", "right")
                + (("top",) if chunk_index == 0 else ())
                + (("bottom",) if chunk_index == len(chunks) - 1 else ()),
            )
            cell.text = ""
            first = True
            for line in chunk:
                paragraph = cell.paragraphs[0] if first else cell.add_paragraph()
                first = False
                run = paragraph.add_run(line if line else " ")
                run.font.name = MONO_FONT
                run.font.size = Pt(8.5)
                rpr = run._element.get_or_add_rPr()
                rfonts = rpr.find(qn("w:rFonts"))
                if rfonts is None:
                    rfonts = OxmlElement("w:rFonts")
                    rpr.append(rfonts)
                for attribute in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
                    rfonts.set(qn(attribute), MONO_FONT)
                paragraph.paragraph_format.space_after = Pt(0)
                paragraph.paragraph_format.line_spacing = 1.0
            _cant_split_row(table.rows[(1 if labelled else 0) + chunk_index])
        if keep_together:
            rows = self._rendered_code_rows(lines)
            estimated_pt = rows * CODE_LINE_HEIGHT_PT
            if estimated_pt > BODY_HEIGHT_PT:
                raise ValueError(
                    f"A {len(lines)}-line listing renders as about {rows} rows / {estimated_pt:.0f} pt "
                    f"and cannot be kept on one A4 page ({BODY_HEIGHT_PT:.0f} pt of body height)."
                )
            _cant_split(table)
        self._collapse(self.document.add_paragraph())
        return table

    # -------------------------------------------------------------- structures
    def _token_fit_sizes(
        self,
        headers: Sequence[str],
        rows: Sequence[Sequence[str]],
        widths: Sequence[float],
        font_size: float,
        columns: Sequence[int],
    ) -> list[float]:
        """Shrink named columns just enough that no identifier breaks mid-token.

        Word breaks inside a word only when the word cannot fit the cell, so an
        identifier such as ``DonationObservationSummaryForAgent`` splits across two
        lines in a column narrower than the word. Rather than guessing a width, the
        longest unbreakable token in each named column is measured and the font for
        that column alone is stepped down until it fits, with a readability floor.
        """
        section = self.document.sections[0]
        usable = section.page_width - section.left_margin - section.right_margin
        total = sum(widths)
        sizes = [font_size] * len(headers)
        for index in columns:
            longest = 0
            for row in rows:
                if index >= len(row):
                    continue
                for token in str(row[index] or "").replace("`", "").split():
                    longest = max(longest, len(token))
            if not longest:
                continue
            # Points available inside the cell, less the default cell margins.
            points = (usable * widths[index] / total) / 12700 - 2 * TABLE_CELL_MARGIN_PT
            size = font_size
            while size > TOKEN_FIT_MIN_PT and longest * size * MONO_ADVANCE_RATIO > points:
                size -= 0.2
            sizes[index] = round(size, 1)
        return sizes

    def table(
        self,
        headers: Sequence[str],
        rows: Sequence[Sequence[str]],
        *,
        caption: str,
        widths: Sequence[float] | None = None,
        font_size: float = 9.0,
        header_size: float = 9.0,
        keep_together: bool = False,
        keep_tail_rows: int = 0,
        pull_up: bool = False,
        min_row_height_cm: float | None = None,
        free_text_rows: set[int] | None = None,
        whole_token_columns: Sequence[int] | None = None,
    ):
        self.table_number += 1
        number = self.table_number
        if pull_up:
            # Bind the block above to this table so a short trailing table is not
            # left alone on a page of its own.
            self._keep_previous_with_next()
        table = self.document.add_table(rows=1, cols=len(headers))
        table.style = "Table Grid"
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        table.autofit = widths is None
        column_sizes = (
            self._token_fit_sizes(headers, rows, widths, font_size, whole_token_columns)
            if whole_token_columns and widths
            else None
        )

        header_cells = table.rows[0].cells
        for index, text in enumerate(headers):
            cell = header_cells[index]
            cell.text = ""
            paragraph = cell.paragraphs[0]
            run = paragraph.add_run(text)
            run.bold = True
            run.font.size = Pt(header_size)
            run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
            paragraph.paragraph_format.space_after = Pt(1)
            paragraph.paragraph_format.space_before = Pt(1)
            _shade(cell._tc.get_or_add_tcPr(), SHADE_HEADER)

        for row_index, row in enumerate(rows):
            cells = table.add_row().cells
            for column_index, value in enumerate(row):
                cell = cells[column_index]
                cell.text = ""
                first = True
                size = column_sizes[column_index] if column_sizes else font_size
                for line in ("" if value is None else str(value)).split("\n"):
                    paragraph = cell.paragraphs[0] if first else cell.add_paragraph()
                    first = False
                    self._rich(paragraph, line, size=size)
                    paragraph.paragraph_format.space_after = Pt(1)
                    paragraph.paragraph_format.space_before = Pt(1)
                    paragraph.paragraph_format.line_spacing = 1.05
            if row_index % 2 == 1:
                for cell in cells:
                    _shade(cell._tc.get_or_add_tcPr(), SHADE_BAND)

        if widths:
            table.autofit = False
            total = sum(widths)
            section = self.document.sections[0]
            usable = section.page_width - section.left_margin - section.right_margin
            for row in table.rows:
                for index, cell in enumerate(row.cells):
                    cell.width = Emu(int(usable * widths[index] / total))

        self._repeat_header(table)
        if min_row_height_cm:
            # A hand-written record row needs room for a line of handwriting. Word
            # only guarantees that with an explicit "at least" row height; a blank
            # cell otherwise collapses to a single text line. Rows that already
            # carry printed content (a verdict checkbox line) keep their natural
            # height, so the extra space goes where someone actually writes.
            height = Emu(int(min_row_height_cm * 360000))
            for index, row in enumerate(table.rows[1:], start=1):
                if free_text_rows is not None and index not in free_text_rows:
                    continue
                tr_pr = row._tr.get_or_add_trPr()
                tr_height = OxmlElement("w:trHeight")
                tr_height.set(qn("w:val"), str(int(height.twips)))
                tr_height.set(qn("w:hRule"), "atLeast")
                tr_pr.append(tr_height)
        if keep_together:
            # A short checklist reads as one unit: keeping every row with the next
            # stops Word from stranding a single row on a nearly empty page.
            for row in table.rows[:-1]:
                for cell in row.cells:
                    for paragraph in cell.paragraphs:
                        paragraph.paragraph_format.keep_with_next = True
        elif keep_tail_rows:
            # A long table cannot fit one page, but its continuation must still
            # carry a readable group. Binding the last ``keep_tail_rows`` rows to
            # each other (and, through the last row, to the caption) makes Word
            # move that whole group rather than a single orphan row.
            tail = table.rows[-keep_tail_rows:] if keep_tail_rows < len(table.rows) else table.rows
            for row in tail[:-1]:
                for cell in row.cells:
                    for paragraph in cell.paragraphs:
                        paragraph.paragraph_format.keep_with_next = True
        self._describe_table(table, f"表 {number}", caption)
        self._caption(f"表 {number}　{caption}")
        self.tables.append(f"表 {number}　{caption}")
        return table

    def _describe_table(self, table, title: str, description: str) -> None:
        """Give a data table an accessible title and description (Word table alt text)."""
        tbl_pr = table._tbl.tblPr
        caption = OxmlElement("w:tblCaption")
        caption.set(qn("w:val"), title)
        tbl_pr.append(caption)
        descr = OxmlElement("w:tblDescription")
        descr.set(qn("w:val"), description)
        tbl_pr.append(descr)

    def _repeat_header(self, table) -> None:
        header = table.rows[0]
        tr_pr = header._tr.get_or_add_trPr()
        repeat = OxmlElement("w:tblHeader")
        repeat.set(qn("w:val"), "true")
        tr_pr.append(repeat)
        _cant_split(table)
        # The last row must pull its caption with it, so the caption can never be
        # stranded at the top of the next page on its own.
        for cell in table.rows[-1].cells:
            for paragraph in cell.paragraphs:
                paragraph.paragraph_format.keep_with_next = True

    def _caption(self, text: str):
        paragraph = self.document.add_paragraph(style="Caption")
        run = paragraph.add_run(text)
        run.font.size = Pt(8.5)
        paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
        paragraph.paragraph_format.space_before = Pt(2)
        paragraph.paragraph_format.space_after = Pt(10)
        paragraph.paragraph_format.keep_lines = True
        return paragraph

    def figure(
        self,
        image: Path | io.BytesIO,
        *,
        caption: str,
        alt_text: str,
        width_ratio: float = 1.0,
        max_height_cm: float | None = None,
    ):
        self.figure_number += 1
        number = self.figure_number
        section = self.document.sections[0]
        usable = section.page_width - section.left_margin - section.right_margin
        paragraph = self.document.add_paragraph()
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        paragraph.paragraph_format.space_before = Pt(6)
        paragraph.paragraph_format.space_after = Pt(2)
        # Bind the caption to its figure: they always land on the same page.
        paragraph.paragraph_format.keep_with_next = True
        run = paragraph.add_run()
        source = str(image) if isinstance(image, Path) else image
        width = Emu(int(usable * width_ratio))
        pixel_width = _pixel_width(image)
        if pixel_width:
            # Stretching a small dialog capture to the full text width prints it at
            # 80-110 dpi, which turns UI labels into mush on paper. Cap the printed
            # width so the capture never falls below MIN_FIGURE_DPI; a small capture
            # simply prints smaller and stays sharp.
            limit = Emu(int(pixel_width / MIN_FIGURE_DPI * 914400))
            if limit < width:
                width = limit
        picture = run.add_picture(source, width=width)
        if max_height_cm is not None:
            limit = Emu(int(max_height_cm * 360000))
            if picture.height > limit:
                scale = limit / picture.height
                picture.height = limit
                picture.width = Emu(int(picture.width * scale))
        set_alt_text(picture, f"図 {number}", alt_text)
        self._caption(f"図 {number}　{caption}")
        self.figures.append(f"図 {number}　{caption}")
        return picture

    # ------------------------------------------------------------------ fields
    def field(self, paragraph, instruction: str, placeholder: str = "") -> None:
        """Write a real Word field.

        Each ``fldChar`` and the ``instrText`` must live in its own run: a run that
        mixes them is not recognised as a field, and Word then prints the raw
        instruction (``TOC \\o "1-3" \\h``) as literal body text instead of building
        the table of contents.
        """
        for kind in ("begin",):
            marker = OxmlElement("w:fldChar")
            marker.set(qn("w:fldCharType"), kind)
            paragraph.add_run()._r.append(marker)
        instr = OxmlElement("w:instrText")
        instr.set(qn("xml:space"), "preserve")
        instr.text = instruction
        paragraph.add_run()._r.append(instr)
        separate = OxmlElement("w:fldChar")
        separate.set(qn("w:fldCharType"), "separate")
        paragraph.add_run()._r.append(separate)
        if placeholder:
            paragraph.add_run(placeholder)
        end = OxmlElement("w:fldChar")
        end.set(qn("w:fldCharType"), "end")
        paragraph.add_run()._r.append(end)

    def table_of_contents(self, *, levels: str = "1-3") -> None:
        heading = self.document.add_paragraph(style="TOC Heading")
        heading.add_run("目次")
        paragraph = self.document.add_paragraph()
        paragraph.paragraph_format.space_after = Pt(0)
        paragraph.paragraph_format.space_before = Pt(0)
        self.field(paragraph, f'TOC \\o "{levels}" \\h \\z \\u', "［Word で開くと目次が生成されます］")
        # A next-page section break keeps the contents listing self-contained: the
        # first chapter always starts on a fresh page, even when the generated
        # listing fills its last page exactly. The paragraph that carries the break
        # is collapsed to a hairline so it never spills onto a page of its own.
        section = self.document.add_section(WD_SECTION.NEW_PAGE)
        section.header.is_linked_to_previous = True
        section.footer.is_linked_to_previous = True
        self._drop_cover_page_setup(section)
        self._collapse(self.document.paragraphs[-1])

    @staticmethod
    def _drop_cover_page_setup(section) -> None:
        """Remove the cover-only first-page settings from a later section.

        ``add_section`` clones the previous section properties, which carry the
        blank first-page header/footer used by the cover. Left in place, the first
        page of every following section would lose its running header and page
        number.
        """
        sect_pr = section._sectPr
        for tag in ("w:titlePg",):
            node = sect_pr.find(qn(tag))
            if node is not None:
                sect_pr.remove(node)
        for tag in ("w:headerReference", "w:footerReference"):
            for node in list(sect_pr.findall(qn(tag))):
                if node.get(qn("w:type")) == "first":
                    sect_pr.remove(node)

    @staticmethod
    def _collapse(paragraph) -> None:
        """Reduce an empty structural paragraph to a hairline.

        ``w:rPr`` is the second-to-last child of ``w:pPr`` in the schema, so it is
        inserted immediately before ``w:sectPr`` (or appended when there is none).
        Writing it anywhere else makes Word treat the document as damaged and
        repair it, which silently unlinks nearby fields.
        """
        paragraph.paragraph_format.space_before = Pt(0)
        paragraph.paragraph_format.space_after = Pt(0)
        paragraph.paragraph_format.line_spacing = Pt(1)
        p_pr = paragraph._p.get_or_add_pPr()
        r_pr = p_pr.find(qn("w:rPr"))
        if r_pr is None:
            r_pr = OxmlElement("w:rPr")
            sect_pr = p_pr.find(qn("w:sectPr"))
            if sect_pr is not None:
                sect_pr.addprevious(r_pr)
            else:
                p_pr.append(r_pr)
        for tag in ("w:sz", "w:szCs"):
            if r_pr.find(qn(tag)) is None:
                element = OxmlElement(tag)
                element.set(qn("w:val"), "2")
                r_pr.append(element)

    def page_break(self) -> None:
        self.document.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

    def update_fields_on_open(self) -> None:
        settings = self.document.settings.element
        existing = settings.find(qn("w:updateFields"))
        if existing is None:
            existing = OxmlElement("w:updateFields")
            settings.append(existing)
        existing.set(qn("w:val"), "true")

    def save(self, path: Path) -> Path:
        normalize_word_parentheses(self.document)
        save_atomically(lambda staged: self.document.save(str(staged)), path)
        return path


def cover_page(
    builder: DocumentBuilder,
    *,
    title: str,
    subtitle: str,
    version: str,
    tagline: str,
    footer_lines: Sequence[str],
    title_break_after: str | None = None,
) -> None:
    """Render the branded cover used by every deliverable.

    ``title_break_after`` inserts a manual line break at that point in the title so
    a Japanese term is never broken across two lines by automatic wrapping.
    """
    logo_paragraph = builder.document.add_paragraph()
    logo_paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
    logo_paragraph.paragraph_format.space_before = Pt(48)
    picture = logo_paragraph.add_run().add_picture(builder.carrier.cover_logo(), width=Emu(1500000))
    set_alt_text(picture, "Microsoft Fabric IQ", "Microsoft Fabric IQ ロゴ")

    heading = builder.document.add_paragraph(style="Title")
    if title_break_after and title_break_after in title:
        head, _, tail = title.partition(title_break_after)
        heading.add_run(head + title_break_after)
        heading.add_run().add_break(WD_BREAK.LINE)
        heading.add_run(tail.lstrip())
    else:
        heading.add_run(title)
    heading.paragraph_format.space_before = Pt(18)
    heading.paragraph_format.space_after = Pt(4)
    heading.paragraph_format.keep_with_next = True

    subtitle_paragraph = builder.paragraph(subtitle, size=12.5, color=BODY_GRAY, space_after=18)
    subtitle_paragraph.paragraph_format.line_spacing = 1.25

    version_paragraph = builder.document.add_paragraph()
    version_run = version_paragraph.add_run(f"v{version}")
    version_run.bold = True
    version_run.font.size = Pt(20)
    version_run.font.color.rgb = BRAND_TEAL
    version_paragraph.paragraph_format.space_after = Pt(2)

    builder.paragraph(tagline, size=11, color=BRAND_GRAY, space_after=26)
    for line in footer_lines:
        builder.paragraph(line, size=9.5, color=BRAND_GRAY, space_after=2)
    builder.page_break()
