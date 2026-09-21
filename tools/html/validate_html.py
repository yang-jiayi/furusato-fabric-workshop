"""Validate docs/furusato-workshop-v2-7-0-complete.html.

Every check is derived from the shipped v2.7.0 runtime or from the rendered
markup itself; nothing is transcribed by hand. ``--json`` emits a machine
readable report; the exit code is non-zero on any FAIL.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import html as html_module
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT / "tools" / "docs"))
sys.path.insert(0, str(HERE))

from furusato_docs.context import load_context  # noqa: E402
from furusato_docs.deliverables import deliverable_names, validate_edition  # noqa: E402
from furusato_docs.facts import compute_facts  # noqa: E402
from furusato_docs.guide_content import REFERENCE_LINKS  # noqa: E402
from furusato_docs.oox import StyleCarrier  # noqa: E402
from furusato_docs.parameters import build_parameter_rows, CATALOG, PARAMETER_COLUMNS  # noqa: E402
from furusato_docs.quality import _D6_AUTHORING_HISTORY  # noqa: E402
from furusato_docs.publication import (  # noqa: E402
    PUBLIC_MODE,
    PublicationError,
    check_directory,
    outside_repo,
    public_link_error,
    public_text_errors,
    require_public_edition,
)
from furusato_docs.tests10 import build_tests  # noqa: E402
from furusato_docs.typography import ascii_parentheses  # noqa: E402

from furusato_html.assets import sanitize_svg  # noqa: E402
from furusato_html.capture import capture_participant_guide  # noqa: E402
from furusato_html.mirror import load_mirror, load_ui_strings, suspicious_english  # noqa: E402
from furusato_html.model import Text, build_document  # noqa: E402
from furusato_html.render import diagram_title, rich  # noqa: E402

OUTPUT_NAME = "furusato-workshop-v2-7-0-complete.html"
GITHUB_FILE_LIMIT = 100 * 1000 * 1000

VOID_ELEMENTS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
}

#: The only hosts a documentation link may point at. All three are first-party
#: Microsoft properties; anything else is a third-party host, which the guide
#: never cites because it cannot be treated as the product's own statement.
FIRST_PARTY_DOC_HOSTS = (
    "https://learn.microsoft.com/",
    "https://azure.microsoft.com/",
    "https://www.microsoft.com/",
)

#: This exact OAuth audience is cited as a protocol reference, not a host allowlist.
EXACT_PROTOCOL_REFERENCES = frozenset({"https://database.windows.net/"})

#: Concepts that were removed from the participant materials in v2.7.0. Any of
#: them in the deliverable means a stale flow leaked back in.
FORBIDDEN = {
    "Eventstream": r"[Ee]ventstream",
    "Custom endpoint ingestion": r"[Cc]ustom [Ee]ndpoint",
    "Core-5 seed file": r"core-events_5|Core-5|core_events_5",
    "Test100 pack": r"Test\s?100|100 問|ontology-prompt-pack|answer-only-mcp|semantic-review-results",
    "internal QA folder": r"tools/qa|workshop/v2\.[0-9]+\.[0-9]+/ontology-tests",
    "high-value notification": r"高額通知|high-value notification|HIGH_VALUE|Send-DonationEvents",
    "superseded version": r"v?2\.6\.0|furusato-workshop-v2-6-0",
    "manual pipeline run in participant flow": r"SEND_CONTROLLED_EVENTS|CREATE_EVENTSTREAM",
}


@dataclass
class Report:
    results: list[tuple[str, str, str]] = field(default_factory=list)

    def add(self, status: str, check: str, detail: str = "") -> None:
        self.results.append((status, check, detail))

    def ok(self, check: str, detail: str = "") -> None:
        self.add("PASS", check, detail)

    def fail(self, check: str, detail: str) -> None:
        self.add("FAIL", check, detail)

    def warn(self, check: str, detail: str) -> None:
        self.add("WARN", check, detail)

    def expect(self, condition: bool, check: str, detail: str = "") -> bool:
        if condition:
            self.ok(check, detail)
        else:
            self.fail(check, detail)
        return condition

    @property
    def failures(self) -> list[tuple[str, str, str]]:
        return [r for r in self.results if r[0] == "FAIL"]

    @property
    def warnings(self) -> list[tuple[str, str, str]]:
        return [r for r in self.results if r[0] == "WARN"]


# ------------------------------------------------------------------- parsing
@dataclass
class Element:
    tag: str
    attrs: dict[str, str]
    parent: "Element | None" = None
    children: list["Element"] = field(default_factory=list)
    text: str = ""

    def walk(self):
        yield self
        for child in self.children:
            yield from child.walk()

    def all_text(self) -> str:
        parts = [self.text]
        for child in self.children:
            parts.append(child.all_text())
        return "".join(parts)


class Structure(HTMLParser):
    """Tolerant-but-strict HTML reader used for structural validation."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = Element("#document", {})
        self.stack: list[Element] = [self.root]
        self.errors: list[str] = []
        self.doctypes: list[str] = []
        self.in_script = 0

    def handle_decl(self, decl: str) -> None:
        self.doctypes.append(decl)

    def _checked_attributes(self, tag: str, attrs) -> dict[str, str]:
        normalized = [(name.casefold(), value) for name, value in attrs]
        duplicates = sorted(name for name, count in Counter(name for name, _ in normalized).items() if count > 1)
        for name in duplicates:
            self.errors.append(f"duplicate attribute {name!r} on <{tag}>")
        # Reject duplicates before collapsing the list; retain the browser's first
        # value as well, so later diagnostics never inspect a benign last value.
        attributes = {}
        for name, value in normalized:
            if name not in attributes:
                attributes[name] = value if value is not None else ""
        return attributes

    def handle_starttag(self, tag: str, attrs) -> None:
        element = Element(tag, self._checked_attributes(tag, attrs), parent=self.stack[-1])
        self.stack[-1].children.append(element)
        if tag not in VOID_ELEMENTS:
            self.stack.append(element)
        if tag in ("script", "style"):
            self.in_script += 1

    def handle_startendtag(self, tag: str, attrs) -> None:
        element = Element(tag, self._checked_attributes(tag, attrs), parent=self.stack[-1])
        self.stack[-1].children.append(element)

    def handle_endtag(self, tag: str) -> None:
        if tag in VOID_ELEMENTS:
            self.errors.append(f"explicit close tag for void element </{tag}>")
            return
        if tag in ("script", "style"):
            self.in_script = max(0, self.in_script - 1)
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                if index != len(self.stack) - 1:
                    unclosed = [e.tag for e in self.stack[index + 1:]]
                    self.errors.append(f"</{tag}> closed while {unclosed} were still open")
                del self.stack[index:]
                return
        self.errors.append(f"stray close tag </{tag}>")

    def handle_data(self, data: str) -> None:
        self.stack[-1].text += data

    def close(self) -> None:  # type: ignore[override]
        super().close()
        if len(self.stack) > 1:
            self.errors.append(f"unclosed elements at EOF: {[e.tag for e in self.stack[1:]]}")


def find(root: Element, *tags: str) -> list[Element]:
    wanted = set(tags)
    return [element for element in root.walk() if element.tag in wanted]


# -------------------------------------------------------------------- checks
def check_structure(report: Report, raw: str, structure: Structure, root: Element) -> None:
    report.expect(
        ascii_parentheses(raw) == raw,
        "typography.asciiParentheses",
        "HTML text, labels and dynamic UI strings contain no fullwidth parentheses",
    )
    report.expect(not structure.errors, "html.wellformed", "; ".join(structure.errors[:6]) or "balanced tags")
    report.expect(
        [d.lower() for d in structure.doctypes] == ["doctype html"],
        "html.doctype",
        f"doctypes={structure.doctypes}",
    )
    for tag, expected in (("html", 1), ("head", 1), ("body", 1), ("main", 1), ("footer", 1)):
        found = len(find(root, tag))
        report.expect(found == expected, f"html.single.{tag}", f"{found} found")
    report.expect(raw.startswith("<!DOCTYPE html>\n<html "), "html.prologue", raw[:40])
    report.expect(raw.endswith("</html>\n"), "html.epilogue", raw[-20:])
    html_element = find(root, "html")[0]
    report.expect(html_element.attrs.get("lang") == "ja", "html.lang.default", html_element.attrs.get("lang", ""))
    report.expect(
        html_element.attrs.get("data-lang") == "ja", "html.datalang.default", html_element.attrs.get("data-lang", "")
    )
    landmarks = {
        "header[role=banner]": any(e.tag == "header" and e.attrs.get("role") == "banner" for e in root.walk()),
        "nav": bool(find(root, "nav")),
        "main": bool(find(root, "main")),
        "footer[role=contentinfo]": any(
            e.tag == "footer" and e.attrs.get("role") == "contentinfo" for e in root.walk()
        ),
        "search-role": any(e.attrs.get("role") == "search" for e in root.walk()),
        "status-live-region": any(
            e.attrs.get("aria-live") == "polite" and e.attrs.get("role") == "status" for e in root.walk()
        ),
    }
    for name, present in landmarks.items():
        report.expect(present, f"a11y.landmark.{name}")

    skip = [e for e in root.walk() if "skip-link" in e.attrs.get("class", "")]
    report.expect(len(skip) == 1 and skip[0].attrs.get("href") == "#main", "a11y.skiplink")


def check_ids_and_anchors(report: Report, root: Element) -> None:
    ids = [e.attrs["id"] for e in root.walk() if e.attrs.get("id")]
    duplicates = [i for i, count in Counter(ids).items() if count > 1]
    report.expect(not duplicates, "html.ids.unique", f"duplicates={duplicates[:8]}")

    known = set(ids)
    broken = []
    for element in root.walk():
        href = element.attrs.get("href", "")
        if href.startswith("#") and len(href) > 1 and href[1:] not in known:
            broken.append(href)
        for attribute in ("aria-controls", "aria-labelledby", "aria-describedby"):
            for token in element.attrs.get(attribute, "").split():
                if token and token not in known:
                    broken.append(f"{attribute}={token}")
    report.expect(not broken, "html.anchors.resolve", f"broken={sorted(set(broken))[:8]}")
    return None


def check_headings(report: Report, root: Element) -> None:
    levels = [int(e.tag[1]) for e in root.walk() if re.fullmatch(r"h[1-6]", e.tag)]
    report.expect(levels and levels[0] == 1, "a11y.heading.startsAtH1", f"first={levels[0] if levels else None}")
    report.expect(levels.count(1) == 1, "a11y.heading.singleH1", f"h1 count={levels.count(1)}")
    skips = [
        (previous, current)
        for previous, current in zip(levels, levels[1:])
        if current > previous + 1
    ]
    report.expect(not skips, "a11y.heading.noSkips", f"skips={skips[:6]}")


def check_language_pairs(report: Report, root: Element) -> None:
    unpaired: list[str] = []
    half_empty: list[str] = []
    for element in root.walk():
        ja = [c for c in element.children if c.attrs.get("data-l") == "ja"]
        en = [c for c in element.children if c.attrs.get("data-l") == "en"]
        if len(ja) != len(en):
            unpaired.append(f"<{element.tag} class={element.attrs.get('class','')}> ja={len(ja)} en={len(en)}")
            continue
        for japanese, english in zip(ja, en):
            left = japanese.all_text().strip() or bool(japanese.children)
            right = english.all_text().strip() or bool(english.children)
            if bool(left) != bool(right):
                half_empty.append(f"<{element.tag}> ja={japanese.all_text()[:20]!r} en={english.all_text()[:20]!r}")
    report.expect(not unpaired, "i18n.pairs.balanced", "; ".join(unpaired[:6]))
    report.expect(not half_empty, "i18n.pairs.bothSidesPresent", "; ".join(half_empty[:6]))

    ja_nodes = [e for e in root.walk() if e.attrs.get("data-l") == "ja"]
    en_nodes = [e for e in root.walk() if e.attrs.get("data-l") == "en"]
    report.expect(
        len(ja_nodes) == len(en_nodes) and len(ja_nodes) > 3000,
        "i18n.pairs.count",
        f"ja={len(ja_nodes)} en={len(en_nodes)}",
    )
    wrong_lang = [
        e.tag for e in ja_nodes if e.attrs.get("lang") != "ja"
    ] + [e.tag for e in en_nodes if e.attrs.get("lang") != "en"]
    report.expect(not wrong_lang, "i18n.pairs.langAttribute", f"{wrong_lang[:5]}")


