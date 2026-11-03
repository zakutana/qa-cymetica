"""The nine product icons for the Products tab of /company.

Their upload (Logo and line, /static/company/app.js) takes a square PNG, JPG or WebP, scales it to 128 px and
shows it at 46 px, 48 px and 64 px, so these are drawn on a 128 grid and exported at exactly 128 px.
Gem Screener, Agent Casino and Airdrop Farmer keep the mark their live page already shows; Promo Market's is its
live hologram cube. The rest are new, in the same finish.

    python outbox/product-icons/build.py      writes svg/, upload/ and preview.png
"""

from __future__ import annotations

from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
CYAN, GREEN, RED, WHITE, INK, GLASS = "#00cfff", "#00ff88", "#ff4444", "#e6edf7", "#0a0e17", "#0d1520"

DEFS = f"""
  <defs>
    <linearGradient id="g" gradientUnits="userSpaceOnUse" x1="18" y1="14" x2="110" y2="114">
      <stop offset="0" stop-color="{CYAN}"/><stop offset="1" stop-color="{GREEN}"/></linearGradient>
    <radialGradient id="bg" cx=".5" cy=".42" r=".72">
      <stop offset="0" stop-color="#10283a"/><stop offset=".62" stop-color="#0b1420"/><stop offset="1" stop-color="{INK}"/></radialGradient>
    <filter id="soft" x="-40%" y="-40%" width="180%" height="180%"><feGaussianBlur stdDeviation="5"/></filter>
    <filter id="led" x="-80%" y="-80%" width="260%" height="260%">
      <feGaussianBlur stdDeviation="2.4" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
  </defs>"""


def lit(shape: str, opacity: float = .55) -> str:
    """The shape again, blurred behind itself: the family's glow."""
    return f'<g filter="url(#soft)" opacity="{opacity}">{shape}</g>{shape}'


# --- new marks ------------------------------------------------------------------------------------------------------

def team_dump_radar() -> str:
    scope = (f'<circle cx="60" cy="62" r="42" fill="{GLASS}"/>'
             f'<path d="M60 62 L60 20 A42 42 0 0 1 100.4 50.6 Z" fill="{GREEN}" fill-opacity=".34"/>'
             f'<circle cx="60" cy="62" r="23" fill="none" stroke="{CYAN}" stroke-opacity=".42" stroke-width="3"/>'
             f'<path d="M60 22V102M20 62H100" stroke="{CYAN}" stroke-opacity=".28" stroke-width="2.5"/>'
             f'<path d="M60 62 L100.4 50.6" stroke="{GREEN}" stroke-width="4.5" stroke-linecap="round" filter="url(#led)"/>'
             f'<circle cx="38" cy="46" r="4.6" fill="{CYAN}" filter="url(#led)"/>')
    ring = '<circle cx="60" cy="62" r="42" fill="none" stroke="url(#g)" stroke-width="8"/>'
    arrow = "M85 62H101V83H112L93 108L74 83H85Z"
    return (lit(ring) + scope + ring
            + f'<path d="{arrow}" fill="none" stroke="{INK}" stroke-width="9" stroke-linejoin="round"/>'
            + lit(f'<path d="{arrow}" fill="{RED}" stroke="{RED}" stroke-width="2" stroke-linejoin="round"/>', .7))


def supply_analyzer() -> str:
    glass = "M34 26 H94 V36 C94 50 74 56 70 64 C74 72 94 78 94 92 V102 H34 V92 C34 78 54 72 58 64 C54 56 34 50 34 36 Z"
    top = f'<path d="M41 34 H87 V37 C87 45 72 52 64 59 C56 52 41 45 41 37 Z" fill="{CYAN}"/>'
    pile = f'<path d="M40 97 C42 84 56 78 64 74 C72 78 86 84 88 97 Z" fill="{GREEN}"/>'
    caps = (f'<rect x="24" y="15" width="80" height="12" rx="6" fill="url(#g)"/>'
            f'<rect x="24" y="101" width="80" height="12" rx="6" fill="url(#g)"/>')
    return (f'<path d="{glass}" fill="{GLASS}"/>' + lit(top, .5) + lit(pile, .6)
            + f'<circle cx="64" cy="65" r="3" fill="{WHITE}"/><circle cx="64" cy="72" r="2.2" fill="{WHITE}"/>'
            + f'<path d="{glass}" fill="none" stroke="url(#g)" stroke-width="5.5" stroke-linejoin="round"/>'
            + lit(caps, .55))


