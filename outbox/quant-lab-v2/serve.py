"""Serve the Quant Lab v2 mock on http://127.0.0.1:8801/, as the operator opens it.

This folder's files, every one with Cache-Control: no-store. A bare http.server sends no such header, and on
2026-10-30 the operator's browser kept an old index.html under the new ql.css ("a co je toto za hnus?"): the first
mark in the second round's lockup. Their style.css, the fonts and the coin logos load from their own hosts straight
from the page. POST, PUT, PATCH and DELETE are refused: nothing is sent from this copy.
"""
import mimetypes
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
PORT = 8801
TYPES = {".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8", ".js": "text/javascript; charset=utf-8",
         ".json": "application/json; charset=utf-8", ".md": "text/plain; charset=utf-8", ".txt": "text/plain; charset=utf-8",
         ".svg": "image/svg+xml", ".webp": "image/webp", ".png": "image/png", ".jpg": "image/jpeg"}


class Handler(BaseHTTPRequestHandler):
    def send(self, code, ctype, body):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def do_GET(self):
        rel = self.path.split("?")[0].lstrip("/") or "index.html"
        f = (HERE / rel).resolve()
        if not f.is_file() or HERE not in f.parents:
            return self.send(404, "text/plain; charset=utf-8", b"not here")
        ctype = TYPES.get(f.suffix.lower()) or mimetypes.guess_type(f.name)[0] or "application/octet-stream"
        return self.send(200, ctype, f.read_bytes())

    do_HEAD = do_GET

    def refuse(self):
        self.send(403, "application/json; charset=utf-8", b'{"detail":"Mock: nothing is sent from this copy."}')

    do_POST = do_PUT = do_PATCH = do_DELETE = refuse

    def log_message(self, fmt, *args):
        if "--quiet" not in sys.argv:
            sys.stderr.write("%s %s\n" % (self.command, self.path[:120]))


if __name__ == "__main__":
    print("Quant Lab v2 mock: http://127.0.0.1:%d/  (Ctrl+C stops it)" % PORT)
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