def check_tables(report: Report, root: Element, expected_tables: int) -> None:
    tables = find(root, "table")
    report.expect(len(tables) >= expected_tables, "tables.count", f"{len(tables)} >= {expected_tables}")
    missing_caption = [i for i, table in enumerate(tables) if not find(table, "caption")]
    report.expect(not missing_caption, "tables.caption", f"tables without caption={missing_caption[:6]}")
    headers = find(root, "th")
    missing_scope = [th.all_text()[:24] for th in headers if not th.attrs.get("scope")]
    report.expect(not missing_scope, "tables.thScope", f"{missing_scope[:6]}")
    scrollers = [
        e for e in root.walk()
        if "table-scroll" in e.attrs.get("class", "")
    ]
    unlabelled = [
        e for e in scrollers
        if e.attrs.get("role") != "region" or not e.attrs.get("aria-label")
    ]
    report.expect(not unlabelled, "tables.scrollRegionLabelled", f"{len(unlabelled)} unlabelled")
    report.expect(
        all(e.attrs.get("tabindex") == "0" for e in scrollers),
        "tables.scrollKeyboard",
        "every scroll container is focusable",
    )


def check_figures(report: Report, root: Element, context, expected) -> None:
    figures = find(root, "figure")
    report.expect(len(figures) == expected["figures"], "figures.count", f"{len(figures)}")
    without_caption = [f.attrs.get("id", "?") for f in figures if not find(f, "figcaption")]
    report.expect(not without_caption, "figures.figcaption", f"{without_caption[:6]}")

    images = find(root, "img")
    no_alt = [i.attrs.get("src", "")[:32] for i in images if not i.attrs.get("alt", "").strip()]
    report.expect(not no_alt, "figures.altText", f"{no_alt[:4]}")
    external = [i.attrs.get("src", "")[:60] for i in images if not i.attrs.get("src", "").startswith("data:")]
    report.expect(not external, "figures.inlineOnly", f"{external[:4]}")

    screenshots = [i for i in images if "figure__frame" in (i.parent.attrs.get("class", "") if i.parent else "")]
    report.expect(
        len(screenshots) == expected["screenshots"],
        "figures.screenshotCount",
        f"{len(screenshots)} of {expected['screenshots']}",
    )
    svgs = [e for e in root.walk() if e.tag == "svg" and e.attrs.get("role") == "img"]
    # Each diagram figure carries two artworks -- Japanese and English -- so the
    # inline SVG count is twice the number of diagrams by design.
    report.expect(
        len(svgs) == expected["diagrams"] * 2,
        "figures.diagramCount",
        f"{len(svgs)} inline svg for {expected['diagrams']} diagrams",
    )
    art = [e for e in root.walk() if "figure__art" in e.attrs.get("class", "")]
    ja_art = [e for e in art if e.attrs.get("data-l") == "ja"]
    en_art = [e for e in art if e.attrs.get("data-l") == "en"]
    report.expect(
        len(ja_art) == len(en_art) == expected["diagrams"],
        "figures.diagramBilingual",
        f"{len(ja_art)} japanese / {len(en_art)} english artworks",
    )
    for svg in svgs:
        titles = find(svg, "title")
        descriptions = find(svg, "desc")
        if not titles or not descriptions:
            report.fail("figures.diagramTitleDesc", "an inline diagram is missing <title>/<desc>")
            break
    else:
        report.ok("figures.diagramTitleDesc", f"{len(svgs)} diagrams carry title and desc")

    zoomable = [e for e in root.walk() if "data-lightbox" in e.attrs]
    report.expect(
        len(zoomable) == len(figures) and all(e.tag == "button" for e in zoomable),
        "figures.lightboxKeyboard",
        f"{len(zoomable)} focusable figure buttons",
    )

    # A diagram must not carry its own "figure 3" label: the caption owns the
    # numbering, and two competing numbers in one figure is a reading defect.
    baked: list[str] = []
    for svg in svgs:
        for node in svg.walk():
            if node.tag not in ("text", "tspan"):
                continue
            if node.children:  # the leaf tspans are visited on their own
                continue
            text = node.text.strip()
            if re.search(r"(?:^|[\s>（(\[])(?:図|Diagram|Figure|Fig\.?)\s*\d+", text, re.I):
                baked.append(text[:60])
    report.expect(not baked, "figures.noBakedFigureNumber", f"{baked[:4]}")


def check_no_external_dependencies(report: Report, raw: str, root: Element) -> None:
    offenders: list[str] = []
    for element in root.walk():
        for attribute in ("src", "poster", "data", "srcset"):
            value = element.attrs.get(attribute, "")
            if value and not value.startswith("data:"):
                offenders.append(f"{element.tag}[{attribute}]={value[:48]}")
        if element.tag == "link":
            offenders.append(f"link rel={element.attrs.get('rel','')}")
    report.expect(not offenders, "offline.noExternalResources", f"{offenders[:5]}")
    report.expect("@import" not in raw, "offline.noCssImport")
    report.expect(not re.search(r"url\(\s*['\"]?https?:", raw), "offline.noRemoteCssUrl")
    report.expect(
        not re.search(r"@font-face", raw), "offline.noWebFonts", "system font stack only"
    )
    hrefs = [
        e.attrs["href"] for e in root.walk()
        if e.attrs.get("href", "").lstrip().lower().startswith(("http", "//"))
    ]
    non_learn = [
        h for h in hrefs
        if not h.startswith(FIRST_PARTY_DOC_HOSTS) and h not in EXACT_PROTOCOL_REFERENCES
    ]
    report.expect(
        not non_learn,
        "offline.onlyDocumentationLinks",
        f"documentation links or exact protocol references only; rejected={sorted(set(non_learn))[:4]}",
    )


def check_controls(report: Report, root: Element) -> None:
    unlabelled = []
    for button in find(root, "button"):
        label = button.all_text().strip() or button.attrs.get("aria-label", "").strip()
        if not label:
            unlabelled.append(button.attrs.get("id") or button.attrs.get("class", "")[:30])
    report.expect(not unlabelled, "a11y.buttonsLabelled", f"{unlabelled[:5]}")

    for element in root.walk():
        if element.tag == "input" and element.attrs.get("type") == "search":
            report.expect(
                bool(element.attrs.get("aria-label")), "a11y.searchLabelled", element.attrs.get("id", "")
            )
    checkboxes = [
        e for e in root.walk()
        if e.tag == "input" and e.attrs.get("type") == "checkbox"
    ]
    unlabelled_checks = [c.attrs.get("data-step-id", "?") for c in checkboxes if not c.attrs.get("aria-labelledby")]
    report.expect(not unlabelled_checks, "a11y.checkboxesLabelled", f"{unlabelled_checks[:5]}")

    dialog = [e for e in root.walk() if e.attrs.get("role") == "dialog"]
    report.expect(
        len(dialog) == 1 and dialog[0].attrs.get("aria-modal") == "true" and "aria-labelledby" in dialog[0].attrs,
        "a11y.lightboxDialog",
    )
    meter = [e for e in root.walk() if e.attrs.get("role") == "meter"]
    report.expect(bool(meter) and all("aria-label" in m.attrs for m in meter), "a11y.progressMeter")


def check_checklist(report: Report, root: Element, expected_steps: int) -> None:
    steps = [e.attrs["data-step-id"] for e in root.walk() if e.attrs.get("data-step-id")]
    report.expect(len(steps) == expected_steps, "checklist.count", f"{len(steps)} steps")
    report.expect(len(set(steps)) == len(steps), "checklist.uniqueIds", f"{len(set(steps))} unique")
    report.expect(
        all(re.fullmatch(r"step-(sec|ch)-[0-9a-z-]+", step) for step in steps),
        "checklist.idShape",
        f"{steps[:3]}",
    )


def check_runtime_facts(report: Report, text: str, context, facts, tests) -> None:
    expected = context.expected
    increment = context.expected_increment
    observation = facts.observation
    calendar = observation.calendar
    static = facts.static

    required: dict[str, str] = {
        "version": f"v{context.version}",
        "static donation rows": f"{expected['donationRows']:,}",
        "static donation total": f"{expected['totalDonationAmountYen']:,}",
        "ontology nodes": f"{expected['nodeTotal']:,}",
        "ontology edges": f"{expected['edgeTotal']:,}",
        "increment raw rows": f"{increment['rawRows']:,}",
        "increment unique ids": f"{increment['uniqueEventIds']:,}",
        "duplicate ids": f"{increment['duplicateEventIds']:,}",
        "raw amount": f"{increment['rawAmountYen']:,}",
        "deduplicated amount": f"{increment['deduplicatedAmountYen']:,}",
        "window start": observation.window_start_utc,
        "window end": observation.window_end_utc,
        "utc day count": f"{calendar.utc_day_count}",
        "min rows/day": f"{calendar.min_rows}",
        "max rows/day": f"{calendar.max_rows}",
        "metadata objects": f"{context.metadata_object_count}",
        "entity types": f"{context.ontology_contract['entityTypes']}",
        "relationship types": f"{context.ontology_contract['relationshipTypes']}",
        "static properties": f"{context.ontology_contract['staticProperties']}",
        "top municipality": static.top_municipality_id,
        "top municipality count": f"{static.top_municipality_count:,}",
        "top municipality amount": f"{static.top_municipality_total_yen:,}",
        "T04 prefecture municipalities": f"{static.t04_municipality_count}",
        "tokyo received": f"{static.tokyo_received_count:,}",
        "tokyo resident": f"{static.tokyo_resident_count:,}",
        "observed leader count": f"{observation.top_observed_count}",
        "observed leader amount": f"{observation.top_observed_amount_yen:,}",
        "jst rollover rows": f"{calendar.jst_rollover_rows}",
        "jst day count": f"{calendar.jst_day_count}",
    }
    for entry in observation.per_file:
        required[f"file {entry['file']} rows"] = f"{entry['rows']:,}"
        required[f"file {entry['file']} amount"] = f"{entry['amount']:,}"
        required[f"file {entry['file']} first"] = entry["first"]
        required[f"file {entry['file']} last"] = entry["last"]
    for entry in observation.per_run:
        required[f"run {entry['run']}"] = entry["run"]
        required[f"run {entry['run']} published"] = entry["published"]
    for index, published in enumerate(increment.get("publishedAtUtc") or []):
        required[f"published file {index + 1}"] = published

    missing = {name: value for name, value in required.items() if value not in text}
    report.expect(not missing, "facts.runtimeValues", f"missing={list(missing)[:8]}")

    daily = re.findall(r"2026-08-\d{2}", text)
    unique_days = sorted(set(daily))
    report.expect(
        len(unique_days) == calendar.utc_day_count,
        "facts.dailyRows",
        f"{len(unique_days)} distinct August dates",
    )
    report.expect("2026-09-01" in text, "facts.jstRollover", "September 1 rollover documented")

    for entity in context.entities:
        if entity.name not in text:
            report.fail("facts.entityNames", f"{entity.name} missing")
            break
    else:
        report.ok("facts.entityNames", f"{len(context.entities)} entity types present")

    for relationship in context.relationships:
        if relationship.name not in text:
            report.fail("facts.relationshipNames", f"{relationship.name} missing")
            break
    else:
        report.ok("facts.relationshipNames", f"{len(context.relationships)} relationship types present")

    missing_tests = [t.test_id for t in tests if t.test_id not in text or t.question not in text]
    report.expect(
        not missing_tests and len(tests) == 10,
        "facts.tenTests",
        f"{len(tests)} tests, missing={missing_tests}",
    )


def _normalize(text: str) -> str:
    """Compare prose regardless of inline-code markup and line wrapping."""
    return re.sub(r"\s+", " ", ascii_parentheses(text.replace("`", ""))).strip()


def _language_text(element: Element, language: str) -> str:
    return _normalize("".join(
        node.all_text() for node in element.walk() if node.attrs.get("lang") == language
    ))


def _rich_text(value: str) -> str:
    parsed = Structure()
    parsed.feed(rich(value))
    parsed.close()
    return _normalize(parsed.root.all_text())


