"""The Quant Lab page, redesigned for degens (outbox/quant-lab-v2): a mock of /company/app/experiments.

What it must hold, each as a test: it runs without an error in both modes; the real mode's numbers are exactly what
their API returned (data.js); the simulated mode (how ET-33142 is meant to work) comes from ONE model, so a winner
cleared its bar, every loser did not, and the bot born from a winner carries the winner's setup chip for chip; no
visible text is longer than a glance; nothing is too small to read; the site's palette only; and the page sends
nothing anywhere (no fetch, no XHR, no form).

    python -m pytest outbox/quant-lab-v2/tests -o addopts="" -p no:cacheprovider
"""
import colorsys
import functools
import http.server
import json
import re
import socket
import threading
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent.parent
MAX_WORDS = 12
MIN_PX = 11


def data() -> dict:
    text = (HERE / "data.js").read_text(encoding="utf-8")
    return json.loads(text[text.index("{"):text.rstrip().rstrip(";").rindex("}") + 1])


@pytest.fixture(scope="module")
def url():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]

    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass
    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), functools.partial(Quiet, directory=str(HERE)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{port}/index.html"
    server.shutdown()


@pytest.fixture(scope="module")
def page(url):
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1900, "height": 1000})
        errors, sent = [], []
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.on("request", lambda r: sent.append((r.method, r.resource_type, r.url)))
        pg.goto(url, wait_until="load")
        pg.wait_for_function("window.QL && window.QL.ready === true")
        pg.errors, pg.sent = errors, sent
        yield pg
        b.close()


def mode(page, m):
    page.click(f'[data-mode="{m}"]')
    page.wait_for_function("(m) => window.QL.mode === m", arg=m)
    page.wait_for_timeout(400)


def test_it_runs_without_an_error_in_both_modes(page):
    for m in ("real", "sim", "real"):
        mode(page, m)
        page.wait_for_timeout(1500)
    assert not page.errors, page.errors


def test_the_real_mode_shows_what_their_api_returned(page):
    mode(page, "real")
    d = data()
    tiles = dict(page.evaluate("() => [...document.querySelectorAll('[data-k]')].map(e => [e.dataset.k, e.textContent.replace(/[,\\s]/g, '')])"))
    done = [s for s in d["searches"] if s["status"] == "done"]
    last = done[0]["summary"]
    assert tiles["searches"] == str(len(d["searches"])), tiles
    assert tiles["failed"] == str(sum(s["status"] == "failed" for s in d["searches"])), tiles
    assert tiles["tried"] == str(d["combinations_tried"]), tiles
    assert tiles["checked"] == str(last["held_back_checked"]), tiles
    assert tiles["won"] == str(last["won"]), tiles
    assert tiles["bots"] == str(len(d["experiments"])), tiles
    rows = page.evaluate("() => [...document.querySelectorAll('.top-row')].map(r => [r.dataset.model, r.dataset.market, +r.dataset.search, +r.dataset.held, +r.dataset.bar, r.dataset.verdict])")
    want = [[x["model"], x["market"], x["search"]["return_pct"], x["held"]["return_pct"], x["bar"]["bar_pct"], x["verdict"]] for x in d["held_back"]]
    assert rows == want, (rows, want)


def test_the_simulation_comes_from_one_model(page):
    mode(page, "sim")
    s = page.evaluate("() => window.QL.sim")
    assert s["tried"] == s["setups"] * len(s["markets"]) * s["settings"], s
    assert s["checked"] == len(s["candidates"]) and 0 < s["checked"] < s["tried"], s
    winners = [c for c in s["candidates"] if c["won"]]
    assert winners, "the simulation must show the point of ET-33142: a winner that becomes a bot"
    for c in s["candidates"]:
        assert c["won"] == (c["held"] > c["bar"]), c
        assert c["bar"] >= 1.0, c   # their method: never below 1%
    assert s["bots"] == len(winners), s
    born = page.evaluate("() => [...document.querySelectorAll('.q2-bot')].map(b => b.dataset.setup)")
    assert sorted(born) == sorted(c["setup_key"] for c in winners), (born, winners)
    tiles = dict(page.evaluate("() => [...document.querySelectorAll('[data-k]')].map(e => [e.dataset.k, e.textContent.replace(/[,\\s]/g, '')])"))
    assert tiles["tried"] == str(s["tried"]) and tiles["won"] == str(len(winners)) and tiles["bots"] == str(s["bots"]), tiles


def test_every_text_is_a_glance(page):
    for m in ("real", "sim"):
        mode(page, m)
        long = page.evaluate("""(n) => { const out = [];
          for (const el of document.querySelectorAll('body *')) {
            const own = [...el.childNodes].filter(c => c.nodeType === 3).map(c => c.textContent).join(' ').trim();
            if (!own) continue;
            const r = el.getBoundingClientRect(), cs = getComputedStyle(el);
            if (!r.width || cs.visibility === 'hidden' || el.closest('[hidden], details:not([open]) > :not(summary)')) continue;
            const w = own.split(/\\s+/).filter(x => /[\\w%$]/.test(x)).length;
            if (w > n) out.push([el.className || el.tagName, own.slice(0, 60), w]);
          } return out; }""", MAX_WORDS)
        assert not long, (m, long)


def test_no_text_too_small(page):
    small = page.evaluate("""(floor) => { const out = [];
      for (const el of document.querySelectorAll('body *')) {
        if (![...el.childNodes].some(n => n.nodeType === 3 && n.textContent.trim())) continue;
        const cs = getComputedStyle(el); if (cs.display === 'none' || !el.getBoundingClientRect().width) continue;
        if (parseFloat(cs.fontSize) < floor) out.push([el.className || el.tagName, el.textContent.trim().slice(0, 24), cs.fontSize]);
      } return out; }""", MIN_PX)
    assert not small, small


def test_the_page_sends_nothing(page):
    calls = [r for r in page.sent if r[1] in ("fetch", "xhr", "websocket") or (r[0] != "GET")]
    assert not calls, calls
    for f in ("ql.js", "index.html"):
        src = (HERE / f).read_text(encoding="utf-8")
        assert not re.search(r"\bfetch\(|XMLHttpRequest|WebSocket|<form|sendBeacon", src), f


def test_the_site_palette_only():
    """Cyan, green, red, blue on navy (their style.css). No purple, magenta, amber, orange or yellow."""
    allowed = ((90, 215), (215, 250), (345, 360), (0, 12))
    bad = []
    for f in ("index.html", "ql.css", "ql.js"):
        text = (HERE / f).read_text(encoding="utf-8")
        for m in re.finditer(r"#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b", text):
            h = m.group(1)
            h = "".join(c * 2 for c in h) if len(h) == 3 else h
            r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
            hue, l, s = colorsys.rgb_to_hls(r, g, b)
            if s >= 0.18 and 0.12 < l < 0.95 and not any(lo <= hue * 360 <= hi for lo, hi in allowed):
                bad.append((f, m.group(0), round(hue * 360)))
        for m in re.finditer(r"rgba?\((\d+),\s*(\d+),\s*(\d+)", text):
            r, g, b = (int(x) / 255 for x in m.groups())
            hue, l, s = colorsys.rgb_to_hls(r, g, b)
            if s >= 0.18 and 0.12 < l < 0.95 and not any(lo <= hue * 360 <= hi for lo, hi in allowed):
                bad.append((f, m.group(0), round(hue * 360)))
    assert not bad, bad
