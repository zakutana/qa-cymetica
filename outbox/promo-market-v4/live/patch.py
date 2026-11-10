"""The v4 changes, laid on top of THEIR live Promo Market (v2 with the v3 look they shipped as ET-33031): their HTML,
their promo_market_v2.js, their CSS. Nothing is redrawn: serve.py feeds this their files and this changes only what
v4 changes.

  * the page: the boot block says who is looking (the brief's owner, the promoter, or a stranger), v4.css is linked
    after their stylesheets, and a small bar at the bottom left is the mock's own (day +N, reset, a sample, the other
    window): it is not part of what is asked for;
  * their script: v4.js goes at the end of their own closure, so its function declarations replace theirs of the
    same name (the market's cards, Post a brief, the drawer, the owner's brief page, Briefs I took) and it calls
    their helpers as they are; seven small text anchors change the market's hero and its fold, and four rename a
    function of theirs that v4.js wraps.

Every anchor must match their file exactly the number of times it says. When they change their file the mirror says
so instead of showing the operator an unchanged page (tests/self/test_promo_market_v4_mirror.py).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent

TAIL = "  route(false);\n  bootStart();\n})();"
JS_ANCHORS = (
    # (their text, ours, how many times it is in their file)
    ("tile('coin', 'USDC up for grabs', '<span class=\"pos\">' + usd(st.up_for_grabs_usdc || 0) + '</span><small>USDC</small>', 'every open brief', 'rgb(0,255,136)')",
     "tile('coin', 'Left in open briefs', v4left(), 'every open brief', 'rgb(0,255,136)')", 1),
    ("tile('users', 'Top pay per new user', usd(st.top_per_user_usdc || 0) + '<small>USDC</small>', st.top_per_user_name ? esc(shortName(st.top_per_user_name)) : 'no brief yet', 'rgb(59,130,246)')",
     "tile('clock', 'Paid after', '3<small>days up</small>', 'a post that stayed up', 'rgb(59,130,246)')", 1),
    ("[['left', 'Most up for grabs'], ['user', 'Best per new user'], ['ending', 'Ending soon']]", "[]", 1),
    ("'How new users, visitors and X accounts are counted <span class=\"dim num\">'", "'How offers are paid <span class=\"dim num\">'", 1),
    ("esc(H.h1).replace('Get paid in USDC.', '<span>Get paid in USDC.</span>')", "esc(H.h1).replace('Get paid.', '<span>Get paid.</span>')", 1),
    # a brief is covered by the owner's Cymetica credit, not read from a wallet on-chain
    ("tile('briefs', 'Open briefs', fmt(st.open_briefs || 0), 'funds checked on-chain')",
     "tile('briefs', 'Open briefs', fmt(st.open_briefs || 0), 'covered by the owner\\'s credit')", 1),
    ("Your budget stays in your own wallet, checked on-chain.", "Covered by your Cymetica credit, locked only when you accept a promoter.", 1),
    # four of theirs that v4.js wraps instead of replacing (Open briefs in the menu, the banner on Today, the count on
    # Market, a redraw that keeps what is typed): theirs gets another name, ours calls it
    ("function rail(tab) {", "function rail0(tab) {", 1),
    ("function today() {", "function today0() {", 1),
    ("function chrome(r) {", "function chrome0(r) {", 2),
    ("function rerender() {", "function rerender0() {", 1),
)


class AnchorMissing(RuntimeError):
    pass


def patch_js(js: str) -> str:
    js = js.replace("\r\n", "\n")
    for old, new, times in JS_ANCHORS:
        if js.count(old) != times:
            raise AnchorMissing(f"v4: {old[:70]!r} is in their promo_market_v2.js {js.count(old)} times, not {times}")
        js = js.replace(old, new)
    if js.count(TAIL) != 1:
        raise AnchorMissing("v4: the end of their closure (route(false); bootStart();) is not where it was")
    v4 = (HERE / "v4.js").read_text(encoding="utf-8") if (HERE / "v4.js").exists() else ""
    return js.replace(TAIL, "/* promo market v4 */\n" + v4.rstrip() + "\n\n" + TAIL)


BOOT = re.compile(r'(<script id="pm2-boot" type="application/json">)(.*?)(</script>)', re.S)
BELL = ('<button class="v3bell" id="v3bell" data-v3inbox="1" aria-label="Offers waiting for you">'
        '<svg width="18" height="18" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6" '
        'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 14.5V9a5 5 0 0 1 10 0v5.5l1.5 1.5h-13z '
        'M8.3 17.5a1.9 1.9 0 0 0 3.4 0"/></svg><i id="v3belln">0</i></button>')

# the mock's own bar: not asked for, not in the pictures; it lets the operator click a 3-day wait and the other window
BAR = ('<div id="v4bar" style="position:fixed;left:16px;bottom:70px;z-index:90;display:flex;gap:6px;align-items:center;padding:5px 8px;border-radius:10px;'
       'background:rgba(6,9,15,.94);border:1px solid rgba(0,207,255,.35);font:600 12px JetBrains Mono,monospace;color:#8fa3bf">'
       '<span style="color:#00cfff">MOCK</span><span id="v4day">day +0</span>'
       '<button data-v4="skip" style="{b}">+1 day</button>'
       '<select id="v4seed" style="{b}"><option value="">sample…</option><option>open</option><option>requested</option><option>approved</option><option>posted</option><option>ready</option><option>paid</option><option>cancelled</option></select>'
       '<button data-v4="reset" style="{b}">Reset</button>'
       '<a href="{owner}" style="{b}text-decoration:none">Owner</a><a href="{promoter}" style="{b}text-decoration:none">Promoter</a></div>'
       '<script>(function(){{var bar=document.getElementById("v4bar");'
       'function go(p,b){{return fetch(p,{{method:"POST",headers:{{"Content-Type":"application/json"}},body:JSON.stringify(b||{{}})}}).then(function(){{location.reload();}});}}'
       'fetch("/__v4/state").then(function(r){{return r.json();}}).then(function(s){{document.getElementById("v4day").textContent="day +"+Math.round(s.offset*10)/10;}});'
       'bar.addEventListener("click",function(e){{var t=e.target.closest("[data-v4]");if(!t)return;'
       'if(t.dataset.v4==="skip")go("/__v4/skip",{{days:1}});if(t.dataset.v4==="reset")go("/__v4/reset");}});'
       'document.getElementById("v4seed").addEventListener("change",function(e){{if(e.target.value)go("/__v4/seed",{{stage:e.target.value}});}});}})();</script>')
BTN = "background:#0f1726;color:#e6edf6;border:1px solid #1d2a40;border-radius:7px;padding:5px 9px;font:600 12px JetBrains Mono,monospace;cursor:pointer;"
WINDOWS = ("http://127.0.0.1:8792/expire76#me/products", "http://127.0.0.1:8808/promoter#me/today")
WHO = {"owner": dict(signed_in=True, is_owner=True, viewer_name="owner_demo", v4role="owner"),
       # the promoter lands where Cymetica's Telegram message sends creators: the Creator Dashboard, on Today
       "promoter": dict(signed_in=True, is_owner=True, viewer_name="promoter_demo", creator="promoter_demo", creator_path="/promoter", tab="me/today", v4role="promoter"),
       "market": dict(tab="market")}


def patch_html(page: str, html: str) -> str:
    """page: 'owner' (the brief's owner, signed in), 'promoter' (signed in, taking offers) or 'market' (a stranger)."""
    m = BOOT.search(html)
    if not m:
        raise AnchorMissing("v4: their page has no pm2-boot block")
    boot = json.loads(m.group(2))
    boot.update(WHO[page])
    html = html[:m.start(2)] + json.dumps(boot) + html[m.end(2):]
    if page == "market":
        html = html.replace("https://cymetica.com/creator-dashboard", "https://cymetica.com/promo-market")
        html = html.replace('href="/creator-dashboard?view=classic"', 'href="/promo-market?view=classic"')
    html = html.replace("</body>", BAR.format(b=BTN, owner=WINDOWS[0], promoter=WINDOWS[1]) + "\n</body>", 1)
    if page == "owner" and 'id="v3bell"' not in html:
        if '<span class="livechip"' not in html:
            raise AnchorMissing("v4: their top bar has no livechip to put the bell beside")
        html = html.replace('<span class="livechip"', BELL + '<span class="livechip"', 1)
    return html.replace("</head>", '<link rel="stylesheet" href="/__v4/v4.css">\n</head>', 1)
