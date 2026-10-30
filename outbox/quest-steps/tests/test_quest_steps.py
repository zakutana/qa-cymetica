"""The Cymetica Quest, step by step (outbox/quest-steps), checked in a real browser before anybody looks at it.

What the operator asked for, each as a test. Fifth take (2026-10-30): the top bar in Capital Maximizer's style (its
brand, its hexagon rail, a pill); a sharp sky with five small companies floating round the sun, in front of it and
behind it, none bigger than an eighth of it; and a top animation in every step: the office with its astronauts walking,
the arms turning an idea into a product with the pipeline as a skill tree beside them, the Quant Lab breeding the hero
agent, users running from the Promo Market's briefs to the product, the whole Universe with your company climbing the
leaderboard. Kept from the takes before: the first screen as the flyer (board left, words right, held in from the
edges), his words with a green line in each step, no link in a step and two at the end, nothing over 62 % of the
screen, no picture in a box, a rail that always says which step you are on, type big enough to read, the palette,
every figure from one place.

    python -m pytest outbox/quest-steps/tests -o addopts="" -p no:cacheprovider

`-o addopts=""` keeps the repository's report plugin out: this is a page, not a check against the platform, and a run
of it must not write a run record. Needs Playwright's Chromium, and the clips record.py makes (clips/, not in git).
"""
import colorsys
import functools
import http.server
import re
import socket
import threading
import time
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent.parent
WIDE = {"width": 2000, "height": 1100}      # the operator's screenshots are ~2000 px wide
PHONE = {"width": 390, "height": 844}
MIN_PX_WIDE, MIN_PX_PHONE = 20, 16           # "type under ~20 px is moc male" (2026-10-23)
GREEN = "rgb(0, 255, 136)"

