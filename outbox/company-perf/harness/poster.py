"""The entry page's pictures of its own scenes (start-space.webp, start-room.webp, start-uv.webp), drawn by the live
page itself (the before variant, offline replay, the fast machine): the sun's scene at a 3.5 : 1 stage 800 px high
(the camera frames the sun by the stage's height, so one wide picture serves every window when scaled to its height
and centred), the two doors' pictures at twice their size. The hero and the darkening over the scene are hidden for
the moment of the picture.
  python poster.py <rec> <variant> <out dir>"""
import asyncio, sys
from pathlib import Path
from playwright.async_api import async_playwright
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from perf import Replay, FLAGS  # noqa: E402

REC, VAR, OUT = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
HIDE = ".lp-hero{visibility:hidden!important}.lp-main::before{display:none!important}.lp-space{--sh:0px!important}"


async def shoot(p, view, dpr, sel_files, hide_hero):
    ctx = await p.chromium.launch_persistent_context("", headless=True, args=FLAGS["fast"], channel="chrome",
                                                     viewport=view, device_scale_factor=dpr)
    rp = Replay(REC, VAR, "out")
    await ctx.route("**/*", rp.handle)
    await ctx.route_web_socket("**/*", lambda ws: ws.close())
    pg = ctx.pages[0] if ctx.pages else await ctx.new_page()
    await pg.goto("https://cymetica.com/company/app/start")
    # until the loading screen has gone: the sun and both doors have drawn (start.js whenDrawn)
    await pg.wait_for_function("() => { const b = document.getElementById('boot'); return !b || b.classList.contains('gone'); }", timeout=60000)
    if hide_hero:
        await pg.add_style_tag(content=HIDE)
    await pg.wait_for_timeout(1500)
    for sel, name in sel_files:
        png = OUT / (name + ".png")
        await pg.locator(sel).screenshot(path=str(png))
        im = Image.open(png).convert("RGB")
        im.save(OUT / (name + ".webp"), "WEBP", quality=78, method=6)
        print(name, im.size, (OUT / (name + ".webp")).stat().st_size)
        png.unlink()
    if rp.miss:
        print("miss", rp.miss[:5])
    await ctx.close()


async def main():
    OUT.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as p:
        await shoot(p, {"width": 2800, "height": 800}, 1, [("#lp-space", "start-space")], True)
        await shoot(p, {"width": 1536, "height": 730}, 2, [("#lp-room", "start-room"), ("#lp-uvpic", "start-uv")], False)

asyncio.run(main())
