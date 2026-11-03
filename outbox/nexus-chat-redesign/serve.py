"""The new NEXUS chat on their own pages: http://127.0.0.1:8830/gem-screener

Any page is THEIR live page, read anonymously (GET, no cookies, no key), with nexus-chat.css swapped for ours and
nexus-chat.js patched: their own script (live/nexus-chat.js, v=20261027-1) with DESIGN below applied, so every function
in it is theirs by construction. A patch that no longer matches raises at start.

Nothing is sent to Cymetica from here. Every POST, PUT, PATCH and DELETE stays on this machine: the chat, upload,
subscription and exchange endpoints are answered locally with scripted replies (a real /api/v1/chat/stream is billed per
message), bodies are read and dropped, and anything else is refused. Figures in the demo reply are read live from
/api/v1/gem-screener/ranked.
"""
from __future__ import annotations

import json
import re
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import httpx

HERE = Path(__file__).resolve().parent
PORT = 8830
UPSTREAM = "https://cymetica.com"
TTL = 900.0
DROP = {"content-security-policy", "content-security-policy-report-only", "content-encoding", "content-length",
        "transfer-encoding", "connection", "set-cookie", "strict-transport-security", "cross-origin-opener-policy",
        "cross-origin-resource-policy", "x-frame-options", "cache-control", "pragma", "etag", "last-modified"}
OWN = {"nexus-chat.css": "text/css; charset=utf-8", "demo.js": "text/javascript; charset=utf-8"}

MARK = ('<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M6.8 17.4V6.6L17.2 17.4V6.6" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/></svg>')
WELCOME = (f'<div class="nexus-welcome"><span class="nx-logo nx-logo-hero">{MARK}</span>'
           '<strong>Ask NEXUS anything</strong>'
           '<span>Type, attach a file or point at anything on this page.</span></div>')

