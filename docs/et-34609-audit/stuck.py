from playwright.sync_api import sync_playwright

TW = """(() => { const t = document.getElementById('traders'); const c = document.getElementById('copyGrid');
  return {top_wallets_rows: t.querySelectorAll('.fr-lb').length, top_wallets_text: t.innerText.slice(0, 40).split('\\n').join(' '),
          best_wallets: c.querySelectorAll('.fr-cw').length, best_text: c.innerText.slice(0, 40).split('\\n').join(' ')}; })()"""
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1440, "height": 900})
    fr = []

    def on_ws(s):
        s.on("framereceived", lambda f: fr.append((s.url[-45:], len(str(f)), '"traders"' in str(f))))

    pg.on("websocket", on_ws)
    pg.goto("https://cymetica.com/fomo-radar", wait_until="load", timeout=120000)
    pg.wait_for_timeout(9000)
    pg.click("#modeSeg button[data-mode=advanced]")
    pg.wait_for_timeout(1500)
    print("1 fresh Robinhood", pg.evaluate(TW))
    pg.click("#chainSeg button[data-chain=solana]")
    pg.wait_for_timeout(8000)
    print("2 Solana", pg.evaluate(TW))
    n = len(fr)
    pg.click("#chainSeg button[data-chain=robinhood]")
    total = 0
    for wait in (10, 20, 30, 30):
        pg.wait_for_timeout(wait * 1000)
        total += wait
        print("3 back on Robinhood +%ds" % total, pg.evaluate(TW), "| ws frames since switch", fr[n:])
    b.close()
