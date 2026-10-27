"""A local copy of their Promo Market v2 with the v3 changes laid on top.

    python outbox/promo-market-v3/live/serve.py       # http://127.0.0.1:8792/expire76#new  and  /promo-market

The pages, styles, scripts and data are THEIR live ones, read anonymously (GET, no cookies, no key) and cached for 30
seconds; patch.py changes only what v3 changes. The owner's own read (/api/v1/promo/mine, which needs a sign-in) is
served from fixtures/mine.json, read from the operator's signed-in browser on 2026-10-27. The mirror READS ONLY:
every method except GET and HEAD is refused here, before anything is sent anywhere, because a copy of a page with
Post the brief and Pay buttons must never be able to post a brief or move money on the real one
(tests/repo/test_promo_market_v3_mirror.py).
"""
from __future__ import annotations

import argparse
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import httpx

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import patch  # noqa: E402

UPSTREAM = "https://cymetica.com"
TTL = 30.0
OWN_FILES = {"v3.css": "text/css; charset=utf-8"}
# /promo-market is the product's own address (the operator, 2026-10-27); their page for a stranger is /creator-dashboard
PAGES = {"/expire76": ("/expire76", "owner"), "/promo-market": ("/creator-dashboard", "market")}
FIXTURES = {"/api/v1/promo/mine": HERE / "fixtures" / "mine.json"}
SCRIPT = "/static/js/promo_market_v2.js"
DROP = {"content-security-policy", "content-security-policy-report-only", "content-encoding", "content-length",
        "transfer-encoding", "connection", "set-cookie", "strict-transport-security", "cross-origin-opener-policy",
        "cross-origin-resource-policy", "x-frame-options", "cache-control", "pragma", "etag", "last-modified"}
_cache: dict[str, tuple[float, tuple]] = {}
_client: httpx.Client | None = None


def fetch_upstream(path: str) -> tuple[int, str, bytes, dict]:
    """One anonymous GET to their platform; the only call here that leaves this machine."""
    global _client
    hit = _cache.get(path)
    if hit and time.time() - hit[0] < TTL:
        return hit[1]
    if _client is None:      # built on first use, so importing this module (the tests do) opens nothing
        _client = httpx.Client(timeout=60, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0 (qa-cymetica v3 mirror)"})
    r = _client.get(UPSTREAM + path)
    out = (r.status_code, r.headers.get("content-type", "application/octet-stream"), r.content, dict(r.headers))
    _cache[path] = (time.time(), out)
    return out


class Handler(BaseHTTPRequestHandler):
    server_version = "v3-mirror"

    def log_message(self, fmt, *args):  # quiet: one line per page, not per asset
        if self.path.split("?")[0] in PAGES:
            sys.stderr.write(f"{self.command} {self.path}\n")

    def _refuse(self):
        body = b'{"detail":"Local copy: nothing is sent to cymetica.com from here."}'
        self.send_response(405)
        self.send_header("Allow", "GET, HEAD")
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    do_POST = do_PUT = do_DELETE = do_PATCH = do_OPTIONS = _refuse

    def _send(self, status: int, ctype: str, body: bytes, headers: dict | None = None, head: bool = False):
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for k, v in (headers or {}).items():
            if k.lower() not in DROP and k.lower() != "content-type":
                self.send_header(k, v)
        self.end_headers()
        if not head:
            self.wfile.write(body)

    def _get(self, head: bool):
        path = self.path
        bare = path.split("?")[0].split("#")[0]
        if path.startswith("/__v3/"):
            name = bare[len("/__v3/"):]
            if name in OWN_FILES:
                return self._send(200, OWN_FILES[name], (HERE / name).read_bytes(), head=head)
            return self._send(404, "text/plain", b"no", head=head)
        if bare == "/":
            return self._send(302, "text/plain", b"", {"Location": "/promo-market"}, head=head)
        if bare in FIXTURES:
            return self._send(200, "application/json", FIXTURES[bare].read_bytes(), head=head)
        if bare in PAGES:
            upstream, page = PAGES[bare]
            status, ctype, body, headers = fetch_upstream(upstream + path[len(bare):])
            if status == 200 and "text/html" in ctype:
                try:
                    body = patch.patch_html(page, body.decode("utf-8")).encode("utf-8")
                except patch.AnchorMissing as e:
                    return self._send(500, "text/plain; charset=utf-8", str(e).encode("utf-8"), head=head)
            return self._send(status, ctype, body, headers, head=head)
        status, ctype, body, headers = fetch_upstream(path)
        if bare == SCRIPT and status == 200:
            try:
                body = patch.patch_js(body.decode("utf-8")).encode("utf-8")
            except patch.AnchorMissing as e:
                msg = str(e).replace("'", " ")
                body = f"document.body.insertAdjacentHTML('afterbegin', '<pre style=\"position:fixed;z-index:9999;inset:0 0 auto 0;margin:0;background:#000;color:#f44;padding:20px\">{msg}</pre>');".encode()
        self._send(status, ctype, body, headers, head=head)

    def do_GET(self):
        self._get(False)

    def do_HEAD(self):
        self._get(True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8792)
    port = ap.parse_args().port
    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"Promo Market v3 on http://127.0.0.1:{port}/expire76#new and /promo-market  (reads cymetica.com, never writes)", flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
