"""A local copy of the live Universe with the Capital Maximizer model on the operator's plot.

    python outbox/capital-maximizer/universe/serve.py       # http://127.0.0.1:8812/company/app#universe

The page, styles, scripts and data are THEIR live ones, read anonymously (GET, no cookies, no key). What changes is only
what this file patches into three of their scripts: adcapital.js into u3d.js, the product on slot-4-4 (the plot the
operator bought, GET /company/land lists it as his with nothing on it) into universe.js, and its panel into
prodpanel.js. Every method except GET and HEAD is refused here, before anything is sent anywhere. Every answer is
Cache-Control: no-store, so his open tab cannot keep an old model.
"""
from __future__ import annotations

import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import httpx

HERE = Path(__file__).resolve().parent
UPSTREAM = "https://cymetica.com"
PORT = 8812
DROP = {"content-security-policy", "content-security-policy-report-only", "content-encoding", "content-length",
        "transfer-encoding", "connection", "set-cookie", "strict-transport-security", "cross-origin-opener-policy",
        "cross-origin-resource-policy", "x-frame-options", "cache-control", "pragma", "etag", "last-modified", "content-type"}
PRODUCT = """    // Capital Maximizer, on the plot the operator bought (slot-4-4)
    'slot-4-4': { c: { id: 'product-capital-maximizer', name: 'Capital Maximizer', accent: 'green', skin: 'dome', public: true, status: 'active',
      departments: [{ key: 'research' }, { key: 'engineering' }] }, panel: 'capital', seed: 97, page: '/capital-maximizer',
      blurb: 'The best DeFi routes for your USDC and your risk.' },
"""
FLAT = """    } else if (it.product.panel === 'capital') {
      // Capital Maximizer: the stepped pyramid and the arrow out of it, flat
      var py = y - s * 0.12, step = s * 0.11, cap = '';
      [0.5, 0.4, 0.3, 0.2].forEach(function (w, i) { cap += '<rect x="' + f1(x - s * w) + '" y="' + f1(py - (i + 1) * step) + '" width="' + f1(s * w * 2) + '" height="' + f1(step * 0.82) + '" fill="#2c4154" stroke="' + ['#00cfff', '#00dcc4', '#00eea6', '#00ff88'][i] + '" stroke-width="2"/>'; });
      out = shadow + cap + '<path d="M' + f1(x) + ' ' + f1(py - 4 * step) + ' L' + f1(x + s * 0.3) + ' ' + f1(py - s * 0.74) + ' L' + f1(x + s * 0.42) + ' ' + f1(py - s * 0.62) + ' L' + f1(x + s * 0.7) + ' ' + f1(py - s * 1.05) + ' M' + f1(x + s * 0.5) + ' ' + f1(py - s * 1.02) + ' L' + f1(x + s * 0.7) + ' ' + f1(py - s * 1.05) + ' L' + f1(x + s * 0.72) + ' ' + f1(py - s * 0.84) + '" fill="none" stroke="#00ff88" stroke-width="5" stroke-linejoin="miter"/>';
      top = py - s * 1.05;
"""


def once(src: str, anchor: str, new: str) -> str:
    """One replacement that must find its anchor exactly once: their build moving under us says so, loudly."""
    if src.count(anchor) != 1:
        raise RuntimeError(f"anchor found {src.count(anchor)} times, not once: {anchor[:60]!r}")
    return src.replace(anchor, new)


def patch_u3d(src: str) -> str:
    model = (HERE / "adcapital.js").read_text(encoding="utf-8")
    src = once(src, "function makeAd(ad) {", model + "function makeAd(ad) {")
    src = once(src, "phase: { gem: 0.4, casino: 2.1, promo: 3.7, farmer: 5.2 }", "phase: { gem: 0.4, casino: 2.1, promo: 3.7, farmer: 5.2, capital: 1.2 }")
    src = once(src, "({ gem: adGem, casino: adCasino, promo: adPromo, farmer: adFarmer }", "({ gem: adGem, casino: adCasino, promo: adPromo, farmer: adFarmer, capital: adCapital }")
    # its halo fainter than the others': a green haze over a dark model took all its contrast away
    src = once(src, "const halo = glowSprite(A.c, 0.4, 5 + b.foot);", "const halo = glowSprite(A.c, ad.key === 'capital' ? 0.12 : 0.4, 5 + b.foot);")
    return src


