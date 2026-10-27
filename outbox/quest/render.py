"""The Quest guide's film: camera flights through the /company mock's own 3D Universe, rendered frame by frame, each
frame screened over the flyer's deep space with the flyer's sunlight, so the first frame is the flyer's picture and the
last ones are the live Universe.

    python outbox/quest/render.py keys            # the keyframes only, as a contact sheet (shots/keys-<set>.png)
    python outbox/quest/render.py film            # every flight, both sets (frames/<set>/<seq>/NNNN.webp + manifest)
    python outbox/quest/render.py office          # placeholder stills of the office rooms until Antigravity's arrive
    python outbox/quest/render.py gen             # Antigravity's pictures (gen/*.png) into stills/, replacing them
    add --set desk or --set mob for one set only

Needs the mock served on http://127.0.0.1:8793 (the company-mock entry in .claude/launch.json), Chrome with a real GPU
(channel "chrome", WebGPU on d3d11: swiftshader is far too slow for hundreds of frames), Playwright, numpy and PIL.
Nothing here is kept in git but this file: frames/, stills/ and shots/ are made here.

How a frame is made (the flyer's render.py, generalised):
  * the page's clock is ours: performance.now and Date.now return a time we advance by 1/30 s a frame, so the stations
    move on their orbits smoothly and the same frame renders the same way twice (pix.py's freeze, made to step);
  * the camera is set from five numbers per keyframe -- what it looks at (the sun, our company, the Agent Casino, the
    Promo Market), its polar angle and turn round the sun, its distance, and where that point sits on screen -- eased
    between keyframes, the looked-at point blended between two keyframes' points;
  * the scene's own sky is hidden; its ground colour is taken back to black and the picture screened over nebula.py's
    deep space (a plate a little larger than the frame, drifting and growing slowly as the camera moves), with the
    flyer's warm core and wide cyan haze laid round the sun where it projects;
  * the first flight starts on the sun alone, as the flyer has it (no lane, no station, no ring), and the Universe
    fades in as the camera comes closer: two passes a frame while it does, blended.
"""
import io
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'revenue-share-flyer'))
import nebula  # noqa: E402  (the flyer's deep space)

MOCK = 'http://127.0.0.1:8793/index.html?board=empty#universe'
SETS = {'desk': (2560, 1440), 'mob': (720, 1280)}   # desk was 1600 x 900 and read soft on a 2000 px screen (2026-10-27)
SEED, STRENGTH = 7, 0.5                      # the flyer's nebula
GROUND = np.array([1, 8, 13], np.float32)    # the Universe's clear colour (0x01080d), taken back to black
DT = 1000 / 30                               # ms of the page's time per frame

# keyframes: (frame, focus, polar, turn from the galaxy's azimuth, distance, (sx, sy) desk, (sx, sy) phone)
# The hero is the flyer's frame (polar 1.25, distance 900), the sun high on the right where the flyer has it.
FLIGHTS = {
    'approach': {'count': 180, 'reveal': (26, 104), 'plates': ['mine'], 'keys': [
        (0, 'sun', 1.25, 0.00, 900, (0.80, 0.17), (0.76, 0.13)),
        (36, 'sun', 1.24, 0.03, 760, (0.78, 0.20), (0.73, 0.16)),
        (112, 'sun', 1.10, 0.12, 250, (0.66, 0.34), (0.58, 0.30)),
        (179, 'mine', 1.12, 0.28, 100, (0.85, 0.60), (0.55, 0.34))]},
    'casino': {'count': 90, 'plates': ['casino'], 'keys': [
        (0, 'casino', 1.00, 0.55, 230, (0.70, 0.46), (0.52, 0.34)),
        (89, 'casino', 1.18, 0.85, 72, (0.70, 0.50), (0.52, 0.36))]},
    'promo': {'count': 90, 'plates': ['promo'], 'keys': [
        (0, 'casino', 1.18, 0.85, 72, (0.70, 0.50), (0.52, 0.36)),
        (45, 'promo', 1.04, 1.20, 170, (0.68, 0.48), (0.52, 0.34)),
        (89, 'promo', 1.18, 1.55, 72, (0.70, 0.50), (0.52, 0.36))]},
    'pullback': {'count': 120, 'plates': ['mine'], 'keys': [
        (0, 'promo', 1.18, 1.55, 72, (0.70, 0.50), (0.52, 0.36)),
        (60, 'sun', 1.02, 1.30, 300, (0.58, 0.58), (0.50, 0.36)),
        (119, 'sun', 0.92, 1.10, 560, (0.50, 0.66), (0.50, 0.30))]},
}
# the chapters' posters: which frame of which flight stands under a chapter before its frames have come
POSTERS = {'hero': ('approach', 0), 's1': ('approach', 179), 's2c': ('casino', 89), 's3': ('promo', 89), 's4': ('pullback', 119)}

