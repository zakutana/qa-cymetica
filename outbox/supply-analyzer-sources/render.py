"""Picture 1: their live Apps table with patch.js inside their page script. GET only; nothing is sent."""
from pathlib import Path

import httpx
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
URL = "https://cymetica.com/gem-screener/app?view=apps"
GO = "/* ================= go ================= */"
CSS = ".gt-unknown { display: inline-block; width: 22px; height: 22px; border-radius: 50%; border: 1.5px dashed var(--muted, #7f93ad); vertical-align: middle; box-sizing: border-box; }"

html = httpx.get(URL, timeout=120, follow_redirects=True).text
if GO not in html:
    raise SystemExit("their page script has moved")
html = html.replace(GO, (HERE / "patch.js").read_text(encoding="utf-8") + "\n" + GO, 1)
html = html.replace("<head>", "<head><script>window.WebSocket = undefined;</script>", 1)

with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome")
    t = b.new_page(viewport={"width": 1440, "height": 1300}, device_scale_factor=2)
    t.route(URL, lambda r: r.fulfill(status=200, content_type="text/html; charset=utf-8", body=html))
    t.goto(URL, wait_until="load", timeout=120000)
    t.wait_for_selector("#tbl-apps tbody tr", timeout=60000)
    t.wait_for_function("() => [...document.querySelectorAll('#tbl-apps .supcell .spn')].some(e => /%/.test(e.textContent))", timeout=90000)
    t.add_style_tag(content=CSS + " .stickytop { position: static !important; }")
    t.wait_for_timeout(3000)
    table = t.locator("#tbl-apps")
    table.scroll_into_view_if_needed()
    cell = t.locator("#tbl-apps tbody tr .supcell.v-na").first
    cell.hover()
    t.wait_for_timeout(900)
    box = table.bounding_box()
    t.screenshot(path=str(HERE / "picture-1-supply-column.png"), clip={"x": box["x"], "y": max(0, box["y"]), "width": min(box["width"], 1400), "height": min(1180, 1300 - max(0, box["y"]))})
    print(t.evaluate("[...document.querySelectorAll('#tbl-apps tbody tr')].slice(0,14).map(r => (r.querySelector('.nm')||{}).innerText + ': ' + (r.querySelector('.supcell .spn')||{}).innerText).join(' | ')"))
    b.close()
print("rendered")
