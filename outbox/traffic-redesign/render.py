"""Check the /traffic mockup, then picture it.

1. Palette scan: cyan, green, red, blue (navy tints included); no purple, orange, yellow or plain gray.
2. Every list that claims to add up to a tile does, read off the rendered page (not off data.js).
3. No JS errors, nothing wider than the window; one full-page picture per page at 1440.
"""
import colorsys
import re
import subprocess
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

here = Path(__file__).resolve().parent
subprocess.run([sys.executable, str(here / "make_data.py")], check=True)

bad = []
for name in ("style.css", "app.js", "index.html", "mine.html"):
    src = (here / name).read_text(encoding="utf-8")
    toks = set(re.findall(r"#[0-9a-fA-F]{6}\b", src)) | {
        re.sub(r"\s", "", m) for m in re.findall(r"rgba?\(([\d\s]+,[\d\s]+,[\d\s]+),", src)}
    for tok in toks:
        if tok.startswith("#"):
            r, g, b = (int(tok[i:i + 2], 16) for i in (1, 3, 5))
        else:
            r, g, b = (int(x) for x in tok.split(","))
        hue, light, sat = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
        if light > .97 or light < .03:
            continue
        if sat < .12:
            bad.append(f"{name} {tok} gray")
        elif not (hue * 360 < 12 or hue * 360 > 348 or 135 <= hue * 360 <= 235):
            bad.append(f"{name} {tok} hue {hue * 360:.0f}")
if bad:
    raise SystemExit("off-palette: " + ", ".join(sorted(bad)))
print("colours ok")

SUMS = """() => {
  const num = s => +String(s).replace(/[^0-9]/g, '');
  const out = [];
  document.querySelectorAll('.rows').forEach((list, i) => {
    const rows = [...list.querySelectorAll('.row:not(.head):not(.sum):not(.gap)')].map(r => num(r.querySelector('.val').textContent));
    const total = num(list.querySelector('.row.sum .val').textContent);
    out.push({i, title: list.closest('.card').querySelector('h3').textContent.trim().slice(0, 40), rows: rows.reduce((a, b) => a + b, 0), total});
  });
  return {out, wide: document.documentElement.scrollWidth > window.innerWidth};
}"""

errors = []
with sync_playwright() as p:
    browser = p.chromium.launch()
    for page_name, html in (("site", "index.html"), ("mine", "mine.html")):
        page = browser.new_page(viewport={"width": 1440, "height": 900}, device_scale_factor=1)
        page.on("pageerror", lambda e: errors.append(f"{page_name}: {e}"))
        page.goto((here / html).as_uri())
        page.wait_for_timeout(1200)
        got = page.evaluate(SUMS)
        for s in got["out"]:
            flag = "ok" if s["rows"] == s["total"] else "MISMATCH"
            print(f"{page_name} list {s['i']} {s['title']!r}: rows {s['rows']:,} total {s['total']:,} {flag}")
            if flag != "ok":
                errors.append(f"{page_name}: list {s['title']} rows {s['rows']} != {s['total']}")
        if got["wide"]:
            errors.append(f"{page_name}: wider than the window")
        page.screenshot(path=str(here / f"{page_name}-1440.png"), full_page=True)
    browser.close()
if errors:
    raise SystemExit("\n".join(errors))
print("pictures: site-1440.png, mine-1440.png")
