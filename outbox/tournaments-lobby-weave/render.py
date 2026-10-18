"""Load the live Agent Tournaments pages (cymetica.com, GET), add lobby-weave.css, and save <page>-1440.png and
<page>-1440-top.png beside this file -- each page exactly as they serve it, plus the patch. The fixed Nexus prompt
bar is hidden for the full-page capture only (it would otherwise be painted once mid-page). Also prints, per page,
how far down main the weave reaches and where the page's content starts, so a fade that runs into content shows."""
import re
from pathlib import Path

from playwright.sync_api import sync_playwright

here = Path(__file__).resolve().parent
css = (here / "lobby-weave.css").read_text(encoding="utf-8")
ALLOWED = {"#00ff88"}
ALLOWED_RGB = {"6,9,15", "0,255,136"}
hexes = {h.lower() for h in re.findall(r"#[0-9a-fA-F]{6}\b", css)} | {"#" + h.lower() for h in re.findall(r"%23([0-9a-fA-F]{6})", css)}
rgbs = {re.sub(r"\s", "", m) for m in re.findall(r"rgba?\(([\d\s]+,[\d\s]+,[\d\s]+),", css)}
bad = sorted(hexes - ALLOWED) + sorted(rgbs - ALLOWED_RGB)
if bad:
    raise SystemExit(f"off-palette colours {bad}")
print("colours ok:", sorted(hexes))

PAGES = (("lobby", "", ".at-sec"), ("leaderboard", "/leaderboard", ".at-lbtable"), ("how", "/how", ".at-stakes"))
HIDE_FIXED = """() => { for (const e of document.querySelectorAll('body *')) {
  const cs = getComputedStyle(e); const r = e.getBoundingClientRect();
  if (cs.position === 'fixed' && r.top > 300) e.style.display = 'none'; } }"""
REACH = """(content) => { const m = document.querySelector('main.content-main'); const mr = m.getBoundingClientRect();
  const w = getComputedStyle(m, '::before'); const c = document.querySelector(content);
  return {weave: w.content === 'none' ? 'none' : w.height, contentTop: c ? Math.round(c.getBoundingClientRect().top - mr.top) : null,
          mainTop: Math.round(mr.top + scrollY)}; }"""

with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome", args=["--disable-lcd-text", "--font-render-hinting=none"])
    for name, path, content in PAGES:
        t = b.new_page(viewport={"width": 1440, "height": 900})
        t.goto("https://cymetica.com/agent-tournaments" + path, wait_until="networkidle")
        t.wait_for_timeout(1200)
        t.add_style_tag(content=css)
        t.evaluate(HIDE_FIXED)
        t.wait_for_timeout(400)
        reach = t.evaluate(REACH, content)
        print(name, reach)
        t.screenshot(path=str(here / f"{name}-1440.png"), full_page=True)
        top = reach["mainTop"]
        t.screenshot(path=str(here / f"{name}-1440-top.png"), full_page=True,
                     clip={"x": 0, "y": top, "width": 1440, "height": 1000 if name != "lobby" else 1400})
        t.close()
    b.close()
print("rendered")
