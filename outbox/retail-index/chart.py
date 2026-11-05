"""Draw retail index v5 the way Cymetica draws their retail tile, and beside theirs.

    python -I outbox/retail-index/chart.py

Reads `data/weekly.csv`, writes `chart-v5.png` (ours), `chart-cymetica-v4.png` (their retail tile redrawn from their own
series), `chart-compare.png` (ours, their v4 and v3 together, the dated tops and lows marked) and `cache/charts.html`.
Their look: a line with a soft area under it on 0 to 100, the market of the small coins in dollars (log) behind it in
blue on the right axis, a pill with today's value. English, Cymetica's colours, numbers first. Playwright, as every
picture in this repo.
"""
from __future__ import annotations

import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent))

from qa import retailindex as R  # noqa: E402
from qa.paths import atomic_write  # noqa: E402

DATA = HERE / "data"
P = {"bg": "#0a0e17", "panel": "#0f1626", "line": "#1d2a44", "grid": "#16213a", "mute": "#6e7f9f", "text": "#e6edf7",
     "cyan": "#00cfff", "green": "#00ff88", "red": "#ff4444", "blue": "#3b82f6"}
W_, H_ = 1200, 566
ML, MR, MT, MB = 58, 86, 138, 46
PW, PH = W_ - ML - MR, H_ - MT - MB


class Frame:
    def __init__(self, weeks):
        self.x0, self.x1 = R.ordinal("2016-12-26"), weeks[-1] + 35
        self.weeks = weeks

    def x(self, o):
        return ML + (o - self.x0) / (self.x1 - self.x0) * PW

    @staticmethod
    def y(v):
        return MT + PH - v / 100 * PH


def path(frame, weeks, vals, yfn=None, gap_ok=False):
    """SVG path through the points that exist; a missing week breaks the line."""
    yfn = yfn or frame.y
    d, pen = [], False
    for w, v in zip(weeks, vals):
        if v is None or w < frame.x0:
            pen = False
            continue
        d.append(f"{'L' if pen else 'M'}{frame.x(w):.1f},{yfn(v):.1f}")
        pen = True
    return " ".join(d)


def area(frame, weeks, vals):
    pts = [(frame.x(w), frame.y(v)) for w, v in zip(weeks, vals) if v is not None and w >= frame.x0]
    if not pts:
        return ""
    return "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts) + f" L{pts[-1][0]:.1f},{frame.y(0):.1f} L{pts[0][0]:.1f},{frame.y(0):.1f} Z"


def others_axis(weeks, others):
    vis = [v for w, v in zip(weeks, others) if v is not None and w >= R.ordinal("2016-12-26")]
    lo, hi = min(vis), max(vis)
    ll, lh = math.log10(lo), math.log10(hi)

    def yfn(v):
        return MT + PH - (math.log10(v) - ll) / (lh - ll) * PH

    return yfn, [(lo, 0), (math.sqrt(lo * hi), 50), (hi, 100)]


def money(v):
    return f"${v / 1e9:.1f}bn" if v < 1e11 else f"${v / 1e9:.0f}bn"


