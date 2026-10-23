"""Replay the /company app offline and measure what it costs on a chosen machine.

Every request is answered from a recording (rec/) or from a folder of the app's own files (--variant): the live
v=6adb7183 files for "before", the patched ones for "after". Nothing reaches cymetica.com, no POST leaves, no
socket opens. The machine: "fast" (this PC's discrete GPU, full CPU) or "weak" (this PC's integrated Radeon, the CPU
slowed --cpu times; the GPU process is not slowed, so the integrated GPU is the GPU half of the weak machine).

  python perf.py --rec <rec> --variant <dir> --scenario universe --machine weak --runs 2 --out <json>
Scenarios: start (signed out: the entry page), universe (#universe, signed out), visit (?visit=14), ours (our own
company, signed in from a recorded /office).
"""
import argparse, asyncio, hashlib, json, shutil, statistics, sys, tempfile, time
from pathlib import Path
from urllib.parse import urlsplit
from playwright.async_api import async_playwright

HERE = Path(__file__).parent
INSTRUMENT = (HERE / "instrument.js").read_text(encoding="utf-8")
CT = {".js": "text/javascript", ".css": "text/css", ".html": "text/html; charset=utf-8", ".webp": "image/webp",
      ".png": "image/png", ".jpg": "image/jpeg", ".json": "application/json", ".svg": "image/svg+xml",
      ".webm": "video/webm", ".mp4": "video/mp4", ".woff2": "font/woff2"}
PAGES = {"/company/app": "app.html", "/company/app/": "app.html", "/company/app/start": "start.html",
         "/company/app/builder": "builder.html"}
VIEW = {"width": 1536, "height": 730}   # a 1920 x 1080 laptop at 125 %, the browser's own bars taken off
DPR = 1.25
FLAGS = {"fast": ["--enable-unsafe-webgpu", "--use-angle=d3d11"],
         "weak": ["--enable-unsafe-webgpu", "--use-angle=d3d11", "--use-webgpu-power-preference=force-low-power",
                  "--force_low_power_gpu"]}
# the two halves apart, to tell what a weak frame waits on: the weak chip with the processor at full speed, the strong
# chip with the processor slowed
FLAGS["weakgpu"], FLAGS["slowcpu"] = FLAGS["weak"], FLAGS["fast"]
SLOWED = ("weak", "slowcpu")


def key_for(rec: Path, url: str) -> Path:
    u = urlsplit(url)
    return rec / "http" / u.netloc / hashlib.sha1((u.path + "?" + u.query).encode()).hexdigest()[:16]


class Replay:
    def __init__(self, rec: Path, variant: Path, mode: str):
        self.rec, self.variant, self.mode = rec, variant, mode
        self.miss, self.served = [], {}

    async def handle(self, route):
        req = route.request
        if req.method != "GET":
            self.miss.append(req.method + " " + req.url)
            return await route.abort()
        u = urlsplit(req.url)
        body, ctype, status = None, None, 200
        if u.netloc == "cymetica.com":
            if u.path in PAGES and (self.variant / PAGES[u.path]).exists():
                f = self.variant / PAGES[u.path]
                body, ctype = f.read_bytes(), CT[".html"]
            elif u.path.startswith("/static/company/"):
                f = self.variant / u.path[len("/static/company/"):]
                if f.is_file():
                    body, ctype = f.read_bytes(), CT.get(f.suffix, "application/octet-stream")
            if body is None and self.mode == "ours":
                if u.path == "/auth/me":
                    body, ctype = json.dumps({"id": 113, "username": "expire76"}).encode(), CT[".json"]
                elif u.path == "/api/v1/company/office":
                    body, ctype = (self.rec / "auth" / "office.json").read_bytes(), CT[".json"]
                elif u.path == "/api/v1/company/universe":
                    j = json.loads(key_for(self.rec, req.url).with_suffix(".body").read_bytes())
                    for c in j.get("companies", []):
                        c["mine"] = c.get("id") == 14
                    body, ctype = json.dumps(j).encode(), CT[".json"]
        if body is None:
            k = key_for(self.rec, req.url)
            meta = k.with_name(k.name + ".meta")
            if meta.exists():
                m = json.loads(meta.read_text())
                body, ctype, status = k.with_name(k.name + ".body").read_bytes(), m["ct"], m["status"]
        if body is None:
            self.miss.append(req.url)
            return await route.abort()
        self.served[u.netloc + u.path] = len(body)
        await route.fulfill(status=status, content_type=ctype, body=body,
                            headers={"Access-Control-Allow-Origin": "*", "Cache-Control": "max-age=2592000"})