def build_a_company() -> str:
    tower = "M44 110 V40 L54 30 V22 H74 V30 L84 40 V110 Z"
    wings = f'<path d="M20 110 V70 H44 V110 Z M84 110 V58 H108 V110 Z" fill="{GLASS}" stroke="url(#g)" stroke-width="5.5" stroke-linejoin="round"/>'
    cells = []
    for row, y in enumerate((44, 58, 72, 86)):
        for col, x in enumerate((53, 67)):
            colour = GREEN if (row + col) % 3 == 0 else CYAN
            cells.append(f'<rect x="{x}" y="{y}" width="8" height="9" rx="1.5" fill="{colour}"/>')
    side = "".join(f'<rect x="{x}" y="{y}" width="8" height="7" rx="1.5" fill="{CYAN}" fill-opacity=".8"/>'
                   for x, y in ((28, 80), (28, 94), (92, 68), (92, 82), (92, 96)))
    return ('<g transform="translate(64 66) scale(.88) translate(-64 -60)">' + wings
            + lit(f'<path d="{tower}" fill="none" stroke="url(#g)" stroke-width="6.5" stroke-linejoin="round"/>')
            + f'<path d="{tower}" fill="{GLASS}" stroke="url(#g)" stroke-width="6.5" stroke-linejoin="round"/>'
            + f'<g filter="url(#led)">{"".join(cells)}</g>' + side
            + f'<path d="M64 21V9" stroke="url(#g)" stroke-width="5" stroke-linecap="round"/>'
            + f'<circle cx="64" cy="8" r="4.2" fill="{GREEN}" filter="url(#led)"/>'
            + f'<path d="M12 111 H116" stroke="url(#g)" stroke-width="6.5" stroke-linecap="round"/></g>')


def chart_analyzer() -> str:
    corners = ("M18 40 V26 Q18 18 26 18 H40 M88 18 H102 Q110 18 110 26 V40 "
               "M110 88 V102 Q110 110 102 110 H88 M40 110 H26 Q18 110 18 102 V88")
    bracket = f'<path d="{corners}" fill="none" stroke="url(#g)" stroke-width="7.5" stroke-linecap="round"/>'

    def candle(x: int, top: int, body: int, end: int, bottom: int, colour: str) -> str:
        return (f'<path d="M{x} {top}V{bottom}" stroke="{colour}" stroke-width="4.5" stroke-linecap="round"/>'
                f'<rect x="{x - 8}" y="{body}" width="16" height="{end - body}" rx="3" fill="{colour}"/>')

    candles = candle(40, 62, 70, 92, 99, GREEN) + candle(64, 44, 52, 76, 86, RED) + candle(88, 28, 36, 72, 82, GREEN)
    return lit(bracket, .5) + lit(candles, .55)


def promo_market() -> str:
    beam = (f'<path d="M50 78 L78 78 L90 110 H38 Z" fill="{CYAN}" fill-opacity=".2" filter="url(#soft)"/>'
            f'<ellipse cx="64" cy="110" rx="33" ry="6.5" fill="{GREEN}" fill-opacity=".5" filter="url(#soft)"/>'
            f'<ellipse cx="64" cy="110" rx="23" ry="3.6" fill="{GREEN}" fill-opacity=".85"/>')
    faces = (f'<path d="M64 12 L102 33 L64 54 L26 33 Z" fill="{CYAN}" fill-opacity=".30"/>'
             f'<path d="M26 33 L64 54 V96 L26 75 Z" fill="{CYAN}" fill-opacity=".12"/>'
             f'<path d="M102 33 L64 54 V96 L102 75 Z" fill="{GREEN}" fill-opacity=".20"/>')
    edges = ('<path d="M64 12 L102 33 V75 L64 96 L26 75 V33 Z M26 33 L64 54 L102 33 M64 54 V96" fill="none" '
             'stroke="url(#g)" stroke-width="6" stroke-linejoin="round" stroke-linecap="round"/>')
    return beam + faces + lit(edges, .6) + f'<circle cx="64" cy="54" r="6" fill="{WHITE}" filter="url(#led)"/>'


