"""Render every page of a generated DOCX and audit the resulting layout.

XML alone cannot prove that a document has no blank page, no page that carries
nothing but a caption, and no callout or listing that was torn across a page
break: those are layout outcomes, not markup. This module exports the document
to PDF with Word and inspects the rendered pages.

The audit is best effort. When Word or PyMuPDF is unavailable the caller reports
the limitation instead of failing the run.
"""

from __future__ import annotations

import contextlib
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence

#: A4 page geometry in points, matching the section properties the builders write.
PAGE_WIDTH_PT = 595.3
PAGE_HEIGHT_PT = 841.9
TOP_MARGIN_PT = 1134 / 20  # twips -> points
BOTTOM_MARGIN_PT = 1020 / 20

#: A body area with less ink than this is treated as blank.
BLANK_INK_RATIO = 0.01

#: A page whose body holds only caption text is a problem only when there is no
#: object on it. Two full-width screenshots plus their captions produce far more
#: ink than this, so the threshold separates a stranded caption from a figure page.
CAPTION_ONLY_INK_RATIO = 0.05

#: Screenshots of a mostly white dialog put very little ink on the page, so ink
#: alone cannot tell a figure page from a stranded caption. A body this much of
#: which is picture carries the figures the captions label: nothing is stranded.
CAPTION_PAGE_IMAGE_RATIO = 0.10

#: Caption paragraphs the layout must never leave alone on a page.
CAPTION_PATTERN = re.compile(r"^(?:表|図)\s*[0-9]+")


#: Characters Japanese line-breaking rules forbid at the start of a line. Limited
#: to closing punctuation, which is always avoidable: the長音符 and small kana of
#: the strict rule set are omitted because Word must break anywhere at all inside
#: a column that is narrower than the word. ``・`` is omitted too - the record
#: sheets start list items with it deliberately.
KINSOKU_LEADING = "。、）」』】〕》〉，．？！"

#: The 標準禁則 small kana and long-vowel mark, which must not start a line either.
#: Reported separately because Word yields on these inside a column that is too
#: narrow for the word, so they point at a layout fix rather than a settings bug.
KINSOKU_KANA_LEADING = "ーァィゥェォッャュョヮヵヶぁぃぅぇぉっゃゅょゎ々"


@dataclass
class PageReport:
    number: int
    ink_ratio: float
    body_text: str
    image_ratio: float = 0.0

    @property
    def is_blank(self) -> bool:
        return self.ink_ratio < BLANK_INK_RATIO

    @property
    def is_caption_only(self) -> bool:
        if self.image_ratio >= CAPTION_PAGE_IMAGE_RATIO:
            return False
        if self.ink_ratio >= CAPTION_ONLY_INK_RATIO:
            return False
        lines = [line.strip() for line in self.body_text.splitlines() if line.strip()]
        if not lines or len(lines) > 2:
            return False
        return all(CAPTION_PATTERN.match(line) for line in lines)

    @property
    def kinsoku_violations(self) -> list[str]:
        """Lines that open with a character Japanese typography forbids there."""
        offenders: list[str] = []
        for line in self.body_text.splitlines():
            stripped = line.strip().replace("\u2060", "")
            if stripped and stripped[0] in KINSOKU_LEADING:
                offenders.append(stripped[:24])
        return offenders

    @property
    def kana_line_starts(self) -> list[str]:
        """Lines opening with a small kana or the long-vowel mark (標準禁則)."""
        offenders: list[str] = []
        for line in self.body_text.splitlines():
            stripped = line.strip().replace("\u2060", "")
            if stripped and stripped[0] in KINSOKU_KANA_LEADING:
                offenders.append(stripped[:24])
        return offenders


#: Caption text that must never be separated from the listing it labels.
CODE_CAPTION_PATTERN = re.compile(r"^(?:KQL|Python|SQL|Pipeline|Agent instructions|Lakehouse|Eventhouse)[（(]")

#: A body page holding no more than this many lines, with almost no ink and no
#: picture, is a page a reader turns to for a single stranded note or table row.
SPARSE_PAGE_MAX_LINES = 12

