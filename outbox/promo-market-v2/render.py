"""Check the v2 mockup the way a reader would, then capture every screen at 1920 x 1080 into shots/:
 - every colour is the site's (cyan, green, red, blue and the greys), in the CSS, the JS and the pictures;
 - everything the live dashboard shows (read signed in, 2026-10-26) is somewhere on the new one (HAS);
 - nothing spills out of its card, nothing scrolls sideways, and Post a brief fits one 1080 screen.
Run with the server up: python -m http.server 8799 --bind 127.0.0.1 --directory outbox."""
import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

here = Path(__file__).resolve().parent
shots = here / "shots"
shots.mkdir(exist_ok=True)
URL = "http://127.0.0.1:8799/promo-market-v2/index.html"

ALLOWED = {"#0a0e17", "#06090f", "#0d1520", "#111a28", "#16233a", "#1a2a44", "#1e3050", "#e6edf7", "#a9b8cc", "#7f93ad",
           "#00cfff", "#00ff88", "#ff4444", "#3b82f6", "#0f1c2e", "#05070c", "#e8fbff", "#33ffa0"}
ALLOWED_RGB = {"0,207,255", "0,255,136", "255,68,68", "230,237,247", "0,0,0", "59,130,246", "6,9,15", "13,21,32", "4,6,10", "10,14,23"}
bad = []
for f in ["style.css", "app.js", "index.html"] + [str(p.relative_to(here)) for p in (here / "art").glob("*.svg")]:
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

# what the live dashboard and market show (signed in, 2026-10-26), each to be found somewhere on the new one
HAS = ["Post it. Bring users", "Earn: take a brief", "Promote my product", "From your AI agent", "USDC up for grabs", "Open briefs",
       "Top pay per new user", "Pick a brief", "Take it", "Post it anywhere", "Get paid in USDC", "Most up for grabs", "Best per new user",
       "Ending soon", "No open briefs right now", "For builders", "Promote from your AI agent", "A new person through your link",
       "What this does not do yet", "My products", "Post a brief", "Up for grabs in your briefs", "Visitors brought", "New users", "Spent",
       "No visitors from briefs yet", "No brief yet", "Create brief", "visitors", "views", "Your budget stays in your own wallet",
       "Today", "Tweet this now", "Copy the tweet", "Open in X", "Save graphic", "Mark posted", "Register post", "UNVERIFIABLE",
       "Trade from your own AI agent", "Why post", "1,299", "4,753", "Links", "Clicks", "Reads", "Likes", "Unique visitors", "Corrected on",
       "Briefs I took", "Briefs taken", "Earned, payout pending", "Queues", "Queue for", "8676 open", "3 communities", "LinkedIn", "YouTube",
       "Reply with this page", "Create page for", "Skip", "Open on Reddit", "Pick the page", "Journalists", "open for you", "Mark pitched",
       "Radar apps", "Safe Launch Check", "Event Cover", "Best Rate Check", "Funding Rate Radar", "Loop Yield", "Get my tracked link",
       "Copy title", "Copy body", "Post to @", "Create a Claude artifact page", "Create artifact page", "tags per outlet", "Playbook",
       "Bring Build it Better to a crypto community", "Make the kit", "Track any other link", "Create link", "Pages & links", "Rewards",
       "Posts rewarded", "ET10 earned", "ETLP earned", "Awaiting verification", "Agent key", "Create key", "81 active keys", "Copy the prompt",
       "Start an app and a company", "Cayman", "Your public page", "Agent prompts", "Promo Market"]
CHECK = """() => { const out = [];
  document.querySelectorAll('.bc, .tile, .pc, .chip, .btn, .rule, .mat, .pays > div, .stepper > div, .rapps button, .pick button, .payrow, .tag, .buys > div, .r3 > div, .item').forEach(c => {
    if (!c.offsetParent) return; const cr = c.getBoundingClientRect();
    c.querySelectorAll('*').forEach(e => { if (e.closest('svg') && e.tagName !== 'svg') return; const r = e.getBoundingClientRect();
      if (e.children.length === 0 && r.width && (r.right > cr.right + 1.5 || r.left < cr.left - 1.5) && getComputedStyle(e).position !== 'absolute')
        out.push(c.className.split(' ')[0] + ' > ' + (e.textContent || e.tagName).trim().slice(0, 28)); }); });
  if (document.documentElement.scrollWidth > innerWidth) out.push('page scrolls sideways');
  return [...new Set(out)].slice(0, 14); }"""
