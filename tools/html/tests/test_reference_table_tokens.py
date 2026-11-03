"""Screen-layout regressions for narrow, horizontally scrollable reference tables."""

from __future__ import annotations

import unittest
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[3]
CSS = ROOT / "tools" / "html" / "assets" / "preview30.css"

FIXTURE = """
<!doctype html><html data-lang="en"><meta charset="utf-8"><main>
<section id="ch-6-4"><div class="table-wrap"><div class="table-scroll">
<table><thead><tr><th>Type</th><th>Source table</th><th>Notes</th></tr></thead>
<tbody><tr><td><span data-l="ja"><code>Integer</code></span><span data-l="en"><code>Integer</code></span></td>
<td><span data-l="ja"><code>ot_pref_donation_flow</code></span><span data-l="en"><code>ot_pref_donation_flow</code></span></td>
<td>A description that should wrap naturally across several lines in a narrow table.</td></tr></tbody></table>
</div></div></section>
<section id="ch-17-7"><div class="table-wrap"><div class="table-scroll">
<table><thead><tr><th>Source kind</th><th>Semantic path</th><th>Description</th></tr></thead>
<tbody><tr><td><code>lakehouse_tables.column</code></td>
<td><code>Schemas / dbo / Tables / ot_supplier / SupplierDisplayName</code></td>
<td>Use the stable business identifier for identity and this property for readable output.</td></tr></tbody></table>
</div></div></section>
<section id="ch-12-4"><div class="table-wrap"><div class="table-scroll">
<table><thead><tr><th>Table</th><th>Measure</th><th>DAX</th><th>Format</th></tr></thead>
<tbody><tr><td><code>DonationAnalytics</code></td><td><code>TotalDonationAmountYen</code></td>
<td>SUM ( 'Donation'[DonationAmountYen] )</td><td><code>#,0;(#,0);-</code></td></tr></tbody></table>
</div></div></section>
<section id="ch-9-2"><div class="codeblock codeblock--source">
<pre tabindex="0"><code>EventID,DonationID,DonationAmountYen,EventTimestampUtc</code></pre></div></section>
<section id="appendix-b-1"><div class="table-wrap"><div class="table-scroll">
<table><thead><tr><th>Parameter</th><th>Meaning</th></tr></thead><tbody>
<tr><td><code>EXPECTED_DEFINITION_SHA256</code></td>
<td>The definition is checked before any changes are applied.</td></tr></tbody></table>
</div></div></section>
</main></html>
"""


class ReferenceTableTokenTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.driver = sync_playwright().start()
        cls.browser = cls.driver.chromium.launch()

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.driver.stop()

    def test_literal_tokens_stay_whole_and_tables_scroll_on_narrow_screens(self):
        page = self.browser.new_page(viewport={"width": 390, "height": 844})
        try:
            page.set_content(FIXTURE)
            page.add_style_tag(content=CSS.read_text(encoding="utf-8"))
            for language in ("en", "ja"):
                page.locator("html").evaluate(
                    "(node, lang) => node.setAttribute('data-lang', lang)", language
                )
                for section in ("#ch-6-4", "#ch-17-7", "#ch-12-4", "#appendix-b-1"):
                    with self.subTest(language=language, section=section):
                        region = page.locator(section + " .table-scroll")
                        self.assertEqual(
                            "auto",
                            region.evaluate("node => getComputedStyle(node).overflowX"),
                        )
                        self.assertGreater(
                            region.evaluate("node => node.scrollWidth"),
                            region.evaluate("node => node.clientWidth"),
                        )
                        for token in region.locator("code:visible").all():
                            self.assertEqual(
                                "nowrap",
                                token.evaluate("node => getComputedStyle(node).whiteSpace"),
                            )
                            self.assertEqual(
                                1,
                                token.evaluate(
                                    "node => {const r=document.createRange();"
                                    "r.selectNodeContents(node);"
                                    "return new Set([...r.getClientRects()]"
                                    ".map(rect=>Math.round(rect.top))).size}"
                                ),
                            )
            pre = page.locator("#ch-9-2 pre")
            self.assertEqual("pre", pre.evaluate("node => getComputedStyle(node).whiteSpace"))
            self.assertEqual("auto", pre.evaluate("node => getComputedStyle(node).overflowX"))
            self.assertEqual("0", pre.get_attribute("tabindex"))
            self.assertGreater(
                pre.evaluate("node => node.scrollWidth"),
                pre.evaluate("node => node.clientWidth"),
            )
        finally:
            page.close()

    def test_desktop_reference_tables_fit_without_unnecessary_scroll(self):
        page = self.browser.new_page(viewport={"width": 1280, "height": 900})
        try:
            page.set_content(FIXTURE)
            page.add_style_tag(content=CSS.read_text(encoding="utf-8"))
            for region in page.locator(".table-scroll").all():
                self.assertLessEqual(
                    region.evaluate("node => node.scrollWidth"),
                    region.evaluate("node => node.clientWidth") + 1,
                )
        finally:
            page.close()


if __name__ == "__main__":
    unittest.main()
