"""Synthetic test endpoints must not become allowed documentation sources."""

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import validate_docs


class SourceHostBoundaries(unittest.TestCase):
    def test_fixture_endpoints_are_scoped_to_their_test_file(self):
        for path, hosts in validate_docs.PROVENANCE_FIXTURE_HOSTS.items():
            with self.subTest(path=path):
                self.assertTrue(Path(path).name.startswith("test_"))
                self.assertTrue(hosts.isdisjoint(validate_docs.ALLOWED_HOSTS))
                self.assertNotIn(
                    path.replace("test_", "guide_"), validate_docs.PROVENANCE_FIXTURE_HOSTS
                )

    def test_document_hosts_remain_an_explicit_allowlist(self):
        self.assertIn("database.windows.net", validate_docs.ALLOWED_HOSTS)
        self.assertIn("purl.oclc.org", validate_docs.ALLOWED_HOSTS)
        self.assertNotIn("synthetic.invalid", validate_docs.ALLOWED_HOSTS)
        self.assertNotIn("unverified.example.com", validate_docs.ALLOWED_HOSTS)
        self.assertNotIn("api.fabric.microsoft.com.evil.example", validate_docs.ALLOWED_HOSTS)


if __name__ == "__main__":
    unittest.main()
