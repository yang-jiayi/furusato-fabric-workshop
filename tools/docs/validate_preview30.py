"""Validate actual v3 Word/HTML files, optionally rendering and driving local HTML."""

from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import os
import re
import sys
import posixpath
import zipfile
from dataclasses import asdict
from html.parser import HTMLParser
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "tools" / "docs"), str(ROOT / "tools" / "html")]

from furusato_docs.console import use_utf8_streams  # noqa: E402
from furusato_docs.preview30_content import HTML_NAME, WORD_NAME, build  # noqa: E402
from furusato_docs.participant30 import figure_path as participant_figure_path  # noqa: E402
from furusato_docs import preview30_release as release  # noqa: E402
from furusato_docs.render_audit import export_pdf, TOP_MARGIN_PT, BOTTOM_MARGIN_PT, PageReport  # noqa: E402
from furusato_docs.typography import ascii_parentheses  # noqa: E402
from furusato_docs import validators as old  # noqa: E402


class HtmlInspection(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ids = []
        self.links = []
        self.resources = []
        self.images_without_alt = []
        self.in_metadata = False
        self.metadata_parts = []
        self.title_parts = []
        self.document_title_count = 0
        self.stack = []
        self.text = {"ja": [], "en": []}
        self.figure_id = None
        self.images_by_figure = {}

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get("id"):
            self.ids.append(attrs["id"])
        if tag == "a":
            self.links.append(attrs.get("href", ""))
        if tag in ("img", "script", "iframe", "source") and attrs.get("src"):
            self.resources.append(attrs["src"])
        if tag == "link" and attrs.get("href"):
            self.resources.append(attrs["href"])
        if tag == "img" and not attrs.get("alt", "").strip():
            self.images_without_alt.append(attrs.get("src", "")[:40])
        if tag == "figure":
            self.figure_id = attrs.get("id")
        if tag == "img" and self.figure_id:
            self.images_by_figure[self.figure_id] = attrs.get("src", "")
        if tag == "script" and attrs.get("id") == "preview30-provenance":
            self.in_metadata = True
        previous = self.stack[-1] if self.stack else ("", None, False)
        if tag == "title" and previous[0] == "head":
            self.document_title_count += 1
        language = attrs.get("data-l", previous[1])
        ignored = previous[2] or tag in {"script", "style"}
        if tag not in {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}:
            self.stack.append((tag, language, ignored))

    def handle_endtag(self, tag):
        if tag == "script":
            self.in_metadata = False
        if tag == "figure":
            self.figure_id = None
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index][0] == tag:
                del self.stack[index:]
                break

    def handle_data(self, data):
        if len(self.stack) >= 2 and self.stack[-1][0] == "title" and self.stack[-2][0] == "head":
            self.title_parts.append(data)
        if self.in_metadata:
            self.metadata_parts.append(data)
        if self.stack and self.stack[-1][2]:
            return
        language = self.stack[-1][1] if self.stack else None
        for lang in ("ja", "en"):
            if language in (None, lang):
                self.text[lang].append(data)


def normalized(value):
    return re.sub(r"\s+", "", ascii_parentheses(value).replace("\u2060", "").replace("\u200b", ""))


def report_check(report, name, condition, detail=""):
    (report.ok if condition else report.fail)(name, detail)


def model_texts(document):
    for section in document.walk():
        yield section.title
        for block in section.blocks:
            if block.kind in {"paragraph", "prompt", "callout"}:
                yield block["text"]
                if block.get("title"):
                    yield block["title"]
            elif block.kind == "list":
                yield from block["items"]
            elif block.kind == "table":
                yield block["caption"]
                yield from block["headers"]
                for row in block["rows"]:
                    yield from row
            elif block.kind == "figure":
                yield block["caption"]


