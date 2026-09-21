"""Metadata-count claims must not consume an unrelated table caption number."""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools" / "html"))

from validate_html import Structure, precondition_registration_claims


def claims(markup: str):
    document = Structure()
    document.feed(markup)
    document.close()
    return precondition_registration_claims(document.root, 97)


class RegistrationClaimTests(unittest.TestCase):
    def test_table_caption_number_does_not_join_unrelated_body(self):
        self.assertEqual(claims(
            '<figcaption>Table 97 <span data-l="en">Operational steps</span></figcaption>'
            '<table><tr><td><span data-l="en">Register the intended objects</span></td></tr></table>'
        ), [])

    def test_actual_claim_in_each_language_is_rejected(self):
        self.assertTrue(claims('<p><span data-l="ja">97 件を登録しました。</span></p>'))
        self.assertTrue(claims('<p><span data-l="en">Registered 97 objects.</span></p>'))

    def test_registration_value_across_cells_is_rejected(self):
        self.assertTrue(claims(
            '<table><tr><th><span data-l="en">Registered objects</span></th>'
            '<td><span data-l="en">97</span></td></tr></table>'
        ))

    def test_correct_precondition_and_zero_write_explanations_pass(self):
        self.assertEqual(claims(
            '<p><span data-l="en">A 97-object precondition is not a registered result.</span></p>'
            '<p><span data-l="ja">97 件の前提条件が不一致なら登録は 0 件です。</span></p>'
        ), [])


if __name__ == "__main__":
    unittest.main()