# What would ship: the design. Each entry is (their text, ours), and must match exactly once unless a count is given.
DESIGN = [
    # no enable switch; the first message already turns Nexus on (Be: C||await Ye(!0))
    ('g="*Enable Nexus AI using the toggle to start chatting.*"', 'g="*Please send your message again.*"'),
    ('e.placeholder=window.innerWidth<=480?"Ask (per-use)…":"Ask anything… (per-use billing applies)"', 'e.placeholder="Ask anything..."'),
    # Select on page: once page-context is mounted its own listener toggles, and this one toggled back (live: on, off at once)
    ('a&&a.addEventListener("click",function(e){e.preventDefault(),e.stopPropagation(),z().then(function(e){e&&e.toggleSelectionMode()})})',
     'a&&a.addEventListener("click",function(e){e.preventDefault(),e.stopPropagation(),a.__nexusCtxBound||z().then(function(e){e&&e.toggleSelectionMode()})})'),
    # Send stays idle while there is nothing to send
    ('n&&(n.disabled=!1)', 'n&&(n.disabled=!e.value.trim()&&!E.length)', 2),
    # the welcome after New Chat
    ('n.innerHTML=\'<div class="nexus-welcome"><strong>EventTrader NEXUS AI</strong></div>\'', "n.innerHTML=" + json.dumps(WELCOME)),
    # the panel stays open while you read the page; Esc and the X close it
    ('document.addEventListener("click",function(e){y&&(w||o.contains(e.target)||G())}),', ''),
    # the menu, and a toast instead of feedback hidden in a tooltip
    ('function T(){try{return localStorage',
     'function nxMenu(){var b=o.querySelector(".nx-more"),m=o.querySelector(".nx-menu");function s(v){m.hidden=!v,b.setAttribute("aria-expanded",v?"true":"false")}'
     'b.addEventListener("click",function(e){e.stopPropagation(),s(m.hidden)}),document.addEventListener("click",function(e){m.hidden||m.contains(e.target)||b.contains(e.target)||s(!1)}),'
     'm.addEventListener("click",function(e){e.target.closest(".nx-mi")&&s(!1)}),document.addEventListener("keydown",function(e){"Escape"!==e.key||m.hidden||(e.stopPropagation(),s(!1))},!0);'
     'if("1"===r("nexus_panel_max")){o.classList.add("nx-max");var x=o.querySelector(".nexus-btn-maximize");x.title="Restore",x.querySelector("span").textContent="Restore"}}'
     # pointer capture: the window follows the cursor over anything, iframes included, and always lets go
     'function nxResize(){var p=o.querySelector(".nexus-panel"),c=function(v,a,b){return Math.max(a,Math.min(v,b))};'
     'o.querySelectorAll(".nexus-resize-handle,.nx-rz").forEach(function(h){var on=!1,sx=0,sy=0,sw=0,sh=0,ax="1"===h.dataset.x,ay="1"===h.dataset.y;'
     'h.addEventListener("pointerdown",function(e){if(0===e.button){e.preventDefault(),e.stopPropagation();'
     'if(!w&&o.classList.contains("nx-max")){var q=p.getBoundingClientRect(),m=o.querySelector(".nexus-btn-maximize");p.style.width=q.width+"px",p.style.height=q.height+"px",o.classList.remove("nx-max"),localStorage.setItem("nexus_panel_max","0"),m.title="Maximize",m.querySelector("span").textContent="Maximize"}'
     'on=!0,sx=e.clientX,sy=e.clientY,sw=w?o.offsetWidth:p.offsetWidth,sh=p.offsetHeight;try{h.setPointerCapture(e.pointerId)}catch(e){}'
     'o.classList.add("nx-resizing"),document.documentElement.classList.add("nx-resizing-doc")}});'
     'h.addEventListener("pointermove",function(e){if(on){var dx=e.clientX-sx,dy=e.clientY-sy;'
     'if(w){var t=Math.round(c("left"===S?sw+dx:sw-dx,320,.5*window.innerWidth));o.style.width=t+"px","left"===S?document.body.style.marginLeft=t+"px":document.body.style.marginRight=t+"px"}'
     'else{ax&&(p.style.width=Math.round(c(sw-dx,360,window.innerWidth-48))+"px"),ay&&(p.style.height=Math.round(c(sh-dy,360,window.innerHeight-48))+"px")}}});'
     'var end=function(){if(on){on=!1,o.classList.remove("nx-resizing"),document.documentElement.classList.remove("nx-resizing-doc");'
     'w?localStorage.setItem("nexus_pinned_width",o.style.width):(localStorage.setItem("nexus_panel_height",p.style.height),localStorage.setItem("nexus_panel_width",p.style.width))}};'
     'h.addEventListener("pointerup",end),h.addEventListener("pointercancel",end),h.addEventListener("lostpointercapture",end)})}'
     'function nxToast(t){var e=o&&o.querySelector(".nexus-panel");if(e){var n=e.querySelector(".nx-toast");n||((n=document.createElement("div")).className="nx-toast",n.setAttribute("role","status"),e.appendChild(n)),'
     'n.textContent=t,n.classList.add("nx-on"),clearTimeout(n._t),n._t=setTimeout(function(){n.classList.remove("nx-on")},2600)}}'
     'function T(){try{return localStorage'),
    ('document.body.appendChild(o),e=function(){', 'document.body.appendChild(o),nxMenu(),e=function(){'),
    ('e.setAttribute("title",t),e.classList.toggle("nexus-share-ok"', 'e.setAttribute("title",t),nxToast(t),e.classList.toggle("nexus-share-ok"'),
    # Pin keeps its three steps (right, left, off); it now labels a menu row instead of a glyph
    ('e&&(e.textContent="right"===S?"⊟→":"⊟←",e.title="right"===S?"Move to left side":"Unpin sidebar")',
     'e&&(e.title="right"===S?"Move to left side":"Unpin sidebar",e.querySelector("span").textContent=e.title)'),
    ('e&&(e.textContent="⊞",e.title="Pin as sidebar")', 'e&&(e.title="Pin as sidebar",e.querySelector("span").textContent=e.title)'),
    # Maximize: a large window; pinned, a wider rail, as today
    ('var e=parseInt(o.style.width||"380",10);return o.style.width=e>=550?"380px":"600px",void(O.title=e>=550?"Maximize":"Restore")',
     'var e=parseInt(o.style.width||"420",10);return o.style.width=e>=550?"420px":"600px",O.title=e>=550?"Maximize":"Restore",void(O.querySelector("span").textContent=O.title)'),
    ('var t="80vh"===n.style.height;n.style.height=t?"400px":"80vh",O.title=t?"Maximize":"Restore",localStorage.setItem("nexus_panel_height",n.style.height)',
     'var t=o.classList.toggle("nx-max");n.style.height="",n.style.width="",O.title=t?"Restore":"Maximize",O.querySelector("span").textContent=O.title,localStorage.removeItem("nexus_panel_height"),localStorage.removeItem("nexus_panel_width"),localStorage.setItem("nexus_panel_max",t?"1":"0")'),
    # resizing is rewritten in nxResize (their mouse and touch block is cut in patched_js)
    ('var r=localStorage.getItem("nexus_panel_height");r&&(s.style.height=r)', 'var r=localStorage.getItem("nexus_panel_height");r&&(s.style.height=r);var nw=localStorage.getItem("nexus_panel_width");s.style.width=nw||""'),
    ('if(e&&(e.style.height=""),w)return', 'if(e&&(e.style.height="",e.style.width=""),w)return'),
    # the composer grows further
    ('Math.min(u.scrollHeight,96)', 'Math.min(u.scrollHeight,168)'),
    # the cost line, warnings and "degraded" badge stay after the stream closes (today the final render wipes them)
    ('function ke(e,n){e.innerHTML=Le(n),_e(e,n),function(e,n){',
     'function ke(e,n){var nk=[].slice.call(e.querySelectorAll(".nexus-msg-cost,.nexus-billing-warning,.nexus-degraded-badge"));e.innerHTML=Le(n),_e(e,n),nk.forEach(function(x){x.classList.contains("nexus-degraded-badge")?e.insertBefore(x,e.firstChild):e.appendChild(x)}),function(e,n){'),
    ('function we(e,n){var t=e.querySelector(".nexus-thinking");t&&t.remove(),e.innerHTML=Le(n)+\'<span class="nexus-cursor"></span>\',y&&Ee()}',
     'function we(e,n){var t=e.querySelector(".nexus-thinking");t&&t.remove();var nk=e.querySelector(".nexus-degraded-badge");e.innerHTML=Le(n)+\'<span class="nexus-cursor"></span>\',nk&&e.insertBefore(nk,e.firstChild),y&&Ee()}'),
    # an inline second click instead of the browser's confirm box
    ('if(!ne&&confirm("Cancel your NEXUS Premium subscription? Access continues until the end of your current period.")){ne=!0;var e=o.querySelector("#nexus-w-cancel-btn");',
     'var e=o.querySelector("#nexus-w-cancel-btn");if(e&&!e._nxArmed)return e._nxArmed=!0,void(e.textContent="Confirm: access continues until the period ends");if(!ne){ne=!0;'),
]

