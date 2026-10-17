"""Check the My Balances mockup against parity.md, then picture it.

1. Palette scan: cyan, green, red, blue (navy tints included); no purple, orange, yellow or plain gray.
2. One assertion per parity.md row, in the three preview states (ours, paper, all), so a row that goes missing fails here.
3. Spills, icons, JS errors; one picture per tab and dialog (1440, and 1920 for our account).
"""
import colorsys
import re
from pathlib import Path

from playwright.sync_api import sync_playwright

here = Path(__file__).resolve().parent
bad = []
for name in ("index.html", "style.css"):
    src = (here / name).read_text(encoding="utf-8")
    toks = set(re.findall(r"#[0-9a-fA-F]{6}\b|(?<=:)#[0-9a-fA-F]{3}\b", src)) | {
        re.sub(r"\s", "", m) for m in re.findall(r"rgba?\(([\d\s]+,[\d\s]+,[\d\s]+),", src)}
    for tok in toks:
        if tok.startswith("#"):
            h = "".join(c * 2 for c in tok[1:]) if len(tok) == 4 else tok[1:]
            r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
        else:
            r, g, b = (int(x) for x in tok.split(","))
        hue, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
        if l > .97 or l < .03:
            continue
        if s < .12:
            bad.append(f"{name} {tok} gray")
        elif not (hue * 360 < 12 or hue * 360 > 348 or 135 <= hue * 360 <= 235):
            bad.append(f"{name} {tok} hue {hue * 360:.0f}")
if bad:
    raise SystemExit("off-palette: " + ", ".join(sorted(bad)))
print("colours ok")

JS = """(state) => {
 const T = s => (document.querySelector(s) || {}).innerText || '';
 const shown = s => { const e = document.querySelector(s); if (!e) return false; let n = e; while (n) { if (getComputedStyle(n).display === 'none') return false; n = n.parentElement; } return true; };
 const boxes = [...document.querySelectorAll('#pos .kv .l')].map(l => l.childNodes[0].textContent.trim());
 const has = s => boxes.includes(s);
 const head = T('#s-act .acts');
 const paper = state === 'paper', all = state === 'all';
 const openRows = [...document.querySelectorAll('#cards tr')].filter(r => r.querySelector('td') && !r.classList.contains('grow') && !r.classList.contains('closed'));
 const c = {
  '1 actions': ['DEPOSIT','WITHDRAW','SWAP','BUY ET10','BUY ETLP','AGENT TOURNAMENTS'].every(x => head.includes(x)),
  '2 buying power': ['SOLANA','ETHEREUM','BASE'].every(x => T('#bp').includes(x)) && !T('#bp').includes('OPTIMISM'),
  '3 explain + sync': !!document.querySelector('#exSw') && T('#sync').startsWith('ON-CHAIN'),
  '4 cash': has('USDC') && !has('USDT'),
  '5 tokens': ['ETH','ET10','ETLP','TBIG','TBIGS','DSCI','DESCI','ORBI'].every(has) && !has('VAIX') && !has('SBIO') && (has('tUSDC') === paper),
  '6 funds/vaults': has('CYM42') && (has('THF') === all),
  '7 exchange holdings': !T('#pos').includes('ET10RWD') && !T('#val').includes('ET10RWD') && (T('#pos').includes('EXCHANGE HOLDINGS') === all),
  '8 card positions': openRows.length === 20 && T('#cards').includes('Showing 20 of 27 open') && T('#cards').includes('SHOW 10 CLOSED'),
  '9 paper banner': shown('#paperBanner') === (paper || all),
  '10 owed to you': shown('#owCard') === all,
  '11 pending + claim': shown('#claimBtn') && shown('#pdCard') === all,
  '12 valuation': !!document.querySelector('#vsb') && T('#vTotal') === '$20,345.28' && T('#total') === '$20,345.28',
  '13 microfunds': T('#mfL').includes('#410') && !T('#mfL').includes('Tuatara'),
  '14 yield term': shown('#ytCard') === all,
  '15 ET10 revenue': T('#e10') === '$1.020442',
  '16 revenue share': shown('#rsCard') === all,
  '17 token revenue': shown('#trCard') === all,
  '18 reward delivery': T('#cad .on') === 'ONCE A WEEK' && T('#cadNext').includes('2026-10-20'),
  '19 telegram': T('#s-tg').includes('Telegram notifications'),
  '20 recent orders': T('#ord').includes('BRRR/USDC'),
  '21 api keys': !!document.querySelector('#kCreate') && T('#s-keys').includes('Bring Your Own Agent') && T('#s-keys').includes('API docs'),
  '22 agents': T('#agAv') === '$22.70',
  '24 deposit dialog': document.querySelectorAll('#nets .cp').length === 11,
  '25 withdraw dialog': document.querySelectorAll('#wdA .cp').length === 13,
  '26 swap is a link': !!document.querySelector('[data-go="/swap"]') && !document.querySelector('#swapModal'),
  'one page, no tabs': !document.querySelector('#tabs') && !document.querySelector('.pane'),
  'no transactions list': !document.querySelector('#txl'),
 };
 return Object.entries(c).filter(([k, v]) => !v).map(([k]) => k);
}"""
SPILL = """() => { const out = [];
 document.querySelectorAll('.panel, .tile, .card, .kv, .vr').forEach(c => { const cr = c.getBoundingClientRect();
  if (!cr.width || getComputedStyle(c).visibility === 'hidden') return;
  c.querySelectorAll('*').forEach(e => { const r = e.getBoundingClientRect();
   if (e.children.length === 0 && r.width && (r.right > cr.right + 1 || r.left < cr.left - 1)) out.push((e.textContent.trim() || e.className).slice(0, 30)); }); });
 return [...new Set(out)].slice(0, 12); }"""