def inspect_word(word, document, metadata, report, *, release_profile=release.PREVIEW):
    profile = release.require_metadata_profile(metadata, release_profile)
    parts = old.check_package(word, report)
    old.check_authorship(parts, report, scope="word")
    old.check_no_foreign_label_guids(parts, report, scope="word")
    old.check_no_build_provenance(parts, report, scope="word")
    old.check_reproducible_package(word, parts, report, scope="word")
    old.check_parentheses(parts, report)
    tree = ET.fromstring(parts["word/document.xml"])
    paragraphs = []
    headings = []
    all_headings = []
    toc_rows = 0
    for paragraph in tree.iter(f"{old.W}p"):
        text = "".join(node.text or "" for node in paragraph.iter(f"{old.W}t"))
        paragraphs.append(text)
        style = paragraph.find(f"{old.W}pPr/{old.W}pStyle")
        if style is not None and style.get(f"{old.W}val") == "Heading1":
            headings.append(text)
        if style is not None and style.get(f"{old.W}val", "").startswith("Heading"):
            all_headings.append(text)
        if style is not None and style.get(f"{old.W}val") in {"TOC1", "TOC2"} and text.strip():
            toc_rows += 1
    report_check(report, "word.24chapters5appendices", len(headings) == 29, f"{len(headings)} top-level headings")
    report_check(report, "word.allHeadings", len(all_headings) == metadata["counts"]["headings"], str(len(all_headings)))
    report_check(report, "word.persistentTOC", toc_rows >= 29, f"{toc_rows} cached TOC rows")
    all_text = normalized("".join(paragraphs))
    prose_text = normalized("".join(paragraphs).replace("`", ""))
    report_check(report, "word.noUnresolvedTOCPlaceholder", "Wordで開くと目次が生成されます" not in prose_text)
    # The current Word renderer converts backtick-delimited prose to styled runs.
    # Executable code is checked separately below without removing backticks.
    missing = [text.ja[:100] for text in model_texts(document) if normalized(text.ja.replace("`", "")) not in prose_text]
    report_check(report, "word.sharedContentComplete", not missing, str(missing[:10]))
    for section in document.walk():
        for block in section.blocks:
            if block.kind == "code":
                report_check(report, "word.codePreserved", normalized(block["text"]) in all_text, block["text"][:65])
    tables = [node for node in tree.iter(f"{old.W}tbl") if node.find(f"{old.W}tblPr/{old.W}tblCaption") is not None]
    report_check(report, "word.tableCount", len(tables) == len(document.tables), str(len(tables)))
    report_check(report, "word.tableAccessibility", all(node.find(f"{old.W}tblPr/{old.W}tblDescription") is not None for node in tables))
    images = list(tree.iter(f"{old.WP}docPr"))
    report_check(report, "word.imageAccessibility", all(node.get("descr") for node in images))
    report_check(report, "word.figureCount", len(images) - old._cover_logo_count(images) == len(document.figures))
    report_check(report, "word.noTrackedChanges", not re.search(r"<w:(ins|del|moveFrom|moveTo)\b", parts["word/document.xml"].decode("utf-8")))
    core = parts["docProps/core.xml"].decode("utf-8")
    report_check(report, "word.contentFingerprint", "Content SHA256: " + metadata["contentSha256"] in core)
    title = ET.fromstring(core).find("{http://purl.org/dc/elements/1.1/}title")
    report_check(report, "word.documentTitle", title is not None and title.text == profile.title + " — participant guide")
    report_check(report, "word.coverEdition", normalized(profile.title) in all_text and normalized(profile.version) in all_text)
    if "evaluation100" in metadata:
        report_check(report, "word.evaluation100Hash", metadata["evaluation100Sha256"] in all_text)
    if "currentArtifactSet" in metadata:
        report_check(report, "word.currentArtifactSetHash",
                     metadata["currentArtifactSet"]["manifestSha256"] in (core if metadata.get("participantEdition") else all_text))
    if metadata.get("participantEdition"):
        found = working_content(" ".join(paragraphs))
        report_check(report, "word.participantProcedureOnly", not found, str(found[:10]))
    return parts


#: Wording that belongs to working records or history, not to a participant procedure.
WORKING_CONTENT = re.compile(
    r"v2\.7参考|v2\.7 reference|記録時刻|Recorded:|撮影時点|State at capture|実施証拠|Execution evidence"
    r"|合格判定とは別|not a pass judgment|\d+\s*PASS\s*/\s*\d+\s*FAIL|original84|frozen100|promotion|receipt"
    r"|Artifact-set SHA|source commit|未合格|not accepted|snapshot|スナップショット|\bseed\b|\braw\b",
    re.IGNORECASE,
)
LITERAL_NAMES = re.compile(r"(?:Files|data)(?:/furusato)?/seed|StaticSeed|/seed/|\\seed\\")


