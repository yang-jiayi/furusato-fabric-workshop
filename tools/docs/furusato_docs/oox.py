"""OOXML package helpers: template derivation, media reuse, labels and properties.

The branded shell is built from the maintained ``tools/docs/assets/style-carrier.zip``
asset, which holds the styles, theme, numbering, settings, header, footer, cover and
header logos, the Purview label part and the page setup. That asset was derived once
from the superseded v2.6.0 participant DOCX and is now maintained in this repository;
the v2.6 deliverable is not a build input and does not need to exist for a clean
checkout to rebuild or validate the v2.7.0 documents.
"""

from __future__ import annotations

import io
import json
import re
import shutil
import zipfile

from pathlib import Path
from typing import Iterable
from xml.sax.saxutils import escape

from docx.oxml.ns import qn

from .reproducible import (
    build_timestamp,
    canonicalise_office_identifiers,
    save_atomically,
    write_package,
)

# Parts copied verbatim from the style carrier.
CARRIED_PARTS = (
    "word/styles.xml",
    "word/theme/theme1.xml",
    "word/numbering.xml",
    "word/settings.xml",
    "word/webSettings.xml",
    "word/fontTable.xml",
    "word/header1.xml",
    "word/footer1.xml",
    "word/_rels/header1.xml.rels",
    "word/footnotes.xml",
    "word/endnotes.xml",
    "docMetadata/LabelInfo.xml",
)

HEADER_LOGO_PART = "word/media/image149.png"
COVER_LOGO_PART = "word/media/image1.png"

#: The single approved Purview classification carried by every deliverable. It is
#: the non-protective "General" label: it marks the documents but does not encrypt
#: them, so the packages stay standard, readable OOXML.
#:
#: ``docMetadata/LabelInfo.xml`` is authoritative. The legacy ``MSIP_Label_*``
#: custom properties are regenerated from these same constants so the two can never
#: disagree: Word and Excel stamp the *signing machine's* tenant default label into
#: ``docProps/custom.xml`` on every COM save, which is why the deliverables are
#: normalised after the last COM pass rather than before it.
LABEL_ID = "f42aa342-8706-4288-bd11-ebb85995028c"
LABEL_SITE_ID = "72f988bf-86f1-41af-91ab-2d7cd011db47"
LABEL_NAME = "General"
LABEL_METHOD = "Privileged"
LABEL_CONTENT_BITS = "0"
#: Fixed so two builds of the same content produce byte-identical property parts.
LABEL_SET_DATE = "2026-08-14T00:00:00Z"

DOCUMENT_AUTHOR = "Furusato Fabric Workshop"

LABEL_INFO_XML = (
    '<?xml version="1.0" encoding="utf-8" standalone="yes"?>'
    '<clbl:labelList xmlns:clbl="http://schemas.microsoft.com/office/2020/mipLabelMetadata">'
    f'<clbl:label id="{{{LABEL_ID}}}" enabled="1" method="{LABEL_METHOD}" '
    f'siteId="{{{LABEL_SITE_ID}}}" contentBits="{LABEL_CONTENT_BITS}" removed="0" />'
    "</clbl:labelList>"
).encode("utf-8")


def custom_properties_xml() -> bytes:
    """The legacy ``MSIP_Label_*`` property set for the approved General label.

    Only the properties modern Office reads are emitted: ``ActionId`` and ``Tag``
    identify a particular labelling *event* on a particular tenant and would be
    meaningless — and misleading — on a deterministically rebuilt file.
    """
    values = (
        ("Enabled", "true"),
        ("SetDate", LABEL_SET_DATE),
        ("Method", LABEL_METHOD),
        ("Name", LABEL_NAME),
        ("SiteId", LABEL_SITE_ID),
        ("ContentBits", LABEL_CONTENT_BITS),
    )
    properties = "".join(
        f'<property fmtid="{{D5CDD505-2E9C-101B-9397-08002B2CF9AE}}" pid="{index}" '
        f'name="MSIP_Label_{LABEL_ID}_{suffix}"><vt:lpwstr>{escape(value)}</vt:lpwstr></property>'
        for index, (suffix, value) in enumerate(values, start=2)
    )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/custom-properties" '
        'xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">'
        f"{properties}</Properties>"
    ).encode("utf-8")


#: A4 portrait in twips. The style carrier was authored on US Letter; every
#: deliverable in this repository is printed on A4, so the page size, the header
#: and footer right-tab stops and the workbook page setup are all normalised to
#: A4 by the builders rather than by hand-editing the carrier asset.
A4_WIDTH_TWIPS = 11906
A4_HEIGHT_TWIPS = 16838

#: Japanese typography defaults written into ``styles.xml``/``settings.xml``.
#: Word applies most of these implicitly, but the deliverables must not depend on
#: an implicit default that a viewer or a converter may resolve differently.
JAPANESE_PARAGRAPH_DEFAULTS = (
    ("w:kinsoku", "true"),
    ("w:wordWrap", "true"),
    ("w:overflowPunct", "true"),
    ("w:topLinePunct", "false"),
    ("w:autoSpaceDE", "true"),
    ("w:autoSpaceDN", "true"),
)
CHARACTER_SPACING_CONTROL = "compressPunctuation"

