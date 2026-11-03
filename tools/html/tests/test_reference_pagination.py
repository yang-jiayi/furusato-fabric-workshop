"""Screen-only regression for the Chapter 6 reference links."""
from __future__ import annotations

import os
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools" / "html"))
sys.path.insert(0, str(ROOT / "tools" / "docs"))

HTML_VALUE = os.environ.get("CROSSREF_HTML")
if not HTML_VALUE and (os.environ.get("CROSSREF_REQUIRE_REFERENCE_PAGINATION") == "1"
                       or __name__ == "__main__"):
    raise RuntimeError("CROSSREF_HTML is required for the focused reference-layout run")
HTML = Path(HTML_VALUE).resolve() if HTML_VALUE else None

REFERENCE_URLS = (
    "https://learn.microsoft.com/en-us/fabric/iq/ontology/how-to-create-entity-types",
    "https://learn.microsoft.com/en-us/fabric/iq/ontology/how-to-bind-data",
)


@unittest.skipUnless(HTML is not None, "Set CROSSREF_HTML to the exact generated candidate")
class ReferenceLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if HTML is None or not HTML.is_file():
            raise FileNotFoundError(HTML)
        from playwright.sync_api import sync_playwright

        cls.driver = sync_playwright().start()
        launch = {"headless": True, "args": ["--no-sandbox"]}
        browser_path = os.environ.get("CROSSREF_BROWSER")
        if browser_path:
            launch["executable_path"] = browser_path
        cls.browser = cls.driver.chromium.launch(**launch)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.driver.stop()

    def test_reference_links_remain_visible_and_contained(self):
        page = self.browser.new_page(viewport={"width": 1440, "height": 1000})
        try:
            page.goto(HTML.as_uri(), wait_until="load")
            page.wait_for_selector("html[data-ready=true]")
            for language in ("ja", "en"):
                page.locator("html").evaluate(
                    "(node, lang) => node.setAttribute('data-lang', lang)", language
                )
                for width in (320, 390, 768, 1440):
                    with self.subTest(language=language, width=width):
                        page.set_viewport_size({"width": width, "height": 844})
                        self.assertLessEqual(
                            page.evaluate("document.documentElement.scrollWidth"),
                            width + 1,
                        )
                        links = page.locator(
                            "#ch-6-5 > ul > li > span > a[href]"
                        ).evaluate_all(
                            "nodes => nodes.filter(node => node.getClientRects().length)"
                            ".map(node => ({href:node.href, rect:node.getBoundingClientRect().toJSON()}))"
                        )
                        self.assertEqual(list(REFERENCE_URLS), [item["href"] for item in links])
                        self.assertTrue(all(
                            item["rect"]["left"] >= -1
                            and item["rect"]["right"] <= width + 1
                            for item in links
                        ), links)
        finally:
            page.close()


if __name__ == "__main__":
    unittest.main()
