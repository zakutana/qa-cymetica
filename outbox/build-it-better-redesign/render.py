"""Check the Build it Better redesign against the live page it replaces, then picture it.

The operator, 2026-10-22: a new design for /build-it-better, functionality unchanged, and on arrival a comparison of vibe
coding against Build it Better. So what has to hold, before any picture is worth showing:

1. The page's own script (live-2026-10-22.html) is in index.html byte for byte: the logic is theirs, untouched.
2. Every element that script looks up by id is in the new markup exactly once, and the structures it queries
   (#bb-board .bb-col[data-stage] > h3 .c + .list, #bb-closed .c + .list, #bb-gate's two data-i18n spans) are there.
3. Every data-i18n key of the live page is kept, on the same text; no new key is invented (a key their bundle does not
   have would be overwritten or blanked by i18n.js on cymetica.com, so new copy carries none).
4. Every class the script creates has a rule in bib.css.
5. Palette: cyan, green, red, blue and navy tints only (the site's rule: no orange, yellow, purple or plain gray).
6. Rendered through serve.py: no error from the page script, no horizontal scroll at 1920, 1440 or 390, the board filled,
   and the comparison inside the first screen at 1920 x 1080 (above the site's fixed chat bar, not the window's edge).
8. The board card is the one function of their script replaced (card.js, "tady mi prijde ze pouzivas porad stary design
   jejich"), so its duties are checked here: every card links its ticket and the link opens it in #bb-mine; every
   shipped card with a page links it; every traffic line links /build-it-better/stats?app=; shipped cards carry a preview.
7. The catalog the operator asked for the same day ("katalog ze klikam doprava a doleva uz buildnutych apek ... serazenych
   podle nejvic views a navstevniku"): cards from /apps/leaderboard, in descending views, re-sorted by visitors on the
   toggle, and the right arrow moves the row while the left one starts disabled.
"""
import colorsys
import re
import sys
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

here = Path(__file__).resolve().parent
sys.path.insert(0, str(here))
import serve  # noqa: E402

live = (here / "live-2026-10-22.html").read_text(encoding="utf-8")
page = (here / "index.html").read_text(encoding="utf-8")
frag = (here / "bib.html").read_text(encoding="utf-8")
css = (here / "bib.css").read_text(encoding="utf-8")
fails = []


def page_script(src):
    m = re.search(r"<script[^>]*>\s*\(function \(\) \{\s*'use strict';\s*var API = '/api/v1/build-it-better';.*?</script>", src, re.S)
    return m.group(0) if m else None


def bb_block(src):
    i = src.find('<div class="bb-page">')
    return src[i:src.find("<script", i)]


# 1. the logic is theirs: byte for byte, except card(b), which card.js replaces (its links are checked in the browser, 8)
THEIR_CARD = re.compile(r"        function card\(b\) \{\n.*?\n        \}\n", re.S)
OUR_CARD = re.compile(r"        // ── board card, redesigned.*?// ── end of the board card ─+\n", re.S)
if not page_script(live):
    fails.append("1: the page script is not where it was in the live copy")
elif THEIR_CARD.sub("", page_script(live), count=1) != OUR_CARD.sub("", page_script(page) or "", count=1):
    fails.append("1: the page script differs from the live one outside card(b)")

# 2. ids and queried structure (the DOM half is checked in the browser below)
script = page_script(live) or ""
ids = sorted(set(re.findall(r"\$\('([\w-]+)'\)", script)) | set(re.findall(r"getElementById\('([\w-]+)'\)", script)))
new = bb_block(page)
for i in ids:
    n = len(re.findall(r'\bid="' + re.escape(i) + '"', new))
    if n != 1:
        fails.append(f"2: #{i} is in the new markup {n} times")

# 3. i18n keys and their text
def keyed(src):
    return {(k, re.sub(r"\s+", " ", t).strip()) for k, t in re.findall(r'data-i18n="([\w.]+)"[^>]*>([^<]*)<', src)}

old_k, new_k = keyed(bb_block(live)), keyed(new)
for k, t in sorted(old_k - new_k):
    fails.append(f"3: {k} lost or reworded ({t[:50]!r})")
for k, t in sorted(new_k - old_k):
    fails.append(f"3: {k} is new or changed ({t[:50]!r})")

# 4. CSS for what the script creates
for sel in (".bb-card", ".bb-card .t", ".bb-card .n", ".bb-card .w", ".bb-card .m", ".bb-card .pv", ".bb-card .tr", ".bb-bar.late",
            ".bb-pill.pos", ".bb-pill.neg", ".bb-empty",
            ".bb-card.flash", ".bb-showall.on", ".bb-thumb.load", ".bb-thumb .x", ".bb-msg.ok", ".bb-msg.err", ".bb-suggest a",
            ".bb-suggest small", ".bb-live.on i", ".bb-closed .row", ".bb-mode.on", ".bb-drop.over"):
    if sel not in css:
        fails.append(f"4: no rule for {sel}")

