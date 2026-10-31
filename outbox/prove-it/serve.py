"""Prove It on their own page: http://127.0.0.1:8802/prove-it

The page is THEIR live /themes/performance, read anonymously (GET, no cookies, no key) and cached for 60 seconds, with
only its <main class="tp-wrap"> replaced by ours and pi.css / data.js / pi.js added. So the header, the product tray,
the Nexus chat bar, the fonts and every inline style are theirs (the operator, 2026-10-31: my standalone page was "ten
tvuj template defaultni claude vzhled"). Every other GET is passed to cymetica.com the same way. Every other method is
refused here, before anything leaves this machine. Our own files are sent with Cache-Control: no-store.
"""
from __future__ import annotations

import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import httpx

HERE = Path(__file__).resolve().parent
PORT = 8802
UPSTREAM = "https://cymetica.com"
SIBLING = "/themes/performance"   # the nearest live page: a ranked table of things to put money in
TTL = 60.0
OWN = {"pi.css": "text/css; charset=utf-8", "pi.js": "text/javascript; charset=utf-8", "data.js": "text/javascript; charset=utf-8"}
DROP = {"content-security-policy", "content-security-policy-report-only", "content-encoding", "content-length",
        "transfer-encoding", "connection", "set-cookie", "strict-transport-security", "cross-origin-opener-policy",
        "cross-origin-resource-policy", "x-frame-options", "cache-control", "pragma", "etag", "last-modified"}
_cache: dict[str, tuple[float, tuple]] = {}
_client: httpx.Client | None = None


def fetch(path: str) -> tuple[int, str, bytes, dict]:
    """One anonymous GET to their platform; the only call here that leaves this machine."""
    global _client
    hit = _cache.get(path)
    if hit and time.time() - hit[0] < TTL:
        return hit[1]
    if _client is None:
        _client = httpx.Client(timeout=60, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0 (qa-cymetica prove-it mock)"})
    r = _client.get(UPSTREAM + path)
    out = (r.status_code, r.headers.get("content-type", "application/octet-stream"), r.content, dict(r.headers))
    _cache[path] = (time.time(), out)
    return out


def page() -> bytes:
    """Their sibling page with our <main> in place of theirs."""
    status, _, body, _ = fetch(SIBLING)
    if status != 200:
        raise RuntimeError(f"{SIBLING} -> HTTP {status}")
    html = body.decode("utf-8")
    start = html.index('<main class="tp-wrap"')
    end = html.index("</main>", start) + len("</main>")
    ours = (HERE / "main.html").read_text(encoding="utf-8")
    html = html[:start] + ours + html[end:]
    t0 = html.index("<title>")
    html = html[:t0] + "<title>Prove It | EventTrader</title>" + html[html.index("</title>", t0) + len("</title>"):]
    v = str(int(time.time()))
    html = html.replace("</head>", f'<link rel="stylesheet" href="/_pi/pi.css?v={v}">\n</head>', 1)
    i = html.rindex("</body>")
    html = html[:i] + f'<script src="/_pi/data.js?v={v}"></script>\n<script src="/_pi/pi.js?v={v}"></script>\n' + html[i:]
    return html.encode("utf-8")


class Handler(BaseHTTPRequestHandler):
    def send(self, code, ctype, body, headers=None):
        self.send_response(code)
        for k, val in (headers or {}).items():
            if k.lower() not in DROP and k.lower() != "content-type":
                self.send_header(k, val)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("#")[0]
        bare = path.split("?")[0]
        if bare in ("/", "/prove-it", "/prove-it/"):
            if bare == "/":
                self.send_response(302)
                self.send_header("Location", "/prove-it")
                self.end_headers()
                return
            return self.send(200, "text/html; charset=utf-8", page())
        if bare.startswith("/_pi/") and bare[5:] in OWN:
            return self.send(200, OWN[bare[5:]], (HERE / bare[5:]).read_bytes())
        status, ctype, body, headers = fetch(path)
        return self.send(status, ctype, body, headers)

    do_HEAD = do_GET

    def refuse(self):
        self.send(403, "application/json; charset=utf-8", b'{"detail":"Mock: nothing is sent from this copy."}')

    do_POST = do_PUT = do_PATCH = do_DELETE = refuse

    def log_message(self, fmt, *args):
        if "--quiet" not in sys.argv:
            sys.stderr.write("%s %s\n" % (self.command, self.path[:120]))


if __name__ == "__main__":
    print("Prove It mock on their page: http://127.0.0.1:%d/prove-it  (Ctrl+C stops it)" % PORT)
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
