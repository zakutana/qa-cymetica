"""Picture 1, from the running mock (serve.py) with the numbers and the box off, at 1440 px."""
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
URL = "http://127.0.0.1:8804/gem-screener/app?view=apps"

with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome")
    t = b.new_page(viewport={"width": 1600, "height": 1300}, device_scale_factor=2)
    t.goto(URL, wait_until="load", timeout=120000)
    t.wait_for_selector("#tbl-apps tbody tr", timeout=60000)
    t.wait_for_function("() => [...document.querySelectorAll('#tbl-apps .supcell .spn')].some(e => /%/.test(e.textContent))", timeout=90000)
    t.add_style_tag(content=".stickytop { position: static !important; }")
    t.evaluate("document.body.classList.add('gt-clean')")
    t.wait_for_timeout(3000)
    table = t.locator("#tbl-apps")
    table.scroll_into_view_if_needed()
    t.locator("#tbl-apps tbody tr .supcell.v-na").first.hover()
    t.wait_for_timeout(900)
    box = table.bounding_box()
    t.screenshot(path=str(HERE / "picture-1-supply-column.png"), clip={"x": box["x"], "y": max(0, box["y"]), "width": min(box["width"], 1560), "height": min(1180, 1300 - max(0, box["y"]))})
    print(t.evaluate("[document.getElementById('tbl-apps').scrollWidth, document.getElementById('tbl-apps').parentElement.clientWidth, [...document.querySelectorAll('#tbl-apps thead th')].map(h => h.innerText.replace(/\\s+/g, ' ').trim() + ' ' + Math.round(h.getBoundingClientRect().width)).join(' | ')]"))

    t.goto("http://127.0.0.1:8804/gem-screener/app?coin=up", wait_until="load", timeout=120000)
    t.wait_for_selector("#panel .sa-pie", timeout=90000)
    t.wait_for_timeout(1500)
    t.add_style_tag(content=".stickytop { position: static !important; }")
    t.evaluate("document.body.classList.add('gt-clean'); document.querySelector('#supplyCard').scrollIntoView({block: 'center'})")
    t.mouse.move(2, 2)
    t.wait_for_timeout(1000)
    t.locator("#supplyCard").screenshot(path=str(HERE / "picture-2-supply-card.png"))
    b.close()
print("rendered")
