"""The v4 pictures drawn in SVG: the NEXUS coach, the ET10 coin, the small clock, the hero tiles' icons, the risk gauge.

Shaded with gradients so they read as objects, not line art (the operator, 2026-10-26, on the first coach: "ma to byt 5x
lepsi top krasna ikonka tak do 3D"). Only the site's colours and darker shades of their cyan, green and blue; no orange,
purple or gold (read-the-vendors-design-rule). Every gradient lives once in SPRITE, which the patch puts in each page.
"""
from __future__ import annotations

import math

# ------------------------------------------------------------------------------------------------ shared gradients

SPRITE = """<svg class="v4-sprite" aria-hidden="true" focusable="false" style="position:absolute;width:0;height:0;overflow:hidden"><defs>
<radialGradient id="v4-face" cx="34%" cy="28%" r="85%"><stop offset="0" stop-color="#1e3050"></stop><stop offset=".5" stop-color="#0d1520"></stop><stop offset="1" stop-color="#06090f"></stop></radialGradient>
<linearGradient id="v4-edge" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#00a3cc"></stop><stop offset=".5" stop-color="#005f7a"></stop><stop offset="1" stop-color="#002633"></stop></linearGradient>
<linearGradient id="v4-rim" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#7FE6FF"></stop><stop offset=".5" stop-color="#00cfff"></stop><stop offset="1" stop-color="#00ff88"></stop></linearGradient>
<linearGradient id="v4-bar-c" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#7FE6FF"></stop><stop offset=".45" stop-color="#00cfff"></stop><stop offset="1" stop-color="#007a99"></stop></linearGradient>
<linearGradient id="v4-bar-g" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#66ffb8"></stop><stop offset=".45" stop-color="#00ff88"></stop><stop offset="1" stop-color="#00995a"></stop></linearGradient>
<radialGradient id="v4-hat" cx="32%" cy="22%" r="90%"><stop offset="0" stop-color="#3b82f6"></stop><stop offset=".4" stop-color="#1e3a6e"></stop><stop offset=".8" stop-color="#16233a"></stop><stop offset="1" stop-color="#0a0e17"></stop></radialGradient>
<linearGradient id="v4-hat-shade" x1="0" y1="0" x2="1" y2="1"><stop offset=".35" stop-color="#06090f" stop-opacity="0"></stop><stop offset="1" stop-color="#06090f" stop-opacity=".75"></stop></linearGradient>
<linearGradient id="v4-brim" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#2a4f8f"></stop><stop offset="1" stop-color="#16233a"></stop></linearGradient>
<linearGradient id="v4-brim-under" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#0a0e17"></stop><stop offset="1" stop-color="#06090f"></stop></linearGradient>
<pattern id="v4-plaid" width="13" height="13" patternUnits="userSpaceOnUse" patternTransform="rotate(-14)"><path d="M0 3.5h13M0 9.5h13" stroke="#00cfff" stroke-opacity=".32" stroke-width="1.1"></path><path d="M3.5 0v13M9.5 0v13" stroke="#93c5fd" stroke-opacity=".28" stroke-width="2.2"></path></pattern>
<linearGradient id="v4-band" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#00995a"></stop><stop offset=".45" stop-color="#00ff88"></stop><stop offset="1" stop-color="#00995a"></stop></linearGradient>
<linearGradient id="v4-metal" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#F3F7FC"></stop><stop offset=".3" stop-color="#A9B8CC"></stop><stop offset=".55" stop-color="#5b6b82"></stop><stop offset=".8" stop-color="#E6EDF7"></stop><stop offset="1" stop-color="#7f93ad"></stop></linearGradient>
<radialGradient id="v4-lens" cx="38%" cy="34%" r="75%"><stop offset="0" stop-color="#7FE6FF" stop-opacity=".45"></stop><stop offset=".6" stop-color="#00cfff" stop-opacity=".10"></stop><stop offset="1" stop-color="#00cfff" stop-opacity=".30"></stop></radialGradient>
<linearGradient id="v4-handle" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#0d1520"></stop><stop offset=".45" stop-color="#2a4f8f"></stop><stop offset="1" stop-color="#0a0e17"></stop></linearGradient>
<radialGradient id="v4-glow" cx="50%" cy="50%" r="50%"><stop offset="0" stop-color="#00cfff" stop-opacity=".38"></stop><stop offset=".55" stop-color="#00ff88" stop-opacity=".08"></stop><stop offset="1" stop-color="#00cfff" stop-opacity="0"></stop></radialGradient>
<radialGradient id="v4-coin" cx="34%" cy="28%" r="80%"><stop offset="0" stop-color="#7FE6FF"></stop><stop offset=".45" stop-color="#00cfff"></stop><stop offset="1" stop-color="#006680"></stop></radialGradient>
<radialGradient id="v4-coin-g" cx="34%" cy="28%" r="80%"><stop offset="0" stop-color="#66ffb8"></stop><stop offset=".45" stop-color="#00ff88"></stop><stop offset="1" stop-color="#007a46"></stop></radialGradient>
<linearGradient id="v4-pod-1" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#66ffb8"></stop><stop offset="1" stop-color="#00995a"></stop></linearGradient>
<linearGradient id="v4-pod-2" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#7FE6FF"></stop><stop offset="1" stop-color="#007a99"></stop></linearGradient>
<linearGradient id="v4-pod-3" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#93c5fd"></stop><stop offset="1" stop-color="#1d4ed8"></stop></linearGradient>
<linearGradient id="v4-glass" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#F3F7FC" stop-opacity=".42"></stop><stop offset="1" stop-color="#F3F7FC" stop-opacity="0"></stop></linearGradient>
<filter id="v4-blur" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="6"></feGaussianBlur></filter>
<filter id="v4-glowf" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="2.4" result="b"></feGaussianBlur><feMerge><feMergeNode in="b"></feMergeNode><feMergeNode in="SourceGraphic"></feMergeNode></feMerge></filter>
<symbol id="v4-et10" viewBox="0 0 32 32">
 <ellipse cx="17.2" cy="17" rx="13" ry="13" fill="#004d66"></ellipse>
 <circle cx="15" cy="15" r="13" fill="url(#v4-coin)"></circle>
 <circle cx="15" cy="15" r="10" fill="none" stroke="#06090f" stroke-opacity=".35" stroke-width="1.1" stroke-dasharray="1.6 1.6"></circle>
 <text x="15" y="19" text-anchor="middle" font-family="Archivo Black, sans-serif" font-size="10.5" fill="#06090f">10</text>
 <path d="M5.6 11.5 A10.5 10.5 0 0 1 12 4.6" fill="none" stroke="#F3F7FC" stroke-opacity=".75" stroke-width="1.6" stroke-linecap="round"></path>
</symbol>
</defs></svg>"""


