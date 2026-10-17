"""Scan the mockup for off-palette colours, check every icon draws, report spills and JS errors, capture each view.

The site rule: cyan, green, red and blue (navy tints of them included); no purple, fuchsia, indigo, violet,
magenta, amber, orange, yellow or plain gray. A colour is judged by hue, so a navy shade passes and a gray fails.
"""
import colorsys
import re
from pathlib import Path

from playwright.sync_api import sync_playwright

here = Path(__file__).resolve().parent
bad = []
for name in ("index.html", "manage.html", "style.css"):
    src = (here / name).read_text(encoding="utf-8")
    toks = set(re.findall(r"#[0-9a-fA-F]{6}\b|(?<=:)#[0-9a-fA-F]{3}\b", src)) | {
        re.sub(r"\s", "", m) for m in re.findall(r"rgba?\(([\d\s]+,[\d\s]+,[\d\s]+),", src)}
    for tok in toks:
        if tok.startswith("#"):
            h = tok[1:] * (2 if len(tok) == 4 else 1) if len(tok) == 4 else tok[1:]
            h = "".join(c * 2 for c in tok[1:]) if len(tok) == 4 else tok[1:]
            r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
        else:
            r, g, b = (int(x) for x in tok.split(","))
        hue, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
        if l > .97 or l < .03:
            continue
        if s < .12:
            bad.append(f"{name} {tok} gray")
        elif not (hue * 360 < 12 or hue * 360 > 348 or 135 <= hue * 360 <= 235):
            bad.append(f"{name} {tok} hue {hue * 360:.0f}")
if bad:
    raise SystemExit("off-palette: " + ", ".join(sorted(bad)))
print("colours ok")

SPILL = """() => { const out = [];
 document.querySelectorAll('.panel, .tile, .hero > div, .row, .lane, .opt, .knob, .hcard').forEach(c => { const cr = c.getBoundingClientRect();
  if (!cr.width || getComputedStyle(c).visibility === 'hidden') return;
  c.querySelectorAll('*').forEach(e => { const r = e.getBoundingClientRect();
   if (e.children.length === 0 && r.width && (r.right > cr.right + 1 || r.left < cr.left - 1)) out.push((e.textContent.trim() || e.className).slice(0, 30)); }); });
 return [...new Set(out)].slice(0, 12); }"""
ICONS = """() => { const missing = []; document.querySelectorAll('i.fa-solid').forEach(i => { const c = getComputedStyle(i, '::before').content;
 if (!c || c === 'none' || c === 'normal' || c === '""') missing.push(i.className); }); return [...new Set(missing)]; }"""
ALL_ICONS = """() => { const n = new Set(BOTS.map(b => 'fa-solid fa-' + b.icon)); const box = document.createElement('div'); document.body.appendChild(box); const miss = [];
 n.forEach(c => { const i = document.createElement('i'); i.className = c; box.appendChild(i); const v = getComputedStyle(i, '::before').content; if (!v || v === 'none' || v === '""') miss.push(c); });
 box.remove(); return [n.size, miss]; }"""


def shot(tab, name, w, full=True):
    tab.screenshot(path=str(here / f"{name}-{w}.png"), full_page=full)
    print(w, name, "spill", tab.evaluate(SPILL), "icons", tab.evaluate(ICONS))


with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome", args=["--disable-lcd-text", "--font-render-hinting=none"])
    for w, h in ((1920, 1080), (1440, 900)):
        tab = browser.new_page(viewport={"width": w, "height": h})
        errors = []
        tab.on("pageerror", lambda e: errors.append(str(e)))
        tab.goto((here / "index.html").as_uri())
        tab.wait_for_load_state("networkidle")
        tab.wait_for_timeout(900)
        if w == 1920:
            print("bot icons", tab.evaluate(ALL_ICONS))
        shot(tab, "agents", w)
        tab.click(".row[data-id] .who")
        tab.wait_for_timeout(500)
        shot(tab, "agents-side", w, full=False)
        tab.click("#filters [data-f=on]")
        tab.click(".row[data-id] .sw")
        tab.wait_for_timeout(300)
        print(w, "toggle:", tab.inner_text("#toastMsg"))
        tab.click("#filters [data-f=all]")
        tab.click(".row:nth-child(3) [data-menu]")
        tab.click(".menu.on [data-fund]")
        tab.wait_for_timeout(300)
        shot(tab, "agents-fund", w, full=False)
        tab.click("#fundNo")
        tab.goto((here / "manage.html").as_uri() + "?id=862f0418-0c04-4ba3-869a-98b8ff9a5bd6")
        tab.wait_for_load_state("networkidle")
        tab.wait_for_timeout(700)
        tab.click("[data-lt=cards]")
        tab.click("[data-lt=catalog]")
        shot(tab, "manage-markets", w)
        tab.click("#tabs [data-p=risk]")
        tab.click("[data-opt=oTf]")
        tab.click("[data-mop='3']")
        shot(tab, "manage-risk", w)
        tab.click("#tabs [data-p=strategy]")
        tab.click("[data-rule=helix]")
        shot(tab, "manage-strategy", w)
        tab.click("#tabs [data-p=advanced]")
        tab.click("#gn .sw")
        shot(tab, "manage-advanced", w)
        print(w, "js errors", errors)
        tab.close()
    browser.close()