SEEN = ("() => document.body.innerText + ' ' + [...document.querySelectorAll('[data-tip]')].map(e => e.dataset.tip).join(' ') + ' ' + "
        "[...document.querySelectorAll('option, details')].map(o => o.textContent).join(' ')")

VIEWS = [("market", "#market"), ("me-products", "#me/products"), ("me-today", "#me/today"), ("me-taken", "#me/taken"),
         ("me-queues", "#me/queues"), ("me-journalists", "#me/journalists"), ("me-radar", "#me/radar"), ("me-kits", "#me/kits"),
         ("me-links", "#me/links"), ("me-rewards", "#me/rewards"), ("me-key", "#me/key"), ("me-company", "#me/company"), ("new", "#new")]
problems = 0
with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome", args=["--disable-lcd-text", "--font-render-hinting=none"])
    t = b.new_page(viewport={"width": 1920, "height": 1080})
    t.goto(URL + "#market")
    t.wait_for_timeout(900)
    t.screenshot(path=str(shots / "loader.png"))                      # the loader, mid-way
    t.wait_for_timeout(3500)
    t.add_style_tag(content=".mock { display: none !important; }")   # the mockup's own switch stays out of the pictures
    seen = ""
    for mode in ("live", "sample"):
        t.evaluate(f"document.querySelector('[data-mode={mode}]').click()")
        t.wait_for_timeout(300)
        for name, h in VIEWS:
            t.evaluate(f"location.hash = '{h}'")
            t.wait_for_timeout(500)
            t.wait_for_load_state("networkidle")                     # the live graphics come from cymetica.com
            seen += t.evaluate(SEEN) + "\n"
            pr = t.evaluate(CHECK)
            hgt = t.evaluate("document.documentElement.scrollHeight")
            if name == "new" and hgt > 1080:
                pr.append(f"Post a brief scrolls: {hgt} px")
            problems += len(pr)
            print(f"{mode:6} {name:15} height {hgt:5} | problems: {pr}")
            t.screenshot(path=str(shots / f"{mode}-{name}.png"), full_page=name not in ("me-queues", "me-journalists"))
            if name == "me-queues":
                for ch in ("x", "telegram"):
                    t.evaluate(f"document.querySelector('[data-qch={ch}]').click()")
                    t.wait_for_timeout(300)
                    seen += t.evaluate(SEEN) + "\n"
                    t.screenshot(path=str(shots / f"{mode}-me-queues-{ch}.png"))
                t.evaluate("document.querySelector('[data-qch=reddit]').click()")
    # the overlays and the brief's own page, on the sample briefs
    for name, h, js in [("brief-drawer", "#market", "document.querySelector('.bc[data-brief=\"101\"]').click()"),
                        ("take", "#market", "document.querySelector('.bc[data-brief=\"102\"] [data-take]').click()"),
                        ("agent", "#market", "document.querySelector('.hero [data-act=agent]').click()"),
                        ("product-drawer", "#me/products", "document.querySelector('.pc[data-product=\"/team-dump-radar\"]').click()"),
                        ("mybrief-101", "#mybrief/101", ""), ("mybrief-103", "#mybrief/103", ""), ("new-chart", "#new/chart-analyzer", "")]:
        t.evaluate(f"location.hash = '{h}'")
        t.wait_for_timeout(400)
        if js:
            t.evaluate(js)
        t.wait_for_timeout(700)
        seen += t.evaluate(SEEN) + "\n"
        pr = t.evaluate(CHECK)
        problems += len(pr)
        print(f"sample {name:15} height {t.evaluate('document.documentElement.scrollHeight'):5} | problems: {pr}")
        t.screenshot(path=str(shots / f"sample-{name}.png"), full_page=name.startswith("mybrief"))
        t.keyboard.press("Escape")
        t.wait_for_timeout(200)
    # post one from the form: it opens on its own page, empty, and shows on My products
    t.evaluate("location.hash = '#new/airdrop-farmer'")
    t.wait_for_timeout(400)
    t.evaluate("document.querySelector('[data-act=publish]').click()")
    t.wait_for_timeout(700)
    print("posted ->", t.evaluate("location.hash"))
    t.screenshot(path=str(shots / "posted.png"), full_page=True)
    missing = [s for s in HAS if s.lower() not in seen.lower()]
    print("missing from the new page:", missing)
    b.close()
if missing or problems:
    sys.exit(1)
print("rendered")