def working_content(value):
    return sorted({match.group(0) for match in WORKING_CONTENT.finditer(LITERAL_NAMES.sub("", value))})


def inspect_html(pair, document, metadata, report, *, release_profile=release.PREVIEW):
    profile = release.require_metadata_profile(metadata, release_profile)
    path = pair / profile.html_name
    source = path.read_text(encoding="utf-8")
    inspection = HtmlInspection()
    inspection.feed(source)
    provenance = json.loads("".join(inspection.metadata_parts))
    report_check(report, "html.uniqueAnchors", len(inspection.ids) == len(set(inspection.ids)))
    missing = [href for href in inspection.links if href.startswith("#") and href[1:] not in inspection.ids]
    report_check(report, "html.internalLinks", not missing, str(missing))
    local = [href for href in inspection.links if href and not href.startswith(("#", "https://", "http://", "mailto:"))]
    actual_title = "".join(inspection.title_parts)
    report_check(report, "html.documentTitle", inspection.document_title_count == 1 and actual_title == profile.title,
                 f"{inspection.document_title_count} document head title(s): {actual_title!r}")
    report_check(report, "html.exactWordLink", local == [profile.word_name], str(local))
    report_check(report, "html.wordExists", (pair / profile.word_name).is_file())
    report_check(report, "html.actualWordDigest", provenance["wordSha256"] == hashlib.sha256((pair / profile.word_name).read_bytes()).hexdigest())
    report_check(report, "html.profileFilenames", provenance.get("wordFilename") == profile.word_name and provenance.get("htmlFilename") == profile.html_name)
    report_check(report, "html.documentProfile", provenance.get("version") == profile.version and provenance.get("documentRelease") == metadata.get("documentRelease"))
    report_check(report, "html.selectedProjection", all(provenance.get(key) == metadata.get(key) for key in (
        "selectedOriginalSuiteRunId", "publicEvidenceProjectionSha256", "originalSuiteRuns", "finalEvaluation",
        "originalSuiteAccepted", "aiAnswerQualityAccepted", "mainPromoted", "allFeaturesPassedClaimed",
        "finalUserAcceptanceCertified",
        "evaluation100", "evaluation100Sha256", "currentArtifactSet",
    )))
    report_check(report, "html.sharedFingerprint", provenance["contentSha256"] == metadata["contentSha256"])
    report_check(report, "html.shape", provenance["counts"] == metadata["counts"])
    report_check(report, "html.offlineResources", all(uri.startswith("data:") for uri in inspection.resources))
    report_check(report, "html.imageAccessibility", not inspection.images_without_alt)
    report_check(report, "html.noNetworkScripts", not re.search(r"(?:fetch\s*\(|XMLHttpRequest|@import)", source))
    report_check(report, "html.honestEvidence", provenance["evidenceComplete"] == metadata["evidenceComplete"])
    for language in ("ja", "en"):
        actual = normalized("".join(inspection.text[language]).replace("`", ""))
        missing = []
        for text in model_texts(document):
            value = text.get(language).replace("`", "")
            if language == "en" and value.startswith("Synonyms (registered by NB02): "):
                value = value.replace("、", ", ")
            if normalized(value) not in actual:
                missing.append(value[:100])
        report_check(report, f"html.{language}.sharedContentComplete", not missing, str(missing[:10]))
        code_text = normalized("".join(inspection.text[language]))
        missing_code = [
            b["text"][:70] for s in document.walk() for b in s.blocks
            if b.kind == "code" and normalized(b["text"]) not in code_text
        ]
        report_check(report, f"html.{language}.codeComplete", not missing_code, str(missing_code[:10]))
        if metadata.get("participantEdition"):
            found = working_content("".join(inspection.text[language]))
            report_check(report, f"html.{language}.participantProcedureOnly", not found, str(found[:10]))
    report.stats["externalLinks"] = sorted({link for link in inspection.links if link.startswith("https://")})
    return provenance


