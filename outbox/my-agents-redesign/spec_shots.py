"""The six pictures for the Build it Better request, at 1440 px like ET-31459's, into spec/ beside this file.

The MOCKUP tag in the top bar is hidden: the pictures show the page as it would be.
"""
from pathlib import Path

from playwright.sync_api import sync_playwright

here = Path(__file__).resolve().parent
out = here / "spec"
out.mkdir(exist_ok=True)
HIDE = ".mock{display:none!important}"
MANAGE = (here / "manage.html").as_uri() + "?id=862f0418-0c04-4ba3-869a-98b8ff9a5bd6"


def snap(tab, name):
    """Back to the top (a click scrolls, and the sticky bar then lands mid-picture) and past the switch animation."""
    tab.evaluate("window.scrollTo(0, 0)")
    tab.wait_for_timeout(500)
    tab.screenshot(path=str(out / name), full_page=True)


def page(browser, url, h=900):
    tab = browser.new_page(viewport={"width": 1440, "height": h})
    tab.goto(url)
    tab.wait_for_load_state("networkidle")
    tab.add_style_tag(content=HIDE)
    tab.wait_for_timeout(900)
    return tab


with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome", args=["--disable-lcd-text", "--font-render-hinting=none"])
    tab = page(browser, (here / "index.html").as_uri())
    tab.screenshot(path=str(out / "1-my-agents.png"), full_page=True, clip={"x": 0, "y": 0, "width": 1440, "height": 1330})
    tab.close()

    tab = page(browser, (here / "index.html").as_uri(), h=1150)
    tab.click(".row[data-id] .who")                     # the best bot, paused by its stop-loss
    tab.wait_for_timeout(600)
    tab.screenshot(path=str(out / "2-my-agents-bot-panel.png"))
    tab.close()

    tab = page(browser, MANAGE)
    tab.click("[data-lt=cards]")
    tab.click("[data-lt=catalog]")
    snap(tab, "3-manage-markets.png")
    tab.click("#tabs [data-p=risk]")
    tab.click("[data-opt=oTf]")
    snap(tab, "4-manage-risk.png")
    tab.click("#tabs [data-p=strategy]")
    snap(tab, "5-manage-strategy.png")
    tab.click("#tabs [data-p=advanced]")
    tab.click("#gn .sw")
    snap(tab, "6-manage-advanced.png")
    tab.close()
    browser.close()
for f in sorted(out.glob("*.png")):
    print(f.name, f.stat().st_size // 1024, "KB")
