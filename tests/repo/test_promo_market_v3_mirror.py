"""The v3 local copy of their Promo Market (outbox/promo-market-v3/live).

The operator, 2026-10-27: "vytvor lokal verzi jak by to mohlo vypadat" -- their live /expire76#new and the market,
with only the v3 changes on top, served by a mirror that may only ever read from their platform.

What each test protects:
* the mirror refuses every method but GET and HEAD and does not touch their platform for it: a copy of a page with
  Post the brief and Pay buttons must never post a brief or move money on the real one;
* the patch says so when their script stops matching it, instead of showing the operator an unchanged page;
* the owner sees the page as its owner, a stranger at /promo-market sees the market.
"""
from __future__ import annotations

import http.client
import importlib.util
import json
import re
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

from qa.marks import SafetyTier, qa

LIVE = Path(__file__).resolve().parents[2] / "outbox" / "promo-market-v3" / "live"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(f"pm3_{name}", LIVE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


patch = _load("patch")
serve = _load("serve")

PAGE = ('<html><head></head><body><span class="livechip" id="livechip"></span>'
        '<script id="pm2-boot" type="application/json">{"creator": "", "is_owner": false, "signed_in": false, "tab": "me/today"}</script>'
        '<a href="/creator-dashboard?view=classic">x</a></body></html>')
SCRIPT = ("(function () {\n  const a = '<section id=\"board\"><div>';\n  const b = ['signed up, own deposit, 14-day check'];\n"
          "  const c = ['signed up, own deposit, 14-day check'];\n" + patch.TAIL)


@pytest.fixture()
def server(monkeypatch):
    calls = []

    def fake(path):
        calls.append(path)
        return 200, "text/html; charset=utf-8", PAGE.encode(), {}

    monkeypatch.setattr(serve, "fetch_upstream", fake)
    srv = ThreadingHTTPServer(("127.0.0.1", 0), serve.Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield srv.server_address[1], calls
    srv.shutdown()


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
@pytest.mark.parametrize("method", ["POST", "PUT", "DELETE", "PATCH"])
def test_the_mirror_never_writes(server, method):
    port, calls = server
    c = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    c.request(method, "/api/v1/promo/briefs", body=b"{}", headers={"Content-Type": "application/json"})
    assert c.getresponse().status == 405
    assert calls == []


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_owner_is_the_owner_and_a_stranger_sees_the_market():
    owner = patch.patch_html("owner", PAGE)
    boot = json.loads(re.search(r'pm2-boot" type="application/json">(.*?)</script>', owner).group(1))
    assert boot["is_owner"] and boot["signed_in"] and 'id="v3bell"' in owner and "/__v3/v3.css" in owner
    market = patch.patch_html("market", PAGE)
    boot = json.loads(re.search(r'pm2-boot" type="application/json">(.*?)</script>', market).group(1))
    assert boot["tab"] == "market" and not boot["is_owner"] and "v3bell" not in market
    assert "/promo-market?view=classic" in market


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_patch_lands_inside_their_closure():
    js = patch.patch_js(SCRIPT)
    assert "v3Protect() + '<section id=\"board\">" in js and "own deposit" not in js
    assert js.index("function newBrief") < js.index(patch.TAIL)


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_changed_script_is_said_not_shown_unchanged():
    with pytest.raises(patch.AnchorMissing):
        patch.patch_js(SCRIPT.replace('<section id="board">', '<section id="briefs">'))
    with pytest.raises(patch.AnchorMissing):
        patch.patch_js(SCRIPT.replace("bootStart();", "start();"))
