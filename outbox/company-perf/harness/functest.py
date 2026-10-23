"""The paths the timing scenarios do not walk, at each level, on the fast machine: (a) signed in, opened on the
Universe, then Headquarters: the office is built then, under the stage's loading screen, and draws; (b) Add a
department: the dialog's room draws (at low with no floors' mirror); (c) Settings > Graphics is there. Console errors
are failures. Pictures of each step go to <out>.
  python functest.py <rec> <variant> <out dir> [levels...]"""
import asyncio, json, sys
from pathlib import Path
from playwright.async_api import async_playwright

sys.path.insert(0, str(Path(__file__).parent))
from perf import Replay, FLAGS, VIEW, DPR  # noqa: E402


async def level(p, rec, var, out, q):
    ctx = await p.chromium.launch_persistent_context("", headless=True, args=FLAGS["fast"], channel="chrome", viewport=VIEW, device_scale_factor=DPR)
    rp = Replay(rec, var, "ours")
    await ctx.route("**/*", rp.handle)
    await ctx.route_web_socket("**/*", lambda ws: ws.close())
    await ctx.add_init_script(f"try {{ localStorage.removeItem('co.q3.auto'); localStorage.setItem('co.q3', '{q}'); }} catch (e) {{}}")
    pg = ctx.pages[0] if ctx.pages else await ctx.new_page()
    errs = []
    pg.on("console", lambda m: errs.append(m.text[:200]) if m.type == "error" and "401" not in m.text else None)
    pg.on("pageerror", lambda e: errs.append("pageerror " + str(e)[:200]))
    res = {"q": q}
    # (a) opened on the Universe: no 3D office yet; Headquarters builds it under #o3load
    await pg.goto("https://cymetica.com/company/app#universe")
    await pg.wait_for_function("() => window.CO && CO.uv && CO.uv.frames > 5", timeout=60000)
    res["office_before_click"] = await pg.evaluate("!!(window.CO && CO.o3)")
    await pg.click('#tabs [data-tab="office"]')
    await pg.wait_for_timeout(300)
    res["o3load_shown"] = await pg.evaluate("(() => { const l = document.getElementById('o3load'); return !!l && !l.hidden; })()")
    await pg.wait_for_function("() => window.CO && CO.o3 && CO.o3.frames > 30", timeout=60000)
    await pg.wait_for_timeout(800)
    res["o3load_gone"] = await pg.evaluate("(() => { const l = document.getElementById('o3load'); return !l || l.hidden; })()")
    res["frozen"] = await pg.evaluate("(() => { let n = 0; CO.o3.scene.traverse((x) => { if (x.isMesh && x.parent && x.parent.isBundleGroup) n++; }); return n; })()")
    await pg.screenshot(path=str(out / f"func-{q}-office.png"))
    # (b) Add a department: the dialog's room draws
    await pg.click("#add-dept")
    await pg.wait_for_timeout(500)
    await pg.wait_for_function("() => { const c = document.querySelector('#modal .d3cv canvas'); return !!c; }", timeout=30000)
    await pg.wait_for_timeout(6000)
    res["dialog_frames"] = await pg.evaluate("(() => { try { return CO.U3.dialogPreview().frames || 0; } catch (e) { return String(e); } })()")
    await pg.screenshot(path=str(out / f"func-{q}-dialog.png"))
    await pg.keyboard.press("Escape")
    await pg.wait_for_timeout(500)
    # (c) Settings > Graphics
    await pg.click('#tabs [data-tab="settings"]')
    await pg.wait_for_timeout(800)
    res["graphics_card"] = await pg.evaluate("Array.from(document.querySelectorAll('#settings [data-a=\"q3\"]')).map((b) => b.textContent + (b.classList.contains('cy') ? '*' : ''))")
    res["errors"] = errs[:6]
    res["miss"] = rp.miss[:4]
    await ctx.close()
    return res


async def main():
    rec, var, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    out.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as p:
        for q in (sys.argv[4:] or ["high", "medium", "low"]):
            print(json.dumps(await level(p, rec, var, out, q)), flush=True)

asyncio.run(main())
