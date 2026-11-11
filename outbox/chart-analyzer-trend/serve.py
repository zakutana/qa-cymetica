"""Chart Analyzer on recorded data: http://127.0.0.1:8849/chart-analyzer?contract=...&chain=solana&tf=1d

The page is THEIR live /chart-analyzer, read anonymously (GET, no cookies, no key) and cached for 60 seconds. Their
live socket is replaced inside the page by sock.js, which plays recorded frames from fixtures/ (one file per coin and
timeframe). A fixture is recorded through their socket only when it is missing or older than an hour (ten minutes for
a "still collecting" answer), and only once per call: every subscribe may write a row into their public calls ledger.
With `frozen=1` in the page address nothing is asked of their socket at all; a coin with no recording shows as busy.
Three of our files go into the page: sock.js, trend.js and patch.js (plus patch.css). Every other GET is passed to
cymetica.com the same way. Every other method is refused here, before anything leaves this machine.
"""
from __future__ import annotations

import asyncio
import json
import re
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import httpx

HERE = Path(__file__).resolve().parent
FIX = HERE / "fixtures"
PORT = 8849
UPSTREAM = "https://cymetica.com"
WS_URL = "wss://cymetica.com/ws/chart-analyzer"
PAGE = "/chart-analyzer"
SCRIPT = "/static/js/chart-analyzer.js"
HOME = PAGE + "?contract=CARDSccUMFKoPRZxt5vt3ksUbxEFEcnZ3H2pd3dKxYjp&chain=solana&tf=1d"
TTL = 60.0
FIXTURE_TTL = 3600.0     # a recording is replayed for an hour; "still collecting" answers for ten minutes
OWN = {"sock.js": "text/javascript; charset=utf-8", "trend.js": "text/javascript; charset=utf-8",
       "patch.js": "text/javascript; charset=utf-8", "patch.css": "text/css; charset=utf-8"}
DROP = {"content-security-policy", "content-security-policy-report-only", "content-encoding", "content-length",
        "transfer-encoding", "connection", "set-cookie", "strict-transport-security", "cross-origin-opener-policy",
        "cross-origin-resource-policy", "x-frame-options", "cache-control", "pragma", "etag", "last-modified"}
UA = "Mozilla/5.0 (chart analyzer mock)"
MAIN_TAG = re.compile(r'<script src="/static/js/chart-analyzer\.js\?v=[^"]*"[^>]*></script>')

# (theirs, ours), each must occur exactly once in their main script
SOCKET = "new WebSocket((location.protocol === 'https:' ? 'wss://' : 'ws://') + location.host + '/ws/chart-analyzer')"
YOUNG = "if (c === 'TOO_LITTLE_HISTORY' && state.autoDown && lowerTfs().length) {"
EDITS = [
    (SOCKET,
     "new (window.czaMockSocket || WebSocket)((location.protocol === 'https:' ? 'wss://' : 'ws://') + location.host + '/ws/chart-analyzer')"),
    (YOUNG,
     "if (c === 'TOO_LITTLE_HISTORY' && window.czaTrend && window.czaTrend.young && window.czaTrend.young(m, state, render, setTf, showTooLittle)) return;\n    " + YOUNG),
]
_cache: dict[str, tuple[float, tuple]] = {}
_client: httpx.Client | None = None
TRANSIENT = {"COLLECTING", "UPSTREAM_UNAVAILABLE", "BUSY"}     # their answers that pass by themselves
_relay_lock = threading.Lock()
_locks: dict[str, threading.Lock] = {}
_relays = 0


def fetch(path: str) -> tuple[int, str, bytes, dict]:
    """One anonymous GET to their platform; the only HTTP call here that leaves this machine."""
    global _client
    hit = _cache.get(path)
    if hit and time.time() - hit[0] < TTL:
        return hit[1]
    if _client is None:
        _client = httpx.Client(timeout=90, follow_redirects=True, headers={"User-Agent": UA})
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
    """Their page with our stylesheet last in the body and our three scripts just before their main script."""
    status, _, body, _ = fetch(path)
    if status != 200:
        raise RuntimeError(f"{path} -> HTTP {status}")
    html = body.decode("utf-8")
    m = MAIN_TAG.findall(html)
    if len(m) != 1 or "</body>" not in html:
        raise RuntimeError("their page no longer has the tags the patch hangs on")
    v = str(int(time.time()))
    # their scripts are all `defer`, so ours are too: deferred scripts run in document order
    ours = "".join(f'<script src="/_mock/{n}?v={v}" defer></script>\n' for n in ("sock.js", "trend.js", "patch.js"))
    html = html.replace(m[0], ours + m[0], 1)
    return html.replace("</body>", f'<link rel="stylesheet" href="/_mock/patch.css?v={v}">\n</body>', 1).encode("utf-8")


def script(path: str) -> bytes:
    status, _, body, _ = fetch(path)
    if status != 200:
        raise RuntimeError(f"{path} -> HTTP {status}")
    js = body.decode("utf-8")
    for theirs, ours in EDITS:
        if js.count(theirs) != 1:
            raise RuntimeError(f"their script no longer has the line the patch edits: {theirs[:60]}")
        js = js.replace(theirs, ours, 1)
    return js.encode("utf-8")


# ── recorded frames ─────────────────────────────────────────────────────────────────────