def coin(cls: str = "v4-coin") -> str:
    return f'<svg class="{cls}" viewBox="0 0 32 32" aria-hidden="true"><use href="#v4-et10"></use></svg>'


# ------------------------------------------------------------------------------------------------ the stopwatch
# The operator, 2026-10-26, on the flat rings: "ty stopky vypadaji moc basic porad trapne". So a stopwatch as an object:
# a brushed-metal bezel and crown, a dark glass face with a minute track, the time gone as a lit arc with a bright tip,
# and a reflection across the glass.

def stopwatch(frac: float, label: str = "", live: bool = False, detail: bool = True) -> str:
    """And the next look: "to je preplacane moc". So the object stays (a metal bezel and crown, a dark face, the lit arc)
    and everything else goes: no minute track, no side button, no glass sheen, no shadow; four quiet quarter marks."""
    cx, cy, r = 32.0, 40.0, 26.0
    ar = 19.0 if detail else 17.0
    marks = "".join(f'<line class="mk" x1="{cx}" y1="{cy - r + 1.5}" x2="{cx}" y2="{cy - r + 4.5}" transform="rotate({a} {cx} {cy})"></line>'
                    for a in (0, 90, 180, 270)) if detail else ""
    tip = ""
    if 0 < frac < 1:
        t = 2 * math.pi * frac
        tip = f'<circle class="tip" cx="{cx + ar * math.sin(t):.2f}" cy="{cy - ar * math.cos(t):.2f}" r="{2.4 if detail else 3.4}"></circle>'
    text = f'<text x="{cx}" y="{cy + 4.6}" text-anchor="middle">{label}</text>' if label else ""
    return (f'<svg class="v4-watch{" live" if live else ""}" viewBox="0 0 64 70" aria-hidden="true">'
            f'<rect x="27.5" y="2.5" width="9" height="5.5" rx="2" fill="url(#v4-metal)"></rect>'
            f'<rect x="30" y="7.5" width="4" height="7" fill="url(#v4-metal)"></rect>'
            f'<circle cx="{cx}" cy="{cy}" r="{r + 1.5}" fill="url(#v4-face)" stroke="url(#v4-metal)" stroke-width="3.4"></circle>'
            f'{marks}<circle class="tr" cx="{cx}" cy="{cy}" r="{ar}"></circle>'
            f'<circle class="pg" cx="{cx}" cy="{cy}" r="{ar}" pathLength="100" stroke-dasharray="{frac * 100:.1f} 100" '
            f'transform="rotate(-90 {cx} {cy})" stroke="url(#v4-rim)"></circle>{tip}{text}</svg>')