#: A listing continuation page must carry the repeated label plus real code. At
#: or below this many lines in total it is a stub, not a page of listing.
CODE_CONTINUATION_MIN_LINES = 4
SPARSE_PAGE_INK_RATIO = 0.11
#: A page whose body is at least this much picture is a figure page, not a stub.
SPARSE_PAGE_IMAGE_RATIO = 0.10

#: A table continuation page carrying no more than this many lines in total (the
#: repeated header, one data row, the caption and perhaps a closing note) means a
#: single row was pushed over the page boundary on its own.
THIN_CONTINUATION_MAX_LINES = 10


@dataclass
class RenderReport:
    ok: bool
    detail: str
    pages: list[PageReport] = field(default_factory=list)

    @property
    def blank_pages(self) -> list[int]:
        return [page.number for page in self.pages if page.is_blank]

    @property
    def caption_only_pages(self) -> list[int]:
        return [page.number for page in self.pages if page.is_caption_only]

    @property
    def kinsoku_violations(self) -> list[tuple[int, str]]:
        return [
            (page.number, offender)
            for page in self.pages
            for offender in page.kinsoku_violations
        ]

    @property
    def kana_line_starts(self) -> list[tuple[int, str]]:
        return [
            (page.number, offender)
            for page in self.pages
            for offender in page.kana_line_starts
        ]

    def orphaned_code_captions(self) -> list[tuple[int, str]]:
        """Listing labels that open a page with almost no listing under them.

        The label is the listing's repeating header row, so it is *expected* to
        open every continuation page - that is the cue telling the reader what the
        code overleaf belongs to. What is still a defect is a label followed by a
        stub: two lines of code under a header is a page that should not exist.
        """
        orphans: list[tuple[int, str]] = []
        for page in self.pages:
            lines = [line.strip() for line in page.body_text.splitlines() if line.strip()]
            if lines and CODE_CAPTION_PATTERN.match(lines[0]) and len(lines) <= CODE_CONTINUATION_MIN_LINES:
                orphans.append((page.number, f"{lines[0][:40]} + {len(lines) - 1} line(s)"))
        return orphans

    def sparse_pages(self, *, skip_before: int = 1) -> list[tuple[int, int, float]]:
        """Body pages that carry almost nothing - a stranded callout or table tail.

        A page dominated by a screenshot or a diagram is not sparse even though a
        picture puts little ink on the page, so image coverage is measured rather
        than inferred from the presence of a caption. Front matter is excluded: the
        cover and the contents listing are legitimately sparse.
        """
        sparse: list[tuple[int, int, float]] = []
        for page in self.pages:
            if page.number < skip_before:
                continue
            lines = [line.strip() for line in page.body_text.splitlines() if line.strip()]
            if not lines or len(lines) > SPARSE_PAGE_MAX_LINES:
                continue
            if page.ink_ratio >= SPARSE_PAGE_INK_RATIO:
                continue
            if page.image_ratio >= SPARSE_PAGE_IMAGE_RATIO:
                continue
            sparse.append((page.number, len(lines), round(page.ink_ratio, 4)))
        return sparse

    def split_terms(self, terms: Sequence[str]) -> list[tuple[int, str]]:
        """Terms broken across a line boundary in the rendered page."""
        broken: list[tuple[int, str]] = []
        for page in self.pages:
            lines = [line.strip() for line in page.body_text.splitlines() if line.strip()]
            for first, second in zip(lines, lines[1:]):
                for term in terms:
                    for cut in range(1, len(term)):
                        if first.endswith(term[:cut]) and second.startswith(term[cut:]):
                            broken.append((page.number, term))
                            break
        return broken

    def orphan_headings(self, titles: Sequence[str]) -> list[tuple[int, str]]:
        """Chapter headings that are the last thing on a page.

        A chapter title with none of its own text under it reads as a mistake, so a
        heading that is allowed to flow onto the previous chapter's closing page
        must still pull its first paragraph with it. Matching is on the exact
        heading text, so a contents entry (which carries a dot leader and a page
        number) and a numbered list item are never mistaken for one.
        """
        wanted = {title.strip() for title in titles}
        orphans: list[tuple[int, str]] = []
        for page in self.pages:
            lines = [line.strip() for line in page.body_text.splitlines() if line.strip()]
            if lines and lines[-1] in wanted:
                orphans.append((page.number, lines[-1][:44]))
        return orphans

    def thin_table_continuations(self, headers: Sequence[str]) -> list[tuple[int, str, float]]:
        """Pages that continue a table with a single data row and little else.

        A continuation page is identified by its first line repeating a table
        header. If almost nothing follows that header, the reader turned a page for
        one row.
        """
        wanted = {header.strip() for header in headers if header.strip()}
        thin: list[tuple[int, str, float]] = []
        for page in self.pages:
            lines = [line.strip() for line in page.body_text.splitlines() if line.strip()]
            if not lines or lines[0] not in wanted:
                continue
            if page.ink_ratio >= SPARSE_PAGE_INK_RATIO or page.image_ratio >= SPARSE_PAGE_IMAGE_RATIO:
                continue
            if len(lines) <= THIN_CONTINUATION_MAX_LINES:
                thin.append((page.number, lines[0][:28], round(page.ink_ratio, 4)))
        return thin

    def pages_containing(self, needle: str) -> list[int]:
        return [page.number for page in self.pages if needle in page.body_text]