# Only for this demo: nobody is signed in on a copy, so the chat behaves as signed in when the demo bar says so.
DEMO = [
    ('function q(){var e=window.hasSession;', 'function q(){if(window.__NX_DEMO)return window.__NX_DEMO.in;var e=window.hasSession;'),
    ('if(!(e||"function"==typeof window.hasSession&&window.hasSession()))return void oe({logged_out:!0});', 'if(!q())return void oe({logged_out:!0});'),
]


def patched_js() -> bytes:
    s = (HERE / "live" / "nexus-chat.js").read_text(encoding="utf-8")
    start = s.index("o.innerHTML=`") + len("o.innerHTML=`")
    end = s.index("`,document.body.appendChild(o)", start)
    s = s[:start] + (HERE / "template.html").read_text(encoding="utf-8").replace("NX_WELCOME_HTML", WELCOME).replace("NX_MARK", MARK) + s[end:]
    start = s.index('var V=o.querySelector(".nexus-resize-handle");')
    s = s[:start] + "nxResize();" + s[s.index("var ne=localStorage.getItem(i);", start):]
    for entry in DESIGN + DEMO:
        old, new = entry[0], entry[1]
        want = entry[2] if len(entry) > 2 else 1
        if s.count(old) != want:
            raise RuntimeError(f"patch matches {s.count(old)}x, wanted {want}: {old[:70]}")
        s = s.replace(old, new)
    return s.encode("utf-8")


_cache: dict[str, tuple[float, tuple]] = {}
_client: httpx.Client | None = None
plan = "premium"
pending = 0
links: dict[str, dict] = {}
fails: dict[str, int] = {}
ranked: dict | None = None