# his words, step by step (2026-10-30), the spelling mended: the headline's white, its green, the words under it
WORDS = {
    "s1": ("Start an", "AI-native company.",
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
# what moves in each step ("v kazdem kroku musi byt top animace"): video clips and live animations, by [data-anim]
ANIMS = {"s1": ["office"], "s2": ["workshop", "pipeline"], "s3": ["lab"], "s4": ["farmer", "flow"], "s5": ["universe", "climb"]}


@pytest.fixture(scope="module")
def url():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]

    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass

    class Server(http.server.ThreadingHTTPServer):
        def handle_error(self, request, client_address):
            pass                             # a page closed while a clip was still streaming to it
    server = Server(("127.0.0.1", port), functools.partial(Quiet, directory=str(HERE)))
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
    """five steps, and in each the moving things he named"""
    page = _open(browser, url, WIDE)
    got = page.evaluate("""() => Object.fromEntries([...document.querySelectorAll('section[data-step]')].map(s =>
      [s.id, [...s.querySelectorAll('[data-anim]')].map(e => e.dataset.anim)]))""")
    assert list(got) == ["hero", "s1", "s2", "s3", "s4", "s5", "go"], got
    assert {k: got[k] for k in ANIMS} == ANIMS, got
    assert page.evaluate("() => window.QUEST.steps.length") == 5
    # the casino chip is gone ("uplne trapny"), and so is the podium: step 5 is the whole Universe now
    srcs = page.evaluate("() => [...document.querySelectorAll('img, video')].map(e => e.getAttribute('src') || e.getAttribute('poster') || '')")
    assert not [s for s in srcs if "casino" in s or "podium" in s], srcs


def test_the_words_are_his(browser, url):
    """each step says what he wrote, its headline white with a green part (as cymetica.com/company/app/start); step 1
    no longer says "Let NEXUS run it" ("krok 1 nepis let nexus run it")"""
    page = _open(browser, url, WIDE)
    got = page.evaluate("""() => Object.fromEntries([...document.querySelectorAll('section.step')].map(s => {
      const h = s.querySelector('.copy h2'), g = h && h.querySelector('.g');
      const white = h ? [...h.childNodes].filter(n => !(n.nodeType === 1 && n.classList.contains('g'))).map(n => n.textContent).join('') : '';
      return [s.id, [white, g ? g.textContent : '', (s.querySelector('.copy p') || {}).textContent || '', g ? getComputedStyle(g).color : '']]; }))""")
    for sid, (head, green, words) in WORDS.items():
        h, g, p, colour = got[sid]
        assert (_norm(h), _norm(g), _norm(p)) == (head, green, words), sid
        assert colour == GREEN, (sid, colour)
    assert "NEXUS" not in page.evaluate("() => document.querySelector('#s1').innerText")


def test_no_link_in_a_step_two_at_the_end(browser, url):
    """"prestan davat linky a odkazy do tech kroku, to bude az na konci": no link in any step or on the first screen's
    words, and at the end exactly two, Start your Company and Explore the Universe"""
    page = _open(browser, url, WIDE)
    inside = page.evaluate("() => [...document.querySelectorAll('section.step a, #hero a[data-link], #hero .cta')].map(a => a.textContent.trim())")
    assert not inside, inside
    end = page.evaluate("() => [...document.querySelectorAll('#go a')].map(a => [a.textContent.replace(/\\s+/g, ' ').trim(), a.href])")
    assert end == [["Start your company →", "https://cymetica.com/company/app/builder"],
                   ["Explore the Universe →", "https://cymetica.com/company/app#universe"]], end


def test_the_top_bar_is_capital_maximizers(browser, url):
    """"top panel je pekne trapnej, me se libi styl jak to mame v capital maximizeru": its brand on the left, its rail of
    hexagons joined by fine lines in the middle, a pill on the right; a bar, not a box of glass"""
    page = _open(browser, url, WIDE)
    bar = page.evaluate("""() => { const b = document.getElementById('bar'), r = b.getBoundingClientRect(), cs = getComputedStyle(b);
      const box = e => { const q = b.querySelector(e); if (!q) return null; const x = q.getBoundingClientRect(); return [x.left, x.right]; };
      return { brand: b.querySelector('.brand') ? b.querySelector('.brand').innerText.replace(/\\s+/g, ' ').trim() : '',
               hexes: b.querySelectorAll('#rail [data-step] svg path').length, lines: b.querySelectorAll('#rail i').length,
               pill: b.querySelector('.pill') ? b.querySelector('.pill').innerText.replace(/\\s+/g, ' ').trim() : '',
               b: box('.brand'), r: box('#rail'), p: box('.pill'), radius: parseFloat(cs.borderTopLeftRadius), width: r.width }; }""")
    assert bar["brand"].startswith("CYMETICA QUEST"), bar
    assert bar["hexes"] == 5 and bar["lines"] == 4, bar
    assert bar["pill"] == "UP TO 500,000 ET10 / MONTH", bar
    assert bar["b"][1] <= bar["r"][0] and bar["r"][1] <= bar["p"][0], ("brand, rail, pill, left to right", bar)
    assert bar["radius"] == 0 and bar["width"] >= WIDE["width"] - 1, ("a bar across the top, not a floating panel", bar)


def test_companies_float_round_the_sun(browser, url):
    """"v pozadi u slunce bych chtel videt se vznaset nejake firmy ... pet kolem slunce i pred nim ze ho prekryvaji
    trochu ale nesmi byt moc velke ... 1/8 velikosti slunce max": five, each at most an eighth of the sun's ball, and
    within a few seconds one passes in front of it (over its ball, above it in the stack) and one behind"""
    page = _open(browser, url, WIDE)
    seen = {"front": False, "back": False}
    for _ in range(24):
        r = page.evaluate("""() => { const core = document.querySelector('#sun .core').getBoundingClientRect(), sz = +getComputedStyle(document.querySelector('#sun .ball')).zIndex;
          return { core: core.width, cos: [...document.querySelectorAll('#sun .co')].map(c => { const b = c.getBoundingClientRect();
            const over = b.right > core.left && b.left < core.right && b.bottom > core.top && b.top < core.bottom;
            return [Math.max(b.width, b.height), over, +getComputedStyle(c).zIndex > sz]; }) }; }""")
        assert len(r["cos"]) == 5, r
        assert all(w <= r["core"] / 8 + 0.5 for w, _, _ in r["cos"]), r
        seen["front"] |= any(over and front for _, over, front in r["cos"])
        seen["back"] |= any(not front for _, _, front in r["cos"])
        time.sleep(0.25)
    assert seen["front"] and seen["back"], seen


def test_the_first_screen_is_the_flyer(browser, url):
    """"ta top sklenena tabule vlevo s open slots a napravo ten napis", the words in the start page's type, held in the
    middle of a wide screen, no button"""
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


def test_the_card_is_a_tilted_hologram_in_its_place(browser, url):
    """step 1: the builder's card where the live page puts it over its office (top left, a quarter of the width), "jemne
    holograficky a taky zesikmeny jak je nase sklenena tabule": turned on its left edge like the board, lines of light
    through it"""
    page = _open(browser, url, WIDE)
    _scroll_to_middle_of(page, "s1")
    r = page.evaluate("""() => { const o = document.querySelector('#s1 .crop').getBoundingClientRect(),
      ui = document.querySelector('#s1 .ui'), c = ui.querySelector('img'), b = c.getBoundingClientRect(), cs = getComputedStyle(c);
      return { pos: [(b.left - o.left) / o.width, (b.top - o.top) / o.height, b.width / o.width],
               turn: getComputedStyle(ui).transform, mask: cs.webkitMaskImage || cs.maskImage }; }""")
    assert 0 <= r["pos"][0] < 0.05 and 0 <= r["pos"][1] < 0.06 and 0.18 < r["pos"][2] < 0.28, r
    assert r["turn"].startswith("matrix3d"), ("turned in 3D like the board", r)
    assert "repeating-linear-gradient" in r["mask"], ("scan lines through it", r)


def test_the_pipeline_is_a_skill_tree(browser, url):
    """step 2: "jak jen hodis IDEA do te pipeliny, tam se zpracuje a vyhodi se z toho produkt", as Capital Maximizer's
    skill tree: hexagon nodes joined by lines, an idea in, the three points he named on the way, the product out"""
    page = _open(browser, url, WIDE)
    _scroll_to_middle_of(page, "s2")
    t = page.evaluate("""() => { const p = document.querySelector('#s2 [data-anim=pipeline]');
      return { nodes: [...p.querySelectorAll('.nd')].map(n => n.textContent.replace(/\\s+/g, ' ').trim()), links: p.querySelectorAll('.lk').length,
               hexes: p.querySelectorAll('.nd svg path, svg .hx').length }; }""")
    assert t["nodes"][0].startswith("Idea") and "Yours" in t["nodes"][-1], t
    text = " ".join(t["nodes"])
    for point in ("Production-grade", "Top security", "Deploy", "Hosting"):
        assert point in text, (point, t)
    assert t["links"] >= len(t["nodes"]) - 1 and t["hexes"] >= len(t["nodes"]), t


@pytest.mark.parametrize("sid", list(ANIMS))
def test_every_step_moves(browser, url, sid):
    """"kazdy krok musi mit top animaci": on screen, each step's clips play (their time runs on) and each live animation
    draws frames (QUEST_STATE.frames counts them); a missing clip fails here, so run record.py. This proves it moves, not
    that it is smooth: headless Chromium has no GPU and draws ~10 a second. Smoothness was measured in Chrome with the
    CPU throttled 10x (2026-10-30: every animation 62+ a second, the clips 30, the farmer's dropping ~1 in 9)."""
    page = _open(browser, url, WIDE)
    _scroll_to_middle_of(page, sid)
    page.wait_for_timeout(600)

    def read():
        return page.evaluate("""(sid) => [...document.querySelectorAll('#' + sid + ' [data-anim]')].map(e => [e.dataset.anim,
          e.tagName === 'VIDEO' || e.querySelector('video') ? (() => { const v = e.tagName === 'VIDEO' ? e : [...e.querySelectorAll('video')].find(x => !x.paused) || e.querySelector('video');
            return { t: v.currentTime, ready: v.readyState, paused: v.paused, w: v.videoWidth }; })() : { f: (window.QUEST_STATE.frames || {})[e.dataset.anim] || 0 }])""", sid)
    a = dict(read())
    page.wait_for_timeout(1500)
    b = dict(read())
    for name in ANIMS[sid]:
        if "t" in b[name]:
            assert b[name]["w"] >= 1280 and b[name]["ready"] >= 2 and not b[name]["paused"], (name, b[name])
            assert b[name]["t"] != a[name]["t"], (name, a[name], b[name])
        else:
            assert b[name]["f"] >= a[name]["f"] + 8, (name, a[name], b[name])   # headless, no GPU: ~10 a second
    assert not page.errors, page.errors


def test_nothing_fills_the_screen_and_no_orbit(browser, url):
    """The second take was 4/10: "je to nahovno jak je to pres celou obrazovku" and "nedavej nikde tu obeznou drahu s
    tolika companies". So no picture or clip is wider than 62 % of the screen, and none of that take's shots is back.
    The one exception is his own, 2026-10-30: step 5 shows "cely vesmir viditelny se vsemi companies kolem cymeticy"."""
    page = _open(browser, url, WIDE)
    _scroll_through(page)
    # a clip cut to its stage (step 1's office runs wider than what shows) is measured by what shows
    wide = page.evaluate("""() => [...document.querySelectorAll('main img, main video, main canvas')].map(i => [i.getAttribute('src') || i.getAttribute('poster') || i.tagName,
      +((i.closest('.crop') || i).getBoundingClientRect().width / innerWidth).toFixed(2)]).filter(([, w]) => w > 0.62)""")
    assert not wide, wide
    srcs = page.evaluate("() => [...document.querySelectorAll('img, video, source')].filter(e => !e.closest('#s5')).map(e => e.getAttribute('src') || e.getAttribute('poster') || '')")
    back = [s for s in srcs if any(k in s for k in ("fly", "finale", "tower", "season", "universe"))]
    assert not back, back


def test_a_cut_out_is_clear_at_its_corners(browser, url):
    """the companies round the sun are cut out clean, so no edge of a rectangle can show on the dark"""
    page = _open(browser, url, WIDE)
    page.wait_for_function("[...document.querySelectorAll('#sun .co img')].every(i => i.complete && i.naturalWidth)", timeout=15000)
    corners = page.evaluate("""() => [...document.querySelectorAll('#sun .co img')].map(img => {
      const c = document.createElement('canvas'); c.width = img.naturalWidth; c.height = img.naturalHeight;
      const x = c.getContext('2d'); x.drawImage(img, 0, 0);
      const W = c.width - 1, H = c.height - 1, a = [[0, 0], [W, 0], [0, H], [W, H]].map(([u, v]) => x.getImageData(u, v, 1, 1).data[3]);
      return [img.getAttribute('src'), a]; })""")
    assert len(corners) == 5, corners
    assert all(max(a) <= 40 for _, a in corners), corners


def test_every_picture_loads(browser, url):
    page = _open(browser, url, WIDE)
    _scroll_through(page)
    page.wait_for_function("[...document.images].every(i => i.complete)", timeout=15000)
    broken = page.evaluate("() => [...document.images].filter(i => !i.naturalWidth).map(i => i.currentSrc || i.getAttribute('src'))")
    assert not broken, broken
    clips = page.evaluate("() => [...document.querySelectorAll('video')].map(v => v.querySelector('source') ? v.querySelector('source').getAttribute('src') : v.getAttribute('src'))")
    missing = [c for c in clips if not (HERE / c).exists()]
    assert clips and not missing, f"clips missing (python outbox/quest-steps/record.py): {missing}"
    assert all((HERE / p).exists() for p in page.evaluate("() => [...document.querySelectorAll('video')].map(v => v.getAttribute('poster'))")), "a clip without its poster"
    assert not page.errors, page.errors


@pytest.mark.parametrize("viewport", [WIDE, PHONE], ids=["wide", "phone"])
def test_no_picture_sits_in_a_box(browser, url, viewport):
    """The operator, 2026-10-29: "nedavej ty veci do takovych panelu ... at to splyva prirozene se strankou". So between
    a picture or a clip and its section nothing draws an edge (a border, an outline, a box-shadow, a filled background),
    and every one fades into the page somewhere (a mask on it or on what holds it)."""
    page = _open(browser, url, viewport)
    found = page.evaluate("""() => [...document.querySelectorAll('main section img, main section video, main section canvas')].map(img => {
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
      if (!masked && !img.closest('#hero')) why.push('no fade into the page');
      return [img.getAttribute('src') || img.getAttribute('poster') || img.tagName, why]; }).filter(([, why]) => why.length)""")
    assert not found, found


def test_the_prize_is_500k_a_month_from_one_config(browser, url):
    """the first screen's prize, its board and the bar's pill are the same figures, written by quest.js from QUEST, and
    a digit in the words sits inside a [data-figure] (mock-figures-come-from-one-model)"""
    page = _open(browser, url, WIDE)
    assert page.evaluate("() => window.QUEST.prizes") == [500000, 250000, 100000]
    loose = page.evaluate("""() => { const out = [];
      for (const root of document.querySelectorAll('#bar .pill, #hero .words, #hero .board, section.step .copy, section.step [data-anim=pipeline]')) {
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
    (read-the-vendors-design-rule-before-drawing). The pictures and clips are scenes and their pages, exempt."""
    bad = []
    for name in ("quest.css", "index.html", "quest.js", "anim.js"):
        for text, (r, g, b) in _colours((HERE / name).read_text(encoding="utf-8")):
            h, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
            hue = h * 360
            if s >= 0.18 and 0.12 < l < 0.95:
                if not any(lo <= hue <= hi for lo, hi in ALLOWED_HUES):
                    bad.append((name, text, round(hue)))
            elif 0.2 < l < 0.85 and s < 0.04:
                bad.append((name, text, "plain grey"))
    assert not bad, bad