def patch_universe(src: str) -> str:
    src = once(src, "  CO.UV_PRODUCTS = {\n", "  CO.UV_PRODUCTS = {\n" + PRODUCT)
    src = once(src, "    } else if (it.product.panel === 'farmer') {", FLAT + "    } else if (it.product.panel === 'farmer') {")
    return src


def patch_prodpanel(src: str) -> str:
    # its panel reads Capital Maximizer's own API, as the others read theirs
    logo = (HERE.parent / "logos" / "logo-12.svg").read_text(encoding="utf-8").strip().replace("\n", " ").replace("'", '"')
    logo = logo.replace('<svg ', '<svg width="64" height="64" ', 1)
    src = once(src, "  function goButtons(p) {\n", """  var CAPITAL_LOGO = '""" + logo + """';
  function capitalBody(d) {
    var c = d && d.counters; if (!c) return '<p class="hint">The routes are not available right now. Open Capital Maximizer for the live list.</p>';
    return '<div class="up-logo">' + CAPITAL_LOGO + '</div><div class="ac-kpis"><div><b>' + num(c.platforms) + '</b><span>verified platforms</span></div><div><b>' + num(c.chains) + '</b><span>chains</span></div><div><b>4</b><span>risk tiers</span></div></div>';
  }
  function goButtons(p) {
    if (p.panel === 'capital') return '<a class="btn gr up-go" href="' + esc(p.page) + '" target="_blank" rel="noopener">Visit Capital Maximizer \\u2197</a>';
""")
    src = once(src, "var url = p.panel === 'gem' ?", "var url = p.panel === 'capital' ? '/api/v1/capital-maximizer/platforms' : p.panel === 'gem' ?")
    src = once(src, "b.innerHTML = p.panel === 'gem' ? gemBody(d) :", "b.innerHTML = p.panel === 'capital' ? capitalBody(d) : p.panel === 'gem' ? gemBody(d) :")
    return src


PATCHES = {"/static/company/u3d.js": patch_u3d, "/static/company/universe.js": patch_universe, "/static/company/prodpanel.js": patch_prodpanel}
_client: httpx.Client | None = None


def upstream(path: str) -> tuple[int, str, bytes, dict]:
    """One anonymous GET to their platform; the only call here that leaves this machine."""
    global _client
    if _client is None:
        _client = httpx.Client(timeout=60, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0 (qa-cymetica capital-maximizer mirror)"})
    r = _client.get(UPSTREAM + path)
    return r.status_code, r.headers.get("content-type", "application/octet-stream"), r.content, dict(r.headers)


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        return

    def _refuse(self):
        body = b'{"detail":"read-only local copy of the Universe: nothing is sent to cymetica.com"}'
        self.send_response(405)
        self.send_header("Allow", "GET, HEAD")
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    do_POST = do_PUT = do_DELETE = do_PATCH = do_OPTIONS = _refuse

    def _send(self, status, ctype, body, headers=None, head=False):
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for k, v in (headers or {}).items():
            if k.lower() not in DROP:
                self.send_header(k, v)
        self.end_headers()
        if not head:
            self.wfile.write(body)

    def _get(self, head):
        bare = self.path.split("?")[0]
        if "/stream" in bare or bare.startswith("/ws"):      # a stream never ends: this copy does not hold one open
            return self._send(404, "text/plain", b"no streams here", head=head)
        try:
            status, ctype, body, headers = upstream(self.path)
        except httpx.HTTPError as exc:
            return self._send(502, "text/plain", str(exc).encode(), head=head)
        fix = PATCHES.get(bare)
        if fix and status == 200:
            try:
                body = fix(body.decode("utf-8")).encode("utf-8")
            except RuntimeError as exc:
                sys.stderr.write(f"{bare}: {exc}\n")
                return self._send(500, "text/plain", str(exc).encode(), head=head)
        self._send(status, ctype, body, headers, head=head)

    def do_GET(self):
        self._get(False)

    def do_HEAD(self):
        self._get(True)


if __name__ == "__main__":
    print(f"http://127.0.0.1:{PORT}/company/app#universe", flush=True)
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