def svg(cid, title, big, sub, series, weeks, others, thin=None, marks=True, legend=(), peaks=()):
    fr = Frame(weeks)
    yo, ticks = others_axis(weeks, others)
    out = [f'<svg id="{cid}" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W_} {H_}" width="{W_}" height="{H_}">',
           f'<defs>' + "".join(
               f'<linearGradient id="{cid}-g{i}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{c}" stop-opacity=".32"/>'
               f'<stop offset="1" stop-color="{c}" stop-opacity="0"/></linearGradient>' for i, c in enumerate((P["cyan"], P["red"], P["green"])))
           + '</defs>',
           f'<rect x="0.5" y="0.5" width="{W_ - 1}" height="{H_ - 1}" rx="12" fill="{P["panel"]}" stroke="{P["line"]}"/>']
    # header: title, then the number first
    out.append(f'<text x="{ML}" y="26" class="k">{title}</text>')
    out.append(f'<text x="{ML}" y="66" class="big">{big}</text>')
    out.append(f'<text x="{ML}" y="90" class="sub">{sub}</text>')
    lx = ML   # the legend has its own row under the header, so it never meets the title
    for label, color, dash in legend:
        out.append(f'<line x1="{lx}" x2="{lx + 22}" y1="108" y2="108" stroke="{color}" stroke-width="3" {"stroke-dasharray=\"5 4\"" if dash else ""}/>')
        out.append(f'<text x="{lx + 28}" y="112" class="leg">{label}</text>')
        lx += 8 * len(label) + 52
    # grid and axes
    for v in range(0, 101, 20):
        out.append(f'<line x1="{ML}" x2="{ML + PW}" y1="{fr.y(v):.1f}" y2="{fr.y(v):.1f}" stroke="{P["grid"]}"/>')
        out.append(f'<text x="{ML - 8}" y="{fr.y(v) + 4:.1f}" class="ax" text-anchor="end">{v}</text>')
    for o, frac in ticks:
        out.append(f'<text x="{ML + PW + 8}" y="{fr.y(frac) + 4:.1f}" class="axb">{money(o)}</text>')
    for yr in range(2017, 2027):
        o = R.ordinal(f"{yr}-01-01")
        out.append(f'<line x1="{fr.x(o):.1f}" x2="{fr.x(o):.1f}" y1="{MT}" y2="{MT + PH}" stroke="{P["grid"]}" stroke-dasharray="2 5"/>')
        out.append(f'<text x="{fr.x(o):.1f}" y="{MT + PH + 20}" class="ax" text-anchor="middle">{yr}</text>')
    # zones
    for v, color, label in ((R.ASLEEP, P["green"], "asleep under 25"), (R.SATURATED, P["red"], "saturated 75 and over")):
        out.append(f'<line x1="{ML}" x2="{ML + PW}" y1="{fr.y(v):.1f}" y2="{fr.y(v):.1f}" stroke="{color}" stroke-opacity=".45" stroke-dasharray="6 5"/>')
        out.append(f'<text x="{ML + PW - 6}" y="{fr.y(v) - 5:.1f}" class="zone" fill="{color}" text-anchor="end">{label}</text>')
    # the dated tops and lows
    if marks:
        for n, d in enumerate(R.TOP_DATES):
            x = fr.x(R.ordinal(d))
            out.append(f'<line x1="{x:.1f}" x2="{x:.1f}" y1="{MT}" y2="{MT + PH}" stroke="{P["red"]}" stroke-opacity=".5" stroke-dasharray="1 4"/>')
            out.append(f'<text x="{x:.1f}" y="{MT - 6 - 13 * (n % 2)}" class="ev" fill="{P["red"]}" text-anchor="middle">top {d[:7]}</text>')
        for n, d in enumerate(R.LOW_DATES):
            x = fr.x(R.ordinal(d))
            out.append(f'<line x1="{x:.1f}" x2="{x:.1f}" y1="{MT}" y2="{MT + PH}" stroke="{P["green"]}" stroke-opacity=".5" stroke-dasharray="1 4"/>')
            out.append(f'<text x="{x:.1f}" y="{MT + PH - 6 - 13 * (n % 2)}" class="ev" fill="{P["green"]}" text-anchor="middle">low {d[:7]}</text>')
    # the small coins in dollars, behind
    out.append(f'<path d="{path(fr, weeks, others, yo)}" fill="none" stroke="{P["blue"]}" stroke-width="1.5" stroke-opacity=".85"/>')
    # the lines
    for i, spec in enumerate(series):
        label, vals, color, dash, fill = spec[:5]
        width = spec[5] if len(spec) > 5 else (2.4 if fill else 1.6)
        opacity = spec[6] if len(spec) > 6 else 1
        if fill:
            out.append(f'<path d="{area(fr, weeks, vals)}" fill="url(#{cid}-g{ {P["cyan"]: 0, P["red"]: 1, P["green"]: 2}[color] })"/>')
        if thin is not None and dash == "thin":
            solid = [v if (v is not None and thin[j] >= 3) else None for j, v in enumerate(vals)]
            two = [v if (v is not None and thin[j] <= 2) else None for j, v in enumerate(vals)]
            # keep the join between the dashed and the solid part
            for j in range(1, len(vals)):
                if two[j - 1] is not None and solid[j] is not None:
                    two[j] = vals[j]
            out.append(f'<path d="{path(fr, weeks, two)}" fill="none" stroke="{color}" stroke-width="{width}" stroke-dasharray="5 4"/>')
            out.append(f'<path d="{path(fr, weeks, solid)}" fill="none" stroke="{color}" stroke-width="{width}"/>')
        else:
            out.append(f'<path d="{path(fr, weeks, vals)}" fill="none" stroke="{color}" stroke-width="{width}" stroke-opacity="{opacity}" stroke-linejoin="round"/>')
        last = next((j for j in range(len(vals) - 1, -1, -1) if vals[j] is not None), None)
        if last is not None and fill:
            x, y = fr.x(weeks[last]), fr.y(vals[last])
            out.append(f'<rect x="{x + 6:.1f}" y="{y - 11:.1f}" width="34" height="22" rx="6" fill="{P["bg"]}" stroke="{color}"/>')
            out.append(f'<text x="{x + 23:.1f}" y="{y + 4:.1f}" class="pill" fill="{color}" text-anchor="middle">{vals[last]:.0f}</text>')
    for w, v in peaks:   # the peak signal: "the top is behind us", drawn on the 4-week mean it reads
        x, y = fr.x(w), fr.y(v)
        out.append(f'<path d="M{x - 6:.1f},{y - 15:.1f} L{x + 6:.1f},{y - 15:.1f} L{x:.1f},{y - 4:.1f} Z" fill="{P["red"]}"/>')
        out.append(f'<text x="{x:.1f}" y="{y - 20:.1f}" class="ev" fill="{P["red"]}" text-anchor="middle">peak signal {R.iso(w)[:7]}</text>')
    out.append("</svg>")
    return "\n".join(out)


