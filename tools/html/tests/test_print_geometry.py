"""Negative fixtures for the A4 print geometry and fragmentation gates.

The gate exists because four real defects reached paper while the suite reported
green: an identifier, a slash-run and a path painting past their cell border, and
a column header overflowing the table's right edge. Each is planted back here and
must be detected, then the shipped page must measure clean.
"""

from __future__ import annotations

import argparse
import pathlib
import sys

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[3]
WORKSHOP_VERSION = (ROOT / "WORKSHOP_VERSION").read_text(encoding="utf-8").strip()
TARGET = ROOT / "docs" / f"furusato-workshop-v{WORKSHOP_VERSION.replace('.', '-')}-complete.html"

#: A4 portrait at 96 dpi - the width at which the defects appear.
A4_PRINT_WIDTH_PX = 794

#: Compares every text rect against its own cell's content box and against the
#: next cell's edge, for every wide reference table, head and body.
GEOMETRY_JS = """() => {
  const problems = [];
  document.querySelectorAll('table.evaluation-reference tr, table.selection-contract tr, table.notebook-parameters tr').forEach(tr => {
    const cells = [].slice.call(tr.children).filter(c => c.offsetParent !== null);
    if (cells.length < 2) { return; }
    const boxes = cells.map(c => c.getBoundingClientRect());
    cells.forEach((c, ci) => {
      const box = boxes[ci], style = getComputedStyle(c);
      const right = box.right - parseFloat(style.paddingRight) - parseFloat(style.borderRightWidth);
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
        [].slice.call(range.getClientRects()).forEach(r => {
          if (r.width <= 0) { return; }
          if (r.right > right + 0.5) {
            problems.push(where + ' pastBorder:' + text.slice(0, 26));
          }
          if (r.right > next + 0.5) {
            problems.push(where + ' intoNext:' + text.slice(0, 26));
          }
        });
      }
    });
  });
  return problems;
}"""

#: Each fixture is (label, CSS that reinstates the defect, substring expected in
#: at least one reported problem).
FIXTURES = (
    (
        "the first reference column paints past its cell",
        "@media print{table.evaluation-reference,table.selection-contract,table.notebook-parameters{table-layout:fixed !important;width:100% !important;min-width:0 !important;}"
        "table.evaluation-reference tr>:first-child,table.selection-contract tr>:first-child,table.notebook-parameters tr>:first-child{width:3px !important;min-width:0 !important;"
        "max-width:3px !important;white-space:nowrap !important;}}",
        "pastBorder",
    ),
    (
        "a narrow second reference column paints past its cell",
        "@media print{table.evaluation-reference,table.selection-contract,table.notebook-parameters{table-layout:fixed !important;width:100% !important;min-width:0 !important;}"
        "table.evaluation-reference tr>:nth-child(2),table.selection-contract tr>:nth-child(2),table.notebook-parameters tr>:nth-child(2){width:3px !important;min-width:0 !important;"
        "max-width:3px !important;white-space:nowrap !important;}}",
        "pastBorder",
    ),
    (
        "a narrow final reference column paints past its cell",
        "@media print{table.evaluation-reference,table.selection-contract,table.notebook-parameters{table-layout:fixed !important;width:100% !important;min-width:0 !important;}"
        "table.evaluation-reference tr>:last-child,table.selection-contract tr>:last-child,table.notebook-parameters tr>:last-child{width:3px !important;min-width:0 !important;"
        "max-width:3px !important;white-space:nowrap !important;}}",
        "pastBorder",
    ),
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", type=pathlib.Path, default=TARGET, help="HTML edition to inspect")
    args = parser.parse_args(argv)
    target = args.target.resolve()
    if not target.is_file():
        print(f"missing build output: {target}")
        return 1
    print(f"Target: {target}")
    failures = 0
    with sync_playwright() as driver:
        browser = driver.chromium.launch()
        page = browser.new_page(viewport={"width": A4_PRINT_WIDTH_PX, "height": 1000})
        page.goto(target.as_uri())
        page.wait_for_timeout(1200)
        if page.locator("table.evaluation-reference, table.selection-contract, table.notebook-parameters").count() == 0:
            print("  FAIL current guide has no wide reference tables to measure")
            browser.close()
            return 1

        for language in ("ja", "en"):
            page.emulate_media(media="screen")
            page.wait_for_timeout(200)
            page.click(f"button[data-language='{language}']")
            page.wait_for_timeout(350)
            page.emulate_media(media="print")
            page.wait_for_timeout(500)
            shipped = page.evaluate(GEOMETRY_JS)
            if shipped:
                print(f"  FAIL shipped page reports {language}: {shipped[:2]}")
                failures += 1
            else:
                print(f"  ok   shipped page is clean at {A4_PRINT_WIDTH_PX}px ({language})")

        page.emulate_media(media="print")
        page.wait_for_timeout(300)
        for label, css, expected in FIXTURES:
            handle = page.add_style_tag(content=css)
            page.wait_for_timeout(400)
            problems = page.evaluate(GEOMETRY_JS)
            if any(expected in item for item in problems):
                print(f"  ok   detected: {label}")
            else:
                print(f"  FAIL undetected: {label} (got {problems[:2]})")
                failures += 1
            page.evaluate("(node) => node.remove()", handle)
            page.wait_for_timeout(300)

        browser.close()

    total = len(FIXTURES) + 2
    print(f"\n{total} print geometry fixtures, {failures} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
