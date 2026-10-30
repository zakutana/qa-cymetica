"""The clips for the Quest steps page, into clips/ (not in git: ~30 MB that record.py makes again), and a poster of
each into pics/ (kept: what the page shows before a clip plays, or if it is missing).

Fifth take (the operator, 2026-10-30): "v kazdem kroku musi byt top animace".

  clip            what moves                                              from
  station.webm    the company's station (Rift Hold, gold) turning         LIVE builder, its first step
  office.webm     the HQ coming in once, then its astronauts at work      LIVE builder, its Start, 1920 x 1080 laid out
  workshop.webm   the arms take the idea and build the product, 10 s      scenes/tools.html, frame by frame: a true loop
  farmer.webm     the Airdrop Farmer turning and blinking, the gem turning our Universe mock, a still camera (capture.py)
  universe.webm   the whole Universe: every company on its orbit          LIVE cymetica.com/company/app#universe

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


def record(page, sel, seconds, name, bps=8_000_000):
    """the canvas `sel` for `seconds`, kept as clips/<name>.webm (remuxed, so it knows its length), and its first
    frame as pics/<name>.webp"""
    CLIPS.mkdir(exist_ok=True)
    r = page.evaluate(RECORD, [sel, int(seconds * 1000), bps])
    fd, tmp = tempfile.mkstemp(suffix='.webm')
    os.close(fd)
    raw = Path(tmp)
    raw.write_bytes(base64.b64decode(r['b64']))
    out = CLIPS / f'{name}.webm'
    ffmpeg('-i', str(raw), '-c', 'copy', str(out))
    raw.unlink()
    print(f'{out.name} {r["w"]}x{r["h"]} {r["mime"]} {out.stat().st_size // 1024} KB')
    return out


def poster(page, sel, name):
    """what the canvas shows now, as the clip's poster"""
    data = page.evaluate("(sel) => document.querySelector(sel).toDataURL('image/jpeg', 0.92)", sel)
    img = Image.open(io.BytesIO(base64.b64decode(data.split(',', 1)[1]))).convert('RGB')
    capture.save(img, f'{name}.webp', quality=82)


def office(b, seconds=16):
    """the live builder's Start in 3D at 1920 x 1080, drawn at 0.75 of it, its astronauts walking; ninth take: the camera
    closer, so the HQ fills the picture as his own screenshot of it does ("zobrazil jen ty headquarters ... v takovem
    zaberu jak posilam"), and the HQ's box in the frame printed, for the page's crop (quest.css #s1 .crop)"""
    page = b.new_page(viewport={'width': 1920, 'height': 1080}, device_scale_factor=0.75)
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
    # the camera in to 0.72 of the way (at 0.8 its rooms touched the builder's stage; the canvas is wider than that
    # stage, and the page crops to the HQ), then still, its astronauts at work; the page plays only the still part
    # ("kasli na tu animaci zoomu"), from data-loop-from, so the poster is a frame of that part
    page.evaluate("""() => { const o = CO.builder.office;
      const p0 = o.camera.position.clone(), t0 = o.controls.target.clone();
      o.tween(t0.clone().add(p0.clone().sub(t0).multiplyScalar(0.72)), t0, 3500); }""")
    record(page, sel, seconds, 'office')
    page.close()
    frame_poster('office', 5.0)
    # the HQ's box in the frame: what is lit after the stars are smoothed away (its plate, rooms and the rock under it)
    import numpy as np
    from PIL import ImageFilter
    im = Image.open(capture.OUT / 'office.webp').convert('L').filter(ImageFilter.MedianFilter(9))
    a = np.asarray(im, np.float32)
    ys, xs = np.nonzero(a > 46)
    f = lambda v, d: round(float(v) / d * 100, 2)
    print('office: the HQ in the frame (left, top, width, height, % of the frame):',
          f(xs.min(), a.shape[1]), f(ys.min(), a.shape[0]), f(xs.max() - xs.min(), a.shape[1]), f(ys.max() - ys.min(), a.shape[0]))


