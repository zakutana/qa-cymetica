"""Palette scan, icon, spill and JS-error check of the My Balances mockup, then one picture per tab at 1920 and 1440.

The site rule: cyan, green, red and blue (navy tints included); no purple, fuchsia, indigo, violet, magenta, amber,
orange, yellow or plain gray. A colour is judged by hue, so a navy shade passes and a gray fails.
"""
import colorsys
import re
from pathlib import Path

from playwright.sync_api import sync_playwright

here = Path(__file__).resolve().parent
bad = []
for name in ("index.html", "style.css"):
    src = (here / name).read_text(encoding="utf-8")
    toks = set(re.findall(r"#[0-9a-fA-F]{6}\b|(?<=:)#[0-9a-fA-F]{3}\b", src)) | {
        re.sub(r"\s", "", m) for m in re.findall(r"rgba?\(([\d\s]+,[\d\s]+,[\d\s]+),", src)}
    for tok in toks:
        if tok.startswith("#"):
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
 document.querySelectorAll('.panel, .tile, .hero > div, .hr, .tr, .card').forEach(c => { const cr = c.getBoundingClientRect();
  if (!cr.width || getComputedStyle(c).visibility === 'hidden') return;
  c.querySelectorAll('*').forEach(e => { const r = e.getBoundingClientRect();
   if (e.children.length === 0 && r.width && (r.right > cr.right + 1 || r.left < cr.left - 1)) out.push((e.textContent.trim() || e.className).slice(0, 30)); }); });
 return [...new Set(out)].slice(0, 12); }"""
ICONS = """() => { const m = []; document.querySelectorAll('i.fa-solid, i.fa-brands').forEach(i => { const c = getComputedStyle(i, '::before').content;
 if (!c || c === 'none' || c === 'normal' || c === '""') m.push(i.className); }); return [...new Set(m)]; }"""

with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome", args=["--disable-lcd-text", "--font-render-hinting=none"])
    for w, h in ((1920, 1080), (1440, 900)):
        tab = browser.new_page(viewport={"width": w, "height": h})
        errors = []
        tab.on("pageerror", lambda e: errors.append(str(e)))
        tab.goto((here / "index.html").as_uri())
        tab.wait_for_load_state("networkidle")
        tab.wait_for_timeout(900)
        for pane in ("assets", "positions", "activity", "earnings", "account"):
            tab.click(f"#tabs [data-p={pane}]")
            tab.evaluate("window.scrollTo(0, 0)")
            tab.wait_for_timeout(400)
            tab.screenshot(path=str(here / f"{pane}-{w}.png"), full_page=True)
            print(w, pane, "spill", tab.evaluate(SPILL), "icons", tab.evaluate(ICONS))
        print(w, "js errors", errors)
        tab.close()
    browser.close()