CLOCK = """(() => {
  const real = performance.now.bind(performance), rd = Date.now;
  window.__qManual = false; window.__qT = 0;
  performance.now = () => window.__qManual ? window.__qT : real();
  Date.now = () => window.__qManual ? 1798761600000 + window.__qT : rd();
})();"""
HIDE = ("#uv-board, .b3pop, #uvstage .top, .uvlegend, #uv-panel, .tip, .uvtip, .b3.qhide { display: none !important; }"
        "#uvstage { position: fixed !important; left: 0 !important; top: 0 !important; width: 100vw !important; height: 100vh !important;"
        " margin: 0 !important; border-radius: 0 !important; border: 0 !important; z-index: 99999 !important; }")
SETUP = """() => { const u = CO.uv;
  const ad = (re) => u.items.find(x => x.ad && re.test(String(x.ad.key) + ' ' + String(x.ad.name)));
  window.__qF = { casino: ad(/casino/i), promo: ad(/promo/i), mine: u.items.find(x => x.mine) };
  if (!__qF.casino || !__qF.promo || !__qF.mine) throw new Error('stations not found: ' + JSON.stringify(u.items.filter(x => x.ad).map(x => x.ad.key + '/' + x.ad.name)));
  const keep = new Set([__qF.casino, __qF.promo, __qF.mine]);
  u.items.forEach(x => { if (x.el && !keep.has(x)) x.el.classList.add('qhide'); });
  document.querySelectorAll('#uvstage .rib').forEach(r => { if (/MY COMPANY/.test(r.textContent)) r.lastChild.textContent = 'YOUR COMPANY'; });
  u.pulse = () => {}; u.sharePulse = () => {};
  u.sky.visible = false;
  const sunPar = u.sun.parent, scene = sunPar.parent;
  window.__qAll = scene.children.filter(c => !c.isLight && c !== sunPar && c !== u.sky && c.visible);
  window.__qSunKids = sunPar.children.filter(c => c !== u.sun && c.visible);
  window.__qT = performance.now(); window.__qManual = true; }"""
# the sun alone (the flyer's ONLY_SUN), taken fresh each time: a light pulse or arc added since the last frame is hidden too
UNIVERSE = """(on) => { const u = CO.uv, sunPar = u.sun.parent, scene = sunPar.parent;
  if (!on) {
    window.__qHid = scene.children.filter(c => !c.isLight && c !== sunPar && c !== u.sky && c.visible)
      .concat(sunPar.children.filter(c => c !== u.sun && c.visible));
    __qHid.forEach(c => { c.visible = false; });
  } else { (window.__qHid || []).forEach(c => { c.visible = true; }); window.__qHid = []; }
  document.querySelectorAll('#uvstage .b3').forEach(b => { b.style.visibility = on ? '' : 'hidden'; }); }"""
# which plates a flight shows: only the station its chapter is about (a plate is page type baked into the picture, and
# any other one lands under the chapter's text or the board's glass)
PLATES = """(keep) => { const want = new Set(keep.map(k => __qF[k] && __qF[k].el).filter(Boolean));
  document.querySelectorAll('#uvstage .b3').forEach(b => { b.classList.toggle('qhide', !want.has(b)); }); }"""