def infiltrator() -> str:
    bubble = ("M30 20 H98 Q112 20 112 34 V76 Q112 90 98 90 H56 L33 111 V90 H30 Q16 90 16 76 V34 Q16 20 30 20 Z")
    eye = "M28 55 C42 33 86 33 100 55 C86 77 42 77 28 55 Z"
    return ('<g transform="translate(64 64) scale(.9) translate(-64 -64)">'
            + lit(f'<path d="{bubble}" fill="none" stroke="url(#g)" stroke-width="8" stroke-linejoin="round"/>')
            + f'<path d="{bubble}" fill="{GLASS}" stroke="url(#g)" stroke-width="8" stroke-linejoin="round"/>'
            + f'<path d="{eye}" fill="{INK}" stroke="{WHITE}" stroke-width="5" stroke-linejoin="round"/>'
            + f'<circle cx="64" cy="55" r="14.5" fill="url(#g)" filter="url(#led)"/>'
            + f'<circle cx="64" cy="55" r="6.5" fill="{INK}"/><circle cx="69" cy="50" r="3" fill="{WHITE}"/></g>')


def pitch_cards() -> str:
    """Nexus pitches, you swipe: a card with a rising line, the card behind it, and the swipe to the right."""
    back = (f'<g transform="rotate(-13 52 66)"><rect x="24" y="22" width="52" height="76" rx="10" fill="{GLASS}" '
            f'stroke="{CYAN}" stroke-opacity=".55" stroke-width="4.5"/></g>')
    line = "M41 88 L52 78 L60 83 L74 56"
    front = (f'<g transform="rotate(7 58 64)">'
             f'<rect x="30" y="24" width="56" height="80" rx="10" fill="{GLASS}" stroke="url(#g)" stroke-width="6"/>'
             f'<rect x="40" y="35" width="22" height="5" rx="2.5" fill="{WHITE}" fill-opacity=".85"/>'
             f'<path d="{line}" fill="none" stroke="{GREEN}" stroke-width="5.5" stroke-linecap="round" stroke-linejoin="round" filter="url(#led)"/>'
             f'<circle cx="74" cy="56" r="5.5" fill="{WHITE}" filter="url(#led)"/>'
             f'<rect x="40" y="94" width="36" height="3.5" rx="1.75" fill="{CYAN}" fill-opacity=".5"/></g>')
    swipe = (f'<path d="M86 64 H112 M101 52 L113 64 L101 76" fill="none" stroke="{GREEN}" stroke-width="7" '
             f'stroke-linecap="round" stroke-linejoin="round"/>')
    cards = back + lit(front, .4)
    return f'<g transform="translate(46 64) scale(.84) translate(-58 -64)">{cards}</g><g filter="url(#led)">{swipe}</g>'


def capital_maximizer() -> str:
    """The product's own mark, logo-12 (Hologram Dollar), the one its spec and its page header use, in the 128 frame."""
    import re
    svg = (HERE.parent / "capital-maximizer" / "logos" / "logo-12.svg").read_text(encoding="utf-8")
    inner = re.sub(r"^\s*<svg[^>]*>|</svg>\s*$", "", svg.strip())
    return f'<g transform="translate(64 64) scale(1.78) translate(-32 -32)">{inner}</g>'


# --- the marks their live pages already show ------------------------------------------------------------------------

def gem_screener() -> str:
    facets = [("22,54 42,32 50,54", "#ffffff", .2), ("42,32 64,32 50,54", "#ffffff", .42), ("50,54 64,32 78,54", "#ffffff", .8),
              ("64,32 86,32 78,54", "#ffffff", .1), ("86,32 106,54 78,54", "#04070d", .06), ("22,54 50,54 64,100", "#04070d", .16),
              ("50,54 64,54 64,100", "#04070d", .02), ("64,54 78,54 64,100", "#04070d", .12), ("78,54 106,54 64,100", "#04070d", .24)]
    gem = "".join(f'<polygon points="{p}" fill="url(#gg)"/><polygon points="{p}" fill="{c}" fill-opacity="{o}"/>'
                  f'<polygon points="{p}" fill="none" stroke="{INK}" stroke-width="1.7" stroke-linejoin="round"/>' for p, c, o in facets)
    grad = (f'<linearGradient id="gg" gradientUnits="userSpaceOnUse" x1="22" y1="32" x2="106" y2="100">'
            f'<stop offset="0" stop-color="{CYAN}"/><stop offset="1" stop-color="{GREEN}"/></linearGradient>')
    halo = '<polygon points="22,54 42,32 86,32 106,54 64,100" fill="url(#gg)" filter="url(#soft)" opacity=".5"/>'
    return f'<defs>{grad}</defs><g transform="translate(64 64) scale(1.12) translate(-64 -66)">{halo}{gem}</g>'


