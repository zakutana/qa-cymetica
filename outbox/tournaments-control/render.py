"""Render table.html and lobby.html (this folder) after a scan that refuses any colour outside the site's
palette and the avatar tints their page already uses."""
import re
from pathlib import Path

from playwright.sync_api import sync_playwright

here = Path(__file__).resolve().parent
ALLOWED = {"#0a0e17", "#06090f", "#0d1520", "#111a28", "#16233a", "#1a2a44", "#1e3050", "#e6edf7", "#a9b8cc",
           "#7f93ad", "#00cfff", "#00ff88", "#ff4444", "#3b82f6", "#7fe6ff", "#66ffb8", "#93c5fd"}
ALLOWED_RGB = {"0,207,255", "0,255,136", "255,68,68", "6,9,15", "13,21,32"}
for name in ("table.html", "lobby.html"):
    src = (here / name).read_text(encoding="utf-8")
    hexes = {h.lower() for h in re.findall(r"#[0-9a-fA-F]{6}\b", src)}
    rgbs = {re.sub(r"\s", "", m) for m in re.findall(r"rgba?\(([\d\s]+,[\d\s]+,[\d\s]+),", src)}
    bad = sorted(hexes - ALLOWED) + sorted(rgbs - ALLOWED_RGB)
    if bad:
        raise SystemExit(f"{name}: off-palette colours {bad}")
print("colours ok")

SHOTS = (("table-1920", "table.html", 1920, 1080, False), ("table-1440", "table.html", 1440, 900, False),
         ("table-390", "table.html", 390, 844, True), ("lobby-1920", "lobby.html", 1920, 1080, False),
         ("lobby-1440", "lobby.html", 1440, 900, False), ("lobby-390", "lobby.html", 390, 844, True))
with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome", args=["--disable-lcd-text", "--font-render-hinting=none"])
    for name, page, w, h, mobile in SHOTS:
        tab = browser.new_page(viewport={"width": w, "height": h}, device_scale_factor=2 if mobile else 1,
                               is_mobile=mobile, has_touch=mobile)
        tab.goto((here / page).as_uri())
        tab.wait_for_load_state("networkidle")
        tab.wait_for_timeout(500)
        wide = tab.evaluate("document.documentElement.scrollWidth > window.innerWidth")
        tall = tab.evaluate("document.documentElement.scrollHeight")
        spill = tab.evaluate("""() => { const out = []; document.querySelectorAll('.tc, .oc, .ta, .st, .box, .panel').forEach(c => {
            const cr = c.getBoundingClientRect(); c.querySelectorAll('*').forEach(e => { const r = e.getBoundingClientRect();
            if (e.children.length === 0 && r.width && r.right > cr.right + 1) out.push(e.textContent.trim().slice(0, 30)); }); });
            return out.slice(0, 8); }""")
        print(name, "wide" if wide else "fits", "height", tall, "spills", spill)
        tab.screenshot(path=str(here / f"{name}.png"), full_page=mobile or tall <= h + 2)
        tab.close()
    browser.close()
print("rendered")
