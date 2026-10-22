"""Serve the Build it Better mockup on http://127.0.0.1:8791/build-it-better, as the operator opens it.

The page is cymetica.com's own (header, footer, scripts) with the new Build it Better block in it, so it needs their
static files and the board's public reads. Nothing else reaches cymetica.com:

* GET /static/*, /i18n/*, /og/app/*           their public files and app cards, fetched once and kept in memory
* GET /previews/*                             the mockup's own pictures of the live apps (shoot_previews.py)
* GET the board's public reads                /api/v1/build-it-better/requests[/ET-n], /apps?q=, /apps/leaderboard,
                                              /token-launch/chains
* GET /api/v1/build-it-better/me              404, so the button reads "Send the request" as it does signed in
* any other GET under /api/                   404
* any other GET                               302 to the same path on cymetica.com (the page's links open the real site)
* POST, PUT, PATCH, DELETE                    403 "Mockup: nothing is sent from this copy." -- no request, upload,
                                              verdict or telemetry leaves this machine
"""
import re
import sys
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
ORIGIN = "https://cymetica.com"
READS = re.compile(r"^/api/v1/(build-it-better/(requests(/ET-\d+)?|apps(/leaderboard)?)|token-launch/chains)(\?.*)?$")
cache = {}


def fetch(path):
    if path not in cache:
        req = urllib.request.Request(ORIGIN + path, headers={"User-Agent": "Mozilla/5.0 (mockup preview)"})
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                cache[path] = (r.status, r.headers.get("Content-Type", "application/octet-stream"), r.read())
        except urllib.error.HTTPError as e:
            return e.code, "application/json", b"{}"
        except OSError:
            return 502, "application/json", b"{}"
    return cache[path]


class Handler(BaseHTTPRequestHandler):
    def send(self, code, ctype, body, extra=None):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def do_GET(self):
        path = self.path
        if path.split("?")[0] in ("/", "/build-it-better", "/index.html"):
            return self.send(200, "text/html; charset=utf-8", (HERE / "index.html").read_bytes())
        if path.startswith("/previews/"):   # the mockup's own pictures of the live apps (shoot_previews.py)
            f = HERE / "previews" / Path(path.split("?")[0]).name
            return self.send(200, "image/jpeg", f.read_bytes()) if f.is_file() else self.send(404, "text/plain", b"")
        if path.startswith(("/static/", "/i18n/", "/og/app/")) or READS.match(path):
            fresh = path.startswith("/api/")
            if fresh:
                cache.pop(path, None)   # the board is read live, every time, like the real page
            return self.send(*fetch(path))
        if path.startswith("/api/") or path.startswith("/ws/"):
            return self.send(404, "application/json", b'{"detail":"not served by the mockup"}')
        return self.send(302, "text/plain", b"", {"Location": ORIGIN + path})

    do_HEAD = do_GET

    def refuse(self):
        self.send(403, "application/json", b'{"detail":"Mockup: nothing is sent from this copy."}')

    do_POST = do_PUT = do_PATCH = do_DELETE = refuse

    def log_message(self, fmt, *args):
        if "--quiet" not in sys.argv:
            sys.stderr.write("%s %s\n" % (self.command, self.path[:120]))


def make(port):
    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


if __name__ == "__main__":
    srv = make(8791)
    print("Build it Better mockup: http://127.0.0.1:8791/build-it-better  (Ctrl+C stops it)")
    srv.serve_forever()
