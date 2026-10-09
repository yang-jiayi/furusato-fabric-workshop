"""Local-only browser transport: one HTML target, no directory or remote access."""

import io
import socket
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "tools" / "docs"), str(ROOT / "tools" / "html")]

import validate_preview30 as validator


class BrowserTransportTests(unittest.TestCase):
    def setUp(self):
        work = tempfile.TemporaryDirectory(prefix="preview30-browser-transport-")
        self.addCleanup(work.cleanup)
        self.target = Path(work.name) / "guide.html"
        self.payload = b"<!doctype html><meta charset=utf-8><p>Standalone guide</p>"
        self.target.write_bytes(self.payload)
        (self.target.parent / "private.txt").write_text("Never exposed", encoding="utf-8")

    def test_default_transport_stays_a_local_file(self):
        with validator.local_browser_target(self.target) as url:
            self.assertEqual(url, self.target.resolve().as_uri())
            self.assertFalse(validator.allowed_browser_request("https://example.com", url))

    def test_loopback_serves_exact_html_and_denies_other_paths(self):
        with validator.local_browser_target(self.target, "loopback") as url:
            address = urlsplit(url)
            self.assertEqual(address.hostname, "127.0.0.1")
            with urlopen(url, timeout=2) as response:
                self.assertEqual(response.read(), self.payload)
                self.assertEqual(response.headers["Content-Type"], "text/html; charset=utf-8")
                self.assertEqual(response.headers["Cache-Control"], "no-store")
            with urlopen(Request(url, method="HEAD"), timeout=2) as response:
                self.assertEqual(response.read(), b"")
                self.assertEqual(int(response.headers["Content-Length"]), len(self.payload))
            for suffix in ("/", "/private.txt", "/../private.txt", "/workshop.html?other=1"):
                with self.subTest(path=suffix), self.assertRaises(HTTPError) as caught:
                    urlopen(f"http://127.0.0.1:{address.port}{suffix}", timeout=2)
                self.assertEqual(caught.exception.code, 404)

    def test_allowlist_requires_the_exact_loopback_document_url(self):
        with validator.local_browser_target(self.target, "loopback") as url:
            address = urlsplit(url)
            for allowed in (url, url + "?lang=ja", url + "?lang=en"):
                self.assertTrue(validator.allowed_browser_request(allowed, url))
                with urlopen(allowed, timeout=2) as response:
                    self.assertEqual(response.read(), self.payload)
            blocked = (
                "https://app.fabric.microsoft.com/", "https://example.com/",
                url.replace("127.0.0.1", "localhost"), url.replace("http:", "https:"),
                url + "?query=1", url + "?lang=fr", url + "?lang=en&lang=ja",
                url + "?lang=en&query=1", url + "#chapter", url.replace("/workshop.html", "/private.txt"),
                f"http://127.0.0.1:{address.port + 1}/workshop.html",
            )
            for request in blocked:
                with self.subTest(request=request):
                    self.assertFalse(validator.allowed_browser_request(request, url))

    def test_server_closes_when_validation_raises(self):
        with self.assertRaisesRegex(RuntimeError, "Synthetic browser failure"):
            with validator.local_browser_target(self.target, "loopback") as url:
                address = urlsplit(url)
                with urlopen(url, timeout=2) as response:
                    self.assertEqual(response.status, 200)
                raise RuntimeError("Synthetic browser failure")
        with self.assertRaises(OSError):
            socket.create_connection(("127.0.0.1", address.port), timeout=2)

    def test_transport_option_requires_interaction_validation(self):
        for transport in ("file", "loopback"):
            with self.subTest(transport=transport), redirect_stderr(io.StringIO()) as error:
                with self.assertRaises(SystemExit) as caught:
                    validator.main(["--pair", str(self.target.parent), "--review", str(self.target.parent / "review"),
                                    "--browser-transport", transport])
                self.assertEqual(caught.exception.code, 2)
                self.assertIn("--browser-transport requires --interactions", error.getvalue())


if __name__ == "__main__":
    unittest.main()