STYLE = f"""
body {{ margin: 0; background: {P['bg']}; padding: 20px; }}
.c {{ margin: 0 0 24px 0; width: {W_}px; }}
svg text {{ font-family: "IBM Plex Sans", "Segoe UI", system-ui, sans-serif; fill: {P['text']}; }}
.k {{ font-size: 12px; letter-spacing: .12em; fill: {P['mute']}; }}
.big {{ font-size: 34px; font-weight: 700; font-family: "IBM Plex Mono", Consolas, monospace; }}
.sub {{ font-size: 15px; fill: {P['mute']}; }}
.ax {{ font-size: 11px; fill: {P['mute']}; font-family: "IBM Plex Mono", Consolas, monospace; }}
.axb {{ font-size: 11px; fill: {P['blue']}; font-family: "IBM Plex Mono", Consolas, monospace; }}
.zone {{ font-size: 10.5px; letter-spacing: .04em; }}
.ev {{ font-size: 10px; letter-spacing: .04em; }}
.leg {{ font-size: 12px; }}
.pill {{ font-size: 13px; font-weight: 700; font-family: "IBM Plex Mono", Consolas, monospace; }}
"""


def render(html, shots):
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel="chrome", args=["--disable-lcd-text", "--font-render-hinting=none"])
        page = browser.new_page(viewport={"width": 1440, "height": 900}, device_scale_factor=1)
        page.set_content(html)
        page.wait_for_timeout(300)
        for cid, name in shots:
            page.locator(f"#{cid}").screenshot(path=str(HERE / name))
        browser.close()


def palette_scan(html):
    found = {h.lower() for h in re.findall(r"#[0-9a-fA-F]{6}\b", html)}
    off = found - set(P.values())
    if off:
        sys.exit(f"off-palette colours in the chart, nothing drawn: {sorted(off)}")


def main_v6():
    """Charts of the social index v6: ours, ours beside their v3 and v4 with the peak signals, and its three families."""
    table = R.merge_social(R.read_table((DATA / "weekly.csv").read_text(encoding="utf-8")),
                           (DATA / "social_weekly.csv").read_text(encoding="utf-8"))
    res = R.compute_index(table, families=R.SOCIAL_FAMILIES)
    weeks, idx, nf = table["week"], res["index"], res["nfam"]
    v4, v3, others = table["cy_v4"], table["cy_v3"], table["cy_others"]
    now = idx[-1]
    ma4 = R.moving_mean(idx)
    peaks = [(weeks[i], ma4[i]) for i in R.peak_signals(idx)]
    blue_leg = ("small coins in $ (log)", P["blue"], False)
    raw = ("v6 weekly", idx, P["cyan"], None, False, 1.1, 0.5)
    fam = res["families"]
    charts = [
        svg("v6", "RETAIL HEAT v6 · SOCIAL ATTENTION ONLY: WIKIPEDIA, REDDIT", f"{now:.0f}",
            f"{R.zone(now)} · week of {R.iso(weeks[-1])} · {nf[-1]} families · 4-week mean {ma4[-1]:.0f}",
            [raw, ("v6 4-week mean", ma4, P["cyan"], "thin", True, 2.4)], weeks, others, thin=nf, marks=True,
            legend=[("v6 weekly (thin) and 4-week mean (dashed: 2 families)", P["cyan"], False), blue_leg], peaks=peaks),
        svg("cmp6", "COMPARE · v6 AGAINST CYMETICA'S TWO RETAIL MEASURES", f"{now:.0f} vs {v4[-1]:.0f} vs {v3[-1]:.0f}",
            f"v6 weekly · v4 · v3, now; v6 4-week mean {ma4[-1]:.0f}",
            [("v3", v3, P["green"], None, False), ("v4", v4, P["red"], None, False), raw, ("v6 4-week mean", ma4, P["cyan"], None, True, 2.4)],
            weeks, others, marks=True, peaks=peaks,
            legend=[("v6 (ours; thin weekly, thick 4-week mean)", P["cyan"], False), ("Cymetica v4", P["red"], False), ("Cymetica v3", P["green"], False), blue_leg]),
        svg("fam6", "THE THREE FAMILIES BEHIND v6", f"{fam['attention'][-1]:.0f} · {fam['crowd'][-1]:.0f} · {fam['degen'][-1]:.0f}",
            f"attention (Wikipedia) · crowd (r/CryptoCurrency, r/Bitcoin, r/ethtrader) · degen (r/CryptoMoonShots, r/SatoshiStreetBets, r/altcoin), now",
            [("attention", fam["attention"], P["cyan"], None, False), ("crowd", fam["crowd"], P["green"], None, False),
             ("degen", fam["degen"], P["text"], None, False)], weeks, others, marks=True,
            legend=[("attention", P["cyan"], False), ("crowd", P["green"], False), ("degen", P["text"], False), blue_leg]),
    ]
    html = f'<!doctype html><meta charset="utf-8"><title>retail index v6</title><style>{STYLE}</style><body>' + "".join(
        f'<div class="c">{c}</div>' for c in charts) + "</body>"
    palette_scan(html)
    atomic_write(HERE / "cache" / "charts6.html", html)
    render(html, (("v6", "chart-v6.png"), ("cmp6", "chart-compare-v6.png"), ("fam6", "chart-families-v6.png")))
    print("drew chart-v6.png, chart-compare-v6.png, chart-families-v6.png")
    return 0


