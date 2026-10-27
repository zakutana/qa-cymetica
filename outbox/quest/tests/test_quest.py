"""The Cymetica Quest guide (outbox/quest), checked in a real browser before anybody looks at it.

What the operator asked for (2026-10-27), each as a test: a panel that is always on screen and says which of the four
steps you are on as you scroll (and jumps when clicked); as little reading as possible; type big enough to read; the
site's own palette on everything that is not the 3D picture; and every figure from one place, so the prize on the
first screen and the prize on the last can never disagree.

    python -m pytest outbox/quest/tests -o addopts="" -p no:cacheprovider

`-o addopts=""` keeps the repository's report plugin out: this is a page, not a check against the platform, and a
run of it must not write a run record. Needs Playwright's Chromium.
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
WIDE = {"width": 2000, "height": 1100}      # the operator's screenshots are ~2000 px wide
PHONE = {"width": 390, "height": 844}
MAX_WORDS = 14                               # per chapter's copy: a glance, not a read
MIN_PX_WIDE, MIN_PX_PHONE = 20, 16           # "type under ~20 px is moc male" (2026-10-23)


@pytest.fixture(scope="module")
def url():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass
    handler = functools.partial(Quiet, directory=str(HERE))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{port}/index.html"
    server.shutdown()


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as p:
        b = p.chromium.launch()
        yield b
        b.close()


def _open(browser, url, viewport):
    page = browser.new_page(viewport=viewport)
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(url, wait_until="load")
    page.wait_for_function("window.QUEST_STATE && window.QUEST_STATE.ready === true")
    page.errors = errors
    return page


def _settle(page):
    # two animation frames: the engine reads the scroll position on the next one
    page.evaluate("() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))")


def _scroll_to_middle_of(page, chapter):
    page.evaluate("""(id) => { const s = document.getElementById(id), r = s.getBoundingClientRect();
      window.scrollTo({ top: window.scrollY + r.top + r.height / 2 - innerHeight / 2, behavior: 'instant' }); }""", chapter)
    _settle(page)


def _chapters(page):
    return page.evaluate("() => [...document.querySelectorAll('section[data-step]')].map(s => [s.id, +s.dataset.step])")


@pytest.mark.parametrize("viewport", [WIDE, PHONE], ids=["wide", "phone"])
def test_the_rail_says_which_step_you_are_on(browser, url, viewport):
    page = _open(browser, url, viewport)
    chapters = _chapters(page)
    assert [c[1] for c in chapters][:1] == [0], "the page opens on the hero, before step 1"
    assert sorted({c[1] for c in chapters}) == [0, 1, 2, 3, 4], chapters
    for chapter, step in chapters:
        _scroll_to_middle_of(page, chapter)
        active = page.evaluate("() => +document.getElementById('rail').dataset.active")
        assert active == step, f"in the middle of #{chapter} the rail says step {active}, not {step}"
        lit = page.evaluate("() => [...document.querySelectorAll('#rail [data-step].on')].map(a => +a.dataset.step)")
        assert lit == ([step] if step else []), f"#{chapter}: lit segments {lit}"
    assert not page.errors, page.errors


@pytest.mark.parametrize("viewport", [WIDE, PHONE], ids=["wide", "phone"])
def test_the_rail_never_leaves_the_screen(browser, url, viewport):
    page = _open(browser, url, viewport)
    height = page.evaluate("() => document.documentElement.scrollHeight - innerHeight")
    for k in range(0, 11):
        page.evaluate("(y) => window.scrollTo({ top: y, behavior: 'instant' })", height * k / 10)
        _settle(page)
        box = page.evaluate("""() => { const r = document.getElementById('rail'), b = r.getBoundingClientRect(), cs = getComputedStyle(r);
          return { top: b.top, bottom: b.bottom, left: b.left, right: b.right, opacity: +cs.opacity, vis: cs.visibility }; }""")
        assert box["vis"] == "visible" and box["opacity"] >= 0.9, (k, box)
        assert box["top"] >= 0 and box["bottom"] <= viewport["height"], (k, box)
        assert box["left"] >= 0 and box["right"] <= viewport["width"], (k, box)


def test_a_click_on_the_rail_jumps_to_that_step(browser, url):
    page = _open(browser, url, WIDE)
    for step in (3, 1, 4, 2):
        page.click(f"#rail [data-step='{step}']")
        page.wait_for_function(f"+document.getElementById('rail').dataset.active === {step}", timeout=4000)


@pytest.mark.parametrize("viewport", [WIDE, PHONE], ids=["wide", "phone"])
def test_each_chapter_is_a_glance(browser, url, viewport):
    page = _open(browser, url, viewport)
    counts = page.evaluate("""() => [...document.querySelectorAll('section[data-step]')].map(s =>
      [s.id, [...s.querySelectorAll('.copy')].map(c => c.innerText).join(' ').split(/\\s+/).filter(w => /[\\w%$]/.test(w)).length])""")
    assert all(n > 0 for _, n in counts), counts
    over = [(c, n) for c, n in counts if n > MAX_WORDS]
    assert not over, f"more than {MAX_WORDS} words: {over}"


@pytest.mark.parametrize("viewport,floor", [(WIDE, MIN_PX_WIDE), (PHONE, MIN_PX_PHONE)], ids=["wide", "phone"])
def test_no_text_too_small_to_read(browser, url, viewport, floor):
    page = _open(browser, url, viewport)
    small = page.evaluate("""(floor) => { const out = [];
      for (const el of document.querySelectorAll('#rail *, section *')) {
        const own = [...el.childNodes].some(n => n.nodeType === 3 && n.textContent.trim());
        if (!own) continue;
        const cs = getComputedStyle(el), b = el.getBoundingClientRect();
        if (cs.display === 'none' || cs.visibility === 'hidden' || b.width === 0) continue;
        if (parseFloat(cs.fontSize) < floor) out.push([el.className || el.tagName, el.textContent.trim().slice(0, 30), cs.fontSize]);
      } return out; }""", floor)
    assert not small, small


def test_every_figure_comes_from_the_one_config(browser, url):
    """A digit in the copy or on the board sits inside a [data-figure] whose text is the config's value: the first
    screen's prize and the last screen's board are the same numbers by construction (mock-figures-come-from-one-model)."""
    page = _open(browser, url, WIDE)
    loose = page.evaluate("""() => { const out = [];
      for (const root of document.querySelectorAll('section .copy, section .board')) {
        const walk = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
        for (let n = walk.nextNode(); n; n = walk.nextNode())
          if (/\\d/.test(n.textContent) && !n.parentElement.closest('[data-figure]')) out.push(n.textContent.trim());
      } return out; }""")
    assert not loose, f"figures typed outside the config: {loose}"
    wrong = page.evaluate("""() => [...document.querySelectorAll('[data-figure]')].filter(el => {
        const v = el.dataset.figure.split('.').reduce((o, k) => o == null ? o : o[k], window.QUEST);
        return v == null || el.textContent.trim() !== String(v); }).map(el => [el.dataset.figure, el.textContent.trim()])""")
    assert not wrong, wrong
    shares = page.evaluate("() => window.QUEST.prize.shares")
    board = page.evaluate("() => [...document.querySelectorAll('#s4 .board [data-figure^=\"prize.shares\"]')].map(e => e.textContent.trim())")
    assert board == [str(s) for s in shares], (board, shares)


def test_no_sideways_scroll_on_a_phone(browser, url):
    page = _open(browser, url, PHONE)
    for chapter, _ in _chapters(page):
        _scroll_to_middle_of(page, chapter)
        wide = page.evaluate("() => document.documentElement.scrollWidth")
        assert wide <= PHONE["width"], (chapter, wide)


def test_the_film_runs_forward_as_you_scroll(browser, url):
    """Inside a flight the frame the engine wants only ever moves forward as the page goes down (scroll up, it flies
    back); and in every chapter something is on screen beneath the text, frames or not."""
    page = _open(browser, url, WIDE)
    height = page.evaluate("() => document.documentElement.scrollHeight - innerHeight")
    seen = []
    for k in range(0, 101):
        page.evaluate("(y) => window.scrollTo({ top: y, behavior: 'instant' })", height * k / 100)
        _settle(page)
        st = page.evaluate("() => ({ shot: window.QUEST_STATE.shot, f: window.QUEST_STATE.frame, lit: window.QUEST_STATE.lit })")
        assert st["lit"] >= 0.99, (k, st)
        seen.append(st)
    for a, b in zip(seen, seen[1:]):
        if a["shot"] == b["shot"] and a["f"] is not None and b["f"] is not None:
            assert b["f"] >= a["f"], (a, b)


ALLOWED_HUES = ((90, 205), (205, 235), (345, 360), (0, 12))   # green .. cyan, blue, red (the site's palette)


def _colours(css):
    for m in re.finditer(r"#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b", css):
        h = m.group(1)
        h = "".join(c * 2 for c in h) if len(h) == 3 else h
        yield m.group(0), tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
    for m in re.finditer(r"rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)", css):
        yield m.group(0), tuple(int(m.group(i)) for i in (1, 2, 3))


def test_the_page_keeps_the_site_palette():
    """Cymetica's rule for its pages: cyan, green, red, blue; no purple, magenta, amber, orange, yellow or plain grey
    (read-the-vendors-design-rule-before-drawing). Near-whites, near-blacks and blue-tinted greys are the board's own
    text and glass. The 3D frames and the generated pictures are the scene, exempt (the operator, 2026-10-18)."""
    bad = []
    for name in ("quest.css", "index.html"):
        for text, (r, g, b) in _colours((HERE / name).read_text(encoding="utf-8")):
            h, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
            hue = h * 360
            if s >= 0.18 and 0.12 < l < 0.95:
                if not any(lo <= hue <= hi for lo, hi in ALLOWED_HUES):
                    bad.append((name, text, round(hue)))
            elif 0.2 < l < 0.85 and s < 0.04:
                bad.append((name, text, "plain grey"))
    assert not bad, bad
