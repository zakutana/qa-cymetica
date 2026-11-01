"""Pitch Cards on their own page: http://127.0.0.1:8802/pitch-cards

The page is THEIR live /agent-casino (our family's app on their site), read anonymously (GET, no cookies, no key) and
cached for 60 seconds, with only the casino app (<div class="at-shell"> to the end of <main>) replaced by app.html and
pc.css / data.js / pc.js added: their header, chat bar, footer, stylesheets and fonts stay. Every other
GET is passed to cymetica.com the same way. Every other method is refused here, before anything leaves this machine.
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
SIBLING = "/agent-casino"
TTL = 60.0
OWN = {"pc.css": "text/css; charset=utf-8", "pc.js": "text/javascript; charset=utf-8", "data.js": "text/javascript; charset=utf-8",
       "scene.webp": "image/webp", "nexus.webp": "image/webp", "nexus-face.webp": "image/webp"}
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
        _client = httpx.Client(timeout=60, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0 (qa-cymetica pitch-cards mock)"})
    r = _client.get(UPSTREAM + path)
    out = (r.status_code, r.headers.get("content-type", "application/octet-stream"), r.content, dict(r.headers))
    if r.status_code == 200:
        _cache[path] = (time.time(), out)
    return out


def page() -> bytes:
    """Their Agent Casino page with our app in place of theirs."""
    status, _, body, _ = fetch(SIBLING)
    if status != 200:
        raise RuntimeError(f"{SIBLING} -> HTTP {status}")
    html = body.decode("utf-8")
    start = html.index('<div class="at-shell"')
    end = html.index("</main>", start)
    html = html[:start] + (HERE / "app.html").read_text(encoding="utf-8") + "\n" + html[end:]
    t0 = html.index("<title>")
    html = html[:t0] + "<title>Pitch Cards: Nexus pitches, you invest | EventTrader</title>" + html[html.index("</title>", t0) + 8:]
    html = html.replace("Agent Casino at cymetica.com/agent-casino", "Pitch Cards at cymetica.com/pitch-cards")
    v = str(int(time.time()))
    html = html.replace("</head>", f'<link rel="stylesheet" href="/_pc/pc.css?v={v}">\n</head>', 1)
    i = html.rindex("</body>")
    html = html[:i] + f'<script src="/_pc/data.js?v={v}"></script>\n<script src="/_pc/pc.js?v={v}"></script>\n' + html[i:]
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
        bare = self.path.split("#")[0].split("?")[0]
        if bare == "/":
            self.send_response(302)
            self.send_header("Location", "/pitch-cards")
            self.end_headers()
            return
        if bare.rstrip("/") == "/pitch-cards":
            return self.send(200, "text/html; charset=utf-8", page())
        if bare.startswith("/_pc/") and bare[5:] in OWN:
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
    print("Pitch Cards mock on their page: http://127.0.0.1:%d/pitch-cards  (Ctrl+C stops it)" % PORT)
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