def main():
    if "--v6" in sys.argv[1:]:
        return main_v6()
    table = R.read_table((DATA / "weekly.csv").read_text(encoding="utf-8"))
    res = R.compute_index(table)
    weeks, idx, nf = table["week"], res["index"], res["nfam"]
    v4, v3, others = table["cy_v4"], table["cy_v3"], table["cy_others"]
    ours_now = idx[-1]
    ma4 = R.moving_mean(idx)
    blue_leg = ("small coins in $ (log)", P["blue"], False)
    raw_v5 = ("v5 weekly", idx, P["cyan"], None, False, 1.1, 0.5)
    charts = [
        svg("v5", "RETAIL HEAT v5 · PEOPLE AND LEVERAGE, NOT DOLLARS", f"{ours_now:.0f}",
            f"{R.zone(ours_now)} · week of {R.iso(weeks[-1])} · {nf[-1]} families · 4-week mean {ma4[-1]:.0f}",
            [raw_v5, ("v5 4-week mean", ma4, P["cyan"], "thin", True, 2.4)], weeks, others, thin=nf,
            marks=True, legend=[("v5 weekly (thin) and 4-week mean (dashed: 2 families)", P["cyan"], False), blue_leg]),
        svg("v4", "CYMETICA RETAIL (v4, TURNOVER / MARKET CAP) · REDRAWN FROM THEIR SERIES", f"{v4[-1]:.0f}",
            f"asleep · week of {R.iso(weeks[-1])} · failed its own back-test", [("v4", v4, P["cyan"], None, True)], weeks, others,
            marks=True, legend=[("Cymetica v4", P["cyan"], False), blue_leg]),
        svg("cmp", "COMPARE · v5 AGAINST CYMETICA'S TWO RETAIL MEASURES", f"{ours_now:.0f} vs {v4[-1]:.0f} vs {v3[-1]:.0f}",
            f"v5 weekly · v4 · v3, now; v5 4-week mean {ma4[-1]:.0f}",
            [("v3", v3, P["green"], None, False), ("v4", v4, P["red"], None, False), raw_v5, ("v5 4-week mean", ma4, P["cyan"], None, True, 2.4)],
            weeks, others, marks=True,
            legend=[("v5 (ours; thin weekly, thick 4-week mean)", P["cyan"], False), ("Cymetica v4", P["red"], False), ("Cymetica v3", P["green"], False), blue_leg]),
    ]
    html = f'<!doctype html><meta charset="utf-8"><title>retail index v5</title><style>{STYLE}</style><body>' + "".join(
        f'<div class="c">{c}</div>' for c in charts) + "</body>"
    allowed = set(P.values())
    found = {h.lower() for h in re.findall(r"#[0-9a-fA-F]{6}\b", html)}
    off = found - allowed
    if off:
        sys.exit(f"off-palette colours in the chart, nothing drawn: {sorted(off)}")
    atomic_write(HERE / "cache" / "charts.html", html)

    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel="chrome", args=["--disable-lcd-text", "--font-render-hinting=none"])
        page = browser.new_page(viewport={"width": 1440, "height": 900}, device_scale_factor=1)
        page.set_content(html)
        page.wait_for_timeout(300)
        for cid, name in (("v5", "chart-v5.png"), ("v4", "chart-cymetica-v4.png"), ("cmp", "chart-compare.png")):
            page.locator(f"#{cid}").screenshot(path=str(HERE / name))
        browser.close()
    print("drew chart-v5.png, chart-cymetica-v4.png, chart-compare.png")
    return 0


if __name__ == "__main__":
    sys.exit(main())
