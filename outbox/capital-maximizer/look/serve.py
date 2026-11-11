"""Capital Maximizer with a look patch on its top 3 cards: http://127.0.0.1:8848/capital-maximizer?tier=og

The page is THEIR live /capital-maximizer, read anonymously (GET, no cookies, no key) and cached for 60 seconds, with
patch.css added and patch.js placed inside their own script, just before it boots: every figure is their engine's,
their functions draw the tree. A few small edits are made to their script on the way through (EDITS below), each one
a fix their tree needs for the look. Every other GET is passed to cymetica.com the same way. Every other method is
refused here, before anything leaves this machine. Their live stream (Server-Sent Events) is left out: it cannot be
proxied here, so the copy shows the figures of the moment it was opened. `?tier=og|high|medium|conservative` opens
the top 3 straight away.
"""
from __future__ import annotations

import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import httpx

HERE = Path(__file__).resolve().parent
PORT = 8848
UPSTREAM = "https://cymetica.com"
PAGE = "/capital-maximizer"
SCRIPT = "/static/js/capital-maximizer.js"
TTL = 60.0
OWN = {"patch.css": "text/css; charset=utf-8"}
DROP = {"content-security-policy", "content-security-policy-report-only", "content-encoding", "content-length",
        "transfer-encoding", "connection", "set-cookie", "strict-transport-security", "cross-origin-opener-policy",
        "cross-origin-resource-policy", "x-frame-options", "cache-control", "pragma", "etag", "last-modified"}
BOOT = "\n  boot(0);"
# (theirs, ours): the borrow node sat under the leverage diamond on a levered pool; the diamond was smaller than its text
EDITS = [
    ("pos[bor.n] = { c: 1, r: pos[col.n].r, side: 'right' };",
     "pos[bor.n] = { c: 1, r: pos[col.n].r + (col === sw ? 1 : 0), side: 'right' };"),
    ("edges.push([sw.n, lev.n]); edges.push([lev.n, bor.n]); edges.push([col.n, bor.n]);",
     "edges.push([sw.n, lev.n]); edges.push([lev.n, bor.n]); if (col !== sw) edges.push([col.n, bor.n]);"),
    ("pos.apex = { c: 0.5, r: spine.length + 1.5 };",
     "pos.apex = col === sw ? { c: 0, r: pos[bor.n].r + 1.2 } : { c: 0.5, r: spine.length + 1.5 };"),
    # a plate was capped at 150 wide and a vault name at 22 letters, so long names ran over the plate or were cut
    ("var pw = Math.max(86, Math.min(150, 12 + 6.1 * Math.max(pt[0].length, pt[1].length)))",
     "var pw = Math.max(86, Math.min(214, 12 + 6.1 * Math.max(pt[0].length, pt[1].length)))"),
    ("String(n.token).slice(0, 22) + ' +' + rateTxt(n.rate), 'earn']",
     "String(n.token).replace(/\\s+\\S*\\d\\S*$/, '').slice(0, 30) + ' +' + rateTxt(n.rate), 'earn']"),
    # a stake step with no rate of its own (the sUSDfr vault) printed "+NaN%"
    ("(n.from ? n.from + ' → ' + n.token + ' ' : 'stake ') + '+' + rateTxt(n.rate), 'earn']",
     "(n.from ? n.from + ' → ' + n.token : 'stake') + (n.rate ? ' +' + rateTxt(n.rate) : ''), n.rate ? 'earn' : '']"),
    ("""'<rect class="dia" x="' + (x - 15) + '" y="' + (y - 15) + '" width="30" height="30" """,
     """'<rect class="dia" x="' + (x - 18) + '" y="' + (y - 18) + '" width="36" height="36" """),
]
_cache: dict[str, tuple[float, tuple]] = {}
_client: httpx.Client | None = None


def fetch(path: str) -> tuple[int, str, bytes, dict]:
    """One anonymous GET to their platform; the only call here that leaves this machine."""
    global _client
    hit = _cache.get(path)
    if hit and time.time() - hit[0] < TTL:
        return hit[1]
    if _client is None:
        _client = httpx.Client(timeout=90, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0 (qa-cymetica capital-maximizer look mock)"})
    for attempt in range(2):
        try:
            r = _client.get(UPSTREAM + path)
        except httpx.HTTPError:
            if attempt == 0:
                continue
            if hit:
                return hit[1]
            raise
        out = (r.status_code, r.headers.get("content-type", "application/octet-stream"), r.content, dict(r.headers))
        if r.status_code == 200:
            _cache[path] = (time.time(), out)
            return out
        if r.status_code not in (502, 503, 504):
            return out
    return hit[1] if hit else out


def page(path: str) -> bytes:
    """Their page, with our stylesheet last in the body and no live stream."""
    status, _, body, _ = fetch(path)
    if status != 200:
        raise RuntimeError(f"{path} -> HTTP {status}")
    html = body.decode("utf-8")
    if "</body>" not in html or "<head>" not in html:
        raise RuntimeError("their page no longer has the tags the patch hangs on")
    v = str(int(time.time()))
    html = html.replace("<head>", "<head><script>window.EventSource = undefined;</script>", 1)
    return html.replace("</body>", f'<link rel="stylesheet" href="/_look/patch.css?v={v}">\n</body>', 1).encode("utf-8")


def script(path: str) -> bytes:
    """Their script with the edits and patch.js inside it, before it boots."""
    status, _, body, _ = fetch(path)
    if status != 200:
        raise RuntimeError(f"{path} -> HTTP {status}")
    js = body.decode("utf-8")
    for theirs, ours in EDITS:
        if js.count(theirs) != 1:
            raise RuntimeError(f"their script no longer has the line the patch edits: {theirs[:60]}")
        js = js.replace(theirs, ours, 1)
    if js.count(BOOT) != 1:
        raise RuntimeError("their script no longer boots where the patch goes in")
    return js.replace(BOOT, "\n" + (HERE / "patch.js").read_text(encoding="utf-8") + BOOT, 1).encode("utf-8")


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
            self.send_header("Location", PAGE + "?tier=og")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        try:
            if bare == PAGE:
                return self.send(200, "text/html; charset=utf-8", page(PAGE))
            if bare == SCRIPT:
                return self.send(200, "text/javascript; charset=utf-8", script(self.path))
            if bare.startswith("/_look/") and bare[7:] in OWN:
                return self.send(200, OWN[bare[7:]], (HERE / bare[7:]).read_bytes())
            if bare.endswith("/stream"):
                return self.send(404, "application/json; charset=utf-8", b'{"detail":"Mock: no live stream in this copy."}')
            status, ctype, body, headers = fetch(self.path)
        except (httpx.HTTPError, RuntimeError) as exc:
            return self.send(502, "text/plain; charset=utf-8", f"The copy could not read their page: {exc}".encode("utf-8"))
        return self.send(status, ctype, body, headers)

    do_HEAD = do_GET

    def refuse(self):
        self.send(403, "application/json; charset=utf-8", b'{"detail":"Mock: nothing is sent from this copy."}')

    do_POST = do_PUT = do_PATCH = do_DELETE = refuse

    def log_message(self, fmt, *args):
        if "--quiet" not in sys.argv:
            sys.stderr.write("%s %s\n" % (self.command, self.path[:120]))


if __name__ == "__main__":
    print("Capital Maximizer, look patch: http://127.0.0.1:%d%s?tier=og  (Ctrl+C stops it)" % (PORT, PAGE))
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
