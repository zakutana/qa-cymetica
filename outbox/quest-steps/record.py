"""The clips for the Quest steps page, into clips/ (not in git: ~30 MB that record.py makes again), and a poster of
each into pics/ (kept: what the page shows before a clip plays, or if it is missing).

Fifth take (the operator, 2026-10-30): "v kazdem kroku musi byt top animace".

  clip              what moves                                              from
  office.webm       the whole HQ, its astronauts at work (step 1, a door)   LIVE builder, its Start, 1920 x 1080 laid out
  workshop.webm     the arms take the idea and build the product, 10 s      scenes/tools.html, frame by frame: a true loop
  promo-cube.webm   the Promo Market's cube turning, 18 s                   their page through our mirror, frame by frame
  farmer.webm       the Airdrop Farmer turning and blinking, the gem turning our Universe mock, a still camera (capture.py)
  lab.webm          the Quant Lab's five stages at their own pace, 23.6 s   outbox/quant-lab-v2, the window filmed
  universe.webm     the whole Universe: every company on its orbit          LIVE cymetica.com/company/app#universe (a door too)

  The office, the farmer and the Universe are filmed with their own skies hidden, on black: the page keys the black
  away (anim.js data-key), so they stand in its one space (thirteenth take). Fourteenth take: the office and the
  Universe drawn at 1.5 and cut to what the page shows (record(crop=), lit_box), then scaled to 1500 and 1600 wide; the
  Universe with its sun in the middle (UV_CENTER); the farmer and the gem on their lanes (FARMER_LANES), the map's arcs
  off; the workshop at 1920 x 1080. Fifteenth take: step 3 is market-orbit.webm and market-building.webm (market(),
  one camera, two layers); the farmer and the Promo Market cube clips are no longer on the page (EXTRA).

    python outbox/quest-steps/record.py                  # every one
    python outbox/quest-steps/record.py office farmer    # some

Real-time scenes are recorded where they are drawn: the canvas's own stream (captureStream) through MediaRecorder,
then remuxed by Playwright's own ffmpeg so the file knows its length (a MediaRecorder WebM does not, and a page
cannot cross-fade a clip whose length is Infinity). The workshop is drawn frame by frame and encoded by that ffmpeg.
Chrome with a real GPU, as capture.py. Live pages are read anonymously (GET, no cookies, no key); the builder is typed
into (a name) and never submitted.
"""
import base64
import glob
import io
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
import capture  # noqa: E402  (its server, its Universe and its farmer's composition)

HERE = Path(__file__).resolve().parent
CLIPS = HERE / 'clips'
W, H = 1440, 810
FFMPEG = (glob.glob(os.path.expandvars(r'%LOCALAPPDATA%\ms-playwright\ffmpeg-*\ffmpeg-win64.exe'))
          or glob.glob(os.path.expanduser('~/.cache/ms-playwright/ffmpeg-*/ffmpeg-linux')) or [None])[0]

# the canvas's own stream for `ms` milliseconds, as a WebM, back to Python in base64
RECORD = """async ([sel, ms, bps]) => {
  const c = document.querySelector(sel), s = c.captureStream(30);
  // VP8: Playwright's ffmpeg has no vp9_superframe filter, so a VP9 recording could not be remuxed to know its length
  const mime = 'video/webm;codecs=vp8';
  const rec = new MediaRecorder(s, { mimeType: mime, videoBitsPerSecond: bps }), parts = [];
  rec.ondataavailable = (e) => { if (e.data.size) parts.push(e.data); };
  const done = new Promise((r) => { rec.onstop = r; });
  rec.start(1000); await new Promise((r) => setTimeout(r, ms)); rec.stop(); await done;
  const buf = new Uint8Array(await new Blob(parts, { type: mime }).arrayBuffer());
  let bin = ''; for (let i = 0; i < buf.length; i += 0x8000) bin += String.fromCharCode.apply(null, buf.subarray(i, i + 0x8000));
  return { mime, w: c.width, h: c.height, b64: btoa(bin) }; }"""


def ffmpeg(*args, stdin=None):
    assert FFMPEG, "Playwright's ffmpeg is missing: python -m playwright install ffmpeg"
    subprocess.run([FFMPEG, '-hide_banner', '-loglevel', 'error', '-y', *args], input=stdin, check=True)


def record(page, sel, seconds, name, bps=8_000_000, crop=None, width=None):
    """the canvas `sel` for `seconds`, kept as clips/<name>.webm (remuxed, so it knows its length), and its first
    frame as pics/<name>.webp; with `crop` (x, y, w, h in the canvas's pixels) only that part, encoded again, so every
    pixel of the clip is one the page shows (fourteenth take: "headquarters mi prijde jeste trochu rozmazane")"""
    CLIPS.mkdir(exist_ok=True)
    r = page.evaluate(RECORD, [sel, int(seconds * 1000), bps])
    fd, tmp = tempfile.mkstemp(suffix='.webm')
    os.close(fd)
    raw = Path(tmp)
    raw.write_bytes(base64.b64decode(r['b64']))
    out = CLIPS / f'{name}.webm'
    if crop:
        x, y, w, h = crop
        ffmpeg('-i', str(raw), '-vf', f'crop={w}:{h}:{x}:{y}' + (f',scale={width}:-2:flags=lanczos' if width else ''), '-c:v', 'libvpx', '-b:v', '10M', '-crf', '5', '-qmin', '2', '-qmax', '24',
               '-auto-alt-ref', '0', '-g', '30', '-pix_fmt', 'yuv420p', str(out))
    else:
        ffmpeg('-i', str(raw), '-c', 'copy', str(out))
    raw.unlink()
    print(f'{out.name} {r["w"]}x{r["h"]}{" cropped to %dx%d" % crop[2:] if crop else ""} {r["mime"]} {out.stat().st_size // 1024} KB')
    return out


