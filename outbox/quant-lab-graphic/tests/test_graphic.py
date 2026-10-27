"""The Quant Lab graphic (outbox/quant-lab-graphic): the picture degens read on the experiments page to see what the lab does.

What it must hold, each as a test: it runs without an error; every word on it is a glance (a few per stage); no type too
small to read; the site's own palette; and its numbers come from ONE running model, so they can never disagree
(more tried than passed the blind test, more passed than ran on paper, more ran on paper than reached the desk).

    python -m pytest outbox/quant-lab-graphic/tests -o addopts="" -p no:cacheprovider
"""
import colorsys
import functools
import http.server
import re
import socket
import threading
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent.parent
MAX_WORDS_PER_STAGE = 10
MIN_PX = 13


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
        pg = b.new_page(viewport={"width": 1500, "height": 800})
        errors = []
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.goto(url, wait_until="load")
        pg.wait_for_function("window.QL && window.QL.ready === true")
        pg.errors = errors
        yield pg
        b.close()


def test_it_runs_without_an_error(page):
    page.wait_for_timeout(2500)
    assert not page.errors, page.errors
    assert page.evaluate("() => window.QL.tried") > 0


def test_every_stage_is_a_glance(page):
    stages = page.evaluate("""() => [...document.querySelectorAll('.stage')].map(s =>
      [s.dataset.stage, s.innerText.split(/\\s+/).filter(w => /[\\w%$]/.test(w)).length])""")
    assert [s[0] for s in stages] == ["try", "blind", "paper", "you"], stages
    over = [s for s in stages if s[1] > MAX_WORDS_PER_STAGE]
    assert not over, f"more than {MAX_WORDS_PER_STAGE} words: {over}"


def test_no_text_too_small(page):
    small = page.evaluate("""(floor) => { const out = [];
      for (const el of document.querySelectorAll('body *')) {
        if (![...el.childNodes].some(n => n.nodeType === 3 && n.textContent.trim())) continue;
        const cs = getComputedStyle(el); if (cs.display === 'none' || el.getBoundingClientRect().width === 0) continue;
        if (parseFloat(cs.fontSize) < floor) out.push([el.className || el.tagName, el.textContent.trim().slice(0, 24), cs.fontSize]);
      } return out; }""", MIN_PX)
    assert not small, small


def test_the_numbers_come_from_one_model(page):
    for _ in range(6):
        page.wait_for_timeout(1500)
        q = page.evaluate("() => ({ ...window.QL })")
        assert q["tried"] >= q["blindDone"] >= q["passed"] >= q["paper"] >= q["approved"] >= 0, q
        shown = page.evaluate("() => [...document.querySelectorAll('[data-q]')].map(e => [e.dataset.q, e.textContent.replace(/,/g, '').trim()])")
        for key, text in shown:
            assert text == str(window_value(page, key)) or abs(int(text) - window_value(page, key)) <= 40, (key, text)


def window_value(page, key):
    return page.evaluate("(k) => window.QL[k]", key)


def test_the_picture_keeps_the_site_palette():
    """Cyan, green, red, blue on navy (the experiments page's own: xp.css). No purple, magenta, amber, orange or yellow."""
    allowed = ((90, 215), (215, 250), (345, 360), (0, 12))
    bad = []
    text = (HERE / "index.html").read_text(encoding="utf-8")
    for m in re.finditer(r"#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b", text):
        h = m.group(1)
        h = "".join(c * 2 for c in h) if len(h) == 3 else h
        r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
        hue, l, s = colorsys.rgb_to_hls(r, g, b)
        if s >= 0.18 and 0.12 < l < 0.95 and not any(lo <= hue * 360 <= hi for lo, hi in allowed):
            bad.append((m.group(0), round(hue * 360)))
    assert not bad, bad