def check_capture_fidelity(pair, document, evidence, report, *, release_profile=release.PREVIEW):
    """Compare approved capture pixels and placement, not just model metadata."""
    from PIL import Image

    def fingerprint(blob):
        with Image.open(io.BytesIO(blob)) as image:
            return image.size, hashlib.sha256(image.convert("RGB").tobytes()).hexdigest()

    profile = release.get_profile(release_profile)
    inspection = HtmlInspection()
    inspection.feed((pair / profile.html_name).read_text(encoding="utf-8"))
    with zipfile.ZipFile(pair / profile.word_name) as archive:
        document_xml = ET.fromstring(archive.read("word/document.xml"))
        relationships = ET.fromstring(archive.read("word/_rels/document.xml.rels"))
        targets = {
            relation.get("Id"): posixpath.normpath("word/" + relation.get("Target", ""))
            for relation in relationships
            if relation.get("Type", "").endswith("/image")
        }
        body_images = [
            archive.read(targets[node.get(f"{old.R}embed")])
            for node in document_xml.iter(f"{old.A}blip")
        ]
        cover_count = len(body_images) - len(document.figures)
        for figure in document.figures:
            if figure["source_kind"] not in {"reviewed-capture", "participant-capture"}:
                continue
            ident = figure["source_key"]
            source = (evidence["captures"][ident]["path"] if figure["source_kind"] == "reviewed-capture"
                      else participant_figure_path(ident))
            expected = fingerprint(source.read_bytes())
            index = cover_count + figure["number"] - 1
            report_check(
                report, "word.capturePixels." + ident,
                0 <= index < len(body_images) and fingerprint(body_images[index]) == expected,
                "Exact decoded RGB pixels at the declared figure position",
            )
            uri = inspection.images_by_figure.get(f"figure-{figure['number']}", "")
            actual = fingerprint(base64.b64decode(uri.split(",", 1)[1])) if uri.startswith("data:image/") else None
            report_check(
                report, "html.capturePixels." + ident, actual == expected,
                "Lossless embedded pixels at the declared figure position",
            )


