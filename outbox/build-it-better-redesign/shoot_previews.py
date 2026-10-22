"""Picture the rebuilt apps for the mockup's previews: previews/<slug>.jpg, 640 x 360, the top of each live page.

The operator, 2026-10-22, of the catalog and the board: "at daji nejake obrazky preview tech appek". Cymetica has no
picture of an app today: /og/app/<slug>.png is a generated card with the app's name on it (it renders for any slug,
even one that does not exist). So the mockup shows what real previews would look like, and the request asks them for one.

Which apps: the 24 most viewed and the 24 most visited in the last 30 days (GET /apps/leaderboard), and every shipped
build on the board (GET /requests) whose page is on cymetica.com. Everything else falls back to the /og/app card.

Nothing is written on their side: every request that is not a GET is aborted, and that includes the page's own visit
beacon (POST /api/v1/build-it-better/apps/visit), so our pictures do not count as views in the numbers the catalog
ranks by. The GETs a page makes on load were listed first (all reads).
"""
import json
import re
import sys
import urllib.request
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse

from PIL import Image
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
OUT = HERE / "previews"
OUT.mkdir(exist_ok=True)
TOP = 24


def get(path):
    req = urllib.request.Request("https://cymetica.com" + path, headers={"User-Agent": "Mozilla/5.0 (mockup preview)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def slug(path):
    return path.strip("/").replace("/", "__") or "home"


paths = []
for sort in ("views", "visitors"):
    paths += [a["path"] for a in get(f"/api/v1/build-it-better/apps/leaderboard?sort={sort}")["apps"][:TOP]]
for b in get("/api/v1/build-it-better/requests")["items"]:
    u = urlparse(b.get("our_url") or "")
    if b.get("stage") == "shipped" and u.path and u.netloc in ("", "cymetica.com", "www.cymetica.com"):
        paths.append(u.path)
paths = [p for p in dict.fromkeys(paths) if re.fullmatch(r"/[\w./-]*", p)]
only = set(sys.argv[1:])
if only:
    paths = [p for p in paths if p in only]
print(f"{len(paths)} pages")

HIDE = """() => { document.querySelectorAll('body *').forEach(e => { const s = getComputedStyle(e);
  if (s.position === 'fixed' || s.position === 'sticky') e.style.setProperty('display', 'none', 'important'); });
  ['agentPasteBar', 'globalSimBanner', 'contentBackBtn'].forEach(id => { const e = document.getElementById(id); if (e) e.style.setProperty('display', 'none', 'important'); });
  document.body.style.setProperty('padding-top', '0', 'important'); window.scrollTo(0, 0); }"""
done = {}
with sync_playwright() as p:
    br = p.chromium.launch(channel="chrome")
    ctx = br.new_context(viewport={"width": 1280, "height": 900}, device_scale_factor=1)
    ctx.route("**/*", lambda r: r.abort() if r.request.method != "GET" else r.continue_())
    for path in paths:
        t = ctx.new_page()
        try:
            t.goto("https://cymetica.com" + path, wait_until="domcontentloaded", timeout=30000)
            t.wait_for_timeout(5500)
            t.evaluate(HIDE)
            t.wait_for_timeout(400)
            top = t.evaluate("() => { const m = document.querySelector('main') || document.body; return Math.max(0, m.getBoundingClientRect().top + scrollY); }")
            png = t.screenshot(clip={"x": 0, "y": top, "width": 1280, "height": 720}, full_page=True)
            im = Image.open(BytesIO(png)).convert("RGB").resize((640, 360), Image.LANCZOS)
            im.save(OUT / f"{slug(path)}.jpg", quality=74, optimize=True)
            done[path] = f"/previews/{slug(path)}.jpg"
            print("ok", path)
        except Exception as e:   # one page that will not load leaves its card on the /og fallback
            print("skip", path, str(e)[:80])
        t.close()
    br.close()

index = OUT / "index.json"
old = json.loads(index.read_text(encoding="utf-8")) if index.exists() else {}
old.update(done)
index.write_text(json.dumps(old, indent=1, sort_keys=True), encoding="utf-8")
print(f"{len(done)} pictured, {len(old)} in previews/index.json")
