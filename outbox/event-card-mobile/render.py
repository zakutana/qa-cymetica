"""Render the phone mockup (index.html, this folder): each tier card on top, his hues for comparison, the swipe, the Buy
sheet and the STATS tab, and the board under his own picture, after a palette scan of the page (his-colours.css, the
comparison, is left out of it on purpose). Checks that each face carries what his card carries, that no card scrolls at
any phone height, that nothing spills out of its box, that the chart keeps a usable height, and that a swipe on the page
really moves the deck."""
import re
from pathlib import Path

from playwright.sync_api import sync_playwright

here = Path(__file__).resolve().parent
ALLOWED = {"#0a0e17", "#06090f", "#0d1520", "#111a28", "#16233a", "#1a2a44", "#1e3050", "#e6edf7", "#a9b8cc", "#7f93ad",
           "#00cfff", "#00ff88", "#ff4444", "#3b82f6"}
# the palette's colours written as rgb: cyan, green, red, blue, text, #06090f, #0d1520, #111a28, #7f93ad, black for shadows
ALLOWED_RGB = {"0,207,255", "0,255,136", "255,68,68", "59,130,246", "230,237,247", "6,9,15", "13,21,32", "17,26,40",
               "127,147,173", "0,0,0"}
for name in ("index.html", "board.html"):
    page = (here / name).read_text(encoding="utf-8")
    hexes = {h.lower() for h in re.findall(r"(?<![\w/=&?%.-])#[0-9a-fA-F]{6}(?![0-9a-fA-F])", page)}
    rgbs = {re.sub(r"\s", "", m) for m in re.findall(r"rgba?\(([\d\s]+,[\d\s]+,[\d\s]+),", page)}
    rgbs |= {re.sub(r"\s", "", m) for m in re.findall(r"--(?:t|ln|sd):([\d\s]+,[\d\s]+,[\d\s]+)", page)}
    bad = sorted(hexes - ALLOWED) + sorted(rgbs - ALLOWED_RGB)
    if bad:
        raise SystemExit(f"{name}: off-palette colours {bad}")
print("colours ok")

FACE = ["Drop rate", "INFO", "STATS", "LIVE", "ago", "NEWS SENTIMENT", "NEGATIVE", "NEUTRAL", "POSITIVE", "LINKED ASSETS",
        "weight", "1d", "5d", "30d", "BACK", "SKIP", "WATCH", "BUY", "SELL"]
TIER = {"hot": ["HOT", "SSL", "+0.70", "cnbc.com"], "warm": ["WARM", "ESTC", "−0.60", "streetinsider.com", "$1.0683"],
        "quiet": ["QUIET", "Penske", "+0.15"]}
BUY = ["Buy", "Paper", "Live", "$100,000.00 available", "0%", "25%", "50%", "75%", "100%", "$0.00", "Confirm Buy", "Cancel"]
STATS = ["Since launch", "+6.83%", "100 → 106.83", "Card index", "Index price", "$102.43", "launch $95.88", "Symbol", "EVCDX-ESTC",
         "Market cap", "not minted yet", "ripple effect", "Per-asset split", "SAIB · Single AI Index Basket", "History", "Share", "Embed"]
SPILL = """() => { const out = [];
 document.querySelectorAll('.card.a .strip, .card.a .tabs, .card.a .sent .sh, .card.a .as, .card.a .price, .card.a .act, .card.a .kv>div, .card.a .links .btn, .top, .sheet.open .pc span, .sheet.open .seg2 span').forEach(c => {
  if (!c.getClientRects().length) return;
  const cr = c.getBoundingClientRect();
  c.querySelectorAll('*').forEach(e => { const r = e.getBoundingClientRect();
   if (r.width && !['path','circle','svg'].includes(e.tagName) && (r.right > cr.right + 1 || r.left < cr.left - 1)) out.push(e.textContent.trim().slice(0, 30)); }); });
 return out.slice(0, 12); }"""