def mini_clock(frac: float, live: bool) -> str:
    """The same stopwatch for a card's length pill: no minute track, a thicker arc, so it still reads at 22 px."""
    return stopwatch(frac, live=live, detail=False)


# ------------------------------------------------------------------------------------------------ the hero tiles

def hero_tiles() -> str:
    clocks = "".join(f'<div class="v4-durbig">{stopwatch(f, d)}</div>' for d, f in (("1H", 1 / 24), ("5H", 5 / 24), ("1D", 1.0)))
    podium = ('<svg class="v4-podium" viewBox="0 0 150 74" aria-hidden="true">'
              '<rect x="6" y="30" width="40" height="44" rx="6" fill="url(#v4-pod-2)"></rect>'
              '<rect x="55" y="8" width="40" height="66" rx="6" fill="url(#v4-pod-1)"></rect>'
              '<rect x="104" y="48" width="40" height="26" rx="6" fill="url(#v4-pod-3)"></rect>'
              '<path d="M6 36 h40 M55 14 h40 M104 54 h40" stroke="#F3F7FC" stroke-opacity=".35" stroke-width="2"></path>'
              '<text x="26" y="58" text-anchor="middle">30</text><text x="75" y="46" text-anchor="middle">60</text>'
              '<text x="124" y="68" text-anchor="middle">10</text></svg>')
    stack = (f'<div class="v4-coins">{coin("v4-coin c3")}{coin("v4-coin c2")}{coin("v4-coin c1")}</div>')
    return (f'<div class="at-kinds v4-kinds" role="list" aria-label="How tables work">'
            f'<div class="v4-kind" role="listitem"><span class="at-lbl">How long</span><div class="v4-durs">{clocks}</div><p>Flash tables only.</p></div>'
            f'<div class="v4-kind" role="listitem"><span class="at-lbl">The pot</span>{podium}<p>Top 3 by ROI split the buy-ins.</p></div>'
            f'<div class="v4-kind" role="listitem"><span class="at-lbl">On top</span><div class="v4-ontop">{stack}<b>+ ET10</b></div><p>Extra for the top 3.</p></div></div>')


# ------------------------------------------------------------------------------------------------ the NEXUS coach

def _edge_stripes(cx_f: float, cx_b: float, cy: float, rx: float, ry: float) -> str:
    """The poker chip's edge inserts on the side that shows: quads between the front and back rim."""
    out = []
    for k in range(-5, 6):
        a0, a1 = math.radians(k * 15 - 3.5), math.radians(k * 15 + 3.5)
        pts = [(cx_f + rx * math.cos(a0), cy + ry * math.sin(a0)), (cx_b + rx * math.cos(a0), cy + ry * math.sin(a0)),
               (cx_b + rx * math.cos(a1), cy + ry * math.sin(a1)), (cx_f + rx * math.cos(a1), cy + ry * math.sin(a1))]
        out.append('<path d="M' + " L".join(f"{x:.1f} {y:.1f}" for x, y in pts) + ' Z" fill="#E6EDF7" fill-opacity=".85"></path>')
    return "".join(out)