def agent_casino() -> str:
    grad = (f'<linearGradient id="at" gradientUnits="userSpaceOnUse" x1="4" y1="4" x2="44" y2="44">'
            f'<stop offset="0" stop-color="{CYAN}"/><stop offset="1" stop-color="{GREEN}"/></linearGradient>')
    return (f'<defs>{grad}</defs><g transform="translate(64 64) scale(2.05) translate(-24 -24)">'
            f'<circle cx="24" cy="24" r="21.5" fill="none" stroke="url(#at)" stroke-width="3.6" filter="url(#soft)" opacity=".5"/>'
            f'<circle cx="24" cy="24" r="21.5" fill="{GLASS}" stroke="url(#at)" stroke-width="3.6"/>'
            f'<circle cx="24" cy="24" r="21.5" fill="none" stroke="{WHITE}" stroke-width="3.6" stroke-dasharray="5 11.886" stroke-dashoffset="2.5" opacity=".92"/>'
            f'<circle cx="24" cy="24" r="15.2" fill="none" stroke="url(#at)" stroke-width="1.3" stroke-dasharray="1.6 2.4" opacity=".75"/>'
            f'<rect x="16.2" y="18.5" width="5.6" height="11" rx="2.8" fill="{CYAN}"/>'
            f'<rect x="26.2" y="18.5" width="5.6" height="11" rx="2.8" fill="{GREEN}"/></g>')


def airdrop_farmer() -> str:
    grads = (f'<linearGradient id="afg" gradientUnits="userSpaceOnUse" x1="2" y1="20" x2="62" y2="60">'
             f'<stop offset="0" stop-color="{CYAN}"/><stop offset="1" stop-color="{GREEN}"/></linearGradient>'
             f'<linearGradient id="afh" x1="0" y1="0" x2="0" y2="1">'
             f'<stop offset="0" stop-color="{GREEN}"/><stop offset="1" stop-color="{CYAN}"/></linearGradient>'
             '<filter id="afglow" x="-80%" y="-80%" width="260%" height="260%"><feGaussianBlur stdDeviation="1.4" result="b"/>'
             '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>')
    return (f'<defs>{grads}</defs><g transform="translate(64 64) scale(1.72) translate(-32 -31)">'
            '<circle cx="32" cy="41" r="17" fill="#070b10" stroke="url(#afg)" stroke-width="3"/>'
            f'<circle cx="32" cy="41" r="12" fill="none" stroke="{CYAN}" stroke-opacity=".4" stroke-width="1" stroke-dasharray="1.6 2.6"/>'
            f'<rect x="24.5" y="37" width="5" height="9" rx="2.5" fill="{GREEN}" filter="url(#afglow)"/>'
            f'<rect x="34.5" y="37" width="5" height="9" rx="2.5" fill="{GREEN}" filter="url(#afglow)"/>'
            '<path d="M20.5 25.5 L22.6 14.6 Q23.2 12 26 12 Q32 14.2 38 12 Q40.8 12 41.4 14.6 L43.5 25.5 Z" fill="url(#afh)"/>'
            '<path d="M21.2 21.6 Q32 19.6 42.8 21.6" stroke="#070b10" stroke-width="2.6" fill="none"/>'
            '<path d="M2.5 30 C8 25.2 15 24 22 24 L42 24 C49 24 56 25.2 61.5 30 C50 30.6 40 31.8 32 31.8 C24 31.8 14 30.6 2.5 30 Z" fill="url(#afg)"/>'
            f'<path d="M32 12.5 V5.8" stroke="{GREEN}" stroke-width="1.9" stroke-linecap="round"/>'
            f'<path d="M31.8 8 C27.6 8 25.5 5.8 25 2.6 C28.8 2.6 31.3 4.6 31.8 8 Z" fill="{GREEN}"/>'
            f'<path d="M32.2 6.6 C36.4 6.6 38.8 4.1 39.3 0.9 C35.2 0.9 32.7 3 32.2 6.6 Z" fill="{CYAN}"/></g>')


