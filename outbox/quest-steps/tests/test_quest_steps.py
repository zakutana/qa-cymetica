"""The Cymetica Quest, step by step (outbox/quest-steps), checked in a real browser before anybody looks at it.

What the operator asked for (2026-10-29), each as a test: the intro and four steps in his order, up to 500k ET10 a
month; in every step a picture and beside it a piece of Cymetica's own web as a hologram, never in a rectangle (the HQ
and the builder; the Development room and Build it Better, OR the agent and the Agent Casino; the Promo Market's cube
and an open brief; the podium and the leaderboard). From the second take's 4/10: nothing over the whole screen, and
nowhere the orbit with its companies. With what holds for every page we draw (outbox/quest/tests): a rail that always
says which step you are on, a glance of words per step, type big enough to read, the site's palette, every figure
from one place.

    python -m pytest outbox/quest-steps/tests -o addopts="" -p no:cacheprovider

`-o addopts=""` keeps the repository's report plugin out: this is a page, not a check against the platform, and a run
of it must not write a run record. Needs Playwright's Chromium.
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
MAX_WORDS = 14                               # per step's words: a glance, not a read
MIN_PX_WIDE, MIN_PX_PHONE = 20, 16           # "type under ~20 px is moc male" (2026-10-23)


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
    page.evaluate("() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))")


def _scroll_to_middle_of(page, chapter):
    page.evaluate("""(id) => { const s = document.getElementById(id), r = s.getBoundingClientRect();
      window.scrollTo({ top: window.scrollY + r.top + r.height / 2 - innerHeight / 2, behavior: 'instant' }); }""", chapter)
    _settle(page)


def _chapters(page):
    return page.evaluate("() => [...document.querySelectorAll('section[data-step]')].map(s => [s.id, +s.dataset.step])")


def _scroll_through(page):
    height = page.evaluate("() => document.documentElement.scrollHeight")
    for y in range(0, height, 700):          # the lazy pictures load as they come near
        page.evaluate("(y) => window.scrollTo(0, y)", y)
        _settle(page)


def test_the_steps_are_his_in_his_order(browser, url):
    """in every step a picture (.pic) and a piece of their web (.holo), the ones he named"""
    page = _open(browser, url, WIDE)
    order = page.evaluate("""() => [...document.querySelectorAll('section[data-step]')].map(s =>
      [s.id, [...s.querySelectorAll('.pic img')].map(i => i.getAttribute('src')), [...s.querySelectorAll('.holo img')].map(i => i.getAttribute('src'))])""")
    assert [o[0] for o in order] == ["hero", "s1", "s2a", "s2b", "s3", "s4", "go"], order
    want = {"s1": (["pics/office.webp"], ["pics/web-builder.webp"]),
            "s2a": (["pics/dev.webp"], ["pics/web-bib.webp"]),
            "s2b": (["pics/agent.webp"], ["pics/web-casino.webp"]),
            "s3": (["pics/cube.webp"], ["pics/web-briefs.webp"]),
            "s4": (["pics/podium.webp"], ["pics/web-board.webp"])}
    got = {sid: (pic, holo) for sid, pic, holo in order if sid in want}
    assert got == want, got
    heads = page.evaluate("() => [...document.querySelectorAll('#s2a h2, #s2b h2')].map(h => h.textContent.trim())")
    assert heads == ["Ship products.", "Breed your agent."], heads
    assert page.locator(".or").count() == 1, "the two ways of step 2 are a choice: OR between them"


def test_nothing_fills_the_screen_and_no_orbit(browser, url):
    """The second take was 4/10: "je to nahovno jak je to pres celou obrazovku" and "nedavej nikde tu obeznou drahu s
    tolika companies". So no picture is wider than 62 % of the screen, and none of that take's Universe shots is back."""
    page = _open(browser, url, WIDE)
    _scroll_through(page)
    wide = page.evaluate("""() => [...document.querySelectorAll('main img')].map(i => [i.getAttribute('src'), +(i.getBoundingClientRect().width / innerWidth).toFixed(2)])
      .filter(([, w]) => w > 0.62)""")
    assert not wide, wide
    srcs = page.evaluate("() => [...document.images].map(i => i.getAttribute('src'))")
    back = [s for s in srcs if any(k in s for k in ("fly", "finale", "tower", "season", "universe"))]
    assert not back, back


def test_a_piece_of_the_web_is_light_not_a_rectangle(browser, url):
    """every hologram is a cut-out: its picture's corners are clear (capture.py keyed the page's dark out), so no edge
    of a rectangle can show on the dark"""
    page = _open(browser, url, WIDE)
    _scroll_through(page)
    page.wait_for_function("[...document.querySelectorAll('.holo img')].every(i => i.complete && i.naturalWidth)", timeout=15000)
    corners = page.evaluate("""() => [...document.querySelectorAll('.holo img')].map(img => {
      const c = document.createElement('canvas'); c.width = img.naturalWidth; c.height = img.naturalHeight;
      const x = c.getContext('2d'); x.drawImage(img, 0, 0);
      const W = c.width - 1, H = c.height - 1, a = [[0, 0], [W, 0], [0, H], [W, H]].map(([u, v]) => x.getImageData(u, v, 1, 1).data[3]);
      return [img.getAttribute('src'), a]; }).filter(([, a]) => a.some(v => v > 40))""")
    assert not corners, corners


def test_every_picture_loads(browser, url):
    page = _open(browser, url, WIDE)
    _scroll_through(page)
    page.wait_for_function("[...document.images].every(i => i.complete)", timeout=15000)
    broken = page.evaluate("() => [...document.images].filter(i => !i.naturalWidth).map(i => i.currentSrc || i.getAttribute('src'))")
    assert not broken, broken
    assert not page.errors, page.errors