def lit_box(page, sel, margin, th=12):
    """what is lit in the canvas `sel` now (filmed on black), widened by `margin` of its size on every side, in even
    canvas pixels; and the canvas's size"""
    import numpy as np
    from PIL import ImageFilter
    data = page.evaluate("(sel) => document.querySelector(sel).toDataURL('image/png')", sel)
    im = Image.open(io.BytesIO(base64.b64decode(data.split(',', 1)[1]))).convert('L').filter(ImageFilter.MedianFilter(5))
    a = np.asarray(im, np.float32)
    ys, xs = np.nonzero(a > th)
    W_, H_ = a.shape[1], a.shape[0]
    x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
    mx, my = (x1 - x0) * margin, (y1 - y0) * margin
    x0, y0 = max(0, int(x0 - mx)) // 2 * 2, max(0, int(y0 - my)) // 2 * 2
    x1, y1 = min(W_, int(x1 + mx)), min(H_, int(y1 + my))
    return (x0, y0, (x1 - x0) // 2 * 2, (y1 - y0) // 2 * 2), (W_, H_)


def poster(page, sel, name):
    """what the canvas shows now, as the clip's poster"""
    data = page.evaluate("(sel) => document.querySelector(sel).toDataURL('image/jpeg', 0.92)", sel)
    img = Image.open(io.BytesIO(base64.b64decode(data.split(',', 1)[1]))).convert('RGB')
    capture.save(img, f'{name}.webp', quality=82)


def office(b, seconds=24, closer=1.0, dsf=1.5):
    """the live builder's Start in 3D at 1920 x 1080, drawn at `dsf` of it, its astronauts walking; twelfth take: the
    camera where the builder leaves it, the whole HQ in the picture with space round it ("proc ty headquarters mas
    useknute nahore a dole?", his picture of it whole); fourteenth take: drawn at 1.5 and cut to the HQ, so the page
    shows the HQ from about 1,500 of its own pixels, not the 800 it had ("jeste trochu rozmazane"). `closer` < 1 moves
    the camera in (the ninth take's 0.72 cut the rooms off)"""
    page = b.new_page(viewport={'width': 1920, 'height': 1080}, device_scale_factor=dsf)
    page.goto('https://cymetica.com/company/app/builder', wait_until='domcontentloaded', timeout=60000)
    time.sleep(12)
    page.fill('#f-name', 'Moonshot Labs')          # typed, never submitted
    page.click('#b-next')
    time.sleep(14)
    assert page.evaluate("() => document.getElementById('stage').classList.contains('is3d')"), 'the builder drew its flat office, not 3D'
    sel = '#office3d canvas'
    # the office's canvas runs wider than the stage (it is shifted right of the card): the page crops it to the stage,
    # by these numbers (quest.css #s1 .crop)
    print('office: canvas in the stage:', page.evaluate("""() => { const s = document.getElementById('stage').getBoundingClientRect(),
      c = document.querySelector('#office3d canvas').getBoundingClientRect(), k = document.querySelector('section.bz-card').getBoundingClientRect();
      const f = (v, d) => +(v / d * 100).toFixed(2);
      return { left: f(c.left - s.left, s.width), top: f(c.top - s.top, s.height), width: f(c.width, s.width), height: f(c.height, s.height),
               card: [f(k.left - s.left, s.width), f(k.top - s.top, s.height), f(k.width, s.width)] }; }"""))
    # thirteenth take: the HQ alone on black, its own sky gone (its stars and nebulae, office.sky; the rocks drifting
    # round it, office.drift), so the page keys the black away and the HQ stands in the page's own space ("pozadi za
    # headquarters je divne, ma byt stejne jako vsude jinde v questu"; anim.js .clip.key). The rock under it stays
    print('office: drift', page.evaluate("""() => { const o = CO.builder.office, sc = o.scene, hid = [];
      o.sky.visible = false;
      (o.drift || []).forEach((d) => { const m = d && d.isObject3D ? d : d && (d.m || d.mesh); if (m && m.isObject3D) { m.visible = false; hid.push(m.type); } });
      sc.background = new sc.background.constructor(0x000000); if (sc.fog) sc.fog.color.setHex(0x000000);
      return { hidden: hid.length, first: o.drift && o.drift[0] ? Object.keys(o.drift[0]).slice(0, 8) : null }; }"""))
    # sixteenth take's third round ("do vaultu dej penize hromadu"): the Vault's own piles (u3d.js piles(): ET10's green
    # bars and USDC's blue coins on pallets, whole near two million and a quarter of a million), in this browser only;
    # what it really holds, nothing, may not rebuild them while it is filmed
    print('office: vault', page.evaluate("""() => { const o = CO.builder.office, r = o.rooms.vault;
      o.piles(r, { et10: 2e6, usdc: 2.5e5 }, false); o.piles = function () {};
      return r.pileSet.all.map(im => im.visible); }"""))
    time.sleep(3)
    # the camera still (or in to `closer` of the way), its astronauts at work; the page plays from data-loop-from
    if closer != 1.0:
        page.evaluate("""(k) => { const o = CO.builder.office;
          const p0 = o.camera.position.clone(), t0 = o.controls.target.clone();
          o.tween(t0.clone().add(p0.clone().sub(t0).multiplyScalar(k)), t0, 3500); }""", closer)
    # the HQ's box (its plate, rooms and the rock under it), with room round it: the clip is that box alone, and the
    # page's crop is its shape (quest.css #s1 .crop)
    box, size = lit_box(page, sel, 0.05)
    print('office: canvas', size, 'the HQ', box, 'aspect', f'{box[2]} / {box[3]}')
    record(page, sel, seconds, 'office', bps=24_000_000, crop=box, width=1500)
    page.close()
    frame_poster('office', 5.0)


def frame_poster(name, at):
    """the clip's frame at `at` seconds as its poster"""
    fd, tmp = tempfile.mkstemp(suffix='.png')
    os.close(fd)
    ffmpeg('-ss', str(at), '-i', str(CLIPS / f'{name}.webm'), '-frames:v', '1', '-c:v', 'png', '-f', 'image2', tmp)
    capture.save(Image.open(tmp).convert('RGB'), f'{name}.webp', quality=82)
    Path(tmp).unlink()


# the Quant Lab at its own pace (ql.js BASE: BUILD 3.2, BLAST 4.4, BLIND 3.4, THE BAR 5.6, FOUND 7.0 s): twelfth take,
# "tu animaci musis zpomalit at je videt co se tam deje". The agent is revealed from 0.16 of FOUND on, so at LAB_BIRTH
# seconds into the clip; the page starts the clip that much before its reader is done reading (anim.js, data-birth)
LAB_STAGES, LAB_FOUND = 16.6, 7.0
LAB_BIRTH = round(LAB_STAGES + 0.16 * LAB_FOUND, 2)


# every CSS animation and transition held still and set to the clock's time, as it is first seen (the page's own clock
# is Playwright's below; a CSS one would run on in real time while each frame is photographed)
HOLD_CSS = """(vt) => { const seen = window.__seen || (window.__seen = new WeakMap());
  document.getAnimations().forEach(a => { if (!seen.has(a)) { seen.set(a, vt); a.pause(); } a.currentTime = (vt - seen.get(a)) * 1000; }); }"""


def lab(b, fps=30):
    """step 4: the Quant Lab's page in its Coming soon mode (outbox/quant-lab-v2, another session's page, served here
    and read only), whole from its heading to its reactor ("zobrazit celkove tu stranku i s tim nadpisem quant lab"):
    its five stages at their own pace, BUILD to FOUND, the agent born at LAB_BIRTH. Fourteenth take ("animace v quant
    labu se mi zda ze je takova sekana, mela by byt top plynula jak v nasi strance"): drawn frame by frame on
    Playwright's clock, `fps` a second, every frame a step of the same length (the window's own video was 25 a second,
    as its screencast delivered them); its canvas cannot be streamed (CoinGecko's logos taint it)"""
    vw, vh, total = 1400, 1100, LAB_STAGES + LAB_FOUND   # 1400 wide: its six score tiles stay one row
    page = b.new_page(viewport={'width': vw, 'height': vh}, device_scale_factor=1)
    page.clock.install()
    page.goto(capture.serve(capture.OUTBOX / 'quant-lab-v2') + '?mode=sim', wait_until='load', timeout=60000)
    page.wait_for_function("() => document.fonts.status === 'loaded' && document.querySelector('#rx').width > 0", timeout=60000)
    page.evaluate("() => document.querySelector('.q2-hero').scrollIntoView({ block: 'start' })")
    page.evaluate("() => window.scrollBy(0, -14)")
    time.sleep(3)
    r = page.evaluate("""() => { const a = document.querySelector('.q2-hero').getBoundingClientRect(), b = document.querySelector('.q2-reactor').getBoundingClientRect();
      return [Math.min(a.left, b.left) - 6, a.top - 10, Math.max(a.right, b.right) - Math.min(a.left, b.left) + 12, b.bottom - a.top + 12].map(Math.round); }""")
    x, y, w, h = r[0] // 2 * 2, r[1] // 2 * 2, r[2] // 2 * 2, r[3] // 2 * 2
    page.clock.pause_at(page.evaluate('Date.now()') + 200)
    page.evaluate("""() => document.querySelector('#rail [data-st="0"]').click()""")   # from the top: BUILD, at the clock's time
    frames, done = [], 0
    for i in range(int(round(total * fps))):
        page.evaluate(HOLD_CSS, i / fps)
        frames.append(page.screenshot(clip={'x': x, 'y': y, 'width': w, 'height': h}, type='jpeg', quality=93))
        step = round((i + 1) * 1000 / fps) - done
        page.clock.run_for(step)
        done += step
    page.close()
    CLIPS.mkdir(exist_ok=True)
    fd, tmp = tempfile.mkstemp(suffix='.mjpeg')
    os.close(fd)
    Path(tmp).write_bytes(b''.join(frames))
    ffmpeg('-f', 'image2pipe', '-c:v', 'mjpeg', '-framerate', str(fps), '-i', tmp, '-c:v', 'libvpx', '-b:v', '8M', '-crf', '6',
           '-qmin', '2', '-qmax', '28', '-auto-alt-ref', '0', '-g', str(fps), '-pix_fmt', 'yuv420p', str(CLIPS / 'lab.webm'))
    Path(tmp).unlink()
    print('lab: the page', w, 'x', h, len(frames), 'frames at', fps, 'a second, the agent born at', LAB_BIRTH, 's,',
          (CLIPS / 'lab.webm').stat().st_size // 1024, 'KB')
    frame_poster('lab', LAB_BIRTH + 2.0)        # the agent found


def doors(b, seconds=12):
    """the end's two calls as the LIVE start tutorial has them (cymetica.com/company/app/start, "udelej je tak jak to
    mame v start tutorialu, ale vylepsi je"): its two pictures, each drawn live by its engine, a room of the office
    turning and the Universe from above, recorded at twice their size"""
    page = b.new_page(viewport={'width': 1600, 'height': 1000}, device_scale_factor=2)
    page.goto('https://cymetica.com/company/app/start', wait_until='domcontentloaded', timeout=60000)
    page.wait_for_function("() => ['#lp-room', '#lp-uvpic'].every(s => document.querySelector(s + ' canvas'))", timeout=90000)
    time.sleep(10)
    for sel, name in (('#lp-room canvas', 'door-room'), ('#lp-uvpic canvas', 'door-universe')):
        poster(page, sel, name)
        record(page, sel, seconds, name)
    page.close()


# fourteenth take ("si nejak smazal ty obezne drahy na kterych jsou apky ve vesmiru ... jsou asi moc nahore"): the
# farmer and the gem each set on a lane of the map (laneDefs: the farmer on the third out, the gem on the second, a
# third of a radian on), the camera raised 0.55 rad over them and 9.5 farmer heights off (7 made them "moc velke na
# orbite"), so the lanes run round and under
# both instead of across the top of the picture; and the map's arcs off (u3d.js arc(): the streaks of work going in to
# Cymetica, which crossed the farmer: "co je to jako za animace nejakeho pruhu pres ty apky")
FARMER_LANES = """() => { const uv = CO.uv, V = uv.camera.position.constructor, up = new V(0, 1, 0);
  uv.arc = function () {}; (uv.arcs || []).forEach(a => { uv.scene.remove(a.head, a.streak); }); uv.arcs = [];
  const F = uv.items.find(x => x.c.id === 'ad-farmer'), G = uv.items.find(x => x.c.id === 'ad-gem');
  uv.items.forEach(x => { if (x !== F && x !== G && x.plot) x.plot.root.visible = false; });
  F.orbit = null; G.orbit = null; uv.follow = null; uv.controls.autoRotate = false;
  const f0 = F.plot.root.position.clone(), h = (F.plot.top - F.plot.bot) * F.plot.k, a0 = Math.atan2(f0.x, f0.z);
  const lanes = uv.laneDefs.map(l => l.r).sort((a, b) => a - b), el = 0.55, dist = 9.5, az = 1.25, ga = 0.32;
  const f = new V(Math.sin(a0) * lanes[2], f0.y, Math.cos(a0) * lanes[2]), g = new V(Math.sin(a0 + ga) * lanes[1], f0.y, Math.cos(a0 + ga) * lanes[1]);
  F.plot.root.position.copy(f); G.plot.root.position.copy(g);
  const out = new V(f.x, 0, f.z).normalize(), along = up.clone().cross(out).normalize();
  const T = f.clone().lerp(g, 0.45); T.y += h * 0.3;
  const dir = out.clone().multiplyScalar(Math.cos(az)).addScaledVector(along, -Math.sin(az)).multiplyScalar(Math.cos(el)).addScaledVector(up, Math.sin(el));
  [F, G].forEach(x => { x.anchor.set(x.plot.root.position.x, x.plot.root.position.y + (x.plot.top + 0.5) * (x.plot.k || 1), x.plot.root.position.z); if (x.el) x.el.classList.add('keep'); });
  uv.tween(T.clone().addScaledVector(dir, h * dist), T, 0); }"""


def farmer(b, seconds=12):
    """our Universe mock, the farmer and the gem on their lanes (FARMER_LANES), the camera still while the farmer turns
    and blinks and the gem turns; where the two names stand, for the page's own labels over the clip"""
    page = capture.universe(b, viewport={'width': 1600, 'height': 1000}, dsf=1.25)
    page.evaluate(FARMER_LANES)
    # thirteenth take: its sky hidden, on black, keyed by the page (anim.js data-key) as the HQ and the Universe are
    page.evaluate("() => { const o = CO.uv; if (o.sky) o.sky.visible = false; o.scene.background = new o.scene.background.constructor(0x000000); }")
    time.sleep(3)
    sel = '#uv3d canvas'
    print('farmer: names over the canvas (left, top %):', page.evaluate("""() => { const c = document.querySelector('#uv3d canvas').getBoundingClientRect();
      return ['ad-farmer', 'ad-gem'].map(id => { const e = CO.uv.items.find(x => x.c.id === id).el.getBoundingClientRect();
        return [id, +((e.left + e.width / 2 - c.left) / c.width * 100).toFixed(1), +((e.top - c.top) / c.height * 100).toFixed(1)]; }); }"""))
    poster(page, sel, 'farmer')
    record(page, sel, seconds, 'farmer', bps=16_000_000)
    page.close()


# fifteenth take, step 3 (the operator, on Gemini's fork of this page, 2026-10-31: "vyhodil bych proste ten screen ze
# stranky a nechal bych jen orbitu, v popredi bude velka budova Promo marketu co mame ve vesmiru a nad ni bude ta krychle
# ... a pridat i dozadu nekde agent casino na orbitu"): the farmer and the gem on their lanes as FARMER_LANES has them,
# the camera further back so they read smaller, the Agent Casino further along the outer lane, and our Universe's Promo
# Market (u3d.js adPromo) big in front on the right, its own hologram away (everything over the projector's lens: the
# page sets the Promo Market's live cube there), its ticker band without its figure (that reads ../promo-market/data.js,
# which this server does not serve, so it said 0 UP FOR GRABS)
# Its second round ("step 3 tam mas nejake divne slunce, to smaz a chybi ti vzducholod kolem promo marketu"): the sun
# (u3d.js core(), coreG) hidden; the PROMO airship back, circling it; the building's clip one whole lap of the airship
# long (`lap` s, 80 in the Universe: a 12 s clip would have jumped it back a sixth of a lap at every loop), and so
# everything of the building seamless at that length: its rings turned whole quarters, its band a whole width, its bob
# twice, its slow turn held still, its own clock run at `tsc` so the billboard's magenta and amber come round 4 times
# Sixteenth take's third round ("gem screener posun trosku dozadu a doleva at ho neprekryva napis od airdrop farmera"):
# the gem on the lane inside and further round it (gl, gx), the camera still aimed by where it stood (ga), so nothing else moves
# Fourth round ("dej jeste mozne ze 4 tyto open slot ikonky at je viditelne ze se daji kupovat landy, treba 1 dopredu a 2
# dozadu"): free slots of the map's own on the lanes, [lane, angle], one in front and three behind. And the box pinned, as
# every plate and outline on the page stands in % of it
MARKET = dict(box=(0, 36, 1946, 1044), slots=[[1, -0.2], [2, 1.0], [1, 1.6], [3, 1.4]], ga=0.32, gl=0, gx=0.5, cl=3, ca=0.75, az=1.25, el=0.55, dist=13.0, ty=0.3, pk=0.2, pr=3.0, ps=2.8, lap=30.0, tsc=28 / 30,
              pan=1.0)   # the airship's hull, measured over a lap: 58 to 92 % of the canvas across (at 0: 70 to 104)
MARKET_SETUP = """(o) => { const uv = CO.uv, V = uv.camera.position.constructor, up = new V(0, 1, 0);
  uv.arc = function () {}; (uv.arcs || []).forEach(a => { uv.scene.remove(a.head, a.streak); }); uv.arcs = [];
  const by = id => uv.items.find(x => x.c.id === id);
  const F = by('ad-farmer'), G = by('ad-gem'), C = by('ad-casino'), P = by('ad-promo');
  uv.items.forEach(x => { if (![F, G, C, P].includes(x) && x.plot) x.plot.root.visible = false; });
  [F, G, C, P].forEach(x => { x.orbit = null; });
  uv.follow = null; uv.controls.autoRotate = false;
  const f0 = F.plot.root.position.clone(), h = (F.plot.top - F.plot.bot) * F.plot.k, a0 = Math.atan2(f0.x, f0.z);
  const lanes = uv.laneDefs.map(l => l.r).sort((a, b) => a - b);
  const at = (lane, a) => new V(Math.sin(a) * lanes[lane], f0.y, Math.cos(a) * lanes[lane]);
  const f = at(2, a0), g = at(1, a0 + o.ga);
  F.plot.root.position.copy(f); G.plot.root.position.copy(at(o.gl, a0 + o.gx)); C.plot.root.position.copy(at(o.cl, a0 + o.ca));
  const free = uv.items.filter(x => x.kind === 'slot' && !x.owned && x.plot); uv.landShow = function () {};
  window.__slots = o.slots.map(([l, g], i) => { const it = free[i]; it.orbit = null; it.plot.root.visible = true; it.plot.root.position.copy(at(l, a0 + g)); return it.plot.root; });
  const out = new V(f.x, 0, f.z).normalize(), along = up.clone().cross(out).normalize();
  const T = f.clone().lerp(g, 0.45); T.y += h * o.ty;
  const dir = out.clone().multiplyScalar(Math.cos(o.az)).addScaledVector(along, -Math.sin(o.az)).multiplyScalar(Math.cos(o.el)).addScaledVector(up, Math.sin(o.el));
  const cam = T.clone().addScaledVector(dir, h * o.dist), right = dir.clone().cross(up).normalize().negate();
  const p = T.clone().lerp(cam, o.pk).addScaledVector(right, h * o.pr); p.y = f0.y;
  P.plot.root.position.copy(p); P.plot.root.scale.multiplyScalar(o.ps);
  P.plot.root.traverse(n => { if (n.isGroup && Math.abs(n.scale.x - 0.85) < 1e-3 && n.children.length > 20) window.__st = n; });
  const st = window.__st, airship = st.children.find(ch => ch.isGroup && Math.abs(ch.position.y - 7.65) < 0.02);
  st.children.forEach(ch => { if (ch !== airship && (ch.isPoints || ch.isSprite || ch.position.y > 5.85)) ch.visible = false; });
  const rings = st.children.filter(ch => ch.isGroup && [3.05, 4.1].some(y => Math.abs(ch.position.y - y) < 0.01));
  const b = P.plot.b, tick0 = b.tick, L = o.lap, body = P.plot.body;
  Object.defineProperty(body.rotation, 'y', { get() { return this._y; }, set() {} });
  let bob = 0; Object.defineProperty(body.position, 'y', { get() { return bob; }, set() {} });
  b.tick = (t) => { tick0(t * o.tsc); const w = 2 * Math.PI * t / L;
    airship.rotation.y = w; rings[0].rotation.y = Math.PI / 2 * 6 * t / L; rings[1].rotation.y = -Math.PI / 2 * 8 * t / L;
    window.__band.material.map.offset.x = -t / L; bob = Math.sin(2 * w) * 0.22; };
  if (uv.coreG) uv.coreG.visible = false;
  st.children.forEach(ch => { const gp = ch.geometry && ch.geometry.parameters; if (gp && gp.openEnded && Math.abs(gp.radiusTop - 1.6) < 1e-6) window.__band = ch; });
  const tex = window.__band.material.map, cv = tex.image, g2 = cv.getContext('2d'), H = cv.height;
  g2.clearRect(0, 0, cv.width, H); g2.font = '800 40px "JetBrains Mono", monospace'; g2.textBaseline = 'middle';
  let x = 24; [['EARN USDC', '#00cfff'], ['PROMOTE YOUR PRODUCT', '#e6edf7'], ['GET USERS', '#00cfff'], ['PROMO MARKET', '#e6edf7']].forEach(([t, col]) => {
    g2.fillStyle = col; g2.fillText(t, x, H / 2 + 2); x += g2.measureText(t).width + 30; g2.fillStyle = '#00cfff'; g2.fillRect(x - 20, H / 2 - 4, 8, 8); x += 14; });
  g2.fillStyle = 'rgba(0,207,255,.6)'; g2.fillRect(0, 4, cv.width, 3); g2.fillRect(0, H - 7, cv.width, 3); tex.needsUpdate = true;
  [F, G, C, P].forEach(x => { x.anchor.set(x.plot.root.position.x, x.plot.root.position.y + (x.plot.top + 0.5) * (x.plot.k || 1) * (x === P ? o.ps : 1), x.plot.root.position.z); });
  // the picture panned right (the scene left), so the airship's lap on the far side stays in it
  T.addScaledVector(right, h * o.pan); cam.addScaledVector(right, h * o.pan);
  uv.tween(cam, T, 0);
  if (uv.sky) uv.sky.visible = false; uv.scene.background = new uv.scene.background.constructor(0x000000); }"""
# where the projector's lens and the three products' names stand, in % of the canvas
MARKET_WHERE = """() => { const uv = CO.uv, cam = uv.camera, V = cam.position.constructor, c = document.querySelector('#uv3d canvas');
  const pr = (v) => { const p = v.clone().project(cam); return [(p.x + 1) / 2 * c.width, (1 - p.y) / 2 * c.height]; };
  const lens = new V(0, 5.7, 0); window.__st.localToWorld(lens); const out = { lens: pr(lens) };
  ['ad-farmer', 'ad-gem', 'ad-casino', 'ad-promo'].forEach(id => { out[id] = pr(uv.items.find(x => x.c.id === id).anchor); });
  return out; }"""


def market_box(page, sel):
    """the box both of step 3's clips are cut to: what was lit, to the canvas's right edge (what is lit leaves out the
    airship's far side), pinned; and the canvas's size, which it was measured on"""
    _, size = lit_box(page, sel, 0.03)
    assert size == (1947, 1081), size
    return MARKET['box'], size


def market(b, seconds=12):
    """step 3: two clips of one camera (MARKET), cut to the same box: the orbit (its lanes, the farmer, the gem and the
    Agent Casino; keyed as light, data-key="glow", the lanes being 2 to 7 % bright), `seconds` long, and the Promo
    Market with its airship alone (keyed hard as the HQ is: under the glow key its dark metal would let the sky
    through), one lap of the airship long"""
    page = capture.universe(b, viewport={'width': 1600, 'height': 1000}, dsf=1.25)
    page.evaluate(MARKET_SETUP, MARKET)
    time.sleep(3)
    sel = '#uv3d canvas'
    box, size = market_box(page, sel)
    x, y, w, h = box
    pct = lambda pt: (round((pt[0] - x) / w * 100, 1), round((pt[1] - y) / h * 100, 1))
    print('market: canvas', size, 'box', box, 'aspect', f'{w} / {h}',
          {k: pct(v) for k, v in page.evaluate(MARKET_WHERE).items()}, '(% of the clip)')
    by = "(id) => CO.uv.items.find(x => x.c.id === id).plot.root"
    page.evaluate(f"() => {{ ({by})('ad-promo').visible = false; }}")
    # the page's first recording stands still for half a second a third of a second in (0.56, 0.56 and, after four
    # seconds' rest, 0.46 s; the second recording never did): a second's recording first, thrown away
    time.sleep(1)
    page.evaluate(RECORD, [sel, 1000, 4_000_000])
    record(page, sel, seconds, 'market-orbit', bps=16_000_000, crop=box)
    page.evaluate(f"() => {{ const r = {by}; ['ad-farmer', 'ad-gem', 'ad-casino'].forEach(id => {{ r(id).visible = false; }}); window.__slots.forEach(s => {{ s.visible = false; }}); r('ad-promo').visible = true; }}")
    page.evaluate(capture.HIDE_SKY)
    time.sleep(1)
    record(page, sel, MARKET['lap'], 'market-building', bps=16_000_000, crop=box)
    page.close()
    frame_poster('market-orbit', 1.0)
    frame_poster('market-building', 1.0)


# sixteenth take's third round ("na kazde kdyz najede nekdo mysi tak se highlightuje ... ty highlighy zkus udelat tim
# zelenym ze budou obramovane ale at to vypada top"; a line drawn live round whatever was lit in the clip came out
# jagged and ran inside the gem, along the lanes and round the building's every ring), and its fourth ("animace highlihtu
# maji byt jen po obvodu a mas tam bugy a klidne trosku tensi to obramovani": a line with a glow outside it left the
# inside black, and it ran round the bloom and the halos, in bubbles round nothing): each product alone on black, no
# bloom, no sprite, no additive light, so only what is solid; everything of it over a whole bob of the building as one
# shape with its holes filled; round that shape one line, an SVG path in outlines.js, which the page lights under the
# pointer and runs a light along. The airship goes its own way, so the Promo Market's shape is without it
# name: its item, how lit counts, its lights kept (the casino's little hologram over it is light), thin things taken off
# in pixels (the building's two lamp posts stuck out of its line as spikes).
# And its fifth ("porad mas to obramovani proste blbe, jen u agent casina je to dobre"): the casino hardly moves and its
# shape had all its lights in it; the gem bobs, the farmer rocks and the Promo Market's ring of words was left out, so the
# object crossed a line that lay tight on one moment of it. So each is now a sticker's edge: everything the eye sees of it
# (only particles and soft sprites off) over the whole of its motion, its waists and notches closed to a radius, stood a
# little off it, rounded. The casino's path is kept as it was filmed
# name: its item, the radius its notches are closed to, how far the line stands off it, how far its corners are rounded
OUTLINED = {'gem': ('ad-gem', 22, 5, 5), 'farmer': ('ad-farmer', 26, 5, 5), 'promo': ('ad-promo', 64, 6, 7)}
MATTE = """(ids) => { const uv = CO.uv; uv.post = null;
  ids.forEach(id => { uv.items.find(x => x.c.id === id).plot.root.traverse(n => { if (n.isPoints || n.isSprite) n.visible = false; }); });
  window.__slots.forEach(s => { s.visible = false; });
  window.__st.children.forEach(ch => { if (ch.isGroup && Math.abs(ch.position.y - 7.65) < 0.02) ch.visible = false; }); }"""


def contour(solid, every=5):
    """round the edge of a bool mask: SVG path data in its pixels, each loop smoothed and thinned to a point in `every`"""
    import numpy as np
    a = np.pad(solid, 1)
    ahead = {}
    for y, x in zip(*np.nonzero(a)):
        if not a[y - 1, x]:
            ahead.setdefault((x, y), []).append((x + 1, y))
        if not a[y, x + 1]:
            ahead.setdefault((x + 1, y), []).append((x + 1, y + 1))
        if not a[y + 1, x]:
            ahead.setdefault((x + 1, y + 1), []).append((x, y + 1))
        if not a[y, x - 1]:
            ahead.setdefault((x, y + 1), []).append((x, y))
    out = []
    while ahead:
        start = next(iter(ahead))
        pts, at = [], start
        while at in ahead:
            pts.append(at)
            ends = ahead[at]
            to = ends.pop()
            if not ends:
                del ahead[at]
            at = to
        if len(pts) < 60:
            continue
        p = np.array(pts, np.float32) - 1
        k = np.ones(9) / 9
        xs = np.convolve(np.r_[p[-4:, 0], p[:, 0], p[:4, 0]], k, 'valid')
        ys = np.convolve(np.r_[p[-4:, 1], p[:, 1], p[:4, 1]], k, 'valid')
        out.append('M' + 'L'.join(f'{u:.1f} {v:.1f}' for u, v in zip(xs[::every], ys[::every])) + 'Z')
    return ''.join(out)


def grown(a, r):
    """a bool mask grown by a disc of radius r"""
    import numpy as np
    yy, xx = np.ogrid[-r:r + 1, -r:r + 1]
    k = np.zeros(a.shape)
    k[:2 * r + 1, :2 * r + 1] = yy * yy + xx * xx <= r * r
    k = np.roll(k, (-r, -r), (0, 1))
    return np.fft.irfft2(np.fft.rfft2(a.astype(float)) * np.fft.rfft2(k), a.shape) > 0.5


def outline_of(lit, close, off, blur):
    """a lit mask (bool array, the clip's size): its shape with its waists and notches closed to radius `close`, stood
    `off` pixels off the object, holes filled, corners rounded by `blur`"""
    import numpy as np
    from PIL import ImageDraw, ImageFilter
    a = grown(~grown(~grown(lit, close), close), off)
    im = Image.fromarray((a * 255).astype(np.uint8))
    pad = Image.new('L', (im.width + 2, im.height + 2), 0)
    pad.paste(im, (1, 1))
    ImageDraw.floodfill(pad, (0, 0), 128)
    solid = np.asarray(pad)[1:-1, 1:-1] != 128
    return np.asarray(Image.fromarray((solid * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(blur)), np.float32) / 255 > 0.5


def outlines(b, frames=26, look=None):
    """outlines.js: the path round each of OUTLINED, in the clip's pixels; and each shape's box (its .hot in index.html),
    in % of the clip. The casino's stays as outlines.js has it. `look`: a folder for each shape's mask"""
    import json
    import re
    import numpy as np
    page = capture.universe(b, viewport={'width': 1600, 'height': 1000}, dsf=1.25)
    page.evaluate(MARKET_SETUP, MARKET)
    time.sleep(3)
    sel = '#uv3d canvas'
    (x, y, w, h), _ = market_box(page, sel)
    page.evaluate(capture.HIDE_SKY)
    items = [v[0] for v in OUTLINED.values()] + ['ad-casino']
    page.evaluate(MATTE, items)
    by = "(id) => CO.uv.items.find(x => x.c.id === id).plot.root"
    paths = {'w': w, 'h': h, 'casino': json.loads(re.search(r'QUEST_OUTLINES = (\{.*\});', (capture.HERE / 'outlines.js').read_text(encoding='utf-8'), re.S).group(1))['casino']}
    for name, (item, close, off, blur) in OUTLINED.items():
        page.evaluate(f"(me) => {{ const r = {by}; {items}.forEach(id => {{ r(id).visible = id === me; }}); }}", item)
        time.sleep(1)
        lit = np.zeros((h, w), bool)
        for _ in range(frames):        # the building's bob comes round in 15 s, the farmer's rock is slower than its bob
            data = page.evaluate("(sel) => document.querySelector(sel).toDataURL('image/png')", sel)
            im = Image.open(io.BytesIO(base64.b64decode(data.split(',', 1)[1]))).convert('RGB').crop((x, y, x + w, y + h))
            lit |= np.asarray(im, np.uint8).max(axis=2) > 24
            time.sleep(0.9)
        solid = outline_of(lit, close, off, blur)
        if look:
            Image.fromarray((solid * 255).astype(np.uint8)).save(Path(look) / f'matte-{name}.png')
        paths[name] = contour(solid)
        ys, xs = np.nonzero(solid)
        p = lambda v, d: round(v / d * 100, 2)
        print(f'{name}: path {len(paths[name]) // 1024} KB',
              f'| hot left: {p(xs.min(), w)}%; top: {p(ys.min(), h)}%; width: {p(xs.max() - xs.min(), w)}%; height: {p(ys.max() - ys.min(), h)}%')
    page.close()
    (capture.HERE / 'outlines.js').write_text('/* record.py outlines: the line round each of step 3\'s products, in the clip\'s pixels */\nwindow.QUEST_OUTLINES = ' + json.dumps(paths) + ';\n', encoding='utf-8')


# step 5's Universe has six companies today; the leaderboard beside it names five more, so they are given a station
# each on the map too ("v univerzu jeste pridej par firem navic"): QUEST.board's, with the stations its marks show, and
# three more. Only our recording browser sees them (record.py universe): nothing is sent anywhere.
EXTRA_COMPANIES = [('Giga Fund', 'vault', 'red'), ('Bull Club', 'pyramid', 'red'), ('Sigma Collective', 'tower', 'blue'),
                   ('Quasar Fund', 'dome', 'green'), ('Vector Trading', 'tower', 'cyan'), ('Your company', 'orbital', 'gold'),
                   ('Helix Partners', 'rift', 'purple'), ('Orbit Ventures', 'vortex', 'pink')]

# sixteenth take ("zajisti aby na sobe nebyly 2 lode moc blizko nikde a nad nejakou lod dej tag YOUR COMPANY"): before
# the recording every company is turned along its own lane, the least it takes, until each one is UV_SPACE times its
# own and its neighbour's half-width from every other ship and product, now and through the clip (the products stay
# where the live map has them). Yours is put first, held still (w 0) nearest UV_YOU_AT of the canvas, so the page's
# tag (index.html .you-tag) stands over it the whole clip; its top is returned for that
UV_SPACE, UV_YOU_AT = 2.4, (0.29, 0.64)   # the map's left, clear of the leaderboard down to a 1440 px screen
UV_SPREAD = """([you, target, T, K]) => { const o = CO.uv, cam = o.camera, V = cam.position.constructor, el = o.renderer.domElement;
  const W = el.clientWidth, H = el.clientHeight, right = new V().setFromMatrixColumn(cam.matrixWorld, 0);
  const all = o.items.filter(it => (!it.kind || it.kind === 'product') && it.plot && it.plot.root.visible && it.orbit);
  // where each one is now: its orbit's a is where it started, the clock has turned it on since (by w a second)
  all.forEach(it => { const p = it.plot.root.position; it.__th = Math.atan2(p.x, p.z); });
  const at = (it, th, h) => { const p = it.plot.root.parent.localToWorld(new V(it.orbit.r * Math.sin(th), it.size * (h || 0.45), it.orbit.r * Math.cos(th)));
    const s = p.clone().project(cam), e = p.clone().addScaledVector(right, it.size * 0.5).project(cam);
    return { x: (s.x + 1) / 2 * W, y: (1 - s.y) / 2 * H, rad: Math.hypot((e.x - s.x) / 2 * W, (e.y - s.y) / 2 * H) }; };
  const ends = (it, th, w) => [at(it, th), at(it, th + w * T / 2), at(it, th + w * T)];
  const placed = [], step = Math.PI * 2 / 180, log = [];
  const room = (pts) => Math.min(Infinity, ...placed.flatMap(q => pts.map((p, k) => Math.hypot(p.x - q.pts[k].x, p.y - q.pts[k].y) / (p.rad + q.pts[k].rad))));
  // stands at th now and turns on at w: its start moved by as much as it is moved now; w 0 holds it where it is put
  const put = (it, th, w) => { it.orbit.a = w ? it.orbit.a + (th - it.__th) : th; it.orbit.w = w; placed.push({ it, th, pts: ends(it, th, w) }); };
  const name = it => it.c.name || it.c.title, me = all.find(it => !it.kind && name(it) === you);
  all.filter(it => it.kind === 'product').forEach(it => put(it, it.__th, it.orbit.w));
  if (me) { let best = null;
    for (let k = 0; k < 180; k++) { const th = k * step, p = at(me, th), d = Math.hypot(p.x / W - target[0], p.y / H - target[1]);
      if (room([p, p, p]) >= K && (!best || d < best.d)) best = { th, d }; }
    put(me, best ? best.th : me.__th, 0);
    // the page's tag over it is in the way too: a ship as wide as the tag, where the tag stands
    const tag = Object.assign(at(me, placed[placed.length - 1].th, 2.4), { rad: 70 }); placed.push({ it: me, pts: [tag, tag, tag] }); }
  all.filter(it => !it.kind && it !== me).sort((a, b) => (a.c.id >= 90000) - (b.c.id >= 90000)).forEach(it => {
    const th0 = it.__th, w = it.orbit.w; let best = null;
    for (let k = 0; k < 180; k++) { const d = (k % 2 ? 1 : -1) * Math.ceil(k / 2) * step, r = room(ends(it, th0 + d, w));
      if (r >= K) { best = { th: th0 + d, r }; break; } if (!best || r > best.r) best = { th: th0 + d, r }; }
    if (best.th !== th0) log.push(name(it) + ' ' + (best.th - th0).toFixed(2) + ' rad'); put(it, best.th, w); });
  let worst = [Infinity];
  placed.forEach((q, i) => placed.forEach((u, j) => { if (j > i && q.it !== u.it) {
    const r = Math.min(...q.pts.map((p, k) => Math.hypot(p.x - u.pts[k].x, p.y - u.pts[k].y) / (p.rad + u.pts[k].rad)));
    if (r < worst[0]) worst = [r, name(q.it) + (q.pts[0].rad === 70 ? "'s tag" : ''), name(u.it) + (u.pts[0].rad === 70 ? "'s tag" : '')]; } }));
  const mine = me && placed.find(q => q.it === me), top = mine && at(me, mine.th, 1.2);
  return { moved: log, closest: [+worst[0].toFixed(2), worst[1], worst[2]], you: mine && [top.x / W, top.y / H] }; }"""


# fourteenth take ("si uplne znicil tu obeznou drahu ... ma byt vetsi mnohem ten vesmir a ta tabule v nem jakoby
# mensi, podobne jak to je v live aplikaci"): the camera moved sideways so the sun stands in the middle (the live map
# keeps it right of its own board) and back by UV_BACK, so the whole outer lane is in the picture with room round it,
# the sun a little above the middle (UV_UP of the picture's height) as the lanes' near side is the bigger
UV_BACK, UV_UP = 1.4, -0.07
UV_CENTER = """([k, dy]) => { const o = CO.uv, cam = o.camera, t = o.controls.target, V = cam.position.constructor;
  const p = o.heartAt.clone().project(cam);
  const d = cam.position.distanceTo(o.heartAt), h = 2 * d * Math.tan(cam.fov * Math.PI / 360), w = h * cam.aspect;
  const right = new V().setFromMatrixColumn(cam.matrixWorld, 0), up = new V().setFromMatrixColumn(cam.matrixWorld, 1);
  const shift = right.multiplyScalar(p.x * w / 2).add(up.multiplyScalar(p.y * h / 2 + h * dy));
  const nt = t.clone().add(shift), np = cam.position.clone().add(shift);
  o.tween(np.clone().sub(nt).multiplyScalar(k).add(nt), nt, 0); }"""


def universe(b, seconds=20, dsf=1.5):
    """step 5: the LIVE Universe (cymetica.com/company/app#universe), its sky, its sun, its real companies and products
    on its orbits ("v univerzu je pozadi mnohem lepe udelane") and, in our browser only, the leaderboard's companies
    beside them (EXTRA_COMPANIES, added to its /universe answer as it arrives); the camera still, the whole map in the
    middle (UV_CENTER), drawn at `dsf` and cut to the map. Its map idles after 1.5 s without input, so it is poked
    awake every 0.8 s."""
    page = b.new_page(viewport={'width': 1920, 'height': 1080}, device_scale_factor=dsf)

    def more(route):
        resp = route.fetch()
        j = resp.json()
        j['companies'] = (j.get('companies') or []) + [
            {'id': 90001 + i, 'name': n, 'owner': 'sample', 'public': True, 'status': 'active', 'skin': s, 'accent': a, 'mission': '',
             'days': 20 + 3 * i, 'departments': 4, 'working': 1 if i % 2 else 0, 'mine': False} for i, (n, s, a) in enumerate(EXTRA_COMPANIES)]
        route.fulfill(response=resp, json=j)
    page.route('**/api/v1/company/universe*', more)
    page.goto('https://cymetica.com/company/app#universe', wait_until='domcontentloaded', timeout=60000)
    page.wait_for_function("() => window.CO && CO.uv && CO.uv.camera && CO.uv.items && CO.uv.items.length", timeout=90000)
    time.sleep(8)
    page.evaluate("() => { setInterval(() => { CO.uv.lastInput = performance.now(); }, 800); }")
    # thirteenth take: its own sky hidden (CO.uv.sky: its stars and nebulae), on black, so the page keys the black away
    # and the Universe stands in the page's own space as the HQ does (anim.js data-key), its orbits' dust kept
    page.evaluate("() => { const o = CO.uv; o.sky.visible = false; o.scene.background = new o.scene.background.constructor(0x000000); }")
    page.evaluate(UV_CENTER, [UV_BACK, UV_UP])
    time.sleep(2.5)
    spread = page.evaluate(UV_SPREAD, ['Your company', list(UV_YOU_AT), seconds + 2, UV_SPACE])
    print('universe: moved along their lanes', spread['moved'], 'the closest two', spread['closest'], 'half-widths apart')
    time.sleep(1.5)
    sel = '#uv3d canvas'
    print('universe (live): companies', page.evaluate("() => CO.uv.items.filter(it => !it.kind).length"),
          'products', page.evaluate("() => CO.uv.items.filter(it => it.kind === 'product').length"))
    box, size = lit_box(page, sel, 0.035)
    sun = page.evaluate("""() => { const p = CO.uv.heartAt.clone().project(CO.uv.camera); return [(p.x + 1) / 2, (1 - p.y) / 2]; }""")
    x, y, w, h = box
    pct = lambda pt: (round((pt[0] * size[0] - x) / w * 100, 2), round((pt[1] * size[1] - y) / h * 100, 2))
    print('universe: canvas', size, 'the map', box, 'aspect', f'{w} / {h}', 'the sun at (% of the clip)', pct(sun),
          'over your company', spread['you'] and pct(spread['you']))
    record(page, sel, seconds, 'universe', bps=24_000_000, crop=box, width=1600)
    page.close()
    frame_poster('universe', 1.0)


def universe_mock(b, seconds=20, keep=18):
    """(the eighth take's step 5) the Universe with more companies than the live one has: our mock's
    (outbox/company-live), its sample companies spread over its orbits, `keep` of them and its products; where its sun
    stands on the canvas is printed, for the page's own sun over it"""
    page = capture.universe(b, viewport={'width': 1920, 'height': 1080}, dsf=0.75)
    page.evaluate("""(keep) => { const cos = CO.uv.items.filter(it => !it.kind && it.plot), step = cos.length / keep;
      cos.forEach((it, i) => { it.plot.root.visible = Math.floor(i / step) * step <= i && i - Math.floor(i / step) * step < 1; }); }""", keep)
    time.sleep(2)
    sel = '#uv3d canvas'
    print('universe: companies shown', page.evaluate("() => CO.uv.items.filter(it => !it.kind && it.plot && it.plot.root.visible).length"),
          'sun at (% of the canvas)', page.evaluate("""() => { const p = CO.uv.heartAt.clone().project(CO.uv.camera);
            return [+((p.x + 1) / 2 * 100).toFixed(1), +((1 - p.y) / 2 * 100).toFixed(1)]; }"""))
    poster(page, sel, 'universe')
    record(page, sel, seconds, 'universe')
    page.close()


def workshop(b, fps=30, at=None, W=1920, H=1080):
    """scenes/tools.html drawn frame by frame through its PERIOD (render(t) is a function of t alone, so the last frame
    leads into the first), encoded to VP8 by Playwright's ffmpeg; `at` (seconds) only pictures those moments.
    Fourteenth take ("build it better taky [rozmazane]"): 1920 x 1080, for a picture drawn about 1,050 wide"""
    base = capture.serve(HERE)
    page = b.new_page(viewport={'width': W, 'height': H})
    page.goto(base + f'scenes/tools.html?w={W}&h={H}&frames', wait_until='load', timeout=60000)
    page.wait_for_function('window.READY === true', timeout=60000)
    grab = "(t) => { window.render(t); return document.querySelector('canvas').toDataURL('image/jpeg', 0.95); }"
    if at:
        for t in at:
            Image.open(io.BytesIO(base64.b64decode(page.evaluate(grab, t).split(',', 1)[1]))).save(HERE / f'workshop-{t}.png')
        page.close()
        return
    period = page.evaluate('window.PERIOD')
    frames = [base64.b64decode(page.evaluate(grab, i / fps).split(',', 1)[1]) for i in range(int(period * fps))]
    CLIPS.mkdir(exist_ok=True)
    out = CLIPS / 'workshop.webm'
    # Playwright's ffmpeg has no pipe protocol: the frames go through a file of JPEGs one after another
    fd, tmp = tempfile.mkstemp(suffix='.mjpeg')
    os.close(fd)
    Path(tmp).write_bytes(b''.join(frames))
    ffmpeg('-f', 'image2pipe', '-c:v', 'mjpeg', '-framerate', str(fps), '-i', tmp, '-c:v', 'libvpx', '-b:v', '14M', '-crf', '5',
           '-qmin', '2', '-qmax', '30', '-auto-alt-ref', '0', '-g', str(fps), '-pix_fmt', 'yuv420p', str(out))
    Path(tmp).unlink()
    capture.save(Image.open(io.BytesIO(base64.b64decode(page.evaluate(grab, 7.4).split(',', 1)[1]))).convert('RGB'), 'workshop.webp', quality=82)
    print(f'{out.name} {W}x{H} {len(frames)} frames {out.stat().st_size // 1024} KB')
    page.close()


def promo_cube(b, loop=18.0, fps=30):
    """step 4: the Promo Market's cube turning as their page turns it ("v promo marketu se ta 3D krychle neotaci tak jak
    na live webu"): their CSS animations held still and set frame by frame, each run a whole number of its own cycles
    in `loop` seconds (the cube's sway is 18 s; the rest within 11 % of their pace), so the clip loops without a seam;
    filmed at 2x over the box capture.promo leaves empty, laid there by the page (quest.css .promo3d .cube)"""
    page, srv, r = capture.promo_page(b)
    box = capture.promo_cube_box(page, r)
    n = page.evaluate("""(L) => { const host = document.querySelector('section.hero .aura').parentElement;
      window.__cube = host.getAnimations({ subtree: true }).map(a => { a.pause(); const d = a.effect.getComputedTiming().duration;
        return { a, f: Math.max(1, Math.round(L * 1000 / d)) * d / L }; });
      window.__at = (t) => window.__cube.forEach(c => { c.a.currentTime = t * c.f; });
      return window.__cube.length; }""", loop)
    print('promo_cube: animations held', n, 'box', box['pct'])
    clip = {'x': box['x'], 'y': box['y'], 'width': box['width'], 'height': box['height']}
    frames = []
    for i in range(int(loop * fps)):
        page.evaluate('(t) => window.__at(t)', i / fps)
        frames.append(page.screenshot(clip=clip, type='jpeg', quality=92))
    page.close()
    srv.shutdown()
    CLIPS.mkdir(exist_ok=True)
    fd, tmp = tempfile.mkstemp(suffix='.mjpeg')
    os.close(fd)
    Path(tmp).write_bytes(b''.join(frames))
    out = CLIPS / 'promo-cube.webm'
    ffmpeg('-f', 'image2pipe', '-c:v', 'mjpeg', '-framerate', str(fps), '-i', tmp, '-vf', 'scale=trunc(iw/2)*2:trunc(ih/2)*2', '-c:v', 'libvpx', '-b:v', '4M', '-crf', '8',
           '-qmin', '2', '-qmax', '30', '-auto-alt-ref', '0', '-g', str(fps), '-pix_fmt', 'yuv420p', str(out))
    Path(tmp).unlink()
    capture.save(Image.open(io.BytesIO(frames[0])).convert('RGB'), 'promo-cube.webp', quality=86)
    print(f'{out.name} {len(frames)} frames {out.stat().st_size // 1024} KB')


SHOTS = {'office': office, 'workshop': workshop, 'lab': lab, 'market': market, 'outlines': outlines, 'universe': universe}
# (the twelfth take's doors show step 1's HQ and step 5's Universe, so the start tutorial's own two are no longer made)
EXTRA = {'universe-mock': universe_mock, 'doors': doors, 'farmer': farmer, 'promo-cube': promo_cube}


def main(names):
    with sync_playwright() as p:
        b = p.chromium.launch(channel='chrome', args=capture.GPU)
        for name in names:
            (SHOTS.get(name) or EXTRA[name])(b)
        b.close()


if __name__ == '__main__':
    main(sys.argv[1:] or list(SHOTS))
