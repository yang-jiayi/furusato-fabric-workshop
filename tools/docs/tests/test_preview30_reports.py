"""Fail-closed tests for the standalone preview report generator.

Transformation coverage lives in the synthetic selected-reporting tests; this
module verifies that an unavailable public projection never creates reports.
"""

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "tools" / "docs"), str(ROOT / "tools" / "html")]

from build_preview30_reports import generate, publication_link, report_payloads
from furusato_docs import preview30_public_evidence as public


class PublicReportSourceTests(unittest.TestCase):
    def test_missing_projection_fails_before_creating_reports(self):
        with tempfile.TemporaryDirectory(prefix="preview30-no-projection-") as directory:
            root = Path(directory)
            projection = root / public.DEFAULT_RELATIVE
            output = root / "docs" / "v3-preview" / "reports"
            message = "Public projection must be an existing file inside the clean source root"
            with self.assertRaisesRegex(ValueError, message):
                generate(projection, output, root=root)
            with self.assertRaisesRegex(ValueError, message):
                report_payloads(projection, root=root)
            self.assertFalse(output.exists())

    def test_unverified_or_wrong_publication_links_are_rejected(self):
        for value in (
            "https://example.com/preview",
            "http://github.com/o/r/tree/preview",
            "https://github.com/o/r/tree/",
            "https://github.com/o/r/issues/1",
        ):
            with self.subTest(value=value), self.assertRaises(ValueError):
                publication_link(value, "branch")
        self.assertIsNone(publication_link(None, "branch"))


if __name__ == "__main__":
    unittest.main()
