#!/usr/bin/env python3
"""Read-only collector for Hisense VIDAA TVs.

Serves the TV-side page over HTTPS, hands out a queue of paths to read,
and stores everything the TV sends back under dumps/.

No writes are ever issued to the TV: the page only calls read-style
vendor APIs (HiUtils_createRequest('fileRead'), Hisense_FileRead,
File.read, XHR file:///). See t.html.
"""
from __future__ import annotations

import argparse
import base64
import re
import json
import mimetypes
import os
import ssl
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent
DUMPS = ROOT / "dumps"
CERT = ROOT / "certs" / "cert.pem"
KEY = ROOT / "certs" / "key.pem"
JOBS = ROOT / "jobs.json"
MANIFEST = DUMPS / "manifest.jsonl"

DEFAULT_JOBS = [
    {"path": "/etc/passwd", "type": "file"},
    {"path": "/etc/version", "type": "file"},
    {"path": "/", "type": "dir"},
    {"path": "/etc/", "type": "dir"},
    {"path": "/config/", "type": "dir"},
    {"path": "/tvconfig/", "type": "dir"},
    {"path": "/tvcustomer/", "type": "dir"},
    {"path": "/websdk/", "type": "dir"},
    {"path": "/applications/", "type": "dir"},
    {"path": "/hidata/", "type": "dir"},
    {"path": "/OAD/", "type": "dir"},
    {"path": "/Customer/", "type": "dir"},
]


PAGE_NAME = re.compile(r"^[tp]\d{0,2}\.html$")
PAGE_ALIASES = {"/index.html": "t.html"}


def page_file(path: str) -> Path | None:
    """Resolve a URL path to a probe page, or None if it is not one.

    Only names the collector actually publishes are served: t.html and the
    numbered probe pages. Everything else — source files, certs, dumps, path
    traversal — falls through to 404.
    """
    name = PAGE_ALIASES.get(path)
    if name is None:
        name = path.lstrip("/")
        if not name.endswith(".html"):
            name += ".html"
        if not PAGE_NAME.match(name):
            return None
    candidate = ROOT / name
    return candidate if candidate.is_file() else None


def safe_name(path: str) -> str:
    p = path.strip("/").replace("/", "__") or "root"
    return "".join(c if c.isalnum() or c in ".__-" else "_" for c in p)[:180]


def load_jobs() -> list[dict]:
    if not JOBS.exists():
        JOBS.write_text(json.dumps(DEFAULT_JOBS, ensure_ascii=False, indent=1))
    try:
        return json.loads(JOBS.read_text())
    except Exception:
        return list(DEFAULT_JOBS)


def write_manifest(entry: dict) -> None:
    DUMPS.mkdir(parents=True, exist_ok=True)
    with MANIFEST.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


class Handler(BaseHTTPRequestHandler):
    server_version = "tvdump/1.0"

    def log_message(self, fmt: str, *args) -> None:  # quieter default log
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    # ---------- helpers ----------
    def _send(self, code: int, body: bytes, ctype: str = "text/plain; charset=utf-8") -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj, code: int = 200) -> None:
        self._send(code, json.dumps(obj, ensure_ascii=False).encode(), "application/json")

    # ---------- routes ----------
    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        qs = parse_qs(parsed.query)
        page = page_file(parsed.path)
        if parsed.path in ("/", "/index"):
            self._index()
        elif page is not None:
            self._send(200, page.read_bytes(), "text/html; charset=utf-8")
        elif parsed.path == "/job":
            cursor = int(qs.get("cursor", ["0"])[0])
            jobs = load_jobs()
            self._json({"cursor": cursor, "total": len(jobs), "jobs": jobs[cursor:]})
        elif parsed.path == "/probe":
            self._json({"ok": True})
        else:
            self._send(404, b"not found")

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b""
        try:
            payload = json.loads(raw.decode("utf-8", "replace") or "{}")
        except Exception:
            payload = {"raw": base64.b64encode(raw).decode()}

        if parsed.path == "/upload":
            self._store(payload)
            self._json({"ok": True})
        elif parsed.path == "/probe":
            self._store_probe(payload)
            self._json({"ok": True})
        else:
            self._send(404, b"not found")

    # ---------- storage ----------
    def _store(self, payload: dict) -> None:
        path = str(payload.get("path", "unknown"))
        data = payload.get("data")
        status = payload.get("status", "ok")
        DUMPS.mkdir(parents=True, exist_ok=True)
        name = safe_name(path)
        prefix = "dir" if payload.get("type") == "dir" else "file"
        target = DUMPS / f"{prefix}__{name}.txt"
        if isinstance(data, str):
            target.write_text(data, encoding="utf-8", errors="replace")
        else:
            target.write_bytes(b"")
        write_manifest({
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "path": path,
            "type": payload.get("type", "file"),
            "status": status,
            "bytes": len(data) if isinstance(data, str) else 0,
            "strategy": payload.get("strategy"),
            "file": target.name,
            "error": payload.get("error"),
        })
        print(f"[+] {path} -> {target.name} ({status})", flush=True)

    def _store_probe(self, payload: dict) -> None:
        DUMPS.mkdir(parents=True, exist_ok=True)
        name = payload.get("name") or "inventory"
        target = DUMPS / f"probe__{name}.json"
        target.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
        items = next((len(v) for k in ("functions", "tests", "calls", "shapes")
                      if isinstance(v := payload.get(k), (list, dict))), 0)
        print(f"[+] probe {name}: {items} items", flush=True)

    def _index(self) -> None:
        rows = []
        if DUMPS.exists():
            for f in sorted(DUMPS.iterdir()):
                if f.is_file() and f.name != "manifest.jsonl":
                    rows.append(f"<li><a href='/d/{f.name}'>{f.name}</a> "
                                f"<small>{f.stat().st_size} B</small></li>")
        html = ("<html><head><meta charset='utf-8'><title>tv-dump</title></head><body>"
                f"<h1>tv-dump</h1><p>TV page: <a href='/t.html'>/t.html</a></p>"
                f"<ul>{''.join(rows) or '<li>empty</li>'}</ul></body></html>")
        self._send(200, html.encode(), "text/html; charset=utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=8443)
    ap.add_argument("--http", action="store_true", help="serve plain HTTP instead of TLS")
    args = ap.parse_args()

    DUMPS.mkdir(parents=True, exist_ok=True)
    load_jobs()

    httpd = ThreadingHTTPServer((args.host, args.port), Handler)
    if not args.http:
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(CERT, KEY)
        httpd.socket = ctx.wrap_socket(httpd.socket, server_side=True)
    scheme = "http" if args.http else "https"
    print(f"listening on {scheme}://{args.host}:{args.port}  (page: /t.html)", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nbye", flush=True)


if __name__ == "__main__":
    main()