def fetch(path: str) -> tuple[int, str, bytes, dict]:
    """One anonymous GET to their platform; the only call here that leaves this machine."""
    global _client
    hit = _cache.get(path)
    if hit and time.time() - hit[0] < TTL:
        return hit[1]
    if _client is None:
        _client = httpx.Client(timeout=60, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0 (qa-cymetica nexus-chat mock)"})
    r = _client.get(UPSTREAM + path)
    out = (r.status_code, r.headers.get("content-type", "application/octet-stream"), r.content, dict(r.headers))
    if r.status_code == 200:
        _cache[path] = (time.time(), out)
    return out


def page(html: str) -> str:
    v = str(int(time.time()))
    html = re.sub(r"/static/css/nexus-chat\.css\?v=[^\"']+", f"/_nx/nexus-chat.css?v={v}", html)
    html = re.sub(r"/static/js/nexus-chat\.js\?v=[^\"']+", f"/_nx/nexus-chat.js?v={v}", html)
    head = ('<script>window.__NX_DEMO={in:true};try{localStorage.getItem("nexus_speak_replies")||localStorage.setItem("nexus_speak_replies","off")}catch(e){}'
            'if(navigator.serviceWorker)navigator.serviceWorker.getRegistrations().then(function(r){r.forEach(function(x){x.unregister()})});</script>')
    html = html.replace("</head>", head + "</head>", 1)
    i = html.rfind("</body>")
    return html[:i] + f'<script src="/_nx/demo.js?v={v}"></script>' + html[i:]


def subscription() -> dict:
    base = {"usdc_balance": 42.5, "premium_price": 9.99, "interaction_fee": 0.01, "microfund_covered_remaining": 0, "is_premium": False, "is_sim_mode": False, "subscription": None}
    if plan == "premium":
        end = time.strftime("%Y-%m-%dT00:00:00Z", time.gmtime(time.time() + 19 * 86400))
        return base | {"is_premium": True, "subscription": {"status": "active", "period_end": end, "interactions_this_period": 214}}
    if plan == "cancelled":
        end = time.strftime("%Y-%m-%dT00:00:00Z", time.gmtime(time.time() + 19 * 86400))
        return base | {"is_premium": True, "subscription": {"status": "cancelled", "period_end": end, "interactions_this_period": 214}}
    if plan == "covered":
        return base | {"microfund_covered_remaining": 37}
    if plan == "paper":
        return base | {"is_sim_mode": True}
    if plan == "broke":
        return base | {"usdc_balance": 1.2}
    return base


def done_meta() -> dict:
    if plan == "covered":
        return {"microfund_covered": True, "microfund_remaining": 36, "microfund_low": False}
    if plan in ("payg", "broke"):
        return {"cost_usd": 0.01, "balance_remaining": 42.49 if plan == "payg" else 1.19}
    return {}


def warm() -> None:
    """Read the demo's figures and the default page ahead, so a reply never waits on their server."""
    global ranked
    while True:
        try:
            status, _, body, _ = fetch("/api/v1/gem-screener/ranked?limit=3")
            if status == 200:
                ranked = json.loads(body)
            for path in ("/gem-screener", "/gem-screener/app?view=apps"):
                fetch(path)
        except httpx.HTTPError:
            pass
        time.sleep(TTL)


def ranked_reply() -> str:
    d = ranked
    if not d:
        return "The Gem Screener did not answer just now. Try again in a moment."
    rows = "\n".join(f"| {i['name']} ({i['symbol']}) | {i['category']} | {i['upside']['value']:g}x | {i['price_vs_revenue']['value']:g}x |" for i in d["items"])
    bench = d["benchmark"]
    return (
        f"## Top 3 apps by upside\n\nFrom **{d['total']['value']} apps** on the [Gem Screener](/gem-screener), as of {d['as_of'][11:16]} UTC.\n\n"
        f"| App | Category | Upside | Price / revenue |\n|---|---|---|---|\n{rows}\n\n"
        f"### How to read it\n\n- **Upside** is the climb to the benchmark's multiple, capped at 50x.\n"
        f"- The benchmark is **{bench['name']}** at {bench['price_vs_revenue']['value']:g}x market cap to annual revenue.\n"
        f"\n1. Open a row\n2. Check its liquidity and holders\n\n---\n\nSame data over the API:\n\n"
        f"```\nGET /api/v1/gem-screener/ranked?limit=3\n```\n"
    )


EXCHANGES = [
    {"id": "alpaca", "display_name": "Alpaca", "type": "stocks", "has_sandbox": True, "setup_url": "https://app.alpaca.markets",
     "setup_instructions": ["Open your Alpaca dashboard", "Generate an API key", "Paste the key and secret below"]},
    {"id": "okx", "display_name": "OKX", "type": "crypto_cex", "requires_passphrase": True, "setup_url": "https://www.okx.com",
     "setup_instructions": ["Open API management", "Create a read and trade key", "Paste the key, secret and passphrase below"]},
    {"id": "soon", "display_name": "Coming soon", "type": "crypto_cex", "coming_soon": True},
]


def script(req: dict):
    """(event, data, seconds before it) for one message. Scripted, because the real stream is billed per message."""
    msg = (req.get("message") or "").strip()
    low = msg.lower()
    ctx = (req.get("page_context") or {}).get("selection") or {}
    yield "session", {"session_id": "demo-session"}, 0.05
    yield "status", {"state": "thinking"}, 0.5
    if low.startswith("confirmed: launch"):
        yield from words("**Demo.** Nothing was launched: this copy sends nothing to Cymetica.")
    elif low.startswith("cancel the token"):
        yield from words("Token launch cancelled.")
    elif "launch" in low:
        yield "tool_start", {"tool": "launch_create_token"}, 0.7
        yield from words("Here is what would be deployed. Check it and confirm.")
        yield "action", {"action": "confirm_launch", "tool_id": "demo", "preview": {"name": "Demo Token", "symbol": "DEMO", "platform": "Demo platform", "chain": "Base", "estimated_cost": "Demo value", "initial_buy": "Demo value"}}, 0.1
    elif low.startswith("i just connected"):
        yield from words("Connected. **Demo:** your keys were dropped on this machine and went nowhere.")
    elif "exchange" in low:
        yield "tool_start", {"tool": "connect_exchange"}, 0.6
        yield from words("Pick the exchange to connect.")
        yield "action", {"action": "open_exchange_modal", "available_exchanges": EXCHANGES}, 0.1
    elif "option" in low and not low.startswith("option"):
        yield from words("Which list do you want?\n\n- **Option A: Top apps by upside**\n- **Option B: How upside is calculated**\n- **Option C: Connect an exchange**")
    elif low.startswith("option b"):
        yield from words("**Upside** is the climb from a token's price to revenue multiple up to the benchmark's. See [Gem Screener](/gem-screener).")
    elif low.startswith("option c"):
        yield "action", {"action": "open_exchange_modal", "available_exchanges": EXCHANGES}, 0.3
    elif "error" in low:
        yield "error", {"error": "demo", "message": "NEXUS could not finish this answer. Please send your message again."}, 0.4
        return
    elif "low balance" in low:
        yield from words("Answered. Your balance is getting low.")
        yield "done", {"cost_usd": 0.01, "balance_remaining": 0.03, "billing_warning": "Low balance: about 3 messages left. Top up to keep chatting."}, 0.05
        return
    elif "degraded" in low:
        yield "status", {"state": "degraded", "message": "Running without conversation history"}, 0.3
        yield from words("I can still answer this one, but I cannot see our earlier messages right now.")
    elif req.get("attachments"):
        yield "status", {"state": "loading"}, 0.6
        yield from words(f"**Demo:** {len(req['attachments'])} attachment(s) reached the chat. The real NEXUS reads them here.")
    elif ctx:
        yield "status", {"state": "loading"}, 0.5
        yield from words(f"You pointed at **{ctx.get('label') or 'a selection'}**. NEXUS gets it with your question.")
    else:
        yield "status", {"state": "loading"}, 0.5
        yield "tool_start", {"tool": "gem_screener_ranked"}, 0.8
        yield from words(ranked_reply())
    yield "done", done_meta(), 0.05


def words(text: str):
    for piece in re.findall(r"\S+\s*", text):
        yield "text", {"content": piece}, 0.022


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

    def js(self, obj, code=200):
        self.send(code, "application/json; charset=utf-8", json.dumps(obj).encode())

    def body(self) -> bytes:
        return self.rfile.read(int(self.headers.get("Content-Length") or 0))

    def do_GET(self):
        global pending
        bare = self.path.split("#")[0].split("?")[0]
        if bare == "/":
            self.send_response(302)
            self.send_header("Location", "/gem-screener")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        if bare == "/_nx/nexus-chat.js":
            return self.send(200, "text/javascript; charset=utf-8", patched_js())
        if bare.startswith("/_nx/") and bare[5:] in OWN:
            return self.send(200, OWN[bare[5:]], (HERE / bare[5:]).read_bytes())
        if bare == "/static/sw.js":
            return self.send(404, "text/plain", b"")
        if bare == "/api/v1/nexus/enabled":
            return self.js({"nexus_enabled": True, "billing_active": True})
        if bare == "/api/v1/nexus/subscription":
            if plan == "fail":
                return self.js({"detail": "demo"}, 500)
            return self.js(subscription())
        if bare == "/api/v1/chat/notifications":
            n, pending = pending, 0
            return self.js({"pending": n})
        if bare == "/api/v1/bootstrap/header":
            return self.js({})
        if bare.startswith("/api/v1/nexus-link/"):
            return self.js(links.get(bare.rsplit("/", 1)[1], {}))
        status, ctype, body, headers = fetch(self.path)
        if status == 200 and ctype.startswith("text/html"):
            body = page(body.decode("utf-8")).encode("utf-8")
        return self.send(status, ctype, body, headers)

    do_HEAD = do_GET

    def do_POST(self):
        global plan, pending
        bare = self.path.split("?")[0]
        raw = self.body()
        if bare == "/__demo/plan":
            plan = json.loads(raw)["plan"]
            return self.js({"plan": plan})
        if bare == "/__demo/pending":
            pending = 1
            return self.js({"pending": 1})
        if bare == "/api/v1/nexus/toggle":
            return self.js({"nexus_enabled": True})
        if bare == "/api/v1/nexus/subscription":
            plan = "premium"
            return self.js({"ok": True})
        if bare == "/api/v1/nexus-link":
            req = json.loads(raw)
            code = f"demo{len(links) + 1}"
            links[code] = {"prompt": req.get("prompt"), "send": req.get("send")}
            return self.js({"url": f"http://127.0.0.1:{PORT}{req.get('page') or '/'}?nexuslink={code}", "code": code})
        if bare == "/api/v1/chat/upload":
            head = raw[:800].decode("latin-1")
            name = re.search(r'filename="([^"]*)"', head)
            kind = re.search(r"Content-Type: ([\w/+.-]+)", head)
            return self.js({"upload_id": f"demo-{time.time()}", "filename": name.group(1) if name else "file", "media_type": kind.group(1) if kind else "application/octet-stream"})
        if bare == "/api/v1/exchanges/connect":
            del raw  # keys, if anyone types real ones: dropped here, never logged
            return self.js({"id": "demo"})
        if bare.startswith("/api/v1/exchanges/connections/"):
            return self.js({"ok": True})
        if bare == "/api/v1/chat/stream":
            req = json.loads(raw)
            if "reconnect" in (req.get("message") or "").lower() and fails.get("n", 0) < 2:
                fails["n"] = fails.get("n", 0) + 1
                return self.send(503, "text/plain", b"demo")
            fails["n"] = 0
            return self.stream(req)
        return self.refuse()

    def stream(self, req):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "close")
        self.end_headers()
        try:
            for event, data, wait in script(req):
                time.sleep(wait)
                self.wfile.write(f"event: {event}\ndata: {json.dumps(data)}\n\n".encode())
                self.wfile.flush()
        except OSError:
            pass
        self.close_connection = True

    def do_DELETE(self):
        global plan
        if self.path.split("?")[0] == "/api/v1/nexus/subscription":
            plan = "cancelled"
            return self.js({"ok": True})
        return self.refuse()

    def refuse(self):
        self.send(403, "application/json; charset=utf-8", b'{"detail":"Mock: nothing is sent from this copy."}')

    do_PUT = do_PATCH = refuse

    def log_message(self, fmt, *args):
        if "--quiet" not in sys.argv:
            sys.stderr.write("%s %s\n" % (self.command, self.path[:120]))


if __name__ == "__main__":
    patched_js()
    threading.Thread(target=warm, daemon=True).start()
    print(f"NEXUS chat on their page: http://127.0.0.1:{PORT}/gem-screener  (Ctrl+C stops it)")
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