# The order of the row on the Products tab; the figures are the operator's screenshot of 2026-11-02.
ICONS = [("team-dump-radar", "Team Dump Radar", "/team-dump-radar", team_dump_radar, 434, 11),
         ("gem-screener", "Gem Screener", "Revenue-generating altcoins", gem_screener, 195, 183),
         ("supply-analyzer", "Supply Analyzer", "/supply-analyzer", supply_analyzer, 195, 49),
         ("agent-casino", "Agent Casino", "/agent-casino", agent_casino, 158, 213),
         ("build-a-company", "Build a Company", "/company", build_a_company, 130, 52),
         ("chart-analyzer", "Chart Analyzer", "/chart-analyzer", chart_analyzer, 121, 303),
         ("promo-market", "Promo Market", "/creator-dashboard", promo_market, 32, 2),
         ("airdrop-farmer", "Airdrop Farmer", "Deposit USDC and do nothing", airdrop_farmer, 23, 28),
         ("infiltrator", "Infiltrator", "/infiltrator", infiltrator, 0, 18),
         ("pitch-cards", "Pitch Cards", "/pitch-cards", pitch_cards, 0, 3),
         ("capital-maximizer", "Capital Maximizer", "/capital-maximizer", capital_maximizer, 0, 4)]


def svg_of(draw) -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128" width="128" height="128">{DEFS}'
            f'<rect width="128" height="128" fill="url(#bg)"/>{draw()}</svg>')


def preview_html(uri: dict) -> str:
    """The icons large, then in the Products tab's own row at its 46 px (style.css .pflogo)."""
    big = "".join(f'<figure><img src="{uri[s]}" width="256" height="256"><figcaption>{n}</figcaption></figure>'
                  for s, n, *_ in ICONS)
    row = "".join(f'<div class="card"><div class="h"><span class="pflogo"><img src="{uri[s]}"></span><div><b>{n}</b><small>{p}</small></div></div>'
                  f'<div class="n"><div><u>{a}</u><small>UNIQUE VISITORS</small></div><div><u>{b}</u><small>USES</small></div></div></div>'
                  for s, n, p, _, a, b in ICONS)
    return f"""<!doctype html><meta charset="utf-8"><style>
    body {{ margin: 0; padding: 28px; width: 1460px; background: #0a0e17; color: #e6edf7; font-family: 'Segoe UI', sans-serif; }}
    .big {{ display: grid; grid-template-columns: repeat(5, 256px); gap: 24px 32px; margin-bottom: 34px; }}
    figure {{ margin: 0; }} figure img {{ display: block; border-radius: 66px; border: 1px solid #1c2a3c; }}
    figcaption {{ margin-top: 10px; font: 700 15px 'Segoe UI', sans-serif; color: #a9bfcd; text-align: center; }}
    .row {{ display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px; }}
    .card {{ background: linear-gradient(#111a27, #0d1520); border: 1px solid #1c2a3c; border-radius: 12px; padding: 12px; }}
    .h {{ display: flex; gap: 10px; align-items: center; margin-bottom: 12px; }} .h b {{ font-size: 13px; display: block; }} .h small {{ font-size: 10px; color: #7f93ad; }}
    .pflogo {{ flex: none; width: 46px; height: 46px; border-radius: 12px; overflow: hidden; display: grid; place-items: center; background: #0d1522; border: 1px solid #243449; }}
    .pflogo img {{ width: 100%; height: 100%; object-fit: cover; display: block; }}
    .n {{ display: flex; gap: 34px; }} .n u {{ text-decoration: none; font: 800 19px Consolas, monospace; display: block; }} .n small {{ font: 600 8px Consolas, monospace; color: #7f93ad; }}
    </style><div class="big">{big}</div><div class="row">{row}</div>"""


def main() -> None:
    (HERE / "svg").mkdir(exist_ok=True)
    (HERE / "upload").mkdir(exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 128, "height": 128})
        for slug, _, _, draw, *_ in ICONS:
            svg = svg_of(draw)
            (HERE / "svg" / f"{slug}.svg").write_text(svg, encoding="utf-8")
            page.set_content(f'<!doctype html><style>html,body{{margin:0;background:{INK}}}svg{{display:block}}</style>{svg}')
            page.screenshot(path=str(HERE / "upload" / f"{slug}.png"), clip={"x": 0, "y": 0, "width": 128, "height": 128})
        sheet = browser.new_page(viewport={"width": 1516, "height": 900}, device_scale_factor=1.5)
        # The preview is built from the exported PNGs, so what it shows is what gets uploaded.
        import base64
        uri = {s: "data:image/png;base64," + base64.b64encode((HERE / "upload" / f"{s}.png").read_bytes()).decode()
               for s, *_ in ICONS}
        sheet.set_content(preview_html(uri))
        sheet.screenshot(path=str(HERE / "preview.png"), full_page=True)
        browser.close()


if __name__ == "__main__":
    main()
