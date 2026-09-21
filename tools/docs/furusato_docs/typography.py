"""Display-only punctuation shared by Word and HTML; runtime inputs stay unchanged."""

from __future__ import annotations

from docx.opc.part import XmlPart

PARENTHESES = str.maketrans({"\uff08": "(", "\uff09": ")"})
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
WP = "{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}"
PIC = "{http://schemas.openxmlformats.org/drawingml/2006/picture}"
DC = "{http://purl.org/dc/elements/1.1/}"
CP = "{http://schemas.openxmlformats.org/package/2006/metadata/core-properties}"

TEXT_TAGS = {
    W + "t", A + "t",
    *(DC + name for name in ("title", "subject", "description")),
    *(CP + name for name in ("keywords", "category", "contentStatus")),
}
TEXT_ATTRIBUTES = {
    WP + "docPr": ("name", "descr", "title"),
    PIC + "cNvPr": ("name", "descr", "title"),
    W + "tblCaption": (W + "val",),
    W + "tblDescription": (W + "val",),
}


def ascii_parentheses(text: str) -> str:
    """Replace only U+FF08/U+FF09, preserving all other characters and spacing."""
    return text.translate(PARENTHESES)


def normalize_word_parentheses(document) -> None:
    """Normalize editable stories/labels without touching URLs, styles or images."""
    for part in document.part.package.parts:
        if not isinstance(part, XmlPart):
            continue
        for node in part.element.iter():
            if node.tag in TEXT_TAGS and node.text is not None:
                node.text = ascii_parentheses(node.text)
            for attribute in TEXT_ATTRIBUTES.get(node.tag, ()):
                value = node.get(attribute)
                if value is not None:
                    node.set(attribute, ascii_parentheses(value))
