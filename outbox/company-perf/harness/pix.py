"""Is the high level the page as it was, pixel for pixel? Each place drawn with its clock stopped, before and after.

The clock is held (performance.now and Date fixed, Math.random seeded, CSS animations and transitions stopped), so a
scene draws the same state on every frame; the picture is taken after it has drawn ~40 frames of that state. Run the
before variant twice first: what differs between two runs of the same page is the floor a before/after is read against.
  python pix.py <rec> <variant A> <variant B> <out dir> [--q high] [places...]
Places: visit (the office of company 14, read only), universe (#universe), start (the entry page, live scenes)."""
import asyncio, json, sys
from pathlib import Path
from playwright.async_api import async_playwright
from PIL import Image, ImageChops

sys.path.insert(0, str(Path(__file__).parent))
from perf import Replay, FLAGS, VIEW, DPR  # noqa: E402

FREEZE = """(() => {
  const T = 1e9, D = 1798761600000;   // a fixed moment (a date later than every timestamp in the recording)
  performance.now = () => T;
  Date.now = () => D;
  const OD = Date; window.Date = class extends OD { constructor(...a) { if (!a.length) super(D); else super(...a); } static now() { return D; } };
  let s = 1234567; Math.random = () => { s = (s + 0x6D2B79F5) | 0; let t = Math.imul(s ^ (s >>> 15), 1 | s); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
  const st = document.createElement('style'); st.textContent = '*,*::before,*::after{animation-play-state:paused!important;animation-delay:0s!important;transition:none!important;caret-color:transparent!important}';
  (document.head || document.documentElement).appendChild(st);
  document.addEventListener('DOMContentLoaded', () => document.head.appendChild(st));
})();"""
URLS = {"visit": "https://cymetica.com/company/app?visit=14", "universe": "https://cymetica.com/company/app#universe",
        "start": "https://cymetica.com/company/app/start"}


async def shot(p, rec, variant, place, out, q, setting=None):
    ctx = await p.chromium.launch_persistent_context("", headless=True, args=FLAGS["fast"], channel="chrome", viewport=VIEW, device_scale_factor=DPR)
    rp = Replay(rec, variant, "out")
    await ctx.route("**/*", rp.handle)
    await ctx.route_web_socket("**/*", lambda ws: ws.close())
    await ctx.add_init_script(FREEZE)
    if q:
        await ctx.add_init_script(f"try {{ localStorage.removeItem('co.q3.auto'); localStorage.setItem('co.q3', '{q}'); }} catch (e) {{}}")
    if setting:   # one setting laid over the level (perf.py --set)
        await ctx.add_init_script("(() => { const O = " + setting + "; const C = window.CO = window.CO || {}; let v;"
                                  " Object.defineProperty(C, 'Q3', { configurable: true, get() { return v; }, set(x) { v = Object.assign(x, O); } }); })();")
    pg = ctx.pages[0] if ctx.pages else await ctx.new_page()
    await pg.goto(URLS[place])
    # drawn: the scenes' canvases have presented ~40 frames of the held state, and nothing is loading
    await pg.wait_for_timeout(9000 if place != "start" else 12000)
    await pg.screenshot(path=str(out))
    await ctx.close()
    return rp.miss


def diff(a, b):
    A, B = Image.open(a).convert("RGB"), Image.open(b).convert("RGB")
    if A.size != B.size:
        return {"size": [A.size, B.size]}
    d = ImageChops.difference(A, B)
    px = sum(1 for v in d.getdata() if max(v) > 0)
    big = sum(1 for v in d.getdata() if max(v) > 8)
    return {"px": px, "over8": big, "bbox": d.getbbox()}


async def main():
    rec, va, vb, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4])
    rest = sys.argv[5:]
    opt = {"--q": None, "--qa": None, "--seta": None, "--setb": None}
    for k in list(opt):
        if k in rest:
            i = rest.index(k); opt[k] = rest[i + 1]; rest = rest[:i] + rest[i + 2:]
    places = rest or ["visit", "universe", "start"]
    out.mkdir(parents=True, exist_ok=True)
    res = {}
    async with async_playwright() as p:
        for place in places:
            a1, a2, b = out / f"{place}-A1.png", out / f"{place}-A2.png", out / f"{place}-B.png"
            await shot(p, rec, va, place, a1, opt["--qa"], opt["--seta"])
            await shot(p, rec, va, place, a2, opt["--qa"], opt["--seta"])
            await shot(p, rec, vb, place, b, opt["--q"], opt["--setb"])
            res[place] = {"A/A": diff(a1, a2), "A/B": diff(a1, b)}
            print(place, json.dumps(res[place], default=str), flush=True)
    (out / "pix.json").write_text(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    asyncio.run(main())
