"""Screenshots of the v4 copy (serve.py must be running on 8790): the pictures for the spec, taken from THEIR page
with the v4 changes on it, so they show exactly what the operator sees in the browser.

    python outbox/tournaments-v4/live/render.py            # writes outbox/tournaments-v4/pictures/*.png

Also reports what would make a picture wrong: a page wider than the screen, text that runs past its card, a seat
over the pool, two race markers that touch, and anything that still says ten seats.
"""
import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "pictures"
OUT.mkdir(exist_ok=True)
BASE = "http://127.0.0.1:8790"
HIDE = """() => { for (const e of document.querySelectorAll('body *')) { const cs = getComputedStyle(e);
  if (cs.position === 'fixed' && !e.closest('.v4-modal') && e.getBoundingClientRect().top > 300) e.style.display = 'none'; } }"""
CHECK = """() => { const out = [];
 document.querySelectorAll('.at-tcard, .at-card, .at-lr, .at-rstrip > div, .at-lane, .v4-trow').forEach(c => { const cr = c.getBoundingClientRect(); if (!cr.width) return;
  c.querySelectorAll('*').forEach(e => { if (e.closest('svg')) return; const r = e.getBoundingClientRect();
   if (e.children.length === 0 && r.width && (r.right > cr.right + 1 || r.left < cr.left - 1)) out.push('past: ' + e.textContent.trim().slice(0, 30)); }); });
 document.querySelectorAll('.at-tbl').forEach(t => { const p = t.querySelector('.at-pot'); if (!p || !t.offsetWidth) return; const pr = p.querySelector('.v').getBoundingClientRect();
  t.querySelectorAll('.at-seat .at-ava').forEach(s => { const r = s.getBoundingClientRect();
   if (r.width && r.right > pr.left && r.left < pr.right && r.bottom > pr.top && r.top < pr.bottom) out.push('seat over pot'); }); });
 const mk = [...document.querySelectorAll('circle.v4-mk')].map(c => { const r = c.getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2, r.width / 2]; });
 for (let i = 0; i < mk.length; i++) for (let j = i + 1; j < mk.length; j++) if (Math.hypot(mk[i][0] - mk[j][0], mk[i][1] - mk[j][1]) < mk[i][2] + mk[j][2]) out.push('markers touch');
 const t = document.body.innerText; const m = t.match(/\\b10 (seats|SEATS|agents\\.|AI agents)|\\b10th\\b|\\b10\\/10\\b/); if (m) out.push('still says ten: ' + m[0]);
 return out.slice(0, 12); }"""


def shot(page, name, selector=None, full=True):
    path = OUT / f"{name}.png"
    if selector:
        page.locator(selector).first.screenshot(path=str(path))
    else:
        page.screenshot(path=str(path), full_page=full)


def main():
    widths = [int(a) for a in sys.argv[1:]] or [1440]
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome", args=["--disable-lcd-text", "--font-render-hinting=none"])
        for w in widths:
            for mode in ("paper", "live"):
                ctx = b.new_context(viewport={"width": w, "height": 900})
                ctx.add_init_script(f"try{{localStorage.setItem('v4mode','{mode}')}}catch(e){{}}")
                pg = ctx.new_page()
                pg.goto(BASE + "/agent-tournaments", wait_until="networkidle")
                pg.wait_for_timeout(1500)
                pg.evaluate(HIDE)
                print(f"lobby {mode} {w}: wide={pg.evaluate('document.documentElement.scrollWidth > innerWidth')} problems={pg.evaluate(CHECK)}")
                shot(pg, f"lobby-{mode}-{w}")
                if mode == "live":
                    pg.locator("[data-v4-live]").nth(2).click()
                    pg.wait_for_timeout(500)
                    print(f"wallet {w}: problems={pg.evaluate(CHECK)}")
                    pg.screenshot(path=str(OUT / f"wallet-{w}.png"))
                ctx.close()
            ctx = b.new_context(viewport={"width": w, "height": 900})
            pg = ctx.new_page()
            pg.goto(BASE + "/agent-tournaments/table/15", wait_until="networkidle")
            pg.wait_for_timeout(1500)
            pg.evaluate(HIDE)
            print(f"table {w}: wide={pg.evaluate('document.documentElement.scrollWidth > innerWidth')} problems={pg.evaluate(CHECK)}")
            shot(pg, f"table-{w}")
            if w == 1440:
                shot(pg, "race-1440", "section.at-race")
                shot(pg, "tune-on-1440", "#atNexus")
                pg.locator("[data-v4-as=free]").click()
                pg.wait_for_timeout(200)
                shot(pg, "tune-free-1440", "#atNexus")
            ctx.close()
        b.close()
    print("rendered to", OUT)


if __name__ == "__main__":
    main()
