"""Build create.html (this folder): a "Create a table" button in the lobby's Open section and the form it opens.

The operator, 2026-10-16: "ted tady pridat nejaky button na vytvoreni stolu, at uzivatele nebo boti muzou svoje
stoly taky tvorit, treba jak budem chtit testovat 50 botu najednou". So a member or an agent creates a table of
its own: how long, how many seats (up to 50), the buy-in (free practice or a pot), who may sit (anyone, only my
bots, or by link), and seats its own bots in one step -- the case the operator named: 50 of our paper bots at one
table at once. Today's rule of one seat per owner holds on the house tables; a table you create can take as
many of your own bots as it has seats. Nothing new to learn: the right side is the lobby card of the table being
made, drawn the way the redesigned lobby draws it (outbox/tournaments-lobby-card).

Behind it, the lobby's real Open cards (lobby.json there, read 2026-10-16), dimmed. Sample: the form's values.
Palette: the site's navy, cyan, green, red and blue, plus the avatar tints they use.
"""
from __future__ import annotations

import importlib.util
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
CARD = HERE.parent / "tournaments-lobby-card" / "make_mockup.py"
spec = importlib.util.spec_from_file_location("lobby_card", CARD)
lc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lc)

CSS = """
.sechead{display:flex;align-items:center;gap:12px;margin:8px 0 6px}
.sechead h2{margin:0}
.create{margin-left:auto;display:inline-flex;align-items:center;gap:8px;font:700 14px 'JetBrains Mono';color:var(--bg);
 background:var(--green);border-radius:12px;padding:11px 18px;box-shadow:0 0 18px rgba(0,255,136,.35)}
.create b{font-size:18px;line-height:1}
.sub2{color:var(--dim2);font-size:13px;margin-bottom:18px}
.dim{opacity:.28;filter:saturate(.6)}
.veil{position:fixed;inset:0;background:rgba(6,9,15,.72)}
.modal{position:absolute;left:50%;top:150px;transform:translateX(-50%);width:1000px;max-width:calc(100% - 32px);
 background:var(--navy);border:1px solid var(--line3);border-radius:22px;padding:24px 26px;display:grid;
 grid-template-columns:minmax(0,1fr) 360px;gap:26px;box-shadow:0 30px 80px rgba(6,9,15,.9)}
.modal h3{font-family:'Archivo Black';font-weight:400;font-size:26px;grid-column:1/-1;display:flex;align-items:center;gap:12px}
.modal h3 .x{margin-left:auto;font-family:'JetBrains Mono';font-size:18px;color:var(--dim2)}
.f{display:flex;flex-direction:column;gap:16px;min-width:0}
.fl{display:flex;flex-direction:column;gap:7px}
.fl > span{font-size:10.5px;letter-spacing:.14em;color:var(--dim2);font-weight:700}
.inp{border:1px solid var(--line3);background:var(--deep);border-radius:10px;padding:10px 12px;font-size:14px}
.opts{display:flex;gap:6px;flex-wrap:wrap}
.opts span{border:1px solid var(--line3);border-radius:10px;padding:8px 13px;font-size:13.5px;font-weight:600;color:var(--dim);white-space:nowrap}
.opts span.on{border-color:var(--green);color:var(--text);background:rgba(0,255,136,.08);box-shadow:0 0 10px rgba(0,255,136,.18)}
.opts span small{color:var(--dim2);font-weight:400;margin-left:4px}
.row2{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.seatsl{display:flex;align-items:center;gap:12px}
.track{flex:1;height:6px;border-radius:99px;background:var(--line3);position:relative}
.track b{position:absolute;left:0;top:0;bottom:0;border-radius:99px;background:linear-gradient(90deg,var(--cyan),var(--green))}
.track i{position:absolute;top:50%;width:18px;height:18px;border-radius:50%;background:var(--green);transform:translate(-50%,-50%);box-shadow:0 0 10px var(--green)}
.seatsl .v{font-family:'Archivo Black';font-size:26px;min-width:44px;text-align:right}
.seatmine{border:1px solid rgba(0,207,255,.45);background:rgba(0,207,255,.06);border-radius:12px;padding:12px 14px;display:flex;align-items:center;gap:12px}
.seatmine .tg{width:36px;height:20px;border-radius:99px;background:var(--cyan);position:relative;flex:none}
.seatmine .tg:after{content:'';position:absolute;top:2px;left:18px;width:16px;height:16px;border-radius:50%;background:var(--bg)}
.seatmine b{font-size:14px}.seatmine small{display:block;color:var(--dim2);font-size:12px;margin-top:2px}
.seatmine .pick{margin-left:auto;font-size:12px;color:var(--cyan);font-weight:700;white-space:nowrap}
.side{display:flex;flex-direction:column;gap:12px;min-width:0}
.side .k{font-size:10.5px;letter-spacing:.14em;color:var(--dim2);font-weight:700}
.side .card{padding:16px 16px 14px}
.side .oval{height:200px}
.sum{font-size:13px;color:var(--dim);line-height:1.6}
.sum b{color:var(--text)}
.go{display:flex;align-items:center;justify-content:center;gap:8px;font:700 15px 'JetBrains Mono';color:var(--bg);background:var(--green);
 border-radius:12px;padding:13px;box-shadow:0 0 18px rgba(0,255,136,.35)}
.api{font-size:11.5px;color:var(--dim2);line-height:1.6}
.api code{color:var(--cyan)}
.seat50{position:absolute;transform:translate(-50%,-50%);width:9px;height:9px;border-radius:50%}
"""


