#!/usr/bin/env python3
"""Behaviour tests for the tv-dump collector.

These pin what a client sees: the TV asks for a page, posts a probe, or fetches
the job queue. They do not touch the handler internals, so the route table can
be restructured underneath them.
"""
from __future__ import annotations

import json
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory

import server


class CollectorTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self._saved = (server.DUMPS, server.MANIFEST, server.JOBS)

        server.DUMPS = self.root / "dumps"
        server.MANIFEST = server.DUMPS / "manifest.jsonl"
        server.JOBS = self.root / "jobs.json"
        server.DUMPS.mkdir(parents=True, exist_ok=True)

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        self.port = self.httpd.server_address[1]
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()
        server.DUMPS, server.MANIFEST, server.JOBS = self._saved
        self.tmp.cleanup()

    # ---------- helpers ----------
    def get(self, path: str):
        url = f"http://127.0.0.1:{self.port}{path}"
        try:
            with urllib.request.urlopen(url, timeout=5) as r:
                return r.status, r.headers.get("Content-Type", ""), r.read()
        except urllib.error.HTTPError as e:
            return e.code, e.headers.get("Content-Type", ""), e.read()

    def post(self, path: str, payload: dict):
        url = f"http://127.0.0.1:{self.port}{path}"
        data = json.dumps(payload).encode()
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            return e.code, e.read()

    # ---------- pages ----------
    def test_serves_every_probe_page_by_both_names(self) -> None:
        for stem in ["t", "p", "p2", "p7", "p10", "p11", "p12", "p13"]:
            for path in (f"/{stem}.html", f"/{stem}"):
                status, ctype, body = self.get(path)
                self.assertEqual(status, 200, f"{path} -> {status}")
                self.assertIn("text/html", ctype)
                self.assertGreater(len(body), 200, path)

    def test_index_html_is_an_alias_for_the_main_page(self) -> None:
        status, _, body = self.get("/index.html")
        self.assertEqual(status, 200)
        self.assertIn(b"tv probe", body)

    def test_unknown_and_non_page_paths_are_404(self) -> None:
        for path in ("/nope", "/server.py", "/certs/cert.pem", "/dumps/", "/../server.py"):
            status, _, _ = self.get(path)
            self.assertEqual(status, 404, path)

    # ---------- queue ----------
    def test_job_queue_returns_remaining_paths(self) -> None:
        status, _, body = self.get("/job?cursor=0")
        self.assertEqual(status, 200)
        data = json.loads(body)
        self.assertEqual(data["cursor"], 0)
        self.assertEqual(data["total"], len(server.DEFAULT_JOBS))
        self.assertEqual(len(data["jobs"]), len(server.DEFAULT_JOBS))

        status, _, body = self.get("/job?cursor=10")
        data = json.loads(body)
        self.assertEqual(len(data["jobs"]), max(0, len(server.DEFAULT_JOBS) - 10))

    # ---------- storage ----------
    def test_upload_writes_the_file_and_a_manifest_line(self) -> None:
        status, _ = self.post("/upload", {
            "path": "/etc/version", "type": "file", "status": "ok",
            "strategy": "hiutils", "data": "V0000.09.60V.Q0612\n",
        })
        self.assertEqual(status, 200)
        written = server.DUMPS / "file__etc__version.txt"
        self.assertTrue(written.exists())
        self.assertIn("Q0612", written.read_text())
        lines = server.MANIFEST.read_text().strip().splitlines()
        self.assertEqual(len(lines), 1)
        entry = json.loads(lines[0])
        self.assertEqual(entry["path"], "/etc/version")
        self.assertEqual(entry["bytes"], len("V0000.09.60V.Q0612\n"))

    def test_probe_is_stored_under_its_own_name(self) -> None:
        status, _ = self.post("/probe", {"name": "bridge", "tests": [1, 2, 3]})
        self.assertEqual(status, 200)
        stored = server.DUMPS / "probe__bridge.json"
        self.assertTrue(stored.exists())
        self.assertEqual(json.loads(stored.read_text())["name"], "bridge")

    def test_probe_without_name_falls_back_to_inventory(self) -> None:
        self.post("/probe", {"functions": {"a": "b"}})
        self.assertTrue((server.DUMPS / "probe__inventory.json").exists())

    def test_unknown_post_path_is_404(self) -> None:
        status, _ = self.post("/whatever", {"a": 1})
        self.assertEqual(status, 404)

    def test_non_json_body_does_not_crash_the_collector(self) -> None:
        url = f"http://127.0.0.1:{self.port}/probe"
        req = urllib.request.Request(url, data=b"not json at all", headers={"Content-Type": "text/plain"})
        with urllib.request.urlopen(req, timeout=5) as r:
            self.assertEqual(r.status, 200)
        self.assertTrue((server.DUMPS / "probe__inventory.json").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