#: Word applies Japanese line-breaking (kinsoku) only where the East Asian
#: language is Japanese. The style carrier declared ``en-US``.
EAST_ASIAN_LANGUAGE = "ja-JP"

#: The standard Japanese kinsoku sets, declared explicitly instead of relying on
#: Word's built-in default for the document language. ``noLineBreaksBefore`` is
#: the 行頭禁則 set (a line may not start with these: closing punctuation, small
#: kana, the long-vowel mark); ``noLineBreaksAfter`` is the 行末禁則 set (a line
#: may not end with these: opening punctuation).
KINSOKU_NO_BREAK_BEFORE = (
    "!%),.:;?]}\u00a2\u2030\u2103\uff01\uff05\uff09\uff0c\uff0e\uff1a\uff1b\uff1f\uff3d\uff5d"
    "\u2019\u201d\u3001\u3002\u3005\u3009\u300b\u300d\u300f\u3011\u3015"
    "\u3041\u3043\u3045\u3047\u3049\u3063\u3083\u3085\u3087\u308e\u309b\u309c\u309d\u309e"
    "\u30a1\u30a3\u30a5\u30a7\u30a9\u30c3\u30e3\u30e5\u30e7\u30ee\u30f5\u30f6\u30fc\u30fd\u30fe"
    "\uff61\uff63\uff64\uff65\uff67\uff68\uff69\uff6a\uff6b\uff6c\uff6d\uff6e\uff6f\uff70\uff9e\uff9f"
)
KINSOKU_NO_BREAK_AFTER = (
    "$([\\{\u00a3\u00a5\uff04\uff08\uff3b\uff5b\u2018\u201c\u3008\u300a\u300c\u300e\u3010\u3014\uff62"
)

_DOCUMENT_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:wpc="http://schemas.microsoft.com/office/word/2010/wordprocessingCanvas" \
xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006" \
xmlns:o="urn:schemas-microsoft-com:office:office" \
xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" \
xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math" \
xmlns:v="urn:schemas-microsoft-com:vml" \
xmlns:wp14="http://schemas.microsoft.com/office/word/2010/wordprocessingDrawing" \
xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" \
xmlns:w10="urn:schemas-microsoft-com:office:word" \
xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" \
xmlns:w14="http://schemas.microsoft.com/office/word/2010/wordml" \
xmlns:w15="http://schemas.microsoft.com/office/word/2012/wordml" \
xmlns:wpg="http://schemas.microsoft.com/office/word/2010/wordprocessingGroup" \
xmlns:wpi="http://schemas.microsoft.com/office/word/2010/wordprocessingInk" \
xmlns:wne="http://schemas.microsoft.com/office/word/2006/wordml" \
xmlns:wps="http://schemas.microsoft.com/office/word/2010/wordprocessingShape" \
mc:Ignorable="w14 w15 wp14"><w:body>{sectpr}</w:body></w:document>"""

_DOCUMENT_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\
<Relationship Id="rIdStyles" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>\
<Relationship Id="rIdSettings" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/settings" Target="settings.xml"/>\
<Relationship Id="rIdWebSettings" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/webSettings" Target="webSettings.xml"/>\
<Relationship Id="rIdFontTable" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/fontTable" Target="fontTable.xml"/>\
<Relationship Id="rIdTheme" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme" Target="theme/theme1.xml"/>\
<Relationship Id="rIdNumbering" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/numbering" Target="numbering.xml"/>\
<Relationship Id="rIdFootnotes" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footnotes" Target="footnotes.xml"/>\
<Relationship Id="rIdEndnotes" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/endnotes" Target="endnotes.xml"/>\
<Relationship Id="rIdHeader1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/header" Target="header1.xml"/>\
<Relationship Id="rIdFooter1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer" Target="footer1.xml"/>\
<Relationship Id="rIdHeaderCover" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/header" Target="header2.xml"/>\
<Relationship Id="rIdFooterCover" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer" Target="footer2.xml"/>\
</Relationships>"""

_NS_DECL = (
    'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
    'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
)

#: Empty first-page header/footer. The cover carries its own branding, so it must
#: not repeat the running header and must not print a page number.
_COVER_HEADER_XML = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    f"<w:hdr {_NS_DECL}><w:p/></w:hdr>"
)
_COVER_FOOTER_XML = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    f"<w:ftr {_NS_DECL}><w:p/></w:ftr>"
)

_CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">\
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>\
<Default Extension="xml" ContentType="application/xml"/>\
<Default Extension="png" ContentType="image/png"/>\
<Default Extension="jpeg" ContentType="image/jpeg"/>\
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>\
<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>\
<Override PartName="/word/settings.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.settings+xml"/>\
<Override PartName="/word/webSettings.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.webSettings+xml"/>\
<Override PartName="/word/fontTable.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.fontTable+xml"/>\
<Override PartName="/word/numbering.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.numbering+xml"/>\
<Override PartName="/word/footnotes.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footnotes+xml"/>\
<Override PartName="/word/endnotes.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.endnotes+xml"/>\
<Override PartName="/word/header1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.header+xml"/>\
<Override PartName="/word/footer1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/>\
<Override PartName="/word/header2.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.header+xml"/>\
<Override PartName="/word/footer2.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/>\
<Override PartName="/word/theme/theme1.xml" ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/>\
<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>\
<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>\
<Override PartName="/docProps/custom.xml" ContentType="application/vnd.openxmlformats-officedocument.custom-properties+xml"/>\
<Override PartName="/docMetadata/LabelInfo.xml" ContentType="application/vnd.ms-office.classificationlabels+xml"/>\
</Types>"""

_PACKAGE_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>\
<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>\
<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>\
<Relationship Id="rId4" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/custom-properties" Target="docProps/custom.xml"/>\
<Relationship Id="rId5" Type="http://schemas.microsoft.com/office/2020/02/relationships/classificationlabels" Target="docMetadata/LabelInfo.xml"/>\
</Relationships>"""

_APP_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" \
xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">\
<Template>Normal</Template><TotalTime>0</TotalTime><Application>Microsoft Office Word</Application>\
<DocSecurity>0</DocSecurity><ScaleCrop>false</ScaleCrop><Company></Company>\
<LinksUpToDate>false</LinksUpToDate><SharedDoc>false</SharedDoc><HyperlinksChanged>false</HyperlinksChanged>\
<AppVersion>16.0000</AppVersion></Properties>"""