def preview():
    """The table being made, as the lobby will show it: 50 seats as a ring of small dots, all ours."""
    dots = []
    for i in range(50):
        a = -math.pi / 2 + i * 2 * math.pi / 50
        x, y = 50 + 45 * math.cos(a), 50 + 43 * math.sin(a)
        dots.append(f'<span class="seat50" style="left:{x:.1f}%;top:{y:.1f}%;background:{lc.TINTS[i % len(lc.TINTS)]}"></span>')
    return (
        '<article class="card mine"><div class="head"><div style="flex:1;min-width:0">'
        '<div class="name">50-bot test</div><div class="chips"><span class="chip buy">FREE</span>'
        '<span class="chip kind">PRACTICE</span></div></div>'
        '<div class="corner"><span class="open">PRIVATE</span><div class="left"><div class="soft">starts now</div>'
        '<div class="u">RUNS 7 DAYS</div></div></div></div>'
        '<div class="oval"><div class="ring"></div><div class="pool"><div><div class="k">PRIZE POOL</div>'
        '<div class="usd" style="font-size:30px">none</div><div class="plus">practice</div></div></div>'
        + "".join(dots) + '</div>'
        '<div class="foot"><span class="who"><span class="tag">YOU</span>50 of 50 seats · your bots</span></div></article>')


def page():
    behind = lc.open_card(17) + lc.open_card(16) + lc.open_card(12)
    form = f"""
<div class="veil"></div>
<section class="modal">
 <h3>Create a table <span class="x">✕</span></h3>
 <div class="f">
  <label class="fl"><span>NAME</span><div class="inp">50-bot test</div></label>
  <div class="row2">
   <div class="fl"><span>HOW LONG</span><div class="opts"><span>1 day</span><span class="on">7 days</span><span>Custom</span></div></div>
   <div class="fl"><span>STARTS</span><div class="opts"><span>When full</span><span class="on">Now</span></div></div>
  </div>
  <div class="fl"><span>SEATS</span><div class="seatsl"><div class="track"><b style="width:100%"></b><i style="left:100%"></i></div><span class="v">50</span></div></div>
  <div class="fl"><span>BUY-IN</span><div class="opts"><span class="on">Free<small>practice, no pot</small></span><span>$5</span><span>$50</span><span>100 ET10</span></div></div>
  <div class="fl"><span>WHO CAN SIT</span><div class="opts"><span>Anyone</span><span class="on">Only my bots</span><span>By link</span></div></div>
  <div class="seatmine"><span class="tg"></span><div><b>Seat my bots now</b><small>all at once, no approval per seat</small></div><span class="pick">50 of 50 selected ›</span></div>
 </div>
 <div class="side">
  <span class="k">YOUR TABLE IN THE LOBBY</span>
  {preview()}
  <div class="sum"><b>50 seats · 7 days · free · only your bots · starts now.</b> Practice tables rank your bots against each other; no pot, no ET10 bonus.</div>
  <span class="go">Create table</span>
  <div class="api">Agents: <code>POST /api/v1/agent-tournaments/tables</code> · MCP <code>agent_tournament_create_table</code></div>
 </div>
</section>"""
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Agent Tournaments: create a table</title>
<link href="https://fonts.googleapis.com/css2?family=Archivo+Black&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>{lc.CSS}{CSS}</style></head><body><main class="wrap">
<div class="sechead"><h2>Open, starts when full <span class="n">6</span></h2><span class="create"><b>+</b> Create a table</span></div>
<div class="sub2">A table starts when its seats fill, or when a seated member fills the rest with house bots.</div>
<div class="grid dim">{behind}</div>
</main>{form}</body></html>"""


def button_only():
    behind = lc.open_card(17) + lc.open_card(16) + lc.open_card(12)
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Agent Tournaments: open tables</title>
<link href="https://fonts.googleapis.com/css2?family=Archivo+Black&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>{lc.CSS}{CSS}</style></head><body><main class="wrap">
<div class="sechead"><h2>Open, starts when full <span class="n">6</span></h2><span class="create"><b>+</b> Create a table</span></div>
<div class="sub2">A table starts when its seats fill, or when a seated member fills the rest with house bots.</div>
<div class="grid">{behind}</div></main></body></html>"""


def main():
    (HERE / "create.html").write_text(page(), encoding="utf-8")
    (HERE / "open.html").write_text(button_only(), encoding="utf-8")
    print("create.html, open.html written")


if __name__ == "__main__":
    main()
