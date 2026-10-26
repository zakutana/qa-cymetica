"""Render the phone mockup (index.html, this folder): each of the three tier cards on top, the swipe, the Buy sheet and the
details sheet, and the board beside today's card, after a palette scan. Checks that each card's face carries what it should,
that no card scrolls at any phone height, that nothing spills out of its box, and that a swipe on the page really moves the
deck (a drag right past the threshold opens the Buy sheet of that card, Back brings it back)."""
import re
from pathlib import Path

from playwright.sync_api import sync_playwright

here = Path(__file__).resolve().parent
ALLOWED = {"#0a0e17", "#06090f", "#0d1520", "#111a28", "#16233a", "#1a2a44", "#1e3050", "#e6edf7", "#a9b8cc", "#7f93ad",
           "#00cfff", "#00ff88", "#ff4444", "#3b82f6"}
# the palette's colours written as rgb: cyan, green, red, text, #06090f, #0d1520, #111a28, #7f93ad, and black for shadows
ALLOWED_RGB = {"0,207,255", "0,255,136", "255,68,68", "230,237,247", "6,9,15", "13,21,32", "17,26,40", "127,147,173", "0,0,0"}
for name in ("index.html", "board.html"):
    page = (here / name).read_text(encoding="utf-8")
    hexes = {h.lower() for h in re.findall(r"(?<![\w/=&?%.-])#[0-9a-fA-F]{6}(?![0-9a-fA-F])", page)}
    rgbs = {re.sub(r"\s", "", m) for m in re.findall(r"rgba?\(([\d\s]+,[\d\s]+,[\d\s]+),", page)}
    rgbs |= {re.sub(r"\s", "", m) for m in re.findall(r"--(?:hue|ln|glow):([\d\s]+,[\d\s]+,[\d\s]+)", page)}
    bad = sorted(hexes - ALLOWED) + sorted(rgbs - ALLOWED_RGB)
    if bad:
        raise SystemExit(f"{name}: off-palette colours {bad}")
print("colours ok")

FACE = ["Drop rate", "LIVE", "ago", "News sentiment", "−1", "+1", "Since launch", "1 day", "1d", "5d", "30d",
        "Back", "Skip", "Watch", "Sell", "Buy"]
TIER = {"hot": ["HOT", "SSL", "+0.70"], "warm": ["WARM", "ESTC", "−0.60", "+6.83%", "-$0.07", "streetinsider.com"],
        "quiet": ["QUIET", "Penske", "+0.15"]}
BUY = ["Buy", "Paper", "Live", "$100,000.00 available", "0%", "25%", "50%", "75%", "100%", "$0.00", "Confirm Buy", "Cancel"]
INFO = ["SAIB · Single AI Index Basket", "▲ 0", "ripple effect", "Card index", "base 100", "Index price", "$102.43", "launch $95.88",
        "Symbol", "EVCDX-ESTC", "Market cap", "not minted yet", "Per-asset split", "ESTC", "100%", "History", "Share", "Embed"]
SPILL = """() => { const out = [];
 document.querySelectorAll('.card.a .tier, .card.a .sent, .card.a .figs, .card.a .act, .card.a .pill, .card.a .art>span, .top, .sheet.open .kv>div, .sheet.open .pc span, .sheet.open .seg2 span, .sheet.open .btn').forEach(c => {
  const cr = c.getBoundingClientRect();
  c.querySelectorAll('*').forEach(e => { const r = e.getBoundingClientRect();
   if (r.width && !['polyline','path','line','circle','rect','svg','stop','linearGradient','defs','polygon'].includes(e.tagName)
       && (r.right > cr.right + 1 || r.left < cr.left - 1)) out.push(e.textContent.trim().slice(0, 30)); }); });
 const a = document.querySelector('.card.a');
 if (a && !document.body.classList.contains('sheets-open') && !a.classList.contains('drag-right')) {
  const body = a.querySelector('.body').getBoundingClientRect();
  a.querySelectorAll('.plot .olab, .plot .tagv, .plot .dot, .figs, .tog, .art, .sent, .title').forEach(e => { const r = e.getBoundingClientRect();
   if (r.width && (r.right > body.right - 6 || r.left < body.left + 6)) out.push('outside the card: ' + e.className); });
  const v = a.querySelector('.figs .v').getBoundingClientRect(), t = a.querySelector('.tog').getBoundingClientRect();
  if (v.bottom > t.top + 1 && v.right > t.left) out.push('figure runs into the 1d/5d/30d switch');
  const tag = a.querySelector('.tagv').getBoundingClientRect(), f = a.querySelector('.figs').getBoundingClientRect();
  if (tag.top < f.bottom && tag.right > t.left) out.push('chart tag runs into the switch');
  const act = a.querySelector('.actions').getBoundingClientRect();
  if (tag.bottom > act.top) out.push('chart tag under the buttons');
 }
 return out.slice(0, 12); }"""
FIT = """() => { const a = document.querySelector('.card.a'); const b = a.querySelector('.body'); const t = a.querySelector('.title');
 const p = a.querySelector('.plot').getBoundingClientRect();
 return {scrolls: b.scrollHeight - b.clientHeight, title_lines: Math.round(t.getBoundingClientRect().height / parseFloat(getComputedStyle(t).lineHeight)),
         plot_height: Math.round(p.height)}; }"""
OPEN_TEXT = "() => [...document.querySelectorAll('.sheet.open')].map(e => e.innerText).join(' ')"


def load(b, w, h, query):
    t = b.new_page(viewport={"width": w, "height": h}, device_scale_factor=2, is_mobile=True, has_touch=True)
    t.goto((here / "index.html").as_uri() + query)
    t.wait_for_load_state("networkidle")
    t.wait_for_timeout(800)
    return t


with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome", args=["--disable-lcd-text", "--font-render-hinting=none"])
    for key, words in TIER.items():
        for (w, h) in ((390, 844), (360, 740), (375, 667), (360, 640)):
            t = load(b, w, h, f"?c={key}")
            txt = t.evaluate("() => document.querySelector('.card.a').innerText + ' ' + document.querySelector('.top').innerText")
            fit = t.evaluate(FIT)
            missing = [x for x in FACE + words if x.lower() not in txt.lower()]
            print(f"{key:5} {w}x{h} | missing {missing} | spill {t.evaluate(SPILL)} | {fit}", "| SCROLLS" if fit["scrolls"] > 1 else "")
            if w == 390 or (w, h) == (360, 640):
                t.screenshot(path=str(here / f"phone-{key}-{w}x{h}.png"))
            t.close()
    for s, names in (("swipe", None), ("buy", BUY), ("info", INFO)):
        t = load(b, 390, 844, f"?s={s}")
        if names:
            txt = t.evaluate(OPEN_TEXT)
            print(f"{s} sheet | missing {[x for x in names if x.lower() not in txt.lower()]} | spill {t.evaluate(SPILL)}")
        t.screenshot(path=str(here / f"phone-{s}-390.png"))
        t.close()
    # the deck really swipes: drag the top card right past the threshold, then Cancel, then Back
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
    t = b.new_page(viewport={"width": 1702, "height": 2060}, device_scale_factor=1.5)
    t.goto((here / "board.html").as_uri())
    t.wait_for_load_state("networkidle")
    t.wait_for_timeout(1800)
    t.screenshot(path=str(here / "board.png"), full_page=True)
    b.close()
print("rendered")