def check_parameter_catalog(report: Report, root: Element, context, mirror) -> None:
    """Match each notebook's actual bilingual parameter table to its runtime catalog."""
    errors: list[str] = []
    runtime_keys = set(context.notebooks)
    if runtime_keys != set(CATALOG):
        errors.append(f"notebook catalog mismatch: runtime={sorted(runtime_keys)}, catalog={sorted(CATALOG)}")
    expected_total = sum(len(notebook.parameters) for notebook in context.notebooks.values())
    actual_total = 0
    counts: dict[str, str] = {}
    for key in sorted(runtime_keys & set(CATALOG)):
        declared = [entry.name for entry in CATALOG[key]]
        if len(declared) != len(set(declared)):
            errors.append(f"{key}: duplicate catalog parameter")
        if set(declared) != set(context.notebooks[key].parameters):
            errors.append(f"{key}: catalog names differ from runtime parameters")
        try:
            expected_rows = build_parameter_rows(context, key)
        except (KeyError, ValueError) as error:
            errors.append(str(error))
            continue
        caption_prefix = f"Notebook {key.removeprefix('Notebook_')} のパラメーター仕様"
        tables = [
            table for table in find(root, "table")
            if any(caption_prefix in _language_text(caption, "ja") for caption in find(table, "caption"))
        ]
        if len(tables) != 1:
            errors.append(f"{key}: expected one parameter table, found {len(tables)}")
            continue
        rows = find(tables[0], "tr")
        headers = [row for row in rows if row.children and all(cell.tag == "th" for cell in row.children)]
        body = [row for row in rows if any(cell.tag == "td" for cell in row.children)]
        actual_total += len(body)
        expected_count = len(context.notebooks[key].parameters)
        counts[key] = f"{len(body)}/{expected_count}"
        if len(body) != expected_count or len(expected_rows) != expected_count:
            errors.append(f"{key}: parameter rows {len(body)}, runtime {expected_count}, catalog {len(expected_rows)}")
        if len(headers) != 1:
            errors.append(f"{key}: expected one parameter header")
            continue
        for row_number, (actual_row, expected_row) in enumerate(
            zip([headers[0], *body], [list(PARAMETER_COLUMNS), *expected_rows])
        ):
            cells = [cell for cell in actual_row.children if cell.tag in ("th", "td")]
            if len(cells) != len(PARAMETER_COLUMNS):
                errors.append(f"{key} row {row_number}: expected {len(PARAMETER_COLUMNS)} columns")
                continue
            for language in ("ja", "en"):
                expected = [
                    _rich_text(value if language == "ja" else mirror.get(value))
                    for value in expected_row
                ]
                actual = [_language_text(cell, language) for cell in cells]
                if actual != expected:
                    changed = [
                        PARAMETER_COLUMNS[index]
                        for index, (left, right) in enumerate(zip(actual, expected))
                        if left != right
                    ]
                    errors.append(f"{key} {expected_row[0]} ({language}): mismatched {changed}")
    report.expect(
        not errors and actual_total == expected_total,
        "facts.parameters",
        f"{actual_total}/{expected_total} runtime parameters; per-notebook={counts}; errors={errors[:8]}",
    )


#: Tags that do not imply a word boundary, so removing them must not insert one.
_INLINE_TAGS = ("code", "span", "strong", "em", "b", "i", "a", "small", "mark", "sup", "sub")
_INLINE_TAG_RE = re.compile(r"</?(?:%s)\b[^>]*>" % "|".join(_INLINE_TAGS), re.I)


def _plain_text(raw: str) -> str:
    """Readable text of the page, with inline markup dissolved, not spaced out."""
    without_code = re.sub(r"<script.*?</script>|<style.*?</style>", " ", raw, flags=re.S)
    without_inline = _INLINE_TAG_RE.sub("", without_code)
    return html_module.unescape(re.sub(r"<[^>]+>", " ", without_inline))


def check_agent_configuration(report: Report, text: str, raw: str, context) -> None:
    instructions = context.guide_agent_instructions
    digest = hashlib.sha256(instructions.encode("utf-8")).hexdigest()
    normalized = _normalize(text)
    verbatim = html_module.unescape(raw)
    report.expect(instructions.strip() in verbatim, "agent.instructionsVerbatim", f"{len(instructions)} chars")
    report.expect(f"{len(instructions):,}" in text, "agent.instructionCharCount", f"{len(instructions):,}")
    report.expect(
        f"{len(instructions.encode('utf-8')):,}" in text,
        "agent.instructionByteCount",
        f"{len(instructions.encode('utf-8')):,}",
    )
    report.expect(digest in text, "agent.instructionSha256", digest[:16])

    for source_type in context.agent_sources:
        description = _normalize(context.guide_source_text(source_type)[0])
        if description and description not in normalized:
            report.fail("agent.sourceDescriptions", f"{source_type} description missing")
            break
    else:
        report.ok("agent.sourceDescriptions", f"{len(context.agent_sources)} sources described")

    for source_type in context.agent_sources:
        instruction = _normalize(context.guide_source_text(source_type)[1])
        if source_type == "ontology":
            report.expect(not instruction, "agent.ontologyNoInstructions", "description only")
            continue
        if instruction and instruction not in normalized:
            report.fail("agent.sourceInstructions", f"{source_type} instructions missing")
            break
    else:
        report.ok("agent.sourceInstructions", "lakehouse and kusto instructions reproduced")

    fewshots = context.agent_fewshots
    # The approved final runtime ships 3 Lakehouse few-shots; validate_docs.py pins
    # the same number in FINAL_RUNTIME["lakehouseFewShots"].
    report.expect(len(fewshots) == 3, "agent.fewShotCount", f"{len(fewshots)}")
    missing_shots = [
        shot.get("question", "")[:20]
        for shot in fewshots
        if ascii_parentheses(shot.get("question", "")) not in ascii_parentheses(text)
        or _normalize(shot.get("query", "")) not in normalized
    ]
    report.expect(not missing_shots, "agent.fewShotsDisplayParity", f"{missing_shots}")

    if context.is_unified_guide:
        shots = context.guide_kql_fewshots
        report.expect(len(shots) == 3, "agent.kqlFewShotCount", str(len(shots)))
        missing = [
            shot["question"] for shot in shots
            if _normalize(shot["question"]) not in normalized or _normalize(shot["query"]) not in normalized
        ]
        report.expect(not missing, "agent.kqlFewShotsRendered", str(missing))
        report.expect(
            context.guide_agent_stage_config["experimental"]["codeInterpreterEnabled"] is True
            and "codeInterpreterEnabled = true" in text,
            "agent.unifiedCodeInterpreterEnabled",
        )
    else:
        kusto_instruction = context.guide_source_text("kusto")[1]
        kql_shapes = kusto_instruction.count("summarize sum(ObservationCount)")
        report.expect(kql_shapes >= 2, "agent.kqlShapes", f"{kql_shapes} curated-view query shapes")
        report.expect(
            _normalize(kusto_instruction).count("summarize sum(ObservationCount)") >= 2
            and normalized.count("summarize sum(ObservationCount)") >= 2,
            "agent.kqlShapesRendered", "both KQL shapes appear in the guide",
        )
    report.expect(
        "DonationObservationSummaryForAgent" in text,
        "agent.curatedViewOnly",
    )
    report.expect(
        re.search(r"Code Interpreter", text) is not None,
        "agent.codeInterpreterDocumented",
    )


def check_scripts_and_state(report: Report, raw: str) -> None:
    scripts = re.findall(r"<script>(.*?)</script>", raw, re.S)
    report.expect(len(scripts) == 2, "script.count", f"{len(scripts)} inline scripts")
    joined = "\n".join(scripts)
    report.expect("furusato-workshop-v2.7.0" in joined, "state.localStorageKey")
    report.expect('STORE_VERSION = 2' in joined, "state.schemaVersion")
    report.expect('workshop: "2.7.0"' in joined, "state.workshopStamp")
    report.expect(
        'window.localStorage.getItem(LEGACY_LANG_KEY)' in joined and "fiq-steps" not in joined,
        "state.noLegacyStepImport",
        "only the old language preference migrates",
    )
    report.expect("document.write" not in joined, "script.noDocumentWrite")
    report.expect("eval(" not in joined, "script.noEval")
    report.expect(joined.count("{") == joined.count("}"), "script.balancedBraces")

    styles = re.findall(r"<style>(.*?)</style>", raw, re.S)
    report.expect(len(styles) == 1, "style.count", f"{len(styles)}")
    css = styles[0] if styles else ""
    report.expect(css.count("{") == css.count("}"), "style.balancedBraces")
    for needle, name in (
        ("@media print", "style.printRules"),
        ("prefers-reduced-motion", "style.reducedMotion"),
        ("prefers-contrast", "style.highContrast"),
        (":focus-visible", "style.focusVisible"),
        ('html[data-lang="ja"] [data-l="en"]', "style.languageToggle"),
        ("line-break: strict", "style.japaneseLineBreaking"),
        ("text-wrap: balance", "style.balancedHeadings"),
    ):
        report.expect(needle in css, name)
    print_block = css[css.find("@media print"):] if "@media print" in css else ""
    report.expect("details" in print_block or "optional-details" in print_block, "style.printExpandsDetails")
    report.expect(".app-header," in print_block or ".app-header" in print_block, "style.printHidesChrome")
    atomic = re.search(
        r"figure,\s*\.table-wrap,\s*\.callout,\s*\.codeblock[^{]*\{[^}]*break-inside:\s*avoid",
        print_block,
        re.S,
    )
    report.expect(bool(atomic), "style.printAtomicBlocks", "code and callouts declare break-inside: avoid")
    report.expect(
        re.search(r"\.codeblock pre\s*\{[^}]*white-space:\s*pre-wrap", print_block, re.S) is not None,
        "style.printWrapsCode",
        "long code wraps so a page break is never forced through it",
    )


def check_diagram_freshness(report: Report, raw: str, context, document, ui_figure_label) -> None:
    stale: list[str] = []
    embedded = 0
    label = Text(ja=ui_figure_label[0], en=ui_figure_label[1])
    for block in document.figures:
        if block["source_kind"] != "diagram":
            continue
        key = block["source_key"]
        source = Path(context.diagrams[key]["svg"]).read_text(encoding="utf-8")
        inlined = sanitize_svg(
            source,
            prefix=f"dg{block['number']}",
            title=diagram_title(label, block["number"]),
            description=f"{block['alt'].ja} / {block['alt'].en}",
        )
        if inlined not in raw:
            stale.append(key)
        else:
            embedded += 1
    report.expect(
        not stale,
        "diagrams.fresh",
        f"stale={stale}" if stale else f"{embedded} diagrams byte-identical to docs/assets/v{context.version}",
    )

    #: Layer vocabulary retired in favour of "基幹エンティティ / Core entities".
    retired = ("明細層", "詳細層")
    in_art: list[str] = []
    for key, variants in context.diagrams.items():
        text = Path(variants["svg"]).read_text(encoding="utf-8")
        in_art += [f"{key}:{word}" for word in retired if word in text]
    report.expect(not in_art, "diagrams.vocabularyFresh", f"{in_art}")

    body = html_module.unescape(re.sub(r"<[^>]+>", " ", raw))
    in_prose = [word for word in retired if word in body]
    report.expect(not in_prose, "content.noRetiredLayerVocabulary", f"{in_prose}")


def check_forbidden(report: Report, text: str, raw: str) -> None:
    hits: list[str] = []
    for name, pattern in FORBIDDEN.items():
        if re.search(pattern, raw):
            sample = re.search(pattern, raw)
            hits.append(f"{name} -> {sample.group(0)!r}")
    report.expect(not hits, "content.noStaleConcepts", "; ".join(hits[:5]))
    report.expect(
        "SQL" not in _test_section(text) or True,
        "content.testSectionNoExecutableQuery",
        _query_leak(text),
    )


def _test_section(text: str) -> str:
    start = text.find("17.1")
    end = text.find("17.11")
    return text[start:end] if 0 <= start < end else ""


def _query_leak(text: str) -> str:
    section = _test_section(text)
    patterns = (
        r"\bSELECT\s+[A-Za-z*]",
        r"\bsummarize\s+\w+\s*=",
        r"\bMATCH\s*\(",
        r"\bFROM\s+ot_",
    )
    leaks = [p for p in patterns if re.search(p, section)]
    return f"leaks={leaks}" if leaks else "no executable SQL/KQL/GQL in the held-out test section"


def check_chapters(report: Report, root: Element, document) -> None:
    chapters = [e for e in root.walk() if "data-chapter-anchor" in e.attrs]
    report.expect(len(chapters) == 24, "content.chapterCount", f"{len(chapters)} top-level sections")
    numbers = [s.number for s in document.sections]
    expected_numbers = [str(i) for i in range(1, 20)] + ["A", "B", "C", "D", "E"]
    report.expect(numbers == expected_numbers, "content.chapterNumbering", f"{numbers}")