def review_pdf(path, review, report, label):
    import fitz
    from PIL import Image, ImageDraw
    pages = []
    clipping = []
    tiles = []
    with fitz.open(path) as pdf:
        for index, page in enumerate(pdf):
            body = fitz.Rect(0, TOP_MARGIN_PT, page.rect.width, page.rect.height - BOTTOM_MARGIN_PT)
            pix = page.get_pixmap(clip=body, colorspace=fitz.csGRAY, dpi=72)
            ratio = sum(value < 250 for value in pix.samples) / len(pix.samples)
            image_ratio = 0.0
            for image in page.get_images(full=True):
                for rectangle in page.get_image_rects(image[0]):
                    image_ratio += (rectangle & body).get_area() / body.get_area()
            pages.append(PageReport(index + 1, ratio, page.get_text(clip=body), image_ratio))
            for block in page.get_text("dict")["blocks"]:
                for line in block.get("lines", []):
                    for span in line["spans"]:
                        x0, y0, x1, y1 = span["bbox"]
                        if x0 < -1 or x1 > page.rect.width + 1 or y0 < -1 or y1 > page.rect.height + 1:
                            clipping.append([index + 1, span["text"][:80], span["bbox"]])
            if index % 8 == 0 or index == len(pdf) - 1:
                image = page.get_pixmap(matrix=fitz.Matrix(.5, .5))
                tile = Image.frombytes("RGB", [image.width, image.height], image.samples)
                tiles.append((index + 1, tile))
        width, height = 320 * 4, 450 * ((len(tiles) + 3) // 4)
        sheet = Image.new("RGB", (width, height), "#d9e4de")
        draw = ImageDraw.Draw(sheet)
        for index, (number, tile) in enumerate(tiles):
            x, y = index % 4 * 320, index // 4 * 450
            draw.text((x + 5, y + 4), f"{label} page {number}", fill="black")
            sheet.paste(tile, (x + 8, y + 22))
        sheet.save(review / f"{label}-contact-sheet.png")
    blank = [p.number for p in pages if p.is_blank]
    captions = [p.number for p in pages if p.is_caption_only]
    report_check(report, f"{label}.noBlankPages", not blank, str(blank))
    report_check(report, f"{label}.noCaptionOnlyPages", not captions, str(captions))
    report_check(report, f"{label}.noClippedText", not clipping, str(clipping[:10]))
    report.stats[label] = {
        "pages": len(pages), "blankPages": blank, "captionOnlyPages": captions, "clippedText": clipping,
        "kinsokuLeading": [[p.number, text] for p in pages for text in p.kinsoku_violations],
    }
    return len(pages)


def local_interactions(target, review, report, print_pdf=False):
    """Only local file:// content, no signed-in browser and no Fabric operations."""
    from playwright.sync_api import sync_playwright
    browser_work = review / "browser-work"
    browser_work.mkdir(exist_ok=True)
    os.environ["TEMP"] = os.environ["TMP"] = str(browser_work)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="msedge", headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 1000})
        context.route("http://**", lambda route: route.abort())
        context.route("https://**", lambda route: route.abort())
        page = context.new_page()
        errors = []
        requests = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on("request", lambda req: requests.append(req.url))
        page.goto(target.as_uri(), wait_until="load")
        report_check(report, "interaction.29sections", page.locator("main > .chapter").count() == 29)
        report_check(report, "interaction.defaultJapanese", page.locator("html").get_attribute("lang") == "ja")
        page.click('[data-language="en"]')
        report_check(report, "interaction.english", page.locator("html").get_attribute("lang") == "en")
        report_check(report, "interaction.japaneseHidden", not page.locator("#ch-15 h2 [data-l=ja]").is_visible())
        report_check(report, "interaction.englishVisible", page.locator("#ch-15 h2 [data-l=en]").is_visible())
        page.reload(wait_until="load")
        report_check(report, "interaction.languagePersists", page.locator("html").get_attribute("lang") == "en")
        page.fill("#search", "Lakehouse")
        found = page.locator("main > .chapter:visible").count()
        report_check(report, "interaction.englishSearch", found > 0 and page.locator("#search-status").inner_text().startswith(f"{found} "))
        page.fill("#search", "NO_SUCH_PHRASE_f9ca2")
        report_check(report, "interaction.emptySearch", page.locator("main > .chapter:visible").count() == 0)
        page.click("#search-clear")
        report_check(report, "interaction.searchClears", page.locator("main > .chapter:visible").count() == 29)
        page.click("#progress-reset")
        first = page.locator("input[data-step]").first
        first.check()
        page.reload(wait_until="load")
        report_check(report, "interaction.progressPersists", page.locator("input[data-step]").first.is_checked())
        page.click("#progress-reset")
        report_check(report, "interaction.progressReset", page.locator("input[data-step]:checked").count() == 0)
        page.locator('a[href="#ch-22"]').click()
        report_check(report, "interaction.tocNavigation", page.url.endswith("#ch-22"))
        page.locator('button[data-copy-target^="prompt-"]:visible').first.click()
        page.wait_for_function("() => document.getElementById('copy-status').textContent.length > 0")
        report_check(report, "interaction.copyFeedback", bool(page.locator("#copy-status").inner_text()))
        if page.locator("#legacy-toggle").count():
            page.click("#legacy-toggle")
            # Search may already have opened all legacy sections; ensure at least one is open.
            page.locator("details.legacy").first.evaluate("(element) => element.open=true")
        page.locator("[data-lightbox]").first.click()
        report_check(report, "interaction.figureZoom", page.locator("#lightbox").is_visible())
        page.keyboard.press("Escape")
        report_check(report, "interaction.escapeClosesZoom", not page.locator("#lightbox").is_visible())
        for lang in ("ja", "en"):
            page.click(f'[data-language="{lang}"]')
            for width, height in ((1440, 1000), (768, 1024), (390, 844)):
                page.set_viewport_size({"width": width, "height": height})
                overflow = page.evaluate("document.documentElement.scrollWidth > innerWidth + 1")
                report_check(report, f"interaction.{lang}.viewport{width}", not overflow)
            page.set_viewport_size({"width": 1440, "height": 1000})
            page.evaluate("window.scrollTo(0,0)")
            page.screenshot(path=str(review / f"html-{lang}-desktop.png"), full_page=False)
            if print_pdf:
                page.emulate_media(media="print")
                page.evaluate("dispatchEvent(new Event('beforeprint'))")
                pdf = review / f"html-{lang}.pdf"
                page.pdf(path=str(pdf), format="A4", print_background=True, prefer_css_page_size=True)
                page.evaluate("dispatchEvent(new Event('afterprint'))")
                page.emulate_media(media="screen")
                review_pdf(pdf, review, report, f"html-{lang}")
        report_check(report, "interaction.noScriptErrors", not errors, str(errors))
        report_check(report, "interaction.noExternalRequests", not any(url.startswith(("http:", "https:")) for url in requests))
        context.close()
        browser.close()
    # Playwright owns and cleans its own per-run profile; the parent directory is not evidence.
    if not any(browser_work.iterdir()):
        browser_work.rmdir()


