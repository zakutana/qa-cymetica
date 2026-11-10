"""Read-only look at the shipped /fomo-radar: screenshots, DOM of the cards, and the API/WS data the page itself received."""
import json
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT = Path(__file__).parent
URL = "https://cymetica.com/fomo-radar"
JS_CARDS = """() => ({
  h1: (() => { const h = document.querySelector('.fr-hl h1'); const r = document.createRange(); r.selectNodeContents(h); return {lines: [...new Set([...r.getClientRects()].map(x => Math.round(x.top)))].length, size: getComputedStyle(h).fontSize, text: h.innerText}; })(),
  mode: document.getElementById('fr').className,
  scrollW: document.documentElement.scrollWidth, clientW: document.documentElement.clientWidth,
  upd: (document.getElementById('upd') || {}).textContent,
  pill: (document.getElementById('heroPill') || {}).textContent,
  mkt: (document.getElementById('basicMkt') || {}).innerText,
  cards: [...document.querySelectorAll('#picksGrid .fr-pick')].map(c => ({
    key: c.dataset.key, name: (c.querySelector('.pk-name b') || {}).textContent, sub: (c.querySelector('.pk-name small') || {}).textContent,
    badges: [...c.querySelectorAll('.pk-top .tag')].map(t => t.textContent),
    p: (c.querySelector('.pk-p b') || {}).textContent, plabel: (c.querySelector('.pk-p span') || {}).textContent,
    stats: [...c.querySelectorAll('.pk-stats > div')].map(d => d.innerText.replace(/\\n/g, ' ')),
    who: [...c.querySelectorAll('.pk-w')].map(w => ({t: w.innerText.replace(/\\n/g, ' | '), href: (w.querySelector('a') || {}).href, sold: w.classList.contains('sold')})),
    more: (c.querySelector('.pk-more') || {}).textContent, warn: (c.querySelector('.fr-warn') || {}).textContent,
    go: (c.querySelector('.pk-go') || {}).href, gotext: (c.querySelector('.pk-go') || {}).textContent, w: Math.round(c.getBoundingClientRect().width),
  })),
  exits: [...document.querySelectorAll('#exits a')].map(a => [a.textContent, a.href]),
  exitsLabel: (document.querySelector('#exits .ex-lb') || {}).textContent,
  promo: (() => { const p = document.getElementById('lpPromo'); return p ? {hidden: p.hidden, text: p.innerText, links: [...p.querySelectorAll('a')].map(a => [a.textContent, a.href])} : null; })(),
  copy: [...document.querySelectorAll('#copyGrid .fr-cw')].map(c => c.innerText.replace(/\\n/g, ' | ')),
  copyWin: (document.getElementById('copyWin') || {}).textContent, copyNote: (document.getElementById('copyNote') || {}).textContent,
  empties: [...document.querySelectorAll('.fr-empty')].map(e => [e.parentElement.id, e.textContent]),
})"""


def run(w, h, mobile, tag):
    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(viewport={"width": w, "height": h}, device_scale_factor=1, is_mobile=mobile, has_touch=mobile)
        pg = ctx.new_page()
        got, ws, errs = {}, [], []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.on("console", lambda m: errs.append("console: " + m.text) if m.type == "error" else None)

        def on_resp(r):
            if "/api/v1/clones/fomo-radar/" in r.url:
                try:
                    got[r.url.split("fomo-radar/")[1]] = {"status": r.status, "body": r.json() if r.status == 200 else r.text()[:300]}
                except Exception as e:  # noqa: BLE001
                    got[r.url.split("fomo-radar/")[1]] = {"status": r.status, "err": str(e)}

        def on_ws(s):
            s.on("framereceived", lambda f: ws.append({"url": s.url, "data": f if isinstance(f, str) else getattr(f, "payload", str(f))}))

        pg.on("response", on_resp)
        pg.on("websocket", on_ws)
        pg.goto(URL, wait_until="load", timeout=120000)
        try:
            pg.wait_for_function("document.querySelectorAll('#picksGrid .fr-pick').length > 0 || document.querySelector('#picksGrid .fr-empty')", timeout=60000)
        except Exception as e:  # noqa: BLE001
            errs.append("wait: " + str(e)[:200])
        pg.wait_for_timeout(8000)
        out = {"basic_rh": pg.evaluate(JS_CARDS)}
        pg.evaluate("window.scrollTo(0,0)")
        pg.screenshot(path=str(OUT / f"{tag}-basic-rh.png"), full_page=True)
        # Solana
        pg.click("#chainSeg button[data-chain=solana]")
        pg.wait_for_timeout(9000)
        out["basic_sol"] = pg.evaluate(JS_CARDS)
        pg.screenshot(path=str(OUT / f"{tag}-basic-sol.png"), full_page=True)
        # Advanced (Solana), then back to Robinhood
        pg.click("#modeSeg button[data-mode=advanced]")
        pg.wait_for_timeout(3000)
        pg.screenshot(path=str(OUT / f"{tag}-adv-sol.png"), full_page=True)
        out["adv_sol_text"] = pg.evaluate("document.getElementById('fr').innerText")
        pg.click("#chainSeg button[data-chain=robinhood]")
        pg.wait_for_timeout(9000)
        pg.screenshot(path=str(OUT / f"{tag}-adv-rh.png"), full_page=True)
        out["adv_rh_text"] = pg.evaluate("document.getElementById('fr').innerText")
        out["adv_scroll"] = pg.evaluate("[document.documentElement.scrollWidth, document.documentElement.clientWidth]")
        pg.reload(wait_until="load")
        pg.wait_for_timeout(6000)
        out["after_reload_mode"] = pg.evaluate("document.getElementById('fr').className")
        out["after_reload_chain"] = pg.evaluate("(document.querySelector('#chainSeg button.on')||{}).textContent")
        out["errors"] = errs[:30]
        (OUT / f"{tag}-dom.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
        (OUT / f"{tag}-api.json").write_text(json.dumps(got, ensure_ascii=False), encoding="utf-8")
        (OUT / f"{tag}-ws.json").write_text(json.dumps(ws, ensure_ascii=False), encoding="utf-8")
        print(tag, "api:", {k: v["status"] for k, v in got.items()}, "ws frames:", len(ws), "errors:", errs[:8])
        b.close()


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "both"
    if which in ("d", "both"):
        run(1440, 900, False, "d")
    if which in ("m", "both"):
        run(390, 844, True, "m")
