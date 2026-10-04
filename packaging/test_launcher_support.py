"""Run from packaging/: python -m unittest test_launcher_support
(stdlib only; launcher_support has no Django/Twisted imports)."""

import http.server
import json
import os
import socket
import sys
import tempfile
import threading
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import launcher_support as s  # noqa: E402


class _Api(http.server.BaseHTTPRequestHandler):
    body, status = b"", 200

    def do_GET(self):
        self.send_response(self.status)
        self.end_headers()
        self.wfile.write(self.body)

    def log_message(self, *args):
        pass


def _serve(body, status=200):
    handler = type("H", (_Api,), {"body": body, "status": status})
    server = http.server.HTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://127.0.0.1:{server.server_port}/"


class PortTests(unittest.TestCase):
    def test_skips_busy_port(self):
        blocker = socket.socket()
        blocker.bind(("0.0.0.0", 0))
        busy = blocker.getsockname()[1]
        try:
            self.assertFalse(s.port_is_free(busy))
            self.assertNotEqual(s.pick_port(preferred=busy), busy)
        finally:
            blocker.close()

    def test_with_port(self):
        self.assertEqual(s.with_port("192.168.1.13:8000", 8001), "192.168.1.13:8001")
        self.assertEqual(s.with_port("192.168.1.13", 8001), "192.168.1.13:8001")
        self.assertEqual(s.with_port("", 8001), "")


class VersionTests(unittest.TestCase):
    def test_parse(self):
        self.assertEqual(s.parse_version("v0.4.1"), (0, 4, 1))
        for bad in ("0.0.0-dev", "pi-4-standalone-packaging", "", None, "v1.2.x"):
            self.assertIsNone(s.parse_version(bad))

    def test_is_newer_compares_numerically(self):
        self.assertTrue(s.is_newer("v0.10.0", "0.9.0"))
        self.assertFalse(s.is_newer("v0.4.0", "0.4.0"))
        self.assertFalse(s.is_newer("v0.3.9", "0.4.0"))
        self.assertFalse(s.is_newer("garbage", "0.4.0"))

    @staticmethod
    def _write(path, text):
        with open(path, "w") as f:
            f.write(text)

    def test_read_current_version(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "version.txt")
            self.assertIsNone(s.read_current_version(path))
            self._write(path, "0.4.0\n")
            self.assertEqual(s.read_current_version(path), "0.4.0")
            self._write(path, "some-branch\n")
            self.assertIsNone(s.read_current_version(path))


class SslTests(unittest.TestCase):
    def test_context_has_trusted_cas(self):
        # A frozen app can't rely on the OS CA bundle; the context must carry certifi's.
        self.assertGreater(len(s._ssl_context().get_ca_certs()), 0)


class UpdateCheckTests(unittest.TestCase):
    def check(self, body, current="0.4.0", status=200):
        server, url = _serve(body, status)
        self.addCleanup(server.shutdown)
        return s.check_for_update(current, api_url=url, timeout=2)

    def test_newer_release(self):
        body = json.dumps({"tag_name": "v0.5.0", "html_url": "https://example/r"}).encode()
        self.assertEqual(self.check(body), ("v0.5.0", "https://example/r"))

    def test_same_or_older_release(self):
        body = json.dumps({"tag_name": "v0.4.0", "html_url": "https://example/r"}).encode()
        self.assertIsNone(self.check(body))

    def test_failures_are_silent(self):
        self.assertIsNone(self.check(b"{}", status=404))  # private repo / no release
        self.assertIsNone(self.check(b"not json"))
        self.assertIsNone(self.check(b'{"tag_name": "v9.0.0"}'))  # missing html_url

    def test_unreachable_server(self):
        self.assertIsNone(s.check_for_update("0.4.0", api_url="http://127.0.0.1:1/", timeout=1))

    def test_no_check_without_a_known_version(self):
        self.assertIsNone(s.check_for_update(None))
        self.assertIsNone(s.check_for_update("0.0.0-dev"))


if __name__ == "__main__":
    unittest.main()