class StyleCarrier:
    """Reads the v2.6 participant DOCX and produces an empty v2.7 shell."""

    FIGURE_TAG = re.compile(r"^図\s*([0-9]+-[0-9]+)")

    #: Name of the compact, self-contained carrier archive produced by
    #: ``tools/docs/make_style_carrier.py``. It is the only style/media input the
    #: build needs, so a clean v2.7 checkout rebuilds without any superseded
    #: deliverable being present.
    ARCHIVE_NAME = "style-carrier.zip"

    #: Parts the shell writer requires from whichever carrier is in use.
    REQUIRED_PARTS = CARRIED_PARTS + (HEADER_LOGO_PART, COVER_LOGO_PART, "docProps/custom.xml")

    @classmethod
    def archive_path(cls, root: Path) -> Path:
        return root / "tools" / "docs" / "assets" / cls.ARCHIVE_NAME

    @classmethod
    def resolve(cls, root: Path) -> "StyleCarrier":
        """Return the maintained style carrier asset.

        The build deliberately has no fallback to a superseded participant
        document: the asset under ``tools/docs/assets`` is the maintained input.
        """
        archive = cls.archive_path(root)
        if not archive.is_file():
            raise FileNotFoundError(
                f"Style carrier asset not found: {archive}. "
                "Regenerate it with 'python tools/docs/make_style_carrier.py --source <styled.docx>'."
            )
        return CompactStyleCarrier(archive)

    def __init__(self, source: Path):
        self.source = source
        with zipfile.ZipFile(source) as archive:
            self._parts = {name: archive.read(name) for name in archive.namelist()}
        self._sectpr = self._extract_sectpr()
        self._screenshots = self._index_screenshots()
        self.used_tags: set[str] = set()

    # ------------------------------------------------------- A4 / typography
    @staticmethod
    def _to_a4(sectpr: str) -> str:
        """Force A4 portrait and keep the header/footer right tab on the margin."""
        sectpr = re.sub(
            r'<w:pgSz\b[^/]*/>',
            f'<w:pgSz w:w="{A4_WIDTH_TWIPS}" w:h="{A4_HEIGHT_TWIPS}"/>',
            sectpr,
        )
        if "<w:pgSz" not in sectpr:
            raise RuntimeError("The style carrier sectPr has no pgSz to normalise.")
        return sectpr

    @classmethod
    def usable_width_twips(cls, sectpr: str) -> int:
        margins = re.search(r'<w:pgMar\b[^/]*/>', sectpr)
        left = right = 1134
        if margins:
            found_left = re.search(r'w:left="([0-9]+)"', margins.group(0))
            found_right = re.search(r'w:right="([0-9]+)"', margins.group(0))
            left = int(found_left.group(1)) if found_left else left
            right = int(found_right.group(1)) if found_right else right
        return A4_WIDTH_TWIPS - left - right

    @classmethod
    def _retab(cls, xml: str, position: int) -> str:
        """Move every right tab stop in a header/footer part onto the A4 margin."""
        return re.sub(
            r'(<w:tab w:val="right" w:pos=")[0-9]+(")',
            lambda match: f"{match.group(1)}{position}{match.group(2)}",
            xml,
        )

    @classmethod
    def _japanese_typography(cls, styles_xml: str) -> str:
        """Write the kinsoku / overflow-punctuation defaults into ``docDefaults``.

        The East Asian language is set to ``ja-JP`` at the same time. Word only
        applies Japanese line-breaking rules to runs whose East Asian language is
        Japanese; the style carrier declared ``en-US``, which silently disabled
        kinsoku no matter how the paragraph properties were written.
        """
        styles_xml = cls._east_asian_language(styles_xml)
        elements = "".join(
            f'<{name} w:val="{value}"/>' for name, value in JAPANESE_PARAGRAPH_DEFAULTS
        )
        match = re.search(r"<w:pPrDefault>\s*<w:pPr>", styles_xml)
        if match:
            for name, _ in JAPANESE_PARAGRAPH_DEFAULTS:
                styles_xml = re.sub(rf"<{name}\b[^>]*/>", "", styles_xml, count=1)
            match = re.search(r"(<w:pPrDefault>\s*<w:pPr>)", styles_xml)
            return styles_xml[: match.end(1)] + elements + styles_xml[match.end(1) :]
        return styles_xml.replace(
            "</w:docDefaults>",
            f"<w:pPrDefault><w:pPr>{elements}</w:pPr></w:pPrDefault></w:docDefaults>",
        )

    @staticmethod
    def _east_asian_language(styles_xml: str) -> str:
        """Declare Japanese as the East Asian language everywhere in the styles."""
        return re.sub(
            r'(<w:lang\b[^>]*?w:eastAsia=")[^"]*(")',
            rf"\1{EAST_ASIAN_LANGUAGE}\2",
            styles_xml,
        )

    @classmethod
    def _settings_typography(cls, settings_xml: str) -> str:
        """Normalise the settings that control Japanese line breaking.

        ``strictFirstAndLastChars`` selects Word's strict kinsoku set, which adds
        the long-vowel mark and the small kana to the characters that may not begin
        a line. In CT_Settings it follows ``characterSpacingControl`` immediately;
        inserting it before that element makes Word repair the part and silently
        drop the whole typography block.
        """
        replacement = f'<w:characterSpacingControl w:val="{CHARACTER_SPACING_CONTROL}"/>'
        if "<w:characterSpacingControl" in settings_xml:
            settings_xml = re.sub(r"<w:characterSpacingControl[^>]*/>", replacement, settings_xml)
        else:
            settings_xml = settings_xml.replace("</w:settings>", replacement + "</w:settings>")
        settings_xml = re.sub(r"<w:strictFirstAndLastChars[^>]*/>", "", settings_xml)
        settings_xml = settings_xml.replace(
            replacement, replacement + '<w:strictFirstAndLastChars w:val="true"/>', 1
        )
        return re.sub(
            r'(<w:themeFontLang\b[^>]*?w:eastAsia=")[^"]*(")',
            rf"\1{EAST_ASIAN_LANGUAGE}\2",
            settings_xml,
        )

    def _normalised_parts(self) -> dict[str, bytes]:
        """Return the carried parts with A4 page setup and Japanese typography."""
        sectpr = self._to_a4(self._sectpr)
        tab = self.usable_width_twips(sectpr)
        parts = dict(self._parts)
        for name in ("word/header1.xml", "word/footer1.xml"):
            parts[name] = self._retab(parts[name].decode("utf-8"), tab).encode("utf-8")
        parts["word/styles.xml"] = self._japanese_typography(
            parts["word/styles.xml"].decode("utf-8")
        ).encode("utf-8")
        parts["word/settings.xml"] = self._settings_typography(
            parts["word/settings.xml"].decode("utf-8")
        ).encode("utf-8")
        return parts

    # ------------------------------------------------------------------ parts
    def _extract_sectpr(self) -> str:
        document = self._parts["word/document.xml"].decode("utf-8")
        match = re.search(r"<w:sectPr\b.*?</w:sectPr>", document, re.S)
        if not match:
            raise RuntimeError("The style carrier has no sectPr.")
        sectpr = match.group(0)
        sectpr = re.sub(
            r'(<w:headerReference[^>]*r:id=")[^"]+(")', r"\1rIdHeader1\2", sectpr
        )
        sectpr = re.sub(
            r'(<w:footerReference[^>]*r:id=")[^"]+(")', r"\1rIdFooter1\2", sectpr
        )
        sectpr = re.sub(r'\sw:rsidR="[0-9A-Fa-f]+"', "", sectpr, count=1)
        return sectpr

    def _cover_sectpr(self) -> str:
        """A4 sectPr with a blank first page header/footer for the cover."""
        sectpr = self._to_a4(self._sectpr)
        sectpr = sectpr.replace(
            '<w:footerReference w:type="default" r:id="rIdFooter1"/>',
            '<w:footerReference w:type="default" r:id="rIdFooter1"/>'
            '<w:headerReference w:type="first" r:id="rIdHeaderCover"/>'
            '<w:footerReference w:type="first" r:id="rIdFooterCover"/>',
        )
        return sectpr.replace("<w:cols ", "<w:titlePg/><w:cols ")

    def _index_screenshots(self) -> dict[str, bytes]:
        """Map the v2.6 figure tag (for example ``5-1``) to its PNG bytes."""
        document = self._parts["word/document.xml"].decode("utf-8")
        rels = self._parts["word/_rels/document.xml.rels"].decode("utf-8")
        targets = dict(re.findall(r'Id="([^"]+)"[^>]*?Target="(media/[^"]+)"', rels))
        index: dict[str, bytes] = {}
        for block in re.findall(r"<w:drawing>.*?</w:drawing>", document, re.S):
            descr = re.search(r'<wp:docPr[^>]*descr="([^"]*)"', block)
            embed = re.search(r'<a:blip r:embed="([^"]+)"', block)
            if not descr or not embed:
                continue
            tag = self.FIGURE_TAG.match(descr.group(1).replace("\u3000", " "))
            if not tag:
                continue
            target = targets.get(embed.group(1))
            if target:
                index[tag.group(1)] = self._parts[f"word/{target}"]
        return index

    # ---------------------------------------------------------------- exports
    #: The v2.6 captures are full-window Fabric screenshots. The top strip holds the
    #: item tab bar, which still lists superseded v2.6 items. It carries no
    #: instructional value, so it is cropped off every reused screenshot.
    TAB_STRIP_RATIO = 0.05

    def screenshot(self, tag: str) -> io.BytesIO:
        """Return the reusable v2.6 Fabric UI screenshot registered under ``tag``."""
        if tag not in self._screenshots:
            raise KeyError(f"v2.6 figure {tag} is not available for reuse.")
        self.used_tags.add(tag)
        return self._crop_tab_strip(self._screenshots[tag])

    @classmethod
    def _crop_tab_strip(cls, blob: bytes) -> io.BytesIO:
        try:
            from PIL import Image
        except ImportError:  # pragma: no cover - Pillow is a build requirement
            return io.BytesIO(blob)
        with Image.open(io.BytesIO(blob)) as image:
            top = int(image.height * cls.TAB_STRIP_RATIO)
            cropped = image.crop((0, top, image.width, image.height))
            buffer = io.BytesIO()
            cropped.save(buffer, format="PNG", optimize=True)
        buffer.seek(0)
        return buffer

    @property
    def available_screenshots(self) -> list[str]:
        return sorted(self._screenshots)

    def cover_logo(self) -> io.BytesIO:
        return io.BytesIO(self._parts[COVER_LOGO_PART])

    def label_info(self) -> bytes:
        """The approved label part, generated rather than carried.

        The carrier archive stores a copy so the asset is self-describing, but the
        build never trusts a stored blob for a security-relevant value.
        """
        return LABEL_INFO_XML

    def custom_properties(self) -> bytes:
        return custom_properties_xml()

    def build_shell(self, target: Path) -> Path:
        """Write an empty, branded A4 DOCX shell to ``target`` and return the path."""
        target.parent.mkdir(parents=True, exist_ok=True)
        parts = self._normalised_parts()
        shell = {
            "[Content_Types].xml": _CONTENT_TYPES.encode("utf-8"),
            "_rels/.rels": _PACKAGE_RELS.encode("utf-8"),
            "word/document.xml": _DOCUMENT_XML.format(sectpr=self._cover_sectpr()).encode("utf-8"),
            "word/_rels/document.xml.rels": _DOCUMENT_RELS.encode("utf-8"),
            **{name: parts[name] for name in CARRIED_PARTS},
            "word/header2.xml": _COVER_HEADER_XML.encode("utf-8"),
            "word/footer2.xml": _COVER_FOOTER_XML.encode("utf-8"),
            HEADER_LOGO_PART: parts[HEADER_LOGO_PART],
            "docProps/app.xml": _APP_XML.encode("utf-8"),
            "docProps/core.xml": core_properties_xml("", "", "", "").encode("utf-8"),
            "docProps/custom.xml": custom_properties_xml(),
        }
        write_package(target, shell)
        return target

    def export_archive(self, target: Path, tags: Iterable[str]) -> Path:
        """Write a compact carrier archive holding only the parts the build needs."""
        target.parent.mkdir(parents=True, exist_ok=True)
        wanted = sorted(set(tags))
        index = {
            "description": (
                "Compact style carrier for the Furusato workshop Word deliverables. "
                "Holds the branded OOXML shell parts and the Fabric UI screenshots the "
                "v2.7.0 participant guide reuses. Screenshots are already cropped to remove "
                "the superseded item tab strip."
            ),
            "sectPr": self._sectpr,
            "screenshots": wanted,
        }
        carrier = {"index.json": json.dumps(index, ensure_ascii=False, indent=1).encode("utf-8")}
        for name in CARRIED_PARTS:
            blob = LABEL_INFO_XML if name == "docMetadata/LabelInfo.xml" else self._parts[name]
            carrier[f"parts/{name}"] = blob
        carrier[f"parts/{HEADER_LOGO_PART}"] = self._parts[HEADER_LOGO_PART]
        carrier[f"parts/{COVER_LOGO_PART}"] = self._parts[COVER_LOGO_PART]
        carrier["parts/docProps/custom.xml"] = custom_properties_xml()
        for tag in wanted:
            carrier[f"screenshots/{tag}.png"] = self.screenshot(tag).getvalue()
        write_package(target, carrier)
        return target


