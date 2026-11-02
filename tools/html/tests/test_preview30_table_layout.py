"""Source-CSS regression fixtures, not a full guide visual or print review.

Run with: python tools\\html\\tests\\test_preview30_table_layout.py
"""

from __future__ import annotations

import unittest
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[3]
CSS = ROOT / "tools" / "html" / "assets" / "preview30.css"

FIXTURE = """
<!doctype html><html data-lang="en"><meta charset="utf-8">
<nav class="toc"><ol><li>1. Introduction</li><li>Appendix B</li></ol></nav>
<main>
<section id="ch-6-4"><div class="table-wrap"><div class="table-scroll">
<table><caption>Entity types and source tables</caption>
<thead><tr><th>Entity type</th><th>Key</th><th>Key type</th>
<th>Source table</th><th><span data-l="en">Static properties</span>
<span data-l="ja">&#38745;&#30340; Property &#12398;&#25968;</span></th></tr></thead>
<tbody>
<tr><th>MunicipalityCategoryMetric</th><td>MunCategoryMetricId</td><td>String</td>
<td>ot_mun_category_metric</td><td>4</td></tr>
<tr><th>PrefectureCategoryMetric</th><td>PrefCategoryMetricId</td><td>String</td>
<td>ot_pref_category_metric</td><td>4</td></tr>
<tr><th>PrefectureDonationFlow</th><td>PrefDonationFlowId</td><td>String</td>
<td>ot_pref_donation_flow</td><td>5</td></tr>
</tbody></table></div></div></section>
<section id="ch-17-7"><div class="table-wrap">
<div class="table-scroll" tabindex="0" role="region" aria-label="Source selection">
<table><caption>Actual flat selection contract</caption>
<thead><tr><th>Source kind</th><th>Semantic path</th><th>Type</th>
<th>is_selected</th><th>Display name</th><th>Description</th></tr></thead>
<tbody><tr><th>lakehouse_tables</th>
<td>Schemas / dbo / Tables / ot_supplier / SupplierDisplayName</td>
<td>lakehouse_tables.column</td><td>true</td><td>SupplierDisplayName</td>
<td>Display-only composition of SupplierName and SupplierId. Use SupplierId
for identity and this property for human-readable output.</td></tr></tbody>
</table></div></div></section>
<section id="appendix-b-1"><div class="table-wrap">
<div class="table-scroll" tabindex="0" role="region" aria-label="Notebook parameters">
<table><caption>Notebook parameters</caption>
<thead><tr><th>Notebook</th><th>Parameter</th><th>Default</th><th>Meaning</th></tr></thead>
<tbody><tr><th>Notebook 03</th><td>EXPECTED_DEFINITION_SHA256</td><td>''</td>
<td>Hash of the ontology definition checked before applying. If the definition
has changed, the run stops without applying changes.</td></tr></tbody>
</table></div></div></section>
</main></html>
"""

MEASURE = """() => {
  const problems=[];
  for (const [section, columns] of [['#ch-17-7',[1,3,4]],['#appendix-b-1',[1,2]]]) {
    const table=document.querySelector(section+' table');
    for (const column of columns) {
      const cell=table.tBodies[0].rows[0].children[column-1];
      const range=document.createRange();range.selectNodeContents(cell);
      const rects=[...range.getClientRects()].filter(r=>r.width>0);
      const box=cell.getBoundingClientRect(), style=getComputedStyle(cell);
      const right=box.right-parseFloat(style.paddingRight);
      const left=box.left+parseFloat(style.paddingLeft);
      if(new Set(rects.map(r=>Math.round(r.top))).size>1)
        problems.push(section+':wrap:'+column);
      if(rects.some(r=>r.right>right+1 || r.left<left-1))
        problems.push(section+':overflow:'+column);
    }
  }
  return problems;
}"""


class PreviewTableLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.driver = sync_playwright().start()
        cls.browser = cls.driver.chromium.launch()

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.driver.stop()

    def setUp(self):
        self.page = self.browser.new_page()
        self.page.set_content(FIXTURE)
        self.page.add_style_tag(content=CSS.read_text(encoding="utf-8"))

    def tearDown(self):
        self.page.close()

    def test_short_tokens_and_parameter_identifiers_stay_whole(self):
        for width in (1440, 1024, 390):
            with self.subTest(width=width):
                self.page.set_viewport_size({"width": width, "height": 900})
                self.assertEqual([], self.page.evaluate(MEASURE))
                self.assertTrue(self.page.evaluate(
                    "()=>document.documentElement.scrollWidth<=window.innerWidth"
                ))
                for section in ("#ch-17-7", "#appendix-b-1"):
                    region = self.page.locator(section + " .table-scroll")
                    self.assertEqual("auto", region.evaluate(
                        "node=>getComputedStyle(node).overflowX"
                    ))
                    if width < 1440:
                        self.assertTrue(region.evaluate(
                            "node=>{node.scrollLeft=node.scrollWidth;return node.scrollLeft>0}"
                        ))
                    region.evaluate("node=>{node.scrollLeft=0}")

    def test_fragmentation_probe_detects_original_narrow_column_regression(self):
        self.page.add_style_tag(content="""
        #ch-17-7 :is(th,td):nth-child(3) {
          width:2%; white-space:normal;
        }
        #appendix-b-1 :is(th,td):nth-child(1) {
          width:2%; white-space:normal;
        }
        """)
        problems = self.page.evaluate(MEASURE)
        self.assertIn("#ch-17-7:wrap:3", problems)
        self.assertIn("#appendix-b-1:wrap:1", problems)

    def test_toc_preserves_authored_number_without_another_list_marker(self):
        self.assertEqual("none", self.page.locator(".toc ol").evaluate(
            "node=>getComputedStyle(node).listStyleType"
        ))
        self.assertEqual(["1. Introduction", "Appendix B"],
                         self.page.locator(".toc li").all_text_contents())

    def test_screen_minimum_width_does_not_spill_into_print(self):
        self.page.emulate_media(media="print")
        self.page.set_viewport_size({"width": 794, "height": 1123})
        for section in ("#ch-17-7", "#appendix-b-1"):
            table = self.page.locator(section + " table")
            self.assertEqual("0px", table.evaluate(
                "node=>getComputedStyle(node).minWidth"
            ))
            self.assertEqual("avoid", self.page.locator(section + " .table-wrap").evaluate(
                "node=>getComputedStyle(node).breakInside"
            ))

    def test_entity_identifiers_fit_actual_a4_content_width(self):
        self.page.emulate_media(media="print")
        # A4 width minus the guide's two 16 mm page margins, at 96 dpi.
        self.page.set_viewport_size({"width": 673, "height": 1123})
        problems = self.page.evaluate("""() => {
          const problems=[];
          for(const cell of document.querySelectorAll('#ch-6-4 tbody :is(th,td)')) {
            const range=document.createRange();range.selectNodeContents(cell);
            const rects=[...range.getClientRects()].filter(r=>r.width>0);
            const box=cell.getBoundingClientRect();
            if(new Set(rects.map(r=>Math.round(r.top))).size>1 ||
               rects.some(r=>r.right>box.right+1))
              problems.push(cell.textContent);
          }
          return problems;
        }""")
        self.assertEqual([], problems)

    def test_static_properties_header_words_fit_in_both_languages(self):
        self.page.emulate_media(media="print")
        self.page.set_viewport_size({"width": 673, "height": 1123})
        measure = """() => {
          const cell=document.querySelector('#ch-6-4 thead th:last-child');
          const walker=document.createTreeWalker(cell,NodeFilter.SHOW_TEXT), problems=[];
          let node;
          while(node=walker.nextNode()) {
            if(!node.parentElement.getClientRects().length) continue;
            for(const match of node.textContent.matchAll(/[A-Za-z]+/g)) {
              const range=document.createRange();
              range.setStart(node,match.index); range.setEnd(node,match.index+match[0].length);
              const rects=[...range.getClientRects()].filter(r=>r.width>0);
              const box=cell.getBoundingClientRect();
              if(new Set(rects.map(r=>Math.round(r.top))).size>1 ||
                 rects.some(r=>r.right>box.right+1))
                problems.push(match[0]);
            }
          }
          return problems;
        }"""
        for language in ("ja", "en"):
            self.page.locator("html").evaluate("(node,lang)=>{node.dataset.lang=lang}", language)
            self.assertEqual([], self.page.evaluate(measure), language)
        self.page.add_style_tag(content="#ch-6-4 thead th:last-child {width:9%;}")
        self.assertIn("properties", self.page.evaluate(measure))


if __name__ == "__main__":
    unittest.main()