# 5. palette
for name, src in (("bib.css", css), ("bib.html", frag)):
    toks = set(re.findall(r"#[0-9a-fA-F]{6}\b|(?<=[:\s\"'])#[0-9a-fA-F]{3}\b", src)) | {
        re.sub(r"\s", "", m) for m in re.findall(r"rgba?\(([\d\s]+,[\d\s]+,[\d\s]+)[,)]", src)}
    for tok in toks:
        if tok.startswith("#"):
            h = "".join(c * 2 for c in tok[1:]) if len(tok) == 4 else tok[1:]
            r, g, b = (int(h[k:k + 2], 16) for k in (0, 2, 4))
        else:
            r, g, b = (int(x) for x in tok.split(","))
        hue, light, sat = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
        if light > .97 or light < .03:
            continue
        if sat < .12:
            fails.append(f"5: {name} {tok} is gray")
        elif not (hue * 360 < 12 or hue * 360 > 348 or 135 <= hue * 360 <= 235):
            fails.append(f"5: {name} {tok} hue {hue * 360:.0f}")

# 6. in the browser
DOM = """() => {
 const out = [];
 const cols = [...document.querySelectorAll('#bb-board .bb-col')];
 if (cols.map(c => c.dataset.stage).join() !== 'requested,funded,building,shipped') out.push('board columns ' + cols.map(c => c.dataset.stage));
 cols.forEach(c => { if (!c.querySelector('h3 .c') || !c.querySelector('.list')) out.push('column ' + c.dataset.stage + ' lacks .c or .list'); });
 const cl = document.getElementById('bb-closed');
 if (!cl || !cl.querySelector('.c') || !cl.querySelector('.list')) out.push('#bb-closed lacks .c or .list');
 if (!document.querySelector('#bb-gate [data-i18n="build_it_better.gate_line_plans"]') || !document.querySelector('#bb-gate [data-i18n="build_it_better.see_usage"]')) out.push('#bb-gate spans');
 const shipped = document.querySelectorAll('#bb-board [data-stage="shipped"] .bb-card').length;
 if (!shipped) out.push('the board is empty');
 if (document.getElementById('bs-shipped').textContent.trim() === '–') out.push('stats not filled');
 return out; }"""
SPILL = """() => document.documentElement.scrollWidth > window.innerWidth + 1"""
FIRST = """() => { const v = document.querySelector('.bb-vs').getBoundingClientRect();
 let floor = innerHeight;   // the site's fixed bottom bar covers the window's last ~60 px
 document.querySelectorAll('body *').forEach(e => { const s = getComputedStyle(e); if (s.position !== 'fixed' || s.display === 'none' || s.visibility === 'hidden') return;
   const r = e.getBoundingClientRect(); if (r.height && r.width > innerWidth / 2 && r.bottom >= innerHeight - 2 && r.top > innerHeight / 2) floor = Math.min(floor, r.top); });
 return [Math.round(v.top), Math.round(v.bottom), Math.round(floor)]; }"""
CAT = """() => [...document.querySelectorAll('#bb-cat-track .cat-card')].map(c => [c.dataset.views, c.dataset.visitors].map(Number))"""
CARDS = """() => { const out = [];
 document.querySelectorAll('#bb-board .bb-card').forEach(c => { const tk = c.id.replace('bbc-', '');
  if (!c.querySelector('a[href="?t=' + encodeURIComponent(tk) + '"]')) out.push(tk + ': no ticket link');
  if (c.classList.contains('shipped') && !c.querySelector('.pv')) out.push(tk + ': no preview');
  if (c.classList.contains('shipped') && c.querySelector('.pv a, a.pv') && !c.querySelector('a.open')) out.push(tk + ': no open link');
  c.querySelectorAll('a.tr').forEach(a => { if (!a.getAttribute('href').startsWith('/build-it-better/stats?app=')) out.push(tk + ': traffic link ' + a.getAttribute('href')); }); });
 return out; }"""
CAT_NAV = """async () => { const t = document.getElementById('bb-cat-track'), prev = document.getElementById('bb-cat-prev'), next = document.getElementById('bb-cat-next');
 const before = t.scrollLeft, prevOff = prev.disabled; next.click(); await new Promise(r => setTimeout(r, 900));
 return [prevOff, t.scrollLeft > before, prev.disabled]; }"""