class CompactStyleCarrier(StyleCarrier):
    """Style carrier backed by the maintained ``tools/docs/assets/style-carrier.zip``."""

    def __init__(self, source: Path):  # noqa: D107 - see StyleCarrier
        self.source = source
        with zipfile.ZipFile(source) as archive:
            names = set(archive.namelist())
            if "index.json" not in names:
                raise ValueError(f"{source.name} has no index.json; regenerate it.")
            index = json.loads(archive.read("index.json"))
            self._parts = {
                name[len("parts/") :]: archive.read(name)
                for name in archive.namelist()
                if name.startswith("parts/")
            }
            missing_screenshots = [
                tag for tag in index["screenshots"] if f"screenshots/{tag}.png" not in names
            ]
            if missing_screenshots:
                raise ValueError(f"{source.name} is missing screenshots: {missing_screenshots}")
            self._screenshots = {
                tag: archive.read(f"screenshots/{tag}.png") for tag in index["screenshots"]
            }
        missing_parts = [name for name in self.REQUIRED_PARTS if name not in self._parts]
        if missing_parts:
            raise ValueError(f"{source.name} is missing required parts: {missing_parts}")
        self._sectpr = index["sectPr"]
        self.used_tags: set[str] = set()

    def screenshot(self, tag: str) -> io.BytesIO:
        if tag not in self._screenshots:
            raise KeyError(
                f"Screenshot {tag} is not in {self.source.name}. "
                "Regenerate it with tools/docs/make_style_carrier.py."
            )
        self.used_tags.add(tag)
        return io.BytesIO(self._screenshots[tag])

    @property
    def screenshot_count(self) -> int:
        return len(self._screenshots)


