"""The Cymetica Quest, step by step (outbox/quest-steps), checked in a real browser before anybody looks at it.

What the operator asked for, each as a test. Fourth take (2026-10-30): the first screen as our flyer, landscape: its
glass board of open slots on the left, the words on the right in the type of cymetica.com/company/app/start, the sun
behind, nothing from edge to edge and no button; then five steps in his words (start an AI-native company; build
products through the Build it Better pipeline; breed your hero agent; get seen; climb the leaderboard), a green line
in each, no link in any of them; the two links at the very end. Kept from the takes before: nothing over the whole
screen, nowhere the second take's orbit, no picture in a box, every cut-out clear at its corners, a rail that always
says which step you are on, type big enough to read, the site's palette, every figure from one place.

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
MIN_PX_WIDE, MIN_PX_PHONE = 20, 16           # "type under ~20 px is moc male" (2026-10-23)
GREEN = "rgb(0, 255, 136)"

# his words, step by step (2026-10-30), the spelling mended: the headline, its green line, the words under it
WORDS = {
    "s1": ("Start an AI-native company.", "Let NEXUS run it.",
           "Your HQ in the Universe. The pre-build comes with 7 rooms, 4 departments and 9 AI agents."),
    "s2": ("Build products.", "Say what. Own the product.",
           "Send only the spec to Cymetica's pipeline and it does the rest. From start to deployment you do nothing: "
           "you say what to build, and the product is yours."),
    "s3": ("Breed your hero agent.", "Send it to the Agent Casino.",
           "Expert agents in your Quant Lab hunt for the best trading strategies while you sleep. Equip your hero agent "
           "with the most profitable ones and send it to compete against other agents."),
    "s4": ("Get seen.", "Bring in users.",
           "Market your products on the Promo Market to get users, or make them visible in the Universe on your own land."),
    "s5": ("Climb the leaderboard.", "Earn monthly rewards.",
           "Collect points for the users your products bring and for your hero agent's trading. Compete against the "
           "other companies in the Universe, take your slot and stay on top."),
}


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


def _norm(s):
    return re.sub(r"\s+", " ", s.replace(" ", " ")).strip()


def test_the_steps_are_his_in_his_order(browser, url):
    """five steps, each with the pictures he named: the builder's Start as it stands (the office, its card in its own
    place); the robot workshop; the hero agent with the Agent Casino under it; the Promo Market with briefs and the
    Airdrop Farmer close in the Universe; the leaderboard"""
    page = _open(browser, url, WIDE)
    order = page.evaluate("""() => [...document.querySelectorAll('section[data-step]')].map(s =>
      [s.id, [...s.querySelectorAll('img')].map(i => i.getAttribute('src'))])""")
    assert [o[0] for o in order] == ["hero", "s1", "s2", "s3", "s4", "s5", "go"], order
    want = {"s1": ["pics/office.webp", "pics/builder-card.webp"],
            "s2": ["pics/tools.webp"],
            "s3": ["pics/agent.webp", "pics/casino.webp"],
            "s4": ["pics/promo.webp", "pics/farmer.webp"],
            "s5": ["pics/podium.webp", "pics/web-board.webp"]}
    got = {sid: srcs for sid, srcs in order if sid in want}
    assert got == want, got
    assert page.locator(".or").count() == 0, "the steps follow one another now (his 3: breed your hero agent)"
    assert page.evaluate("() => window.QUEST.steps.length") == 5


def test_the_words_are_his(browser, url):
    """each step says what he wrote, its headline white with a green line under it (as cymetica.com/company/app/start)"""
    page = _open(browser, url, WIDE)
    got = page.evaluate("""() => Object.fromEntries([...document.querySelectorAll('section.step')].map(s => {
      const h = s.querySelector('.copy h2'), g = h && h.querySelector('.g');
      const white = h ? [...h.childNodes].filter(n => !(n.nodeType === 1 && n.classList.contains('g'))).map(n => n.textContent).join('') : '';
      return [s.id, [white, g ? g.textContent : '', (s.querySelector('.copy p') || {}).textContent || '', g ? getComputedStyle(g).color : '']]; }))""")
    for sid, (head, green, words) in WORDS.items():
        h, g, p, colour = got[sid]
        assert (_norm(h), _norm(g), _norm(p)) == (head, green, words), sid
        assert colour == GREEN, (sid, colour)


def test_no_link_in_a_step_two_at_the_end(browser, url):
    """"prestan davat linky a odkazy do tech kroku, to bude az na konci": no link in any step or on the first screen's
    words, and at the end exactly two, Start your Company and Explore the Universe"""
    page = _open(browser, url, WIDE)
    inside = page.evaluate("() => [...document.querySelectorAll('section.step a, #hero a[data-link], #hero .cta')].map(a => a.textContent.trim())")
    assert not inside, inside
    end = page.evaluate("() => [...document.querySelectorAll('#go a')].map(a => [a.textContent.replace(/\\s+/g, ' ').trim(), a.href])")
    assert end == [["Start your company →", "https://cymetica.com/company/app/builder"],
                   ["Explore the Universe →", "https://cymetica.com/company/app#universe"]], end


def test_the_first_screen_is_the_flyer(browser, url):
    """"ta top sklenena tabule vlevo s open slots a napravo ten napis", the words in the start page's type, held in the
    middle of a wide screen ("roztahly od kraje obrazovky do kraje" was the fault), no button"""
    page = _open(browser, url, WIDE)
    box = page.evaluate("""() => { const r = e => document.querySelector(e).getBoundingClientRect();
      const b = r('#hero .board'), t = r('#hero .words'), h = document.querySelector('#hero h1'), cs = getComputedStyle(h);
      return { board: [b.left, b.right, b.top, b.bottom], words: [t.left, t.right, t.top, t.bottom],
               h1: h.innerText.replace(/\\s+/g, ' ').trim(), g: (h.querySelector('.g') || {}).innerText, font: cs.fontFamily, colour: cs.color,
               seats: [...document.querySelectorAll('#hero .board .seat')].map(s => s.innerText.replace(/\\s+/g, ' ').trim()) }; }""")
    W = WIDE["width"]
    assert box["board"][1] <= box["words"][0], ("the board stands left of the words", box)
    assert box["board"][0] >= 0.08 * W and box["words"][1] <= 0.92 * W, ("held in from the edges", box)
    assert box["board"][3] <= WIDE["height"] and box["words"][3] <= WIDE["height"], ("all on the first screen", box)
    assert "Archivo Black" in box["font"] and box["colour"] == "rgb(255, 255, 255)", box
    assert box["h1"] == "Join the Cymetica Quest. Win up to 500,000 ET10 every month.", box["h1"]
    assert _norm(box["g"]) == "Win up to 500,000 ET10 every month.", box["g"]
    assert box["seats"] == ["1 ? Open slot could be yours 500,000 ET10", "2 ? Open slot could be yours 250,000 ET10",
                            "3 ? Open slot could be yours 100,000 ET10"], box["seats"]
    assert page.locator("#hero .eng").count() == 0, "the engraved title read as a marketing flyer"


def test_the_card_stands_where_the_builder_puts_it(browser, url):
    """step 1 is the builder's Start "jak tam je defaultne": its card in the top left of the office, at the size the
    live page draws it at 1920 x 1080 (capture.py measures it: 448 px of 1874, 18 px down)"""
    page = _open(browser, url, WIDE)
    _scroll_to_middle_of(page, "s1")
    r = page.evaluate("""() => { const o = document.querySelector('#s1 .pic img').getBoundingClientRect(),
      c = document.querySelector('#s1 .ui img').getBoundingClientRect();
      return [(c.left - o.left) / o.width, (c.top - o.top) / o.height, c.width / o.width]; }""")
    assert 0 <= r[0] < 0.05 and 0 <= r[1] < 0.06 and 0.2 < r[2] < 0.28, r


def test_the_pipeline_is_on_the_picture(browser, url):
    """step 2: "na tom obrazku musi byt hlavni body": the spec in, the Build it Better pipeline with its three points,
    the product yours, laid over the workshop"""
    page = _open(browser, url, WIDE)
    _scroll_to_middle_of(page, "s2")
    got = page.evaluate("""() => { const p = document.querySelector('#s2 .pipe'), i = document.querySelector('#s2 .pic img');
      const a = p.getBoundingClientRect(), b = i.getBoundingClientRect();
      return { text: p.innerText.replace(/\\s+/g, ' ').trim(), over: a.top >= b.top && a.bottom <= b.bottom + 2 && a.left >= b.left - 2 && a.right <= b.right + 2,
               points: [...p.querySelectorAll('.pt li')].map(l => l.textContent.trim()) }; }""")
    assert got["over"], got
    assert got["points"] == ["Production-grade apps", "Top security", "Deployment & hosting"], got
    assert got["text"].startswith("Your spec") and got["text"].endswith("You own it"), got["text"]
    assert "Build it Better pipeline" in got["text"], got["text"]


def test_nothing_fills_the_screen_and_no_orbit(browser, url):
    """The second take was 4/10: "je to nahovno jak je to pres celou obrazovku" and "nedavej nikde tu obeznou drahu s
    tolika companies". So no picture is wider than 62 % of the screen, and none of that take's shots is back (the
    Airdrop Farmer close-up, farmer.webp, is a near camera on two products, capture.py)."""
    page = _open(browser, url, WIDE)
    _scroll_through(page)
    wide = page.evaluate("""() => [...document.querySelectorAll('main img')].map(i => [i.getAttribute('src'), +(i.getBoundingClientRect().width / innerWidth).toFixed(2)])
      .filter(([, w]) => w > 0.62)""")
    assert not wide, wide
    srcs = page.evaluate("() => [...document.images].map(i => i.getAttribute('src'))")
    back = [s for s in srcs if any(k in s for k in ("fly", "finale", "tower", "season", "universe"))]
    assert not back, back


def test_a_cut_out_is_clear_at_its_corners(browser, url):
    """the leaderboard's rows (light) and the Agent Casino (cut out clean) have clear corners, so no edge of a
    rectangle can show on the dark"""
    page = _open(browser, url, WIDE)
    _scroll_through(page)
    page.wait_for_function("[...document.querySelectorAll('.holo img, .cut img')].every(i => i.complete && i.naturalWidth)", timeout=15000)
    corners = page.evaluate("""() => [...document.querySelectorAll('.holo img, .cut img')].map(img => {
      const c = document.createElement('canvas'); c.width = img.naturalWidth; c.height = img.naturalHeight;
      const x = c.getContext('2d'); x.drawImage(img, 0, 0);
      const W = c.width - 1, H = c.height - 1, a = [[0, 0], [W, 0], [0, H], [W, H]].map(([u, v]) => x.getImageData(u, v, 1, 1).data[3]);
      return [img.getAttribute('src'), a]; })""")
    assert len(corners) == 2, corners
    assert all(max(a) <= 40 for _, a in corners), corners


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
    picture fades into the page somewhere (a mask on it or on what holds it). One exception, his own: the builder's
    card in step 1 is their page's panel as it stands (.ui), "jak tam je defaultne"."""
    page = _open(browser, url, viewport)
    found = page.evaluate("""() => [...document.querySelectorAll('main img')].map(img => {
      const why = []; let masked = !!img.closest('.ui');
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
    """the first screen's prize, its board and step 5's podium are the same figures, written by quest.js from QUEST, and
    a digit in the words sits inside a [data-figure] (mock-figures-come-from-one-model)"""
    page = _open(browser, url, WIDE)
    assert page.evaluate("() => window.QUEST.prizes") == [500000, 250000, 100000]
    loose = page.evaluate("""() => { const out = [];
      for (const root of document.querySelectorAll('#hero .words, #hero .board, section.step .copy, section.step .pipe')) {
        const walk = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
        for (let n = walk.nextNode(); n; n = walk.nextNode())
          if (/\\d/.test(n.textContent) && !n.parentElement.closest('[data-figure], .kick, .rk')) out.push(n.textContent.trim());
      } return out; }""")
    assert not loose, f"figures typed outside the config: {loose}"
    wrong = page.evaluate("""() => [...document.querySelectorAll('[data-figure]')].filter(el => {
        const v = el.dataset.figure.split('.').reduce((o, k) => o == null ? o : o[k], window.QUEST);
        const t = typeof v === 'number' ? v.toLocaleString('en-US') : String(v);
        return v == null || el.textContent.trim() !== t; }).map(el => [el.dataset.figure, el.textContent.trim()])""")
    assert not wrong, wrong
    got = page.evaluate("() => [...document.querySelectorAll('#hero .board .pay b')].map(b => b.textContent)")
    assert got == ["500,000", "250,000", "100,000"], got


def test_every_link_goes_to_cymetica(browser, url):
    page = _open(browser, url, WIDE)
    hrefs = page.evaluate("() => [...document.querySelectorAll('a[data-link]')].map(a => a.href)")
    assert hrefs and all(h.startswith("https://cymetica.com/") for h in hrefs), hrefs


@pytest.mark.parametrize("viewport", [WIDE, PHONE], ids=["wide", "phone"])
def test_the_rail_says_which_step_you_are_on(browser, url, viewport):
    page = _open(browser, url, viewport)
    chapters = _chapters(page)
    assert sorted({c[1] for c in chapters}) == [0, 1, 2, 3, 4, 5], chapters
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
    for step in (3, 1, 5, 2, 4):
        page.click(f"#rail [data-step='{step}']")
        page.wait_for_function(f"+document.getElementById('rail').dataset.active === {step}", timeout=5000)


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