def export_pdf(source: Path, target: Path) -> str | None:
    """Export ``source`` to PDF with Word. Returns an error message on failure."""
    try:
        import pythoncom  # type: ignore
        import win32com.client  # type: ignore
    except Exception as error:  # pragma: no cover - depends on the host
        return f"pywin32 unavailable ({error.__class__.__name__})"

    pythoncom.CoInitialize()
    application = None
    try:
        application = win32com.client.DispatchEx("Word.Application")
        application.Visible = False
        application.DisplayAlerts = 0
        document = application.Documents.Open(
            str(source.resolve()), ConfirmConversions=False, ReadOnly=True, AddToRecentFiles=False
        )
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            document.ExportAsFixedFormat(str(target.resolve()), 17)  # wdExportFormatPDF
        finally:
            document.Close(SaveChanges=0)
        return None
    except Exception as error:  # pragma: no cover - depends on the host
        return f"Word export failed: {error}"
    finally:
        if application is not None:
            with contextlib.suppress(Exception):
                application.Quit()
        with contextlib.suppress(Exception):
            pythoncom.CoUninitialize()


def audit(source: Path, scratch: Path) -> RenderReport:
    """Render every page of ``source`` and report blank / caption-only pages."""
    try:
        import fitz  # type: ignore
    except Exception as error:  # pragma: no cover - depends on the host
        return RenderReport(False, f"PyMuPDF unavailable ({error.__class__.__name__})")

    pdf_path = scratch / f"{source.stem}.pdf"
    failure = export_pdf(source, pdf_path)
    if failure:
        return RenderReport(False, failure)

    pages: list[PageReport] = []
    with fitz.open(str(pdf_path)) as document:
        for index, page in enumerate(document, start=1):
            rect = page.rect
            body = fitz.Rect(
                rect.x0,
                rect.y0 + TOP_MARGIN_PT,
                rect.x1,
                rect.y1 - BOTTOM_MARGIN_PT,
            )
            pixmap = page.get_pixmap(clip=body, colorspace=fitz.csGRAY, dpi=72)
            samples = pixmap.samples
            ink = sum(1 for value in samples if value < 250)
            ratio = ink / len(samples) if samples else 0.0
            covered = 0.0
            for image in page.get_images(full=True):
                try:
                    bbox = fitz.Rect(page.get_image_bbox(image))
                except Exception:  # pragma: no cover - malformed placement
                    continue
                covered += (bbox & body).get_area()
            image_ratio = covered / body.get_area() if body.get_area() else 0.0
            pages.append(PageReport(index, ratio, page.get_text("text", clip=body), image_ratio))
    with contextlib.suppress(Exception):
        pdf_path.unlink()
    return RenderReport(True, f"{len(pages)} pages rendered and inspected", pages)