def core_properties_xml(title: str, subject: str, keywords: str, description: str) -> str:
    now = build_timestamp()
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
        'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" '
        'xmlns:dcmitype="http://purl.org/dc/dcmitype/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
        f"<dc:title>{escape(title)}</dc:title>"
        f"<dc:subject>{escape(subject)}</dc:subject>"
        "<dc:creator>Furusato Fabric Workshop</dc:creator>"
        f"<cp:keywords>{escape(keywords)}</cp:keywords>"
        f"<dc:description>{escape(description)}</dc:description>"
        "<cp:lastModifiedBy>Furusato Fabric Workshop</cp:lastModifiedBy>"
        "<cp:revision>1</cp:revision>"
        f'<dcterms:created xsi:type="dcterms:W3CDTF">{now}</dcterms:created>'
        f'<dcterms:modified xsi:type="dcterms:W3CDTF">{now}</dcterms:modified>'
        "</cp:coreProperties>"
    )


def apply_package_metadata(
    path: Path,
    *,
    title: str,
    subject: str,
    keywords: str,
    description: str,
    label_info: bytes | None = None,
    custom_properties: bytes | None = None,
) -> None:
    """Rewrite core/custom properties and re-attach the Purview label parts."""
    with zipfile.ZipFile(path) as archive:
        parts = {name: archive.read(name) for name in archive.namelist()}

    parts["docProps/core.xml"] = core_properties_xml(title, subject, keywords, description).encode("utf-8")
    if label_info is not None:
        parts["docMetadata/LabelInfo.xml"] = label_info
    if custom_properties is not None:
        parts["docProps/custom.xml"] = custom_properties

    content_types = parts["[Content_Types].xml"].decode("utf-8")
    if "docMetadata/LabelInfo.xml" in parts and "classificationlabels" not in content_types:
        content_types = content_types.replace(
            "</Types>",
            '<Override PartName="/docMetadata/LabelInfo.xml" '
            'ContentType="application/vnd.ms-office.classificationlabels+xml"/></Types>',
        )
    if "docProps/custom.xml" in parts and "custom-properties+xml" not in content_types:
        content_types = content_types.replace(
            "</Types>",
            '<Override PartName="/docProps/custom.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.custom-properties+xml"/></Types>',
        )
    parts["[Content_Types].xml"] = content_types.encode("utf-8")

    package_rels = parts["_rels/.rels"].decode("utf-8")
    additions = []
    if "docMetadata/LabelInfo.xml" in parts and "classificationlabels" not in package_rels:
        additions.append(
            '<Relationship Id="rIdLabelInfo" '
            'Type="http://schemas.microsoft.com/office/2020/02/relationships/classificationlabels" '
            'Target="docMetadata/LabelInfo.xml"/>'
        )
    if "docProps/custom.xml" in parts and "custom-properties" not in package_rels:
        additions.append(
            '<Relationship Id="rIdCustomProps" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/custom-properties" '
            'Target="docProps/custom.xml"/>'
        )
    if additions:
        package_rels = package_rels.replace("</Relationships>", "".join(additions) + "</Relationships>")
    parts["_rels/.rels"] = package_rels.encode("utf-8")

    write_package(path, parts)


