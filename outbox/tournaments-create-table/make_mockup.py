"""Build create.html (this folder): a "Create a table" button in the lobby's Open section and the form it opens.

The operator, 2026-10-16: "ted tady pridat nejaky button na vytvoreni stolu, at uzivatele nebo boti muzou svoje
stoly taky tvorit, treba jak budem chtit testovat 50 botu najednou". Then: "kazdy stul ma vzdy jen 10 slotu to
nepujde menit". And then: "ma se proste vytvorit klasicky stul jak tvori oni, nic navic. a jen jeden a zadne
free, nevymyslej si nic navic". So the form makes one ordinary table, the same as theirs: a kind (Week or Flash)
and a buy-in from the ones they offer; 10 seats, starts when full, 60 / 30 / 10. The right side is the lobby card
of the table being made, drawn the way the redesigned lobby draws it (outbox/tournaments-lobby-card).

Behind it, the lobby's real Open cards (lobby.json there, read 2026-10-16), dimmed. Sample: the form's values.
Palette: the site's navy, cyan, green, red and blue, plus the avatar tints they use.
"""
from __future__ import annotations

import importlib.util
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
.modal{position:absolute;left:50%;top:150px;transform:translateX(-50%);width:880px;max-width:calc(100% - 32px);
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
.times{position:absolute;top:-13px;right:18px;font-size:12px;font-weight:700;letter-spacing:.08em;color:var(--bg);background:var(--cyan);border-radius:99px;padding:4px 11px;box-shadow:0 0 14px rgba(0,207,255,.45)}
"""


def preview():
    """The table being made, as the lobby will show it: a Pro week table at $50 drawn by the lobby's own card
    (Pro #12's real figures), only its number not yet given."""
    card = lc.open_card(12)
    return card.replace('<div class="name">Pro #12</div>', '<div class="name">Pro · new</div>')


def page():
    behind = lc.open_card(17) + lc.open_card(16) + lc.open_card(12)
    form = f"""
<div class="veil"></div>
<section class="modal">
 <h3>Create a table <span class="x">✕</span></h3>
 <div class="f">
  <div class="fl"><span>KIND</span><div class="opts"><span class="on">Week<small>7 days</small></span><span>Flash<small>1 day</small></span></div></div>
  <div class="fl"><span>BUY-IN</span><div class="opts"><span>$5</span><span class="on">$50</span><span>100 ET10</span><span>1,000 ET10</span></div></div>
  <div class="sum">The same table as every other in the lobby: 10 seats, starts when full, the top 3 split the pot 60 / 30 / 10.</div>
 </div>
 <div class="side">
  <span class="k">YOUR TABLE IN THE LOBBY</span>
  {preview()}
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