def frame_poster(name, at):
    """the clip's frame at `at` seconds as its poster"""
    fd, tmp = tempfile.mkstemp(suffix='.png')
    os.close(fd)
    ffmpeg('-ss', str(at), '-i', str(CLIPS / f'{name}.webm'), '-frames:v', '1', '-c:v', 'png', '-f', 'image2', tmp)
    capture.save(Image.open(tmp).convert('RGB'), f'{name}.webp', quality=82)
    Path(tmp).unlink()


# the Quant Lab's clock run faster: its first four stages (BUILD to THE BAR, 16.6 s of its time, ql.js BASE) in FAST
# real seconds, then FOUND at its own pace ("nacasovat animaci ze uz po 5 sekundach se zrodi hero agent"). Its reactor
# reads performance.now(), so that is what is bent, from the moment __warp is set
LAB_FAST, LAB_FOUND = 5.0, 7.0
LAB_WARP = """(() => { const real = performance.now.bind(performance), K = 16.6 / %f, A = %f * 1000;
  window.__warp = null;
  performance.now = () => { const r = real(); if (window.__warp == null) return r; const e = r - window.__warp; return window.__warp + (e < A ? e * K : A * K + (e - A)); }; })()""" % (LAB_FAST, LAB_FAST)


def lab(b):
    """step 3: the Quant Lab's page in its Coming soon mode (outbox/quant-lab-v2, another session's page, served here
    and read only), whole from its heading to its reactor ("zobrazit celkove tu stranku i s tim nadpisem quant lab"):
    its stages BUILD to THE BAR in 5 s, then FOUND, the agent born, at its own 7 s; the clip then loops. It draws
    CoinGecko's coin logos into its canvas, which taints it, and a tainted canvas's own stream stops: so the window is
    filmed instead (Playwright's video) and cut by ffmpeg"""
    import shutil
    vw, vh, total = 1400, 1100, LAB_FAST + LAB_FOUND   # 1400 wide: its six score tiles stay one row
    tmpdir = Path(tempfile.mkdtemp())
    ctx = b.new_context(viewport={'width': vw, 'height': vh}, device_scale_factor=1, record_video_dir=str(tmpdir), record_video_size={'width': vw, 'height': vh})
    t0 = time.time()
    page = ctx.new_page()
    page.add_init_script(LAB_WARP)
    page.goto(capture.serve(capture.OUTBOX / 'quant-lab-v2') + '?mode=sim', wait_until='load', timeout=60000)
    page.wait_for_function("() => document.fonts.status === 'loaded' && document.querySelector('#rx').width > 0", timeout=60000)
    page.evaluate("() => document.querySelector('.q2-hero').scrollIntoView({ block: 'start' })")
    page.evaluate("() => window.scrollBy(0, -14)")
    time.sleep(3)
    r = page.evaluate("""() => { const a = document.querySelector('.q2-hero').getBoundingClientRect(), b = document.querySelector('.q2-reactor').getBoundingClientRect();
      return [Math.min(a.left, b.left) - 6, a.top - 10, Math.max(a.right, b.right) - Math.min(a.left, b.left) + 12, b.bottom - a.top + 12].map(Math.round); }""")
    page.evaluate('() => { window.__warp = performance.now(); }')
    page.click('#rail [data-st="0"]')           # from the top: BUILD, on the bent clock
    start = time.time() - t0
    time.sleep(total + 0.6)
    video = page.video.path()
    ctx.close()
    CLIPS.mkdir(exist_ok=True)
    x, y, w, h = r[0] // 2 * 2, r[1] // 2 * 2, r[2] // 2 * 2, r[3] // 2 * 2
    ffmpeg('-ss', f'{start:.2f}', '-i', str(video), '-t', str(total), '-vf', f'crop={w}:{h}:{x}:{y}', '-c:v', 'libvpx', '-b:v', '6M', '-crf', '8',
           '-qmin', '2', '-qmax', '30', '-auto-alt-ref', '0', '-pix_fmt', 'yuv420p', str(CLIPS / 'lab.webm'))
    shutil.rmtree(tmpdir, ignore_errors=True)
    print('lab: the page', w, 'x', h, 'from', round(start, 2), 's,', total, 's,', (CLIPS / 'lab.webm').stat().st_size // 1024, 'KB')
    frame_poster('lab', LAB_FAST + 3.2)        # the agent found


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


def farmer(b, seconds=12):
    """our Universe mock, capture.py's composition (the farmer near, the gem behind it), the camera still while the
    farmer turns and blinks and the gem turns; where the two names stand, for the page's own labels over the clip"""
    page = capture.universe(b, viewport={'width': 1600, 'height': 1000}, dsf=1)
    page.evaluate(capture.FARMER_SHOT)
    time.sleep(3)
    sel = '#uv3d canvas'
    print('farmer: names over the canvas (left, top %):', page.evaluate("""() => { const c = document.querySelector('#uv3d canvas').getBoundingClientRect();
      return ['ad-farmer', 'ad-gem'].map(id => { const e = CO.uv.items.find(x => x.c.id === id).el.getBoundingClientRect();
        return [id, +((e.left + e.width / 2 - c.left) / c.width * 100).toFixed(1), +((e.top - c.top) / c.height * 100).toFixed(1)]; }); }"""))
    poster(page, sel, 'farmer')
    record(page, sel, seconds, 'farmer')
    page.close()


def universe(b, seconds=20):
    """step 5: the LIVE Universe (cymetica.com/company/app#universe), its sky, its sun, every real company and product
    on its orbits ("v univerzu je pozadi mnohem lepe udelane"), the camera still; its map idles after 1.5 s without
    input, so it is poked awake every 0.8 s. The companies it has today are printed."""
    page = b.new_page(viewport={'width': 1920, 'height': 1080}, device_scale_factor=1)
    page.goto('https://cymetica.com/company/app#universe', wait_until='domcontentloaded', timeout=60000)
    page.wait_for_function("() => window.CO && CO.uv && CO.uv.camera && CO.uv.items && CO.uv.items.length", timeout=90000)
    time.sleep(8)
    page.evaluate("() => { setInterval(() => { CO.uv.lastInput = performance.now(); }, 800); }")
    time.sleep(1)
    sel = '#uv3d canvas'
    print('universe (live): companies', page.evaluate("() => CO.uv.items.filter(it => !it.kind).length"),
          'products', page.evaluate("() => CO.uv.items.filter(it => it.kind === 'product').length"))
    poster(page, sel, 'universe')
    record(page, sel, seconds, 'universe')
    page.close()


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


def workshop(b, fps=30, at=None):
    """scenes/tools.html drawn frame by frame through its PERIOD (render(t) is a function of t alone, so the last frame
    leads into the first), encoded to VP8 by Playwright's ffmpeg; `at` (seconds) only pictures those moments"""
    base = capture.serve(HERE)
    page = b.new_page(viewport={'width': W, 'height': H})
    page.goto(base + f'scenes/tools.html?w={W}&h={H}&frames', wait_until='load', timeout=60000)
    page.wait_for_function('window.READY === true', timeout=60000)
    grab = "(t) => { window.render(t); return document.querySelector('canvas').toDataURL('image/jpeg', 0.93); }"
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
    ffmpeg('-f', 'image2pipe', '-c:v', 'mjpeg', '-framerate', str(fps), '-i', tmp, '-c:v', 'libvpx', '-b:v', '8M', '-crf', '8',
           '-qmin', '2', '-qmax', '30', '-auto-alt-ref', '0', '-g', str(fps), '-pix_fmt', 'yuv420p', str(out))
    Path(tmp).unlink()
    capture.save(Image.open(io.BytesIO(base64.b64decode(page.evaluate(grab, 7.4).split(',', 1)[1]))).convert('RGB'), 'workshop.webp', quality=82)
    print(f'{out.name} {W}x{H} {len(frames)} frames {out.stat().st_size // 1024} KB')
    page.close()


SHOTS = {'office': office, 'workshop': workshop, 'lab': lab, 'farmer': farmer, 'universe': universe, 'doors': doors}
EXTRA = {'universe-mock': universe_mock}


def main(names):
    with sync_playwright() as p:
        b = p.chromium.launch(channel='chrome', args=capture.GPU)
        for name in names:
            (SHOTS.get(name) or EXTRA[name])(b)
        b.close()


if __name__ == '__main__':
    main(sys.argv[1:] or list(SHOTS))
