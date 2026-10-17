"""Scan index.html for off-palette colours, then capture every view of the terminal mockup at 1920 and 1440.

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
 document.querySelectorAll('.panel, .tile, .hero > div, .knob, .chip, .lrow').forEach(c => { const cr = c.getBoundingClientRect();
  if (!cr.width) return;
  c.querySelectorAll('*').forEach(e => { const r = e.getBoundingClientRect();
   if (e.children.length === 0 && r.width && (r.right > cr.right + 1 || r.left < cr.left - 1)) out.push('past: ' + e.textContent.trim().slice(0, 30)); }); });
 return [...new Set(out)].slice(0, 12); }"""

with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome", args=["--disable-lcd-text", "--font-render-hinting=none"])
    for w, h in ((1920, 1080), (1440, 900)):
        tab = browser.new_page(viewport={"width": w, "height": h})
        tab.goto((here / "index.html").as_uri())
        tab.wait_for_load_state("networkidle")
        tab.wait_for_timeout(900)
        tab.screenshot(path=str(here / f"leaderboard-{w}.png"), full_page=True)
        print(w, "leaderboard", tab.evaluate(SPILL))
        before = tab.inner_text("#total")
        tab.click(".lrow:nth-child(15) .del")                 # the worst bot
        tab.wait_for_timeout(900)
        print(w, "delete", before, "->", tab.inner_text("#total"), "|", tab.inner_text("#toastMsg"))
        tab.screenshot(path=str(here / f"deleted-{w}.png"))
        tab.click("#toastBtn")                                 # undo
        tab.wait_for_timeout(800)
        tab.click("#tabs [data-tab=build]")
        tab.click("#items .item:nth-child(13)")          # Vortex Drain
        tab.click("#ltabs [data-lib=algo]")
        tab.click("#items .item:nth-child(1)")
        tab.click("#items .item:nth-child(6)")
        tab.click("#ltabs [data-lib=skill]")
        tab.click("#items .item:nth-child(1)")
        tab.click("#items .item:nth-child(4)")
        tab.click("#items .item:nth-child(20)")
        tab.click("#run")
        tab.wait_for_timeout(1900)
        tab.screenshot(path=str(here / f"build-{w}.png"), full_page=True)
        print(w, "build", tab.evaluate(SPILL))
        tab.click("#tabs [data-tab=slot]")
        tab.click("#spin")
        tab.wait_for_timeout(2900)
        tab.screenshot(path=str(here / f"slot-{w}.png"), full_page=True)
        print(w, "slot", tab.evaluate(SPILL))
        tab.close()
    browser.close()