CAMERA = """([fa, fb, w, pol, az, dist, sx, sy, T]) => {
  window.__qT = T;
  const u = CO.uv, c = u.camera, t = u.controls.target, V = c.position.constructor, AZ = CO.uvGalaxy.AZ + az;
  u.tw = null; u.follow = null; u.followAt = null; u.used = true;
  const at = (k) => { if (k === 'sun') return u.heartAt.clone(); const it = __qF[k], r = it.plot.root;
    const p = r.position.clone(); p.y += ((it.plot.top || 0) + (it.plot.bot || 0)) / 2 * (r.scale.y || 1); return p; };
  const focus = at(fa).lerp(at(fb), w);
  const dir = new V(Math.sin(pol) * Math.sin(AZ), Math.cos(pol), Math.sin(pol) * Math.cos(AZ));
  const right = new V(0, 1, 0).cross(dir).normalize(), up = right.clone().cross(dir.clone().negate()).normalize();
  const h = 2 * dist * Math.tan(c.fov * Math.PI / 360), wd = h * c.aspect;
  const pan = right.multiplyScalar(-(sx - 0.5) * wd).add(up.multiplyScalar((sy - 0.5) * h));
  t.copy(focus).add(pan); c.position.copy(focus).addScaledVector(dir, dist).add(pan); u.controls.update();
  c.updateMatrixWorld(); const s = u.heartAt.clone().project(c);
  return [(s.x + 1) / 2, (1 - s.y) / 2, s.z < 1 ? 1 : 0, c.position.distanceTo(u.heartAt)]; }"""
# The page's pacer draws only when its clock has moved (12.5 ms at least), so while we wait for a frame the clock steps
# 20 ms a display frame: a frame's picture is the scene some 40 to 60 ms after its own time T, the same for every frame.
FRAMES_UP = """(n) => new Promise(r => { const f0 = CO.uv.frames;
  (function w() { window.__qT += 20; CO.uv.frames >= f0 + n ? r() : requestAnimationFrame(w); })(); })"""


def smooth(t):
    t = min(max(t, 0.0), 1.0)
    return t * t * (3 - 2 * t)


def camera_at(flight, f, phone):
    keys = flight['keys']
    for a, b in zip(keys, keys[1:]):
        if a[0] <= f <= b[0]:
            break
    else:
        a = b = keys[-1]
    t = smooth((f - a[0]) / max(1, b[0] - a[0]))
    lerp = lambda x, y: x + (y - x) * t  # noqa: E731
    sa, sb = (a[6], b[6]) if phone else (a[5], b[5])
    return [a[1], b[1], t, lerp(a[2], b[2]), lerp(a[3], b[3]),
            math.exp(lerp(math.log(a[4]), math.log(b[4]))),     # distance eased in log space: no lurch at the end
            lerp(sa[0], sb[0]), lerp(sa[1], sb[1])]


class Plate:
    """The flyer's deep space at this set's shape, 30 % larger than the frame, so it can drift and grow under the
    camera without an edge ever showing."""
    def __init__(self, w, h):
        self.w, self.h = w, h
        nebula.W, nebula.H = int(w * 1.3), int(h * 1.3)
        self.img = np.clip(nebula.make(SEED, STRENGTH), 0, 255).astype(np.float32)

    def view(self, grow, dx, dy):
        H, W = self.img.shape[:2]
        cw, ch = self.w / grow * 1.0, self.h / grow * 1.0
        cw, ch = min(cw * 1.0, W), min(ch * 1.0, H)
        cx = W / 2 + dx * (W - cw) / 2
        cy = H / 2 + dy * (H - ch) / 2
        box = (int(cx - cw / 2), int(cy - ch / 2), int(cx + cw / 2), int(cy + ch / 2))
        crop = Image.fromarray(self.img.astype(np.uint8)).crop(box).resize((self.w, self.h), Image.BICUBIC)
        return np.asarray(crop, np.float32)


def screen(a, b):
    return 255 - (255 - a) * (255 - b) / 255


def sunlight(w, h, sx, sy, dist, vis):
    """The flyer's light round its sun (core 150 px and haze 620 px at 2160 wide), scaled to this frame and to how
    near the sun is: brighter and wider as the camera comes in, never washing the whole frame."""
    if not vis:
        return 0
    k = w / 2160 * min(2.2, (900 / max(dist, 60)) ** 0.35)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    r = np.hypot(xx - sx * w, yy - sy * h)
    fade = min(1.0, (dist / 120) ** 0.6)
    return (np.exp(-(r / (150 * k)) ** 2)[..., None] * np.array([255, 226, 180], np.float32) * 0.55 * fade
            + np.exp(-(r / (620 * k)) ** 1.4)[..., None] * np.array([40, 150, 190], np.float32) * 0.42 * fade)


