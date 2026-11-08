"""FOMO Radar redesign mock: python outbox/fomo-radar-redesign/serve.py [--quiet]   ->  http://127.0.0.1:8846/

Serves this folder with Cache-Control: no-store, and answers /api/v1/clones/fomo-radar/* with THEIR live data:
one anonymous GET to cymetica.com per endpoint, cached for 20 s (the backtest for 10 min, with a short timeout, because
it hangs a minute and then answers 503). Every other method is refused: nothing is sent from a copy.
index.html is built by build.py from their live page (header, chat bar) with our page in its place.
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
PORT = 8846
UPSTREAM = "https://cymetica.com"
API = "/api/v1/clones/fomo-radar/"
TYPES = {".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8", ".js": "text/javascript; charset=utf-8",
         ".json": "application/json; charset=utf-8", ".svg": "image/svg+xml", ".png": "image/png", ".webp": "image/webp"}
QUIET = "--quiet" in sys.argv
# --snap: answer from snapshot/ (their API read 2026-11-08 19:18 UTC, 221 tokens, window 67 min) where a file exists,
# for pictures that do not depend on the moment; port 8847 so the live preview keeps running
SNAP = HERE / "snapshot" if "--snap" in sys.argv else None
if SNAP:
    PORT = 8847
FLAG = {"hot": "hot", "fresh": "fresh", "exits": "exit_signal"}


def snapshot(path: str) -> bytes | None:
    from urllib.parse import parse_qs, urlsplit
    import json
    u = urlsplit(path)
    q = {k: v[0] for k, v in parse_qs(u.query).items()}
    name = u.path[len(API):].strip("/")
    f = SNAP / (f"{name}-{q['chain']}.json" if "chain" in q else f"{name}.json")
    if not f.is_file():
        return None
    if name != "signals" or q.get("filter", "all") == "all":
        return f.read_bytes()
    d = json.loads(f.read_text(encoding="utf-8"))
    d["rows"] = [r for r in d["rows"] if r.get(FLAG.get(q["filter"], ""))]
    d["filter"], d["count"] = q["filter"], len(d["rows"])
    return json.dumps(d).encode()


_cache: dict[str, tuple[float, int, bytes]] = {}
_lock = threading.Lock()


def upstream(path: str) -> tuple[int, bytes]:
    slow = path.startswith(API + "backtest")
    ttl, timeout = (600, 12) if slow else (20, 40)
    with _lock:
        hit = _cache.get(path)
    if hit and time.time() - hit[0] < ttl:
        return hit[1], hit[2]
    req = urllib.request.Request(UPSTREAM + path, headers={"User-Agent": "Mozilla/5.0 (qa-cymetica fomo mock)",
                                                           "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            out = (r.status, r.read())
    except urllib.error.HTTPError as e:
        out = (e.code, e.read() or b"{}")
    except Exception:  # noqa: BLE001 - a timeout is an answer too: the page shows their own 'unavailable' state
        out = (504, b'{"error":"upstream timeout"}')
    if out[0] == 200 or not hit:
        with _lock:
            _cache[path] = (time.time(), *out)
        return out
    return hit[1], hit[2]  # keep the last good answer over a failure


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        if not QUIET:
            sys.stderr.write(fmt % args + "\n")

    def _send(self, status: int, ctype: str, body: bytes, head: bool = False):
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if not head:
            self.wfile.write(body)

    def do_GET(self, head: bool = False):
        path = self.path
        if path.startswith(API):
            snap = snapshot(path) if SNAP else None
            status, body = (200, snap) if snap is not None else upstream(path)
            return self._send(status, "application/json; charset=utf-8", body, head)
        bare = path.split("?")[0].split("#")[0]
        rel = "index.html" if bare in ("/", "") else bare.lstrip("/")
        f = (HERE / rel).resolve()
        if HERE not in f.parents and f != HERE or not f.is_file():
            return self._send(404, "text/plain; charset=utf-8", b"not found", head)
        return self._send(200, TYPES.get(f.suffix, "application/octet-stream"), f.read_bytes(), head)

    def do_HEAD(self):
        self.do_GET(head=True)

    def refuse(self):
        self._send(405, "text/plain; charset=utf-8", b"a copy sends nothing")

    do_POST = do_PUT = do_PATCH = do_DELETE = refuse


if __name__ == "__main__":
    try:
        server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    except OSError as e:
        sys.exit(f"port {PORT} is taken: {e}")
    print(f"http://127.0.0.1:{PORT}/", flush=True)
    server.serve_forever()