srv = serve.make(0)
port = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()
url = f"http://127.0.0.1:{port}/build-it-better"
dirs = [a for a in sys.argv[1:] if not a.startswith("--")]   # serve's --quiet is read from argv too
shots = Path(dirs[0]) if dirs else here
with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome", args=["--disable-lcd-text", "--font-render-hinting=none"])
    for w, h, full in ((1920, 1080, False), (1440, 900, True), (390, 844, True)):
        t = b.new_page(viewport={"width": w, "height": h})
        errs = []
        t.on("pageerror", lambda e, errs=errs: errs.append(str(e)))
        t.goto(url)
        t.wait_for_selector("#bb-board .bb-card", timeout=20000)
        t.wait_for_timeout(1500)
        for e in errs:
            if "build-it-better" in e or "bb-" in e:
                fails.append(f"6: {w}: page error {e[:120]}")
        if t.evaluate(SPILL):
            fails.append(f"6: {w}: scrolls sideways")
        fails += [f"6: {w}: {x}" for x in t.evaluate(DOM)]
        top, bottom, floor = t.evaluate(FIRST)
        print(f"{w}x{h}: comparison {top}..{bottom} px (bar at {floor}), page {t.evaluate('document.documentElement.scrollHeight')} px, other page errors {len(errs)}")
        if w == 1920 and bottom > floor:
            fails.append(f"6: at 1920x1080 the comparison ends at {bottom} px, under the fixed bar at {floor}")
        t.wait_for_selector("#bb-cat-track .cat-card", timeout=20000)
        views = t.evaluate(CAT)
        if len(views) < 10 or [v for v, _ in views] != sorted((v for v, _ in views), reverse=True):
            fails.append(f"7: {w}: {len(views)} catalog cards, not in descending views")
        if w == 1920:
            t.click("#bb-cat-sort [data-sort='visitors']")
            t.wait_for_function("document.querySelector('#bb-cat-sort [data-sort=visitors]').getAttribute('aria-pressed') === 'true' && !document.getElementById('bb-cat-track').classList.contains('loading')")
            vis = [v for _, v in t.evaluate(CAT)]
            if len(vis) < 10 or vis != sorted(vis, reverse=True):
                fails.append("7: the visitors toggle does not sort by visitors")
            t.click("#bb-cat-sort [data-sort='views']")
            t.wait_for_function("document.querySelector('#bb-cat-sort [data-sort=views]').getAttribute('aria-pressed') === 'true' && !document.getElementById('bb-cat-track').classList.contains('loading')")
            prev_off, moved, prev_after = t.evaluate(CAT_NAV)
            if not (prev_off and moved and not prev_after):
                fails.append(f"7: arrows: left disabled at start {prev_off}, right moves the row {moved}, left enabled after {not prev_after}")
            fails += [f"8: {x}" for x in t.evaluate(CARDS)]
            first = t.evaluate("document.querySelector('#bb-board [data-stage=shipped] .bb-card .tk').textContent")
            t.click("#bb-board [data-stage=shipped] .bb-card .tk")
            try:   # the ticket is read live from cymetica.com through serve.py: wait for it, up to 10 s, not a fixed beat
                t.wait_for_function("(tk) => getComputedStyle(document.getElementById('bb-mine')).display !== 'none' && document.getElementById('bb-mine-ticket').textContent.startsWith(tk)", arg=first, timeout=10000)
            except Exception:
                fails.append(f"8: clicking {first} did not open it in #bb-mine within 10 s")
            t.evaluate("document.getElementById('bb-cat-track').scrollLeft = 0")
            t.wait_for_timeout(600)
            t.screenshot(path=str(shots / "catalog-1920.png"), full_page=True,
                         clip={"x": 0, "y": t.evaluate("document.querySelector('.bb-cat').getBoundingClientRect().top + scrollY") - 20, "width": 1920, "height": 460})
            t.evaluate("window.scrollTo(0, 0)")
            t.wait_for_timeout(400)
        # a full-page capture never scrolls, so lazy pictures below the fold would stay unloaded in it; only the board's
        # (forcing all 130 catalog pictures too queues the board's behind them, six connections at a time)
        t.evaluate("document.querySelectorAll('#bb-board img[loading=lazy]').forEach(i => i.loading = 'eager')")
        t.wait_for_timeout(2500)
        name = {1920: "first-screen-1920.png", 1440: "page-1440.png", 390: "phone-390.png"}[w]
        t.screenshot(path=str(shots / name), full_page=full)
        t.close()
    b.close()
srv.shutdown()

print(f"{len(ids)} ids, {len(old_k)} i18n keys, script {'identical outside card(b)' if not any(f.startswith('1') for f in fails) else 'DIFFERS'}")
if fails:
    print("\n".join(fails))
    raise SystemExit(f"{len(fails)} problem(s)")
print("all checks hold")
