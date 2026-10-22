"""Render the Promo Market mockup after a palette scan, and check it the way a reader would:
 - every colour is the site's (cyan, green, red, blue and the greys), in the CSS and the JS;
 - everything the live creator dashboard shows is still somewhere on the new one (HAS, read off the live page of
   2026-10-22), across all its views;
 - nothing spills out of its card or tile, and nothing scrolls sideways;
then capture each view at 1440 (and the market at 1920) into shots/."""
import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

here = Path(__file__).resolve().parent
shots = here / "shots"
shots.mkdir(exist_ok=True)

ALLOWED = {"#0a0e17", "#06090f", "#0d1520", "#111a28", "#16233a", "#1a2a44", "#1e3050", "#e6edf7", "#a9b8cc", "#7f93ad",
           "#00cfff", "#00ff88", "#ff4444", "#3b82f6"}
ALLOWED_RGB = {"0,207,255", "0,255,136", "255,68,68", "230,237,247", "0,0,0", "59,130,246", "6,9,15", "13,21,32", "3,5,9"}
bad = []
for f in ("style.css", "app.js", "index.html"):
    src = (here / f).read_text(encoding="utf-8")
    for h in re.findall(r"#[0-9a-fA-F]{6}\b", src):
        if h.lower() not in ALLOWED:
            bad.append((f, h))
    for m in re.findall(r"rgba?\(([\d\s]+,[\d\s]+,[\d\s]+)[,)]", src):
        if re.sub(r"\s", "", m) not in ALLOWED_RGB:
            bad.append((f, m))
if bad:
    raise SystemExit(f"off-palette colours {sorted(set(bad))}")
print("colours ok")

# what the live page shows (its public view and what its owner sees, read 2026-10-22), each to be found somewhere
HAS = ["Most token lists rank by hype", "Copy", "Open in X", "Mark posted", "Save graphic", "post 1 of 4",
       "Wait for my instructions before placing any trade", "Trade", "Radar apps", "Safe Launch Check", "Event Cover",
       "Best Rate Check", "Funding Rate Radar", "Loop Yield", "Who to reach", "r/CryptoMoonShots", "@StonkFunXyz",
       "Copy title", "Copy body", "Copy post", "Telegram post", "Links", "Clicks", "Reads", "Likes", "Unique", "Queues",
       "Rewards", "Create a page", "Track a link", "1,000 ET10", "ETLP", "Start a company",
       "Reuse it on every matching thread", "moomoo", "Hyblock Capital", "r/ai_trading", "google.com", "Download HTML",
       "Also on claude.ai", "Open page", "Are you Mumtaz?", "Log in", "Reply with this page", "Skip", "Mumtaz",
       "4,335", "6,852", "1,443", "2,821", "liking removed", "Press", "Pitch by email", "Promo Market", "Post a brief",
       "Up for grabs", "per new user", "per post", "My products", "Create brief", "How a new user is counted",
       "Visitors your briefs brought", "Promote from your AI agent", "Briefs I took", "After you post it", "Posted something yourself?", "Channel post", "Queue post", "Article published?", "Create key", "First look: you", "New page for this thread", "Mark pitched"]
CHECK = """() => { const out = [];
  document.querySelectorAll('.bc, .stat, .kpi, .qt, .sb, .qi, .ra, .house, .step, .rr, .prod, .chip, .btn, .tp').forEach(c => {
    if (!c.offsetParent) return; const cr = c.getBoundingClientRect();
    c.querySelectorAll('*').forEach(e => { if (e.closest('svg') && e.tagName !== 'svg') return; const r = e.getBoundingClientRect();
      if (e.children.length === 0 && r.width && (r.right > cr.right + 1.5 || r.left < cr.left - 1.5) && getComputedStyle(e).position !== 'absolute')
        out.push(c.className.split(' ')[0] + ' > ' + (e.textContent || e.tagName).trim().slice(0, 28)); }); });
  if (document.documentElement.scrollWidth > innerWidth) out.push('page scrolls sideways');
  return [...new Set(out)].slice(0, 14); }"""