def stats(frames, longtasks, t0, t1, present=None, spans=None):
    """rAF ticks (the page answering), long tasks (the main thread held), the scenes' drawn frames and the GPU's busy
    share in [t0, t1]."""
    fr = [t for t in frames if t0 <= t <= t1]
    gaps = [b - a for a, b in zip(fr, fr[1:])]
    lt = [d for s, d in longtasks if t0 <= s <= t1]
    out = {"ms": round(t1 - t0), "lt_n": len(lt), "lt_sum": round(sum(lt)), "lt_max": round(max(lt) if lt else 0)}
    if gaps:
        g = sorted(gaps)
        out.update(tick_p95=round(g[int(len(g) * 0.95)], 1), tick_max=round(g[-1]),
                   over50=sum(1 for x in g if x > 50), over100=sum(1 for x in g if x > 100))
    if present is not None:
        pr = [t for t in present if t0 <= t <= t1]
        dg = sorted(b - a for a, b in zip(pr, pr[1:]))
        out["draws"] = len(pr)
        if dg and pr[-1] > pr[0]:
            out.update(draw_fps=round(len(dg) / ((pr[-1] - pr[0]) / 1000), 1), draw_p50=round(dg[len(dg) // 2], 1),
                       draw_p95=round(dg[int(len(dg) * 0.95)], 1), draw_max=round(dg[-1]))
    if spans is not None and t1 > t0:
        busy = sum(max(0.0, min(b, t1) - max(a, t0)) for a, b in spans)
        out["gpu_busy"] = round(100 * busy / (t1 - t0))
    return out


async def wait_mark(pg, names, timeout_s):
    t = time.time()
    while time.time() - t < timeout_s:
        m = await pg.evaluate("window.__perf ? window.__perf.marks : {}")
        if all(n in m for n in names):
            return True
        await pg.wait_for_timeout(100)
    return False


PHASE_PROF = {}   # {"cdp", "path", "phase"}: a CPU profile of one phase only (--prof-phase)


async def mark(pg, k):
    await pg.evaluate(f"window.__perf && window.__perf.mark({json.dumps(k)})")
    P = PHASE_PROF
    if P and k == P["phase"] + "0":
        await P["cdp"].send("Profiler.enable"); await P["cdp"].send("Profiler.setSamplingInterval", {"interval": 250})
        await P["cdp"].send("Profiler.start")
    if P and k == P["phase"] + "1":
        prof = await P["cdp"].send("Profiler.stop")
        Path(P["path"]).write_text(json.dumps(prof["profile"]))


async def drag_circle(pg, cx, cy, r, seconds, button="left"):
    """A turn of the view, the button let go well away from where it went down: let go where it was pressed, the page
    takes the drag for a click (the office opens Add a department on an empty slot, the map opens a station)."""
    import math
    await pg.mouse.move(cx + r, cy)
    await pg.mouse.down(button=button)
    steps = int(seconds * 60)
    for i in range(steps):
        a = i / steps * math.pi * 1.75
        await pg.mouse.move(cx + r * math.cos(a), cy + r * 0.45 * math.sin(a))
        await pg.wait_for_timeout(16)
    await pg.mouse.up(button=button)


async def stage_center(pg, sel):
    b = await pg.evaluate(f"(() => {{ const e = document.querySelector({json.dumps(sel)}); if (!e) return null; const r = e.getBoundingClientRect(); return [r.x + r.width / 2, r.y + r.height / 2, r.width, r.height]; }})()")
    return b or [VIEW["width"] / 2, VIEW["height"] / 2, 600, 400]


async def scenario(pg, name, t_nav):
    """Drive the page; returns the phases as (name, from mark, to mark)."""
    if name == "start":
        await pg.goto("https://cymetica.com/company/app", wait_until="commit")
        await pg.wait_for_url("**/company/app/start", timeout=60000)
        await wait_mark(pg, ["bootGone"], 60)
        await mark(pg, "idle0"); await pg.wait_for_timeout(8000); await mark(pg, "idle1")
        return [("load", None, "bootGone"), ("idle", "idle0", "idle1")]
    if name == "universe":
        await pg.goto("https://cymetica.com/company/app#universe", wait_until="commit")
        await wait_mark(pg, ["bootGone"], 60)
        # (its first look flies in for 3.4 s and settles; idle is after that)
        await pg.wait_for_timeout(6000)
        await mark(pg, "idle0"); await pg.wait_for_timeout(5000); await mark(pg, "idle1")
        cx, cy, w, h = await stage_center(pg, "#uvstage")
        await mark(pg, "drag0"); await drag_circle(pg, cx, cy, min(w, h) * 0.25, 5); await mark(pg, "drag1")
        await pg.mouse.move(cx, cy)
        await mark(pg, "zoom0")
        for i in range(16):
            await pg.mouse.wheel(0, -120 if i < 8 else 120); await pg.wait_for_timeout(120)
        await pg.wait_for_timeout(1000); await mark(pg, "zoom1")
        return [("load", None, "bootGone"), ("idle", "idle0", "idle1"), ("drag", "drag0", "drag1"), ("zoom", "zoom0", "zoom1")]
    if name == "visit":
        await pg.goto("https://cymetica.com/company/app?visit=14", wait_until="commit")
        await wait_mark(pg, ["bootGone"], 60)
        await pg.wait_for_timeout(3000)
        await mark(pg, "idle0"); await pg.wait_for_timeout(6000); await mark(pg, "idle1")
        cx, cy, w, h = await stage_center(pg, "#stage")
        await mark(pg, "drag0"); await drag_circle(pg, cx, cy, min(w, h) * 0.25, 4); await mark(pg, "drag1")
        return [("load", None, "bootGone"), ("idle", "idle0", "idle1"), ("drag", "drag0", "drag1")]
    if name == "ours":
        await pg.goto("https://cymetica.com/company/app", wait_until="commit")
        await wait_mark(pg, ["bootGone"], 60)
        # the first 20 s after the loading screen: what the page builds behind the office while it is looked at
        await mark(pg, "idle0"); await pg.wait_for_timeout(20000); await mark(pg, "idle1")
        cx, cy, w, h = await stage_center(pg, "#stage")
        await mark(pg, "drag0"); await drag_circle(pg, cx, cy, min(w, h) * 0.25, 4); await mark(pg, "drag1")
        await mark(pg, "uvtab0")
        f0 = await pg.evaluate("window.CO && CO.uv && CO.uv.frames || 0")
        await pg.click('#tabs [data-tab="universe"]')
        # open: the map has drawn two new frames and its loading screen (if it needed one) is gone; built ahead, it had none
        await pg.wait_for_function("(f0) => { const u = window.CO && CO.uv, l = document.getElementById('uvload');"
                                   " return u && (u.frames || 0) >= f0 + 2 && (!l || l.hidden); }", arg=f0, timeout=60000)
        await mark(pg, "uvtab1")
        cx, cy, w, h = await stage_center(pg, "#uvstage")
        await mark(pg, "uvdrag0"); await drag_circle(pg, cx, cy, min(w, h) * 0.25, 4); await mark(pg, "uvdrag1")
        await mark(pg, "back0")
        await pg.click('#tabs [data-tab="office"]')
        await pg.wait_for_timeout(4000); await mark(pg, "back1")
        return [("load", None, "bootGone"), ("idle", "idle0", "idle1"), ("drag", "drag0", "drag1"),
                ("uvopen", "uvtab0", "uvtab1"), ("uvdrag", "uvdrag0", "uvdrag1"), ("back", "back0", "back1")]
    raise SystemExit("no such scenario: " + name)


async def one_run(p, args, profile_dir):
    flags = FLAGS[args.machine] + ["--disable-background-timer-throttling", "--disable-renderer-backgrounding"]
    # the installed Chrome: Playwright's own Chromium has no DXC libraries, so its WebGPU cannot make a device on
    # Windows and three.js quietly draws through WebGL2 instead (measured 2026-10-23)
    ctx = await p.chromium.launch_persistent_context(str(profile_dir), headless=not args.headed, args=flags, channel="chrome",
                                                     viewport=VIEW, device_scale_factor=DPR)
    rp = Replay(Path(args.rec), Path(args.variant), "ours" if args.scenario == "ours" else "out")
    await ctx.route("**/*", rp.handle)
    await ctx.route_web_socket("**/*", lambda ws: ws.close())
    await ctx.add_init_script(INSTRUMENT)
    # the level by hand (quality.js reads Settings' choice from localStorage, so it holds across the entry's redirect);
    # "auto" leaves the choice to the chip's name and the frames
    if args.q:
        await ctx.add_init_script("try { localStorage.removeItem('co.q3.auto'); " + ("localStorage.removeItem('co.q3')" if args.q == "auto" else f"localStorage.setItem('co.q3', '{args.q}')") + " } catch (e) {}")
    if args.init:
        await ctx.add_init_script(Path(args.init).read_text(encoding="utf-8"))
    # a diagnosis: once the office (or the map) has drawn 5 frames, one part of its scene taken away, to see what that
    # part costs (o: the scene object, CO.o3 or CO.uv)
    DIAG = {"nosky": "o.sky.visible = false;",
            "nolamps": "o.scene.traverse((x) => { if (x.isPointLight) x.visible = false; });",
            "noglass": "o.scene.traverse((x) => { if (x.isMesh && x.material && x.material.transparent && x !== o.sky) x.visible = false; });",
            "noshadow": "if (o.sun) o.sun.castShadow = false;",
            "nopost": "o.post = null;",
            "nofill": "o.scene.traverse((x) => { if (x.isDirectionalLight || x.isHemisphereLight) x.visible = false; });"}
    if args.diag:
        js = " ".join(DIAG[d] for d in args.diag.split(","))
        await ctx.add_init_script("(() => { const t = setInterval(() => { const o = window.CO && (CO.o3 || CO.uv); if (!o || !(o.frames > 5)) return;"
                                  " clearInterval(t); try { " + js + " } catch (e) { console.error('diag', e); } }, 100); })();")
    # one setting of the level changed by hand (what each costs): laid over CO.Q3 as quality.js sets it
    if args.set:
        await ctx.add_init_script("(() => { const O = " + args.set + "; const C = window.CO = window.CO || {}; let q;"
                                  " Object.defineProperty(C, 'Q3', { configurable: true, get() { return q; }, set(v) { q = Object.assign(v, O); } }); })();")
    pg = ctx.pages[0] if ctx.pages else await ctx.new_page()
    console = []
    pg.on("console", lambda msg: console.append(msg.type + ": " + msg.text[:240]) if msg.type in ("error", "warning") else None)
    pg.on("pageerror", lambda e: console.append("pageerror: " + str(e)[:240]))
    cdp = await ctx.new_cdp_session(pg)
    cpu = args.cpu if args.machine in SLOWED else 1
    if cpu > 1:
        await cdp.send("Emulation.setCPUThrottlingRate", {"rate": cpu})
    if args.cpuprofile and args.prof_phase:
        PHASE_PROF.clear(); PHASE_PROF.update(cdp=cdp, path=args.cpuprofile, phase=args.prof_phase)
    elif args.cpuprofile:
        await cdp.send("Profiler.enable"); await cdp.send("Profiler.setSamplingInterval", {"interval": 500})
        await cdp.send("Profiler.start")
    t_nav = time.time() * 1000
    phases = await scenario(pg, args.scenario, t_nav)
    if args.cpuprofile and not args.prof_phase:
        prof = await cdp.send("Profiler.stop")
        Path(args.cpuprofile).write_text(json.dumps(prof["profile"]))
    PHASE_PROF.clear()
    if args.shot:
        await pg.screenshot(path=args.shot)
    P = await pg.evaluate("""() => { const M = window.__perf; return { frames: M.frames, longtasks: M.longtasks, marks: M.marks,
        present: M.present || [], spans: M.gpuSpans || [], passes: M.passes || {},
        gpu: { devices: M.devices, contexts: M.contexts, pipelinesSync: M.pipelinesSync, pipelinesAsync: M.pipelinesAsync,
               shaderModules: M.shaderModules, syncPipeMs: Math.round(M.syncPipeMs), textures: M.textures,
               texPeakMB: Math.round(M.texBytesPeak / 1048576), texLiveMB: Math.round(M.texBytesLive / 1048576) },
        heapMB: performance.memory ? Math.round(performance.memory.usedJSHeapSize / 1048576) : null,
        origin: performance.timeOrigin, errors: M.errors, tier: window.CO && CO.Q3 ? CO.Q3.name : null,
        dbg: { backend: (() => { try { const r = (CO.uv || CO.o3 || {}).renderer; return r && r.backend ? (r.backend.isWebGPUBackend ? 'webgpu' : 'webgl') : null; } catch (e) { return String(e); } })(),
               wrapped: window.GPUDevice ? String(GPUDevice.prototype.createRenderPipeline).slice(0, 40) : 'no GPUDevice' } }; }""")
    await ctx.close()
    res = {"phases": {}, "gpu": P["gpu"], "heapMB": P["heapMB"], "errors": P["errors"][:5], "tier": P["tier"], "dbg": P["dbg"],
           "console": [c for c in console if "401" not in c][:8],
           # draw calls per drawn frame, by pass kind, over the whole run
           "draws_per_frame": {k: round(v["draws"] / max(1, len(P["present"])), 1) for k, v in P["passes"].items() if v["draws"] / max(1, len(P["present"])) >= 0.5},
           "passes_per_frame": {k: round(v["passes"] / max(1, len(P["present"])), 2) for k, v in P["passes"].items()},
           "miss": rp.miss[:20], "bytes": sum(rp.served.values())}
    m = P["marks"]
    for name, a, b in phases:
        if b not in m:
            res["phases"][name] = {"missing": b}
            continue
        t0 = m[a] if a else 0.0
        res["phases"][name] = stats(P["frames"], P["longtasks"], t0, m[b], P["present"], P["spans"])
    # the load from the click: the entry page is a second document (the app sends a signed-out visitor there)
    if "bootGone" in m:
        res["boot_ms"] = round(P["origin"] + m["bootGone"] - t_nav)
    # the first frame a 3D scene put on the screen (the entry page's live scenes come after the page itself)
    if P["present"]:
        res["first_draw_ms"] = round(P["origin"] + P["present"][0] - t_nav)
    return res


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rec", required=True); ap.add_argument("--variant", required=True)
    ap.add_argument("--scenario", required=True); ap.add_argument("--machine", default="weak")
    ap.add_argument("--cpu", type=float, default=3); ap.add_argument("--runs", type=int, default=1)
    ap.add_argument("--warm", action="store_true", help="one unmeasured load first, in the same profile")
    ap.add_argument("--headed", action="store_true"); ap.add_argument("--out")
    ap.add_argument("--cpuprofile"); ap.add_argument("--shot"); ap.add_argument("--init")
    ap.add_argument("--q", help="high | medium | low | auto (the after variant's quality.js)")
    ap.add_argument("--set", help='settings laid over the level, JSON: {"samples": 0}')
    ap.add_argument("--diag", help="nosky,nolamps,noglass,noshadow,nopost,nofill: a part of the scene taken away after 5 frames")
    ap.add_argument("--prof-phase", help="with --cpuprofile: profile only this phase (drag, idle, ...)")
    args = ap.parse_args()
    out = []
    async with async_playwright() as p:
        for i in range(args.runs):
            prof = Path(tempfile.mkdtemp(prefix="coperf-"))
            try:
                if args.warm:
                    await one_run(p, args, prof)
                r = await one_run(p, args, prof)
            finally:
                shutil.rmtree(prof, ignore_errors=True)
            r.update(run=i, machine=args.machine, cpu=args.cpu, warm=args.warm, variant=Path(args.variant).name, scenario=args.scenario, q=args.q, set=args.set, diag=args.diag)
            out.append(r)
            print(json.dumps({k: r[k] for k in ("run", "boot_ms", "gpu", "tier", "dbg", "draws_per_frame") if k in r}), flush=True)
            for k, v in r["phases"].items():
                print("   ", k, json.dumps(v), flush=True)
            if r["miss"]:
                print("    miss:", r["miss"][:8], flush=True)
            if r["errors"]:
                print("    errors:", r["errors"], flush=True)
            if r["console"]:
                print("    console:", r["console"], flush=True)
    if args.out:
        Path(args.out).write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    asyncio.run(main())

