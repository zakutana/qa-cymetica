"""The Gem Screener with our improvements on it: http://127.0.0.1:8803/gem-screener/app

The page is THEIR live /gem-screener/app, read anonymously (GET, no cookies, no key) and cached for 60 seconds, with
patch.css and patch.js added: every figure is their own snapshot, their functions draw it. Every other GET is passed to cymetica.com the same way. Every other method is refused
here, before anything leaves this machine. Their socket is left out: a push of new data would undo nothing, but it
cannot be proxied here, and the page then simply hides its Live label.
"""
from __future__ import annotations

import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import httpx

HERE = Path(__file__).resolve().parent
PORT = 8803
UPSTREAM = "https://cymetica.com"
TTL = 60.0
OWN = {"patch.css": "text/css; charset=utf-8"}
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
        _client = httpx.Client(timeout=90, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0 (qa-cymetica gem-screener-trust mock)"})
    r = _client.get(UPSTREAM + path)
    out = (r.status_code, r.headers.get("content-type", "application/octet-stream"), r.content, dict(r.headers))
    if r.status_code == 200:
        _cache[path] = (time.time(), out)
    return out


GO = "/* ================= go ================= */"


def page(path: str) -> bytes:
    """Their page with our changes added, and no socket. Their code is one strict function, so patch.js goes inside it,
    just before their first render. /gem-screener only frames that app, and passes as it is."""
    status, _, body, _ = fetch(path)
    if status != 200:
        raise RuntimeError(f"{path} -> HTTP {status}")
    html = body.decode("utf-8")
    v = str(int(time.time()))
    html = html.replace("<head>", "<head><script>window.WebSocket = undefined;</script>", 1)
    html = html.replace("</head>", f'<link rel="stylesheet" href="/_gt/patch.css?v={v}">\n</head>', 1)
    return html.replace(GO, (HERE / "patch.js").read_text(encoding="utf-8") + "\n" + GO, 1).encode("utf-8")


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
        bare = self.path.split("#")[0].split("?")[0].rstrip("/")
        if bare == "":
            self.send_response(302)
            self.send_header("Location", "/gem-screener/app")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        if bare == "/gem-screener/app":
            return self.send(200, "text/html; charset=utf-8", page(self.path))
        if bare.startswith("/_gt/") and bare[5:] in OWN:
            return self.send(200, OWN[bare[5:]], (HERE / bare[5:]).read_bytes())
        status, ctype, body, headers = fetch(self.path)
        return self.send(status, ctype, body, headers)

    do_HEAD = do_GET

    def refuse(self):
        self.send(403, "application/json; charset=utf-8", b'{"detail":"Mock: nothing is sent from this copy."}')

    do_POST = do_PUT = do_PATCH = do_DELETE = refuse

    def log_message(self, fmt, *args):
        if "--quiet" not in sys.argv:
            sys.stderr.write("%s %s\n" % (self.command, self.path[:120]))


if __name__ == "__main__":
    print("Gem Screener with our improvements: http://127.0.0.1:%d/gem-screener/app  (Ctrl+C stops it)" % PORT)
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
