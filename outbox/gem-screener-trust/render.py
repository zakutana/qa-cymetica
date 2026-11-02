"""The pictures for the request, from the running mock (serve.py) with the numbers and the box off, at 1440 px."""
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
URL = "http://127.0.0.1:8803/gem-screener/app"


def clean(page):
    page.add_style_tag(content=".stickytop { position: static !important; }")
    page.evaluate("document.body.classList.add('gt-clean')")


def panel(page, slug, line, out):
    """The panel in the viewport with the changed line centred: a section's own shot breaks under the panel's sticky head."""
    page.goto(f"{URL}?coin={slug}", wait_until="load", timeout=120000)
    page.wait_for_selector("#panel.open", timeout=60000)
    page.wait_for_selector(f"#panel {line}", timeout=30000)
    page.wait_for_timeout(5000)
    clean(page)
    page.evaluate(f"document.querySelector('#panel {line}').scrollIntoView({{block: 'center'}})")
    page.mouse.move(2, 2)
    page.wait_for_timeout(1000)
    page.locator("#panel").screenshot(path=str(HERE / out))


with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome")
    t = b.new_page(viewport={"width": 1440, "height": 1200}, device_scale_factor=2)

    t.goto(URL, wait_until="load", timeout=120000)
    t.wait_for_selector("#startCards .dcard .dc-watch", timeout=90000)
    t.wait_for_timeout(5000)
    clean(t)
    t.evaluate("document.querySelectorAll('#startCards img').forEach(i => i.loading = 'eager')")
    t.wait_for_timeout(2500)
    t.locator("#startCards").screenshot(path=str(HERE / "picture-1-cards.png"))

    near = t.locator("#startNear")
    near.scroll_into_view_if_needed()
    t.evaluate("window.scrollBy(0, 300)")
    t.wait_for_timeout(800)
    t.locator("#startNear .nq-cube", has_text="Nullmask").hover()
    t.wait_for_selector("#gtNearTip:not([hidden])", timeout=10000)
    t.wait_for_timeout(800)
    box = near.bounding_box()
    tip = t.locator("#gtNearTip").bounding_box()
    log = t.locator("#startBtLine").bounding_box()
    top = min(box["y"], tip["y"]) - 12
    bottom = max(log["y"] + log["height"], tip["y"] + tip["height"]) + 12
    t.screenshot(path=str(HERE / "picture-4-near-misses.png"), clip={"x": 20, "y": top, "width": 1400, "height": bottom - top})

    panel(t, "lido", ".gt-hold", "picture-2-holders.png")
    panel(t, "stargate-finance", ".gt-chain", "picture-3-chain.png")
    b.close()
print("rendered")
