"""Pictures of the mirror (index.html), served at http://localhost:8796/mirror/: their page today (?live=1) and
with our patch, the Farms tab's plan panel, the Coming soon rows and the Live farms tab, at 1440 px.
Needs the local server (launch.json "airdrop-farms-mock")."""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

here = Path(__file__).resolve().parent
out = here / "pictures"
out.mkdir(exist_ok=True)
BASE = "http://localhost:8796/mirror/index.html"
with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome", args=["--disable-lcd-text", "--font-render-hinting=none"])
    errors = []
    for mode, q in (("live", "live=1&"), ("new", "")):
        for tab in ("farms", "live"):
            t = b.new_page(viewport={"width": 1440, "height": 900}, device_scale_factor=1)
            t.on("pageerror", lambda e, m=mode: errors.append(f"{m}: {e}"))
            t.goto(f"{BASE}?{q}tab={tab}", wait_until="networkidle")
            t.wait_for_timeout(4500)                      # the loading screen fades out
            t.evaluate("() => { const b = document.getElementById('afboot'); if (b) b.remove(); }")
            t.wait_for_timeout(300)
            if tab == "farms":
                adf = t.locator("#adf")
                adf.screenshot(path=str(out / f"{mode}-farms-top.png"), clip=None) if False else None
                t.screenshot(path=str(out / f"{mode}-farms-top.png"))
                soon = t.locator("#soon")
                if soon.count():
                    soon.scroll_into_view_if_needed()
                    t.wait_for_timeout(300)
                    t.screenshot(path=str(out / f"{mode}-coming-soon.png"))
            else:
                t.screenshot(path=str(out / f"{mode}-live-farms.png"), full_page=False)
            t.close()
    b.close()
print("page errors:", errors or "none")
