"""MethylMap redesign mock: python outbox/methylmap-redesign/serve.py [--quiet]  ->  http://127.0.0.1:8850/

THEIR live page (biomiv.com/healthbuilder/apps/methylmap, read anonymously with GET) with our design on top:
redesign.css and redesign.js are added after their own files. Their markup, script and wording stay theirs.

  /            their page + our design, the demo report opened
  /?orig       their page as it is live, the demo report opened (to compare)

Only three things are read from biomiv.com: the page, /static/* and /api/v1/healthspan/evidence (gene name only).
Everything else is answered here with an empty reply, and POST, PUT, PATCH and DELETE are refused, so nothing is
sent from a copy and no view of ours is counted. Every reply is Cache-Control: no-store.
"""
from __future__ import annotations

import sys
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
PORT = 8850
UPSTREAM = "https://biomiv.com"
PAGE = "/healthbuilder/apps/methylmap"
EVIDENCE = "/api/v1/healthspan/evidence"
QUIET = "--quiet" in sys.argv
TYPES = {".css": "text/css; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".html": "text/html; charset=utf-8"}

_cache: dict[str, tuple[float, int, str, bytes]] = {}
_lock = threading.Lock()


def upstream(path: str, ttl: float) -> tuple[int, str, bytes]:
    with _lock:
        hit = _cache.get(path)
    if hit and time.time() - hit[0] < ttl:
        return hit[1], hit[2], hit[3]
    req = urllib.request.Request(UPSTREAM + path, headers={"User-Agent": "Mozilla/5.0 (methylmap design mock)"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            out = (r.status, r.headers.get("Content-Type", "application/octet-stream"), r.read())
    except urllib.error.HTTPError as e:
        out = (e.code, e.headers.get("Content-Type", "text/plain"), e.read() or b"")
    except Exception:  # noqa: BLE001 - offline: fall back to what we already have
        if hit:
            return hit[1], hit[2], hit[3]
        out = (504, "text/plain", b"upstream unavailable")
    if out[0] == 200:
        with _lock:
            _cache[path] = (time.time(), *out)
    return out


def page(orig: bool) -> tuple[int, bytes]:
    code, _, body = upstream(PAGE, 60)
    if code != 200:
        snap = HERE / "live" / "page.html"
        if not snap.is_file():
            return code, body
        body = snap.read_bytes()
    html = body.decode("utf-8", "replace")
    v = str(int(max((HERE / n).stat().st_mtime for n in ("redesign.css", "redesign.js", "auto.js"))))
    head = "" if orig else f'<link rel="stylesheet" href="/rd/redesign.css?v={v}">'
    tail = f'<script src="/rd/auto.js?v={v}" defer></script>'
    if not orig:
        tail += f'<script src="/rd/redesign.js?v={v}" defer></script>'
    html = html.replace("</head>", head + "</head>", 1).replace("</body>", tail + "</body>", 1)
    return 200, html.encode("utf-8")


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def send(self, code: int, ctype: str, body: bytes):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def do_GET(self):
        path, _, query = self.path.partition("?")
        if path in ("/", PAGE):
            code, body = page("orig" in query.split("&"))
            return self.send(code, "text/html; charset=utf-8", body)
        if path.startswith("/rd/"):
            f = HERE / path[4:]
            if f.parent == HERE and f.suffix in TYPES and f.is_file():
                return self.send(200, TYPES[f.suffix], f.read_bytes())
            return self.send(404, "text/plain", b"not found")
        if path.startswith("/static/"):
            code, ctype, body = upstream(self.path, 3600)
            return self.send(code, ctype, body)
        if path == EVIDENCE:
            code, ctype, body = upstream(self.path, 600)
            return self.send(code, ctype, body)
        if path.startswith("/api/"):
            return self.send(200, "application/json; charset=utf-8", b"{}")
        return self.send(404, "text/plain", b"not in the mock")

    do_HEAD = do_GET

    def refuse(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length:
            self.rfile.read(length)
        self.send(405, "application/json; charset=utf-8", b'{"error":"the mock sends nothing"}')

    do_POST = do_PUT = do_PATCH = do_DELETE = refuse

    def log_message(self, fmt, *args):
        if not QUIET:
            sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))


if __name__ == "__main__":
    print(f"http://127.0.0.1:{PORT}/", flush=True)
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
