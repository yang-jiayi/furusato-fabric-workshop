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
TARGET = ROOT / "docs" / "furusato-workshop-v2-7-0-complete.html"

#: A4 portrait at 96 dpi - the width at which the defects appear.
A4_PRINT_WIDTH_PX = 794

#: Compares every text rect against its own cell's content box and against the
#: next cell's edge, for all eight columns, head and body.
GEOMETRY_JS = """() => {
  const problems = [];
  document.querySelectorAll('table.cols-8 tr').forEach(tr => {
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
        "an identifier paints past the safety-gate column",
        "@media print{table.cols-8 tbody td:nth-child(7){overflow-wrap:normal !important;}}",
        "c7",
    ),
    (
        "a slash-run paints past the default-behaviour column",
        "@media print{table.cols-8 tbody td:nth-child(6){overflow-wrap:normal !important;}}",
        "c6",
    ),
    (
        "the section header overflows the table's right edge",
        "@media print{table.cols-8 thead th:nth-child(8),table.cols-8 tbody td:nth-child(8)"
        "{width:5% !important;}table.cols-8 thead th{white-space:nowrap !important;}}",
        "c8",
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

        for language in ("ja", "en"):
            page.emulate_media(media="screen")
            page.wait_for_timeout(200)
            page.click(f"[data-set-lang='{language}']")
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
