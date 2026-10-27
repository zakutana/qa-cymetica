"""The v3 changes, laid on top of THEIR live Promo Market v2 (ET-32929): their HTML, their promo_market_v2.js, their CSS.

Nothing is redrawn. serve.py feeds this their files and this changes only what v3 changes:

  * the page: the boot block says who is looking (the owner on /expire76, a stranger on /promo-market), v3.css is
    linked after their stylesheet, and the owner's top bar gets the bell for promoters who want a brief;
  * their script: v3.js is spliced in at the end of their own closure, so its function declarations replace theirs
    of the same name (Post a brief, the brief card) and it calls their helpers as they are; the market draws the
    protection band above Open briefs; a promoter's drawer asks for the X handle and shows the offer; the owner's
    brief page shows the offers; the drawer's "own deposit" line says the rule their tooltip already says.
  * ?v2 on either page serves their script untouched, with the same sample brief (sample.py), to compare.

Every anchor must match their file exactly once. When they change it, the mirror says so instead of showing the
operator an unchanged page (tests/repo/test_promo_market_v3_mirror.py).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent

TAIL = "  route(false);\n  bootStart();\n})();"
JS_ANCHORS = (
    # (their text, ours, how many times it is in their file)
    # the protection band, right above Open briefs (the operator, 2026-10-27: "nad to Open briefs ... user protection")
    ("'<section id=\"board\">", "v3Protect() + '<section id=\"board\">", 1),
    # their tooltip says fees, their label says a deposit; the rule is the fees (how-counted, "Costs more to fake").
    # Twice: the brief's drawer and their Post a brief (which v3.js replaces whole)
    ("'signed up, own deposit, 14-day check'", "'signed up, spent at least this on Cymetica in 14 days'", 2),
    # a post priced by reach has no one price: the brief's drawer and its owner page leave the v2 price out
    (".filter((p) => +b[p[0]] > 0);", ".filter((p) => +b[p[0]] > 0 && !(b.post_by_reach && p[0] === 'per_post_usdc'));", 2),
    # the promoter's drawer: their X handle in, the offer out, above Take it
    ("(tk ? '<div class=\"mylink\">", "v3OfferBox(b, tk) + (tk ? '<div class=\"mylink\">", 1),
    # the owner's brief page: the offers, right under the numbers (the operator: "kdyz kliknu na brief ... tam to chci
    # nejak videt ty nabidky"); they replace v2's Quotes from promoters, which asked a promoter to name a price
    ("'<div class=\"g2\"><div class=\"card pad\"><div class=\"ch\"><h3>Visitors by day</h3>",
     "v3Offers(b, r) + '<div class=\"g2\"><div class=\"card pad\"><div class=\"ch\"><h3>Visitors by day</h3>", 1),
    ("'<div class=\"card pad\"><div class=\"ch\"><h3>Quotes from promoters</h3>",
     "'<div class=\"card pad v3gone\"><div class=\"ch\"><h3>Quotes from promoters</h3>", 1),
)


class AnchorMissing(RuntimeError):
    pass


def patch_js(js: str) -> str:
    js = js.replace("\r\n", "\n")
    for old, new, times in JS_ANCHORS:
        if js.count(old) != times:
            raise AnchorMissing(f"v3: {old!r} is in their promo_market_v2.js {js.count(old)} times, not {times}")
        js = js.replace(old, new)
    if js.count(TAIL) != 1:
        raise AnchorMissing("v3: the end of their closure (route(false); bootStart();) is not where it was")
    v3 = (HERE / "v3.js").read_text(encoding="utf-8")
    return js.replace(TAIL, v3.rstrip() + "\n\n" + TAIL)


BOOT = re.compile(r'(<script id="pm2-boot" type="application/json">)(.*?)(</script>)', re.S)
BELL = ('<button class="v3bell" id="v3bell" data-v3inbox="1" aria-label="Promoters who want your briefs">'
        '<svg width="18" height="18" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6" '
        'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 14.5V9a5 5 0 0 1 10 0v5.5l1.5 1.5h-13z '
        'M8.3 17.5a1.9 1.9 0 0 0 3.4 0"/></svg><i id="v3belln">3</i></button>')


# the operator flips between the two with one click, on the same page and the same sample brief
SWITCH = ('<div id="v3switch" style="position:fixed;left:16px;bottom:16px;z-index:90;display:flex;gap:2px;padding:3px;border-radius:10px;'
          'background:rgba(6,9,15,.92);border:1px solid rgba(0,207,255,.35);font:600 12px JetBrains Mono,monospace">'
          '<a href="#" data-v="v2" style="padding:6px 10px;border-radius:7px;color:{c2};background:{b2}">LIVE NOW · v2</a>'
          '<a href="#" data-v="v3" style="padding:6px 10px;border-radius:7px;color:{c3};background:{b3}">WILL BE · v3</a></div>'
          '<script>document.getElementById("v3switch").addEventListener("click",function(e){{var a=e.target.closest("a");if(!a)return;'
          'e.preventDefault();location.href=location.pathname+(a.dataset.v==="v2"?"?v2":"")+location.hash;}});</script>')
ON, OFF = ("#06090f", "#00ff88"), ("#8fa3bf", "transparent")


def patch_html(page: str, html: str, version: str = "v3") -> str:
    """page: 'owner' (/expire76, the operator signed in) or 'market' (/promo-market, a stranger); version 'v2' is
    their page as it is today, with the same sample brief, so the two can be compared."""
    m = BOOT.search(html)
    if not m:
        raise AnchorMissing("v3: their page has no pm2-boot block")
    boot = json.loads(m.group(2))
    if page == "owner":
        boot.update(signed_in=True, is_owner=True, viewer_name="expire76")
    else:
        boot.update(tab="market")
    html = html[:m.start(2)] + json.dumps(boot) + html[m.end(2):]
    if page == "market":
        html = html.replace("https://cymetica.com/creator-dashboard", "https://cymetica.com/promo-market")
        html = html.replace('href="/creator-dashboard?view=classic"', 'href="/promo-market?view=classic"')
    (c2, b2), (c3, b3) = (ON, OFF) if version == "v2" else (OFF, ON)
    html = html.replace("</body>", SWITCH.format(c2=c2, b2=b2, c3=c3, b3=b3) + "\n</body>", 1)
    if version == "v2":
        if 'promo_market_v2.js?' not in html:
            raise AnchorMissing("v3: their page no longer loads promo_market_v2.js")
        return html.replace("promo_market_v2.js?", "promo_market_v2.js?raw=1&", 1)
    if page == "owner":
        if '<span class="livechip"' not in html:
            raise AnchorMissing("v3: their top bar has no livechip to put the bell beside")
        html = html.replace('<span class="livechip"', BELL + '<span class="livechip"', 1)
    return html.replace("</head>", '<link rel="stylesheet" href="/__v3/v3.css">\n</head>', 1)
