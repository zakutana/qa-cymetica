"""Render lobby.html, table.html, tune.html and join.html (this folder) after a palette scan that refuses any colour
outside the site's palette and the avatar tints their page already uses, and report anything that runs past its
box, any seat label over the pool, and any two race markers that touch."""
import re
from pathlib import Path

from playwright.sync_api import sync_playwright

here = Path(__file__).resolve().parent
PAGES = ("lobby.html", "table.html", "tune.html", "join.html")
ALLOWED = {"#0a0e17", "#06090f", "#0d1520", "#111a28", "#16233a", "#1a2a44", "#1e3050", "#e6edf7", "#a9b8cc",
           "#7f93ad", "#00cfff", "#00ff88", "#ff4444", "#3b82f6", "#7fe6ff", "#66ffb8", "#93c5fd"}
ALLOWED_RGB = {"0,207,255", "0,255,136", "255,68,68", "13,21,32", "59,130,246"}
for name in PAGES:
    src = (here / name).read_text(encoding="utf-8")
    hexes = {h.lower() for h in re.findall(r"#[0-9a-fA-F]{6}\b", src)}
    rgbs = {re.sub(r"\s", "", m) for m in re.findall(r"rgba?\(([\d\s]+,[\d\s]+,[\d\s]+),", src)}
    bad = sorted(hexes - ALLOWED) + sorted(rgbs - ALLOWED_RGB)
    if bad:
        raise SystemExit(f"{name}: off-palette colours {bad}")
print("colours ok")

CHECK = """() => { const out = [];
 const boxes = '.card, .panel, .st, .top, .tr, .rstrip div, .livenote div, .stp div, .tbl, .rec div, .trig div, .lrow, .band, .addr, .modesw, .tabs, pre.api';
 document.querySelectorAll(boxes).forEach(c => { const cr = c.getBoundingClientRect();
  c.querySelectorAll('*').forEach(e => { if (e.closest('svg')) return; const r = e.getBoundingClientRect();
   if (e.children.length === 0 && r.width && (r.right > cr.right + 1 || r.left < cr.left - 1)) out.push('past: ' + e.textContent.trim().slice(0, 30)); });
  if (c.scrollWidth > c.clientWidth + 1) out.push('overflow: ' + c.textContent.trim().slice(0, 30)); });
 document.querySelectorAll('.oval').forEach(o => { const pool = o.querySelector('.pool > div'); if (!pool) return; const pr = pool.getBoundingClientRect();
  o.querySelectorAll('.seat .lbl, .seat .you, .seat .av, .seat .slot').forEach(l => { const r = l.getBoundingClientRect();
   if (r.right > pr.left && r.left < pr.right && r.bottom > pr.top && r.top < pr.bottom) out.push('over pool: ' + l.textContent.trim().slice(0, 20)); });
  const lbls = [...o.querySelectorAll('.seat .lbl')].map(l => l.getBoundingClientRect());
  for (let i = 0; i < lbls.length; i++) for (let j = i + 1; j < lbls.length; j++) { const a = lbls[i], b = lbls[j];
   if (a.right > b.left && a.left < b.right && a.bottom > b.top && a.top < b.bottom) out.push('labels overlap ' + i + '/' + j); } });
 const mk = [...document.querySelectorAll('circle.mk')].map(c => { const r = c.getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2, r.width / 2]; });
 for (let i = 0; i < mk.length; i++) for (let j = i + 1; j < mk.length; j++) { const d = Math.hypot(mk[i][0] - mk[j][0], mk[i][1] - mk[j][1]);
  if (d < mk[i][2] + mk[j][2]) out.push('markers touch ' + i + '/' + j); }
 if (mk.length) out.push('info: ' + mk.length + ' race markers');
 return out.slice(0, 14); }"""

with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome", args=["--disable-lcd-text", "--font-render-hinting=none"])
    for page, name, w, h in (("lobby.html", "lobby-1440", 1440, 900), ("lobby.html", "lobby-1920", 1920, 1080),
                             ("table.html", "table-1440", 1440, 900), ("table.html", "table-1920", 1920, 1080),
                             ("join.html", "join-1440", 1440, 900), ("tune.html", "tune", 1440, 900)):
        tab = browser.new_page(viewport={"width": w, "height": h}, device_scale_factor=2 if name == "tune" else 1)
        tab.goto((here / page).as_uri())
        tab.wait_for_load_state("networkidle")
        tab.wait_for_timeout(1000)
        print(name, "wide" if tab.evaluate("document.documentElement.scrollWidth > window.innerWidth") else "fits",
              "height", tab.evaluate("document.documentElement.scrollHeight"), "problems", tab.evaluate(CHECK))
        if name == "tune":
            tab.locator("#tunepair").screenshot(path=str(here / "tune-1440.png"))
        else:
            tab.screenshot(path=str(here / f"{name}.png"), full_page=True)
        if name == "table-1440":
            tab.close()
            tab = browser.new_page(viewport={"width": w, "height": h}, device_scale_factor=2)
            tab.goto((here / page).as_uri())
            tab.wait_for_load_state("networkidle")
            tab.wait_for_timeout(800)
            tab.locator("section.race").screenshot(path=str(here / "race-1440.png"))
        tab.close()
    browser.close()
print("rendered")
