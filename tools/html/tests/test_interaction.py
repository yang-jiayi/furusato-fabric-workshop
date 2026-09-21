"""Automated interaction tests for the single-file bilingual guide.

Drives the built HTML in headless Chromium and asserts the behaviour a
participant depends on: it loads without console errors, the language toggle
switches and persists, search finds and jumps, the checklist persists and
resets, copy reports success, the lightbox closes from the keyboard, the table
of contents navigates, nothing overflows horizontally at desktop or phone
widths, and print media keeps the document readable.

    python tools/html/tests/test_interaction.py
    python tools/html/tests/test_interaction.py --artifacts <dir>   # screenshots

Artifacts are written only where you point them; nothing is stored in the
repository.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from pathlib import Path

from playwright.sync_api import ConsoleMessage, Error, sync_playwright

ROOT = Path(__file__).resolve().parents[3]
TARGET = ROOT / "docs" / "furusato-workshop-v2-7-0-complete.html"

DESKTOP = {"width": 1440, "height": 900}
LAPTOP = {"width": 1024, "height": 800}
TABLET = {"width": 768, "height": 1024}
PHONE = {"width": 390, "height": 844}


class Results:
    def __init__(self) -> None:
        self.rows: list[tuple[str, bool, str]] = []

    def check(self, name: str, condition: bool, detail: str = "") -> bool:
        self.rows.append((name, bool(condition), detail))
        return bool(condition)

    @property
    def failed(self) -> list[tuple[str, bool, str]]:
        return [row for row in self.rows if not row[1]]


def _settle_scroll(page, timeout_ms: int = 8000) -> None:
    """Wait until smooth scrolling has stopped moving the page.

    A fixed timeout cannot cover this document: one TOC jump travels tens of
    thousands of pixels, and how long the browser animates that is a browser
    detail, not a property of the guide. Polling the offset until it stops
    keeps the assertion strict while staying independent of the engine.
    """
    page.wait_for_function(
        """() => {
            const now = Math.round(window.scrollY);
            if (window.__lastScrollY === now) { return true; }
            window.__lastScrollY = now;
            return false;
        }""",
        timeout=timeout_ms,
        polling=120,
    )
    page.evaluate("() => { delete window.__lastScrollY; }")


#: A4 portrait at 96 dpi. The parameter tables only overprint once the page is
#: this narrow, so the print geometry is measured at the printed width rather
#: than at whatever viewport the harness happened to open with.
A4_PRINT_WIDTH_PX = 794


def run(target: Path, artifacts: Path | None) -> Results:
    results = Results()
    console: list[str] = []
    page_errors: list[str] = []
    requests: list[str] = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        context = browser.new_context(viewport=DESKTOP, device_scale_factor=1)
        page = context.new_page()

        def on_console(message: ConsoleMessage) -> None:
            if message.type in ("error", "warning"):
                console.append(f"{message.type}: {message.text}")

        page.on("console", on_console)
        page.on("pageerror", lambda error: page_errors.append(str(error)))
        page.on("request", lambda request: requests.append(request.url))

        url = target.as_uri()
        page.goto(url, wait_until="load")
        page.wait_for_selector("html[data-ready='true']", timeout=15000)

        #: The guide must render with no network at all. Static analysis already
        #: bans external URLs; this is the end-to-end proof, because a stylesheet
        #: @import or a JS fetch would show up here even though it is not a link.
        subresources = [r for r in requests if r != url]
        results.check(
            "offline.noSubresourceRequests",
            not subresources,
            f"{len(subresources)} request(s): {subresources[:3]}",
        )

        results.check("load.noPageErrors", not page_errors, "; ".join(page_errors[:3]))
        results.check("load.noConsoleErrors", not console, "; ".join(console[:3]))
        results.check(
            "load.title",
            "Fabric IQ" in page.title(),
            page.title(),
        )

        # ---------------------------------------------------------- language
        ja_visible = page.locator("h1 [data-l='ja']").first.is_visible()
        en_hidden = not page.locator("h1 [data-l='en']").first.is_visible()
        results.check("lang.defaultJapanese", ja_visible and en_hidden)

        page.click("[data-set-lang='en']")
        page.wait_for_timeout(150)
        results.check(
            "lang.switchToEnglish",
            page.locator("h1 [data-l='en']").first.is_visible()
            and not page.locator("h1 [data-l='ja']").first.is_visible(),
        )
        results.check(
            "lang.htmlLangAttribute",
            page.get_attribute("html", "lang") == "en",
            page.get_attribute("html", "lang") or "",
        )
        results.check(
            "lang.controlsLocalized",
            page.locator("#print-guide span[data-i18n='print.label']").inner_text().strip() == "Print",
            page.locator("#print-guide span[data-i18n='print.label']").inner_text(),
        )

        stored = page.evaluate("() => window.localStorage.getItem('furusato-workshop-v2.7.0')")
        results.check("lang.persisted", bool(stored) and json.loads(stored)["lang"] == "en", str(stored)[:80])

        page.reload(wait_until="load")
        page.wait_for_selector("html[data-ready='true']")
        results.check(
            "lang.persistsAcrossReload",
            page.get_attribute("html", "data-lang") == "en",
            page.get_attribute("html", "data-lang") or "",
        )

        # ------------------------------------------------------------ search
        page.fill("#search-input", "Eventhouse")
        page.wait_for_timeout(250)
        hits = page.locator("#search-results .search__hit")
        results.check("search.findsResults", hits.count() > 0, f"{hits.count()} hits")

        #: Search covers the active language only. Both languages sit in the DOM, so
        #: a term that exists *only* in Japanese prose must find nothing while English
        #: is shown. The term is verified to be Japanese-only first: plenty of Japanese
        #: legitimately appears inside English text (Ontology synonym lists and pasted
        #: UI labels are identical in both languages), and matching those is correct.
        probe = "必ず"
        spans = page.evaluate(
            "t=>({ja:[...document.querySelectorAll('[data-l=\"ja\"]')].filter(e=>e.textContent.includes(t)).length,"
            "en:[...document.querySelectorAll('[data-l=\"en\"]')].filter(e=>e.textContent.includes(t)).length})",
            probe,
        )
        results.check(
            "search.probeIsJapaneseOnly",
            spans["ja"] > 0 and spans["en"] == 0,
            f"{probe!r} appears in {spans['ja']} japanese and {spans['en']} english spans",
        )
        page.fill("#search-input", probe)
        page.wait_for_timeout(300)
        ja_in_en = page.locator("#search-results .search__hit").count()
        page.click("[data-set-lang='ja']")
        page.wait_for_timeout(200)
        page.fill("#search-input", probe)
        page.wait_for_timeout(300)
        ja_in_ja = page.locator("#search-results .search__hit").count()
        results.check(
            "search.activeLanguageOnly",
            ja_in_en == 0 and ja_in_ja > 0,
            f"{probe!r}: {ja_in_en} hits while English, {ja_in_ja} while Japanese",
        )
        page.click("[data-set-lang='en']")
        page.wait_for_timeout(200)
        page.fill("#search-input", "Eventhouse")
        page.wait_for_timeout(250)
        results.check(
            "search.highlightsTerm",
            page.locator("#search-results mark").count() > 0,
        )
        page.focus("#search-input")
        page.keyboard.press("ArrowDown")
        page.wait_for_timeout(80)
        results.check(
            "search.keyboardSelection",
            page.locator("#search-results .search__hit[aria-selected='true']").count() == 1,
        )
        page.keyboard.press("Enter")
        page.wait_for_timeout(400)
        results.check("search.closesOnJump", page.locator("#search-panel").is_hidden())
        results.check("search.jumped", page.evaluate("() => window.scrollY") > 200)

        page.fill("#search-input", "")
        page.wait_for_timeout(120)

        # --------------------------------------------------------- checklist
        first_step = page.locator("[data-step-id]").first
        step_id = first_step.get_attribute("data-step-id")
        first_step.scroll_into_view_if_needed()
        first_step.check()
        page.wait_for_timeout(150)
        state = json.loads(page.evaluate("() => window.localStorage.getItem('furusato-workshop-v2.7.0')"))
        results.check("checklist.persists", step_id in state["steps"], str(state["steps"])[:60])
        results.check("checklist.version", state["version"] == 2 and state["workshop"] == "2.7.0", str(state)[:60])
        results.check(
            "checklist.progressText",
            page.locator("#progress-text").inner_text().startswith("1 / "),
            page.locator("#progress-text").inner_text(),
        )

        page.reload(wait_until="load")
        page.wait_for_selector("html[data-ready='true']")
        results.check(
            "checklist.restoredAfterReload",
            page.locator(f"[data-step-id='{step_id}']").is_checked(),
        )

        page.once("dialog", lambda dialog: dialog.accept())
        page.click("#reset-progress")
        page.wait_for_timeout(200)
        results.check(
            "checklist.reset",
            page.locator("#progress-text").inner_text().startswith("0 / "),
            page.locator("#progress-text").inner_text(),
        )

        # -------------------------------------------------- legacy isolation
        page.evaluate(
            "() => { window.localStorage.clear();"
            " window.localStorage.setItem('fiq-lang','en');"
            " window.localStorage.setItem('fiq-steps', JSON.stringify(['step-6-1','step-9-2'])); }"
        )
        page.reload(wait_until="load")
        page.wait_for_selector("html[data-ready='true']")
        results.check(
            "state.migratesLanguageOnly",
            page.get_attribute("html", "data-lang") == "en"
            and page.locator("#progress-text").inner_text().startswith("0 / "),
            page.locator("#progress-text").inner_text(),
        )
        page.evaluate("() => window.localStorage.clear()")
        page.reload(wait_until="load")
        page.wait_for_selector("html[data-ready='true']")

        # --------------------------------------------------------------- copy
        context.grant_permissions(["clipboard-read", "clipboard-write"])
        copy_button = page.locator(".codeblock__copy").first
        copy_button.scroll_into_view_if_needed()
        copy_button.click()
        page.wait_for_timeout(250)
        results.check(
            "copy.feedback",
            "is-done" in (copy_button.get_attribute("class") or ""),
            copy_button.get_attribute("class") or "",
        )
        results.check(
            "copy.clipboardContent",
            len(page.evaluate("() => navigator.clipboard.readText()")) > 10,
        )
        results.check(
            "copy.liveRegionAnnounced",
            page.locator("#live-status").inner_text().strip() != "",
            page.locator("#live-status").inner_text(),
        )

        # ------------------------------------------------- quality pass gates
        # Expand/collapse used to put data-i18n on the button itself, so applyLang
        # replaced the button's textContent and deleted the inner label. Every
        # click after that threw. Assert state, label, key, aria and console
        # together, after a language switch, which is what exposed it.
        quality_errors: list[str] = []
        page.on("pageerror", lambda error: quality_errors.append(str(error)))
        lang_before_quality = page.get_attribute("html", "data-lang")

        def expand_state() -> dict:
            return page.evaluate(
                """() => {
                    const button = document.getElementById('expand-all');
                    const label = button && button.querySelector('[data-expand-label]');
                    const items = Array.prototype.slice.call(
                        document.querySelectorAll('details.optional-details'));
                    return {
                        hasLabel: !!label,
                        text: label ? label.textContent.trim() : '',
                        key: label ? label.getAttribute('data-i18n') : '',
                        aria: button ? button.getAttribute('aria-expanded') : '',
                        open: items.filter(i => i.open).length,
                        total: items.length
                    };
                }"""
            )

        # Force a known starting state so the assertions do not depend on what
        # earlier checks left behind.
        page.evaluate(
            "document.querySelectorAll('details.optional-details').forEach(d => d.open = false)"
        )
        page.wait_for_timeout(200)
        before = expand_state()
        results.check(
            "details.labelSurvivesLanguageSwitch",
            before["hasLabel"],
            f"inner label present after a language switch: {before['hasLabel']}",
        )
        results.check(
            "details.labelMatchesInitialState",
            before["key"] == "details.expand" and before["aria"] == "false" and before["open"] == 0,
            f"{before['open']}/{before['total']} open, key={before['key']}, aria={before['aria']}",
        )

        page.click("#expand-all")
        page.wait_for_timeout(200)
        opened = expand_state()
        results.check(
            "details.expandAllAgrees",
            opened["open"] == opened["total"]
            and opened["key"] == "details.collapse"
            and opened["aria"] == "true"
            and opened["text"] != "",
            f"{opened['open']}/{opened['total']} open, key={opened['key']}, aria={opened['aria']}",
        )

        page.click("#expand-all")
        page.wait_for_timeout(200)
        closed = expand_state()
        results.check(
            "details.collapseAllAgrees",
            closed["open"] == 0
            and closed["key"] == "details.expand"
            and closed["aria"] == "false",
            f"{closed['open']}/{closed['total']} open, key={closed['key']}, aria={closed['aria']}",
        )
        results.check(
            "details.noExceptionOnToggle", not quality_errors, "; ".join(quality_errors[:2])
        )

        # One disclosure open is not all of them, so the control must still offer
        # "expand all" rather than flipping to "collapse all".
        page.evaluate("document.querySelector('details.optional-details').open = true")
        page.wait_for_timeout(200)
        partial = expand_state()
        results.check(
            "details.labelTracksIndividualToggle",
            partial["key"] == "details.expand"
            and partial["aria"] == "false"
            and 0 < partial["open"] < partial["total"],
            f"{partial['open']}/{partial['total']} open, key={partial['key']}",
        )

        page.click("[data-set-lang='en']")
        page.wait_for_timeout(350)
        diagram_language = page.evaluate(
            """() => {
                const out = [];
                document.querySelectorAll('figure.figure--diagram').forEach(fig => {
                    const shown = Array.prototype.slice.call(fig.querySelectorAll('.figure__art'))
                        .filter(a => a.offsetParent !== null);
                    // Only <text> is drawn. <title>/<desc> stay bilingual on purpose
                    // so assistive technology can announce either language.
                    const drawn = shown.flatMap(a =>
                        Array.prototype.slice.call(a.querySelectorAll('text')).map(t => t.textContent));
                    out.push({
                        visible: shown.length,
                        lang: shown.length ? shown[0].getAttribute('data-l') : '',
                        japanese: /[\\u3040-\\u309f\\u30a0-\\u30ff\\u4e00-\\u9fff]/.test(drawn.join(' '))
                    });
                });
                return out;
            }"""
        )
        results.check(
            "diagrams.oneArtworkVisible",
            bool(diagram_language) and all(i["visible"] == 1 for i in diagram_language),
            f"{[i['visible'] for i in diagram_language]}",
        )
        results.check(
            "diagrams.englishWhenEnglish",
            all(i["lang"] == "en" and not i["japanese"] for i in diagram_language),
            f"{[(i['lang'], i['japanese']) for i in diagram_language]}",
        )

        page.set_viewport_size({"width": 390, "height": 844})
        page.wait_for_timeout(300)
        page.evaluate("window.scrollTo(0, 4000)")
        page.wait_for_timeout(400)
        overlap = page.evaluate(
            """() => {
                const top = document.getElementById('to-top');
                if (!top) { return {ok: false}; }
                const box = top.getBoundingClientRect();
                const hits = [];
                document.querySelectorAll('.table-wrap, .figure__frame, .codeblock__copy').forEach(el => {
                    const r = el.getBoundingClientRect();
                    if (r.bottom < 0 || r.top > window.innerHeight) { return; }
                    if (r.left < box.right && r.right > box.left &&
                        r.top < box.bottom && r.bottom > box.top) { hits.push(el.className); }
                });
                return {
                    ok: true,
                    compact: box.width <= 60,
                    named: !!top.getAttribute('aria-label') && !!top.getAttribute('title'),
                    width: Math.round(box.width),
                    hits: hits
                };
            }"""
        )
        results.check(
            "backToTop.compactOnPhone",
            bool(overlap.get("compact")) and bool(overlap.get("named")),
            f"width={overlap.get('width')}px, localized name and title: {overlap.get('named')}",
        )
        results.check(
            "backToTop.noOverlap",
            not overlap.get("hits"),
            f"overlapping elements: {overlap.get('hits', [])[:3]}",
        )
        page.set_viewport_size(DESKTOP)
        page.wait_for_timeout(250)
        # Hand the page back exactly as it was found, so the checks that follow
        # are not reading state this block happened to leave behind.
        page.evaluate(
            "document.querySelectorAll('details.optional-details').forEach(d => d.open = true)"
        )
        if lang_before_quality:
            page.click(f"[data-set-lang='{lang_before_quality}']")
        page.wait_for_timeout(300)

        # --------------------------------------------------- print integrity
        # A 64-character digest or a long OneLake path is the kind of value a
        # reader retypes to verify something, so a printed copy that clips it is
        # worse than useless. Measured under print emulation in both languages:
        # the cell must render its full text without horizontal overflow.
        page.wait_for_timeout(200)
        print_report = {}
        for language in ("ja", "en"):
            # The header is hidden in print, so switch language on screen first.
            page.emulate_media(media="screen")
            page.wait_for_timeout(200)
            page.click(f"[data-set-lang='{language}']")
            page.wait_for_timeout(300)
            page.emulate_media(media="print")
            page.wait_for_timeout(400)
            print_report[language] = page.evaluate(
                """() => {
                    const digest = /\\b[0-9a-f]{64}\\b/;
                    const longPath = /(Files|Tables)\\/[^\\s]{12,}/;
                    const leaves = Array.prototype.slice.call(document.querySelectorAll('*'))
                        .filter(e => e.children.length === 0 && e.offsetParent !== null);
                    const wanted = leaves.filter(e => digest.test(e.textContent) || longPath.test(e.textContent));
                    const clipped = [];
                    wanted.forEach(c => {
                        if (c.scrollWidth > c.clientWidth + 1) {
                            clipped.push(c.tagName + ':' + c.textContent.trim().slice(0, 34));
                        }
                    });
                    const digests = new Set();
                    wanted.forEach(c => {
                        (c.textContent.match(/\\b[0-9a-f]{64}\\b/g) || []).forEach(d => digests.add(d));
                    });
                    return {cells: wanted.length, clipped: clipped,
                            sample: wanted.slice(0, 4).map(e => e.tagName + ':' + e.textContent.trim().slice(0, 30)),
                            digests: Array.from(digests)};
                }"""
            )
        results.check(
            "print.longValuesNotClipped.ja",
            not print_report["ja"]["clipped"],
            f"{print_report['ja']['cells']} cells checked, clipped={print_report['ja']['clipped'][:2]}",
        )
        results.check(
            "print.longValuesNotClipped.en",
            not print_report["en"]["clipped"],
            f"{print_report['en']['cells']} cells checked, clipped={print_report['en']['clipped'][:2]}",
        )
        results.check(
            "print.digestsPresentInBothLanguages",
            bool(print_report["ja"]["digests"])
            and sorted(print_report["ja"]["digests"]) == sorted(print_report["en"]["digests"]),
            f"{len(print_report['ja']['digests'])} full 64-char digests print in both languages",
        )

        # A fixed table layout cannot widen a column to fit its content, so a cell
        # whose text is wider than its box does not wrap - it paints over the cell
        # beside it. Clipping is invisible to scrollWidth in that case, so the
        # geometry is compared directly: every cell's painted text must stay
        # inside its own column, and no two cells in a row may overlap.
        # A fixed table layout cannot widen a column, so an over-long token does
        # not push the column out - it paints past the cell border and over the
        # column beside it. `scrollWidth` does not report that for inline content,
        # which is how POLL_INTERVAL_SECONDS, bronze/silver/gold/ops/quarantine,
        # Files/furusato/seed and the "Implementation section" header all reached
        # paper overprinting. Every text rect is therefore compared against its
        # own cell's content box and against the next cell's edge, across all
        # eight columns, head and body, in both languages - and at the printed A4
        # width, because the defect only appears once the page is that narrow.
        overlap_report = {}
        page.set_viewport_size({"width": A4_PRINT_WIDTH_PX, "height": 1000})
        page.wait_for_timeout(300)
        for language in ("ja", "en"):
            page.emulate_media(media="screen")
            page.wait_for_timeout(200)
            page.click(f"[data-set-lang='{language}']")
            page.wait_for_timeout(300)
            page.emulate_media(media="print")
            page.wait_for_timeout(500)
            overlap_report[language] = page.evaluate(
                """() => {
                    const problems = [];
                    const fragments = [];
                    let rows = 0;
                    let measured = 0;
                    document.querySelectorAll('table.cols-8 tr').forEach(tr => {
                        const cells = Array.prototype.slice.call(tr.children)
                            .filter(c => c.offsetParent !== null);
                        if (cells.length < 2) { return; }
                        rows += 1;
                        const boxes = cells.map(c => c.getBoundingClientRect());
                        for (let i = 0; i + 1 < boxes.length; i += 1) {
                            if (boxes[i].right > boxes[i + 1].left + 0.5) {
                                problems.push('cellOverlap:' + cells[i].textContent.trim().slice(0, 24));
                            }
                        }
                        cells.forEach((c, ci) => {
                            const box = boxes[ci];
                            const style = getComputedStyle(c);
                            const right = box.right - parseFloat(style.paddingRight)
                                - parseFloat(style.borderRightWidth);
                            const left = box.left + parseFloat(style.paddingLeft)
                                + parseFloat(style.borderLeftWidth);
                            const next = ci + 1 < boxes.length ? boxes[ci + 1].left : Infinity;
                            const where = tr.parentElement.tagName.toLowerCase() + ' c' + (ci + 1);
                            const walker = document.createTreeWalker(c, NodeFilter.SHOW_TEXT);
                            let node;
                            while ((node = walker.nextNode())) {
                                const text = node.textContent.trim();
                                if (!text) { continue; }
                                const owner = node.parentElement;
                                if (!owner || owner.getClientRects().length === 0) { continue; }
                                const range = document.createRange();
                                range.selectNodeContents(node);
                                Array.prototype.slice.call(range.getClientRects()).forEach(r => {
                                    if (r.width <= 0) { return; }
                                    if (r.right > right + 0.5) {
                                        problems.push(where + ' pastBorder+'
                                            + Math.round(r.right - right) + ':' + text.slice(0, 26));
                                    }
                                    if (r.right > next + 0.5) {
                                        problems.push(where + ' intoNext+'
                                            + Math.round(r.right - next) + ':' + text.slice(0, 26));
                                    }
                                    if (r.left < left - 0.5) {
                                        problems.push(where + ' pastLeft:' + text.slice(0, 26));
                                    }
                                });
                            }
                        });
                    });
                    // Fragmentation is measured on the short Latin labels: a
                    // column header or a section reference broken into
                    // three-character pieces is the defect, and it shows as a
                    // label using more line boxes than it has words. Japanese
                    // labels are excluded on purpose - Japanese wraps between
                    // characters by design, so a line count above the word count
                    // is correct typography there, not a fragment.
                    const labels = Array.prototype.slice.call(document.querySelectorAll(
                        'table.cols-8 thead th, table.cols-8 tbody th, table.cols-8 tbody td'));
                    labels.forEach(c => {
                        const active = Array.prototype.slice
                            .call(c.querySelectorAll('span[data-l]'))
                            .find(s => s.getClientRects().length > 0);
                        const holder = active || c;
                        if (holder.childNodes.length !== 1) { return; }
                        const node = holder.childNodes[0];
                        if (node.nodeType !== 3) { return; }
                        const text = node.textContent.trim();
                        if (!text || text.length > 24) { return; }
                        if (/[\\u3040-\\u30ff\\u4e00-\\u9fff]/.test(text)) { return; }
                        const range = document.createRange();
                        range.selectNodeContents(node);
                        const lineTops = new Set();
                        Array.prototype.slice.call(range.getClientRects())
                            .filter(r => r.width > 0)
                            .forEach(r => lineTops.add(Math.round(r.top)));
                        measured += 1;
                        const words = text.split(/\\s+/).length;
                        if (lineTops.size > Math.max(2, words)) {
                            fragments.push(lineTops.size + 'L:' + text);
                        }
                    });
                    return {rows: rows, measured: measured,
                            problems: problems, fragments: fragments};
                }"""
            )
        for language in ("ja", "en"):
            report = overlap_report[language]
            results.check(
                f"print.parameterTableGeometry.{language}",
                not report["problems"],
                f"{report['rows']} rows measured at {A4_PRINT_WIDTH_PX}px, "
                f"problems={report['problems'][:2]}",
            )
            results.check(
                f"print.parameterTableFragments.{language}",
                not report["fragments"],
                f"{report['measured']} short labels measured, fragments={report['fragments'][:2]}",
            )
        page.set_viewport_size({"width": 1280, "height": 900})
        page.wait_for_timeout(200)
        page.emulate_media(media="screen")
        page.wait_for_timeout(250)

        # The DOM says nothing about what the paginator actually emitted, so the
        # authoritative check renders real A4 PDFs and reads the text back.
        check_print_pdf_digests(page, results, target, artifacts)
        if lang_before_quality:
            page.click(f"[data-set-lang='{lang_before_quality}']")
            page.wait_for_timeout(250)

        # ----------------------------------------------------------- lightbox
        figure_button = page.locator("[data-lightbox]").first
        figure_button.scroll_into_view_if_needed()
        figure_button.click()
        page.wait_for_timeout(250)
        results.check("lightbox.opens", page.locator("#lightbox").is_visible())
        results.check(
            "lightbox.focusMoved",
            page.evaluate("() => document.activeElement && document.activeElement.id") == "lightbox-close",
        )
        page.keyboard.press("Escape")
        page.wait_for_timeout(200)
        results.check("lightbox.closesWithEscape", page.locator("#lightbox").is_hidden())
        results.check(
            "lightbox.focusRestored",
            page.evaluate("() => document.activeElement && document.activeElement.hasAttribute('data-lightbox')"),
        )

        # ---------------------------------------------------------------- TOC
        page.evaluate("() => window.scrollTo(0, 0)")
        page.click(".toc__link[href='#ch-13']")
        _settle_scroll(page)
        results.check(
            "toc.navigates",
            page.evaluate("() => Math.abs(document.getElementById('ch-13').getBoundingClientRect().top) < 220"),
            str(page.evaluate("() => document.getElementById('ch-13').getBoundingClientRect().top")),
        )
        results.check(
            "toc.currentSectionIndicator",
            page.locator("#current-section").inner_text().startswith("13"),
            page.locator("#current-section").inner_text(),
        )
        results.check(
            "toc.ariaCurrent",
            page.locator(".toc__link[aria-current='true']").count() == 1,
        )
        results.check(
            "progress.readingBar",
            page.evaluate("() => parseFloat(document.getElementById('reading-progress-value').style.width) > 0"),
        )
        results.check(
            "backToTop.visible",
            "is-visible" in (page.get_attribute("#to-top", "class") or ""),
        )
        page.click("#to-top")
        _settle_scroll(page)
        results.check("backToTop.scrolls", page.evaluate("() => window.scrollY") < 60)

        # ------------------------------------------------------ optional detail
        results.check(
            "details.openByDefault",
            page.evaluate("() => Array.from(document.querySelectorAll('details.optional-details')).every(d => d.open)"),
        )
        page.click("#expand-all")
        page.wait_for_timeout(200)
        results.check(
            "details.collapseAll",
            page.evaluate("() => Array.from(document.querySelectorAll('details.optional-details')).every(d => !d.open)"),
        )
        page.click("#expand-all")
        page.wait_for_timeout(200)
        results.check(
            "details.expandAll",
            page.evaluate("() => Array.from(document.querySelectorAll('details.optional-details')).every(d => d.open)"),
        )

        # ----------------------------------------------------------- overflow
        for name, viewport in (("desktop1440", DESKTOP), ("laptop1024", LAPTOP), ("tablet768", TABLET), ("phone390", PHONE)):
            page.set_viewport_size(viewport)
            page.wait_for_timeout(250)
            overflow = page.evaluate(
                "() => ({ doc: document.documentElement.scrollWidth,"
                " win: window.innerWidth,"
                " widest: (function(){"
                "  let worst = 0, tag='';"
                "  document.querySelectorAll('main *').forEach(function(node){"
                "   const r = node.getBoundingClientRect();"
                "   if (r.right > worst) { worst = r.right; tag = node.tagName + '.' + (node.className || ''); }"
                "  });"
                "  return [Math.round(worst), tag];"
                " })() })"
            )
            results.check(
                f"responsive.noHorizontalOverflow.{name}",
                overflow["doc"] <= overflow["win"] + 1,
                f"scrollWidth={overflow['doc']} innerWidth={overflow['win']} widest={overflow['widest']}",
            )
            if artifacts:
                page.screenshot(path=str(artifacts / f"{name}.png"), full_page=False)

        page.set_viewport_size(PHONE)
        page.wait_for_timeout(200)
        page.click("#toc-toggle")
        page.wait_for_timeout(250)
        results.check("responsive.tocDrawerOpens", page.locator("#toc").evaluate("n => n.classList.contains('is-open')"))
        page.keyboard.press("Escape")
        page.wait_for_timeout(250)
        results.check(
            "responsive.tocDrawerCloses",
            not page.locator("#toc").evaluate("n => n.classList.contains('is-open')"),
        )

        # ------------------------------------------------ japanese wrapping
        page.click("[data-set-lang='ja']")
        page.wait_for_timeout(250)
        kinsoku = page.evaluate(
            "() => {"
            " const NO_START = '\u3001\u3002\uff0c\uff0e\u30fb\uff1a\uff1b\uff1f\uff01"
            "\u3041\u3043\u3045\u3047\u3049\u3063\u3083\u3085\u3087\u308e"
            "\u30a1\u30a3\u30a5\u30a7\u30a9\u30c3\u30e3\u30e5\u30e7\u30ee\u30fc"
            "\uff09\uff3d\uff5d\u300d\u300f\u3009\u300b\u3015)]}';"
            " const range = document.createRange();"
            " let violations = 0, runs = 0;"
            " document.querySelectorAll('main p [data-l=\"ja\"], main li [data-l=\"ja\"],"
            "   main td [data-l=\"ja\"], main figcaption [data-l=\"ja\"]').forEach(node => {"
            "   node.childNodes.forEach(child => {"
            "     if (child.nodeType !== 3) { return; }"
            "     const text = child.textContent;"
            "     if (!/[\\u3040-\\u30ff\\u4e00-\\u9fff]/.test(text)) { return; }"
            "     range.selectNodeContents(child);"
            "     if (range.getClientRects().length < 2) { return; }"
            "     runs += 1;"
            "     let prevTop = null;"
            "     for (let i = 0; i < text.length; i += 1) {"
            "       range.setStart(child, i); range.setEnd(child, Math.min(i + 1, text.length));"
            "       const r = range.getBoundingClientRect();"
            "       if (r.width === 0 && r.height === 0) { continue; }"
            "       const top = Math.round(r.top);"
            "       if (prevTop !== null && top > prevTop && NO_START.includes(text[i])) { violations += 1; }"
            "       prevTop = top;"
            "     }"
            "   });"
            " });"
            " return { runs: runs, violations: violations }; }"
        )
        results.check(
            "typography.japaneseKinsoku",
            kinsoku["violations"] == 0,
            f"{kinsoku['violations']} line-start violations across {kinsoku['runs']} wrapped runs",
        )

        # ---------------------------------------------------- wide tables        page.evaluate("() => window.scrollTo(0, 0)")
        sticky = page.evaluate(
            "() => {"
            " const wrap = document.querySelector('.table-wrap.is-scrollable');"
            " if (!wrap) { return null; }"
            " const scroller = wrap.querySelector('.table-scroll');"
            " const head = wrap.querySelector('tbody th[scope=\"row\"]');"
            " if (!head) { return null; }"
            " const before = head.getBoundingClientRect().left;"
            " scroller.scrollLeft = scroller.scrollWidth;"
            " const after = head.getBoundingClientRect().left;"
            " const overflow = scroller.scrollWidth > scroller.clientWidth;"
            " scroller.scrollLeft = 0;"
            " return { before: Math.round(before), after: Math.round(after), overflow: overflow };"
            " }"
        )
        results.check(
            "tables.stickyRowHeader",
            bool(sticky) and sticky["overflow"] and abs(sticky["after"] - sticky["before"]) <= 2,
            f"{sticky}",
        )
        results.check(
            "tables.scrollHintShown",
            page.locator(".table-wrap.is-scrollable .table-hint").first.is_visible(),
        )

        # ---------------------------------------------------- toggle budget
        toggle_ms = page.evaluate(
            "() => { const t0 = performance.now();"
            " document.querySelector(\"[data-set-lang='en']\").click();"
            " document.body.getBoundingClientRect();"
            " const a = performance.now() - t0;"
            " const t1 = performance.now();"
            " document.querySelector(\"[data-set-lang='ja']\").click();"
            " document.body.getBoundingClientRect();"
            " return Math.round((a + (performance.now() - t1)) / 2); }"
        )
        results.check("perf.languageToggleBudget", toggle_ms < 500, f"{toggle_ms} ms (budget 500)")

        # -------------------------------------------------------------- print
        page.set_viewport_size(DESKTOP)
        # A4 content box at 96 dpi (210mm - 28mm margins wide), so print
        # measurements reflect the real page geometry rather than the screen.
        page.set_viewport_size({"width": 688, "height": 1002})
        # A reader may have collapsed Optional content; printing must restore it.
        page.evaluate(
            "() => { document.querySelectorAll('details.optional-details').forEach(d => { d.open = false; });"
            " window.dispatchEvent(new Event('beforeprint')); }"
        )
        page.emulate_media(media="print")
        page.wait_for_timeout(250)
        active = page.get_attribute("html", "data-lang") or "ja"
        print_state = page.evaluate(
            "() => ({ header: getComputedStyle(document.querySelector('.app-header')).display,"
            " toc: getComputedStyle(document.getElementById('toc')).display,"
            " topBtn: getComputedStyle(document.getElementById('to-top')).display,"
            " steps: getComputedStyle(document.querySelector('.step-check')).display,"
            " figure: getComputedStyle(document.querySelector('figure')).display,"
            " table: getComputedStyle(document.querySelector('table')).display,"
            " detailsBody: document.querySelector('.optional-details__body').offsetHeight,"
            " ja: getComputedStyle(document.querySelector(\"[data-l='ja']\")).display,"
            " en: getComputedStyle(document.querySelector(\"[data-l='en']\")).display })"
        )
        results.check("print.hidesHeader", print_state["header"] == "none", str(print_state["header"]))
        results.check("print.hidesToc", print_state["toc"] == "none")
        results.check("print.hidesBackToTop", print_state["topBtn"] == "none")
        results.check("print.hidesCheckboxes", print_state["steps"] == "none")
        results.check("print.keepsFigures", print_state["figure"] != "none")
        results.check("print.keepsTables", print_state["table"] != "none")
        results.check(
            "print.expandsOptionalDetails",
            print_state["detailsBody"] > 40,
            f"optional body height={print_state['detailsBody']}",
        )

        # A block taller than the printable area cannot honour break-inside:avoid.
        # Such a block must be marked at build time so print CSS lets it flow
        # deliberately; an unmarked oversized block is a silent split.
        atomic = page.evaluate(
            "() => {"
            " const PAGE = 1002;"  # A4 height 297mm minus 16mm margins, at 96dpi
            " const out = { unmarked: [], marked: [] };"
            " document.querySelectorAll('.codeblock, .callout').forEach(el => {"
            "   const h = el.getBoundingClientRect().height;"
            "   if (h <= PAGE) { return; }"
            "   const row = { cls: el.className, h: Math.round(h),"
            "                 text: (el.textContent || '').trim().slice(0, 40) };"
            "   if (el.hasAttribute('data-long')) { out.marked.push(row); }"
            "   else { out.unmarked.push(row); }"
            " });"
            " return out; }"
        )
        results.check(
            "print.noSilentBlockSplit",
            not atomic["unmarked"],
            f"unmarked oversized: {atomic['unmarked'][:3]}",
        )
        results.check(
            "print.longBlocksMarked",
            all(
                page.evaluate(
                    "() => Array.from(document.querySelectorAll('.codeblock[data-long]'))"
                    " .every(el => getComputedStyle(el).breakInside === 'auto')"
                )
                for _ in [0]
            ),
            f"{len(atomic['marked'])} block(s) deliberately allowed to flow",
        )
        unguarded = page.evaluate(
            "() => Array.from(document.querySelectorAll('.codeblock, .callout'))"
            " .filter(el => !el.hasAttribute('data-long'))"
            " .filter(el => getComputedStyle(el).breakInside !== 'avoid')"
            " .map(el => (el.textContent || '').trim().slice(0, 40))"
        )
        results.check(
            "print.atomicBlocksGuarded",
            not unguarded,
            f"{len(unguarded)} block(s) without break-inside: avoid",
        )
        shown, hidden = ("ja", "en") if active == "ja" else ("en", "ja")
        results.check(
            "print.activeLanguageOnly",
            print_state[shown] != "none" and print_state[hidden] == "none",
            f"active={active} ja={print_state['ja']} en={print_state['en']}",
        )
        if artifacts:
            page.pdf(path=str(artifacts / "print.pdf"), format="A4", print_background=True)
        page.emulate_media(media="screen")

        browser.close()
    return results


def notebook_digests(html: Path) -> list[str]:
    """The 64-character digests the parameter appendix promises to print.

    Read from the built file rather than hard-coded, so the check follows the
    runtime instead of drifting from it.
    """
    text = html.read_text(encoding="utf-8")
    found: list[str] = []
    for match in re.finditer(r">([0-9a-f]{64})<", text):
        if match.group(1) not in found:
            found.append(match.group(1))
    return found


def check_print_pdf_digests(page, results: "Results", target: Path, artifacts: Path | None) -> None:
    """Render real A4 PDFs and require every digest to survive pagination.

    A DOM measurement cannot see this: a table cell reports no overflow while the
    paginator quietly drops the part of an unbreakable 64-character token that
    does not fit the column, so the printed page carries a truncated digest that
    still looks like a digest. Chromium's own PDF is the only faithful evidence.
    The digests are ASCII, so they extract reliably even though the surrounding
    Japanese is drawn with a subset font that pypdf cannot decode.
    """
    from pypdf import PdfReader

    expected = notebook_digests(target)
    results.check(
        "print.pdf.digestsDiscovered",
        len(expected) >= 5,
        f"{len(expected)} distinct 64-char digests found in the document",
    )
    if not expected:
        return

    destination = artifacts or Path(tempfile.mkdtemp(prefix="furusato-print-"))
    destination.mkdir(parents=True, exist_ok=True)

    for language in ("ja", "en"):
        page.emulate_media(media="screen")
        page.wait_for_timeout(200)
        page.click(f"[data-set-lang='{language}']")
        page.wait_for_timeout(300)
        # page.pdf() honours whatever media is currently emulated, so this must be
        # switched back to print before rendering or the PDF is a screen layout.
        page.emulate_media(media="print")
        page.wait_for_timeout(300)
        pdf_path = destination / f"print-{language}.pdf"
        page.pdf(path=str(pdf_path), format="A4", print_background=True)

        reader = PdfReader(str(pdf_path))
        # Default extraction follows the content stream and keeps a two-line wrap
        # contiguous. "layout" mode was measured here and is worse: it recovered
        # none of the digests in either language.
        extracted = "".join(p.extract_text() or "" for p in reader.pages)
        # Chromium may break a long token across lines; join before matching so a
        # legitimate wrap is not mistaken for truncation.
        flattened = re.sub(r"[\s\u00ad]+", "", extracted)
        missing = [d for d in expected if d not in flattened]
        truncated = [
            d
            for d in missing
            if any(d[:n] in flattened for n in (56, 48, 40, 36, 32))
        ]
        results.check(
            f"print.pdf.digestsComplete.{language}",
            not missing,
            f"{len(expected) - len(missing)}/{len(expected)} digests print in full"
            + (f"; truncated={[d[:16] + '...' for d in truncated][:3]}" if truncated else "")
            + (f"; missing={[d[:16] + '...' for d in missing][:3]}" if missing else ""),
        )
        _check_pdf_images(page, results, pdf_path, language)

    page.emulate_media(media="screen")
    page.wait_for_timeout(200)


def _check_pdf_images(page, results: "Results", pdf_path: Path, language: str) -> None:
    """Every screenshot must survive into the printed PDF as a real raster image.

    CSS visibility is not the same evidence: an image that the print pipeline
    never decoded is still ``display: block`` in the DOM while contributing no
    XObject to the PDF, so the page prints an empty frame with a caption under
    it. Counting the image XObjects Chromium actually embedded is the only way
    to prove the screenshots are on the paper.
    """
    figures = page.evaluate(
        "() => document.querySelectorAll('figure.figure--shot img, figure img[src^=\"data:\"]').length"
    )
    embedded = 0
    with pdf_path.open("rb") as handle:
        import fitz  # PyMuPDF, already required by the docs render audit

        document = fitz.open(stream=handle.read(), filetype="pdf")
        try:
            unique: set[int] = set()
            for index in range(document.page_count):
                for image in document.get_page_images(index, full=False):
                    unique.add(image[0])
            embedded = len(unique)
        finally:
            document.close()
    results.check(
        f"print.pdf.screenshotsEmbedded.{language}",
        figures > 0 and embedded >= figures,
        f"{embedded} image XObjects for {figures} inline figure images",
    )


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
    parser.add_argument("--target", default=str(TARGET))
    parser.add_argument("--artifacts", default=None, help="write screenshots and a print PDF here")
    args = parser.parse_args(argv)

    target = Path(args.target).resolve()
    if not target.is_file():
        print(f"missing build output: {target}")
        return 1
    artifacts = Path(args.artifacts).resolve() if args.artifacts else None
    if artifacts:
        artifacts.mkdir(parents=True, exist_ok=True)

    try:
        results = run(target, artifacts)
    except Error as error:  # pragma: no cover - browser level failure
        print(f"playwright error: {error}")
        return 1

    for name, ok, detail in results.rows:
        print(f"[{'  ok  ' if ok else ' FAIL '}] {name:44s} {detail}")
    print()
    print(f"{len(results.rows)} interaction checks, {len(results.failed)} failed")
    return 1 if results.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