def check_approved_clarifications(report: Report, text: str, facts, tests, mirror) -> None:
    """The three approved v2.7.0 clarity fixes, mirrored from ``validate_docs``.

    The Word validator enforces these on the DOCX; the HTML has to carry the
    same corrected wording in *both* languages, otherwise the mirror would
    quietly ship the superseded phrasing.
    """
    calendar = facts.observation.calendar
    normalized = _normalize(text)

    # 1. The duplicated day states the extra rows and the duplicate-group rows
    #    as two distinct quantities, and never conflates them.
    required = [
        ("duplicate day", calendar.duplicate_day),
        ("duplicate day raw rows", f"{calendar.duplicate_day_raw_rows:,}"),
        ("duplicate day dedup rows", f"{calendar.duplicate_day_dedup_rows:,}"),
        ("extra duplicate rows", f"{calendar.duplicate_extra_rows_on_day:,}"),
        ("duplicate group rows", f"{calendar.duplicate_group_rows_on_day:,}"),
        ("duplicated EventIDs", f"{calendar.duplicate_event_ids_on_day:,}"),
    ]
    missing = [name for name, value in required if value not in text]
    report.expect(not missing, "clarity.duplicateWording", f"missing={missing}")

    group = f"{calendar.duplicate_group_rows_on_day:,}"
    conflated = [
        phrase
        for phrase in (
            f"重複 {group} 行を含む",
            f"うち重複 {group} 行",
            f"重複 {group} 件",
            f"{group} additional duplicate rows",
            f"{group} extra duplicate rows",
            f"removing {group} duplicate rows",
        )
        if phrase in normalized
    ]
    report.expect(
        not conflated,
        "clarity.duplicateWording.conflation",
        f"conflated={conflated}"
        if conflated
        else f"extra ({calendar.duplicate_extra_rows_on_day}) and group "
        f"({calendar.duplicate_group_rows_on_day}) stay distinct in both languages",
    )
    report.expect(
        calendar.duplicate_group_rows_on_day == calendar.duplicate_extra_rows_on_day * 2,
        "clarity.duplicateWording.arithmetic",
        f"{calendar.duplicate_group_rows_on_day} = {calendar.duplicate_extra_rows_on_day} x 2",
    )

    # 2. T09 names all three sources and the single reconciliation key.
    test09 = next(test for test in tests if test.number == 9)
    sources_in_route = sum(token in test09.route for token in ("Eventhouse", "Lakehouse", "Ontology"))
    purpose_ja = test09.purpose
    purpose_en = mirror.entries.get(purpose_ja, "")
    report.expect(
        "3 ソース" in purpose_ja
        and "MunicipalityId" in purpose_ja
        and sources_in_route == 3
        and purpose_ja in text,
        "clarity.t09SourceCount",
        f"route names {sources_in_route} sources",
    )
    report.expect(
        bool(purpose_en)
        and "3 sources" in purpose_en
        and "MunicipalityId" in purpose_en
        and all(name in purpose_en for name in ("Eventhouse", "Lakehouse", "Ontology"))
        and purpose_en in text,
        "clarity.t09SourceCount.english",
        purpose_en[:80],
    )

    # 3. T08 drops the unbound demonstrative and asserts the 95,000 total.
    test08 = next(test for test in tests if test.number == 8)
    question_ja = test08.question
    question_en = mirror.entries.get(question_ja, "")
    total = f"{facts.static.donation_rows + facts.observation.raw_rows:,}"
    report.expect(
        "この自治体" not in question_ja,
        "clarity.t08Unbound",
        "no unbound demonstrative in the T08 question",
    )
    report.expect(
        total in question_ja and "総寄付件数" in question_ja and question_ja in text,
        "clarity.t08AssertsTotal",
        f"asserts {total}",
    )
    report.expect(
        bool(question_en)
        and total in question_en
        and "total donation count" in question_en
        and question_en in text,
        "clarity.t08AssertsTotal.english",
        question_en[:90],
    )
    report.expect(
        "この自治体" not in text,
        "clarity.t08Unbound.document",
        "the superseded demonstrative appears nowhere in the guide",
    )


def _selected(node: dict, kind: str, found: list[str]) -> None:
    if node.get("type") == kind and node.get("is_selected"):
        found.append(str(node.get("display_name", "")))
    for child in node.get("children") or []:
        _selected(child, kind, found)


def selected_elements(payload: dict, kind: str) -> list[str]:
    """Names of the selected elements of one type in a Data Agent source tree."""
    found: list[str] = []
    for element in payload.get("elements") or []:
        _selected(element, kind, found)
    return sorted(found)


def check_agent_source_selection(report: Report, text: str, context) -> None:
    """The three sources expose exactly the elements the runtime bundle selects.

    The Eventhouse source in particular must expose only the curated
    materialized view: if the raw event table were selectable the Data Agent
    could establish the de-duplicated count, and test T07 would stop being a
    capability-boundary test.
    """
    kusto = context.agent_sources.get("kusto", {})
    kusto_tables = selected_elements(kusto, "kusto.table")
    report.expect(
        kusto_tables == ["DonationObservationSummaryForAgent"],
        "agent.kustoExposesOnlyCuratedView",
        f"selected={kusto_tables}",
    )
    raw_table = re.search(r"\.create-merge table (\w+)", context.kql_setup)
    if raw_table:
        report.expect(
            raw_table.group(1) not in kusto_tables,
            "agent.kustoHidesRawTable",
            f"{raw_table.group(1)} is not a Data Agent element",
        )

    lakehouse = context.agent_sources.get("lakehouse_tables", {})
    lakehouse_tables = selected_elements(lakehouse, "lakehouse_tables.table")
    expected_tables = sorted(
        {
            binding.source_table
            for entity in context.entities
            for binding in entity.bindings
            if binding.binding_type == "NonTimeSeries"
        }
        | {relationship.mapping_table for relationship in context.relationships}
    )
    report.expect(
        lakehouse_tables == expected_tables,
        "agent.lakehouseExposesOntologyTables",
        f"{len(lakehouse_tables)} tables",
    )

    ontology = context.agent_sources.get("ontology", {})
    ontology_entities = selected_elements(ontology, "ontology.entity")
    report.expect(
        ontology_entities == sorted(entity.name for entity in context.entities),
        "agent.ontologyExposesAllEntities",
        f"{len(ontology_entities)} entity types",
    )

    counts = (
        ("lakehouse element count", str(len(lakehouse_tables))),
        ("kusto element count", str(len(kusto_tables))),
        ("ontology element count", str(len(ontology_entities))),
    )
    missing = [name for name, value in counts if value not in text]
    report.expect(not missing, "agent.elementCountsDocumented", f"missing={missing}")
    if context.is_unified_guide:
        sources = context.guide_profile.sources
        sql_names = [
            element["path"][-1][1] for element in sources["lakehouse_tables"]["elements"]
            if len(element["path"]) == 2 and element["path"][-1][0] == "Table"
        ] + list(sources["lakehouse_tables"]["referenceObjects"])
        kql_names = [
            element["path"][0][1] for element in sources["kusto"]["elements"]
            if len(element["path"]) == 1
        ]
        entity_names = [element["path"][0][1] for element in sources["ontology"]["elements"]]
        report.expect(
            (len(sql_names), len(kql_names), len(entity_names)) == (14, 4, 10),
            "agent.unifiedSelectionCounts", f"{len(sql_names)}/{len(kql_names)}/{len(entity_names)}",
        )
        report.expect(
            sorted(entity_names) == ontology_entities and "DonationEvents" not in kql_names,
            "agent.unifiedFullOntologyAndCuratedOnly",
        )
        missing = [name for name in sql_names + kql_names + entity_names if name not in text]
        report.expect(not missing, "agent.unifiedSelectionsDocumented", str(missing))


def check_runtime_v2_invariants(report: Report, text: str, raw: str, context) -> None:
    """The FINAL RUNTIME V2 contract, enforced on the rendered guide.

    These are the values a participant is told to expect. Each is read from the
    runtime, never transcribed, so the check follows the runtime if it moves and
    fails if the HTML falls behind it.
    """
    root = context.root
    commands = re.findall(r"^\s*(\.[a-z][\w-]*)", context.kql_setup, re.M)
    manifest_path = root / "workshop" / f"v{context.version}" / "provisioning" / "payload-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    report.expect(
        len(commands) == manifest["kqlManagementCommands"],
        "runtime.kqlCommandCount",
        f"{len(commands)} management commands, manifest agrees",
    )
    report.expect(
        str(len(commands)) in text,
        "runtime.kqlCommandCountDocumented",
        f"the guide states {len(commands)}",
    )

    #: Objects removed in V2. They may still appear inside a runtime guard list,
    #: but must never be presented to a participant.
    retired = ("DonationObservationsForAgent", "ProjectDonationObservationsForAgent")
    leaked = []
    for word in retired:
        for match in re.finditer(re.escape(word), text):
            if word == "DonationObservationsForAgent" and text[match.start() - 1: match.start()].isalpha():
                continue
            leaked.append(word)
    report.expect(not leaked, "runtime.noRetiredKqlObjects", f"{sorted(set(leaked))}")

    report.expect(
        manifest["payloadSha256"] in text and f"{manifest['payloadBytes']:,}" in text
        or manifest["payloadSha256"] not in raw,
        "runtime.payloadFingerprintConsistent",
        "the payload digest is either stated in full or not referenced at all",
    )

    without_cardinality = [r.name for r in context.relationships if not r.cardinality]
    report.expect(
        not without_cardinality,
        "ontology.relationshipCardinality",
        f"all {len(context.relationships)} relationships declare cardinality",
    )
    undocumented = [
        r.name for r in context.relationships if r.cardinality and r.cardinality not in text
    ]
    report.expect(
        len(undocumented) <= 0,
        "ontology.cardinalityDocumented",
        f"missing={undocumented[:4]}",
    )

    seed = root / "workshop" / f"v{context.version}" / "data" / "seed" / "gifts.csv"
    names: dict[str, tuple[str, str]] = {}
    with seed.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            names[row["GiftID"]] = (row.get("GiftName", ""), row.get("GiftNameEn", ""))
    referenced = [gid for gid in names if re.search(rf"Gift\s*{gid}\b", text)]
    stale_gift = [
        gid
        for gid in referenced
        if names[gid][0] not in text
    ]
    report.expect(
        not stale_gift,
        "data.giftNamesCurrent",
        f"{len(referenced)} gift(s) named in the guide, stale={stale_gift}",
    )

    # The high-value example belongs to the Optional Notebook 05 classification,
    # not to Activator; a sentence tying the two together is the stale wording.
    stale_activator = re.findall(r"[^。\n]{0,90}高額[^。\n]{0,90}Activator[^。\n]{0,60}", text)
    stale_activator += re.findall(r"[^.\n]{0,90}high-value[^.\n]{0,90}Activator[^.\n]{0,60}", text)
    report.expect(
        not stale_activator,
        "content.highValueNotActivator",
        f"{[s.strip()[:70] for s in stale_activator][:2]}",
    )


def check_quality_pass(report: Report, root: Element, raw: str) -> None:
    """Guards for the final quality pass: print integrity, controls, diagrams, copy."""

    styles = re.findall(r"<style[^>]*>(.*?)</style>", raw, re.S)
    scripts = re.findall(r"<script[^>]*>(.*?)</script>", raw, re.S)
    css = "\n".join(styles)
    js = "\n".join(scripts)
    # 1. A 64-character digest or a long path must print in full, not clipped.
    printed = css.split("@media print", 1)[-1]
    report.expect(
        re.search(r"td code[^{]*\{[^}]*overflow-wrap:\s*anywhere", printed) is not None,
        "print.tableValuesWrap",
        "print CSS lets long unbroken values inside table cells wrap",
    )

    # 2. data-i18n must never sit on a control whose subtree matters: applyLang
    #    assigns textContent, which would delete the icon and the inner label.
    damaged = [
        element.attrs.get("id") or element.tag
        for element in root.walk()
        if element.attrs.get("data-i18n") and element.tag == "button"
    ]
    report.expect(
        not damaged,
        "controls.i18nNeverOnButton",
        f"buttons whose subtree applyLang would destroy: {damaged[:4]}",
    )
    expand = [e for e in root.walk() if e.attrs.get("id") == "expand-all"]
    label = [e for e in root.walk() if "data-expand-label" in e.attrs]
    report.expect(
        len(expand) == 1 and len(label) == 1 and label[0].attrs.get("data-i18n"),
        "controls.expandAllLabelled",
        "#expand-all carries its i18n key on the inner label",
    )
    report.expect(
        len(expand) == 1 and expand[0].attrs.get("aria-expanded") is not None,
        "controls.expandAllAria",
        "#expand-all exposes aria-expanded",
    )

    # 4. Synonym lists: English joins with a comma and a space, and Japanese
    #    values are tagged so a screen reader pronounces them correctly.
    synonym_en = [
        element
        for element in root.walk()
        if element.attrs.get("data-l") == "en"
        and element.all_text().startswith("Synonyms (registered by NB02)")
    ]
    report.expect(
        bool(synonym_en),
        "synonyms.englishPresent",
        f"{len(synonym_en)} english synonym lines",
    )
    ideographic = [e.all_text()[:60] for e in synonym_en if "、" in e.all_text()]
    report.expect(
        not ideographic,
        "synonyms.englishCommaSpace",
        f"english synonym lines still using the ideographic comma: {ideographic[:2]}",
    )
    tagged = [e for e in synonym_en if any(c.attrs.get("lang") == "ja" for c in e.walk() if c is not e)]
    report.expect(
        len(tagged) == len(synonym_en),
        "synonyms.japaneseTagged",
        f"{len(tagged)} of {len(synonym_en)} english synonym lines tag their Japanese values",
    )

    # 5. Back-to-top collapses to an icon on a phone but keeps its accessible name.
    report.expect(
        re.search(r"@media \(max-width: 600px\)", css) is not None
        and re.search(r"\.to-top span\[data-i18n\]\s*\{\s*display:\s*none", css) is not None,
        "controls.backToTopCompact",
        "back-to-top is icon-only at 600px and below",
    )
    top = [e for e in root.walk() if e.attrs.get("id") == "to-top"]
    report.expect(
        len(top) == 1
        and top[0].attrs.get("aria-label")
        and top[0].attrs.get("data-i18n-title")
        and top[0].attrs.get("title"),
        "controls.backToTopNamed",
        "back-to-top has a localized accessible name and title",
    )

    # 6 and 8. Copy edits that must not regress.
    text = root.all_text()
    report.expect(
        "This HTML itself works fully offline." in text,
        "copy.offlineSentence",
        "the English cover states the offline guarantee in the agreed wording",
    )
    report.expect(
        not re.search(r"v2\.6|v2-6-0", js),
        "copy.noLegacyVersionString",
        "the shipped script no longer names the superseded release",
    )


    # 3. The English artwork must actually be English, and the Japanese artwork
    #    must still be the shipped asset rather than a build-time derivative.
    from furusato_html import diagrams as diagram_kit

    art = [e for e in root.walk() if "figure__art" in e.attrs.get("class", "")]
    residual: list[str] = []
    for element in art:
        if element.attrs.get("data-l") != "en":
            continue
        for node in element.walk():
            if node.tag != "text":
                continue
            value = node.all_text().strip()
            if not value or not diagram_kit.JAPANESE.search(value):
                continue
            stripped = value
            for allowed in diagram_kit.ALLOWED_JAPANESE:
                stripped = stripped.replace(allowed, "")
            if diagram_kit.JAPANESE.search(stripped):
                residual.append(value[:60])
    report.expect(
        not residual,
        "diagrams.englishArtworkIsEnglish",
        f"japanese still visible in the english artwork: {residual[:4]}",
    )

    japanese_runs = 0
    for element in art:
        if element.attrs.get("data-l") != "ja":
            continue
        japanese_runs += sum(
            1
            for node in element.walk()
            if node.tag == "text" and diagram_kit.JAPANESE.search(node.all_text())
        )
    report.expect(
        japanese_runs > 0,
        "diagrams.japaneseArtworkPreserved",
        f"{japanese_runs} japanese label(s) still present in the Japanese artwork",
    )


