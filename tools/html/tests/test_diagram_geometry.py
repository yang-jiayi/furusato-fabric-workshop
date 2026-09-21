r"""Browser geometry and lossless-translation checks without rebuilding the guide.

    python tools\html\tests\test_diagram_geometry.py
    python tools\html\tests\test_diagram_geometry.py --artifacts <directory>

The source artwork is read-only. Optional screenshots and the measured geometry
are written only to the explicitly supplied artifact directory.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools" / "html"))
from furusato_html import diagrams

ASSETS = ROOT / "docs" / "assets" / "v2.7.0"

SOURCE_GEOMETRY = r"""() => {
    const svg = document.querySelector('svg');
    const rect = b => ({x:b.x, y:b.y, width:b.width, height:b.height});
    const shapes = [...svg.querySelectorAll('rect,polygon,circle,ellipse')]
        .filter(e => !e.closest('defs') && e.getAttribute('fill') !== 'none');
    return [...svg.querySelectorAll('text')].map((e, index) => {
        const b = e.getBBox(), size = parseFloat(getComputedStyle(e).fontSize);
        const x = parseFloat(e.getAttribute('x')), y = parseFloat(e.getAttribute('y'));
        const containing = shapes.filter(s => {
            const a = s.getBBox();
            return a.x <= x && a.x + a.width >= x
                && a.y <= y - size * .35 && a.y + a.height >= y - size * .35
                && a.y <= b.y + 2 && a.y + a.height >= b.y + b.height - 2;
        }).sort((a,c) => {
            const ab=a.getBBox(), cb=c.getBBox();
            return ab.width*ab.height-cb.width*cb.height;
        });
        const owner = containing[0];
        return {index, text:e.textContent.trim(), x, y, size,
            box:rect(b), shape:owner ? shapes.indexOf(owner) : null,
            owner:owner ? rect(owner.getBBox()) : rect(svg.viewBox.baseVal),
            tag:owner ? owner.tagName : 'svg'};
    });
}"""

MEASURE = r"""source => {
    const svg = document.querySelector('svg');
    const rect = b => ({x:b.x, y:b.y, width:b.width, height:b.height});
    const shapes = [...svg.querySelectorAll('rect,polygon,circle,ellipse')]
        .filter(e => !e.closest('defs') && e.getAttribute('fill') !== 'none');
    const elements = [...svg.querySelectorAll('text')];
    const rows = [];
    const outsideOutline = [], occluded = [];
    for (const [index,e] of elements.entries()) {
        const parent = source[index];
        const owner = parent.shape === null
            ? parent.owner : rect(shapes[parent.shape].getBBox());
        const lines = e.querySelectorAll('tspan').length
            ? [...e.querySelectorAll('tspan')] : [e];
        for (const line of lines) {
            if (!line.textContent.trim()) continue;
            const b = line.getBBox();
            const row = {index, text:line.textContent.trim(), box:rect(b), owner,
                tag:parent.tag, shape:parent.shape,
                size:parseFloat(getComputedStyle(line).fontSize),
                overflow:{
                    left:Math.max(0, owner.x-b.x),
                    right:Math.max(0, b.x+b.width-owner.x-owner.width),
                    top:Math.max(0, owner.y-b.y),
                    bottom:Math.max(0, b.y+b.height-owner.y-owner.height)
                }};
            rows.push(row);
            const points = [
                [b.x+.5,b.y+.5], [b.x+b.width-.5,b.y+.5],
                [b.x+.5,b.y+b.height-.5], [b.x+b.width-.5,b.y+b.height-.5]
            ];
            if (parent.tag === 'polygon' && points.some(([x,y]) =>
                !shapes[parent.shape].isPointInFill(new DOMPoint(x,y))))
                outsideOutline.push(row);
            for (const s of shapes) {
                if (s === shapes[parent.shape] ||
                    !(e.compareDocumentPosition(s) & Node.DOCUMENT_POSITION_FOLLOWING))
                    continue;
                const a = s.getBBox();
                const x=Math.max(a.x,b.x), y=Math.max(a.y,b.y);
                const width=Math.min(a.x+a.width,b.x+b.width)-x;
                const height=Math.min(a.y+a.height,b.y+b.height)-y;
                if (width>1.5 && height>1.5 &&
                    s.isPointInFill(new DOMPoint(x+width/2,y+height/2)))
                    occluded.push({text:row.text, shape:shapes.indexOf(s), width, height});
            }
        }
    }
    const overlaps = [];
    for (let i=0;i<rows.length;i++) for (let j=i+1;j<rows.length;j++) {
        const a=rows[i], b=rows[j];
        const width=Math.min(a.box.x+a.box.width,b.box.x+b.box.width)
            - Math.max(a.box.x,b.box.x);
        const height=Math.min(a.box.y+a.box.height,b.box.y+b.box.height)
            - Math.max(a.box.y,b.box.y);
        if (width > 1 && height > 1)
            overlaps.push({a:a.text,b:b.text,width,height,indices:[a.index,b.index]});
    }
    const coveredArrowheads = [];
    const connectors = [...svg.querySelectorAll('[marker-end]')];
    for (const e of connectors) {
        if (!e.getTotalLength) continue;
        const tip = e.getPointAtLength(Math.max(0,e.getTotalLength()-3));
        for (const s of shapes) {
            if ((e.compareDocumentPosition(s) & Node.DOCUMENT_POSITION_FOLLOWING) &&
                s.isPointInFill(tip))
                coveredArrowheads.push({connector:connectors.indexOf(e),
                    shape:shapes.indexOf(s), x:tip.x, y:tip.y});
        }
    }
    return {rows, overlaps, outsideOutline, occluded, coveredArrowheads,
        overflow:rows.filter(r => Object.values(r.overflow).some(n => n>1.5)),
        markerCount:svg.querySelectorAll('[marker-end],[marker-start]').length};
}"""


def render(page, svg: str, width: int = 1600, *, lightbox: bool = False) -> None:
    svg = re.sub(r"<\?xml[^>]*\?>", "", svg)
    if lightbox:
        wrapper = (
            f'<dialog style="width:{width}px;max-width:none;max-height:none;'
            'padding:16px;border:0;border-radius:12px">'
            '<header style="display:flex;justify-content:space-between;align-items:center;'
            'height:32px;font:14px sans-serif">English diagram — enlarged view'
            '<button>Close</button></header>' + svg + '</dialog>'
        )
    else:
        wrapper = f'<main style="width:{width}px">{svg}</main>'
    page.set_content(
        '<!doctype html><html lang="en"><meta charset="utf-8">'
        '<style>body{margin:0;background:#fff}svg{display:block;width:100%;height:auto}'
        'dialog::backdrop{background:#123d34dd}</style>' + wrapper + '</html>'
    )
    if lightbox:
        page.evaluate("() => document.querySelector('dialog').showModal()")
    page.evaluate("() => document.fonts.ready")


def audit(artifacts: Path | None = None) -> dict:
    mapping = diagrams.load_map()
    report = {}
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1600, "height": 1200})
        for path in sorted(ASSETS.glob("*.svg")):
            raw = path.read_text(encoding="utf-8")
            english, missing = diagrams.to_english(raw, mapping)
            render(page, raw)
            source = page.evaluate(SOURCE_GEOMETRY)
            render(page, english)
            measured = page.evaluate(MEASURE, source)
            measured["missing"] = missing
            measured["sourceSha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
            report[path.stem] = measured
            if artifacts:
                artifacts.mkdir(parents=True, exist_ok=True)
                (artifacts / f"{path.stem}.svg").write_text(english, encoding="utf-8")
                page.locator("svg").screenshot(path=str(artifacts / f"{path.stem}.png"))
            if path.stem == "system-data-flow":
                for name, width in (("normal", 1024), ("enlarged", 1408)):
                    lightbox = name == "enlarged"
                    page.set_viewport_size({"width": 1440, "height": 1080})
                    render(page, english, width, lightbox=lightbox)
                    scaled = page.evaluate(MEASURE, source)
                    measured[name] = {key: scaled[key] for key in (
                        "overflow", "overlaps", "outsideOutline", "occluded", "coveredArrowheads"
                    )}
                    if artifacts:
                        page.locator("dialog" if lightbox else "svg").screenshot(
                            path=str(artifacts / f"system-data-flow-{name}.png")
                        )
                page.set_viewport_size({"width": 1600, "height": 1200})
        browser.close()
    if artifacts:
        (artifacts / "geometry.json").write_text(
            json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    return report


class DiagramGeometryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not hasattr(cls, "report"):
            cls.report = audit()

    def test_translations_have_complete_coverage(self):
        used = {
            text
            for path in ASSETS.glob("*.svg")
            for text in diagrams.units(path.read_text(encoding="utf-8"))
        }
        self.assertEqual(set(diagrams.load_map()), used)
        for name, row in self.report.items():
            with self.subTest(diagram=name):
                self.assertEqual(row["missing"], [])

    def test_english_labels_stay_inside_their_own_shapes(self):
        for name, row in self.report.items():
            with self.subTest(diagram=name):
                self.assertEqual(row["overflow"], [])

    def test_labels_do_not_overprint(self):
        for name, row in self.report.items():
            with self.subTest(diagram=name):
                self.assertEqual(row["overlaps"], [])

    def test_diamond_labels_stay_inside_sloping_edges(self):
        for name, row in self.report.items():
            with self.subTest(diagram=name):
                self.assertEqual(row["outsideOutline"], [])

    def test_neighbouring_shapes_do_not_cover_labels_or_arrowheads(self):
        for name, row in self.report.items():
            with self.subTest(diagram=name):
                self.assertEqual(row["occluded"], [])
                self.assertEqual(row["coveredArrowheads"], [])

    def test_normal_and_enlarged_english_views(self):
        for view in ("normal", "enlarged"):
            for check, failures in self.report["system-data-flow"][view].items():
                with self.subTest(view=view, check=check):
                    self.assertEqual(failures, [])

    def test_reported_cards_keep_the_original_body_type_size(self):
        for row in self.report["system-data-flow"]["rows"]:
            owner = row["owner"]
            if owner["x"] in (96, 896, 918) and row["box"]["y"] > owner["y"] + 48:
                with self.subTest(label=row["text"]):
                    self.assertEqual(row["size"], 11.2)

    def test_browser_uses_the_measured_installed_typefaces(self):
        source = (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 120">'
            '<rect x="0" y="0" width="500" height="120" fill="white"/>'
            '<text id="regular" x="20" y="30" font-size="11.2">説明</text>'
            '<text id="bold" x="20" y="75" font-size="14" font-weight="bold">見出し</text>'
            '</svg>'
        )
        english, missing = diagrams.to_english(
            source, {"説明": "72 static properties / SourceFile / WorkshopRunId", "見出し": "Static data binding"}
        )
        self.assertEqual(missing, [])
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page()
            render(page, english)
            cdp = page.context.new_cdp_session(page)
            cdp.send("DOM.enable")
            cdp.send("CSS.enable")
            root = cdp.send("DOM.getDocument")["root"]["nodeId"]
            for selector, bold in (("#regular", False), ("#bold", True)):
                with self.subTest(weight=selector):
                    node = cdp.send("DOM.querySelector", {"nodeId": root, "selector": selector})["nodeId"]
                    fonts = cdp.send("CSS.getPlatformFontsForNode", {"nodeId": node})["fonts"]
                    used = [font for font in fonts if font["glyphCount"]]
                    self.assertTrue(used)
                    self.assertEqual({font["familyName"] for font in used}, {diagrams._font(bold).getname()[0]})
                    self.assertTrue(all(not font["isCustomFont"] for font in used))
            cdp.detach()
            browser.close()

    def test_translated_and_original_labels_are_lossless(self):
        normalize = lambda value: " ".join(value.split())
        mapping = diagrams.load_map()
        for path in sorted(ASSETS.glob("*.svg")):
            with self.subTest(diagram=path.stem):
                before = path.read_bytes()
                source = before.decode("utf-8")
                english, missing = diagrams.to_english(source, mapping)
                self.assertEqual(path.read_bytes(), before)
                self.assertEqual(missing, [])
                self.assertEqual(diagrams.residual_japanese(english), [])
                font_or_host_reference = re.search(
                    r"(?i)@font-face|data:font|\bfile:|(?<![a-z0-9_])[a-z]:[\\/]"
                    r"|/(?:Users|home)/|\.(?:ttf|ttc|otf|woff2?)\b",
                    english,
                )
                self.assertIsNone(font_or_host_reference)
                original_lines = diagrams.parse_lines(source)
                translated_lines = diagrams.parse_lines(english)
                self.assertEqual(len(original_lines), len(translated_lines))
                positions = {line.start: index for index, line in enumerate(original_lines)}
                groups = diagrams.group_lines(original_lines)
                expected = [line.text for line in original_lines]
                for index, group in enumerate(groups):
                    if not group.needs_english:
                        continue
                    translation = mapping[group.text]
                    expected[positions[group.lines[0].start]] = translation
                    for line in group.lines[1:]:
                        expected[positions[line.start]] = ""
                    if index + 1 < len(groups):
                        sibling = groups[index + 1]
                        if not sibling.needs_english and diagrams._normalize(sibling.text) == diagrams._normalize(translation):
                            for line in sibling.lines:
                                expected[positions[line.start]] = ""
                self.assertEqual(
                    [normalize(line.text) for line in translated_lines],
                    [normalize(text) for text in expected],
                )
                def topology(svg):
                    root = ET.fromstring(svg)
                    return [
                        (node.tag, sorted(node.attrib.items()))
                        for node in root.iter()
                        if node.tag.rsplit("}", 1)[-1] in ("marker", "path", "line", "polygon")
                    ]
                self.assertEqual(topology(english), topology(source))

    def test_wrapping_never_dumps_excess_into_the_last_line(self):
        text = "10 entity types / 72 static properties — 15 relationship contextual keys — key resolution and record-count verification"
        pieces = diagrams.wrap_to(text, 11.2, 180, 3)
        self.assertGreater(len(pieces), 3)
        self.assertEqual(" ".join(pieces), text)
        self.assertTrue(all(diagrams._width(piece, 11.2) <= 180 for piece in pieces))

    def test_strict_missing_translation_returns_untouched_source(self):
        source = '<svg><text x="0" y="20" font-size="12">未訳</text></svg>'
        self.assertEqual(diagrams.to_english(source, {}), (source, ["未訳"]))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifacts", type=Path)
    parser.add_argument("--audit-only", action="store_true")
    options, remaining = parser.parse_known_args()
    if options.artifacts or options.audit_only:
        results = audit(options.artifacts)
        for name, result in results.items():
            print(
                f"{name}: {len(result['rows'])} lines, "
                f"{len(result['overflow'])} overflow, "
                f"{len(result['overlaps'])} overlap, "
                f"{len(result['outsideOutline'])} outside outlines, "
                f"{len(result['occluded'])} occluded, "
                f"{len(result['coveredArrowheads'])} covered arrowheads"
            )
        if options.audit_only:
            sys.exit(0)
        DiagramGeometryTests.report = results
    unittest.main(argv=[sys.argv[0], *remaining])