ICONS = """() => { const m = []; document.querySelectorAll('i.fa-solid, i.fa-brands').forEach(i => { const c = getComputedStyle(i, '::before').content;
 if (!c || c === 'none' || c === 'normal' || c === '""') m.push(i.className); }); return [...new Set(m)]; }"""

fails = 0
with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome", args=["--disable-lcd-text", "--font-render-hinting=none"])
    for state, widths in (("ours", (1920, 1440)), ("paper", (1440,)), ("all", (1440,))):
        for w in widths:
            tab = browser.new_page(viewport={"width": w, "height": 900})
            errors = []
            tab.on("pageerror", lambda e: errors.append(str(e)))
            tab.goto((here / "index.html").as_uri())
            tab.wait_for_load_state("networkidle")
            tab.wait_for_timeout(800)
            tab.click(f"#pv [data-v={state}]")
            tab.wait_for_timeout(300)
            missing = tab.evaluate(JS, state)
            fails += len(missing)
            print(f"{state} {w} parity: {'all rows ok' if not missing else 'MISSING ' + ', '.join(missing)}")
            tab.evaluate("window.scrollTo(0, 0)")
            tab.wait_for_timeout(350)
            tab.screenshot(path=str(here / f"{state}-{w}.png"), full_page=True)
            sp, ic = tab.evaluate(SPILL), tab.evaluate(ICONS)
            if sp or ic:
                print(f"  spill {sp} icons {ic}")
            if state == "ours" and w == 1440:
                tab.click("#exSw")
                tab.wait_for_timeout(300)
                tab.screenshot(path=str(here / "ours-explain-1440.png"), clip={"x": 0, "y": 0, "width": 1440, "height": 1500}, full_page=True)
                for dlg in ("dep", "wd"):
                    tab.click(f"#s-act [data-dlg={dlg}]")
                    tab.wait_for_timeout(350)
                    tab.screenshot(path=str(here / f"ours-dialog-{dlg}-1440.png"))
                    tab.keyboard.press("Escape")
            print(f"  js errors: {errors}" if errors else "  js ok")
            fails += len(errors)
            tab.close()
    browser.close()
raise SystemExit(1 if fails else 0)
