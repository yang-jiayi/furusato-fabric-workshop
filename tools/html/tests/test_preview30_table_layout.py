"""HTML-only responsive table and layout regression fixtures.

Run with: python tools\\html\\tests\\test_preview30_table_layout.py
"""

from __future__ import annotations

import unittest
from pathlib import Path
import sys

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[3]
CSS = ROOT / "tools" / "html" / "assets" / "preview30.css"
sys.path[:0] = [str(ROOT / "tools" / "html"), str(ROOT / "tools" / "docs")]

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
for identity and this property for human-readable output.</td></tr>
<tr><th>kusto</th>
<td>Materialized Views / DonationObservationSummaryForAgent</td>
<td>kusto.table</td><td>true</td><td>DonationObservationSummaryForAgent</td>
<td>Curated operational aggregates with stable business identifiers.</td></tr></tbody>
</table></div></div></section>
<section id="appendix-c-25-canonical-evaluation"><div class="table-wrap">
<div class="table-scroll" tabindex="0" role="region" aria-label="Scoring criteria">
<table class="cols-2 canonical-condition-rubric"><caption>Scoring criteria</caption>
<thead><tr><th>Condition ID</th><th>Verbatim scoring criterion</th></tr></thead>
<tbody><tr><th scope="row">B01.content</th><td>The answer preserves the required business meaning.</td></tr>
<tr><th scope="row">B01.execution</th><td>Execution evidence is checked separately from content.</td></tr>
<tr><th scope="row">B01.boundary.long-provenance-id</th><td>Do not infer unsupported data scope or runtime behavior.</td></tr></tbody>
</table></div></div></section>
<section id="appendix-b-1"><div class="table-wrap">
<div class="table-scroll" tabindex="0" role="region" aria-label="Notebook parameters">
<table><caption>Notebook parameters</caption>
<thead><tr><th>Notebook</th><th>Parameter</th><th>Default</th><th>Meaning</th></tr></thead>
<tbody><tr><th>Notebook 03</th><td>EXPECTED_DEFINITION_SHA256</td><td>''</td>
<td>Hash of the ontology definition checked before applying. If the definition
has changed, the run stops without applying changes.</td></tr></tbody>
</table></div></div></section>
<section id="appendix-c-1"><h3>Question list</h3>
<div class="table-wrap"><div class="table-scroll"><table>
<thead><tr><th>No.</th><th>ID</th><th>Question</th><th>Conditions</th></tr></thead>
<tbody><tr><th>1</th><td>T01</td><td>Keep the complete question unchanged.</td><td>8</td></tr></tbody>
</table></div></div>
<div class="table-wrap"><div class="table-scroll"><table>
<thead><tr><th>ID</th><th>Date</th><th>Answer</th><th>Score</th><th>Notes</th></tr></thead>
<tbody><tr><th>T01</th><td></td><td></td><td></td><td></td></tr></tbody>
</table></div></div></section>
</main></html>
"""

MEASURE = """() => {
  const problems=[];
  for (const [section, columns] of [['#ch-17-7',[1,3,4,5]],['#appendix-b-1',[1,2]],
                                    ['#appendix-c-25-canonical-evaluation',[1]]]) {
    const table=document.querySelector(section+' table');
    for (const row of table.tBodies[0].rows) {
      for (const column of columns) {
        const cell=row.children[column-1];
        const walker=document.createTreeWalker(cell,NodeFilter.SHOW_TEXT);
        const rects=[];
        while(walker.nextNode()) {
          const text=walker.currentNode;
          for(const match of text.textContent.matchAll(/\\S+/g)) {
            const range=document.createRange();
            range.setStart(text,match.index);range.setEnd(text,match.index+match[0].length);
            const wordRects=[...range.getClientRects()].filter(rect=>rect.width>0);
            if(new Set(wordRects.map(rect=>Math.round(rect.top))).size>1)
              problems.push(section+':wrap:'+column+':'+match[0]);
            rects.push(...wordRects);
          }
        }
        const box=cell.getBoundingClientRect(), style=getComputedStyle(cell);
        const right=box.right-parseFloat(style.paddingRight);
        const left=box.left+parseFloat(style.paddingLeft);
        if(rects.some(r=>r.right>right+1 || r.left<left-1))
          problems.push(section+':overflow:'+column+':'+cell.textContent);
      }
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

    def test_scrolled_header_remains_nearly_opaque_without_changing_sticky_behavior(self):
        self.page.set_content("""<header>Current workshop</header><main>
          <p style="height:2000px;background:#000;color:white">SCROLLED_BODY</p>
          </main>""")
        self.page.add_style_tag(content=CSS.read_text(encoding="utf-8"))
        for width in (2160, 390):
            with self.subTest(width=width):
                self.page.set_viewport_size({"width": width, "height": 900})
                self.page.evaluate("window.scrollTo(0,200)")
                header = self.page.locator("header")
                self.assertAlmostEqual(.94, header.evaluate("""node=>{
                  const components=getComputedStyle(node).backgroundColor.match(/[\\d.]+/g).map(Number);
                  return components.length===4 ? components[3] : 1;
                }"""), places=2)
                self.assertEqual("sticky", header.evaluate(
                    "node=>getComputedStyle(node).position"))
                self.assertEqual(0, header.bounding_box()["y"])

    def test_short_tokens_and_parameter_identifiers_stay_whole(self):
        for language in ("en", "ja"):
            self.page.locator("html").evaluate(
                "(node, lang) => node.setAttribute('data-lang', lang)", language
            )
            for width in (1440, 1024, 390, 320):
                with self.subTest(language=language, width=width):
                    self.page.set_viewport_size({"width": width, "height": 900})
                    self.assertEqual([], self.page.evaluate(MEASURE))
                    self.assertTrue(self.page.evaluate(
                        "()=>document.documentElement.scrollWidth<=window.innerWidth"
                    ))
                    if width == 390:
                        prose = self.page.locator("#ch-17-7 tbody tr:first-child td:nth-child(6)")
                        self.assertEqual("normal", prose.evaluate(
                            "node=>getComputedStyle(node).whiteSpace"
                        ))
                        self.assertGreater(prose.evaluate("""node=>{
                          const range=document.createRange();range.selectNodeContents(node);
                          return new Set([...range.getClientRects()].filter(rect=>rect.width>0)
                            .map(rect=>Math.round(rect.top))).size;
                        }"""), 1)
                    for section in ("#ch-17-7", "#appendix-b-1", "#appendix-c-25-canonical-evaluation"):
                        region = self.page.locator(section + " .table-scroll")
                        self.assertEqual("auto", region.evaluate(
                            "node=>getComputedStyle(node).overflowX"
                        ))
                        if width < 1440 and region.evaluate(
                                "node=>node.scrollWidth>node.clientWidth"):
                            self.assertTrue(region.evaluate(
                                "node=>{node.scrollLeft=node.scrollWidth;return node.scrollLeft>0}"
                            ))
                        region.evaluate("node=>{node.scrollLeft=0}")

    def test_canonical_condition_ids_remain_whole_in_a_scoped_scrollable_table(self):
        self.page.set_content("""<html data-lang="en"><main>
          <section id="appendix-c-15-canonical-evaluation"><div class="table-wrap">
          <div class="table-scroll"><table class="cols-3 canonical-condition-rubric">
          <thead><tr><th>Condition ID</th><th>Verbatim Japanese reference</th>
          <th>English explanation</th></tr></thead><tbody><tr>
          <th scope="row">B04.content</th><td>Canonical condition text</td>
          <td>Include every required value and do not assert zero records.</td>
          </tr></tbody></table></div></div></section></main></html>""")
        self.page.add_style_tag(content=CSS.read_text(encoding="utf-8"))
        for width in (1280, 390):
            with self.subTest(width=width):
                self.page.set_viewport_size({"width": width, "height": 900})
                identifier = self.page.locator("#appendix-c-15-canonical-evaluation tbody th")
                self.assertEqual("nowrap", identifier.evaluate(
                    "node=>getComputedStyle(node).whiteSpace"))
                self.assertEqual(1, identifier.evaluate("""node=>{
                  const range=document.createRange();range.selectNodeContents(node);
                  return [...range.getClientRects()].filter(rect=>rect.width>0).length;
                }"""))
                region = self.page.locator("#appendix-c-15-canonical-evaluation .table-scroll")
                self.assertEqual("auto", region.evaluate("node=>getComputedStyle(node).overflowX"))
                self.assertGreaterEqual(
                    float(self.page.locator("table.canonical-condition-rubric").evaluate(
                        "node=>getComputedStyle(node).minWidth").removesuffix("px")),
                    960,
                )
                if width < 700:
                    self.assertGreater(
                        region.evaluate("node=>node.scrollWidth"),
                        region.evaluate("node=>node.clientWidth"),
                    )

    def test_fragmentation_probe_detects_original_narrow_column_regression(self):
        self.page.add_style_tag(content="""
        #ch-17-7 :is(th,td):nth-child(3) {
          width:2%; white-space:normal; overflow-wrap:anywhere;
        }
        #appendix-b-1 :is(th,td):nth-child(1) {
          width:2%; white-space:normal; overflow-wrap:anywhere;
        }
        """)
        problems = self.page.evaluate(MEASURE)
        self.assertTrue(any(problem.startswith("#ch-17-7:wrap:3:") for problem in problems))
        self.assertTrue(any(problem.startswith("#appendix-b-1:wrap:1:") for problem in problems))

    def test_toc_preserves_authored_number_without_another_list_marker(self):
        self.assertEqual("none", self.page.locator(".toc ol").evaluate(
            "node=>getComputedStyle(node).listStyleType"
        ))
        self.assertEqual(["1. Introduction", "Appendix B"],
                         self.page.locator(".toc li").all_text_contents())

if __name__ == "__main__":
    unittest.main()
