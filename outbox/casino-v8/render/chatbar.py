"""Copy their chat bar once, anonymously, GET only, into ../chatbar.html: their script draws it, and their scripts stay stripped from the mock.

    python outbox/casino-v8/render/chatbar.py
"""
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parent.parent / "chatbar.html"

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1920, "height": 1080})
    page.route("**/*", lambda r: r.abort() if r.request.method != "GET" else r.continue_())
    page.goto("https://cymetica.com/agent-casino", wait_until="domcontentloaded", timeout=60000)
    page.wait_for_selector("#nexus-chat-widget .nexus-bar", timeout=30000)
    page.wait_for_timeout(1500)
    html = page.evaluate("""() => { const w = document.querySelector('#nexus-chat-widget'), c = w.cloneNode(false), b = w.querySelector('.nexus-bar').cloneNode(true);
      c.appendChild(b); c.removeAttribute('data-state'); return c.outerHTML; }""")
    links = page.evaluate("""() => [...document.querySelectorAll('link[rel=stylesheet]')].map(l => l.href).filter(h => /nexus/.test(h))""")
    browser.close()
OUT.write_text("".join(f'<link rel="stylesheet" href="{h}">' for h in links) + html.replace('src="/', 'src="https://cymetica.com/').replace('href="/', 'href="https://cymetica.com/'), encoding="utf8")
print(len(html), links)