def grab(pg):
    png = pg.screenshot(type='png')
    img = np.asarray(Image.open(io.BytesIO(png)).convert('RGB'), np.float32)
    return np.clip((img - GROUND) / (255 - GROUND) * 255, 0, 255)


def open_mock(p, w, h):
    b = p.chromium.launch(channel='chrome', args=['--enable-unsafe-webgpu', '--use-angle=d3d11', '--ignore-gpu-blocklist'])
    pg = b.new_page(viewport={'width': w, 'height': h}, device_scale_factor=1)
    pg.add_init_script(CLOCK)
    pg.goto(MOCK)
    pg.wait_for_function("() => !!(window.CO && CO.uv && CO.uv.camera) && CO.uv.frames > 40", timeout=120000)
    pg.add_style_tag(content=HIDE)
    pg.evaluate(SETUP)
    pg.evaluate(FRAMES_UP, 4)
    return b, pg


def frame(pg, plate, flight, name, f, T, phone):
    cam = camera_at(flight, f, phone)
    pg.evaluate("(T) => { window.__qT = T; }", T)
    pg.evaluate(FRAMES_UP, 1)                    # the stations step to time T first
    sx, sy, vis, dist = pg.evaluate(CAMERA, cam + [T])
    reveal = flight.get('reveal')
    wgt = 1.0 if not reveal else smooth((f - reveal[0]) / (reveal[1] - reveal[0]))
    if wgt < 1:
        pg.evaluate(UNIVERSE, False)
        pg.evaluate(FRAMES_UP, 2)
        sun_only = grab(pg)
        pg.evaluate(UNIVERSE, True)
    pg.evaluate(FRAMES_UP, 2)
    full = grab(pg)
    scene = full if wgt >= 1 else sun_only * (1 - wgt) + full * wgt
    h, w = scene.shape[:2]
    # the deep space drifts against the turn and grows a little as the camera comes in
    grow = 1.0 + 0.12 * (1 - min(1.0, math.log(max(dist, 40) / 40) / math.log(900 / 40)))
    plate_now = plate.view(grow, -math.sin(cam[4]) * 0.6, (cam[3] - 1.1) * 1.4)
    light = screen(scene, np.clip(sunlight(w, h, sx, sy, dist, vis), 0, 255))
    return Image.fromarray(np.clip(screen(plate_now, light), 0, 255).astype(np.uint8), 'RGB')


