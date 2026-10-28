"""Picture every step of the Yield Booster demo from its frozen states (?shot=1), and say what a look would miss:
page errors, horizontal overflow, and whether the card, the amount screen and the end of the pipe show one number.

python outbox/yield-booster/render.py [out_dir] [width ...]   (default: the scratch folder given, 1920)
Pictures are not committed (git is over its ceiling); they are for looking."""
import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

here = Path(__file__).resolve().parent
out = Path(sys.argv[1]) if len(sys.argv) > 1 else here / "pictures"
out.mkdir(parents=True, exist_ok=True)
widths = [int(a) for a in sys.argv[2:]] or [1920]
url = (here / "mock.html").as_uri()
STATES = [("1-risk", "step=1&tier=high"), ("2-amount", "step=2&tier=high"), ("3-finder", "step=3&tier=high"),
          ("4-route-high", "step=4&tier=high"), ("4-route-conservative", "step=4&tier=conservative"),
          ("4-route-medium", "step=4&tier=medium"), ("4-route-og", "step=4&tier=og"),
          ("4-route-medium-10", "step=4&tier=medium&move=0.1"), ("4-route-medium-30", "step=4&tier=medium&move=0.3"),
          ("logo", "logo=1")]

with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome", args=["--disable-lcd-text", "--font-render-hinting=none"])
    errors, agree = [], []
    for w in widths:
        t = b.new_page(viewport={"width": w, "height": 1000}, device_scale_factor=1)
        t.on("pageerror", lambda e: errors.append(str(e)))
        for name, qs in STATES:
            t.goto(f"{url}?shot=1&amount=5000&{qs}", wait_until="networkidle")
            t.wait_for_timeout(600)
            over = t.evaluate("() => document.documentElement.scrollWidth - innerWidth")
            if over > 0:
                errors.append(f"{name} at {w}px overflows by {over}px")
            t.screenshot(path=str(out / f"{name}-{w}.png"), full_page=True)
        # one number: the card's good month, the amount screen's dollars, the tank and the outcome row
        for tier in ("conservative", "medium", "high", "og"):
            t.goto(f"{url}?shot=1&amount=5000&step=1", wait_until="networkidle")
            card = t.inner_text(f"[data-tier={tier}] .pair .up b")
            t.goto(f"{url}?shot=1&amount=5000&step=2&tier={tier}", wait_until="networkidle")
            side = t.inner_text("#picked .pair .up b")
            dollars = t.inner_text("#month2 .up b")
            t.goto(f"{url}?shot=1&amount=5000&step=4&tier={tier}", wait_until="networkidle")
            t.wait_for_timeout(300)
            tank = t.text_content(".tank .v")
            row = t.inner_text("#outcome .up b")
            mult = t.inner_text("#outcome .up span").split(" ")[0]
            agree.append((tier, card, side, mult, dollars, tank, row))
            if not (card == side == mult and dollars == tank == row):
                errors.append(f"{tier}: card {card} / amount {side} / route {mult}; {dollars} / tank {tank} / row {row}")
        t.close()
    b.close()
for a in agree:
    print(*a)
print("problems:", errors or "none")
sys.exit(1 if errors else 0)
