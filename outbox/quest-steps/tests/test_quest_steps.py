"""The Cymetica Quest, step by step (outbox/quest-steps), checked in a real browser before anybody looks at it.

What the operator asked for (2026-10-29), each as a test: the intro and four steps in his order (the tutorial's office;
space robot tools OR breed your agent; the Promo Market's building close and its page; the leaderboard), up to 500k ET10
a month. And his two rules from the first take's 7/10: no picture in a panel, a frame or a box, every one melting into
the page; and the opening not a giant banner. With what holds for every page we draw (outbox/quest/tests): a rail that
always says which step you are on, a glance of words per step, type big enough to read, the site's palette, every
figure from one place.

    python -m pytest outbox/quest-steps/tests -o addopts="" -p no:cacheprovider

`-o addopts=""` keeps the repository's report plugin out: this is a page, not a check against the platform, and a run
of it must not write a run record. Needs Playwright's Chromium. Passes without the flight's frames (pics/fly/, not in
git): the opening then shows its first frame.
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
    page = _open(browser, url, WIDE)
    order = page.evaluate("""() => [...document.querySelectorAll('section[data-step]')].map(s =>
      [s.id, [...s.querySelectorAll('img')].map(i => i.getAttribute('src'))])""")
    assert [o[0] for o in order] == ["hero", "s1", "s2", "s3", "s4", "go"], order
    pics = dict(order)
    assert pics["s1"] == ["pics/office.webp"], "step 1 is the tutorial's office, the headquarters"
    assert pics["s2"] == ["pics/tools.webp", "pics/agent.webp"], "step 2: space robot tools, or the agent"
    assert pics["s3"] == ["pics/tower.webp", "pics/promo-ui.webp"], "step 3: the Promo Market building close, and its page"
    assert pics["s4"] == ["pics/board.webp"]
    heads = page.evaluate("() => [...document.querySelectorAll('#s2 .way h2')].map(h => h.textContent.trim())")
    assert heads == ["Ship products.", "Breed your agent."], heads
    assert page.locator("#s2 .or").count() == 1, "the two ways of step 2 are a choice: OR between them"


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


def test_the_opening_is_not_a_banner(browser, url):
    """The first take's opening was "moc obrovsky ... jak nejaky obri reklamni banner": the title now takes at most
    60 % of the width, nothing on the first screen is over 84 px, and nothing there sits in a filled box but the call."""
    page = _open(browser, url, WIDE)
    box = page.evaluate("() => document.querySelector('#hero h1').getBoundingClientRect().width / innerWidth")
    assert box <= 0.6, f"the title is {box:.0%} of the width"
    big = page.evaluate("""() => [...document.querySelectorAll('#hero .hero-copy *')].filter(e => [...e.childNodes].some(n => n.nodeType === 3 && n.textContent.trim()))
      .map(e => [e.className || e.tagName, parseFloat(getComputedStyle(e).fontSize)]).filter(([, s]) => s > 84)""")
    assert not big, big
    boxed = page.evaluate("""() => [...document.querySelectorAll('#hero .prizes *')].filter(e => !/rgba\\(0, 0, 0, 0\\)/.test(getComputedStyle(e).backgroundColor)).map(e => e.className)""")
    assert not boxed, f"the prizes are type, not chips: {boxed}"


def test_the_prize_is_500k_a_month_from_one_config(browser, url):
    """the first screen's prize and step 4's are the same figures, written by quest.js from QUEST, and a digit in the
    words sits inside a [data-figure] (mock-figures-come-from-one-model)"""
    page = _open(browser, url, WIDE)
    assert page.evaluate("() => window.QUEST.prizes") == [500000, 250000, 100000]
    assert page.evaluate("() => document.querySelector('#hero .lede').innerText.replace(/\\s+/g, ' ').trim()") == \
        "Win up to 500,000 ET10 every month."
    loose = page.evaluate("""() => { const out = [];
      for (const root of document.querySelectorAll('section [data-glance]')) {
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
    for sel in ("#hero [data-prizes]", "#s4 [data-prizes]"):
        got = page.evaluate(f"() => [...document.querySelectorAll('{sel} .pz b')].map(b => b.textContent)")
        assert got == ["500,000", "250,000", "100,000"], (sel, got)


def test_every_link_goes_to_cymetica(browser, url):
    page = _open(browser, url, WIDE)
    hrefs = page.evaluate("() => [...document.querySelectorAll('a[data-link]')].map(a => a.href)")
    assert hrefs and all(h.startswith("https://cymetica.com/") for h in hrefs), hrefs


def test_the_flight_runs_forward_as_you_scroll(browser, url):
    """through the opening the frame it wants only ever moves forward as the page goes down, ends on the last, and
    something is always drawn: a frame, or the first frame until frames come"""
    page = _open(browser, url, WIDE)
    span = page.evaluate("() => document.getElementById('hero').offsetHeight - innerHeight")
    seen = []
    for k in range(0, 21):
        page.evaluate("(y) => window.scrollTo({ top: y, behavior: 'instant' })", span * k / 20)
        _settle(page)
        seen.append(page.evaluate("() => [QUEST_STATE.frame, QUEST_STATE.drawn]"))
    frames = [f for f, _ in seen]
    assert frames == sorted(frames) and frames[0] == 0, frames
    assert frames[-1] == page.evaluate("() => QUEST.fly.count - 1"), frames
    assert all(d != -1 for _, d in seen[1:]), seen


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
