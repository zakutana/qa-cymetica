"""Pictures of the Quest guide as the operator will see it: the middle of every chapter at his width (2000 x 1100) and
on a phone (390 x 844), into shots/ (not kept in git). Also a CPU-throttled scroll from top to bottom, timed, so a stall
on a weak laptop shows up as a number before anybody scrolls it.

    python outbox/quest/shots.py              # the pictures
    python outbox/quest/shots.py --scroll     # and the throttled scroll
"""
import functools
import http.server
import json
import socket
import sys
import threading
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
OUT = HERE / 'shots'
SIZES = {'wide': {'width': 2000, 'height': 1100}, 'phone': {'width': 390, 'height': 844}}


def serve():
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        port = s.getsockname()[1]

    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass
    server = http.server.ThreadingHTTPServer(('127.0.0.1', port), functools.partial(Quiet, directory=str(HERE)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return f'http://127.0.0.1:{port}/index.html'


def settle(page, seconds=0.0):
    page.evaluate("() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))")
    if seconds:
        time.sleep(seconds)


def pictures(browser, url):
    OUT.mkdir(exist_ok=True)
    for name, vp in SIZES.items():
        page = browser.new_page(viewport=vp)
        page.goto(url, wait_until='networkidle')
        page.wait_for_function("() => window.QUEST_STATE && QUEST_STATE.ready && document.fonts.status === 'loaded'")
        ids = page.evaluate("() => [...document.querySelectorAll('section[data-step]')].map(s => s.id)")
        for i, cid in enumerate(ids):
            page.evaluate("""(id) => { const s = document.getElementById(id), r = s.getBoundingClientRect();
              window.scrollTo({ top: window.scrollY + r.top + r.height * 0.5 - innerHeight / 2, behavior: 'instant' }); }""", cid)
            settle(page, 1.2)
            path = OUT / f'{name}-{i}-{cid}.png'
            page.screenshot(path=str(path))
            print(path.name)
        page.close()


def scroll(browser, url):
    """Top to bottom in 12 s with the CPU slowed 4x (a weak laptop): the longest gap between two painted frames."""
    page = browser.new_page(viewport=SIZES['wide'])
    cdp = page.context.new_cdp_session(page)
    page.goto(url, wait_until='networkidle')
    page.wait_for_function("() => window.QUEST_STATE && QUEST_STATE.ready")
    time.sleep(3)
    cdp.send('Emulation.setCPUThrottlingRate', {'rate': 4})
    run = """() => new Promise(done => {
      const H = document.documentElement.scrollHeight - innerHeight, T = 12000, t0 = performance.now(), gaps = [];
      let last = t0;
      function step(now) {
        const k = Math.min(1, (now - t0) / T); gaps.push(now - last); last = now; (window.__slow = window.__slow || []).push([k, gaps[gaps.length - 1], window.QUEST_STATE.shot]);
        window.scrollTo(0, H * k);
        if (k < 1) requestAnimationFrame(step); else done({ frames: gaps.length, worst: Math.max(...gaps.slice(2)),
          over50: gaps.filter(g => g > 50).length, mean: gaps.reduce((a, b) => a + b, 0) / gaps.length,
          ...Object.fromEntries(window.__slow.filter(s => s[1] > 50).map(s => [s[2] + '@' + s[0].toFixed(2), Math.round(s[1])]).slice(0, 40)) });
      }
      requestAnimationFrame(step);
    })"""
    # two passes: the first is the first visit (frames still arriving), the second is the page as it feels once loaded
    for label in ('first pass ', 'second pass'):
        result = page.evaluate(run)
        print(f'throttled 4x scroll, {label}:', json.dumps({k: round(v, 1) for k, v in result.items()}))
        page.evaluate("() => window.scrollTo(0, 0)")
        time.sleep(2)
    page.close()


if __name__ == '__main__':
    url = serve()
    with sync_playwright() as p:
        b = p.chromium.launch(channel='chrome', args=['--enable-unsafe-webgpu', '--use-angle=d3d11', '--ignore-gpu-blocklist'])
        pictures(b, url)
        if '--scroll' in sys.argv:
            scroll(b, url)
        b.close()