def coach_icon() -> str:
    """Their Agent Tournaments chip, standing, in a deerstalker, with a magnifying glass: Sherlock as a coach."""
    cx, cy, rx, ry, depth = 112.0, 152.0, 60.0, 64.0, 15.0
    inserts = "".join(
        f'<ellipse cx="{cx}" cy="{cy}" rx="{rx - 5}" ry="{ry - 5}" fill="none" stroke="{c}" stroke-width="9" pathLength="360" '
        f'stroke-dasharray="16 29" stroke-dashoffset="{off}"></ellipse>' for c, off in (("#E6EDF7", 0),))
    return f"""<svg class="v4-coach-ico" viewBox="0 0 240 240" aria-hidden="true">
 <circle cx="120" cy="134" r="108" fill="url(#v4-glow)"></circle>
 <ellipse cx="124" cy="226" rx="74" ry="9" fill="#06090f" opacity=".9" filter="url(#v4-blur)"></ellipse>
 <path d="M{cx} {cy - ry} H{cx + depth} A{rx} {ry} 0 0 1 {cx + depth} {cy + ry} H{cx} Z" fill="url(#v4-edge)"></path>
 {_edge_stripes(cx, cx + depth, cy, rx, ry)}
 <ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="url(#v4-face)"></ellipse>
 <ellipse cx="{cx}" cy="{cy}" rx="{rx - 5}" ry="{ry - 5}" fill="none" stroke="url(#v4-rim)" stroke-width="9"></ellipse>
 {inserts}
 <ellipse cx="{cx}" cy="{cy}" rx="{rx - 17}" ry="{ry - 17}" fill="none" stroke="url(#v4-rim)" stroke-width="1.8" stroke-dasharray="3 5" opacity=".85"></ellipse>
 <rect x="{cx - 20}" y="{cy - 20}" width="15" height="40" rx="7.5" fill="url(#v4-bar-c)" filter="url(#v4-glowf)"></rect>
 <rect x="{cx + 5}" y="{cy - 20}" width="15" height="40" rx="7.5" fill="url(#v4-bar-g)" filter="url(#v4-glowf)"></rect>
 <rect x="{cx - 17}" y="{cy - 16}" width="4" height="14" rx="2" fill="#F3F7FC" fill-opacity=".55"></rect>
 <rect x="{cx + 8}" y="{cy - 16}" width="4" height="14" rx="2" fill="#F3F7FC" fill-opacity=".55"></rect>
 <path d="M{cx - 48} {cy - 4} A{rx - 10} {ry - 10} 0 0 1 {cx - 6} {cy - 52}" fill="none" stroke="#F3F7FC" stroke-opacity=".28" stroke-width="5" stroke-linecap="round"></path>
 <g transform="rotate(-9 112 94)">
  <path d="M160 92 C178 91 192 96 198 106 C186 104 172 102 154 101 Z" fill="url(#v4-brim-under)"></path>
  <path d="M160 92 C178 91 192 96 198 106 C188 100 174 97 158 97 Z" fill="url(#v4-brim)"></path>
  <path d="M56 98 C56 42, 168 42, 168 98 Z" fill="url(#v4-hat)"></path>
  <path d="M56 98 C56 42, 168 42, 168 98 Z" fill="url(#v4-plaid)"></path>
  <path d="M56 98 C56 42, 168 42, 168 98 Z" fill="url(#v4-hat-shade)"></path>
  <path d="M112 50 C107 66 105 82 105 96" fill="none" stroke="#06090f" stroke-opacity=".45" stroke-width="1.6"></path>
  <path d="M80 58 C74 70 70 84 70 96" fill="none" stroke="#06090f" stroke-opacity=".35" stroke-width="1.4"></path>
  <path d="M56 98 C56 42, 168 42, 168 98" fill="none" stroke="url(#v4-rim)" stroke-width="2.2" stroke-opacity=".8"></path>
  <path d="M56 92 Q112 80 168 92 L168 100 Q112 88 56 100 Z" fill="url(#v4-band)"></path>
  <path d="M60 96 C42 96 28 102 22 113 C34 111 50 108 70 106 Z" fill="url(#v4-brim-under)"></path>
  <path d="M60 96 C42 96 28 102 22 113 C36 106 50 103 68 102 Z" fill="url(#v4-brim)"></path>
  <path d="M22 113 C36 106 50 103 68 102" fill="none" stroke="#7FE6FF" stroke-opacity=".7" stroke-width="1.6"></path>
  <path d="M112 50 C98 32 80 38 92 52 C98 56 106 54 112 50 Z" fill="url(#v4-hat)" stroke="#00cfff" stroke-opacity=".8" stroke-width="1.6"></path>
  <path d="M112 50 C126 32 144 38 132 52 C126 56 118 54 112 50 Z" fill="url(#v4-hat)" stroke="#00cfff" stroke-opacity=".8" stroke-width="1.6"></path>
  <circle cx="112" cy="50" r="5" fill="url(#v4-rim)"></circle>
  <path d="M72 78 C78 68 88 62 100 60" fill="none" stroke="#F3F7FC" stroke-opacity=".3" stroke-width="3.4" stroke-linecap="round"></path>
 </g>
 <g>
  <rect x="190" y="200" width="16" height="42" rx="8" transform="rotate(-45 198 221)" fill="url(#v4-handle)" stroke="#00ff88" stroke-opacity=".8" stroke-width="1.6"></rect>
  <rect x="190" y="198" width="16" height="7" rx="3" transform="rotate(-45 198 221)" fill="url(#v4-band)"></rect>
  <circle cx="178" cy="182" r="30" fill="url(#v4-lens)" stroke="url(#v4-metal)" stroke-width="8"></circle>
  <circle cx="178" cy="182" r="25.5" fill="none" stroke="#06090f" stroke-opacity=".5" stroke-width="1.2"></circle>
  <path d="M160 174 A19 19 0 0 1 172 162" fill="none" stroke="#F3F7FC" stroke-opacity=".85" stroke-width="3.6" stroke-linecap="round"></path>
  <circle cx="190" cy="196" r="2.6" fill="#F3F7FC" fill-opacity=".6"></circle>
 </g>
</svg>"""