FIT = """() => { const a = document.querySelector('.card.a'); const v = a.querySelector(a.classList.contains('stats') ? '.stats-view' : '.info-view');
 const t = a.querySelector('.title');
 return {scrolls: Math.max(v.scrollHeight - v.clientHeight, a.scrollHeight - a.clientHeight), title_lines: Math.round(t.getBoundingClientRect().height / parseFloat(getComputedStyle(t).lineHeight)),
         chart: Math.round(a.querySelector('.chart').getBoundingClientRect().height)}; }"""


def load(b, w, h, query):
    t = b.new_page(viewport={"width": w, "height": h}, device_scale_factor=2, is_mobile=True, has_touch=True)
    t.goto((here / "index.html").as_uri() + query)
    t.wait_for_load_state("networkidle")
    t.wait_for_timeout(900)
    return t


with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome", args=["--disable-lcd-text", "--font-render-hinting=none"])
    for key, words in TIER.items():
        for (w, h) in ((390, 844), (360, 740), (375, 667), (360, 640)):
            t = load(b, w, h, f"?c={key}")
            txt = t.evaluate("() => document.querySelector('.card.a').innerText + ' ' + document.querySelector('.top').innerText")
            fit = t.evaluate(FIT)
            missing = [x for x in FACE + words if x.lower() not in txt.lower()]
            flag = " | SCROLLS" if fit["scrolls"] > 1 else (" | CHART TOO LOW" if fit["chart"] < 60 else "")
            print(f"{key:5} {w}x{h} | missing {missing} | spill {t.evaluate(SPILL)} | {fit}{flag}")
            if w == 390 or (w, h) == (360, 640):
                t.screenshot(path=str(here / f"phone-{key}-{w}x{h}.png"))
            t.close()
    for s, names in (("swipe", None), ("buy", BUY), ("stats", STATS)):
        t = load(b, 390, 844, f"?s={s}")
        if names:
            sel = ".sheet.open" if s == "buy" else ".card.a .stats-view"
            txt = t.evaluate(f"() => document.querySelector('{sel}').innerText")
            extra = f" | {t.evaluate(FIT)}" if s == "stats" else ""
            print(f"{s} | missing {[x for x in names if x.lower() not in txt.lower()]} | spill {t.evaluate(SPILL)}{extra}")
        t.screenshot(path=str(here / f"phone-{s}-390.png"))
        t.close()
    t = load(b, 390, 844, "")
    top0 = t.evaluate("() => document.querySelector('.card.a').dataset.key")
    box = t.evaluate("() => { const r = document.querySelector('.card.a .title').getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2] }")
    t.mouse.move(*box); t.mouse.down()
    for k in range(1, 15):
        t.mouse.move(box[0] + k * 12, box[1]); t.wait_for_timeout(16)
    stamp = t.evaluate("() => getComputedStyle(document.querySelector('.card.a .stamp.bull')).opacity")
    t.mouse.up(); t.wait_for_timeout(600)
    after = t.evaluate("() => [document.querySelector('.card.a').dataset.key, document.body.classList.contains('sheets-open'), (document.querySelector('.sheet.open') || {}).dataset]")
    t.click(".sheet.open .cancel"); t.wait_for_timeout(400)
    t.click(".card.a .act[data-do=back]"); t.wait_for_timeout(500)
    back = t.evaluate("() => document.querySelector('.card.a').dataset.key")
    print(f"swipe right from {top0}: stamp {stamp}, now on top {after[0]}, sheet open {after[1]} {after[2]}; Back -> {back}")
    t.close()
    t = b.new_page(viewport={"width": 1364, "height": 4400}, device_scale_factor=1.25)
    t.goto((here / "board.html").as_uri())
    t.wait_for_load_state("networkidle")
    t.wait_for_timeout(2500)
    t.screenshot(path=str(here / "board.png"), full_page=True)
    b.close()
print("rendered")
