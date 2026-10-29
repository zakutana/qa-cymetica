"""Build the Gem Screener tier list (HTML -> PNG) from a saved snapshot.

    python make_tier.py <snapshot.json> <logo.svg> <out.png>

S = passes all Degen gates (degen_ok); A..F = Upside (potential) bands over the
vetted apps with $100K+ revenue in 30 days. Reads files only; writes the PNG.
"""
import html
import json
import sys
from datetime import datetime
from pathlib import Path

snap_path, logo_path, out_path = sys.argv[1:4]
# SYMBOL=path pairs: a logo the snapshot has wrong (Securitize carries BlackRock's), replaced by
# the token's own image from CoinGecko.
overrides = dict(arg.split("=", 1) for arg in sys.argv[4:])
g = json.loads(Path(snap_path).read_text(encoding="utf-8"))
import base64
for a in g["apps"]:
    if a.get("symbol") in overrides:
        raw = Path(overrides[a["symbol"]]).read_bytes()
        a["logo_data"] = "data:image/png;base64," + base64.b64encode(raw).decode()
logo_svg = Path(logo_path).read_text(encoding="utf-8")
gates = len(g["degen_gates"]["gates"])
bench = g["bench"]["mult"]
when = datetime.fromisoformat(g["generated_at_iso"].replace("Z", "+00:00"))

# The set the live Gem Tier List draws (gem-screener/app?view=apps, tierModel): $100K+ revenue in 30 days and
# vetted (reliable) or young, plus every Degen pick; an app without an upside number is not ranked. A tier follows the
# upside rounded to one decimal, the number the icon shows (9.96 reads 10x). 2026-10-29: this was "reliable or
# degen_ok" before, which left out young apps (MASK was in their list and not in ours).
apps = [a for a in g["apps"] if a.get("degen_ok") or ((a.get("rev30d") or 0) >= 1e5 and (a.get("reliable") or a.get("young")))]
unranked = [a for a in apps if a.get("potential") is None]
apps = [a for a in apps if a.get("potential") is not None]
apps.sort(key=lambda a: -(a.get("potential_raw") or a.get("potential") or 0))
up = lambda a: round(a["potential"] * 10) / 10
TIERS = [
    ("S", "♥ PICKS", "#00ff88", "#04140c", lambda a: a.get("degen_ok")),   # as the live page labels it (the Degen picks)
    ("A", "10x+ UPSIDE", "#2fe0a3", "#04140c", lambda a: up(a) >= 10),
    ("B", "5 TO 10x", "#00cfff", "#03121a", lambda a: up(a) >= 5),
    ("C", "2 TO 5x", "#3b82f6", "#ffffff", lambda a: up(a) >= 2),
    ("D", "1 TO 2x", "#64748b", "#ffffff", lambda a: up(a) >= 1),
    ("F", "UNDER 1x", "#475569", "#ffffff", lambda a: True),
]
rows, left = [], list(apps)
for key, label, bg, fg, test in TIERS:
    mine = [a for a in left if test(a)]
    left = [a for a in left if a not in mine]
    rows.append((key, label, bg, fg, mine))
assert not left

def coin(a):
    sym = html.escape(a.get("symbol") or a["name"][:6])
    src = a.get("logo_data") or ""
    img = f'<img src="{src}" alt="">' if src else f'<span class="ph">{sym[:2]}</span>'
    return f'<div class="coin"><div class="ring">{img}</div><b>{sym}</b></div>'

body = "".join(
    f'<section class="row"><div class="lab" style="background:{bg};color:{fg}"><span>{k}</span><i>{html.escape(l)}</i></div>'
    f'<div class="coins">{"".join(coin(a) for a in mine)}</div></section>'
    for k, l, bg, fg, mine in rows)
n = len(apps)
foot = (f"{n} apps with $100K+ revenue in 30 days, vetted or a Degen pick. S = the Degen picks, passing all {gates} Degen gates. "
        f"A to F = Upside: Hyperliquid's price-to-revenue multiple ({bench:.1f}x) divided by the app's own. "
        f"Data {when.day} {when.strftime('%b %Y')}. A research screen, not financial advice.")

page = f"""<!doctype html><html><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Archivo+Black&family=JetBrains+Mono:wght@500;700;800&display=swap" rel="stylesheet">
<style>
*{{box-sizing:border-box;margin:0}}
body{{width:2000px;background:#0a0e17;color:#fff;font-family:'JetBrains Mono',monospace;padding:28px 44px 40px}}
header{{display:flex;align-items:center;gap:56px;margin-bottom:22px}}
.brand{{background:#0f1726;border-radius:10px;padding:14px 20px}}
.brand svg{{height:76px;width:auto;display:block}}
h1{{font-family:'Archivo Black',sans-serif;font-size:44px;letter-spacing:-.5px}}
h1 em{{font-style:normal;color:#00ff88}}
.row{{display:flex;background:#0f1726;border:1px solid #182234;border-radius:10px;margin-bottom:14px;overflow:hidden;min-height:176px}}
.lab{{width:212px;flex:none;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:12px}}
.lab span{{font-family:'Archivo Black',sans-serif;font-size:76px;line-height:1}}
.lab i{{font-style:normal;font-weight:800;font-size:16px;letter-spacing:2px}}
.coins{{display:flex;flex-wrap:wrap;gap:18px 42px;padding:20px 36px;align-content:center;align-items:flex-start}}
.coin{{width:97px;display:flex;flex-direction:column;align-items:center;gap:12px}}
.ring{{width:97px;height:97px;border-radius:50%;background:#162033;overflow:hidden;display:flex;align-items:center;justify-content:center}}
.ring img{{width:100%;height:100%;object-fit:cover}}
.ph{{font-weight:800;font-size:28px;color:#9fb3c8}}
.coin b{{font-size:21px;font-weight:800;letter-spacing:.5px;white-space:nowrap}}
footer{{display:flex;justify-content:space-between;align-items:flex-end;margin-top:22px;gap:40px}}
footer p{{color:#9fb3c8;font-size:19px;line-height:1.6;max-width:1240px}}
footer a{{color:#00ff88;font-size:34px;font-weight:800;text-decoration:none;white-space:nowrap}}
</style></head><body>
<header><div class="brand">{logo_svg}</div><h1>Revenue-generating <em>altcoin gems</em> tier list</h1></header>
{body}
<footer><p>{html.escape(foot)}</p><a>cymetica.com/gem-screener</a></footer>
</body></html>"""
Path(out_path).with_suffix(".html").write_text(page, encoding="utf-8")

from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome")
    tab = browser.new_page(viewport={"width": 2000, "height": 1200}, device_scale_factor=1)
    tab.goto(Path(out_path).with_suffix(".html").resolve().as_uri())
    tab.wait_for_load_state("networkidle")
    tab.evaluate("document.fonts.ready")
    tab.screenshot(path=out_path, full_page=True)
    browser.close()
print(n, "apps;", {k: len(m) for k, _, _, _, m in rows}, "->", out_path)
