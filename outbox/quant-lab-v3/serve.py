"""Quant Lab mock on their own page: http://127.0.0.1:8807/company/app/experiments

The page is THEIR live /company/app/experiments, read anonymously, with their quant-lab.js and quant-lab.css swapped
for the patched copies here (build.py) and the company API answered from data/ (freeze.py: company 14 after search
#19). Every other GET goes to cymetica.com without cookies or a key. Every other method is refused here.
"""
from __future__ import annotations

import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import httpx

HERE = Path(__file__).resolve().parent
PORT = 8807
UPSTREAM = "https://cymetica.com"
PAGE = "/company/app/experiments"
LOCAL = {"/static/company/quant-lab.js": ("quant-lab.js", "text/javascript; charset=utf-8"),
         "/static/company/quant-lab.css": ("quant-lab.css", "text/css; charset=utf-8")}
API = {"/api/v1/company/mine/id": None,
       "/api/v1/company/mine": "mine.json",
       "/api/v1/company/14/quant-lab": "quant-lab.json",
       "/api/v1/company/14/quant-lab/search": "search.json",
       "/api/v1/company/14/quant-lab/search/results": "results.json",
       "/api/v1/company/14/quant-lab/search/memory": "memory.json"}
JSON = "application/json; charset=utf-8"
client = httpx.Client(timeout=60, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0 (qa-cymetica quant-lab mock)"})


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def send(self, code, ctype, body):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
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
        if path.startswith("/api/v1/company/"):
            return self.send(404, JSON, b'{"detail": "not in this mock"}')
        try:
            r = client.get(UPSTREAM + self.path)
        except httpx.HTTPError as e:
            return self.send(502, "text/plain", str(e).encode("utf-8"))
        return self.send(r.status_code, r.headers.get("content-type", "application/octet-stream"), r.content)

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
