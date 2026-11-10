"""A local copy of their Promo Market with the v4 changes on it, in TWO windows over one sample:

    python outbox/promo-market-v4/live/serve.py
        the brief's owner      http://127.0.0.1:8792/expire76#me/products
        the promoter           http://127.0.0.1:8808/promoter#me/today    (a stranger: /promo-market on either)

The pages, styles, scripts and data are THEIR live ones, read anonymously (GET, no cookies, no key) and cached for 30
seconds; patch.py changes only what v4 changes. The sample (sample.py) is the one place the mock keeps state, so what
the owner does in one window is what the promoter sees in the other, by itself: each window polls /__v4/state and
reads again when the other one wrote. The window you are in is the port you opened: the owner's reads on 8792, the
promoter's on 8808.

Nothing leaves this machine except those GETs. The writes the workflow needs (post a brief, add funds, take a brief,
send an amount, accept it or not, pass, register a post, approve, cancel) are answered HERE and change the sample only; every other write is
refused before anything is sent anywhere, because a copy of a page with Pay and Post the brief buttons must never be
able to move money or post a brief on the real one (tests/self/test_promo_market_v4_mirror.py).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs

import httpx

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import patch  # noqa: E402
import sample  # noqa: E402

UPSTREAM = "https://cymetica.com"
TTL = 30.0
OWN_FILES = {"v4.css": "text/css; charset=utf-8"}
PAGES = {"/expire76": ("/expire76", "owner"), "/promoter": ("/creator-dashboard", "promoter"), "/promo-market": ("/creator-dashboard", "market")}
SCRIPT = "/static/js/promo_market_v2.js"
APP_PAGE = "/api/v1/creator/app-page"
DROP = {"content-security-policy", "content-security-policy-report-only", "content-encoding", "content-length",
        "transfer-encoding", "connection", "set-cookie", "strict-transport-security", "cross-origin-opener-policy",
        "cross-origin-resource-policy", "x-frame-options", "cache-control", "pragma", "etag", "last-modified"}
_cache: dict[str, tuple[float, tuple]] = {}
_client: httpx.Client | None = None
M = sample.MARKET

BRIEF = r"/api/v1/promo/briefs"
ROUTES = (    # (method, path, who may, handler(body, *ids))
    ("POST", re.compile(rf"^{BRIEF}$"), "owner", lambda b: {"brief": M.create_brief(b)}),
    ("POST", re.compile(rf"^{BRIEF}/(\d+)/offer/take$"), "promoter", lambda b, i: M.take(b.get("handle", ""))),
    ("POST", re.compile(rf"^{BRIEF}/(\d+)/offers/(\d+)$"), "owner", lambda b, i, o: M.decide(int(o), b.get("decision"), b.get("amount"))),
    ("POST", re.compile(rf"^{BRIEF}/(\d+)/offers/(\d+)/accept$"), "promoter", lambda b, i, o: M.accept(int(o))),
    ("POST", re.compile(rf"^{BRIEF}/(\d+)/offers/(\d+)/pass$"), "promoter", lambda b, i, o: M.give_up(int(o))),
    ("POST", re.compile(rf"^{BRIEF}/(\d+)/offers/(\d+)/pay$"), "owner", lambda b, i, o: M.pay(int(o))),
    ("POST", re.compile(rf"^{BRIEF}/(\d+)/posts$"), "promoter", lambda b, i: M.register_post(b.get("url", ""))),
    ("PATCH", re.compile(rf"^{BRIEF}/(\d+)$"), "owner", lambda b, i: _brief_act(b)),
    ("POST", re.compile(r"^/api/v1/promo/uploads$"), "owner", lambda b: {"file_id": 1, "url": sample.PREVIEW}),
    ("POST", re.compile(r"^/__v4/skip$"), None, lambda b: M.skip(b.get("days", 1)) or {"offset": M.offset}),
    ("POST", re.compile(r"^/__v4/reset$"), None, lambda b: M.reset() or {}),
    ("POST", re.compile(r"^/__v4/seed$"), None, lambda b: M.seed(b.get("stage", "open")) or {}),
)


def _brief_act(b: dict):
    if b.get("action") == "cancel":
        return M.cancel()
    if b.get("action") == "add_budget":
        return M.add_budget(b.get("amount") or b.get("amount_usdc"))
    raise sample.Refused(422, "The mock cancels a brief and adds funds to it; nothing else.")


def state(role: str, since: int) -> dict:
    """What a window polls: the mock's day, a counter that goes up with every write (read again when it moved), and
    what happened for this side since the last one it saw (the pop-up)."""
    with M.lock:
        return {"offset": M.offset, "ver": M.ver, "last": len(M.news), "news": [n for n in M.news if n["to"] == role and n["n"] > since]}


def fetch_upstream(path: str) -> tuple[int, str, bytes, dict]:
    """One anonymous GET to their platform; the only call here that leaves this machine."""
    hit = _cache.get(path)
    if not hit:
        return _read(path)
    if time.time() - hit[0] >= TTL and path not in _busy:
        # their answer from a moment ago is shown at once and read again behind it: when their server takes ten
        # seconds over a read, the two windows must not stand still for it
        _busy.add(path)
        threading.Thread(target=_again, args=(path,), daemon=True).start()
    return hit[1]


_busy: set[str] = set()


def _again(path: str):
    try:
        _read(path)
    except httpx.HTTPError:
        pass
    finally:
        _busy.discard(path)


def _read(path: str) -> tuple[int, str, bytes, dict]:
    global _client
    if _client is None:      # built on first use, so importing this module (the tests do) opens nothing
        _client = httpx.Client(timeout=60, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0 (qa-cymetica v4 mirror)"})
    r = _client.get(UPSTREAM + path)
    out = (r.status_code, r.headers.get("content-type", "application/octet-stream"), r.content, dict(r.headers))
    was = _cache.get(path)
    if r.status_code < 500 or not was:      # a 5xx of theirs does not replace a page that was read well
        _cache[path] = (time.time(), out)
    return out


class Handler(BaseHTTPRequestHandler):
    server_version = "v4-mirror"

    def log_message(self, fmt, *args):  # quiet: one line per page, not per asset
        if self.path.split("?")[0] in PAGES:
            sys.stderr.write(f"{self.command} {self.path}\n")

    @property
    def role(self) -> str:
        return getattr(self.server, "role", "owner")

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

    def _json(self, obj, head: bool = False, status: int = 200):
        return self._send(status, "application/json", json.dumps(obj, default=str).encode("utf-8"), head=head)

    # ---- writes: the workflow is answered here, anything else is refused ----------------------------------------------
    def _write(self):
        bare = self.path.split("?")[0]
        n = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(n) if n else b""
        for method, rx, who, fn in ROUTES:
            m = rx.match(bare)
            if method != self.command or not m:
                continue
            if who and who != self.role:
                return self._json({"detail": f"Only the {who} can do this."}, status=403)
            try:
                body = json.loads(raw) if raw[:1] in (b"{", b"[") else {}
                out = fn(body, *m.groups())
                M.ver += 1          # the other window reads again
                return self._json(out)
            except sample.Refused as e:
                return self._json({"detail": e.detail}, status=e.code)
        body = b'{"detail":"Local copy: nothing is sent to cymetica.com from here."}'
        self.send_response(405)
        self.send_header("Allow", "GET, HEAD")
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    do_POST = do_PATCH = do_PUT = do_DELETE = do_OPTIONS = _write

    # ---- reads -------------------------------------------------------------------------------------------------------
    def _get(self, head: bool):
        path = self.path
        bare, _, query = path.split("#")[0].partition("?")
        args = parse_qs(query, keep_blank_values=True)
        if bare == "/__v4/state":
            since = (args.get("since") or ["0"])[0]
            return self._json(state(self.role, int(since) if since.isdigit() else 0), head)
        if bare.startswith("/__v4/"):
            name = bare[len("/__v4/"):]
            if name in OWN_FILES:
                return self._send(200, OWN_FILES[name], (HERE / name).read_bytes(), head=head)
            return self._send(404, "text/plain", b"no", head=head)
        if bare == "/":
            return self._send(302, "text/plain", b"", {"Location": "/expire76" if self.role == "owner" else "/promoter"}, head=head)
        try:
            ours = sample.answer(self.role, bare)
        except sample.Refused as e:
            return self._json({"detail": e.detail}, head, e.code)
        if ours is not None:
            return self._json(ours, head)
        if bare in PAGES:
            upstream, page = PAGES[bare]
            status, ctype, body, headers = fetch_upstream(upstream)
            if status == 200 and "text/html" in ctype:
                try:
                    body = patch.patch_html(page, body.decode("utf-8")).encode("utf-8")
                except patch.AnchorMissing as e:
                    return self._send(500, "text/plain; charset=utf-8", str(e).encode("utf-8"), head=head)
            return self._send(status, ctype, body, headers, head=head)
        # the promoter is a made-up member: the member-only reads that have no sample are read as the operator's page, anonymously
        status, ctype, body, headers = fetch_upstream(path.replace("promoter_demo", "expire76"))
        if bare == "/api/v1/creator/posts" and status != 200:      # a member's read: the made-up member has posted nothing, and Today opens
            return self._json({"posts": [], "daily_cap": 3, "rule": ""}, head)
        if bare == APP_PAGE and status == 200:
            body = json.dumps(sample.fix_copy(json.loads(body), self.role)).encode("utf-8")
        if bare == SCRIPT and status == 200:
            try:
                body = patch.patch_js(body.decode("utf-8")).encode("utf-8")
            except patch.AnchorMissing as e:
                msg = str(e).replace("'", " ")
                body = f"document.body.insertAdjacentHTML('afterbegin', '<pre style=\"position:fixed;z-index:9999;inset:0 0 auto 0;margin:0;background:#000;color:#f44;padding:20px\">{msg}</pre>');".encode()
        self._send(status, ctype, body, headers, head=head)

    def do_GET(self):
        try:
            self._get(False)
        except httpx.HTTPError as e:      # their server did not answer in time: say so, the page reads it again
            self._send(504, "application/json", json.dumps({"detail": f"cymetica.com did not answer: {type(e).__name__}"}).encode("utf-8"))

    def do_HEAD(self):
        self._get(True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--owner-port", type=int, default=8792)
    ap.add_argument("--promoter-port", type=int, default=8808)
    a = ap.parse_args()
    servers = []
    for role, port in (("owner", a.owner_port), ("promoter", a.promoter_port)):
        srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
        srv.role = role
        servers.append(srv)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
    for path in ("/expire76", "/creator-dashboard", SCRIPT, APP_PAGE + "?u=expire76"):      # read once now, so the first click does not wait for them
        _busy.add(path)
        threading.Thread(target=_again, args=(path,), daemon=True).start()
    print(f"Promo Market v4: owner http://127.0.0.1:{a.owner_port}/expire76#me/products · promoter http://127.0.0.1:{a.promoter_port}/promoter#me/today "
          "(reads cymetica.com, never writes)", flush=True)
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