def normalise_package_metadata(path: Path) -> dict[str, object]:
    """Restore the approved authorship and classification metadata on ``path``.

    Word and Excel rewrite ``cp:lastModifiedBy`` with the signed-in user and stamp
    their tenant's default sensitivity label into ``docProps/custom.xml`` on every
    COM save. That default is a *different* label on a *different* tenant, so a
    file that has been through the refresh carries two contradictory
    classifications. This pass runs after the last COM save — the package must not
    be reopened in Office afterwards — and leaves exactly one label behind.
    """
    with zipfile.ZipFile(path) as archive:
        parts = {name: archive.read(name) for name in archive.namelist()}

    core = parts["docProps/core.xml"].decode("utf-8")
    before_creator = _tag_text(core, "dc:creator")
    before_modifier = _tag_text(core, "cp:lastModifiedBy")
    core = _replace_tag(core, "dc:creator", DOCUMENT_AUTHOR)
    core = _replace_tag(core, "cp:lastModifiedBy", DOCUMENT_AUTHOR)
    # Word sets the modified date to the wall-clock time of its own save, which is
    # the last thing that varies between two builds of identical content.
    before_modified = _stamped_text(core, "dcterms:modified")
    core = _replace_stamp(core, "dcterms:created", build_timestamp())
    core = _replace_stamp(core, "dcterms:modified", build_timestamp())
    parts["docProps/core.xml"] = core.encode("utf-8")

    app = parts.get("docProps/app.xml")
    if app is not None:
        # TotalTime counts the minutes the document has been open in Word, so it
        # depends on how long the refresh took rather than on the content.
        parts["docProps/app.xml"] = re.sub(
            r"<TotalTime>\d+</TotalTime>", "<TotalTime>0</TotalTime>", app.decode("utf-8")
        ).encode("utf-8")

    previous_custom = parts.get("docProps/custom.xml", b"").decode("utf-8")
    removed = sorted(set(re.findall(r"MSIP_Label_([0-9a-fA-F-]{36})_", previous_custom)) - {LABEL_ID})
    parts["docProps/custom.xml"] = custom_properties_xml()
    parts["docMetadata/LabelInfo.xml"] = LABEL_INFO_XML

    # This is the last write on the package, so every member — not just the parts
    # touched above — is re-emitted with the fixed build instant. Word stamps each
    # member with the local clock, which would otherwise make two builds differ.
    write_package(path, parts)
    identifiers = canonicalise_office_identifiers(path)

    return {
        "creatorWas": before_creator,
        "lastModifiedByWas": before_modifier,
        "modifiedWas": before_modified,
        "removedLabelIds": removed,
        "canonicalisedIdentifiers": identifiers,
    }


def _stamped_text(xml: str, tag: str) -> str:
    match = re.search(rf"<{tag}\b[^>]*>(.*?)</{tag}>", xml, re.DOTALL)
    return match.group(1) if match else ""


def _replace_stamp(xml: str, tag: str, value: str) -> str:
    """Replace a ``dcterms`` date, keeping its ``xsi:type`` attribute intact."""
    return re.sub(rf"(<{tag}\b[^>]*>).*?(</{tag}>)", rf"\g<1>{value}\g<2>", xml, count=1, flags=re.DOTALL)


def _tag_text(xml: str, tag: str) -> str:
    match = re.search(rf"<{tag}>(.*?)</{tag}>", xml, re.DOTALL)
    return match.group(1) if match else ""


def _replace_tag(xml: str, tag: str, value: str) -> str:
    replacement = f"<{tag}>{escape(value)}</{tag}>"
    if re.search(rf"<{tag}>.*?</{tag}>", xml, re.DOTALL):
        return re.sub(rf"<{tag}>.*?</{tag}>", replacement, xml, count=1, flags=re.DOTALL)
    return xml.replace(f"<{tag}/>", replacement)


def set_alt_text(inline_shape, name: str, description: str) -> None:
    """Give an inline picture an accessible title and description."""
    doc_pr = inline_shape._inline.docPr
    doc_pr.set("name", name)
    doc_pr.set("descr", description)
    doc_pr.set("title", name)


def strip_scratch(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path, ignore_errors=True)


