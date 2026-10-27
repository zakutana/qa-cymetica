"""A local copy of their Agent Tournaments pages with the v4 changes laid on top.

    python outbox/tournaments-v4/live/serve.py            # http://127.0.0.1:8790/agent-casino

The pages, styles, scripts and data are THEIR live ones, read anonymously (GET, no cookies, no key) and cached for 30
seconds; patch.py changes only what v4 changes. The mirror READS ONLY: every method except GET and HEAD is refused
here, before anything is sent anywhere, because a local copy of a page with approve and seat buttons must never be
able to move money or seats on the real one (tests/repo/test_tournaments_v4_mirror.py).
"""
from __future__ import annotations

import argparse
import re
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
SNAPSHOT = True        # the four pages come from fixtures/ (their old page): the live ones already carry ET-32932's build
OWN_FILES = {"v4.js": "application/javascript; charset=utf-8", "v4.css": "text/css; charset=utf-8"}
# v4 renames it Agent Casino at /agent-casino (the operator, 2026-10-26); their page still lives at /agent-tournaments,
# so a page here is fetched from there, and the old page addresses answer with a permanent redirect, as v4 asks of them
NEW, OLD = "/agent-casino", "/agent-tournaments"
PAGES = (
    (re.compile(r"^/agent-casino/?$"), "lobby"),
    (re.compile(r"^/agent-casino/leaderboard/?$"), "leaderboard"),
    (re.compile(r"^/agent-casino/how/?$"), "how"),
    (re.compile(r"^/agent-casino/table/\d+/?$"), "table"),
)
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
        _client = httpx.Client(timeout=60, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0 (qa-cymetica v4 mirror)"})
    r = _client.get(UPSTREAM + path)
    out = (r.status_code, r.headers.get("content-type", "application/octet-stream"), r.content, dict(r.headers))
    _cache[path] = (time.time(), out)
    return out


class Handler(BaseHTTPRequestHandler):
    server_version = "v4-mirror"

    def log_message(self, fmt, *args):  # quiet: one line per page, not per asset
        if self.path.startswith((NEW, OLD)):
            sys.stderr.write(f"{self.command} {self.path}\n")

    def _refuse(self):
        body = b'{"detail":"read-only local copy of the Agent Tournaments pages: nothing is sent to cymetica.com"}'
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
        if path.startswith("/__v4/"):
            name = path[len("/__v4/"):].split("?")[0]
            if name in OWN_FILES:
                return self._send(200, OWN_FILES[name], (HERE / name).read_bytes(), head=head)
            return self._send(404, "text/plain", b"no", head=head)
        if path == OLD or path.startswith((OLD + "/", OLD + "?", OLD + "#")):
            return self._send(301, "text/plain", b"", {"Location": NEW + path[len(OLD):]}, head=head)
        upstream = OLD + path[len(NEW):] if path == NEW or path.startswith((NEW + "/", NEW + "?")) else path
        # their scripts name the page they run on (?path=/agent-casino, e.g. the Build it Better app stats); their API
        # knows it as /agent-tournaments, and a 404 there makes the widget ask again and again
        upstream = upstream.replace("path=%2Fagent-casino", "path=%2Fagent-tournaments").replace("path=/agent-casino", "path=/agent-tournaments")
        status, ctype, body, headers = fetch_upstream(upstream)
        bare = path.split("?")[0]
        for rx, page in PAGES:
            if rx.match(bare) and status == 200 and "text/html" in ctype:
                if SNAPSHOT:      # their page as it was before v4 (their live one now carries the build of ET-32932)
                    body = (HERE / "fixtures" / f"{'table15' if page == 'table' else page}.html").read_bytes()
                body = patch.patch_html(page, body.decode("utf-8")).encode("utf-8")
                break
        self._send(status, ctype, body, headers, head=head)

    def do_GET(self):
        self._get(False)

    def do_HEAD(self):
        self._get(True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8790)
    ap.add_argument("--live", action="store_true", help="patch their live pages instead of the saved pre-v4 snapshots")
    args = ap.parse_args()
    global SNAPSHOT
    SNAPSHOT = not args.live
    port = args.port
    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"v4 mirror on http://127.0.0.1:{port}/agent-casino  (reads cymetica.com, never writes)", flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
