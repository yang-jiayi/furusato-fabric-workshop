"""Read-only payload-decoding regressions; no live runtime files are mutated."""

from __future__ import annotations

import base64
import gzip
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools" / "docs"))

from furusato_docs.notebook_payload import PAYLOAD_CELL_TAG, decode_notebook_payload


def cell(source: str, *, tagged: bool = True) -> dict:
    return {
        "cell_type": "code",
        "metadata": {"tags": [PAYLOAD_CELL_TAG] if tagged else []},
        "source": source.splitlines(keepends=True),
    }


class NotebookPayloadTests(unittest.TestCase):
    def setUp(self):
        self.payload = {"bundle": {"example.json": '{"complete":true}\n'}, "other": [1, 2, 3]}
        self.encoded = base64.b64encode(
            gzip.compress(json.dumps(self.payload).encode("utf-8"), mtime=0)
        ).decode("ascii")

    def test_split_tagged_cells_decode_in_document_order(self):
        chunks = [self.encoded[:37], self.encoded[37:83], self.encoded[83:]]
        notebook = {"cells": [
            cell("PARTICIPANT_ID = '001'", tagged=False),
            cell("UNRELATED = " + repr("A" * 400), tagged=False),
            cell("_PAYLOAD_CHUNKS = " + repr(chunks[:1])),
            cell("_PAYLOAD_CHUNKS.extend(" + repr(chunks[1:2]) + ")"),
            cell("_PAYLOAD_CHUNKS.extend(" + repr(chunks[2:]) + ")"),
        ]}
        self.assertTrue(all(len(chunk) < 200 for chunk in chunks))
        self.assertEqual(decode_notebook_payload(notebook), self.payload)

    def test_legacy_cell_is_found_without_a_fixed_index(self):
        notebook = {"cells": [
            cell("IGNORE = 1", tagged=False),
            cell("_PAYLOAD_CHUNKS = " + repr([self.encoded]), tagged=False),
        ]}
        self.assertEqual(decode_notebook_payload(notebook), self.payload)

    def test_tagged_layout_does_not_collect_unrelated_quoted_text(self):
        notebook = {"cells": [cell(
            "NOT_PAYLOAD = " + repr("A" * 400) + "\n_PAYLOAD_CHUNKS = " + repr([self.encoded])
        )]}
        self.assertEqual(decode_notebook_payload(notebook), self.payload)

    def test_other_notebook_statements_are_not_executed(self):
        notebook = {"cells": [cell(
            "_PAYLOAD_CHUNKS = " + repr([self.encoded]) + "\nraise RuntimeError('do not execute')"
        )]}
        self.assertEqual(decode_notebook_payload(notebook), self.payload)

    def test_chunk_expressions_are_not_executed(self):
        notebook = {"cells": [cell("_PAYLOAD_CHUNKS = __import__('builtins').eval('1 + 1')")]}
        with patch("builtins.eval") as evaluate, self.assertRaises(ValueError):
            decode_notebook_payload(notebook)
        evaluate.assert_not_called()

    def test_extension_before_initializer_is_rejected(self):
        notebook = {"cells": [cell("_PAYLOAD_CHUNKS.extend(" + repr([self.encoded]) + ")")]}
        with self.assertRaisesRegex(ValueError, "no initializer"):
            decode_notebook_payload(notebook)

    def test_duplicate_initializers_are_rejected(self):
        notebook = {"cells": [
            cell("_PAYLOAD_CHUNKS = " + repr([self.encoded])),
            cell("_PAYLOAD_CHUNKS = " + repr([self.encoded])),
        ]}
        with self.assertRaisesRegex(ValueError, "more than one"):
            decode_notebook_payload(notebook)

    def test_missing_and_nonliteral_payloads_are_rejected(self):
        for cells in ([], [cell("_PAYLOAD_CHUNKS = [42]")], [cell("_PAYLOAD_CHUNKS = []")]):
            with self.subTest(cells=cells), self.assertRaises(ValueError):
                decode_notebook_payload({"cells": cells})

    def test_incomplete_or_invalid_base64_is_rejected(self):
        for encoded in (self.encoded[:-12], self.encoded + "!"):
            with self.subTest(encoded=encoded), self.assertRaises((ValueError, EOFError)):
                decode_notebook_payload({"cells": [cell("_PAYLOAD_CHUNKS = " + repr([encoded]))]})


if __name__ == "__main__":
    unittest.main()