def tidy_contents_tail(path: Path) -> int:
    """Stop the paragraph after the contents listing from spilling onto its own page.

    Word rebuilds the table of contents as one paragraph per entry and keeps the
    original field container as a trailing paragraph. When the listing fills its
    last page that leftover paragraph spills onto a page of its own, which then
    shows up as a blank page in front of the first chapter.

    The container paragraph usually still carries the field's ``end`` marker.
    Deleting it would unlink the TOC field, so a paragraph that carries any field
    part is collapsed to a hairline instead of being removed. Only a paragraph
    with no text, no drawing and no field part is deleted outright.

    Returns the number of paragraphs that were removed or collapsed.
    """
    from docx import Document
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn as _qn

    document = Document(str(path))
    body = document.element.body
    touched = 0
    children = list(body)
    for index, element in enumerate(children):
        if element.tag != _qn("w:p"):
            continue
        if element.find(f"{_qn('w:pPr')}/{_qn('w:sectPr')}") is None:
            continue
        candidate = children[index - 1] if index else None
        previous = children[index - 2] if index >= 2 else None
        if candidate is None or candidate.tag != _qn("w:p"):
            continue
        if previous is None or previous.tag != _qn("w:p"):
            continue
        previous_style = previous.find(f"{_qn('w:pPr')}/{_qn('w:pStyle')}")
        if previous_style is None or not (previous_style.get(_qn("w:val")) or "").upper().startswith("TOC"):
            continue
        has_text = any((node.text or "").strip() for node in candidate.iter(_qn("w:t")))
        has_drawing = candidate.find(f".//{_qn('w:drawing')}") is not None
        if has_text or has_drawing:
            continue
        has_field = (
            candidate.find(f".//{_qn('w:fldChar')}") is not None
            or candidate.find(f".//{_qn('w:instrText')}") is not None
        )
        if has_field:
            _hairline(candidate, OxmlElement, _qn)
        else:
            body.remove(candidate)
        touched += 1
    if touched:
        save_atomically(lambda staged: document.save(str(staged)), path)
    return touched


def _hairline(paragraph_element, oxml_element, qname) -> None:
    """Shrink a paragraph to a hairline without disturbing its runs."""
    p_pr = paragraph_element.find(qname("w:pPr"))
    if p_pr is None:
        p_pr = oxml_element("w:pPr")
        paragraph_element.insert(0, p_pr)
    spacing = p_pr.find(qname("w:spacing"))
    if spacing is None:
        spacing = oxml_element("w:spacing")
        r_pr = p_pr.find(qname("w:rPr"))
        if r_pr is not None:
            r_pr.addprevious(spacing)
        else:
            p_pr.append(spacing)
    spacing.set(qname("w:before"), "0")
    spacing.set(qname("w:after"), "0")
    spacing.set(qname("w:line"), "20")
    spacing.set(qname("w:lineRule"), "exact")
    r_pr = p_pr.find(qname("w:rPr"))
    if r_pr is None:
        r_pr = oxml_element("w:rPr")
        sect_pr = p_pr.find(qname("w:sectPr"))
        if sect_pr is not None:
            sect_pr.addprevious(r_pr)
        else:
            p_pr.append(r_pr)
    for tag in ("w:sz", "w:szCs"):
        if r_pr.find(qname(tag)) is None:
            element = oxml_element(tag)
            element.set(qname("w:val"), "2")
            r_pr.append(element)
    for run in paragraph_element.findall(qname("w:r")):
        run_pr = run.find(qname("w:rPr"))
        if run_pr is None:
            run_pr = oxml_element("w:rPr")
            run.insert(0, run_pr)
        for tag in ("w:sz", "w:szCs"):
            existing = run_pr.find(qname(tag))
            if existing is None:
                existing = oxml_element(tag)
                run_pr.append(existing)
            existing.set(qname("w:val"), "2")


def apply_japanese_typography(path: Path) -> bool:
    """Re-declare the Japanese typography defaults in a saved package.

    Word normalises ``docDefaults`` when it re-saves and drops any paragraph
    property that already matches its implicit default, so the kinsoku and
    overflow-punctuation declarations disappear from the shipped file even though
    the behaviour is unchanged. Writing them back after the Word pass keeps the
    delivered document explicit about its Japanese line-breaking rules instead of
    depending on a consumer resolving the implicit defaults the same way.
    """
    with zipfile.ZipFile(path) as archive:
        parts = {name: archive.read(name) for name in archive.namelist()}

    styles = parts["word/styles.xml"].decode("utf-8")
    settings = parts["word/settings.xml"].decode("utf-8")
    updated_styles = StyleCarrier._japanese_typography(styles)
    updated_settings = StyleCarrier._settings_typography(settings)
    if updated_styles == styles and updated_settings == settings:
        return False

    parts["word/styles.xml"] = updated_styles.encode("utf-8")
    parts["word/settings.xml"] = updated_settings.encode("utf-8")
    write_package(path, parts)
    return True


def paragraph_alt_targets(document) -> list[tuple[str, str]]:
    """Return ``(name, descr)`` for every inline drawing in the document body."""
    results: list[tuple[str, str]] = []
    for doc_pr in document.element.body.iter(qn("wp:docPr")):
        results.append((doc_pr.get("name") or "", doc_pr.get("descr") or ""))
    return results