VIEWS = [("market", "#market", None), ("me-products", "#me/products", None), ("me-today", "#me/today", None), ("me-briefs", "#me/taken", None),
         ("me-queues", "#me/queues", None), ("me-press", "#me/queues", "[data-q=press]"), ("me-radar", "#me/queues", "[data-q=radar]"), ("me-channels", "#me/queues", "[data-q=telegram]"),
         ("me-pages", "#me/pages", "[data-row]"), ("me-rewards", "#me/rewards", None), ("profile", "#profile", "[data-row]")]
# a tooltip is part of what the page says: count its text too
SEEN = "() => document.body.innerText + ' ' + [...document.querySelectorAll('[data-tip]')].map(e => e.dataset.tip).join(' ')"
with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome", args=["--disable-lcd-text", "--font-render-hinting=none"])
    t = b.new_page(viewport={"width": 1440, "height": 900})
    t.goto((here / "index.html").as_uri())
    t.wait_for_load_state("networkidle")
    t.wait_for_timeout(800)
    seen = ""
    for name, h, click in VIEWS:
        t.evaluate(f"location.hash = '{h}'")
        t.wait_for_timeout(300)
        if click:
            t.click(click)
            t.wait_for_timeout(300)
        t.wait_for_load_state("networkidle")
        t.wait_for_timeout(400)
        seen += t.evaluate(SEEN) + "\n"
        print(name, "height", t.evaluate("document.documentElement.scrollHeight"), "| problems:", t.evaluate(CHECK))
        t.screenshot(path=str(shots / f"{name}-1440.png"), full_page=name not in ("profile",))
        if name == "profile":
            t.screenshot(path=str(shots / f"{name}-1440.png"))
    # the overlays: one brief, the form, the agent prompts, create a page
    for name, h, click in [("brief-drawer", "#market", ".bc[data-brief=gem]"), ("post-brief", "#me/products", "[data-newbrief=nexus]"),
                           ("agent", "#market", ".hero [data-act=agent]"), ("take", "#market", ".bc[data-brief=supply] [data-take]"), ("product-drawer", "#me/products", ".pc[data-product=gem] .btn"),
                           ("create-page", "#me/pages", "[data-act=page]")]:
        t.evaluate(f"location.hash = '{h}'")
        t.wait_for_timeout(300)
        t.evaluate("window.scrollTo(0, 0)")
        if name in ("brief-drawer", "take"):
            t.evaluate("document.getElementById('board').scrollIntoView()")
        t.click(click)
        t.wait_for_timeout(700)
        seen += t.evaluate(SEEN) + "\n"
        print(name, "| problems:", t.evaluate(CHECK))
        t.screenshot(path=str(shots / f"{name}-1440.png"))
        t.keyboard.press("Escape")
        t.wait_for_timeout(300)
    missing = [s for s in HAS if s.lower() not in seen.lower()]
    print("missing from the new page:", missing)
    t.close()
    for w, hgt in ((1920, 1080),):
        t = b.new_page(viewport={"width": w, "height": hgt})
        t.goto((here / "index.html").as_uri() + "#market")
        t.wait_for_load_state("networkidle")
        t.wait_for_timeout(900)
        print(w, "market height", t.evaluate("document.documentElement.scrollHeight"), "| problems:", t.evaluate(CHECK))
        t.screenshot(path=str(shots / f"market-{w}.png"), full_page=True)
        t.evaluate("location.hash = '#me/today'")
        t.wait_for_timeout(900)
        print(w, "today | problems:", t.evaluate(CHECK))
        t.screenshot(path=str(shots / f"me-today-{w}.png"))
        t.close()
    b.close()
if missing:
    sys.exit(1)
print("rendered")