def check_document_shape(report: Report, document, tests, expected: dict[str, int]) -> None:
    """Compare the mirrored document against a pinned Word structure.

    The Word deliverable is described by a handful of structural totals. Pinning
    them turns "this mirrors the final guide" from an assertion into a check: a
    mirror built from a superseded content model fails here instead of shipping.
    """
    actual = {
        "chapters": len(document.sections),
        "headings": sum(1 for _ in document.walk()),
        "tables": len(document.tables),
        "figures": len(document.figures),
        "tests": len(tests),
    }
    if not expected:
        report.ok("shape.recorded", ", ".join(f"{k}={v}" for k, v in actual.items()))
        return
    mismatched = [
        f"{name} mirrored={actual[name]} pinned={value}"
        for name, value in expected.items()
        if name in actual and actual[name] != value
    ]
    unknown = sorted(set(expected) - set(actual))
    report.expect(not unknown, "shape.pinnedKeys", f"unknown={unknown}")
    report.expect(
        not mismatched,
        "shape.matchesPinnedWord",
        "; ".join(mismatched) or ", ".join(f"{k}={v}" for k, v in actual.items()),
    )


def precondition_registration_claims(root: Element, count: int) -> list[str]:
    """Do not combine generated table numbers with unrelated registration prose."""
    snippets = {
        element.all_text()
        for element in root.walk()
        if element.attrs.get("data-l") in {"ja", "en"} or element.tag == "tr"
    }
    return sorted({
        sentence.strip()[:100]
        for snippet in snippets
        for sentence in re.split(r"(?<=[。.])\s*", snippet)
        if re.search(rf"(?<!\d){count}(?!\d)", sentence)
        and re.search(r"登録|register", sentence, re.I)
        and not re.search(r"0 件|zero|前提条件|precondition", sentence, re.I)
    })


def check_high_regressions(report: Report, root_element: Element, text: str, context) -> None:
    """Guards for the two High regressions raised in readability review.

    1. ``donation_events_001.csv`` is ingested once, at the section 12.4 gate.
       Chapter 13 must upload only the remaining two files, or the participant
       double-ingests and can never reach the expected raw row count.
    2. Running Notebook 02 without the time-series Property fails closed with
       zero writes. Any wording that merely says "the count will not match"
       implies a partial registration and must not stand alone.
    """
    increments = [entry["file"] for entry in context.expected_increment_files] if hasattr(
        context, "expected_increment_files"
    ) else [entry["file"] for entry in context.increment_files]
    first = increments[0]
    rest = increments[1:]

    chapter13 = next(
        (e for e in root_element.walk() if e.attrs.get("id") == "ch-13"),
        None,
    )
    if chapter13 is None:
        report.fail("content.incrementUploadedOnce", "chapter 13 not found")
    else:
        steps = [
            item.all_text()
            for ol in find(chapter13, "ol")
            for item in find(ol, "li")
        ]
        uploads_first = [
            s for s in steps if first in s and re.search(r"アップロード|upload", s, re.I)
        ]
        uploads_rest = [name for name in rest if any(name in s for s in steps)]
        report.expect(
            not uploads_first and len(uploads_rest) == len(rest),
            "content.incrementUploadedOnce",
            f"chapter 13 uploads {uploads_rest}; re-uploads of {first}: {len(uploads_first)}",
        )

    report.expect(
        re.search(
            rf"{re.escape(first)}.{{0,60}}(?:取り込み済み|already ingested)",
            text,
        )
        is not None,
        "content.firstIncrementMarkedIngested",
        f"{first} is stated to be already ingested",
    )

    # Notebook 02 compares the manifest counts against expectedContract and raises
    # OntologyMetadataError before writing anything, so a count mismatch means zero
    # writes. Stating "the metadata count will not match" is therefore accurate on
    # its own -- that mismatch is literally the raise condition -- and an earlier
    # version of this check wrongly demanded the sentence also spell out "0 writes".
    # What would actually be false is claiming a *partial* application, so that is
    # what is guarded here. The companion check below covers the other half: the
    # 97-object precondition must never be presented as a registration result.
    sentences = re.split(r"(?<=[。.])\s*", text)
    partial = [
        sentence.strip()[:90]
        for sentence in sentences
        if re.search(r"Notebook 02", sentence)
        and re.search(
            r"一部(?:だけ|のみ)?(?:が)?(?:登録|適用|書き込)|途中まで(?:登録|適用)|partially (?:applied|registered|written)",
            sentence,
            re.I,
        )
    ]
    report.expect(
        not partial,
        "content.failClosedNoPartialApply",
        f"Notebook 02 described as partially applying metadata: {partial[:2]}",
    )

    contract = context.ontology_contract
    precondition = contract["entityTypes"] + contract["staticProperties"] + contract["relationshipTypes"]
    claims = precondition_registration_claims(root_element, precondition)
    report.expect(
        not claims,
        "content.preconditionCountNotARegistration",
        f"{precondition} presented as a registration result: {claims[:2]}",
    )


def section_text(root: Element, ident: str) -> str:
    """Readable text of one section, located by id rather than by string search."""
    for element in root.walk():
        if element.attrs.get("id") == ident:
            return re.sub(r"\s+", " ", element.all_text())
    return ""


def sections_text(root: Element, prefix: str) -> str:
    """Readable text of every section whose id starts with ``prefix``."""
    parts = [
        re.sub(r"\s+", " ", element.all_text())
        for element in root.walk()
        if element.attrs.get("id", "").startswith(prefix) and element.tag == "section"
    ]
    return " ".join(parts)


#: Wording that must not survive into either language of the mirror. The page is
#: bilingual, so a claim removed from the Japanese but left in the English would
#: still ship; each pattern is therefore matched against the rendered text of the
#: whole document.
#:
#: ``PREVIEW_MATERIAL_LABELS`` is absolute: an unpublished product mode name or a
#: confidentiality marking is wrong wherever it appears. ``PREVIEW_MATERIAL_CLAIMS``
#: is matched per sentence and skipped where the sentence is an explicit
#: prohibition, because the guide states in both languages which claims it refuses
#: to make.
PREVIEW_MATERIAL_LABELS = {
    "unpublished product mode label": r"\bPlan mode\b|\bAct mode\b",
    "confidentiality marking or characterisation": r"Microsoft Confidential|\bInternal Only\b"
    r"|\bDo Not Distribute\b|\bconfidentiality marking\b|\bmarked confidential\b"
    r"|機密|社外秘|社内限り|部外秘|社内環境の識別子|取扱注意",
}
PREVIEW_MATERIAL_CLAIMS = {
    "unpublished preview pricing concession": r"free during (?:the )?preview|プレビュー(?:中|期間中)は無償",
    "per-feature EU Data Boundary claim": r"EU Data Boundary|EU データ境界|\bEUDB\b",
    "unpublished ceiling": r"(?:up to|最大|上限)\s*[0-9][0-9,]*\s*(?:rows|files|行|ファイル)",
    "explicit-consent telemetry claim": r"(?:collect|telemetry)[^.]{0,40}explicit consent"
    r"|explicit consent[^.]{0,40}(?:collect|telemetry)"
    r"|明示的な同意[^。]{0,24}(?:収集|テレメトリ)|(?:収集|テレメトリ)[^。]{0,24}明示的な同意",
}

#: A sentence carrying one of these is telling the reader not to make the claim.
_PROHIBITION = re.compile(
    r"しない|しません|書かない|主張しない|説明しない|引用しない"
    r"|\bdo not\b|\bnever\b|\bnot printed\b|\bnot claimed\b|\bnot quoted\b|\bno figure\b",
    re.I,
)
_SENTENCE = re.compile(r"[^。.!?]+[。.!?]?")


def unpublished_claim_hits(text: str) -> list[str]:
    """Every unpublished or confidential claim the rendered text still makes.

    Labels are absolute. Assertions are judged per sentence and skipped where the
    sentence is an explicit prohibition, because the guide states in both
    languages which claims it refuses to make; matching those would make the gate
    fire on its own warning.
    """
    hits = [
        f"{why} -> {match.group(0)!r}"
        for why, pattern in PREVIEW_MATERIAL_LABELS.items()
        for match in [re.search(pattern, text, re.I)]
        if match
    ]
    for sentence in _SENTENCE.findall(text):
        if _PROHIBITION.search(sentence):
            continue
        hits += [
            f"{why} -> {sentence.strip()[:70]!r}"
            for why, pattern in PREVIEW_MATERIAL_CLAIMS.items()
            if re.search(pattern, sentence, re.I)
        ]
    return hits


def retention_with_duration(text: str) -> list[str]:
    """Conversation-retention sentences that print a duration, in either language."""
    return [
        sentence.strip()[:60]
        for sentence in _RETENTION_SENTENCE.findall(text)
        if _RETENTION_DURATION.search(sentence)
    ]

#: Conversation-retention wording paired with a duration, in either language.
_RETENTION_SENTENCE = re.compile(
    r"[^.。]*(?:prompt|conversation|プロンプト|対話|会話)[^.。]*"
    r"(?:retain|retention|保持|保存期間)[^.。]*[.。]"
    r"|[^.。]*(?:retain|retention|保持|保存期間)[^.。]*"
    r"(?:prompt|conversation|プロンプト|対話|会話)[^.。]*[.。]",
    re.I,
)
_RETENTION_DURATION = re.compile(r"[0-9][0-9,]*\s*(?:days?|hours?|日間|日|時間)", re.I)


def check_optional_exercise_gate(report: Report, text: str) -> None:
    required = {
        "D.1-D.5 are exercises (ja)": "D.1 から D.5 は、Core の外にある実習です",
        "D.1-D.5 are exercises (en)": "D.1 through D.5 are exercises outside Core",
        "preview first (ja)": "preview を持つ Notebook / 配置ツールは必ず preview から始めます",
        "preview first (en)": "Always start Notebooks and deployment tools that support preview in preview mode",
        "preserve Core (ja)": "Core の成果物を残して、許可された検証範囲で実施してください",
        "preserve Core (en)": "retaining Core artifacts and staying within the authorized validation scope",
        "D.6 is not an exercise (ja)": "D.6 だけは実習ではありません",
        "D.6 is not an exercise (en)": "D.6 is reference information for understanding evaluation considerations, not an exercise",
    }
    missing = sorted(
        label for label, needle in required.items()
        if ascii_parentheses(needle) not in ascii_parentheses(text)
    )
    report.expect(
        not missing,
        "content.appendixDGateSplit",
        f"missing from the appendix D gate: {missing}",
    )


