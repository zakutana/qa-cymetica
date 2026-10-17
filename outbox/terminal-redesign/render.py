"""Scan index.html for off-palette colours, check every icon draws, then capture each view of the mockup at 1920 and 1440.

The site rule: cyan, green, red and blue (navy tints of them included); no purple, fuchsia, indigo, violet,
magenta, amber, orange, yellow or plain gray. A colour is judged by hue, so a navy shade passes and a gray fails.
"""
import colorsys
import re
from pathlib import Path

from playwright.sync_api import sync_playwright

here = Path(__file__).resolve().parent
src = (here / "index.html").read_text(encoding="utf-8")


def rgb_of(tok):
    if tok.startswith("#"):
        h = tok[1:]
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
    return tuple(int(x) for x in tok.split(","))


bad = []
for tok in set(re.findall(r"#[0-9a-fA-F]{6}\b|(?<=:)#[0-9a-fA-F]{3}\b", src)) | {
        re.sub(r"\s", "", m) for m in re.findall(r"rgba?\(([\d\s]+,[\d\s]+,[\d\s]+),", src)}:
    r, g, b = rgb_of(tok)
    h, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
    deg = h * 360
    if l > .97 or l < .03:  # white text on the red button, black shadows
        continue
    if s < .12:
        bad.append(f"{tok} gray")
    elif not (deg < 12 or deg > 348 or 135 <= deg <= 235):
        bad.append(f"{tok} hue {deg:.0f}")
if bad:
    raise SystemExit("off-palette: " + ", ".join(sorted(bad)))
print("colours ok")

SPILL = """() => { const out = [];
 document.querySelectorAll('.panel, .tile, .hero > div, .knob, .lrow').forEach(c => { const cr = c.getBoundingClientRect();
  if (!cr.width || getComputedStyle(c).visibility === 'hidden') return;
  c.querySelectorAll('*').forEach(e => { const r = e.getBoundingClientRect();
   if (e.children.length === 0 && r.width && (r.right > cr.right + 1 || r.left < cr.left - 1)) out.push('past: ' + (e.textContent.trim() || e.className).slice(0, 30)); }); });
 return [...new Set(out)].slice(0, 12); }"""

# every icon name the page can draw, drawn once, and the ones whose glyph is empty
ICONS = """() => { const names = new Set(); CAT.bots.concat(CAT.algos, CAT.skills).forEach(x => names.add(x.icon));
 document.querySelectorAll('i.fa-solid').forEach(i => i.classList.forEach(c => c.startsWith('fa-') && c !== 'fa-solid' && names.add(c.slice(3))));
 const box = document.createElement('div'); document.body.appendChild(box); const missing = [];
 names.forEach(n => { const i = document.createElement('i'); i.className = 'fa-solid fa-' + n; box.appendChild(i);
  const c = getComputedStyle(i, '::before').content; if (!c || c === 'none' || c === 'normal' || c === '""') missing.push(n); });
 box.remove(); return [names.size, missing]; }"""


def shot(tab, name, w):
    tab.screenshot(path=str(here / f"{name}-{w}.png"), full_page=True)
    print(w, name, tab.evaluate(SPILL))


with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome", args=["--disable-lcd-text", "--font-render-hinting=none"])
    for w, h in ((1920, 1080), (1440, 900)):
        tab = browser.new_page(viewport={"width": w, "height": h})
        tab.goto((here / "index.html").as_uri())
        tab.wait_for_load_state("networkidle")
        tab.wait_for_timeout(900)
        if w == 1920:
            print("icons", tab.evaluate(ICONS))
        shot(tab, "leaderboard", w)
        before = tab.inner_text("#total")
        tab.click(".lrow:nth-child(15) .del")                 # the worst bot
        tab.wait_for_timeout(900)
        print(w, "delete", before, "->", tab.inner_text("#total"), "|", tab.inner_text("#toastMsg"))
        tab.click("#toastBtn")                                 # undo
        tab.wait_for_timeout(800)
        tab.click(".lrow:nth-child(2) .who")                   # the best bot's properties
        tab.wait_for_timeout(500)
        shot(tab, "leaderboard-props", w)
        tab.click("#tabs [data-tab=build]")
        tab.click("#items .item[data-key='Vortex Drain'] [data-add]")
        tab.click("#ltabs [data-lib=algo]")
        tab.click("#items .item[data-key='MACD Crossover'] [data-add]")
        tab.click("#items .item[data-key='Mean Reversion'] [data-add]")
        tab.click("#ltabs [data-lib=skill]")
        tab.click("#items .item[data-key='Stop Loss'] [data-add]")
        tab.click("#items .item[data-key='Headline Sentiment'] [data-add]")
        tab.click("#run")
        tab.wait_for_timeout(1900)
        tab.click("#algoZone .chip[data-key='MACD Crossover']")  # its properties, with parameters to tune
        tab.wait_for_timeout(500)
        shot(tab, "build", w)
        tab.click("#items .item[data-key='Headline Sentiment']")
        tab.wait_for_timeout(400)
        shot(tab, "build-skill", w)
        tab.click("#ix")
        tab.click("#tabs [data-tab=slot]")
        tab.click("#spin")
        tab.wait_for_timeout(2900)
        shot(tab, "slot", w)
        tab.click("#out .recipe .chip.algo")
        tab.wait_for_timeout(500)
        shot(tab, "slot-props", w)
        tab.close()
    browser.close()