@pytest.mark.parametrize("viewport", [WIDE, PHONE], ids=["wide", "phone"])
def test_no_picture_sits_in_a_box(browser, url, viewport):
    """The operator, 2026-10-29: "nedavej ty veci do takovych panelu ... at to splyva prirozene se strankou". So between
    a picture and its section nothing draws an edge (a border, an outline, a box-shadow, a filled background), and every
    picture fades into the page somewhere (a mask on it or on what holds it)."""
    page = _open(browser, url, viewport)
    found = page.evaluate("""() => [...document.querySelectorAll('main img')].map(img => {
      const why = []; let masked = false;
      for (let e = img; e && e.tagName !== 'SECTION'; e = e.parentElement) {
        const cs = getComputedStyle(e);
        if ((cs.webkitMaskImage || cs.maskImage || 'none') !== 'none') masked = true;
        for (const side of ['Top', 'Right', 'Bottom', 'Left']) {
          if (parseFloat(cs['border' + side + 'Width']) > 0 && cs['border' + side + 'Style'] !== 'none' && !/rgba\\(.*, 0\\)$/.test(cs['border' + side + 'Color'])) why.push(e.tagName + ' border-' + side);
        }
        if (cs.outlineStyle !== 'none' && parseFloat(cs.outlineWidth) > 0) why.push(e.tagName + ' outline');
        if (cs.boxShadow !== 'none') why.push(e.tagName + ' box-shadow');
        if (e !== img && !/rgba\\(0, 0, 0, 0\\)|transparent/.test(cs.backgroundColor)) why.push(e.tagName + ' background ' + cs.backgroundColor);
      }
      if (!masked) why.push('no fade into the page');
      return [img.getAttribute('src'), why]; }).filter(([, why]) => why.length)""")
    assert not found, found


def test_the_prize_is_500k_a_month_from_one_config(browser, url):
    """the first screen's prize and step 4's are the same figures, written by quest.js from QUEST, and a digit in the
    words sits inside a [data-figure] (mock-figures-come-from-one-model)"""
    page = _open(browser, url, WIDE)
    assert page.evaluate("() => window.QUEST.prizes") == [500000, 250000, 100000]
    assert page.evaluate("() => document.querySelector('#hero .lede').innerText.replace(/\\s+/g, ' ').trim()") == \
        "Win up to 500,000 ET10 every month."
    loose = page.evaluate("""() => { const out = [];
      for (const root of document.querySelectorAll('section [data-glance] .copy')) {
        const walk = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
        for (let n = walk.nextNode(); n; n = walk.nextNode())
          if (/\\d/.test(n.textContent) && !n.parentElement.closest('[data-figure], .kick')) out.push(n.textContent.trim());
      } return out; }""")
    assert not loose, f"figures typed outside the config: {loose}"
    wrong = page.evaluate("""() => [...document.querySelectorAll('[data-figure]')].filter(el => {
        const v = el.dataset.figure.split('.').reduce((o, k) => o == null ? o : o[k], window.QUEST);
        const t = typeof v === 'number' ? v.toLocaleString('en-US') : String(v);
        return v == null || el.textContent.trim() !== t; }).map(el => [el.dataset.figure, el.textContent.trim()])""")
    assert not wrong, wrong
    got = page.evaluate("() => [...document.querySelectorAll('#hero [data-prizes] .pz b')].map(b => b.textContent)")
    assert got == ["500,000", "250,000", "100,000"], got


def test_every_link_goes_to_cymetica(browser, url):
    page = _open(browser, url, WIDE)
    hrefs = page.evaluate("() => [...document.querySelectorAll('a[data-link]')].map(a => a.href)")
    assert hrefs and all(h.startswith("https://cymetica.com/") for h in hrefs), hrefs


@pytest.mark.parametrize("viewport", [WIDE, PHONE], ids=["wide", "phone"])
def test_the_rail_says_which_step_you_are_on(browser, url, viewport):
    page = _open(browser, url, viewport)
    chapters = _chapters(page)
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
        page.wait_for_function(f"+document.getElementById('rail').dataset.active === {step}", timeout=5000)


@pytest.mark.parametrize("viewport", [WIDE, PHONE], ids=["wide", "phone"])
def test_each_step_is_a_glance(browser, url, viewport):
    page = _open(browser, url, viewport)
    counts = page.evaluate("""() => [...document.querySelectorAll('[data-glance]')].map(g =>
      [g.closest('section').id, [...g.querySelectorAll('.copy')].map(c => c.innerText).join(' ').split(/\\s+/).filter(w => /[\\w%$]/.test(w)).length])""")
    assert len(counts) == 7 and all(n > 0 for _, n in counts), counts
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


def test_no_sideways_scroll_on_a_phone(browser, url):
    page = _open(browser, url, PHONE)
    for chapter, _ in _chapters(page):
        _scroll_to_middle_of(page, chapter)
        wide = page.evaluate("() => document.documentElement.scrollWidth")
        assert wide <= PHONE["width"], (chapter, wide)


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
    (read-the-vendors-design-rule-before-drawing). The pictures are scenes and their pages, exempt."""
    bad = []
    for name in ("quest.css", "index.html", "quest.js"):
        for text, (r, g, b) in _colours((HERE / name).read_text(encoding="utf-8")):
            h, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
            hue = h * 360
            if s >= 0.18 and 0.12 < l < 0.95:
                if not any(lo <= hue <= hi for lo, hi in ALLOWED_HUES):
                    bad.append((name, text, round(hue)))
            elif 0.2 < l < 0.85 and s < 0.04:
                bad.append((name, text, "plain grey"))
    assert not bad, bad