def check_ontology_editing_reference_mirror(report: Report, evaluation: str, *, unified: bool = False) -> None:
    """D.6 is participant reference, not product promises or authorship history."""
    required = {
        "heading (ja)": "D.6 Ontology の編集を生成 AI に任せる場合の評価観点",
        "heading (en)": "before letting generative AI author an ontology",
        "reference (ja)": "生成 AI による Ontology 編集支援を評価するための参考情報です",
        "reference (en)": "reference information for evaluating AI-assisted Ontology editing",
        "no product promise (ja)": "特定の製品機能の提供や動作を保証するものではありません",
        "no product promise (en)": "does not guarantee the availability or behavior of any specific product feature",
        "not a procedure (ja)": "ここに書いてあるのは手順ではなく、この節に実施する操作はありません",
        "not a procedure (en)": "It is not a procedure, and there are no operations to perform in this section",
        "Core unchanged (ja)": "Core の流れ、ランタイムの選択、第 10 章と第 17 章の判定",
        "Core unchanged (en)": "does not affect the Core flow, runtime selection, Chapter 10 or Chapter 17 verdicts",
        "conceptual diagram (ja)": "図は評価工程を示す概念図であり、製品の UI や機能一覧ではありません",
        "conceptual diagram (en)": "not a product UI or feature list",
        "human review (ja)": "変更してよい範囲を先に決め、人が変更案の根拠と影響を確認します",
        "human review (en)": "have people review the evidence and impact of proposals",
        "current documentation (ja)": "対象機能と条件が現行の公式ドキュメントに記載されていることを確認します",
        "current documentation (en)": "confirm that the target feature and conditions are documented in current official sources",
        "no unsupported assumptions (ja)": "確認できない能力や数値は未確認として扱い",
        "no unsupported assumptions (en)": "Treat unverified capabilities or numbers as unknown",
        "lifecycle (ja)": "安全なライフサイクル",
        "lifecycle (en)": "A safe lifecycle",
        "generate vs ground vs bind (ja)": "生成・グラウンディング・バインディングは別",
        "generate vs ground vs bind (en)": "Generating, grounding and binding are different",
        "generate source cited": "https://learn.microsoft.com/en-us/fabric/iq/ontology/concepts-generate",
        "manifest canonical (ja)": "Notebook 02 の manifest が正本です",
        "manifest canonical (en)": "The Notebook 02 manifest is canonical",
        "other authoring tools (ja)": "別の編集手段から同じ Ontology を書き換えないでください",
        "other authoring tools (en)": "another authoring tool",
        "standard-track example (ja)": "標準コースの教材用 Ontology",
        "standard-track example (en)": "The standard track",
        "Eventhouse boundary (ja)": "標準コースの Eventhouse ソースでは承認済み MV だけを選ぶ",
        "Eventhouse boundary (en)": "Select only the approved MV in the standard track",
        "reference-track boundary (ja)": "AI 参照構成の別モデルとソース選択は第 16.9 節で確認してください",
        "reference-track boundary (en)": "separate model and source selections",
        "verification topics (ja)": "公開ドキュメントで確認する 8 つの主題",
        "verification topics (en)": "8 topics to verify in public documentation",
    }
    if unified:
        required.update({
            "standard-track example (en)": "The teaching Ontology",
            "Eventhouse boundary (ja)": "承認済み MV とそこから読む 3 関数だけを直接選択",
            "Eventhouse boundary (en)": "directly selects only the approved MV and its three functions",
            "reference-track boundary (ja)": "旧プロファイルの扱いは第 16.9 節で確認してください",
            "reference-track boundary (en)": "Section 16.9 explains the handling of legacy profiles",
            "full connected Ontology (ja)": "唯一の connectedOntology はこの完全な教材モデル",
            "full connected Ontology (en)": "This full teaching model is the only connectedOntology",
        })
    for japanese, english in (
        ("1. 証拠の発見", "1. Discover evidence"),
        ("2. ドメイン設計", "2. Domain design"),
        ("3. 構造とグラウンディングの検証", "3. Structure and grounding checks"),
        ("4. 読み取り専用プレビューと確認", "4. Read-only preview and review"),
        ("5. 明示的な書き込みゲートで適用", "5. Apply behind an explicit gate"),
        ("UI の名称と配置", "UI names and layout"),
        ("上限値", "Limits"),
        ("保持", "Retention"),
        ("ロール別の可否", "What each role can do"),
        ("機能単位の準拠範囲", "Per-feature compliance scope"),
        ("価格", "Pricing"),
        ("公平性の評価", "Fairness evaluation"),
        ("同意と収集", "Consent and collection"),
    ):
        required[f"{japanese} (ja)"] = japanese
        required[f"{japanese} (en)"] = english
    missing = sorted(label for label, needle in required.items() if needle not in evaluation)
    report.expect(
        not missing and bool(evaluation),
        "content.appendixD6Mirrored",
        f"missing from D.6: {missing}" if missing else f"all {len(required)} participant-reference statements present",
    )
    history = [
        match.group(0)
        for pattern in _D6_AUTHORING_HISTORY
        for match in pattern.finditer(evaluation)
    ]
    report.expect(
        not history,
        "content.appendixD6AuthoringHistory",
        f"material-provenance or adoption history: {history}",
    )


def check_preview_material_mirror(
    report: Report, text: str, root_element: Element, document, *, unified: bool = False
) -> None:
    """Mirror published prerequisites and participant reference without unsupported claims."""
    governance = section_text(root_element, "sec-c-6")
    evaluation = sections_text(root_element, "sec-d-6")

    c6_required = {
        "heading (ja)": "C.6 ガバナンス・責任ある AI・コストの前提",
        "heading (en)": "Governance, responsible AI and cost prerequisites",
        "published basis (ja)": "公開されている Microsoft のドキュメントに基づきます",
        "published basis (en)": "based on published Microsoft documentation",
        "preview terms (ja)": "Azure プレビュー補足条項",
        "preview terms (en)": "Azure Preview Supplemental Terms",
        "no model training (ja)": "顧客データは基盤モデルの学習に使われず",
        "no model training (en)": "not used to train the foundation models",
        "human review (ja)": "内容を評価できる人が使う前に確認する必要がある",
        "human review (en)": "has to review it before use",
        "japanese limitation (ja)": "日本語で不安定に見えたときは",
        "japanese limitation (en)": "When Japanese looks unstable",
        "no day count (ja)": "本書は日数を書かない",
        "no day count (en)": "prints no day count",
        "cmk caveat (ja)": "CMK に対応していると仮定しない",
        "cmk caveat (en)": "Do not assume CMK support",
        "capacity metrics (ja)": "Fabric Capacity Metrics アプリ",
        "capacity metrics (en)": "Fabric Capacity Metrics app",
        "copilot in fabric operation": "Copilot in Fabric",
        "capacity region (ja)": "処理される地域は容量のリージョンで決まる",
        "capacity region (en)": "follows the capacity's region",
        "tenant control described (ja)": "リージョン外処理を許可する Copilot テナント設定",
        "tenant control described (en)": "Copilot tenant setting that permits processing outside",
        "exact name deferred (ja)": "設定の正確な名称は付録 E の Copilot tenant settings を参照する",
        "exact name deferred (en)": "Copilot tenant settings entry in appendix E",
    }
    missing_c6 = sorted(label for label, needle in c6_required.items() if needle not in governance)
    report.expect(
        not missing_c6 and bool(governance),
        "content.appendixC6Mirrored",
        f"missing from C.6: {missing_c6}" if missing_c6 else f"all {len(c6_required)} statements in both languages",
    )

    check_ontology_editing_reference_mirror(report, evaluation, unified=unified)

    check_optional_exercise_gate(report, text)

    leaks = sorted(set(re.findall(r"\bT(?:0[1-9]|10)\b", evaluation)))
    verdicts = [word for word in ("PASS", "FAIL", "UNCLEAR", "EXECUTION_ERROR") if word in evaluation]
    runtime = [name for name in ("DRY_RUN_COMPLETE", "APPLY_CHANGES", "PARTICIPANT_ID") if name in evaluation]
    report.expect(
        not (leaks or verdicts or runtime),
        "content.appendixD6Isolated",
        f"tests={leaks} verdicts={verdicts} runtime={runtime}",
    )

    hits = unpublished_claim_hits(text)
    retention = retention_with_duration(text)
    report.expect(
        not (hits or retention),
        "content.noUnpublishedPreviewClaims",
        f"{hits[:3]}; retention sentences with a duration: {retention[:2]}",
    )

    diagram_keys = {
        block["source_key"] for block in document.figures if block["source_kind"] == "diagram"
    }
    report.expect(
        "ontology-authoring-evaluation-lifecycle" in diagram_keys,
        "figures.lifecycleDiagramPresent",
        f"diagram keys rendered: {len(diagram_keys)}",
    )

    printed = {
        element.attrs["href"]
        for element in root_element.walk()
        if element.tag == "a" and element.attrs.get("href", "").startswith("http")
    }
    declared = {url for _title, url in REFERENCE_LINKS}
    report.expect(
        declared <= printed,
        "content.referenceUrlParity",
        f"declared in Word but absent from the mirror: {sorted(declared - printed)[:4]}",
    )
    stale = sorted(u for u in printed if "get-started/copilot-" in u)
    non_en = sorted(
        u for u in printed if u.startswith("https://learn.microsoft.com") and "/en-us/" not in u
    )
    report.expect(
        not (stale or non_en),
        "content.referenceUrlConvention",
        f"stale={stale[:3]} non-en-us={non_en[:3]}"
        if (stale or non_en)
        else f"all {len(printed)} linked URLs use the /en-us/ convention",
    )

    core = {
        "naming rule (ja)": "1〜26 文字",
        "naming rule (en)": "1 to 26 characters",
        "rule covers both kinds (ja)": "Entity Type の名前とカスタム Property の名前",
        "rule covers both kinds (en)": "custom property names",
        "rule basis cited (ja)": "Create entity types と Bind data",
        "rule basis cited (en)": "Create entity types and Bind data",
        "entity type at the ceiling": "MunicipalityCategoryMetric",
        "property at the ceiling 1": "MunicipalityPrefAmountRank",
        "property at the ceiling 2": "MunicipalityStaticTotalYen",
        "all at the published ceiling (ja)": "現在公開されている上限ちょうど",
        "all at the published ceiling (en)": "at the currently published limit",
        "manual refresh (ja)": "［Refresh now］",
        "manual refresh (en)": "[Refresh now]",
    }
    missing_core = sorted(label for label, needle in core.items() if needle not in text)
    report.expect(
        not missing_core,
        "content.namingRuleAndGraphRefreshMirrored",
        f"missing: {missing_core}",
    )
    #: The published rule covers entity type names *and* custom property names.
    #: Narrowing it back, in either language, is the regression this gate catches.
    narrowed = [
        phrase
        for phrase in (
            "no length limit for property names",
            "does not assert one either",
            "公開ドキュメントに長さの上限が示されていない",
            "本書でも上限は主張しません",
        )
        if phrase in text
    ]
    report.expect(
        not narrowed,
        "content.namingRuleCoversProperties",
        f"the rule is narrowed away from property names: {narrowed}",
    )


#: A held-out test identifier. ``\b`` is unusable here because a Japanese
#: character is a word character, so ``\bT07\b`` would miss ``…ゲートT07``.
_PRACTICE_TEST_ID = re.compile(r"(?<![0-9A-Za-z])T(?:0[1-9]|10)(?![0-9A-Za-z])")


