"""Interaction tests for the standalone 3.1 participant HTML guide.

The current guide uses the ``preview30`` renderer: ``data-language`` buttons,
the ``furusato-preview30-learning-v1`` progress store, and a compact search UI.
This suite verifies those actual participant-facing controls rather than the
separate ``furusato_html.page`` application shell.

    python tools/html/tests/test_interaction.py
    python tools/html/tests/test_interaction.py --target <staged-html>
    python tools/html/tests/test_interaction.py --artifacts <dir>
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[3]
WORKSHOP_VERSION = (ROOT / "WORKSHOP_VERSION").read_text(encoding="utf-8").strip()
STORAGE_KEY = "furusato-preview30-learning-v1"
TARGET = ROOT / "docs" / f"furusato-workshop-v{WORKSHOP_VERSION.replace('.', '-')}-complete.html"

VIEWPORTS = (
    ("desktop", {"width": 1440, "height": 900}),
    ("laptop", {"width": 1024, "height": 800}),
    ("tablet", {"width": 768, "height": 1024}),
    ("phone", {"width": 390, "height": 844}),
)


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


def _language_probe(page, language: str, candidates: tuple[str, ...]) -> str | None:
    return page.evaluate(
        """({language, candidates}) => {
          const otherLanguage = language === "ja" ? "en" : "ja";
          for (const term of candidates) {
            const selected = [...document.querySelectorAll(`main [data-l="${language}"]`)]
              .some(node => node.textContent.includes(term));
            const other = [...document.querySelectorAll(`main [data-l="${otherLanguage}"]`)]
              .some(node => node.textContent.includes(term));
            if (selected && !other) return term;
          }
          return null;
        }""",
        {"language": language, "candidates": candidates},
    )


def run(target: Path, artifacts: Path | None = None) -> Results:
    results = Results()
    errors: list[str] = []
    requests: list[str] = []
    unexpected_requests: list[str] = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        context = browser.new_context(viewport=VIEWPORTS[0][1], device_scale_factor=1)
        context.add_init_script(
            """(() => {
              window.__clipboardTest = {mode: "reject", text: ""};
              Object.defineProperty(navigator, "clipboard", {
                configurable: true,
                value: {
                  writeText: async text => {
                    if (window.__clipboardTest.mode === "reject") {
                      throw new Error("simulated clipboard rejection");
                    }
                    window.__clipboardTest.text = text;
                  },
                  readText: async () => window.__clipboardTest.text
                }
              });
            })();"""
        )

        def guard_request(route) -> None:
            request_url = route.request.url
            if urlsplit(request_url).scheme in {"file", "data", "about"}:
                route.continue_()
            else:
                unexpected_requests.append(request_url)
                route.abort()

        context.route("**/*", guard_request)
        page = context.new_page()
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on(
            "console",
            lambda message: errors.append(f"{message.type}: {message.text}")
            if message.type == "error" else None,
        )
        page.on("request", lambda request: requests.append(request.url))

        url = target.resolve().as_uri()
        page.goto(url, wait_until="load")
        page.wait_for_selector("html[data-ready='true']", timeout=15000)

        results.check("load.title", "Furusato Workshop" in page.title(), page.title())
        results.check("load.noPageOrConsoleErrors", not errors, "; ".join(errors[:3]))
        subresources = [request for request in requests if request != url]
        results.check("offline.noSubresourceRequests", not subresources, str(subresources[:3]))
        results.check(
            "structure.uniqueIds",
            page.evaluate("() => { const ids=[...document.querySelectorAll('[id]')].map(e=>e.id); return ids.length===new Set(ids).size; }"),
        )
        results.check(
            "structure.tocTargetsExist",
            page.evaluate(
                """() => [...document.querySelectorAll('.toc a[href^="#"]')].every(link =>
                  document.getElementById(decodeURIComponent(link.hash.slice(1))))"""
            ),
        )
        results.check("structure.bilingualSpansPresent", page.locator("[data-l='ja']").count() > 0 and page.locator("[data-l='en']").count() > 0)
        results.check("structure.checklistPresent", page.locator("input[data-step]").count() > 0)
        results.check("structure.copyButtonsPresent", page.locator("button[data-copy-target]").count() > 0)
        results.check("structure.figuresCanOpen", page.locator("[data-lightbox]").count() > 0)
        results.check("structure.scrollableTablesPresent", page.locator(".table-scroll").count() > 0)
        results.check(
            "structure.copyTargetsResolve",
            page.evaluate("() => [...document.querySelectorAll('button[data-copy-target]')].every(button => document.getElementById(button.dataset.copyTarget))"),
        )
        results.check(
            "structure.stepIdsAreUnique",
            page.evaluate("() => { const ids=[...document.querySelectorAll('input[data-step]')].map(input=>input.dataset.step); return ids.length===new Set(ids).size; }"),
        )
        results.check(
            "structure.figuresHaveAccessibleNames",
            page.evaluate("() => [...document.querySelectorAll('button[data-lightbox]')].every(button => Boolean(button.getAttribute('aria-label') || button.textContent.trim()))"),
        )

        # Language selection is encoded in the URL and applied to every bilingual span.
        ja_heading = page.locator("main > .chapter h2 [data-l='ja']").first
        en_heading = page.locator("main > .chapter h2 [data-l='en']").first
        results.check(
            "lang.defaultJapanese",
            page.get_attribute("html", "lang") == "ja"
            and ja_heading.is_visible()
            and not en_heading.is_visible()
            and page.get_attribute("button[data-language='ja']", "aria-pressed") == "true",
        )
        page.click("button[data-language='en']")
        results.check(
            "lang.switchesEnglish",
            page.get_attribute("html", "lang") == "en"
            and en_heading.is_visible()
            and not ja_heading.is_visible()
            and page.get_attribute("button[data-language='en']", "aria-pressed") == "true",
        )
        results.check(
            "lang.allSpansFollowSelection",
            page.evaluate(
                """() => [...document.querySelectorAll('[data-l]')].every(node =>
                  (node.dataset.l === 'en') === (getComputedStyle(node).display !== 'none'))"""
            ),
        )
        results.check(
            "lang.updatesUrl",
            parse_qs(urlsplit(page.url).query).get("lang") == ["en"],
            page.url,
        )
        page.reload(wait_until="load")
        page.wait_for_selector("html[data-ready='true']")
        results.check("lang.reloadUsesUrl", page.get_attribute("html", "lang") == "en")

        # Search is scoped to the currently selected language and can be cleared.
        ja_probe = _language_probe(page, "ja", ("必ず", "確認", "停止", "寄付"))
        results.check("search.hasJapaneseOnlyProbe", ja_probe is not None, repr(ja_probe))
        if ja_probe:
            page.fill("#search", ja_probe)
            page.wait_for_timeout(80)
            english_matches = page.locator("main > .chapter:not([hidden])").count()
            page.click("button[data-language='ja']")
            page.wait_for_timeout(80)
            japanese_matches = page.locator("main > .chapter:not([hidden])").count()
            results.check(
                "search.activeLanguageOnly",
                english_matches == 0 and japanese_matches > 0,
                f"{ja_probe!r}: en={english_matches}, ja={japanese_matches}",
            )
            results.check(
                "search.statusAnnouncesMatches",
                bool(page.locator("#search-status").inner_text().strip()),
            )
        page.click("#search-clear")
        results.check(
            "search.clearRestoresChapters",
            page.locator("#search").input_value() == ""
            and page.locator("main > .chapter:not([hidden])").count()
            == page.locator("main > .chapter").count(),
        )
        page.click("button[data-language='en']")
        en_probe = _language_probe(page, "en", ("expected", "should", "must", "source"))
        results.check("search.hasEnglishOnlyProbe", en_probe is not None, repr(en_probe))
        if en_probe:
            page.fill("#search", en_probe)
            page.wait_for_timeout(80)
            english_matches = page.locator("main > .chapter:not([hidden])").count()
            page.click("button[data-language='ja']")
            page.wait_for_timeout(80)
            japanese_matches = page.locator("main > .chapter:not([hidden])").count()
            results.check(
                "search.reverseLanguageScope",
                english_matches > 0 and japanese_matches == 0,
                f"{en_probe!r}: en={english_matches}, ja={japanese_matches}",
            )
        page.click("#search-clear")

        # Progress checkboxes persist by stable step ID and reset without changing the guide.
        first_step = page.locator("input[data-step]").first
        step_id = first_step.get_attribute("data-step")
        first_step.check()
        stored = page.evaluate("(key) => JSON.parse(localStorage.getItem(key) || '{}')", STORAGE_KEY)
        results.check("progress.persistsByStepId", stored.get(step_id) is True, str(stored)[:100])
        results.check("progress.statusUpdates", "1/" in page.locator("#progress").inner_text() or "1 /" in page.locator("#progress").inner_text())
        page.reload(wait_until="load")
        page.wait_for_selector("html[data-ready='true']")
        results.check("progress.reloadRestoresStep", page.locator(f"input[data-step='{step_id}']").is_checked())
        page.click("#progress-reset")
        reset_state = page.evaluate("(key) => JSON.parse(localStorage.getItem(key) || '{}')", STORAGE_KEY)
        results.check(
            "progress.resetClearsAllSteps",
            page.locator("input[data-step]:checked").count() == 0
            and all(value is not True for value in reset_state.values()),
            str(reset_state)[:100],
        )

        # Copy supports both clipboard success and the explicit selectable-text fallback.
        copy_button = page.locator("button[data-copy-target]").first
        code_id = copy_button.get_attribute("data-copy-target")
        expected_copy = page.locator(f"#{code_id}").text_content()
        copy_button.click()
        status = page.locator("#copy-status").inner_text().strip()
        selection = page.evaluate("() => String(getSelection())")
        results.check(
            "copy.reportsSelectableTextOnRejection",
            bool(status)
            and selection == expected_copy,
            status,
        )
        page.evaluate(
            "() => { window.__clipboardTest.mode = 'write'; window.__clipboardTest.text = ''; }"
        )
        page.locator("#copy-status").evaluate("(node) => { node.textContent = ''; }")
        copy_button.click()
        page.wait_for_function("() => document.getElementById('copy-status').textContent.length > 0")
        copied = page.evaluate("() => window.__clipboardTest.text")
        results.check(
            "copy.successPathWritesTargetText",
            copied == expected_copy,
        )

        # The modal figure viewer closes by its visible control and by Escape.
        figure_button = page.locator("[data-lightbox]").first
        figure_button.click()
        results.check("lightbox.opensNativeDialog", page.locator("dialog#lightbox[open]").count() == 1)
        page.keyboard.press("Escape")
        results.check("lightbox.closesWithEscape", page.locator("dialog#lightbox[open]").count() == 0)
        figure_button.click()
        page.click("#lightbox-close")
        results.check("lightbox.closesWithButton", page.locator("dialog#lightbox[open]").count() == 0)

        # A TOC link resets filtering and lands on the addressed chapter.
        page.fill("#search", "not-a-workshop-term")
        page.wait_for_timeout(80)
        page.click(".toc a[href='#ch-13']")
        _settle_scroll(page)
        results.check(
            "toc.hashAndTarget",
            urlsplit(page.url).fragment == "ch-13"
            and page.locator("#search").input_value() == ""
            and page.locator("#ch-13").is_visible(),
        )
        results.check(
            "toc.scrollsTargetIntoView",
            page.evaluate("() => Math.abs(document.getElementById('ch-13').getBoundingClientRect().top) < 240"),
        )

        # Responsive widths must not create page-level overflow; wide tables own their scroll.
        for label, viewport in VIEWPORTS:
            page.emulate_media(media="screen")
            page.set_viewport_size(viewport)
            page.wait_for_timeout(120)
            dimensions = page.evaluate(
                "() => ({inner: innerWidth, document: document.documentElement.scrollWidth, body: document.body.scrollWidth})"
            )
            results.check(
                f"responsive.noPageOverflow.{label}",
                dimensions["document"] <= dimensions["inner"] + 1
                and dimensions["body"] <= dimensions["inner"] + 1,
                str(dimensions),
            )
            if label == "phone":
                results.check(
                    "responsive.wideTablesKeepLocalScroll",
                    page.evaluate(
                        "() => [...document.querySelectorAll('.table-scroll')].some(node => node.scrollWidth > node.clientWidth + 2)"
                    ),
                )
                if artifacts:
                    artifacts.mkdir(parents=True, exist_ok=True)
                    page.screenshot(path=str(artifacts / "current-guide-phone.png"), full_page=True)
        if artifacts:
            artifacts.mkdir(parents=True, exist_ok=True)
            page.set_viewport_size(VIEWPORTS[0][1])
            page.screenshot(path=str(artifacts / "current-guide-desktop.png"), full_page=True)

        # Print media must keep chapter content present; geometric clipping is gated separately.
        page.emulate_media(media="print")
        print_state = page.evaluate(
            """() => ({
              chapter: getComputedStyle(document.querySelector('main > .chapter')).display,
              heading: getComputedStyle(document.querySelector('main > .chapter h2')).display,
              figure: [...document.querySelectorAll('main figure')].some(node => getComputedStyle(node).display !== 'none'),
              table: [...document.querySelectorAll('main table')].some(node => getComputedStyle(node).display !== 'none'),
              pageWidth: document.documentElement.scrollWidth,
              viewportWidth: innerWidth
            })"""
        )
        results.check(
            "print.chapterContentRemainsVisible",
            print_state["chapter"] != "none"
            and print_state["heading"] != "none"
            and print_state["figure"]
            and print_state["table"],
            str(print_state),
        )
        results.check(
            "runtime.noPageOrConsoleErrorsAfterInteractions",
            not errors,
            "; ".join(errors[:3]),
        )
        unexpected = unexpected_requests + [
            request for request in requests
            if urlsplit(request).scheme not in {"file", "data", "about"}
        ]
        results.check(
            "offline.noUnexpectedRequestsAfterInteractions",
            not unexpected,
            "; ".join(unexpected[:3]),
        )
        browser.close()

    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", type=Path, default=TARGET, help="HTML edition to inspect")
    parser.add_argument("--artifacts", type=Path, help="Optional directory for desktop and phone screenshots")
    args = parser.parse_args(argv)
    if not args.target.is_file():
        print(f"missing HTML target: {args.target}")
        return 2
    results = run(args.target, args.artifacts)
    for name, passed, detail in results.rows:
        safe_detail = detail.encode("ascii", "backslashreplace").decode("ascii")
        print(f"  {'ok  ' if passed else 'FAIL'} {name}" + (f": {safe_detail}" if detail else ""))
    print(f"\n{len(results.rows)} interaction checks, {len(results.failed)} failed")
    return 1 if results.failed else 0


if __name__ == "__main__":
    sys.exit(main())
