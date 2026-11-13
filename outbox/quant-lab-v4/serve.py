"""Quant Lab v4 mock: http://127.0.0.1:8811/company/app/experiments

Our page shell (index.html: a left menu as in their Promo Market, four tabs) around THEIR quant-lab.js with the v4 hooks
(build.py) and company 14's data as frozen by freeze.py. Their stylesheets, fonts and pictures are fetched from
cymetica.com without cookies or a key. Every method but GET is refused here: Approve, Search now and the bot buttons
answer "This is a mock".
"""
from __future__ import annotations

import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import httpx

HERE = Path(__file__).resolve().parent
PORT = 8811
UPSTREAM = "https://cymetica.com"
PAGE = "/company/app/experiments"
JSON = "application/json; charset=utf-8"
LOCAL = {PAGE: ("index.html", "text/html; charset=utf-8"),
         "/static/company/quant-lab.js": ("quant-lab.js", "text/javascript; charset=utf-8"),
         "/static/company/quant-lab.css": ("their/quant-lab.css", "text/css; charset=utf-8"),
         "/v4/v4.css": ("v4.css", "text/css; charset=utf-8"),
         "/v4/v4.js": ("v4.js", "text/javascript; charset=utf-8"),
         "/v4/ingredients.json": ("data/ingredients.json", JSON)}
API = {"/api/v1/company/mine": "mine.json",
       "/api/v1/company/14/quant-lab": "quant-lab.json",
       "/api/v1/company/14/quant-lab/search": "search.json",
       "/api/v1/company/14/quant-lab/search/results": "results.json",
       "/api/v1/company/14/quant-lab/search/memory": "memory.json"}
client = httpx.Client(timeout=60, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0 (qa-cymetica quant-lab v4 mock)"})
cache: dict[str, tuple[int, str, bytes]] = {}


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def send(self, code, ctype, body, store=False):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "max-age=3600" if store else "no-store")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/":
            self.send_response(302)
            self.send_header("Location", PAGE)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return None
        if path in LOCAL:
            name, ctype = LOCAL[path]
            return self.send(200, ctype, (HERE / name).read_bytes())
        if path == "/api/v1/company/mine/id":
            return self.send(200, JSON, b'{"id": 14}')
        if path in API:
            return self.send(200, JSON, (HERE / "data" / API[path]).read_bytes())
        if path.startswith("/api/") or path.startswith("/ws/"):
            return self.send(404, JSON, b'{"detail": "not in this mock"}')
        if self.path not in cache:
            try:
                r = client.get(UPSTREAM + self.path)
            except httpx.HTTPError as e:
                return self.send(502, "text/plain", str(e).encode("utf-8"))
            cache[self.path] = (r.status_code, r.headers.get("content-type", "application/octet-stream"), r.content)
        code, ctype, body = cache[self.path]
        return self.send(code, ctype, body, store=code == 200)

    do_HEAD = do_GET

    def refuse(self):
        self.send(403, JSON, b'{"detail": "This is a mock: nothing is sent."}')

    do_POST = do_PUT = do_PATCH = do_DELETE = refuse

    def log_message(self, *args):
        if "--quiet" not in sys.argv:
            super().log_message(*args)


if __name__ == "__main__":
    print(f"http://127.0.0.1:{PORT}{PAGE}")
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