def main(argv=None):
    use_utf8_streams()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pair", required=True, type=Path)
    parser.add_argument("--review", required=True, type=Path)
    inputs = parser.add_mutually_exclusive_group()
    inputs.add_argument("--evidence", type=Path)
    inputs.add_argument("--public-evidence", type=Path)
    parser.add_argument("--evaluation-report", type=Path)
    parser.add_argument("--artifact-manifest", type=Path)
    parser.add_argument("--render", action="store_true")
    parser.add_argument("--interactions", action="store_true")
    parser.add_argument("--print-html", action="store_true")
    release.add_arguments(parser)
    args = parser.parse_args(argv)
    profile = release.get_profile(args.release_profile)
    document, _, _, _, evidence, metadata = build(
        ROOT, args.evidence, args.evaluation_report, public_evidence_path=args.public_evidence,
        release_profile=profile, release_approval=args.release_approval,
        evaluation100_path=args.evaluation100,
        **({"artifact_manifest_path": args.artifact_manifest} if args.artifact_manifest else {}),
        **({"participant_edition": True} if args.participant_edition else {}),
    )
    pair, review = args.pair.resolve(), args.review.resolve()
    if review.is_relative_to(ROOT) or review.is_relative_to(pair):
        parser.error("Raw review artifacts must be outside the public tree and exact pair")
    if {p.name for p in pair.iterdir()} != {profile.word_name, profile.html_name}:
        parser.error("The pair directory must contain exactly the matching Word and HTML")
    review.mkdir(parents=True, exist_ok=True)
    report = old.Report(target="Furusato " + profile.display_version + " actual pair")
    inspect_word(pair / profile.word_name, document, metadata, report, release_profile=profile)
    inspect_html(pair, document, metadata, report, release_profile=profile)
    check_capture_fidelity(pair, document, evidence, report, release_profile=profile)
    if args.render:
        pdf = review / "word.pdf"
        error = export_pdf(pair / profile.word_name, pdf)
        report_check(report, "word.renderAvailable", not error, error or "Current Word COM renderer")
        if not error:
            review_pdf(pdf, review, report, "word")
    if args.interactions:
        try:
            local_interactions(pair / profile.html_name, review, report, args.print_html)
        except Exception as error:
            report.fail("interaction.runner", f"{error.__class__.__name__}: {error}")
    result = {
        "passedLocalChecks": report.passed, "evidenceComplete": evidence["complete"],
        "status": "locally-checked-draft" if report.passed and not evidence["complete"] else "validation-failed",
        "files": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in pair.iterdir()},
        "findings": [asdict(f) for f in report.findings], "stats": report.stats,
        "evidenceScope": metadata["evidenceScope"], "newDeploymentReadinessCertified": False,
        "knownIssueLabs": metadata["knownIssueLabs"],
        "releaseFreezeStatus": metadata.get("releaseFreezeStatus", "not-frozen"),
        "documentIdentity": release.document_identity(metadata, profile),
    }
    if report.passed and evidence["complete"]:
        result["status"] = "evidence-backed" if args.render and args.interactions and args.print_html else "more-local-validation-required"
    if report.passed and profile.is_release:
        result["status"] = (
            "locally-validated-known-limitations-release"
            if args.render and args.interactions and args.print_html else "more-local-validation-required"
        )
    if report.passed and profile.is_snapshot and args.render and args.interactions and args.print_html:
        result["status"] = "locally-validated-known-limitations-snapshot"
    (review / "validation.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "passed": sum(f.level == "PASS" for f in report.findings),
        "failed": len(report.failures), "status": result["status"],
        "failures": [asdict(f) for f in report.failures], "wordPages": report.stats.get("word", {}).get("pages"),
    }, ensure_ascii=False, indent=2))
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