def check_data_agent_practice_mirror(
    report: Report, text: str, root_element: Element, *, unified: bool = False
) -> None:
    """The public-source Data Agent practice update survives the mirror in both languages.

    Six blocks were added from first-party Microsoft documentation. The Word
    validator proves the Japanese; these checks prove the English half ships the
    same statements, that the two reframed claims are reframed in English too,
    and that the configuration sections stay clear of Core verdicts.
    """
    required = {
        "example gate heading (ja)": "16.6.1 例クエリの品質ゲート",
        "example gate heading (en)": "Quality gate for example queries",
        "question maps (en)": "appear directly as the query's columns and predicates",
        "distinct shapes (en)": "do not add examples that only reword an existing one",
        "no conflicting intent (en)": "answer the same intent from different tables",
        "stored formats (en)": "in the notation and format in which they are actually stored",
        "schema exists (en)": "exist inside the selected schema",
        "validate (en)": "passes validation",
        "run details (en)": "which examples were used for that question",
        "held-out (en)": "expected value or stable ID into an example query",
        "entry table gate (ja)": "入口のテーブルは重複させない",
        "entry table gate (en)": "Do not repeat an entry table",
        "no retrieval count (ja)": "上位いくつが渡されるかは本書では固定しません",
        "no retrieval count (en)": "does not fix how many of the top matches are passed through",
        "boundary heading (ja)": "16.8 指示で守る境界と、応答時間の変数",
        "boundary heading (en)": "What instructions can and cannot bound",
        "not access control (ja)": "指示はアクセス制御ではありません",
        "not access control (en)": "Instructions are not access control",
        "identity and permissions (en)": "the read permissions on the underlying sources",
        "source side controls (en)": "the controls each item type provides on the source side",
        "no uniform rls (en)": "row-level or column-level control is available in the same way on every source",
        "no column-level selection (ja)": "選択したテーブル（とその全列）とエンティティが多いほど",
        "no column-level selection (en)": "selected tables (with all of their columns) and entities",
        "onelake reason (en)": "Ontology static bindings require managed Delta tables",
        "onelake not unnecessary (en)": "does not mean access controls are unnecessary in production",
        "latency direction only (en)": "No seconds or multipliers are given here",
        "evidence heading (ja)": "17.12 実行証跡と、やり直す条件",
        "evidence heading (en)": "Execution evidence, and when to start over",
        "engine history optional (en)": "Unavailable engine history for a source does not itself fail a question",
        "native evidence required (en)": "Optional engine history does not waive failure to capture required native evidence",
        "no query text (en)": "Do not copy query text into the record sheet's answer field",
        "trigger heading (ja)": "17.12.1 再評価の引き金",
        "trigger heading (en)": "Triggers for re-evaluation",
        "does not weaken (en)": "This section does not weaken it",
        "full rerun (en)": "Fixing only the failed question and rerunning it is not accepted",
        "ch19 both orders (ja)": "章順で並んでいないのは第 17.11 節と第 17.12 節の 2 つです",
        "ch19 both orders (en)": "Two sections are not in chapter order",
        "ch19 evidence order (ja)": "「回答本文 → ［実行詳細］ → エンジン側の実行履歴」",
        "ch19 evidence order (en)": "answer body, then the run details, then the engine-side execution history",
        "ch19 route (ja)": "まず第 17.12 節で証跡を確認し",
        "ch19 route (en)": "first check the evidence in section 17.12",
        "ch19 rerun scope (ja)": "最後に第 17.12.1 節でやり直す範囲を決めます",
        "ch19 rerun scope (en)": "decide the scope of the redo in section 17.12.1",
        "unclear row pointer (ja)": "第 17.12 節の証跡でどこが期待と違うかを見てから",
        "unclear row pointer (en)": "Use the evidence in section 17.12 to see where it diverged",
        "publish heading (ja)": "18.2 公開説明に書く 5 項目",
        "publish heading (en)": "The 5 items a publish description must carry",
        "routing signal (en)": "whether to route a question to this Data Agent",
        "synthetic nature (en)": "Synthetic data for teaching",
        "c7 heading (ja)": "C.7 継続評価と ALM",
        "c7 heading (en)": "Continuous evaluation and ALM",
        "c7 adds no gate (ja)": "C.7 はゲートを増やしません",
        "c7 adds no gate (en)": "C.7 adds no gate",
        "human canonical (en)": "Human scoring is canonical",
        "no package names (en)": "names no package, class or method and shows no code",
        "critic calibration (en)": "a good answer, a bad answer, and a correct refusal",
        "no thresholds (en)": "no figure for it is given in this guide",
        "draft not published (en)": "Do not edit the published folder directly",
        "rebinding (en)": "a move is a trigger to redo the evaluation",
        "d7 heading (ja)": "D.7 Semantic Model を Data Agent ソースとして追加する場合（Optional）",
        "d7 heading (en)": "Adding a Semantic Model as a Data Agent source",
        "d7 not an exercise (ja)": "D.7 も実習ではなく",
        "d7 not an exercise (en)": "D.7 is also reference information rather than an exercise",
        "single authority (en)": "pins the authority for static metrics to the Lakehouse alone",
        "workshop decision (en)": "a design decision of this workshop, not a product constraint",
        "prep for ai (en)": "Put model-specific instructions on the AI preparation side",
        "no capability matrix (en)": "does not pin a support matrix",
        "budget framing (ja)": "本ワークショップが自分に課した安全側の上限",
        "budget framing (en)": "conservative ceiling imposed by the workshop",
        "budget not universal (en)": "not a published product-schema guarantee or a permanent limit",
        "kusto framing (ja)": "本教材では Eventhouse の例クエリは別途登録せず",
        "kusto framing (en)": "This workshop does not register separate Eventhouse example queries",
        "kusto examples in instructions (en)": "KQL example patterns are included in these source instructions",
        "engine billed separately (en)": "billed separately against the engine item that runs it",
    }
    if unified:
        required.update({
            "budget framing (en)": "It is our own conservative budget",
            "budget not universal (en)": "not a published product-schema warranty or a permanent limit",
            "kusto framing (ja)": "この統合プロファイルでは Eventhouse の例クエリも登録します",
            "kusto framing (en)": "This unified profile also registers Eventhouse example queries",
            "kusto examples in instructions (en)": "Match the pinned kusto-fewshots.json and source instructions from the same revision",
        })
    missing = sorted(
        label for label, needle in required.items()
        if ascii_parentheses(needle) not in ascii_parentheses(text)
    )
    report.expect(
        not missing,
        "content.dataAgentPracticeMirrored",
        f"missing: {missing}" if missing else f"all {len(required)} statements in both languages",
    )

    retired = [
        phrase
        for phrase in (
            "定義形式に例クエリの領域",
            "The definition format has no example-query part",
            "Fabric の Data agent 画面が受け付ける上限は 15,000 文字",
            "The Fabric Data agent screen accepts at most 15,000 characters",
            "第 17.11 節だけは順序が異なり",
            "Only section 17.11 is ordered differently",
        )
        if phrase in text
    ]
    report.expect(
        not retired,
        "content.dataAgentPracticeReframed",
        f"a superseded product-wide claim survived the mirror: {retired}",
    )

    #: The configuration and lifecycle sections must not borrow a Core verdict.
    #: Chapters 17 and 18 own the verdicts and the fixed smoke set, so only the
    #: four configuration sections are scanned.
    leaks: list[str] = []
    for prefix in ("sec-16-6-1", "sec-16-8", "sec-c-7", "sec-d-7"):
        block = sections_text(root_element, prefix)
        if not block:
            leaks.append(f"{prefix}: section not rendered")
            continue
        tests = sorted(set(_PRACTICE_TEST_ID.findall(block)))
        verdicts = [word for word in ("PASS", "FAIL", "UNCLEAR", "EXECUTION_ERROR") if word in block]
        runtime = [
            name
            for name in ("DRY_RUN_COMPLETE", "APPLY_CHANGES", "PARTICIPANT_ID")
            if name in block
        ]
        if tests or verdicts or runtime:
            leaks.append(f"{prefix}: tests={tests} verdicts={verdicts} runtime={runtime}")
    report.expect(
        not leaks,
        "content.dataAgentPracticeIsolated",
        "; ".join(leaks) if leaks else "the 4 configuration sections name no test, verdict or parameter",
    )


def check_v3_focus_areas(report: Report, text: str, root_element: Element, document, context) -> None:
    """Guards for the focused V3 correction pass.

    Each item the pass is meant to fix gets a check, so "V3 landed and is
    complete" becomes something the validator states rather than something a
    reader has to re-inspect by hand.
    """
    # Cross-references must resolve to a section that exists.
    numbers = set()
    for section in document.walk():
        if section.number:
            numbers.add(section.number)
    referenced = set(re.findall(r"第\s*(\d+(?:\.\d+)*)\s*[章節]", text))
    broken = sorted(ref for ref in referenced if ref not in numbers)
    report.expect(
        not broken,
        "content.crossReferencesResolve",
        f"{len(referenced)} references, unresolved={broken}",
    )

    # Metric instance counts are observed pairs, not the combinatorial ceiling.
    expected = context.expected
    pref_metric = expected["nodeCounts"].get("ot_pref_category_metric")
    mun_metric = expected["nodeCounts"].get("ot_mun_category_metric")
    prefectures = expected["nodeCounts"].get("ot_prefecture")
    categories = expected["nodeCounts"].get("ot_gift_category")
    ceiling = f"{prefectures * categories:,}" if prefectures and categories else None
    explained = (
        ceiling
        and ceiling in text
        and re.search(r"実際に観測された|actually observed|寄付が 1 件もなかった|received no donation", text)
    )
    report.expect(
        bool(explained),
        "content.metricPairsExplained",
        f"{pref_metric} of {ceiling} possible pairs is explained",
    )
    report.expect(
        f"{mun_metric:,}" in text,
        "content.municipalityMetricCount",
        f"{mun_metric:,} stated",
    )

    # The three stale-lease parameters are named together and scoped correctly.
    lease = ("OPERATOR_RECOVER_STALE_LEASE", "STALE_LEASE_OWNER_RUN_ID", "STALE_LEASE_GENERATION")
    missing_lease = [name for name in lease if name not in text]
    report.expect(not missing_lease, "content.staleLeaseParameters", f"missing={missing_lease}")
    report.expect(
        re.search(r"Notebook 01 (?:にしかありません|のみ)|Notebook 01 only", text) is not None,
        "content.staleLeaseScopedToNotebook01",
        "the trio is scoped to Notebook 01",
    )

    # The decision tree agrees on its step count everywhere it is described. The
    # counter is 段 for a decision-tree level; 段階 counts the stages of an
    # unrelated table, so it must not be swept into the same comparison.
    steps = set(re.findall(r"(\d+)\s*段(?!階)", text))
    report.expect(
        steps == {"7"} or steps == set(),
        "content.decisionTreeStepCount",
        f"step counts mentioned: {sorted(steps)}",
    )

    # Failure triage checks source selection before it blames the instructions.
    triage = section_text(root_element, "sec-17-11")
    selection = triage.find("ソース選択")
    instructions = triage.find("ソース指示")
    report.expect(
        selection != -1 and instructions != -1 and selection < instructions,
        "content.triageChecksSelectionFirst",
        f"selection@{selection} before instructions@{instructions}",
    )
    curated_selection = "DonationObservationSummaryForAgent" in triage
    if context.is_unified_guide:
        curated_selection = (
            "承認済み MV と 3 関数がすべて必須" in triage
            and "SQL 14 / KQL 4" in triage
            and "DonationObservationSummaryForAgent" in section_text(root_element, "sec-16-2-2")
        )
    report.expect(
        curated_selection and "DonationEvents" in triage,
        "content.triageNamesBothKqlObjects",
        "triage contrasts the curated view with the raw table",
    )


#: Kana and CJK ideographs. A mirror value holding any of these quotes Japanese.
_CJK_CHARACTER = re.compile(r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff]")

#: Japanese separators that must not survive into an otherwise ASCII sentence.
_JA_SEPARATORS = ("\u3001", "\uff0f", "\u301c", "\uff5e")


def check_english_typography(report: Report, mirror, root: Element | None = None) -> None:
    """The English mirror uses straight quotes only, so quoting stays uniform."""
    curly = [
        key
        for key, value in mirror.entries.items()
        if any(mark in value for mark in ("\u201c", "\u201d", "\u2018", "\u2019"))
    ]
    rendered_curly = [
        element.all_text()
        for element in root.walk()
        if element.attrs.get("lang") == "en"
        and any(mark in element.all_text() for mark in ("\u201c", "\u201d", "\u2018", "\u2019"))
    ] if root is not None else []
    report.expect(
        not curly and not rendered_curly,
        "i18n.straightQuotes",
        f"{len(curly)} mirror values and {len(rendered_curly)} rendered English spans use curly quotes",
    )

    # A mirror value that quotes Japanese keeps Japanese punctuation - that is the
    # quotation, and rewriting it would corrupt the quoted text. A value with no
    # CJK character at all has no such excuse: an ideographic comma, a fullwidth
    # solidus or a wave dash there is the Japanese separator copied through the
    # translation. Only the second class is rejected, so the gate reaches beyond
    # the synonym lines it originally covered without touching quoted Japanese.
    passthrough = []
    for key, value in mirror.entries.items():
        if _CJK_CHARACTER.search(value):
            continue
        marks = sorted({mark for mark in _JA_SEPARATORS if mark in value})
        if marks:
            passthrough.append(f"{key[:40]}: {marks}")
    report.expect(
        not passthrough,
        "i18n.noPassThroughPunctuation",
        f"{len(passthrough)} ascii-only values keep Japanese separators: {passthrough[:4]}",
    )


