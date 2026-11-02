"""The Gem Screener and Supply Analyzer with this request on them: http://127.0.0.1:8804/gem-screener/app

Their live pages, read anonymously (GET, no cookies, no key) and cached for 60 seconds. data.json holds what the Supply Analyzer
would read from the other sources; overlay() lays it on their batch, so the column, the card, the panel and the gate all read it the
way the build would. patch.js goes inside their page script. Every other GET passes through; every other method is refused here.
"""
from __future__ import annotations

import json
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import httpx

HERE = Path(__file__).resolve().parent
PORT = 8804
UPSTREAM = "https://cymetica.com"
TTL = 60.0
GO = "/* ================= go ================= */"
DATA = json.loads((HERE / "data.json").read_text(encoding="utf-8"))
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
        _client = httpx.Client(timeout=120, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0 (qa-cymetica supply-analyzer-sources mock)"})
    r = _client.get(UPSTREAM + path)
    out = (r.status_code, r.headers.get("content-type", "application/octet-stream"), r.content, dict(r.headers))
    if r.status_code == 200:
        _cache[path] = (time.time(), out)
    return out


def overlay_row(row: dict) -> None:
    """One batch or analyze record, as the Supply Analyzer would hold it with the other sources."""
    token = row.get("token") or {}
    slug = token.get("slug") or (token.get("gem_screener") or {}).get("slug")
    tiles = row.get("tiles")
    if not slug or not isinstance(tiles, dict):
        return
    found = DATA["sources"].get(slug)
    if found:
        circ = row.get("circulating") or 1
        nxt = found["next"]
        tiles["dilution_12m"] = {"pct": found["pct"], "net_of_buybacks_pct": None, "new_tokens_12m": found["new_tokens_12m"], "month_tokens": found["month_tokens"],
                                 "kinds": found["kinds"], "schedule_known": True, "emissions_known": False, "tone": "red", "source": found["source"], "until": found["until"]}
        tiles["next_unlock_row"] = {"kind": "scheduled", "ts": nxt["ts"], "tokens": nxt["tokens"], "pct_of_circulating": round(100 * nxt["tokens"] / circ, 2),
                                    "recipients": nxt["recipients"], "source": found["source"]}
        row["dilution_12m_pct"] = found["pct"]
        return
    if (tiles.get("dilution_12m") or {}).get("pct") is not None:
        return
    circ, top = row.get("circulating"), row.get("max_supply")
    if circ and top and (top - circ) / circ < 0.01:
        tiles["dilution_12m"] = {"pct": 0.0, "new_tokens_12m": 0, "month_tokens": 0, "kinds": [], "at_max": True, "tone": "green"}
        tiles["next_unlock_row"] = {"kind": "none_scheduled", "text": "Max supply is reached", "at_max": True}


def supply_json(path: str, body: bytes) -> bytes:
    payload = json.loads(body)
    for row in payload.get("items", [payload]) if isinstance(payload, dict) else []:
        if isinstance(row, dict):
            overlay_row(row)
    return json.dumps(payload).encode("utf-8")


def page(path: str) -> bytes:
    """Their app page, our changes inside its script, no socket: a push can't be proxied here, and the page then hides its Live label."""
    status, _, body, _ = fetch(path)
    if status != 200:
        raise RuntimeError(f"{path} -> HTTP {status}")
    html = body.decode("utf-8")
    v = str(int(time.time()))
    html = html.replace("<head>", "<head><script>window.WebSocket = undefined;</script>", 1)
    html = html.replace("</head>", f'<link rel="stylesheet" href="/_sa/patch.css?v={v}">\n</head>', 1)
    code = "var SA_MOCK = " + json.dumps(DATA) + ";\n" + (HERE / "patch.js").read_text(encoding="utf-8")
    return html.replace(GO, code + "\n" + GO, 1).encode("utf-8")


def supply_page(path: str) -> bytes:
    """Their Supply Analyzer page, with our data and stylesheet; its script comes through supply_script()."""
    status, _, body, _ = fetch(path)
    if status != 200:
        raise RuntimeError(f"{path} -> HTTP {status}")
    v = str(int(time.time()))
    head = f'<script>window.SA_MOCK = {json.dumps(DATA)};</script><link rel="stylesheet" href="/_sa/patch.css?v={v}">\n</head>'
    return body.decode("utf-8").replace("</head>", head, 1).encode("utf-8")


def supply_script(path: str) -> bytes:
    """Their page script with patch_page.js inside it, before its first read."""
    status, _, body, _ = fetch(path)
    if status != 200:
        raise RuntimeError(f"{path} -> HTTP {status}")
    js = body.decode("utf-8")
    at = js.rindex("boot();")
    return (js[:at] + (HERE / "patch_page.js").read_text(encoding="utf-8") + "\n  " + js[at:]).encode("utf-8")


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
        bare = urlparse(self.path).path.rstrip("/")
        if bare == "":
            self.send_response(302)
            self.send_header("Location", "/gem-screener/app")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        if bare == "/gem-screener/app":
            return self.send(200, "text/html; charset=utf-8", page(self.path))
        if bare == "/supply-analyzer":
            return self.send(200, "text/html; charset=utf-8", supply_page(self.path))
        if bare == "/static/js/supply-analyzer.js":
            return self.send(200, "text/javascript; charset=utf-8", supply_script(self.path))
        if bare.startswith("/_sa/") and bare[5:] in OWN:
            return self.send(200, OWN[bare[5:]], (HERE / bare[5:]).read_bytes())
        status, ctype, body, headers = fetch(self.path)
        if status == 200 and bare in ("/api/v1/supply-analyzer/batch/gem-screener", "/api/v1/supply-analyzer/analyze"):
            body = supply_json(self.path, body)
        return self.send(status, ctype, body, headers)

    do_HEAD = do_GET

    def refuse(self):
        self.send(403, "application/json; charset=utf-8", b'{"detail":"Mock: nothing is sent from this copy."}')

    do_POST = do_PUT = do_PATCH = do_DELETE = refuse

    def log_message(self, fmt, *args):
        if "--quiet" not in sys.argv:
            sys.stderr.write("%s %s\n" % (self.command, self.path[:120]))


if __name__ == "__main__":
    print("Supply Analyzer request, local copy: http://127.0.0.1:%d/gem-screener/app  (Ctrl+C stops it)" % PORT)
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