def fixture_path(q: dict) -> Path | None:
    tf = (q.get("tf") or q.get("timeframe") or [""])[0]
    contract = (q.get("contract") or [""])[0]
    symbol = (q.get("symbol") or [""])[0]
    if not re.fullmatch(r"[A-Za-z0-9]{1,5}", tf):
        return None
    key = re.sub(r"[^A-Za-z0-9]", "_", contract) if contract else re.sub(r"[^A-Za-z0-9]", "_", symbol.upper())
    if not key:
        return None
    return FIX / f"{key}-{tf}.json"


async def _relay(sub: dict, hold: float = 20.0) -> list:
    """One subscribe on their socket. `hold`: how long to stay connected after a "collecting" answer."""
    import websockets
    frames: list = []
    async with websockets.connect(WS_URL, open_timeout=15, close_timeout=1, user_agent_header=UA) as ws:
        await ws.send(json.dumps(sub))
        t0 = time.time()
        got_analysis = None
        have = set()
        while time.time() - t0 < 40:
            try:
                raw = await asyncio.wait_for(ws.recv(), 2)
            except asyncio.TimeoutError:
                raw = None
            except websockets.ConnectionClosed:      # their side hung up: what arrived so far is the answer
                break
            if raw is not None:
                f = json.loads(raw)
                t = f.get("type")
                if t != "candle":
                    frames.append(f)
                have.add(t)
                if t == "analysis" and got_analysis is None:
                    got_analysis = time.time()
                if t == "error" and f.get("code") == "COLLECTING" and time.time() - t0 < hold:
                    continue                 # their page keeps the socket open here and the answer is pushed later
                if t == "error":
                    await asyncio.sleep(1)
                    break
            elif "error" in have and got_analysis is None and time.time() - t0 >= hold:
                break                        # still collecting: the page shows their collecting card
            if got_analysis is not None and ({"pool", "trends"} <= have or time.time() - got_analysis > 6):
                break
        try:
            await ws.send(json.dumps({"op": "unsubscribe"}))
        except Exception:
            pass
    return frames


def frames_for(q: dict) -> tuple[int, dict]:
    global _relays
    p = fixture_path(q)
    if p is None:
        return 400, {"detail": "need contract+chain+tf or symbol+tf"}
    frozen = (q.get("frozen") or [""])[0] == "1"
    chip = (q.get("chip") or [""])[0] == "1"
    with _relay_lock:                    # one lock per coin and timeframe: a chip lookup never holds up the chart
        lock = _locks.setdefault(str(p), threading.Lock())
    with lock:
        old = json.loads(p.read_text(encoding="utf-8")) if p.exists() else None
        collecting = bool(old) and not any(f.get("type") == "analysis" for f in old["frames"]) and any(
            f.get("type") == "error" and f.get("code") in TRANSIENT for f in old["frames"])
        # a passing answer ("still collecting", "try again shortly") is kept ten minutes for the trend chips and 25 s
        # for the page's own timeframe, which retries every 30 s
        ttl = (600.0 if chip else 25.0) if collecting else FIXTURE_TTL
        if old and (frozen or time.time() - old.get("recorded_at", 0) < ttl):
            return 200, {**old, "source": "fixture"}
        if frozen:                       # frozen never asks their socket, even for a coin with no recording
            return 404, {"detail": "Mock: no recorded frames for this coin and timeframe."}
        contract = (q.get("contract") or [""])[0]
        tf = (q.get("tf") or q.get("timeframe") or [""])[0]
        sub = ({"op": "subscribe", "contract": contract, "chain": (q.get("chain") or [""])[0], "timeframe": tf}
               if contract else {"op": "subscribe", "symbol": (q.get("symbol") or [""])[0].upper(), "timeframe": tf})
        try:
            _relays += 1
            sys.stderr.write("RELAY #%d %s\n" % (_relays, json.dumps(sub)))
            frames = asyncio.run(_relay(sub, 0.0 if chip else 20.0))
            if not any(f.get("type") in ("analysis", "error") for f in frames):
                raise RuntimeError("no analysis or error frame")
            if any(f.get("type") == "analysis" for f in frames):      # collected while we waited: the earlier "collecting" goes
                frames = [f for f in frames if not (f.get("type") == "error" and f.get("code") == "COLLECTING")]
        except Exception as exc:
            sys.stderr.write("relay failed: %r\n" % (exc,))
            if old:
                return 200, {**old, "source": "fixture"}
            return 502, {"detail": "relay failed: %s" % exc}
        out = {"recorded_at": int(time.time()), "source": "relay", "frames": frames}
        FIX.mkdir(exist_ok=True)
        p.write_text(json.dumps(out), encoding="utf-8")
        return 200, out


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
        parts = urlsplit(self.path)
        bare = parts.path.rstrip("/")
        if bare == "":
            self.send_response(302)
            self.send_header("Location", HOME)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        try:
            if bare == PAGE:
                return self.send(200, "text/html; charset=utf-8", page(self.path))
            if bare == SCRIPT:
                return self.send(200, "text/javascript; charset=utf-8", script(self.path))
            if bare == "/_mock/frames":
                code, obj = frames_for(parse_qs(parts.query))
                return self.send(code, "application/json; charset=utf-8", json.dumps(obj).encode("utf-8"))
            if bare.startswith("/_mock/") and bare[7:] in OWN:
                f = HERE / bare[7:]
                return self.send(200, OWN[bare[7:]], f.read_bytes() if f.exists() else b"")
            if bare.startswith("/ws/"):
                return self.send(404, "application/json; charset=utf-8", b'{"detail":"Mock: no live socket in this copy."}')
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
    print("Chart Analyzer, recorded frames: http://127.0.0.1:%d%s  (Ctrl+C stops it)" % (PORT, HOME), flush=True)
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
