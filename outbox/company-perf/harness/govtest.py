"""The frames' verdict, run once: on the weak machine, a chip whose name says high (the renderer string replaced by an
add-in card's) opens an office and turns it. While turned it cannot hold ~38 frames a second, so u3d.js govern() should
draw fewer pixels twice and keep the level one lower for this chip (localStorage co.q3.auto); the next visit should
then start at medium, chosen "by frames". Prints what each step found.
  python govtest.py <rec> <variant> [seconds of turning]"""
import asyncio, json, sys
from pathlib import Path
from playwright.async_api import async_playwright

sys.path.insert(0, str(Path(__file__).parent))
from perf import Replay, FLAGS, VIEW, DPR, drag_circle, stage_center  # noqa: E402

CHIP = "ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 (0x00002504) Direct3D11 vs_5_0 ps_5_0, D3D11)"
SPOOF = ("(() => { const N = %s; for (const C of [window.WebGL2RenderingContext, window.WebGLRenderingContext]) {"
         " if (!C) continue; const g = C.prototype.getParameter;"
         " C.prototype.getParameter = function (p) { return p === 0x9246 ? N : g.call(this, p); }; } })();") % json.dumps(CHIP)
Q = "(() => { const q = window.CO && CO.Q3; return q ? { name: q.name, by: q.by, scale: q.scale, chip: q.chip.slice(0, 40),"
Q += " kept: localStorage.getItem('co.q3.auto') } : null; })()"


async def main():
    rec, var = Path(sys.argv[1]), Path(sys.argv[2])
    secs = float(sys.argv[3]) if len(sys.argv) > 3 else 8
    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context("", headless=True, args=FLAGS["weak"], channel="chrome",
                                                         viewport=VIEW, device_scale_factor=DPR)
        rp = Replay(rec, var, "out")
        await ctx.route("**/*", rp.handle)
        await ctx.route_web_socket("**/*", lambda ws: ws.close())
        await ctx.add_init_script(SPOOF)
        pg = ctx.pages[0] if ctx.pages else await ctx.new_page()
        errs = []
        pg.on("console", lambda m: errs.append(m.text[:200]) if m.type == "error" and "401" not in m.text else None)
        cdp = await ctx.new_cdp_session(pg)
        await cdp.send("Emulation.setCPUThrottlingRate", {"rate": 3})
        res = {}
        await pg.goto("https://cymetica.com/company/app?visit=14")
        await pg.wait_for_function("() => window.CO && CO.o3 && CO.o3.frames > 30", timeout=90000)
        await pg.wait_for_timeout(3500)
        res["opened"] = await pg.evaluate(Q)
        cx, cy, w, h = await stage_center(pg, "#stage")
        await drag_circle(pg, cx, cy, min(w, h) * 0.25, secs)
        await pg.wait_for_timeout(500)
        res["after_turning"] = await pg.evaluate(Q)
        await pg.goto("https://cymetica.com/company/app?visit=14")
        await pg.wait_for_function("() => window.CO && CO.Q3", timeout=60000)
        res["next_visit"] = await pg.evaluate(Q)
        res["errors"] = errs[:4]
        res["miss"] = rp.miss[:4]
        await ctx.close()
        print(json.dumps(res, indent=1))

if __name__ == "__main__":
    asyncio.run(main())