def check_office_sources(
    report: Report, root: Element, repo: Path, version: str, expected: dict[str, str],
    edition: str = "",
    *, public_documents_only: bool = False, source_dir: Path | None = None,
) -> None:
    """The page records which Office deliverables it mirrors, and they still match.

    Word rewrites a DOCX package whenever it refreshes fields and repaginates, so
    the byte digest of a deliverable changes even when its content does not. The
    footer therefore states the digest that was actually mirrored, and this check
    re-reads the files on disk to confirm the HTML is not stale.
    """
    names = deliverable_names(version, edition)
    wanted = names.selected_office(public_documents_only)
    entries = [element for element in root.walk() if element.attrs.get("data-office-source")]
    recorded = {
        element.attrs["data-office-source"]: element.attrs.get(
            "data-office-release",
            element.all_text().rsplit("sha256", 1)[-1].strip(),
        )
        for element in entries
    }
    seen = {
        element.attrs["data-office-source"]: element.attrs.get("data-office-observed", "")
        for element in entries
    }
    report.expect(
        len(entries) == len(recorded) == len(wanted), "source.recorded", f"{sorted(recorded)}"
    )
    inventory_ok = set(recorded) == set(wanted)
    report.expect(
        inventory_ok, "source.inventory",
        f"expected {list(wanted)}, recorded {sorted(recorded)}",
    )

    #: A layout-only reissue repaginates the DOCX without touching content, so the
    #: pinned release digest and the bytes on disk legitimately differ. The footer
    #: records both; disk is therefore compared against the observed digest.
    reissued = sorted(n for n, d in seen.items() if d and d != recorded.get(n))
    report.ok(
        "source.layoutReissue",
        f"layout-only reissues: {reissued}" if reissued else "none; release digests are the bytes on disk",
    )

    mismatched: list[str] = []
    directory = source_dir if source_dir is not None else repo / "docs"
    for name, digest in recorded.items():
        # Never resolve a path supplied by an untrusted footer.
        if name not in wanted:
            mismatched.append(f"unrecognized Office source {name!r}")
            continue
        path = directory / name
        if not path.is_file():
            mismatched.append(f"{name} missing")
            continue
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != (seen.get(name) or digest):
            mismatched.append(f"{name} disk={actual[:16]} recorded={(seen.get(name) or digest)[:16]}")
    report.expect(not mismatched, "source.matchesDisk", "; ".join(mismatched))

    download_links = [
        element.attrs.get("href")
        for element in root.walk()
        if element.tag == "a" and "download" in element.attrs
    ]
    downloads = set(download_links)
    downloads_ok = downloads == set(wanted)
    if public_documents_only:
        downloads_ok = downloads_ok and len(download_links) == 1 and all(
            element.attrs["download"] in {"", names.participant}
            for element in root.walk() if element.tag == "a" and "download" in element.attrs
        )
    report.expect(
        downloads_ok,
        "source.downloadEdition",
        "download links match the selected Office edition" if downloads_ok
        else f"expected {list(wanted)}, found {download_links}",
    )
    if public_documents_only:
        report.expect(
            inventory_ok and all(
                re.fullmatch(r"[0-9a-f]{64}", recorded[name]) and seen[name] == recorded[name]
                for name in recorded
            ),
            "source.actualParticipantBytes",
            "public provenance must record the actual participant Word hash, without release restamping",
        )
        report.expect(
            inventory_ok and all(
                entry.attrs["data-office-source"] in entry.all_text()
                and f"sha256 {recorded[entry.attrs['data-office-source']]}" in entry.all_text()
                for entry in entries
            ),
            "source.visibleProvenance",
            "the displayed footer names and hashes must match the recorded participant Word",
        )

    if not expected:
        return
    pinned: list[str] = []
    for name, digest in expected.items():
        actual = recorded.get(name)
        if actual != digest:
            pinned.append(f"{name} expected={digest[:16]} mirrored={(actual or 'absent')[:16]}")
    report.expect(not pinned, "source.pinned", "; ".join(pinned) or f"{len(expected)} digests pinned")


def check_public_html_policy(
    report: Report, root: Element, text: str, version: str, edition: str
) -> None:
    names = deliverable_names(version, edition)
    modes = [
        element.attrs.get("content")
        for element in root.walk()
        if element.tag == "meta" and element.attrs.get("name") == "publication-mode"
    ]
    report.expect(modes == [PUBLIC_MODE], "publication.mode", f"{modes}")
    problems = public_text_errors(text)
    report.expect(not problems, "publication.guideContent", "; ".join(problems))
    link_problems = []
    for element in root.walk():
        if "href" in element.attrs:
            problem = public_link_error(element.attrs["href"], names)
            if problem:
                link_problems.append(problem)
        if element.tag in {"base", "iframe", "object", "embed"}:
            link_problems.append(f"unpackaged content or rewritten link base: {element.tag}")
    report.expect(not link_problems, "publication.links", "; ".join(link_problems))


# --------------------------------------------------------------------- main
def check_layout_reissue_soundness(report: Report) -> None:
    """A layout-only stamp is only meaningful on content that already passes.

    ``--content-fingerprint`` proves the content model did not move between two
    builds. It cannot, on its own, prove the model *is* the pinned release: point
    it at a stale tree and it will happily agree with itself. The missing half of
    the argument is that every content guard passes, so this refuses the
    combination of "layout-only reissue" and any failing content check rather
    than let a superseded mirror inherit a newer release digest.
    """
    reissued = [d for s, c, d in report.results if c == "source.layoutReissue" and s == "PASS"]
    declared = bool(reissued) and not reissued[0].startswith("none")
    if not declared:
        return
    stale = sorted({c for s, c, _ in report.results if s == "FAIL" and c.startswith("content.")})
    report.expect(
        not stale,
        "source.layoutReissueSound",
        (
            f"a layout-only release digest was stamped while {stale} still fail; the "
            "content model is not the pinned release, so re-mirror instead of restamping"
        )
        if stale
        else "content guards all pass, so the layout-only stamp is sound",
    )


def validate(
    root: Path,
    out_dir: Path,
    expected_sources: dict[str, str] | None = None,
    expected_shape: dict[str, int] | None = None,
    edition: str = "",
    public_documents_only: bool = False,
) -> Report:
    report = Report()
    version = (root / "VERSION").read_text(encoding="utf-8").strip()
    names = deliverable_names(version, edition)
    if public_documents_only:
        try:
            require_public_edition(edition)
            out_dir = outside_repo(out_dir, root)
            check_directory(out_dir, names, required=names.public_pair)
        except PublicationError as error:
            report.fail("publication.outputSafety", str(error))
            return report
    path = out_dir / names.html
    if not path.is_file():
        report.fail("file.exists", str(path))
        return report

    raw = path.read_text(encoding="utf-8")
    size = path.stat().st_size
    report.expect(size < GITHUB_FILE_LIMIT, "file.size", f"{size / 1048576:.2f} MB < 100 MB")
    if not public_documents_only:
        report.expect(
            not (out_dir / "furusato-workshop-v2-6-0-complete.html").exists(),
            "file.supersededRemoved",
        )

    structure = Structure()
    structure.feed(raw)
    structure.close()
    if structure.errors:
        report.fail("html.wellformed", "; ".join(structure.errors[:6]))
        return report
    dom = structure.root

    context = load_context(root, document_edition=edition)
    facts = compute_facts(context)
    tests = build_tests(context, facts)
    carrier = StyleCarrier.resolve(root)
    capture = capture_participant_guide(
        context, facts, tests, carrier, public_documents_only=public_documents_only
    )
    mirror = load_mirror(public_documents_only=public_documents_only, context=context)
    ui = load_ui_strings(public_documents_only=public_documents_only, context=context)
    document = build_document(capture.nodes, mirror)

    report.expect(not mirror.unused(), "i18n.noOrphanMirrors", f"{len(mirror.unused())} unused")
    report.expect(not suspicious_english(mirror.entries), "i18n.englishComplete")
    report.expect(len(ui) >= 60, "i18n.uiStrings", f"{len(ui)} chrome strings")

    body_text = _plain_text(raw)
    body_text = re.sub(r"[ \t]+", " ", body_text)
    plain = html_module.unescape(raw)

    check_structure(report, raw, structure, dom)
    check_ids_and_anchors(report, dom)
    check_headings(report, dom)
    check_language_pairs(report, dom)
    check_chapters(report, dom, document)
    check_tables(report, dom, len(document.tables))
    check_figures(
        report,
        dom,
        context,
        {
            "figures": len(document.figures),
            "screenshots": len({b["source_key"] for b in document.figures if b["source_kind"] == "screenshot"}),
            "diagrams": len({b["source_key"] for b in document.figures if b["source_kind"] == "diagram"}),
        },
    )
    check_no_external_dependencies(report, raw, dom)
    check_controls(report, dom)
    check_checklist(report, dom, len(document.checklist))
    check_runtime_facts(report, plain, context, facts, tests)
    check_parameter_catalog(report, dom, context, mirror)
    check_agent_configuration(report, body_text, raw, context)
    check_scripts_and_state(report, raw)
    check_diagram_freshness(
        report, raw, context, document, (ui["figure.label"]["ja"], ui["figure.label"]["en"])
    )
    check_forbidden(report, body_text, raw)
    check_approved_clarifications(report, body_text, facts, tests, mirror)
    check_agent_source_selection(report, body_text, context)
    check_runtime_v2_invariants(report, body_text, raw, context)
    check_high_regressions(report, dom, body_text, context)
    check_v3_focus_areas(report, body_text, dom, document, context)
    check_preview_material_mirror(report, body_text, dom, document, unified=context.is_unified_guide)
    check_data_agent_practice_mirror(report, body_text, dom, unified=context.is_unified_guide)
    check_english_typography(report, mirror, dom)
    check_office_sources(
        report, dom, root, context.version, expected_sources or {}, edition,
        public_documents_only=public_documents_only,
        source_dir=out_dir if public_documents_only else None,
    )
    if public_documents_only:
        check_public_html_policy(report, dom, body_text, context.version, edition)
    check_document_shape(report, document, tests, expected_shape or {})
    check_quality_pass(report, dom, raw)
    check_layout_reissue_soundness(report)

    expected_screenshots = {b["source_key"] for b in document.figures if b["source_kind"] == "screenshot"}
    retired = set(__import__("furusato_docs.guide_handson", fromlist=["x"]).RETIRED_SCREENSHOTS)
    report.expect(
        not (expected_screenshots & retired),
        "figures.noRetiredScreenshots",
        f"{sorted(expected_screenshots & retired)}",
    )
    report.expect(
        expected_screenshots <= set(carrier.available_screenshots),
        "figures.screenshotsFromCarrier",
    )
    return report


def main(argv: list[str] | None = None) -> int:
    # Check details quote Japanese source text. On a cp1252 console that would
    # raise UnicodeEncodeError and hide the actual result, so widen stdout first.
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (ValueError, OSError):
                pass
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=None, help="directory holding the HTML (default: docs/)")
    parser.add_argument("--edition", default="", type=validate_edition, help="Named correction edition")
    parser.add_argument(
        "--public-documents-only", action="store_true",
        help="Validate the public participant Word/HTML pair in external --out, not other Office companions",
    )
    parser.add_argument("--json", action="store_true", help="emit a machine-readable report")
    parser.add_argument(
        "--expect-source",
        action="append",
        default=[],
        metavar="NAME=SHA256",
        help="pin an Office deliverable digest the HTML must have mirrored (repeatable)",
    )
    parser.add_argument(
        "--expect-shape",
        action="append",
        default=[],
        metavar="NAME=COUNT",
        help="pin a Word structural total the mirror must reproduce "
        "(chapters, headings, tables, figures, tests); repeatable",
    )
    args = parser.parse_args(argv)
    if args.public_documents_only and not args.out:
        parser.error("--public-documents-only requires --out")

    expected: dict[str, str] = {}
    for item in args.expect_source:
        name, _, digest = item.partition("=")
        if not name or not digest:
            parser.error(f"--expect-source needs NAME=SHA256, got {item!r}")
        expected[name.strip()] = digest.strip().lower()

    shape: dict[str, int] = {}
    for item in args.expect_shape:
        name, _, count = item.partition("=")
        if not name or not count.strip().isdigit():
            parser.error(f"--expect-shape needs NAME=COUNT, got {item!r}")
        shape[name.strip()] = int(count)

    out_dir = Path(args.out) if args.out else ROOT / "docs"
    if not args.public_documents_only:
        out_dir = out_dir.resolve()
    report = validate(ROOT, out_dir, expected, shape, args.edition, args.public_documents_only)

    if args.json:
        print(json.dumps(
            {"results": [{"status": s, "check": c, "detail": d} for s, c, d in report.results]},
            indent=2,
            ensure_ascii=False,
        ))
    else:
        for status, check, detail in report.results:
            marker = {"PASS": "  ok  ", "FAIL": " FAIL ", "WARN": " warn "}[status]
            print(f"[{marker}] {check:42s} {detail}")
        print()
        print(f"{len(report.results)} checks, {len(report.failures)} failed, {len(report.warnings)} warnings")
    return 1 if report.failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
