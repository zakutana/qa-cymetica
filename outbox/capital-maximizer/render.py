"""Picture every screen of the Capital Maximizer demo from its frozen states (?shot=1), and say what a look would
miss: page errors, horizontal overflow, and whether the card, the amount screen, the first of the three strategies and
the plan show one number -- also after the leverage is tuned in a tree.

python outbox/capital-maximizer/render.py [out_dir] [width ...]   (default: ./pictures, 1920)
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
STATES = [("1-risk", "step=1"), ("2-amount", "step=2&tier=high"),
          ("3-top3-high", "step=3&tier=high"), ("3-top3-og", "step=3&tier=og"),
          ("3-top3-conservative", "step=3&tier=conservative"), ("3-top3-medium", "step=3&tier=medium"),
          ("4-plan-high", "step=4&tier=high"), ("4-plan-og-lev3", "step=4&tier=og&lev=3"),
          ("4-plan-conservative", "step=4&tier=conservative"), ("4-plan-medium-loop", "step=4&tier=medium&pick=2"),
          ("4-plan-medium-lp", "step=4&tier=medium&pick=0"),
          ("platforms", "tab=platforms"), ("logo", "logo=1")]


def dollars(s: str) -> float:
    v = float(re.sub(r"[^\d.]", "", s))
    return -v if s.startswith("−") else v


with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome", args=["--disable-lcd-text", "--font-render-hinting=none"])
    errors, agree = [], []
    for w in widths:
        t = b.new_page(viewport={"width": w, "height": 1080}, device_scale_factor=1)
        t.on("pageerror", lambda e: errors.append(str(e)))
        for name, qs in STATES:
            t.goto(f"{url}?shot=1&amount=5000&{qs}", wait_until="networkidle")
            t.wait_for_timeout(700)
            over = t.evaluate("() => document.documentElement.scrollWidth - innerWidth")
            if over > 0:
                errors.append(f"{name} at {w}px overflows by {over}px")
            t.screenshot(path=str(out / f"{name}-{w}.png"), full_page=True)
        # the operator expects some fifty platforms: copy the tiles to fifty in the picture only, to see they fit
        t.goto(f"{url}?shot=1&tab=platforms", wait_until="networkidle")
        t.evaluate("""() => { const g = document.getElementById('plats'), tiles = [...g.children];
            for (let k = tiles.length; k < 50; k++) g.appendChild(tiles[k % tiles.length].cloneNode(true)); }""")
        t.wait_for_timeout(300)
        t.screenshot(path=str(out / f"platforms-50-copies-{w}.png"), full_page=True)
        for tier in ("conservative", "medium", "high", "og"):
            t.goto(f"{url}?shot=1&amount=5000&step=1", wait_until="networkidle")
            card = t.inner_text(f"[data-tier={tier}] .big b")
            want = t.evaluate(f"() => {{ const r = CM.top3('{tier}')[0]; return [r.up, CM.profit(r, 5000)]; }}")
            t.goto(f"{url}?shot=1&amount=5000&step=2&tier={tier}", wait_until="networkidle")
            amount = dollars(t.inner_text("#preview b"))
            t.goto(f"{url}?shot=1&amount=5000&step=3&tier={tier}", wait_until="networkidle")
            col = dollars(t.inner_text('[data-usd="0"]'))
            # tune the first strategy one step up in its tree, if it has a leverage
            tuned = t.evaluate(f"""() => {{ const b = document.querySelector('[data-act="inc"][data-col="0"]');
                if (!b || b.classList.contains('off')) return null;
                b.dispatchEvent(new MouseEvent('click', {{bubbles: true}}));
                const r = CM.tune(CM.top3('{tier}')[0], CM.top3('{tier}')[0].L + 0.5);
                return [CM.profit(r, 5000), document.querySelector('[data-usd="0"]').textContent]; }}""")
            t.goto(f"{url}?shot=1&amount=5000&step=4&tier={tier}&pick=0", wait_until="networkidle")
            t.wait_for_timeout(300)
            plan = dollars(t.inner_text("#pv"))
            agree.append((tier, card, round(want[1], 2), amount, col, plan, tuned))
            if abs(float(card.lstrip("×")) - want[0]) > 0.006 or not (abs(amount - want[1]) < 1 and amount == col == plan):
                errors.append(f"{tier}: card {card} model {want}; amount {amount} / column {col} / plan {plan}")
            if tuned and abs(dollars(tuned[1]) - tuned[0]) > 1:
                errors.append(f"{tier}: tuned in the tree {tuned[1]}, model {tuned[0]:.2f}")
        t.close()
    b.close()
for a in agree:
    print(*a)
print("problems:", errors or "none")
sys.exit(1 if errors else 0)