# ------------------------------------------------------------------------------------------------ the risk gauge

RISK_COLOURS = ["#3b82f6", "#3b82f6", "#00cfff", "#00cfff", "#00cfff", "#00ff88", "#00ff88", "#ff4444", "#ff4444", "#ff4444"]


def gauge(value: int) -> str:
    """Ten segments from Safe to All in, lit up to the value, a needle on it."""
    cx, cy, r = 120.0, 122.0, 94.0
    segs = []
    for i in range(10):
        a0 = math.pi - i * math.pi / 10 - math.radians(1.3)
        a1 = math.pi - (i + 1) * math.pi / 10 + math.radians(1.3)
        x0, y0 = cx + r * math.cos(a0), cy - r * math.sin(a0)
        x1, y1 = cx + r * math.cos(a1), cy - r * math.sin(a1)
        segs.append(f'<path class="v4-seg{" on" if i < value else ""}" data-i="{i + 1}" d="M{x0:.1f} {y0:.1f} A{r} {r} 0 0 1 {x1:.1f} {y1:.1f}" '
                    f'stroke="{RISK_COLOURS[i]}"></path>')
    ang = 180 - (value - 0.5) * 18
    return (f'<svg class="v4-gauge" viewBox="0 0 240 136" aria-hidden="true">'
            f'<path d="M{cx - r - 14} {cy} A{r + 14} {r + 14} 0 0 1 {cx + r + 14} {cy}" fill="none" stroke="#16233a" stroke-width="1.5" stroke-dasharray="2 5"></path>'
            f'{"".join(segs)}'
            f'<g class="v4-needle" style="transform:rotate({90 - ang:.1f}deg)"><path d="M{cx} {cy - r + 13} L{cx - 7} {cy - r + 29} L{cx + 7} {cy - r + 29} Z"></path></g>'
            f'</svg>')