def render_set(p, set_name, mode):
    w, h = SETS[set_name]
    phone = set_name == 'mob'
    t0 = time.time()
    plate = Plate(w, h)
    print(f'{set_name}: nebula plate in {time.time() - t0:.0f}s')
    b, pg = open_mock(p, w, h)
    T0 = pg.evaluate("() => window.__qT")
    manifest = {}
    sheet = []
    for name, flight in FLIGHTS.items():
        n = flight['count']
        todo = [k[0] for k in flight['keys']] if mode == 'keys' else range(n)
        out = HERE / 'frames' / set_name / name
        out.mkdir(parents=True, exist_ok=True)
        pg.evaluate(PLATES, flight.get('plates', []))
        t1 = time.time()
        for f in todo:
            T = T0 + f * DT + {'approach': 0, 'casino': 4e5, 'promo': 4e5 + 89 * DT, 'pullback': 4e5 + 179 * DT}[name]
            img = frame(pg, plate, flight, name, f, T, phone)
            if mode == 'keys':
                sheet.append((f'{name} {f}', img))
            else:
                img.save(out / f'{f:04d}.webp', quality=84, method=4)
        if mode != 'keys':
            manifest[name] = {'count': n, 'w': w, 'h': h}
            print(f'{set_name}/{name}: {n} frames in {time.time() - t1:.0f}s')
    b.close()
    if mode == 'keys':
        cols = 4
        tw, th = w // 2, h // 2
        rows = (len(sheet) + cols - 1) // cols
        S = Image.new('RGB', (tw * cols, th * rows))
        for i, (_, im) in enumerate(sheet):
            S.paste(im.resize((tw, th)), ((i % cols) * tw, (i // cols) * th))
        (HERE / 'shots').mkdir(exist_ok=True)
        S.save(HERE / 'shots' / f'keys-{set_name}.png')
        print('->', HERE / 'shots' / f'keys-{set_name}.png', [s[0] for s in sheet])
        return
    # the posters: the chapter's own frame, saved as its still
    st = HERE / 'stills' / set_name
    st.mkdir(parents=True, exist_ok=True)
    for chapter, (seq, f) in POSTERS.items():
        Image.open(HERE / 'frames' / set_name / seq / f'{f:04d}.webp').save(st / f'{chapter}.webp', quality=82)
    mf = HERE / 'frames' / 'manifest.json'
    allm = json.loads(mf.read_text()) if mf.exists() else {}
    allm[set_name] = manifest
    mf.write_text(json.dumps(allm, indent=1))


OFFICE = """() => { const S = CO.S, deps = (S && S.departments) || [];
  return deps.map(d => ({ id: d.id, key: d.key, name: d.name })); }"""


def office(p, set_name):
    """Placeholders for the two office chapters until Antigravity's pictures come: the mock's own 3D office, aimed at
    the Development room (s2a) and the Quant Lab (s2b)."""
    w, h = SETS[set_name]
    b = p.chromium.launch(channel='chrome', args=['--enable-unsafe-webgpu', '--use-angle=d3d11', '--ignore-gpu-blocklist'])
    pg = b.new_page(viewport={'width': w, 'height': h})
    pg.add_init_script("localStorage.setItem('co.me.v1', JSON.stringify({ prebuild: 'starter' }));")
    pg.goto('http://127.0.0.1:8793/index.html?empty')
    pg.wait_for_function("() => !!(window.CO && CO.o3 && CO.S)", timeout=120000)
    time.sleep(6)
    deps = pg.evaluate(OFFICE)
    print('departments:', deps)
    st = HERE / 'stills' / set_name
    st.mkdir(parents=True, exist_ok=True)
    for still, pat in (('dev', 'develop'), ('lab', 'quant')):
        d = next((x for x in deps if pat in (str(x.get('key')) + str(x.get('name'))).lower()), None)
        if not d:
            print('no department like', pat)
            continue
        pg.evaluate("(k) => { CO.o3.focus(k, 0, true); CO.o3.moved = true; }", d['key'])
        time.sleep(2.5)
        box = pg.evaluate("() => { const r = CO.o3.renderer.domElement.getBoundingClientRect(); return [r.left, r.top, r.width, r.height]; }")
        png = pg.screenshot(type='png', clip={'x': box[0], 'y': box[1], 'width': box[2], 'height': box[3]})
        im = Image.open(io.BytesIO(png)).convert('RGB')
        k = max(w / im.width, h / im.height)
        im = im.resize((round(im.width * k), round(im.height * k)), Image.BICUBIC)
        l, t = (im.width - w) // 2, (im.height - h) // 2
        im.crop((l, t, l + w, t + h)).save(st / f'{still}.webp', quality=82)
        print('->', st / f'{still}.webp')
    b.close()


GEN = {'16x9': ('desk', (1920, 1080)), '9x16': ('mob', (1080, 1920))}


def gen():
    """Antigravity's pictures (gen/<slot>-16x9.png, -9x16.png; ANTIGRAVITY.md) into the page's stills: lab and dev stand
    under the two office chapters, casino and promo are cut in at the end of the Casino and Promo Market flights."""
    for src in sorted((HERE / 'gen').glob('*.png')):
        slot, _, shape = src.stem.rpartition('-')
        if shape not in GEN or slot not in ('lab', 'dev', 'casino', 'promo'):
            print('skipped', src.name)
            continue
        set_name, (w, h) = GEN[shape]
        im = Image.open(src).convert('RGB')
        k = max(w / im.width, h / im.height)
        im = im.resize((round(im.width * k), round(im.height * k)), Image.LANCZOS)
        l, t = (im.width - w) // 2, (im.height - h) // 2
        out = HERE / 'stills' / set_name / f'{slot}.webp'
        out.parent.mkdir(parents=True, exist_ok=True)
        im.crop((l, t, l + w, t + h)).save(out, quality=84)
        print(src.name, '->', out.relative_to(HERE))


if __name__ == '__main__':
    args = sys.argv[1:]
    mode = args[0] if args else 'keys'
    sets = [args[args.index('--set') + 1]] if '--set' in args else list(SETS)
    if mode == 'gen':
        gen()
        sys.exit(0)
    with sync_playwright() as p:
        for s in sets:
            if mode == 'office':
                office(p, s)
            else:
                render_set(p, s, mode)
